# grammar-engine - bridge for a host program which embeds Python: everything goes in and out as text (JSON),
# so the host needs no knowledge of the objects of the engine.
#
#   configure('["C:/Users/me/grammar"]')        folders with your own languages (optional)
#   set_known(callable)                         the spelling dictionary of the host: callable(word) -> bool (optional)
#   check('fr', 'en', 'fr.a,fr.ont', text)      -> JSON list of issues, offsets in UTF-8 bytes
#   rules('fr')                                 -> JSON list of the rules of the language
#
# SPDX-License-Identifier: MIT

import json

from . import Checker

_paths = []
_known = None
_checkers = {}


def configure(paths_json):
    """Sets the folders with the languages of the user (a JSON list of paths) and drops the checkers already built."""
    global _paths
    _paths = json.loads(paths_json)
    _checkers.clear()


def set_known(fn):
    """Sets the spelling dictionary of the host: callable(word) -> bool."""
    global _known
    _known = fn
    _checkers.clear()


def _checker(language, ignored):
    """The Checker for a language and a set of ignored rules; a few are kept, built when first asked for."""
    key = (language.replace('-', '_').lower(), ignored)
    c = _checkers.get(key)
    if c is None:
        if len(_checkers) > 16:
            _checkers.clear()
        known = (lambda w: bool(_known(w))) if _known else None
        c = _checkers[key] = Checker(key[0], known=known, ignored=[r for r in ignored.split(',') if r], paths=_paths)
    return c


def check(language, ui, ignored, text):
    """Checks a paragraph: JSON list of issues, the ranges in UTF-8 bytes (what a C or C++ host indexes)."""
    out = []
    for i in _checker(language, ignored).check(text, ui=ui[:2].lower()):
        d = i.as_dict()
        d['start'] = len(text[:i.start].encode('utf-8'))
        d['end'] = len(text[:i.end].encode('utf-8'))
        out.append(d)
    return json.dumps(out, ensure_ascii=False)


def rules(language):
    """The rules of a language, as JSON."""
    return json.dumps(_checker(language, '').rules(), ensure_ascii=False)
