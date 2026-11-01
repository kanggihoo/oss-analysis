#!/bin/sh
# update 확인 스크립트(네트워크 차단 모드)와 recover-output 사용법 경로. 네트워크·파일 변경 없음.
S=/Users/kkh/.claude/skills/archify
cd "$(dirname "$0")"
echo "== check-update (ARCHIFY_UPDATE_CHECK_DISABLED=1)"; ARCHIFY_UPDATE_CHECK_DISABLED=1 node $S/scripts/check-update.mjs; echo "exit=$?"
echo "== check-update --snooze (disabled 모드: 상태 파일을 쓰지 않음)"; ARCHIFY_UPDATE_CHECK_DISABLED=1 node $S/scripts/check-update.mjs --snooze somekey; echo "exit=$?"
echo "== recover-output 인자 없음"; node $S/bin/recover-output.mjs; echo "exit=$?"
echo "== recover-output --help"; node $S/bin/recover-output.mjs --help; echo "exit=$?"
echo "== recover-output 잘못된 옵션"; node $S/bin/recover-output.mjs -x 2>&1; echo "exit=$?"
echo "== brands --json 전체 개수"; node $S/bin/archify.mjs brands --json | node -e "const r=JSON.parse(require('fs').readFileSync(0,'utf8'));const c={};r.marks.forEach(m=>c[m.category]=(c[m.category]||0)+1);console.log(r.count,JSON.stringify(c),Object.keys(r.marks[0]).join())"
echo "== brands 질의 'google' (부분 일치, 도메인/별칭)"; node $S/bin/archify.mjs brands google --json | node -e "const r=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(r.count,r.marks.map(m=>m.id).join())"
echo "== brands 대소문자·공백 질의 'Hugging Face'"; node $S/bin/archify.mjs brands "Hugging Face" --json | node -e "const r=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(r.count,r.marks.map(m=>m.id).join())"
