import io
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, ROOT)
from grammar_engine.__main__ import Server


def ask(server, **request):
    return server.handle(request)


class ServerRequests(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def test_check_text(self):
        r = ask(self.server, id=1, lang='fr', ui='en', text='Les chat dorment.')
        self.assertEqual(r['id'], 1)
        issue = r['issues'][0]
        self.assertEqual((issue['rule'], issue['text'], issue['suggestions'], issue['start'], issue['end']), ('fr.det_number', 'chat', ['chats'], 4, 8))
        self.assertIn('agree in number', issue['message'])

    def test_positions_in_code_points_and_bytes(self):
        r = ask(self.server, id=2, lang='fr', text='Éé Les chat dorment.')
        issue = r['issues'][0]
        self.assertEqual((issue['start'], issue['byte_start']), (7, 9))        # two accented letters: two more bytes
        self.assertEqual(issue['byte_end'] - issue['byte_start'], 4)

    def test_several_lines_keep_absolute_positions(self):
        text = 'Il mange.\nLes chat dorment.'
        issue = ask(self.server, id=3, lang='fr', text=text)['issues'][0]
        self.assertEqual(text[issue['start']:issue['end']], 'chat')
        self.assertEqual(issue['paragraph'], 1)
        accented = 'Été.\nLes chat dorment.'                  # bytes and code points differ on the first line
        issue = ask(self.server, id=3, lang='fr', text=accented)['issues'][0]
        self.assertEqual((issue['start'], issue['byte_start']), (9, 11))
        self.assertEqual(accented.encode('utf-8')[issue['byte_start']:issue['byte_end']].decode('utf-8'), 'chat')

    def test_paragraphs_have_relative_positions(self):
        r = ask(self.server, id=4, lang='fr', paragraphs=['Il mange.', 'Les chat dorment.'])
        issue = r['issues'][0]
        self.assertEqual((issue['paragraph'], issue['start']), (1, 4))

    def test_ignore_and_ui(self):
        r = ask(self.server, id=5, lang='fr', ui='fr', text='Les chat dorment.', ignore=['fr.det_number'])
        self.assertFalse(any(i['rule'] == 'fr.det_number' for i in r['issues']))
        r = ask(self.server, id=6, lang='fr', ui='fr', text='Les chat dorment.')
        self.assertIn('nombre', r['issues'][0]['message'])

    def test_operations(self):
        self.assertEqual(ask(self.server, id=7, op='ping')['engine'], 'grammar_engine')
        codes = [x['code'] for x in ask(self.server, id=8, op='languages')['languages']]
        self.assertTrue({'fr', 'en', 'es', 'es-AR'} <= set(codes))
        rules = ask(self.server, id=9, op='rules', lang='fr')['rules']
        self.assertTrue(any(x['id'] == 'fr.elision' for x in rules))

    def test_errors(self):
        self.assertIn('error', ask(self.server, id=10, lang='fr'))
        self.assertIn('error', ask(self.server, id=11, op='nothing'))
        self.assertEqual(ask(self.server, id=12, lang='fr', paragraphs='x')['id'], 12)

    def test_stream(self):
        out = io.StringIO()
        self.server.serve(io.StringIO('{"id": 1, "op": "ping"}\n\nnot json\n[1]\n{"id": 2, "lang": "en", "text": "a apple"}\n'), out)
        lines = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0]['id'], 1)
        self.assertIn('error', lines[1])
        self.assertIn('error', lines[2])
        self.assertEqual(lines[3]['issues'][0]['rule'], 'en.a_an')


class ServerProcess(unittest.TestCase):
    def test_process(self):
        request = json.dumps({'id': 1, 'lang': 'es', 'text': 'Los casa son bonitas.'}) + '\n' + json.dumps({'id': 2, 'op': 'ping'}) + '\n'
        done = subprocess.run([sys.executable, '-m', 'grammar_engine', '--serve'], input=request.encode('utf-8'), capture_output=True, cwd=ROOT, timeout=60)
        lines = [json.loads(x) for x in done.stdout.decode('utf-8').splitlines()]
        self.assertEqual(lines[0]['issues'][0]['suggestions'], ['casas'])
        self.assertEqual(lines[1]['id'], 2)


if __name__ == '__main__':
    unittest.main()
