"""Build hafr.ae.

    python build.py                 development build into dev/ (placeholders visible, noindex)
    python build.py --production    production build into public/ (fails on any rule breach)

Options: --out DIR, --site FILE, --content DIR, --cdn URL (development only).
"""
import argparse
import json
import os
import shutil
import sys

from hafrbuild.checks import find_banned, load_banned, validate_site
from hafrbuild.pages import (DEFAULT_CDN, amiri_text, arabic_chars, font_links, importmap,
                             page_context, robots, sitemap, gate)
from hafrbuild.render import RenderError, render

ROOT = os.path.dirname(os.path.abspath(__file__))


def _read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)


def parity(a, b, path=''):
    """Both languages must share one shape: same keys, same list lengths."""
    errors = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            sub = f'{path}.{key}' if path else key
            if key not in a or key not in b:
                errors.append(f'key only in one language: {sub}')
            else:
                errors += parity(a[key], b[key], sub)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            errors.append(f'list length differs: {path} (ar {len(a)}, en {len(b)})')
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                errors += parity(x, y, f'{path}[{i}]')
    elif type(a) is not type(b):
        errors.append(f'type differs: {path}')
    return errors


def main(argv=None):
    # Arabic and other non-Latin text in messages must never crash a legacy console.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    ap = argparse.ArgumentParser(description='Build hafr.ae')
    ap.add_argument('--production', action='store_true')
    ap.add_argument('--out')
    ap.add_argument('--site', default=os.path.join(ROOT, 'src', 'site.json'))
    ap.add_argument('--content', default=os.path.join(ROOT, 'src', 'content'))
    ap.add_argument('--cdn')
    args = ap.parse_args(argv)
    production = args.production
    out = args.out or os.path.join(ROOT, 'public' if production else 'dev')

    def fail(errors):
        for e in errors:
            print(f'error: {e}', file=sys.stderr)
        return 1

    if production and args.cdn:
        return fail(['--cdn is for development builds only'])

    site = json.loads(_read(args.site))
    contents = {lang: json.loads(_read(os.path.join(args.content, f'{lang}.json'))) for lang in ('ar', 'en')}
    errors = validate_site(site, production) + parity(contents['ar'], contents['en'])
    if errors:
        return fail(errors)

    template = _read(os.path.join(ROOT, 'src', 'template.html'))
    pdir = os.path.join(ROOT, 'src', 'partials')
    partials = {os.path.splitext(f)[0]: _read(os.path.join(pdir, f)) for f in sorted(os.listdir(pdir))}
    head_js = _read(os.path.join(ROOT, 'assets', 'js', 'head.js'))
    if not production:
        head_js = 'window.__HAFR_DEV=true;\n' + head_js
    imap = importmap(args.cdn or DEFAULT_CDN)
    amiri = amiri_text([contents['ar']])

    pages = {}
    try:
        for lang in ('ar', 'en'):
            if lang == 'ar':
                fonts = font_links('ar', amiri)
            else:
                # English page: Arabic appears only in the proof sheet, night scene, brand line and switch.
                amiri_en = ''.join(ch for ch in amiri_text([contents['en']]) if '؀' <= ch <= 'ۿ')
                fonts = font_links('en', amiri_en, cairo_text=arabic_chars(contents['en']) + 'عربي')
            ctx = page_context(lang, site, contents[lang], production=production,
                               head_js=head_js, importmap=imap, fonts=fonts)
            pages[lang] = render(template, ctx, partials=partials, dev=not production)
    except RenderError as exc:
        return fail([f'render: {exc}'])

    banned = load_banned(os.path.join(ROOT, 'src', 'banned.json'))
    problems = []
    for lang, page in pages.items():
        problems += [f'{lang}: banned term {hit}' for hit in find_banned(page, banned)]
        if production and '[[' in page:
            problems.append(f'{lang}: unresolved [[placeholder]] in output')
        if production and 'data-pending' in page:
            problems.append(f'{lang}: pending claim rendered in production')
    if production and problems:
        return fail(problems)
    for p in problems:
        print(f'warning: {p}', file=sys.stderr)

    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(ROOT, 'assets'), os.path.join(out, 'assets'),
                    ignore=shutil.ignore_patterns('*.test.*', '__pycache__'))
    shutil.copy(os.path.join(ROOT, 'CNAME'), os.path.join(out, 'CNAME'))
    _write(os.path.join(out, 'index.html'), pages['ar'])
    _write(os.path.join(out, 'en', 'index.html'), pages['en'])
    _write(os.path.join(out, 'sitemap.xml'), sitemap(site))
    _write(os.path.join(out, 'robots.txt'), robots(site, production))

    _, omitted = gate(contents['ar'], production=True)
    if omitted:
        state = 'left out of production' if production else 'shown as pending here, left out of production'
        print(f'gated claims {state}: {", ".join(omitted)}')
    print(f'built {"production" if production else "development"} site -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
