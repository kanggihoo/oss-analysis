# 라우팅 스펙용 최소 입력 생성. 사용: python3 -I gen.py  (이 폴더에서) -> in/*.architecture.json
import json
def mk(name, comps, conns, meta=None, extra=None):
    d = {"schema_version": 1, "diagram_type": "architecture",
         "meta": {"title": name, "output": name + ".html", **(meta or {})},
         "components": [{"id": i, "type": "backend", "label": i.upper(), "pos": [c[0], c[1]],
                         **({"size": [c[2], c[3]]} if len(c) > 2 else {})} for i, c in comps.items()],
         "connections": conns}
    if extra: d.update(extra)
    json.dump(d, open(f"in/{name}.architecture.json", "w"), indent=1)
C = lambda f, t, **k: {"from": f, "to": t, **k}
mk("r01-facing", {"a": (40, 40), "b": (240, 40)}, [C("a", "b")])
mk("r02-offset-h", {"a": (40, 40), "b": (240, 100)}, [C("a", "b")])
mk("r03-vertical-dogleg", {"a": (40, 40), "b": (60, 200)}, [C("a", "b")])
mk("r04-vertical-snap", {"a": (40, 40), "b": (50, 200)}, [C("a", "b")])
mk("r05-fanout", {"h": (200, 40), "x": (40, 220), "y": (200, 220), "z": (360, 220)}, [C("h", "x"), C("h", "y"), C("h", "z")])
mk("r06-blocked-grid", {"a": (40, 100), "m": (240, 100), "c": (440, 100)}, [C("a", "c")])
mk("r07-reciprocal-aligned", {"a": (40, 40), "b": (240, 40)}, [C("a", "b"), C("b", "a")])
mk("r08-reciprocal-offset", {"a": (40, 40), "b": (240, 70)}, [C("a", "b"), C("b", "a")])
mk("r09-explicit-sides", {"a": (40, 40), "b": (240, 200)}, [C("a", "b", fromSide="bottom", toSide="top")])
mk("r10-order-by-distance", {"a": (40, 40), "b": (240, 40), "c": (440, 40)}, [C("a", "c"), C("a", "b")])
mk("r11-label-shared", {"a": (40, 40), "b": (240, 100), "c": (440, 160)}, [C("a", "b", label="one"), C("b", "c", label="two")])

# 라벨: 긴 라벨이 짧은 틈(40px)에 놓인 경우. 프로파일별 비교용 3종.
for q in (None, "standard", "showcase"):
    mk("l01-label-gap" + ("" if q is None else "-" + q), {"a": (40, 40), "b": (200, 40)},
       [C("a", "b", label="LONGLABELTEXT")], meta=({} if q is None else {"quality_profile": q}))
# 겹침 교차(대각선 두 연결)
mk("r12-crossing", {"a": (40, 40), "b": (240, 200), "c": (240, 40), "d": (40, 200)}, [C("a", "b"), C("c", "d")])
# 경계 프레임이 있는 경우(프레임 테두리를 따라 달리는 경로 금지)
mk("r13-boundary", {"a": (60, 80), "b": (260, 80), "c": (460, 80)}, [C("a", "c")],
   extra={"boundaries": [{"kind": "region", "label": "Zone", "wraps": ["a", "b"]}]})

# 라벨 충돌: 서로 반대 방향 연결 두 개(포트 14px 간격)에 라벨
for q in (None, "showcase"):
    mk("l02-reciprocal-labels" + ("" if q is None else "-" + q), {"a": (40, 40), "b": (280, 40)},
       [C("a", "b", label="request"), C("b", "a", label="response")], meta=({} if q is None else {"quality_profile": q}))
# 라벨이 다른 연결선 위를 지나는 경우: 위쪽 연결의 라벨 기본 위치가 아래 연결선과 겹침
for q in (None, "showcase"):
    mk("l03-label-vs-route" + ("" if q is None else "-" + q), {"a": (40, 40), "b": (280, 40), "c": (40, 62), "d": (280, 62)},
       [C("a", "b", label="LABEL ONE"), C("c", "d")], meta=({} if q is None else {"quality_profile": q}))

# 아래 여백 24px: 교차가 남은 연결만 장면 아래 24px 안쪽 통로를 쓸 수 있다(자동 viewBox일 때). 같은 입력에 meta.viewBox 를 주면 쓸 수 없다.
_b = ({"a": (440, 170), "b": (640, 170), "c": (240, 300), "d": (40, 300)}, [C("a", "c"), C("b", "a"), C("b", "d")])
mk("r14-bottom-margin", *_b)
mk("r14-bottom-margin-fixedvb", *_b, meta={"viewBox": [800, 400]})

# 선 굵기가 포트 간격을 키운다: 두 연결 width 6 -> 간격 max(14, 3.5*(6+6)+3.5)=45.5
mk("r15-port-width", {"h": (200, 40), "x": (100, 220), "y": (300, 220)}, [C("h", "x", width=6), C("h", "y", width=6)])
# 자기 연결과 끝점 없는 연결
mk("r16-self-and-unknown", {"a": (40, 40), "b": (240, 40)}, [C("a", "a"), C("a", "zzz"), C("a", "b")])
# 포트 정렬: 대상 중심 y 오름차순으로 위쪽 포트부터
mk("r17-port-order", {"h": (40, 120), "u": (300, 20), "m": (300, 130), "d": (300, 240)}, [C("h", "d"), C("h", "u"), C("h", "m")])

# 같은 입력에 labelDx:0 을 붙인 "-greedy" 변형: labelDx 가 있으면 개선 스윕이 건드리지 않으므로(hasAuthoredLabelPlacement)
# 1차 계획(computePath)의 결과만 관찰된다. 포트 퍼뜨림은 labelAt 만 건너뛰므로 labelDx 는 그대로 퍼뜨린다.
import glob
for f in sorted(glob.glob("in/r*.architecture.json")):
    if "-greedy" in f or "explicit" in f: continue
    d = json.load(open(f)); n = d["meta"]["title"]
    for c in d["connections"]: c["labelDx"] = 0
    d["meta"]["title"] = n + "-greedy"; d["meta"]["output"] = n + "-greedy.html"
    json.dump(d, open(f.replace(".architecture.json", "-greedy.architecture.json"), "w"), indent=1)

