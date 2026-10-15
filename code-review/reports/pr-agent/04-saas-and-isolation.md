# pr-agent — 인증, 큐, 격리, 장애 복구

- 분석 SHA: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q10
- 검증 수준 요약: 코드 확인 33 / 실행 확인 0 / 추론 0 / 미확인 1 (대략 집계: 머리 줄을 뺀 본문에서 각 표기 문자열이 나온 횟수이며, 표 행 수가 아니고 설명 문장 속 언급도 포함. 실행 확인 0은 실제로 실행한 항목이 없다는 뜻이고 본문의 "실행 확인" 문구는 실행하지 않았다는 서술. 2026-10-13 재집계)
- 실행 여부: 정적 추적만. 웹훅 서버를 띄우거나 호출하지 않았다.

> 요약: PR-Agent의 웹훅 서버는 **"단일 운영자가 한 벌의 자격증명으로 여러 저장소를 처리하는 서버"**이지 **멀티테넌트 SaaS 백엔드가 아니다.** 큐·영속 저장소·테넌트 개념이 코드에 없고, 요청 단위 격리는 "요청마다 설정 객체를 deepcopy"하는 방식이다. 이 문서의 "SaaS 기반 재사용" 판단은 이 사실을 전제로 한다.

---

## Q10-1. 인증

| 항목 | 구현 | 위치 | 검증 |
|---|---|---|---|
| GitHub 웹훅 서명 | `GITHUB.WEBHOOK_SECRET`이 **없으면 403으로 거부**(무인증 허용 안 함). `x-hub-signature-256`을 HMAC-SHA256으로 계산해 `hmac.compare_digest` 비교 | `servers/github_app.py:99-119`, `servers/utils.py:91-106` | 코드 확인 |
| GitHub App 토큰 | 웹훅 payload의 `installation.id`를 요청 컨텍스트에 넣고(`context["installation_id"]`), provider가 `Auth.AppInstallationAuth(AppAuth(app_id, private_key), installation_id)`로 클라이언트 생성. **App ID·개인 키는 서비스 설정에 한 벌**(`github.app_id`, `github.private_key`), 테넌트는 설치(installation) 단위 | `github_app.py:68-71`, `github_provider.py:112-118,1849-1893` | 코드 확인 |
| 토큰 수명·갱신 | 설치 토큰 발급·갱신은 PyGithub의 `AppInstallationAuth`에 위임. provider 인스턴스를 만들 때마다 `AppInstallationAuth`가 새로 만들어진다. 한 요청에 provider가 몇 번 만들어지는지는 아래 Q10-3 "provider 인스턴스" 행 참조(요청당 한 번이라고 단정할 수 없음, [07 3.2절](07-credentials.md)). 권한 범위는 GitHub App 설치 설정에 의존 | `git_providers/__init__.py:151-185`, `github_provider.py:1863-1867` | 코드 확인(위임 구조), 갱신 시점·인스턴스 간 토큰 공유 여부는 라이브러리 동작이라 미확인 |
| GitHub user 토큰 | `deployment_type="user"`면 `github.user_token` 한 개를 모든 요청에 사용(CLI/Action용) | `github_provider.py:1868-1875` | 코드 확인 |
| GitLab 웹훅 | `X-Gitlab-Token`이 `GITLAB.SHARED_SECRET`과 같으면 통과. 아니면 `<secret-name>:<webhook-token>` 형식으로 해석해 **시크릿 제공자(AWS Secrets Manager/GCS)**에서 `{webhook_token, gitlab_token}` JSON을 읽어 웹훅 토큰을 비교하고, 맞으면 **그 요청에만** 해당 `gitlab_token`을 쓴다 | `servers/gitlab_webhook.py:266-314`, `secret_providers/__init__.py:19-37` | 코드 확인 |
| GitLab API 토큰 | 기본은 호스트 설정의 `GITLAB.PERSONAL_ACCESS_TOKEN` 하나(`oauth_token` 또는 `private_token`). 위 시크릿 방식으로 웹훅별 토큰을 줄 수 있다 | `gitlab_webhook.py:180-234,299-314` | 코드 확인 |
| 토큰 보관 | 환경변수/`.secrets.toml`/Secrets Manager. 저장소 `.pr_agent.toml`이 연결 정보·키를 바꾸지 못하도록 차단 | `config_loader.py:51-52,103-159`, `config_security.py:1-60` | 코드 확인 |
| 사용자 자격 | `IdentityProvider.verify_eligibility("github", sender_id, api_url)`로 호출자 자격 확인. **기본 구현은 항상 ELIGIBLE**, 확장 지점으로만 존재 | `identity_providers/__init__.py:4-13`, `default_identity_provider.py:4-6`, `github_app.py:161,192,288,327` | 코드 확인 |
| 이벤트 필터 | 봇 발신자, PR 상태(open), 드래프트, 제목/라벨/브랜치/작성자/저장소 정규식 정책, 처음 열린 PR의 `synchronize`, 댓글은 `/`로 시작해야 함 | `github_app.py:364-376,383-424,459-474,129-139`, `servers/utils.py:344-` , `request_policy.py:28-48` | 코드 확인 |
| 요청 크기 | 웹훅 본문 상한 5 MiB | `configuration.toml:6`, `servers/request_body_limit.py` | 코드 확인(설정), 구현은 미열람 |

## Q10-2. 큐와 작업 처리

| 항목 | 구현 | 위치 | 검증 |
|---|---|---|---|
| 발행·소비 | **외부 큐 없음.** FastAPI `BackgroundTasks`가 응답 후 같은 프로세스에서 `handle_request`를 실행 | `github_app.py:72-77`, `gitlab_webhook.py:477-480` | 코드 확인 |
| ack/nack/재시도 | **없음.** 실패하면 로그만 남기고 끝. GitHub 재전송이 오면 다시 실행되며 중복 제거는 옵트인 | `github_app.py:427-456,535-538`, `gitlab_webhook.py:111-112` | 코드 확인 |
| 실패 작업 저장 | **없음.** DB·파일에 저장하지 않는다. 사용자에게는 실패 사유 댓글만 게시 | `pr_reviewer.py:506-525` | 코드 확인 |
| 워커 수 | gunicorn+uvicorn 워커 기본 `min 2, max 4`(cgroup CPU 기준), `preload_app=True`, `timeout=240` | `servers/gunicorn_config.py:78-83,145-162` | 코드 확인 |
| 동시성 제어 | PR 키 단위 `push_trigger_slot`(최대 1개 실행 + 대기 1개). **프로세스 로컬**이라 워커·레플리카 간에는 공유되지 않음 | `servers/utils.py:198-258` | 코드 확인 |
| 중복 제거 | `X-GitHub-Delivery` 인메모리 캐시(옵트인, 워커·레플리카 간 비공유, 재시작 시 소거) | `github_app.py:49-54,442-455`, `configuration.toml:354-358` | 코드 확인 |
| 폴링 대안 | `github_polling.py`는 알림 API를 폴링하며 인메모리 `deque`로 작업을 처리 | `servers/github_polling.py:1-30,363-393,489` | 코드 확인(앞부분·큐 부분만) |
| 장애 복구 | 프로세스 재시작 시 진행 중 작업과 중복 제거 상태가 사라진다. 복구 절차 코드 없음 | 위 행들 | 코드 확인(부재) |

기능 지원 수준: 큐·ack/nack·재시도·dead-letter = **미지원**(찾아본 곳: `servers/*.py`, `grep celery|kafka|redis|sqs|rabbit`). 이벤트 필터링·서명 검증 = **지원**.

## Q10-3. 테넌트 격리

PR-Agent에는 "테넌트"라는 데이터 모델이 없다. 조직/팀 범위가 전달되는 지점을 하나씩 확인했다.

| 지점 | 격리 방식 | 위치 | 검증 |
|---|---|---|---|
| 설정 | 요청마다 `copy.deepcopy(global_settings)`를 `starlette_context`에 넣어 요청 범위로 사용. 저장소 설정은 그 사본에만 병합 | `github_app.py:70`, `gitlab_webhook.py:320`, `config_loader.py:58-71`, `git_providers/utils.py:533-538` | 코드 확인 |
| provider 인스턴스 | `get_git_provider_with_context`는 요청 컨텍스트(`context["git_provider"]`, 웹훅 진입 시 빈 dict로 초기화)에 `{PR URL: provider}`로 캐시한다. **그러나 요청당 provider가 하나라고 단정할 수 없다.** 일부 도구와 서버 코드는 캐시를 거치지 않고 `get_git_provider()(pr_url)`로 직접 새 인스턴스를 만든다(`tools/pr_questions.py:39`, `pr_config.py:21`, `pr_add_docs.py:29`, `pr_generate_labels.py:37`, `pr_line_questions.py:25`, `pr_update_changelog.py:56`, `servers/github_app.py:338`). 상세와 토큰 발급 영향은 [07-credentials.md 3.2절·7절](07-credentials.md) | `git_providers/__init__.py:135-148,151-185`, `github_app.py:71` | 코드 확인 |
| 요청 단위 캐시 | `diff_files`, `git_files`, `repo_settings`가 컨텍스트에 저장되어 요청이 끝나면 사라짐 | `github_provider.py:360-401,446-453,567-571`, `git_providers/utils.py:299-310` | 코드 확인 |
| **프로세스 단위 캐시** | ① repo context(`_repo_context_process_cache`): 키가 `(provider 클래스, PR URL, 파일목록, 줄수, 커밋 SHA)`. SHA가 아니면 저장 안 함 ② 조직 전역 설정(`get_cached_global_settings`): 키 `ProviderClass:namespace` ③ 봇 사용자 ID: 키 `sha256(url:token)` ④ 웹훅 delivery ID | `repo_context.py:61,83-98`, `git_provider.py:230-262`, `git_provider.py:870-876`, `gitlab_webhook.py:178-234`, `github_app.py:49-54` | 코드 확인 |
| 공유되는 전역 자격증명 | LLM 키(`openai.key` 등), GitHub App 개인 키, GitLab 기본 토큰이 **서비스 전체에 한 벌** | `github_provider.py:1854-1858`, `litellm_ai_handler.py:314-321`(클래스 독스트링: 요청 격리는 PR-Agent 설정·캡처한 환경값 범위이고 배포 소유 LiteLLM 시크릿 매니저는 범위 밖) | 코드 확인 |
| 프로세스 전역 상태 | `os.environ["AUTO_CAST_FOR_DYNACONF"]`를 요청마다 설정, LiteLLM 전역 설정·콜백 사용 | `git_providers/utils.py:269,290`, `litellm_ai_handler.py:2556-2593` | 코드 확인 |
| DB 쿼리·큐 메시지·벡터 필터·메모리 조회 | 해당 저장소가 없으므로 **해당 없음.** 단, `/similar_issue`는 저장소별 네임스페이스/이름 필터로 인덱스를 나눈다 | `pr_similar_issue.py:89-92,195` | 코드 확인 |
| clone 경로·샌드박스 | 리뷰 경로에서 clone·샌드박스를 쓰지 않음 | 01 문서 2.1절 | 코드 확인 |

- 코드 확인: 요청 간에 **저장소 내용이 섞일 수 있는 공유 상태는 SHA 키(repo context)와 조직 네임스페이스 키(global settings)뿐**이고, 둘 다 키에 PR URL/네임스페이스가 포함된다. 단 `starlette_context`가 없는 실행(CLI, 스크립트)에서는 `get_settings()`가 **프로세스 전역 `global_settings`**로 떨어지므로 서비스 워커에서 직접 호출할 때는 반드시 요청 컨텍스트를 감싸야 한다(`config_loader.py:58-71`, `pr_agent.py:350-357`).
- **우리 서비스 관점(의견)**: 팀 A의 규칙/메모리/코드가 팀 B 리뷰에 섞이지 않는다는 보장은 PR-Agent에서 가져올 수 없다. 이 코드에는 조직 범위를 인자로 전달하는 계층이 없으므로, 격리 경계(작업 메시지에 org 식별자, 캐시 키에 org 포함, 자격증명 조회를 org로 스코프)는 PR-Agent 바깥에서 새로 설계해야 한다.

## Q10-4. 외부 서비스 장애·지연·비용이 영향을 주는 단계

| 외부 서비스 | 영향 단계 | 장애 시 동작 | 위치 | 검증 |
|---|---|---|---|---|
| LLM API | 리뷰 호출, `/improve` 반성 호출 | 같은 모델 재시도 2회 → fallback 모델 → 모두 실패 시 예외·실패 댓글. 호출당 `ai_timeout=120`초 | `litellm_ai_handler.py:2797-2801`, `pr_processing.py:830-872`, `configuration.toml:32-35` | 코드 확인 |
| Git Provider API | 파일 목록·본문 수집, 게시 | GitHub는 rate limit 시 `retry_call(tries=5, delay=2, backoff=2)`, 영구 오류는 즉시 실패. 파일 수 불일치 등은 "불완전" 오류 | `github_provider.py:429-441,575-588` | 코드 확인 |
| 티켓 시스템(Jira 등) | 입력 구성 | 실패하면 **그 티켓을 건너뛰고 리뷰는 계속**(예외는 잡아서 빈 목록 반환) | `ticket_pr_compliance_check.py:303-307,1180-1183` | 코드 확인 |
| repo context 파일 읽기 | 입력 구성 | 읽기 실패 시 건너뛰고(캐시도 안 함) 계속 | `repo_context.py:336-341,490-494` | 코드 확인 |
| 비용 | LLM 호출 수 = `/review` 1회(+청크 시 ≤3), `/improve` 청크 ≤3 + 반성 1, 재시도·fallback 배수 | 위 | `run_details`에 토큰·호출 수·비용 집계(`output_run_cost` 옵션) | `pr_agent.py:301-326`, `configuration.toml:69-70` | 코드 확인 |
| 관측 | OpenTelemetry 스팬·메트릭, Prometheus `/metrics`, LiteLLM 콜백(Langfuse 등) 옵션 | `pr_agent.py:339-372`, `telemetry/*`, `litellm_ai_handler.py:2556-2593` | 코드 확인 |

## Q10-5. 서비스 워커로 옮길 때 분리해야 할 의존성 (CLI·로컬 성격 코드)

PR-Agent는 CLI 도구가 아니라 서버 지원 구조이지만, 우리 워커에 **라이브러리로 포함**한다고 가정할 때 분리·주의할 지점이다(의견은 아래 표 마지막 열에 표시).

| 의존성 | 위치 | 영향 | 의견 |
|---|---|---|---|
| 전역 `global_settings`(Dynaconf) + `starlette_context` | `config_loader.py:25-71` | 컨텍스트 없이 호출하면 전역 설정을 공유 | 워커에서 요청마다 `request_cycle_context`로 감싼다(`pr_agent.py:350-357`이 이 패턴) |
| 환경변수 기반 자격증명 | `litellm_ai_handler.py:314-321` | 테넌트별 LLM 키를 요청 단위로 바꾸기 어렵다 | 테넌트별 키가 필요하면 핸들러를 교체(`PRAgent(ai_handler=...)`, `pr_agent.py:329-331`) |
| 파일 시스템(`skills`, `artifacts`, `push_outputs`, 로컬 `lancedb`) | `skills_loader.py`, `artifacts.py`, `output_sinks.py` | 호스트 경로를 읽거나 쓴다 | 서비스 워커에서는 모두 끄는 것이 안전(기본 비활성) |
| 프로세스 내 중복 제거·슬롯 | `servers/utils.py:198-258` | 워커 간 공유 안 됨 | 큐/분산 락으로 대체 |
