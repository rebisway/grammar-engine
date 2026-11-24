"""The sample texts of examples/sample_texts/ (made by tools/make_sample_texts.py): the files of errors must trigger every announced
rule, the corrected files must trigger none."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import grammar_engine

FOLDER = os.path.join(os.path.dirname(__file__), '..', 'examples', 'sample_texts')


def expected_rules():
    """{language: [rule ids]} from expected_rules.txt"""
    result = {}
    with open(os.path.join(FOLDER, 'expected_rules.txt'), encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                lang, rules = line.split(':', 1)
                result[lang.strip()] = rules.split()
    return result


def check_file(lang, name):
    """The rules triggered by a sample file. The engine is given a spelling dictionary which knows every word (two French rules need one)."""
    checker = grammar_engine.Checker(lang, known=lambda word: True)
    found = []
    with open(os.path.join(FOLDER, name), encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                found += checker.check(line.rstrip('\n'))
    return found


class SampleTexts(unittest.TestCase):
    def test_errors_trigger_every_announced_rule(self):
        for lang, rules in expected_rules().items():
            for ext in ('md', 'txt'):
                found = {i.rule for i in check_file(lang, '%s_errors.%s' % (lang, ext))}
                self.assertEqual([r for r in rules if r not in found], [], '%s_errors.%s' % (lang, ext))

    def test_corrected_texts_have_no_problem(self):
        for lang in expected_rules():
            for ext in ('md', 'txt'):
                found = check_file(lang, '%s_corrected.%s' % (lang, ext))
                self.assertEqual([(i.rule, i.start) for i in found], [], '%s_corrected.%s' % (lang, ext))


if __name__ == '__main__':
    unittest.main()
