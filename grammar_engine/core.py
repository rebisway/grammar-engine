# grammar-engine - the core: tokens in, issues out.
#
# The engine knows nothing about a language. A language is one file (langs/fr.py) with a class named Grammar, which
# derives from grammar_engine.core.Grammar and holds the rules, as methods marked with @rule. The core cuts the
# paragraph into tokens, calls every rule of the language and collects what they report. A rule works on tokens and
# the lexicon, never on the raw text, and reports with p.add().
#
#   class Grammar(core.Grammar):
#       language = 'fr'
#       elisions = ("l'", "qu'")
#       lexicon = 'fr.lex'
#       messages = {'en': {'fr.a': '...'}, 'fr': {...}}
#
#       @rule('fr.a', 'spelling', 0.9)
#       def a_verb(self, p):
#           for i in range(1, len(p)):
#               ...
#               p.add('fr.a', p[i], p[i], 'a')
#
# SPDX-License-Identifier: MIT

import importlib
import importlib.util
import os

from . import lexicon as lx
from . import tagger
from .text import match_case, tokenize

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
LANGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'langs')


def rule(rule_id, category, confidence, emits=()):
    """Marks a method of Grammar as a rule. `emits` lists the other identifiers the method may report."""
    def mark(fn):
        fn.rule_info = (rule_id, category, confidence, tuple(emits))
        return fn
    return mark


class Issue:
    """A problem found in a paragraph: the rule, its category, the range in code points, the text of the problem, the suggestions and the message."""
    __slots__ = ('rule', 'category', 'start', 'end', 'arg', 'suggestions', 'confidence', 'message')

    def __init__(self, rule_id, category, start, end, arg, suggestions, confidence):
        """The message is filled in later, by Checker.check, in the language of the interface."""
        self.rule, self.category, self.start, self.end = rule_id, category, start, end
        self.arg, self.suggestions, self.confidence = arg, suggestions, confidence
        self.message = ''

    def as_dict(self):
        """The issue as a dictionary of its fields."""
        return {s: getattr(self, s) for s in self.__slots__}


class Paragraph:
    """The tokens of one paragraph, with the helpers a rule needs and the place where it reports."""

    def __init__(self, text, tokens, grammar):
        """text: the paragraph; tokens: its tokens; grammar: the Grammar which reports the issues."""
        self.text = text
        self.tokens = tokens
        self._grammar = grammar
        self.issues = []

    def __len__(self):
        """The number of tokens."""
        return len(self.tokens)

    def __getitem__(self, i):
        """The token i."""
        return self.tokens[i]

    def word(self, i):
        """True when token i exists and is a word."""
        return 0 <= i < len(self.tokens) and self.tokens[i].kind == 'word'

    def add(self, rule_id, first, last, suggestion, arg='', confidence=None):
        """Reports a problem on the tokens first..last (included); the suggestion replaces them."""
        self.add_range(rule_id, first.start, last.end, suggestion, arg, confidence)

    def add_range(self, rule_id, start, end, suggestion, arg='', confidence=None):
        """Reports a problem on a range of the text (code points); the suggestion replaces it, "" deletes it."""
        category, default = self._grammar.rule_meta(rule_id)
        self.issues.append(Issue(rule_id, category, start, end, arg, [suggestion], default if confidence is None else confidence))


class Grammar:
    """Base of the languages. It holds the rules which work in any language."""
    language = 'any'
    elisions = ()
    lexicon = None                      # name of the lexicon file, in the data folder
    messages = {}                       # {'ui language': {'rule id': 'text with {arg}'}}
    removed_rules = ()                  # identifiers of inherited rules which this variant of a language does not have

    ANY_MESSAGES = {
        'en': {'any.repeat': 'Repeated word: "{arg}".', 'any.capital': 'A sentence starts with a capital letter.'},
        'fr': {'any.repeat': 'Mot répété : « {arg} ».', 'any.capital': 'Une phrase commence par une majuscule.'},
        'es': {'any.repeat': 'Palabra repetida: «{arg}».', 'any.capital': 'Una frase empieza con mayúscula.'},
    }

    def __init__(self):
        """Collects the rules: the methods marked with @rule, including the inherited ones, except those listed in removed_rules."""
        self.core = None
        self._rules = []                # (method, id, category, confidence, emits)
        self._meta = {}                 # id -> (category, confidence)
        for name in dir(type(self)):
            fn = getattr(self, name)
            info = getattr(fn, 'rule_info', None)
            if info and info[0] not in self.removed_rules:
                rid, cat, conf, emits = info
                self._rules.append((fn, rid, cat, conf, emits))
                self._meta[rid] = (cat, conf)
                for e in emits:
                    self._meta.setdefault(e, (cat, conf))

    def set_core(self, core):
        """Gives the grammar the Checker which uses it (for the lexicon and the spelling dictionary)."""
        self.core = core

    def rule_meta(self, rule_id):
        """(category, default confidence) of a rule identifier."""
        return self._meta.get(rule_id, ('other', 0.5))

    def rules(self):
        """The rules of the language as dictionaries: id, category, confidence, language."""
        return [{'id': rid, 'category': cat, 'confidence': conf, 'language': rid.split('.')[0]} for _, rid, cat, conf, _ in self._rules]

    def message(self, ui, rule_id):
        # The messages of the language, then those of the languages it derives from
        """The message of a rule in the ui language; the messages of the language it derives from, then English, are the fallback."""
        tables = [c.__dict__['messages'] for c in type(self).__mro__ if 'messages' in c.__dict__] + [self.ANY_MESSAGES]
        for table in tables:
            for code in (ui, 'en'):
                text = table.get(code, {}).get(rule_id)
                if text:
                    return text
        return rule_id

    def disambiguate(self, p):
        """Chooses the reading of each word from its neighbours (tagger.py); a language overrides it with its constraints."""

    def check(self, p, ignored):
        """Calls every rule on the paragraph, except those which are switched off with all their identifiers."""
        for fn, rid, _, _, emits in self._rules:
            if rid in ignored and all(e in ignored for e in emits):
                continue
            fn(p)

    # [SECTION] Rules of any language

    @rule('any.repeat', 'repetition', 0.85)
    def repeat(self, p):
        """a word written twice: the the -> the"""
        allowed = {'nous', 'vous', 'bien', 'pas', 'non', 'si', 'tout', 'très', 'had', 'that', 'ha', 'no', 'bye', 'so', 'very', 'yo', 'knock', 'blah'}
        for i in range(1, len(p)):
            a, b = p[i - 1], p[i]
            if p.word(i) and p.word(i - 1) and b.space_before and a.text == b.text and len(b.low) >= 2 and b.low not in allowed:
                p.add_range('any.repeat', a.end, b.end, '', b.text)

    @rule('any.capital', 'punctuation', 0.7)
    def capital(self, p):
        """a sentence which starts with a lower-case letter: it is late. she came -> She"""
        abbreviations = {'etc', 'cf', 'vs', 'mme', 'mlle', 'dr', 'st', 'ste', 'av', 'apr', 'env', 'ex', 'fig', 'mr', 'mrs', 'ms', 'no', 'ibid', 'approx', 'vol', 'ch', 'chap', 'min', 'max'}
        interjections = {'alas', 'oh', 'ah', 'hurrah', 'hush', 'hey', 'well', 'hélas'}
        ends = ('.', '!', '?')
        t = p.tokens
        for i in range(1, len(t) - 1):
            mark = t[i]
            if mark.kind != 'punct' or mark.text not in ends or not p.word(i + 1) or not t[i + 1].space_before or mark.space_before:
                continue
            before = t[i - 1]
            if before.kind == 'word' and mark.text == '.' and len(before.text) <= 4 and before.text[0].isupper():
                continue                # "Abm.", "Dr.", "St.": abbreviations
            if before.kind == 'number' or (before.kind == 'word' and (len(before.low) < 2 or (mark.text == '.' and before.low in abbreviations))):
                continue
            if before.kind == 'punct' and before.text not in ('…', ')', '"'):
                continue
            # An exclamation or a question which is one word, or starts with an interjection, does not end the sentence:
            # "Thump! thump! down she came", "alas for poor Alice! when she got there"
            if mark.text != '.':
                start = i
                while start > 0 and not (t[start - 1].kind == 'punct' and t[start - 1].text in ends):
                    start -= 1
                interjection = any(p.word(k) and t[k].low in interjections for k in range(max(start, i - 8 if i > 8 else 0), i))
                if i - start == 1 or interjection or (p.word(i - 1) and t[i - 1].low == t[i + 1].low):
                    continue
            w = t[i + 1]
            if w.text[0].islower():
                p.add('any.capital', w, w, match_case('A', w.text))

    # [SECTION] Helpers for the rules of the languages

    coordinators = ()                   # words which join two subjects: "and" (en), "et" (fr), "y" (es)

    def compound_subject(self, p, i):
        """True when the token i follows a coordinator which joins it to a subject without a verb of its own
        ("he and I are", "Paul et elle sont"): the verb then agrees with both, and a rule which checks a verb against
        the single pronoun at i must stay silent. A verb before the coordinator ("I came and he go") means a new clause."""
        if i < 2 or not p.word(i - 1) or p[i - 1].low not in self.coordinators:
            return False
        for j in range(i - 2, max(i - 8, -1), -1):
            t = p[j]
            if t.kind == 'punct':
                break
            if t.kind == 'word' and t.tags and tagger.only(t, lx.VERB | lx.AUX):
                return False
        return True

    def phrases(self, p, table, rule_id):
        """Fixed expressions which are always wrong: table of (words, replacement, not_before_capital)."""
        t = p.tokens
        for words, replacement, not_before_capital in table:
            words = words.split(' ')
            for i in range(len(t) - len(words) + 1):
                if not all(t[i + k].kind == 'word' and t[i + k].low == words[k] for k in range(len(words))):
                    continue
                nxt = i + len(words)
                if not_before_capital and nxt < len(t) and t[nxt].text[0].isupper():
                    continue
                r = match_case(t[i].text, replacement)
                p.add(rule_id, t[i], t[i + len(words) - 1], r, r, 0.85)


class Checker:
    """Checks the paragraphs of a text in one language.

    language: 'fr', 'fr-FR', 'en'... (the first two letters)
    known:    function(word) -> bool, the spelling dictionary; the rules which need it are silent without it
    ignored:  identifiers of the rules which are switched off
    paths:    folders searched first for a language file (<code>.py) and a lexicon: your own languages
    """

    def __init__(self, language='en', known=None, ignored=(), paths=()):
        """Loads the grammar of the language and its lexicon (shared between the checkers of the same file)."""
        self.paths = [os.path.abspath(p) for p in paths]
        self.known = known
        self.ignored = set(ignored)
        self.lexicon = None
        self.grammar = Grammar()
        self.set_language(language)

    def set_language(self, language):
        # "es-AR" or "es_AR": the variant if there is a file for it (langs/es_ar.py, which derives from es.Grammar), else the language
        """Chooses the language: a variant ("es-AR") if there is a file for it, else the language, else the base grammar."""
        full = (language or 'en').replace('-', '_').lower()
        code = full[:2]
        self.language = full
        cls = self._load_language(full) if full != code else None
        cls = cls or self._load_language(code) or Grammar
        self.grammar = cls()
        self.grammar.set_core(self)
        self.lexicon = None
        if self.grammar.lexicon:
            path = self._find_file(self.grammar.lexicon)
            if path:
                self.lexicon = _lexicon_cache(path)

    def _find_file(self, name):
        """The path of a data file: the user folders first, then the delivered data folder."""
        for d in self.paths + [DATA_DIR]:
            f = os.path.join(d, name)
            if os.path.isfile(f):
                return f
        return None

    def _load_language(self, code):
        """The Grammar class of a language file, searched in the user folders first, then in langs/. None if there is none."""
        for d in self.paths:
            f = os.path.join(d, code + '.py')
            if os.path.isfile(f):
                spec = importlib.util.spec_from_file_location('grammar_engine_user_' + code, f)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.Grammar
        if os.path.isfile(os.path.join(LANGS_DIR, code + '.py')):
            return importlib.import_module('grammar_engine.langs.' + code).Grammar
        return None

    def rules(self):
        """The rules of the language: id, category, confidence."""
        return self.grammar.rules()

    def check(self, text, ui='en'):
        """Issues of one paragraph, sorted by position; messages in the ui language. Ranges are in code points."""
        if not text.strip(' \t'):
            return []
        g = self.grammar
        p = Paragraph(text, tokenize(text, g.elisions), g)
        if self.lexicon:
            tagger.assign(p, self.lexicon)
            g.disambiguate(p)
        g.check(p, self.ignored)
        issues = [i for i in p.issues if i.rule not in self.ignored]
        issues.sort(key=lambda i: i.start)
        clean = []
        for i in issues:               # one issue for a stretch of text: the first one wins
            if not clean or i.start >= clean[-1].end:
                clean.append(i)
        for i in clean:
            i.message = g.message(ui, i.rule).replace('{arg}', i.arg)
        return clean


_lexicons = {}


def _lexicon_cache(path):
    """The lexicon of a file, loaded once for the whole process."""
    if path not in _lexicons:
        _lexicons[path] = lx.Lexicon(path)
    return _lexicons[path]
