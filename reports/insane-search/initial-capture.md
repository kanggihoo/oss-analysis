# insane-search initial capture

Date: 2026-06-28
Repo: `https://github.com/fivetaku/insane-search`
Local checkout: `repos/insane-search/`
Artifacts: `artifacts/insane-search/`

## Completed capture work

- DeepWiki baseline extracted first, per oss-analysis workflow: `artifacts/insane-search/deepwiki/`.
  - Extractor output: `[start] fivetaku/insane-search`, `[index] OK`, `[toc] 33`, `[match] 33/33`, `[write] OK`, `Done: 33/33 missing=0`.
  - Completeness artifact: `artifacts/insane-search/deepwiki/completeness-check.json`.
  - Verified counts: `toc_count=33`, `pages_md_count=33`, `pages_meta_count=33`, manifest missing pages `0`, filesystem missing Markdown/meta `0`.
- Repository cloned to `repos/insane-search/`.
- Git/repo metadata saved to `artifacts/insane-search/repo-metadata.txt`.
- GitHub REST metadata saved to `artifacts/insane-search/github-metadata.json` after `gh repo view` reported no authenticated GitHub CLI session.
- Static inventory saved under `artifacts/insane-search/static-analysis/`:
  - `tracked-files.txt`
  - `top-level-file-counts.txt`
  - `source-tree-counts.txt`
  - `tokei.txt`
  - `pygount-summary.txt`
  - `pip-install-test-deps.log`
  - `unit-tests-with-deps.log`
  - `package-mode-and-smoke-tests-with-deps.log`

## Checkout snapshot

Source: `artifacts/insane-search/repo-metadata.txt`

- Branch: `main`
- HEAD: `a16f7c1c40aeb7480c44dfb5e6ee108063ec8f8f`
- Describe: `v0.9.0`
- Latest commit: `chore: release v0.9.0 — content-safety envelope + calibrated risk scoring`
- Remote: `https://github.com/fivetaku/insane-search.git`
- Working tree status in metadata: clean/no short-status output.

GitHub REST metadata says the public repo description is `Auto-bypass for blocked websites in Claude Code — Phase 0→3 adaptive scheduler, no API keys`; primary language is Python; stars/watchers at capture were `1473`.

## Static footprint

Tracked-file inventory: `artifacts/insane-search/static-analysis/tracked-files.txt`

- Total tracked files: `53`.
- Top-level distribution from `top-level-file-counts.txt`:
  - `skills`: 38
  - `assets`: 2
  - `setup`: 2
  - single-file roots: `.claude-plugin`, `.gitignore`, changelog/disclaimer/license/platform/readme files.
- `tokei.txt` counted 47 code/document files, 7,610 total lines, including:
  - Python: 20 files, 4,047 lines / 3,253 code lines
  - Markdown: 21 files, 2,255 lines
  - JavaScript: 3 files, 417 lines
  - Shell: 1 file, 137 lines
  - YAML: 1 file, 162 lines

## Source-verified initial facts

These are verified against the current checkout, not accepted from DeepWiki alone.

1. **Project positioning / boundary claim**
   - `README.md:5-10` names the project `insane-search` and describes it as a resilient public-page reader for Claude Code with no API keys or proxy setup.
   - `README.md:97-104` states the boundary: public content only; stops at login/paywall and reports `authentication required`; does not store/transmit credentials.

2. **Claude plugin packaging surface**
   - `.claude-plugin/plugin.json:2-11` declares plugin `name=insane-search`, `version=0.9.0`, MIT license, GitHub homepage/repository.
   - `.claude-plugin/plugin.json:4` describes a Phase 0→3 adaptive scheduler with `curl_cffi` TLS impersonation and auto dependency install.
   - `skills/insane-search/SKILL.md:20-26` defines the first-run setup hook behavior and optional star prompt flow.

3. **Agent skill trigger / command contract**
   - `skills/insane-search/SKILL.md:36-44` instructs the agent not to manually retry ordinary WebFetch/curl paths after a blocked/403/402 URL; it should invoke `python3 -m engine "<URL>"` and inspect exit code/trace.
   - `skills/insane-search/engine/__main__.py:27-48` implements the CLI parser with URL, selector, device, timeout, max-attempts, Playwright/Phase0 toggles, JSON, and trace flags.
   - `skills/insane-search/engine/__main__.py:51-62` routes the CLI call to `fetch(...)` with `enable_playwright` and `enable_phase0` flags.
   - `skills/insane-search/engine/__main__.py:112-127` emits either JSON metadata or agent-safe untrusted text and exits `0` when `result.ok` is true, otherwise `1`.

4. **Single Python API entrypoint and result envelope**
   - `skills/insane-search/engine/__init__.py:7-18` exports `fetch`, `FetchResult`, validators, transform helpers, detector, and content-safety helpers as the public engine surface.
   - `skills/insane-search/engine/fetch_chain.py:1-31` documents the public contract: `fetch(url, ...) -> FetchResult`, explicit probe/validate/detect/plan/execute/report phases, and no site-specific branching except runtime hints.
   - `skills/insane-search/engine/fetch_chain.py:84-149` defines `FetchResult` fields including `trace`, `grid_exhausted`, `stop_reason`, `untried_routes`, `must_invoke_playwright_mcp`, and prompt-injection metadata.

5. **Phase 0 public-platform exception is source-localized**
   - `skills/insane-search/engine/phase0.py:1-11` says Phase 0 is the sanctioned exception to the No-Site-Name rule and that platform names should not be added elsewhere in `engine/`.
   - `skills/insane-search/engine/phase0.py:58-69` recognizes Reddit, X/Twitter, and YouTube for deterministic public route handling.
   - `skills/insane-search/engine/phase0.py:72-105`, `108-160`, and `163-182` implement Reddit RSS/JSON, X/Twitter syndication/oEmbed/tweet-result, and YouTube `yt-dlp` attempts respectively.

6. **Validation and fallback mechanics**
   - `skills/insane-search/engine/validators.py:69-86` defines verdicts and terminal non-success statuses: auth-required, not-found, and rate-limited.
   - `skills/insane-search/engine/validators.py:192-220` begins the layered `validate(...)` implementation and differentiates HTTP status semantics before content checks.
   - `skills/insane-search/engine/executor.py:1-18` describes capability-matched Playwright fallback routing and explicitly states MCP Playwright must be driven by the Claude session itself.
   - `skills/insane-search/engine/executor.py:65-75` maps profile capabilities/device class to local real Chrome, mobile Chrome, or MCP fallback executor choices.

7. **Safety surfaces are present in source**
   - `skills/insane-search/engine/safety.py:1-12` frames SSRF/redirect protection for attacker-influenced URLs and default-denies internal targets unless `INSANE_ALLOW_PRIVATE=1`.
   - `skills/insane-search/engine/safety.py:37-71` blocks non-http(s), hosts resolving to internal/private/link-local/reserved/multicast/unspecified addresses, and IP literals in those ranges.
   - `skills/insane-search/engine/content_safety.py:11-13` defines untrusted web-content markers and the `untrusted_public_web` trust label.
   - `skills/insane-search/engine/content_safety.py:29-72` detects prompt-injection signals such as instruction override, system prompt access, credential access, tool execution, and data exfiltration.
   - `skills/insane-search/engine/content_safety.py:122-151` wraps fetched text with an explicit boundary and header instructing consumers to treat it as untrusted data.

8. **Test surface exists but is script-based, not CI-manifest-based**
   - No `.github/` directory was present in the checkout during capture.
   - `skills/insane-search/engine/tests/test_smoke.py:7-8` documents manual execution via `python3 engine/tests/test_smoke.py`.
   - `skills/insane-search/engine/tests/test_u8.py:1-9` documents deterministic prompt-injection boundary regression tests.

## Test / verification runs

Because the repo has no package manifest or CI workflow in this checkout, I used an artifact-scoped virtual environment:

- venv path: `artifacts/insane-search/static-analysis/test-venv/`
- install log: `artifacts/insane-search/static-analysis/pip-install-test-deps.log`
- installed test deps recorded in log: Python 3.14.5, PyYAML 6.0.3, beautifulsoup4 4.15.0, curl_cffi 0.15.0.

Observed results:

- `unit-tests-with-deps.log`: `test_u1.py` passed `12/12`; `test_u4.py` passed `7/7`; direct-script run then hit the known invocation mismatch for `test_u5.py` (`ModuleNotFoundError: No module named 'engine'`) because that file documents package-mode execution.
- `package-mode-and-smoke-tests-with-deps.log`: `python -m engine.tests.test_u5` passed `14/14`; `test_u7.py` passed `7/7`; `test_u8.py` passed `11/11`; `test_smoke.py` passed `8/8` including an online `example.com` fetch and `httpbin.org/status/403` trace-shape check.

Important setup context: before installing dependencies, several tests degraded/skipped/failed due missing local Python packages (`PyYAML`, `beautifulsoup4`, `curl_cffi`). I did not record those as project failures because the source has no declared dependency manifest and the CI-equivalent setup is absent.

## DeepWiki baseline topics captured, not yet source-verified in depth

DeepWiki produced 33 pages under `artifacts/insane-search/deepwiki/pages-md/`. Its TOC covers Overview, Getting Started, Supported Platforms, Legal, Architecture Overview, Phase 0→3 pipeline, Fetch Chain/Diversity Grid, Phase 0 routes, Response Validation/WAF Detection, Transport, TLS/URL transforms, Playwright, Self-Learning, Safety/SSRF, Bias Check, reference guides, WAF profiles, setup/plugin infrastructure, and tests.

Treat those pages as an external baseline only. The source-verified facts above checked the high-leverage surfaces but did not fully verify every DeepWiki claim about all WAF profile details, every platform reference, or every fallback path.

## Recommended next steps

1. Run a standard-depth source verification of DeepWiki section `2 Architecture Overview` against `fetch_chain.py`, `waf_detector.py`, `waf_profiles.yaml`, `transport.py`, `executor.py`, and `learning.py`.
2. Write `reports/insane-search/architecture.md` and `reports/insane-search/deepwiki-comparison.md`, separating DeepWiki labels from current-source corrections.
3. Add a dependency/test setup note because this checkout has tests but no explicit Python dependency manifest or CI workflow.
4. Optionally update `wiki/projects/insane-search.md` after the architecture claims are source-verified more deeply.
