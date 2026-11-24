# grammar-engine - Spanish
#
# Index of this file:
#   [SECTION] Tagger                          two passes of constraints
#   [SECTION] Rules without lexicon           inverted marks, fixed errors
#   [SECTION] Rules with the lexicon          determiner and noun, noun and adjective, subject and verb, participle after haber, tilde
#   [SECTION] Accents, interrogatives, dequeísmo, impersonal "haber", noun subject, subjunctive
# Messages are in English, French and Spanish: the table at the start of the class, then MORE_MESSAGES at the end of the file.
# SPDX-License-Identifier: MIT

from .. import core, lexicon as lx
from .. import tagger as tg
from ..core import rule
from ..text import match_case

# Fixed errors: (words, replacement, not_before_capital), see Grammar.phrases
PHRASES = [
    ('a el', 'al', True), ('de el', 'del', True), ('haber si', 'a ver si', False), ('a sido', 'ha sido', False), ('mas o menos', 'más o menos', False),
    ('a cerca de', 'acerca de', False), ('en base a', 'con base en', False), ('de acuerdo a', 'de acuerdo con', False), ('a parte', 'aparte', False),
    ('tambien', 'también', False), ('ademas', 'además', False), ('despues', 'después', False), ('alli', 'allí', False), ('aqui', 'aquí', False), ('asi', 'así', False),
    ('quizas', 'quizás', False), ('facil', 'fácil', False), ('dificil', 'difícil', False), ('rapido', 'rápido', False), ('cafe', 'café', False), ('sabado', 'sábado', False),
    ('miercoles', 'miércoles', False), ('ahi', 'ahí', False), ('habia', 'había', False), ('ojala', 'ojalá', False), ('exelente', 'excelente', False),
    ('mas tarde', 'más tarde', False), ('no mas', 'no más', False), ('mas bien', 'más bien', False), ('a mi me', 'a mí me', False),
    ('aveces', 'a veces', False), ('porfavor', 'por favor', False), ('enserio', 'en serio', False), ('osea', 'o sea', False), ('atravez', 'a través', False),
    ('a pesar que', 'a pesar de que', False), ('me di cuenta que', 'me di cuenta de que', False), ('se dio cuenta que', 'se dio cuenta de que', False),
    ('me doy cuenta que', 'me doy cuenta de que', False), ('nos dimos cuenta que', 'nos dimos cuenta de que', False), ('te diste cuenta que', 'te diste cuenta de que', False),
    ('estoy seguro que', 'estoy seguro de que', False), ('estoy segura que', 'estoy segura de que', False), ('en caso que', 'en caso de que', False),
    ('me alegro que', 'me alegro de que', False), ('me acuerdo que', 'me acuerdo de que', False), ('al menos que', 'a menos que', False), ('debido que', 'debido a que', False),
    ('tubo que', 'tuvo que', False), ('él tubo', 'él tuvo', False), ('ella tubo', 'ella tuvo', False), ('que valla', 'que vaya', False), ('ojalá valla', 'ojalá vaya', False),
]

# The determiners, by family: masculine singular, feminine singular, masculine plural, feminine plural
# The determiners, by family: masculine singular, feminine singular, masculine plural, feminine plural
FAMILIES = [('el', 'la', 'los', 'las'), ('un', 'una', 'unos', 'unas'), ('este', 'esta', 'estos', 'estas'), ('ese', 'esa', 'esos', 'esas'),
            ('aquel', 'aquella', 'aquellos', 'aquellas'), ('nuestro', 'nuestra', 'nuestros', 'nuestras'), ('vuestro', 'vuestra', 'vuestros', 'vuestras'),
            ('algún', 'alguna', 'algunos', 'algunas'), ('ningún', 'ninguna', 'ningunos', 'ningunas')]
DETERMINERS = {}                        # word -> (family index, gender, number)
for _i, _f in enumerate(FAMILIES):
    for _word, _gender, _number in zip(_f, (1, 2, 1, 2), (1, 1, 2, 2)):
        DETERMINERS[_word] = (_i, _gender, _number)
# Possessives which agree in number only (mi, tu, su, cada)
INVARIABLE_GENDER = {'mi': 1, 'mis': 2, 'tu': 1, 'tus': 2, 'su': 1, 'sus': 2, 'cada': 1}      # number only
# Subject pronoun -> (person, number)
SUBJECTS = {'yo': (1, 1), 'tú': (2, 1), 'él': (3, 1), 'ella': (3, 1), 'usted': (3, 1), 'nosotros': (1, 2), 'nosotras': (1, 2),
            'vosotros': (2, 2), 'vosotras': (2, 2), 'ellos': (3, 2), 'ellas': (3, 2), 'ustedes': (3, 2)}
# Object pronouns which stand between a subject and its verb
CLITICS = {'me', 'te', 'se', 'nos', 'os', 'lo', 'la', 'le', 'los', 'las', 'les', 'no'}
# Words after which a new clause starts
STARTERS = {'y', 'e', 'o', 'u', 'pero', 'que', 'si', 'cuando', 'porque', 'aunque', 'como', 'ni', 'mientras', 'donde', 'sino'}
# Forms of haber: auxiliary of the compound tenses
HABER = {'he', 'has', 'ha', 'hemos', 'habéis', 'han', 'había', 'habías', 'habíamos', 'habíais', 'habían', 'hube', 'habré', 'habrás', 'habrá', 'habremos', 'habrán', 'habría', 'habrías',
         'habríamos', 'habrían', 'haya', 'hayas', 'hayamos', 'hayan', 'hubiera', 'hubiese', 'hubieran', 'habiendo'}
# Prepositions: after one the word is a noun, an infinitive or a gerund
PREPOSITIONS = {'de', 'en', 'con', 'por', 'para', 'sin', 'sobre', 'desde', 'hasta', 'entre', 'hacia', 'según', 'ante', 'bajo', 'tras', 'contra', 'durante'}
# Determiners which are also pronouns
PRONOUN_DETERMINERS = {'el', 'tu', 'te', 'se', 'me', 'nos', 'os'}      # also pronouns: "tu eres", "el canta"
# Coordinators: adjectives joined by one may differ in gender and number
COORDINATORS = {'y', 'e', 'o', 'u', 'ni', ','}


class Grammar(core.Grammar):
    """Spanish: agreement of determiner, noun, adjective and verb, participle after haber, accents, dequeísmo, subjunctive."""
    language = 'es'
    lexicon = 'es.lex'
    coordinators = ('y', 'e', 'o', 'u', 'ni')

    messages = {
        'en': {
            'es.inverted': 'The opening mark "{arg}" is missing at the start of the sentence.',
            'es.phrase': 'Correct form: "{arg}".',
            'es.det_number': 'The determiner and the noun do not agree in number: "{arg}".',
            'es.det_gender': 'The determiner does not agree in gender with the noun: "{arg}".',
            'es.noun_adjective': 'The adjective agrees in gender and number with the noun: "{arg}".',
            'es.subject_verb': 'The verb agrees with its subject: "{arg}".',
            'es.haber_participle': 'After "haber" the participle does not change: "{arg}".',
            'es.tilde': 'The pronoun is written with an accent: "{arg}".',
        },
        'fr': {
            'es.inverted': "Le signe d'ouverture « {arg} » manque au début de la phrase.",
            'es.phrase': 'Écriture correcte : « {arg} ».',
            'es.det_number': "Le déterminant et le nom ne s'accordent pas en nombre : « {arg} ».",
            'es.det_gender': "Le déterminant ne s'accorde pas en genre avec le nom : « {arg} ».",
            'es.noun_adjective': "L'adjectif s'accorde en genre et en nombre avec le nom : « {arg} ».",
            'es.subject_verb': "Le verbe s'accorde avec son sujet : « {arg} ».",
            'es.haber_participle': 'Après « haber », le participe est invariable : « {arg} ».',
            'es.tilde': 'Le pronom s\'écrit avec un accent : « {arg} ».',
        },
        'es': {
            'es.inverted': 'Falta el signo de apertura «{arg}» al principio de la oración.',
            'es.phrase': 'Forma correcta: «{arg}».',
            'es.det_number': 'El determinante y el nombre no concuerdan en número: "{arg}".',
            'es.det_gender': 'El determinante no concuerda en género con el nombre: "{arg}".',
            'es.noun_adjective': 'El adjetivo concuerda en género y número con el nombre: "{arg}".',
            'es.subject_verb': 'El verbo concuerda con su sujeto: "{arg}".',
            'es.haber_participle': 'Después de "haber" el participio no varía: "{arg}".',
            'es.tilde': 'El pronombre lleva tilde: "{arg}".',
        },
    }

    # [SECTION] Tagger

    def disambiguate(self, p):
        """Two passes, so that "los" sees the word after it already read."""
        for _ in range(2):              # the second pass lets "los" see the word after it already read
            self.disambiguate_once(p)

    def disambiguate_once(self, p):
        """Tagger constraints: after a determiner a noun or an adjective, after a subject pronoun a verb, after haber a participle."""
        t = p.tokens
        for i, w in enumerate(t):
            if w.kind != 'word' or len(w.tags) < 2:
                continue
            if w.low in ('la', 'las', 'lo', 'los'):
                nxt = t[i + 1] if i + 1 < len(t) else None
                if nxt is not None and nxt.kind == 'word' and nxt.tags and tg.has(nxt, lx.NOUN | lx.ADJ) and not tg.has(nxt, lx.VERB | lx.AUX):
                    tg.keep(w, lx.DET)
                continue
            if i == 0 or t[i - 1].kind != 'word':
                continue
            before = t[i - 1].low
            if before in DETERMINERS or before in INVARIABLE_GENDER or before in ('el', 'la', 'las', 'los'):
                if tg.only(t[i - 1], lx.DET) or before in DETERMINERS or before in INVARIABLE_GENDER:
                    tg.keep(w, lx.NOUN | lx.ADJ | lx.PROPN)
            elif before in SUBJECTS:
                tg.select(w, lambda a: bool(a.pos & (lx.VERB | lx.AUX)) and a.verb_form in tg.FINITE)
            elif before in HABER:
                tg.select(w, lambda a: bool(a.pos & lx.VERB) and a.verb_form == lx.PAST_PARTICIPLE)
            elif before in PREPOSITIONS:
                tg.select(w, lambda a: not (a.pos & (lx.VERB | lx.AUX)) or a.verb_form in (lx.INFINITIVE, lx.PRESENT_PARTICIPLE))

    # [SECTION] Rules without lexicon

    @rule('es.inverted', 'punctuation', 0.85)
    def inverted(self, p):
        """A question or an exclamation which does not open with its inverted mark"""
        start, opened = 0, False
        for i, t in enumerate(p.tokens):
            if t.kind != 'punct':
                continue
            if t.text in ('¿', '¡'):
                opened = True
            elif t.text in ('?', '!'):
                if not opened and i > start and p.word(start):
                    mark = '¿' if t.text == '?' else '¡'
                    p.add('es.inverted', p[start], p[start], mark + p[start].text, mark)
                start, opened = i + 1, False
            elif t.text == '.':
                start, opened = i + 1, False

    @rule('es.phrase', 'expression', 0.85)
    def phrase(self, p):
        """fixed errors of the table PHRASES: a el -> al"""
        self.phrases(p, PHRASES, 'es.phrase')

    # [SECTION] Rules with the lexicon

    @staticmethod
    def det_disagrees(det, number):
        """The determiner and the noun differ in number."""
        if det in DETERMINERS:
            return DETERMINERS[det][2] != number
        if det in INVARIABLE_GENDER:
            return (1 if INVARIABLE_GENDER[det] == 1 else 2) != number
        return False

    def noun_features(self, tok, det=None, before_det=None, after=None):
        """(is_noun_only, gender, number) of a word read as a noun: 0 where the readings differ.
        A word which is also a verb form ("casa", "pinta", "eres") counts as a noun only when the context says so: a verb follows it
        ("las casa son bonitas") and the determiner before it is not also a pronoun, unless nothing but the start of the sentence or a
        preposition stands before that determiner ("los pinta con cuidado" is a verb, "para las casa son" is not tested)."""
        readings = [a for a in tok.tags if a.pos & lx.NOUN]
        if not readings or any(a.pos & ~(lx.NOUN | lx.ADJ | lx.PROPN) for a in tok.tags) or not tg.has(tok, lx.NOUN):
            return False, 0, 0
        lex = self.core.lexicon
        if any(a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE for a in lex.analyses(tok.text)):
            verb_follows = after is not None and after.kind == 'word' and any(a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE for a in after.tags)
            if det is not None and det.low in PRONOUN_DETERMINERS:
                return False, 0, 0
            if det is not None and det.low in ('la', 'las', 'lo', 'los'):
                adjective_follows = after is not None and after.kind == 'word' and tg.has(after, lx.ADJ) and not tg.has(after, lx.VERB | lx.AUX)
                if not (verb_follows or adjective_follows) or (before_det is not None and before_det.kind == 'word' and before_det.low not in PREPOSITIONS | STARTERS):
                    return False, 0, 0      # "los pinta con cuidado", "ella las casa": the determiner is a pronoun
        genders, numbers = {a.gender for a in readings}, {a.number for a in readings}
        return True, (genders.pop() if len(genders) == 1 else 0), (numbers.pop() if len(numbers) == 1 else 0)

    @rule('es.det_number', 'agreement', 0.75, emits=('es.det_gender',))
    def determiner(self, p):
        """los casa -> casas, la libros -> los libros"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)) or not t[i + 1].space_before or t[i + 1].text[0].isupper():
                continue
            det = t[i].low
            if det in DETERMINERS:
                family, dgender, dnumber = DETERMINERS[det]
            elif det in INVARIABLE_GENDER:
                family, dgender, dnumber = -1, 0, 1 if INVARIABLE_GENDER[det] == 1 else 2
            else:
                continue
            noun = t[i + 1]
            if not tg.only(t[i], lx.DET) and not (t[i].tags and tg.has(t[i], lx.DET) and det not in ('la', 'las', 'lo', 'los', 'el')):
                if t[i].tags and not tg.has(t[i], lx.DET):
                    continue
            if det in ('la', 'las', 'los') and not tg.only(t[i], lx.DET):
                continue                # a pronoun: "la vi"
            after = t[i + 2] if i + 2 < len(t) else None
            ok, gender, number = self.noun_features(noun, t[i], t[i - 1] if i > 0 else None, after)
            if not ok or number not in (lx.SINGULAR, lx.PLURAL):
                continue
            if after is not None and after.kind == 'word' and tg.has(after, lx.NOUN) and not tg.has(after, lx.VERB | lx.AUX | lx.ADJ):
                continue                # the noun is a modifier of the next word
            if number != dnumber:
                reading = next(a for a in noun.tags if a.pos & lx.NOUN)
                form = lex.inflect(reading, 0, dnumber, 0, 0)
                if form and form != noun.low:
                    p.add('es.det_number', noun, noun, match_case(noun.text, form), form)
                continue
            if family >= 0 and gender in (lx.MASCULINE, lx.FEMININE) and gender != dgender:
                if gender == lx.FEMININE and (noun.low.startswith(('a', 'á', 'ha', 'há'))) and det in ('el', 'un', 'algún', 'ningún'):
                    continue            # el agua, un águila: the feminine noun with a stressed a
                fix = FAMILIES[family][(0 if gender == lx.MASCULINE else 1) + (0 if dnumber == 1 else 2)]
                p.add('es.det_gender', t[i], t[i], match_case(t[i].text, fix), fix)

    @rule('es.noun_adjective', 'agreement', 0.7)
    def noun_adjective(self, p):
        """a noun and its adjective: la casa blanco -> blanca, los libros viejo -> viejos"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for k in range(1, len(t) - 1):
            if not (p.word(k) and p.word(k + 1)) or not t[k + 1].space_before:
                continue
            if not (tg.has(t[k - 1], lx.DET) and t[k - 1].low in DETERMINERS | INVARIABLE_GENDER.keys() | {'el', 'la', 'los', 'las'}):
                continue
            ok, gender, number = self.noun_features(t[k], t[k - 1], t[k - 2] if k > 1 else None, t[k + 1] if k + 1 < len(t) else None)
            if ok and self.det_disagrees(t[k - 1].low, number):
                continue                # the noun is wrong: the determiner rule reports it
            if not ok or gender in (0, lx.EPICENE) or number not in (lx.SINGULAR, lx.PLURAL):
                continue
            adj = t[k + 1]
            readings = [a for a in adj.tags if a.pos & lx.ADJ]
            if not readings or any(a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE for a in adj.tags):
                continue
            if k + 2 < len(t) and t[k + 2].low in COORDINATORS:
                continue                # "un perro grande y bonito": coordinated adjectives may differ
            if any(a.gender in (0, lx.EPICENE, gender) and a.number in (number, lx.INVARIABLE) for a in readings):
                continue
            form = lex.inflect(readings[0], gender, number, 0, 0)
            if form and form != adj.low:
                p.add('es.noun_adjective', adj, adj, match_case(adj.text, form), form)

    @rule('es.subject_verb', 'agreement', 0.7)
    def subject_verb(self, p):
        """yo comes -> como, nosotros come -> comemos"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i, w in enumerate(t):
            if not p.word(i) or w.low not in SUBJECTS:
                continue
            if i > 0 and not (t[i - 1].kind == 'punct' or t[i - 1].low in STARTERS):
                continue                # "a él le gusta": not a subject
            if self.compound_subject(p, i):
                continue                # "él y yo comemos"
            v = i + 1
            while p.word(v) and t[v].low in CLITICS and v < i + 4:
                v += 1
            if not p.word(v):
                continue
            finite = [a for a in t[v].tags if a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE]
            if not finite or any(a.pos & ~(lx.VERB | lx.AUX) for a in t[v].tags):
                continue
            person, number = SUBJECTS[w.low]
            if any(a.person == person and a.number == number for a in finite):
                continue
            form = lex.inflect(finite[0], 0, number, person, finite[0].verb_form)
            if form and form != t[v].low:
                p.add('es.subject_verb', t[v], t[v], match_case(t[v].text, form), form)

    def participles(self, text):
        """The readings of a word as a past participle: (analysis, masculine singular form). The inflected forms of a participle
        (comprados) are entries of their own in the lexicon, with the participle (comprado) as lemma."""
        lex = self.core.lexicon
        found = []
        for a in lex.analyses(text):
            if not a.pos & lx.VERB:
                continue
            if a.verb_form == lx.PAST_PARTICIPLE:
                found.append((a, text.lower()))
            elif a.verb_form == 0 and any(b.verb_form == lx.PAST_PARTICIPLE for b in lex.analyses(lex.lemma(a))):
                found.append((a, lex.lemma(a)))
        return found

    @rule('es.haber_participle', 'agreement', 0.75)
    def haber_participle(self, p):
        """he comprados -> comprado: after haber the participle is always masculine singular"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)) or t[i].low not in HABER:
                continue
            readings = self.participles(t[i + 1].text)
            if not readings or any(a.gender in (0, lx.MASCULINE, lx.EPICENE) and a.number in (0, lx.SINGULAR, lx.INVARIABLE) for a, _ in readings):
                continue
            form = readings[0][1]
            if form and form != t[i + 1].low:
                p.add('es.haber_participle', t[i + 1], t[i + 1], match_case(t[i + 1].text, form), form)

    @rule('es.tilde', 'spelling', 0.8)
    def tilde(self, p):
        """tu eres -> tú eres, el es -> él es (only before the commonest verbs: the other words may be nouns)"""
        verbs = {'tu': {'eres', 'tienes', 'estás', 'vas', 'haces', 'puedes', 'quieres', 'sabes', 'dices', 'ves', 'vienes', 'fuiste', 'eras', 'estabas', 'tenías', 'hiciste', 'serás', 'tendrás'},
                 'el': {'es', 'está', 'tiene', 'va', 'hace', 'puede', 'quiere', 'sabe', 'dice', 've', 'viene', 'fue', 'era', 'estaba', 'tenía', 'hizo', 'será', 'tendrá', 'son', 'están'}}
        t = p.tokens
        for i in range(len(t) - 1):
            if p.word(i) and p.word(i + 1) and t[i].low in verbs and t[i + 1].low in verbs[t[i].low] and (i == 0 or t[i - 1].kind == 'punct' or t[i - 1].low in STARTERS):
                fix = 'tú' if t[i].low == 'tu' else 'él'
                p.add('es.tilde', t[i], t[i], match_case(t[i].text, fix), fix)

    # [SECTION] Accents, interrogatives, dequeísmo, impersonal "haber", noun subject, subjunctive

    @rule('es.accent', 'spelling', 0.85)
    def accent_cion(self, p):
        """informacion -> información: no Spanish word ends in an unaccented -cion"""
        for w in p.tokens:
            if w.kind == 'word' and len(w.low) > 5 and w.low.endswith('cion') and not w.text.isupper():
                fix = w.text[:-4] + 'ción'
                p.add('es.accent', w, w, fix, fix)

    INTERROGATIVES = {'donde': 'dónde', 'quien': 'quién', 'quienes': 'quiénes', 'cuanto': 'cuánto', 'cuantos': 'cuántos', 'cuanta': 'cuánta', 'cuantas': 'cuántas',
                      'cual': 'cuál', 'cuales': 'cuáles', 'porque': 'por qué'}

    @rule('es.interrogative', 'spelling', 0.8)
    def interrogative(self, p):
        """¿Donde vives? -> ¿Dónde vives?, ¿Porque no viniste? -> ¿Por qué no viniste?"""
        t = p.tokens
        for i in range(len(t) - 1):
            if t[i].kind != 'punct' or t[i].text != '¿' or not p.word(i + 1):
                continue
            w = t[i + 1]
            if w.low in self.INTERROGATIVES:
                fix = self.INTERROGATIVES[w.low]
                p.add('es.interrogative', w, w, match_case(w.text, fix), fix)
            elif w.low == 'por' and p.word(i + 2) and t[i + 2].low == 'que':
                p.add('es.interrogative', w, t[i + 2], match_case(w.text, 'por qué'), 'por qué')

    DEQUEISMO_VERBS = {'pienso', 'piensas', 'piensa', 'pensamos', 'piensan', 'creo', 'crees', 'cree', 'creemos', 'creen', 'digo', 'dices', 'dice', 'decimos', 'dicen', 'dije',
                       'dijo', 'dijeron', 'opino', 'opina', 'opinan', 'supongo', 'supone', 'suponen', 'afirmó', 'afirma', 'aseguró', 'asegura', 'comentó', 'comenta', 'explicó', 'explica'}

    @rule('es.dequeismo', 'syntax', 0.8)
    def dequeismo(self, p):
        """pienso de que vendrá -> pienso que vendrá"""
        t = p.tokens
        for i in range(len(t) - 2):
            if p.word(i) and p.word(i + 1) and p.word(i + 2) and t[i].low in self.DEQUEISMO_VERBS and t[i + 1].low == 'de' and t[i + 2].low == 'que':
                p.add('es.dequeismo', t[i + 1], t[i + 2], 'que', '%s que' % t[i].text)

    QUANTIFIERS = {'muchos', 'muchas', 'varios', 'varias', 'pocos', 'pocas', 'algunos', 'algunas', 'unos', 'unas', 'demasiados', 'demasiadas', 'dos', 'tres', 'cuatro', 'cinco',
                   'seis', 'siete', 'ocho', 'nueve', 'diez', 'tantos', 'tantas', 'bastantes'}
    IMPERSONAL = {'habían': 'había', 'habrán': 'habrá', 'habrían': 'habría', 'hubieran': 'hubiera', 'habían': 'había'}

    @rule('es.impersonal', 'agreement', 0.8)
    def impersonal(self, p):
        """habían muchas personas -> había muchas personas, hubieron fiestas -> hubo fiestas"""
        lex = self.core.lexicon
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)):
                continue
            w, nxt = t[i].low, t[i + 1]
            if w in self.IMPERSONAL and nxt.low in self.QUANTIFIERS:
                fix = self.IMPERSONAL[w]
                p.add('es.impersonal', t[i], t[i], match_case(t[i].text, fix), fix)
            elif w == 'hubieron' and not (lex and any(a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE for a in lex.analyses(nxt.text))):
                p.add('es.impersonal', t[i], t[i], match_case(t[i].text, 'hubo'), 'hubo')

    @rule('es.haber_echo', 'spelling', 0.85)
    def haber_echo(self, p):
        """he echo -> he hecho: after haber the participle of hacer is hecho"""
        t = p.tokens
        for i in range(len(t) - 1):
            if p.word(i) and p.word(i + 1) and t[i].low in HABER and t[i + 1].low == 'echo':
                p.add('es.haber_echo', t[i + 1], t[i + 1], match_case(t[i + 1].text, 'hecho'), 'hecho')

    COLLECTIVES = {'gente', 'grupo', 'mayoría', 'minoría', 'familia', 'multitud', 'equipo', 'público', 'resto', 'mitad', 'parte', 'serie', 'número', 'conjunto', 'ejército', 'pueblo'}

    @rule('es.noun_verb', 'agreement', 0.7)
    def noun_verb(self, p):
        """Los niños juega -> juegan, El niño juegan -> juega"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for k in range(1, len(t) - 1):
            if not (p.word(k - 1) and p.word(k) and p.word(k + 1)) or not t[k].space_before or t[k].text[0].isupper() or t[k].low in self.COLLECTIVES:
                continue
            det = t[k - 1].low
            if det not in DETERMINERS and det not in INVARIABLE_GENDER or not (k == 1 or t[k - 2].kind == 'punct' or t[k - 2].low in STARTERS):
                continue
            if self.compound_subject(p, k - 1):
                continue                # "el niño y la niña juegan"
            if not tg.only(t[k - 1], lx.DET) and det not in INVARIABLE_GENDER and det not in ('un', 'una', 'unos', 'unas'):
                continue
            ok, _, number = self.noun_features(t[k], t[k - 1], None, t[k + 1])
            if not ok or number not in (lx.SINGULAR, lx.PLURAL) or self.det_disagrees(det, number):
                continue
            verb = t[k + 1]
            finite = [a for a in verb.tags if a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE]
            if not finite or any(a.pos & ~(lx.VERB | lx.AUX) for a in verb.tags) or any(a.person == 3 and a.number == number for a in finite):
                continue
            form = lex.inflect(finite[0], 0, number, 3, finite[0].verb_form)
            if form and form != verb.low:
                p.add('es.noun_verb', verb, verb, match_case(verb.text, form), form)

    WISH_VERBS = {'quiero', 'quieres', 'quiere', 'queremos', 'quieren', 'espero', 'esperas', 'espera', 'deseo', 'necesito', 'necesitas', 'necesita', 'prefiero', 'prefieres', 'prefiere',
                  'dudo', 'pido', 'exijo', 'ojalá', 'temo', 'sugiero', 'recomiendo', 'ruego', 'permito', 'impido'}
    OBJECT_CLITICS = {'me', 'te', 'se', 'nos', 'os', 'lo', 'la', 'le', 'los', 'las', 'les', 'no'}

    @rule('es.subjunctive', 'conjugation', 0.75)
    def subjunctive(self, p):
        """quiero que vienes -> quiero que vengas: a verb of wish or doubt takes the subjunctive"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 2):
            if not (p.word(i) and p.word(i + 1)) or t[i].low not in self.WISH_VERBS or t[i + 1].low != 'que':
                continue
            if i > 0 and t[i - 1].kind == 'word' and t[i - 1].low in ('no', 'lo', 'que'):
                continue                # "lo que quiero que" or a negation: not a plain wish
            v = i + 2
            while p.word(v) and t[v].low in self.OBJECT_CLITICS and v < i + 5:
                v += 1
            if not p.word(v):
                continue
            readings = lex.analyses(t[v].text)
            finite = [a for a in readings if a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE]
            if not finite or any(a.pos & ~(lx.VERB | lx.AUX) for a in readings) or any(a.verb_form != lx.PRESENT for a in finite) or len({(a.person, a.number) for a in finite}) != 1:
                continue
            form = lex.inflect(finite[0], 0, finite[0].number, finite[0].person, lx.SUBJUNCTIVE_PRESENT)
            if form and form != t[v].low:
                p.add('es.subjunctive', t[v], t[v], match_case(t[v].text, form), form)


MORE_MESSAGES = {
    'en': {
        'es.accent': 'This word is written with an accent: "{arg}".',
        'es.interrogative': 'An interrogative word is written with an accent: "{arg}".',
        'es.dequeismo': 'Dequeísmo: this verb takes no "de": "{arg}".',
        'es.impersonal': 'Impersonal "haber" stays in the singular: "{arg}".',
        'es.haber_echo': 'The participle of "hacer" is "hecho" ("echo" is from "echar").',
        'es.noun_verb': 'The verb agrees with its subject: "{arg}".',
        'es.subjunctive': 'After a verb of wish or doubt the subjunctive is used: "{arg}".',
    },
    'fr': {
        'es.accent': "Ce mot s'écrit avec un accent : « {arg} ».",
        'es.interrogative': "Un mot interrogatif s'écrit avec un accent : « {arg} ».",
        'es.dequeismo': 'Dequeísmo : ce verbe ne prend pas « de » : « {arg} ».',
        'es.impersonal': '« haber » impersonnel reste au singulier : « {arg} ».',
        'es.haber_echo': 'Le participe de « hacer » est « hecho » (« echo » vient de « echar »).',
        'es.noun_verb': "Le verbe s'accorde avec son sujet : « {arg} ».",
        'es.subjunctive': 'Après un verbe de souhait ou de doute, on emploie le subjonctif : « {arg} ».',
    },
    'es': {
        'es.accent': 'Esta palabra lleva tilde: "{arg}".',
        'es.interrogative': 'La palabra interrogativa lleva tilde: "{arg}".',
        'es.dequeismo': 'Dequeísmo: este verbo no lleva "de": "{arg}".',
        'es.impersonal': '"Haber" impersonal va en singular: "{arg}".',
        'es.haber_echo': 'El participio de "hacer" es "hecho" ("echo" es de "echar").',
        'es.noun_verb': 'El verbo concuerda con su sujeto: "{arg}".',
        'es.subjunctive': 'Después de un verbo de deseo o duda se usa el subjuntivo: "{arg}".',
    },
}
for _ui, _table in MORE_MESSAGES.items():
    Grammar.messages[_ui].update(_table)
