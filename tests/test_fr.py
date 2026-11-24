import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import grammar_engine


def rules(lang, text, known=None):
    return [(i.rule, text[i.start:i.end], i.suggestions[0]) for i in grammar_engine.Checker(lang, known=known).check(text)]


class French(unittest.TestCase):
    def test_agreement(self):
        self.assertIn(('fr.det_number', 'chat', 'chats'), rules('fr', 'Les chat dorment.'))
        self.assertIn(('fr.noun_adjective', 'noir', 'noire'), rules('fr', 'Une voiture noir.'))
        self.assertIn(('fr.subject_verb', 'mange', 'manges'), rules('fr', 'Tu mange.'))

    def test_clean(self):
        self.assertEqual(rules('fr', 'Les chats noirs dorment sur la table.'), [])

    def test_participle_needs_dictionary(self):
        self.assertEqual(rules('fr', 'Il a manger.'), [])
        self.assertIn(('fr.participle', 'manger', 'mangé'), rules('fr', 'Il a manger.', known=lambda w: w in ('mangé', 'manger')))


class Participle(unittest.TestCase):
    def test_être(self):
        self.assertIn(('fr.participle_subject', 'parti', 'partie'), rules('fr', 'Elle est parti hier.'))
        self.assertIn(('fr.participle_subject', 'parti', 'partis'), rules('fr', 'Nous sommes parti.'))
        self.assertIn(('fr.participle_subject', 'parti', 'parties'), rules('fr', 'Les filles sont parti.'))
        for ok in ('Elle est partie.', 'Ils sont partis.', "C'est fini.", "Elle s'est parti."):
            self.assertEqual(rules('fr', ok), [])

    def test_avoir(self):
        self.assertIn(('fr.participle_object', 'mangé', 'mangés'), rules('fr', 'Je les ai mangé.'))
        for ok in ('Je les ai mangés.', 'Je les ai vu partir.', 'Elle a mangé.'):
            self.assertEqual(rules('fr', ok), [])


class MoreAgreements(unittest.TestCase):
    def test_flagged(self):
        for text, expected in (('Elle est grand.', ('fr.attribute', 'grand', 'grande')), ('Les filles sont content.', ('fr.attribute', 'content', 'contentes')),
                               ('Les chats dort sur le lit.', ('fr.subject_noun_verb', 'dort', 'dorment')), ('Le chat dorment.', ('fr.subject_noun_verb', 'dorment', 'dort')),
                               ('Une grand maison.', ('fr.noun_adjective', 'grand', 'grande')), ('Les grands maison.', ('fr.det_number', 'maison', 'maisons')),
                               ('Tout les jours.', ('fr.tout', 'Tout', 'Tous')), ('Toute les semaines.', ('fr.tout', 'Toute', 'Toutes')),
                               ('Tous le monde.', ('fr.tout', 'Tous', 'Tout')), ('Ma amie est là.', ('fr.possessive_vowel', 'Ma', 'Mon')),
                               ('Chaque jours.', ('fr.det_number', 'jours', 'jour'))):
            self.assertIn(expected, rules('fr', text), text)

    def test_correct(self):
        for text in ('Elle est grande.', "C'est grand.", 'Nous sommes grand.', 'Elle est bleu.', 'Le chien et le chat dorment.', 'La foule crient.', 'La porte ferme.',
                     'Un bel arbre.', 'Tout le monde.', 'Sa honte est grande.', "Le granit sous elle était froid et présent.", "Ce ne sont pas du tout les mêmes raisons.",
                     'Le chien et la chatte sont partis.'):
            self.assertEqual([r for r in rules('fr', text)], [], text)


class Tenses(unittest.TestCase):
    def test_flagged(self):
        self.assertIn(('fr.si_tense', 'aurais', 'avais'), rules('fr', "Si j'aurais su, je serais venu."))
        self.assertIn(('fr.si_tense', 'viendras', 'viens'), rules('fr', 'Si tu viendras, tu verras.'))
        self.assertIn(('fr.subjunctive', 'viens', 'viennes'), rules('fr', 'Il faut que tu viens.'))
        self.assertIn(('fr.subjunctive', 'a', 'ait'), rules('fr', "Bien qu'il a mangé."))
        self.assertIn(('fr.indicative_after', 'soit', 'est'), rules('fr', "Après qu'il soit parti."))

    def test_correct(self):
        for text in ("Si j'avais su, je serais venu.", 'Je ne sais pas si tu viendras.', "Il demande s'il viendrait.", 'Il faut que tu viennes.',
                     'Il faut que je parle.', "Bien qu'il ait mangé.", "Après qu'il est parti.", "Si grand qu'il soit."):
            self.assertEqual(rules('fr', text), [], text)


class Prepositions(unittest.TestCase):
    def test_flagged(self):
        self.assertIn(('fr.preposition', 'à ', 'de '), rules('fr', 'Il essaie à manger.'))
        self.assertIn(('fr.preposition', 'de ', 'à '), rules('fr', 'Il apprend de lire.'))
        self.assertIn(('fr.preposition', ' à', ''), rules('fr', 'Ils vont pallier à la pénurie.'))
        self.assertIn(('fr.preposition', ' de', ''), rules('fr', 'Elle se rappelle de la chanson.'))
        self.assertIn(('fr.preposition', 'que', 'de'), rules('fr', "C'est différent que hier."))
        self.assertIn(('fr.phrase', 'Malgré que', 'Bien que'), rules('fr', 'Malgré que tu viennes.'))

    def test_correct(self):
        for text in ('Il essaie de manger.', 'Il apprend à lire.', 'Il apprend de ses erreurs.', 'Elle se rappelle la chanson.', "Elle se rappelle d'avoir fermé.",
                     "Il refuse à quelqu'un l'entrée.", 'Il cherche à comprendre.'):
            self.assertEqual(rules('fr', text), [], text)


class Pronominal(unittest.TestCase):
    def test_flagged(self):
        self.assertIn(('fr.participle_subject', 'lavé', 'lavée'), rules('fr', "Elle s'est lavé."))
        self.assertIn(('fr.participle_subject', 'enfui', 'enfuis'), rules('fr', 'Ils se sont enfui.'))
        self.assertIn(('fr.participle_object', 'mangé', 'mangées'), rules('fr', "Les pommes que j'ai mangé."))
        self.assertIn(('fr.participle_invariable', 'mangées', 'mangé'), rules('fr', 'Elle a mangées la pomme.'))

    def test_correct(self):
        for text in ("Elle s'est lavée.", "Elle s'est lavé les mains.", 'Elles se sont parlé.', "Les pommes que j'ai mangées.", "Les pommes qu'elle a mangées.",
                     "L'idée que j'ai eu.", 'Elle les a mangées.', 'Quelle pomme as-tu mangée ?', 'Ils ont pris le train.'):
            self.assertEqual(rules('fr', text), [], text)


class Homophones(unittest.TestCase):
    def test_flagged(self):
        for text, rule, fix in (('Il ce lave les mains.', 'fr.ce_se', 'se'), ('Il va a la plage.', 'fr.a_accent', 'à'), ('Le lieu ou il habite.', 'fr.ou_where', 'où'),
                                ('Leur amis sont là.', 'fr.leur', 'Leurs'), ('Il est la.', 'fr.la_there', 'là'), ('Sa va bien.', 'fr.sa_ca', 'Ça'),
                                ("Il c'est lavé.", 'fr.cest_sest', "s'"), ('Il et parti.', 'fr.et_est', 'est'), ('Il peu manger.', 'fr.peu_peut', 'peut'),
                                ('Il ma dit oui.', 'fr.ma_ma', "m'a")):
            self.assertIn(rule, [r[0] for r in rules('fr', text) if r[2] == fix], text)

    def test_correct(self):
        for text in ('Ce lave-linge est neuf.', 'Il a la clé.', 'Jaune ou bleu.', 'Sa porte est ouverte.', 'Marie a la clé.', 'Il leur donne un livre.',
                     "C'est une bonne idée.", 'Le chat et le chien dorment.', "Si l'âge qui vient a un visage, c'est bien."):
            self.assertEqual(rules('fr', text), [], text)


class Tagger(unittest.TestCase):
    def pos(self, text):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
        import show_tags
        p = show_tags.tags(grammar_engine.Checker('fr'), text)
        return {t.text: set().union(*(show_tags.names(a.pos) for a in t.tags)) for t in p.tokens if t.tags}

    def test_pronoun_or_determiner(self):
        self.assertEqual(self.pos('Il le porte.')['le'], {'PRON'})
        self.assertEqual(self.pos('Il porte le sac.')['le'], {'DET'})
        self.assertEqual(self.pos('Je veux le manger.')['le'], {'PRON'})

    def test_verb_or_noun(self):
        self.assertEqual(self.pos('Il le porte.')['porte'], {'VERB'})
        self.assertIn('VERB', self.pos('Elle a mangé.')['mangé'])
        self.assertEqual(self.pos('Je veux manger.')['manger'], {'VERB'})
        self.assertEqual(self.pos('Il dort sur la table.')['sur'], {'ADP'})


class English(unittest.TestCase):
    def test_rules(self):
        self.assertIn(('en.a_an', 'a', 'an'), rules('en', 'She ate a apple.'))
        self.assertIn(('en.then_than', 'then', 'than'), rules('en', 'It is better then that.'))
        self.assertEqual(rules('en', 'Oh! thump! down she came.'), [])


class Spanish(unittest.TestCase):
    def test_inverted(self):
        self.assertIn(('es.inverted', 'Cómo', '¿Cómo'), rules('es', 'Cómo estás?'))


if __name__ == '__main__':
    unittest.main()
