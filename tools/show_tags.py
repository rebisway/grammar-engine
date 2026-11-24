# grammar-engine - tool: prints the readings left by the tagger for a text.
#
#   python tools/show_tags.py fr "Il le porte sur la table."
#
# SPDX-License-Identifier: MIT
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import grammar_engine
from grammar_engine import tagger
from grammar_engine.core import Paragraph
from grammar_engine.text import tokenize

NAMES = {1: 'NOUN', 2: 'ADJ', 4: 'VERB', 8: 'AUX', 16: 'DET', 32: 'PRON', 64: 'ADP', 128: 'ADV', 256: 'CCONJ', 512: 'SCONJ', 1024: 'PROPN', 2048: 'INTJ', 4096: 'OTHER'}


def names(mask):
    return {n for bit, n in NAMES.items() if mask & bit}


def tags(checker, text):
    g = checker.grammar
    p = Paragraph(text, tokenize(text, g.elisions), g)
    tagger.assign(p, checker.lexicon)
    g.disambiguate(p)
    return p


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    c = grammar_engine.Checker(sys.argv[1])
    for t in tags(c, sys.argv[2]).tokens:
        print('%-12s %s' % (t.text, ' | '.join(sorted(set().union(*(names(a.pos) for a in t.tags)))) if t.tags else ''))
