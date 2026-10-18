---
sha: "1486f2042c87bb547a4e34808ab54ab34a33f132"
created: 2026-10-17
updated: 2026-10-17
sources:
  - src/main/utils/jsonl.ts
  - src/main/constants/messageTags.ts
  - src/main/services/discovery/SessionContentFilter.ts
---

# [Q2] claude-devtools는 system prompt를 보여 주는가, 로그에는 있는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 코드 확인 (claude-devtools) + 실행 확인 (이 PC의 실제 로그 610개 세션) / 로그 형식의 버전별 차이는 미확인
- **이 문서로 만든 스펙**: [claude-code-session-log-reading](../capabilities/claude-code-session-log-reading.md) R-15

## 답

1. **로그에는 system prompt가 있다.** `type: "attachment"` 줄의 `attachment.type == "prompt_snapshot"`이고 `systemPrompt`는 문자열 목록이다. 610개 세션 중 576개에 있다. `실행 확인` ([스크립트](../../../artifacts/claude-devtools/log-format-demos/attachment_types.py), [출력](../../../artifacts/claude-devtools/log-format-demos/2026-10-17-attachment-output.txt))
2. **devtools는 이 줄을 읽는 단계에서 버린다.** `parseMessageType`이 `user`/`assistant`/`system`/`summary`/`file-history-snapshot`/`queue-operation` 외에는 `null`을 돌려주고, 주석도 "Unknown types are skipped"이다(`src/main/utils/jsonl.ts:199-217`). `attachment`는 이 목록에 없다. `코드 확인`
3. **"일부러 숨긴다"는 근거는 없다.** 의도가 드러나는 필터는 `<system-reminder>`·`<local-command-caveat>`로만 된 user 줄을 목록에서 제외하는 것(`SessionContentFilter.ts:38`)뿐이다. system prompt 생략은 type 화이트리스트의 부작용으로 보인다. `추론`
4. **`attachment`에는 system prompt 외에도 주입된 지침이 있다.** `instructions`(AGENTS.md 등), `skill_listing`, `mcp_instructions_delta`, `environment`, `session_context` 등 35종(`prompt_snapshot` 1163건, `total_tokens_reminder` 13037건 포함). `실행 확인`

## 미확인

- `prompt_snapshot`이 모델이 받은 system prompt **전체**인지. 한 세션(스냅샷 5개)에서는 `systemPrompt`가 매번 같았고(13조각, 10,660자), `You are Claude Code…` 한 줄은 `cliPrefix`, 도구 정의는 `tools`로 따로 있었다. 이 세션 안의 실제 system prompt 본문과 조각 구성이 맞는다. `실행 확인`(한 세션). 다른 세션에서 `systemPrompt`가 달라지는지(전체 길이 291~15,019자)는 `미확인`
- 이 형식이 Claude Code 어느 버전부터인지. 34개 세션에는 스냅샷이 없다. `미확인`
