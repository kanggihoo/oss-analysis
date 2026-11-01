# workflow 스펙 수락 사례용 입력 생성기. 사용: python3 -I make-inputs.py  (이 폴더에서)
import json, copy, os
os.makedirs('in', exist_ok=True)
def base(v=2, **meta):
    d = {"schema_version": v, "diagram_type": "workflow",
         "meta": {"title": "W", "output": "w.html", **meta},
         "lanes": [{"id": "L1", "label": "Lane one"}, {"id": "L2", "label": "Lane two"}],
         "nodes": [
           {"id": "a", "lane": "L1", "col": 0, "type": "frontend", "label": "A"},
           {"id": "b", "lane": "L1", "col": 1, "type": "backend", "label": "B"},
           {"id": "c", "lane": "L2", "col": 2, "type": "database", "label": "C"}],
         "edges": [{"from": "a", "to": "b", "label": "go"}, {"from": "b", "to": "c"}]}
    return d
def w(name, d): json.dump(d, open(f'in/{name}.json', 'w'), indent=1)

w('w01-v2-base', base(2))
w('w02-v1-base', base(1))
# v1 column capacity: same lane col 1 and 2 (80px apart, widths 92)
d = base(1); d['nodes'][1]['col'] = 1; d['nodes'][2].update(lane='L1', col=2); d['edges'] = [{"from": "b", "to": "c"}]
w('w03-v1-column-capacity', d)
# v2 same shape: no capacity problem
d2 = copy.deepcopy(d); d2['schema_version'] = 2; w('w04-v2-same-shape', d2)
# v2 long direct label between same-lane neighbours
d = base(2); d['edges'][0]['label'] = 'a rather long relationship label'
w('w05-v2-long-label', d)
# v2 long label with labelAt unset but fromSide set -> no channel preference
# v2 vertical stack (independent lane measurement)
d = {"schema_version": 2, "diagram_type": "workflow", "meta": {"title": "stack", "output": "s.html"},
     "lanes": [{"id": "cage", "label": "one cage"}],
     "groups": [{"id": "g", "label": "cage", "lane": "cage", "fromCol": 1, "toCol": 3}],
     "nodes": [{"id": k, "lane": "cage", "col": 2, "type": "security", "label": "stage" + k.upper(), "yOffset": y} for k, y in (("a", -90), ("b", 0), ("c", 90))],
     "edges": [{"from": "a", "to": "b", "fromSide": "bottom", "toSide": "top"}, {"from": "b", "to": "c", "fromSide": "bottom", "toSide": "top"}]}
w('w06-v2-stack', d)
# phases + groups widen columns
d = base(2); d['phases'] = [{"id": "p", "label": "A very long phase label for one column", "fromCol": 0, "toCol": 0}]
d['groups'] = [{"id": "g", "label": "Group label that is long", "lane": "L1", "fromCol": 1, "toCol": 1}]
w('w07-v2-phase-group', d)
# explicit pin conflict: labelAt on node a
d = base(2); d['edges'][0]['labelAt'] = [94, 120]
w('w10-pin-labelat-on-node', d)
# route preset conflict: drop between same-lane nodes
d = base(2); d['edges'][0]['route'] = 'drop'
w('w11-preset-drop-same-lane', d)
# viewbox capacity
d = base(2, viewBox=[700, 240]); w('w12-viewbox-capacity', d)
# explicit via with non-orthogonal point
d = base(2); d['edges'][1]['via'] = [[300, 200]]
w('w13-pin-via-diagonal', d)
# semantic checks
d = base(2); d['semanticChecks'] = {"allowedRoots": ["b"], "allowedTerminals": ["c"], "requiredEdges": [{"from": "c", "to": "a"}], "requiredPaths": [{"from": "c", "to": "a"}]}
w('w14-semantic', d)
d = base(2); d['semanticChecks'] = {"allowedRoots": ["zzz"]}; w('w15-semantic-unknown-node', d)
# node overlap same lane same col
d = base(2); d['nodes'][1]['col'] = 0; d['edges'] = [{"from": "a", "to": "c"}]
w('w16-node-overlap', d)
# layout/constraint problems: mainPath backward, empty group, phase overlap
d = base(2); d['mainPath'] = ['b', 'a']; d['groups'] = [{"id": "g", "label": "G", "lane": "L2", "fromCol": 0, "toCol": 0}]
d['phases'] = [{"id": "p1", "label": "P1", "fromCol": 0, "toCol": 1}, {"id": "p2", "label": "P2", "fromCol": 1, "toCol": 2}]
w('w17-constraint-problems', d)
# crossing: 자동 라우트 두 개가 서로 엇갈리는 배치 (a->d, b->c), standard vs showcase
d = {"schema_version": 2, "diagram_type": "workflow", "meta": {"title": "X", "output": "x.html"},
     "lanes": [{"id": "L1", "label": "Top"}, {"id": "L2", "label": "Bottom"}],
     "nodes": [{"id": "a", "lane": "L1", "col": 0, "type": "frontend", "label": "A"},
               {"id": "b", "lane": "L1", "col": 1, "type": "frontend", "label": "B"},
               {"id": "c", "lane": "L2", "col": 0, "type": "backend", "label": "C"},
               {"id": "d", "lane": "L2", "col": 1, "type": "backend", "label": "D"}],
     "edges": [{"id": "e1", "from": "a", "to": "d"}, {"id": "e2", "from": "b", "to": "c"}]}
w('w18-crossing-auto-standard', d)
d['meta']['quality_profile'] = 'showcase'; w('w19-crossing-auto-showcase', d)
# sublabel readability showcase: wide automatic canvas with long sublabel on narrow-ish node
d = base(2, quality_profile='showcase')
d['nodes'][0]['sublabel'] = 'a very long sublabel that cannot fit in the node at all really'
w('w20-sublabel-showcase', d)
# unknown endpoints / invalid column / duplicate id
d = base(2); d['edges'][1]['to'] = 'zz'; w('w21-unknown-endpoint', d)
d = base(2); d['nodes'][2]['lane'] = 'nope'; w('w22-unknown-lane', d)
d = base(2); d['nodes'][2]['id'] = 'a'; w('w23-duplicate-node', d)
d = base(2); d['nodes'][2]['col'] = 9; w('w24-col-out-of-range', d)
# authored sides impossible: a(left)->b(right) where b right of a? fromSide left toSide right with b to the right
d = base(2); d['edges'][0].update(fromSide='left', toSide='right')
w('w25-authored-sides', d)
# cross-lane routes: auto, drop, return-left, outside-right
d = {"schema_version": 2, "diagram_type": "workflow", "meta": {"title": "R", "output": "r.html"},
     "lanes": [{"id": "L1", "label": "Top"}, {"id": "L2", "label": "Bottom"}],
     "nodes": [{"id": "a", "lane": "L1", "col": 1, "type": "frontend", "label": "A"},
               {"id": "b", "lane": "L2", "col": 3, "type": "backend", "label": "B"},
               {"id": "c", "lane": "L2", "col": 4, "type": "database", "label": "C"}],
     "edges": [{"id": "auto", "from": "a", "to": "b", "label": "auto"},
               {"id": "drop", "from": "a", "to": "c", "route": "drop", "bias": 0.25},
               {"id": "ret", "from": "b", "to": "a", "route": "return-left", "role": "return"}]}
w('w26-routes', d)
d['edges'] = [{"id": "o", "from": "a", "to": "b", "route": "outside-right"}, {"id": "bc", "from": "b", "to": "c", "route": "bottom-channel"}, {"id": "uc", "from": "c", "to": "a", "route": "up-channel"}]
w('w27-presets', d)
# v1 viewBox auto height
d = base(1); d['lanes'] = d['lanes'] + [{"id": "L3", "label": "three"}]; w('w28-v1-three-lanes', d)
# v2 node auto width
d = base(2); d['nodes'][0]['label'] = 'A fairly long node label'; d['nodes'][1]['sublabel'] = 'a sublabel of some length here'
w('w29-auto-width', d)
# v2 pinned via on cross lane keeps absolute pins (8px clearance rank)
d = base(2); d['edges'][1]['via'] = [[284, 119], [284, 243]]; w('w30-pinned-via-ok', d)
# lane header shift: top-side endpoint on col 0 with long lane label
d = base(2); d['lanes'][0]['label'] = 'A very long lane label for header shift'
d['edges'] = [{"from": "a", "to": "c", "fromSide": "top", "toSide": "top"}]
w('w31-lane-header-shift', d)

# lane-gap feedback: 위 레인 bottom -> 아래 레인 top 으로 열이 다른 노드 (laneGap 20 에서는 코리도 불가)
d = {"schema_version": 2, "diagram_type": "workflow", "meta": {"title": "G", "output": "g.html"},
     "lanes": [{"id": "L1", "label": "Top"}, {"id": "L2", "label": "Bottom"}],
     "nodes": [{"id": "a", "lane": "L1", "col": 0, "type": "frontend", "label": "A"},
               {"id": "d", "lane": "L2", "col": 3, "type": "backend", "label": "D"}],
     "edges": [{"id": "e", "from": "a", "to": "d", "fromSide": "bottom", "toSide": "top"}]}
w('w32-lane-gap-feedback', d)
d = copy.deepcopy(d); d['edges'] = [{"id": "self", "from": "a", "to": "a"}]; w('w33-self-loop', d)
# sublabel readability: 넓은 캔버스(phase 라벨) + showcase + 저자 폭 92 + 23자 sublabel
d = base(2, quality_profile='showcase')
d['phases'] = [{"id": "p", "label": "A very long phase label for one column", "fromCol": 0, "toCol": 0}]
d['groups'] = [{"id": "g", "label": "Group label that is long", "lane": "L1", "fromCol": 1, "toCol": 1}]
d['nodes'][0].update(width=92, sublabel='abcdefghijklmnopqrstuvw')
w('w34-sublabel-readability', d)
d2 = copy.deepcopy(d); del d2['nodes'][0]['width']; w('w35-sublabel-auto-widen', d2)
d = base(2); d['mainPath'] = ['a', 'b', 'c']; w('w36-mainpath-ok', d)

# 핀으로 만든 진짜 교차: 열 [94,214,334,454] (핀이 있으면 기본 피치 120, 8px 간격 규칙)
d = {"schema_version": 2, "diagram_type": "workflow", "meta": {"title": "X", "output": "x.html"},
     "lanes": [{"id": "L1", "label": "Top"}, {"id": "L2", "label": "Bottom"}],
     "nodes": [{"id": "a", "lane": "L1", "col": 1, "type": "frontend", "label": "A"},
               {"id": "b", "lane": "L1", "col": 2, "type": "frontend", "label": "B"},
               {"id": "c", "lane": "L2", "col": 1, "type": "backend", "label": "C"},
               {"id": "d", "lane": "L2", "col": 3, "type": "backend", "label": "D"}],
     "edges": [{"id": "e1", "from": "a", "to": "d", "fromSide": "bottom", "toSide": "top", "via": [[214, 165], [454, 165]]},
               {"id": "e2", "from": "b", "to": "c", "fromSide": "bottom", "toSide": "top", "via": [[334, 170], [214, 170]]}]}
w('w37-pinned-crossing-standard', d)
d['meta']['quality_profile'] = 'showcase'; w('w38-pinned-crossing-showcase', d)
# rank-gap feedback 후보: 같은 레인 인접 열, yOffset 이 달라 direct 직선이 아니고 bend 가 필요
d = {"schema_version": 2, "diagram_type": "workflow", "meta": {"title": "F", "output": "f.html"},
     "lanes": [{"id": "L1", "label": "One"}],
     "nodes": [{"id": "a", "lane": "L1", "col": 0, "type": "frontend", "label": "A", "yOffset": -30},
               {"id": "b", "lane": "L1", "col": 1, "type": "backend", "label": "B", "yOffset": 30}],
     "edges": [{"id": "e", "from": "a", "to": "b", "fromSide": "right", "toSide": "left"}]}
w('w39-rank-gap-candidate', d)

# v1 절대 좌표 via 를 가진 문서 (migrate 사례)
d = base(1); d['edges'][1].update(fromSide='bottom', toSide='top', via=[[220, 166], [300, 166]])
w('w40-v1-via', d)

# 명시 viewBox: 충분히 크면 그대로, 핀이 없어도 nodeClearance 는 8 (viewBox 가 있으면 absolute-geometry 정책)
d = base(2, viewBox=[900, 500]); w('w41-explicit-viewbox-ok', d)
d = base(1, viewBox=[700, 300]); w('w42-v1-viewbox-small', d)

# v1 에서 같은 진단이 어떤 code 로 나가는지
d = base(1); d['edges'][1]['to'] = 'zz'; w('w43-v1-unknown-endpoint', d)
d = base(1); d['nodes'][1]['col'] = 0; d['edges'] = [{"from": "a", "to": "c"}]; w('w44-v1-node-overlap', d)
d = base(1); d['nodes'][2]['lane'] = 'nope'; w('w45-v1-unknown-lane', d)
