# AI 학습 오픈소스 분석 가이드

- 작성일: 2026-10-25
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기, 기능 지도 → 범위 승인 → 기능 스펙). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

사람이 AI와 함께 배우는 **AI 튜터·학습 앱** 오픈소스를 같은 기준으로 분석해 비교한다. 레포마다 `reports/<repo>/overview.md`(기능 지도·구조도)를 먼저 쓰고, 스펙 범위는 사용자가 지도를 보고 승인한다(기본). 비교 축(코드 확인 전 후보):

1. **학습자 상태**: 학습자가 무엇을 아는지를 어디에 어떤 형태로 저장하고, 다음 수업에 어떻게 쓰는가?
2. **수업 진행**: 계획 → 설명 → 연습 → 평가 흐름을 누가(코드/LLM) 결정하는가?
3. **자료 연결**: 사용자 문서·노트·웹 검색을 수업에 연결하는 방법(RAG, 지식 그래프 등).
4. **모델·데이터**: 어떤 모델 제공자를 쓰고, 데이터가 어디에 저장되고 어디로 나가는가?

## 디렉터리

```text
ai-learning/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt, 실행 실험(<주제>-demos/) 등 도구 출력
└── reports/<repo>/       # overview.md, capabilities/, questions/, diagrams/, next.md
```

루트 `repos/`·`reports/`와 섞지 않는다(`agent-memory/`, `herdr-plugin/`과 같은 방식). 이 폴더의 레포도 루트 `index.md`에 행을 둔다. 문서 안의 경로는 `ai-learning/…`처럼 루트 기준으로 쓰고, 문서 간 링크는 상대 경로를 쓴다.

## 분석 대상

| 이름 | URL | 하는 일 (README 기준, 코드 확인 전) | 라이선스 |
|---|---|---|---|
| DeepTutor | https://github.com/HKUDS/DeepTutor | 개인 맞춤 AI 튜터. Python(`deeptutor/`) 백엔드 + Next.js(`web/`) 웹, CLI. 지식베이스·읽기·북·학습 경로·멀티유저 등 | Apache-2.0 (`repos/DeepTutor/LICENSE`; 하위 MIT·CC BY-NC 4.0 등은 overview 1절) |
| learnharness | https://github.com/amosblomqvist/learnharness | 이해도를 측정하고 의존 관계 계획 → 가르치기 → 연습으로 이끄는 학습용 에이전트 하네스. 지식 그래프, 데스크톱 앱 | AGPL-3.0 (`repos/learnharness/LICENSE`, `skills/learnharness/LICENSE` 동일) |

"하는 일"은 README 요약이라 코드로 확인하지 않았다(`미확인`). 기준 SHA는 `repos.lock.tsv`, 각 overview의 frontmatter `sha`와 같다. 예전 wiki에 `deeptutor` 기록이 있다(`git show b52364d:wiki/projects/deeptutor.md`). 후보로만 읽는다.

## 진행 상태

| 레포 | 상태 |
|---|---|
| DeepTutor | 기능 지도 53행·구조도 완료(2026-10-25), 스펙 범위 승인 대기 |
| learnharness | 기능 지도 29행·구조도 완료(2026-10-25), 스펙 범위 승인 대기 |
