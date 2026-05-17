#!/usr/bin/env bash
set -u

usage() {
  cat <<'EOF'
Usage:
  mvn-test-filter.sh [maven args...]
  mvn-test-filter.sh --filter-log <log-file>

Examples:
  ./mvn-test-filter.sh test
  ./mvn-test-filter.sh -Dtest=FooTest test
  ./mvn-test-filter.sh verify
  MVN_CMD=./mvnw ./mvn-test-filter.sh test

Behavior:
  - Uses ./mvnw first, then ./mvnw.cmd, then mvn from PATH.
  - If no args are given, runs "test".
  - Writes full Maven output to .rtk-logs/mvn-<timestamp>.log.
  - Prints compact test failures, summaries, report paths, and build status.
EOF
}

die() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 127
}

filter_maven_log() {
  awk '
  BEGIN {
    esc = sprintf("%c", 27)
  }

  function strip_ansi(s) {
    gsub(esc "\\[[0-9;]*[A-Za-z]", "", s)
    return s
  }

  function strip_maven_prefix(s) {
    sub(/^[[:space:]]+/, "", s)
    sub(/^\[(INFO|ERROR|WARNING|WARN)\][[:space:]]*/, "", s)
    sub(/^[[:space:]]+/, "", s)
    return s
  }

  function is_framework_frame(s) {
    return s ~ /^at org\.junit\./ ||
           s ~ /^at junit\./ ||
           s ~ /^at org\.apache\.maven\./ ||
           s ~ /^at org\.apache\.surefire\./ ||
           s ~ /^at org\.apache\.failsafe\./ ||
           s ~ /^at org\.codehaus\.plexus\./ ||
           s ~ /^at java\.base\/java\.lang\.reflect\./ ||
           s ~ /^at java\.lang\.reflect\./ ||
           s ~ /^at jdk\.internal\.reflect\./ ||
           s ~ /^at sun\.reflect\./
  }

  function is_exception_line(s) {
    return s ~ /^(java|javax|jakarta|kotlin|scala|groovy|org\.opentest4j)\./ ||
           s ~ /^AssertionError/ ||
           s ~ /^Caused by:/ ||
           s ~ /^Suppressed:/
  }

  function keep_summary(line) {
    return line ~ /^\[INFO\] BUILD (SUCCESS|FAILURE)/ ||
           line ~ /^\[INFO\] Total time:/ ||
           line ~ /^\[INFO\] Finished at:/ ||
           line ~ /^\[ERROR\] Tests run:/ ||
           line ~ /Tests run: [0-9]+, Failures: [0-9]+, Errors: [0-9]+/ ||
           line ~ /target\/surefire-reports/ ||
           line ~ /target\/failsafe-reports/ ||
           line ~ /Please refer to/ ||
           line ~ /There are test failures/
  }

  {
    line = strip_ansi($0)
    trimmed = strip_maven_prefix(line)

    if (line ~ /^\[INFO\] Scanning for projects/) next
    if (line ~ /^\[INFO\] ---/) next
    if (line ~ /^\[INFO\] Building /) next
    if (line ~ /^\[INFO\] Download(ing|ed) /) next
    if (line ~ /^Downloading:/) next
    if (line ~ /^Downloaded:/) next
    if (line ~ /^Progress /) next
    if (line ~ /^\[INFO\][[:space:]]*$/) next
    if (line ~ /^\[INFO\] Running /) next
    if (line ~ /^\[ERROR\] Re-run Maven using/) next
    if (line ~ /^\[ERROR\] For more information/) next
    if (line ~ /^\[ERROR\] After correcting the problems/) next
    if (line ~ /^\[ERROR\] \[Help [0-9]+\]/) next

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
      if (is_exception_line(trimmed)) {
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

      if (line ~ /^\[ERROR\][[:space:]]{3,}/) {
        print line
        next
      }

      if (line ~ /^\[INFO\]/ || line ~ /^\[ERROR\] ->/) {
        in_failure = 0
        next
      }
    }
  }
  ' "$1"
}

choose_maven_command() {
  if [ "${MVN_CMD:-}" != "" ]; then
    # shellcheck disable=SC2206
    MVN_COMMAND=(${MVN_CMD})
    return 0
  fi

  if [ -f "./mvnw" ]; then
    if [ -x "./mvnw" ]; then
      MVN_COMMAND=("./mvnw")
    else
      MVN_COMMAND=("sh" "./mvnw")
    fi
    return 0
  fi

  if [ -f "./mvnw.cmd" ]; then
    MVN_COMMAND=("./mvnw.cmd")
    return 0
  fi

  if command -v mvn >/dev/null 2>&1; then
    MVN_COMMAND=("mvn")
    return 0
  fi

  if [ -d ".mvn/wrapper" ]; then
    die "Maven wrapper config exists, but ./mvnw or ./mvnw.cmd is missing. Restore the wrapper script or set MVN_CMD."
  fi

  die "No Maven runner found. Expected ./mvnw, ./mvnw.cmd, mvn in PATH, or MVN_CMD."
}

run_filter_only() {
  local log_file="$1"

  if [ ! -f "$log_file" ]; then
    printf '[FAIL] log file not found: %s\n' "$log_file" >&2
    return 2
  fi

  filter_maven_log "$log_file"
}

main() {
  if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    return 0
  fi

  if [ "${1:-}" = "--filter-log" ]; then
    if [ "${2:-}" = "" ]; then
      printf '[FAIL] --filter-log requires a file path\n' >&2
      return 2
    fi
    run_filter_only "$2"
    return $?
  fi

  local args=("$@")
  if [ "${#args[@]}" -eq 0 ]; then
    args=("test")
  fi

  choose_maven_command

  local log_dir="${RTK_TEE_DIR:-.rtk-logs}"
  mkdir -p "$log_dir" || return 1

  local timestamp
  timestamp="$(date +%Y%m%d-%H%M%S)"
  local raw_log="$log_dir/mvn-${timestamp}.log"
  local filtered_log="${raw_log}.filtered"

  "${MVN_COMMAND[@]}" "${args[@]}" >"$raw_log" 2>&1
  local status=$?

  filter_maven_log "$raw_log" >"$filtered_log"

  if [ -s "$filtered_log" ]; then
    cat "$filtered_log"
  elif [ "$status" -eq 0 ]; then
    printf 'ok - maven tests passed\n'
  else
    printf '[FAIL] %s %s failed; last output:\n' "${MVN_COMMAND[*]}" "${args[*]}"
    tail -n 20 "$raw_log"
  fi

  if [ "$status" -ne 0 ]; then
    printf '[full output: %s]\n' "$raw_log"
  fi

  return "$status"
}

main "$@"
