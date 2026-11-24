"""Builds data/es.lex (the format of fr.lex and en.lex) from the Spanish dictionary of Wiktionary extracted by kaikki.org (JSON lines, CC BY-SA 4.0).

    curl -s https://kaikki.org/dictionary/Spanish/kaikki.org-dictionary-Spanish.jsonl | python tools/build_lexicon_es.py grammar_engine/data/es.lex

The source text is read as a stream and not kept. In this dictionary the inflected forms are entries of their own
("habla": form of hablar, third-person singular present indicative): they give most of the analyses. The entries of the
lemmas give the base form of the nouns, adjectives and verbs and the plural, feminine and superlative forms they list.
"""

import json
import struct
import sys

NOUN, ADJ, VERB, AUX, DET, PRON, ADP, ADV, CCONJ, SCONJ, PROPN, INTJ, OTHER = (1 << k for k in range(13))
PRESENT, IMPERFECT, PAST_SIMPLE, FUTURE, CONDITIONAL, SUBJ_PRESENT, SUBJ_IMPERFECT, IMPERATIVE, INFINITIVE, PRESENT_PARTICIPLE, PAST_PARTICIPLE = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11

POS = {'noun': NOUN, 'verb': VERB, 'adj': ADJ, 'adv': ADV, 'det': DET, 'article': DET, 'pron': PRON, 'prep': ADP, 'postp': ADP, 'conj': CCONJ,
       'intj': INTJ, 'name': PROPN, 'num': OTHER, 'particle': OTHER, 'contraction': ADP | DET}
AUXILIARIES = {'ser', 'estar', 'haber'}
SKIP_TAGS = {'obsolete', 'archaic', 'nonstandard', 'misspelling', 'pronunciation-spelling', 'proscribed', 'alternative', 'rare'}


def is_word(s):
    """True for a one-word entry: letters, apostrophe and hyphen only."""
    return bool(s) and s[0].isalpha() and all(c.isalpha() or c in "'-" for c in s)


def features(tags):
    """(gender, number, person, verb form) from the tags of an inflected form of Wiktionary."""
    gender = 3 if 'masculine' in tags and 'feminine' in tags else 1 if 'masculine' in tags else 2 if 'feminine' in tags else 0
    number = 1 if 'singular' in tags else 2 if 'plural' in tags else 0
    persons = [n for n, t in ((1, 'first-person'), (2, 'second-person'), (3, 'third-person')) if t in tags] or [0]
    if 'infinitive' in tags:
        vf = INFINITIVE
    elif 'participle' in tags and 'past' in tags:
        vf = PAST_PARTICIPLE
    elif 'gerund' in tags or ('participle' in tags and 'present' in tags):
        vf = PRESENT_PARTICIPLE
    elif 'imperative' in tags:
        vf = IMPERATIVE
    elif 'subjunctive' in tags:
        vf = SUBJ_IMPERFECT if 'imperfect' in tags else SUBJ_PRESENT
    elif 'conditional' in tags:
        vf = CONDITIONAL
    elif 'future' in tags:
        vf = FUTURE
    elif 'preterite' in tags:
        vf = PAST_SIMPLE
    elif 'imperfect' in tags:
        vf = IMPERFECT
    elif 'present' in tags:
        vf = PRESENT
    else:
        vf = 0
    return gender, number, persons, vf


def main():
    """Reads the kaikki.org JSON lines on the standard input and writes the lexicon to argv[1]."""
    target = sys.argv[1]
    lemmas, lemma_list, entries = {}, [], {}
    count = 0

    def lemma_id(lemma):
        """The number of a lemma, given in the order it is first seen."""
        lid = lemmas.get(lemma)
        if lid is None:
            lid = lemmas[lemma] = len(lemma_list)
            lemma_list.append(lemma)
        return lid

    def add(form, lemma, pos, gender=0, number=0, person=0, verb_form=0):
        """Records one analysis of a form; the forms of an auxiliary verb are marked VERB | AUX."""
        if lemma in AUXILIARIES and pos == VERB:
            pos = VERB | AUX
        entries.setdefault(form, set()).add((lemma_id(lemma), pos, gender, number, person, verb_form))

    for line in sys.stdin.buffer:
        count += 1
        if count % 200000 == 0:
            print(count, 'entries read,', len(entries), 'forms', file=sys.stderr)
        d = json.loads(line)
        if d.get('lang_code') != 'es':
            continue
        word, pos = d['word'], POS.get(d['pos'])
        if pos is None or not is_word(word):
            continue
        senses = d.get('senses') or []
        name = pos == PROPN
        form = word if name else word.lower()
        if senses and all(SKIP_TAGS & set(s.get('tags', [])) for s in senses):
            continue
        # An inflected form: the analyses come from the tags of its senses
        inflected = [s for s in senses if s.get('form_of') and 'form-of' in s.get('tags', []) and not SKIP_TAGS & set(s.get('tags', []))]
        if inflected:
            for s in inflected:
                lemma = s['form_of'][0].get('word', '')
                if not is_word(lemma):
                    continue
                gender, number, persons, vf = features(set(s.get('tags', [])))
                for person in persons:
                    add(form, lemma.lower(), pos, gender, number, person, vf)
            if len(inflected) == len(senses):
                continue
        # A lemma
        tags = {t for s in senses if not s.get('form_of') for t in s.get('tags', [])}
        forms = [(f['form'], set(f.get('tags', []))) for f in d.get('forms') or [] if is_word(f.get('form', '')) and not SKIP_TAGS & set(f.get('tags', []))]
        lemma = form
        if name:
            add(form, lemma, pos, number=1)
        elif pos == NOUN:
            gender = 3 if 'masculine' in tags and 'feminine' in tags else 1 if 'masculine' in tags else 2 if 'feminine' in tags else 0
            add(form, lemma, pos, gender, 2 if 'plural-only' in tags else 1)
            for text, ft in forms:
                if 'plural' in ft:
                    add(text.lower(), lemma, pos, 2 if 'feminine' in ft else gender, 2)
                elif 'feminine' in ft:
                    add(text.lower(), lemma, pos, 2, 1)
        elif pos == ADJ:
            has_feminine = any('feminine' in ft for _, ft in forms)
            invariable = not forms or all(ft & {'superlative', 'comparative'} for _, ft in forms)
            add(form, lemma, pos, 1 if has_feminine else 3, 3 if invariable and not has_feminine else 1)
            for text, ft in forms:
                if 'superlative' in ft:
                    add(text.lower(), lemma, pos, 1, 1)
                elif 'plural' in ft:
                    add(text.lower(), lemma, pos, 2 if 'feminine' in ft else (1 if has_feminine else 3), 2)
                elif 'feminine' in ft:
                    add(text.lower(), lemma, pos, 2, 1)
        elif pos == VERB:
            add(form, lemma, pos, verb_form=INFINITIVE)
        else:
            add(form, lemma, pos)
            for text, ft in forms:
                if 'plural' in ft or 'feminine' in ft:
                    g = 2 if 'feminine' in ft else 1 if 'masculine' in ft else 0
                    add(text.lower(), lemma, pos, g, 2 if 'plural' in ft else 1)

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
