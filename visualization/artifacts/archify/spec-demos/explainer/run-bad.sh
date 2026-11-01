#!/bin/bash
# 잘못된 초안 각각에 validate explainer 를 돌려 진단 code·줄·메시지를 out/bad/*.json 과 out/bad-summary.tsv 에 남긴다.
cd "$(dirname "$0")"; . ./env.sh; mkdir -p out/bad
: > out/bad-summary.tsv
for f in in/bad/*.archify.md; do
  n=$(basename $f .archify.md)
  $A validate explainer $f --repo-root $R --json > out/bad/$n.json 2> out/bad/$n.err; rc=$?
  node -e '
const fs=require("fs");let j;try{j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"))}catch(e){console.log("\t(no json)");process.exit()}
const ds=j.diagnostics||[];console.log(process.argv[2]+"\t"+(j.ok?"ok":"fail")+"\t"+(j.stage||"")+"\t"+ds.slice(0,6).map(d=>d.code+"@"+(d.subject&&d.subject.line)+" "+(d.message||"").slice(0,90)).join(" || "))' out/bad/$n.json "rc=$rc $n" >> out/bad-summary.tsv
done
cat out/bad-summary.tsv
