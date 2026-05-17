# RTK 실행 방법과 Gradle 테스트 필터링 흐름

기준 문서: `analysis-reports/rtk/overview.md`  
분석 대상 저장소: `rtk/`

이 문서는 기존 overview에서 이어지는 추가 질문 2개에 대한 정리다.

1. RTK를 실제로 어떻게 실행하고, 다른 프로젝트에서 어떻게 쓰는가?
2. Java/Gradle 테스트 실행 시 RTK가 어떤 코드로 어떤 출력을 필터링해서 보여주는가?

## 1. RTK는 어떻게 실행하는가?

RTK는 Rust로 작성된 단일 CLI 바이너리다. 핵심 사용 방식은 "원래 실행하려던 명령 앞에 `rtk`를 붙여서 실행"하는 것이다.

예를 들면 다음과 같다.

```bash
rtk git status
rtk cargo test
rtk pytest
rtk go test
rtk gradlew test
rtk gradlew :app:testDebugUnitTest
rtk test ./gradlew test
```

다만 Gradle은 `rtk test ./gradlew test`보다 `rtk gradlew test`를 우선해서 이해하는 것이 좋다. `rtk gradlew ...`는 Gradle 전용 Rust 모듈을 타고, 테스트/빌드/lint/dependencies 작업을 구분해 더 구체적으로 필터링한다. `rtk test <cmd>`는 임의 테스트 명령을 감싸는 범용 wrapper라서 Gradle 전용 필터만큼 정교하지 않다.

## 2. 다른 프로젝트에서 사용하려면?

다른 프로젝트에서 RTK 기능을 쓰려면, 분석 대상 저장소의 코드를 복사하는 것이 아니라 RTK 바이너리를 설치해서 해당 프로젝트 디렉터리에서 실행하면 된다.

설치 경로는 README 기준으로 다음 방식이 있다.

```bash
# macOS 권장
brew install rtk

# Linux/macOS quick install
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh

# Cargo로 설치할 경우 crates.io 이름 충돌 주의. README는 git 설치를 권장한다.
cargo install --git https://github.com/rtk-ai/rtk
```

설치 확인:

```bash
rtk --version
rtk gain
```

다른 프로젝트에서 직접 쓰는 방식:

```bash
cd /path/to/your-project

rtk git status
rtk cargo test
rtk gradlew test
rtk gradlew :app:testDebugUnitTest
rtk gradlew lint
rtk gradlew dependencies
```

Gradle의 경우 `rtk gradlew ...`를 실행하면 내부에서 현재 디렉터리의 Gradle wrapper를 우선 사용한다.

- Unix 계열: 현재 디렉터리에 `./gradlew`가 있으면 `./gradlew` 실행
- Windows: 현재 디렉터리에 `.\\gradlew.bat`이 있으면 `.\\gradlew.bat` 실행
- wrapper가 없으면 시스템의 `gradle` 실행

근거 코드는 `rtk/src/cmds/jvm/gradlew_cmd.rs`의 `gradlew_binary()`와 `new_gradle_command()`다.

## 3. AI 도구에 자동으로 붙여 쓰는 방식

RTK는 사용자가 매번 `rtk`를 직접 붙이지 않아도 되도록 agent hook/plugin 설치를 제공한다.

README 기준 예시는 다음과 같다.

```bash
rtk init -g                     # Claude Code / Copilot 기본
rtk init -g --gemini            # Gemini CLI
rtk init -g --codex             # Codex
rtk init -g --agent cursor      # Cursor
rtk init --agent windsurf       # Windsurf
rtk init --agent cline          # Cline / Roo Code
rtk init --agent kilocode       # Kilo Code
rtk init --agent antigravity    # Google Antigravity
rtk init --agent hermes         # Hermes
rtk init --show                 # 설치 상태 확인
```

hook 기반 도구에서는 사용자가 다음처럼 일반 명령을 입력해도:

```bash
./gradlew test
gradle build
git status
```

RTK의 rewrite 규칙이 가능한 명령을 다음 형태로 바꾼다.

```bash
rtk gradlew test
rtk gradlew build
rtk git status
```

Gradle rewrite 근거는 `rtk/src/discover/rules.rs`의 Gradle `RtkRule`이다. 이 규칙은 `./gradlew`, `gradlew.bat`, `gradlew`, `gradle`을 `rtk gradlew`로 매핑한다. `rtk/src/discover/registry.rs`에는 `./gradlew assembleDebug`, `gradlew build`, `gradlew.bat clean`, `gradle build`가 모두 `rtk gradlew ...`로 분류/재작성되는 테스트가 있다.

## 4. 이 저장소를 개발용으로 직접 실행하는 방법

RTK 저장소 자체를 clone해서 로컬에서 실행하려면 Rust/Cargo 기준으로 실행하면 된다.

```bash
cd rtk

# 개발 중 바로 실행
cargo run -- gradlew test
cargo run -- git status
cargo run -- verify --filter gradle

# 릴리즈 빌드
cargo build --release
./target/release/rtk --version
./target/release/rtk gradlew test

# 현재 checkout을 설치해서 PATH에서 사용
cargo install --path . --force
rtk --version
```

RTK 자체 테스트는 일반 Rust 프로젝트처럼 실행한다.

```bash
cd rtk
cargo test

# Gradle wrapper 필터 관련 테스트만 좁혀서 보고 싶을 때
cargo test gradlew_cmd
```

## 5. Gradle 테스트 명령은 어떤 코드로 라우팅되는가?

`rtk gradlew test` 같은 명령은 다음 흐름을 탄다.

1. `rtk/src/main.rs`의 clap `Commands::Gradlew`가 `rtk gradlew ...`를 명령으로 인식한다.
2. `run_cli()`의 match 분기에서 `Commands::Gradlew { args } => gradlew_cmd::run(&args, cli.verbose)`로 위임한다.
3. 실제 구현은 `rtk/src/cmds/jvm/gradlew_cmd.rs`에 있다.

중요한 점은 `rtk gradlew ...`는 `src/filters/gradle.toml`만으로 처리되는 것이 아니라, 전용 Rust 모듈인 `gradlew_cmd.rs`를 탄다는 것이다.

`gradlew_cmd.rs`의 핵심 함수:

- `detect_task(args)`: Gradle task 종류를 판별한다.
- `gradlew_binary()`: `./gradlew`, `.\\gradlew.bat`, `gradle` 중 실제 실행 파일을 고른다.
- `new_gradle_command(args)`: Gradle 실행 `Command`를 만든다.
- `run(args, verbose)`: task 종류에 따라 build/test/connected test/lint/dependencies/passthrough 경로로 분기한다.
- `filter_test(output)`: Gradle unit test 출력을 줄이는 핵심 필터다.
- `filter_connected(output)`: Android connected test 출력을 1차로 줄인 뒤 `filter_test()`에 넘긴다.

## 6. Gradle task 판별 방식

`detect_task(args)`는 인자 중 flag가 아니고 `clean`도 아닌 마지막 task를 기준으로 판단한다.

예:

```bash
rtk gradlew clean assembleDebug
```

이 경우 `clean`은 제외하고 마지막 task인 `assembleDebug`를 보고 `Build`로 판단한다.

판별 규칙은 대략 다음과 같다.

| Gradle task 형태 | RTK 내부 분류 |
|---|---|
| `connected...` | `ConnectedTest` |
| `test...`, `:app:test...`, `check` | `Test` |
| `assemble...`, `build`, `bundle...`, `install...`, `clean` 단독 | `Build` |
| `lint`, `ktlint...`, `detekt...` | `Lint` |
| `dependencies`, `:app:dependencies` | `Dependencies` |
| 그 외 예: `signingReport` | `Other` -> passthrough |

또한 다음 플래그가 있으면 사용자가 전체 로그를 원한다고 보고 필터링하지 않고 원본 passthrough로 실행한다.

```text
--stacktrace
--info
--debug
--full-stacktrace
```

## 7. Gradle 테스트 필터링 흐름

Gradle 테스트로 판별되면 `run()`에서 다음 코드 경로를 탄다.

```text
GradlewTask::Test
-> runner::run_filtered(...)
-> filter_test(raw_output)
-> print_with_hint(filtered, raw, "gradlew_test", exit_code)
-> tracking 저장
```

근거:

- `rtk/src/cmds/jvm/gradlew_cmd.rs`: `GradlewTask::Test` 분기에서 `runner::run_filtered(..., filter_test, RunOptions::with_tee("gradlew_test"))` 호출
- `rtk/src/core/runner.rs`: `run_filtered()`가 외부 명령의 stdout/stderr를 캡처하고 필터 함수를 적용한 뒤 출력
- `rtk/src/core/tee.rs`: 실패했거나 설정상 tee 조건을 만족하면 원본 로그를 파일로 저장하고 `[full output: ...]` 힌트를 출력
- `rtk/src/core/tracking.rs`: raw/filtered 출력량과 실행 정보를 tracking DB에 저장

## 8. `filter_test()`가 남기는 것과 버리는 것

`filter_test(output)`는 Gradle unit test 출력을 다음 기준으로 줄인다.

버리는 것:

- `> Task :...` 형태의 task 진행 라인
- `* Try:`, `> Run with --stacktrace`, `> Get more help at ...` 같은 Gradle 안내 섹션
- `... PASSED`, `... SKIPPED` 테스트 케이스 라인
- JUnit/Gradle/reflection framework stack frame
  - `at org.junit.`
  - `at junit.`
  - `at java.lang.reflect.`
  - `at sun.reflect.`
  - `at org.gradle.`

남기는 것:

- 실패 테스트 라인: `... FAILED`
- 예외 타입과 메시지: `java...`, `kotlin...`으로 시작하는 라인
- 사용자 코드 stack frame: framework frame이 아닌 첫 `at ...` 라인
- 요약 라인:
  - `BUILD SUCCESSFUL ...`
  - `BUILD FAILED ...`
  - `N actionable tasks ...`
  - `N tests completed, M failed`
  - `There were failing tests...`
  - `See the report at: ...`

즉, 목적은 "성공한 테스트 목록 전체"를 보여주는 것이 아니라, LLM이나 개발자가 바로 봐야 하는 실패 테스트명, 실패 원인, 사용자 코드 위치, 전체 테스트 요약만 보여주는 것이다.

## 9. 예시: 성공한 Gradle 테스트 출력

입력 fixture: `rtk/tests/fixtures/gradlew_test_raw.txt`

원본에는 다음 같은 개별 성공 테스트가 포함된다.

```text
com.example.myapp.CalculatorTest > testAddition PASSED
com.example.myapp.CalculatorTest > testSubtraction PASSED
com.example.myapp.CalculatorTest > testMultiplication PASSED
...
6 tests completed, 0 failed
BUILD SUCCESSFUL in 18s
```

필터 후에는 `PASSED` 라인이 제거되고, 요약 중심으로 남는다.

```text
6 tests completed, 0 failed
BUILD SUCCESSFUL in 18s
4 actionable tasks: 1 executed, 3 up-to-date
```

만약 Gradle 기본 설정 때문에 개별 테스트 로그가 거의 없고 `BUILD SUCCESSFUL`만 있는 경우에도 빈 출력이 되지 않도록 `ok ✓ (no test output — add testLogging to build.gradle for details)` 같은 메시지를 반환하는 fallback이 있다.

## 10. 예시: 실패한 Gradle 테스트 출력

입력 fixture: `rtk/tests/fixtures/gradlew_test_failed_raw.txt`

원본에는 성공/실패 테스트가 섞여 있고 JUnit framework frame도 포함된다.

```text
com.example.myapp.CalculatorTest > testSubtraction FAILED
    java.lang.AssertionError: expected:<3> but was:<-1>
        at org.junit.Assert.fail(Assert.java:89)
        at org.junit.Assert.assertEquals(Assert.java:197)
        at com.example.myapp.CalculatorTest.testSubtraction(CalculatorTest.kt:25)
...
5 tests completed, 2 failed
BUILD FAILED in 22s
```

필터 후에는 성공 테스트와 JUnit 내부 frame은 빠지고, 실패와 사용자 코드 위치 중심으로 남는다.

```text
com.example.myapp.CalculatorTest > testSubtraction FAILED
    java.lang.AssertionError: expected:<3> but was:<-1>
        at com.example.myapp.CalculatorTest.testSubtraction(CalculatorTest.kt:25)
com.example.myapp.MainViewModelTest > loadDataError FAILED
    kotlin.NotImplementedError: An operation is not implemented: TODO
        at com.example.myapp.MainViewModelTest.loadDataError(MainViewModelTest.kt:45)
5 tests completed, 2 failed
There were failing tests. See the report at: file:///Users/user/MyApp/app/build/reports/tests/testDebugUnitTest/index.html
BUILD FAILED in 22s
4 actionable tasks: 1 executed, 3 up-to-date
```

실패 시 원본이 충분히 크고 tee 설정이 켜져 있으면 다음 같은 힌트도 함께 붙을 수 있다.

```text
[full output: ~/.local/share/rtk/tee/<timestamp>_gradlew_test.log]
```

이 힌트는 축약 출력으로 부족할 때 원본 로그를 다시 확인하기 위한 경로다.

## 11. `src/filters/gradle.toml`은 무엇인가?

`rtk/src/filters/gradle.toml`도 Gradle 관련 코드지만, `rtk gradlew ...` 전용 Rust 모듈과 역할이 다르다.

이 TOML 필터는 선언형 fallback 필터다.

주요 설정:

```toml
[filters.gradle]
match_command = "^(gradle|gradlew|\\./)gradlew?\\b"
strip_ansi = true
strip_lines_matching = [
  "^\\s*$",
  "^> Configuring project",
  "^> Resolving dependencies",
  "^> Transform ",
  "^Download(ing)?\\s+http",
  "^> Task :.*UP-TO-DATE$",
  "^> Task :.*NO-SOURCE$",
  "^> Task :.*FROM-CACHE$",
  "^Starting a Gradle Daemon",
  "^Daemon will be stopped",
]
truncate_lines_at = 150
max_lines = 50
on_empty = "gradle: ok"
```

이 필터는 다음 일을 한다.

- ANSI 색상 제거
- 빈 줄, 설정/다운로드/UP-TO-DATE/NO-SOURCE/FROM-CACHE 같은 noise 제거
- 각 줄을 150자로 자름
- 전체를 50줄로 제한
- 남는 출력이 없으면 `gradle: ok` 출력

하지만 이 TOML 필터는 실패 stack trace에서 JUnit frame을 제거하고 사용자 코드 frame만 남기는 식의 Gradle 테스트 전용 의미 분석은 하지 않는다. 그런 정교한 처리는 `src/cmds/jvm/gradlew_cmd.rs`의 `filter_test()`가 담당한다.

## 12. fallback TOML 필터는 언제 쓰이는가?

`rtk/src/main.rs`의 `run_fallback()`은 clap이 RTK 명령으로 인식하지 못한 입력을 받았을 때 동작한다.

흐름은 다음과 같다.

```text
rtk <알 수 없는 명령>
-> clap parse 실패
-> run_fallback()
-> core::toml_filter::find_matching_filter()
-> 외부 명령 실행
-> core::toml_filter::apply_filter()
-> 필터된 출력 표시
```

예를 들어 `rtk ./gradlew build`나 `rtk gradle build`처럼 `gradlew` 전용 subcommand가 아닌 형태로 들어오면 fallback TOML 필터가 매칭될 수 있다. 반면 `rtk gradlew build`, `rtk gradlew test`는 clap이 `Commands::Gradlew`로 인식하므로 전용 Rust 모듈을 탄다.

## 13. 관련 파일 요약

| 파일 | 역할 |
|---|---|
| `rtk/README.md` | 설치, quick start, agent별 init, 주요 사용 예시 |
| `rtk/src/main.rs` | clap 명령 정의, `Commands::Gradlew`, fallback TOML 경로 |
| `rtk/src/cmds/jvm/gradlew_cmd.rs` | Gradle wrapper 전용 실행/필터링 구현 |
| `rtk/src/core/runner.rs` | 외부 명령 실행, raw 출력 캡처, 필터 적용, 출력/추적 공통 처리 |
| `rtk/src/core/tee.rs` | 실패/긴 출력의 원본 로그 저장과 `[full output: ...]` 힌트 |
| `rtk/src/core/toml_filter.rs` | TOML 필터 로딩/컴파일/적용 engine |
| `rtk/src/filters/gradle.toml` | Gradle fallback 선언형 필터 |
| `rtk/src/discover/rules.rs` | `./gradlew`, `gradle` 등을 `rtk gradlew`로 rewrite하는 규칙 |
| `rtk/src/discover/registry.rs` | rewrite/classification 테스트와 registry 동작 |
| `rtk/tests/fixtures/gradlew_test_raw.txt` | Gradle 테스트 성공 fixture |
| `rtk/tests/fixtures/gradlew_test_failed_raw.txt` | Gradle 테스트 실패 fixture |

## 14. 결론

다른 프로젝트에서 쓰는 가장 일반적인 방법은 다음 두 가지다.

```bash
# 직접 실행
cd /path/to/project
rtk gradlew test
rtk gradlew :app:testDebugUnitTest

# AI 도구에 자동 적용
rtk init -g --codex   # 사용하는 agent에 맞게 선택
rtk init --show
```

Gradle 테스트 필터링의 핵심은 `src/cmds/jvm/gradlew_cmd.rs`다. `detect_task()`가 `test`, `check`, `:app:testDebugUnitTest` 같은 task를 테스트로 분류하고, `filter_test()`가 성공 테스트/Gradle noise/framework stack frame을 제거한 뒤 실패 테스트, 예외 메시지, 사용자 코드 위치, 요약만 남긴다.
