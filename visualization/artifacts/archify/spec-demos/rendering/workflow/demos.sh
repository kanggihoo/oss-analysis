#!/bin/sh
# workflow 스펙 실행 확인. 설치본 archify(레포와 바이트 동일)만 쓴다. 사용: sh demos.sh (이 폴더에서)
CLI=/Users/kkh/.claude/skills/archify/bin/archify.mjs
cd "$(dirname "$0")"; mkdir -p out; : > summary.txt
python3 -I make-inputs.py
for f in in/*.json; do
  b=$(basename "$f" .json)
  node "$CLI" validate workflow "$f" --layout-json >"out/$b.json" 2>"out/$b.err" </dev/null; rc=$?
  echo "== $b exit=$rc" >>summary.txt
  if [ -s "out/$b.json" ]; then python3 -I summarize.py "out/$b.json" >>summary.txt 2>&1; else echo "(no stdout) $(head -c 300 out/$b.err | tr '\n' ' ')" >>summary.txt; fi
done
