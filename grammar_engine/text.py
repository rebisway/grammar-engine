# grammar-engine - text helpers: case, tokens
# SPDX-License-Identifier: MIT

from dataclasses import dataclass


@dataclass
class Token:
    """A word, a number or a punctuation mark, with its range in the paragraph and the readings the tagger left on it."""
    kind: str                   # 'word', 'number' or 'punct'
    text: str                   # as written
    low: str                    # lower case, with the straight apostrophe
    start: int                  # code points in the paragraph
    end: int
    space_before: bool = False
    tags: tuple = ()            # readings left by the tagger (lexicon analyses)

    @property
    def is_word(self):
        """True for a word."""
        return self.kind == 'word'


def lower(s):
    """Lower case, the typographic apostrophe becomes the straight one."""
    return s.lower().replace('’', "'")


def blen(s):
    """Length in UTF-8 bytes (some thresholds were written for bytes)."""
    return len(s.encode('utf-8'))


def match_case(original, replacement):
    """The replacement written like the original: a capital letter at the start if the original has one."""
    if original and original[0].isupper() and replacement and replacement[0].islower():
        return replacement[0].upper() + replacement[1:]
    return replacement


def tokenize(text, elisions=()):
    """Cuts a paragraph into words, numbers and punctuation, with their range and the space before them.
    An apostrophe followed by a letter stays in the word, except for the elisions of the language
    ("l'", "qu'"): the elided article is a token of its own."""
    tokens = []
    space = True
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ' \t  ':
            space = True
            i += 1
            continue
        if c.isalpha():
            j = i
            while j < n:
                d = text[j]
                if d.isalpha():
                    j += 1
                elif d in "'’-" and j + 1 < n and text[j + 1].isalpha():
                    j += 1
                else:
                    break
            word = text[i:j]
            low = lower(word)
            cut = -1
            ap = low.find("'")
            if elisions and 0 <= ap < len(low) - 1 and low[:ap + 1] in elisions:
                cut = ap + 1
            if cut > 0:
                tokens.append(Token('word', word[:cut], low[:cut], i, i + cut, space))
                tokens.append(Token('word', word[cut:], lower(word[cut:]), i + cut, j, False))
            else:
                tokens.append(Token('word', word, low, i, j, space))
            space = False
            i = j
            continue
        if '0' <= c <= '9':
            j = i
            while j < n and (text[j].isdigit() or (text[j] in '.,' and j + 1 < n and text[j + 1].isdigit())):
                j += 1
            tokens.append(Token('number', text[i:j], text[i:j], i, j, space))
            space = False
            i = j
            continue
        if text.startswith('...', i):
            tokens.append(Token('punct', '…', '…', i, i + 3, space))
            i += 3
        else:
            tokens.append(Token('punct', c, c, i, i + 1, space))
            i += 1
        space = False
    return tokens
