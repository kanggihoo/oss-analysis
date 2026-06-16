# obsidianmd/obsidian-clipper initial capture

## Snapshot

- GitHub: <https://github.com/obsidianmd/obsidian-clipper>
- Local checkout: `repos/obsidian-clipper/`
- Artifact root: `artifacts/obsidian-clipper/`
- Captured commit: `372d420481745f0332a9deae4bea4f0046360b30` (`main`, `1.6.3-2-g372d420`)
- DeepWiki baseline: `artifacts/obsidian-clipper/deepwiki/`

## Work completed

1. Ran the DeepWiki Markdown extractor against `obsidianmd/obsidian-clipper`.
   - `artifacts/obsidian-clipper/deepwiki/manifest.json` reports `toc_count=33`, `matched_pages_count=33`, `missing_pages_count=0`.
   - English DeepWiki pages are preserved under `artifacts/obsidian-clipper/deepwiki/pages-md/` as external baseline material.
2. Cloned the GitHub repository with `git clone https://github.com/obsidianmd/obsidian-clipper.git repos/obsidian-clipper`.
3. Captured repository metadata and static language summary.
   - `artifacts/obsidian-clipper/repo-metadata.txt`
   - `artifacts/obsidian-clipper/github-metadata.json`
   - `artifacts/obsidian-clipper/static-analysis/language-summary.txt`

## Source-verified initial facts

- The project describes itself as the official Obsidian Web Clipper and points users to browser-store downloads and Obsidian Help documentation. Evidence: `repos/obsidian-clipper/README.md` lines 1-18.
- The npm package is named `obsidian-clipper`, version `1.6.3`, exposes a CLI binary at `./dist/cli.cjs`, and exports `./api` at `./dist/api.mjs`. Evidence: `repos/obsidian-clipper/package.json` lines 1-14.
- Build scripts target Chrome, Firefox, and Safari; tests are run through Vitest. Evidence: `repos/obsidian-clipper/package.json` lines 15-33.
- Browser manifests exist for Chrome, Firefox, and Safari. Evidence: `repos/obsidian-clipper/src/manifest.chrome.json`, `repos/obsidian-clipper/src/manifest.firefox.json`, `repos/obsidian-clipper/src/manifest.safari.json`.
- Chrome/Firefox/Safari manifests all request broad host access for `http://*/*`, `https://*/*`, and `<all_urls>`; Safari additionally declares `nativeMessaging`. Evidence: manifest files above.
- The extension has background/content-script message flow using `webextension-polyfill` APIs. Evidence: `repos/obsidian-clipper/src/background.ts`, `repos/obsidian-clipper/src/content.ts` search hits for `browser.runtime` / `browser.tabs` / `browser.storage`.
- No GitHub Actions workflow files were found under `.github/workflows/` in this checkout; only issue templates/FUNDING were found under `.github/`.

## Static summary

`tokei` summary in `artifacts/obsidian-clipper/static-analysis/language-summary.txt` reports 324 files and 86,028 total lines in the checkout, dominated by TypeScript and JSON.

## Important caveat

DeepWiki pages are stored as an external baseline/second opinion only. Their architectural claims have not yet been fully validated against the current local checkout beyond the initial source checks listed above.

## Suggested next steps

1. Run graphify after adding/validating a `.graphifyignore` for generated/browser build output.
2. Produce `reports/obsidian-clipper/architecture.md` and `deepwiki-comparison.md` by verifying DeepWiki architecture claims against `src/background.ts`, `src/content.ts`, `src/utils/*`, and build scripts.
3. Optionally run `npm install`/`npm test` if dependency installation and test execution are desired in this workspace.
