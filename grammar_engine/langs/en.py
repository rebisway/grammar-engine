# grammar-engine - English
#
# Index of this file:
#   [SECTION] Tagger                          constraints which choose the reading of a word from its neighbours
#   [SECTION] Rules without lexicon           a/an, then/than, "i", fixed errors, to/too, loose/lose
#   [SECTION] Rules with the lexicon          subject and verb, determiner and noun, participles
#   [SECTION] More agreement                  "there is" + plural, "everyone are", noun subject and verb, "if I would have"
# Messages are in English, French and Spanish: the table at the start of the class, then MORE_MESSAGES at the end of the file.
# SPDX-License-Identifier: MIT

from .. import core, lexicon as lx
from .. import tagger as tg
from ..core import rule
from ..text import match_case

# Fixed errors: (words, replacement, not_before_capital), see Grammar.phrases
PHRASES = [
    ('could of', 'could have', False), ('would of', 'would have', False), ('should of', 'should have', False), ('must of', 'must have', False),
    ('might of', 'might have', False), ('alot', 'a lot', False), ('your welcome', "you're welcome", False), ('its a', "it's a", False),
    ('its an', "it's an", False), ('its been', "it's been", False), ('its not', "it's not", False), ('its going', "it's going", False),
    ('irregardless', 'regardless', False),
    # An apostrophe which is missing
    ('dont', "don't", False), ('doesnt', "doesn't", False), ('didnt', "didn't", False), ('isnt', "isn't", False), ('arent', "aren't", False), ('wasnt', "wasn't", False),
    ('werent', "weren't", False), ('couldnt', "couldn't", False), ('wouldnt', "wouldn't", False), ('shouldnt', "shouldn't", False), ('havent', "haven't", False),
    ('hasnt', "hasn't", False), ('hadnt', "hadn't", False), ('im', "I'm", False), ('ive', "I've", False), ('youre', "you're", False), ('theyre', "they're", False),
    # Confusions and non-standard forms
    ('its the', "it's the", False), ('its all', "it's all", False), ('its just', "it's just", False), ('its so', "it's so", False), ('its true', "it's true", False),
    ('its okay', "it's okay", False), ('its because', "it's because", False), ("it's own", 'its own', False), ('your a', "you're a", False), ('your the', "you're the", False),
    ('your not', "you're not", False), ('their is', 'there is', False), ('their are', 'there are', False), ('their was', 'there was', False), ('there own', 'their own', False),
    ('whose the', "who's the", False), ('whose going', "who's going", False), ('whose been', "who's been", False), ('the affect of', 'the effect of', False),
    ('between you and i', 'between you and me', False), ('between him and i', 'between him and me', False), ('between her and i', 'between her and me', False),
    ('more better', 'better', False), ('more bigger', 'bigger', False), ('more faster', 'faster', False), ('more easier', 'easier', False), ('more smaller', 'smaller', False),
    ('more worse', 'worse', False), ('more cheaper', 'cheaper', False), ('more older', 'older', False), ('more happier', 'happier', False), ('most best', 'best', False),
    ("don't have no", "don't have any", False), ("doesn't have no", "doesn't have any", False), ("didn't have no", "didn't have any", False),
    ("didn't do nothing", "didn't do anything", False), ("don't know nothing", "don't know anything", False), ("can't find nothing", "can't find anything", False),
    ('depend of', 'depend on', False), ('depends of', 'depends on', False), ('listen at', 'listen to', False), ('listening at', 'listening to', False),
    ('married with', 'married to', False), ('discuss about', 'discuss', False), ('discussing about', 'discussing', False), ('discussed about', 'discussed', False),
    ('in the other hand', 'on the other hand', False), ('on my opinion', 'in my opinion', False), ('looking forward to see', 'looking forward to seeing', False),
    ('look forward to see', 'look forward to seeing', False),
    ('less people', 'fewer people', False), ('less items', 'fewer items', False), ('less books', 'fewer books', False), ('less cars', 'fewer cars', False),
    ('less students', 'fewer students', False), ('less mistakes', 'fewer mistakes', False), ('less errors', 'fewer errors', False), ('less words', 'fewer words', False),
    ('less things', 'fewer things', False), ('less calories', 'fewer calories', False),
    ('much people', 'many people', False), ('much things', 'many things', False), ('much books', 'many books', False), ('much friends', 'many friends', False),
    ('much times', 'many times', False), ('much years', 'many years', False), ('much students', 'many students', False), ('many money', 'much money', False),
    ('many water', 'much water', False), ('many information', 'much information', False), ('many advice', 'much advice', False),
    ('informations', 'information', False), ('advices', 'advice', False), ('furnitures', 'furniture', False), ('equipments', 'equipment', False),
    ('homeworks', 'homework', False), ('luggages', 'luggage', False),
    # Regular endings put on irregular verbs and nouns
    ('goed', 'went', False), ('runned', 'ran', False), ('eated', 'ate', False), ('taked', 'took', False), ('buyed', 'bought', False), ('catched', 'caught', False),
    ('thinked', 'thought', False), ('swimmed', 'swam', False), ('speaked', 'spoke', False), ('bringed', 'brought', False), ('teached', 'taught', False),
    ('maked', 'made', False), ('gived', 'gave', False), ('writed', 'wrote', False), ('comed', 'came', False), ('knowed', 'knew', False), ('falled', 'fell', False),
    ('drinked', 'drank', False), ('builded', 'built', False), ('holded', 'held', False), ('standed', 'stood', False), ('sleeped', 'slept', False),
    ('feeled', 'felt', False), ('keeped', 'kept', False), ('sended', 'sent', False), ('spended', 'spent', False), ('losed', 'lost', False),
    ('childs', 'children', False), ('womans', 'women', False), ('tooths', 'teeth', False), ('gooder', 'better', False), ('badder', 'worse', False),
]

# Words which start with a vowel letter but a consonant sound, and the other way round
# Words which start with a vowel letter but a consonant sound ("a university"), and the other way round
CONSONANT_SOUND = {'one', 'once', 'unit', 'units', 'university', 'uniform', 'union', 'unique', 'useful', 'user', 'use', 'used', 'usual', 'utility',
                   'european', 'eulogy', 'ubiquitous', 'unicorn', 'unified', 'universal'}
SILENT_H = {'hour', 'hours', 'honest', 'honor', 'honour', 'heir', 'hourly', 'honorable', 'honourable'}
# Comparatives which are followed by "than"
COMPARATIVES = {'more', 'less', 'better', 'worse', 'bigger', 'smaller', 'larger', 'higher', 'lower', 'faster', 'slower', 'greater', 'rather', 'other',
                'older', 'younger', 'easier', 'harder', 'stronger', 'longer', 'taller'}

# Subject pronoun -> (person, number)
SUBJECTS = {'i': (1, 1), 'you': (2, 0), 'he': (3, 1), 'she': (3, 1), 'it': (3, 1), 'we': (1, 2), 'they': (3, 2)}
# Words after which a new clause (with its own subject) starts
CLAUSE_STARTERS = {'and', 'but', 'or', 'so', 'then', 'because', 'when', 'while', 'although', 'though', 'that', 'whereas', 'until', 'unless', 'since', 'as'}
# Adverbs which may stand between a subject and its verb
ADVERBS = {'never', 'always', 'often', 'usually', 'just', 'also', 'really', 'still', 'already', 'sometimes', 'rarely', 'seldom', 'even', 'only', 'now', 'soon'}
# Modal verbs, followed by a bare infinitive
MODALS = {'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'ought', 'need', 'dare'}
# Subject pronoun -> the right form of "be" (present, past)
BE_PRESENT = {'i': 'am', 'you': 'are', 'we': 'are', 'they': 'are', 'he': 'is', 'she': 'is', 'it': 'is'}
BE_PAST = {'i': 'was', 'you': 'were', 'we': 'were', 'they': 'were', 'he': 'was', 'she': 'was', 'it': 'was'}
# Determiners by number
SINGULAR_DETS = {'a', 'an', 'this', 'another', 'each', 'every'}
PLURAL_DETS = {'these', 'those', 'many', 'several', 'both'}
# Every determiner the tagger knows
DETERMINERS = SINGULAR_DETS | PLURAL_DETS | {'the', 'my', 'your', 'his', 'its', 'our', 'their', 'some', 'any', 'no', 'few', 'that'}
# Prepositions: after one the word is not a conjugated verb
PREPOSITIONS = {'of', 'in', 'on', 'at', 'by', 'for', 'with', 'from', 'about', 'into', 'over', 'under', 'between', 'through', 'during', 'before', 'after', 'without', 'against'}
BE_FORMS = {'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
HAVE_FORMS = {'have', 'has', 'had', 'having'}
# Adjectives and adverbs which "too" can modify
TOO_WORDS = {'much', 'many', 'late', 'early', 'soon', 'long', 'far', 'big', 'small', 'hard', 'easy', 'difficult', 'expensive', 'heavy', 'tired', 'good', 'bad', 'hot', 'cold', 'fast', 'slow', 'high', 'low', 'young', 'old'}


class Grammar(core.Grammar):
    """English: determiners, subject and verb, participles, confusions (to/too, then/than, its/it's), fixed errors."""
    language = 'en'
    lexicon = 'en.lex'
    coordinators = ('and', 'or', 'nor')

    messages = {
        'en': {
            'en.a_an': 'Use "a" before a consonant sound and "an" before a vowel sound (here before "{arg}").',
            'en.then_than': 'After a comparative use "than", not "then".',
            'en.i': 'The pronoun "I" is always a capital letter.',
            'en.phrase': 'Correct form: "{arg}".',
            'en.subject_verb': 'The verb agrees with its subject: "{arg}".',
            'en.det_number': 'The determiner and the noun do not agree in number: "{arg}".',
            'en.participle': 'After "have", "has" or "had" use the past participle: "{arg}".',
            'en.past': 'Without an auxiliary the simple past is used: "{arg}".',
            'en.to_too': '"too" (excessively), not "to": "{arg}".',
            'en.loose_lose': '"lose" (to mislay) is spelled with one o.',
        },
        'fr': {
            'en.a_an': 'Utilisez « a » devant un son consonne et « an » devant un son voyelle (ici devant « {arg} »).',
            'en.then_than': 'Après un comparatif on emploie « than », pas « then ».',
            'en.i': 'Le pronom « I » prend toujours une majuscule.',
            'en.phrase': 'Écriture correcte : « {arg} ».',
            'en.subject_verb': "Le verbe s'accorde avec son sujet : « {arg} ».",
            'en.det_number': "Le déterminant et le nom ne s'accordent pas en nombre : « {arg} ».",
            'en.participle': 'Après « have », « has » ou « had », on emploie le participe passé : « {arg} ».',
            'en.past': "Sans auxiliaire, on emploie le prétérit : « {arg} ».",
            'en.to_too': '« too » (trop), et non « to » : « {arg} ».',
            'en.loose_lose': '« lose » (perdre) s\'écrit avec un seul o.',
        },
        'es': {
            'en.a_an': 'Use "a" ante un sonido consonántico y "an" ante un sonido vocálico (aquí ante "{arg}").',
            'en.then_than': 'Después de un comparativo se usa "than", no "then".',
            'en.i': 'El pronombre "I" siempre va en mayúscula.',
            'en.phrase': 'Forma correcta: "{arg}".',
            'en.subject_verb': 'El verbo concuerda con su sujeto: "{arg}".',
            'en.det_number': 'El determinante y el nombre no concuerdan en número: "{arg}".',
            'en.participle': 'Después de "have", "has" o "had" se usa el participio: "{arg}".',
            'en.past': 'Sin auxiliar se usa el pasado simple: "{arg}".',
            'en.to_too': '"too" (demasiado), no "to": "{arg}".',
            'en.loose_lose': '"lose" (perder) se escribe con una sola o.',
        },
    }

    # [SECTION] Tagger

    def disambiguate(self, p):
        """Tagger constraints: the reading of a word from the determiner, the subject, the auxiliary or the preposition before it."""
        t = p.tokens
        for i, w in enumerate(t):
            if w.kind != 'word' or len(w.tags) < 2 or i == 0 or t[i - 1].kind != 'word':
                continue
            before = t[i - 1].low
            j = i - 1
            while j > 0 and t[j].kind == 'word' and t[j].low in ADVERBS:
                j -= 1                  # "he never goes": the adverb is skipped
            head = t[j].low
            if before in DETERMINERS and before != 'that':
                tg.keep(w, lx.NOUN | lx.ADJ | lx.PROPN | lx.OTHER)
            elif head in SUBJECTS and tg.select(w, lambda a: bool(a.pos & (lx.VERB | lx.AUX)) and a.verb_form in (lx.PRESENT, lx.IMPERFECT)):
                continue
            elif head in MODALS or (head == 'to' and before == 'to'):
                tg.select(w, lambda a: bool(a.pos & (lx.VERB | lx.AUX)) and a.verb_form == lx.INFINITIVE)
            elif head in HAVE_FORMS:
                tg.select(w, lambda a: bool(a.pos & lx.VERB) and a.verb_form == lx.PAST_PARTICIPLE)
            elif head in BE_FORMS:
                tg.select(w, lambda a: bool(a.pos & lx.VERB) and a.verb_form in (lx.PRESENT_PARTICIPLE, lx.PAST_PARTICIPLE)) or tg.keep(w, lx.ADJ)
            elif before in PREPOSITIONS:
                tg.select(w, lambda a: not (a.pos & (lx.VERB | lx.AUX)) or a.verb_form == lx.PRESENT_PARTICIPLE)

    # [SECTION] Rules without lexicon

    @rule('en.a_an', 'syntax', 0.75)
    def a_an(self, p):
        """a apple -> an apple, an dog -> a dog"""
        for i in range(len(p) - 1):
            if not (p.word(i) and p.word(i + 1)):
                continue
            a, w = p[i].low, p[i + 1].low
            if a not in ('a', 'an') or not w:
                continue
            vowel = w[0] in 'aeiou'
            text = p[i + 1].text
            if len(text) > 1 and all('A' <= ch <= 'Z' for ch in text):
                continue                # acronyms: the sound of the letters decides
            if a == 'a' and vowel and w not in CONSONANT_SOUND:
                p.add('en.a_an', p[i], p[i], match_case(p[i].text, 'an'), text)
            elif a == 'an' and not vowel and w not in SILENT_H and ord(w[0]) < 0x80:
                p.add('en.a_an', p[i], p[i], match_case(p[i].text, 'a'), text)

    @rule('en.then_than', 'spelling', 0.8)
    def then_than(self, p):
        """better then -> better than"""
        for i in range(1, len(p)):
            if p.word(i) and p.word(i - 1) and p[i].low == 'then' and p[i - 1].low in COMPARATIVES:
                p.add('en.then_than', p[i], p[i], match_case(p[i].text, 'than'))

    @rule('en.i', 'punctuation', 0.9)
    def pronoun_i(self, p):
        """the pronoun i is always a capital letter"""
        for i in range(len(p)):
            if p.word(i) and p[i].text == 'i':
                p.add('en.i', p[i], p[i], 'I')

    @rule('en.phrase', 'expression', 0.85)
    def phrase(self, p):
        """fixed errors of the table PHRASES: could of -> could have"""
        self.phrases(p, PHRASES, 'en.phrase')

    @rule('en.to_too', 'spelling', 0.7)
    def to_too(self, p):
        """it is to big -> too big"""
        t = p.tokens
        for i in range(2, len(t)):
            if p.word(i) and t[i].low == 'to' and t[i - 1].low in BE_FORMS and p.word(i + 1) and t[i + 1].low in TOO_WORDS:
                after = t[i + 2] if i + 2 < len(t) else None
                if after is None or after.kind == 'punct' or after.low in ('for', 'of', 'and', 'but'):
                    p.add('en.to_too', t[i], t[i], match_case(t[i].text, 'too'), 'too')

    @rule('en.loose_lose', 'spelling', 0.75)
    def loose_lose(self, p):
        """you will loose -> lose"""
        t = p.tokens
        for i in range(1, len(t)):
            if p.word(i) and t[i].low == 'loose' and t[i - 1].low in MODALS | {'to', "don't", "doesn't", "didn't", "won't", "can't"}:
                p.add('en.loose_lose', t[i], t[i], match_case(t[i].text, 'lose'), 'lose')

    # [SECTION] Rules with the lexicon

    @rule('en.subject_verb', 'agreement', 0.75)
    def subject_verb(self, p):
        """he go -> goes, they goes -> go, I is -> am, he don't -> doesn't"""
        lex = self.core.lexicon
        t = p.tokens
        for i, w in enumerate(t):
            if not p.word(i) or w.low not in SUBJECTS:
                continue
            if i > 0 and not (t[i - 1].kind == 'punct' or t[i - 1].low in CLAUSE_STARTERS):
                continue                # "does he go": the subject is not at the start of its clause
            if self.compound_subject(p, i):
                continue                # "he and I are"
            v = i + 1
            while p.word(v) and t[v].low in ADVERBS:
                v += 1
            if not p.word(v):
                continue
            verb = t[v]
            person, number = SUBJECTS[w.low]
            third = w.low in ('he', 'she', 'it')
            if verb.low in ('am', 'is', 'are'):
                if verb.low != BE_PRESENT[w.low]:
                    p.add('en.subject_verb', verb, verb, match_case(verb.text, BE_PRESENT[w.low]), BE_PRESENT[w.low])
                continue
            if verb.low in ('was', 'were'):
                if verb.low != BE_PAST[w.low] and not (verb.low == 'were' and w.low != 'you'):
                    p.add('en.subject_verb', verb, verb, match_case(verb.text, BE_PAST[w.low]), BE_PAST[w.low])
                continue
            if verb.low in ("don't", "doesn't"):
                right = "doesn't" if third else "don't"
                if verb.low != right:
                    p.add('en.subject_verb', verb, verb, match_case(verb.text, right), right)
                continue
            if not lex:
                continue
            finite = [a for a in verb.tags if a.pos & (lx.VERB | lx.AUX) and a.verb_form in (lx.PRESENT, lx.IMPERFECT)]
            if not finite or any(lex.lemma(a) in MODALS for a in finite) or any(a.verb_form == lx.IMPERFECT for a in finite):
                continue
            has_third = any(a.person == 3 for a in finite)
            has_base = any(a.person != 3 for a in finite)
            if third and not has_third:
                form = lex.inflect(finite[0], 0, 1, 3, lx.PRESENT)
                if form and form != verb.low:
                    p.add('en.subject_verb', verb, verb, match_case(verb.text, form), form)
            elif not third and has_third and not has_base:
                form = lex.lemma(finite[0])
                if form and form != verb.low:
                    p.add('en.subject_verb', verb, verb, match_case(verb.text, form), form)

    @rule('en.det_number', 'agreement', 0.7)
    def det_number(self, p):
        """a books -> a book, these book -> these books"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)) or not t[i + 1].space_before:
                continue
            det, noun = t[i].low, t[i + 1]
            if det not in SINGULAR_DETS and det not in PLURAL_DETS:
                continue
            readings = [a for a in noun.tags if a.pos & lx.NOUN]
            if not readings or any(a.pos & ~(lx.NOUN | lx.ADJ | lx.OTHER) for a in noun.tags) or noun.text[0].isupper():
                continue
            raw = lex.analyses(noun.text)
            after = t[i + 2] if i + 2 < len(t) else None
            if after is not None and after.kind == 'word' and tg.has(after, lx.NOUN | lx.ADJ) and not tg.has(after, lx.VERB | lx.AUX):
                continue                # the noun is a modifier of the next word: "several other creatures"
            if any(a.pos & (lx.PRON | lx.ADV | lx.ADP | lx.CCONJ | lx.SCONJ | lx.DET | lx.INTJ) for a in raw):
                continue                # "those who run": a function word is not a noun
            if det in PLURAL_DETS and any(a.pos & (lx.ADJ | (lx.VERB | lx.AUX if det not in ('these', 'those') else 0)) for a in raw):
                continue                # "both go", "those long words": not a noun for sure
            numbers = {a.number for a in readings}
            plural = [a for a in readings if a.number == lx.PLURAL and lex.lemma(a) != noun.low]
            if det in SINGULAR_DETS and plural and not any(a.number == lx.SINGULAR and lex.lemma(a) != noun.low for a in readings):
                form = lex.lemma(plural[0])      # "a books": 'books' is also a noun of its own, so only a plural of another word counts
                if form and form != noun.low:
                    p.add('en.det_number', noun, noun, match_case(noun.text, form), form)
            elif det in PLURAL_DETS and numbers == {lx.SINGULAR}:
                form = lex.inflect(readings[0], 0, lx.PLURAL, 0, 0)
                if form and form != noun.low:
                    p.add('en.det_number', noun, noun, match_case(noun.text, form), form)

    @rule('en.participle', 'conjugation', 0.75, emits=('en.past',))
    def participle(self, p):
        """I have went -> gone, I seen it -> I saw it"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i, w in enumerate(t):
            if not p.word(i):
                continue
            if w.low in ('have', 'has', 'had'):
                v = i + 1
                while p.word(v) and t[v].low in ADVERBS | {'not'}:
                    v += 1
                if not p.word(v):
                    continue
                raw = [a for a in lex.analyses(t[v].text) if a.pos & lx.VERB]
                past = [a for a in raw if a.verb_form == lx.IMPERFECT]
                if past and not any(a.verb_form == lx.PAST_PARTICIPLE for a in raw) and not any(a.verb_form in (lx.INFINITIVE, lx.PRESENT) for a in raw):
                    form = lex.inflect(past[0], 0, 0, 0, lx.PAST_PARTICIPLE)
                    if form and form != t[v].low:
                        p.add('en.participle', t[v], t[v], match_case(t[v].text, form), form)
            elif w.low in SUBJECTS and i + 1 < len(t) and p.word(i + 1) and (i == 0 or t[i - 1].kind == 'punct' or t[i - 1].low in CLAUSE_STARTERS):
                raw = [a for a in lex.analyses(t[i + 1].text) if a.pos & lx.VERB]
                if raw and all(a.verb_form == lx.PAST_PARTICIPLE for a in raw):
                    form = lex.inflect(raw[0], 0, 0, 0, lx.IMPERFECT)
                    if form and form != t[i + 1].low:
                        p.add('en.past', t[i + 1], t[i + 1], match_case(t[i + 1].text, form), form, 0.65)

    # [SECTION] More agreement: "there is" + plural, "everyone are", noun subject and verb, "if I would have"

    PLURAL_AFTER_THERE = {'many', 'several', 'few', 'these', 'those', 'both', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'twelve', 'hundreds', 'thousands'}
    THERE_FORMS = {'is': 'are', 'was': 'were'}

    @rule('en.there_is', 'agreement', 0.8)
    def there_is(self, p):
        """there is many people -> there are many people"""
        t = p.tokens
        for i in range(len(t) - 2):
            if p.word(i) and p.word(i + 1) and p.word(i + 2) and t[i].low == 'there' and t[i + 1].low in self.THERE_FORMS and t[i + 2].low in self.PLURAL_AFTER_THERE:
                fix = self.THERE_FORMS[t[i + 1].low]
                p.add('en.there_is', t[i + 1], t[i + 1], match_case(t[i + 1].text, fix), fix)

    INDEFINITE = {'everyone', 'everybody', 'everything', 'someone', 'somebody', 'anyone', 'anybody', 'nobody', 'nothing', 'something', 'anything'}
    SUBJECT_PRONOUN_WORDS = {'i', 'you', 'we', 'they', 'he', 'she', 'it'}

    @rule('en.everyone', 'agreement', 0.8)
    def everyone(self, p):
        """everyone are happy -> everyone is happy, nobody were there -> nobody was there"""
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)) or t[i].low not in self.INDEFINITE or t[i + 1].low not in ('are', 'were'):
                continue
            after = t[i + 2] if i + 2 < len(t) else None
            if after is not None and after.kind == 'word' and after.low in self.SUBJECT_PRONOUN_WORDS:
                continue                # "hello everyone are you ready": the verb opens a question
            if i > 0 and t[i - 1].kind == 'word' and t[i - 1].low in ('are', 'were', 'who', 'what', 'where', 'how', 'why', 'when'):
                continue
            fix = 'is' if t[i + 1].low == 'are' else 'was'
            p.add('en.everyone', t[i + 1], t[i + 1], match_case(t[i + 1].text, fix), fix)

    COLLECTIVE_NOUNS = {'team', 'family', 'group', 'staff', 'committee', 'government', 'police', 'people', 'audience', 'class', 'crew', 'jury', 'couple', 'majority', 'public',
                        'army', 'band', 'board', 'company', 'council', 'faculty', 'number', 'data', 'media', 'criteria', 'phenomena', 'bacteria', 'agenda', 'minority', 'club', 'cast'}
    SINGULAR_IN_S = {'news', 'series', 'species', 'means', 'headquarters', 'crossroads', 'measles', 'mumps', 'billiards', 'darts', 'works', 'barracks', 'gallows'}
    SUBJECT_DETERMINERS = {'the', 'these', 'those', 'my', 'our', 'your', 'their', 'his', 'some', 'many', 'several', 'both'}
    SINGULAR_SUBJECT_DETERMINERS = {'the', 'a', 'an', 'this', 'my', 'your', 'his', 'her', 'our', 'their', 'each', 'every'}
    PLURAL_VERBS = {'are': 'is', 'were': 'was', 'have': 'has', "don't": "doesn't"}
    SINGULAR_VERBS = {'is': 'are', 'was': 'were', 'has': 'have', "doesn't": "don't"}

    @rule('en.noun_verb', 'agreement', 0.7)
    def noun_verb(self, p):
        """The dogs runs -> The dogs run, The dogs is -> are, The dog are -> The dog is"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for k in range(1, len(t) - 1):
            if not (p.word(k) and p.word(k + 1)) or not t[k].space_before or not t[k + 1].space_before or t[k].text[0].isupper():
                continue
            det = t[k - 1].low
            if not p.word(k - 1) or not (k == 1 or t[k - 2].kind == 'punct' or t[k - 2].low in CLAUSE_STARTERS):
                continue
            if self.compound_subject(p, k - 1):
                continue                # "the dog and the cat are"
            readings = [a for a in t[k].tags if a.pos & lx.NOUN]
            if not readings or any(a.pos & ~(lx.NOUN | lx.ADJ | lx.OTHER) for a in t[k].tags) or t[k].low in self.COLLECTIVE_NOUNS:
                continue
            plural = any(a.number == lx.PLURAL and lex.lemma(a) != t[k].low for a in readings) and t[k].low not in self.SINGULAR_IN_S and not t[k].low.endswith('ics')
            singular = all(a.number == lx.SINGULAR for a in readings) and all(lex.lemma(a) == t[k].low for a in readings) and not t[k].low.endswith('s')
            verb = t[k + 1]
            if plural and det in self.SUBJECT_DETERMINERS:
                if verb.low in self.SINGULAR_VERBS:
                    fix = self.SINGULAR_VERBS[verb.low]
                    p.add('en.noun_verb', verb, verb, match_case(verb.text, fix), fix)
                    continue
                raw = [a for a in lex.analyses(verb.text) if a.pos & (lx.VERB | lx.AUX) and a.verb_form in (lx.PRESENT, lx.IMPERFECT)]
                after = t[k + 2] if k + 2 < len(t) else None
                closed = after is None or after.kind != 'word' or not tg.only(after, lx.NOUN | lx.PROPN)       # not "dogs bones" (a compound noun)
                if raw and closed and all(a.person == 3 and a.number == lx.SINGULAR and a.verb_form == lx.PRESENT for a in raw):
                    form = lex.lemma(raw[0])
                    if form and form != verb.low:
                        p.add('en.noun_verb', verb, verb, match_case(verb.text, form), form)
            elif singular and det in self.SINGULAR_SUBJECT_DETERMINERS and verb.low in self.PLURAL_VERBS:
                fix = self.PLURAL_VERBS[verb.low]
                p.add('en.noun_verb', verb, verb, match_case(verb.text, fix), fix)

    @rule('en.if_would', 'conjugation', 0.75)
    def if_would(self, p):
        """if I would have known -> if I had known"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 4):
            if not all(p.word(i + k) for k in range(5)) or t[i].low != 'if' or t[i + 1].low not in self.SUBJECT_PRONOUN_WORDS or t[i + 2].low != 'would' or t[i + 3].low != 'have':
                continue
            if any(a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE for a in lex.analyses(t[i + 4].text)) and t[i + 4].low not in ('time', 'chance', 'a', 'the'):
                p.add('en.if_would', t[i + 2], t[i + 3], 'had', 'if %s had' % t[i + 1].text)


MORE_MESSAGES = {
    'en': {
        'en.there_is': 'With a plural, "there are" (or "there were"): "{arg}".',
        'en.everyone': 'Words like "everyone" and "nobody" take a singular verb: "{arg}".',
        'en.noun_verb': 'The verb agrees with its subject: "{arg}".',
        'en.if_would': 'After "if" the past perfect is used, not "would have": "{arg}".',
    },
    'fr': {
        'en.there_is': 'Avec un pluriel : « there are » (ou « there were ») : « {arg} ».',
        'en.everyone': 'Des mots comme « everyone » et « nobody » veulent un verbe au singulier : « {arg} ».',
        'en.noun_verb': "Le verbe s'accorde avec son sujet : « {arg} ».",
        'en.if_would': 'Après « if », on emploie le plus-que-parfait et non « would have » : « {arg} ».',
    },
    'es': {
        'en.there_is': 'Con un plural: "there are" (o "there were"): "{arg}".',
        'en.everyone': 'Palabras como "everyone" y "nobody" llevan el verbo en singular: "{arg}".',
        'en.noun_verb': 'El verbo concuerda con su sujeto: "{arg}".',
        'en.if_would': 'Después de "if" se usa el pluscuamperfecto, no "would have": "{arg}".',
    },
}
for _ui, _table in MORE_MESSAGES.items():
    Grammar.messages[_ui].update(_table)
