"""Checks a lexicon file (.lex): prints its size and, with --spot, looks up a few well-known words and compares what the file says.

    python tools/check_lexicon.py grammar_engine/data/fr.lex --lang fr --spot

Exit code 0 when the file loads (and, with --spot, when every check passes), 1 otherwise. It is the last step of tools/build_lexicons.py,
and the test to run by hand after building a lexicon.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from grammar_engine import lexicon as lx          # noqa: E402

# Spot checks: (word, lemma, part of speech mask, number, verb form). None = do not compare that field.
# A check passes when one analysis of the word matches every field which is given.
SPOT = {
    'fr': [
        ('chats', 'chat', lx.NOUN, lx.PLURAL, None), ('belle', 'beau', lx.ADJ, lx.SINGULAR, None), ('mangeons', 'manger', lx.VERB, lx.PLURAL, lx.PRESENT),
        ('mangé', 'manger', lx.VERB, None, lx.PAST_PARTICIPLE), ('les', 'le', lx.DET, lx.PLURAL, None), ('serait', 'être', lx.AUX, None, lx.CONDITIONAL),
        ('manger', 'manger', lx.VERB, None, lx.INFINITIVE),
    ],
    'en': [
        ('went', 'go', lx.VERB, None, lx.IMPERFECT), ('gone', 'go', lx.VERB, None, lx.PAST_PARTICIPLE), ('goes', 'go', lx.VERB, lx.SINGULAR, lx.PRESENT),
        ('children', 'child', lx.NOUN, lx.PLURAL, None), ('books', 'book', lx.NOUN, lx.PLURAL, None), ('set', 'set', lx.VERB, None, lx.IMPERFECT),
        ('the', 'the', lx.DET, None, None), ('running', 'run', lx.VERB, None, lx.PRESENT_PARTICIPLE),
    ],
    'es': [
        ('hablamos', 'hablar', lx.VERB, lx.PLURAL, None), ('hablado', 'hablar', lx.VERB, None, lx.PAST_PARTICIPLE), ('casas', 'casa', lx.NOUN, lx.PLURAL, None),
        ('blanca', 'blanco', lx.ADJ, lx.SINGULAR, None), ('fui', 'ir', lx.VERB, lx.SINGULAR, lx.PAST_SIMPLE), ('hablar', 'hablar', lx.VERB, None, lx.INFINITIVE),
    ],
}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Checks a lexicon file.')
    ap.add_argument('lexicon', help='the .lex file')
    ap.add_argument('--lang', choices=sorted(SPOT), help='language of the file, for --spot')
    ap.add_argument('--spot', action='store_true', help='compare a few well-known words with what the file says')
    args = ap.parse_args(argv)

    try:
        lex = lx.Lexicon(args.lexicon)
    except (OSError, ValueError) as e:
        print('Cannot load %s: %s' % (args.lexicon, e))
        return 1
    print('%s: %.1f MB, %d forms, %d lemmas, %d analyses' % (os.path.basename(args.lexicon), os.path.getsize(args.lexicon) / 1e6, lex._forms, lex._lemmas, lex._count))
    if lex._forms == 0:
        print('the file is empty')
        return 1
    if not args.spot:
        return 0
    if not args.lang:
        print('--spot needs --lang')
        return 1
    failed = 0
    for word, lemma, pos, number, form in SPOT[args.lang]:
        found = False
        for a in lex.analyses(word):
            if lex.lemma(a) == lemma and a.pos & pos and (number is None or a.number in (number, lx.INVARIABLE)) and (form is None or a.verb_form == form):
                found = True
                break
        print('  %-10s %s' % (word, 'ok' if found else 'MISSING (lemma %s)' % lemma))
        failed += not found
    print('%d of %d checks failed' % (failed, len(SPOT[args.lang])) if failed else 'all checks passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
