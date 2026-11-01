# R-16·R-17·R-18 치수 예산이 실제로 어느 단계에서 걸리는지 관찰. python3 -I run.py > run.out.txt
# 설치본 archify(render → check, validate --layout-json)만 쓴다. HTML은 만들고 즉시 지운다.
import json, subprocess, os, re
CLI='/Users/kkh/.claude/skills/archify/bin/archify.mjs'
os.makedirs('out', exist_ok=True)
def comp(i, x, y, w=120, h=60, t='backend', **k): return {'id':i,'type':t,'label':i.upper(),'pos':[x,y],'size':[w,h],**k}
def arch(comps, conns, **m):
    return {'schema_version':1,'diagram_type':'architecture','meta':{'title':'B','output':'x.html',**m},'components':comps,'connections':conns}
def sh(args): return subprocess.run(['node',CLI]+args,capture_output=True,text=True,stdin=subprocess.DEVNULL)
def run(name, doc, quality, show_points=False):
    p='out/%s.json'%name; json.dump(doc, open(p,'w')); html='out/%s.html'%name
    r=sh(['render','architecture',p,html,'--quality',quality])
    rcodes=sorted(set(re.findall(r'\[([a-z-]+/[a-z-]+)\]', r.stderr)))
    line='%-22s %-8s render rc=%d %s'%(name,quality,r.returncode,rcodes)
    if r.returncode==0:
        vb=re.search(r'<svg viewBox="([^"]*)"',open(html).read()).group(1)
        c=sh(['check',html,'--json']); d=json.loads(c.stdout)
        iss=[(x['code'],x['severity']) for x in d['composition']['issues']]
        met=d['composition']['metrics']
        line+=' | vb=%s check rc=%d issues=%s minProjected=%s'%(vb,c.returncode,iss,round(met['minProjectedNodeTextPx'],2) if met.get('minProjectedNodeTextPx') else None)
        os.remove(html)
    print(line)
    if show_points:
        l=sh(['validate','architecture',p,'--layout-json','--quality',quality])
        try:
            d=json.loads(l.stdout)
            print('    ports:',[ (c.get('from'),[ '%g,%g'%tuple(q) for q in c['points']]) for c in d['connections']])
        except Exception as e: print('    layout-json unavailable',l.stdout[:80],l.stderr[:120])
print('## E1 포트 예산 32+14(k-1): 허브 왼쪽 변에 k개, 라벨 없음. 변 길이 H')
for k,H in [(4,74),(4,66),(4,50),(5,88),(5,80)]:
    comps=[comp('hub',300,200,120,H)]+[comp('s%d'%i,20,20+i*70,100,40) for i in range(k)]
    run('fan_k%d_H%d'%(k,H), arch(comps,[{'from':'s%d'%i,'to':'hub'} for i in range(k)]),'showcase',True)
print('## E1b 같은 조건 + 모든 연결에 toSide:left 고정(라우터가 변을 못 바꿈)')
for k,H in [(4,74),(4,66),(4,62),(4,58),(4,56),(4,54),(4,52),(4,50),(4,40)]:
    comps=[comp('hub',300,200,120,H)]+[comp('s%d'%i,20,20+i*70,100,40) for i in range(k)]
    run('pin_k%d_H%d'%(k,H), arch(comps,[{'from':'s%d'%i,'to':'hub','toSide':'left'} for i in range(k)]),'showcase',True)
print('## E2 라벨 간격 6.5*단위+21: 라벨 approve-order(13단위, 권고 105.5px), 가로 인접 두 노드 간격 g')
for g in [60,66,70,72,74,76,80,106]:
    run('gap_%d'%g, arch([comp('a',40,100),comp('b',40+120+g,100)],[{'from':'a','to':'b','label':'approve-order'}]),'showcase')
print('## E3 캔버스 폭·비율: 가로 줄 n개(120폭, 간격 g, 좌우 40), 라벨 8px. 비율<1.55면 1240, >=1.55면 1790 근처')
def row(n,g,tall=0):
    comps=[comp('n%d'%i,40+i*(120+g),40) for i in range(n)]
    if tall: comps.append(comp('tall',40,40+tall,120,60))
    return arch(comps,[{'from':'n%d'%i,'to':'n%d'%(i+1),'label':'go'} for i in range(n-1)])
for name,doc in [('lowratio_1236',row(8,28,800)),('lowratio_1243',row(8,29,800)),('wide_1790',row(11,39)),('wide_1800',row(11,40))]:
    for q in ['showcase','standard']: run(name,doc,q)
print('## E4 프로파일별: 같은 입력을 standard로 / 실패 문장 첫 줄')
comps=[comp('hub',300,200,120,50)]+[comp('s%d'%i,20,20+i*70,100,40) for i in range(4)]
run('pin_k4_H50', arch(comps,[{'from':'s%d'%i,'to':'hub','toSide':'left'} for i in range(4)]),'standard')
run('gap_66', arch([comp('a',40,100),comp('b',40+120+66,100)],[{'from':'a','to':'b','label':'approve-order'}]),'standard')
for n in ['pin_k4_H50','gap_66']:
    r=sh(['render','architecture','out/%s.json'%n,'out/t.html','--quality','showcase'])
    print('  ',n,'showcase 첫 문장:',(r.stderr.strip().splitlines() or [''])[1][:230])
if os.path.exists('out/t.html'): os.remove('out/t.html')
print('## E5 부제 예산 5.4*단위+8: 부제 20단위(권고 116px)를 폭 w 노드에, 9px 선호')
for w in [120,116,100,80,70,60]:
    doc=arch([comp('a',40,40,w,60,sublabel='abcdefghijklmnopqrst'),comp('b',40+w+80,40,w,60)],[{'from':'a','to':'b','label':'go'}])
    p='out/sub_%d.json'%w; json.dump(doc,open(p,'w'))
    r=sh(['render','architecture',p,'out/t.html','--quality','showcase'])
    if r.returncode==0:
        s=open('out/t.html').read(); fs=re.findall(r'data-detail="context"[^>]*font-size="([\d.]+)"[^>]*>abcdefghijklmnopqrst',s)
        print('  w=%d render rc=0 sublabel font-size=%s'%(w,fs))
        c=sh(['check','out/t.html','--json']); print('     check rc=%d issues=%s'%(c.returncode,[(x['code'],x['severity']) for x in json.loads(c.stdout)['composition']['issues']]))
    else: print('  w=%d render rc=%d %s'%(w,r.returncode,(r.stderr.strip().splitlines() or [''])[1][:200]))
    if os.path.exists('out/t.html'): os.remove('out/t.html')
print('## E6 finalize 영수증: 1243px 저비율(showcase) / 앞쪽 여백 큰 배치 / 정상')
def fin(name, doc, quality='showcase'):
    p='out/%s.json'%name; json.dump(doc,open(p,'w'))
    r=sh(['finalize','architecture',p,'out/%s.html'%name,'--quality',quality,'--json','--out-dir','out/fin-%s'%name])
    try: d=json.loads(r.stdout)
    except Exception: print('  ',name,'rc=%d unparsable'%r.returncode, r.stderr[:160]); return
    print('  %-16s %-8s rc=%d ok=%s stage=%s keys=%s'%(name,quality,r.returncode,d.get('ok'),d.get('failedStage') or d.get('stage'),sorted(d.keys())[:12]))
    for k in ('layoutReviewRecommendation','diagnostics'):
        if d.get(k): print('     ',k,json.dumps(d[k])[:420])
fin('lowratio_1243', row(8,29,800))
fin('lowratio_1243', row(8,29,800),'standard')
fin('leading_space', arch([comp('a',400,300),comp('b',600,300)],[{'from':'a','to':'b','label':'go'}]))
fin('plain', arch([comp('a',40,40),comp('b',240,40)],[{'from':'a','to':'b','label':'go'}]))
import shutil
for f in os.listdir('out'):
    pth=os.path.join('out',f)
    if f.endswith('.html') or f.endswith('.delivery.json'): os.remove(pth)
    if f.startswith('fin-') and os.path.isdir(pth): shutil.rmtree(pth)
print('## E8 경계 프레임 안 비구성원: 구성원 a(왼위)·b(오른아래)가 만드는 프레임 안 왼아래에 비구성원 c')
def bnd(**m):
    d=arch([comp('a',60,40),comp('c',60,200,100,60),comp('b',400,200)],[{'from':'a','to':'b','label':'go'}],**m)
    d['boundaries']=[{'kind':'region','label':'Region','wraps':['a','b'],'pad':20}]
    return d
run('bnd_meta_showcase', bnd(quality_profile='showcase'), 'showcase')
run('bnd_meta_standard', bnd(quality_profile='standard'), 'showcase')
run('bnd_meta_none', bnd(), 'showcase')
run('bnd_meta_none_std', bnd(), 'standard')
for n in ['bnd_meta_showcase','bnd_meta_none']:
    r=sh(['render','architecture','out/%s.json'%n,'out/t.html','--quality','showcase'])
    print('  ',n,'첫 문장:',(r.stderr.strip().splitlines() or [''])[1][:150] if r.returncode else 'rc=0')
if os.path.exists('out/t.html'): os.remove('out/t.html')
import shutil
print('## E9 --quality 와 meta.quality_profile 불일치(R-19의 미확인): 경고·오류가 있는가')
for meta_q,cli_q in [('standard','showcase'),('showcase','standard')]:
    d=arch([comp('a',40,40),comp('b',240,40)],[{'from':'a','to':'b','label':'go'}],quality_profile=meta_q)
    json.dump(d,open('out/mm.json','w'))
    for cmd in (['render','architecture','out/mm.json','out/mm.html'],['validate','architecture','out/mm.json','--json'],['finalize','architecture','out/mm.json','out/mm.html','--json','--out-dir','out/fin-mm']):
        for f in ('out/mm.html','out/mm.delivery.json'):
            if os.path.exists(f): os.remove(f)
        shutil.rmtree('out/fin-mm',ignore_errors=True)
        r=sh(cmd+['--quality',cli_q])
        try: dd=json.loads(r.stdout); extra=' ok=%s quality=%s diags=%s'%(dd.get('ok'),json.dumps(dd.get('quality'))[:80],[x['code'] for x in dd.get('diagnostics',[])])
        except Exception: extra=''
        print('  meta=%s --quality=%s %-8s rc=%d stderr=%r%s'%(meta_q,cli_q,cmd[0],r.returncode,r.stderr.strip()[:100],extra))
import shutil
shutil.rmtree('out/fin-mm',ignore_errors=True)
for f in ('out/mm.html','out/mm.delivery.json'):
    if os.path.exists(f): os.remove(f)
print('## E7 browser-check(Chrome 1440x900): standard로 렌더한 같은 입력')
import shutil
for n in ['lowratio_1236','lowratio_1243','wide_1790','wide_1800']:
    r=sh(['render','architecture','out/%s.json'%n,'out/bc.html','--quality','standard'])
    b=subprocess.run(['node',CLI,'browser-check','out/bc.html','--summary','--out-dir','out/bc'],capture_output=True,text=True,stdin=subprocess.DEVNULL)
    try:
        d=json.loads(b.stdout); ds=d.get('diagnostics',[])
        print('  %-14s ok=%s checks=%s diags=%s minProjected=%s'%(n,d['ok'],d['checks'],[(x['code'],x['severity']) for x in ds],[round(x['evidence'].get('minimumProjectedNodeTextPx',0),2) for x in ds]))
    except Exception: print('  ',n,'browser-check unparsable rc=%d'%b.returncode,b.stderr[:120])
    shutil.rmtree('out/bc',ignore_errors=True)
    if os.path.exists('out/bc.html'): os.remove('out/bc.html')
