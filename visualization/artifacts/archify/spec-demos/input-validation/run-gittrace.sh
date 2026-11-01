#!/bin/sh
# Shows the git commands verifyRepositoryEvidence runs. GIT_TRACE=<file> is inherited by its git children.
cd "$(dirname "$0")"
A="node $HOME/.claude/skills/archify/bin/archify.mjs"
rm -f out/gittrace-ev-ok.raw
GIT_TRACE="$PWD/out/gittrace-ev-ok.raw" $A validate architecture inputs/ev-ok.json --repo-root "$PWD/repo" > out/gittrace-ev-ok.stdout 2> out/gittrace-ev-ok.stderr < /dev/null
echo $? > out/gittrace-ev-ok.exit
grep 'built-in' out/gittrace-ev-ok.raw | sed "s#$PWD#<demo>#g; s#^[0-9:.]* ##" > out/gittrace-ev-ok.commands
