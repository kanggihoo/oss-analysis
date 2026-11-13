# stack-diagram은 스택 설명 한 문장을 어떤 순서로 architecture 그림 한 장으로 바꾸나? {#stack-diagram-workflow}

에이전트가 `SKILL.md`의 7단계를 따라 그림을 직접 짜고, 스크립트 3개가 로고 수집, 자산 inline, PNG 캡처만 맡습니다. 결과의 원본은 HTML 파일 하나이고, PNG와 React 컴포넌트와 artifact는 이 HTML에서 만듭니다.

- 그림을 그리는 엔진은 레포에 없습니다. 에이전트가 `template.html`을 복사해서 `geometry.md`의 규칙대로 노드와 화살표 좌표를 직접 씁니다.[](source:geometry)
- 스크립트는 `fetch_icons.py`(로고 받기), `build.py`(로고와 폰트를 HTML에 넣기), `render_png.py`(PNG 찍기) 순서로 이어집니다.[](source:skillmd)
- 화살표가 글자를 지나가는지는 코드가 검사하지 않습니다. 에이전트가 PNG를 열어 눈으로 확인하고, 문제가 있으면 좌표를 고쳐 다시 만듭니다.[](source:renderpng)
- 로고는 색을 바꾸지 않습니다. 흰색 로고는 로고를 건드리는 대신 어두운 tile 위에 올립니다.[](source:skillmd)

@answer scope="커밋 5af3b09 · 스킬 본체 skills/stack-diagram 기준 · 코드와 문서를 읽은 결과이고 스크립트는 실행하지 않음 · 갤러리 사이트 제외"
@meta locale=ko
@source repo title="stack-diagram 저장소 (커밋 5af3b09)" url=https://github.com/caru-ini/stack-diagram/tree/5af3b095fff7109c905c5284dc510dc06588bade
@source skillmd title="SKILL.md: 에이전트가 따르는 7단계" url=https://github.com/caru-ini/stack-diagram/blob/5af3b095fff7109c905c5284dc510dc06588bade/skills/stack-diagram/SKILL.md
@source fetch title="fetch_icons.py: 로고 수집과 manifest.json" url=https://github.com/caru-ini/stack-diagram/blob/5af3b095fff7109c905c5284dc510dc06588bade/skills/stack-diagram/scripts/fetch_icons.py
@source build title="build.py: 폰트와 아이콘 inline" url=https://github.com/caru-ini/stack-diagram/blob/5af3b095fff7109c905c5284dc510dc06588bade/skills/stack-diagram/scripts/build.py
@source renderpng title="render_png.py: Playwright로 PNG 캡처" url=https://github.com/caru-ini/stack-diagram/blob/5af3b095fff7109c905c5284dc510dc06588bade/skills/stack-diagram/scripts/render_png.py
@source geometry title="geometry.md: 좌표와 화살표 규칙" url=https://github.com/caru-ini/stack-diagram/blob/5af3b095fff7109c905c5284dc510dc06588bade/skills/stack-diagram/references/geometry.md
@source template title="template.html: 에이전트가 복사해 고치는 틀" url=https://github.com/caru-ini/stack-diagram/blob/5af3b095fff7109c905c5284dc510dc06588bade/skills/stack-diagram/assets/template.html
@source tsx title="tsx.md: React 컴포넌트로 바꾸는 방법" url=https://github.com/caru-ini/stack-diagram/blob/5af3b095fff7109c905c5284dc510dc06588bade/skills/stack-diagram/references/tsx.md

## 에이전트는 어떤 순서로 일하나? {#flow}

사용자가 "Next.js와 Hono API를 Vercel에 올리고 Neon, Clerk를 쓴다"처럼 말하면, 에이전트는 아래 순서로 진행합니다.[](source:skillmd) 확인 단계에서 겹침이 보이면 좌표 단계로 돌아갑니다.

@workflow id=make-flow title="그림 한 장을 만드는 순서"
| lane prep | 준비 |
| lane make | 제작 |
| lane out | 전달 |
| content | 내용 정하기 | external | prep |
| icons | 로고 받기 | backend | prep |
| layout | 좌표 쓰기 | backend | make |
| build | HTML 만들기 | backend | make |
| look | PNG로 확인 | security | make |
| deliver | 형식별 전달 | frontend | out |
| share | 갤러리 공유 | cloud | out |
| content > icons | |
| icons > layout | icons 폴더 |
| layout > build | 초안 |
| build > look | out.html |
| look > layout | 겹침 있음 | dashed |
| look > deliver | 통과 | emphasis |
| deliver > share | 동의 시 | dashed |

@steps id=make-steps
| s-content | 내용 정하기 | 기술마다 node 하나, 같은 runtime이나 vendor는 group 박스로 묶고, edge는 주 흐름(accent 실선), 내부 연결(neutral 실선), dev·deploy(점선) 세 종류로 나눕니다. | make-flow | content |
| s-icons | 로고 받기 | `fetch_icons.py <dir> tanstack hono ...`를 실행하면 svgl, devicon, gilbarbara/logos 순으로 시도해 로고 파일과 `manifest.json`을 씁니다. | make-flow | icons |
| s-layout | 좌표 쓰기 | `template.html`을 복사해 노드는 `left = centerX - 66`, 그룹은 가장 바깥 노드 상자에서 24px 밖에 놓습니다. | make-flow | layout |
| s-build | HTML 만들기 | `build.py draft.html <icons> out.html --fonts <fonts>`가 `%%ICON_<name>%%` 자리에 로고를 data URI로 채웁니다. | make-flow | build |
| s-look | PNG로 확인 | `render_png.py`로 PNG를 찍고 화살표가 글자를 지나지 않는지, 아이콘이 다 보이는지 에이전트가 직접 봅니다. | make-flow | look |
| s-deliver | 형식별 전달 | 요청한 형식으로 줍니다. HTML이 기본이고 PNG는 라이트와 다크 두 장입니다. | make-flow | deliver |
| s-share | 갤러리 공유 | 사용자가 명시적으로 동의한 경우에만 `share.py submit`을 실행합니다. 대화당 한 번만 제안합니다. | make-flow | share |

## 어떤 파일이 무엇을 받아서 무엇을 내놓나? {#files}

`build.py`는 두 군데에서 입력을 받습니다. 하나는 `fetch_icons.py`가 만든 icons 폴더이고, 다른 하나는 에이전트가 `template.html`을 고쳐 쓴 초안입니다.[](source:build) 이 둘이 만나는 곳이 `%%ICON_<name>%%` 토큰입니다. 초안에 `%%ICON_hono%%`라고 적혀 있으면, `build.py`가 icons 폴더에서 이름이 `hono`인 파일을 찾아 base64 data URI로 바꿔 넣습니다.

@architecture id=file-data title="파일과 산출물의 흐름"
| fetch | fetch_icons.py | backend |
| iconsdir | icons 폴더 | database |
| draft | 초안 HTML | frontend |
| build | build.py | backend |
| render | render_png.py | backend |
| png | PNG 두 장 | frontend |
| fetch > iconsdir | 로고 |
| iconsdir > build | 아이콘 |
| draft > build | 토큰 | emphasis |
| build > render | out.html | emphasis |
| render > png | 라이트, 다크 |

한 문장에서 파일까지 가는 실제 명령은 `SKILL.md`에 있는 예시 그대로 이렇습니다.[](source:skillmd)

```bash title="로고 받기 (SKILL.md 2단계 예시)"
python3 scripts/fetch_icons.py <icons-dir> tanstack hono drizzle "betterauth:better-auth" "orpc=https://orpc.unnoq.com/logo.webp"
```

```bash title="HTML 만들기 (SKILL.md 4단계)"
python3 scripts/build.py my-diagram.html <icons-dir> out.html --fonts <skill>/assets/fonts
```

```bash title="PNG로 확인 (SKILL.md 5단계)"
python3 scripts/render_png.py out.html check.png --selector .canvas --scale 2
```

## 누가 어떤 일을 하나? {#who-does-what}

위 흐름에서 스크립트가 하는 일은 파일을 받고, 바꾸고, 찍는 일뿐입니다. 어디에 무엇을 놓을지 정하는 일과 결과가 괜찮은지 판단하는 일은 에이전트에게 있습니다.[](source:skillmd)

| 일 | 맡은 쪽 | 근거 |
| --- | --- | --- |
| 기술을 node, group, edge로 나누기 | 에이전트 | `SKILL.md` 1단계 지시문 |
| 로고 받기 | `fetch_icons.py` | 출처를 순서대로 시도하고 `manifest.json`에 기록 |
| 노드와 화살표 좌표 정하기 | 에이전트 {caution:코드 없음} | `geometry.md` 규칙만 있음 |
| 로고와 폰트를 HTML에 넣기 | `build.py` | 남은 `%%...%%` 토큰이 있으면 실패 |
| PNG 찍기 | `render_png.py` | 기본은 라이트와 다크 두 장 |
| 겹침과 잘림 확인 | 에이전트 {caution:코드 검사 없음} | `render_png.py`는 캡처만 함 |
| React 컴포넌트로 바꾸기 | 에이전트 | 변환 스크립트 없이 `tsx.md`를 읽고 직접 작성 |
| 갤러리에 올리기 | `share.py` | 사용자 동의는 `SKILL.md`의 지시이고 `share.py`에는 확인 절차가 없음 |

@callout level=warning title="코드가 막아 주지 않는 것"
| `build.py`는 토큰이 남았는지만 검사합니다. 화살표가 글자를 지나가는지, 노드가 그룹 밖으로 튀어나왔는지는 아무 스크립트도 검사하지 않습니다.
| 그래서 5단계에서 PNG를 직접 열어 보고, 문제가 있으면 3단계 좌표를 고쳐 다시 만드는 것이 이 워크플로의 품질 확인 방법입니다.

## 로고는 어떤 규칙으로 고르나? {#icon-rules}

`fetch_icons.py`는 이름이 정확히 일치하는 로고만 받고, 일치하지 않으면 다음 출처로 넘어갑니다. 비슷한 이름의 다른 브랜드 로고가 들어가는 것을 막기 위해서입니다.[](source:fetch)

- `svgl`에서 먼저 찾습니다. 라이트와 다크가 따로 있으면 라이트를 `<name>`으로, 다크를 `<name>_dark`로 저장합니다.
- `svgl`에 없으면 `devicon`, 그다음 `gilbarbara/logos`를 시도합니다.
- 모두 없으면 `FAIL`을 출력하고 종료 코드 1로 끝납니다. 이때 에이전트는 공식 로고 파일 주소를 `name=URL` 형식으로 넘깁니다.
- 로고 전체가 흰색이면 `manifest.json`에 `white_fill`을 표시합니다. 에이전트는 SVG를 열어 정말 흰색인지 확인한 뒤, 맞으면 `tile dark` 클래스로 어두운 tile 위에 올립니다.[](source:skillmd)
- 사용자, 브라우저 같은 brand 없는 노드는 `lucide/<icon>` 아이콘을 씁니다. 글자나 이모지를 tile에 넣지 않습니다.

## 이 설명을 코드로 확인하려면? {#check}

- [ ] `SKILL.md` 18~26행에서 7단계 순서가 위 흐름도와 같은지 봅니다.
- [ ] `build.py`의 `main`에서 `%%ICON_<name>%%` 치환과 남은 토큰 검사(`unresolved tokens`)를 찾아봅니다.
- [ ] `render_png.py`의 `main`에 겹침 검사가 없고 `shoot` 함수가 캡처만 하는지 확인합니다.
- [ ] `geometry.md`의 "Edge anchoring" 절에서 수직 화살표를 상자 아래쪽에서 tile 위쪽으로 잇는 규칙을 읽습니다.
