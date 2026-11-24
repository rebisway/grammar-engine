# Python (tkinter)

Two programs, no dependency but Python 3.9+ with tkinter (included with Python on Windows and macOS):

- `grammar_window.py`: calls the engine as a library (`import grammar_engine`, one `Checker` per language). The check runs in a worker thread; the answer comes back through a queue read by a Tk timer. The function `check_text()` has no window in it and can be tested alone.
- `grammar_window_serve.py`: the same window, but the engine runs in another process through `--serve`. The class `ServeClient` shows the protocol (one JSON request per line, one answer per line, `id` to match them, errors, a dead process).

```
python grammar_window.py [file.txt]
python grammar_window_serve.py [file.txt]
```

Checked: both start, check `sample_texts/fr.txt` and list 10 problems; a click on a row selects the passage (the tag `problem` of the Text widget).
