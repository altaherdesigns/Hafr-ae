# hafr.ae

Source for the Hafr landing page (Arabic at `/`, English at `/en/`) and the English guides at `/en/blog/`. The landing page opens with a 3D exploded assembly of the logo, which falls back to a still image wherever 3D isn't suitable.

Specs, research and logo masters are kept in `D:\Hafr`, not here. This repository holds only what the site build needs.

## Build

```
python build.py                 # development build into dev/ (placeholders visible, noindex)
python build.py --production    # production build into public/
```

The build needs only Python 3.12 and its standard library. A production build fails and lists what's wrong if any of these are true:

- `src/site.json` is missing the WhatsApp number (format `9715XXXXXXXX`);
- a banned word appears anywhere on either page (see `src/banned.json`);
- a placeholder is left unfilled;
- the Arabic and English content files don't have the same shape.

## Preview

```
python -m http.server 8765 -d dev
```

Then open `http://localhost:8765/` (Arabic) or `http://localhost:8765/en/` (English). Development builds accept two URL parameters:

- `?stage=3d` or `?stage=still` forces the stage mode;
- `?p=0.35` freezes the stage at that point in the scroll.

## Tests

```
python -m unittest discover -s tests
node --test "tests/js/*.test.mjs"
```

## Copy

All copy lives in `src/content/ar.json` and `src/content/en.json`, which must stay the same shape. Arabic copy is read by a second, native Arabic reader before it ships.

Some claims are gated, each marked `"status": "pending"` or `"verified"`. These are the "Built to stay outside" rows, the lighting line and the kit list. A production build leaves out anything still pending. To publish a claim once it is confirmed, change its status to `"verified"` in **both** files.

## Guides (`/en/blog/`)

Each guide is one Markdown file in `src/blog/en/`, named `NN-slug.md`. `NN` is the guide's number and the slug is its address: `src/blog/en/09-corten-signs.md` is published at `/en/blog/corten-signs/`.

The file starts with front matter between `---` lines:

```
---
title: "Title, up to 70 characters"
slug: corten-signs
meta_description: "What the guide answers, 70 to 160 characters."
date: 2026-10-10
cta: "One sentence that leads into the WhatsApp block at the end."
draft: true            # optional: kept out of the live site until removed or set to false
primary_keyword: ...   # optional, with secondary_keywords: [a, b] and arabic_keyword: "..."
---
```

The body uses a strict Markdown subset (see `hafrbuild/markdown.py`): `##` and `###` headings, paragraphs, bold, italic, links, one-level lists, tables, and figures on a line of their own. A `## Frequently asked questions` section must be a bold question on one line and its answer on the next. Anything else fails the build, so a broken guide can never go live.

- **Links between guides** are written `/blog/<slug>/`. A link to a draft shows as plain text until that guide is published, then becomes a link by itself. A link to a guide that doesn't exist fails the build.
- **Figures** are SVG drawings in `src/blog/figures/`, written `![Alt text, a full sentence](figures/name.svg "Caption")` and placed inline in the page. Photos go in `assets/blog/img/` as WebP, JPEG or PNG.
- **Figures quoted in guides**, such as the starting price and the lead time, live in `src/blog/facts.json` and are written in a guide as `{{PRICE_FROM}}`. Change a value there and every guide updates on the next build.
- **Share cards** (`assets/blog/og/<slug>.jpg`, 1200 x 630) are made by `D:\Hafr\tools\make_blog_og.mjs` and committed. A guide without one uses the site's share image.
- **Rules.** The guides follow `src/blog/banned.json`, and the landing page follows the stricter `src/banned.json`. A production build fails on a breach of either.
- The writing standard, confirmed facts and the topic list for new guides are kept in `D:\Hafr\blog\` (`STYLE.md`, `FACTS.md`, `backlog.md`), not here.

## Deploy

Every push to `main` runs `.github/workflows/pages.yml`. It runs both test suites, does a production build and publishes `public/` to GitHub Pages. Nothing outside `public/` is served.

To set it up:

- In *Settings → Pages*, set the source to **GitHub Actions** and the custom domain to `hafr.ae`.
- Tick *Enforce HTTPS* once the certificate is issued.

The DNS records are listed in the site spec in `D:\Hafr\docs\specs`.

## Images

The images in `assets/img/` are generated once by `D:\Hafr\tools\make_site_images.py` from the locked logo geometry. They are committed here, so the build itself never generates images.
