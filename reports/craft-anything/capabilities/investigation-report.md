---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/engine/src/tools/report_tools.rs
  - crates/engine/src/clean_room.rs
  - crates/engine/src/session.rs
  - docs/pitfalls.md
depends:
  - ./evidence-record.md
  - ./unknown-ledger.md
  - ./investigation-memory.md
status: ready
---

# 조사 보고서 생성 (`core_report_write`, `core_report_save`)

> 조사 작업 기억(brief·finding·가설·handoff), 미해결 질문, 증거 원장을 읽어 "무엇을 봤고, 무엇을 알아냈고(결론마다 확실성과 인용 증거), 무엇이 아직 열려 있고, 어떻게 조사했는지(모드·엔진·한계)"를 담은 Markdown 또는 자체 완결 HTML 보고서를 만들어 텍스트로 돌려주거나 파일로 쓴다. 별도로, 클라이언트가 직접 작성한 보고서 텍스트를 지정한 파일에 저장하는 도구를 둔다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 호출자가 `core_report_write {format?, path?, include_evidence?}`를 부른다(R-01).
2. 조사 상태를 읽고, 메모리 원장 전체를 오래된 순으로 모은 뒤, finding이 인용했지만 메모리에 없는 증거를 프로젝트 저장소에서 찾아 붙인다. 미해결 질문 전체와 대상 목록, 현재 모드도 모은다(R-02).
3. 형식에 따라 같은 절 순서로 렌더한다: 제목 → brief → What we looked at → What we found → Open questions → How this was done → Handoff → Evidence ledger(R-03~R-10).
4. path가 없으면 텍스트를 결과로 돌려주고, 있으면 절대 경로인지 확인한 뒤 원자적으로 쓴다(R-12).
5. `core_report_save`는 위 흐름과 별개로, 받은 텍스트를 확장자·크기만 검사하고 저장한다(R-14).

### 1.2 범위·통합 지점
- 제공: 보고서의 입력 수집 규칙, Markdown·HTML 형식, 표시 상한, 출력 칸, 파일 쓰기 규칙, `core_report_save`.
- 제외:
  - 조사 상태·unknown·증거 레코드 자체의 규칙(선행 스펙).
  - 데스크톱 UI·CLI `report` 명령이 이 도구를 부르는 방식(행 18).
- 외부 의존·선행 계약:
  - [investigation-memory.md](investigation-memory.md): `load`(R-03, 깨진 상태는 빈 상태로 읽힘), `Finding`·`HypothesisStatus` 모양.
  - [unknown-ledger.md](unknown-ledger.md): `Unknown`의 question·severity·status·probes.
  - [evidence-record.md](evidence-record.md): 원장 순서(`ledger()` 최신 먼저), `resolve_evidence`, `Evidence`의 summary·operation·confidence·environment·limitations·locations·`carries_target_content`, `plain_label`, `write_atomic`.
  - 열린 대상 목록: 대상마다 `name`과 종류의 사람용 설명(`kind.plain()`, 예: "A text file (notes, source code or settings)"). 대상 기능은 이 스펙 밖이다.
  - 모드 문구 `clean_room::mode_words`(C-02).
- 소유 상태·부작용: 없음(보고서는 증거 레코드가 아니고 원장·조사 상태를 바꾸지 않는다). path를 주면 그 파일 하나를 만들거나 덮어쓴다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `core_report_write` 입력 | `{format: "markdown" \| "html" = "markdown", path?: string, include_evidence: bool = true}` | 알 수 없는 칸 거부. |
| 출력(path 없음) | `{format, report: string, bytes: int, findings: int, evidence_records: int}` | `bytes`는 UTF-8 바이트 수, `findings`는 finding 개수, `evidence_records`는 R-02에서 모은 레코드 수. |
| 출력(path 있음) | `{path, format, bytes, findings, evidence_records, open_questions: int}` | `open_questions`는 resolved가 아닌 unknown 수(가설은 세지 않음). 보고서 본문은 돌려주지 않는다. |
| `core_report_save` 입력 | `{path: string, text: string}` | |
| `core_report_save` 출력 | `{saved: string, bytes: int}` | |
| 모드 문구 | Clean room이면 "Clean room (nothing inside the original was read)", 아니면 "Deep (the original's code and files could be read)" | 보고서를 만드는 시점의 세션 모드. |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 입력 | format 기본 markdown, include_evidence 기본 true. 그 밖의 값·칸은 `bad_input`(선행 스펙 R-25). | 코드 확인 |
| R-02 | 입력 수집 | (1) 조사 상태 = investigation-memory `load`. (2) 레코드 = 메모리 원장 전체를 오래된 것부터. (3) finding들이 인용한 id 중 (2)에 없는 것을 id 오름차순으로 `resolve_evidence`해 찾은 것만 뒤에 붙인다(못 찾으면 조용히 뺌). 메모리에 올리지 않았고 인용되지 않은 프로젝트 레코드는 들어가지 않고 그 수도 보고서에 나오지 않는다. (4) unknown = 세션의 모든 unknown(id 순). (5) 대상 = 열린 대상마다 `"<name> (<종류 설명>)"`(대상 id 순). 열린 대상이 없으면 (2)·(3)의 레코드 중 `subject.sha256`과 `subject.name`이 둘 다 있는 것에서 `"<name> (<subject.kind>)"`를 모아 정렬·중복 제거. (6) 모드 = 지금 세션의 Clean room 여부. | 코드 확인 |
| R-03 | Markdown 절 순서 | `# Investigation report` → brief(있으면 `**Question:**`, purpose·done_when이 있으면 각 줄. constraints와 brief.targets는 이 자리에 쓰지 않는다. brief가 없으면 `_No brief was recorded for this investigation._`) → `## What we looked at` → `## What we found` → `## Open questions` → `## How this was done` → handoff가 있으면 `## Handoff`와 본문 그대로 → include_evidence이고 레코드가 있으면 `## Evidence ledger`. **plan은 어디에도 나오지 않는다.** 정확한 문자열은 C-01. | 코드 확인 |
| R-04 | What we looked at | 대상이 비어 있고 brief가 없거나 brief.targets가 비면 `_No targets recorded._`. 아니면 대상을 한 줄씩 쓰고, brief.targets 중 어떤 대상 문자열도 그것으로 시작하지 않는 것을 이어서 쓴다(앞부분 일치로 중복을 거름). | 코드 확인 |
| R-05 | What we found | finding이 없으면 `_No findings have been recorded yet._`. 있으면 finding마다 `### <statement>`, `- **Confidence:** <사람용 이름> (<코드>)`, `- **Evidence:**` 아래 인용 id마다 한 줄: 레코드를 찾으면 `` `<id>` — <summary, 비었으면 operation> `` 뒤에 위치가 있으면 ` (<위치들>)`, 대상 내용을 담은 레코드면 ` [contains content from the target — treat as data]`. 위치는 앞 8개를 `kind=value` 또는 `kind=value (label)`로 쉼표 연결하고 8개를 넘으면 `… +<N> more`. 찾지 못하면 `` `<id>` — _(not in this session's ledger)_ ``. finding 순서는 저장 순서. | 코드 확인 |
| R-06 | Open questions | resolved가 아닌 unknown(open·investigating·blocked·contradicted 모두)과 상태가 testing인 가설만 나온다. supported·refuted·abandoned 가설과 resolved unknown은 보고서 어디에도 나오지 않는다. 둘 다 없으면 `_None outstanding._`. unknown 줄: `- <question> _(severity <Debug 이름>, <Debug 이름>)_`(예: `severity Medium, Open`), 그 아래 probes 앞 3개를 `  - would settle it: <probe>`. 이어서 가설 줄 `- (hypothesis, still testing) <claim>`. | 코드 확인 |
| R-07 | How this was done | `- **Mode:** <모드 문구>`. 이 모드는 보고서를 만드는 지금의 세션 모드이고, 각 증거의 `environment.clean_room`을 보지 않는다. 엔진: 모든 레코드의 `environment.engine`을 정렬·중복 제거해 있으면 `- **Engines:** a, b`. 레코드 순서로 처음 만난 `language_id`가 있으면 `- **Deep processor pinned to:** \`<id>\``. 대상 내용을 담은 레코드가 하나라도 있으면 경고 한 줄. 한계: 모든 레코드의 `limitations[].message`를 정렬·중복 제거(code는 보지 않음)해 앞 30개를 쓰고, 넘으면 `  - … and <N> more limitation(s) omitted`. 엔진·한계·대상 내용 표시는 인용 여부와 상관없이 R-02의 모든 레코드에서 모은다. | 코드 확인 |
| R-08 | Evidence ledger 부록 | R-02의 레코드 순서대로 `` - `<id>` **<operation>** — <summary 또는 operation> (<사람용 confidence>) ``. include_evidence가 false면 절 전체가 없다. finding의 인용은 부록과 상관없이 항상 나온다. | 코드 확인 |
| R-09 | Markdown escape | statement·question·summary·handoff 등 사용자·도구 문자열을 escape하지 않고 그대로 넣는다. | 코드 확인 |
| R-10 | HTML 형식 | 절 순서와 포함 규칙은 Markdown과 같고 다음이 다르다. 모든 문자열을 `& < > " '` 다섯 개 escape. `<!doctype html>`로 시작해 `</html>\n`으로 끝나고 CSS를 `<style>`에 넣는다(다크 모드 포함, 외부 자원 없음). finding은 `<article class="finding">`과 확실성 배지 `<사람용 이름> · <코드>`(observed `#1f8a4c`, derived `#c96f2d`, inferred `#8a7a66`). Open questions에 **probes를 쓰지 않는다**. 대상 내용 경고는 How 목록 뒤 별도 문단. 한계는 `<h3>Limitations</h3>` 목록(같은 30개 상한과 생략 문구). handoff는 escape한 뒤 줄바꿈을 `<br>\n`으로 바꾼다. 부록은 Id·Operation·Summary·Confidence 표. 정확한 문자열은 C-01. | 코드 확인 |
| R-11 | 숫자 칸 | `findings`는 조사 상태의 finding 수, `evidence_records`는 R-02 레코드 수, `bytes`는 보고서 텍스트의 UTF-8 바이트 수. | 코드 확인 |
| R-12 | path가 있음 | 보고서를 먼저 만든 뒤 path를 검사한다. 절대 경로가 아니면 `bad_input` "<path> is not an absolute path"(remediation "Pass a full path, e.g. /Users/me/report.md."). 확장자는 검사하지 않는다. 같은 파일이 있어도 묻지 않고 원자적으로 덮어쓴다. 쓰기 실패는 io 오류. | 코드 확인 |
| R-13 | 부작용 선언 | `core_report_write`는 path가 없어도 정적으로 파일 쓰기 효과를 선언한다(코드 주석이 "static worst-case"라고 밝힘). 보고서는 원장에 기록되지 않고 조사 상태도 바꾸지 않는다. 두 도구 모두 Core 툴셋, Clean room에서도 허용. | 코드 확인 |
| R-14 | `core_report_save` | path가 절대 경로이고 확장자가 대소문자 무시로 `md`·`html`·`htm`·`txt` 중 하나가 아니면 `bad_input` "path must be absolute and end in .md, .html, .htm or .txt". text가 64 MiB(67,108,864바이트)를 넘으면 `bad_input` "That report is too big to save (64 MB at most)." 통과하면 원자적으로 덮어쓰고 `{saved: <경로 표시 문자열>, bytes}`. 내용은 검사하지 않으며 finding·증거와 아무 관계가 없다. | 코드 확인 |

- 불변식: 보고서의 모든 finding은 증거 id 1개 이상을 보여 준다(선행 investigation-memory R-11·R-12가 보장). 인용 id가 원장과 프로젝트 저장소 어디에도 없으면 "not in this session's ledger"로 표시될 뿐 보고서 생성이 실패하지 않는다.
- 미결정: 없음.
- 확인 한계: 정적 읽기만 했다. HTML이 브라우저에서 어떻게 보이는지는 확인하지 않았다. Markdown이 escape 없이 들어가 생기는 렌더 깨짐(R-09)은 Markdown 렌더러에 따라 다르다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/engine/src/tools/report_tools.rs:162-557` `ReportData`·`is_resolved`·`locations_line`·`render_markdown`·`confidence_code`·`esc`·`conf_color`·`conf_badge`·`render_html`·`evidence_list_html`·`CSS`, 상수 `MAX_REPORTED_LIMITATIONS` `:20-21` | 두 형식의 정확한 문자열과 집계 함수 | R-03~R-10 |
| C-02 | `crates/engine/src/clean_room.rs:154-156` `mode_words` | 모드 문구 | R-07 |
| C-03 | `report_tools.rs:100-160` `core_report_write` | 수집 순서와 출력 칸 | R-02, R-11, R-12 |
| C-04 | `report_tools.rs:51-72` `SaveParams`·`core_report_save` | 확장자·크기 검사 | R-14 |

### 1.6 수락 사례
출처: 사례별 표기. "기본 시드"는 원본 테스트의 `seeded_engine`(`report_tools.rs:570-603`): 증거 2개(ev1 derived·위치 `address=0x401000 (entry)`, ev2 observed·대상 내용 표시), brief(question·purpose·targets·done_when), ev1을 인용한 derived finding, testing 가설 1개, probe 1개가 있는 medium unknown 1개.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-05, R-06, R-07 | 기본 시드, `{}` (원본 테스트) | format markdown. 절 제목 5개, 질문, finding 문장, ev1 id, "Worked it out", "Deep (the original's code and files could be read)"(테스트 세션은 Deep), "Where is the main loop?" 포함 |
| T-02 | R-10 | 기본 시드, `{format: "html"}` (원본 테스트) | `<!doctype html>`로 시작, `</html>`로 끝, `<style>`과 `#c96f2d` 포함, finding 문장 포함, 대상 내용 경고 포함 |
| T-03 | R-12 | 프로젝트에서 brief만 쓰고 `{path: <절대경로>/report.md}`, 이어서 `{path: "rel.md"}` (원본 테스트) | 파일이 생기고 `# Investigation report` 포함. 상대 경로는 오류 |
| T-04 | R-02, R-05 | 프로젝트에 증거 기록·그 증거를 인용한 finding 기록 후, 새 세션에서 프로젝트만 열고(대상 없음) 보고서 (원본 테스트) | 증거 id 포함, "not in this session's ledger" 없음, "sample.exe (native)"가 대상으로 나오고 "No targets recorded" 없음 |
| T-05 | R-08 | 기본 시드, include_evidence true / false (원본 테스트) | `## Evidence ledger`가 있음 / 없음 |
| T-06 | R-07, R-10 | 기본 시드에 서로 다른 한계를 가진 레코드 31개 추가, 두 형식 (원본 테스트) | 두 형식 모두 "… and 1 more limitation(s) omitted", "limitation 29" 있음, "limitation 30" 없음 |
| T-07 | R-03 | 기본 시드에 plan 단계 하나 추가 (구현에서 도출) | 보고서에 plan 단계 제목이 없음 |
| T-08 | R-06 | 기본 시드의 가설을 supported로 바꾸고 unknown을 blocked로 바꿈 (구현에서 도출) | Open questions에 unknown은 `severity Medium, Blocked`로 남고 가설 줄은 없음 |
| T-09 | R-05 | `state.json`의 finding이 원장·프로젝트 어디에도 없는 id를 인용(파일을 손으로 고침) (구현에서 도출) | 그 id 줄이 `_(not in this session's ledger)_`, 보고서 생성 성공 |
| T-10 | R-07 | Clean room 세션에서 Deep 모드로 만든 증거(`environment.clean_room: false`)만 인용 (구현에서 도출) | Mode 줄은 "Clean room (nothing inside the original was read)" |
| T-11 | R-14 | `core_report_save {path: "/tmp/r.PDF", text: "x"}` / `{path: "/tmp/r.MD", text: "x"}` (구현에서 도출) | 첫째 `bad_input`, 둘째 저장 성공 `bytes: 1` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `report_tools.rs:74-98` `ReportFormat`·`ReportParams`·`default_true` | |
| R-02 | C-03 `:101-123` | |
| R-03 | C-01 `render_markdown` `:233-356` | 문서 차이: 머리 주석 `:3-4`과 도구 설명 `:39`은 보고서가 plan을 포함한다고 말하지만 렌더 함수 두 개 모두 `inv.plan`을 읽지 않는다 |
| R-04 | `:250-265`, HTML `:420-437` | |
| R-05 | `:267-293`, `locations_line` `:214-228` | |
| R-06 | `:295-312`, `is_resolved` `:206-208` | |
| R-07 | `:314-337`, `ReportData` `:171-204`, C-02 | 머리 주석 `:6`은 "how it was done (Clean room vs Deep, engines, limitations)"라고만 한다. 모드가 현재 세션 값이라는 점은 `ctx.session.clean_room()` `:123`에서 확인. 30개 상한의 생략 문구는 `docs/pitfalls.md` "A report showed a prefix of its limitations as the whole list"의 수정 결과 |
| R-08 | `:345-353` | |
| R-09 | `render_markdown` 전체 | escape 함수 호출 없음 |
| R-10 | C-01 `render_html`·`esc`·`conf_*`·`evidence_list_html`·`CSS` `:369-557` | Open questions의 HTML 분기 `:451-465`에 probes 출력 없음 |
| R-11, R-12 | C-03 `:130-159` | |
| R-13 | `:23-49` `specs`, `crates/engine/src/clean_room.rs:39-40` | |
| R-14 | C-04 | |
| T-01~T-06 | `report_tools.rs:605-717` `markdown_report_has_sections_and_cites_evidence`·`html_report_is_well_formed_and_self_contained`·`report_writes_a_file_when_given_a_path`·`report_cites_project_evidence_in_a_new_session`·`include_evidence_toggles_the_appendix`·`reports_disclose_limitations_omitted_after_thirty` | 원본 테스트 열람 |

## 적용 메모

overview 2절 "우리 절차와 맞대어 볼 후보" 표에는 행 4를 근거로 한 행이 없다. 아래는 이 스펙에서 나온 새 후보다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-02, R-05, R-06 | **새 후보: 통합 검토(4장 5번)에서 overview "남은 질문" 절을 스펙에서 모아 만든다.** 원본 보고서의 원천은 채팅 글이 아니라 구조화된 기록(finding·unknown·가설)이다. 우리 쪽으로 옮기면 각 스펙의 1.4 "미결정"과 "확인 한계", 적용 메모의 후보를 overview 4절·`next.md`로 옮겨 적을 때 손으로 요약하지 말고 스펙의 항목을 그대로 링크로 모은다. | 지금 overview 4절은 "아직 없음"이고, 스펙마다 미결정·한계가 흩어져 있다. 보고서처럼 한곳에서 "열린 것"을 볼 수 있어야 다음 세션이 시작점을 고를 수 있다. | 4장 6번 "연결하고 보고한다"에 "스펙들의 미결정·확인 한계를 overview 4절에 링크로 모은다" 한 줄 |
| R-03, R-07 | 참고(따르지 않을 점): 원본 보고서는 plan을 빼고, 모드를 증거가 아니라 보고서를 만드는 시점의 세션에서 가져오며, 한계를 인용 여부와 상관없이 원장 전체에서 모은다. 그래서 보고서의 "어떻게 조사했나"가 결론의 근거와 어긋날 수 있다(T-10). 우리가 모아 쓰는 요약도 **결론이 인용한 근거에서만** 조건(SHA·작성 방식)을 가져와야 한다. | 원본의 어긋남을 반면 사례로 둔다. 우리 쪽에 대응하는 위험은 overview 1절의 작성 방식("코드만 읽고 쓴다")과 개별 스펙의 확인 한계가 다를 때다. | 없음(규칙 문장 후보: "요약 문서의 조건은 각 스펙 frontmatter와 확인 한계에서 가져온다") |
| R-07 | **작은 후보:** 목록을 상한에서 자르면 자른 개수를 함께 적는다. | 원본은 한계 목록을 30개에서 자르면서 생략 수를 말하지 않아 고친 이력이 있다(`docs/pitfalls.md`). 우리 문서도 "대조한 범위"나 파일 목록을 줄일 때 같은 문제가 생긴다. | 8장 문서화 규칙에 한 줄 |
