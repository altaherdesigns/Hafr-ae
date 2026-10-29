"""Per-page values, claim gating, structured data and search files."""
import copy
import json
import urllib.parse

THREE_VERSION = '0.186.1'
DEFAULT_CDN = 'https://cdn.jsdelivr.net/npm/'
FOUNDED = '2026'

LANGS = {
    'ar': {'dir': 'rtl', 'path': '/', 'base': '', 'og_locale': 'ar_AE',
           'switch': {'href': '/en/', 'label': 'English', 'lang': 'en', 'dir': 'ltr'}},
    'en': {'dir': 'ltr', 'path': '/en/', 'base': '../', 'og_locale': 'en_AE',
           'switch': {'href': '/', 'label': 'عربي', 'lang': 'ar', 'dir': 'rtl'}},
}

# Strings rendered in the Arabic display face (Amiri); the font is subset to their characters.
DISPLAY_KEYS = ['stage.headline', 'stage.captions', 'make.title', 'ideas.title', 'ideas.items', 'try.title', 'built.title', 'name.title',
                'dark.title', 'kit.title', 'start.title', 'name.proof.name', 'dark.scene_label']

FONT_CSS = 'https://fonts.googleapis.com/css2?'


def gate(content, production):
    """Unverified claims (spec §3) ship only once marked verified."""
    c = copy.deepcopy(content)
    omitted = []

    rows = []
    for i, row in enumerate(c['built']['rows']):
        pending = row.get('status') != 'verified'
        if pending and production:
            omitted.append(f'built.rows[{i}]')
            continue
        row['pending'] = pending
        rows.append(row)
    c['built']['rows'] = rows
    c['built']['has_rows'] = bool(rows)
    c['built']['show_fallback'] = not rows

    kit_pending = c['kit'].get('status') != 'verified'
    if kit_pending and production:
        omitted.append('kit.items')
        c['kit']['items'] = []
    c['kit']['pending'] = kit_pending and not production
    c['kit']['has_items'] = bool(c['kit']['items'])
    c['kit']['show_fallback'] = not c['kit']['items']

    dark_pending = c['dark'].get('status') != 'verified'
    if dark_pending and production:
        omitted.append('dark.lighting')
        c['dark']['lighting'] = ''
    c['dark']['pending'] = dark_pending and not production
    c['dark']['show_lighting'] = bool(c['dark']['lighting'])
    c['dark']['show_fallback'] = not c['dark']['lighting']
    return c, omitted


def jsonld(site):
    data = {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        '@id': f"{site['siteUrl']}/#org",
        'name': 'Hafr',
        'alternateName': 'حفر',
        'url': f"{site['siteUrl']}/",
        'foundingDate': FOUNDED,
        'logo': f"{site['siteUrl']}/assets/img/hafr-logo.png",
        'areaServed': {'@type': 'Country', 'name': 'United Arab Emirates'},
        'parentOrganization': {'@type': 'Organization', 'name': 'Al Taher Group',
                               'alternateName': 'مجموعة الطاهر', 'url': 'https://altaherdesign.ae'},
    }
    if site.get('instagram'):
        data['sameAs'] = [f"https://www.instagram.com/{site['instagram']}"]
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


IDEA_WIDTHS = (640, 1024, 1408)


def ideas(content, images, site, base, lang):
    """Join each Ideas caption (content file) with its image (src/ideas.json), by position."""
    items = content['ideas']['items']
    if len(items) != len(images):
        raise ValueError(f'ideas: {len(items)} captions but {len(images)} images in src/ideas.json')
    out = []
    for i, (item, img) in enumerate(zip(items, images)):
        stem = f"assets/img/ideas/{img['slug']}"
        msg = content['ideas']['wa_message'].replace('{style}', item['name']).replace('{n}', str(i + 1))
        out.append({
            'name': item['name'], 'alt': item['alt'], 'w': img['w'], 'h': img['h'],
            'src': f'{base}{stem}-1024.jpg',
            'srcset': ', '.join(f'{base}{stem}-{w}.webp {w}w' for w in IDEA_WIDTHS),
            'large': f'{base}{stem}-1408.webp',
            'abs': f"{site['siteUrl']}/{stem}-1408.webp",
            'thumb': f"{site['siteUrl']}/{stem}-640.webp",
            'wa_url': whatsapp_url(site.get('whatsapp'), msg),
        })
    return out


def gallery_jsonld(site, content, items, page_url, lang):
    """ImageGallery for the Ideas section: names, captions and credit for image search."""
    org = {'@id': f"{site['siteUrl']}/#org"}
    data = {
        '@context': 'https://schema.org',
        '@type': 'ImageGallery',
        '@id': f'{page_url}#ideas',
        'url': f'{page_url}#ideas',
        'name': content['ideas']['title'],
        'description': content['ideas']['intro'],
        'inLanguage': lang,
        'publisher': org,
        'associatedMedia': [{
            '@type': 'ImageObject',
            'contentUrl': it['abs'],
            'thumbnailUrl': it['thumb'],
            'width': it['w'], 'height': it['h'],
            'encodingFormat': 'image/webp',
            'name': it['name'],
            'caption': it['alt'],
            'creator': org,
            'creditText': 'Hafr',
            'copyrightNotice': f'© {FOUNDED} Hafr',
        } for it in items],
    }
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def whatsapp_url(number, message):
    if not number:
        return '#start'
    return f'https://wa.me/{number}?text={urllib.parse.quote(message, safe="")}'


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)


def _get(content, dotted):
    value = content
    for part in dotted.split('.'):
        value = value[part]
    return value


def amiri_text(contents):
    chars = set()
    for content in contents:
        for key in DISPLAY_KEYS:
            for s in _strings(_get(content, key)):
                chars.update(ch for ch in s if not ch.isspace())
    return ''.join(sorted(chars))


def arabic_chars(content):
    """Arabic-script characters used anywhere in a content file (for the English page's Cairo subset)."""
    chars = set()
    for s in _strings(content):
        chars.update(ch for ch in s if '؀' <= ch <= 'ۿ' or ch in '«»')
    return ''.join(sorted(chars))


def font_links(lang, amiri, cairo_text=''):
    q = urllib.parse.quote
    if lang == 'ar':
        return [FONT_CSS + 'family=Cairo:wght@300;400;500&family=Outfit:wght@400;500&display=swap',
                FONT_CSS + 'family=Amiri&text=' + q(amiri, safe='') + '&display=swap']
    links = [FONT_CSS + 'family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,300'
             '&family=Outfit:wght@300;400;500&display=swap']
    if amiri:
        links.append(FONT_CSS + 'family=Amiri&text=' + q(amiri, safe='') + '&display=swap')
    if cairo_text:
        links.append(FONT_CSS + 'family=Cairo:wght@400;500&text=' + q(cairo_text, safe='') + '&display=swap')
    return links


def importmap(cdn=DEFAULT_CDN, version=THREE_VERSION):
    base = f'{cdn}three@{version}/'
    return json.dumps({'imports': {
        'three': base + 'build/three.module.min.js',
        base + 'build/three.core.js': base + 'build/three.core.min.js',
        'three/addons/': base + 'examples/jsm/',
    }})


def page_context(lang, site, content, *, production, head_js, importmap, fonts, images=()):
    info = LANGS[lang]
    gated, _ = gate(content, production)
    url = site['siteUrl']
    other = 'en' if lang == 'ar' else 'ar'
    idea_items = ideas(gated, list(images), site, info['base'], lang)
    return {
        'lang': lang,
        'dir': info['dir'],
        'base': info['base'],
        'site_url': url,
        'canonical': url + info['path'],
        'alternates': [{'hreflang': 'ar', 'href': url + '/'},
                       {'hreflang': 'en', 'href': url + '/en/'},
                       {'hreflang': 'x-default', 'href': url + '/'}],
        'og_locale': info['og_locale'],
        'og_locale_alt': LANGS[other]['og_locale'],
        'og_image': url + '/assets/img/og-image.png',
        'switch': info['switch'],
        # The guides are in English: linked from the English menu, and from both footers.
        'guides': {'href': '/en/blog/', 'label': 'Guides', 'in_header': lang == 'en'},
        'fonts': fonts,
        'jsonld': jsonld(site),
        'ideas': idea_items,
        'gallery_jsonld': gallery_jsonld(site, gated, idea_items, url + info['path'], lang),
        'head_js': head_js,
        'importmap': importmap,
        'wa_url': whatsapp_url(site.get('whatsapp'), gated['start']['wa_message']),
        'wa_base': f"https://wa.me/{site['whatsapp']}?text=" if site.get('whatsapp') else 'https://wa.me/?text=',
        'whatsapp': site.get('whatsapp'),
        'instagram_url': f"https://www.instagram.com/{site['instagram']}" if site.get('instagram') else None,
        'has_instagram': bool(site.get('instagram')),
        'year': FOUNDED,
        'dev': not production,
        'c': gated,
    }


def sitemap(site, extra=(), images=()):
    """The two landing pages (with their language alternates and the Ideas images),
    then any extra (url, lastmod) entries such as the guides, which exist in English only."""
    url = site['siteUrl']
    pages = [(url + '/', 'ar'), (url + '/en/', 'en')]
    links = ''.join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{u}"/>' for u, l in pages)
    pics = ''.join(f"<image:image><image:loc>{url}/assets/img/ideas/{img['slug']}-1408.webp</image:loc></image:image>"
                   for img in images)
    body = ''.join(f'<url><loc>{u}</loc>{links}{pics}</url>' for u, _ in pages)
    body += ''.join(f'<url><loc>{u}</loc>' + (f'<lastmod>{m}</lastmod>' if m else '') + '</url>'
                    for u, m in extra)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">' + body + '</urlset>\n')


def robots(site, production):
    if not production:
        return 'User-agent: *\nDisallow: /\n'
    return f"User-agent: *\nAllow: /\n\nSitemap: {site['siteUrl']}/sitemap.xml\n"
