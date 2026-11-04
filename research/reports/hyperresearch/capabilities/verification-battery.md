---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/cli/lint.py
  - src/hyperresearch/core/citecheck.py
  - src/hyperresearch/cli/citecheck_cmd.py
  - src/hyperresearch/core/patterns.py
  - src/hyperresearch/core/note.py
  - src/hyperresearch/core/scholar.py
  - src/hyperresearch/core/fetcher.py
  - src/hyperresearch/core/hooks.py
  - src/hyperresearch/core/config.py
  - src/hyperresearch/core/runs.py
  - src/hyperresearch/core/sync.py
  - src/hyperresearch/models/output.py
  - src/hyperresearch/cli/_output.py
  - src/hyperresearch/skills/hyperresearch.md
  - src/hyperresearch/skills/hyperresearch-14-5-cite-check.md
  - src/hyperresearch/skills/hyperresearch-15-polish.md
  - README.md
  - CHANGELOG.md
depends:
  - run-manifest-gate.md
  - vault-store.md
  - claims-store.md
status: ready
---

# 콘텐츠 검증 배터리

> 볼트(SQLite 색인)·런 산출물·최종 보고서를 결정적으로 검사해 이슈 목록을 내는 `hyperresearch lint`(규칙 26개 선언)와, 보고서의 (문장, 인용) 쌍을 뽑아 클레임 표로 기계 분류하고 에이전트가 볼 몫만 `cite-check-pairs.json`에 쓰는 `hyperresearch citecheck extract`를 제공한다. LLM은 부르지 않는다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 보고서 후처리 단계(스킬)가 `lint --rule <규칙> --json`을 규칙별로 부르거나(step 15.5 사전 검사 4개), 선택적으로 `lint --rule numeric-consistency --json`을 부른다. 이 호출들은 참고용이다. 구속력은 `run finish`의 `verify_run`이 가진다(경계: run-manifest-gate.md).
2. `lint`는 볼트를 찾고 `auto_sync`로 파일→DB를 맞춘 뒤, 선택된 규칙을 코드 순서대로 돌려 이슈(`rule`, `severity`, `note_id`, …)를 모은다. 보고서에 의존하는 3규칙(`quote-integrity`·`numeric-consistency`·`retracted-citations`)은 마지막에 한 번 보고서를 읽어 돌린다.
3. 출력은 요약(`errors/warnings/info/total`)과 이슈 목록이다. 이슈가 error여도 종료 코드는 0이다. 판정을 종료 코드로 바꾸는 쪽은 `verify_run`이다.
4. `verify_run`은 같은 함수 `_check_quote_integrity`·`_check_retracted_citations`를 직접 불러 error 이슈가 있으면 `quote-integrity`·`retracted-citations` 검사를 실패시킨다. 길이·제목·인용 밀도·스캐폴드 누출은 lint 규칙이 아니라 `verify_run` 자체 검사다(1.3 F).
5. step 14.5는 `citecheck extract <tag>`를 부른다. 보고서(Sources/References 앞부분)를 줄·문장으로 나누고 각 인용 표식을 볼트 노트 id에 묶어 쌍을 만든다.
6. 쌍마다 기계 분류한다: 노트에 안 묶이면 `dangling`, 노트의 클레임이 문장을 뒷받침하면 `supported-mechanical`, 나머지는 `needs-llm`. `needs-llm` 중 숫자·강한 표지가 있는 문장은 전부, 그 밖은 `--sample-rate`(기본 0.6) 비율로 골라 `runs/<tag>/cite-check-pairs.json`에 쓴다. 이 파일을 에이전트가 읽는 흐름은 경계다([critique-patch-polish](critique-patch-polish.md)).

### 1.2 범위·통합 지점 [필수]
- 제공: `lint` 명령(옵션·출력·JSON), 규칙 26개의 판정, 보고서 의존 3규칙의 알고리즘, `extract_pairs`·`parse_sources_section`·`triage_pairs`·`sample_needs_llm`·`write_pairs_file`, `citecheck extract` 명령, `cite-check-pairs.json` 형식.
- 제외(경계만):
  - `verify_run`의 구성·`run finish`의 상태 전이·`cite-check-resolved` 검사: run-manifest-gate.md. 이 스펙은 `verify_run`이 부르는 두 규칙 함수의 입출력(R-22)만 정의한다. `verify_run` 자체 검사 4종(길이 ±20%·필수 제목·인용 밀도·`## User Prompt (VERBATIM` 누출)은 그 스펙 R-23~R-25가 소유하고, 1.3 F에 비교용 요약만 둔다.
  - cite-checker 에이전트의 판정(supported/partially-supported/unsupported/wrong-source)·findings JSON·2차 패치: [critique-patch-polish](critique-patch-polish.md). 이 스펙은 `needs-llm` 쌍을 파일로 넘기는 데까지다.
  - `prompt-decomposition.json`의 필드 의미·작성(entry-decompose.md, draft)과 `loci.json`·`patch-log.json`·`critic-findings-*.json`을 쓰는 단계: 행 4~8. 여기서는 lint가 읽는 필드만 1.3 D에 적는다.
  - 노트·`claims`·`notes_fts` 스키마와 동기화: vault-store.md, claims-store.md. `is_retracted` 값을 채우는 일(`sources retractions`)은 source-quality.md.
- 외부 의존·선행 계약: `Vault.discover`·`auto_sync`·`vault.db`(vault-store.md), `notes`·`note_content.body_plain`·`notes_fts`(porter unicode61)·`tags`·`links`·`sources`·`claims` 테이블, `config.toml [lint]`, 런 산출물 이름(S1, run-manifest-gate.md). 파일시스템과 시계(`expired-notes`·`stale-reviews`는 현재 UTC 시각).
- 소유 상태·부작용: `lint`는 DB와 파일을 바꾸지 않는다(`auto_sync`가 DB 색인을 갱신하는 것은 제외). `citecheck extract`는 `runs/<tag>/cite-check-pairs.json`을 만들거나 덮어쓰고 런 디렉터리가 없으면 만든다(`run.json`은 만들지 않는다). 둘 다 보고서를 수정하지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**A. `hyperresearch lint`** (typer 앱, 하위 명령 없음)

| 옵션 | 의미 |
|---|---|
| `--rule`, `-r <이름>` | 그 규칙 하나만 실행. 목록에 없는 이름이면 아무 규칙도 돌지 않아 이슈 0건이고 "healthy"로 끝난다(오류 아님). 하나만 받는다 |
| `--audit-file <경로>` | `audit-gate`가 읽을 파일(볼트 루트 기준 상대 경로). 기본은 `_run_artifact`가 찾는 `audit_findings.json` |
| `--json`, `-j` | 봉투 `{ok:true, data:{issues:[…], summary:{errors,warnings,info,total}}, count:<이슈 수>, vault:<루트>, timestamp}` (`exclude_none`, UTF-8 들여쓰기 2) |
| `--fix` | 받기만 하고 쓰지 않는다(동작 없음) |

- 이슈 객체: `rule`(RULES 키), `severity`(`error`\|`warning`\|`info`), `note_id`(노트 id, 보고서면 `<report>`, 볼트 전체면 `<vault>`), `note_path`(있을 때만), `line`(`broken-links`만), `message`. 순서는 규칙 코드 순서이고 정렬하지 않는다.
- 텍스트 모드: 이슈 없으면 `Vault is healthy. No issues found.`. 있으면 이슈마다 `  <rule> <note_path 또는 note_id>[ line N]: <message>`를 심각도 색(error 굵은 빨강, warning 노랑, info 흐림)으로, 끝에 `Summary: E errors, W warnings, I info`.
- 종료 코드: 정상 종료는 이슈 유무·심각도와 무관하게 0이다. 볼트가 없으면 `VaultError`가 잡히지 않고 전파돼 비정상 종료한다(추론: 이 파일에 처리기가 없고 `Exit`도 없음).
- 시작 시 `Vault.discover()` + `vault.auto_sync()`(설정이 켜졌을 때만 색인 갱신).

**B. 규칙 26개** — 이름·순서는 `RULES` 딕셔너리(C-01). 심각도는 코드 문자열 그대로 `error`/`warning`/`info`. "노트 규칙"은 파일이 아니라 `notes` 등 DB 행을 본다. 판정 상세가 긴 규칙은 R-ID로 넘긴다.

공통 규칙: ① **보고서**는 `research/notes/final_report*.md` 중 mtime이 가장 최신인 파일이고(없으면 레거시 `final_report.md` 경로), 런 태그를 받지 않는다(R-03). ② **런 산출물**(`loci.json`·`patch-log.json`·`critic-findings-*.json`·`prompt-decomposition.json`·`scaffold.md`·`comparisons.md`·`audit_findings.json`)은 `research/runs/*/`(run.json이 있는 디렉터리) 중 run.json mtime이 최신인 것부터 보아 그 파일이 있는 첫 디렉터리, 없으면 레거시 `research/<이름>`이다. ③ 어느 규칙도 티어(`light`/`full`/…)나 `response_format`을 직접 읽지 않는다. 켜지는 조건은 산출물 존재 여부(`loci.json`은 full급 런만 만든다)·노트 태그·설정 파일로 결정된다.

| # | 규칙 | 검사 대상 | 판정·임계값 | 심각도 | 예외·켜지는 조건 | 상세 |
|---|---|---|---|---|---|---|
| 1 | `missing-title` | 노트 전부 | `title`이 `''` 또는 `Untitled` | warning | type 제한 없음 | R-04 |
| 2 | `missing-tags` | 노트 | `tags` 행이 하나도 없음 | warning | type이 `index`·`raw`면 제외 | R-04 |
| 3 | `missing-summary` | 노트 | `summary`가 NULL이거나 trim 길이 0 | warning | type이 `index`·`raw`면 제외 | R-04 |
| 4 | `uncurated` | 노트 | `status != 'draft'`이면서 `tier`가 NULL/`unknown` 또는 `content_type`이 NULL/`unknown`. 메시지에 빠진 필드(`tier`/`content_type`)와 현재 status | warning | type `index`·`raw`·`moc` 제외, id가 `_`로 시작하면 제외 | R-04 |
| 5 | `workflow` | 노트 + `scaffold.md`·`loci.json`·`comparisons.md` | 연구 산출 노트(id에 `final_report` 포함, type `moc`, 태그 `synthesis` 중 하나)가 1개 이상일 때만: ① scaffold 노트(태그 `scaffold`)도 `scaffold.md`도 없으면 error ② `loci.json`이 있는데 `type='interim'` 노트가 0이면 error ③ `loci.json`의 dict 원소가 1개 이상인데 `comparisons.md`가 없으면 error | error | `loci.json` 없으면 ②③ 생략. `loci.json` 파싱 실패 시 locus 수 0으로 취급해 ③ 생략 | R-21 |
| 6 | `scaffold-prompt` | 태그 `scaffold` 노트의 본문 | 첫 20개 비어 있지 않은 줄 안에 `## User Prompt (VERBATIM … gospel)` 헤더가 없으면 error. 정본 질문이 있으면 헤더 아래 텍스트가 정본과 정확히 같아야 error 해제, 정본이 없으면 길이 50자 미만이 warning | error / warning | scaffold 노트가 0개면 규칙이 아무것도 안 한다 | R-13 |
| 7 | `wrapper-report` | 보고서 + `wrapper_contract.json` | 보고서 없음, 계약에 선언된 `required_terminal_sections` 누락, 스캐폴드 전용 제목 10개(+계약의 `forbidden_body_sections`)가 본문에 부분 문자열로 존재 | error | `research/prompt.txt`·`query.md`/`query-*.md`·`wrapper_contract.json` 중 하나가 있어야 활성(V8 런은 `query.md`가 항상 있음) | R-14 |
| 8 | `audit-gate` | `audit_findings.json` | 최신 `conformance` run의 미해결 critical, conformance 없이 comprehensiveness만 있음, `status=failed`, 미해결 important(info), 자기인증 위반 | error / info / warning | 파일 없음 또는 `runs` 키 없음이면 이슈 0 | R-11, R-12 |
| 9 | `provenance` | 출처 노트의 `*Suggested by [[id]]` 이력 | 씨앗(이력 없음) 존재, 이력 대상 id 실존, 씨앗에서 BFS 도달, 비율 임계 | error / warning | 출처 노트 5개 이하면 전체 생략. `loci.json` 있으면 비율 검사 생략 | R-15 |
| 10 | `locus-coverage` | `loci.json` + `interim` 노트 | locus마다 태그 `locus-<name>`·type `interim` 노트가 1개 이상. 누락 2개 이상 error, 1개 warning. 한 locus에 interim이 2개 이상이면 warning | error / warning | `loci.json` 없으면 생략. 파싱 실패 error | R-16 |
| 11 | `patch-surgery` | `patch-log.json` | `skipped`에 `severity=="critical"` 항목이 있으면 error. 로그의 applied+skipped+conflicts가 0인데 critic findings가 있고 보고서가 있으면 warning | error / warning | `patch-log.json` 없으면 생략(light 티어는 만들지 않음) | R-18 |
| 12 | `instruction-coverage` | `prompt-decomposition.json` + 보고서 | `entities[].name`이 보고서(소문자)에 없음: 3개 이상 error, 1~2개 warning. `required_formats[]`의 첫 구가 없음: warning | error / warning | 분해 JSON과 보고서가 둘 다 있어야 함. JSON이 객체가 아니면 생략 | R-19 |
| 13 | `citation-style-preservation` | 보고서 + `citation_style` | `wikilink`면 실존 노트로 풀리는 `[[…]]`가 0개, `inline`이면 `[N]` 표식 또는 Sources/References 제목 부재 | error | `citation_style`이 `wikilink`/`inline`일 때만(`none`·없음 제외). 출처 노트와 보고서가 모두 있어야 함 | R-20 |
| 14 | `extract-coverage` | `extract` 태그 노트 | 출처 노트 N개에 대해 실제 추출 노트 수가 `max(1, N//3)` 미만이면 이슈. `max(1, N//4)` 미만이면 error, 아니면 warning | error / warning | `loci.json`이 있으면 규칙 전체 생략. 출처 노트 0이면 생략 | R-17 |
| 15 | `quote-integrity` | 보고서 | 따옴표 구간(5단어 이상)이 볼트 노트 본문에 없음 | error | 보고서 없으면 생략. `verify_run`이 호출 | R-07 |
| 16 | `numeric-consistency` | 보고서 + `claims` + 출처 노트 본문 | 보고서 수치가 증거 덩어리에 부분 문자열로도 없음 | warning | 보고서 없으면 생략. 게이트에 안 들어감 | R-08 |
| 17 | `retracted-citations` | 보고서 + `notes.is_retracted` | 철회(`is_retracted=1`) 노트를 `[[id]]`로 인용했는데 앞뒤 200자에 `retract` 없음 | error | 철회 노트 0개면 생략. `verify_run`이 호출 | R-09 |
| 18 | `orphaned-raw-files` | `research/raw/*` 파일 | 확장자가 pdf·png·jpg·jpeg·gif·webp이고 파일 stem이 어떤 노트 id와도 같지 않음 | warning | `research/raw`가 없으면 생략. `note_path`는 볼트 루트 기준 posix 경로 | R-06 |
| 19 | `singleton-tags` | `tags` | 태그가 정확히 노트 1개에만 쓰임. `note_id`에 태그 문자열을 넣음 | info | - | R-05 |
| 20 | `broken-links` | `links` | `target_id IS NULL`. 메시지 `Broken link: [[<target_ref>]]`, `line`=`line_number` | warning | - | R-05 |
| 21 | `orphaned-notes` | `notes`+`links` | 들어오는 링크도 나가는 링크도 없음 | info | type `index`·`raw` 제외 | R-05 |
| 22 | `duplicate-ids` | `notes` | `GROUP BY id HAVING count>1` | error | `notes.id`가 PK라 도달 불가(추론) | R-05 |
| 23 | `empty-notes` | `note_content.body` | `LENGTH(TRIM(body)) < 10` | info | type `index`만 제외 | R-05 |
| 24 | `stale-indexes` | - | 구현 없음. 이름·설명만 선언되어 어떤 입력에도 이슈가 없다 | - | - | R-02 |
| 25 | `expired-notes` | `notes.expires` | `expires < 현재 UTC ISO 문자열`(문자열 비교) | warning | `expires`가 NULL이면 제외 | R-05 |
| 26 | `stale-reviews` | `notes.reviewed` | `status='evergreen'`이고 `reviewed <` (지금 − `[lint] stale_review_days`일, 기본 90) ISO 문자열 비교 | info | `reviewed` NULL 제외 | R-05 |

**C. `hyperresearch citecheck extract <vault_tag>`**

| 항목 | 규칙 |
|---|---|
| 인자·옵션 | `vault_tag`(필수, 런 태그 정규식 검증은 `validate_run_tag`), `--report <경로>`(기본 `<볼트>/research/notes/final_report_<tag>.md`, 상대 경로는 현재 작업 디렉터리 기준), `--sample-rate <float>`(기본 0.6, 0~1로 잘림), `--json`/`-j` |
| 실패 | 볼트 없음 `NO_VAULT`, 태그 형식 위반 `INVALID_TAG`, 보고서 없음 `NO_REPORT`(메시지 `report not found: <경로>`). 모두 종료 코드 1. JSON이면 `{ok:false, error, error_code, vault?}` 봉투, 텍스트면 `Error: <메시지>` |
| 성공 출력(JSON) | `{ok:true, data:{pairs_file:<경로>, summary:{total, supported_mechanical, dangling, needs_llm}, sampled_for_llm:<건수>, dangling:<건수>}, vault, timestamp}`. 텍스트: `Cite-check triage: <total> pairs — <auto> auto-passed, <sampled> sampled for LLM verification, <dangling> dangling`. 종료 0 |
| 시작 | `auto_sync` 후 보고서를 `utf-8-sig`로 읽는다. `runs/<tag>/`가 없으면 만든다 |

**D. 쌍 객체와 `cite-check-pairs.json`**

| 필드 | 타입 | 의미 |
|---|---|---|
| `sentence` | string | 보고서 한 줄에서 잘라낸 문장 원문(앞뒤 공백 제외, 인용 표식 포함). 패처가 편집하는 텍스트 그대로다 |
| `marker` | string | `[N]`(그룹 `[7, 12]`는 번호마다 한 쌍) 또는 `[[note-id]]` |
| `note_id` | string\|null | 묶인 볼트 노트 id. 못 묶으면 null |
| `numbers` | list of string | `sentence` 전체(인용 표식 포함)에서 숫자 정규식(C-20)으로 뽑은 토큰 |
| `strong` | bool | 문장(소문자)에 `%`·`$`·`billion`·`million`·`increase`·`decrease`·`grew`·`fell` 중 하나가 부분 문자열로 있거나 문장에 숫자가 하나라도 있으면 true. 표식 안의 숫자도 센다(R-24) |
| `unresolved` | string? | `note_id`가 null일 때만: `no-sources-entry`·`unknown-note-id`·`unresolved-entry` |
| `verdict` | string | 분류 뒤에만 붙음: `dangling`\|`supported-mechanical`\|`needs-llm` |

`cite-check-pairs.json`(UTF-8, `ensure_ascii=False`, 들여쓰기 2): `{report:<보고서 경로 문자열>, summary:{total, supported_mechanical, dangling, needs_llm}, sampled_for_llm:[verdict가 needs-llm인 쌍 중 샘플], dangling:[verdict가 dangling인 쌍 전부]}`. `supported-mechanical` 쌍은 파일에 없다. `summary.needs_llm`은 샘플 전 개수다.

**E. lint가 읽는 입력 필드**

| 입력 | 읽는 필드 |
|---|---|
| `prompt-decomposition.json` | `entities`(list of {`name`}), `required_formats`(list of string), `citation_style`(string). 소유 스펙: entry-decompose.md 1.3 D |
| `research/wrapper_contract.json`(UTF-8 BOM 허용) | `required_terminal_sections`(list of string), `forbidden_body_sections`(list of string), `citation_style`(string, 분해 JSON의 값을 덮어씀). 하니스가 두는 외부 파일이고 이 레포가 만들지 않는다 |
| `loci.json` | `{"loci":[{name,…}]}` 또는 최상위 배열. 원소 중 dict만, `name`이 비면 건너뜀 |
| `patch-log.json` | `skipped`(list of {`severity`,`finding_id`,`critic`}), `applied`, `conflicts` |
| `critic-findings-{dialectic,depth,width}.json` | `findings`(list). `instruction`은 세지 않는다 |
| `audit_findings.json` | `{"runs":[{`mode`,`timestamp`,`status`,`criticals`:[{`id`,`description`,`fixed_at`}],`important`:[…같은 모양…]}]}` |
| `config.toml [lint]` | `extract_min_words`(150), `extract_coverage_divisor`(3), `stale_review_days`(90) |
| DB | `notes`(id, title, path, status, type, tier, content_type, source, parent, summary, expires, reviewed, word_count, is_retracted), `note_content`(body, body_plain), `notes_fts(body_plain)`, `tags`, `links`, `claims`(claim, quoted_support, numbers) |

**F. `verify_run` 자체 검사 4종 (lint 규칙이 아님, 소유: run-manifest-gate.md R-23~R-25·C-13. 비교용 요약)**

| 검사 | 조건 | 비고 |
|---|---|---|
| `length-in-range` | `response_format`이 프로필 `word_targets` 키일 때 공백 분리 단어 수가 `low×0.8 ≤ wc ≤ high×1.2` | 공백 토큰 평균 길이 ≥ 15.0이면 글자 수와 `char_targets_no_word_boundary`(없으면 `int(단어 목표×chars_per_word)`)로 같은 ±20% |
| `required-headings` | `required_section_headings`의 각 문자열이 보고서에 부분 문자열로 있음 | 순서는 보지 않음 |
| `citation-density` | `[n, m]`은 번호 수, `[[x]]`는 `WIKI_LINK_RE` 일치 수로 센 인용 ×1000 / max(1, 유효 단어 수) ≥ `citation_density_min` | 유효 단어 수는 단어 경계 없으면 글자/`chars_per_word` |
| `no-scaffold-leak` | `## User Prompt (VERBATIM` 부분 문자열이 없음 | lint `wrapper-report`의 10개 제목 검사보다 좁다 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `lint` 호출 | 1.3 A의 순서로 `discover`→`auto_sync`→규칙 실행. `rules_to_run`은 `--rule`이 있으면 `[rule]`, 없으면 `RULES` 키 26개 전부. 규칙 코드 실행 순서는 `missing-title`, `missing-tags`, `missing-summary`, `audit-gate`, `scaffold-prompt`, `wrapper-report`, `provenance`, `locus-coverage`, `extract-coverage`, `patch-surgery`, `instruction-coverage`, `citation-style-preservation`, `orphaned-raw-files`, `workflow`, `uncurated`, `singleton-tags`, `broken-links`, `orphaned-notes`, `duplicate-ids`, `empty-notes`, `expired-notes`, `stale-reviews`, (보고서 의존 3규칙), (자기인증 후검사). `summary`의 건수는 심각도 문자열 일치 수. 어떤 경우에도 `typer.Exit`을 던지지 않는다 | 코드 확인 |
| R-02 | `--rule`에 알 수 없는 이름·`stale-indexes`, 또는 `--fix` | 이슈 0건·종료 0. `stale-indexes`는 선언만 있고 검사 블록이 없다. `--fix`는 읽지 않는다. 단 `audit-gate`가 돌면 `rules_to_run`에 규칙이 추가될 수 있다(R-12) | 코드 확인 |
| R-03 | 보고서·런 산출물 해석 | `_latest_report`: `research/notes/final_report*.md` glob의 mtime 최대, `utf-8-sig`로 읽고 읽기 오류나 후보 없음이면 `(None, None)`. `_run_artifact`·`_query_files`는 1.3 B 공통 규칙 ②와 같다(`query.md`는 최신 런부터 모은 뒤 레거시 `query-*.md`를 이름순으로 뒤에 붙임). 어느 쪽도 런 태그로 거르지 않으므로 볼트에 런이 여러 개면 최신 것이 쓰이고, `verify_run`이 보는 `final_report_<tag>.md`와 다른 파일을 lint가 볼 수 있다 | 코드 확인 |
| R-04 | 노트 규칙 1~4 | 1.3 B 표의 SQL 조건대로 노트마다 이슈 한 건(warning). `note_path`=`notes.path`. 메시지: `Note has no meaningful title.`, `Note has no tags.`, `Note has no summary. Add one for better search and listings.`, `Note is <status> but missing tier/content_type. Run curation pass.` | 코드 확인 |
| R-05 | 위생 규칙 19~23·25·26 | 1.3 B 표대로. `singleton-tags`는 태그당 한 건. `broken-links`는 링크 행당 한 건(`line` 포함). `expired-notes`는 `expires`와 `datetime.now(UTC).isoformat()`을 SQL에서 문자열로 비교한다(타임존·형식이 다른 문자열이면 사전순 결과). `stale-reviews` 메시지 `Last reviewed YYYY-MM-DD. Consider re-reviewing.` | 코드 확인 |
| R-06 | `orphaned-raw-files` | `research/raw`의 직계 파일(하위 디렉터리 제외) 중 확장자(소문자)가 `.pdf .png .jpg .jpeg .gif .webp`이고 `stem`이 노트 id 집합에 없으면 warning. `note_id`=stem | 코드 확인 |
| R-07 | `quote-integrity` (C-03·C-04) | ① 본문 = 보고서에서 첫 `## Sources`/`## References`(2단계 제목, 대소문자 무시, 줄 맨 앞) 이후를 버리고 `[N]`·`[N, M]`(1~3자리) 표식을 지운 것. ② 따옴표 구간 정규식(C-03)으로 구간을 뽑는다: 여는 `"` 또는 `“`, 닫는 `"` 또는 `”`, 내용은 따옴표 문자를 뺀 1~600자(개행 포함)의 최단 일치. ③ 내용의 공백열을 한 칸으로 줄이고 공백 분리 단어가 5개 미만이면 건너뛴다. ④ 아니면 내용의 `"`를 공백으로, `'`를 `''`로 바꾼 문구로 `SELECT id FROM notes_fts WHERE notes_fts MATCH 'body_plain: "<문구>"' LIMIT 1`을 실행한다. FTS 문구 일치는 `porter unicode61` 토큰 열의 연속 일치라서 대소문자·구두점·어형(복수·시제)·하이픈 유무에 둔감하다. ⑤ 행이 있으면 통과, 없거나 쿼리가 예외를 던지면 error 한 건(`note_id=<report>`, 메시지에 구간 앞 120자). 대상 노트는 FTS에 든 모든 노트(출처·`interim`·`source-analysis`·`moc` 등 type 무제한, `claims`는 제외). 최종 보고서는 frontmatter가 없어 색인되지 않으므로 자기 자신과 일치하지 않는다. 같은 구간이 두 번 나오면 이슈도 두 건 | 코드 확인 |
| R-08 | `numeric-consistency` (C-03·C-05) | 본문(R-07 ①)에서 수치 정규식(C-03: 소수는 자릿수 무관, 쉼표 포함 4자 이상 숫자열, 정수%)으로 뽑아 끝의 `.`·`,`를 지운 집합. 비면 이슈 없음. 증거 덩어리 = `claims` 전 행(`claim`·`quoted_support`·`numbers`)과 `source IS NOT NULL`인 모든 노트의 `body_plain`을 공백으로 이은 뒤 쉼표를 전부 제거한 문자열(런·인용 여부로 거르지 않음). 수치에서도 쉼표를 지워 증거 덩어리의 부분 문자열이 아니면 미추적. 미추적 수치를 문자열 사전순으로 정렬해 앞 20개마다 warning, 20개를 넘으면 `...and N more untraceable numbers (showing first 20).` 한 건. 부분 문자열이라 `10.5`는 `110.52` 안에서도 추적된 것으로 본다 | 코드 확인 |
| R-09 | `retracted-citations` (C-06) | `is_retracted = 1`인 노트 {id→title}. 없으면 종료. 보고서 **전체 텍스트**(Sources 포함, 코드 구간 제거 없음)에서 `WIKI_LINK_RE`(C-22; `[[id]]`·`[[id\|별칭]]`, 뒤에 `(`가 오면 제외) 일치마다 대상이 철회 노트면, 일치 앞뒤 200자 창(소문자)에 부분 문자열 `retract`가 없을 때 error(`note_id`=대상 id). 창 안의 `retract`는 다른 소스에 관한 것이어도 면제한다. 숫자형 `[N]` 인용은 검사하지 않는다(inline 스타일 보고서의 철회 인용은 이 규칙에 안 잡힌다) | 코드 확인 |
| R-10 | 보고서 의존 3규칙 디스패치 | 3규칙 중 하나라도 선택되면 `_latest_report`를 한 번 부른다. 결과가 None이면 셋 다 조용히 건너뛴다(이슈 없음). 아니면 `quote-integrity`→`numeric-consistency`→`retracted-citations` 순으로 실행해 이슈를 이어 붙인다 | 코드 확인 |
| R-11 | `audit-gate` 본체 (C-07) | 파일 경로: `--audit-file`이면 `<볼트 루트>/<값>`, 아니면 `_run_artifact("audit_findings.json")`. 파일이 없으면 이슈 없음. JSON 파싱·읽기 실패면 error(`... is malformed (<예외명>)`). 최상위가 dict가 아니면 이슈 없음. `runs` 중 `mode=="conformance"`와 `"comprehensiveness"`를 나눈다. ① conformance가 0개이고 comprehensiveness가 있으면 error. 둘 다 0이면 통과(초기 단계) ② conformance가 있으면 `timestamp` 문자열 정렬 최신 run: `criticals` 중 `fixed_at`이 falsy인 것이 있으면 error(최대 5개를 `[id] description[:80]`으로 나열), 없고 `status=="failed"`면 error ③ 두 모드 각각의 최신 run에 미해결 `important`가 있으면 info(차단 아님) | 코드 확인 |
| R-12 | `audit-gate` 자기인증 (C-08) | 두 모드 각각의 최신 run에서 `fixed_at`이 있는 critical마다 `(description + " " + id)` 소문자에서 키워드 표(C-08)를 위에서부터 훑어 처음 맞는 규칙을 그 critical의 "보증 규칙"으로 삼고, 그 규칙이 `rules_to_run`에 없으면 추가한다(그래서 `--rule audit-gate`만 줘도 보증 규칙이 돌고 그 이슈가 출력에 섞인다). 표에 안 맞으면 warning(`... not machine-verified`). 모든 규칙이 끝난 뒤 보증 규칙마다 같은 규칙의 error 이슈가 1건 이상 있으면 `SELF-CERTIFICATION VIOLATION` error 한 건을 보증마다 추가한다 | 코드 확인 |
| R-13 | `scaffold-prompt` (C-09) | 대상: 태그 `scaffold`인 노트의 `body`. 정본 질문: `_query_files` 결과가 있으면(첫 원소가 `query.md`이면 그 하나, 아니면 레거시 목록의 마지막) `utf-8-sig`로 읽고 CRLF→LF, `---`로 시작하면 첫 `\n---\n`(3번째 문자 이후)까지 frontmatter로 보고 그 뒤를 취해 끝의 `\n`을 제거한 것. 없으면 `research/prompt.txt`(같은 정규화). 본문에서 첫 20개 비어 있지 않은 줄 안에 헤더 정규식(`^\s*##\s+User\s+Prompt\s*\(\s*VERBATIM.*gospel\s*\)`, 대소문자 무시)이 있어야 하고 없으면 error 후 다음 노트. 헤더 다음 줄부터 `##`로 시작하는 줄 전까지를 모으되 `>`로 시작하는 줄은 `>`와 뒤 공백 한 칸을 떼고, 앞뒤 빈 줄을 버린 뒤 `\n`으로 잇는다. 정본이 있으면 같아야 하고(다르면 error) 다음 노트로 간다. 정본이 없으면 추출 텍스트가 50자 미만일 때만 warning | 코드 확인 |
| R-14 | `wrapper-report` (C-10·C-11) | 활성 조건: `research/prompt.txt`가 있거나 `_query_files`가 비지 않았거나 `wrapper_contract.json`이 읽혔을 때. 계약 파일이 있는데 파싱 실패면 error(그래도 나머지는 진행). 보고서 = `final_report*.md` mtime 최신(없으면 `notes/final_report.md`). 없으면 error 하나로 끝. 읽기 오류는 error를 내고 본문을 빈 문자열로 두고 계속한다. 본문(CRLF→LF)에서 ① 계약 `required_terminal_sections` 문자열 중 본문에 부분 문자열로 없는 것이 있으면 error(목록 나열) ② 금지 제목 = `SCAFFOLD_ONLY_SECTION_HEADERS` 10개(C-11) + 계약 `forbidden_body_sections`(중복 제외) 중 본문에 부분 문자열로 있는 것이 있으면 error(목록 나열). 줄 맨 앞인지는 보지 않는다 | 코드 확인 |
| R-15 | `provenance` (C-12) | 대상 출처 노트: `source IS NOT NULL`, id가 `_`로 시작하지 않음, type이 `index`·`raw`·`moc`가 아님. 5개 이하면 아무것도 안 한다. 아니면 노트마다 본문에서 `\*Suggested by \[\[([^\]]+)\]\]` 대상을 모아 `\|` 앞부분만 취한다. 씨앗 = 이력이 없는 노트. ① 씨앗 0개면 error ② 이력 있는 노트의 대상 id가 `notes`에 없으면 error(앞 10건) ③ 씨앗에서 "제안자→제안받은 노트" 역방향 맵으로 BFS해 도달 못 한 이력 노트가 있으면 error 한 건(앞 5개 id). 비율 검사는 `loci.json`이 없을 때만: 이력 노트 0개이고 출처 5개 초과면 error, 비율 < 0.3이고 출처 10개 초과면 error, 비율 < 0.5이고 10개 초과면 warning(첫 맞는 가지만) | 코드 확인 |
| R-16 | `locus-coverage` (C-13) | `loci.json`이 없으면 생략. 읽기·파싱 실패면 error 하나(locus 목록은 빈 것으로). locus마다 `n.type='interim'`이면서 태그 `locus-<name>`(이름 그대로, 소문자화하지 않음)인 노트 수가 0이면 누락. 누락 수 ≥ 2이면 error, 1이면 warning(목록은 앞 6개). 별도로 interim이 2개 이상인 locus가 있으면 warning 한 건 | 코드 확인 |
| R-17 | `extract-coverage` (C-14) | `loci.json`이 있으면 생략. 출처 수 N = `source IS NOT NULL`, id가 `_`로 시작하지 않음, type이 `index`·`raw`·`moc`가 아님, 태그가 `extract`·`scaffold`·`comparison`·`dud` 중 어느 것도 아닌 노트 수. 실제 추출 수 = 태그 `extract`이고 `word_count ≥ extract_min_words`이며 `parent`가 `source IS NOT NULL`인 노트를 가리키고 태그 `dud`가 없는 노트 수. N ≥ 1일 때 필요 수 = `max(1, N // extract_coverage_divisor)`, 오류 하한 = `max(1, N // (divisor+1))`. 실제 < 필요면 이슈 한 건: 실제 < 하한이면 error, 아니면 warning. 메시지에 스텁(길이 미달)·부모 없는 추출 수를 덧붙인다 | 코드 확인 |
| R-18 | `patch-surgery` (C-15) | `patch-log.json`이 없으면 생략. 파싱 실패면 error 하나(로그는 `{}`). `skipped` 중 dict이고 `severity=="critical"`인 것이 있으면 error 한 건(앞 5개를 `#<finding_id> (<critic>)`). 로그 합계(applied+skipped+conflicts)가 0이고, `critic-findings-{dialectic,depth,width}.json`의 `findings` 길이 합이 0보다 크며 `final_report*.md`가 있으면 warning 한 건("패처 로그가 유실됐을 가능성"). critic 파일이 객체가 아니라 배열이면 `.get` 때문에 예외가 난다(잡는 예외는 JSON·OS 오류뿐) | 코드 확인 |
| R-19 | `instruction-coverage` (C-16) | 분해 JSON과 보고서(`final_report*.md` mtime 최신, 없으면 `final_report.md`)가 모두 있어야 함. JSON 파싱 실패면 error 하나. 객체가 아니면 생략. 보고서는 `utf-8`로 읽어 소문자화. `entities`의 dict 중 `name`이 비지 않고 `name.lower()`가 보고서에 부분 문자열로 없는 것을 모은다: 3개 이상 error, 1~2개 warning(앞 8개와 `+N more`). `required_formats`의 문자열마다 `" of "`로 나눈 첫 조각을 trim·소문자화해 보고서에 없으면 모아 warning 한 건(앞 5개). `sub_questions`·`required_sections`는 검사하지 않는다 | 코드 확인 |
| R-20 | `citation-style-preservation` (C-17) | 스타일 = 분해 JSON의 `citation_style`(문자열일 때), `wrapper_contract.json`에 문자열 `citation_style`이 있으면 그것이 덮어쓴다(각 파일의 파싱 실패는 이 규칙에서 보고하지 않음). `wikilink`/`inline`이 아니면 종료. 출처 노트(R-15의 출처 조건) 수가 0이거나 보고서가 없으면 종료. `wikilink`: `\[\[([^\]]+)\]\]`로 뽑아 `\|` 앞을 trim한 대상 중 실존 노트 id가 하나도 없으면 error(링크 0개인지, 있으나 안 풀리는지를 메시지에 구분). `inline`: `\[\d+(?:\s*,\s*\d+)*\]` 일치가 있고 `^#{1,6}\s*(sources\|references)\b`(대소문자 무시, 줄 단위) 제목도 있어야 하며, 빠진 것(표식/제목)을 메시지에 적은 error. 밀도 검사는 하지 않는다(존재 여부만) | 코드 확인 |
| R-21 | `workflow` (C-18) | 1.3 B 5번 행의 세 조건. 연구 산출 노트 수는 `id LIKE '%final_report%' OR type='moc' OR 태그 synthesis`. 최종 보고서는 frontmatter가 없어 노트가 아니므로 V8 런에서 이 수는 `moc`·`synthesis` 노트로만 채워진다(추론: 동기화 규칙·스킬 지시에서 도출) | 코드 확인 |
| R-22 | `verify_run`이 부르는 함수 | `_check_quote_integrity(vault, conn, report_path, report_text)`, `_check_retracted_citations(…)`는 이슈 dict 목록을 돌려준다. 호출자는 `severity=="error"`만 센다. 보고서 본문은 `final_report_<tag>.md`(`utf-8-sig`)이고 `_latest_report`를 거치지 않는다. 함수가 예외를 던지면 `content-lints` 검사가 실패한다(run-manifest-gate.md). `numeric-consistency`는 `verify_run`에 없다 | 코드 확인 |
| R-23 | `extract_pairs` 문장 분리(C-20·C-22·C-24) | 본문 = 보고서에서 첫 `^##\s+(Sources\|References)\b`(대소문자 무시, 여러 줄 모드) 앞부분. 본문을 `mask_code`한 것과 줄 단위로 짝지어(줄 수가 같다) 줄마다: 마스킹 줄이 공백뿐(빈 줄·펜스 코드 줄)이거나 원문 줄이 링크 정의 `^\s*\[\d+\]:`이면 건너뛴다. 아니면 원문 줄을 문장으로 자른다: 분리점은 `[.!?]` 뒤의 공백열 중 다음 글자가 `A-Z`나 CJK(U+4E00~9FFF)인 곳(줄바꿈은 줄 단위라 없음). 문장 = 줄에서 그 구간(앞뒤 공백 제외)의 **원문**, 표식 탐색용 텍스트 = 마스킹 줄의 같은 구간. 문장은 줄 안에서만 만들어지므로 여러 줄에 걸친 문장은 줄마다 따로 쌍이 된다. 제목·목록·표 줄도 제외하지 않는다 | 코드 확인 |
| R-24 | `extract_pairs` 번호 표식 | 문장의 마스킹 텍스트에서 `\[(\d{1,3}(?:\s*,\s*\d{1,3})*)\]`마다 번호를 쉼표로 나눈다. 번호 중 하나라도 `0`으로 시작하고 Sources 맵에 없는 키면 표식 전체를 인용으로 보지 않는다(`[0]`·`[007]` 등). 번호마다: 맵에 있으면 `marker="[<번호>]"`, `note_id`=맵 값, 값이 None이면 `unresolved="unresolved-entry"`. 맵에 없고 맵이 비어 있지 않으면 `note_id=None, unresolved="no-sources-entry"`. 맵이 비어 있으면 인용이 아니다(Sources에 `[N] …` 줄이 하나도 없는 보고서에서 `[3]`은 무시). 쌍 객체는 번호 표식 쌍들 뒤에 위키링크 쌍들이 온다. `numbers`·`strong`은 표식이 든 문장 전체에서 계산하므로 `[3]`의 `3`이 숫자로 잡혀 번호 인용 문장은 모두 `strong=true`다 | 코드 확인 |
| R-25 | `extract_pairs` 위키링크 | 문장 마스킹 텍스트에서 `WIKI_LINK_RE` 일치마다 대상(trim)이 `notes` id 집합에 있으면 `marker="[[<id>]]"`, `note_id`=id. 없으면 `note_id=None, unresolved="unknown-note-id"`. id에 숫자가 들어 있으면(예: `gpt-4-report`) 문장이 `strong`이 된다. 같은 문장·표식도 중복 제거하지 않는다 | 코드 확인 |
| R-26 | `parse_sources_section` (C-21·C-23) | Sources/References 제목(R-23과 같은 정규식, 줄 맨 앞) 다음 줄부터 `## `로 시작하는 줄 전까지, `^\s*\[(\d{1,3})\]\s+(.+)$` 줄을 `번호→노트 id` 맵 항목으로 만든다(같은 번호는 뒤가 덮어씀, 번호 문자열은 앞의 0 포함 그대로). 노트 해소는 순서대로 첫 성공: ① 줄에서 `https?://\S+` 첫 일치의 끝 `.,)`를 뗀 URL로 `sources` 테이블의 살아 있는 노트(`note_id` 비NULL), 없으면 `notes.source = URL` 정확 일치(id 순 첫 행) ② 줄에서 첫 `http` 앞 부분을 ` .–-`로 trim한 제목과 `notes.title`의 대소문자 무시 일치(정렬 없는 첫 행) ③ URL의 DOI 키(`_doi_key`)와 `lower(notes.doi)`가 같은 노트가 정확히 1개 ④ `lower(notes.source)`에 DOI 키가 부분 문자열로 있고 그 뒤가 문자열 끝 또는 `?`·`#`·`&`인 첫 노트(id 순). 모두 실패하면 값은 None. DOI 키: `extract_doi(url)`(doi.org 호스트 경로나 arXiv URL만 해당)의 소문자 값이되, URL 파싱이 `ValueError`이거나, `(`가 `)`보다 많거나, 경로에서 `DOI_RE`가 끝난 뒤 `>"'`를 뗀 나머지가 남으면 키 없음 | 코드 확인 |
| R-27 | `triage_pairs` (C-25) | 쌍마다 `note_id`가 None이면 `verdict="dangling"`. 아니면 문장에서 위키링크(`WIKI_LINK_RE`)와 번호 표식을 제거하고 소문자화·공백 정리 후 양끝 ` .,:;`를 뗀다. 숫자 토큰(숫자 정규식 C-20)을 모으되 쉼표·끝의 `.`를 뗀 길이가 2 이상인 것만 "수치"로 센다(`Step 1`·`GPT-4`의 `4`는 라벨). 수치가 있으면: 이 문장이 인용된 노트의 어떤 클레임의 `claim` 또는 `quoted_support`(같은 정규화·trim)와 **완전히 같을 때만** 통과. 수치가 없으면: 그 노트 모든 클레임의 `claim`+`quoted_support`를 공백으로 이어 같은 정규화를 한 덩어리 안에 문장의 연속 6단어 조각(공백 분리, 구두점은 단어에 붙은 채) 중 하나가 부분 문자열로 있으면 통과(6단어 미만 문장은 통과 불가). 통과면 `supported-mechanical`, 아니면 `needs-llm`. 클레임이 없는 노트는 항상 `needs-llm`. `claims.numbers` 칼럼은 읽지 않는다. 반환 `{total, supported_mechanical, dangling, needs_llm, pairs}` | 코드 확인 |
| R-28 | `sample_needs_llm` (C-26) | 입력 순서대로 `verdict=="needs-llm"`만 본다. `strong`이면 전부 포함. 나머지(weak)는 `rate=clamp(sample_rate,0,1)`로 `weak_seen`을 1씩 올리며 `int(weak_seen*rate) > int((weak_seen-1)*rate)`일 때만 포함한다(무작위 없음, 재현 가능). 결과는 입력 순서를 유지한다 | 코드 확인 |
| R-29 | `write_pairs_file` | 보고서 `utf-8-sig` 읽기 → `extract_pairs(report, vault.db)` → `triage_pairs` → `sample_needs_llm` → `runs/<tag>/`(없으면 생성) `cite-check-pairs.json`을 1.3 D 형식으로 쓰고(기존 파일 덮어씀) 같은 객체를 돌려준다 | 코드 확인 |
| R-30 | `citecheck extract` CLI | 1.3 C의 순서: 볼트 발견(실패 `NO_VAULT`) → 태그 검증(`INVALID_TAG`) → `auto_sync` → 보고서 존재(`NO_REPORT`) → R-29 → 출력. 성공 종료 0. cite-check 에이전트 호출·`run step 14.5` 기록은 이 명령이 하지 않는다 | 코드 확인 |
| R-31 | `verify_run` 자체 검사 4종 경계 | 1.3 F 표의 판정은 run-manifest-gate.md 소유다. lint에는 같은 이름의 규칙이 없고, `lint`는 이 검사들을 부르지 않는다 | 코드 확인 |

- 불변식: (1) `lint`·`citecheck`의 판정은 DB·파일 상태와 현재 시각(`expired-notes`·`stale-reviews`)만의 함수이고 LLM·네트워크를 쓰지 않는다. (2) `lint`는 종료 코드로 판정을 알리지 않는다. 호출자는 `summary`나 이슈 `severity`를 읽어야 한다. (3) `sample_needs_llm`은 같은 입력에 같은 결과를 낸다. (4) `cite-check-pairs.json`에는 `needs-llm`이 아니거나 샘플에서 빠진 쌍이 `sampled_for_llm`에 없고, `dangling`은 전부 들어 있다.
- 미결정: 없음.
- 확인 한계: 코드를 실행하지 않았다. FTS5가 토큰이 하나도 없는 문구(예: 기호만 5단어)를 어떻게 처리하는지는 실행으로 확인하지 못했다. 예외든 무일치든 `quote-integrity`는 그 구간을 error로 보고하므로 결과가 같다는 것은 코드에서 도출한 추론이다. `lint`의 Windows 콘솔 출력·rich 마크업 이스케이프(메시지의 `[[…]]`)는 보지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스는 MIT(overview 1절)라 인용 제약이 없다. 줄 번호는 기준 SHA다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/hyperresearch/cli/lint.py:17-44` `RULES` | 규칙 26개의 이름·순서·설명 문구 | R-01, R-02 |
| C-02 | `lint.py:47-95` `_run_dirs_newest_first`·`_run_artifact`·`_query_files`·`_latest_report` | 런 디렉터리 탐색·산출물 해소·보고서 선택 | R-03 |
| C-03 | `lint.py:98-107` `_QUOTE_SPAN_RE`·`_REPORT_NUMBER_RE`·`_report_body_only` | 따옴표 구간·수치 정규식, Sources 이후 제거와 `[N]` 표식 제거 | R-07, R-08 |
| C-04 | `lint.py:110-147` `_check_quote_integrity` | FTS 문구 일치 판정·이슈 형태 | R-07 |
| C-05 | `lint.py:150-197` `_check_numeric_consistency` | 증거 덩어리 구성, 추적 판정, 20개 상한 | R-08 |
| C-06 | `lint.py:200-232` `_check_retracted_citations` | 철회 노트 인용 판정, ±200자 `retract` 면제 | R-09 |
| C-07 | `lint.py:235-264`, `:309-431`, `:1767-1778`, `:1808-1835` `lint` 본체 | 옵션 선언, `audit-gate`, 보고서 의존 규칙 디스패치, 요약·출력 | R-01, R-10, R-11 |
| C-08 | `lint.py:433-574`, `:1780-1806` | `audit-gate` 키워드→보증 규칙 표(`kw_to_rule`)와 자기인증 후검사 | R-12 |
| C-09 | `lint.py:576-708` `scaffold-prompt` 블록 | 헤더 정규식, 정본 질문 읽기·frontmatter 제거, 헤더 아래 텍스트 추출, 비교 | R-13 |
| C-10 | `lint.py:710-825` `wrapper-report` 블록 | 활성 조건, 계약 필드, 누락·누출 판정 | R-14 |
| C-11 | `src/hyperresearch/core/hooks.py:105-116` `SCAFFOLD_ONLY_SECTION_HEADERS` | 스캐폴드 전용 제목 10개 | R-14 |
| C-12 | `lint.py:827-1003` `provenance` 블록 | 이력 정규식, 씨앗·BFS·비율 임계 | R-15 |
| C-13 | `lint.py:1005-1095` `locus-coverage` 블록 | locus별 interim 조회, error/warning 경계 | R-16 |
| C-14 | `lint.py:1097-1199`, `src/hyperresearch/core/config.py:155-160` `LintSettings` | 추출 커버리지 SQL·임계, `[lint]` 기본값 | R-17 |
| C-15 | `lint.py:1201-1296` `patch-surgery` 블록 | 건너뛴 critical, 빈 로그 감지 | R-18 |
| C-16 | `lint.py:1298-1394` `instruction-coverage` 블록 | 엔티티·형식 존재 검사와 심각도 | R-19 |
| C-17 | `lint.py:1396-1510` `citation-style-preservation` 블록 | 스타일 해소(계약 우선), wikilink·inline 판정 | R-20 |
| C-18 | `lint.py:1538-1642` `workflow` 블록 | 산출물 존재 검사 | R-21 |
| C-19 | `lint.py:271-307`, `:1512-1536`, `:1644-1765` | 노트 위생 규칙들의 SQL 조건 | R-04~R-06 |
| C-20 | `src/hyperresearch/core/citecheck.py:33-57` 상수·`_sentence_spans` | 문장 분리·번호 표식·수치 정규식, 강한 표지 목록 | R-23, R-24 |
| C-21 | `citecheck.py:59-175` `_doi_key`·`_note_for_url`·`_note_with_doi`·`_note_holding_doi`·`parse_sources_section` | Sources 줄→노트 해소 4단계 | R-26 |
| C-22 | `src/hyperresearch/core/patterns.py:24`, `:63-153` `WIKI_LINK_RE`·`_strip_fenced_blocks`·`_strip_inline_code`·`mask_code` | 위키링크 정규식, 코드 마스킹(길이 보존) | R-09, R-23, R-25 |
| C-23 | `src/hyperresearch/core/scholar.py:40`, `:63-94`; `src/hyperresearch/core/fetcher.py:11-23` | `DOI_RE`, `_clean_doi`, `extract_doi`, `existing_live_note_for_url` | R-26 |
| C-24 | `citecheck.py:178-250` `extract_pairs` | 쌍 생성, 표식 해소, `unresolved` 사유, 쌍 필드 | R-23~R-25 |
| C-25 | `citecheck.py:253-327` `_norm`·`triage_pairs` | 기계 분류 | R-27 |
| C-26 | `citecheck.py:330-371` `sample_needs_llm`·`write_pairs_file` | 샘플링, 파일 형식 | R-28, R-29 |
| C-27 | `src/hyperresearch/cli/citecheck_cmd.py:15-78` `citecheck_extract` | 옵션·오류 코드·출력 | R-30 |
| C-28 | `src/hyperresearch/core/note.py:175-196` `strip_markdown` | `body_plain`이 되는 변환(FTS 일치 대상) | R-07, R-08 |
| C-29 | `src/hyperresearch/core/runs.py:35-54`, `:704-777` | `verify_run` 자체 검사 4종(소유: run-manifest-gate.md C-13). 비교용 | R-31 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(코드를 실행하지 않음). 별도 표기 없으면 DB는 `auto_sync`된 상태다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-07 | 출처 노트 본문 `Language models are getting better at reasoning tasks every year.` 보고서 `As noted, "Language model are getting better at reasoning task" [1].` | 일치(porter 어형 무시)로 `quote-integrity` 이슈 0 |
| T-02 | R-07 | 보고서에 4단어 따옴표 구간 `"three word phrase here"`와 6단어짜리 `"nothing like this exists anywhere in vault"`(어느 노트에도 없음) | 앞 구간은 건너뜀. 뒤 구간만 error 1건(`note_id="<report>"`, 메시지에 구간 앞 120자) |
| T-03 | R-07 | 따옴표 구간이 `## Sources` 아래에만 있음 | 이슈 0(본문에서 잘림) |
| T-04 | R-08 | `claims.numbers`=`["$1,234"]`, 보고서 `…grew by 1,234 units and 47% overall.` | `1,234`는 추적됨(쉼표 제거 `1234`가 증거에 있음). `47%`가 증거에 없으면 warning 1건 |
| T-05 | R-09 | 노트 `paper-a`의 `is_retracted=1`. 보고서 (a) `Smith [[paper-a]] found X.` (b) `Smith [[paper-a]] (retracted in 2025) found X.` (c) `[[paper-a]](https://x)` (d) 번호 인용 `[1]`이 Sources에서 `paper-a`를 가리킴 | (a)만 error 1건(`note_id="paper-a"`). (b) 창에 `retract` 있어 통과, (c)는 `(`가 뒤따라 일치 제외, (d)는 검사 대상 아님 |
| T-06 | R-02, R-01 | `hyperresearch lint --rule stale-indexes -j` | `data.issues=[]`, `summary` 전부 0, `count=0`, 종료 0 |
| T-07 | R-01, R-04 | 제목이 `Untitled`인 노트 하나. `lint --rule missing-title` 텍스트 모드 | `  missing-title <경로>: Note has no meaningful title.`와 `Summary: 0 errors, 1 warnings, 0 info`. 종료 0. error 이슈가 있어도 종료 0 |
| T-08 | R-16 | `loci.json`에 locus 3개(a, b, c), 노트는 태그 `locus-a`·type `interim` 하나뿐 | b·c 누락 2개 → error 1건(`2 of 3 loci have no interim note: b, c…`). a·b에 interim이 있고 c만 없으면 누락 1개 → warning |
| T-09 | R-17 | `loci.json` 없음, 출처 노트 7개, 설정 기본값. 실제 추출 노트 (a) 0개 (b) 1개 | 필요 `max(1,7//3)=2`, 하한 `max(1,7//4)=1`. (a) 0<1 → error, (b) 1<2이고 1≥1 → warning |
| T-10 | R-19 | `entities` 이름 3개가 보고서에 없음 / 2개만 없음. `required_formats`=`["mind map of causal structure"]`이고 보고서에 `mind map`이 없음 | 앞은 error, 뒤는 warning. 형식은 warning 별도 1건 |
| T-11 | R-20 | `citation_style="inline"`, 출처 노트 1개 이상. 보고서에 `[1]`은 있으나 `## Sources` 없음 | error 1건, 메시지에 `a Sources/References section heading` |
| T-12 | R-11, R-12 | `audit_findings.json`={`runs`:[{mode:`conformance`, criticals:[{id:`C1`, description:`scaffold extraction gap`, fixed_at:`2026-11-05`}]}]}이고 `scaffold-prompt`가 여전히 error를 냄. `lint --rule audit-gate` | `scaffold-prompt`가 추가로 돌아 그 error가 출력에 섞이고, `SELF-CERTIFICATION VIOLATION: CRITICAL [C1] …` error 1건이 마지막에 붙는다. 같은 파일에서 `fixed_at` 없는 critical이면 미해결 error만 나온다 |
| T-13 | R-14 | `query.md`가 있는 V8 런. 보고서 본문 어딘가에 문자열 `## Citation budget`이 들어 있음(줄 맨 앞이든 아니든) | `wrapper-report` error 1건(누출 목록에 `## Citation budget`). 부분 문자열 일치라 줄 중간이어도 잡힘 |
| T-14 | R-23, R-24, R-25 | 보고서 `First claim [01]. Second claim [0]. Wiki cite [[known-note]].\n\n## Sources\n[0] Rust. https://e.com/r\n[01] Async. https://e.com/a` (두 URL 모두 노트와 연결됨) | Sources가 `0`·`01` 번호를 갖기 때문에 두 표식이 인용으로 유지된다: 쌍 `("First claim [01].", [01]→Async 노트)`, `("Second claim [0].", [0]→Rust 노트)`, 그리고 위키링크 `[[known-note]]`(id가 실존하면 `note_id`) |
| T-15 | R-24 | 보고서 본문 `Claim [3].`이고 Sources 항목이 `[1]`뿐 | 쌍 `marker="[3]"`, `note_id=null`, `unresolved="no-sources-entry"`, `strong=true`(표식의 `3`). Sources 줄이 하나도 없으면 쌍 0 |
| T-16 | R-27 | 인용 노트 클레임 `claim`=`Revenue grew 12% in 2023.`. 문장 (a) `Revenue grew 12% in 2023. [[n]]` (b) `Revenue grew 12% in 2024 per the filing. [[n]]` | (a) 표식 제거·정규화 후 클레임과 완전 일치 → `supported-mechanical`. (b)는 수치가 있어 완전 일치 요구 → 불일치 → `needs-llm` |
| T-17 | R-27 | 수치 없는 문장 `The committee reviewed the proposal and approved the revised budget plan. [[n]]`, 노트 클레임에 `reviewed the proposal and approved the revised budget` 포함 | 문장의 6단어 연속 조각이 클레임 덩어리에 부분 문자열로 있어 `supported-mechanical`. 5단어 문장 `Short five word sentence here. [[n]]`은 조각이 없어 `needs-llm` |
| T-18 | R-28 | `needs-llm` 쌍 중 weak 4개(순서 1~4)와 strong 1개, `--sample-rate 0.5` | weak 중 2번째·4번째만 포함(`int(k*0.5)`가 올라가는 시점), strong은 항상 포함. 입력 순서 유지. `rate=0`이면 strong만, `rate=1`이면 전부 |
| T-19 | R-29, R-30 | `citecheck extract RUN1`을 보고서가 없는 상태로 / `--report /x.md`가 없는 파일 | `NO_REPORT`, 종료 1, 파일 안 만들어짐. `INVALID_TAG`는 `../x` 같은 태그에서 같은 방식 |
| T-20 | R-29 | 보고서에 쌍 5개: dangling 1, 기계 통과 2, needs-llm 2(둘 다 strong) | `summary={total:5, supported_mechanical:2, dangling:1, needs_llm:2}`, `sampled_for_llm` 2건, `dangling` 1건. 통과 쌍은 파일에 없음. CLI JSON `data.sampled_for_llm=2`, `data.dangling=1` |
| T-21 | R-15 | 출처 노트 6개, 이력(`*Suggested by [[x]]`) 하나도 없음. (a) `loci.json` 있음 (b) 없음 | 씨앗이 6개라 구조 검사 통과. (a) 비율 검사 생략으로 이슈 0. (b) 이력 0개·출처 6개(>5) → error(`ZERO … breadcrumbs`) |
| T-22 | R-10 | 보고서가 하나도 없는 볼트에서 `lint --rule quote-integrity` | `_latest_report`가 `(None, None)`이라 이슈 0, 종료 0 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
검증 수준은 1.4 표를 따른다. 근거 열의 `lint.py`는 `src/hyperresearch/cli/lint.py`다.

| R-ID / T-ID | 근거 (hyperresearch@aece65f) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-07 `lint.py:235-264`, `:1808-1835` | `typer.Exit`·`raise`가 `lint()` 안에 없음을 파일 전체에서 확인. 종료 코드 0은 정상 반환의 결과(실행 안 함) |
| R-02 | `lint.py:41`(선언), grep 결과 `stale-indexes`는 이 한 곳뿐; `:238` `fix` 인자는 본문에서 쓰이지 않음 | 파일 전체 grep. `duplicate-ids`가 도달 불가인 것은 `notes.id`가 PK(vault-store.md 1.3)인 데서 온 추론 |
| R-03 | C-02 | 코드 읽음. 다중 런에서의 불일치는 코드에서 도출 |
| R-04~R-06 | C-19 | SQL 조건 그대로 옮김 |
| R-07 | C-03, C-04, C-28, `src/hyperresearch/core/sync.py:62-113`(`_has_frontmatter`, `runs/` 건너뜀) | 보고서가 색인되지 않는다는 판단은 합성 스킬의 "No YAML frontmatter"(`skills/hyperresearch-11-synthesize.md:231,253`)와 `compute_sync_plan`의 frontmatter 프로브에서 도출. FTS 토크나이저는 vault-store.md(`porter unicode61`). README·CHANGELOG는 "verbatim"이라 쓰지만 구현은 토큰 열 일치(아래 차이 1) |
| R-08 | C-03, C-05 | 코드 읽음. 정규식 동작은 손으로 추적(실행 안 함) |
| R-09 | C-06, C-22 | 코드 읽음. 번호 인용 미검사는 함수가 `WIKI_LINK_RE`만 쓴다는 사실 |
| R-10 | C-07 `lint.py:1767-1778` | |
| R-11, R-12 | C-07, C-08. V8에서 `audit_findings.json`이 만들어지는 곳: `skills/hyperresearch-15-polish.md:115-125`, 읽는 쪽 모양 `lint.py:345-348` | 두 모양이 다르다(아래 차이 4) |
| R-13 | C-09 | frontmatter 제거 산술(`raw[end+5:]`)은 코드에서 도출(아래 차이 5) |
| R-14 | C-10, C-11 | |
| R-15 | C-12 | |
| R-16 | C-13 | 태그가 DB에서 소문자로 저장된다는 vault-store.md R-15와 locus 이름을 소문자화하지 않는 쿼리의 불일치는 추론(아래 차이 6) |
| R-17 | C-14 | 스킬·훅에 `extract` 태그 노트를 만들라는 지시가 없다는 grep 근거(아래 차이 3) |
| R-18 | C-15 | |
| R-19 | C-16 | |
| R-20 | C-17 | |
| R-21 | C-18 | 보고서가 노트가 아니라는 판단은 R-07과 같은 근거 |
| R-22 | `src/hyperresearch/core/runs.py:778-806` (run-manifest-gate.md C-13) | 시그니처·에러 처리 확인 |
| R-23~R-25 | C-20, C-22, C-24 | 테스트 `tests/test_core/test_verification.py`(`test_numbering_from_zero_or_zero_padded_still_cites`, `test_brackets_in_code_and_link_definitions_are_not_citations`, `test_marker_without_a_sources_entry_is_dangling_not_dropped`, `test_bracketed_numbers_without_a_sources_section_are_not_citations`)의 사례 이름이 코드 읽기와 일치함을 확인. 테스트 본문은 T-14·T-15에 필요한 부분만 열람 |
| R-26 | C-21, C-23 | 테스트 사례 이름(`test_title_match_beats_an_address_that_merely_holds_the_doi`, `test_doi_two_notes_hold_resolves_to_neither` 등)과 일치. 제목 조회에 `ORDER BY`가 없어 같은 제목 노트가 둘이면 어느 행인지는 SQLite 의존 |
| R-27 | C-25 | 테스트 `test_numeric_overlap_does_not_certify_different_claims`와 일치 |
| R-28 | C-26 | |
| R-29, R-30 | C-26, C-27 | |
| R-31 | C-29 | 소유 스펙의 R-23~R-25와 대조 |
| T-01~T-22 | 해당 R-ID의 코드 | 손으로 추적, 실행하지 않음. T-18의 `int(k*0.5)` 증가 시점은 산술(k=2,4) |

**문서와 구현의 차이** (구현을 사실로 썼다)
1. `quote-integrity`: README(`README.md:319`)와 CHANGELOG(`CHANGELOG.md:264`)는 "verbatim"이라 쓰고 `_check_quote_integrity` docstring은 "nearest fuzzy match를 알려 준다"고 쓴다. 구현은 FTS5 porter 토큰 구문 일치이고(대소문자·구두점·어형 무시) 가장 가까운 퍼지 일치는 계산하지 않는다(`lint.py:110-147`). 메시지에도 후보 노트가 없다.
2. `RULES`는 26개이지만 `stale-indexes`는 검사 코드가 없고 `duplicate-ids`는 `notes.id` PK 때문에 이슈를 낼 수 없다. 실질 규칙은 24개다.
3. `extract-coverage`(`README`는 단일 패스 런용 규율): V8의 스킬·훅 어디에도 `extract` 태그 노트를 만들라는 지시가 없다(`skills/`·`core/hooks.py` grep). `loci.json`을 만드는 full급 런에서는 건너뛰고, `loci.json`이 없는 light 런에서는 출처 노트가 1개 이상이면 실제 추출 0개로 error가 난다(추론: grep 근거).
4. `audit-gate`: 읽는 모양은 `{"runs":[{mode: conformance|comprehensiveness,…}]}`(`lint.py:345-348`)인데 V8 step 15.5가 `runs/<tag>/audit_findings.json`에 쓰는 것은 `{"mode":"hyperresearch-v8","run_id":…,"loci_count":…}`(`skills/hyperresearch-15-polish.md:115-125`)라 `runs` 키가 없다. 감사 에이전트(`hyperresearch-auditor`)는 설치 시 폐기 목록(`core/hooks.py:4207-4213`)에 있다. 그래서 `audit-gate`는 V8 산출물에서는 항상 이슈 0이다(코드 확인 + 판단).
5. `scaffold-prompt`: README(`README.md:325`)는 "스캐폴드가 사용자 프롬프트로 시작하지 않으면 막는다"고 하지만, V8 스캐폴드는 `runs/<tag>/scaffold.md` 파일이고 동기화는 `runs/` 아래를 노트로 색인하지 않으며(`sync.py:110`) 스킬이 태그 `scaffold` 노트를 만들라고도 하지 않아 규칙이 대상 0건이다(코드 확인 + grep). 또 `query.md` frontmatter 뒤에 빈 줄이 오는 스킬 형식(`skills/hyperresearch.md:129-139`)에서는 정본 문자열이 `\n`으로 시작하지만 추출 텍스트는 앞 빈 줄을 버리므로, 스캐폴드 노트가 있어도 동등 비교가 맞지 않는다(코드 산술, 실행 안 함). step 15.5도 이 규칙을 사전 검사로 부르지만 효과가 없다.
6. `patch-surgery`: 폴리시 스킬(`skills/hyperresearch-15-polish.md:140`)은 "step 11→최종 사이 draft churn이 안전 임계를 넘었다"고 설명하지만 코드는 건너뛴 critical과 빈 로그만 본다(`lint.py:1201-1296`). `locus-coverage`는 locus 이름을 그대로 `locus-<name>` 태그로 조회하는데 DB 태그는 소문자로 저장되므로(vault-store.md R-15) 대문자가 든 이름은 항상 누락으로 보일 수 있다(추론: 이름 규칙은 확인하지 못함).
7. 린트 규칙은 `run`·태그에 묶이지 않는다(R-03). 보고서·`loci.json` 등을 가장 최근 런에서 가져오므로 `verify_run`(`final_report_<tag>.md`)과 다른 런을 볼 수 있다.
8. 같은 이름의 개념이 둘이다: lint `wrapper-report`의 누출 검사는 제목 10개 + 계약 제목의 부분 문자열이고, `verify_run`의 `no-scaffold-leak`는 `## User Prompt (VERBATIM` 하나뿐이다. `run finish`는 전자를 부르지 않는다(step 15.5 사전 검사에서만 호출).
9. 스킬은 "numeric-consistency는 light 티어에서도 step 15 게이트가 기계적으로 덮는다"(`skills/hyperresearch-14-5-cite-check.md:15`)고 쓰지만 `verify_run`은 이 규칙을 부르지 않는다(`runs.py:778-806`). 구속력이 없는 warning이다.

### 2.2 코드 읽는 순서 [선택]
1. `lint.py:17-44` `RULES` → `:235-269` `lint()` 시작 → 규칙 블록을 `rules_to_run` 순서로. 단순 SQL 규칙(`:271-307`, `:1644-1765`)은 훑고, 보고서 의존 규칙은 `:98-232`(함수)와 `:1767-1778`(호출)을 같이 읽는다.
2. 복잡한 블록은 `audit-gate`(`:309-574`, 키워드 표 포함)와 `provenance`(`:827-1003`)다.
3. `citecheck.py`는 `extract_pairs`(`:178`) → `parse_sources_section`(`:140`) → `_doi_key` 계열(`:59-137`) → `triage_pairs`(`:257`) → `sample_needs_llm`·`write_pairs_file`(`:330-371`) 순. 마스킹은 `patterns.py:63-153`.
4. 호출 맥락은 `skills/hyperresearch-14-5-cite-check.md`(extract 호출·dangling 처리), `skills/hyperresearch-15-polish.md:127-143`(사전 검사), `skills/hyperresearch.md:262-284`(ship gate)이다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 없다. 이 스펙의 코드는 복사하지 않고 위치만 인용했다.

## 적용 메모 [선택]
없음. 원본 동작만 적었다.
