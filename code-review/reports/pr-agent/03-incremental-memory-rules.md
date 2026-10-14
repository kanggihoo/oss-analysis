# pr-agent — 증분 리뷰, 메모리, 팀 규칙, Jira

- 분석 SHA: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q6, Q7, Q8, Q9
- 검증 수준 요약: 코드 확인 73 / 실행 확인 0 / 추론 4 / 미확인 0 (대략 집계: 머리 줄을 뺀 본문에서 각 표기 문자열이 나온 횟수이며, 표 행 수가 아니고 설명 문장 속 언급도 포함. 실행 확인 0은 실제로 실행한 항목이 없다는 뜻이고 본문의 "실행 확인" 문구는 실행하지 않았다는 서술. 2026-10-13 재집계)
- 실행 여부: 정적 추적만. 웹훅·API·모델을 실행하지 않았다.

---

<a id="q6"></a>
## Q6. 증분 리뷰

### 6.1 새 커밋 이후의 비교 기준

| 항목 | 동작 | 위치 | 검증 |
|---|---|---|---|
| 트리거 | `/review -i`(첫 인자 `-i`)가 증분. **기본 push 트리거는 꺼져 있고**(`handle_push_trigger=false`), 켜도 기본 `push_commands`는 `/describe`, `/review`로 **전체 리뷰**다(증분이 아님) | `pr_reviewer.py:286-293`, `configuration.toml:360-368,393-397` | 코드 확인 |
| GitHub 기준점 | 이전 **리뷰 댓글의 `created_at`**. 그 이후에 만들어진 커밋(committer date 우선)이 새 커밋. 기준 이전의 마지막 커밋이 `last_seen_commit` | `github_provider.py:290-335,337-346` | 코드 확인 |
| GitLab 기준점 | 이전 리뷰 노트의 `anchor_time`과 커밋 `author.date` 비교. 그 뒤 `repository_compare(last_seen_sha, head_sha)`로 파일을 얻고, **MR 전체 diff의 경로와 교집합**을 취해 타깃 브랜치 머지로 딸려 온 파일을 제외 | `gitlab_provider.py:744-897,899-921` | 코드 확인 |
| 증분 diff 생성 | 증분 모드에서는 `last_seen_commit` 본문과 head 본문을 `difflib`로 비교(GitHub), compare 결과의 diff 사용(GitLab) | `github_provider.py:508-513`, `gitlab_provider.py:1122-1136` | 코드 확인 |
| 앵커가 없을 때 | "이전 리뷰 없음", "모든 커밋이 리뷰 이후" 등이면 **전체 리뷰로 폴백** | `github_provider.py:294-316`, `gitlab_provider.py:778-783,795-800,811-819`, `pr_reviewer.py:314-321,1626-1635` | 코드 확인 |
| 새 파일 없음 | "Incremental Review Skipped" 댓글을 게시하고 종료 | `pr_reviewer.py:337-349` | 코드 확인 |
| 임계값 | `minimal_commits_for_incremental_review=0`, `minimal_minutes_for_incremental_review=0`(기본은 항상 통과) | `pr_reviewer.py:1637-1665`, `configuration.toml:204-206` | 코드 확인 |

- 비교 기준은 **"마지막으로 리뷰한 SHA"가 아니라 "이전 리뷰 댓글의 게시 시각 이후의 커밋"**이다. 시각 비교이므로 리베이스·커밋 날짜 조작에 취약하다는 점은 주석에서도 인식하고 있다(`github_provider.py:318-323`, committer date 사용). 이 해석 위험은 추론이다.
- 별도로, 전체 리뷰의 finding 상태에는 `last_run.head_sha`가 기록된다(`review_finding_state.py:278-288`). 이 SHA는 증분 diff 기준이 아니라 "이전 head와 달라졌을 때만 finding을 resolved로 전환"하는 용도다(`:225-232`).

### 6.2 중복 방지

| 장치 | 범위 | 기본값 | 위치 | 검증 |
|---|---|---|---|---|
| PR 최초 생성 시 `synchronize` 무시 | `created_at == updated_at`이면 "처음 열린 PR의 이중 리뷰" 방지 | 항상 | `github_app.py:470-473` | 코드 확인 |
| PR별 push 슬롯 | PR 키로 동시 실행 1개(+백로그 1개)만 허용, 초과 이벤트는 버림. **프로세스 내 메모리** | GitHub `push_trigger_pending_tasks_backlog=true`, TTL 300초. GitLab은 `allow_backlog=True, ttl=300` | `servers/utils.py:198-258`, `github_app.py:320-329`, `gitlab_webhook.py:362,384` | 코드 확인 |
| 웹훅 delivery ID 중복 제거 | `X-GitHub-Delivery` 기준, 완료된 ID를 TTL 동안 기억. **워커·레플리카 간 공유 안 됨** | `webhook_delivery_deduplication=false` | `github_app.py:49-54,427-456`, `configuration.toml:354-358` | 코드 확인 |
| 같은 PR의 댓글 중복 | persistent comment를 찾아 **편집**(없을 때만 새로 작성) | `persistent_comment=true` | `git_provider.py:1066-1131`, `configuration.toml:187` | 코드 확인 |
| 인라인 댓글 중복 | 본문/코드 fingerprint를 HTML 주석 마커로 심고 기존 댓글에서 복원해 스킵 | `persistent_inline_comments=false`(`/review` 인라인 key issue는 별도 위치 마커를 항상 사용) | `inline_comment_dedup.py:1-35`, `pr_reviewer.py:1489-1583` | 코드 확인 |
| 작업 재시도 | 웹훅 실패는 로그만 남기고 재시도·dead-letter 없음. 실패한 delivery는 중복 제거 캐시에 기록되지 않아 재전송 시 다시 실행됨 | - | `github_app.py:453-455`, `github_app.py:535-538` | 코드 확인 |

### 6.3 실행 중 Head SHA 변경

| 구간 | 처리 | 위치 | 검증 |
|---|---|---|---|
| 파일 수집 중 | GitHub/GitLab 모두 수집 전후 메타(`head/base/changed_files`, `sha/diff_refs/changes_count`)를 비교해 어긋나면 오류. GitHub는 1회 재시도 | `github_provider.py:359-401`, `gitlab_provider.py:608-640` | 코드 확인 |
| 증분 준비 중(GitLab) | MR diff refs가 증분 설정 시점과 다르면 전체 실행으로 폴백 | `gitlab_provider.py:857-864` | 코드 확인 |
| LLM 호출 중/게시 직전 | head를 다시 확인해 결과를 폐기하는 코드 없음. 오래된 SHA 기준 결과가 그대로 게시된다 | `pr_reviewer.py:295-530` 전체 확인 | 코드 확인(부재) |
| 직렬화 | 같은 PR의 push 트리거는 한 번에 하나씩 실행(대기 최대 1개). 실행 중인 리뷰를 **취소하지는 않는다** | `servers/utils.py:223-258` | 코드 확인 |

기능 지원 수준: 증분 리뷰 = **지원**(시각 기반). 오래된 결과 취소·폐기 = **미지원**(찾아본 곳: `pr_reviewer.py`, `pr_agent.py`, `servers/*`, provider 게시 함수).

### 6.4 이전 코멘트의 유지 / 수정 / 해결

| 동작 | 구현 | 위치 | 검증 |
|---|---|---|---|
| 유지 / 수정 | 전체 리뷰는 같은 persistent comment를 편집하고 `(Review updated until commit …)`를 넣는다. 증분 리뷰는 **별도 새 댓글**(증분 identity 마커) | `git_provider.py:1096-1100`, `pr_reviewer.py:435,481-489` | 코드 확인 |
| 작성자 확인 | 숨은 마커가 있어도 PR-Agent가 쓴 댓글만 편집 대상. 신원 확인이 안 되면 덮어쓰지 않고 별도 게시 | `pr_reviewer.py:445-479`, `git_provider.py:1044-1064` | 코드 확인 |
| finding 해결 표시 | 완전한 전체 리뷰에서 **이전 ACTIVE finding이 이번에 다시 나오지 않으면 RESOLVED**로 바꾼다(조건은 7.3절) | `review_finding_state.py:262-275`, `pr_reviewer.py:849-861` | 코드 확인 |
| 인라인 스레드 해결(GitLab) | 옵트인: ① head가 바뀌어 낡은 diff 버전에 달린 자기 스레드 resolve, ② 지적한 줄이 이후 커밋에서 수정/삭제된 자기 스레드 resolve(내용 기반) | `gitlab_provider.py:1427-1465,1495-1557`, `configuration.toml:385-392` | 코드 확인 |
| 스레드 해결(GitHub) | 자기 스레드를 코드 변경에 따라 자동 resolve하는 코드는 이 SHA에서 찾지 못함. `resolve_comment_thread` 호출처는 `/improve` 진행 댓글과 `/ask` 라인 질문뿐 | `pr_code_suggestions.py:673-692`, `pr_line_questions.py:122` | 코드 확인(부재는 grep) |

---

<a id="q7"></a>
## Q7. 장기 메모리

### 7.1 층위 구분

| 층위 | 이 레포 | 근거 | 검증 |
|---|---|---|---|
| 실행 대화 | 없음. 매 호출은 `[system, user]` 2메시지의 무상태 요청 | `litellm_ai_handler.py:2863-2868` | 코드 확인 |
| 실행 체크포인트 | 한 번의 실행 안에서만: 성공한 청크 결과를 `_chunked_results`에 캐시했다가 fallback 모델이 실패 청크만 재시도. 프로세스 밖으로 저장되지 않음 | `pr_reviewer.py:1023-1068,1155-1177` | 코드 확인 |
| **같은 PR 이력** | **있음.** ① 리뷰 댓글에 숨겨 저장한 finding 상태, ② `/improve` 이전 제안 스레드 읽기(GitLab·Azure), ③ 사람이 resolve한 스레드를 "dismissed"로 읽기, ④ 인라인 댓글 fingerprint 마커 | 7.2~7.4절 | 코드 확인 |
| **PR 간 영속 메모리** | **없음.** 쓰기·읽기 어느 쪽도 다른 PR로 이어지는 저장소가 없다 | 7.5절 | 코드 확인(부재) |

### 7.2 같은 PR: finding 상태 (쓰기 → 저장 → 읽기)

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 쓰기 트리거 | **전체 리뷰 실행이 끝날 때마다**(증분 제외). 댓글 답변·승인·수정 이벤트를 저장하는 코드는 없음 | `pr_reviewer.py:532-556,803-871`, `:548-549`(증분은 제외) | 코드 확인 |
| 저장소 | 별도 저장소 없음. **리뷰 댓글 본문 끝에 숨은 HTML 주석** `<!-- pr-agent-review-state:v1 {json} -->` | `review_finding_state.py:15-21,168-177,381-421` | 코드 확인 |
| 스키마 | `findings[]`: `finding_id`(`sha256("경로|공백 정규화·소문자 본문")`의 앞 12자리. **줄 번호는 포함되지 않아** 줄이 이동해도 같은 finding으로 본다. 본문에는 헤더가 포함되므로 헤더·문구가 바뀌면 새 finding. `inline_comment_dedup.py:114-117`, `review_finding_state.py:66`), `state`(ACTIVE/RESOLVED), `body`, `path`, `line_start/end`, `first_seen`, `last_seen`, `reopened_at/count`, `resolved_at`, `last_seen_head_sha`. `last_run`: `complete`, `excluded_files`, `head_sha`, `kind`, `run_id` | `review_finding_state.py:48-92,199-296` | 코드 확인 |
| 출처 | 댓글 안에만 있고 PR·댓글·SHA는 `last_run.head_sha`/`run_id`(커밋 URL)로 기록. 작성자는 PR-Agent 신원으로 검증 | `pr_reviewer.py:766-789`, `review_finding_state.py:278-288` | 코드 확인 |
| 적용 범위 | **그 PR 하나.** 다른 PR의 댓글을 조회하지 않음 | `pr_reviewer.py:647-679` | 코드 확인 |
| 읽기 | `PRReviewer.__init__`에서 `_load_previous_findings_context()` → 댓글 마커 파싱 → `render_previous_findings` → **최초 user 프롬프트에 JSON으로 주입** (호출 가능한 도구가 아님) | `pr_reviewer.py:224,681-694`, `review_finding_state.py:314-351`, `pr_reviewer_prompts.toml:323-333` | 코드 확인 |
| 검색 조건 | 없음(그 댓글의 전체 상태). 글자 수 예산(`max_previous_findings_chars=8000`)에 맞춰 ACTIVE → dismissed → RESOLVED 순, 최신 순으로 채움 | `review_finding_state.py:338-351` | 코드 확인 |
| 지원 provider | GitHub(user 배포 또는 앱 로그인 해석 가능), GitLab, Azure DevOps(고정 에이전트 신원 설정 시). 나머지는 기본 `False` | `github_provider.py:632-640`, `gitlab_provider.py:1282-1283`, `azuredevops_provider.py:1221-1222`, `git_provider.py:981-983` | 코드 확인 |

프롬프트 지시(원문 + 번역): "If the issue still exists in the current code, report it again with the same issue_header and issue_content, word for word, updating only start_line, end_line ..." (`pr_reviewer_prompts.toml:330`) / "이슈가 현재 코드에 아직 있으면 같은 `issue_header`, `issue_content`를 **글자 그대로** 다시 보고하고 줄 번호만 갱신하라." 즉 **이전 finding과의 동일성은 모델이 문구를 그대로 복사하는 것에 의존**한다(fingerprint가 정규화 본문 기준이므로, 표현이 달라지면 새 finding으로 취급됨).

### 7.3 수명 관리와 "동의/해결" 해석

| 질문 | 구현 | 위치 | 검증 |
|---|---|---|---|
| 언제 RESOLVED가 되나 | 이전 ACTIVE finding이 **이번 완전한 전체 리뷰에서 나오지 않았고**, 이전 head와 현재 head가 모두 알려져 있으며 서로 다를 때 | `review_finding_state.py:225-232,262-275` | 코드 확인 |
| 해결 금지 조건 | 증분 실행, 실패·누락 청크 있음, 토큰 예산 때문에 제외된 파일 있음, 파싱 불가한 이전 상태, 보고된 issue가 일부 버려짐, **현재 finding 수가 `num_max_findings` 이상**(포화) | `pr_reviewer.py:849-861` | 코드 확인 |
| 해석 위험 | 모델이 **단순히 이번에 안 적었다는 사실**을 "고쳐졌다"로 해석한다. 포화·부분 커버리지 조건은 이를 줄이는 보정이지만 모델 비결정성 자체는 남는다 | 위 두 행 | 추론(근거: 해결 판정이 코드 비교가 아니라 부재에 기반) |
| 재발 | RESOLVED finding이 다시 나오면 ACTIVE로 되돌리고 `reopened_count` 증가 | `review_finding_state.py:240-257` | 코드 확인 |
| 보존 상한 | RESOLVED는 최근 20개만 유지(ACTIVE는 유지) | `review_finding_state.py:16,180-196` | 코드 확인 |
| 신뢰도·승인·충돌 | 신뢰도/승인 상태/충돌 해결 필드 없음 | `review_finding_state.py:48-92` | 코드 확인(부재) |
| 상태 마커 손상 | 파싱 불가·크기 초과면 "state blocked"로 표시하고 상태를 건드리지 않거나 깨끗한 마커로 교체 | `pr_reviewer.py:397-433,647-679,1392-1422` | 코드 확인 |

### 7.4 사람의 resolve를 읽는 경로 ("dismissed")

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 읽기 | PR-Agent가 연 인라인 key issue 스레드 중 **사람이 resolve한 것**을 가져온다. 마지막 텍스트 답글(750자 이내)을 `reply`로 함께 주입 | `pr_reviewer.py:696-717`, `github_provider.py:1096-1141` | 코드 확인 |
| 프롬프트 의미 | `"dismissed": a reviewer closed its thread without fixing it (won't fix, by design)` → 같은 지적을 다시 올리지 말 것 | `pr_reviewer_prompts.toml:332` | 코드 확인 |
| 해석 위험 | 코드는 스레드가 `resolved`이고 resolve한 사람이 에이전트가 아니라는 조건만 본다. **코드가 실제로 수정되었는지는 구분하지 않는다.** 수정 후 resolve한 경우에도 "수정 없이 닫음"으로 전달될 수 있다 | `github_provider.py:1096-1105` | 추론(코드에 수정 여부 확인 로직이 없다는 사실에서 도출) |
| 쓰기 | 이 상태는 별도로 저장되지 않는다. 매 실행마다 provider에서 다시 조회한다 | `pr_reviewer.py:696-717` | 코드 확인 |

### 7.5 PR 간 메모리: 없는 범위와 근거

- **찾아본 곳**: `pr_agent/**/*.py`에서 `sqlite|redis|postgres|mongo|dynamodb|firestore|sqlalchemy|celery|kafka` 검색 → 큐·DB 관련 실사용 0건(LiteLLM 로거 이름과 메모리 내 `deque`만 검출). 파일 쓰기는 `push_outputs`의 `FileSink`(append)와 `--json-output`뿐이다.
- `push_outputs`(`output_sinks.py:52-62`, `configuration.toml:626-632`)는 **쓰기 전용**이다. 리뷰 결과를 JSONL/웹훅/Slack으로 내보내지만 다음 실행에서 읽는 코드가 없다.
- `/improve`의 이전 제안 스레드 읽기(`git_provider.py:382-413`)도 **같은 PR**의 스레드만 본다(GitLab·Azure).
- 따라서 "피드백을 다음 PR에 활용하는 학습"은 **미지원**이다. 쓰기만 있고 조회가 없는 저장(`push_outputs`)과 PR 안으로 한정된 상태는 "피드백 학습"이라 부르지 않는다.

### 7.6 `similar-issue`는 팀 메모리가 아니다

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 데이터 원천 | **GitHub 저장소의 이슈와 댓글** (`supports_issue_indexing`은 GitHub만 True) | `pr_similar_issue.py:164-197`, `git_provider.py:446-457` | 코드 확인 |
| 인덱싱 | `text-embedding-ada-002` 임베딩(OpenAI 키 사용) → 벡터 DB(lancedb 기본, pinecone, qdrant). 저장소별 네임스페이스/필터 | `pr_similar_issue.py:16-35,59-92,275-405`, `configuration.toml:557-577` | 코드 확인 |
| 검색 | 대상 이슈 텍스트 임베딩 → 상위 유사 이슈 목록을 댓글로 | `pr_similar_issue.py:419-447` 이후 | 코드 확인(앞부분만 열람) |
| 입력 단위 | PR이 아니라 **이슈 URL** (`--issue_url ... similar_issue`) | `cli.py:138,234-235` | 코드 확인 |
| 의존성 | 의존성 그룹 `similar-issue` (기본 설치·Docker 이미지에 미포함) | `pyproject.toml:139-147`, `docker/Dockerfile:18` | 코드 확인 |

기능 지원 수준: 같은 PR 상태 = **지원**(finding 상태, dismissed, 이전 제안 스레드). **PR 간 장기 메모리 = 미지원.** 쓰기→읽기 양쪽을 추적했고 두 번째 층위는 없다.

---

<a id="q8"></a>
## Q8. 팀 규칙

### 8.1 범위 계층과 소유자

| 범위 | 메커니즘 | 소유자 | 위치 | 검증 |
|---|---|---|---|---|
| 전역(호스트) | `configuration.toml` 기본값, 환경변수(최상위 우선), `.secrets.toml`, AWS Secrets Manager 병합 | 서비스 운영자 | `config_loader.py:25-55`, `git_providers/utils.py:162-180`, `config_loader.py:103-159` | 코드 확인 |
| 추가 외부 설정 | `extra_config_url`(URL 또는 경로)를 저장소 설정보다 **먼저** 병합 | 운영자/조직 | `configuration.toml:29`, `utils.py:59-150,267-286` | 코드 확인 |
| 조직/네임스페이스 | `global_settings_repo`(예: `pr-agent-settings`)의 `.pr_agent.toml`이 같은 org/group의 모든 저장소에 적용. 기본은 비활성(빈 문자열) | 조직 관리자 | `configuration.toml:25`, `git_provider.py:850-882` | 코드 확인 |
| 저장소 | 기본 브랜치의 `.pr_agent.toml` (`use_repo_settings_file=true`) | 저장소 팀 | `git_providers/utils.py:289-348` | 코드 확인 |
| 경로별(모노레포) | 변경 파일의 상위 디렉터리를 따라 올라가며 찾은 `.pr_agent.toml`(옵트인, 최대 20개, 비핵심 섹션만, 가까운 디렉터리 우선) | 하위 디렉터리 팀 | `configuration.toml:26-28`, `git_providers/utils.py:382-545,596-710`, `config_security.py:225-246` | 코드 확인(상세 병합 규칙은 일부만 열람) |
| 명령별 | `[pr_reviewer].extra_instructions`, `[pr_code_suggestions].extra_instructions`, 명령줄/댓글 `--pr_reviewer.extra_instructions="..."` | 사용자 | `configuration.toml:197`, `pr_agent.py:398-410,273-298` | 코드 확인 |
| 지침 파일 | `repo_context_files`(기본 `AGENTS.md`, 기본 브랜치에서 읽음, 형제 저장소 파일은 호스트 허용 목록만), `SKILL.md`(호스트 파일시스템) | 저장소 / 운영자 | `repo_context.py:446-494`, `skills_loader.py:197-300` | 코드 확인 |
| 보안 경계 | 저장소 설정이 바꿀 수 없는 키: LLM·Git·Jira 연결 정보, `skills.paths`, `push_outputs`, `repo_context_sibling_repos` 등 | 운영자 | `config_security.py:1-60,225-246` | 코드 확인(앞부분만 열람) |

### 8.2 우선순위와 충돌

- 적용 순서(코드 확인): 기본값 → 환경변수 → `extra_config_url` → 조직 `global_settings_repo` → 저장소 `.pr_agent.toml` → 디렉터리별 → 명령 인자. 그리고 **환경변수는 파일 설정 뒤에 다시 적용해 최상위로 복원**한다(`utils.py:162-180`의 주석에 "env vars are the highest layer"). 명령 인자는 설정 적용 직후 `update_settings_from_args`로 다시 덮는다(`pr_agent.py:378-410`).
- 충돌은 키 단위 덮어쓰기다(섹션 단위로 병합하고 겹치는 값은 나중 것이 이긴다, 리스트/딕셔너리는 병합이 아니라 교체): `git_providers/utils.py:183-193,533-538`. **자연어 규칙끼리의 충돌 해결(의미 수준)은 없다.** `extra_instructions` 문자열이 계층마다 덮어써질 뿐이다.
- 생성·편집·승인·버전·비활성화: 전용 경로가 없다. 규칙은 **git에 커밋된 설정 파일**이며, 버전 관리는 그 파일의 git 이력이고 승인은 그 저장소의 PR 리뷰 프로세스다(추론: 별도 승인 코드를 찾지 못함). 비활성화는 `use_repo_settings_file=false` 같은 설정 키.
- 개발자 피드백에서 규칙을 **추출**하는 과정: 없음(트리거·검증 단계 코드 없음, 7.5절과 같은 범위 검색).

### 8.3 규칙을 읽고 모델에 넣는 방식

| 구분 | 읽는 위치 | 모델 입력 위치 | 위치 | 검증 |
|---|---|---|---|---|
| 커스텀 프롬프트 | 설정(`extra_instructions`) | system 메시지의 `Extra instructions from the user:` 블록 | `pr_reviewer.py:260`, `pr_reviewer_prompts.toml:34-41` | 코드 확인 |
| 규칙·지침 파일 | provider API로 설정 경로 파일 읽기 | system 메시지 `Repository context:` (`<instruction_files>` 래핑, 줄 수 예산) | `repo_context.py:376-443`, `pr_reviewer_prompts.toml:51-58` | 코드 확인 |
| 스킬 | 호스트 디렉터리의 `SKILL.md` (이름·설명·본문, 하위 `*.md` 인라인) | system 메시지 맨 앞 `Organizational standards and review skills` | `skills_loader.py:237-300`, `pr_reviewer_prompts.toml:2-8` | 코드 확인 |
| 저장·승인·버전 관리되는 팀 규칙 | - | - | - | 미지원 |
| 자동화된 정책 엔진 | - | - | - | 미지원 (정책 필터 `ignore_*`는 **리뷰 실행 여부**만 결정, `request_policy.py:8-48`) |

- 규칙의 **경로별 적용**(예: `src/payments/**`에서만 적용)은 모델이 파일명을 보고 알아서 적용하도록 프롬프트에 넣는 방식이다(스킬은 "the model decides which guidance applies based on the descriptions", `skills_loader.py:17-19`). 코드가 경로 매칭으로 규칙을 선별하지 않는다.
- 문서에 없는 파일: 저장소 루트의 `pr_compliance_checklist.yaml`(규칙 목록 형태)은 코드가 읽지 않는다(`02` 문서 하단 표).

기능 지원 수준: 커스텀 프롬프트/지침 파일 = **지원**, 저장·승인·버전 관리되는 규칙, 피드백에서의 규칙 추출 = **미지원**.

---

<a id="q9"></a>
## Q9. Jira / 요구사항

Jira 연동은 **있다.** 다만 "요구사항 텍스트를 입력에 넣고 모델이 diff만 보고 판정"하는 수준이다.

### 9.1 이슈 식별·인증·필드·삽입

| 항목 | 구현 | 위치 | 검증 |
|---|---|---|---|
| 이슈 식별 | PR **제목 + 설명 + 브랜치명**을 이어서 `[A-Z]{2,10}-\d{1,7}` 정규식(대소문자 무시)으로 키 추출, 첫 등장 순서 유지 | `ticket_pr_compliance_check.py:167-194,351-378` | 코드 확인 |
| 필터 | `jira.project_keys` 허용 목록(호스트 전용). 비어 있으면 모든 키 조회(`SHA-256` 같은 오탐도 조회 시도). 조회 시도 최대 10, 해석 성공 최대 5 | `:59-65,110-164,244-338` | 코드 확인 |
| 인증 | **Jira Cloud 전용.** `jira_site`로 `https://<site>.atlassian.net`을 조립(자유 URL 불가), email+API token. 모두 호스트 설정이며 저장소 `.pr_agent.toml`이 바꿀 수 없다 | `:90-107,197-241`, `config_security.py:53`(`"jira"` 호스트 전용 키), `configuration.toml:450-468` | 코드 확인 |
| 의존성 | `from atlassian import Jira`. 없으면 "Install pr-agent[bitbucket]" 경고 후 Jira 조회를 건너뜀 | `:227-235`, `pyproject.toml:96` | 코드 확인 |
| 추출 필드 | `summary`, `description`(REST v2 문자열), `labels`, 설정한 커스텀 필드(`jira_requirements_field`, 예: `customfield_10127`)를 `requirements`로. 각 1만 자 상한 | `:311-337`, `configuration.toml:461` | 코드 확인 |
| 하위 작업·첨부 | Jira 하위 작업·이미지는 가져오지 않음(문서는 가져온다고 서술, 02 문서 표 참조) | `:311-337` | 코드 확인(부재) |
| 삽입 위치 | `extract_and_cache_pr_tickets` → `vars["related_tickets"]` → user 메시지 `--PR Ticket Info--` 블록(제목, 라벨, 설명, 요구사항). 프롬프트 예산에 맞춰 **티켓 단위로 잘라낸다** | `pr_reviewer.py:334`, `ticket_pr_compliance_check.py:406-507,1188-1218`, `pr_reviewer_prompts.toml:253-288` | 코드 확인 |
| 대상 도구 | `/review`(`require_ticket_analysis_review=true`가 기본), `/describe` | `configuration.toml:177`, `ticket_pr_compliance_check.py:1189` | 코드 확인 |

### 9.2 텍스트 입력 vs 조건별 근거 판정

| 구분 | 이 레포 | 위치 | 검증 |
|---|---|---|---|
| 요구사항 텍스트를 입력에 넣기 | **지원** | 9.1 | 코드 확인 |
| 모델이 요구사항을 bullet로 풀어쓰고 충족/미충족/사람 확인 필요를 분류 | **지원.** 출력 `ticket_compliance_check[]`의 `ticket_requirements`, `fully_compliant_requirements`, `not_compliant_requirements`, `requires_further_human_verification` | `pr_reviewer_prompts.toml:83-113,161-165`, `output_models.py:34-40` | 코드 확인 |
| **조건별로 구현 근거를 찾아 판정** | **미지원.** 판정 근거는 입력 diff뿐이다. 요구사항별로 코드를 검색하거나 읽는 단계가 없다(02 문서 3.1·3.2: 탐색 수단 없음) | `pr_reviewer.py:367-370` 전후 흐름 | 코드 확인(부재) |
| 연결된 이슈 전체 vs **이번 PR 범위** 구분 | **미지원.** 프롬프트가 "모든 요구사항, 하위 작업, DoD, acceptance criteria를 다시 적어라"고 지시하고, PR 범위에 해당하는 것만 추리는 로직이나 지시가 없다 | `pr_reviewer_prompts.toml:87` | 코드 확인 |
| 청크 분할 시 | 청크별 판정을 합집합으로 합쳐 "한 청크는 충족, 다른 청크는 미충족"이면 **부분 준수**로 표시 | `review_merge.py:258-281` | 코드 확인 |

프롬프트 인용(`pr_reviewer_prompts.toml:87`): "Repeat, in your own words (in bullet points), all the requirements, sub-tasks, DoD, and acceptance criteria raised by the ticket" / "티켓이 제기한 모든 요구사항·하위 작업·완료 정의·인수 조건을 당신의 말로 bullet로 다시 적어라."

### 9.3 확장 지점 (Q12 의견과 연결)

| 목적 | 삽입 지점 | 근거 위치 |
|---|---|---|
| 요구사항 수집(수락 기준을 구조화) | `extract_jira_tickets()`의 반환 dict(`ticket_id`, `title`, `body`, `requirements`, `labels`)에 구조화된 `criteria` 리스트를 추가 | `ticket_pr_compliance_check.py:329-337` |
| 다른 이슈 시스템(Jira Server 등) | `extract_tickets()`의 provider별 분기 끝에서 `tickets_content`를 더하는 지점(`add_jira_tickets`와 동일 위치) | `ticket_pr_compliance_check.py:1075,1129,1168,1176` |
| **조건별 근거 탐색·검증** | 리뷰 응답 파싱 직후(`_prepare_prediction` 이후, `_prepare_pr_review` 이전)에 별도 단계 추가 | `pr_reviewer.py:360-370` |
| 이번 PR 범위 구분 | 위 검증 단계에서 diff로 영향받는 조건만 필터링 | 신규 설계 필요 (현재 코드 없음) |
