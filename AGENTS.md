# AGENTS.md — oss-analysis

이 레포는 AI와 함께 오픈소스를 분석하고, 검증한 지식을 쌓는 작업 공간이다.
규칙의 원본은 [OSS_ANALYSIS_WORKFLOW.md](OSS_ANALYSIS_WORKFLOW.md)다. 이 파일은 상황마다 읽을 곳만 가리킨다. **작업을 시작하기 전에 해당 절을 읽고 따른다.**

## 상황별로 읽을 곳

| 상황 | 읽을 곳 |
|---|---|
| 새 레포 분석 시작, 레포 업데이트 | [2장 분석 절차](OSS_ANALYSIS_WORKFLOW.md#2-분석-절차) 1~3단계, [1장 디렉터리 구조](OSS_ANALYSIS_WORKFLOW.md#1-디렉터리-구조) |
| 사용자가 레포에 대해 질문 | [2장 질문과 답변](OSS_ANALYSIS_WORKFLOW.md#질문과-답변), [4장 근거·검증 수준](OSS_ANALYSIS_WORKFLOW.md#4-근거-및-검증-수준-기준), [7장 설명·문서화 스타일](OSS_ANALYSIS_WORKFLOW.md#7-설명과-문서화-스타일-사용자-맞춤) |
| 질문에 답한 직후 | [2장 기능 스펙으로 넘어가기](OSS_ANALYSIS_WORKFLOW.md#기능-스펙으로-넘어가기)의 트리거 확인 |
| 기능 스펙 작성, 재구현 검증 | [8장 기능 스펙](OSS_ANALYSIS_WORKFLOW.md#8-기능-스펙-capability-spec) |
| reports와 wiki 중 어디에 쓸지 | [3장 역할 구분](OSS_ANALYSIS_WORKFLOW.md#3-reports와-wiki의-역할-구분) |
| wiki 페이지 작성·수정 | [wiki/SCHEMA.md](wiki/SCHEMA.md) |
| 코드 실행 실험 | [7.5 실행 실험 정책](OSS_ANALYSIS_WORKFLOW.md#75-실행-실험-정책) |
| 세션 마무리 | [2장 세션 마무리](OSS_ANALYSIS_WORKFLOW.md#세션-마무리) |
| 커밋할 대상 판단 | [5장 Git 관리 방침](OSS_ANALYSIS_WORKFLOW.md#5-git-관리-방침) |

## 템플릿 (`templates/`)

| 템플릿 | 쓰는 단계 | 만드는 파일 |
|---|---|---|
| [request-template.md](templates/request-template.md) | 새 레포 분석, 사용자 요청문 | — |
| [overview-template.md](templates/overview-template.md) | 2·3단계 | `reports/<repo>/overview.md` |
| [question-template.md](templates/question-template.md) | 질문과 답변 | `reports/<repo>/questions/qN-<topic>.md` |
| [next-template.md](templates/next-template.md) | 세션 마무리 | `reports/<repo>/next.md` |
| [capability-request-template.md](templates/capability-request-template.md) | 기능 스펙, 요청문 | — |
| [capability-spec-template.md](templates/capability-spec-template.md) | 기능 스펙 | `wiki/capabilities/<기능-slug>.md` |
