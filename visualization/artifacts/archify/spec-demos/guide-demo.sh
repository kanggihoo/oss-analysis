#!/bin/sh
# 읽기 전용: 로컬 설치본(레포 archify/와 diff -rq 동일)의 guide를 사례별로 실행
A=/Users/kkh/.claude/skills/archify/bin/archify.mjs
run() { echo "\$ archify guide $*"; node $A guide "$@"; echo "[exit $?]"; echo; }
slim() { node -e 'const r=JSON.parse(require("fs").readFileSync(0,"utf8")); console.log(JSON.stringify({ok:r.ok,mode:r.mode,lang:r.lang,confidence:r.confidence,matchedSignals:r.matchedSignals,rec:r.recommendation&&[r.recommendation.id,r.recommendation.type],alts:r.alternatives&&r.alternatives.map(a=>[a.id,a.score]),keys:Object.keys(r),recKeys:r.recommendation&&Object.keys(r.recommendation)}))'; }
j() { echo "\$ archify guide $* --json  (slim)"; node $A guide "$@" --json | slim; echo; }
j "ci/cd release workflow with rollback"
j "kafka topology with consumer group and dlq"
j "hello"
j ""
j "system-overview"
j "database schema"
j "API 请求 调用链"
j "api request" --lang zh
j "data lineage etl"
j "viewport overflow"
j "Deployment Lifecycle"
echo '$ archify guide --json (list, slim)'; node $A guide --json | node -e 'const r=JSON.parse(require("fs").readFileSync(0,"utf8")); console.log(r.mode,r.lang,r.recipes.length,Object.keys(r.recipes[0]).join(","))'
echo; run "api request"
run --bogus
run x --lang fr
