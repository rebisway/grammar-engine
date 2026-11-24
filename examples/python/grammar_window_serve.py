# Grammar window, server version - the same window as grammar_window.py, but the engine runs in ANOTHER PROCESS.
#
# What it shows:
#   - the protocol of "python -m grammar_engine --serve": one JSON request per line in, one JSON response per line out;
#   - how a program in any language can use the engine without importing it. The code of ServeClient below is what a C#,
#     Java or JavaScript client does too (see the other folders in examples/);
#   - the process is started once and stays alive: the lexicon of a language loads at the first request only.
#
# Run it:   python grammar_window_serve.py [file.txt]
#
# SPDX-License-Identifier: MIT

import json
import os
import subprocess
import sys
import threading

import grammar_window as base       # the window, the lists of languages and the helpers are the ones of the other example

ENGINE_DIR = os.path.abspath(os.path.join(base.HERE, '..', '..'))     # the folder which holds the package grammar_engine


class ServeClient:
    """Talks to a "python -m grammar_engine --serve" process."""

    def __init__(self):
        self.lock = threading.Lock()            # one request at a time: the answers come back in the order of the questions
        self.next_id = 1
        try:
            # The engine flushes its output after each answer, so reading a line never waits for more than the answer.
            # It is found from its folder, so the working directory is the folder which contains the package.
            self.process = subprocess.Popen(
                [sys.executable, '-m', 'grammar_engine', '--serve'],
                cwd=ENGINE_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                # Both pipes carry UTF-8, whatever the code page of the console is: we encode and decode by hand.
            )
        except OSError as e:                    # Python not found, folder missing...
            raise RuntimeError('Cannot start the engine: %s' % e)

    def request(self, **fields):
        """Sends one request and waits for its answer. Raises RuntimeError if the process is gone or the answer is an error."""
        with self.lock:
            request_id = self.next_id
            self.next_id += 1
            fields['id'] = request_id
            # ensure_ascii=False keeps the accents as they are; json.dumps never puts a raw line break in its output,
            # so "one line = one request" holds even for a text which has line breaks.
            line = json.dumps(fields, ensure_ascii=False) + '\n'
            try:
                self.process.stdin.write(line.encode('utf-8'))
                self.process.stdin.flush()
                answer = self.process.stdout.readline()
            except (OSError, ValueError):
                answer = b''
            if not answer:                      # the process died: the reason is on its error output
                error = self.process.stderr.read().decode('utf-8', 'replace') if self.process.poll() is not None else ''
                raise RuntimeError('The engine stopped. %s' % error.strip())
            try:
                response = json.loads(answer.decode('utf-8'))
            except ValueError as e:             # the engine only writes JSON, but a host must not trust that blindly
                raise RuntimeError('Invalid answer: %s' % e)
            if response.get('id') != request_id:
                raise RuntimeError('The answer %r does not match the request %d' % (response.get('id'), request_id))
            if 'error' in response:             # {"id": 3, "error": "..."}: the request was wrong, the engine is fine
                raise RuntimeError(response['error'])
            return response

    def close(self):
        """Closing the input of the process ends its loop: it exits by itself."""
        try:
            self.process.stdin.close()
            self.process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()


class ServeWindow(base.GrammarWindow):
    def __init__(self, path=None):
        self.client = None
        super().__init__(path)
        self.title('Grammar window - engine in a separate process')
        self.protocol('WM_DELETE_WINDOW', self.quit_all)

    def work(self, language, ui, text):
        """Runs in the worker thread (see GrammarWindow.start_check): asks the process, puts the answer in the queue."""
        try:
            if self.client is None:
                self.client = ServeClient()
            # "paragraphs" gives the issues of each paragraph with its own positions: "paragraph" is the index in the list
            # and start/end count code points inside that paragraph, exactly what a Tk Text line needs.
            # (With "text" instead, one string with line breaks, the positions would be absolute in the whole text.)
            response = self.client.request(lang=language, ui=ui, paragraphs=text.split('\n'))
            found = []
            for issue in response['issues']:
                found.append({
                    'paragraph': issue['paragraph'], 'start': issue['start'], 'end': issue['end'], 'text': issue['text'],
                    'suggestion': issue['suggestions'][0] if issue['suggestions'] else '',
                    'message': issue['message'], 'rule': issue['rule'],
                })
            self.results.put(('ok', found))
        except RuntimeError as e:
            self.client = None                  # start a new process at the next check
            self.results.put(('error', str(e)))

    def quit_all(self):
        if self.client:
            self.client.close()
        self.destroy()


if __name__ == '__main__':
    ServeWindow(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
