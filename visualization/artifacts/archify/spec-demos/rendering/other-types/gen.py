# 입력 생성기: python3 -I gen.py  (in/ 아래에 최소 입력 JSON을 쓴다)
import json, os
os.makedirs('in', exist_ok=True)
def w(name, d): json.dump(d, open('in/'+name+'.json','w'), indent=1)
def meta(t, **k): return {'title': t, 'output': 'x.html', **k}

# --- dataflow
def df(**m):
    return {'schema_version':1,'diagram_type':'dataflow','meta':meta('D',**m),
     'stages':[{'label':'In'},{'label':'Mid'},{'label':'Out'}],
     'nodes':[{'id':'a','type':'frontend','label':'A','stage':0,'row':0},
              {'id':'b','type':'backend','label':'B','stage':1,'row':1},
              {'id':'c','type':'database','label':'C','stage':2,'row':0},
              {'id':'d','type':'database','label':'D','stage':2,'row':2}],
     'flows':[{'from':'a','to':'b','label':'rows'},{'from':'b','to':'c','label':'agg'},{'from':'b','to':'d','label':'raw'},{'from':'a','to':'c','label':'skip'}]}
w('df.std', df())
w('df.show', df(quality_profile='showcase'))
x=df(); x['flows'][0]['to']='zzz'; w('df.unknown', x)
x=df(); x['nodes'][1]['yOffset']=-150; w('df.above', x)
x=df(); x['nodes'][1]['row']=9; w('df.badrow', x)

# --- lifecycle
def lc(states, trans, main, **m):
    return {'schema_version':3,'diagram_type':'lifecycle','meta':meta('L',**m),'mainPath':main,
            'states':[{'id':i,'type':t,'label':l} for i,t,l in states],'transitions':trans}
S=[('a','start','Draft'),('b','active','Review'),('c','success','Done'),('d','failure','Rejected'),('e','waiting','Hold')]
w('lc.basic', lc(S,[{'from':'a','to':'b','label':'submit'},{'from':'b','to':'c','label':'ok'},{'from':'b','to':'d','label':'no'},{'from':'a','to':'e','label':'park'},{'from':'e','to':'a','label':'resume'}],['a','b','c']))
w('lc.bracket', lc(S,[{'from':'a','to':'b','label':'go'},{'from':'b','to':'c','label':'ok'},{'from':'a','to':'d','label':'abort'},{'from':'b','to':'d','label':'abort'}],['a','b','c']))
w('lc.gap', lc(S[:3],[{'from':'a','to':'b'}],['a','b','c']))
w('lc.crowded', lc(S,[{'from':'a','to':'d'},{'from':'a','to':'e'}]+[{'from':'d','to':'e','label':'t%d'%i} for i in range(6)]+[{'from':'a','to':'b'},{'from':'b','to':'c'}],['a','b','c']))
big=[('s%d'%i,'active','State name number %d long'%i) for i in range(12)]
w('lc.wide', lc(big,[{'from':'s%d'%i,'to':'s%d'%(i+1),'label':'step %d is a long label'%i} for i in range(11)],['s%d'%i for i in range(12)]))
w('lc.dup', lc(S[:2]+[S[0]],[{'from':'a','to':'b'}],['a','b']))

# --- erd
def ent(i, row, col, tag=None, **k):
    e={'id':i,'label':i,'row':row,'col':col,'attributes':[{'name':'id','type':'int','key':'pk'}]}
    if tag: e['tag']=tag
    e.update(k); return e
def erd(ents, rels, **m):
    return {'schema_version':1,'diagram_type':'erd','meta':meta('E',**m),'layout':{'mode':'grid'},'entities':ents,'relationships':rels}
R=lambda a,b,l=None:{'from':a,'to':b,'fromCardinality':'many','toCardinality':'one',**({'label':l} if l else {})}
w('erd.fan', erd([ent('p',0,1),ent('c1',0,0),ent('c2',1,0),ent('c3',2,0)],[R('c1','p'),R('c2','p'),R('c3','p')]))
tall=lambda i,r,c,**k: ent(i,r,c,attributes=[{'name':n,'type':'int'} for n in ('id','a','b','c','d','e')],**k)
w('erd.trunk', erd([tall('p',1,1),tall('c1',0,0),tall('c2',1,0),tall('c3',2,0)],[R('c1','p'),R('c2','p'),R('c3','p')]))
w('erd.band', erd([ent('a',0,0,'sales'),ent('b',0,1,'sales'),ent('c',1,0,'ops')],[R('a','c'),R('b','a','owns')]))
w('erd.L', erd([ent('a',0,0,'sales'),ent('b',0,1,'sales'),ent('c',1,0,'sales'),ent('z',1,1)],[R('a','z')]))
w('erd.nogrid', erd([ent('a',0,0,'sales',pos=[40,60]),ent('b',0,1,'sales')],[R('a','b')]))
w('erd.self', erd([ent('a',0,0),ent('b',0,1)],[R('a','a')]))
w('erd.hdr', erd([ent('a_very_long_table_name_that_overflows',0,0,width=100),ent('b',0,1)],[R('a_very_long_table_name_that_overflows','b')]))

# --- class
def cls(types, rels, **m):
    return {'schema_version':1,'diagram_type':'class','meta':meta('C',**m),'layout':{'mode':'grid'},'types':types,'relationships':rels}
T=lambda i,row,col,kind='class',**k:{'id':i,'label':i,'kind':kind,'row':row,'col':col,**k}
w('cl.bus', cls([T('base',0,1,'interface'),T('x',1,0),T('y',1,1),T('z',1,2)],[{'from':k,'to':'base','kind':'realization'} for k in 'xyz']))
w('cl.cycle', cls([T('p',0,0),T('q',0,1)],[{'from':'p','to':'q','kind':'inheritance'},{'from':'q','to':'p','kind':'inheritance'}]))
w('cl.kind', cls([T('p',0,0),T('i',0,1,'interface')],[{'from':'p','to':'i','kind':'inheritance'}]))
w('cl.real', cls([T('p',0,0),T('q',0,1)],[{'from':'p','to':'q','kind':'realization'}]))
w('cl.half', cls([T('p',0,0),T('q',0,2),T('m',1,1.5)],[{'from':'m','to':'p','kind':'association'}]))

# --- sequence
def sq(parts, msgs, **m):
    return {'schema_version':1,'diagram_type':'sequence','meta':meta('S',**m),
            'participants':[{'id':i,'type':'backend','label':l,**({'sublabel':s} if s else {})} for i,l,s in parts],'messages':msgs}
P3=[('a','A',None),('b','B',None),('c','C',None)]
M=[{'from':'a','to':'b','y':180,'label':'call'},{'from':'b','to':'c','y':220,'label':'next'}]
w('sq.spread3', sq(P3,M)); w('sq.fixed3', sq(P3,M,column_fit='fixed'))
P5=[(c,'P'+c,None) for c in 'abcde']
M5=[{'from':'a','to':'e','y':180,'label':'long hop'}]
w('sq.spread5', sq(P5,M5)); w('sq.fixed5', sq(P5,M5,column_fit='fixed'))
w('sq.fixed5vb', sq(P5,M5,column_fit='fixed',viewBox=[1000,480]))
w('sq.longlabel', sq([('a','A very long participant label here',None),('b','B',None)],M[:1],column_fit='fixed',viewBox=[480,480]))
w('sq.self', sq(P3,[{'from':'a','to':'a','y':180,'label':'me'}]))
w('sq.self', sq(P3,[{'from':'a','to':'a','y':180,'label':'me'}]))
NOTE='a very long note text that must wrap inside the gap between lifelines '*2
w('sq.notelimit', sq(P3,[{'from':'a','to':'b','y':397,'label':'call','note':NOTE}],quality_profile='showcase',viewBox=[560,480]))
w('sq.noteoverlap', sq(P3,[{'from':'a','to':'b','y':180,'label':'call','note':NOTE},{'from':'a','to':'b','y':200,'label':'next'}],quality_profile='showcase',viewBox=[560,480]))
w('sq.borderrun', {**sq(P3,M,quality_profile='showcase'),'segments':[{'from':180,'to':300,'label':'Phase'}]})
w('sq.wide', sq([(c,'Participant '+c,'sublabel text for '+c) for c in 'abcdefgh'],[{'from':'a','to':'h','y':180,'label':'x'}]))

# --- tree
def tr(nodes, **l):
    return {'schema_version':1,'diagram_type':'tree','meta':meta('T'),**({'layout':l} if l else {}),'nodes':nodes}
kids=[{'id':'k%d'%i,'label':'Leaf %d'%i,'parent':'r'} for i in range(4)]
w('tr.stack', tr([{'id':'r','label':'Root'}]+kids)); w('tr.right', tr([{'id':'r','label':'Root'}]+kids,direction='right'))
w('tr.two', tr([{'id':'r','label':'Root'}]+kids[:2]))
w('tr.roots', tr([{'id':'r','label':'Root'},{'id':'s','label':'S'}]))
w('tr.cycle', tr([{'id':'r','label':'R'},{'id':'a','label':'A','parent':'b'},{'id':'b','label':'B','parent':'a'}]))

# --- timeline
def tl(evs, lanes=None, **m):
    d={'schema_version':1,'diagram_type':'timeline','meta':meta('E',evidence='illustrative',**m),'events':evs}
    if lanes: d['lanes']=lanes
    return d
ev=lambda i,at,t='E',**k:{'id':i,'at':at,'title':t+i,**k}
w('tl.break', tl([ev('a','2026-10-01T10:00:00Z'),ev('b','2026-10-01T10:05:00Z'),ev('c','2026-10-01T10:10:00Z'),ev('d','2026-10-05T10:10:00Z'),ev('e','2026-10-05T10:15:00Z')]))
w('tl.lanes', tl([ev('a','2026-10-01T10:00:00Z',lane='x'),ev('b','2026-10-01T10:00:00Z',lane='x'),ev('c','2026-10-01T10:01:00Z',lane='y')],[{'id':'x','label':'Lane X'},{'id':'y','label':'Lane Y'}]))
w('tl.badts', tl([ev('a','2026-02-30T10:00:00Z')]))
w('tl.tz', tl([ev('a','2026-10-01T10:00:00Z')],timezone='Not/AZone'))

# --- waterfall
def wf(spans, **m): return {'schema_version':1,'diagram_type':'waterfall','meta':meta('W',unit='ms',evidence='illustrative',**m),'spans':spans}
w('wf.inc', wf([{'id':'r','name':'root','start':0,'end':100},{'id':'c','name':'child','start':20,'status':'incomplete','parent':'r'}]))
w('wf.bad', wf([{'id':'r','name':'root','start':0,'end':100,'duration':5},{'id':'c','name':'child','start':20,'parent':'zz'}]))
w('wf.cycle', wf([{'id':'a','name':'a','start':0,'end':1,'parent':'b'},{'id':'b','name':'b','start':0,'end':1,'parent':'a'}]))
