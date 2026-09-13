---
type: deepwiki-translation-index
repo: insane-search
source_toc: artifacts/insane-search/deepwiki/toc.json
---

# DeepWiki Translation: insane-search

> 이 문서는 DeepWiki 산출물의 한국어 번역입니다. 코드 검증이 완료된 최종 분석 보고서가 아닙니다.

## TOC

- [[1-overview|1 Overview]]
  - [[1.1-getting-started-and-installation|1.1 Getting Started & Installation]]
  - [[1.2-supported-platforms-and-reference-index|1.2 Supported Platforms & Reference Index]]
  - [[1.3-legal-disclaimer-and-license|1.3 Legal, Disclaimer & License]]
- [[2-architecture-overview|2 Architecture Overview]]
  - [[2.1-phase-03-adaptive-escalation-pipeline|2.1 Phase 0→3 Adaptive Escalation Pipeline]]
  - [[2.2-the-fetch-chain-and-diversity-grid|2.2 The Fetch Chain & Diversity Grid]]
  - [[2.3-phase-0:-platform-specific-official-routes|2.3 Phase 0: Platform-Specific Official Routes]]
  - [[2.4-response-validation-and-waf-detection|2.4 Response Validation & WAF Detection]]
- [[3-core-engine-modules|3 Core Engine Modules]]
  - [[3.1-transport-layer-and-session-pool|3.1 Transport Layer & Session Pool]]
  - [[3.2-tls-impersonation-and-url-transforms|3.2 TLS Impersonation & URL Transforms]]
  - [[3.3-playwright-executor-and-browser-templates|3.3 Playwright Executor & Browser Templates]]
  - [[3.4-self-learning-store|3.4 Self-Learning Store]]
  - [[3.5-safety-and-ssrf-guard|3.5 Safety & SSRF Guard]]
  - [[3.6-bias-check-and-no-site-name-rule|3.6 Bias Check & No-Site-Name Rule]]
- [[4-reference-guides|4 Reference Guides]]
  - [[4.1-json-apis-and-rss-feeds|4.1 JSON APIs & RSS Feeds]]
  - [[4.2-public-apis-(bluesky-mastodon-stack-overflow-arxiv-github)|4.2 Public APIs (Bluesky, Mastodon, Stack Overflow, arXiv, GitHub)]]
  - [[4.3-media-extraction-(yt-dlp)|4.3 Media Extraction (yt-dlp)]]
  - [[4.4-jina-reader-integration|4.4 Jina Reader Integration]]
  - [[4.5-cache-and-archive-fallbacks|4.5 Cache & Archive Fallbacks]]
  - [[4.6-metadata-extraction-(ogp-and-json-ld)|4.6 Metadata Extraction (OGP & JSON-LD)]]
- [[5-waf-profiles-and-detection|5 WAF Profiles & Detection]]
  - [[5.1-waf-profile-schema-and-configuration|5.1 WAF Profile Schema & Configuration]]
  - [[5.2-waf-vendor-profiles:-akamai-cloudflare-datadome-perimeterx|5.2 WAF Vendor Profiles: Akamai, Cloudflare, DataDome, PerimeterX]]
- [[6-setup-and-plugin-infrastructure|6 Setup & Plugin Infrastructure]]
  - [[6.1-first-run-setup-script|6.1 First-Run Setup Script]]
  - [[6.2-update-notifier-hook|6.2 Update Notifier Hook]]
- [[7-testing|7 Testing]]
  - [[7.1-unit-tests|7.1 Unit Tests]]
  - [[7.2-coverage-battery-and-integration-tests|7.2 Coverage Battery & Integration Tests]]
- [[8-glossary|8 Glossary]]
