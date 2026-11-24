# Building the lexicons

The lexicons (`grammar_engine/data/fr.lex`, `en.lex`, `es.lex`) are made from public dictionaries by the scripts of `tools/`. The files are delivered with the engine; this page is for rebuilding them: a newer source, a fix in a build tool, a new language. The format of the files is in [LEXICON.md](LEXICON.md).

| Lexicon | Source | Download | License of the source | Build tool | Result |
| --- | --- | --- | --- | --- | --- |
| `fr.lex` | the French inflected forms of Grammalecte (Dicollecte), v7.7 | a zip of a few MB | MPL 2.0 | `tools/build_lexicon.py` | 14.8 MB, 476 104 forms |
| `en.lex` | the English dictionary of Wiktionary, extracted by kaikki.org | one file of JSON lines, 3.4 GB | CC BY-SA 4.0 | `tools/build_lexicon_en.py` | 29.6 MB, 806 123 forms |
| `es.lex` | the Spanish dictionary of Wiktionary, extracted by kaikki.org | one file of JSON lines, 1.1 GB | CC BY-SA 4.0 | `tools/build_lexicon_es.py` | 23.0 MB, 758 215 forms |

The sources are not kept in the repository: they are large and have their own licenses. A build reads the source, keeps one analysis (lemma, part of speech, gender, number, person, verb form) per reading of every form, and writes the compact file.

## What you need

- Python 3.9 or later. Nothing else: the scripts use the standard library only.
- A connection, for the first build. The English and the Spanish sources are read **as a stream** (the 3.4 GB and 1.1 GB are never written to the disk, unless you ask to keep them), so the disk space needed is the size of the result. The French zip is a few MB.
- Memory: a build keeps all the forms of the language in memory before it writes them. English is the largest (not measured exactly: close the other programs).
- Time: minutes, mostly the download.

## In one command

From the `grammar-engine` folder:

```
python tools/build_lexicons.py fr
python tools/build_lexicons.py en es
python tools/build_lexicons.py all
```

For each language the script gets the source, runs the build tool, writes the result under a temporary name, checks it (`tools/check_lexicon.py --spot`) and only then replaces the old file. A build which fails, or a lexicon which does not pass the check, leaves the delivered file as it was.

| Option | Use |
| --- | --- |
| `--source FILE` | a source you already have instead of the download (one language at a time): the text file or the zip for French, the JSON lines file (`.jsonl`, or `.jsonl.gz`) for English and Spanish |
| `--keep-source FOLDER` | also keep a copy of what is downloaded (English, Spanish), to build again without downloading |
| `--out FOLDER` | write the `.lex` files elsewhere; the default is `grammar_engine/data` |
| `--sample` | the source is a partial test file: load the result but do not compare it with well-known words |
| `--no-check` | skip the check |

To work offline, download the sources once (section below), then `python tools/build_lexicons.py en --source kaikki.org-dictionary-English.jsonl`.

## By hand, step by step

### French

1. Download the zip (it holds a text file with one line per inflected form):

   ```
   curl -L -o lexique-grammalecte-fr-v7.7.zip https://grammalecte.net/dic/lexique-grammalecte-fr-v7.7.zip
   ```
   PowerShell: `Invoke-WebRequest https://grammalecte.net/dic/lexique-grammalecte-fr-v7.7.zip -OutFile lexique-grammalecte-fr-v7.7.zip`
2. Unzip it: `unzip lexique-grammalecte-fr-v7.7.zip` (PowerShell: `Expand-Archive lexique-grammalecte-fr-v7.7.zip .`). You get `lexique-grammalecte-fr-v7.7.txt`.
3. Build:

   ```
   python tools/build_lexicon.py lexique-grammalecte-fr-v7.7.txt grammar_engine/data/fr.lex
   ```
   The text file has tab-separated columns: id, id of the group of forms, the form, the lemma, the tags (`nom mas sg`, `v1 ipre 1sg`, ...). The tool turns the tags into the features of the lexicon (`analyze()` in the script: `nom` is a noun, `v0` an auxiliary, `v1`-`v3` a verb, `mas`/`fem`/`epi`, `sg`/`pl`/`inv`, the persons `1sg`...`3pl`, and the verb forms `ipre`, `iimp`, `ipsi`, `ifut`, `cond`, `spre`, `simp`, `impe`, `infi`, `ppre`, `ppas`).
4. Check (section below). Keep `data/README_lexique_fr.txt` beside the file: it is the notice of the lexicon (MPL 2.0).

### English and Spanish

1. Choose where the source comes from. The files are published at

   - `https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl`
   - `https://kaikki.org/dictionary/Spanish/kaikki.org-dictionary-Spanish.jsonl`

   Either read them as a stream, with no copy on the disk:

   ```
   curl -s -L https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl | python tools/build_lexicon_en.py grammar_engine/data/en.lex
   curl -s -L https://kaikki.org/dictionary/Spanish/kaikki.org-dictionary-Spanish.jsonl | python tools/build_lexicon_es.py grammar_engine/data/es.lex
   ```
   (Windows PowerShell 5 does not pipe bytes unchanged: use `cmd /c "curl -s -L URL | python tools\build_lexicon_en.py grammar_engine\data\en.lex"`, or the one-command script.)

   or keep the file and read it from the disk:

   ```
   curl -L -o english.jsonl https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl
   python tools/build_lexicon_en.py grammar_engine/data/en.lex < english.jsonl
   ```
2. The tool prints a line every 200 000 entries on the standard error, then `N forms, N lemmas, N analyses`.
3. Check (next section). Keep `data/README_lexicon_en.txt` and `README_lexicon_es.txt`: the lexicons are derived works of Wiktionary and are shared under CC BY-SA 4.0 with the same notice.

What the tools keep, in short. **English**: every one-word entry with its part of speech, its plural (nouns), third person, past, past participle and present participle (verbs), comparative and superlative (adjectives and adverbs); inflected-form entries and spelling variants are skipped (the entry of the lemma lists the forms), and so are the forms marked obsolete, archaic, dialectal or wrong. **Spanish**: the inflected forms are entries of their own in the source (`form_of` a lemma, with tags for person, number, mood, tense, gender): they give most of the analyses, and the entries of the lemmas give the base forms, the plurals, the feminines and the superlatives. The details and the exact mapping of the tags are in the scripts and in [LEXICON.md](LEXICON.md).

## Checking a lexicon

```
python tools/check_lexicon.py grammar_engine/data/fr.lex --lang fr --spot
```

It loads the file, prints its size (`fr.lex: 14.8 MB, 476104 forms, 84686 lemmas, 591636 analyses`), and with `--spot` looks up a few well-known words (`chats` is a plural noun of `chat`, `went` is a past of `go`, `hablamos` a plural form of `hablar`...). The exit code is 0 when everything passes. Then run the whole test suite and look at the alerts on the sample texts, because a new lexicon can change what the rules report:

```
python -m unittest discover -s tests
python -m grammar_engine --lang fr --ui en examples/sample_texts/fr_corrected.txt     # must print []
```

## Using a newer source

- **French**: change the version in the file name and the URL (`lexique-grammalecte-fr-vX.Y.zip`, see <https://grammalecte.net/>), and the notice `data/README_lexique_fr.txt`.
- **English, Spanish**: kaikki.org publishes new extractions regularly; the address is the same. A new extraction can change the shape of the JSON (fields `lang_code`, `pos`, `forms`, `senses`, `form_of`, `tags`): if the build fails or the counts fall, compare a few lines of the new file with what the tool reads (`head -n 3 file.jsonl`).
- Compare the counts with the previous file (forms, lemmas, analyses: a drop of more than a few percent means something changed in the source), pass the check, run the tests, and look at the alerts on the reference texts before delivering the new file.

## When something goes wrong

| Message | Cause |
| --- | --- |
| `HTTP Error 404` or a download which stops at once | the address changed; open the page of the source in a browser and take the new link |
| `json.decoder.JSONDecodeError` in the middle of a build | the download was cut (a truncated last line); start again, or use `--keep-source` and check the size of the file |
| `The build tool failed` | read the lines printed just before: the tool's own error |
| `The check failed` | the file loads but a well-known word is missing: the source changed, or the tool was edited; the previous lexicon is unchanged |
| `MemoryError` | not enough memory for the language; close other programs, or build on a larger machine |

## Licenses

A lexicon built from a source carries its license: keep the notice file beside it (`data/README_lexique_fr.txt`, `README_lexicon_en.txt`, `README_lexicon_es.txt`), mention the source in what you distribute (the program's About box and README), and for the English and Spanish files share your changes under CC BY-SA 4.0. The code of the engine and of the build tools is MIT, which does not change the license of the data.

## A new language

Write a build tool on the model of `tools/build_lexicon_es.py` (read the source, fill `form -> set of analyses`, sort, write), add its source to `SOURCES` in `tools/build_lexicons.py` and its well-known words to `SPOT` in `tools/check_lexicon.py`, then write the language file as described in [WRITING_A_LANGUAGE.md](WRITING_A_LANGUAGE.md).
