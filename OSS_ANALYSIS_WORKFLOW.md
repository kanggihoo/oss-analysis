# OSS Analysis Workflow

Created: 2026-06-09
Updated: 2026-06-09
Workspace: `/Users/kkh/Desktop/oss-analysis`
Hermes profile: `oss-analyst`

이 문서는 `oss-analyst` profile이 `/Users/kkh/Desktop/oss-analysis`에서 오픈소스 코드베이스 분석을 반복 가능하게 수행하기 위한 기준 문서다.

## 1. 목표

이 workspace는 open-source analysis lab처럼 운영한다.

```text
repo clone/update
→ external/local analyzer output capture
→ Hermes가 실제 코드로 핵심 claim 검증
→ reports 작성
→ wiki에 durable knowledge 누적
→ 다음 repo 분석/비교에 재사용
```

핵심 원칙은 단순 요약이 아니라 **증거 기반 분석**이다. DeepWiki, graphify, Understand-Anything 결과는 분석 후보/second opinion이며, 중요한 결론은 실제 local checkout의 source path로 검증한다.

## 2. 현재 디렉토리 구조

```text
/Users/kkh/Desktop/oss-analysis/
├── AGENTS.md
├── OSS_ANALYSIS_WORKFLOW.md
├── .env.example
├── scripts/
│   ├── analyze-repo.sh
│   └── wiki-lint.py
├── repos/
│   └── <repo>/
├── artifacts/
│   └── <repo>/
│       ├── repo-metadata.txt
│       ├── static-analysis/
│       ├── deepwiki/
│       ├── graphify/
│       └── understand-anything/
├── reports/
│   └── <repo>/
│       ├── overview.md
│       ├── architecture.md
│       ├── code-map.md
│       ├── dependency-analysis.md
│       ├── test-ci-analysis.md
│       ├── risk-report.md
│       ├── deepwiki-comparison.md
│       ├── graphify-findings.md
│       └── understand-anything-findings.md
└── wiki/
    ├── SCHEMA.md
    ├── index.md
    ├── log.md
    ├── projects/
    ├── concepts/
    ├── comparisons/
    ├── queries/
    ├── raw/
    └── _meta/
```

## 3. 루트 디렉토리 역할

| 경로 | 역할 | 신뢰도/취급 |
|---|---|---|
| `repos/<repo>/` | 분석 대상 repo의 local checkout | primary evidence. architecture/runtime/dependency claim은 여기서 검증한다. |
| `artifacts/<repo>/` | analyzer와 external baseline의 raw output | evidence candidate. 그대로 결론으로 쓰지 않는다. |
| `reports/<repo>/` | 사람에게 보여줄 repo별 분석 보고서 | 검증된 결론과 source path를 포함한다. |
| `wiki/` | LLM Wiki 장기 지식 저장소 | 반복 사용 가능한 project/concept/comparison/query synthesis를 보관한다. |
| `scripts/` | workspace helper script | repo 분석 자동화, wiki health check 등 보조 도구를 둔다. |

## 4. 도구별 역할

| 도구 | 역할 | 저장 위치 |
|---|---|---|
| Hermes `oss-analyst` | 전체 orchestration, 검증, synthesis, report/wiki 작성 | profile + workspace |
| DeepWiki | 외부 baseline / second opinion | `artifacts/<repo>/deepwiki/` |
| graphify | repo-local knowledge graph / graph report | `artifacts/<repo>/graphify/` |
| Understand-Anything | dashboard, guided tour, diff impact, wiki graph 탐색 | `artifacts/<repo>/understand-anything/` |
| pygount/tokei | LOC/language/file composition | `artifacts/<repo>/static-analysis/` |
| semgrep/ast-grep | 정적 분석, pattern search | `artifacts/<repo>/static-analysis/` |
| llm-wiki | 장기 지식 저장소 | `wiki/` |

## 5. repo 분석 요청 형태

분석 요청은 가능하면 다음 형태가 좋다.

```text
Analyze https://github.com/owner/repo at depth=standard.
Focus on architecture, extension points, runtime flow, risks.
Use DeepWiki and graphify if available.
Update reports and wiki.
```

Depth 기준:

| depth | 범위 |
|---|---|
| `quick` | clone/update, README/docs, metadata, basic static summary, minimal overview |
| `standard` | quick + DeepWiki baseline, graphify, architecture/code-map reports, wiki update |
| `deep` | standard + dependency/security/test/CI/risk deep dive, Understand-Anything if available, comparisons |

## 6. 표준 분석 절차

### 6.1 Intake

확인할 것:

- GitHub URL 또는 local repo path
- 분석 깊이: `quick`, `standard`, `deep`
- focus: architecture, runtime flow, extension points, dependency, security, tests/CI, risks, project health, comparison
- 사용할 analyzer: DeepWiki, graphify, Understand-Anything, static analysis

### 6.2 Clone/update

가능하면 helper를 사용한다.

```bash
cd /Users/kkh/Desktop/oss-analysis
./scripts/analyze-repo.sh https://github.com/owner/repo
```

기대 저장 위치:

```text
repos/<repo>/
artifacts/<repo>/repo-metadata.txt
artifacts/<repo>/static-analysis/
reports/<repo>/README.md 또는 overview.md
```

### 6.3 Metadata/docs/manifest 확인

최소 확인 대상:

- README, docs, examples
- package manifests: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, etc.
- lockfiles
- CI: `.github/workflows/`, project-specific CI config
- test directories and scripts
- license and contribution docs when relevant

### 6.4 DeepWiki baseline

GitHub repo라면 다음 위치를 확인한다.

```text
https://deepwiki.com/<owner>/<repo>
```

유용한 내용이 있으면 raw capture와 parsed pages를 다음 위치에 저장한다.

```text
artifacts/<repo>/deepwiki/
├── raw/
├── toc.md
├── toc.json
├── pages-md/
├── pages-meta/ 또는 pages-json/
└── translated-ko/        # 필요한 경우
```

DeepWiki 결과는 다음 항목으로 분리해서 다룬다.

- DeepWiki가 주장한 내용
- local source로 검증된 내용
- local source에서 확인되지 않은 내용
- DeepWiki가 놓친 내용
- 최종 synthesis

### 6.5 graphify

graphify는 local graph analyzer / second opinion으로 사용한다.

일반적인 저장 위치:

```text
artifacts/<repo>/graphify/
├── GRAPH_REPORT.md
├── graph.json
├── graph.html
├── manifest.json
└── wiki/
```

graphify output에서 얻은 call graph, module cluster, generated wiki는 source 검증 전까지 hypothesis로 취급한다.

### 6.6 Understand-Anything

사용 가능한 환경에서는 repo root에서 guided tour, dashboard, diff impact, knowledge graph 탐색에 사용한다.

산출물은 다음 위치로 복사한다.

```text
artifacts/<repo>/understand-anything/
```

Understand-Anything 결과도 source verification 전까지 exploration aid로 취급한다.

### 6.7 Hermes source verification

Hermes는 외부 도구 결과를 그대로 믿지 않는다.

검증 규칙:

1. Architecture claim → 실제 file/module path를 확인한다.
2. Runtime flow claim → entrypoint와 call/data path를 확인한다.
3. Dependency/security claim → manifest, lockfile, CI, advisory를 확인한다.
4. Test/CI claim → test directory와 CI workflow를 확인한다.
5. Project health claim → GitHub metadata, release, issue/PR, commit history를 확인한다.
6. 검증 불가 claim은 `unverified` 또는 낮은 confidence로 표시한다.

## 7. reports 작성 기준

repo별 report는 가능하면 다음 파일로 나눈다.

```text
reports/<repo>/overview.md
reports/<repo>/architecture.md
reports/<repo>/code-map.md
reports/<repo>/dependency-analysis.md
reports/<repo>/test-ci-analysis.md
reports/<repo>/risk-report.md
reports/<repo>/deepwiki-comparison.md
reports/<repo>/graphify-findings.md
reports/<repo>/understand-anything-findings.md
```

보고서에는 다음을 포함한다.

- 분석 대상 repo URL과 local path
- 분석 commit SHA
- 사용한 artifacts 경로
- 핵심 claim별 source path evidence
- 검증된 내용과 미검증 내용을 분리한 결론

## 8. wiki 반영 기준

`wiki/`는 Hermes가 전담 관리하는 장기 지식 저장소다. 단순 작업 로그나 raw dump가 아니다.

반영 위치:

```text
wiki/projects/<repo>.md          # repo별 durable summary
wiki/concepts/<concept>.md       # 반복 출현하는 기술/패턴/분석 개념
wiki/comparisons/<topic>.md      # cross-repo 또는 tool 비교
wiki/queries/<query>.md          # 재사용 가치가 큰 질의 결과
wiki/index.md                    # catalog
wiki/log.md                      # append-only action log
```

운영 규칙:

1. wiki 편집 전 `wiki/SCHEMA.md`, `wiki/index.md`, 최근 `wiki/log.md`를 읽는다.
2. 기존 page를 검색한 뒤 새 page를 만들지 결정한다.
3. `repos/`, `artifacts/`, `reports/`의 안정적인 path를 frontmatter `sources:`에 기록한다.
4. raw output 전체를 wiki에 복사하지 않는다.
5. 모든 새/수정 page는 `index.md`와 `log.md`에 반영한다.
6. 큰 변경 후 `python3 scripts/wiki-lint.py`를 실행한다.

## 9. Wiki health check

wiki 기본 검증:

```bash
cd /Users/kkh/Desktop/oss-analysis
python3 scripts/wiki-lint.py
```

검사 항목:

- required wiki directories
- frontmatter required fields
- tags defined in `SCHEMA.md`
- broken wikilinks
- pages missing from `index.md`
- pages over recommended size

## 10. 최종 응답 기준

분석 작업을 완료한 뒤 사용자에게 보고할 때는 다음을 포함한다.

- 생성/수정한 `artifacts/`, `reports/`, `wiki/` 파일 경로
- 실제 실행한 analyzer 또는 명령 결과 요약
- 검증한 source path
- 검증하지 못한 claim과 이유
- 다음에 이어서 볼 수 있는 구체적 후속 작업
