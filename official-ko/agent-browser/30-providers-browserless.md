---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/30-providers-browserless.md
order: 30
title: "Browserless"
---

# Browserless

[Browserless](https://browserless.io)는 Sessions API가 있는 cloud browser infrastructure를 제공합니다. local browser를 사용할 수 없는 environments에서 agent-browser를 실행할 때 사용하세요.

## 설정

```bash
agent-browser -p browserless open https://example.com
```

또는 CI/scripts에는 환경 변수를 사용하세요.

```bash
agent-browser open https://example.com
```

`-p` flag는 `AGENT_BROWSER_PROVIDER`보다 우선합니다.

## 구성

<table>
  <thead>
    <tr><th>변수</th><th>설명</th><th>기본값</th></tr>
  </thead>
  <tbody>
    <tr><td><code>BROWSERLESS_API_KEY</code></td><td>API token(필수)</td><td></td></tr>
    <tr><td><code>BROWSERLESS_API_URL</code></td><td>Base API URL(custom regions 또는 self-hosted용)</td><td><code>https://production-sfo.browserless.io</code></td></tr>
    <tr><td><code>BROWSERLESS_BROWSER_TYPE</code></td><td>사용할 browser type(<code>chromium</code> 또는 <code>chrome</code>)</td><td><code>chromium</code></td></tr>
    <tr><td><code>BROWSERLESS_TTL</code></td><td>Session TTL in milliseconds</td><td><code>300000</code></td></tr>
    <tr><td><code>BROWSERLESS_STEALTH</code></td><td>stealth mode 활성화</td><td><code>true</code></td></tr>
  </tbody>
</table>

활성화되면 agent-browser는 로컬 브라우저를 실행하는 대신 Browserless cloud session에 연결합니다. 모든 commands는 동일하게 작동합니다.

API token은 [Browserless Dashboard](https://browserless.io)에서 받으세요.
