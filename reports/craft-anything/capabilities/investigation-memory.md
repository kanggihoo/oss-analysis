---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/engine/src/tools/investigation_tools.rs
  - crates/engine/src/journal.rs
  - crates/engine/src/session.rs
  - crates/engine/src/lib.rs
  - crates/engine/src/clean_room.rs
  - crates/ai/src/prompt.rs
  - crates/mcp/src/prompts.rs
  - docs/pitfalls.md
depends:
  - ./evidence-record.md
status: ready
---

# 조사 작업 기억 (brief · plan · hypothesis · finding · handoff, 저널 읽기)

> 한 조사의 질문·목적·완료 기준(brief), 단계 계획(plan), 예측이 달린 가설(hypothesis), 증거 id가 원장에 실제로 있어야만 기록되는 결론(finding), 다음 작업자를 위한 인계 메모(handoff)를 하나의 개정 번호가 붙은 상태로 저장하고, 프로젝트가 열려 있으면 JSON 원본과 읽기용 Markdown 5개를 함께 쓰며, 프로젝트 저널에 남은 모든 도구 호출 기록을 쪽 단위로 읽게 한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 에이전트가 조사를 시작하거나 이어받을 때 `core_investigation_show`로 현재 상태를 읽는다(R-03).
2. 새 질문이면 `core_brief_write`로 질문·목적·대상·제약·완료 기준을 적고, `core_plan_update`로 단계 목록을 통째로 쓴다(R-07, R-08).
3. 확인할 주장은 `core_hypothesis_record`로 남기고(상태 testing), 결과에 따라 `core_hypothesis_update`로 상태와 찬반 증거·메모를 더한다(R-09, R-10).
4. 결론은 `core_finding_record`로 남긴다. 증거 id가 하나 이상 있어야 하고, 모든 id가 선행 스펙의 원장에서 찾아져야 기록된다. 틀린 결론은 `core_finding_edit`로 같은 id를 유지한 채 고친다(R-11, R-12, R-16).
5. 쓰기 도구는 모두 같은 순서를 따른다: 입력·증거 id 검사 → (프로젝트가 있으면) 파일 잠금 → 디스크 상태 읽기 → 바꾸기 → revision +1·시각 기록 → `state.json`과 Markdown 5개 쓰기 → 메모리 사본 갱신(R-04, R-14).
6. 턴이 끝날 때 `core_handoff_write`로 "어디까지 왔고, 다음은 무엇이고, 피할 함정은 무엇인지"를 통째로 다시 쓴다(R-13).
7. 엔진은 프로젝트가 열려 있으면 이 도구들을 포함한 모든 도구 호출을 날짜별 JSONL 저널에 남기고, `core_journal_read`로 날짜·종류·도구별로 걸러 읽는다(R-20, R-21).

### 1.2 범위·통합 지점
- 제공: 조사 상태(`Investigation`)의 모양과 저장 위치, 도구 9개(`core_investigation_show`, `core_brief_write`, `core_plan_update`, `core_hypothesis_record`, `core_hypothesis_update`, `core_finding_record`, `core_finding_edit`, `core_handoff_write`, `core_journal_read`)의 입력·출력·오류, revision 검사, 프로세스 사이 파일 잠금, Markdown 렌더, 외부 에이전트용 공유 프로젝트 생성 시 상태 옮기기, 도구 호출 저널 항목의 형식.
- 제외:
  - 보고서 생성(행 4 [investigation-report.md](investigation-report.md)).
  - 미해결 질문(행 2). 조사 상태에는 unknown을 가리키는 칸이 없다.
  - 저널의 다른 항목 종류(`model_turn`, `consent`, `user_message`, `error` 등)를 쓰는 쪽(행 14). 이 스펙은 `Engine::call`이 쓰는 `tool_call` 항목과 읽기 도구만 다룬다.
  - 에이전트에게 이 도구들을 언제 쓰라고 지시하는 문구(행 5). 경계: MCP 지침은 "core_investigation_show 먼저, 새 질문엔 brief·plan, finding은 증거 id와 함께만, 멈추기 전에 handoff"라고 지시한다(`crates/mcp/src/prompts.rs:32`), 내장 에이전트 프롬프트도 같은 순서를 지시한다(`crates/ai/src/prompt.rs:24`).
- 외부 의존·선행 계약:
  - 선행 [evidence-record.md](evidence-record.md): `resolve_evidence`(R-17), `Confidence`와 `plain_label`, `ToolError`·`parse_params`, `write_atomic`.
  - 운영체제 파일 잠금(`std::fs::File::try_lock`, 배타 잠금): 다른 프로세스가 잡고 있으면 즉시 `WouldBlock`, 파일 핸들을 닫으면 풀린다.
  - 시스템 시계(UTC, 초 단위): `updated` 칸과 저널 시각.
- 소유 상태·부작용: 프로젝트가 열려 있으면 `<project>/investigation/` 아래 `state.json`, `brief.md`, `plan.md`, `hypotheses.md`, `findings.md`, `handoff.md`, `update.lock`과 `<project>/journal/YYYY-MM-DD.jsonl`. 프로젝트가 없으면 세션 확장 슬롯의 메모리 상태(세션이 끝나면 사라짐). 어느 경우든 세션에 마지막으로 읽거나 쓴 상태의 사본(캐시)을 둔다(UI가 그리는 중 디스크를 읽지 않도록).

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `Investigation` (`state.json`) | map `{revision: u64, brief?: Brief, plan: [PlanStep], hypotheses: [Hypothesis], findings: [Finding], handoff?: string, updated?: string}` | 조사 하나의 원본 상태. 없으면 revision 0의 빈 상태. `updated`는 마지막 저장 시각 `YYYY-MM-DDThh:mm:ssZ`(UTC). 형식 버전 칸은 없다. |
| `Brief` | `{question: string, purpose?: string, targets: [string], constraints: [string], done_when?: string}` | 답할 질문, 이유, 대상(경로·패키지·URL), 제약(clean room, 대상 실행 금지, 시간 예산 등), 끝났다고 볼 기준. |
| `PlanStep` | `{title: string, status: todo/doing/done/blocked (기본 todo), why?: string}` | 순서 있는 단계. |
| `Hypothesis` | `{id: "hyp_<n>", claim, prediction?, status: testing/supported/refuted/abandoned, supporting: [증거 id], contradicting: [증거 id], notes: [string]}` | 검증 중인 주장과 맞다면 관찰될 것. |
| `Finding` | `{id: "fnd_<n>", statement, evidence_ids: [증거 id, 1개 이상], confidence: observed/derived/inferred}` | 확정된 답. 보고서의 원천. |
| `handoff` | string | 다음 턴·다음 에이전트를 위한 메모 한 덩어리. |
| `core_investigation_show` | in `{}` → `{revision, updated, brief, plan, hypotheses, findings, handoff, stored_in}` | `stored_in`은 조사 폴더 경로 또는 `"session (no project open)"`. |
| `core_brief_write` | in `{question, purpose?, targets=[], constraints=[], done_when?}` → show와 같은 전체 상태 | brief 전체를 교체. |
| `core_plan_update` | in `{steps: [PlanStep], based_on_revision?}` → 전체 상태 | plan 전체를 교체. |
| `core_hypothesis_record` | in `{claim, prediction?, evidence_for=[], evidence_against=[]}` → `{hypothesis_id, revision}` | |
| `core_hypothesis_update` | in `{hypothesis_id, status?, add_supporting_evidence_ids=[], add_contradicting_evidence_ids=[], note?}` → `{hypothesis: Hypothesis, revision}` | |
| `core_finding_record` | in `{statement, evidence_ids, confidence="inferred"}` → `{finding_id, revision}` | |
| `core_finding_edit` | in `{finding_id, statement, evidence_ids, confidence?, based_on_revision?}` → `{finding_id, revision}` | |
| `core_handoff_write` | in `{text}` → `{revision}` | |
| `core_journal_read` | in `{day?: "YYYY-MM-DD", kind?, tool?, offset=0, limit?}` → `{day, days, total, entries, next_offset}` | `days`는 저널이 있는 날짜 오름차순, `total`은 걸러낸 뒤 개수, `next_offset`은 더 없으면 `null`. |
| 저널 `tool_call` 항목 | JSON 한 줄 `{tool, caller, params, duration_ms, ok, evidence_id? \| error_code?+error?, ts, time, kind: "tool_call"}` | `ts`는 유닉스 초, `time`은 `YYYY-MM-DDThh:mm:ssZ`. 성공이면 `ok: true`(증거 반환이면 `evidence_id` 추가), 실패면 `ok: false, error_code, error`. |

모든 입력 구조체는 알 수 없는 칸을 거부한다. 타입·enum 오류는 선행 스펙 R-25의 `bad_input`이다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | revision | 저장할 때마다 이전 revision + 1(포화 덧셈). 아무것도 저장한 적 없으면 0이고 첫 저장이 1이다. 내용이 바뀌지 않는 호출(예: R-10에서 아무 칸도 주지 않음)도 저장이므로 revision이 오른다. | 코드 확인 |
| R-02 | 저장 위치 | 프로젝트가 열려 있으면 `<project>/investigation/`, 아니면 세션 메모리. | 코드 확인 |
| R-03 | 읽기(`core_investigation_show`, 보고서 등이 쓰는 `load`) | 프로젝트가 있으면 매번 디스크의 `state.json`을 읽는다. 파일이 없거나 읽기·파싱에 실패하면 오류 없이 빈 상태(revision 0)를 준다. 프로젝트가 없으면 세션 메모리 상태. 읽기 도구는 캐시를 갱신하지 않는다. | 코드 확인 |
| R-04 | 쓰기 도구의 공통 순서 | (1) 입력 검사와 증거 id 검사(R-16) → (2) R-14 잠금 → (3) 수정용 읽기: 프로젝트의 `state.json`이 없으면 빈 상태, 파싱 실패면 `garbled_output` "The investigation state could not be read; it was not changed."(remediation: 유효한 백업으로 되돌리기), 그 밖의 읽기 오류는 io 오류. 프로젝트가 없으면 메모리 상태 → (4) 바꾸기·revision 검사 → (5) 저장: revision +1, `updated` 기록, `state.json`을 pretty JSON으로 원자적 쓰기, 이어서 `brief.md`·`plan.md`·`hypotheses.md`·`findings.md`·`handoff.md`를 이 순서로 각각 원자적 쓰기 → (6) 캐시 갱신 → (7) 잠금 해제(도구가 끝날 때). (1)·(3)·(4)에서 실패하면 디스크와 캐시는 그대로다. | 코드 확인 |
| R-05 | (5)에서 Markdown 쓰기 하나가 실패 | 오류를 돌려주지만 `state.json`은 이미 새 revision으로 바뀌었고 앞서 쓴 Markdown도 새 내용이다. 캐시는 갱신되지 않는다(다음 `open_project` 때 맞춰짐). 파일 묶음 전체의 원자성은 없다. | 코드 확인 |
| R-06 | Markdown 렌더 | `state.json`에서만 만든다. 형식은 C-03. 빈 칸은 `_No brief yet._`, `_No plan yet._`, `_None yet._`, `_No handoff yet._`. 가설 제목의 상태는 Rust Debug 이름(`Testing`, `Supported` …), finding의 확실성은 선행 스펙의 사람용 이름("Seen it" 등). 사용자 문자열은 escape하지 않는다. | 코드 확인 |
| R-07 | `core_brief_write` | `question`을 trim해 비면 `bad_input` "The brief needs a question." 통과하면 brief 전체를 입력으로 교체한다(생략한 칸은 비워짐). 저장되는 question은 trim하지 않은 원문. revision 인자가 없다. | 코드 확인 |
| R-08 | `core_plan_update` | 단계가 200개를 넘으면 `bad_input` "A plan can have at most 200 steps."(잠금 전). `based_on_revision`을 주고 현재 revision과 다르면 `stale_revision` "The investigation is at revision <R>, not <B>.", remediation "Call core_investigation_show, merge your change, and retry with the current revision." 생략하면 검사 없이 덮어쓴다. plan 전체를 교체하고 단계 제목은 검사하지 않는다(빈 문자열 허용). | 코드 확인 |
| R-09 | `core_hypothesis_record` | `claim`을 trim해 비면 `bad_input` "A hypothesis needs a claim." `evidence_for`·`evidence_against`의 모든 id를 R-16으로 검사. id는 `hyp_<현재 가설 수 + 1>`, 상태 testing, notes 빈 목록. revision 인자가 없다. | 코드 확인 |
| R-10 | `core_hypothesis_update` | 더할 증거 id를 R-16으로 먼저 검사. 가설이 없으면 `bad_input` "No hypothesis <id>"(remediation "See core_investigation_show for the ids."). status를 주면 바꾼다(전이 제한 없음). 더할 id는 이미 목록에 없을 때만 뒤에 붙인다(입력 안의 중복도 한 번만). note는 공백만이 아니면 notes 뒤에 붙인다. 출력의 `hypothesis`는 바뀐 뒤의 값. revision 인자가 없다. | 코드 확인 |
| R-11 | `core_finding_record` | `statement`를 trim해 비면 `bad_input` "A finding needs a statement." `evidence_ids`가 비면 `bad_input` "A finding must cite at least one evidence id."(remediation "Run the analysis that shows it, then cite the evidence id it returns.") 그다음 모든 id를 R-16으로 검사. id는 `fnd_<현재 finding 수 + 1>`. confidence 생략 시 `inferred`. 주어진 confidence가 인용한 증거들의 confidence와 맞는지는 검사하지 않는다(예: inferred 증거만 인용하고 observed로 기록 가능). revision 인자가 없다. | 코드 확인 |
| R-12 | `core_finding_edit` | statement가 공백이거나 `evidence_ids`가 비면 `bad_input` "A finding needs a statement and at least one evidence id." id 검사(R-16) → 잠금 → 읽기 → `based_on_revision`이 있으면 R-08과 같은 검사 → finding이 없으면 `bad_input` "Unknown finding <id>". statement와 `evidence_ids`를 통째로 교체하고 confidence는 줄 때만 바꾼다(생략하면 기존 값 유지). id는 그대로. | 코드 확인 |
| R-13 | `core_handoff_write` | `text`로 handoff 전체를 교체. 빈 문자열도 받는다. revision 인자가 없다. | 코드 확인 |
| R-14 | 잠금 | 프로젝트가 있으면 조사 폴더를 만들고 `update.lock`을 열어(없으면 생성, 내용은 비우지 않음) 배타 파일 잠금을 시도한다. 잡혀 있으면 5 ms 간격으로 최대 10초 다시 시도하고, 시도 전·매 반복마다 취소를 확인한다(취소면 `cancelled`). 10초가 지나면 `timed_out` "Another process is updating this investigation."(remediation "Wait for the other update, reload the investigation and retry with its current revision."). 프로젝트가 없으면 파일 잠금 없이 진행한다(같은 세션의 도구 호출은 엔진의 세션 잠금으로 이미 한 번에 하나다). 잠금을 잡은 뒤 저장 직전에 조사 폴더 경로가 바뀌었으면 `internal` "The investigation changed while its update lock was held." | 코드 확인 |
| R-15 | 같은 프로젝트에 두 프로세스가 동시에 쓰기 | R-14 잠금 안에서 읽기·수정·쓰기가 이뤄지므로 추가(append) 쓰기는 하나도 잃지 않고 id도 겹치지 않는다. 둘이 같은 `based_on_revision`으로 plan을 바꾸면 하나만 성공하고 다른 하나는 `stale_revision`. revision 인자가 없는 도구(brief·hypothesis·finding_record·handoff)는 낡은 읽기를 막지 않는다. | 코드 확인 · 원본 테스트 열람 |
| R-16 | 증거 id 검사 `check_ids` | 목록 순서대로 선행 스펙 `resolve_evidence`로 찾고, 처음 실패한 id에서 `bad_input` "Unknown evidence id <id>"(remediation "Cite ids returned by analysis tools (see core_evidence_show).")로 멈춘다. 선행 스펙의 `details`(`reason: missing`)는 이 오류에 실리지 않는다. 메모리 원장 또는 프로젝트 저장소(변조 검사 포함)에 있으면 통과한다. 검사는 존재만 본다: 증거의 내용이 statement를 뒷받침하는지는 보지 않는다. | 코드 확인 |
| R-17 | id 부여 | `hyp_`·`fnd_` 번호는 목록 길이 + 1이다. 가설·finding을 지우는 도구가 없으므로 같은 상태 안에서 번호가 겹치지 않는다(전제: `state.json`을 손으로 고치지 않음). | 코드 확인 |
| R-18 | 외부 에이전트용 공유 프로젝트(`ensure_shared_project`) | 이미 프로젝트가 열려 있으면 그 경로를 준다. 없으면 현재 조사 상태를 읽고, `<config>/investigations/session-<나노초>.cany` 프로젝트를 만들고, 메모리 원장의 증거와 unknown을 모두 그 프로젝트에 쓴 뒤 프로젝트를 붙인다. 이어 조사 상태를 저장하는데, 그 폴더에 `state.json`이 이미 있으면 `stale_revision` "This project already has an investigation."이고, 저장이 실패하면 프로젝트를 다시 떼어낸다(이미 쓴 증거·unknown 파일은 남는다). 저장하면 revision이 1 오른다. | 코드 확인 |
| R-19 | 프로젝트 열기 | 증거·unknown을 올린 뒤 조사 상태를 R-03으로 읽어 캐시를 바꾼다. 다른 프로세스가 쓴 finding은 이 시점에 캐시에 들어온다. | 코드 확인 |
| R-20 | 저널 `tool_call` 기록 | 프로젝트가 열려 있으면 `Engine::call`이 모든 도구 호출(없는 도구 id, 입력 오류, Clean room 거부, 동의 거부 포함)의 결과를 1.3 형식으로 `journal/<UTC 날짜>.jsonl`에 한 줄 덧붙인다. `params`는 비밀 이름 칸(C-05의 목록, 대소문자 무시, 모든 깊이)의 값을 `"(redacted)"`로 바꾼 뒤 JSON 텍스트가 4,096바이트를 넘으면 `{"omitted": "too large for the journal", "bytes": <길이>}`로 바꾼다. 쓰기 실패는 경고 로그만 남기고 도구 결과에 영향을 주지 않는다. 프로젝트가 없으면 남기지 않는다. | 코드 확인 |
| R-21 | `core_journal_read` | 프로젝트가 없으면 `feature_missing` "The journal is kept per project, and no project is open."(remediation "Open or create a project (.cany) first."). day를 생략하면 가장 최근 날짜, 저널이 없으면 `""`. day가 10자의 숫자·`-` 형식이 아니면 오류 없이 빈 결과. 읽을 수 없는 줄은 건너뛴다. kind·tool은 JSON 값 완전 일치. limit 기본 50, 1~500으로 자른다. offset부터 limit개를 주고, 더 남았으면 `next_offset = offset + 준 개수`. | 코드 확인 |
| R-22 | 모드·효과 | 9개 모두 Core 툴셋, Clean room에서도 허용. show·journal_read는 읽기 전용, 나머지 7개는 세션 변경 + 파일 쓰기로 선언한다. | 코드 확인 |
| R-23 | 조사 항목과 증거의 관계 | brief·plan·가설·finding·handoff는 증거 레코드가 아니다(`ToolOutput::Value`). 원장에 들어가지 않고 해시 id도 없다. finding과 증거를 잇는 것은 `evidence_ids` 문자열뿐이다. | 코드 확인 |

- 불변식: 디스크의 `state.json`이 유효한 JSON이면, 쓰기 도구는 잠금을 잡은 상태에서 읽은 그 내용 위에서만 바꾼다(빈 상태로 덮어쓰지 않는다, R-04 (3)). 기록된 모든 finding은 기록 시점에 증거 id 1개 이상이 원장에서 찾아졌다(이후 증거가 사라지는 경로는 없다, 선행 스펙 R-24).
- 미결정: 없음.
- 확인 한계: 정적 읽기만 했다. 여러 프로세스 쓰기 보장(R-15)은 원본 테스트 코드를 읽어 확인했고 실행하지 않았다. `File::try_lock`이 네트워크 파일 시스템에서 배타성을 보장하는지는 운영체제·파일 시스템에 달려 있어 확인하지 않았다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/engine/src/tools/investigation_tools.rs:127-209` `Brief`·`StepStatus`·`PlanStep`·`HypothesisStatus`·`Hypothesis`·`Finding`·`Investigation` | 상태 모양, serde 기본값·생략 규칙 | R-01 |
| C-02 | `investigation_tools.rs:226-318` `dir`·`load`·`UpdateLock::acquire`·`lock_update`·`load_for_update`·`save_new_project`·`save` | 읽기·잠금·저장 순서, 상수(10초, 5 ms) | R-03, R-04, R-05, R-14, R-18 |
| C-03 | `investigation_tools.rs:320-394` `render` | Markdown 5개의 정확한 형식 | R-06 |
| C-04 | `investigation_tools.rs:409-424` `check_ids`·`check_revision` | 검사 문구 | R-08, R-12, R-16 |
| C-05 | `crates/engine/src/journal.rs:13-64`, `:158-212` `MAX_FIELD_BYTES`·`now_utc`·`civil`·`bounded`·`SECRET_FIELDS`·`redacted`·`append`·`days`·`read_day` | 저널 항목 크기 상한, 비밀 칸 이름 목록, 날짜 계산, 파일 이름 규칙 | R-20, R-21 |
| C-06 | `crates/engine/src/lib.rs:213-229` `Engine::call` | `tool_call` 항목 조립 | R-20 |

### 1.6 수락 사례
출처: 사례별 표기

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-07~R-11, R-13, R-21 | 프로젝트 없이 brief → plan(`doing` 한 단계) → hypothesis(prediction 포함) → hypothesis_update(supported, note) → finding(빈 id 목록, `ev_00`) → handoff → show → plan_update(revision + 7) → journal_read (원본 테스트) | 가설 id `hyp_1`, finding 두 번 모두 오류, show에 brief·supported·handoff 반영, 낡은 revision은 `stale_revision`, journal_read는 오류(프로젝트 없음) |
| T-02 | R-04, R-06, R-20, R-21 | 프로젝트를 열고 brief(targets 포함)·handoff 쓰기, 없는 도구 호출, `journal_read {kind: "tool_call"}`, `journal_read {tool: "core_handoff_write"}` (원본 테스트) | 조사 폴더에 파일 6개, `handoff.md`에 텍스트, 저널 항목 3개 이상이고 첫 항목이 `core_brief_write`·`ok: true`, 없는 도구 항목은 `ok: false`, tool 필터 결과 `total` 1 |
| T-03 | R-04 | 프로젝트에서 brief를 쓴 뒤 `state.json`을 `not-json`으로 바꾸고 brief를 다시 씀 (원본 테스트) | `garbled_output`. `state.json`과 `brief.md`는 그대로 |
| T-04 | R-14 | 시간 0으로 잠금을 잡은 상태에서 다시 시도 / 취소 후 시도 / 첫 잠금 해제 후 시도 (원본 테스트) | `timed_out` / `cancelled` / 성공 |
| T-05 | R-15, R-17 | 두 프로세스가 각각 가설 24개 추가 (원본 테스트) | revision 48, 가설 48개, id 48개 모두 다름, Markdown이 최종 상태 렌더와 같음 |
| T-06 | R-15 | 두 프로세스가 각각 `based_on_revision: 0`으로 plan 교체 (원본 테스트) | revision 1, 결과는 하나 `ok`·하나 `stale` |
| T-07 | R-11, R-12 | 증거 하나를 기록하고 finding 기록 → `edit {confidence: observed, based_on_revision: 1}` → 같은 edit 다시 → confidence를 각각 준 edit과 생략한 edit (원본 테스트) | 첫 edit 성공, id `fnd_1` 유지·finding 1개, 두 번째 `stale_revision`, confidence 생략 시 직전 값 유지 |
| T-08 | R-12 | finding이 없는 상태에서 `evidence_ids: []`와 `["ev_missing"]`로 edit (원본 테스트) | 둘 다 오류, 상태 변화 없음 |
| T-09 | R-18, R-19 | 프로젝트 없는 세션에 증거·brief를 둔 뒤 공유 프로젝트 생성(두 번 호출), 다른 세션이 그 프로젝트를 열어 finding 기록, 원래 세션이 프로젝트를 다시 엶 (원본 테스트) | 두 번째 생성은 같은 경로, 다른 세션이 brief를 읽음, 다시 연 뒤 캐시의 finding `fnd_1` "Shared finding" |
| T-10 | R-08 | 단계 201개로 plan_update (구현에서 도출) | `bad_input`, revision 그대로 |
| T-11 | R-11 | confidence `inferred`인 증거만 인용해 `confidence: "observed"` finding 기록 (구현에서 도출) | 성공 |
| T-12 | R-01, R-10 | `hypothesis_update {hypothesis_id: "hyp_1"}`만 보냄 (구현에서 도출) | 성공, 가설 내용은 그대로, revision +1 |
| T-13 | R-03 | 프로젝트의 `state.json`을 깨뜨린 뒤 `core_investigation_show` (구현에서 도출) | 오류 없이 revision 0의 빈 상태 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-04, R-05 | C-02 `save` `:302-318`, `load_for_update` `:277-288` | |
| R-02, R-03 | C-02 `dir`·`load` `:226-236`, `core_investigation_show` `:428-431`, `out` `:396-407` | 문서 차이: `docs/pitfalls.md` "Atomic replacements still lost concurrent investigation updates"는 "Never treat malformed state as an empty update"라고 적는다. 쓰기 경로는 지키지만 읽기 경로(`load`)는 깨진 상태를 빈 상태로 보여 준다(T-13) |
| R-06 | C-03 | |
| R-07 | `:433-462` `BriefParams`·`core_brief_write` | |
| R-08 | `:464-485` `PlanParams`·`core_plan_update`, C-04 | 문서 차이: 머리 주석 `:3-4`은 상태를 "revisioned"라고 하지만 revision 비교는 plan_update와 finding_edit에서만, 그것도 인자를 줄 때만 한다 |
| R-09 | `:487-522` | |
| R-10 | `:524-568` | |
| R-11 | `:570-615` `FindingParams`·`ConfidenceParam`·`inferred`·`core_finding_record` | confidence를 증거와 비교하는 코드 없음 |
| R-12 | `:617-659` `EditFindingParams`·`core_finding_edit` | `docs/pitfalls.md` "A finding correction reset omitted confidence to inferred"가 이 동작(생략 시 유지)을 고친 이력이다 |
| R-13 | `:661-675` | |
| R-14 | C-02 `UpdateLock` `:238-275`, `save` `:303-305` | |
| R-15 | C-02, 테스트 `:778-843` | 원본 테스트 열람 |
| R-16 | C-04 `check_ids`, 선행 스펙 R-17 | 도구 설명(`:83`) "every id is checked against the ledger"의 ledger는 메모리 원장과 프로젝트 저장소를 모두 뜻한다 |
| R-17 | `:510`, `:606` | 삭제 도구가 `specs()` `:22-125`에 없음 |
| R-18 | `crates/engine/src/session.rs:153-176` `ensure_shared_project`, C-02 `save_new_project` `:290-300` | |
| R-19 | `session.rs:347-350` | |
| R-20 | C-06, C-05 `bounded`·`redacted`·`append` | `journal.rs:1-6` 주석이 다른 항목 종류를 나열한다(행 14) |
| R-21 | `:677-719` `JournalParams`·`core_journal_read`, C-05 `days`·`read_day` | |
| R-22 | `:22-125` `specs`, `crates/engine/src/clean_room.rs:30-38` | |
| R-23 | `:396-407`, 도구 반환이 모두 `ToolOutput::Value` | |
| T-01, T-02 | `:932-977` `memory_round_trip_without_project`·`project_files_and_journal` | 원본 테스트 열람 |
| T-03, T-04 | `:742-776` `investigation_locks_are_bounded_cancelled_and_released_on_drop`·`investigation_updates_never_replace_unreadable_state` | 원본 테스트 열람 |
| T-05, T-06 | `:778-843` `project_writer_child`·`project_writers_serialize_across_processes` | 원본 테스트 열람 |
| T-07, T-08 | `:731-740`, `:845-876` | 원본 테스트 열람 |
| T-09 | `:878-905` `shared_projects_preserve_memory_and_refresh_an_external_writers_findings` | 원본 테스트 열람 |

### 2.2 코드 읽는 순서
`investigation_tools.rs` 머리 주석 → `specs()`(도구 설명이 사용 시점을 말함) → 상태 타입 → `load`·`UpdateLock`·`load_for_update`·`save` → `render` → `check_ids`·`check_revision` → 도구 함수 순서대로 → `core_journal_read`와 `journal.rs`. 공유 프로젝트는 `session.rs` `ensure_shared_project`·`open_project` 끝부분.

## 적용 메모

overview 2절 "우리 절차와 맞대어 볼 후보" 4행(check.py로 `파일:줄` 존재 검사)과 5행(`next.md`에 함정 기록)에 대한 의견, 그리고 새 후보 하나.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-11, R-16 | **4행 후보 확정, 범위 명시.** `scripts/check.py`에 "스펙 2.1·1.5에 인용한 `파일:줄`이 frontmatter `sha`의 `repos/<repo>`에 있고 줄 범위가 파일 길이 안인가"를 검사한다. 원본의 `check_ids`도 **존재만** 본다(R-16). 근거가 결론을 뒷받침하는지, 선언한 확실성이 근거와 맞는지(R-11, T-11)는 원본도 검사하지 않으므로 우리도 기계 검사 범위를 존재·범위로 한정하고 내용 대조는 사람 검토(4장 5번)에 남긴다. | 원본에서 가장 강하게 강제되는 규칙이 "증거 id 없이는 finding 불가 + id가 실제로 있어야 함"이다. 우리 R-ID에 `파일:줄`이 없거나 틀린 경우를 지금은 사람만 잡는다. | `check.py`에 검사 하나 추가. 레포 작업트리가 기준 SHA가 아니면 `git show <sha>:<path>`로 읽어야 한다. "코드 확인" R-ID에 `파일:줄` 근거가 하나도 없으면 ERROR로 보는 규칙도 같은 검사에서 가능하다 |
| R-13, R-20 | **5행 후보 확정(작게).** `next.md`에 "시도했다 막힌 경로" 칸을 둔다. 원본의 handoff는 자유 문장 하나이고 "where we are, what's next, traps to avoid"라는 지시(도구 설명 `:105`, 파라미터 설명 `:664`)로만 형식을 정한다. 대신 저널이 실패한 도구 호출까지 자동으로 남기므로(R-20) handoff에 적지 않은 막힌 경로도 나중에 찾을 수 있다. 우리에게는 호출 단위 저널이 없으므로 그 몫을 `next.md` 칸이 맡아야 한다. | 우리 `log.md`는 세션 요약이라 실패한 시도가 남지 않는다. | `next.md` 형식에 `막힌 경로: <시도 · 결과 · 다시 하지 말 이유>` 한 줄 |
| R-09, R-10 | **새 후보.** overview 2절 "우리 절차와 맞대어 볼 후보" 표가 원본의 hypothesis와 같은 역할(검증 전 주장)이다. 표에 `상태(testing / supported / refuted)`와 `근거 스펙` 열을 더해, 스펙을 쓴 뒤 그 행이 확정·수정·기각됐는지와 어느 스펙 적용 메모가 근거인지 남긴다. | 원본은 가설에 "맞다면 관찰될 것(prediction)"과 찬반 증거를 붙여 결론(finding)과 분리한다. 지금 우리 표는 가설로 시작해 스펙이 끝난 뒤에도 같은 문장으로 남아, 무엇이 확인됐는지 표에서 보이지 않는다. | overview 2절 표 열 추가. 행 상태가 바뀌면 메인 세션이 고친다 |
| R-08, R-15 | 채택하지 않음: revision·파일 잠금 | 원본은 여러 에이전트가 같은 상태 파일을 고치므로 필요하다. 우리는 쓰기 주체를 파일 단위로 나눈다(4장 1번). | 없음 |
