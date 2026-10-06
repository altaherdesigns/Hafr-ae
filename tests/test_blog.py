"""The guides: Markdown subset, posts, links, figures, and their place in the build."""
import contextlib
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from html.parser import HTMLParser

import build
from hafrbuild import blog
from hafrbuild.checks import find_banned, load_banned
from hafrbuild.markdown import MarkdownError, Renderer, smart_quotes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def md(source, links=None):
    seen = []

    def resolve(href):
        seen.append(href)
        if links is not None and href in links:
            return links[href]
        return href, href.startswith('https://')

    def figure(src, alt, caption, n):
        return f'<figure data-n="{n}">{alt}|{caption}</figure>'
    r = Renderer(resolve, figure)
    return r.render(source), r, seen


class MarkdownTests(unittest.TestCase):
    def test_paragraphs_headings_and_inline(self):
        out, r, _ = md('## A title\n\nSome **bold** and *soft* text with a [link](https://example.com).')
        self.assertIn('<h2 id="a-title">A title</h2>', out)
        self.assertIn('<strong>bold</strong>', out)
        self.assertIn('<em>soft</em>', out)
        self.assertIn('<a href="https://example.com" target="_blank" rel="noopener">link</a>', out)
        self.assertEqual(r.headings, [(2, 'a-title', 'A title')])

    def test_html_is_escaped_or_refused(self):
        with self.assertRaises(MarkdownError):
            md('Text with <script>alert(1)</script>')
        out, _, _ = md('Under 5 m & over 3 < 4')
        self.assertIn('&amp;', out)
        self.assertIn('3 &lt; 4', out)

    def test_quotes_curl_and_close_after_bold(self):
        out, _, _ = md('He said "**Villa 24**" and it\'s fine.')
        self.assertIn('“<strong>Villa 24</strong>”', out)
        self.assertIn('it’s', out)
        self.assertEqual(smart_quotes('"a" \'b\''), '“a” ‘b’')

    def test_lists_and_tables(self):
        out, _, _ = md('- one\n- two\n\n1. first\n2. second\n\n| A | B |\n|---|---|\n| x | y |')
        self.assertIn('<ul><li>one</li><li>two</li></ul>', out)
        self.assertIn('<ol><li>first</li><li>second</li></ol>', out)
        self.assertIn('<th scope="row" data-label="A">x</th><td data-label="B">y</td>', out)

    def test_nested_lists_and_quotes_refused(self):
        for bad in ('- a\n  - b', '> quoted', '```\ncode\n```', '# H1 in body', '#### deep'):
            with self.assertRaises(MarkdownError, msg=bad):
                md(bad)

    def test_faq_section(self):
        out, r, _ = md('## Frequently asked questions\n\n**Is it so?**\nYes, it is.\n\n**Why?**\nBecause.')
        self.assertIn('<details class="faq__item"><summary class="faq__q">Is it so?</summary>', out)
        self.assertEqual([q for q, _, _ in r.faq], ['Is it so?', 'Why?'])
        with self.assertRaises(MarkdownError):
            md('## Frequently asked questions\n\nNot a question line.')

    def test_figure_line(self):
        out, r, _ = md('![A long description of the drawing](figures/x.svg "The caption")')
        self.assertIn('<figure data-n="1">A long description of the drawing|The caption</figure>', out)
        with self.assertRaises(MarkdownError):
            md('Inline ![image](figures/x.svg) inside text')

    def test_arabic_runs_are_marked(self):
        out, _, _ = md('Arabic-Indic numerals (١٢٣) for style.')
        self.assertIn('<span lang="ar" dir="rtl">١٢٣</span>', out)

    def test_unwrapped_link(self):
        out, _, _ = md('See [the guide](/blog/x/).', links={'/blog/x/': (None, False)})
        self.assertIn('See the guide.', out)


def write_post(directory, name, meta, body='Hello there.'):
    lines = ['---'] + [f'{k}: {v}' for k, v in meta.items()] + ['---', '', body]
    with open(os.path.join(directory, name), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))


BASE_META = {'title': '"A guide"', 'slug': 'a-guide', 'date': '2026-10-06', 'cta': '"Ask us."',
             'meta_description': '"' + 'A description that is long enough to pass the length check, comfortably.' + '"'}


class PostTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_loads_and_fills_tokens(self):
        write_post(self.dir, '01-a-guide.md', {**BASE_META, 'title': '"From {{PRICE_FROM}}"'})
        posts = blog.load_posts(self.dir, {'PRICE_FROM': 'AED 299'})
        self.assertEqual(posts[0].title, 'From AED 299')
        self.assertEqual(posts[0].url, '/en/blog/a-guide/')
        self.assertEqual(posts[0].num, '01')

    def test_rejects_bad_posts(self):
        cases = [
            ('01-a-guide.md', {**BASE_META, 'colour': 'red'}, 'unknown front matter key'),
            ('01-other.md', BASE_META, 'does not match the file name'),
            ('1-a-guide.md', BASE_META, 'file name must be NN-slug.md'),
            ('01-a-guide.md', {**BASE_META, 'meta_description': '"Too short."'}, 'meta_description'),
            ('01-a-guide.md', {**BASE_META, 'title': '"{{NOPE}}"'}, 'unknown token'),
            ('01-a-guide.md', {**BASE_META, 'date': '6 Oct'}, 'YYYY-MM-DD'),
        ]
        for name, meta, needle in cases:
            for f in os.listdir(self.dir):
                os.remove(os.path.join(self.dir, f))
            write_post(self.dir, name, meta)
            with self.assertRaises(blog.BlogError, msg=needle) as ctx:
                blog.load_posts(self.dir, {})
            self.assertIn(needle, str(ctx.exception))

    def test_null_token_is_an_error(self):
        write_post(self.dir, '01-a-guide.md', BASE_META, 'From {{PRICE_FROM}}.')
        with self.assertRaises(blog.BlogError):
            blog.load_posts(self.dir, {'PRICE_FROM': None})

    def test_links_between_guides(self):
        write_post(self.dir, '01-a-guide.md', BASE_META, 'See [two](/blog/two/) and [three](/blog/three/).')
        write_post(self.dir, '02-two.md', {**BASE_META, 'slug': 'two'})
        write_post(self.dir, '03-three.md', {**BASE_META, 'slug': 'three', 'draft': 'true'})
        posts = blog.load_posts(self.dir, {})
        prod = blog.render_body(posts[0], posts, production=True, figures_dir=self.dir, root=self.dir)
        self.assertIn('<a href="/en/blog/two/">two</a>', prod.html)
        self.assertIn('and three.', prod.html)
        self.assertEqual(prod.unwrapped, ['three'])
        dev = blog.render_body(posts[0], posts, production=False, figures_dir=self.dir, root=self.dir)
        self.assertIn('<a href="/en/blog/three/">three</a>', dev.html)

    def test_bad_links_fail(self):
        for body in ('[x](/blog/missing/)', '[x](http://insecure.example)', '[x](https://wa.me/971500000000)',
                     '[x](/somewhere/)', '[x](/en/#nowhere)'):
            write_post(self.dir, '01-a-guide.md', BASE_META, body)
            posts = blog.load_posts(self.dir, {})
            with self.assertRaises(blog.BlogError, msg=body):
                blog.render_body(posts[0], posts, production=True, figures_dir=self.dir, root=self.dir)

    def test_svg_figures_are_inlined_safely(self):
        figs = os.path.join(self.dir, 'figures')
        os.mkdir(figs)
        with open(os.path.join(figs, 'ok.svg'), 'w') as fh:
            fh.write('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" width="10">'
                     '<metadata>m</metadata><rect width="5" height="5"/></svg>')
        with open(os.path.join(figs, 'bad.svg'), 'w') as fh:
            fh.write('<svg viewBox="0 0 10 10"><script>x()</script></svg>')
        write_post(self.dir, '01-a-guide.md', BASE_META, '![A drawing of a small square](figures/ok.svg "Cap")')
        posts = blog.load_posts(self.dir, {})
        r = blog.render_body(posts[0], posts, production=True, figures_dir=figs, root=self.dir)
        self.assertIn('role="img" aria-label="A drawing of a small square"', r.html)
        self.assertNotIn('metadata', r.html)
        self.assertNotIn('width="10"', r.html)
        self.assertIn('<figcaption><span class="fig__n">Fig. 1</span> Cap</figcaption>', r.html)
        write_post(self.dir, '01-a-guide.md', BASE_META, '![A drawing of a small square](figures/bad.svg)')
        posts = blog.load_posts(self.dir, {})
        with self.assertRaises(blog.BlogError):
            blog.render_body(posts[0], posts, production=True, figures_dir=figs, root=self.dir)

    def test_image_sizes(self):
        png = os.path.join(self.dir, 'x.png')
        with open(png, 'wb') as fh:
            fh.write(b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x0dIHDR' + (640).to_bytes(4, 'big') + (360).to_bytes(4, 'big') + b'\x08' * 13)
        self.assertEqual(blog.image_size(png), (640, 360))


def run_build(args):
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = build.main(args)
    return code, err.getvalue()


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


class _Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs, self.h1 = set(), [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'a' and a.get('href'):
            self.hrefs.append(a['href'])
        if tag == 'h1':
            self.h1 += 1


class BlogBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.out = os.path.join(cls.tmp, 'out')
        site = os.path.join(cls.tmp, 'site.json')
        with open(site, 'w', encoding='utf-8') as fh:
            json.dump({"siteUrl": "https://hafr.ae", "whatsapp": "971501234567", "instagram": None}, fh)
        code, err = run_build(['--production', '--out', cls.out, '--site', site])
        assert code == 0, err
        cls.posts = blog.load_posts(os.path.join(ROOT, 'src', 'blog', 'en'),
                                    {k: v for k, v in json.loads(read(os.path.join(ROOT, 'src', 'blog', 'facts.json'))).items()
                                     if not k.startswith('_')})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def page(self, rel):
        return read(os.path.join(self.out, *rel.strip('/').split('/'), 'index.html'))

    def test_published_guides_and_no_drafts(self):
        for p in self.posts:
            path = os.path.join(self.out, 'en', 'blog', p.slug, 'index.html')
            self.assertEqual(os.path.exists(path), not p.draft, p.slug)
        index = self.page('/en/blog/')
        for p in self.posts:
            self.assertEqual(p.url in index, not p.draft, p.slug)
        self.assertNotIn('data-draft', index)

    def test_every_internal_link_and_anchor_resolves(self):
        known = {'/', '/en/', '/en/blog/', '/en/blog/feed.xml'}
        known |= {p.url for p in self.posts if not p.draft}
        for p in [q for q in self.posts if not q.draft] + [None]:
            html_text = self.page(p.url if p else '/en/blog/')
            parser = _Ids()
            parser.feed(html_text)
            self.assertEqual(parser.h1, 1)
            for href in parser.hrefs:
                if href.startswith(('https://', 'mailto:')):
                    continue
                path, _, anchor = href.partition('#')
                if path == '':
                    self.assertIn(anchor, parser.ids, f'{href} on {p.slug if p else "index"}')
                else:
                    self.assertIn(path, known, f'{href} on {p.slug if p else "index"}')

    def test_guides_pass_their_rulebook_and_landing_keeps_its_own(self):
        guides = load_banned(os.path.join(ROOT, 'src', 'blog', 'banned.json'))
        landing = load_banned(os.path.join(ROOT, 'src', 'banned.json'))
        for p in self.posts:
            if not p.draft:
                self.assertEqual(find_banned(self.page(p.url), guides), [], p.slug)
        for rel in ('/', '/en/'):
            self.assertEqual(find_banned(self.page(rel), landing), [], rel)

    def test_structured_data_and_meta(self):
        for p in self.posts:
            if p.draft:
                continue
            page = self.page(p.url)
            data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1))
            types = [n['@type'] for n in data['@graph']]
            self.assertIn('BlogPosting', types)
            self.assertIn('BreadcrumbList', types)
            self.assertIn('FAQPage', types)
            self.assertIn(f'<link rel="canonical" href="https://hafr.ae{p.url}">', page)
            self.assertIn(f'https://hafr.ae/assets/blog/og/{p.slug}.', page)
            self.assertNotIn('noindex', page)
            self.assertNotIn('{{', page)
            self.assertNotIn('Alt text', page)

    def test_sitemap_and_feed(self):
        sitemap = read(os.path.join(self.out, 'sitemap.xml'))
        feed = read(os.path.join(self.out, 'en', 'blog', 'feed.xml'))
        for p in self.posts:
            self.assertEqual(f'https://hafr.ae{p.url}' in sitemap, not p.draft, p.slug)
            self.assertEqual(f'https://hafr.ae{p.url}' in feed, not p.draft, p.slug)
        self.assertIn('<loc>https://hafr.ae/en/blog/</loc>', sitemap)

    def test_guides_link_on_landing(self):
        en, ar = self.page('/en/'), self.page('/')
        self.assertEqual(en.count('href="/en/blog/"'), 2)
        self.assertEqual(ar.count('href="/en/blog/"'), 1)

    def test_whatsapp_cta_names_the_guide(self):
        p = next(q for q in self.posts if not q.draft)
        page = self.page(p.url)
        self.assertIn('https://wa.me/971501234567?text=', page)
        self.assertRegex(page, r'id="start"')

    def test_share_cards_exist_for_every_guide(self):
        for p in self.posts:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, 'assets', 'blog', 'og', f'{p.slug}.jpg')), p.slug)


class BlogTemplateAssetTests(unittest.TestCase):
    def test_blog_template_assets_exist(self):
        refs = set()
        for dirpath, _, files in os.walk(os.path.join(ROOT, 'src', 'blog')):
            for f in files:
                if f.endswith('.html'):
                    refs |= set(re.findall(r'"/(assets/[^"\s{]+)"', read(os.path.join(dirpath, f))))
        self.assertTrue(refs)
        for ref in sorted(refs):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, *ref.split('/'))), ref)


if __name__ == '__main__':
    unittest.main()
