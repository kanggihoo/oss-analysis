# pr-agent — 우리 서비스 적용 (분석자 의견)

- 분석 SHA: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q12 (Q1~Q11의 결론을 종합)
- 검증 수준 요약: 코드 확인 2 / 실행 확인 0 / 추론 6 / 미확인 4 (대략 집계: 머리 줄을 뺀 본문에서 각 표기 문자열이 나온 횟수이며, 표 행 수가 아니고 설명 문장 속 언급도 포함. 실행 확인 0은 실제로 실행한 항목이 없다는 뜻이고 본문의 "실행 확인" 문구는 실행하지 않았다는 서술. 2026-10-13 재집계)
- 실행 여부: 정적 추적만.

> **이 문서의 모든 판단은 "의견"이다.** 코드 근거가 있는 사실은 `01`~`05` 문서에 있고, 여기서는 그 사실에서 도출한 설계 판단을 적는다. 근거 위치는 해당 문서 링크 또는 `경로:줄`로 붙였다. 서비스 목표는 GUIDE 0절의 "GitHub/GitLab PR 웹훅 → diff + 관련 기존 코드 + Jira 요구사항 + 팀 규칙 + 과거 피드백을 함께 리뷰하고, 동적 코드 탐색·검증·PR 간 메모리를 가진 서비스"다.

검증 수준 표기: 각 표의 "근거"는 모두 코드로 확인한 위치이고(코드 확인), 그 근거에서 도출한 "판단·권장"은 전부 의견이다. 코드에서 직접 확인하지 못한 동작(예: 핸들러가 PR 컨텍스트를 얻는 방법, 업스트림 변경 추적 부담)은 "추론" 또는 "미확인"으로 표시했다. 기능 지원 수준은 `00` 5절 표를 따른다.

---

## 1. 최종 질문에 대한 답 (의견)

**질문**: PR-Agent의 어떤 부분을 유지하면 플랫폼 연동과 Diff 처리를 절약할 수 있으며, 동적 탐색과 PR 간 메모리를 구현하려면 어떤 경계를 새로 설계해야 하는가?

- **유지하면 절약되는 부분**: (a) GitHub/GitLab provider 어댑터 — 변경 파일 수집, 완전성 검사, 본문 조회, 인라인 위치 변환, persistent comment·신원 마커, 스레드 조회(`git_providers/github_provider.py`, `gitlab_provider.py`); (b) diff 전처리 — `FilePatchInfo`, 주변 줄 확장, 토큰 예산 기반 압축·청크(`algo/git_patch_processing.py`, `algo/pr_processing.py`); (c) 같은 PR 안의 finding 상태 마커와 인라인 fingerprint 중복 제거(`algo/review_finding_state.py`, `algo/inline_comment_dedup.py`); (d) 웹훅 서명 검증과 이벤트 필터 로직(`servers/utils.py:91-106`, `request_policy.py`).
- **새로 설계할 경계**: (1) **저장소 접근 경계** — PR 고정 SHA(base/head/merge-base)로 파일을 읽고 검색하는 "워크스페이스"(현재 PR-Agent에는 임의 파일 조회가 없음); (2) **엔진 경계** — 모델이 도구를 호출하며 반복하고 종료 조건을 갖는 루프와 독립 검증자(현재는 단발 호출); (3) **메모리 경계** — 다른 PR로 이어지는 쓰기 이벤트와 조회 도구, 조직 범위 격리(현재는 PR 안으로 한정); (4) **요구사항 경계** — Jira 기준을 구조화하고 조건별 근거를 찾아 판정하는 단계(현재는 텍스트를 프롬프트에 넣는 수준); (5) **실행 경계** — 큐·재시도·취소·SHA 고정과 테넌트 스코프(현재는 프로세스 내 `BackgroundTasks`).
- PR-Agent의 "단발성"은 단점이 아니라 **설계 선택**이다(유지보수자가 코드 주석에서 "single-shot ... no tool-use loop"라고 밝힘, `configuration.toml:579-591`). 따라서 PR-Agent를 확장해 에이전트로 만드는 것보다 **provider·diff·게시 계층만 가져오고 엔진은 새로 두는 쪽**이 경계가 깨끗하다고 판단한다(의견).

---

## 2. 가져올 것 / 직접 만들 것 / 운영해야 할 의존성 (의견)

| 구분 | 항목 | 근거 | 비고 |
|---|---|---|---|
| **가져올 것** | GitHub·GitLab provider의 파일 수집·게시·스레드 조회 | `github_provider.py:359-401,443-588,939-1019,1056-1141`, `gitlab_provider.py:608-640,1103-1214,1784-1922` | 완전성 검사(PR 변경 중 수집), 대형 patch 복구, GitLab SHA·라인 매핑까지 이미 구현 (01 문서) |
| | `FilePatchInfo`와 diff 압축·청크 | `algo/types.py:14-31`, `pr_processing.py:206-381,907-1082` | 에이전트의 "초기 문맥"과 대형 PR 대비로 재사용 |
| | `extend_patch` 주변 줄 확장 | `git_patch_processing.py:33-234` | **초기 문맥 한정으로** 사용. 함수 경계는 AST가 아니라 휴리스틱임(01 문서 3.3절) |
| | finding 상태 마커(같은 PR) | `review_finding_state.py` 전체 | 순수 함수로 분리돼 있어 이식 쉬움. PR 간 메모리는 이 위에 새로 쌓음 |
| | 인라인 fingerprint 저장소 인터페이스 | `inline_comment_dedup.py:1-35,249-313` | 모듈 독스트링이 "다른 백엔드(DB, 캐시)가 같은 load/seen/add 인터페이스를 채울 수 있다"고 명시 |
| | 웹훅 서명 검증·이벤트 필터 | `servers/utils.py:91-106,344-`, `request_policy.py:28-48`, `github_app.py:364-376,459-474` | 로직은 가져오되 실행 모델은 교체 |
| | `register_git_provider`, `IdentityProvider`, 시크릿 제공자 같은 확장 지점 | `git_providers/__init__.py:120-132`, `identity_providers/__init__.py:4-13`, `secret_providers/__init__.py` | 내부 provider를 수정하지 않고 우리 provider를 꽂을 수 있음 |
| **직접 만들 것** | **저장소 워크스페이스**(고정 SHA 읽기·검색·참조 탐색) | PR-Agent에는 없음(02 문서 3.2절) | clone/미러, grep, 심볼 인덱스(AST/LSP), 도구 스키마 |
| | **에이전트 루프와 독립 검증자** | 02 문서 4절·5절: Agent Loop·검증 모두 없음 | 도구 호출, 반복 상한, 종료 조건, 추가 파일을 읽는 검증자 |
| | **PR 간 메모리**(쓰기 이벤트, 저장, 조회 도구, 수명 관리) | 03 문서 7.5절: 없음 | 답글·resolve·수정 이벤트 수집, 조직/저장소/경로 범위, 승인·무효화 |
| | **Jira 요구사항 구조화와 조건별 근거 판정** | 03 문서 9.2절: 텍스트 입력까지만 | 수락 기준 파싱, 이번 PR 범위 구분, 요구사항별 코드 근거 탐색 |
| | **팀 규칙 저장소**(범위·우선순위·승인·버전) | 03 문서 8.3절: 설정 파일·프롬프트뿐 | 경로별 규칙 선별은 코드로 |
| | **큐·재시도·취소·SHA 고정·테넌트 스코프** | 04 문서: 큐 없음, 격리 계층 없음 | 작업 메시지에 org·installation·head SHA·멱등 키, stale 폐기 |
| **운영해야 할 의존성** | LLM API, Git 호스팅 API | 05 문서 3절 | PR-Agent를 쓰든 안 쓰든 필수 |
| | (PR-Agent 일부 사용 시) PyGithub, python-gitlab, tiktoken(기본 토큰 추정. 정확 계산 경로는 `litellm.acount_tokens`, 05 문서 "토큰 계산 경로"), (선택) litellm, Dynaconf, starlette-context | 05 문서 2절 | provider 코드를 가져오면 Dynaconf·starlette-context 결합이 따라옴 |
| | (우리가 새로 도입) 큐, DB/벡터 저장소, Jira API, 코드 검색 인프라 | 04·05 문서: PR-Agent는 요구하지 않음 | PR-Agent를 가져와도 이 인프라는 별도 필요 |

---

## 3. 재사용 / 재구현 판단 (모듈별, 의견)

| 모듈 | 판단 | 이유 (근거) |
|---|---|---|
| provider 어댑터 (GitHub, GitLab) | **재사용** | 플랫폼 특성 처리가 두껍다: 수집 중 변경 감지(`github_provider.py:348-401`, `gitlab_provider.py:608-640`), 파일 50개 상한과 본문 폴백(`git_provider.py:52`), GitLab 인라인 위치·폴백(`gitlab_provider.py:1617-1752,1846-1882`). 직접 재작성은 비용이 크다 |
| provider의 설정 결합 | **분리 필요** | provider가 `get_settings()`(Dynaconf, 요청 컨텍스트)를 곳곳에서 읽는다(예: `github_provider.py:112-121,1849-1893`). 라이브러리로 쓰려면 요청마다 `request_cycle_context`로 감싸야 한다(`pr_agent.py:350-357` 패턴) |
| diff 전처리 | **부분 재사용** | 압축·청크·번호 붙이기는 재사용 가치가 크다. 반면 주변 줄 확장은 "프로그램이 정한 규칙"이라 동적 탐색을 대체하지 못한다. 우리 엔진의 첫 입력으로 쓰고 이후는 도구로 보충 |
| `PRReviewer` 전체(1750줄) | **재구현 권장** | 입력 수집·프롬프트·청크·상태·게시·라벨이 한 클래스에 섞여 있다(`pr_reviewer.py:174-1750`). 에이전트 루프를 끼우면 diff-only 지시(`pr_reviewer_prompts.toml:17,24`)와 충돌 |
| `PRCodeSuggestions` 자기 반성 | **아이디어만** | 같은 diff만 보고 점수를 매겨 추가 근거 탐색이 없음(02 문서 5.1절). 우리 검증자는 파일을 읽을 수 있어야 함 |
| LiteLLM 핸들러(3666줄) | **재구현 또는 선택적 사용** | 도구 호출을 지원하지 않고(`litellm_ai_handler.py:2863-2868,2987-2991`) 클라우드 인증·reasoning 파라미터 분기가 매우 길다. 우리가 provider SDK의 Tool Calling을 쓰면 불필요. 단 다중 provider 라우팅이 필요하면 LiteLLM 자체를 따로 쓰는 편이 낫다 |
| 웹훅 서버 | **재구현** | 큐·ack·재시도 없음, 프로세스 로컬 슬롯·중복 제거(04 문서). 검증·필터 함수만 참고 |
| 프롬프트(TOML) | **아이디어 참고** | 지시가 "diff만 본다"를 전제로 설계됨. 출력 스키마(YAML)와 "same wording" 재제시 규칙은 참고할 만함(`pr_reviewer_prompts.toml:330`) |
| 티켓 추출(Jira 등) | **부분 재사용** | 키 추출·허용 목록·인증 경계(`ticket_pr_compliance_check.py:90-338`)는 재사용 가능. 요구사항 구조화·근거 검증은 신규 |
| 설정 계층(`.pr_agent.toml`) | **개념만** | 저장소가 못 바꾸는 키를 코드로 막는 방식(`config_security.py`)은 참고. 전역 Dynaconf 결합 때문에 코드 재사용은 비추 |
| finding 상태 | **재사용 + 확장** | 같은 PR 안의 ACTIVE/RESOLVED, 재발, 보존 상한 구현이 독립적(`review_finding_state.py:199-296`). 단 "resolved" 판정이 "이번에 안 나옴"에 기반하므로(03 문서 7.3절) 우리 서비스에서는 코드 근거 기반 판정으로 보강 |

---

## 4. 라이선스 (근거 있는 범위)

- 프로젝트 라이선스는 **MIT**다(`LICENSE:1-3`). 코드 복사·수정·재배포가 가능하고 저작권·허가 고지를 유지해야 한다. 따라서 **코드 재사용이 가능**하다(코드 확인: LICENSE 앞부분. 하위 디렉터리 별도 라이선스는 이번에 전수 확인하지 않음 → 미확인).
- 전이 의존성의 라이선스와 LiteLLM 등의 사용 조건은 조사하지 않았다(미확인).
- 상표·로고(`README.md`의 Qodo 표기)는 코드 라이선스와 별개이므로 가져올 때 제외한다(의견).

---

## 5. 새로 설계해야 할 경계 (의견)

각 경계마다 PR-Agent 코드 쪽 접점(붙이는 위치)을 같이 적는다.

### 5.1 저장소 접근(워크스페이스) 경계
- **무엇**: `(org, repo, base_sha, head_sha, merge_base)`로 고정된 읽기 전용 뷰. `read_file(path, ref, range)`, `search(pattern)`, `find_references(symbol)`.
- **왜**: 리뷰 중 head가 바뀌어도 도구 결과가 일관되려면 SHA를 입력으로 받아야 한다. PR-Agent는 수집 시점에만 SHA를 쓰고 이후 재검증이 없다(01 문서 2.4절).
- **접점**: 파일 읽기는 이미 있는 `GitProvider.get_pr_file_content(path, sha)`(`github_provider.py:1908-1927`, `gitlab_provider.py:1003-1016`)를 도구로 감싸면 된다. 검색·참조는 PR-Agent에 없으므로 **clone 또는 미러를 새로 운영**해야 한다. `GitProvider.clone()`(`git_provider.py:575-601`)은 `--depth 1` 기본 브랜치 복제라 PR head를 받으려면 확장해야 한다(의견).

### 5.2 엔진(루프·검증) 경계
- **무엇**: 입력(`FilePatchInfo` 목록, 초기 diff 문맥, 규칙, 요구사항, 메모리) → 도구 호출 반복 → finding 목록 → 독립 검증 → 게시용 결과.
- **접점 A (최소 변경)**: `PRAgent(ai_handler=...)` 주입(`pr_agent.py:329-331`, `pr_reviewer.py:213`)으로 `chat_completion(model, system, user)` 안에서 루프를 돌리고 최종 YAML만 반환하는 핸들러를 쓴다. 장점은 provider·게시 코드를 그대로 쓰는 점, 한계는 핸들러가 PR 컨텍스트(SHA·테넌트)를 인자로 받지 못해 컨텍스트 변수에 의존해야 하고(추론) diff-only 프롬프트를 바꿔야 한다는 점.
- **접점 B (권장)**: `PRReviewer`를 쓰지 않고 provider·`get_pr_diff`·게시 함수만 호출하는 **자체 오케스트레이터**를 둔다. 종료 조건(최대 반복, 토큰·시간, 취소, "충분히 조사함" 판정)은 우리가 정의한다.
- 검증자는 생성자와 별도 호출이고 **추가 파일을 읽을 수 있는 도구를 가져야** 한다(PR-Agent의 자기 반성은 같은 diff만 봄).

### 5.3 메모리 경계
- **쓰기 이벤트**: 우리 서비스가 직접 받는다 — 리뷰 댓글에 대한 답글, 스레드 resolve/unresolve, 이후 커밋의 수정. PR-Agent는 resolve를 읽기만 하고(`pr_reviewer.py:696-717`) 저장하지 않는다.
- **저장**: `(org, repo, 범위[경로/심볼/규칙], 출처[PR, 댓글, SHA], 상태[제안/승인/폐기], 신뢰도)` 단위. 같은 PR 상태는 PR-Agent의 마커 방식을 그대로 두고, PR 간 메모리는 별도 저장소를 둔다.
- **읽기**: 최초 프롬프트 주입(PR-Agent 방식, `render_previous_findings`) **과** 호출 가능한 도구(`recall(path|symbol|rule)`)를 같이 둔다. 도구로 제공하면 모델이 필요한 만큼만 조회한다.
- **보정 필요**: PR-Agent는 resolve를 "수정 없이 닫음"으로 전달한다(03 문서 7.4절 추론). 무응답·resolve·코드 수정을 동의로 단정하지 않도록 상태를 구분해 저장해야 한다.
- **격리**: 모든 저장·조회에 org 식별자를 필수 인자로 둔다. PR-Agent에는 이 계층이 없다(04 문서 Q10-3).

### 5.4 요구사항(Jira) 경계
- **수집**: `extract_jira_tickets()` 반환 dict(`ticket_pr_compliance_check.py:329-337`)를 확장해 수락 기준을 **항목 리스트**로 구조화.
- **판정**: 리뷰 결과 파싱 직후, 게시 이전에 "기준별 검증 단계"를 삽입(`pr_reviewer.py:360-370` 사이에 해당). 각 기준에 대해 워크스페이스 도구로 구현 근거를 찾아 충족/미충족/확인 불가와 근거 위치를 낸다.
- **범위**: 연결된 이슈 전체와 이번 PR이 다루는 부분을 구분하는 로직은 PR-Agent에 없다(03 문서 9.2절). 신규 설계.

### 5.5 팀 규칙 경계
- 규칙 소유자·범위·승인 상태를 가진 저장소를 새로 두고, 리뷰 시 **경로 매칭으로 선별한 규칙만** 프롬프트/도구로 제공한다. PR-Agent의 `repo_context_files`(고정 경로 파일)와 스킬(모델이 설명 보고 선택)은 이 단계의 초기 형태로만 쓸 수 있다(03 문서 8.3절).

### 5.6 실행·테넌시 경계
- 작업 메시지: `{org/installation, repo, PR, head_sha, delivery_id, command}`. 멱등 키는 `(PR, head_sha, command)`, 새 head가 오면 이전 작업을 취소·폐기(PR-Agent는 둘 다 없음).
- 캐시 키·저장·검색 요청에 org를 포함. 요청마다 설정 컨텍스트를 새로 만든다(`pr_agent.py:350-357` 패턴은 재사용 가능).

---

## 6. 통합 시나리오 비교 (의견)

| 시나리오 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A. PR-Agent 거의 그대로 + 문맥 주입 | `repo_context_files`·`extra_instructions`·티켓 경로로 팀 규칙과 요구사항 텍스트를 넣는다 | 구현량이 가장 적다 | 동적 탐색·검증·PR 간 메모리 불가. 요구 목표의 핵심을 충족하지 못함 |
| B. 핸들러 교체 | `ai_handler`를 에이전트 루프 구현으로 교체 | provider·게시·상태 코드 재사용. 프롬프트·파싱 흐름 유지 | 핸들러가 컨텍스트를 못 받음, 단발 프롬프트 설계와 충돌, `PRReviewer` 내부(청크·상태)와 결합 |
| C. 라이브러리화 + 자체 오케스트레이터 | provider·diff·게시·상태 모듈만 import, 엔진·큐·메모리는 자체 | 경계가 깨끗, 격리·종료 조건·SHA 고정을 우리 방식으로 | Dynaconf·요청 컨텍스트 결합을 감싸야 함, 업스트림 변경 추적 부담 |

의견: **C를 기본으로 하고, 초기에는 B로 빠르게 검증**하는 순서가 비용 대비 위험이 낮다고 본다. 단 이 비교는 정량 측정 없이 코드 구조에서 도출한 것이다.

---

## 7. 우선 읽을 파일 (순서)

1. `pr_agent/algo/git_patch_processing.py` — 주변 줄 확장·번호 붙이기 (01 문서 3.3, 3.6)
2. `pr_agent/algo/pr_processing.py:206-381,423-552` — 예산·압축·청크
3. `pr_agent/git_providers/git_provider.py` — provider 인터페이스(`is_supported`, `get_diff_files`, `clone`, `publish_persistent_comment_full`)
4. `pr_agent/git_providers/github_provider.py:359-588`, `gitlab_provider.py:608-640,1103-1214` — 수집
5. `pr_agent/tools/pr_reviewer.py:186-530,803-871` — 입력 구성·게시·상태
6. `pr_agent/algo/review_finding_state.py` — 같은 PR 상태
7. `pr_agent/settings/pr_reviewer_prompts.toml` — 프롬프트와 출력 스키마
8. `pr_agent/tools/ticket_pr_compliance_check.py:167-338,945-1218` — Jira 경로

## 8. 알려진 이슈·주의 (분석 중 코드에서 관찰한 것)

> 업스트림 이슈 트래커·릴리스 노트는 조회하지 않았다(미확인). 아래는 이 SHA의 코드에서 직접 본 사항이다.

| 관찰 | 근거 | 영향 |
|---|---|---|
| 주변 줄 확장은 휴리스틱이며, 파일 50개 초과·신규 파일·본문 조회 실패 시 적용되지 않음 | `git_patch_processing.py:35`, `git_provider.py:52` | 문맥이 파일마다 불균일 |
| 부분적으로 잘린 patch를 감지하지 못함 | `github_provider.py:546-553` | 일부 변경이 조용히 누락될 수 있음 |
| `/review`는 커밋 메시지를 수집하지만 프롬프트에서 쓰지 않음 | `pr_reviewer.py:265`, `pr_reviewer_prompts.toml`(참조 없음) | 의도 파악에 쓰이지 않음 |
| 스키마 검증은 경고만 남김 | `pr_reviewer.py:1233-1284` | 형식 오류가 게시까지 갈 수 있음 |
| 증분 리뷰 기준이 리뷰 댓글 시각 | `github_provider.py:325-335` | 리베이스·시계 어긋남에 취약(추론) |
| 중복 제거·슬롯이 프로세스 로컬 | `servers/utils.py:198-258`, `github_app.py:49-54` | 다중 워커·레플리카에서 중복 실행 가능(추론) |
| GitLab 인라인 게시 시 MR을 다시 조회해 SHA가 리뷰 시점과 다를 수 있음 | `gitlab_provider.py:1758-1774` | 위치 어긋남 가능(추론) |
| `pr_compliance_checklist.yaml`을 읽는 코드가 없음 | grep | 용도 불명 |
| 유지보수 상태: "community-maintained legacy project of Qodo" | `README.md:27` | 장기 업스트림 의존 위험 |
