# Writing a language

A language is one Python file with a class named `Grammar`. This tutorial builds a small Italian grammar, then shows how to add a lexicon and a tagger, how to test, how to make a variant and how to install your own languages next to the delivered ones. The calls a rule can make are listed in section 7 of [API.en.md](API.en.md).

## 1. The file and the class

Create `it.py`. The name of the file is the language code; the class is always called `Grammar`.

```python
# it.py - a small Italian grammar: two rules, no lexicon
from grammar_engine import core
from grammar_engine.core import rule

# Fixed errors: (words, replacement, not_before_capital)
PHRASES = [('perchè', 'perché', False), ('un pò', "un po'", False), ('benchè', 'benché', False)]


class Grammar(core.Grammar):
    language = 'it'
    elisions = ("l'", "un'", "dell'", "all'")          # cut off the word that follows: dell'amico = dell' + amico
    messages = {
        'en': {'it.phrase': 'Correct form: "{arg}".', 'it.conjunction': 'A comma stands before "{arg}".'},
        'fr': {'it.phrase': 'Écriture correcte : « {arg} ».', 'it.conjunction': 'Une virgule précède « {arg} ».'},
    }

    @rule('it.phrase', 'expression', 0.85)
    def phrase(self, p):
        """perchè -> perché, un pò -> un po'"""
        self.phrases(p, PHRASES, 'it.phrase')

    @rule('it.conjunction', 'punctuation', 0.7)
    def comma_before_ma(self, p):
        """a clause which starts with "ma" has a comma before it: vado ma resto -> vado, ma resto"""
        for i in range(1, len(p)):
            if p.word(i) and p.word(i - 1) and p[i].low == 'ma' and p[i].space_before:
                p.add_range('it.conjunction', p[i - 1].end, p[i].end, ', ' + p[i].text, 'ma')
```

Put the file in a folder of your own and use it:

```python
import grammar_engine
checker = grammar_engine.Checker('it', paths=['.'])            # the folder which holds it.py
text = 'Non vado perchè piove ma resto.'
[(i.rule, text[i.start:i.end], i.suggestions, i.message) for i in checker.check(text, ui='fr')]
# [('it.phrase', 'perchè', ['perché'], 'Écriture correcte : « perché ».'),
#  ('it.conjunction', ' ma', [', ma'], 'Une virgule précède « ma ».')]
```

What each part does:

| Part | Role |
|---|---|
| `language` | the code of the language (`'it'`; for a variant `'it_ch'`) |
| `elisions` | the elided forms the tokenizer cuts off, so that `dell'amico` is the two tokens `dell'` and `amico`. Leave it out when the language has none |
| `messages` | `{ui language: {rule id: text}}`. `{arg}` is replaced by the `arg` of the issue. Give English at least: it is the fallback for every other interface language |
| `@rule(id, category, confidence)` | marks a method as a rule. The identifier starts with the language code; the category is free (the delivered ones are `agreement`, `conjugation`, `spelling`, `syntax`, `punctuation`, `repetition`, `expression`); the confidence (0 to 1) is the default for the issues of the rule |
| `p` | the `Paragraph`: `p.tokens`, `p[i]`, `len(p)`, `p.word(i)` |

The base class already provides the rules of any language (`any.repeat`, `any.capital`) and the helper `phrases`.

## 2. Writing a rule

A rule is a method with one argument, the paragraph. It looks at tokens and reports with `p.add(...)`.

```python
@rule('it.example', 'spelling', 0.8)
def example(self, p):
    """what it reports, with a wrong -> correct example: this line is the description in RULES.md"""
    for i in range(1, len(p)):
        if p.word(i) and p.word(i - 1) and p[i - 1].low == 'un' and p[i].low == 'amica':
            p.add('it.example', p[i - 1], p[i - 1], 'una')
```

- `p[i].text` is the word as written, `p[i].low` its lower case with a straight apostrophe, `p[i].space_before` tells whether a space comes before it, `p[i].kind` is `'word'`, `'number'` or `'punct'`.
- Always test `p.word(i)` before reading a neighbour: the first and last tokens have no neighbour, and a neighbour can be punctuation.
- `p.add(rule_id, first, last, suggestion, arg='', confidence=None)` reports the tokens from `first` to `last` (both included) and proposes `suggestion` instead. `arg` fills `{arg}`; if you leave it out the message has no value. An empty suggestion means "delete".
- When the problem is not a whole token (a missing comma, a space), use `p.add_range(rule_id, start, end, suggestion, arg)` with a range in code points: in the example above the range is the space before `ma` and the word, and the suggestion `, ma` replaces both.
- To keep the case of the original, build the suggestion with `text.match_case(original, replacement)`.
- A rule never raises, never changes the tokens, never reads the other rules' issues.

A rule which may report another identifier lists it: `@rule('it.a', 'spelling', 0.8, emits=('it.b',))`. The messages table has an entry for each.

## 3. Fixed errors with a table

The most useful rules are tables: `PHRASES` is a list of `(words, replacement, not_before_capital)`. `words` are lower-case words separated by one space; an elision counts as its own word (`"c' est à dire"`). `not_before_capital` skips the match when a capital letter follows (useful for `a el` in Spanish, which is right before a name). One call, `self.phrases(p, PHRASES, 'xx.phrase')`, reports every match. Add an error to the table only if it is **always** wrong.

## 4. A lexicon and a tagger

A language with a lexicon (the file named in the `lexicon` attribute, for example `lexicon = 'it.lex'`) gets, on each word, every analysis the lexicon holds: `token.tags` is a tuple of `Analysis(lemma, pos, gender, number, person, verb_form, index)`.

```python
from grammar_engine import lexicon as lx
from grammar_engine import tagger as tg

def disambiguate(self, p):
    """called once per paragraph, before the rules"""
    t = p.tokens
    for i in range(1, len(t)):
        if t[i].kind == 'word' and t[i - 1].kind == 'word' and tg.only(t[i - 1], lx.DET):
            tg.keep(t[i], lx.NOUN | lx.ADJ)          # after a determiner: a noun or an adjective
```

`keep(t, mask)`, `drop(t, mask)` and `select(t, predicate)` remove the readings which the context excludes; none of them empties a word. After this step, `tg.only(t, lx.NOUN)` says that a word can only be a noun, and `tg.has(t, lx.VERB)` that it may be a verb. A rule reads those tags, and asks the lexicon for the corrected form:

```python
lex = self.core.lexicon
form = lex.inflect(analysis, gender=0, number=lx.PLURAL, person=0, verb_form=0)    # the plural of a noun
```

Look at what the tagger leaves on a text with `python tools/show_tags.py fr "Il le porte sur la table."`. How to make a lexicon: [LEXICON.md](LEXICON.md).

**The rule of thumb: when two readings are possible, stay silent.** "Les porte" is wrong, but "Il les porte" is right: the first step is to make the tagger say which `les` it is, the second to report only when every reading of the next word is a noun. The existing languages are full of such guards; read `langs/fr.py` before writing a rule of agreement.

## 5. Testing

Every rule needs cases which must be reported and cases which must not. A test with the standard library:

```python
import unittest
import grammar_engine

def rules(text):
    return [(i.rule, text[i.start:i.end], i.suggestions[0]) for i in grammar_engine.Checker('it', paths=['.']).check(text)]

class Italian(unittest.TestCase):
    def test_flagged(self):
        self.assertIn(('it.phrase', 'perchè', 'perché'), rules('Non vado perchè piove.'))

    def test_correct(self):
        self.assertEqual(rules('Non vado perché piove, ma resto.'), [])
```

Then run the engine on a long, correct text of the language (a book chapter): every issue it reports there is a false alarm to remove or tighten. The tests of the delivered languages are in `tests/`; run them with `python -m unittest discover -s tests`.

## 6. Variants

A variant of a language derives from it and holds only the difference:

```python
# langs/es_ar.py
from . import es
from ..core import rule

class Grammar(es.Grammar):
    language = 'es_ar'
    removed_rules = ()                       # identifiers of inherited rules this variant does not want
    messages = {'en': {'es_ar.voseo': 'In Argentine Spanish the verb of "vos" is: "{arg}".'}}

    @rule('es_ar.voseo', 'agreement', 0.8)
    def voseo(self, p):
        self.phrases(p, VOSEO, 'es_ar.voseo')
```

`Checker('es-AR')` loads it; the messages, the rules and the lexicon of Spanish are inherited. A variant without a file (`es-MX`) uses the language. In a folder of your own, import the parent as `from grammar_engine.langs import es`.

## 7. Installing your languages

A file `<code>.py` in a folder which you pass with `paths=[...]` (Python), `--path` (command line and server) or `bridge.configure('["folder"]')` replaces the delivered language of the same code. A host usually keeps them in its user data folder, for example `%AppData%\MyApp\grammar`. The same goes for a lexicon: a file with the same name in the folder wins over the delivered one.

## 8. Checklist

- File `<code>.py`, class `Grammar`, `language`, `messages` (English at least; fr and es if you can).
- Every rule has an identifier starting with the code, a category, a confidence and a docstring with a wrong -> correct example.
- Every identifier a rule may report is in `messages`.
- Tests with reported and correct cases; a run on a long correct text gives no issue.
- `python tools/list_rules.py` lists the rules of the delivered languages in [RULES.md](RULES.md); your own folder is not scanned, so describe your rules in your own README.
