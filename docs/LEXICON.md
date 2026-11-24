# The lexicon format (BNLX)

A lexicon holds every inflected form of a language with its analyses. It is made by a tool from a public source and read by `grammar_engine/lexicon.py`. One file per language: `data/fr.lex`, `data/en.lex`, `data/es.lex`.

## What an analysis is

An analysis answers "what can this written form be?": a lemma (the dictionary form), a part of speech, a gender, a number, a person and a verb form, in the vocabulary of Universal Dependencies. A form has one analysis per reading: `porte` is a noun (feminine singular, lemma `porte`) and a verb (present, 1st and 3rd person singular, lemma `porter`).

| Feature | Values |
|---|---|
| part of speech (a bit mask) | `NOUN` 1, `ADJ` 2, `VERB` 4, `AUX` 8, `DET` 16, `PRON` 32, `ADP` 64, `ADV` 128, `CCONJ` 256, `SCONJ` 512, `PROPN` 1024, `INTJ` 2048, `OTHER` 4096 |
| gender (2 bits) | 0 none, 1 masculine, 2 feminine, 3 epicene (both) |
| number (2 bits) | 0 none, 1 singular, 2 plural, 3 invariable |
| person (2 bits) | 0 none, 1, 2, 3 |
| verb form (1 byte) | 0 none, 1 present, 2 imperfect, 3 past simple, 4 future, 5 conditional, 6 subjunctive present, 7 subjunctive imperfect, 8 imperative, 9 infinitive, 10 present participle, 11 past participle |

In the English lexicon the gender field of an adjective or an adverb holds its degree: 1 comparative, 2 superlative.

## The file, byte by byte

All integers are little endian. `F` is the number of forms, `L` the number of lemmas, `A` the number of analyses.

| Offset | Size | Content |
|---|---|---|
| 0 | 4 | the characters `BNLX` |
| 4 | 4 | version, `1` |
| 8 | 4 | `F` |
| 12 | 4 | `L` |
| 16 | 4 | `A` |
| 20 | 4 | `0` (reserved) |
| 24 | 4 | size in bytes of the lemma blob |
| 28 | 4 | size in bytes of the form blob |
| 32 | 4 × (L + 1) | lemma offsets: the lemma number `i` is `blob[offset[i] : offset[i+1]]` |
| | lemma blob | the lemmas in UTF-8, one after the other |
| | 4 × (F + 1) | form offsets, same scheme |
| | form blob | the forms in UTF-8. **The forms are sorted by their UTF-8 bytes**: this is what makes the binary search possible |
| | 4 × (F + 1) | index of the first analysis of each form; the analyses of form `i` are the records `first[i]` to `first[i+1] - 1` |
| | 8 × A | the analysis records |

An analysis record is 8 bytes:

| Byte | Content |
|---|---|
| 0 to 3 | lemma number (an index in the lemma table) |
| 4 to 5 | part of speech, the bit mask above |
| 6 | features: bits 0-1 gender, bits 2-3 number, bits 4-5 person |
| 7 | verb form |

The reader checks the first four bytes and the version, then builds views on the tables (`memoryview`) without copying them. A lookup is a binary search on the form offsets, then a read of the records of the form. `Lexicon.analyses` keeps the 50,000 most recent answers.

## Reading it

```python
from grammar_engine import Checker

lex = Checker('fr').lexicon
for a in lex.analyses('porte'):
    print(lex.lemma(a), a.pos, a.gender, a.number, a.person, a.verb_form)
```

`Lexicon.inflect(model, gender, number, person, verb_form)` finds the form of the same lemma and part of speech with other features: the rules ask it for the corrected word ("the plural of this noun", "this verb in the 3rd person plural"). Among several candidates the most exact wins (the one which is neither epicene nor invariable).

## How the delivered lexicons are made

The procedure to rebuild them (one command, or step by step, with the checks) is in [BUILDING_LEXICONS.md](BUILDING_LEXICONS.md); the one-command script is `tools/build_lexicons.py`, the check is `tools/check_lexicon.py`.

| File | Source | Tool | Licence |
|---|---|---|---|
| `fr.lex` | the lexicon of Grammalecte v7.7 (`lexique-grammalecte-fr-v7.7.txt`) | `tools/build_lexicon.py lexique-grammalecte-fr-v7.7.txt data/fr.lex` | MPL 2.0 (see `data/README_lexique_fr.txt`) |
| `en.lex` | the English dictionary of Wiktionary as published by kaikki.org | `curl -s <kaikki English dump> \| python tools/build_lexicon_en.py data/en.lex` | CC BY-SA 4.0 (see `data/README_lexicon_en.txt`) |
| `es.lex` | the Spanish dictionary of Wiktionary, kaikki.org | `curl -s <kaikki Spanish dump> \| python tools/build_lexicon_es.py data/es.lex` | CC BY-SA 4.0 (see `data/README_lexicon_es.txt`) |

The source text is read as a stream and not kept. The French tool turns the tags of Grammalecte (`ipre`, `ppas`, `1sg`...) into the features above; the English and Spanish tools read the JSON lines of Wiktionary: every inflected form of every one-word entry becomes an analysis. The English and Spanish tools skip the forms and senses tagged `obsolete`, `archaic`, `nonstandard`, `rare`, `misspelling` or `proscribed`, so the lexicon does not accept what a checker should flag.

## Adding a language

1. Find a source with the inflected forms (a Wiktionary dump, a Hunspell dictionary with affix expansion, a morphological dictionary).
2. Write a build tool on the model of `tools/build_lexicon_es.py`: read the source, fill a dictionary `form -> set of (lemma, part of speech, gender, number, person, verb form)`, sort the forms by their UTF-8 bytes, and write the file as described above.
3. Put the file in `grammar_engine/data/` (or in a folder passed with `paths`) and name it in the `lexicon` attribute of the `Grammar` class of the language.
4. Check it with `python tools/show_tags.py <code> "a sentence"`, which prints the readings left on each word.
5. Keep the licence of the source and write a `README_*.txt` next to the file.
