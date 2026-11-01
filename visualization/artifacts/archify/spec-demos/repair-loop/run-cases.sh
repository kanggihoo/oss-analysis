#!/bin/bash
# repair-loop 실험. 설치본(레포 archify/와 바이트 동일, 실행 때 diff -rq 확인)으로 실행한다.
# 각 사례: 일부러 만든 실패 입력 -> finalize --json -> 진단/supportedFixes/nextAction 관찰 -> 지시문대로 한 번 고쳐 같은 finalize 재실행.
# 출력: out/<사례>.<단계>.{stdout,stderr,exit,ls} 와 영수증 사본, 요약 digest 는 out/cases-digest.txt
H="$(cd "$(dirname "$0")" && pwd)"; cd "$H"
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
R="$H/../input-validation/repo"           # c3 용 임시 git 레포(input-validation/setup-repo.sh 가 만든 것, 읽기만)
[ -d "$R/.git" ] || sh "$H/../input-validation/setup-repo.sh"
REPO_SHA=$(cat "$H/../input-validation/repo-sha.txt")
export ARCHIFY_UPDATE_CHECK_DISABLED=1
diff -rq /Users/kkh/.claude/skills/archify /Users/kkh/Desktop/oss-analysis/visualization/repos/archify/archify > out/installed-vs-repo.diff.txt 2>&1; echo "diff-rq exit=$? (0이면 설치본=레포)" >> out/installed-vs-repo.diff.txt
rm -rf work; mkdir -p work out; : > out/cases-digest.txt
# run <이름> <작업폴더> 명령... -> out/<이름>.{stdout,stderr,exit}
run() { n=$1; d=$2; shift 2; mkdir -p "$H/work/$d"; (cd "$H/work/$d" && "$@" >"$H/out/$n.stdout" 2>"$H/out/$n.stderr"; echo $? >"$H/out/$n.exit")
  { echo "## $n  (exit $(cat out/$n.exit))"; python3 digest.py "out/$n.stdout"; } | tee -a out/cases-digest.txt; }
cp_() { cp "work/$1" "out/$2" 2>/dev/null; }
IN="$H/in"
# ---------- C1 스키마 오류 (validate 단계) ----------
run c1.1-bad c1 $A finalize architecture $IN/c1-schema.bad.architecture.json d.html --json
cp_ c1/d.finalize-summary.json c1.1.finalize-summary.json
run c1.2-fixed c1 $A finalize architecture $IN/c1-schema.fixed.architecture.json d.html --json
# ---------- C2 노드 겹침 (validate 단계, 레이아웃) ----------
run c2.1-bad c2 $A finalize architecture $IN/c2-overlap.bad.architecture.json d.html --json
cp_ c2/d.finalize-summary.json c2.1.finalize-summary.json
python3 apply_c2.py $IN/c2-overlap.bad.architecture.json out/c2.1.finalize-summary.json $IN/c2-overlap.fixed.architecture.json | tee -a out/cases-digest.txt
run c2.2-fixed c2 $A finalize architecture $IN/c2-overlap.fixed.architecture.json d.html --json
# c2.2 가 새로 드러낸 진단(layout/constraint: 'change set' 연결이 8px)은 별도 수리 시퀀스다. 메시지의 최소 24px을 넘게 github 를 오른쪽으로 더 민다(좌표는 실험자가 고름: 연결 길이 44px).
python3 - <<'PY'
import json
d=json.load(open('in/c2-overlap.fixed.architecture.json'))
for c in d['components']:
    if c['id']=='github': c['pos']=[402,270]
json.dump(d,open('in/c2-overlap.fixed2.architecture.json','w'),indent=2,ensure_ascii=False)
PY
run c2.3-fixed2 c2 $A finalize architecture $IN/c2-overlap.fixed2.architecture.json d.html --json
cp_ c2/d.finalize-summary.json c2.3.finalize-summary.json
# c2.3 의 진단은 supportedFixes 가 비어 있고 메시지 안에 'Suggested fix: set labelAt [x, y]'가 있다. nextAction.constraint 가 가리키는 'the fix its message names'.
python3 apply_c2_label.py $IN/c2-overlap.fixed2.architecture.json out/c2.3.finalize-summary.json $IN/c2-overlap.fixed3.architecture.json | tee -a out/cases-digest.txt
run c2.4-fixed3 c2 $A finalize architecture $IN/c2-overlap.fixed3.architecture.json d.html --json
# ---------- C3 근거 줄 오류 (validate 단계, repository-evidence) ----------
run c3.1-bad c3 $A finalize architecture $IN/c3-evidence.bad.architecture.json d.html --repo-root $R --json
run c3.1b-bad-no-root c3b $A finalize architecture $IN/c3-evidence.fixed.architecture.json d.html --json
run c3.2-fixed c3 $A finalize architecture $IN/c3-evidence.fixed.architecture.json d.html --repo-root $R --json
# ---------- C4 통과 후 권고(resolvedCrossovers) -> 한 번의 배치 수리 + 새 --out-dir ----------
run c4.1-first c4 $A finalize architecture $IN/c4-crossover.architecture.json d.html --quality showcase --json
cp_ c4/d.finalize-summary.json c4.1.finalize-summary.json
# 같은 출력 경로·같은 폴더에서 수정본을 다시 돌리면(--out-dir 없이): 소유권 충돌
run c4.2-same-dir c4 $A finalize architecture $IN/c4-crossover.fixed.architecture.json d.html --quality showcase --json
cp_ c4/d.finalize-summary.json c4.2.finalize-summary.json
# 지시문대로: 새 --out-dir 로 다시(같은 수정본). HTML 은 이미 교체됐으므로 바이트는 같다.
run c4.3-review-2 c4 $A finalize architecture $IN/c4-crossover.fixed.architecture.json d.html --quality showcase --out-dir review-2 --json
(cd work/c4 && find . -type f | sort) > out/c4.ls
# ---------- C5 composition/viewport-height (showcase 경고 -> deliver 실패) ----------
run c5.1-bad c5 $A finalize sequence $H/../rendering/in/async-job-roundtrip.sequence.json s.html --quality showcase --json
cp_ c5/s.finalize-summary.json c5.1.finalize-summary.json
(cd work/c5 && ls) > out/c5.1.ls
run c5.2-widen c5 $A finalize sequence $IN/c5-seq-height.fixed.sequence.json s.html --quality showcase --json
# ---------- C6 browser-check 단계 실패: standard 로 통과한 workflow 를 showcase 대신 standard 로 ----------
run c6.1-standard-workflow c6 $A finalize workflow $H/../finalize/in/release-delivery.workflow.json w.html --quality standard --json
cp_ c6/w.finalize-summary.json c6.1.finalize-summary.json
# ---------- C7 explainer prepare 실패(시작 전 실패) ----------
run c7.1-bad c7 $A finalize explainer $IN/c7-explainer.bad.archify.md x.html --json
(cd work/c7 && find . | sort) > out/c7.1.ls
run c7.2-fixed c7 $A finalize explainer $IN/c7-explainer.fixed.archify.md x.html --repo-root /Users/kkh/Desktop/oss-analysis/visualization/repos/archify --json
# ---------- C8 Chrome 없음(skipped, 종료 2) ----------
mkdir -p work/c8
ARCHIFY_CHROME=/nonexistent run c8.1-no-chrome c8 $A finalize architecture $IN/c1-schema.fixed.architecture.json d.html --json
# ---------- C9 check 단계: 산출물 변조 후 standalone check ----------
mkdir -p work/c9; (cd work/c9 && $A finalize architecture $IN/c1-schema.fixed.architecture.json d.html --json >/dev/null 2>&1; printf '\n<!-- tampered -->' >> d.html)
run c9.1-check-tampered c9 $A check d.html --require-provenance
cp_ c9/d.delivery.json c9.delivery.json
# ---------- C11 통과 후 layoutReviewRecommendation(inspect-leading-space) -> 위치만 위로 옮기고 새 --out-dir ----------
run c11.1-leading c11 $A finalize architecture $IN/c11-leading-space.architecture.json l.html --json
python3 - <<'PY'
import json
d=json.load(open('in/c11-leading-space.architecture.json'))
for c in d['components']: c['pos']=[c['pos'][0],c['pos'][1]-260]
json.dump(d,open('in/c11-leading-space.fixed.architecture.json','w'),indent=1)
PY
run c11.2-moved-up c11 $A finalize architecture $IN/c11-leading-space.fixed.architecture.json l.html --out-dir review-2 --json
# ---------- C12 경로 교차(composition/proper-crossing): nextAction.constraint 가 레이아웃 수리 문장으로 바뀐다(수리는 하지 않고 관찰만) ----------
run c12.1-crossing c12 $A finalize architecture $IN/c12-crossing.architecture.json d.html --json
cp_ c12/d.finalize-summary.json c12.1.finalize-summary.json
# ---------- C10 validate 의 frozen candidate -> nextAction.arguments, 수정 후 옛 해시를 쓰면 ----------
mkdir -p work/c10
(cd work/c10 && $A validate architecture $IN/c1-schema.fixed.architecture.json --quality showcase --json > $H/out/c10.1-validate.json 2>/dev/null; echo "validate exit=$?")
python3 - <<'PY' | tee -a out/cases-digest.txt
import json
j=json.load(open('out/c10.1-validate.json'))
print('## c10.1-validate  ok=%s candidateFrozen=%s'%(j['ok'],j.get('candidateFrozen')))
print('  candidate:',j['candidate']); print('  nextAction:',json.dumps(j['nextAction']))
json.dump([a if a!='<output.html>' else 'd.html' for a in j['nextAction']['arguments']],open('work/c10/args.json','w'))
PY
ARGS=$(python3 -c "import json;print(' '.join(json.load(open('work/c10/args.json'))))")
run c10.2-next-action c10 $A finalize $ARGS
# 후보를 고친 뒤(라벨 한 글자) 옛 해시로 다시: 시작 전 실패
python3 - <<'PY'
import json
d=json.load(open('in/c1-schema.fixed.architecture.json')); d['components'][0]['label']='Product request v2'
json.dump(d,open('in/c10-edited.architecture.json','w'),indent=2)
PY
OLD=$(python3 -c "import json;print(json.load(open('out/c10.1-validate.json'))['candidate']['sha256'])")
run c10.3-stale-hash c10 $A finalize architecture $IN/c10-edited.architecture.json d.html --quality showcase --candidate-sha256 $OLD --json
run c10.4-no-hash c10 $A finalize architecture $IN/c10-edited.architecture.json d.html --quality showcase --out-dir review-2 --json
echo done
