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
- [ ] 코드 본문은 열지 않았다. feature map, 구조도, 질문, 기능 스펙은 시작하지 않았다.

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] **분석 목적**(사용자 결정). 예: "취약점 발견·검증 skill 설계 참고", "재구현", "스캔 결과 연동(import·export·게시) 파악". feature map 세밀도와 권장 범위가 이것으로 정해진다.
- [ ] 실행 허용 여부. `cs login`·`cs scan`·SDK·Docker는 모델 API 키와 대상 저장소가 필요해서 실행하지 않았다. 코드 읽기만으로 진행해도 되는지.
- [ ] `ai-pentest/` 레포와 같은 비교 축(에이전트 구조, 증명 절차, 모델·데이터, 상태와 보고)으로 볼지, 이 폴더만의 축을 둘지.

---

## 3. 기능 스펙 후보

없음.

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

목적이 정해지면 feature map(워크플로 2장 3~4번)부터 쓴다. 처음 읽을 후보는 아래이고, 역할은 모두 파일 이름 기준 추론이다.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `sdk/typescript/src/cli.ts`, `sdk/typescript/bin/codex-security.mjs` | CLI 명령 등록부 | 공개 명령 목록. feature map의 "공개 명령과 대조" 기준 |
| `sdk/typescript/src/scan-executor.ts`, `scan-modes.ts`, `deep-scan.ts` | — | Standard/Deep 스캔이 plugin skill을 어떻게 호출하는지 |
| `plugins/codex-security/skills/security-scan/`, `finding-discovery/`, `validation/` | skill 본문 | 후보 탐지 → 검증 절차(지침과 코드가 나뉘는 경계) |
| `plugins/codex-security/references/scan-contract.md`, `scripts/validate_scan_contract.py` | — | 스캔 산출물 계약과 강제 지점 |
| `plugins/codex-security/scripts/workbench_*.py` | — | 스캔 이력·finding 저장소와 상태 |
| `sdk/typescript/src/external-findings*.ts`, `*-findings.ts` | — | 외부 스캐너 가져오기 공통 계약과 어댑터 패밀리 |

---

## 5. 참고 사항 및 후속 제안

- 한 레포 안에 배포 단위가 4개(`sdk/typescript`, `plugins/codex-security`, `github-action`, `docker`)라서, feature map에서 단위별 `핵심`/`부속`을 먼저 나누는 편이 좋다.
- 레포 루트 `AGENTS.md`는 그 레포 개발자용 지침이다. 따르지 않는다.
- clone은 `.gitignore` 대상이다. 다른 PC에서는 `repos.lock.tsv`의 URL·SHA로 다시 clone한다.
