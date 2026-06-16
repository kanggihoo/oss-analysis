---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/29-providers-browserbase.md
order: 29
title: "Browserbase"
---

# Browserbase

[Browserbase](https://browserbase.com)는 agentic browsing agents의 배포를 쉽게 만들기 위한 remote browser infrastructure를 제공합니다. local browser를 사용하기 어려운 environments에서 agent-browser를 실행할 때 사용하세요.

## 설정

```bash
agent-browser -p browserbase open https://example.com
```

또는 CI/scripts에는 환경 변수를 사용하세요.

```bash
agent-browser open https://example.com
```

`-p` flag는 `AGENT_BROWSER_PROVIDER`보다 우선합니다.

활성화되면 agent-browser는 로컬 브라우저를 실행하는 대신 Browserbase session에 연결합니다. 모든 commands는 동일하게 작동합니다.

API key는 [Browserbase Dashboard](https://browserbase.com/overview)에서 받으세요.
