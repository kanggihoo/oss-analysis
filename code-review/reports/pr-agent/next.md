# pr-agent — 다음 시작점

- 분석 SHA: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q1~Q12 (세션 마무리)
- 검증 수준 요약: 이 문서는 점검 목록이라 별도 집계를 하지 않음. 개별 문서의 머리 참조.
- 실행 여부: 정적 추적만 (설치·실행·테스트·모델 호출 없음)

---

## 1. 확인한 범위

| 영역 | 확인 정도 |
|---|---|
| 실행 경로 | `agent/pr_agent.py` 전체, `servers/github_app.py` 전체, `servers/gitlab_webhook.py` 전체, `servers/utils.py` 앞 330줄, `cli.py` 전체 |
| `/review` | `tools/pr_reviewer.py` 전체(1750줄), `settings/pr_reviewer_prompts.toml` 시스템 프롬프트 앞부분과 user 템플릿 |
| `/improve` | `tools/pr_code_suggestions.py` 실행·예측·반성·검증 핵심부 |
| Diff | `algo/git_patch_processing.py` 전체, `algo/pr_processing.py` 전체, `algo/types.py`, `algo/file_filter.py`, `algo/language_handler.py` 일부 |
| Provider | `git_provider.py` 인터페이스·clone·persistent comment, `github_provider.py` 수집·게시·스레드 핵심, `gitlab_provider.py` 수집·증분·인라인·스레드 핵심, `plain_diff_provider.py`, `local_git_provider.py` 앞부분, `diff_parsing.py` |
| 메모리·상태 | `algo/review_finding_state.py` 전체, `algo/review_merge.py` 전체, `algo/inline_comment_dedup.py` 앞부분, `pr_similar_issue.py` 앞부분 |
| 문맥·규칙 | `algo/repo_context.py` 전체, `algo/skills_loader.py` 머리말, `config_loader.py`, `git_providers/utils.py` 설정 적용부, `config_security.py` 앞부분 |
| Jira·티켓 | `tools/ticket_pr_compliance_check.py` 앞 520줄과 `extract_tickets` 이후 전부 |
| LLM 호출 | `algo/ai_handlers/litellm_ai_handler.py` 메시지 구성·재시도·`_get_completion`·콜백, 나머지 핸들러 2종 |
| 의존성 | `pyproject.toml` 전체, `uv.lock`의 해당 패키지 항목, `docker/Dockerfile`, `docker/Dockerfile.lambda` 앞부분 |

## 2. 미확인 항목 체크리스트

### GUIDE 8절 "레포 하나의 완료 기준" 자체 점검

- [x] 모든 문서 머리의 SHA가 `repos.lock.tsv`와 같다.
- [x] Q1 호출 흐름 다이어그램이 있고 노드마다 코드 위치가 있다 (`00`, `01`).
- [x] 고정 문맥 확장 / 동적 탐색 / 재시도 / Agent Loop가 구분되어 있다 (`02` 3.1절, 4.1절).
- [ ] 종료 조건을 각각 확인했거나 미확인으로 표시했다: **부분 충족.** 정상·도구 없음·최대 반복·토큰·취소·모델 오류는 확인. **리뷰 전체에 대한 제한 시간(호출당이 아닌 실행 전체)의 부재**는 `pr_reviewer.py`, `pr_agent.py`, `servers/*` 범위에서 못 찾았으나 서버 계층(gunicorn `timeout`과 BackgroundTasks의 상호작용)을 끝까지 추적하지 않았다 → 미확인.
- [x] 검증 단계의 독립성과 추가 파일 접근 여부를 답했다 (`02` 5절).
- [x] 메모리는 쓰기와 읽기를 모두 추적했고, PR 간 메모리가 없는 범위를 근거와 함께 적었다 (`03` 7절).
- [x] 의존성 표에 선언·해석 버전, 선택/필수, 호출 위치가 있다. 선언만 있는 패키지(`anthropic`)를 구분했다. **단 간접(transitive) 의존성의 호출 위치와 라이선스는 조사하지 않았다**(`05` 2절 하단).
- [x] 모든 주장에 검증 수준과 지원 수준을 붙였다. `추론`에는 근거를 달았다.
- [x] README·문서와 코드가 다른 곳을 기록했다 (`00` 7절, `01` 3.9절, `02` 하단).
- [x] 5절의 최종 질문에 답했다 (`00` 6절, `06` 1절).
- [x] 정적 추적만 한 항목과 실행한 항목을 분리했다: 실행한 항목은 **없다.** 모든 "실행 예"는 정적 추적(손 계산)이며 문서에 그렇게 표시했다.

### 이번에 열지 않았거나 일부만 본 코드 (미확인)

- [ ] Bitbucket(Cloud/Server), Azure DevOps, Gitea, Gerrit, CodeCommit provider 내부와 해당 서버(`bitbucket_app.py`, `azuredevops_server_webhook.py`, `gitea_app.py`, `gerrit_server.py`, `github_polling.py` 본문, Lambda 웹훅)
- [ ] `/describe`, `/ask`, `/add_docs`, `/update_changelog`, `/generate_labels` 내부 (호출 지점과 모델 타입만 확인)
- [ ] `mosaico/`(A2A 서버) 내부. 모듈 머리말과 Docker 타깃만 확인
- [ ] `servers/request_body_limit.py`, `servers/github_action_runner.py`의 이벤트 분기 세부
- [ ] `git_providers/utils.py`의 `_get_per_directory_settings`(596-710) 병합 규칙 세부, `custom_merge_loader.py`
- [ ] `config_security.py`의 호스트 전용 키 전체 목록(앞 60줄과 per-directory 섹션 정의만 확인)
- [ ] `algo/token_budget.py`의 `AttemptTokenBudget` 상세(`fit_prompt_variable`, `fit_optional_text`)와 `get_max_tokens` 후반부, `algo/utils.py`의 `load_yaml` 복구 로직과 마크다운 변환
- [ ] `algo/ai_handlers/litellm_ai_handler.py` 3666줄 중 인증·reasoning·OpenRouter·Bedrock 분기 대부분, `cloud_auth.py`, `litellm_helpers.py`
- [ ] `settings/prompt_fragments.toml`(diff hunk 형식 설명 문구 본체), `pr_reviewer_prompts.toml` 출력 스키마·예시 후반부
- [ ] `pr_similar_issue.py` 중반 이후(인덱싱 세부), `inline_comment_dedup.py`의 `InlineCommentStore` 본문
- [ ] `docs/` 전체(제품 문서와 코드의 차이는 4개 문서만 대조), `tests/`의 내용(테스트 존재 여부만 확인, 통과 여부는 실행하지 않음)
- [ ] 업스트림 이슈 트래커·릴리스 노트·CHANGELOG (알려진 이슈는 코드에서 관찰한 것만 `06`에 기록)
- [ ] 전이 의존성 라이선스, LiteLLM 내부 동작(`anthropic` SDK 사용 여부 등)
- [ ] 실제 실행: 설치, 모델 호출, 웹훅 수신, 이미지 빌드. 사용자와 합의 후에만 진행(GUIDE 2.2절)

## 3. 다음에 볼 파일과 함수

| 우선 | 파일 · 함수 | 이유 |
|---|---|---|
| 1 | `pr_agent/algo/token_budget.py` — `AttemptTokenBudget.fit_prompt_variable`, `for_prompt_attempt` | 예산 초과 시 정확히 무엇을 자르고 어디서 `FallbackEligibleError`가 나는지 |
| 2 | `pr_agent/git_providers/utils.py:596-710` — `_get_per_directory_settings` | 경로별 규칙(모노레포) 병합 규칙 |
| 3 | `pr_agent/algo/inline_comment_dedup.py:201-313` — `InlineCommentStore` | PR 간 메모리 저장소로 교체할 인터페이스의 실제 계약 |
| 4 | `pr_agent/tools/pr_description.py` — `_prepare_prediction`, 다중 patch 경로(`get_pr_diff_multiple_patchs`) | `/describe` 대형 PR 처리 |
| 5 | `pr_agent/servers/github_action_runner.py:206-500` | Action 경로의 증분·`workflow_run` 처리 |
| 6 | `pr_agent/algo/utils.py` — `load_yaml`, `convert_to_markdown_v2`, `ticket_markdown_logic` | 응답 복구와 티켓 준수 결과 렌더링 |
| 7 | `pr_agent/git_providers/github_provider.py` — `_try_fix_invalid_inline_comments`, `_publish_inline_comments_fallback_with_verification` | 인라인 위치 실패 시 복구 |

## 4. 분석 중 생긴 질문

1. 파일이 50개를 넘고 API가 patch를 비워 준 파일은 `content_fetch_failed` 없이 조용히 누락되는가? (`github_provider.py:496-503,530-531`와 `pr_processing.py:618-627`의 조합을 재현해야 확인됨)
2. `commit_messages_str`을 `/review`가 수집만 하고 프롬프트에 쓰지 않는 것은 의도인가, 템플릿 개편의 잔재인가?
3. `pr_compliance_checklist.yaml`은 어떤 흐름이 읽는가(외부 워크플로, 이전 버전)?
4. 사람이 resolve한 스레드를 "dismissed"로 전달하는 것이 수정 후 resolve와 구분되지 않는데, 실제 사용에서 문제가 되는가?
5. `PRAgent(ai_handler=...)` 방식으로 에이전트 핸들러를 꽂을 때 핸들러가 PR 컨텍스트(SHA, 테넌트)를 얻는 가장 안전한 방법은 무엇인가? (현재 `chat_completion`은 `(model, system, user)`만 받음)
6. GitLab 인라인 게시에서 `get_relevant_diff`의 재조회가 리뷰 시점 SHA와 어긋난 사례가 있는가?
7. 우리 서비스에서 provider 계층만 import할 때 `get_settings()`/`starlette_context` 결합을 얼마나 얇게 감쌀 수 있는가? (프로토타입 필요, 실행은 사용자 합의 후)
8. GitHub/GitLab 외 `inline_key_issues` 지원 provider(Bitbucket Cloud, Azure)의 검증 가능성 조건(`can_verify_inline_comment_publication`) 세부.

---

## 5. 정정 이력(2026-10-13)

코드는 고정 SHA(`330f0813b5fe0d1f54b794077c2d02aa85a1fb63`, HEAD 확인)에서 파일을 다시 열어 확인한 뒤 고쳤다. 실행은 하지 않았다.

- `04-saas-and-isolation.md` Q10-1 "토큰 수명·갱신" 행: "요청마다 새 provider(→새 클라이언트)" 단정을 "provider 인스턴스를 만들 때마다 `AppInstallationAuth` 새로 생성, 요청당 한 번이라고 단정 불가"로 바꾸고 07 링크를 달았다. 이유: 도구가 `get_git_provider()(pr_url)`로 캐시 밖 인스턴스를 만든다(`tools/pr_questions.py:39` 등, `servers/github_app.py:338`). 지적대로였다.
- `04` Q10-3 "provider 인스턴스" 행: "요청 컨텍스트에 PR URL 키로 저장(요청 단위)"만 있던 서술에 캐시 우회 경로 목록과 07 3.2절 링크를 추가했다. 인용 줄 `git_providers/__init__.py:152-186`을 직접 열어 확인한 `151-185`(+`135-148`)로 고쳤다.
- `05-dependencies.md`: `tiktoken` 행을 "기본 로컬 추정, `force_accurate=True`일 때만 provider-native 추가"로 고치고, "토큰 계산 경로" 절을 추가했다(`token_handler.py:237-279,300-319,321-339`의 `litellm.acount_tokens`). 이유: 기존 서술이 tiktoken 위주라 불완전했다. 실제 외부 API 호출 여부는 LiteLLM 내부라 `미확인`으로 표시했다. 추가로 확인한 사실: `force_accurate=True` 호출자는 `tools/pr_help_docs.py:632`(과 `token_budget.py:447-451` 전달부)뿐이고 `/help_docs`는 이 SHA에서 비활성(`agent/pr_agent.py:69-71`)이다. 지적에 없던 내용이며 "기본 명령 경로에서는 호출되지 않는 것으로 보인다"로 적었다.
- `05` `anthropic` 행·후속 문장: "선언만 있음"을 "`pr_agent/`에 직접 import 없음(grep 재확인), LiteLLM 내부 사용 여부는 미확인"으로 고쳤다. 이유: "쓰이지 않음"으로 읽히는 것을 방지. 지적대로였다.
- `05` 외부 서비스 표에 provider 토큰 카운트 행(미확인 표시) 추가, 자체 구현·SDK 경계 표의 "토큰 예산" 행과 `litellm` 행 보완.
- `00-overview.md` Q11 행(`anthropic`은 선언만 -> 위 정정 문구, 토큰 계산 경로 추가), `06-fit.md` 의존성 표의 `tiktoken` 서술(정확 계산 경로 병기): 위 정정과 맞췄다.
- `07-credentials.md` §7: "정정 반영됨 2026-10-13" 표시를 추가했다(provider 행). 07 본문 3.2절은 이미 정확해 고치지 않았다(`151-181` 인용은 함수 끝 185까지가 아니라 캐시·반환까지의 범위).
- 모든 문서(00~07) 머리의 "검증 수준 요약": 숫자가 문서마다 다른 기준(05·06 불일치, 07은 머리 줄까지 포함)으로 집계돼 있어, 머리 줄을 제외한 본문 문자열 출현 횟수로 재집계하고 "대략 집계"(표 행 수 아님)라고 명시했다. 05는 10/5/3에서 16/8/10으로, 06은 1/5/3에서 2/6/4로, 00은 미확인 2에서 3으로, 07은 76/9/21에서 75/8/20으로 바뀌었다(01~04는 그대로). 표 행 단위 분류가 아니므로 정확한 통계로 쓰지 않는다.
