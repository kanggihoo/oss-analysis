#!/usr/bin/env python3
"""resolvedCrossovers 신호가 켜지는(통과하면서 선이 교차하는) 아키텍처 입력을 찾는다.
web-app.architecture 의 pos 를 시드 고정 난수로 흔들고 deliver 후 check 의 composition.metrics 를 본다(브라우저 없음)."""
import json,random,subprocess,os,copy,sys
H=os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
A=['node','/Users/kkh/.claude/skills/archify/bin/archify.mjs']; env={**os.environ,'ARCHIFY_UPDATE_CHECK_DISABLED':'1'}
base=json.load(open('../rendering/in/web-app.architecture.json'))
random.seed(7); os.makedirs('work/xo',exist_ok=True); hits=[]
for i in range(int(sys.argv[1]) if len(sys.argv)>1 else 60):
    d=copy.deepcopy(base)
    for c in random.sample(d['components'],2):
        c['pos']=[c['pos'][0]+random.choice([-80,-40,40,80]),c['pos'][1]+random.choice([-60,60])]
    for c in d['components']: c['pos']=[max(10,c['pos'][0]),max(10,c['pos'][1])]
    d['meta'].pop('viewBox',None)
    for e in d['connections']:
        for k in('via','fromSide','toSide','labelAt','labelDx','labelDy','route'): e.pop(k,None)
    fn=f'work/xo/v{i}.architecture.json'; json.dump(d,open(fn,'w'),indent=1)
    out=f'work/xo/v{i}.html'
    r=subprocess.run(A+['deliver','architecture',fn,out,'--quality','showcase','--json'],capture_output=True,text=True,env=env)
    if r.returncode: continue
    ok_n=globals().get('ok_n',0)+1; globals()['ok_n']=ok_n
    c=subprocess.run(A+['check',out],capture_output=True,text=True,env=env)
    try: m=json.loads(c.stdout)['composition']['metrics']
    except Exception: continue
    s={k:m.get(k) for k in('resolvedCrossovers','routesOverSuggestedBends','routesOverSuggestedStretch')}
    if s['resolvedCrossovers']: hits.append((i,s)); print(i,s)
print('delivered',globals().get('ok_n',0),'hits',hits)
