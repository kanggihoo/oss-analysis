"""Static documentation audit; does not import or execute the analyzed repository."""
from pathlib import Path
import re, subprocess
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'trading/repos/daily_stock_analysis'
caps = workspace / 'trading/reports/daily_stock_analysis/capabilities'
expected = 'ce364e457aab288863a5707e7b3df79786ad07f2'
errors = []; counts = {}; graph = {}
for doc in sorted(caps.glob('*.md')):
    text = doc.read_text(); fm = text.split('---', 2)[1]
    if f'sha: "{expected}"' not in fm: errors.append(f'{doc.name}: SHA')
    if 'status: ready' not in fm: errors.append(f'{doc.name}: not ready')
    sources = set(re.findall(r'^  - (.+)$', fm.split('sources:',1)[1].split('depends:',1)[0].split('status:',1)[0], re.M))
    # Each backticked code reference may contain several disjoint ranges.
    refs = 0
    for m in re.finditer(r'`([^`\n]+\.(?:py|yaml|yml|json|md)):(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)`', text):
        path = repo / m[1]
        if not path.is_file(): errors.append(f'{doc.name}: missing {m[1]}'); continue
        if m[1] not in sources: errors.append(f'{doc.name}: sources missing {m[1]}')
        lines = len(path.read_text().splitlines())
        for span in m[2].split(','):
            ns = [int(x) for x in span.strip().split('-')]; lo, hi = ns[0], ns[-1]; refs += 1
            if not 1 <= lo <= hi <= lines: errors.append(f'{doc.name}: bad {m[1]}:{span} (len {lines})')
    for section in ('1.1','1.2','1.3','1.4','1.5','1.6','2.1'):
        if not re.search(r'^### '+re.escape(section)+r'\b',text,re.M): errors.append(f'{doc.name}: section {section}')
    dep_block = fm.split('depends:',1)[1].split('status:',1)[0]
    deps = re.findall(r'^  - (.+\.md)$',dep_block,re.M)
    graph[doc.name] = deps
    for dep in deps:
        if not (doc.parent/dep).is_file(): errors.append(f'{doc.name}: missing dep {dep}')
    counts[doc.name] = refs

def visit(n, trail):
    if n in trail: errors.append('cycle: '+' -> '.join(trail+[n])); return
    for d in graph.get(n,[]): visit(d,trail+[n])
for n in graph: visit(n,[])
head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
clean=subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
if head != expected: errors.append('checkout SHA mismatch')
if clean: errors.append('checkout dirty')
print('Static spec audit: 2026-11-11')
print('SHA:',head,'clean:',not bool(clean))
for n,c in counts.items(): print(n, c, 'code ranges')
print('specs:',len(counts),'code ranges:',sum(counts.values()),'DAG: checked')
print('ERROR',len(errors))
for error in errors: print(error)
raise SystemExit(bool(errors))
