# agent-browser initial capture

## Scope

- Repository: `https://github.com/vercel-labs/agent-browser`
- Local checkout: `/Users/kkh/Desktop/oss-analysis/repos/agent-browser`
- Artifact root: `/Users/kkh/Desktop/oss-analysis/artifacts/agent-browser`
- Report type: initial capture, not a full source-verified architecture report.

## Completed capture work

1. DeepWiki baseline extraction completed first, following the DeepWiki-first workflow.
   - Output: `artifacts/agent-browser/deepwiki/`
   - Manifest: `artifacts/agent-browser/deepwiki/manifest.json`
   - TOC: `artifacts/agent-browser/deepwiki/toc.md`
   - English pages: `artifacts/agent-browser/deepwiki/pages-md/`
   - Page metadata: `artifacts/agent-browser/deepwiki/pages-meta/`
   - Completeness check: `artifacts/agent-browser/deepwiki/completeness-check.json`
2. GitHub repository cloned into `repos/agent-browser`.
3. Repository metadata captured in `artifacts/agent-browser/repo-metadata.txt`.
4. GitHub API metadata captured in `artifacts/agent-browser/github-metadata.json`.
5. Static language summary captured with `tokei`.
   - `artifacts/agent-browser/static-analysis/tokei.txt`
   - `artifacts/agent-browser/static-analysis/tokei.json`
6. Tracked-file inventory captured.
   - `artifacts/agent-browser/static-analysis/tracked-files.txt`
   - `artifacts/agent-browser/static-analysis/top-level-file-counts.txt`

## Execution verification

### DeepWiki extraction

Command shape:

```bash
python3 /Users/kkh/.hermes/profiles/oss-analyst/skills/research/deepwiki-markdown-extraction/scripts/deepwiki_extract.py \
  vercel-labs/agent-browser \
  --out artifacts/agent-browser/deepwiki \
  --request-delay 1.0
```

Observed output:

```text
[start] vercel-labs/agent-browser
[index] OK
[toc] 41
[match] 41/41
[write] OK
Done: 41/41 missing=0
```

Filesystem completeness from `artifacts/agent-browser/deepwiki/completeness-check.json`:

```json
{
  "toc_count": 41,
  "manifest_missing_pages_count": 0,
  "filesystem_pages_md_count": 41,
  "filesystem_pages_meta_count": 41,
  "filesystem_missing_count": 0
}
```

### Git checkout

From `artifacts/agent-browser/repo-metadata.txt`:

```text
branch: main
head_sha: 2c7991c9eccca1c9db6eee1a26a713414778de5a
describe: v0.27.3
remote_url: https://github.com/vercel-labs/agent-browser.git
latest_commit: Prepare v0.27.3 release (#1446)
```

`status_short` was empty at capture time, so the checkout was clean.

### Static summary

`tokei` counted 321 source/documentation files and 145,079 total lines in the analyzed tree. Main language/file groups from `artifacts/agent-browser/static-analysis/tokei.txt`:

- Rust: 71 files, 56,073 lines
- TSX: 90 files, 8,851 lines
- TypeScript: 44 files, 4,465 lines
- MDX: 33 files, 5,351 lines
- Markdown: 25 files, 5,075 lines

Tracked Git file count from `tracked-files.txt`: 344 files.

Top tracked directories from `top-level-file-counts.txt`:

```text
docs        107
cli         80
packages    53
examples    30
skill-data  21
evals       16
scripts     10
benchmarks   8
```

## Source-verified initial facts

These are verified only to the level needed for initial capture. They should be revisited before writing a full architecture report.

1. The project describes itself as a browser automation CLI for AI agents with a native Rust CLI. Evidence: `repos/agent-browser/README.md:1-3`.
2. The npm package is named `agent-browser`, version `0.27.3`, exposes the `agent-browser` binary at `./bin/agent-browser.js`, uses `pnpm@11.1.3`, and requires Node.js `>=24.0.0`. Evidence: `repos/agent-browser/package.json:1-19`.
3. Source build instructions require Node.js 24+, pnpm 11+, and Rust. Evidence: `repos/agent-browser/README.md:43-55` and `repos/agent-browser/README.md:75-79`.
4. The Rust crate is also named `agent-browser`, version `0.27.3`, with repository and homepage metadata matching the GitHub project and docs site. Evidence: `repos/agent-browser/cli/Cargo.toml:1-12`.
5. The Rust CLI entry module wires modules for chat, commands, connection, doctor, flags, install, native, output, skills, upgrade, and validation. Evidence: `repos/agent-browser/cli/src/main.rs:1-14`.
6. The native layer currently exposes modules for browser/CDP control, daemon, interactions, network, policy, providers, React inspection, recording, screenshot, snapshot, state, storage, streaming, tracing, and WebDriver support. Evidence: `repos/agent-browser/cli/src/native/mod.rs:1-44`.
7. The workspace includes root package, `packages/*`, and `docs` as pnpm workspace packages. Evidence: `repos/agent-browser/pnpm-workspace.yaml:1-4`.
8. CI checks version sync, Rust formatting, clippy, Rust tests, dashboard build, cross-target Rust tests, native e2e tests with Chrome, and Windows integration. Evidence: `repos/agent-browser/.github/workflows/ci.yml:10-131` and `repos/agent-browser/.github/workflows/ci.yml:133-180`.
9. The repository's own `AGENTS.md` says pnpm is required for JS/package workflows, code output must avoid emojis, CLI flags must use kebab-case, and user-facing feature changes must update CLI help, README, skill data, docs, and inline comments. Evidence: `repos/agent-browser/AGENTS.md:5-33`.

## DeepWiki baseline captured but not yet source-verified

DeepWiki produced 41 pages covering:

- Overview and getting started
- Architecture and system overview
- CLI client, daemon layer, browser control, communication protocol
- sessions/state, refs, snapshots, command execution flow
- command reference
- security topics
- advanced topics such as cloud browser providers, iOS automation, network recording, dashboard, diffing
- development, CI/CD, project structure, tests, examples, glossary

Important note: these DeepWiki pages are external baseline material under `artifacts/agent-browser/deepwiki/pages-md/`. They should not be treated as final facts until checked against `repos/agent-browser`.

## Recommended next steps

1. Run graphify after adding a repo-local `.graphifyignore` or using an artifact output directory that excludes generated/build folders.
2. Write source-verified `reports/agent-browser/architecture.md`, focusing first on:
   - CLI parse and dispatch flow: `cli/src/main.rs`, `cli/src/commands.rs`, `cli/src/flags.rs`
   - daemon and browser control: `cli/src/native/daemon.rs`, `cli/src/native/browser.rs`, `cli/src/native/cdp/`
   - state/snapshot/ref mechanics: `cli/src/native/state.rs`, `cli/src/native/snapshot.rs`, `cli/src/native/element.rs`
   - security boundaries: `cli/src/native/policy.rs`, `cli/src/native/auth.rs`, `cli/src/native/network.rs`
3. Produce `reports/agent-browser/deepwiki-comparison.md` by checking DeepWiki architecture claims against current source paths.
4. Update `wiki/projects/agent-browser.md` only after the first source-verified architecture pass.
