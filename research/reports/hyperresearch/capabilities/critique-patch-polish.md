---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/skills/hyperresearch-12-critics.md
  - src/hyperresearch/skills/hyperresearch-13-gap-fetch.md
  - src/hyperresearch/skills/hyperresearch-14-patcher.md
  - src/hyperresearch/skills/hyperresearch-14-5-cite-check.md
  - src/hyperresearch/skills/hyperresearch-15-polish.md
  - src/hyperresearch/skills/hyperresearch-16-readability-audit.md
  - src/hyperresearch/skills/hyperresearch.md
  - src/hyperresearch/core/hooks.py
  - src/hyperresearch/core/profiles.py
  - src/hyperresearch/core/citecheck.py
  - src/hyperresearch/cli/citecheck_cmd.py
  - src/hyperresearch/core/runs.py
  - src/hyperresearch/cli/lint.py
depends:
  - draft-synthesis.md
  - run-manifest-gate.md
  - vault-store.md
  - claims-store.md
  - subagent-roster.md
  - verification-battery.md
status: ready
---

# 비평·패치·인용 검사·다듬기 (12, 14, 14.5, 15, 16단계)

> 합성된 최종 보고서 `research/notes/final_report_<tag>.md`를 입력으로, 비평가 4종이 서로 다른 관점의 findings JSON을 쓰고(12), 패처가 그것을 "수술적 Edit"로만 적용하고(14), 인용 검사가 인용-문장 결합을 기계 분류·에이전트 판정 뒤 2차 패치로 고치고(14.5), polish 감사기가 위생·군더더기를 걷어내고(15), 가독성 추천기가 낸 제안을 호스트가 골라 적용하는(16) 프롬프트 절차와 각 단계의 로그 파일 형식을 정의한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

**full 티어**
1. step 12: 호스트가 비평가 4종(dialectic·depth·width·instruction)을 한 메시지로 동시에 spawn한다. 각자 보고서를 끝까지 읽고 볼트에서 증거를 찾아 `critic-findings-<이름>.json`(`{critic_type, findings:[…]}`)을 쓴다. 호스트는 그 findings를 직접 읽거나 적용하지 않고 step 13으로 넘긴다.
2. step 13(행 5 경계): 비평가가 지적한 빈 곳 중 볼트에 소스가 0~1개인 것만 최대 `gap_fetch_cap`(5)개 fetch하고 증거 다이제스트에 `### Post-critic gap fill`을 덧붙인다. 패처가 인용할 재료를 준비하는 단계다.
3. step 14: `skip-patcher.txt`가 있으면 최소 로그만 쓰고 건너뛴다. 아니면 호스트가 `patch-log.json` 스텁을 만들고 패처를 한 번 spawn한다(도구 `Read, Edit`). 패처는 findings를 심각도순으로 합쳐 중복을 제거하고 보고서에 Edit를 하나씩 적용하며 로그를 채운다. 호스트는 로그를 읽어 skip된 critical을 해결하고, `orchestrator_escalated`(제목 순서·누락 같은 구조 재편)를 직접 Edit로 처리한 뒤 `orchestrator-restructure-log.md`에 기록한다.
4. step 14.5: `citecheck extract <tag> -j`가 (문장, 인용) 쌍을 뽑아 기계 분류해 `cite-check-pairs.json`을 쓴다. 호스트는 dangling 인용을 사유별로 처리하고, 에이전트가 판정할 표본(`sampled_for_llm`)을 `cite-checker`에 보낸다(40쌍 초과면 2개로 나눔). 판정에서 나온 findings(+dangling findings)가 비어 있지 않으면 같은 패처를 `cite-check-patch-log.json` 스텁과 함께 한 번 더 spawn한다. 끝에 `run step <tag> 14.5 --status done`.
5. step 15: 호스트가 `polish-log.json` 스텁을 만들고 `polish-auditor`를 한 번 spawn한다(도구 `Read, Edit`). 감사기가 위생 누출 제거, 파이프라인 어휘 재작성, 필러·메타 담화·중복·헤지 삭제, 긴 문장·문단 쪼개기를 Edit로 하고 `{applied, escalations}`를 기록한다. 호스트는 에스컬레이션을 한 번만 직접 고치고, 필수 산출물 존재를 확인하고(없으면 담당 에이전트를 한 번 재spawn, 또 실패하면 스텁), `audit_findings.json`에 실행 기록을 덧붙이고 lint 4규칙을 돌린다.
6. step 16: 호스트가 `readability-recommender`(도구 `Read, Write`)를 한 번 spawn해 `readability-recommendations.json`을 받고, 제안을 골라(제안 `current`를 `old_string`, `recommended`를 `new_string`으로) Edit로 적용하고 `readability-decisions.json`에 결정을 기록한다.
7. 이후 진입 스킬의 ship gate(`sources retractions` → `run finish`, 행 9)가 최종 판정을 한다.

**light 티어**: 12·13·14·14.5를 건너뛴다(비평가 없음 = 패치할 findings 없음). 15와 16만 돈다. 필수 산출물은 `polish-log.json` 하나다.

### 1.2 범위·통합 지점 [필수]
- 제공: 비평가 4종의 관점·입력·spawn 규칙·findings JSON 형식·심각도·상한, 패처의 수술적 Edit 규칙과 `patch-log.json`, 호스트의 skip 게이트·스텁 생성·로그 판독·구조 재편 에스컬레이션 처리, step 14.5의 호출 순서·입력·산출·2차 패치 조건과 cite-checker 판정 규칙, polish 감사기의 위생·군더더기 제거 규칙과 `polish-log.json`, step 15의 통합 게이트·lint 호출, 가독성 추천기의 범주·임계값·JSON 형식, 호스트의 선택 적용 규칙과 `readability-decisions.json`, 단계별 종료·건너뛰기·티어 차이.
- 제외(경계만):
  - step 13 갭 fetch(행 5, [width-sweep](width-sweep.md)): 12가 끝난 뒤 14 앞에서 돈다. 이 스펙은 "critic findings를 읽어 증거가 부족한 빈 곳을 채우고 다이제스트에 덧붙인다"는 사실만 쓴다.
  - 인용 쌍 추출과 기계 분류 알고리즘, lint 26개 규칙(`quote-integrity`·`numeric-consistency`·`wrapper-report`·`locus-coverage`·`scaffold-prompt`·`patch-surgery`의 판정 본문 등)(행 10, [verification-battery](verification-battery.md)). 이 스펙은 호출 순서와 입력·산출·결과의 쓰임만 쓴다. 입력 `final_report_<tag>.md`와 `claims` 테이블, 정상 결과 `cite-check-pairs.json`(`report`, `summary{total,supported_mechanical,dangling,needs_llm}`, `sampled_for_llm[]`, `dangling[]`), 실패 시 `NO_REPORT`(보고서 없음)·`NO_VAULT`·`INVALID_TAG`로 종료 코드 1.
  - 서브에이전트 정의의 frontmatter(모델 키·색·도구 줄)(행 3, [subagent-roster](subagent-roster.md))와 shim 내용(행 2). 이 스펙은 각 에이전트가 받는 shim 파일 이름과 도구 잠금 사실만 쓴다.
  - `run finish`·`verify_run`(행 9, `run-manifest-gate.md`): `critic-findings-*`·`patch-log.json`·`polish-log.json`·`cite-check-findings.json`·`cite-check-patch-log.json`의 존재 검사.
  - 최종 보고서를 만드는 단계(행 7, `draft-synthesis.md`)와 분해 JSON의 필드(행 4, `entry-decompose.md`): 이 스펙은 `required_section_headings`·`citation_style`·`response_format`·원자 항목을 읽는다는 사실만 쓴다.
- 외부 의존·선행 계약:
  - 볼트 CLI(`vault-store.md`): `search "<질의>" --tag T -j`, `note list --tag T [--type interim] --all -j`, `note show <id>... -j`(웹 출처 노트 본문은 `<untrusted-source>` 울타리, `interim`·`source-analysis`는 울타리 없음), `lint --rule <이름> --json`(행 10). `claims search "<구절>" -j`(`claims-store.md` R-17: FTS 일치, 결과에 `note_id`·`claim`·`quoted_support`).
  - 호스트: 서브에이전트 spawn, Bash(`echo`로 스텁 생성, python으로 JSON 읽기·쓰기, `test -f`), 호스트 자신의 Write·Edit(구조 재편·로그 복구에만 허용, 서브에이전트 잠금은 적용되지 않음), 도구 호출 없는 응답 금지 규칙.
  - 프로필 값(행 2, 이 스펙의 입력): `critic_finding_caps`, `readability_rec_cap`, `gap_fetch_cap`(1.3 I).
- 소유 상태·부작용: 최종 보고서 `research/notes/final_report_<tag>.md`를 **Edit로만** 바꾼다(재생성 금지). 런 작업 공간에 1.3 C의 산출물을 쓴다.

### 1.3 인터페이스와 데이터 의미 [필수]

**A. 티어별 실행·건너뛰기**

| 단계 | light | full / dissertation(전역 11 뒤) | 건너뛰기 조건 |
|---|---|---|---|
| 12 비평 | 건너뜀 | 실행 | light. 비평가 하나가 두 번 실패하면 빈 스텁으로 진행(건너뜀 아님, R-04) |
| 13 갭 fetch(경계) | 건너뜀 | 실행 | light. 갭 0개면 "갭 없음"을 로그하고 14로 |
| 14 패처 | 건너뜀 | 실행 | light. 또는 `research/runs/<tag>/skip-patcher.txt`가 있으면 건너뛰기 경로(R-19) |
| 14.5 인용 검사 | 건너뜀(light는 `quote-integrity`·`numeric-consistency`가 15 게이트에서 기계적으로 덮음) | 실행 | light. `sampled_for_llm`이 비고 dangling도 없으면 에이전트·2차 패치 없이 `[]`만 쓰고 종료(R-35) |
| 15 polish | 실행 | 실행 | 건너뛰기 없음(모든 티어) |
| 16 가독성 | 실행 | 실행 | 건너뛰기 없음 |

**B. 서브에이전트 (frontmatter `tools`·모델 키는 행 3, 여기서는 사실만)**

| 에이전트 | 도구 | 모델 키 | spawn | 받는 shim | 쓰는 파일 |
|---|---|---|---|---|---|
| `hyperresearch-dialectic-critic` / `-depth-critic` / `-width-critic` / `-instruction-critic` | Bash, Read, Write | `critics`(기본 opus) | 4개 동시(한 메시지) | `shims/critics.md` | `critic-findings-{dialectic,depth,width,instruction}.json` |
| `hyperresearch-patcher` | **Read, Edit** | `patcher`(opus) | step 14에서 1회, step 14.5.3에서 1회 | `shims/critics.md`(14), 2차 패스는 "step 14 장치를 그대로"(R-38) | 보고서(Edit), `patch-log.json` / `cite-check-patch-log.json`(스텁에 Edit) |
| `hyperresearch-cite-checker` | Bash, Read, Write | `cite_checker`(sonnet) | 1개, 표본이 약 40쌍을 넘으면 색인 범위를 나눠 2개 | **없음**(검증은 register와 무관) | `cite-check-findings.json` 또는 `-a.json`/`-b.json` |
| `hyperresearch-polish-auditor` | **Read, Edit** | `polish_auditor`(opus) | 1회 | `shims/polish.md` | 보고서(Edit), `polish-log.json`(스텁에 Edit) |
| `hyperresearch-readability-recommender` | **Read, Write** | `readability_recommender`(opus) | 1회 | `shims/polish.md` | `readability-recommendations.json` |

Codex 렌더링에서는 "도구 잠금" 대신 "읽고 patch만 적용"(`apply_patch`)으로 말하고 spawn은 `custom_agent`이며 구조적 사실은 같다.

**C. 파일** (경로는 `research/runs/<tag>/` 기준. "코드가 보는가"는 `run-manifest-gate.md` 1.3 B·G와 lint)

| 파일 | 쓰는 쪽 | 코드가 보는가 |
|---|---|---|
| `critic-findings-{dialectic,depth,width,instruction}.json` | 비평가(실패 시 호스트 스텁) | `verify_run`: 12·14가 필수 단계 집합에 있으면 4개 모두 존재. lint `patch-surgery`의 빈 로그 탐지: dialectic·depth·width의 `findings` 길이 합 |
| `patch-log.json` | 호스트 스텁 → 패처가 채움(없으면 호스트가 결과 메시지에서 복구) | `verify_run` 존재. lint `patch-surgery`: JSON 유효성, `skipped[]`의 `severity == "critical"` 항목(`finding_id`·`critic`을 메시지에 씀), `applied+skipped+conflicts == 0`이면서 비평 findings가 있으면 경고 |
| `skip-patcher.txt` | 호출자(드물게) | 스킬 분기에서만 |
| `orchestrator-restructure-log.md` | 호스트(구조 재편 시) | 코드가 읽지 않음(`archive-run`의 보관 대상 이름에만 있음) |
| `cite-check-pairs.json` | `citecheck extract` | 에이전트 입력 |
| `cite-check-findings.json` (+`-a`/`-b`) | cite-checker 병합본, 호스트가 dangling findings를 덧붙임 | `verify_run`의 `cite-check-resolved`(14.5가 `done`으로 기록된 경우만) |
| `cite-check-patch-log.json` | 호스트 스텁 → 2차 패처 | `critical` finding이 하나라도 있으면 존재해야 함 |
| `polish-log.json` | 호스트 스텁 → polish 감사기 | `verify_run`: 15가 필수 단계 집합에 있으면 존재 |
| `audit_findings.json` | 호스트(15.5에서 덧붙임) | v8 기록은 어느 규칙도 읽지 않는다(R-56) |
| `readability-recommendations.json` | 추천기 | 코드가 보지 않음 |
| `readability-decisions.json` | 호스트 | 코드가 보지 않음 |

**D. findings JSON** (비평가 4종 공통 파일 형태 `{"critic_type": "<이름>", "findings": [ … ]}`, 빈 결과는 `findings: []`, 실패 스텁은 `{"findings": [], "critic_failed": "<이유>"}`)

| 필드 | 값 | 어떤 비평가 |
|---|---|---|
| `severity` | `critical` / `major` / `minor` (정의는 R-07) | 전부 |
| `location` | 섹션 이름·제목 + 대상 영역의 짧은 텍스트 조각(정확 일치 불필요, 패처가 위치를 찾을 수 있을 만큼) | 전부(구조 일치 검사 finding은 `""`) |
| `issue` | 한 문장: 무엇이 빠졌거나 틀렸나 | 전부 |
| `evidence` | 지지하는 볼트 노트 id 또는 인용. depth는 반드시 interim 노트를 가리킴 | dialectic·depth·width(instruction의 구조 finding에는 없음) |
| `recommendation` | 수정이 이루어야 할 일(무엇을 어디에 추가·한정할지). 정확한 문구는 패처가 정한다 | 전부 |
| `atomic_item` | 지키지 못한 프롬프트 조각을 `research_query` 또는 분해 JSON에서 **글자 그대로** 인용. readability 구조 점검은 접두사 `readability-structural` | instruction |
| `failure_mode` | `missing` `under-covered` `wrong-order` `wrong-format` `vague-recommendation`, 그리고 `decomposition-gap` `missing-definitions` `low-citation-density` `missing-forward-analysis` `missing-comparison-table` `missing-section-primers` `missing-comparison-dimensions` | instruction |
| `requires_orchestrator_restructure` | bool(기본 false). H2의 이동·추가·삭제, 수술적 Edit 범위를 넘는 수정(새 섹션 본문 전체)일 때 true. 제목 일치 검사 finding은 **항상 true** | instruction |

`old_text`/`new_text` 같은 정확 패치는 **쓰지 않는다**(패처가 문구를 정한다). 비평가는 Write 도구로 파일을 쓰고 Bash heredoc을 쓰지 않는다(이스케이프 문제). 설치된 instruction-critic·readability-recommender 프롬프트의 JSON 예시에는 이중 중괄호 `{{ }}`가 그대로 남아 있다(2.1).

**E. `patch-log.json`** (정본 스텁, 호스트가 쓰는 값)

```json
{"total_findings": 0, "applied": [], "skipped": [], "conflicts": [], "orchestrator_escalated": []}
```

패처는 **이 키들만** 채운다(대체 스키마를 만들지 않는다. 하류 도구가 이 모양을 가정). `total_findings`는 정수가 되고 네 배열이 채워진다. 코드가 읽는 항목 필드는 `skipped[].severity`·`skipped[].finding_id`·`skipped[].critic`뿐이고 나머지 항목 내부 형태는 원문이 정하지 않았다. 건너뛰기 경로의 로그: `{"total_findings": <세 비평가 파일의 findings 합>, "applied": [], "skipped": [{"reason": "patcher-skipped-by-invoker"}], "conflicts": [], "orchestrator_escalated": []}`(`critic-findings-*.json` 4개 중 존재하는 것의 `findings` 길이 합).

**F. cite-check**

`cite-check-pairs.json`의 쌍(`sampled_for_llm[]`·`dangling[]` 항목): `sentence`, `marker`(`[N]` 또는 `[[id]]`), `note_id`(해석 실패 시 null), `numbers`, `strong`(수치 있는 문장 여부), `verdict`(`dangling`/`supported-mechanical`/`needs-llm`), dangling이면 `unresolved` ∈ {`no-sources-entry`, `unknown-note-id`, `unresolved-entry`}. 알고리즘(문장 분할, 숫자·6단어 겹침 판정, 표본 추출)은 행 10이 소유한다. 호출:

| 명령 | 입력 | 효과·출력 |
|---|---|---|
| `hyperresearch citecheck extract <tag> [--report PATH] [--sample-rate 0.6] [-j]` | 태그(검증됨), 보고서 기본 `research/notes/final_report_<tag>.md`, `--sample-rate`는 수치 없는 쌍의 표본 비율(수치 있는 문장은 항상 100%) | `cite-check-pairs.json` 작성. 데이터 `{pairs_file, summary{total,supported_mechanical,dangling,needs_llm}, sampled_for_llm(개수), dangling(개수)}`, 텍스트 `Cite-check triage: N pairs — A auto-passed, S sampled for LLM verification, D dangling` |

cite-checker findings 한 항목: `{"verdict": "unsupported|partially-supported|wrong-source", "severity": "critical|major", "sentence": <쌍 파일의 문장 그대로>, "cited_note_id": <id>, "correct_note_id": <id 또는 null>, "evidence": <한 문장: 노트가 실제로 말하거나 빠뜨린 것>, "suggested_fix": "swap citation | soften claim to what the source supports | delete sentence"}`. 파일은 JSON 배열(`[]` 가능)이고 `verify_run`은 배열과 `{"findings":[…]}` 둘 다 받는다.

**G. `polish-log.json`**

```json
{"applied": [{"category": "hygiene", "description": "stripped YAML frontmatter", "chars_removed": 142}],
 "escalations": [{"category": "prompt_adherence", "issue": "user asked for ranked list; draft is unranked prose. Recommend restructure."}]}
```

스텁은 `{"applied": [], "escalations": []}`. 감사기는 Edit로 `'"applied": []'`와 `'"escalations": []'`를 채운다.

**H. 가독성 JSON**

`readability-recommendations.json`: `{"recommendations": [{"id": "rec-N", "category": <8개 중 하나>, "severity": "minor|moderate|major", "section": "## I. 섹션 제목 / <exec summary> / <conclusion>", "current": <보고서 원문 그대로 복사한 텍스트>, "recommended": <대체 텍스트, remove-hr는 "">, "rationale": <한 문장>}], "summary": {"total_recommendations": int, "by_category": {8개 범주별 int}, "highest_severity": …, "expected_net_char_delta": int}}`. 범주 8개: `merge-paragraphs` `break-paragraph` `make-list` `make-table` `bold-keyterms` `split-sentence` `remove-hr` `add-whitespace`.

`readability-decisions.json`: `{"total_recommendations": int, "applied": [적용한 id], "skipped": [{"id": "rec-N", "reason": 한 문장}], "edit_failures": [{"id": "rec-N", "reason": "old_string did not match the draft"}], "net_char_delta_actual": int(실제 측정)}`.

**I. 프로필 값 (행 2 소유, 이 스펙의 입력)**

| 값 | full gear | premier gear | dissertation | 쓰이는 곳 |
|---|---|---|---|---|
| `critic_finding_caps` dialectic / depth / width / instruction | 12 / 12 / 10 / 15 | 16 / 16 / 14 / 18 | 24 / 24 / 20 / 30 | 각 비평가 "최대 N개". width는 N−2 커버리지 + 2 bloat, instruction은 N−3 지시 이행 + 3 readability |
| `readability_rec_cap` | 50 | 60 | 100 | step 16 spawn 지시와 추천기 상한 |
| `gap_fetch_cap` | 5 | 8 | 10 | step 13(경계) |
| `citation_density_min`, `chars_per_word_no_word_boundary` | 9.0, 3.0 | 같음 | 같음 | instruction critic의 R2 점검(`draft-synthesis.md` 1.3 A와 같은 값) |

### 1.4 행동 규칙과 남은 질문 [필수]

프롬프트의 원문은 1.5 C-ID가 정본이다. 모든 규칙은 호스트 LLM과 서브에이전트가 따르는 텍스트 규약이며 코드가 강제하는 것은 ship gate의 존재·형식 검사와 CLI뿐이다(확인 한계).

**step 12: 비평가 4종**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | step 12 시작 | light는 건너뛰고 step 15로. full은 `scaffold.md`(vault_tag), `prompt-decomposition.json`(`pipeline_tier`, 원자 항목), `final_report_<tag>.md`, `query.md`를 읽는다. 비평가는 **보고서를 직접 수정하지 않는다**. | 코드 확인 |
| R-02 | spawn | 4개를 **한 메시지에서 동시에**(Codex: 모두 지금 병렬로) spawn한다. 프롬프트: 질의 원문 `> ` 인용, `QUERY FILE`, `PIPELINE POSITION`(step 12 (<이름> critic), step 11이 최종 보고서를 만들었고 이후 step 13이 갭 fetch를 하고 step 14가 findings를 Edit로 적용), 입력 `draft_path`(`final_report_<tag>.md`)·`output_path`(`critic-findings-<이름>.json`)·`vault_tag`·`decomposition_path`(**instruction만**), 끝에 `shims/critics.md` 전문. | 코드 확인 |
| R-03 | 대기 | 4개가 모두 끝날 때까지 기다린다(대기 중 도구 호출 없는 텍스트 응답 금지는 진입 스킬 규약). | 코드 확인 |
| R-04 | 비평가 실패 | 한 번 재spawn. 또 실패하면 부분 집합으로 진행하고 그 비평가의 파일을 **호스트가 직접** `{"findings": [], "critic_failed": "<이유>"}`로 쓴다(ship gate가 4개 파일을 모두 요구하므로). 실행 로그에 부재를 적는다. 패치 패스가 덜 견고해진다는 경고와 함께. **instruction-critic은 생략하지 않는다**(프롬프트 준수 차원을 재는 유일한 비평가이고 변동이 가장 큰 차원). | 코드 확인 |
| R-05 | 호스트의 역할 | findings를 읽고 직접 적용하지 않는다. step 13(갭 fetch) 다음에 패처에게 넘긴다. 종료 조건: 4개 JSON이 존재하고 각각 유효 JSON에 `findings` 배열이 있다(실패 비평가의 스텁 포함). | 코드 확인 |
| R-06 | 비평가 공통 | 질의 파일을 **먼저** 읽는다(초안의 프레임에 닻을 내리지 않으려고). 결과는 Write 도구로 `output_path`에 쓴다(Bash heredoc 금지). findings 개수는 1.3 I의 상한을 넘지 않으며 넘으면 하중이 큰 것을 남긴다("작은 지적 40개가 critical을 묻는다"). **섹션 전체를 지우고 다시 쓰는 수정을 제안하지 않는다**(재생성). 문장 삽입·주장 한정·짧은 문단 추가로 고칠 수 있는 지적만 낸다. 문서 전체 재구조가 필요하면 `issue`에 structural이라 표시해 호스트에 에스컬레이션한다. 정확 패치 `old_text`/`new_text`는 쓰지 않는다. 보고: 파일 경로, 심각도별 개수, 단일 패치로 못 고치는 최상위 우려(예: "증거에 비춰 초안이 틀린 논지를 골랐다"). | 코드 확인 |
| R-07 | 심각도 정의 | **dialectic**: `critical` 초안이 볼트 자신의 증거와 모순되는 것을 주장, `major` 볼트가 다루는 실제 반대 입장을 초안이 무시, `minor` 헤지·한정이 주장을 강화하지만 초안이 틀리진 않음. **depth**: `critical` 초안의 핵심 논지가 interim 노트가 반박·복잡화하는 얕은 주장에 기댐, `major` 섹션이 interim 노트의 하중 증거를 덜 씀, `minor` 구체 수치·인용이 이미 적절한 문단을 강화. **width**: `critical` 질의가 명시적으로 묻는 코퍼스 군집이 초안에 전혀 없음, `major` 질의에 관련된 군집이 덜 다뤄짐, `minor` 군집이 초안을 풍부하게 하지만 필수는 아님. **instruction**: `critical` 프롬프트가 명시한 원자 항목이 통째로 없음 또는 근본적으로 틀린 형식(순위 목록을 요구했는데 순위 없는 산문), `major` 항목이 있으나 덜 다뤄짐(전용 섹션이 암시되는데 한 문단) 또는 순서가 뒤섞임 또는 증거가 구체성을 뒷받침하는데 추상적인 권고, `minor` 항목이 적절하지만 암시된 표현·하위 항목이 빠짐. | 코드 확인 |
| R-08 | dialectic 절차 | 질의 → 보고서 끝까지 읽으며 **입장을 취하는 모든 주장**을 표시(반론을 인정하지 않고 자신 있게 들리는 주장 포함) → `search "<키워드>" --tag <tag> -j`로 보고서의 주장과 어긋나거나 복잡하게 하는 interim·폭 코퍼스·소스 발췌를 찾고 의심 노트는 `note show <id> -j`로 전문 읽기 → 각 지적에 구체 패치(삽입할 문장, 붙일 한정어, 포함할 인용)를 권고로 제안. 질의가 요청한 것과 초안이 낸 것의 틈에 닿지 않는 지적은 패처가 기각해야 한다. | 코드 확인 |
| R-09 | depth 절차 | 질의 → `note list --tag <tag> --type interim --all -j`로 모든 깊이 조사자 interim 보고 나열 → 각 interim의 Synthesis 섹션이 초안에 충분히 반영됐는지 대조 → 얕은 지점을 표시: 수치·인용 없는 결론, interim이 설명하는 이름 붙은 메커니즘을 언급만 함, **전개된 정량 메커니즘(요인 모델과 적재량, 항이 있는 공식, 수치가 있는 인과 사슬)을 한 절로 압축**(**major**, 패처에게 interim이 받치는 깊이까지 전개하라고 지시), 소스 간 불일치를 뭉개 요약, interim이 직접 인용으로 뒷받침하는 주장에서 인용이 빠짐 → 질의가 이름 붙인 주제의 얕음은 major, 곁가지면 minor. `evidence`에 **반드시 interim 노트를 인용**. 초안이 완전히 무시한 interim은 호스트에 보고(깊이 패킷을 건너뛴 구조 문제). | 코드 확인 |
| R-10 | width 절차 | 질의의 모든 명사구·개체·범주를 뽑는다(분해가 아니라 이 목록이 근거) → `note list --tag <tag> --all -j`로 군집(태그·제목 키워드) → `temp/coverage-gaps.md`(있으면): 근거가 약한 원자 항목을 다루는데 출처 지지가 부족하면 지적, **조용히 통째로 생략했으면 critical** → 분해의 원자 항목 중 코퍼스 지지는 있는데 초안 처리가 없는 것이 최고 심각도 → 초안 섹션 훑기 → 격차 계산(주제 이탈·대체된 군집은 거름) → 그럴듯한 군집마다 노트 2~3개를 읽어 진짜 누락인지 판단 → 지적은 기존 섹션에 삽입할 문장·짧은 문단 또는 누락 각도를 인정하는 한정어이며 **새 섹션 전체는 안 됨**(필요하면 structural로 호스트에). 상한 = N(= width 상한 10)이고 커버리지 N−2 + bloat 2. **Bloat 점검(커버리지 점검 뒤)**: B1 내용 희석(반복·메타 서술·같은 논지를 다르게 재진술한 소절) → `major` finding 1개로 가장 약한 2~3개 구절을 지목하고 반복 논지·중복 소절·메타 서술을 줄이라 권고. B2 요약과 결론이 같은 키 구절 50% 초과 중복 → `minor`, 결론에 앞날 함의·전략 권고를 더해 차별화하라 권고. bloat finding은 최대 2개. | 코드 확인 |
| R-11 | instruction 절차 1 (준비) | ① 질의 파일을 읽고 모든 의미 있는 명사구·고유명사·기술 용어·범주 이름·명령형 동사("각 X에 대해 Y, Z를 포함")·형식 단서("마인드맵", "순위 목록", "FAQ")·하위 질문 표지("A? B? C?")를 목록으로 만든다. ② 분해 JSON이 같은 원자 항목을 담았는지 확인. 질의가 분명히 이름 붙인 것이 분해에 빠졌으면 `critical`(파이프라인이 잘못된 명세에서 시작). **2a**: 질의의 명사구마다 원자 항목이 있는지, 그 범위가 구절의 자연스러운 범위만큼 넓은지("SaaS applications"가 "POS SaaS"로 좁혀지면 안 됨) 확인해 좁혔거나 빠뜨렸으면 `failure_mode: "decomposition-gap"`, `critical`. | 코드 확인 |
| R-12 | instruction 절차 2 (구조 일치 검사, **먼저**) | `required_section_headings`가 비어 있지 않으면 가장 영향이 큰 검사다. 보고서의 최상위 H2를 줄 시작 `^## `로 모아 `required_section_headings`와 원소 단위로 비교하고, **불일치(누락·초과·순서 바뀜·문구 다름)마다 finding 하나**를 낸다: `{"severity": "critical", "atomic_item": "required_section_headings[<index>]: <기대 제목>", "failure_mode": "wrong-order", "location": "", "issue": "Expected H2 at position <N>: '<기대>'. Got: '<실제 또는 MISSING>'. Full heading diff: <두 배열>.", "requires_orchestrator_restructure": true}`. 이 finding은 **항상** `requires_orchestrator_restructure: true`(패처의 도구 잠금이 H2 이동·개명을 신뢰성 있게 못 하므로 호스트가 step 15 전에 처리). 비어 있으면 이 검사를 통째로 건너뛴다(서술형 프롬프트). | 코드 확인 |
| R-13 | instruction 절차 3 (항목별 내용 검사) | 분해의 원자 항목마다: 전용 섹션·문단·글머리표가 있는가, 형식을 지켰는가(순위 목록은 순위, FAQ는 Q-A, 표는 표), 프롬프트가 암시하는 순서를 지켰는가(A→B→C인데 B→A→C면 major), 깊이·구체성이 충분한가. finding에 `failure_mode`는 `missing`·`under-covered`·`wrong-order`·`wrong-format`. 형식 전체 교체(순위 목록 → FAQ)는 구조 문제로 `critical`이고 `issue`에 설명, 호스트에 에스컬레이션(패처 아님). `missing`은 무엇을 어디에 삽입할지 `recommendation`에. | 코드 확인 |
| R-14 | instruction 처방 구체성 | 질의가 권고·틀·규칙·지침을 요구하면 답은 증거가 뒷받침하는 한 **구체 임계값·수치·시간 창·비율·이름 붙은 메커니즘**을 담아야 한다. 권고형 주장마다 ① 구체 임계값 ② 이름 붙은 메커니즘 ③ 구체 수치가 있는지 본다. 없는데 볼트에 구체 버전을 받칠 증거가 있으면 `failure_mode: "vague-recommendation"` finding(추상 문구를 볼트 증거의 구체 문구로 바꾸라는 권고, 증거 인용). 증거가 구체를 뒷받침하지 않으면 `minor`이고 `issue`에 "vault does not contain quantitative evidence for this threshold"라 적어 패처가 수치를 지어내지 않게 한다. | 코드 확인 |
| R-15 | instruction 가독성 구조 점검 (개별 항목 점검 뒤) | R1 정의: 비전문가가 모를 기술 용어·약어·전문 용어가 3개 이상인데 첫 사용에 정의(괄호 또는 용어집)가 없다 → `missing-definitions`, `major`, 정의가 없는 용어를 지목하고 첫 언급에 괄호 정의 추가를 권고. R2 인용 밀도: 본문 인용 수(`## Sources` 제외, `[7, 12]`는 2건)를 세고 본문 단어 수(공백으로 단어를 나누지 않는 스크립트는 글자 수 ÷ 3)로 나눠 1000단어당 **9건 미만**이면 `low-citation-density`, `major`, 인용 없는 claim-dense 구절 5~8개를 짚고 볼트 소스 인용을 권고. R3 앞날 분석: `response_format == "argumentative"`이고 앞날 함의·추세·전략 전망을 다루는 섹션 또는 **200자 이상** 문단이 없다 → `missing-forward-analysis`, `major`. R4 비교 표: 3개 이상 개체를 2개 이상 차원으로 **산문으로만** 비교 → `missing-comparison-table`, `minor`. R5 섹션 입문: 주요 본문 섹션 2개 이상이 3~5문장의 평이한 입문 없이 평가·순위·밀도 높은 정량 분석으로 곧장 시작 → `missing-section-primers` **한 건**, `major`, 입문이 필요한 섹션과 가르칠 개념을 지목. R6 비교 축 커버리지: R4와 같은 트리거이고 분해의 커버리지 매트릭스·필수 항목이 이름 붙인 의사결정 차원을 보고서가 아예 생략하거나 한 줄 언급으로 압축 → `missing-comparison-dimensions` **한 건**, `major`, 누락·압축된 축마다 표의 행 하나 + 왜 중요한지 한 문장을 권고. R6는 **register와 무관**하게 적용한다. 이 가독성 구조 finding은 **합계 최대 3개**이고 `atomic_item` 접두사는 `readability-structural`. | 코드 확인 |
| R-16 | instruction 규칙 | 상한은 N(= 15) = 지시 이행 N−3 + 가독성 3, 우선순위 critical > major > minor. **원자 항목을 지어내지 않는다**: 모든 finding의 `atomic_item`은 `research_query` 또는 분해 JSON에서 글자 그대로 인용하고, 프롬프트가 이름 붙이지 않은 것은 width 비평가의 일이다. 권고는 최소 변경으로 수술적. register 조건: shim이 teach·survey를 지정하면 사용자 프롬프트가 요구하지 않은 확정 순위·판결을 요구하는 finding을 내지 않는다(커버리지 형태의 전달이 옳음). 프롬프트가 명시한 형식 단서는 register와 무관하게 이긴다. | 코드 확인 |
| R-17 | register 조건 (dialectic) | (depth·width 프롬프트에는 register 문단이 없고 공통 "Run directives" 안내만 있다.) shim이 teach·survey를 지정하면 쟁점에 대한 공평한 헤지 처리는 **옳다**(확정 입장의 부재가 아니라 견해의 불공정한 대표·설명 없는 메커니즘을 지적). advocate에서는 강한 반대 입장의 질이 핵심 기준이고 약한 반론은 critical. | 코드 확인 |

**step 14: 패처와 호스트**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | 티어 게이트 | light는 건너뜀(findings 없음). full 실행. 복구 입력: `scaffold.md`, `final_report_<tag>.md`, 존재하는 `critic-findings-*.json`, `temp/evidence-digest.md`(패처의 **주요 인용 출처**), `query.md`. | 코드 확인 |
| R-19 | 건너뛰기 경로(14.0) | 패처 spawn 전에 `research/runs/<tag>/skip-patcher.txt`가 있으면 호출자가 14 생략을 요청한 것이다. 이때 `patch-log.json`을 python으로 `{"total_findings": <존재하는 비평 파일의 findings 합>, "applied": [], "skipped": [{"reason": "patcher-skipped-by-invoker"}], "conflicts": [], "orchestrator_escalated": []}`로 쓰고 step 15로 간다. "대부분의 런은 이 게이트를 쓰지 않는다". | 코드 확인 |
| R-20 | 스텁 생성(14.1) | 패처는 Edit만 가능해 새 파일을 만들 수 없으므로 **호스트가 먼저** 정본 스텁(1.3 E)을 `echo … > patch-log.json`으로 쓴다. 스텁을 만들지 않으면 패처가 로그를 쓸 곳이 없어 결과 메시지에 인라인으로 돌려주고 감사 기록이 사라질 수 있다. | 코드 확인 |
| R-21 | 패처 spawn(14.2) | **한 번만** spawn. 입력 `draft_path`, `findings_paths`(critic 4개; light 분기 표기가 있으나 light는 14를 건너뜀), `patch_log_path`(스텁 있음), `evidence_digest_path`, 끝에 `shims/critics.md` 전문. 호스트는 **패처를 건너뛰고 직접 `final_report`를 Edit하지 않는다**(패처의 수술 규율·충돌 해결·"한정 통합" 규칙이 프롬프트에 있고 우회는 적대적 검토 구조를 무너뜨린다). 패처가 빈 결과를 돌려주면 한 번 재spawn하고 직접 하지 않는다(단 R-27 에스컬레이션 처리 제외). 같은 findings로 패처를 다시 spawn하지 않는다(findings를 수정한 경우만). | 코드 확인 |
| R-22 | 패처 불변식 | **쓰기 도구가 없다**(`Read, Edit`). 수술적으로 고치고 재생성하지 않는다. 한 finding이 섹션 전체 재작성을 요구하면 **finding을 기각**하고 호스트가 구조 문제로 처리하도록 보고에 적는다. 편집은 최소 변경: 한 문장을 더 나은 한 문장으로 바꾸는 것은 허용, 문단 전체를 바꾸는 편집은 재생성일 가능성이 높으니 쪼개거나 기각. 섹션 전체를 지우고 다시 입력하는 것은 "패치 옷을 입은 재생성"(Edit는 일치하는 `old_string`/`new_string` 쌍이면 받아주므로 도구 잠금이 막아 주지 않고 **패처가 편집 크기로 스스로 막는다**). | 코드 확인 |
| R-23 | 패처 절차 | ① 4개 findings를 읽어 평평한 목록으로 합치고 심각도순(critical → major → minor) 정렬, 없는 파일은 조용히 건너뜀. **사전 필터**: `requires_orchestrator_restructure: true` finding은 곧바로 에스컬레이션(`orchestrator_escalated`에 기록하고 넘어감). ② 각 finding의 `severity`·`location`·`issue`·`evidence`(볼트 노트가 실제 있는지 확인하고 환각이면 건너뜀)·`recommendation`을 읽는다. ③ **중복 제거**: 두 비평가가 같은 구절에 호환되는 권고를 하면 한 편집으로 합치고, 비호환이면 심각도가 높은 쪽을 택한다. ④ 보고서를 읽는다. ⑤ finding마다: `location`으로 구절을 찾고 `issue`·`recommendation`을 이해해 대상 영역에서 **유일한 `old_string`**(Read 출력에서 글자 그대로 복사)과 `new_string`을 만든다. 최소 편집(문장 삽입·주장 한정·구체 수치 추가), 증거는 권위 있는 산문으로 통합하고 기존 인용 스타일을 따른다. ⑥ 로그를 Edit로 채운다. 질의에 도움이 되지 않는 finding은 기각한다(질의가 이긴다). | 코드 확인 |
| R-24 | 패처 규칙 | critical부터 적용하고 **이유를 로그하지 않고는 critical을 건너뛰지 않는다**. Markdown 구조 보존(제목 수준, 번호 목록의 번호, 표 열 수 불변). 인용 스타일 일치: `wikilink`는 `[[<source-note-id>]]`, `inline`은 `[N]`, `none`은 마커 없음. | 코드 확인 |
| R-25 | 통합하라, 단서로 붙이지 말라 | 반대 증거 finding(특히 dialectic·width)은 **주장의 범위를 좁혀** 통합한다("X는 참" → "X는 유럽·북미에서 성립하고 중국에서는 Y 때문에 X가 적용되지 않는 다른 체제가 있다 [N]"). 확정한 주장 뒤에 "다른 체제에서는 다를 수 있다" 같은 헤지를 덧붙이는 **append-as-caveat는 금지**(되돌림처럼 읽히고 주장이 덜 구체적이 되며 polish가 어차피 지움). 차이: 범위 한정은 독자에게 "어디서 왜 참인지"를, caveat는 "작성자가 더 이상 확신하지 못한다"를 알려준다. | 코드 확인 |
| R-26 | 패치 로그 | 패처는 스텁의 키를 `Edit`로 채운다: `total_findings`(정수), `applied[]`·`skipped[]`(기각·건너뜀과 이유)·`conflicts[]`(두 비평가가 충돌해 하나를 고른 것)·`orchestrator_escalated[]`. 대체 스키마 금지. 코드(lint `patch-surgery`)가 읽는 필드는 `skipped[].severity`(`critical` 여부)와 `finding_id`·`critic`(메시지에 표시)뿐이다. 보고: 적용·건너뜀·충돌 개수, 로그 경로, 적용하지 못한 severity-critical finding(파이프라인을 막는 것이므로 호스트가 해결). | 코드 확인 |
| R-27 | 로그 판독(14.3) | 패처가 돌아오면: ① **critical이 skip됐는가** → 파이프라인 차단 요인이니 step 15 전에 호스트가 해결: (a) 보고서를 다시 읽고 finding을 부당하다고 기각, (b) 사용자에게 에스컬레이션, (c) 직접 Edit(호스트는 Write/Edit이 있고 잠금은 패처에게만 적용). ② 충돌이 있었는가 → 버려진 쪽이 더 중요했는지 검토. ③ "patch too large" skip이 있는가 → 비평가가 패치 옷을 입은 재생성을 제안한 것이다. critical이면 더 구체적인 제안으로 비평가를 재spawn하거나 작은 편집 여러 개로 호스트가 직접 처리. ④ 로그가 여전히 빈 스텁인가 → 패처가 로그를 못 썼으니 **결과 메시지에 인라인 로그**가 있다. 그 JSON을 파싱해 `patch-log.json`에 호스트가 Bash로 쓴다(하류 lint가 보도록). | 코드 확인 |
| R-28 | 구조 재편 에스컬레이션(14.4) | `orchestrator_escalated` 항목(대개 instruction critic의 제목 일치 finding)마다 호스트가: ① `issue`를 읽고 어느 H2를 옮기거나 추가·개명할지 이해, ② `final_report`에 **직접 Edit**(호스트는 Write·Edit 접근이 있음), ③ H2 안 본문은 보존(제목을 옮기고 개명하고 넣는 것이지 산문을 다시 쓰는 것이 아님. 새 제목에 본문이 필요하면 증거에 근거한 짧은 문단), ④ `orchestrator-restructure-log.md`에 변경 하나당 글머리표 한 줄(평문 마크다운), ⑤ 섹션 전체·초안 전체를 재생성하지 않는다("패치하되 재생성하지 않는다" 불변식은 호스트에도 적용, 더 넓은 도구이지 더 넓은 허가가 아님). | 코드 확인 |
| R-29 | 종료 조건 | `patch-log.json`이 있고 `total_findings`가 설정되고 `applied`·`skipped`·`conflicts` 중 하나 이상이 채워졌다. 모든 critical finding은 적용됐거나 호스트가 해결했다. 모든 `orchestrator_escalated`가 처리됐다(재편이 있었다면 `orchestrator-restructure-log.md`). `final_report`가 편집됐다(편집할 것이 없을 만큼 사소했다면 예외). 이후 step 14.5. | 코드 확인 |

**step 14.5: 인용 검사**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | 티어 | `full`·`dissertation`에서 실행. light는 건너뜀(인용 규모가 크지 않고 `quote-integrity`·`numeric-consistency`가 step 15 게이트에서 기계적으로 덮음). 14 **뒤**(패처가 텍스트와 인용을 옮겼으니 출고될 것을 검사)·15 **앞**(polish가 교정된 텍스트를 봄)에서 돈다. 목표: 이 검사가 덮는 모든 인용(모든 dangling, 수치 있는 모든 문장, 나머지의 표본)이 문장을 뒷받침하거나 고쳐진다. | 코드 확인 |
| R-31 | 추출·기계 분류(14.5.1) | `hyperresearch citecheck extract <tag> -j` 한 번. 보고서에서 `[N]`(묶음 `[7, 12]`은 소스 번호마다 한 쌍)과 `[[note-id]]` 스타일의 (문장, 인용) 쌍을 모두 뽑고, 인용된 노트의 추출 클레임이 이미 확인해 주는 쌍만 **자동 통과**시킨다: 2자리 이상 수치가 있는 문장은 클레임·인용 하나와 **전체 일치**해야 하고(수치만 같으면 다른 개체·지표일 수 있어서), 수치 없는 문장은 6단어 이상의 긴 단어 연속 일치로 통과. 한 자리 숫자("Step 1", "GPT-4"의 4)는 레이블이라 수치가 아니다. 산출 `cite-check-pairs.json`: `summary`(total·auto-passed·dangling·needs-llm), `sampled_for_llm`(수치 있는 문장은 100%, 나머지는 표본), `dangling`(어느 볼트 노트에도 해석되지 않는 인용과 `unresolved` 사유·`marker`). 알고리즘은 행 10 소유. | 코드 확인 |
| R-32 | dangling 처리 | 에이전트 없이 호스트가 **사유별로**: `no-sources-entry`(`[N]`에 Sources/References의 `[N]` 줄이 없음)와 `unknown-note-id`(`[[note-id]]`가 볼트 노트를 가리키지 않음)는 각각 `critical` finding(조작·훼손된 인용). `unresolved-entry`(Sources 항목은 있는데 URL·제목이 어느 볼트 노트와도 안 맞음)는 **조회 실패이지 인용에 대한 증거가 아니다**: 먼저 `search "<특징적 제목 단어>" -j`와 `note show`로 그 작업이 맞는지 확인해 볼트에 있으면 인용은 유효하고 finding 없음. 볼트에 그런 소스가 없을 때만 `major` finding(볼트가 뒷받침 못 하는 인용). | 코드 확인 |
| R-33 | 빈 경우 | `sampled_for_llm`이 비어 있고 dangling도 없으면 `cite-check-findings.json`에 `[]`를 쓰고 `run step <tag> 14.5 --status done -j`를 기록한 뒤 step 15로 간다(에이전트·2차 패치 없음). | 코드 확인 |
| R-34 | cite-checker spawn(14.5.2) | 하나를 spawn한다(`sampled_for_llm`이 **약 40쌍을 넘으면** 색인 범위를 나눠 2개 동시). 프롬프트: 질의 원문·`QUERY FILE`·`PIPELINE POSITION`(14.5, 패처가 이미 비평 finding을 적용, 보고서를 직접 고치지 않음)·입력 `pairs_file`·`your_range`(`sampled_for_llm[<start>..<end>]`)·`findings_path`·`vault_tag`. **shim 없음.** 2개로 나누면 각자 `cite-check-findings-a.json`/`-b.json`을 쓰고 호스트가 배열을 병합해 `cite-check-findings.json`을 만든다. | 코드 확인 |
| R-35 | cite-checker 판정 | 쌍마다 `note show <note_id> -j`로 인용된 노트 본문을 읽고(연속 쌍이 서로 다른 노트를 인용하면 호출 하나에 최대 5개 id) **문장이 쓰인 그대로** 노트가 뒷받침하는지 판정한다: `supported`(노트가 문장의 주장을 수치까지 진술하거나 직접 함의), `partially-supported`(요지는 맞으나 규모·한정어·범위가 다름), `unsupported`(노트에 근거 없음), `wrong-source`(다른 볼트 노트가 뒷받침: `claims search "<핵심 구절>" -j`로 찾아 `correct_note_id`에 지명). **주장이 사실인지가 아니라 이 소스가 그렇게 말하는지**만 본다. 기본은 회의적: 근거를 못 찾으면 unsupported이고 "아마 괜찮다"는 없다. `supported`가 아닌 것만 finding이 되고 모두를 **JSON 배열 하나**로 `findings_path`에 쓴다(1.3 F 형식). 심각도: 수치 있는 unsupported와 `wrong-source`는 `critical`, 그 밖은 `major`. 모두 통과했으면 `[]`. 이미 기계적으로 자동 통과한 쌍은 다시 따지지 않는다. 마지막 메시지는 판정별 개수와 파일 경로(데이터, 산문 아님). | 코드 확인 |
| R-36 | 2차 패처 패스(14.5.3) | dangling findings를 `cite-check-findings.json`에 덧붙인 뒤(병합 파일에 호스트가 직접) step 14 장치를 **그대로 재사용**: 패처 **하나**를 `findings` 입력 = `cite-check-findings.json`, `cite-check-patch-log.json`을 정본 스텁(1.3 E와 같은 모양)으로 미리 만들어 spawn. 수정 레퍼토리(findings의 `suggested_fix`): `correct_note_id`로 **인용 교체**, 소스가 뒷받침하는 수준으로 **주장 완화**, 아무것도 뒷받침하지 않으면 **문장 삭제**. 규칙은 step 14와 같다: 수술적 hunk, 재생성 금지, `critical`을 조용히 건너뛰지 않는다. **병합된 findings가 `[]`이면 패스를 통째로 건너뛴다.** | 코드 확인 |
| R-37 | 종료·기록 | `cite-check-pairs.json`이 있고 `cite-check-findings.json`이 있다(`[]` 가능). findings가 비어 있지 않았다면 `cite-check-patch-log.json`이 모든 `critical`을 적용 또는 에스컬레이션으로 기록. `run step <tag> 14.5 --status done -j`. `done` 기록이 있으면 `run finish`가 `cite-check-resolved`를 검사한다(R-62). 이후 step 15. | 코드 확인 |

**step 15: polish**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-38 | 티어·스텁 | **모든 티어**에서 실행. 입력: 패치된 `final_report_<tag>.md`(light는 단일 초안), `query.md`. 스텁 `echo '{"applied": [], "escalations": []}' > polish-log.json`을 호스트가 먼저 만든다(감사기는 새 파일을 못 만듦). 스텁이 없으면 감사기는 **멈추고 호스트에 보고**한다(호스트가 다시 스텁하고 재시도). | 코드 확인 |
| R-39 | spawn | 한 번. 입력 `draft_path`, `polish_log_path`, `wrapper_contract_path`(**`research/wrapper_contract.json`이 존재할 때만** 포함, 프론트매터 유지 여부를 알려 주는 유일한 경로). 끝에 `shims/polish.md`. "마지막 편집 패스, 이후는 step 16 가독성 감사(선택 적용)와 ship gate". 호스트는 감사기를 우회해 직접 polish하지 않는다(빈 결과면 재spawn, 에스컬레이션 처리 때만 직접). | 코드 확인 |
| R-40 | 1 위생 누출 (모두 **critical**, 해당 블록을 통째로 삭제하는 Edit) | 초안에 없어야 한다: C-13의 스캐폴드 전용 섹션 머리 10개 접두사(`## User Prompt (VERBATIM`, `## Canonical research query source`, `## Session wrapper requirements`, `## What the user explicitly asked for`, `## Prompt decomposition`, `## Primary activity and secondary flavor`, `## The structural plan`, `## Where each source will land`, `## Citation budget`, `## Coverage checklist`), 파일 맨 위 YAML 프론트매터(wrapper 계약이 요구하면 예외), 프롬프트 에코("User prompt:", "The query is:"), 제목 둘레의 남은 백틱, "Here is the report:"/"Below is the draft:" 서문 줄. **verbatim이 아닌 따옴표**: 따옴표는 소스의 글자 그대로 인용에만 쓴다. 수사적 프레이밍·바꿔 쓰기·가상의 반론·보고서 자체의 조어("the scaling wall")를 따옴표로 감싸면 안 되며 평문이나 이탤릭으로 다시 쓴다(**ship gate가 볼트에서 글자 그대로 찾을 수 없는 따옴표 구간을 기계적으로 거부하므로** 장식용 인용 하나가 게이트 실패). **인용 통과**: 모든 `[N]` 인라인 인용과 Sources/References 섹션을 작성자가 쓴 그대로 둔다. 허용되는 **유일한 인용 편집**: 인접 묶음 `[3][4][5]`을 `[3, 4, 5]`로 합치기(번호 그대로, 삭제·재번호 없음). | 코드 확인 |
| R-41 | 1a 프론트매터 위생 (wrapper 계약이 프론트매터를 **요구**할 때만) | 제자리에서 고친다: `title: Untitled` → 본문 첫 H1 텍스트(앞 `# ` 제거), `status: draft` → `status: evergreen`, `summary:`가 "Hyperresearch final report:"·"Layer 4 output:" 같은 파이프라인 어휘로 시작하면 H1과 첫 확정 주장 문단으로 다시 쓰기(파이프라인 이름이 독자 대상 필드에 나오면 안 됨), `summary:`가 `...`로 잘렸으면 보고서 논지의 한 문장 설명으로 완성. wrapper 계약이 없거나 요구하지 않으면 블록 전체를 삭제(R-40). | 코드 확인 |
| R-42 | 1b 인라인 스캐폴드 어휘 제거 (모두 critical, **의미 재작성 Edit**, 리터럴 치환 아님) | 목록은 **닫혀 있다**(새 패턴을 즉석에서 추가하지 않는다). 설치된 정규식과 전략: `\bLocus\s+\d+\b` → 그 locus가 다룬 실질 주제로 이름 붙임("Locus 3" → "the 500K-passenger threshold question"). `\bTension\s+\d+\b` → 실제 역학 서술("the isolation-versus-competition question"). `comparisons\.md` / `research/comparisons\.md` → 파일 경로 참조 삭제, 실질 문장은 보존. `committed\s+(reading\|position)` → "the argument this report commits to" 또는 삭제 후 다음 문장이 서게. `cross[- ]locus` → "across the evidence clusters" 또는 삭제하고 실질을 직접 진술. `\bwidth\s+corpus\b` → "the literature surveyed"/"the source base". `\bdepth\s+investigation\b` → "the detailed analysis on <주제>". `(per\|from)\s+the\s+scaffold` → 통째로 삭제. `hyperresearch(\s+final\s+report)?` → 통째로 삭제(파이프라인 이름을 독자에 노출하지 않음). `\[?\[?interim[-_]report[-_]` / `\[I\d+\]` → 작업공간 산출물 참조이므로 R-43 처리. 독립 단어 `\bloci\b`: 분자생물학·법·신경과학의 정당한 도메인 용어면 그대로 두고(`genetic locus`, `legal locus`), "three loci converge", "the fidelity locus", "across loci"처럼 파이프라인 내부 분류를 가리킬 때만 재작성("three separate lines of inquiry converge…"). 작업 사례 4개는 C-12. | 코드 확인 |
| R-43 | 1c 파이프라인 참조 정리 | `[[interim-*]]` 위키링크와 `[I\d+]`는 독자용 소스 노트가 아니라 작업공간 산출물을 가리키는 **누출**이다. `citation_style`에 따라 변환·삭제한다: `wikilink` → 그 interim이 인용하던 **가장 관련 높은 소스 노트의 `[[<source-note-id>]]`**(interim의 frontmatter·첫 인용 소스를 읽어 확인), `inline` → Sources 목록의 맞는 `[N]`, `none` → 완전히 삭제. 독자용 `[[<source-note-id>]]`(대상이 interim·scaffold 산출물이 아니라 볼트의 실제 소스 노트)는 `wikilink`에서 **보존**(인용 체계이지 누출이 아님). `inline`에서는 `[N]`으로 변환, `none`에서는 삭제. 독자용 `[N]`과 Sources 섹션은 손대지 않는다. | 코드 확인 |
| R-44 | 2 프롬프트 준수 | `research_query`를 읽고 초안이 요청한 것을 전달했는지 본다. 불일치 처리: 사용자가 N개를 요구했는데 초안이 그보다 적게 다룸 → **범위 한계를 알리는 한정어**를 추가(항목을 지어내지 않음). 사용자가 특정 형식(FAQ·순위 목록·표)을 요구했는데 초안이 다른 형식 → polish 로그에 불일치를 적고 형식 전환은 polish Edit에 너무 크니 **에스컬레이션**. 사용자가 권고를 요구했는데 초안이 서술만 → 에스컬레이션하고 polish에서 권고를 지어내지 않는다. | 코드 확인 |
| R-45 | 3 필러·중복·메타 담화 | 정보를 더하지 않는 필러 구절을 삭제("It is worth noting that…", "Importantly, …", "It should be mentioned that…", "Notably, …", "Of course, …", "In essence, …"). 직전 문장을 재진술하는 문장을 삭제(문단 끝에서 앞 두 문장을 요약하는 문장은 대개 삭제). **메타 담화(최우선, 기계 문체의 대표 표지)**: 보고서·섹션이 무엇을 하는지 서술하는 절을 삭제("This report examines/evaluates/turns to…", "This section maps/covers/addresses…", 같은 점을 곧바로 다시 말하는 곳의 "As noted above/as discussed in section N"(서술을 자르고 재진술은 보존), "a caveat developed in section 10"/"declared up front so the analysis can return to them", "The interpretive point the sources do not make:" 같은 프레임(프레임만 자르고 해석은 남김), 보고서의 자기 산문을 묘사하는 형용사("a brief overview", "this concise assessment")). 수정은 삭제 또는 최소 이어붙임이다("This section maps the four strategies. The first is X…" → "The first strategy is X…"). 정말 하중이 있는 교차 참조는 섹션 번호가 아니라 주제로("the yield question, below"). | 코드 확인 |
| R-46 | 3a 헤지 문구 (register 가드) | shim이 teach·survey를 지정하면 확정을 강제하는 규칙은 **건너뛰고** 헤지 쌓기 규칙만 적용한다(쟁점에 대한 공평한 헤지 어법이 옳음). advocate에서는 최대 강도로 적용. 기본(analyze)에서: 같은 문단의 증거가 더 강한 주장을 뒷받침하는데 붙은 약화 표현을 삭제한다: `suggests that`(인용 증거가 이미 직접 뒷받침하는 결론 앞: "Data X suggests Y" → "Data X shows Y" 또는 다음 절이 이미 단정이면 "suggests that" 삭제), `may`·`might`·`could`(문단이 이미 낸 결론의 헤지: "The evidence may indicate…" → "The evidence indicates…", 증거가 같은 문장·문단에 있을 때), `appears to`·`seems to`·`tends to`(주변 인용이 뒷받침하면 삭제: "X tends to cause Y [3][5]" → "X causes Y [3][5]"), **희석하는 덧붙임 단서**(확정 주장 뒤에 "though this may resolve differently in other regimes"를 다른 체제와 이유를 **이름 붙이지 않고** 붙인 것: 삭제하거나(주장이 서 있을 만큼 강하면) 한정이 필요하다고 호스트에 에스컬레이션하되, 맨 "may be different" 헤지를 초안에 남기지 않는다), **헤지 쌓기**("may potentially indicate", "could arguably suggest")는 최대 하나(또는 증거가 맨 주장을 뒷받침하면 0개)로 붕괴. 진짜 추측적 주장(데이터 없는 예측, 열린 질문, 증거가 논쟁적인 곳)의 헤지는 정직이므로 남긴다. | 코드 확인 |
| R-47 | 4 반복 섹션 | 서로 다른 섹션에서 같은 말을 두 번 하는 문단·글머리표는 약한 쪽을 삭제(섹션 전체 병합은 재생성이라 금지). **4a 요약 ↔ Opinionated Synthesis 중복 제거(높은 우선순위)**: 요약이 핵심 결론 3~4개를 말하고 종합이 거의 같은 문구로 다시 말하는 것이 가장 흔한 반복이다. 두 섹션이 핵심 구절·논지를 공유하면 종합을 **요약을 넘어 논증을 진전시키도록** 고친다(구체 권고, 앞날 함의, 요약에 없던 결정 기준 추가). 종합이 요약 이상을 더하지 않으면 중복 문단을 삭제하고 고유한 것(전략 권고, "what would change my mind", 결정 틀)만 남긴다. **요약은 자르지 않는다**(독자가 먼저 본다). | 코드 확인 |
| R-48 | 5 가독성 | 문장이 약 **50단어**를 넘으면 둘로 쪼갠다. 문단이 약 **200단어**를 넘으면 자연스러운 경첩에서 둘로 쪼갠다. 인접 인용 괄호 `[3][4][5]`는 `[3, 4, 5]`로 합치되 묶음이 3개를 넘으면 임의로 빼지 말고 에스컬레이션한다. | 코드 확인 |
| R-49 | 절차·규칙·로그 | 보고서를 끝까지 읽고 다섯 범주(위생 / 프롬프트 준수 / 필러·중복 / 반복 / 가독성)에서 문제를 모은다 → 문제마다 최소 Edit(대개 순문자 수가 **음수**: 자르는 일이지 더하는 일이 아님) → 적용 순서: **위생(critical) → 프롬프트 준수 조정(major) → 필러·중복(minor) → 가독성 쪼개기(minor)** → 로그를 `old_string='"applied": []'`의 Edit로 채움(escalations도 같은 방식). 규칙: 내용을 **지어내지 않는다**(제거·압축·가벼운 바꿔 쓰기만, 초안에 없던 주장 추가 금지), 구조 불일치는 **에스컬레이션**(형식 불일치를 polish Edit로 강제하지 않음), Sources 목록은 손대지 않음, polish 뒤 순길이가 앞보다 **같거나 짧아야** 한다(늘어나면 잘못된 일을 하는 것이니 멈추고 에스컬레이션). 보고: 범주별 적용 편집 수, 순 글자 수 차이, 에스컬레이션 목록. | 코드 확인 |
| R-50 | 호스트 에스컬레이션 처리(15.3) | 로그의 `escalations`를 읽는다. 구조 문제(예: "순위 목록을 요구했는데 초안이 순위 없는 산문")면 호스트에게 **한 번의 기회**가 있다: 직접 hand-written Edit로 재편하고 출고한다. **순 길이 점검**: polish 로그가 양의 순 글자 추가를 보이면 잘못된 것이다(polish는 자르는 단계). 감사기가 빈 결과를 돌려주면 재spawn하고 호스트가 직접 하지 않는다. | 코드 확인 |
| R-51 | 최종 무결성 게이트(15.4) | 티어별 필수 산출물이 있는지 확인한다: **light**는 `polish-log.json`만(12~14가 건너뛰어 critic·patch 로그가 없음). **full**은 critic findings 4개 + `patch-log.json` + `polish-log.json`(`test -f`로 `MISSING:` 출력). 빠진 것은 책임 에이전트를 **한 번** 재spawn해 누락 출력 경로를 명시적으로 요구한다. 두 번째에도 실패하면 **최소 스텁**(critic 파일은 `{"findings":[]}`, patch·polish 로그는 정본 빈 로그)을 쓰고 실행 로그에 실패를 적은 뒤 진행한다. | 코드 확인 |
| R-52 | 실행 기록·lint 사전 점검(15.5) | ① `research/runs/<tag>/audit_findings.json`에 `{"mode": "hyperresearch-v8", "run_id": <ISO 시각>, "loci_count": K, "critical_findings_applied": int, "critical_findings_skipped": int, "polish_escalations": int, "final_word_count": int}`를 덧붙인다(컨테이너 모양은 원문에 없음). ② `lint --rule wrapper-report --json`, `--rule locus-coverage`, `--rule scaffold-prompt`, `--rule patch-surgery`를 돌린다. `error` 심각도가 나오면 처리: `wrapper-report`(스캐폴드가 본문에 샘) → 특정 누출을 지적해 polish 감사기를 재spawn, `locus-coverage`(step 4 locus에 interim 노트 없음) → 재실행하지 말고 실행 로그에 기록, `scaffold-prompt`(scaffold의 User Prompt가 질의 파일과 다름) → scaffold를 고침, `patch-surgery` → 패치 로그를 읽고 조사. 이 4개는 **사전 점검**이고 **구속력 있는 게이트는 `run finish`**다(진입 스킬 종료 단계, 인용문·철회 점검 포함). 게이트 오류는 보고서에 대한 사실이며 오탐으로 분류하지 않는다. **장식용 인용의 해법은 따옴표를 지우는 것이지 변명 메모가 아니다.** | 코드 확인 |
| R-53 | 종료·출고 | `polish-log.json`이 채워졌고, 최종 무결성 게이트가 통과(또는 문서화된 실패로 스텁), lint 게이트 통과. 최종 보고서는 `research/notes/final_report_<tag>.md`이고 wrapper가 요구하는 별도 저장 경로가 있으면 그것은 별도 사본으로 wrapper 계약에 따라 처리한다. 이후 step 16. | 코드 확인 |

**step 16: 가독성 감사**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-54 | 티어·spawn | **모든 티어**에서 실행(작은 구조 변경이 큰 점수 이득을 주는 차원). 추천기를 **한 번** spawn: 입력 `draft_path`(`final_report_<tag>.md`), `recommendations_path`(`readability-recommendations.json`), 끝에 `shims/polish.md` 전문, 지시 "추천을 JSON 객체(`recommendations` 배열 + `summary`)로 쓰고 `readability_rec_cap`(full 50)개를 넘지 않게 영향순으로". 추천기는 보고서를 수정하지 못한다(`Read, Write`). 분리 이유: Edit 기반 재포맷기는 흐르는 문단을 글머리표로 바꾸거나 별개 하위 주제를 합치는 등 논증을 해치는 편집을 했으므로 추천기의 패턴 매칭과 호스트의 판단을 분리했다. | 코드 확인 |
| R-55 | 추천기 범주와 임계값 | 우선순위 순: ① **merge-paragraphs(최우선)**: 인접 문단이 각각 CJK 200자 / EN 300자 미만이고 같은 하위 주제면 병합(목표 문단 길이 CJK 300~600자 / EN 500~1000자). 하위 주제 경계를 넘어 병합하지 않는다. 대체문에 필요하면 전환어를 넣는다. ② **break-paragraph**: CJK 800자 / EN 1500자를 넘는 문단은 자연스러운 경첩(하위 주제 이동·전환·증거→해석)에서 분할. ③ **make-list**: 3개 이상 항목이 산문에서 순차 서술되면 글머리표로(범주어로 시작하면 굵은 레이블 권고). 흐르는 논증 산문은 대상 아님. ④ **make-table**: 3개 이상 개체를 2개 이상 차원으로 산문 비교하면 표(헤더·행 제안). ⑤ **bold-keyterms**: 목록 항목·문단이 굵지 않은 핵심 용어·통계·범주 레이블로 시작하면 굵게. ⑥ **split-sentence**: 문장이 중국어 80자 / 영어 150자를 넘으면 자연스러운 접속사·세미콜론에서 분할. ⑦ **remove-hr**: 섹션 사이 `---` 줄을 모두 삭제(`recommended`는 `""`). ⑧ **add-whitespace**: 문단 사이·목록·표·인용문 둘레의 빈 줄 보장. | 코드 확인 |
| R-56 | 추천기 규칙 | 실질 내용을 **추가하지 않는다**(재포맷만, 논증·증거는 `recommended`에서 그대로). 실질 내용을 **삭제하자고 하지 않는다**(문장이 길면 분할이지 증거 삭제 아님). **H2 제목 텍스트를 바꾸자고 하지 않는다**(섹션 구조는 synthesizer 소유, 섹션 **안**의 변경만). **여는 논지 문단은 건드리지 않는다**(하중 있음). **기존 표를 건드리지 않는다**(새 표만). 상한 `readability_rec_cap`. 비ASCII(CJK·아랍·키릴) 텍스트는 `current`를 Read 출력에서 **글자 그대로 복사**한다(다시 입력하면 글자가 깨지는 것이 1번 실패 모드이고 호스트의 Edit가 정확 일치를 요구한다). 보고: 경로, 총 개수, 범주별, 최고 심각도 한 문장, 모두 적용했을 때 예상 순 글자 차이, 검토했으나 표시하지 않은 섹션. | 코드 확인 |
| R-57 | 호스트 선택 적용(16.3) | **확신하고 적용**: `merge-paragraphs`(인접 문단이 분명 같은 하위 주제, rationale이 확인), 1500 EN / 800 CJK자 초과 문단의 `break-paragraph`, 모든 `remove-hr`, 모든 `add-whitespace`(위험 0), `make-table`(산문 비교가 3개 이상 개체 × 2개 이상 차원을 인용하고 제안 표가 모든 비교점을 보존). **판단하고 적용**: `make-list`(산문이 실제 열거형(순차 3개 이상 항목)인지 확인. rationale이 "항목이 흐르는 산문 속에 순차로 나온다"이면 목록 후보가 **아님**, 건너뜀), `bold-keyterms`(진짜 핵심 용어인지, 하중 있는 개념·통계만 굵게, 과잉 금지). **회의적으로(대개 건너뜀)**: 강조·리듬을 위한 문장 길이를 가진 논증 산문의 `split-sentence`, 여는 논지 문단을 건드리는 추천, 기존 표를 바꾸는 추천. **항상 건너뜀**: `current`가 실제 초안과 일치하지 않는 추천(추천기가 닻을 잘못 잡음: 기록하고 무시), H2 제목 텍스트를 바꾸는 추천, 실질 내용을 삭제하는 추천. 모든 추천을 적용할 의무는 없다. | 코드 확인 |
| R-58 | 적용 방법·순서(16.4) | 각 추천: 보고서에 Edit를 하며 `old_string` = 추천의 `current`(추천기가 쓴 그대로), `new_string` = `recommended`(비ASCII도 다시 입력하지 않음). **순서**: ① `remove-hr` ② `merge-paragraphs`·`break-paragraph` ③ `make-list`·`make-table` ④ `bold-keyterms`(병합·분할을 거친 문단 안) ⑤ `split-sentence`(확정된 문단 안) ⑥ `add-whitespace`. Edit가 `old_string` 불일치로 실패하면 **그 추천을 건너뛰고** 나머지를 계속한다(`edit_failures`에 기록). | 코드 확인 |
| R-59 | 결정 로그(16.5) | 호스트가 `readability-decisions.json`을 Write로 쓴다(1.3 H). 감사 기록: 나중에 가독성 문제가 발견되면 "검토하고 건너뛰었는지, 아예 못 봤는지"를 이 로그가 보여 준다. `net_char_delta_actual`은 실제로 측정한다. | 코드 확인 |
| R-60 | 종료 조건 | `readability-recommendations.json`이 있고, `readability-decisions.json`이 있으며 `applied`에 하나 이상이거나 전부 `skipped`이고, 보고서가 적용된 추천을 반영하고, **보고서의 구조(H2 목록·요약·결론)가 step 15 출력과 같다**(이 단계는 구조를 바꾸지 않는다). 이후 진입 스킬 ship gate(`sources retractions --tag <tag>` → `run finish`, 최대 3라운드)로 간다. | 코드 확인 |

**단계 사이의 공통**

| ID | 조건 | 결과 | 검증 수준 |
|---|---|---|---|
| R-61 | 수술적 편집 불변식(12~16 전체) | 최종 보고서는 step 11(light는 step 10) 이후 **Edit hunk로만** 바뀐다: 패처(14·14.5.3), polish 감사기(15), 호스트의 구조 재편·에스컬레이션 처리·로그 복구(14.4·15.3), 호스트의 가독성 선택 적용(16). 재작성·재합성 금지(예외: `draft-synthesis.md` R-42·R-43의 길이 압축 1회). 비평가의 지적이 섹션 전체 재작성을 요구하면 호스트에게 구조 이슈로 올리고 다시 쓰지 않는다. | 코드 확인 |
| R-62 | ship gate와의 접점(경계) | `run finish`는 필수 단계 집합에 12와 14가 모두 있으면 critic 4개·`patch-log.json`의 존재를, 15가 있으면 `polish-log.json`의 존재를 검사하고(light 선언이면 검사 없음), 14.5가 `done`으로 기록된 경우에만 `cite-check-resolved`(findings 존재·JSON 유효·`critical`이 있으면 `cite-check-patch-log.json` 존재)를 검사한다. 검증 배터리(`quote-integrity`·`retracted-citations`)가 실패하면 보고서를 고친다(따옴표 제거·철회 명시)는 규칙은 `run-manifest-gate.md` R-33이 소유한다. | 코드 확인 |

- 불변식: 비평가·cite-checker·추천기는 보고서를 수정하지 않는다(Write로 자기 JSON만). 패처·polish 감사기는 `Read, Edit`라서 기존 파일의 일부 교체만 하고 새 파일을 만들 수 없다(그래서 호스트가 로그 스텁을 만든다). 호스트의 직접 편집은 위 R-61의 열거된 경우뿐이다. 로그 파일 이름은 S1 표(`run-manifest-gate.md`)와 같다.
- 미결정: 없음.
- 확인 한계: 코드를 실행하지 않았다. 모든 규칙은 호스트 LLM과 서브에이전트가 프롬프트를 따를 때만 성립하며 코드가 강제하는 것은 `verify_run`의 존재·형식 검사와 `citecheck extract`·`lint` CLI 동작뿐이다. 패치 로그 `applied[]`·`conflicts[]`·`orchestrator_escalated[]` 항목 내부 필드는 원문이 정하지 않았고 어느 코드도 읽지 않아(`skipped[]`의 `severity`·`finding_id`·`critic` 제외) 구현자가 정해도 외부에서 관찰되는 결과가 바뀌지 않는다. `audit_findings.json`의 컨테이너 모양(리스트인지 `{"runs": []}`인지)도 원문에 없지만 v8 기록(`mode: "hyperresearch-v8"`)은 `audit-gate` 규칙이 보는 `mode ∈ {conformance, comprehensiveness}`가 아니라서 어느 모양이든 게이트에 영향이 없다. 기계 분류 알고리즘과 lint 규칙 내부는 행 10이 소유한다.

### 1.5 필수 코드 참조 [필수]

원문 프롬프트는 MIT 라이선스(overview 1절)로 인용 가능하다. 범위는 모두 프롬프트 텍스트이고 `<< >>`·`<% %>` 빈칸은 설치 시 렌더링된다. 위 R-ID 표는 임계값과 형식을 옮겼고, 아래는 원문이 더 정확한 부분이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/hyperresearch/skills/hyperresearch-12-critics.md:11-79` | step 12 전체: 4 비평가 spawn 템플릿, 실패 처리, 종료 조건 | R-01~R-05 |
| C-02 | `src/hyperresearch/core/hooks.py:641-755` · `DIALECTIC_CRITIC_AGENT` | dialectic 절차, 출력 스키마, 규칙, 보고 | R-06~R-08, R-17 |
| C-03 | `src/hyperresearch/core/hooks.py:775-874` · `DEPTH_CRITIC_AGENT` | depth 절차와 규칙 | R-06, R-09 |
| C-04 | `src/hyperresearch/core/hooks.py:893-1026` · `WIDTH_CRITIC_AGENT` | width 절차, 규칙, bloat B1·B2 | R-06, R-10 |
| C-05 | `src/hyperresearch/core/hooks.py:1053-1354` · `INSTRUCTION_CRITIC_AGENT` | instruction 절차 1~5, 구조 일치 finding 예시 JSON, 심각도, 처방 구체성 예시, 가독성 점검 R1~R6, 규칙 | R-11~R-16 |
| C-06 | `src/hyperresearch/skills/hyperresearch-14-patcher.md:34-165` | skip 경로(python 코드), 스텁 명령, spawn 템플릿, 로그 판독, 에스컬레이션 처리, 제약, 종료 조건 | R-18~R-21, R-27~R-29 |
| C-07 | `src/hyperresearch/core/hooks.py:1378-1532` · `PATCHER_AGENT` | 패처 불변식, 입력, 절차, 규칙, "통합하라, 단서로 붙이지 말라", 보고 | R-22~R-26 |
| C-08 | `src/hyperresearch/skills/hyperresearch-14-5-cite-check.md:15-99` | 14.5 전체: extract, dangling 사유별 처리, spawn, 2차 패치, 종료 | R-30~R-37 |
| C-09 | `src/hyperresearch/cli/citecheck_cmd.py:15-78` · `citecheck_extract`, `src/hyperresearch/core/citecheck.py:329-371` · `sample_needs_llm`, `write_pairs_file` | CLI 옵션·출력, 표본 추출(수치 문장 100%, 수치 없는 문장 `sample_rate`)과 쌍 파일 구조. 쌍 추출·기계 분류 알고리즘 자체는 행 10 | R-31 |
| C-10 | `src/hyperresearch/core/hooks.py:3494-3562` · `CITE_CHECKER_AGENT` | 판정 4종, findings 항목 JSON, 심각도, 규칙 | R-35 |
| C-11 | `src/hyperresearch/skills/hyperresearch-15-polish.md:13-171` | step 15 전체: 스텁, spawn 템플릿, 에스컬레이션, 통합 게이트(bash 루프), 기록·lint | R-38~R-39, R-50~R-53 |
| C-12 | `src/hyperresearch/core/hooks.py:1555-1899` · `POLISH_AUDITOR_AGENT` | polish 규칙 전문: 위생(1·1a·1b 표와 작업 사례·1c), 프롬프트 준수, 필러·메타 담화, 헤지 문구(register 가드), 반복(4a), 가독성, 절차·로그 스키마·규칙. 설치 시 `{scaffold_only_sections}`에 C-13을 채움 | R-40~R-49 |
| C-13 | `src/hyperresearch/core/hooks.py:105-123` · `SCAFFOLD_ONLY_SECTION_HEADERS`, `_render_scaffold_only_bullets`, `:4123-4132` | 스캐폴드 전용 섹션 머리 10개(접두사 일치). lint도 같은 상수를 쓴다 | R-40 |
| C-14 | `src/hyperresearch/skills/hyperresearch-16-readability-audit.md:16-181` | step 16 전체: spawn 템플릿, 선택 적용 휴리스틱, 적용 순서, 결정 로그 형식 | R-54, R-57~R-60 |
| C-15 | `src/hyperresearch/core/hooks.py:2565-2755` · `READABILITY_REFORMATTER_AGENT`(이름 `hyperresearch-readability-recommender`) | 범주 8개와 임계값, 추천 JSON 스키마, 비ASCII 복사 규칙, 규칙 | R-55, R-56 |
| C-16 | `src/hyperresearch/core/profiles.py:300-303`, `:367-370`, `:409-411` | `critic_finding_caps`, `gap_fetch_cap`, `readability_rec_cap` 값(full·premier·dissertation) | 1.3 I |
| C-17 | `src/hyperresearch/cli/lint.py:1200-1296` · `patch-surgery` 규칙 | 패치 로그를 읽는 필드와 빈 로그 경고(규칙 판정 본문은 행 10) | R-26, R-27 |

### 1.6 수락 사례 [필수]
출처: 모두 구현(프롬프트 텍스트·CLI)에서 도출. 호스트·서브에이전트는 LLM이므로 아래 기대 결과는 프롬프트를 지킨 실행의 관측 결과이며, 코드가 강제하는 사례(T-05·T-07·T-12)를 표시했다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-12 | `required_section_headings = ["## 1. 개요", "## 2. 비교", "## 3. 전망"]`, 보고서의 H2 순서가 개요·전망·비교 | instruction critic이 위치 2·3에 각각 finding(`critical`, `failure_mode: "wrong-order"`, `requires_orchestrator_restructure: true`, `location: ""`). 패처는 이들을 `orchestrator_escalated`에 기록하고 건드리지 않으며, 호스트가 14.4에서 H2를 옮기고 `orchestrator-restructure-log.md`에 기록 |
| T-02 | R-10 | 질의가 "carbon capture in cement"를 명시, 볼트에 해당 군집 노트 12개, 보고서에는 없음 | width critic `critical` finding 하나(`recommendation`은 기존 섹션에 삽입할 문장·짧은 문단, 새 섹션 아님) |
| T-03 | R-04 | depth critic이 두 번 실패 | 호스트가 `critic-findings-depth.json`을 `{"findings": [], "critic_failed": "<이유>"}`로 쓰고 진행. `verify_run`의 `artifact:critic-findings-depth.json`은 통과 |
| T-04 | R-20, R-27 | 호스트가 스텁을 만들지 않고 패처를 spawn, 패처가 결과 메시지에 로그를 인라인으로 반환 | `patch-log.json`은 빈 스텁(또는 없음)이므로 호스트가 결과 메시지의 JSON을 `patch-log.json`에 Bash로 써 넣는다. 스텁도 없이 비평 findings가 있었다면 lint `patch-surgery`가 `applied=0, skipped=0, conflicts=0` 경고를 낸다 |
| T-05 | R-26 | `patch-log.json`의 `skipped`에 `{"severity": "critical", "finding_id": 3, "critic": "dialectic", …}` 한 항목 | lint `patch-surgery`가 `error`: `1 critical finding(s) skipped by patcher: #3 (dialectic)…`(코드 강제) |
| T-06 | R-25 | 보고서 문장 "X is true [4]."에 대해 dialectic finding이 "중국에서는 Y 때문에 X가 성립하지 않는다 (note n7)" | 패치 결과 "X holds in Europe and North America; in China, Y creates a different regime in which X does not apply [7]." (범위 한정). "…though it may differ elsewhere"를 덧붙이는 편집은 금지 |
| T-07 | R-31, R-33 | 보고서에 인용 `[3]`이 있는데 Sources 목록에 `[3]` 줄이 없음 | `citecheck extract`가 그 쌍을 `dangling`에 `unresolved: "no-sources-entry"`로 둔다(`cite-check-pairs.json`). 호스트가 `critical` finding을 만든다(코드 강제: 추출 결과) |
| T-08 | R-32 | dangling 쌍이 `unresolved-entry`(Sources 항목은 있는데 URL·제목이 볼트 노트와 불일치) | 호스트가 `search`로 제목 단어를 찾아 볼트에 소스가 있으면 finding을 만들지 않는다. 볼트에 없으면 `major` finding |
| T-09 | R-33 | 인용이 모두 기계 통과(`sampled_for_llm: []`, dangling 0) | `cite-check-findings.json`에 `[]`, `run step <tag> 14.5 --status done -j`, cite-checker·2차 패처 spawn 없음 |
| T-10 | R-35, R-36 | cite-checker가 수치 있는 문장 "revenue grew 40% [[acme-q3]]"에 대해 노트가 25%를 말한다고 판정(`partially-supported`, 규모만 다름) | finding `{"verdict": "partially-supported", "severity": "major", "suggested_fix": "soften claim to what the source supports", …}`(수치 있는 문장이라도 `critical`은 `unsupported`·`wrong-source`에만). 2차 패처가 문장을 "25%"로 고친다. 다른 노트가 40%를 뒷받침하면 `wrong-source`·`critical`이고 `correct_note_id`로 인용 교체, 아무것도 뒷받침하지 않는 `unsupported`는 `critical`이고 문장 삭제 |
| T-11 | R-40, R-43 | `citation_style: "wikilink"`, 보고서에 "[[interim-report-labor]] [I4]" | polish 감사기가 interim이 인용하던 소스의 `[[<source-note-id>]]`로 바꾼다(예 `[[labor-ilo-2024]]`). 보고서의 다른 `[[source-note-id]]` 인용은 그대로. `inline`이면 `[N]`, `none`이면 삭제 |
| T-12 | R-40, R-52 | 보고서에 "the "scaling wall" problem"(소스에 없는 조어를 따옴표로 감쌈) | polish는 따옴표를 제거해 평문·이탤릭으로 바꾼다. 남으면 `run finish`의 `quote-integrity`가 error로 실패(행 10, 코드 강제) |
| T-13 | R-42 | "Three separate loci converge on the same failure mode."(파이프라인 내부 분류) vs "the genetic locus on chromosome 7"(도메인 용어) | 앞 문장은 "Three separate lines of inquiry converge…"로 재작성. 뒤 문장은 그대로 |
| T-14 | R-46 | register = survey(shim) | 확정을 강제하는 헤지 삭제 규칙을 건너뛰고 헤지 쌓기("may potentially indicate")만 붕괴. "suggests that"은 그대로 둔다 |
| T-15 | R-49, R-50 | polish 로그가 순 +1,200자 | 호스트가 "polish는 자르는 단계"이므로 잘못으로 보고 원인을 조사(재spawn 또는 에스컬레이션 점검) |
| T-16 | R-38, R-51 | light 티어 실행 | `polish-log.json`만 필수. critic·patch 로그가 없어도 정상이며 15.4는 MISSING을 보고하지 않는다 |
| T-17 | R-57, R-58 | 추천 `rec-7`(`make-list`)의 rationale이 "items appear sequentially in flowing prose"이고 `rec-9`의 `current`가 보고서와 불일치 | rec-7은 건너뛰고 `skipped`에 이유 기록. rec-9는 Edit가 실패하면 `edit_failures`에 기록하고 나머지 계속 |
| T-18 | R-58 | 추천 `remove-hr`·`merge-paragraphs`·`add-whitespace`가 섞여 있음 | 적용 순서: remove-hr → merge-paragraphs → … → add-whitespace |
| T-19 | R-60 | step 16 뒤 보고서의 H2 목록이 step 15 출력과 다름 | 종료 조건 위반(원문 규칙). H2 텍스트를 바꾸는 추천은 R-57이 항상 건너뜀 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, C-ID) | 확인 방법·한계 |
|---|---|---|
| R-01~R-05 | C-01 | 읽음. `skills/hyperresearch-12-critics.md:60`에 실패 스텁 JSON과 "ship gate가 4개 파일을 모두 요구"가 있고 `verify_run`이 이를 확인(`core/runs.py:808-817`) |
| R-06 | C-02~C-05(공통 문구 "Use the **Write tool**", "At most N findings", "Never propose deleting and retyping an entire section") | 읽음 |
| R-07 | C-02 `:727-739`, C-03 `:854-864`, C-04 `:975-983`, C-05 `:1185-1197` | 비평가별 심각도 정의를 읽음 |
| R-08 | C-02 | 읽음 |
| R-09 | C-03 | 읽음. 정량 메커니즘 압축 항목은 `:830-837` |
| R-10 | C-04 | 읽음. bloat 문구 "top-performing reports average 45-55KB while bottom performers average 65-70KB"는 프롬프트 근거 문구(검증 안 됨, 벤치 주장) |
| R-11~R-16 | C-05 | 읽음. R1~R6의 문턱값은 프롬프트 문구 그대로 |
| R-17 | C-02 `:734-739`, C-05 `:1328-1332` | register 문단을 읽음. 해당 shim 내용은 `core/levers.py:77-130`(`_REGISTER_CRITICS`)로 확인(행 2 소유) |
| R-18~R-21 | C-06 | 읽음. skip 경로 python 코드가 프롬프트에 그대로 있음 |
| R-22~R-26 | C-07, C-17(skipped 필드를 읽는 코드) | 읽음. lint가 읽는 필드를 `cli/lint.py:1223-1246`에서 확인 |
| R-27, R-28 | C-06 `:112-138` | 읽음 |
| R-29 | C-06 `:150-155` | 읽음 |
| R-30~R-34, R-36~R-37 | C-08, C-09 | 읽음. `citecheck extract` 옵션 기본값 0.6은 `cli/citecheck_cmd.py:19`. `--sample-rate`에 대해 스킬은 언급하지 않아 기본값으로 호출됨 |
| R-31 | C-09, `core/citecheck.py:178-376` | 쌍 추출·`triage_pairs`·`sample_needs_llm`·`write_pairs_file`은 행 10이 소유. 이 스펙은 스킬 요약문과 CLI 출력 필드만 근거로 씀 |
| R-35 | C-10 | 읽음 |
| R-38~R-39 | C-11 `:29-75` | 읽음 |
| R-40~R-49 | C-12, C-13 | 읽음. 정규식은 Python 문자열(`\\b`→`\b`)이 설치 시 이스케이프 해제된 값으로 옮김 |
| R-50~R-53 | C-11 `:79-163` | 읽음. lint 4규칙의 존재는 `cli/lint.py:17-40` `RULES`로 확인 |
| R-54~R-60 | C-14, C-15 | 읽음 |
| R-61 | `skills/hyperresearch.md:180-182`, `:289-290`(재생성 금지), C-06 `:131-138`, C-11 `:83-87` | 진입 스킬 불변식과 각 단계 스킬을 읽음 |
| R-62 | `core/runs.py:808-842`, `run-manifest-gate.md` 1.3 G·R-25·R-26·R-33 | 소유 스펙을 참조 |
| T-01~T-19 | 위 각 R-ID의 근거 | 구현에서 도출. 코드 실행 없음. 코드 강제로 표시한 T-05(`lint.py:1223-1246`)·T-07(`citecheck.py:178-250`)·T-12(`lint.py` `quote-integrity`, 행 10)만 코드 경로 |

**문서와 구현의 차이 (구현·본문을 사실로 썼다)**
- **step 12 스킬의 입력 설명**: `skills/hyperresearch-12-critics.md:24`가 `final_report_<tag>.md`를 "merged draft from step 10"이라 부르지만 이 파일은 step 11 synthesizer(light는 step 10)가 쓴 최종 보고서다. 비평가 프롬프트도 "Layer 4 draft", "Layer 5", "7-phase", "revisor"(패처의 옛 이름)를 섞어 쓴다(`core/hooks.py:646-657`, `:1385-1392`). 현행 단계 번호는 스킬 번호다.
- **instruction critic 구조 일치 규칙의 담당**: 에이전트는 "orchestrator must handle the restructure directly before Layer 7"이라 하고, 스킬 step 14.4가 실제로 호스트 처리 절차를 둔다(`core/hooks.py:1139-1142` ↔ `skills/hyperresearch-14-patcher.md:129-138`). 같은 사실의 양쪽 서술이다.
- **패처 입력의 findings 수**: 프롬프트는 "four findings JSONs"라 하고 스킬 템플릿은 "(full tier only)" 주석을 두 파일에 붙인다(`skills/hyperresearch-14-patcher.md:89-94`). 14는 light에서 건너뛰므로 실제로는 항상 4개다.
- **cite-check 2차 패스의 입력 형식**: cite-checker findings는 `sentence`·`cited_note_id`·`correct_note_id`·`suggested_fix`·`verdict`를 가진 JSON **배열**이고, 패처 프롬프트가 읽는 비평 finding 필드(`location`·`issue`·`evidence`·`recommendation`)와 키가 다르며 `findings` 객체 래퍼도 없다. 스킬은 "step 14 장치를 그대로 재사용"한다고만 쓰고 필드 매핑을 정의하지 않는다(`skills/hyperresearch-14-5-cite-check.md:78-84`). 실제 적용은 패처 LLM이 `suggested_fix`를 읽고 `sentence`로 위치를 찾는 것으로 읽힌다(추론). dangling findings(`no-sources-entry`·`unknown-note-id`는 `critical`, `unresolved-entry` 미해소는 `major`)를 호스트가 이 배열에 덧붙이는 항목의 키는 정의되지 않았다(cite-checker 항목과 같은 키를 쓴다고 보는 것이 자연스러움: 추론).
- **`patch-surgery` 규칙 설명**: 스킬 15.5는 이 규칙이 "draft churn from step 11 → final exceeds the safety threshold"라고 하지만 구현은 패치 로그의 `skipped` 중 `critical` 항목과 빈 로그를 본다(`skills/hyperresearch-15-polish.md:140` ↔ `cli/lint.py:1200-1296`). 구현을 사실로 썼다. 빈 로그 경고의 비평 파일 합산은 dialectic·depth·width만 센다(`:1275-1283`).
- **`audit_findings.json`**: step 15.5가 "Append"하는 v8 기록(`mode: "hyperresearch-v8"`, `loci_count` 등)을 읽는 코드가 없다. 같은 파일을 읽는 `audit-gate` 규칙은 `runs[]` 안 `mode: "conformance"|"comprehensiveness"` 항목과 `criticals[].fixed_at`을 기대한다(구버전 auditor 설계의 잔재, `cli/lint.py:306-400`). v8은 이 규칙의 입력을 만들지 않는다.
- **polish 감사기의 "Layer 7"·"Step 11 mandates BOTH modes"류 문구**는 구버전의 흔적이다(`cli/lint.py:372-381`의 메시지 포함).
- **설치된 프롬프트의 이중 중괄호**: `INSTRUCTION_CRITIC_AGENT`와 `READABILITY_REFORMATTER_AGENT`는 설치 시 `.format()`을 거치지 않아(`core/hooks.py:4092-4101`, `:4135-4150`) JSON 예시의 `{{`·`}}`가 그대로 남는다. 반면 dialectic·depth·width critic·polish 감사기는 `.format()`을 거쳐 `{`·`}`가 된다(`:4059-4090`, `:4123-4132`). 호스트 LLM이 이중 중괄호를 해석하는 데 문제를 보인다는 증거는 없다(추론). 재현 시 단일 중괄호로 쓰면 된다.
- **step 12 도구**: 비평가는 `Bash, Read, Write`(Bash는 볼트 검색용)이지만 프롬프트가 "You do NOT have Edit tools"라 한다. 일치한다. Codex 렌더링에서 이 도구 목록이 어떻게 번역되는지는 행 1·3(`core/codex.py:233`)이 소유한다.
- **cite-check 단계의 shim**: 스킬 spawn 템플릿에 shim이 없고 진입 스킬도 "cite-checker는 shim을 받지 않는다"고 쓴다(`skills/hyperresearch.md:212`). 2차 패처 패스가 `shims/critics.md`를 받는지는 "step 14 장치를 그대로"라는 문장뿐이고 명시되지 않았다(R-36은 이를 따라 "받는다고 본다: 추론").
- **가독성 임계값의 언어 범위**: 추천기는 EN과 CJK 임계값만 병기하고(R-55) 그 밖의 스크립트(아랍어·키릴 등)는 비ASCII 복사 규칙만 있고 임계값이 없다.

### 2.2 코드 읽는 순서 [선택]
1. 단계별 스킬 순서: `skills/hyperresearch-12-critics.md` → `-14-patcher.md` → `-14-5-cite-check.md` → `-15-polish.md` → `-16-readability-audit.md`.
2. 에이전트 프롬프트(`core/hooks.py`): 비평가 4종(`:627-1354`) → `PATCHER_AGENT`(`:1363-1532`) → `POLISH_AUDITOR_AGENT`(`:1539-1899`) → `READABILITY_REFORMATTER_AGENT`(`:2548-2755`) → `CITE_CHECKER_AGENT`(`:3478-3563`).
3. 인용 검사 CLI: `cli/citecheck_cmd.py:15` → `core/citecheck.py:353` `write_pairs_file`(알고리즘은 행 10).
4. 게이트 쪽: `core/runs.py:808-842`(필수 산출물·`cite-check-resolved`), `cli/lint.py:1200-1296`(`patch-surgery`).
5. 프로필 값: `core/profiles.py:300-303`·`:367-370`·`:409-411`, 렌더링 `core/render.py:50-64`.

## 적용 메모 [선택]
(없음)
