import unittest
from hafrbuild.render import render, RenderError


class RenderTests(unittest.TestCase):
    def r(self, t, ctx, dev=False, partials=None):
        return render(t, ctx, partials=partials or {}, dev=dev)

    def test_escapes_text(self):
        self.assertEqual(self.r('<p>{{a}}</p>', {'a': '<b>&'}), '<p>&lt;b&gt;&amp;</p>')

    def test_attr_escapes_quotes(self):
        self.assertEqual(self.r('<i title="{{a|attr}}">', {'a': 'x"y'}), '<i title="x&quot;y">')

    def test_html_allowlist(self):
        self.assertEqual(self.r('{{a|html}}', {'a': 'one<br>two <em>x</em>'}), 'one<br>two <em>x</em>')
        with self.assertRaises(RenderError):
            self.r('{{a|html}}', {'a': '<script>x</script>'})

    def test_url_filter(self):
        self.assertEqual(self.r('{{a|url}}', {'a': 'مرحبا حفر'}),
                         '%D9%85%D8%B1%D8%AD%D8%A8%D8%A7%20%D8%AD%D9%81%D8%B1')

    def test_each_with_index(self):
        out = self.r('{{#each xs}}[{{@nn}}:{{.name}}]{{/each}}', {'xs': [{'name': 'a'}, {'name': 'b'}]})
        self.assertEqual(out, '[01:a][02:b]')

    def test_if(self):
        self.assertEqual(self.r('{{#if x}}yes{{/if}}', {'x': None}, dev=True), '')
        self.assertEqual(self.r('{{#if x}}yes{{/if}}', {'x': 'h'}), 'yes')

    def test_partial_uses_ctx(self):
        self.assertEqual(self.r('{{> p}}', {'a': 'z'}, partials={'p': '<b>{{a}}</b>'}), '<b>z</b>')

    def test_missing_key_raises(self):
        with self.assertRaisesRegex(RenderError, 'missing slot: a.b'):
            self.r('{{a.b}}', {'a': {}})

    def test_none_dev_placeholder_prod_raises(self):
        self.assertEqual(self.r('{{w}}', {'w': None}, dev=True), '[[w]]')
        with self.assertRaises(RenderError):
            self.r('{{w}}', {'w': None})


if __name__ == '__main__':
    unittest.main()
