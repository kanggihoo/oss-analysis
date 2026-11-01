#!/usr/bin/env python3
"""일부러 만든 실패 입력(변이)을 `archify validate --quality showcase --json`으로 돌려
진단 code 빈도와 supportedFixes 문장을 모은다. 시드 고정(재현 가능). 출력: out/sweep-*.{json,txt}"""
import json, random, subprocess, os, glob, copy, collections, sys
H=os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
A=['node','/Users/kkh/.claude/skills/archify/bin/archify.mjs']
random.seed(20261102)
seeds=sorted(glob.glob('../rendering/in/*.json'))+['../finalize/in/brand-aware-delivery.architecture.json','../finalize/in/release-delivery.workflow.json']
os.makedirs('work/sweep',exist_ok=True)
def walk(o,path=()):
    yield path,o
    if isinstance(o,dict):
        for k,v in o.items(): yield from walk(v,path+(k,))
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from walk(v,path+(i,))
def get(o,p):
    for k in p: o=o[k]
    return o
def mut(d,kind):
    d=copy.deepcopy(d); nodes=list(walk(d))
    if kind=='drop-key':
        c=[p for p,v in nodes if isinstance(v,dict) and p and len(v)>1]
        if not c: return None
        p=random.choice(c); v=get(d,p); k=random.choice(list(v)); del v[k]
    elif kind=='extra-key':
        c=[p for p,v in nodes if isinstance(v,dict)]
        p=random.choice(c); get(d,p)['colour']='red'
    elif kind=='wrong-type':
        c=[p for p,v in nodes if isinstance(v,(str,int,float)) and not isinstance(v,bool) and p and p[0] not in('schema_version',)]
        p=random.choice(c); parent=get(d,p[:-1]); parent[p[-1]]= 7 if isinstance(get(d,p),str) else 'x'
    elif kind=='jitter-pos':
        c=[p for p,v in nodes if p and p[-1]=='pos' and isinstance(v,list)]
        if not c: return None
        for p in random.sample(c,min(3,len(c))):
            v=get(d,p); v[0]+=random.choice([-120,-60,60,150]); v[1]+=random.choice([-90,-40,40,110])
    elif kind=='shrink-viewbox':
        v=d.get('meta',{}).get('viewBox')
        if not v: return None
        d['meta']['viewBox']=[int(v[0]*0.7),int(v[1]*0.8)]
    elif kind=='unknown-ref':
        for key in ('connections','edges','messages','transitions','flows','relationships'):
            if isinstance(d.get(key),list) and d[key]:
                e=random.choice(d[key])
                for f in ('to','target','dst'):
                    if f in e: e[f]=e[f]+'_typo'; return d
        return None
    elif kind=='long-label':
        c=[p for p,v in nodes if p and p[-1]=='label' and isinstance(v,str)]
        if not c: return None
        for p in random.sample(c,min(2,len(c))): get(d,p[:-1])['label']='Extremely long label text that does not fit in the box '*2
    elif kind=='dup-id':
        for key in ('connections','edges','messages','transitions','flows','relationships'):
            if isinstance(d.get(key),list) and len(d[key])>1 and 'id' in d[key][0]:
                d[key][1]['id']=d[key][0]['id']; return d
        return None
    return d
kinds=['drop-key','extra-key','wrong-type','jitter-pos','shrink-viewbox','unknown-ref','long-label','dup-id']
nofix=collections.Counter(); tally=collections.Counter(); bytype=collections.defaultdict(collections.Counter); fixes=collections.defaultdict(collections.Counter); ex={}
runs=0; passes=0
for s in seeds:
    base=json.load(open(s)); t=base['diagram_type']
    for kind in kinds:
        for rep in range(3):
            m=mut(base,kind)
            if m is None: break
            m.setdefault('meta',{}).pop('output',None) if False else None
            fn=f'work/sweep/{os.path.basename(s)[:-5]}.{kind}.{rep}.json'; json.dump(m,open(fn,'w'))
            r=subprocess.run(A+['validate',t,fn,'--quality','showcase','--json'],capture_output=True,text=True,env={**os.environ,'ARCHIFY_UPDATE_CHECK_DISABLED':'1'})
            runs+=1
            try: j=json.loads(r.stdout)
            except Exception: tally['<nojson exit %d>'%r.returncode]+=1; continue
            if j.get('ok'): passes+=1; continue
            for dg in j.get('diagnostics',[]):
                c=dg['code']; tally[c]+=1; bytype[t][c]+=1
                if not dg.get('supportedFixes'): nofix[c]+=1
                for f in dg.get('supportedFixes',[]): fixes[c][f]+=1
                ex.setdefault(c,{'type':t,'mutation':kind,'file':fn,'message':dg['message'][:200],'supportedFixes':dg.get('supportedFixes',[])})
out={'runs':runs,'passed':passes,'codes':tally.most_common(),'examples':ex}
json.dump(out,open('out/sweep-codes.json','w'),indent=1,ensure_ascii=False)
with open('out/sweep-summary.txt','w') as f:
    f.write(f'runs={runs} passed={passes}\n')
    for c,n in tally.most_common():
        f.write(f'{n:4d}  {c}  (supportedFixes 없음 {nofix[c]})  types={dict(bytype and {t:bytype[t][c] for t in bytype if bytype[t][c]})}\n')
        for fx,k in fixes[c].most_common(2): f.write(f'        fix: {fx[:170]}\n')
print(open('out/sweep-summary.txt').read())
