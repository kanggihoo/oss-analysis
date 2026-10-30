# oss-analysis

AI와 함께 오픈소스를 분석하고, 코드로 검증한 내용을 쌓는 작업 공간이다. 원본 코드는 보관하지 않는다(`repos/`는 Git 추적 제외).

| 파일·폴더 | 역할 |
|---|---|
| [AGENTS.md](AGENTS.md) | AI가 상황마다 읽을 곳 |
| [OSS_ANALYSIS_WORKFLOW.md](OSS_ANALYSIS_WORKFLOW.md) | 분석·기록 절차 (규칙 원본) |
| [index.md](index.md) | 분석한 레포와 기능 스펙 전체 목록 |
| [log.md](log.md) | 작업 기록 |
| [handoff.md](handoff.md) | 사용자 결정을 기다리는 항목 (레포 공통) |
| [SCHEMA.md](SCHEMA.md) | index·log 형식, reports 문서 frontmatter |
| `templates/` | 요청문·문서 양식 |
| `reports/<repo>/` | 레포 하나에 관한 분석 전부 |
| `artifacts/<repo>/` | 도구 출력 원재료 |
| `<주제>/` | 같은 목적으로 비교하는 레포 묶음 (`GUIDE.md` + 위와 같은 구조) |
| `scripts/check.py` | SHA·index·스펙 상태·링크 점검 |
