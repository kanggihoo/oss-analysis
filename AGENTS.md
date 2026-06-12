# AGENTS.md — oss-analysis workspace instructions

이 디렉토리는 Hermes `oss-analyst` profile의 기본 작업 공간이다.

- Hermes profile: `oss-analyst`
- Workspace root: `/Users/kkh/Desktop/oss-analysis`
- Long-term wiki: `./wiki`
- Repo clones: `./repos`
- Per-repo artifacts: `./artifacts/<repo>/`
- Human-facing reports: `./reports/<repo>/`

## 기본 원칙

1. 오픈소스 repo 분석은 단순히 `clone 후 읽기`로 끝내지 않는다.
2. 항상 다음 네 가지 입력을 분리한다.
   - 실제 local checkout: `repos/<repo>`
   - local analyzer 산출물: `artifacts/<repo>`
   - 외부 참고 자료: DeepWiki, README, docs, release notes
   - 최종 누적 지식: `wiki/`
3. graphify, Understand-Anything, DeepWiki 결과는 최종 정답이 아니라 `분석 후보/second opinion`이다.
4. 중요한 claim은 실제 파일 경로와 코드로 검증한 뒤 reports/wiki에 반영한다.
5. 새 세션에서는 먼저 이 파일과 `OSS_ANALYSIS_WORKFLOW.md`를 읽고 작업한다.

## 새 repo 분석 표준 흐름

1. 입력 repo URL과 분석 목적을 확인한다.
2. `repos/<repo>`에 clone 또는 update한다.
3. 현재 commit SHA를 기록한다.
4. GitHub metadata, README, docs, CI, dependency manifest를 확인한다.
5. 가능한 경우 DeepWiki `https://deepwiki.com/<owner>/<repo>`를 확인하고 notes로 저장한다.
6. 가능한 경우 `scripts/analyze-repo.sh <github-url>`를 실행해 기본 artifacts를 만든다.
7. graphify 결과가 있으면 `artifacts/<repo>/graphify/GRAPH_REPORT.md`, `graph.json`, `wiki/`를 읽는다.
8. Understand-Anything 결과가 있으면 `.understand-anything/knowledge-graph.json` 또는 copied artifacts를 읽는다.
9. Hermes가 핵심 claim을 실제 코드 파일로 검증한다.
10. `reports/<repo>/`에 분석 문서를 작성한다.
11. `wiki/projects/<repo>.md`, 관련 `concepts/`, `comparisons/`를 업데이트한다.
12. `wiki/index.md`와 `wiki/log.md`를 업데이트한다.



