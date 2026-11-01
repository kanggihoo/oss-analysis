#!/usr/bin/env python3
"""c2 3회차: supportedFixes 가 비어 있고 메시지에 'Suggested fix: set labelAt [x, y]'가 있다(nextAction.constraint 가 'or the fix its message names'라고 지시).
라벨이 겹친 연결의 labelAt 에 그 좌표를 넣는다. 사용: apply_c2_label.py <in.json> <summary.json> <out.json>"""
import json,re,sys
src,summ,out=sys.argv[1:]
d=json.load(open(src)); s=json.load(open(summ))
msg=s['diagnostics'][0]['message']
label=re.search(r'Label "([^"]+)"',msg).group(1); xy=re.search(r'set labelAt \[(\d+), (\d+)\]',msg)
for e in d['connections']:
    if e.get('label')==label: e['labelAt']=[int(xy.group(1)),int(xy.group(2))]; e.pop('labelDy',None); print('labelAt set on',e['id'],e['labelAt'])
json.dump(d,open(out,'w'),indent=2,ensure_ascii=False)
