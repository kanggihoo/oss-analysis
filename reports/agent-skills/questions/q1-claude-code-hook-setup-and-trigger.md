---
sha: "aeac41d4d005999432bb7312f7ff06383a91d59d"
created: 2026-10-17
updated: 2026-10-17
sources:
  - hooks/SDD-CACHE.md
  - hooks/SIMPLIFY-IGNORE.md
  - hooks/sdd-cache-pre.sh
  - hooks/sdd-cache-post.sh
  - hooks/simplify-ignore.sh
---

# [Q] Claude Code hook은 어떻게 설정하고, 트리거되면 어떻게 동작하는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 스크립트가 가정하는 입출력은 `코드 확인`. Claude Code 본체가 실제로 그렇게 동작하는지는 이 레포 코드·문서에 기댄 `추론` (Claude Code 공식 문서·실행으로 대조하지 않음)

---

## 1. 질문 및 결론

- **질문**: 이 레포 기준으로 Claude Code hook 설정 방법과, 트리거됐을 때 hook 스크립트가 받는 것·돌려주는 것은?
- **핵심 결론**: 설정은 `.claude/settings.json`의 `hooks`에 "이벤트 → matcher → command"로 적는다. 트리거되면 Claude Code가 command를 실행하며 stdin으로 이벤트 JSON을 넘기고, 스크립트는 **exit code와 stderr**로 반응한다. exit 0은 통과, exit 2는 차단이며 stderr가 에이전트에게 전달된다.

## 2. 설정

```json
{ "hooks": {
    "PreToolUse":  [ { "matcher": "WebFetch",
        "hooks": [ { "type": "command",
                     "command": "bash \"${CLAUDE_PROJECT_DIR}/hooks/sdd-cache-pre.sh\"",
                     "timeout": 10 } ] } ],
    "PostToolUse": [ { "matcher": "WebFetch",
        "hooks": [ { "type": "command", "command": "...sdd-cache-post.sh",
                     "async": true, "timeout": 10 } ] } ],
    "Stop": [ { "hooks": [ { "type": "command", "command": "...simplify-ignore.sh" } ] } ]
} }
```

(`hooks/SDD-CACHE.md`, `SIMPLIFY-IGNORE.md` Setup: 코드 확인)

| 키 | 뜻 |
|---|---|
| 이벤트(`PreToolUse` 등) | 언제 실행되는가 |
| `matcher` | 어떤 도구일 때 (`Read`, `Edit\|Write`, `WebFetch`). `Stop`은 matcher 없음 |
| `command` | 실행할 명령. `${CLAUDE_PROJECT_DIR}`는 Claude Code를 실행한 프로젝트 디렉토리 |
| `timeout` | 제한 시간(초 단위로 보임, 단위는 `미확인`) |
| `async: true` | 기다리지 않고 백그라운드로 실행. 결과가 필요 없는 `PostToolUse` 저장에 사용 |

설정 위치는 프로젝트 `.claude/settings.json` 또는 개인용 `.claude/settings.local.json` (`SDD-CACHE.md`).

## 3. 트리거되면 일어나는 일

**받는 것**: stdin으로 JSON. 이 레포 스크립트가 읽는 필드는 다음과 같다 (코드 확인).
- 공통: `tool_name`
- `PreToolUse`: `tool_input` (예: `.tool_input.url`, `.tool_input.file_path`)
- `PostToolUse`: `tool_input` + `tool_response` (`SDD-CACHE.md` smoke test 예시)

**돌려주는 것**: 이 레포의 hook은 JSON 출력을 쓰지 않고 exit code와 stderr만 쓴다 (`permissionDecision` 등 검색 결과 없음: 코드 확인).

| 반응 | 효과 | 이 레포의 사용 |
|---|---|---|
| exit 0 | 통과. 도구가 그대로 실행됨 | 캐시 없음·의존성 없음·대상 아님 등 거의 모든 경로 |
| **exit 2 + stderr** | 도구 실행을 막고(`PreToolUse`) stderr를 에이전트에 도구 오류로 전달 | `sdd-cache-pre.sh` 106행: 캐시 적중 시 캐시 본문을 stderr로 보냄. `simplify-ignore.sh`: `PostToolUse`에서 placeholder가 지워졌을 때 "되돌려라"는 메시지 |
| exit 1 | 이 레포에서는 의존성 누락(`jq` 없음) 오류 표시 | `simplify-ignore.sh` 28행 |

(exit 2의 의미는 `sdd-cache-pre.sh` 주석 "exits 2 and writes the cached body to stderr so Claude Code can deliver it to the agent", `SDD-CACHE.md` "blocked via exit code 2 ... delivers stderr as a tool error"에 근거: 레포 설명이며 `추론`)

## 4. 예: WebFetch가 호출될 때 (`sdd-cache`)

1. 에이전트가 `WebFetch(url, prompt)` 호출 → `PreToolUse`(WebFetch)가 `sdd-cache-pre.sh` 실행.
2. 스크립트가 `.tool_input.url`을 읽고 `.claude/sdd-cache/<sha256(url)>.json`이 있는지 확인. 없으면 exit 0 → WebFetch 진행.
3. 있으면 저장된 `ETag`/`Last-Modified`로 HEAD 요청. 304가 아니면 exit 0.
4. 304이면 캐시 본문을 stderr에 쓰고 **exit 2** → WebFetch는 실행되지 않고 에이전트는 캐시 본문을 받음.
5. WebFetch가 실제로 실행됐다면 `PostToolUse`가 `sdd-cache-post.sh`를 `async`로 실행해 응답과 현재 `ETag`를 저장.

의존성(`jq`, `curl`, `shasum`)이 없으면 전부 exit 0으로 빠져서 도구를 막지 않는다 (fail-open: `sdd-cache-pre.sh` 21~23행).

## 5. 예: Read/Edit 사이클 (`simplify-ignore`)

`PreToolUse` Read에서 hook이 막지 않고 **파일 내용을 직접 바꿔 놓는다**. 도구는 그대로 실행되어 모델은 바뀐 파일을 읽는다. 이후 `Edit|Write`의 `PostToolUse`에서 복원하고, 모델이 placeholder를 지웠으면 exit 2로 알린다. 마지막 `Stop`에서 한 번 더 복원한다 (`simplify-ignore.sh` 상단 주석, 346~400행).

## 6. 남은 질문

- [ ] `PreToolUse`에서 exit 2와 JSON `permissionDecision` 방식의 차이 (context-mode는 JSON 방식, agent-skills는 exit code 방식)
- [ ] `timeout` 단위, `async` 동작을 공식 문서와 대조
- [ ] `Stop` hook이 exit 2를 내면 어떻게 되는가
