#!/usr/bin/env python3
"""c2: 진단의 supportedFixes 중 'move component "<id>" pos to [x, y]' 문장을 그대로 적용한다(에이전트가 fix를 따르는 것을 흉내).
사용: apply_c2.py <bad.json> <summary.json> <fixed.json>"""
import json,re,sys
bad,summ,out=sys.argv[1:]
d=json.load(open(bad)); s=json.load(open(summ)); applied=[]
for x in s['diagnostics']:
    for f in x.get('supportedFixes',[]):
        m=re.match(r'(?:or )?move component "([^"]+)" pos to \[(\d+), (\d+)\]',f)
        if m and not applied:
            cid,px,py=m.group(1),int(m.group(2)),int(m.group(3))
            for c in d['components']:
                if c['id']==cid: c['pos']=[px,py]
            applied.append(f)
json.dump(d,open(out,'w'),indent=2,ensure_ascii=False); print('applied:',applied)
