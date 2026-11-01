#!/bin/bash
# 후보 변조 감지 실험(타이밍 의존). finalize 실행 중 입력 파일 끝에 개행을 덧붙인다.
# 지연 0.9초: 보통 browser-check 중 → finalize/candidate-changed (failedStage finalize)
# 지연 0.12초: 보통 deliver 시작 전후 → finalize/candidate-changed-during-delivery 이거나 정상 통과(경쟁). 결과는 out/race-*.txt
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
H="$(cd "$(dirname "$0")" && pwd)"; cd "$H"; mkdir -p work/race out
export ARCHIFY_UPDATE_CHECK_DISABLED=1
for delay in 0.9 0.12 0.2 0.3; do
  d=work/race/d$delay; rm -rf $d; mkdir -p $d; cp in/ok.json $d/cand.json
  (cd $d && $A finalize lifecycle cand.json r.html --json > stdout.json 2>stderr.txt; echo $? > exit.txt) &
  sleep $delay; echo >> $d/cand.json; wait
  python3 - "$d" "$delay" >> out/race-summary.txt <<'P'
import json,sys
d,delay=sys.argv[1:]
s=json.load(open(d+'/stdout.json'))
print(delay,open(d+'/exit.txt').read().strip(),s['status'],s['gates'],s.get('failedStage'),[x['code'] for x in s['diagnostics']])
P
done
