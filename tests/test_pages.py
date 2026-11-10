import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import urljoin
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_pages import ALL_PAGES, HeadParser, build, clean_copy, summary
from sync_choices import render, START, END


class PagesTests(unittest.TestCase):
    def test_addition_preserves_originals_and_generates_clean_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp)/'public', Path(tmp)/'_site'
            src.mkdir()
            old = '<!doctype html><html><head><title>A</title></head><body>A</body></html>'
            (src/'a.html').write_text(old)
            build(src, out)
            (src/'새 문서.html').write_text('<h1>B</h1>')
            (src/'data.json').write_text('{"value":3}')
            pages = build(src, out, 'a.html')
            self.assertEqual((out/'a.html').read_text(), old)
            self.assertEqual((out/'data.json').read_text(), '{"value":3}')
            self.assertTrue((out/'a/index.html').exists())
            self.assertTrue((out/'새 문서/index.html').exists())
            self.assertNotIn('<a ', (out/'index.html').read_text())
            self.assertFalse((out/'pages.json').exists())
            report = summary(pages, 'https://example.org/repo/', 'a.html')
            self.assertIn('[a](https://example.org/repo/a/)', report)
            self.assertIn('/%EC%83%88%20%EB%AC%B8%EC%84%9C/', report)
            self.assertIn('### 선택한 페이지', report)

    def test_relative_assets_resolve_to_original_directory(self):
        text = '<!doctype html><html><head></head><body><img src="image.png"></body></html>'
        page = clean_copy(text, 'a.html')
        base = HeadParser(page).base
        document_base = urljoin('https://example.org/repo/nested/a/', base)
        self.assertEqual(urljoin(document_base, 'data.json'), 'https://example.org/repo/nested/data.json')
        existing = clean_copy('<head><base href="assets/"></head>', 'a.html')
        document_base = urljoin('https://example.org/repo/a/', HeadParser(existing).base)
        self.assertEqual(urljoin(document_base, 'x.css'), 'https://example.org/repo/assets/x.css')

    def test_script_and_comment_head_text_is_not_modified(self):
        html = '<!-- <head> --><html><head><script>const s="<head>";</script></head></html>'
        result = clean_copy(html, 'test.html')
        self.assertIn('<html><head><base href="../test.html">', result)
        self.assertIn('const s="<head>"', result)

    def test_existing_index_preserved_and_collision_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp)/'public', Path(tmp)/'_site'
            (src/'a').mkdir(parents=True)
            (src/'index.html').write_text('home')
            (src/'a/index.html').write_text('existing')
            pages = build(src, out)
            self.assertEqual((out/'index.html').read_text(), 'home')
            self.assertEqual({p['route'] for p in pages}, {'', 'a/'})
            (src/'a.html').write_text('collision')
            with self.assertRaisesRegex(ValueError, '주소 충돌'):
                build(src, out)
            self.assertEqual((out/'a/index.html').read_text(), 'existing')

    def test_missing_selection_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp)/'public', Path(tmp)/'_site'; src.mkdir()
            (src/'a.html').write_text('a')
            with self.assertRaisesRegex(ValueError, '선택한 파일'):
                build(src, out, 'missing.html')
            (src/'link.html').symlink_to(src/'a.html')
            with self.assertRaisesRegex(ValueError, '심볼릭'):
                build(src, out)

    def test_menu_refresh_add_delete_and_escaping(self):
        template = 'prefix\n' + START + '          - "old.html"\n' + END + '\nsuffix\n'
        paths = ['한글.html', 'a"b.html', 'x\ny.html']
        result = render(template, paths)
        self.assertNotIn('old.html', result)
        choices = [json.loads(line.strip()[2:]) for line in result.splitlines() if line.strip().startswith('- ')]
        self.assertEqual(choices, [ALL_PAGES] + sorted(paths, key=str.casefold))
        self.assertEqual(render(result, paths), result)
        self.assertTrue(result.endswith('\nsuffix\n'))

    def test_summary_escapes_filename_markdown(self):
        report = summary([{'file':'[x]|<b>.html','label':'[x]|<b>','route':'[x]|<b>/'}],
                         'https://example.org/', ALL_PAGES)
        self.assertNotIn('<b>', report)
        self.assertIn('%5Bx%5D%7C%3Cb%3E/', report)


if __name__ == '__main__':
    unittest.main()
