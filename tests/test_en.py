import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import grammar_engine


def rules(text):
    return [(i.rule, text[i.start:i.end], i.suggestions[0]) for i in grammar_engine.Checker('en').check(text)]


class English(unittest.TestCase):
    def test_agreement(self):
        for text, expected in (('He go to school.', ('en.subject_verb', 'go', 'goes')), ('They goes home.', ('en.subject_verb', 'goes', 'go')),
                               ('She have a car.', ('en.subject_verb', 'have', 'has')), ('I is happy.', ('en.subject_verb', 'is', 'am')),
                               ('We was there.', ('en.subject_verb', 'was', 'were')), ("He don't know.", ('en.subject_verb', "don't", "doesn't")),
                               ('A books are here.', ('en.det_number', 'books', 'book')), ('These book is old.', ('en.det_number', 'book', 'books')),
                               ('I have went home.', ('en.participle', 'went', 'gone')), ('I seen him.', ('en.past', 'seen', 'saw')),
                               ('It is to big.', ('en.to_too', 'to', 'too')), ('You will loose.', ('en.loose_lose', 'loose', 'lose')),
                               ('I dont know.', ('en.phrase', 'dont', "don't"))):
            self.assertIn(expected, rules(text), text)

    def test_correct(self):
        for text in ('He goes to school.', 'They go home.', 'He never goes there.', 'He can go home.', 'If I were rich, I would travel.', 'This information is useful.',
                     'Those cars are fast.', 'I have gone home.', 'I have read the book.', 'She has been there.', 'He has a dog.', 'Does he go home?',
                     'So she set to work.', 'I have a saw.', 'Let us both go to law.', 'Several other curious creatures came.', 'Those long words are hard.'):
            self.assertEqual(rules(text), [], text)


class Variants(unittest.TestCase):
    def test_variant_derives_from_language(self):
        ar = grammar_engine.Checker('es-AR')
        self.assertEqual(ar.language, 'es_ar')
        # what Spanish has, the variant has
        self.assertIn('es.inverted', [r['id'] for r in ar.rules()])
        self.assertIn(('es_ar.voseo', 'vos tienes'), [(i.rule, 'Vos tienes'.lower()) for i in ar.check('Vos tienes razón.')])
        self.assertTrue(ar.check('Vos tienes razón.', ui='es')[0].message.startswith('En el español'))
        # an inherited message still works
        self.assertEqual([i.rule for i in ar.check('Cómo estás?')], ['es.inverted'])

    def test_unknown_variant_falls_back(self):
        mx = grammar_engine.Checker('es-MX')
        self.assertEqual(mx.language, 'es_mx')
        self.assertEqual([i.rule for i in mx.check('Cómo estás?')], ['es.inverted'])
        self.assertEqual(mx.check('Vos tienes razón.'), [])


if __name__ == '__main__':
    unittest.main()
