# <Repo Name> Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `<URL>`
- **분석 Commit SHA**: `<commit-sha>`
- **분석 일자**: `YYYY-MM-DD`
- **작업트리 상태**: `Clean / Modified (diff 보관 여부)`
- **분석 목적**: `<학습 / 설계 참고 / 도입 검토>`

---

## 2. 프로젝트 개요

<이 프로젝트가 해결하고자 하는 문제와 핵심 가치를 간결하게 서술>

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도 및 대표 실행 흐름 다이어그램입니다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 주요 컴포넌트 간 관계 및 경계 |
| 대표 실행 흐름 | [flow.json](./diagrams/flow.json) | [flow.html](./diagrams/flow.html) | 핵심 시나리오(요청 처리 / 라이프사이클) |

### 그림 읽는 가이드
1. <첫 번째로 주목할 영역이나 진입점 설명>
2. <데이터나 제어 흐름이 흘러가는 경로 설명>
3. <미확인 영역 또는 주의해서 보아야 할 경계>

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

다이어그램을 탐색하며 도출된 질문과 코드 기반 검증 보고서 링크입니다.

- [Q1: <질문 제목>](./questions/q1-<topic>.md) - *간단한 한 줄 결론 요약*
- [Q2: <질문 제목>](./questions/q2-<topic>.md) - *간단한 한 줄 결론 요약*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/<repo>.md](../../wiki/projects/<repo>.md)
