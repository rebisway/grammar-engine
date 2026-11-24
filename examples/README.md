# Examples: a grammar window in six languages

Every example does the same thing: a small window (or page) where you **open a text file or paste a text**, **choose the language**, **run the check** and **see the list of problems** (line, wrong text, suggestion, message, rule). A click on a problem **selects the passage** in the text.

| Folder | Language / toolkit | How it reaches the engine | Checked here |
|---|---|---|---|
| [python/](python/) | Python, tkinter | `import grammar_engine` (`grammar_window.py`), or `--serve` (`grammar_window_serve.py`) | run |
| [csharp/](csharp/) | C#, Windows Forms (.NET 8+) | `python -m grammar_engine --serve` | built and run |
| [java/](java/) | Java 8+, Swing | `--serve` | built (JDK 21, `--release 8`) and run |
| [javascript/](javascript/) | HTML page + small server (`server.py` in Python, `server.js` in Node.js) | `--serve`, behind a small HTTP server | `server.py` run and queried over HTTP; `server.js` **not run here** (no Node.js on the machine) |
| [cpp/](cpp/) | C++17, Dear ImGui + GLFW | `--serve`, with pipes | built (MSVC) and run |
| [powershell/](powershell/) | PowerShell, Windows Forms | `--serve` | run |

The examples are written as tutorials: almost every block has a comment saying why it is there (why the engine runs with `--serve`, how the JSON is written and read, how positions are converted between code points and UTF-8 bytes, how the interface stays responsive, how errors are handled).

## The common idea

```mermaid
sequenceDiagram
    participant W as Window
    participant P as python -m grammar_engine --serve
    W->>P: {"id": 1, "lang": "fr", "ui": "en", "text": "..."} (one line)
    P-->>W: {"id": 1, "issues": [{"rule": "fr.det_number", "start": 4, "end": 8, ...}]} (one line)
    Note over W: the list shows the issues; a click selects start..end
```

The process is started once and kept alive: the lexicon of a language loads at the first request only. The request and the answer are one line each; see [../docs/API.en.md](../docs/API.en.md) for every field.

**Positions.** The engine gives each problem a range in *code points* (`start`, `end`) and in *UTF-8 bytes* (`byte_start`, `byte_end`). Use the one your text widget counts in: Python (tkinter) counts code points; C# and Java strings are UTF-16, so the code point position is converted (the helper is a few lines); Dear ImGui counts bytes of its UTF-8 buffer, so the example uses `byte_start` and `byte_end` directly; JavaScript is UTF-16 like C#.

## The sample texts

[sample_texts/](sample_texts/) holds three short texts with errors (`fr.txt`, `en.txt`, `es.txt`) and, for each language, a Markdown and a plain-text file of mistakes with their corrected version (`fr_errors.md`, `fr_corrected.txt`...). Each example loads `fr.txt` at start and picks the language from the name of the file it opens.

## Prerequisites

Python 3.9 or later on the `PATH` (`python` on Windows, `python3` elsewhere). The engine is found from the folder of the example (two levels up); the variable `GRAMMAR_ENGINE_DIR` overrides it in the programs which start a process.
