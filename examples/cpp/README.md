# C++ (Dear ImGui)

`main.cpp` (one file) and `CMakeLists.txt`. The engine runs in another process (`CreateProcess` with two pipes on Windows, `fork`/`exec` elsewhere); a tiny JSON reader and writer are included. The request runs in a `std::thread`; the frame loop looks at a flag. Dear ImGui counts its text buffer in UTF-8 bytes, so the fields `byte_start` / `byte_end` select a passage directly.

Build (Dear ImGui and GLFW come from the folder `GRAMMAR_THIRD_DIR`):

```
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DGRAMMAR_THIRD_DIR=C:/path/to/third
cmake --build build
build\grammar_window_cpp.exe [file.txt]
```

Without a window, to test the protocol code alone: `grammar_window_cpp --selftest ../sample_texts/fr.txt fr` prints one line per problem and checks that each byte range really holds the text.

Checked: built with MSVC (no warning), `--selftest` gives 10, 11 and 9 problems on the three samples with every byte range correct, the window opens and the engine process stops with it. The POSIX branch (`fork`/`exec`, GLFW from the system) was not compiled here.
