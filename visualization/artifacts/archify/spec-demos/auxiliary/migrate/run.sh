#!/bin/sh
# migrate 실험. scratch 사본만 사용, 출력은 out/ 안.
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
cd "$(dirname "$0")"
rm -rf out && mkdir out
echo "== 1. v1 -> v2 정상"; $A migrate workflow v1.json out/v1-migrated.json --to-schema 2; echo "exit=$?"; ls -A out
echo "== 2. --json"; $A migrate workflow v1.json out/v1-migrated2.json --to-schema 2 --json > out/report.json; echo "exit=$?"
echo "== 3. 이미 v2"; $A migrate workflow v2.json out/v2-same.json --to-schema 2; echo "exit=$?"; cmp v2.json out/v2-same.json && echo "v2: bytes equal to source"
echo "== 4. --to-schema 3"; $A migrate workflow v1.json out/x.json --to-schema 3 2>&1 | head -2; echo "exit=${PIPESTATUS:-?}"
echo "== 4b exit"; $A migrate workflow v1.json out/x.json --to-schema 3 >/dev/null 2>&1; echo "exit=$?"
echo "== 5. 소스==목적지"; cp v1.json out/same-src.json; $A migrate workflow out/same-src.json out/same-src.json --to-schema 2 2>&1 | head -3; $A migrate workflow out/same-src.json out/same-src.json --to-schema 2 >/dev/null 2>&1; echo "exit=$?"; cmp v1.json out/same-src.json && echo "source untouched"
echo "== 6. 소스 없음"; $A migrate workflow nope.json out/n.json --to-schema 2 --json > out/nope.json.out; echo "exit=$?"
echo "== 7. --output 로 meta.output 교체"; $A migrate workflow v1.json out/v1-o.json --to-schema 2 --output portable.html --json > out/o.report.json; echo "exit=$?"
echo "== 8. release-delivery v1 -> v2"; $A migrate workflow v1b.json out/v1b-migrated.json --to-schema 2 --json > out/report-b.json; echo "exit=$?"
node -e "const r=require('./out/report-b.json');console.log(r.ok,r.fromSchemaVersion,r.toSchemaVersion,JSON.stringify(r.destination).slice(-90),'changed:',r.changedCoordinates.length,r.oldRequiredViewBox,r.newRequiredViewBox,'pre:',r.preExistingDiagnostics.length,Object.keys(r).join())"
node -e "const a=require('./v1b.json'),b=require('./out/v1b-migrated.json');console.log('schema',a.schema_version,'->',b.schema_version)"
ls -A out | tr '\n' ' '; echo
echo "== 9. 재실행 결정성"; $A migrate workflow v1b.json out/v1b-migrated-again.json --to-schema 2 >/dev/null; cmp out/v1b-migrated.json out/v1b-migrated-again.json && echo identical
echo "== 10. 목적지 덮어쓰기(기존 파일 있음)"; echo '{"keep":"old"}' > out/exist.json; $A migrate workflow v1b.json out/exist.json --to-schema 2 >/dev/null; echo "exit=$?"; head -c 60 out/exist.json; echo
echo "== 11. 실패 시 기존 목적지 유지"; echo '{"keep":"old"}' > out/exist2.json; $A migrate workflow v1.json out/exist2.json --to-schema 2 >/dev/null 2>&1; echo "exit=$?"; cat out/exist2.json
echo "== 12. v1 output 필드 오류 후 --output"; ls -A out | grep -c archify-migration || true
