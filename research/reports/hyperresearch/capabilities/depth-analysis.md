---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/skills/hyperresearch-3-contradiction-graph.md
  - src/hyperresearch/skills/hyperresearch-4-loci-analysis.md
  - src/hyperresearch/skills/hyperresearch-5-depth-investigation.md
  - src/hyperresearch/skills/hyperresearch-6-cross-locus-reconcile.md
  - src/hyperresearch/skills/hyperresearch-7-source-tensions.md
  - src/hyperresearch/skills/hyperresearch-8-corpus-critic.md
  - src/hyperresearch/skills/hyperresearch-9-evidence-digest.md
  - src/hyperresearch/skills/hyperresearch.md
  - src/hyperresearch/skills/hyperresearch-10-triple-draft.md
  - src/hyperresearch/skills/hyperresearch-11-synthesize.md
  - src/hyperresearch/skills/hyperresearch-14-patcher.md
  - src/hyperresearch/core/hooks.py
  - src/hyperresearch/core/profiles.py
  - src/hyperresearch/core/levers.py
  - src/hyperresearch/core/untrusted.py
  - src/hyperresearch/core/codex.py
  - src/hyperresearch/cli/levers_cmd.py
  - src/hyperresearch/cli/lint.py
  - src/hyperresearch/cli/note.py
  - src/hyperresearch/models/note.py
depends:
  - width-sweep.md
  - run-manifest-gate.md
  - source-quality.md
  - vault-store.md
  - subagent-roster.md
  - claims-store.md
status: draft
---

# 깊이 분석 (step 3~9, full 티어)

> step 2가 모은 코퍼스(노트와 클레임 JSON)에서 클레임 충돌을 그래프로 묶고(3), 증거가 갈라지는 지점을 loci로 뽑아 점수·소스 예산을 매기고(4), loci마다 깊이 조사자가 전문을 읽어 "Committed position"으로 끝나는 interim 노트를 쓰게 하고(5), 그 입장들을 교차 조정해 `comparisons.md`로(6), 코퍼스 안의 전문가 이견을 `source-tensions.json`으로(7), "무엇이 뒤집을까" 점검과 보충 fetch로(8), 가장 가치 있는 클레임과 원문 인용을 `evidence-digest.md`로(9) 만들어 step 10 초안의 입력으로 넘긴다.

<!-- 이 문서의 `~`는 research/repos/hyperresearch/src/hyperresearch/ 이다. 이 단계들의 규칙은 거의 전부 스킬·에이전트 프롬프트 본문에 있다. 파이썬은 노트 유형 `interim`의 허용·비울타리, `locus-coverage`·`workflow` lint, `levers set --rerender`만 코드로 안다(R-34). -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. (step 3) `temp/claims-*.json` 전부를 읽어 서로 다른 소스의 모순 쌍을 찾고, 쟁점(fight)별 클러스터로 묶어 순위를 매겨 `temp/contradiction-graph.json`에 쓴다. `sources independence`로 독립 소스를 센 뒤 3개 이상 독립 소스가 동의하는 주장을 `temp/consensus-claims.json`에 쓴다. 클레임 파일이 없으면 이 단계를 통째로 건너뛴다(R-02~R-05).
2. (step 4) `loci-analyst` 2개(full, premier는 3개)를 병렬로 띄워 각자 1~8개 locus 후보를 `loci-<a|b|…>.json`에 쓰게 한다. 오케스트레이터가 이름으로 중복을 합치고 6개(premier 10개)로 자르고, locus마다 중요도·불확실성·이견·결정 영향(각 0~10, 합 40)을 매겨 소스 예산을 배정해 `loci.json`을 쓴다. 변증적(dialectical) locus가 최소 1개 있어야 한다(R-06~R-13).
3. (step 5) `source_budget > 0`인 locus마다 `depth-investigator`를 병렬로 띄운다(최대 6개). 각자 관련 노트 전문을 읽고 예산 안에서 fetcher로 소스를 더 가져와 `type: interim` 노트 하나를 쓰며, 노트는 반드시 `## Committed position`으로 끝난다(입장·확신도·경계 조건·"무엇이 이 입장을 바꿀까"·증거 무게)(R-14~R-18).
4. (step 6) interim 노트들의 Committed position을 나란히 놓고 loci 사이의 충돌·수렴·복합 관계 3~5개를 골라 `comparisons.md`에 쓴다. 이 문서가 초안의 논증 뼈대다(R-19).
5. (step 7) 코퍼스 상위 15~20개 소스를 훑고 이견이 숨은 8~12개는 전문을 읽어, `comparisons.md`의 긴장과 locus가 되지 못한 "고아 긴장"을 합쳐 3~7개를 고르고 각각 미리 결론(resolution)을 정해 `temp/source-tensions.json`에 쓴다(R-20).
6. (step 8) 기간 고정 1차 공시가 볼트에 있는지 사전 점검하고, `corpus-critic` 하나가 "이 입장을 뒤집을 소스가 있다면?"을 물어 갭 3~8개를 `corpus-critic-gaps-raw.json`에 쓴다. 오케스트레이터가 둘을 `corpus-critic-gaps.json`으로 합치고 fetcher 2~4개로 표적 수집한 뒤 결과에 따라 `comparisons.md`의 확신도를 고친다(R-21~R-25).
7. (step 9) 클레임 JSON에서 high 확신 또는 실증·통계 클레임을 거르고 80~120개로 잘라 원자 항목별로 묶어, 원문 인용(`quoted_support`)과 노트 id가 붙은 `temp/evidence-digest.md`를 쓴다(R-26, R-27).
8. light 티어는 step 3~9를 모두 건너뛰고 step 2 뒤 곧바로 step 10으로 간다(R-01). 이 단계들의 산출물은 step 10·11·14의 입력이다(1.2, R-28).

### 1.2 범위·통합 지점 [필수]
- 제공: step 3~9의 입력·처리·산출물·종료 조건, loci 점수·예산 규칙, interim 노트 형식, `comparisons.md`·`source-tensions.json`·갭 JSON·다이제스트 형식, 티어 생략 규칙, 이 단계가 spawn하는 `loci-analyst`·`depth-investigator`·`corpus-critic`의 프롬프트 동작 규칙과 fetcher를 부르는 방식.
- 제외(경계):
  - fetcher의 절차(R-13~R-18 of [width-sweep.md](width-sweep.md))·`fetch` CLI. step 8·5의 fetcher는 그 규칙을 그대로 쓴다.
  - 서브에이전트 frontmatter·도구 잠금(행 3, [subagent-roster](subagent-roster.md)). 여기서는 프롬프트가 쓰는 도구만 사실로 적는다.
  - 프로필 값 정의·렌더링·shim 문구(행 2). 1.3 C는 렌더링된 숫자만 적는다.
  - 초안·합성(행 7, [draft-synthesis](draft-synthesis.md))과 비평·패치(행 8, [critique-patch-polish](critique-patch-polish.md)). 이 스펙의 산출물을 그쪽이 읽는 경계는 아래 표와 R-28.
  - dissertation 챕터 변형: 3~9 스킬은 챕터를 언급하지 않는다([entry-decompose.md](entry-decompose.md) R-31 미결정).
  - `claims` 테이블: step 3~9는 DB가 아니라 `temp/claims-*.json` 파일을 직접 읽는다.
- 외부 의존·선행 계약: ① [width-sweep.md](width-sweep.md): 노트(`vault_tag` 태그), `temp/claims-<note-id>.json`, `temp/coverage-gaps.md`, `temp/redundancy-audit.md`, 소스 노트의 `word_count`·`quality_score`. ② [run-manifest-gate.md](run-manifest-gate.md) S1 산출물 이름. ③ [source-quality.md](source-quality.md) `sources independence`. ④ [vault-store.md](vault-store.md): `note list/show/new/update`, `search`, `NoteType`에 `interim`·`source-analysis`, 두 유형은 `<untrusted-source>` 울타리로 감싸지 않음. ⑤ 호스트의 서브에이전트 spawn(진입 스킬 규약, [entry-decompose.md](entry-decompose.md) R-33).
- 소유 상태·부작용: 런 작업 공간 파일(1.3 B), 볼트의 `type: interim` 노트(locus당 하나, 태그 `<vault_tag>`+`locus-<locus-name>`), `prompt-decomposition.json`의 `levers.inference_depth`(step 4가 `levers set`으로 바꿀 수 있음), fetch된 보충 소스 노트와 클레임 파일.

**step 10 이후와의 경계** (읽는 쪽 스킬의 입력 목록)

| 산출물 | 읽는 단계 | 읽는 방식 |
|---|---|---|
| `temp/evidence-digest.md` | step 10(각 초안 오케스트레이터), 11(합성), 14(patcher의 1차 인용 원천) | 초안의 "1차 증거층". light에는 없다 |
| `comparisons.md` | step 10, 11 | 논증 뼈대. 긴장 하나하나가 최종 보고서의 논증 단락이 되어야 한다(R-19). step 8이 확신도 주석을 덧붙인 뒤의 판 |
| `temp/source-tensions.json` | step 10, 11 | "Source Tensions" 전용 섹션의 재료(스킬 주장). 이견 하나가 소절 하나 |
| `type: interim` 노트 | step 10 | "모든 초안의 소스 목록에 포함"(Committed position이 들어 있음) |
| `type: source-analysis` 노트(step 2) | step 10 | 모든 초안에 포함 |
| `temp/contradiction-graph.json` | step 10(초안 B가 소수 의견 소스를 고를 때) | 선택적 |
| `loci.json` | step 5·6·8, lint | 초안 단계는 직접 읽지 않음 |
| `temp/consensus-claims.json` | step 8(corpus-critic), 9 | step 10 이후는 직접 읽지 않음 |
| `corpus-critic-gaps.json`, `temp/corpus-critic-results.md` | 하류 스킬 없음 | 기록용 |

### 1.3 인터페이스와 데이터 의미 [필수]

**A. 공통 spawn 형식** — 3요소(질문 원문 blockquote, `QUERY FILE`, `PIPELINE POSITION`) + `YOUR INPUTS` + `RUN DIRECTIVES: shims/research.md 전문`(C-04, [entry-decompose.md](entry-decompose.md) 1.3 I). 세 에이전트 모두 연구용 shim을 받는다.

| 에이전트 | 호출 단계 | 입력 | 출력 | 프롬프트가 쓰는 도구 |
|---|---|---|---|---|
| `hyperresearch-loci-analyst` | 4 | `corpus_tag`, `analyst_id`(a,b,c…), `output_path = research/runs/<tag>/loci-<analyst_id>.json` | JSON(R-07) | Bash, Read, Write |
| `hyperresearch-depth-investigator` | 5 | locus 5필드(`name`,`one_line`,`flavor`,`source_budget`,`rationale`), `corpus_tag`, `locus_name`, `source_budget`, "전문을 읽고 interim 노트를 쓰라"는 지시 | 볼트 노트 id | Bash, Read, Write, Task |
| `hyperresearch-corpus-critic` | 8 | `corpus_tag`, `comparisons_path`, `loci_path`, `output_path = temp/corpus-critic-gaps-raw.json` | 갭 JSON(R-22) | Bash, Read, Write |
| `hyperresearch-fetcher` | 8 | `vault_tag`, `search_queries`, `source_type`, `gap_id` | 노트·클레임([width-sweep.md](width-sweep.md)) | |

**B. 산출물** (이름은 S1, 모두 `research/runs/<vault_tag>/` 아래)

| 파일 | 쓰는 이: 단계 | 내용 |
|---|---|---|
| `temp/contradiction-graph.json` | 오케스트레이터: 3 | 순위가 매겨진 쟁점 클러스터의 배열(없으면 `[]`). 클러스터: `cluster_id`, `fight`, `side_a`/`side_b`(`position`, `claims`(클레임 문장 배열), `sources`(노트 id 배열)), `evidence_quality_delta`, `scope_overlap`, `decision_relevance`(high\|medium\|low)(C-01) |
| `temp/consensus-claims.json` | 오케스트레이터: 3 | 독립 소스 3개 이상이 동의하는 주장 목록(`[]` 허용). 항목의 모양은 스킬에 없다(U-01) |
| `loci-<id>.json` | loci-analyst: 4 | R-07 |
| `loci.json` | 오케스트레이터: 4 | `{"loci":[{name, one_line, flavor, importance, uncertainty, disagreement, decision_impact, composite_score, source_budget, rationale}], "skip_loci":[…]}`(C-02) |
| `temp/interim-report-<locus-name>.md` + 볼트 노트 | depth-investigator: 5 | 본문 파일을 만들고 `note new --type interim`으로 노트화(R-16) |
| `comparisons.md` | 오케스트레이터: 6, 갱신 8 | R-19 |
| `temp/source-tensions.json` | 오케스트레이터: 7 | R-20 |
| `temp/period-pinned-gaps.json` | 오케스트레이터: 8 사전 점검 | `{"gaps":[{id:"pp-N", type:"period-pinned-primary", target_position, search_queries, source_type:"primary-filing", priority:"critical", rationale}]}` |
| `temp/corpus-critic-gaps-raw.json` | corpus-critic: 8 | `{"gaps":[{id:"cc-N", type, target_position, search_queries(2~3개), source_type, priority, rationale}]}` |
| `corpus-critic-gaps.json` | 오케스트레이터: 8 | 위 두 파일을 합친 `{"gaps":[…]}`, `pp-` 항목이 앞(루트에 둔다. S1) |
| `temp/corpus-critic-results.md` | 오케스트레이터: 8 | 갭마다 검색·발견·확신도 영향 |
| `temp/evidence-digest.md` | 오케스트레이터: 9 | R-26 |
| `temp/orchestrator-notes.md` | 오케스트레이터 | step 6의 임시 목록 등 |

**C. 프로필 수치** (`~/core/profiles.py:253-373`, gear `p`로 렌더링. 범위는 (하한, 상한))

| 키 | full | premier | 쓰이는 곳 |
|---|---|---|---|
| `loci_analysts` | 2 | 3 | step 4 spawn 수 |
| `loci_max` | 6 | 10 | 병합 후 상한, 분석가당 1~`loci_max+2`개 |
| `depth_budget_total` | 40 | 80 | step 5 총 소스 예산(R-10) |
| `depth_budget_brackets` | (30,15), (20,10), (10,5), (0,3) | (30,25), (20,15), (10,8), (0,5) | 합성 점수 구간 → 구간 상한 |
| `investigator_max` | 6 | 10 | step 5 spawn 상한 |
| `depth_default_budget` | 10 | 15 | `source_budget`이 없을 때 조사자 기본 |
| `comparisons_tensions` | 3–5 | 4–7 | step 6 긴장 수 |
| `source_tensions` | 3–7 | 4–9 | step 7 이견 수 |
| `tension_survey` / `tension_full_reads` | 15–20 / 8–12 | 20–30 / 10–15 | step 7 훑을 소스 / 전문을 읽을 소스 |
| `corpus_critic_gaps` / `corpus_critic_fetchers` | 3–8 / 2–4 | 4–10 / 3–5 | step 8 갭 수 / 보충 fetcher 수 |
| `claims_cap` / `claims_min` | 80–120 / 30 | 150–220 / 50 | step 9 |

### 1.4 행동 규칙과 남은 질문 [필수]

"코드 확인"은 스킬·에이전트 프롬프트 본문 또는 코드를 직접 읽었다는 뜻이다. 프롬프트 준수는 코드가 강제하지 않는다(R-34).

**A. 티어·공통**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `pipeline_tier = light` | step 3~9는 모두 "SKIP for light"(step 6은 "loci 없음 = comparisons 없음", step 9는 "light 건너뜀"). 호출 순서는 2 → 10 → 15 → 16(step 2 스킬의 다음 단계 분기)이고 step 10은 "light에는 `evidence-digest.md`가 없다"며 볼트를 직접 읽는다. 따라서 `contradiction-graph.json`·`consensus-claims.json`·`loci.json`·interim 노트·`comparisons.md`·`source-tensions.json`·갭 JSON·`evidence-digest.md`는 만들어지지 않는다. step 4의 문구 "proceed directly to step 9"는 낡은 문구다(2.1) | 코드 확인 |
| R-02 | step 3 입력 | `scaffold.md`(vault_tag), `prompt-decomposition.json`(원자 항목, `pipeline_tier`), `temp/claims-*.json` **전부**(폐기 노트의 클레임 파일 필터 없음). 클레임 파일이 하나도 없으면 step 3을 통째로 건너뛰고 step 4는 코퍼스 산문 스캔으로 대체한다. 파일이 없으므로 이후 스킬의 "(step 3이 돌았다면)" 입력은 없다 | 코드 확인 |
| R-03 | step 3 모순 쌍 | 각 클레임에 대해 **다른** 소스의 클레임 중 다음 중 하나에 해당하는 것을 모순으로 짝짓는다: ① 같은 `stance_target`에 반대 `stance`(supports↔refutes) ② 같은 `entities`에 반대 결론 ③ 같은 범위인데 다른 `numbers`("15% 성장" vs "3% 감소") ④ `scope_conditions`가 겹치는데 `evidence_type`이 반대 방향을 가리킴 | 코드 확인 |
| R-04 | step 3 클러스터링 | 관련된 쌍을 하나의 쟁점(fight)으로 묶어 C-01의 객체로 쓴다. 순위: `decision_relevance`(high 먼저), 같으면 `evidence_quality_delta`가 좁은(팽팽한) 쟁점이 위(empirical > theoretical > anecdotal로 어느 쪽 증거가 강한지 기술). `scope_overlap`에는 진짜 이견인지 범위만 달라 둘 다 맞는지를 쓴다. `temp/contradiction-graph.json`에 순위순 배열로 쓴다. 코퍼스가 일치하면 빈 배열 | 코드 확인 |
| R-05 | step 3 합의 주장 | 합의 = **독립 소스 3개 이상**이 동의하는 클레임. 독립은 가정이 아니라 계산한다: 먼저 `sources independence --tag <vault_tag> -j`를 돌려 같은 정규 URL·거의 같은 본문·같은 통신사 문구 사본을 묶고, 클러스터는 한 표로 센다("독립성 점수 합 ≥ 3.0, 원 소스 수 ≥ 3이 아님"). 결과를 `temp/consensus-claims.json`에 쓴다(`[]` 허용) = "초안이 헤지 없이 단언해도 되는 기반". 점수 정의(root 1.0, 나머지 `1/크기`)는 [source-quality.md](source-quality.md) R-12이며 2.1에 차이가 있다. 종료: 두 파일 모두 존재 | 코드 확인 |

**B. step 4 loci 분석**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | step 4 시작 | 입력: `scaffold.md`, `prompt-decomposition.json`, `contradiction-graph.json`(있으면), `coverage-gaps.md`. 먼저 `note list --tag <vault_tag> --all -j`로 폭 탐색이 끝났는지 본다. `loci_analysts`(full 2, premier 3)개의 `hyperresearch-loci-analyst`를 **한 메시지에서 병렬 spawn**하고 각각 알파벳 id(a,b,c)와 자기 출력 파일을 준다. 모두 같은 코퍼스를 독립적으로 읽는다 | 코드 확인 |
| R-07 | loci-analyst 절차 | ① `note list --tag <corpus_tag> --all --json`으로 코퍼스를 읽는다. **노트가 10개 미만이면 부모에게 알리고 중단**(얇은 코퍼스에서 locus를 못 찾는다) ② `contradiction-graph.json`이 있으면 먼저 읽고 `decision_relevance: high` 클러스터가 진짜 쟁점(범위 불일치가 아님)인지 확인해 `flavor: dialectical` 후보로 승격하며 `side_a/side_b`를 `opposing_positions`로 쓴다 ③ 노트는 제목+요약+본문 앞 ~400자만 읽는다(전문은 힌트가 있을 때만) ④ locus 조건: 3~8개의 표적 소스로 답할 만큼 구체적이고, 폭 코퍼스가 답을 **암시하되 해결하지 못하는** 곳이며, 답이 최종 보고서의 논지·권고를 바꿀 만큼 중요하다. 걸러낼 것: 주 질문의 재진술("X를 더 설명"), 코퍼스 증거를 댈 수 없는 것, 발견 단계를 처음부터 다시 해야 하는 것, 질문과 직교하는 것 ⑤ flavor는 `convergent`(소스들이 가리키지만 완결 못 한 기술적 질문) 또는 `dialectical`(소스끼리 실제로 불일치) ⑥ **적어도 하나는 dialectical**이어야 하고, 없으면 `skip_loci`에 구체 증거로 정당화한다("30개 노트를 모두 스캔했고 어느 것도 핵심 지점에서 다른 것과 모순되지 않는다") ⑦ 출력 JSON(C-05): `analyst_id`, `loci[]`(`name`(하이픈 슬러그), `flavor`, `one_line`, `rationale`(코퍼스 노트 id를 최소 하나 명시), `corpus_evidence`(노트 id 배열, 필수), `suggested_starting_urls`, `suggested_searches`, dialectical은 `opposing_positions`(최소 2개, 각 `position`+`sources`)), `skip_loci[]`(`slug`, `reason`). 개수 1~`loci_max+2`개(full 8). 소수 정예를 선호한다. 보고: 출력 경로, 채택/기각 수, 코퍼스가 깊이 조사를 지지하는지 한 줄 | 코드 확인 |
| R-08 | 병합 | 전원을 기다린다. 일부가 실패하면 성공한 출력으로 진행한다. **모두 실패(빈 loci)면 사용자에게 "폭 탐색이 너무 얇았다"고 알리고 중단**한다(약한 코퍼스에 깊이를 강제하지 않음). 모든 `loci-<id>.json`을 읽어 `name` 완전 일치 또는 같은 핵심 질문의 근접 일치로 중복을 합치되 의심스러우면 `corpus_evidence`가 강한 쪽을 택한다. 합친 수가 `loci_max`를 넘으면 정본 질문에 대한 근거의 하중이 약한 순으로 버린다. 모든 분석가의 `skip_loci`는 합집합으로 최상위 `skip_loci`에 남긴다 | 코드 확인 |
| R-09 | 점수 | 남은 locus마다 네 차원(각 0~10)을 매긴다: importance(주 하위 질문에 직접 답하면 8~10, 주변 보강이면 2~4), uncertainty(모순 그래프에서 양쪽 증거 질이 비슷한 날카로운 쟁점이면 8~10, 한쪽이 분명히 강하면 4~6, 이미 해결이면 1~3), disagreement(독립 소스 중 몇이 불일치하나, 모순 클러스터 크기로 대리: 단독 2~3, 다수 쟁점 7~10, 그래프가 없으면 `opposing_positions`로 추정), decision_impact(해결하면 초안의 권고·논지가 바뀌나: 바뀌면 8~10, 뉘앙스만 더하면 4~6). `composite_score` = 네 합(최대 40) | 코드 확인 |
| R-10 | 예산 배정 | step 5의 총 소스 예산은 `depth_budget_total`(40). 비례 배분하되 합성 점수 구간별 `source_budget` 상한: 30~40 → `depth_budget_brackets[0][1]`(15, deep dive), 20~29 → `[1][1]`(10), 10~19 → `[2][1]`(5, shallow pass), 10 미만 → 0~3 또는 조사 생략. "20 넘는 locus가 1~2개뿐이어도 괜찮다, 그쪽에 크게 배정하라". 상한(구간)과 총액이 어떻게 맞물리는지의 알고리즘은 없다(U-02) | 코드 확인 |
| R-11 | `loci.json` 쓰기 | C-02의 스키마로 `loci.json`을 쓴다(각 locus: `name`, `one_line`, `flavor`, 네 차원 점수, `composite_score`, `source_budget`, `rationale`; 최상위 `skip_loci`). `flavor`의 허용 값이 스킬(`dialectical\|synthesis\|technical`)과 에이전트(`convergent\|dialectical`)에서 다르고, 분석가의 `corpus_evidence`·`opposing_positions`·`suggested_*` 필드를 `loci.json`으로 옮기라는 지시가 없다(U-03, 2.1) | 코드 확인 |
| R-12 | 조사자 수·inference depth | step 5의 조사자는 `source_budget > 0`인 locus당 하나, 최대 `investigator_max`(6). locus가 하나만 통과하면 하나. 이어서 오케스트레이터는 **실제 코퍼스를 본 뒤** `inference_depth`를 재검토한다: 최상위 질문의 증거가 회색 문헌·공시·미공개 수치처럼 폭 소스로는 미결정이면 `deep`으로 올리고, step 1이 `deep`을 골랐는데 코퍼스가 풍부·일치하면 `surface`로 내린다. 바꿀 때는 `levers set <vault_tag> inference_depth=deep --rerender -j`(`prompt-decomposition.json`의 `levers`를 고치고 shim 4개를 다시 쓴다. 허용값 위반이면 `LEVER_ERROR`, 쓰기 전에 검증, C-09). 현재 값이 맞으면 아무것도 하지 않는다 | 코드 확인 |
| R-13 | step 4 불변식·종료 | 변증적 locus가 최소 1개여야 한다(분석가의 `skip_loci`가 구체 증거로 정당화한 경우 제외). 없고 정당화도 없으면 loci-analyst를 더 엄격한 프롬프트로 다시 spawn한다. 조사자에게 `--suggested-by`로 `hyperresearch-locus-seed` 같은 가짜 breadcrumb를 주지 않는다(실제 노트 id를 쓰거나 아예 생략). 종료: `loci.json`에 locus 1개 이상(또는 모든 분석가가 `skip_loci`로 정당화), 변증적 locus 또는 `skip_loci` 정당화, 남은 locus는 모두 `source_budget` 배정 | 코드 확인 |

**C. step 5 깊이 조사**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | step 5 spawn | `source_budget > 0`인 locus마다 `depth-investigator` 하나를 **한 메시지에서 병렬 spawn**한다(최대 `investigator_max`). 프롬프트에는 질문 원문, 위치 진술("step 4가 `loci.json`을 만들었고 끝나면 step 6이 당신의 committed position을 다른 조사자들과 조정한다"), locus 5필드, 입력(`corpus_tag`, `locus_name`, `source_budget` = "추가로 가져올 수 있는 소스의 **하드 상한**"), shim, 그리고 **전문 읽기 지시**("`note show <id1> <id2> … -j`로 관련 노트 전문을 읽은 뒤에 쓴다. 요약만으로 쓰면 패러프레이즈, 전문으로 쓰면 종합이다")와 출력 지시(`type=interim`, 태그 `<vault_tag>`+`locus-<locus-name>`, 반드시 `## Committed position`으로 끝나고 확신도와 "무엇이 바꿀까"를 포함)가 있다(C-06) | 코드 확인 |
| R-15 | 조사자 절차 | ① 볼트부터: 분석가가 `corpus_evidence`로 든 노트를 `note show … --json`으로 읽는다. 해당 노트의 `claims-<note-id>.json`이 있으면 읽고 `stance`가 반대인 같은 `stance_target`을 우선 조사 대상으로 삼는다 ② 소스 예산은 `locus.source_budget`(없으면 `depth_default_budget` 10). 정설·고인용 소스를 우선, `suggested_starting_urls`는 출발점일 뿐 상한이 아니다 ③ 새 소스는 **`fetch`를 직접 부르지 않고** `hyperresearch-fetcher`에 Task로 위임한다(여러 URL을 한 Task에 배치). 위임 때 `--tag <corpus_tag>`와 추가 `--tag locus-<locus-name>`을 넘기고, 코퍼스 노트가 소개한 URL이면 `--suggested-by <코퍼스 노트 id>`(아니면 생략, 지어내지 않음) ④ 연구 문헌이 있는 locus는 웹 검색 전에 학술 소스(스킬 문구: Semantic Scholar/arXiv/OpenAlex)를 먼저 ⑤ 새 소스를 `note show <id> -j`로 읽고 논지를 움직이는 구절은 패러프레이즈 대신 직접 인용한다 ⑥ interim 노트 하나를 쓴다(R-16). Codex에서는 조사자가 잎 에이전트라 spawn 없이 자기 fetch·읽기로 끝낸다(C-11) | 코드 확인 |
| R-16 | interim 노트 쓰기 | **쓰기 전에** `note list --tag locus-<locus-name> --type interim --all --json`으로 이미 있는지 본다. 있으면 새로 만들지 않고 `note update`로 고치거나 부모에게 "이미 조사됨, 내가 더했을 것은 …"을 보고한다(중복 interim은 소스 수를 부풀리고 비평가를 혼란시키며 locus 커버리지 계산을 깬다고 명시). 없으면 본문을 `research/runs/<vault_tag>/temp/interim-report-<locus-name>.md`에 쓰고 `note new "Interim report — <locus name>" --tag <corpus_tag> --tag locus-<locus-name> --type interim --body-file … --summary "<한 줄>" --json`. **본문 구성(C-06)**: `# Interim report: <name>`, `**Locus question:**`, `**Flavor:**`, `## What the corpus already said`(코퍼스 노트를 `[[note-id]]`로 인용), `## What the new sources say`(새 소스 3~10개, 각 1~2문단, 중요한 곳은 직접 인용, `[[note-id]]` 링크), `## Evidence synthesis`(2~4문단, 기술적, 변증적 locus는 입장마다 `### Position A: …`/`### Position B: …` 소절로 각 입장의 최선의 증거를 강하게 제시), `## Committed position`, `## Open questions`, `## Sources`(`[[note-id]]` 번호 목록). **Committed position**: 한 문단으로 한 편을 든다("증거가 말하는 것"이 아니라 "증거가 합쳐 가리키는 것"). 변증적이면 어느 입장의 증거가 나은지 또는 종합을 택하고 "both have merit"로 비껴가지 않는다. 문단 뒤 **필수 보정 필드 5개**: `Position`(한 문장 주장), `Confidence`(high >80% / medium 50–80% / low 30–50%, "소스 5개 중 2개만 지지하면 medium"), `Boundary conditions`, `What would change this position`(입장을 뒤집을 구체 증거, "가장 가치 있는 보정 신호"), `Evidence weight`(예: "실증 3 지지, 이론 모델 1 반박, 사례 2 모호"). **규범적 구체성**: 증거가 허락하는 한 구체 규칙·임계값·퍼센트·시간 창·이름 있는 메커니즘을 쓴다(방향만은 폴백, 모호함은 거부). 수치를 못 대면 "코퍼스가 이 임계값을 수량화하지 않는다"고 쓰되 방향은 헤지하지 않는다. 풀 수 없는 locus도 입장은 낸다("증거가 X를 결정하기에 불충분하지만 입증 책임은 Y 쪽에 있다"는 유효, "우리는 모른다"는 무효). 조사자당 노트 정확히 하나. 최종 보고서 섹션을 쓰는 것이 아니라 오케스트레이터가 읽을 밀도 있는 종합 패킷이다. 상한: 새 fetch는 `source_budget` 이내(더 필요하면 후속 locus를 권고). 보고: interim 노트 id, 가져온 소스 수, 한 줄 종합, 미해결 질문 | 코드 확인 |
| R-17 | step 5 완료 점검 | 전원을 기다린다. 일부가 실패해도 성공한 것으로 진행하되 **50% 넘게 실패하면 멈추고 loci 품질을 사용자와 재검토**("stop and escalate"; 비대화형 처리는 스킬에 없다, U-04). 끝나면 `note list --tag <vault_tag> --type interim --all --json`으로 interim 노트를 나열하고 `note show <id1> <id2> … -j`로 한꺼번에 읽어 각 `## Committed position`을 컨텍스트에 쥔다. **불변식**: 모든 interim 노트는 `## Committed position`으로 끝난다. 서술 요약으로 끝난 노트는 결함이므로 그 조사자를 "committed position을 강조해" 다시 spawn한다. 종료: `source_budget > 0` locus마다 interim 노트 하나(태그 `<vault_tag>`+`locus-<locus-name>`), 모두 Committed position으로 끝남 | 코드 확인 |
| R-18 | lint 연동(ship gate 아님) | `lint`의 `locus-coverage`: `loci.json`의 locus마다 태그 `locus-<name>`과 `type=interim`인 노트 수를 센다. 없는 locus가 1개면 warning, 2개 이상이면 error. 한 locus에 interim이 2개 이상이면 warning(중복). `workflow`: 보고서 산출 노트가 있고 `loci.json`이 있는데 interim 노트가 0개면 error, `loci.json`에 locus가 1개 이상인데 `comparisons.md`가 없으면 error. `verify_run`(ship gate)은 이 규칙들을 부르지 않는다(run-manifest-gate의 content 규칙은 `quote-integrity`·`retracted-citations` 둘뿐). `Committed position` 문자열을 검사하는 코드는 없다 | 코드 확인 |

**D. step 6~7 조정·이견**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | step 6 교차 조정(full 전용, 항상 실행) | 입력: `loci.json`, 모든 interim 노트 전문(Committed position이 컨텍스트에 있어야 함). ① 모든 입장을 나란히 적는다(`orchestrator-notes.md` 사용 가능) ② 모든 입장 쌍에 묻는다: 사실은 같은데 해석이 다른가, 다른 증거로 반대 결론인가, 한 locus의 입장이 다른 locus의 증거에 의해 복잡해지는가, 한쪽이 다른 쪽의 특수 사례인가, 다른 경로로 같은 결론에 수렴하는가(독립 경로의 수렴도 발견) ③ 약한 것(직교하거나 서로 반복)은 버리고 `comparisons_tensions`(full 3–5개)의 가장 강한 긴장을 고른다 ④ `comparisons.md`를 쓴다: `# Cross-locus comparisons` 뒤 긴장마다 `## Tension N: <짧은 이름>`, `- **Locus A** ([[interim-A]]) commits: <한 줄 입장>`, `- **Locus B** ([[interim-B]]) commits: …`, `- **The cross-locus dynamic:** <2~3문장: 충돌/수렴/복합/특수 사례, 하중이 있는 이견 또는 합의>`, `- **How the draft should engage this:** <한 문장>`(C-07). 노트 링크의 id는 `note new`가 제목에서 만든 실제 id다 ⑤ 보정 종합: 긴장마다 조사자들의 확신도와 "what would change" 조건을 본다(한쪽 high, 다른 쪽 low면 초안이 그만큼 가중, 둘이 같은 "바꿀 조건"을 말하면 진짜 미해결 질문으로 명시) ⑥ 이 문서는 **초안의 논증 뼈대**: 여기 이름 붙인 긴장은 최종 보고서의 눈에 보이는 논증 단락이 되어야 한다("4개를 적고 초안이 1개만 다루면 insight 점수가 떨어진다"). locus가 1개뿐인 full 실행도 그 locus의 입장을 유일한 닻으로 한 `comparisons.md`를 쓴다. 종료: 파일 존재, 긴장 3~5개(또는 단일 locus의 정제된 입장 1개), 긴장마다 locus 참조·역학·초안 대응 지침·보정 메모(템플릿에는 보정 줄이 없다, U-05) | 코드 확인 |
| R-20 | step 7 이견 추출(full 전용) | 입력: `comparisons.md`(step 4가 `skip_loci`로 locus 0개를 정당화했다면 없음 → 바로 고아 스캔), `contradiction-graph.json`(있으면), 코퍼스. ① `comparisons.md`의 긴장 각각이 이미 후보 이견: 두 입장, 각각의 가장 강한 증거, 예비 판단을 뽑는다 ② 코퍼스에서 "가장 품질이 높은" 폐기 아닌 소스 `tension_survey`(15–20개)를 훑고(`note list`, 품질 정렬 방법은 없다, U-06) 그중 이견이 있을 법한 `tension_full_reads`(8–12개)는 **전문**을 `note show <ids…> -j`로 읽는다("이견은 요약이 평평하게 만드는 뉘앙스 속에 숨는다": "however" 절, 각주 단서, 토론 절의 방법론 비판) ③ 찾을 것: 서로 명시적으로 반박하는 소스, 같은 현상을 경쟁 이론 틀로 설명, 한쪽이 다른 쪽이 무시한 데이터를 인용, 정부·기관 입장 vs 학계 결과, 업계 주장 vs 독립 연구, 역사적 합의 vs 최근 증거 ④ 모순 그래프의 high 클러스터 중 locus로 승격되지 않은 것은 우선 고아 후보 ⑤ `source_tensions`(full 3–7개) 선별 기준: 결정 관련성, 증거 질(둘 다 실증에 기반), 독자 가치. 버릴 것: 쉽게 해소되는 것(한쪽이 분명히 틀림), 정의상의 불일치, 질문과 직교 ⑥ **이견마다 미리 결론을 정한다**(열린 채로 두지 않음): 5~10단어 이름, 각 쪽의 가장 강한 증거(인용 또는 노트 id), 어느 쪽이 나은지 또는 종합과 하중 있는 이유 ⑦ `temp/source-tensions.json`(C-08): `{"tensions":[{name, side_a:{position, evidence, proponents[노트 id]}, side_b:{…}, resolution(한 문단), origin("comparisons"\|"contradiction-graph"\|"orphan-scan"), decision_relevance("high"\|"medium")}]}`. 코퍼스에 진짜 이견이 없을 때(단일 목소리 코퍼스)만 범위보다 적게(0까지) 허용되며 그때는 최상위 `"shortfall_reason"`(무엇을 읽었고 왜 더 없는지)을 쓴다. 이견을 지어내지 않는다. 이 파일은 step 10의 필수 "Source Tensions" 섹션이 되도록 설계됐다(스킬 주장) | 코드 확인 |

**E. step 8 코퍼스 비평가**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-21 | 사전 점검: 기간 고정 1차 공시(`time_periods` 비어 있지 않을 때만, **critic spawn 전에**) | 각 `time_period` 항목마다: ① `search "<period> <issuer>" --tag <vault_tag> --include-body -j`로 `primary_source` 설명·`issuer`에 맞는 노트를 찾는다 ② 후보를 `note show <id> -j`로 열어 문서의 **실제 보고 기간**이 정확히 그 기간인지 확인한다(Q1 2025 10-Q는 "Q3 2024"를 충족하지 못한다) ③ 없으면 오케스트레이터의 **자기 파일** `temp/period-pinned-gaps.json`(`{"gaps":[…]}`)에 `priority: critical`, `type: period-pinned-primary` 갭을 `pp-1`, `pp-2`… id로 추가한다(1.3 B 스키마, 검색 질의 예시 포함). 이 파일은 corpus-critic이 쓰지 않으므로 덮어쓰이지 않고 merge 단계에서 합쳐진다. 이유: 수치 정밀도 누락이 가장 큰 단일 범주의 피할 수 있는 사실 오류이므로 수집을 critic 완료 전에 먼저 한다 | 코드 확인 |
| R-22 | corpus-critic spawn·절차 | **하나만** spawn(질문 원문, 위치 진술 "step 6이 `comparisons.md`를 만들었고, 끝나면 오케스트레이터가 표적 fetch 웨이브를 돌리고 step 10이 초안을 쓴다", 입력 4개, shim). 모든 committed position과 합의 주장에 한 질문: "이걸 뒤집을 소스가 존재한다면 무엇인가?" 절차: ① `comparisons.md`의 입장·긴장마다 조사자의 "What would change this position"을 읽고, 약화시킬 구체 반증과 강화할 소스 유형을 이름 붙인다 ② 입장마다 그것이 기대는 노트 id 2~3개를 `note show … -j`로 **전문** 읽고 원본이 입장을 정말 지지하는지 확인한다(요약·interim이 원문에서 어긋날 수 있음; 단서·범위 한정·모순 세부를 입장이 무시하면 갭으로 표시) ③ `temp/consensus-claims.json`이 있으면 고확신 합의마다 반대 소스가 있을 법한지, 독립 소스가 지지하는지(상류 하나로 수렴하는 파생인지) 본다 ④ `temp/redundancy-audit.md`가 있으면 파생 소스만 지지하는 입장은 취약하다고 표시 ⑤ `search "<adversarial query>" --tag <corpus_tag> -j`로 이미 볼트에 반증이 있는지 먼저 본다 ⑥ `output_path`에 갭 JSON(C-10): `id`(`cc-1`…, 순번), `type`(overturning\|strengthening\|independent-verification), `target_position`, `search_queries`(2~3개 구체 질의), `source_type`(academic\|government\|industry\|investigative), `priority`, `rationale`. 상한 `corpus_critic_gaps`(full 3–8개). 프롬프트 본문은 `critical`·`high`만 내라고 하지만 스키마 문구에는 `medium`도 있다(2.1). 규칙: 갭은 실행 가능해야 하고(검색 질의로 바꿀 수 있게), 반증 소스가 최우선, 폭 탐색이 이미 다룬 것은 표시하지 않고(볼트를 먼저 확인), 조사자의 입장을 재논쟁하지 않는다(빠진 증거를 찾는 일이지 해석에 반대하는 일이 아니다), 질문과 무관한 주변 주제의 갭은 내지 않는다 | 코드 확인 |
| R-23 | 갭 병합 | critic이 끝나면 `temp/corpus-critic-gaps-raw.json`을 읽어 **런 루트의** `corpus-critic-gaps.json`을 `{"gaps":[…]}`로 쓴다: 사전 점검의 `pp-` 항목을 **먼저**, 그다음 critic의 `cc-` 항목. 모든 갭이 id를 유지한다(접두어로 충돌 방지; 아래 fetch 웨이브가 id로 참조). 사전 점검 파일이 없으면 critic 갭만 | 코드 확인 |
| R-24 | 표적 fetch 웨이브 | `corpus_critic_fetchers`(full 2–4개)의 `hyperresearch-fetcher`를 spawn한다(Codex: 병렬 spawn·전원 대기). 입력: `vault_tag`, `search_queries: [<gap.search_queries>]`, `source_type: <gap.source_type>`, `gap_id: <gap.id>`, shim. 위치 진술: "step 8 fetcher (corpus-critic gap-fill) … 끝나면 오케스트레이터가 가져온 것을 바탕으로 `comparisons.md`를 갱신한다". `pp-` 갭이 critic의 폭넓은 분석보다 먼저 수집되도록 둔다("숫자 정밀도 누락 방지"). 갭을 fetcher에 어떻게 나누는지(갭 수 3~8이 fetcher 수 2~4보다 많음)와, fetcher 프롬프트가 `search_queries`·`gap_id` 입력을 처리하는지는 스킬·프롬프트에 없다(U-07). step 8 뒤에 `claims ingest`·랭킹 명령을 다시 돌리라는 지시도 없다 | 코드 확인 |
| R-25 | 결과 평가·로그 | 갭마다 결과를 평가하고 `comparisons.md`를 **수정**한다: ① 반증 소스 발견: 해당 interim 노트의 입장을 다시 읽고 정말 약화시키면 `comparisons.md`에 약화된 입장을 기록(**전체 깊이 조사를 다시 돌리지 않고** 입장의 확신도만 조정, 초안이 적절한 보정으로 다룬다) ② 반증 소스 없음: "[입장]에 대한 반증의 적대적 검색은 실질적 도전을 찾지 못했다"고 기록, 입장은 확신을 얻는다 ③ 강화·검증 소스 발견: 추가 지지를 기록(초안이 더 확신 있게 단언 가능). `temp/corpus-critic-results.md`에 갭마다 무엇을 검색했고 무엇을 찾았는지(또는 못 찾았는지), 확신도 영향, 바뀐 입장의 갱신된 확신도를 쓴다. 종료: `corpus-critic-gaps.json`(병합본, id 있음) 존재, **모든 critical 갭을 시도**(가져왔거나 찾을 수 없다고 기록), `corpus-critic-results.md` 존재, `comparisons.md`가 확신도·강화·반증 주석으로 갱신됨 | 코드 확인 |

**F. step 9 증거 다이제스트**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | step 9 (full 전용) | 입력: `scaffold.md`, `prompt-decomposition.json`(원자 항목, `response_format`, `pipeline_tier`), `temp/claims-*.json`(**폐기 아닌** 노트 중 이 태그의 것. step 3은 이 필터가 없다), `consensus-claims.json`·`contradiction-graph.json`(있으면). 클레임 파일이 없으면 이 단계를 건너뛴다. 절차: ① 필터: `confidence == "high"`이거나 `evidence_type`이 `empirical`·`statistical`인 클레임만 남기고, 나머지에서는 `numbers`가 비지 않고 `quoted_support`가 비지 않은 것을 우선한다. 총 `claims_cap`(full 80–120개)으로 자른다(상한 내 우선순위 정렬은 정의되지 않았다, U-08) ② 원자 항목별로 묶는다: **주제 겹침으로** 판단하고 필드 완전 일치에 의존하지 않는다(`entities`·`stance_target`·`scope_conditions`·`claim` 텍스트를 종합). 애매하면 Ungrouped로 버리지 말고 가장 관련 있는 항목에 넣는다. 어느 항목에도 안 맞는 것만 맨 끝 "Ungrouped" 절 ③ 합의·논쟁 포함: `consensus-claims.json`이 있으면 그 클레임을 `[consensus]`로 표시해 포함, `contradiction-graph.json`이 있으면 상위 3~5개 논쟁 쌍을 양쪽의 `quoted_support`와 함께 포함 ④ `temp/evidence-digest.md`를 쓴다: 원자 항목마다 `### Atomic item: <이름>` 하나, 아래에 불릿 목록. 불릿 = `- <claim 텍스트> (<evidence_type>)` + 블록 인용된 `quoted_support` 원문 + `[source_note_id]`(C-12 예시). "스캔하기 쉽게, 서사가 아닌 증거 색인". 종료: 파일 존재, full에서 `claims_min`(30)개 이상(전체 클레임이 그보다 적으면 모두 포함), 원자 항목별 묶음·원문 인용·노트 id 포함. 이 단계는 `claims` 테이블, `quality_score`, 철회 표시를 읽지 않는다 | 코드 확인 |
| R-27 | step 9 이후 | 다음은 step 10. 스킬은 step 10이 파이프라인에서 가장 중요한 단계이며 full에서 draft-orchestrator 3개를 반드시 띄우라고 덧붙인다([entry-decompose.md](entry-decompose.md) 불변식 10). step 13이 `### Post-critic gap fill` 절을 이 파일에 덧붙인다([width-sweep.md](width-sweep.md) R-30) | 코드 확인 |

**G. 경계·플랫폼·강제**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-28 | step 10 이후 소비 | 1.2 표. 주의: `comparisons.md`는 step 8 이후 판이 초안의 입력이다. `source-tensions.json`·`comparisons.md`·`evidence-digest.md`는 step 10·11 입력 목록에 직접 명시되고, `loci.json`·`consensus-claims.json`·갭 JSON은 step 10 이후 스킬이 읽지 않는다. 세부는 [draft-synthesis](draft-synthesis.md) | 코드 확인 |
| R-29 | Codex 번역 | 단계 스킬의 spawn 문장은 명시적 지시이고 이름 붙은 에이전트를 모두 병렬로 띄우고 기다린다. 조사자(depth-investigator)는 Codex에서 잎이다: "자기 fetch·읽기로 locus를 끝내고 interim 노트를 쓴다"(C-11). Claude 쪽 조사자는 Task로 fetcher를 위임한다(R-15) | 코드 확인 |
| R-30 | 신뢰 경계 | `interim`·`source-analysis`는 신뢰하는 유형이라 `note show`가 `<untrusted-source>`로 감싸지 않는다(`untrusted.py:21`). 웹에서 가져온 소스 노트 본문은 감싸져 나오므로 조사자·critic은 그 안의 지시를 데이터로만 다룬다(조사자 프롬프트의 정책 블록, C-06 앞부분). interim 노트는 우리 에이전트가 쓴 요약이라 그 안에 웹 지시가 섞이지 않는다는 가정이다 | 코드 확인 |
| R-31 | 노트 색인 | `type: interim`은 DB `notes.type` CHECK에 허용된다(`models/note.py:27`, `core/db.py:26`). `temp/` 아래 본문 파일(`interim-report-*.md`, `evidence-digest.md`, 초안 등)은 frontmatter가 없어 노트 색인에 들어가지 않고(`core/sync.py:62-80`), `note new --body-file`이 만든 노트만 색인된다 | 코드 확인 |
| R-32 | 다이제스트 vs claims 테이블 | step 3~9는 모두 `temp/claims-*.json`을 직접 읽는다. step 2.7의 `claims ingest`가 만든 `claims` 테이블은 이 단계들이 쓰지 않는다(`claims search`·`matrix`는 step 10의 큐레이션·cite-check 쪽) | 코드 확인 |
| R-33 | 불변식 연결 | 진입 스킬이 이 단계들에 거는 불변식: "step 4는 변증적 locus ≥ 1(정당한 생략 제외)", "step 5의 모든 interim 노트는 `## Committed position`으로 끝남", "loci가 1개 이상이면 `comparisons.md` 필수(step 6)". 3번은 R-13, 4번은 R-17, 5번은 R-19에 대응하고 5번과 locus-coverage 계열은 lint(R-18)도 확인한다([entry-decompose.md](entry-decompose.md) 1.3 I 3~5) | 코드 확인 |
| R-34 | 강제 범위 | 파이썬이 아는 것: `levers set --rerender`(R-12), `locus-coverage`·`workflow` lint(R-18), `NoteType.INTERIM`·비울타리(R-30, R-31). 나머지(모순 쌍 규칙, 점수·예산 구간, 입장 형식, 갭 JSON, 다이제스트 선별)는 프롬프트에만 있고 어떤 코드도 `contradiction-graph.json`·`consensus-claims.json`·`source-tensions.json`·갭 JSON·`evidence-digest.md`를 읽지 않는다(`grep`: `cli/archive.py`가 옛 평면 레이아웃의 이름을 옮기고 `core/runs.py`는 docstring에서 언급할 뿐, lint는 `loci.json`·`comparisons.md`만 읽는다) | 코드 확인 |

- 불변식: (1) loci는 변증적 하나 이상(또는 정당화). (2) interim 노트마다 `## Committed position`, locus당 노트 하나. (3) loci ≥ 1이면 `comparisons.md` 존재. (4) 갭 JSON의 id는 `pp-`/`cc-` 접두어로 충돌하지 않는다. (5) 조사자는 `source_budget`을 넘어 fetch하지 않는다. (6) `source-tensions.json`은 이견마다 결론(resolution)을 가진다. 전제: 호스트가 프롬프트를 따른다.
- 미결정:
  - U-01 · R-05 · `consensus-claims.json` 항목의 모양(클레임 문장·노트 id·독립성 점수 필드 등)이 스킬에 없다. step 9는 "그 클레임을 `[consensus]`로 표시"하고 corpus-critic은 "고확신 합의"를 읽으므로 최소 클레임 텍스트와 원본 소스 id가 필요하다. 영향: 낮음~중간.
  - U-02 · R-10 · 구간별 상한(15/10/5/0~3)과 총 예산 `depth_budget_total`(40)의 관계가 없다. 6개 locus가 모두 30점 이상이면 상한 합 90이 총액 40을 넘는데 "비례 배분"의 방식이 정의돼 있지 않다. 영향: 중간(locus별 예산 숫자).
  - U-03 · R-11 · `flavor` 값 집합이 문서마다 다르고(스킬 `dialectical\|synthesis\|technical`, 분석가·조사자 `convergent\|dialectical`), 분석가 출력의 `corpus_evidence`·`opposing_positions`·`suggested_*`를 `loci.json`에 담으라는 지시가 없다. 조사자 프롬프트는 이 필드들이 담긴 "full locus object"를 받는다고 가정한다. step 5 spawn 템플릿이 넘기는 것은 5필드뿐이다. 영향: 중간(조사자가 출발점을 잃는다).
  - U-04 · R-08, R-17 · 조사자의 50% 넘는 실패나 분석가 전원 실패 때 "사용자에게 알리고 멈춘다/에스컬레이션"의 비대화형(`-p`) 처리 방법이 없다. 영향: 낮음.
  - U-05 · R-19 · 종료 조건은 "긴장마다 보정 메모(calibration note)"를 요구하지만 템플릿 4줄에는 보정 줄이 없다. 어디에 쓸지 미정. 영향: 낮음.
  - U-06 · R-20 · "가장 품질이 높은 소스"를 고르는 방법이 없다. `note list`는 `quality_score`를 출력하지 않고 정렬 키도 `created|updated|title|words`뿐이다(`cli/note.py:303-368`). `search --ranked`나 `sources list`를 쓰는지는 스킬에 없다. 영향: 낮음.
  - U-07 · R-24 · step 8 fetcher에 갭을 배정하는 방법(갭당 하나가 아님)과 fetcher 프롬프트의 `search_queries`·`gap_id` 처리(검색을 어디까지 허용하는지)가 없다. 영향: 중간.
  - U-08 · R-26 · 클레임 상한 안에서의 정렬(같은 필터 통과 클레임이 120개를 넘을 때 무엇을 먼저 남기는지), "the remainder" 우선순위의 정확한 의미가 없다. `quoted_support`가 비면 하류에서 보이지 않는다는 fetcher 규칙이 있을 뿐이다. 영향: 낮음~중간.
- 확인 한계: 프롬프트 준수와 LLM의 쌍 맺기·점수의 일관성은 정적 읽기로 확인할 수 없다. 코드는 실행하지 않았다. 호스트별(Claude/Codex) 에이전트 번역 결과는 읽지 않았다.

### 1.5 필수 코드 참조 [필수]

원문 프롬프트는 MIT 라이선스(overview 1절)로 인용 가능하다. 글보다 원문이 정확한 부분만 넘긴다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/hyperresearch/skills/hyperresearch-3-contradiction-graph.md:12-67` | step 3 전문: 입력, 모순 쌍 4기준, 클러스터 JSON, 순위, 합의 판정(독립성), 종료 | R-02~R-05 |
| C-02 | `skills/hyperresearch-4-loci-analysis.md:12-125` | step 4 전문: spawn 템플릿, 병합·클램프, 네 차원·예산 구간, `loci.json` 스키마, 조사자 수, inference depth 재검토, 불변식 | R-06, R-08~R-13 |
| C-03 | `src/hyperresearch/core/hooks.py:130-329` `LOCI_ANALYST_AGENT` | loci-analyst 프롬프트 전문(입력, 절차 1~5, 출력 JSON, 규칙) | R-07 |
| C-04 | `skills/hyperresearch.md:197-216` | 서브에이전트 spawn 규약(질문 원문·위치 진술·입력·shim 전문) | 1.3 A |
| C-05 | `core/hooks.py:262-298` | loci-analyst 출력 JSON 예시(필드 이름·모양) | R-07 |
| C-06 | `core/hooks.py:336-621` `DEPTH_INVESTIGATOR_AGENT` | 조사자 프롬프트 전문: 정책, flavor별 자세, 절차 1~6, interim 본문 템플릿, Committed position·보정 5필드·규범적 구체성 예시, 규칙 | R-15, R-16, R-30 |
| C-07 | `skills/hyperresearch-5-depth-investigation.md:12-101`, `-6-cross-locus-reconcile.md:11-72` | step 5 spawn 템플릿·완료 점검·불변식, step 6 질문 5개·`comparisons.md` 형식·종료 | R-14, R-17, R-19 |
| C-08 | `skills/hyperresearch-7-source-tensions.md:13-91` | step 7 전문: 입력·고아 스캔 범주·선별·결론 선결정·`source-tensions.json` 스키마·`shortfall_reason` | R-20 |
| C-09 | `src/hyperresearch/cli/levers_cmd.py:67-104`, `src/hyperresearch/core/levers.py:198-215`, `:277-288` | `levers set <tag> key=value… --rerender`, 검증(쓰기 전)·`LeverError` | R-12 |
| C-10 | `skills/hyperresearch-8-corpus-critic.md:12-131`, `core/hooks.py:3227-3348` `CORPUS_CRITIC_AGENT` | step 8 전문(사전 점검·병합·fetch 웨이브·평가)과 critic 프롬프트(절차 1~6, 갭 JSON, 규칙) | R-21~R-25 |
| C-11 | `src/hyperresearch/core/codex.py:210-218` `CODEX_AGENT_NOTES` | Codex에서 조사자는 잎 에이전트 | R-15, R-29 |
| C-12 | `skills/hyperresearch-9-evidence-digest.md:12-71` | step 9 전문: 필터·상한·그룹핑·합의·논쟁·출력 형식 예시·종료 | R-26 |
| C-13 | `src/hyperresearch/cli/lint.py:1005-1100`, `:1555-1650` | `locus-coverage`(누락 locus·중복 interim)와 `workflow`(loci만 있고 interim 없음, `comparisons.md` 없음) 규칙 | R-18 |
| C-14 | `src/hyperresearch/core/profiles.py:253-373` | `_FULL`·`_PREMIER` 수치 | 1.3 C |
| C-15 | `src/hyperresearch/core/untrusted.py:19-62`, `src/hyperresearch/models/note.py:13-40` | 신뢰 유형 집합, `NoteType.INTERIM` | R-30, R-31 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(스킬·에이전트 본문과 CLI 코드). 테스트는 열지 않았다. 프롬프트 사례는 호스트의 준수를 가정한 기대값이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `pipeline_tier=light` | step 2 후 곧바로 step 10. 3~9의 어떤 파일도 만들어지지 않고 step 10은 볼트를 직접 읽는다 |
| T-02 | R-02 | `temp/claims-*.json`이 하나도 없음 | step 3 전체 생략(두 파일 모두 없음), step 4는 코퍼스 산문 스캔, step 9도 생략 |
| T-03 | R-03, R-04 | 소스 A: stance_target "X" supports, 소스 B: 같은 target refutes | 한 클러스터(`side_a`=A의 클레임·노트 id, `side_b`=B), `decision_relevance`가 high면 앞순위. 코퍼스가 일치하면 `contradiction-graph.json`은 `[]` |
| T-04 | R-05 | 클레임 동의 소스: 4개 사본 클러스터 2개(크기 4 각각) | 독립성 점수 합 (1+3×0.25)×2 = 3.5로 ≥ 3.0이라 합의 후보이지만 "한 클러스터 = 한 표"로 세면 2표다(2.1 차이). 크기 2 클러스터 하나와 독립 소스 2개: 1.0+0.5+1+1 = 3.5 |
| T-05 | R-09, R-10 | importance 9, uncertainty 8, disagreement 7, decision_impact 9 | composite 33 → `source_budget` ≤ 15(full). composite 15 → ≤ 5, composite 8 → 0~3 또는 생략 |
| T-06 | R-08 | 분석가 a가 loci 8개, b가 7개를 낸다. 두 쌍은 이름이 같거나 핵심 질문이 같다 | 중복을 합치고 `loci_max`=6으로 자른다(하중이 약한 순으로 버림). 두 분석가의 `skip_loci`는 합집합 |
| T-07 | R-07, R-13 | 두 분석가 모두 dialectical locus가 없고 `skip_loci`에 정당화도 없다 | loci-analyst를 더 엄격한 프롬프트로 다시 spawn |
| T-08 | R-08 | 모든 분석가가 빈 `loci` | 사용자에게 "폭 탐색이 너무 얇다"고 알리고 중단. 코퍼스가 10개 미만이면 분석가 자신이 이미 중단하고 부모에게 알림 |
| T-09 | R-16 | locus `x`에 이미 `type: interim` + 태그 `locus-x` 노트가 있음 | 조사자는 `note new`를 하지 않고 `note update`로 고치거나 이미 조사됐다고 보고한다. 어긴 상태는 lint `locus-coverage` warning(중복) |
| T-10 | R-17 | 조사자 4개 중 3개 실패 | 50% 초과이므로 중단하고 사용자와 loci 품질 재검토. 1개 실패면 성공한 3개로 진행 |
| T-11 | R-17, R-18 | interim 노트가 서술 요약으로 끝나고 `## Committed position`이 없음 | 결함으로 표시, 그 조사자를 "committed position 강조"로 재spawn. (lint는 이 문자열을 검사하지 않는다) |
| T-12 | R-18 | `loci.json`에 locus 3개, interim 노트는 2개만 있음 | `locus-coverage` warning(1개 누락). 2개 누락이면 error. locus ≥ 1인데 `comparisons.md`가 없으면 `workflow` error. `run finish`의 통과 여부와는 무관 |
| T-13 | R-19 | locus 4개, interim 4개 | `comparisons.md`에 긴장 3~5개(full). locus가 1개면 그 입장을 유일한 닻으로 하는 문서 |
| T-14 | R-20 | step 4가 `skip_loci`로 locus 0개를 정당화(단일 목소리 코퍼스) | `comparisons.md` 없이 바로 고아 스캔. 이견이 2개뿐이면 그것과 `"shortfall_reason"`을 쓴 `source-tensions.json` |
| T-15 | R-21, R-23 | `time_periods=[Q3 2024 UNH]`이고 볼트에 UNH Q1 2025 10-Q만 있음 | `period-pinned-gaps.json`에 `pp-1`(`priority: critical`, `source_type: primary-filing`). critic spawn 후 `corpus-critic-gaps.json`은 `pp-1`이 앞, 이어서 `cc-1…` |
| T-16 | R-25 | `cc-2`(overturning)에 대해 fetcher가 반증 소스를 찾음 | `comparisons.md`에서 해당 입장의 확신도를 낮추고 약화를 기록. 깊이 조사는 재실행하지 않는다 |
| T-17 | R-26 | 후보 클레임 200개, 필터 통과 150개 | `claims_cap`(full 120)으로 자름, 원자 항목별 H3 + 인용 블록 + `[note-id]`, 합의는 `[consensus]` 표시, 논쟁 쌍 3~5개. 전체 클레임이 20개뿐이면 모두 포함(`claims_min` 30 미달 허용) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@aece65f `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `skills/hyperresearch-3-contradiction-graph.md:14`, `-4-loci-analysis.md:14`, `-5-depth-investigation.md:14`, `-6-cross-locus-reconcile.md:13`, `-7-source-tensions.md:15`, `-8-corpus-critic.md:14`, `-9-evidence-digest.md:14`, `-2-width-sweep.md:349-352`, `-10-triple-draft.md:62` | 각 스킬의 "Tier gate"를 읽음. step 4의 "proceed directly to step 9"(`:14`)는 step 9도 light에서는 건너뛰므로 낡은 문구 |
| R-02~R-04 | C-01(`skills/hyperresearch-3-contradiction-graph.md:20-56`) | 직접 읽음 |
| R-05 | C-01(`:58`), `core/independence.py`(source-quality R-12 경유) | 독립성 점수는 root 1.0, 나머지 `round(1/크기, 4)`이므로 클러스터 하나의 합은 1을 넘는다(크기 2 → 1.5, 크기 4 → 1.75). 스킬 문구의 "클러스터를 한 표로 센다"와 "점수 합 ≥ 3.0"은 서로 같지 않다. 코드 확인(source-quality 스펙 인용) |
| R-06~R-13 | C-02, C-03(`core/hooks.py:130-329`), `profiles.py:258-292`, `:345-355` | 직접 읽음. 에이전트 설명의 "1—<< p.loci_max + 2 >>"는 렌더링 시 8(premier 12). 분석가 출력 경로 예시 `research/loci-{analyst_id}.json`(`hooks.py:187`)은 낡은 레이아웃 |
| R-14~R-17 | C-06, C-07(`skills/hyperresearch-5-depth-investigation.md:30-101`) | 직접 읽음. 조사자의 `mkdir -p research/temp`(`hooks.py:485`)는 3.0 이전 레이아웃의 흔적이고 실제 본문 파일 경로는 `runs/<tag>/temp/interim-report-<locus>.md`(`:493`) |
| R-18 | C-13(`cli/lint.py:1005-1100`, `:1538-1650`), `core/runs.py:649-847`·run-manifest-gate 1.3의 검사 목록 | 직접 읽음. lint `RULES`가 `verify_run`에서 두 규칙만 불리는 것은 run-manifest-gate에서 확인 |
| R-19 | C-07(`skills/hyperresearch-6-cross-locus-reconcile.md:34-72`) | 직접 읽음. 종료 조건의 "calibration note"는 템플릿(`:49-60`)에 대응 줄이 없다 |
| R-20 | C-08 | 직접 읽음 |
| R-21~R-25 | C-10(`skills/hyperresearch-8-corpus-critic.md:31-131`, `core/hooks.py:3227-3348`), `cli/search.py:33` `--include-body` | 직접 읽음. critic 프롬프트 본문은 "Only `critical` and `high` priority"(`:3331-3332`)인데 스키마 문구는 `critical\|high\|medium`(`:3324`) |
| R-26, R-27 | C-12 | 직접 읽음 |
| R-28 | `skills/hyperresearch-10-triple-draft.md:26-32`, `:114-121`, `-11-synthesize.md:28-33`, `:176-178`, `-14-patcher.md:24-30`, `core/hooks.py:939` | 하류 스킬의 입력 목록을 읽음 |
| R-29, R-30, R-31 | C-11, C-15, `core/sync.py:62-80` | 직접 읽음 |
| R-32 | `grep`: step 3~9 스킬에 `claims search`·`claims matrix` 호출이 없음 | grep 결과 |
| R-33 | `skills/hyperresearch.md:287-303` | 진입 스킬 불변식 목록과 대조 |
| R-34 | `grep -rn "contradiction-graph\|consensus-claims\|source-tensions\|evidence-digest\|corpus-critic-gaps" src/hyperresearch`(파이썬 코드에는 참조 없음, 스킬·에이전트 프롬프트와 `agent_docs`뿐) | grep에 의존. 런타임 동적 경로는 추적하지 않음 |
| T-01~T-17 | 위 R-ID의 근거 | 구현에서 도출. T-04의 점수는 source-quality R-12 공식으로 계산 |

**문서와 구현의 차이·주의점**
- `flavor` 어휘: 스킬 4·5의 템플릿은 `dialectical|synthesis|technical`, 에이전트 프롬프트는 `convergent|dialectical`이다(U-03). 코드 확인.
- 독립성 합 vs "한 표": 위 R-05 근거. 구현(`sources independence`)은 클러스터별 점수만 쓰고 합의 판정에서 어떤 합을 쓰는지는 스킬 텍스트다. 코드 확인.
- critic 갭 priority: 스키마 문구에 `medium`이 있는데 규칙은 `critical`·`high`만 허용한다. 코드 확인.
- 스킬 8의 사전 점검 JSON 예시는 `{{ … }}`로 쓰였는데 스킬 렌더링은 `.format`이 아니라 치환이라 `{{`가 그대로 남는다(width-sweep 2.1과 같은 현상). 코드 확인.
- 깊이 조사자 프롬프트는 `locus`가 "분석가 출력의 전체 locus 객체"라고 하는데 step 5 템플릿은 5필드만 넘긴다(U-03). 코드 확인.

### 2.2 코드 읽는 순서 [선택]
진입 스킬 티어 표(`skills/hyperresearch.md:84-98`) → step 3·4 스킬 → `core/hooks.py:130` `LOCI_ANALYST_AGENT` → step 5 스킬 → `core/hooks.py:336` `DEPTH_INVESTIGATOR_AGENT`(interim 노트 템플릿이 핵심) → step 6·7 스킬 → step 8 스킬과 `core/hooks.py:3227` → step 9 스킬 → `cli/lint.py:1005`(강제되는 유일한 부분). 원본의 전략: 폭 코퍼스에서 "증거가 갈라지는 곳"을 먼저 구조화(3)해 locus가 직감이 아니라 모순에서 나오게 하고, locus마다 한 입장을 강제로 커밋(5)해 하류 초안이 서술이 아니라 논증이 되게 한다. 초안 전에 반증을 찾는 것(8)이 가장 싸다는 설계 의도는 스킬의 설명 문구(추론이 아니라 스킬 본문의 주장)다.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| (없음) | 아직 정해진 것 없음. 스펙을 어디에 쓸지 미정(overview 1절) | — | — |
