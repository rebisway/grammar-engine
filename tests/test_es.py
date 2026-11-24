import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import grammar_engine


def rules(text, language='es'):
    return [(i.rule, text[i.start:i.end], i.suggestions[0]) for i in grammar_engine.Checker(language).check(text)]


class Spanish(unittest.TestCase):
    def test_flagged(self):
        for text, expected in (('Yo comes pan.', ('es.subject_verb', 'comes', 'como')), ('Nosotros come pan.', ('es.subject_verb', 'come', 'comemos')),
                               ('Los casa son grandes.', ('es.det_number', 'casa', 'casas')), ('La libros están aquí.', ('es.det_number', 'libros', 'libro')),
                               ('La casa blanco es bonita.', ('es.noun_adjective', 'blanco', 'blanca')), ('Los libros viejo.', ('es.noun_adjective', 'viejo', 'viejos')),
                               ('He comprados los libros.', ('es.haber_participle', 'comprados', 'comprado')), ('Tu eres bueno.', ('es.tilde', 'Tu', 'Tú')),
                               ('Cómo estás?', ('es.inverted', 'Cómo', '¿Cómo'))):
            self.assertIn(expected, rules(text), text)

    def test_correct(self):
        for text in ('Ella come pan.', 'Los libros están aquí.', 'El agua fría.', 'Un águila grande.', 'Tú eres bueno.', 'He comprado los libros.', 'La vi ayer.',
                     'A él le gusta.', 'El perro grande y bonito.', 'Las niñas contentas juegan.'):
            self.assertEqual(rules(text), [], text)

    def test_variant_inherits_the_lexicon(self):
        self.assertIn(('es.subject_verb', 'comes', 'como'), rules('Yo comes pan.', 'es-AR'))


if __name__ == '__main__':
    unittest.main()
