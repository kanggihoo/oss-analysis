# Codex SDK TypeScript 주요 메서드와 인자 정리

작성일: 2026-05-19

분석 대상: `codex/sdk/typescript/`

이 문서는 `analysis-reports/codex-sdk-typescript/overview.md`의 분석 내용을 바탕으로, 실제 TypeScript SDK 코드를 직접 확인해 구현 시 자주 쓰는 주요 메서드와 인자를 정리한 것이다. 핵심 근거 파일은 `src/codex.ts`, `src/thread.ts`, `src/codexOptions.ts`, `src/threadOptions.ts`, `src/turnOptions.ts`, `src/exec.ts`, `src/events.ts`, `src/items.ts`이다.

## 1. 기본 사용 흐름

```ts
import { Codex } from "@openai/codex-sdk";

const codex = new Codex({
  apiKey: process.env.CODEX_API_KEY,
  baseUrl: "https://example.test",
});

const thread = codex.startThread({
  model: "gpt-5.2",
  sandboxMode: "workspace-write",
  workingDirectory: "/path/to/project",
  skipGitRepoCheck: true,
});

const turn = await thread.run("Diagnose the test failure and propose a fix");

console.log(turn.finalResponse);
console.log(turn.items);
console.log(turn.usage);
```

SDK의 public entry point는 `src/index.ts`에서 export된다. 주요 공개 API는 `Codex`, `Thread`, `CodexOptions`, `ThreadOptions`, `TurnOptions`, `ThreadEvent`, `ThreadItem`이다.

## 2. 주요 클래스와 메서드

### 2.1 `new Codex(options?: CodexOptions)`

근거: `src/codex.ts`, `src/codexOptions.ts`

`Codex`는 SDK의 메인 클라이언트 클래스이다. 생성자에서 `CodexExec`를 만들고, 이후 thread 생성 시 client-level 옵션을 전달한다.

```ts
const codex = new Codex({
  codexPathOverride: "/path/to/codex",
  baseUrl: "https://example.test",
  apiKey: "test-key",
  config: {
    approval_policy: "never",
    sandbox_workspace_write: {
      network_access: true,
    },
  },
  env: {
    PATH: "/usr/local/bin",
  },
});
```

| 인자 | 타입 | 설명 |
|---|---|---|
| `options` | `CodexOptions` | Codex CLI 실행 경로, API 설정, 환경변수, 전역 config override를 담는 객체 |

반환값은 `Codex` 인스턴스이다.

### 2.2 `codex.startThread(options?: ThreadOptions): Thread`

근거: `src/codex.ts`, `src/thread.ts`, `src/threadOptions.ts`

새 Codex 대화 thread를 시작한다. 반환된 `Thread` 인스턴스에 대해 `run()` 또는 `runStreamed()`를 반복 호출하면 같은 thread 안에서 대화를 이어간다.

```ts
const thread = codex.startThread({
  model: "gpt-5.2",
  sandboxMode: "workspace-write",
  workingDirectory: "/path/to/project",
});
```

| 인자 | 타입 | 설명 |
|---|---|---|
| `options` | `ThreadOptions` | thread 단위로 적용되는 모델, sandbox, 작업 디렉터리, 승인 정책, 검색 설정 등 |

반환값은 `Thread` 인스턴스이다.

### 2.3 `codex.resumeThread(id: string, options?: ThreadOptions): Thread`

근거: `src/codex.ts`, `src/exec.ts`

기존 thread id를 이용해 저장된 대화를 재개한다. `src/exec.ts`에서는 `threadId`가 있으면 CLI 인자에 `resume <threadId>`를 추가한다.

```ts
const thread = codex.resumeThread(savedThreadId, {
  model: "gpt-5.2",
});

await thread.run("Continue the previous task");
```

| 인자 | 타입 | 설명 |
|---|---|---|
| `id` | `string` | 재개할 thread id |
| `options` | `ThreadOptions` | 재개한 thread에 적용할 thread-level 옵션 |

반환값은 `Thread` 인스턴스이다.

### 2.4 `thread.id: string | null`

근거: `src/thread.ts`

`Thread`의 id를 반환하는 getter이다. 새 thread는 처음 생성 직후에는 `null`일 수 있고, `thread.started` 이벤트를 받은 뒤 `parsed.thread_id`로 채워진다.

```ts
const thread = codex.startThread();
console.log(thread.id); // null 가능

await thread.run("Hello");
console.log(thread.id); // string 가능
```

### 2.5 `thread.run(input: Input, turnOptions?: TurnOptions): Promise<Turn>`

근거: `src/thread.ts`, `src/turnOptions.ts`

agent에게 입력을 보내고 turn이 끝날 때까지 이벤트를 내부에서 소비한 뒤 최종 결과를 반환한다. 일반적인 구현에서는 `run()`이 가장 단순하다.

```ts
const turn = await thread.run("Summarize repository status");

console.log(turn.finalResponse);
console.log(turn.items);
console.log(turn.usage);
```

구조화 출력이 필요하면 `TurnOptions.outputSchema`를 함께 전달한다.

```ts
const schema = {
  type: "object",
  properties: {
    summary: { type: "string" },
    status: { type: "string", enum: ["ok", "action_required"] },
  },
  required: ["summary", "status"],
  additionalProperties: false,
} as const;

const turn = await thread.run("Summarize repository status", {
  outputSchema: schema,
});
```

| 인자 | 타입 | 설명 |
|---|---|---|
| `input` | `Input` | 문자열 prompt 또는 text/image 항목 배열 |
| `turnOptions` | `TurnOptions` | turn 단위 output schema와 abort signal |

반환 타입:

```ts
type Turn = {
  items: ThreadItem[];
  finalResponse: string;
  usage: Usage | null;
};
```

`run()` 내부 동작:

- `runStreamedInternal()`을 호출해 JSONL 이벤트를 받는다.
- `item.completed` 이벤트가 오면 `items`에 `event.item`을 추가한다.
- 완료된 item이 `agent_message`이면 `finalResponse`를 해당 `text`로 갱신한다.
- `turn.completed` 이벤트가 오면 `usage`를 저장한다.
- `turn.failed` 이벤트가 오면 `event.error.message`로 `Error`를 throw한다.

### 2.6 `thread.runStreamed(input: Input, turnOptions?: TurnOptions): Promise<StreamedTurn>`

근거: `src/thread.ts`, `src/events.ts`, `src/items.ts`

이벤트를 실시간으로 처리해야 할 때 사용한다. 반환값의 `events`는 `AsyncGenerator<ThreadEvent>`이다.

```ts
const { events } = await thread.runStreamed("Diagnose the failure");

for await (const event of events) {
  switch (event.type) {
    case "item.completed":
      console.log(event.item);
      break;
    case "turn.completed":
      console.log(event.usage);
      break;
    case "turn.failed":
      console.error(event.error.message);
      break;
  }
}
```

| 인자 | 타입 | 설명 |
|---|---|---|
| `input` | `Input` | 문자열 prompt 또는 text/image 항목 배열 |
| `turnOptions` | `TurnOptions` | output schema와 abort signal |

반환 타입:

```ts
type StreamedTurn = {
  events: AsyncGenerator<ThreadEvent>;
};
```

## 3. `CodexOptions`

근거: `src/codexOptions.ts`, `src/exec.ts`

```ts
type CodexOptions = {
  codexPathOverride?: string;
  baseUrl?: string;
  apiKey?: string;
  config?: CodexConfigObject;
  env?: Record<string, string>;
};
```

| 필드 | 타입 | 실제 동작 |
|---|---|---|
| `codexPathOverride` | `string` | 기본 CLI 탐색 대신 지정한 `codex` 실행 파일 경로를 사용한다. 내부적으로 `new CodexExec(codexPathOverride, ...)`에 전달된다. |
| `baseUrl` | `string` | CLI 인자 `--config openai_base_url=<value>`로 변환된다. |
| `apiKey` | `string` | child process 환경변수 `CODEX_API_KEY`로 주입된다. |
| `config` | `CodexConfigObject` | JSON 객체를 dotted path로 펼치고 TOML literal로 직렬화해 `--config key=value` 인자로 반복 전달한다. |
| `env` | `Record<string, string>` | CLI child process에 전달할 환경변수를 직접 지정한다. 제공하면 `process.env`를 상속하지 않는다. 단, SDK가 필요한 env는 추가로 주입된다. |

`config` 값은 `string`, `number`, `boolean`, 배열, 중첩 객체를 지원한다. `null`, non-finite number, 비어 있는 key 등은 오류가 된다.

예시:

```ts
const codex = new Codex({
  config: {
    approval_policy: "never",
    sandbox_workspace_write: {
      network_access: true,
    },
    retry_budget: 3,
    tool_rules: {
      allow: ["git status", "git diff"],
    },
  },
});
```

위 설정은 대략 다음 CLI 인자로 변환된다.

```txt
--config approval_policy="never"
--config sandbox_workspace_write.network_access=true
--config retry_budget=3
--config tool_rules.allow=["git status", "git diff"]
```

## 4. `ThreadOptions`

근거: `src/threadOptions.ts`, `src/thread.ts`, `src/exec.ts`

```ts
type ThreadOptions = {
  model?: string;
  sandboxMode?: SandboxMode;
  workingDirectory?: string;
  skipGitRepoCheck?: boolean;
  modelReasoningEffort?: ModelReasoningEffort;
  networkAccessEnabled?: boolean;
  webSearchMode?: WebSearchMode;
  webSearchEnabled?: boolean;
  approvalPolicy?: ApprovalMode;
  additionalDirectories?: string[];
};
```

| 필드 | 타입/값 | CLI 변환 | 설명 |
|---|---|---|---|
| `model` | `string` | `--model <model>` | 사용할 모델 지정 |
| `sandboxMode` | `"read-only"`, `"workspace-write"`, `"danger-full-access"` | `--sandbox <mode>` | Codex 실행 sandbox 모드 지정 |
| `workingDirectory` | `string` | `--cd <dir>` | Codex가 실행될 작업 디렉터리 |
| `skipGitRepoCheck` | `boolean` | `--skip-git-repo-check` | 작업 디렉터리의 Git repo 검사 생략 |
| `modelReasoningEffort` | `"minimal"`, `"low"`, `"medium"`, `"high"`, `"xhigh"` | `--config model_reasoning_effort="<value>"` | 모델 reasoning effort 설정 |
| `networkAccessEnabled` | `boolean` | `--config sandbox_workspace_write.network_access=true/false` | workspace-write sandbox에서 네트워크 허용 여부 |
| `webSearchMode` | `"disabled"`, `"cached"`, `"live"` | `--config web_search="<value>"` | web search 모드 지정 |
| `webSearchEnabled` | `boolean` | true면 `web_search="live"`, false면 `web_search="disabled"` | legacy boolean 검색 옵션 |
| `approvalPolicy` | `"never"`, `"on-request"`, `"on-failure"`, `"untrusted"` | `--config approval_policy="<value>"` | 승인 정책 |
| `additionalDirectories` | `string[]` | 각 항목마다 `--add-dir <dir>` | 작업 디렉터리 외 추가 접근 디렉터리 |

`CodexOptions.config`와 `ThreadOptions`가 같은 설정을 건드리면, `src/exec.ts`에서 전역 config가 먼저 emit되고 thread option이 나중에 emit된다. 따라서 중복 key에 대해서는 thread option이 더 나중에 전달된다.

## 5. `TurnOptions`

근거: `src/turnOptions.ts`, `src/outputSchemaFile.ts`, `src/thread.ts`

```ts
type TurnOptions = {
  outputSchema?: unknown;
  signal?: AbortSignal;
};
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `outputSchema` | `unknown` | 구조화 출력용 JSON schema. plain JSON object여야 한다. 임시 `schema.json` 파일로 저장된 뒤 `--output-schema <path>`로 CLI에 전달된다. |
| `signal` | `AbortSignal` | turn 실행 취소용 signal. 내부적으로 `spawn()` 옵션에 전달된다. |

`outputSchema`가 `undefined`이면 아무 파일도 만들지 않는다. 객체가 아니거나 배열이면 `outputSchema must be a plain JSON object` 오류를 던진다.

Abort 예시:

```ts
const controller = new AbortController();

const promise = thread.run("Long running task", {
  signal: controller.signal,
});

controller.abort("Stop");

await promise;
```

## 6. 입력 타입 `Input`

근거: `src/thread.ts`

```ts
type UserInput =
  | {
      type: "text";
      text: string;
    }
  | {
      type: "local_image";
      path: string;
    };

type Input = string | UserInput[];
```

문자열 입력은 그대로 prompt가 된다.

```ts
await thread.run("Fix the failing test");
```

배열 입력은 `normalizeInput()`에서 다음처럼 처리된다.

- `type: "text"` 항목은 `text` 값을 모아 `\n\n`로 합친다.
- `type: "local_image"` 항목은 image path 배열로 분리한다.
- image path는 `src/exec.ts`에서 각 항목마다 `--image <path>`로 CLI에 전달된다.

```ts
await thread.run([
  { type: "text", text: "Describe these screenshots" },
  { type: "local_image", path: "./ui.png" },
  { type: "local_image", path: "./diagram.jpg" },
]);
```

## 7. 반환 타입과 이벤트 타입

### 7.1 `Turn`

근거: `src/thread.ts`

```ts
type Turn = {
  items: ThreadItem[];
  finalResponse: string;
  usage: Usage | null;
};
```

| 필드 | 설명 |
|---|---|
| `items` | turn 중 완료된 item 목록 |
| `finalResponse` | 마지막 `agent_message` item의 `text` |
| `usage` | `turn.completed` 이벤트의 token usage. 완료 이벤트가 없으면 `null` 가능 |

### 7.2 `Usage`

근거: `src/events.ts`

```ts
type Usage = {
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  reasoning_output_tokens: number;
};
```

### 7.3 `ThreadEvent`

근거: `src/events.ts`

`runStreamed()`의 async generator가 내보내는 top-level event union이다.

| 이벤트 타입 | 주요 payload | 의미 |
|---|---|---|
| `thread.started` | `thread_id` | 새 thread가 시작됨. 이 값으로 `thread.id`가 갱신된다. |
| `turn.started` | 없음 | 새 turn 시작 |
| `item.started` | `item` | thread item 시작 |
| `item.updated` | `item` | thread item 중간 갱신 |
| `item.completed` | `item` | thread item 완료 |
| `turn.completed` | `usage` | turn 정상 완료 |
| `turn.failed` | `error` | turn 실패 |
| `error` | `message` | stream-level unrecoverable error |

### 7.4 `ThreadItem`

근거: `src/items.ts`

| item 타입 | 주요 필드 | 의미 |
|---|---|---|
| `agent_message` | `id`, `text` | agent의 최종 또는 중간 응답 메시지 |
| `reasoning` | `id`, `text` | reasoning summary |
| `command_execution` | `id`, `command`, `aggregated_output`, `exit_code?`, `status` | agent가 실행한 shell command |
| `file_change` | `id`, `changes`, `status` | patch 적용 결과 |
| `mcp_tool_call` | `id`, `server`, `tool`, `arguments`, `result?`, `error?`, `status` | MCP tool 호출 |
| `web_search` | `id`, `query` | web search 요청 |
| `todo_list` | `id`, `items` | agent todo list 상태 |
| `error` | `id`, `message` | non-fatal error item |

## 8. 내부 실행 흐름

근거: `src/thread.ts`, `src/exec.ts`, `src/outputSchemaFile.ts`

1. 사용자가 `new Codex(options)`로 SDK client를 만든다.
2. `Codex` 생성자는 내부적으로 `CodexExec`를 생성한다.
3. 사용자가 `startThread()` 또는 `resumeThread(id)`로 `Thread`를 만든다.
4. 사용자가 `thread.run()` 또는 `thread.runStreamed()`를 호출한다.
5. `Thread`는 `Input`을 prompt 문자열과 image path 목록으로 정규화한다.
6. `outputSchema`가 있으면 임시 `schema.json` 파일을 만든다.
7. `CodexExec.run()`이 `codex exec --experimental-json` CLI 프로세스를 spawn한다.
8. prompt는 child process stdin으로 전달된다.
9. stdout은 line 단위 JSONL로 읽힌다.
10. `Thread`가 각 line을 `JSON.parse()`해 `ThreadEvent`로 yield한다.
11. `thread.started` 이벤트가 오면 `Thread._id`를 갱신한다.
12. generator 종료 시 output schema 임시 디렉터리를 cleanup한다.

## 9. 구현 시 선택 기준

일반적인 최종 응답만 필요하면 `run()`을 사용한다.

```ts
const result = await thread.run("Implement the fix");
console.log(result.finalResponse);
```

진행 상황, command 실행, 파일 변경, todo list, token usage를 실시간으로 보여줘야 하면 `runStreamed()`를 사용한다.

```ts
const { events } = await thread.runStreamed("Implement the fix");

for await (const event of events) {
  if (event.type === "item.completed") {
    console.log(event.item);
  }
}
```

같은 대화를 이어가려면 같은 `Thread` 인스턴스에 `run()`을 반복 호출한다.

```ts
await thread.run("Find the issue");
await thread.run("Now implement the fix");
```

프로세스가 재시작되어 `Thread` 객체를 잃었으면 저장해 둔 `thread.id`로 `resumeThread()`를 호출한다.

```ts
const restored = codex.resumeThread(savedThreadId);
await restored.run("Continue");
```

이미지 입력이 필요하면 문자열 prompt 대신 `UserInput[]`를 사용한다.

```ts
await thread.run([
  { type: "text", text: "Review this UI screenshot" },
  { type: "local_image", path: "./screenshot.png" },
]);
```

구조화된 JSON 응답이 필요하면 turn 단위로 `outputSchema`를 전달한다.

```ts
const result = await thread.run("Return task status", {
  outputSchema: {
    type: "object",
    properties: {
      status: { type: "string" },
      summary: { type: "string" },
    },
    required: ["status", "summary"],
    additionalProperties: false,
  },
});
```

## 10. 관련 테스트에서 확인된 동작

근거: `tests/run.test.ts`, `tests/runStreamed.test.ts`, `tests/exec.test.ts`, `tests/abort.test.ts`

- `run()`은 `items`, `usage`, `thread.id`를 정상 반환한다.
- 같은 `Thread`에서 `run()` 또는 `runStreamed()`를 두 번 호출하면 이전 assistant item을 포함해 같은 thread를 이어간다.
- `resumeThread(id)`는 기존 thread id를 유지한다.
- `model`, `sandboxMode`, `modelReasoningEffort`, `networkAccessEnabled`, `webSearchMode`, `webSearchEnabled`, `approvalPolicy`, `additionalDirectories`, `workingDirectory`가 CLI 인자로 전달된다.
- `CodexOptions.config`는 TOML `--config` flag로 변환된다.
- 중복 config의 경우 thread option이 전역 config보다 나중에 전달된다.
- `outputSchema`는 임시 파일로 작성되고 turn 종료 후 삭제된다.
- text input segment는 `\n\n`로 결합된다.
- image input은 `--image` 인자로 전달된다.
- `AbortSignal`은 `run()`과 `runStreamed()` 모두에서 실행 취소에 사용된다.

