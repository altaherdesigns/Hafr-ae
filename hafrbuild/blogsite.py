"""Assembles the guide pages (index, posts, feed) for build.py."""
import json
import os

from . import blog
from .checks import find_banned, load_banned
from .pages import whatsapp_url
from .render import render


def _read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def _common(site, c, strings, production):
    return {
        'lang': 'en', 'dir': 'ltr', 'site_url': site['siteUrl'], 'c': c, 's': strings, 'dev': not production,
        'switch': {'href': '/', 'label': 'عربي', 'lang': 'ar', 'dir': 'rtl'},
        'wa_url': whatsapp_url(site.get('whatsapp'), c['start']['wa_message']),
        'whatsapp': site.get('whatsapp'),
        'instagram_url': f"https://www.instagram.com/{site['instagram']}" if site.get('instagram') else None,
        'has_instagram': bool(site.get('instagram')),
    }


def _og(root, site, slug):
    """The guide's own share card if it exists (assets/blog/og/<slug>.jpg), else the site's."""
    for ext in ('jpg', 'png'):
        if os.path.isfile(os.path.join(root, 'assets', 'blog', 'og', f'{slug}.{ext}')):
            return f"{site['siteUrl']}/assets/blog/og/{slug}.{ext}"
    return f"{site['siteUrl']}/assets/img/og-image.png"


def build(root, site, c_en, production, partials):
    """Returns (files: {relative_path: text}, sitemap_entries, problems, notes).

    `problems` are rule breaches (fatal in production); a malformed post raises
    blog.BlogError, which is fatal in every build."""
    bdir = os.path.join(root, 'src', 'blog')
    strings = json.loads(_read(os.path.join(bdir, 'blog.json')))
    tokens = json.loads(_read(os.path.join(bdir, 'facts.json')))
    tokens = {k: v for k, v in tokens.items() if not k.startswith('_')}
    posts = blog.load_posts(os.path.join(bdir, 'en'), tokens)
    live = blog.published(posts, production)
    parts = dict(partials)
    pdir = os.path.join(bdir, 'partials')
    for f in sorted(os.listdir(pdir)):
        parts['blog_' + os.path.splitext(f)[0]] = _read(os.path.join(pdir, f))
    t_post = _read(os.path.join(bdir, 'post.html'))
    t_index = _read(os.path.join(bdir, 'index.html'))
    banned = load_banned(os.path.join(bdir, 'banned.json'))
    base = site['siteUrl']
    files, problems, notes, entries = {}, [], [], []
    s = strings['post']

    rendered = {}
    for p in live:
        rendered[p.slug] = blog.render_body(p, posts, production=production,
                                            figures_dir=os.path.join(bdir, 'figures'), root=root)
        if rendered[p.slug].unwrapped:
            notes.append(f'{p.slug}: links to unpublished {", ".join(rendered[p.slug].unwrapped)} shown as plain text')

    def item(p):
        return {'num': p.num, 'url': p.url, 'title': p.title, 'dek': p.description, 'draft': p.draft,
                'date_iso': p.date.isoformat(), 'date_human': blog.human_date(p.date),
                'minutes': rendered[p.slug].minutes, 'read': f"{rendered[p.slug].minutes} {s['read']}"}

    for p in live:
        r = rendered[p.slug]
        og = _og(root, site, p.slug)
        ctx = _common(site, c_en, strings, production)
        ctx.update({
            'nav_current': 'true',
            'fonts': blog.font_links(blog.arabic_chars('عربي', c_en['footer']['brand'], r.html)),
            'page': {'title': f'{p.title} | Hafr', 'description': p.description, 'canonical': base + p.url,
                     'og_type': 'article', 'og_title': p.title, 'og_image': og, 'og_image_alt': p.title,
                     'is_article': True, 'jsonld': blog.jsonld_post(site, p, r, og)},
            'post': {**item(p), 'updated_iso': p.updated.isoformat(),
                     'updated_human': blog.human_date(p.updated), 'show_updated': p.updated != p.date,
                     'body': r.html, 'toc': r.toc, 'has_toc': len(r.toc) >= 3,
                     'related': [item(q) for q in blog.related(p, r, live)],
                     'has_related': len(live) > 1},
            'cta': {'text': p.cta, 'wa_url': whatsapp_url(site.get('whatsapp'), blog.wa_message(p))},
        })
        page = render(t_post, ctx, partials=parts, dev=not production)
        files[f'en/blog/{p.slug}/index.html'] = page
        if not p.draft:
            entries.append((base + p.url, p.updated.isoformat()))
        problems += [f'{p.slug}: banned term {hit}' for hit in find_banned(page, banned)]

    idx = strings['index']
    listed = sorted(live, key=lambda p: p.number, reverse=True)
    ctx = _common(site, c_en, strings, production)
    ctx.update({
        'nav_current': 'page',
        'fonts': blog.font_links(blog.arabic_chars('عربي', c_en['footer']['brand'])),
        'page': {'title': idx['title'], 'description': idx['description'], 'canonical': base + blog.BLOG_PATH,
                 'og_type': 'website', 'og_title': idx['h1'], 'og_image': _og(root, site, '_index'),
                 'og_image_alt': idx['h1'], 'is_article': False,
                 'jsonld': blog.jsonld_index(site, [p for p in listed if not p.draft], idx['h1'], idx['description'])},
        'index': {**idx, 'posts': [item(p) for p in listed], 'has_posts': bool(listed), 'empty_state': not listed},
        'cta': {'text': idx['cta'], 'wa_url': whatsapp_url(site.get('whatsapp'), idx['wa_message'])},
    })
    page = render(t_index, ctx, partials=parts, dev=not production)
    files['en/blog/index.html'] = page
    problems += [f'blog index: banned term {hit}' for hit in find_banned(page, banned)]
    entries.insert(0, (base + blog.BLOG_PATH, max((p.updated.isoformat() for p in listed if not p.draft),
                                                  default=None)))
    files['en/blog/feed.xml'] = blog.feed(site, [p for p in listed if not p.draft], idx['h1'])

    if production:
        for path, text in files.items():
            if '[[' in text:
                problems.append(f'{path}: unresolved [[placeholder]]')
            if 'data-draft' in text:
                problems.append(f'{path}: a draft guide was rendered in production')
    drafts = [p.slug for p in posts if p.draft]
    if drafts:
        notes.append(f'drafts {"left out" if production else "previewed with a badge"}: {", ".join(drafts)}')
    return files, entries, problems, notes
