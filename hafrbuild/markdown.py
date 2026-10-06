"""A strict Markdown subset for the guides (standard library only).

Supported, and nothing else:

    ## Heading / ### Heading         (H1 is the post title, so it is not allowed in the body)
    paragraphs, **bold**, *italic*, [text](href)
    - unordered lists / 1. ordered lists   (one level, no nesting)
    | pipe | tables |                       (header row + separator row required)
    ![alt text](figures/name.svg "Caption")  on a line of its own -> <figure>
    ---                                      -> a 35-degree hairline divider

Under a "## Frequently asked questions" heading every paragraph must be a
question in bold on its first line, with the answer on the following line(s).

Anything else (raw HTML, block quotes, code, nested lists, H1/H4+) raises
MarkdownError, so a post that would render wrongly never ships quietly.
"""
import html
import re

FAQ_TITLE = re.compile(r'^frequently asked questions$', re.I)
_LINK = re.compile(r'\[([^\]\n]+)\]\(([^)\s]+)\)')
_BOLD = re.compile(r'\*\*(.+?)\*\*', re.S)
_ITALIC = re.compile(r'(?<![\*\w])\*(?![\s\*])(.+?)(?<![\s\*])\*(?![\*\w])', re.S)
_IMAGE_LINE = re.compile(r'^!\[([^\]\n]+)\]\(([^)\s"]+)(?:\s+"([^"]*)")?\)$')
_ARABIC_RUN = re.compile(r'[\u0600-\u06FF](?:[\u0600-\u06FF\s\u060C\u061B]*[\u0600-\u06FF])?')
_ORDERED = re.compile(r'^(\d{1,3})\.\s+(.*)$')
_TABLE_SEP = re.compile(r'^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$')


class MarkdownError(Exception):
    pass


def slugify(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text).lower()
    text = re.sub(r'[\u2018\u2019\u201c\u201d\'"]', '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text or 'section'


def smart_quotes(text):
    """Typographic quotes and apostrophes for plain text (never for URLs)."""
    text = re.sub(r'(^|[\s(\[\u2014\u2013/-])"', '\\1\u201c', text)
    text = text.replace('"', '\u201d')
    text = re.sub(r"(^|[\s(\[\u2014\u2013/-])'", '\\1\u2018', text)
    text = text.replace("'", '\u2019')
    return text


def plain(md_inline):
    """Inline Markdown reduced to plain text (for titles, JSON-LD and the TOC)."""
    t = _LINK.sub(lambda m: m.group(1), md_inline)
    t = _BOLD.sub(lambda m: m.group(1), t)
    t = _ITALIC.sub(lambda m: m.group(1), t)
    return smart_quotes(re.sub(r'\s+', ' ', t).strip())


def _text(segment):
    escaped = html.escape(segment, quote=False)
    return _ARABIC_RUN.sub(lambda m: f'<span lang="ar" dir="rtl">{m.group(0)}</span>', escaped)


class Renderer:
    """Turns Markdown into HTML. `resolve_link(href)` returns (href, external) or
    (None, False) to unwrap the link to plain text; it raises MarkdownError for a
    link that must not ship. `figure(src, alt, caption, n)` returns figure HTML."""

    def __init__(self, resolve_link, figure):
        self.resolve_link = resolve_link
        self.figure = figure
        self.headings = []      # [(level, id, text)]
        self.faq = []           # [(question_text, answer_text, answer_html)]
        self.figures = 0
        self.words = 0
        self._ids = set()

    # ---------- inline ----------
    def inline(self, src):
        if '<' in src and re.search(r'<[a-zA-Z/!]', src):
            raise MarkdownError(f'raw HTML is not allowed: {src.strip()[:60]!r}')
        if '`' in src:
            raise MarkdownError(f'code spans are not allowed: {src.strip()[:60]!r}')
        if '![' in src:
            raise MarkdownError(f'images must sit on a line of their own: {src.strip()[:60]!r}')
        # Curl quotes across the whole run (so a quote closing after **bold** stays a
        # closing quote), but never inside link targets.
        hrefs = []

        def mask(m):
            hrefs.append(m.group(2))
            return f'[{m.group(1)}](\x00{len(hrefs) - 1}\x00)'
        curled = smart_quotes(_LINK.sub(mask, src))
        return self._inline(re.sub('\x00(\\d+)\x00', lambda m: hrefs[int(m.group(1))], curled))

    def _inline(self, src):
        out, pos = [], 0
        patterns = (('link', _LINK), ('bold', _BOLD), ('em', _ITALIC))
        while pos < len(src):
            best = None
            for kind, rx in patterns:
                m = rx.search(src, pos)
                if m and (best is None or m.start() < best[1].start()):
                    best = (kind, m)
            if not best:
                out.append(_text(src[pos:]))
                break
            kind, m = best
            out.append(_text(src[pos:m.start()]))
            if kind == 'link':
                href, external = self.resolve_link(m.group(2))
                inner = self._inline(m.group(1))
                if href is None:
                    out.append(inner)
                else:
                    extra = ' target="_blank" rel="noopener"' if external else ''
                    out.append(f'<a href="{html.escape(href, quote=True)}"{extra}>{inner}</a>')
            elif kind == 'bold':
                out.append(f'<strong>{self._inline(m.group(1))}</strong>')
            else:
                out.append(f'<em>{self._inline(m.group(1))}</em>')
            pos = m.end()
        return ''.join(out)

    # ---------- blocks ----------
    def _heading_id(self, text):
        base = slugify(text)
        hid, n = base, 2
        while hid in self._ids:
            hid, n = f'{base}-{n}', n + 1
        self._ids.add(hid)
        return hid

    def render(self, source):
        blocks = _split_blocks(source)
        out, in_faq, faq_items = [], False, []

        def close_faq():
            if faq_items:
                out.append('<div class="faq__list">' + ''.join(faq_items) + '</div></section>')
                faq_items.clear()

        for kind, lines in blocks:
            text = '\n'.join(lines)
            self.words += len(re.findall(r"[\w'\u2019-]+", plain(text)))
            if kind == 'heading':
                level = len(lines[0]) - len(lines[0].lstrip('#'))
                title_md = lines[0][level:].strip()
                if level not in (2, 3):
                    raise MarkdownError(f'only ## and ### headings are allowed: {lines[0][:60]!r}')
                if in_faq and level == 2:
                    close_faq()
                    in_faq = False
                hid = self._heading_id(plain(title_md))
                title_html = self.inline(title_md)
                if level == 2:
                    self.headings.append((2, hid, plain(title_md)))
                if level == 2 and FAQ_TITLE.match(plain(title_md)):
                    in_faq = True
                    out.append(f'<section class="faq" aria-labelledby="{hid}"><h2 id="{hid}">{title_html}</h2>')
                    continue
                out.append(f'<h{level} id="{hid}">{title_html}</h{level}>')
            elif in_faq:
                if kind != 'para' or not lines[0].startswith('**') or not lines[0].rstrip().endswith('**') or len(lines) < 2:
                    raise MarkdownError('under "Frequently asked questions" each block must be '
                                        '**Question** on one line followed by its answer')
                q_md = lines[0].strip()[2:-2]
                a_md = ' '.join(l.strip() for l in lines[1:])
                a_html = self.inline(a_md)
                self.faq.append((plain(q_md), plain(a_md), a_html))
                faq_items.append(f'<details class="faq__item"><summary class="faq__q">{self.inline(q_md)}</summary>'
                                 f'<div class="faq__a"><p>{a_html}</p></div></details>')
            elif kind == 'para':
                m = _IMAGE_LINE.match(text.strip())
                if m:
                    self.figures += 1
                    out.append(self.figure(m.group(2), plain(m.group(1)), plain(m.group(3) or ''), self.figures))
                else:
                    out.append(f'<p>{self.inline(" ".join(l.strip() for l in lines))}</p>')
            elif kind in ('ul', 'ol'):
                tag = kind
                items = ''.join(f'<li>{self.inline(item)}</li>' for item in _list_items(kind, lines))
                out.append(f'<{tag}>{items}</{tag}>')
            elif kind == 'table':
                out.append(self._table(lines))
            elif kind == 'hr':
                out.append('<hr class="cut">')
        if in_faq:
            close_faq()
        return '\n'.join(out)

    def _table(self, lines):
        rows = [_cells(l) for l in lines]
        if len(rows) < 3 or not _TABLE_SEP.match(lines[1].strip()):
            raise MarkdownError('a table needs a header row, a separator row and at least one body row')
        head, body = rows[0], rows[2:]
        for r in body:
            if len(r) != len(head):
                raise MarkdownError(f'table row has {len(r)} cells, header has {len(head)}')
        th = ''.join(f'<th scope="col">{self.inline(c)}</th>' for c in head)
        trs = []
        for r in body:
            cells = [f'<th scope="row" data-label="{html.escape(plain(head[0]), quote=True)}">{self.inline(r[0])}</th>']
            cells += [f'<td data-label="{html.escape(plain(h), quote=True)}">{self.inline(c)}</td>'
                      for h, c in zip(head[1:], r[1:])]
            trs.append('<tr>' + ''.join(cells) + '</tr>')
        return (f'<div class="tbl"><table><thead><tr>{th}</tr></thead>'
                f'<tbody>{"".join(trs)}</tbody></table></div>')


def _cells(line):
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def _list_items(kind, lines):
    items = []
    for line in lines:
        if line.startswith((' ', '\t')):
            if line.strip()[:2] in ('- ', '* ') or _ORDERED.match(line.strip()):
                raise MarkdownError(f'nested lists are not allowed: {line.strip()[:60]!r}')
            items[-1] += ' ' + line.strip()
            continue
        if kind == 'ul':
            items.append(line[2:].strip())
        else:
            items.append(_ORDERED.match(line).group(2).strip())
    return items


def _split_blocks(source):
    """Group lines into (kind, lines) blocks separated by blank lines."""
    blocks, cur, kind = [], [], None

    def flush():
        nonlocal cur, kind
        if cur:
            blocks.append((kind, cur))
        cur, kind = [], None

    for raw in source.replace('\r\n', '\n').split('\n'):
        line = raw.rstrip()
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith('```') or s.startswith('>') or s.startswith('<'):
            raise MarkdownError(f'not allowed in a guide: {s[:60]!r}')
        if s.startswith('#') and not line.startswith((' ', '\t')):
            flush()
            if not re.match(r'^#{1,6}\s', s):
                raise MarkdownError(f'heading needs a space after the hashes: {s[:60]!r}')
            blocks.append(('heading', [s]))
            continue
        if re.fullmatch(r'-{3,}|\*{3,}', s):
            flush()
            blocks.append(('hr', [s]))
            continue
        starts_ul = line[:2] in ('- ', '* ')
        starts_ol = bool(_ORDERED.match(line)) and not line.startswith((' ', '\t'))
        starts_table = s.startswith('|')
        if kind is None:
            kind = 'ul' if starts_ul else 'ol' if starts_ol else 'table' if starts_table else 'para'
        elif kind == 'para' and (starts_ul or starts_ol or starts_table):
            flush()
            kind = 'ul' if starts_ul else 'ol' if starts_ol else 'table'
        elif kind in ('ul', 'ol') and not (starts_ul or starts_ol or line.startswith((' ', '\t'))):
            raise MarkdownError(f'leave a blank line after a list: {s[:60]!r}')
        elif kind == 'table' and not starts_table:
            raise MarkdownError(f'leave a blank line after a table: {s[:60]!r}')
        if kind == 'ul' and starts_ol or kind == 'ol' and starts_ul:
            raise MarkdownError(f'do not mix list types in one list: {s[:60]!r}')
        cur.append(line)
    flush()
    return blocks
