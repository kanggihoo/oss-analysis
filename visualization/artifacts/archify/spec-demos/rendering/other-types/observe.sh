#!/bin/sh
# 개별 좌표 관찰(HTML은 삭제). sh observe.sh > observed.txt
CLI=/Users/kkh/.claude/skills/archify/bin/archify.mjs
cd "$(dirname "$0")"
for t in "sequence sq.spread3" "sequence sq.fixed3" "erd erd.band" "tree tr.stack" "waterfall wf.inc"; do
  set -- $t; node $CLI render $1 in/$2.json out/obs.html >/dev/null 2>&1 </dev/null
  echo "== $2"
  python3 -I - <<'P'
import re
s=open('out/obs.html').read()
for m in re.finditer(r'<rect[^>]*data-domain-band|<g data-domain-band="([^"]*)"[^>]*>\s*<rect ([^>]*)>', s): print('band', m.group(1), m.group(2))
for m in re.finditer(r'<g id="node-([^"]*)"[^>]*>\s*(?:<[^>]*>\s*)*?<rect ([^>]*?)/?>', s):
    a=m.group(2); xs=dict(re.findall(r'(\w+)="([^"]*)"',a)); print('node', m.group(1), {k:xs.get(k) for k in ('x','y','width','height')})
for m in re.finditer(r'<line[^>]*lifeline[^>]*>', s): print(m.group(0)[:160])
P
done
rm -f out/obs.html
