---
name: oss-repo-spec
description: 레포 하나를 받아 이 작업 공간의 절차대로 처음부터 분석한다. clone, feature map, 사용자 범위 승인을 거쳐 기능별 스펙까지 쓴다. 새 레포 분석, 레포 전체 기능 스펙화, 이미 feature map이 있는 레포의 남은 스펙 이어 쓰기에 쓴다.
---

# oss-repo-spec

레포 URL 하나에서 시작해 `reports/<repo>/overview.md`(feature map)와 `reports/<repo>/capabilities/*.md`(기능 스펙)를 만든다. 결과물은 스펙과 스펙이 가리킨 원본 코드만으로 거의 같은 기능을 다시 만들 수 있어야 한다.

이 스킬은 순서와 멈출 곳만 정한다. 규칙의 원본은 [OSS_ANALYSIS_WORKFLOW.md](../../../OSS_ANALYSIS_WORKFLOW.md)다. 각 단계에서 가리킨 절을 먼저 읽고 그 절의 완료 조건을 따른다.

## 입력

- 레포 URL (필수)
- 목적과 스펙 범위 (선택). 형식은 [request-template.md](../../../templates/request-template.md)를 따르고, 범위가 없으면 "feature map 보고 정함"이다.
- 주제 폴더 (선택). 같은 목적의 `<주제>/GUIDE.md`가 있거나 사용자가 지정하면 모든 경로를 `<주제>/` 아래로 읽는다(워크플로 1장 "주제 폴더").
- 이미 `reports/<repo>/`가 있으면 처음부터 다시 쓰지 않는다. 빠진 산출물부터 채운다. feature map과 승인 범위가 이미 있으면 5단계부터 한다.

## 단계

1. **기준 고정.** 워크플로 2장 1~2번을 한다. 주제 폴더면 그 `GUIDE.md`를 먼저 읽는다. 결과는 clone, `repo-metadata.txt`(주제 폴더는 `repos.lock.tsv` 행도 됨), 라이선스, `index.md` 행, overview 1절(목적은 스펙을 어디에 쓸지까지)이다.
   - 완료: `python scripts/check.py <repo>`에 `[sha]`·`[index]` ERROR가 없다.
2. **좁혀 읽고 feature map 쓰기.** 워크플로 2장 3~4번을 하고, [overview-template.md](../../../templates/overview-template.md) 2절 형식으로 쓴다.
   - 읽는 순서는 파일 이름 → README·매니페스트·진입점 → 관련 문서 → 호출 경로다. feature map 단계는 진입점, 사용자 동작, 주요 호출을 설명할 수 있으면 멈추고, helper는 5단계에서 본다.
   - 중첩 패키지와 별도 배포 입구를 빠짐없이 찾아 `핵심`/`부속`으로 구분한다.
   - 세밀도는 목적이 정한다. 목적 밖 영역은 패밀리 한 행이나 "미탐색"으로 굵게 둔다. 20행을 넘으면 묶을 수 있는지 다시 본다.
   - 완료: 모든 행에 진입점·선행·구분·검증 수준이 있고, "대조한 범위와 미탐색 영역"이 적혀 있다.
3. **구조도.** 워크플로 2장 5번대로 archify 스킬로 구조도 하나와 그림 해설을 쓴다.
4. **범위 승인 — 여기서 멈춘다.** 워크플로 2장 6번대로 feature map 요약과 권장 범위를 보여 주고 답을 기다린다.
   - 표 한 장: 기능 · 한 줄 설명 · 구분 · 선행 · 권장(○/—와 이유 한 줄).
   - 질문은 한 번: "권장대로 / 행 추가·제외". `부속` 행은 기본 제외이고, 넣을 행만 고르게 한다.
   - 공유 계약과 패밀리로 묶은 행은 무엇을 묶었는지 한 줄 덧붙인다.
   - 묻기 전에 권장안을 overview 1절 "스펙 범위"(`승인 전 (권장안: …)`)와 `handoff.md` 대기 표에 적는다. 승인을 받으면 승인 범위로 바꾸고 handoff 행을 지운다. 요청이 "feature map만"이면 6단계 보고로 끝낸다.
5. **기능별 스펙.** 승인된 행마다 워크플로 4장 1~4번을 한다. 스펙 형식은 [capability-spec-template.md](../../../templates/capability-spec-template.md) 주석을 따른다.
   - 순서: 선행 계약과 공유 계약을 먼저 쓰고, 나머지는 feature map 순서대로 쓴다.
   - 병렬: 선행이 없는 행끼리는 서브에이전트에 맡겨도 된다. 지시문은 [capability-request-template.md](../../../templates/capability-request-template.md) 1번을 행마다 채워 쓴다. 작업자는 자기 스펙 파일만 쓰고, 메인 세션이 그들의 "feature map 보정 제안"을 feature map에 반영한다.
   - 분량: 규칙마다 글과 C-ID(코드 위치) 중 구현자가 더 짧고 정확하게 읽을 쪽을 고른다. 짧고 자기완결적인 함수는 C-ID 한 줄과 경계 설명이면 된다.
   - 완료: 승인된 모든 행에 스펙 파일이 있고, `python scripts/check.py <repo>`에 `[status]` ERROR가 없다(feature map·index 상태 = 스펙 `status`).
6. **통합 검토와 보고.** 워크플로 4장 5번(통합 검토 4항목)과 7번(연결·보고)을 하고, 6장대로 `next.md`·`index.md`·`log.md`를 갱신한다.
   - 보고: "재현 준비 완료" 또는 "조사·초안 작성 종료", `ready M / draft K / 미작성 N`, 남은 미결정, 바꾼 파일.
   - 재구현 검증(4장 6번)은 사용자가 요청할 때만 한다.

## 세션이 끊길 때

컨텍스트가 부족하면 지금 쓰는 스펙을 `draft`로 저장한다. 그리고 `next.md` 4절에 다음 기능, 진입 코드, 막힌 점을 적고 지금까지의 결과를 보고한다. 다음 세션은 `next.md`와 overview feature map에서 이어 간다.
