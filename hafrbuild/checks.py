"""Content-rule enforcement: site settings, and words that must never ship.

Hafr's owner rules (spec §3): no material names, no prices or warranties, no
durations, none of the Language Bank's AVOID words. These are checked on the
generated HTML, so a banned word in an alt text, aria label, meta tag or the
JSON-LD fails the build just like one in visible copy.
"""
import json
import re
from html.parser import HTMLParser

SITE_RULES = {
    'siteUrl': (re.compile(r'^https://[a-z0-9.-]+$'), True),
    'whatsapp': (re.compile(r'^9715\d{8}$'), True),
    'instagram': (re.compile(r'^[A-Za-z0-9._]{1,30}$'), False),
}


def validate_site(site, production):
    errors = []
    for key, (pattern, required) in SITE_RULES.items():
        value = site.get(key)
        if value is None:
            if required and production:
                errors.append(f'{key}: required for a production build (currently null)')
            continue
        if not isinstance(value, str) or not pattern.match(value):
            errors.append(f'{key}: {value!r} does not match {pattern.pattern}')
    return errors


def load_banned(path):
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    return {'latin': data.get('latin', []), 'arabic': data.get('arabic', []),
            'patterns': data.get('patterns', [])}


class _Collector(HTMLParser):
    """Collects text nodes, every attribute value and JSON-LD bodies."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        for _, value in attrs:
            if value:
                self.chunks.append(value)
        if tag == 'style' or (tag == 'script' and dict(attrs).get('type') != 'application/ld+json'):
            self._skip += 1

    def handle_startendtag(self, tag, attrs):
        for _, value in attrs:
            if value:
                self.chunks.append(value)

    def handle_endtag(self, tag):
        if tag in ('style', 'script') and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.chunks.append(data)


def _compile(banned):
    rules = []
    for term in banned['latin']:
        rules.append((term, re.compile(r'(?<![A-Za-z0-9])' + re.escape(term) + r'(?![A-Za-z0-9])', re.I)))
    for term in banned['arabic']:
        rules.append((term, re.compile(re.escape(term))))
    for pattern in banned['patterns']:
        rules.append((pattern, re.compile(pattern, re.I)))
    return rules


def find_banned(html_text, banned):
    collector = _Collector()
    collector.feed(html_text)
    collector.close()
    rules = _compile(banned)
    hits = []
    for chunk in collector.chunks:
        for label, rule in rules:
            match = rule.search(chunk)
            if match:
                hits.append(f'{label!r} in: {chunk.strip()[:80]!r}')
    return hits
