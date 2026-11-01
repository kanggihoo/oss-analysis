#!/bin/sh
# Needs 01 (out/) and 02 (work/). Chrome readability boundary, stale receipt ownership, finalize rerun, output forms, visual-check capture names.
A=/Users/kkh/.claude/skills/archify/bin/archify.mjs
cd "$(dirname "$0")"
python3 - <<'PY'
h=open('out/brand-aware-delivery.architecture.html',encoding='utf8').read()
old='x="289" y="292" class="t-primary" font-size="11"'
for v in ('5.9','6'): open(f'work/font_{v}.html','w',encoding='utf8').write(h.replace(old,old.replace('11',v),1))
PY
echo "== readability: static check (legacy 930px budget) vs browser (real svg width)"
for c in font_5.9 font_6 font_7.2 font_7.3; do
  node $A check work/$c.html >work/$c.c.json; ce=$?
  node $A browser-check work/$c.html --json --out-dir out/bc-$c >out/bc-$c.stdout.json; be=$?
  python3 -c "
import json;c=json.load(open('work/$c.c.json'));b=json.load(open('out/bc-$c.stdout.json'))
print('$c','check exit=$ce',[round(i['projectedFontPx'],3) for i in c['composition']['issues'] if 'readab' in i['code']],'| browser exit=$be',b['status'],[(d['code'],d['subject']['viewport']['width']) for d in b['diagnostics']][:2])"
done
echo "== stale receipt: redeliver changed bytes to same path, rerun browser-check"
rm -rf prov3; mkdir prov3
node $A deliver architecture inputs/brand-aware-delivery.architecture.json prov3/a.html --json >/dev/null 2>&1
node $A browser-check prov3/a.html --json --require-provenance >/dev/null; echo "run1 exit=$?"
node $A deliver architecture inputs/brand-aware-delivery.v2.architecture.json prov3/a.html --json >/dev/null 2>&1
node $A browser-check prov3/a.html --json --require-provenance | python3 -c "import json,sys;j=json.load(sys.stdin);print(j['status'],[(d['code'],d['evidence'].get('reason')) for d in j['diagnostics']])"
node $A browser-check prov3/a.html --json --require-provenance --out-dir prov3/evid2 | python3 -c "import json,sys;j=json.load(sys.stdin);print('with fresh --out-dir:',j['status'])"
echo "== finalize twice to same output with changed input"
rm -rf prov4; mkdir prov4
node $A finalize architecture inputs/brand-aware-delivery.architecture.json prov4/a.html --json >prov4/f1.json 2>&1; echo "f1 exit=$?"
node $A finalize architecture inputs/brand-aware-delivery.v2.architecture.json prov4/a.html --json >prov4/f2.json 2>&1; echo "f2 exit=$?"
python3 -c "import json;j=json.load(open('prov4/f2.json'));print(j['failedStage'],j['gates'],[d['code'] for d in j['diagnostics']])"
echo "== forms and capture names"
node $A browser-check prov3/a.html --out-dir out/bc-human; echo "exit=$?"
node $A browser-check prov3/a.html --summary --out-dir out/bc-human | head -c 300; echo
rm -rf out/bc-vis; node $A visual-check prov3/a.html --json --out-dir out/bc-vis >/dev/null; echo "visual-check exit=$?"; ls out/bc-vis
