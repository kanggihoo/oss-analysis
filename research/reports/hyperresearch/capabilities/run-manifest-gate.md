---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/core/runs.py
  - src/hyperresearch/cli/run_cmd.py
  - src/hyperresearch/core/codex.py
  - src/hyperresearch/core/vault.py
  - src/hyperresearch/core/hooks.py
  - src/hyperresearch/core/profiles.py
  - src/hyperresearch/core/levers.py
  - src/hyperresearch/core/patterns.py
  - src/hyperresearch/core/citecheck.py
  - src/hyperresearch/core/escalation.py
  - src/hyperresearch/cli/lint.py
  - src/hyperresearch/cli/archive.py
  - src/hyperresearch/cli/vault_tag.py
  - src/hyperresearch/skills/hyperresearch.md
  - src/hyperresearch/skills/hyperresearch-1-5-chapter-partition.md
  - src/hyperresearch/skills/hyperresearch-14-5-cite-check.md
  - README.md
  - CHANGELOG.md
depends: []
status: ready
---

# 런 매니페스트·재개·예산·ship gate

> 런 태그 하나마다 작업 공간 `research/runs/<tag>/`와 매니페스트(`run.json`·`events.jsonl`)를 만들고, 단계 상태·지출·개수 상한을 기록하며, 중단된 런의 다음 단계를 계산하고, `run finish`의 검증 배터리(`verify_run`)가 통과할 때만 런을 `done`으로 만들고 실패는 `blocked`로 두며, Codex Stop 훅이 진행 중인 런의 세션 종료를 막는다. 이 스펙은 공유 계약 S1(런 작업 공간과 산출물 이름)의 소유자다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 진입 스킬이 `vault-tag`로 태그를 만든 뒤 `run init <tag> --profile <p> [--budget] [--max-sources] [--max-notes]`를 부른다. `run.json`(상태 `running`, `profile_steps` 고정)과 `temp/`가 생긴다. 같은 태그로 다시 부르면 기존 매니페스트를 그대로 돌려준다.
2. 파이프라인이 도는 동안 호스트가 `run step <tag> <step> --status running|done|...`로 단계 전이를 남기고, `run event`로 임의 이벤트를, `run spend`로 지출을 더한다. `done` 전이마다 볼트 DB에서 이 태그의 노트 수·소스 URL 수를 다시 세어 `spend`에 덮어쓰고, 상한(`max_sources`·`max_notes`)을 넘으면 런이 `blocked`가 된다. `--budget`은 `run spend`가 `estimated_usd`를 올릴 때만 평가한다.
3. 컨텍스트가 압축되거나 세션이 끊기면 `run resume [<tag>]`가 `blocked/paused/failed` 런을 `running`으로 되돌리고(개수 차단은 기준선을 갱신하며 풀되 최대 3번), 단계 상태에서 다음 단계와 그 스킬 이름을 계산해 돌려준다. 계산은 step 1이 `prompt-decomposition.json`에 적은 `pipeline_tier`를 따른다.
4. Codex에서는 Stop 훅(`run stop-gate`)이 "최신 런이 `running`이고, 최근 6시간 안에 갱신됐고, 남은 단계가 있으면" 세션 종료를 막고 다음 단계 파일을 읽으라고 지시한다. `stop_hook_active`·환경변수·읽기 실패는 모두 통과(막지 않음)다.
5. step 16이 끝나면 진입 스킬이 `sources retractions --tag <tag>`로 철회 정보를 갱신하고 `run finish <tag>`를 부른다. `verify_run`이 검사 목록을 만들어 모두 ok여야 `passed`다.
6. 통과하면 `status=done`, 실패하면 `status=blocked, blocked_on="verify"`이고 종료 코드는 1이다. `verify` 블록(`passed/at/failed_checks`)과 `finish` 이벤트가 어느 쪽이든 남는다. 실패 시 고치는 대상은 보고서이고 검사 해석이 아니다. 진입 스킬은 최대 3라운드 뒤에는 `blocked` 그대로 두고 사용자에게 알리라고 지시한다.

### 1.2 범위·통합 지점 [필수]
- 제공: 런 작업 공간·매니페스트·이벤트 로그, 단계·장(chapter) 상태 기록, 지출·개수·예산 상한, 재개 위치 계산, 구조 검증 배터리와 종료 게이트, 텔레메트리 요약(`run report`), Codex Stop 훅 판정. 산출물 파일 이름 표(S1)를 1.3에 둔다.
- 제외(경계만): 프로필 값과 렌더링·레버(행 2), 서브에이전트 프롬프트(행 3), 각 산출물의 내용 필드(행 4~8), `quote-integrity`·`retracted-citations`·cite-check 쌍 추출의 판정 알고리즘(행 10), 노트·`tags`·`sources` 스키마(행 15), 에스컬레이션 큐(행 18), Stop 훅 설치(행 1).
- 외부 의존·선행 계약:
  - 볼트(`Vault`): 루트 경로, `research_dir`(기본 `research`), `config_path`, SQLite 연결(`vault.db`). 볼트가 없으면 모든 `run *` 명령은 `NO_VAULT`로 실패한다.
  - 프로필(행 2, `profiles-levers.md`(범위 밖, 스펙 없음)): 입력 이름 → 정규화된 프로필. 이 스펙이 읽는 필드는 `steps`(오름차순 정수 1..16), `word_targets`(형식→(low,high)), `char_targets_no_word_boundary`, `chars_per_word_no_word_boundary`, `citation_density_min`뿐이다. 이름이 알 수 없으면 `ProfileError`(`RunError`·`VaultError`가 아니므로 `run init`·`run verify`·`run finish`의 오류 처리기가 잡지 않는다). 내장 값은 1.3 "프로필 경계 값".
  - 검증 배터리(행 10, [verification-battery](verification-battery.md)): `quote-integrity`와 `retracted-citations` 두 규칙 함수. 입력은 (vault, 연결, 보고서 경로, 보고서 본문)이고 정상 결과는 이슈 dict 목록(각 `severity`, `message`)이다. 이 스펙은 `severity=="error"`인 것만 센다. 실행 중 예외가 나면 `content-lints` 검사가 실패로 기록된다.
  - 레버(행 2): `levers render <tag>`가 `shims/{research,drafting,critics,polish}.md`를 쓰고 `run.json`의 `levers`와 `levers` 이벤트를 남긴다. 이 스펙은 네 역할 이름과 `levers` 키 존재만 쓴다.
  - 에스컬레이션(행 18, `escalation-lane.md`(범위 밖, 스펙 없음)): `run status`가 `queue_stats(db, vault_tag)`(상태별 건수 dict)를 `escalations`에 붙인다. 실패하면 `null`.
  - 볼트 저장소(행 15, [vault-store](vault-store.md)): 개수 세기는 `notes`·`tags(note_id, tag)`·`sources(url, note_id)` 테이블을 읽는다.
  - 시계: 모든 시각은 UTC `isoformat()`(`+00:00` 포함). 테스트는 `stop_gate_decision`의 `now`만 주입할 수 있다.
- 소유 상태·부작용: `research/runs/<tag>/`(디렉터리, `temp/`, `run.json`, `events.jsonl`, `query.md`는 `--query-file`이 있을 때만), `run.json`의 읽기-수정-쓰기. 잠금은 없다(`확인 한계`).

### 1.3 인터페이스와 데이터 의미 [필수]

타입은 중립 표현이다. "step id"는 문자열이다(`"1"`, `"1.5"`, `"14.5"`, 자유 문자열 허용, 형식 검증 없음).

**A. 이름과 경로**

| 항목 | 값·규칙 |
|---|---|
| 런 태그 정규식 | `^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$` 전체 일치. 위반이면 `InvalidRunTagError`(`VaultError` 하위)이고 모든 `run *`가 `Error: invalid run tag ...`로 종료 코드 1이다. `vault-tag`가 만드는 `<slug>-<6hex>`는 이 정규식을 통과한다. |
| 런 디렉터리 | `<볼트 루트>/<research_dir>/runs/<tag>/`. `research_dir` 기본값은 `research`. |
| 최종 보고서 | `<볼트 루트>/research/notes/final_report_<tag>.md`. `verify_run`은 `research_dir` 설정과 무관하게 `research`를 고정으로 쓴다. UTF-8(BOM 허용)로 읽는다. |
| `archive-*` | `runs/` 아래 `run.json`이 없는 디렉터리(`archive-run`이 만든 보관본)는 `list_runs`에서 건너뛴다. |
| 태그 생략 | `status/resume/verify/finish/reconcile/report`는 태그를 생략하면 `started_at`이 가장 최신인 런을 쓴다. 런이 없으면 `NO_RUNS`로 종료 코드 1. `step/spend/event/block/abort/init`은 태그가 필수다. |
| `--json` 출력 | `{ok, data, error, error_code, count, vault, timestamp}` 봉투(None 필드 생략). 오류 코드: `RUN_ERROR`, `NO_VAULT`, `NO_RUNS`, `BAD_JSON`(`run event --data`). 오류는 종료 코드 1. |

**B. 런 작업 공간 산출물 이름 (S1)** — 경로는 모두 `research/runs/<tag>/` 기준. "코드가 보는가" 칸이 `-`인 파일은 스킬(프롬프트)끼리만 약속한 이름이다.

| 파일 | 쓰는 쪽(단계) | 코드가 보는가 | 비고 |
|---|---|---|---|
| `run.json` | CLI `run *`, `levers render` | 매니페스트 본체 | 아래 C |
| `events.jsonl` | CLI(`record_event`) | `run report`가 `type` 집계 | 한 줄 = JSON 한 객체, 추가만 한다 |
| `query.md` | `run init --query-file` 원문 그대로, 또는 진입 스킬 부트스트랩 3이 프론트매터(`vault_tag`, `created`, `source: prompt.txt \| user-prompt`) + 원문으로 직접 | lint의 `_query_files` | 모든 단계·서브에이전트가 경로로 읽는다 |
| `scaffold.md` | 진입 스킬 부트스트랩 5, step 1이 "Tier rationale"을 덧붙임 | lint(존재 여부) | 최종 보고서에 새면 안 됨(`no-scaffold-leak`) |
| `prompt-decomposition.json` | step 1 | `pipeline_tier`·`response_format`·`required_section_headings`·`levers`(이 스펙), `entities`·`required_formats`·`citation_style`(lint) | 필드 의미는 행 4 |
| `shims/{research,drafting,critics,polish}.md` | step 1의 `levers render` | `levers`가 선언됐으면 4개 모두 있어야 함(`levers-rendered`) | 역할 이름은 `ROLES` 튜플 |
| `temp/` | `run init`이 생성 | - | 스크래치 전체. 그 안 파일은 아래 |
| `temp/coverage-matrix.md` | step 1 | - | |
| `temp/search-plan.md`, `temp/scored-urls.md`, `temp/coverage-gaps.md`, `temp/redundancy-audit.md`, `temp/source-analysis-<source_note_id>.md`, `temp/claims-<note-id>.json` | step 2(claims는 fetcher) | - | claims는 행 17이 적재 |
| `temp/contradiction-graph.json`, `temp/consensus-claims.json` | step 3 | - | |
| `loci-<analyst_id>.json`, `loci.json` | step 4 | lint(`loci.json` 존재로 하이퍼리서치 런 판정) | |
| `comparisons.md` | step 6 | lint | |
| `temp/source-tensions.json` | step 7 | - | |
| `corpus-critic-gaps.json`, `temp/corpus-critic-gaps-raw.json`, `temp/period-pinned-gaps.json`, `temp/corpus-critic-results.md` | step 8 | - | |
| `temp/evidence-digest.md` | step 9 | - | |
| `temp/draft-{a,b,c}.md`, `temp/draft-angles.md`, `temp/draft-<x>-source-list.md` | step 10 | - | light는 `final_report_<tag>.md`를 직접 씀 |
| `temp/synthesis-{plan,outline,pass1,conflicts}.md` | step 11 | - | |
| `critic-findings-{dialectic,depth,width,instruction}.json` | step 12 | 티어가 12·14를 포함하면 4개 모두 필수 | |
| `temp/post-critic-fetch-log.md` | step 13 | - | |
| `patch-log.json`, `skip-patcher.txt`, `orchestrator-restructure-log.md` | step 14 | `patch-log.json` 필수(12·14 포함 티어) | `skip-patcher.txt`가 있으면 step 14를 건너뛰는 경로 |
| `cite-check-pairs.json` | `citecheck extract <tag>`(행 10) | - | |
| `cite-check-findings.json`, `cite-check-findings-a/-b.json`, `cite-check-patch-log.json` | step 14.5 | `cite-check-resolved` | findings는 `[]` 또는 `{"findings":[...]}` |
| `polish-log.json`, `audit_findings.json` | step 15 | `polish-log.json`은 15 포함 티어에서 필수 | |
| `readability-recommendations.json`, `readability-decisions.json` | step 16 | - | |
| `chapter-plan.json`, `chapters/<id>/{temp/, loci.json, comparisons.md, draft.md}` | step 1.5와 장 루프(dissertation) | - | 장 id가 하위 디렉터리 이름 |
| `temp/orchestrator-notes.md`, `temp/interim-report-<locus>.md` | 오케스트레이터, 깊이 조사자 | - | |

런 디렉터리 밖: 최종 보고서 `research/notes/final_report_<tag>.md`, 볼트 노트(전역).

**C. `run.json` 필드**

| 필드 | 타입 | 의미 |
|---|---|---|
| `manifest_version` | int | 1 |
| `vault_tag` | string | 태그 |
| `profile` | string | `run init --profile` 값(기본 `full`). 정보용이며 길이·밀도 검사는 이 프로필을 쓴다 |
| `profile_steps` | list of string | 초기화 시점에 프로필 `steps`를 문자열로 바꾼 것(`["1",...,"16"]`). 이후 불변 |
| `status` | string | `running` `paused` `blocked` `done` `failed` `aborted` 중 하나 |
| `started_at`, `updated_at` | string | UTC ISO. `updated_at`은 저장·이벤트마다 갱신(하트비트) |
| `budget_usd` | float\|null | 상한. 검증 없음(0·음수 허용) |
| `max_sources`, `max_notes` | int\|null | 양수만(초기화에서 검증) |
| `counts_force_cleared` | int | 개수 차단을 푼 누적 횟수(상한 3) |
| `counts_clear_baselines` | map reason→int | 마지막으로 푼 시점의 개수. 개수가 이 값을 넘어야 다시 차단 |
| `blocked_on` | string\|null | `status=="blocked"`일 때 이유(`budget`, `max_sources`, `max_notes`, `verify`, `run block --on`의 임의 문자열). 아니면 null |
| `steps` | map step id→{status, started_at?, finished_at?, chapter?} | 아래 D |
| `chapters` | map 장 id→{status, title?} | 아래 D |
| `spend` | {estimated_usd float, sources_fetched int, notes_written int, agents_spawned int} | `estimated_usd`·`agents_spawned`는 `run spend`로만 움직이고, 나머지 둘은 DB 재계산이 덮어쓴다 |
| `verify` | {passed, at, failed_checks[]}? | `run finish`가 쓴 마지막 판정. `run resume`은 지우지 않는다 |
| `levers` | {register, inference_depth, domain_notes}? | `levers render`가 기록(행 2) |

**D. 상태 값**

| 대상 | 값 | 의미·전이 |
|---|---|---|
| 런 `status` | `running` | `run init`, `run resume`, 개수 차단 해제 |
| | `blocked` | `add_spend`(예산, `blocked_on=budget`), 개수 상한(`max_sources`/`max_notes`), `run block --on <x>`, `run finish` 실패(`verify`) |
| | `done` | `run finish` 통과만(유일한 경로) |
| | `aborted` | `run abort`. 산출물은 디스크에 남는다 |
| | `paused`, `failed` | 설정하는 CLI 명령이 없다. `set_status`와 `run resume`만 인식 |
| 단계 `status` | `pending` `running` `done` `skipped` `failed` | `run step -s`가 받는 값. 첫 `running`에서 `started_at`(한 번만), `done/skipped/failed`에서 `finished_at`(매번 갱신) |
| 장 `status` | `planned`(`chapter-plan` 이벤트), `step-<step>-<status>`(`run step --chapter` 마다 덮어씀) | 장은 `status ∈ {"done","step-10-done"}`일 때만 완료 |

**E. 이벤트 (`events.jsonl`)** — 모든 줄은 `{"at": <UTC ISO>, "type": ..., ...}`.

| `type` | 쓰는 곳 | 추가 필드 |
|---|---|---|
| `step` | `run step` | `step`, `status`, `chapter`(null 가능), `force` |
| `spend_reconcile` | 개수 재계산마다 | `sources_fetched`, `notes_written`, `agents_spawned`, `estimated_usd`, `max_sources`, `max_notes`, `blocked_on` |
| `counts_force_clear` | 개수 차단 해제 | `cleared`(누적 횟수) |
| `finish` | `run finish` | `passed`, `failed_checks` |
| `levers` | `levers render` | `register`, `inference_depth` |
| `chapter-plan` | 스킬이 `run event`로 | `chapter`, `title` (매니페스트 `chapters`에도 접힘) |
| 임의(`spawn`, `fetch-wave`, `escalation`, `note` 등 도움말 예시) | `run event --type X --data '<json object>'` | 그대로 저장 |

**F. CLI (`hyperresearch run ...`, 별칭 `hpr run ...`)**

| 명령 | 입력 | 효과·출력 |
|---|---|---|
| `init <tag> [--profile full] [--budget f] [--max-sources n] [--max-notes n] [--query-file p] [-j]` | | 있으면 기존 매니페스트 반환, 없으면 생성. `{run_dir, manifest}` |
| `status [<tag>] [-j]` | | 매니페스트 + `resume` + `possibly_stalled` + (`budget_usd`가 truthy면) `budget_remaining_usd` + `escalations` |
| `list [-j]` | | `{runs:[{vault_tag,status,profile,started_at}]}` 최신 시작 순 |
| `resume [<tag>] [-j]` | | 상태 복구 후 `{vault_tag, run_dir, profile, next_step, done_steps, remaining_steps, chapters_pending, skill_to_invoke, codex_step_file}` |
| `step <tag> <step> -s <status> [--chapter c] [--force] [-j]` | | 단계 전이 기록. `{steps}` 출력 |
| `spend <tag> [--usd f] [--sources n] [--notes n] [--agents n] [-j]` | 기본 0 | 가산(음수 허용). `{spend,status,blocked_on}` |
| `reconcile [<tag>] [-j]` | | 개수 재계산. `{vault_tag,spend,status,blocked_on}` |
| `event <tag> --type T [--data json] [-j]` | | 이벤트 추가. `--data`는 JSON 객체이고 `type` 키를 덮어쓸 수 있다. JSON이 아니면 `BAD_JSON` |
| `block <tag> --on X [-j]` | | `status=blocked, blocked_on=X` |
| `abort <tag> [-j]` | | `status=aborted` |
| `report [<tag>] [--all] [-j]` | | 단계별 소요 분·지출·이벤트 집계 |
| `verify [<tag>] [-j]` | | `verify_run` 결과 출력. 실패면 종료 코드 1. 매니페스트는 바꾸지 않음 |
| `finish [<tag>] [-j]` | | `finish_run`. 통과 시 `SHIPPED`, 실패 시 종료 코드 1 |
| `stop-gate`(숨김) | stdin JSON | Codex Stop 훅. 항상 종료 코드 0 |

**G. `verify_run` 검사 목록** — 반환 `{vault_tag, passed, checks:[{name, ok, detail}]}`. `passed`는 모든 `ok`의 AND. 검사 이름과 추가 조건은 아래 표 순서대로 목록에 쌓인다.

| 검사 이름 | 만들어지는 조건 | 통과 조건 | 실패 시 결과(detail) |
|---|---|---|---|
| `report-exists` | 항상 | 보고서 파일 존재 | `passed=false`. 이후 "보고서 있음" 블록의 검사는 모두 생략됨 |
| `decomposition-readable` | 보고서 있음, `prompt-decomposition.json` 있음, JSON 파싱 실패일 때만(성공 시 항목 없음) | (항상 실패 항목) | `"prompt-decomposition.json is not valid JSON"`. 이 경우 `response_format`·`required_section_headings`·`levers`는 기본값(없음/빈/거짓)으로 진행 |
| `levers-rendered` | 보고서 있음, 분해 JSON의 `levers`가 truthy | `shims/<role>.md` 4개 모두 존재 | `missing shims: [...] (run \`hpr levers render <tag>\`)` |
| `length-in-range` | 보고서 있음, `response_format`이 매니페스트 프로필의 `word_targets` 키 | 공백 구분 단어 수 `wc`가 `low*0.8 <= wc <= high*1.2`. 보고서가 "단어 경계 없음"(공백 토큰 평균 길이 ≥ 15.0)이면 글자 수로 `char_targets_no_word_boundary[형식]`(없으면 `int(word low/high × chars_per_word)`)에 같은 ±20% | `"<n> words vs target <low>-<high> (<fmt>; ±20% tolerance)"` 또는 글자 기준 문구 |
| `required-headings` | 보고서 있음 | `required_section_headings`의 모든 문자열이 보고서에 **부분 문자열**로 존재(빈 목록이면 통과) | `missing: [...]` |
| `citation-density` | 보고서 있음 | 인용 수 × 1000 / max(1, 유효 단어 수) ≥ `citation_density_min` | `"<d:.2f> citations/1000 words (floor 9.0)"` |
| `no-scaffold-leak` | 보고서 있음 | `"## User Prompt (VERBATIM"`가 보고서에 없음 | `scaffold gospel header must not ship` |
| `quote-integrity` | 보고서 있음 | 행 10 규칙의 `error` 이슈 0건 | `"<n> error(s) — first: <message[:160]>"` |
| `retracted-citations` | 위와 같음(같은 try 블록) | 동 | 동 |
| `content-lints` | 위 두 규칙 중 하나가 예외를 던지면 | (항상 실패 항목) | `"content lint rules failed to run: <exc>"`(이미 쌓인 항목은 남고 나머지 규칙은 건너뜀) |
| `artifact:critic-findings-{dialectic,depth,width,instruction}.json`, `artifact:patch-log.json` | 필수 단계 집합에 `"12"`와 `"14"`가 둘 다 있을 때 5개 | 파일 존재 | detail = 파일 경로 |
| `artifact:polish-log.json` | 필수 단계 집합에 `"15"` | 파일 존재 | detail = 파일 경로 |
| `cite-check-resolved` | 매니페스트 `steps["14.5"].status == "done"`일 때만 | `cite-check-findings.json` 존재, JSON 파싱됨(객체면 `["findings"]`, 없으면 `[]`), `severity=="critical"` 항목이 있으면 `cite-check-patch-log.json`도 존재 | 파일 없음 → 경로, JSON 오류 → `"cite-check-findings.json is not valid JSON"`, 치명 항목 → `"<n> critical finding(s); patch log MISSING"` |

"필수 단계 집합" = 분해 JSON의 `pipeline_tier`가 있고 매니페스트 `profile`과 다르면 그 티어 이름을 프로필로 해석한 `steps`, 아니면(티어 없음·같음·해석 불가) 매니페스트 `profile_steps`. 인용 수 = `[n]`·`[n, m, ...]`(1~3자리 숫자, 쉼표 구분) 한 괄호 안 번호 수의 합 + `[[target]]`·`[[target|alias]]` 일치 수(뒤에 `(`가 붙는 `[[x]](url)`은 제외). 유효 단어 수 = 단어 경계가 있으면 공백 분리 토큰 수, 없으면 글자 수 / `chars_per_word_no_word_boundary`(기본 3.0).

**H. 프로필 경계 값 (행 2가 소유, 이 스펙의 입력)** — 사용자 `config.toml`의 `[profile.<name>]`이 덮어쓸 수 있다.

| 프로필 | `steps` | `word_targets` | `citation_density_min` |
|---|---|---|---|
| `light` | 1,2,10,15,16 | full과 같음 | 9.0 |
| `full` | 1..16 | short 500–2000, structured 2000–5000, argumentative 5000–10000 | 9.0 |
| `premier` | 1..16 | short 500–2000, structured 3000–8000, argumentative 8000–16000 | 9.0 |
| `dissertation` | 1..16 | full + `dissertation` 25000–80000 | 9.0 |

글자 기준(`char_targets_no_word_boundary`)은 각 단어 목표 × 3(full: short 1500–6000, structured 6000–15000, argumentative 15000–30000, premier structured 9000–24000, argumentative 24000–48000, dissertation 75000–240000).

**I. 단계 id ↔ 스킬 이름**: 단계 id는 `hyperresearch-` 접두 뒤 선행 숫자 세그먼트를 `.`로 이은 값(`hyperresearch-14-5-cite-check` → `14.5`)이고, `resume`의 `skill_to_invoke`는 설치기 로스터에서 찾은 슬러그(없으면 null)다. Codex 단계 파일은 `.hyperresearch/codex/steps/<slug>.md`.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 태그가 정규식을 어김(경로 구분자·`..`·절대 경로·앞 문자가 `.`/`-`·101자 이상) | `run_dir` 접근 시 `InvalidRunTagError`. 모든 `run *`는 메시지를 내고 종료 코드 1, 디렉터리를 만들지 않는다 | 코드 확인 |
| R-02 | `run init`, `max_sources`/`max_notes`가 0 이하 | `RunError`(종료 1). 디렉터리·매니페스트를 만들지 않는다. `budget`은 검증하지 않는다 | 코드 확인 |
| R-03 | `run init`, `run.json`이 이미 있음 | 기존 매니페스트를 그대로 반환하고 옵션(프로필·예산·상한·query)은 무시한다. 파일은 바뀌지 않는다 | 코드 확인 |
| R-04 | `run init`, 새 런 | `runs/<tag>/`와 `temp/`를 `mkdir -p`. `--query-file`이 있으면 UTF-8(BOM 제거)로 읽어 `query.md`에 그대로 기록(없으면 파일 없음). 매니페스트는 1.3 C의 초기값(`status=running`, `steps={}`, `chapters={}`, `spend` 모두 0, `counts_force_cleared=0`, `blocked_on=null`)이다. 프로필이 해석 불가이면 `ProfileError`가 그대로 전파된다 | 코드 확인 |
| R-05 | 매니페스트 저장 | 항상 `updated_at`을 현재 시각으로 갱신하고, 임시 파일에 `indent=2` JSON + 개행을 쓴 뒤 교체(rename)한다. 읽기 시 파일이 없으면 `RunError("no run '<tag>' ...")`, JSON이 깨졌으면 `RunError("corrupt manifest ...")` | 코드 확인 |
| R-06 | `record_event`(및 `run event`) | 런이 없으면 `RunError`. 있으면 `{"at": 지금, **event}`를 `events.jsonl`에 한 줄 추가하고 `updated_at`을 갱신한다. 이벤트 객체가 `at`·`type`을 가지면 덮어쓴다. `run event --data`는 객체여야 한다(객체가 아니면 처리되지 않은 예외) | 코드 확인 |
| R-07 | `chapter-plan` 이벤트 | `chapter`가 문자열 또는 int(bool 제외)이고 공백 제거 후 1~64자일 때만 `chapters[id]`를 만들고 `status`를 `planned`로 둔다(이미 있으면 유지, 진행을 되돌리지 않음). `title`이 비어 있지 않은 문자열이면 공백 제거 후 500자로 잘라 저장. 그 밖의 키·잘못된 id는 로그에만 남고 매니페스트는 안 바뀐다 | 코드 확인 |
| R-08 | `set_step`, 상태 값이 `pending|running|done|skipped|failed` 밖 | `RunError`. 상태·파일 불변 | 코드 확인 |
| R-09 | `set_step(done)`, 런이 `blocked`이고 `blocked_on`이 `max_sources`/`max_notes` | `--force` 없으면 `RunError`(불변). 있으면 `clear_count_block`(R-14)을 먼저 한 뒤 기록. `blocked_on`이 그 외(`budget`, `verify`, `human-challenges` 등)이면 `--force`로도 `RunError` | 코드 확인 |
| R-10 | `set_step` 성공 경로 | `steps[str(step)].status` 갱신, 첫 `running`에서 `started_at`, `done/skipped/failed`마다 `finished_at`. `--chapter c`가 있으면 `steps[step].chapter = c`와 `chapters[c].status = "step-<step>-<status>"`(장이 없으면 생성). 저장 후 `step` 이벤트를 쓴다. 상태가 `done`이면 이어서 R-12 재계산을 하고 그 결과 매니페스트를 반환한다. 단계 키는 장과 무관하게 하나라서 장마다 덮어쓴다 | 코드 확인 |
| R-11 | `done`이 아닌 전이, 또는 런이 `blocked`가 아닐 때 | 런 상태·`blocked_on` 검사를 하지 않고 기록한다(`aborted`·`done` 런에도 기록 가능). 개수 재계산은 하지 않는다 | 코드 확인 |
| R-12 | 개수 재계산(`done` 전이, `run reconcile`, `run finish`, 차단 해제 직전) | `notes_written` = `tags.tag == lower(strip(tag))`인 노트 수(타입 불문), `sources_fetched` = 그 노트에 연결된 `sources`의 서로 다른 URL 수를 `spend`에 **덮어쓴다**(mtime 미사용). DB 오류는 `RunError`(0으로 대체하지 않음). `estimated_usd`·`agents_spawned`는 건드리지 않는다. 그다음 상한을 적용(R-13)하고 저장한 뒤 `spend_reconcile` 이벤트를 쓴다 | 코드 확인 |
| R-13 | 개수 상한 적용 | 런이 `running`일 때만. `max_sources`, `max_notes` 순으로 보고, 첫 번째로 `ceiling != null`이고 `count >= ceiling`이며 (`baseline` 없음 또는 `count > baseline`)이면 `status=blocked`, `blocked_on=<이유>`, 그 이유의 baseline 항목을 삭제하고 나머지는 보지 않는다 | 코드 확인 |
| R-14 | `clear_count_block`(`run resume` 또는 `--force`) | 런이 `blocked`이고 이유가 개수 계열이 아니면 `RunError("... no count block to clear")`. `counts_force_cleared >= 3`이면 `RunError("... force-clear limit")`. 아니면 재계산으로 최신 개수를 얻고, `baselines[이유] = 그 개수`, `counts_force_cleared += 1`, `status=running`, `blocked_on=null`, 저장, `counts_force_clear` 이벤트. 이후 개수가 baseline을 넘기 전에는 다시 차단되지 않는다. 한도 3은 이유 구분 없는 누적이다 | 코드 확인 |
| R-15 | `add_spend`(`run spend`) | 네 카운터를 가산(`estimated_usd`는 4자리로 반올림, 음수 허용). `budget_usd != null`이고 `estimated_usd >= budget_usd`이고 `status=="running"`이면 `status=blocked`, `blocked_on="budget"`. 개수 상한은 평가하지 않는다. 예산 평가는 이 경로뿐이다(예산 0이면 첫 호출에서 차단) | 코드 확인 |
| R-16 | `run block --on X`, `run abort` | 상태를 `blocked`(`blocked_on=X`) 또는 `aborted`로 설정. 상태가 `blocked`가 아니면 `blocked_on`은 null로 지운다. 런이 없으면 `RunError`(종료 1) | 코드 확인 |
| R-17 | `run resume`, 상태별 | `blocked`+개수 이유 → R-14(한도 초과 시 오류 종료 1). 그 밖의 `paused/blocked/failed` → `running`, `blocked_on=null`. `running/done/aborted`는 상태 불변. 이어서 위치를 계산해 1.3 F의 필드를 출력한다. 텍스트 모드: `next_step`이 null이면 "all profile steps complete", 아니면 `resume at step <n>`과 `Skill(skill: "<slug>")` | 코드 확인 |
| R-18 | `resume_position(manifest, required)` | 대상 목록 L = `profile_steps` (`required`가 있으면 `required`에 속한 것만 원래 순서로 + `required`에만 있는 것을 `_step_sort_key` 오름차순으로 뒤에 덧붙임). `done_steps` = L 중 `steps[s].status ∈ {done, skipped}`, `remaining_steps` = 나머지(순서 유지), `next_step` = `remaining[0]` 또는 null(`failed`·`running`·`pending` 단계는 남은 것으로 센다). `chapters_pending` = `chapters`의 키 중 `status ∉ {"done","step-10-done"}`(dict가 아닌 항목 포함). 장 상태는 `next_step`에 영향이 없다 | 코드 확인 |
| R-19 | `run_resume_position`(`status`, `resume`, Stop 훅 공통) | `required`는 "필수 단계 집합"(1.3 G 아래 정의): 분해 JSON `pipeline_tier`가 있고 매니페스트 `profile`과 다르고 해석되는 프로필이면 그 `steps`, 아니면 `profile_steps`. 분해 JSON이 없거나 읽을 수 없거나 `pipeline_tier`가 비문자열이면 티어 없음으로 본다(예외 없음) | 코드 확인 |
| R-20 | `status_summary` | `possibly_stalled` = 런이 `running`이고 `now − updated_at > 30분`(`updated_at` 파싱 실패 시 true), `running`이 아니면 false. `budget_usd`가 truthy일 때만 `budget_remaining_usd = round(max(0, budget − estimated_usd), 4)`. CLI는 `escalations`를 붙이고 실패하면 null | 코드 확인 |
| R-21 | `list_runs`, `latest_run_tag` | `runs/` 하위 디렉터리 중 `run.json`이 있는 것을 읽어 `started_at` 내림차순. 파싱 실패 항목은 `{"vault_tag": 디렉터리명, "status": "corrupt-manifest"}`로 목록 끝에 온다. `latest_run_tag`는 첫 항목의 `vault_tag` | 코드 확인 |
| R-22 | `verify_run`, 구성 | 1.3 G 표대로 검사를 쌓고 `passed = all(ok)`. 매니페스트·디스크를 바꾸지 않는다(`run verify`와 동일). 보고서 본문 의존 검사 블록은 보고서가 있을 때만 실행된다. 단계 상태가 모두 `done`인지는 검사하지 않는다(`14.5`만 예외) | 코드 확인 |
| R-23 | `length-in-range` 계산 | 1.3 G. 프로필은 매니페스트 `profile`(티어가 아님)로 해석한 것. `response_format`이 없거나 `word_targets`에 없는 값이면 검사 항목이 만들어지지 않는다. 계산 대상은 프론트매터·참고문헌 포함 보고서 전체 | 코드 확인 |
| R-24 | `citation-density`, `required-headings`, `no-scaffold-leak` | 1.3 G 정의대로. `citation_style`은 읽지 않으므로 인용 표식이 없는 보고서(`none`)는 밀도 0으로 실패한다. 제목 일치는 줄 단위가 아닌 부분 문자열 | 코드 확인 |
| R-25 | 12·14·15 포함 여부에 따른 산출물 검사 | 필수 단계 집합에 `"12"`·`"14"`가 모두 있으면 critic 4개 + `patch-log.json`, `"15"`가 있으면 `polish-log.json`을 요구한다. 티어가 `light`로 선언되면 위 검사는 만들어지지 않는다 | 코드 확인 |
| R-26 | `cite-check-resolved` | 매니페스트에 `14.5=done`이 기록된 때만 만든다(기록이 없으면 검사 자체가 없다). 정상 조건과 실패 detail은 1.3 G | 코드 확인 |
| R-27 | `finish_run` | `verify_run` 실행 → 개수 재계산(상한 적용 포함) → `verify={passed, at, failed_checks[이름]}`를 매니페스트에 기록 → 통과면 `status=done, blocked_on=null`, 실패면 `status=blocked, blocked_on="verify"`(기존 `budget`·개수 차단·`aborted`도 이 판정이 덮어쓴다) → 저장 → `finish` 이벤트. 반환 `{manifest, verify}`. `done`에 이르는 유일한 경로다 | 코드 확인 |
| R-28 | `run verify`·`run finish` CLI | 실패(`passed=false`)면 종료 코드 1. 텍스트 모드는 검사마다 `ok/FAIL <name>: <detail>`을 출력하고 `PASSED`/`FAILED`, `SHIPPED — run status: done`/`BLOCKED ... Fix the report, then run finish again.`를 낸다. `RunError`·`VaultError`는 종료 1. `ProfileError`는 처리되지 않는다 | 코드 확인 |
| R-29 | `stop_gate_decision(vault, now)` | 런이 없으면 null. 최신 런(`list_runs()[0]`)의 `status != "running"`이면 null. `updated_at` 파싱 실패 → null, tz 없으면 UTC로 간주, `now − updated_at > 6시간`이면 null. `run_resume_position(...)["next_step"]`이 null이면 null. 아니면 `{"decision":"block","reason":"<tag> is at step <n> (<slug>). Continue the pipeline: read .hyperresearch/codex/steps/<slug>.md and follow it. Answering without finishing the pipeline is a failure."}`(슬러그를 모르면 `step <n>`) | 코드 확인 |
| R-30 | `run stop-gate` CLI | 환경변수 `HYPERRESEARCH_STOP_GATE`가 `0/false/no/off`(대소문자 무시)면 아무것도 출력하지 않는다. stdin JSON(없거나 깨지면 `{}`, 객체가 아니면 `{}`). `stop_hook_active`가 truthy면 출력 없음(무한 루프 방지). `cwd` 문자열이 있으면 거기서 볼트를 찾고, 볼트가 없으면 출력 없음. 판정이 있으면 JSON 한 줄을 stdout으로. 모든 예외를 삼키고 종료 코드 0 | 코드 확인 |
| R-31 | `run_report_data`(`run report`) | 프로필 단계(없던 id는 정렬해 뒤에 덧붙임)마다 `{step, status(기본 pending), minutes(started→finished, 소수 1자리, 없으면 null), chapter}`, `total_wall_minutes`(started→updated), `spend`, `budget_usd`, 이벤트 `type`별 건수(깨진 줄은 건너뜀, `type` 없으면 `unknown`). `--all`은 런별 보고서와 합계(`total_estimated_usd`·`total_sources`·`total_agents`) | 코드 확인 |
| R-32 | 단계 id → 스킬 슬러그 | 로스터 18개 이름에서 `hyperresearch-` 뒤 선행 숫자 세그먼트를 `.`로 이은 것이 키. 알 수 없는 id는 null | 코드 확인 |
| R-33 | 종료 게이트 절차(진입 스킬 프롬프트) | step 16 뒤: 6개 파일 존재 확인 루프(light는 critic·patch 로그 없음이 정상), `sources retractions --tag <tag>`, `run finish <tag> --json`. 실패 검사는 **보고서를 고쳐서** 해결하고(`length-in-range` 초과 → synthesizer 압축 1회 후 곧장 재검사, `quote-integrity` → 따옴표 제거 또는 원문으로 교정, `retracted-citations` → 철회 명시 또는 인용 삭제) 최대 3라운드, 그래도 실패면 `blocked`로 두고 보고. 개별 규칙을 따로 돌려 오탐으로 재해석하지 않는다. 호스트 준수는 코드로 강제되지 않는다 | 코드 확인(프롬프트 본문) |

- 불변식: `status=="done"`인 매니페스트는 마지막 `run finish`가 통과한 뒤에만 생긴다(`set_status`는 `done`을 받지만 이를 부르는 CLI 명령이 없다). `profile_steps`는 초기화 뒤 바뀌지 않는다. 이벤트 로그는 추가만 되고 읽는 쪽이 매니페스트 상태를 이벤트에서 복원하지 않는다(장 등록만 이벤트가 매니페스트에 접힌다).
- 미결정: 없음.
- 확인 한계: 코드는 실행하지 않았다. 동시 쓰기(서브에이전트가 병렬로 `run event`를 부르는 상황)는 읽기-수정-쓰기에 잠금이 없다는 것만 코드로 확인했고 실제 손실 여부는 실행해 보지 않았다(추론: 마지막 쓰기가 이긴다). `quote-integrity`·`retracted-citations` 내부, 프로필 해석, DB 스키마는 이 스펙 밖이다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/hyperresearch/core/vault.py:25-44` `RUN_TAG_RE`, `validate_run_tag`; `:104-116` `runs_dir`, `run_dir` | 태그 정규식과 경로 조립 | R-01 |
| C-02 | `src/hyperresearch/core/runs.py:30-82` 상수 | `RUN_STATUSES`, `STEP_STATUSES`, `CHAPTER_PLAN_EVENT`, `CHAPTER_LAST_STEP="10"`, `STALL_MINUTES=30`, 개수 차단 이유·한도 3·필드 매핑 | R-09, R-13, R-14, R-18, R-20 |
| C-03 | `runs.py:97-177` `init_run`, `load_manifest`, `_save` | 초기 매니페스트 필드 전체, 멱등성, 원자적 저장 | R-02~R-05 |
| C-04 | `runs.py:180-237` `record_event`, `_chapter_id_of`, `_fold_chapter_plan` | 이벤트 형식, 장 id·제목 제한 | R-06, R-07 |
| C-05 | `runs.py:240-298` `set_step` | 상태 검증, 차단 중 `done` 처리, 단계·장 기록, 이벤트, `done` 뒤 재계산 | R-08~R-11 |
| C-06 | `runs.py:301-324` `add_spend` | 카운터 가산, 예산 차단 | R-15 |
| C-07 | `runs.py:327-432` `_count_notes_and_sources`, `clear_count_block`, `_apply_count_ceilings`, `reconcile_spend_from_disk` | 개수 SQL, 기준선, 상한 판정, `spend_reconcile` 필드 | R-12~R-14 |
| C-08 | `runs.py:435-466` `set_status`, `list_runs`, `latest_run_tag` | 상태 설정과 목록 정렬 | R-16, R-21 |
| C-09 | `runs.py:469-525` `resume_position`, `_step_sort_key`, `run_resume_position` | 재개 위치 알고리즘 | R-18, R-19 |
| C-10 | `runs.py:528-548` `status_summary`; `:562-606` `run_report_data` | 정체 판정, 텔레메트리 | R-20, R-31 |
| C-11 | `runs.py:609-646` `_declared_tier`, `_required_step_ids` | 선언 티어가 필수 단계 집합을 결정 | R-19, R-25 |
| C-12 | `runs.py:33-54` `_lacks_word_boundaries`, `_effective_word_count` | 단어 경계 없음 판정(평균 토큰 길이 ≥ 15.0), 유효 단어 수 | R-23, R-24 |
| C-13 | `runs.py:649-844` `verify_run` | 검사 목록 전체와 순서, 길이 허용 오차 0.8~1.2, 인용 수 정규식, detail 문구 | R-22~R-26 |
| C-14 | `runs.py:847-879` `finish_run` | 판정 기록과 상태 전이 | R-27 |
| C-15 | `src/hyperresearch/cli/run_cmd.py:29-90` `_resolve_tag`, `run_init` | 태그 생략 규칙, 옵션·기본값 | R-03, R-04 |
| C-16 | `run_cmd.py:184-246` `run_resume`, `_codex_step_file` | 재개 시 상태 복구와 출력 필드 | R-17 |
| C-17 | `run_cmd.py:249-294` `run_stop_gate` | 훅 입력·환경변수·종료 정책 | R-30 |
| C-18 | `run_cmd.py:297-317` `run_abort`; `:320-470` `run_step`, `run_spend`, `run_reconcile`, `run_event`, `run_block` | 옵션·기본값·출력 | R-06, R-15, R-16 |
| C-19 | `run_cmd.py:541-617` `run_verify`, `run_finish` | 종료 코드·출력 | R-28 |
| C-20 | `src/hyperresearch/core/codex.py:347-398` `STOP_GATE_WINDOW`, `stop_gate_decision` | 훅 판정과 `reason` 문구 | R-29 |
| C-21 | `src/hyperresearch/core/hooks.py:4388-4437` `_HYPERRESEARCH_STEP_SKILLS`, `_step_id_of_skill`, `STEP_SKILL_BY_ID`, `step_skill_slug` | 단계 id↔슬러그 로스터 | R-32 |
| C-22 | `src/hyperresearch/core/profiles.py:234-242` `steps` 검증; `:253-298` `_FULL`; `:309-325` `_LIGHT`; `:327-374` `_PREMIER`; `:376-415` `_DISSERTATION` | 1.3 H의 내장 값 원본 | R-18, R-23 |
| C-23 | `src/hyperresearch/core/patterns.py:24` `WIKI_LINK_RE` | `[[target]]`/`[[target\|alias]]`(뒤에 `(` 아님) 인용 정규식 | R-24 |
| C-24 | `src/hyperresearch/core/levers.py:29` `ROLES`; `:290-330` `render_shims`(매니페스트 `levers` 기록) | 네 역할 이름과 `levers` 필드 | R-22 |
| C-25 | `src/hyperresearch/skills/hyperresearch.md:249-283` | 종료 게이트 절차 원문 | R-33 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 테스트는 열지 않았다. 시간·태그가 변하는 값은 조건으로 적는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 태그 `../x`, `a/b`, `-a`, `.a`, 빈 문자열, 101자 | 모두 `invalid run tag`, 종료 1, `runs/` 하위에 아무것도 생기지 않음. `a.b_c-d`, `A1`은 통과 |
| T-02 | R-02, R-04 | `run init t1 --max-sources 0` | `--max-sources must be a positive integer`, 종료 1, `runs/t1` 없음 |
| T-03 | R-03, R-04 | `run init t1 --profile full --budget 5` 후 `run init t1 --profile light` | 첫 호출: `status=running`, `profile_steps=["1",...,"16"]`, `budget_usd=5.0`, `temp/` 존재, `query.md` 없음. 두 번째: 같은 매니페스트(프로필 `full` 유지), 파일 불변 |
| T-04 | R-12, R-13 | `max_sources=3`, 이 태그의 노트에 연결된 서로 다른 소스 URL 3개, `run step t1 2 -s done` | 단계 2 `done` 기록 뒤 `spend.sources_fetched=3`, `status=blocked`, `blocked_on="max_sources"`. 이어서 `run step t1 3 -s done`은 오류(종료 1), 매니페스트 불변 |
| T-05 | R-09, R-14 | T-04 상태에서 `run step t1 3 -s done --force` | `counts_force_cleared=1`, `counts_clear_baselines.max_sources=3`, 단계 3 `done`, 재계산 후에도 `running`(3은 baseline 초과 아님). URL이 4개가 된 뒤 다음 `done`에서 다시 `blocked`, baseline 항목 삭제. 네 번째 해제 시도(`--force` 또는 `run resume`)는 `force-clear limit` 오류 |
| T-06 | R-15, R-09, R-17 | `--budget 1.0`, `run spend t1 --usd 0.6` → `--usd 0.4` | 두 번째에서 `estimated_usd=1.0 >= 1.0`, `blocked_on="budget"`. `run step t1 4 -s done --force`는 오류("cannot be cleared"). `run resume t1`은 `running`으로 복구하지만 이후 `run spend t1`(0 가산)에서 다시 `blocked` |
| T-07 | R-18, R-19 | 프로필 `full`(steps 1..16), 단계 1·2 `done`, 분해 JSON `pipeline_tier:"light"` | `next_step="10"`, `remaining_steps=["10","15","16"]`, `skill_to_invoke="hyperresearch-10-triple-draft"`. 분해 JSON이 없으면 `next_step="3"` |
| T-08 | R-18, R-19 | 프로필 `light`(steps 1,2,10,15,16)로 시작, 단계 1·2 `done`, 분해 JSON `pipeline_tier:"full"` | 필수 집합은 1..16이고 매니페스트 단계가 먼저, 나머지가 뒤: `remaining_steps=["10","15","16","3","4","5","6","7","8","9","11","12","13","14"]`, `next_step="10"`(3이 아님) |
| T-09 | R-07, R-10, R-18 | `run event t1 --type chapter-plan --data '{"chapter":"ch1","title":"  Intro  "}'`, `{"chapter":true}`, 65자 id | `chapters.ch1={"status":"planned","title":"Intro"}`만 생김(나머지 둘은 로그에만). `chapters_pending=["ch1"]`. `run step t1 10 -s done --chapter ch1` 후 `chapters.ch1.status="step-10-done"`, `chapters_pending=[]`, 그러나 단계 `"10"`이 전역으로 `done`이 되므로 `next_step`이 장 진행과 무관하게 다음 미완 단계로 넘어간다 |
| T-10 | R-22, R-25 | 보고서 없음, 매니페스트 프로필 `full`, 분해 JSON 없음 | 검사: `report-exists`(실패), `artifact:critic-findings-{dialectic,depth,width,instruction}.json`, `artifact:patch-log.json`, `artifact:polish-log.json`(모두 실패). 길이·제목·밀도 검사는 없음. `passed=false` |
| T-11 | R-23 | 프로필 `full`, `response_format:"argumentative"` | 공백 단어 4000·12000은 통과(0.8×5000, 1.2×10000 경계 포함), 3999·12001은 `length-in-range` 실패. `response_format` 없음 → 이 검사 없음 |
| T-12 | R-24 | 본문 1000단어, `[1]`, `[2, 3]`, `[[a]]`, `[[b\|c]]`, `[[x]](http://u)` | 인용 수 5, 밀도 5.00 < 9.0 → `citation-density` 실패(`5.00 citations/1000 words (floor 9.0)`). 인용 9개면 통과 |
| T-13 | R-23, R-24 | 공백 없는 한 덩어리 3만 자 보고서, `argumentative` | 평균 토큰 길이 ≥ 15이므로 글자 기준: 허용 12000~36000, 통과. 밀도 분모는 30000/3.0=10000 단어 |
| T-14 | R-24 | `required_section_headings:["## 1. A"]`, 보고서에 `### x ## 1. A` | 부분 문자열이라 통과. 빈 목록이면 항상 통과 |
| T-15 | R-26 | `steps["14.5"].status=="done"`, `cite-check-findings.json`이 `{"findings":[{"severity":"critical"}]}`이고 `cite-check-patch-log.json` 없음 | `cite-check-resolved` 실패, detail `1 critical finding(s); patch log MISSING`. 14.5 기록이 없으면 이 검사는 목록에 없다 |
| T-16 | R-27, R-28 | 모든 검사 통과 / 하나라도 실패 | 통과: `status=done`, `blocked_on=null`, `verify.passed=true`, `verify.failed_checks=[]`, `finish` 이벤트, 종료 0. 실패: `status=blocked`, `blocked_on="verify"`, `verify.failed_checks`에 실패 이름, 종료 1. 둘 다 `spend`가 DB 개수로 갱신됨 |
| T-17 | R-29, R-30 | 최신 런 `running`, `updated_at`이 1시간 전, 남은 단계 있음 | 블록 JSON 한 줄. 7시간 전 → 출력 없음. 상태 `blocked`/`done` → 출력 없음. 남은 단계 없음 → 출력 없음. stdin `{"stop_hook_active": true}` → 출력 없음. `HYPERRESEARCH_STOP_GATE=off` → 출력 없음. 모두 종료 0 |
| T-18 | R-21 | `runs/` 아래 `run.json`이 깨진 디렉터리 `bad`와 정상 런 | `list`에서 `bad`는 `corrupt-manifest`로 마지막. 태그 생략 시 최신 시작 순 첫 항목을 쓴다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@aece65f) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 정규식·예외 읽음. 종료 코드는 `run_cmd.py` 각 핸들러가 `VaultError`를 잡는 것에서 도출 |
| R-02~R-05 | C-03, C-15 | `init_run` 전체 읽음 |
| R-06, R-07 | C-04 | 읽음. `--data` 비객체 예외는 `payload.update(json.loads(...))`에서 도출(추론: `update`에 리스트가 오면 `ValueError`/`TypeError`가 `JSONDecodeError`로 잡히지 않는다) |
| R-08~R-11 | C-05 | 읽음 |
| R-12~R-14 | C-07 | 읽음. 태그를 소문자로 비교하는 이유(노트 쪽 저장 형태)는 행 15 소관이라 확인하지 않음 |
| R-15 | C-06 | 읽음. `budget_usd == 0`이 `is not None`이라 첫 호출에서 차단되는 것은 코드에서 도출 |
| R-16 | C-08, C-18 | 읽음 |
| R-17~R-19 | C-09, C-11, C-16 | 읽음. 순서 규칙(필수 집합의 "뒤에 덧붙임")은 `resume_position`의 `ordered + extra`에서 직접 도출 |
| R-20, R-21, R-31 | C-10, C-08 | 읽음 |
| R-22~R-26 | C-12, C-13, C-23 | `verify_run` 전체 읽음. `decomposition-readable`이 실패일 때만 항목이 생기고 `ok=True`로 만들어지는 경로가 없음을 코드에서 확인 |
| R-27, R-28 | C-14, C-19 | 읽음 |
| R-29 | C-20 | 읽음 |
| R-30 | C-17 | 읽음 |
| R-32 | C-21 | 로스터 목록과 `_step_id_of_skill` 읽음. 모든 정수 1..16이 로스터에 있음 |
| R-33 | C-25 | 프롬프트 본문 읽음 |
| T-01~T-18 | 위 R-ID | 코드 읽기만으로 계산한 기대값. 원본 테스트는 열지 않았다 |

**문서와 구현의 차이 (구현을 사실로 썼다)**
- README는 "`run resume`이 죽은 정확한 단계에서 이어 간다"고 한다(`README.md:60`). 구현에서 단계 상태는 호스트가 `run step`을 부를 때만 바뀌고, 진입 스킬(`skills/hyperresearch.md:127`)만 모든 전이를 기록하라고 지시한다. 단계 스킬 중 `run step`을 직접 지시하는 곳은 `1.5`(`skills/hyperresearch-1-5-chapter-partition.md:62,79`)와 `14.5`(`skills/hyperresearch-14-5-cite-check.md:44,95`)뿐이다. `run spend`를 지시하는 스킬은 없어서 `estimated_usd`·`agents_spawned`는 호스트가 임의로 부르지 않으면 0이다.
- 프로필 `steps`는 정수 1..16(`profiles.py:234-242`)이라 `1.5`·`14.5`는 `profile_steps`·필수 집합에 절대 들어가지 않는다. `resume`의 `next_step`은 그 둘을 가리킬 수 없다(`14.5=done`은 `cite-check-resolved` 검사 때문에만 의미가 있다). `"6g"`·`"11g"`는 `skills/hyperresearch.md:92`와 `set_step` docstring에만 있고 어느 코드·스킬도 정의하지 않는다.
- 장(chapter) 루프: `steps`는 장 구분 없이 단계 id 하나에 한 항목이라 장 1이 단계 2를 끝내면 전역 단계 2가 `done`이 된다. 그래서 `resume`의 `next_step`은 장 진행을 반영하지 못하고 `chapters_pending`만 장 상태를 알려 준다. Stop 훅은 `next_step`만 본다(`stop_gate_decision`).
- 진입 스킬이 "매니페스트의 `profile`은 정보용, 분해의 티어가 우선"이라고 한 것은 `resume`·ship gate의 필수 단계 집합에 해당한다(`runs.py:627-646`). 길이·밀도 검사는 여전히 매니페스트 `profile`로 해석한 값을 쓴다(`runs.py:661`, `:705-730`).
- `#103`("dissertation의 길이·읽기·인용 목표를 읽는 곳이 없다", `README.md:167`)과 달리 `verify_run`은 `response_format`을 키로 `word_targets`를 읽는다. 다만 `dissertation` 키는 `response_format=="dissertation"`일 때만 쓰이는데 step 1 스킬은 `short/structured/argumentative`만 정의한다(`skills/hyperresearch-1-decompose.md:121-125`). 그래서 dissertation 런이 `argumentative`로 분류되면 `full`의 5000–10000 단어 ±20%로 측정된다(추론: step 1이 `dissertation` 형식을 내지 않는다는 전제).
- `run finish`가 검사하는 항목이 진입 스킬·README의 설명(`skills/hyperresearch.md:272`, `README.md:316`)보다 많다: `no-scaffold-leak`, `levers-rendered`, `decomposition-readable`. 반대로 설명이 말한 "철회 재확인"(`sources retractions`)은 게이트가 아니라 사전 호출이고, 게이트는 DB의 `is_retracted`만 읽는다.
- `vault-tag`의 모듈 설명(`cli/vault_tag.py:1-19`)은 `research/query-<tag>.md`를 말하지만 현재 런은 `runs/<tag>/query.md`를 쓰고, 태그 충돌 검사는 둘 다와 `runs/*` 디렉터리를 모두 본다(`:45-78`).
- `RUN_STATUSES`의 `paused`·`failed`는 CLI로 설정할 방법이 없다(`run_cmd.py`에 해당 명령 없음).
- `verify_run`·lint의 보고서·런 경로는 `research`를 하드코딩(`runs.py:668`, `lint.py:49`)하는 반면 `Vault.run_dir`은 `research_dir` 설정을 따른다(`vault.py:104-116`). `research_dir`를 바꾼 볼트에서는 보고서 경로가 어긋난다(추론: 설정 변경 시나리오를 실행해 보지 않음).
- 분해 JSON이 객체가 아닌 유효한 JSON이거나, `cite-check-findings.json` 항목이 dict가 아니면 `verify_run`이 처리되지 않은 예외로 끝난다(`runs.py:681-684`, `:834`).

### 2.2 코드 읽는 순서 [선택]
1. `core/runs.py` 상단 docstring(1-21)과 상수(30-82) → `init_run`/`_save` → `set_step` → `reconcile_spend_from_disk` 묶음(327-432) → `resume_position`/`_required_step_ids` → `verify_run` → `finish_run`.
2. `cli/run_cmd.py`는 각 명령이 위 함수를 얇게 감싼 것이다(오류 처리·출력만 추가). `run_resume`과 `run_stop_gate`만 로직이 있다.
3. `core/codex.py:347-398`은 `run_resume_position`을 재사용하는 한 함수다. 훅 설치(`merge_stop_hook`)는 행 1.
4. 진입 스킬 `skills/hyperresearch.md:218-283`(복구·종료 게이트)는 위 CLI를 부르는 호스트 쪽 절차다.

## 적용 메모 [선택]
(없음)
