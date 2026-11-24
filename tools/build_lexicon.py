# www.rebisway.com - contact@rebisway.com
# Copyright (C) 2026 Thomas Gourgnier
# SPDX-License-Identifier: MIT
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Builds the compact lexicon of the grammar checker from the "lexique de Grammalecte" (MPL 2.0, https://grammalecte.net/)
#
#   python build_lexicon.py lexique-grammalecte-fr-v7.7.txt ../lexicon/fr.lex
#
# The text file has one line per inflected form: id, fid, form, lemma, tags, ... The tags are turned into the features of Universal Dependencies
# (part of speech, gender, number, person, verb form). The binary file keeps every form once, sorted, with its analyses (see lexicon.h for the layout).

import struct
import sys

POS = {'NOUN': 1, 'ADJ': 2, 'VERB': 4, 'AUX': 8, 'DET': 16, 'PRON': 32, 'ADP': 64, 'ADV': 128, 'CCONJ': 256, 'SCONJ': 512, 'PROPN': 1024, 'INTJ': 2048, 'OTHER': 4096}
FORMS = {'ipre': 1, 'iimp': 2, 'ipsi': 3, 'ifut': 4, 'cond': 5, 'spre': 6, 'simp': 7, 'impe': 8, 'infi': 9, 'ppre': 10, 'ppas': 11}
PERSONS = {'1sg': (1, 1), '2sg': (2, 1), '3sg': (3, 1), '1pl': (1, 2), '2pl': (2, 2), '3pl': (3, 2)}


def analyze(tags):
    """Features of one line: (pos mask, gender, number, [persons], [verb forms])"""
    pos = 0
    gender = 0
    number = 0
    persons = []
    forms = []
    for t in tags.split():
        t = t.rstrip('!')
        if t == 'nom':
            pos |= POS['NOUN']
        elif t == 'adj':
            pos |= POS['ADJ']
        elif t in ('npr', 'patr'):
            pos |= POS['PROPN']
        elif t == 'adv':
            pos |= POS['ADV']
        elif t == 'det':
            pos |= POS['DET']
        elif t.startswith('prep'):
            pos |= POS['ADP']
        elif t == 'cjco':
            pos |= POS['CCONJ']
        elif t == 'cjsub':
            pos |= POS['SCONJ']
        elif t.startswith('pro') or t == 'prn':
            pos |= POS['PRON']
        elif t == 'interj':
            pos |= POS['INTJ']
        elif len(t) > 1 and t[0] == 'v' and t[1].isdigit():
            pos |= POS['AUX'] if t[1] == '0' else POS['VERB']
        elif t == 'mas':
            gender |= 1
        elif t == 'fem':
            gender |= 2
        elif t == 'epi':
            gender |= 3
        elif t == 'sg':
            number |= 1
        elif t == 'pl':
            number |= 2
        elif t == 'inv':
            number |= 3
        elif t in PERSONS:
            persons.append(PERSONS[t])
        elif t in FORMS:
            forms.append(FORMS[t])
    if pos == 0:
        pos = POS['OTHER']
    return pos, gender, number, persons, forms


def main():
    """Reads the Grammalecte text file (argv[1]) and writes the binary lexicon (argv[2])."""
    source, target = sys.argv[1], sys.argv[2]
    lemmas = {}
    lemma_list = []
    entries = {}		# form -> list of analyses (lemma id, pos, gender, number, person, verb form)
    with open(source, encoding='utf-8') as f:
        for line in f:
            cols = line.rstrip('\n').split('\t')
            if len(cols) < 5 or not cols[0].isdigit():
                continue
            form, lemma, tags = cols[2], cols[3], cols[4]
            if not form:
                continue
            lid = lemmas.get(lemma)
            if lid is None:
                lid = lemmas[lemma] = len(lemma_list)
                lemma_list.append(lemma)
            pos, gender, number, persons, forms = analyze(tags)
            found = set()
            for person, pn in (persons or [(0, 0)]):
                for vf in (forms or [0]):
                    # a verb form has the number of its person, a noun or adjective its own
                    n = pn if pn else number
                    g = gender
                    found.add((lid, pos, g, n, person, vf))
            lst = entries.setdefault(form, [])
            for a in sorted(found):
                if a not in lst:
                    lst.append(a)

    forms = sorted(entries, key=lambda s: s.encode('utf-8'))
    lemma_offsets = [0]
    lemma_blob = bytearray()
    for l in lemma_list:
        lemma_blob += l.encode('utf-8')
        lemma_offsets.append(len(lemma_blob))
    form_offsets = [0]
    form_blob = bytearray()
    first = [0]
    analyses = bytearray()
    count = 0
    for form in forms:
        form_blob += form.encode('utf-8')
        form_offsets.append(len(form_blob))
        for (lid, pos, g, n, person, vf) in entries[form]:
            analyses += struct.pack('<IHBB', lid, pos, (g & 3) | ((n & 3) << 2) | ((person & 3) << 4), vf)
            count += 1
        first.append(count)

    # The blobs are padded so every table which follows is aligned on 4 bytes
    while len(lemma_blob) % 4:
        lemma_blob += bytes(1)
    while len(form_blob) % 4:
        form_blob += bytes(1)

    with open(target, 'wb') as out:
        out.write(b'BNLX')
        out.write(struct.pack('<IIIII', 1, len(forms), len(lemma_list), count, 0))
        out.write(struct.pack('<II', len(lemma_blob), len(form_blob)))
        out.write(struct.pack('<%dI' % len(lemma_offsets), *lemma_offsets))
        out.write(bytes(lemma_blob))
        out.write(struct.pack('<%dI' % len(form_offsets), *form_offsets))
        out.write(bytes(form_blob))
        out.write(struct.pack('<%dI' % len(first), *first))
        out.write(bytes(analyses))
    print('%d forms, %d lemmas, %d analyses' % (len(forms), len(lemma_list), count))


main()
