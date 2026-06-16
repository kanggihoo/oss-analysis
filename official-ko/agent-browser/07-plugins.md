---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/07-plugins.md
order: 7
title: "Plugins"
---

# Plugins

Plugins를 사용하면 agent-browser가 외부 도구를 core에 추가하지 않고도 해당 도구와 통합할 수 있습니다. plugin은 stdin에서 하나의 JSON 요청을 읽고 stdout에 하나의 JSON 응답을 쓰는 로컬 실행 파일입니다.

vault 기반 로그인, 사용자 지정 브라우저 provider, 로컬 launch 사용자 지정, CAPTCHA 해결 같은 도메인별 명령에 plugins를 사용하세요.

## Plugin을 작성해야 할 때

통합에 vendor SDK, 로컬 CLI, 자격 증명, 유료 API, 또는 agent-browser 의존성이 되어서는 안 되는 동작이 필요할 때 plugin을 작성하세요.

Plugin에 잘 맞는 사례:

- 외부 vault에서 로그인 자격 증명 해석
- 호스팅 provider를 통해 브라우저를 실행하고 CDP WebSocket URL 반환
- 로컬 Chrome launch 인자, extensions 또는 init scripts 추가
- `captcha.solve` 같은 namespaced 명령 실행

브라우저 자동화 자체는 agent-browser 안에 두세요. plugin은 데이터나 launch 구성을 제공한 뒤 agent-browser가 계속 브라우저를 제어하게 해야 합니다.

## Plugin으로 만들 것

plugin 작성자는 다음 영역에서 시작하는 것이 좋습니다.

- **새 cloud browser providers**: 호스팅 브라우저 플랫폼은 `browser.provider`에 적합한 모델입니다. 기존 built-in은 호환성을 위해 core에 남을 수 있지만, 새 provider는 일반적으로 plugin으로 시작하는 것이 좋습니다.
- **Vault integrations**: Password manager, secret store, enterprise SSO helper는 `credential.read`에 적합합니다. 로컬 암호화 auth vault는 core에 두되, vendor별 vault 접근은 plugins에 두세요.
- **Stealth and anti-detection**: 이런 기법은 빠르게 변하고 core에서 지원하기에 위험할 수 있습니다. launch args, extensions, init scripts 또는 user-agent override를 추가하는 `launch.mutate` plugins에 적합합니다.
- **CAPTCHA solvers**: CAPTCHA 통합은 third-party API, 자격 증명, 정책 문제, 빠른 vendor 변동을 수반하므로 plugin 영역입니다. `command.run` 또는 `captcha.solve` 같은 사용자 지정 capability를 사용할 수 있습니다.
- **Vendor-specific auth helpers**: 특정 앱, IdP 또는 enterprise flow를 위한 로그인 helper는 일반적인 브라우저 자동화 primitive가 되지 않는 한 core 외부에 있어야 합니다.

## 다른 사람이 만든 plugin 추가

패키지 또는 저장소 이름과 함께 `plugin add`를 사용하세요.

```bash
agent-browser plugin add agent-browser-plugin-captcha
agent-browser plugin add @company/agent-browser-plugin-vault --name vault
agent-browser plugin add org/agent-browser-plugin-cloud-browser
```

agent-browser는 reference에서 source를 선택합니다.

<table>
  <thead>
    <tr><th>Reference</th><th>Source</th><th>예시</th></tr>
  </thead>
  <tbody>
    <tr><td><code>name</code></td><td>npm package</td><td><code>agent-browser-plugin-captcha</code></td></tr>
    <tr><td><code>@scope/name</code></td><td>scoped npm package</td><td><code>@company/agent-browser-plugin-vault</code></td></tr>
    <tr><td><code>owner/repo</code></td><td>GitHub repository</td><td><code>org/agent-browser-plugin-cloud-browser</code></td></tr>
  </tbody>
</table>

`plugin add`는 기본적으로 `./agent-browser.json`에 씁니다. 대신 `~/.agent-browser/config.json`에 쓰려면 `--global`을 사용하세요.

추가하는 동안 agent-browser는 패키지를 한 번 실행하고 `plugin.manifest`를 요청합니다. plugin manifest는 plugin 이름과 capabilities를 선언합니다. plugin이 아직 manifest를 지원하지 않는 경우 plugin README의 capabilities를 사용하세요.

```bash
agent-browser plugin add agent-browser-plugin-captcha --capability command.run --capability captcha.solve --no-manifest
```

plugin이 구성되었는지 확인하세요.

```bash
agent-browser plugin list
agent-browser plugin show captcha
```

그런 다음 capability에 맞는 명령 경로를 통해 사용하세요.

```bash
agent-browser auth login my-app --credential-provider vault --item "My App"
agent-browser --provider cloud-browser open https://example.com
agent-browser open https://example.com
agent-browser plugin run captcha captcha.solve --payload '{"siteKey":"abc","url":"https://example.com"}'
```

`launch.mutate` plugins는 `agent-browser open` 같은 로컬 launch에서 자동으로 실행됩니다.

## Plugin 구성

`plugin add`가 이 config를 만들어 줍니다. `plugins` 배열을 직접 편집할 수도 있습니다.

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
      "name": "captcha",
      "command": "agent-browser-plugin-captcha",
      "capabilities": ["command.run", "captcha.solve"]
    }
  ]
}
```

registry를 확인하세요.

```bash
agent-browser plugin list
agent-browser plugin show vault
```

`AGENT_BROWSER_PLUGINS`는 같은 형태의 JSON 배열로 config 탐색을 대체할 수 있습니다.

API token, vault token 또는 비밀번호를 plugin `args`에 넣지 마세요. agent-browser config 외부에서 vendor 자체 CLI login, keychain, 환경 또는 session 메커니즘을 사용하세요.

## Protocol

agent-browser는 실행 파일을 시작하고, 이 envelope를 stdin에 쓰고, stdout을 기다린 다음 stdout을 JSON으로 파싱합니다.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "type": "credential.resolve",
  "capability": "credential.read",
  "request": {}
}
```

모든 성공 응답은 같은 protocol과 `success: true`를 포함해야 합니다.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "data": {}
}
```

stdout만 파싱됩니다. stdout에 로그를 쓰지 마세요. agent-browser는 core 통합에서 plugin stderr를 억제하므로 개발 중에는 파일이나 자체 debug 모드를 사용하세요.

Core 통합은 실수로 secret이 노출되는 것을 줄이기 위해 사용자에게 표시되는 오류에서 plugin 제공 오류 텍스트를 억제합니다. 일반 `plugin run`은 개발자용 명령이므로 plugin 오류 텍스트를 유지합니다.

## Plugin manifest

사용자가 capabilities를 수동으로 입력하지 않고도 plugin을 추가할 수 있도록 `plugin.manifest`를 지원하세요.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "type": "plugin.manifest",
  "capability": "plugin.manifest",
  "request": {}
}
```

plugin 이름과 capabilities를 반환하세요.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "manifest": {
    "name": "captcha",
    "capabilities": ["command.run", "captcha.solve"],
    "description": "Solve CAPTCHA challenges through Example CAPTCHA"
  }
}
```

manifest가 있으면 사용자는 다음을 실행할 수 있습니다.

```bash
agent-browser plugin add agent-browser-plugin-captcha
```

manifest가 없으면 사용자는 추가 시 `--capability` 플래그를 전달해야 합니다.

## Capabilities

<table>
  <thead>
    <tr><th>Capability</th><th>Request type</th><th>사용자가 호출하는 방법</th><th>Response field</th></tr>
  </thead>
  <tbody>
    <tr><td><code>credential.read</code></td><td><code>credential.resolve</code></td><td><code>auth login --credential-provider &lt;name&gt;</code></td><td><code>credential</code></td></tr>
    <tr><td><code>browser.provider</code></td><td><code>browser.launch</code>, <code>browser.close</code></td><td><code>--provider &lt;name&gt;</code></td><td><code>browser</code></td></tr>
    <tr><td><code>launch.mutate</code></td><td><code>launch.mutate</code></td><td>모든 로컬 launch</td><td><code>launch</code></td></tr>
    <tr><td><code>command.run</code></td><td>사용자 지정 request type</td><td><code>plugin run &lt;name&gt; &lt;type&gt;</code></td><td><code>data</code></td></tr>
  </tbody>
</table>

Plugins는 `captcha.solve` 같은 사용자 지정 capabilities를 선언할 수 있습니다. `plugin run`은 `command.run` 및 사용자 지정 capabilities를 호출할 수 있지만 core capabilities나 protocol request types를 직접 호출할 수는 없습니다. `credential.read`, `browser.provider`, `launch.mutate`에는 전용 명령 경로를 사용하세요.

## 최소 plugin

이 plugin은 `captcha.solve`를 구현하고 가짜 token을 반환합니다.

```js
#!/usr/bin/env node

const chunks = [];
for await (const chunk of process.stdin) {
  chunks.push(chunk);
}

const input = JSON.parse(Buffer.concat(chunks).toString("utf8"));

function reply(body) {
  process.stdout.write(
    JSON.stringify({
      protocol: "agent-browser.plugin.v1",
      success: true,
      ...body,
    })
  );
}

if (input.protocol !== "agent-browser.plugin.v1") {
  process.stdout.write(
    JSON.stringify({
      protocol: "agent-browser.plugin.v1",
      success: false,
      error: "unsupported protocol",
    })
  );
  process.exit(0);
}

if (input.type === "plugin.manifest") {
  reply({
    manifest: {
      name: "captcha",
      capabilities: ["command.run", "captcha.solve"],
      description: "Example CAPTCHA plugin",
    },
  });
  process.exit(0);
}

if (input.type === "captcha.solve") {
  reply({
    data: {
      token: "example-token",
      siteKey: input.request.siteKey,
      url: input.request.url,
    },
  });
  process.exit(0);
}

process.stdout.write(
  JSON.stringify({
    protocol: "agent-browser.plugin.v1",
    success: false,
    error: `unsupported request type: ${input.type}`,
  })
);
```

실행 가능하게 만들고 구성하세요.

```bash
chmod +x ./agent-browser-plugin-captcha
```

```json
{
  "plugins": [
    {
      "name": "captcha",
      "command": "./agent-browser-plugin-captcha",
      "capabilities": ["command.run", "captcha.solve"]
    }
  ]
}
```

실행하세요.

```bash
agent-browser plugin run captcha captcha.solve --payload '{"siteKey":"abc","url":"https://example.com"}'
```

## Credential plugin

credential plugin은 다음을 받습니다.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "type": "credential.resolve",
  "capability": "credential.read",
  "request": {
    "profileName": "my-app",
    "itemRef": "My App",
    "url": "https://app.example.com/login"
  }
}
```

`credential`을 반환하세요.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "credential": {
    "username": "alice@example.com",
    "password": "secret",
    "url": "https://app.example.com/login",
    "usernameSelector": "#username",
    "passwordSelector": "#password",
    "submitSelector": "input[type=submit]"
  }
}
```

한 번의 로그인에 사용하세요.

```bash
agent-browser auth login my-app --credential-provider vault --item "My App"
```

외부 vault의 경우 plugin에서 vendor CLI를 호출하고 기존 로컬 session에 의존하는 방식을 선호하세요. `agent-browser.json`에 vault token을 전달하지 마세요.

## Browser provider plugin

browser provider plugin은 `browser.launch`를 받고 CDP URL을 반환합니다.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "browser": {
    "cdpUrl": "ws://127.0.0.1:9222/devtools/browser/session",
    "directPage": false,
    "metadata": {
      "sessionId": "provider-session-id"
    },
    "cleanup": {
      "sessionId": "provider-session-id"
    }
  }
}
```

그런 다음 사용자는 plugin 이름을 통해 launch합니다.

```bash
agent-browser --provider cloud-browser open https://example.com
```

`cleanup`이 반환되고 연결이 실패하면 agent-browser는 나중에 이를 `browser.close`의 request body로 다시 보냅니다.

## Launch mutator plugin

launch mutator는 Chrome이 시작되기 전에 로컬 launch options를 받으며 arguments, extensions, init scripts 또는 user agent를 추가할 수 있습니다.

```json
{
  "protocol": "agent-browser.plugin.v1",
  "success": true,
  "launch": {
    "args": ["--disable-blink-features=AutomationControlled"],
    "extensions": ["/absolute/path/to/extension"],
    "initScripts": [
      "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    ],
    "userAgent": "my-agent/1.0"
  }
}
```

`launch.mutate`로 구성한 다음 로컬 launch 명령을 사용하세요.

```bash
agent-browser open https://example.com
```

Launch mutator는 CDP 연결이나 remote browser providers에는 실행되지 않습니다. 해당 브라우저는 이미 로컬 launch 경로 밖에서 실행 중이기 때문입니다.

## 정책과 confirmation

Plugin 접근은 capability 범위의 policy action으로 노출됩니다.

```bash
agent-browser --confirm-actions plugin:vault:credential.read auth login my-app --credential-provider vault --item "My App"
agent-browser --confirm-actions plugin:cloud-browser:browser.provider --provider cloud-browser open https://example.com
agent-browser --confirm-actions plugin:stealth:launch.mutate open https://example.com
```

action 문자열은 `plugin:<name>:<capability>`입니다.

## Packaging 지침

npm packages의 경우 필수 stdout 로그가 없는 `bin` 명령을 노출하세요.

```json
{
  "name": "agent-browser-plugin-example",
  "bin": {
    "agent-browser-plugin-example": "./bin/plugin.js"
  }
}
```

plugin은 작고 명시적으로 유지하세요.

- 실제로 지원하는 capabilities만 선언
- stdin에서 정확히 하나의 request 읽기
- stdout에 정확히 하나의 JSON response 쓰기
- command-line arguments에서 secrets 제외
- navigation, selectors, screenshots, state, policy는 agent-browser가 처리하게 두기
