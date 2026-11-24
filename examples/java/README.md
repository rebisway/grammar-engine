# Java (Swing)

`GrammarWindow.java`: one file, Java 8 or later, no library (a small JSON reader is included). `ProcessBuilder` starts `python -m grammar_engine --serve`; a `SwingWorker` keeps the window responsive; `String.offsetByCodePoints` converts the code point positions of the engine to the UTF-16 positions of the `JTextArea`.

```
javac GrammarWindow.java
java GrammarWindow [file.txt]
```

Run it from this folder (`user.dir` is used to find the engine) or set `GRAMMAR_ENGINE_DIR`.

Checked: compiled with JDK 21 using `--release 8` (no error); started with the same JDK, the window opens and the engine process starts and stops with it. The Java 8 runtime of the machine has no compiler, so it was not run on Java 8 itself.
