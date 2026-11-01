# 일반 관계선(trunk·버스·레인 아닌 것) 관찰용 입력. python3 -I gen-routes.py; sh observe-routes.sh > routes.txt
import json, os
os.makedirs('in', exist_ok=True)
def w(n, d): json.dump(d, open('in/'+n+'.json','w'), indent=1)
def meta(t): return {'title': t, 'output': 'x.html'}
def ent(i,row,col,n=1,**k):
    return {'id':i,'label':i,'row':row,'col':col,'attributes':[{'name':'c%d'%j,'type':'int'} for j in range(n)],**k}
R=lambda a,b,l=None:{'from':a,'to':b,'fromCardinality':'many','toCardinality':'one',**({'label':l} if l else {})}
def erd(ents,rels): return {'schema_version':1,'diagram_type':'erd','meta':meta('E'),'layout':{'mode':'grid'},'entities':ents,'relationships':rels}
w('erd.r1', erd([ent('a',0,0),ent('b',0,1)],[R('a','b')]))                       # 같은 높이: 직선
w('erd.r2', erd([ent('a',0,0,1),ent('b',0,1,4)],[R('a','b')]))                    # 높이 차: 한 번 꺾임
w('erd.r3', erd([ent('a',0,0),ent('m',0,1),ent('c',0,2)],[R('a','c')]))          # 가운데가 막음
w('erd.r4', erd([ent('a',0,0),ent('b',1,0)],[R('a','b')]))                       # 같은 열: 세로 변
w('erd.r5', erd([ent('a',0,0),ent('b',0,1),ent('c',1,0),ent('d',1,1)],[R('a','d'),R('b','c')]))  # X 교차
w('erd.r6', erd([ent('a',0,0),ent('m',0,1),ent('c',0,2)],[R('a','c','uses')]))   # 막힘 + 라벨
T=lambda i,row,col,kind='class',**k:{'id':i,'label':i,'kind':kind,'row':row,'col':col,**k}
def cls(ts,rs): return {'schema_version':1,'diagram_type':'class','meta':meta('C'),'layout':{'mode':'grid'},'types':ts,'relationships':rs}
A=lambda a,b,k='association',**x:{'from':a,'to':b,'kind':k,**x}
w('cl.r1', cls([T('a',0,0),T('b',0,1)],[A('a','b')]))
w('cl.r2', cls([T('a',0,0),T('b',0,1,attributes=[{'name':n,'type':'int'} for n in 'xyz'])],[A('a','b')]))
w('cl.r3', cls([T('a',0,0),T('m',0,1),T('c',0,2)],[A('a','c')]))
w('cl.r4', cls([T('a',0,0),T('b',1,0)],[A('a','b')]))
w('cl.r5', cls([T('a',0,0),T('b',0,1),T('c',1,0),T('d',1,1)],[A('a','d'),A('b','c')]))
w('cl.r6', cls([T('a',0,0),T('m',0,1),T('c',0,2)],[A('a','c',label='uses')]))

# --- dataflow showcase: 가운데 노드가 막는 건너뛰기 흐름
def dfs(profile, labels=True):
    L=lambda s: {'label':s} if labels else {}
    return {'schema_version':1,'diagram_type':'dataflow','meta':{**meta('D'),'quality_profile':profile},
      'stages':[{'label':'In'},{'label':'Mid'},{'label':'Out'}],
      'nodes':[{'id':'a','type':'frontend','label':'A','stage':0,'row':0},
               {'id':'b','type':'backend','label':'B','stage':1,'row':0},
               {'id':'c','type':'database','label':'C','stage':2,'row':0}],
      'flows':[{'from':'a','to':'b','label':'one'},{'from':'b','to':'c','label':'two'},{'from':'a','to':'c','label':'skip'}]}
w('df.r1.show', dfs('showcase')); w('df.r1.std', dfs('standard'))
