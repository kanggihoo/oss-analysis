#!/bin/sh
# compare 추가 실험: 실패 시 기존 출력 보존, 연결 id 누락, 스키마 위반, 기본 출력 이름, 같은 입력 비교
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
cd "$(dirname "$0")"
rm -rf out2 && mkdir out2
node -e "
const fs=require('fs');const d=JSON.parse(fs.readFileSync('head.json','utf8'));
delete d.connections[0].id; fs.writeFileSync('head-noid.json',JSON.stringify(d));
const e=JSON.parse(fs.readFileSync('head.json','utf8')); e.schema_version=1; delete e.components[0].type; fs.writeFileSync('head-badschema.json',JSON.stringify(e));
const f=JSON.parse(fs.readFileSync('head.json','utf8')); f.connections[1].id=f.connections[0].id; fs.writeFileSync('head-dupid.json',JSON.stringify(f));
"
echo "== A. 연결 id 누락"; $A compare architecture base.json head-noid.json out2/a.html --json > out2/a.json; echo "exit=$?"; node -e "const r=require('./out2/a.json');console.log(r.stage,r.diagnostics[0].code,JSON.stringify(r.diagnostics[0].subject),JSON.stringify(r.diagnostics[0].evidence))"
echo "== B. 중복 id"; $A compare architecture base.json head-dupid.json out2/b.html --json > out2/b.json; echo "exit=$?"; node -e "const r=require('./out2/b.json');console.log(r.stage,r.diagnostics[0].code)"
echo "== C. 필수 필드 누락 head"; $A compare architecture base.json head-badschema.json out2/c.html --json > out2/c.json; echo "exit=$?"; node -e "const r=require('./out2/c.json');console.log(r.stage,r.diagnostics.map(d=>d.code).join(','))"
echo "== D. 실패 시 기존 출력 보존"; echo OLD > out2/keep.html; echo OLD > out2/keep.receipt.json; $A compare architecture base.json noshare.json out2/keep.html >/dev/null 2>&1; echo "exit=$?"; cat out2/keep.html out2/keep.receipt.json
echo "== E. 성공 시 기존 출력 교체"; $A compare architecture base.json head.json out2/keep.html >/dev/null; echo "exit=$?"; head -c 15 out2/keep.html; echo; head -c 30 out2/keep.receipt.json; echo
echo "== F. 기본 출력 이름 (cwd=out2)"; (cd out2 && $A compare architecture ../base.json ../head.json >/dev/null; echo "exit=$?"; ls | tr '\n' ' '; echo)
echo "== G. 출력 확장자 오류"; $A compare architecture base.json head.json out2/x.txt --json > out2/g.json; echo "exit=$?"; node -e "const r=require('./out2/g.json');console.log(r.stage,r.diagnostics[0].code)"
echo "== H. 출력이 입력과 같은 경로"; $A compare architecture base.json head.json base.json --json > out2/h.json; echo "exit=$?"; node -e "const r=require('./out2/h.json');console.log(r.stage,r.diagnostics[0].code)"; node -e "JSON.parse(require('fs').readFileSync('base.json','utf8'));console.log('base.json intact')"
echo "== I. 스테이징 잔여물"; ls -A out2 | grep -c '^\.archify' || true
