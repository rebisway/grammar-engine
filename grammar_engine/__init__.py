# grammar-engine - a grammar checker made of independent rules, one Python file per language.
# Offline, no model, standard library only.
#
#   import grammar_engine
#   checker = grammar_engine.Checker('fr')
#   for issue in checker.check('Les chat noir dort.', ui='en'):
#       print(issue.rule, issue.start, issue.end, issue.suggestions, issue.message)
#
# SPDX-License-Identifier: MIT

from .core import Checker, Grammar, Issue, rule
from . import lexicon

__version__ = '0.2.0'
__all__ = ['Checker', 'Grammar', 'Issue', 'rule', 'lexicon']
