# RTK gh 명령 지원 범위 정리

분석 대상: `rtk gh`

근거 파일:
- `rtk/src/main.rs`
- `rtk/src/cmds/git/gh_cmd.rs`
- `rtk/src/discover/rules.rs`
- `rtk/src/discover/registry.rs`
- `rtk/README.md`
- `rtk/docs/usage/FEATURES.md`

## 1. help 출력과 실제 구현의 차이

현재 환경에서 `rtk gh --help`는 다음처럼 표시된다.

```text
GitHub CLI (gh) commands with token-optimized output

Usage: rtk gh [OPTIONS] <SUBCOMMAND> [ARGS]...

Arguments:
  <SUBCOMMAND>  Subcommand: pr, issue, run, repo
  [ARGS]...     Additional arguments
```

하지만 실제 구현인 `src/cmds/git/gh_cmd.rs::run()` 기준으로는 top-level subcommand가 하나 더 있다.

| top-level subcommand | 실제 처리 |
|---|---|
| `pr` | RTK 전용 compact 처리 있음 |
| `issue` | RTK 전용 compact 처리 있음 |
| `run` | RTK 전용 compact 처리 있음 |
| `repo` | `repo view`에 한해 RTK 전용 compact 처리 있음 |
| `api` | 인식은 하지만 compact 처리 없이 passthrough |
| 그 외 | unknown subcommand로 보고 `gh <subcommand> ...` passthrough |

즉 help 설명의 `pr, issue, run, repo`는 완전한 목록이라기보다 대표/문서화된 목록에 가깝다. 구현에는 `api`도 분기되어 있다.

## 2. `rtk gh pr ...`

`rtk gh pr` 아래에서 RTK가 별도 처리하는 명령은 다음과 같다.

| 명령 | 처리 방식 |
|---|---|
| `rtk gh pr list` | `gh pr list --json number,title,state,author,updatedAt`로 실행한 뒤 PR 목록을 compact 출력한다. 최대 20개까지 보여준다. |
| `rtk gh pr view <num>` | `gh pr view <num> --json number,title,state,author,body,url,mergeable,reviews,statusCheckRollup`로 실행한 뒤 PR 상태, author, merge 가능 여부, review/check 요약, URL, body를 정리한다. |
| `rtk gh pr checks <num>` | `gh pr checks <num>` 결과에서 passed/failed/pending 개수와 실패 check를 요약한다. |
| `rtk gh pr status` | `gh pr status --json number,title,reviewDecision,statusCheckRollup`로 실행한 뒤 현재 branch/내 PR 상태와 check 결과를 compact 출력한다. |
| `rtk gh pr create ...` | 실제 `gh pr create`를 실행하고 성공 출력은 `ok created #N URL` 형태로 줄인다. |
| `rtk gh pr merge ...` | destructive action이라 RTK가 줄이지 않고 원본 `gh pr merge` 출력 그대로 passthrough한다. |
| `rtk gh pr diff ...` | 기본적으로 `gh pr diff` 결과를 `git::compact_diff(raw, 500)`로 축약한다. |
| `rtk gh pr comment ...` | 실제 명령 실행 후 성공 출력은 `ok commented #N` 형태로 줄인다. |
| `rtk gh pr edit ...` | 실제 명령 실행 후 성공 출력은 `ok edited #N` 형태로 줄인다. |

`pr` 아래의 그 외 명령은 `gh pr ...`로 passthrough된다.

### `pr view` passthrough 조건

`rtk gh pr view <num>`은 다음 플래그가 있으면 RTK compact 처리를 하지 않고 원본 `gh pr view`로 넘긴다.

- `--json`
- `--jq`
- `--web`
- `--comments`

### `pr status` passthrough 조건

`rtk gh pr status`는 다음 플래그가 있으면 원본 `gh pr status`로 넘긴다.

- `--help`
- `-h`
- `--web`
- `--jq`
- `--template`

### `pr diff` passthrough 조건

`rtk gh pr diff`는 기본 diff 형식일 때만 compact diff를 적용한다. 다음 조건에서는 원본 출력으로 넘긴다.

- `--no-compact`
- `--name-only`
- `--name-status`
- `--stat`
- `--numstat`
- `--shortstat`

## 3. `rtk gh issue ...`

`rtk gh issue` 아래에서 RTK가 별도 처리하는 명령은 다음과 같다.

| 명령 | 처리 방식 |
|---|---|
| `rtk gh issue list` | `gh issue list --json number,title,state,author`로 실행한 뒤 issue 목록을 compact 출력한다. 최대 20개까지 보여준다. |
| `rtk gh issue view <num>` | `gh issue view <num> --json number,title,state,author,body,url`로 실행한 뒤 제목, 상태, author, URL, body를 정리한다. |

`issue` 아래의 그 외 명령은 `gh issue ...`로 passthrough된다.

### `issue view` passthrough 조건

`rtk gh issue view <num>`은 다음 플래그가 있으면 compact 처리를 하지 않는다.

- `--json`
- `--jq`
- `--web`
- `--comments`

## 4. `rtk gh run ...`

`rtk gh run` 아래에서 RTK가 별도 처리하는 명령은 다음과 같다.

| 명령 | 처리 방식 |
|---|---|
| `rtk gh run list` | `gh run list --json databaseId,name,status,conclusion,createdAt --limit 10`으로 실행한 뒤 workflow run 목록을 compact 출력한다. |
| `rtk gh run view <id>` | `gh run view <id>` 결과에서 status/conclusion과 실패 job 중심으로 정리한다. |

`run` 아래의 그 외 명령은 `gh run ...`으로 passthrough된다.

### `run view` passthrough 조건

`rtk gh run view <id>`는 다음 플래그가 있으면 compact 처리를 하지 않는다.

- `--log-failed`
- `--log`
- `--json`

## 5. `rtk gh repo ...`

`rtk gh repo`는 `view`만 별도 처리한다.

| 명령 | 처리 방식 |
|---|---|
| `rtk gh repo` | 인자가 없으면 `repo view`로 간주한다. |
| `rtk gh repo view [repo]` | `gh repo view --json name,owner,description,url,stargazerCount,forkCount,isPrivate`로 실행한 뒤 repo 요약을 compact 출력한다. |

`repo view`가 아닌 다른 `repo` 하위 명령은 `gh repo ...`로 passthrough된다.

## 6. `rtk gh api ...`

`api`는 `gh_cmd.rs::run()`에서 top-level subcommand로 인식된다.

하지만 별도 compact formatter는 적용하지 않는다. 구현 주석상 `gh api`는 사용자가 명시적으로 고급/구조화 응답을 요청한 명령이므로 JSON 값을 망가뜨리지 않기 위해 원본 응답을 보존한다.

따라서 `rtk gh api ...`는 지원되지만 token 절감용 compact 명령이라기보다 tracking이 붙은 passthrough에 가깝다.

## 7. `gh release` 관련 단서

`src/discover/rules.rs`의 rewrite 규칙은 다음 패턴을 GitHub 범주로 분류한다.

```text
^gh\s+(pr|issue|run|repo|api|release)
```

또한 `src/discover/registry.rs` 테스트에는 `gh release list`가 `rtk gh release list`로 rewrite되는지 확인하는 테스트가 있다.

하지만 `src/cmds/git/gh_cmd.rs::run()`에는 `release` 전용 분기가 없다. 따라서 실제 실행 시 `rtk gh release list`는 unknown subcommand로 처리되어 `gh release list` passthrough가 된다.

정리하면 다음과 같다.

| 명령 | rewrite 대상 여부 | RTK compact 처리 여부 |
|---|---:|---:|
| `gh release list` -> `rtk gh release list` | 예 | 아니오, passthrough |

## 8. 공통 passthrough 정책

`rtk gh`는 사용자가 `--json`을 직접 넘기면 top-level에서 바로 passthrough한다.

이유는 `--json`, `--jq`, `--template` 같은 구조화 출력은 사용자가 특정 필드나 형식을 의도한 경우가 많고, RTK가 이를 compact 처리하면 응답 구조를 손상시킬 수 있기 때문이다.

rewrite/discover 쪽도 비슷한 정책을 가진다. `gh` 명령에 `--json`, `--jq`, `--template`이 포함되어 있으면 `rtk gh`로 rewrite하지 않도록 막는다.

## 9. 요약

현재 구현 기준으로 RTK가 `gh`에 대해 실질적으로 제공하는 compact 명령은 다음이다.

```text
rtk gh pr list
rtk gh pr view <num>
rtk gh pr checks <num>
rtk gh pr status
rtk gh pr create ...
rtk gh pr diff ...
rtk gh pr comment ...
rtk gh pr edit ...

rtk gh issue list
rtk gh issue view <num>

rtk gh run list
rtk gh run view <id>

rtk gh repo
rtk gh repo view [repo]
```

다음은 RTK가 인식하거나 rewrite할 수는 있지만 compact formatter가 없거나 원본 보존 정책 때문에 passthrough에 가깝다.

```text
rtk gh api ...
rtk gh release ...
rtk gh pr merge ...
rtk gh <unknown-subcommand> ...
```

핵심 결론:

- help에는 `pr, issue, run, repo`만 보이지만 구현에는 `api`도 top-level 분기로 있다.
- `release`는 rewrite 규칙에는 있지만 `gh_cmd.rs`에는 compact 구현이 없다.
- compact 처리는 주로 PR, issue, workflow run, repo view에 집중되어 있다.
- 구조화 출력 플래그(`--json`, `--jq`, `--template`)가 있으면 원본 보존을 우선한다.
