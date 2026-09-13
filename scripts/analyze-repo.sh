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
TEMPLATES_ROOT="${OSS_TEMPLATES_PATH:-$ROOT/templates}"

mkdir -p "$REPOS" "$ARTIFACTS_ROOT" "$REPORTS_ROOT"

if [ $# -ge 2 ]; then
  NAME="$2"
else
  NAME="$(basename "$INPUT" .git)"
fi

REPO_DIR="$REPOS/$NAME"
ARTIFACTS="$ARTIFACTS_ROOT/$NAME"
REPORTS="$REPORTS_ROOT/$NAME"

mkdir -p "$ARTIFACTS/static-analysis" "$ARTIFACTS/deepwiki" "$REPORTS/diagrams" "$REPORTS/questions"

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
  mkdir -p "$ARTIFACTS/static-analysis" "$ARTIFACTS/deepwiki" "$REPORTS/diagrams" "$REPORTS/questions"
fi

cd "$REPO_DIR"

COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
ORIGIN_URL="$(git remote get-url origin 2>/dev/null || echo "$INPUT")"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  WORKTREE_STATUS="dirty"
else
  WORKTREE_STATUS="clean"
fi

{
  echo "repo_dir=$REPO_DIR"
  echo "name=$NAME"
  echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "commit=$COMMIT_SHA"
  echo "origin=$ORIGIN_URL"
  echo "worktree=$WORKTREE_STATUS"
} > "$ARTIFACTS/repo-metadata.txt"

if command -v pygount >/dev/null 2>&1; then
  pygount --format=summary \
    --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,dist,build,.next,.tox,vendor,third_party,target" \
    . > "$ARTIFACTS/static-analysis/pygount.txt" 2>&1 || true
else
  echo "pygount not found" > "$ARTIFACTS/static-analysis/pygount.txt"
fi

if command -v tokei >/dev/null 2>&1; then
  tokei . > "$ARTIFACTS/static-analysis/tokei.txt" 2>&1 || true
else
  echo "tokei not found" > "$ARTIFACTS/static-analysis/tokei.txt"
fi

if command -v gh >/dev/null 2>&1; then
  gh repo view --json name,owner,description,url,stargazerCount,forkCount,licenseInfo,defaultBranchRef,pushedAt \
    > "$ARTIFACTS/static-analysis/github-repo-view.json" 2> "$ARTIFACTS/static-analysis/github-repo-view.err" || true
fi

# Initial overview.md if not exists
if [ ! -f "$REPORTS/overview.md" ] && [ -f "$TEMPLATES_ROOT/overview-template.md" ]; then
  sed -e "s|<Repo Name>|$NAME|g" \
      -e "s|<URL>|$ORIGIN_URL|g" \
      -e "s|<commit-sha>|$COMMIT_SHA|g" \
      -e "s|YYYY-MM-DD|$(date +%Y-%m-%d)|g" \
      -e "s|Clean / Modified (diff 보관 여부)|$WORKTREE_STATUS|g" \
      "$TEMPLATES_ROOT/overview-template.md" > "$REPORTS/overview.md"
fi

# Initial next.md if not exists
if [ ! -f "$REPORTS/next.md" ] && [ -f "$TEMPLATES_ROOT/next-template.md" ]; then
  sed -e "s|<Repo Name>|$NAME|g" \
      -e "s|<commit-sha>|$COMMIT_SHA|g" \
      -e "s|YYYY-MM-DD|$(date +%Y-%m-%d)|g" \
      "$TEMPLATES_ROOT/next-template.md" > "$REPORTS/next.md"
fi

echo "=================================================="
echo "Repo:       $REPO_DIR"
echo "Commit:     $COMMIT_SHA ($WORKTREE_STATUS)"
echo "Artifacts:  $ARTIFACTS"
echo "Reports:    $REPORTS"
echo "Next steps:"
echo " 1. archify로 주요 구조도 및 대표 실행 흐름 생성 -> reports/$NAME/diagrams/"
echo " 2. 질문 도출 및 소스 검증 -> reports/$NAME/questions/"
echo " 3. 재사용 핵심 지식 요약 -> wiki/projects/$NAME.md"
echo " 4. 세션 마무리 시 reports/$NAME/next.md 및 wiki/log.md 갱신"
echo "=================================================="
