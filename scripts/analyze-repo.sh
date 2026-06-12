#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <github-url-or-local-repo-path> [repo-name]" >&2
  exit 2
fi

INPUT="$1"
ROOT="${OSS_LAB_ROOT:-/Users/kkh/Desktop/oss-analysis}"
REPOS="${OSS_REPOS_PATH:-$ROOT/repos}"
ARTIFACTS_ROOT="${OSS_ARTIFACTS_PATH:-$ROOT/artifacts}"
REPORTS_ROOT="${OSS_REPORTS_PATH:-$ROOT/reports}"

mkdir -p "$REPOS" "$ARTIFACTS_ROOT" "$REPORTS_ROOT"

if [ $# -ge 2 ]; then
  NAME="$2"
else
  NAME="$(basename "$INPUT" .git)"
fi

REPO_DIR="$REPOS/$NAME"
ARTIFACTS="$ARTIFACTS_ROOT/$NAME"
REPORTS="$REPORTS_ROOT/$NAME"

mkdir -p "$ARTIFACTS/static-analysis" "$ARTIFACTS/deepwiki" "$REPORTS"

if [[ "$INPUT" == http://* || "$INPUT" == https://* || "$INPUT" == git@* ]]; then
  if [ ! -d "$REPO_DIR/.git" ]; then
    git clone "$INPUT" "$REPO_DIR"
  else
    git -C "$REPO_DIR" fetch --all --tags --prune
    git -C "$REPO_DIR" pull --ff-only || true
  fi
else
  REPO_DIR="$INPUT"
  NAME="$(basename "$REPO_DIR")"
  ARTIFACTS="$ARTIFACTS_ROOT/$NAME"
  REPORTS="$REPORTS_ROOT/$NAME"
  mkdir -p "$ARTIFACTS/static-analysis" "$ARTIFACTS/deepwiki" "$REPORTS"
fi

cd "$REPO_DIR"

{
  echo "repo_dir=$REPO_DIR"
  echo "name=$NAME"
  echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git rev-parse HEAD 2>/dev/null | sed 's/^/commit=/' || true
  git remote get-url origin 2>/dev/null | sed 's/^/origin=/' || true
} > "$ARTIFACTS/repo-metadata.txt"

if command -v pygount >/dev/null 2>&1; then
  pygount --format=summary     --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,dist,build,.next,.tox,vendor,third_party,target"     . > "$ARTIFACTS/static-analysis/pygount.txt" 2>&1 || true
else
  echo "pygount not found" > "$ARTIFACTS/static-analysis/pygount.txt"
fi

if command -v tokei >/dev/null 2>&1; then
  tokei . > "$ARTIFACTS/static-analysis/tokei.txt" 2>&1 || true
else
  echo "tokei not found" > "$ARTIFACTS/static-analysis/tokei.txt"
fi

if command -v gh >/dev/null 2>&1; then
  gh repo view --json name,owner,description,url,stargazerCount,forkCount,licenseInfo,defaultBranchRef,pushedAt     > "$ARTIFACTS/static-analysis/github-repo-view.json" 2> "$ARTIFACTS/static-analysis/github-repo-view.err" || true
fi

if command -v graphify >/dev/null 2>&1; then
  graphify . --wiki > "$ARTIFACTS/static-analysis/graphify-run.log" 2>&1 || true
  if [ -d graphify-out ]; then
    mkdir -p "$ARTIFACTS/graphify"
    rsync -a --delete graphify-out/ "$ARTIFACTS/graphify/" || cp -R graphify-out/. "$ARTIFACTS/graphify/"
  fi
else
  echo "graphify not found" > "$ARTIFACTS/static-analysis/graphify-run.log"
fi

if [ -d .understand-anything ]; then
  mkdir -p "$ARTIFACTS/understand-anything"
  rsync -a --delete .understand-anything/ "$ARTIFACTS/understand-anything/" || cp -R .understand-anything/. "$ARTIFACTS/understand-anything/"
fi

cat > "$REPORTS/README.md" <<EOF
# $NAME analysis reports

Generated artifact directory: \`$ARTIFACTS\`

Recommended next step for Hermes:

1. Read \`$ARTIFACTS/repo-metadata.txt\`.
2. Read static analysis outputs under \`$ARTIFACTS/static-analysis/\`.
3. If present, read \`$ARTIFACTS/graphify/GRAPH_REPORT.md\` and \`$ARTIFACTS/graphify/wiki/index.md\`.
4. Check DeepWiki manually: \`https://deepwiki.com/<owner>/$NAME\`.
5. Verify claims against local source files in \`$REPO_DIR\`.
6. Write overview, architecture, code-map, dependency-analysis, and risk-report.
EOF

echo "Repo: $REPO_DIR"
echo "Artifacts: $ARTIFACTS"
echo "Reports: $REPORTS"
