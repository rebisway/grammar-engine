# grammar-engine - tagger: which reading of each word is the right one in its sentence.
#
# The lexicon gives every analysis of a word ("porte": noun, or verb). The tagger starts from all of them and removes the
# readings which the neighbours exclude, with the rules of the language (Grammar.disambiguate, constraints written as
# keep / drop / select on a token). A rule never empties a word: when every reading would go, the word is left as it is.
# After tagging, token.tags holds the remaining analyses (one, or still several when the context does not decide).
# SPDX-License-Identifier: MIT

from . import lexicon as lx

FINITE = range(lx.PRESENT, lx.SUBJUNCTIVE_IMPERFECT + 1)
UNKNOWN = lx.Analysis(-1, lx.OTHER, 0, 0, 0, 0, -1)


def assign(p, lex):
    """Every analysis of the lexicon on each word; an unknown word gets one reading (a proper name inside a sentence, else other)."""
    for i, t in enumerate(p.tokens):
        if t.kind != 'word':
            continue
        an = lex.analyses(t.text)
        if an:
            t.tags = an
        else:
            capital = t.text[0].isupper() and i > 0 and p.tokens[i - 1].text not in ('.', '!', '?')
            t.tags = (UNKNOWN._replace(pos=lx.PROPN if capital else lx.OTHER),)


def narrow(tags, mask):
    """The analyses which have a part of speech of the mask, their own mask reduced to it."""
    return tuple(a if not a.pos & ~mask else a._replace(pos=a.pos & mask) for a in tags if a.pos & mask)


def keep(t, mask):
    """Keeps the readings of the mask. Not done if none would stay."""
    n = narrow(t.tags, mask)
    if n:
        t.tags = n
    return bool(n)


def drop(t, mask):
    """Removes the readings of the mask. Not done if none would stay."""
    n = narrow(t.tags, ~mask & ((1 << 13) - 1))
    if n:
        t.tags = n
    return bool(n)


def select(t, predicate):
    """Keeps the readings which satisfy the predicate. Not done if none would stay."""
    n = tuple(a for a in t.tags if predicate(a))
    if n:
        t.tags = n
    return bool(n)


def only(t, mask):
    """True when every reading of the word is of the mask."""
    return bool(t.tags) and all(not a.pos & ~mask for a in t.tags)


def has(t, mask):
    """True when a reading of the word is of the mask."""
    return any(a.pos & mask for a in t.tags)


def pos(t):
    """The part of speech of a word when its readings agree on one, else 0."""
    masks = {a.pos for a in t.tags}
    return masks.pop() if len(masks) == 1 else 0
