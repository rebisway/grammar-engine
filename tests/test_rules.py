import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import grammar_engine


def rules(lang, text):
    return [(i.rule, text[i.start:i.end], i.suggestions[0]) for i in grammar_engine.Checker(lang).check(text)]


def has_rule(lang, text, rule_id, bad=None, good=None):
    return any(r == rule_id and (bad is None or b == bad) and (good is None or g == good) for r, b, g in rules(lang, text))


class Homographs(unittest.TestCase):
    """A noun which is also a verb form, after a determiner."""

    def test_french_flagged(self):
        for text, bad, good in (('Les pomme sont rouges.', 'pomme', 'pommes'), ('Une pommes est tombée.', 'pommes', 'pomme'), ('Un pomme rouge.', 'Un', 'Une'),
                                ('Ces porte sont ouvertes.', 'porte', 'portes'), ('Les grandes pomme sont bonnes.', 'pomme', 'pommes'),
                                ('Il a mangé les pomme.', 'pomme', 'pommes'), ('Mes rêve sont fous.', 'rêve', 'rêves'), ('Cette pommes.', 'pommes', 'pomme')):
            self.assertTrue(has_rule('fr', text, 'fr.det_number' if bad != 'Un' else 'fr.det_gender', bad, good), text)

    def test_french_correct(self):
        for text in ('Le garçon les mange.', 'Le garçon la porte.', 'Il la porte.', 'La porte est ouverte.', 'Elle ferme la ferme.', 'Castellan la vit.',
                     'Il leva les yeux et les vit.', 'La poussa simplement.', 'Ce sont des chats.', 'Il a son livre.', "Elle l'a vu."):
            self.assertEqual(rules('fr', text), [], text)

    def test_spanish(self):
        self.assertTrue(has_rule('es', 'Las casa son bonitas.', 'es.det_number', 'casa', 'casas'))
        self.assertTrue(has_rule('es', 'Esta casas es vieja.', 'es.det_number', 'casas', 'casa'))
        self.assertTrue(has_rule('es', 'Un casa grande.', 'es.det_gender', 'Un', 'Una'))
        for text in ('Las he buscado.', 'Los pinta con cuidado.', 'Ella las canta.', 'Tu eres bueno.'):
            self.assertFalse(has_rule('es', text, 'es.det_number'), text)

    def test_english(self):
        self.assertTrue(has_rule('en', 'These book is old.', 'en.det_number', 'book', 'books'))
        self.assertTrue(has_rule('en', 'A books.', 'en.det_number', 'books', 'book'))
        self.assertEqual(rules('en', 'Those who run win.'), [])


class FrenchRules(unittest.TestCase):
    def test_flagged(self):
        for text, rule_id, bad, good in (('Si il vient.', 'fr.elision', 'Si il', "S'il"), ('Je pense que elle vient.', 'fr.elision', 'que elle', "qu'elle"),
                                         ('Ce est fini.', 'fr.elision', 'Ce est', "C'est"), ('Le homme parle.', 'fr.elision', 'Le homme', "L'homme"),
                                         ('Il parle de un ami.', 'fr.elision', 'de un', "d'un"), ('Je ne ai rien.', 'fr.elision', 'ne ai', "n'ai"),
                                         ('Il as faim.', 'fr.subject_verb', 'as', 'a'), ('Elle va-y.', 'fr.phrase', 'va-y', 'vas-y'),
                                         ('Il y a deux cent personnes.', 'fr.number_word', 'cent', 'cents'), ('Deux cents mille euros.', 'fr.number_word', 'cents', 'cent'),
                                         ('Ils sont quatre-vingt hommes.', 'fr.number_word', 'quatre-vingt', 'quatre-vingts'),
                                         ('Quelque personnes sont venues.', 'fr.quelque', 'Quelque', 'Quelques'),
                                         ("C'est moi qui a fait ça.", 'fr.relative_person', 'a', 'ai'),
                                         ('La plupart des gens est content.', 'fr.plupart', 'est', 'sont'), ('Il est tres fatigué.', 'fr.phrase', 'tres', 'très')):
            self.assertTrue(has_rule('fr', text, rule_id, bad, good), text)

    def test_correct(self):
        for text in ("Il a l'air content.", 'Pour le oui ou le non.', "S'il vient, j'ai faim.", 'Deux cents personnes et deux cent trois chats.', 'Il a quatre-vingts ans.',
                     "C'est moi qui ai fait ça.", 'La plupart des gens sont contents.', 'Il y a quelques personnes.', "Elle l'aime."):
            self.assertEqual(rules('fr', text), [], text)


class EnglishRules(unittest.TestCase):
    def test_flagged(self):
        for text, rule_id, bad, good in (('There is many people here.', 'en.there_is', 'is', 'are'), ('Everyone are happy.', 'en.everyone', 'are', 'is'),
                                         ('The dogs runs fast.', 'en.noun_verb', 'runs', 'run'), ('The dogs is happy.', 'en.noun_verb', 'is', 'are'),
                                         ('The dog are happy.', 'en.noun_verb', 'are', 'is'), ('If I would have known, I left.', 'en.if_would', 'would have', 'had'),
                                         ('He goed home.', 'en.phrase', 'goed', 'went'), ('Between you and I.', 'en.phrase', 'Between you and I', 'Between you and me'),
                                         ('I depend of you.', 'en.phrase', 'depend of', 'depend on'), ('Its the best.', 'en.phrase', 'Its the', "It's the")):
            self.assertTrue(has_rule('en', text, rule_id, bad, good), text)

    def test_correct(self):
        for text in ('Hello everyone are you ready?', 'I would have time.', 'The data are clear.', 'The team have won.', 'The dogs bark.', 'The books are old.',
                     'There are many people here.', 'It is its own way.', 'If I had known, I would have gone.'):
            self.assertEqual(rules('en', text), [], text)


class SpanishRules(unittest.TestCase):
    def test_flagged(self):
        for text, rule_id, bad, good in (('La informacion es util.', 'es.accent', 'informacion', 'información'), ('¿Donde vives?', 'es.interrogative', 'Donde', 'Dónde'),
                                         ('¿Por que no?', 'es.interrogative', 'Por que', 'Por qué'), ('Pienso de que vendrá.', 'es.dequeismo', 'de que', 'que'),
                                         ('Habían muchas personas.', 'es.impersonal', 'Habían', 'Había'), ('Hubieron fiestas.', 'es.impersonal', 'Hubieron', 'Hubo'),
                                         ('Él ha echo la tarea.', 'es.haber_echo', 'echo', 'hecho'), ('Los niños juega en el patio.', 'es.noun_verb', 'juega', 'juegan'),
                                         ('El niño juegan.', 'es.noun_verb', 'juegan', 'juega'), ('Quiero que vienes.', 'es.subjunctive', 'vienes', 'vengas'),
                                         ('Tambien vino.', 'es.phrase', 'Tambien', 'También'), ('Me di cuenta que era tarde.', 'es.phrase', 'Me di cuenta que', 'Me di cuenta de que')):
            self.assertTrue(has_rule('es', text, rule_id, bad, good), text)

    def test_correct(self):
        for text in ('Hubieron llegado tarde.', 'Quiero que me llames.', 'Espero que vengas.', 'La gente dice la verdad.', 'Las niñas juegan.', '¿Dónde vives?',
                     'Había muchas personas.', 'Los niños que juegan son felices.'):
            self.assertEqual(rules('es', text), [], text)

    def test_voseo(self):
        self.assertTrue(has_rule('es-AR', 'Vos tienes razón.', 'es_ar.voseo', 'Vos tienes', 'Vos tenés'))
        self.assertTrue(has_rule('es-AR', 'Vos comes poco.', 'es_ar.voseo', 'Vos comes', 'Vos comés'))
        self.assertEqual(rules('es-AR', 'Vos sos bueno.'), [])


class CompoundSubjects(unittest.TestCase):
    """A subject made of two parts takes a verb which agrees with both: nothing is reported."""

    def test_correct(self):
        for lang, texts in (('en', ('He and I are friends.', 'The dog and the cat are asleep.', 'Either he or I am wrong.', 'The dog, the cat and I are here.', 'The data show a clear trend.',
                                    'The police are here.', 'Everyone, are you ready?', 'If I would have to choose, I would pick one.')),
                            ('es', ('Él y yo comemos juntos.', 'El niño y la niña juegan.', 'Tú y yo somos amigos.', 'Los hijos de María viven aquí.', 'Habían llegado muchas personas.')),
                            ('fr', ('Il et moi mangeons.', 'Paul et elle sont partis.', 'Elle et lui mangent.', 'La plupart du temps est perdu.', 'Deux cent cinquante euros.'))):
            for text in texts:
                self.assertEqual(rules(lang, text), [], text)

    def test_new_clause_is_still_checked(self):
        self.assertTrue(has_rule('en', 'I came and he go home.', 'en.subject_verb', 'go', 'goes'))
        self.assertTrue(has_rule('es', 'Yo vine y tú comen.', 'es.subject_verb', 'comen', 'comes'))
        self.assertTrue(has_rule('fr', 'Il mange et tu mange.', 'fr.subject_verb', 'mange', 'manges'))


if __name__ == '__main__':
    unittest.main()
