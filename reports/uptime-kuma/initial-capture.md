# Uptime Kuma initial capture

- Repo: `louislam/uptime-kuma`
- Local checkout: `repos/uptime-kuma`
- DeepWiki baseline: `artifacts/uptime-kuma/deepwiki/`
- Capture date: 2026-07-03

## Completed capture work

- Cloned the repository into `repos/uptime-kuma`.
- Captured the current git metadata in `artifacts/uptime-kuma/repo-metadata.txt`.
- Extracted the DeepWiki baseline into `artifacts/uptime-kuma/deepwiki/`.
- Saved GitHub metadata to `artifacts/uptime-kuma/github-metadata.json`.
- Saved tracked-file inventories and tree counts under `artifacts/uptime-kuma/static-analysis/`.
- Saved a filesystem/manifest completeness check to `artifacts/uptime-kuma/deepwiki/completeness-check.json`.

## Verification snapshot

### Git / checkout

- Branch: `master`
- HEAD: `b4ce00530ef7a343ed921cb72a5a351b51e7118f`
- Describe: `2.4.0-37-gb4ce0053`
- Remote: `https://github.com/louislam/uptime-kuma.git`
- Working tree: clean

Source: `artifacts/uptime-kuma/repo-metadata.txt`

### DeepWiki baseline

- TOC pages: `37`
- Pages extracted: `37`
- Missing pages: `0`

Source: `artifacts/uptime-kuma/deepwiki/manifest.json`

### Static summary

- Tracked files: `749`
- Top-level tracked-file winners: `src/`, `server/`, `db/`

Sources:
- `artifacts/uptime-kuma/static-analysis/tracked-files.txt`
- `artifacts/uptime-kuma/static-analysis/top-level-file-counts.txt`
- `artifacts/uptime-kuma/static-analysis/source-tree-counts.txt`

## Source-verified initial facts

### Project positioning and runtime requirements

The README describes Uptime Kuma as an easy-to-use self-hosted monitoring tool. It lists HTTP(s), TCP, keyword, JSON query, WebSocket, ping, DNS, push, Steam, and Docker-container monitoring, plus multiple status pages, certificate info, proxy support, and 2FA.

- `README.md:5-7`
- `README.md:24-37`

The non-Docker install section says the project requires Node.js `>= 20.4` plus Git and pm2.

- `README.md:68-80`

### Packaging / scripts

`package.json` identifies the package as `uptime-kuma`, version `2.4.0`, MIT licensed, and requires Node.js `>= 20.4.0`.

- `package.json:2-10`

Its scripts define the server entrypoint and the main checks:

- `start-server`: `node server/server.js`
- `start-server-dev`: `cross-env NODE_ENV=development node server/server.js`
- `test`: `npm run test-backend && npm run test-e2e`
- `test-backend`: `node test/test-backend.mjs`

- `package.json:21-35`

The lockfile confirms a `package-lock.json`-based npm workflow.

- `package-lock.json:1-10`

### Backend entrypoint and runtime wiring

`server/server.js` is the backend entrypoint. It prints a welcome message, loads `dotenv`, checks the current Node.js version against `package.json`, and then wires the Express / socket.io server by importing `UptimeKumaServer`.

- `server/server.js:1-5`
- `server/server.js:14-22`
- `server/server.js:48-58`
- `server/server.js:113-116`

`server/config.js` sets the default port to `3001`, derives the hostname from CLI flags / env, and enables SSL only when both key and cert are present.

- `server/config.js:10-24`

### Frontend entrypoint

`src/main.js` is the Vue frontend bootstrap. It creates the app, installs router/i18n/toast plugins, mounts `#app`, and registers the service worker used for web push.

- `src/main.js:1-18`
- `src/main.js:28-45`
- `src/main.js:47-59`

### CI / test surface

The main CI test workflow (`.github/workflows/auto-test.yml`) runs `npm clean-install --no-fund`, then `npm run build`, then `npm run test-backend` on Node 20/24/25 matrix jobs.

- `.github/workflows/auto-test.yml:43-64`

The validation workflow checks language JSON files, knex migration filenames, and package.json formatting/consistency.

- `.github/workflows/validate.yml:38-50`

## DeepWiki baseline notes

DeepWiki extraction succeeded with `toc_count=37`, `matched_pages_count=37`, and `missing_pages_count=0`. The extracted baseline is stored under:

- `artifacts/uptime-kuma/deepwiki/raw/index.html`
- `artifacts/uptime-kuma/deepwiki/toc.json`
- `artifacts/uptime-kuma/deepwiki/pages-md/`
- `artifacts/uptime-kuma/deepwiki/pages-meta/`

This is external baseline material only; the claims above were verified separately against the local checkout.

## Test / verification result

I ran the CI-shaped backend verification in the repo checkout using:

- `npm clean-install --no-fund`
- `npm run test-backend`

Observed result:

- `npm clean-install --no-fund` completed successfully.
- The install emitted deprecation warnings plus `allow-scripts` pending-review warnings, but it finished and added 1268 packages.
- `npm run test-backend` failed because the environment has Docker installed but the daemon/socket is unavailable (`failed to connect to the docker API at unix:///var/run/docker.sock`), and many backend tests in this repo require container runtime access.

Logs:

- `artifacts/uptime-kuma/static-analysis/npm-clean-install.log`
- `artifacts/uptime-kuma/static-analysis/npm-test-backend.log`

## Recommended next steps

1. If you want a full backend verification here, start the Docker daemon and rerun `npm run test-backend`.
2. Run a focused code-map pass around `server/`, `src/`, and `db/` if you want a deeper architecture summary.
3. If the goal is durable synthesis, add a `wiki/projects/uptime-kuma.md` page after the baseline is fully source-checked.
