# AGENTS.md — oss-analysis

오픈소스를 원본 코드로 검증하며 분석하고, 결과를 레포별로 쌓는 작업 공간이다. 절차와 규칙의 원본은 [OSS_ANALYSIS_WORKFLOW.md](OSS_ANALYSIS_WORKFLOW.md)이고, 작업 전에 아래 표에서 해당 장을 읽고 따른다.

## 항상

- 주장은 `repos/<repo>` 기준 SHA의 원본 코드로 확인하고, 주장마다 검증 수준(`코드 확인` / `실행 확인` / `추론` / `미확인`)을 붙인다(기능 스펙은 R-ID 단위로 묶어 붙인다). 분석기·DeepWiki 출력은 후보로 읽는다.
- 레포에 관한 글은 `reports/<repo>/`, 도구 출력은 `artifacts/<repo>/`에 쓰고, `index.md`(목록)와 `log.md`(기록)를 갱신한다.
- 확인한 내용은 요청이 없어도 문서에 반영하고, 바꾼 파일과 절을 한 줄로 보고한다.

## 상황별로 읽을 곳

| 상황 | 읽을 곳 |
|---|---|
| 새 레포 분석 (기능 지도 → 범위 승인 → 기능 스펙. 지도만이면 2장에서 끝) | 스킬 `oss-repo-spec`, [2장](OSS_ANALYSIS_WORKFLOW.md#2-새-레포-분석), [4장](OSS_ANALYSIS_WORKFLOW.md#4-기능-스펙) |
| 레포에 대한 질문 (답한 뒤 기능 스펙 트리거 확인까지) | [3장](OSS_ANALYSIS_WORKFLOW.md#3-질문과-답변), [7장](OSS_ANALYSIS_WORKFLOW.md#7-근거와-검증-수준), [8장](OSS_ANALYSIS_WORKFLOW.md#8-설명과-문서화) |
| 기능 스펙 작성, 재구현 검증 | [4장](OSS_ANALYSIS_WORKFLOW.md#4-기능-스펙) |
| 분석한 레포의 새 커밋 | [5장](OSS_ANALYSIS_WORKFLOW.md#5-레포가-업데이트됐을-때) |
| 세션 마무리 | [6장](OSS_ANALYSIS_WORKFLOW.md#6-세션-마무리) |
| 코드·명령 실행 실험 | [9장](OSS_ANALYSIS_WORKFLOW.md#9-실행-실험) |
| 저장 위치, reports frontmatter | [1장](OSS_ANALYSIS_WORKFLOW.md#1-저장-위치), [SCHEMA.md](SCHEMA.md) |
