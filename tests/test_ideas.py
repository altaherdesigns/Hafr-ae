"""The Ideas gallery: every image exists in every size, every picture has alt text,
and the gallery's structured data and image sitemap point at real files."""
import json
import os
import re
import shutil
import tempfile
import unittest

from test_build import read, run_build, site_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = json.loads(read(os.path.join(ROOT, 'src', 'ideas.json')))['images']


class IdeasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        out = os.path.join(cls.tmp, 'out')
        code, err = run_build(['--production', '--out', out, '--site', site_file(cls.tmp, '971501234567')])
        assert code == 0, err
        cls.pages = {'ar': read(os.path.join(out, 'index.html')), 'en': read(os.path.join(out, 'en', 'index.html'))}
        cls.sitemap = read(os.path.join(out, 'sitemap.xml'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_size_exists(self):
        for img in IMAGES:
            for name in [f"{img['slug']}-{w}.webp" for w in (640, 1024, 1408)] + [f"{img['slug']}-1024.jpg"]:
                self.assertTrue(os.path.isfile(os.path.join(ROOT, 'assets', 'img', 'ideas', name)), name)

    def test_captions_match_images(self):
        for lang in ('ar', 'en'):
            c = json.loads(read(os.path.join(ROOT, 'src', 'content', f'{lang}.json')))
            self.assertEqual(len(c['ideas']['items']), len(IMAGES), lang)
            for item in c['ideas']['items']:
                self.assertGreaterEqual(len(item['alt']), 40, item)
                self.assertLessEqual(len(item['alt']), 125, item)

    def test_every_picture_has_alt_and_size(self):
        for lang, page in self.pages.items():
            imgs = re.findall(r'<img [^>]*loading="lazy"[^>]*>', page)
            self.assertEqual(len(imgs), len(IMAGES), lang)
            for tag in imgs:
                self.assertRegex(tag, r'alt="[^"]{40,}"')
                self.assertRegex(tag, r'width="\d+" height="\d+"')

    def test_gallery_jsonld(self):
        for lang, page in self.pages.items():
            blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]
            gallery = [b for b in blocks if b.get('@type') == 'ImageGallery']
            self.assertEqual(len(gallery), 1, lang)
            media = gallery[0]['associatedMedia']
            self.assertEqual(len(media), len(IMAGES))
            for m in media:
                rel = m['contentUrl'].replace('https://hafr.ae/', '')
                self.assertTrue(os.path.isfile(os.path.join(ROOT, *rel.split('/'))), rel)
                self.assertTrue(m['caption'])

    def test_whatsapp_links_name_the_style(self):
        self.assertIn('wa.me/971501234567?text=', self.pages['en'])
        self.assertEqual(self.pages['en'].count('data-idea-ask'), len(IMAGES))

    def test_image_sitemap(self):
        self.assertIn('xmlns:image=', self.sitemap)
        for img in IMAGES:
            self.assertIn(f"/assets/img/ideas/{img['slug']}-1408.webp", self.sitemap)


if __name__ == '__main__':
    unittest.main()
