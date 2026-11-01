#!/bin/sh
# 딥 링크 문법 실행 확인: headless Chrome으로 file:// URL을 열고 DOM의 상태 속성을 읽는다.
# 사용: ./deeplink.sh   (Chrome 경로는 CHROME 환경변수로 바꿀 수 있음)
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
cd "$(dirname "$0")"
D="$PWD/demo.html"
PROFILE="$(mktemp -d)"
probe() {
  url="$1"
  dom="$("$CHROME" --headless=new --disable-gpu --no-sandbox --user-data-dir="$PROFILE" --window-size=1600,1000 --virtual-time-budget=4000 --dump-dom "$url" 2>/dev/null)"
  echo "## $url" | sed "s#$D#demo.html#"
  echo "$dom" > "dom-last.html"
  node probe-dom.mjs dom-last.html
}
probe "file://$D"
probe "file://$D#focus=api"
probe "file://$D#focus=api&reach=downstream"
probe "file://$D#focus=api&reach=upstream"
probe "file://$D#focus=nope"
probe "file://$D#route=users~worker"
probe "file://$D#route=worker~users"
probe "file://$D#route=users~nope"
probe "file://$D#lens=backend~database"
probe "file://$D#lens=backend~database~cloud"
probe "file://$D#relation=nope"
probe "file://$D#focus=api&route=users~worker"
probe "file://$D#lens=backend&focus=api"
probe "file://$D#view=d1"
probe "file://$D?present=1"
probe "file://$D?embed=1#focus=api"
probe "file://$D?theme=light"
rm -rf "$PROFILE" dom-last.html
