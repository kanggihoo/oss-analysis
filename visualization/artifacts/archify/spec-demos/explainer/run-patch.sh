#!/bin/bash
# patch explainer 실험: 정상 HTML(out/deliver/ok.html)의 사본에서 패널 하나를 바꾼다. 결과는 out/patch/.
cd "$(dirname "$0")"; . ./env.sh; O=out/patch; rm -rf $O; mkdir -p $O; cp out/deliver/ok.html $O/base.html
run(){ # name panel replacement
  $A patch explainer $O/base.html $2 in/patch/$3 $O/$1.html --repo-root $R --json > $O/$1.json 2> $O/$1.err; rc=$?
  node -e 'const fs=require("fs");let j;try{j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"))}catch(e){console.log(process.argv[2],"rc="+process.argv[3],"(no json)");process.exit()}
  const ds=j.diagnostics||[];console.log(process.argv[2],"rc="+process.argv[3],"ok="+j.ok,"stage="+(j.stage||""),ds.slice(0,3).map(d=>d.code+"@"+(d.subject&&d.subject.line)+" "+(d.message||"").slice(0,80)).join(" || "), j.revision?("rev="+j.revision.slice(0,8)+" orig="+(j.original&&j.original.revision||"").slice(0,8)):"")' $O/$1.json $1 $rc
}
run p1-good options p1-good.md
run p2-new-id options p2-new-id.md
run p3-two-panels options p3-two-panels.md
run p4-adds-source options p4-adds-source.md
run p5-parse-error options p5-parse-error.md
run p6-no-newline options p6-no-newline.md
run p7-dup-block-id options p7-dup-block-id.md
run p8-no-id-heading options p8-no-id-heading.md
run p9-unknown-panel nope p1-good.md
run p10-answer answer p1-good.md
ls $O
