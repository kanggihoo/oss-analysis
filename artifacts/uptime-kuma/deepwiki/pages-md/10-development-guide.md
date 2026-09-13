# Development Guide

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/ISSUE_TEMPLATE/ask_for_help.yml](.github/ISSUE_TEMPLATE/ask_for_help.yml)
- [.github/ISSUE_TEMPLATE/bug_report.yml](.github/ISSUE_TEMPLATE/bug_report.yml)
- [.github/ISSUE_TEMPLATE/config.yml](.github/ISSUE_TEMPLATE/config.yml)
- [.github/ISSUE_TEMPLATE/feature_request.yml](.github/ISSUE_TEMPLATE/feature_request.yml)
- [.github/ISSUE_TEMPLATE/security_issue.yml](.github/ISSUE_TEMPLATE/security_issue.yml)
- [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)
- [.github/dependabot.yml](.github/dependabot.yml)
- [.github/workflows/auto-test.yml](.github/workflows/auto-test.yml)
- [.github/workflows/close-incorrect-issue.yml](.github/workflows/close-incorrect-issue.yml)
- [.github/workflows/codeql-analysis.yml](.github/workflows/codeql-analysis.yml)
- [.github/workflows/prevent-file-change.yml](.github/workflows/prevent-file-change.yml)
- [.github/workflows/stale-bot.yml](.github/workflows/stale-bot.yml)
- [.github/workflows/validate.yml](.github/workflows/validate.yml)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [README.md](README.md)
- [SECURITY.md](SECURITY.md)
- [extra/check-knex-filenames.mjs](extra/check-knex-filenames.mjs)
- [extra/check-package-json.mjs](extra/check-package-json.mjs)
- [extra/close-incorrect-issue.js](extra/close-incorrect-issue.js)

</details>



This guide provides comprehensive onboarding for developers contributing to Uptime Kuma. It covers environment setup, codebase architecture, development workflow, and practical guidance for adding features. For detailed contribution rules and PR guidelines, see [Contributing Guidelines](#10.1). For Docker build specifics, see [Docker Build System](#10.2). For testing and code quality, see [Code Quality and Testing](#10.3).

## Quick Start for New Contributors

**Getting Started in 5 Minutes:**

```bash
# 1. Clone and setup
git clone https://github.com/louislam/uptime-kuma.git
cd uptime-kuma
npm run setup

# 2. Start development servers
# Option 1: Try it directly
node server/server.js

# Option 2: Run in the background using PM2 (Recommended)
npm install pm2 -g && pm2 install pm2-logrotate
pm2 start server/server.js --name uptime-kuma
```

**First Steps:**
1. Create a fork of the repository on GitHub.
2. Create a feature branch: `git checkout -b feature/your-feature-name`.
3. Make changes with ESLint support in your IDE.
4. Test your changes thoroughly.
5. Create a pull request following the [Contributing Guidelines](#10.1) guidelines.

Sources: [README.md:81-95](), [CONTRIBUTING.md:174-180]()

## Development Environment Setup

### Prerequisites

**System Requirements:**

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Node.js | >= 20.4 | Runtime environment [README.md:77-77]() |
| npm | Latest | Package management |
| Git | Latest | Version control [README.md:78-78]() |
| pm2 | Latest | Process management for background execution [README.md:79-79]() |

**Recommended Tools:**
- **IDE**: VS Code or similar with ESLint plugins.
- **SQLite GUI**: For inspecting the local database in `data/`.
- **Docker**: For testing containerized builds [README.md:40-58]().

Sources: [README.md:68-80](), [CONTRIBUTING.md:11-13]()

### Development Architecture

**Dual-Server Development Setup**

```mermaid
graph TB
    subgraph "Developer Workflow"
        [Developer] -- "Edit Code" --> [SourceFiles]
        [Browser] -- "localhost:3000" --> [ViteDevServer]
    end
    
    subgraph "Frontend Layer (Vue 3)"
        [ViteDevServer] -- "HMR" --> [Browser]
        [ViteDevServer] -- "Proxy API/Socket" --> [ExpressServer]
    end
    
    subgraph "Backend Layer (Node.js)"
        [ExpressServer] -- "socket.io" --> [SocketHandlers]
        [ExpressServer] -- "RedBeanPHP" --> [SQLite_kuma_db]
        [ExpressServer] -- "Execute" --> [MonitorLogic]
    end
    
    subgraph "Entity Mapping"
        [SourceFiles] -. "src/" .-> [ViteDevServer]
        [SourceFiles] -. "server/server.js" .-> [ExpressServer]
        [SourceFiles] -. "server/socket-handlers/" .-> [SocketHandlers]
    end
```

**How It Works:**
1. **Frontend**: The project is built with `vite` and `vue3` [CONTRIBUTING.md:11-11](). In development, Vite runs on one port (usually 3000) with Hot Module Replacement (HMR).
2. **Backend**: The `express.js` server runs on another port (usually 3001) [CONTRIBUTING.md:16-17]().
3. **Communication**: Most communication between frontend and backend occurs via WebSockets [CONTRIBUTING.md:12-12]().
4. **Production**: For production, the frontend is built into the `dist` directory, which the server then exposes as the root [CONTRIBUTING.md:15-16]().

Sources: [CONTRIBUTING.md:11-18]()

## Understanding the Codebase

### Project Structure Overview

**High-Level Directory Layout**

```mermaid
graph TD
    ["/"] --> [server]
    ["/"] --> [src]
    ["/"] --> [db]
    ["/"] --> [docker]
    ["/"] --> [test]
    ["/"] --> [extra]

    subgraph "Backend Logic"
        [server] --> [notification-providers]
        [server] --> [model]
    end

    subgraph "Frontend App"
        [src] --> [components]
        [src] --> [lang]
        [src] --> [pages]
    end

    subgraph "Data & Persistence"
        [db] -- "Knex Migrations" --> [Migrations]
        ["data"] -- "App Data" --> [SQLite]
    end
```

**Key Directories:**

| Directory | Purpose |
|-----------|---------|
| `server/` | Backend source code, including Express logic and monitor execution [CONTRIBUTING.md:28-28](). |
| `src/` | Frontend source code (Vue 3 components and pages) [CONTRIBUTING.md:29-29](). |
| `db/` | Base database templates and migration scripts [CONTRIBUTING.md:23-23](). |
| `server/notification-providers/` | Individual implementations for 90+ notification services [CONTRIBUTING.md:98-99](). |
| `src/lang/` | Internationalization files (i18n) [CONTRIBUTING.md:80-82](). |

Sources: [CONTRIBUTING.md:19-31](), [CONTRIBUTING.md:94-100]()

## Git Workflow and Branching

### Branch Strategy
- **`master`**: The main development branch for upcoming releases [.github/workflows/auto-test.yml:9-9]().
- **`1.23.X`**: Maintenance branch for the v1.x series [.github/workflows/auto-test.yml:9-9]().
- **`3.0.0`**: Active development for the next major version [.github/workflows/auto-test.yml:9-9]().

### Pull Request Process
1. **Scope**: Keep PRs small and focused on a single fix or feature [CONTRIBUTING.md:67-68]().
2. **No AI Slop**: Do not submit code generated by AI without thorough review and understanding. Failure to follow this results in an immediate ban [.github/PULL_REQUEST_TEMPLATE.md:2-7]().
3. **Checklist**: Ensure all UI changes adhere to the project's visual style and documentation is updated [.github/PULL_REQUEST_TEMPLATE.md:21-34]().
4. **Translations**: Add new strings to `src/lang/en.json` only. Do not manually edit other language files to avoid merge conflicts with Weblate [CONTRIBUTING.md:80-82]().

Sources: [CONTRIBUTING.md:62-92](), [.github/PULL_REQUEST_TEMPLATE.md:1-54]()

## Code Quality and Tools

### Linting and Validation
- **Linting**: Run `npm run lint:prod` to check for style violations [.github/workflows/auto-test.yml:120-120]().
- **JSON/YAML**: Automated validation of configuration files is performed via GitHub Actions [.github/workflows/validate.yml:14-29]().
- **Migrations**: Filenames for Knex migrations are validated by `extra/check-knex-filenames.mjs` [.github/workflows/validate.yml:46-47]().

### CI/CD Pipeline
The project uses GitHub Actions for automated testing:
- **Auto Test**: Runs on Ubuntu, macOS, Windows, and ARM across Node 20 and 24 [.github/workflows/auto-test.yml:14-24]().
- **E2E Test**: Executes Playwright end-to-end tests [.github/workflows/auto-test.yml:122-154]().
- **Security**: CodeQL analysis scans for vulnerabilities in JavaScript/TypeScript and Go code [.github/workflows/codeql-analysis.yml:24-27]().

Sources: [.github/workflows/auto-test.yml:1-155](), [.github/workflows/validate.yml:1-51](), [.github/workflows/codeql-analysis.yml:1-45]()
