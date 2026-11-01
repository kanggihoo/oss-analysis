# timeline·waterfall 시간·기간 서식 관찰. python3 -I time-formats.py > time-formats.txt (설치본 archify render, HTML은 즉시 삭제)
import json, subprocess, re, os, datetime
CLI='/Users/kkh/.claude/skills/archify/bin/archify.mjs'
os.makedirs('out', exist_ok=True)
def render(t, d):
    json.dump(d, open('out/tf.json','w'))
    r=subprocess.run(['node',CLI,'render',t,'out/tf.json','out/tf.html'],capture_output=True,text=True,stdin=subprocess.DEVNULL)
    if r.returncode: return None, r.stderr[:200]
    s=open('out/tf.html').read(); os.remove('out/tf.html'); return s, ''
def tl(evs, **m):
    return {'schema_version':1,'diagram_type':'timeline','meta':{'title':'T','output':'x.html','evidence':'illustrative',**m},'events':[{'id':'e%d'%i,'at':a,'title':'E%d'%i} for i,a in enumerate(evs)]}
base=datetime.datetime(2026,10,1,10,0,0,tzinfo=datetime.timezone.utc)
iso=lambda dt: dt.strftime('%Y-%m-%dT%H:%M:%S')+('.%03d'%(dt.microsecond//1000) if dt.microsecond else '')+'Z'
print('# timeline 휴지기: 이벤트 0, +1분, +1분+gap  -> 칩 라벨(approximateDuration) / aria-label(durationLabel)')
for name,gap in [('15h3s',15*3600+3),('1d1h30m',86400+3600+1800),('59m40s',59*60+40),('23h59m40s',23*3600+59*60+40),('10m',600),('2d',2*86400),('3d12h',3*86400+12*3600),('45s*',45)]:
    evs=[base, base+datetime.timedelta(minutes=1), base+datetime.timedelta(minutes=1,seconds=gap)]
    s,e=render('timeline',tl([iso(x) for x in evs]))
    if s is None: print(name,'ERR',e); continue
    chip=re.findall(r'data-break-ms="(\d+)" aria-label="([^"]*)"',s); lab=re.findall(r'<text[^>]*font-size="10" font-weight="700" text-anchor="middle">([^<]*)</text>',s)
    ticks=re.findall(r'class="t-muted tl-tick"[^>]*>([^<]*)<',s); times=re.findall(r'class="t-[a-z]+ tl-time"[^>]*>([^<]*)<',s)
    print(name,'gap_ms=%d'%(gap*1000),'break',chip,'chip',lab,'| event times',times)
print('# 시계 라벨: 초·밀리초·다중일·시간대')
for name,evs,m in [('분 단위, 같은 날',['2026-10-01T10:00:00Z','2026-10-01T10:05:00Z'],{}),
   ('초 있음',['2026-10-01T10:00:00Z','2026-10-01T10:00:30Z'],{}),
   ('밀리초 있음',['2026-10-01T10:00:00.250Z','2026-10-01T10:00:30Z'],{}),
   ('다중일',['2026-10-01T22:00:00Z','2026-10-02T02:00:00Z'],{}),
   ('Asia/Seoul',['2026-10-01T10:00:00Z','2026-10-01T10:05:00Z'],{'timezone':'Asia/Seoul'}),
   ('America/New_York(DST)',['2026-03-08T06:00:00Z','2026-03-08T09:00:00Z'],{'timezone':'America/New_York'}),
   ('Asia/Kolkata',['2026-10-01T10:00:00Z','2026-10-01T10:05:00Z'],{'timezone':'Asia/Kolkata'})]:
    s,e=render('timeline',tl(evs,**m))
    if s is None: print(name,'ERR',e); continue
    cap=re.findall(r'data-timeline-axis-caption="" [^>]*>([^<]*)<',s); times=re.findall(r'class="t-[a-z]+ tl-time"[^>]*>([^<]*)<',s); ticks=re.findall(r'class="t-muted tl-tick"[^>]*>([^<]*)<',s)
    ctx=re.findall(r'data-node-context="([^"]*)"',s) or re.findall(r'(\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)? UTC[+-]\d\d:\d\d)',s)
    print(name,'| caption',cap,'| times',times,'| ticks',ticks[:4],'| ctx',ctx[:2])
def wf(spans,unit='ms'):
    return {'schema_version':1,'diagram_type':'waterfall','meta':{'title':'W','output':'x.html','unit':unit,'evidence':'illustrative'},'spans':spans}
print('# waterfall: 루트 start 0 end X, 자식 start a end b -> 라벨(막대 오른쪽), 헤더 wall, 공유율')
cases=[('정수',100,[(0,40)]),('소수 2자리',100.456,[(0,33.333)]),('1천 이상',1234567.891,[(0,500000)]),('0.005',0.005,[(0,0.002)]),('1e-7',1e-7,[(0,4e-8)]),('0.01 경계',0.0123,[(0,0.0099)]),('큰 공유 12.6%',100,[(0,12.6)]),('작은 공유 3.14%',100,[(0,3.14)])]
for name,end,kids in cases:
    spans=[{'id':'r','name':'root','start':0,'end':end}]+[{'id':'c%d'%i,'name':'k%d'%i,'start':a,'end':b,'parent':'r'} for i,(a,b) in enumerate(kids)]
    s,e=render('waterfall',wf(spans))
    if s is None: print(name,'ERR',e); continue
    wall=re.findall(r'data-waterfall-total="[^"]*"[^>]*>(.*?)</text>',s)
    labs=re.findall(r'wf-num" font-size="[^"]*" font-weight="[^"]*">([^<]*)</text>',s)
    share=re.findall(r'data-node-sublabel="([^"]*)"',s) or re.findall(r'(\d[\d.,]*%)',s)
    print(name,'| wall',[re.sub('<[^>]+>',' ',w) for w in wall],'| row labels',labs,'| share',share[:2])
s,e=render('waterfall',wf([{'id':'r','name':'root','start':0,'end':2500}],unit='us')); print('unit us ->',re.findall(r'data-waterfall-unit="([^"]*)"',s), re.findall(r'(\d+ µs)',s)[:3])
