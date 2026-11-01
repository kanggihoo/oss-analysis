#!/bin/sh
# 설치본(레포와 바이트 동일) archify render 만 사용. 사용: python3 -I gen.py; sh run.sh
CLI=/Users/kkh/.claude/skills/archify/bin/archify.mjs
R=/Users/kkh/.claude/skills/archify/renderers
EX=/Users/kkh/.claude/skills/archify/examples
cd "$(dirname "$0")"; mkdir -p out; : > summary.txt
type_of() { case "$1" in df*) echo dataflow;; lc*) echo lifecycle;; erd*) echo erd;; cl*) echo class;; sq*) echo sequence;; tr*) echo tree;; tl*) echo timeline;; wf*) echo waterfall;; esac; }
run() { # name file type
  node "$CLI" render "$3" "$2" "out/$1.html" >"out/$1.out" 2>"out/$1.err" </dev/null; rc=$?
  vb=$(grep -o '<svg viewBox="[^"]*"' "out/$1.html" 2>/dev/null | head -1 | sed 's/<svg viewBox=//')
  codes=$(grep -o '^\[[a-z/-]*\]' "out/$1.err" | sort -u | tr '\n' ' ')
  echo "$1 exit=$rc viewBox=$vb codes=$codes" | tee -a summary.txt
}
for f in in/*.json; do b=$(basename "$f" .json); run "$b" "$f" "$(type_of "$b")"; done
echo "--- bundled examples" | tee -a summary.txt
for p in orders.erd payments.class payment-processors.class agent-run.lifecycle deployment-release.lifecycle async-job-roundtrip.sequence cache-miss-request.sequence product-analytics.dataflow event-stream.dataflow payment-platform.tree archify-repository.tree payment-incident.timeline archify-dev-activity.timeline checkout-request.waterfall example-rebuild.waterfall subscription-billing.erd; do
  t=${p##*.}; run "ex.$p" "$EX/$p.json" "$t"; done
echo "--- layout-json (installed renderer direct)" | tee -a summary.txt
for p in "erd erd.trunk" "erd erd.band" "class cl.bus" "class cl.half" "tree tr.stack" "tree tr.right" "timeline tl.break" "waterfall wf.inc"; do
  set -- $p; node $R/$1/render-$1.mjs in/$2.json --layout-json >out/$2.layout.json 2>/dev/null </dev/null; echo "$2 layout-json exit=$? bytes=$(wc -c <out/$2.layout.json | tr -d ' ')" | tee -a summary.txt
done
echo "--- finalize sequence width advice" | tee -a summary.txt
for n in sq.fixed5 sq.spread5; do
  node "$CLI" finalize sequence in/$n.json out/$n.fin.html --json --out-dir out/fin-$n >out/$n.fin.json 2>/dev/null </dev/null
  echo "$n finalize exit=$? $(python3 -I -c "import json;d=json.load(open('out/$n.fin.json'));print(d.get('ok'), json.dumps(d.get('layoutReviewRecommendation',{}).get('evidence')))")" | tee -a summary.txt
done
python3 -I extract.py >points.txt
rm -rf out/*.html out/fin-* 
