#!/bin/sh
# 기준 SHA a44493f의 순수 함수만 소스에서 줄 범위로 뽑아 실행한다. 네트워크, claude CLI, npm 실행 없음.
# 복사한 범위: src/pkg/manifest.ts:138-159, src/resources/mcp-format.ts:125-146,155-202,348-351
# 대체한 부분: import 문(type 선언으로 대체), placeholderValue(148-153: sameEnvName 보조 탐색 제거, Object.hasOwn만 남김)
set -e
REPO=/Users/kkh/Desktop/oss-analysis/repos/teamai-cli
OUT=${1:-$(dirname "$0")}
G="git -C $REPO show a44493f"
{
  echo "import crypto from 'node:crypto';"
  echo "type PackageManifest = { packages: any }; type McpServerDef = any;"
  $G:src/pkg/manifest.ts | sed -n '138,159p'
  $G:src/resources/mcp-format.ts | sed -n '125,146p'
  echo "function placeholderValue(vars: Record<string, string>, name: string): string | undefined { return Object.hasOwn(vars, name) ? vars[name] : undefined; }"
  $G:src/resources/mcp-format.ts | sed -n '155,202p'
  $G:src/resources/mcp-format.ts | sed -n '348,351p'
  echo "export { packageSetHash, renderClaude };"
} > "$OUT/copied.ts"
node "$OUT/demo.ts"
