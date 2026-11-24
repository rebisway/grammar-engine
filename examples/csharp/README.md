# C# (Windows Forms)

`Program.cs` and `GrammarWindow.csproj`: a Windows Forms window (.NET 8 or later, Windows). The engine runs as a child process through `python -m grammar_engine --serve`; `EngineClient` writes one JSON line per request (`System.Text.Json`) and reads one line back. Requests run with `Task.Run`, so the window stays responsive. The code point positions of the engine are converted to UTF-16 (`Utf16Index`) before `RichTextBox.Select`.

```
dotnet run
```

(from this folder; Python on the PATH). `GRAMMAR_ENGINE_DIR` points at the engine when the program is copied elsewhere.

Checked: built with the .NET 10 SDK for `net8.0-windows` without warning; the window opens, lists the 10 problems of `fr.txt`, and the engine process starts and stops with the window.
