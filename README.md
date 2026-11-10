# HTML 개별 페이지 배포

`public/`에 HTML을 넣으면 기존 파일과 함께 배포합니다. 공개 메인 페이지에는 HTML 목록을 만들지 않습니다.

## 실행하고 링크 확인하기

1. **Actions → Publish HTML pages → Run workflow**를 엽니다.
2. `page` 선택 메뉴에서 HTML 파일 또는 **전체 페이지**를 고릅니다.
3. **Run workflow**를 누릅니다.
4. 실행 이름을 클릭하고 **Summary** 화면에서 **HTML 페이지 바로가기**를 확인합니다.

선택한 파일은 바로가기가 맨 위에 표시됩니다. 기존 페이지가 사라지지 않도록 모든 HTML은 함께 배포하며, 전체 목록도 Summary에 나옵니다. 업로드에 따른 자동 실행은 전체 목록을 보여 줍니다.

| 원본 | 새 바로가기 | 기존 주소 |
| --- | --- | --- |
| public/test1.html | https://kdh2110.github.io/html-deploy/test1/ | /html-deploy/test1.html도 유지 |
| public/topic/index.html | https://kdh2110.github.io/html-deploy/topic/ | /html-deploy/topic/index.html도 유지 |

바로가기의 표시 이름과 주소에는 `.html`이 없습니다. GitHub Pages의 디렉터리 주소라 마지막 `/`는 붙습니다. 원본 파일 이름을 바꿀 필요는 없습니다. 기존 루트 `index.html`은 메인 주소 `/html-deploy/`로 연결됩니다.

## 새 HTML을 선택 메뉴에 자동으로 추가하기 (한 번 설정)

GitHub의 Run workflow 선택 항목은 YAML에 고정되어 있습니다. 이 프로젝트는 HTML이 바뀌면 그 목록을 다시 계산해 YAML의 선택 항목만 갱신합니다. 워크플로 파일을 수정하려면 기본 GITHUB_TOKEN 외에 Workflows 쓰기 권한이 필요합니다.

1. GitHub 계정 Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token을 엽니다.
2. Resource owner는 저장소 소유자, Repository access는 **Only select repositories → html-deploy**만 선택합니다.
3. Repository permissions에서 **Contents: Read and write**, **Workflows: Read and write**를 지정하고 만료일을 정해 발급합니다.
4. 저장소 **Settings → Secrets and variables → Actions → New repository secret**에서 이름을 **MENU_SYNC_TOKEN**, 값은 발급한 토큰으로 저장합니다. 토큰은 채팅이나 코드에 넣지 않습니다.
5. **Publish HTML pages**를 한 번 실행합니다. `sync-menu` 작업이 성공하면 Actions 화면을 새로고침합니다.

이후 public/에 HTML을 추가·삭제하면 메뉴도 자동 갱신됩니다. 갱신 커밋으로 실행이 한 번 더 생길 수 있으며, 목록이 같으면 추가 커밋을 만들지 않습니다. 토큰 만료·권한 부족·브랜치 보호 규칙으로 갱신이 막히면 sync-menu 결과에 표시됩니다. 페이지 배포 작업은 별도로 진행됩니다.

토큰이 없으면 자동 메뉴 갱신은 꺼진 상태입니다. 현재 등록된 선택 항목은 사용할 수 있고, 새 HTML도 배포 및 결과의 전체 목록에는 포함됩니다. 아직 메뉴에 없는 파일은 **전체 페이지**로 실행해서 결과 링크를 확인할 수 있습니다.

### 토큰 없이 수동 갱신

`.github/workflows/publish-html.yml`의 `BEGIN HTML CHOICES`와 `END HTML CHOICES` 사이에 `public/` 기준 상대 파일명을 추가하고 커밋합니다.

```yaml
          - "전체 페이지"
          - "test1.html"
          - "new-page.html"
```

로컬에서는 `python3 scripts/sync_choices.py` 실행 후 변경된 YAML을 커밋해도 됩니다.

## 파일과 주소 유지

- 같은 이름을 덮어쓰면 내용이 교체됩니다. 다른 결과를 추가하려면 새 파일명을 사용하세요.
- HTML이 참조하는 JSON, CSS, 이미지 등도 public/에 함께 넣습니다.
- 깨끗한 주소용 HTML에는 원래 파일 위치를 기준으로 하는 `<base>`를 추가해 일반적인 상대 경로의 이미지·CSS·fetch 요청을 유지합니다. 원본 파일은 그대로 보관합니다. `location.pathname`으로 데이터를 계산하는 스크립트나 기존 상대 링크·페이지 내 앵커는 별도 조정이 필요할 수 있으며, 기존 `.html` 주소로 이동할 수도 있습니다.
- `a.html`과 `a/index.html`처럼 새 주소가 겹치면 파일을 덮어쓰지 않고 빌드를 중단합니다.
- 사이트 용량 제한에는 기존 HTML과 새 주소용 복사본이 모두 포함됩니다. HTML은 UTF-8을 사용하세요.
- 저장소가 공개이므로 다른 사람도 저장소 파일과 **Actions 결과의 목록**을 볼 수 있습니다. 공개 사이트의 목록을 없애는 기능이며 접근 권한 제한은 아닙니다.
- 기존 public/index.html이 있다면 그대로 유지합니다. 그 안에 수동으로 넣은 다른 페이지 링크는 자동 제거하지 않습니다.

## 개발 확인

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_pages.py build
```

`_site/`만 웹사이트로 게시합니다. 링크 목록 JSON은 별도 Actions artifact이며 웹사이트에는 포함하지 않습니다. Summary는 실제 배포 성공 후 반환된 주소를 사용합니다.
