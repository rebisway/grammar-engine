# Examples index

Complete programs which use the engine, in six languages. Each one lets you open a text file or paste a text, choose the language, run the check and see the problems; a click on a problem selects the passage. They are written as tutorials (almost every block is commented). The common ideas and the way to convert positions are in [../examples/README.md](../examples/README.md); the protocol they use is in [API.en.md](API.en.md) (section 1, "Server mode").

| Example | File | What it teaches | Checked here |
|---|---|---|---|
| Python, tkinter, library | [grammar_window.py](../examples/python/grammar_window.py) | `import grammar_engine`; a worker thread and a queue; Tk text indexes | run |
| Python, tkinter, process | [grammar_window_serve.py](../examples/python/grammar_window_serve.py) | the `--serve` protocol: `id`, errors, a dead process | run |
| C#, Windows Forms | [Program.cs](../examples/csharp/Program.cs) | `Process`, `System.Text.Json`, `Task.Run`, UTF-16 positions | built and run |
| Java, Swing | [GrammarWindow.java](../examples/java/GrammarWindow.java) | `ProcessBuilder`, a small JSON reader, `SwingWorker`, `offsetByCodePoints` | built (JDK 21, `--release 8`) and run |
| JavaScript, page + server | [index.html](../examples/javascript/index.html), [server.py](../examples/javascript/server.py), [server.js](../examples/javascript/server.js) | a server which owns the process, answers matched by `id`, UTF-16 positions in a browser; the page is opened through the server, never as a file | `server.py` run and queried; `server.js` not run (no Node.js here) |
| C++, Dear ImGui | [main.cpp](../examples/cpp/main.cpp) | pipes, a JSON reader, `std::thread`, selection in UTF-8 bytes | built and run |
| PowerShell, Windows Forms | [grammar_window.ps1](../examples/powershell/grammar_window.ps1) | `ReadLineAsync` and a timer instead of threads | run |

The sample texts, with errors, are in [../examples/sample_texts/](../examples/sample_texts/): short texts `fr.txt`, `en.txt`, `es.txt` and, for each language, full texts of mistakes and their corrected version in `.md` and `.txt` (see its [README](../examples/sample_texts/README.md)).
