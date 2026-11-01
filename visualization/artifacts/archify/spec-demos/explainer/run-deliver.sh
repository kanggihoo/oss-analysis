#!/bin/bash
# 정상 초안을 finalize/deliver/check 하고, 최종 HTML 구조·locale 문구를 관찰한다. 결과는 out/deliver/ 아래.
cd "$(dirname "$0")"; . ./env.sh; O=out/deliver; rm -rf $O; mkdir -p $O in/loc
# 1) finalize (기본: browser-check 없음, quality showcase)
$A finalize explainer in/ok.archify.md $O/ok.html --repo-root $R --json > $O/ok.finalize.json 2>$O/ok.finalize.err; echo "finalize rc=$?"
node -e 'const j=JSON.parse(require("fs").readFileSync(process.argv[1]));console.log(JSON.stringify({ok:j.ok,status:j.status,quality:j.quality,gates:j.gates,browserCheck:j.browserCheck,visualReview:j.visualReview,diag:(j.diagnostics||[]).length},null,1))' $O/ok.finalize.json
ls -la $O
# 2) check 단독
$A check $O/ok.html > $O/ok.check.json 2>$O/ok.check.err; echo "check rc=$?"
node -e 'const j=JSON.parse(require("fs").readFileSync(process.argv[1]));console.log(j.ok,j.family,j.checks&&j.checks.map(c=>c.name+":"+c.ok).join(","),j.provenance)' $O/ok.check.json
# 3) deliver 단독(검증 겸함)
$A deliver explainer in/ok.archify.md $O/ok-deliver.html --repo-root $R --json > $O/ok.deliver.json 2>$O/ok.deliver.err; echo "deliver rc=$?"
node -e 'const j=JSON.parse(require("fs").readFileSync(process.argv[1]));console.log(Object.keys(j).join(","));console.log(JSON.stringify(j.explainer&&{preparedSha256:j.explainer.preparedSha256,deps:j.explainer.dependencies.map(d=>d.kind+":"+d.id)}))' $O/ok.deliver.json
# 4) locale 별 Ask UI
for L in ko en zh-CN none; do
  if [ $L = none ]; then grep -v '^@meta locale' in/ok.archify.md > in/loc/$L.archify.md; else sed "s/^@meta locale=en/@meta locale=$L/" in/ok.archify.md > in/loc/$L.archify.md; fi
  $A finalize explainer in/loc/$L.archify.md $O/loc-$L.html --repo-root $R --json >/dev/null 2>&1; echo "loc $L rc=$?"
  node -e '
const h=require("fs").readFileSync(process.argv[1],"utf8");
const lang=h.match(/<html lang="([^"]*)"/)[1];
const w=JSON.parse(h.match(/id="explainer-reader-words">([\s\S]*?)<\/script>/)[1]);
console.log(process.argv[2],"lang="+lang,"ask="+w.ask,"askCopy="+w.askCopy,"answer="+w.answer)' $O/loc-$L.html $L
done
