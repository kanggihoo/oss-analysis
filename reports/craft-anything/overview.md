---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
---

# Craft Anything Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/storytold/craft-anything.git`
- **작업트리 상태**: Clean (clone 직후, `git status --short` 0줄)
- **분석 목적**: **설계 참고** — 우리 절차(AI가 오픈소스 코드를 읽고 검증해 스펙 문서로 남기고, 스펙만으로 재구현 가능한지 보는 작업, `OSS_ANALYSIS_WORKFLOW.md`)를 이 레포가 어떻게 하는지와 맞대어 **보완·개선할 점**을 찾는다. 스펙은 "우리 절차 개선안"의 근거 자료로 쓴다(제품 재구현이 아님). 그래서 증거·질문·조사 기억·재구성 검증·리빌드 루프 쪽은 세분하고, 분석 도구 본체(파서·디스어셈블러 등)는 묶었다. (2026-11-14 사용자 요청으로 확정)
- **라이선스**: `MIT OR Apache-2.0` — `repos/craft-anything/LICENSE-MIT`(Copyright 2026 ArtCraft Team and the Craft Anything contributors), `repos/craft-anything/LICENSE-APACHE`. `NOTICE`: ArtCraft 이름·로고(`docs/brand/`)는 상표로 위 라이선스 밖(`docs/brand/LICENSE-brand.txt`). 번들 폰트는 OFL 1.1, Lucide 아이콘은 ISC(`assets/icons/LICENSE-lucide.txt`). `vendor/wgpu-hal/`은 자체 `LICENSE.APACHE`·`LICENSE.MIT`를 둔다. `Cargo.toml` `[workspace.package] license = "MIT OR Apache-2.0"`.
- **분석 대상 제품**: Rust 워크스페이스 v0.6.1(`Cargo.toml`). 라이브러리 crate 13개(`crates/*`: evidence, formats, disasm, js, analysis, platform, engines, engine, ai, mcp, setup, ui-egui, testkit), 앱 3개(`apps/craft-anything` 데스크톱 egui, `apps/craft-anything-cli` CLI+MCP, `apps/craft-anything-web` 브라우저 뷰어), `xtask/`, 예제 WASM 플러그인 2개(`examples/`), 설치 패키징(`packaging/`), 수정본 `vendor/wgpu-hal/`.
- **스펙 범위**: 2026-11-14 승인(권장대로) — 행 1~11. 제외: 행 12~20(사용자 제외: 우리 절차와 직접 대응 없음, 12~14는 필요하면 추가). 7행의 선행 13(에이전트 구동)은 범위 밖이라 스펙에서 "턴을 수행하고 이벤트를 돌려주는 경계"로만 정의한다. 작성 방식: 코드만 읽고 쓴다(실행·빌드·테스트 없음).

---

## 2. 프로젝트 개요

README 기준: 웹사이트·앱·게임이 어떻게 만들어졌는지 검사 도구로 조사하고(Study), 코딩 에이전트(Claude Code 등)에 새 프로젝트를 만들게 하고(Build), 원본과 비교하고(Check), 차이를 줄여 다듬는(Ready/Refine) 순수 Rust 엔진이다. 모든 기능이 `ToolSpec` 하나로 등록되어 데스크톱 UI·CLI·MCP·내장 에이전트가 같은 id로 호출한다(`AGENTS.md` Golden rules 2번, `crates/engine/src/tool.rs` `ToolSpec`). "Clean room"(대상 내부를 읽지 않음)과 "Deep"(모든 도구 사용) 두 모드가 있다(`crates/engine/src/clean_room.rs` `allows`). 상태는 early alpha(README "Status").

### Feature map

분할과 경로는 제안이다. 목적이 "우리 절차 보완"이라 **우리 절차와 대응되는 영역(1~11)은 세분**하고, 나머지는 패밀리 한 행으로 묶었다(행 수 20). 이번 세션에서 열어 본 파일은 행마다 검증 수준에 적었다. "코드 확인(전문)"은 해당 파일을 끝까지 읽었다는 뜻이고, "진입점"은 머리 주석·도구 설명·시그니처만 읽었다는 뜻이다. 동작 규칙(R-ID)은 아직 확정하지 않았다.

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 증거 레코드 (신뢰도·권위·범위·한계) | 분석 결과 하나 = `Evidence`: `Confidence`(observed/derived/inferred), `Authority`(5종), `Coverage`(examined/total/next_offset, 쪽 나누기 정보), `Limitation`, `Environment`(clean_room 플래그). 세션 원장 기록·조회, 프로젝트 저장·로드 시 변조 검사, 내보내기·가져오기, `ToolError` 계약 포함. id에는 `environment` 전체가 들어가므로 같은 관찰이 같은 id인 것은 환경이 같을 때만 | `crates/evidence/src/{lib,canonical,error}.rs`, `crates/engine/src/session.rs` `record`·`resolve_evidence`, `project.rs`, `tools/session_tools.rs` | 없음 | 핵심 | [evidence-record](./capabilities/evidence-record.md) · ready | 코드 확인 |
| 2 | 미해결 질문 (Unknown) | 열린 질문을 상태·중요도·확인 방법(probes)·찬반 증거와 함께 기록. 개정 번호로 동시 수정 거부. resolved 변경 시 막는 것은 resolution 누락뿐이고(resolved→resolved일 때), 증거 id는 기록 시 검사하지 않으며 읽기 전용 `core_unknown_verify`가 따로 검사 | `crates/evidence/src/unknown.rs`, `crates/engine/src/tools/session_tools.rs` `core_unknown_*` | 1 | 핵심 | [unknown-ledger](./capabilities/unknown-ledger.md) · ready | 코드 확인 |
| 3 | 조사 작업 기억 (brief·plan·hypothesis·finding·handoff·저널) | 질문·목적·제약·완료 기준(brief) → 단계 상태(plan) → 예측 달린 가설 → **증거 id 없이는 기록 불가한 finding**(id를 원장에서 존재 검증, 내용·신뢰도 일치는 검사 안 함) → handoff. `based_on_revision` 검사는 plan_update·finding_edit에서만 인자를 줄 때만. 모든 도구 호출을 저널로 기록하고 `core_journal_read`로 조회 | `crates/engine/src/tools/investigation_tools.rs`, `lib.rs` `Engine::call`(저널 기록), `journal.rs` | 1 | 핵심 | [investigation-memory](./capabilities/investigation-memory.md) · ready | 코드 확인 |
| 4 | 조사 보고서 생성 | finding·가설·질문·증거에서 보고서(Markdown/HTML)를 만든다. 모드는 증거가 아니라 현재 세션 값, 한계는 인용하지 않은 증거에서도 모음, plan은 렌더에 없음(주석·도구 설명과 다름). `core_report_save`는 finding과 무관하게 받은 텍스트를 저장 | `crates/engine/src/tools/report_tools.rs` | 1, 2, 3 | 핵심 | [investigation-report](./capabilities/investigation-report.md) · ready | 코드 확인 |
| 5 | 조사 방법 지침 (스킬 2파일 + MCP instructions + 프롬프트 6개) | 관찰/도출/추론 구분, 증거 id 인용, "없음은 증거가 아님", 예측 후 검증, 요약 먼저 페이징, 턴 끝 handoff. 설치된 스킬 상태(missing/current/outdated/foreign)와 설치·제거. 내장 에이전트용 `prompt.rs`의 `METHOD`·`MEMORY`는 별도 문구라 14행 소관 | `crates/setup/src/{skill.md,skill_recovery.md,skill.rs}`, `crates/mcp/src/{prompts.rs,lib.rs}` `INSTRUCTIONS` | 3 | 핵심 | [method-guidance](./capabilities/method-guidance.md) · ready | 코드 확인 |
| 6 | 재구성 원장·증명 강도 | 기대 동작(expectation)마다 담당 위치 하나, 필요한 사례(실제로는 works·refuses·bad-input 3종, `CASE_KINDS`는 미사용), 요구 증명 강도(8단계)를 적고, 그 강도 이상의 통과한 검사가 사례를 나열·결과를 인용해야 `proven`. "유효"는 증거 존재·해시 일치뿐이고 강도는 호출자 선언. 리빌드 루프(7행)와 연결되지 않음. Deep 전용 | `crates/analysis/src/js_ledger.rs`, `crates/engine/src/tools/application_tools.rs`(`app_ledger_build`·`app_coverage_evaluate`), `compare_tools.rs`(`app_rebuild_claim_check`: 원장과 무관한 약한 검사) | 1, 15(경계만) | 핵심 | [rebuild-ledger](./capabilities/rebuild-ledger.md) · ready | 코드 확인 |
| 7 | 리빌드 루프 (Study→Build→Check→Refine) | 요청+대상 → 조사 노트 → 코딩 에이전트가 `app/`만 수정 → 검사 → 측정된 차이를 에이전트에 되돌림. 멈춤 조건 3개(재다듬기 상한 `max_rounds`: 실행마다 초기화, 작동하지 않는 라운드 연속 10: 프로젝트에 저장, `app/` 무변경 턴 연속 2: 내용 해시·저장), 검사 도구 오류 1회 재시도, 검사 결과 재사용. 기본 rounds는 앱 6, CLI·도구 2. 에이전트 구동(13·14행)은 경계만 | `crates/ai/src/rebuild/{mod,study,check,self_check,kept_check,runs,tools}.rs`, `crates/engine/src/workspace/progress.rs`, `workspace.rs` Manifest | 8, 9, 10 | 핵심 | [rebuild-loop](./capabilities/rebuild-loop.md) · ready | 코드 확인 |
| 8 | 빌더 브리프·행동 규칙 | 에이전트에 주는 고정 규칙(`RULES` 상수, `steps`는 모드만 받는 함수): 요청 우선, `app/`만 수정, 로고·문구 복사 금지, 결정이 필요한 것만 2~4지선다로 질문, 범위에서 빼는 것은 먼저 묻기, 모르는 것은 unknown 기록·추정 표시. 턴 메시지 선택, API 루프용 상수, 게임 추출기 브리프 포함 | `crates/ai/src/rebuild/brief.rs`, `stacks.rs`·`stacks.toml`, `rebuild/mod.rs:876-944` | 2, 9 | 핵심 | [builder-brief](./capabilities/builder-brief.md) · ready | 코드 확인 |
| 9 | 대상 종류·검사·재시도 계약 | `TargetKind`(판별·기본 스택·브리프 절)와 `Check`(`run`·`applies`·`can_refine`), `CheckResult`(`passed`와 `good` 분리, 비교하지 못한 것은 통과로 치지 않음). `can_refine=false`는 "오라클이 없어 에이전트가 고쳐도 풀리지 않음"이며 이 SHA에서 바꾸는 검사는 `MechanicsCheck` 하나. 원본 버그: `game-self-test` 판정이 반대 | `crates/ai/src/rebuild/kinds/mod.rs`, `check.rs`, `kinds/{website,game,app,own,screenshot,self_test,mechanics,runs,plugin_check}.rs`, `workspace.rs:247-388` | 없음 | 핵심 | [check-contract](./capabilities/check-contract.md) · ready | 코드 확인 |
| 10 | 질문·승인·중간 노트 인박스 + Just ask | 에이전트→사람 질문·행동 승인을 `<id>.request.json`/`<id>.answer.json`로 주고받음, 승인 정책(허용/질문/거절), 사람이 작업 중 추가한 노트를 훅으로 전달(철회 가능). 사람→빌더 질문(Just ask)은 인박스가 아니라 `questions.json` 경로 | `crates/engine/src/{inbox,questions}.rs`, `tools/interaction_tools.rs`, `crates/ai/src/rebuild/{question,notes}.rs`, CLI `builder-notes` | 없음 | 핵심 | [person-inbox](./capabilities/person-inbox.md) · ready | 코드 확인 |
| 11 | Clean room / Deep 모드 | 도구 id 허용 목록(`TOOLS`, 기본 거부) + 허용 도구 안의 자체 축소(`web_site_capture`) + 빌더용 `off_limits`의 세 층. `settings_set`이 허용 목록에 있어 `deep_mode`를 켤 수 있고, 증거 열람 도구는 모드로 거르지 않음 | `crates/engine/src/clean_room.rs`, `lib.rs` `Engine::call`, `settings.rs`, `tools/interaction_tools.rs:500-548`, `tools/browser_tools.rs` | 1 | 핵심 | [clean-room-mode](./capabilities/clean-room-mode.md) · ready | 코드 확인 |
| 12 | 도구 계약·MCP 서버 | 모든 기능을 `ToolSpec`(id·effects·requires·toolset·스키마)으로 등록, UI·CLI·MCP·내장 에이전트가 같은 id로 호출. MCP는 Core 툴셋만 처음 공개하고 `enable_toolset`으로 확장, 큰 결과는 `evidence://<id>`로 참조, 실행·기기 변경 도구는 동의 필요 | `crates/engine/src/tool.rs` `ToolSpec`, `lib.rs` `Engine::call`, `registry.rs`, `crates/mcp/src/lib.rs` `serve` | 1 | 핵심 | `capabilities/tool-contract-and-mcp.md` · 미작성 | 코드 확인(머리 주석) |
| 13 | 코딩 에이전트 구동·앱 연결 (패밀리) | Claude Code·Codex·ACP 계열을 서브프로세스로 실행하고 MCP 서버·승인 요청을 연결. 설치된 에이전트 앱에 MCP 등록·스킬 설치(계획→적용, 백업), 진단 | `crates/ai/src/cli_agents/{mod,adapters,acp,grants}.rs`, `crates/setup/src/{plan,clients,doctor,skill}.rs` | 12 | 핵심(패밀리) | `capabilities/agent-drivers-and-setup.md` · 미작성 | 코드 확인(머리 주석) · 어댑터 개별은 미탐색 |
| 14 | 내장 에이전트 루프·저널·컨텍스트 | API 모델(Anthropic·OpenAI 등)이 엔진 도구를 호출하는 루프, 동의, 모든 도구 호출·모델 턴을 저널로 남기고 `core_journal_read`로 재조회 | `crates/ai/src/{agent,context,model}.rs`, `crates/engine/src/journal.rs` | 12 | 핵심 | `capabilities/builtin-agent-loop.md` · 미작성 | 코드 확인(머리 주석) · 본문 미확인 |
| 15 | 분석 도구 본체 (패밀리) | 파서(formats 80 파일)·네이티브(disasm)·JS/Electron·웹사이트 캡처·플랫폼별(Apple·Android·Java·.NET·펌웨어·패킷·DB) 도구 수백 개. 우리 절차와 직접 대응 없음 | `crates/formats/`, `crates/disasm/`, `crates/js/`, `crates/analysis/`, `crates/engine/src/tools/*_tools.rs`, `docs/tools.md` | 1, 12 | 핵심(목적 밖 묶음) | `capabilities/analysis-toolsets.md` · 미작성 | 코드 확인(파일·도구 목록) · 미탐색 |
| 16 | 외부 엔진 어댑터·프로세스 안전 | Ghidra·adb·Frida·JADX 등 서브프로세스를 데드라인·출력 상한·종료 보장으로 실행, 데드락 방지 Mutex | `crates/engines/src/`, `crates/platform/src/{process,sync}.rs` | 없음 | 핵심(목적 밖 묶음) | `capabilities/engines-and-process-safety.md` · 미작성 | 코드 확인(파일 목록·AGENTS.md 주장) · 미탐색 |
| 17 | 프로젝트·워크스페이스 저장 | `craft.json`(요청·대상·상태·이력, 버전·마이그레이션), `.cany` 조사 폴더(원자적 쓰기), 고정 빌드(pins), 피드 | `crates/engine/src/workspace.rs` `Workspace`·`MANIFEST`·`TargetRef`, `project.rs`, `pins.rs`, `feed.rs` | 1 | 핵심 | `capabilities/workspace-store.md` · 미작성 | 코드 확인(머리 주석·`TargetRef`) |
| 18 | 표면: 데스크톱 UI·CLI·웹 뷰어 | egui Simple/Advanced 화면, CLI 서브명령(`rebuild`·`mcp`·`report`·`chat`·도구 직접 실행), 브라우저 WASM 뷰어 | `crates/ui-egui/src/`, `apps/craft-anything-cli/src/main.rs`, `apps/craft-anything-web/` | 7, 12, 17 | 부속 | `capabilities/surfaces.md` · 미작성 | 코드 확인(파일 목록·CLI `Command`) · 미탐색 |
| 19 | 플러그인·에셋 생성 | `config.toml`의 MCP 서버·WASM 컴포넌트가 새 툴셋이 됨(WASM은 import 없음·fuel·메모리 상한). fal.ai 이미지·3D 생성(옵트인, 예산) | `crates/engine/src/plugins.rs`, `crates/engines/src/{wasm_plugin,assets/}` | 12 | 부속 | `capabilities/plugins-and-assets.md` · 미작성 | 코드 확인(머리 주석) · 미탐색 |
| 20 | 릴리스·패키징·xtask | 플랫폼별 설치본, 레이어·락·비밀 검사, 도구 문서 생성 | `xtask/src/main.rs`, `packaging/`, `.github/workflows/release.yml` | 없음 | 부속 | `capabilities/release-and-xtask.md` · 미작성 | 코드 확인(파일 목록) · 미탐색 |

20행(핵심 16 / 부속 4). 공유 계약은 행 1(증거 레코드)과 행 12(`ToolSpec`·`ToolError`)가 겸하므로 별도 표를 두지 않는다.

**대표 흐름** (통합 검토 4장 5번 4항. 스펙 11개를 잇는 글이며, 각 연결의 근거는 괄호 안 스펙의 R-ID)

사용자가 대상과 요청을 주면 리빌드 루프(7)가 시작한다. 루프는 빌더에게 줄 브리프(8)를 만들고(고정 규칙 + 대상 종류별 절), 대상 종류(9)가 정한 `Check`로 결과를 판정한다. 빌더는 조사 중 모르는 것을 미해결 질문(2)으로 기록하고, 사람에게 물을 것은 인박스(10)로 보내며, 사용자가 중간에 쓴 노트도 인박스로 전달된다. 도구 호출은 Clean room이면 허용 목록(11)으로 제한되고, 모든 결과는 증거 레코드(1)로 남는다. 외부 코딩 에이전트가 직접 조사할 때는 방법 지침(5)을 따라 조사 작업 기억(3)에 finding을 쌓고, 보고서(4)는 그 finding에서 만든다. 재구성 원장(6)은 이 흐름 밖에서 별도 도구로만 호출되며 루프와 연결되지 않는다(rebuild-loop 스펙).

**통합 검토 결과** (2026-11-15, 메인이 `check.py`와 스펙 frontmatter로 확인): (1) 행 1~11 모두 스펙 파일과 상태가 있다(`ready` 11). (2) 선행·`depends`의 스펙 파일이 존재하고 링크 오류가 없다(`check.py` ERROR 0). (3) 일부 스펙은 `depends`에서 설명용 링크를 뺐다(예: investigation-memory는 unknown-ledger를 뺌). (4) 7↔9 순환은 9를 먼저 쓰는 것으로 끊었다. (5) 위 대표 흐름은 스펙 요약을 이은 글이고, 실제 실행으로 확인하지 않았다(코드 읽기만).

**우리 절차와 맞대어 본 결과** (2026-11-15, 스펙 11개의 "적용 메모"를 취합. 판정 근거는 괄호 안 스펙. 2026-11-15에 Codex 검토를 거쳐 A·G·I 등을 조정한 뒤 일부를 `OSS_ANALYSIS_WORKFLOW.md`·스킬·템플릿·`check.py`에 반영했다: 4장 5번 원본 대조 점검(기본 메인 점검, 독립 검토는 조건부), 재구현 검증은 선택·사용자 승인 시에만, `ready` 의미 정리와 보고 문구, 부재 주장·U-ID 표·`sources` 확장·요청 템플릿(B·C·D·H·K), `check.py` 인용 줄 범위 검사. E(`next.md` 막힌 경로)도 반영했다. 미반영: J·M(P2, 사용자 결정으로 보류), 테스트 표적 열람, 해시 ID·숫자 신뢰도 등 기각 항목. **이 레포의 11개 스펙은 새 기준 이전의 `ready`**라 2.4 검토 기록이 없고 "새 기준 검토 미실시, 재구현 미수행"이다)

| # | 우리 절차 | craft-anything에서 확인한 것 | 판정 | 제안 | 근거 스펙 |
|---|---|---|---|---|---|
| A | 검증 수준 3단계(7장) | `Confidence`·`Authority`·`Coverage`(쪽 나누기 숫자일 뿐 검색 범위는 아님). `Environment.clean_room` 값의 뜻이 주석과 다름 | 수정 후 채택 | `코드 확인`을 "직접 읽음"과 "검색·도구 결과"로 나눈다. 새 칸을 만들기 전에 값의 정의부터 고정. 증거마다 해시 id는 기각 | evidence-record, clean-room-mode |
| B | 7장에 "없음" 규칙 없음 | skill.md 규칙 + 분석기가 결과에 한계 문구를 직접 넣음 | 확정 | 7장에 "찾지 못함은 증거가 아니다" 한 줄, 스펙 템플릿 2.1에 "없다/전부다" 주장의 검색 명령·범위 필수 | method-guidance, evidence-record |
| C | 미결정·확인 한계는 자유 서술(4장) | `Unknown`: 상태·중요도·확인 방법·찬반 증거. 근거 요구는 쓸 때 막지 않고 verify 도구가 따로 검사 | 형식 확정, 강제는 수정 | `U-ID · 질문 · 확인 방법 · 영향` 목록, 해소 항목은 `resolved · 근거`로 남김, 근거 검사는 `check.py`. 개정번호는 기각 | unknown-ledger |
| D | `check.py`는 SHA·index·상태·링크만 점검(1장) | finding은 증거 id의 **존재**만 검증, 내용·신뢰도 일치는 검사 안 함 | 확정, 범위 한정 | 인용한 `파일:줄`이 기준 SHA에 존재하는지, `코드 확인` R-ID에 `파일:줄`이 있는지까지만 기계 검사. 내용 대조는 사람 | investigation-memory |
| E | `next.md`·`handoff.md`(6장) | handoff는 자유 문장, 실패한 시도는 저널이 호출 단위로 자동 보존 | 확정, 작게 | `next.md`에 `막힌 경로: 시도 · 결과 · 다시 하지 말 이유` 칸 | investigation-memory |
| F | 재구현 검증: 워크플로 본문에 단계 없음, 스킬 41행에만 "요청 시" | 원장의 `proven`은 증거 존재·해시만 보고 강도는 호출자 선언(약점). 사례 3종·상태 어휘(disproved/unclear/built/proven) | 확정 + 보완 | R-ID에 사례 종류(정상·거부·잘못된 입력) 열을 붙이고 재구현 후 R-ID별 충족 표를 만든다. 강도는 선언이 아니라 `artifacts/` 실행 기록으로 정하는 3단계(읽기 대조 < 재구현 단독 실행 < 원본 대조 실행) | rebuild-ledger |
| G | 재구현 검증 반복·미검증 처리 | `can_refine=false`=오라클 없음. `passed`(작동)와 `good`(일치) 분리, 비교 못 한 것은 통과 아님. 멈춤 조건 3개 + 검사 도구 오류 재시도 | 수정(앞서 쓴 "스펙 결함 vs 환경 한계"는 틀린 해석) | R-ID별 작동/일치/미검증(사유: 오라클 없음) 표, 재시도는 고칠 수 있는 항목에만, 검증 도구 실패는 별도 분류, 카운트는 세션을 넘겨 저장, 무변경 연속 2회면 사용자에게 넘김 | check-contract, rebuild-loop |
| H | 스펙 작업 지시문(`capability-request-template.md`) | 규칙이 코드 상수로 고정, 모든 요청에 같은 규칙 블록 | 확정 + 보강 | 요청 템플릿을 "작업별 목표·단계 + 공통 규칙 블록"으로 나누고, "범위를 줄이려면 먼저 묻기", "미결정마다 확인 방법·중요도", "작업자가 보고 전에 자기 출력에 기계 점검", "받을 때 `git status`로 출력 파일 밖 변경 확인", "분석 목적 칸" 추가 | builder-brief |
| I | 작성자/구현자 분리(암묵) | 분리를 규칙 문구가 아니라 도구 허용 목록으로 강제(기본 거부). 단 `settings_set`이 모드를 푸는 구멍 | 수정 | 재구현 검증에 "레포를 읽을 수 없는 별도 세션에 스펙만 입력한다"는 조건을 넣는다. 허용 경로 목록만 두고 나머지 거부. 경계를 푸는 동작은 허용하지 않는다 | clean-room-mode |
| J | 사용자 결정 대기(`handoff.md`) | 선택지 2~4개 질문·승인을 파일로 주고받음. 답이 없으면 가정을 밝히고 계속 | 필요성 낮음, 일부 채택 | 파일 프로토콜은 기각. `handoff.md` 항목에 "임시 가정"과 "그 가정에 기대어 쓴 문서", 사용자 원문 한 줄 인용 칸 | person-inbox |
| K | (없음) 통합 검토·세션 마무리 | skill.md의 "보고한 결론이 기록된 finding과 일치하는가" | 신규 | 스펙 완료 점검·세션 마무리에 "보고한 결론이 R-ID와 일치하는가" 추가 | method-guidance |
| L | (없음) overview feature map | 가설 목록(hypothesis)에 상태·근거 | 신규 | feature map에 `상태(testing/supported/refuted)`와 `근거 스펙` 열을 두는 것은 보류(현재 상태 칸으로 충분한지 먼저 판단) | investigation-memory |
| M | 목록 상한 처리 | 상한에서 자를 때 생략 개수를 같이 적음(pitfalls) | 신규, 작게 | `check.py`·문서 목록에서 자를 때 개수 표시 | investigation-report |

**스펙 작성 중 발견한 원본의 버그·문서와 구현의 차이** (우리 절차와 무관, 참고용. 각 스펙 2.1에 있음)
- `game-self-test` 판정이 반대다(`kinds/self_test.rs:87-101`, 직접 확인).
- 재다듬기 상한이 실행을 넘어 유지되지 않는다(`rebuild/mod.rs:956`). 공백 메시지로 연속 실패 상한을 지울 수 있다(`:948`). 도구 `rebuild_start`는 설정 `build.good_enough`를 무시한다.
- `resolution_is_valid`는 호출처가 없다. `CASE_KINDS`는 미사용이다. `settings_set`은 Clean room에서 모드를 풀 수 있다.
- README의 "320 tools"와 `docs/tools.md`의 303은 확인하지 않았다(`cargo xtask tools` 미실행).

**대조한 범위와 미탐색 영역**
- 대조: README, `AGENTS.md`, 워크스페이스 `Cargo.toml`, `docs/tools.md` 툴셋 제목, 행 1~12의 진입 파일(위 표의 "검증 수준"에 읽은 정도 표시), CLI `Command`.
- 문서와 구현의 차이: README는 "320 tools", `docs/tools.md`는 "303 engine tools"(AI·설정 계층 도구가 더해진 수인지 미확인). `cargo xtask tools`를 실행하지 않았다.
- 미탐색: 도구 구현 본문 전체(`crates/engine/src/tools/*` 약 80 파일), 파서 개별 구현과 `tests/` fixture, `vendor/wgpu-hal/`, `docs/ROADMAP.md`·`STATUS.md`·`pitfalls.md`(본문), `js_ledger.rs`의 평가 로직, `rebuild/mod.rs`의 정체 감지·라운드 본문, 패키징·CI·번역 tsv. 실행·빌드는 하지 않았다.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

이번 세션에서는 구조도를 그리지 않았다(사용자 요청). `AGENTS.md`의 층 구분(L0~L6)이 구조도의 초안 근거다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | 미작성 | 미작성 | — |

### 그림 해설 (임시: 층 구조 요약)

`AGENTS.md` "Workspace map"과 `Cargo.toml` `[workspace.dependencies]`가 같은 13개 crate를 가리킨다(코드 확인). 층 규칙은 `cargo xtask layers`가 강제한다고 문서가 말하나 실행하지 않았다(미확인).

| 층 | crate | 맡은 일 | 근거 |
|---|---|---|---|
| L0 | evidence, formats | 증거 레코드·오류 계약 / I/O 없는 파서 모음 | `crates/evidence/src/lib.rs`, `crates/formats/src/lib.rs` |
| L1 | disasm, js | 자체 디스어셈블·pseudo-C / JS 번들 분석 | `crates/disasm/src/lib.rs`, `crates/js/src/lib.rs` |
| L2 | analysis, platform | 증거를 만드는 분석기 / 프로세스·락·파일 서비스 | `crates/analysis/src/lib.rs`, `crates/platform/src/lib.rs` |
| L3 | engines | 외부 엔진 어댑터 | `crates/engines/src/lib.rs` |
| L4 | engine | 세션·프로젝트·워크스페이스·인박스·ToolSpec 레지스트리 | `crates/engine/src/lib.rs` |
| L5 | ai, mcp, setup | AI 백엔드·리빌드 / MCP 서버 / 에이전트 앱 연결 | `crates/ai/src/rebuild/mod.rs`, `crates/mcp/src/lib.rs`, `crates/setup/src/lib.rs` |
| L6 | ui-egui | egui UI(유일하게 egui 사용) | `crates/ui-egui/src/lib.rs` |

**읽는 순서(제안)**: `AGENTS.md` → `crates/engine/src/tool.rs`(ToolSpec) → `registry.rs`·`clean_room.rs` → CLI `main.rs` `Command` → `crates/ai/src/rebuild/mod.rs` 머리 주석과 `RebuildRun::start` → `kinds/mod.rs`.

**미확인 영역**: crate 사이 실제 의존 방향, 호출 흐름, 각 행의 동작 규칙.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸 (모두 미작성)
