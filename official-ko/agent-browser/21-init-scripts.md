---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/21-init-scripts.md
order: 21
title: "Init Scripts & Extensions"
---

# Init Scripts & Extensions

Init scripts는 page JavaScript보다 먼저 실행됩니다. 첫 navigation 전에 hooks, polyfills, instrumentation 또는 test helpers를 설치하는 데 사용하세요.

## Launch-time scripts

```bash
agent-browser --init-script ./instrumentation.js open https://example.com
agent-browser --init-script ./a.js --init-script ./b.js open https://example.com
```

환경 변수로 scripts를 구성할 수도 있습니다.

```bash
agent-browser open https://example.com
```

Launch-time scripts는 브라우저가 시작될 때 적용됩니다. daemon이 이미 실행 중이면 launch-time script options를 변경하기 전에 닫으세요.

## Built-in scripts

```bash
agent-browser --enable react-devtools open http://localhost:3000
```

`react-devtools`는 현재 사용 가능한 built-in feature입니다. application code가 실행되기 전에 React DevTools hook을 설치하며 `react tree`, `react inspect`, `react renders`, `react suspense`에 필요합니다.

## Runtime scripts

```bash
agent-browser addinitscript "window.__testMode = true"
# Returns an identifier

agent-browser removeinitscript <identifier>
```

Runtime init scripts는 session이 시작된 후에 유용합니다. 여전히 init scripts이므로 이미 실행된 page code를 다시 작성하는 것이 아니라 향후 documents와 navigations에 영향을 줍니다.

## Pre-navigation setup

첫 실제 navigation 전에 routes, cookies 또는 scripts를 설치해야 하는 flows의 경우 URL 없이 브라우저를 시작하세요.

```bash
agent-browser batch \
  '["open"]' \
  '["network","route","*","--abort","--resource-type","script"]' \
  '["cookies","set","--curl","cookies.curl","--domain","localhost"]' \
  '["navigate","http://localhost:3000/target"]'
```

URL 없이 `open`을 실행하면 브라우저가 `about:blank`에서 시작되어 target page가 로드되기 전에 state를 준비할 여지가 생깁니다.

## Extensions

```bash
agent-browser --extension ./extension open https://example.com
agent-browser --extension ./a --extension ./b open https://example.com
```

Extensions는 launch-time options입니다. 로컬 Chromium 기반 브라우저가 필요하며 CDP connections, cloud providers 또는 Lightpanda에서는 지원되지 않습니다.

## 안전

Init scripts와 extensions는 page context에서 높은 권한으로 실행됩니다. 신뢰할 수 있는 local paths의 scripts와 extension directories만 로드하세요.
