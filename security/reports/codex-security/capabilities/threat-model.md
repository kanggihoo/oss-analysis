---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
sources:
  - plugins/codex-security/skills/threat-model/SKILL.md
  - plugins/codex-security/skills/README.md
  - plugins/codex-security/skills/security-scan/SKILL.md
  - plugins/codex-security/skills/security-scan/references/scan-results.md
  - plugins/codex-security/skills/security-scan/references/sdk-files.md
  - plugins/codex-security/skills/security-diff-scan/SKILL.md
  - plugins/codex-security/references/threat-model.md
  - plugins/codex-security/references/core-scan.md
  - plugins/codex-security/references/artifact-storage.md
  - plugins/codex-security/references/scan-artifacts.md
  - plugins/codex-security/references/scan-contract.md
  - plugins/codex-security/references/scan-runtime.md
  - plugins/codex-security/references/final-report.md
  - plugins/codex-security/mcp-app/src/threat-model-schema.ts
  - plugins/codex-security/mcp-app/src/threat-model-render.ts
  - plugins/codex-security/mcp-app/src/threat-model-format.ts
  - plugins/codex-security/mcp-app/src/threat-model-document.ts
  - plugins/codex-security/mcp-app/src/artifact-contracts.ts
  - plugins/codex-security/mcp-app/src/finding-detail-schemas.ts
  - plugins/codex-security/mcp-app/src/artifact-scan-draft.ts
  - plugins/codex-security/mcp-app/src/artifact-storage.ts
  - plugins/codex-security/mcp-app/src/coverage-publication.ts
  - plugins/codex-security/mcp-app/src/workbench-client.ts
  - plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts
  - plugins/codex-security/mcp-app/src/deep-scan/artifact-validation.ts
  - plugins/codex-security/mcp-app/server.ts
  - plugins/codex-security/scripts/threat_model_projection.py
  - plugins/codex-security/scripts/report_projection.py
  - plugins/codex-security/scripts/finalize_scan_contract.py
  - plugins/codex-security/scripts/workbench_saved_results.py
  - plugins/codex-security/scripts/workbench_setup.py
  - plugins/codex-security/scripts/workbench_db.py
  - plugins/codex-security/scripts/workbench_constants.py
  - plugins/codex-security/scripts/workbench/retained_records.py
  - plugins/codex-security/scripts/workbench/saved_outputs.py
  - plugins/codex-security/scripts/reserved_artifact_paths.json
  - plugins/codex-security/schemas/scan-manifest.schema.json
  - sdk/typescript/src/api.ts
  - sdk/typescript/src/artifact-export.ts
depends:
  - ./caller-modes.md
status: draft
---

# Threat model 생성·저장

> 스캔 초반에 모델이 지침(`threat-model` skill, `references/threat-model.md`)에 따라 아키텍처·공격자·보호 자산 모델을 만들고, `record_codex_security_scan_draft`의 `threatModel`로 early checkpoint에 저장하면, 코드가 형식을 검사해 `scan-manifest.json`의 `scan.threatModel`에 보존하고 `threatmodel.md` 문서로 투영하는 기능이다.

<!--
이 레포에는 정적 분석 코드가 없다. 모델 내용(어떤 경계를 찾고 어떻게 쓰는가)은 skill·reference 문서가 모델에게 주는 지침이다. R-ID 앞의 [지침]은 문서가 모델에게 요구하는 규칙(검증 수준 `코드 확인` = 그 지침 문장을 읽었다는 뜻), [강제]는 코드가 검사하거나 만드는 규칙이다. 모델이 [지침]을 실제로 따르는지는 실행하지 않았으므로 R-32가 `미확인`으로 묶는다.
용어: "per-scan 모델"은 한 scan의 `scan.threatModel`에 담긴 모델, "shared cache"는 저장소 하나에 대해 `threatmodel.md`를 standalone 저장소에 두는 재사용 문서(R-26), "projection"은 canonical `scan.threatModel`에서 코드가 만드는 `threatmodel.md`다.
선행 스펙 caller-modes.md가 정의한 호출자 모드, scan 등록, 시작·완료 도구, `CODEX_SECURITY_*` 환경 변수는 다시 설명하지 않고 그 스펙의 R-ID로 참조한다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 workbench-owned Standard scan(`start_codex_security_standard_scan`으로 시작, caller-modes R-25)이 모델을 만들고 저장하는 경로다. 순서는 이 순서다.

1. 모델(LLM)이 scan에 쓸 threat model의 출처를 고른다. 사용자가 준 모델이 있으면 그대로 두고, 없으면 새로 만든다(R-01~R-05). Standard와 Deep worker는 `threat-model` skill을 부르지 않고 자기 workflow 안에서 `references/threat-model.md`를 읽고 만든다(R-05).
2. 모델이 소스를 읽고 아키텍처, 신뢰 경계, 공격자 능력, 보호 자산을 정리한다(R-06~R-08). 결과는 구조화 객체(`summary` + 5개 목록) 또는 Markdown 문서(`{format:"markdown", content}`)로 만든다(R-09).
3. 첫 번째로 쓸 만한 모델이 나오면, findings가 아직 없어도 `record_codex_security_scan_draft({ scanId, complete:false, threatModel, findings:[], reviewState })`로 저장한다(R-10).
4. MCP 서버가 입력을 zod 스키마로 검사한다(R-15). 이전 draft가 있으면 모델을 이어받을지 정한다(R-17, R-18). workbench `write-scan-draft`가 `scan-manifest.json`·`findings.json`·checkpoint를 쓰고(R-20), 같은 호출 안에서 `threatmodel.md`를 렌더해 쓴다(R-20, R-22). 렌더가 실패해도 draft는 저장되고 `warnings`에 사유가 실린다(R-20).
5. Standard scan이면 workbench가 phase를 정한다. 모델만 담은 checkpoint는 `threat_model` phase에 그대로 두고, 후보나 surface가 들어온 draft부터 phase를 `discovery`로 올린다(R-19).
6. 이후 phase가 모델을 입력으로 쓴다. 모델은 `read_codex_security_artifact`로 `threatmodel.md`를 읽거나 자기 context의 모델 텍스트를 쓴다(R-14). 후속 draft가 `threatModel`을 생략하면 코드가 이전 모델을 이어붙인다(R-17).
7. 최종 `complete:true` draft는 보존한 모델을 다시 실어 보낸다(R-10). 완료(finalize)할 때 같은 projection 함수가 한 번 더 `threatmodel.md`를 쓴다(R-21). 저장된 모델의 내보내기는 `cs export`·앱 도구가 맡고 이 스펙 밖이다(R-31).

SDK-owned Standard(`cs scan`)에서는 draft 도구가 없을 때 모델이 `CODEX_SECURITY_SCAN_DIR`의 `scan-manifest.json`에 `scan.threatModel`을 직접 쓰고(caller-modes R-41), SDK의 finalize가 4단계의 렌더와 같은 함수로 `threatmodel.md`를 만든다(R-21).

### 1.2 범위·통합 지점 [필수]
- 제공: (가) 모델이 따를 threat modeling 지침(출처 선택, 모델링 내용, 결과 형식, checkpoint 시점, shared cache 규칙), (나) `threatModel` 입력 스키마와 그 검사, (다) draft 사이의 모델 보존 규칙, (라) `threatmodel.md` projection의 렌더 규칙과 쓰는 시점, (마) `threatmodel.md`를 scan 중에는 모델이 직접 못 쓰게 하는 경계와 standalone shared cache의 저장 위치.
- 제외:
  - draft 전체의 검증·확정·봉인 규칙(행 9). 이 스펙은 `threatModel` 필드가 그 안에서 어떻게 다뤄지는지만 다룬다.
  - 호출자 모드, scan 등록, 시작·완료 도구, 환경 변수(행 1, 선행 스펙).
  - Standard 감사 본문과 worker 위임(행 2).
  - Deep coordinator의 반복·종료(행 7). worker가 낸 모델을 aggregate에 합치는 한 규칙만 경계로 둔다(R-30).
  - `threat-model-visualize` skill(이번 범위 밖).
  - `cs export --artifact threat-model` 등 내보내기 CLI와 앱 도구(이번 범위 밖). 경계 한 줄만 R-31에 있다. SDK의 `writeThreatModel`(`sdk/typescript/src/artifact-export.ts`)은 `finalize_scan_contract.py --write-threat-model`을 실행하는 얇은 호출이고 `security-policy.ts`의 `cs policy` 흐름에서만 호출된다(이 SHA에서 찾은 호출처는 그 한 곳이다. 근거 범위는 2.1 R-31).
- 외부 의존·선행 계약: 선행 스펙 [caller-modes.md](./caller-modes.md)가 정의한 scan 소유 증명(claim token, owner thread)과 draft 도구가 서는 scan context. workbench(Python + SQLite)가 draft를 게시하고 `scan_dir`을 소유한다. LLM이 지침을 읽고 따른다고 가정한다(R-32).
- 소유 상태·부작용: `<scan_dir>/scan-manifest.json`의 `scan.threatModel`과 `scan.complete`, `<scan_dir>/checkpoints/*.json`·`checkpoint-head.json`에 실린 모델, `<scan_dir>/threatmodel.md`(projection, 봉인 대상이 아닌 편의 문서), Deep·Standard worker의 출력 디렉터리 `result.json`·`threatmodel.md`, standalone shared cache 디렉터리의 `threatmodel.md`, workbench `scans.phase`(R-19).

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 `threatModel` 값

`record_codex_security_scan_draft`의 입력 필드 `threatModel`(선택)과 `scan-manifest.json`의 `scan.threatModel`, worker `result.json`의 `threatModel`이 같은 형태다. 정확한 검사식은 C-02다. 의미만 적는다.

| 형태 | 필드 | 의미·제약 |
|---|---|---|
| 구조화 | `summary`(필수, 공백만 아닌 string), `assets`·`trustBoundaries`·`attackerCapabilities`·`securityObjectives`·`assumptions`(선택, 공백만 아닌 string의 list) | 지침의 필드 매핑은 C-01(`references/threat-model.md`의 `Scan Result Contract` 표). 추가 필드를 거부하지 않는다(looseObject) |
| Markdown | `format`(`"markdown"` 고정), `content`(필수, 공백이 아닌 문자가 하나 이상인 string), `scope`(선택), `origin`(선택) | `content`가 문서 본문 그대로다. `scope`는 모델이 다룬 소스 범위이고 scan 범위와 다를 수 있다 |
| `scope` | `includePaths`(필수, 비어 있지 않은 string의 list), `excludePaths`(선택, 같은 형), `summary`(선택, 비어 있지 않은 string) | draft 최상위 `scope`(scan 범위)와 다른 필드다(R-16) |
| `origin` | `"generated"` \| `"provided"` \| `"reconciled"` \| `"recovered"` | 출처 표시일 뿐이다. 코드는 값의 사실 여부를 검사하지 않는다(R-28) |

구조화 형태가 union의 첫 분기라서 `summary`가 있는 객체는 `format:"markdown"`이 같이 있어도 스키마를 통과한다. 렌더는 이 경우 Markdown `content`가 유효하면 그것을 본문으로 쓴다(R-22).

#### 1.3.2 도구와 파일

| 연산·데이터 | 입력·출력 | 의미·제약 |
|---|---|---|
| `record_codex_security_scan_draft` | 입력 `{ scanId, handoffClaimToken?, complete?, scope?, threatModel?, findings, reviewState }`(`complete` 생략 = 최종). 결과 `{ scanId, findingCount, surfaceCount, reviewState, operation:"replace", status:"draft_written", warnings? }` | 도구 설명이 "The host derives threatmodel.md"라고 적는다. 인가·소유·진행 중 scan 검사는 행 9와 caller-modes R-28·R-29 |
| `scan-manifest.json` | `scan.threatModel`(위 형태), `scan.complete:false`(checkpoint일 때만) | canonical 저장소다. projection은 이 값에서 만든다 |
| `threatmodel.md` | UTF-8 Markdown | 본문 + `---` + `## Saved Model Context` 이하 provenance 푸터(R-22). 파일 쓰기는 owner 읽기·쓰기 옵션으로 한다 |
| `save_codex_security_artifact` / `read_codex_security_artifact` | `{ scanId \| targetPath, handoffClaimToken?, storage, path, content? \| sourcePath? }` | `scanId` 없이 `targetPath`만 주면 standalone 저장소다(R-25, R-26) |
| shared cache 푸터 | 문서 끝에 `Repository: <stable target identity>`, `Version: <revision 또는 snapshot digest>` 두 줄 | 모델이 쓰고 모델이 비교한다. 코드는 읽지 않는다(R-26) |

### 1.4 행동 규칙과 남은 질문 [필수]

#### 모델이 따르는 지침 ([지침])

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [지침] `$threat-model` skill이 모델을 고를 때, 사용자가 모델이나 권위 있는 보안 지침(authoritative guidance)을 지정함 | 개정을 요청받지 않았으면 그것을 그대로 보존한다 | 코드 확인 (지침 문장) |
| R-02 | [지침] scan에 supplied 모델, 비어 있지 않은 `userContext`, authoritative knowledge base, 더 좁은 scope 중 하나가 있음 | supplied 모델을 보존하거나 이 scan용 모델을 새로 만든다. shared cache를 읽지도 바꾸지도 않는다 | 코드 확인 (지침 문장) |
| R-03 | [지침] R-02에 해당하지 않음 | shared model의 마지막 `Repository`·`Version` 줄이 대상과 현재 revision 또는 snapshot digest에 일치하고, 사용자가 교체·생성·개정을 요청하지 않았을 때만 재사용한다. cache를 우회하라는 host 지시는 따른다 | 코드 확인 (지침 문장) |
| R-04 | [지침] 저장소의 `AGENTS.md`나 해석한 `SECURITY.md`가 필요한 경계를 서술하고 fresh·context별 모델이 필요 없음 | 그 지침이 모델 대신이 될 수 있다 | 코드 확인 (지침 문장) |
| R-05 | [지침] 어떤 흐름이 모델을 만드는가 | `threat-model` skill의 사용 조건은 "이미 threat modeling phase에 있거나, 사용자가 `$threat-model`을 명시하거나, 저장소 모델을 만들거나 고치거나 저장하라고 명시한 때"이고 전체 PR·commit·branch·patch·저장소 scan의 주 trigger가 아니다. Standard와 Deep worker는 이 skill을 부르지 않고 `core-scan.md` 3번(`references/threat-model.md`를 읽어 매핑)으로 자기 workflow 안에서 만든다. diff scan은 `$threat-model`을 한 번 돌리거나 supplied 모델을 쓴다. Standard·Deep 경로의 지침 파일에는 shared cache 규칙이 없다(2.1) | 코드 확인 (지침 문장) / 부재 주장은 2.1 |
| R-06 | [지침] 모델링 내용 | 제품·사용자·인터페이스·구성요소·실행/배포 모드를 식별하고, 대표 입력을 실제 진입점→통제→민감한 소비자까지 따라가 행위자·이동하는 데이터나 권한·보호 자산·불변식을 정한다. 라이브러리는 기본 강제 보호와 호출자가 켜야 하는 보호를 가른다. 설정·배포가 경계를 바꾸면 실제 경로를 추적한다. 변경·게시 동작은 target·account·revision·payload의 결속을 추적한다. 코드로 확정한 사실은 저장소 상대 경로와 줄을 인용하고, 인용을 반환 전에 확인하며, 코드 근거·제공된 배포 사실·가정·미지를 구분한다. 비밀 값은 복사하지 않고 key·위치·수신자·통제만 쓴다. 소스 검토는 읽기 전용·오프라인이다 | 코드 확인 (지침 문장) |
| R-07 | [지침] 위협 시나리오 | 시나리오는 가설이지 확인된 finding이 아니다. 경계마다 현실적인 공격자와 시작 능력, 통제하는 입력, 진입점, 기대 통제, 민감 동작, 실패 시 새로 얻는 능력을 적고, 영향·도달 가능성으로 우선순위를 정한다. 신뢰된 운영자 설정을 공격자가 통제한다고 가정하거나 원격 노출·tenant·없는 통제·수용된 위험을 지어내지 않는다. 공격자가 이미 가진 권한과 자기에게만 미치는 영향은 새 보안 영향이 아니다 | 코드 확인 (지침 문장) |
| R-08 | [지침] 복잡하거나 불확실한 경계 | 호출자의 허용이 있으면 기존 scan 안에서 독립 architecture reviewer를 쓴다. 새 worker pool을 만들지 않는다. reviewer에게는 생성한 가설·finding 없이 소스 범위, 정확한 user context, supplied 모델·정책, knowledge base, `references/threat-model.md`를 준다. 반환 주장은 소스로 확인하고, 부모가 직접 했으면 독립 검토라고 부르지 않는다 | 코드 확인 (지침 문장) |
| R-09 | [지침] scan 결과 계약 | supplied 스키마 유효 모델은 그대로 보존한다. supplied 텍스트는 `{format:"markdown", content:<원문>, origin:"provided"}`로 보존하고 선언된 scope를 알면 기록한다. 생성한 모델은 canonical `threatModel`로 쓰고 `origin:"generated"`·알려진 `scope`를 넣을 수 있으며, 구조화 필드 매핑은 C-01 표를 따른다. supplied·복구된 worker 모델이 부모 scope를 자동으로 덮지는 않는다. 근거는 사실 옆에 두고 제공된 context에 표시한다. 중요한 시나리오는 finding, 근거 있는 처분, 열린 질문으로 정리한다. 해결된 통제 질문과 기각은 `reviewState.surfaces[].notes`에 소스 앵커와 함께, 미해결 전제는 `reviewState.openQuestions`에 둔다. 확립된 불일치는 finding이 없어도 유지하고 별도의 추측성 finding 목록을 만들지 않는다 | 코드 확인 (지침 문장) |
| R-10 | [지침] checkpoint 시점 | 첫 번째로 쓸 만한 모델이 나오면 findings가 없어도(`findings: []`) `complete:false` semantic checkpoint로 `record_codex_security_scan_draft`에 즉시 저장하고, 증거가 바뀌면 갱신하며, 최종 `complete:true` draft에 보존한 모델을 다시 싣는다. 아키텍처 매핑만으로는 완료된 audit coverage가 성립하지 않는다. SDK-owned이고 draft 도구가 없으면 같은 모델을 `scan-manifest.json`에 직접 쓴다(caller-modes R-41). diff scan은 host-backed scan이면 모델링 전에 phase를 `threat_model`로 올린다 | 코드 확인 (지침 문장) |
| R-11 | [지침] diff scan의 모델 범위 | 사용자가 더 좁은 범위를 요청하지 않으면 저장소를 모델링한다. 모델의 실제 범위(`threatModel.scope`)를 변경 파일 범위(scan 범위)와 따로 기록한다 | 코드 확인 (지침 문장) |
| R-12 | [지침 + 강제 일부] knowledge base가 있는 SDK scan | [강제] SDK `scanPrompt`는 knowledge base가 준비된 때만(`standard` 분기와 비`standard` 분기 모두) "knowledge base 문서는 source of truth이고 충돌하는 SECURITY.md·생성 모델을 덮어쓴다(명시적 user 지시 제외), 이 scan용 threat model을 shared cache를 읽거나 바꾸지 말고 다시 생성하라"는 문단을 prompt에 넣는다. [지침] 모델이 그대로 따른다. 모델링 지침도 "knowledge-base 사실은 생성한 가정과 저장소 정책을 덮는다"고 적는다 | 코드 확인 (prompt 문단) / 준수는 R-32 |
| R-13 | [지침] standalone 요청 | 문서를 `save_codex_security_artifact`(`targetPath`, `storage:"persistent"`, `path:"threatmodel.md"`)로 저장하거나 유효한 cache hit이면 기존 문서 경로를 돌려준다. 재사용 가능한 저장소 모델을 직접 만들거나 고치라는 요청은 host가 막지 않는 한 shared output을 갱신할 수 있고, 이때만 `Repository`·`Version` 푸터를 붙인다. per-scan 모델을 저장·내보내는 것은 shared cache 갱신 권한이 아니다. 문서는 아키텍처·배포, 자산·경계, 공격자 능력, 우선순위 시나리오·완화, severity 고려를 설명하고 시나리오는 검증 전까지 가설로 표시한다 | 코드 확인 (지침 문장) |
| R-14 | [지침] scan 중 모델 반환과 후속 phase | scan 중에는 `{format:"markdown", content:<정확한 모델 텍스트>}`를 호출자에게 돌려주고 checkpoint로 저장한다. `threatmodel.md`는 host가 만들므로 모델이 따로 쓰지 않는다. 선택한 텍스트를 이후 phase에서 보존한다. 후속 phase는 retained canonical 내용이나 `threatmodel.md`를 쓰고, 오래된 `context_dir/threat_model.md`는 canonical 모델이 없을 때만 읽는다 | 코드 확인 (지침 문장) |

#### 코드가 강제하는 규칙 ([강제])

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-15 | [강제] `record_codex_security_scan_draft`에 `threatModel`이 있음 | 입력은 `scanDraftInputSchema`(strict object)로 검사한다. `threatModel`은 C-02의 union이다. 구조화 분기는 `summary`가 공백 아닌 문자를 가진 string이어야 하고 5개 목록은 선택이며 원소는 공백 아닌 문자를 가진 string이다. Markdown 분기는 `format:"markdown"`과 공백 아닌 문자를 가진 `content`가 필요하고 `scope`가 있으면 `includePaths`가 비어 있지 않은 string의 list여야 하며 `origin`이 있으면 4개 값 중 하나여야 한다. 위반은 draft 전체를 거부하고 아무것도 저장하지 않는다. `threatModel` 자체는 선택이라 생략해도 통과한다. Python `write-scan-draft`는 `scan.threatModel`을 스키마로 다시 검사하지 않는다(2.1). 모델의 완결성 검사는 finalize 쪽 `scan-manifest.schema.json` 검증이 맡는다(행 9) | 코드 확인 (TS 검사) / finalize 쪽은 추론 |
| R-16 | [강제] 모델의 범위와 scan의 범위 | draft 최상위 `scope`는 `includePaths`·`excludePaths`를 받지 않는다(`z.never`). scan 범위는 host가 `buildScope`로 workbench 계약(`requiredIncludePaths`·`requiredExcludePaths`)에서 채워 manifest `scan.scope`에 쓴다. 모델 범위는 `threatModel.scope`에만 있다. 코드는 둘을 비교하지 않고, projection 푸터가 둘을 따로 보여 준다(R-22) | 코드 확인 |
| R-17 | [강제] 부모 scan draft(`complete:false` 또는 `true`)가 `threatModel`을 생략하고 이전 저장본(직전 draft, checkpoint, 보관된 worker checkpoint) 중 모델이 있는 것이 있음 | 수정 시각이 가장 새로운 저장본의 모델을 복제해 이번 결과에 붙인다. draft가 `threatModel`을 주면 그것이 통째로 이전 모델을 대체한다(필드 단위 병합은 없다). Standard worker draft도 같은 함수를 쓴다. Deep 터미널 draft는 이전 manifest의 모델만 이어받는다 | 코드 확인 |
| R-18 | [강제] 이미 최종(`complete`가 `false`가 아닌) 저장본이 있는데 `complete:false` draft가 옴 | 결과의 기반은 그 최종 저장본이 된다. 이번 draft의 `reviewState` 진행분만 조건부로 합쳐지고, 이번 draft의 `threatModel`은 쓰이지 않는다. 최종 저장본의 모델이 남고, 최종 저장본에 모델이 없으면 다른 저장본에서 찾은 모델을 붙인다. 이번 draft가 새 모델을 가져와도 반영되지 않는다 | 코드 확인 |
| R-19 | [강제] Standard scan에서 draft가 게시됨 | 모델만 담은 checkpoint(`complete:false`, `threatModel`이 객체, `findings` 없음, `reviewState.surfaces`·`deferred` 없음)는 phase를 바꾸지 않는다. 그 밖의 draft는 phase가 더 앞일 때만 `complete:false`면 `discovery`, 최종이면 `reporting`으로 올리고 그때 `scan_progress`의 phase 항목 수를 0으로 되돌린다. phase 순서는 `preflight`, `threat_model`, `discovery`, `validation`, `attack_path`, `reporting`이다. diff·Deep scan은 draft로 phase를 올리지 않는다 | 코드 확인 |
| R-20 | [강제] 부모 scan draft가 `write-scan-draft`로 게시됨 | workbench가 completion lock 안에서 `findings.json`·`scan-manifest.json`(`scan.threatModel` 포함)·checkpoint를 쓴 뒤 같은 lock 안에서 `write_threat_model_projection_if_possible`로 `threatmodel.md`를 쓴다(C-05, C-06). 그 쓰기가 `ContractError`나 `OSError`로 실패하면 파일을 만들지 않고, `Automatic threat model save failed: …` 경고를 stderr에 내고 결과 `warnings`에 싣는다. 게시된 manifest·findings는 되돌리지 않고 응답은 `status:"draft_written"`이다. 경고는 TS가 결과 `warnings`로 전달한다 | 코드 확인 |
| R-21 | [강제] finalize(`finalize_scan`)가 `scan-manifest.json`을 쓴 뒤 | 같은 `write_threat_model_projection_if_possible`를 prepared manifest로 호출한다. 경고는 `projection_warnings`에 중복 없이 덧붙는다. manifest의 `scan.artifacts`에 `threatmodel.md`(대소문자 무시) 경로가 기록돼 있으면(봉인된 scan이 이 경우다) 쓰지 않고 `None`을 돌려준다. `threatModel`이 객체가 아니면 아무것도 쓰지 않으며 이미 있는 `threatmodel.md`를 지우지 않는다 | 코드 확인 (지우는 호출이 없다는 점은 함수 본문 범위 안) |
| R-22 | [강제] projection 렌더 | 본문은 Markdown `content`가 공백 아닌 문자를 가지면 그 `content` 그대로, 아니면 `# Threat Model` + 빈 줄 + `summary`(공백뿐이면 "No explicit canonical threat-model summary was recorded.") + 값이 있는 섹션마다 `## <Assets\|Trust Boundaries\|Attacker Capabilities\|Security Objectives\|Assumptions>`와 `- ` 목록(줄바꿈은 두 칸 들여쓰기)이다. 본문 뒤에 `---`, 빈 줄, `## Saved Model Context`, 빈 줄과 아래 줄들을 붙인다. `Source`·`Scan`·`Target`·`Revision`·`Snapshot`·`Result status`는 provenance에 값이 있을 때만, `Model origin`은 항상(없으면 `not recorded`), `Model scope`는 항상(`includePaths`가 문자열 list가 아니면 `not recorded`), `Scan scope`는 provenance에 `scanScope`가 있을 때만 쓴다. 범위 줄은 `includePaths`를 쉼표로 잇고 `excludePaths`가 있으면 `<label> exclusions`, `summary`가 있으면 `<label> description` 줄을 더한다. provenance `provisional`이 참이면 마지막에 "This is a provisional model saved before successful completion."을 붙인다. scan에서 온 provenance는 `status`가 `completed`인데 `sealedAt`이 없으면 `draft`로 바꾸고 `provisional`을 참으로 한다. 경로 이스케이프·텍스트 정규화는 C-04, 푸터 줄 구성은 C-03이다 | 코드 확인 (draft 푸터가 `Result status: draft`·`provisional`이 되는 것은 workbench binding에 `status` 키가 없다는 읽기에서 온 추론) |
| R-23 | [강제] 렌더 입력이 잘못됨 | `threat_model_projection.render_threat_model`이 `ValueError`를 낸다. Markdown이 비어 있으면 "threatModel.content: expected non-empty Markdown", 구조화에서 `summary`가 문자열이 아니거나 비어 있으면 "threatModel.summary: expected a non-empty string", 섹션이 list가 아니거나 원소가 비어 있으면 "threatModel.<key>[…]…", Markdown 메타데이터에서 `origin`이 4개 값 밖이면 "threatModel.origin: unsupported value", `scope`가 객체가 아니거나 `includePaths`가 없으면 "threatModel.scope: expected an object with includePaths"를 낸다. 단, 구조화 검사를 통과하는 객체(`summary`가 있고 섹션이 유효)에 유효한 Markdown `content`가 있으면 메타데이터 검사를 건너뛰고 `content`를 쓴다. finalize 쪽 `_render_threat_model`은 이 오류를 `ContractError("threat model projection failed: …")`로 바꾸고, write-if-possible는 그것을 R-20의 경고로 처리하며, export는 그대로 실패한다 | 코드 확인 |
| R-24 | [강제] worker 디렉터리 draft(`recordCodexSecurityWorkerScanDraft`) | `preserveScanDraft` 안에서 worker draft를 검사하고(`validateWorkerReport`: `findings`·`scope`·`threatModel`이 well-formed Unicode·유한 숫자·안전 정수 JSON) 이전 저장본과 합친(R-17) 결과로 `result.json`을 교체한 다음, 다음 checkpoint를 지연시키지 않게 그 뒤에 `saveThreatModelDocument`를 부른다. 이 함수는 plugin 경로(`pluginRoot`)가 없으면 아무것도 하지 않고, 같은 `root`의 쓰기를 직렬화하며, `result.json`의 `threatModel`을 TS 렌더러(`renderThreatModel`, Python 렌더와 같은 규칙으로 쓰였다)로 worker 출력의 `threatmodel.md`에 쓴다. 실패하면 던지지 않고 "The threat model was saved, but threatmodel.md could not be written: …" 경고를 돌려준다. provenance는 `source:"worker"`, `scanId`, `target`에 **저장소 루트의 전체 경로**, `revision`, `status`(기본 `running`), `provisional`(`status`가 `complete`가 아니면 참)이고 `scanScope`는 `{includePaths:[<scope>]}`뿐이다. Python의 부모 provenance(표시 이름, manifest scope 전체)와 다르다 | 코드 확인 / 두 렌더러의 출력 동등성은 추론 |
| R-25 | [강제] `save_codex_security_artifact`·`read_codex_security_artifact`로 `threatmodel.md`를 다룸 | persistent 저장소에서 `scanId`가 있는 호출은 쓰기를 거부한다("Use the existing scan tools for canonical artifacts, ledgers and checkpoints."). Python `save-scan-artifact`도 `artifacts/`·`findings/`·`hardening/` 아래나 `report_validation.md`가 아니면 거부한다(`threatmodel.md`가 걸린다). `scanId`가 있는 읽기와, `scanId` 없는 standalone 읽기·쓰기는 허용한다. `threat_model.md`는 standalone 읽기만 허용한다. Python `save-scan-artifact`는 scan이 `running`이고 봉인되지 않았을 때만 쓰기를 받는다 | 코드 확인 |
| R-26 | [강제] shared cache의 위치와 코드가 하는 일 | 위치는 `<scanRoot>/<이름>/artifacts-<sha256>/threatmodel.md`다. `scanRoot`는 workbench `resolve-scan-root`(`CODEX_SECURITY_SCAN_ROOT`가 있으면 그것, 없으면 상태 디렉터리의 `scans`, caller-modes 1.3.4)가 주고, `<이름>`은 `fs.realpath`된 `targetPath`의 basename에서 `[^a-zA-Z0-9._-]+`를 `-`로 바꾼 값, `<sha256>`은 그 realpath 문자열의 sha256 16진수다. `targetPath`는 `inspect-target`이 절대 경로를 `resolve()`한 디렉터리(git 최상위로 올리지 않는다)다. 이 경로(와 `scanRoot`)가 대상 저장소 안이면 "Artifact storage must be outside the target repository."로 거부한다. 코드는 파일 바이트를 그대로 저장·반환할 뿐이고 `Repository`·`Version` 푸터를 읽거나 비교하거나 쓰는 코드를 찾지 못했다. 재사용 판단은 전부 모델이 한다 | 코드 확인 / 없다 주장은 2.1 |
| R-27 | [강제] `threatModel` 없이 scan을 끝냄 | 코드는 모델의 존재를 요구하지 않는다. draft 입력에서 선택이고, `scan-manifest.schema.json`의 `scan.required`에 `threatModel`이 없으며, `_read_saved_threat_model`은 모델이 없는 봉인 scan에서 그대로 `None`을 돌려준다. 모델을 먼저 만들게 하는 것은 R-10의 지침뿐이다 | 코드 확인 / 없다 주장은 2.1 |
| R-28 | [강제] supplied 모델 보존·생성 모델 구분 | 코드에는 "이 모델이 supplied인가"를 구분하거나 보존을 강제하는 곳이 없다. 코드가 하는 일은 R-15의 형식 검사, R-17·R-18의 이어붙이기, R-22의 verbatim 렌더뿐이다. `origin`은 선택적 라벨이다. 이 스펙 범위에서 코드가 값을 붙이는 곳은 `"recovered"`(R-29)뿐이고, `"reconciled"`를 정하는 코드는 찾지 못했다. 같은 scan에서 모델이 supplied 모델을 다른 내용으로 draft에 보내면 그대로 저장된다 | 코드 확인 / 없다 주장은 2.1 |
| R-29 | [강제] 복구(recovery)가 보관된 worker draft를 읽음 | draft에 `threatModel`이 있고 객체면 `origin`을 `"recovered"`로 덮은 사본을 `scan-manifest.schema.json`의 `scan.threatModel` 스키마로 검증하고 안전한 JSON인지 확인한다. 실패하면 그 모델만 draft에서 빼고 "<relative>: Skipped malformed threat model: …" 경고를 남긴다. 객체가 아니면 `origin` 덮기를 건너뛰고 스키마 검증에서 걸린다 | 코드 확인 |
| R-30 | [강제] Deep 부모가 worker 결과를 aggregate에 합침 | 먼저 합쳐지는 worker의 `threatModel`이 aggregate의 `threatModel`이 된다(`??=`). 이후 worker의 모델이 깊은 비교로 다르면 그 worker의 `reviewState.reviews[]` 항목에 `threatModel`로 따로 남는다. 같으면 남기지 않는다 | 코드 확인 |
| R-31 | [강제] 저장된 모델을 읽어 내보냄(경계) | `_read_saved_threat_model`은 manifest(없으면 policy draft)의 `scan.threatModel`을 먼저 읽어 projection 바이트와 provenance를 만들고, 없을 때만 `threatmodel.md`·`THREAT_MODEL.md`·`artifacts/01_context/threat_model.md`·`threat_model.md` 순으로 파일을 `{format:"markdown", content}`로 읽는다(봉인 scan은 manifest에 기록된 artifact만). 내보내기(`exports/threatmodel.md`)는 이 값을 쓴다. 이 스펙은 여기까지만 다룬다 | 코드 확인 (`_read_saved_threat_model`) / 내보내기 CLI 본문은 읽지 않음 |
| R-32 | 모델이 [지침] 규칙(R-01~R-14)을 따르는가: 출처 선택과 cache 조건 판단, 경계·인용의 정확성, 시나리오를 가설로 표시, 첫 모델에서 checkpoint 저장, `Repository`·`Version` 푸터 작성, 독립 reviewer 사용 | 실행하지 않았다. 서버가 하는 검사는 R-15~R-30이 정한 형식·소유·보존뿐이고, 모델 내용의 정확성이나 지침 준수는 코드가 검사하지 않는다 | 미확인 |

- 불변식:
  - `threatmodel.md`는 canonical `scan.threatModel`에서 만든 projection이다. 모델이 직접 쓸 수 없고(R-25), 렌더·쓰기가 실패해도 canonical 모델과 draft 게시는 되돌려지지 않는다(R-20, R-24). 전제: R-22의 렌더에 입력이 R-15 검사를 통과한 값이다.
  - draft가 `threatModel`을 생략하면 코드가 이전 모델을 이어붙이므로, 한 번 저장된 모델은 이후 draft에서 삭제되지 않는다(R-17, R-18). 새 모델로 교체하려면 새 모델을 보내야 하고, 최종 draft 뒤의 `complete:false` draft로는 교체되지 않는다(R-18).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-03, R-13, R-26 | shared cache 푸터의 `Repository: <stable target identity from scan-contract.md>`에 정확히 무엇을 쓰는가. `scan-contract.md` 71행은 `targetId`를 "stable repository or workspace" 식별자로 정의하지만, 푸터의 값이 `targetId`인지 `displayName`인지는 문서가 적지 않았다 | cache hit 판정의 비교 대상. 구현자는 푸터 규칙을 하나 정해야 한다 | `scan-contract.md` 전문과 `threat-model` skill을 standalone으로 실행해 만든 푸터 예를 보거나, 푸터가 든 예시 문서를 찾는다(이 레포 예시 디렉터리에서는 찾지 못했다) |

- 확인 한계:
  - LLM의 지침 준수와 지침으로 만든 모델의 품질은 실행하지 않아 확인하지 못했다(R-32).
  - TS 렌더러와 Python 렌더러가 같은 출력을 내는지는 코드 대조만 했고 같은 입력으로 돌려 비교하지 않았다(R-24). 렌더 동등성을 검사하는 테스트 파일(`plugins/codex-security/tests/test_threat_model_projection.py`, `plugins/codex-security/mcp-app/tests/test_threat_model_render.ts`)은 파일 이름만 확인하고 열지 않았다.
  - `write_scan_local_bytes`·`_read_scan_local_json`(scan 디렉터리 안의 안전한 읽기·쓰기), TS의 `artifactDestination`·`replaceArtifactText`·`readArtifactJsonObject`의 본문은 열지 않았다. "경로가 안전하지 않으면 실패한다"는 동작은 `saved_outputs.py`의 주석과 호출 형태에서 읽었다.
  - parent draft의 `requireFiniteNumbers`가 `threatModel` 안의 값에 어디까지 적용되는지는 본문을 열지 않았다. worker draft는 `validateWorkerReport`로 확인했다(R-24).

### 1.5 필수 코드 참조 [필수]

원본은 Apache-2.0이고 인용을 허용한다(overview 1절). 모델이 따를 지침 문서는 길이가 문서보다 짧지 않아도 모델에게 주어지는 입력 자체이므로 C-ID로 둔다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `plugins/codex-security/skills/threat-model/SKILL.md:1-27`, `plugins/codex-security/references/threat-model.md:1-59` | 모델에게 주는 지침 원문 전체. skill의 사용 조건·`Select the Model`·`Retain the Result`, reference의 아키텍처·경계, 독립 검토, 시나리오, `Scan Result Contract`(필드 매핑 표 포함), `Standalone Model` | R-01~R-14 |
| C-02 | `plugins/codex-security/mcp-app/src/threat-model-schema.ts:3-41` `threatModelSchemas`, `plugins/codex-security/mcp-app/src/artifact-contracts.ts:24-29` `nonEmptyText`, `plugins/codex-security/mcp-app/src/artifact-contracts.ts:298` `draft_threatModel`, `plugins/codex-security/mcp-app/src/artifact-contracts.ts:373-386` `draft_scanDraftInput`, `plugins/codex-security/mcp-app/src/finding-detail-schemas.ts:9` `textList` | `threatModel` union 검사식, 공백 판정 정규식(`nonEmptyText`), draft 입력의 필드와 선택성. `textList` = `nonEmptyText`의 배열 | R-15, R-16 |
| C-03 | `plugins/codex-security/scripts/threat_model_projection.py:17-136` `_is_structured_model`·`threat_model_body`·`_scope_lines`·`render_threat_model`, `plugins/codex-security/scripts/report_projection.py:17-24` `THREAT_MODEL_SECTIONS`, `plugins/codex-security/scripts/report_projection.py:41-46` `markdown_threat_model_content` | 렌더 알고리즘: 본문 선택, 섹션 제목 표, 푸터 줄 순서와 조건, 범위 줄, 오류 메시지 | R-22, R-23 |
| C-04 | `plugins/codex-security/scripts/report_projection.py:32-34` 정규식 상수, `plugins/codex-security/scripts/report_projection.py:49-69` `_escape_markdown`, `plugins/codex-security/scripts/report_projection.py:72-77` `_text`, `plugins/codex-security/scripts/report_projection.py:91-105` `_path_label`·`_path_text`, `plugins/codex-security/scripts/report_projection.py:428-430` `_code_fence` | 푸터의 provenance 값과 범위 경로에 쓰는 이스케이프·정규화. URL 안의 `&`을 보존하고 코드 span을 건드리지 않으며, 경로는 쉼표·공백·제어 문자가 있으면 JSON으로 인용해 백틱으로 감싼다 | R-22 |
| C-05 | `plugins/codex-security/scripts/finalize_scan_contract.py:162-194` `threat_model_provenance`·`_render_threat_model` | provenance 구성(`source:"scan"`, `scanId`, `target` = `displayName`, `revision`(없으면 `headRevision`), `snapshotDigest`, `scanScope` = `scan.scope`, `status`, `provisional`)과 렌더 오류를 `ContractError`로 바꾸는 규칙 | R-21, R-22, R-23 |
| C-06 | `plugins/codex-security/scripts/finalize_scan_contract.py:307-358` `write_threat_model_projection_if_possible`, `plugins/codex-security/scripts/finalize_scan_contract.py:197-290` `_read_saved_threat_model` | `threatmodel.md`를 쓸지 정하는 분기(봉인 artifact 기록 여부, 모델이 객체인지), 쓰기 실패의 경고 처리, 저장된 모델을 읽는 우선순위와 legacy 경로 | R-20, R-21, R-31 |
| C-07 | `plugins/codex-security/scripts/workbench_saved_results.py:1007-1209` `write_scan_draft` | draft 게시 순서(검증된 draft와 checkpoint 쓰기, `findings.json`·`scan-manifest.json` 쓰기, projection 호출, 경고 전달)와 Standard phase 갱신 규칙(1177-1204) | R-19, R-20 |
| C-08 | `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:963-979` `preserveScanDraft`의 모델 이어붙이기, `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:2233-2260` `preserveDeepThreatModel` | 이전 저장본에서 모델을 이어받는 규칙과 최종 저장본 우선 규칙 | R-17, R-18 |
| C-09 | `plugins/codex-security/mcp-app/src/threat-model-document.ts:10-75` `saveThreatModelDocument`, `plugins/codex-security/mcp-app/src/threat-model-render.ts:6-168` `renderThreatModel`, `plugins/codex-security/mcp-app/src/threat-model-format.ts:1-85` | worker 출력의 `threatmodel.md` 쓰기와 같은 렌더를 하는 TS 구현 | R-24 |
| C-10 | `plugins/codex-security/mcp-app/src/artifact-storage.ts:43-84` `standaloneArtifactContext`, `plugins/codex-security/mcp-app/src/artifact-storage.ts:148-173` `supplementalPath`, `plugins/codex-security/scripts/workbench_saved_results.py:972-1005` `save_scan_artifact` | standalone 저장소 위치 계산과 `threatmodel.md` 쓰기·읽기 허용 규칙, scan 안의 쓰기 거부 | R-25, R-26 |
| C-11 | `plugins/codex-security/scripts/workbench/retained_records.py:253-267` | 복구 draft의 모델 검증과 `origin:"recovered"` 부여 | R-29 |
| C-12 | `plugins/codex-security/mcp-app/src/deep-scan/artifact-validation.ts:246-262` `addScanCoverage` | Deep aggregate의 모델 선택 | R-30 |
| C-13 | `sdk/typescript/src/api.ts:6456-6466` `scanPrompt`의 knowledge base 문단, `sdk/typescript/src/api.ts:6492` | SDK prompt가 knowledge base가 있을 때 넣는 문장과 첫 모델에서 checkpoint하라는 문장(후자는 caller-modes C-02에도 있다) | R-10, R-12 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(코드를 읽어 기대값을 계산했고 실행하지 않았다. 원본 테스트는 열지 않았다).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-15, R-20, R-22 | running Standard scan(`phase: threat_model`). `record_codex_security_scan_draft({ scanId, complete:false, threatModel:{ summary:"S", assets:["a"] }, findings:[], reviewState:<빈 검토 상태> })` | 결과 `status:"draft_written"`. `scan-manifest.json`의 `scan.threatModel`이 입력과 같고 `scan.complete`가 `false`다. `threatmodel.md`는 `# Threat Model`, 빈 줄, `S`, `## Assets`, 빈 줄, `- a`, 빈 줄, `---`, 빈 줄, `## Saved Model Context`로 이어지고 `Source: scan`, `Scan: <scanId>`, `Target: <표시 이름>`, `Model origin: not recorded`, `Model scope: not recorded`, `Scan scope: <요청 경로>`가 있으며 `Result status: draft`와 provisional 문장으로 끝난다(마지막 두 항목은 추론, R-22) |
| T-02 | R-19 | T-01 직후의 같은 scan | `scans.phase`가 `threat_model`로 남는다(모델만 담은 checkpoint). 다음에 후보나 surface를 담은 `complete:false` draft가 게시되면 `discovery`로 오르고 `scan_progress`의 phase 항목 수가 0이 된다. 같은 입력을 diff scan에 하면 phase는 바뀌지 않는다 |
| T-03 | R-15 | `threatModel:{ format:"markdown", content:"   " }` | 입력 검사에서 거부되고(구조화 분기는 `summary`가 없고 Markdown 분기는 `content`가 공백뿐) `scan-manifest.json`·`threatmodel.md`가 바뀌지 않는다 |
| T-04 | R-15, R-22 | `threatModel:{ format:"markdown", content:"# M\n\nbody\n", origin:"generated", scope:{ includePaths:["src"] } }` | 통과한다. `threatmodel.md`는 `# M\n\nbody\n` 다음에 빈 줄 하나(본문이 줄바꿈으로 끝나므로 `\n` 하나만 더한다)를 두고 `---`로 이어진다. 푸터에 `Model origin: generated`, `Model scope: src`가 있다 |
| T-05 | R-17 | checkpoint 1이 모델 M을 담음. checkpoint 2는 `complete:false`이고 `findings`·`reviewState`만 있고 `threatModel`이 없음(그 사이 최종 draft 없음) | 게시된 `scan.threatModel`이 M이다. checkpoint 2가 M2를 담았다면 M2가 통째로 M을 대체한다 |
| T-06 | R-18 | 최종(`complete:true`) draft가 모델 M을 담아 게시됨. 이후 `complete:false` draft가 새 모델 M2를 담아 옴 | 결과의 기반이 최종 저장본이라 `scan.threatModel`은 M으로 남는다(M2는 반영되지 않는다) |
| T-07 | R-20 | `threatmodel.md` 쓰기를 막는 상태(예: 그 경로가 안전하지 않은 파일로 이미 있음) | 응답이 `status:"draft_written"`이고 `warnings`에 `Automatic threat model save failed: …`가 들어 있다. `scan-manifest.json`과 checkpoint는 이미 게시돼 있다. `threatmodel.md`는 새로 만들어지지 않는다 |
| T-08 | R-21 | manifest `scan.artifacts`에 `threatmodel.md` 경로가 기록돼 있고(봉인된 scan) finalize가 다시 불림 | projection을 쓰지 않는다(`None`). 기록돼 있지 않으면 쓴다 |
| T-09 | R-25 | running scan에 `save_codex_security_artifact({ scanId, storage:"persistent", path:"threatmodel.md", content:"x" })` | "Use the existing scan tools for canonical artifacts, ledgers and checkpoints." 오류. 같은 `path`를 `scanId` 대신 `targetPath:<저장소>`로 보내면 shared cache 위치(R-26)에 쓰인다. `read_codex_security_artifact({ scanId, storage:"persistent", path:"threatmodel.md" })`는 scan의 `threatmodel.md`를 읽는다 |
| T-10 | R-26 | 같은 저장소를 두 경로(심볼릭 링크 경로와 실경로)로 `targetPath`에 줌 | 둘 다 `fs.realpath` 후의 같은 문자열로 `sha256`을 만들어 같은 `artifacts-<sha256>` 디렉터리를 쓴다. 저장소의 하위 디렉터리를 `targetPath`로 주면 다른 디렉터리다. `targetPath`나 `scanRoot`가 저장소 안이면 저장 시 오류다 |
| T-11 | R-24 | Standard worker가 모델을 담은 draft를 worker 출력에 게시하고 `pluginRoot`가 있음 | worker `result.json`이 교체되고, 그 뒤 worker 출력에 `threatmodel.md`가 생긴다. 푸터의 `Source`는 `worker`, `Target`은 저장소 루트의 전체 경로다. `pluginRoot`가 없으면 파일이 생기지 않고 오류도 없다 |
| T-12 | R-30 | Deep 부모가 worker A, B의 결과를 순서대로 합침. A의 모델 MA, B의 모델 MB(MA와 다름) | aggregate `threatModel`은 MA이고, B 항목의 `reviewState.reviews[]`에 `threatModel: MB`가 있다. B의 모델이 MA와 같으면 `reviews[]`에 모델을 따로 남기지 않는다 |
| T-13 | R-12 | SDK scan에 knowledge base가 준비됨 | prompt가 knowledge base 문단 중 "Regenerate the threat model for this scan without reading or replacing the shared cache."를 포함한다. 없으면 이 문단이 없다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

기준은 모두 `codex-security@173483d7c658be7a512c93d9559bf01a05d5b196`이다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 또는 C-ID) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `plugins/codex-security/skills/threat-model/SKILL.md:14` | 지침 문장을 읽었다 |
| R-02 | C-01 `plugins/codex-security/skills/threat-model/SKILL.md:15` | 같음 |
| R-03 | C-01 `plugins/codex-security/skills/threat-model/SKILL.md:16`, `plugins/codex-security/references/artifact-storage.md:49-54` | 같음. 푸터 두 줄 형식은 artifact-storage.md 51-54행 |
| R-04 | C-01 `plugins/codex-security/skills/threat-model/SKILL.md:17` | 같음 |
| R-05 | C-01 `plugins/codex-security/skills/threat-model/SKILL.md:3`·`8`, `plugins/codex-security/references/core-scan.md:11`, `plugins/codex-security/skills/security-diff-scan/SKILL.md:28`, `plugins/codex-security/skills/security-scan/SKILL.md:21` | 부재 주장: "Standard·Deep scan 경로의 지침에 shared cache 규칙이 없다". 명령 `git grep -n -i "cache" -- plugins/codex-security/skills plugins/codex-security/references`(threat-model-visualize 제외)로 찾은 `cache` 언급은 모델 cache 규칙을 다루는 `artifact-storage.md`·`scan-artifacts.md`·`threat-model.md`·`threat-model/SKILL.md`와, 모델 cache와 무관한 `final-report.md:77`(token usage), `assess-patch-risk/references/risk-rubric.md`, `fix-finding/SKILL.md`, `publish-findings/scripts/collect_checkmarx.py`뿐이다. `core-scan.md`·`baseline-auditor.md`·`focused-investigator.md`·`security-scan/**`·`deep-security-scan/SKILL.md`에는 없었다. 놓칠 수 있는 것은 이 파일들이 링크하는 다른 reference나 SDK 외 prompt다 |
| R-06 | C-01 `plugins/codex-security/references/threat-model.md:3-14` | 지침 문장을 읽었다 |
| R-07 | C-01 `plugins/codex-security/references/threat-model.md:30-36` | 같음 |
| R-08 | C-01 `plugins/codex-security/references/threat-model.md:16-28` | 같음 |
| R-09 | C-01 `plugins/codex-security/references/threat-model.md:38-55`, `plugins/codex-security/skills/security-diff-scan/SKILL.md:28`, `plugins/codex-security/references/final-report.md:28`, `plugins/codex-security/references/scan-contract.md:173` | 지침 문장을 읽었다. "supplied가 아닌 경우 `origin:"generated"`"는 diff skill이 쓰고 reference는 "may include"라고 적어 약간 다르다 |
| R-10 | `plugins/codex-security/references/core-scan.md:11`, `plugins/codex-security/skills/security-scan/references/scan-results.md:7`·`11`, `plugins/codex-security/skills/security-scan/references/sdk-files.md:3`·`24`, `plugins/codex-security/references/threat-model.md:42`, `plugins/codex-security/references/scan-runtime.md:7`, `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:172` | 지침 문장을 읽었다. 도구 설명(172행)이 "Use complete:false as soon as a model is available, even with empty findings"라고 적는 것은 같은 지침의 코드 쪽 표지다 |
| R-11 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:28` | 지침 문장을 읽었다 |
| R-12 | C-13 `sdk/typescript/src/api.ts:6456-6466`, `plugins/codex-security/references/threat-model.md:3` | prompt 문단은 소스에서 읽은 문장. `security-policy.ts:943`에도 같은 취지의 문장이 있으나(`cs policy` 전용) 이 스펙 범위 밖이라 열지 않았다 |
| R-13 | C-01 `plugins/codex-security/skills/threat-model/SKILL.md:27`, `plugins/codex-security/references/threat-model.md:57-59`, `plugins/codex-security/references/artifact-storage.md:49-54` | 지침 문장을 읽었다 |
| R-14 | C-01 `plugins/codex-security/skills/threat-model/SKILL.md:25`, `plugins/codex-security/references/scan-artifacts.md:27-29`, `plugins/codex-security/references/artifact-storage.md:13`·`32` | 부재 주장: "후속 phase 도구가 모델을 돌려주는 코드가 없다". 명령 `git grep -n -i "threatModel" -- plugins/codex-security/mcp-app`(tests 제외)로 후보·검증·공격 경로 도구 파일(`artifact-candidate-ledger.ts`, `artifact-discovery.ts`)에는 `threatModel`이 없었고, `compact-artifact-tools.ts`에는 draft 도구 설명(172행)뿐이다. 모델이 후속 phase에서 `read_codex_security_artifact`로 읽는지는 artifact-storage.md 예시(32행)에서 읽은 지침이다 |
| R-15 | C-02, `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:2935-2982` `parseScanDraft`·`parsePersistedScanDraft`, `plugins/codex-security/schemas/scan-manifest.schema.json:85` | 스키마 코드를 읽었다. 부재 주장: "Python `write-scan-draft`가 `scan.threatModel`을 스키마로 다시 검사하지 않는다". 읽은 범위는 `plugins/codex-security/scripts/workbench_saved_results.py:1007-1209`(검증 호출은 `_validate_completion_binding`이고, 이 함수는 `finalize_scan_contract.py:1717-1759`에서 scan id·status·target·scope·coverage 결속만 본다). 명령 `grep -n "validate_against_schema(" plugins/codex-security/scripts/*.py plugins/codex-security/scripts/workbench/*.py`가 준 호출 줄은 `finalize_scan_contract.py`의 226·2771-2773·3196-3199·3239·3263뿐이고 `workbench_saved_results.py`에는 없었다. finalize 쪽 호출이 `threatModel`을 검사하는 것은 스키마가 이 속성을 포함하기 때문에 추론이다 |
| R-16 | `plugins/codex-security/mcp-app/src/artifact-contracts.ts:287-296` `draft_scope`, `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:262-267`, `3148-3175` `buildScope` | 코드를 읽었다. 둘을 비교하는 코드가 없다는 것은 `buildScope`와 `threatModel` 처리 구간에서 `threatModel.scope`를 읽는 곳이 없음에서 온 판단이다(`git grep -n "threatModel" plugins/codex-security/mcp-app/src/artifact-scan-draft.ts` 결과 33-80행·251·292-294·472-474·974-979·2233-2260·2908-2910만 있다) |
| R-17 | C-08 `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:802-810`·`974-979`·`2233-2260`, `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:250-252` | 코드를 읽었다. 저장본 정렬(`modifiedMs` 내림차순, 같으면 head 먼저)과 `sources.find`로 첫 모델을 고른다. 부모 호출은 `preserveScanDraft(context, parsed, false)`로 이번 입력을 checkpoint로 미리 저장하지 않는다 |
| R-18 | C-08 `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:963-979` | 코드를 읽었다. `retainedFinal`이 있으면 `result = structuredClone(retainedFinal.input)`로 기반이 바뀌고 이후 모델 처리는 `result.threatModel === undefined`일 때만 이어받는다. 이번 draft의 모델이 `result`에 복사되는 줄을 찾지 못했다(`threatModel` 검색 위 R-16 목록). 984-1100행의 `reviewState` 병합은 모델을 건드리지 않는다고 읽었다. 이 R-ID는 의도가 아닌 코드 읽기에서 온 것이라 메인 점검 표본으로 권한다 |
| R-19 | C-07 `plugins/codex-security/scripts/workbench_saved_results.py:1177-1204`, `plugins/codex-security/scripts/workbench_constants.py:7` | 코드를 읽었다. `scan["mode"] == "standard"`가 아니면 갱신하지 않는다. 한 draft가 `findings`·`surfaces`·`deferred` 중 하나만 있어도 model-only가 아니다 |
| R-20 | C-07 `plugins/codex-security/scripts/workbench_saved_results.py:1121-1209`, C-06 `plugins/codex-security/scripts/finalize_scan_contract.py:351-358`, `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:394-406` | 코드를 읽었다. `write_scan_local_bytes(..., owner_read_write=True)`의 본문과 "unsafe path가 실패한다"는 열지 않았다(T-07의 "안전하지 않은 파일" 예는 `saved_outputs.py:29-33`의 주석에서 읽은 것이다) |
| R-21 | C-06 `plugins/codex-security/scripts/finalize_scan_contract.py:307-349`, `plugins/codex-security/scripts/finalize_scan_contract.py:3322-3344`, `3404-3406` | 코드를 읽었다. 부재 주장: "이미 있는 `threatmodel.md`를 지우는 호출이 없다". 읽은 범위는 `write_threat_model_projection_if_possible` 본문(307-358행)이다. `_remove_scan_local_file_if_exists`가 이 함수 안에 없다는 것까지만 확인했다. 다른 함수가 지울 가능성은 확인하지 않았다 |
| R-22 | C-03, C-04, C-05 | 코드를 읽었다. "Result status: draft"는 `finalize_scan_contract.py:176-177`의 변환과 `workbench_db.py:396-433`의 binding에 `status` 키가 없다는 것(그래서 `_populate_unsealed_manifest_envelope`이 `completed`를 채움, `finalize_scan_contract.py:1576-1578`)을 합친 추론이다 |
| R-23 | C-03 `plugins/codex-security/scripts/threat_model_projection.py:30-84`, C-05 `plugins/codex-security/scripts/finalize_scan_contract.py:190-194` | 코드를 읽었다. 구조화 판정(`_is_structured_model`)이 참이면 메타데이터 검사를 건너뛰는 분기는 39-40행 |
| R-24 | C-09, `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:411-490`, `plugins/codex-security/mcp-app/src/coverage-publication.ts:8-29`·`65-68` | 코드를 읽었다. 두 렌더러가 같은 출력을 낸다는 판단은 TS 파일 주석("Match report_projection._escape_markdown", "Match the retained artifact projection's Python whitespace semantics")과 함수 구조 대조에서 온 추론이다. 부모 provenance의 `Target`이 `displayName`인 것은 `finalize_scan_contract.py:181`이다. 이 함수의 호출처 검색: `git grep -n "saveThreatModelDocument"` 결과가 `artifact-scan-draft.ts`의 import와 472행뿐이라 부모 scan 경로(`layout:"scan"`)가 호출하는 곳은 찾지 못했다(함수 자체는 `layout:"scan"`도 처리한다) |
| R-25 | C-10 `plugins/codex-security/mcp-app/src/artifact-storage.ts:148-173`, `plugins/codex-security/scripts/workbench_saved_results.py:972-1005`, `plugins/codex-security/scripts/reserved_artifact_paths.json` | 코드를 읽었다. `storage:"temporary"`는 경로 허용 검사를 받지 않는다(`supplementalPath` 154행) |
| R-26 | C-10 `plugins/codex-security/mcp-app/src/artifact-storage.ts:43-84`, `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:234-258`, `plugins/codex-security/mcp-app/src/workbench-client.ts:13-30`, `plugins/codex-security/scripts/workbench_setup.py:24-45` | 위치 계산은 코드를 읽었다. 부재 주장: "푸터를 읽거나 비교하는 코드가 없다". 명령 `git grep -n -E "Version:|\"Repository|'Repository" -- plugins/codex-security/mcp-app/src plugins/codex-security/scripts plugins/codex-security/mcp-app/server.ts sdk/typescript/src`와, 레포 전체에 대한 `git grep -n -i -E "shared (threat|cache|model)|threat.model cache|Version: <|Repository:"`(tests, evals, CHANGELOG, lock 파일 제외)의 결과에 이를 읽는 코드가 없었고, `shared cache` 문구는 `sdk/typescript/src/api.ts:6459`와 `security-policy.ts:943`의 prompt 문장에서만 나왔다. 놓칠 수 있는 것은 문자열을 조각내 조립하는 코드다. `plugins/codex-security/native/`(Rust)는 `git grep -n -i threat -- plugins/codex-security/native`에서 결과가 없었고, 빌드 산출물 번들은 `plugins/codex-security/`에 추적되지 않아 검색 대상이 아니었다 |
| R-27 | `plugins/codex-security/schemas/scan-manifest.schema.json`(`scan.required`: `id, producer, status, startedAt, completedAt, sealedAt, target, scope, findingsRef, artifacts`), `plugins/codex-security/mcp-app/src/artifact-contracts.ts:383`, `plugins/codex-security/scripts/finalize_scan_contract.py:219-231` | 부재 주장: "모델이 없다고 실패하는 코드가 없다". `grep -n -i "threatModel\|threat_model" plugins/codex-security/scripts/finalize_scan_contract.py`로 본 38건 중 `"threatModel" not in scan`은 219행(내보내기 분기) 하나뿐이고 어디에도 모델 필수 검사가 없었다. 다른 스크립트(`validate_scan_contract.py` 등)는 열지 않았다 |
| R-28 | `plugins/codex-security/mcp-app/src/threat-model-schema.ts:21-23`, `plugins/codex-security/scripts/workbench/retained_records.py:255-258` | 부재 주장: "supplied/생성을 구분하는 코드가 없고 `reconciled`를 정하는 코드가 없다". 명령 `git grep -n -E "\"reconciled\"\|'reconciled'\|origin: \"" -- plugins/codex-security/mcp-app/src plugins/codex-security/scripts sdk/typescript/src`에서 `reconciled`는 `threat-model-schema.ts`·`models.ts`(sdk·mcp 각 한 곳)의 타입·enum과 `threat_model_projection.py:44`의 검사에만 있었다. `origin: "generated"`를 쓰는 코드는 `sdk/typescript/src/security-policy.ts:882` 한 곳이다(앞뒤 문맥은 열지 않았다). 놓칠 수 있는 것은 동적으로 값을 만드는 코드다 |
| R-29 | C-11 | 코드를 읽었다. 이 함수의 호출 경로(`recover_scan_results` 등)는 행 9·7 범위라 열지 않았다 |
| R-30 | C-12 | 코드를 읽었다. 호출 순서(worker 합류 순서)는 행 7 |
| R-31 | C-06 `plugins/codex-security/scripts/finalize_scan_contract.py:197-290`, `sdk/typescript/src/artifact-export.ts:212-224`, `plugins/codex-security/mcp-app/server.ts:1803-1815` | `_read_saved_threat_model`을 읽었다. 부재 주장: "SDK에서 `writeThreatModel`의 호출처는 `security-policy.ts` 하나"(`git grep -n "writeThreatModel\|write-threat-model" -- sdk/typescript/src` 결과: 정의 `artifact-export.ts:212`, 호출 `security-policy.ts:918`). 내보내기 CLI·앱 도구 본문은 열지 않았다 |
| R-32 | 실행하지 않음 | `cs`·SDK·MCP 서버를 실행하지 않았다 |
| T-01~T-13 | 각 사례의 R-ID 행 | 코드에서 도출했고 실행하지 않았다. T-01의 푸터 줄 순서는 C-03(`render_threat_model` 117-134행), T-04의 줄바꿈은 같은 함수 134행의 분기(`body.endswith("\n")`)다 |

### 2.2 코드 읽는 순서 [선택]

1. 모델이 읽는 쪽: `skills/threat-model/SKILL.md`(27줄), `references/threat-model.md`(59줄), `references/core-scan.md` 3번. 이 셋이 Standard·diff·standalone의 지침 전부다.
2. 입력 형식: `mcp-app/src/threat-model-schema.ts`(C-02)에서 시작해 `artifact-contracts.ts`의 `draft_scanDraftInput`.
3. 저장: `mcp-app/src/server/compact-artifact-tools.ts` 168-186행(도구 등록) → `artifact-scan-draft.ts`의 `recordCodexSecurityScanDraftViaWorkbench`(226-408행) → `scripts/workbench_saved_results.py`의 `write_scan_draft`(1007-1209행).
4. projection: `scripts/finalize_scan_contract.py`의 `write_threat_model_projection_if_possible` → `scripts/threat_model_projection.py` → `scripts/report_projection.py`의 이스케이프 helper.

원본의 구현 전략은 하나다. 같은 렌더 규칙이 Python(부모 scan 게시·finalize·내보내기)과 TypeScript(worker 출력)에 두 번 구현돼 있고, TS 쪽 주석이 Python 동작과 맞추라고 적는다. 재구현할 때는 한 구현으로 합쳐도 provenance 입력(R-24의 차이)을 호출자가 정하게 하면 같은 효과를 낼 수 있다(이 문장은 설계 의견이라 적용 메모로 옮기지 않고 추론으로 둔다).

### 2.3 비교·재사용 출처 [선택]

해당 없음(이 주제 폴더에 같은 기능의 다른 레포 스펙이 없다).

### 2.4 검토 기록 [필수, ready 스펙]

- 방식: 메인 세션 기본 점검(2026-11-16). `python scripts/check.py codex-security`로 인용 줄의 존재를 확인하고(형식·위치 확인일 뿐), 작성자가 고위험으로 권한 R-ID 2개를 인용 줄과 검색으로 대조했다. 다른 스펙이 `depends`로 의존하지 않아 독립 검토 조건에는 해당하지 않는다. 아직 `draft`인 이유는 미결정 U-01이 남아 있어서다.
- 대조한 R-ID: R-18(`artifact-scan-draft.ts:963-979`. `retainedFinal`이 있으면 `result`가 저장본으로 바뀌고 `retainedThreatModel`은 `sources`에서만 찾는다. `sources`는 `savedSources.map`이라 이번 입력을 포함하지 않으므로 "이번 draft의 모델은 반영되지 않는다"가 맞다), R-26(스펙 2.1의 `git grep` 명령을 다시 실행해 `Version:`/`Repository:` 푸터를 읽거나 비교하는 코드가 없음을 확인. 위치 계산식 자체는 열지 않았다).
- 대조하지 않은 R-ID: 위 2개를 제외한 전부. 특히 R-15·R-17·R-19·R-20·R-21(상태 변경·실패 처리), R-22(`추론`), R-24(렌더러 동일성 `추론`), R-27·R-28(부재 주장)은 필요하면 독립 검토 대상이다.
- 재구현: 미수행
