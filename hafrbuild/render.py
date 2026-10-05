"""A deliberately small slot language for the site template.

{{a.b}}            HTML-escaped text
{{a.b|attr}}       escaped for an attribute value (quotes included)
{{a.b|html}}       trusted inline markup from the content files (allow-listed tags only)
{{a.b|url}}        percent-encoded with no safe characters
{{a.b|raw}}        emitted as is; only for values the build generates itself
{{#each a.b}}…{{/each}}   loop; inside: {{.x}} item field, {{.}} the item, {{@n}} 1-based, {{@nn}} "01"
{{#if a.b}}…{{/if}}       rendered when the value is truthy
{{> name}}         partial template, rendered with the same context

A missing key always raises. A None value renders as a visible [[key]] in dev
builds and raises in production, so nothing unknown can ship silently.
"""
import html
import re
import urllib.parse
from html.parser import HTMLParser

TOKEN = re.compile(r'\{\{\s*(.+?)\s*\}\}', re.S)
FILTERS = {'attr', 'html', 'url', 'raw'}
ALLOWED_TAGS = {'em', 'br', 'a', 'bdi', 'span'}
ALLOWED_ATTRS = {'href', 'lang', 'dir', 'hreflang', 'target', 'rel', 'class'}
_MISSING = object()


class RenderError(Exception):
    pass


def _parse(template):
    root = []
    stack = [('root', None, root)]
    pos = 0
    for m in TOKEN.finditer(template):
        if m.start() > pos:
            stack[-1][2].append(('text', template[pos:m.start()]))
        pos = m.end()
        tag = m.group(1)
        if tag.startswith('#each ') or tag.startswith('#if '):
            kind, name = tag[1:].split(None, 1)
            children = []
            stack[-1][2].append((kind, name.strip(), children))
            stack.append((kind, name.strip(), children))
        elif tag in ('/each', '/if'):
            if stack[-1][0] != tag[1:]:
                raise RenderError(f'unexpected {{{{{tag}}}}}')
            stack.pop()
        elif tag.startswith('>'):
            stack[-1][2].append(('partial', tag[1:].strip()))
        else:
            name, _, flt = tag.partition('|')
            name, flt = name.strip(), flt.strip() or None
            if flt and flt not in FILTERS:
                raise RenderError(f'unknown filter: {flt}')
            stack[-1][2].append(('var', name, flt))
    if len(stack) != 1:
        raise RenderError(f'unclosed {{{{#{stack[-1][0]} {stack[-1][1]}}}}}')
    if pos < len(template):
        root.append(('text', template[pos:]))
    return root


class _Scope:
    def __init__(self, root, item=_MISSING, index=None, parent=None):
        self.root, self.item, self.index, self.parent = root, item, index, parent

    def lookup(self, name):
        if name == '@n' or name == '@nn':
            if self.index is None:
                raise RenderError(f'{name} used outside #each')
            return self.index + 1 if name == '@n' else f'{self.index + 1:02d}'
        if name == '.':
            if self.item is _MISSING:
                raise RenderError('{{.}} used outside #each')
            return self.item
        if name.startswith('.'):
            if self.item is _MISSING:
                raise RenderError(f'{name} used outside #each')
            return _dig(self.item, name[1:].split('.'), name)
        return _dig(self.root, name.split('.'), name)


def _dig(value, parts, full):
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise RenderError(f'missing slot: {full}')
    return value


class _MarkupCheck(HTMLParser):
    def handle_starttag(self, tag, attrs):
        self._check(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._check(tag, attrs)

    def _check(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            raise RenderError(f'tag not allowed in |html: <{tag}>')
        for key, val in attrs:
            if key not in ALLOWED_ATTRS:
                raise RenderError(f'attribute not allowed in |html: {key}')
            if key == 'href' and val and val.strip().lower().startswith('javascript:'):
                raise RenderError('javascript: links are not allowed')


def _format(value, flt, name):
    text = str(value)
    if flt is None:
        return html.escape(text, quote=False)
    if flt == 'attr':
        return html.escape(text, quote=True)
    if flt == 'url':
        return urllib.parse.quote(text, safe='')
    if flt == 'html':
        _MarkupCheck().feed(text)
        return text
    return text  # raw


def render(template, ctx, *, partials, dev):
    cache = {}

    def nodes_for(name):
        if name not in partials:
            raise RenderError(f'missing partial: {name}')
        if name not in cache:
            cache[name] = _parse(partials[name])
        return cache[name]

    def run(nodes, scope, depth):
        if depth > 8:
            raise RenderError('partials nested too deeply')
        out = []
        for node in nodes:
            kind = node[0]
            if kind == 'text':
                out.append(node[1])
            elif kind == 'var':
                _, name, flt = node
                value = scope.lookup(name)
                if value is None:
                    if not dev:
                        raise RenderError(f'empty slot in production: {name}')
                    out.append(f'[[{name.lstrip(".")}]]')
                else:
                    out.append(_format(value, flt, name))
            elif kind == 'if':
                if scope.lookup(node[1]):
                    out.append(run(node[2], scope, depth))
            elif kind == 'each':
                items = scope.lookup(node[1])
                if not isinstance(items, list):
                    raise RenderError(f'#each needs a list: {node[1]}')
                for i, item in enumerate(items):
                    out.append(run(node[2], _Scope(scope.root, item, i, scope), depth))
            elif kind == 'partial':
                out.append(run(nodes_for(node[1]), scope, depth + 1))
        return ''.join(out)

    return run(_parse(template), _Scope(ctx), 0)
