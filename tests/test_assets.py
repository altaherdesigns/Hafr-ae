"""Every asset the pages reference exists, and the deploy workflow guards the release."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


class AssetTests(unittest.TestCase):
    def test_template_assets_exist(self):
        refs = set(re.findall(r'\{\{base\}\}(assets/[^"\s]+)', read('src', 'template.html')))
        self.assertTrue(refs)
        for ref in sorted(refs):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, *ref.split('/'))), ref)

    def test_structured_data_and_share_images_exist(self):
        for ref in ('assets/img/hafr-logo.png', 'assets/img/og-image.png'):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, *ref.split('/'))), ref)

    def test_share_image_is_1200_by_630(self):
        with open(os.path.join(ROOT, 'assets', 'img', 'og-image.png'), 'rb') as fh:
            head = fh.read(24)
        self.assertEqual(head[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual((int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')), (1200, 630))

    def test_workflow_tests_builds_and_publishes_public_only(self):
        wf = read('.github', 'workflows', 'pages.yml')
        for needle in ('python -m unittest discover -s tests', 'node --test "tests/js/*.test.mjs"',
                       'python build.py --production', 'actions/upload-pages-artifact', 'path: public',
                       'actions/deploy-pages', 'pages: write', 'id-token: write'):
            self.assertIn(needle, wf)

    def test_readme_has_no_research(self):
        readme = read('README.md')
        self.assertIn('python build.py --production', readme)
        self.assertIn('D:\\Hafr', readme)
        for word in ('AED', 'competitor', 'margin'):
            self.assertNotIn(word, readme)


if __name__ == '__main__':
    unittest.main()
