#!/bin/sh
# get_skill_source_diff: ls-remote 로 revision 을 먼저 구하고(resolve_remote_revision), 그 뒤 depth-1 clone 을 만들어
# `git checkout --detach <revision>` 을 한다(checkout_revision 의 1차 경로). 그 사이 원격이 전진하면 어떻게 되는지
# git CLI 만으로 확인한다. Rust 코드는 실행하지 않았다. 네트워크 없음(file:// 임시 저장소).
set -eu
W="$1"                       # 새 스크래치 디렉터리
rm -rf "$W"; mkdir -p "$W"; cd "$W"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git init -q -b main origin
git -C origin -c user.name=t -c user.email=t@t commit -q --allow-empty -m A
echo "== 1. ls-remote 로 revision 확보 (resolve_remote_revision 1단계)"
REV=$(git ls-remote file://$W/origin refs/heads/main | cut -f1)
echo "REV=$REV"
echo "== 2. 원격 전진 (확인 사이에 push 된 커밋 B)"
git -C origin -c user.name=t -c user.email=t@t commit -q --allow-empty -m B
echo "== 3. depth-1 clone (clone_repo_ref_scoped 의 full 경로와 같은 옵션)"
git clone -q --depth 1 --branch main file://$W/origin clone
echo "clone HEAD=$(git -C clone rev-parse HEAD)"
echo "== 4. checkout --detach <옛 REV> (checkout_revision 1차 경로)"
if git -C clone checkout --detach "$REV" >/dev/null 2>&1; then echo "checkout OK"; else echo "checkout FAILED (exit $?)"; fi
echo "== 5. 같은 REV 가 clone 의 HEAD 일 때"
git -C clone checkout -q --detach HEAD && echo "checkout HEAD OK"
