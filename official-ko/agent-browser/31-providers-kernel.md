---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/31-providers-kernel.md
order: 31
title: "Kernel"
---

# Kernel

[Kernel](https://www.kernel.sh)은 stealth mode와 persistent profiles 같은 기능을 갖춘 AI agents용 cloud browser infrastructure를 제공합니다.

## 설정

```bash
agent-browser -p kernel open https://example.com
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
    <tr><td><code>KERNEL_API_KEY</code></td><td>API key(필수)</td><td></td></tr>
    <tr><td><code>KERNEL_HEADLESS</code></td><td>headless mode로 browser 실행</td><td><code>true</code></td></tr>
    <tr><td><code>KERNEL_STEALTH</code></td><td>bot detection을 피하기 위해 stealth mode 활성화</td><td><code>false</code></td></tr>
    <tr><td><code>KERNEL_TIMEOUT_SECONDS</code></td><td>Session timeout in seconds</td><td><code>300</code></td></tr>
    <tr><td><code>KERNEL_PROFILE_NAME</code></td><td>persistent cookies/logins를 위한 browser profile name</td><td>(none)</td></tr>
  </tbody>
</table>

**Profile persistence:** `KERNEL_PROFILE_NAME`이 설정되면 profile이 아직 없을 경우 생성됩니다. Cookies, logins, session data는 browser session이 끝날 때 자동으로 profile에 다시 저장되어 향후 sessions에서 사용할 수 있습니다.

활성화되면 agent-browser는 로컬 브라우저를 실행하는 대신 Kernel cloud session에 연결합니다. 모든 commands는 동일하게 작동합니다.

API key는 [Kernel Dashboard](https://dashboard.onkernel.com)에서 받으세요.
