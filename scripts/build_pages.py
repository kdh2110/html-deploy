"""Publish the complete public/ tree, preserving each relative URL and file byte.

Standard library only. Run from the repository root with Python 3.10+.
The repository is the source of truth, not a previous deployment artifact.
"""

from pathlib import Path
import shutil


def build(source: Path, output: Path) -> int:
    source, output = source.resolve(), output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("Source and output must be separate directories.")
    if not source.is_dir():
        raise ValueError("public/ 폴더를 만들고 HTML 파일을 넣어 주세요.")
    entries = list(source.rglob("*"))
    if any(p.is_symlink() for p in entries):
        raise ValueError("public/에는 심볼릭 링크를 넣을 수 없습니다.")
    pages = sorted(
        (p.relative_to(source) for p in entries
         if p.is_file() and p.suffix.lower() in {".html", ".htm"}),
        key=lambda p: p.as_posix().casefold(),
    )
    if not pages:
        raise ValueError("배포 중단: public/에 HTML 파일이 한 개 이상 필요합니다.")
    total = sum(p.stat().st_size for p in entries if p.is_file())
    if total > 1_000_000_000:
        raise ValueError("배포 중단: 사이트 크기가 1 GB를 초과합니다.")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output)
    (output / ".gitkeep").unlink(missing_ok=True)
    if not (output / "index.html").exists():
        (output / "index.html").write_text(
            '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow">'
            '<title>페이지 안내</title><style>'
            'body{font:17px/1.7 system-ui,sans-serif;max-width:720px;margin:80px auto;'
            'padding:0 24px;color:#172337;background:#f6f8fc}'
            '</style></head><body><h1>페이지 안내</h1>'
            '<p>전달받은 개별 링크로 접속해 주세요.</p></body></html>',
            encoding="utf-8"
        )
    print(f"Built {len(pages)} HTML file(s). All public/ assets included.")
    return len(pages)


if __name__ == "__main__":
    build(Path("public"), Path("_site"))
