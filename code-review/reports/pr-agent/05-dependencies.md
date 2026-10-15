# pr-agent — 의존성

- 분석 SHA: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q11
- 검증 수준 요약: 코드 확인 16 / 실행 확인 0 / 추론 8 / 미확인 10 (대략 집계: 머리 줄을 뺀 본문에서 각 표기 문자열이 나온 횟수이며, 표 행 수가 아니고 설명 문장 속 언급도 포함. 실행 확인 0은 실제로 실행한 항목이 없다는 뜻이고 본문의 "실행 확인" 문구는 실행하지 않았다는 서술. 2026-10-13 재집계)
- 실행 여부: 정적 추적만. 설치·빌드·`uv sync`를 실행하지 않았다. "해석 버전"은 `uv.lock` 파일의 기록을 읽은 값이다(설치 결과 확인이 아님).

검증 수준 표기: 표의 선언 버전·해석 버전·호출 위치·분류는 매니페스트·`uv.lock`·`grep`/파일 열람으로 확인한 **코드 확인**이다. 표의 "교체·제거 영향" 열 중 "추론"이라고 적은 것만 추론이고, 열람하지 않은 부분은 "미확인"으로 적었다. 지원 수준(필수/선택)은 extras·group 선언과 Docker 설치 명령으로 판단했다.

조사 순서: `pyproject.toml`의 선언 → `uv.lock`의 해석 버전 → `import` 위치 → 호출 함수 → 리뷰 단계. 버전은 이 SHA의 `pyproject.toml`(프로젝트 버전 `0.47.0`, `requires-python >= 3.12`, `pyproject.toml:5-20`)과 `uv.lock`(`revision = 5`)에서 읽었다.

---

## 1. 선언의 구조: base / extras / dependency group

| 구분 | 내용 | 위치 | 검증 |
|---|---|---|---|
| **base** (`dependencies`) | LLM(`litellm`, `openai`, `anthropic`), 서버(`fastapi`, `starlette`, `uvicorn`, `gunicorn`), 설정(`dynaconf`, `starlette-context`), diff/토큰(`tiktoken`, `unidiff`, `GitPython`), 프롬프트(`Jinja2`, `PyYAML`, `pydantic`), 관측(`opentelemetry-*`, `prometheus-client`, `langfuse`) 등 | `pyproject.toml:32-72` | 코드 확인 |
| **extras** (provider SDK는 선택) | `github`(PyGithub), `gitlab`(python-gitlab), `bitbucket`(atlassian-python-api), `azure`, `codecommit`(boto3), `gitea`(giteapy), `google`, `mosaico`(a2a-sdk), `all`(위 전부), `lambda`(mangum), `otel-grpc`, `langchain` | `pyproject.toml:92-131` | 코드 확인 |
| **dependency group** | `similar-issue`(pandas, pinecone, lancedb, qdrant-client), `integration-dev`(= `pr-agent[all]`), `dev`(pytest, ruff 등) | `pyproject.toml:136-156` | 코드 확인 |
| 잠금 파일 | `uv.lock`은 위 extras·groups를 모두 해석해 보관. `provides-extras = [github, gitlab, bitbucket, azure, codecommit, gitea, google, mosaico, all, lambda, otel-grpc, langchain]` | `uv.lock:2488-2660` | 코드 확인 |

- **"기본 설치에 모든 Provider와 벡터 DB가 포함된다"는 해석은 틀리다.** Provider SDK는 extras, 벡터 DB는 `similar-issue` 그룹이고 `langchain`은 `all`에도 들어 있지 않다(`pyproject.toml:116`). 단 **Docker 이미지는 `--extra all`로 설치**해 이전 이미지와 같은 구성을 유지한다(`pyproject.toml:115-116` 주석, `docker/Dockerfile:18`). Docker는 `similar-issue` 그룹과 `langchain`을 설치하지 않는다(`--no-dev --extra all`; 그룹 제외는 uv의 기본 그룹이 `dev`뿐이라는 규칙에 근거한 추론).
- provider는 지연 로딩되고 SDK가 없으면 `pip install 'pr-agent[<extra>]'` 안내와 함께 `ImportError`를 낸다(`git_providers/__init__.py:24-57`).
- `GitPython`은 **base에 선언**되어 있지만 `import git`은 `local_git_provider.py:5`와 `gerrit_provider.py:17`에만 있다. GitHub/GitLab 경로에서는 쓰이지 않는다. 일반 `clone()`은 GitPython이 아니라 **`git` 실행 파일을 `subprocess`로** 호출한다(`git_provider.py:564-570`). 즉 GitPython ≠ 모든 Provider의 clone이다.
- LangChain extra는 `LangChainOpenAIHandler`를 위한 것이다. 이 핸들러는 `config`로 선택되지 않고 코드 주입으로만 쓰이며 `[system, user]` 두 메시지만 보낸다(`langchain_ai_handler.py:77,104-109`). 기본 핸들러인 LiteLLM 경로와의 차이: LiteLLM은 다중 provider·스트리밍·캐시·추론 파라미터 처리 등 수천 줄(`litellm_ai_handler.py` 3666줄)을 갖고, LangChain 핸들러는 121줄이며 토큰 사용량·비용 집계를 연결하지 않는다(`:104-109` 주석).

## 2. 의존성 표

> 분류: 직접(declared)/간접(transitive), 필수/선택, 런타임/개발. "선언만 있고 직접 import가 없는" 항목은 비고에 표시했다.

| 패키지 | 선언 버전 | 해석 버전 | 분류 | 호출 위치 | 역할 | 교체·제거 영향 | 근거 |
|---|---|---|---|---|---|---|---|
| `litellm` | `==1.104.0` | 1.104.0 | 직접, 필수(base), 런타임 | `algo/ai_handlers/litellm_ai_handler.py:15,17`(`import litellm`, `from litellm import acompletion`), `_acompletion` `:3406-`, 호출은 리뷰 단계 `pr_reviewer.py:1216` | **모든 LLM 호출의 통로.** 다중 provider 라우팅, 모델 컨텍스트 메타데이터(`get_max_tokens`), `litellm.acount_tokens` 토큰 카운트(`token_handler.py:257`, 아래 "토큰 계산 경로") | 교체하려면 `BaseAiHandler` 구현을 갈아끼운다(`PRAgent(ai_handler=...)`, `pr_agent.py:329-331`). 핸들러가 LiteLLM 내부 모듈을 직접 import(`litellm.llms...`, `_get_model_info_helper`, `:20-38`, 사용 `:326,699,858`)하므로 **버전 결합이 강하다** | `pyproject.toml:41`, `uv.lock:1754-1755`, `docker/Dockerfile:4-10` |
| `openai` | `>=1.55.3` | 2.44.0 | 직접, 필수(base) | 예외 타입으로 `pr_processing.py:9,855`(재시도 대상 `openai.APIError`), `/similar_issue` 임베딩 `pr_similar_issue.py:6,31-35` | 오류 계층·임베딩 클라이언트 | 오류 타입을 LiteLLM이 `openai.*`로 매핑하므로 제거하면 fallback 판정(`pr_processing.py:855`)이 깨진다 | `pyproject.toml:43`, `uv.lock:2166-2167` |
| `anthropic` | `>=0.69.0` | 0.116.0 | 직접(선언), 필수(base) | **`pr_agent/` 아래 `.py` 파일에 `import anthropic`/`from anthropic` 직접 import 없음**(`grep` 결과, 이 SHA). Claude 모델은 LiteLLM을 거쳐 호출한다(핸들러는 `litellm.llms...`의 anthropic 모듈만 import, `litellm_ai_handler.py:20-23`) | pr_agent 코드가 직접 쓰지는 않는다. **LiteLLM 내부가 이 SDK를 쓰는지는 열어 보지 않아 미확인**("쓰이지 않는다"는 뜻이 아님) | 제거·교체 영향은 LiteLLM 내부 의존 여부에 달려 있어 미확인 | `pyproject.toml:34`, `uv.lock:197-198` |
| `tiktoken` | `==0.14.0` | 0.14.0 | 직접, 필수 | `algo/token_handler.py:11,332`(`self.encoder.encode`), `count_tokens`가 기본으로 돌려주는 값(`:321-337`) → `get_pr_diff` 예산 계산 | 로컬 토큰 수 추정(압축·청크·절단의 근거). `force_accurate=True`일 때만 provider-native 카운트를 추가로 시도(아래 `litellm` 보조 행과 "토큰 계산 경로" 참조) | 제거하면 기본 토큰 추정이 없어져 diff 예산 계산 불가 | `pyproject.toml:48`, `uv.lock:3626-3627` |
| `unidiff` | `==0.7.5` | 0.7.5 | 직접, 필수(base) | `git_providers/diff_parsing.py:1-2`, `plain_diff_provider.py:6,59` | **plain-diff 입력 파싱과 base 복원에만 사용.** GitHub/GitLab 경로는 사용 안 함 | GitHub/GitLab만 쓰면 제거해도 리뷰 경로는 동작(추론: import 위치 근거) | `pyproject.toml:50`, `uv.lock:3815-3816` |
| `GitPython` | `>=3.1.62,<4` | 3.1.62 | 직접, 필수(base) 선언 | `local_git_provider.py:5,46`, `gerrit_provider.py:17` | 로컬 브랜치 diff, Gerrit | GitHub/GitLab 서비스에서는 사실상 불필요(추론) | `pyproject.toml:38`, `uv.lock:878-879` |
| `PyGithub` | `>=2.10,<3` | 2.10.0 | 직접, **선택(extra `github`)** | `github_provider.py:13`(`Auth`, `Github`, `GithubIntegration`) → 파일 수집·게시 전체 | GitHub API 래퍼, App 설치 토큰 인증 | GitHub 지원 자체. `GithubProvider`는 `all` 또는 `github` extra 필요 | `pyproject.toml:94`, `uv.lock:3006-3007` |
| `python-gitlab` | `==8.3.0` | 8.3.0 | 직접, 선택(extra `gitlab`) | `gitlab_provider.py`, `servers/gitlab_webhook.py:194` | GitLab API 래퍼 | GitLab 지원 자체 | `pyproject.toml:95`, `uv.lock:3169-3170` |
| `atlassian-python-api` | `==3.41.4` | 3.41.4 | 직접, 선택(extra `bitbucket`) | Bitbucket provider들, **Jira 조회** `ticket_pr_compliance_check.py:227-237` | Bitbucket + Jira Cloud REST | **Jira 연동은 이 선언이 아니라 `[jira]` 호스트 설정 + 이 extra 설치가 있어야 동작**(없으면 경고 후 건너뜀). 선언만으로 Jira가 켜지지 않는다 | `pyproject.toml:96`, `uv.lock:229-230`, `docs fetching_ticket_context.md:179` |
| `fastapi`, `starlette`, `uvicorn`, `gunicorn` | `>=0.141.1,<1`, `>=1.6.0,<2`, `>=0.31.1,<1`, `==23.0.0` | 0.141.1, 1.6.0, 0.52.4, 23.0.0 | 직접, 필수(base) | `servers/github_app.py:7-12`, `servers/gitlab_webhook.py:9-16`, `servers/gunicorn_config.py` | 웹훅 서버. **리뷰 엔진 본체와 분리 가능**(엔진은 `PRAgent.handle_request`) | 우리 서비스가 자체 서버를 쓰면 `pr_agent/servers/`는 가져오지 않아도 됨 | `pyproject.toml:33-39,54,57` |
| `dynaconf` | `>=3.3.5,<4` | 3.3.5 | 직접, 필수 | `config_loader.py:5,25-55` | 계층형 설정·프롬프트 로딩(프롬프트가 TOML) | **프롬프트·설정 로딩이 전역 Dynaconf에 묶여 있어** 라이브러리로 쓸 때 가장 큰 결합점 | `pyproject.toml:36`, `uv.lock:681-682` |
| `starlette-context` | `==0.3.6` | 0.3.6 | 직접, 필수 | `config_loader.py:6,58-71`, `cli.py:8` | 요청 범위 설정·캐시 | 컨텍스트 없이 호출하면 전역 설정으로 폴백 | `pyproject.toml:47`, `uv.lock:3605-3606` |
| `Jinja2` | `==3.1.6` | 3.1.6 | 직접, 필수 | `algo/token_budget.py:6-7,477-483`(`SandboxedEnvironment`) | 프롬프트 템플릿 렌더 | 프롬프트가 Jinja 의존 | `pyproject.toml:40` |
| `PyYAML` | `==6.0.3` | 6.0.3 | 직접, 필수 | `algo/utils.py:13,987`(`load_yaml`) | **모델 응답(YAML) 파싱** | 출력 형식이 YAML이라 핵심 | `pyproject.toml:45` |
| `pydantic` | `==2.13.3` | 2.13.3 | 직접, 필수 | `algo/output_models.py:6` | 출력 스키마 검증(경고 수준) | 02 문서 5.1절 | `pyproject.toml:58` |
| `tenacity`, `retry` | `==8.2.3`, `==0.9.2` | 8.2.3, 0.9.2 | 직접, 필수 | `litellm_ai_handler.py:18`(LLM 재시도), `github_provider.py:18`(API 재시도) | 재시도 | 소규모 | `pyproject.toml:46,55` |
| `PyJWT` | `>=2.15.1,<3` | 2.15.1 | 직접, 필수 | `github_provider.py:16`(예외 import), `servers/bitbucket_app.py:13` | GitHub App JWT 오류 처리, Bitbucket JWT | GitHub App 인증 흐름 | `pyproject.toml:44` |
| `html2text` | `==2025.4.15` | 2025.4.15 | 직접, 필수 | `algo/utils.py:12,1572` | `/describe` 변경 요약 표 파싱 | 소규모 | `pyproject.toml:63` |
| `ujson` | `>=5.13.0,<6` | 5.13.0 | 직접, 필수 선언 | `secret_providers/google_cloud_storage_secret_provider.py:1` 한 곳 | GCS 시크릿 JSON | 사실상 선택 기능 전용(추론) | `pyproject.toml:49` |
| `langfuse` | `==3.14.5` | 3.14.5 | 직접, 필수 선언 | LiteLLM 콜백 이름 검사 `litellm_ai_handler.py:2567`, A2A 서버 `mosaico/observability.py` | LLM 호출 추적(콜백을 켠 경우만) | **import가 아니라 설정으로 켜질 때 쓰임.** 기본 경로에서는 호출되지 않음 | `pyproject.toml:56`, `uv.lock:1649-1650` |
| `opentelemetry-*`, `prometheus-client` | `==1.43.0`, `==0.21.1` | 동일 | 직접, 필수 선언 | `agent/pr_agent.py:8,339-372`, `telemetry/*` | 명령 스팬·토큰 메트릭·`/metrics` | 꺼도 동작(설정으로 비활성) | `pyproject.toml:66-71` |
| `a2a-sdk` | `==1.0.3` | 1.0.3 | 직접, 선택(extra `mosaico`) | `mosaico/server.py:14-24` | A2A 에이전트 서버 | 리뷰 경로와 무관 | `pyproject.toml:114`, `uv.lock:17-18` |
| `boto3` | `==1.43.78` | 1.43.78 | 직접, 선택(extra `codecommit`) | `codecommit_client.py`, `aws_secrets_manager_provider.py`, `litellm_ai_handler.py`(Bedrock 인증) | CodeCommit, AWS 시크릿 | 해당 기능만 | `pyproject.toml:102` |
| `azure-devops`, `azure-identity`, `msrest` | `==7.1.0b4`, `==1.25.0`, `==0.7.1` | 동일 | 직접, 선택(extra `azure`) | `azuredevops_provider.py`, `cloud_auth.py` | Azure DevOps, Azure AD 인증 | 해당 기능만 | `pyproject.toml:97-101` |
| `giteapy` | `==1.0.8` | 1.0.8 | 직접, 선택(extra `gitea`) | `gitea_provider.py` | Gitea | 해당 기능만 | `pyproject.toml:103` |
| `google-cloud-aiplatform`, `google-cloud-storage`, `protobuf` | `==1.154.0`, `==2.10.0`(py<3.13) / `==3.12.0`(py≥3.13), `==6.33.6` | 1.154.0, **2.10.0 및 3.12.0(파이썬 버전 마커별로 둘 다 잠금)**, 6.33.6 | 직접, 선택(extra `google`) | `cloud_auth.py`, `litellm_ai_handler.py`, GCS 시크릿 | Vertex AI 인증, GCS 시크릿 | 해당 기능만 | `pyproject.toml:104-113`, `uv.lock:1005-1007,1026-1027` |
| `pandas`, `pinecone`, `lancedb`, `qdrant-client` | 무버전(pandas), `==10.0.0`, `==0.38.0`, `==1.15.1` | 3.0.3, 10.0.0, 0.38.0, 1.15.1 | 직접, **선택(dependency group `similar-issue`)** | `pr_similar_issue.py:198-405`(지연 import) | `/similar_issue` 벡터 검색 | 리뷰 경로와 무관. Docker 이미지에는 미포함 | `pyproject.toml:139-147`, `uv.lock:2385,2437,1569,3247` |
| `langchain`, `langchain-core`, `langchain-openai` | 무버전 | 1.3.11, 1.4.8, 1.3.3 | 직접, 선택(extra `langchain`) | `algo/ai_handlers/langchain_ai_handler.py:13-20` (try/except import) | `LangChainOpenAIHandler` | 코드 주입으로만 쓰임, `all`에도 없음 | `pyproject.toml:126-131`, `uv.lock:1589-1590,1623-1624` |
| `mangum` | `==0.22.0` | 0.22.0 | 직접, 선택(extra `lambda`) | `servers/github_lambda_webhook.py`, `gitlab_lambda_webhook.py` | AWS Lambda 어댑터 | 해당 배포만 | `pyproject.toml:122` |

- 직접 import가 확인되지 않은 선언: `anthropic`(위 표 참조: pr_agent는 직접 import하지 않고, LiteLLM 내부 사용 여부는 미확인). `certifi`는 `git_providers/git_provider.py`(clone용 SSL 환경)에서 쓰이고, `urllib3`는 `gerrit_provider.py`가 import한다(`pyproject.toml:51-53` 주석).
- 간접(transitive) 의존성은 `uv.lock`에 프로젝트 자신을 포함해 185개 `[[package]]` 항목이 있다(`grep -c '^\[\[package\]\]'` 결과). 개별 전이 의존성별 호출 위치는 이번에 조사하지 않았다(미확인).

### 토큰 계산 경로 (tiktoken + LiteLLM provider-native)

| 경로 | 동작 | 위치 | 검증 |
|---|---|---|---|
| 기본(로컬 추정) | `count_tokens(patch)`가 `tiktoken` 인코더로 센 값을 그대로 반환 | `algo/token_handler.py:321-337` | 코드 확인 |
| 정확 계산(`force_accurate=True`) | `_get_token_count_by_model_type`이 `_await_coroutine(self._acount_tokens(patch))`를 호출하고, 값이 0보다 크면 그 값을 쓴다. 0이면 OpenAI 모델·키 설정 시 tiktoken 추정, 아니면 `model_token_count_estimate_factor`를 곱한 추정 | `token_handler.py:300-319,339` | 코드 확인 |
| provider-native 카운트 | `_acount_tokens`가 `litellm.acount_tokens(model=..., messages=[{"role":"user","content":patch}], system="system", api_key=..., api_base=...)`를 `asyncio.wait_for`(`config.ai_timeout`, 기본 120초)로 호출. 본문 9,000,000바이트 초과(`CLAUDE_MAX_CONTENT_SIZE`), 예외, 응답 `tokenizer_type == "local_tokenizer"`이면 0을 반환해 로컬 추정으로 돌아간다. 모델 문자열로 provider를 추정(`claude` 포함 시 `anthropic` 등)하고 설정의 API 키·base를 함께 넘긴다 | `token_handler.py:97,160-180,182-215,237-279` | 코드 확인 |
| 이 경로의 호출자 | `force_accurate=True`를 넘기는 곳은 `/help_docs`의 `count_tokens(docs_input, force_accurate=True)` 한 곳(`tools/pr_help_docs.py:632`)과 이를 전달하는 `AttemptTokenBudget.count_tokens`(`algo/token_budget.py:447-451`)뿐이다(`grep force_accurate`). **`/help_docs`는 이 SHA의 명령 매핑에서 비활성**(`agent/pr_agent.py:69-71`)이므로, 이 SHA의 기본 명령 경로에서는 이 정확 계산이 호출되지 않는 것으로 보인다 | `pr_help_docs.py:632`, `token_budget.py:447-451`, `pr_agent.py:69-71` | 코드 확인(호출자 grep), 다른 진입점에서의 간접 호출은 추론 |
| **실제 외부 API 호출 여부** | 코드는 `patch` 본문을 메시지로 `litellm.acount_tokens`에 넘기고 API 키·base도 전달한다. 이것이 provider 서버로 가는 네트워크 호출인지(예: 토큰 카운트 엔드포인트) LiteLLM 내부의 로컬 계산인지는 LiteLLM 소스를 열지 않아 **미확인**. 독스트링은 "provider-native counter"라고 설명한다(작성자 서술, 근거 아님) | `token_handler.py:237-245` | **미확인** |

### 자체 구현과 SDK의 경계

| 기능 | 자체 구현 | SDK/라이브러리 |
|---|---|---|
| diff 전처리(확장·압축·분할·번호 붙이기) | **전부 자체**(`git_patch_processing.py`, `pr_processing.py`) | `difflib`(표준 라이브러리), plain-diff만 `unidiff` |
| 토큰 예산 | 자체 계산 로직(`token_budget.py`) | 토큰 수는 기본 `tiktoken`, `force_accurate=True`일 때만 `litellm.acount_tokens`(위 "토큰 계산 경로") |
| LLM 호출 | 재시도·fallback·라우팅·프롬프트 정규화(`litellm_ai_handler.py`, `pr_processing.py`) | 실제 HTTP/provider 호출은 `litellm` |
| 에이전트 루프·검색·검증 | **없음** | - |
| Git 플랫폼 연동 | provider 어댑터(`git_providers/*`) | PyGithub, python-gitlab 등이 API 호출 |
| 메모리(같은 PR) | 자체(`review_finding_state.py`) | - |

## 3. 외부 서비스·바이너리 요구

| 요구 | 필수 여부 | 사용 위치 | 근거 |
|---|---|---|---|
| LLM API (LiteLLM이 지원하는 provider) | **필수** | 리뷰/개선/설명/질문 | `configuration.toml:8-9`(기본 모델 `gpt-5.6`, fallback `gpt-5.6-terra`: 설정값이며 이번에 호출해 보지 않음) |
| Git 호스팅 REST API(GitHub/GitLab 등) | **필수** | diff·본문 수집, 댓글 게시 | 01 문서 |
| provider 토큰 카운트(`litellm.acount_tokens`) | 선택 경로(`force_accurate=True`, 이 SHA에서는 비활성 `/help_docs`만 호출). 외부 호출 여부는 LiteLLM 내부라 **미확인** | `token_handler.py:237-279`, `pr_help_docs.py:632` | 코드 확인(호출 지점), 외부 호출 여부 미확인 |
| `git` 실행 파일 || `git` 실행 파일 | 리뷰 경로엔 **불필요**. clone 계열 코드(`GitProvider.clone`, Bitbucket Server, Gerrit)에서만 호출. Docker 이미지는 `git`과 `curl`을 apt로 설치 | `git_provider.py:564-570`, `bitbucket_server_provider.py:777`, `gerrit_provider.py:31-45`, `docker/Dockerfile:12` | 코드 확인 |
| Jira Cloud REST | 선택 | `ticket_pr_compliance_check.py:197-241` | 코드 확인 |
| Asana API | 선택 | `ticket_pr_compliance_check.py:381-392,553-632` | 코드 확인 |
| OpenAI 임베딩 + 벡터 DB(lancedb 로컬 파일/pinecone/qdrant) | `/similar_issue` 한정 | `pr_similar_issue.py:16-35,275-405` | 코드 확인 |
| 시크릿 제공자(AWS Secrets Manager, GCS) | 선택 | `secret_providers/__init__.py:19-37` | 코드 확인 |
| OTLP 수집기, Prometheus, Langfuse | 선택 | `telemetry/*`, `litellm_ai_handler.py:2567` | 코드 확인 |
| **DB, 메시지 큐, Redis, 컨테이너 샌드박스** | **요구 없음** | - | `grep`: 04 문서·03 문서 7.5절 |
| MCP 서버 | 요구 없음 (미지원) | - | 02 문서 3.1절 |

## 4. 최소 실행 구성 (문서·설정 근거)

| 목적 | 설치 | 필수 설정 | 근거 |
|---|---|---|---|
| 로컬 CLI로 GitHub PR 리뷰 | `pip install 'pr-agent[github]'` | `github.user_token`(`deployment_type="user"`), LLM 키 | `pyproject.toml:94,133-134`, `configuration.toml:312-315`, `github_provider.py:1868-1875` |
| 로컬 diff만 리뷰 | base만 (`plain-diff`와 `local`은 extra 매핑에 없음) | LLM 키 | `git_providers/__init__.py:21,24-32`, `cli.py:152-155,202-210` |
| GitHub App 서버 | base + `github` (Docker 타깃 `github_app`은 `--extra all`) | `github.deployment_type=app`, `github.app_id`, `github.private_key`, `github.webhook_secret`, LLM 키 | `docker/Dockerfile:18,33-35`, `github_provider.py:1852-1867`, `github_app.py:105-112` |
| GitLab webhook 서버 | base + `gitlab` | `gitlab.url`(없으면 시작 시 `ValueError`), 토큰, `gitlab.shared_secret`, LLM 키 | `gitlab_webhook.py:266-314,517-520`, `docker/Dockerfile:55-57` |
| Jira 포함 | 위 + `bitbucket` extra | 호스트 `[jira]`(`jira_site`, `jira_api_email`, `jira_api_token`) | `ticket_pr_compliance_check.py:197-241`, `configuration.toml:450-468` |
| `/similar_issue` | 위 + `uv sync --group similar-issue` | OpenAI 키, 벡터 DB 설정 | `pyproject.toml:139-147` |

숫자(이미지 크기, 메모리, 처리량)는 측정하지 않았으므로 적지 않는다.

## 5. 라이선스·비용 (근거 있는 범위)

- 프로젝트 라이선스: **MIT**(`LICENSE:1-3`, "Copyright (c) 2026 The PR Agent"). 코드 재사용이 가능하며 저작권 고지가 필요하다.
- 전이 의존성의 라이선스는 조사하지 않았다(미확인).
- API 비용: 호출 수 구조만 확인했다. `/review` 1회 호출(청크 사용 시 최대 3), `/improve`는 청크 최대 3 + 반성 1, fallback·재시도는 배수. 모델 단가·실비용은 측정하지 않았다. 실행 비용 집계 옵션: `output_run_cost`(`configuration.toml:70`).
- README는 이 저장소를 "community-maintained legacy project of Qodo"라고 밝힌다(`README.md:27`). 장기 유지 가능성은 우리 판단이 필요한 요소다(의견).
