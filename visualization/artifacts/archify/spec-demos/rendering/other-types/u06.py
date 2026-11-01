# U-06: dataflow node-below-area 수정안, --quality·meta.quality_profile 영향. python3 -I u06.py > u06.txt (HTML 즉시 삭제)
import json, subprocess, os, re
CLI='/Users/kkh/.claude/skills/archify/bin/archify.mjs'
os.makedirs('out', exist_ok=True)
def df(nodes, flows, **m):
    return {'schema_version':1,'diagram_type':'dataflow','meta':{'title':'D','output':'x.html',**m},'stages':[{'label':'In'},{'label':'Out'}],'nodes':nodes,'flows':flows}
N=lambda i,s,r,**k:{'id':i,'type':'backend','label':i.upper(),'stage':s,'row':r,**k}
F=lambda a,b,l='x':{'from':a,'to':b,'label':l}
def run(name, doc, args=(), env=None):
    p='out/u06.json'; json.dump(doc,open(p,'w'))
    e=dict(os.environ); 
    if env: e.update(env)
    r=subprocess.run(['node',CLI,'render','dataflow',p,'out/u06.html',*args],capture_output=True,text=True,stdin=subprocess.DEVNULL,env=e)
    codes=sorted(set(re.findall(r'\[([a-z-]+/[a-z-]+)\]',r.stderr)))
    vb=''
    if r.returncode==0:
        vb=re.search(r'<svg viewBox="([^"]*)"',open('out/u06.html').read()).group(1); os.remove('out/u06.html')
    print('%-34s rc=%d vb=%s codes=%s'%(name,r.returncode,vb,codes)); return r
print('## A. node-below-area: 노드 b에 yOffset 400 (b.y=242+400, 바닥 700 > 720-74=646)')
r=run('standard', df([N('a',0,0),N('b',1,1,yOffset=400)],[F('a','b')]))
for line in r.stderr.splitlines():
    if 'node-below-area' in line or 'readable diagram area' in line: print('   ',line[:900]); break
print('## B. 같은 입력에 meta.viewBox [940,720] 고정(저자 캔버스) -> 높이 키우기 수정안이 나오는지')
r=run('viewBox 940x720', df([N('a',0,0),N('b',1,1,yOffset=400)],[F('a','b')],viewBox=[940,720]))
for line in r.stderr.splitlines():
    if 'readable diagram area' in line: print('   ',line[:1100]); break
print('## B2. 저자 viewBox [1400,720] (넓은 캔버스) -> 높이 키우기 수정안 허용 구간')
r=run('viewBox 1400x720', df([N('a',0,0),N('b',1,1,yOffset=400)],[F('a','b')],viewBox=[1400,720]))
for line in r.stderr.splitlines():
    if 'readable diagram area' in line: print('   ',line[:700]); break
print('## B3. 키가 큰 노드: row 3(y=470)에 height 300')
r=run('tall node row3', df([N('a',0,0),N('b',1,3,height=300)],[F('a','b')]))
for line in r.stderr.splitlines():
    if 'readable diagram area' in line: print('   ',line[:700]); break
print('## C. 프로파일 입력 조합: 가운데 노드를 건너뛰는 흐름(showcase에서만 격자 우회)')
def skip(**m):
    return {'schema_version':1,'diagram_type':'dataflow','meta':{'title':'D','output':'x.html',**m},'stages':[{'label':'In'},{'label':'Mid'},{'label':'Out'}],
      'nodes':[N('a',0,0),N('b',1,0),N('c',2,0)],'flows':[F('a','b','one'),F('b','c','two'),F('a','c','skip')]}
run('meta 없음', skip())
run('meta standard + --quality showcase', skip(quality_profile='standard'), ['--quality','showcase'])
run('meta showcase + --quality standard', skip(quality_profile='showcase'), ['--quality','standard'])
run('meta showcase', skip(quality_profile='showcase'))
run('meta 없음 + --quality showcase', skip(), ['--quality','showcase'])
run('meta 없음 + env=showcase', skip(), env={'ARCHIFY_QUALITY_PROFILE':'showcase'})
print('## D. 교차 게이트 심각도: 두 흐름이 교차하는 입력(a:0→d:1행2, b:행2→c:행0)')
def cross(**m):
    return df([N('a',0,0),N('b',0,2),N('c',1,0),N('d',1,2)],[F('a','d','p'),F('b','c','q')],**m)
run('cross standard', cross(quality_profile='standard'))
run('cross meta 없음', cross())
run('cross showcase', cross(quality_profile='showcase'))
run('cross standard + --quality showcase', cross(quality_profile='standard'), ['--quality','showcase'])
if os.path.exists('out/u06.html'): os.remove('out/u06.html')
print('## E. validate --json 의 node-below-area supportedFixes·evidence')
for name,doc in [('A auto',df([N('a',0,0),N('b',1,1,yOffset=400)],[F('a','b')])),('B2 1400',df([N('a',0,0),N('b',1,1,yOffset=400)],[F('a','b')],viewBox=[1400,720])),('B3 tall',df([N('a',0,0),N('b',1,3,height=300)],[F('a','b')]))]:
    json.dump(doc,open('out/u06.json','w'))
    r=subprocess.run(['node',CLI,'validate','dataflow','out/u06.json','--json'],capture_output=True,text=True,stdin=subprocess.DEVNULL)
    for x in json.loads(r.stdout).get('diagnostics',[]):
        if x['code']=='dataflow/node-below-area': print(name, x['supportedFixes'], {k:x['evidence'][k] for k in ('requiredViewBoxHeight','requiredViewBoxFitsViewport','maximumViewBoxHeight')})
