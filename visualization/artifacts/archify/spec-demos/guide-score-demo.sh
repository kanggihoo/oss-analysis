#!/bin/sh
# 읽기 전용: 점수·신뢰도 경계, 동점, alternatives, 부분 문자열 일치 확인 (설치본 사용)
A=/Users/kkh/.claude/skills/archify/bin/archify.mjs
j() { printf '%s => ' "$1"; node $A guide "$1" --json | node -e 'const r=JSON.parse(require("fs").readFileSync(0,"utf8")); console.log(JSON.stringify({conf:r.confidence,matched:r.matchedSignals,rec:r.recommendation.id,type:r.recommendation.type,alts:r.alternatives.map(a=>[a.id,a.score])}))'; }
j "cache miss"
j "kafka topology"
j "components"
j "region"
j "services"
j "state machine and er diagram"
j "approval gate rollback pull request"
j "Kafka   Topology"
j "settled accounts"
j "ER 图"
j "review the viable design"
j "api gateway via cdn"
j "layout overlap and crossing"
