# 타입별 SVG 루트 속성 이름과 본문 섹션 주석 순서 관찰. python3 -I markup-observe.py > markup.txt (HTML 즉시 삭제)
import subprocess, re, os
CLI='/Users/kkh/.claude/skills/archify/bin/archify.mjs'
for t,f in [('dataflow','df.std'),('lifecycle','lc.basic'),('erd','erd.band'),('class','cl.bus'),('sequence','sq.spread3'),('tree','tr.stack'),('timeline','tl.break'),('waterfall','wf.inc')]:
    r=subprocess.run(['node',CLI,'render',t,'in/%s.json'%f,'out/mk.html'],capture_output=True,text=True,stdin=subprocess.DEVNULL)
    if r.returncode: print(t,'ERR',r.stderr[:100]); continue
    s=open('out/mk.html').read(); os.remove('out/mk.html')
    root=re.search(r'<svg\b[^>]*>',s).group(0)
    attrs=re.findall(r'\s([a-zA-Z:-]+)=',root)
    secs=re.findall(r'<!-- ([^>]*?) -->',s[s.index(root):s.index('</svg>')])
    print('##',t,'root attrs:',attrs); print('   sections:',[x.split('(')[0].strip() for x in secs])
