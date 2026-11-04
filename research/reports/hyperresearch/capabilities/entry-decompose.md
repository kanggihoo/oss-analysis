---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/skills/hyperresearch.md
  - src/hyperresearch/skills/hyperresearch-1-decompose.md
  - src/hyperresearch/skills/hyperresearch-1-5-chapter-partition.md
  - src/hyperresearch/cli/vault_tag.py
  - src/hyperresearch/cli/run_cmd.py
  - src/hyperresearch/cli/archive.py
  - src/hyperresearch/cli/main.py
  - src/hyperresearch/core/runs.py
  - src/hyperresearch/core/levers.py
  - src/hyperresearch/core/render.py
  - src/hyperresearch/core/profiles.py
  - src/hyperresearch/core/vault.py
  - src/hyperresearch/cli/lint.py
depends:
  - run-manifest-gate.md
status: draft
---

# 진입 스킬·분해·티어 라우팅

> 사용자 질문 하나를 받아 볼트·런 작업 공간을 준비하고(부트스트랩), 질문을 원자 항목·필수 섹션 제목·티어·응답 형식·레버로 분해해 `prompt-decomposition.json`에 적고, 그 티어에 맞는 단계 순서로 단계 스킬을 호출하게 하는 오케스트레이터 프롬프트와, dissertation 티어의 챕터 분할(step 1.5) 절차를 정의한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 사용자가 `/hyperresearch <질문>`(Codex는 `$hyperresearch`)을 호출한다. 호스트는 진입 스킬만 읽고 "나는 단계를 순서대로 부르는 라우터이고 질문에 직접 답하지 않는다"는 역할을 갖는다.
2. 부트스트랩: 볼트와 단계 파일이 없으면 설치·초기화 → 이전(3.0 이전) 평면 산출물 보관(`archive-run`) → 정본 질문 결정(`research/prompt.txt`가 있으면 그것, 아니면 사용자 문장) → `vault-tag <slug>`로 충돌 없는 태그 → `run init <tag> --profile <gear>` → `runs/<tag>/query.md` 저장 → 모달리티 분류 → `scaffold.md` 작성 → 단계별 할 일 목록 → step 1 호출.
3. step 1(분해): 정본 질문을 원자 항목으로 나누고, 필수 섹션 제목 배열·시간 범위·시간 기간·`pipeline_tier`·`response_format`·`citation_style`·`levers`를 정해 `prompt-decomposition.json`을 쓴다. 질문의 모든 명사구가 항목에 매핑됐는지 커버리지 매트릭스로 자체 점검해 `Gap? = YES`가 0이 될 때까지 고친다. `scaffold.md`에 티어 근거를 덧붙이고 `levers render`로 역할별 shim 4개를 만든다.
4. 호스트가 `prompt-decomposition.json`의 `pipeline_tier`를 읽고 티어 표에 따라 단계를 순서대로 호출한다: `light`는 1→2→10→15→16, `full`은 1~16 전부, `dissertation`은 1→1.5→[2~10을 챕터마다]→전역 6·11→12→…→16.
5. dissertation만: step 1.5가 원자 항목을 4~10개 챕터로 나눠 `chapter-plan.json`을 쓰고, 챕터마다 작업 공간을 만들고, `chapter-plan` 이벤트로 매니페스트에 등록한다. 이후 챕터 루프(동시 최대 2개)로 단계 2~10을 돈다.
6. 각 단계 스킬이 끝나면 호스트는 진입 스킬로 돌아와 다음 단계를 부른다. 서브에이전트를 띄울 때는 정본 질문 원문·파이프라인 위치·입력·shim을 프롬프트에 넣는 규약을 지킨다. 끝은 `run finish` 통과이고(행 9), 그 전에 답을 대화로 내놓는 것은 실패로 규정된다.

### 1.2 범위·통합 지점 [필수]
- 제공: 부트스트랩 절차, `vault-tag` CLI 계약, 분해 절차와 `prompt-decomposition.json`·`scaffold.md`·`query.md`·`temp/coverage-matrix.md`의 내용 규칙, 티어별 단계 순서와 티어 판정 규칙, step 1.5 챕터 분할과 챕터 실행 루프, 서브에이전트 spawn 규약, 복구 절차·불변식·네 가지 정본 규칙. 호스트 플랫폼(Claude Code / Codex)별 문구 차이.
- 제외(경계만):
  - 설치와 플랫폼 번역(행 1, `install-platforms.md`(범위 밖, 스펙 없음)): `install --steps-only`가 단계 스킬·에이전트·Stop 훅을 설치한다는 사실만 쓴다.
  - 프로필 값·`<< p.x >>` 렌더링·레버 shim 내용(행 2, `profiles-levers.md`(범위 밖, 스펙 없음)): 진입 스킬이 설치 시 렌더링된 텍스트라는 것과, `levers render`가 입력 `levers` 블록(허용값은 1.3)으로 shim 4개를 쓴다는 것만 쓴다.
  - 서브에이전트 로스터·프롬프트(행 3, [subagent-roster](subagent-roster.md)).
  - step 2~16의 절차(행 5~8: [width-sweep](width-sweep.md), [depth-analysis](depth-analysis.md), [draft-synthesis](draft-synthesis.md), [critique-patch-polish](critique-patch-polish.md)): 이 스펙은 단계 이름·티어·호출 순서와 분해 산출물을 그 단계가 읽는다는 사실만 쓴다.
  - 런 매니페스트·재개·예산·ship gate(행 9, `run-manifest-gate.md`): `run init`/`step`/`resume`/`finish`의 동작은 거기 있다. 여기서는 부르는 시점과 인자만 쓴다.
  - 에스컬레이션 큐·브라우저 레인(행 18), `archive-run` 본체(행 19, 경계만 1.3).
- 외부 의존·선행 계약:
  - `run-manifest-gate.md`: `run init`(멱등, `runs/<tag>/`·`temp/`·`run.json` 생성), `run step`·`run event`·`run resume`·`run finish`, 산출물 이름표(S1).
  - 호스트 에이전트: 스킬 호출 도구(`Skill` 또는 단계 파일 읽기), 서브에이전트 spawn, Bash, 할 일 도구(`TodoWrite`/`update_plan`). 호스트가 프롬프트를 실제로 따르는지는 코드로 강제되지 않는다.
  - 볼트: `Vault.discover()`가 작업 디렉터리에서 위로 올라가며 `.hyperresearch/`를 찾는다. 없으면 `vault-tag`·`run *`가 `NO_VAULT`로 실패한다.
- 소유 상태·부작용: `runs/<tag>/query.md`, `scaffold.md`, `prompt-decomposition.json`, `temp/coverage-matrix.md`, `shims/`(`levers render`가 씀), `chapter-plan.json`, `chapters/<id>/temp/`, 매니페스트의 `chapters`(`chapter-plan` 이벤트로). 볼트·`research/` 초기화는 부트스트랩 0의 CLI가 한다.

### 1.3 인터페이스와 데이터 의미 [필수]

**A. 부트스트랩에서 호스트가 부르는 명령**

| 순서 | 명령 | 조건·인자 | 결과 사용 |
|---|---|---|---|
| 0 | `hyperresearch init . --json` | 작업 디렉터리 직속에 `.hyperresearch/`가 없을 때 | `.hyperresearch/`, `research/{notes,index,temp}`, SQLite, 에이전트 문서 블록 생성. 이미 있으면 `VAULT_EXISTS` 오류이므로 조건부로만 부른다 |
| 0 | Claude: `hyperresearch install --steps-only . --json` / Codex: `hyperresearch install --steps-only . --target codex --json` | Claude는 `.claude/skills/hyperresearch-1-decompose/SKILL.md`, Codex는 `.hyperresearch/codex/steps/hyperresearch-1-decompose.md`가 없을 때 | 16개(실제 로스터 18개) 단계 스킬/파일 설치. Codex는 커스텀 에이전트와 `.codex/hooks.json` Stop 훅도 설치. 바이너리가 없으면 사용자에게 `pip install hyperresearch`를 안내. 둘 다 있으면 no-op이라 무조건 실행해도 안전 |
| 0.5 | `hyperresearch archive-run --json` | 항상 | `research/` 루트의 3.0 이전 평면 산출물(`scaffold.md`, `loci.json` 등 18개 이름)과 비어 있지 않은 `research/temp/`를 `research/runs/archive-<이전태그>-<UTC타임스탬프>/`로 이동. 옮길 게 없으면 no-op |
| 2 | `hyperresearch vault-tag <slug> --json` | 질문에서 만든 슬러그 | `data.vault_tag` 파싱 |
| 2.5 | `hyperresearch run init <tag> --profile <full\|light\|premier\|dissertation> [--budget <usd>] --json` | 기본은 설치된 gear 이름(`<< p.name >>`), 사용자가 상한을 말했을 때만 `--budget` | `research/runs/<tag>/`, `temp/`, `run.json`(행 9) |
| 1단계 끝 | `hyperresearch levers render <tag> -j` | `prompt-decomposition.json` 작성 후 | `shims/{research,drafting,critics,polish}.md`와 매니페스트 `levers`·`levers` 이벤트. 열거형 위반이면 `LEVER_ERROR`로 종료 1 |

진입 스킬은 `run init`에 `--query-file`·`--max-sources`·`--max-notes`를 쓰지 않는다. `query.md`는 호스트가 직접 쓴다.

**B. `vault-tag` CLI** — `hyperresearch vault-tag <slug> [--json]`

| 항목 | 규칙 |
|---|---|
| 슬러그 형식 | `^[a-z0-9][a-z0-9-]{0,59}$`(소문자 영숫자로 시작, 영숫자·`-`, 최대 60자). 위반 시 `INVALID_SLUG`, 종료 1 |
| 볼트 | 없으면 `NO_VAULT`, 종료 1 |
| 사용 중 태그 집합 | `research/query-*.md`의 `<tag>`(구 레이아웃), `research/notes/final_report_*.md`의 `<tag>`, `research/runs/` 아래 모든 디렉터리 이름(`archive-`로 시작하는 것 제외) |
| 생성 | `<slug>-<6hex>`(`secrets.token_hex(3)`)을 만들어 사용 중 집합에 없으면 반환. 최대 100번 시도, 모두 충돌하면 `TAG_SPACE_EXHAUSTED`, 종료 1 |
| 출력 | JSON: `{"vault_tag", "slug", "suffix"}`(봉투 `data`), 텍스트: 태그 한 줄. 디렉터리를 만들거나 예약하지 않는다 |
| 호스트 쪽 슬러그 | 정본 질문에서 3~5개 소문자 하이픈 단어(예 `efield-dft-sac`). 결과 `efield-dft-sac-a3f9b7`가 `vault_tag` |

**C. 문서 형식**

| 파일 | 형식 |
|---|---|
| `query.md` | YAML 프론트매터(`vault_tag: <slug>`, `created: <ISO-8601>`, `source: prompt.txt \| user-prompt`) + 빈 줄 + 정본 질문 원문(글자 그대로). 모든 단계·서브에이전트가 이 경로로 질문을 읽는다 |
| `scaffold.md` | 호스트 개인 계획 문서(최종 보고서에 절대 나오면 안 됨). 내용: "User Prompt (VERBATIM — gospel)", Run config(`vault_tag`, `query_file_path`, `modality`, 래퍼 요구), 모달리티 근거, "Tier rationale"(step 1이 2~3문장으로 덧붙임), 래퍼 요구(저장 경로·인용 형식·말미 섹션). 정확한 마크다운 구조는 정해져 있지 않다 |
| `temp/coverage-matrix.md` | `## Coverage Matrix — query phrase → atomic item mapping` + 표 열 `Query phrase (verbatim) \| Mapped atomic item(s) \| Scope check \| Gap?`. `Gap?`은 `No` 또는 `**YES**` |

**D. `prompt-decomposition.json`** (step 1 출력, S1) — 생산 규칙은 1.4, 소비처는 이 표.

| 필드 | 타입 | 값·의미 | 읽는 곳 |
|---|---|---|---|
| `sub_questions` | list of string | 명시·암시된 질문(원자 항목) | step 2·여러 단계, instruction critic |
| `entities` | list of {`name`, `type`, `required_fields`: list of string} | 이름이 붙은 개체·범주 | step 2, instruction critic, lint `instruction-coverage` |
| `required_formats` | list of string | 표·마인드맵·FAQ 등 요구 형식 | instruction critic, lint |
| `required_sections` | list of string | 프롬프트가 요구한 섹션("끝에 Y") | instruction critic |
| `required_section_headings` | list of string | 보고서가 **순서대로** 내야 하는 H2 제목 리터럴(`"## 1. ..."` 꼴). 비우지 않는다 | step 10·11(제목 계약), instruction critic, `run finish`의 `required-headings`(행 9) |
| `time_horizons` | list of string | 미래 지향 범위("2027까지", "12-month forward") | step 2 |
| `time_periods` | list of {`period`, `type`, `primary_source`, `issuer`} | 과거의 특정 보고 기간. 예 `type`: `fiscal-quarter`, `fiscal-year`, `event-anchored`. 비어 있지 않으면 step 2 렌즈 D(기간 고정 1차 문서 검색)가 필수이고 step 8이 1차 문서 커버리지를 점검 | step 2, 8 |
| `scope_conditions` | list of string | 범위 조건("도시철도 한정") | step 2 |
| `pipeline_tier` | `"light"` \| `"full"` | 기본 `full`. step 1은 `dissertation`을 내지 않는다 | 호스트(티어 표), 행 9의 재개·게이트 |
| `response_format` | `"short"` \| `"structured"` \| `"argumentative"` | 보고서 모양 | step 9~11, `run finish`의 `length-in-range` |
| `citation_style` | `"wikilink"`(기본) \| `"inline"` \| `"none"` | 인용 표기 | step 10·11·15, lint |
| `levers` | {`register`, `register_confidence`, `domain_notes`, `inference_depth`, `rationale`: {`register`, `inference_depth`}} | 1.4 R-22. 검증은 `levers render`가 한다: `register ∈ {teach,survey,analyze,advocate}`, `inference_depth ∈ {surface,standard,deep}`, `domain_notes`는 문자열(없으면 기본값 `analyze`/`standard`/`""`). `register_confidence`·`rationale`은 검증도 소비도 하지 않는다 | `levers render`, `run finish`(`levers-rendered`) |

**E. 티어와 단계 순서** (진입 스킬 표를 그대로 옮김)

| 티어 | 실행되는 단계 | 비고 |
|---|---|---|
| `light` | 1 → 2 → 10(단일 초안) → 15 → 16 | step 1이 자동 분류. 프로필 `light`의 `steps`와 같음 |
| `full` | 1 → 2 → 3 → … → 13 → 14 → 14.5 → 15 → 16 (전부) | 기본값 |
| `dissertation` | 1 → 1.5 → [2 → … → 10 챕터마다] → 6(전역)·11 → 12 → 13 → 14 → 14.5 → 15 → 16 | 사용자가 명시적으로 요청했거나 `--profile dissertation`일 때만. 실험적(#103) |

단계 이름: 1 `hyperresearch-1-decompose`, 1.5 `-1-5-chapter-partition`, 2 `-2-width-sweep`, 3 `-3-contradiction-graph`, 4 `-4-loci-analysis`, 5 `-5-depth-investigation`, 6 `-6-cross-locus-reconcile`, 7 `-7-source-tensions`, 8 `-8-corpus-critic`, 9 `-9-evidence-digest`, 10 `-10-triple-draft`, 11 `-11-synthesize`, 12 `-12-critics`, 13 `-13-gap-fetch`, 14 `-14-patcher`, 14.5 `-14-5-cite-check`, 15 `-15-polish`, 16 `-16-readability-audit`(모두 `hyperresearch-` 접두). 1.5는 dissertation 전용, 3~9·11~14.5는 full 이상, 1·2·10·15·16은 전 티어.

**F. gear와 tier**: tier(`light`/`full`/`dissertation`)는 쿼리별 단계 집합이고, gear는 설치된 프로필(`full`/`premier`)이 단계 스킬에 렌더링해 넣는 수치(소스 목표·loci 상한·깊이 예산·단어 목표)다. gear 전환(`hyperresearch profile use <full|premier>`)은 스킬을 다시 렌더링하므로 **다음 런**부터 적용된다. `light`와 `dissertation`은 gear가 아니라 tier다.

**G. 챕터 계획 `chapter-plan.json`** (dissertation)

```text
{"chapters": [{"id": string, "title": string, "atomic_items": list of string(분해 항목 원문),
               "rationale": string(1~2문장), "depends_on": list of 챕터 id}]}
```

챕터 작업 공간 `runs/<tag>/chapters/<id>/`에 빈 `temp/`. 챕터 범위 산출물(`loci.json`, `comparisons.md`, 클레임, 초안 `draft.md`)은 여기에 두고, 챕터 실행 중 런 루트의 평면 사본은 쓰지 않는다. 챕터 노트는 태그 두 개를 모두 단다: `<vault_tag>`와 `<vault_tag>-<id>`.

**H. 플랫폼별 차이** (진입 스킬의 `<% if platform == "codex" %>` 분기)

| 항목 | Claude Code | Codex |
|---|---|---|
| 단계 호출 | `Skill(skill: "hyperresearch-N-name")` | `.hyperresearch/codex/steps/hyperresearch-N-name.md`를 끝까지(잘리면 페이징) 읽고 따른다 |
| 할 일 | `TodoWrite`(정수 단계 번호, 압축을 견딤) | `update_plan` |
| 종료 규칙 1 | 서브에이전트가 도는 동안 도구 호출 없는 텍스트 응답 금지(`-p` 모드에서 프로세스 종료). 대신 `temp/orchestrator-notes.md`에 추가 | 파이프라인 중간에 턴을 끝내지 말 것. `codex exec`에서는 도구 호출 없는 메시지가 프로세스를 끝낸다. Stop 훅이 실행 중 런이면 되돌려 보냄 |
| 규칙 2(패치) | step 14·15 서브에이전트는 `[Read, Edit]`로 잠김 | 읽고 패치만(`apply_patch`) 적용 |
| spawn | 단계 스킬이 "spawn하라"고 하면 지시 | "그 문장이 명시적 spawn 지시다. 이름 붙은 모든 에이전트를 병렬로 띄우고 기다린다. 서브에이전트 일을 인라인으로 하지 않는다" |
| 브라우저 레인 | step 2.8이 `hyperresearch-browser-fetcher` 하나로 큐를 비움. 비대화형이면 `run block <tag> --on human-challenges` 후 계속 | 브라우저 레인 없음. 큐를 비우려 기다리지 않고 마지막 메시지에 남은 항목(URL+이유)을 한 번에 사용자에게 전달 |
| 복구 시 재진입 | `Skill(skill: "hyperresearch")` | `cat .agents/skills/hyperresearch/SKILL.md` |
| 부트스트랩 점검 파일 | `.claude/skills/hyperresearch-1-decompose/SKILL.md` | `.hyperresearch/codex/steps/hyperresearch-1-decompose.md`(+ Stop 훅 설치, `.codex/hooks.json`이 쓰기 불가면 권한 상승으로 한 번 재실행, 거부되면 훅 없이 진행) |
| 불변식 11 | synthesizer는 Read+Write 도구 잠금 | synthesizer는 입력을 읽고 파일만 쓴다 |

**I. 진입 스킬 불변식 15개** (플랫폼 공통 문구 요약)

| # | 불변식 |
|---|---|
| 1 | step 11(light는 step 10)이 최종 보고서를 만든 뒤에는 수술적 패치만(재생성 금지) |
| 2 | 최종 보고서는 한 번만 쓴다. 예외: ship gate의 `length-in-range` 압축 1회(자기 출력만 입력으로) |
| 3 | step 4는 변증적(dialectical) locus를 최소 1개 내야 한다(정당한 생략 제외) |
| 4 | step 5의 모든 interim 노트는 `## Committed position`으로 끝난다 |
| 5 | loci가 1개 이상이면 `comparisons.md`가 존재해야 한다(step 6 필수) |
| 6 | 단계는 바깥에서 순차, 안에서 병렬. 단계 N이 끝나기 전에 N+1을 시작하지 않는다 |
| 7 | 정본 질문은 모든 곳에서 gospel. 모든 서브에이전트가 원문을 받는다 |
| 8 | 위생 규칙은 최종 보고서에만 적용(작업 공간 산출물은 자유) |
| 9 | 티어가 돌리라는 단계는 건너뛰지 않는다(full 16단계, light 5단계) |
| 10 | full 티어의 step 10은 `hyperresearch-draft-orchestrator` 3개를 반드시 띄운다. step 10에서 `final_report_<tag>.md`를 직접 쓰면 위반 |
| 11 | full 티어의 step 11은 synthesizer가 3개 초안으로 최종 보고서를 쓴다. 오케스트레이터가 직접 쓰지 않는다 |
| 12 | 서브에이전트는 전문을 읽는다: 초안 오케스트레이터는 `must_read_note_ids`를 일괄 읽고, fetcher는 인용 사슬로 1차 소스 3~8개를 추적 |
| 13 | Claude: 서브에이전트가 도는 동안 도구 호출 없는 텍스트 응답 금지. Codex: 파이프라인 중 턴 종료 금지·질문을 대화로 답하지 않음 |
| 14 | 런은 `run finish`가 `passed: true`를 보고할 때만 완료. 실패는 보고서를 고쳐 해결하고 3라운드 뒤에도 실패면 `blocked`로 두고 정직하게 보고 |
| 15 | shim 파일은 그대로 붙여 넣는다. 오케스트레이터는 shim 텍스트를 쓰거나 요약·생략하지 않고, cite-checker에는 주지 않는다 |

### 1.4 행동 규칙과 남은 질문 [필수]

모든 R-ID의 "검증 수준 코드 확인"은 프롬프트 본문(스킬 마크다운)이나 CLI 구현을 직접 읽었다는 뜻이다. 프롬프트 규칙은 호스트 LLM이 따르는지를 코드가 강제하지 않는다(1.4 끝 확인 한계).

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 호스트가 진입 스킬을 읽음 | 역할은 라우팅뿐이다: 진입 스킬 읽기 → 부트스트랩 → 단계를 순서대로 호출 → 단계 사이에는 할 일 갱신과(선택) `temp/orchestrator-notes.md` 기록만. 단계의 일을 직접 하지 않고, 질문에 대화로 답하지 않는다(답하면 실패) | 코드 확인 |
| R-02 | 부트스트랩 0: 볼트·단계 파일 점검 | 1.3 A 표의 조건·명령. 점검은 작업 디렉터리 직속만 본다. 바이너리가 PATH에 없어 실패하면 사용자에게 `pip install hyperresearch`를 안내. 둘 다 있으면 무조건 실행해도 no-op | 코드 확인 |
| R-03 | 부트스트랩 0.5 | `archive-run`을 항상 부른다. 3.0 이후 볼트는 런마다 `runs/<tag>/`를 가지므로 보통 no-op. 동작은 1.3 A. 이동 대상에 `research/temp/`가 포함된다 | 코드 확인 |
| R-04 | 부트스트랩 1: 정본 질문 | 우선순위: (1) `research/prompt.txt`가 있으면 그 내용(gospel, 래퍼 실행) (2) 없으면 사용자의 verbatim 프롬프트. 래퍼 요구(저장 경로·인용 형식·말미 섹션·래퍼 계약)는 질문과 분리해 따로 추출하며 구속력이 있으나 질문의 일부가 아니다. `research/wrapper_contract.json`이 있으면 읽는다 | 코드 확인 |
| R-05 | 부트스트랩 2: 태그 | 슬러그를 만들어 `vault-tag`를 부르고 `vault_tag` 필드를 그대로 쓴다. CLI 계약은 1.3 B. 태그는 이후 `runs/<tag>/`, `final_report_<tag>.md`, 노트 태그의 키다 | 코드 확인 |
| R-06 | 부트스트랩 2.5: 런 초기화 | `run init <tag> --profile <p> [--budget]`. 표준 런은 설치된 gear 이름을 쓰고 사용자가 다른 것을 원하면 그것을 쓴다. 이후 매니페스트가 "내구성 있는 기억"이고 모든 단계 전이를 `run step <tag> <N> --status running|done -j`로 기록하라고 지시한다. 매니페스트 `profile`은 정보용이고 분해의 티어가 규칙을 정한다 | 코드 확인 |
| R-07 | 부트스트랩 3: `query.md` | 1.3 C 형식으로 정본 질문을 글자 그대로 저장한다(프론트매터 포함). `source`는 `prompt.txt`를 썼으면 `prompt.txt`, 아니면 `user-prompt` | 코드 확인 |
| R-08 | 부트스트랩 4: 모달리티 | `collect`(개체별 섹션·이름 붙은 필드를 열거) / `synthesize`(주장+증거 사슬) / `compare`(개체별 비례 깊이 + 추천) / `forecast`(과거·현재 근거의 예측, 명시적 시간 범위) 중 하나를 골라 scaffold에 기록한다. step 10의 초안 문체를 보정하는 라벨이다 | 코드 확인 |
| R-09 | 부트스트랩 5: `scaffold.md` | 1.3 C 내용 항목을 쓴다. 최종 보고서에 나오면 안 된다(행 9가 `## User Prompt (VERBATIM` 헤더를 검사) | 코드 확인 |
| R-10 | 부트스트랩 6~7 | 단계 호출마다 하나씩 정수 번호(1~16)로 할 일/계획 항목을 만든다(압축을 견디는 위치 기억). 그다음 step 1을 호출한다. step 1이 돌아오면 `prompt-decomposition.json`을 읽어 티어를 안 뒤 티어 표대로 계속하고, 단계의 종료 조건을 만족하면 항목을 완료 처리한다 | 코드 확인 |
| R-11 | 티어 판정 읽기·준수 | step 1 뒤 호스트가 `pipeline_tier`를 읽고 1.3 E 표의 단계만 순서대로 호출한다. `light`일 때 생략된 단계를 "철저함을 위해" 돌리지 않는다. 불확실하면 티어를 올리되 모든 쿼리를 조용히 `full`로 올리지 않는다. 티어는 구속력 있는 계약이다: 돌리라는 단계를 건너뛰지 않고, 안 돌려도 되는 단계를 더하지 않는다 | 코드 확인 |
| R-12 | 단계 순서 | 바깥에서는 순차(N이 끝나야 N+1)이고 단계 안에서 서브에이전트가 여럿이면 병렬이 필수다. 라우터 표의 단계별 한 줄 설명은 1.3 E 아래 이름 목록과 같다. light의 단계 10은 단일 초안, full은 draft-orchestrator 3개 | 코드 확인 |
| R-13 | `dissertation` 선택 | 사용자가 명시적으로 요청했거나 런을 `--profile dissertation`으로 초기화한 경우만. step 1은 자동 분류하지 않는다. 시작 전에 사용자에게 "실험적이며 길이·읽기 예산·인용 목표는 설정돼 있으나 읽는 곳이 없다(#103)"고 알린다. 챕터 수·동시성·챕터당 소스·총 소스는 프로필 값(행 2)으로 렌더링된다 | 코드 확인 |
| R-14 | 티어·프로필의 코드 쪽 효과 | 코드는 `pipeline_tier`를 읽어 `run resume`·Stop 훅·`run finish`의 필수 단계 집합을 바꾼다(`run-manifest-gate.md` R-18, R-19, R-25). 선언된 티어가 이름이 해석되는 프로필이어야 한다. 이 스펙의 단계 표와 프로필 `light`의 `steps`(1,2,10,15,16)가 일치한다 | 코드 확인 |
| R-15 | step 1 입력 | `scaffold.md`와 `query.md`를 읽고 정본 질문을 끝까지 다시 읽는다. `vault_tag`는 scaffold의 Run config에 있다 | 코드 확인 |
| R-16 | 원자 항목 추출 | 질문이 이름 붙인 모든 이산 항목을 뽑는다. 범주: 하위 질문, 이름 붙은 개체·범주, 요구 형식, 요구 섹션, 시간 범위(미래 지향), 시간 기간(과거의 보고 기간·`primary_source`를 가진 것, "Q3 2024", "FY 2023", "as of ..."), 범위 조건. 시간 기간 누락은 "주제는 맞는데 정확한 수치를 놓치는" 최대 원인으로 명시돼 있다. 프롬프트가 명시한 것은 하나도 빼지 않고 중복처럼 보여도 별도 항목으로 둔다(오탐은 비평가가 싸게 잡고 미탐은 못 잡는다). 래퍼 요구는 분해에 넣지 않는다 | 코드 확인 |
| R-17 | `required_section_headings` | 절대 비우지 않는다. 채우는 규칙: (a) 번호 매긴 요구(`\b\d[.\)]`, "List X, Y, Z", "cover the following:")가 있으면 항목마다 하나, 프롬프트 순서, 프롬프트의 명사구를 제목에 쓴다. (b) 개체 N개를 열거하고 각각을 논의·분석·서술·평가하라고 하면 개체마다 하나. (c) 서술형이면 추출한 하위 질문마다 H2 하나를 선언문 형태(`"## 1. Historical Context and Evolution"`)로. 열린 프롬프트("Write about X")는 주제의 자연스러운 분석 구조에서 4~7개(배경 → 핵심 분석 1~3개 → 비교 → 함의·전망), 모든 하위 질문을 덮어야 한다 | 코드 확인 |
| R-18 | `prompt-decomposition.json` 작성 | 1.3 D의 필드로 `runs/<tag>/prompt-decomposition.json`을 쓴다(유효 JSON, 모든 원자 항목이 정본 질문으로 추적 가능). 필수로 채울 것: `pipeline_tier`, `response_format`, `citation_style`, `levers`(register·domain_notes·inference_depth 포함), 비어 있지 않은 `required_section_headings` | 코드 확인 |
| R-19 | `pipeline_tier` 분류 | `light`: 명확하고 한정된 답(사실 조회, 정의, 단순 설명, 짧은 how-to, 목록·카탈로그, 빠른 비교, 지형 개요, 다개체 조사; 신호 "What is...", "How do I...", "List the...", "Define...", "Overview of...", "Compare X and Y", 짧거나 중간 길이, 질문 하나 또는 하위 질문 2~5개). `full`: 깊은 분석, 상충 증거 종합, 방어되는 논지, 문헌 리뷰, 증거 사슬 예측(신호 "Analyze the impact of...", "Evaluate whether...", 여러 문단, 깊이·엄밀성 요구, 연구급·논쟁적 주제). 기본값 `full`, 애매하면 올린다("단순 질문에 full은 비용 낭비, 복잡한 질문에 light는 나쁜 보고서") | 코드 확인 |
| R-20 | `response_format` 분류 | `short`: 직접 답(500~2000단어, 1~5문단, Opinionated Synthesis 없음, 논지 먼저). `structured`: 개체·주제 전반 커버(2000~5000단어, 스캔 가능한 소절, 폭 우선, 표·불릿). `argumentative`: 방어되는 논지·깊은 분석(5000~10000단어, 밀도 높은 산문, "ARGUE, DON'T JUST REPORT" 전력, Opinionated Synthesis 필수). 두 축은 독립이다. 흔한 짝: light+short(사실 조회), light+structured(목록·개요), full+argumentative(깊은 분석·문헌 리뷰·예측, 기본), full+structured(포괄적 서베이). 위 단어 수는 gear 값이며 렌더링 값은 프로필을 따른다 | 코드 확인 |
| R-21 | `citation_style` | `wikilink`(기본): 본문에 `[[note-id]]`, 별도 Sources 섹션 없음. `inline`: `[N]`(한 지점이 여러 소스면 `[7, 12]`)과 말미 `## Sources`. `none`: 표식도 Sources도 없음. `research/wrapper_contract.json`에 `citation_style`이 있으면 그것이 기본값을 덮어쓴다(벤치마크 하니스는 `inline`을 씀) | 코드 확인 |
| R-22 | `levers` 선택 | `register`: 질문의 동사 형태로 분류 — `teach`("explain", "how does X work", "walk me through"), `survey`("overview of", "landscape", "compile", "what are the main X", 판정 요구 없음), `analyze`("evaluate", "assess", "which is most effective", "feasibility of"; 기본), `advocate`("should we", "argue for/against", "make the case", "recommend"). `register_confidence`(기록 전용 필드): `analyze`에서 벗어나는 것은 신호가 강할 때(`high`)만, 애매하거나 혼합이면 `analyze`+`low`. 우선순위: 사용자의 명시 지시("make it a survey", "mode=teach")가 항상 이기고, 그다음 `wrapper_contract.json`의 `levers`, 마지막이 분류. `domain_notes`: 2~3문장(소싱 전략·증거 규범·중요한 최신성 범위), 항상 쓰며 하류 에이전트가 그대로 읽는다. `inference_depth`: `surface`(한정된 질문·권위 있는 합의로 충분), `standard`(기본), `deep`(답이 열린 웹 밖에 있을 가능성: 회색 문헌·공시·부재 추론). step 4가 코퍼스에 비춰 재평가해 올릴 수 있는 잠정값이다 | 코드 확인 |
| R-23 | 커버리지 매트릭스 | 정본 질문을 구절 단위로 훑어 모든 의미 있는 명사구·고유명사·전문 용어·범주명을 뽑고, 각각이 (a) 적어도 하나의 원자 항목에 매핑되는지 (b) 해석이 구절의 자연스러운 범위만큼 넓은지(예 "SaaS applications"를 "POS SaaS"로 좁히면 안 됨, "rugged tablets"를 "payment terminals"로 접으면 안 됨) (c) 지시 대상이 여럿이면 둘 다 덮는지 확인한다. 1.3 C 형식으로 `temp/coverage-matrix.md`를 쓰고, `Gap? = YES`가 하나라도 있으면 분해에서 빠진 항목을 더하거나 좁혀진 범위를 넓히고 모든 행이 통과할 때까지 매트릭스를 다시 만든다. 알려진 간극을 두고 진행하지 않는다 | 코드 확인 |
| R-24 | 티어 근거 기록 | step 1이 `scaffold.md`에 "Tier rationale" 소절(2~3문장)을 덧붙인다 | 코드 확인 |
| R-25 | 레버 렌더링 | step 1의 마지막에 `levers render <tag> -j`를 실행한다. 열거형 값 오류면 `levers` 블록을 고쳐 다시 실행한다. 이후 단계는 shim을 서브에이전트 프롬프트에 그대로 붙인다(오케스트레이터가 shim을 쓰거나 고치지 않는다). shim 디렉터리가 없으면 spawn 전에 `levers render`를 실행한다 | 코드 확인 |
| R-26 | step 1 종료 조건과 다음 단계 | 종료: 분해 JSON 존재·유효, `pipeline_tier`·`response_format`·`citation_style`·`levers` 설정, shim 4개 존재, 커버리지 매트릭스에 `Gap? = YES` 없음, scaffold에 Tier rationale. 그다음 진입 스킬로 돌아가 티어를 읽고 step 2를 호출한다(step 2는 전 티어 공통) | 코드 확인 |
| R-27 | step 1.5 적용 | 프로필 `chapters` 범위가 0이 아닐 때(`dissertation` = 4~10)만 실행한다. `light`·`full`에는 이 단계가 없고 step 2로 간다. 프로필 게이트는 프롬프트가 지시하며 코드가 강제하지 않는다 | 코드 확인 |
| R-28 | 챕터 수·배치 | 분해의 원자 항목을 주제적으로 응집한 챕터로 묶는다. 모든 항목은 정확히 한 챕터에 들어간다(교차 항목은 가장 깊이 다룰 챕터에, 다른 챕터는 참조만). 챕터는 `chapter_source_target`(기본 40~80) 소스로 답할 수 있어야 하고 아니면 쪼갠다. `required_section_headings`가 이미 챕터 구조를 함의하면(프롬프트가 이름 붙은 부분을 요구) 그것을 따라 챕터가 최상위 제목과 1:1로 대응한다. 원자 항목이 약 12개 미만이면 챕터화가 필요 없어 챕터 1개로 기록하고 평면 `full` 모양으로 퇴화한다(프로필 범위 아래 탈출구) | 코드 확인 |
| R-29 | 챕터 계획·작업 공간·등록 | 1.3 G 형식으로 `chapter-plan.json`을 쓴다. 챕터마다 `chapters/<id>/temp/`를 만든다. 챕터마다 `run event <tag> --type chapter-plan --data '{"chapter": "<id>", "title": "<title>"}' -j`를 보내(매니페스트 `chapters`에 `planned`로 접힘, 행 9 R-07) 이어서 `run step <tag> 1.5 --status done -j`를 기록한다. 이동 전에 `run resume <tag> -j`가 모든 챕터 id를 `chapters_pending`에 나열하는지 확인한다(비어 있으면 등록이 안 된 것) | 코드 확인 |
| R-30 | 챕터 태그 | 챕터를 위해 가져오거나 쓴 모든 노트는 `<vault_tag>`와 `<vault_tag>-<id>`를 모두 단다. 전체 질의는 앞의 것, 챕터 질의는 뒤의 것을 쓴다. 챕터 간 소스 재사용은 URL 기준으로 중복이 제거되므로 공짜이고, 챕터의 커버리지 점검은 가져오기 전에 `<vault_tag>` 전체 코퍼스를 먼저 검색한다 | 코드 확인 |
| R-31 | 챕터 실행 루프 | 챕터마다(`depends_on` 존중, 동시 진행 최대 `chapter_concurrency`=2) 단계 2→10을 챕터 범위로 돈다: 챕터 범위 spawn의 질문은 정본 질문 원문 + 챕터 제목·원자 항목을 적은 배정 블록, 산출물 경로는 `runs/<tag>/`를 `runs/<tag>/chapters/<id>/`로 바꿔 챕터별 `loci.json`·`comparisons.md`·`temp/`를 쓰고, 소스 목표는 전역 `source_target`이 아닌 `chapter_source_target`, step 10은 챕터당 초안 하나(`chapters/<id>/draft.md`, `draft_count`=1)를 쓴다. 챕터-단계가 끝날 때마다 `run step <tag> <N> --status done --chapter <id> -j`. 모든 챕터가 step 10을 마친 뒤 전역 층: step 6을 전역으로 다시(챕터들의 `comparisons.md`의 챕터 간 긴장 → 런 루트 `comparisons.md`), 이어 step 11이 챕터 초안을 최종 문서로 종합(챕터 제목이 H1), 그다음 12~16은 문서 전체에 대해 한 번 | 코드 확인 |
| R-32 | 챕터 경계의 예산 점검 | 챕터 경계마다 `run status <tag> -j`. `status`가 `blocked`이고 `blocked_on: "budget"`이면 spawn을 멈추고 사용자에게 알린다. 프로필이 요구한 단계를 조용히 건너뛰지 않으며, `budget_remaining_usd`가 약 30% 미만이면 다음 챕터의 fan-out(wave-2 fetcher 수, 깊이 예산)을 줄인다 | 코드 확인 |
| R-33 | 서브에이전트 spawn 규약 | 모든 spawn 프롬프트는 상단 근처에 다음을 포함한다(스킬 본문은 "세 가지"라 하나 목록은 네 가지): (1) `research_query`를 `runs/<tag>/query.md`에서 verbatim 블록 인용(바꿔 쓰거나 요약 금지) (2) 파이프라인 위치 진술 한 문장(어느 단계인지, 앞에 무엇이 있었는지, 뒤에 무엇이 오는지) (3) 그 서브에이전트의 고유 입력(`vault_tag`, `output_path`, locus 등; 단계 스킬의 spawn 템플릿이 필수 필드를 적는다) (4) 해당 역할의 shim 파일 전문을 spawn 프롬프트 끝에 수정 없이 붙임(단계 스킬이 어느 shim인지 정한다). cite-checker는 shim을 받지 않는다. 하나라도 빠지면 프로세스 위반이다 | 코드 확인 |
| R-34 | 정본 규칙 4개 | (1) 플랫폼별 종료 금지(1.3 H). (2) 패치만, 재생성 금지: step 11(light는 10) 뒤에는 step 14·15의 수술적 패치만. 비평가의 지적이 섹션 전체 재작성을 요구하면 오케스트레이터에게 구조 이슈로 올리고 재작성하지 않는다. (3) ARGUE, DON'T JUST REPORT: `argumentative`에서 전력, `structured`·`short`에서 완화. loci에 변증적 locus ≥1, 깊이 조사자는 입장을 확정, step 6이 교차 조정을 강제, step 11은 긴장에 닿는 본문 섹션마다 명시적으로 다루게 한다. (4) 티어 게이트 존중(R-11) | 코드 확인 |
| R-35 | 복구 | 길을 잃으면 순서대로: (0) `run resume <tag>`(생략 시 최신 런)가 정확한 다음 단계와 호출을 돌려준다(주 경로, Claude는 스킬 이름, Codex는 단계 파일). (1) 할 일/계획 목록. (2) 디스크 산출물 스캔(폴백, 매니페스트가 없거나 갱신이 안 된 경우): 단계별 대표 산출물은 단계 1 `scaffold.md`·`prompt-decomposition.json`·`temp/coverage-matrix.md`, 2 태그된 볼트 노트, 3 `temp/contradiction-graph.json`·`temp/consensus-claims.json`, 4 `loci.json`, 5 `type: interim` 노트, 6 `comparisons.md`, 7 `temp/source-tensions.json`, 8 `corpus-critic-gaps.json`·`temp/corpus-critic-results.md`, 9 `temp/evidence-digest.md`, 10 `temp/draft-{a,b,c}.md`(light는 `final_report_<tag>.md`), 11 `temp/synthesis-{plan,outline,pass1}.md`와 `final_report_<tag>.md`, 12 `critic-findings-{dialectic,depth,width,instruction}.json`, 13 `temp/post-critic-fetch-log.md`, 14 `patch-log.json`, 15 `polish-log.json`, 16 `readability-recommendations.json`·`readability-decisions.json`. (3) 산출물이 존재하는 가장 높은 번호 단계 다음에서 재개. (4) 그래도 모르면 진입 스킬을 다시 읽는다 | 코드 확인 |
| R-36 | 브라우저 레인 규칙(경계) | 막힌 fetch는 큐에 쌓이고 사라지지 않는다(`escalation list --status queued --tag <tag> -j`). Claude: 캡차·로그인·2FA는 항상 사람의 몫(`needs_human`으로 표시, 자연스러운 멈춤 지점에 한 번에 한 메시지로 정리), 브라우저 fetcher는 한 번에 하나, step 13 뒤 큐를 다시 확인. Codex: 큐 소진을 기다리지 않고(파이프라인을 막지 않음) 마지막 메시지에 한꺼번에 사람에게 넘김 | 코드 확인 |
| R-37 | 종료 게이트(경계) | step 16 뒤 `run-manifest-gate.md` R-33의 절차(6개 파일 확인 루프, `sources retractions --tag`, `run finish`, 보고서 수정 최대 3라운드)를 따른다. 이 스펙은 부르는 시점만 소유한다 | 코드 확인 |
| R-38 | `vault-tag` | 1.3 B. 입력 슬러그 검증 → 볼트 탐색 → 사용 중 집합 → `<slug>-<6hex>` 유일성 보장(최대 100회) → 출력 | 코드 확인 |

- 불변식: `vault_tag`는 `vault-tag`가 만든 값이므로 `run-manifest-gate.md`의 태그 정규식을 항상 만족한다(슬러그 ≤60자 + `-` + 6자). 정본 질문 원문은 `query.md` 하나이고 모든 단계가 경로로 읽는다.
- 미결정:
  - R-31 · 챕터 모드에서 단계 2~11 스킬은 챕터를 전혀 언급하지 않는다(`grep -i chapter`가 1.5 스킬 밖에서 0건). 챕터 경로 교체·챕터 범위 spawn·전역 step 6/11의 입력 선택은 1.5 스킬의 "챕터 실행 루프" 문단에만 있고 해당 단계 스킬에는 대응 절차가 없다. 호스트가 그 문단만으로 단계 스킬을 재해석한다. 구현에 미치는 영향: dissertation 경로를 재현하려면 단계별 챕터 변형을 새로 정해야 한다(중간 영향, dissertation은 실험적).
  - R-31 · 전역 step 6·11을 매니페스트에 어느 단계 키로 기록하는지(진입 스킬 표의 "6g/11", `run step` 도움말의 "11g", 1.5 스킬은 "step 6 re-runs GLOBALLY"뿐)가 어디에도 정의돼 있지 않다. `run step`은 `--chapter` 없는 `6`을 이미 챕터 루프에서 `done`으로 쓴 키와 구분하지 못한다. 구현에 미치는 영향: 재개 위치가 부정확해진다(낮음).
- 확인 한계: 호스트 LLM이 프롬프트를 실제로 따르는지(분류의 정확도, 매트릭스 점검의 철저함 등)는 코드나 정적 읽기로 검증할 수 없다. 분류 규칙은 신호 예시이며 결정 알고리즘이 아니다. 코드는 실행하지 않았다.

### 1.5 필수 코드 참조 [필수]

원문 프롬프트는 MIT 라이선스(overview 1절)로 인용 가능하다. 글보다 원문이 정확한 부분만 C-ID로 넘긴다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/hyperresearch/skills/hyperresearch.md:25-37` | 오케스트레이터 역할 선언(Claude/Codex 분기) | R-01 |
| C-02 | `skills/hyperresearch.md:59-80` | 단계 표(번호·이름·한 줄 설명·티어) | R-12 |
| C-03 | `skills/hyperresearch.md:84-98` | 티어 표, dissertation opt-in·실험적 경고, 티어 게이트 존중, gear≠tier | R-11, R-13, R-14 |
| C-04 | `skills/hyperresearch.md:102-172` | 부트스트랩 0~7(플랫폼 분기 포함) | R-02~R-10 |
| C-05 | `skills/hyperresearch.md:176-216` | 정본 규칙 4개, 브라우저 레인, spawn 규약 | R-33, R-34, R-36 |
| C-06 | `skills/hyperresearch.md:218-245` | 복구 절차와 단계별 산출물 목록 | R-35 |
| C-07 | `skills/hyperresearch.md:249-283` | 종료 게이트 절차 | R-37 |
| C-08 | `skills/hyperresearch.md:287-303` | 불변식 15개 | 1.3 I |
| C-09 | `src/hyperresearch/skills/hyperresearch-1-decompose.md:34-58` | 원자 항목 범주와 `required_section_headings` 채우기 규칙·예시 | R-16, R-17 |
| C-10 | `skills/hyperresearch-1-decompose.md:60-102` | `prompt-decomposition.json` 전체 예시(필드 이름·모양) | R-18 |
| C-11 | `skills/hyperresearch-1-decompose.md:104-160` | 래퍼 요구 제외, 티어·형식·인용 스타일·레버 분류 표와 우선순위 | R-19~R-22 |
| C-12 | `skills/hyperresearch-1-decompose.md:162-199` | 커버리지 매트릭스, 티어 근거, `levers render`, 종료 조건 | R-23~R-26 |
| C-13 | `src/hyperresearch/skills/hyperresearch-1-5-chapter-partition.md:15-66` | 챕터 분할 규칙, `chapter-plan.json` 예시, 작업 공간·등록·태그 | R-27~R-30 |
| C-14 | `skills/hyperresearch-1-5-chapter-partition.md:70-94` | 챕터 실행 루프, 예산 점검, 종료 조건 | R-31, R-32 |
| C-15 | `src/hyperresearch/cli/vault_tag.py:36-144` | 슬러그 정규식, 사용 중 태그 수집(`_existing_tags`), 6-hex 생성·재시도·오류 코드 | R-05, R-38 |
| C-16 | `src/hyperresearch/cli/run_cmd.py:44-90` | `run init` 옵션과 출력 | R-06 |
| C-17 | `src/hyperresearch/core/levers.py:23-35`, `:198-215`, `:235-258`, `:265-330` | `REGISTERS`·`INFERENCE_DEPTHS`·`ROLES`·`DEFAULT_LEVERS`, `validate_levers`, `compose_shims`(shim 4개 조립), `read_levers`/`render_shims`(분해 JSON에서 levers 읽기·shim 쓰기·매니페스트 기록) | R-22, R-25 |
| C-18 | `src/hyperresearch/cli/archive.py:25-50`, `:96-170` | `archive-run`이 옮기는 이름 18개·`temp/`, 보관 디렉터리 이름 | R-03 |
| C-19 | `src/hyperresearch/core/render.py:1-76` | 프롬프트 구분자(`<< >>`, `<% %>`)와 변수 `p`·`<profile>`·`platform`, 필터 `dash`·`hyphen`, strict 모드 | 1.2(경계) |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(CLI 동작은 코드에서, 프롬프트 동작은 스킬 본문에서). 테스트는 열지 않았다. 프롬프트 사례는 호스트의 준수를 가정한 기대값이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-05, R-38 | `vault-tag efield-dft-sac` | 반환 태그는 `efield-dft-sac-` + 6자리 소문자 16진수(조건: 사용 중 집합에 없음). 디렉터리는 만들어지지 않는다. `vault-tag Efield`·`-a`·61자 슬러그는 `INVALID_SLUG`, 종료 1 |
| T-02 | R-38 | `research/runs/efield-dft-sac-a3f9b7/`가 이미 있고 `research/notes/final_report_efield-dft-sac-b00001.md`와 `research/query-efield-dft-sac-c00002.md`가 있다 | 위 세 접미사는 다시 나오지 않는다. `runs/archive-...` 이름은 사용 중 집합에서 제외된다 |
| T-03 | R-02 | cwd에 `.hyperresearch/`가 없다 | `hyperresearch init . --json`이 실행돼 `research/{notes,index,temp}`가 생긴다. cwd가 기존 볼트의 하위 디렉터리여도 직속 `.hyperresearch/`가 없으면 `init`이 실행된다(중첩 볼트 가능, 점검이 직속만 보기 때문) |
| T-04 | R-04, R-07 | `research/prompt.txt`가 있고 사용자 프롬프트가 다르다 | 정본 질문은 `prompt.txt` 내용이고 `query.md` 프론트매터의 `source: prompt.txt`. 없으면 사용자 문장과 `source: user-prompt` |
| T-05 | R-17, R-18 | 질문: "1) List major manufacturers... 2) Include images... 3) Analyze primary use cases... 4) Investigate market penetration..." | `required_section_headings`는 4개(질문 순서, 번호 매긴 제목), 비어 있지 않음. `entities`는 질문이 이름을 붙인 것만 |
| T-06 | R-17 | 질문: "Write about rail electrification" (열린 서술) | 제목은 4~7개: 배경 → 핵심 분석 1~3 → 비교 → 함의·전망. 모든 하위 질문을 덮음 |
| T-07 | R-19, R-20 | "What is a Bloom filter?" / "Evaluate whether urban rail beats BRT under SIL-4 constraints, through 2035" | 앞: `light`+`short`(또는 `structured`), 뒤: `full`+`argumentative`, `scope_conditions`에 SIL-4, `time_horizons`에 "through 2035". 애매한 질문은 `full` |
| T-08 | R-22 | 질문: "Make it a survey: ...", `wrapper_contract.json.levers.register = "teach"` | `register = "survey"`(사용자 명시 > 래퍼 > 분류) |
| T-09 | R-22, R-25 | 분해 JSON의 `levers.register = "expert"` | `levers render`가 `LEVER_ERROR`(알 수 없는 register)로 종료 1, shim이 쓰이지 않는다. 호스트는 `levers`를 고쳐 다시 렌더링 |
| T-10 | R-23 | 질문이 "SaaS applications"를 말하는데 분해 항목이 "POS SaaS" | 매트릭스 행 `Gap? = **YES**`(NARROWED) → 분해를 넓힌 뒤 매트릭스 재작성, 모든 행 `No`가 되기 전에는 step 2로 가지 않는다 |
| T-11 | R-11, R-12 | 분해 `pipeline_tier = "light"` | 호출 순서는 2, 10, 15, 16(3~9·11~14.5는 안 부름). 코드 쪽에서도 `run resume`은 `next_step`을 10으로 계산한다(`run-manifest-gate.md` T-07) |
| T-12 | R-29, R-31 | dissertation, 챕터 3개(`ch1`~`ch3`) | `chapter-plan.json` 챕터 3개, `chapters/ch{1,2,3}/temp/` 생성, `chapter-plan` 이벤트 3번 → `run resume`의 `chapters_pending = ["ch1","ch2","ch3"]`, 단계 1.5 `done`. 원자 항목이 10개뿐인 질문은 챕터 1개로 기록(`full` 모양) |
| T-13 | R-31 | 챕터 `ch1`이 step 10 완료 | `run step <tag> 10 --status done --chapter ch1`, 초안은 `chapters/ch1/draft.md`, 챕터 노트는 태그 `<tag>`와 `<tag>-ch1` 둘 다 |
| T-14 | R-33 | step 5 depth-investigator spawn | 프롬프트 상단 근처에 `query.md`의 질문 원문 블록 인용, "당신은 step 5 ... step 4가 `loci.json`을 만들었고 끝나면 step 6이 조정" 같은 위치 진술, `vault_tag`·`output_path`·locus, 그리고 `shims/research.md` 전문. cite-checker spawn에는 shim이 없다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@aece65f `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-08 | 스킬 본문 전체 읽음 |
| R-02, R-03 | C-04, C-18 `main.py:16-35` `init`, `vault.py:140-196` `Vault.init`, `archive.py:96-170` `archive_run` | 호출 시점은 스킬, 부작용은 CLI 구현에서 확인. `Vault.discover`(`vault.py:199-211`)는 위로 올라가며 찾지만 스킬 점검은 직속 `.hyperresearch/`만 본다 |
| R-04, R-07 | C-04 | 읽음. `prompt.txt` 생산자는 `codex_bench/`(미열람) |
| R-05, R-38 | C-15 | 구현 전체 읽음 |
| R-06 | C-04, C-16 | 읽음. 매니페스트 효과는 행 9 |
| R-08, R-09 | C-04 | 읽음. 모달리티를 읽는 곳: step 10 스킬 본문(`hyperresearch-10-triple-draft.md:27,34,174`)과 에이전트 프롬프트(`core/hooks.py:1985`)에서 라벨로만 소비 |
| R-10 | C-04 | 읽음 |
| R-11~R-13 | C-02, C-03 | 읽음 |
| R-14 | C-03, 행 9 `runs.py:609-646` | 코드 확인 |
| R-15~R-26 | C-09~C-12, C-17 | 스킬 본문을 끝까지 읽음. 분류 규칙은 신호 예시이고 결정 절차가 아님 |
| R-22 | C-11, C-17 `levers.py:198-215` `validate_levers`, `:235-258` `compose_shims` | `register_confidence`는 `DEFAULT_LEVERS`에만 있고 `_header`·검증에서 안 쓰임을 확인. shim 본문 읽기는 행 2 소관 |
| R-27~R-32 | C-13, C-14 | 읽음. 챕터 언급 없음은 `grep -i chapter skills/hyperresearch-*.md`(1.5 제외)로 확인 |
| R-33~R-37 | C-05~C-07 | 읽음 |
| T-01~T-14 | 위 R-ID | 코드·스킬 읽기만으로 도출. 원본 테스트는 열지 않았다 |

**문서와 구현의 차이 (구현·본문을 사실로 썼다)**
- 스킬 단계 표·티어 표는 스킬을 "16 steps"로 부르지만 설치기 로스터는 18개(1.5, 14.5 포함)다(`core/hooks.py:4388-4407`). 진입 스킬의 "The 16 step skills" 표 자체는 1.5와 14.5를 포함한 18행이다.
- spawn 규약은 "다음 세 가지가 반드시 들어간다"고 하고 목록은 네 항목이다(`skills/hyperresearch.md:204-212`). 4번(shim 붙임)이 나중에 추가된 흔적으로 본다(추론).
- 진입 스킬은 `dissertation`을 `1 → 1.5 → [2~10 챕터마다] → 6g/11 → …`로 쓰지만 `6g`·`11g`를 정의하는 곳이 없다(`skills/hyperresearch.md:92`, 행 9 2.1 참조).
- `dissertation`의 길이·소스·인용 목표를 "읽는 곳이 없다(#103)"고 하나, 소스·챕터 수치는 스킬에 렌더링돼 읽히고 길이는 `run finish`가 `response_format` 키로만 읽는다(`run-manifest-gate.md` 2.1). step 1은 `dissertation` 응답 형식을 정의하지 않는다(`hyperresearch-1-decompose.md:121-125`).
- `vault-tag` 모듈 주석(`vault_tag.py:1-19`)은 `research/query-<tag>.md`를 중심으로 설명하지만 현재 쿼리 파일은 `runs/<tag>/query.md`다. 사용 중 집합이 둘을 모두 보는 것은 그 호환 때문이다(추론).
- 부트스트랩 0.5의 `archive-run`은 `research/temp/`가 비어 있지 않으면 통째로 옮긴다(`archive.py:50`, `:128-138`). 같은 경로는 `Vault.temp_dir`(링크 자동 해소가 쓰는 "옆으로 치운 노트" 폴더, `vault.py` `temp_dir`)이기도 하다. 그래서 새 런을 시작할 때마다 이 폴더의 노트가 `runs/archive-*/temp`로 이동할 수 있다(코드 확인: 이동 대상 선택. 이동 뒤 동기화가 DB 행을 지우는지는 행 15에서 확인해야 함 — 추론).
- 슬러그 정규식은 `re.match`와 `$`를 쓴다(`vault_tag.py:101`). `$`는 끝의 개행 하나를 허용하므로 `abc\n` 같은 입력이 통과할 수 있고 그러면 만들어진 태그가 `run-manifest-gate.md`의 태그 정규식을 어긴다(추론: 실행하지 않음).
- `register_confidence`는 분해 예시와 `DEFAULT_LEVERS`에만 있고 `validate_levers`·`compose_shims`·매니페스트 기록 어디서도 읽지 않는다(`core/levers.py:33`, `grep register_confidence`로 확인). 신뢰도 규칙("애매하면 `analyze`")은 step 1을 수행하는 호스트가 분류할 때만 적용되고 코드는 값을 소비하지 않는다(R-22).

### 2.2 코드 읽는 순서 [선택]
1. `skills/hyperresearch.md` 전체(특히 59-172 부트스트랩과 218-283 복구·게이트). Jinja 분기(`<% if platform == "codex" %>`)는 설치 시 렌더링으로 하나만 남는다(`core/render.py`, 행 2).
2. `skills/hyperresearch-1-decompose.md` → `core/levers.py:200-330`(`validate_levers`/`render_shims`) → `core/runs.py:609-646`(분해 JSON의 `pipeline_tier` 읽기).
3. `cli/vault_tag.py`와 `cli/run_cmd.py:44-90`.
4. dissertation만: `skills/hyperresearch-1-5-chapter-partition.md`.

## 적용 메모 [선택]
(없음)
