# grammar-engine - French
#
# Index of this file:
#   [SECTION] Helpers                         small tests shared by the rules
#   [SECTION] Tagger                          constraints which choose the reading of a word from its neighbours
#   [SECTION] Agreement of the past participle
#   [SECTION] More agreements                 attribute, noun subject, adjective before the noun, tout, possessive before a vowel
#   [SECTION] Sequence of tenses              "si" and the mood after a conjunction
#   [SECTION] Prepositions                    which a verb or an adjective does not take
#   [SECTION] Homophones                      chosen with the readings left by the tagger
#   [SECTION] Rules without lexicon           a/à, ont/sont, participle and infinitive (with the dictionary of the host), fixed errors
#   [SECTION] Agreement, with the lexicon     determiner and noun, noun and adjective, subject and verb
#   [SECTION] Elision, verb person, number words, "quelque", "moi qui", "la plupart"
# Messages are in English, French and Spanish: the table at the start of the class, then MORE_MESSAGES at the end of the file.
# SPDX-License-Identifier: MIT

from .. import core, lexicon as lx
from .. import tagger as tg
from ..core import rule
from ..text import match_case

# Conjunctions after which a new clause (with its own subject) starts
STARTERS = {'et', 'ou', 'mais', 'que', "qu'", 'si', "s'", 'quand', 'lorsque', "lorsqu'", 'comme', 'puisque', "puisqu'", 'car', 'donc', 'alors', 'où', 'dont', 'pendant', 'ni'}
# Subject pronouns: after one of them "est", "sont"... are auxiliaries
SUBJECTS_BEFORE_ETRE = {'il', 'elle', 'on', 'ils', 'elles', 'je', "j'", 'tu', 'nous', 'vous'}
# Forms of avoir and être which take a past participle
AUXILIARIES = {'ai', 'as', 'a', 'avons', 'avez', 'ont', 'avais', 'avait', 'avions', 'aviez', 'avaient', 'aurai', 'auras', 'aura', 'aurons', 'aurez', 'auront',
               'aurais', 'aurait', 'aurions', 'auriez', 'auraient', 'ayant', 'est', 'sont', 'était', 'étaient', 'sera', 'seront', 'serait', 'seraient', 'suis', 'es',
               'sommes', 'êtes', 'étais', 'fut'}
# Determiners by number and gender (the lexicon does not label them all)
PLURAL_DETS = {'les', 'des', 'ces', 'mes', 'tes', 'ses', 'nos', 'vos', 'leurs', 'aux', 'quelques', 'plusieurs'}
SINGULAR_DETS = {'chaque', 'le', 'la', 'un', 'une', 'ce', 'cet', 'cette', 'mon', 'ma', 'ton', 'ta', 'son', 'sa', 'notre', 'votre', 'du', 'au'}
MASCULINE_DETS = {'le', 'un', 'ce', 'cet', 'mon', 'ton', 'son', 'du', 'au'}
FEMININE_DETS = {'la', 'une', 'cette', 'ma', 'ta', 'sa'}
TO_FEMININE = {'le': 'la', 'un': 'une', 'ce': 'cette', 'cet': 'cette', 'mon': 'ma', 'ton': 'ta', 'son': 'sa'}
TO_MASCULINE = {'la': 'le', 'une': 'un', 'cette': 'ce', 'ma': 'mon', 'ta': 'ton'}
# Number words which are not nouns after "un", "deux cent"...
NUMERALS = {'cent', 'cents', 'mille', 'vingt', 'vingts', 'million', 'millions', 'milliard', 'milliards', 'douze', 'quinze', 'seize', 'trente', 'quarante', 'cinquante', 'soixante'}
# Every form of être (the attribute rule looks for an adjective after them)
ETRE_FORMS = {'suis', 'es', 'est', 'sommes', 'êtes', 'sont', 'étais', 'était', 'étions', 'étiez', 'étaient', 'fus', 'fut', 'fûmes', 'furent', 'serai', 'seras', 'sera', 'serons', 'serez',
              'seront', 'serais', 'serait', 'serions', 'seriez', 'seraient', 'sois', 'soit', 'soyons', 'soyez', 'soient', 'étant'}
# Adverbs which may stand between an auxiliary and its participle
BETWEEN = {'pas', 'déjà', 'bien', 'toujours', 'jamais', 'plus', 'encore', 'vraiment', 'enfin', 'souvent', 'tôt', 'tard', 'presque', 'trop', 'très', 'aussi', 'même', 'point'}
# Subject pronoun -> (possible genders, number), for the agreement of participles and adjectives
SUBJECT_FEATURES = {'il': ((1,), 1), 'elle': ((2,), 1), 'ils': ((1,), 2), 'elles': ((2,), 2), 'je': ((1, 2), 1), "j'": ((1, 2), 1), 'tu': ((1, 2), 1), 'nous': ((1, 2), 2)}
# Verbs whose past participle does not agree with a preceding object (durée, prix: "les années qu'il a vécu")
INVARIABLE_VERBS = {'savoir', 'pouvoir', 'vouloir', 'devoir', 'falloir', 'croire', 'penser', 'espérer', 'prétendre', 'affirmer', 'déclarer', 'coûter', 'valoir', 'peser', 'durer', 'vivre', 'courir', 'marcher', 'régner', 'dormir', 'mesurer'}
# Pronominal verbs whose reflexive pronoun is a direct object: the participle agrees with the subject
PRONOMINAL_VERBS = {'laver', 'lever', 'coucher', 'réveiller', 'habiller', 'promener', 'dépêcher', 'asseoir', 'tromper', 'arrêter', 'approcher', 'éloigner', 'retourner',
                    'préparer', 'installer', 'précipiter', 'évanouir', 'enfuir', 'envoler', 'endormir', 'réfugier', 'cacher', 'blottir', 'pencher', 'redresser', 'détourner',
                    'tourner', 'baisser', 'glisser', 'dresser', 'élever', 'écrouler', 'effondrer', 'noyer', 'souvenir', 'apercevoir', 'aller', 'abstenir', 'absenter', 'retrouver', 'perdre'}
# Nouns which take a clause ("l'idée que..."): there "que" is a conjunction, not a relative pronoun
CLAUSE_NOUNS = {'fait', 'idée', 'impression', 'sentiment', 'certitude', 'espoir', 'crainte', 'peur', 'sensation', 'raison', 'preuve', 'croyance', 'rumeur',
                'hypothèse', 'possibilité', 'chance', 'condition', 'promesse', 'sorte', 'façon', 'manière', 'douleur', 'joie', 'honte', 'pitié', 'regret', 'surprise',
                'nouvelle', 'avis', 'illusion', 'conviction', 'habitude', 'moment', 'jour', 'temps', 'fois', 'année', 'ans', 'heure', 'heures', 'minutes', 'mois', 'semaine', 'semaines'}
# Words which can be a direct object placed before the verb (so the participle may agree)
OBJECT_WORDS = {'les', 'la', "l'", 'le', 'que', "qu'", 'me', "m'", 'te', "t'", 'nous', 'vous', 'se', "s'", 'quel', 'quelle', 'quels', 'quelles', 'combien', 'lequel', 'laquelle',
                'lesquels', 'lesquelles', 'en', 'dont', 'ce', 'ceux', 'celles', 'tout', 'toute', 'tous', 'toutes', 'où', 'comment', 'pourquoi', 'quand', 'ci'}
# Verbs which take "de" before an infinitive (not "à"), and the other way round
# Verbs which take "de" before an infinitive (not "à"), and the other way round
VERBS_DE = {'essayer', 'tenter', 'oublier', 'refuser', 'cesser', 'risquer', 'éviter', 'regretter', 'craindre', 'menacer', 'accepter'}
VERBS_A = {'apprendre', 'aider', 'hésiter', 'réussir', 'parvenir', 'habituer', 'chercher', 'inviter', 'encourager', 'consentir'}
# Adjective -> the preposition it takes ("différent de")
ADJECTIVES_PREPOSITION = {'différent': 'de', 'identique': 'à', 'semblable': 'à'}
# Verbs after which an adjective is an attribute of the subject
LINK_VERBS = ETRE_FORMS | {'semble', 'semblent', 'semblait', 'semblaient', 'paraît', 'paraissent', 'paraissait', 'paraissaient', 'devient', 'deviennent', 'devenait',
                          'devenaient', 'reste', 'restent', 'restait', 'restaient', 'demeure', 'demeurent'}
# Adverbs which may stand between a link verb and its adjective
DEGREE_ADVERBS = {'très', 'trop', 'si', 'assez', 'plus', 'moins', 'aussi', 'bien', 'fort', 'tellement', 'vraiment', 'toujours', 'jamais', 'pas', 'encore', 'déjà'}
# Collective nouns: the verb after them may be singular or plural
COLLECTIVES = {'plupart', 'majorité', 'minorité', 'foule', 'groupe', 'moitié', 'tiers', 'quart', 'partie', 'multitude', 'bande', 'troupe', 'série', 'quantité', 'nombre',
               'paire', 'dizaine', 'douzaine', 'centaine', 'millier', 'reste', 'équipe', 'famille', 'peuple', 'armée', 'public', 'police'}
# Adjectives which usually go before the noun
ANTEPOSED = {'grand', 'petit', 'beau', 'bon', 'mauvais', 'joli', 'vieux', 'jeune', 'nouveau', 'gros', 'long', 'haut', 'gentil', 'vilain', 'court', 'large', 'faux', 'seul',
             'premier', 'dernier', 'autre', 'meilleur', 'pire', 'vrai'}
SUBJECT_STARTERS = STARTERS - {'et', 'ou', 'ni'}      # a noun after "et" may belong to a compound subject
# Colours: often invariable, so not checked against the noun
COLORS = {'bleu', 'vert', 'rouge', 'jaune', 'rose', 'marron', 'orange', 'noir', 'blanc', 'gris', 'violet', 'bordeaux', 'turquoise'}
# Object pronouns which stand between a subject and its verb
CLITICS = {'ne', "n'", 'me', "m'", 'te', "t'", 'se', "s'", 'le', 'la', "l'", 'les', 'lui', 'y', 'en', 'nous', 'vous'}
# Subject pronoun -> (person, number)
SUBJECT_PRONOUNS = {'je': (1, 1), "j'": (1, 1), 'tu': (2, 1), 'il': (3, 1), 'elle': (3, 1), 'on': (3, 1), 'nous': (1, 2), 'vous': (2, 2), 'ils': (3, 2), 'elles': (3, 2)}

# Parts of speech of words which are never nouns
FUNCTION_WORDS = lx.CCONJ | lx.SCONJ | lx.ADP | lx.ADV | lx.PRON | lx.DET | lx.INTJ

# Fixed errors: (words, replacement, not_before_capital), see Grammar.phrases
PHRASES = [
    ('lendemain matins', 'lendemain matin', False), ('lendemain soirs', 'lendemain soir', False), ('surlendemain matins', 'surlendemain matin', False),
    ('au dessus', 'au-dessus', False), ('au dessous', 'au-dessous', False), ("c' est à dire", "c'est-à-dire", False), ('vis à vis', 'vis-à-vis', False),
    ('ci joint', 'ci-joint', False), ('quelque soit', 'quel que soit', False), ('quelque soient', 'quels que soient', False), ('quand à', 'quant à', False),
    ('au dépend de', 'aux dépens de', False), ('voire même', 'voire', False), ('malgré que', 'bien que', False), ('à cause que', 'parce que', False),
    ('a cause de', 'à cause de', False), ('a propos de', 'à propos de', False), ("d' ou", "d'où", False), ('parce-que', 'parce que', False),
    ('tout a coup', 'tout à coup', False), ("tout a l' heure", "tout à l'heure", False), ('a peu près', 'à peu près', False), ("a l' instar de", "à l'instar de", False),
    ('quant a', 'quant à', False), ('prêt a', 'prêt à', False), ('grâce a', 'grâce à', False), ('a travers', 'à travers', False), ('par rapport a', 'par rapport à', False),
    ('tout a fait', 'tout à fait', False), ('au fur et a mesure', 'au fur et à mesure', False), ('a côté de', 'à côté de', False), ('a gauche', 'à gauche', False),
    ('a droite', 'à droite', False), ('va-y', 'vas-y', False), ('vous disez', 'vous dites', False), ('vous faisez', 'vous faites', False), ('quatre vingt', 'quatre-vingt', False),
    ('tres', 'très', False), ('deja', 'déjà', False), ('apres', 'après', False), ('etre', 'être', False), ('ecole', 'école', False), ('tete', 'tête', False),
    ('fenetre', 'fenêtre', False), ('foret', 'forêt', False), ('pere', 'père', False), ('mere', 'mère', False), ('frere', 'frère', False), ('premiere', 'première', False),
    ('derniere', 'dernière', False), ('lumiere', 'lumière', False), ('riviere', 'rivière', False), ('maniere', 'manière', False), ('probleme', 'problème', False),
    ('systeme', 'système', False), ('reponse', 'réponse', False), ('etait', 'était', False), ('etaient', 'étaient', False), ('different', 'différent', False),
    ('evidemment', 'évidemment', False), ('a bientot', 'à bientôt', False),
]


class Grammar(core.Grammar):
    """French: agreement, participles, tenses and moods, homophones, elision, fixed errors."""
    language = 'fr'
    coordinators = ('et', 'ou', 'ni')
    elisions = ("l'", "d'", "j'", "n'", "s'", "c'", "m'", "t'", "qu'", "jusqu'", "lorsqu'", "puisqu'", "quoiqu'")
    lexicon = 'fr.lex'

    messages = {
        'en': {
            'fr.a': '"à" is a preposition; after "il", "elle" or "on" it is the verb avoir: "a".',
            'fr.ont': 'After "ils" or "elles", the verb avoir is written "ont".',
            'fr.sont': 'After "ils", "elles", "ceux" or "celles", the verb être is written "sont" ("son" is a determiner).',
            'fr.participle': 'After an auxiliary (avoir or être) the verb is a past participle: "{arg}".',
            'fr.infinitive': 'After "pour", "sans" or a verb like pouvoir, vouloir, devoir or aller, the verb is an infinitive: "{arg}".',
            'fr.phrase': 'Correct form: "{arg}".',
            'fr.det_number': 'The determiner and the noun do not agree in number: "{arg}".',
            'fr.det_gender': 'The determiner does not agree in gender with the noun: "{arg}".',
            'fr.noun_adjective': 'The adjective agrees in gender and number with the noun: "{arg}".',
            'fr.subject_verb': 'The verb agrees with its subject: "{arg}".',
            'fr.participle_subject': 'The past participle agrees with the subject after être: "{arg}".',
            'fr.participle_object': 'The past participle agrees with the direct object placed before avoir: "{arg}".',
            'fr.attribute': 'The adjective agrees with the subject: "{arg}".',
            'fr.subject_noun_verb': 'The verb agrees with its subject: "{arg}".',
            'fr.tout': '"tout" agrees with what follows: "{arg}".',
            'fr.possessive_vowel': 'Before a vowel the possessive is "{arg}".',
            'fr.preposition': 'Correct construction: "{arg}".',
            'fr.si_tense': 'After "si" (a condition) use neither the conditional nor the future: "{arg}".',
            'fr.subjunctive': 'This construction takes the subjunctive: "{arg}".',
            'fr.indicative_after': 'After "après que" the indicative is the rule: "{arg}".',
            'fr.participle_invariable': 'With avoir, with no direct object before, the past participle does not agree: "{arg}".',
            'fr.ce_se': 'Confusion between "ce" and "se": "{arg}".',
            'fr.a_accent': '"à" (preposition) is written with an accent here.',
            'fr.ou_where': '"où" (place or time) is written with an accent.',
            'fr.leur': '"leur" is singular and "leurs" plural, like the noun: "{arg}".',
            'fr.la_there': '"là" (place) is written with an accent.',
            'fr.sa_ca': 'Here the pronoun is "ça", not the determiner "sa".',
            'fr.cest_sest': 'With a reflexive verb, "s\'est" is written, not "c\'est".',
            'fr.et_est': '"{arg}" (the verb être), not "et" (and).',
            'fr.peu_peut': '"peut" (the verb pouvoir), not "peu" (little).',
            'fr.ma_ma': '"{arg}": the pronoun and the auxiliary avoir, not the determiner.',
        },
        'fr': {
            'fr.a': '« à » est une préposition ; après « il », « elle » ou « on », c\'est le verbe avoir : « a ».',
            'fr.ont': 'Après « ils » ou « elles », le verbe avoir s\'écrit « ont ».',
            'fr.sont': 'Après « ils », « elles », « ceux » ou « celles », le verbe être s\'écrit « sont » (« son » est un déterminant).',
            'fr.participle': 'Après un auxiliaire (avoir ou être), le verbe est un participe passé : « {arg} ».',
            'fr.infinitive': 'Après « pour », « sans » ou un verbe comme pouvoir, vouloir, devoir ou aller, le verbe est à l\'infinitif : « {arg} ».',
            'fr.phrase': 'Écriture correcte : « {arg} ».',
            'fr.det_number': 'Le déterminant et le nom ne s\'accordent pas en nombre : « {arg} ».',
            'fr.det_gender': 'Le déterminant ne s\'accorde pas en genre avec le nom : « {arg} ».',
            'fr.noun_adjective': 'L\'adjectif s\'accorde en genre et en nombre avec le nom : « {arg} ».',
            'fr.subject_verb': 'Le verbe s\'accorde avec son sujet : « {arg} ».',
            'fr.participle_subject': "Avec être, le participe passé s'accorde avec le sujet : « {arg} ».",
            'fr.participle_object': "Avec avoir, le participe passé s'accorde avec le COD placé avant : « {arg} ».",
            'fr.attribute': "L'adjectif s'accorde avec le sujet : « {arg} ».",
            'fr.subject_noun_verb': "Le verbe s'accorde avec son sujet : « {arg} ».",
            'fr.tout': "« tout » s'accorde avec ce qui suit : « {arg} ».",
            'fr.possessive_vowel': 'Devant une voyelle, le possessif est « {arg} ».',
            'fr.preposition': 'Construction correcte : « {arg} ».',
            'fr.si_tense': 'Après « si » (condition), ni conditionnel ni futur : « {arg} ».',
            'fr.subjunctive': 'Cette tournure veut le subjonctif : « {arg} ».',
            'fr.indicative_after': "Après « après que », la règle est l'indicatif : « {arg} ».",
            'fr.participle_invariable': 'Avec avoir, sans COD placé avant, le participe passé reste invariable : « {arg} ».',
            'fr.ce_se': 'Confusion entre « ce » et « se » : « {arg} ».',
            'fr.a_accent': "« à » (préposition) s'écrit avec un accent ici.",
            'fr.ou_where': "« où » (lieu ou temps) s'écrit avec un accent.",
            'fr.leur': '« leur » est au singulier et « leurs » au pluriel, comme le nom : « {arg} ».',
            'fr.la_there': "« là » (lieu) s'écrit avec un accent.",
            'fr.sa_ca': "Ici, c'est le pronom « ça », pas le déterminant « sa ».",
            'fr.cest_sest': "Avec un verbe pronominal, on écrit « s'est », pas « c'est ».",
            'fr.et_est': '« {arg} » (verbe être), pas « et » (conjonction).',
            'fr.peu_peut': '« peut » (verbe pouvoir), pas « peu » (adverbe).',
            'fr.ma_ma': "« {arg} » : le pronom et l'auxiliaire avoir, pas le déterminant.",
        },
        'es': {
            'fr.a': '"à" es una preposición; después de "il", "elle" u "on" es el verbo avoir: "a".',
            'fr.ont': 'Después de "ils" o "elles", el verbo avoir se escribe "ont".',
            'fr.sont': 'Después de "ils", "elles", "ceux" o "celles", el verbo être se escribe "sont".',
            'fr.participle': 'Después de un auxiliar (avoir o être) el verbo es un participio: "{arg}".',
            'fr.infinitive': 'Después de "pour", "sans" o un verbo como pouvoir, vouloir, devoir o aller, el verbo va en infinitivo: "{arg}".',
            'fr.phrase': 'Forma correcta: "{arg}".',
            'fr.det_number': 'El determinante y el nombre no concuerdan en número: "{arg}".',
            'fr.det_gender': 'El determinante no concuerda en género con el nombre: "{arg}".',
            'fr.noun_adjective': 'El adjetivo concuerda en género y número con el nombre: "{arg}".',
            'fr.subject_verb': 'El verbo concuerda con su sujeto: "{arg}".',
            'fr.participle_subject': 'Con être, el participio concuerda con el sujeto: "{arg}".',
            'fr.participle_object': 'Con avoir, el participio concuerda con el complemento directo colocado antes: "{arg}".',
            'fr.attribute': 'El adjetivo concuerda con el sujeto: "{arg}".',
            'fr.subject_noun_verb': 'El verbo concuerda con su sujeto: "{arg}".',
            'fr.tout': '"tout" concuerda con lo que sigue: "{arg}".',
            'fr.possessive_vowel': 'Ante una vocal el posesivo es "{arg}".',
            'fr.preposition': 'Construcción correcta: "{arg}".',
            'fr.si_tense': 'Después de "si" (condición) ni condicional ni futuro: "{arg}".',
            'fr.subjunctive': 'Esta construcción pide el subjuntivo: "{arg}".',
            'fr.indicative_after': 'Después de "après que" la regla es el indicativo: "{arg}".',
            'fr.participle_invariable': 'Con avoir, sin complemento directo antes, el participio no concuerda: "{arg}".',
            'fr.ce_se': 'Confusión entre "ce" y "se": "{arg}".',
            'fr.a_accent': '"à" (preposición) lleva acento aquí.',
            'fr.ou_where': '"où" (lugar o tiempo) lleva acento.',
            'fr.leur': '"leur" es singular y "leurs" plural, como el nombre: "{arg}".',
            'fr.la_there': '"là" (lugar) lleva acento.',
            'fr.sa_ca': 'Aquí es el pronombre "ça", no el determinante "sa".',
            'fr.cest_sest': 'Con un verbo pronominal se escribe "s\'est", no "c\'est".',
            'fr.et_est': '"{arg}" (verbo être), no "et" (y).',
            'fr.peu_peut': '"peut" (verbo pouvoir), no "peu" (poco).',
            'fr.ma_ma': '"{arg}": el pronombre y el auxiliar avoir, no el determinante.',
        },
    }

    # [SECTION] Helpers

    def opens_clause(self, p, i):
        """The word starts a clause: first of the paragraph, after a punctuation mark or after a conjunction."""
        return i == 0 or p[i - 1].kind == 'punct' or (p[i - 1].kind == 'word' and p[i - 1].low in STARTERS)

    def plain_word(self, p, i):
        """A word which is not a proper name (a capital letter inside a sentence)."""
        return p.word(i) and not (p[i].text[0].isupper() and i > 0)

    @staticmethod
    def det_disagrees(det, number):
        """The determiner and the noun differ in number: the noun is wrong, so no other rule may rely on its number."""
        return (det in PLURAL_DETS and number == lx.SINGULAR) or (det in SINGULAR_DETS and number == lx.PLURAL)

    @staticmethod
    def starts_with_vowel(low):
        """True when a word starts with a vowel letter or an h (the h is not checked)."""
        return low.startswith(('a', 'e', 'i', 'o', 'u', 'y', 'h', 'à', 'â', 'é', 'è', 'ê', 'î', 'ô', 'û'))

    @staticmethod
    def noun_only(an):
        """(is_noun_only, gender, number): gender and number are 0 when the readings differ."""
        if not an:
            return False, 0, 0
        gender, number = an[0].gender, an[0].number
        for a in an:
            if a.pos != lx.NOUN:
                return False, 0, 0
            if a.gender != gender:
                gender = 0
            if a.number != number:
                number = 0
        return True, gender, number

    def noun_after_determiner(self, t, i, prev_word):
        """The word after "le", "la", "les" at i is a noun although it is also a finite verb form ("les pomme sont", "mangé les pomme"):
        another finite verb follows it, or what stands before "les" cannot be a subject (a preposition, a participle or an infinitive)."""
        after = t[i + 2] if i + 2 < len(t) else None
        if after is not None and after.kind == 'word' and tg.only(after, lx.VERB | lx.AUX) and any(a.verb_form in tg.FINITE for a in after.tags):
            return True
        if prev_word is not None:
            if prev_word.low in self.PREPOSITIONS:
                return True
            return tg.has(prev_word, lx.VERB | lx.AUX) and not tg.has(prev_word, lx.NOUN | lx.PRON) and not any(a.verb_form in tg.FINITE for a in prev_word.tags)
        return False

    # [SECTION] Tagger: constraints which choose the reading of a word from its neighbours

    SUBJECT_WORDS = {'je', "j'", 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles', 'ce', "c'", 'ça', 'cela', 'qui'}
    OBJECT_CLITICS = {'me', "m'", 'te', "t'", 'se', "s'", 'lui', 'y', 'en', 'leur'}
    PREPOSITIONS = {'sur', 'dans', 'avec', 'chez', 'sous', 'vers', 'par', 'entre', 'contre', 'depuis', 'pendant', 'après', 'avant', 'devant', 'derrière', 'selon', 'malgré', 'sans', 'pour', 'de', "d'", 'du', 'à', 'au', 'aux', 'en'}
    PREPOSITIONS_ONLY = {'sur', 'dans', 'avec', 'chez', 'sous', 'vers', 'entre', 'contre', 'depuis', 'pendant', 'après', 'avant', 'devant', 'derrière', 'selon', 'malgré', 'sans', 'pour'}
    MODALS = {'pouvoir', 'vouloir', 'devoir', 'aller', 'savoir', 'falloir', 'faire', 'laisser', 'sembler', 'oser', 'désirer', 'espérer', 'préférer', 'venir'}

    # Determiners which the lexicon labels as "other" (possessives, demonstratives): read as determiners before a word
    DETERMINER_WORDS = {'ces', 'mes', 'tes', 'ses', 'nos', 'vos', 'mon', 'ton', 'ma', 'ta', 'sa', 'cette', 'cet', 'notre', 'votre', 'chaque', 'quelques', 'ce', 'leurs', 'son'}
    NOT_BEFORE_DETERMINER = {'ils', 'elles', 'ceux', 'celles', 'qui', 'il', 'elle', 'on', 'je', "j'", 'tu', 'nous', 'vous', 'ne', "n'", 'me', "m'", 'te', "t'", 'se', "s'", 'lui', 'y', 'en'}

    def read_determiners(self, p):
        """Gives the readings of a determiner to the possessives and demonstratives, and to "un", "une", when a word follows."""
        t = p.tokens
        for i, w in enumerate(t):
            if w.kind != 'word' or i + 1 >= len(t) or not t[i + 1].kind == 'word' or not t[i + 1].space_before:
                continue
            if w.low in ('un', 'une') and t[i + 1].low not in ('de', "d'", 'à', 'et', 'ou') and (i == 0 or t[i - 1].kind != 'word' or t[i - 1].low != 'pas'):
                tg.keep(w, lx.DET)
            elif w.low in self.DETERMINER_WORDS and (i == 0 or t[i - 1].kind != 'word' or t[i - 1].low not in self.NOT_BEFORE_DETERMINER):
                nxt = t[i + 1]
                if w.low in ('son', 'leurs', 'ce', 'nos', 'ton') and not (nxt.tags and tg.has(nxt, lx.NOUN | lx.ADJ)):
                    continue            # the readings stay: "ce sont", "il ton"
                det = tuple(a._replace(pos=lx.DET) for a in w.tags if a.pos & lx.OTHER)
                if det:
                    w.tags = det + tuple(a for a in w.tags if a.pos & lx.PRON and w.low == 'ce')

    def disambiguate(self, p):
        """Tagger constraints: the reading of a word from its neighbours (determiner, subject pronoun, auxiliary, modal verb, preposition)."""
        lex = self.core.lexicon
        t = p.tokens
        self.read_determiners(p)
        for i in range(len(t)):
            w = t[i]
            if w.kind != 'word' or len(w.tags) < 2 and not (w.low in ('le', 'la', 'les', "l'")):
                continue
            if w.low in self.PREPOSITIONS_ONLY:
                tg.keep(w, lx.ADP)
                continue
            prev = t[i - 1] if i > 0 else None
            prev_word = prev if prev is not None and prev.kind == 'word' else None

            # "le", "la", "les", "l'": a determiner before a noun, a pronoun before a verb
            if w.low in ('le', 'la', 'les', "l'"):
                nxt = t[i + 1] if i + 1 < len(t) else None
                if prev_word and (prev_word.low in self.SUBJECT_WORDS or prev_word.low in ('ne', "n'") or prev_word.low in self.OBJECT_CLITICS):
                    tg.keep(w, lx.PRON)
                elif nxt is not None and nxt.kind == 'word' and nxt.tags:
                    finite = any(a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE for a in nxt.tags)
                    infinitive = any(a.pos & (lx.VERB | lx.AUX) and a.verb_form == lx.INFINITIVE for a in nxt.tags)
                    noun = tg.has(nxt, lx.NOUN | lx.ADJ)
                    before_verb = prev_word and (tg.only(prev_word, lx.VERB | lx.AUX) or prev_word.low in ('à', 'de', "d'", 'pour', 'sans', 'par', 'afin', 'après'))
                    if infinitive and before_verb:
                        tg.keep(w, lx.PRON)         # "veux le manger", "sans les toucher"
                    elif finite and (tg.only(nxt, lx.VERB | lx.AUX) or (prev_word and tg.only(prev_word, lx.PROPN))):
                        tg.keep(w, lx.PRON)         # "Castellan la vit"
                    elif noun and not infinitive and (not finite or self.noun_after_determiner(t, i, prev_word)):
                        tg.keep(w, lx.DET)          # a noun after it; when the noun is also a verb form ("les pomme"), the context decides
                continue

            if prev_word is None:
                continue
            before = prev_word.low

            # After a determiner: a noun or an adjective
            if tg.only(prev_word, lx.DET):
                tg.keep(w, lx.NOUN | lx.ADJ | lx.PROPN)
                continue
            # Determiner, adjective of the kind which goes before the noun, then the noun: "les grandes pomme"
            if i >= 2 and tg.only(t[i - 2], lx.DET) and t[i - 2].kind == 'word' and any(a.pos & lx.ADJ and lex.lemma(a) in ANTEPOSED for a in prev_word.tags) and tg.has(w, lx.NOUN) and not tg.has(w, lx.DET | lx.PRON):
                tg.keep(w, lx.NOUN | lx.ADJ)
                continue
            # A subject, with its clitics, then a conjugated verb
            k = i - 1
            while k > 0 and t[k].kind == 'word' and (t[k].low in CLITICS or t[k].low in ('ne', "n'")):
                k -= 1
            subject = t[k].kind == 'word' and t[k].low in self.SUBJECT_WORDS and (k == 0 or t[k - 1].kind == 'punct' or t[k - 1].low in STARTERS or t[k].low in ('je', "j'", 'il', 'elle', 'ils', 'elles', 'on', 'tu'))
            if subject or before in ('ne', "n'") or before in self.OBJECT_CLITICS:
                if tg.select(w, lambda a: bool(a.pos & (lx.VERB | lx.AUX)) and a.verb_form in tg.FINITE):
                    tg.keep(w, lx.VERB | lx.AUX)
                    continue
            # After an auxiliary: a past participle, else an adjective
            if before in AUXILIARIES and any(a.pos & lx.AUX for a in prev_word.tags):
                if tg.select(w, lambda a: bool(a.pos & lx.VERB) and a.verb_form == lx.PAST_PARTICIPLE):
                    continue
                if tg.keep(w, lx.ADJ):
                    continue
            # After a modal verb, "pour" or "sans": an infinitive
            m = i - 1                   # the pronouns between the modal verb and the verb are skipped
            while m > 0 and t[m].kind == 'word' and (t[m].low in ('le', 'la', 'les', "l'") or t[m].low in self.OBJECT_CLITICS) and tg.has(t[m], lx.PRON):
                m -= 1
            if (before in ('pour', 'sans') or any(a.pos & lx.VERB and lex.lemma(a) in self.MODALS and a.verb_form in tg.FINITE for a in t[m].tags)) and tg.has(w, lx.VERB):
                if tg.select(w, lambda a: a.verb_form == lx.INFINITIVE):
                    continue
            # After a preposition: not a conjugated verb
            if before in self.PREPOSITIONS and tg.has(w, lx.NOUN | lx.PRON | lx.PROPN | lx.ADJ | lx.DET):
                tg.drop(w, lx.VERB | lx.AUX)

    # [SECTION] Agreement of the past participle

    def participle_at(self, p, i):
        """Index of the past participle which follows the auxiliary at i (adverbs may stand between), else -1."""
        j = i + 1
        while p.word(j) and p[j].low in BETWEEN and j < i + 3:
            j += 1
        if not p.word(j):
            return -1
        w = p[j]
        if not any(a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE for a in w.tags):
            return -1
        if any(a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE for a in w.tags):
            return -1
        return j

    def check_participle(self, p, j, genders, number, rule_id, object_check=False):
        """The participle at j must fit one of the genders and the number: reports the form which does."""
        lex = self.core.lexicon
        w = p[j]
        readings = [a for a in w.tags if a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE]
        if any(lex.lemma(a) in INVARIABLE_VERBS for a in readings):
            return
        if p.word(j + 1) and any(a.verb_form == lx.INFINITIVE for a in p[j + 1].tags):
            return                      # "je les ai vu partir": invariable before an infinitive
        if object_check and p.word(j + 1) and p[j + 1].low in ('de', "d'", 'à', 'comment', 'pourquoi', 'si', 'que', "qu'", 'quoi', 'où', 'ce'):
            return                      # the object is what follows ("fini de comprendre", "su comment"), not the word before
        for a in readings:
            if a.number in (number, lx.INVARIABLE) and (a.gender in (0, lx.EPICENE) or a.gender in genders):
                return
        model = readings[0]
        gender = genders[0] if len(genders) == 1 else (model.gender if model.gender in genders else genders[0])
        form = lex.inflect(model, gender, number, 0, lx.PAST_PARTICIPLE)
        if form and form != w.low:
            p.add(rule_id, w, w, match_case(w.text, form), form)

    @rule('fr.participle_subject', 'agreement', 0.8)
    def participle_subject(self, p):
        """With être the past participle agrees with the subject: elle est parti -> partie"""
        if not self.core.lexicon:
            return
        for i in range(1, len(p)):
            if not p.word(i) or p[i].low not in ETRE_FORMS or not any(a.pos & lx.AUX for a in p[i].tags):
                continue
            j = self.participle_at(p, i)
            if j < 0:
                continue
            k = i - 1
            while k > 0 and p[k].kind == 'word' and p[k].low in ('ne', "n'", 'y', 'en'):
                k -= 1
            # A pronominal verb: "elle s'est lavée", "je me suis levé". The participle agrees with the subject when the reflexive
            # pronoun is the direct object: not when a direct object follows ("elle s'est lavé les mains") nor with the verbs
            # which take an indirect object ("elles se sont parlé").
            reflexive = p.word(k) and p[k].low in ('se', "s'", 'me', "m'", 'te', "t'")
            if reflexive:
                clitic = p[k].low
                k -= 1
                while k > 0 and p[k].kind == 'word' and p[k].low in ('ne', "n'"):
                    k -= 1
                if (p.word(j + 1) and tg.has(p[j + 1], lx.DET)) or not any(self.core.lexicon.lemma(a) in PRONOMINAL_VERBS for a in p[j].tags if a.pos & lx.VERB):
                    continue
                if not p.word(k) or (clitic in ('me', "m'") and p[k].low not in ('je', "j'")) or (clitic in ('te', "t'") and p[k].low != 'tu') or \
                        (clitic in ('se', "s'") and p[k].low in ('je', "j'", 'tu', 'nous', 'vous', 'on')):
                    continue
            subject = SUBJECT_FEATURES.get(p[k].low) if p.word(k) else None
            if subject and k > 0 and not (p[k - 1].kind == 'punct' or p[k - 1].low in SUBJECT_STARTERS or p[k - 1].low in ('ne', "n'")):
                subject = None          # an object pronoun: "sous elle est parti"
            if subject is None and p.word(k) and k >= 1 and tg.only(p[k], lx.NOUN) and tg.only(p[k - 1], lx.DET):
                ok, gender, number = self.noun_only(p[k].tags)
                if ok and gender != 0 and number in (lx.SINGULAR, lx.PLURAL) and not self.det_disagrees(p[k - 1].low, number) and (k == 1 or p[k - 2].kind == 'punct' or p[k - 2].low in SUBJECT_STARTERS):
                    subject = ((1, 2) if gender == lx.EPICENE else (gender,), number)
            if subject:
                self.check_participle(p, j, subject[0], subject[1], 'fr.participle_subject')

    @rule('fr.participle_object', 'agreement', 0.75)
    def participle_object(self, p):
        """With avoir the past participle agrees with a direct object placed before: je les ai mangé -> mangés"""
        lex = self.core.lexicon
        if not lex:
            return
        for i in range(1, len(p)):
            if not p.word(i) or p[i].low not in AUXILIARIES or not any(a.pos & lx.AUX and lex.lemma(a) == 'avoir' for a in p[i].tags):
                continue
            j = self.participle_at(p, i)
            if j < 0:
                continue
            k = i - 1
            if p.word(k) and p[k].low == 'les' and tg.has(p[k], lx.PRON):
                self.check_participle(p, j, (1, 2), 2, 'fr.participle_object', True)
                continue
            # A relative "que": "les pommes que j'ai mangé" -> mangées. The noun before "que" is the object and fixes the agreement.
            # Nouns which take a clause ("l'idée que j'ai eu") are left alone: there "que" is a conjunction.
            while k > 0 and p.word(k) and p[k].low in ('ne', "n'", 'y', 'en'):
                k -= 1
            if k >= 3 and p.word(k) and p[k].low in SUBJECT_FEATURES and p[k - 1].low in ('que', "qu'") and p.word(k - 2) and tg.has(p[k - 3], lx.DET):
                if k >= 4 and p[k - 4].kind == 'word' and p[k - 4].low in ('de', "d'", 'du', 'des', 'à', 'au', 'aux'):
                    continue            # "la ligne de son carnet qu'elle a effacée": the antecedent may be the first noun
                noun = p[k - 2]
                readings = [a for a in noun.tags if a.pos & lx.NOUN]
                genders, numbers = {a.gender for a in readings}, {a.number for a in readings}
                gender, number = (genders.pop() if len(genders) == 1 else 0), (numbers.pop() if len(numbers) == 1 else 0)
                if readings and gender != 0 and number in (lx.SINGULAR, lx.PLURAL) and noun.low not in CLAUSE_NOUNS:
                    self.check_participle(p, j, (1, 2) if gender == lx.EPICENE else (gender,), number, 'fr.participle_object', True)

    @rule('fr.participle_invariable', 'agreement', 0.7)
    def participle_invariable(self, p):
        """With avoir and no direct object before, the participle does not agree: elle a mangées -> mangé"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(1, len(t)):
            if not p.word(i) or t[i].low not in AUXILIARIES or not any(a.pos & lx.AUX and lex.lemma(a) == 'avoir' for a in t[i].tags):
                continue
            j = self.participle_at(p, i)
            if j < 0:
                continue
            start = i
            while start > 0 and t[start - 1].kind != 'punct' and t[start - 1].low not in ('et', 'ou', 'mais', 'car', 'donc', 'alors', 'ni'):
                start -= 1
            if any(t[k].low in OBJECT_WORDS for k in range(start, i)):
                continue                # an object may stand before: the agreement is right
            readings = [a for a in t[j].tags if a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE]
            if not readings or any(a.gender in (0, lx.MASCULINE, lx.EPICENE) and a.number in (lx.SINGULAR, lx.INVARIABLE) for a in readings):
                continue
            form = lex.inflect(readings[0], lx.MASCULINE, lx.SINGULAR, 0, lx.PAST_PARTICIPLE)
            if form and form != t[j].low:
                p.add('fr.participle_invariable', t[j], t[j], match_case(t[j].text, form), form)

    # [SECTION] More agreements: attribute, noun subject, adjective before the noun, "tout", possessive before a vowel

    def subject_before(self, p, i, pronoun_only_number=False):
        """(genders, number) of the simple subject which stands before the verb at i, else None."""
        k = i - 1
        while k > 0 and p[k].kind == 'word' and p[k].low in ('ne', "n'", 'y', 'en'):
            k -= 1
        if not p.word(k):
            return None
        if p[k].low in SUBJECT_FEATURES:
            # a pronoun which is not at the start of its clause is an object: "le granit sous elle était froid"
            return SUBJECT_FEATURES[p[k].low] if (k == 0 or p[k - 1].kind == 'punct' or p[k - 1].low in SUBJECT_STARTERS or p[k - 1].low in ('ne', "n'")) else None
        if k >= 1 and tg.only(p[k], lx.NOUN) and tg.only(p[k - 1], lx.DET) and p[k].low not in COLLECTIVES and (k == 1 or p[k - 2].kind == 'punct' or p[k - 2].low in SUBJECT_STARTERS):
            ok, gender, number = self.noun_only(p[k].tags)
            if ok and gender != 0 and number in (lx.SINGULAR, lx.PLURAL) and not self.det_disagrees(p[k - 1].low, number):
                return ((1, 2) if gender == lx.EPICENE else (gender,), number)
        return None

    def adjective_fits(self, readings, genders, number):
        """True when one of the readings is an adjective which agrees with the genders and the number."""
        return any(a.pos & lx.ADJ and a.gender in (0, lx.EPICENE, *genders) and a.number in (number, lx.INVARIABLE) for a in readings)

    @rule('fr.attribute', 'agreement', 0.75)
    def attribute(self, p):
        """The adjective after être agrees with the subject: elle est grand -> grande, les filles sont content -> contentes"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(1, len(t)):
            if not p.word(i) or t[i].low not in LINK_VERBS or not any(a.pos & (lx.VERB | lx.AUX) for a in t[i].tags):
                continue
            k = i - 1
            while k > 0 and t[k].kind == 'word' and t[k].low in ('ne', "n'", 'y', 'en'):
                k -= 1
            if not p.word(k) or t[k].low in ('nous', 'vous', 'on', 'se', "s'", 'ce', "c'"):
                continue
            subject = self.subject_before(p, i)
            if not subject:
                continue
            j = i + 1
            while p.word(j) and t[j].low in DEGREE_ADVERBS and j < i + 4:
                j += 1
            if not p.word(j):
                continue
            adj = t[j]
            if adj.low in COLORS or any(a.verb_form == lx.PAST_PARTICIPLE for a in adj.tags):
                continue                # colours are often invariable; participles have their own rule
            if any(a.pos & ~(lx.ADJ | lx.NOUN) for a in adj.tags) or not any(a.pos & lx.ADJ for a in adj.tags):
                continue
            nxt = t[j + 1] if j + 1 < len(t) else None
            if nxt is not None and nxt.kind == 'word' and tg.has(nxt, lx.NOUN) and not tg.has(nxt, lx.VERB | lx.AUX | lx.ADJ):
                continue                # "elle est grande fille": not an attribute
            genders, number = subject
            if self.adjective_fits(adj.tags, genders, number):
                continue
            model = next(a for a in adj.tags if a.pos & lx.ADJ)
            gender = genders[0] if len(genders) == 1 else (model.gender if model.gender in genders else genders[0])
            form = lex.inflect(model, gender, number, 0, 0)
            if form and form != adj.low:
                p.add('fr.attribute', adj, adj, match_case(adj.text, form), form)

    @rule('fr.subject_noun_verb', 'agreement', 0.7)
    def subject_noun_verb(self, p):
        """A noun subject and its verb: les chats dort -> dorment"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for k in range(1, len(t) - 1):
            if not p.word(k) or not tg.only(t[k - 1], lx.DET) or not tg.only(t[k], lx.NOUN) or t[k].low in COLLECTIVES:
                continue
            if not (k == 1 or t[k - 2].kind == 'punct' or t[k - 2].low in SUBJECT_STARTERS):
                continue
            ok, gender, number = self.noun_only(t[k].tags)
            if not ok or number not in (lx.SINGULAR, lx.PLURAL) or self.det_disagrees(t[k - 1].low, number):
                continue
            v = k + 1
            if p.word(v) and tg.has(t[v], lx.ADJ) and not tg.has(t[v], lx.VERB | lx.AUX) and p.word(v + 1):
                v += 1                  # "les chats noirs dorment"
            if not p.word(v) or not tg.only(t[v], lx.VERB | lx.AUX):
                continue
            finite = [a for a in t[v].tags if a.verb_form in tg.FINITE]
            if not finite or any(a.person == 3 and a.number == number for a in finite):
                continue
            form = lex.inflect(finite[0], 0, number, 3, finite[0].verb_form)
            if form and form != t[v].low:
                p.add('fr.subject_noun_verb', t[v], t[v], match_case(t[v].text, form), form)

    @rule('fr.noun_adjective', 'agreement', 0.75, emits=('fr.det_number',))
    def adjective_before(self, p):
        """A determiner, an adjective which goes before the noun, the noun: une grand maison -> grande, les grands maison -> maisons"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 2):
            if not (p.word(i) and p.word(i + 1) and p.word(i + 2)) or not t[i + 2].space_before or not t[i + 1].space_before:
                continue
            det, adj, noun = t[i], t[i + 1], t[i + 2]
            if not tg.has(det, lx.DET) or not (det.low in PLURAL_DETS or det.low in SINGULAR_DETS) or noun.text[0].isupper():
                continue
            if not any(a.pos & lx.ADJ and lex.lemma(a) in ANTEPOSED for a in adj.tags):
                continue
            ok, gender, number = self.noun_only(noun.tags or lex.analyses(noun.text))
            if not ok or gender == 0 or number not in (lx.SINGULAR, lx.PLURAL):
                continue
            genders = (1, 2) if gender == lx.EPICENE else (gender,)
            wanted = lx.PLURAL if det.low in PLURAL_DETS else lx.SINGULAR
            if number != wanted:
                noun_an = noun.tags or lex.analyses(noun.text)
                form = lex.inflect(noun_an[0], 0, wanted, 0, 0)
                if form and form != noun.low:
                    p.add('fr.det_number', noun, noun, match_case(noun.text, form), form)
                continue
            if self.starts_with_vowel(noun.low) and wanted == lx.SINGULAR and gender == lx.MASCULINE:
                continue                # "un bel arbre": the adjective changes before a vowel
            if self.adjective_fits(adj.tags, genders, wanted):
                continue
            model = next(a for a in adj.tags if a.pos & lx.ADJ and lex.lemma(a) in ANTEPOSED)
            form = lex.inflect(model, genders[0] if len(genders) == 1 else (model.gender if model.gender in genders else 1), wanted, 0, 0)
            if form and form != adj.low:
                p.add('fr.noun_adjective', adj, adj, match_case(adj.text, form), form)

    @rule('fr.tout', 'agreement', 0.8)
    def tout(self, p):
        """tout les jours -> tous les jours, toute les semaines -> toutes, tous le monde -> tout le monde"""
        lex = self.core.lexicon
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)) or not t[i + 1].space_before:
                continue
            w, nxt = t[i].low, t[i + 1].low
            if w in ('tout', 'toute') and i > 0 and t[i - 1].low in ('du', 'de', 'au', 'en', 'pas', 'à', 'près', 'tant'):
                continue                # "pas du tout les mêmes", "en tout les deux"
            if w in ('tout', 'toute') and nxt in ('les', 'ces', 'mes', 'tes', 'ses', 'nos', 'vos', 'leurs'):
                feminine = False
                if lex and i + 2 < len(t) and p.word(i + 2):
                    ok, gender, number = self.noun_only(lex.analyses(t[i + 2].text))
                    feminine = ok and gender == lx.FEMININE
                fix = 'toutes' if feminine or w == 'toute' and not lex else 'tous'
                if w == 'toute' and not lex:
                    fix = 'toutes'
                p.add('fr.tout', t[i], t[i], match_case(t[i].text, fix), fix)
            elif w in ('tous', 'toutes') and nxt in ('le', 'la') and i + 2 < len(t) and p.word(i + 2) and t[i + 2].low == 'monde':
                p.add('fr.tout', t[i], t[i], match_case(t[i].text, 'tout'), 'tout')

    @rule('fr.possessive_vowel', 'spelling', 0.8)
    def possessive_vowel(self, p):
        """ma amie -> mon amie, sa énorme erreur -> son énorme erreur"""
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)) or t[i].low not in ('ma', 'ta', 'sa') or not t[i + 1].space_before:
                continue
            nxt = t[i + 1].low
            if nxt[0] in 'aeiouyàâéèêîôû' and tg.has(t[i + 1], lx.NOUN | lx.ADJ):
                fix = {'ma': 'mon', 'ta': 'ton', 'sa': 'son'}[t[i].low]
                p.add('fr.possessive_vowel', t[i], t[i], match_case(t[i].text, fix), fix)

    # [SECTION] Sequence of tenses: "si" and the mood after a conjunction

    SI_CLAUSE_BLOCKERS = {'savoir', 'demander', 'ignorer', 'douter', 'vérifier', 'dire', 'découvrir', 'comprendre', 'voir', 'regarder', 'chercher', 'essayer', 'apprendre',
                          'expliquer', 'décider', 'rappeler', 'se demander', 'tester', 'imaginer', 'savoir'}
    SUBJUNCTIVE_TRIGGERS = [('il', 'faut'), ('il', 'faudrait'), ('il', 'vaut', 'mieux'), ('il', 'se', 'peut'), ('bien',), ('pour',), ('afin',), ('avant',), ('sans',),
                            ('à', 'moins'), ('pourvu',), ("jusqu'", 'à', 'ce'), ('de', 'peur'), ('de', 'crainte'), ('en', 'attendant'), ('à', 'condition'),
                            ('je', 'veux'), ('je', 'voudrais'), ('je', 'souhaite'), ("j'", 'aimerais'), ("j'", 'exige'), ('je', 'préfère'), ('je', 'crains'), ('je', 'doute'),
                            ("j'", 'ai', 'peur'), ('je', 'regrette'), ('tu', 'veux'), ('il', 'veut'), ('elle', 'veut'), ('nous', 'voulons'), ('vous', 'voulez'), ('ils', 'veulent')]
    WHOLE_TRIGGERS = [('quoique',), ("quoiqu'",)]

    def verb_after(self, p, start):
        """Index of the verb which follows (after "ne" and the pronouns), with its subject pronoun: (subject index, verb index) or None."""
        t = p.tokens
        k = start
        while p.word(k) and t[k].low in ('ne', "n'"):
            k += 1
        if not p.word(k) or t[k].low not in SUBJECT_PRONOUNS:
            return None
        v = k + 1
        while p.word(v) and (t[v].low in CLITICS or t[v].low in ('ne', "n'")) and v < k + 5:
            v += 1
        return (k, v) if p.word(v) else None

    @rule('fr.si_tense', 'conjugation', 0.75)
    def si_tense(self, p):
        """After "si" (a condition) neither the conditional nor the future: si j'aurais su -> si j'avais su"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i, w in enumerate(t):
            if not w.kind == 'word' or w.low not in ('si', "s'"):
                continue
            if w.low == "s'" and not (p.word(i + 1) and t[i + 1].low in ('il', 'ils')):
                continue
            found = self.verb_after(p, i + 1)
            if not found:
                continue
            k, v = found
            # An indirect question keeps its tenses: "je ne sais pas si tu viendras"
            start = i
            while start > 0 and not (t[start - 1].kind == 'punct' and t[start - 1].text in '.!?;:'):
                start -= 1
            if any(lex.lemma(a) in self.SI_CLAUSE_BLOCKERS for m in range(max(start, i - 25), i) if p.word(m) for a in t[m].tags if a.pos & (lx.VERB | lx.AUX)):
                continue
            finite = [a for a in t[v].tags if a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE]
            if not finite:
                continue
            forms = {a.verb_form for a in finite}
            if forms <= {lx.CONDITIONAL}:
                target = lx.IMPERFECT
            elif forms <= {lx.FUTURE}:
                target = lx.PRESENT
            else:
                continue
            person, number = SUBJECT_PRONOUNS[t[k].low]
            form = lex.inflect(finite[0], 0, number, person, target)
            if form and form != t[v].low:
                p.add('fr.si_tense', t[v], t[v], match_case(t[v].text, form), form)

    @rule('fr.subjunctive', 'conjugation', 0.7, emits=('fr.indicative_after',))
    def mood_after_conjunction(self, p):
        """After "il faut que", "bien que", "pour que"... the subjunctive; after "après que" the indicative."""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t)):
            for trigger in self.SUBJUNCTIVE_TRIGGERS + [('après',)] + self.WHOLE_TRIGGERS:
                n = len(trigger)
                if i + n > len(t) or any(not p.word(i + m) or t[i + m].low != trigger[m] for m in range(n)):
                    continue
                after = i + n
                if trigger not in self.WHOLE_TRIGGERS:
                    if not (p.word(after) and t[after].low in ('que', "qu'")):
                        continue
                    after += 1
                found = self.verb_after(p, after)
                if not found:
                    continue
                k, v = found
                finite = [a for a in t[v].tags if a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE]
                if not finite:
                    continue
                person, number = SUBJECT_PRONOUNS[t[k].low]
                subjunctive = [a for a in finite if a.verb_form in (lx.SUBJUNCTIVE_PRESENT, lx.SUBJUNCTIVE_IMPERFECT)]
                if trigger == ('après',):
                    if subjunctive and len(subjunctive) == len(finite):
                        form = lex.inflect(subjunctive[0], 0, number, person, lx.PRESENT)
                        if form and form != t[v].low:
                            p.add('fr.indicative_after', t[v], t[v], match_case(t[v].text, form), form, 0.5)
                elif not subjunctive:
                    model = next((a for a in finite if a.verb_form in (lx.PRESENT, lx.FUTURE, lx.CONDITIONAL, lx.IMPERFECT)), None)
                    if model:
                        form = lex.inflect(model, 0, number, person, lx.SUBJUNCTIVE_PRESENT)
                        if form and form != t[v].low:
                            p.add('fr.subjunctive', t[v], t[v], match_case(t[v].text, form), form)
                break

    # [SECTION] Prepositions which a verb or an adjective does not take

    @rule('fr.preposition', 'syntax', 0.75)
    def preposition(self, p):
        """essayer à faire -> essayer de faire, apprendre de lire -> apprendre à lire, pallier à -> pallier, différent que -> différent de"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens

        def lemmas(tok):
            return {lex.lemma(a) for a in tok.tags if a.pos & (lx.VERB | lx.AUX | lx.ADJ) and a.lemma >= 0}

        for i in range(len(t) - 2):
            verb, prep, nxt = t[i], t[i + 1], t[i + 2]
            if not (p.word(i) and p.word(i + 1) and p.word(i + 2)):
                continue
            found = lemmas(verb)
            infinitive = any(a.pos & lx.VERB and a.verb_form == lx.INFINITIVE for a in lex.analyses(nxt.text)) and not tg.has(nxt, lx.DET)    # the tagger took it for a noun after a preposition
            # an infinitive after the wrong preposition
            if prep.low == 'à' and infinitive and found & VERBS_DE:
                new = "d'" if self.starts_with_vowel(nxt.low) else 'de '
                p.add_range('fr.preposition', prep.start, nxt.start, new, '%s %s' % (verb.text, new.strip()))
            elif prep.low in ('de', "d'") and infinitive and found & VERBS_A:
                p.add_range('fr.preposition', prep.start, nxt.start, 'à ', '%s à' % verb.text)
            # "pallier à la pénurie" -> "pallier la pénurie"
            elif prep.low == 'à' and 'pallier' in found:
                p.add_range('fr.preposition', verb.end, prep.end, '', '%s %s' % (verb.text, nxt.text))
            # "se rappeler de la chanson" -> "se rappeler la chanson"
            elif prep.low in ('de', "d'") and 'rappeler' in found and i > 0 and t[i - 1].low in ('me', "m'", 'te', "t'", 'se', "s'", 'nous', 'vous') and tg.has(nxt, lx.DET):
                p.add_range('fr.preposition', verb.end, prep.end, '', '%s %s' % (verb.text, nxt.text))
            # "différent que" -> "différent de", "identique que" -> "identique à"
            elif prep.low == 'que' and found & set(ADJECTIVES_PREPOSITION):
                right = ADJECTIVES_PREPOSITION[next(iter(found & set(ADJECTIVES_PREPOSITION)))]
                p.add('fr.preposition', prep, prep, right, '%s %s' % (verb.text, right))

    # [SECTION] Homophones, chosen with the readings left by the tagger

    HOMOPHONES = ('fr.ce_se', 'fr.a_accent', 'fr.ou_where', 'fr.leur', 'fr.la_there', 'fr.sa_ca', 'fr.cest_sest', 'fr.et_est', 'fr.peu_peut', 'fr.ma_ma')
    ETRE_ALLER = {'est', 'suis', 'es', 'sommes', 'êtes', 'sont', 'va', 'vais', 'vas', 'vont', 'allons', 'allez', 'reste', 'restes', 'restons', 'restez', 'restent', 'étais', 'était', 'étaient', 'sera', 'serai', 'seront'}
    SUBJECT_PRONOUNS = {'il', 'elle', 'on', 'ils', 'elles', 'je', "j'", 'tu', 'nous', 'vous'}
    STOP_VERBS = {'être', 'devoir', 'pouvoir', 'sembler', 'paraître', 'falloir', 'rester', 'suffire'}

    @rule('fr.ce_se', 'spelling', 0.75, emits=HOMOPHONES)
    def homophones(self, p):
        """ce / se, a / à, ou / où, leur / leurs, la / là, sa / ça, c'est / s'est, et / est, peu / peut, ma / m'a"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens

        def finite_only(tok):
            return tg.only(tok, lx.VERB | lx.AUX) and any(a.verb_form in tg.FINITE for a in tok.tags)

        def lemma(tok):
            return lex.lemma(tok.tags[0]) if tok.tags and tok.tags[0].lemma >= 0 else ''

        def subject_like(tok):
            return tok.kind == 'word' and (tok.low in self.SUBJECT_PRONOUNS or tg.only(tok, lx.NOUN | lx.PROPN))

        for i, w in enumerate(t):
            if w.kind != 'word':
                continue
            prev = t[i - 1] if i > 0 and t[i - 1].kind == 'word' else None
            nxt = t[i + 1] if i + 1 < len(t) and t[i + 1].kind == 'word' else None
            nn = t[i + 2] if i + 2 < len(t) and t[i + 2].kind == 'word' else None
            low = w.low
            if low == 'ce' and prev and nxt and lemma(nxt) not in self.STOP_VERBS and                     ((prev.low in self.SUBJECT_PRONOUNS and any(a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE for a in lex.analyses(nxt.text))) or (subject_like(prev) and finite_only(nxt))):
                p.add('fr.ce_se', w, w, match_case(w.text, 'se'), 'se')
            elif low == 'se' and nxt and tg.only(nxt, lx.NOUN) and not any(a.pos & (lx.VERB | lx.AUX) for a in lex.analyses(nxt.text)):
                p.add('fr.ce_se', w, w, match_case(w.text, 'ce'), 'ce')
            elif low == 'a' and prev and tg.only(prev, lx.VERB | lx.AUX) and lemma(prev) != 'avoir' and nxt and (tg.has(nxt, lx.DET) or tg.only(nxt, lx.PROPN)) and \
                    ((i >= 2 and subject_like(t[i - 2])) or all(x.verb_form == lx.INFINITIVE for x in prev.tags)):
                p.add('fr.a_accent', w, w, 'à', 'à')
            elif low == 'ou' and prev and nxt and tg.only(prev, lx.NOUN) and nxt.low in ('il', 'elle', 'on', 'ils', 'elles', 'je', 'nous'):
                p.add('fr.ou_where', w, w, 'où', 'où')
            elif low in ('leur', 'leurs') and nxt:
                numbers = {a.number for a in nxt.tags if a.pos & lx.NOUN}
                ok = bool(numbers) and not tg.has(nxt, lx.VERB | lx.AUX)
                number = numbers.pop() if len(numbers) == 1 else 0
                if ok and low == 'leur' and number == lx.PLURAL:
                    p.add('fr.leur', w, w, match_case(w.text, 'leurs'), 'leurs')
                elif ok and low == 'leurs' and number == lx.SINGULAR:
                    p.add('fr.leur', w, w, match_case(w.text, 'leur'), 'leur')
            elif low == 'la' and prev and (i + 1 == len(t) or (t[i + 1].kind == 'punct' and t[i + 1].text in '.,;:!?')) and \
                    (prev.low in self.ETRE_ALLER or (tg.only(prev, lx.NOUN) and i >= 2 and t[i - 2].low in ('ce', 'cet', 'cette', 'ces'))):
                p.add('fr.la_there', w, w, match_case(w.text, 'là'), 'là')
            elif low == 'sa' and nxt and finite_only(nxt) and nxt.low in ('va', 'fait', 'marche', 'dépend', 'suffit', 'sert', 'existe', 'compte'):
                p.add('fr.sa_ca', w, w, match_case(w.text, 'ça'), 'ça')
            elif low == "c'" and prev and prev.low in ('il', 'elle', 'on') and nxt and nxt.low in ('est', 'était') and nn and any(a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE for a in lex.analyses(nn.text)):
                p.add('fr.cest_sest', w, w, match_case(w.text, "s'"), "s'")
            elif low == 'et' and prev and nxt and prev.low in ('il', 'elle', 'on', 'ils', 'elles') and not tg.has(nxt, lx.DET | lx.PRON) and                     any(a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE for a in lex.analyses(nxt.text)):
                fix = 'sont' if prev.low in ('ils', 'elles') else 'est'
                p.add('fr.et_est', w, w, match_case(w.text, fix), fix)
            elif low == 'peu' and prev and nxt and prev.low in ('il', 'elle', 'on') and any(a.verb_form == lx.INFINITIVE for a in nxt.tags):
                p.add('fr.peu_peut', w, w, match_case(w.text, 'peut'), 'peut')
            elif low in ('ma', 'ta') and prev and nxt and prev.low in ('il', 'elle', 'on', 'qui') and \
                    any(a.pos & lx.VERB and a.verb_form == lx.PAST_PARTICIPLE for a in lex.analyses(nxt.text)):
                fix = "m'a" if low == 'ma' else "t'a"
                p.add('fr.ma_ma', w, w, match_case(w.text, fix), fix)

    # [SECTION] Rules without lexicon

    @rule('fr.a', 'spelling', 0.9)
    def a(self, p):
        """il à -> il a"""
        for i in range(1, len(p)):
            if p.word(i) and p.word(i - 1) and p[i].low == 'à' and p[i - 1].low in ('il', 'elle', 'on') and self.opens_clause(p, i - 1):
                p.add('fr.a', p[i], p[i], match_case(p[i].text, 'a'))

    @rule('fr.ont', 'spelling', 0.9, emits=('fr.sont',))
    def ont_sont(self, p):
        """ils on -> ils ont, ils son -> ils sont"""
        for i in range(1, len(p)):
            if not (p.word(i) and p.word(i - 1)):
                continue
            before = p[i - 1].low
            if before not in ('ils', 'elles', 'ceux', 'celles'):
                continue
            if p[i].low == 'on' and before in ('ils', 'elles'):
                p.add('fr.ont', p[i], p[i], match_case(p[i].text, 'ont'))
            elif p[i].low == 'son':
                p.add('fr.sont', p[i], p[i], match_case(p[i].text, 'sont'))

    @rule('fr.participle', 'conjugation', 0.8)
    def participle(self, p):
        """After an auxiliary a verb in -er is a participle: il a manger -> mangé"""
        known = self.core.known
        if not known:
            return
        for i in range(1, len(p)):
            if not (p.word(i) and p.word(i - 1)) or p[i - 1].low not in AUXILIARIES:
                continue
            aux = p[i - 1].low
            avoir = aux in ('a', 'ai', 'as', 'avons', 'avez', 'ont', 'ayant') or aux.startswith(('avi', 'avai', 'aura'))
            # "c'est continuer": the verb of being then takes an infinitive; only after a subject pronoun is it an auxiliary
            if not avoir and not (i >= 2 and p[i - 2].kind == 'word' and p[i - 2].low in SUBJECTS_BEFORE_ETRE):
                continue
            w = p[i].low
            if len(w.encode()) < 5 or not w.endswith('er'):
                continue
            base = w[:-2] + 'é'
            if known(base) and known(p[i].text):
                p.add('fr.participle', p[i], p[i], match_case(p[i].text, base), base)

    @rule('fr.infinitive', 'conjugation', 0.7)
    def infinitive(self, p):
        """After pour, sans or a modal verb a participle is an infinitive: pour mangé -> manger"""
        triggers = {'pour', 'sans', 'faut', 'peut', 'peuvent', 'veut', 'veulent', 'doit', 'doivent', 'dois', 'peux', 'veux', 'pouvoir', 'vouloir', 'devoir', 'va', 'vais', 'vas', 'vont', 'allons', 'allez'}
        excluded = {'été', 'passé', 'étés', 'côté', 'degré'}
        known = self.core.known
        if not known:
            return
        for i in range(1, len(p)):
            if not (p.word(i) and p.word(i - 1)) or p[i - 1].low not in triggers:
                continue
            w = p[i].low
            if len(w.encode()) < 5 or not w.endswith('é') or w in excluded:
                continue
            base = w[:-1] + 'er'
            if known(base):
                p.add('fr.infinitive', p[i], p[i], match_case(p[i].text, base), base)

    @rule('fr.phrase', 'expression', 0.85)
    def phrase(self, p):
        """fixed errors of the table PHRASES: quand à -> quant à"""
        self.phrases(p, PHRASES, 'fr.phrase')

    # [SECTION] Agreement, with the lexicon

    @rule('fr.det_number', 'agreement', 0.8, emits=('fr.det_gender',))
    def determiner(self, p):
        """Determiner and noun: les chat -> les chats, un voiture -> une voiture"""
        lex = self.core.lexicon
        if not lex:
            return
        for i in range(len(p) - 1):
            if not p.word(i) or not self.plain_word(p, i + 1) or not p[i + 1].space_before:
                continue
            det = p[i].low
            plural, singular = det in PLURAL_DETS, det in SINGULAR_DETS
            if not plural and not singular:
                continue
            if p[i].tags and not tg.only(p[i], lx.DET) and det != 'chaque':
                continue                # a pronoun, or not sure: "il le porte"
            if p[i + 1].low in NUMERALS:
                continue
            if det in ('un', 'une') and i > 0 and (p[i - 1].low == 'et' or p[i - 1].kind == 'number'):
                continue                # "trente et un ans": a number
            noun = p[i + 1]
            an = noun.tags or lex.analyses(noun.text)
            ok, gender, number = self.noun_only(an)
            if not ok and all(a.pos & ~(lx.NOUN | lx.ADJ) == 0 for a in an) and any(a.pos & lx.NOUN for a in an):
                # "ces porte sont ouvertes": a word which is a noun or an adjective is the noun when no other noun or adjective follows
                after = p[i + 2] if i + 2 < len(p) else None
                if after is None or after.kind != 'word' or not (after.tags or lex.analyses(after.text)) or not any(a.pos & (lx.NOUN | lx.ADJ) for a in (after.tags or lex.analyses(after.text))):
                    ok, gender, number = self.noun_only([a for a in an if a.pos & lx.NOUN])
            if not ok or any(a.pos & FUNCTION_WORDS for a in lex.analyses(noun.text)):
                continue                # "son mais": a conjunction, an adverb... is not a noun
            if plural and number == lx.SINGULAR:
                form = lex.inflect(an[0], 0, lx.PLURAL, 0, 0)
                if form and form != noun.low:
                    p.add('fr.det_number', noun, noun, match_case(noun.text, form), form)
            elif singular and number == lx.PLURAL and det not in ('du', 'au'):
                form = lex.inflect(an[0], 0, lx.SINGULAR, 0, 0)
                if form and form != noun.low:
                    p.add('fr.det_number', noun, noun, match_case(noun.text, form), form)
            elif singular and number != lx.INVARIABLE and gender not in (0, lx.EPICENE) and not self.starts_with_vowel(noun.low):
                other = ''
                if gender == lx.FEMININE and det in MASCULINE_DETS:
                    other = TO_FEMININE.get(det, '')
                elif gender == lx.MASCULINE and det in FEMININE_DETS:
                    other = TO_MASCULINE.get(det, 'son')
                if other:
                    p.add('fr.det_gender', p[i], p[i], match_case(p[i].text, other), other)

    @rule('fr.noun_adjective', 'agreement', 0.75)
    def adjective(self, p):
        """Noun and adjective: des chats noir -> noirs, une voiture noir -> noire"""
        lex = self.core.lexicon
        if not lex:
            return
        for i in range(len(p) - 1):
            if not p.word(i) or not self.plain_word(p, i + 1) or not p[i + 1].space_before:
                continue
            if p[i].low == 'air':       # "avoir l'air fatiguée": the adjective agrees with the subject
                continue
            if i > 0 and p[i - 1].low in ('de', "d'"):  # "une carte de vœux manuscrite"
                continue
            noun_an = lex.analyses(p[i].text)
            ok, gender, number = self.noun_only(noun_an)
            if not ok or gender in (0, lx.EPICENE) or number in (0, lx.INVARIABLE):
                continue
            adj = p[i + 1]
            adj_an = lex.analyses(adj.text)
            any_adj, fine = False, bool(adj_an)
            for a in adj_an:
                if a.pos & ~(lx.ADJ | lx.NOUN):
                    fine = False        # the word can be something else (a verb): not sure
                    break
                if a.pos & lx.ADJ:
                    any_adj = True
            if not fine or not any_adj:
                continue
            # A colour followed by another word is invariable ("bleu ciel"), and so are the compounds
            if adj.low in COLORS and i + 2 < len(p) and p.word(i + 2):
                nxt = lex.analyses(p[i + 2].text)
                if not nxt or any(a.pos & (lx.NOUN | lx.ADJ) for a in nxt):
                    continue
            if i + 2 < len(p) and p[i + 2].kind == 'punct' and p[i + 2].text == ',':
                continue                # "le surlendemain, seule, ...": an apposition does not agree with the noun before it
            if adj.low in COLORS and i + 2 < len(p) and p.word(i + 2) and p[i + 2].low in ('et', 'ou'):
                continue                # "des wagons bleu et blanc": colours which agree with each other
            model, compatible = None, False
            for a in adj_an:
                if not a.pos & lx.ADJ:
                    continue
                if model is None:
                    model = a
                if a.gender in (gender, lx.EPICENE) and a.number in (number, lx.INVARIABLE):
                    compatible = True
            if compatible or model is None:
                continue
            form = lex.inflect(model, gender, number, 0, 0)
            if form and form != adj.low:
                p.add('fr.noun_adjective', adj, adj, match_case(adj.text, form), form)

    @rule('fr.subject_verb', 'agreement', 0.8)
    def subject_verb(self, p):
        """Subject and verb: tu mange -> manges, ils est -> sont"""
        lex = self.core.lexicon
        if not lex:
            return
        for i in range(len(p) - 1):
            if not p.word(i) or p[i].low not in SUBJECT_PRONOUNS:
                continue
            person, number = SUBJECT_PRONOUNS[p[i].low]
            # The subject opens a clause: after a punctuation mark, the start of the paragraph or a conjunction
            if i > 0 and not (p[i - 1].kind == 'punct' or (p[i - 1].kind == 'word' and p[i - 1].low in STARTERS)):
                continue
            if self.compound_subject(p, i):
                continue                # "Paul et elle sont": the verb agrees with both
            # "nous" and "vous" are often objects: subjects only after a punctuation mark
            if i > 0 and p[i - 1].kind == 'word' and p[i].low[0] in 'nv' and number == 2 and person != 3:
                continue
            v = i + 1
            while p.word(v) and p[v].low in CLITICS and v < i + 4:
                v += 1
            if not p.word(v):
                continue
            an = p[v].tags or lex.analyses(p[v].text)
            finite_found, match, model = False, False, None
            for a in an:
                if not a.pos & (lx.VERB | lx.AUX):
                    continue
                if a.verb_form < lx.PRESENT or a.verb_form > lx.SUBJUNCTIVE_IMPERFECT:
                    continue            # imperative, infinitive and participles do not have a subject
                finite_found = True
                if model is None:
                    model = a
                if a.person == person and a.number == number:
                    match = True
            # A word which can also be something else after the pronoun is not looked at ("il part", "on lit")
            other = any(a.pos & (lx.DET | lx.PRON | lx.ADP | lx.ADV | lx.CCONJ | lx.SCONJ) for a in an)
            if not finite_found or match or other or model is None:
                continue
            form = lex.inflect(model, 0, number, person, model.verb_form)
            if form and form != p[v].low:
                p.add('fr.subject_verb', p[v], p[v], match_case(p[v].text, form), form)

    # [SECTION] Elision, verb person, number words, "quelque", "moi qui", "la plupart", missing accent

    H_MUET = {'homme', 'heure', 'heures', 'hôtel', 'histoire', 'habitude', 'habitant', 'herbe', 'hiver', 'hôpital', 'honneur', 'horizon', 'humanité', 'hypothèse', 'harmonie', 'hôte'}
    NOT_ELIDED = {'oui', 'onze', 'ouistiti', 'ouate', 'un', 'une', 'uhlan', 'ululement', 'yacht', 'yaourt', 'ukase', 'ouistitis'}
    ELIDED_WITH_IL = {'que': "qu'", 'lorsque': "lorsqu'", 'puisque': "puisqu'", 'quoique': "quoiqu'", 'si': "s'"}
    SUBJECT_AFTER_QUE = {'il', 'ils', 'elle', 'elles', 'on', 'un', 'une'}

    @rule('fr.elision', 'spelling', 0.85)
    def elision(self, p):
        """si il -> s'il, que elle -> qu'elle, je ai -> j'ai, ce est -> c'est, le homme -> l'homme, de un -> d'un"""
        lex = self.core.lexicon
        t = p.tokens
        for i in range(len(t) - 1):
            a, b = t[i], t[i + 1]
            if not (p.word(i) and p.word(i + 1)) or not b.space_before:
                continue
            x, y = a.low, b.low
            follow = t[i + 2].low if i + 2 < len(t) else ''
            elided = None
            if x in self.ELIDED_WITH_IL and (y in ('il', 'ils') or (x != 'si' and y in self.SUBJECT_AFTER_QUE)):
                elided = self.ELIDED_WITH_IL[x]
            elif x == 'ce' and y in ('est', 'était', 'étaient', 'étant'):
                elided = "c'"
            elif x == 'de' and y in ('un', 'une', 'elle', 'elles', 'ici', 'autres', 'autre') and follow not in ('à', 'a'):
                elided = "d'"
            elif x in ('je', 'ne', 'me', 'te', 'le', 'la') and lex and not b.text[0].isupper() and not (x == 'je' and y in ('a', 'as')):    # "je a" is for fr.verb_person
                vowel = y[0] in 'aeiouàâéèêîôû' or (y in self.H_MUET and x in ('le', 'la'))
                if not vowel or y in self.NOT_ELIDED:
                    continue
                readings = lex.analyses(b.text)
                if not readings or any(r.pos & FUNCTION_WORDS for r in readings):
                    if y not in ('y', 'en') or x not in ('je', 'ne', 'me', 'te'):
                        continue
                if x in ('je', 'ne', 'me', 'te') and not any(r.pos & (lx.VERB | lx.AUX) and r.verb_form in tg.FINITE for r in readings):
                    continue
                elided = {'je': "j'", 'ne': "n'", 'me': "m'", 'te': "t'", 'le': "l'", 'la': "l'"}[x]
            if elided:
                fix = match_case(a.text, elided) + b.text
                p.add('fr.elision', a, b, fix, fix)

    VERB_PERSON = {('tu', 'a'): 'as', ('tu', 'va'): 'vas', ('tu', 'ai'): 'as', ('il', 'as'): 'a', ('elle', 'as'): 'a', ('on', 'as'): 'a', ('il', 'vas'): 'va', ('elle', 'vas'): 'va',
                   ('on', 'vas'): 'va', ('il', 'ai'): 'a', ('elle', 'ai'): 'a', ('on', 'ai'): 'a'}

    @rule('fr.verb_person', 'conjugation', 0.85)
    def verb_person(self, p):
        """tu a -> tu as, il as -> il a, je a -> j'ai"""
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)) or not self.opens_clause(p, i) or self.compound_subject(p, i):
                continue
            pair = (t[i].low, t[i + 1].low)
            if pair in self.VERB_PERSON:
                fix = self.VERB_PERSON[pair]
                p.add('fr.verb_person', t[i + 1], t[i + 1], match_case(t[i + 1].text, fix), fix)
            elif pair in (('je', 'a'), ('je', 'as')) and i + 2 < len(t):
                fix = match_case(t[i].text, "j'ai")
                p.add('fr.verb_person', t[i], t[i + 1], fix, fix)

    UNITS = {'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf'}
    NUMBER_AFTER_CENTS = {'un', 'une', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'vingt',
                          'trente', 'quarante', 'cinquante', 'soixante', 'mille'}

    @rule('fr.number_word', 'agreement', 0.8)
    def number_word(self, p):
        """deux cent personnes -> deux cents personnes, quatre-vingt ans -> quatre-vingts ans, deux cents mille -> deux cent mille"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 1):
            if not (p.word(i) and p.word(i + 1)):
                continue
            w, nxt = t[i].low, t[i + 1]
            if w in self.UNITS and nxt.low == 'cent' and p.word(i + 2) and t[i + 2].space_before:
                ok, _, _ = self.noun_only(lex.analyses(t[i + 2].text))
                if ok and t[i + 2].low not in NUMERALS and t[i + 2].low not in self.NUMBER_AFTER_CENTS and not t[i + 2].text[0].isupper():
                    p.add('fr.number_word', nxt, nxt, match_case(nxt.text, 'cents'), 'cents')
            elif w in self.UNITS and nxt.low == 'cents' and p.word(i + 2) and t[i + 2].low in self.NUMBER_AFTER_CENTS:
                p.add('fr.number_word', nxt, nxt, match_case(nxt.text, 'cent'), 'cent')
            elif w == 'quatre-vingt' and nxt.space_before:
                ok, _, _ = self.noun_only(lex.analyses(nxt.text))
                if ok and nxt.low not in NUMERALS and nxt.low not in self.NUMBER_AFTER_CENTS and not nxt.text[0].isupper():
                    p.add('fr.number_word', t[i], t[i], match_case(t[i].text, 'quatre-vingts'), 'quatre-vingts')

    @rule('fr.quelque', 'agreement', 0.8)
    def quelque(self, p):
        """quelque personnes -> quelques personnes"""
        lex = self.core.lexicon
        if not lex:
            return
        for i in range(len(p) - 1):
            if p.word(i) and p.word(i + 1) and p[i].low == 'quelque' and p[i + 1].space_before and not p[i + 1].text[0].isupper():
                ok, _, number = self.noun_only(lex.analyses(p[i + 1].text))
                if ok and number == lx.PLURAL and not any(a.pos & FUNCTION_WORDS for a in lex.analyses(p[i + 1].text)):
                    p.add('fr.quelque', p[i], p[i], match_case(p[i].text, 'quelques'), 'quelques')

    @rule('fr.relative_person', 'agreement', 0.8)
    def relative_person(self, p):
        """moi qui est -> moi qui suis, toi qui a -> toi qui as"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(len(t) - 2):
            if not (p.word(i) and p.word(i + 1) and p.word(i + 2)) or t[i + 1].low != 'qui' or t[i].low not in ('moi', 'toi'):
                continue
            person = 1 if t[i].low == 'moi' else 2
            readings = t[i + 2].tags or lex.analyses(t[i + 2].text)
            finite = [a for a in readings if a.pos & (lx.VERB | lx.AUX) and a.verb_form in tg.FINITE]
            if not finite or (any(not a.pos & (lx.VERB | lx.AUX) for a in readings) and t[i + 2].low not in AUXILIARIES) or any(a.person == person and a.number == lx.SINGULAR for a in finite):
                continue
            form = lex.inflect(finite[0], 0, lx.SINGULAR, person, finite[0].verb_form)
            if form and form != t[i + 2].low:
                p.add('fr.relative_person', t[i + 2], t[i + 2], match_case(t[i + 2].text, form), form)

    @rule('fr.plupart', 'agreement', 0.75)
    def plupart(self, p):
        """la plupart des gens est -> sont"""
        lex = self.core.lexicon
        if not lex:
            return
        t = p.tokens
        for i in range(1, len(t) - 3):
            if not all(p.word(i + k) for k in range(4)) or t[i].low != 'plupart' or t[i - 1].low != 'la' or t[i + 1].low != 'des' or not self.opens_clause(p, i - 1):
                continue
            ok, _, number = self.noun_only(t[i + 2].tags or lex.analyses(t[i + 2].text))
            if not ok or number != lx.PLURAL:
                continue
            verb = t[i + 3]
            readings = verb.tags or lex.analyses(verb.text)
            finite = [a for a in readings if a.verb_form in tg.FINITE]
            if not finite or (any(not a.pos & (lx.VERB | lx.AUX) for a in readings) and verb.low not in AUXILIARIES) or any(a.number == lx.PLURAL for a in finite):
                continue
            form = lex.inflect(finite[0], 0, lx.PLURAL, 3, finite[0].verb_form)
            if form and form != verb.low:
                p.add('fr.plupart', verb, verb, match_case(verb.text, form), form)


MORE_MESSAGES = {
    'en': {
        'fr.elision': 'Elision: "{arg}".',
        'fr.verb_person': 'The verb does not agree with its pronoun: "{arg}".',
        'fr.number_word': 'Number word: "{arg}".',
        'fr.quelque': 'Before a plural noun it is "quelques".',
        'fr.relative_person': 'The verb of "qui" agrees with the pronoun it stands for: "{arg}".',
        'fr.plupart': 'After "la plupart des" the verb is plural: "{arg}".',
    },
    'fr': {
        'fr.elision': 'Élision : « {arg} ».',
        'fr.verb_person': "Le verbe ne s'accorde pas avec son pronom : « {arg} ».",
        'fr.number_word': 'Mot de nombre : « {arg} ».',
        'fr.quelque': 'Devant un nom pluriel, on écrit « quelques ».',
        'fr.relative_person': "Le verbe de « qui » s'accorde avec le pronom qu'il représente : « {arg} ».",
        'fr.plupart': 'Après « la plupart des », le verbe est au pluriel : « {arg} ».',
    },
    'es': {
        'fr.elision': 'Elisión: "{arg}".',
        'fr.verb_person': 'El verbo no concuerda con su pronombre: "{arg}".',
        'fr.number_word': 'Numeral: "{arg}".',
        'fr.quelque': 'Ante un nombre plural se escribe "quelques".',
        'fr.relative_person': 'El verbo de "qui" concuerda con el pronombre al que se refiere: "{arg}".',
        'fr.plupart': 'Después de "la plupart des" el verbo va en plural: "{arg}".',
    },
}
for _ui, _table in MORE_MESSAGES.items():
    Grammar.messages[_ui].update(_table)
