#!/bin/sh
# Builds scratch git repos next to this script. Remotes are only names; nothing is ever fetched.
#   repo/            origin https://github.com/example/demo.git
#   repo-ssh/        origin git@github.com:Example/Demo.git
#   repo-selfhosted/ origin https://git.example.com/example/demo
#   repo-noorigin/   no remote
# All four hold the same commit (fixed dates => same SHA): src/a.txt = 3 lines.
# repo/ then gets an UNCOMMITTED edit (6 lines in the working tree) to show checks use committed bytes.
set -e
cd "$(dirname "$0")"
export GIT_AUTHOR_DATE='2026-01-01T00:00:00Z' GIT_COMMITTER_DATE='2026-01-01T00:00:00Z'
mk() {
  rm -rf "$1" && mkdir "$1" && cd "$1"
  git init -q -b main
  git config user.email demo@example.com && git config user.name demo
  [ -n "$2" ] && git remote add origin "$2"
  mkdir src && printf 'alpha\nbeta\ngamma\n' > src/a.txt && printf 'x' > src/nolines.txt
  git add . && git commit -q -m c1
  git rev-parse HEAD > ../repo-sha.txt
  cd ..
}
mk repo https://github.com/example/demo.git
mk repo-ssh git@github.com:Example/Demo.git
mk repo-selfhosted https://git.example.com/example/demo
mk repo-noorigin ""
printf 'alpha\nbeta\ngamma\nd\ne\nf\n' > repo/src/a.txt
