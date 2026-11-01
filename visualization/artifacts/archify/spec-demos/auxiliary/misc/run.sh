#!/bin/sh
# doctor / demo / brands(조회) / preview(서버 없이 실패하는 경로만) 실험. 네트워크 사용 없음(brands capture 제외).
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
cd "$(dirname "$0")"
rm -rf out && mkdir out
echo "== doctor"; $A doctor > out/doctor.out 2>&1; echo "exit=$?"; cat out/doctor.out
echo "== demo (scratch dir)"; $A demo out/demo > out/demo.out 2>&1; echo "exit=$?"; cat out/demo.out | tail -4; ls out/demo
echo "== demo 인자 2개"; $A demo a b >/dev/null 2>&1; echo "exit=$?"
echo "== demo 알 수 없는 옵션"; $A demo --x >/dev/null 2>&1; echo "exit=$?"
echo "== brands claude --json"; $A brands claude --json > out/brands-claude.json; echo "exit=$?"; node -e "const r=require('./out/brands-claude.json');console.log(JSON.stringify({...r,marks:r.marks.map(m=>m)}).slice(0,700))"
echo "== brands (질의 없음, 텍스트)"; $A brands | head -8; echo "..."
echo "== brands 매칭 없음 (텍스트)"; $A brands zzzznotabrand; echo "exit=$?"
echo "== brands 알 수 없는 옵션"; $A brands --x >/dev/null 2>&1; echo "exit=$?"
echo "== brands capture 인자 오류(네트워크 없음)"; $A brands capture >/dev/null 2>&1; echo "exit=$?"
echo "== brands capture 비-HTTP URL(네트워크 전 단계에서 거부)"; $A brands capture ftp://example.com 2>&1 | head -2; $A brands capture ftp://example.com >/dev/null 2>&1; echo "exit=$?"
echo "== preview explainer"; $A preview explainer x.md 2>&1 | head -2; $A preview explainer x.md >/dev/null 2>&1; echo "exit=$?"
echo "== preview 알 수 없는 옵션"; $A preview workflow workflow-min.json --bogus 2>&1 | head -1; $A preview workflow workflow-min.json --bogus >/dev/null 2>&1; echo "exit=$?"
echo "== preview 알 수 없는 타입(서버 전)"; $A preview nope workflow-min.json >/dev/null 2>out/pv.err; echo "exit=$?"; head -1 out/pv.err
echo "== help"; $A help | head -3; $A --help >/dev/null; echo "exit=$?"; $A bogus >/dev/null 2>&1; echo "unknown command exit=$?"
echo "== 명령별 --help"; $A preview --help | head -3
