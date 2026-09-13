# claude-devtools initial capture

- Repo: `matt1398/claude-devtools`
- GitHub URL: <https://github.com/matt1398/claude-devtools>
- Local checkout: `repos/claude-devtools`
- Artifact root: `artifacts/claude-devtools`
- Capture type: DeepWiki-first baseline + local clone/static inventory

## Completed capture work

### 1. DeepWiki Markdown extraction

Command shape used:

```bash
cd /Users/kkh/Desktop/oss-analysis
python3 /Users/kkh/.hermes/profiles/oss-analyst/skills/research/deepwiki-markdown-extraction/scripts/deepwiki_extract.py \
  matt1398/claude-devtools \
  --out artifacts/claude-devtools/deepwiki \
  --request-delay 1.0
```

Observed extraction output:

```text
[start] matt1398/claude-devtools
[index] OK
[toc] 54
[match] 54/54
[write] OK
Done: 54/54 missing=0
```

DeepWiki outputs:

- Raw index HTML: `artifacts/claude-devtools/deepwiki/raw/index.html`
- Ordered TOC JSON: `artifacts/claude-devtools/deepwiki/toc.json`
- Readable TOC: `artifacts/claude-devtools/deepwiki/toc.md`
- Manifest: `artifacts/claude-devtools/deepwiki/manifest.json`
- Markdown chunks: `artifacts/claude-devtools/deepwiki/next-payload/markdown-chunks.json`
- Extracted pages: `artifacts/claude-devtools/deepwiki/pages-md/`
- Per-page metadata: `artifacts/claude-devtools/deepwiki/pages-meta/`
- Completeness check: `artifacts/claude-devtools/deepwiki/completeness-check.json`

Completeness snapshot from filesystem + manifest:

- `toc_count`: 54
- `pages-md/*.md`: 54
- `pages-meta/*.json`: 54
- Manifest `missing_pages_count`: 0
- Filesystem missing Markdown pages: 0
- Filesystem missing metadata pages: 0

### 2. Local repository clone

The repository was cloned into:

```text
/Users/kkh/Desktop/oss-analysis/repos/claude-devtools
```

Recorded metadata path:

```text
artifacts/claude-devtools/repo-metadata.txt
```

Current recorded checkout state:

```text
branch: main
head_sha: 16cc3c87c1e4d0e08ee101fb52dad1b85dbbe48a
describe: v0.5.0
status: 0 dirty entries
latest_commit: Merge pull request #198 from matt1398/feat/memory-viewer
```

### 3. GitHub metadata and static inventory

Saved files:

- GitHub REST metadata: `artifacts/claude-devtools/github-metadata.json`
- gh error/fallback note: `artifacts/claude-devtools/github-metadata.err`
- Git tracked-file inventory: `artifacts/claude-devtools/static-analysis/tracked-files.txt`
- Top-level tracked-file counts: `artifacts/claude-devtools/static-analysis/top-level-file-counts.txt`
- Source/test subtree counts: `artifacts/claude-devtools/static-analysis/source-tree-counts.txt`
- Tokei text summary: `artifacts/claude-devtools/static-analysis/tokei.txt`
- Tokei JSON summary: `artifacts/claude-devtools/static-analysis/tokei.json`

GitHub metadata note: `gh repo view` was attempted first, but this Hermes tool shell is not authenticated with GitHub CLI (`gh auth login` / `GH_TOKEN` needed), so capture fell back to the public GitHub REST API.

Static summary snapshot:

- Git tracked files: 479
- Top-level tracked-file concentration:
  - `src`: 349
  - `test`: 57
  - `resources`: 17
  - `.claude`: 11
  - `public`: 7
  - `.github`: 5
- `src/` second-level split:
  - `renderer`: 221
  - `main`: 104
  - `shared`: 20
  - `preload`: 3
- Tokei total: 430 counted files, 93,218 lines, 67,645 code lines
- Largest language surfaces by tokei:
  - TypeScript: 276 files, 56,532 lines, 38,672 code lines
  - TSX: 123 files, 22,574 lines, 18,910 code lines
  - YAML: 3 files, 11,231 lines, 8,738 code lines

## Source-verified initial facts

These facts were checked against the local checkout rather than copied from DeepWiki:

1. The project is an Electron/Vite TypeScript application. Evidence:
   - `repos/claude-devtools/package.json` declares `main: "dist-electron/main/index.cjs"`.
   - `repos/claude-devtools/package.json` scripts include `electron-vite dev`, `electron-vite build`, and `electron-builder` distribution scripts.
   - `repos/claude-devtools/package.json` dependencies/devDependencies include `electron`, `electron-vite`, `electron-builder`, `react`, `react-dom`, `vite`, `typescript`, and `vitest`.

2. The package uses `pnpm` as the package manager. Evidence:
   - `repos/claude-devtools/package.json` has `packageManager: "pnpm@10.25.0..."`.
   - `repos/claude-devtools/pnpm-lock.yaml` and `repos/claude-devtools/pnpm-workspace.yaml` are tracked.

3. The application describes itself as a desktop app for visualizing Claude Code session execution. Evidence:
   - `repos/claude-devtools/package.json` description: “Desktop app that visualizes Claude Code session execution — explore conversations, track context usage, and analyze tool calls”.
   - `repos/claude-devtools/README.md` says it reads Claude Code logs/session transcripts saved under `~/.claude/` and reconstructs tool calls, token usage, subagent activity, and context.

4. The committed source surface is split primarily into Electron main, renderer, shared, and preload areas. Evidence:
   - `artifacts/claude-devtools/static-analysis/source-tree-counts.txt` records `src/renderer`, `src/main`, `src/shared`, and `src/preload` tracked-file counts.

5. Test/quality entrypoints are present in package scripts. Evidence:
   - `repos/claude-devtools/package.json` defines `typecheck`, `lint`, `test`, `test:coverage`, `check`, and `quality` scripts.
   - `.github/workflows/ci.yml` and `.github/workflows/release.yml` are tracked according to `artifacts/claude-devtools/static-analysis/tracked-files.txt`.

## DeepWiki baseline topics captured but not yet source-verified

DeepWiki extracted 54 pages covering these high-level areas:

- Overview / Getting Started
- Architecture, Electron process model, multi-context system, IPC layer, state management
- Session discovery/parsing, project scanning, path encoding, JSONL parsing, caching
- SSH remote access and remote file operations
- Notification system
- Configuration management and Claude root detection
- HTTP sidecar server
- UI shell/session views/command palette/settings/real-time updates
- Build system, native module handling, dependency management
- Testing, CI, release/distribution, code signing/notarization, auto-updates
- Session analysis/reporting, cost/pricing
- API references and contribution guides

Important: these DeepWiki pages are external baseline material only. They should not be treated as final facts until checked against `repos/claude-devtools` source paths.

## Recommended next steps

1. Produce a source-verified architecture report under `reports/claude-devtools/architecture.md` by checking DeepWiki architecture pages against `src/main`, `src/preload`, `src/renderer`, and `src/shared`.
2. Run focused source tracing for the session ingestion path: `~/.claude/projects/.../*.jsonl` discovery → parser → chunk/session model → renderer views.
3. Verify the HTTP sidecar server and SSH remote access claims against `src/main/http/` and SSH-related source files before reporting behavior.
4. Run package quality gates only if needed for deeper analysis: `pnpm install`, then `pnpm typecheck`, `pnpm test`, and selected parser tests.
5. Optionally run graphify after this DeepWiki-first capture and store results under `artifacts/claude-devtools/graphify/`.
