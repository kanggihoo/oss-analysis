# Q1. CodeWiki가 생성한 문서는 얼마나 정확한가? (2.0 vs 1.0.1)

- 분석일: 2026-09-30
- 대상: CodeWiki가 자기 레포를 문서화한 결과 두 개
  - **2.0 (우리 실행)**: `artifacts/CodeWiki/codewiki/` — generator 2.0.0, `claude-sonnet-5-5` (claude-code 구독 모드), `--max-depth 2`(기본값), 한국어 `--instructions`, commit `3e3d848`
  - **1.0.1 (업스트림 커밋본)**: `repos/CodeWiki/docs/` — generator 1.0.1, `claude-sonnet-4`, max_depth 설정 4, commit `3c4b4c2`
- 방법: 각 결과에서 구체적 주장(함수·호출 흐름·경로·플래그·기본값·Mermaid 엣지) 30~40개를 표본으로 뽑아, **그 문서가 생성된 commit의 코드**와 대조. 서브에이전트 2개가 병렬 수행, 주요 오류 일부는 직접 재확인.
- 검증 수준: 코드 확인 (표본 기반, 전수 아님)

## 결론

| | 2.0 (우리) | 1.0.1 (업스트림) |
|---|---|---|
| 표본 주장 | 34개 / 17페이지 | 40개 / 14페이지 |
| 정확 | 30 (88%) | 27 (68%) |
| 부분정확 | 3 | 6 |
| 부정확 | 1 | 7 |
| 존재하지 않는 식별자 | 없음 | 함수·클래스는 없음, **CLI 표면 3건** (`--repo`, `codewiki configure`, `--model`) |
| 페이지 / 줄 수 | 22 / 2,821 | 35 / 8,654 |
| 현재 코드와의 일치 | 동일 commit | 71커밋 뒤처짐 (109파일, +15.4k/−4.9k) |

- 둘 다 **식별자·상수·기본값은 매우 정확**하다. 상수·타임아웃·재시도 조건까지 코드와 일치한다.
- 오류는 두 버전 모두 **호출 주체(누가 누구를 부르는가)** 에 몰린다. 모듈 단위로 문서를 나눠 쓰기 때문에 모듈 경계를 넘는 호출 관계를 뭉개는 경향이 있다 (추론). Mermaid 모듈 간 엣지는 "개념 관계"로 읽는 것이 안전하다.
- 1.0.1은 CLI 사용법 서술이 틀린 곳이 많다(존재하지 않는 플래그, 호출되지 않는 `commit_documentation`/`to_backend_config()`를 주 경로로 서술).
- 2.0은 정확도가 높지만 분량이 1/3이다. ~~`max_depth` 2 vs 4 설정 차이로 보인다~~ → **depth 4 재실행으로 반증됨** (아래 "depth 4 재실행" 참고). 원인은 1.0.1과 2.0의 클러스터링 로직 차이로 추정 (미확인).
- 공통 최대 약점: **클래스 없는 함수 위주 파일이 통째로 누락** — `cli/commands/generate.py`(플래그 30여 개, rung 0 증분 경로), `mcp/server.py`·`mcp/tools/*`(MCP 도구 목록). 사용자가 실제로 만지는 표면이 빠진다.

## 2.0 결과 상세

### 오류
| 문서 | 주장 | 판정 | 코드 |
|---|---|---|---|
| `incremental_updater.md` | `DocumentationGenerator`가 `IncrementalUpdater.run()` 호출 | 부정확 | 실제 호출자는 `CLIDocumentationGenerator` (`codewiki/cli/adapters/doc_generator.py:432`) |
| `overview.md` 시퀀스 | CLI가 `run()` 호출 | 부분정확 | CLI는 그래프·클러스터·모듈 생성을 직접 호출, `run()`은 웹 경로 (`fe/background_worker.py:231`) |
| `cli_core.md` 시퀀스 | "_finalize_job (Stage 5)" | 부분정확 | `start_stage`는 1~4만 호출 (`doc_generator.py:185-515`) |
| `c_family_analyzers.md` | 미사용 헬퍼 `_find_containing_function` (양쪽 분석기) | 부분정확 | `c.py:169,190`에서 사용됨. 문서 내부 모순 |

### 잘한 점
- 캐시 규칙·폴백·위임 조건(`caw_backend.py:397-400`), MCP 세션 TTL/상한, 증분 업데이트 옵션 기본값 등 세부가 정확.
- 코드의 잠재 문제를 짚음: `artifact_exclude`가 런타임 instructions 병합에서 빠짐 (`codewiki/cli/models/config.py:283-293`, 직접 확인), 웹 캐시 키에 commit 없음, MCP `remove()`가 cleanup 안 함.
- 범위 밖 파일은 "미확인"으로 표시.

### 커버리지
- 충분: CLI 어댑터, 설정/git/HTML, caw 백엔드·toolkit, 증분 업데이트, artifact 분석, 언어 분석기, 웹 UI
- 얕음: 클러스터링 알고리즘(`cluster_modules.py`), `prompt_template.py`, `topo_sort`/`leaf_selection`/`external_symbols`
- 누락: `cli/commands/generate.py`, `cli/main.py`, `commands/config.py`, `mcp/server.py`·`mcp/tools/*`, `tests/`

## 1.0.1 결과 상세

### 오류 (commit 3c4b4c2 기준)
- 존재하지 않는 CLI: `codewiki generate --repo .` (`docs/CLI.md:56`, 실제는 `Path.cwd()`), `codewiki configure` (실제 `config` 그룹), `codewiki --repo-path ... --model`
- 호출되지 않는 경로를 주 경로로 서술: 생성 후 `commit_documentation`, `to_backend_config()`, `GitManager.get_commit_hash()`
- 웹: `from_cli` (실제 `from_args`), 라우트 `/api/jobs/{id}` (실제 `/api/job/{id}`)
- clean 검사가 항상 수행된다고 서술 (실제 `--create-branch`일 때만)
- 에러 flowchart가 `IncompleteGenerationError` 시 `job.fail()` 호출을 누락

### 커버리지
- 충분: CLI adapter·job 모델, config/git/html/progress, 백엔드·llm_services·caw, 분석기, MCP session/workspace, 웹
- 누락: `commands/generate.py` 본체(`--focus`/`--doc-type`/`--include` 언급 0회), MCP `server.py`·tools, `cli/utils`(api_errors, repo_validator 등), `security.py`

### 최신성 (HEAD 대비 누락)
`src/be/updater/` 패키지(컴포넌트 단위 증분 업데이트), Ruby/Scala 분석기, artifact-aware 생성(`artifact.py`), super-group 클러스터링, overview 프롬프트 방식 변경, viewer 재작성 등. 업스트림에 재생성 커밋(`bcfcf3f`)이 있으나 커밋된 `docs/`는 여전히 1.0.1 결과 (metadata 기준).

## 우리 워크플로우에 대한 시사점
- CodeWiki 결과는 **"어디에 무엇이 있는지" 지도와 상수·기본값 조회에는 신뢰도 높음**, **호출 흐름·CLI 사용법은 반드시 코드로 재검증** — AGENTS.md의 "second opinion" 취급과 일치.
- 함수 위주 진입점 파일(CLI 명령, MCP 서버)은 누락될 수 있으므로 해당 영역은 직접 추적한다.
- 더 세분화된 문서가 필요하면 `--max-depth`가 아니라 **`--max-token-per-leaf-module`을 낮춰** 새 출력 폴더에 재생성한다 (같은 폴더는 기존 `.md`를 건너뛰어 변화 없음 — `caw_backend.py:375-383`).

## depth 4 재실행 (같은 commit, 같은 모델)

- 산출물: `artifacts/CodeWiki/codewiki-depth4/`, 로그 `artifacts/CodeWiki/codewiki-depth4-generate.log`
- 검증 수준: 실행 확인 + 코드 확인

| | depth 2 | depth 4 |
|---|---|---|
| 소요 / CLI 표기 비용 | 약 18분 / $5.4 | 약 17분 / $5.1 |
| 페이지 / 줄 수 | 22 / 2,821 | 19 / 2,875 |
| 실제 트리 깊이 | 3 | 3 |
| 하위 모듈 위임 | 16회 중 2회 | 14회 중 1회 |
| 표본 정확 | 30/34 (88%) | **41/43 (95%)** |
| 부분정확 / 부정확 | 3 / 1 | 1 / 1 |

### 왜 깊어지지 않았나 (코드 + 로그 확인)
- `max_depth`는 위임의 **상한**일 뿐이다. 위임 조건은 `is_complex_module` AND `start_depth < max_depth` AND `num_tokens >= max_token_per_leaf_module`(기본 16,000) (`codewiki/src/be/caw_backend.py:397-401`).
- 로그상 모듈 토큰 수는 대부분 1,300~15,700 → 토큰 조건에서 탈락. 16,451 토큰인 모듈 1개만 위임됐다.
- 세분화를 원하면 `--max-token-per-leaf-module`을 낮춰야 한다 (추론, 미실행).
- 클러스터링은 LLM이 하므로 같은 입력에서도 모듈 트리가 달라진다 (이번 두 실행의 트리가 서로 다름, 실행 확인).

### 품질 차이
- **MCP**: depth 4에서 `mcp_server.md`가 생겨 도구 10개, `_analyze_lock`, 세션 생명주기까지 정확히 기술 → depth 2의 MCP 공백 해소. 단 `codewiki mcp` 서브커맨드(`cli/main.py:48`)는 여전히 미언급.
- **증분 업데이트**: 라우팅 규칙 표, LeafAgentRunner 흐름, `_recluster` 실패 시 children 미복원 지적(코드상 사실) 추가. depth 2의 호출자 오류(`DocumentationGenerator`→`IncrementalUpdater`)는 재발하지 않고 "CLIDocumentationGenerator, 미확인"으로 유보.
- **남은 오류 (같은 유형)**:
  - overview/pipeline 시퀀스 "CLI → `DG.run()`" (부분정확 — CLI는 `run()`을 부르지 않음, `doc_generator.py:190`)
  - `agent_backends_and_tools.md` Mermaid `IU[IncrementalUpdater] --> GB[get_backend]` (부정확 — updater는 `doc_generator.backend`를 주입받음, `doc_generator.py:432-433`; 직접 확인)
- **여전히 누락**: `generate.py` 플래그 표(`--update-rung`, `--github-pages` 등), 클러스터링 알고리즘 내부, `tests/`, `prompt_template.py`.

### 결론
- 같은 비용으로 depth 4 쪽이 약간 더 정확하고 MCP 커버리지가 좋았지만, 이는 `max_depth` 효과라기보다 **클러스터링이 매번 다르게 나오는 비결정성** 때문일 가능성이 크다 (추론). 실행 간 품질 편차가 있다는 점 자체가 중요한 관찰이다.
- 표본 3회 모두 **식별자 할루시네이션 0 (2.0 기준)**, 오류는 **호출 주체** 유형에 집중 — 이 패턴은 재현성 있게 관찰됨.

## 미확인
- `--max-token-per-leaf-module`을 낮췄을 때 분량·정확도 변화
- 1.0.1이 35페이지로 더 세분화된 실제 원인 (클러스터링 로직 차이 추정)
- 표본 외 주장의 정확도 (전수 검증 아님)
