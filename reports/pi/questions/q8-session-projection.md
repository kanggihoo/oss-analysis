# Q8: 세션 파일에서 모델에게 보낼 대화를 어떻게 만드나?

- **Commit**: `4259686d9290c0d73ae7192b796aee3e530a9779` · **작성일**: 2026-09-29 · **목적**: 학습 (Q7 후속)
- **대상**: `packages/coding-agent/src/core/session-manager.ts` (2013줄 중 entry 타입, 저장, projection 구간), `core/messages.ts` `convertToLlm`, `core/compaction/compaction.ts` `prepareCompaction`/`findProjectedCutPoint`
- **관련 그림**: [세션 파일 → 모델 컨텍스트](../diagrams/session-projection-dataflow.html)

## 결론

세션 파일은 **덧붙이기만 하는(append-only) JSONL 트리**다. 기존 줄은 절대 고치지 않는다. 요약(compaction), 실패한 시도 숨기기, 내용 교체는 모두 **새 entry를 추가**하는 방식으로 표현한다. 모델에게 보낼 대화(projection)는 요청할 때마다 이 트리를 처음부터 해석해서 만든다. `코드 확인`

```
세션 파일 (JSONL, append-only)
  → 현재 leaf에서 root까지 경로 (가지 선택)
  → 최신 compaction 기준으로 자르기
  → context_edit 적용 (숨김·교체)
  → entry → 메시지 변환
  = SessionProjection.messages   → prepareRequest → convertToLlm → LLM
```

## 1. 저장 형식: id/parentId 트리

- 모든 entry에는 `id`와 `parentId`가 있다(`SessionEntryBase`, :57). 새 entry의 `parentId`는 현재 `leafId`이고, 추가한 뒤에는 `leafId`가 새 entry로 옮겨 간다(`_appendEntry`, :1191).
- 파일은 한 줄에 entry 하나인 JSONL이고 `appendFileSync`로 덧붙인다(`_persist`, :1172).
- 파일은 **user나 assistant 메시지가 처음 생길 때** 만든다. 그 전의 설정 entry(모델, thinking level)는 메모리에만 있다. 그래서 pi를 열었다가 대화 없이 닫으면 파일이 남지 않는다(:1160-1170 주석, #10000).
- 기본 위치: `~/.pi/agent/sessions/--<cwd 경로>--/`(:587 주석)
- **가지치기(branch)**: `branch(id)`는 `leafId`를 과거 entry로 옮기기만 한다(:1579). 그다음 추가하는 entry는 그 지점의 새 자식이 된다. 옛 가지는 파일에 그대로 남는다.

### entry 종류 (`SessionEntry`, :183)

| type | 모델 컨텍스트에 들어가나 | 용도 |
|---|---|---|
| `message` | O | system/user/assistant/toolResult, custom, bashExecution 메시지 |
| `custom_message` | O (user 메시지로 변환) | extension이 대화에 주입하는 메시지. `display`로 TUI 표시 여부를 정한다 |
| `compaction` | O (요약 메시지로) | `summary`, `firstKeptEntryId`, `tokensBefore`, 선택적으로 당시 `systemMessage` |
| `branch_summary` | O (요약 메시지로) | 버린 가지의 요약 |
| `context_edit` | 다른 entry를 수정 | `targetId`의 내용을 교체하거나(`replacement`) 숨긴다(`null`) |
| `model_change`, `thinking_level_change` | X (설정으로 반영) | 복원할 모델과 thinking level |
| `custom` | X | extension 상태 저장용 |
| `usage`, `label`, `session_info` | X | 사용량 기록, 북마크, 세션 이름 |

## 2. projection 만드는 과정 (`buildSessionProjection`, :543)

1. **경로 (`buildSessionPath`, :390)**: `leafId`에서 `parentId`를 따라 root까지 올라간 뒤 뒤집는다. 현재 가지에 속한 entry만 남는다.
2. **설정 (`getSessionContextSettings`, :418)**: 경로에서 마지막 `thinking_level_change`와 마지막 모델을 찾는다. 모델은 `model_change`나 assistant 메시지의 provider/model 중 나중에 나온 것을 쓴다.
3. **compaction으로 자르기 (`buildContextEntries`, :476)**: 경로에서 **가장 최근 compaction**을 찾는다. 결과는 다음 순서로 조립된다. 그보다 오래된 entry는 버린다.
   - 그 compaction entry
   - compaction 이전 entry 중 `firstKeptEntryId`부터의 것 (system 메시지 제외)
   - compaction 이후의 entry 전부
4. **편집 적용 (`projectContextEntry`, :519)**: `context_edit`를 `targetId`별로 모은다. 같은 대상에 편집이 여러 개면 나중 것이 이긴다(Map 덮어쓰기).
   - `replacement: null`이면 그 entry를 모델 컨텍스트에서 뺀다.
   - 값이 있으면 content만 바꾸고, role·timestamp 같은 메타데이터는 그대로 둔다.
5. **메시지 변환 (`sessionEntryToContextMessages`, :439)**: entry를 `AgentMessage[]`로 바꾼다. 방어 코드가 있어서 content가 null인 옛 파일이나 손으로 고친 파일도 빈 content로 바꿔 처리한다.

결과에는 `entries`(각 메시지가 어느 entry에서 왔는지)와 `messages`가 함께 들어 있다. `AgentSession`은 `entries`를 써서 메시지 객체와 entry id를 연결한다(`_refreshFinalizedContext`, agent-session.ts:897).

## 3. LLM 메시지로 바꾸기 (`convertToLlm`, messages.ts:149)

projection에는 pi 전용 메시지 role이 섞여 있다. `convertToLlm`이 LLM이 이해하는 형태로 바꾼다.

| AgentMessage role | LLM 메시지 |
|---|---|
| `compactionSummary` | `user`: "The conversation history before this point was compacted into the following summary: `<summary>…</summary>`" |
| `branchSummary` | `user` (branch 요약 prefix/suffix로 감쌈) |
| `custom` | `user` |
| `bashExecution` | `user` (명령과 출력 텍스트). `!!` 접두어로 실행한 것(`excludeFromContext`)은 뺀다 |
| system/user/assistant/toolResult | 그대로 |

## 4. 이 구조가 Q7의 동작을 가능하게 한다

| Q7에서 본 동작 | 세션 파일에서 일어나는 일 |
|---|---|
| 실패한 재시도 시도를 모델에게서 숨김 (`_omitRecoveryAttempt`) | 실패한 assistant entry를 대상으로 `appendContextEdit(targetId, null)` (agent-session.ts:1202). 원래 줄은 파일에 남는다 |
| compaction | `CompactionEntry { summary, firstKeptEntryId }`를 추가. 다음 projection부터 그 앞은 요약 하나로 바뀐다 |
| `prepareRequest`가 매번 context를 교체 | 위 편집들이 다음 요청에 바로 반영된다 |

"원본은 지우지 않고, 해석 규칙으로 모델이 볼 것을 정한다"는 설계다. 그래서 과거 가지로 돌아가거나(branch) 기록을 감사(audit)할 때 원래 내용을 그대로 복원할 수 있다. `코드 확인` (설계 의도는 `추론`)

## 5. compaction은 어디서 자르나 (`prepareCompaction`, compaction.ts:894)

- **언제**: `contextTokens > contextWindow - reserveTokens`일 때(`shouldCompact`, :289). 기본값은 `reserveTokens: 16384`, `keepRecentTokens: 20000`(:150).
- **어디서 자르나** (`findProjectedCutPoint`, :828): 최신 메시지부터 거꾸로 토큰을 더해 가다가 `keepRecentTokens`를 넘는 지점에서 자른다. 자를 수 있는 위치는 user나 assistant 메시지뿐이고 tool 결과에서는 자르지 않는다. assistant의 tool 호출과 그 결과가 떨어지지 않게 하기 위해서다(:458 주석).
- **turn 중간에서 잘리면** (`isSplitTurn`): 그 turn의 앞부분(`turnPrefixMessages`)을 따로 요약 대상으로 넘긴다.
- **이전 요약 이어받기**: 이미 compaction이 있으면 그 `summary`를 `previousSummary`로 넘기고, 그 뒤부터만 새로 요약한다.
- **파일 작업 추적**: 요약할 메시지에서 읽고 수정한 파일 목록(`fileOps`)을 뽑아 둔다. 요약에 쓰이는지는 `미확인`
- 경로의 마지막 entry가 이미 compaction이면 다시 하지 않는다.

## 남은 질문

- `compact()` / `generateSummary`: 요약 prompt 내용과 `fileOps` 사용 방식
- `branchWithSummary`: 가지를 옮길 때 버린 가지의 요약은 언제 만드나 (`branch-summarization.ts`)
- 세션 버전 마이그레이션(`migrateSessionEntries`, `CURRENT_SESSION_VERSION = 3`)
