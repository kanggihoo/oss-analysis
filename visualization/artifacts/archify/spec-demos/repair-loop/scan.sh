#!/bin/bash
# 기존 데모 입력(변이 없음) 전체를 showcase finalize --json 으로 돌려 어떤 입력이 어떤 진단·권고를 내는지 본다. 요약: out/scan-summary.txt
H="$(cd "$(dirname "$0")" && pwd)"; export ARCHIFY_UPDATE_CHECK_DISABLED=1
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
mkdir -p $H/out; : > $H/out/scan-summary.txt
for f in $H/../rendering/in/*.json $H/../finalize/in/release-delivery.workflow.json $H/../verification-gates/inputs/*.json $H/../verification-gates/inputs/alltypes/*.json; do
  n=$(basename $f .json); t=${n##*.}; d=$H/work/scan-$(basename $(dirname $(dirname $f)))-$(basename $(dirname $f))-$n; rm -rf $d; mkdir -p $d
  (cd $d; $A finalize $t $f s.html --json >o.json 2>e.txt; echo $? >x)
  python3 - $d $n $(basename $(dirname $f)) <<'PY'
import json,sys
d,n=sys.argv[1:3]
try:
  j=json.load(open(d+'/o.json'))
  print(sys.argv[3],n,open(d+'/x').read().strip(),j.get('status'),[k for k in ('visualReviewRecommendation','layoutReviewRecommendation','nextAction') if k in j],[x['code'] for x in j.get('diagnostics',[])][:3])
except Exception as e: print(n,'ERR',e)
PY
done
