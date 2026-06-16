---
type: deepwiki-translation-index
repo: claude-code-history-viewer
source_toc: artifacts/claude-code-history-viewer/deepwiki/toc.json
---

# DeepWiki Translation: claude-code-history-viewer

> 이 문서는 DeepWiki 산출물의 한국어 번역입니다. 코드 검증이 완료된 최종 분석 보고서가 아닙니다.

## TOC

- [[deepwiki-ko/claude-code-history-viewer/1-overview|1 Overview]]
  - [[1.1-installation-and-setup|1.1 Installation and Setup]]
  - [[1.2-key-features|1.2 Key Features]]
- [[2-architecture-overview|2 Architecture Overview]]
  - [[2.1-system-architecture|2.1 System Architecture]]
  - [[2.2-frontend-architecture|2.2 Frontend Architecture]]
  - [[2.3-backend-architecture|2.3 Backend Architecture]]
  - [[2.4-data-flow|2.4 Data Flow]]
  - [[2.5-multi-provider-system|2.5 Multi-Provider System]]
- [[3-core-components|3 Core Components]]
  - [[3.1-project-tree|3.1 Project Tree]]
    - [[3.1.1-session-item|3.1.1 Session Item]]
  - [[3.2-session-board|3.2 Session Board]]
    - [[3.2.1-interaction-cards-and-lanes|3.2.1 Interaction Cards and Lanes]]
    - [[3.2.2-activity-timeline|3.2.2 Activity Timeline]]
  - [[3.3-message-viewer|3.3 Message Viewer]]
  - [[3.4-analytics-dashboard|3.4 Analytics Dashboard]]
    - [[3.4.1-analytics-views|3.4.1 Analytics Views]]
  - [[3.5-token-stats-viewer|3.5 Token Stats Viewer]]
  - [[3.6-settings-manager|3.6 Settings Manager]]
  - [[3.7-header-and-navigation|3.7 Header and Navigation]]
  - [[3.8-archive-manager|3.8 Archive Manager]]
  - [[3.9-recent-edits-viewer|3.9 Recent Edits Viewer]]
- [[4-state-management|4 State Management]]
  - [[4.1-store-architecture|4.1 Store Architecture]]
  - [[4.2-state-slices|4.2 State Slices]]
  - [[4.3-data-models|4.3 Data Models]]
- [[5-backend-systems|5 Backend Systems]]
  - [[5.1-project-and-session-commands|5.1 Project and Session Commands]]
  - [[5.2-statistics-and-analytics|5.2 Statistics and Analytics]]
  - [[5.3-settings-management|5.3 Settings Management]]
  - [[5.4-file-watcher|5.4 File Watcher]]
  - [[5.5-provider-implementations|5.5 Provider Implementations]]
  - [[5.6-webui-server-mode|5.6 WebUI Server Mode]]
  - [[5.7-wsl-support|5.7 WSL Support]]
- [[6-content-rendering|6 Content Rendering]]
  - [[6.1-content-renderers|6.1 Content Renderers]]
  - [[6.2-brushing-system|6.2 Brushing System]]
  - [[6.3-tool-icons-and-display|6.3 Tool Icons and Display]]
  - [[6.4-ansi-and-terminal-rendering|6.4 ANSI and Terminal Rendering]]
- [[7-internationalization|7 Internationalization]]
  - [[7.1-translation-system|7.1 Translation System]]
  - [[7.2-type-generation|7.2 Type Generation]]
- [[8-update-system|8 Update System]]
  - [[8.1-release-workflow|8.1 Release Workflow]]
  - [[8.2-auto-updater|8.2 Auto-Updater]]
- [[9-development-guide|9 Development Guide]]
  - [[9.1-build-system|9.1 Build System]]
  - [[9.2-testing|9.2 Testing]]
  - [[9.3-utility-functions|9.3 Utility Functions]]
- [[10-glossary|10 Glossary]]
