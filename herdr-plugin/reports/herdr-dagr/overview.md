---
sha: "52991f9a95a2b8c11518ed66f9530d938c1ba254"
created: 2026-11-06
updated: 2026-11-06
sources:
  - herdr-plugin.toml
  - Cargo.toml
  - README.md
  - CONTRACT.md
  - LICENSE-APACHE
  - LICENSE-MIT
  - scripts/install.sh
  - scripts/build.sh
  - scripts/open-dagr.sh
  - scripts/open-dagr.ps1
  - skills/dagr-producer/SKILL.md
  - demos/selfrun/README.md
  - src/main.rs
  - src/contract.rs
  - src/check.rs
  - src/scale.rs
  - src/stats.rs
  - src/model.rs
  - src/render.rs
  - src/view.rs
  - src/herdr.rs
  - src/message.rs
  - src/picker.rs
  - src/select.rs
---

# herdr-dagr Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/aemrebarut/herdr-dagr` (`herdr-plugin/artifacts/herdr-dagr/repo-metadata.txt`, branch `main`, 커밋일 2026-08-22)
- **작업트리 상태**: Clean (`git clone --depth 50`, 2026-11-06)
- **분석 목적**: 학습 · 도입 검토. (1) herdr 플러그인이 매니페스트(`herdr-plugin.toml`)와 소켓·CLI로 herdr와 어떻게 연동하는지, (2) 이 플러그인이 하는 일(에이전트 실행 상태를 DAG로 그려 주는 뷰어)을 본다.
- **라이선스**: MIT OR Apache-2.0 이중 라이선스(사용자가 고름). 근거는 세 곳이다. ① `LICENSE-MIT` 1~3행 "MIT License / Copyright (c) 2026 the herdr-dagr contributors", ② `LICENSE-APACHE`는 Apache License 2.0 표준 전문(2행 "Apache License", 202행; 부록의 저작권자 칸은 채워져 있지 않다), ③ `Cargo.toml:6` `license = "MIT OR Apache-2.0"`와 `README.md:354-360` License 절("either of Apache License, Version 2.0 or MIT license at your option"). `git ls-files`에서 LICENSE류 파일은 이 둘뿐이라 하위 디렉터리의 다른 LICENSE는 없다. (코드 확인)
- **분석 대상 제품**: 추적 파일 58개. 배포 단위는 하나, 즉 플러그인 매니페스트 + 설치 스크립트 + Rust 바이너리 `dagr`(패키지 `dagr` 0.3.1, `Cargo.toml:2-3`, `herdr-plugin.toml:18`)다. 크레이트 분할 없이 `src/` 13개 파일로 이루어진 단일 패키지다. (코드 확인)

  | 영역 | 추적 파일 수 | 맡은 일 |
  |---|---|---|
  | `src/` | 13 | `dagr` 바이너리: 계약 타입·린트·그래프 모델·렌더·뷰어·herdr 연결·메시지·통계 |
  | `scripts/` | 9 | 설치(`install.*`)·빌드(`build.*`)·창 열기(`open-dagr.*`) 래퍼, README 스냅샷 변환(`snapshot-svg.py`), 설치 점검 스크립트 2개(`test-*.sh`, 열지 않음) |
  | `skills/dagr-producer/` | 10 | 에이전트용 지침 `SKILL.md` 1개 + `examples/` JSON 9개 |
  | `demos/selfrun/`, `samples/`, `assets/` | 7, 2, 4 | 데모 run 파일과 영수증, 표본 run 파일, README 이미지 |
  | `tests/` | 3 | 통합 테스트 3개 — 열지 않음 |
  | `.github/` | 2 | CI·릴리스 워크플로 — 열지 않음 |
  | 루트 | 8 | `README.md`, `CONTRACT.md`, `herdr-plugin.toml`, `Cargo.toml`, `Cargo.lock`, `LICENSE-*`, `.gitignore` |

  (규모는 `git ls-files | cut -d/ -f1 | sort | uniq -c`로 센 값. 코드 확인)
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지) · 제외: 없음(승인 전)

---

## 2. 프로젝트 개요

**용어 먼저.** *herdr*는 코딩 에이전트용 터미널 멀티플렉서이고, *pane*은 그 안의 터미널 칸 하나다. *run 파일*(`run.json`)은 여러 에이전트가 하는 일을 JSON 하나로 적어 둔 문서이고, *producer*는 그 파일을 쓰는 쪽(오케스트레이터나 아무 에이전트)이다. *task*는 할 일 한 건, *attempt*는 그 task를 한 번 시도한 기록(재시도하면 새 attempt가 생긴다), *gate*는 여러 task가 끝나야 열리는 합류 지점이다. *evidence tier*는 "끝났다"는 결과를 얼마나 믿을 수 있는지 나타내는 네 단계(`verified`·`reported`·`heuristic`·`asserted`)다. *계약(contract)*은 run 파일이 지켜야 할 형식 규칙(`CONTRACT.md`)이다. *locator*는 attempt가 어느 herdr pane·agent에서 도는지 적어 둔 주소다.

**CONTRACT.md가 정의하는 것.** herdr와 plugin 사이의 약속이 아니라 **producer(run 파일을 쓰는 에이전트)와 `dagr`(읽어서 그리는 쪽) 사이의 데이터 형식 계약**이다. 헤더가 "`dagr` renders exactly this contract and nothing else"라고 못 박고(`CONTRACT.md:17-18`), 설계 입장을 "representation kernel, not an enforcement kernel"(표현만 하고 강제하지 않는다)로 적는다(`:22-28`). 그래서 지키는 쪽은 producer이고, `dagr check`가 그 준수 여부를 검사하며(`:316-343`의 E/W 코드), `dagr view`는 계약에 없는 사실을 지어내지 않는다(`:353-359` Non-goals). herdr의 pane id 같은 정보는 attempt에 붙는 "휘발성 주소"로만 기록한다(`:35-37`). 계약 본문과 `src/contract.rs`·`src/check.rs`의 일치는 필드 목록·버전 상수(`contract.rs:18-19`, 버전 3, 1·2도 읽음)·E100 분기(`check.rs:145-150`)까지만 대조했다. (코드 확인: 문서 내용, 버전 상수. 항목별 E/W 코드 전체 일치는 미확인)

**skills/가 무엇인가.** 에이전트(producer)에게 주는 지침서 `skills/dagr-producer/SKILL.md`(498줄)와 그 예제 JSON 9개다. 사람이 읽는 문서가 아니라 "run 파일을 쓰고 `dagr check`로 검증한 뒤 `mv`로 교체하라"는 절차를 에이전트에게 가르친다(`SKILL.md:31-63` "The loop"). `npx skills add ... --skill dagr-producer`로 에이전트에 설치하거나(`README.md:36`, `:102`), `dagr --skill`로 출력해 붙여 넣는다. 바이너리에 `include_str!`로 들어 있어 바이너리와 항상 같은 판이다(`src/main.rs:53`, `:62-65`). 플러그인 설치 때 에이전트 설정에 자동으로 쓰지는 않는다(README 주장, 설치 스크립트에 해당 코드가 없음은 `install.sh` 전체를 읽어 확인). (코드 확인)

**한 줄 요약.** `dagr`는 run 파일을 **읽기만 하는** 뷰어다(README `:123`, `CONTRACT.md:355` "dagr never settles, fences, or retries anything"). herdr에서 얻는 것은 pane 생존·에이전트 상태 힌트, 포커스 이동, 운영자 메시지 전달 세 가지뿐이고, 작업 상태의 진실은 항상 run 파일이다(`src/herdr.rs:1-9`). (코드 확인)

- **herdr 매니페스트는 build·panes·actions만 쓴다.** `startup`, `events` 같은 항목은 없다(`herdr-plugin.toml` 전체 154행에서 찾아본 결과). 즉 herdr가 이벤트를 플러그인에 밀어 넣는 방식이 아니라, 뷰어 프로세스가 스스로 소켓에 접속해 이벤트를 구독한다(`herdr.rs:198-338`). (코드 확인)
- **창 열기는 액션 → 셸 스크립트 → herdr CLI 재호출**이다. 매니페스트에는 "이 pane을 연다"는 선언 항목이 없어서, 액션이 `scripts/open-dagr.sh`를 실행하고 그 스크립트가 `herdr plugin pane open`을 다시 부른다(`open-dagr.sh:1-6`, `:38-47`). (코드 확인)
- **메시지는 기록 후 전달**이다. 운영자가 `m`으로 쓴 글을 `messages.jsonl`에 먼저 적고, 그다음 herdr 소켓의 `agent.prompt`로 보낸다(`message.rs:514`, `:537-569`, `herdr.rs:505-510`). (코드 확인)
- README가 주장하는 "5개 이상 에이전트 관리에 쓴다", "큰 run도 읽기 쉽다" 같은 효용은 검증 대상이 아니다. 접기·줌·정렬이 실제로 큰 문서에서 읽기 좋은지는 실행하지 않아 `미확인`이다.

### Feature map

<!--
OSS_ANALYSIS_WORKFLOW.md 2장 4번. 한 행 = 스펙 하나의 작업 단위. 이번에는 지도만(스펙 미작성).
상태는 전부 "미작성"(파일 없음, 경로는 코드 표기).
검증 수준: 진입점·호출을 읽었으면 "코드 확인", 모듈 머리 주석만 봤으면 "추론(머리 주석)", 열지 않았으면 "미확인".
-->

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 플러그인 입구·설치 | `herdr plugin install` 시 herdr가 `[[build]]`의 `install.sh`(또는 Windows `install.ps1`)를 실행 → 릴리스 바이너리를 내려받아 체크섬·커밋 일치 확인 후 `bin/dagr`에 설치, 조건이 안 맞으면 `cargo`로 빌드. 제외: 릴리스 CI, Windows 설치 본문 | `herdr-plugin.toml:27-33`, `scripts/install.sh:44-95`(분기), `:97-132`(검증·설치), `scripts/build.sh:8-10` | 없음 | 핵심 | `capabilities/plugin-install.md` · 미작성 | 코드 확인(`install.sh`·`build.sh` 전체). `install.ps1`·릴리스 실제 성공 여부는 미확인 |
| 창 열기 액션 (`open-dagr*`) | 사용자가 키·`herdr plugin action invoke`로 액션 실행 → 실행 중인 pane의 cwd를 찾아 → 새 split pane에 `dagr view`를 띄움. 방향 right·down·left·up(left·up은 split 후 swap). Windows는 별도 액션·스크립트 | `herdr-plugin.toml:37-47`(pane), `:55-93`(unix 액션), `:101-153`(windows 액션), `scripts/open-dagr.sh:20-58`, `src/main.rs` `cmd_pane_cwd`(:85), `scripts/open-dagr.ps1:33-68` | 플러그인 입구·설치(바이너리 존재) | 핵심 | `capabilities/open-pane-action.md` · 미작성 | 코드 확인(unix·windows 스크립트 전체, `cmd_pane_cwd`). herdr가 `HERDR_PLUGIN_ROOT` 등을 주입하고 `plugin pane open`을 이 의미로 처리하는지는 미확인(herdr 쪽) |
| `dagr check` (계약 린트) | `dagr check <run.json> [--json] [--strict]` → 파싱 → 크기 한도 → 계약 검사 → 오류 E-코드·경고 W-코드 출력. 종료 코드 0/1/2. 제외: run 파일 수정 | `src/main.rs` `cmd_check`(:202), `src/check.rs` `check`(:123), `src/contract.rs` `Doc`(:46), `src/scale.rs` `read_limited`(:12), `enforce_document`(:35) | 공유 계약(run-state) | 핵심 | `capabilities/check-lint.md` · 미작성 | 코드 확인(`cmd_check`·`scale.rs` 전체, `check` 시작부 `:123-160`). 개별 E/W 규칙 구현은 미확인 |
| `dagr view` 로드·감시·그래프 모델·렌더 | 인자·`$DAGR_RUN`·`.dagr/run.json`·`run.json` 순으로 run 파일을 찾고, 없으면 기다림. 파일 mtime을 300ms 주기로 확인해 다시 읽고, 마지막으로 성공한 장면을 유지. task·attempt·gate·project를 행으로 만들어 폭에 따라 cockpit/sidecar 두 레이아웃으로 그림. `--snapshot`은 한 프레임 출력 | `src/main.rs` `discover_run_file`(:155), `src/view.rs` `load`(:38), `interactive`(:967), `event_loop`(:1041, mtime 감시 `:1306-1312`), `snapshot`(:114), `src/model.rs` `build`(:1151), `src/render.rs` `compose`(:1716), `FOLD_WIDTH`(:17) | 공유 계약 | 핵심 | `capabilities/view-render.md` · 미작성 | 코드 확인(`discover_run_file`·`load`·`interactive`·감시 루프). `model.rs`·`render.rs` 본문(약 5,800줄)은 진입 함수와 머리 주석만 읽음: 행 도출·상태 글리프·게이트 합류 표시는 `추론(머리 주석)` |
| 뷰어 탐색 상호작용 | `j/k/g/G`, `tab`(주의 큐), `d`(상세), `←/→`(접기·줌), `z`(끝난 것 접기), `/`·`n/N`(검색), `f`(다른 run 파일 선택), `y`·마우스 드래그(클립보드 복사), `?`, `q`. 제외: 렌더 세부 | `src/view.rs` 키 분기(`:1085-1172`), `reload`(:928), `src/picker.rs`(:1-5, `mru_file` :149), `src/select.rs`(:1-14, `osc52` :181) | `dagr view` 로드·감시·렌더 | 핵심 | `capabilities/view-navigation.md` · 미작성 | 코드 확인(키 분기·`reload`·`picker`/`select` 머리 주석). 접기·줌·검색·마우스 처리의 내부 구현은 미확인 |
| herdr 연결 (생존 힌트·포커스) | herdr 안에서 실행하면 소켓에 접속해 pane 목록·에이전트 상태를 구독, locator가 가리키는 pane이 사라지면 표시. 선택한 attempt에서 `enter`를 누르면 해당 pane/agent로 포커스 이동. herdr 밖이면 힌트·포커스 없음. Windows는 힌트·포커스 불가 | `src/herdr.rs` `Link::start`(:65), `worker`(:115), `session`(:198), `apply_event`(:391), `focus_pane`(:493), `focus_agent`(:498), `src/view.rs` `update_watch`(:241), `focus`(:682) | `dagr view` 로드·감시·렌더 | 핵심 | `capabilities/herdr-link.md` · 미작성 | 코드 확인(`herdr.rs` 560행 앞까지 전체, `view.rs` `focus`·`update_watch`). herdr 서버의 응답·이벤트 형식은 코드의 가정일 뿐 미확인(`herdr.rs:11-19` 주석은 "live 0.8 daemon으로 확인"이라 주장) |
| 운영자 메시지 | `m` → 선택한 task에 대한 편집 가능한 메시지 작성(시작 문구 3종, 권한 `recommend`/`decide`) → `Enter`로 `messages.jsonl`에 먼저 기록 → herdr `agent.prompt`로 `run.orchestrator`에 전달 → 전달 영수증 추가. 오케스트레이터가 `message_resolved` 이벤트로 답을 연결. 제외: 결과 해석·재시도(dagr는 하지 않음) | `src/message.rs` `prepare`(:445), `deliver`(:537), `load_config`(:105), `defaults`(:70), `src/view.rs` `start_message`(:794), `submit_message`(:808), `src/herdr.rs` `prompt`(:505) | herdr 연결, 공유 계약 | 핵심 | `capabilities/operator-message.md` · 미작성 | 코드 확인(`prepare`·`deliver`·`defaults`·`config_path`·`journal_path`·`submit_message`). `Draft` 편집·`read_summaries` 파서·`actions.json` 검증 세부는 미확인 |
| `dagr stats` | `dagr stats <run.json> [--json]` → attempt별 타임스탬프로 age·시간대별 체류·재작업률·WIP·크리티컬 패스·단순 ETA 계산. 시계는 실제 시간이 아니라 문서의 `generated_at` | `src/stats.rs` `run`(:296), `compute`(:82), `header_chip`(:274) | 공유 계약 | 핵심 | `capabilities/stats.md` · 미작성 | 코드 확인(`run` 인자 처리, `compute` 시계 선택부). 각 지표의 계산식은 `추론(머리 주석)` |
| 에이전트용 producer 스킬 | 에이전트가 `SKILL.md`를 읽고 run 파일을 `run.json.tmp`에 쓰고 → `dagr check --strict --json` → 통과하면 `mv`로 교체. 운영자 메시지 봉투를 받으면 `message_id`를 보존해 `message_resolved` 이벤트를 남김. 제외: 스킬 설치(별도 명령) | `skills/dagr-producer/SKILL.md:31-63`(검증 루프), `:403-443`(메시지 처리), `src/main.rs` `SKILL`(:53), `--skill`(:62), `src/message.rs:515-525`(봉투 형식) | 공유 계약, 운영자 메시지 | 핵심 | `capabilities/producer-skill.md` · 미작성 | 코드 확인(SKILL.md 위 두 절과 `object model` 절, 봉투 형식이 `message.rs`와 일치함). 에이전트가 실제로 이 절차를 따르는지는 미확인 |
| 샘플·데모·README 자산 | `samples/run.json`(표본), `samples/states.json`(모든 상태 조합 회귀 픽스처), `demos/selfrun/`(이 레포 개발을 run 파일로 기록한 데모와 영수증), `assets/`(PNG·SVG), `scripts/snapshot-svg.py`(스냅샷→SVG) | `samples/states.json`(앞부분), `demos/selfrun/README.md:1-40`, `README.md:199-212` | 없음 | 부속 | `capabilities/samples-demos.md` · 미작성 | 추론(README·demo README만 읽음). 파일 내용과 `snapshot-svg.py`는 미확인 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| run-state 계약 v3 (`run.json` 형식, v1·v2 읽기 호환) | `check`, `view`, `stats`, 운영자 메시지, producer 스킬 | `CONTRACT.md:267-314`(필드 목록), `src/contract.rs` `Doc`(:46), `CONTRACT_VERSIONS`(:19) | `capabilities/run-contract.md` · 미작성 | 코드 확인(필드·버전 상수 대조). 필드 전체 일치는 미확인 |
| 메시지 사이드카 파일 (`actions.json`, `messages.jsonl`) | 운영자 메시지, `view`(변경 감시) | `src/message.rs` `config_path`(:95), `journal_path`(:99), `append_json`(:392, 소유자만 읽기·쓰기 모드 `0o600`은 `:398`), `CONTRACT.md:200-257` | 운영자 메시지 스펙에 포함 | 코드 확인 |

**대조한 범위와 미탐색 영역**
- **대조**: README의 "What dagr does"·"Navigation"·"Install"·"Repo layout"을 `main.rs` USAGE(:21-48)와 서브커맨드 분기(:55-75), `view.rs` 키 분기, 매니페스트 `[[actions]]` 10개(unix 5 + windows 5, `herdr-plugin.toml`)와 대조했다. 서브커맨드는 `check`·`view`·`stats`·`pane-cwd`·`--skill`·`--version`으로 README와 일치한다(`pane-cwd`는 README에 없는 내부용). README의 "Press `d` or `esc` to return"(:191-193)은 `view.rs:1096`(`Esc | Char('d') => toggle_details`)과 맞다.
- **문서와 구현의 차이**: (1) `open-dagr`와 `open-dagr-right`는 같은 명령(`open-dagr.sh right`)을 실행한다(`herdr-plugin.toml:61`, `:93`). README는 "한 방향에 액션 하나"라고 쓰지만 right는 둘이다. (2) README "the plugin pane"은 Windows에서도 쓰는 것처럼 읽히지만 매니페스트 `[[panes]]`는 `platforms = ["linux", "macos"]`뿐이고(`:40`), Windows는 pane을 선언하지 않고 `pane split` + `pane run`으로 셸에 명령을 타이핑한다(`open-dagr.ps1:50-63`). (3) `dagr` 매니페스트 주석은 스키마를 "herdr 0.8.0의 현장 플러그인에서 검증했다"고 쓰는데(`herdr-plugin.toml:6-7`) herdr 쪽 공식 문서로는 확인하지 못했다.
- **미탐색(열지 않음)**: `tests/`(3개: 테스트), `.github/workflows/`(CI·릴리스; 단 `install.sh`가 기대하는 릴리스 자산 이름 `COMMIT`·`dagr-<target>.tar.gz`·`.sha256`이 실제로 올라가는지는 확인하지 못함), `scripts/test-*.sh`(설치 점검 테스트), `scripts/install.ps1`·`snapshot-svg.py` 본문, `Cargo.lock`, `skills/.../examples/*.json` 개별 파일. `src/model.rs`(3,132줄)·`src/render.rs`(2,695줄)·`src/view.rs` 중 렌더·접기·줌·마우스 구현은 진입 함수까지만 읽었다.

---

## 3. 구조 해설 (archify 도면 없이 글로)

사용자 지시로 이 레포는 구조도(archify)를 만들지 않는다. 아래 글이 그 자리를 대신한다.

**읽는 순서**
1. `herdr-plugin.toml`: herdr가 이 플러그인에 무엇을 시키는지(빌드 1종, pane 1개, 액션 10개)를 먼저 본다.
2. `scripts/open-dagr.sh` → `src/main.rs`: 액션이 어떻게 `dagr view` 프로세스가 되는지, 서브커맨드 분기를 본다.
3. `CONTRACT.md` 앞부분(`:20-38` 설계 입장, `:267-314` 필드 목록)과 `src/contract.rs`: 뷰어가 읽는 데이터의 모양을 이해한다.
4. `src/view.rs`의 `load`·`interactive`·`event_loop`: 파일 감시와 화면 갱신 루프.
5. `src/herdr.rs`·`src/message.rs`: herdr와 주고받는 부분(소켓·CLI 호출).
6. 에이전트 쪽이 궁금하면 `skills/dagr-producer/SKILL.md:31-63`과 `:403-443`.

**모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 매니페스트 | herdr에게 빌드·pane·액션을 선언 | build 명령, pane 명령, 액션 명령(herdr가 실행) | `herdr-plugin.toml:27-153` | 코드 확인 |
| 설치 스크립트 | 릴리스 바이너리를 검증해 `bin/dagr`에 놓거나 `cargo`로 빌드 | 입력: `herdr-plugin.toml`의 version, git HEAD, 릴리스 URL → 출력: `bin/dagr` | `scripts/install.sh:12`, `:62-95`, `:122-132`, `scripts/build.sh:8-10` | 코드 확인 |
| 창 열기 스크립트 | 사용자 cwd를 정해 `herdr plugin pane open`을 호출, left/up은 `pane swap` | 입력: 방향 인자, `HERDR_BIN_PATH`, `HERDR_PLUGIN_ID`, `dagr pane-cwd` 출력 → herdr CLI | `scripts/open-dagr.sh:14-58`, `src/main.rs` `cmd_pane_cwd`(:85) | 코드 확인 |
| CLI 진입 | 서브커맨드 분기, run 파일 위치 찾기, USAGE | 인자·환경변수 → `check`/`view`/`stats` 호출 | `src/main.rs` `main`(:55), `discover_run_file`(:155) | 코드 확인 |
| 계약 타입·한도 | run 파일을 serde로 읽는 느슨한 타입, 크기 한도(16MiB, 항목 4,096, 이벤트 32,768) | JSON → `Doc` | `src/contract.rs` `Doc`(:46), `src/scale.rs:7-10`, `enforce_document`(:35) | 코드 확인 |
| 린트 | 계약 위반을 E/W 코드로 보고 | `Doc` → `Report` | `src/check.rs` `check`(:123) | 코드 확인(시작부) / 규칙 전체는 미확인 |
| 그래프 모델 | 계약 데이터에서 행·합류·큐를 도출 | `Doc`+선택+`Hints` → `Scene` | `src/model.rs` `build`(:1151), 머리 주석(:1-6) | 코드 확인(시그니처) / 추론(머리 주석) |
| 렌더 | `Scene`을 폭에 따라 ANSI 프레임으로 그림 | `Scene`·폭 → `Frame` | `src/render.rs` `compose`(:1716), `FOLD_WIDTH`(:17) | 코드 확인(시그니처) / 추론(머리 주석) |
| 뷰어 | 파일 감시, 키·마우스 처리, 화면 갱신, 백그라운드 포커스·메시지 전송 | run 파일, 키 입력 → 프레임, herdr 호출 | `src/view.rs` `interactive`(:967), `event_loop`(:1041), `reload`(:928) | 코드 확인(주요 루프) |
| herdr 연결 | 소켓 구독 스레드로 pane 상태 힌트 유지, 포커스·prompt 요청 | 소켓 JSON 줄 ↔ `Hints`, 요청 → `Result` | `src/herdr.rs` `Link`(:50), `worker`(:115), `socket_request_at`(:456) | 코드 확인 |
| 메시지 | 운영자 글을 저널에 기록하고 herdr로 전달, 상태 복원 | 글 → `messages.jsonl` + `agent.prompt` | `src/message.rs` `prepare`(:445), `deliver`(:537), `read_summaries`(:296) | 코드 확인(`prepare`·`deliver`) / `read_summaries` 본문 미확인 |
| 통계 | 타임스탬프 기반 흐름 지표 | `Doc` → `Flow` | `src/stats.rs` `compute`(:82), `run`(:296) | 코드 확인(진입부) |
| 스킬 | 에이전트가 읽고 따르는 producer 지침 | 에이전트 → run 파일 | `skills/dagr-producer/SKILL.md`, `src/main.rs:53` | 코드 확인(일부 절) |

**herdr 연동 지점** (herdr가 하는 일은 herdr 서버 쪽 동작이라 코드로 확인하지 못하면 `미확인`)

| 매니페스트 항목 | 실행되는 명령 | 코드 진입 | 하는 일 | 검증 수준 |
|---|---|---|---|---|
| `[[build]]` (linux·macos) | `bash scripts/install.sh` (`herdr-plugin.toml:27-29`) | `scripts/install.sh:44-132` | 릴리스 바이너리 다운로드·검증, 실패 시 `build.sh`로 `cargo build --release --locked` | 코드 확인(스크립트). herdr가 설치 시 이 명령을 실행한다는 것은 README `:254`·매니페스트 주석(`:23-26`)의 주장이고 herdr 쪽은 미확인 |
| `[[build]]` (windows) | `powershell ... -File scripts/install.ps1` (`:31-33`) | `scripts/install.ps1` | Windows용 같은 일 | 매니페스트만 확인, 본문은 미확인 |
| `[[panes]]` `id="dagr"` (linux·macos, `placement="split"`) | `/bin/sh -c 'exec "${HERDR_PLUGIN_ROOT:?not launched by herdr}/bin/dagr" view'` (`:37-47`) | `src/main.rs` `main`(:55) → `cmd_view`(:103) → `view::run`(:101) | split pane 안에서 뷰어 실행. `HERDR_PLUGIN_ROOT` 미설정이면 셸이 오류로 종료 | 코드 확인(명령). `HERDR_PLUGIN_ROOT` 주입은 매니페스트 주석(`:42-43`)의 주장, herdr 쪽 미확인 |
| `[[actions]]` `open-dagr`, `-right` (linux·macos, `contexts=["workspace"]`) | `bash scripts/open-dagr.sh right` (`:55-61`, `:87-93`) | `open-dagr.sh:20-58` | `herdr plugin pane open --plugin herdr-dagr --entrypoint dagr --placement split --direction right --focus [--cwd <사용자 cwd>]`로 위 pane을 연다 | 코드 확인(스크립트의 호출 인자). `contexts`가 무엇을 제한하는지는 미확인 |
| `[[actions]]` `open-dagr-down` | `open-dagr.sh down` (`:63-69`) | 위와 같음 | `--direction down` | 코드 확인 |
| `[[actions]]` `open-dagr-left` / `-up` | `open-dagr.sh left` / `up` (`:79-85`, `:71-77`) | `open-dagr.sh:24-25`, `:54-58` | right/down으로 연 뒤 새 pane의 `pane_id`를 응답에서 `sed`로 뽑아 `herdr pane swap --pane <id> --direction left\|up` | 코드 확인 |
| `[[actions]]` `*-windows` 5개 | PowerShell 한 줄로 `herdr plugin list --json`에서 `plugin_root`를 찾아 `open-dagr.ps1 <방향>` 실행 (`:101-153`) | `scripts/open-dagr.ps1:33-68` | `pane list`로 포커스 pane의 cwd → `pane split --direction --cwd --focus` → `pane run <id> '& "<bin>\dagr.exe" view'` → `pane rename <id> dagr` → 필요하면 `pane swap` | 코드 확인(스크립트). Windows에서 실제로 동작하는지는 미확인 |
| `events` / `startup` | **매니페스트에 없다.** 이벤트는 뷰어가 소켓으로 직접 구독 | `src/herdr.rs:225-239`(구독 항목 `pane.created`·`pane.closed`·`pane.exited`·`pane.agent_detected`, locator pane마다 `pane.agent_status_changed`) | 위 이벤트로 `Hints.pane_status` 갱신 | 코드 확인 |

**herdr 호출 방식 요약** (코드 확인)
- **소켓** (`$HERDR_SOCKET_PATH`, Unix 도메인 소켓, 줄 단위 JSON, `herdr.rs:1-9`): `session.snapshot`(`:173`), `events.subscribe`(`:236-239`, 연결 유지), `pane.focus`(`:494`), `agent.focus`(`:499`), `agent.prompt`(`:506-509`). 요청 id는 `dagr-snap`·`dagr-sub`·`dagr-focus`다. Windows(비 Unix)에서는 구독 스레드가 아무 일도 하지 않고(`:149-156`) 포커스는 오류를 돌려준다(`:487-490`).
- **CLI**: 창 열기(`plugin pane open`, `pane swap`, Windows는 `pane list/split/run/rename/swap`, `plugin list --json`)와 Windows의 메시지 전달(`herdr agent prompt <target> <text>`, `herdr.rs:514-543`)만 CLI를 쓴다. 실행 파일은 `$HERDR_BIN_PATH`, 없으면 `herdr`(`open-dagr.sh:14`, `herdr.rs:519-523`, `:541`).
- **환경변수**: `HERDR_PLUGIN_ROOT`(pane 명령, `herdr-plugin.toml:47`), `HERDR_PLUGIN_ID`(`open-dagr.sh:15`), `HERDR_BIN_PATH`, `HERDR_SOCKET_PATH`(`herdr.rs:66`, `:448`), `HERDR_PLUGIN_CONTEXT_JSON`(`main.rs:86`, `:161`; JSON에서 `workspace_cwd`·`focused_pane_cwd`·`cwd` 순서가 상황별로 다름: 액션 시점 `pane-cwd`는 `focused_pane_cwd` 우선(`:90`), 뷰어 시점 `discover_run_file`은 `workspace_cwd` 우선(`:165`)), `HERDR_ACTIVE_PANE_CWD`(Windows 폴백, `open-dagr.ps1:40-41`). 이 값들을 herdr가 실제로 어떻게 채우는지는 코드 밖이라 `미확인`.
- **파일 약속**: 뷰어는 run 파일 옆 `actions.json`(읽기)·`messages.jsonl`(추가 쓰기)을 쓰고(`message.rs:95-101`), 최근 연 파일 목록은 `$XDG_STATE_HOME/dagr/recent`(`picker.rs:149-159`)에 남긴다.

**실행 흐름: 운영자 메시지 보내기** (대표 흐름 하나)
1. 사용자가 herdr에서 액션을 실행 → `bash scripts/open-dagr.sh right` → `herdr plugin pane open ... --entrypoint dagr` (`open-dagr.sh:38-49`) → herdr가 `[[panes]]`의 `sh -c 'exec .../bin/dagr view'`를 새 split pane에서 실행 (`herdr-plugin.toml:47`; herdr 쪽 실행은 매니페스트 선언대로라고 가정, 미확인).
2. `dagr view`가 run 파일을 찾는다: `$DAGR_RUN` → `<cwd>/.dagr/run.json` → `<cwd>/run.json` (`main.rs:155-200`). 읽어서 `check`를 돌리고 오류가 있으면 배너로만 알리며 읽힌 부분을 그린다 (`view.rs:38-80`). 동시에 `herdr::Link::start()`가 소켓 구독 스레드를 띄운다 (`view.rs:994`, `herdr.rs:65`). 이후 300ms마다 입력을 확인하고 파일 mtime이 바뀌면 `reload`한다 (`view.rs:1057`, `:1306-1312`).
3. producer 에이전트가 `run.json.tmp`에 쓰고 `dagr check`로 통과시킨 뒤 `mv`로 교체한다 (`SKILL.md:31-63`). 뷰어가 새 mtime을 보고 다시 읽는다.
4. 사용자가 task 행을 고르고 `m`을 누르면 `start_message`가 작성 창을 연다 (`view.rs:794-806`). `Enter`를 누르면 `submit_message`(`:808`)가 `message::prepare`를 부른다: 빈 글·32KiB 초과·`run.orchestrator` 없음·`generated_at` 없음·대상 task가 유일하지 않음이면 거절하고 (`message.rs:453-489`), 통과하면 `message_queued` 레코드를 `messages.jsonl`에 먼저 추가한다 (`:502-514`).
5. 백그라운드 스레드가 `message::deliver`를 실행한다 (`view.rs:832-834`). `[DAGR OPERATOR MESSAGE]` 봉투(`message_id`·run·revision·target·starter·authority + 본문, `message.rs:515-525`)를 `herdr::prompt`로 보낸다. Unix는 소켓 `agent.prompt`, Windows는 `herdr agent prompt` CLI다 (`herdr.rs:505-510`, `:540-543`). 결과는 `message_delivered` 또는 `message_delivery_failed` 영수증으로 저널에 추가한다 (`message.rs:546-559`).
6. 오케스트레이터 에이전트가 봉투를 받아 처리하고 run 파일에 `message_resolved` 이벤트(`message_id` 포함)를 추가한다 (`SKILL.md:403-443`, `CONTRACT.md:246-249`). 이 단계는 에이전트 쪽 동작이라 코드로 확인할 수 없다(`미확인`). 뷰어는 저널·run 파일 변경을 보고 다시 읽는다 (`view.rs:1313-1320`).

**미확인 영역**
- herdr 서버 쪽 전부: 매니페스트 스키마 해석(build·panes·actions·`contexts`), `HERDR_*` 주입, 소켓 프로토콜(`protocol 19`)과 응답 형식, `agent.prompt`가 입력 큐에 어떻게 쌓이는지. `dagr` 코드는 "클라이언트가 그렇게 가정했다"는 증거일 뿐이다(OSS_ANALYSIS_WORKFLOW.md 7장).
- `src/model.rs`·`src/render.rs`의 행 도출·레이아웃·글리프, `check.rs`의 개별 규칙, 접기·줌·검색·마우스 처리, `stats.rs` 계산식.
- Windows 경로 전체(`install.ps1`, 비 Unix 분기를 실제로 돌려 보는 것).
- 릴리스 자동화(`.github/`)와 릴리스 자산의 실제 존재.
- 실행·빌드는 하지 않았다(읽기만 함). 따라서 "화면이 이렇게 보인다"는 README 주장은 모두 `미확인`이다.

---

## 4. 질문 (Questions)

없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: 없음 (`next.md` 미작성, 사용자가 범위를 승인하면 만든다)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸. 전부 `미작성`이다.
- **권장 범위(승인 전 제안)**: 목적이 herdr 연동 방식이므로 연동 지점 행을 우선한다. 창 열기 액션, herdr 연결, 운영자 메시지, 플러그인 입구·설치, producer 스킬(에이전트가 이 플러그인에 데이터를 넣는 경로). `dagr view` 렌더·탐색은 연동과 거리가 있어 보류하고, 샘플·데모는 부속이라 제외를 기본으로 한다.
