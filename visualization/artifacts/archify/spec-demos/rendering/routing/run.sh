#!/bin/sh
# 설치본 CLI(레포와 바이트 동일)로 validate --layout-json 을 돌려 out/<name>.layout.json 과 요약(summary.txt)을 만든다.
CLI=/Users/kkh/.claude/skills/archify/bin/archify.mjs
cd "$(dirname "$0")"; mkdir -p out; : > summary.txt
for f in in/*.architecture.json; do
  b=$(basename "$f" .architecture.json)
  node "$CLI" validate architecture "$f" --layout-json >"out/$b.layout.json" 2>"out/$b.err" </dev/null; rc=$?
  python3 -I - "$b" "$rc" <<'PY' | tee -a summary.txt
import json,sys
b,rc=sys.argv[1:3]
try: d=json.load(open(f"out/{b}.layout.json"))
except Exception as e: print(b,"rc="+rc,"no-json"); sys.exit()
print(b,"rc="+rc,"ok="+str(d.get("ok")),"viewBox="+str(d.get("viewBox")))
for c in d.get("connections",[]):
    print("  %s->%s %s labelAt=%s"%(c["from"],c["to"],";".join("%g,%g"%tuple(p) for p in c["points"]),c.get("labelAt")))
for l in d.get("labels",[]): print("  label %s x=%g y=%g w=%g"%(l["text"],l["x"],l["y"],l["width"]))
if not d.get("ok"):
    for x in d.get("diagnostics",[]): print("  DIAG",x["code"],x["message"][:100])
PY
done
