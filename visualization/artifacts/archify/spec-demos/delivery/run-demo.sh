#!/bin/bash
# deliver 실험: 설치본 archify.mjs를 scratch(work/) 안에서만 실행한다.
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
export ARCHIFY_UPDATE_CHECK_DISABLED=1
HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$HERE/work"; mkdir -p "$HERE/work"; cp -R "$HERE/in" "$HERE/work/in"; cd "$HERE/work"
run(){ echo; echo "\$ archify $*"; $A "$@" </dev/null; echo "[exit $?]"; }
ls_(){ echo "-- ls ${1:-.}"; ls -A "${1:-.}" | sed 's/^/   /'; }
sha(){ shasum -a 256 "$1" | cut -c1-16; }

echo "=== 1. 첫 전달 (CLI 경로 없음 -> meta.output)"
run deliver lifecycle in/ok.json
ls_ ; echo "-- meta-default.delivery.json"; cat meta-default.delivery.json
echo "html sha $(sha meta-default.html)"; RID1=$(grep receiptId meta-default.delivery.json)

echo; echo "=== 2. 같은 경로 재전달 (같은 입력)"
run deliver lifecycle in/ok.json
echo "html sha $(sha meta-default.html)"; grep receiptId meta-default.delivery.json; echo "(1차 $RID1)"
ls_

echo; echo "=== 3. CLI 인자 > meta.output"
run deliver lifecycle in/ok.json cli/out.html --json
ls_ ; ls_ cli

echo; echo "=== 4. 실패 시도: 스키마 오류 입력을 기존 출력 경로에 (직전 파일 보존?)"
BEFORE=$(sha meta-default.html)
run deliver lifecycle in/bad-schema.json --json
echo "html sha before $BEFORE after $(sha meta-default.html)"
echo "-- meta-default.delivery.json (실패 후)"; cat meta-default.delivery.json
ls_
run check meta-default.html --json --require-provenance
run check meta-default.html

echo; echo "=== 5. 성공 재전달로 복구"
run deliver lifecycle in/ok-v2.json
cat meta-default.delivery.json; run check meta-default.html --require-provenance

echo; echo "=== 6. 처음 쓰는 경로에서 실패 (이전 산출물 없음) + 새 디렉터리"
run deliver lifecycle in/bad-schema.json fresh/dir/never.html
ls_ ; ls_ fresh/dir

echo; echo "=== 7. 입력과 같은 경로"
cp in/ok.json same.html
run deliver lifecycle same.html same.html --json
ln -s ok.json in/link.html
run deliver lifecycle in/ok.json in/link.html --json
run deliver lifecycle in/ok.json ./in/../in/ok.json
ls_ in

echo; echo "=== 8. CLI 경로 종류"
run deliver lifecycle in/ok.json out.txt
run deliver lifecycle in/ok.json out.htm
run deliver lifecycle in/ok.json dir/
run deliver lifecycle in/ok.json up/../rel/x.html
run deliver lifecycle in/ok.json "$HERE/work/abs/y.html"
mkdir -p outside; (cd outside && run deliver lifecycle ../in/ok.json ../up-out.html); ls_
run deliver lifecycle in/ok.json Mixed.HTML
ls_
run deliver lifecycle in/ok.json CamelCase.html
ls_
ln -s target.txt lnk.html; run deliver lifecycle in/ok.json lnk.html
run deliver lifecycle in/ok.json con.html

echo; echo "=== 9. meta.output 규칙 (CLI 인자를 줘도 meta.output을 먼저 검증)"
for n in meta-abs meta-dotdot meta-backslash meta-con meta-txt meta-nodir-dotdot meta-missing; do
  echo "--- $n"; run deliver lifecycle in/$n.json cli9/$n.html --json
done
ls_

echo; echo "=== 10. 인자 오류"
run deliver
run deliver lifecycle
run deliver nosuchtype in/ok.json
run deliver lifecycle in/ok.json a.html b.html
run deliver lifecycle in/ok.json --bogus
run deliver lifecycle in/ok.json --bogus --json
run deliver lifecycle in/nope.json x10.html --json
echo '{bad' > in/badjson.json; run deliver lifecycle in/badjson.json x10.html
ls_
