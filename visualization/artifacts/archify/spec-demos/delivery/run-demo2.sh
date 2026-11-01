#!/bin/bash
# deliver 실험 2: 실패 후 잔여 journal, 재전달, 심볼릭 링크·하드링크·디렉터리 대상, 변조 검출.
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
export ARCHIFY_UPDATE_CHECK_DISABLED=1
HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$HERE/work2"; mkdir -p "$HERE/work2"; cp -R "$HERE/in" "$HERE/work2/in"; cd "$HERE/work2"
run(){ echo; echo "\$ archify $*"; $A "$@" </dev/null | cut -c1-230 | grep -v '^      \|^    }\|^  }\|^    {\|^  \]'; echo "[exit ${PIPESTATUS[0]}]"; }
ls_(){ echo "-- ls ${1:-.}"; ls -A "${1:-.}" | sed 's/^/   /'; }

echo "=== A. 첫 전달 실패 -> journal 잔여 -> 같은 경로 성공 전달"
run deliver lifecycle in/bad-schema.json n/never.html
ls_ n; echo "-- journal"; cat n/never.delivery-pending.json
run deliver lifecycle in/ok.json n/never.html
ls_ n

echo; echo "=== B. HTML만 있고 provenance 없는 기존 파일 + 실패"
cp n/never.html legacy.html
run check legacy.html
run deliver lifecycle in/bad-schema.json legacy.html
ls_; echo "-- legacy.delivery.json"; cat legacy.delivery.json

echo; echo "=== C. 연속 실패 두 번 (receiptId 갱신, 파일 보존)"
run deliver lifecycle in/bad-schema.json legacy.html
grep receiptId legacy.delivery.json

echo; echo "=== D. 변조 검출"
run deliver lifecycle in/ok.json t.html
echo "<!-- tamper -->" >> t.html
run check t.html --require-provenance --json
run check t.html

echo; echo "=== E. 파일 심볼릭 링크 대상"
run deliver lifecycle in/ok.json real.html
ln -s real.html alias.html
run deliver lifecycle in/ok-v2.json alias.html
ls_; ls -l alias.html | sed 's/^/   /'; grep input real.delivery.json

echo; echo "=== F. 하드링크 / 디렉터리 대상"
ln real.html hard.html
run deliver lifecycle in/ok.json real.html --json
ls_
mkdir dirtarget.html
run deliver lifecycle in/ok.json dirtarget.html

echo; echo "=== G. 입력 경로를 meta.output으로 지정되는 경우: 입력 파일명이 .html 이고 meta.output 이 같은 이름"
cp in/ok.json selfmeta.html
node -e "const fs=require('fs');const d=JSON.parse(fs.readFileSync('selfmeta.html','utf8'));d.meta.output='selfmeta.html';fs.writeFileSync('selfmeta.html',JSON.stringify(d))"
run deliver lifecycle selfmeta.html

echo; echo "=== H. 기존 삭제 후 provenance만 남은 상태에서 전달 / provenance가 입력과 같은 이름"
rm real.html
run deliver lifecycle in/ok.json real.html
cp in/ok.json prov.delivery.json
run deliver lifecycle prov.delivery.json prov.html
ls_

echo; echo "=== I. 잔여 journal이 다른 출력 경로 전달을 막는지"
run deliver lifecycle in/bad-schema.json m1.html
run deliver lifecycle in/ok.json m2.html
ls_
