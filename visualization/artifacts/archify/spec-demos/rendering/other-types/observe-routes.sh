#!/bin/sh
# 설치본 렌더러 직접 호출(--layout-json)로 일반 관계선 좌표 관찰. HTML은 만들지 않는다.
R=/Users/kkh/.claude/skills/archify/renderers
cd "$(dirname "$0")"
for n in erd.r1 erd.r2 erd.r3 erd.r4 erd.r5 erd.r6 cl.r1 cl.r2 cl.r3 cl.r4 cl.r5 cl.r6; do
  case $n in erd*) t=erd;; *) t=class;; esac
  node $R/$t/render-$t.mjs in/$n.json --layout-json 2>/dev/null </dev/null | python3 -I -c "
import json,sys
d=json.load(sys.stdin)
print('$n','viewBox',d['viewBox'])
k='entities' if 'entities' in d else 'types'
print('  boxes',[(e['id'],e['x'],e['y'],e['width'],e['height']) for e in d[k]])
for r in d['relationships']:
    print('  ',r['from'],'->',r['to'],';'.join('%g,%g'%tuple(p) for p in r['points']), 'label',r.get('labelPoint') or r.get('label'))
"
done
# dataflow showcase 격자 우회(HTML은 만들고 바로 삭제)
mkdir -p out
for n in df.r1.show df.r1.std; do
  node /Users/kkh/.claude/skills/archify/bin/archify.mjs render dataflow in/$n.json out/$n.html >/dev/null 2>out/$n.err </dev/null
  echo "$n exit=$? $(grep -o '\[[a-z/-]*\]' out/$n.err | sort -u | tr '\n' ' ')"
done
python3 -I extract.py | grep -A4 "df.r1"
rm -f out/df.r1.*.html
