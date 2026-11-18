---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-18
updated: 2026-11-18
sources:
  - cli-anything-plugin/HARNESS.md
  - cli-anything-plugin/guides/mcp-backend.md
  - registry.json
  - README.md
  - libreoffice/agent-harness/cli_anything/libreoffice/utils/lo_backend.py
  - libreoffice/agent-harness/cli_anything/libreoffice/core/export.py
  - libreoffice/agent-harness/cli_anything/libreoffice/libreoffice_cli.py
  - blender/agent-harness/cli_anything/blender/utils/blender_backend.py
  - freecad/agent-harness/cli_anything/freecad/utils/freecad_backend.py
  - gimp/agent-harness/cli_anything/gimp/core/export.py
  - drawio/agent-harness/cli_anything/drawio/core/export.py
  - drawio/agent-harness/cli_anything/drawio/drawio_cli.py
  - eth2-quickstart/agent-harness/cli_anything/eth2_quickstart/utils/eth2qs_backend.py
  - intelwatch/agent-harness/cli_anything/intelwatch/intelwatch_cli.py
  - quietshrink/agent-harness/cli_anything/quietshrink/quietshrink_cli.py
  - ollama/agent-harness/cli_anything/ollama/utils/ollama_backend.py
  - adguardhome/agent-harness/cli_anything/adguardhome/utils/adguardhome_backend.py
  - adguardhome/agent-harness/cli_anything/adguardhome/adguardhome_cli.py
  - anygen/agent-harness/cli_anything/anygen/utils/anygen_backend.py
  - rms/agent-harness/cli_anything/rms/utils/rms_backend.py
  - slay_the_spire_ii/agent-harness/cli_anything/slay_the_spire_ii/utils/sts2_backend.py
  - seaclip/agent-harness/cli_anything/seaclip/utils/seaclip_backend.py
  - openrefine/agent-harness/cli_anything/openrefine/utils/openrefine_backend.py
  - browser/agent-harness/cli_anything/browser/utils/domshell_backend.py
  - browser/agent-harness/cli_anything/browser/browser_cli.py
  - browser/agent-harness/setup.py
  - safari/agent-harness/cli_anything/safari/utils/safari_backend.py
  - safari/agent-harness/cli_anything/safari/safari_cli.py
  - safari/agent-harness/setup.py
  - exa/agent-harness/cli_anything/exa/utils/exa_backend.py
  - iterm2/agent-harness/cli_anything/iterm2_ctl/utils/iterm2_backend.py
  - unimol_tools/agent-harness/cli_anything/unimol_tools/utils/unimol_backend.py
  - renderdoc/agent-harness/cli_anything/renderdoc/core/capture.py
  - cloudanalyzer/agent-harness/cli_anything/cloudanalyzer/utils/ca_backend.py
  - lldb/agent-harness/cli_anything/lldb/utils/lldb_backend.py
  - lldb/agent-harness/cli_anything/lldb/utils/session_client.py
  - 3MF/agent-harness/cli_anything/threemf/core/parser.py
  - obs-studio/agent-harness/cli_anything/obs_studio/utils/obs_utils.py
  - obs-studio/agent-harness/cli_anything/obs_studio/core/project.py
  - live2d/agent-harness/LIVE2D.md
  - cc-switch/agent-harness/cli_anything/ccswitch/utils/db.py
  - sketch/agent-harness/package.json
  - zotero/agent-harness/cli_anything/zotero/utils/zotero_sqlite.py
  - zotero/agent-harness/cli_anything/zotero/core/discovery.py
  - zotero/agent-harness/cli_anything/zotero/core/experimental.py
  - mubu/agent-harness/mubu_probe.py
  - mubu/agent-harness/setup.py
  - web-yu-pri/agent-harness/cli_anything/web_yu_pri/core/browser.py
  - nslogger/agent-harness/cli_anything/nslogger/core/listener.py
  - macrocli/agent-harness/cli_anything/macrocli/core/routing.py
  - sbox/agent-harness/cli_anything/sbox/utils/sbox_backend.py
  - sbox/agent-harness/cli_anything/sbox/sbox_cli.py
  - macrocli/agent-harness/MACROCLI.md
  - mubu/agent-harness/MUBU.md
  - zotero/agent-harness/ZOTERO.md
  - iterm2/agent-harness/cli_anything/iterm2_ctl/core/session.py
  - n8n/agent-harness/cli_anything/n8n/n8n_cli.py
  - n8n/agent-harness/cli_anything/n8n/core/versions.py
  - zoom/agent-harness/cli_anything/zoom/utils/zoom_backend.py
  - minimax/agent-harness/cli_anything/minimax/utils/minimax_backend.py
  - siyuan/agent-harness/cli_anything/siyuan/utils/siyuan_backend.py
  - QGIS/agent-harness/cli_anything/qgis/utils/qgis_backend.py
  - godot/agent-harness/cli_anything/godot/utils/godot_backend.py
  - krita/agent-harness/cli_anything/krita/utils/krita_backend.py
  - musescore/agent-harness/cli_anything/musescore/utils/musescore_backend.py
  - wavetone/agent-harness/cli_anything/wavetone/utils/wavetone_backend.py
  - gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py
  - drawio/agent-harness/cli_anything/drawio/utils/drawio_backend.py
  - cc-switch/agent-harness/cli_anything/ccswitch/ccswitch_cli.py
  - rekordbox/agent-harness/cli_anything/rekordbox/rekordbox_cli.py
depends:
  - ../capabilities/harness-contract.md
status: draft
---

# 하니스 카탈로그(패밀리)

> 하니스 디렉터리 69개를 입력으로 받아, 앱이나 서비스에 일을 시키는 호출 채널(외부 실행 파일, HTTP, MCP, in-process SDK, 호출 없음)에 따라 7개 패밀리로 나누고, 패밀리마다 백엔드 위치와 공통 호출·실패 전달 패턴과 규칙을 따르지 않는 예외를 안내한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

이 스펙은 레포가 구현한 기능이 아니고 레포 안 69개 구현체를 읽는 분류표다. 레포에는 분류 코드가 없고 `README.md`, `HARNESS.md`, `registry.json`에도 "패밀리"라는 말이 없다(R-01). 아래는 하니스 하나를 분류할 때 따르는 순서다.

1. 입력은 `<sw>/agent-harness/` 디렉터리 하나다.
2. 비테스트 소스(Python이면 `cli_anything/<pkg>/` 아래, Node이면 `src/`)에서 앱이나 서비스를 부르는 수단을 찾는다. 찾는 대상은 `subprocess` 호출, `requests`·`urllib.request` 요청, `mcp` import, 앱 Python 패키지 import, 그 밖의 수단이다.
3. 도메인 명령의 결과를 만드는 수단을 패밀리로 정한다. 가용성 점검, 권한 설정, 서버 기동 같은 보조 사용은 무시한다(R-09).
4. 패밀리의 공통 패턴(R-12~R-24)으로 백엔드 파일 위치, 호출 방식, 실패가 올라오는 모양을 읽는다.
5. HARNESS.md 규칙과 다른 곳이 있는지 예외 규칙(R-28~R-33)과 대조한다.
6. 앱별 설명(`description`)은 [harness-catalog.tsv](../../../artifacts/CLI-Anything/harness-catalog.tsv)에서 읽는다.

### 1.2 범위·통합 지점 [필수]

- 제공: 패밀리 정의와 판정 기준, 패밀리 소속 목록과 백엔드 위치, 패밀리별 호출·실패 전달 패턴, HARNESS.md 규칙과 다른 하니스 목록.
- 제외: 하니스 도메인 명령의 세부 구현. CLI 표면 계약(`--json`, 오류 JSON 형식, 종료 코드, REPL, 패키지 레이아웃)은 형제 스펙 `capabilities/harness-contract.md`가 소유한다. registry 필드 형식은 형제 스펙 `capabilities/registry-schema.md`가 소유한다. 이 스펙은 registry를 하니스 목록과 교차 확인할 때만 쓴다(R-10, R-11).
- 외부 의존·선행 계약: `harness-contract`가 정하는 CLI 표면에 대해 이 스펙이 가정하는 것은 한 가지다. 백엔드 계층이 실패를 예외나 결과 dict로 올리고, CLI 계층이 그것을 사용자에게 보이는 오류 출력으로 바꾼다. 이 변환 형식 자체는 이 스펙이 정의하지 않는다.
- 소유 상태·부작용: 이 스펙은 상태를 만들지 않는다. 각 패밀리가 다루는 외부 자원(외부 프로세스, 네트워크 연결, 파일, SQLite)은 R-12~R-27에 적었다.

### 1.3 인터페이스와 데이터 의미 [필수]

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `family` | string, 7개 중 하나: `exec`, `http`, `mcp`, `sdk`, `file`, `mixed`, `solo` | 하니스 하나에 하나다. 판정 기준은 R-01~R-09. 이 값은 이 분석이 붙인 이름이고 레포의 필드가 아니다. |
| 하니스 레코드 | map: `dir`(string, 레포 루트 하위), `package`(string), `family`, `backend_location`(optional string), `secondary_channels`(list), `confirmation`(`열람` / `AST`) | `dir`은 69개이고 `package`는 `dir`과 다를 수 있다(예: `iterm2`의 `iterm2_ctl`, `3MF`의 `threemf`). `backend_location`은 `cli_anything/<package>/` 아래 상대 경로다. 없으면 R-31 목록에 있다. `confirmation`은 2.1(d)에 표로 둔다. |
| 앱별 설명 | [harness-catalog.tsv](../../../artifacts/CLI-Anything/harness-catalog.tsv)의 `description` 열 | 앱이 하는 일은 TSV를 쓴다. TSV의 `backend_tags` 열은 휴리스틱이라 이 스펙의 `family`가 대신한다(2.1(c)에 수정 제안). |
| 실패 전달 형태 | 4가지: 예외(`RuntimeError`나 하위 클래스), 결과 dict(`ok`/`returncode`), `sys.exit`, `ClickException` 또는 `emit` 후 종료 | 패밀리 안에서도 섞여 있다(R-14, R-19). |
| 실행 파일·키·주소 설정 이름 | 환경변수 이름은 하니스마다 다르다 | 통일된 접두사나 규칙이 없다(R-12, R-18). |

**패밀리 정의** (개수는 합쳐서 69)

| `family` | 판정 규칙 | 개수 | 대표 구현체 |
|---|---|---|---|
| `exec` | 도메인 결과를 만들려고 앱이나 앱의 CLI를 `subprocess`로 실행한다 | 30 | libreoffice, blender, freecad, gimp |
| `http` | 서비스에 `requests` 또는 `urllib.request`로 요청한다 | 20 | ollama, adguardhome, anygen |
| `sdk` | 앱·서비스의 Python 패키지나 바인딩을 in-process로 import해 호출한다 | 7 | exa, renderdoc, lldb |
| `file` | 앱·서비스를 부르는 코드가 없고 파일·DB만 만든다 | 5 | obs-studio, live2d, 3MF |
| `mcp` | `mcp` 클라이언트로 MCP 서버를 호출한다 | 2 | safari, browser |
| `mixed` | 읽기와 쓰기·실행이 서로 다른 채널이고 둘 다 도메인 명령이다 | 2 | zotero, mubu |
| `solo` | 위 어느 것에도 속하지 않고 고유한 연결 방식을 쓴다 | 3 | web-yu-pri, nslogger, macrocli |

**패밀리별 소속과 백엔드 위치** (`dir`: 백엔드 파일. 경로는 `<dir>/agent-harness/cli_anything/<package>/` 아래)

- `exec` 30개, 대부분 `utils/<sw>_backend.py`다.
  - 파일 이름이 `<dir>_backend.py`와 다른 것: audacity `sox_backend.py`, cloudcompare `cc_backend.py`, eth2-quickstart `eth2qs_backend.py`, kdenlive·shotcut `melt_backend.py`, openscreen `ffmpeg_backend.py`, videocaptioner `vc_backend.py`.
  - 나머지 `utils/` 아래 파일: QGIS(`qgis_backend.py`), blender, calibre, dify-workflow(`dify_workflow_backend.py`), drawio, eez-studio(`eez_studio_backend.py`), freecad, gimp, godot, inkscape, joplin(`core/backend.py`도 있음), krita, libreoffice(`lo_backend.py`), musescore, notebooklm, nsight-graphics(`nsight_graphics_backend.py`와 `utils/backend/` 디렉터리), pm2, sbox, tigris, unrealinsights, wavetone.
  - 백엔드 파일이 없는 것: intelwatch(`intelwatch_cli.py`가 직접 호출), quietshrink(`quietshrink_cli.py`가 직접 호출).
- `http` 20개: `utils/<sw>_backend.py`가 있는 것은 adguardhome, anygen, chromadb, comfyui, firefly-iii(`firefly_iii_backend.py`), mermaid, minimax, n8n, novita, obsidian, ollama, openrefine, rms, seaclip, siyuan, zoom, slay_the_spire_ii(`sts2_backend.py`) 17개다. 나머지 3개는 jumpserver(`core/session.py`), mailchimp(`core/client.py`), wiremock(`utils/client.py`)이다.
- `sdk` 7개: cloudanalyzer(`utils/ca_backend.py`), exa(`utils/exa_backend.py`), iterm2(`utils/iterm2_backend.py`), lldb(`utils/lldb_backend.py`와 소켓 세션 `utils/session_server.py`, `utils/session_client.py`), unimol_tools(`utils/unimol_backend.py`)는 백엔드 파일이 있다. renderdoc은 `core/*.py` 각각이 `import renderdoc`을 하고, rekordbox는 `rekordbox_cli.py`가 `pyrekordbox`와 `mido`를 직접 쓴다.
- `file` 5개: 3MF(`core/parser.py`와 `utils/threemf_backend.py`는 trimesh 기하 helper), live2d(`core/*.py`), obs-studio(`core/*.py`, `utils/obs_utils.py`는 JSON helper), cc-switch(`utils/db.py`), sketch(Node.js, `src/*.js`).
- `mcp` 2개: browser(`utils/domshell_backend.py`), safari(`utils/safari_backend.py`).
- `mixed` 2개: zotero(`utils/zotero_sqlite.py`, `utils/zotero_http.py`, `core/discovery.py`), mubu(레포의 `mubu/agent-harness/mubu_probe.py`, 패키지 밖 모듈).
- `solo` 3개: web-yu-pri(`core/browser.py`), nslogger(`core/listener.py`), macrocli(`backends/`와 `core/routing.py`).

### 1.4 행동 규칙과 남은 질문 [필수]

검증 수준 표기: 개수와 소속은 AST로 전수 계산했고, 하니스를 직접 열어 읽은 범위는 2.1(d)에 있다. 직접 읽지 않은 하니스의 소속은 "휴리스틱, 미확인"이고 `추론`으로 표시한다.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 하니스를 패밀리에 배정할 때 | 기준은 "도메인 명령의 결과를 만들려고 앱·서비스를 부르는 채널"이다. 채널은 외부 프로세스 실행, HTTP 요청, MCP 서버 호출, 앱 패키지 import, 호출 없음 다섯 가지다. 로컬 파일 편집은 모든 하니스가 하는 데이터 계층이라 채널로 세지 않는다. "패밀리"는 레포 용어가 아니다. HARNESS.md Phase 1·3과 "Applying This to Other Software" 표가 같은 구분(실행 파일, WebSocket, MCP)을 보여 준다. | 추론(분류 정의는 분석자의 선택, 근거 사실은 코드 확인) |
| R-02 | 비테스트 소스가 `subprocess.run/Popen/...`로 앱이나 앱의 CLI를 실행해 도메인 결과를 만든다 | `exec` 30개: QGIS, audacity, blender, calibre, cloudcompare, dify-workflow, drawio, eez-studio, eth2-quickstart, freecad, gimp, godot, inkscape, intelwatch, joplin, kdenlive, krita, libreoffice, musescore, notebooklm, nsight-graphics, openscreen, pm2, quietshrink, sbox, shotcut, tigris, unrealinsights, videocaptioner, wavetone. 호출 대상은 앱 자체의 headless/batch 모드(blender, libreoffice, gimp)와 앱과 별개인 CLI 도구(dify-workflow, notebooklm, tigris, joplin, quietshrink, intelwatch)로 갈린다. | 코드 확인(열람 13개) / 추론(나머지 17개는 AST) |
| R-03 | 비테스트 소스가 `requests`(18개) 또는 `urllib.request`(mermaid, slay_the_spire_ii)로 서비스에 요청한다 | `http` 20개: adguardhome, anygen, chromadb, comfyui, firefly-iii, jumpserver, mailchimp, mermaid, minimax, n8n, novita, obsidian, ollama, openrefine, rms, seaclip, siyuan, slay_the_spire_ii, wiremock, zoom. 서비스는 사용자가 띄운 로컬·셀프호스트(열람한 ollama, adguardhome, seaclip, slay_the_spire_ii, openrefine. chromadb, comfyui, n8n, wiremock은 열람하지 않은 추정)와 클라우드 API(열람한 anygen, rms. 열람하지 않은 minimax, novita, mailchimp, zoom은 기본 주소 상수 기준)로 갈린다. `httpx`, `aiohttp`, `websocket(s)` import는 69개 어디에도 없다. | 코드 확인(열람 7개, 부분 확인 3개) / 추론(나머지) |
| R-04 | 비테스트 소스가 `mcp` 패키지(`ClientSession`, `stdio_client`)를 import한다 | `mcp` 2개: browser, safari. 레포 전체 `.py`에서 `import mcp`·`from mcp`는 이 둘의 `utils/*_backend.py`뿐이다. 두 하니스는 `subprocess`도 쓰지만 `npx`·`npm` 존재 점검용이다. | 코드 확인(2개 모두 열람) |
| R-05 | 비테스트 소스가 앱·서비스의 Python 패키지를 import해 in-process로 호출한다 | `sdk` 7개: cloudanalyzer(`ca`), exa(`exa_py`), iterm2(`iterm2`), lldb(`lldb`), renderdoc(`renderdoc`), unimol_tools(`unimol_tools`), rekordbox(`pyrekordbox`, `mido`). exa는 클라우드 서비스의 SDK이고 iterm2는 앱의 WebSocket API를 SDK가 감싼다. 두 경우 모두 하니스 코드는 네트워크를 직접 다루지 않는다. | 코드 확인(7개 모두 발췌 열람) |
| R-06 | 앱·서비스를 부르는 코드가 하니스 소스에 없다 | `file` 5개: 3MF(`zipfile`+`xml.etree`+trimesh), live2d(JSON·바이너리 파서), obs-studio(JSON 씬 파일), cc-switch(`sqlite3`와 JSON 설정), sketch(Node.js, `sketch-constructor`와 `jszip`으로 `.sketch` 파일 생성). 이 5개는 앱이 설치돼 있지 않아도 동작한다. | 코드 확인(발췌 열람) |
| R-07 | 읽기와 쓰기·실행이 서로 다른 채널이고 둘 다 도메인 명령이다 | `mixed` 2개. zotero는 읽기에 SQLite 읽기 전용 연결, 쓰기에 connector·Local API HTTP, 앱 기동에 `Popen`, 실험적 쓰기에 SQLite 쓰기 연결을 쓴다. mubu는 읽기에 로컬 백업·저장소·로그 파일, 쓰기에 live API HTTP(`urllib.request`)를 쓴다. | 코드 확인(zotero 채널 위치) / 추론(mubu 명령과 채널의 연결) |
| R-08 | 위 어느 패밀리의 규칙에도 맞지 않는 연결이다 | `solo` 3개. web-yu-pri는 Playwright로 실제 웹 UI를 조작한다. nslogger는 하니스가 TCP 리스너가 되어 앱이 보내는 로그를 받는다. macrocli는 7개 백엔드를 우선순위로 고르는 라우터다. | 코드 확인(3개 모두 발췌 열람) |
| R-09 | 하니스가 여러 채널의 코드를 갖고 있다 | 가용성 사전 점검(`npx`, `npm view`, `ps`), 파일 권한 설정(`icacls`), 셸 자동완성 생성(n8n), 서버 기동(openrefine `Popen`), TLS 인증서 생성(nslogger `openssl`), 하니스 자체 상태 저장(n8n `versions.db`)은 분류에 반영하지 않는다. 읽은 하니스에서 보조 사용을 이렇게 나눴고, 다른 하니스에도 같은 기준을 적용했다. | 추론 |
| R-10 | registry의 `category`와 `family`를 함께 볼 때 | 둘은 독립이다. `graphics` 카테고리 6개가 `exec` 2·`sdk` 2·`file` 2로 갈리고, `ai` 카테고리 6개가 `http` 4·`exec` 2로 갈린다. `category`는 도메인 분류이고 호출 채널을 알려 주지 않는다. | 코드 확인(교차표 계산) |
| R-11 | 하니스 디렉터리와 registry를 대조할 때 | `<sw>/agent-harness/` 디렉터리는 69개다. `registry.json`은 79항목이고, 68개는 레포 안에 디렉터리가 있다. 11개(clibrowser, hacker-feeds-cli, inkstitch, magnific, meerk40t, openwebui, palmier, stata, tinyfish, ueatelier, ve-twini)는 다른 저장소를 가리키며 이 레포에 코드가 없어 패밀리를 정하지 않는다. rekordbox는 디렉터리만 있고 registry에 없다. | 코드 확인(스크립트 대조) |
| R-12 | `exec` 백엔드가 실행 파일을 찾을 때 | 순서는 (환경변수 경로, 있는 하니스만) → `shutil.which` → OS별 설치 경로 → 못 찾으면 설치 안내(apt, brew, winget 등)를 담은 `RuntimeError`다(C-01). 환경변수 경로는 7개만 지원하고 이름이 다르다: `QGIS_PREFIX_PATH`, `FREECAD_PATH`, `GODOT_BIN`, `KRITA_PATH`, `MUSESCORE_PATH`, `SBOX_PATH`, `WAVETONE_EXE`·`WAVETONE_HOME`. `shutil.which`는 30개 중 27개가 쓰고 eth2-quickstart, intelwatch, unrealinsights는 쓰지 않는다. | 코드 확인(freecad, libreoffice, blender, gimp) / 추론(전체 수는 정규식) |
| R-13 | `exec` 백엔드가 외부 프로그램을 호출할 때 | `subprocess.run(cmd, capture_output=True, text=True, timeout=N)` 형태이고 timeout 기본값은 하니스마다 다르다(libreoffice 120초, blender 300초, gimp 120초, freecad 120초). QGIS, dify-workflow, eth2-quickstart, intelwatch, notebooklm, quietshrink, tigris 7개는 비테스트 소스에 `timeout=`이 없다. | 코드 확인(4개) / 추론(7개 목록은 정규식) |
| R-14 | `exec` 호출이 실패할 때(미설치, 비정상 종료, 타임아웃) | 전달 방식이 셋으로 갈린다. (a) 예외: libreoffice `convert`와 blender `render_scene_headless`는 종료 코드와 출력 파일을 확인하고, gimp `create_and_export`·`render_project`는 출력 파일 존재만 확인해(종료 코드는 보지 않는다) stderr·stdout 끝 500자를 담은 `RuntimeError`를 올린다. (b) 결과 dict: freecad `_run`은 미설치·타임아웃도 `{"ok": false, "returncode": -1, "stderr": ...}`로 돌려주고, eth2-quickstart `_run`은 종료 코드 127·126과 `ok: false`로 돌려준다(C-03). (c) 직접 종료: quietshrink는 `emit({"error": ...})` 후 종료 코드 1. blender `render_script`와 gimp `batch_script_fu`는 저수준에서 `returncode` dict를 돌려주고, blender의 고수준 함수는 그 값을 보고 예외를 올린다(C-02). | 코드 확인 |
| R-15 | `exec` 호출이 종료 코드 0으로 끝난다 | 기대한 출력 파일이 없으면 libreoffice와 blender는 `RuntimeError`를 올린다. gimp는 출력 파일 유무만으로 성공을 판단하므로 종료 코드 0이 아니어도 파일이 있으면 성공한다. blender는 `render0001.png` 같은 프레임 번호 접미사 후보(`0001`, `0000`, `1`)도 찾아본다. | 코드 확인(libreoffice, blender) |
| R-16 | 앱과 별개인 CLI 도구를 감싸는 `exec` 하니스 | intelwatch는 받은 인자를 그대로 `npx intelwatch`에 전달하고 `FileNotFoundError`면 안내문과 종료 코드 1로 끝낸다. quietshrink는 PATH의 `quietshrink` bash CLI와 `ffprobe`를 호출하고 못 찾으면 `ClickException`이나 `{"error": "ffprobe not found"}`를 낸다. 이 둘은 `utils/*_backend.py`가 없다. | 코드 확인 |
| R-17 | `exec` 하니스의 명령이 앱 호출 없이 끝날 수 있는가 | 명령마다 다르다. libreoffice `export`는 `odt`, `ods`, `odp`, `html`, `text` 프리셋을 앱 호출 없이 파일로 쓰고, `pdf`, `docx`, `xlsx`, `pptx`, `csv`만 ODF 중간 파일을 만든 뒤 `soffice --headless`로 변환한다. sbox는 `subprocess`를 launch·compile 명령에만 쓰고 대부분의 편집은 JSON 파일 조작이다(README의 sbox 백엔드 표기도 "direct file I/O"). 다른 `exec` 하니스도 같은지는 열람하지 않았다. | 코드 확인(libreoffice, sbox) / 미확인(나머지) |
| R-18 | `http` 백엔드가 서비스 주소와 인증을 정할 때 | 로컬·셀프호스트 서비스는 기본 주소를 코드에 둔다(ollama `http://localhost:11434`, seaclip `http://127.0.0.1:5200`, slay_the_spire_ii `http://localhost:15526`, adguardhome host `localhost`·port 3000). 클라우드 API는 키를 "CLI 인자 → 환경변수 → 설정 파일" 순서로 찾고(C-05) 없으면 입력 방법을 안내하는 `RuntimeError`를 낸다. 환경변수 이름은 `AGH_HOST`, `SEACLIP_URL`, `RMS_API_TOKEN`처럼 하니스마다 다르다. | 코드 확인(ollama, adguardhome, anygen, rms, seaclip, slay_the_spire_ii) |
| R-19 | `http` 호출이 연결 실패, HTTP 오류, 타임아웃을 만날 때 | 기본은 `RuntimeError`(slay_the_spire_ii는 하위 클래스 `ApiError`)로 감싸 서버 주소와 기동 방법을 메시지에 담는다(C-04). 변종이 있다. adguardhome은 연결 오류만 감싸고 HTTP 4xx·5xx는 `requests.HTTPError`로 올라가며, 최상위 `main()`이 `RuntimeError`와 `RequestException`을 잡아 `--json`이면 `{"error": ...}`를 출력하고 종료 코드 1로 끝낸다. seaclip은 `raise_for_status()` 예외를 감싸지 않는다. anygen과 rms는 `requests` import에 실패하면 모듈 로드 시점에 `sys.exit(1)`로 끝낸다. | 코드 확인(ollama, adguardhome, slay_the_spire_ii, seaclip, anygen, rms) |
| R-20 | `http` 대상 서비스가 꺼져 있을 때 openrefine이 서버를 띄울 수 있다 | `start_openrefine`이 PATH의 `openrefine`·`refine`·`OpenRefine`를 찾아 `Popen`으로 서버(기본 `127.0.0.1:3333`)를 띄운다. 못 찾으면 설치 안내가 담긴 `OpenRefineError`를 올린다. 서버 프로세스를 시작하는 부작용이 있다. 다른 `http` 하니스가 같은 일을 하는지는 열람하지 않았다. | 코드 확인(openrefine) / 미확인(나머지) |
| R-21 | `mcp` 하니스가 도구를 호출할 때 | 호출마다 `npx`로 MCP 서버 프로세스를 새로 띄워 `initialize` 후 `call_tool` 한 번을 부르고 닫는다(C-06). browser는 MCP 도구 `domshell_execute` 하나에 명령 문자열을 보내고 `--daemon`이면 연결을 재사용하되, daemon 호출이 실패하면 `log.warning` 후 호출마다 새 프로세스로 대체한다. safari는 도구 이름(`safari_navigate` 등)을 그대로 부른다. 호출 실패는 원인과 실행 안내(Chrome 확장, Safari 설정)를 담은 `RuntimeError`가 된다. | 코드 확인 |
| R-22 | `mcp` 하니스의 CLI 그룹이 시작할 때 | `backend.is_available()`를 호출하고(프로세스 안에서 결과를 캐시) 실패면 `--json`일 때 `{"error": <메시지>, "type": "dependency_error"}`를 출력하고 종료 코드 1로 끝낸다(C-07). safari는 macOS가 아니면, `npx`가 없으면, npm 패키지를 못 찾으면 실패하고, browser는 `npx`나 DOMShell이 없으면 실패한다. browser는 추가로 `DOMSHELL_TOKEN` 환경변수가 없으면 `RuntimeError`를 올린다. `dependency_error` 문자열은 이 두 CLI에만 있다. | 코드 확인 |
| R-23 | `sdk` 하니스의 패키지가 import되지 않을 때 | import를 `try/except ImportError`로 감싸 플래그(renderdoc `HAS_RD`, unimol `UNIMOL_AVAILABLE`)나 `is_available()`(cloudanalyzer)에 보관하고, 쓰는 시점에 설치 안내가 담긴 `RuntimeError`를 올린다(C-08). 변종: exa는 import 실패를 바로 `ImportError`로 올리고, lldb는 `lldb -P`로 모듈 경로를 찾아 `sys.path`에 넣고 재시도한 뒤에도 실패하면 `RuntimeError`를 올린다. lldb는 비-REPL 사용을 위해 `session_client.py`가 백그라운드 세션 서버 프로세스를 `Popen`으로 띄운다. | 코드 확인 |
| R-24 | `sdk` 하니스가 자격이나 연결을 점검할 때 | exa `get_client`는 `EXA_API_KEY`가 없으면 `RuntimeError`를 올린다. `check_connectivity`는 예외 대신 `{"ok": bool, "message": str}`를 돌려주고 실제 검색 1건을 호출하므로 크레딧을 쓴다(C-09). | 코드 확인 |
| R-25 | `file` 하니스의 앱 호출 여부 | obs-studio는 JSON 씬 파일을 읽고 쓸 뿐 OBS 실행, WebSocket, HTTP 호출 코드가 하니스 전체(소스·테스트·문서)에서 검색되지 않는다. HARNESS.md의 적용 표와 README의 OBS 항목은 백엔드를 `obs-websocket`이라고 쓰므로 문서와 구현이 다르다. live2d는 문서가 "Live2D Cubism Editor 없이" 동작한다고 밝힌다. | 코드 확인(검색 범위는 2.1) |
| R-26 | `mixed` 하니스가 쓰기 명령을 실행할 때 | zotero 공식 쓰기는 connector HTTP로 하고, 실험적 SQLite 쓰기는 Zotero가 실행 중(connector 응답)이면 `RuntimeError`로 막으며 읽기용 연결은 `mode=ro&immutable=1`이다. mubu `perform_*` 함수는 `execute` 기본값이 `False`라서 HTTP 호출 없이 요청 payload만 돌려주고, `execute=True`일 때만 `post_json`을 부른다. | 코드 확인(SQLite 연결 방식, `execute` 기본값) / 추론(zotero 공식 쓰기가 connector HTTP라는 점은 `ZOTERO.md` 설명) |
| R-27 | `solo` 하니스가 연결을 만들 때 | web-yu-pri는 영속 프로필로 Chromium 계열을 `msedge` → `chrome` → 번들 Chromium 순서로 시도하고 모두 실패하면 `RuntimeError`를 올린다. nslogger는 하니스가 TCP 서버를 열어 앱의 연결을 받는다. macrocli `RoutingEngine.select`는 단계가 요청한 백엔드가 쓸 수 없으면 우선순위가 높은 순으로 쓸 수 있는 백엔드를 고르고, 없으면 `RuntimeError`를 올린다. | 코드 확인 |
| R-28 | gimp `render`가 호출될 때 | GIMP가 설치돼 있고 프로젝트에 그리기 연산이 없으면 `render_project`를 시도한다. 그 안에서 어떤 예외가 나도 `except Exception: pass`로 삼키고 Pillow 경로로 진행한다. GIMP가 없거나 그리기 연산이 있어도 Pillow로 간다. Pillow도 없으면 `RuntimeError`를 올린다. HARNESS.md의 "폴백 라이브러리로 낮추지 않는다"는 규칙과 다르다. | 코드 확인 |
| R-29 | draw.io CLI가 없을 때 drawio `render_or_save`가 호출될 때 | 예외 메시지에 `not installed`가 있으면 예외를 올리지 않고 `.drawio` 파일을 쓴 뒤 `{"action": "export_fallback", ...}`를 성공 값으로 돌려준다. CLI 호출부는 반환값을 출력만 하므로 오류 종료로 이어지지 않는다. HARNESS.md의 "설치 안내와 함께 오류" 규칙과 다르다. | 코드 확인 |
| R-30 | HARNESS.md 규칙 "실제 앱이 필수 의존"과 `file` 하니스 | `file` 5개는 앱 호출 경로가 없어 이 규칙을 따르지 않는다(R-06, R-25). 규칙 문구는 "Every harness MUST follow all of them"이다. | 코드 확인 |
| R-31 | 백엔드 모듈 위치 규칙(`utils/<sw>_backend.py`)과 실제 | 이 파일을 가진 하니스는 53개이고 그중 3MF의 `threemf_backend.py`는 외부 앱 백엔드로 쓰이지 않고 trimesh 기하 helper 역할이다. 없는 16개: cc-switch(`utils/db.py`), intelwatch·quietshrink·rekordbox(`<sw>_cli.py` 안), jumpserver(`core/session.py`), live2d, macrocli(`backends/`), mailchimp(`core/client.py`), mubu(패키지 밖 `mubu_probe.py`, `setup.py`의 `py_modules`로 설치), nslogger(`core/listener.py`), obs-studio(`utils/obs_utils.py`는 JSON helper), renderdoc(`core/*.py`가 각각 import), sketch(`src/*.js`), web-yu-pri(`core/browser.py`), wiremock(`utils/client.py`), zotero(`utils/zotero_*.py`). | 코드 확인 |
| R-32 | sketch의 패키지 형태 | Node.js 패키지다(`package.json`의 `bin`, `commander`, `sketch-constructor`, `jest`). `setup.py`와 `cli_anything/` 디렉터리가 없어 Python 하니스 계약의 대상이 아니다. | 코드 확인 |
| R-33 | `guides/mcp-backend.md`와 browser 구현을 비교할 때 | 가이드는 도구마다 래퍼(`domshell_ls` 등)와 `args=["@apireno/domshell"]`을 보여 주지만 구현은 단일 도구 `domshell_execute`와 `domshell-proxy --port --token` 인자를 쓰고 토큰이 필수다. 가이드의 선택 사항인 daemon은 구현돼 있다(`--daemon`). 가이드의 `mcp>=0.1.0`은 browser의 `setup.py`와 맞고 safari는 `mcp>=1.0.0,<2.0.0`이다. | 코드 확인 |

- 불변식: `family` 7개의 개수 합은 69이고 각 하니스는 정확히 하나에 속한다(AST 스캔과 목록이 일치, 2.1(b)). 분류 기준(R-01)과 보조 채널 기준(R-09)이 바뀌면 개수가 달라진다.
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-01, R-09, R-17 | 채널 기준을 "앱을 호출하는 코드가 있는가"로 둘지 "주된 작업이 파일 편집인가"로 둘지 | 후자를 쓰면 sbox(README 표기 "direct file I/O"), inkscape(README "Direct SVG/XML manipulation"), kdenlive·shotcut(MLT XML 생성)이 `file` 쪽으로 옮겨 가 개수와 R-02가 바뀐다. 현재 스펙은 전자를 기준으로 했다. | 메인이 목적(Claude Code 생성 절차 설계)에 맞는 기준을 정한다. 필요하면 해당 하니스의 명령별 앱 호출 비율을 열람한다. |
| U-02 | R-03, R-05 | 클라우드 서비스를 SDK로 감싼 하니스(exa)를 `http`로 볼지 `sdk`로 볼지 | `http` 20 → 21, `sdk` 7 → 6이 된다. 설계 참고로는 "키 필요, 네트워크 의존" 특성이 `http`와 같다. | 기준을 "하니스 코드가 직접 쓰는 수단"(현재)과 "실제 전송 계층"(대안) 중 정한다. |
| U-03 | R-07 | `mixed`의 판정 임계: 보조 채널을 쓰는 하니스(seaclip의 SQLite 읽기 대체 경로, openrefine의 서버 기동)를 `mixed`로 볼지 | 현재는 둘 다 `http`이고 `mixed`는 2개다. 바꾸면 `mixed`가 4개로 늘어난다. | seaclip `_query_db`가 HTMX 응답 엔드포인트 대체 경로(모듈 docstring 근거)인지 명령 비중까지 열람해 정한다. |

- 확인 한계: 하니스를 실행해 보지 않았다(Windows, 외부 앱·서비스 미설치). AST는 정적 import와 호출만 본다. `importlib` 동적 import와 문자열로 조립한 명령은 놓친다. 분류에 쓴 스캔 스크립트는 임시 파일이라 레포와 `artifacts/`에 두지 않았다. 외부 앱의 실제 CLI 동작(예: `lldb -P` 출력)은 확인하지 않았다.

### 1.5 필수 코드 참조 [필수]

라이선스는 Apache 2.0(overview 1절)이라 인용이 허용된다. 아래는 구현자가 다시 쓰기에 글보다 코드가 짧고 자기완결적인 패턴이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `libreoffice/agent-harness/cli_anything/libreoffice/utils/lo_backend.py:45-82` `find_libreoffice` | 실행 파일 탐색 순서(PATH → Windows 경로 → macOS 번들 → 설치 안내 `RuntimeError`). 표준 라이브러리만 쓴다. 환경변수 단계는 freecad의 `find_freecad`(`freecad/agent-harness/cli_anything/freecad/utils/freecad_backend.py:54-124`)에 있다. | R-12 |
| C-02 | `blender/agent-harness/cli_anything/blender/utils/blender_backend.py:14-126` `find_blender`, `render_script`, `render_scene_headless` | 저수준은 `returncode` dict, 고수준은 returncode 확인·출력 파일 확인 후 `RuntimeError`. 표준 라이브러리만 쓴다. | R-14, R-15 |
| C-03 | `freecad/agent-harness/cli_anything/freecad/utils/freecad_backend.py:132-178` `_run` | 미설치·타임아웃을 `ok: false` dict로 돌려주는 방식. 표준 라이브러리만 쓴다. | R-14 |
| C-04 | `ollama/agent-harness/cli_anything/ollama/utils/ollama_backend.py:11-54` `DEFAULT_BASE_URL`, `api_get` | 연결 실패·HTTP 오류·타임아웃을 `RuntimeError`로 감싸는 `http` 호출. `api_post`(56-)와 같은 구조다. | R-18, R-19 |
| C-05 | `anygen/agent-harness/cli_anything/anygen/utils/anygen_backend.py:30-70` `CONFIG_FILE`, `ENV_API_KEY`, `load_config`, `get_api_key` | 키 탐색 순서 "CLI 인자 → 환경변수 `ANYGEN_API_KEY` → `~/.config/anygen/config.json`". 범위 안의 상수와 `load_config`가 같은 범위에 들어 있다. | R-18 |
| C-06 | `safari/agent-harness/cli_anything/safari/utils/safari_backend.py:20-106` `DEFAULT_SERVER_*`, `is_available`, `_call_tool` | 가용성 점검(플랫폼, `npx`, npm 패키지)과 호출마다 MCP 서버를 띄우는 호출. | R-21 |
| C-07 | `safari/agent-harness/cli_anything/safari/safari_cli.py:193-216` `cli` 그룹 콜백 | `is_available()` 캐시와 `dependency_error` 출력, 종료 코드 1. | R-22 |
| C-08 | `renderdoc/agent-harness/cli_anything/renderdoc/core/capture.py:20-34` `HAS_RD`, `_require_rd` | `sdk` import 가드와 사용 시점 `RuntimeError`. | R-23 |
| C-09 | `exa/agent-harness/cli_anything/exa/utils/exa_backend.py:21-56` `get_client`, `check_connectivity` | 자격 누락 `RuntimeError`와 연결 점검의 `{"ok", "message"}` 반환. | R-24 |
| C-10 | `gimp/agent-harness/cli_anything/gimp/core/export.py:54-84` `render` | 예외를 삼키고 Pillow로 넘어가는 fallback. 원본 동작 기록용이다. | R-28 |
| C-11 | `drawio/agent-harness/cli_anything/drawio/core/export.py:110-130` `render_or_save` | `not installed` 오류를 `export_fallback` 성공 값으로 바꾸는 분기. | R-29 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 하니스를 실행하지 않았고 코드에서 기대 결과를 읽었다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-09 | 가상의 하니스가 `requests`로 서비스를 부르고 `shutil.which("npx")`로 사전 점검만 한다 | `http`. 사전 점검은 분류에 반영하지 않는다. |
| T-02 | R-04, R-09 | browser: `mcp` import와 `subprocess.run(["npx", ...])`가 모두 있다 | `mcp`. `subprocess`는 `npx` 점검용이다. |
| T-03 | R-17, R-14 | LibreOffice가 없는 환경에서 `odt` 프리셋과 `pdf` 프리셋으로 각각 `export` | `odt`는 앱 호출 없이 파일이 생기고, `pdf`는 `RuntimeError("LibreOffice is not installed. ...")`가 올라와 `--json`이면 `{"error": ..., "type": "RuntimeError"}`가 출력된다. |
| T-04 | R-28 | GIMP가 설치돼 있고 프로젝트에 그리기 연산이 있다. 또는 GIMP도 Pillow도 없다 | 앞 경우는 Pillow 경로로 렌더하고 성공을 돌려준다. 뒤 경우는 `RuntimeError("Neither GIMP nor Pillow is available. ...")`. |
| T-05 | R-19 | AdGuardHome 서버가 꺼진 채 `--json`으로 명령 실행 | stdout에 `{"error": "Cannot connect to AdGuardHome at ..."}`가 한 줄 출력되고 종료 코드 1. |
| T-06 | R-22 | macOS가 아닌 환경에서 safari CLI를 `--json`으로 실행 | `{"error": "Safari MCP only supports macOS. Detected non-Darwin platform.", "type": "dependency_error"}`가 출력되고 종료 코드 1. |
| T-07 | R-14 | freecad 호출이 timeout을 넘긴다(기본 `_run` timeout 120초) | 예외 없이 `{"ok": false, "returncode": -1, "stderr": "FreeCAD process timed out after 120s", ...}`가 반환된다. |
| T-08 | R-24 | `EXA_API_KEY`가 비어 있을 때 `check_connectivity()` | 예외 없이 `{"ok": False, "message": "EXA_API_KEY environment variable is not set. ..."}`가 반환된다. |
| T-09 | R-29 | draw.io CLI가 없는 환경에서 `export render out.png` | 오류 종료 없이 `out.drawio`가 쓰이고 `{"action": "export_fallback", ...}`가 출력된다. `out.png`는 생기지 않는다. |
| T-10 | R-26 | mubu `perform_create_child(..., execute=False)` | HTTP 호출 없이 `{"execute": False, "request": ...}`를 돌려준다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

**(a) R-ID별 근거**

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `cli-anything-plugin/HARNESS.md:14-21` Phase 1 항목 1·4, `cli-anything-plugin/HARNESS.md:54-66` Phase 3 항목 4, `cli-anything-plugin/HARNESS.md:715-724` 적용 표, `cli-anything-plugin/guides/mcp-backend.md:5-12` | "패밀리" 부재는 `grep -rniE "famil" README.md cli-anything-plugin/HARNESS.md cli-anything-plugin/README.md registry.json` 결과 0건(기준 SHA, 범위는 이 4개 파일, 다른 문서는 안 봄). 분류 기준은 분석자의 선택이라 `추론`이다. |
| R-02 | 열람: C-01, C-02, C-03, C-10, C-11, `eth2-quickstart/agent-harness/cli_anything/eth2_quickstart/utils/eth2qs_backend.py:15-49`, `intelwatch/agent-harness/cli_anything/intelwatch/intelwatch_cli.py:18-29`, `quietshrink/agent-harness/cli_anything/quietshrink/quietshrink_cli.py:18-31`, `sbox/agent-harness/cli_anything/sbox/utils/sbox_backend.py:144-170` | 30개 목록은 AST 스캔(2.1(b)) 결과와 `subprocess` 호출이 있는 파일로 확정했다. 열람 13개는 2.1(d). 나머지 17개는 소속만 AST이고 본문은 읽지 않았다. 호출 대상 구분(앱 자체 vs 별개 CLI)은 열람한 하니스와 README 백엔드 열로만 확인했다. |
| R-03 | C-04, `adguardhome/agent-harness/cli_anything/adguardhome/utils/adguardhome_backend.py:1-71`, `anygen/agent-harness/cli_anything/anygen/utils/anygen_backend.py:1-30`, `slay_the_spire_ii/agent-harness/cli_anything/slay_the_spire_ii/utils/sts2_backend.py:1-62`, `seaclip/agent-harness/cli_anything/seaclip/utils/seaclip_backend.py:1-47` | `httpx|aiohttp|websocket` 부재는 2.1(b)의 검색. `requests` 18개와 `urllib.request` 2개는 AST로 센 값이다. 로컬 vs 클라우드 구분은 열람한 하니스에서만 확인했다. |
| R-04 | `browser/agent-harness/cli_anything/browser/utils/domshell_backend.py:25-30`, `safari/agent-harness/cli_anything/safari/utils/safari_backend.py:13-18`, `browser/agent-harness/cli_anything/browser/utils/domshell_backend.py:93-109` `_check_npx*` | 전칭 "mcp는 2개뿐"은 2.1(b)의 grep. 놓칠 수 있는 경우: `importlib`, Node 하니스(sketch)의 MCP 사용(`package.json` 의존성에는 없음). |
| R-05 | `exa/agent-harness/cli_anything/exa/utils/exa_backend.py:13-18`, `iterm2/agent-harness/cli_anything/iterm2_ctl/utils/iterm2_backend.py:34-42`, `unimol_tools/agent-harness/cli_anything/unimol_tools/utils/unimol_backend.py:7-11`, `renderdoc/agent-harness/cli_anything/renderdoc/core/capture.py:20-26`, `cloudanalyzer/agent-harness/cli_anything/cloudanalyzer/utils/ca_backend.py:1-30`, `lldb/agent-harness/cli_anything/lldb/utils/lldb_backend.py:22-66`, `rekordbox/agent-harness/cli_anything/rekordbox/rekordbox_cli.py:49-51` | iterm2의 "WebSocket을 SDK가 감싼다"는 `iterm2_backend.py:73-85`의 주석·오류 메시지 근거이고 SDK 내부 구현은 보지 않았다(추론). cloudanalyzer는 `ca_backend.py:1`의 docstring이 "direct Python import (no subprocess needed)"라고 밝힌다. |
| R-06 | `3MF/agent-harness/cli_anything/threemf/core/parser.py:10-18`, `obs-studio/agent-harness/cli_anything/obs_studio/utils/obs_utils.py:1-8`, `obs-studio/agent-harness/cli_anything/obs_studio/core/project.py:103-108`, `cc-switch/agent-harness/cli_anything/ccswitch/utils/db.py:31-36`, `live2d/agent-harness/LIVE2D.md:5-7`, `sketch/agent-harness/package.json` | live2d는 소스 전체를 읽지 않고 문서 선언과 `core/*.py` import 목록(AST)으로 판단했다(추론 일부). sketch는 `package.json`·README·`src/builder.js` import로 판단했고 `src/*.js`는 AST 대상이 아니다. |
| R-07 | `zotero/agent-harness/cli_anything/zotero/utils/zotero_sqlite.py:25-40`, `zotero/agent-harness/cli_anything/zotero/core/discovery.py:51-58`, `zotero/agent-harness/cli_anything/zotero/core/experimental.py:9-11`, `mubu/agent-harness/mubu_probe.py:149-174`, `mubu/agent-harness/mubu_probe.py:806-838`, `mubu/agent-harness/setup.py:35` | zotero 공식 쓰기가 connector HTTP로 간다는 점은 `ZOTERO.md`의 설명과 `zotero_http` import로 확인했고 각 명령의 호출 경로는 따라가지 않았다. mubu의 "읽기는 파일" 부분은 `MUBU.md` 설명이고 `load_collection_records`(239행) 존재만 확인했다(추론). |
| R-08 | `web-yu-pri/agent-harness/cli_anything/web_yu_pri/core/browser.py:61-104`, `nslogger/agent-harness/cli_anything/nslogger/core/listener.py:1-30`, `macrocli/agent-harness/cli_anything/macrocli/core/routing.py:41-114` | macrocli는 `MACROCLI.md`의 백엔드 표(7개, 우선순위 100·80·75·70·60·50·10)와 `routing.py` 생성자의 백엔드 7개가 일치한다. 각 백엔드 내부는 읽지 않았다. nslogger는 리스너 파일 앞부분만 읽었다. |
| R-09 | `browser/agent-harness/cli_anything/browser/utils/domshell_backend.py:93-109`, `safari/agent-harness/cli_anything/safari/utils/safari_backend.py:33-55`, `iterm2/agent-harness/cli_anything/iterm2_ctl/core/session.py:301-314`, `n8n/agent-harness/cli_anything/n8n/n8n_cli.py:461-473`, `n8n/agent-harness/cli_anything/n8n/core/versions.py:1-30`, `openrefine/agent-harness/cli_anything/openrefine/utils/openrefine_backend.py:176-183`, `nslogger/agent-harness/cli_anything/nslogger/core/listener.py:38-50`, `zoom/agent-harness/cli_anything/zoom/utils/zoom_backend.py:39-53` | 보조 사용으로 본 호출은 위 위치에서 읽었다. "보조"라는 판정 자체가 `추론`이다. 아직 읽지 않은 하니스에도 같은 기준을 적용했다. |
| R-10 | `registry.json`의 `clis[].category`, 위 R-02~R-08 소속 | 교차표는 TSV `registry_category` 열과 이 스펙 소속으로 계산했다(임시 스크립트). `scientific`·`science`, `game`·`gamedev`, `knowledge`·`knowledge-management`가 따로 존재하는 점은 registry-schema 스펙의 관심사다. |
| R-11 | `registry.json`의 `clis` 79항목(`source_url`, `install_cmd`) | 이름을 소문자·`-`·`_` 제거로 정규화해 `*/agent-harness/` 디렉터리 69개와 대조했다. 11개는 `install_cmd`가 `pip install git+https://github.com/<다른 저장소>`·`cargo install --git ...`이다(clibrowser는 `cargo`). 레포 안에 구현이 없으므로 코드로 분류하지 않았다. |
| R-12 | C-01, `freecad/agent-harness/cli_anything/freecad/utils/freecad_backend.py:54-124`, `blender/agent-harness/cli_anything/blender/utils/blender_backend.py:14-24`, `gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py:25-34`, `QGIS/agent-harness/cli_anything/qgis/utils/qgis_backend.py:46-66`, `godot/agent-harness/cli_anything/godot/utils/godot_backend.py:41`, `krita/agent-harness/cli_anything/krita/utils/krita_backend.py:65`, `musescore/agent-harness/cli_anything/musescore/utils/musescore_backend.py:33`, `sbox/agent-harness/cli_anything/sbox/utils/sbox_backend.py:44`, `wavetone/agent-harness/cli_anything/wavetone/utils/wavetone_backend.py:31-34` | 환경변수 7개와 `shutil.which` 27개는 정규식 스캔 결과다. 탐색 순서 본문은 freecad·libreoffice·blender·gimp 네 개만 읽었다. 정규식이 놓친 환경변수 패턴(예: 설정 파일로 경로를 받는 경우)이 있을 수 있다. |
| R-13 | `libreoffice/agent-harness/cli_anything/libreoffice/utils/lo_backend.py:249-254`, `blender/agent-harness/cli_anything/blender/utils/blender_backend.py:56-60`, `freecad/agent-harness/cli_anything/freecad/utils/freecad_backend.py:132-148` | `timeout=`이 없는 7개는 그 하니스의 비테스트 `.py` 전체에서 `timeout\s*=` 정규식이 0건인 경우다. 호출 인자가 없다는 뜻이 아니라 코드에 이 문자열이 없다는 뜻이다. |
| R-14 | C-02, C-03, `libreoffice/agent-harness/cli_anything/libreoffice/utils/lo_backend.py:279-292`, `eth2-quickstart/agent-harness/cli_anything/eth2_quickstart/utils/eth2qs_backend.py:15-49`, `quietshrink/agent-harness/cli_anything/quietshrink/quietshrink_cli.py:93-97`, `gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py:47-74`, `gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py:138-146`, `gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py:431-439` | 세 방식의 분포(몇 개가 예외인지, dict인지)는 열람한 7개에서만 확인했다. 전체 분포는 모른다. |
| R-15 | `libreoffice/agent-harness/cli_anything/libreoffice/utils/lo_backend.py:286-292`, `blender/agent-harness/cli_anything/blender/utils/blender_backend.py:100-118`, `gimp/agent-harness/cli_anything/gimp/utils/gimp_backend.py:138-146` | libreoffice는 macOS에서 직접 호출이 실패하면 `open -W -n -a` 재시도 경로가 있다(`lo_backend.py:259-277`). 이 재시도는 이 스펙의 범위 밖이라 규칙에 넣지 않았다. |
| R-16 | `intelwatch/agent-harness/cli_anything/intelwatch/intelwatch_cli.py:18-29`, `quietshrink/agent-harness/cli_anything/quietshrink/quietshrink_cli.py:18-31`, `quietshrink/agent-harness/cli_anything/quietshrink/quietshrink_cli.py:111-114` | dify-workflow, notebooklm, tigris, joplin도 별개 CLI를 감싼다는 점은 파일 머리 docstring·함수 이름(`require_dify_workflow_command`)과 README 백엔드 열("NotebookLM CLI wrapper", "Wrapper around the open-source dify-workflow CLI", "subprocess wrapping the official tigris CLI", "Joplin terminal CLI subprocess")로 확인했다. 본문은 읽지 않았다. |
| R-17 | `libreoffice/agent-harness/cli_anything/libreoffice/core/export.py:18-31`, `libreoffice/agent-harness/cli_anything/libreoffice/core/export.py:119-150`, `sbox/agent-harness/cli_anything/sbox/utils/sbox_backend.py:144-170`, `README.md:1328`, `libreoffice/agent-harness/cli_anything/libreoffice/utils/lo_backend.py:191-294` | sbox의 "대부분 편집은 JSON 파일 조작"은 `sbox_cli.py`에서 `sbox_backend.` 호출이 launch·compile·find 위치(1604, 1616, 1703, 2127, 2207, 2239행 등)에만 보이는 것과 README 표기로 판단했다(추론). 다른 `exec` 하니스는 확인하지 않았다. |
| R-18 | C-05, `ollama/agent-harness/cli_anything/ollama/utils/ollama_backend.py:10-11`, `seaclip/agent-harness/cli_anything/seaclip/utils/seaclip_backend.py:15-24`, `slay_the_spire_ii/agent-harness/cli_anything/slay_the_spire_ii/utils/sts2_backend.py:15-20`, `rms/agent-harness/cli_anything/rms/utils/rms_backend.py:16-17`, `adguardhome/agent-harness/cli_anything/adguardhome/core/project.py:31-34` | 환경변수 이름 비통일은 위 하니스와 2.1 앞 grep에서 본 이름(`SIYUAN_HOST`, `WIREMOCK_HOST`, `FIREFLY_III_BASE_URL`, `MAILCHIMP_API_KEY` 등)을 비교한 결과다. 20개 전수는 아니다. |
| R-19 | C-04, `adguardhome/agent-harness/cli_anything/adguardhome/utils/adguardhome_backend.py:36-53`, `adguardhome/agent-harness/cli_anything/adguardhome/adguardhome_cli.py:87-98`, `slay_the_spire_ii/agent-harness/cli_anything/slay_the_spire_ii/utils/sts2_backend.py:12-62`, `seaclip/agent-harness/cli_anything/seaclip/utils/seaclip_backend.py:33-46`, `anygen/agent-harness/cli_anything/anygen/utils/anygen_backend.py:18-25`, `rms/agent-harness/cli_anything/rms/utils/rms_backend.py:8-14` | seaclip의 `_get`이 감싸지 않는다는 점은 `raise_for_status()` 호출 주변에 `try/except`가 없는 것을 읽었다. 이 예외를 CLI 계층이 잡는지는 확인하지 않았다. |
| R-20 | `openrefine/agent-harness/cli_anything/openrefine/utils/openrefine_backend.py:168-183` | zotero의 `launch_zotero`(`zotero/agent-harness/cli_anything/zotero/core/discovery.py:51-58`)도 서버 기동이지만 `mixed`로 분류했다. "다른 `http` 하니스는 기동하지 않는다"는 주장은 하지 않는다. |
| R-21 | C-06, `browser/agent-harness/cli_anything/browser/utils/domshell_backend.py:497-610`, `browser/agent-harness/cli_anything/browser/utils/domshell_backend.py:571-575` | safari의 `call`(110-140행)은 도구 이름을 그대로 넘긴다. browser daemon 경로의 asyncio 한계는 원본 주석에 "Known limitation"으로 적혀 있다(`domshell_backend.py:608-612`). |
| R-22 | C-07, `browser/agent-harness/cli_anything/browser/browser_cli.py:105-133`, `safari/agent-harness/cli_anything/safari/utils/safari_backend.py:58-85`, `browser/agent-harness/cli_anything/browser/utils/domshell_backend.py:43-58` | "`dependency_error` 문자열은 이 두 CLI에만 있다"는 `grep -rln dependency_error --include=*.py */agent-harness`(테스트 제외 결과) 2건이다. 문서·Node 코드는 검색하지 않았다. |
| R-23 | C-08, `cloudanalyzer/agent-harness/cli_anything/cloudanalyzer/utils/ca_backend.py:13-30`, `unimol_tools/agent-harness/cli_anything/unimol_tools/utils/unimol_backend.py:7-12`, `unimol_tools/agent-harness/cli_anything/unimol_tools/utils/unimol_backend.py:37-43`, `exa/agent-harness/cli_anything/exa/utils/exa_backend.py:13-18`, `lldb/agent-harness/cli_anything/lldb/utils/lldb_backend.py:22-66`, `lldb/agent-harness/cli_anything/lldb/utils/session_client.py:118-131` | lldb 세션 서버의 소켓 프로토콜은 읽지 않았다(`session_server.py`가 `socket`을 import하는 것만 확인). |
| R-24 | C-09, `exa/agent-harness/cli_anything/exa/utils/exa_backend.py:41-56` | exa 크레딧 소모는 함수 docstring의 주석("uses 1 search credit")이 근거다. 실제 과금은 확인하지 않았다(미확인). |
| R-25 | `obs-studio/agent-harness/cli_anything/obs_studio/utils/obs_utils.py:1-8`, `obs-studio/agent-harness/cli_anything/obs_studio/core/project.py:96-108`, `cli-anything-plugin/HARNESS.md:723`, `README.md:1181`, `live2d/agent-harness/LIVE2D.md:5-7` | 부재 주장: `grep -rniE "subprocess|websocket|obs64|shutil.which|requests|urllib" obs-studio/agent-harness`가 0건(소스·테스트·문서 포함, 기준 SHA). 놓칠 가능성: `socket`을 직접 열거나 `os.system`을 쓰는 경우(이 패턴은 검색에 없었다, AST에서는 비테스트 소스에 `subprocess`·`socket` import 없음). |
| R-26 | `zotero/agent-harness/cli_anything/zotero/utils/zotero_sqlite.py:25-40`, `zotero/agent-harness/cli_anything/zotero/core/experimental.py:9-11`, `mubu/agent-harness/mubu_probe.py:1377-1388`, `mubu/agent-harness/mubu_probe.py:1389-1402` | zotero에서 "공식 쓰기는 connector"는 `ZOTERO.md` 설명 근거다(추론). mubu `perform_text_update`·`perform_delete_node`도 같은 `execute=False` 기본값이다(`mubu_probe.py:1350-1359`, `:1430-1438`에서 시그니처 확인, 본문 일부만 읽음). |
| R-27 | `web-yu-pri/agent-harness/cli_anything/web_yu_pri/core/browser.py:61-104`, `macrocli/agent-harness/cli_anything/macrocli/core/routing.py:59-87`, `nslogger/agent-harness/cli_anything/nslogger/core/listener.py:1-30` | nslogger 서버가 실제로 `bind`·`accept`하는 위치는 열람하지 않았다. 파일 docstring과 `socket`·`ssl` import로 판단했다(추론). |
| R-28 | C-10, `gimp/agent-harness/cli_anything/gimp/core/export.py:96-103`, `README.md:1076`, `cli-anything-plugin/HARNESS.md:485-488` | README의 GIMP 백엔드 표기("Pillow + GEGL/Script-Fu")는 구현과 맞고 HARNESS.md 규칙과 다르다. 문서끼리도 다르다. |
| R-29 | C-11, `drawio/agent-harness/cli_anything/drawio/drawio_cli.py:524-538`, `drawio/agent-harness/cli_anything/drawio/utils/drawio_backend.py:20-37` | `render_or_save`는 메시지 문자열(`"not installed"`)로 분기하므로 `drawio_backend.py:36`의 문구가 바뀌면 fallback이 발동하지 않는다. 이 문자열 결합은 코드 확인이다. |
| R-30 | `cli-anything-plugin/HARNESS.md:480-488`, R-06·R-25의 근거들 | 규칙 문구 "These are non-negotiable. Every harness MUST follow all of them."은 `cli-anything-plugin/HARNESS.md:482`이고 "실제 앱 필수"는 485-488행이다. |
| R-31 | 2.1(b)의 `ls` 스크립트 결과, `mubu/agent-harness/setup.py:35`, `nsight-graphics/agent-harness/cli_anything/nsight_graphics/utils/nsight_graphics_backend.py`, `joplin/agent-harness/cli_anything/joplin/core/backend.py` | "53개 중 3MF의 파일은 앱 백엔드가 아니다"는 `threemf_backend.py` 머리 docstring("trimesh / numpy integration")을 읽은 결과다. |
| R-32 | `sketch/agent-harness/package.json` | `git ls-files sketch/agent-harness`에 `setup.py`와 `cli_anything/`가 없다. |
| R-33 | `cli-anything-plugin/guides/mcp-backend.md:14-43`, `cli-anything-plugin/guides/mcp-backend.md:51-59`, `browser/agent-harness/cli_anything/browser/utils/domshell_backend.py:497-600`, `browser/agent-harness/setup.py:37`, `safari/agent-harness/setup.py:41` | 가이드가 보여 주는 코드는 예시(`...` 생략 포함)라서 차이가 결함이라는 뜻은 아니다. |
| T-01~T-10 | 각 사례의 R-ID 근거 | 모두 코드에서 기대값을 읽었고 실행하지 않았다. T-03의 `"type": "RuntimeError"`는 `libreoffice_cli.py:97-99`의 `type(e).__name__` 근거다. T-06의 메시지는 `safari_backend.py:58-67`과 `safari_cli.py:206-214` 조합이다. |

**(b) 전칭·부재 주장의 검색 범위** (기준 SHA, 레포 루트, 임시 스크립트와 명령은 레포·`artifacts/`에 두지 않았다)

| 주장 | 명령·범위 | 놓칠 수 있는 경우 |
|---|---|---|
| `mcp` import는 browser·safari뿐 | `grep -rn "import mcp\|from mcp" --include=*.py .` 결과에서 `browser/`·`safari/` 경로를 뺀 결과 0건 | `importlib` 동적 import, Node 코드 |
| `httpx`·`aiohttp`·`websocket(s)` import 없음 | `grep -rnE "^\s*(import|from)\s+(websocket\|websockets\|httpx\|aiohttp)" --include=*.py */agent-harness` 0건 | 함수 안에서 문자열로 만든 import |
| obs-studio에 앱 호출 없음 | R-25의 grep 0건 | `socket`·`os.system` 직접 사용(AST상 비테스트 소스에서 import 없음으로 보완) |
| `dependency_error`는 browser·safari CLI뿐 | `grep -rln dependency_error --include=*.py */agent-harness`에서 `tests/` 제외 2건 | 문자열 조합으로 만든 오류 타입 |
| 패밀리 소속·개수 | 비테스트 `.py`에 Python `ast`로 import·`subprocess.*` 호출 수집. 제외: `tests/`, `test/`, `node_modules/`, `eval/`, `_codegen/` 디렉터리와 `test_*.py`, `setup.py`, `repl_skin.py`, `skill_generator.py`. 69개 모두 대상이고 sketch(JS)는 0파일이라 별도 판단했다. audacity `file_io.py`는 BOM 때문에 파싱 실패했다(영향 없음, `subprocess`는 `sox_backend.py`에서 잡혔다). | 동적 import, `eval` 디렉터리 안의 코드, JS 하니스 |
| `utils/*_backend.py` 53개 / 16개 | `for d in */agent-harness; do ls $d/cli_anything/*/utils/*_backend.py; done` | `utils/` 밖의 `*_backend.py`(R-31에 목록) |
| `exec` 27개 `shutil.which`, 7개 `timeout=` 없음, 7개 환경변수 | 비테스트 `.py`에서 `shutil\.which\(`, `timeout\s*=`, 환경변수 이름 패턴(`PATH|BIN|EXE|HOME`로 끝나는 `os.environ.get`, `*backend*` 파일만) 정규식 | 다른 이름의 환경변수, 설정 파일 경로 |
| registry 79 = 68 + 11 | `registry.json`의 `clis[].name`을 소문자·`-`·`_` 제거로 정규화해 `agent-harness` 디렉터리와 대조 | 이름 규칙이 다른 항목 |

**(c) TSV 수정 제안** ([harness-catalog.tsv](../../../artifacts/CLI-Anything/harness-catalog.tsv)는 고치지 않았다)

TSV의 `backend_tags` 열은 소스 문자열 존재만 본 휴리스틱이라 24행에서 이 스펙의 `family`와 주된 채널이 다르다. 원인은 문서·테스트·docstring의 단어 일치, 보조 호출(사전 점검, 권한 설정), Python 밖 하니스(sketch)다. 아래는 제안이고 원인 열은 소스 위치를 열어 본 것과 추론을 구분했다.

권장: `family` 열을 추가하고 `backend_tags`는 보조 채널 표시용으로 남긴다.

| dir | 현재 tag | 제안 `family` | 이유 |
|---|---|---|---|
| 3MF | `-` | `file` | `core/parser.py`가 `zipfile`·`xml.etree`로 3MF 파일을 읽고 trimesh로 기하를 계산한다. 앱 호출 없음. |
| exa | `-` | `sdk` | `exa_py` SDK를 import한다(`exa_backend.py:11-18`). |
| live2d | `-` | `file` | 모델 파일 파서 중심이고 앱 호출 코드 없음. |
| mubu | `-` | `mixed` | `mubu_probe.py`가 패키지 밖 모듈이라 스캔 범위에서 빠졌다. `urllib.request` live API와 로컬 파일을 쓴다. |
| obs-studio | `-` | `file` | JSON 씬 파일만 조작한다(R-25). |
| renderdoc | `-` | `sdk` | `core/*.py`가 `import renderdoc`을 한다. |
| sketch | `-` | `file` | Node.js 하니스라 Python 스캔 범위 밖이다. `sketch-constructor`로 파일을 만든다. |
| unimol_tools | `-` | `sdk` | `unimol_tools`를 import한다. |
| web-yu-pri | `-` | `solo` | Playwright로 웹 UI를 조작한다. |
| cc-switch | `http+mcp+sqlite` | `file` | `sqlite3`만 import한다. `mcp`는 관리 대상 데이터(MCP 서버 목록)이고 `http`는 URL 문자열(원인은 추론, `ccswitch_cli.py:513`, `:559`에서 단어 위치 확인). |
| minimax | `http+ws` | `http` | `websocket`은 API 카탈로그 메타데이터 문자열이고 import가 없다(`minimax_backend.py:92`, `:151`). |
| cloudanalyzer | `subprocess` | `sdk` | `ca_backend.py:1`이 "no subprocess needed"라고 쓴 docstring에서 단어가 잡혔다(추론). 실제는 `ca` 패키지 import. |
| lldb | `subprocess` | `sdk` | `lldb` 바인딩 import가 주 경로이고 `subprocess`는 모듈 경로 탐색과 세션 서버 기동이다. |
| rekordbox | `subprocess` | `sdk` | `pyrekordbox`·`mido`를 쓰고 `subprocess`는 프로세스 점검(`ps`, `pgrep`)이다. registry에 항목이 없어 `registry_category`가 `?`다. |
| macrocli | `subprocess` | `solo` | 7개 백엔드 라우터가 본체이고 `native_api` 백엔드만 `subprocess`다. |
| freecad | `subprocess+http` | `exec` | `http`는 `core/measure.py:6`의 단어 "requests" 일치로 보인다(추론). import 없음. |
| openrefine | `subprocess+http` | `http` | `subprocess`는 서버 기동(`openrefine_backend.py:176-183`). |
| siyuan | `subprocess+http` | `http` | `subprocess`는 `siyuan_backend.py:9`의 import뿐이고 호출이 없으며 테스트 파일에도 있다. |
| zoom | `subprocess+http` | `http` | `subprocess`는 Windows 권한 설정(`icacls`, `zoom_backend.py:47`). |
| n8n | `subprocess+http+mcp+sqlite` | `http` | `subprocess`는 셸 자동완성(`n8n_cli.py:461-473`), `sqlite`는 자체 버전 저장소(`core/versions.py`), `mcp`는 `core/fixers.py:3`의 docstring 단어다. |
| browser | `subprocess+mcp` | `mcp` | `subprocess`는 `npx` 점검(R-04). |
| safari | `subprocess+mcp` | `mcp` | `subprocess`는 `npm view`(R-04). |
| iterm2 | `subprocess+ws` | `sdk` | `iterm2` 패키지 import. `subprocess`는 `ps`(`iterm2/agent-harness/cli_anything/iterm2_ctl/core/session.py:301-314`), `ws`는 오류 메시지 문자열. |
| nslogger | `subprocess+ws` | `solo` | TCP 리스너(`socket`, `zeroconf`)이고 `subprocess`는 `openssl`. |

변경 없음으로 두는 행(주된 채널과 tag가 같다): `subprocess` 29행(exec), `http` 14행, `http+sqlite` seaclip(`http` 주 + SQLite 읽기 대체), `subprocess+http+sqlite` zotero(`mixed`).

**(d) 직접 열람 범위** (이 범위 밖은 AST 소속만 확인, "휴리스틱, 미확인")

| family | 직접 열람(파일 일부를 읽음) | AST만 |
|---|---|---|
| `exec` 30 | libreoffice, blender, gimp, freecad, eth2-quickstart, intelwatch, quietshrink, drawio, QGIS, sbox, joplin(fallback 주석), dify-workflow(함수 목록), notebooklm(머리 docstring) | audacity, calibre, cloudcompare, eez-studio, godot, inkscape, kdenlive, krita, musescore, nsight-graphics, openscreen, pm2, shotcut, tigris, unrealinsights, videocaptioner, wavetone |
| `http` 20 | adguardhome, ollama, anygen, rms, slay_the_spire_ii, seaclip, openrefine(주요 메서드 목록), zoom(머리), minimax(일부), n8n(일부) | chromadb, comfyui, firefly-iii, jumpserver, mailchimp, mermaid, novita, obsidian, siyuan, wiremock |
| `sdk` 7 | exa, iterm2, unimol_tools, renderdoc, cloudanalyzer, lldb, rekordbox (모두 발췌) | 없음 |
| `file` 5 | 3MF, obs-studio, cc-switch, live2d(문서·import), sketch(README·package.json) | 없음 |
| `mcp` 2 | browser, safari | 없음 |
| `mixed` 2 | zotero, mubu | 없음 |
| `solo` 3 | web-yu-pri, nslogger(머리), macrocli(문서·routing) | 없음 |

### 2.2 코드 읽는 순서 [선택]

`cli-anything-plugin/HARNESS.md:54-66`(백엔드 모듈이 하는 일)과 `:715-724`(앱별 백엔드 표) → `exec`의 대표 `libreoffice/.../utils/lo_backend.py`(C-01, 호출·오류 전체)와 `libreoffice/.../core/export.py`(명령별로 앱을 부르는지) → 오류가 사용자에게 가는 곳 `libreoffice/agent-harness/cli_anything/libreoffice/libreoffice_cli.py:86-110` → `http` 대표 `ollama/.../ollama_backend.py`(C-04) → `mcp` 대표 `safari`(C-06, C-07) → `sdk`는 C-08, C-09 → 규칙과 다른 곳은 C-10, C-11과 R-25.

### 2.4 검토 기록 [필수, ready 스펙]

`draft` 스펙이라 아직 해당 없음. 작성자 자체 점검만 했다: `python scripts/check.py CLI-Anything`로 인용 줄 범위와 링크를 확인한다. 원본 대조 점검은 메인 세션 몫이다.

## 적용 메모 [선택]

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-30 | 새 하니스 생성 절차 맨 앞에 "이 앱을 어떤 채널로 부를 것인가"를 묻는 단계를 두고, `file`(앱 호출 없음)을 고르면 사유를 기록한다 | 원본 HARNESS.md는 채널 선택 단계가 없고 앱 필수 규칙을 모든 하니스에 요구하지만 5개가 따르지 않는다 | 생성 절차에 채널 선택 질문이 추가되고 채널이 템플릿(`exec`, `http`, `sdk`, `mcp`)을 고른다 |
| R-14, R-19 | 백엔드는 실패를 항상 예외(`RuntimeError`)로만 올리고, `{"ok": false}` dict 반환은 쓰지 않는다. 변환은 CLI 최상위 한 곳(adguardhome `main()` 형태)에서 한다 | 원본은 예외·dict·직접 종료가 섞여 호출자가 모양마다 처리해야 한다 | C-03 같은 dict 반환 패턴 삭제, T-07 대신 "timeout이면 `RuntimeError`" 사례 |
| R-22 | 사전 점검 `is_available()`과 `dependency_error` 타입을 모든 패밀리의 공통 단계로 둔다 | 원본은 browser·safari·일부 하니스만 점검하고 나머지는 호출 시점에 실패한다 | 공통 오류 타입 하나가 `harness-contract`의 오류 형식에 추가돼야 한다 |
| R-28, R-29 | fallback은 금지하거나, 허용하면 결과에 `fallback: true`와 원인을 남긴다. 예외를 삼키지 않는다 | gimp는 GIMP 렌더 오류를 `except Exception: pass`로 삼키고 Pillow로 넘어가며, drawio는 오류 대신 성공 값을 돌려준다 | T-04, T-09의 기대값이 "원인이 담긴 결과 또는 오류"로 바뀐다 |
