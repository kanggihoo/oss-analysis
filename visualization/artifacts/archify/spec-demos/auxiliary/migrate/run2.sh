#!/bin/sh
# migrate 성공 경로: 최소 v1 워크플로
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
cd "$(dirname "$0")"
rm -rf out2 && mkdir out2
echo "== A. v1-min -> v2"; $A migrate workflow v1-min.json out2/min-v2.json --to-schema 2; echo "exit=$?"; ls -A out2
echo "== B. --json 보고서"; $A migrate workflow v1-min.json out2/min-v2b.json --to-schema 2 --json > out2/report.json; echo "exit=$?"
node -e "const r=require('./out2/report.json');const {source,destination,...x}=r;console.log(JSON.stringify(x));console.log(Object.keys(source),Object.keys(destination))"
node -e "const a=require('./v1-min.json'),b=require('./out2/min-v2.json');console.log('schema',a.schema_version,'->',b.schema_version);console.log(JSON.stringify(Object.keys(b)),JSON.stringify(b.meta))"
echo "== C. 결정성"; $A migrate workflow v1-min.json out2/min-v2c.json --to-schema 2 > /dev/null; cmp out2/min-v2.json out2/min-v2c.json && echo identical
echo "== D. v2 결과를 다시 migrate (멱등)"; $A migrate workflow out2/min-v2.json out2/min-v2d.json --to-schema 2 >/dev/null; echo "exit=$?"; cmp out2/min-v2.json out2/min-v2d.json && echo idempotent
echo "== E. 기존 목적지 교체"; echo '{"keep":"old"}' > out2/exist.json; $A migrate workflow v1-min.json out2/exist.json --to-schema 2 >/dev/null; echo "exit=$?"; head -c 40 out2/exist.json; echo
echo "== F. 렌더 가능 확인(render)"; $A render workflow out2/min-v2.json out2/min-v2.html >/dev/null; echo "exit=$?"; ls out2/min-v2.html
echo "== G. --output 으로 meta.output 교체"; $A migrate workflow v1-min.json out2/o.json --to-schema 2 --output portable.html >/dev/null; echo "exit=$?"; node -e "console.log(require('./out2/o.json').meta.output)"
echo "== H. schema_version 3 소스"; node -e "const d=require('./v1-min.json');d.schema_version=3;require('fs').writeFileSync('v3.json',JSON.stringify(d))"; $A migrate workflow v3.json out2/v3.json --to-schema 2 --json > out2/v3.report.json; echo "exit=$?"; node -e "const r=require('./out2/v3.report.json');console.log(JSON.stringify([r.preExistingDiagnostics.map(d=>d.code),r.migrationDiagnostics.map(d=>d.code)]))"
