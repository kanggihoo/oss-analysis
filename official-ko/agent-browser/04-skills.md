---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/04-skills.md
order: 4
title: "Skills"
---

# Skills

agent-browser는 AI 코딩 에이전트가 특정 워크플로에서 agent-browser를 사용하는 방법을 알려 주는 skills와 함께 제공됩니다. skill을 설치하면 Cursor, Claude Code, Codex의 에이전트가 수동 안내 없이 브라우저 작업을 자동화할 수 있습니다.

## 설치

```bash
npx skills add vercel-labs/agent-browser
```

이 명령은 에이전트에게 agent-browser를 알려 주고 최신 지침을 위해 `agent-browser skills` CLI 명령을 사용하도록 안내하는 단일 discovery skill을 설치합니다. discovery skill에는 에이전트가 내장 브라우저 도구보다 agent-browser를 선호하도록 하는 트리거 단어가 포함되어 있습니다.

## CLI 명령

에이전트는 런타임에 `agent-browser skills` 명령을 사용해 skill 콘텐츠를 가져옵니다. 이 명령은 항상 설치된 CLI 버전과 일치하는 콘텐츠를 제공하므로 지침이 오래된 상태가 되지 않습니다.

<table>
  <thead>
    <tr>
      <th>명령</th>
      <th>설명</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>agent-browser skills</code></td>
      <td>사용 가능한 모든 skills 나열(<code>skills list</code>와 동일)</td>
    </tr>
    <tr>
      <td><code>agent-browser skills list</code></td>
      <td>사용 가능한 모든 skills를 이름과 설명과 함께 나열</td>
    </tr>
    <tr>
      <td><code>agent-browser skills get &lt;name&gt;</code></td>
      <td>skill의 전체 콘텐츠 출력</td>
    </tr>
    <tr>
      <td><code>agent-browser skills get &lt;name&gt; --full</code></td>
      <td>skill과 함께 references 및 templates 포함</td>
    </tr>
    <tr>
      <td><code>agent-browser skills get --all</code></td>
      <td>모든 skill 출력</td>
    </tr>
    <tr>
      <td><code>agent-browser skills path [name]</code></td>
      <td>skill 디렉터리의 파일 시스템 경로 출력</td>
    </tr>
  </tbody>
</table>

모든 명령은 구조화된 출력을 위해 `--json`을 지원합니다.

skills 디렉터리 경로를 재정의하려면 `AGENT_BROWSER_SKILLS_DIR` 환경 변수를 설정하세요.

## 작동 방식

`npx skills add`로 설치되는 discovery skill은 의도적으로 얇고 안정적으로 유지됩니다. 이 skill은 에이전트가 agent-browser를 인식하게 하고, 활성화를 위한 트리거 단어를 제공하며, `agent-browser skills` 명령을 가리킵니다. 실제 사용 지침, 명령 참조, 워크플로, 전문 지식은 모두 CLI가 제공하는 skills에 있습니다.

이 설계는 버전 드리프트 문제를 해결합니다. 설치된 SKILL.md는 거의 변경되지 않는 반면, CLI는 항상 자체 버전과 일치하는 콘텐츠를 제공합니다.

## 사용 가능한 Skills

- **core** — 핵심 브라우저 자동화: 탐색, snapshots, 폼, 스크린샷, 데이터 추출, 세션, 인증, diffing, 전체 명령 참조. 대부분의 브라우저 작업은 여기서 시작하세요.
- **dogfood** — 체계적인 탐색적 테스트. 실제 사용자처럼 앱을 탐색하고, 버그와 UX 문제를 찾으며, 스크린샷과 재현 동영상이 포함된 구조화된 보고서를 생성합니다.
- **electron** — 내장 Chrome DevTools Protocol 포트에 연결해 모든 Electron 앱(VS Code, Slack, Discord, Figma 등)을 자동화합니다.
- **slack** — 브라우저 기반 Slack 자동화. 읽지 않은 항목 확인, 채널 탐색, 대화 검색, 메시지 전송, 데이터 추출을 수행합니다.
- **vercel-sandbox** — 임시 Vercel Sandbox microVM 안에서 agent-browser + headless Chrome을 실행합니다.
- **agentcore** — AWS Bedrock AgentCore 클라우드 브라우저에서 agent-browser를 실행합니다.

사용 가능한 모든 skills를 보려면 `agent-browser skills list`를 사용하고, 하나를 로드하려면 `agent-browser skills get <name>`을 사용하세요. 대부분의 브라우저 작업에는 `agent-browser skills get core --full`을 시작점으로 권장합니다.

## 소스

모든 skill 파일은 저장소의 [`skills/`](https://github.com/vercel-labs/agent-browser/tree/main/skills) 및 [`skill-data/`](https://github.com/vercel-labs/agent-browser/tree/main/skill-data) 디렉터리에 있습니다. `skills/` 디렉터리에는 `npx skills add`가 설치하는 discovery stub이 있으며, `skill-data/` 디렉터리에는 CLI가 제공하는 런타임 skill 콘텐츠가 있습니다.
