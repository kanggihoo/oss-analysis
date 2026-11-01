#!/bin/sh
# render 결과 HTML 에서 svg 루트·레인·그룹·노드 한 개만 잘라 render-slices.txt 에 남긴다 (HTML 은 지운다).
CLI=/Users/kkh/.claude/skills/archify/bin/archify.mjs
cd "$(dirname "$0")"; : > render-slices.txt
for n in w01-v2-base w02-v1-base w06-v2-stack w07-v2-phase-group w36-mainpath-ok; do
  node "$CLI" render workflow in/$n.json out/$n.html >/dev/null 2>out/$n.rerr </dev/null; rc=$?
  echo "== $n exit=$rc" >>render-slices.txt
  grep -o '<svg viewBox[^>]*>' out/$n.html | head -1 >>render-slices.txt
  grep -o '<rect data-graph-role="structural-frame"[^>]*>' out/$n.html | head -6 >>render-slices.txt
  grep -o '<path data-edge-from[^>]*>' out/$n.html | head -3 | cut -c1-420 >>render-slices.txt
  grep -c 'data-node-id=' out/$n.html >>render-slices.txt
  rm -f out/$n.html
done
