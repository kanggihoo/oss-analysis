---
sha: "f8d46390613f068f232eb14ad91804841c64bdfa"
created: 2026-10-17
updated: 2026-10-17
sources:
  - hooks/hooks.json
  - .claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - docs/platform-support.md
  - .claude/settings.json
---

# [Q] context-mode는 Claude Code hook을 어떻게 정의하는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: `코드 확인` (hook 파일 내용) / Claude Code가 `hooks/hooks.json`을 자동 인식하는 규칙은 `추론` (레포 문서의 간접 언급만 확인)

---

## 1. 질문 및 결론

- **질문**: Claude Code hook을 어떤 파일에 어떤 형식으로 정의하는가?
- **핵심 결론**: 플러그인 루트의 `hooks/hooks.json` 한 파일에 "이벤트 → matcher(대상 도구 이름 정규식) → 실행할 command"를 적는다. 실행 command는 `node "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.mjs"`이고, 스크립트가 stdin으로 이벤트 JSON을 받아 stdout JSON으로 결정을 돌려준다. `plugin.json`에는 hook 항목이 없다.

---

## 2. 정의 구조

`hooks/hooks.json` (코드 확인):

```json
{
  "description": "...",
  "hooks": {
    "<이벤트>": [
      {
        "matcher": "<도구 이름 정규식, 빈 문자열이면 전체>",
        "hooks": [ { "type": "command", "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/x.mjs\"" } ]
      }
    ]
  }
}
```

| 요소 | 의미 | 이 레포의 예 |
|---|---|---|
| 이벤트 | 언제 실행되는가 | `PreToolUse`, `PostToolUse`, `PreCompact`, `UserPromptSubmit`, `SessionStart` |
| `matcher` | 어떤 도구일 때 실행되는가 (도구 이벤트에서만 의미) | `"Bash"`, `"Write\|Edit\|..."`, `"mcp__"`, 또는 `""` |
| `type: "command"` | 외부 프로세스로 실행 | 전부 `command` |
| `command` | 실행할 명령. `${CLAUDE_PLUGIN_ROOT}`는 플러그인 설치 경로 | `node ".../pretooluse.mjs"` |

이벤트별 matcher (코드 확인):

- `PreToolUse`: 9개 항목. `Bash`, `WebFetch`, `Read`, `Grep`, `Agent`, context-mode 자신의 MCP 도구 3개(`ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`), 그리고 모든 MCP 도구(`mcp__`). 전부 같은 스크립트 `pretooluse.mjs`를 가리킨다.
- `PostToolUse`: 한 항목에 `Bash|Read|Write|Edit|...|mcp__`를 `|`로 묶었다.
- `PreCompact`, `UserPromptSubmit`, `SessionStart`: matcher가 `""`라서 항상 실행.

## 3. 어떻게 Claude Code에 연결되는가

- 플러그인 manifest(`.claude-plugin/plugin.json`)는 MCP 서버(`mcpServers`)와 `skills`만 선언하고 hook 항목이 없다 (코드 확인). hook은 `hooks/hooks.json`이 따로 정의한다.
- `.claude-plugin/marketplace.json`은 이 레포 루트(`source: "./"`)를 플러그인 하나로 등록한다 (코드 확인).
- 레포 문서가 "Cursor manifest는 Claude 형식의 `./hooks/hooks.json`과 충돌하지 않도록 `hooks`를 `./hooks/cursor/hooks.json`으로 명시한다"고 쓴다 (`docs/platform-support.md` 508행). 이는 Claude Code가 `./hooks/hooks.json`을 이름 규칙으로 자동 인식한다는 뜻으로 읽힌다 (`추론`. Claude Code 공식 문서로 대조하지 않았다).
- 플러그인이 아니라 직접 설정하는 경로는 `~/.claude/settings.json`의 `hooks` 객체다 (`docs/platform-support.md` 47·52행: 문서 기재, 코드 확인 아님).

## 4. 주의할 점

- `.claude/settings.json`은 hook 정의가 아니다. 이 레포를 개발할 때 쓰는 `permissions`(deny: `sudo`, `rm -rf /*`, `.env` 읽기 / allow: git, ls, npm 등)만 있다 (코드 확인). "차단"에는 hook 방식과 permissions 방식이 따로 있다.
- 같은 hook이 플러그인과 설정 파일 양쪽에 등록되면 이벤트가 두 번 실행된다. Cursor 쪽 문서가 이 중복을 경고하고 `context-mode doctor`가 검사한다고 하며(`docs/platform-support.md` 510행), Claude Code에도 같은지는 `미확인`.
- README: 상태줄(statusLine)은 plugin manifest로 선언할 수 없어 `~/.claude/settings.json`을 직접 고쳐야 한다 (README 기재, 코드 확인 아님).

## 5. 남은 질문

- [ ] `pretooluse.mjs`가 stdin에서 무엇을 받고 어떤 JSON을 돌려주는가
- [ ] Claude Code가 `hooks/hooks.json`을 인식하는 규칙을 공식 문서와 대조
