---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/24-security.md
order: 24
title: "Security"
---

# Security

agent-browser에는 credential 노출, 신뢰할 수 없는 page content를 통한 prompt injection, 무단 browser actions를 방지하기 위한 security features가 포함되어 있습니다.

모든 security features는 opt-in입니다. 기본적으로 agent-browser는 navigation, actions 또는 output에 제한을 두지 않습니다. 배포에 필요할 때 이 features를 활성화하세요. 명시적으로 feature를 활성화하기 전까지 기존 workflows에는 영향이 없습니다.

## Threat Model

이 features는 LLM 기반 agent가 브라우저를 제어할 때 다음 threats를 완화하도록 설계되었습니다.

- **Credential exposure** -- auth vault에 저장된 passwords는 LLM context에 절대 포함되지 않습니다. CLI가 vault operations를 로컬에서 처리하며, credentials는 daemon의 IPC channel을 통과하지 않습니다.
- **Plugin secret access**: Credential provider plugins는 out-of-process로 실행되며 구조화된 credential resolution request만 받습니다. Core agent-browser는 browser automation, policy checks, redaction-sensitive output handling을 유지합니다.
- **Prompt injection via page content** -- 악성 pages는 tool output 또는 system instructions처럼 보이는 text를 삽입할 수 있습니다. Content boundary markers(`--content-boundaries`)를 사용하면 orchestrator가 신뢰할 수 있는 tool output과 신뢰할 수 없는 page content를 구분할 수 있습니다.
- **Unauthorized navigation / data exfiltration** -- 손상되거나 조작된 agent가 데이터를 유출하기 위해 attacker-controlled domains로 navigate할 수 있습니다. domain allowlist(`--allowed-domains`)는 허용되지 않은 domains로 향하는 navigations, sub-resource requests, WebSocket connections, EventSource streams, `sendBeacon` calls를 차단합니다.
- **Unauthorized destructive actions** -- Action policy(`--action-policy`)와 confirmation gating(`--confirm-actions`)은 명시적 승인 없이 agent가 위험한 operations(eval, downloads, uploads)를 수행하지 못하게 합니다.
- **Context flooding** -- 큰 page outputs는 LLM의 context window를 압도할 수 있습니다. Output truncation(`--max-output`)은 page-sourced content의 크기에 상한을 둡니다.

### 알려진 제한 사항

- **WebSocket/EventSource blocking은 best-effort입니다.** init script를 통해 browser constructors를 override하는 방식으로 작동합니다. `eval` action category가 허용되면 page scripts가 이론적으로 원래 constructors를 복원할 수 있습니다. 최대 보호를 위해 `--action-policy`로 `eval`을 deny하세요.
- **Remote connections에서 domain filter timing.** CDP 또는 cloud provider를 통해 기존 browser에 연결할 때, domain filter가 설치되기 전에 pages가 이미 content를 로드했을 수 있습니다. agent-browser는 filter가 활성화된 뒤 disallowed pages를 `about:blank`로 navigate하지만, 그 전에 로드된 resources는 소급해서 차단되지 않습니다.
- **Content boundaries는 defense-in-depth입니다.** LLM과 orchestrator가 structural markers를 존중한다는 전제에 의존합니다. 충분히 강력한 adversarial page가 boundary format을 흉내 내려고 시도할 수 있지만, per-process CSPRNG nonce 때문에 예측은 사실상 어렵습니다.
- **Plugins는 local executables입니다.** 신뢰하는 maintainers의 credential plugins만 설치하세요. agent-browser는 plugins에 보내는 데이터를 제한하고 policy gates를 지원하지만, 임의의 local executables를 sandbox하지는 않습니다.
- **Plugin config는 secret storage가 아닙니다.** vault tokens 또는 passwords를 plugin command args에 넣지 마세요. vendor 자체의 login/session 메커니즘이나 agent-browser config 외부의 환경을 사용하세요.
- **Confirmation timeout.** Pending confirmations는 60초 후 자동으로 deny됩니다. Orchestrators는 그 window 안에 응답해야 합니다.
- **Non-TTY auto-deny.** `--confirm-interactive`가 설정되었지만 stdin이 terminal이 아닌 경우(예: piped input), non-interactive contexts에서 실수로 승인되는 것을 막기 위해 actions가 자동으로 deny됩니다.

## Authentication Vault

credentials를 로컬에 저장하고 이름으로 참조합니다. LLM은 passwords를 절대 보지 않습니다.

```bash
# Save credentials (encrypted if AGENT_BROWSER_ENCRYPTION_KEY is set)
# Recommended: pipe password via stdin to avoid shell history / process listing exposure
echo "pass" | agent-browser auth save github --url https://github.com/login --username user --password-stdin

# Or pass directly (a warning will be shown)
agent-browser auth save github --url https://github.com/login --username user --password pass

# Login using saved credentials
agent-browser auth login github

# List saved profiles (names and URLs only, no secrets)
agent-browser auth list

# Show profile metadata
agent-browser auth show github

# Delete a profile
agent-browser auth delete github
```

`auth login`은 `load` lifecycle event로 navigate한 다음 form selectors가 나타날 때까지 기다린 뒤 fill/click합니다. 이렇게 하면 long-lived background requests가 있는 pages에서 `networkidle` hang을 피하면서 delayed SPA login pages의 신뢰성이 높아집니다.

auto-detection이 실패하면 custom selectors를 지정할 수 있습니다.

```bash
agent-browser auth save myapp \
  --url https://app.example.com/login \
  --username user --password pass \
  --username-selector "#email" \
  --password-selector "#password" \
  --submit-selector "button.login"
```

Profiles는 `~/.agent-browser/auth/`에 저장되며 항상 AES-256-GCM으로 암호화됩니다. `AGENT_BROWSER_ENCRYPTION_KEY`가 설정되어 있지 않으면 처음 사용할 때 `~/.agent-browser/.encryption-key`에 key가 자동 생성됩니다. portability를 위해 이 file을 백업하거나 환경 변수를 명시적으로 설정하세요.

다른 users가 encryption keys 또는 auth profiles를 읽지 못하도록 Unix(`chmod 600`/`700`)와 Windows(현재 user로 제한된 `icacls`) 모두에서 file permissions가 강제됩니다.

### Plugins

Plugins는 `agent-browser.plugin.v1` stdio JSON protocol을 통해 out-of-process로 실행됩니다. `agent-browser.json`에서 구성하세요.

plugin author protocol과 구현 예시는 [Plugins](/plugins)를 참조하세요.
plugin config를 자동으로 생성하려면 `agent-browser plugin add <ref>`를 사용하세요.

```json
{
  "plugins": [
    {
      "name": "vault",
      "command": "agent-browser-plugin-vault",
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

구성된 plugins를 inspect합니다.

```bash
agent-browser plugin list
agent-browser plugin show vault
```

login에 plugin을 사용합니다.

```bash
agent-browser auth login my-app --credential-provider vault --item "My App"
```

plugin을 browser provider로 사용합니다.

```bash
agent-browser --provider cloud-browser open https://example.com
```

generic plugin command를 사용합니다.

```bash
agent-browser plugin run captcha captcha.solve --payload '{"siteKey":"...","url":"https://example.com"}'
```

Credential plugins는 `credential.resolve`를 받고 username, password, 선택적으로 URL 또는 selector metadata를 반환합니다. Browser provider plugins는 `browser.launch`를 받고 CDP WebSocket URL을 반환합니다. Launch mutator plugins는 `launch.mutate`를 받고 Chrome이 시작되기 전에 local launch args, extensions 또는 init script source를 추가할 수 있습니다. Generic command plugins는 `plugin run`에 전달된 request type을 받습니다.

`plugin run`은 `command.run` 및 custom capabilities용입니다. Core capabilities와 protocol request types는 전용 command paths를 사용하므로 credential, browser-provider, launch-mutator access가 일반 policy gates 안에 유지됩니다.

agent-browser는 browser automation, redaction-sensitive output, policy enforcement를 core에 유지합니다. Credential plugin secrets는 command arguments, dashboard events 또는 일반 command output에 나타나지 않습니다.

capability actions로 plugin access를 gate하세요.

```bash
agent-browser --confirm-actions plugin:vault:credential.read auth login my-app --credential-provider vault --item "My App"
agent-browser --confirm-actions plugin:cloud-browser:browser.provider --provider cloud-browser open https://example.com
agent-browser --confirm-actions plugin:stealth:launch.mutate open https://example.com
```

## Content Boundary Markers

`--content-boundaries`가 활성화되면 모든 page-sourced output이 structural markers로 감싸져 LLMs가 tool output과 신뢰할 수 없는 page content를 구분할 수 있습니다.

```
--- AGENT_BROWSER_PAGE_CONTENT nonce=a1b2c3d4 origin=https://example.com ---
[snapshot / text / html / eval output here]
--- END_AGENT_BROWSER_PAGE_CONTENT nonce=a1b2c3d4 ---
```

nonce는 CLI process invocation마다 생성되는 random value이므로 boundary를 spoof하려는 page content가 예측할 수 없습니다.

flag 또는 환경 변수로 활성화합니다.

```bash
agent-browser --content-boundaries snapshot
# or
```

영향을 받는 output types: `snapshot`, `get text`, `get html`, `eval`, `console`.

`--json` mode에서는 boundary metadata가 `nonce`와 `origin` fields를 포함하는 `_boundary` object로 JSON response에 주입되어, orchestrators가 provenance를 프로그래밍 방식으로 검증할 수 있습니다.

```json
{
  "success": true,
  "data": { "snapshot": "...", "origin": "https://example.com" },
  "_boundary": { "nonce": "a1b2c3d4e5f6...", "origin": "https://example.com" }
}
```

## Domain Allowlist

redirect-based attacks와 data exfiltration을 방지하기 위해 browser가 상호작용할 수 있는 domains를 제한합니다.

```bash
agent-browser --allowed-domains "example.com,*.example.com,github.com" open https://example.com
# or
```

exact match(`github.com`)와 wildcard prefix(`*.example.com`, bare domain `example.com`도 matching)를 지원합니다. 허용되지 않은 domains로 향하는 page navigations와 sub-resource requests(scripts, images, fetch, XHR 등)가 모두 차단되어 data exfiltration을 방지합니다. WebSocket 및 EventSource connections도 constructor-level patching으로 차단됩니다. Non-http(s) sub-resources(data URIs, blobs)는 여전히 허용됩니다. request가 차단되면 command는 error를 반환합니다.

> **참고:** WebSocket/EventSource blocking은 best-effort입니다. init script를 통해 browser constructors를 override하는 방식으로 작동합니다. `eval` action category가 허용되면 page scripts가 이론적으로 원래 constructors를 복원할 수 있습니다. 최대 보호를 위해 `--allowed-domains`를 사용할 때 `--action-policy`로 `eval` category를 deny하세요.

Config file:

```json
{
  "allowedDomains": ["example.com", "*.example.com", "github.com"]
}
```

> **CDN and third-party resources:** domain filter는 허용되지 않은 domains로 향하는 모든 sub-resource requests(scripts, stylesheets, images, fonts, fetch/XHR)를 차단합니다. 대부분의 websites는 CDN domains에서 assets를 로드합니다. allowlist에 이를 포함하지 않으면 pages가 깨집니다. 예:
>
> ```bash
> --allowed-domains "myapp.com,*.myapp.com,cdn.jsdelivr.net,fonts.googleapis.com,fonts.gstatic.com"
> ```

## Action Policy

static policy file을 사용해 actions를 gate합니다. policy는 daemon이 강제합니다. denied actions는 즉시 실패합니다.

```bash
agent-browser --action-policy ./policy.json open https://example.com
# or
```

예시 policy(특정 denial이 있는 permissive policy):

```json
{
  "default": "allow",
  "deny": ["eval", "download", "upload"]
}
```

예시 policy(restrictive):

```json
{
  "default": "deny",
  "allow": ["navigate", "snapshot", "click", "scroll", "wait", "get"]
}
```

<table>
  <thead>
    <tr><th>Category</th><th>Actions</th></tr>
  </thead>
  <tbody>
    <tr><td><code>navigate</code></td><td>open, back, forward, reload, tab new</td></tr>
    <tr><td><code>click</code></td><td>click, dblclick, tap</td></tr>
    <tr><td><code>fill</code></td><td>fill, type, keyboard type/inserttext, select, check, uncheck</td></tr>
    <tr><td><code>eval</code></td><td>eval, evalhandle, addscript, addinitscript, addstyle, expose, setcontent</td></tr>
    <tr><td><code>download</code></td><td>download, waitfordownload</td></tr>
    <tr><td><code>upload</code></td><td>upload</td></tr>
    <tr><td><code>snapshot</code></td><td>snapshot, screenshot, pdf, diff</td></tr>
    <tr><td><code>scroll</code></td><td>scroll, scrollintoview</td></tr>
    <tr><td><code>wait</code></td><td>wait, waitforurl, waitforloadstate, waitforfunction</td></tr>
    <tr><td><code>get</code></td><td>get text/html/url/title, count, isvisible, getbyrole, getbytext, getbylabel, etc.</td></tr>
    <tr><td><code>interact</code></td><td>hover, focus, drag, press, keydown, keyup, mousemove, dispatch</td></tr>
    <tr><td><code>network</code></td><td>network route/unroute, requests, har start/stop</td></tr>
    <tr><td><code>state</code></td><td>state save/load, cookies set, storage set</td></tr>
  </tbody>
</table>

Auth vault operations는 secrets를 일반 command output과 LLM context 밖에 유지합니다. Domain allowlist restrictions는 `auth login` navigations에도 계속 적용됩니다. Plugin-backed logins는 policy 및 confirmation gates를 위해 capability action `plugin:<name>:credential.read`도 노출합니다.

## Action Confirmation

명시적 승인이 필요한 actions에는 `--confirm-actions`를 사용해 confirmation이 필요한 categories를 지정하세요.

```bash
# Orchestrator mode: returns confirmation_required response
agent-browser --confirm-actions eval,download eval "document.title"

# Then approve or deny:
agent-browser confirm c_8f3a1234
agent-browser deny c_8f3a1234
```

interactive(human-in-the-loop) confirmation:

```bash
agent-browser --confirm-actions eval,download --confirm-interactive eval "document.title"
# Prompts: Allow? [y/N]
```

Pending confirmations는 60초 후 자동으로 deny됩니다.

> **Non-TTY behavior:** `--confirm-interactive`가 설정되었지만 stdin이 TTY가 아닌 경우(예: piped input 또는 automated pipeline 안에서 실행), actions는 자동으로 deny됩니다. 이는 non-interactive contexts에서 실수로 승인되는 것을 방지합니다.

## Output Length Limits

큰 page outputs를 잘라 context flooding을 방지합니다.

```bash
agent-browser --max-output 50000 get text body
# or
```

영향을 받는 output types: `snapshot`, `get text`, `get html`, `eval`, `console`.

## Environment Variables

<table>
  <thead>
    <tr><th>Variable</th><th>Description</th></tr>
  </thead>
  <tbody>
    <tr><td><code>AGENT_BROWSER_CONTENT_BOUNDARIES</code></td><td>page output을 boundary markers로 감싸기</td></tr>
    <tr><td><code>AGENT_BROWSER_MAX_OUTPUT</code></td><td>page output의 최대 문자 수</td></tr>
    <tr><td><code>AGENT_BROWSER_ALLOWED_DOMAINS</code></td><td>쉼표로 구분된 허용 domain patterns</td></tr>
    <tr><td><code>AGENT_BROWSER_ACTION_POLICY</code></td><td>action policy JSON file 경로</td></tr>
    <tr><td><code>AGENT_BROWSER_CONFIRM_ACTIONS</code></td><td>confirmation이 필요한 쉼표로 구분된 action categories</td></tr>
    <tr><td><code>AGENT_BROWSER_CONFIRM_INTERACTIVE</code></td><td>interactive confirmation prompts 활성화</td></tr>
    <tr><td><code>AGENT_BROWSER_ENCRYPTION_KEY</code></td><td>AES-256-GCM encryption(auth vault + sessions)을 위한 64자 hex key</td></tr>
    <tr><td><code>AGENT_BROWSER_PLUGINS</code></td><td>JSON plugin registry override</td></tr>
  </tbody>
</table>

## Recommended Configuration

production AI agent deployments에는 다음을 권장합니다.

```json
{
  "contentBoundaries": true,
  "maxOutput": 50000,
  "allowedDomains": ["your-app.com", "*.your-app.com"],
  "actionPolicy": "./policy.json"
}
```
