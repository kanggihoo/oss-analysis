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

### 그림 해설
그림을 열지 않고 이 글만 읽어도 구조와 흐름이 이해되도록 쓴다. 각 설명에 `파일:심볼`과 검증 수준을 붙인다.

**읽는 순서**
1. <처음 볼 영역 또는 진입점>
2. <그다음 따라갈 경로>

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| <모듈 A> | <역할과 경계> | <입력·출력, 호출 대상> | `<path>` `<symbol>` | 코드 확인 |

**실행 흐름: <대표 동작 이름>**
1. <단계> — 입력 `<...>` → 처리 `<...>` → 출력 `<...>` (`파일:심볼`)
2. <단계> — ...

**미확인 영역**
- <그림에 넣지 않았거나 코드로 확인하지 못한 부분>

---

## 4. 질문과 답변 목록 (Questions)

사용자가 질문한 내용과 코드 기반 답변 문서 링크입니다.

- [Q1: <질문 제목>](./questions/q1-<topic>.md) - *간단한 한 줄 결론 요약*
- [Q2: <질문 제목>](./questions/q2-<topic>.md) - *간단한 한 줄 결론 요약*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/<repo>.md](../../wiki/projects/<repo>.md)
- **기능 스펙**: <없음 | [wiki/capabilities/<기능-slug>.md](../../wiki/capabilities/<기능-slug>.md)>
