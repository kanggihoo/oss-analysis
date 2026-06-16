---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/02-installation.md
order: 2
title: "Installation"
---

# 설치

## 전역 설치(권장)

최대 성능을 위해 네이티브 Rust 바이너리를 설치합니다.

```bash
npm install -g agent-browser
agent-browser install  # Download Chrome from Chrome for Testing (first time)
```

이 옵션이 가장 빠릅니다. 명령은 네이티브 Rust CLI를 통해 직접 실행되며, 파싱 오버헤드는 밀리초 미만입니다.

## 빠른 시작(설치 없음)

```bash
npx agent-browser install   # Download Chrome (first time only)
npx agent-browser open example.com
```

## 프로젝트 설치(로컬 의존성)

`package.json`에 버전을 고정하려는 프로젝트용입니다.

```bash
npm install agent-browser
npx agent-browser install  # Download Chrome (first time)
```

그런 다음 `npx` 또는 `package.json` 스크립트를 통해 사용합니다.

## Homebrew(macOS)

```bash
brew install agent-browser
agent-browser install  # Download Chrome (first time)
```

## Cargo(Rust)

```bash
cargo install agent-browser
agent-browser install  # Download Chrome (first time)
```

소스에서 컴파일합니다(~2-3분). Node.js 24+, pnpm 11+, Rust 툴체인([rustup.rs](https://rustup.rs))이 필요합니다.

## 소스에서 설치

```bash
git clone https://github.com/vercel-labs/agent-browser
cd agent-browser
pnpm install
pnpm build
pnpm build:native
./bin/agent-browser install
pnpm link --global
```

## Linux 의존성

Linux에서는 시스템 의존성을 설치합니다.

```bash
agent-browser install --with-deps
```

## 업데이트

최신 버전으로 업그레이드합니다.

```bash
agent-browser upgrade
```

설치 방법(npm, Homebrew 또는 Cargo)을 감지하고 적절한 업데이트 명령을 자동으로 실행합니다. 성공하면 버전 변경 사항을 표시하고, 이미 최신 버전이면 이를 알려 줍니다.

## Doctor

`doctor`는 설치 상태를 진단하고 오래된 데몬 파일을 자동으로 정리합니다. 무언가가 예기치 않게 작동을 멈췄거나 업그레이드 후에 실행하세요.

```bash
agent-browser doctor                     # Full diagnosis
agent-browser doctor --offline --quick   # Local-only, fastest (~<1s)
agent-browser doctor --fix               # Also run destructive repairs
agent-browser doctor --json              # Structured output
```

다음을 확인합니다.

<table>
<thead>
<tr><th>범주</th><th>확인 항목</th></tr>
</thead>
<tbody>
<tr><td>환경</td><td>CLI 버전, 플랫폼, 홈 디렉터리, 상태 및 소켓 디렉터리, 여유 디스크 공간</td></tr>
<tr><td>Chrome</td><td>Chrome 설치 경로와 버전, 캐시 디렉터리, Puppeteer 폴백, user-data 디렉터리와 프로필 수, 선택적 <code>lightpanda</code> 엔진</td></tr>
<tr><td>데몬</td><td>세션별 실행 중인 데몬, 오래된 <code>.sock</code> / <code>.pid</code> / <code>.version</code> / <code>.stream</code> 파일(자동 정리됨), CLI와의 버전 불일치, 대시보드 프로세스 활성 상태</td></tr>
<tr><td>구성</td><td><code>~/.agent-browser/config.json</code>, <code>./agent-browser.json</code>, 그리고 <code>AGENT_BROWSER_CONFIG</code>에 있는 모든 파일이 유효한 JSON으로 파싱되는지 확인</td></tr>
<tr><td>보안</td><td>암호화 키 환경 변수 또는 <code>~/.agent-browser/.encryption-key</code>(unix에서 0600 권한), 상태 파일 수와 수명 및 <code>AGENT_BROWSER_STATE_EXPIRE_DAYS</code> 비교, 작업 정책 파일</td></tr>
<tr><td>Providers</td><td>Browserless, Browserbase, Browser Use, Kernel, AgentCore(AWS 자격 증명), Appium(<code>--provider ios</code>용), 채팅용 <code>AI_GATEWAY_API_KEY</code>의 환경 변수</td></tr>
<tr><td>네트워크</td><td>Chrome for Testing CDN, AI Gateway(구성된 경우), 현재 선택된 provider 엔드포인트의 도달 가능성(<code>--offline</code>에서는 건너뜀)</td></tr>
<tr><td>실행 테스트</td><td>임시 세션을 생성하고 headless Chrome을 실행한 뒤 <code>about:blank</code>로 이동한 다음 닫습니다. 실제 경과 시간을 측정합니다(<code>--quick</code>에서는 건너뜀)</td></tr>
</tbody>
</table>

오래된 사이드카 파일은 항상 정리됩니다. 파괴적 작업은 `--fix`를 통해 명시적으로 선택해야 합니다.

<table>
<thead>
<tr><th>검사</th><th><code>--fix</code>가 수행하는 작업</th></tr>
</thead>
<tbody>
<tr><td>Chrome 누락</td><td><code>agent-browser install</code> 실행</td></tr>
<tr><td>버전이 일치하지 않는 데몬</td><td>각 데몬에 <code>close</code>를 보내고 파일을 정리</td></tr>
<tr><td>오래된 상태 파일</td><td><code>AGENT_BROWSER_STATE_EXPIRE_DAYS</code>보다 오래된 상태 파일 삭제(기본값 30)</td></tr>
<tr><td>암호화 키 누락</td><td><code>~/.agent-browser/.encryption-key</code>에 새 키 생성(0600, unix). 기존 키를 덮어쓰지 않음</td></tr>
</tbody>
</table>

모든 검사를 통과하면 종료 코드는 `0`입니다(경고는 괜찮습니다). 실패한 검사가 있으면 `1`입니다.

## 사용자 지정 브라우저

번들된 Chromium 대신 사용자 지정 브라우저 실행 파일을 사용합니다.

- **Serverless** - `@sparticuz/chromium` 사용(~50MB vs ~684MB)
- **System browser** - 기존 Chrome 설치 사용
- **Custom builds** - 수정된 브라우저 빌드 사용

```bash
# Via flag
agent-browser --executable-path /path/to/chromium open example.com

# Via environment variable
AGENT_BROWSER_EXECUTABLE_PATH=/path/to/chromium agent-browser open example.com
```

### Serverless 예시

`@sparticuz/chromium` 또는 유사한 패키지를 사용해 Chromium 실행 파일 경로를 얻은 다음, `--executable-path` 또는 `AGENT_BROWSER_EXECUTABLE_PATH`로 전달합니다.

## AI 에이전트 설정

agent-browser는 어떤 AI 에이전트와도 기본적으로 바로 작동합니다. 더 풍부한 컨텍스트를 원한다면 다음을 사용하세요.

### AI 코딩 어시스턴트(권장)

AI 코딩 어시스턴트용 skill을 설치합니다.

```bash
npx skills add vercel-labs/agent-browser
```

Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, Goose, OpenCode, Windsurf와 함께 작동합니다. skill은 저장소에서 가져오며 자동으로 최신 상태를 유지합니다.

> `node_modules`에서 `SKILL.md`를 복사하지 **마세요**. 새 기능이 추가되면 오래된 상태가 됩니다. 항상 `npx skills add`를 사용하거나 저장소 버전을 참조하세요.

### AGENTS.md / CLAUDE.md

지침 파일에 추가하세요.

```markdown
## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:
1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes
```
