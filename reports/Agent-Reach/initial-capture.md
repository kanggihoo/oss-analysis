# Agent Reach initial capture

- Repository: `https://github.com/Panniantong/Agent-Reach`
- Local checkout: `repos/Agent-Reach/`
- Artifact root: `artifacts/Agent-Reach/`
- Capture date: 2026-06-26
- Checkout HEAD: `a7c56eb474f915308f02c39b9fa0c20f1abff222` (`v1.5.0-11-ga7c56eb`), branch `main`, status clean

## Completed capture work

1. DeepWiki external baseline captured first, before local analysis.
   - Extract command: `python3 .../deepwiki_extract.py https://deepwiki.com/Panniantong/Agent-Reach --out artifacts/Agent-Reach/deepwiki --request-delay 1.0`
   - Output summary: `[toc] 30`, `[match] 30/30`, `Done: 30/30 missing=0`
   - Key files:
     - `artifacts/Agent-Reach/deepwiki/raw/index.html`
     - `artifacts/Agent-Reach/deepwiki/toc.json`
     - `artifacts/Agent-Reach/deepwiki/toc.md`
     - `artifacts/Agent-Reach/deepwiki/manifest.json`
     - `artifacts/Agent-Reach/deepwiki/pages-md/`
     - `artifacts/Agent-Reach/deepwiki/pages-meta/`
     - `artifacts/Agent-Reach/deepwiki/completeness-check.json`
2. Repository cloned under `repos/Agent-Reach/` from `https://github.com/Panniantong/Agent-Reach.git`.
3. Metadata/static artifacts written:
   - `artifacts/Agent-Reach/repo-metadata.txt`
   - `artifacts/Agent-Reach/github-metadata.json`
   - `artifacts/Agent-Reach/static-analysis/tracked-files.txt`
   - `artifacts/Agent-Reach/static-analysis/tracked-file-count.txt`
   - `artifacts/Agent-Reach/static-analysis/top-level-file-counts.txt`
   - `artifacts/Agent-Reach/static-analysis/source-tree-counts.txt`
   - `artifacts/Agent-Reach/static-analysis/tokei.txt`
   - `artifacts/Agent-Reach/static-analysis/tokei.json`
4. CI-equivalent pytest setup and test run completed in `artifacts/Agent-Reach/static-analysis/test-venv/`.
   - Install log: `artifacts/Agent-Reach/static-analysis/pip-install-dev.log`
   - Test log: `artifacts/Agent-Reach/static-analysis/pytest-q.log`

## Artifact verification snapshot

- DeepWiki completeness: `toc_count=30`, `pages_md_count=30`, `pages_meta_count=30`, `missing_pages_count=0`, filesystem missing counts both `0` (`artifacts/Agent-Reach/deepwiki/completeness-check.json`).
- Git tracked surface: `89` tracked files (`artifacts/Agent-Reach/static-analysis/tracked-file-count.txt`).
- Top-level tracked file concentration:
  - `agent_reach/`: 44 files
  - `docs/`: 15 files
  - `tests/`: 15 files
- Tokei summary: 81 files, 11,702 total lines; dominant implementation language is Python with 45 files / 6,058 code lines (`artifacts/Agent-Reach/static-analysis/tokei.txt`).
- Test result: `162 passed in 12.69s` (`artifacts/Agent-Reach/static-analysis/pytest-q.log`). During package installation pip printed dependency-conflict warnings involving the surrounding Hermes environment, but the artifact-scoped venv test command completed successfully.

## Source-verified initial facts

1. **Project positioning** — README presents Agent Reach as a way to give AI agents internet read/search capability and lists concrete platform examples such as YouTube subtitles, Twitter/X search, Reddit, XiaoHongShu, Bilibili, web pages, GitHub, RSS, and Exa search (`repos/Agent-Reach/README.md:24-48`, `README.md:70-87`).
2. **Capability layer, not a full wrapper** — README states Agent Reach is a higher-level capability layer for selecting/installing/checking/routing tools, while actual reading is performed by upstream tools directly (`repos/Agent-Reach/README.md:164-174`). The Python package docstring says the same: after installation, agents call upstream tools directly (`repos/Agent-Reach/agent_reach/core.py:3-15`).
3. **Packaging and entrypoint** — `pyproject.toml` defines package name `agent-reach`, version `1.5.0`, Python `>=3.10`, MIT license, core dependencies (`requests`, `feedparser`, `python-dotenv`, `loguru`, `pyyaml`, `rich`, `yt-dlp`), and CLI entrypoint `agent-reach = agent_reach.cli:main` (`repos/Agent-Reach/pyproject.toml:1-38`, `pyproject.toml:52-65`). `agent_reach/__init__.py` also reports `__version__ = "1.5.0"` (`repos/Agent-Reach/agent_reach/__init__.py:1-9`).
4. **CLI surface** — `agent_reach/cli.py` defines subcommands for `setup`, `install`, `configure`, `doctor`, `uninstall`, `skill`, `format`, `transcribe`, `check-update`, `watch`, and `version` (`repos/Agent-Reach/agent_reach/cli.py:50-165`).
5. **Channel registry** — current source registers 13 channels: GitHub, Twitter, YouTube, Reddit, Bilibili, XiaoHongShu, LinkedIn, Xiaoyuzhou, V2EX, Xueqiu, RSS, Exa Search, and Web (`repos/Agent-Reach/agent_reach/channels/__init__.py:9-39`).
6. **Backend ordering semantics** — `Channel` base class documents ordered backend candidates and user overrides via `<channel>_backend`; health checks should set `active_backend` only after lightweight executable probing, not just `shutil.which()` (`repos/Agent-Reach/agent_reach/channels/base.py:12-23`, `base.py:45-70`).
7. **Doctor behavior** — doctor iterates over all registered channels, isolates per-channel exceptions into `status="error"`, and records `status`, `tier`, `backends`, and `active_backend` in its result (`repos/Agent-Reach/agent_reach/doctor.py:12-35`).
8. **CI/test expectations** — GitHub Actions runs pytest on Python 3.10, 3.11, 3.12, and 3.13 after `pip install -c constraints.txt -e .[dev]`, plus a wheel-gate that builds a wheel and smoke-installs it (`repos/Agent-Reach/.github/workflows/pytest.yml:7-30`, `pytest.yml:35-70`). The local run reproduced the pytest part and passed.

## DeepWiki baseline topics captured, not yet source-verified

DeepWiki extracted 30 pages covering overview/architecture, CLI reference, per-channel pages, configuration, AI agent integration, and development/testing (`artifacts/Agent-Reach/deepwiki/toc.md`). These pages are stored as external baseline material only. They should not be treated as final facts until checked against `repos/Agent-Reach/`.

High-value follow-up checks from the DeepWiki TOC:

- Compare DeepWiki's channel architecture against `agent_reach/channels/*` and tests.
- Verify CLI command examples against `python -m agent_reach.cli --help` and subcommand help output.
- Check configuration/security claims against `agent_reach/config.py`, `agent_reach/cookie_extract.py`, and docs.
- Inspect MCP/agent integration claims against `agent_reach/integrations/mcp_server.py`, `config/mcporter.json`, and `agent_reach/skill/`.

## Recommended next steps

1. Write a source-verified `reports/Agent-Reach/architecture.md` focused on channel registry, backend routing, installer, doctor, and skill/MCP integration.
2. Produce `reports/Agent-Reach/deepwiki-comparison.md` by checking each DeepWiki architecture/CLI/channel claim against current source.
3. Run graphify after adding/validating a `.graphifyignore` scope for generated/local state, then store output under `artifacts/Agent-Reach/graphify/`.
4. If this project becomes a durable comparison target, update `wiki/projects/Agent-Reach.md` only after DeepWiki claims have been source-verified.
