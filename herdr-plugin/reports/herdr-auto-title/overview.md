---
sha: "69d7182ce46d539dd092ae666b11298a9a2bc39e"
created: 2026-10-22
updated: 2026-10-22
sources:
  - herdr-plugin.toml
  - README.md
  - cmd/herdr-auto-title/main.go
  - internal/herdr/client.go
  - internal/herdr/protocol.go
  - internal/herdr/session.go
  - internal/app/app.go
  - internal/app/tabs.go
  - internal/app/config.go
  - internal/app/paths.go
  - internal/app/topics.go
  - internal/state/tab.go
  - internal/state/changes.go
  - internal/reads/reads.go
  - internal/reads/processes.go
  - internal/resolver/resolver.go
  - internal/resolver/agent.go
  - internal/resolver/terminal.go
  - internal/resolver/transcript.go
  - internal/resolver/process.go
  - internal/resolver/remote.go
  - internal/resolver/git.go
  - internal/resolver/cwd.go
  - internal/resolver/sanitize.go
  - internal/resolver/position.go
  - internal/resolver/topics.go
  - internal/labels/labels.go
  - internal/labels/claims.go
  - internal/claude/transcript.go
  - internal/antigravity/annotation.go
  - internal/pi/transcript.go
  - internal/transcript/transcript.go
  - internal/git/git.go
  - internal/instance/instance.go
  - internal/instance/restart.go
  - docs/architecture/herdr-socket-api.md
---

# herdr-auto-title Analysis Overview

범례: 검증 수준은 `코드 확인`(구현부를 직접 읽음) / `추론` / `미확인`. 이 문서는 실행하지 않고 읽기만 했으므로 `실행 확인`은 없다. 경로는 모두 `repos/herdr-auto-title/` 기준이고, `파일:줄`은 기준 SHA에서 직접 열어 확인한 줄이다.

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/kryptamine/herdr-auto-title` (`artifacts/herdr-auto-title/repo-metadata.txt`)
- **기준 SHA**: `69d7182ce46d539dd092ae666b11298a9a2bc39e` (commit 2026-10-21, main)
- **작업트리 상태**: Clean (repo-metadata.txt, 추적 파일 133개)
- **분석 목적**: 학습·도입 검토. (1) herdr 플러그인이 매니페스트(`herdr-plugin.toml`)로 herdr와 어떻게 연동하는지, (2) 탭 제목을 자동으로 만드는 poll loop(주기적으로 세션을 읽고 결정하는 반복)가 어떻게 도는지.
- **라이선스**: MIT, 루트 `LICENSE` 하나. 하위 디렉터리에 다른 LICENSE는 없음 (`tools/go.mod` 등은 별도 모듈이지만 LICENSE 파일은 추적 파일 목록에 없음. 코드 확인: `git ls-files` 결과)
- **분석 대상 제품**: Go 바이너리 하나(`cmd/herdr-auto-title`)와 매니페스트 `herdr-plugin.toml`. 별도 모듈 `tools/`(린터 의존성)와 `scripts/*.py`(probe 스크립트)는 개발 도구라 분석 밖.
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지) · 제외: 없음

### 용어

- **herdr**: 코딩 에이전트용 터미널 멀티플렉서. workspace > tab > pane 계층을 가진다.
- **플러그인**: herdr가 `herdr-plugin.toml`을 읽어 빌드·시작하는 외부 프로그램. 이 레포는 herdr 소켓 API로 세션을 읽고 이름을 바꾼다.
- **소켓 API**: herdr가 `HERDR_SOCKET_PATH`에 여는 로컬 소켓. 줄 단위 JSON(NDJSON) 요청·응답.
- **poll loop**: 일정 주기(기본 500ms)로 세션 스냅샷을 읽고 이름을 다시 정하는 반복.
- **transcript**: 코딩 에이전트(Claude Code 등)가 대화를 이어 붙여 쓰는 세션 파일.
- **claim(잠금)**: 사용자가 직접 바꾼 이름이라고 판단해 플러그인이 더 이상 건드리지 않기로 한 라벨.

---

## 2. 프로젝트 개요

herdr는 기본적으로 탭을 위치 번호로, pane을 에이전트 이름(`claude`)으로 보여 준다. 이 플러그인은 tab·pane 이름을 그 안에서 하는 일(디렉터리, git 브랜치, 에이전트의 작업 주제, 실행 중인 프로그램, ssh 호스트)로 자동 바꾼다. 외부 LLM·네트워크를 쓰지 않는 결정적 규칙으로 제목을 만든다.

### 플러그인이 하는 일 (README·docs와 코드 대조)

| # | 주장 | 근거 | 검증 수준 |
|---|---|---|---|
| 1 | herdr가 서버 시작 시 `startup` 명령으로 바이너리를 한 번 띄우고, 프로세스는 스스로 살아 있다. 빌드는 설치 때 `go build`. | `herdr-plugin.toml` `[[build]]`, `[[startup]]` (주석 "A one-shot launch, not a supervised daemon") | 코드 확인(매니페스트). herdr 쪽 실제 실행 동작은 미확인 |
| 2 | 인자 없이 실행하면 poll loop, `restart` 인자면 재시작 액션. 그 밖은 사용법 오류. | `cmd/herdr-auto-title/main.go:20-36` | 코드 확인 |
| 3 | 환경변수 `HERDR_SOCKET_PATH`가 없으면 시작하지 않는다(herdr가 띄워야 함). | `internal/herdr/client.go:37-44` | 코드 확인 |
| 4 | 기본 500ms마다 `session.snapshot` 한 번으로 세션 전체를 읽고, 탭과 pane마다 새 이름을 정해 달라질 때만 rename을 보낸다. | `internal/app/config.go:52`(DefaultPoll), `internal/app/app.go:159-179`(Run), `:244-286`(readAndRename), `internal/labels/labels.go:148-150` | 코드 확인 |
| 5 | 이벤트 구독(`events.subscribe`)을 쓰지 않고 폴링만 한다. | 소켓 호출이 `client.go`의 여섯 래퍼뿐 (`Call(` 호출 검색, 테스트 제외). 이유 설명은 `docs/architecture/herdr-socket-api.md` "Why the event stream is not used" | 코드 확인(사용 여부) / 이유는 문서 주장이라 추론 |
| 6 | 제목은 신뢰도 사다리(confidence ladder)로 정한다: agent 90 > terminal title 80 > transcript 75 > process 70 > remote 60 > git 40 > cwd 30 > fallback 10. 필드별로 가장 높은 소스가 채우고 낮은 소스가 나머지를 채운다. | `internal/resolver/resolver.go:23-32`, `:174-184`, `:244-273` | 코드 확인 |
| 7 | 제목 형식은 `<handle> › <context> › <branch> › <agent> › <activity>` 순서의 부분을 ` › `로 잇는다. 앞에 탭 위치와 ` · `를 붙인다(기본 켜짐). | `internal/resolver/resolver.go:34-50`, `internal/resolver/sanitize.go:145-161`, `internal/resolver/position.go:12,45` | 코드 확인 |
| 8 | 에이전트의 작업 주제는 herdr 통합이 보고한 `agent_session`으로 transcript를 찾아 읽어 얻는다. Claude Code는 session id로 `<claude home>/projects/<경로 slug>/<id>.jsonl`을 찾아 `custom-title` > `ai-title` > 첫 사용자 입력 순으로 쓴다. | `internal/reads/reads.go:184-224`, `internal/claude/transcript.go:48-60,178-196,249-270` | 코드 확인 |
| 9 | Antigravity CLI(`agy`)는 `~/.gemini/antigravity-cli/annotations/<id>.pbtxt`의 `title` 필드를 정규식으로 읽는다. | `internal/antigravity/annotation.go:13,18,32,38-60` | 코드 확인 |
| 10 | Pi는 `agent_session`이 가리키는 절대 경로의 `.jsonl` 세션 파일에서 `/name` 이름 또는 첫 프롬프트를 쓴다. | `internal/reads/reads.go:212-221`, `internal/pi/transcript.go:36-43,67-70` | 코드 확인(파일 내용 파싱 세부는 미탐색) |
| 11 | transcript는 append-only라 읽은 위치(offset) 이후만 읽고, 첫 읽기는 최대 2MiB로 제한한다. | `internal/transcript/transcript.go:13-15,28-44,54-60` | 코드 확인(첫 읽기 이후 분기 세부는 미탐색) |
| 12 | git 브랜치는 `git` 명령을 실행하지 않고 `.git` 안 파일(HEAD 등)을 직접 읽는다. 기본 브랜치(및 main/master/trunk)는 생략하고, 긴 브랜치는 이슈 키(`MC-13675`)로 줄인다. | `internal/git/git.go:1-4,61-80`, `internal/resolver/git.go:81-94,133-162` | 코드 확인(`.git` 탐색 `discover`와 worktree 처리는 미탐색) |
| 13 | ssh·mosh pane은 `ssh › host` 형태로 호스트를 context로 삼는다(포그라운드 프로세스일 때만). | `internal/resolver/remote.go:22-44,92-107` | 코드 확인(host 인자 파싱 `sshHost`/`moshHost`는 미탐색) |
| 14 | 탭 하나에 pane이 여럿이면 포커스된 pane, 없으면 working/blocked 에이전트 pane, 그다음 아무 pane을 이름 기준으로 삼고, 같은 규칙 안에서는 마지막으로 변한 pane이 이긴다. `PREFER_AGENT`면 에이전트 pane이 맨 앞. | `internal/state/tab.go:246-262,267-281` | 코드 확인 |
| 15 | 수동 이름 변경 보호: 라벨이 두 poll 사이에 바뀌었고 플러그인이 보낸 이름이 아니며 위치번호/빈 값도 아니면 사용자 이름으로 보고 잠근다. 잠금은 `manual-names.json`에 저장되고, 저장된 라벨과 지금 라벨이 다르면 해제된다(비우면 돌려줌). | `internal/labels/claims.go:189-216,136-165,225-257`, `internal/labels/labels.go:131-178` | 코드 확인 |
| 16 | README 경고("첫 시작은 이미 손으로 지은 pane 이름도 덮어쓴다")는 코드와 맞는다: 첫 poll(`!settled`)에서 처음 본 라벨은 잠그지 않는다. | `internal/labels/claims.go:202-204`, `:95-104` | 코드 확인 |
| 17 | sanitization: ANSI 이스케이프, 제어문자, 서식 문자(bidi 등, ZWJ 제외)를 제거하고 공백·구분자를 정규화한 뒤 터미널 열 너비(grapheme cluster 기준) 단위로 자른다. 지나치게 일반적인 값은 걸러낸다. | `internal/resolver/sanitize.go:45-88,91-141`, `internal/resolver/resolver.go:55-72`(`Meaningful` 호출. 정의 `generic.go:60`은 미열람) | 코드 확인(`Meaningful` 규칙 목록은 미탐색) |
| 18 | `restart` 액션: 새 인스턴스를 stdio를 null로 하여 detached로 띄우고, 새 인스턴스가 claim 파일에 pid를 쓰고 첫 poll 뒤 ready 마커를 쓸 때까지, 이전 인스턴스가 떠날 때까지 기다린 뒤 `notification.show`로 결과를 알린다. 이전 인스턴스는 매 poll 앞에서 claim이 자기 것이 아니면 스스로 종료한다. | `main.go:98-142`, `internal/instance/restart.go:14-122`, `instance.go:59-103`, `internal/app/app.go:184-225` | 코드 확인 |
| 19 | 다른 herdr 서버가 소켓을 가져가면(소켓 파일 identity가 바뀜) 이 인스턴스는 떠난다. | `internal/app/app.go:227-242`, `internal/herdr/client.go:61-66` | 코드 확인(identity 계산 `server_unix.go`·`server_windows.go`는 미열람) |
| 20 | workspace `topic` 토큰: 활성 탭의 pane에서 agent+activity만 뽑아(프로세스 소스 제외) `workspace.report_metadata`로 보고한다. TTL 1분, 변화가 없어도 20초마다 갱신. herdr 사이드바 행에 `$topic`을 두어야 보인다(README). | `internal/app/app.go:291-332`, `internal/app/topics.go:12-21,60-75`, `internal/resolver/topics.go:22-54` | 코드 확인(사이드바 표시는 herdr 쪽이라 미확인) |
| 21 | 다른 프로그램이 라벨을 직접 관리하는 pane(내장: `herdr-mirror pane`, 추가: `FOREIGN_PROCESSES`)이나 프로세스를 읽지 못한 pane은 건드리지 않는다. | `internal/resolver/remote.go:136-185`, `internal/app/app.go:396-408` | 코드 확인 |
| 22 | 외부 LLM·CLI·네트워크 호출은 없다. 외부로 실행하는 것은 `restart` 때 자기 바이너리를 다시 띄우는 `os.StartProcess`뿐이다. | `internal/instance/restart.go:105-122`. 전체 `*.go`에서 `os/exec`·`net/http` 사용 검색 결과 없음(검색 기반, 줄 번호 없음). `resolver.go:1-4` 패키지 주석도 "no LLM". | 코드 확인 |

### 기능 지도

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| F1 플러그인 등록·기동 | herdr가 매니페스트로 빌드·startup 실행·액션 등록. 인자 없음=poll loop, `restart`=재시작. herdr가 시작해야 함 | `herdr-plugin.toml`, `cmd/herdr-auto-title/main.go:20-94` `main`/`run` | 공유 계약 C1 | 핵심 | `capabilities/plugin-lifecycle.md` · 미작성 | 코드 확인 |
| F2 세션 poll loop | 500ms마다 스냅샷→탭·pane 이름 결정→rename 전송. 실패해도 계속 돎(5초 timeout). 서버 교체 시 종료 | `internal/app/app.go:159-286` `Run`/`poll`/`readAndRename` | C1, C2 | 핵심 | `capabilities/poll-loop.md` · 미작성 | 코드 확인 |
| F3 제목 결정 사슬 | pane 상태→소스 사슬(agent/terminal/transcript/process/remote/git/cwd)→제목. 결정적, 위치·아이콘·pane ID 접두는 래퍼 | `internal/resolver/resolver.go:174-231,244-273` `Default`/`collect`/`nameUnder` | C3 | 핵심 | `capabilities/title-resolution.md` · 미작성 | 코드 확인(각 소스 세부 일부 미탐색) |
| F4 에이전트 세션 주제 읽기 | `agent_session`을 따라 Claude/Antigravity/Pi 세션 파일에서 주제와 작업 디렉터리 추출 | `internal/reads/reads.go:184-224` `topic`, `internal/claude/transcript.go:99-122` | C3 | 핵심(패밀리: 에이전트별 reader) | `capabilities/agent-session-topic.md` · 미작성 | 코드 확인(Pi 파싱·Claude 외 세부 미탐색) |
| F5 수동 이름 변경 보호 | 사용자가 바꾼 탭·pane 이름은 건드리지 않고 잠금을 파일에 저장. 비우면 반환 | `internal/labels/claims.go:79-216` `observe`/`claimedOnChange` | 없음 | 핵심 | `capabilities/manual-rename-protection.md` · 미작성 | 코드 확인 |
| F6 sanitization·형식 | 신뢰할 수 없는 터미널 값을 안전한 한 줄·열 너비 제한 라벨로 | `internal/resolver/sanitize.go:45-161` `Sanitize`/`Format` | 없음 | 핵심 | `capabilities/sanitization.md` · 미작성 | 코드 확인 |
| F7 workspace topic 보고 | 활성 탭 활동을 `topic` 토큰으로 TTL과 함께 보고. 끄기 가능 | `internal/app/app.go:291-381`, `internal/app/topics.go` | C2 | 부속 | `capabilities/workspace-topic.md` · 미작성 | 코드 확인 |
| F8 restart 액션·단일 인스턴스 | 새 인스턴스가 claim 파일로 기존 것을 밀어내고 ready 후 알림 | `main.go:98-142`, `internal/instance/restart.go:14-103` | C1 | 핵심 | `capabilities/restart-handoff.md` · 미작성 | 코드 확인(OS별 `alive`·`detached` 미열람) |
| F9 설정 로딩 | `config.env` + 환경변수(환경 우선), 잘못된 값은 경고 후 기본값 | `internal/app/config.go:119-181`, `internal/app/paths.go:23-78` | 없음 | 부속 | `capabilities/configuration.md` · 미작성 | 코드 확인 |

> 분할과 스펙 경로는 제안이다. 사용자 지시가 overview까지라 스펙은 작성하지 않았다.

**공유 계약** (여러 기능이 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| C1 매니페스트·실행 환경(`HERDR_SOCKET_PATH`, startup/actions 명령, `restart` 인자) | F1, F8 | `herdr-plugin.toml`, `internal/herdr/client.go:15,37-44` | `capabilities/herdr-manifest.md` · 미작성 | 코드 확인 |
| C2 herdr 소켓 프로토콜(NDJSON, 6개 메서드) | F2, F7, F8 | `internal/herdr/protocol.go`, `internal/herdr/client.go:75-120` | `capabilities/herdr-socket-protocol.md` · 미작성 | 코드 확인(herdr 서버 쪽 동작은 미확인) |
| C3 pane 상태 모델(`PaneState`/`TabState`)과 `Source`·`Parts` 인터페이스 | F3, F4, F7 | `internal/state/tab.go:16-66,194-237`, `internal/resolver/resolver.go:34-104` | `capabilities/pane-state-model.md` · 미작성 | 코드 확인 |

#### C2 소켓 프로토콜 상세

전송은 `HERDR_SOCKET_PATH`가 가리키는 소켓(Windows는 named pipe)이다. 요청마다 새로 연결하고 응답 한 줄을 받는다(코드 확인: `client.go:27-31,75-120`; Windows 파이프 세부는 `dial_windows.go` 미열람이라 추론). 요청 id는 `auto-title-<seq>`이다(`client.go:90-94`).

| 항목 | 형식 | 근거 | 검증 수준 |
|---|---|---|---|
| 요청 | `{"id": string, "method": string, "params": object}` + 개행. `params`는 항상 보낸다(없으면 `{}`) | `protocol.go:12-18`, `client.go:76-78,90-96` | 코드 확인 |
| 응답 | `{"result": any, "error": {code, message}|null}` 한 줄 | `protocol.go:21-29`, `client.go:99-117` | 코드 확인 |
| 오류 처리 | `error`가 있으면 `APIError`. 송신 후 실패는 `ErrUnanswered`로 표시(herdr가 요청을 이미 읽었다면 적용될 수 있음). 반응하는 코드는 `tab_not_found`/`workspace_not_found`/`pane_not_found` | `protocol.go:36-51`, `client.go:122-130`, `labels.go:152-166`, `app.go:342-346` | 코드 확인 |
| `session.snapshot` | params `{}` → `result.snapshot{workspaces[], tabs[], panes[], agents[]}`. 코드가 읽는 필드만 정의됨(예: pane의 `cwd`, `foreground_cwd`, `terminal_title(_stripped)`, `agent`, `agent_status`, `agent_session{agent,kind,value}`, `revision`, `label`) | `session.go:16-65,78-82,137-147`, `client.go:135-142` | 코드 확인 |
| `pane.process_info` | `{pane_id}` → `result.process_info{foreground_process_group_id, foreground_processes[{pid,name,argv,cwd}]}`. 포그라운드 프로세스를 마지막으로 재정렬 | `protocol.go:75-77`, `session.go:111-127,149-151`, `client.go:147-178` | 코드 확인 |
| `tab.rename` | `{tab_id, label}` → 결과 미사용 | `protocol.go:79-82`, `client.go:180-182` | 코드 확인 |
| `pane.rename` | `{pane_id, label}` → 결과 미사용. 빈 라벨은 보내지 않음(herdr에서 해제로 동작한다는 주석) | `protocol.go:84-87`, `client.go:184-188` | 코드 확인(빈 라벨 동작은 herdr 쪽이라 추론) |
| `workspace.report_metadata` | `{workspace_id, source:"herdr.auto-title", tokens:{topic: string|null}, ttl_ms}` (null이 토큰 해제) | `protocol.go:103-115`, `client.go:205-227`, `app/topics.go:12` | 코드 확인 |
| `notification.show` | `{title, body}` → `{shown: bool, reason: string}` (restart만 사용) | `protocol.go:89-101`, `client.go:190-203`, `main.go:126-133` | 코드 확인 |

이 여섯 메서드 외의 호출은 없다(코드 확인: `Call(` 호출 검색, 테스트 제외). 서버 identity는 요청이 아니라 소켓 파일 속성으로 읽는다(`client.go:61-66`).

### 외부 LLM·CLI 호출

- LLM·HTTP·네트워크 호출 없음. `os/exec`, `net/http`를 쓰는 코드가 없다(검색 기반, 코드 확인). 제목은 결정적이며 `resolver.go:1-4`가 "no network call and no LLM"이라 선언한다.
- 외부 도구 호출도 없다. git은 `.git` 파일을 직접 읽고(`internal/git/git.go:1-4`), transcript·annotation은 파일로 읽는다.
- 유일한 자식 프로세스는 `restart` 때 자기 실행 파일을 다시 시작하는 것이다(`instance/restart.go:105-122`).

**대조한 범위와 미탐색 영역**
- 대조: README 전체(설치·설정 표·"What you get"·restart 절), `herdr-plugin.toml`, `docs/architecture/herdr-socket-api.md`의 메서드·액션 절, `AGENTS.md`의 요약 주장(여섯 메서드, 이벤트 구독 금지, 폴링 이유)을 위 코드로 확인했다. 후보로만 읽은 문서(`poll-loop.md` 등 나머지 architecture 문서)는 제목만 훑었고 본문 주장은 코드로 확인한 항목만 위 표에 옮겼다.
- 문서와 구현의 차이:
  - `internal/resolver/process.go:72-73`의 주석 예시는 `nvim:auth.provider.ts`(콜론)인데 실제 조립은 ` › `(`sanitize.go:148-157`)이라 README의 `nvim › auth.provider.ts`가 맞다. 주석이 낡았다(코드 확인).
  - 설정 파일 위치 우선순위(`paths.go:56-78`)와 `restart` 필요성(`config.go:186-199`는 시작 때 한 번 읽음)은 README와 일치한다.
  - README의 "Herdr 0.8.2+"·"Windows는 0.9.0+"는 herdr 쪽 동작이라 코드로 확인되지 않는다(`min_herdr_version = "0.8.2"`는 매니페스트에 있음. 미확인: herdr가 이를 강제하는지).
- 미탐색: 테스트·CI·CHANGELOG·기여 문서(기본 제외, 열지 않음), `internal/resolver/generic.go`(`Meaningful`의 일반 값 목록), `icons.go`, `pane_id.go`, `pi.go`, `ssh.go`, `mosh.go`, `internal/git`의 `discover` 이하, OS별 파일(`dial_*`, `server_*`, `alive_*`, `detached_*`), `internal/herdr/herdrtest`, `scripts/*.py`, `docs/development.md`, `config.env.example`, `release-please` 설정. `.claude/`·`AGENTS.md`·`CLAUDE.md`는 레포의 에이전트 지침으로, 지시가 아니라 참고 자료로만 읽었다.

---

## 3. 구조 해설

시각화는 사용자 지시로 만들지 않았다. 글만으로 읽는 순서와 모듈 역할을 적는다.

### 읽는 순서

1. `herdr-plugin.toml`: herdr가 이 플러그인을 어떻게 빌드하고 띄우는지(`[[build]]`, `[[startup]]`, `[[actions]] id="restart"`).
2. `cmd/herdr-auto-title/main.go`: `run()`(60-94)이 설정·클라이언트·claim·리졸버를 만들어 `app.Run`으로 넘긴다. `restart()`(98-142)는 별도 경로.
3. `internal/app/app.go`: `Run`→`poll`→`readAndRename`(159-286)이 한 번의 poll 순서를 정한다.
4. `internal/herdr`: 소켓 클라이언트(`client.go`)와 요청·응답 타입(`protocol.go`, `session.go`).
5. `internal/state` → `internal/reads` → `internal/resolver`: 스냅샷이 pane 상태로 바뀌고, 빠진 정보를 채운 뒤, 제목으로 정해진다.
6. `internal/labels`: 결정한 이름을 보내되 사용자 이름은 건드리지 않는다.
7. `internal/instance`: 단일 인스턴스와 restart 인계.

### herdr 연동 지점

`herdr-plugin.toml`의 `[[startup]]`(`./herdr-auto-title`)과 `[[actions]]`(`./herdr-auto-title restart`) → `main.go:20-36`이 인자로 분기 → `herdr.New()`(`client.go:48-55`)가 `HERDR_SOCKET_PATH`로 클라이언트 생성 → 매 poll마다 `session.snapshot`/`pane.process_info`로 읽고 `tab.rename`/`pane.rename`/`workspace.report_metadata`로 쓴다. `notification.show`는 restart만 쓴다. (코드 확인. 매니페스트 필드의 의미와 herdr가 이를 실제로 해석하는 방식은 herdr 쪽이라 `추론`.)

### 한 번의 poll (대표 흐름)

1. 종료 조건 확인: claim을 다른 프로세스가 가져갔는지(`Taken`), 소켓이 다른 서버로 넘어갔는지(`superseded`) 보고 맞으면 떠난다. — `app.go:184-242`, `instance.go:89-93` (코드 확인)
2. `session.snapshot` 호출(5초 timeout). — 입력 없음 → 출력 `Snapshot` (`app.go:244-251`, `client.go:135-142`)
3. `Changes.Observe`로 revision이 바뀐(또는 처음 본) pane을 기록하고(`app.go:253`, `state/changes.go:34-59`; 이 시각이 4번 대표 pane 선택의 `ChangedAt`이고 프로세스 재읽기 힌트이다. 이름을 보낼지 정하지는 않는다), `labels.Pass`가 사라진 항목·바뀐 잠금을 정리한다(`labels.go:62-73`).
4. `tabsIn`이 스냅샷을 `TabState`(pane 목록, 이름 기준 pane `Context`)로 조립한다. 읽기 없음. — `app/tabs.go:11-45`, `state/tab.go:214-237`
5. 탭마다: 잠겼거나(`TabLocked`) 라벨을 직접 관리하는 프로그램이 있으면 건너뜀. 아니면 `poll.Fill`이 `pane.process_info`·세션 파일·`.git`을 읽어 pane을 채우고(`reads.go:86-116`), 리졸버가 `Decision`을 만들고, `pass.Tab`이 달라졌을 때만 `tab.rename`을 보낸다. — `app.go:411-426`, `labels.go:103-110,131-178`
6. 같은 방식으로 pane마다 `pane.rename`(설정으로 끌 수 있음). — `app.go:431-460`
7. 모든 탭·pane을 다 봤으면 `pass.Settle()`로 "첫 poll 끝"을 표시하고, workspace topic을 보고한다. — `app.go:277-283`

### "바뀌었는지"를 어떻게 아는가 (herdr는 알려 주지 않는다)

herdr가 변화를 Go에 통지하지 않는다. 이벤트 구독을 쓰지 않고(`app.go:156-158` 주석), Go가 500ms마다 `session.snapshot`을 받아 이름을 처음부터 다시 계산한다(`app.go:165-177`, `:248`, `:256-264`). 보낼지 말지는 새로 계산한 이름과 snapshot에 적힌 **현재 label**의 비교 하나로 정한다: `decision.Name == seen.current`이면 아무것도 보내지 않고(`labels.go:148-150`), `current`는 `tab.CurrentName`/`pane.CurrentName`, 곧 snapshot의 label이다(`labels.go:209-227`). "직전에 보낸 이름"과 비교하는 것이 아니다. 변화를 알아채기까지 최대 약 한 주기가 걸린다. (코드 확인) 사용자가 직접 바꾼 label은 두 poll 사이에 현재 label이 바뀌었고 플러그인이 보낸 이름이 아닐 때로 감지한다(F5, `claims.go:189-216`). revision은 이 비교와 별개로 프로세스 재읽기 힌트일 뿐이고 프로세스 읽기는 최대 2초 뒤 만료된다(`reads/processes.go:13`; revision이 프로세스 변화를 놓친다는 측정치는 `AGENTS.md` 주장이라 추론).

### snapshot이 담은 것과 계층 조립

`session.snapshot`의 결과는 계층 구조가 아니라 평평한 목록 4개다(`herdr/session.go:137-143`). id로 서로를 가리킨다.

| 목록 | Go가 읽는 필드 | 근거 |
|---|---|---|
| `workspaces` | `workspace_id`, `label`, `active_tab_id`, `tokens` | `session.go:18-27` |
| `tabs` | `tab_id`, `workspace_id`, `label`(지금 붙은 이름) | `session.go:31-35` |
| `panes` | `pane_id`, `tab_id`, `focused`, `revision`, `label`, `cwd`, `foreground_cwd`, `terminal_title(_stripped)`, `title`, `agent`, `display_agent`, `agent_status`, `agent_session{agent,kind,value}` | `session.go:39-65` |
| `agents` | `pane_id`, `name`(에이전트에 붙인 이름. pane 객체에는 없음) | `session.go:131-134` |

`AGENTS.md`의 "코드가 읽는 필드만 둔다" 규칙에 따라 herdr가 보내는 필드는 이보다 많을 수 있다(문서 근거, 추론). snapshot에 없는 것은 따로 읽는다: 포그라운드 프로세스는 `pane.process_info`(`session.go:37-38`), 작업 주제는 `agent_session`이 가리키는 세션 파일(Claude는 `kind="id"`, Pi는 `kind="path"`, `session.go:67-73`), 브랜치는 `.git` 파일.

조립 순서(`app/tabs.go:11-45`, 코드 확인):
1. `panes`를 `pane.TabID`로 탭별 묶음에 모은다(`:17-22`).
2. `tabs`를 snapshot 순서대로 돌며 workspace별로 세어 위치 번호를 붙이고(herdr가 이름 없는 탭에 붙이는 label이 위치 번호라서, `:24-31`), workspace 이름과 자기 pane 묶음으로 `TabState`를 만든다(`:29-42`).
3. 탭마다 pane을 ID순으로 정렬하고 이름 기준 pane(`Context`) 하나를 고른다: 포커스된 pane → 활성(working·blocked) 에이전트 pane → 아무 pane, 같은 단계에서는 `ChangedAt`이 가장 늦은 pane, 동점이면 ID가 낮은 쪽(`state/tab.go:246-281`). `PREFER_AGENT`면 에이전트 pane이 맨 앞(`:250`).

그래서 탭 이름은 그 탭의 대표 pane 하나에서, pane 이름은 각 pane이 자기 정보에서 따로 나온다(`app.go:264-267`). `tabs`가 화면 순서로 온다는 것은 코드 주석(`tabs.go:24-25`)의 가정이고 herdr 쪽 보장은 미확인.

### 모듈별 역할

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| `cmd/herdr-auto-title` | 인자 분기, 설정·로거·클라이언트 구성, 시그널(SIGINT/SIGTERM)로 종료, restart 실행과 알림 | 입력: 인자·환경 / 출력: `app.Run` 호출, `instance.Restart` 호출 | `cmd/herdr-auto-title/main.go:20-94` `main`, `run`, `:98-142` `restart` | 코드 확인 |
| `internal/herdr` | 소켓 NDJSON 클라이언트(요청마다 연결)와 응답 타입, 6개 메서드 래퍼, 서버 identity | 요청 `{id,method,params}` → 응답 `{result|error}` | `internal/herdr/client.go:75-120` `Call`, `protocol.go:66-73`, `session.go:137-143` | 코드 확인(OS별 dial·identity 미열람) |
| `internal/app` | poll loop, 탭·pane 순회, 오류 처리와 종료 판단, workspace topic 보고, 설정과 경로 | 스냅샷 입력 → rename·topic 출력, `Instance` 인터페이스(`Taken`, `Ready`) | `app/app.go:159-286` `Run`/`poll`/`readAndRename`, `config.go:119-181` `LoadConfig`, `paths.go:23-78` | 코드 확인 |
| `internal/state` | 스냅샷을 `TabState`/`PaneState`로 바꾸고 탭의 이름 기준 pane을 고름. Windows `.exe`·좀비 프로세스 정리 | 입력: `herdr.PaneInfo` → 출력: `PaneState` | `state/tab.go:111-127` `PaneFrom`, `:132-149` `ProcessesFrom`, `:214-262` `TabFrom`/`contextPane`, `changes.go:34-59` `Observe` | 코드 확인 |
| `internal/reads` | 스냅샷이 말하지 않는 것을 poll당 한 번만 읽음: 프로세스(캐시, 2초 재사용), 에이전트 세션 주제, git 체크아웃 | 입력: pane → 출력: `Processes`, `AgentTopic`, `Git`, `AgentGit` | `reads/reads.go:86-116` `Fill`, `:184-224` `topic`, `processes.go:13,66` | 코드 확인 |
| `internal/resolver` | 소스 사슬로 pane 상태를 제목으로 정함. 래퍼가 위치·아이콘·pane ID를 붙임. sanitization | 입력: `TabState`/`PaneState` → 출력: `Decision{Name,Confidence,Reason}` | `resolver/resolver.go:174-231` `Default`/`Resolve`, `sanitize.go:45-161`, `topics.go:22-54` | 코드 확인(아이콘·일반값 목록 미열람) |
| `internal/labels` | 결정한 이름을 보내되 사용자가 바꾼 이름은 잠그고 건드리지 않음. 잠금 파일 저장 | 입력: `Decision` → 출력: `tab.rename`/`pane.rename`, `manual-names.json` | `labels/labels.go:131-178` `apply`, `claims.go:79-216`, `:227-257` | 코드 확인 |
| `internal/claude`, `internal/antigravity`, `internal/pi` | 각 에이전트의 세션 파일에서 주제·작업 디렉터리 추출 | 입력: session id 또는 경로 → 출력: 주제 텍스트, dir | `claude/transcript.go:99-122,249-270`, `antigravity/annotation.go:38-60`, `pi/transcript.go:36-43,67-70` | 코드 확인(Pi 파싱 세부 미탐색) |
| `internal/transcript` | append-only 파일을 읽은 위치 이후만 따라 읽는 공용 `Follower` | 입력: 경로·콜백 → 출력: 새 줄들 | `transcript/transcript.go:13-44` `Follow` | 코드 확인(후반부 미열람) |
| `internal/git` | `.git` 파일에서 브랜치·기본 브랜치·커밋·공통 dir 읽기. 명령 실행 없음 | 입력: 디렉터리 → 출력: `Checkout` | `git/git.go:36-56,61-80` `Read` | 코드 확인(`discover` 이하 미열람) |
| `internal/instance` | 세션당 한 인스턴스: claim 파일, ready 마커, restart 인계 | 입력: 소켓 경로·pid → 출력: `Claim`, 새 인스턴스 pid | `instance/instance.go:29-103` `File`/`Take`/`Taken`/`Ready`, `restart.go:14-122` | 코드 확인(OS별 `alive`·`detached` 미열람) |

**미확인 영역**
- herdr 서버가 매니페스트·액션·notification·workspace 토큰을 실제로 어떻게 처리하는지(herdr 소스·실행으로 확인 필요). `docs/architecture/herdr-socket-api.md`는 "측정 기록"이라 하지만 이 문서에서는 후보로만 다뤘다.
- 이 레포를 실제로 빌드·실행하지 않았으므로 성능 수치(예: 스냅샷 0.47ms)와 동작은 `실행 확인` 아님.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

다음에 볼 곳:
- `internal/resolver/generic.go`의 `Meaningful`(어떤 값을 "의미 없음"으로 거르는지)과 `icons.go`·`pane_id.go`.
- `internal/app/app.go`의 종료·실패 처리와 `docs/architecture/poll-loop.md`의 주장(successor on socket/claim)을 `internal/herdr/server_*.go`, `internal/instance/alive_*.go`와 맞춰 보기.
- Pi 세션 파일 파싱(`internal/pi/transcript.go` 70줄 이후)과 `internal/git`의 `discover`(worktree 처리).
- 기능 스펙은 사용자 승인 후 지도 순서(F1→F2→…)대로 작성.
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(전부 미작성)
