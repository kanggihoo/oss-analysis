---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/13-network.md
order: 13
title: "Network"
---

# Network

브라우저 자동화 중 request를 intercept하고, response를 mock하고, traffic을 inspect하고, HAR files를 export하려면 network commands를 사용하세요.

## Request routing

Routes는 일치하는 requests가 전송되기 전에 적용됩니다. 첫 page load에 영향을 주어야 할 때는 navigation 전에 설정하세요.

```bash
agent-browser open
agent-browser network route "**/analytics/**" --abort
agent-browser network route "**/api/users" --body '{"users":[]}'
agent-browser navigate https://app.example.com
```

<table>
  <thead>
    <tr><th>명령</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>network route &lt;url&gt;</code></td><td>일치하는 requests intercept</td></tr>
    <tr><td><code>network route &lt;url&gt; --abort</code></td><td>일치하는 requests 차단</td></tr>
    <tr><td><code>network route &lt;url&gt; --body &lt;json&gt;</code></td><td>일치하는 requests에 mock body로 응답</td></tr>
    <tr><td><code>network route "*" --resource-type script --abort</code></td><td>특정 resource type만 차단</td></tr>
    <tr><td><code>network unroute [url]</code></td><td>하나의 route 또는 모든 routes 제거</td></tr>
  </tbody>
</table>

`--resource-type`은 `script`, `image`, `font`, `xhr`, `fetch` 같은 쉼표로 구분된 resource types를 받습니다.

## Request log

```bash
agent-browser network requests
agent-browser network requests --filter api
agent-browser network requests --type xhr,fetch
agent-browser network requests --method POST
agent-browser network requests --status 2xx
agent-browser network request <requestId>
agent-browser network requests --clear
```

<table>
  <thead>
    <tr><th>Filter</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>--filter &lt;pattern&gt;</code></td><td>URL substring 또는 pattern으로 필터링</td></tr>
    <tr><td><code>--type &lt;csv&gt;</code></td><td>resource type으로 필터링</td></tr>
    <tr><td><code>--method &lt;method&gt;</code></td><td>HTTP method로 필터링</td></tr>
    <tr><td><code>--status &lt;status&gt;</code></td><td>정확한 status, status family 또는 range로 필터링</td></tr>
    <tr><td><code>--clear</code></td><td>추적된 request log 지우기</td></tr>
  </tbody>
</table>

`network requests`에서 ID를 찾은 뒤 하나의 request와 response를 자세히 inspect하려면 `network request <requestId>`를 사용하세요.

## HAR export

```bash
agent-browser network har start

agent-browser open https://app.example.com
agent-browser click @e4

agent-browser network har stop ./trace.har
```

HAR files에는 request headers, response headers, response bodies가 포함될 수 있습니다. 페이지가 cookies, bearer tokens 또는 API keys를 사용할 때는 민감한 정보로 취급하세요.

## SSR and no-JavaScript debugging

```bash
agent-browser batch \
  '["open"]' \
  '["network","route","*","--abort","--resource-type","script"]' \
  '["navigate","http://localhost:3000"]' \
  '["snapshot","-i"]'
```

URL 없이 `open`으로 실행하면 브라우저가 `about:blank`에 머무르므로, 첫 실제 navigation 전에 routes를 등록할 시간이 생깁니다.
