# Hafr landing page — design spec

Date: 5 October 2026 · Status: draft for owner review · Owner: Muaaz Butt

## 1. Purpose and success

A single landing page for Hafr (حفر), the exterior villa-signage line of Al Taher Group. It has to make a private Emirati or GCC villa owner feel that a family name in metal at their gate is a considered commission, and then start that conversation on WhatsApp. Sales are a guided conversation that begins with a photo of the wall; the page is not a shop.

The page succeeds when:

- the opening motion reads as craftsmanship (a fabricator's exploded drawing coming to life), not as a gimmick;
- Arabic readers get a first-class Arabic page by default, and English readers get the same page in English;
- it runs smoothly on a mid-range phone and degrades to a still version wherever 3D is not appropriate;
- nothing on it is a claim Hafr cannot yet back.

## 2. Decisions already made

| Decision | Detail | Source |
|---|---|---|
| Logo | 07 Slice is locked: heavy Kufi حفر with one straight laser kerf at 35°, Latin HAFR beneath, split-tag maker's mark. Geometry is copied exactly from the canvas, not redrawn. | Owner, 5 Oct 2026 |
| Logo files | SVG and 2400 px transparent PNG, ink `#14120F` and light `#F1EDE4`: lockup, Arabic, Latin, maker's mark. Saved in `D:\Hafr\logo\`. | Done 5 Oct 2026 |
| Motion | Scroll-driven exploded assembly of the logo. No material is named anywhere in it. | Owner |
| Rendering | Real 3D in the browser (WebGL via three.js), with a still fallback. | Owner |
| Language | Arabic is the default page; a full English page mirrors it. | Owner |
| Palette | Close to Al Taher's (altaherdesign.ae) but darker and quieter. | Owner |
| Durability section | Kept, written without naming any material. | Owner |
| Al Taher | A discreet part with a backlink to altaherdesign.ae. | Owner |
| Founding year | Al Taher's live site and its WPVC artwork say 1984; the Hafr documents say 1983. The page uses **1984**. | Owner did not object |
| Where it lives | Repo folder `C:\Users\SaaD Computer\Documents\GitHub\Hafr`, site at the root. | Owner |

## 3. Content rules

**Audience:** private Emirati and GCC villa owners on owner-built plots (Al Barsha, Jumeirah, Umm Suqeim, Mirdif, Al Warqa, Sharjah, Al Ain, Abu Dhabi). Contractors and expats are a secondary audience.

**Single call to action:** start a WhatsApp conversation.

**Never publish:**

- prices or price bands (the ladder in the Hafr documents is still an assumption to be costed);
- names of materials or grades (no stainless, grade numbers, aluminium, brass and so on);
- certifications, coating classes, warranties or durations ("20 years", "lifetime");
- statistics, testimonials, client names or photographs that do not exist yet;
- a real family name as an example. Use **اسمك** / *your name*.

**May publish** (all from `D:\Hafr`):

- the five products: house numbers; family names in Arabic with optional Latin; flags and family crests; gate and boundary-wall panels and screens; plot-entrance monuments. Interior cut wall art as one quiet line;
- the conditions: 45–50°C summers, intense UV, coastal salt, seasonal humidity, winter sand;
- the engineering intent, without materials: metal chosen by distance from the sea, thickness matched to size, fixings matched to the sign so they do not stain the wall, sealed lighting rated for 50°C with a reachable driver, 15–25 mm standoffs for drainage and a true shadow, every cut edge deburred and rounded;
- the proof and sign-off process (six steps, below);
- the fixing kit and "installation on request; where Hafr installs, Hafr handles community or municipality approval";
- what to send to start: a photo of the wall or gate, the rough width, the wall material, whether there is power nearby (for lighting), and the name typed in Arabic.

**Copy that needs a check before launch:**

- the durability line "finishes chosen to hold their colour in Gulf sun" stays only if Al Taher's coating line confirms it;
- all Arabic copy is read by a second, native Arabic reader before launch, matching Hafr's own proof rule.

## 4. Page structure

Headlines are given in both languages; body copy is written during implementation within the rules above.

1. **Header** — the lockup (light on the stage, ink once scrolled onto ivory), four anchor links on desktop, the language switch (English / عربي) and a "Begin / ابدأ" button that jumps to the last section. On phones: logo, language switch and button only.
2. **Opening stage** (pinned, §5). Headline **اسمُ العائلة، محفورٌ ليبقى** / *Your family name, cut in metal. Built to stay outside.*
3. **ما نصنع / What we make** — the five products as typographic rows: number, name, one line of description. No icons or prices. Interior wall art as one line under the list.
4. **صُنع ليبقى في الخارج / Built to stay outside** — a two-column comparison on night petrol: *what fails here* against *how Hafr builds*, seven rows, no materials named:
   1. printed faces that chalk and fade in the sun, against finishes chosen to hold their colour (pending check, §3);
   2. thin sheets that bend in the heat and lift at the fixings, against thickness matched to the size of each piece;
   3. metal that rusts near the sea and stains the wall, against metal chosen by the plot's distance from the sea;
   4. fixings that rust before the sign does, against fixings matched to the sign so they do not stain the wall;
   5. lights that cook in a 50°C summer and fail one letter at a time, against sealed lighting rated for 50°C with a driver that can be reached;
   6. flush mounting that traps water and stains a rectangle on the wall, against mounting 15–25 mm off the wall for drainage, air and a true shadow;
   7. raw, sharp cut edges, against every edge deburred and rounded.
5. **الاسمُ هو القطعة / The name is the piece** — the proof sheet visual beside six steps: you type the name in Arabic yourself; choose from two or three settings of your actual name; see it at true proportions on a photo of your own wall; sign it off in writing; a second Arabic reader checks it against your text; the file is locked, cut, finished and photographed before it ships.
6. **بعد الغروب / After dark** — halo-lit and front-lit options, with a night render (a halo-lit house number ٢٤ on a dark wall). Copy: sealed lighting for 50°C summers, with a driver placed where it can be reached.
7. **يصلك جاهزاً للتركيب / Delivered ready to fit** — the kit as a quiet list: full-size drilling template with the drill size printed on it; anchors for UAE block-and-render walls plus spares; standoffs matched to the piece; the exact key; a small spirit level; photo instructions in Arabic and English; protective film that comes off last. Then: installation on request, with approvals handled where Hafr installs.
8. **ابدأ بصورةٍ لجدارك / Start with a photo of your wall** — the five things to send and one WhatsApp button that opens a pre-filled message in the page's language.
9. **Footer** — the lockup, one line describing Hafr, anchor links, WhatsApp, the Al Taher part (§8), and © Hafr with the year.

## 5. Opening stage

**Layout:** a section 500 vh tall containing a sticky full-viewport stage. The WebGL canvas fills the stage. The headline, scroll cue and captions are real HTML layered over it.

**Scene:**

- a wall plane in night petrol with a subtle limewash texture (procedural noise, no image file);
- the logo extruded from the locked outlines: Arabic pieces (two kerf-cut pieces plus the dot), and the Latin letters H, A, F, R as separate pieces. Depth is about 4% of the logo width, with a small rounded bevel;
- the material is a satin champagne-bronze metal (metalness 1, roughness about 0.38) with a soft reflection environment;
- one key light raking from the upper left at 35° casting soft shadows onto the wall, plus a low fill;
- slim standoff cylinders behind each piece, and small fixing points on the wall. These are hidden until the explode begins.

**Timeline**, where *p* is scroll progress through the section (0–1), eased and smoothed:

| p | Action |
|---|---|
| 0.00–0.15 | Assembled logo, front-on. A champagne laser line sweeps the 35° kerf from lower left to upper right and the gap glows briefly. The headline fades out from 0.08. |
| 0.15–0.55 | Pieces separate: the two Arabic pieces move apart perpendicular to the kerf, the dot rises, the Latin letters stagger apart. All lift off the wall to an exaggerated standoff depth, standoffs and fixing points appear, and the camera turns to a three-quarter view (about 28° yaw, 8° down). |
| 0.55–0.80 | Hold, exploded, with a slow drift. Captions arrive one at a time: **قطعٌ واحد** / *One cut.* (0.55–0.63) · **مرفوعٌ عن الجدار** / *Lifted off the wall.* (0.63–0.71) · **مثبّتٌ ليبقى** / *Fixed to stay.* (0.71–0.80). |
| 0.80–1.00 | Pieces return and lock together, the camera returns front-on and the stage unpins into §4.3. |

**Rendering discipline:** render only when *p* or the drift changes; pause when the stage is off screen; cap the device pixel ratio at 1.75 (1.25 on phones); one shadow map of at most 2048 px.

**Still fallback** is the default markup and is upgraded by script. It is used when WebGL is unavailable, when the visitor prefers reduced motion, when data-saver is on, or on low-memory devices. It shows the assembled lockup on the petrol wall with the headline and the three captions as static text, with no pinning.

## 6. Visual system

**Colour tokens:**

| Token | Value | Use |
|---|---|---|
| `--night` | `#0F2427` | stage, dark sections |
| `--petrol` | `#1F454A` | secondary dark surface |
| `--ivory` | `#F4EFE6` | light sections |
| `--sand` | `#E9E1D2` | alternate light sections |
| `--ink` | `#161616` | text on light |
| `--taupe` | `#5C5650` | secondary text on light |
| `--mist` | `#C9CFC9` | secondary text on dark |
| `--champagne` | `#B9A06A` | hairlines, laser, small labels |

Every text and background pair must reach a 4.5:1 contrast ratio.

**Type:**

- Arabic display: Amiri. English display: Fraunces Light, with italics for emphasis.
- Body: Cairo for Arabic, Outfit for English.
- Labels: Outfit 500 in widely spaced capitals, Cairo 500 in Arabic.
- Fonts come from Google Fonts with swap loading.

**Layout:** content up to 1280 px wide; side gutters `clamp(16px, 4vw, 48px)`; logical CSS properties throughout so one stylesheet serves both directions.

**Motif:** the 35° kerf. Section dividers are single 35° champagne hairlines; buttons show a 35° sheen on hover.

**Motion:** reveals fade in and rise 12 px over 900 ms using `cubic-bezier(.2,.7,.1,1)`. Nothing bounces. Everything stops under reduced motion.

**Imagery:** rendered SVG scenes (proof sheet, night) inside frames sized for future photographs of the reference piece.

## 7. Architecture

```
/                      generated index.html (Arabic) + robots.txt, sitemap.xml
/en/index.html         generated English page
/assets/css/site.css
/assets/js/site.js     header state, reveals, footer year
/assets/js/stage.js    3D stage (ES module)
/assets/data/slice.json  locked Slice outlines (from the canvas)
/assets/img/           logo SVGs, favicons, share image
/src/template.html     one template with {{key}} slots
/src/content/ar.json   Arabic copy
/src/content/en.json   English copy
/src/site.json         site URL, WhatsApp number, Instagram handle
/build.py              Python 3 standard library only; writes the pages, sitemap and robots
/docs/superpowers/specs/  this spec
```

**three.js:**

- Loaded through an import map from jsDelivr, pinned to one version, with its SVGLoader (outline to shape) and RoomEnvironment (reflections) add-ons.
- No other runtime dependencies.

**Scroll driver:**

- Reads the stage section's position on scroll and resize, and computes *p*.
- A requestAnimationFrame loop eases toward it and renders only on change.

**Language:**

- `index.html` is `lang="ar" dir="rtl"`; `en/index.html` is `lang="en" dir="ltr"`.
- They are linked with `hreflang` alternates, and `x-default` points to Arabic.
- The language switch is a plain link between the two.

## 8. Al Taher part and search

**Footer disclosure:**

- A native `<details>` element whose summary is the small maker's mark and **من يصنع حفر؟** / *Who makes Hafr?*
- It opens to: *Every Hafr piece is cut and finished in the workshops of Al Taher Group: metalwork, coating, aluminium, glass and fit-out in the UAE since 1984.* Then a link to `https://altaherdesign.ae`.
- This text describes Al Taher, not Hafr's materials.

**Fine print:** **حفر — من مجموعة الطاهر** / *Hafr, an Al Taher Group line*, also linked.

**Link rules:**

- Both links are in the generated HTML of both pages, are followed links (no `nofollow`), open in a new tab with `rel="noopener"`, and are never hidden with CSS or added by script.
- Discreet is fine; invisible would breach search-engine spam rules.

**Structured data:** JSON-LD `Organization` for Hafr (alternate name حفر, area served AE) with `parentOrganization` Al Taher Group (`url: https://altaherdesign.ae`, founding year 1984).

**Search basics:**

- A title and description for each language, plus Open Graph tags.
- A 1200×630 share image of the assembled logo on petrol, plus favicons.
- `build.py` generates the sitemap and robots.txt from `site.json`.

## 9. Placeholders

These are held in `src/site.json` and shown visibly as `[[…]]` only in development builds:

- the site URL (pending the domain transfer);
- the WhatsApp number;
- the Instagram handle.

A production build refuses to run while any of them is still a placeholder.

## 10. Verification

1. Screenshots of both pages at 1440 px and 390 px widths; the stage at *p* = 0, 0.15, 0.35, 0.55, 0.80 and 1.
2. The still fallback forced by reduced motion and by disabling WebGL.
3. Frame times while scrolling the stage, measured in the browser; page weight excluding three.js under 60 KB of HTML, CSS and JavaScript.
4. A script check that the altaherdesign.ae link is present, followed and visible-on-open in both generated pages; the WhatsApp links are well formed.
5. A contrast check of every token pairing in use.
6. Independent reviews for brand fidelity, accessibility and right-to-left handling, and performance.

## 11. Out of scope

E-commerce, prices, contact forms or a backend, a CMS, a blog, analytics and cookie banners (to be added when the domain is live and the owner chooses a tool), and real photography (to be dropped into the frames from the reference-piece shoot).
