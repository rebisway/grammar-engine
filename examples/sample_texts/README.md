# Sample texts

Texts with mistakes, to try the engine and the examples of the interface. Three languages, each in four files:

| File | Content |
| --- | --- |
| `fr_errors.md`, `en_errors.md`, `es_errors.md` | Markdown, one section per kind of mistake (agreement, verbs, homophones, tenses, prepositions...) |
| `fr_errors.txt`, `en_errors.txt`, `es_errors.txt` | The same sentences as plain text, one paragraph per line |
| `*_corrected.md`, `*_corrected.txt` | The same texts corrected, to see what the engine accepts (it reports nothing) |
| `fr.txt`, `en.txt`, `es.txt` | Three short texts with mistakes, loaded by the examples at start |

The files are written by [`../../tools/make_sample_texts.py`](../../tools/make_sample_texts.py) from one list of (wrong sentence, corrected sentence, rules which must report it) per language: change the list and run the script to change the files. `expected_rules.txt` gives, per language, the rules which the files of errors trigger. `tests/test_samples.py` checks that every one of them is triggered and that the corrected files give no problem.

Some sentences are decoys: correct sentences close to a mistake ("Je ne sais pas si tu viendras", "El agua fría", "He can go home now"). They show what the engine leaves alone.

Two French rules (`fr.participle`, `fr.infinitive`) need the spelling dictionary of the program which hosts the engine (a host can give it Hunspell). Without it, "Il a manger" is not reported; the tests give the engine a `known` function which accepts every word.

```
python -m grammar_engine --lang fr --ui en examples/sample_texts/fr_errors.txt
python -m grammar_engine --lang es examples/sample_texts/es_corrected.md
```
