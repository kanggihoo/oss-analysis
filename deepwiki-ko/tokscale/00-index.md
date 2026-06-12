---
type: deepwiki-translation-index
repo: tokscale
source_toc: artifacts/tokscale/deepwiki/toc.json
---

# DeepWiki Translation: tokscale

> 이 문서는 DeepWiki 산출물의 한국어 번역입니다. 코드 검증이 완료된 최종 분석 보고서가 아닙니다.

## TOC

- [[1-overview|1 Overview]]
- [[2-architecture|2 Architecture]]
  - [[2.1-monorepo-structure|2.1 Monorepo Structure]]
  - [[2.2-data-flow-pipeline|2.2 Data Flow Pipeline]]
- [[3-cli-tool|3 CLI Tool]]
  - [[3.1-installation-and-basic-usage|3.1 Installation and Basic Usage]]
  - [[3.2-commands-reference|3.2 Commands Reference]]
    - [[3.2.1-data-visualization-commands|3.2.1 Data Visualization Commands]]
    - [[3.2.2-social-platform-commands|3.2.2 Social Platform Commands]]
    - [[3.2.3-cursor-ide-integration|3.2.3 Cursor IDE Integration]]
    - [[3.2.4-pricing-lookup|3.2.4 Pricing Lookup]]
  - [[3.3-terminal-ui-(tui)|3.3 Terminal UI (TUI)]]
    - [[3.3.1-tui-architecture-and-state-management|3.3.1 TUI Architecture and State Management]]
    - [[3.3.2-tui-views-and-navigation|3.3.2 TUI Views and Navigation]]
    - [[3.3.3-tui-components|3.3.3 TUI Components]]
  - [[3.4-native-rust-core|3.4 Native Rust Core]]
    - [[3.4.1-core-architecture-and-napi-integration|3.4.1 Core Architecture and NAPI Integration]]
    - [[3.4.2-session-parsing-and-data-sources|3.4.2 Session Parsing and Data Sources]]
    - [[3.4.3-pricing-system|3.4.3 Pricing System]]
    - [[3.4.4-report-generation-and-aggregation|3.4.4 Report Generation and Aggregation]]
- [[4-frontend-web-application|4 Frontend Web Application]]
  - [[4.1-application-structure|4.1 Application Structure]]
  - [[4.2-leaderboard-page|4.2 Leaderboard Page]]
  - [[4.3-user-profile-pages|4.3 User Profile Pages]]
  - [[4.4-navigation-and-layout|4.4 Navigation and Layout]]
  - [[4.5-3d-visualization-components|4.5 3D Visualization Components]]
  - [[4.6-embeddable-profile-cards-and-badges|4.6 Embeddable Profile Cards and Badges]]
- [[5-api-routes|5 API Routes]]
  - [[5.1-submit-endpoint|5.1 Submit Endpoint]]
  - [[5.2-leaderboard-api|5.2 Leaderboard API]]
  - [[5.3-user-profile-api|5.3 User Profile API]]
  - [[5.4-authentication-flow|5.4 Authentication Flow]]
  - [[5.5-settings-and-data-management-api|5.5 Settings and Data Management API]]
- [[6-database-schema|6 Database Schema]]
  - [[6.1-data-models-and-relationships|6.1 Data Models and Relationships]]
  - [[6.2-query-patterns-and-optimization|6.2 Query Patterns and Optimization]]
- [[7-development-and-build-system|7 Development and Build System]]
  - [[7.1-local-development-setup|7.1 Local Development Setup]]
  - [[7.2-build-pipeline-and-native-module-compilation|7.2 Build Pipeline and Native Module Compilation]]
  - [[7.3-cicd-and-publishing|7.3 CI/CD and Publishing]]
- [[8-configuration-and-customization|8 Configuration and Customization]]
  - [[8.1-cli-configuration|8.1 CLI Configuration]]
  - [[8.2-frontend-environment-variables|8.2 Frontend Environment Variables]]
- [[9-glossary|9 Glossary]]
