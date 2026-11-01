# 레포 examples 의 architecture 5개를 meta.quality_profile = (없음|standard|showcase)로 바꿔 layout-json 의 라우트·라벨·viewBox 가 같은지 비교한다.
# 사용: python3 -I profile-compare.py > summary-profiles.txt   (설치본 CLI 사용, 레포 코드는 실행하지 않음)
import json, glob, subprocess, os, tempfile
EX = "/Users/kkh/Desktop/oss-analysis/visualization/repos/archify/archify/examples"
CLI = "/Users/kkh/.claude/skills/archify/bin/archify.mjs"
for f in sorted(glob.glob(EX + "/*.architecture.json")):
    b = os.path.basename(f).replace(".architecture.json", "")
    res = {}
    for q in ("none", "standard", "showcase"):
        d = json.load(open(f))
        if q == "none": d["meta"].pop("quality_profile", None)
        else: d["meta"]["quality_profile"] = q
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t: json.dump(d, t)
        r = subprocess.run(["node", CLI, "validate", "architecture", t.name, "--layout-json"], capture_output=True, text=True)
        os.unlink(t.name)
        res[q] = json.loads(r.stdout)
    same = all(res[q]["connections"] and [c["points"] for c in res[q]["connections"]] == [c["points"] for c in res["none"]["connections"]] for q in res)
    lab = all(res[q]["labels"] == res["none"]["labels"] for q in res)
    print(b, "connections=%d" % len(res["none"]["connections"]), "ok=%s" % [res[q]["ok"] for q in res],
          "route_points_equal_across_profiles=%s" % same, "labels_equal=%s" % lab, "viewBox=%s" % res["none"]["viewBox"])
