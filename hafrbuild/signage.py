"""The signage section: a hub and one page per sign type, in Arabic and English.

    Arabic:  /signage/            /signage/<slug>/
    English: /en/signage/         /en/signage/<slug>/

Each page is one Markdown file per language: src/signage/ar/NN-slug.md and
src/signage/en/NN-slug.md, same NN and slug in both. Front matter:

    title, slug, name, summary, meta_description, date, cta      (required)
    updated, wa_message, primary_keyword, secondary_keywords      (optional)

The body uses the guides' strict Markdown (hafrbuild/markdown.py). Links:
`/signage/<slug>/` and `/signage/` point to the page in the same language;
`/blog/<slug>/` points to an English guide; `/#start` and the other landing
anchors point to the landing page in the same language.

The section follows the guides' rulebook (src/blog/banned.json): materials and
grades may be named; warranties, durations and the AVOID words may not.
"""
import datetime
import json
import os
import re
import urllib.parse

from .blog import BlogError, parse_front_matter, human_date
from .checks import find_banned, load_banned
from .markdown import MarkdownError, Renderer, smart_quotes
from .pages import whatsapp_url
from .render import render

LANGS = ('ar', 'en')
BASE = {'ar': '/signage/', 'en': '/en/signage/'}
HOME = {'ar': '/', 'en': '/en/'}
FILE_RE = re.compile(r'^(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$')
REQUIRED = ('title', 'slug', 'name', 'summary', 'meta_description', 'date', 'cta')
OPTIONAL = ('updated', 'wa_message', 'primary_keyword', 'secondary_keywords', 'arabic_keyword')
LANDING_ANCHORS = {'stage', 'make', 'ideas', 'try', 'built', 'name', 'dark', 'kit', 'start', 'signage'}
AR_MONTHS = ('يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس',
             'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر')


class Page:
    def __init__(self, lang, number, meta, body, name):
        self.lang, self.number, self.meta, self.body, self.file = lang, number, meta, body, name
        self.slug = meta['slug']
        q = smart_quotes if lang == 'en' else (lambda s: s)
        self.title = q(meta['title'])
        self.name = q(meta['name'])
        self.summary = q(meta['summary'])
        self.description = q(meta['meta_description'])
        self.cta = q(meta['cta'])
        self.date = datetime.date.fromisoformat(meta['date'])
        self.updated = datetime.date.fromisoformat(meta['updated']) if meta.get('updated') else self.date
        self.url = BASE[lang] + self.slug + '/'

    @property
    def num(self):
        return f'{self.number:02d}'


def load(root):
    """{lang: [Page]} for both languages, sorted by number. Raises BlogError."""
    errors, pages = [], {}
    for lang in LANGS:
        d = os.path.join(root, 'src', 'signage', lang)
        pages[lang] = []
        for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not name.endswith('.md'):
                continue
            where = f'src/signage/{lang}/{name}'
            m = FILE_RE.match(name)
            if not m:
                errors.append(f'{where}: file name must be NN-slug.md')
                continue
            try:
                with open(os.path.join(d, name), encoding='utf-8') as fh:
                    meta, body = parse_front_matter(fh.read())
            except ValueError as exc:
                errors.append(f'{where}: {exc}')
                continue
            errs = [f'{where}: missing "{k}"' for k in REQUIRED if not meta.get(k)]
            errs += [f'{where}: unknown front matter key "{k}"' for k in meta if k not in REQUIRED + OPTIONAL]
            if not errs:
                if meta['slug'] != m.group(2):
                    errs.append(f'{where}: slug "{meta["slug"]}" does not match the file name')
                if len(meta['title']) > 62:
                    errs.append(f'{where}: title is {len(meta["title"])} characters; keep it to 62 (" | Hafr" is added)')
                n = len(meta['meta_description'])
                if not 70 <= n <= 160:
                    errs.append(f'{where}: meta_description is {n} characters; keep it between 70 and 160')
                for k in ('date', 'updated'):
                    if meta.get(k):
                        try:
                            datetime.date.fromisoformat(str(meta[k]))
                        except ValueError:
                            errs.append(f'{where}: {k} must be YYYY-MM-DD')
            if errs:
                errors += errs
                continue
            pages[lang].append(Page(lang, int(m.group(1)), meta, body, name))
    keys = {lang: {(p.number, p.slug) for p in pages[lang]} for lang in LANGS}
    for k in sorted(keys['ar'] ^ keys['en']):
        errors.append(f'signage page {k[0]:02d}-{k[1]} exists in only one language')
    for lang in LANGS:
        seen = set()
        for p in pages[lang]:
            if p.number in seen:
                errors.append(f'signage number {p.num} is used twice in {lang}')
            seen.add(p.number)
    if errors:
        raise BlogError(errors)
    for lang in LANGS:
        pages[lang].sort(key=lambda p: p.number)
    return pages


def _render(page, siblings, guides):
    by_slug = {p.slug: p for p in siblings}
    linked = []

    def resolve(href):
        if href.startswith('http://'):
            raise MarkdownError(f'links must use https: {href}')
        if 'wa.me' in href or 'whatsapp.com' in href:
            raise MarkdownError('WhatsApp links come from the closing call to action, not the body')
        if href.startswith('https://'):
            return href, True
        path, _, anchor = href.partition('#')
        frag = f'#{anchor}' if anchor else ''
        if path in ('/signage/', '/signage'):
            return BASE[page.lang] + frag, False
        m = re.fullmatch(r'/signage/([a-z0-9-]+)/?', path)
        if m:
            target = by_slug.get(m.group(1))
            if target is None:
                raise MarkdownError(f'link to a signage page that does not exist: {href}')
            if target.slug == page.slug:
                raise MarkdownError(f'a page must not link to itself: {href}')
            linked.append(target.slug)
            return target.url + frag, False
        m = re.fullmatch(r'/(?:en/)?blog/([a-z0-9-]+)/?', path)
        if m:
            if m.group(1) not in guides:
                raise MarkdownError(f'link to a guide that is not published: {href}')
            return f'/en/blog/{m.group(1)}/' + frag, False
        if path == '/' and (not anchor or anchor in LANDING_ANCHORS):
            return HOME[page.lang] + frag, False
        if path == '' and anchor:
            return frag, False
        raise MarkdownError(f'link not allowed on a signage page: {href}')

    def figure(src, alt, caption, n):
        raise MarkdownError('signage pages take photos through the page template, not the body')

    r = Renderer(resolve, figure, lang=page.lang)
    try:
        body = r.render(page.body)
    except MarkdownError as exc:
        raise BlogError([f'src/signage/{page.lang}/{page.file}: {exc}'])
    toc = [{'id': hid, 'text': text} for level, hid, text in r.headings if level == 2]
    faq = [{'q': q, 'a': a} for q, a, _ in r.faq]
    return {'html': body, 'toc': toc, 'faq': faq, 'words': r.words, 'linked': linked}


# ---------------------------------------------------------------- structured data
def business(site, info):
    base = site['siteUrl']
    data = {
        '@type': 'LocalBusiness', '@id': f'{base}/#business', 'name': 'Hafr', 'alternateName': 'حفر',
        'url': f'{base}/', 'logo': f'{base}/assets/img/hafr-logo.png', 'image': f'{base}/assets/img/og-image.png',
        'address': {'@type': 'PostalAddress', **info['address']},
        'areaServed': [{'@type': 'City', 'name': c} for c in info['cities']]
                      + [{'@type': 'Country', 'name': 'United Arab Emirates'}],
        'knowsLanguage': ['ar', 'en'],
        'parentOrganization': {'@type': 'Organization', 'name': 'Al Taher Group',
                               'alternateName': 'مجموعة الطاهر', 'url': 'https://altaherdesign.ae'},
    }
    if site.get('whatsapp'):
        data['telephone'] = '+' + site['whatsapp']
    if site.get('instagram'):
        data['sameAs'] = [f"https://www.instagram.com/{site['instagram']}"]
    return data


def _dump(data):
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def jsonld_page(site, info, s, page, rendered):
    base = site['siteUrl']
    url = base + page.url
    graph = [
        {'@type': 'WebPage', '@id': url, 'url': url, 'name': page.title, 'description': page.description,
         'inLanguage': page.lang, 'dateModified': page.updated.isoformat(),
         'isPartOf': {'@id': f'{base}/#website'}, 'about': {'@id': url + '#service'},
         'breadcrumb': {'@id': url + '#crumbs'}},
        {'@type': 'Service', '@id': url + '#service', 'name': page.name, 'serviceType': page.name,
         'description': page.description, 'url': url, 'provider': {'@id': f'{base}/#business'},
         'areaServed': [{'@type': 'City', 'name': c} for c in info['cities']]
                       + [{'@type': 'Country', 'name': 'United Arab Emirates'}],
         'category': s['hub']['h1']},
        {'@type': 'BreadcrumbList', '@id': url + '#crumbs', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Hafr', 'item': base + HOME[page.lang]},
            {'@type': 'ListItem', 'position': 2, 'name': s['page']['signage'], 'item': base + BASE[page.lang]},
            {'@type': 'ListItem', 'position': 3, 'name': page.name, 'item': url}]},
        business(site, info),
    ]
    kw = [k for k in [page.meta.get('primary_keyword')] + list(page.meta.get('secondary_keywords') or []) if k]
    if kw:
        graph[1]['keywords'] = ', '.join(kw)
    if rendered['faq']:
        graph.append({'@type': 'FAQPage', '@id': url + '#faq', 'inLanguage': page.lang, 'mainEntity': [
            {'@type': 'Question', 'name': f['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}}
            for f in rendered['faq']]})
    return _dump({'@context': 'https://schema.org', '@graph': graph})


def jsonld_hub(site, info, s, lang, pages):
    base = site['siteUrl']
    url = base + BASE[lang]
    return _dump({'@context': 'https://schema.org', '@graph': [
        {'@type': 'CollectionPage', '@id': url, 'url': url, 'name': s['hub']['h1'],
         'description': s['hub']['description'], 'inLanguage': lang,
         'mainEntity': {'@type': 'ItemList', 'itemListElement': [
             {'@type': 'ListItem', 'position': i + 1, 'name': p.name, 'url': base + p.url}
             for i, p in enumerate(pages)]}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Hafr', 'item': base + HOME[lang]},
            {'@type': 'ListItem', 'position': 2, 'name': s['page']['signage'], 'item': url}]},
        business(site, info)]})


# ---------------------------------------------------------------- fonts
def font_links(lang, text=''):
    css = 'https://fonts.googleapis.com/css2?'
    if lang == 'ar':
        return [css + 'family=Amiri:wght@400;700&family=Cairo:wght@300;400;500;600&family=Outfit:wght@400;500&display=swap']
    links = [css + 'family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,300'
                   '&family=Outfit:wght@300;400;500;600&display=swap']
    ar = ''.join(sorted({ch for ch in text if '؀' <= ch <= 'ۿ' or ch in '«»'}))
    if ar:
        links.append(css + 'family=Cairo:wght@400;500&text=' + urllib.parse.quote(ar, safe='') + '&display=swap')
    return links


def human(d, lang):
    return human_date(d) if lang == 'en' else f'{d.day} {AR_MONTHS[d.month - 1]} {d.year}'


# ---------------------------------------------------------------- build
def build(root, site, contents, production, partials, guides):
    """Returns (files {relpath: html}, sitemap pairs [(ar_url, en_url, lastmod)], problems, page index)."""
    sdir = os.path.join(root, 'src', 'signage')
    with open(os.path.join(sdir, 'signage.json'), encoding='utf-8') as fh:
        strings = json.load(fh)
    info = strings['business']
    pages = load(root)
    parts = dict(partials)
    for f in sorted(os.listdir(os.path.join(sdir, 'partials'))):
        with open(os.path.join(sdir, 'partials', f), encoding='utf-8') as fh:
            parts['sg_' + os.path.splitext(f)[0]] = fh.read()
    with open(os.path.join(sdir, 'page.html'), encoding='utf-8') as fh:
        t_page = fh.read()
    with open(os.path.join(sdir, 'hub.html'), encoding='utf-8') as fh:
        t_hub = fh.read()
    banned = load_banned(os.path.join(root, 'src', 'blog', 'banned.json'))
    base = site['siteUrl']
    files, problems, pairs = {}, [], []
    other = {'ar': 'en', 'en': 'ar'}

    def common(lang, c, path_ar, path_en):
        s = strings[lang]
        o = other[lang]
        return {
            'lang': lang, 'dir': 'rtl' if lang == 'ar' else 'ltr', 'c': c, 's': s, 'dev': not production,
            'home': HOME[lang], 'hub': BASE[lang], 'og_locale': 'ar_AE' if lang == 'ar' else 'en_AE',
            'alternates': [{'hreflang': 'ar', 'href': base + path_ar}, {'hreflang': 'en', 'href': base + path_en},
                           {'hreflang': 'x-default', 'href': base + path_ar}],
            'switch': {'href': path_en if lang == 'ar' else path_ar, 'label': strings[o]['lang_name'],
                       'lang': o, 'dir': 'rtl' if o == 'ar' else 'ltr'},
            'whatsapp': site.get('whatsapp'),
            'wa_url': whatsapp_url(site.get('whatsapp'), s['hub']['wa_message']),
            'instagram_url': f"https://www.instagram.com/{site['instagram']}" if site.get('instagram') else None,
            'has_instagram': bool(site.get('instagram')),
            'guides_href': '/en/blog/', 'show_guides': lang == 'en',
        }

    by_lang = {lang: {p.slug: p for p in pages[lang]} for lang in LANGS}
    for lang in LANGS:
        s = strings[lang]
        c = contents[lang]
        listed = [{'num': p.num, 'url': p.url, 'name': p.name, 'summary': p.summary} for p in pages[lang]]
        for p in pages[lang]:
            r = _render(p, pages[lang], guides)
            twin = by_lang[other[lang]][p.slug]
            ar_url = p.url if lang == 'ar' else twin.url
            en_url = p.url if lang == 'en' else twin.url
            ctx = common(lang, c, ar_url, en_url)
            others = [x for x in listed if x['url'] != p.url]
            linked_first = sorted(others, key=lambda x: (x['url'].rstrip('/').rsplit('/', 1)[-1] not in r['linked'],
                                                         abs(int(x['num']) - p.number)))
            ctx.update({
                'nav_current': 'true',
                'fonts': font_links(lang, s['lang_name'] + c['footer']['brand'] + r['html']),
                'page': {'title': f"{p.title} | {'حفر' if lang == 'ar' else 'Hafr'}", 'description': p.description, 'canonical': base + p.url,
                         'og_title': p.title, 'og_image': f'{base}/assets/img/og-image.png',
                         'og_image_alt': p.name, 'jsonld': jsonld_page(site, info, s, p, r)},
                'sg': {'num': p.num, 'name': p.name, 'title': p.title, 'dek': p.description,
                       'updated_iso': p.updated.isoformat(), 'updated_human': human(p.updated, lang),
                       'body': r['html'], 'toc': r['toc'], 'has_toc': len(r['toc']) >= 3,
                       'related': linked_first[:3], 'has_related': len(others) > 0},
                'cta': {'text': p.cta,
                        'wa_url': whatsapp_url(site.get('whatsapp'),
                                               p.meta.get('wa_message') or s['page']['wa_message'].replace('{name}', p.name))},
            })
            html_page = render(t_page, ctx, partials=parts, dev=not production)
            files[p.url.lstrip('/') + 'index.html'] = html_page
            problems += [f'signage {lang}/{p.slug}: banned term {hit}' for hit in find_banned(html_page, banned)]
            if lang == 'ar':
                pairs.append((base + ar_url, base + en_url, max(p.updated, twin.updated).isoformat()))

        ctx = common(lang, c, BASE['ar'], BASE['en'])
        ctx.update({
            'nav_current': 'page',
            'fonts': font_links(lang, s['lang_name'] + c['footer']['brand']),
            'page': {'title': s['hub']['title'], 'description': s['hub']['description'],
                     'canonical': base + BASE[lang], 'og_title': s['hub']['h1'],
                     'og_image': f'{base}/assets/img/og-image.png', 'og_image_alt': s['hub']['h1'],
                     'jsonld': jsonld_hub(site, info, s, lang, pages[lang])},
            'pages': listed,
            'cta': {'text': s['hub']['cta'], 'wa_url': whatsapp_url(site.get('whatsapp'), s['hub']['wa_message'])},
        })
        html_hub = render(t_hub, ctx, partials=parts, dev=not production)
        files[BASE[lang].lstrip('/') + 'index.html'] = html_hub
        problems += [f'signage hub {lang}: banned term {hit}' for hit in find_banned(html_hub, banned)]

    newest = max((p.updated for p in pages['ar'] + pages['en']), default=None)
    pairs.insert(0, (base + BASE['ar'], base + BASE['en'], newest.isoformat() if newest else None))
    if production:
        for path, text in files.items():
            if '[[' in text:
                problems.append(f'{path}: unresolved [[placeholder]]')
    return files, pairs, problems, items(pages)


def items(pages):
    """{lang: [{url, name, summary}]} for linking to the section from other pages."""
    return {lang: [{'url': p.url, 'name': p.name, 'summary': p.summary} for p in pages[lang]] for lang in LANGS}
