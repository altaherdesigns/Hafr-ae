"""Integration tests: build both pages from the real src/ into a temp dir."""
import contextlib
import html
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from html.parser import HTMLParser

import build
from hafrbuild.checks import find_banned, load_banned

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def site_file(tmp, whatsapp):
    path = os.path.join(tmp, 'site.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({"siteUrl": "https://hafr.ae", "whatsapp": whatsapp, "instagram": None}, fh)
    return path


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def run_build(args):
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = build.main(args)
    return code, err.getvalue()


class _Links(HTMLParser):
    """Finds links to a host and whether any ancestor hides them."""

    def __init__(self, host):
        super().__init__()
        self.host, self.stack, self.found = host, [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        hidden = 'hidden' in a or 'display:none' in (a.get('style') or '').replace(' ', '')
        self.stack.append((tag, hidden))
        if tag == 'a' and (a.get('href') or '').rstrip('/') == self.host:
            self.found.append({'rel': a.get('rel') or '', 'hidden': any(h for _, h in self.stack)})

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


class _Bidi(HTMLParser):
    """Records each text occurrence of a Latin word and whether it is isolated."""
    VOID = {'br', 'img', 'meta', 'link', 'input', 'hr', 'source', 'path', 'circle', 'rect', 'use', 'stop'}

    def __init__(self, word):
        super().__init__()
        self.word, self.stack, self.bad, self.seen = word, [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        a = dict(attrs)
        self.stack.append((tag, a.get('dir')))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.word not in data:
            return
        tags = [t for t, _ in self.stack]
        if {'title', 'script', 'style'} & set(tags):
            return
        self.seen += 1
        if not any(t == 'bdi' or d == 'ltr' for t, d in self.stack):
            self.bad.append(data.strip()[:60])


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, 'out')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def prod(self):
        code, err = run_build(['--production', '--out', self.out, '--site', site_file(self.tmp, '971501234567')])
        self.assertEqual(code, 0, err)
        return read(os.path.join(self.out, 'index.html')), read(os.path.join(self.out, 'en', 'index.html'))

    def test_dev_build_writes_both_pages(self):
        code, err = run_build(['--out', self.out, '--site', site_file(self.tmp, None)])
        self.assertEqual(code, 0, err)
        for rel in ('index.html', 'en/index.html', 'sitemap.xml', 'robots.txt', 'assets/css/site.css',
                    'assets/data/slice.json', 'CNAME'):
            self.assertTrue(os.path.exists(os.path.join(self.out, rel)), rel)
        self.assertIn('noindex', read(os.path.join(self.out, 'index.html')))

    def test_production_fails_without_whatsapp(self):
        code, err = run_build(['--production', '--out', self.out, '--site', site_file(self.tmp, None)])
        self.assertEqual(code, 1)
        self.assertIn('whatsapp', err)

    def test_production_succeeds_with_values(self):
        ar, en = self.prod()
        self.assertIn('lang="ar" dir="rtl"', ar)
        self.assertIn('lang="en" dir="ltr"', en)
        self.assertNotIn('[[', ar + en)
        self.assertNotIn('noindex', ar + en)
        self.assertIn('https://wa.me/971501234567?text=', ar)

    def test_production_omits_pending(self):
        ar, en = self.prod()
        self.assertNotIn('data-pending', ar + en)
        for lang, page in (('ar', ar), ('en', en)):
            content = json.loads(read(os.path.join(ROOT, 'src', 'content', f'{lang}.json')))
            for row in content['built']['rows']:
                if row['status'] == 'pending':
                    self.assertNotIn(html.escape(row['build'], quote=False), page)
            if content['kit']['status'] == 'pending':
                for item in content['kit']['items']:
                    self.assertNotIn(html.escape(item, quote=False), page)

    def test_hreflang_canonical(self):
        ar, en = self.prod()
        self.assertIn('<link rel="canonical" href="https://hafr.ae/">', ar)
        self.assertIn('<link rel="canonical" href="https://hafr.ae/en/">', en)
        for page in (ar, en):
            self.assertIn('<link rel="alternate" hreflang="ar" href="https://hafr.ae/">', page)
            self.assertIn('<link rel="alternate" hreflang="en" href="https://hafr.ae/en/">', page)
            self.assertIn('<link rel="alternate" hreflang="x-default" href="https://hafr.ae/">', page)

    def test_altaher_links_present_followed(self):
        for page in self.prod():
            parser = _Links('https://altaherdesign.ae')
            parser.feed(page)
            self.assertEqual(len(parser.found), 2, parser.found)
            for link in parser.found:
                self.assertNotIn('nofollow', link['rel'])
                self.assertFalse(link['hidden'])

    def test_no_banned_terms_in_output(self):
        banned = load_banned(os.path.join(ROOT, 'src', 'banned.json'))
        for page in self.prod():
            self.assertEqual(find_banned(page, banned), [])

    def test_bidi_wrapping(self):
        ar, _ = self.prod()
        parser = _Bidi('HAFR')
        parser.feed(ar)
        self.assertGreater(parser.seen, 0)
        self.assertEqual(parser.bad, [])

    def test_cli_survives_a_legacy_console_encoding(self):
        import subprocess, sys
        env = dict(os.environ, PYTHONIOENCODING='cp1252')
        proc = subprocess.run([sys.executable, os.path.join(ROOT, 'build.py'), '--out', self.out,
                               '--site', site_file(self.tmp, None)],
                              capture_output=True, env=env, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('cp1252', 'replace'))

    def test_lists_match_lengths(self):
        content_dir = os.path.join(self.tmp, 'content')
        shutil.copytree(os.path.join(ROOT, 'src', 'content'), content_dir)
        en_path = os.path.join(content_dir, 'en.json')
        en = json.loads(read(en_path))
        en['make']['items'] = en['make']['items'][:-1]
        with open(en_path, 'w', encoding='utf-8') as fh:
            json.dump(en, fh, ensure_ascii=False)
        code, err = run_build(['--out', self.out, '--site', site_file(self.tmp, None), '--content', content_dir])
        self.assertEqual(code, 1)
        self.assertIn('make.items', err)


if __name__ == '__main__':
    unittest.main()
