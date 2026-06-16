---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/27-providers-agentcore.md
order: 27
title: "AgentCore"
---

# AgentCore

[AWS Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)는 SigV4 authentication을 사용하는 cloud browser sessions를 제공합니다. AWS environments에서 agent-browser를 실행하거나 AWS infrastructure 기반의 managed cloud browsers가 필요할 때 사용하세요.

## 설정

Credentials는 다음에서 자동으로 해석됩니다.

1. 환경 변수(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. SSO, profiles, IAM roles 등을 지원하는 AWS CLI(`aws configure export-credentials`)

```bash
agent-browser -p agentcore open https://example.com
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
    <tr><td><code>AGENTCORE_REGION</code></td><td>AgentCore endpoint용 AWS region</td><td><code>us-east-1</code></td></tr>
    <tr><td><code>AGENTCORE_BROWSER_ID</code></td><td>Browser identifier</td><td><code>aws.browser.v1</code></td></tr>
    <tr><td><code>AGENTCORE_PROFILE_ID</code></td><td>persistent state(cookies, localStorage)를 위한 browser profile</td><td>(none)</td></tr>
    <tr><td><code>AGENTCORE_SESSION_TIMEOUT</code></td><td>Session timeout in seconds</td><td><code>3600</code></td></tr>
    <tr><td><code>AWS_PROFILE</code></td><td>credential resolution용 AWS CLI profile</td><td><code>default</code></td></tr>
    <tr><td><code>AWS_ACCESS_KEY_ID</code></td><td>AWS access key(AWS CLI fallback 전에 확인됨)</td><td>(none)</td></tr>
    <tr><td><code>AWS_SECRET_ACCESS_KEY</code></td><td>AWS secret key</td><td>(none)</td></tr>
    <tr><td><code>AWS_SESSION_TOKEN</code></td><td>temporary session token(STS/SSO credentials용)</td><td>(none)</td></tr>
  </tbody>
</table>

## Browser Profiles

sessions 간 browser state(cookies, localStorage)를 유지하려면 `AGENTCORE_PROFILE_ID`를 사용하세요.

```bash
AGENTCORE_PROFILE_ID=my-profile agent-browser -p agentcore open https://example.com
```

profile이 설정되면 AgentCore는 sessions 사이에 browser state를 자동으로 저장하고 복원합니다.

## Live View

session이 시작되면 AgentCore는 stderr에 Live View URL을 출력합니다.

```
Session: abc123-def456
Live View: https://us-east-1.console.aws.amazon.com/bedrock-agentcore/browser/aws.browser.v1/session/abc123-def456#
```

AWS Console에서 agent session을 실시간으로 보려면 브라우저에서 이 URL을 여세요.

## Credential Resolution

AgentCore는 lightweight manual SigV4 signing을 사용합니다(AWS SDK dependency 없음). Credentials는 다음 순서로 해석됩니다.

1. **환경 변수**(`AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`, 선택적으로 `AWS_SESSION_TOKEN`)
2. **AWS CLI**(`aws configure export-credentials --format env`), SSO, IAM roles, credential files, profiles 지원

SSO를 사용하는 경우 agent-browser를 실행하기 전에 `aws sso login`을 실행하세요. 특정 named profile을 선택하려면 `AWS_PROFILE`을 설정하세요.

## 예시

```bash
# Basic usage (credentials auto-resolved via AWS CLI)
agent-browser -p agentcore open https://example.com

# With a browser profile for persistent login state
AGENTCORE_PROFILE_ID=my-profile agent-browser -p agentcore open https://x.com/home

# With explicit region
AGENTCORE_REGION=eu-west-1 agent-browser -p agentcore open https://example.com

# With SSO profile
AWS_PROFILE=my-sso-profile agent-browser -p agentcore open https://example.com
```

활성화되면 agent-browser는 로컬 브라우저를 실행하는 대신 AgentCore cloud browser session에 연결합니다. 모든 commands는 동일하게 작동합니다.
