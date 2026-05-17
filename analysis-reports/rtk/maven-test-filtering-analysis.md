# RTK Gradle 테스트 필터링과 Maven 적용 가능성 분석

분석 대상 저장소: `rtk/`  
관련 기존 보고서: `analysis-reports/rtk/overview.md`, `analysis-reports/rtk/usage-and-gradle-filtering.md`

## 1. 결론

현재 RTK에는 Gradle 테스트 출력처럼 Maven 테스트 출력도 전용으로 줄여 주는 기능은 없다.

정확히는 다음 상태다.

- `rtk gradlew test`: 전용 Rust 구현이 있고, Gradle 테스트 실패/요약 중심으로 출력이 필터링된다.
- `rtk test mvn test`: 실행은 가능하지만 Maven 전용이 아니라 범용 테스트 wrapper다. Maven/Surefire/Failsafe 출력 구조를 해석하지 못한다.
- `rtk mvn test`: 현재 built-in TOML 필터와 rewrite 규칙 기준으로는 테스트 필터링이 적용되지 않는다. fallback passthrough로 원본이 그대로 나갈 가능성이 높다.
- `rtk mvn compile`, `rtk mvn package`, `rtk mvn clean`, `rtk mvn install`: `src/filters/mvn-build.toml`의 선언형 필터 대상이다.

따라서 RTK 프로젝트를 직접 수정하지 않고 Maven 테스트에도 비슷한 효과를 내고 싶다면, 별도 shell script가 `mvn test` 또는 `mvn verify`를 실행해 raw output을 캡처한 뒤 Surefire/Failsafe 패턴을 필터링하는 방식이 가장 현실적이다.

## 2. Gradle 테스트는 어떤 경로로 필터링되는가

`rtk gradlew test`의 실행 흐름은 다음과 같다.

```text
src/main.rs
  Commands::Gradlew { args }
    -> src/cmds/jvm/gradlew_cmd.rs::run(args, verbose)
      -> detect_task(args) == GradlewTask::Test
        -> core::runner::run_filtered(..., filter_test, RunOptions::with_tee("gradlew_test"))
          -> 외부 gradle/gradlew 실행
          -> raw stdout/stderr 캡처
          -> filter_test(raw)
          -> print_with_hint(filtered, raw, "gradlew_test", exit_code)
          -> tracking 저장
```

핵심 근거:

- `rtk/src/main.rs`: `Commands::Gradlew`와 `Commands::Gradlew { args } => gradlew_cmd::run(...)`
- `rtk/src/cmds/jvm/gradlew_cmd.rs`: `detect_task()`, `run()`, `filter_test()`, `filter_connected()`
- `rtk/src/core/runner.rs`: `run_filtered()`, `print_with_hint()`
- `rtk/src/core/tee.rs`: 실패 시 raw log 저장 hint
- `rtk/tests/fixtures/gradlew_test_raw.txt`, `rtk/tests/fixtures/gradlew_test_failed_raw.txt`

## 3. Gradle 테스트 필터가 남기는 정보

`filter_test()`는 원본 출력에서 다음 정보를 남긴다.

- 실패 테스트명: `... FAILED`
- 예외 타입과 메시지: `java...`, `kotlin...`으로 시작하는 라인
- 사용자 코드 stack frame: `at ...` 중 JUnit/Gradle/reflection frame이 아닌 첫 frame
- 테스트 요약: `N tests completed, M failed`
- report path: `See the report at: ...`
- build 결과: `BUILD SUCCESSFUL ...`, `BUILD FAILED ...`
- task 요약: `N actionable tasks ...`

반대로 다음은 제거한다.

- `> Task :...` 진행 라인
- Gradle 안내 섹션: `* Try:`, `> Run with --stacktrace`, `> Get more help at ...`
- 성공/스킵 테스트 라인: `... PASSED`, `... SKIPPED`
- framework stack frame:
  - `at org.junit.`
  - `at junit.`
  - `at java.lang.reflect.`
  - `at sun.reflect.`
  - `at org.gradle.`

즉 Gradle 필터의 목표는 "전체 테스트 로그"가 아니라 "실패 원인, 실패 위치, 전체 요약"만 남기는 것이다.

## 4. Maven 쪽 현재 지원 상태

### 4.1 Maven 전용 CLI는 없다

`src/main.rs`의 clap subcommand 목록에는 `Gradlew`는 있지만 `Mvn`은 없다. 따라서 `rtk mvn ...`은 전용 Rust adapter를 타지 않는다.

근거:

- `rtk/src/main.rs`에 `#[command(name = "gradlew")] Gradlew { ... }` 존재
- `rtk/src/main.rs`, `rtk/src/cmds` 검색 결과 `Mvn` command/adapter 없음

### 4.2 Maven build용 TOML 필터는 있다

`rtk/src/filters/mvn-build.toml`은 존재한다.

대상 command:

```toml
match_command = "^mvn\\s+(compile|package|clean|install)\\b"
```

따라서 `mvn test`는 이 필터 대상이 아니다. 이 필터는 Maven build noise를 줄이는 목적이며, Surefire/Failsafe 테스트 실패 구조를 분석하지 않는다.

### 4.3 rewrite 규칙도 test를 포함하지 않는다

`rtk/src/discover/rules.rs`의 Maven 규칙:

```rust
pattern: r"^mvn\s+(compile|package|clean|install)\b",
rtk_cmd: "rtk mvn",
rewrite_prefixes: &["mvn"],
category: "Build",
```

여기에도 `test`, `verify`는 없다.

### 4.4 `rtk test mvn test`는 대체재로 약하다

`rtk test <cmd>`는 `src/cmds/rust/runner.rs::run_test()`를 사용한다. 내부 `extract_test_summary()`는 다음 도구만 명시적으로 감지한다.

- `cargo test`
- `pytest`
- `jest` / `npm test` / `yarn test`
- `go test`

Maven은 이 목록에 없다. 따라서 Maven 테스트 실패를 Surefire/Failsafe 기준으로 뽑아내지 못하고, 결과가 없으면 마지막 5줄 중심 fallback에 의존한다.

## 5. Maven 테스트에 적용할 필터링 기준

Maven 테스트는 보통 Surefire 또는 Failsafe plugin 출력을 사용한다.

주요 command:

- unit test: `mvn test`
- integration test 포함: `mvn verify`
- 특정 테스트: `mvn -Dtest=FooTest test`
- 특정 integration test: `mvn -Dit.test=FooIT verify`
- 실패 후에도 계속: `mvn -fae test`

필터에서 남겨야 할 Maven/Surefire/Failsafe 정보:

- `<<< FAILURE!`, `<<< ERROR!`가 포함된 테스트 실패 header
- `[ERROR] Tests run: ..., Failures: ..., Errors: ..., Skipped: ...`
- `[ERROR] Failures:`, `[ERROR] Errors:` 섹션
- 실패 테스트명 라인: `[ERROR]   FooTest.testBar:42 ...`
- 예외/Assertion 라인:
  - `java.lang.AssertionError`
  - `org.opentest4j.AssertionFailedError`
  - `kotlin.*`
  - `Caused by:`
- 사용자 코드 stack frame:
  - `at com.myapp...`
  - `at org.example...`
  - framework frame이 아닌 첫 `at ...`
- report 위치:
  - `target/surefire-reports`
  - `target/failsafe-reports`
  - `Please refer to ...`
- Maven 최종 결과:
  - `[INFO] BUILD SUCCESS`
  - `[INFO] BUILD FAILURE`
  - `[INFO] Total time: ...`

제거해도 되는 noise:

- `[INFO] Scanning for projects...`
- `[INFO] --- ...`
- `[INFO] Building ...`
- `[INFO] Downloading ...`, `[INFO] Downloaded ...`
- 빈 `[INFO]` 라인
- 성공 테스트 실행 noise: `[INFO] Running ...`, `[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0`
- Maven 도움말 반복:
  - `[ERROR] Re-run Maven using the -X switch ...`
  - `[ERROR] For more information ...`
  - `[ERROR] After correcting the problems ...`

주의할 점:

- Maven은 실패 상세를 stdout에 바로 많이 보여주기도 하지만, 자세한 내용은 `target/surefire-reports` 또는 `target/failsafe-reports`에만 남는 경우가 있다.
- 따라서 shell script는 raw Maven log뿐 아니라 실패 시 report directory 힌트도 반드시 보여줘야 한다.
- 더 견고하게 만들려면 실패 시 `target/surefire-reports/*.txt`, `target/failsafe-reports/*.txt`에서 실패 block을 추가로 읽는 것이 좋다.

## 6. 별도 shell script 설계안

RTK 프로젝트를 수정하지 않는 조건에서는 다음 구조가 좋다.

```text
mvn-test-filter.sh
  1. 인자를 그대로 Maven에 전달한다. 인자가 없으면 test를 기본값으로 둔다.
  2. stdout/stderr를 임시 raw log에 합쳐서 저장한다.
  3. Maven exit code를 보존한다.
  4. raw log에서 ANSI/color와 noise를 제거한다.
  5. 실패 test header, 예외, 사용자 stack frame, 요약, report path만 출력한다.
  6. 필터 결과가 비면 성공/실패에 따라 fallback 메시지를 출력한다.
  7. 실패하거나 출력이 긴 경우 raw log 경로를 `[full output: ...]`로 보여준다.
```

RTK Gradle 구현에서 가져올 핵심 아이디어:

- `run_filtered()`처럼 raw를 먼저 캡처하고 나중에 필터링한다.
- `filter_test()`처럼 실패 block 상태를 추적한다.
- framework frame은 버리고 사용자 코드 frame을 우선 표시한다.
- exit code는 원래 Maven exit code 그대로 반환한다.
- `tee`처럼 raw output 위치를 남긴다.

## 7. shell script 초안

아래는 시작점으로 쓸 수 있는 예시다. RTK 저장소에 넣는 파일이 아니라 별도 작업공간이나 사용자 프로젝트에 두고 실행하는 전제다.

```bash
#!/usr/bin/env bash
set -u

args=("$@")
if [ "${#args[@]}" -eq 0 ]; then
  args=(test)
fi

log_dir="${RTK_TEE_DIR:-.rtk-logs}"
mkdir -p "$log_dir"
timestamp="$(date +%Y%m%d-%H%M%S)"
raw_log="$log_dir/mvn-${timestamp}.log"

mvn "${args[@]}" >"$raw_log" 2>&1
status=$?

awk '
function strip_ansi(s) {
  gsub(/\033\[[0-9;]*[A-Za-z]/, "", s)
  return s
}
function is_framework_frame(s) {
  return s ~ /^at org\.junit\./ ||
         s ~ /^at org\.apache\.maven\./ ||
         s ~ /^at org\.apache\.surefire\./ ||
         s ~ /^at org\.codehaus\.plexus\./ ||
         s ~ /^at java\.base\/java\.lang\.reflect\./ ||
         s ~ /^at java\.lang\.reflect\./ ||
         s ~ /^at jdk\.internal\.reflect\./ ||
         s ~ /^at sun\.reflect\./
}
function keep_summary(line) {
  return line ~ /\[INFO\] BUILD (SUCCESS|FAILURE)/ ||
         line ~ /\[INFO\] Total time:/ ||
         line ~ /\[INFO\] Finished at:/ ||
         line ~ /\[ERROR\] Tests run:/ ||
         line ~ /Tests run: .*Failures: [1-9]/ ||
         line ~ /Tests run: .*Errors: [1-9]/ ||
         line ~ /target\/surefire-reports/ ||
         line ~ /target\/failsafe-reports/ ||
         line ~ /Please refer to/
}
{
  line = strip_ansi($0)
  trimmed = line
  sub(/^[[:space:]]+/, "", trimmed)

  if (line ~ /^\[INFO\] Scanning for projects/) next
  if (line ~ /^\[INFO\] ---/) next
  if (line ~ /^\[INFO\] Building /) next
  if (line ~ /^\[INFO\] Download(ing|ed) /) next
  if (line ~ /^\[INFO\][[:space:]]*$/) next
  if (line ~ /^\[INFO\] Running /) next
  if (line ~ /^\[INFO\] Tests run: .*Failures: 0, Errors: 0/) next
  if (line ~ /^\[ERROR\] Re-run Maven using/) next
  if (line ~ /^\[ERROR\] For more information/) next
  if (line ~ /^\[ERROR\] After correcting the problems/) next

  if (keep_summary(line)) {
    print line
    next
  }

  if (line ~ /<<< (FAILURE|ERROR)!/) {
    in_failure = 1
    print line
    next
  }

  if (line ~ /^\[ERROR\] (Failures|Errors):/) {
    in_failure = 1
    print line
    next
  }

  if (line ~ /^\[ERROR\][[:space:]]+[A-Za-z0-9_.#$-]+[:.][A-Za-z0-9_#$-]+/) {
    in_failure = 1
    print line
    next
  }

  if (in_failure) {
    if (trimmed ~ /^(java|javax|jakarta|kotlin|org\.opentest4j)\./ ||
        trimmed ~ /^Caused by:/ ||
        trimmed ~ /^AssertionError/) {
      print line
      next
    }

    if (trimmed ~ /^at /) {
      if (!is_framework_frame(trimmed)) {
        print line
        in_failure = 0
      }
      next
    }

    if (line ~ /^\[INFO\]/ && line !~ /^\[INFO\] BUILD/) {
      in_failure = 0
      next
    }
  }
}
' "$raw_log" >"${raw_log}.filtered"

if [ -s "${raw_log}.filtered" ]; then
  cat "${raw_log}.filtered"
else
  if [ "$status" -eq 0 ]; then
    echo "ok - maven tests passed"
  else
    echo "[FAIL] mvn ${args[*]} failed; last output:"
    tail -n 20 "$raw_log"
  fi
fi

if [ "$status" -ne 0 ]; then
  echo "[full output: $raw_log]"
fi

exit "$status"
```

## 8. 이 script를 RTK와 함께 쓰는 방법

RTK 자체 기능을 최대한 이용하려면 두 가지 선택지가 있다.

### 선택지 A: script가 직접 Maven을 실행하고 필터링한다

권장 방식이다.

```bash
./mvn-test-filter.sh test
./mvn-test-filter.sh -Dtest=FooTest test
./mvn-test-filter.sh verify
```

장점:

- Maven/Surefire/Failsafe 전용 필터를 직접 통제할 수 있다.
- exit code 보존이 쉽다.
- raw log 저장과 report hint를 원하는 형식으로 만들 수 있다.

단점:

- RTK tracking DB에는 이 실행이 `rtk` 명령으로 기록되지 않는다.

### 선택지 B: `rtk test`로 script를 감싼다

```bash
rtk test ./mvn-test-filter.sh test
```

장점:

- RTK의 generic test wrapper와 tracking 경로를 일부 활용할 수 있다.

단점:

- script가 이미 필터링한 출력을 다시 `rtk test`가 처리하므로 결과가 과하게 줄어들 수 있다.
- Maven 전용 필터의 출력 포맷을 `rtk test`가 이해하는 것은 아니다.

### 선택지 C: `rtk proxy`로 Maven을 실행한다

```bash
rtk proxy mvn test
```

이 방식은 Maven 원본 실행과 tracking에는 유용하지만, 출력 필터링은 하지 않는다. Maven 테스트 정보를 줄이는 목적에는 부족하다.

## 9. 더 견고한 개선 방향

별도 script를 실제로 오래 쓸 계획이면 다음 순서로 보강하는 것이 좋다.

1. stdout 기반 필터부터 적용한다.
2. 실패 시 `target/surefire-reports/*.txt`, `target/failsafe-reports/*.txt`를 추가로 읽는다.
3. multi-module Maven 프로젝트를 고려해 `*/target/surefire-reports/*.txt`까지 찾는다.
4. `-Dtest=...`, `-Dit.test=...`, `-pl`, `-am`, `-fae` 같은 Maven 인자를 그대로 보존한다.
5. raw log 저장 위치를 `RTK_TEE_DIR` 또는 별도 환경 변수로 제어한다.
6. 성공 시에는 `BUILD SUCCESS`, `Tests run`, `Total time` 정도만 남긴다.
7. 실패 시에는 실패 테스트당 "테스트명 + 예외 + 사용자 코드 첫 frame + report path"를 남긴다.

## 10. RTK 프로젝트에 기능을 넣는다면 필요한 변경점

이번 요청은 RTK 프로젝트 수정이 아니므로 참고용이다.

RTK 본체에 Maven 테스트 전용 기능을 넣으려면 대략 다음이 필요하다.

- `src/cmds/jvm/mvn_cmd.rs` 추가
- `src/cmds/jvm/mod.rs`에 module 등록
- `src/main.rs`에 `Mvn { args }` subcommand 추가
- `run()`에서 `test`, `surefire:test`, `failsafe:integration-test`, `verify` 감지
- `filter_maven_test()` 구현
- `src/discover/rules.rs` Maven rule에 `test`, `verify` 추가
- fixture 추가:
  - `tests/fixtures/mvn_test_raw.txt`
  - `tests/fixtures/mvn_test_failed_raw.txt`
  - multi-module 실패 fixture
- `cargo test mvn_cmd` 수준의 단위 테스트 추가

## 11. 최종 판단

Maven 테스트에 현재 RTK의 Gradle 테스트 필터링이 자동으로 적용되지는 않는다.

다만 Gradle 필터의 설계 원칙은 Maven에도 그대로 적용 가능하다.

- raw output 먼저 캡처
- 실패 block 상태 추적
- framework stack frame 제거
- 사용자 코드 frame 보존
- 테스트 요약과 report path 보존
- 실패 시 원본 로그 hint 제공
- 원래 exit code 보존

따라서 별도 `.sh`를 만든다면 `rtk gradlew`의 Rust 코드를 그대로 흉내 내기보다, Maven/Surefire/Failsafe 출력 형식에 맞춘 전용 shell filter로 만드는 것이 맞다.
