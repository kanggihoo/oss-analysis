# layout JSON 또는 stderr JSON에서 핵심 값만 뽑는다. 사용: python3 -I summarize.py <receipt.json>
import json, sys
r = json.load(open(sys.argv[1]))
out = {"contract": r.get("contract"), "ok": r.get("ok", True), "viewBox": r.get("viewBox"), "requiredViewBox": r.get("requiredViewBox"), "columns": r.get("columns")}
out["nodes"] = [(n["id"], n["col"], n["x"], n["y"], n["width"], n["height"]) for n in r.get("nodes", [])]
out["edges"] = [(e["id"] or f'{e["from"]}->{e["to"]}', e["points"]) for e in r.get("edges", [])]
out["labels"] = [(l["label"], l["x"], l["y"], l["width"]) for l in r.get("labels", [])]
out["diagnostics"] = [(d["code"], d["severity"], d["message"][:110]) for d in r.get("diagnostics", [])]
print(json.dumps(out, ensure_ascii=False))
