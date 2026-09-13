# Build, Release, and Distribution

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/workflows/release.yml](.github/workflows/release.yml)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)
- [Makefile](Makefile)
- [bin/ocr.js](bin/ocr.js)
- [internal/release/asset_naming_test.go](internal/release/asset_naming_test.go)
- [package.json](package.json)

</details>



The OpenCodeReview (OCR) project employs a multi-stage pipeline to compile, package, and distribute the CLI tool across various platforms and package managers. The process ranges from local development builds using a `Makefile` to automated global distribution via GitHub Actions, encompassing Go binary compilation, npm package publishing, and GitHub Pages deployment.

## Pipeline Overview

The distribution pipeline bridges the Go source code with end-user environments (macOS, Linux, Windows, npm).

### From Source to Distribution
The following diagram illustrates the flow from code changes to various distribution channels, mapping the build targets to their respective automation scripts.

**Build and Release Flow**
```mermaid
graph TD
    subgraph "Source Space"
        "GoSource"["./cmd/opencodereview"]
        "WebSource"["./pages/"]
        "NPMSource"["./package.json"]
    end

    subgraph "Local Build (Makefile)"
        "make_build"["make build"]
        "make_dist"["make dist"]
    end

    subgraph "CI/CD (GitHub Actions)"
        "release_yml"[".github/workflows/release.yml"]
        "deploy_pages_yml"[".github/workflows/deploy-pages.yml"]
    end

    subgraph "Distribution Space"
        "gh_release"["GitHub Releases (Binaries + sha256sum.txt)"]
        "npm_registry"["npm Registry (@alibaba-group/open-code-review)"]
        "gh_pages"["GitHub Pages (Website)"]
    end

    "GoSource" --> "make_build"
    "GoSource" --> "release_yml"
    "WebSource" --> "deploy_pages_yml"
    "NPMSource" --> "release_yml"
    
    "make_dist" --> "gh_release"
    "release_yml" --> "gh_release"
    "release_yml" --> "npm_registry"
    "deploy_pages_yml" --> "gh_pages"
```
**Sources:**
- [.github/workflows/release.yml:1-98]()
- [Makefile:1-81]()
- [package.json:1-10]()

---

## Makefile and Local Build

Local development and manual release preparation are handled by the `Makefile`. It defines the standard build environment, including static linking requirements (`CGO_ENABLED=0`) and metadata injection via Go's `-ldflags`.

Key capabilities include:
- **Metadata Injection**: Injecting `Version`, `GitCommit`, and `BuildDate` into the `main` package variables using `LD_FLAGS` [Makefile:17-20]().
- **Cross-Compilation**: A `BUILD_PLATFORM` macro facilitates building for `linux`, `darwin`, and `windows` across `amd64` and `arm64` architectures [Makefile:22-26]().
- **Artifact Verification**: The `sha256sum` target generates a `sha256sum.txt` for all binaries in the `./dist` directory [Makefile:75-76]().

For a deep dive into the build targets and flags, see [Makefile and Local Build](#9.1).

**Sources:**
- [Makefile:10-26]()
- [Makefile:54-72]()
- [Makefile:75-81]()

---

## CI/CD Workflows

The project uses GitHub Actions to automate the heavy lifting of multi-platform releases and documentation hosting.

### Release Workflow
Triggered by version tags (e.g., `v*`), the `release.yml` workflow executes a multi-stage process:
1.  **Build Matrix**: Compiles binaries for a matrix of 6 combinations (Linux, Darwin, Windows x AMD64, ARM64) [ .github/workflows/release.yml:13-27]().
2.  **Release**: Creates a GitHub Release using `softprops/action-gh-release`, uploading the binaries and a fresh `sha256sum.txt` [ .github/workflows/release.yml:69-75]().
3.  **npm Publish**: Injects the version from the git tag into `package.json` and publishes the package to the npm registry with provenance [ .github/workflows/release.yml:91-95]().

### Distribution Asset Naming
To ensure consistency between the `Makefile`, GitHub Actions, and the npm install script, naming conventions are validated via tests.

**Naming Consistency Map**
```mermaid
graph LR
    subgraph "Logic Entities"
        "PkgConfig"["package.json: ocrConfig"]
        "MakefileVar"["Makefile: BINARY_NAME"]
        "WorkflowVar"["release.yml: BIN_NAME"]
    end

    subgraph "Resulting Artifacts"
        "LinuxBin"["opencodereview-linux-amd64"]
        "WinBin"["opencodereview-windows-amd64.exe"]
    end

    "PkgConfig" -- "defines pattern" --> "LinuxBin"
    "MakefileVar" -- "renders" --> "LinuxBin"
    "WorkflowVar" -- "renders" --> "WinBin"
```
**Sources:**
- [internal/release/asset_naming_test.go:88-131]()
- [package.json:18-21]()
- [Makefile:6-8]()

For details on the automation logic and secret management, see [CI/CD Workflows and npm Publishing](#9.2).

---

## Distribution Channels and Installation

OCR is distributed through three primary channels:

| Channel | Artifact Type | Target Audience |
| :--- | :--- | :--- |
| **GitHub Releases** | Cross-platform Binaries | Manual installation, CI environments, and system package managers [ .github/workflows/release.yml:72-74](). |
| **npm Registry** | Node.js wrapper | Web developers using `npx` or `npm install`. Uses `bin/ocr.js` as a shim [package.json:2-7](). |
| **GitHub Pages** | Static Website | Documentation, benchmarks, and project landing page [pages/src/i18n/index.ts](). |

### The npm Wrapper
The npm package `@alibaba-group/open-code-review` acts as a distribution wrapper. It includes a `postinstall` script [package.json:9]() that downloads the correct platform-specific binary based on `ocrConfig.urlPattern` [package.json:19](). The `bin/ocr.js` shim then handles execution and automatic updates [bin/ocr.js:10-32]().

For CI/CD integration examples using these channels, see [CI/CD Integration Examples](#9.3).

**Sources:**
- [package.json:5-9]()
- [bin/ocr.js:1-10]()
- [.github/workflows/release.yml:77-98]()
