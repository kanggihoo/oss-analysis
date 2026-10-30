# 프롬프트·스킬 평가/개선 오픈소스 분석 가이드

- 작성일: 2026-10-22
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

내가 만든 스킬(SKILL.md)과 프롬프트를 **평가하고, 어떤 모델이 가장 맞는지 비교하고, 개선**하는 데 쓸 오픈소스 3개를 분석한다. 레포마다 먼저 아래 질문에 답할 수 있게 읽는다.

1. **평가**: SKILL.md(또는 프롬프트)를 여러 모델에 같은 케이스로 돌려 비교하려면 입력을 어떻게 구성하는가?
2. **개선**: 평가 결과(지표)를 받아 프롬프트를 고치는 기능이 있는가? 입력으로 무엇이 필요한가(평가셋, 채점 함수)?
3. **한계**: 비용, 라이선스, 데이터가 어디로 나가는가.

현재 단계는 **oss-repo-spec 5~6단계(기능 스펙, 통합 검토) 완료**다. 승인 범위(promptfoo 15개, prompt-optimizer 6개)의 스펙이 모두 `ready`이고, 다음 단계는 이 스펙을 바탕으로 한 환경 설계다(레포별 `reports/<repo>/next.md`). 재구현 검증은 하지 않았다. 구현에 들어가기 전에 부족한 것은 아래 "구현 준비 점검"에 있다.

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

**dspy는 기능 스펙 범위에서 제외했다**(사용자 결정, 2026-10-22). 이유는 평가셋·채점 함수가 먼저 필요하고 최적화 호출 비용이 크며, 이번 목적은 promptfoo와 prompt-optimizer로 먼저 다루기 때문이다. overview(feature map)는 남겨 둔다.

기준 SHA는 `repos.lock.tsv`와 같다. prompt-optimizer의 기본 브랜치는 `main`이 아니라 `develop`이다.

## 먼저 볼 곳 (후보, 코드로 확인 전)

| 레포 | 위치 | 이유 |
|---|---|---|
| promptfoo | `src/providers/claude-agent-sdk.ts` | `Skill` 도구 호출을 추려 내는 코드(`deriveSkillCalls`)가 있다. 스킬이 실제로 호출됐는지 평가할 수 있는지 확인 |
| promptfoo | `src/optimizer/promptOptimizer.ts` | 평가 도구 안에 프롬프트 최적화가 있다. 범위와 입력 확인 |
| promptfoo | `src/evaluator.ts`, `src/assertions/`, `src/providers/` | 케이스 실행, 채점, 모델 연결 |
| dspy | `dspy/teleprompt/`(`gepa/`, `mipro_optimizer_v2.py`, `simba.py` 등), `dspy/evaluate/` | 옵티마이저 종류와 평가 입력 |
| prompt-optimizer | `packages/core`, `packages/mcp-server` | 최적화 로직과 MCP 노출 방식 |

## 구현 준비 점검 (2026-10-24)

스펙 21개의 frontmatter·1.4 "미결정"·적용 메모를 모두 읽고, skill-calls-metadata 1부를 끝까지 읽어 판단했다(`추론`, 재구현은 하지 않음).

- **원본 동작 재현**: 21개 모두 `ready`, 미결정 없음, R-ID·C-ID·수락 사례가 있다. 다만 `reimplementation: 미실행`이고 실행 확인이 하나도 없어서, 재현 가능하다는 판단은 아직 검증되지 않았다. 작은 스펙(skill-calls-metadata, history-chain)으로 4장 6번 재구현 검증을 먼저 해 볼 수 있다.
- **내 평가·개선 환경 구현**: 지금 문서만으로는 구현자가 추측할 부분이 많다. 스펙 본문은 원본 동작이고, 우리 요구사항은 21개 적용 메모에 "후보"로 흩어져 있다.

### 사용자가 정해야 할 것

1. 기반: promptfoo를 엔진으로 쓰고 기록·조회·루프만 붙일지, 직접 다시 만들지. 이 결정에 따라 필요한 스펙 범위가 크게 달라진다.
2. 스킬 투입 방식: 채팅 모델에 시스템 프롬프트로 넣을지, 에이전트 런타임(Claude Agent SDK·Codex·OpenCode)에서 실제로 로딩할지. `skill-used` 측정은 에이전트 런타임에서만 된다(skill-calls-metadata R-13).
3. 대상 모델 목록, 심판 모델, 호출 예산(반복 N × 모델 × 케이스 × 심판).
4. 개선 루프: 점수 기반 자동 채택(promptfoo optimize 구조)인지, 사람 승인인지. 종료 조건과 채택 기준.
5. 임계값: 심판 안정성(일치율·표준편차), 합격선, 종료 코드.
6. 첫 대상 스킬, 평가 차원(rubric), 테스트 케이스. 어느 문서에도 없다.
7. 구현 언어와 UI 필요 여부(`promptfoo view` 재사용 / 읽기 전용 서버 / 없음).

### 실행으로 닫아야 할 사실 (구현을 막는 것만)

- Claude Agent SDK의 스킬 발견·로딩과 `Skill` 도구 호출 모양. 2번에서 에이전트 런타임을 고르면 `skill-used`가 이 가정에 기댄다(agent-providers 확인 한계 ①).
- `{{env.X}}` 렌더 값이 `evals.config`에 저장되는지. promptfoo를 그대로 쓰면 DB에 API 키가 남을 수 있다(results-store R-37).
- repeat와 캐시: 반복 실행 때 캐시가 분산을 0으로 만드는지(eval-run R-52, response-cache). 안정성 측정 설계에 직접 영향을 준다.
- `mustache`·`jsonrepair` 내부, 어댑터별 `onError` 횟수는 라이브러리 버전을 맞추면 되므로 구현을 막지 않는다.

### 적용 메모에 흩어진 공통 결정 (한 문서로 모아야 할 것)

| 공통 결정 | 나오는 스펙 |
|---|---|
| 기록 행 키 `(실행 id, 모델, 스킬 버전, 케이스 안정 id, repeat)` | eval-records, eval-run, results-store, web-ui |
| 버전별 점수 이력(원본에 없음) | history-chain, llm-evaluation, iterate-rewrite, results-store |
| 심판 독립성(심판≠대상, 심판 id·설정 기록, 순서 교대) | llm-evaluation, default-providers, model-graded-matchers, calibration-script |
| 채점 장애를 불합격과 분리(`graderError`·`parseQuality`·`parseFailed`) | assertion-family, model-graded-matchers, llm-evaluation |
| 반복 채점과 점수 분산 | eval-run, model-graded-matchers, calibration-script |
| 스킬 내용 해시(캐시 키·resume·버전 식별) | response-cache, eval-run, config-loading |
| 개선 결과 검사(변수·frontmatter 보존, 빈 응답 오류) | promptfoo prompt-optimize, prompt-optimizer prompt-optimize, iterate-rewrite |
| 점수 척도: prompt-optimizer는 0~100, promptfoo는 0~1 | llm-evaluation, model-graded-matchers |
