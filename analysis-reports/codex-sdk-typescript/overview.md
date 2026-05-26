# Codex SDK TypeScript 분석 보고서

분석 일자: 2026-05-19

분석 범위: `codex/sdk/typescript/` 내부만 확인했다. `codex-rs`, 다른 SDK, 상위 workspace 설정은 사용자가 제한한 범위 밖이므로 동작 근거로 확장 분석하지 않았다.

## 1. 이 프로젝트의 목적

`codex/sdk/typescript`는 Node.js/TypeScript 애플리케이션에서 Codex agent를 임베드하기 위한 SDK 패키지다. `README.md`는 이 SDK가 `@openai/codex`의 `codex` CLI를 감싸고, 하위 프로세스의 stdin/stdout을 통해 JSONL 이벤트를 주고받는다고 설명한다.

핵심 목적은 사용자가 직접 CLI 프로세스와 JSONL 스트림을 다루지 않아도 `Codex`, `Thread`, `run()`, `runStreamed()` 같은 TypeScript API로 Codex 대화를 시작, 이어가기, 재개, 스트리밍 처리할 수 있게 하는 것이다.

근거:

- `README.md`: SDK가 `@openai/codex` CLI를 spawn하고 JSONL 이벤트를 교환한다고 설명
- `src/codex.ts`: 공개 진입 클래스 `Codex`
- `src/thread.ts`: 대화 thread와 turn 실행 API
- `src/exec.ts`: 실제 `codex exec --experimental-json` 하위 프로세스 실행

## 2. 프로젝트 유형과 사용 방식

유형은 TypeScript 라이브러리 패키지다. `package.json`의 패키지명은 `@openai/codex-sdk`, ESM 패키지이며 Node.js 18 이상을 요구한다. 빌드 결과는 `dist/index.js`와 `dist/index.d.ts`로 배포된다.

사용자는 다음 흐름으로 SDK를 사용한다.

1. `new Codex(options)`로 SDK 클라이언트를 만든다.
2. `codex.startThread(options)`로 새 대화 thread를 시작하거나 `codex.resumeThread(id, options)`로 기존 thread를 재개한다.
3. `thread.run(input, turnOptions)`로 완료 결과를 받거나 `thread.runStreamed(input, turnOptions)`로 이벤트 스트림을 소비한다.

근거:

- `package.json`: `name`, `type: "module"`, `module`, `types`, `exports`, `engines.node >=18`
- `README.md`: Quickstart, streaming, structured output, image attachment, resume, working directory, environment/config 예시
- `src/index.ts`: 공개 export 표면

## 3. 핵심 기능

핵심 기능은 네 가지다.

- 대화 thread 관리: `Codex.startThread()`와 `Codex.resumeThread()`가 `Thread` 인스턴스를 만든다.
- 실행 모드 제공: `Thread.run()`은 이벤트를 내부에서 끝까지 모아 `finalResponse`, `items`, `usage`를 반환하고, `Thread.runStreamed()`는 `AsyncGenerator<ThreadEvent>`를 반환한다.
- CLI 옵션 매핑: `ThreadOptions`와 `CodexOptions`를 `codex exec` 인자와 `--config` 값으로 변환한다.
- 구조화 출력과 멀티모달 입력: turn 단위 `outputSchema`를 임시 JSON 파일로 넘기고, `local_image` 입력은 `--image` 인자로 넘긴다.

근거:

- `src/thread.ts`: `runStreamedInternal`, `run`, `normalizeInput`
- `src/outputSchemaFile.ts`: output schema 임시 파일 생성/정리
- `src/exec.ts`: commandArgs 구성, stdin 입력, stdout line streaming
- `tests/run.test.ts`: 옵션 전달, schema 파일 정리, text segment 결합, image 전달 검증

## 4. 실행/사용 진입점

패키지 공개 진입점은 `src/index.ts`다. 여기서 `Codex`, `Thread`, event/item 타입, option 타입을 re-export한다.

런타임의 실제 실행 진입점은 `src/exec.ts`의 `CodexExec.run()`이다. 이 메서드는 다음 형태로 CLI를 실행한다.

```text
codex exec --experimental-json ...
```

thread 재개 시에는 `resume <threadId>`를 추가하고, 이미지 입력은 그 뒤에 `--image <path>`로 추가한다. `tests/exec.test.ts`는 resume 인자가 image 인자보다 먼저 배치되는 것을 검증한다.

샘플 진입점은 `samples/` 아래 세 파일이다.

- `samples/basic_streaming.ts`: 대화형 readline 루프에서 `runStreamed()` 이벤트를 출력
- `samples/structured_output.ts`: JSON schema 객체를 `outputSchema`로 전달
- `samples/structured_output_zod.ts`: Zod schema를 `zod-to-json-schema`로 변환해 전달

## 5. 주요 모듈과 책임

`src/index.ts`

- 패키지 공개 API를 모으는 barrel 파일이다.
- event, item, `Codex`, `Thread`, option 타입을 외부에 노출한다.

`src/codex.ts`

- SDK의 메인 클래스 `Codex`를 정의한다.
- 생성자에서 `CodexExec`를 만들고, client-level `CodexOptions`를 보관한다.
- `startThread()`와 `resumeThread()`로 `Thread`를 생성한다.

`src/thread.ts`

- 사용자 입력, thread id, thread option, turn option을 조합한다.
- `runStreamed()`는 `ThreadEvent` async generator를 제공한다.
- `run()`은 스트림을 소비하면서 완료된 item을 모으고 마지막 `agent_message`를 `finalResponse`로 기록한다.
- `thread.started` 이벤트가 오면 내부 `_id`를 갱신한다.

`src/exec.ts`

- CLI 바이너리 위치를 찾고 하위 프로세스를 실행한다.
- SDK 옵션을 CLI 플래그와 환경 변수로 변환한다.
- stdout을 줄 단위 JSONL 문자열로 yield한다.
- 종료 코드, signal, stderr, spawn error를 오류로 표면화한다.

`src/events.ts`, `src/items.ts`

- `codex exec --experimental-json` 이벤트와 item의 TypeScript 타입을 정의한다.
- 파일 주석상 타입 모델은 `codex-rs/exec/src/exec_events.rs` 기반이지만, 해당 Rust 파일은 이번 범위 밖이라 직접 검증하지 않았다.

`src/outputSchemaFile.ts`

- `outputSchema`가 있으면 임시 디렉터리에 `schema.json`을 쓰고 cleanup 함수를 반환한다.
- schema가 plain object가 아니면 오류를 던진다.

`src/codexOptions.ts`, `src/threadOptions.ts`, `src/turnOptions.ts`

- client/thread/turn 단위 설정 타입을 정의한다.

## 6. 핵심 개념과 용어

- `Codex`: SDK client. CLI 실행기와 전역 옵션을 소유한다.
- `Thread`: 하나의 Codex 대화 세션. 여러 turn을 이어서 실행할 수 있고 id로 재개할 수 있다.
- `Turn`: 하나의 사용자 입력 처리 단위. 완료 결과는 `items`, `finalResponse`, `usage`로 표현된다.
- `ThreadEvent`: JSONL 스트림의 top-level 이벤트. `thread.started`, `turn.started`, `item.started`, `item.updated`, `item.completed`, `turn.completed`, `turn.failed`, `error`가 있다.
- `ThreadItem`: agent가 생성하거나 수행한 작업 단위. agent message, reasoning, command execution, file change, MCP tool call, web search, todo list, error item을 포함한다.
- `CodexExec`: TypeScript API와 실제 `codex` CLI 프로세스 사이의 어댑터다.
- `outputSchema`: 구조화 출력을 위해 turn 단위로 넘기는 JSON schema 객체다.
- `config overrides`: JSON 객체를 dotted path와 TOML literal로 직렬화해 `--config key=value`로 넘기는 설정이다.

## 7. 입력/데이터/상태/제어 흐름

일반 실행 흐름은 다음과 같다.

1. 사용자가 `Codex`를 생성한다.
2. `Codex` 생성자는 `CodexExec`를 준비한다. `codexPathOverride`가 없으면 플랫폼별 `@openai/codex-*` 패키지에서 CLI 바이너리를 찾는다.
3. 사용자가 `startThread()` 또는 `resumeThread(id)`를 호출한다.
4. `Thread.run()` 또는 `Thread.runStreamed()`가 입력을 정규화한다.
5. 문자열 입력은 그대로 prompt가 되고, 배열 입력의 `text` 항목은 빈 줄로 결합되며, `local_image` 항목은 image path 배열로 분리된다.
6. `outputSchema`가 있으면 임시 `schema.json`을 만들고 `--output-schema` 인자로 넘긴다.
7. `CodexExec.run()`이 `codex exec --experimental-json`을 spawn한다.
8. prompt는 child process stdin으로 쓰고 닫는다.
9. stdout은 line 단위로 읽고, `Thread`가 각 line을 JSON으로 parse해 `ThreadEvent`로 yield한다.
10. `thread.started` 이벤트가 오면 `Thread.id`가 갱신된다.
11. `run()`은 `item.completed`를 모으고, `turn.completed`의 usage를 저장하며, `turn.failed`가 오면 오류를 던진다.
12. generator 종료 시 schema 임시 디렉터리는 cleanup된다.

상태는 SDK 내부에서 매우 작게 유지된다. `Thread`는 `_id`, `_threadOptions`, `_options`, `_exec`를 들고 있고, 실제 대화 기록과 세션 지속성은 CLI 쪽 `~/.codex/sessions`에 의존한다고 README가 설명한다.

## 8. 설정 및 환경 구성

`CodexOptions`

- `codexPathOverride`: 기본 바이너리 탐색 대신 특정 CLI 경로를 사용한다.
- `baseUrl`: `--config openai_base_url=...`로 전달된다.
- `apiKey`: child process 환경 변수 `CODEX_API_KEY`로 전달된다.
- `config`: 전역 CLI config override 객체다.
- `env`: child process에 전달할 환경 변수 전체를 직접 지정한다. 제공되면 `process.env`를 상속하지 않는다.

`ThreadOptions`

- `model` -> `--model`
- `sandboxMode` -> `--sandbox`
- `workingDirectory` -> `--cd`
- `additionalDirectories` -> 반복 `--add-dir`
- `skipGitRepoCheck` -> `--skip-git-repo-check`
- `modelReasoningEffort` -> `--config model_reasoning_effort=...`
- `networkAccessEnabled` -> `--config sandbox_workspace_write.network_access=...`
- `webSearchMode` -> `--config web_search=...`
- `webSearchEnabled` -> legacy boolean을 `web_search="live"` 또는 `web_search="disabled"`로 변환
- `approvalPolicy` -> `--config approval_policy=...`

`TurnOptions`

- `outputSchema`: 임시 JSON schema 파일로 전달된다.
- `signal`: `spawn()` 옵션으로 전달되어 turn 실행을 abort할 수 있다.

전역 `config` override는 `CodexExec.run()` 초반에 먼저 emitted되고, thread option에서 생성되는 override는 뒤에 추가된다. `tests/run.test.ts`는 같은 key가 겹칠 때 thread option 값이 뒤에 오므로 우선 적용된다는 기대를 검증한다.

## 9. 의존성 구조

`package.json` 기준 런타임 패키지 항목은 `dependencies`로 분리되어 있지 않고, `devDependencies`만 보인다. 주요 개발 의존성은 다음과 같다.

- TypeScript/build/test: `typescript`, `tsup`, `jest`, `ts-jest`, `ts-node`
- lint/format: `eslint`, `typescript-eslint`, `prettier`
- 타입/보조: `@types/node`, `@types/jest`
- MCP item typing: `@modelcontextprotocol/sdk`
- structured output 샘플: `zod`, `zod-to-json-schema`

런타임상 중요한 외부 의존은 `@openai/codex` CLI와 플랫폼별 바이너리 패키지다. `src/exec.ts`의 `findCodexPath()`는 `@openai/codex/package.json`을 resolve하고, 그 패키지 기준으로 `@openai/codex-linux-x64`, `@openai/codex-darwin-arm64`, `@openai/codex-win32-x64` 같은 플랫폼 패키지의 `vendor/<target>/codex/<binary>` 경로를 찾는다.

확인 필요: `sdk/typescript/package.json` 범위 안에서는 `@openai/codex`가 `dependencies` 또는 `peerDependencies`로 선언된 근거가 보이지 않는다. 실제 배포 시 `@openai/codex`와 플랫폼 optional dependency가 어떻게 함께 설치되는지는 상위 workspace 또는 publish 설정 확인이 필요하지만, 이번 범위에서는 제외했다.

## 10. 빌드/실행/테스트 방식

빌드

- `package.json`의 `build`는 `tsup`이다.
- `tsup.config.ts`는 entry를 `src/index.ts`, format을 ESM, target을 `node18`, dts와 sourcemap 생성을 켠다.
- `tsconfig.json`은 `strict`, `noUncheckedIndexedAccess`, declaration output, `moduleResolution: "bundler"`를 사용한다.

테스트

- `package.json`의 `test`는 `jest`다.
- `jest.config.cjs`는 `ts-jest/presets/default-esm`, Node test environment, `tests/setupCodexHome.ts` setup, `**/tests/**/*.test.ts` match를 사용한다.
- `tests/setupCodexHome.ts`는 각 테스트마다 임시 `CODEX_HOME`을 만들고 끝나면 제거한다.
- `tests/testCodex.ts`는 `CODEX_EXEC_PATH`가 있으면 그 값을 쓰고, 없으면 `../../codex-rs/target/debug/codex`를 테스트 CLI 경로로 사용한다.
- `tests/responsesProxy.ts`는 로컬 HTTP `/responses` SSE mock server를 띄워 CLI와 Responses API 사이의 요청/응답을 검증한다.

샘플 실행

- 샘플 파일들은 shebang으로 `pnpm ts-node-esm --files`를 사용한다.
- `samples/helpers.ts`는 `CODEX_EXECUTABLE` 환경 변수가 있으면 그 경로를, 없으면 `../../codex-rs/target/debug/codex`를 사용한다.

## 11. 에러 처리와 디버깅 포인트

주요 오류 처리 지점은 다음과 같다.

- `src/thread.ts`: stdout line이 JSON parse에 실패하면 `Failed to parse item: ...` 오류를 던진다.
- `src/thread.ts`: `turn.failed` 이벤트를 만나면 `event.error.message`로 오류를 던진다.
- `src/outputSchemaFile.ts`: `outputSchema`가 plain JSON object가 아니면 `outputSchema must be a plain JSON object` 오류를 던진다.
- `src/exec.ts`: child process에 stdin/stdout이 없으면 즉시 kill 후 오류를 던진다.
- `src/exec.ts`: process exit code가 0이 아니거나 signal로 종료되면 stderr 내용을 포함해 `Codex Exec exited with ...` 오류를 던진다.
- `src/exec.ts`: 지원하지 않는 platform/arch 조합이면 `Unsupported platform` 또는 `Unsupported target triple` 오류를 던진다.
- `src/exec.ts`: `@openai/codex`와 플랫폼 바이너리를 resolve하지 못하면 CLI binary를 찾을 수 없다는 오류를 던진다.
- `src/exec.ts`: config override 값이 finite number가 아니거나 null/unsupported type이면 오류를 던진다.

디버깅 단서:

- CLI 호출 인자는 `CodexExec.run()`의 `commandArgs` 구성 순서로 추적하면 된다.
- 환경 변수 문제는 `CodexOptions.env`, `CODEX_API_KEY`, `CODEX_INTERNAL_ORIGINATOR_OVERRIDE` 주입 지점을 보면 된다.
- 테스트에서는 `tests/codexExecSpy.ts`가 `child_process.spawn`을 감싸 command args와 env를 기록한다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 공개 API나 타입을 추가할 때는 `src/index.ts` export를 같이 확인해야 한다.

새 CLI 옵션을 SDK에 노출하려면 보통 다음 순서가 필요하다.

1. `src/threadOptions.ts` 또는 `src/codexOptions.ts`에 타입 추가
2. `src/thread.ts`에서 `CodexExec.run()` 인자로 전달
3. `src/exec.ts`의 `CodexExecArgs`와 commandArgs 변환 로직 추가
4. `tests/run.test.ts` 또는 `tests/exec.test.ts`에 인자 전달 테스트 추가
5. 필요하면 `README.md` 사용 예시 추가

새 이벤트나 item 타입을 지원하려면 `src/events.ts`, `src/items.ts`, `README.md` streaming 예시, `samples/basic_streaming.ts`, 관련 테스트를 함께 보면 된다.

structured output 관련 변경은 `src/outputSchemaFile.ts`, `src/thread.ts`, `tests/run.test.ts`, `tests/runStreamed.test.ts`, `samples/structured_output*.ts`를 함께 확인해야 한다.

## 13. 처음 기여자가 먼저 읽어야 할 파일

추천 순서:

1. `README.md`: SDK의 의도와 사용자-facing API 파악
2. `src/index.ts`: 외부에 노출되는 API 표면 확인
3. `src/codex.ts`: client와 thread 생성 구조 확인
4. `src/thread.ts`: `run()`/`runStreamed()` 흐름, 입력 정규화, thread id 갱신 확인
5. `src/exec.ts`: CLI spawn, 옵션 매핑, 환경 변수, JSONL transport 확인
6. `src/events.ts`, `src/items.ts`: 스트리밍 이벤트와 item 타입 모델 확인
7. `tests/run.test.ts`, `tests/runStreamed.test.ts`, `tests/exec.test.ts`: 실제 기대 동작과 옵션 precedence 확인
8. `samples/basic_streaming.ts`: 사용자 입장에서 streaming event를 처리하는 방식 확인

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- `src/events.ts`와 `src/items.ts`는 Rust 쪽 `codex-rs/exec/src/exec_events.rs` 기반이라고 주석을 달고 있다. 이번 분석은 `sdk/typescript`로 제한했기 때문에 Rust 이벤트 정의와 TypeScript 타입의 완전한 동기화 여부는 확인하지 않았다.
- `@openai/codex` CLI 및 플랫폼별 바이너리 패키지가 최종 npm 배포에서 어떤 dependency 관계로 설치되는지는 `sdk/typescript/package.json`만으로는 확인되지 않는다.
- `codex exec --experimental-json` 프로토콜의 모든 event payload 세부 형식은 SDK 타입과 테스트 mock 기준으로만 확인했다. 실제 CLI 구현과의 전체 대응 관계는 범위 밖이다.
- 테스트 실행 자체는 이 보고서 작성 중 수행하지 않았다. 테스트는 `CODEX_EXEC_PATH` 또는 `../../codex-rs/target/debug/codex`에 실제 CLI 바이너리가 있어야 정상적으로 돌 수 있다.
