"""Build every saved page; add clean URLs and an Actions-only link manifest."""
import argparse
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
from urllib.parse import quote, urlsplit

ALL_PAGES = "전체 페이지"
NOTICE = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<meta name="robots" content="noindex,nofollow"><title>페이지 안내</title>'
          '</head><body><p>전달받은 개별 링크로 접속해 주세요.</p></body></html>')


def html_files(source):
    return sorted((p.relative_to(source) for p in source.rglob('*')
                   if p.is_file() and p.suffix.lower() in {'.html', '.htm'}),
                  key=lambda p: p.as_posix().casefold())


class HeadParser(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.lines = text.splitlines(keepends=True)
        self.head = self.html = self.doctype = None
        self.base = None
        self.template_depth = 0
        self.feed(text)

    def absolute_offset(self):
        line, column = self.getpos()
        return sum(len(s) for s in self.lines[:line - 1]) + column

    def handle_starttag(self, tag, attrs):
        if tag == 'template':
            self.template_depth += 1
        if self.template_depth:
            return
        end = self.absolute_offset() + len(self.get_starttag_text())
        if tag == 'head' and self.head is None:
            self.head = end
        if tag == 'html' and self.html is None:
            self.html = end
        if tag == 'base' and self.base is None:
            attrs = dict(attrs)
            if attrs.get('href') is not None:
                self.base = attrs['href']

    def handle_endtag(self, tag):
        if tag == 'template':
            self.template_depth = max(0, self.template_depth - 1)

    def handle_decl(self, decl):
        if decl.lower().startswith('doctype') and self.doctype is None:
            self.doctype = self.absolute_offset() + len(decl) + 3


def clean_copy(text, original_name):
    """Keep relative CSS, images and fetch() requests at the original location."""
    parser = HeadParser(text)
    old_document = '../' + quote(original_name, safe='')
    href = old_document
    if parser.base is not None:
        existing = parser.base.strip()
        if existing.startswith('/') or urlsplit(existing).scheme:
            href = existing
        elif not existing or existing.startswith(('?', '#')):
            href = old_document + existing
        else:
            href = '../' + existing
    base = '<base href="' + escape(href, quote=True) + '">'
    if parser.head is not None:
        pos, insert = parser.head, base
    else:
        pos = parser.html if parser.html is not None else (parser.doctype or 0)
        insert = '<head>' + base + '</head>'
    return text[:pos] + insert + text[pos:]


def build(source, output, selected=ALL_PAGES):
    source, output = source.resolve(), output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Source and output must be separate directories.')
    if not source.is_dir():
        raise ValueError('public/ 폴더가 없습니다.')
    entries = list(source.rglob('*'))
    if any(p.is_symlink() for p in entries):
        raise ValueError('public/에는 심볼릭 링크를 넣을 수 없습니다.')
    pages = html_files(source)
    if not pages:
        raise ValueError('public/에 HTML 파일을 한 개 이상 넣어 주세요.')
    if selected != ALL_PAGES and selected not in [p.as_posix() for p in pages]:
        raise ValueError('선택한 파일이 없습니다. 메뉴를 갱신하거나 전체 페이지를 선택하세요.')
    aliases = {}
    manifest = []
    for rel in pages:
        if rel.name == 'index.html':
            route = '' if rel.parent == Path('.') else rel.parent.as_posix() + '/'
        else:
            target = rel.with_suffix('') / 'index.html'
            if (source / target).exists() or target in aliases:
                raise ValueError(f'주소 충돌: {rel} → {target}. 파일명이나 폴더명을 바꿔 주세요.')
            if any((source / parent).is_file() for parent in target.parents):
                raise ValueError(f'주소 경로에 같은 이름의 파일이 있습니다: {target}')
            text = (source / rel).read_text(encoding='utf-8-sig')
            aliases[target] = clean_copy(text, rel.name)
            route = target.parent.as_posix() + '/'
        manifest.append({'file': rel.as_posix(), 'label': rel.with_suffix('').as_posix(),
                         'route': route})
    size = sum(p.stat().st_size for p in entries if p.is_file())
    size += sum(len(s.encode('utf-8')) for s in aliases.values()) + len(NOTICE.encode('utf-8'))
    if size > 1_000_000_000:
        raise ValueError('배포 결과가 1 GB를 초과합니다.')
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output)
    (output / '.gitkeep').unlink(missing_ok=True)
    for rel, text in aliases.items():
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    if not (output / 'index.html').exists():
        (output / 'index.html').write_text(NOTICE, encoding='utf-8')
    return manifest


def md_label(value):
    # Escape Markdown syntax and HTML, including table separators and newlines.
    return ''.join(f'&#{ord(c)};' if c in '\\`*_{}[]()<>#+-.!|\r\n&' else c for c in value)


def summary(pages, base_url, selected):
    if not base_url.startswith(('https://', 'http://')):
        raise ValueError('배포 결과 URL이 없습니다.')
    def link(page):
        url = base_url.rstrip('/') + '/' + quote(page['route'], safe='/')
        return f"[{md_label(page['label'])}]({url})"
    lines = ['## HTML 페이지 바로가기', '', '배포가 완료되었습니다. 파일명을 누르면 페이지가 열립니다.', '']
    if selected != ALL_PAGES:
        page = next(p for p in pages if p['file'] == selected)
        lines += ['### 선택한 페이지', '', link(page), '']
    lines += [f'### 전체 HTML 목록 ({len(pages)}개)', '', '| 파일명 | 바로가기 |', '| --- | --- |']
    lines += [f"| {md_label(p['file'])} | {link(p)} |" for p in pages]
    lines += ['', '선택은 바로가기 강조용이며, 기존 페이지 유지를 위해 모든 HTML을 함께 배포합니다.',
              '이 목록은 Actions 실행 결과에만 표시됩니다. 공개 저장소에서는 다른 사람도 Actions 결과를 볼 수 있습니다.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs='?', default='build', choices=['build', 'summary'])
    args = parser.parse_args()
    selected = os.environ.get('SELECTED_PAGE') or ALL_PAGES
    manifest_path = Path('page-metadata/pages.json')
    if args.command == 'build':
        pages = build(Path('public'), Path('_site'), selected)
        manifest_path.parent.mkdir(exist_ok=True)
        manifest_path.write_text(json.dumps(pages, ensure_ascii=False), encoding='utf-8')
        print(f'Prepared {len(pages)} HTML page(s); original URLs also preserved.')
    else:
        pages = json.loads(manifest_path.read_text(encoding='utf-8'))
        report = summary(pages, os.environ['PAGE_URL'], selected)
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(report)
