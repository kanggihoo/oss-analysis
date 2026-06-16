---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/18-profiler.md
order: 18
title: "Profiler"
---

# Profiler

브라우저 자동화 중 Chrome DevTools performance profiles를 캡처합니다.
profiles를 사용해 agentic workflows에서 느린 page loads, 비용이 큰 JavaScript, layout thrashing 및 기타 performance bottlenecks를 진단하세요.

## 기본 사용법

```bash
# Start profiling
agent-browser profiler start

# Perform actions
agent-browser navigate https://example.com
agent-browser click "#button"

# Stop and save profile
agent-browser profiler stop ./trace.json
```

출력 JSON file은 Chrome DevTools, Perfetto UI 또는 Chrome Trace Event format을 받는 모든 도구에 로드할 수 있습니다.

## 명령

<table>
  <thead>
    <tr><th>명령</th><th>설명</th></tr>
  </thead>
  <tbody>
    <tr><td><code>profiler start</code></td><td>performance profile recording 시작</td></tr>
    <tr><td><code>profiler start --categories &lt;list&gt;</code></td><td>사용자 지정 trace categories로 시작</td></tr>
    <tr><td><code>profiler stop [path]</code></td><td>profiling을 중지하고 file로 저장</td></tr>
  </tbody>
</table>

## Trace categories

`--categories` flag는 쉼표로 구분된 Chrome trace categories 목록을 받습니다.

```bash
agent-browser profiler start --categories "devtools.timeline,v8.execute,blink.user_timing"
```

기본 categories에는 `devtools.timeline`, `v8.execute`, `blink`, `blink.user_timing`, `latencyInfo`, `renderer.scheduler`, `toplevel` 및 자세한 CPU profiling과 call stack analysis를 위한 여러 `disabled-by-default-*` categories가 포함됩니다.

### 일반적인 categories

<table>
  <thead>
    <tr><th>Category</th><th>캡처하는 항목</th></tr>
  </thead>
  <tbody>
    <tr><td><code>devtools.timeline</code></td><td>표준 DevTools performance events</td></tr>
    <tr><td><code>v8.execute</code></td><td>JavaScript 실행에 소요된 시간</td></tr>
    <tr><td><code>blink</code></td><td>Renderer events(layout, paint, style)</td></tr>
    <tr><td><code>blink.user_timing</code></td><td><code>performance.mark()</code> 및 <code>performance.measure()</code> calls</td></tr>
    <tr><td><code>latencyInfo</code></td><td>Input-to-display latency</td></tr>
    <tr><td><code>disabled-by-default-v8.cpu_profiler</code></td><td>Sampling-based JS CPU profiling</td></tr>
  </tbody>
</table>

## 출력 형식

출력은 Chrome Trace Event format의 JSON file입니다.

```json
{
  "traceEvents": [
    {
      "cat": "devtools.timeline",
      "name": "RunTask",
      "ph": "X",
      "ts": 12345,
      "dur": 100,
      "pid": 1,
      "tid": 1
    }
  ],
  "metadata": {
    "clock-domain": "LINUX_CLOCK_MONOTONIC"
  }
}
```

`metadata.clock-domain` field는 host platform(Linux 또는 macOS)을 반영합니다.
Windows에서는 생략됩니다.

## Profiles 보기

- **Chrome DevTools** -- Performance panel > Load profile
- **Perfetto** -- https://ui.perfetto.dev/ (JSON file drag and drop)
- **Trace Viewer** -- 모든 Chromium 브라우저의 `chrome://tracing`

## 사용 사례

- **Page load analysis** -- navigation을 profile해 느린 resources, long tasks 또는 layout shifts 식별
- **Interaction profiling** -- clicks, form fills 및 기타 user interactions 비용 측정
- **CI regression checks** -- build마다 profiles를 캡처하고 시간에 따른 trace data 비교
- **Agent workflow optimization** -- agentic flow에서 가장 비용이 큰 steps 찾기

## 제한 사항

- Chromium 기반 브라우저(Chrome, Edge)에서만 작동합니다. Firefox 또는 WebKit에서는 지원되지 않습니다.
- profiling이 활성화된 동안 trace data가 memory에 누적됩니다(5백만 events로 제한). 관심 영역이 끝나면 즉시 profiling을 중지하세요.
- 중지 시 data collection에는 30초 timeout이 있습니다. 브라우저가 응답하지 않으면 stop command가 실패할 수 있습니다.
- output path를 제공하지 않으면 profile은 agent-browser temp directory 아래 자동 생성된 path에 저장됩니다.
