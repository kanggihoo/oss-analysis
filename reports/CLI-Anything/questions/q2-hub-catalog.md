---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-19
updated: 2026-11-19
sources:
  - registry.json
  - public_registry.json
  - cli-hub/cli_hub/registry.py
  - inkscape/agent-harness/cli_anything/inkscape/utils/inkscape_backend.py
---

# [Q] `cli-hub list`가 보여 주는 103개 CLI는 각각 무엇을 지원하는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 목록·필드 `코드 확인`(registry 데이터를 읽고 원격 캐시와 대조). 각 CLI의 실제 기능 범위와 동작은 `미확인`(`mermaid` 하나만 설치해 실행, [q1](./q1-cli-hub.md))

---

## 1. 질문 및 결론

- **질문**: README 표(약 40개)가 아니라 현재 버전의 `cli-hub list` 기준으로 무엇이 지원되는가.
- **핵심 결론**: 103개이고 두 registry에서 온다. `registry.json`의 harness 79개는 CLI-Anything 방식(Click CLI + `SKILL.md`)으로 만든 CLI이고, `public_registry.json`의 public 24개는 외부에서 배포하는 CLI(공식 CLI 포함)의 설치 정보만 등록한 것이다. 대부분의 CLI는 대상 소프트웨어를 대체하지 않고 **이미 설치된 앱·실행 중인 서버·클라우드 API를 호출하는 wrapper**라서, `cli-hub install`만으로는 쓸 수 없고 3절의 "필요한 것"이 따로 있어야 한다.

---

## 2. 목록의 성격

- **기준**: `repos/CLI-Anything` `34f5195`(커밋일 2026-09-22). `registry.json`의 `meta.updated`는 `2026-06-19`, `public_registry.json`은 `2026-08-20`이다. 원격 registry(hkuds.github.io)와 로컬 두 파일은 항목과 필드가 같았다(차이 0, [q1](./q1-cli-hub.md) 4절).
- **소속**: harness 79 + public 24 = 103.
- **설치 방식**(registry의 `package_manager`/`install_cmd`로 계산): pip 83(harness 77 + public 6), npm 11, brew 2, bundled 2, uv 1, script 1, go 1, 그 외 2(`sketch`는 `npm install && npm link`, `clibrowser`는 `cargo install`).
- **registry의 category는 일관되지 않다**: 35개 값이 있고 `science`/`scientific`, `knowledge`/`knowledge-management`가 따로 있으며 `web`에 브라우저, CMS, 메일, 쇼핑이 섞여 있다. 아래 분류는 사람이 보기 쉽게 다시 묶은 것이다.
- 전체 103행은 [`artifacts/CLI-Anything/hub-catalog.tsv`](../../../artifacts/CLI-Anything/hub-catalog.tsv)(name, source, category, package_manager, requires, entry_point, version, skill_md, description).

### 표 읽는 법

- **소속** `H` = harness, `P` = public.
- **유형**은 registry `requires` 문장으로 사람이 붙인 분류다(휴리스틱).
  - `앱`: 해당 소프트웨어(데스크톱 앱·바이너리)가 로컬에 설치돼 있어야 함
  - `서버`: 실행 중인 서비스(로컬 또는 self-hosted)에 REST/MCP로 접속
  - `클라우드`: 계정·API key로 외부 서비스 호출
  - `독립`: Python/Node 등 런타임만 있으면 동작
- **설치명령**은 `cli-hub install <name>` 하나로 같다.

---

## 3. 분류별 목록

### 3.1 창작: 이미지·영상·오디오·음악·3D·CAD (24)

| name | 소속 | 유형 | 하는 일 | 필요한 것 |
|---|---|---|---|---|
| gimp | H | 앱 | 래스터 이미지 배치 처리(`gimp -i -b`) | gimp |
| inkscape | H | 앱 | SVG 벡터 편집·export | inkscape |
| krita | H | 앱 | 디지털 페인팅, export 파이프라인 | krita |
| blender | H | 앱 | 3D 모델링·애니메이션·렌더(`blender --background --python`) | blender ≥ 4.2 |
| freecad | H | 앱 | 파라메트릭 CAD (258개 명령: Part, Sketcher, Assembly, TechDraw 등) | FreeCAD ≥ 1.1 |
| meerk40t | H | 독립 | 레이저 커팅·조각, SVG/G-code export | MeerK40t(자동 설치) |
| inkstitch | H | 앱 | 자수 디지타이징, DST/PES/JEF/VP3 export | Ink/Stitch 확장 |
| live2d | H | 독립 | Live2D 모델 검사·검증·편집·diff·배포 | Python 3.10+ |
| audacity | H | 앱 | 오디오 편집·처리(sox) | sox |
| wavetone | H | 앱 | 음원 채보 manifest 준비, Windows WaveTone 실행 | WaveTone 2.61 (Windows) |
| elevenlabs | P | 클라우드 | 음성 에이전트를 코드로 관리(push/pull sync) | Node, API key |
| musescore | H | 앱 | 악보 transpose, PDF/오디오/MIDI export | MuseScore 4 |
| suno | P | 클라우드 | 가사·스타일로 음악 생성, 일괄 생성 | Python, sunoapi.org key |
| kdenlive | H | 앱 | 영상 편집·렌더(melt) | melt |
| shotcut | H | 앱 | 영상 편집·렌더(melt/ffmpeg) | melt, ffmpeg |
| openscreen | H | 앱 | 화면 녹화 편집(zoom, speed ramp, trim, 주석) | ffmpeg |
| palmier | H | 앱 | Palmier Pro 영상 편집기의 timeline·자막 제어(MCP) | Palmier Pro 실행 |
| quietshrink | H | 앱 | macOS 화면 녹화 압축(70~90% 감소) | ffmpeg hevc_videotoolbox, Apple Silicon |
| videocaptioner | H | 앱 | 음성 인식, 자막 번역·최적화·영상에 입히기 | videocaptioner(pip) |
| obs-studio | H | 앱 | 스트리밍·녹화 scene 구성 | obs-studio |
| drawio | H | 앱 | 다이어그램 생성·export | draw.io desktop |
| mermaid | H | 독립 | Mermaid 상태 파일, 렌더 URL 생성 | 없음 |
| sketch | H | 독립 | JSON 명세로 `.sketch` 디자인 파일 생성 | Node ≥ 16 |
| 3mf | H | 독립 | 3D 프린팅 mesh 편집: 구멍 크기 조정, 수리, 비교 | numpy, scipy, trimesh |

### 3.2 AI·미디어 생성 (13)

| name | 소속 | 유형 | 하는 일 | 필요한 것 |
|---|---|---|---|---|
| comfyui | H | 서버 | 이미지 생성 workflow 관리 | ComfyUI(localhost:8188) |
| ollama | H | 서버 | 로컬 LLM 추론·모델 관리 | Ollama(localhost:11434) |
| openwebui | H | 서버 | OpenWebUI backend 조작 | 실행 중인 인스턴스 |
| dify-workflow | H | 독립 | Dify workflow DSL 생성·검사·편집·export | upstream dify-workflow CLI |
| minimax | H | 클라우드 | MiniMax 채팅·TTS | MINIMAX_API_KEY |
| minimax-cli | P | 클라우드 | MiniMax 플랫폼 token·모델 관리 | Node ≥ 16, API key |
| novita | H | 클라우드 | Novita(OpenAI 호환) API로 DeepSeek·GLM 등 호출 | NOVITA_API_KEY |
| notebooklm | H | 클라우드 | NotebookLM notebook·source·chat(실험적 wrapper) | notebooklm CLI, 로그인 |
| magnific | H | 클라우드 | Magnific의 원격 MCP로 이미지·영상 생성·업스케일 | Node(mcpc), Python |
| anygen | H | 클라우드 | 문서·슬라이드·웹사이트 생성 | ANYGEN_API_KEY |
| generate-veo-video | P | 클라우드 | Google Veo 3.1 영상 생성(text/image-to-video) | uv, GCP 프로젝트 |
| jimeng | P | 클라우드 | ByteDance 이미지·영상 생성 | Jimeng 계정·API key |
| vivideo | P | 클라우드 | 아바타·text-to-video 생성 | Node ≥ 18.17, API key |

### 3.3 문서·지식·생산성 (11)

| name | 소속 | 유형 | 하는 일 | 필요한 것 |
|---|---|---|---|---|
| libreoffice | H | 앱 | ODF 문서 생성, PDF/DOCX/XLSX/PPTX export(headless) | libreoffice |
| calibre | H | 앱 | e-book 목록·검색·메타데이터·변환 | calibre |
| zotero | H | 앱 | 문헌 검색·가져오기·PDF·BibTeX·노트(CLI 70+, MCP 도구 52) | Zotero 7/8 실행 |
| joplin | H | 앱 | notebook·note·to-do·태그·동기화 | Joplin terminal CLI |
| obsidian | H | 앱 | vault 노트·검색·명령 실행(Local REST API) | Obsidian + 플러그인 |
| obsidian-cli | P | 앱 | Obsidian 공식 CLI(vault 자동화, 스크린샷, 검색) | Obsidian ≥ 1.12.7 |
| obsidian-agent-cli | P | 앱 | 노트·canvas·Excalidraw·Kanban·주기 노트 관리 | Obsidian + REST API 플러그인 |
| siyuan | H | 서버 | SiYuan notebook·document·block·검색 | SiYuan HTTP API |
| mubu | H | 앱 | Mubu 아웃라이너의 로컬 데이터 조작 | Mubu desktop |
| pieces | P | 서버 | Pieces OS 장기 메모리 검색·생성 | Pieces OS(localhost) |
| seaclip | H | 서버 | Kanban, 6-agent AI pipeline, 이슈 관리 | SeaClip-Lite(localhost:5200) |

### 3.4 개발·DevOps·자동화·디버깅·테스트 (21)

| name | 소속 | 유형 | 하는 일 | 필요한 것 |
|---|---|---|---|---|
| n8n | H | 서버 | workflow 자동화(55개 이상 명령) | n8n ≥ 1.0.0 |
| eez-studio | H | 앱 | EEZ Studio 프로젝트·LVGL UI·SCPI 명령 자동화 | EEZ Studio 소스 빌드 |
| lldb | H | 앱 | native 디버깅, JSON CLI와 stdio Debug Adapter Protocol server | LLDB + Python binding |
| renderdoc | H | 앱 | GPU frame capture 분석, shader export | RenderDoc Python binding |
| nsight-graphics | H | 앱 | NVIDIA GPU capture·GPU Trace 요약(Windows 우선) | Nsight Graphics |
| unrealinsights | H | 앱 | Unreal trace 캡처·세션 제어(Windows 우선) | Unreal Engine + Windows |
| nslogger | H | 앱 | iOS/macOS 로그 캡처·필터·export | macOS(Bonjour 라이브 캡처) |
| iterm2 | H | 앱 | 실행 중인 iTerm2의 창·탭·pane 제어 | iTerm2 (macOS) |
| pm2 | H | 앱 | Node 프로세스 start/stop/logs | PM2 |
| wiremock | H | 서버 | HTTP mock stub·요청 검사·트래픽 녹화 | WireMock server |
| jumpserver | H | 서버 | 배스천 호스트 자산·사용자·권한·감사 로그 | JumpServer ≥ 3.0 |
| cc-switch | H | 앱 | AI 코딩 도구 설정(provider, skills, MCP, 사용량) 조회 | CC Switch |
| eth2-quickstart | H | 앱 | Ethereum 노드 배포·운영 | eth2-quickstart checkout |
| tigris | H | 앱 | S3 호환 object storage: bucket, object, snapshot, IAM | tigris CLI |
| 1password-cli | P | 클라우드 | vault 접근·secret 조회 | 1Password 계정, brew |
| sentry | P | 클라우드 | release, sourcemap, monitor 관리 | Sentry 계정·token, npm |
| deployhq | P | 클라우드 | 배포·서버·프로젝트 관리 | DeployHQ 계정, brew |
| android-cli | P | 앱 | Android SDK·프로젝트·에뮬레이터·배포(공식, preview) | Linux x86_64/macOS arm64 |
| smithue-cli | P | 앱 | SmithUE 플러그인으로 Unreal Editor 명령 실행 | UE + SmithUE 플러그인 |
| macrocli | H | 독립 | GUI workflow를 매개변수화된 macro로 변환(한 번 녹화, 반복 실행) | 없음 |
| cloakbrowser | P | 독립 | 봇 탐지를 통과하는 stealth Chromium 제어 | Node ≥ 20, playwright |

### 3.5 게임 (4)

| name | 소속 | 유형 | 하는 일 | 필요한 것 |
|---|---|---|---|---|
| godot | H | 앱 | 프로젝트·scene 편집·export·GDScript 실행(headless) | Godot 4.x |
| sbox | H | 앱 | s&box(Source 2) scene·prefab·material·codegen | s&box (Steam) |
| ueatelier | H | 앱 | Unreal Editor 5.6/5.7 MCP 확장 workbench | UE 5.6/5.7 + 플러그인 |
| slay_the_spire_ii | H | 앱 | 실제 게임을 로컬 HTTP API로 제어 | Slay the Spire 2 + STS2_Bridge mod |

### 3.6 데이터·과학·GIS·점군 (13)

| name | 소속 | 유형 | 하는 일 | 필요한 것 |
|---|---|---|---|---|
| openrefine | H | 서버 | 데이터 import, operation history 정리, export | OpenRefine ≥ 3.10 |
| chromadb | H | 서버 | 벡터 DB collection·문서·검색 | ChromaDB(localhost:8000) |
| stata | H | 앱 | do-file·배치 실행, JSON 출력 | Stata 라이선스 |
| unimol_tools | H | 독립 | 분자 특성 예측 학습·추론(task 5종) | PyTorch ≥ 1.12 |
| py4csr | P | 독립 | CDISC 임상시험 보고서(CSR/TFL) 생성 | Python ≥ 3.10 |
| qgis | H | 앱 | 지리 프로젝트·레이아웃 export·처리(PyQGIS, `qgis_process`) | QGIS |
| arcgis-pro | P | 앱 | ArcGIS Pro(ArcPy) 지도 제작·지오프로세싱 | Windows 전용, 라이선스 |
| cloudcompare | H | 앱 | 점군·mesh 처리: 색, normal, Delaunay, 노이즈 필터 | CloudCompare |
| cloudanalyzer | H | 독립 | 점군·궤적 품질 평가(Chamfer, AUC, ATE/RPE) | cloudanalyzer |
| intelwatch | H | 독립 | 경쟁 정보·M&A 실사·OSINT | Node ≥ 18 |
| firefly-iii | H | 서버 | 개인 재무 관리 | Firefly III 인스턴스 + token |
| rms | H | 클라우드 | Teltonika 라우터 장치 관리·모니터링 | RMS_API_TOKEN |
| adguardhome | H | 서버 | DNS 광고 차단·네트워크 관리 | AdGuardHome 인스턴스 |

### 3.7 웹·검색·브라우저·커뮤니케이션 (17)

| name | 소속 | 유형 | 하는 일 | 필요한 것 |
|---|---|---|---|---|
| browser | H | 앱 | DOMShell MCP로 Chrome Accessibility Tree를 파일시스템처럼 탐색 | Chrome + DOMShell 확장, Node |
| browser-cdp | P | 앱 | 이미 열린 Chrome에 Chrome DevTools Protocol로 연결 | Chrome `--remote-debugging-port` |
| safari | H | 앱 | macOS Safari 자동화(84개 도구) | macOS, safari-mcp |
| clibrowser | H | 독립 | 에이전트용 CLI 브라우저: 검색·추출·폼·RSS·크롤 | cargo 또는 바이너리 |
| web-yu-pri | H | 클라우드 | 일본 우체국 Web Yu-pri 발송 라벨 자동화 | 계정, Playwright |
| exa | H | 클라우드 | AI 웹 검색·콘텐츠 추출 | EXA_API_KEY |
| tinyfish | H | 클라우드 | 웹 검색·페이지 추출·브라우저 자동화 | TinyFish API key |
| hacker-feeds-cli | H | 독립 | GitHub Trending, Hacker News, Reddit 등 피드 | Python, Node(`hf`) |
| mailchimp | H | 클라우드 | 오디언스·캠페인·리포트·automation(303개 명령) | MAILCHIMP_API_KEY |
| zoom | H | 클라우드 | 회의 관리(OAuth2) | Zoom OAuth 앱 |
| feishu | P | 클라우드 | Lark(Feishu) 앱·봇·클라우드 리소스(공식) | Node ≥ 16 |
| wecom | P | 클라우드 | WeCom 연락처·일정·문서·메시지(공식) | Node ≥ 18, 계정 |
| ve-twini | H | 앱 | Twitter/X 통합(`bird` + `opencli`) | bird, opencli |
| x-twitter-scraper | P | 클라우드 | Twitter 검색·프로필·모니터링 | Go |
| contentful | P | 클라우드 | Contentful space·migration 관리(공식) | Node, 계정 |
| sanity | P | 클라우드 | Sanity studio·dataset·schema(공식) | Node, 계정 |
| shopify | P | 클라우드 | Shopify app·theme·extension(공식) | Node, 계정 |

### 3.8 합계

3.1(24) + 3.2(13) + 3.3(11) + 3.4(21) + 3.5(4) + 3.6(13) + 3.7(17) = 103. 표의 첫 열 이름을 `hub-catalog.tsv`의 `name` 103개와 대조했고, 누락과 중복이 없다(5절).

---

## 4. 코드 근거 (Source Evidence)

| 구분 | 파일 | 설명 |
|---|---|---|
| harness 79개 | `registry.json` | 필드: `name`, `display_name`, `version`, `description`, `requires`, `homepage`, `install_cmd`, `entry_point`, `skill_md`, `category`, `contributors` |
| public 24개 | `public_registry.json` | 위 필드에 `package_manager`, `npm_package`, `npx_cmd`, `install_strategy`, `uninstall_cmd`, `update_cmd`, `detect_cmd`, `platform` 등이 추가됨 |
| 병합 | `cli-hub/cli_hub/registry.py` `fetch_all_clis` | harness + public을 합쳐 `list`가 보여 줌 |

**harness 79개의 위치(스크립트 계산)**: `install_cmd`의 `#subdirectory=<경로>`가 이 레포에 실제로 있는 폴더인 항목이 66개다. 나머지 13개 중 `sketch`는 이 레포의 폴더를 쓰지만 설치 방식이 `cd sketch/agent-harness && npm install && npm link`로 다르다. 12개는 이 레포 밖이다. `pip install cli-anything-<이름>`(PyPI)은 zotero·inkstitch·tinyfish·meerk40t, 외부 GitHub 레포는 openwebui·ueatelier·ve-twini·stata·hacker-feeds-cli·palmier·magnific, `cargo install --git`은 clibrowser다. `skill_md` 경로가 이 레포에 파일로 존재하는 항목은 71개다. 외부 12개는 이 레포의 코드로 내용을 확인할 수 없다.

---

## 5. 검증 과정 및 실행 결과

```bash
python dump.py artifacts/CLI-Anything/hub-catalog.tsv   # 원격 캐시 vs 로컬 비교 + TSV 생성
# live meta 2026-06-19 2026-08-20 / local 2026-06-19 2026-08-20
# harness live 79 local 79 only_live [] only_local [] diff_fields []
# public  live 24 local 24 ...                                    diff_fields []
# 103 {'harness': 79, 'public': 24}
```

3절 표 이름 대조: 표 행 103개, TSV `name` 103개, 누락·중복 0(정규식으로 첫 열 추출).

## 5.1 보충: 앱 wrapper가 실제로 하는 일 (inkscape 확인)

질문: AI가 SVG를 직접 쓸 수 있는데 왜 Inkscape가 필요한가. `inkscape` harness를 열어 확인했다(`코드 확인`, 이 harness 한정).

- SVG 편집(도형, path, gradient, text, layer, transform)은 harness의 Python 코드가 SVG(XML)를 직접 고친다. 파일은 `inkscape/agent-harness/cli_anything/inkscape/core/`(`shapes.py`, `paths.py`, `gradients.py` 등)와 `utils/svg_utils.py`다.
- Inkscape 프로그램은 **PNG·PDF 같은 형식으로 export할 때만** 호출한다. `utils/inkscape_backend.py:49-52`가 `inkscape <svg> --export-filename=<out> --export-dpi=<dpi>`를 실행하고, `:91`도 같은 방식이다. 프로그램이 없으면 `find_inkscape()`가 설치 안내와 함께 오류를 낸다(`:13-20`).
- 따라서 Inkscape가 필요한 이유는 SVG를 만들기 위해서가 아니라 **SVG를 래스터·PDF로 정확히 렌더하기 위해서**다. 다른 harness(blender, freecad, gimp)가 같은 구조인지는 harness마다 열어 봐야 한다(`미확인`).
- blender와 freecad의 "실제 결과물" 사례(Curiosity rover, orbital relay drone)는 README의 데모 주장이고 직접 실행해 확인하지 않았다(`미확인`).

## 6. 남은 질문 및 추가 조사 사항

- [ ] 각 CLI의 실제 명령 범위. README의 테스트 수와 registry 설명(예: freecad 258개 명령)은 `미확인`
- [ ] 소속(`harness`/`public`)을 가르는 기준과 외부 레포 CLI(13개)의 품질 검수 여부
