---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/19-react.md
order: 19
title: "React & Web Vitals"
---

# React & Web Vitals

agent-browser는 React component trees를 inspect하고, re-renders를 기록하고, Suspense boundaries를 분류하고, Core Web Vitals를 측정하며, SPA navigation을 수행할 수 있습니다.

## React inspection 활성화

React inspection은 page JavaScript가 실행되기 전에 React DevTools hook이 설치되어 있어야 합니다.

```bash
agent-browser open --enable react-devtools http://localhost:3000
agent-browser react tree
```

브라우저가 이미 실행 중이면 `--enable react-devtools`로 다시 실행하기 전에 닫으세요.

## React commands

<table>
  <thead>
    <tr><th>명령</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>react tree</code></td><td>fiber IDs와 함께 React component tree 출력</td></tr>
    <tr><td><code>react inspect &lt;fiberId&gt;</code></td><td>하나의 component에 대한 props, hooks, state, source inspect</td></tr>
    <tr><td><code>react renders start</code></td><td>component render commits 기록 시작</td></tr>
    <tr><td><code>react renders stop [--json]</code></td><td>기록을 중지하고 render profile 출력</td></tr>
    <tr><td><code>react suspense [--only-dynamic] [--json]</code></td><td>Suspense boundaries를 순회하고 static boundaries와 dynamic boundaries를 분류</td></tr>
  </tbody>
</table>

```bash
agent-browser react tree
agent-browser react inspect 42

agent-browser react renders start
agent-browser click @e3
agent-browser react renders stop

agent-browser react suspense --only-dynamic
```

## Web Vitals

`vitals`는 모든 사이트에서 작동합니다. React profiling build가 감지되면 hydration phases도 보고합니다.

```bash
agent-browser vitals
agent-browser vitals https://example.com --json
```

기본적으로 `vitals`는 구조화된 `--json` response와 같은 fields를 사용해 summary를 출력합니다. 보고되는 metrics에는 가능한 경우 LCP, CLS, TTFB, FCP, INP 및 hydration timing이 포함됩니다.

## SPA navigation

`pushstate`는 전체 브라우저 reload를 강제하지 않고 client-side navigation을 수행합니다. Next.js 앱에서는 RSC fetches가 계속 실행되도록 `window.next.router.push` 사용을 시도합니다. 다른 frameworks는 `history.pushState`와 navigation events로 fallback합니다.

```bash
agent-browser pushstate /dashboard
agent-browser wait --load networkidle
agent-browser snapshot -i
```

전체 navigation에는 `open`을 사용하고, workflow에 SPA behavior가 필요할 때는 `pushstate`를 사용하세요.
