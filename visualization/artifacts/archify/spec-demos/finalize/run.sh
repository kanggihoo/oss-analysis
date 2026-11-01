#!/bin/bash
# finalize 실험. 설치본(레포 archify/와 diff -rq 차이 없음)으로 실행. 결과는 work/ 와 out/ 에 남는다.
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
R=/Users/kkh/Desktop/oss-analysis/visualization/repos/archify   # --repo-root (읽기 전용)
H="$(cd "$(dirname "$0")" && pwd)"
cd "$H"; rm -rf work out; mkdir -p work out
export ARCHIFY_UPDATE_CHECK_DISABLED=1
# run <이름> <cwd> 명령...  -> out/<이름>.{stdout,stderr,exit}
run() { n=$1; d=$2; shift 2; (cd "$d" && "$@" >"$H/out/$n.stdout" 2>"$H/out/$n.stderr"; echo $? >"$H/out/$n.exit"); echo "$n exit=$(cat out/$n.exit)"; }
ls_() { (cd "$1" && find . -type f -o -type l | sort) > "$H/out/$2.ls"; }

# 01 정상 통과(architecture) --json
mkdir -p work/a; run 01-pass-json work/a $A finalize architecture $H/in/brand-aware-delivery.architecture.json out.html --json; ls_ work/a 01-pass-json
cp work/a/out.finalize.json out/01.finalize.json; cp work/a/out.finalize-summary.json out/01.finalize-summary.json; cp work/a/out.delivery.json out/01.delivery.json; cp work/a/out.browser-check.json out/01.browser-check.json
# 02 같은 경로 반복 실행(텍스트 모드)
shasum -a 256 work/a/out.html > out/02.html.before
run 02-repeat-text work/a $A finalize architecture $H/in/brand-aware-delivery.architecture.json out.html
shasum -a 256 work/a/out.html > out/02.html.after; ls_ work/a 02-repeat-text
cp work/a/out.finalize.json out/02.finalize.json; cp work/a/out.delivery.json out/02.delivery.json
# 03 --out-dir
mkdir -p work/b; run 03-out-dir work/b $A finalize architecture $H/in/brand-aware-delivery.architecture.json out.html --out-dir rcpt --json; ls_ work/b 03-out-dir
# 04 --receipt
mkdir -p work/c; run 04-receipt work/c $A finalize architecture $H/in/brand-aware-delivery.architecture.json out.html --receipt r/my.json --json; ls_ work/c 04-receipt
# 05 --receipt 가 출력 HTML 경로와 같음
mkdir -p work/d; run 05-receipt-collide work/d $A finalize architecture $H/in/brand-aware-delivery.architecture.json out.html --receipt out.delivery.json --json; ls_ work/d 05-receipt-collide
# 06 deliver 단계 실패(스키마 오류)
#  (a) 기존 정상 산출물 위에서
mkdir -p work/e; run 06a-pass work/e $A finalize lifecycle $H/in/ok.json e.html --json
shasum -a 256 work/e/e.html > out/06.html.before; ls_ work/e 06a-pass
run 06b-bad-schema-existing work/e $A finalize lifecycle $H/in/bad-schema.json e.html --json
shasum -a 256 work/e/e.html > out/06.html.after; ls_ work/e 06b-bad-schema-existing
cp work/e/e.finalize.json out/06b.finalize.json; cp work/e/e.finalize-summary.json out/06b.finalize-summary.json; cp work/e/e.delivery.json out/06b.delivery.json
#  (b) 첫 실행(기존 HTML 없음)
mkdir -p work/f; run 06c-bad-schema-fresh work/f $A finalize lifecycle $H/in/bad-schema.json f.html --json; ls_ work/f 06c-bad-schema-fresh
cp work/f/f.finalize-summary.json out/06c.finalize-summary.json
#  (c) 텍스트 모드 실패
run 06d-bad-schema-text work/f $A finalize lifecycle $H/in/bad-schema.json f.html
# 07 showcase 경고 실패(release-delivery.workflow: composition/viewport-height 경고 1건) / standard 로는 deliver·check 통과, browser-check 실패
mkdir -p work/g; run 07a-showcase-warning work/g $A finalize workflow $H/in/release-delivery.workflow.json w.html --json; ls_ work/g 07a-showcase-warning
cp work/g/w.finalize.json out/07a.finalize.json; cp work/g/w.finalize-summary.json out/07a.finalize-summary.json
mkdir -p work/h; run 07b-standard-browser-fail work/h $A finalize workflow $H/in/release-delivery.workflow.json w.html --quality standard --json; ls_ work/h 07b-standard-browser-fail
cp work/h/w.finalize.json out/07b.finalize.json; cp work/h/w.finalize-summary.json out/07b.finalize-summary.json
# 08 --candidate-sha256
SHA=$(shasum -a 256 in/ok.json | cut -d' ' -f1)
mkdir -p work/i
run 08a-candidate-match work/i $A finalize lifecycle $H/in/ok.json i.html --candidate-sha256 $SHA --json
run 08b-candidate-mismatch work/i $A finalize lifecycle $H/in/ok-v2.json i2.html --candidate-sha256 $SHA --json
ls_ work/i 08b-candidate-mismatch
run 08c-candidate-badformat work/i $A finalize lifecycle $H/in/ok.json i3.html --candidate-sha256 ABC --json
run 08d-candidate-badformat-text work/i $A finalize lifecycle $H/in/ok.json i3.html --candidate-sha256 ABC
# 09 explainer
mkdir -p work/x
run 09a-explainer-ok work/x $A finalize explainer $H/in/ok.archify.md x.html --repo-root $R --json; ls_ work/x 09a-explainer-ok
cp work/x/x.finalize.json out/09a.finalize.json; cp work/x/x.finalize-summary.json out/09a.finalize-summary.json
run 09b-explainer-browser work/x $A finalize explainer $H/in/ok.archify.md x.html --repo-root $R --browser-check --json
cp work/x/x.finalize-summary.json out/09b.finalize-summary.json
mkdir -p work/y; run 09c-explainer-bad work/y $A finalize explainer $H/in/b07-unresolved-source.archify.md y.html --repo-root $R --json; ls_ work/y 09c-explainer-bad
# 10 Chrome 없음 -> browser-check skipped, 종료 2
mkdir -p work/j; ARCHIFY_CHROME=/nonexistent run 10-no-chrome work/j $A finalize architecture $H/in/brand-aware-delivery.architecture.json j.html --json; ls_ work/j 10-no-chrome
cp work/j/j.finalize-summary.json out/10.finalize-summary.json
# 11 출력 경로 재사용 소유권 충돌(verification-gates R-35): 입력을 바꿔 같은 경로에 finalize
mkdir -p work/k; run 11a-first work/k $A finalize lifecycle $H/in/ok.json k.html --json
run 11b-changed-same-path work/k $A finalize lifecycle $H/in/ok-v2.json k.html --json
cp work/k/k.finalize-summary.json out/11b.finalize-summary.json; ls_ work/k 11b-changed-same-path
shasum -a 256 work/k/k.html > out/11b.html.sha
run 11c-changed-fresh-outdir work/k $A finalize lifecycle $H/in/ok-v2.json k.html --out-dir k.review-2 --json
ls_ work/k 11c-changed-fresh-outdir
# 12 인자 오류
run 12a-noargs work/a $A finalize --json
run 12b-unknown-option work/a $A finalize lifecycle $H/in/ok.json z.html --bogus --json
run 12c-unknown-option-text work/a $A finalize lifecycle $H/in/ok.json z.html --bogus
run 12d-bad-type work/a $A finalize nosuch $H/in/ok.json z.html --json
run 12e-outdir-novalue work/a $A finalize lifecycle $H/in/ok.json z.html --out-dir
run 12f-four-positional work/a $A finalize lifecycle $H/in/ok.json z.html extra --json
run 12g-output-ext work/a $A finalize lifecycle $H/in/ok.json z.txt --json
run 12h-missing-input work/a $A finalize lifecycle $H/in/none.json z.html --json
run 12i-quality-bad work/a $A finalize lifecycle $H/in/ok.json z.html --quality gold --json
run 12j-writing-nonexplainer work/a $A finalize lifecycle $H/in/ok.json z.html --writing strict --json
run 12k-receipt-ext work/a $A finalize lifecycle $H/in/ok.json q.html --receipt r.txt --json
# 13 진단 8개 상한: 모든 state 에서 id 제거(스키마 오류 다수)
mkdir -p work/m; run 13-many-errors work/m $A finalize lifecycle $H/in/many-errors.json m.html --json
python3 -c "
import json;s=json.load(open('work/m/m.finalize-summary.json'));print(s['diagnosticSummary']);print([d['code'] for d in s['diagnostics']])
r=json.load(open('work/m/m.finalize.json'));print(len(r['diagnostics']))" > out/13.summary.txt
