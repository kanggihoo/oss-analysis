# 비공개 저장소 접근 자격증명 비교 (Q13)

- 작성일: 2026-10-13
- 정정 반영: 2026-10-13 보고서 정정 반영
- 대상 SHA (`../repos.lock.tsv`):
  - pr-agent `330f0813b5fe0d1f54b794077c2d02aa85a1fb63`
  - open-code-review `57273a9ea28548b94b3d67c247ff13a63c01fc47`
  - kodus-ai `45676c5fe7ac016b6206ccea006e459677d92842`
- 기준: 각 레포 `reports/<repo>/07-credentials.md`를 중심으로 `04`(SaaS·격리), `03`(Jira), `next.md`를 대조했다. 근거를 복제하지 않고 **해당 절 링크**를 단다. 점수·순위는 매기지 않는다.
- 약어: **PA** = pr-agent, **OC** = open-code-review, **KO** = kodus-ai. 링크 텍스트의 `07 3.3`은 그 레포 `07` 문서의 3.3절이다. 절 번호는 각 문서 본문 번호를 따른다(OC는 `Q13-1~6` 번호).
- **실제 토큰·키 값은 어디에도 쓰지 않는다.** 변수명·설정 키 경로만 적는다.
- 세 레포 모두 **정적 추적만** 했고 실행 확인은 0건이다. 지원 수준은 GUIDE 3.3절 기준이다.
- 1~9절은 보고서 근거의 정리이고 **10절 위험 후보는 "후보"**(정적 추적, 실행으로 재현하지 않음), **11절만 분석자 의견**이다.

---

## 0. 한눈 요약

| 질문 | PA | OC | KO |
|---|---|---|---|
| 엔진이 Git 토큰을 직접 다루는가 | 예. 호스트 설정 한 벌(PAT / GitHub App / GitLab PAT) | **아니오.** 로컬 체크아웃만 읽고 clone·fetch·게시 코드가 엔진에 없음 | 예. Postgres에 (조직, 팀) 단위로 저장하고 사용 직전 복호화·재발급 |
| 테넌트별 토큰 분리 | 미지원(설치 ID와 GitLab 웹훅별 토큰만 부분) | 해당 없음(단일 사용자 CLI) | 지원(연결 행이 조직·팀 단위). 암호화는 전역 키 하나 |
| 토큰 저장 | 저장 안 함(환경·설정 파일·시크릿 제공자에서 읽기만) | Git 토큰 없음. LLM 키는 평문 JSON(0600) | PAT는 암호화, **GitLab OAuth·GitHub 설치 토큰 스냅샷은 평문** |
| clone 시 토큰 전달 | 구현 있으나 호출자(`/help_docs`)가 **비활성** | 엔진이 clone하지 않음 | 헤더 방식. 로컬은 `GIT_CONFIG_*` env, **E2B·linked-repo는 argv에 남음** |
| 웹훅 서명 검증 | 있음(GitHub·GitLab·Gitea·Bitbucket Server) | 해당 코드 없음 | **Git 4종 없음**, Azure만 전역 공유 토큰 |
| 근거 | [PA 07](../reports/pr-agent/07-credentials.md) 요약 | [OC 07 0절](../reports/open-code-review/07-credentials.md) | [KO 07 0절](../reports/kodus-ai/07-credentials.md) |

---

## 1. 자격증명 종류 × 플랫폼

권한(scope)은 **코드가 검사하는 것**과 **문서가 안내하는 것(제품 문구)**을 구분한다. PA는 scope를 읽지 않고, KO는 일부 판정에만 쓴다.

| 자격증명 | PA | OC | KO |
|---|---|---|---|
| GitHub App 설치 토큰 | **지원.** `github.app_id` + `github.private_key`, 웹훅 payload의 `installation.id`로 PyGithub `AppInstallationAuth` 생성. 발급·갱신은 라이브러리에 위임(내부 **미확인**) [PA 07 3.1](../reports/pr-agent/07-credentials.md) | 미지원(엔진). 예제 YAML이 CI의 `secrets.GITHUB_TOKEN`으로 게시 [OC 07 Q13-6](../reports/open-code-review/07-credentials.md) | **지원.** 배포당 App 하나를 모든 테넌트가 공유. `installationId`로 `@octokit/auth-app`에서 재발급(코드 확인으로 격상). 필요 권한은 문서 안내(Contents RO, Pull requests RW 등) [KO 07 1.1, 3.1](../reports/kodus-ai/07-credentials.md) |
| GitHub PAT | **지원.** `github.user_token`(classic·fine-grained 구분 없음). 문서 `repo` scope, fine-grained 세부 권한은 **미확인** [PA 07 1절](../reports/pr-agent/07-credentials.md) | 엔진에 없음 | **지원.** 암호화 저장. classic은 `x-oauth-scopes`로 쓰기 가능 판정, fine-grained는 `unknown`, 체크런 제한 [KO 07 1.1](../reports/kodus-ai/07-credentials.md) |
| GitHub Action `GITHUB_TOKEN` | **지원.** 러너가 `github.user_token`에 대입, 배포 유형 `user` 강제. 문서 권한 `contents: read`, `issues: write`, `pull-requests: write` [PA 07 1절](../reports/pr-agent/07-credentials.md) | 예제 YAML의 게시 단계에서만 사용(`contents: read`, `pull-requests: write`) [OC 07 Q13-6](../reports/open-code-review/07-credentials.md) | 리뷰 실행용 Action 없음(내부 알림용뿐) [KO 07 4.5](../reports/kodus-ai/07-credentials.md) |
| GitHub OAuth(사용자 위임) | **미지원** | 없음 | **미지원**(저장소 접근용). OAuth 교환은 사용자 로그인에만 있음 |
| GitLab PAT | **지원.** `gitlab.personal_access_token`, 헤더 `oauth_token`(기본) 또는 `private_token`. 문서 `api` scope [PA 07 4절](../reports/pr-agent/07-credentials.md) | 엔진에 없음. 예제가 `GITLAB_API_TOKEN`으로 게시 | **지원.** 암호화 저장. 문서 `api`, `read_api` 등 [KO 07 1.1](../reports/kodus-ai/07-credentials.md) |
| GitLab OAuth | **미지원** | 없음 | **부분 지원.** access·refresh 토큰 **평문 저장**, **refresh 교환 코드 없음** [KO 07 1.1, 3.2](../reports/kodus-ai/07-credentials.md) |
| GitLab 프로젝트·그룹 토큰 | **미확인**(전용 분기 없음, PAT 자리에 넣으면 같은 경로) | 예제 주석이 PAT/프로젝트 토큰 언급 | **부분 지원(추론).** 별도 분기 없음, 코드 주석이 입력을 가정 |
| `CI_JOB_TOKEN` | **미지원.** API 자격이 아님(extra config 헤더 예시 문구일 뿐) [PA 07 1절, 7절](../reports/pr-agent/07-credentials.md) | **예제 YAML만**: `GITLAB_API_TOKEN` 없을 때 `JOB-TOKEN` 헤더로 게시 [OC 07 Q13-6](../reports/open-code-review/07-credentials.md) | **미지원**(부정 grep) |
| Bitbucket / Azure DevOps / Gitea·Forgejo | 부분 확인(키 이름만): `bitbucket_server.bearer_token`, `azure_devops.pat`, `gitea.personal_access_token` 등. Bitbucket Cloud 앱은 JWT 교환 | 엔진에 없음 | **지원(PAT 한정).** Bitbucket Cloud·Azure OAuth는 "not implemented". Forgejo는 부분 지원 |
| Jira / MCP 토큰 | Jira Cloud: `jira.jira_site`·email·API token(호스트 전용 키) [PA 03 9.1](../reports/pr-agent/03-incremental-memory-rules.md#q9) | **없음** | `mcp-manager` 전용 스키마, OAuth(갱신 있음) 또는 API 토큰, 조직 단위 [KO 07 5.4](../reports/kodus-ai/07-credentials.md) |
| 웹훅 시크릿 | 8절 | 없음 | 8절 |
| LLM API 키 | 9절 | 9절 | 9절 |
| 시크릿 매니저·KMS | 선택: AWS Secrets Manager / GCS 시크릿 제공자 [PA 07 2.1](../reports/pr-agent/07-credentials.md) | **미지원** [OC 07 Q13-5](../reports/open-code-review/07-credentials.md) | **미지원**(부정 grep) [KO 07 1.2](../reports/kodus-ai/07-credentials.md) |
| 비공개 저장소 지원(종합) | 지원(호스트 한 벌의 토큰으로) | **엔진 책임 아님.** 호출자가 미리 clone한 로컬 체크아웃 전제 [OC 07 Q13-2](../reports/open-code-review/07-credentials.md) | 지원 |

- PA의 MOSAICO(A2A) 서버는 PR URL에 `.diff`를 붙여 **공개 diff만** 가져오므로 비공개 저장소는 미지원이다 [PA 07 1절](../reports/pr-agent/07-credentials.md).
- KO `.env.example`의 `GITHUB_TOKEN`은 서버 코드에서 읽는 곳을 찾지 못했다(선언만, 부정 grep) [KO 07 1.1](../reports/kodus-ai/07-credentials.md).

---

## 2. 주입 경로와 저장(암호화 여부)

| 항목 | PA | OC | KO |
|---|---|---|---|
| 주입 경로 | Dynaconf: 번들 기본값 → `settings/.secrets.toml` → **환경변수** → (비어 있을 때만) AWS Secrets Manager. 비밀 파일은 `.gitignore`·`.dockerignore`에 포함 [PA 07 2.1~2.2](../reports/pr-agent/07-credentials.md) | LLM 키만: 설정 파일 → `OCR_LLM_*` → `ANTHROPIC_*` → **셸 rc 파일 파싱**. CLI 키 플래그 없음 [OC 07 Q13-3](../reports/open-code-review/07-credentials.md) | 환경변수(App 비밀, 기본 LLM 키, `API_CRYPTO_KEY` 등) + **DB**(테넌트별 Git 자격증명, BYOK) [KO 07 1.2, 2.1](../reports/kodus-ai/07-credentials.md) |
| 저장 위치 | 저장 계층 없음. 외부 저장은 시크릿 제공자 2종과 Bitbucket Cloud 설치 시크릿뿐 | `~/.opencodereview/config.json`(**평문**), 디렉터리 권한은 만든 쪽에 따라 0755 또는 0700 [OC 07 Q13-3.3](../reports/open-code-review/07-credentials.md) | Postgres `auth_integrations.authDetails`(jsonb) + `integrations`(FK 조직·팀). Mongo에는 자격증명 없음 [KO 07 2.1](../reports/kodus-ai/07-credentials.md) |
| 암호화 | 저장하지 않으므로 해당 없음. 설치 토큰은 **프로세스 메모리**의 `Auth` 객체에만 존재 [PA 07 3.2](../reports/pr-agent/07-credentials.md) | **없음**(평문 JSON, 키체인·시크릿 매니저 없음) | PAT·BYOK `apiKey`: **AES-256-CBC, 랜덤 IV, MAC 없음, 전역 키 하나(`API_CRYPTO_KEY`), 회전·키 버전 없음.** 암호화는 DB 계층이 아니라 각 플랫폼 서비스가 PAT 필드만 호출 [KO 07 2.2](../reports/kodus-ai/07-credentials.md) |
| 평문으로 남는 것 | 해당 없음 | LLM 키 전부 | **GitLab OAuth access·refresh 토큰**, **GitHub App 설치 토큰 스냅샷**(리뷰 경로는 읽지 않아 사실상 쓰기 전용), BYOK의 `baseURL` 등 비밀 아닌 설정 [KO 07 2.3](../reports/kodus-ai/07-credentials.md) |
| 저장소가 바꿀 수 있는가 | 저장소 `.pr_agent.toml`·댓글 인자로는 **막힘**(금지 목록 + 접미사 규칙 `url/key/token/secret…`). 허용 목록이 아님 [PA 07 5.3](../reports/pr-agent/07-credentials.md) | PR head의 `rule.json`은 읽지만 키는 읽지 못함(도구가 저장소 밖 경로 거부, 추론) [OC 07 Q13-6](../reports/open-code-review/07-credentials.md) | 해당 없음(DB 저장) |
| 지원 수준 | 환경변수·`.secrets.toml`·외부 시크릿 주입 **지원**. DB·요청 헤더 임의 토큰 주입 **미지원** | LLM 키 주입 **지원(평문)**, 시크릿 매니저 **미지원** | 암호화 저장 **부분 지원** |

---

## 3. 테넌트별 분리

| 항목 | PA | OC | KO |
|---|---|---|---|
| 토큰 분리 단위 | **없음.** App ID·개인 키·웹훅 시크릿·LLM 키가 서비스 전체 한 벌. 테넌트 구분은 GitHub 설치 단위(payload의 `installation.id`)에 위임. 설치 ID와 PR 저장소의 대응을 검증하는 코드 없음(추론) [PA 07 3.2](../reports/pr-agent/07-credentials.md) | **해당 없음**(단일 사용자) [OC 04 10.1](../reports/open-code-review/04-saas-and-isolation.md) | **(조직, 팀) 단위 행.** 조회는 `{organization, team, platform}`, 조직 ID 없으면 `undefined` 반환. 다만 `integrations (platform, org, team)`는 일반 인덱스일 뿐 **DB 유일 제약이 없음이 확정**됐다(마이그레이션 59개 확인; 1행 유지는 앱 로직 의존, 동시 요청 시 중복 행 생성 여부는 **미확인**) [KO 07 2.1](../reports/kodus-ai/07-credentials.md) |
| 요청 범위 전달 | `copy.deepcopy(global_settings)`를 요청 컨텍스트에 넣어 토큰을 **요청 사본에만** 반영(GitLab 시크릿 제공자 경로가 그 사례). 컨텍스트 없는 실행(CLI)은 전역 객체 [PA 07 2.2](../reports/pr-agent/07-credentials.md), [PA 04 Q10-3](../reports/pr-agent/04-saas-and-isolation.md) | 환경 상속(`cmd.Env` 미설정)이라 워커 프로세스 환경이 그대로 자식 git에 전달 [OC 07 Q13-2](../reports/open-code-review/07-credentials.md) | 호출마다 `(organizationId, teamId)`로 DB에서 읽어 같은 워커 메모리로 전달. 큐 메시지·Mongo 리스에는 토큰 없음 [KO 07 4.1, 5.1](../reports/kodus-ai/07-credentials.md) |
| 캐시 키 | GitLab 봇 ID 캐시 키는 `sha256(url:token)`(값은 사용자 ID, 토큰 아님) | 없음 | 설치 토큰 캐시 키는 **`installationId` 원문**(조직 접두사 없음), 같은 설치를 두 조직이 공유하면 같은 토큰 재사용 [KO 07 3.1, 4.3](../reports/kodus-ai/07-credentials.md) |
| 팀 간 복제 | 해당 없음 | 해당 없음 | `CloneIntegrationUseCase`가 `authDetails`를 **통째로** 같은 조직의 다른 팀 행으로 복사(평문 필드는 평문 그대로) [KO 07 2.1](../reports/kodus-ai/07-credentials.md) |
| MCP·Jira | 호스트 설정 1벌 | 없음 | 조직 단위(팀 단위 아님) [KO 07 5.4](../reports/kodus-ai/07-credentials.md) |
| 지원 수준 | **미지원**(웹훅별 GitLab 토큰은 부분 지원, 단일 GitLab URL 한정) | 해당 없음 | **지원**(앱 수준 격리, RLS 없음) [KO 04 3절](../reports/kodus-ai/04-saas-and-isolation.md) |

---

## 4. 수명과 갱신

| 항목 | PA | OC | KO |
|---|---|---|---|
| GitHub 설치 토큰 | 발급·갱신은 PyGithub 위임(**미확인**). 코드에 JWT·만료·재발급 없음. 401은 영구 오류로 분류돼 재시도 안 함. 요청 단위로 클라이언트를 만들지만 도구가 추가 provider를 만들어 발급이 여러 번일 수 있음(추론) [PA 07 3.1~3.2](../reports/pr-agent/07-credentials.md) | 해당 없음 | 사용 직전 재발급. 프로세스 메모리 캐시 **TTL 50분**, 적중마다 `GET /rate_limit`으로 유효성 확인, 실패하면 캐시 삭제 후 재발급(최대 2회). JWT 내부는 라이브러리라 **미확인** [KO 07 3.1](../reports/kodus-ai/07-credentials.md) |
| PAT | 갱신 없음, 만료 시 사용자가 교체 | 해당 없음 | 갱신 없음. 만료 임박 알림 코드는 찾지 못함(**미확인**) |
| GitLab OAuth refresh | **미지원**(OAuth 갱신 코드 없음) | 없음 | **미지원.** `authorization_code` 교환 한 곳뿐, `refresh_token`은 저장만. 만료 시간 필드 저장 없음. 만료 시 실패 가능(추론) [KO 07 3.2](../reports/kodus-ai/07-credentials.md) |
| MCP/Jira OAuth 갱신 | 해당 없음 | 해당 없음 | **있음**(`refreshOAuthStateIfNeeded`, 재암호화 저장) [KO 07 5.4](../reports/kodus-ai/07-credentials.md) |
| 연결 해제·폐기 | 해당 없음 | 해당 없음 | DB의 `auth_integrations` 행 삭제. GitHub App은 `apps.deleteInstallation` 호출(복제로 다른 팀이 같은 설치 ID면 영향, 추론). **PAT·GitLab·Bitbucket·Azure·Forgejo의 제공자 측 revoke는 없음.** 해제가 설치 토큰 캐시를 비우지 않아 최대 50분 남음 [KO 07 2.4](../reports/kodus-ai/07-credentials.md) |
| 지원 수준 | GitHub App 사용 지원(갱신은 위임), OAuth 갱신 미지원 | 해당 없음 | App 재발급 지원, GitLab 갱신 **미지원**, 제공자 측 revoke **부분 지원** |

---

## 5. clone·fetch 시 토큰 전달 (argv / 헤더 / env / 로그 노출)

| 경로 | 전달 방식 | argv(`ps`)에 남는가 | `.git/config`에 남는가 | 리뷰 경로에서 쓰이는가 | 근거 |
|---|---|---|---|---|---|
| PA `GitProvider.clone` | URL userinfo로 받은 뒤 **제거**하고 `Authorization: Basic …`을 `GIT_CONFIG_*`(`http.extraHeader`) **환경변수**로 전달. `--filter=blob:none --depth 1` | 아니오(코드 기준) | 아니오(코드 기준) | **아니오.** 유일한 호출자 `/help_docs`가 `command2class`에서 빠져 **비활성** | [PA 07 5.1](../reports/pr-agent/07-credentials.md) |
| PA 자식 git 환경 | `os.environ.copy()` 상속(`OPENAI__KEY`, `GITHUB__USER_TOKEN` 등 포함) | - | - | 위와 같음 | 같은 절 |
| OC 엔진 | **clone·fetch·remote 호출 코드 없음.** 쓰는 서브커맨드는 `diff, show, merge-base, ls-files, ls-tree, grep, log, rev-parse`뿐. 부모 환경 상속. 부분 clone 체크아웃에서 누락 blob을 lazy fetch할 때 상속된 credential 설정이 쓰일 수 있음(**추론**, 실행 안 함) | 해당 없음 | 엔진은 `.git/config`를 읽지도 쓰지도 않음 | 해당 없음(예제 YAML이 `actions/checkout`·`git fetch origin pull/N/head`를 **엔진 밖에서** 실행) | [OC 07 Q13-1~2](../reports/open-code-review/07-credentials.md) |
| KO 로컬 샌드박스 본 clone | `git init` → `git fetch --depth=1 <토큰 없는 URL>`를 `GIT_CONFIG_COUNT/KEY_0/VALUE_0` **환경변수**로 실행. `remote add` 없이 `core.hooksPath=/dev/null` | **아니오** | **아니오** | 예 | [KO 07 4.2](../reports/kodus-ai/07-credentials.md) |
| KO 로컬 서브모듈 | 헤더를 `http.<origin>/.extraHeader`로 **origin에 한정**해 env 전달, 같은 호스트의 base 브랜치 선언 서브모듈만 | 아니오 | 아니오 | 예 | 같은 절 |
| KO **E2B** clone·sync | `git -c http.extraHeader="$GIT_AUTH_HEADER" fetch …`, `GIT_AUTH_HEADER`는 명령의 `envs`로 전달. 쉘이 풀어 `-c` 인자로 넘김 | **예(VM 안에서)**, 코드 주석이 인정 | 아니오(`-c`는 저장 안 함) | 예(E2B 키가 있을 때) | 같은 절 |
| KO **linked-repo clone** [ee] | E2B와 같은 `-c … "$GIT_AUTH_HEADER"` 방식. 로컬 샌드박스에서 `/bin/sh`로 실행하면 워커 호스트 `ps`에 헤더가 보일 수 있음(추론) | 예(추론) | 아니오 | 플랜 검증 통과한 조직만 | 같은 절 |
| KO 로컬 샌드박스 환경 상속 | 모든 자식 프로세스가 `{...process.env}` 수신(워커의 `API_CRYPTO_KEY`·DB 정보·GitHub 개인 키·LLM 키가 환경에 있음). 에이전트 `exec`는 읽기 전용 화이트리스트 + 경로 검사, 우회 가능성은 **미확인** | - | - | 예 | [KO 07 4.2](../reports/kodus-ai/07-credentials.md) |
| KO 셀프호스팅 doctor `ls-remote` | `GIT_CONFIG_*` env + `credential.helper=` 비움 + `GIT_TERMINAL_PROMPT=0` | 아니오 | 해당 없음 | 아니오(진단용) | 같은 절 |

**clone 후 정리**

| 레포 | 정리 | 근거 |
|---|---|---|
| PA | `TemporaryDirectory` + `ScopedClonedRepo.__del__`의 `rmtree`. 실패 시 `.git`과 새 폴더 삭제. stdout/stderr는 `DEVNULL`, 실패 로그는 `redact_credentials` | [PA 07 5.1](../reports/pr-agent/07-credentials.md) |
| OC | 엔진은 clone하지 않으므로 정리 주체는 호출자(러너 폐기 시 소멸). 세션 JSONL은 삭제·만료 코드 없음 | [OC 07 Q13-4 4.2](../reports/open-code-review/07-credentials.md) |
| KO | 리뷰마다 랜덤 `mkdtemp`(경로에 조직·저장소 ID 없음). 리스 카운트 0이면 로컬 디렉터리 **즉시** `rm -rf`(`tmpdir` 직속 + `kodus-sandbox-` 접두사만). E2B는 30초 유휴 후 kill 예약. 로컬 리스는 워커 간 공유되지 않음 | [KO 07 4.3](../reports/kodus-ai/07-credentials.md) |

**CLI·Action·웹훅 서버별 차이 요약**

- PA: CLI·Docker·Action은 `user` 배포(PAT/워크플로 토큰, 설치 토큰 아님), 웹훅 서버는 `app` 배포 [PA 07 1절](../reports/pr-agent/07-credentials.md).
- OC: 로컬 CLI / GitHub Actions 예제 / GitLab CI 예제 모두 Git 인증은 러너 책임. 웹훅 서버·SaaS 코드는 없음 [OC 07 Q13-6](../reports/open-code-review/07-credentials.md).
- KO: 워커(큐 소비) 경로 + 팀 키 CLI 경로 + **체험(trial) 모드**. 체험 모드는 인증 없는 `POST /cli/trial/review`가 사용자 PAT와 임의 `gitRemote`를 받아 API 프로세스에서 직접 실행하며 PAT를 큐에 넣지 않는다 [KO 07 4.5](../reports/kodus-ai/07-credentials.md).

---

## 6. 로그·에러·관측으로의 유출 방지

| 항목 | PA | OC | KO |
|---|---|---|---|
| 전역 마스킹 | **없음.** `redact_credentials`(URL userinfo, `Authorization`, 키-값, `glpat-` 형태, AWS 키 ID 패턴)는 clone URL 오류 로그와 CI 아티팩트 본문에만 적용. 호출 지점별 방어(웹훅 본문 대신 키 목록, 병합 설정 미기록) [PA 07 5.2](../reports/pr-agent/07-credentials.md) | **없음.** 마스킹은 `maskKey`(config 출력 표시용 한 곳). 오류 문자열은 세션 JSONL·결과 JSON·콘솔·OTel로 그대로 간다 [OC 07 Q13-3.3](../reports/open-code-review/07-credentials.md) | 로거 `deepSanitize` + pino `redact.paths`(`token`, `secret`, `apiKey`, `authorization`…). `SENSITIVE_KEYS`는 정확 일치이며 **`authToken`·`appPassword`·`githubPat`이 없음**. `message` 인자는 정화 안 함 [KO 07 5.2](../reports/kodus-ai/07-credentials.md) |
| diff·소스 본문 | diff 안에 커밋된 비밀은 **마스킹 없이 LLM으로** 감(CI 아티팩트에만 마스킹) | 소스 평문이 세션 JSONL에 항상 기록(끌 수 없음, 보존·삭제·민감 파일 필터 없음) [OC 07 Q13-4 4.2](../reports/open-code-review/07-credentials.md) | Langfuse는 입력·출력 마스크 설정이 없음(범위는 **미확인**) [KO 07 5.3](../reports/kodus-ai/07-credentials.md) |
| 설정값 로그 | 댓글·CLI로 통과한 설정은 값까지 INFO 로그(비밀 키는 5.3 필터로 차단) | 키 필드는 세션 레코드에 없음 | BYOK 저장 실패 로그는 `configValue`를 넣지 않는다고 주석 명시 |
| 외부 관측 | OpenTelemetry·Prometheus·LiteLLM 콜백 옵션([PA 04 Q10-4](../reports/pr-agent/04-saas-and-isolation.md)) | OTel은 기본 꺼짐. 켜면 저장소 절대경로·파일 경로·**오류 문자열**이 외부로. `content_logging`은 호출처가 없어 **효과 없음**(README와 불일치) [OC 07 Q13-4 4.3](../reports/open-code-review/07-credentials.md) | Langfuse 켜면 스팬에 조직·팀·PR·저장소·LLM 제공자 이름만(토큰·URL·키 없음) |
| 오류 → PR 댓글 | 실패 사유 댓글만 게시 | 두 예제 모두 실패 시 stderr 내용을 **PR/MR 댓글로 게시**, 엔진에 redaction 없음(추론) | 파이프라인 오류는 단계 오류로 기록 |

---

## 7. 저장소·댓글 입력으로 토큰을 바꾸거나 읽을 수 있는가

| 레포 | 결과 | 근거 |
|---|---|---|
| PA | 찾아본 범위에서 **막혀 있음**. 방어는 호스트 전용 키 목록 + 키 이름 접미사 휴리스틱 + 댓글 인자의 금지어 목록이며 **허용 목록이 아님**. 빈틈 후보 3건은 10절 | [PA 07 5.3](../reports/pr-agent/07-credentials.md) |
| OC | 저장소가 바꿀 수 있는 것은 PR head의 `rule.json`(프롬프트 주입 경로). 키를 읽을 도구는 없음(추론: 도구 목록과 경로 가드) | [OC 07 Q13-6](../reports/open-code-review/07-credentials.md) |
| KO | 모델 도구 `readReference`가 clone 토큰을 사용(토큰 자체는 모델에 노출 안 됨). 10절 참조 | [KO 07 4.6](../reports/kodus-ai/07-credentials.md) |

---

## 8. 웹훅 시크릿 검증

| 플랫폼 | PA | OC | KO |
|---|---|---|---|
| GitHub | **지원.** `github.webhook_secret` 없으면 403, `x-hub-signature-256` HMAC-SHA256을 `hmac.compare_digest`로 비교, 서명은 본문 바이트로 검증한 뒤 JSON 파싱. 예외: `/marketplace_webhooks`는 검증 없음 [PA 07 3.3](../reports/pr-agent/07-credentials.md) | 웹훅 수신 코드 없음 | **미지원.** `x-github-event`만 읽고 200. PAT 모드 `createWebhook`에 `secret` 없음. App 모드는 서버 쪽에서 설정할 방법이 없음 [KO 07 7절](../reports/kodus-ai/07-credentials.md) |
| GitLab | **지원.** `X-Gitlab-Token`을 `gitlab.shared_secret`과 `compare_digest`. 아니면 `<secret-name>:<webhook-token>`으로 해석해 시크릿 제공자에서 읽어 검증, 통과하면 그 요청 사본에 웹훅별 토큰 적용. fail-closed(401) [PA 07 4절](../reports/pr-agent/07-credentials.md) | 없음 | **미지원.** `ProjectHooks.add`에 `token` 없음, 문서도 "Secret token: Leave blank" |
| Bitbucket | Server: 시크릿 없으면 거부. Cloud 앱: JWT [PA 07 3.3](../reports/pr-agent/07-credentials.md) | 없음 | **미지원**(Cloud·Data Center) |
| Gitea·Forgejo | Gitea: GitHub과 같은 방식 | 없음 | **미지원**(헤더 4종 모두 수용) |
| Azure | 키 이름만 확인(미열람) | 없음 | **부분 지원.** `?token=` 쿼리를 복호화해 전역 `CODE_MANAGEMENT_WEBHOOK_TOKEN`과 `===` 비교. **모든 테넌트 공유**, 만료·회전 없음, 상수 시간 비교 아님 |
| 재전송 방어 | 서명은 재전송을 막지 못함. `X-GitHub-Delivery` 중복 제거는 **옵트인·프로세스 로컬**(워커 간 비공유) | 없음 | enqueue 시점 SHA 기반 중복 키 없음, inbox `(consumerId,messageId)` claim은 큐 메시지 중복용 [KO 03 6.2](../reports/kodus-ai/03-incremental-memory-rules.md#q6) |
| 재확인 | 요약만 | - | **04의 결론을 07이 컨트롤러를 직접 다시 열어 확인**, 결론 동일 [KO 07 7절](../reports/kodus-ai/07-credentials.md), [KO 04 1.3](../reports/kodus-ai/04-saas-and-isolation.md) |
| 영향 | 위조 payload는 서명 통과가 필요 | 해당 없음 | 보고서 평가: 조직 간 유출이 아니라 **서비스 남용(비용·스팸)** 위험이 주(추론) [KO 04 1.3](../reports/kodus-ai/04-saas-and-isolation.md) |

---

## 9. LLM API 키 관리

| 항목 | PA | OC | KO |
|---|---|---|---|
| 주입 | `openai.key`, `anthropic.key` 등 호스트 설정·환경변수(`OPENAI__KEY`). 저장소 설정·댓글로 변경 불가. 인증·reasoning 분기 대부분은 **미열람**([PA next](../reports/pr-agent/next.md)) [PA 07 1절, 2.1](../reports/pr-agent/07-credentials.md) | 우선순위: 설정 파일 → `OCR_LLM_*` → `ANTHROPIC_*` → 셸 rc. 프리셋별 환경변수 폴백(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` 등 12종). **설정 파일에 유효 엔드포인트가 있으면 환경변수가 무시됨**(README는 반대로 서술) [OC 07 Q13-3](../reports/open-code-review/07-credentials.md) | 조직별 BYOK(`BYOK_CONFIG`, Postgres jsonb) 또는 env 기본 키. 모델 생성 시점에만 복호화 [KO 07 6절](../reports/kodus-ai/07-credentials.md) |
| 저장 | 저장 안 함(환경에서 캡처한 전역 값) | **평문** `config.json`(파일 0600). `config set`은 값을 argv로 받음(노출은 추론) | `apiKey`와 Bedrock 비밀 필드만 `encrypt()`(전역 `API_CRYPTO_KEY`), 조회 응답은 앞 2자…뒤 3자 마스킹 |
| 테넌트 분리 | **없음.** 요청마다 키를 바꾸기 어려움. `PRAgent(ai_handler=...)` 주입 접점이 있음 [PA 04 Q10-3, Q10-5](../reports/pr-agent/04-saas-and-isolation.md) | 해당 없음 | **조직 단위.** 동시성 게이트 키는 `sha256(provider+apiKey+baseURL)`에 조직 포함 |
| 폴백 | 같은 모델 재시도 후 fallback 모델 | 해당 없음 | BYOK 실패 시 조직이 설정한 `fallback` 슬롯. **BYOK 실패가 자동으로 Kodus 기본 키로 넘어가지는 않음.** 슬롯이 없거나 `managed`이면 env 기본 키(조직 간 공유) |
| 회전·감사 | 없음 | 없음 | **미지원**(키 ID·버전 없음) |
| 소스 전송 | LLM 호출로 diff·파일이 감 | 사용자가 정한 URL(사내 게이트웨이 가능)로 감 | LLM 제공자·Langfuse로 감 |
| 지원 수준 | 호스트 한 벌 **지원**, 테넌트별 **미지원** | **지원(평문)** | 조직별 BYOK **지원**, 회전 **미지원** |

---

## 10. 발견된 위험 후보 (레포별)

- 아래는 **후보 목록**이다. 모두 **정적 추적**이며 실행·재현하지 않았다(실행 확인 0건). "코드 확인"은 코드의 사실, "추론"은 그 사실에서 도출한 영향이다.
- 검증 열의 "재열람"은 이 문서를 쓰며 해당 코드를 다시 열어 보고서 서술과 일치함을 확인했다는 뜻이다. 그 외는 보고서의 확인에 의존한다.

### 10.1 pr-agent

| ID | 후보 | 검증 | 근거 |
|---|---|---|---|
| PA-1 | 저장소 설정 방어가 **금지 목록 + 접미사 휴리스틱**이라 새 provider·새 비밀 키 이름이 접미사에 안 걸리면 자동 보호가 아니다. `github.app_id`, `config.git_provider`, `config.secret_provider`, `aws_secrets_manager.secret_arn`은 저장소 경로에서 막히지 않음(댓글 경로는 일부 차단). 외부로의 토큰 유출 경로는 확인하지 못함 | 코드 확인(목록 부재) / 영향은 추론 | [PA 07 5.3](../reports/pr-agent/07-credentials.md) |
| PA-2 | 로그 마스킹이 전역이 아니라 호출 지점별. `redact_credentials` 적용 범위는 clone 로그·CI 아티팩트뿐 | 코드 확인(grep 전수) | [PA 07 5.2](../reports/pr-agent/07-credentials.md) |
| PA-3 | diff 안에 커밋된 비밀이 마스킹 없이 LLM으로 전송 | 코드 확인(부재는 grep) | [PA 07 5.2](../reports/pr-agent/07-credentials.md) |
| PA-4 | GitLab 시크릿 제공자 경로에서 웹훅 토큰과 payload의 프로젝트를 대조하는 코드가 없음. 웹훅 시크릿을 아는 호출자가 payload를 위조하면 그 토큰 권한 범위 안에서 다른 MR을 지정할 수 있음 | 추론(낮음) | [PA 07 4절](../reports/pr-agent/07-credentials.md) |
| PA-5 | GitHub 설치 ID와 PR URL의 저장소 대응을 검증하지 않음. 서명된 payload를 신뢰하고 권한은 GitHub 쪽에 의존 | 코드 확인(부재) / 영향은 추론 | [PA 07 3.2, 8절](../reports/pr-agent/07-credentials.md) |
| PA-6 | `/marketplace_webhooks`는 서명 검증 없이 로그만 남김(코드 주석이 명시) | 코드 확인 | [PA 07 3.3](../reports/pr-agent/07-credentials.md) |
| PA-7 | 재전송 방어가 옵트인(`webhook_delivery_deduplication=false`)·프로세스 로컬 | 코드 확인 | [PA 07 3.3](../reports/pr-agent/07-credentials.md) |
| PA-8 | clone 구현이 자식 git에 환경 전체를 상속, GitLab은 호스트명에 `gitlab.`이 있어야 함. **호출자 `/help_docs`가 비활성이라 현재 도달 불가** | 코드 확인 | [PA 07 5.1](../reports/pr-agent/07-credentials.md) |
| PA-9 | 요청당 `GithubProvider`가 여러 번 만들어져 설치 토큰이 여러 번 발급될 수 있음(비용·rate limit) | 추론(라이브러리 내부 캐시 **미확인**) | [PA 07 3.2](../reports/pr-agent/07-credentials.md) |
| PA-10 | `GITLAB__SSL_VERIFY` 문자열 `"false"`의 provider 해석, `PR_AGENT_EXTRA_CONFIG_AUTH_HEADER` 리다이렉트 처리 | **미확인** | [PA 07 4절, 8절](../reports/pr-agent/07-credentials.md) |

### 10.2 open-code-review

| ID | 후보 | 검증 | 근거 |
|---|---|---|---|
| OC-1 | LLM 키가 평문 JSON에 저장. 디렉터리 권한은 만든 쪽에 따라 0755가 될 수 있고, 셸 rc 파일의 평문 `export`를 직접 파싱 | 코드 확인 | [OC 07 Q13-3.1, 3.3](../reports/open-code-review/07-credentials.md) |
| OC-2 | `ocr config set …api_key <값>`가 값을 argv로 받음. 두 예제 CI가 시크릿을 argv로 넘겨 러너 홈 `config.json`에 평문 기록 | 코드 확인 / argv 노출은 추론 | [OC 07 Q13-3.3, Q13-6](../reports/open-code-review/07-credentials.md) |
| OC-3 | 세션 JSONL에 diff와 도구가 읽은 **소스 전체**가 평문으로 항상 기록, 끌 수 없음, 보존·삭제·민감 파일(`.env` 등) 필터 없음. 키 필드는 레코드에 없음 | 코드 확인 | [OC 07 Q13-4 4.2](../reports/open-code-review/07-credentials.md), [OC 04 C](../reports/open-code-review/04-saas-and-isolation.md) |
| OC-4 | 예제가 `ocr` 실패 시 stderr를 공개 댓글로 게시. 엔진에 오류 redaction 없음 | 추론(코드 확인 + redaction 부재) | [OC 07 Q13-6](../reports/open-code-review/07-credentials.md) |
| OC-5 | `pull_request_target`(시크릿 접근) + PR head 작업 트리의 `rule.json` 로드 → 포크 PR이 리뷰 프롬프트를 바꿀 수 있음. 보고서 평가는 키 유출보다 **리뷰 품질 조작** 쪽 | 코드 확인 / 영향은 추론 | [OC 07 Q13-6](../reports/open-code-review/07-credentials.md), [OC 03 Q8](../reports/open-code-review/03-incremental-memory-rules.md#q8) |
| OC-6 | git 호출이 부모 환경을 그대로 상속. 부분 clone 체크아웃에서 lazy fetch 시 상속된 credential 설정이 쓰일 수 있음 | 코드 확인(상속) / lazy fetch는 추론 | [OC 07 Q13-2](../reports/open-code-review/07-credentials.md) |
| OC-7 | OTel을 켜면 저장소 절대경로·파일 경로·오류 문자열이 외부 수집기로 나감. `process.command_args` 포함 시 `--background` 값도 나갈 수 있음(추론). TLS 기본값·`OTEL_EXPORTER_OTLP_HEADERS` 처리 **미확인** | 코드 확인 / 추론 / 미확인 | [OC 07 Q13-4 4.3](../reports/open-code-review/07-credentials.md) |
| OC-8 | 세션 뷰어는 인증 없음. `--addr :3000`이면 전 인터페이스 바인드(기본은 `localhost:5483`) | 코드 확인 | [OC 07 Q13-4 4.1](../reports/open-code-review/07-credentials.md) |
| OC-9 | README는 환경변수가 최우선이라 하나 코드는 설정 파일이 우선 → 의도하지 않은 키·엔드포인트 사용 가능 | 코드 확인 | [OC 07 Q13-3.1, 8절](../reports/open-code-review/07-credentials.md) |
| OC-10 | Anthropic/OpenAI Go SDK의 환경변수 자동 읽기, SDK 오류 문자열에 요청 정보가 들어가는지 | **미확인**(SDK 소스 미열람) | [OC 07 Q13-3.2, 미확인](../reports/open-code-review/07-credentials.md) |

### 10.3 kodus-ai

| ID | 후보 | 검증 | 근거 |
|---|---|---|---|
| KO-1 | **GitHub App 연결 시 설치 ID 소유권 검증 없음.** 브라우저가 돌려준 `installation_id`를 그대로 서버가 App 키로 서명해 토큰을 발급. 같은 App을 공유하는 배포에서 다른 계정의 설치 ID를 제출하면 그 설치의 접근권을 자기 팀에 연결할 수 있음 | 코드 확인(검증 코드 부재) / 영향은 추론 | [KO 07 2.5](../reports/kodus-ai/07-credentials.md) |
| KO-2 | **`readReference` 도구가 clone 토큰을 플랫폼 확인 없이 `api.github.com`으로 전송.** 비-GitHub·GHES 조직의 토큰이 모델의 도구 호출 한 번으로 제3자 서비스에 전송될 수 있고, GitHub 조직에서는 토큰이 닿는 임의 저장소를 읽을 수 있음 | 코드 확인(**재열람**: `agent-tools.factory.ts`의 `api.github.com` 고정 호출과 `agent-review.stage.ts`의 `resolveGitHubToken`이 플랫폼 확인 없이 `authToken` 반환) / 영향은 추론 | [KO 07 4.6](../reports/kodus-ai/07-credentials.md) |
| KO-3 | **`mcp-manager`의 `AuthGuard`가 JWT를 `decode`만 하고 서명을 검증하지 않음.** 닿을 수 있으면 `organizationId` 클레임만 있는 임의 JWT로 해당 조직의 복호화된 연결 자격증명을 반환하는 내부 엔드포인트를 읽을 수 있음. dev compose는 포트를 호스트에 게시, 운영 노출은 `docker-compose.prod.yml`에 서비스가 없어 **미확인** | 코드 확인(**재열람**) / 운영 노출 미확인 | [KO 07 5.4](../reports/kodus-ai/07-credentials.md) |
| KO-4 | **로거 민감 키 목록에 `authToken`·`appPassword`·`githubPat`이 없음.** GitHub `checkRepositoryPermissions` 실패 로그가 `params`를 통째로 남기고 App 모드의 `authDetails.authToken`은 평문 설치 토큰 | 코드 확인(**재열람**: `logger.ts`에 `xauthtoken`만 있고 `authtoken` 없음) / 실제 발생은 실패 경로에서만(추론) | [KO 07 5.2](../reports/kodus-ai/07-credentials.md) |
| KO-5 | **Git 4종 웹훅 서명 검증 없음**, Azure는 전역 공유 정적 토큰(상수 시간 비교 아님, 회전 없음) | 코드 확인(부정 grep, 컨트롤러 직접 재확인) | [KO 07 7절](../reports/kodus-ai/07-credentials.md) |
| KO-6 | 암호화 설계: 전역 키 하나, **MAC 없는 AES-256-CBC**, 키 버전·회전 없음. **GitLab OAuth access·refresh 토큰과 GitHub 설치 토큰 스냅샷은 평문**. `safeDecrypt`는 복호화 실패 시 값을 평문으로 간주 | 코드 확인 | [KO 07 2.2~2.3, 6절](../reports/kodus-ai/07-credentials.md) |
| KO-7 | **E2B·linked-repo clone은 헤더가 git 프로세스 argv에 남음**(코드 주석이 로컬과 다르다고 인정). 로컬 샌드박스 자식 프로세스는 워커 `process.env`를 상속(워커의 `API_CRYPTO_KEY`·DB 정보·LLM 키 포함). 화이트리스트 우회 가능성은 **미확인** | 코드 확인 / linked-repo의 호스트 `ps` 노출은 추론 | [KO 07 4.2](../reports/kodus-ai/07-credentials.md) |
| KO-8 | GitHub 설치 토큰 캐시 키가 `installationId` 원문(조직 접두사 없음). 같은 설치를 두 조직이 공유하면 같은 토큰 재사용. 연결 해제가 캐시를 비우지 않아 최대 50분 잔존 | 코드 확인 / 영향은 추론 | [KO 07 3.1, 2.4](../reports/kodus-ai/07-credentials.md), [KO 04 3절](../reports/kodus-ai/04-saas-and-isolation.md) |
| KO-9 | 연결 해제 시 PAT·GitLab·Bitbucket·Azure·Forgejo 토큰의 제공자 측 revoke 없음. GitHub App은 `deleteInstallation`을 호출하는데 `CloneIntegrationUseCase`로 같은 설치 ID가 다른 팀에 복제됐다면 그 팀도 끊김 | 코드 확인 / 복제 영향은 추론 | [KO 07 2.1, 2.4](../reports/kodus-ai/07-credentials.md) |
| KO-10 | 팀 키 CLI 경로에서 GitHub·GitLab·Bitbucket Cloud·Forgejo의 `getCloneParams`가 `fullName`을 허용 목록과 대조하지 않음(Azure만 대조). PAT로 닿는 임의 저장소가 clone 대상이 될 수 있음 | 코드 확인 / 영향은 추론 | [KO 07 4.5](../reports/kodus-ai/07-credentials.md) |
| KO-11 | 체험(trial) 모드: 인증 없는 엔드포인트가 사용자 PAT와 임의 `gitRemote`를 받아 API 프로세스에서 직접 clone. CLI는 `GITHUB_TOKEN`·`GH_TOKEN` 환경 토큰을 자동 선택하고 인증 리뷰 실패 시 같은 토큰으로 체험 모드로 폴백 | 코드 확인 | [KO 07 4.5](../reports/kodus-ai/07-credentials.md) |
| KO-12 | 기본 LLM 키는 조직 간 공유(비용 귀속이 섞임). Langfuse 입출력 마스크 설정 없음(실리는 범위 **미확인**) | 코드 확인 / 미확인 | [KO 07 6절, 5.3](../reports/kodus-ai/07-credentials.md) |
| KO-13 | 웹훅이 서명 없이 repository id로 테넌트를 정하므로 임의 호스트가 해당 조직의 리뷰 잡을 발행할 수 있음(서비스 남용 위험, 조직 간 유출은 아님) | 추론 | [KO 04 1.3](../reports/kodus-ai/04-saas-and-isolation.md) |

---

## 11. 의견: 우리 서비스(여러 팀, 비공개 저장소)의 권장 구성

**이 절은 분석자 의견이며 코드 근거가 아니다.** 근거는 위 1~10절 링크를 따른다. 라이선스는 [GUIDE 2.1절](../GUIDE.md) 표 기준(PA MIT, OC Apache-2.0, KO는 `license.md`/`license_ee.md` 분리)이고 법률 자문이 아니다. 외부 지식(GitHub·GitLab 토큰 수명 등)은 이 레포 근거가 아니다.

### 11.1 Git 접근 모델

1. **GitHub는 App 방식만 쓴다.** KO에서도 GitHub PAT로 연결하면 Checks를 쓸 수 없고(문서·코드 주석), 07은 PAT를 보조 경로로 본다([KO 07 1.1, 8절](../reports/kodus-ai/07-credentials.md)). 설치 토큰은 **저장하지 않고 작업 시작 시 발급**한다. KO의 재발급 + 짧은 캐시 + 유효성 확인 구조([KO 07 3.1](../reports/kodus-ai/07-credentials.md))를 참고하되 캐시 키에 조직 접두사를 둔다.
2. **설치 소유권 검증은 직접 만든다**(KO-1). 설치 완료 URL의 `installation_id`를 믿지 않고 사용자 OAuth 토큰으로 설치 목록을 대조하거나 서명된 `state`를 쓴다.
3. **GitLab은 프로젝트·그룹 액세스 토큰을 1급으로 지원하고 OAuth refresh는 직접 구현한다.** PA는 PAT만, KO는 refresh 없음 + 평문이라 가져올 구현이 없다. `CI_JOB_TOKEN`은 PA·KO 모두 미지원이고 OC는 예제 YAML에만 있다.
4. **발급 시 범위를 PR 저장소 하나·최소 권한으로 줄이는 방식**(외부 지식, 세 레포 모두 코드로 확인되지 않음)을 쓰면 KO-2·KO-10 같은 임의 저장소 접근이 구조적으로 막힌다.

### 11.2 저장·테넌트 분리

1. **자격증명 저장은 KO 방식을 그대로 가져오지 않는다**(KO-6). 테넌트별 키 + 봉투 암호화(KMS 데이터 키, 인증 태그가 있는 방식, 키 ID 저장), 토큰은 전용 테이블·전용 DB 역할로 분리한다.
2. **요청 범위 객체로만 전달한다.** PA의 요청별 설정 사본 주입 패턴(웹훅이 팀을 식별한 뒤 사본에 토큰을 넣음, [PA 07 6절](../reports/pr-agent/07-credentials.md))이 가장 작은 접점이다. 팀별 토큰을 환경변수로 주입하는 설계는 피한다(PA·OC 모두 환경 상속·전역 상태 문제를 보고함).
3. **리뷰 실행은 프로세스·컨테이너 단위로 격리한다.** OC는 환경 상속과 `$HOME` 평문 로그, KO 로컬 샌드박스는 `process.env` 상속이므로, 최소 환경변수만 가진 격리 환경에서 실행하고 `HOME`·작업 디렉터리를 작업 단위로 쓴다([OC 07 의견](../reports/open-code-review/07-credentials.md)).

### 11.3 clone

1. **KO 로컬 샌드박스의 `GIT_CONFIG_*` 환경변수 방식을 따른다**(argv·`.git/config`에 토큰 없음, PA의 `_clone_inner`도 같은 방식). `-c "$VAR"`처럼 쉘이 argv로 푸는 방식(KO E2B·linked-repo)은 피한다.
2. 서브모듈 헤더를 **origin에 한정**하는 KO `submodule-fetch.ts` 규칙(base 선언 일치, 같은 호스트, 재귀 금지)은 그대로 참고할 가치가 크다([KO 07 4.2, 8절](../reports/kodus-ai/07-credentials.md)). 코드 재사용은 KO 비-ee 코드도 AGPL 대상일 수 있어 **패턴 재구현**을 권한다.
3. 작업 디렉터리는 작업 단위 임시 경로 + 종료 시 삭제(KO 리스 정리, PA `ScopedClonedRepo`)를 강제한다.
4. **모델 도구에는 clone 토큰을 주지 않는다**(KO-2). 교차 저장소 읽기가 필요하면 서버 측 허용 목록과 플랫폼별 호스트 고정으로 제공한다.

### 11.4 웹훅·로그·LLM·Jira

1. **웹훅은 통합 단위 시크릿으로 HMAC을 직접 검증한다.** PA의 GitHub 구현(시크릿 없으면 거부, 본문 바이트로 검증 후 파싱, `compare_digest`)이 참고가 되고(MIT), KO는 가져오지 않는다. 재전송 방어는 워커 간 공유 저장소의 delivery ID로 한다(PA는 프로세스 로컬·옵트인).
2. **로그**: 허용 목록 로깅, 전역 redaction 필터, 오류를 PR 댓글로 게시하기 전 redaction(OC-4), 요청 파라미터 객체를 통째로 로깅하지 않기(KO-4), 키 이름 목록에 `authToken`류 추가. diff 안의 비밀은 별도 시크릿 스캐너가 필요하다(PA-3, OC-3).
3. **LLM 키**: 조직별 BYOK + 서버 암호화 + 마스크 응답은 KO 설계를 따를 만하다. 회전·사용량 귀속·기본 키 폴백의 비용 책임은 직접 정한다. OC처럼 `ResolvedEndpoint`를 서비스가 직접 채우거나 PA의 `ai_handler` 주입 접점을 쓰면 환경 변수 우선순위 함정을 피한다.
4. **Jira·MCP 토큰**: KO의 전용 스키마·별도 키·OAuth 갱신 구조는 참고할 만하다. 서비스 간 JWT는 반드시 **서명 검증**하고 내부망으로 한정한다(KO-3). 팀별 Jira 사이트가 필요하면 PA의 호스트 전용 키 경계 패턴을 팀 단위로 확장한다.

### 11.5 직접 만들어야 하는 부분

설치 소유권 검증 · 테넌트별 키 봉투 암호화와 회전 · GitLab refresh · 단명·최소 범위 토큰 발급 · 통합별 웹훅 서명 검증과 재전송 방어 · 작업 단위 격리 환경과 최소 환경변수 · 모델 도구용 서버 측 교차 저장소 읽기 · 로그·오류 redaction · 연결 해제 시 제공자 측 revoke. 재사용 가치가 있는 것은 PA의 provider·서명 검증·요청 범위 설정 패턴, KO의 clone 헤더·서브모듈 규칙·BYOK 마스킹 정도다.

---

## 12. 보고서 간 모순과 검증 약점

| # | 내용 | 위치 | 상태 |
|---|---|---|---|
| 1 | **KO 04와 07의 불일치 3건**: (a) 04는 "(org, team, platform)당 1행"이나 07은 일반 인덱스일 뿐이라고 정정(마이그레이션까지 확인해 DB 유일 제약 없음 확정), (b) 04는 E2B가 `GIT_AUTH_HEADER` env로 전달한다고 적었으나 07은 쉘이 argv로 푼다고 정정, (c) 04는 설치 토큰 재발급을 추론으로 뒀으나 07이 코드 확인으로 격상. **04 정정 반영됨(2026-10-13)**: 세 건 모두 04 1.1·1.2절이 07에 맞춰졌다 | [KO 04 1.1~1.2](../reports/kodus-ai/04-saas-and-isolation.md) vs [KO 07 9절](../reports/kodus-ai/07-credentials.md) | 정정 완료, 07·04 일치 |
| 2 | **PA 04 "요청마다 새 provider"**를 07이 도구의 추가 인스턴스 생성으로 정정. **04 정정 반영됨(2026-10-13)**: Q10-1 토큰 수명 행과 Q10-3 provider 인스턴스 행이 "provider 인스턴스를 만들 때마다"로 바뀌었다 | [PA 04 Q10-1](../reports/pr-agent/04-saas-and-isolation.md) vs [PA 07 3.2, 7절](../reports/pr-agent/07-credentials.md) | 정정 완료 |
| 3 | **PA 04** "저장소 `.pr_agent.toml`이 연결 정보·키를 바꾸지 못하도록 차단"은 맞지만 07이 **금지 목록 + 접미사 휴리스틱**이라는 단서를 추가 | 같은 곳, [PA 07 7절](../reports/pr-agent/07-credentials.md) | 04의 결론 유지 + 단서 |
| 4 | **OC 03의 `content_logging` 서술**(켜면 프롬프트·응답을 내보냄)이 07(호출처 없어 효과 없음)과 어긋났던 것은 **정정 완료**(03 7.4가 07과 일치). 직접 재검색해 07이 맞음을 확인 | [OC 03 7.4](../reports/open-code-review/03-incremental-memory-rules.md#q7) vs [OC 07 Q13-4 4.3](../reports/open-code-review/07-credentials.md) | 정정 완료 |
| 5 | **OC 도구 개수 표기**: **정정 완료.** 기준은 [OC 00 1절](../reports/open-code-review/00-overview.md)(`Tool` 값 7개 = 모델 호출 가능 6개 + 내부 `Unknown` 1개, Provider 등록 5개, `task_done`은 직접 처리). 직접 확인한 `definitions.go`의 7개 항목(`Unknown`·`TaskDone` 포함)과 일치 | [OC 07 Q13-5](../reports/open-code-review/07-credentials.md), OC 00 1절 | 정정 완료 |
| 6 | **README·문서와 코드 차이**(보고서 기록): OC README의 환경변수 우선순위·`content_logging` 설명, KO 문서의 Secret token 비우기 안내 vs 서명 검증 부재의 일관성(코드와 문서가 같은 상태) | [OC 07 8절](../reports/open-code-review/07-credentials.md), [KO 07 7절](../reports/kodus-ai/07-credentials.md) | 보고서 간 모순 아님 |

**검증 약점**

- **KO 줄 번호의 재대조 현황(2026-10-13 정정 후)**: 02~05의 `path:range` 인용 약 650개를 모두 열어 범위·식별자를 대조하고 약 30건을 정정했다(02 약 198, 03 약 205, 04 약 155 중 약 150, 05 약 95). **재대조하지 못한 범위**: 01 전체, 02의 긴 범위, 03·04·05의 일부 긴 범위·파일명만 인용한 파일(각 문서 머리, [KO next](../reports/kodus-ai/next.md)). **KO 07은 모든 줄 번호를 작성자가 직접 열어 확인**했고 04 인용 줄 번호도 모두 일치했다고 밝힌다([KO 07 9절](../reports/kodus-ai/07-credentials.md)). 이 문서의 KO 근거는 07 중심이다. 이 문서 작성 중 KO-2·KO-3·KO-4 후보의 핵심 줄은 직접 다시 열어 일치를 확인했다. 그 밖은 보고서에 의존한다.
- **외부 라이브러리 내부 동작은 어느 레포도 열지 못했다**: PyGithub `AppInstallationAuth`(PA), `@octokit/auth-app`(KO), Anthropic/OpenAI Go SDK·OTel SDK(OC). 설치 토큰 발급·만료·오류 문자열의 실제 내용은 **미확인**이다.
- **PA의 비-GitHub provider(Bitbucket·Azure·Gitea·Gerrit)와 Lambda 웹훅 인증은 키 이름만 확인**했다([PA 07 8절](../reports/pr-agent/07-credentials.md)). 표의 해당 칸은 "부분 확인"이다.
- **KO Azure·Bitbucket·Forgejo의 file-change·게시 본문은 미열람**([KO next](../reports/kodus-ai/next.md)). 자격증명 저장·웹훅 검증은 07에서 확인했다.
- **KO `workflow_jobs` 보존 기간, 운영 `mcp-manager` 네트워크 노출, GitLab 프로젝트 토큰의 봇 사용자 동작, 동시 요청 시 `integrations` 중복 행 생성 여부는 미확인**이다(`integrations`의 DB 유일 제약 없음 자체는 확정)([KO 07 10절](../reports/kodus-ai/07-credentials.md)).
- 세 레포 모두 **실행 확인 0건**이다. 로그에 실제로 토큰이 나타나는지, argv 노출, 토큰 만료 시 동작은 모두 정적 추적이다.
- 이 문서의 위험 후보는 GUIDE 3.3절 규칙에 따라 "후보"이며 우선순위나 심각도 순위를 매기지 않았다.
