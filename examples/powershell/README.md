# PowerShell (Windows Forms)

`grammar_window.ps1`: a Windows Forms window in Windows PowerShell 5.1 (or PowerShell 7 on Windows). The engine runs through `python -m grammar_engine --serve`. No thread is needed: `StreamReader.ReadLineAsync()` returns a task and a Forms timer looks every 100 ms whether it has finished. The code point positions are converted to UTF-16 before `RichTextBox.Select`.

```
powershell -ExecutionPolicy Bypass -File grammar_window.ps1 [file.txt]
```

The file contains only ASCII, so Windows PowerShell 5.1 reads it correctly without a byte order mark.

Checked: the window opens, lists the 10 problems of `fr.txt` and stops the engine when it closes.
