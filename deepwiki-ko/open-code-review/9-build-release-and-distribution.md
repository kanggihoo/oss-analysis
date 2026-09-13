---
type: deepwiki-translation
repo: open-code-review
source: artifacts/open-code-review/deepwiki/pages-md/9-build-release-and-distribution.md
deepwiki_url: https://deepwiki.com/alibaba/open-code-review/9-build-release-and-distribution
section: "9"
order: 27
---

# Build, Release, Distribution

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하기 위한 컨텍스트로 사용되었습니다.

- [.github/workflows/release.yml](.github/workflows/release.yml)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)
- [Makefile](Makefile)
- [bin/ocr.js](bin/ocr.js)
- [internal/release/asset_naming_test.go](internal/release/asset_naming_test.go)
- [package.json](package.json)

</details>



OpenCodeReview (OCR) project는 다양한 platforms와 package managers 전반에 CLI tool을 compile, package, distribute하기 위해 multi-stage pipeline을 사용합니다. 이 process는 `Makefile`을 사용한 local development builds부터 GitHub Actions를 통한 automated global distribution까지 이어지며, Go binary compilation, npm package publishing, GitHub Pages deployment를 포함합니다.

## Pipeline Overview

distribution pipeline은 Go source code와 end-user environments(macOS, Linux, Windows, npm)를 연결합니다.

### Source에서 Distribution까지
다음 다이어그램은 code changes에서 다양한 distribution channels까지의 flow를 보여주며, build targets를 각각의 automation scripts에 매핑합니다.

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
**출처:**
- [.github/workflows/release.yml:1-98]()
- [Makefile:1-81]()
- [package.json:1-10]()

---

## Makefile 및 Local Build

local development와 manual release preparation은 `Makefile`이 처리합니다. 이는 static linking requirements(`CGO_ENABLED=0`)와 Go의 `-ldflags`를 통한 metadata injection을 포함하는 표준 build environment를 정의합니다.

주요 기능은 다음과 같습니다.
- **Metadata Injection**: `LD_FLAGS`를 사용해 `Version`, `GitCommit`, `BuildDate`를 `main` package variables에 주입합니다 [Makefile:17-20]().
- **Cross-Compilation**: `BUILD_PLATFORM` macro는 `amd64` 및 `arm64` architectures 전반에서 `linux`, `darwin`, `windows`용 build를 지원합니다 [Makefile:22-26]().
- **Artifact Verification**: `sha256sum` target은 `./dist` directory의 모든 binaries에 대한 `sha256sum.txt`를 생성합니다 [Makefile:75-76]().

build targets와 flags에 대한 자세한 내용은 [Makefile and Local Build](#9.1)를 참조하세요.

**출처:**
- [Makefile:10-26]()
- [Makefile:54-72]()
- [Makefile:75-81]()

---

## CI/CD Workflows

프로젝트는 GitHub Actions를 사용해 multi-platform releases와 documentation hosting의 무거운 작업을 자동화합니다.

### Release Workflow
version tags(예: `v*`)로 trigger되는 `release.yml` workflow는 multi-stage process를 실행합니다.
1.  **Build Matrix**: 6개 조합(Linux, Darwin, Windows x AMD64, ARM64)의 matrix로 binaries를 compile합니다 [ .github/workflows/release.yml:13-27]().
2.  **Release**: `softprops/action-gh-release`를 사용해 GitHub Release를 생성하고 binaries와 새 `sha256sum.txt`를 upload합니다 [ .github/workflows/release.yml:69-75]().
3.  **npm Publish**: git tag의 version을 `package.json`에 주입하고 provenance와 함께 package를 npm registry에 publish합니다 [ .github/workflows/release.yml:91-95]().

### Distribution Asset Naming
`Makefile`, GitHub Actions, npm install script 사이의 consistency를 보장하기 위해 naming conventions는 tests로 검증됩니다.

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
**출처:**
- [internal/release/asset_naming_test.go:88-131]()
- [package.json:18-21]()
- [Makefile:6-8]()

automation logic와 secret management에 대한 자세한 내용은 [CI/CD Workflows and npm Publishing](#9.2)을 참조하세요.

---

## Distribution Channels 및 Installation

OCR은 세 가지 primary channel을 통해 배포됩니다.

| Channel | Artifact Type | Target Audience |
| :--- | :--- | :--- |
| **GitHub Releases** | Cross-platform Binaries | Manual installation, CI environments, system package managers [ .github/workflows/release.yml:72-74](). |
| **npm Registry** | Node.js wrapper | `npx` 또는 `npm install`을 사용하는 web developers입니다. `bin/ocr.js`를 shim으로 사용합니다 [package.json:2-7](). |
| **GitHub Pages** | Static Website | Documentation, benchmarks, project landing page [pages/src/i18n/index.ts](). |

### npm Wrapper
npm package `@alibaba-group/open-code-review`는 distribution wrapper 역할을 합니다. `ocrConfig.urlPattern`을 기준으로 올바른 platform-specific binary를 다운로드하는 `postinstall` script [package.json:9]()를 포함합니다 [package.json:19](). 이후 `bin/ocr.js` shim이 execution과 automatic updates를 처리합니다 [bin/ocr.js:10-32]().

이 channels를 사용한 CI/CD integration examples는 [CI/CD Integration Examples](#9.3)를 참조하세요.

**출처:**
- [package.json:5-9]()
- [bin/ocr.js:1-10]()
- [.github/workflows/release.yml:77-98]()
