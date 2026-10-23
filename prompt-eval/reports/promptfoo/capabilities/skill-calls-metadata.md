---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/types/providers.ts
  - src/providers/claude-agent-sdk.ts
  - src/providers/opencode-sdk.ts
  - src/providers/openai/codexSkillMetadata.ts
  - src/providers/openai/codex-sdk.ts
  - src/providers/openai/codex-app-server.ts
  - src/providers/openai/codex-security.ts
  - src/providers/openai/codexProcess.ts
  - src/assertions/skill.ts
  - src/assertions/traceUtils.ts
  - src/assertions/index.ts
  - site/docs/configuration/expected-outputs/deterministic.md
  - site/docs/providers/openai-codex-sdk.md
  - site/docs/providers/opencode-sdk.md
depends: []
status: ready
reimplementation: 미실행
---

# SkillCallEntry 메타데이터 계약 (`response.metadata.skillCalls`)

> 에이전트 provider가 한 번의 호출에서 관찰한 "스킬 사용"을 `response.metadata.skillCalls`(항목 `{name, input?, path?, source?, is_error?}`의 배열)로 기록하고, `skill-used` / `not-skill-used` 어서션이 그 배열만 읽어 통과 여부를 정하는 생산자-소비자 계약이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 에이전트 provider(Claude Agent SDK / OpenCode SDK / Codex SDK·app-server / Codex Security)가 한 번의 `callApi` 안에서 도구 호출·명령 실행 기록을 모은다.
2. provider마다 자기 방식으로 "스킬을 썼다"는 증거를 골라 `SkillCallEntry`로 바꾼다. Claude·OpenCode는 스킬 도구 호출 자체(`source: 'tool'`), Codex는 셸 명령 문자열 속 `SKILL.md` 경로(`source: 'heuristic'`)다.
3. 결과를 `ProviderResponse.metadata.skillCalls`에 넣어 돌려준다. 비에이전트 provider는 이 필드를 만들지 않는다.
4. 평가가 끝난 응답이 `runAssertion`에 `providerResponse`로 전달되면, `skill-used` 핸들러는 `metadata.skillCalls`에서 `is_error`가 `true`가 아닌 항목만 남긴다.
5. 어서션의 `value`(문자열 / 문자열 배열 / `{name|pattern, min, max}`)를 해석해 남은 항목과 맞춰 보고, `pass`·`score`(1 또는 0)·`reason`을 가진 `GradingResult`를 돌려준다. `not-skill-used`는 같은 핸들러에 `inverse = true`가 전달된 것이다.

### 1.2 범위·통합 지점 [필수]
- 제공: ① `SkillCallEntry` 항목 모양과 각 필드의 의미, ② provider별 채우기 규칙(요약), ③ `skill-used` 소비 규칙.
- 제외: 에이전트 provider의 전체 옵션·캐시·세션·트레이스(별도 스펙 `agent-providers`). `skill-used` 이외 어서션과 `not-` 반전의 공통 처리(별도 스펙 `assertion-family`). 스킬을 SDK가 실제로 찾고 로딩하는 일(외부 SDK, 아래 확인 한계).
- 외부 의존·선행 계약: 생산자는 SDK가 준 도구 호출·메시지·명령 항목(`ToolCallEntry`, OpenCode 메시지 `parts`, Codex `items`)에 의존한다. 소비자는 어서션 호출 규약 `AssertionParams`(`providerResponse`, `renderedValue`/`assertion.value`, `inverse`)에 의존하며, 이 경계는 아래 1.3에서 필요한 만큼만 정의한다.
- 소유 상태·부작용: 없다. 생산자는 응답 객체에 필드를 쓰고, 소비자는 읽기만 한다. 영속화·캐시는 `ProviderResponse` 전체가 따라가는 것이고 이 계약은 따로 다루지 않는다(agent-providers 소관, 이 스펙에서는 읽지 않음).

### 1.3 인터페이스와 데이터 의미 [필수]

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `response.metadata.skillCalls` | `list<SkillCallEntry>` (optional) | `metadata`는 `map<string, any>`이다. 이 필드가 배열이 아니거나 없으면 소비자는 빈 목록으로 취급한다. 순서는 생산자가 만든 순서이고 소비자는 순서를 쓰지 않는다. |
| `SkillCallEntry.name` | string (필수) | 스킬 이름. 소비자가 보는 유일한 필수 필드이고, 문자열이 아닌 항목은 소비 단계에서 버려진다. Claude·OpenCode 생산자는 앞뒤 공백을 제거한 값을 넣고 빈 이름은 항목으로 만들지 않는다. Codex는 경로에서 뽑은 이름(R-09), Codex Security는 작업 이름(R-12)이다. |
| `SkillCallEntry.input` | any (optional) | 스킬 도구 호출의 원본 입력. Claude는 도구 입력 객체 전체(`{skill: ...}` + 그 밖의 키), OpenCode는 `state.input`. Codex 항목에는 없다. 소비자는 읽지 않는다. |
| `SkillCallEntry.path` | string (optional) | 읽은 `SKILL.md` 경로. OpenCode는 결과 메타데이터에 스킬 디렉터리가 있을 때만, Codex는 항상(명령에 적힌 정규화된 경로), Claude는 절대 넣지 않는다. 소비자는 사유 문자열 표시에만 쓴다. |
| `SkillCallEntry.source` | `'tool'` \| `'heuristic'` (optional) | `'tool'` = 스킬 도구 호출을 그대로 옮김(Claude, OpenCode). `'heuristic'` = 명령 문자열에서 추정(Codex). Codex Security 항목은 이 필드가 없다. 소비자는 사유 문자열 표시에만 쓴다. |
| `SkillCallEntry.is_error` | boolean (optional) | `true`이면 그 호출은 실패로 기록된 것이고 소비자가 무시한다. Claude 항목은 항상 이 필드를 가진다(`true`/`false`). OpenCode는 실패일 때만 `true`를 넣고 아니면 필드를 생략한다. Codex 항목은 없다. 소비자는 `=== true`인 것만 제외하므로 없음·`false`는 성공으로 본다. |
| `metadata.attemptedSkillCalls` | `list<SkillCallEntry>` (optional) | Codex 전용. 성공 여부와 무관하게 명령에서 찾은 항목. `skillCalls`보다 길 때만 넣는다. 소비자(어서션)는 읽지 않는다. |
| `skill-used` 어서션 `value` | string \| list<string> \| `{name?, pattern?, min?, max?}` | 문자열 / 문자열 배열: 이름 정확 일치 목록. 객체: `name`(정확 일치) 또는 `pattern`(glob)이 하나 이상 있어야 하고, `min`/`max`는 0 이상 정수. 규칙은 R-11~R-16. |
| 어서션 결과 | `{pass: bool, score: 1 \| 0, reason: string, assertion}` | 점수는 이진이다. `reason`에 실제로 관찰된 스킬 목록(`이름 (source, path)` 형식, 없으면 `(none)`)을 적는다. |

### 1.4 행동 규칙과 남은 질문 [필수]

생산자 규칙

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 항목 모양 | `SkillCallEntry`는 `name`만 필수이고 `input`, `path`, `source`(`'heuristic'`\|`'tool'`), `is_error`는 모두 선택이다. 이 타입에 `attemptedSkillCalls`는 없다(별도 필드 이름만 존재). | 코드 확인 |
| R-02 | Claude Agent SDK: 한 세션이 끝나 `result` 메시지가 정해졌을 때 | 그 세션에서 모은 도구 호출(`toolCalls`) 중 `name === 'Skill'`인 것만 항목이 된다. `name = input.skill`을 `trim()`한 값이고 `input.skill`이 문자열이 아니거나 trim 후 빈 값이면 그 호출은 건너뛴다. 항목은 `{name, input: 도구 입력 전체, is_error: 그 호출의 is_error, source: 'tool'}`이며 `path`는 없다. 중복 제거를 하지 않으므로 같은 스킬을 두 번 부르면 두 항목이다. 서브에이전트가 부른 `Skill`도 도구 호출 표에 있으면 포함된다(부모 구분 없음). | 코드 확인 |
| R-03 | Claude: `is_error`의 값 | 도구 결과(`tool_result`)가 오면 `block.is_error ?? false`로 채우고, 결과가 오지 않은 호출(중단 등)은 초기값 `false`로 남는다. 즉 결과 없이 끊긴 `Skill` 호출도 성공 항목으로 보인다. | 코드 확인 |
| R-04 | Claude: 응답에 싣는 위치 | `skillCalls`(비어 있어도 빈 배열)는 `result` 처리 두 경로(성공 `subtype === 'success'`, 그 외 오류 `subtype`) 모두의 `metadata`에 들어간다. 오류 경로에서도 `error` 문자열과 함께 `skillCalls`가 남는다. | 코드 확인 |
| R-05 | OpenCode: 항목으로 바꾸는 부분(part) 조건 | `part.type === 'tool'`이고 `part.tool === 'skill'`이며 `part.state.input.name`이 trim 후 비어 있지 않은 문자열일 때만 항목이 된다. 항목은 `{name, input: state.input, source: 'tool'}`에 더해, `state.metadata.dir`이 비어 있지 않은 문자열이면 `path = <dir>/SKILL.md`(플랫폼 경로 결합), `state.status === 'error'`이면 `is_error: true`(아니면 필드 생략). | 코드 확인 |
| R-06 | OpenCode: 어느 부분을 훑는가 | 스킬 도구가 켜져 있으면(`permission`이 `skill` 또는 `*`인 규칙 중 `deny`가 아닌 것이 하나라도 있음) 호출 후 세션 메시지 이력을 다시 읽어, 이번 프롬프트의 시작(`parentID` 메시지)부터 끝(응답 `id` 메시지)까지의 모든 part를 훑는다. 앵커가 없거나(`parentID`/`id` 없음, 이력에서 못 찾음, 끝이 시작보다 앞), 이력 조회가 예외를 던지거나, 스킬 도구가 꺼져 있으면 최종 응답의 part만 훑는다. 이력 조회 실패는 로그만 남기고 삼킨다. | 코드 확인 |
| R-07 | OpenCode: 응답에 싣는 위치 | 항목이 하나라도 있을 때만 `metadata: { skillCalls }`를 넣고, 없으면 `metadata` 자체를 넣지 않는다. | 코드 확인 |
| R-08 | Codex SDK·app-server: 명령 항목 선택 | 항목 후보는 명령 실행 항목(SDK `type === 'command_execution'` + 문자열 `command`, app-server `type === 'commandExecution'` + 문자열 `command`)의 `command` 문자열뿐이다. "성공한 명령" = `status`가 문자열이면 `'completed'`여야 하고, 종료 코드(SDK `exit_code`, app-server `exitCode`)가 숫자이면 0이어야 한다(둘 다 없으면 성공으로 본다). | 코드 확인 |
| R-09 | Codex: 명령 문자열에서 스킬 경로 찾기 | 명령 문자열을 공백으로 쪼개고 각 토큰의 앞쪽 `` ` " ' ( [ { < `` 와 뒤쪽 `` ` " ' , ; : ) ] } > ``를 벗기고 `\`를 `/`로 바꾼다. 토큰이 (a) 정확히 `.agents/skills/<이름>/SKILL.md` 이거나(상대 경로, 이 정규식은 `./`로 시작하면 맞지 않는다), (b) `<루트 접두어>/skills/<이름>/SKILL.md`(접두어 뒤가 정확히 이 모양)일 때만 후보다. `<이름>`은 `/`·공백이 없고 `[A-Za-z0-9._:-]+`여야 한다. 루트 접두어는 `CODEX_HOME`, `/etc/codex`, `<working_dir 절대경로>/.agents`, `<working_dir의 상위 중 `.git`이 있는 첫 디렉터리>/.agents`, `<HOME 또는 USERPROFILE>/.codex`다(끝 `/` 제거, 값이 없으면 생략). `*` 같은 와일드카드가 든 토큰은 이름 문자 규칙에서 탈락한다. | 코드 확인 |
| R-10 | Codex: 항목 생성·중복·분류 | 후보는 `path`를 키로 중복 제거하고 항목은 `{name, path, source: 'heuristic'}`이다(`input`, `is_error` 없음). `attemptedSkillCalls`는 모든 명령에서, `skillCalls`는 R-08의 성공한 명령에서만 만든다. 둘 다 비면 스킬 메타데이터가 없다. | 코드 확인 |
| R-11 | Codex: 응답에 싣는 위치 | `skillCalls`는 비어 있지 않을 때만, `attemptedSkillCalls`는 `attempted.length > skillCalls.length`일 때만 `metadata`에 들어간다. 같은 경로를 실패 후 재시도해 성공하면 두 목록이 같은 길이가 되어 `attemptedSkillCalls`는 생략된다. SDK provider는 둘 다 없으면 `metadata`가 `undefined`이고, app-server provider는 `codexAppServer` 등 다른 메타데이터 옆에 이 필드를 합친다. | 코드 확인 |
| R-12 | Codex Security 성공 응답 | `metadata.skillCalls`는 `[{name: operation}]`(`operation` = `security-scan` \| `deep-security-scan` \| `security-diff-scan`, 설정 `operation`의 기본은 `security-scan`) 또는 검증 작업에서는 `[{name: 'validation'}]`이다. `source`·`input`·`path`·`is_error`는 없다. 오류 응답에는 붙지 않는다. 이름이 실제 `SKILL.md`가 아니라 작업 이름이다. | 코드 확인 |
| R-13 | 비에이전트 provider | `skillCalls`를 만드는 코드는 위 provider(Claude Agent SDK, OpenCode SDK, Codex SDK·app-server, Codex Security)뿐이다. 그 외 provider 응답에는 이 필드가 없으므로 `skill-used`는 항상 "(none)"으로 판정된다(비반전은 실패, 반전은 통과). | 코드 확인 (`src/`의 비테스트 소스에서 `skillCalls` 검색) |

소비자 규칙 (`skill-used`)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | 입력 선별 | `metadata.skillCalls`가 배열이 아니면 빈 목록. 배열이면 원소가 truthy 객체이고 `name`이 문자열이며 `is_error !== true`인 것만 남긴다. 이 단계는 예외를 던지지 않는다(없거나 비면 아래 규칙대로 실패·통과). | 코드 확인 |
| R-15 | `value` 해석 | 값은 `renderedValue ?? assertion.value`다. (a) trim 후 비지 않은 문자열 → 이름 1개 목록. (b) 비지 않은 배열이고 모든 원소가 trim 후 비지 않은 문자열 → 목록(각 원소 trim). (c) 배열이 아닌 객체 → 개수 조건 객체: `name`·`pattern`은 문자열이면 trim(빈 값은 없는 것), 둘 다 없으면 `skill-used assertion object must include a name or pattern property` 오류, `min`/`max`가 키로 있으면 유한한 0 이상 정수여야 하고(아니면 `skill-used assertion object <min|max> must be a finite non-negative integer`), 둘 다 숫자이고 `max < min`이면 `skill-used assertion object max must be greater than or equal to min` 오류. (d) 그 밖(빈 문자열, 빈 배열, 숫자, null, 일부만 문자열인 배열 등) → `skill-used assertion must have a string, string array, or object value` 오류. 오류는 핸들러가 던지고 `runAssertion`을 거쳐 호출자에게 전파된다. | 코드 확인 |
| R-16 | 이름·패턴 일치 | 한 항목이 matcher와 맞으려면 matcher에 `name`이 있을 때 `entry.name === name`(대소문자 구분, 정확 일치)이고, `pattern`이 있을 때 `entry.name`이 glob에 맞아야 한다(둘 다 있으면 모두 만족). glob은 `*`=임의 길이, `?`=한 글자, 그 밖의 정규식 특수문자는 리터럴, 전체 일치, 대소문자 무시. 목록 형태(a, b)는 `name`만 쓰므로 `token-*` 문자열도 리터럴 이름이다. | 코드 확인 |
| R-17 | 목록 형태 판정 | 비반전: 목록의 모든 이름이 어떤 항목과 일치해야 통과(하나라도 없으면 `Missing required skill(s): ...`로 실패). 반전(`not-skill-used`): 어느 이름도 어떤 항목과 일치하지 않아야 통과(하나라도 쓰였으면 `Forbidden skill(s) were used: ...`로 실패). 항목 개수는 보지 않고, 같은 스킬을 여러 번 불렀는지는 구분하지 않는다. | 코드 확인 |
| R-18 | 개수 형태 판정, 비반전 | 일치 항목 수 `count`를 센다(같은 스킬이 N번 기록되면 N). `min` 기본값은 `max`가 지정되면 0, 아니면 1이다. `count >= min` 이고 `max`가 없거나 `count <= max`이면 통과. 예: `{name: 'a'}`는 "1회 이상", `{name: 'a', max: 0}`은 "0회". | 코드 확인 |
| R-19 | 개수 형태 판정, 반전 | `min`이 키로 있거나(값 0이어도), `max`가 있고 0이 아니면 `not-skill-used object assertions only support name/pattern with no count bounds, or max: 0` 오류. 그렇지 않으면 `count === 0`일 때 통과. | 코드 확인 |
| R-20 | 결과 객체 | 모든 경로가 `{pass, score: pass ? 1 : 0, reason, assertion: params.assertion}`을 돌려준다. `reason`의 "Actual skills"는 R-14로 걸러진 항목을 `이름 (source, path)` 형식(둘 다 없으면 이름만)으로 쉼표로 이은 것이고 비면 `(none)`. 걸러진(`is_error: true`) 항목은 여기에도 나오지 않는다. | 코드 확인 |
| R-21 | `not-skill-used`와 `value` 렌더링 | `not-skill-used`는 별도 핸들러가 아니라 `skill-used` 핸들러에 `inverse: true`가 전달되는 것이다(타입이 `not-` 접두어면 반전). `value`가 문자열이면 Nunjucks 렌더링(`{{ var }}`)을, 배열이면 각 문자열 원소에 같은 렌더링을 거친 뒤 핸들러에 `renderedValue`로 전달된다. 객체 값은 렌더링되지 않는다. | 코드 확인 |

- 불변식: 소비자는 `name`(문자열)과 `is_error`만으로 판정하고, `input`·`path`·`source`는 `reason` 표기에만 쓴다. 따라서 생산자가 같은 의미의 `name`/`is_error`를 채우면 어서션 결과가 같다. Claude·OpenCode 생산자에서는 같은 스킬 N회 호출이 N개 항목이 되어 개수 조건(`min`/`max`)이 의미를 가지고, Codex는 같은 경로를 한 번만 센다(R-10).
- 미결정: 없음.
- 확인 한계: 모든 항목은 소스 읽기로만 확인했다(설치·빌드·네트워크·모델 호출을 하지 않음). 다음은 이 레포 밖 동작이라 코드로 닫을 수 없다. ① Claude Agent SDK가 실제로 `name: 'Skill'`, `input.skill` 형태의 도구 호출을 내보내는지, 스킬을 어디서 찾아 로딩하는지(생산자 코드는 그 형태를 가정한다). ② OpenCode의 `skill` 도구 part가 `state.input.name`, `state.metadata.dir`, `state.status`를 그 모양으로 주는지. ③ Codex SDK의 비스트리밍 `thread.run` 결과 `items`에 `command_execution` 항목이 들어 있는지(문서는 증거 수집용으로 `enable_streaming: true`를 권하지만 코드는 두 경로 모두 `turn.items`를 같은 방식으로 읽는다. 이 차이는 2.1에 적음).

### 1.5 필수 코드 참조 [필수]
라이선스는 MIT(overview 1절)라 인용·복사에 제약이 없다. 단 복사하면 저작권 고지를 유지한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/types/providers.ts:49-55` `SkillCallEntry` | 항목 필드와 선택 여부 | R-01 |
| C-02 | `src/providers/claude-agent-sdk.ts:311-335` `deriveSkillCalls` | `Skill` 도구 호출 → 항목 변환, trim·건너뛰기 | R-02, R-03 |
| C-03 | `src/providers/opencode-sdk.ts:1939-1964` `deriveSkillCalls` | OpenCode `skill` part → 항목 변환(`path`, `is_error` 조건) | R-05 |
| C-04 | `src/providers/opencode-sdk.ts:1812-1822` `isSkillToolEnabled`, `:1835-1886` `fetchCurrentPromptParts` | 이력 조회 게이트와 시작·끝 앵커 슬라이스, 폴백 | R-06 |
| C-05 | `src/providers/openai/codexSkillMetadata.ts:27-61` `getCodexSkillRootPrefixes` | 루트 접두어 5종과 정규화 | R-09 |
| C-06 | `src/providers/openai/codexSkillMetadata.ts:63-99` `extractCodexSkillPathCandidates` | 토큰 정리, 상대 경로 정규식, 접두어 경로 규칙 | R-09 |
| C-07 | `src/providers/openai/codexSkillMetadata.ts:101-174` `buildCodexSkillMetadata`, `getCodexSkillMetadataFields`, `extractCodexSkillCallsFromItems`, `isValidCodexSkillName` | 성공/시도 분리, 경로 기준 중복 제거, 필드 생략 조건, 이름 문자 규칙 | R-10, R-11 |
| C-08 | `src/providers/openai/codex-sdk.ts:949-975` `buildSkillMetadata`·`isSuccessfulCommandExecution`; `src/providers/openai/codex-app-server.ts:3798-3819` 같은 이름의 두 메서드 | 명령 항목 선택과 "성공" 판정(어댑터) | R-08 |
| C-09 | `src/providers/openai/codexProcess.ts:51-65` `findGitRepositoryRoot` | git 루트 접두어를 정하는 상위 탐색 | R-09 |
| C-10 | `src/providers/openai/codex-security.ts:606`, `:665` | 고정 `skillCalls` 두 곳(스캔 작업 이름, `validation`) | R-12 |
| C-11 | `src/assertions/skill.ts:12-42` `getSkillCalls`, `matchesSkill`, `formatSkillCall` | 입력 선별, 일치 규칙, 표시 형식 | R-14, R-16, R-20 |
| C-12 | `src/assertions/skill.ts:44-108` `resolveSkillMatchers` | `value` 3형태 해석과 검증 오류 메시지 | R-15 |
| C-13 | `src/assertions/skill.ts:110-205` `handleListSkillAssertion`, `handleCountSkillAssertion`, `handleSkillUsed` | 목록·개수 판정, 반전 제약, 결과·사유 문자열 | R-17~R-20 |
| C-14 | `src/assertions/traceUtils.ts:62-71` `matchesPattern` | glob→정규식 변환(대소문자 무시) | R-16 |
| C-15 | `src/assertions/index.ts:354-372` `isAssertionInverse`, `getAssertionBaseType`; `:483-560` 값 렌더링 | `not-` 접두어 반전, 문자열·배열 값 렌더링 | R-21 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트 `test/assertions/skill.test.ts`는 사례명만 열람하고 실행하지 않았다). 외부 SDK는 대체물(입력 데이터)로 바꾼 사례라 SDK가 실제로 그 데이터를 만드는지는 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | Claude 도구 호출 `[{name:'Skill', input:{skill:' review '}, is_error:false}, {name:'Read', input:{}}]` | `skillCalls = [{name:'review', input:{skill:' review '}, is_error:false, source:'tool'}]` |
| T-02 | R-02 | Claude `Skill` 호출 중 `input.skill`이 없음 / `'  '` / 숫자 | 해당 호출은 항목 없음 |
| T-03 | R-03 | Claude `Skill` 호출이 `tool_result` 없이 끊김 | 항목의 `is_error: false` |
| T-04 | R-05 | OpenCode part `{type:'tool', tool:'skill', state:{status:'error', input:{name:'x'}}}` | `{name:'x', input:{name:'x'}, source:'tool', is_error:true}`, `path` 없음 |
| T-05 | R-05, R-07 | OpenCode part `{type:'tool', tool:'skill', state:{status:'completed', input:{name:'x'}, metadata:{dir:'/s/x'}}}`, 다른 part 없음 | `metadata.skillCalls = [{name:'x', input:{name:'x'}, path:'/s/x/SKILL.md', source:'tool'}]`(`is_error` 키 없음). 스킬 part가 하나도 없으면 `metadata` 키 자체가 없다. |
| T-06 | R-08~R-11 | Codex items `[{command_execution, 'cat .agents/skills/a/SKILL.md', completed, exit 0}, {command_execution, 'cat .agents/skills/b/SKILL.md', completed, exit 1}]` | `skillCalls=[{name:'a', path:'.agents/skills/a/SKILL.md', source:'heuristic'}]`, `attemptedSkillCalls`는 a·b 두 항목 |
| T-07 | R-10, R-11 | Codex: 같은 `a` 경로를 먼저 exit 1, 다음에 exit 0으로 읽음 | `skillCalls=[a]`, 시도 목록도 1개라 `attemptedSkillCalls` 생략 |
| T-08 | R-09 | Codex 명령 `cat ./.agents/skills/a/SKILL.md`, `cat .agents/skills/a/SKILL.md\|head`(파이프가 토큰에 붙음), `cat .agents/skills/*/SKILL.md` | 세 경우 모두 후보 없음(앞의 둘은 정규식이 `.agents`로 시작하고 `SKILL.md`로 끝나야 하므로 탈락. 이 입력으로 직접 실행하지는 않았고 정규식에서 도출) |
| T-09 | R-09 | Codex `working_dir=/w`, 명령 `cat /w/.agents/skills/a/SKILL.md` | 후보 `{name:'a', path:'/w/.agents/skills/a/SKILL.md'}` |
| T-10 | R-12 | Codex Security 스캔 성공, `operation` 미지정 | `metadata.skillCalls = [{name:'security-scan'}]` |
| T-11 | R-14, R-17 | `skillCalls=[{name:'a', is_error:true}]`, `skill-used` 값 `'a'` | 실패, 사유에 `Missing required skill(s): a`와 `Actual skills: (none)` |
| T-12 | R-14 | `metadata.skillCalls`가 배열이 아닌 객체이거나 `metadata`가 없음, 값 `'a'` | 예외 없이 실패(빈 목록과 같음) |
| T-13 | R-16 | 항목 `token-a`, 값 `'token-*'`(문자열) / `{pattern:'TOKEN-*'}` | 문자열은 리터럴 이름이라 실패, 패턴은 대소문자 무시로 통과 |
| T-14 | R-18 | 항목 `token-a`, `token-b`, 값 `{pattern:'token-*', min:2, max:2}` / `{name:'token-a', min:2}` | 앞은 통과(`expected 2-2`), 뒤는 실패(count 1) |
| T-15 | R-17, R-21 | 항목 `[a]`, `not-skill-used` 값 `'a'` / `['b']` | 앞은 실패(`Forbidden skill(s) were used: a`), 뒤는 통과 |
| T-16 | R-19 | `not-skill-used` 값 `{name:'a', min:0}` / `{name:'a', max:1}` / `{name:'a', max:0}` | 앞 둘은 `not-skill-used object assertions only support ...` 오류, 마지막은 count가 0이면 통과 |
| T-17 | R-15 | `skill-used` 값 `''`, `[]`, `['a', 1]`, `{min:1}`, `{name:'a', min:-1}`, `{name:'a', min:2, max:1}` | 각각 R-15의 오류 메시지로 예외 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 타입 정의를 직접 읽음. |
| R-02, R-03 | C-02; 도구 호출 수집 `src/providers/claude-agent-sdk.ts:2076`(`toolCallsMap`), `:2189-2201`(`tool_use` 블록 등록, `is_error: false` 초기값, `parentToolUseId`), `:2215-2225`(`tool_result`에서 `is_error` 갱신) | 호출→수집→변환 흐름을 읽음. SDK가 실제로 그런 도구 이름·입력을 내는지는 미확인(외부). `parentToolUseId`가 서브에이전트를 뜻하는 것은 필드 이름과 코드 사용에서의 추론이고, `deriveSkillCalls`는 그 값을 보지 않는다는 것은 코드 확인. |
| R-04 | `src/providers/claude-agent-sdk.ts:2433-2434`(변환 호출), `:2474`(성공 경로 `metadata.skillCalls`), `:2518`(오류 경로) | 두 반환문을 읽음. 예외로 빠지는 경로의 응답 모양은 이 스펙이 다루지 않음(agent-providers). |
| R-05 | C-03; `src/providers/opencode-sdk.ts:523-531` `OpenCodePromptPart` 타입 | 코드 확인. `part.state.metadata.dir` 의미는 OpenCode 쪽 규약(미확인). 문서(`site/docs/providers/opencode-sdk.md:431-436`)도 같은 서술. |
| R-06 | C-04; 호출부 `src/providers/opencode-sdk.ts:2136-2159` | 게이트·앵커·폴백·예외 삼킴을 모두 코드에서 읽음. `buildEffectivePermissionRules`의 규칙 구성은 읽지 않음(agent-providers). |
| R-07 | `src/providers/opencode-sdk.ts:1927`, `:1935` `buildProviderResponse` | 코드 확인. |
| R-08 | C-08; 호출부 `codex-sdk.ts:2448-2463`, `codex-app-server.ts:3264-3282` | 두 provider의 어댑터를 읽음. 실행 항목 구조(`status`, `exit_code`/`exitCode`)는 SDK 쪽 규약(미확인), 코드는 그 필드를 가정. |
| R-09 | C-05, C-06, C-09; 접두어 조립 호출 `codex-sdk.ts:934-947`, `codex-app-server.ts:3780-3796` | 정규식·분기를 직접 읽음. 사례 T-08·T-09는 코드에서 도출(실행하지 않음). 문서 대비 차이는 아래. |
| R-10, R-11 | C-07; `codex-sdk.ts:2454-2464`, `codex-app-server.ts:3263-3283` | 코드 확인. |
| R-12 | C-10; 작업 이름 설정 `src/providers/openai/codex-security.ts:54`, `:351`, `:437-457`, 스캔 응답 구성 `:564-610`, 검증 응답 `:650-668` | 코드 확인. |
| R-13 | `src/` 비테스트 소스에서 `skillCalls`·`attemptedSkillCalls`·`SkillCallEntry` 검색 결과가 위 provider와 `src/assertions/skill.ts`뿐 | grep으로 전수 확인(주석·동적 문자열 키 접근은 제외될 수 있음). 플러그인·extension 같은 사용자 코드가 필드를 채우는 경우는 범위 밖. |
| R-14, R-16, R-20 | C-11, C-14 | 코드 확인. |
| R-15 | C-12 | 코드 확인. 오류 문자열은 소스 그대로. |
| R-17~R-19 | C-13 | 코드 확인. |
| R-21 | C-15; 등록 `src/assertions/index.ts:305`, 타입 목록 `src/types/index.ts:732`와 `:748-760`(`not-` 파생) | 코드 확인. `renderedValue` 생성에서 `file://` 문자열 값은 별도 분기(파일을 읽음)이지만 그 규칙은 assertion-family 소관. |
| T-01~T-17 | 구현에서 도출. 열람한 테스트 사례명: `test/assertions/skill.test.ts`의 "passes when an exact skill name is present", "ignores errored skill calls ...", "supports pattern matching with count thresholds", "trims object matcher name and pattern values", "treats not-skill-used object assertions with no count bounds as forbidding any match", "rejects ambiguous not-skill-used count bounds other than max: 0", "rejects invalid count bounds", "throws when object values omit name and pattern", "fails gracefully when skillCalls is an empty array" 등 | 사례 본문은 읽지 않았고 기대값은 구현 코드에서 직접 도출. 테스트 파일이 있다는 것은 실행 확인이 아니다. |

문서와 구현의 차이·주의

- `site/docs/providers/openai-codex-sdk.md:750`은 `~/.codex/skills/<name>/` 경로를 인식한다고 쓴다. 구현(C-05, C-06)은 `HOME`/`USERPROFILE`을 펼친 절대 경로 접두어 `<HOME>/.codex/skills/`만 비교하므로, 명령에 글자 그대로 `~/.codex/skills/a/SKILL.md`가 적혀 있으면(셸 확장은 실행 시점이라 문자열에는 `~`가 남는다) 후보가 되지 않는다. 구현을 사실로 썼다(코드 확인, 문서 서술의 의도는 추론).
- 같은 문서와 `site/docs/guides/test-agent-skills.md`는 Codex에서 `enable_streaming: true`를 켜면 스킬 증거를 모을 수 있다고 안내한다. 코드는 스트리밍·비스트리밍 모두 같은 `turn.items`를 읽어 `buildCodexSkillMetadata`에 넣는다(`codex-sdk.ts:2419-2421`, `:2448`). 비스트리밍 `thread.run`이 `command_execution` 항목을 돌려주는지는 SDK 쪽이라 미확인이다(1.4 확인 한계 ③).
- `site/docs/configuration/expected-outputs/deterministic.md:742-745`는 Claude·Codex SDK·OpenCode SDK 세 가지를 생산자로 든다. 코드에는 Codex app-server와 Codex Security도 생산자다(R-08, R-12). 문서에 없는 생산자이고, Codex Security의 `name`은 실제 스킬이 아니라 작업 이름이라 의미가 다르다.
- 문서는 Codex의 `source`가 항상 `heuristic`이라고 하고, 구현도 그렇다(C-07). 다만 Codex Security 항목은 `source`가 없어 `SkillCallEntry` 타입상 선택 필드이기 때문에 허용되는 값이다.
- `site/docs/providers/claude-agent-sdk.md:535`는 Codex와 "같은 스타일"이라 하지만, 필드 채움이 서로 다르다. Claude는 `input`·`is_error`가 있고 `path`가 없으며, Codex는 `path`·`source`만 있고 `input`·`is_error`가 없다(R-02, R-10).

### 2.2 코드 읽는 순서 [선택]
1. `src/types/providers.ts:49` 타입 → `src/assertions/skill.ts` 전체(약 200줄, 이 스펙의 소비자 규칙 전부).
2. 생산자: `claude-agent-sdk.ts:311`(가장 단순) → `opencode-sdk.ts:1939`와 `:1835-1886`(이력 슬라이스) → `codexSkillMetadata.ts`(Codex 추정 전체가 이 파일 하나) → 두 Codex provider의 어댑터(`codex-sdk.ts:949`, `codex-app-server.ts:3798`).
3. 응답에 싣는 위치는 provider마다 한 곳이다: Claude `:2474`·`:2518`, OpenCode `:1935`, Codex SDK `:2448`, app-server `:3282`.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-13 | (원본 동작 설명) 모델 적합도를 비교할 때 `skill-used`는 에이전트 런타임이 있는 provider에서만 의미가 있다. 일반 채팅 모델(`messages`·`chat` 계열)에는 `skillCalls`가 생기지 않으므로 "SKILL.md를 프롬프트로 넣은 모델"의 사용 여부는 이 계약으로 잴 수 없다. | 사용자 목적(여러 모델에 스킬 평가·적합도 기록) 관점에서 가장 중요한 제약이다. | 변경 없음. 필요하면 출력 품질 어서션으로 별도 판정. |
| R-02, R-10, R-12 | 기록할 때 `source`(`tool`/`heuristic`)와 생산자 종류를 함께 남기면 "확실한 호출"과 "추정"을 구분할 수 있다. Codex 항목은 추정치이고 Codex Security의 항목은 스킬이 아니다. | `skill-used`가 이들을 같은 이름 공간에서 섞어 센다(R-14). | 원본은 구분 없이 소비한다. |
| R-03 | 결과 없이 끊긴 Claude `Skill` 호출도 `is_error:false`로 남는다. 엄격히 성공만 세고 싶으면 호출 쪽 `output` 유무도 봐야 한다(원본은 `toolCalls`에 `output`을 같이 남긴다). | 원본은 `output`을 `skill-used`에서 쓰지 않는다. | 신규 규칙이 되므로 필요할 때만. |
