#!/usr/bin/env python3
"""Boundary of label_route_clearance: label mask rect of 'brief' is x 181..215, y 274..288.
A vertical route at x=215+g gives clearance g. Showcase threshold 4px, standard 2px (error only in showcase)."""
import subprocess, json, os, shutil
HERE=os.path.dirname(os.path.abspath(__file__)); W=f'{HERE}/work'
A=['node','/Users/kkh/.claude/skills/archify/bin/archify.mjs']
h=open(f'{HERE}/out/brand-aware-delivery.architecture.html',encoding='utf8').read()
def edge(s,eid,old,new):
    i=s.index(f'data-edge-id="{eid}"'); i=s.rindex('<path',0,i); j=s.index('/>',i)
    assert old in s[i:j]; return s[:i]+s[i:j].replace(old,new)+s[j:]
for prof in ('showcase','standard'):
  for g in (1.9,2,3.9,4,4.1):
    x=215+g
    s=edge(h,'github-to-container','d="M 540 294 L 584 294"',f'd="M {x} 250 L {x} 340"')
    s=edge(s,'github-to-container','data-composition-crossover="halo"','')
    s=edge(s,'github-to-container','data-composition-points="540,294;584,294"',f'data-composition-points="{x},250;{x},340"')
    s=s.replace('data-quality-profile="showcase"',f'data-quality-profile="{prof}"',1)
    p=f'{W}/lc_{prof}_{g}.html'; open(p,'w',encoding='utf8').write(s)
    r=subprocess.run(A+['check',p],capture_output=True,text=True); j=json.loads(r.stdout)
    lc=[i for i in j['composition']['issues'] if i['code']=='composition/label-route-clearance']
    print(prof,'gap',g,'exit',r.returncode,'label-route-clearance issues:',[(i['severity'],i['clearance'],i['threshold']) for i in lc])
