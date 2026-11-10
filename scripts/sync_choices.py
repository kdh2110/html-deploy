"""Refresh native Run workflow choices. Remote mode needs Workflows write access."""
import argparse
import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from build_pages import DIRECT_PATH, html_files

WORKFLOW = '.github/workflows/publish-html.yml'
START = '          # BEGIN HTML CHOICES\n'
END = '          # END HTML CHOICES'


def render(text, paths):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('워크플로의 HTML CHOICES 표시를 확인하세요.')
    choices = [DIRECT_PATH] + sorted({'public/' + p for p in paths}, key=str.casefold)
    lines = ''.join('          - ' + json.dumps(p, ensure_ascii=False) + '\n' for p in choices)
    before, tail = text.split(START)
    _, after = tail.split(END)
    return before + START + lines + END + after


def note(text):
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write('## 실행 전 선택 메뉴\n\n' + text + '\n')


def remote():
    token = os.environ.get('MENU_SYNC_TOKEN', '')
    if not token:
        note('자동 메뉴 갱신은 아직 꺼져 있습니다. MENU_SYNC_TOKEN을 설정하면 새 HTML을 자동 반영합니다. '
             '목록에 없는 파일은 Publish HTML page의 input_path에 경로를 직접 입력하면 됩니다.')
        return
    repo = os.environ['GITHUB_REPOSITORY']
    def api(path, payload=None):
        req = Request('https://api.github.com/repos/' + repo + '/' + path,
                      data=json.dumps(payload).encode() if payload else None,
                      method='PUT' if payload else 'GET',
                      headers={'Authorization': 'Bearer ' + token,
                               'Accept': 'application/vnd.github+json',
                               'Content-Type': 'application/json',
                               'X-GitHub-Api-Version': '2022-11-28'})
        with urlopen(req, timeout=30) as r:
            return json.load(r)
    try:
        branch = api('')['default_branch']
        for attempt in range(3):
            head = api('git/ref/heads/' + quote(branch, safe=''))['object']['sha']
            tree = api('git/trees/' + head + '?recursive=1')
            if tree.get('truncated'):
                raise ValueError('저장소 파일 목록이 잘렸습니다. 수동 메뉴 갱신이 필요합니다.')
            paths = [x['path'][7:] for x in tree['tree'] if x['type'] == 'blob'
                     and x['path'].startswith('public/')
                     and Path(x['path']).suffix.lower() in {'.html', '.htm'}]
            current = api('contents/' + WORKFLOW + '?ref=' + head)
            old = base64.b64decode(current['content']).decode('utf-8')
            new = render(old, paths)
            if new == old:
                note('선택 메뉴가 최신 HTML 목록과 일치합니다.')
                return
            if api('git/ref/heads/' + quote(branch, safe=''))['object']['sha'] != head:
                continue
            try:
                api('contents/' + WORKFLOW, {'message': 'Refresh HTML selection menu',
                    'branch': branch, 'sha': current['sha'],
                    'content': base64.b64encode(new.encode()).decode()})
                note('선택 메뉴를 갱신했습니다. Actions 화면을 새로고침하면 새 파일이 표시됩니다.')
                return
            except HTTPError as e:
                if e.code != 409:
                    raise
        raise ValueError('동시에 파일이 변경되었습니다. 워크플로를 다시 실행해 주세요.')
    except HTTPError as e:
        # Do not print request headers, tokens, or response bodies.
        note(f'메뉴 갱신 실패 (HTTP {e.code}). 토큰의 Contents/Workflows 쓰기 권한과 저장소 브랜치 정책을 확인하세요.')
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--remote', action='store_true')
    args = p.parse_args()
    if args.remote:
        remote()
    else:
        path = Path(WORKFLOW)
        path.write_text(render(path.read_text(encoding='utf-8'),
                               [p.as_posix() for p in html_files(Path('public'))]), encoding='utf-8')
