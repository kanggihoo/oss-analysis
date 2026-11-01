#!/usr/bin/env python3
"""Tamper with a delivered architecture HTML and run `check` (installed archify, byte-identical to repo archify/).
Cases without sidecar: provenance status is 'unknown' (passes unless --require-provenance)."""
import re, subprocess, json, shutil, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
A = ['node', '/Users/kkh/.claude/skills/archify/bin/archify.mjs']
SRC = f'{HERE}/out/brand-aware-delivery.architecture.html'
W = f'{HERE}/work'; shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
h = open(SRC, encoding='utf8').read()

def edge(s, edge_id, old, new):
    """replace `old` only inside the marker-end <path> of the given data-edge-id (the underlay <path> has the same d)."""
    i = s.index(f'data-edge-id="{edge_id}"'); i = s.rindex('<path', 0, i); j = s.index('/>', i)
    assert old in s[i:j], old
    return s[:i] + s[i:j].replace(old, new) + s[j:]

def sub1(s, old, new):
    assert s.count(old) >= 1, old
    return s.replace(old, new, 1)

arrow0 = 'd="M 176 294 L 220 294"'
arrow2 = 'd="M 540 294 L 584 294"'
cases = {}
cases['diagonal'] = edge(h, 'brief-to-claude', arrow0, 'd="M 176 294 L 220 300"')
# arrow2 (github->container) becomes a vertical line crossing arrow0 (request->claude) at x=200; strip its halo marker
a2 = edge(h, 'github-to-container', arrow2, 'd="M 200 250 L 200 340"')
a2 = edge(a2, 'github-to-container', 'data-composition-crossover="halo"', '')
a2 = edge(a2, 'github-to-container', 'data-composition-points="540,294;584,294"', 'data-composition-points="200,250;200,340"')
cases['crossing_showcase'] = a2
cases['crossing_standard'] = sub1(cases['crossing_showcase'], 'data-quality-profile="showcase"', 'data-quality-profile="standard"')
cases['font_7.2'] = sub1(h, 'x="289" y="292" class="t-primary" font-size="11"', 'x="289" y="292" class="t-primary" font-size="7.2"')
cases['font_7.3'] = sub1(h, 'x="289" y="292" class="t-primary" font-size="11"', 'x="289" y="292" class="t-primary" font-size="7.3"')
cases['nan_attr'] = sub1(h, '<rect x="220" y="260" width="138" height="68" rx="8" class="c-mask"/>', '<rect x="NaN" y="260" width="138" height="68" rx="8" class="c-mask"/>')
cases['two_svg'] = h.replace('</body>', '<svg viewBox="0 0 1 1"></svg></body>', 1)
# node overlap: move GitHub node mask+body rect onto Claude (x 402 -> 250). check has no node-overlap rule.
cases['node_overlap'] = h.replace('<rect x="402" y="260"', '<rect x="250" y="260"')
cases['label_mask_far_right'] = h  # placeholder removed below
del cases['label_mask_far_right']

rows = []
for name, html in cases.items():
    p = f'{W}/{name}.html'; open(p, 'w', encoding='utf8').write(html)
    r = subprocess.run(A + ['check', p], capture_output=True, text=True)
    try: j = json.loads(r.stdout)
    except Exception: j = {'raw': r.stdout[:300]}
    failed = [c['name'] for c in j.get('checks', []) if not c['ok']]
    comp = j.get('composition', {})
    codes = [(i['severity'], i['code']) for i in comp.get('issues', [])]
    rows.append((name, r.returncode, j.get('ok'), failed, comp.get('summary'), codes, j.get('provenance')))
    json.dump(j, open(f'{W}/{name}.check.json', 'w'), indent=1)
for r in rows: print(r)
