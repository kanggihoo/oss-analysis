# 프롬프트·스킬 평가/개선 오픈소스 분석 가이드

- 작성일: 2026-10-22
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

내가 만든 스킬(SKILL.md)과 프롬프트를 **평가하고, 어떤 모델이 가장 맞는지 비교하고, 개선**하는 데 쓸 오픈소스 3개를 분석한다. 레포마다 먼저 아래 질문에 답할 수 있게 읽는다.

1. **평가**: SKILL.md(또는 프롬프트)를 여러 모델에 같은 케이스로 돌려 비교하려면 입력을 어떻게 구성하는가?
2. **개선**: 평가 결과(지표)를 받아 프롬프트를 고치는 기능이 있는가? 입력으로 무엇이 필요한가(평가셋, 채점 함수)?
3. **한계**: 비용, 라이선스, 데이터가 어디로 나가는가.

현재 단계는 **oss-repo-spec 5~6단계(기능 스펙, 통합 검토) 완료**다. 승인 범위(promptfoo 15개, prompt-optimizer 6개)의 스펙이 모두 `ready`이고, 다음 단계는 이 스펙을 바탕으로 한 환경 설계다(레포별 `reports/<repo>/next.md`). 재구현 검증은 하지 않았다.

## 디렉터리

```text
prompt-eval/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt 등 도구 출력
└── reports/<repo>/       # overview.md, diagrams/
```

루트 `repos/`·`reports/`와 섞지 않는다(`trading/`, `herdr-plugin/`과 같은 방식). 이 폴더의 레포도 루트 `index.md`에 행을 둔다.

## 분석 대상

| 이름 | URL | 하는 일 | 라이선스 (LICENSE 파일 확인) |
|---|---|---|---|
| dspy | https://github.com/stanfordnlp/dspy | 시그니처·모듈로 LM 프로그램을 짜고 옵티마이저(`dspy/teleprompt/`)가 프롬프트를 튜닝 | MIT (`repos/dspy/LICENSE`) |
| promptfoo | https://github.com/promptfoo/promptfoo | 프롬프트·에이전트·RAG 평가, 모델 비교, 레드팀 CLI | MIT (`repos/promptfoo/LICENSE`) |
| prompt-optimizer | https://github.com/linshenkx/prompt-optimizer | 프롬프트 최적화·모델 비교 GUI (web·desktop·extension·mcp-server 패키지) | AGPL-3.0-only (`repos/prompt-optimizer/LICENSE`) |

"하는 일" 열은 Obsidian 노트(README 요약)와 디렉터리 이름 기준이고 코드로 확인하지 않았다(`미확인`).

**dspy는 기능 스펙 범위에서 제외했다**(사용자 결정, 2026-10-22). 이유는 평가셋·채점 함수가 먼저 필요하고 최적화 호출 비용이 크며, 이번 목적은 promptfoo와 prompt-optimizer로 먼저 다루기 때문이다. overview(지도)는 남겨 둔다.

기준 SHA는 `repos.lock.tsv`와 같다. prompt-optimizer의 기본 브랜치는 `main`이 아니라 `develop`이다.

## 먼저 볼 곳 (후보, 코드로 확인 전)

| 레포 | 위치 | 이유 |
|---|---|---|
| promptfoo | `src/providers/claude-agent-sdk.ts` | `Skill` 도구 호출을 추려 내는 코드(`deriveSkillCalls`)가 있다. 스킬이 실제로 호출됐는지 평가할 수 있는지 확인 |
| promptfoo | `src/optimizer/promptOptimizer.ts` | 평가 도구 안에 프롬프트 최적화가 있다. 범위와 입력 확인 |
| promptfoo | `src/evaluator.ts`, `src/assertions/`, `src/providers/` | 케이스 실행, 채점, 모델 연결 |
| dspy | `dspy/teleprompt/`(`gepa/`, `mipro_optimizer_v2.py`, `simba.py` 등), `dspy/evaluate/` | 옵티마이저 종류와 평가 입력 |
| prompt-optimizer | `packages/core`, `packages/mcp-server` | 최적화 로직과 MCP 노출 방식 |
