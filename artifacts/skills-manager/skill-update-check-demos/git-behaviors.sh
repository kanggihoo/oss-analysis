#!/bin/sh
# 순수 git CLI로 skills-manager의 "원본 변경 확인"이 기대는 git 동작만 재현한다.
# 대응 소스: git_fetcher.rs `unchanged_subtrees`(1236-1306)의 알고리즘을 git 명령으로 옮긴 것(libgit2 대신
# `git rev-parse <rev>:<path>`), `candidate_ref_names`/`select_remote_revision`(1650-1681)의 ls-remote 사용.
# 앱 코드는 실행하지 않았다. 사용법: sh git-behaviors.sh <빈 작업 디렉터리>
set -u
W="$1"; mkdir -p "$W"; cd "$W" || exit 1
G="git -c user.email=t@t -c user.name=t"
URL="file://$W/mono"

echo "== git: $(git --version)"
echo
echo "## A. 모노레포: skills/a 만 바뀐 커밋 뒤의 하위 트리 비교"
git init -q mono; cd mono
mkdir -p skills/a skills/b
echo root > SKILL.md; echo a1 > skills/a/SKILL.md; echo b1 > skills/b/SKILL.md
git add -A; $G commit -qm c1; C1=$(git rev-parse HEAD)
git config uploadpack.allowFilter true
echo a2 > skills/a/SKILL.md; git add -A; $G commit -qm c2; HEAD=$(git rev-parse HEAD)
cd "$W"
echo "c1=$C1"; echo "head=$HEAD"

# unchanged_subtrees 의 fetch: 빈 bare 저장소에 head 와 옛 revision 을 depth=1 blob:none 으로 한 번에 가져온다
git init -q --bare tmpA
git -C tmpA fetch -q --no-tags --depth=1 --filter=blob:none "$URL" "$C1" "$HEAD" && echo "fetch ok (exit 0)"
# 코드의 checkout_inputs(rev, subpath) = (subpath 트리 id, subpath 위쪽 각 디렉터리의 .gitattributes 항목 id 또는 없음)
inputs() { # $1=repo $2=rev $3=subpath
  t=$(git -C "$1" rev-parse "$2:$3" 2>/dev/null) || { echo NONE; return; }
  out="tree=$t"
  d=$(dirname "$3")
  while :; do
    p=".gitattributes"; [ "$d" != "." ] && p="$d/.gitattributes"
    a=$(git -C "$1" rev-parse "$2:$p" 2>/dev/null) || a=absent
    out="$out attr($p)=$a"
    [ "$d" = "." ] && break
    d=$(dirname "$d")
  done
  echo "$out"
}
cmp_pair() { # $1=repo $2=oldrev $3=newrev $4=subpath
  o=$(inputs "$1" "$2" "$4"); n=$(inputs "$1" "$3" "$4")
  if [ "$o" = "$n" ] && [ "$n" != NONE ]; then r=unchanged; else r="CHANGED(update_available)"; fi
  echo "  ($4): $r"; echo "     old: $o"; echo "     new: $n"
}
cmp_pair tmpA "$C1" "$HEAD" skills/a
cmp_pair tmpA "$C1" "$HEAD" skills/b

echo
echo "## B. 위쪽 디렉터리에 .gitattributes 가 새로 생기면 트리는 같아도 CHANGED"
cd mono
printf 'skills/b/** text eol=crlf\n' > .gitattributes; git add -A; $G commit -qm c3; H3=$(git rev-parse HEAD)
cd "$W"
git init -q --bare tmpB
git -C tmpB fetch -q --no-tags --depth=1 --filter=blob:none "$URL" "$HEAD" "$H3" && echo "fetch ok"
cmp_pair tmpB "$HEAD" "$H3" skills/b

echo
echo "## C. 서버가 모르는 옛 revision 하나가 섞이면 fetch 전체가 실패하는가 (유효한 쌍도 같이 빠지나)"
git init -q --bare tmpC
BOGUS=0123456789abcdef0123456789abcdef01234567
git -C tmpC fetch -q --no-tags --depth=1 --filter=blob:none "$URL" "$BOGUS" "$C1" "$HEAD" >err.txt 2>&1; rc=$?
sed 's/^/  git: /' err.txt; echo "  fetch exit=$rc"
echo "  fetch 뒤 head 객체가 있는가: $(git -C tmpC cat-file -t "$HEAD" 2>&1)"
echo "  fetch 뒤 c1 객체가 있는가:   $(git -C tmpC cat-file -t "$C1" 2>&1)"

echo
echo "## D. 서버가 partial clone(filter)을 허용하지 않을 때 같은 fetch"
cd mono; git config uploadpack.allowFilter false; cd "$W"
git init -q --bare tmpD
git -C tmpD fetch -q --no-tags --depth=1 --filter=blob:none "$URL" "$C1" "$HEAD" >err.txt 2>&1; rc=$?
sed 's/^/  git: /' err.txt; echo "  fetch exit=$rc"
cmp_pair tmpD "$C1" "$HEAD" skills/b

echo
echo "## E. ls-remote 후보 ref: 브랜치 main, 같은 이름의 주석 태그 main 과 v1"
cd "$W"; git init -q lsr; cd lsr
echo x > f; git add f; $G commit -qm x; git branch -M main
$G tag -a v1 -m v1; $G tag -a main -m same-name-tag 2>/dev/null
echo y > f; git add f; $G commit -qm y
cd "$W"
L="file://$W/lsr"
echo "-- branch 후보 (branch=main): refs/heads/main refs/tags/main^{} refs/tags/main"
git ls-remote "$L" refs/heads/main 'refs/tags/main^{}' refs/tags/main | sed 's/^/  /'
echo "-- tag 후보 (branch=v1): refs/heads/v1 refs/tags/v1^{} refs/tags/v1"
git ls-remote "$L" refs/heads/v1 'refs/tags/v1^{}' refs/tags/v1 | sed 's/^/  /'
echo "-- branch=None: HEAD"
git ls-remote "$L" HEAD | sed 's/^/  /'
echo "-- 존재하지 않는 ref (branch=nope): 종료코드와 출력"
git ls-remote "$L" refs/heads/nope 'refs/tags/nope^{}' refs/tags/nope >out.txt 2>&1; echo "  exit=$? bytes=$(wc -c <out.txt)"
echo "-- 접근 불가 URL (file://없는경로): 종료코드"
git ls-remote "file://$W/does-not-exist" HEAD >out.txt 2>&1; echo "  exit=$?"; sed 's/^/  /' out.txt
