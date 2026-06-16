---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/22-proxy.md
order: 22
title: "Proxy"
---

# Proxy

corporate networks, geo-testing, scraping infrastructure, 그리고 제어된 egress point를 통한 traffic routing에는 proxies를 사용하세요.

## CLI flags

```bash
agent-browser --proxy "http://proxy.example.com:8080" open https://example.com
agent-browser --proxy "http://user:pass@proxy.example.com:8080" open https://example.com
agent-browser --proxy "http://proxy.example.com:8080" --proxy-bypass "localhost,*.internal.com" open https://example.com
```

<table>
  <thead>
    <tr><th>Flag</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>--proxy &lt;url&gt;</code></td><td>선택적 credentials를 포함한 proxy server URL</td></tr>
    <tr><td><code>--proxy-bypass &lt;hosts&gt;</code></td><td>proxy를 우회해야 하는 hosts</td></tr>
  </tbody>
</table>

## 환경 변수

<table>
  <thead>
    <tr><th>변수</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>AGENT_BROWSER_PROXY</code></td><td>agent-browser proxy URL</td></tr>
    <tr><td><code>AGENT_BROWSER_PROXY_BYPASS</code></td><td>agent-browser proxy bypass list</td></tr>
    <tr><td><code>AGENT_BROWSER_PROXY_USERNAME</code></td><td>credentials가 별도로 제공될 때의 proxy username</td></tr>
    <tr><td><code>AGENT_BROWSER_PROXY_PASSWORD</code></td><td>credentials가 별도로 제공될 때의 proxy password</td></tr>
    <tr><td><code>HTTP_PROXY</code> / <code>HTTPS_PROXY</code></td><td>fallback으로 사용되는 표준 proxy environment variables</td></tr>
    <tr><td><code>ALL_PROXY</code></td><td>SOCKS 또는 all-traffic proxy fallback</td></tr>
    <tr><td><code>NO_PROXY</code></td><td>표준 proxy bypass fallback</td></tr>
  </tbody>
</table>

`AGENT_BROWSER_PROXY`는 표준 proxy variables보다 우선합니다. CLI는 proxy URL에 포함된 credentials도 받으며, launch options를 daemon에 전달하기 전에 이를 분리합니다.

## SOCKS proxy

```bash
agent-browser open https://example.com

agent-browser open https://example.com
```

## Local traffic 우회

```bash

agent-browser open https://external.example.com
agent-browser open http://localhost:3000
```

## Routing 검증

```bash
agent-browser open https://httpbin.org/ip
agent-browser get text body
```

response에는 machine의 direct network address가 아니라 proxy egress address가 표시되어야 합니다.

## 보안 참고 사항

- proxy credentials에는 environment variables 또는 secret stores를 선호하세요.
- proxy usernames, passwords 또는 session URLs를 commit하지 마세요.
- HAR exports와 network logs에는 proxy-authenticated requests가 포함될 수 있습니다.
