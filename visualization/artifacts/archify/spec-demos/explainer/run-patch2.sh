#!/bin/bash
# patch explainer 추가 실험: 변조된 원본, native HTML, 연쇄 패치, 제자리 덮어쓰기. 결과는 out/patch2/.
cd "$(dirname "$0")"; . ./env.sh; O=out/patch2; rm -rf $O; mkdir -p $O
sum(){ node -e 'const fs=require("fs");let j;try{j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"))}catch(e){console.log(process.argv[2],"(no json)");process.exit()}
 const ds=j.diagnostics||[];console.log(process.argv[2],"ok="+j.ok,ds.slice(0,3).map(d=>d.code+" "+(d.message||"").slice(0,90)).join(" || "))' $1 $2; }
# a) 변조: 본문 텍스트를 HTML에서 직접 바꿈
sed 's/Look up the key first/Look up the KEY first/' out/deliver/ok.html > $O/tampered.html
$A patch explainer $O/tampered.html options in/patch/p1-good.md $O/a.html --json > $O/a.json 2>/dev/null; echo "a rc=$?"; sum $O/a.json a-tampered
# b) native 다이어그램 HTML (사본)
cp /Users/kkh/Desktop/oss-analysis/visualization/reports/archify/diagrams/structure.html $O/native.html
$A patch explainer $O/native.html options in/patch/p1-good.md $O/b.html --json > $O/b.json 2>/dev/null; echo "b rc=$?"; sum $O/b.json b-native
# c) 연쇄: 패치 결과를 다시 패치 (다른 패널)
cp out/patch/p1-good.html $O/chain1.html
cat > $O/c-replacement.md <<'X'
## What should you check? {#checks}

- [ ] Confirm the TTL
- [ ] Watch the hit rate
- [ ] Alert on a low hit rate
X
$A patch explainer $O/chain1.html checks $O/c-replacement.md $O/chain2.html --repo-root $R --json > $O/c.json 2>/dev/null; echo "c rc=$?"; sum $O/c.json c-chain
# d) 제자리 덮어쓰기 (output == artifact)
cp out/deliver/ok.html $O/inplace.html
$A patch explainer $O/inplace.html options in/patch/p1-good.md $O/inplace.html --repo-root $R --json > $O/d.json 2>/dev/null; echo "d rc=$?"; sum $O/d.json d-inplace
cmp -s out/deliver/ok.html $O/inplace.html && echo "d: file unchanged" || echo "d: file changed"
# e) --repo-root 없이 패치 (원본 초안에 repository 근거가 있음, 그 패널은 안 건드림)
$A patch explainer out/deliver/ok.html options in/patch/p1-good.md $O/e.html --json > $O/e.json 2>/dev/null; echo "e rc=$?"; sum $O/e.json e-no-repo-root
