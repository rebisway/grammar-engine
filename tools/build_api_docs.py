# grammar-engine - tool: writes docs/API.en.md and docs/API.fr.md from the templates in tools/api_templates/.
#
# The templates hold the prose. Every example in them is a placeholder, {{name}}, which this script replaces by the REAL
# result of running the engine (Python calls, the command line, the --serve process, the bridge), so the examples of the
# reference cannot drift from the code. The script also checks that every signature written in a template
# (`Class.method(arguments)`) exists in the code with the same argument names, and that every rule identifier written in
# backticks and starting with a language code exists in the catalogue.
#
#   python tools/build_api_docs.py            writes the two files
#   python tools/build_api_docs.py --check    only checks that the files on disk are what the templates produce
#
# SPDX-License-Identifier: MIT

import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

import grammar_engine                                       # noqa: E402
from grammar_engine import bridge, core, lexicon, tagger, text as text_module    # noqa: E402

# The sentences of the reference: every example of the document uses them.
FR = 'Les chat dorment sur le canapé.'
EN = 'These book is very old.'
ES = 'Los casa son bonitas.'
TWO_LINES = 'Il mange.\nLes chat dorment.'
REPEAT = 'Il y a un un chat.'


def run_serve(requests):
    """Runs a --serve process on the requests (a list of dictionaries or raw lines); returns [(request line, answer line)]."""
    lines = [r if isinstance(r, str) else json.dumps(r, ensure_ascii=False) for r in requests]
    done = subprocess.run([sys.executable, '-m', 'grammar_engine', '--serve'], input=('\n'.join(lines) + '\n').encode('utf-8'), capture_output=True, cwd=ROOT, timeout=120)
    answers = done.stdout.decode('utf-8').splitlines()
    return list(zip(lines, answers))


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def block(language, text):
    return '```%s\n%s\n```' % (language, text.rstrip('\n'))


def exchange(requests, shorten=None):
    """A --serve conversation as a code block: '>' lines are sent, '<' lines come back (one line each, as on the wire)."""
    out = []
    for request, answer in run_serve(requests):
        out.append('> ' + request)
        out.append('< ' + (shorten(answer) if shorten else answer))
    return block('text', '\n'.join(out))


def abridge_rules(answer, keep=2):
    """The answer to a "rules" request with only the first rules written out (the full list is in RULES.md)."""
    data = json.loads(answer)
    total = len(data['rules'])
    text = json.dumps({'id': data['id'], 'rules': data['rules'][:keep]}, ensure_ascii=False)
    return text[:-2] + ', ...]}' + '   (%d rules in all)' % total


def abridge_languages(answer):
    return answer


# [SECTION] The examples

def build_examples():
    ex = {}
    checker = grammar_engine.Checker('fr')
    issues = checker.check(FR, ui='en')
    ex['fr_sentence'] = FR
    ex['en_sentence'] = EN
    ex['es_sentence'] = ES

    ex['py_basic'] = block('python', "import grammar_engine\n\nchecker = grammar_engine.Checker('fr')\nfor issue in checker.check('%s', ui='en'):\n    print(issue.rule, issue.start, issue.end, issue.suggestions)\n\n# output:\n%s" % (FR, '\n'.join('# ' + ' '.join(map(str, (i.rule, i.start, i.end, i.suggestions))) for i in issues)))
    ex['issue_fields'] = block('python', "issue = checker.check('%s', ui='en')[0]\nissue.as_dict()\n\n# result:\n%s" % (FR, pretty(issues[0].as_dict())))

    # Several paragraphs, one list each
    ex['py_paragraphs'] = block('python', "for number, paragraph in enumerate('Il mange.\\nLes chat dorment.'.split('\\n')):\n    for issue in checker.check(paragraph):\n        print(number, issue.rule, issue.start, issue.end)\n\n# output:\n%s" % '\n'.join('# %d %s %d %d' % (n, i.rule, i.start, i.end) for n, p in enumerate(TWO_LINES.split('\n')) for i in checker.check(p)))

    # Ignoring rules
    plain = [i.rule for i in grammar_engine.Checker('fr').check(FR)]
    quiet = [i.rule for i in grammar_engine.Checker('fr', ignored=['fr.det_number']).check(FR)]
    ex['py_ignore'] = block('python', "grammar_engine.Checker('fr').check(...)                          # rules: %s\ngrammar_engine.Checker('fr', ignored=['fr.det_number']).check(...)    # rules: %s" % (plain, quiet))

    # The interface language
    msg = {ui: grammar_engine.Checker('fr').check(FR, ui=ui)[0].message for ui in ('en', 'fr', 'es', 'de')}
    ex['py_ui'] = block('python', "for ui in ('en', 'fr', 'es', 'de'):\n    print(ui, grammar_engine.Checker('fr').check('%s', ui=ui)[0].message)\n\n# output:\n%s" % (FR, '\n'.join('# %s %s' % kv for kv in msg.items())))

    # An empty suggestion
    rep = grammar_engine.Checker('fr').check(REPEAT)[0]
    ex['empty_suggestion'] = block('python', ">>> [(i.rule, REPEAT[i.start:i.end], i.suggestions) for i in grammar_engine.Checker('fr').check(REPEAT)]\n%s" % [(rep.rule, REPEAT[rep.start:rep.end], rep.suggestions)]).replace('REPEAT', repr(REPEAT))

    # Language and variants
    voseo = grammar_engine.Checker('es-AR').check('Vos tienes razón.')
    ex['py_variant'] = block('python', "grammar_engine.Checker('es-AR').check('Vos tienes razón.')[0].suggestions\n# %s\ngrammar_engine.Checker('es').check('Vos tienes razón.')\n# %s" % (voseo[0].suggestions, grammar_engine.Checker('es').check('Vos tienes razón.')))
    mx = grammar_engine.Checker('es-MX')
    ex['py_variant_fallback'] = block('python', "grammar_engine.Checker('es-MX').grammar.language     # no file langs/es_mx.py: the Spanish grammar is used\n# %r\ngrammar_engine.Checker('zz').grammar.language        # no file at all: the base grammar\n# %r" % (mx.grammar.language, grammar_engine.Checker('zz').grammar.language))

    # The command line
    cli = subprocess.run([sys.executable, '-m', 'grammar_engine', '--lang', 'fr', '--ui', 'en'], input=FR.encode('utf-8'), capture_output=True, cwd=ROOT).stdout.decode('utf-8').replace(chr(13), '')
    ex['cli_json'] = block('text', 'echo "%s" | python -m grammar_engine --lang fr --ui en\n%s' % (FR, cli))
    cli_lines = subprocess.run([sys.executable, '-m', 'grammar_engine', '--lang', 'fr', '--lines'], input=TWO_LINES.encode('utf-8'), capture_output=True, cwd=ROOT).stdout.decode('utf-8').replace(chr(13), '')
    ex['cli_lines'] = block('text', 'python -m grammar_engine --lang fr --lines < two_lines.txt\n%s' % cli_lines)

    # --serve
    ex['serve_basic'] = exchange([{'id': 1, 'lang': 'fr', 'ui': 'en', 'text': FR}])
    ex['serve_text_lines'] = exchange([{'id': 2, 'lang': 'fr', 'ui': 'en', 'text': TWO_LINES}])
    ex['serve_paragraphs'] = exchange([{'id': 3, 'lang': 'fr', 'ui': 'en', 'paragraphs': ['Il mange.', 'Les chat dorment.']}])
    ex['serve_ignore'] = exchange([{'id': 4, 'lang': 'fr', 'ui': 'fr', 'text': FR, 'ignore': ['fr.det_number']}])
    ex['serve_ui'] = exchange([{'id': 5, 'lang': 'fr', 'ui': 'es', 'text': FR}])
    ex['serve_accents'] = exchange([{'id': 6, 'lang': 'fr', 'text': 'Été. Les chat dorment.'}])
    ex['serve_rules'] = exchange([{'id': 7, 'op': 'rules', 'lang': 'es-AR'}], shorten=lambda a: abridge_rules(a))
    ex['serve_languages'] = exchange([{'id': 8, 'op': 'languages'}])
    ex['serve_ping'] = exchange([{'id': 9, 'op': 'ping'}])
    ex['serve_errors'] = exchange([{'id': 10, 'lang': 'fr'}, {'id': 11, 'op': 'spell'}, '{"id": 12, "lang": "fr", "paragraphs": "Il mange."}', 'not json', '[1, 2]'])
    ex['serve_empty'] = exchange([{'id': 13, 'lang': 'fr', 'text': ''}])

    # The first lines of the full answer, to show the fields in the order they are written
    first = json.loads(run_serve([{'id': 1, 'lang': 'fr', 'ui': 'en', 'text': FR}])[0][1])
    ex['serve_issue_pretty'] = block('json', pretty(first))

    # known(): the spelling dictionary of the host
    words = {'mangé', 'manger'}
    no_known = [(i.rule, i.suggestions) for i in grammar_engine.Checker('fr').check('Il a manger.')]
    with_known = [(i.rule, i.suggestions) for i in grammar_engine.Checker('fr', known=lambda w: w in words).check('Il a manger.')]
    ex['py_known'] = block('python', "words = {'mangé', 'manger'}\ngrammar_engine.Checker('fr').check('Il a manger.')                              # %s\ngrammar_engine.Checker('fr', known=lambda w: w in words).check('Il a manger.')   # %s" % (no_known, with_known))

    # The bridge
    bridge._checkers.clear()
    b_check = bridge.check('fr', 'en', '', 'Été. Les chat dorment.')
    b_rules = json.loads(bridge.rules('es-AR'))
    ex['bridge_check'] = block('python', "from grammar_engine import bridge\n\nbridge.check('fr', 'en', '', 'Été. Les chat dorment.')\n# %s" % b_check)
    ex['bridge_rules'] = block('python', "json.loads(bridge.rules('es-AR'))[:2]\n# %s\n# ... %d rules in all" % (json.dumps(b_rules[:2], ensure_ascii=False), len(b_rules)))
    bridge.set_known(lambda w: w in words)
    ex['bridge_known'] = block('python', "bridge.set_known(lambda w: w in {'mangé', 'manger'})\nbridge.check('fr', 'en', '', 'Il a manger.')\n# %s" % bridge.check('fr', 'en', '', 'Il a manger.'))
    bridge.set_known(None)

    # A language of the user
    with tempfile.TemporaryDirectory() as folder:
        code = ("from grammar_engine import core\nfrom grammar_engine.core import rule\n\n\nclass Grammar(core.Grammar):\n    language = 'xx'\n"
                "    messages = {'en': {'xx.shout': 'No capital words: \"{arg}\".'}}\n\n"
                "    @rule('xx.shout', 'style', 0.6)\n    def shout(self, p):\n        \"\"\"a word in capitals: STOP -> stop\"\"\"\n        for tok in p.tokens:\n"
                "            if tok.kind == 'word' and len(tok.text) > 2 and tok.text.isupper():\n                p.add('xx.shout', tok, tok, tok.text.lower(), tok.text)\n")
        with open(os.path.join(folder, 'xx.py'), 'w', encoding='utf-8') as f:
            f.write(code)
        user = grammar_engine.Checker('xx', paths=[folder]).check('Please STOP now.')
        ex['user_language_code'] = block('python', code)
        ex['user_language_run'] = block('python', "checker = grammar_engine.Checker('xx', paths=[r'C:\\Users\\me\\grammar'])\n[(i.rule, i.start, i.end, i.suggestions, i.message) for i in checker.check('Please STOP now.')]\n# %s" % [(i.rule, i.start, i.end, i.suggestions, i.message) for i in user])
    return ex


# [SECTION] Measures

MEASURE_SCRIPT = r"""
import ctypes, sys, time
from ctypes import wintypes
sys.path.insert(0, ROOT)
t = time.perf_counter()
import grammar_engine
t_import = time.perf_counter() - t
t = time.perf_counter()
c = grammar_engine.Checker(CODE)
t_load = time.perf_counter() - t
t = time.perf_counter()
c.check('Test.')
t_first = time.perf_counter() - t
t = time.perf_counter()
for _ in range(50):
    c.check(TEXT)
t_para = (time.perf_counter() - t) / 50

class PMC(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
        'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]

pmc = PMC()
pmc.cb = ctypes.sizeof(pmc)
k = ctypes.WinDLL('kernel32')
k.GetCurrentProcess.restype = ctypes.c_void_p
k.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
k.K32GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
print(t_import, t_load, t_first, t_para, pmc.PeakWorkingSetSize)
"""


def measure():
    """Loading time of each lexicon, time per paragraph and peak memory of a process, on this machine (Windows only: the memory comes from kernel32)."""
    texts = {'fr': 'Les chat dorment sur le canapé et la plupart des gens sont partis hier soir après le dîner.',
             'en': 'These book is very old, and the dogs runs in the garden every morning after the long rain.',
             'es': 'Los casa son bonitas y los niños juega en el patio mientras las madres conversan del tiempo.'}
    rows = {}
    for code, text in texts.items():
        script = 'ROOT = %r\nCODE = %r\nTEXT = %r\n' % (ROOT, code, text) + MEASURE_SCRIPT
        out = subprocess.run([sys.executable, '-c', script], capture_output=True, cwd=ROOT).stdout.decode().split()
        if len(out) == 5:
            rows[code] = tuple(float(x) for x in out)
    return rows


# [SECTION] Checks

def check_signatures(text):
    """Every `Class.method(arguments)` of a template must exist with the same argument names."""
    classes = {'Checker': core.Checker, 'Grammar': core.Grammar, 'Paragraph': core.Paragraph, 'Issue': core.Issue, 'Token': text_module.Token, 'Lexicon': lexicon.Lexicon}
    modules = {'tagger': tagger, 'bridge': bridge, 'text': text_module, 'core': core}
    problems = []
    for owner, name, args in re.findall(r'`(\w+)\.(\w+)\(([^`)]*)\)`', text):
        target = classes.get(owner) or modules.get(owner)
        if target is None or '[' in args or '"' in args:        # an example of a call, not a signature
            continue
        member = getattr(target, name, None)
        if member is None:
            problems.append('%s.%s does not exist' % (owner, name))
            continue
        try:
            names = [p for p in inspect.signature(member).parameters if p != 'self']
        except (TypeError, ValueError):
            continue
        written = [a.split('=')[0].strip().lstrip('*') for a in args.split(',') if a.strip() and a.strip() != '...']
        if written != names[:len(written)] or (len(written) < len(names) and '...' not in args and not all(inspect.signature(member).parameters[n].default is not inspect.Parameter.empty for n in names[len(written):])):
            problems.append('%s.%s(%s) is written with (%s)' % (owner, name, ', '.join(names), ', '.join(written)))
    return problems


def check_rules(text):
    """Every rule identifier written in backticks must exist: as a rule or as an identifier a rule may emit."""
    known = set()
    for code in ('fr', 'en', 'es', 'es-AR', 'xx'):
        known |= set(grammar_engine.Checker(code).grammar._meta)
    known.add('xx.shout')                                   # the rule of the tutorial language, built by build_examples()
    found = re.findall(r'`((?:fr|en|es|es_ar|any)\.[a-z_]+)`', text)
    return ['unknown rule `%s`' % r for r in found if r not in known and r.split('.')[1] not in ('py', 'lex')]


def render(template, values):
    def substitute(match):
        key = match.group(1)
        if key not in values:
            raise KeyError('no example named %s' % key)
        return values[key]
    return re.sub(r'\{\{(\w+)\}\}', substitute, template)


def main():
    check_only = '--check' in sys.argv
    examples = build_examples()
    m = measure()
    if m:
        for code, (t_import, t_load, t_first, t_para, peak) in m.items():
            examples['measure_' + code] = '%.0f ms|%.1f ms|%.1f ms|%.0f MB' % (t_load * 1000, t_first * 1000, t_para * 1000, peak / 1048576)
    examples['version'] = grammar_engine.__version__
    failed = False
    for lang in ('en', 'fr'):
        path = os.path.join(ROOT, 'tools', 'api_templates', 'API.%s.tmpl.md' % lang)
        with open(path, encoding='utf-8') as f:
            template = f.read()
        problems = check_signatures(template) + check_rules(template)
        for p in problems:
            print('%s: %s' % (os.path.basename(path), p))
            failed = True
        result = render(template, examples)
        target = os.path.join(ROOT, 'docs', 'API.%s.md' % lang)
        if check_only:
            mask = lambda t: re.sub(r'<!-- measures:begin -->.*?<!-- measures:end -->', '', t, flags=re.S)     # the measures differ at every run
            with open(target, encoding='utf-8') as f:
                if mask(f.read()) != mask(result):
                    print('%s is not what its template produces' % target)
                    failed = True
        else:
            with open(target, 'w', encoding='utf-8', newline='\n') as f:
                f.write(result)
            print('wrote', target)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
