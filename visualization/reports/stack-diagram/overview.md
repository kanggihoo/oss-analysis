---
sha: "5af3b095fff7109c905c5284dc510dc06588bade"
created: 2026-11-10
updated: 2026-11-10
---

# stack-diagram Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/caru-ini/stack-diagram` (branch `main`, 커밋 날짜 2026-11-09)
- **작업트리 상태**: Clean (`../../artifacts/stack-diagram/repo-metadata.txt`, [repos.lock.tsv](../../repos.lock.tsv))
- **분석 목적**: **미정**(사용자가 정하면 [GUIDE.md](../../GUIDE.md)와 여기에 적는다). 지금은 "시각화 주제 폴더의 두 번째 대상으로 구조 파악"만 정해졌고, 같은 폴더의 archify와 비교할 수 있게 feature map을 굵게 나눴다.
- **라이선스**: MIT, `repos/stack-diagram/LICENSE`(Copyright 2026 caru-ini). `skills/stack-diagram/LICENSE`는 같은 MIT 본문에 "assets/fonts/는 이 라이선스 밖이고 SIL OFL 1.1"이라는 문단이 붙은 사본이다(`diff`로 확인). 폰트 라이선스는 `skills/stack-diagram/assets/fonts/OFL-Geist.txt`, `OFL-JetBrainsMono.txt`. 로고는 레포에 넣지 않고 실행 때 내려받는다(README "Licenses and trademarks").
- **분석 대상 제품**: 배포 단위가 둘이다. (1) 에이전트 스킬 `skills/stack-diagram/`(Python 스크립트 4개 + `SKILL.md` + 템플릿). `release.yml`이 `v*` 태그에서 이 폴더를 `stack-diagram.zip`으로 묶어 Release에 올린다. (2) 공개 갤러리 `site/`(TanStack Start, Cloudflare Workers, https://stacks.caru.moe). 갤러리는 `site.yml`이 `site/**` 변경 때 검사한다.
- **스펙 범위**: 승인 전 (권장안: 행 1~7, 이유는 아래 4절 요약과 [handoff.md](../../../handoff.md)) · 제외(권장안): 행 8~14 — 부속(갤러리 클라이언트와 `site/`)

---

## 2. 프로젝트 개요

사용자가 "Next.js와 Hono API를 Vercel에 올리고 Neon, Clerk, Stripe를 쓴다" 같은 문장으로 스택을 말하면, 에이전트가 공식 로고를 내려받아 그룹 박스와 직교 화살표가 있는 아키텍처 다이어그램을 만든다. 결과의 원본은 폰트와 로고를 data URI로 넣은 HTML 한 장이고, PNG(라이트·다크), React 컴포넌트, Claude artifact는 이 HTML에서 파생한다(`SKILL.md` 6단계). 스킬 자체에는 다이어그램을 그리는 엔진이 없다. 에이전트가 `template.html`을 복사해 좌표를 손으로 정하고, 스크립트는 로고 수집·inline·PNG 캡처·갤러리 업로드만 맡는다. 이 점이 archify(JSON 스키마, 렌더러, 검증 gate를 코드로 가진 구조)와 가장 크게 다르다.

### Feature map

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 콘텐츠 설계 규칙 | 기술 목록 → node, group, edge 3종(accent 실선=주 흐름, neutral 실선=내부, 점선=dev·deploy)을 에이전트가 정한다. 규칙만 있고 코드로 강제하는 곳은 없다. | `skills/stack-diagram/SKILL.md` 28~39행 | 없음 | 핵심 | `capabilities/content-design.md` · 미작성 | 코드 확인(규칙 문장). 에이전트가 따르는지는 추론 |
| 2 | 로고 수집: 브랜드 체인 | `fetch_icons.py <dir> spec...` → svgl, devicon, gilbarbara 순으로 시도해 `<name>.<ext>`와 `manifest.json`을 쓴다. `name=URL`, `lucide/`, 라이트·다크 쌍(`<name>_dark`), `white_fill` 휴리스틱을 포함한다. | `skills/stack-diagram/scripts/fetch_icons.py` `main`, `sources`, `svgl_lookup`, `white_fill` | 없음 | 핵심 | `capabilities/icon-fetch-brands.md` · 미작성 | 코드 확인(함수 전체 읽음). 외부 API 응답은 실행하지 않아 미확인 |
| 3 | 로고 수집: 벤더 공식 패키지 | `aws/`, `gcp/`, `azure/` spec이나 `aws`·`gcp-*`·`azure-*` slug → 벤더 공식 zip을 한 번 받아 메모리에서 이름을 찾는다. 별칭, 접두어 생략, 정확 일치만 허용하고 miss는 전체 이름 목록을 출력한다. 실패 시 서드파티로 fallback하지 않는다. | `fetch_icons.py` `aws_index`/`aws_sources`, `gcp_index`/`gcp_sources`, `azure_index`/`azure_sources`, `package_from_page`, 표 `AWS_ALIASES`·`GCP_PRODUCTS`·`AZURE_ALIASES` | 2 (출력 계약 `manifest.json`) | 핵심 | `capabilities/icon-fetch-vendors.md` · 미작성 | 코드 확인(index·sources). 별칭 표 내용(60~146행)은 미정독 |
| 4 | 레이아웃 규칙과 템플릿 | 에이전트가 `template.html`을 복사해 GROUPS·EDGES·NODES를 손으로 채운다. 노드 132×100, 간격, 그룹 패딩, edge anchoring(텍스트 관통 금지), 벤더별 group 클래스(`aws`·`gcp`·`azure`), 다크 테마 토큰이 규칙이다. | `skills/stack-diagram/references/geometry.md`, `assets/template.html`, `SKILL.md` 70~72행·59~64행 | 없음 | 핵심 | `capabilities/layout-template.md` · 미작성 | 코드 확인(geometry.md 전체, template 앞뒤). CSS 중간부는 미정독 |
| 5 | 빌드: 자산 inline | `build.py DRAFT ICONDIR OUT [--fonts DIR]` → `%%FONT_DISPLAY%%`, `%%FONT_JBM%%`, `%%ICON_<name>%%`을 base64 data URI로 치환하고 남은 `%%…%%`가 있으면 실패한다. | `skills/stack-diagram/scripts/build.py` `main` | 2·3(icons dir), 4(토큰 규약) | 핵심 | `capabilities/build-inline.md` · 미작성 | 코드 확인(51줄 전체) |
| 6 | PNG 렌더 | `render_png.py IN OUT [--selector --scale --full-page --single]` → Playwright Chromium으로 `.canvas`를 라이트·다크 두 장(`OUT.png`, `OUT-dark.png`)으로 캡처한다. 라운드 제거, 일본어 폰트 경고, 헤드리스 렌더 옵션을 포함한다. | `skills/stack-diagram/scripts/render_png.py` `main` | 4 (`.canvas`, `data-theme`) | 핵심 | `capabilities/png-render.md` · 미작성 | 코드 확인(98줄 전체). Playwright 실행은 하지 않음 |
| 7 | 전달 형식과 검증 절차 | HTML(기본), PNG, TSX(`references/tsx.md`), artifact를 요청별로 만든다. 렌더 후 눈으로 확인하는 체크리스트와 footer의 아이콘 출처 표기를 따른다. TSX 변환은 에이전트가 문서를 보고 직접 하며 스크립트가 없다. | `SKILL.md` 84~112행, `references/tsx.md` | 5, 6 | 핵심 | `capabilities/delivery-formats.md` · 미작성 | 코드 확인(문서). 시각 확인은 에이전트 절차라 추론 |
| 8 | 갤러리 공유 클라이언트 | `share.py submit LIGHT DARK --title --stack --name [--github] [--icons]`, `delete ID`, `list`. PNG·메타 검증 → `GET /api/challenge` → proof of work 풀이 → multipart `POST /api/stacks` → delete key를 `~/.config/stack-diagram/gallery.json`(0600)에 저장. 사용자 동의 두 번은 `SKILL.md` 7단계의 규칙이고 코드에는 없다. | `skills/stack-diagram/scripts/share.py` `submit`, `solve`, `call`, `delete` | 6(PNG), 2(manifest) | 부속 | `capabilities/gallery-client.md` · 미작성 | 코드 확인(217줄 전체). 서버 응답은 실행하지 않아 미확인 |
| 9 | 갤러리 제출 intake | `GET /api/challenge`와 `POST /api/stacks`가 값싼 검사부터 순서대로 한다: rate limit → submission mode(`closed`면 503) → Content-Length → proof of work → 일일 한도 → challenge 재사용 방지 → multipart·meta·PNG 크기 검사. | `site/src/features/submit/server/intake.ts` `intake`, `pow.ts`, `challenge.ts`, `meta.ts`, `png.ts` | 8의 제출 계약(C3) | 부속 | `capabilities/gallery-intake.md` · 미작성 | 코드 확인(`intake.ts` 전체). `pow.ts`·`meta.ts`·`png.ts` 본문은 미정독 |
| 10 | 갤러리 게시와 심사 | intake를 통과한 글을 WebP·JPEG preview로 인코딩, R2에 저장, 아이콘 저장, Workers AI로 diagram·abuse·spam·exposure 점수를 매겨 `published` 또는 `held`로 결정하고 Neon에 insert한다. 점수가 없으면(AI 실패) 항상 `held`다. 응답은 `{id, url, status, deleteKey}`. | `site/src/features/submit/server/submit.ts` `publish`, `moderation.ts` `classify`·`decide`, `icons.ts` `storeIcons` | 9 | 부속 | `capabilities/gallery-publish.md` · 미작성 | 코드 확인(`submit.ts` 전체, `decide`). `classify` 본문과 `icons.ts` 세부는 미정독 |
| 11 | 갤러리 읽기: 목록·상세·OG·파일 | `GET /api/stacks`(목록), `/`·`/s/$id`·`/share` 페이지, `/og/*` 이미지, `/files/$` 서빙(게시된 글만 공개, 소유자·관리자는 비공개 글도 봄). `server.ts`가 공유 파일과 로그인 없는 페이지를 cache한다. | `site/src/server.ts` `isCacheableRequest`, `features/gallery/server/list.ts` `handleList`, `features/submit/server/files.ts` `handleFile`, `features/og/server/og.ts` | 10 (DB 계약 C4) | 부속 | `capabilities/gallery-read.md` · 미작성 | 코드 확인(`server.ts` 앞부분, `files.ts`). 페이지 컴포넌트는 미탐색 |
| 12 | 갤러리 투표·신고 | `castVote`, `reportStack` server function. voter pass 쿠키(`sd_voter`, 7일), 투표자·네트워크별 일일 한도, 신고 누적 숨김 기준 상수 `HIDE_AT_REPORTS = 3`, 두 번 기각된 신고자는 무시. | `site/src/features/stack/server/vote.ts` `castVote`, `report.ts` `reportStack`, `rules.ts`, `voter-pass.ts` | 10 (C4) | 부속 | `capabilities/gallery-vote-report.md` · 미작성 | 추론(`rules.ts` 상수와 export 이름만 읽음) |
| 13 | 갤러리 관리자 | `/admin` 화면, 대기열(held 또는 신고 있음), `moderate`, `setMode`(`open`·`review`·`closed`), 관리자는 `ADMIN_GITHUB_IDS`로 판별. | `site/src/features/admin/server/moderate.ts`, `queue.ts`, `overview.ts`, `guard.ts` | 10, 12 | 부속 | `capabilities/gallery-admin.md` · 미작성 | 추론(export 목록만 확인) |
| 14 | 갤러리 계정·내 글·삭제 | GitHub 로그인(Neon Auth) 프록시, `/me` 내 글 목록·삭제, `DELETE /api/stacks/$id`(delete key로 삭제). | `site/src/lib/auth.ts` `handleAuthProxy`·`getViewer`, `features/account/server/my-posts.ts`, `features/submit/server/delete.ts` `handleDelete` | 10 (C4) | 부속 | `capabilities/gallery-account.md` · 미작성 | 추론(export 목록만 확인) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 것)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| C1 icons dir와 `manifest.json` (`{name: {source, url, file, bytes, white_fill?, dark_file?, dark_url?}}`, 파일명 = `%%ICON_<name>%%` 토큰) | 2, 3(쓰기), 5(읽기), 8(`--icons`로 읽기) | `fetch_icons.py` 375~395행, `build.py` 36~41행, `share.py` `stack_items` | `capabilities/icons-manifest.md` · 미작성 | 코드 확인 |
| C2 HTML 템플릿 규약 (`%%…%%` 토큰, `.canvas`·`.scroller` 선택자, `html[data-theme="dark"]`, 캔버스 크기 3곳 동기화) | 4, 5, 6, 7 | `assets/template.html`, `build.py`, `render_png.py` `SQUARE_CORNERS` | `capabilities/template-contract.md` · 미작성 | 코드 확인 |
| C3 갤러리 제출 프로토콜 (`GET /api/challenge` → `{challenge, bits}`, `POST /api/stacks` multipart `meta`·`light`·`dark` + 헤더 `X-Proof-Of-Work`, 응답 `{id, url, status, deleteKey}`, 한도: PNG 1MB, 본문 2.5MB) | 8, 9, 10 | `share.py` 166~185행, `intake.ts` 36~115행, `submit.ts` 137행 | `capabilities/gallery-protocol.md` · 미작성 | 코드 확인 |
| C4 DB·공개 모델 (`stacks`, `votes`, `reports`, `reporter_strikes`, `used_challenges`, `settings`, `PublicStack`) | 9~14 | `site/src/lib/db/schema.ts`, `lib/public-stack.ts` | `capabilities/gallery-data-model.md` · 미작성 | 코드 확인(`schema.ts` 앞 110줄 중 `stacks` 위주). `public-stack.ts`는 미정독 |

**대조한 범위와 미탐색 영역**
- 대조: README 기능 목록(공식 로고, 화살표가 글자를 지나지 않음, HTML·PNG·React·Artifact, 갤러리), `SKILL.md` 7단계, `scripts/` 4개 전체, `references/` 2개, `assets/template.html`(앞뒤), `release.yml`, `site.yml` 앞부분, `site/wrangler.jsonc`·`package.json`, `site/src/routes/` 파일 목록, 제출 경로(`intake.ts`·`submit.ts`·`challenge.ts`·`files.ts`)와 `moderation.ts` 앞 60줄.
- 문서와 구현의 차이: README는 "posts only after you say yes twice"라고 하지만 이 두 번의 동의는 `SKILL.md` 7단계 지시문이고 `share.py`에는 확인 절차가 없다(코드 확인). `SKILL.md`는 "stdlib only"라고 하고 `fetch_icons.py` import가 stdlib뿐임을 확인했다(코드 확인).
- 미탐색: `site/src/components/`(UI 부품 약 40개)와 CSS, 페이지 컴포넌트(`*-page.tsx`), `site/drizzle/` 마이그레이션 내용, `site.yml` 뒷부분, 테스트 파일(기본 제외), `docs/*.png`(README 이미지), `fetch_icons.py` 60~146행의 별칭 표, `template.html` CSS 중간부(160행 이전 일부).
- 실행하지 않은 것: 스크립트 실행, 네트워크 호출, Playwright 렌더, 갤러리 호출. 모든 동작 서술은 읽은 코드 기준이다.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 스킬 파이프라인과 갤러리 배포 단위의 경계 |

검증 구분: archify `finalize`의 4개 gate(validate, deliver, check, browser-check)는 통과했다(`diagrams/structure.finalize.json`). 사람이 그림을 열어 보는 시각 검토는 하지 않았다.

### 그림 해설

**읽는 순서**
1. 맨 윗줄 왼쪽에서 오른쪽으로 `사용자 + 코딩 에이전트` → `SKILL.md` → `fetch_icons.py` → `build.py` → `render_png.py` → `share.py`. 스킬이 실행되는 순서다.
2. `fetch_icons.py` 아래 `로고 출처`와 `build.py` 아래 `template.html`은 각각 로고를 넣어 주는 쪽과 초안을 넣어 주는 쪽이다.
3. 오른쪽 아래 `갤러리 Worker`와 그 주변 3개는 `share.py`가 `POST`하는 서버 쪽이다.

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 사용자 + 코딩 에이전트 | 스택을 설명하고, 에이전트가 `SKILL.md`를 읽어 단계를 실행한다. 좌표 계획과 HTML 편집, TSX 변환은 에이전트의 몫이다. | 입력 문장 → 다이어그램 | `SKILL.md` 8~26행 | 코드 확인(문서 서술) |
| SKILL.md | 7단계 워크플로와 로고·레이아웃 규칙을 지시문으로 담는다. 코드로 강제하는 부분은 없다. | 에이전트에게 지시 | `SKILL.md` `## Workflow` | 코드 확인 |
| fetch_icons.py | spec마다 출처를 순서대로 시도해 로고를 받고 `manifest.json`을 갱신한다. 하나라도 실패하면 exit 1이다. | 입력 spec → `<dir>/<name>.*`, `manifest.json` | `fetch_icons.py` `main`, `sources` | 코드 확인 |
| 로고 출처 | svgl API, devicon, gilbarbara/logos, Lucide, AWS·Google·Microsoft 공식 zip, 명시 URL. | HTTP GET 응답 | `fetch_icons.py` `sources`, `*_index` | 코드 확인(실행 안 함) |
| template.html | 에이전트가 복사해 고치는 단일 HTML. 토큰과 클래스가 형식 문서를 겸한다. | `%%ICON_<name>%%` 토큰이 있는 초안 | `assets/template.html`, `geometry.md` | 코드 확인 |
| build.py | 토큰을 data URI로 바꿔 자체 완결 HTML을 쓴다. 남은 토큰이 있으면 실패한다. | 초안 + icons dir → `out.html` | `build.py` `main` | 코드 확인 |
| render_png.py | HTML을 Chromium으로 열어 `.canvas`를 라이트·다크로 캡처한다. | `out.html` → `out.png`, `out-dark.png` | `render_png.py` `main` | 코드 확인 |
| share.py | PNG와 메타를 검증하고 proof of work를 푼 뒤 갤러리에 올린다. | PNG 쌍 + 메타 → 글 URL, delete key | `share.py` `submit` | 코드 확인 |
| 갤러리 Worker | intake 검사를 통과한 글을 인코딩해 저장한다. | multipart → `{id, url, status, deleteKey}` | `submit.ts` `handleSubmit`, `publish` | 코드 확인 |
| Workers AI 심사 | 4개 점수로 `published`/`held`를 정한다. 점수가 없으면 `held`다. | 미리보기 JPEG + 제목 → 점수 | `moderation.ts` `decide`, `submit.ts` 97~102행 | 코드 확인(`decide`). `classify` 본문은 미정독 |
| Cloudflare R2 | 라이트·다크 WebP와 preview JPEG를 `stacks/<id>/` 아래에 둔다. | 바이트 | `submit.ts` 106~116행 | 코드 확인 |
| Neon Postgres | 글 메타, 투표, 신고를 저장한다. insert가 실패하면 R2 파일을 지운다. | SQL | `schema.ts` `stacks`, `submit.ts` 117~136행 | 코드 확인 |

**실행 흐름: 스킬로 다이어그램 한 장 만들기**
1. 사용자가 스택을 말하면 에이전트가 node, group, edge를 정한다 (`SKILL.md` Step 1, 추론).
2. `python3 fetch_icons.py <icons> tanstack hono ...` → 로고와 `manifest.json` (`fetch_icons.py:main`).
3. 에이전트가 `template.html`을 복사해 `geometry.md` 규칙으로 좌표를 적는다 (`geometry.md`, 추론).
4. `python3 build.py draft.html <icons> out.html --fonts <skill>/assets/fonts` → 자체 완결 HTML (`build.py:main`).
5. `python3 render_png.py out.html check.png --selector .canvas --scale 2` → 라이트·다크 PNG를 에이전트가 눈으로 확인 (`render_png.py:main`, `SKILL.md` Step 5).
6. 사용자가 원하면 `share.py submit`으로 갤러리에 올린다 (`share.py:submit`).

**미확인 영역**
- 구조도에서 뺀 갤러리 화면(투표, 신고, 관리자, 내 글, OG)은 feature map 행 11~14에 있고 코드를 열어 보지 않았다.
- 갤러리의 `classify`가 호출하는 Workers AI 모델과 AI Gateway 설정은 `moderation.ts` 64행 이후를 읽지 않았다.
- 로고 수집이 실제로 어느 출처에서 성공하는지는 네트워크를 쓰지 않아 모른다.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸. 전부 미작성이고 범위 승인을 기다린다.
- **워크플로 설명 페이지**: [workflow.html](./explainer/workflow.html)(초안 [workflow.archify.md](./explainer/workflow.archify.md)). 스킬이 스택 설명 한 문장을 architecture 그림 한 장으로 바꾸는 순서를 archify explainer로 설명한다.
- **비교 대상**: 같은 폴더의 [archify overview](../archify/overview.md). 둘 다 "구조 다이어그램을 만드는 에이전트 스킬"이지만 stack-diagram은 렌더러·스키마 없이 템플릿과 규칙 문서로 만들고, archify는 JSON 스키마와 검증 gate를 코드로 둔다.
