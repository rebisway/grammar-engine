# grammar-engine - command line and server mode.
#
# Command line: reads text on the standard input (or files), one paragraph per line, writes the issues as JSON
# (one array, or one object per line with --lines).
#
#   python -m grammar_engine --lang fr < text.txt
#   python -m grammar_engine --lang en --ui fr file1.txt file2.txt
#   python -m grammar_engine --rules --lang fr
#
# Server mode (--serve): a process which stays alive and answers one JSON request per line on the standard input with one
# JSON response per line on the standard output. The lexicons are loaded once, so a host program pays the loading time only
# at the first request of a language.
#
#   {"id": 1, "lang": "fr", "ui": "en", "text": "Les chat dorment.", "ignore": ["fr.a"]}
#   {"id": 1, "issues": [{"rule": "fr.det_number", ...}]}
#   {"id": 2, "op": "rules", "lang": "fr"}          list of the rules of a language
#   {"id": 3, "op": "languages"}                    languages and variants available
#   {"id": 4, "op": "ping"}                         version of the engine
#
# SPDX-License-Identifier: MIT

import argparse
import json
import os
import sys

from . import Checker, __version__
from . import core


# [SECTION] Issues as dictionaries

def issue_dict(issue, text, offset=0, byte_offset=0):
    """An Issue as the dictionary of the protocol: ranges in code points (start, end) and in UTF-8 bytes (byte_start, byte_end)
    of the paragraph `text`. For a paragraph which stands inside a longer text, `offset` (code points) and `byte_offset` (bytes)
    are the position of the paragraph in that text and are added to the ranges."""
    d = issue.as_dict()
    d['text'] = text[issue.start:issue.end]
    d['byte_start'] = byte_offset + len(text[:issue.start].encode('utf-8'))
    d['byte_end'] = byte_offset + len(text[:issue.end].encode('utf-8'))
    d['start'] += offset
    d['end'] += offset
    return d


# [SECTION] Server mode

def languages(paths=()):
    """The languages and variants which can be loaded: the delivered ones and those found in the folders of `paths`."""
    found = {}
    for folder in list(paths) + [core.LANGS_DIR]:
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            stem, ext = os.path.splitext(name)
            if ext == '.py' and stem != '__init__' and stem.isidentifier() and stem not in found:
                found[stem] = folder
    out = []
    for stem in sorted(found):
        checker = Checker(stem, paths=paths)
        parts = stem.split('_')
        out.append({'code': parts[0] + ('-' + parts[1].upper() if len(parts) > 1 else ''), 'variant_of': parts[0] if len(parts) > 1 else None,
                    'lexicon': checker.lexicon is not None, 'rules': len(checker.rules())})
    return out


class Server:
    """Answers the requests of the protocol. One Checker is kept per language and set of ignored rules."""

    def __init__(self, paths=()):
        """paths: folders with the languages of the user."""
        self.paths = list(paths)
        self._checkers = {}

    def checker(self, language, ignored):
        """The Checker for a language and a set of ignored rules, built at the first request."""
        key = (language.replace('-', '_').lower(), tuple(sorted(ignored)))
        c = self._checkers.get(key)
        if c is None:
            c = self._checkers[key] = Checker(key[0], ignored=ignored, paths=self.paths)
        return c

    def handle(self, request):
        """One request (a dictionary) -> one response (a dictionary). Errors come back as {"id": ..., "error": "..."}."""
        rid = request.get('id') if isinstance(request, dict) else None
        try:
            if not isinstance(request, dict):
                raise ValueError('a request is a JSON object')
            op = request.get('op', 'check')
            if op == 'ping':
                return {'id': rid, 'engine': 'grammar_engine', 'version': __version__}
            if op == 'languages':
                return {'id': rid, 'languages': languages(self.paths)}
            language = request.get('lang') or 'en'
            ignored = request.get('ignore') or []
            if not isinstance(ignored, list):
                raise ValueError('"ignore" is a list of rule identifiers')
            checker = self.checker(language, ignored)
            if op == 'rules':
                return {'id': rid, 'rules': checker.rules()}
            if op != 'check':
                raise ValueError('unknown operation "%s"' % op)
            ui = str(request.get('ui') or 'en')[:2].lower()
            issues = []
            if 'paragraphs' in request:
                paragraphs = request['paragraphs']
                if not isinstance(paragraphs, list) or not all(isinstance(x, str) for x in paragraphs):
                    raise ValueError('"paragraphs" is a list of strings')
                for number, paragraph in enumerate(paragraphs):
                    for issue in checker.check(paragraph, ui=ui):
                        d = issue_dict(issue, paragraph)
                        d['paragraph'] = number
                        issues.append(d)
            elif isinstance(request.get('text'), str):
                text, offset, byte_offset = request['text'], 0, 0
                for number, line in enumerate(text.split('\n')):
                    for issue in checker.check(line, ui=ui):
                        d = issue_dict(issue, line, offset, byte_offset)
                        d['paragraph'] = number
                        issues.append(d)
                    offset += len(line) + 1
                    byte_offset += len(line.encode('utf-8')) + 1
            else:
                raise ValueError('a "check" request has "text" or "paragraphs"')
            return {'id': rid, 'issues': issues}
        except Exception as e:                  # a bad request never stops the server
            return {'id': rid, 'error': str(e)}

    def serve(self, source, sink):
        """Reads requests (one JSON object per line) from `source` until its end, writes the responses to `sink`."""
        for line in source:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError('a request is a JSON object')
                response = self.handle(request)
            except ValueError as e:
                response = {'id': None, 'error': 'invalid request: %s' % e}
            sink.write(json.dumps(response, ensure_ascii=False) + '\n')
            sink.flush()


# [SECTION] Command line

def main(argv=None):
    """Entry point: command line, or server mode with --serve."""
    ap = argparse.ArgumentParser(prog='grammar_engine', description='Grammar checker made of independent rules.')
    ap.add_argument('files', nargs='*', help='text files (UTF-8); the standard input if none')
    ap.add_argument('--lang', default='en', help='language of the text: fr, en, es...')
    ap.add_argument('--ui', default='en', help='language of the messages')
    ap.add_argument('--ignore', default='', help='identifiers of rules to switch off, separated by commas')
    ap.add_argument('--path', action='append', default=[], help='folder with your own language files and lexicons (repeatable)')
    ap.add_argument('--rules', action='store_true', help='list the rules of the language and quit')
    ap.add_argument('--lines', action='store_true', help='one JSON object per issue and per line instead of one array')
    ap.add_argument('--serve', action='store_true', help='server mode: one JSON request per line on the standard input, one response per line')
    ap.add_argument('--version', action='version', version='grammar_engine ' + __version__)
    args = ap.parse_args(argv)

    if args.serve:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
        Server(args.path).serve(sys.stdin, sys.stdout)
        return 0

    checker = Checker(args.lang, ignored=[r for r in args.ignore.split(',') if r], paths=args.path)
    if args.rules:
        sys.stdout.reconfigure(encoding='utf-8')
        json.dump(checker.rules(), sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0

    if args.files:
        text = ''
        for name in args.files:
            with open(name, encoding='utf-8') as f:
                text += f.read() + '\n'
    else:
        sys.stdin.reconfigure(encoding='utf-8')
        text = sys.stdin.read()
    sys.stdout.reconfigure(encoding='utf-8')

    out = []
    for number, line in enumerate(text.splitlines(), 1):
        for issue in checker.check(line, ui=args.ui):
            d = issue_dict(issue, line)
            d['line'] = number
            if args.lines:
                print(json.dumps(d, ensure_ascii=False))
            else:
                out.append(d)
    if not args.lines:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
