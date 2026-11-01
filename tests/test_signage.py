"""The signage section: both languages, linked as a pair, with structured data,
working links, the guides' rulebook, and a place on the home pages and in the sitemap."""
import json
import os
import re
import shutil
import tempfile
import unittest
from html.parser import HTMLParser

from hafrbuild import signage
from hafrbuild.checks import find_banned, load_banned
from test_build import read, run_build, site_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1, self.hrefs, self.ids, self.alts, self.faq_items = 0, [], set(), {}, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'h1':
            self.h1 += 1
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'a' and a.get('href'):
            self.hrefs.append(a['href'])
        if tag == 'link' and a.get('rel') == 'alternate' and a.get('hreflang'):
            self.alts[a['hreflang']] = a['href']
        if tag == 'details' and 'faq__item' in (a.get('class') or ''):
            self.faq_items += 1


def parse(html_text):
    p = _Page()
    p.feed(html_text)
    return p


def graph(html_text):
    out = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S):
        out += json.loads(block).get('@graph', [])
    return {g['@type']: g for g in out}


class SignageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.out = os.path.join(cls.tmp, 'out')
        code, err = run_build(['--production', '--out', cls.out, '--site', site_file(cls.tmp, '971501234567')])
        assert code == 0, err
        cls.pages = signage.load(ROOT)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def html(self, url):
        return read(os.path.join(self.out, *url.strip('/').split('/'), 'index.html'))

    def urls(self):
        for lang in ('ar', 'en'):
            yield lang, signage.BASE[lang]
            for p in self.pages[lang]:
                yield lang, p.url

    def test_every_page_exists_in_both_languages(self):
        self.assertGreaterEqual(len(self.pages['en']), 6)
        self.assertEqual([p.slug for p in self.pages['ar']], [p.slug for p in self.pages['en']])

    def test_hreflang_pairs_point_at_each_other(self):
        for lang, url in self.urls():
            doc = parse(self.html(url))
            self.assertEqual(set(doc.alts), {'ar', 'en', 'x-default'}, url)
            self.assertTrue(doc.alts[lang].endswith(url), url)
            other = doc.alts['en' if lang == 'ar' else 'ar'].replace('https://hafr.ae', '')
            self.assertTrue(parse(self.html(other)).alts[lang].endswith(url), url)

    def test_one_h1_and_every_internal_link_resolves(self):
        for lang, url in self.urls():
            doc = parse(self.html(url))
            self.assertEqual(doc.h1, 1, url)
            for href in doc.hrefs:
                if href.startswith(('https://', 'mailto:')):
                    continue
                path, _, anchor = href.partition('#')
                if path == '':
                    self.assertIn(anchor, doc.ids, f'{href} on {url}')
                elif path.endswith('.xml'):
                    self.assertTrue(os.path.isfile(os.path.join(self.out, *path.strip('/').split('/'))), href)
                else:
                    self.assertTrue(os.path.isfile(os.path.join(self.out, *path.strip('/').split('/'), 'index.html')),
                                    f'{href} on {url}')

    def test_titles_descriptions_and_structured_data(self):
        for lang, url in self.urls():
            text = self.html(url)
            title = re.search(r'<title>(.*?)</title>', text).group(1)
            self.assertLessEqual(len(title), 72, title)
            desc = re.search(r'<meta name="description" content="([^"]*)"', text).group(1)
            self.assertTrue(70 <= len(desc) <= 160, (url, len(desc)))
            g = graph(text)
            biz = g['LocalBusiness']
            self.assertEqual(biz['address']['addressLocality'], 'Fujairah')
            self.assertEqual(biz['telephone'], '+971501234567')
            if url != signage.BASE[lang]:
                self.assertEqual(g['Service']['provider']['@id'], biz['@id'])
                self.assertEqual(len(g['FAQPage']['mainEntity']), parse(text).faq_items, url)
                self.assertEqual(g['WebPage']['inLanguage'], lang)

    def test_arabic_headings_get_arabic_ids(self):
        for p in self.pages['ar']:
            ids = re.findall(r'<h2 id="([^"]+)"', self.html(p.url))
            self.assertTrue(ids)
            self.assertFalse([i for i in ids if i.startswith('section')], p.slug)

    def test_guides_rulebook(self):
        banned = load_banned(os.path.join(ROOT, 'src', 'blog', 'banned.json'))
        for _, url in self.urls():
            self.assertEqual(find_banned(self.html(url), banned), [], url)

    def test_home_pages_feature_the_section(self):
        for lang, home in (('ar', '/'), ('en', '/en/')):
            text = read(os.path.join(self.out, *home.strip('/').split('/'), 'index.html'))
            self.assertIn('id="signage"', text)
            for p in self.pages[lang]:
                self.assertIn(f'href="{p.url}"', text)
            self.assertGreaterEqual(text.count(f'href="{signage.BASE[lang]}"'), 2)

    def test_sitemap_lists_both_languages_with_alternates(self):
        sm = read(os.path.join(self.out, 'sitemap.xml'))
        for _, url in self.urls():
            self.assertIn(f'<loc>https://hafr.ae{url}</loc>', sm)
        self.assertIn('hreflang="x-default" href="https://hafr.ae/signage/"', sm)


if __name__ == '__main__':
    unittest.main()
