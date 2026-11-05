---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-11-05
updated: 2026-11-05
sources: []
---

# 두 리서치 도구의 내부 로직 비교

## 근거와 확인 한계

기존 기능 스펙을 읽고 비교했다. 현재 research/repos/ 아래 원본 clone이 없어 이번 세션의 원본 코드 재검증은 미확인이다. 아래는 기존 스펙의 코드 확인 기록을 요약한 설명이며 새 코드 확인으로 취급하지 않는다. 상대 분석: [overview](../../hyperresearch/overview.md).

## 입력 → 내부 동작 → 출력

- gpt-researcher: 질문 → 서브쿼리 계획 → 병렬 검색·스크랩 → 관련 본문 조각 선별 → 컨텍스트 → 보고서 작성. deep 모드는 질의별 조사에서 learning과 후속 질문을 뽑아 breadth·depth에 따라 재귀 조사한다. 근거: [연구 파이프라인](../../gpt-researcher/capabilities/research-pipeline.md), [Deep Research](../../gpt-researcher/capabilities/deep-research.md). 검증 수준: 미확인(이번 세션 원본 재검증), 기존 스펙은 코드 확인으로 기록.
- hyperresearch full 티어: 질문 분해 → 자료 수집·노트 저장 → 주장 충돌과 쟁점 분석 → 쟁점별 추가 조사 → 증거 다이제스트 → 각도별 초안 3개 → 충돌 대조·합성 → 비평·패치·인용 검사·다듬기 → 완료 검사. light는 단일 초안 경로다. 근거: [깊이 분석](../../hyperresearch/capabilities/depth-analysis.md), [초안·합성](../../hyperresearch/capabilities/draft-synthesis.md), [완료 검사](../../hyperresearch/capabilities/run-manifest-gate.md). 검증 수준: 미확인(이번 세션 원본 재검증), 기존 스펙은 코드 확인으로 기록.

## 핵심 차이

gpt-researcher는 Python 호출 경로가 조사를 진행하고 컨텍스트를 작성 단계에 넘긴다. hyperresearch는 호스트 에이전트가 스킬의 절차를 실행하며 Markdown 노트·SQLite·단계 산출물을 이어 사용한다. hyperresearch의 분석·초안 절차는 프롬프트 지시와 Python 검사로 나누어 이해해야 한다. 지시가 있다고 실제 모델이 항상 준수한다고 확정할 수 없다. 검증 수준: 추론(기존 스펙 비교).

## 다음 단계

기존 스펙 범위의 비교이므로 새 기능 스펙 요청은 만들지 않는다. 실제 품질·속도·비용의 우열은 미확인이다.
