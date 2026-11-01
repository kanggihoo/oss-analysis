#!/bin/sh
# deliver -> check -> browser-check on three example types (installed copy, byte-identical to repo archify/)
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
cd "$(dirname "$0")"; rm -rf out; mkdir -p out
for p in architecture:brand-aware-delivery.architecture sequence:cache-miss-request.sequence workflow:release-delivery.workflow; do
  t=${p%%:*}; n=${p#*:}
  $A deliver $t inputs/$n.json out/$n.html --json > out/$n.deliver.json 2>out/$n.deliver.err; echo "$n deliver exit=$?"
  $A check out/$n.html --json --require-provenance > out/$n.check.json; echo "$n check exit=$?"
  $A browser-check out/$n.html --json --require-provenance > out/$n.browser-check.stdout.json; echo "$n browser-check exit=$?"
done
ls out
