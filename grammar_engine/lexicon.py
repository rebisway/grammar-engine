# grammar-engine - lexicon: every inflected form of a language with its analyses,
# as Universal Dependencies features (part of speech, gender, number, person, verb form).
# The file is made by tools/build_lexicon.py. Layout (little endian): "BNLX", version, forms, lemmas, analyses,
# 0, size of the lemma blob, size of the form blob, lemma offsets, lemma blob, form offsets, form blob,
# index of the first analysis of each form, analyses (8 bytes: lemma u32, part of speech mask u16, features u8, verb form u8).
# SPDX-License-Identifier: MIT

import struct
from bisect import bisect_right
from collections import namedtuple
from functools import lru_cache

# Part of speech (a mask: "nom adj" is NOUN | ADJ)
NOUN, ADJ, VERB, AUX, DET, PRON, ADP, ADV, CCONJ, SCONJ, PROPN, INTJ, OTHER = (1 << k for k in range(13))
# Gender
NO_GENDER, MASCULINE, FEMININE, EPICENE = 0, 1, 2, 3
# Number
NO_NUMBER, SINGULAR, PLURAL, INVARIABLE = 0, 1, 2, 3
# Verb form
(NO_FORM, PRESENT, IMPERFECT, PAST_SIMPLE, FUTURE, CONDITIONAL, SUBJUNCTIVE_PRESENT, SUBJUNCTIVE_IMPERFECT,
 IMPERATIVE, INFINITIVE, PRESENT_PARTICIPLE, PAST_PARTICIPLE) = range(12)

Analysis = namedtuple('Analysis', 'lemma pos gender number person verb_form index')

_RECORD = struct.Struct('<IHBB')


class Lexicon:
    """The inflected forms of a language with their analyses. The file is read once; the lookups are binary searches in memory."""
    def __init__(self, path=None):
        """Loads the file when a path is given."""
        self._forms = 0
        self._by_lemma = None
        if path:
            self.load(path)

    @property
    def loaded(self):
        """True when a lexicon is loaded."""
        return self._forms > 0

    def load(self, path):
        """Reads a BNLX file and builds the views on its tables. Raises ValueError if the file is not a lexicon of version 1."""
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) < 36 or data[:4] != b'BNLX':
            raise ValueError('not a lexicon file: %s' % path)
        version, forms, lemmas, analyses, _, lemma_blob, form_blob = struct.unpack_from('<7I', data, 4)
        if version != 1:
            raise ValueError('unknown lexicon version %d' % version)
        view = memoryview(data)
        p = 32

        def table(count):
            nonlocal p
            t = view[p:p + 4 * count].cast('I')
            p += 4 * count
            return t

        self._lemma_offsets = table(lemmas + 1)
        self._lemma_blob = view[p:p + lemma_blob]
        p += lemma_blob
        self._form_offsets = table(forms + 1)
        self._form_blob = view[p:p + form_blob]
        p += form_blob
        self._first = table(forms + 1)
        self._records = view[p:p + 8 * analyses]
        self._data = data
        self._forms, self._lemmas, self._count = forms, lemmas, analyses
        self._by_lemma = None
        Lexicon.analyses.cache_clear()

    # Index of a form by binary search; -1 when the word is unknown
    def _find(self, word):
        """Index of a form by binary search on its UTF-8 bytes; -1 when the word is unknown."""
        key = word.encode('utf-8')
        lo, hi = 0, self._forms
        off, blob = self._form_offsets, self._form_blob
        while lo < hi:
            mid = (lo + hi) // 2
            s = bytes(blob[off[mid]:off[mid + 1]])
            if s == key:
                return mid
            if s < key:
                lo = mid + 1
            else:
                hi = mid
        return -1

    def _read(self, index):
        """The analysis number `index` as a namedtuple."""
        lemma, pos, feat, verb_form = _RECORD.unpack_from(self._records, 8 * index)
        return Analysis(lemma, pos, feat & 3, (feat >> 2) & 3, (feat >> 4) & 3, verb_form, index)

    @lru_cache(maxsize=50000)
    def analyses(self, word):
        """Every analysis of a word as written, else in lower case (the first word of a sentence). A tuple, empty if unknown."""
        form = self._find(word)
        if form < 0:
            low = word.lower()
            form = -1 if low == word else self._find(low)
            if form < 0:
                return ()
        return tuple(self._read(a) for a in range(self._first[form], self._first[form + 1]))

    def lemma(self, a):
        """The lemma of an analysis, as a string."""
        return bytes(self._lemma_blob[self._lemma_offsets[a.lemma]:self._lemma_offsets[a.lemma + 1]]).decode('utf-8')

    def _form_string(self, index):
        """The form which owns the analysis number `index`."""
        form = bisect_right(self._first, index) - 1
        return bytes(self._form_blob[self._form_offsets[form]:self._form_offsets[form + 1]]).decode('utf-8')

    def _build_lemma_index(self):
        """Index lemma -> analyses, built at the first call of inflect()."""
        by = {}
        for idx, (lemma, _, _, _) in enumerate(_RECORD.iter_unpack(self._records)):
            by.setdefault(lemma, []).append(idx)
        self._by_lemma = by

    def inflect(self, model, gender=0, number=0, person=0, verb_form=0):
        """The form of the same lemma and part of speech with other features (0 = any); '' if there is none."""
        if self._by_lemma is None:
            self._build_lemma_index()

        def fits(wanted, has):
            return wanted == 0 or has == wanted or has == 3

        best, best_score = '', -1
        for idx in self._by_lemma.get(model.lemma, ()):
            a = self._read(idx)
            if (a.pos & model.pos) == 0:
                continue
            if not fits(gender, a.gender) or not fits(number, a.number):
                continue
            if (person and a.person != person) or (verb_form and a.verb_form != verb_form):
                continue
            # The most exact form wins: the one which is not epicene or invariable
            score = (2 if a.gender == gender else 0) + (2 if a.number == number else 0)
            if score > best_score:
                best_score, best = score, self._form_string(idx)
        return best
