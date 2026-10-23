---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/main.ts
  - src/mainUtils.ts
  - src/migrate.ts
  - src/util/env.ts
  - src/util/config/manage.ts
  - src/database/index.ts
  - src/database/tables.ts
  - src/database/evalDeletion.ts
  - src/database/signal.ts
  - src/models/eval.ts
  - src/models/evalResult.ts
  - src/models/evalMutation.ts
  - src/util/database.ts
  - src/commands/eval.ts
  - src/commands/list.ts
  - src/commands/show.ts
  - src/commands/delete.ts
  - src/commands/export.ts
  - src/commands/import.ts
  - src/commands/retry.ts
  - src/node/doEval.ts
  - src/node/retry.ts
  - src/node/evaluatorRuntime.ts
  - src/node/evaluationStore.ts
  - src/evaluator.ts
  - src/util/output.ts
  - src/util/outputFormats.ts
  - src/util/exportToFile/writeToFile.ts
  - src/util/eval/evalTableUtils.ts
  - src/util/junit.ts
  - src/util/sanitizer.ts
  - src/util/sharing.ts
  - src/util/cliOptions.ts
  - src/importers/parse.ts
  - src/table.ts
  - src/tableOutput.html
  - src/types/index.ts
  - src/blobs/extractor.ts
  - src/tracing/store.ts
  - src/server/server.ts
  - drizzle/0023_wooden_mandrill.sql
  - drizzle/0024_repair_eval_redteam_flags.sql
  - drizzle/0025_broken_emma_frost.sql
  - site/docs/configuration/outputs.md
  - site/docs/usage/command-line.md
depends:
  - eval-records.md
  - provider-contract.md
status: ready
reimplementation: 미실행
---

# 결과 저장·출력·결과 관리 명령 (SQLite 영속화, `-o` 출력, `list/show/export/import/delete/retry`)

> 평가 결과를 로컬 SQLite 파일에 점진적으로 영속시키고, 그 기록을 `list`·`show`로 훑고, `-o <파일>`·`export`로 json·yaml·txt·xml·html·csv·jsonl·junit.xml 파일로 꺼내고, `import`로 JSON을 되가져오고, `delete`·`retry`·`--resume`으로 관리하는 기능이다. 레코드 모양은 [eval-records](eval-records.md)가 정한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 모든 CLI 명령은 시작할 때 설정 디렉터리(기본 `~/.promptfoo`)의 `promptfoo.db`를 열고 `drizzle/` 마이그레이션을 적용한다(R-01, R-04).
2. `eval`이 `--no-write`가 아니면 평가를 시작하기 전에 `evals` 행(설정 스냅샷, 태그, 프롬프트·데이터셋 연결 포함)을 만든다. 그 뒤 칸이 끝날 때마다 `eval_results` 행이 하나씩 들어가고, 열 메트릭은 일정 간격으로 덮어 저장된다(R-06~R-08).
3. 평가가 끝나면 `vars`·소요 시간이 저장되고 CLI 표가 출력된다. 공유(`share`)는 별도 결정이고 로컬 저장과 무관하다(R-08, R-28, R-42).
4. 그 뒤 `-o`/`outputPath`로 지정한 파일들을 확장자별 형식으로 한꺼번에 쓴다. jsonl만은 평가 도중에도 같은 경로로 행을 흘려 쓴다(R-19~R-26).
5. 나중에 `list`·`show`로 기록을 훑고, `export eval`로 JSON을 꺼내고, `import`로 되가져오고, `delete`로 지운다(R-12~R-15, R-29~R-33).
6. 중단된 평가는 `eval --resume [id]`로 이어 가고, 오류 행만 `retry <id>`/`--retry-errors`로 다시 돌린다. 둘 다 같은 eval id의 행을 갱신한다(R-09~R-11).

### 1.2 범위·통합 지점

- 제공: 저장 위치·환경변수·연결 정책·마이그레이션, 저장 시점과 중단·재개 상태, 기록 조회 명령과 교차 평가 모음 기능의 유무, 출력 형식별 내용과 옵션, export/import 왕복 범위, 삭제·동시 접근 규칙, 비밀 정제 범위.
- 제외(이유):
  - 웹 UI·서버 API(`web-ui` 스펙). 다만 태그 필터를 가진 유일한 소비자가 서버 `/api/history`이므로 그 존재만 R-17에 적는다.
  - 공유·호스팅 연동(`hosted-integration`)과 레드팀 리포트. 공유 *결정*이 로컬 저장을 끄지 않는다는 사실만 R-42에 적는다.
  - 평가 실행 순서·필터·동시성(`eval-run`). 재개·재시도가 *무엇을 저장하고 지우는지*만 R-09~R-11에 적는다.
  - 레코드 필드·집계 규칙은 eval-records, `ProviderResponse` 의미는 [provider-contract](provider-contract.md)가 정하므로 복제하지 않는다.
  - OpenAI Evals JSONL의 변환 규칙(`src/importers/openaiEvals`). 스킬 평가 기록 목적과 무관한 외부 형식 변환이라 열지 않았고, 입구(R-30)만 적는다.
  - 레거시 v3 `Eval`(`evals.results.table` 비정규화 저장). 새 평가는 항상 v4로 저장되므로 보장 대상에서 제외하고, import·export 입구에서 갈라지는 지점만 R-30에 적는다.
- 외부 의존·선행 계약: 저장 경계는 eval-records R-26(`EvaluationStore`, 기본 구현이 `Eval` 위의 `EvalEvaluationStore`)이다. 이 스펙은 그 구현체가 호출되는 시점과 DB 쪽 효과를 적는다. SQLite 접근은 libsql 클라이언트(`@libsql/client`)와 drizzle ORM이다.
- 소유 상태·부작용: 설정 디렉터리의 `promptfoo.db`(+WAL 파일), `evalLastWritten`(신호 파일), 지정한 출력 파일들. 같은 디렉터리의 `cache/`·`logs/`·`blobs/`·`promptfoo.yaml`은 R-02에서 위치만 적는다.

### 1.3 인터페이스와 데이터 의미

**설정·환경변수** (이름은 원문)

| 이름 | 종류 | 의미 |
|---|---|---|
| `PROMPTFOO_CONFIG_DIR` | env | 설정 디렉터리. 기본 `~/.promptfoo`. DB는 그 안의 `promptfoo.db`(R-01) |
| `--env-file`, `--env-path` | CLI 전역 | argv를 미리 훑어 로드하며, 이 파일의 `PROMPTFOO_CONFIG_DIR`도 반영된다(R-01) |
| `IS_TESTING` | env | 참이면 파일 대신 공유 메모리 DB(`file::memory:?cache=shared`) |
| `PROMPTFOO_DISABLE_WAL_MODE` | env | 참이면 WAL 설정·종료 시 checkpoint를 건너뜀(R-03) |
| `PROMPTFOO_ENABLE_DATABASE_LOGS` | env | 참이면 drizzle 쿼리를 debug 로그로 남김 |
| `PROMPTFOO_STRIP_PROMPT_TEXT`·`_RESPONSE_OUTPUT`·`_TEST_VARS`·`_GRADING_RESULT`·`_METADATA` | env 또는 설정 `env:` | 출력(파일)에서 해당 필드를 지움(R-40) |
| `PROMPTFOO_DISABLE_CSV_FORMULA_ESCAPING` | env 또는 설정 `env:` | CSV 수식 이스케이프 끄기(R-41) |
| `PROMPTFOO_INLINE_MEDIA` | env | 참이면 이진 응답을 blob으로 빼지 않고 인라인 저장. 기본은 blob 외부화 |
| `PROMPTFOO_DISABLE_SHARING` | env | 공유 자동 실행 끄기(R-42) |
| 설정 파일 `outputPath` | string 또는 list | `-o`와 같은 출력 경로(R-19) |
| 설정 파일 `tags` / CLI `--tag k=v` | map&lt;string,string&gt; | 평가에 붙는 라벨(R-17) |
| 설정 파일 `description`, `--description` | string | `evals.description`에 복사 |
| `commandLineOptions.write`·`.table` | 설정 | `--no-write`·`--no-table`의 Commander 기본값. **자동 로드되는 기본 설정 파일에서만** 읽는다(R-06, R-28) |

**CLI**

| 명령 | 입력 | 출력·효과 |
|---|---|---|
| `eval ... -o <paths...>` | 확장자가 형식을 정하는 경로 하나 이상 | 평가 후 파일 작성(R-19~R-27) |
| `eval --no-write` | — | DB에 아무것도 쓰지 않음. `--resume`·`--retry-errors`와 병용 불가(R-06) |
| `eval --no-table` / `--table-cell-max-length <n>` | — | CLI 표 끄기 / 셀 길이(기본 250)(R-28) |
| `eval --tag k=v`(반복) | — | `config.tags`에 합쳐져 저장(R-17) |
| `eval --resume [evalId]` | 생략하면 latest | 미완료 칸만 이어서 실행(R-10) |
| `eval --retry-errors` | — | latest eval의 ERROR 행만 재실행(R-11) |
| `retry <evalId> [-c cfg] [-v] [--max-concurrency n] [--delay ms] [--share/--no-share]` | 정확한 eval id | ERROR 행만 재실행해 같은 eval에 반영(R-11) |
| `list evals [-n N] [--ids-only] [--env-file]` | | 최근 N개(기본 100)(R-12) |
| `list prompts`, `list datasets` (같은 옵션) | | 프롬프트·데이터셋 기준 모음(R-13) |
| `show [id]`, `show eval [id]`, `show prompt <id>`, `show dataset <id>` | | 상세(R-14) |
| `export eval <evalId\|latest> [-o path] [--include-media]` | | JSON(기본 stdout)(R-29) |
| `import <file> [--new-id] [--force]` | promptfoo JSON export 또는 OpenAI Evals JSONL | 새 eval 생성(R-30, R-31) |
| `delete <id>`, `delete eval <id\|latest\|all>` | | 삭제(R-33) |

**출력 파일 형식** (확장자 소문자 비교, 지원: `csv html json jsonl txt xml yaml yml`, 그리고 접미사 `.junit.xml`이 `xml`보다 우선)

| 형식 | 최상위 내용 | 근거 |
|---|---|---|
| json, yaml/yml, txt | `OutputFile`: `evalId`, `results`(EvaluateSummaryV3: `version:3`, `timestamp`, `prompts`, `results`, `stats`, 선택 `repeatStability`), 정제된 `config`, `shareableUrl`, `metadata{promptfooVersion,nodeVersion,platform,arch,exportedAt,evaluationCreatedAt,author}`, 선택 `vars`, `runtimeOptions`, `traces`, `blobAssets`. **`txt`는 YAML 덤프**다 | R-21 |
| xml | `<promptfoo>{evalId, results, config, shareableUrl}`. metadata·vars·traces는 없음 | R-22 |
| html | 정적 보고서 한 장. 설정은 `description`만 보임 | R-23 |
| csv | 변수 열 + 프롬프트(열)마다 7개 열 | R-24 |
| jsonl | 한 줄에 `EvaluateResult` 한 행(정제됨). 헤더·메타 줄 없음 | R-25 |
| junit.xml | `testsuites > testsuite(provider×prompt) > testcase(칸)` | R-26 |

### 1.4 행동 규칙과 남은 질문

**저장소 위치·연결·마이그레이션**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | DB 위치 | 설정 디렉터리 = `setConfigDirectoryPath`로 명시한 값 ‖ **프로세스 시작 시점에 읽은** `PROMPTFOO_CONFIG_DIR` ‖ `~/.promptfoo`. DB 파일 = `<디렉터리>/promptfoo.db`이고 디렉터리는 없으면 `mkdir -p`로 만든다. `--env-file` 값은 argv에서 미리 로드되고 그때 한 번만 `PROMPTFOO_CONFIG_DIR`가 다시 읽힌다. 평가 설정 파일의 `env:`나 이후 로드한 env는 DB 위치를 바꾸지 않는다. `view`·`eval setup`은 `[directory]` 인자로 디렉터리를 명시한다. 테스트 러너(vitest 등)가 기본 DB(`~/.promptfoo/promptfoo.db`)를 열려 하면 예외로 거부한다. `IS_TESTING`이면 파일 없이 공유 메모리 DB | 코드 확인 |
| R-02 | 같은 디렉터리의 다른 영속물 | `evalLastWritten`(신호 파일, R-36), `cache/`(응답 캐시, `PROMPTFOO_CACHE_PATH`로 분리 가능), `logs/`, `blobs/`(이진 응답 파일, 메타·참조는 DB `blob_assets`·`blob_references`), `promptfoo.yaml`(전역 설정, 로그인·ID 등) | 코드 확인 |
| R-03 | 연결·잠금 정책 | 한 프로세스에 클라이언트 하나(`concurrency:1`), 모든 최상위 문의는 프로세스 안에서 직렬 큐로 실행되고 트랜잭션 콜백 안에서는 `tx`만 쓸 수 있다(루트 호출은 거부). 연결마다 `foreign_keys=ON`, `busy_timeout=5000ms`, WAL이 켜지면 `wal_autocheckpoint=1000`·`synchronous=NORMAL`. WAL 전환이 실패하면 경고만 하고 기본 저널로 계속. 일시적 `SQLITE_BUSY/LOCKED`는 문장 단위로 최대 10회, 5ms부터 두 배씩(최대 250ms) 재시도하고 재연결로 복구를 시도하며, 트랜잭션은 재시도하지 않는다. 종료 때 `PRAGMA wal_checkpoint(TRUNCATE)`를 시도하되(`busy_timeout=0`) 실패해도 커밋된 데이터는 WAL에 남아 다음 열기에서 복구된다 | 코드 확인 |
| R-04 | 마이그레이션 | CLI는 명령 파싱 전에 항상 `runDbMigrations`를 부른다(`--no-write`여도). `drizzle/`의 SQL을 순서대로 적용하고 이미 적용된 것은 건너뛰며 DB 파일이 없으면 만든다(건너뛰기 기록은 drizzle 마이그레이터 몫이고 그 내부는 읽지 않았다). 폴더 위치: 번들 실행(`dist/src`)이면 `<루트>/dist/drizzle`, 클라우드 번들(`dist/server/src`)이면 `<루트>/dist/promptfoo/drizzle`, 소스 실행이면 `src/../drizzle`. 실패하면 오류를 로그하고 던진다. 기준 SHA에는 `0000`~`0025`(26개)가 있다. 최신 셋: `0023` 인덱스 2개(`blob_assets.mime_type`, `blob_references(blob_hash,created_at)`), `0024` `evals.is_redteam`을 `config.redteam` 존재 여부로 재계산, `0025` 중복 `spans`(같은 `trace_id,span_id`)을 가장 앞 행만 남기고 삭제한 뒤 유일 인덱스 추가. `evals`·`eval_results` 등 소유 테이블의 컬럼은 eval-records C-04를 따른다 | 코드 확인 / drizzle 내부 동작은 외부 라이브러리 |
| R-05 | 이 스펙이 더하는 테이블 | `tags(id=sha256("이름:값"), name, value)`(이름+값 유일), `evals_to_tags(eval_id, tag_id)`(PK 둘, `eval_id` FK에 cascade 없음), `blob_assets(hash PK, size_bytes, mime_type, provider)`, `blob_references(blob_hash FK cascade, eval_id FK cascade, test_idx, prompt_idx, location, kind)`, `traces`·`spans`(FK, cascade 없음), `configs`, `model_audits`. `evals_to_prompts.eval_id`는 cascade FK, `evals_to_datasets`·`evals_to_tags`·`eval_results.eval_id`·`traces.evaluation_id`는 cascade 없는 FK다. 외래 키는 `foreign_keys=ON`으로 강제된다 | 코드 확인 |

**저장 시점·중단·재개**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | `eval` 시작(쓰기 모드) | 설정을 푼 뒤, 평가를 시작하기 **전에** `Eval.create`로 `evals` 행(eval-records R-18)을 한 트랜잭션으로 만든다. 따라서 평가 도중 중단돼도 `evals` 행은 남는다. `--no-write`이면 `Eval.create`를 부르지 않고 `new Eval(config, {persisted:false})`(id는 메모리에서 생성)를 쓰며 행은 메모리 `results`에만 쌓여 DB에는 `evals`·`eval_results`·태그·프롬프트 연결이 전혀 생기지 않는다. `-o` 출력·CLI 표는 메모리 행으로 그대로 만들어진다. `write` 기본값은 true이고 자동 로드된 기본 설정 파일의 `commandLineOptions.write`만 이 기본값을 바꾼다(`-c`로 준 설정의 `commandLineOptions.write`는 읽는 코드가 없다) | 코드 확인 |
| R-07 | 칸이 끝날 때마다 | 평가기는 행 하나가 만들어지는 즉시 `appendResult`(→ `Eval.addResult` → `eval_results` insert, eval-records R-16)를 호출한다. 즉 **종료 시 일괄 저장이 아니라 행 단위 점진 저장**이다. insert가 실패하면 평가는 멈추지 않고 오류를 로그하며 `resultPersistenceFailed=true`가 되고 그 행은 메모리에 보관된다. 저장 뒤 같은 `testIdx`의 비교 어서션(`select-best`·`max-score`)이 행을 다시 쓴다(eval-records R-17). 매 저장 후 신호 파일이 갱신된다(R-36) | 코드 확인 |
| R-08 | 열·부가값 저장 | 열 목록(`evals.prompts`, 메트릭 포함)은 평가 시작 직후 한 번, 행 처리 중 **이전 flush 후 1초 이상 지났을 때** 다음 행 완료 시점마다, 끝에 한 번 통째로 덮어쓴다(eval-records R-19). `vars`는 끝에 `setVars`, `durationMs`는 `setDurationMs`로 정하고 `save()`가 `evals`를 갱신한다(`durationMs` 키는 `json_set`으로 `results` JSON에 병합해 동시 `save`가 다른 키를 덮지 않는다). `Eval.findById`는 `evals.vars`가 비어 있으면 행에서 변수 이름을 모아 채우고 DB에도 되쓴다. 종료 뒤 영속된 `Eval`은 메모리 행을 비우고(`clearResults`), 표·출력은 DB에서 다시 읽는다 | 코드 확인 |
| R-09 | 일시정지·중단 | CLI(`write`가 true)에서 첫 SIGINT는 "일시정지"다: 중단 신호를 보내 새 칸을 시작하지 않고, **응답이 오기 전에 끊긴 칸은 ERROR 행으로 저장하지 않고 건너뛴다**(재개 대상으로 남김). 이때 `vars`와 `prompts`(메트릭)만 저장하고 `save()`·`setDurationMs`는 부르지 않는다(`evals.durationMs`는 비고 `vars`는 R-08의 읽기 보정에 의존). 출력은 `Evaluation paused. ID: <id>`와 `promptfoo eval --resume <id>` 안내뿐이며 표·요약·`-o` 파일·공유는 건너뛴다. 두 번째 SIGINT 또는 일시정지 후 10초 안에 안 끝나면 checkpoint 없이 `process.exit(130)`한다. `--no-write`이거나 CLI가 아닌 호출이면 이 핸들러가 없다. 강제 종료(kill) 시 이미 저장된 행은 남고, 마지막 flush 이후의 열 메트릭 증분은 저장되지 않을 수 있다(R-10) | 코드 확인 / 강제 종료 후 상태는 추론 |
| R-10 | `eval --resume [evalId]` | `write=false`이면 오류("requires database persistence"). 생략하면 `latest`(`createdAt` 최신), 없으면 오류. **저장된 설정**(`evals.config`)으로 다시 해석해 같은 테스트 순서를 얻고, 저장된 `runtimeOptions`(repeat·cache·maxConcurrency·delay·filterRange·providerFilter)를 복원한다. CLI의 `--filter-providers`·`--filter-range`가 저장값과 다르면 경고하고 무시한다. `--tag`·`--retry-errors`와는 병용 불가(오류). 이미 `eval_results`에 있는 `(testIdx:promptIdx)` 칸은 **성공·실패·ERROR 구분 없이** 건너뛰고("Resuming: skipping N previously completed cases") 나머지만 실행한다. 저장된 열의 `metrics`를 그대로 이어받고 **재계산하지 않는다**(`testCacheHitCount` 누락 보충만 예외). 그러므로 마지막 flush 이후 저장된 행은 `eval_results`에는 있어도 열 `metrics`에 빠져 있을 수 있다(추론). 저장된 완료 칸을 읽다 실패하면 경고하고 전체를 다시 실행한다. jsonl 출력 경로는 `append`로 열린다 | 코드 확인 / 메트릭 누락은 추론 |
| R-11 | 오류 행 재시도 | **`eval --retry-errors`**: latest eval의 `failure_reason=ERROR`(=2) 행 id를 모아 두고, 0개면 "No ERROR results"로 끝내며, 있으면 R-10과 같은 재개 경로로 `ERROR` 칸만 다시 실행한다(완료 칸 계산이 ERROR를 제외). 일시정지되지 않고 평가가 끝난 **뒤에만** 옛 ERROR 행을 삭제하고 열 `metrics`를 재계산한다(`derivedMetrics`는 다시 적용하지 않음, eval-records R-24). 정리가 실패하면 경고만 하고 새 행은 이미 저장돼 있다. **`retry <evalId>`**: 정확한 id만 받는다(`latest` 불가), 없으면 오류. 같은 흐름이며 `-c`가 없으면 저장된 설정을 쓰고 있으면 그 파일로 다시 해석한다(저장된 provider 필터는 유지, 그 필터가 provider를 하나도 못 맞추면 오류이고 기존 ERROR 행은 보존). 재실행 결과가 저장에 실패하면 오류로 끝내고 ERROR 행을 지우지 않는다. 성공하면 원본 설정의 **jsonl 출력 경로만** 다시 쓰고(다른 형식은 쓰지 않음) 공유 결정(R-42)을 한다. 두 경로 모두 새 eval을 만들지 않고 같은 id를 갱신한다. 같은 칸의 새 행과 옛 ERROR 행이 삭제 전까지 공존한다 | 코드 확인 |

**기록 조회·교차 평가 모음**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | `list evals [-n N] [--ids-only]` | `Eval.getMany(N)`: `createdAt` 내림차순 상위 N개(N이 없거나 0·비숫자면 100). 표는 **오름차순**으로 다시 정렬해 열 `eval id`, `description`(100자 초과 시 `...`), `prompts`(각 열 `sha256(raw)` 앞 6자, 쉼표 구분), `vars`를 보인다. `--ids-only`는 정렬 없이 `getMany` 순서(최신 먼저)로 id만 한 줄씩. 날짜·provider·점수 열과 필터 옵션은 없다 | 코드 확인 |
| R-13 | `list prompts`, `list datasets` | 둘 다 최신 N개(기본 100) eval을 읽어 **메모리에서** 묶는다. prompts: 열의 `raw` 문자열의 `sha256`(열 `id`와 다름)으로 묶어 `prompt id`(6자)·`raw`(100자)·`evals`(그 raw를 쓴 eval 수)·`recent eval`을 보이고, `recent eval` 문자열 오름차순으로 정렬한다. datasets: `sha256(JSON(config.tests))`로 묶고(배열·문자열인 `tests`만, `tests`가 없거나 생성기 객체면 제외), `best prompt`(그 데이터셋에 속한 raw별 최신 eval의 열 `metrics.score` 합이 가장 큰 raw), `evals`, `prompts`(서로 다른 raw 수), `recent eval`을 보인다. 둘 다 `-n`·`--ids-only`만 받는다. `tests`가 파일 참조 문자열이면 해시는 **내용이 아니라 참조 문자열**의 해시다 | 코드 확인 |
| R-14 | `show [id]` | id 없음: 최신 eval(`Eval.latest`), 없으면 오류·exit 1. id 있음: ① 최근 100개 eval 중 id가 접두 일치하는 것이 있으면 eval ② 최근 100개 eval에서 모은 프롬프트(`sha256(raw)` 접두 일치) ③ 데이터셋(접두 일치) 순으로 해석하고 모두 없으면 오류. `show eval [id]`는 정확한 id로 `Eval.findById`. eval 상세: 표(최대 25행, 셀 100자)와 `N prompts`, 앞 5개 고유 `Prompt IDs`, `N variables`(앞 5개 이름). `show prompt <id>`: raw 전문과, 그 raw를 쓴 eval 최대 10개의 `Eval ID`(6자)·`Dataset ID`(6자)·`Raw score`(=열 score 합)·`Pass rate`(통과/(통과+실패+오류))·`Pass count`·`Fail count`(+오류 수). 이 10개는 eval id 문자열 내림차순으로 고르며 id는 `eval-<임의 3자>-<시각>`이라 **시간순이 아니다**. `show dataset <id>`: 그 데이터셋의 raw별 최신 eval 한 줄씩(최대 10) | 코드 확인 |
| R-15 | id 접두 해석의 한계 | `show <id>`·`delete <id>`(상위 명령)는 접두 일치로 eval을 **찾지만**, 이어서 상세·삭제는 입력한 문자열 그대로 정확 일치로 부른다. 따라서 eval id의 접두만 주면 "찾았다"가 된 뒤 `No evaluation found`(show) 또는 `Eval with ID ... not found`(delete, exit 1)로 끝난다. 그리고 eval을 찾는 범위가 **최근 100개**라서 그보다 오래된 eval은 상위 명령 `show <id>`·`delete <id>`로 닿지 않고, `show eval <id>`·`delete eval <id>`(정확 id)로만 닿는다. 프롬프트·데이터셋 id는 6자 접두가 정상 동작한다 | 코드 확인 |
| R-16 | 교차 평가 모음·비교(있는 것) | 기본 제공은 다음뿐이다. (a) **같은 프롬프트 원문**의 eval들을 모아 점수·통과율을 나열: `show prompt`, `list prompts`(R-13, R-14). (b) **같은 `tests` 설정**(해시)의 eval들과 최고 프롬프트: `list datasets`/`show dataset`. (c) 서버 `GET /api/history?tagName&tagValue&description`: 최근 eval의 열 정보 행(`evalId`, `description`, `promptId`, `datasetId`, `createdAt`, 열 `metrics`)을 `createdAt` 내림차순으로 돌려주며(조인 행마다 그 eval의 모든 열을 펼치므로 같은 열이 중복될 수 있다) 태그 하나(이름·값 정확 일치)와 `description` 정확 일치로 거른다. `LIMIT`가 eval 수가 아니라 프롬프트·데이터셋·태그 조인 **행 수**에 걸린다(기본 100). 결과는 2시간 TTL LRU 캐시에 들어가고 변경 시 비워진다. (d) 서버 쪽 `getEvalSummaries(datasetId?, type?)`(eval·레드팀 구분, 데이터셋 필터, 합계 통과율)와 CSV 내보내기의 `comparisonEvalIds`(`testIdx`가 같은 행끼리 옆으로 붙임)와 eval 상세 UI의 비교. (e) 실행 쪽 `--filter-failing/-errors-only <evalId>`(`eval-run`) | 코드 확인 |
| R-17 | 라벨·태그 | 평가에 붙일 수 있는 라벨: `tags`(`map<string,string>`; 설정 `tags:`, 설정의 `commandLineOptions.tags`, CLI `--tag k=v` 반복, 우선순위 CLI > `commandLineOptions.tags` > 설정 `tags`, `k=v`가 아니거나 키가 비었거나 앞뒤 공백이 있으면 오류, 값은 그대로이며 빈 값 허용), `description`, `author`, 설정 `metadata`(자유 JSON, `evals.config`에 그대로). `Eval.create`가 `config.tags`마다 `tags` 행(`ON CONFLICT DO NOTHING`)과 `evals_to_tags` 행을 만든다. `evals.description`·`evals.author`(인덱스)·`evals.is_redteam`(인덱스)은 컬럼이다. `--resume`·`--retry-errors`에서는 새 태그를 받지 않고(오류) 원래 태그를 유지한다. 태그를 **읽는** 코드는 `getStandaloneEvals`(서버 `/api/history`)와 `Eval.copy`의 재삽입뿐이고, CLI의 `list`·`show`·`export`는 태그를 보이거나 거르지 않는다(내보낸 JSON의 `config.tags`로는 보인다) | 코드 확인(CLI에서 태그를 읽는 코드가 없다는 점은 `tagsTable`·`evalsToTagsTable` 사용처 전수 grep) |
| R-18 | 없는 것(코드로 확인) | 다음은 원본에 **없다**: (a) 모델·provider별로 여러 eval을 모아 시간순으로 보는 명령·쿼리(provider는 컬럼이 아니라 `evals.prompts[].provider` 문자열과 `config.providers` JSON 안에 있다), (b) 스킬·프롬프트 버전 같은 사용자 정의 키를 가진 전용 컬럼·인덱스, (c) 태그·메타데이터로 거르는 CLI, (d) 시계열(추세) 집계·두 eval 사이 회귀 비교 CLI(UI·`--filter-failing` 외), (e) eval 간 같은 칸을 잇는 안정 키(행 `id`는 매번 새 UUID, `testIdx`·`promptIdx`는 구성이 바뀌면 달라짐, eval-records 1.3). 같은 설정의 반복 실행을 묶는 단서는 `datasetId`(`tests` 설정 해시)·프롬프트 raw 해시·태그·`description`뿐이다 | 코드 확인(부재는 `list`/`show`/`util/database.ts`/`models/eval.ts`의 조회 함수 목록과 `tags` 사용처 grep) |

**출력 파일**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | 출력 경로 결정·검증 | 경로 목록 = CLI `-o <paths...>`(여러 번·여러 값 가능)가 있으면 **그것**, 없으면 설정 `outputPath`(문자열 또는 목록, 여러 설정 파일이면 이어 붙임). 둘은 합쳐지지 않는다. 형식 = `.junit.xml` 접미사면 `junit.xml`, 아니면 확장자(소문자)가 `csv html json jsonl txt xml yaml yml` 중 하나. **CLI `-o`만** 평가 시작 전에 확장자를 검사해 지원하지 않으면 `Unsupported output file format ...`으로 거부한다(exit 1, 평가 안 함). 설정 `outputPath`는 사전 검사가 없어 잘못된 확장자는 평가·저장이 **끝난 뒤** 출력 단계에서 실패한다. `https://docs.google.com/spreadsheets/`로 시작하는 경로는 `writeOutput`이 받지만 CLI `-o`의 사전 검사는 통과하지 못한다(R-27) | 코드 확인 |
| R-20 | 출력 쓰기 시점·실패 | 출력은 평가·표 출력·요약·(있다면) 공유가 모두 끝난 뒤에 쓴다(그래서 공유 URL이 `shareableUrl`에 들어갈 수 있다). 경로마다 `mkdir -p` 후 병렬로 쓰고 하나가 실패해도 나머지는 끝까지 쓴 뒤 "One or more output writes failed"를 던진다(`errors` 배열). 일시정지된 실행은 출력을 쓰지 않는다(R-09). 평가 결과는 출력 실패와 무관하게 이미 DB에 있다 | 코드 확인 |
| R-21 | `json`, `yaml`/`yml`, `txt` | 같은 `OutputFile`(1.3)을 만들어 JSON은 `JSON.stringify(…, 2)`로, 나머지는 `js-yaml` 덤프로 쓴다(`txt`도 YAML). `results`는 전체 행을 메모리에 올려 만든다(`toEvaluateSummary`가 `loadResults`). 문자열이 너무 길거나 힙이 모자라면 "Dataset too large for JSON export"로 끝나며 jsonl을 쓰라고 안내한다. 트레이스가 있으면 `traces`(민감 속성 정제), `--include-media`(export 전용)이면 `blobAssets`(base64, 오버사이즈는 건너뜀)가 붙는다. 설정은 R-38로 정제하고 `PROMPTFOO_STRIP_*`를 적용한다 | 코드 확인 |
| R-22 | `xml`(promptfoo XML) | 루트 `<promptfoo>` 아래 `evalId`, `results`(R-21과 같은 요약), `config`(정제), `shareableUrl`(없으면 빈 문자열). 모든 값은 문자열화되고 null은 빈 문자열이다. `metadata`·`vars`·`runtimeOptions`·`traces`는 쓰지 않는다. JUnit과 호환되지 않는다 | 코드 확인 |
| R-23 | `html` | 자체 완결 정적 보고서(`src/tableOutput.html`을 Nunjucks로 렌더, 모든 값 `escape`). 머리말: `config.description`, 내보낸 시각·평가 시각·author. 요약: 전체 결과 수, 통과율, 통과·실패·오류 수, 프롬프트 열 수. 표: 변수 열 + `[provider] label` 열마다 칸(상태 PASS/FAIL/ERROR, 점수, 이름 있는 점수, 출력 텍스트, grader 이유, 오류). 칸별 상세에 최종 프롬프트 전문, provider, 지연, 비용(`$`, 6자리, 0 초과일 때), 토큰(전체·입력·출력). 설정 JSON 자체나 응답 `metadata`는 싣지 않는다 | 코드 확인 |
| R-24 | `csv` | 행 = 테스트(`testIdx`), 스트리밍 방식(행 100개 단위 읽기, 헤더 전에 변수 열·설명·`Metric:` 열 후보를 한 번 훑음)이고 UI CSV와 같은 열 규칙이다. 열: `Description`(설명이 하나라도 있을 때만), 변수 이름들, 그리고 열(프롬프트)마다 `[provider] label`(출력 텍스트), `Status`(`PASS`/`FAIL`/`ERROR`), `Score`(소수 2자리), `Named Scores`(2자리로 반올림한 JSON), 열의 이름 있는 점수마다 `Metric: <이름>`(이름 정렬), `Grader Reason`, `Comment`. 레드팀이면 끝에 `Messages RedteamHistory RedteamTreeHistory pluginId strategyId sessionId sessionIds`가 붙는다. **지연·비용·토큰 열은 없다**. 다른 칸에 값이 없으면 빈 칸. 변수 값이 문자열이 아니면 CLI 경로는 `String(value)`로 바꾼다(객체 변수는 `[object Object]`가 된다. UI용 `generateEvalCsv` 경로는 JSON 문자열이다) | 코드 확인 |
| R-25 | `jsonl` | 평가 **도중** 칸마다 정제된 `EvaluateResult` 한 줄을 지정 경로로 흘려 쓴다(첫 쓰기에서 `w`로 열어 이전 내용을 지우고, 쓸 행이 없으면 파일을 건드리지 않는다. 재개 때는 `a`). 평가가 끝나면 같은 경로를 **DB(또는 메모리) 기준으로 통째로 다시 쓴다**: 같은 디렉터리에 `.promptfoo-<uuid>.tmp`를 만들고 `rename`으로 교체하며 기존 파일 권한을 유지한다. 권한 오류면 외부 임시 디렉터리에 백업·교체·복원하는 대체 경로를 탄다. 행 저장이 한 번이라도 실패했다면(`resultPersistenceFailed`) 스트리밍된 행·DB 행·메모리의 최종 행을 `testIdx:promptIdx` 키로 합쳐(나중 것 우선) 다시 쓴다. 한 줄 = 행 하나, 순서는 DB 읽기 순서(`testIdx`별 묶음), 헤더·합계 줄은 없다. 메모리를 거의 쓰지 않아 큰 평가에 권장되는 형식이다. jsonl은 promptfoo가 다시 읽을 수 없다(R-30) | 코드 확인 |
| R-26 | `junit.xml` | `<testsuites name="promptfoo" tests errors failures skipped=0 time>` 아래 (provider, 프롬프트) 쌍마다 `<testsuite name="[<provider label 또는 id>] prompt <순번>" ... timestamp>`(순번은 provider별 `promptIdx` 순, 표시 이름이 겹치는 provider는 id 해시 16자를 덧붙임), 칸마다 `<testcase name="test <testIdx+1>[: <설명>]" classname=suite time(초)>`. ASSERT 실패는 `<failure message="Assertion failed" type="assertion">`(점수, 실패한 어서션 종류 목록, 최대 8192자), 그 밖의 실패는 `<error message="Evaluation error" type="error">`. 시간은 칸의 `latencyMs` 합(초). 프롬프트·변수·출력·설정·이유 문장은 싣지 않는다. 이름은 512자로 자르고 XML 금지 문자를 지운다 | 코드 확인 |
| R-27 | Google Sheets URL | `writeOutput`은 `https://docs.google.com/spreadsheets/...` 경로를 받아 변수 열 + `[provider] label` 열(셀: `[PASS] (점수, 이름 있는 점수)\n\n출력\n\n이유`)을 시트에 쓴다. CLI `-o`는 R-19의 사전 검사 때문에 이 경로를 거부하므로 사실상 설정 `outputPath`로만 쓸 수 있다(구현은 시트 쓰기 모듈 `googleSheets`에 있고 열지 않았다) | 코드 확인 / 시트 쓰기는 미탐색 |
| R-28 | 표 출력·`--no-table` | 평가 후 CLI 표는 `table`이 참이고 로그 레벨이 `debug`가 아니고 전체 테스트 수가 500 미만일 때만 출력된다(500 이상이면 "Skipping table output..." 안내). 표는 최대 25행, 셀 길이는 `--table-cell-max-length`(기본 250), 25행을 넘으면 "... N more rows not shown". `--no-table`은 표만 끄며 저장·요약·`-o`에는 영향이 없다. `table` 기본값은 자동 로드된 기본 설정 파일의 `commandLineOptions.table`(R-06과 같은 한계) | 코드 확인 |
| R-29 | `export eval <id\|latest> [-o path] [--include-media]` | 정확한 id(또는 `latest`)로 `Eval`을 읽고, 없으면 오류·exit 1. `-o`가 있으면 `writeOutput`을 그대로 쓰므로 **확장자가 형식을 정한다**(`.csv`면 CSV, 설명은 "JSON file"이라 하지만). 없으면 `createOutputData`의 JSON(들여쓰기 2)을 로거(stdout)로 출력한다. `-o`를 값 없이 주면 `true`가 `writeOutput`에 넘어가 실패한다(추론: 문자열 메서드 호출). `--include-media`가 `blobAssets`를 싣는 유일한 경로다. 실패는 "Failed to export eval", exit 1 | 코드 확인 / 값 없는 `-o`는 추론 |

**가져오기·왕복**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | `import <file>` 입력 | 파일 전체를 JSON으로 파싱하고, 실패하면 줄 단위 JSONL로 파싱해 OpenAI Evals 행인지 본다. OpenAI Evals 모양이면 변환해서 들어가고(규칙 미탐색), 아니면 오류. JSON이 OpenAI Evals가 아니면 promptfoo export로 간주한다. 그다음 `results`가 ① v3(`version:3`, `prompts`·`results` 배열)이면 정규화 저장 경로, ② 레거시(`version`≠3, `results` 배열, `table` 객체)면 `evals.results`에 통째로 넣는 경로, ③ 그 밖은 "Unsupported eval export results format". **따라서 promptfoo가 쓴 jsonl·yaml·txt·xml·html·csv·junit.xml은 모두 가져올 수 없다.** 이름 = `evalId`(없으면 `id`), 생성 시각 = `metadata.evaluationCreatedAt` → `results.timestamp` → `createdAt` → 지금, author = `metadata.author` → `author`. 같은 id가 이미 있으면 기본은 오류(exit 1, "Use --new-id ... or --force"), `--new-id`는 새 id, `--force`는 기존 eval을 지우고 교체한다 | 코드 확인 |
| R-31 | import 쓰기 절차 | v3 경로: ① `--force`면 먼저 파일의 아티팩트(트레이스·blob)를 검증만 한다. ② blob(`blobAssets`)은 해시·크기를 검증하고(1건 한도 `BLOB_MAX_SIZE`), 안전한 inline MIME이 아니면 `application/octet-stream`으로 낮춰 저장한다. ③ `--force` 교체는 blob 복원 **뒤에** 기존 eval 삭제(`Eval.delete`)를 한다. ④ `Eval.create`(트랜잭션 하나: `evals`+프롬프트·데이터셋·**태그**(`config.tags`) 연결)로 만들고, 트레이스를 만든 뒤(충돌하거나 `--new-id`면 새 trace id), 행은 `createManyFromEvaluateResult`(트랜잭션 하나, 행 `id`는 새 UUID)로 넣는다. `completedPrompts`·`vars`·`runtimeOptions`·`stats.durationMs`류가 복원된다. **①~④ 전체는 한 트랜잭션이 아니다**: 행 삽입이 실패하면 `evals` 행(과 트레이스)이 행 없이 남을 수 있고(코드 확인), `--force`로 이미 지운 옛 eval은 복구되지 않으며 오류 메시지가 그렇게 알린다. 레거시 경로는 `evals` 한 행만 넣고(태그·연결 없음) 프롬프트 연결도 만들지 않는다 | 코드 확인 |
| R-32 | 왕복 가능성 | 왕복 가능한 형식은 **`export eval`/`-o *.json`이 만든 JSON 하나뿐**이다. 보존: eval id(기본), 생성 시각, author, 정제된 설정, 열(`prompts`와 메트릭), 행 전체(`response`·`gradingResult`·`namedScores`·`metadata`·`testCase` 등), 변수 순서, `runtimeOptions`, 소요 시간, 트레이스, 포함했을 때의 blob. **바뀌는 것**: 행 `id`(새 UUID), 설정의 비밀 값(출력 시 `[REDACTED]`로 정제되고 그 정제본이 그대로 저장되므로 가져온 eval의 `config`로는 원 키를 복원할 수 없다), 행의 `tokenUsage`(저장 컬럼이 없어 `response`에서 재구성, eval-records R-13), `PROMPTFOO_STRIP_*`로 지운 필드(지운 채로 저장), 신호·캐시·공유 상태(재생성 안 함). 태그와 데이터셋 연결은 문서(`command-line.md`)가 "재구성되지 않는다"고 쓰지만 **v3 가져오기에서는 `config.tags`·`config.tests`에서 다시 만들어진다**. 레거시 경로에서는 만들어지지 않는다 | 코드 확인 |

**삭제·정리·동시 접근**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-33 | `delete` | `delete eval <id>`: 정확한 id의 한 eval을 **한 트랜잭션**으로 지운다: 스팬·트레이스(스팬 먼저), `evals_to_prompts`, `evals_to_datasets`, `evals_to_tags`, `eval_results`, 마지막으로 `evals`(0행이면 "not found" 오류로 전체 롤백). `eval latest`는 최신 eval, `eval all`은 확인 프롬프트(`@inquirer/confirm`, 거절하면 아무것도 안 함) 후 위 테이블 전부를 비운다. `delete <id>`(상위 명령)는 R-15의 접두·최근 100개 제한이 있고 못 찾으면 "No resource found", exit 1. 실패는 "Could not delete ..." 로그와 exit 1. 삭제 후 이 프로세스의 캐시를 무효화하고 신호 파일에 삭제를 기록한다(R-36). 프롬프트·데이터셋·태그 **마스터 행**은 지우지 않는다 | 코드 확인 |
| R-34 | 보존·정리 규칙 | 평가 결과(`evals`·`eval_results`)를 나이·개수·크기로 자동 삭제하는 정책은 **없다**(삭제는 명령·서버 API로만; 코드 확인: `retention`/`ttl`/`prune` 검색에서 평가 기록에 해당하는 것 없음). 자동 보존 기간이 있는 것은 설정 `tracing`의 `retentionDays`로 트레이스·스팬만 지우는 경로(`deleteOldTraces`)와 응답 캐시 TTL뿐이다. `delete`는 `blob_references`를 cascade로 지우지만 `blob_assets` 행과 `blobs/` 파일은 지우는 코드가 없어 남는다(코드 확인: 삭제 함수가 `src/blobs`에 없음) | 코드 확인 |
| R-35 | 여러 프로세스의 동시 접근 | 지원 수단은 SQLite 수준뿐이다: WAL(읽기와 쓰기 병행), `busy_timeout` 5초, 프로세스 안 직렬화, 잠금 재시도(R-03), 행마다 즉시 커밋하는 짧은 쓰기, `durationMs` 병합용 `json_set`. 같은 eval을 쓰는 프로세스 사이를 막는 잠금은 **없다**: 두 프로세스가 같은 eval을 동시에 `--resume`하거나 `retry`하면 같은 칸이 중복 저장될 수 있다(`eval_results`에 `(eval_id,test_idx,prompt_idx)` 유일 제약이 없다, eval-records R-03)(추론). 평가 중인 eval을 다른 프로세스가 `delete`하면 `eval_results.eval_id` FK 때문에 이후 행 저장이 실패해 `resultPersistenceFailed`로 이어질 수 있다(추론). 새 eval id의 충돌은 `Eval.create`의 PK insert가 실패해 평가가 시작되지 못한다(`eval-<임의 3자>-<초>`, 추론) | 코드 확인 / 경합 결과는 추론 |
| R-36 | 신호 파일 | 행 저장·열 flush·`save`·삭제·가져오기마다 `evalLastWritten`을 갱신해 `view` 서버가 파일 감시(`fs.watch`, 250ms 디바운스)로 새로 고침할 수 있게 한다. 형식: 기본 `<evalId>:<ISO시각>` 텍스트, 같은 디바운스 창 안에 다른 갱신·삭제가 겹치면 JSON(`updatedEvalIds`, `deletedEvalIds`, `refreshLatest`)으로 합친다. 쓰기 실패는 경고만 한다. 잠금이 없어 프로세스 간 경합에서는 신호가 유실될 수 있고 다음 신호가 복구한다(코드 주석). 데이터의 정본은 DB이며 이 파일은 알림용이다 | 코드 확인 |

**비밀·민감 데이터**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-37 | DB에 들어가는 것 | `evals.config`는 **추적(tracing) 자격증명만 정제**하고(`sanitizeTracingConfigForPersistence`) 그 밖의 설정은 그대로 저장한다. 설정에 리터럴로 쓴 provider `apiKey` 등도 DB에는 쓴 그대로 남는다. 그뿐 아니라 설정 파일의 `{{ env.X }}` 템플릿은 **설정을 읽는 시점에 이미 값으로 렌더**되므로(`readConfig`→`renderConfigEnvTemplates`, `PROMPTFOO_DISABLE_TEMPLATING`이 아니면), `apiKey: "{{env.OPENAI_API_KEY}}"`처럼 환경변수 참조로 쓴 키도 렌더된 실제 값으로 `evals.config`에 저장된다고 보아야 한다(저장 경로에 일반 정제가 없으므로, 추론; 추적 자격증명만 템플릿 문자열로 보존하는 별도 장치가 있다). 재개·재시도가 저장된 설정으로 다시 실행하는 구조(추론: 사유)와 맞물린다. 반면 `eval_results`의 `provider`는 `sanitizeObject`로, `testCase`·`prompt`는 비밀 필드 마스킹으로, `response`·`gradingResult`·`metadata`는 인증·세션 헤더 정제로 정리된다(eval-records R-21). **따라서 `promptfoo.db`는 설정에 리터럴로 쓴 키가 들어 있을 수 있는 비밀 파일로 다뤄야 한다.** 모델 출력·변수 값·프롬프트 본문에 사용자가 넣은 비밀은 이름·패턴이 걸리는 경우(R-38)를 빼고 정제되지 않는다 | 코드 확인 / 실제 DB 내용은 실행 확인하지 않음 |
| R-38 | 출력(json·yaml·txt·xml·html 머리)의 설정 정제 | `sanitizeConfigForOutput(config)`: 추적 자격증명 정제 후 `basePath`를 빼고 `sanitizeObject(sanitizeUrls=true, 깊이 무제한)`을 돌린 다음 `basePath`를 되돌린다. 규칙: ① 키 이름(소문자화, `-`·`_`·공백·`=` 제거)이 비밀 목록(`password`·`apiKey`·`token`·`secret`·`authorization`·`bearer`·`cookie`·`sessionId`·`privateKey`·AWS 자격증명 등 약 80개)에 있으면 값을 `[REDACTED]`로. `env` 맵 안에서는 `KEY`·`TOKEN`·`SECRET`·`PASSWORD` 등으로 끝나는 변수 이름도 비밀. ② `headers`는 비자격 헤더(`accept`·`content-type`·`user-agent`·일부 `openai-*`)나 안전한 템플릿이 아니면 `[REDACTED]`. ③ 문자열 값이 비밀 모양이면(`sk-`·`sk-ant-`·`sk-proj-` 20자↑, `key-`, `Bearer `/`Basic ` 20자↑, `AKIA…`, `AIza…`, 영숫자·`+/=_-`만 64자↑) `[REDACTED]`. ④ `url`·`apiBaseUrl`·`apiHost` 등은 URL 정제(userinfo는 `***`, 쿼리·프래그먼트의 비밀 파라미터는 `[REDACTED]`, 템플릿 `{{…}}`는 보존). ⑤ 클래스 인스턴스는 `[이름 Instance]`, 함수는 `[Function] 이름`. 정제가 던지면 출력이 실패한다(`throwOnError`). 기본 정제는 **최선 노력**이다: 위 목록·패턴에 안 걸리는 비밀(짧은 임의 토큰, 이름이 일반적인 필드)은 남고, 비밀이 아닌 `config.env` 값도 남는다(문서도 같은 경고). 내부 helper(`sanitizeJsonString`·`redactNestedJsonValue`·`isSecretParameter`·`hasSecretFormSegment`·`isCredentialHeader` 등)는 풀지 않고 C-12의 모듈 단위로 가져온다 | 코드 확인 / helper 내부 미탐색 |
| R-39 | 형식별 비밀 노출 요약 | 행 단위 데이터(`results.results`)는 저장 때 이미 정제된 값(R-37)이 나가고, 출력 때 `PROMPTFOO_STRIP_*`가 추가로 적용된다(R-40). **설정**은 json·yaml·txt·xml에 정제본(R-38)이 들어가고 html에는 `description`만, jsonl·csv·junit.xml에는 싣지 않는다. 최종 프롬프트 전문·변수·모델 출력·grader 이유는 json·yaml·txt·xml(`results`), html(셀), csv(출력·이유·변수), jsonl 행에 **그대로** 들어가므로 사용자 데이터 속 비밀은 걸러지지 않는다(csv는 `PROMPTFOO_STRIP_*`도 받지 않는다, R-40). junit.xml은 어떤 사용자 데이터도 싣지 않는다(R-26). jsonl은 행마다 DB 저장과 같은 정제(`sanitizeResultForJsonlArtifact`)를 거친다. `traces`는 트레이스 저장소가 읽을 때 민감 속성 키를 정제한다 | 코드 확인 |
| R-40 | `PROMPTFOO_STRIP_*` | 평가 설정의 `env:`가 환경변수보다 우선하는 불리언 5개: `PROMPTFOO_STRIP_PROMPT_TEXT`(프롬프트 본문을 `[prompt stripped]`로, 설정의 `prompts`·provider별 `prompts` 선택자 제거), `…_RESPONSE_OUTPUT`(출력을 `[output stripped]`, 테스트의 `providerOutput` 제거), `…_TEST_VARS`(변수를 `{}`), `…_GRADING_RESULT`(`gradingResult`를 `null`), `…_METADATA`(행·응답·테스트 metadata 제거, 원격·재생 경로용 `__promptfoo` 일부만 유지). 효과는 json·yaml·txt·xml·html(표는 `getTable`→`toResultsFile`→`toEvaluateSummary`를 거침)·jsonl 출력과 `export`, CLI 표에 적용되고 **DB에는 영향이 없다**(DB는 평문 그대로). **CLI csv에는 적용되지 않는다**: `streamEvalCsv`가 `EvalResult`의 `response.output`·`testCase.vars`·`gradingResult`를 직접 읽고 strip 호출이 없다(`evalTableUtils.ts`에 해당 호출 없음). 그러므로 `PROMPTFOO_STRIP_*`로 비운 export가 csv로는 샐 수 있다 | 코드 확인 |
| R-41 | CSV 수식 이스케이프 | csv의 문자열 셀(헤더 포함)은 앞쪽 공백·제로폭 문자를 무시하고 첫 글자가 `=`·`@`이거나 숫자가 아닌 `-`·`+`로 시작하면 앞에 `'`를 붙인다(스프레드시트 수식 주입 방어). 유한한 부호 있는 숫자 문자열은 그대로 둔다. `PROMPTFOO_DISABLE_CSV_FORMULA_ESCAPING`이 `1/true/yes/yup/yeppers`면(설정 `env:`가 환경변수보다 우선) 끈다. 이스케이프된 CSV를 다시 읽을 때 `'`는 복원되지 않는다 | 코드 확인 |
| R-42 | 공유 억제와 로컬 저장 | 공유 여부는 `shouldShareResults`가 정한다: 명시적 끄기(`--no-share`, `--share=false`, `PROMPTFOO_DISABLE_SHARING`) > `--share` > 설정 `commandLineOptions.share` > 설정 `sharing` > (로그인했고 `sharing`이 `false`가 아니면 자동 공유). 어느 쪽이든 **로컬 DB 저장·`-o` 출력은 그대로**이고 공유는 저장이 끝난 `Eval`을 올리는 별도 단계다. 로컬 저장을 끄는 것은 `--no-write`뿐이다. `--no-write`와 공유를 같이 주면 안내 메시지 처리만 R-06의 `cmdObj.write` 분기에 따른다(공유 업로드·호스팅은 `hosted-integration` 몫) | 코드 확인 |

- 불변식:
  - 영속된 `Eval`은 평가 시작 전에 `evals` 행이 존재하고, 이후 `eval_results` 행은 완료된 칸마다 단조 증가한다(삭제는 `retry` 성공 후 ERROR 행 정리와 사용자 `delete`뿐).
  - `-o` 출력은 항상 DB(또는 `--no-write`일 때 메모리) 기준 최종 상태를 반영한다. 스트리밍된 jsonl은 최종 재작성 전까지 잠정본이다.
  - 파일 출력(json·yaml·txt·xml·html)의 설정은 정제본이고 DB의 설정은 비정제본이다. 서로 같다고 가정하지 않는다.
- 미결정: 없음.
- 확인 한계: 설치·실행·네트워크를 하지 않았다(순수 읽기). 동시성·강제 종료 후 상태·SQLite 파일 실제 내용·값 없는 `-o`의 동작은 코드 추적으로만 판단했다. drizzle 마이그레이터의 적용 기록 방식, Google Sheets 쓰기(`googleSheets`), OpenAI Evals 변환(`src/importers/openaiEvals`), 서버 라우터 본문(`/api/eval` 목록·삭제)과 서버 쪽 `/api/history` 외 조회, `sanitizer.ts`의 내부 helper 세부(C-16을 모듈 단위로 가져오는 것으로 대체), `tableOutput.html`의 스타일·스크립트(렌더되는 값만 봄), 원본 테스트(파일명 검색도 하지 않음)는 열지 않았다. csv·junit·html 경로에서 레거시 v3 `Eval`이 어떻게 동작하는지는 부분 확인(junit만 분기를 읽음). 이들은 이 스펙의 사용 목적(스킬 평가 기록)에 영향을 주지 않는다고 판단해 범위에서 뺐고, 그 범위에서 구현을 막는 질문은 없다.

### 1.5 필수 코드 참조

라이선스: MIT(`overview.md` 1절). 옮길 때 저작권·허가 문구를 유지한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/util/config/manage.ts:1-37`, `src/database/index.ts:124-152` `getDbPath`·`getDbSignalPath` | 설정 디렉터리 해석 우선순위와 DB·신호 파일 경로, 테스트 러너의 기본 DB 접근 거부 | R-01, R-02 |
| C-02 | `src/database/index.ts:154-239` `configureConnection`·재시도 상수·`isTransientDatabaseLockError`, `:241-371` `serializeTopLevelOperations`, `:373-428` `getDb`, `:430-501` `closeDb` | PRAGMA 값, 직렬화 큐, 잠금 재시도·재연결, 종료 checkpoint | R-03, R-35 |
| C-03 | `src/migrate.ts:49-92` `resolveMigrationsFolder`·`runDbMigrations`, `src/main.ts:53-64` | 마이그레이션 폴더 해석과 시작 시 항상 실행 | R-04 |
| C-04 | `src/database/tables.ts:43-56, 156-192, 205-253, 257-286, 324-430`, `src/database/evalDeletion.ts:20-40` | 태그·연결·blob·데이터셋·트레이스·스팬 테이블 정의, 트레이스 먼저 지우는 순서 | R-05, R-33 |
| C-05 | `src/node/doEval.ts:359-361, 414-520, 813-818, 871-875, 884-1010, 1065-1080, 1174-1179` `doEval` | 쓰기·재개·재시도 분기, 태그 병합, `Eval.create` vs `new Eval`, SIGINT 일시정지, 평가 후 정리·출력 호출 | R-06, R-09~R-11, R-17, R-20 |
| C-06 | `src/evaluator.ts:3665-3695` `filterCompletedResumeSteps`, `:4085-4087`, `:4240-4262`(행 저장 실패 처리와 jsonl 쓰기), `:4722-4735, 4866-4876, 4915-4960, 5575-5616`(열 flush·종료 저장), `:6140-6150`(writer 닫기) | 재개 시 완료 칸 건너뛰기, 행 단위 저장, 열 메트릭 flush 시점 | R-07~R-10 |
| C-07 | `src/models/eval.ts:365-474` `latest`·`findById`·`getMany`, `:513-620`(`create`의 태그·프롬프트·데이터셋 삽입), `:688-727` `save`, `:850-861` `fetchResultsBatched`, `:1644-1657` `delete`, `:1850-1979` `getEvalSummaries` | 조회·생성·저장·삭제 연산 | R-06~R-08, R-12, R-16, R-17, R-33 |
| C-08 | `src/util/database.ts:215-334` `getPromptsWithPredicate`·`readTestCases`, `:364-423` `getEvalFromId`, `:425-485` `deleteEval`·`deleteEvals`·`deleteAllEvals`, `:487-589` `getStandaloneEvals`, `src/util/standaloneEvalCache.ts` | 프롬프트·데이터셋 묶기, 접두 일치, 삭제 범위, 태그·설명 필터와 캐시 키 | R-13~R-17, R-33 |
| C-09 | `src/commands/list.ts:15-142`, `src/commands/show.ts:44-212`, `src/commands/delete.ts:1-78` | 표 열·정렬·옵션, 해석 순서, 삭제 명령 형태 | R-12~R-15, R-33 |
| C-10 | `src/node/retry.ts:134-170, 296-464` `getErrorResultIds`·`deleteErrorResults`·`retryCommand`·`retryWithConfig`, `src/commands/retry.ts:12-46` | 오류 행 재시도와 성공 후 정리 | R-11 |
| C-11 | `src/util/outputFormats.ts:1-20`, `src/types/index.ts:1586-1596, 1609-1618` | 지원 확장자 목록, `.junit.xml` 우선, `OutputFile` 모양 | R-19, R-21 |
| C-12 | `src/util/output.ts:390-457` `createOutputData`, `:535-746` `writeOutput`·`:748-760` `writeMultipleOutputs`(형식 분기, jsonl 임시 파일 교체와 복구), `src/util/exportToFile/writeToFile.ts:1-102` `JsonlFileWriter`, `src/node/evaluatorRuntime.ts:75-83` | 출력 형식 분기·jsonl 스트리밍과 최종 재작성, 병렬 쓰기와 오류 모으기 | R-19~R-23, R-25 |
| C-13 | `src/util/eval/evalTableUtils.ts:62-125, 337-365, 382-430, 452-505, 762-825` | CSV 열 규칙, 상태·이름 있는 점수 서식, 수식 이스케이프, 스트리밍 | R-24, R-41 |
| C-14 | `src/util/junit.ts:171-313` | JUnit 스위트 묶음·이름·실패/오류 표기 | R-26 |
| C-15 | `src/tableOutput.html`(렌더되는 값 목록은 R-23), `src/table.ts:7-47` `generateTable` | HTML 보고서 템플릿과 CLI 표 | R-23, R-28 |
| C-16 | `src/util/sanitizer.ts:144-227` `SECRET_FIELD_NAMES`, `:240-328`, `:360-413` `looksLikeSecret`, `:416-495`(헤더 규칙), `:605-697`, `:792-921` `sanitizeConfigForOutput`, `:1288-1352`, `:1357-1556` `sanitizeObject`, `:1563-1700` `sanitizeUrl`·`sanitizeUrlForLogging`(같은 파일 안의 helper는 모듈째 가져온다) | 출력 설정 정제 규칙 전체 | R-37, R-38 |
| C-17 | `src/models/evalResult.ts:896-985` `getStripFlags`·`sanitizeResultForJsonlArtifact`, `:1077-1136` `createManyFromEvaluateResult` | 출력 투영(`PROMPTFOO_STRIP_*`)과 행 정제, import의 행 삽입 | R-31, R-39, R-40 |
| C-18 | `src/commands/export.ts:107-160`, `src/commands/import.ts:28-100, 224-240, 383-529`, `src/importers/parse.ts:1-71` | export 분기, import 입력 판별·ID 규칙·쓰기 순서 | R-29~R-32 |
| C-19 | `src/util/sharing.ts:30-69` `shouldShareResults` | 공유 결정 우선순위 | R-42 |
| C-20 | `src/database/signal.ts:72-111, 288-349` | 신호 파일 형식과 감시 | R-36 |
| C-21 | `src/util/cliOptions.ts:3-38` `collectKeyValueOption`·`normalizeTagOption` | `--tag k=v` 파싱과 검증 | R-17 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(실행·테스트 열람 없음).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-04 | 환경변수 `PROMPTFOO_CONFIG_DIR=/tmp/x`로 아무 명령 실행 | `/tmp/x`가 생기고 `/tmp/x/promptfoo.db`에 마이그레이션 `0000`~`0025`가 적용됨. `~/.promptfoo`는 건드리지 않음 |
| T-02 | R-06, R-28 | `eval -c cfg.yaml --no-write -o out.json` | DB에 `evals`·`eval_results` 행이 생기지 않는다. 표는 나오고 `out.json`이 만들어지며 안의 `evalId`는 메모리 id다. `eval --no-write --resume`은 "Cannot use --resume with --no-write..."로 실패 |
| T-03 | R-19 | `eval -o out.pdf` / 설정 `outputPath: out.pdf` | 앞은 평가 없이 "Unsupported output file format"으로 거부. 뒤는 평가·저장은 끝나고 출력 단계에서 같은 오류로 실패해 eval은 DB에 남아 있음 |
| T-04 | R-07, R-25 | `-o r.jsonl`로 평가 중 프로세스 강제 종료(칸 7개 완료) | `r.jsonl`에 정제된 행 7줄(스트리밍분), DB에도 7행. `eval --resume`하면 나머지 칸만 돌고 `r.jsonl`은 append로 이어 쓰이다가 끝나면 DB 기준으로 재작성됨 |
| T-05 | R-09, R-10 | Ctrl+C 1회(칸 3개 완료, 2개 진행 중) → `eval --resume <id>` | 일시정지 안내가 `--resume <id>`와 함께 나오고 표·`-o`는 건너뜀. 진행 중이던 2칸은 ERROR 행이 아니라 행 없음. 재개 시 "skipping 3 previously completed cases"이고 5칸+나머지를 실행 |
| T-06 | R-11 | 오류 행 3개인 eval에 `retry <id>`, 재실행 모두 성공 / 재실행 도중 저장 실패 | 성공이면 새 행 3개가 쓰이고 옛 ERROR 행 3개가 삭제되며 열 `metrics`가 재계산됨(jsonl 경로만 재작성). 저장 실패면 "Retry results failed to persist. Existing ERROR rows were preserved." 로 끝나고 옛 행 유지 |
| T-07 | R-29~R-32 | `export eval X -o x.json` → `delete eval X` → `import x.json` → `import x.json` → `import x.json --new-id` → `import x.json --force` | 첫 import는 같은 id `X`로 성공(행 `id`는 새 UUID, 태그·데이터셋 연결 재생성), 둘째는 "already exists" 오류 exit 1, 셋째는 새 id, 넷째는 `X`를 지우고 다시 만듦 |
| T-08 | R-30, R-25 | `eval -o r.jsonl` 결과를 `import r.jsonl` | "File parsed as JSONL but line 1 is not a valid OpenAI Evals row"로 실패(yaml·csv·xml·html도 불가) |
| T-09 | R-37~R-39 | 설정에 provider `config: {apiKey: "sk-ant-…20자↑", baseUrl: "https://u:p@h/x?token=abc"}`, 다른 provider에는 `apiKey: "{{env.MY_KEY}}"`(환경변수에 키가 있음) | `export`/`-o *.json`의 `config`에는 두 `apiKey` 모두 `[REDACTED]`이고 URL은 userinfo가 `***`, `token`이 `[REDACTED]`. DB `evals.config`에는 첫째는 쓴 그대로, 둘째는 렌더된 키 값(추론, R-37). html에는 설정이 없고, csv·jsonl·junit에도 설정이 없음 |
| T-10 | R-41 | 모델 출력이 `=SUM(A1)`, `-5`, `-hello`인 csv 셀 | `'=SUM(A1)`, `-5`(그대로), `'-hello`. `PROMPTFOO_DISABLE_CSV_FORMULA_ESCAPING=true`면 셋 모두 그대로 |
| T-11 | R-26 | provider `A`·`B`가 각각 같은 프롬프트 2개를 3개 테스트로 평가, 한 칸 ASSERT 실패·한 칸 타임아웃 | `testsuite` 4개(`[A] prompt 1`, `[A] prompt 2`, `[B] prompt 1`, `[B] prompt 2`), 각 3 `testcase`. ASSERT 실패 칸은 `<failure type="assertion">`, 타임아웃 칸은 `<error type="error">`. `testsuites` 속성에 `failures=1 errors=1` |
| T-12 | R-33, R-15 | eval 150개가 있고 가장 오래된 id `O`에 대해 `delete O` / `delete eval O` | `delete O`는 "No resource found with ID O"(최근 100개에 없음), `delete eval O`는 성공. 후자는 `eval_results`·연결 행·스팬·트레이스를 지우고 프롬프트·데이터셋·태그 마스터 행과 `blobs/` 파일은 남음 |
| T-13 | R-17, R-16 | `eval --tag skill=v2 --tag model=sonnet` 두 번(설정 `tags: {skill: v1}`) | 두 eval 모두 `config.tags = {skill: "v2", model: "sonnet"}`(CLI가 우선), `tags`에 2행·`evals_to_tags`에 eval당 2행. 서버 `/api/history?tagName=skill&tagValue=v2`는 두 eval의 열 행들을 돌려줌. CLI에는 같은 조회가 없음 |
| T-14 | R-17, R-10 | `eval --resume X --tag a=b` | "Cannot use --tag with --resume. Resumed evaluations keep their original tags." |
| T-15 | R-13, R-14 | SKILL.md 두 버전을 `prompts: file://SKILL.md`로 각각 평가(`raw`가 다름) | `list prompts`에 raw 해시가 다른 두 줄(각 `evals: 1`). 같은 버전을 다시 평가하면 그 줄의 `evals`가 2가 되고 `show prompt <6자>`에 두 eval(Raw score·Pass rate)이 나열됨 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01; `src/mainUtils.ts:42-101` `loadEnvPathOnce`·`setupEnvFilesFromArgv`; `src/util/env.ts:55-57`; `src/main.ts:54-55`; `src/database/index.ts:388-390` | 코드 읽기. 평가 설정의 `env:`가 DB 위치를 못 바꾼다는 것은 `refreshConfigDirectoryPathFromEnv` 호출처가 argv env 로드뿐임을 grep으로 확인(`src/util/env.ts:55`, `mainUtils.ts:56`) |
| R-02 | `src/database/index.ts:150-152`; `src/cache.ts:99`; `src/util/logs.ts:22`; `src/globalConfig/globalConfig.ts:16`; `src/blobs/constants.ts:4`, `src/blobs/filesystemProvider.ts:53`; `src/blobs/extractor.ts:589-592` | 코드 읽기 |
| R-03 | C-02 | 코드 읽기. 재시도·재연결 분기는 주석과 함께 읽었고 libsql 내부 버그 주석(`:260-262`)은 외부 동작이라 검증하지 않음 |
| R-04 | C-03; `drizzle/meta/_journal.json`(idx 0~25); `drizzle/0023…0025`; `drizzle/AGENTS.md`(위치 설명) | 코드 읽기. `drizzle-orm`의 `migrate` 내부는 열지 않음 |
| R-05 | C-04; `src/database/tables.ts:156-170`(`evals_to_prompts` cascade), `:177-192`, `:228-246` | 코드 읽기. cascade 유무는 `.references(..., { onDelete })` 표기로 판단 |
| R-06 | C-05 `:359-361`, `:871-875`; `src/models/eval.ts:476-634`, `:636-663`(생성자 `persisted` 기본 false); `src/commands/eval.ts:158-162`; `src/main.ts:64` | 코드 읽기. `commandLineOptions.write`가 `-c` 설정에서 읽히지 않는다는 것은 `src/node/doEval.ts` 안 `write` 참조 전수 확인(`cmdObj.write`만 사용)이고, 로드 후 병합 코드를 찾지 못한 부정 결과다 |
| R-07 | C-06 `:4240-4262`; `src/node/evaluationStore.ts:25-27`; `src/models/eval.ts:765-790` `addResult` | 코드 읽기. eval-records R-16·R-17·R-26과 같은 코드 |
| R-08 | C-06 `:4722-4735, 4866-4876, 5575-5616`; `src/models/eval.ts:688-727, 1421-1430, 438-443`; `src/node/doEval.ts:1006-1010` | 코드 읽기. flush가 "이전 flush 후 1초 경과 + 다음 행 완료 시점"인 것은 `:4722-4735`·`:4870-4875`로 확인 |
| R-09 | `src/node/doEval.ts:877-930, 996-1004`; `src/evaluator.ts:1985-2005, 4915-4932`; `src/node/doEval.ts:958-965`(pauseSignal 전달) | 코드 읽기. 강제 종료 후 열 메트릭 증분 유실은 flush 구조에서의 추론 |
| R-10 | C-05 `:414-465, 534-556, 601-675, 935-956`; C-06 `:3665-3695`; `src/models/evalResult.ts:1186-1209` `getCompletedIndexPairs`; 재개 시 열 복원은 eval-records R-01의 근거(`src/evaluator.ts:2690-2740`) | 코드 읽기. 메트릭 누락은 "재개가 `metrics`를 재계산하는 코드가 없다"는 부정 확인과 flush 구조의 결합(추론) |
| R-11 | `src/node/doEval.ts:466-520, 967-989`; `src/node/retry.ts:134-170, 232-292, 296-464`; `src/commands/retry.ts` | 코드 읽기. `recalculatePromptMetrics`의 본문(`:171-291`)은 eval-records R-24가 다룬 범위를 따름 |
| R-12 | C-09 `src/commands/list.ts:15-56`; `src/models/eval.ts:448-474`; `src/constants.ts:6` `DEFAULT_QUERY_LIMIT = 100` | 코드 읽기. 문서(`command-line.md`)는 `-n`을 "descending date"로 설명하나 표는 오름차순으로 다시 정렬(차이) |
| R-13 | C-08 `:215-334`; `src/commands/list.ts:58-142` | 코드 읽기 |
| R-14 | `src/commands/show.ts:44-212`; C-08 `:364-423`; `src/models/eval.ts:365-446` | 코드 읽기. id 형식은 eval-records 1.3(`createEvalId`)과 `src/models/eval.ts:99-101` |
| R-15 | `src/commands/show.ts:167-191`; `src/commands/delete.ts:46-60`; `src/util/database.ts:364-423, 425-444` | 코드 읽기(정적 추적, 실행 아님). `show <id>`가 `getEvalFromId`(접두) 뒤 `handleEval(id)`(`findById` 정확 일치)를 부르는 점에서 도출 |
| R-16 | C-08 `:215-334, 487-589`; `src/server/server.ts:203-218`; `src/models/eval.ts:1850-1979`; `src/util/eval/evalTableUtils.ts:681-760`(`comparisonEvalIds`·`mergeComparisonTables`); `src/commands/eval.ts:119-129`(`--filter-failing`) | 코드 읽기. 서버 라우트는 `/api/history` 한 곳만 열어 봄(web-ui 스펙 몫). `LIMIT` 위치는 `src/util/database.ts:514-527`의 조인 후 `.limit` |
| R-17 | `src/commands/eval.ts:80-85`; `src/util/cliOptions.ts:3-38`; `src/node/doEval.ts:94-104, 421-437, 813-818`; `src/models/eval.ts:594-619, 1731-1760`; `src/types/index.ts:149, 1182-1183, 1313-1314`; `grep tagsTable evalsToTagsTable src` | 코드 읽기. 부재 확인은 grep(사용처가 `src/util/database.ts`·`src/models/eval.ts`뿐) |
| R-18 | R-12~R-17의 조회 함수 목록 전수(`list/show/delete/export/import/retry`, `src/util/database.ts`, `src/models/eval.ts`); 스키마 `src/database/tables.ts:58-77` | 부재 확인이라 기본값은 "코드 확인(전수 목록)". 서버·MCP·Node API 쪽에 다른 조회가 있을 수 있으나 범위 밖 |
| R-19 | C-11; `src/commands/eval.ts:143-146, 230-244`; `src/util/config/load.ts:887-893, 1088`; `src/node/doEval.ts:1065-1072` | 코드 읽기. 문서(`outputs.md`)는 `--output a --output b`도 허용하는 것으로 쓰며 `<paths...>`가 반복 사용을 합치는 Commander 동작은 외부 라이브러리 규칙(추론) |
| R-20 | C-05 `:1174-1179`; C-12 `:748-760`; `src/node/doEval.ts:998-1004` | 코드 읽기 |
| R-21 | C-12 `:390-457, 503-533, 584-590`; `src/models/eval.ts:1538-1576` | 코드 읽기. 문서 `outputs.md`의 JSON 예(`version/timestamp/results{prompts,providers,outputs,stats}`)와 필드 표는 현재 구현의 `OutputFile`과 다르다(차이) |
| R-22 | C-12 `:707-745` | 코드 읽기 |
| R-23 | C-12 `:591-645`; `src/tableOutput.html:6, 659-667, 674-694, 736-793, 828-920`(렌더되는 값 전수 grep) | 코드 읽기. 문서의 "HTML 출력에도 config 포함" 경고와 달리 템플릿은 `config.description`만 쓴다(차이). 템플릿 스타일·스크립트는 미열람 |
| R-24 | C-13; `src/util/exportToFile/index.ts:1-70`; C-12 `:570-583` | 코드 읽기. 문서의 CSV 열 목록(변수·프롬프트·출력·통과/실패·지연·토큰)과 달리 구현에 지연·비용·토큰 열은 없다(차이) |
| R-25 | C-12 `:646-706, 142-280`; `src/node/evaluatorRuntime.ts:75-83`; `src/util/exportToFile/writeToFile.ts`; C-06 `:4085-4087, 4256-4261, 6140-6150`; `src/node/doEval.ts:1067-1076` | 코드 읽기. 큰 평가에서 메모리가 적다는 것은 `fetchResultsBatched`(100건 배치) 사용에서의 도출 |
| R-26 | C-14 | 코드 읽기 |
| R-27 | C-12 `:541-556`; `src/commands/eval.ts:230-244` | 코드 읽기. 시트 쓰기(`writeCsvToGoogleSheet`)는 미열람 |
| R-28 | C-05 `:1035-1063`; `src/table.ts:7-47`; `src/commands/eval.ts:147-149` | 코드 읽기 |
| R-29 | C-18 `src/commands/export.ts:107-160`; C-12 `:535-566` | 코드 읽기. `-o` 값 없음 처리는 코드 추적(실행 아님) |
| R-30 | C-18 `src/importers/parse.ts:1-71`; `src/commands/import.ts:28-124, 431-466` | 코드 읽기. 문서(`command-line.md`)의 "tags, dataset links ... not reconstructed"와 달리 v3 경로는 `Eval.create`로 재생성한다(차이, R-32) |
| R-31 | C-18 `src/commands/import.ts:176-240, 383-529`; `src/models/eval.ts:513-620`; C-17 `:1077-1136` | 코드 읽기. 트랜잭션 경계는 `Eval.create`(`:513`)와 `createManyFromEvaluateResult`(`:1095`)가 각각 독립임에서 확인 |
| R-32 | R-30·R-31의 근거 + C-11 `:1586-1596`; `site/docs/usage/command-line.md:491-502` | 코드 읽기와 문서 대조 |
| R-33 | C-08 `:425-485`; C-07 `:1644-1657`; `src/commands/delete.ts:15-78`; `src/models/evalMutation.ts:33-53` | 코드 읽기 |
| R-34 | `grep -rniE "retention|ttl|prune|…" src`; `src/tracing/store.ts:295-336`, `src/tracing/evaluatorTracing.ts:73-80`; `src/blobs/`(삭제 함수 없음); `src/database/tables.ts:228-246`(cascade) | 부정 확인(grep). 평가 기록 자동 삭제가 서버 쪽 어딘가에 숨어 있을 가능성은 `src/server/routes/eval.ts:857-896`의 DELETE 라우트 확인으로 좁혔으나 서버 전체는 미탐색 |
| R-35 | C-02; `src/models/eval.ts:688-727`(`json_set`); `src/database/tables.ts:79-153`(유일 제약 없음, eval-records R-03); `src/database/signal.ts:62-69`(주석) | 코드 읽기. 경합 결과는 추론 |
| R-36 | C-20; `src/models/evalMutation.ts:33-53` | 코드 읽기 |
| R-37 | `src/models/eval.ts:521, 696`; `src/util/sanitizer.ts:605-697`; `src/models/evalResult.ts:46-52, 388-442, 636-690, 1077-1136`; `src/node/retry.ts:57-96`(저장된 설정으로 재해석); `src/util/config/load.ts:300-345, 385-395`(`renderConfigEnvTemplates`가 설정 로드 때 `{{env.X}}`를 값으로 렌더); `src/util/render.ts:40-80` | 코드 읽기. 설정이 정제되지 않은 채 저장된다는 것은 `Eval.create`·`save`가 `sanitizeTracingConfigForPersistence`만 호출하는 것과 `src/util/config/load.ts`·`doEval.ts`에 일반 정제가 없다는 grep의 결합이며 실제 DB 내용은 열어 보지 않았다 |
| R-38 | C-16 | 코드 읽기. 비밀 목록 개수(약 80)는 `SECRET_FIELD_NAMES` 항목 수 개수 |
| R-39 | R-21~R-26의 근거; `src/models/evalResult.ts:918-985`; `src/util/output.ts:441` | 코드 읽기 |
| R-40 | C-17 `:896-985`; `src/util/output.ts:417-419`; `src/util/sanitizer.ts:803-891`; `src/models/eval.ts:1552-1565` | 코드 읽기. csv는 `streamEvalCsv`(`:762-825`, `batchToStreamRows` `:282-323`)가 `EvalResult`를 직접 읽는 것과 `evalTableUtils.ts`에 `getStripFlags` 호출이 없다는 grep으로 확인. html·CLI 표는 `getTable`(`src/models/eval.ts:1623-1642`, `toResultsFile`)을 거쳐 투영된다 |
| R-41 | C-13 `:452-505`; `src/envars.ts:37` | 코드 읽기 |
| R-42 | C-19; `src/node/doEval.ts:1012-1033, 1106-1127` | 코드 읽기. 업로드 구현(`src/share.ts`)은 범위 밖 |
| T-01~T-15 | 관련 R-ID의 근거 | 구현을 읽고 손으로 도출. 실행하지 않았다 |

**문서·주석과 구현의 차이**

- `site/docs/configuration/outputs.md`의 JSON 구조 예·"Structured Output Fields" 표(`timestamp`/`prompts`/`providers`/`tests`/`outputs`/`results`/`stats`)는 현재 `OutputFile`(`evalId`, `results`, `config`, `shareableUrl`, `metadata` …)과 다르다. 구현을 사실로 썼다(R-21).
- 같은 문서의 CSV 열 목록에 Latency·Token usage가 있으나 `buildCsvHeaders`에는 없다(R-24). 같은 문서의 "html도 config 포함" 경고와 달리 HTML 템플릿은 `config.description`만 렌더한다(R-23). `txt`는 문서에서 구조화 출력으로 나열되며 실제로 YAML 덤프다(R-21).
- `site/docs/usage/command-line.md`는 `list`의 `-n`을 "descending date"로 쓰나 `list evals` 표는 오름차순이다(R-12). `export eval`을 "JSON"으로 설명하나 `-o` 확장자가 형식을 정한다(R-29). `import`가 태그·데이터셋 연결을 "재구성하지 않는다"고 쓰나 v3 경로는 설정에서 재생성한다(R-32).
- `delete`·`show`의 "ID" 설명은 접두 일치를 암시하나 eval에 대해서는 접두로 끝까지 가지 못한다(R-15).

### 2.2 코드 읽는 순서

1. `src/node/doEval.ts`의 `doEval`(`:276-`): 쓰기·재개·재시도 분기 → `Eval.create`(`src/models/eval.ts:476`) → `evaluate`(`src/evaluator.ts`)의 행 저장(`:4240`) → 평가 후 표·공유·`writeMultipleOutputs`.
2. `src/util/output.ts`: `createOutputData` → `writeOutput` 형식 분기 → jsonl 보조 함수들(`:58-280`).
3. `src/commands/{list,show,delete,export,import}.ts`와 `src/util/database.ts`(묶기·삭제·태그 필터).
4. `src/database/index.ts`(연결·잠금) → `src/migrate.ts` → `drizzle/AGENTS.md`.
5. 비밀 경계: `src/util/sanitizer.ts`의 `sanitizeConfigForOutput` → `sanitizePlainObject` → `src/models/evalResult.ts`의 저장·출력 투영.

원본의 전략: 영속화는 "평가 시작 시 헤더 행 + 칸마다 행 + 열 집계 주기적 덮어쓰기"로 중단 허용(재개)을 만들고, 출력은 저장이 끝난 상태를 읽어 파일을 만든다. jsonl만 평가 중에도 스트리밍하고 끝에 DB 기준으로 정리한다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다.

## 적용 메모

사용 목적: 내 스킬(SKILL.md)을 여러 모델에 평가하고, 결과를 누적 보관해 스킬 버전·모델별로 꺼내 비교하는 기록 환경. 아래는 원본과 다르게 할 점이며, 원본에서 비어 있는 부분(R-16~R-18)을 채우는 항목이다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-17, R-18 | 평가 실행마다 `skill`, `skill_version`, `model`, `suite` 같은 라벨을 **전용 필드(컬럼)**로 저장하고, 조회·필터·집계를 우리가 구현한다. 원본의 `--tag k=v`는 라벨 입력 수단으로만 받거나 대체한다 | 원본에서 라벨은 `tags` 문자열 맵이고 CLI에는 이를 읽거나 거르는 명령이 없으며(서버 `/api/history`가 단일 태그 정확 일치만 지원) 모델은 `provider` 문자열 속에만 있다 | 기록 행 = (실행 id, 시각, 스킬·버전, 모델, 케이스 안정 id, repeat). T-13을 라벨 필터 조회 사례로 대체 |
| R-12, R-14, R-16 | 시간 정렬은 `createdAt`(ms)만 신뢰하고, eval id 문자열 정렬·접두 일치·최근 100개 제한에 기대지 않는다 | `list evals`는 100개 기본 제한, `show prompt`의 10개는 id 문자열 정렬이라 시간순이 아니며, 접두 해석은 eval에서 끝까지 가지 못한다(R-15) | 조회 인터페이스에 시간 범위·페이지·정확 id만 둔다 |
| R-16 | 버전 간 비교 키를 프롬프트 raw 해시(SKILL.md를 prompt로 넣는 경우에만 성립)나 `datasetId`에 의존하지 않고, 스킬 버전 라벨과 안정적인 케이스 id로 한다 | `datasetId`는 `tests`가 파일 참조면 내용이 아니라 참조 문자열의 해시이고, 에이전트 provider로 평가할 때 SKILL.md는 prompt가 아니라 `working_dir`에 있어 prompt 해시에 나타나지 않는다 | 같은 케이스 집합의 반복 실행을 한 키로 묶는 모델 |
| R-37, R-38 | 저장 시점에 설정을 정제하고(환경변수 참조는 렌더하지 않은 템플릿 문자열로 보존), 원 설정이 필요하면 별도 비밀 저장소에 둔다. 출력 정제는 이름·패턴 외에 "값이 실제로 쓰인 env 값"을 마스킹하는 쪽으로 보강한다 | 원본 DB는 설정을 평문(env 참조도 렌더된 값)으로 저장해(재개·재시도를 위해) DB 파일이 비밀 파일이 되고, 출력 정제는 최선 노력이다 | 저장된 설정으로 재실행하는 흐름이 있다면 키 주입을 실행 시점에 분리 |
| R-32 | 왕복 형식을 정제되지 않은 자체 아카이브(또는 정제 전 DB 덤프)로 두고, export는 정제본을 별도로 만든다 | 원본 JSON export는 정제본을 그대로 가져와 `config`의 키를 복원할 수 없고, 행 `id`·`tokenUsage`가 바뀐다 | 가져오기 후에도 같은 행 id·토큰이 유지되는 사례를 새로 정의 |
| R-35, R-07, R-10 | 같은 실행 id에 대한 쓰기 주체를 하나로 제한하고, 행 저장 후 열 집계는 행에서 읽을 때 계산한다 | 원본은 프로세스 간 eval 잠금이 없고 `eval_results`에 유일 제약이 없으며 열 메트릭은 증분 flush라 강제 종료 후 어긋날 수 있다 | `(run_id, case_id, model)` 유일 제약과 재계산 가능한 집계 |
