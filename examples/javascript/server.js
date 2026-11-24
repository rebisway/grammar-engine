// Grammar page in JavaScript: a small Node.js server and a web page (index.html).
//
// What it shows:
//   - a browser cannot start a process, so a tiny Node.js server does it: it starts "python -m grammar_engine --serve"
//     once, and turns every HTTP request of the page into one JSON line for the engine and one JSON line back;
//   - how to match answers to questions with the "id" field when several requests may be waiting;
//   - how to serve the page and the sample texts with the standard library only (http, fs, child_process, readline).
//
// Run it:   node server.js            then open http://localhost:8089/
// Needs Node.js 14 or later and Python 3.9+ on the PATH. No npm package.
//
// SPDX-License-Identifier: MIT

'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { spawn } = require('child_process');

const PORT = Number(process.env.PORT || 8089);
// The engine is the folder two levels up (grammar-engine/); GRAMMAR_ENGINE_DIR overrides it.
const ENGINE_DIR = process.env.GRAMMAR_ENGINE_DIR || path.resolve(__dirname, '..', '..');
const SAMPLES = path.join(ENGINE_DIR, 'examples', 'sample_texts');

// [SECTION] The engine process

let engine = null;                  // the child process, started at the first request
const waiting = new Map();          // id -> { resolve, reject }: the requests which have no answer yet
let nextId = 1;

function startEngine() {
  const child = spawn(process.platform === 'win32' ? 'python' : 'python3', ['-m', 'grammar_engine', '--serve'], {
    cwd: ENGINE_DIR,                // the folder which contains the package grammar_engine
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  child.stdin.setDefaultEncoding('utf8');   // the protocol is UTF-8 on both pipes
  child.stdout.setEncoding('utf8');

  // The engine answers one JSON object per line. readline cuts the stream into lines, however the chunks arrive.
  readline.createInterface({ input: child.stdout }).on('line', (line) => {
    let answer;
    try {
      answer = JSON.parse(line);
    } catch (e) {
      return;                       // not JSON: ignore the line (the engine never writes any)
    }
    const entry = waiting.get(answer.id);       // the id tells which question this answers
    if (!entry) return;
    waiting.delete(answer.id);
    if (answer.error) entry.reject(new Error(answer.error));
    else entry.resolve(answer);
  });

  let errorText = '';
  child.stderr.on('data', (chunk) => { errorText += chunk; });
  // The process may fail to start (Python not installed) or die later: every waiting request gets the error.
  const fail = (message) => {
    engine = null;
    for (const entry of waiting.values()) entry.reject(new Error(message));
    waiting.clear();
  };
  child.on('error', (e) => fail('Cannot start Python: ' + e.message));
  child.on('exit', (code) => fail('The engine stopped (code ' + code + '). ' + errorText.trim()));
  return child;
}

// Sends one request to the engine and returns a promise of its answer.
function ask(request) {
  if (!engine) engine = startEngine();
  return new Promise((resolve, reject) => {
    const id = nextId++;
    waiting.set(id, { resolve, reject });
    // JSON.stringify never writes a raw line break, so "one line = one request" holds for any text.
    engine.stdin.write(JSON.stringify(Object.assign({ id }, request)) + '\n', (error) => {
      if (error) { waiting.delete(id); reject(error); }
    });
  });
}

// [SECTION] The HTTP server

function send(res, status, type, body) {
  res.writeHead(status, { 'Content-Type': type + '; charset=utf-8' });
  res.end(body);
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) {
    return send(res, 200, 'text/html', fs.readFileSync(path.join(__dirname, 'index.html')));
  }
  // /sample/fr, /sample/en, /sample/es: the sample texts
  const sample = /^\/sample\/(fr|en|es)$/.exec(req.url);
  if (req.method === 'GET' && sample) {
    return send(res, 200, 'text/plain', fs.readFileSync(path.join(SAMPLES, sample[1] + '.txt')));
  }
  // POST /check with {"lang", "ui", "text"}: the page's request, forwarded to the engine
  if (req.method === 'POST' && req.url === '/check') {
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => { body += chunk; if (body.length > 2e6) req.destroy(); });   // a text of 2 MB at most
    req.on('end', () => {
      let input;
      try {
        input = JSON.parse(body);
      } catch (e) {
        return send(res, 400, 'application/json', JSON.stringify({ error: 'Invalid JSON' }));
      }
      ask({ lang: input.lang, ui: input.ui, text: input.text })
        .then((answer) => send(res, 200, 'application/json', JSON.stringify(answer)))
        .catch((e) => send(res, 500, 'application/json', JSON.stringify({ error: e.message })));
    });
    return;
  }
  send(res, 404, 'text/plain', 'Not found');
});

server.listen(PORT, '127.0.0.1', () => console.log('Grammar page on http://localhost:' + PORT + '/'));

// Stop the engine with the server: closing its input ends its loop.
process.on('SIGINT', () => { if (engine) engine.stdin.end(); process.exit(0); });
