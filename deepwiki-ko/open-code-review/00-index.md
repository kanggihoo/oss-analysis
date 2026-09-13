---
type: deepwiki-translation-index
repo: open-code-review
source_toc: artifacts/open-code-review/deepwiki/toc.json
---

# DeepWiki Translation: open-code-review

> 이 문서는 DeepWiki 산출물의 한국어 번역입니다. 코드 검증이 완료된 최종 분석 보고서가 아닙니다.

## TOC

- [[1-opencodereview-overview|1 OpenCodeReview Overview]]
  - [[1.1-getting-started|1.1 Getting Started]]
  - [[1.2-cli-command-reference|1.2 CLI Command Reference]]
- [[2-core-architecture|2 Core Architecture]]
  - [[2.1-review-agent|2.1 Review Agent]]
  - [[2.2-memory-compression-and-context-management|2.2 Memory Compression and Context Management]]
  - [[2.3-git-diff-processing|2.3 Git Diff Processing]]
- [[3-agent-tool-system|3 Agent Tool System]]
  - [[3.1-file-and-code-tools|3.1 File and Code Tools]]
  - [[3.2-comment-collection-and-code_comment-tool|3.2 Comment Collection and code_comment Tool]]
- [[4-llm-client-layer|4 LLM Client Layer]]
  - [[4.1-endpoint-resolution-and-protocol-selection|4.1 Endpoint Resolution and Protocol Selection]]
  - [[4.2-http-client-streaming-and-token-counting|4.2 HTTP Client, Streaming, and Token Counting]]
- [[5-configuration-system|5 Configuration System]]
  - [[5.1-system-review-rules|5.1 System Review Rules]]
  - [[5.2-prompt-templates-and-task-configuration|5.2 Prompt Templates and Task Configuration]]
  - [[5.3-tool-definitions-config-and-file-allowlist|5.3 Tool Definitions Config and File Allowlist]]
- [[6-session-persistence-and-webui-viewer|6 Session Persistence and WebUI Viewer]]
  - [[6.1-session-persistence-(jsonl-format)|6.1 Session Persistence (JSONL Format)]]
  - [[6.2-webui-session-viewer|6.2 WebUI Session Viewer]]
- [[7-telemetry-and-observability|7 Telemetry and Observability]]
  - [[7.1-opentelemetry-setup-and-exporters|7.1 OpenTelemetry Setup and Exporters]]
  - [[7.2-spans-metrics-and-content-logging|7.2 Spans, Metrics, and Content Logging]]
- [[8-project-website-(pages)|8 Project Website (pages/)]]
  - [[8.1-landing-page-components|8.1 Landing Page Components]]
  - [[8.2-internationalization-(i18n)|8.2 Internationalization (i18n)]]
- [[9-build-release-and-distribution|9 Build, Release, and Distribution]]
  - [[9.1-makefile-and-local-build|9.1 Makefile and Local Build]]
  - [[9.2-cicd-workflows-and-npm-publishing|9.2 CI/CD Workflows and npm Publishing]]
  - [[9.3-cicd-integration-examples|9.3 CI/CD Integration Examples]]
- [[10-glossary|10 Glossary]]
