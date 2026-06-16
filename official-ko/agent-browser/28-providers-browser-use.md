---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/28-providers-browser-use.md
order: 28
title: "Browser Use"
---

# Browser Use

[Browser Use](https://browser-use.com)는 AI agents를 위한 cloud browser infrastructure를 제공합니다. local browser를 사용할 수 없는 environments(serverless, CI/CD 등)에서 agent-browser를 실행할 때 사용하세요.

## 설정

```bash
agent-browser -p browseruse open https://example.com
```

또는 CI/scripts에는 환경 변수를 사용하세요.

```bash
agent-browser open https://example.com
```

`-p` flag는 `AGENT_BROWSER_PROVIDER`보다 우선합니다.

활성화되면 agent-browser는 로컬 브라우저를 실행하는 대신 Browser Use cloud session에 연결합니다. 모든 commands는 동일하게 작동합니다.

API key는 [Browser Use Cloud Dashboard](https://cloud.browser-use.com/settings?tab=api-keys)에서 받으세요. 시작할 수 있는 free credits가 제공되며, 이후에는 pay-as-you-go pricing이 적용됩니다.
