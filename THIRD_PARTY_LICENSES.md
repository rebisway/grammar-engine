# Third-party licenses

The code (engine, rules, tools, examples, tests) is MIT; see [LICENSE](LICENSE).

The lexicons in `grammar_engine/data/` are derived from other works and keep their original licenses. They are separate data files: MIT does not apply to them, and their licenses do not apply to the code.

| File | Source | License |
|---|---|---|
| `fr.lex` | Grammalecte / Dicollecte French lexicon v7.7 (Olivier R.), <https://grammalecte.net/> | [MPL 2.0](https://www.mozilla.org/MPL/2.0/) |
| `en.lex` | English Wiktionary, via wiktextract (Tatu Ylonen) and <https://kaikki.org/dictionary/English/> | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `es.lex` | Spanish entries of English Wiktionary, via wiktextract and <https://kaikki.org/dictionary/Spanish/> | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

Notices: `grammar_engine/data/README_lexique_fr.txt`, `README_lexicon_en.txt`, `README_lexicon_es.txt`.

- **`fr.lex`** stays under MPL 2.0. If you modify the file, publish your version under MPL 2.0. It can be used alongside code under any license. `tools/build_lexicon.py` rebuilds it from the public source.
- **`en.lex` and `es.lex`** are derived from Wiktionary: credit Wiktionary and its contributors, keep the notice, and release any adaptation under CC BY-SA 4.0. They contain only lemmas, inflected forms and grammatical features, no definition text. Rebuild them with `tools/build_lexicons.py`.
- **Redistributing the engine with these files** means carrying the notices for the lexicons you ship. To avoid share-alike data, drop the `.lex` files and provide your own (format: `docs/LEXICON.md`).

This is a summary, not legal advice; the licenses themselves prevail.
