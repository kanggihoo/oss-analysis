# Open Design Windows native 실행 시 CLI 감지 트러블슈팅

## 요약

Windows PowerShell에서 `pnpm tools-dev run web`로 Open Design을 소스 실행할 때, `codex`, `claude`, `gemini` 같은 로컬 agent CLI가 UI에 보이지 않는 문제가 있었다.

이번 확인에서 중요한 결론은 다음과 같다.

- Docker 실행은 호스트 Windows PATH를 볼 수 없으므로 별도 문제다.
- 소스 직접 실행은 daemon 프로세스가 받은 PATH를 기준으로 CLI를 찾는다.
- Windows에서는 npm 전역 설치 CLI가 실제 바이너리라기보다 `*.cmd` shim으로 잡힌다.
- `where.exe codex`가 보이더라도 Open Design이 실행 중인 repo의 `.od/app-config.json`에 agent별 `*_BIN` 설정이 없으면 감지가 흔들릴 수 있다.
- `tools-dev`는 실행할 때마다 web/daemon 포트를 새로 잡을 수 있으므로, 항상 터미널에 출력된 최신 `Daemon` URL로 `/api/agents`를 확인해야 한다.

## 확인된 환경

작업 중 확인된 Windows npm 전역 prefix:

```powershell
npm config get prefix
# C:\nvm4w\nodejs

npm root -g
# C:\nvm4w\nodejs\node_modules
```

CLI shim 위치:

```powershell
where.exe codex
# C:\nvm4w\nodejs\codex
# C:\nvm4w\nodejs\codex.cmd

where.exe claude
# C:\nvm4w\nodejs\claude
# C:\nvm4w\nodejs\claude.cmd

where.exe gemini
# C:\nvm4w\nodejs\gemini
# C:\nvm4w\nodejs\gemini.cmd
```

`C:\nvm4w\nodejs\codex.cmd`는 npm이 만든 wrapper이며, 내부적으로 다음 JS entry를 실행한다.

```text
C:\nvm4w\nodejs\node_modules\@openai\codex\bin\codex.js
```

즉 Open Design이 실행할 안정적인 경로는 `codex`라는 bare command보다 `C:\nvm4w\nodejs\codex.cmd` 같은 절대경로다.

## 증상

다음처럼 소스 실행은 정상처럼 보인다.

```powershell
pnpm tools-dev run web
```

출력 예:

```text
Open Design dev server ready

  Web:    http://127.0.0.1:50148/
  Daemon: http://127.0.0.1:59633/
```

브라우저에서 `Web` URL로 접속하면 UI는 열리지만, Settings 또는 Execution mode에서 Codex/Claude/Gemini 같은 CLI 도구가 보이지 않거나 unavailable로 보일 수 있다.

## 핵심 원인 후보

### 1. 다른 repo의 `.od`를 보고 있음

이번 세션에서는 두 위치가 섞였다.

```text
C:\Users\SSAFY\Desktop\oss-analysis\open-design
C:\Users\SSAFY\Desktop\open-design
```

Open Design 런타임 설정은 각 repo root의 `.od/app-config.json`에 저장된다. 한쪽 repo에 설정을 넣어도, 다른 repo에서 `pnpm tools-dev run web`을 실행하면 적용되지 않는다.

### 2. PATH는 보이지만 Open Design 설정에는 binary override가 없음

PowerShell에서 `where.exe codex`가 성공하는 것과 Open Design daemon이 agent별 실행 경로를 안정적으로 사용하는 것은 별개다.

Open Design 코드상 agent CLI override는 `.od/app-config.json`의 `agentCliEnv`에 저장된다. 예를 들어 Codex는 `CODEX_BIN`, Claude는 `CLAUDE_BIN`, Gemini는 `GEMINI_BIN`을 사용할 수 있다.

### 3. web 포트와 daemon 포트를 혼동함

`tools-dev run web` 출력에는 두 URL이 있다.

```text
Web:    브라우저 UI 주소
Daemon: API 서버 주소
```

UI 접속은 `Web` 포트로 한다. CLI 감지 결과 확인은 `Daemon` 포트의 `/api/agents`를 호출해야 한다.

### 4. 이전 daemon/web 프로세스 또는 이전 포트를 보고 있음

`tools-dev run web`은 기본적으로 빈 포트를 잡는다. 종료 후 다시 실행하면 포트가 바뀔 수 있다.

이전 실행에서 출력된 `Daemon` 포트로 `/api/agents`를 확인하면 연결 실패가 나거나, 다른 프로세스 상태를 보고 오판할 수 있다.

## 해결: 실행 중인 repo의 `.od/app-config.json`에 CLI 경로 고정

실제로 `pnpm tools-dev run web`을 실행하는 repo root에 다음 파일을 만든다.

경로 예:

```text
C:\Users\SSAFY\Desktop\open-design\.od\app-config.json
```

내용:

```json
{
  "agentCliEnv": {
    "codex": {
      "CODEX_BIN": "C:\\nvm4w\\nodejs\\codex.cmd",
      "CODEX_HOME": "C:\\Users\\SSAFY\\.codex"
    },
    "claude": {
      "CLAUDE_BIN": "C:\\nvm4w\\nodejs\\claude.cmd"
    },
    "gemini": {
      "GEMINI_BIN": "C:\\nvm4w\\nodejs\\gemini.cmd"
    }
  }
}
```

주의할 점:

- 이 파일은 Open Design runtime data인 `.od/` 아래에 둔다.
- repo를 다른 경로에 clone했다면 그 repo의 `.od/app-config.json`에 다시 설정해야 한다.
- Windows JSON 문자열에서는 backslash를 `\\`로 escape해야 한다.
- `CODEX_HOME`은 Codex 설정/인증 홈을 명시하려는 경우에만 필요하지만, Windows에서는 함께 고정해 두는 편이 디버깅에 좋다.

## 재시작 절차

같은 repo root에서 실행한다.

```powershell
cd C:\Users\SSAFY\Desktop\open-design

pnpm tools-dev stop
pnpm tools-dev run web
```

출력된 최신 URL을 확인한다.

```text
Web:    http://127.0.0.1:<WEB_PORT>/
Daemon: http://127.0.0.1:<DAEMON_PORT>/
```

브라우저는 `Web` URL로 접속한다.

## 검증 명령

### 1. PowerShell에서 CLI가 보이는지 확인

```powershell
where.exe codex
where.exe claude
where.exe gemini
```

### 2. Open Design 설정 확인

터미널에 출력된 최신 `Daemon` 포트를 사용한다.

```powershell
Invoke-RestMethod http://127.0.0.1:<DAEMON_PORT>/api/app-config |
  ConvertTo-Json -Depth 8
```

`config.agentCliEnv`에 `CODEX_BIN`, `CLAUDE_BIN`, `GEMINI_BIN`이 들어 있어야 한다.

### 3. agent 감지 결과 확인

```powershell
$agents = Invoke-RestMethod http://127.0.0.1:<DAEMON_PORT>/api/agents
$agents.agents |
  Where-Object { $_.id -in @("claude", "codex", "gemini") } |
  Select-Object id, available, path, version
```

정상 예:

```text
id      available path                         version
--      --------- ----                         -------
claude       True C:\nvm4w\nodejs\claude.cmd   ...
codex        True C:\nvm4w\nodejs\codex.cmd    ...
gemini       True C:\nvm4w\nodejs\gemini.cmd   ...
```

### 4. tools-dev 상태 확인

```powershell
pnpm tools-dev status --json
```

`run web` 기준으로는 daemon과 web이 running이면 충분하다. desktop은 idle일 수 있다.

## UI에서 확인할 점

브라우저에서는 반드시 `Web` URL로 접속한다.

```text
http://127.0.0.1:<WEB_PORT>/
```

Settings 또는 Execution mode에서 Rescan을 누른다. 그래도 안 보이면 브라우저 cache 문제가 아니라 daemon API 결과를 먼저 봐야 한다.

```powershell
Invoke-RestMethod http://127.0.0.1:<DAEMON_PORT>/api/agents
```

이 API에서 `available: true`인데 UI에만 안 보이면 frontend 상태/캐시 문제다. API에서도 `available: false`이면 daemon의 실행 경로 또는 인증 문제다.

## Docker와의 차이

Docker Compose 실행은 이 문서의 해결책과 다르다.

Docker 컨테이너는 Windows 호스트의 다음 경로를 볼 수 없다.

```text
C:\nvm4w\nodejs\codex.cmd
```

따라서 Docker 기본 이미지에서 로컬 CLI를 쓰려면 다음 중 하나가 필요하다.

- BYOK/API 모드 사용
- 컨테이너 이미지 안에 agent CLI를 별도 설치
- 인증 파일/API key/설정 파일을 컨테이너 환경에 맞게 별도 주입

단순히 Windows 사용자 PATH에 CLI가 있다고 해서 Docker 컨테이너가 그 CLI를 인식하지는 않는다.

## 최종 판단

Windows native 소스 실행에서 CLI가 안 보이면 우선순위는 다음과 같다.

1. 지금 접속한 URL이 `tools-dev`가 출력한 최신 `Web` URL인지 확인한다.
2. 최신 `Daemon` URL의 `/api/agents`를 직접 호출한다.
3. 실행 중인 repo root의 `.od/app-config.json`에 `agentCliEnv`가 있는지 확인한다.
4. `CODEX_BIN`, `CLAUDE_BIN`, `GEMINI_BIN`을 `*.cmd` 절대경로로 고정한다.
5. `pnpm tools-dev stop` 후 새 PowerShell에서 다시 `pnpm tools-dev run web`을 실행한다.

이번 케이스에서는 `PATH`에 `C:\nvm4w\nodejs`가 이미 있었으므로, 핵심은 PATH 추가가 아니라 **실제 실행 repo의 `.od/app-config.json`에 agent CLI 절대경로를 저장하는 것**이었다.
