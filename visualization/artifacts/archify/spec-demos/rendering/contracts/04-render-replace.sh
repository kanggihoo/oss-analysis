#!/bin/sh
# 점검 2: 단일 파일 경로(render → writeDiagram → publishRegularFileBinding)로 기존 파일을 교체한 뒤 남는 것.
# 사용: sh 04-render-replace.sh  (결과: out/04-render-replace.txt, HTML은 지움)
CLI=$HOME/.claude/skills/archify/bin/archify.mjs; EX=$HOME/.claude/skills/archify/examples
cd "$(dirname "$0")"; W=out/work-r; rm -rf $W; mkdir -p $W; : > out/04-render-replace.txt
log() { echo "$*" | tee -a out/04-render-replace.txt; }
node $CLI render tree $EX/payment-platform.tree.json $W/a.html >/dev/null; log "first : $(ls -A $W | tr '\n' ' ') inode=$(ls -i $W/a.html | cut -d' ' -f1) links=$(ls -l $W/a.html | awk '{print $2}')"
node $CLI render tree $EX/payment-platform.tree.json $W/a.html >/dev/null; log "second: $(ls -A $W | tr '\n' ' ') inode=$(ls -i $W/a.html | cut -d' ' -f1) links=$(ls -l $W/a.html | awk '{print $2}')  (inode가 바뀌면 rename 덮어쓰기와 같은 관찰 결과, 하드링크 교체)"
echo old > $W/b.html; ln $W/b.html $W/b-alias.html
node $CLI render tree $EX/payment-platform.tree.json $W/b.html >/dev/null 2>$W/err.txt; log "hardlinked target: exit=$? $(grep -m1 '^\[' $W/err.txt | cut -c1-90) b.html=$(cat $W/b.html)"
echo '{"schemaVersion":1,"receiptId":"11111111-1111-4111-8111-111111111111","pid":4194000}' > $W/.archify-delivery-lock.json
node $CLI render tree $EX/payment-platform.tree.json $W/c.html >/dev/null; log "render with delivery lock present: exit=$? c.html=$(ls $W/c.html)"
rm -rf $W
