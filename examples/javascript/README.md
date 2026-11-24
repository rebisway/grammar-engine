# JavaScript (web page + small server)

A web page cannot start a process, so a small server does it: it starts `python -m grammar_engine --serve` once and turns each `POST /check` of the page into one JSON line for the engine and one line back (`id` matches answers to questions). `index.html` has the editor, the choice of languages, the list and the selection of a passage (`setSelectionRange`, with the code point positions converted to UTF-16).

The server comes twice, with the same endpoints (`GET /`, `GET /sample/<lang>`, `POST /check`):

| File | Needs | Run |
| --- | --- | --- |
| `server.py` | Python 3.9+ only (standard library) | `python server.py` |
| `server.js` | Node.js 14+ and Python 3.9+, no npm package | `node server.js` |

Then open <http://localhost:8089/> in the browser (`PORT` changes the port). The server listens on `127.0.0.1` only.

**Do not open `index.html` as a file** (`file:///...`): the page talks to the server with relative addresses, which do not exist for a page read from the disk. The page then says so in its status line instead of "NetworkError".

**What was run**: `server.py` was started and queried over HTTP (page, sample text, check, bad request): it answers like the engine. `server.js` was not run here (Node.js is not installed on the machine where the examples were written); it was reviewed with care.
