---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/06-configuration.md
order: 6
title: "Configuration"
---

# 구성

모든 명령에서 플래그를 반복하지 않고 지속적인 기본값을 설정하려면 `agent-browser.json` 파일을 만드세요.

## Config 파일 위치

agent-browser는 두 위치를 확인하며, 우선순위 순서로 병합합니다.

<table>
  <thead>
    <tr><th>우선순위</th><th>위치</th><th>범위</th></tr>
  </thead>
  <tbody>
    <tr><td>1(가장 낮음)</td><td><code>~/.agent-browser/config.json</code></td><td>사용자 수준 기본값</td></tr>
    <tr><td>2</td><td><code>./agent-browser.json</code></td><td>프로젝트 수준 재정의</td></tr>
    <tr><td>3</td><td><code>AGENT_BROWSER_*</code> env vars</td><td>config 값을 재정의</td></tr>
    <tr><td>4(가장 높음)</td><td>CLI flags</td><td>모든 항목을 재정의</td></tr>
  </tbody>
</table>

프로젝트 수준 값은 사용자 수준 값을 재정의합니다. 환경 변수는 둘 다 재정의합니다. CLI 플래그가 항상 우선합니다.

기본 위치 대신 특정 config 파일을 로드하려면 `--config <path>` 또는 `AGENT_BROWSER_CONFIG` 환경 변수를 사용하세요.

```bash
agent-browser --config ./ci-config.json open example.com
AGENT_BROWSER_CONFIG=./ci-config.json agent-browser open example.com
```

## Config 예시

```json
{
  "headed": true,
  "proxy": "http://localhost:8080",
  "profile": "./browser-data",
  "userAgent": "my-agent/1.0",
  "hideScrollbars": false,
  "ignoreHttpsErrors": true
}
```

IDE 자동 완성과 검증을 위한 [JSON Schema](https://agent-browser.dev/schema.json)를 사용할 수 있습니다. 활성화하려면 config 파일에 `$schema` 키를 추가하세요.

```json
{
  "$schema": "https://agent-browser.dev/schema.json",
  "headed": true
}
```

## 모든 옵션

전역 launch, 출력, provider, chat 옵션은 camelCase에 해당하는 이름을 사용해 config 파일에서 설정할 수 있습니다. `screenshot --full` 같은 명령 범위 플래그는 명령 인자로 남습니다.

<table>
  <thead>
    <tr><th>Config Key</th><th>CLI Flag</th><th>타입</th></tr>
  </thead>
  <tbody>
    <tr><td><code>headed</code></td><td><code>--headed</code></td><td>boolean</td></tr>
    <tr><td><code>json</code></td><td><code>--json</code></td><td>boolean</td></tr>
    <tr><td><code>debug</code></td><td><code>--debug</code></td><td>boolean</td></tr>
    <tr><td><code>session</code></td><td><code>--session</code></td><td>string</td></tr>
    <tr><td><code>sessionName</code></td><td><code>--session-name</code></td><td>string</td></tr>
    <tr><td><code>executablePath</code></td><td><code>--executable-path</code></td><td>string</td></tr>
    <tr><td><code>extensions</code></td><td><code>--extension</code></td><td>string[]</td></tr>
    <tr><td><code>initScripts</code></td><td><code>--init-script</code></td><td>string[]</td></tr>
    <tr><td><code>enable</code></td><td><code>--enable</code></td><td>string[]</td></tr>
    <tr><td><code>profile</code></td><td><code>--profile</code></td><td>string</td></tr>
    <tr><td><code>state</code></td><td><code>--state</code></td><td>string</td></tr>
    <tr><td><code>proxy</code></td><td><code>--proxy</code></td><td>string</td></tr>
    <tr><td><code>proxyBypass</code></td><td><code>--proxy-bypass</code></td><td>string</td></tr>
    <tr><td><code>args</code></td><td><code>--args</code></td><td>string</td></tr>
    <tr><td><code>userAgent</code></td><td><code>--user-agent</code></td><td>string</td></tr>
    <tr><td><code>provider</code></td><td><code>-p, --provider</code></td><td>string</td></tr>
    <tr><td><code>device</code></td><td><code>--device</code></td><td>string</td></tr>
    <tr><td><code>hideScrollbars</code></td><td><code>--hide-scrollbars</code></td><td>boolean</td></tr>
    <tr><td><code>ignoreHttpsErrors</code></td><td><code>--ignore-https-errors</code></td><td>boolean</td></tr>
    <tr><td><code>allowFileAccess</code></td><td><code>--allow-file-access</code></td><td>boolean</td></tr>
    <tr><td><code>cdp</code></td><td><code>--cdp</code></td><td>string</td></tr>
    <tr><td><code>autoConnect</code></td><td><code>--auto-connect</code></td><td>boolean</td></tr>
    <tr><td><code>annotate</code></td><td><code>--annotate</code></td><td>boolean</td></tr>
    <tr><td><code>colorScheme</code></td><td><code>--color-scheme</code></td><td>string(<code>dark</code>, <code>light</code>, <code>no-preference</code>)</td></tr>
    <tr><td><code>downloadPath</code></td><td><code>--download-path</code></td><td>string</td></tr>
    <tr><td><code>contentBoundaries</code></td><td><code>--content-boundaries</code></td><td>boolean</td></tr>
    <tr><td><code>maxOutput</code></td><td><code>--max-output</code></td><td>number</td></tr>
    <tr><td><code>allowedDomains</code></td><td><code>--allowed-domains</code></td><td>string[]</td></tr>
    <tr><td><code>actionPolicy</code></td><td><code>--action-policy</code></td><td>string</td></tr>
    <tr><td><code>confirmActions</code></td><td><code>--confirm-actions</code></td><td>string</td></tr>
    <tr><td><code>confirmInteractive</code></td><td><code>--confirm-interactive</code></td><td>boolean</td></tr>
    <tr><td><code>engine</code></td><td><code>--engine</code></td><td>string(<code>chrome</code>, <code>lightpanda</code>)</td></tr>
    <tr><td><code>screenshotDir</code></td><td><code>--screenshot-dir</code></td><td>string</td></tr>
    <tr><td><code>screenshotQuality</code></td><td><code>--screenshot-quality</code></td><td>number(0-100)</td></tr>
    <tr><td><code>screenshotFormat</code></td><td><code>--screenshot-format</code></td><td>string(<code>png</code>, <code>jpeg</code>)</td></tr>
    <tr><td><code>idleTimeout</code></td><td><code>--idle-timeout</code></td><td>string(<code>10s</code>, <code>3m</code>, <code>1h</code> 또는 원시 ms)</td></tr>
    <tr><td><code>noAutoDialog</code></td><td><code>--no-auto-dialog</code></td><td>boolean</td></tr>
    <tr><td><code>model</code></td><td><code>--model</code></td><td>string</td></tr>
    <tr><td><code>headers</code></td><td><code>--headers</code></td><td>string(JSON)</td></tr>
    <tr><td><code>plugins</code></td><td>(config only)</td><td>plugin config[]</td></tr>
  </tbody>
</table>

## 일반적인 구성

### 로컬 개발

```json
{
  "headed": true,
  "profile": "./browser-data"
}
```

### 프록시 뒤에서

```json
{
  "proxy": "http://proxy.corp.example.com:8080",
  "proxyBypass": "localhost,*.internal.com",
  "ignoreHttpsErrors": true
}
```

### CI / Devcontainer

```json
{
  "args": "--no-sandbox,--disable-gpu",
  "ignoreHttpsErrors": true
}
```

### iOS 테스트

```json
{
  "provider": "ios",
  "device": "iPhone 16 Pro"
}
```

### AI 에이전트 보안

```json
{
  "contentBoundaries": true,
  "maxOutput": 50000,
  "allowedDomains": ["your-app.com", "*.your-app.com"],
  "actionPolicy": "./policy.json"
}
```

## Boolean 옵션 재정의

Boolean 플래그는 config 설정을 재정의하기 위해 선택적 `true`/`false` 값을 받을 수 있습니다.

```bash
agent-browser --headed false open example.com
```

값 없이 플래그만 전달하는 것은 `true`를 전달하는 것과 같습니다.

```bash
agent-browser --headed open example.com       # same as --headed true
agent-browser --headed true open example.com  # explicit
```

이는 `--headed`, `--debug`, `--json`, `--ignore-https-errors`, `--allow-file-access`, `--hide-scrollbars`, `--auto-connect`, `--annotate`, `--content-boundaries`, `--confirm-interactive`, `--no-auto-dialog` 같은 boolean 플래그에 적용됩니다.

## Extensions 병합

사용자 수준 및 프로젝트 수준 config의 extensions는 대체되지 않고 **연결**됩니다. 예를 들어 `~/.agent-browser/config.json`이 `["/ext1"]`을 지정하고 `./agent-browser.json`이 `["/ext2"]`를 지정하면 결과는 `["/ext1", "/ext2"]`입니다.

`AGENT_BROWSER_EXTENSIONS` 환경 변수와 CLI `--extension` 플래그는 표준 우선순위 규칙을 따릅니다(env는 config를 대체하고, CLI는 추가합니다).

## Plugins

외부 plugin은 `plugins` 배열로 구성합니다.

plugin author protocol과 구현 예시는 [Plugins](/plugins)를 참조하세요.
이 config를 자동으로 생성하려면 `agent-browser plugin add <ref>`를 사용하세요.

```json
{
  "plugins": [
    {
      "name": "vault",
      "command": "agent-browser-plugin-vault",
      "args": [],
      "capabilities": ["credential.read"]
    },
    {
      "name": "cloud-browser",
      "command": "agent-browser-plugin-cloud-browser",
      "capabilities": ["browser.provider"]
    },
    {
      "name": "stealth",
      "command": "agent-browser-plugin-stealth",
      "capabilities": ["launch.mutate"]
    },
    {
      "name": "captcha",
      "command": "agent-browser-plugin-captcha",
      "capabilities": ["command.run", "captcha.solve"]
    }
  ]
}
```

프로젝트 수준 plugin 항목은 사용자 수준 항목 뒤에 추가됩니다. 두 항목이 같은 이름을 사용하면 agent-browser는 나중 항목을 해석하므로, 프로젝트가 사용자 기본값을 재정의할 수 있습니다. `AGENT_BROWSER_PLUGINS`는 같은 형태의 JSON 배열로 config 탐색을 대체할 수 있습니다.

Plugin command args에 vault token이나 비밀번호를 넣지 마세요. vault vendor 자체의 login/session 메커니즘이나 agent-browser config 외부의 환경을 사용하세요.

```bash
agent-browser plugin list
agent-browser auth login my-app --credential-provider vault --item "My App"
agent-browser --provider cloud-browser open https://example.com
agent-browser plugin run captcha captcha.solve --payload '{"siteKey":"...","url":"https://example.com"}'
```

`plugin run`은 `command.run` 및 사용자 지정 기능을 위한 것입니다. 핵심 기능과 protocol 요청 유형은 전용 명령 경로를 사용합니다.

## 환경 변수

이 환경 변수들은 추가 daemon 및 runtime 동작을 구성합니다.

<table>
  <thead>
    <tr><th>변수</th><th>설명</th><th>기본값</th></tr>
  </thead>
  <tbody>
    <tr><td><code>AGENT_BROWSER_CONFIG</code></td><td>명시적 config 파일 경로입니다.</td><td>(기본 탐색)</td></tr>
    <tr><td><code>AGENT_BROWSER_SESSION</code></td><td>격리된 브라우저 세션 이름입니다.</td><td><code>default</code></td></tr>
    <tr><td><code>AGENT_BROWSER_AUTO_CONNECT</code></td><td>실행 중인 Chrome 인스턴스를 자동으로 찾고 연결합니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_ALLOW_FILE_ACCESS</code></td><td><code>file://</code> URL이 로컬 파일에 접근하도록 허용합니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_EXECUTABLE_PATH</code></td><td>사용자 지정 브라우저 실행 파일 경로입니다.</td><td>(자동 탐색)</td></tr>
    <tr><td><code>AGENT_BROWSER_PROFILE</code></td><td>Chrome 프로필 이름 또는 지속 프로필 디렉터리입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_STATE</code></td><td>실행 시 로드할 storage state 파일입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_PROXY</code></td><td>Proxy URL입니다. 표준 proxy 변수보다 우선합니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_PROXY_BYPASS</code></td><td>Proxy 우회 호스트 목록입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_PROXY_USERNAME</code></td><td>자격 증명이 별도로 제공될 때의 proxy 사용자 이름입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_PROXY_PASSWORD</code></td><td>자격 증명이 별도로 제공될 때의 proxy 비밀번호입니다.</td><td>(없음)</td></tr>
    <tr><td><code>HTTP_PROXY</code> / <code>HTTPS_PROXY</code> / <code>ALL_PROXY</code></td><td>표준 proxy fallback 변수입니다.</td><td>(없음)</td></tr>
    <tr><td><code>NO_PROXY</code></td><td>표준 proxy 우회 fallback입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_ARGS</code></td><td>쉼표 또는 줄바꿈으로 구분된 브라우저 launch 인자입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_USER_AGENT</code></td><td>사용자 지정 User-Agent 문자열입니다.</td><td>(브라우저 기본값)</td></tr>
    <tr><td><code>AGENT_BROWSER_PROVIDER</code></td><td><code>ios</code>, <code>browserbase</code>, <code>kernel</code>, <code>browseruse</code>, <code>browserless</code>, <code>agentcore</code> 같은 브라우저 provider 또는 구성된 <code>browser.provider</code> plugin 이름입니다.</td><td>(로컬 브라우저)</td></tr>
    <tr><td><code>AGENT_BROWSER_HIDE_SCROLLBARS</code></td><td>Headless Chromium 스크린샷에서 네이티브 스크롤바를 숨깁니다.</td><td><code>true</code></td></tr>
    <tr><td><code>AGENT_BROWSER_COLOR_SCHEME</code></td><td>Color scheme 선호값(<code>dark</code>, <code>light</code>, <code>no-preference</code>)입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_DOWNLOAD_PATH</code></td><td>브라우저 다운로드의 기본 디렉터리입니다.</td><td>(임시 디렉터리)</td></tr>
    <tr><td><code>AGENT_BROWSER_DEFAULT_TIMEOUT</code></td><td>기본 timeout(ms)입니다. IPC timeout을 피하려면 30000보다 작게 유지하세요.</td><td><code>25000</code></td></tr>
    <tr><td><code>AGENT_BROWSER_SESSION_NAME</code></td><td>상태 자동 저장/로드 지속성 이름입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_STATE_EXPIRE_DAYS</code></td><td>N일보다 오래된 저장된 세션 상태를 자동 삭제합니다.</td><td><code>30</code></td></tr>
    <tr><td><code>AGENT_BROWSER_ENCRYPTION_KEY</code></td><td>AES-256-GCM 세션 암호화를 위한 64자 hex 키입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_EXTENSIONS</code></td><td>쉼표로 구분된 브라우저 extension 경로입니다. Extensions는 headed 및 headless 모드 모두에서 작동합니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_INIT_SCRIPTS</code></td><td>페이지 init scripts로 향하는 쉼표로 구분된 경로입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_ENABLE</code></td><td><code>react-devtools</code> 같은 쉼표로 구분된 내장 init script 기능입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_HEADED</code></td><td>headless로 실행하는 대신 브라우저 창을 표시합니다(활성화하려면 <code>1</code>).</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_JSON</code></td><td>기본적으로 JSON 출력을 사용합니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_ANNOTATE</code></td><td>기본적으로 annotated screenshots를 활성화합니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_CDP</code></td><td>daemon을 CDP 포트 또는 WebSocket URL에 연결합니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_STREAM_PORT</code></td><td>WebSocket streaming 포트를 재정의합니다. 기본적으로 OS가 할당한 포트가 사용됩니다. 특정 포트(예: <code>9223</code>)에 바인딩하려면 이를 설정하세요.</td><td>OS 할당</td></tr>
    <tr><td><code>AGENT_BROWSER_IDLE_TIMEOUT_MS</code></td><td>N ms 동안 활동이 없으면(명령을 받지 않으면) daemon을 자동 종료합니다. 임시 환경에 유용합니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_IOS_DEVICE</code></td><td><code>ios</code> provider의 기본 iOS 기기 이름입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_IOS_UDID</code></td><td><code>ios</code> provider의 기본 iOS 기기 UDID입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_DEBUG</code></td><td>Debug 출력을 활성화합니다(활성화하려면 <code>1</code>).</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_CONTENT_BOUNDARIES</code></td><td>LLM 안전성을 위해 페이지 출력을 boundary marker로 감쌉니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_MAX_OUTPUT</code></td><td>페이지 출력의 최대 문자 수입니다(한도를 넘으면 잘림).</td><td>(무제한)</td></tr>
    <tr><td><code>AGENT_BROWSER_ALLOWED_DOMAINS</code></td><td>쉼표로 구분된 허용 domain pattern입니다(예: <code>example.com,*.example.com</code>).</td><td>(제한 없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_ACTION_POLICY</code></td><td>action policy JSON 파일 경로입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_CONFIRM_ACTIONS</code></td><td>confirmation이 필요한 쉼표로 구분된 action category입니다.</td><td>(없음)</td></tr>
    <tr><td><code>AGENT_BROWSER_CONFIRM_INTERACTIVE</code></td><td>대화형 confirmation prompt를 활성화합니다(stdin이 TTY가 아니면 자동 deny).</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_ENGINE</code></td><td>사용할 브라우저 엔진: <code>chrome</code>(기본값), <code>lightpanda</code>.</td><td><code>chrome</code></td></tr>
    <tr><td><code>AGENT_BROWSER_NO_AUTO_DIALOG</code></td><td><code>alert</code>/<code>beforeunload</code> dialog의 자동 dismiss를 비활성화합니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>AGENT_BROWSER_PLUGINS</code></td><td>JSON plugin registry 재정의입니다.</td><td>(config 탐색)</td></tr>
    <tr><td><code>AGENT_BROWSER_SCREENSHOT_DIR</code></td><td>기본 screenshot 출력 디렉터리입니다.</td><td>(임시 디렉터리)</td></tr>
    <tr><td><code>AGENT_BROWSER_SCREENSHOT_QUALITY</code></td><td>0부터 100까지의 JPEG screenshot 품질입니다.</td><td>(format 기본값)</td></tr>
    <tr><td><code>AGENT_BROWSER_SCREENSHOT_FORMAT</code></td><td>Screenshot format: <code>png</code> 또는 <code>jpeg</code>.</td><td><code>png</code></td></tr>
    <tr><td><code>AGENT_BROWSER_SOCKET_DIR</code></td><td>daemon socket 파일에 대한 고급 재정의입니다.</td><td>runtime dir 또는 <code>~/.agent-browser</code></td></tr>
    <tr><td><code>AGENT_BROWSER_SKILLS_DIR</code></td><td><code>agent-browser skills</code>가 사용하는 디렉터리를 재정의합니다.</td><td>bundled skills</td></tr>
    <tr><td><code>AGENT_BROWSER_COLOR</code></td><td>truthy일 때 컬러 CLI 출력을 활성화합니다.</td><td>(비활성화)</td></tr>
    <tr><td><code>NO_COLOR</code></td><td>존재할 때 컬러 출력을 비활성화합니다.</td><td>(설정되지 않음)</td></tr>
    <tr><td><code>AI_GATEWAY_URL</code></td><td>Vercel AI Gateway base URL입니다.</td><td><code>https://ai-gateway.vercel.sh</code></td></tr>
    <tr><td><code>AI_GATEWAY_API_KEY</code></td><td>Vercel AI Gateway용 API 키입니다. AI chat을 활성화하려면 필요합니다.</td><td>(없음)</td></tr>
    <tr><td><code>AI_GATEWAY_MODEL</code></td><td>dashboard chat의 기본 AI model입니다.</td><td><code>anthropic/claude-sonnet-4.6</code></td></tr>
  </tbody>
</table>

## 오류 처리

- **자동으로 발견된 config 파일**(`~/.agent-browser/config.json`, `./agent-browser.json`)이 없으면 조용히 무시됩니다.
- **`--config <path>`**에 지정한 파일이 없거나 형식이 잘못된 경우 오류와 함께 종료됩니다.
- 자동으로 발견된 파일에 **잘못된 JSON**이 있으면 stderr에 경고를 출력하고 해당 파일 없이 계속합니다.
- **알 수 없는 키**는 forward compatibility를 위해 조용히 무시됩니다.

> **팁:** 프로젝트 수준 `agent-browser.json`에 환경별 값(경로, 프록시)이 포함되어 있다면 `.gitignore`에 추가하는 것을 고려하세요.
