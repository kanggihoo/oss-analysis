---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
---

# codex-security Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/openai/codex-security`
- **기준 SHA**: `173483d7c658be7a512c93d9559bf01a05d5b196` (main, 2026-11-13T18:38:24-08:00, "fix(plugin): preserve Windows helper exit codes (#2651)"). 전체 이력 clone이다. 기록은 [repo-metadata.txt](../../artifacts/codex-security/repo-metadata.txt).
- **작업트리 상태**: Clean
- **분석 목적**: **미정**. 사용자가 정하면 여기에 적는다. feature map 세밀도와 권장 범위의 기준이 된다. 주제 폴더 목적은 [GUIDE.md](../../GUIDE.md).
- **라이선스**: Apache-2.0. `LICENSE`(루트)와 `sdk/typescript/LICENSE`를 열어 첫머리가 Apache License Version 2.0임을 확인했다(코드 확인). 추가 LICENSE 파일은 `git ls-files`에서 이 둘뿐이다. `plugins/codex-security/native/licenses/`(파일 1개, 네이티브 모듈 서드파티 고지 후보)는 열지 않았다.
- **분석 대상 제품**: 한 레포 안의 배포 단위 4개(README와 매니페스트 기준, 역할은 feature map 작성 때 코드로 확인한다).
  - `sdk/typescript/`: npm 패키지 `@openai/codex-security` 0.10.0. CLI 바이너리 `cs`·`codex-security`와 TypeScript SDK(`sdk/typescript/package.json`의 `bin`, `exports`)
  - `plugins/codex-security/`: Codex 플러그인 `codex-security` 0.1.95. skill 20개, Python 스크립트, MCP 앱, Rust 네이티브 모듈(`plugins/codex-security/.codex-plugin/plugin.json`)
  - `github-action/`: GitHub Action(`action.yml`, `github-action/README.md`)
  - `docker/`: 컨테이너 이미지와 workflow runner(`Dockerfile`, `compose*.yaml`, `docker/README.md`)
- **스펙 범위**: feature map 작성 전. 목적이 정해지면 권장안을 만들어 승인받는다.

---

## 2. 프로젝트 개요

README는 이 도구를 "코드의 취약점을 찾고, 조사하고, 고치도록 돕는 것"으로 소개한다(미확인: README의 주장). 같은 워크플로를 Codex 안(플러그인 skill), 터미널(`cs` CLI), 자동화(TypeScript SDK·GitHub Action·컨테이너)에서 쓸 수 있다고 한다.

README가 나열한 기능(코드로는 아직 확인하지 않은 후보):

- 저장소·경로·Git 변경분 스캔. Deep 스캔은 Standard 스캔을 반복해 중복을 제거한 결과를 낸다.
- 후보 취약점 검증, 패치 생성, 기존 수정 검증
- `SECURITY.md` 초안 작성, threat model 저장·내보내기
- 저장된 스캔·finding 조회, 중복 판별, 사용자 rubric 기준 severity 평가, 소스·Git 이력 기반 owner 제안
- 외부 스캐너 결과 가져오기(`docs/scanner-imports/`)와 Codex Security Cloud 게시
- Linear·Jira·GitHub 추적, SARIF·JSON·CSV 내보내기, ServiceNow 내보내기
- 여러 저장소·컴포넌트 대상 자동화(CI, 컨테이너 bulk scan)
- 모델 제공자: OpenAI, Amazon Bedrock, OpenRouter, Fireworks AI, Cheaper Inference

### Feature map

**미작성.** 목적이 정해진 뒤 2장 3~4번을 따라 쓴다. 아래 "처음 읽은 범위"는 최상위 구조를 훑은 결과이고 feature map이 아니다.

### 처음 읽은 범위 (2장 3번 초반)

`git ls-files`로 추적 파일 1,607개의 상위 경로를 집계하고, README 전문과 두 `package.json`·`plugin.json`·두 `LICENSE`를 읽었다. 코드 본문은 열지 않았다.

| 위치 | 추적 파일 수 | 읽을 이유 (후보) | 검증 수준 |
|---|---|---|---|
| `sdk/typescript/src/` | 203 | CLI·SDK 본체. 파일 이름에 `scan-*`, `deep-scan`, `component-scan`, `multiscan`, `validation`, `severity`, `dedupe`, `publish*`, `security-policy*`, `suggest-owners`, `hosted-*`가 보인다 | 추론(파일 이름) |
| `sdk/typescript/src/*-findings.ts` | 22 | `snyk`, `semgrep`, `sonar`, `trivy`, `wiz`, `veracode` 등 외부 스캐너 결과 변환기 후보. `external-findings.ts`·`native-json-findings.ts`는 공통 계약 쪽일 수 있어 어댑터인지 미확인. 같은 계약을 구현한 어댑터 패밀리로 묶을 후보 | 추론(파일 이름) |
| `plugins/codex-security/skills/` | 75 | skill 20개: `security-scan`, `security-diff-scan`, `deep-security-scan`, `finding-discovery`, `validation`, `triage-finding`, `fix-finding`, `verify-fix`, `threat-model`, `attack-path-analysis`, `define-security-policy`, `publish-findings`, `track-findings`, `cloud-findings` 등 | 코드 확인(`ls`로 이름만) |
| `plugins/codex-security/references/` | 19 | 스캔 절차 문서 후보: `core-scan.md`, `baseline-auditor.md`, `focused-investigator.md`, `scan-contract.md`, `final-report.md` 등 | 추론(파일 이름) |
| `plugins/codex-security/scripts/` | 56 | `workbench_*.py`(스캔 이력·finding 색인·검증·게시·수정 저장소 후보), `validate_scan_contract.py`, `finalize_scan_contract.py` | 추론(파일 이름) |
| `plugins/codex-security/mcp-app/`, `native/` | 232, 34 | MCP 서버와 Rust 네이티브 모듈(Windows 파일·프로세스 처리 이름이 보인다). 부속 후보 | 추론(파일 이름) |
| `docs/` (`scanner-imports/` 22 포함) | 29 | 사용자·통합 문서. `scanner-imports/`는 스캐너별 가져오기 가이드 후보 | 추론(파일 이름) |
| `evals/`, `sdk/mutation/`, `examples/`, `.github/` | 108, 3, 65, 60 | 평가·mutation·예제·CI. 기본으로 본문을 열지 않는 영역이다(워크플로 2장 3번) | 추론(파일 이름) |

**미탐색 영역**: 코드 본문 전부. 특히 스캔 실행기(`scan-executor.ts`)와 skill 본문, `workbench_*.py`, 모델 제공자 연결, 인증·`login`, 외부 스캐너 변환기, 게시 경로는 역할을 확인하지 않았다. 실행(`cs`, SDK, Docker, MCP)은 하지 않았다.

**읽지 않은 것과 이유**: 레포 루트 `AGENTS.md`·`sdk/typescript/AGENTS.md`는 그 레포 개발자용 지침이라 따르지 않았고 본문도 열지 않았다. `CONTRIBUTING.md`, `RELEASING.md`, `SECURITY.md`, `CHANGELOG.md`는 기본 제외 대상이다.

---

## 3. 핵심 아키텍처 (archify Diagrams)

미작성. feature map 이후 2장 5번으로 그린다.

---

## 4. 질문 (Questions)

아직 없다.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: feature map 작성 후 2절의 "스펙·상태" 칸
