---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
---

# Next Session Plan: codex-security

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] `security/` 주제 폴더 생성: `GUIDE.md`, `repos.lock.tsv`, `.gitignore`의 `/security/repos/`
- [x] 전체 이력 clone, 기준 SHA `173483d`, 작업트리 clean (`artifacts/codex-security/repo-metadata.txt`)
- [x] 라이선스: 루트와 `sdk/typescript/` 두 `LICENSE`의 첫머리 확인(Apache-2.0)
- [x] `git ls-files` 상위 경로 집계, README 전문, 두 `package.json`·`plugin.json` 읽기
- [x] feature map 17행(핵심 14 / 부속 3)과 공유 계약 4개를 [overview 2절](./overview.md)에 작성했다. 처음에는 SDK 기능 기준 21행이었으나 사용자가 "skill과 skill이 호출하는 코드"로 목적을 정정해 skill → 호출 코드 기준으로 다시 나눴다. 읽은 것: CLI 명령 등록부, `scanPrompt`·`skillNameFor`, `runDeepScan`, skill `security-scan`·`finding-discovery`·`validation`·`attack-path-analysis` 전문, `core-scan.md`, `final-report.md` 표, `compact-artifact-tools.ts` 110~215행, `artifact-candidate-ledger.ts` 앞부분, MCP 도구 이름, helper 목록. 대부분 행은 진입점 수준이다.
- [ ] 구조도(2장 5번), 질문, 기능 스펙은 시작하지 않았다.

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] **스펙 범위 승인**(사용자 결정). overview 1절에 `승인 전`으로 권장안(행 1~10, S1~S3)을 적었다. 권장대로 / 행 추가·제외, 선택 행(11·12·14), 구조도를 지금 그릴지를 정한다.
- [ ] 스펙을 어디에 쓸지(재구현, 설계 참고, 다른 에이전트의 skill 재료 등)는 아직 없다. 분석 목적은 "보안 검증 skill과 그 skill이 호출하는 코드의 소스 이해"로 정해졌다.
- [ ] 실행 허용 여부. `cs login`·`cs scan`·SDK·Docker는 모델 API 키와 대상 저장소가 필요해서 실행하지 않았다. 코드 읽기만으로 진행해도 되는지.
- [ ] `ai-pentest/` 레포와 같은 비교 축(에이전트 구조, 증명 절차, 모델·데이터, 상태와 보고)으로 볼지, 이 폴더만의 축을 둘지.

---

## 3. 기능 스펙 후보

없음.

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

범위가 승인되면 기능 스펙(워크플로 4장)을 선행이 없는 행 1부터 쓴다. 처음 읽을 후보는 아래이고, 아래 역할은 파일 이름 기준 추론이다.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts` | `registerCompactTool` 목록 | 행 4~6. skill이 부르는 후보 기록·검증 기록·공격 경로 도구와 입력 스키마 |
| `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts` | `recordCodexSecurityCandidateValidations`, `recordCodexSecurityCandidateAttackPaths` | S1. 후보 ledger 교체 규칙과 거절 조건 |
| `plugins/codex-security/references/core-scan.md`, `skills/security-scan/` | — | 행 2. Standard 감사 지침(이미 전문 읽음)과 `references/` 나머지 |
| `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts`, `scripts/finalize_scan_contract.py` | — | 행 9. 모델 출력을 코드가 어디서 걸러내는지 (3,500줄대라 `findings` 검사부터) |
| `plugins/codex-security/mcp-app/src/helpers/` | `normalize-candidates.ts`, `resolve-security-md.ts` | 행 4·10. skill이 부르는 helper 본문 |
| `plugins/codex-security/mcp-app/src/deep-scan/coordinator.ts`, `iteration.ts` | — | 행 7. 반복·종료 조건을 코드가 소유하는지 |
| `sdk/typescript/src/api.ts` | `scanPrompt` | 행 15. 모델에게 skill을 어떻게 따르게 하는지(필요할 때만) |


### 막힌 경로

| 시도 | 결과 | 재개 조건 |
|---|---|---|
| `cs scan`·`cs --help`·SDK `run`·MCP 서버 실행으로 동작 확인 | 실행하지 않음(모델 API 키와 대상 저장소 필요, 승인 없이 실행 금지) | 사용자가 실행을 허용하면 `--mock`·`--dry-run`(모델 호출 없음)부터 |

---

## 5. 참고 사항 및 후속 제안

- feature map 작성 중 확인한 열린 의문: workbench·중복 판별이 Python(`plugins/codex-security/scripts/workbench_*.py`)과 TypeScript(`mcp-app/src/workbench/`, `sdk/typescript/src/deduplication/`) 양쪽에 있는 이유, README가 제거했다는 `serve`와 `sdk/typescript/src/server/`의 관계.
- 한 레포 안에 배포 단위가 4개(`sdk/typescript`, `plugins/codex-security`, `github-action`, `docker`)다. 이번 목적에서는 `plugins/codex-security`가 중심이고 나머지는 부속이다.
- Standard·Deep worker는 phase skill(`finding-discovery`·`validation`·`attack-path-analysis`)을 호출하지 않고 `core-scan.md` 하나로 처리한다. phase skill은 diff 스캔·구형 phase 스캔·단독 요청에서 쓴다(세 SKILL.md의 "Scan integration").
- 레포 루트 `AGENTS.md`는 그 레포 개발자용 지침이다. 따르지 않는다.
- clone은 `.gitignore` 대상이다. 다른 PC에서는 `repos.lock.tsv`의 URL·SHA로 다시 clone한다.
