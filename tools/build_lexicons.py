"""Builds the lexicons of the grammar engine (data/fr.lex, data/en.lex, data/es.lex) from their public sources, in one command.

    python tools/build_lexicons.py fr            # the French lexicon (a zip of a few MB)
    python tools/build_lexicons.py en es         # the English and the Spanish lexicons (3.4 GB and 1.1 GB of JSON lines, read as a stream)
    python tools/build_lexicons.py all

    python tools/build_lexicons.py en --source kaikki.org-dictionary-English.jsonl     # a file you already have (also .jsonl.gz)
    python tools/build_lexicons.py fr --source lexique-grammalecte-fr-v7.7.zip         # also the .txt inside the zip
    python tools/build_lexicons.py en --keep-source downloads/                         # keep a copy of what is downloaded
    python tools/build_lexicons.py all --out build/                                    # write the files elsewhere

What it does for each language: gets the source (downloads it, or opens the file given with --source), runs the build tool of the language
(tools/build_lexicon.py, build_lexicon_en.py, build_lexicon_es.py) on it, writes the result to a temporary name, checks it with
tools/check_lexicon.py and only then puts it in place of the old file: a build which fails never leaves a broken lexicon.
The step by step procedure, by hand, is in docs/BUILDING_LEXICONS.md.

Only the standard library is used. The sources have their own licenses (see grammar_engine/data/README_lexi*).
"""

import argparse
import gzip
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'grammar_engine', 'data')

# [SECTION] The sources

SOURCES = {
    'fr': {
        'url': 'https://grammalecte.net/dic/lexique-grammalecte-fr-v7.7.zip',
        'tool': 'build_lexicon.py',
        'kind': 'file',                     # the build tool takes the path of a text file
        'license': 'MPL 2.0 (Grammalecte, https://grammalecte.net/) - keep data/README_lexique_fr.txt',
    },
    'en': {
        'url': 'https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl',
        'tool': 'build_lexicon_en.py',
        'kind': 'stream',                   # the build tool reads JSON lines on its standard input
        'license': 'CC BY-SA 4.0 (Wiktionary through kaikki.org) - keep data/README_lexicon_en.txt',
    },
    'es': {
        'url': 'https://kaikki.org/dictionary/Spanish/kaikki.org-dictionary-Spanish.jsonl',
        'tool': 'build_lexicon_es.py',
        'kind': 'stream',
        'license': 'CC BY-SA 4.0 (Wiktionary through kaikki.org) - keep data/README_lexicon_es.txt',
    },
}


# [SECTION] Helpers

def opener(path):
    """Opens a local source for reading as bytes; a .gz file is decompressed on the fly."""
    return gzip.open(path, 'rb') if path.endswith('.gz') else open(path, 'rb')


def download(url, sink, keep=None):
    """Copies the body of `url` into the binary file object `sink`, 1 MB at a time, printing the progress.
    keep: a folder where a copy of what is read is also written (the source is otherwise not kept)."""
    request = urllib.request.Request(url, headers={'User-Agent': 'grammar-engine-build/1.0'})
    copy = None
    if keep:
        os.makedirs(keep, exist_ok=True)
        copy = open(os.path.join(keep, url.rsplit('/', 1)[-1]), 'wb')
    done = 0
    try:
        with urllib.request.urlopen(request) as response:
            total = int(response.headers.get('Content-Length') or 0)
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                sink.write(chunk)
                if copy:
                    copy.write(chunk)
                done += len(chunk)
                print('\r  downloaded %d MB%s' % (done >> 20, ' of %d MB' % (total >> 20) if total else ''), end='', file=sys.stderr, flush=True)
    finally:
        if copy:
            copy.close()
        print('', file=sys.stderr)
    return done


def french_text(source, work):
    """The path of the text file of the Grammalecte lexicon: `source` (a .txt, or the .zip which holds it), else the zip is downloaded."""
    if source is None:
        source = os.path.join(work, 'lexique-grammalecte-fr.zip')
        print('Downloading %s' % SOURCES['fr']['url'])
        with open(source, 'wb') as f:
            download(SOURCES['fr']['url'], f)
    if not source.lower().endswith('.zip'):
        return source
    with zipfile.ZipFile(source) as z:
        names = [n for n in z.namelist() if n.lower().endswith('.txt') and 'lexique' in n.lower()]
        if not names:
            raise SystemExit('No lexicon text file in %s' % source)
        z.extract(names[0], work)
        return os.path.join(work, names[0])


# [SECTION] One language

def build(lang, args):
    """Builds data/<lang>.lex; returns True when it is in place."""
    info = SOURCES[lang]
    tool = os.path.join(HERE, info['tool'])
    out = os.path.join(args.out, lang + '.lex')
    os.makedirs(args.out, exist_ok=True)
    print('== %s: %s' % (lang, info['license']))
    with tempfile.TemporaryDirectory() as work:
        tmp = os.path.join(work, lang + '.lex.tmp')
        if info['kind'] == 'file':
            text = french_text(args.source, work)
            code = subprocess.call([sys.executable, '-I', tool, text, tmp])
        else:
            # The build tool reads the source on its standard input: the source is never written to the disk (unless --keep-source).
            child = subprocess.Popen([sys.executable, '-I', tool, tmp], stdin=subprocess.PIPE)
            try:
                if args.source:
                    print('Reading %s' % args.source)
                    with opener(args.source) as f:
                        shutil.copyfileobj(f, child.stdin, 1 << 20)
                else:
                    print('Downloading %s' % info['url'])
                    download(info['url'], child.stdin, args.keep_source)
            except BrokenPipeError:
                pass                        # the tool stopped: its exit code tells why
            finally:
                try:
                    child.stdin.close()
                except BrokenPipeError:
                    pass
            code = child.wait()
        if code != 0 or not os.path.isfile(tmp):
            print('The build tool failed (exit code %d): %s is unchanged.' % (code, out))
            return False
        if not args.no_check:
            # A lexicon built from a partial source (--sample) is only loaded, not compared with well-known words.
            check = [sys.executable, os.path.join(HERE, 'check_lexicon.py'), tmp] + ([] if args.sample else ['--lang', lang, '--spot'])
            if subprocess.call(check) != 0:
                print('The check failed: %s is unchanged.' % out)
                return False
        shutil.move(tmp, out)
    print('written: %s' % os.path.normpath(out))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description='Builds the lexicons of the grammar engine.')
    ap.add_argument('languages', nargs='+', choices=sorted(SOURCES) + ['all'], help='fr, en, es or all')
    ap.add_argument('--source', help='a local source instead of the download (one language at a time)')
    ap.add_argument('--keep-source', metavar='FOLDER', help='also keep a copy of the downloaded stream (en, es)')
    ap.add_argument('--out', default=DATA, help='folder of the .lex files (default: grammar_engine/data)')
    ap.add_argument('--sample', action='store_true', help='the source is partial (a test file): do not compare with well-known words')
    ap.add_argument('--no-check', action='store_true', help='do not check the file before putting it in place')
    args = ap.parse_args(argv)
    languages = sorted(SOURCES) if 'all' in args.languages else args.languages
    if args.source and len(languages) != 1:
        ap.error('--source is for one language at a time')
    results = {lang: build(lang, args) for lang in languages}
    print('\n' + ', '.join('%s %s' % (lang, 'ok' if ok else 'FAILED') for lang, ok in results.items()))
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
