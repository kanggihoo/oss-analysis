#!/bin/sh
# Per-type differences (erd/tree). Same installed archify, read-only validate.
cd "$(dirname "$0")"
A="node $HOME/.claude/skills/archify/bin/archify.mjs"
mkdir -p out-other
for spec in erd-no-output:erd erd-output-colon:erd erd-output-txt:erd arch-output-colon:architecture tree-missing-parent:tree tree-engineering-profile:tree; do
  c=${spec%%:*}; t=${spec##*:}
  $A validate $t inputs-other/$c.json > out-other/$c.stdout 2> out-other/$c.stderr < /dev/null; echo $? > out-other/$c.exit
done
# top-level non-object JSON
$A validate architecture inputs-other/top-null.json > out-other/top-null.stdout 2> out-other/top-null.stderr < /dev/null; echo $? > out-other/top-null.exit
# loadDiagram's last step: output path resolved AFTER validation; output == input is refused before anything is written
cp inputs/ok.json inputs-other/alias-copy.json
$A render architecture inputs-other/alias-copy.json inputs-other/alias-copy.json > out-other/alias.stdout 2> out-other/alias.stderr < /dev/null; echo $? > out-other/alias.exit
cmp inputs/ok.json inputs-other/alias-copy.json && echo "input untouched" > out-other/alias.check
