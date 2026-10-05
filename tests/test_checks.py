import unittest
from hafrbuild.checks import validate_site, find_banned

BANNED = {"latin": ["stainless", "aluminium", "316", "price", "luxury", "name plate"],
          "arabic": ["ستانلس", "فاخر", "لوحة اسم"],
          "patterns": [r"\d+\s*(year|years|سنة|سنوات|عام|عاماً)"]}


class CheckTests(unittest.TestCase):
    def test_site_valid(self):
        self.assertEqual(validate_site({"siteUrl": "https://hafr.ae", "whatsapp": "971501234567", "instagram": None}, True), [])

    def test_site_production_needs_whatsapp(self):
        errs = validate_site({"siteUrl": "https://hafr.ae", "whatsapp": None, "instagram": None}, True)
        self.assertTrue(any("whatsapp" in e for e in errs))

    def test_site_dev_allows_null(self):
        self.assertEqual(validate_site({"siteUrl": "https://hafr.ae", "whatsapp": None, "instagram": None}, False), [])

    def test_site_bad_formats(self):
        errs = validate_site({"siteUrl": "https://hafr.ae/", "whatsapp": "+971 50", "instagram": "bad handle!"}, True)
        self.assertEqual(len(errs), 3)

    def test_banned_in_text(self):
        self.assertTrue(find_banned("<p>Brushed stainless face</p>", BANNED))

    def test_banned_in_attribute_and_jsonld(self):
        self.assertTrue(find_banned('<img alt="luxury sign">', BANNED))
        self.assertTrue(find_banned('<script type="application/ld+json">{"d":"316 grade"}</script>', BANNED))

    def test_ignores_other_scripts_and_styles(self):
        self.assertEqual(find_banned('<script>var price=1</script><style>.price{}</style><p>ok</p>', BANNED), [])

    def test_word_boundaries(self):
        self.assertEqual(find_banned('<p>priceless? no: 3160 and stainlessly</p>',
                                     {"latin": ["price", "316"], "arabic": [], "patterns": []}), [])

    def test_arabic_and_duration(self):
        self.assertTrue(find_banned('<p>تصميم فاخر</p>', BANNED))
        self.assertTrue(find_banned('<p>يدوم 20 سنة</p>', BANNED))
        self.assertEqual(find_banned('<p>© 2026</p>', BANNED), [])


if __name__ == '__main__':
    unittest.main()
