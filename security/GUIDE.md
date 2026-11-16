# 보안 도구 오픈소스 분석 가이드

- 작성일: 2026-11-16
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기, feature map → 범위 승인 → 기능 스펙). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

보안 점검·취약점 관리용 오픈소스를 분석한다. 첫 대상은 **codex-security**(OpenAI)다. 코드의 취약점을 찾고, 검증하고, 패치하고, 결과를 외부 도구로 내보내는 워크플로를 Codex 플러그인(skill), CLI, TypeScript SDK, GitHub Action으로 제공한다(README 기준, 코드 확인 전).

[`ai-pentest/`](../ai-pentest/GUIDE.md)와의 구분: `ai-pentest/`는 **실행 중인 대상**을 공격해 익스플로잇으로 증명하는 에이전트를 비교한다. 이 폴더는 **소스 코드를 읽어** 취약점을 찾고 고치는 쪽, 그리고 스캔 결과를 관리·연동하는 쪽을 다룬다. 두 영역이 겹치는 레포가 생기면 목적이 더 가까운 쪽에 두고, 이 문서에 이유를 적는다.

- 분석 목적: codex-security는 **보안 검증 skill과 그 skill이 호출하는 코드(MCP 도구·helper·Python)의 소스 이해**(2026-11-16 사용자 정정). 스펙을 어디에 쓸지는 미정이며 정해지면 여기와 각 overview 1절에 적는다(예: "취약점 발견·검증 skill 설계 참고", "재구현"). feature map 세밀도와 권장 범위가 이 목적으로 정해진다.
- 현재 단계: codex-security는 2026-11-16에 feature map 17행과 공유 계약 4개까지 썼고 범위 승인을 기다린다. 목적은 "보안 검증 skill과 그 skill이 호출하는 코드의 소스 이해"다.

읽기 전용 소스 분석만 한다. codex-security는 모델 API 키와 사용자 저장소를 받아 스캔을 돌리는 도구라서, 승인 없이 `cs login`·`cs scan`·SDK `run`·Docker 컨테이너를 실행하지 않는다. 실행이 필요하면 `handoff.md`에 허용 요청으로 올린다.

## 디렉터리

```text
security/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt 등 도구 출력
└── reports/<repo>/       # overview.md, next.md, diagrams/, questions/, capabilities/
```

루트 `repos/`·`reports/`와 섞지 않는다. 이 폴더의 레포도 루트 `index.md`에 `<repo> (security/)` 이름으로 행을 둔다.

## 분석 대상

| 이름 | URL | 라이선스 (파일 확인) |
|---|---|---|
| codex-security | https://github.com/openai/codex-security | Apache-2.0 (`repos/codex-security/LICENSE`, `repos/codex-security/sdk/typescript/LICENSE`). 두 파일 모두 첫머리가 Apache License Version 2.0이다 |

기준 SHA는 `repos.lock.tsv`, `artifacts/codex-security/repo-metadata.txt`와 같다(main, 2026-11-13).

## 차이점

- `codex-security`의 루트 `AGENTS.md`와 `sdk/typescript/AGENTS.md`는 그 레포 개발자용 지침이다. 이 작업 공간의 분석 규칙이 아니므로 따르지 않고, 분석 대상 문서로만 읽는다.
- 이 레포는 한 레포 안에 배포 단위가 여러 개다(`sdk/typescript` npm 패키지, `plugins/codex-security` Codex 플러그인, `github-action`, `docker`). feature map에서 단위별로 `핵심`/`부속`을 나눌 때 이 경계를 쓴다.
