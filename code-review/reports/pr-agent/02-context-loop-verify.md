# pr-agent — 문맥 확보, Agent Loop 여부, 검증

- 분석 SHA: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q3, Q4, Q5
- 검증 수준 요약: 코드 확인 31 / 실행 확인 0 / 추론 2 / 미확인 2 (대략 집계: 머리 줄을 뺀 본문에서 각 표기 문자열이 나온 횟수이며, 표 행 수가 아니고 설명 문장 속 언급도 포함. 실행 확인 0은 실제로 실행한 항목이 없다는 뜻이고 본문의 "실행 확인" 문구는 실행하지 않았다는 서술. 2026-10-13 재집계)
- 실행 여부: 정적 추적만. 모델을 호출하지 않았고, 아래 "실행 예"는 코드 경로를 따라간 정적 추적이다.

> 결론부터: 이 SHA의 PR-Agent는 **"고정 규칙 전처리 + 단발 LLM 호출(청크 병렬, 모델 fallback, `/improve`만 2단계)"** 구조이며 **Agent Loop가 없다.** 사용자의 체감("고정 diff 주변 줄 확장만으로는 문맥 부족")은 코드와 일치한다. 다만 이를 "단발성이라 한계"라고 단정하지 않고 아래 코드 근거로 판단했다.

---

<a id="q3"></a>
## Q3. 문맥 확보와 동적 탐색

### 3.1 자동 수집(고정)과 모델 요청(동적)의 분리

**프로그램이 자동 수집해 최초 프롬프트에 넣는 것** (모두 `PRReviewer.__init__`의 `self.vars`, `pr_reviewer.py:237-277`):

| 구분 | 수집 방법 | 상한·규칙 | 프롬프트 위치 | 위치 | 검증 |
|---|---|---|---|---|---|
| diff hunk + 주변 줄 | `get_pr_diff` → `extend_patch` | 앞 5줄/뒤 1줄, 동적 문맥 최대 10줄, 예산 초과 시 확장 포기 | user 메시지 `The PR code diff:` | `pr_processing.py:206-381`, `git_patch_processing.py:33-234`, `pr_reviewer_prompts.toml:338-342` | 코드 확인 |
| PR 제목·브랜치·설명 | provider API | 설명은 `max_description_tokens`(설정 있음) | user 메시지 `--PR Info--` | `pr_reviewer.py:226-227,238-240`, `pr_reviewer_prompts.toml:291-307` | 코드 확인 |
| 커밋 메시지 | provider API | `max_commits_tokens=500`으로 `clip_tokens` | vars `commit_messages_str`로 수집되지만 **`pr_reviewer_prompts.toml`에는 이 변수를 쓰는 곳이 없다**(grep 0건). 즉 `/review` 모델 입력에는 들어가지 않는다 | `github_provider.py:2033-2050`, `pr_reviewer.py:265` | 코드 확인 |
| 티켓(이슈·Jira 등) | 제목/설명/브랜치에서 키 추출 후 API 조회 | 합계 최대 5(`MAX_TICKETS`), 본문 1만 자 | user 메시지 `--PR Ticket Info--` | `ticket_pr_compliance_check.py:59-65,945-1218`, `pr_reviewer_prompts.toml:253-288` | 코드 확인 |
| 저장소 지침 파일 | 설정된 **고정 경로**(기본 `AGENTS.md`)를 provider로 읽음. 기본 브랜치 우선 | 합계 500줄, 15분 TTL 캐시 | system 메시지 `Repository context:` | `repo_context.py:446-494`, `configuration.toml:40-47`, `pr_reviewer_prompts.toml:51-58` | 코드 확인 |
| 스킬(SKILL.md) | **PR-Agent 호스트의 파일시스템** 경로를 재귀 탐색, 텍스트만 인라인 | `max_skills_tokens=8000`, 기본 비활성 | system 메시지 맨 앞 | `skills_loader.py:1-37,197-300`, `configuration.toml:579-591`, `pr_reviewer_prompts.toml:2-8` | 코드 확인 |
| CI 아티팩트 | 파일 경로(`artifact_path`)를 읽어 잘라서 삽입. 신뢰할 수 없는 데이터로 표시 | `max_artifact_size=50000`자 | user 메시지 앞부분 | `artifacts.py:92-203`, `configuration.toml:593-607` | 코드 확인 |
| 같은 PR의 이전 finding | 이전 리뷰 댓글의 숨은 마커 + 사람이 resolve한 스레드 | `max_previous_findings_chars=8000` | user 메시지 `Findings from earlier reviews of this PR` | `pr_reviewer.py:681-717`, `review_finding_state.py:314-351`, `pr_reviewer_prompts.toml:323-333` | 코드 확인 (상세는 [03](03-incremental-memory-rules.md#q7)) |
| 이전 제안 스레드(`/improve`) | GitLab/Azure DevOps 스레드를 JSON으로 | `max_discussion_context_chars=24000` | `/improve` 프롬프트 | `git_provider.py:382-413`, `pr_code_suggestions.py:306-308,335-343` | 코드 확인 |
| 사용자 Q&A | `/answer` 시 이전 질문/답변 댓글 | - | user 메시지 | `pr_reviewer.py:1585-1615` | 코드 확인 |

**모델이 요청해서 읽는 것: 없음.** 모델에게 도구를 주는 코드가 없다. 근거:
- 모델 호출은 `messages = [system, user]` 두 개뿐이고 `kwargs`에 `tools`/`tool_choice`가 없다: `litellm_ai_handler.py:2863-2868`(메시지 구성), `:2987-2991`(요청 kwargs), `base_ai_handler.py:18-30`.
- `pr_agent/**/*.py`에서 `tool_calls`, `tool_choice`, `tools=`, `function_call`, `mcp`, `MCP`, `ReAct`, `agent_loop`를 검색했으나 **0건**이다(grep).
- 유지보수자도 코드에서 같은 사실을 적었다: "PR-Agent supports text-only skills ... because PR-Agent uses a single-shot model call (no tool-use loop)" (`configuration.toml:579-591`), "PR-Agent runs single-shot model calls and has no tool-use loop" (`skills_loader.py:25-27`). 이 문구는 개발자 진술이며 위 grep과 호출 코드로 따로 확인했다.
- LangChain/OpenAI 핸들러도 `[system, user]`만 보낸다(`langchain_ai_handler.py:77`, `openai_ai_handler.py:54`). 두 핸들러는 설정으로 선택되지 않고 코드 주입으로만 쓰인다(`openai_ai_handler.py:66-69`, `langchain_ai_handler.py:104-109` 주석). **LiteLLM 사용 ≠ 에이전트 구조**다.

### 3.2 탐색 수단과 도구 스키마 표

| 도구 | 입력 | 출력 | 탐색 방식 (grep/AST/LSP/모델) | 위치 | 비고 |
|---|---|---|---|---|---|
| (모델이 호출하는 도구) | 없음 | 없음 | 해당 없음 | `litellm_ai_handler.py:2987-2991` | 미지원. 찾아본 곳: 핸들러 3종, 서버·도구·알고리즘 전체 grep |
| 프로그램의 저장소 파일 읽기 | `get_repo_file_content(file_path, from_default_branch)` | 파일 문자열 | provider API (경로 지정 읽기) | `git_provider.py:884`, `github_provider.py:1626-1649` | **모델이 부르지 못함.** `repo_context_files`에 적힌 경로만 읽음(`repo_context.py:337`) |
| 프로그램의 형제 저장소 읽기 | `get_sibling_repo_file_content(repo_id, path)` | 파일 문자열 | provider API | `git_provider.py:895`, `github_provider.py:1677-1697`, `repo_context.py:309-311` | 호스트가 허용한 저장소만(`repo_context_sibling_repos`), 최대 5개(상한 20) |
| 심볼·참조 검색 | - | - | AST, LSP, ctags, 임베딩 | - | 미지원. grep: `ast`(Bitbucket 웹훅 1건), `tree_sitter`, `libcst`, `jedi`, `lsp` 없음 |
| 코드 검색 | - | - | grep/ripgrep/glob | - | 미지원. `pr_agent/**/*.py`의 `os.walk`는 `skills_loader.py:111,220`과 `/help_docs`뿐 |
| 명령 실행 | - | - | shell | - | 미지원(리뷰 경로). `subprocess`는 clone 계열뿐 |
| MCP | - | - | - | - | 미지원 (grep 0건) |

기능 지원 수준: **동적 탐색 = 미지원**. **고정 문맥 확장 = 지원**(주변 줄, 지침 파일, 티켓, 아티팩트, 이전 finding).

### 3.3 "변경하지 않은 호출부를 찾는" 실행 예 (정적 추적)

[01 문서 3.8절](01-execution-and-diff.md)의 `apply_discount` 예를 재사용한다.
1. 입력에 포함되는 줄은 hunk와 앞 5줄/뒤 1줄이다(4~13행). 호출부 `checkout()` 16행은 같은 파일이어도 hunk에서 7줄 떨어져 있어 들어오지 않는다.
2. 모델이 "`checkout`에서 `apply_discount`를 어떻게 쓰는지 보여 달라"고 요청할 수단이 없다. 응답 형식은 YAML 한 번뿐이다(`pr_reviewer.py:1226-1231`).
3. 시스템 프롬프트는 오히려 추측을 막는다: "Do not speculate that a change might break other code unless you can identify the specific affected code path from the diff context." (`pr_reviewer_prompts.toml:24`) / "관련 코드가 diff 문맥에서 식별되지 않으면 다른 코드가 깨질 것이라고 추측하지 말라."
4. 결과: 호출부가 hunk 근처에 있을 때만 우연히 탐지 가능. 다른 파일의 호출부나 인터페이스 구현체는 탐지 불가(추론: 코드 경로와 프롬프트에서 도출, 모델 출력은 실행하지 않음).

### 3.4 파일 그룹별 리뷰에서 파일 간 결함을 놓칠 가능성

| 사실 | 위치 | 검증 |
|---|---|---|
| 청크는 **독립 호출**이다. 같은 프롬프트에 diff만 다른 묶음을 넣고 `asyncio.gather`로 병렬 실행하며 서로의 입력·출력을 보지 못한다 | `pr_reviewer.py:1042-1048` | 코드 확인 |
| 묶음은 파일 단위로 토큰을 채워 만든다. 같은 모듈의 두 파일이 다른 묶음으로 갈라질 수 있다 | `pr_processing.py:423-552` | 코드 확인 |
| 병합은 key issue를 `(파일, 헤더, 내용)` 정규화 문자열이 같을 때만 중복 제거한다. 표현이 다른 같은 결함은 중복으로 남는다 | `review_merge.py:181-199,326` | 코드 확인 |
| 티켓 준수 여부도 청크별로 판정 후 합치므로 "한 청크는 충족, 다른 청크는 미충족"이면 둘 다에 올라가 **부분 준수**로 렌더링된다. 파일 간 종합 판단이 아니다 | `review_merge.py:258-281` | 코드 확인 |
| 결과 수 상한 `num_max_findings=3`은 프롬프트 지시일 뿐 코드 강제가 없다(병합은 합집합) | `pr_reviewer_prompts.toml:142`, `configuration.toml:198` | 코드 확인 |
| 청크 분할은 기본 꺼져 있다(`enable_large_pr_chunking=false`). 꺼져 있으면 예산 초과분은 **잘려 나가고** 푸터에 "Review coverage"로 표시된다 | `configuration.toml:212`, `pr_reviewer.py:1360-1376` | 코드 확인 |

---

<a id="q4"></a>
## Q4. Agent Loop

### 4.1 반복의 단위 구분

| 구분 | 이 레포에서 해당하는 것 | 위치 | 검증 |
|---|---|---|---|
| **Agent Loop** (모델이 도구 호출 → 결과를 대화에 넣어 재추론) | **없음** | 3.1절 근거 | 코드 확인(부재) |
| 재시도/fallback | 같은 모델 재시도(tenacity 2회), 모델 체인 순차 교체(`config.model` → `fallback_models`), 타임아웃 시 같은 모델 재시도 여부 설정, `/improve` 실패 청크만 뒤 모델로 복구 | `litellm_ai_handler.py:149,285-299,2797-2801`, `pr_processing.py:830-872`, `pr_code_suggestions.py:1951-2085` | 코드 확인 |
| 다중 호출 (같은 프롬프트, 다른 입력) | `/review` 청크(옵션), `/improve` 청크(기본), `/describe` 다중 patch | `pr_reviewer.py:981-1077`, `pr_code_suggestions.py:2086-2223`, `pr_processing.py:384-420` | 코드 확인 |
| 다단계 파이프라인 (단계마다 다른 프롬프트, 고정 순서) | `/improve`: 생성 → self-reflect(점수). `/review`: 단계 없음(단일 프롬프트 + 코드 후처리) | `pr_code_suggestions.py:1062-1081` | 코드 확인 |

### 4.2 상태·입력·종료 조건 표

| 단계 | 반복 단위 | 입력(상태) | 모델 선택 | 프로그램 고정 | 종료 조건 | 위치 |
|---|---|---|---|---|---|---|
| `/review` 단일 호출 | 호출 1회 | `self.vars`(PR 메타, 티켓, 지침, 이전 finding) + 확장/압축된 diff | 응답 텍스트(YAML)의 내용만 | 입력 구성 전부, 호출 시점, 모델, 온도(`temperature=0.2`) | 응답 수신 → YAML 파싱 성공이면 후처리, 예산 초과·빈 review면 `FallbackEligibleError` | `pr_reviewer.py:1188-1223,1279-1284` |
| 모델 fallback | 모델 1개씩 순차 | 동일 입력 | 없음 | 체인=`[model]+fallback_models`(소형 PR은 `model_routing`으로 첫 모델 교체 가능). 대상 예외는 `openai.APIError`, `asyncio.TimeoutError`, `FallbackEligibleError`뿐 | 첫 성공 시 종료, 마지막 모델도 실패하면 예외 | `pr_processing.py:830-872`, `model_routing.py:35-84` |
| 같은 모델 재시도 | 호출 1회씩, 최대 2회 | 동일 입력 | 없음 | RateLimit/BadRequest/Unprocessable은 재시도하지 않음. 타임아웃·길이 초과 빈 응답은 설정 | 2회 소진 시 예외 전파 | `litellm_ai_handler.py:149,285-299,2797-2801` |
| `/review` 청크(옵션) | 파일 묶음 ≤3 | 묶음별 diff + 같은 vars | 없음 | 묶음 분할(`pr_processing.py:423-552`), 병렬 실행, 실패 청크만 다음 모델로 재시도(성공 청크 캐시) | 모든 청크 성공 또는 모델 소진 시 **성공한 청크만 병합**하고 실패 수를 푸터에 표기 | `pr_reviewer.py:981-1077,1155-1177,360-366` |
| `/improve` 청크 | 파일 묶음 ≤3 | 묶음별 diff(번호 포함/제외 2벌) | 없음 | 병렬(`parallel_calls=true`), 실패 청크 복구 | 청크 전부 실패하면 첫 예외 전파, 일부 성공이면 성공분 사용 | `pr_code_suggestions.py:1904-1920,2086-2223` |
| `/improve` self-reflect | 제안 전체 1회 | diff + 제안 목록 | 제안별 점수와 라인 범위 | 반성 모델 체인(`model_reasoning` 지정 시 그 모델), 빈 응답이면 다음 모델 | 응답 파싱 후 점수 적용. 전부 실패하면 모든 제안에 `score_on_reflection_failure=7` | `pr_code_suggestions.py:1083-1116,2432-2503`, `configuration.toml:271` |
| **Agent Loop** | - | - | - | - | **없음** | - |

### 4.3 종료 조건 점검 (GUIDE 8절 체크 항목)

| 종료 조건 | 이 레포 | 근거 | 검증 |
|---|---|---|---|
| 정상 종료 | 파싱 성공 → 후처리 → 게시. 게시 생략 조건(변경 없는 "No major issues")도 있음 | `pr_reviewer.py:370-391` | 코드 확인 |
| 도구 호출 없음으로 종료 | 해당 없음(도구 호출 개념이 없음) | 3.1절 | 코드 확인 |
| 최대 반복 | Agent Loop 반복은 없음. 고정 상한은 있음: 청크 수 `max_number_of_calls=3`, 같은 모델 재시도 2회, 모델 체인 길이 | `configuration.toml:213,282`, `litellm_ai_handler.py:149` | 코드 확인 |
| 토큰 한도 | 사전 예산 계산 후 초과면 압축/청크/`FallbackEligibleError`. 입력은 `max_model_tokens=32000`으로 상한. 출력 길이 초과 빈 응답은 별도 예외(`EmptyTruncatedResponseError`) | `pr_processing.py:206-381`, `token_budget.py:81-96`, `litellm_ai_handler.py:285-299,3394` | 코드 확인 |
| 시간 한도 | 호출당 `ai_timeout=120`초. 타임아웃은 같은 모델 재시도(설정) 후 fallback. 리뷰 전체에 대한 별도 제한 시간은 찾지 못함 | `configuration.toml:32-34`, `litellm_ai_handler.py:2989-2990` | 코드 확인, 전체 제한 부재는 미확인(검색 범위: `pr_reviewer.py`, `pr_agent.py`, 서버) |
| 취소 | 명시적 취소 API 없음. `CancelledError`는 `finally`에서 진행 댓글 삭제만 한다(`/improve`는 "cancelled" 문구로 편집 후 삭제) | `pr_reviewer.py:499-505`, `pr_code_suggestions.py:550-564` | 코드 확인 |
| 모델 오류 | fallback 체인 → 소진 시 `Failed to generate prediction with any model` → 실패 사유 댓글 | `pr_processing.py:862-866`, `pr_reviewer.py:154-171,490-525` | 코드 확인 |
| "충분히 조사했다"는 판단 | 해당 없음 | - | 코드 확인 |

### 4.4 최초 모델 입력 재구성 (`/review`)

| 메시지 | 들어가는 것 | 순서 | 위치 |
|---|---|---|---|
| system | (스킬) → 역할/기준 지침 → 사용자 `extra_instructions` → (아티팩트 지침) → `Repository context` → 출력 스키마(Pydantic 정의 + YAML 예) | 이 순서 | `pr_reviewer_prompts.toml:1-62` 이후 |
| user | (CI 아티팩트) → 티켓 → PR 정보(날짜, 제목, 브랜치, 설명) → (Q&A) → 이전 finding → `The PR code diff` | 이 순서 | `pr_reviewer_prompts.toml:243-345` |

- **모델이 선택하는 것**: 무엇을 finding으로 올릴지, 심각도·점수, 티켓 요구사항의 충족 판정 (모두 출력 내용).
- **프로그램이 고정하는 것**: 입력 구성, 호출 횟수, 모델 체인, 출력 스키마, 게시 위치.
- 시스템 프롬프트의 핵심 지침(원문 + 번역):
  - "The review should focus on new code added in the PR code diff (lines starting with '+'), and only on issues introduced by this PR." (`pr_reviewer_prompts.toml:10`) / "리뷰는 PR diff에서 추가된 코드('+' 줄)에 집중하고, 이 PR이 도입한 문제만 다룬다."
  - "Note that you only see changed code segments (diff hunks in a PR), not the entire codebase." (`:17`) / "너는 전체 코드베이스가 아니라 변경된 코드 조각(diff hunk)만 본다."
  - 티켓 판정 필드 설명은 `pr_reviewer_prompts.toml:83-92`에 있다(상세는 [03 Q9](03-incremental-memory-rules.md#q9)).

---

<a id="q5"></a>
## Q5. 검증 (finding 필터링)

### 5.1 검증 단계 표

| 단계 | 입력 | 출력 | 모델·문맥 독립성 | 추가 파일 접근 | 위치 |
|---|---|---|---|---|---|
| `/review` 구조화 출력 검사 | 모델 YAML | `PRReview` pydantic 검증 결과. **실패해도 경고 로그만** 남고 진행. 하드 실패는 "review가 비어 있거나 매핑이 아님"뿐(`FallbackEligibleError`) | 모델 호출 없음 | 없음 | `pr_reviewer.py:1233-1284`, 청크 경로 `:1066`(반환값 무시) |
| `/review` YAML 복구 | 깨진 YAML | `load_yaml`이 키 기준 휴리스틱으로 복구 | 모델 호출 없음 | 없음 | `pr_reviewer.py:1226-1231`, `algo/utils.py:987` |
| `/review` 별도 결함 검증 | - | - | - | - | **없음.** 생성 모델의 finding을 다른 호출로 재검토하는 코드가 없다 (`pr_reviewer.py` 전체, `tools/` 목록 확인) |
| `/review` 위치 유효성(인라인 모드) | finding의 파일·줄 | 파일이 diff에 있고 `end_line ≤ head_file 줄 수`이면 인라인 후보, 아니면 요약에 유지 | 모델 호출 없음 | head 본문(이미 수집됨) | `pr_reviewer.py:1438-1472` |
| `/review` 중복·재제시 | 이전 finding 마커 | 같은 문구 재제시를 프롬프트로 요구, fingerprint로 동일 finding 판정 | 같은 호출 | 없음 | `pr_reviewer_prompts.toml:323-333`, `review_finding_state.py:48-92` |
| `/improve` self-reflect | 제안 목록 + **같은 diff** | 제안별 `suggestion_score`(0~10), `why`, 라인 범위 | **별도 LLM 호출**. `model_reasoning`을 지정하면 다른 모델, 아니면 같은 모델 체인. 생성 호출의 대화 기록은 공유하지 않지만 입력 diff는 같다 | **없음** (diff와 제안 문자열만) | `pr_code_suggestions.py:1062-1081,1083-1116,2432-2503` |
| `/improve` 점수 필터 | 점수 | `suggestions_score_threshold` 미만 제거(코드상 최소 1) | 호출 없음 | 없음 | `pr_code_suggestions.py:87-137` |
| `/improve` 적용 가능성 검증 | 제안의 `existing_code`, 줄 범위 | 앵커 범위의 실제 줄과 비교(들여쓰기·공백 정규화) | 호출 없음 | head 본문(수집 완료본) | `pr_code_suggestions.py:1631-1667` |
| `/improve` Python 문법 검사 | 대체 코드 | 대체 후 파일이 `compile()`되는지 확인. 원본이 이미 깨져 있으면 건너뜀 | 호출 없음 | head 본문 | `pr_code_suggestions.py:1566-1605` |
| 평가 스크립트(evals) | - | - | - | - | **실제 리뷰 경로와 연결된 평가 없음.** `tests/health_test/main.py`는 명령이 마크다운 헤더를 내는지 보는 스모크 테스트이고, `settings/pr_evaluate_prompt_response.toml`은 `config_loader.py`의 `settings_files`에 없으며 테스트(`test_output_models.py:376`)만 참조한다 |

### 5.2 판정

- **구조화 출력 검증과 의미적 결함 검증은 다르다.** `/review`에는 구조 검사(경고 수준)만 있고 **의미 검증이 없다**.
- `/improve`의 자기 반성은 **생성과 같은 diff만 보고 점수를 매기는 2차 평가**다. 검증자는 호출부나 다른 파일을 읽을 수 없다(추가 파일 접근 = 없음). 프롬프트가 "surrounding PR code context"를 보라고 하지만(`pr_code_suggestions_reflect_prompts.toml:24`) 그 문맥은 입력 diff 안으로 한정된다.
- 오탐 필터링은 주로 **프롬프트 지시**("be certain before flagging", `pr_reviewer_prompts.toml:20-26`)와 `/improve`의 점수 임계값이다. 생성 단계와 독립된 근거 재탐색은 없다.
- 반성 실패 시 제안은 "검증 안 됨" 표시 없이 기본 점수 7로 통과한다(`apply_reflection_failure_score`, `pr_code_suggestions.py:98-112`). 임계값보다 낮게 설정해야 걸러진다(`configuration.toml:271`).
- 결과 중복 제거: 파일 묶음 간은 `review_merge`의 정규화 동일 문자열(`review_merge.py:181-199,326`), 재실행 간은 finding fingerprint(`review_finding_state.py:66`)와 인라인 댓글 fingerprint(`inline_comment_dedup.py:1-35`, 기본 꺼짐 `persistent_inline_comments=false`, `configuration.toml:76`).

기능 지원 수준: **별도 결함 검증 = 미지원**(`/review`), **부분 지원**(`/improve`: 동일 diff 기반 자기 반성 + 기계적 적용 가능성 검사). **추가 근거 탐색 검증 = 미지원.**

---

## README·문서와 코드가 다른 곳

| 문서 서술 | 코드 | 위치 | 검증 |
|---|---|---|---|
| "Supported Git Platforms: GitHub, GitLab, Bitbucket, Azure DevOps, Gitea" 로 모든 core ability 표기 | 일부 기능은 provider 성격에 따라 갈림: finding 상태는 GitHub/GitLab/Azure(+식별 설정)만, 이슈 인덱싱은 GitHub만 | `github_provider.py:632-640`, `gitlab_provider.py:1282`, `azuredevops_provider.py:1221-1222`, `git_provider.py:446-457` | 코드 확인 |
| `fetching_ticket_context.md`: 가져오는 티켓 데이터에 "Subtasks", "Attached Images/Screenshots" 포함 | Jira 경로는 제목·설명·요구사항 필드·라벨만. GitHub 하위 이슈는 있음. `image`/`attachment` 처리 코드 없음(해당 파일 grep) | `fetching_ticket_context.md:22-28` vs `ticket_pr_compliance_check.py:311-337` | 코드 확인 |
| `pr_compliance_checklist.yaml`이 저장소 루트에 있음 | 코드·문서 어디에서도 이 파일을 읽지 않는다(`grep -rn pr_compliance_checklist` → 파일 자신뿐) | `pr_compliance_checklist.yaml` | 코드 확인(참조 부재), 용도는 미확인 |
