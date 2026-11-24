# Grammar page, the server side in Python: the same server as server.js, for a machine without Node.js.
#
# What it shows:
#   - a web page cannot start a process, so this small server does it: it starts "python -m grammar_engine --serve" once and turns
#     every HTTP request of the page (index.html) into one JSON line for the engine and one JSON line back;
#   - how to share one engine process between several requests (a lock keeps the lines of two requests from being mixed);
#   - how to serve the page and the sample texts with the standard library only.
#
# Run it:   python server.py            then open http://localhost:8089/
# Do not open index.html as a file: the page needs this server (a page opened from the disk cannot reach it).
#
# SPDX-License-Identifier: MIT

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get('PORT', '8089'))
HERE = os.path.dirname(os.path.abspath(__file__))
# The engine is the folder two levels up (grammar-engine/); GRAMMAR_ENGINE_DIR overrides it.
ENGINE_DIR = os.environ.get('GRAMMAR_ENGINE_DIR', os.path.abspath(os.path.join(HERE, '..', '..')))
SAMPLES = os.path.join(ENGINE_DIR, 'examples', 'sample_texts')


# [SECTION] The engine process

class Engine:
    """The process `python -m grammar_engine --serve`, started at the first request and shared by all the requests."""

    def __init__(self):
        self.process = None
        self.lock = threading.Lock()        # one question at a time: the answer to a line is the next line
        self.next_id = 1

    def start(self):
        # The same Python which runs this server; the folder with the package grammar_engine is the working folder.
        self.process = subprocess.Popen([sys.executable, '-m', 'grammar_engine', '--serve'], cwd=ENGINE_DIR, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def ask(self, request):
        """Sends one request (a dictionary) and returns the answer (a dictionary). Raises RuntimeError if the engine fails."""
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self.start()
            request = dict(request, id=self.next_id)
            self.next_id += 1
            try:
                # json.dumps never writes a raw line break, so "one line = one request" holds for any text.
                # The protocol is UTF-8 on both pipes: the bytes are written and read without any conversion of the platform.
                self.process.stdin.write((json.dumps(request, ensure_ascii=False) + '\n').encode('utf-8'))
                self.process.stdin.flush()
                line = self.process.stdout.readline()
            except OSError as e:
                raise RuntimeError('The engine stopped: %s' % e)
            if not line:
                raise RuntimeError('The engine stopped. ' + self.process.stderr.read().decode('utf-8', 'replace').strip())
            answer = json.loads(line.decode('utf-8'))
            if answer.get('error'):
                raise RuntimeError(answer['error'])
            return answer

    def stop(self):
        """Closing the input of the engine ends its loop."""
        if self.process is not None and self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=5)


engine = Engine()


# [SECTION] The HTTP server

class Handler(BaseHTTPRequestHandler):
    def send(self, status, content_type, body):
        """One complete answer."""
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # The page
        if self.path in ('/', '/index.html'):
            with open(os.path.join(HERE, 'index.html'), 'rb') as f:
                return self.send(200, 'text/html', f.read())
        # /sample/fr, /sample/en, /sample/es: the sample texts
        for lang in ('fr', 'en', 'es'):
            if self.path == '/sample/' + lang:
                with open(os.path.join(SAMPLES, lang + '.txt'), 'rb') as f:
                    return self.send(200, 'text/plain', f.read())
        self.send(404, 'text/plain', 'Not found')

    def do_POST(self):
        # POST /check with {"lang", "ui", "text"}: the request of the page, forwarded to the engine
        if self.path != '/check':
            return self.send(404, 'text/plain', 'Not found')
        size = int(self.headers.get('Content-Length') or 0)
        if size > 2_000_000:                                        # a text of 2 MB at most
            return self.send(413, 'application/json', json.dumps({'error': 'Text too long'}))
        try:
            data = json.loads(self.rfile.read(size).decode('utf-8'))
        except ValueError:
            return self.send(400, 'application/json', json.dumps({'error': 'Invalid JSON'}))
        try:
            answer = engine.ask({'lang': data.get('lang'), 'ui': data.get('ui'), 'text': data.get('text', '')})
            self.send(200, 'application/json', json.dumps(answer, ensure_ascii=False))
        except RuntimeError as e:
            self.send(500, 'application/json', json.dumps({'error': str(e)}, ensure_ascii=False))

    def log_message(self, format, *args):
        pass                                                        # no line per request on the console


if __name__ == '__main__':
    # Listens on this computer only: the page and the engine are not meant to be reached from the network.
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print('Grammar page on http://localhost:%d/  (Ctrl+C to stop)' % PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
