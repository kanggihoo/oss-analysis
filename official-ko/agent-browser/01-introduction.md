---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/01-introduction.md
order: 1
title: "agent-browser"
---

# agent-browser

AI 에이전트를 위해 설계된 브라우저 자동화 CLI입니다. 간결한 텍스트 출력으로 컨텍스트 사용량을 최소화합니다. 100% 네이티브 Rust로 작성되었습니다.

```bash
npm install -g agent-browser      # all platforms
brew install agent-browser        # macOS
agent-browser install             # Download Chrome (first time)

# or try without installing
npx agent-browser open example.com
```

## 기능

- **에이전트 우선**: 간결한 텍스트 출력은 JSON보다 토큰을 적게 사용하며, AI 컨텍스트 효율성을 위해 설계되었습니다
- **Ref 기반**: Snapshot은 결정적인 요소 선택을 위한 ref가 포함된 접근성 트리를 반환합니다
- **완전함**: 탐색, 폼, 스크린샷, 네트워크, 스토리지, 파일, 탭, 프레임, 디버깅을 위한 50개 이상의 명령을 제공합니다
- **관찰 가능**: [Video recording](/recording), [streaming](/streaming), [debugging](/debugging), [profiler](/profiler), [diffing](/diffing) 도구가 내장되어 있습니다
- **최신 앱**: [Network control](/network), [React & Web Vitals](/react), [init scripts](/init-scripts), [Next.js + Vercel](/next) 워크플로에는 일급 문서가 제공됩니다
- **상태 유지**: [Sessions](/sessions), 프로필, 인증 상태, 쿠키, 스토리지, 프록시, 보안 제어가 장시간 실행되는 에이전트를 지원합니다
- **크로스 플랫폼**: 네이티브 바이너리로 macOS, Linux, Windows를 지원합니다

## 함께 작동하는 도구

Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Google Gemini, opencode, 그리고 셸 명령을 실행할 수 있는 모든 에이전트에서 작동합니다.

## 예시

```bash
# Navigate and get snapshot
agent-browser open example.com
agent-browser snapshot -i

# Output:
# - heading "Example Domain" [ref=e1]
# - link "More information..." [ref=e2]

# Interact using refs
agent-browser click @e2
agent-browser screenshot page.png
agent-browser close
```

## 왜 refs인가요?

`snapshot` 명령은 각 요소에 `@e1`, `@e2` 같은 고유한 ref가 있는 간결한 접근성 트리를 반환합니다. 이를 통해 다음을 제공합니다.

- **컨텍스트 효율성**: 텍스트 출력은 전체 DOM의 ~3000-5000 토큰에 비해 ~200-400 토큰만 사용합니다
- **결정적**: Ref는 snapshot의 정확한 요소를 가리킵니다
- **빠름**: DOM을 다시 쿼리할 필요가 없습니다
- **AI 친화적**: LLM이 텍스트 출력을 자연스럽게 파싱합니다

## 아키텍처

최적의 성능을 위한 클라이언트-데몬 아키텍처입니다.

1. **Rust CLI**: 명령을 파싱하고 데몬과 통신합니다
2. **Native Daemon**: 직접 CDP를 사용하는 순수 Rust 데몬이며, Chrome DevTools Protocol을 통해 Chrome을 관리합니다

데몬은 자동으로 시작되며 명령 사이에도 계속 유지됩니다.

## 플랫폼

macOS(ARM64, x64), Linux(ARM64, x64), Windows(x64)를 위한 네이티브 Rust 바이너리를 제공합니다.
