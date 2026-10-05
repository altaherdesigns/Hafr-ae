# hafr.ae

Source for the Hafr landing page: Arabic at `/`, English at `/en/`. It opens with a 3D exploded assembly of the logo, which falls back to a still image wherever 3D isn't suitable.

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

## Deploy

Every push to `main` runs `.github/workflows/pages.yml`. It runs both test suites, does a production build and publishes `public/` to GitHub Pages. Nothing outside `public/` is served.

To set it up:

- In *Settings → Pages*, set the source to **GitHub Actions** and the custom domain to `hafr.ae`.
- Tick *Enforce HTTPS* once the certificate is issued.

The DNS records are listed in the site spec in `D:\Hafr\docs\specs`.

## Images

The images in `assets/img/` are generated once by `D:\Hafr\tools\make_site_images.py` from the locked logo geometry. They are committed here, so the build itself never generates images.
