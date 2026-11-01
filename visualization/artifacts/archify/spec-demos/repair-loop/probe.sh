#!/bin/bash
# 탐색용: 일부러 만든 실패 입력들을 finalize --json 으로 돌려 요약의 진단 code만 훑는다.
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
H="$(cd "$(dirname "$0")" && pwd)"; cd "$H"
export ARCHIFY_UPDATE_CHECK_DISABLED=1
for f in "$@"; do
  n=$(basename $f .json); t=${n##*.}; rm -rf work/probe-$n; mkdir -p work/probe-$n
  (cd work/probe-$n && $A finalize $t $f p.html --json >stdout.json 2>stderr.txt; echo "exit=$?" > exit.txt)
  echo "== $n $(cat work/probe-$n/exit.txt)"
  python3 -c "
import json,sys
try:
  d=json.load(open('work/probe-$n/stdout.json'))
except Exception as e:
  print('nojson'); sys.exit()
print(d.get('status'),d.get('failedStage'),d.get('gates'))
for x in d.get('diagnostics',[]): print(' ',x['code'],'|',x['message'][:140])
"
done
