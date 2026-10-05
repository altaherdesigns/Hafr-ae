import json
import unittest
from hafrbuild.pages import gate, jsonld, whatsapp_url, sitemap, robots

SITE = {"siteUrl": "https://hafr.ae", "whatsapp": "971501234567", "instagram": None}


class PageTests(unittest.TestCase):
    def content(self):
        return {"built": {"rows": [{"status": "verified", "fail": "a", "build": "b"},
                                   {"status": "pending", "fail": "c", "build": "d"}], "fallback": "f"},
                "kit": {"status": "pending", "items": ["x"], "fallback": "k"},
                "dark": {"status": "verified", "lighting": "l"}}

    def test_production_omits_pending(self):
        c, omitted = gate(self.content(), production=True)
        self.assertEqual(len(c["built"]["rows"]), 1)
        self.assertEqual(c["kit"]["items"], [])
        self.assertIn("built.rows[1]", omitted)
        self.assertIn("kit.items", omitted)

    def test_dev_marks_pending(self):
        c, _ = gate(self.content(), production=False)
        self.assertTrue(c["built"]["rows"][1]["pending"])
        self.assertEqual(len(c["kit"]["items"]), 1)

    def test_jsonld_shape(self):
        d = json.loads(jsonld(SITE))
        self.assertEqual(d["foundingDate"], "2026")
        self.assertEqual(d["parentOrganization"]["url"], "https://altaherdesign.ae")
        self.assertNotIn("foundingDate", d["parentOrganization"])
        self.assertNotIn("sameAs", d)
        self.assertNotIn("</", jsonld({**SITE, "instagram": "hafr.ae"}).replace("<\\/", ""))

    def test_whatsapp(self):
        self.assertEqual(whatsapp_url("971501234567", "مرحبا"),
                         "https://wa.me/971501234567?text=%D9%85%D8%B1%D8%AD%D8%A8%D8%A7")
        self.assertEqual(whatsapp_url(None, "x"), "#start")

    def test_sitemap_and_robots(self):
        s = sitemap(SITE)
        self.assertIn("<loc>https://hafr.ae/</loc>", s)
        self.assertIn("<loc>https://hafr.ae/en/</loc>", s)
        self.assertNotIn("index.html", s)
        self.assertIn("Sitemap: https://hafr.ae/sitemap.xml", robots(SITE, True))
        self.assertIn("Disallow: /", robots(SITE, False))


if __name__ == '__main__':
    unittest.main()
