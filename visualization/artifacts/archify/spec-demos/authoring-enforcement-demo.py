#!/usr/bin/env python3
"""읽기 전용 데모: 초안 규칙 중 코드가 강제하는 것을 설치본(레포 archify/와 동일) validate로 확인.
validate는 HTML을 쓰지 않는다. --repo-root 사례는 레포 clone에 git 읽기 명령만 실행된다."""
import json, subprocess, copy, os, tempfile
A='/Users/kkh/.claude/skills/archify/bin/archify.mjs'
REPO='/Users/kkh/Desktop/oss-analysis/visualization/repos/archify'
SHA='a4065941f12be7967436261d9934784e381d423c'
URL='https://github.com/tt-a1i/archify'
base={"schema_version":1,"diagram_type":"architecture",
 "meta":{"title":"T","output":"t.html","quality_profile":"showcase"},
 "components":[{"id":"a","type":"backend","label":"A","pos":[40,40],"size":[120,60]},
               {"id":"b","type":"database","label":"B","pos":[240,40],"size":[120,60]}],
 "connections":[{"id":"a-b","from":"a","to":"b","label":"x"}]}
src=[{"path":"archify/SKILL.md","line":18,"end_line":30}]
def mk(f):
    d=copy.deepcopy(base); f(d); return d
repo={"url":URL,"revision":SHA}
cases={
 "ok-no-evidence": (lambda d:None, []),
 "ok-with-evidence": (lambda d:(d['meta'].update(repository=repo), d['components'][0].update(sources=src)), ['--repo-root',REPO]),
 "sources-without-repository": (lambda d:d['components'][0].update(sources=src), ['--repo-root',REPO]),
 "repository-without-sources": (lambda d:d['meta'].update(repository=repo), ['--repo-root',REPO]),
 "evidence-without-repo-root": (lambda d:(d['meta'].update(repository=repo), d['components'][0].update(sources=src)), []),
 "short-revision": (lambda d:d['meta'].update(repository={"url":URL,"revision":SHA[:7]}), []),
 "four-sources": (lambda d:(d['meta'].update(repository=repo), d['components'][0].update(sources=src*4)), ['--repo-root',REPO]),
 "sources-on-connection": (lambda d:d['connections'][0].update(sources=src), []),
 "line-out-of-range": (lambda d:(d['meta'].update(repository=repo), d['components'][0].update(sources=[{"path":"archify/SKILL.md","line":9999}])), ['--repo-root',REPO]),
 "file-missing": (lambda d:(d['meta'].update(repository=repo), d['components'][0].update(sources=[{"path":"archify/NOPE.md","line":1}])), ['--repo-root',REPO]),
 "wrong-origin": (lambda d:(d['meta'].update(repository={"url":"https://github.com/other/other","revision":SHA}), d['components'][0].update(sources=src)), ['--repo-root',REPO]),
 "output-parent-dir": (lambda d:d['meta'].update(output="../t.html"), []),
 "output-not-html": (lambda d:d['meta'].update(output="t.txt"), []),
 "animation-invalid": (lambda d:d['meta'].update(animation="pulse"), []),
 "unknown-meta-field": (lambda d:d['meta'].update(foo=1), []),
 "subtitle-allowed": (lambda d:d['meta'].update(subtitle="s"), []),
 "quality-profile-omitted": (lambda d:d['meta'].pop('quality_profile'), []),
 "locale-unbundled": (lambda d:d['meta'].update(locale="fr"), []),
}
tmp=tempfile.mkdtemp()
for name,(f,extra) in cases.items():
    p=os.path.join(tmp,name+'.json'); json.dump(mk(f),open(p,'w'))
    r=subprocess.run(['node',A,'validate','architecture',p,'--json']+extra,capture_output=True,text=True,cwd=tmp)
    try:
        j=json.loads(r.stdout or r.stderr)
        codes=[x.get('code') for x in j.get('diagnostics',[])]
        print(f"{name}: exit={r.returncode} ok={j.get('ok')} codes={codes[:4]}")
    except Exception:
        print(f"{name}: exit={r.returncode} raw={(r.stdout or r.stderr)[:200]!r}")
