#!/bin/bash
# 기타 실험: --repo-root 없는 @code, --writing 모드, 실패 시 finalize 영수증, 품질 프로파일 기본값. 결과는 out/misc/.
cd "$(dirname "$0")"; . ./env.sh; O=out/misc; rm -rf $O; mkdir -p $O
sum(){ node -e 'const fs=require("fs");let j;try{j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"))}catch(e){console.log(process.argv[2],"(no json)");process.exit()}
 const ds=j.diagnostics||[];console.log(process.argv[2],"ok="+j.ok,"gates="+JSON.stringify(j.gates||""),ds.slice(0,4).map(d=>d.severity+":"+d.code+"@"+(d.subject&&d.subject.line)+" "+(d.message||"").slice(0,70)).join(" || "))' $1 $2; }
# 1) @code, --repo-root 없음, @meta repo_* 없음
$A validate explainer in/bad/b14-code-no-repo.archify.md --json > $O/code-no-root.json 2>/dev/null; echo "1 rc=$?"; sum $O/code-no-root.json code-no-root
# 2) --writing 모드
for m in warn strict off; do $A validate explainer in/bad/d01-long-sentence.archify.md --writing $m --json > $O/writing-$m.json 2>/dev/null; echo "2 $m rc=$?"; sum $O/writing-$m.json writing-$m; done
# 3) 실패하는 초안에 finalize
$A finalize explainer in/bad/b07-unresolved-source.archify.md $O/fail.html --json > $O/finalize-fail.json 2>/dev/null; echo "3 rc=$?"; sum $O/finalize-fail.json finalize-fail; ls $O | grep fail
# 4) 경고만 있는 초안을 finalize: 통과하고 경고가 영수증에 남나
$A finalize explainer in/bad/d02-cliche-quality.archify.md $O/warn.html --json > $O/finalize-warn.json 2>$O/finalize-warn.err; echo "4 rc=$?"; sum $O/finalize-warn.json finalize-warn; head -c 300 $O/finalize-warn.err
# 5) JSON 초안
$A validate explainer in/ok-json.archify.md --json > $O/json-draft.json 2>/dev/null; echo "5 rc=$?"; sum $O/json-draft.json json-draft
# 6) quality: meta.quality_profile=standard 인 초안을 finalize / deliver
sed 's/^@meta locale=en/@meta locale=en quality_profile=standard/' in/ok.archify.md > in/q-standard.archify.md
$A finalize explainer in/q-standard.archify.md $O/q-fin.html --repo-root $R --json > $O/q-fin.json 2>/dev/null; echo "6a rc=$?"
$A deliver explainer in/q-standard.archify.md $O/q-del.html --repo-root $R --json > $O/q-del.json 2>/dev/null; echo "6b rc=$?"
for f in q-fin q-del; do python3 - $O/$f.html <<'P'
import re,json,sys
h=open(sys.argv[1]).read()
b=json.loads(re.search(r'id="archify-explainer-prepared">(.*?)</script>',h,re.S).group(1))
print(sys.argv[1],'quality=',b['quality'])
P
done
# 7) --browser-check 실행 시도
$A finalize explainer in/ok.archify.md $O/bc.html --repo-root $R --browser-check --json > $O/finalize-bc.json 2>$O/finalize-bc.err; echo "7 rc=$?"; node -e 'const j=JSON.parse(require("fs").readFileSync(process.argv[1]));console.log(j.status,JSON.stringify(j.gates),JSON.stringify(j.browserCheck),(j.diagnostics||[]).map(d=>d.code).join(","))' $O/finalize-bc.json
