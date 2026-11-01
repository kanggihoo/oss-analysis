#!/bin/sh
# Runs the installed archify (byte-identical to repos/archify archify/ at a406594; diff -rq checked) read-only:
#   archify validate architecture inputs/<case>.json [--json] --repo-root <repo>
# cwd = this directory because meta.output must stay inside cwd. Run setup-repo.sh and make-inputs.py first.
# Output: out/<case>.<mode>.{stdout,stderr,exit}; mode = text | receipt (--json) | noroot (no --repo-root) | <other>
cd "$(dirname "$0")"
A="node $HOME/.claude/skills/archify/bin/archify.mjs"
mkdir -p out
run() { # name mode extra-args... (stdin closed)
  name=$1; mode=$2; shift 2
  $A "$@" > "out/$name.$mode.stdout" 2> "out/$name.$mode.stderr" < /dev/null
  echo $? > "out/$name.$mode.exit"
}
R="$PWD/repo"
for f in inputs/*.json; do
  c=$(basename "$f" .json)
  run "$c" text    validate architecture "$f" --repo-root "$R"
  run "$c" receipt validate architecture "$f" --json --repo-root "$R"
  run "$c" noroot  validate architecture "$f"
done
# origin forms and other hosts
run ev-ok-origin-ssh-case    text validate architecture inputs/ev-ok.json --repo-root "$PWD/repo-ssh"
run ev-origin-case-vs-ssh    text validate architecture inputs/ev-origin-case.json --repo-root "$PWD/repo-ssh"
run ev-localonly-selfhosted  repo-selfhosted validate architecture inputs/ev-localonly-selfhosted.json --repo-root "$PWD/repo-selfhosted"
run ev-web-selfhosted        repo-selfhosted validate architecture inputs/ev-web-selfhosted.json --repo-root "$PWD/repo-selfhosted"
run ev-selfhosted-gitlab-hint repo-selfhosted validate architecture inputs/ev-selfhosted-gitlab-hint.json --repo-root "$PWD/repo-selfhosted"
run ev-ok                    repo-noorigin validate architecture inputs/ev-ok.json --repo-root "$PWD/repo-noorigin"
# --repo-root problems
run ev-ok root-subdir    validate architecture inputs/ev-ok.json --repo-root "$R/src"
run ev-ok root-missing   validate architecture inputs/ev-ok.json --repo-root "$PWD/no-such-dir"
run ev-ok root-not-git   validate architecture inputs/ev-ok.json --repo-root /private/tmp
run ev-ok root-flag-bare validate architecture inputs/ev-ok.json --repo-root
# missing input file
run missing-file text validate architecture inputs/does-not-exist.json
# renderer's own loadDiagram path (no CLI pre-check): render fails before writing anything
for c in broken-json schema-bad ev-line-out-of-range out-ext; do
  run "$c" render render architecture "inputs/$c.json" out/never-written.html --repo-root "$R"
done
ls out/never-written.html > out/never-written.check 2>&1
