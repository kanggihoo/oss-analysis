#!/bin/sh
# compare 실험. scratch 사본(base.json/head.json) 대상. 출력은 이 폴더 안에서만.
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
cd "$(dirname "$0")"
rm -rf out && mkdir out
echo "== 1. 정상 (기본 receipt)"; $A compare architecture base.json head.json out/delta.html; echo "exit=$?"; ls out
echo "== 2. --json"; $A compare architecture base.json head.json out/delta2.html --receipt out/delta2.receipt.json --json > out/stdout2.json; echo "exit=$?"
echo "== 3. 같은 입력(변화 없음)"; $A compare architecture base.json base.json out/same.html >/dev/null 2>out/same.err; echo "exit=$?"; tail -3 out/same.err
echo "== 4. 공유 id 없음"; python3 - <<'PY'
import json
d=json.load(open('base.json'))
for c in d['components']: c['id']='x_'+c['id']
for c in d['connections']: c['id']='x_'+c['id']; c['from']='x_'+c['from']; c['to']='x_'+c['to']
for b in d.get('boundaries',[]): b['wraps']=['x_'+w for w in b['wraps']]
json.dump(d,open('noshare.json','w'))
PY
$A compare architecture base.json noshare.json out/noshare.html --json > out/noshare.json.out 2>out/noshare.err; echo "exit=$?"; cat out/noshare.json.out | head -30
echo "== 5. 사용법 오류"; $A compare sequence base.json head.json >/dev/null 2>out/usage.err; echo "exit=$?"; head -2 out/usage.err
echo "== 6. receipt가 다른 디렉터리"; mkdir -p out/sub; $A compare architecture base.json head.json out/d6.html --receipt out/sub/r.json 2>out/r6.err; echo "exit=$?"; head -3 out/r6.err
echo "== 7. 알 수 없는 옵션"; $A compare architecture base.json head.json --bogus 2>&1 | head -2; echo "exit=$?"
