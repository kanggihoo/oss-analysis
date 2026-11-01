#!/bin/sh
# Extra observations: (1) JSON mode keeps earlier warnings in a later failure's diagnostics,
# (2) renderer diagnostic boundary in JSON mode when run via `render` (stderr = one JSON line, exit 1).
cd "$(dirname "$0")"
A="node $HOME/.claude/skills/archify/bin/archify.mjs"
for m in text receipt; do
  f=""; [ $m = receipt ] && f=--json
  $A validate architecture inputs/locale-xx-then-dup-id.json $f > out/locale-xx-then-dup-id.$m.stdout 2> out/locale-xx-then-dup-id.$m.stderr < /dev/null
  echo $? > out/locale-xx-then-dup-id.$m.exit
done
ARCHIFY_DIAGNOSTIC_FORMAT=json $A render architecture inputs/dup-relationship-id.json out/never-written.html > out/dup-id.render-jsonenv.stdout 2> out/dup-id.render-jsonenv.stderr < /dev/null
echo $? > out/dup-id.render-jsonenv.exit
