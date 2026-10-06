"""The guides (blog): posts, links, figures, structured data, feed and sitemap entries.

Posts live in src/blog/en/NN-slug.md (NN = the guide's number). Each starts with
front matter between --- lines, then a body in the strict Markdown subset of
hafrbuild/markdown.py. A post with `draft: true` is never published: production
builds leave it out entirely and turn links to it into plain text until it ships.
"""
import datetime
import html
import json
import math
import os
import re
import urllib.parse

from .markdown import MarkdownError, Renderer, plain, smart_quotes

BLOG_PATH = '/en/blog/'
FILE_RE = re.compile(r'^(\d{2,3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$')
SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
TOKEN_RE = re.compile(r'\{\{\s*([A-Z][A-Z0-9_]*)\s*\}\}')
REQUIRED = ('title', 'slug', 'meta_description', 'date', 'cta')
OPTIONAL = ('updated', 'draft', 'primary_keyword', 'secondary_keywords', 'arabic_keyword', 'wa_message')
LANDING_ANCHORS = {'stage', 'make', 'built', 'name', 'dark', 'kit', 'start'}
IMG_TYPES = ('.png', '.jpg', '.jpeg', '.webp')
WORDS_PER_MINUTE = 230
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December')


class BlogError(Exception):
    def __init__(self, errors):
        super().__init__('\n'.join(errors))
        self.errors = errors


# ---------------------------------------------------------------- front matter
def _value(raw):
    raw = raw.strip()
    if raw in ('true', 'false'):
        return raw == 'true'
    if raw.startswith('[') and raw.endswith(']'):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        items = re.findall(r'"((?:[^"\\]|\\.)*)"|([^,]+)', inner)
        return [(q.replace('\\"', '"') if q else b.strip()) for q, b in items if (q or b.strip())]
    if raw.startswith('"'):
        if not raw.endswith('"') or len(raw) < 2:
            raise ValueError(f'unclosed quote: {raw[:40]}')
        return raw[1:-1].replace('\\"', '"')
    return raw


def parse_front_matter(text):
    text = text.lstrip('﻿').replace('\r\n', '\n')
    if not text.startswith('---\n'):
        raise ValueError('a post must start with front matter between --- lines')
    end = text.find('\n---\n', 4)
    if end < 0:
        raise ValueError('front matter is not closed with ---')
    meta = {}
    for n, line in enumerate(text[4:end].split('\n'), 2):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, val = line.partition(':')
        if not sep or not re.match(r'^[a-z_]+$', key.strip()):
            raise ValueError(f'front matter line {n} is not "key: value": {line[:50]!r}')
        meta[key.strip()] = _value(val)
    return meta, text[end + 5:]


# ---------------------------------------------------------------- posts
class Post:
    def __init__(self, number, meta, body, path):
        self.number = number
        self.meta = meta
        self.body = body
        self.path = path
        self.slug = meta['slug']
        self.draft = bool(meta.get('draft', False))
        self.date = datetime.date.fromisoformat(meta['date'])
        self.updated = datetime.date.fromisoformat(meta['updated']) if meta.get('updated') else self.date
        self.title = smart_quotes(meta['title'])
        self.description = smart_quotes(meta['meta_description'])
        self.cta = smart_quotes(meta['cta'])
        self.url = f'{BLOG_PATH}{self.slug}/'

    @property
    def num(self):
        return f'{self.number:02d}'


def _subst(text, tokens, where, errors):
    def rep(m):
        key = m.group(1)
        if key not in tokens:
            errors.append(f'{where}: unknown token {{{{{key}}}}}')
            return m.group(0)
        if tokens[key] in (None, ''):
            errors.append(f'{where}: token {{{{{key}}}}} has no value in src/blog/facts.json')
            return m.group(0)
        return str(tokens[key])
    out = TOKEN_RE.sub(rep, text)
    if not errors and ('{{' in out or '}}' in out):
        errors.append(f'{where}: stray braces left after filling tokens')
    return out


def load_posts(directory, tokens):
    """Read every post. Raises BlogError listing every problem found."""
    errors, posts = [], []
    if not os.path.isdir(directory):
        return []
    for name in sorted(os.listdir(directory)):
        if not name.endswith('.md'):
            continue
        where = f'src/blog/en/{name}'
        m = FILE_RE.match(name)
        if not m:
            errors.append(f'{where}: file name must be NN-slug.md (two or three digits, then the slug)')
            continue
        try:
            with open(os.path.join(directory, name), encoding='utf-8') as fh:
                meta, body = parse_front_matter(fh.read())
        except ValueError as exc:
            errors.append(f'{where}: {exc}')
            continue
        errs = []
        for key in REQUIRED:
            if not meta.get(key):
                errs.append(f'{where}: missing "{key}"')
        for key in meta:
            if key not in REQUIRED and key not in OPTIONAL:
                errs.append(f'{where}: unknown front matter key "{key}"')
        if errs:
            errors += errs
            continue
        for key in ('title', 'meta_description', 'cta', 'wa_message'):
            if isinstance(meta.get(key), str):
                meta[key] = _subst(meta[key], tokens, f'{where} ({key})', errs)
        body = _subst(body, tokens, where, errs)
        if meta['slug'] != m.group(2):
            errs.append(f'{where}: slug "{meta["slug"]}" does not match the file name')
        if not SLUG_RE.match(str(meta['slug'])):
            errs.append(f'{where}: slug must be lowercase words joined by hyphens')
        for key in ('date', 'updated'):
            if meta.get(key):
                try:
                    datetime.date.fromisoformat(str(meta[key]))
                except ValueError:
                    errs.append(f'{where}: {key} must be YYYY-MM-DD')
        if 'draft' in meta and not isinstance(meta['draft'], bool):
            errs.append(f'{where}: draft must be true or false')
        if len(meta['title']) > 70:
            errs.append(f'{where}: title is {len(meta["title"])} characters; keep it to 70')
        d = len(meta['meta_description'])
        if not 70 <= d <= 160:
            errs.append(f'{where}: meta_description is {d} characters; keep it between 70 and 160')
        if errs:
            errors += errs
            continue
        posts.append(Post(int(m.group(1)), meta, body, os.path.join(directory, name)))
    seen_n, seen_s = {}, {}
    for p in posts:
        if p.number in seen_n:
            errors.append(f'guide number {p.num} is used twice ({seen_n[p.number]} and {p.slug})')
        if p.slug in seen_s:
            errors.append(f'slug {p.slug} is used twice')
        seen_n[p.number], seen_s[p.slug] = p.slug, True
    if errors:
        raise BlogError(errors)
    return sorted(posts, key=lambda p: p.number)


def published(posts, production):
    return [p for p in posts if not (production and p.draft)]


# ---------------------------------------------------------------- figures
def image_size(path):
    """(width, height) of a PNG, JPEG or WebP file, read from its header."""
    with open(path, 'rb') as fh:
        head = fh.read(64)
        if head[:8] == b'\x89PNG\r\n\x1a\n':
            return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
        if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            chunk = head[12:16]
            if chunk == b'VP8X':
                return 1 + int.from_bytes(head[24:27], 'little'), 1 + int.from_bytes(head[27:30], 'little')
            if chunk == b'VP8 ':
                return (int.from_bytes(head[26:28], 'little') & 0x3FFF,
                        int.from_bytes(head[28:30], 'little') & 0x3FFF)
            if chunk == b'VP8L':
                b = int.from_bytes(head[21:25], 'little')
                return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        if head[:2] == b'\xff\xd8':
            fh.seek(2)
            while True:
                marker = fh.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    break
                length = int.from_bytes(fh.read(2), 'big')
                if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    data = fh.read(5)
                    return int.from_bytes(data[3:5], 'big'), int.from_bytes(data[1:3], 'big')
                fh.seek(length - 2, 1)
    raise ValueError(f'cannot read the size of {os.path.basename(path)}')


_SVG_FORBIDDEN = re.compile(r'<script|<foreignObject|\son[a-z]+\s*=|href\s*=\s*"(?:https?:|javascript:)|<image\b', re.I)


def inline_svg(path, alt):
    with open(path, encoding='utf-8') as fh:
        svg = fh.read()
    svg = re.sub(r'<\?xml[^>]*\?>|<!DOCTYPE[^>]*>|<!--.*?-->|<metadata>.*?</metadata>', '', svg, flags=re.S).strip()
    if _SVG_FORBIDDEN.search(svg):
        raise ValueError(f'{os.path.basename(path)} contains scripts, external links or embedded images')
    m = re.match(r'<svg\b([^>]*)>', svg)
    if not m or 'viewBox' not in m.group(1):
        raise ValueError(f'{os.path.basename(path)} must start with <svg ... viewBox="...">')
    attrs = re.sub(r'\s(?:width|height|role|aria-label|aria-hidden|focusable|class)="[^"]*"', '', m.group(1))
    label = html.escape(alt, quote=True)
    return (f'<svg{attrs} class="fig__svg" role="img" aria-label="{label}" focusable="false">'
            + svg[m.end():])


# ---------------------------------------------------------------- body rendering
class Rendered:
    def __init__(self, html_body, toc, faq, words, unwrapped, linked):
        self.html, self.toc, self.faq, self.words = html_body, toc, faq, words
        self.unwrapped, self.linked = unwrapped, linked

    @property
    def minutes(self):
        return max(1, math.ceil(self.words / WORDS_PER_MINUTE))


def render_body(post, all_posts, *, production, figures_dir, root):
    by_slug = {p.slug: p for p in all_posts}
    unwrapped, linked = [], []

    def resolve(href):
        if href.startswith('http://'):
            raise MarkdownError(f'links must use https: {href}')
        if href.startswith('https://wa.me') or href.startswith('https://api.whatsapp.com'):
            raise MarkdownError('WhatsApp links come from the closing call to action, not the body')
        if href.startswith('https://'):
            return href, True
        path, _, anchor = href.partition('#')
        m = re.fullmatch(r'/(?:en/)?blog/([a-z0-9-]+)/?', path)
        if m:
            target = by_slug.get(m.group(1))
            if target is None:
                raise MarkdownError(f'link to a guide that does not exist: {href}')
            if target.slug == post.slug:
                raise MarkdownError(f'a guide must not link to itself: {href}')
            if target.draft and production:
                unwrapped.append(target.slug)
                return None, False
            linked.append(target.slug)
            return target.url + (f'#{anchor}' if anchor else ''), False
        if path in ('/', '/en/', '/en') and (not anchor or anchor in LANDING_ANCHORS):
            return ('/en/' if path != '/' else '/') + (f'#{anchor}' if anchor else ''), False
        if path == '' and anchor:
            return f'#{anchor}', False
        raise MarkdownError(f'link not allowed in a guide: {href}')

    def figure(src, alt, caption, n):
        if not alt or len(alt) < 12:
            raise MarkdownError(f'figure {src} needs real alt text (at least a short sentence)')
        if src.startswith('figures/') and src.endswith('.svg'):
            path = os.path.join(figures_dir, src[len('figures/'):])
            if not os.path.isfile(path):
                raise MarkdownError(f'missing figure file src/blog/{src}')
            try:
                media = inline_svg(path, alt)
            except ValueError as exc:
                raise MarkdownError(str(exc))
            kind = 'svg'
        elif src.startswith('/assets/blog/img/') and src.lower().endswith(IMG_TYPES):
            path = os.path.join(root, *src.strip('/').split('/'))
            if not os.path.isfile(path):
                raise MarkdownError(f'missing image {src}')
            w, h = image_size(path)
            media = (f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" '
                     f'width="{w}" height="{h}" loading="lazy" decoding="async">')
            kind = 'img'
        else:
            raise MarkdownError(f'figures must be figures/NAME.svg or /assets/blog/img/NAME.(webp|jpg|png): {src}')
        cap = (f'<figcaption><span class="fig__n">Fig. {n}</span> {html.escape(caption, quote=False)}</figcaption>'
               if caption else '')
        return f'<figure class="fig fig--{kind}">{media}{cap}</figure>'

    r = Renderer(resolve, figure)
    try:
        body = r.render(post.body)
    except MarkdownError as exc:
        raise BlogError([f'src/blog/en/{os.path.basename(post.path)}: {exc}'])
    toc = [{'id': hid, 'text': text} for level, hid, text in r.headings if level == 2]
    faq = [{'q': q, 'a': a} for q, a, _ in r.faq]
    return Rendered(body, toc, faq, r.words, sorted(set(unwrapped)), linked)


# ---------------------------------------------------------------- page data
def human_date(d):
    return f'{d.day} {MONTHS[d.month - 1]} {d.year}'


def wa_message(post):
    return post.meta.get('wa_message') or (
        f'Hello Hafr, I’ve just read your guide “{post.title}”. '
        f'I’d like to ask about a sign for my home.')


def related(post, rendered, pool, limit=3):
    """Guides linked from the body first, then the nearest numbers."""
    by_slug = {p.slug: p for p in pool}
    picks = []
    for slug in rendered.linked:
        if slug in by_slug and slug != post.slug and by_slug[slug] not in picks:
            picks.append(by_slug[slug])
    for p in sorted(pool, key=lambda p: (abs(p.number - post.number), p.number)):
        if p.slug != post.slug and p not in picks:
            picks.append(p)
    return picks[:limit]


def org(site):
    data = {
        '@type': 'Organization', '@id': f"{site['siteUrl']}/#org", 'name': 'Hafr', 'alternateName': 'حفر',
        'url': f"{site['siteUrl']}/", 'logo': f"{site['siteUrl']}/assets/img/hafr-logo.png",
        'parentOrganization': {'@type': 'Organization', 'name': 'Al Taher Group',
                               'alternateName': 'مجموعة الطاهر', 'url': 'https://altaherdesign.ae'},
    }
    if site.get('instagram'):
        data['sameAs'] = [f"https://www.instagram.com/{site['instagram']}"]
    return data


def _dump(data):
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def jsonld_post(site, post, rendered, image):
    base = site['siteUrl']
    url = base + post.url
    graph = [
        {'@type': 'BlogPosting', '@id': url + '#article', 'headline': post.title,
         'description': post.description, 'url': url, 'mainEntityOfPage': url, 'inLanguage': 'en',
         'datePublished': post.date.isoformat(), 'dateModified': post.updated.isoformat(),
         'image': image, 'wordCount': rendered.words,
         'author': {'@id': f'{base}/#org'}, 'publisher': {'@id': f'{base}/#org'},
         'isPartOf': {'@id': f'{base}{BLOG_PATH}#blog'}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Hafr', 'item': f'{base}/en/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Guides', 'item': f'{base}{BLOG_PATH}'},
            {'@type': 'ListItem', 'position': 3, 'name': post.title, 'item': url}]},
        org(site),
    ]
    kw = [k for k in [post.meta.get('primary_keyword')] + list(post.meta.get('secondary_keywords') or []) if k]
    if kw:
        graph[0]['keywords'] = ', '.join(kw)
    if rendered.faq:
        graph.insert(1, {'@type': 'FAQPage', '@id': url + '#faq', 'mainEntity': [
            {'@type': 'Question', 'name': f['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}}
            for f in rendered.faq]})
    return _dump({'@context': 'https://schema.org', '@graph': graph})


def jsonld_index(site, posts, title, description):
    base = site['siteUrl']
    return _dump({'@context': 'https://schema.org', '@graph': [
        {'@type': 'Blog', '@id': f'{base}{BLOG_PATH}#blog', 'name': title, 'description': description,
         'url': f'{base}{BLOG_PATH}', 'inLanguage': 'en', 'publisher': {'@id': f'{base}/#org'},
         'blogPost': [{'@type': 'BlogPosting', 'headline': p.title, 'url': base + p.url,
                       'datePublished': p.date.isoformat()} for p in posts]},
        org(site)]})


def feed(site, posts, title):
    base = site['siteUrl']
    esc = lambda s: html.escape(s, quote=True)
    newest = max((p.updated for p in posts), default=datetime.date(2026, 1, 1))
    entries = ''.join(
        f'<entry><title>{esc(p.title)}</title><link href="{base}{p.url}"/><id>{base}{p.url}</id>'
        f'<published>{p.date.isoformat()}T08:00:00+04:00</published>'
        f'<updated>{p.updated.isoformat()}T08:00:00+04:00</updated>'
        f'<summary>{esc(p.description)}</summary></entry>'
        for p in sorted(posts, key=lambda p: p.number, reverse=True))
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            f'<title>{esc(title)}</title><link href="{base}{BLOG_PATH}"/>'
            f'<link rel="self" href="{base}{BLOG_PATH}feed.xml"/><id>{base}{BLOG_PATH}</id>'
            f'<updated>{newest.isoformat()}T08:00:00+04:00</updated>'
            f'<author><name>Hafr</name></author>{entries}</feed>\n')


def font_links(arabic_text):
    q = urllib.parse.quote
    css = 'https://fonts.googleapis.com/css2?'
    links = [css + 'family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,300'
                   '&family=Outfit:wght@300;400;500;600&display=swap']
    if arabic_text:
        links.append(css + 'family=Cairo:wght@400;500&text=' + q(arabic_text, safe='') + '&display=swap')
    return links


def arabic_chars(*texts):
    chars = set()
    for t in texts:
        chars.update(ch for ch in t if '؀' <= ch <= 'ۿ' or ch in '«»')
    return ''.join(sorted(chars))
