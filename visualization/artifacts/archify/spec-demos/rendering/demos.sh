#!/bin/sh
# rendering 스펙의 실행 확인. 설치본(레포와 바이트 동일)의 archify render만 쓴다.
# 사용: sh demos.sh   (이 폴더에서). 결과: summary.txt (HTML은 크기가 커서 out/에 만들었다가 지운다)
CLI=/Users/kkh/.claude/skills/archify/bin/archify.mjs
cd "$(dirname "$0")"; mkdir -p out; : > summary.txt
log() { echo "$*" | tee -a summary.txt; }
# 1) 타입별 예제와 최소 입력: 종료 코드, stdout, SVG viewBox, 슬롯 흔적
for f in in/*.json in/min/min.architecture.json in/min/t1.tree.json in/min/w1.waterfall.json in/min/e1.timeline.json in/min/s1.sequence.json in/min/l1.lifecycle.json in/min/d1.dataflow.json in/min/boundary.architecture.json in/min/fr.architecture.json; do
  b=$(basename "$f" .json); t=${b##*.}
  node "$CLI" render "$t" "$f" "out/$b.html" >"out/$b.out" 2>"out/$b.err" </dev/null; rc=$?
  log "$b exit=$rc stdout_is_abs_path=$(grep -c '^/' out/$b.out) stderr_bytes=$(wc -c <out/$b.err | tr -d ' ') $(grep -o '<svg viewBox="[^"]*"' out/$b.html) json_in_html=$(grep -c diagram_type out/$b.html) cards=$(grep -c 'class="card"' out/$b.html) nodes=$(grep -o 'data-node-id=' out/$b.html | wc -l | tr -d ' ') edges=$(grep -o 'data-edge-from=' out/$b.html | wc -l | tr -d ' ')"
done
# 2) 슬롯 위치(최소 architecture, locale=ko, preset=blueprint, 제목에 $&와 </script>)
log "--- slots in min.architecture"
grep -n -o '<html [^>]*>\|<title>[^<]*</title>\|<h1>[^<]*</h1>\|<p class="subtitle">[^<]*</p>\|id="archify-i18n-data"\|id="archify-software-notices"' out/min.architecture.html | head -8 | tee -a summary.txt
# 3) 실패: 출력 파일을 만들지 않거나 기존 파일을 건드리지 않는다
echo seed > out/keep.html
python3 - <<'PY'
import json
d=json.load(open('in/min/min.architecture.json')); d['components'][1]['pos']=[100,80]; json.dump(d,open('out/overlap.json','w'))
d=json.load(open('in/min/min.architecture.json')); d['meta']['viewBox']=[320,240]; json.dump(d,open('out/oob.json','w'))
PY
node "$CLI" render architecture out/overlap.json out/keep.html >/dev/null 2>out/overlap.err </dev/null; log "overlap exit=$? keep.html=$(cat out/keep.html) first_stderr=$(grep -m1 '^\[' out/overlap.err | cut -c1-60)"
node "$CLI" render architecture out/oob.json out/oob.html >/dev/null 2>out/oob.err </dev/null; log "oob exit=$? created=$(ls out/oob.html 2>/dev/null | wc -l | tr -d ' ') $(grep -m1 '^\[' out/oob.err | cut -c1-110)"
mkdir -p out/dir.html; node "$CLI" render architecture in/min/min.architecture.json out/dir.html >/dev/null 2>out/dir.err </dev/null; log "dir-target exit=$? $(grep -m1 '^\[' out/dir.err | cut -c1-70)"
node "$CLI" render architecture in/min/min.architecture.json out/x.txt >/dev/null 2>out/x.err </dev/null; log "non-html exit=$? $(grep -m1 '^\[' out/x.err | cut -c1-60)"
# 4) 기존 파일 교체 시 모드 유지, 새 하위 폴더 생성
echo old > out/mode.html; chmod 640 out/mode.html
node "$CLI" render architecture in/min/min.architecture.json out/mode.html >/dev/null </dev/null; log "mode kept: $(ls -l out/mode.html | cut -c1-10) leftover_tmp=$(ls -A out | grep -c archify-render)"
node "$CLI" render architecture in/min/min.architecture.json out/newdir/deep/x.html >/dev/null </dev/null; log "mkdir -p: $(ls out/newdir/deep)"
# 5) 진단 JSON 모드(렌더러 직접 호출, stderr에 한 줄 JSON)과 --layout-json
R=/Users/kkh/.claude/skills/archify/renderers
ARCHIFY_DIAGNOSTIC_FORMAT=json node $R/architecture/render-architecture.mjs out/overlap.json out/keep.html 2>out/overlap.diag.json >/dev/null </dev/null
log "diag-json exit=$? $(python3 -c "import json;d=json.load(open('out/overlap.diag.json'));print(d['ok'],d['source'],d['diagnostics'][0]['code'])")"
node $R/architecture/render-architecture.mjs out/overlap.json --layout-json >out/overlap.layout.json 2>/dev/null </dev/null
log "layout-json(overlap) exit=$? keys=$(python3 -c "import json;print(','.join(json.load(open('out/overlap.layout.json')).keys()))")"
# 6) 근거 슬롯: --repo-root + meta.repository + sources
node "$CLI" render architecture in/min/evidence.architecture.json out/ev.html --repo-root /Users/kkh/Desktop/oss-analysis/visualization/repos/archify >/dev/null </dev/null
log "evidence slot count=$(grep -c 'id="archify-source-evidence-data"' out/ev.html) without_repo=$(grep -c 'id="archify-source-evidence-data"' out/min.architecture.html)"
# 7) --quality showcase는 svg 루트 속성만 바꾼다(예)
node "$CLI" render architecture in/min/min.architecture.json out/q.html --quality showcase >/dev/null </dev/null
log "quality: min=$(grep -o 'data-quality-profile="[a-z]*"\( data-quality-gates="[a-z]*"\)\?' out/min.architecture.html | head -1) showcase=$(grep -o 'data-quality-profile="[a-z]*"\( data-quality-gates="[a-z]*"\)\?' out/q.html | head -1)"
# 8) 인자 없이 렌더러 직접 호출: 번들 예제 + 그 meta.output 이름으로 현재 디렉터리에 쓴다
mkdir -p out/default; (cd out/default && node $R/architecture/render-architecture.mjs >stdout.txt 2>/dev/null </dev/null; echo "default-example exit=$? stdout=$(cat stdout.txt | sed 's#.*/out/#out/#') created=$(find . -name '*.html' | tr '\n' ' ')") | tee -a ../../summary.txt
rm -f out/*.html out/dir.html/ 2>/dev/null; rmdir out/dir.html 2>/dev/null; rm -rf out/newdir out/default/*.html
