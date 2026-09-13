# Infrastructure and Development

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/APPROVED_CONTRIBUTORS](.github/APPROVED_CONTRIBUTORS)
- [.github/ISSUE_TEMPLATE/bug.yml](.github/ISSUE_TEMPLATE/bug.yml)
- [.github/ISSUE_TEMPLATE/config.yml](.github/ISSUE_TEMPLATE/config.yml)
- [.github/ISSUE_TEMPLATE/contribution.yml](.github/ISSUE_TEMPLATE/contribution.yml)
- [.github/workflows/approve-contributor.yml](.github/workflows/approve-contributor.yml)
- [.github/workflows/build-binaries.yml](.github/workflows/build-binaries.yml)
- [.github/workflows/ci.yml](.github/workflows/ci.yml)
- [.github/workflows/issue-gate.yml](.github/workflows/issue-gate.yml)
- [.github/workflows/npm-audit.yml](.github/workflows/npm-audit.yml)
- [.github/workflows/openclaw-gate.yml](.github/workflows/openclaw-gate.yml)
- [.github/workflows/pr-gate.yml](.github/workflows/pr-gate.yml)
- [.gitignore](.gitignore)
- [.husky/pre-commit](.husky/pre-commit)
- [.npmrc](.npmrc)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [LICENSE](LICENSE)
- [packages/coding-agent/src/utils/changelog.ts](packages/coding-agent/src/utils/changelog.ts)
- [packages/coding-agent/test/changelog.test.ts](packages/coding-agent/test/changelog.test.ts)
- [scripts/build-binaries.sh](scripts/build-binaries.sh)
- [scripts/release-notes.mjs](scripts/release-notes.mjs)

</details>



The `pi` project employs a comprehensive infrastructure that manages continuous integration and delivery (CI/CD), enforces community contribution policies, distributes cross-platform binaries, and maintains a robust testing environment. This page provides a high-level overview of the key subsystems and their interactions, linking to detailed child pages for each area.

## CI/CD and Binary Distribution

The build and release process for `pi` is automated through GitHub Actions and specialized scripts to produce standalone, cross-platform binaries. Key components include:

- **Cross-Platform Binary Builds**: The system targets six platforms — `darwin-arm64`, `darwin-x64`, `linux-x64`, `linux-arm64`, `windows-x64`, and `windows-arm64`. Binaries are compiled using `bun build --compile` with platform-specific entry points and worker scripts like `image-resize-worker.ts` embedded [scripts/build-binaries.sh:124-141](), [.github/workflows/build-binaries.yml:46-47]().
- **Native Dependency Management**: Because features such as clipboard access require native bindings, the build script `build-binaries.sh` explicitly installs all platform-specific native dependencies (e.g., `@mariozechner/clipboard-darwin-arm64`) using `--force` to bypass platform restrictions during the cross-compilation phase [scripts/build-binaries.sh:91-108]().
- **Release Automation**: Release notes are extracted automatically from `CHANGELOG.md` using `release-notes.mjs`, which handles version parsing and link normalization for GitHub releases [.github/workflows/build-binaries.yml:49-54](), [packages/coding-agent/src/utils/changelog.ts:108-168]().
- **Packaging**: Binaries are bundled with required assets, including the `photon_rs_bg.wasm` file for image processing, interactive mode themes, and the `export-html` subsystem [scripts/build-binaries.sh:143-198]().

For full technical details, see the child page [CI/CD and Binary Distribution](#10.1).

### Build Pipeline Overview

```mermaid
flowchart TD
    "SourceCode[Source Code]" --> "npm_ci[npm ci --ignore-scripts]"
    "npm_ci" --> "NativeDeps[Install cross-platform native bindings]"
    "NativeDeps" --> "BuildBinaries[scripts/build-binaries.sh]"
    "BuildBinaries" --> "BunCompile[bun build --compile]"
    "BunCompile" --> "Assets[Package themes, WASM, and export-html]"
    "Assets" --> "Archives[Create .tar.gz / .zip]"
    "Archives" --> "GHRelease[gh release create/upload]"
```

**Sources:** [scripts/build-binaries.sh:1-198](), [.github/workflows/build-binaries.yml:1-83](), [packages/coding-agent/src/utils/changelog.ts:69-98]()

---

## Contribution Gate and Community Workflow

To maintain high quality and manage community interactions at scale, `pi` enforces an automated contribution gate:

- **Auto-Closing of New Contributions**: All new issues and PRs from contributors not listed in the approval file are automatically closed by the `issue-gate.yml` and `pr-gate.yml` workflows [.github/workflows/issue-gate.yml:1-120](), [.github/workflows/pr-gate.yml:1-127]().
- **Flat-File Permissions**: The `.github/APPROVED_CONTRIBUTORS` file acts as the source of truth for contributor permissions, mapping GitHub handles to `issue` or `pr` capabilities [.github/APPROVED_CONTRIBUTORS:1-240]().
- **Maintainer Commands**: Maintainers approve contributors by commenting `lgtm` (for PR rights) or `lgtmi` (for issue rights). This triggers `approve-contributor.yml`, which automatically updates the permissions file and commits the change [.github/workflows/approve-contributor.yml:33-42](), [.github/workflows/approve-contributor.yml:138-146]().
- **Quality Standards**: `CONTRIBUTING.md` explicitly states "The One Rule": contributors must understand their code. It defines the quality bar for issues and the policy regarding AI-generated "slop" [CONTRIBUTING.md:5-12]().

For implementation details, see [Contribution Gate and Community Workflow](#10.2).

### Permission Approval Flow

```mermaid
graph TD
    "User[Contributor]" -->|Opens Issue/PR| "Gate[issue-gate.yml / pr-gate.yml]"
    "Gate" -->|Reads| "AuthFile[.github/APPROVED_CONTRIBUTORS]"
    "AuthFile" -->|Not Found| "Close[Auto-close with message]"
    "AuthFile" -->|Found| "Allow[Stay Open]"
    
    "Maintainer[Maintainer]" -->|Comments 'lgtm'| "ApproveWorkflow[approve-contributor.yml]"
    "ApproveWorkflow" -->|Updates| "AuthFile"
    "ApproveWorkflow" -->|Git Push| "Repo[GitHub Repository]"
```

**Sources:** [.github/APPROVED_CONTRIBUTORS:1-5](), [.github/workflows/approve-contributor.yml:27-42](), [CONTRIBUTING.md:13-27]()

---

## Testing Infrastructure

The testing infrastructure ensures stability across different environments and LLM providers:

- **CI Validation**: The `ci.yml` workflow runs on every push and PR, executing `npm run build`, `npm run check` (linting/types), and `npm test` on an Ubuntu runner [.github/workflows/ci.yml:35-43]().
- **System Dependencies**: CI and local test environments require specific system packages for canvas and image processing, including `libcairo2-dev`, `fd-find`, and `ripgrep` [.github/workflows/ci.yml:26-31]().
- **Pre-commit Hooks**: Local development is guarded by `.husky/pre-commit` which typically triggers checks to ensure code quality before pushing.
- **Provider Verification**: New LLM providers added to `pi-ai` are required to pass specific tests as defined in the project guidelines [CONTRIBUTING.md:63-64]().

For comprehensive test framework details, see [Testing Infrastructure](#10.3).

---

# Infrastructure Mapping: Code to System

```mermaid
flowchart TD
  subgraph "CI/CD & Distribution"
    "build-binaries.yml" --> "build-binaries.sh"
    "build-binaries.sh" --> "image-resize-worker.ts"
    "build-binaries.yml" --> "release-notes.mjs"
  end

  subgraph "Contribution Control"
    "issue-gate.yml" --> "APPROVED_CONTRIBUTORS"
    "pr-gate.yml" --> "APPROVED_CONTRIBUTORS"
    "approve-contributor.yml" --> "APPROVED_CONTRIBUTORS"
  end

  subgraph "Quality & Testing"
    "ci.yml" --> "npm_test[npm test]"
    "CONTRIBUTING.md" --> "npm_check[npm run check]"
  end

  "APPROVED_CONTRIBUTORS" --- "CONTRIBUTING.md"
  "build-binaries.sh" --- "package.json"
```

**Sources:** [.github/workflows/ci.yml:35-43](), [.github/workflows/build-binaries.yml:1-47](), [.github/APPROVED_CONTRIBUTORS:1-10](), [scripts/build-binaries.sh:137-140]()

---

For further details, visit the child pages:
- [CI/CD and Binary Distribution](#10.1)
- [Contribution Gate and Community Workflow](#10.2)
- [Testing Infrastructure](#10.3)
