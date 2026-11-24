# Grammar window - the smallest useful program built on the grammar engine, in Python with tkinter.
#
# What it shows:
#   - how to call the engine as a library: import grammar_engine, make one Checker per language, call check();
#   - how to keep a window responsive: the check runs in a worker thread, the result comes back through a queue;
#   - how to turn the ranges of the engine into positions in a tkinter Text widget, and to select a problem on a click.
#
# Run it from anywhere:   python grammar_window.py [file.txt]
# It needs nothing but Python 3.9 or later with tkinter (delivered with Python on Windows and macOS).
#
# SPDX-License-Identifier: MIT

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# The engine is the folder two levels up (grammar-engine/). When it is installed, this block does nothing useful
# and the plain "import grammar_engine" below finds it anyway.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))

import grammar_engine  # noqa: E402

SAMPLES = os.path.abspath(os.path.join(HERE, '..', 'sample_texts'))
LANGUAGES = ['fr', 'en', 'es', 'es-AR']        # the code of a language: its first two letters pick the grammar, "es-AR" a variant
UI_LANGUAGES = ['en', 'fr', 'es']              # the language of the messages


# [SECTION] The logic, without any window: easy to test

_checkers = {}


def checker_for(language):
    """One Checker per language, kept for the whole run: building one loads the lexicon, which is the slow part."""
    if language not in _checkers:
        _checkers[language] = grammar_engine.Checker(language)
    return _checkers[language]


def check_text(language, ui, text):
    """Checks a text paragraph by paragraph (one line = one paragraph).
    Returns a list of dictionaries: paragraph (0-based), start and end (code points inside the paragraph), text, suggestion, message, rule."""
    checker = checker_for(language)
    found = []
    for number, paragraph in enumerate(text.split('\n')):
        # check() returns the issues of one paragraph, sorted by position, with the message already in the language of the interface
        for issue in checker.check(paragraph, ui=ui):
            found.append({
                'paragraph': number,
                'start': issue.start,
                'end': issue.end,
                'text': paragraph[issue.start:issue.end],
                # An empty suggestion means "delete the text" (for instance a repeated word)
                'suggestion': issue.suggestions[0] if issue.suggestions else '',
                'message': issue.message,
                'rule': issue.rule,
            })
    return found


# [SECTION] The window

class GrammarWindow(tk.Tk):
    def __init__(self, path=None):
        super().__init__()
        self.title('Grammar window')
        self.geometry('1000x640')
        self.results = queue.Queue()            # the worker thread puts its answer here, the main thread reads it
        self.issues = []                        # what the list shows, in the same order
        self.busy = False

        # Tool bar: open a file, choose the language of the text and the language of the messages, check
        bar = ttk.Frame(self, padding=4)
        bar.pack(fill='x')
        ttk.Button(bar, text='Open...', command=self.open_file).pack(side='left')
        ttk.Label(bar, text='  Text language:').pack(side='left')
        self.language = tk.StringVar(value='fr')
        ttk.Combobox(bar, textvariable=self.language, values=LANGUAGES, width=7, state='readonly').pack(side='left')
        ttk.Label(bar, text='  Messages:').pack(side='left')
        self.ui = tk.StringVar(value='en')
        ttk.Combobox(bar, textvariable=self.ui, values=UI_LANGUAGES, width=5, state='readonly').pack(side='left')
        self.check_button = ttk.Button(bar, text='Check', command=self.start_check)
        self.check_button.pack(side='left', padx=8)
        self.status = ttk.Label(bar, text='Paste a text or open a file, then press Check.')
        self.status.pack(side='left', padx=8)

        # Two panes: the text above, the list of problems below
        panes = ttk.PanedWindow(self, orient='vertical')
        panes.pack(fill='both', expand=True)
        self.editor = tk.Text(panes, wrap='word', undo=True, font=('Segoe UI', 11))
        self.editor.tag_configure('problem', background='#ffe08a')      # the passage selected in the list
        panes.add(self.editor, weight=3)

        columns = ('line', 'text', 'suggestion', 'message', 'rule')
        self.table = ttk.Treeview(panes, columns=columns, show='headings', selectmode='browse')
        for name, width in zip(columns, (50, 160, 160, 480, 130)):
            self.table.heading(name, text=name.capitalize())
            self.table.column(name, width=width, anchor='w')
        self.table.bind('<<TreeviewSelect>>', self.show_selected)       # a click on a problem selects the passage
        panes.add(self.table, weight=2)

        self.after(100, self.poll)              # start looking at the queue
        if path:
            self.load(path)
        else:
            self.load(os.path.join(SAMPLES, 'fr.txt'))

    # --- Loading a text

    def open_file(self):
        path = filedialog.askopenfilename(initialdir=SAMPLES, filetypes=[('Text', '*.txt *.md'), ('All files', '*.*')])
        if path:
            self.load(path)

    def load(self, path):
        try:
            with open(path, encoding='utf-8') as f:     # the engine works on Unicode text: read the file as UTF-8
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            messagebox.showerror('Grammar window', 'Cannot read %s:\n%s' % (path, e))
            return
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', text.rstrip('\n'))
        # The name of the sample tells its language: fr.txt, en.txt, es.txt
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem in LANGUAGES:
            self.language.set(stem)
        self.start_check()

    # --- Checking, in a thread

    def start_check(self):
        if self.busy:
            return
        self.busy = True
        self.check_button.state(['disabled'])
        self.status.config(text='Checking...')
        text = self.editor.get('1.0', 'end-1c')      # read the widget here: Tk widgets belong to the main thread
        language, ui = self.language.get(), self.ui.get()
        threading.Thread(target=self.work, args=(language, ui, text), daemon=True).start()

    def work(self, language, ui, text):
        """Runs in the worker thread: no widget is touched here, the answer goes through the queue."""
        try:
            self.results.put(('ok', check_text(language, ui, text)))
        except Exception as e:                  # a broken language file, for instance
            self.results.put(('error', str(e)))

    def poll(self):
        """Runs in the main thread every 100 ms: shows the answer of the worker when there is one."""
        try:
            kind, payload = self.results.get_nowait()
        except queue.Empty:
            self.after(100, self.poll)
            return
        self.busy = False
        self.check_button.state(['!disabled'])
        if kind == 'error':
            self.status.config(text='Error: ' + payload)
        else:
            self.show(payload)
        self.after(100, self.poll)

    # --- Showing the problems

    def show(self, issues):
        self.issues = issues
        self.table.delete(*self.table.get_children())
        for number, issue in enumerate(issues):
            self.table.insert('', 'end', iid=str(number), values=(issue['paragraph'] + 1, issue['text'], issue['suggestion'] or '(delete)', issue['message'], issue['rule']))
        self.status.config(text='%d problem(s).' % len(issues) if issues else 'No problem found.')

    def show_selected(self, _event):
        """Selects the passage of the chosen problem in the text.
        Tk indexes a Text by "line.column", lines from 1 and columns from 0, in characters: this is exactly
        (paragraph + 1, start) because the engine counts in code points inside a paragraph."""
        selection = self.table.selection()
        if not selection:
            return
        issue = self.issues[int(selection[0])]
        line = issue['paragraph'] + 1
        first, last = '%d.%d' % (line, issue['start']), '%d.%d' % (line, issue['end'])
        self.editor.tag_remove('problem', '1.0', 'end')
        self.editor.tag_add('problem', first, last)
        self.editor.mark_set('insert', first)
        self.editor.see(first)


if __name__ == '__main__':
    GrammarWindow(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
