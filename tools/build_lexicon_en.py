"""Builds data/en.lex (the format of fr.lex) from the English dictionary of Wiktionary extracted by kaikki.org (JSON lines, CC BY-SA 4.0).

    curl -s https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl | python tools/build_lexicon_en.py grammar_engine/data/en.lex

The source text is not kept: it is read as a stream. Every inflected form of every one-word entry becomes an analysis
(lemma, part of speech, number, person, verb form). The degree of an adjective or an adverb is written in the gender field:
1 comparative, 2 superlative.
"""

import json
import re
import struct
import sys

# Parts of speech (a mask, see grammar_engine/lexicon.py)
NOUN, ADJ, VERB, AUX, DET, PRON, ADP, ADV, CCONJ, SCONJ, PROPN, INTJ, OTHER = (1 << k for k in range(13))
SINGULAR, PLURAL = 1, 2
PRESENT, IMPERFECT, INFINITIVE, PRESENT_PARTICIPLE, PAST_PARTICIPLE = 1, 2, 9, 10, 11

POS = {'noun': NOUN, 'verb': VERB, 'adj': ADJ, 'adv': ADV, 'det': DET, 'article': DET, 'pron': PRON, 'prep': ADP, 'postp': ADP, 'conj': CCONJ,
       'intj': INTJ, 'name': PROPN, 'num': OTHER, 'particle': OTHER}
AUXILIARIES = {'be', 'have', 'do', 'will', 'shall', 'can', 'may', 'must', 'might', 'could', 'would', 'should', 'ought'}
SKIP_FORM_TAGS = {'alternative', 'obsolete', 'archaic', 'dialectal', 'nonstandard', 'rare', 'misspelling', 'pronunciation-spelling', 'error-lua-exec', 'class',
                  'table-tags', 'inflection-template', 'variant', 'proscribed', 'no-past-participle', 'abbreviation'}
SKIP_SENSE_TAGS = {'obsolete', 'archaic', 'dialectal', 'rare', 'nonstandard', 'misspelling', 'proscribed'}
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


def main():
    """Reads the kaikki.org JSON lines on the standard input and writes the lexicon to argv[1]."""
    target = sys.argv[1]
    lemmas, lemma_list = {}, []
    entries = {}
    count = 0

    def add(form, lid, pos, gender=0, number=0, person=0, verb_form=0):
        """Records one analysis of a form (a set per form: the same reading is kept once)."""
        entries.setdefault(form, set()).add((lid, pos, gender, number, person, verb_form))

    for line in sys.stdin.buffer:
        count += 1
        if count % 200000 == 0:
            print(count, 'entries read,', len(entries), 'forms', file=sys.stderr)
        d = json.loads(line)
        if d.get('lang_code') != 'en':
            continue
        word, pos_name = d['word'], d['pos']
        pos = POS.get(pos_name)
        if pos is None or not WORD.fullmatch(word):
            continue
        senses = d.get('senses') or []
        if senses and all(('form_of' in s or 'alt_of' in s) for s in senses):
            continue                    # an inflected form or a spelling variant: the entry of the lemma gives it
        if senses and all(SKIP_SENSE_TAGS & set(s.get('tags', [])) for s in senses):
            continue
        lemma = word.lower() if pos != PROPN else word
        lid = lemmas.get(lemma)
        if lid is None:
            lid = lemmas[lemma] = len(lemma_list)
            lemma_list.append(lemma)
        if pos == VERB and lemma in AUXILIARIES:
            pos = AUX if lemma not in ('be', 'have', 'do') else VERB | AUX
        forms = []
        for f in d.get('forms') or []:
            text, tags = f.get('form', ''), set(f.get('tags', []))
            if not WORD.fullmatch(text) or tags & SKIP_FORM_TAGS:
                continue
            forms.append((text, tags))

        if pos == PROPN:
            add(word, lid, pos, number=SINGULAR)
        elif pos == NOUN:
            add(word, lid, pos, number=SINGULAR)
            for text, tags in forms:
                if 'plural' in tags and len(tags) == 1:
                    add(text, lid, pos, number=PLURAL)
        elif pos & (VERB | AUX):
            add(word, lid, pos, verb_form=INFINITIVE)
            add(word, lid, pos, verb_form=PRESENT)
            for text, tags in forms:
                person = 1 if 'first-person' in tags else 2 if 'second-person' in tags else 3 if 'third-person' in tags else 0
                number = SINGULAR if 'singular' in tags else PLURAL if 'plural' in tags else 0
                if 'participle' in tags and 'present' in tags:
                    add(text, lid, pos, verb_form=PRESENT_PARTICIPLE)
                elif 'participle' in tags and 'past' in tags:
                    add(text, lid, pos, verb_form=PAST_PARTICIPLE)
                elif 'past' in tags:
                    add(text, lid, pos, number=number, person=person, verb_form=IMPERFECT)
                elif 'present' in tags:
                    add(text, lid, pos, number=number, person=person, verb_form=PRESENT)
        elif pos & (ADJ | ADV):
            add(word, lid, pos)
            for text, tags in forms:
                if 'comparative' in tags:
                    add(text, lid, pos, gender=1)
                elif 'superlative' in tags:
                    add(text, lid, pos, gender=2)
        else:
            add(word, lid, pos)

    names = sorted(entries, key=lambda s: s.encode('utf-8'))
    lemma_offsets, lemma_blob = [0], bytearray()
    for l in lemma_list:
        lemma_blob += l.encode('utf-8')
        lemma_offsets.append(len(lemma_blob))
    form_offsets, form_blob, first, analyses, total = [0], bytearray(), [0], bytearray(), 0
    for form in names:
        form_blob += form.encode('utf-8')
        form_offsets.append(len(form_blob))
        for (lid, pos, g, n, person, vf) in sorted(entries[form]):
            analyses += struct.pack('<IHBB', lid, pos, (g & 3) | ((n & 3) << 2) | ((person & 3) << 4), vf)
            total += 1
        first.append(total)
    while len(lemma_blob) % 4:
        lemma_blob += bytes(1)
    while len(form_blob) % 4:
        form_blob += bytes(1)
    with open(target, 'wb') as out:
        out.write(b'BNLX')
        out.write(struct.pack('<IIIII', 1, len(names), len(lemma_list), total, 0))
        out.write(struct.pack('<II', len(lemma_blob), len(form_blob)))
        out.write(struct.pack('<%dI' % len(lemma_offsets), *lemma_offsets))
        out.write(bytes(lemma_blob))
        out.write(struct.pack('<%dI' % len(form_offsets), *form_offsets))
        out.write(bytes(form_blob))
        out.write(struct.pack('<%dI' % len(first), *first))
        out.write(bytes(analyses))
    print('%d forms, %d lemmas, %d analyses' % (len(names), len(lemma_list), total))


if __name__ == '__main__':
    main()
