---
type: deepwiki-translation
repo: pi
source: artifacts/pi/deepwiki/pages-md/10-infrastructure-and-development.md
deepwiki_url: https://deepwiki.com/earendil-works/pi/10-infrastructure-and-development
section: "10"
order: 33
---

# 인프라와 개발

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하기 위한 컨텍스트로 사용되었습니다.

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



`pi` 프로젝트는 지속적 통합과 전달(CI/CD)을 관리하고, 커뮤니티 기여 정책을 적용하며, 크로스 플랫폼 바이너리를 배포하고, 견고한 테스트 환경을 유지하는 포괄적인 인프라를 사용한다. 이 페이지는 주요 하위 시스템과 그 상호작용에 대한 상위 수준 개요를 제공하며, 각 영역의 자세한 하위 페이지로 연결한다.

## CI/CD와 바이너리 배포

`pi`의 빌드와 릴리스 프로세스는 GitHub Actions와 전용 스크립트를 통해 자동화되어 독립 실행형 크로스 플랫폼 바이너리를 생성한다. 주요 구성 요소는 다음과 같다.

- **크로스 플랫폼 바이너리 빌드**: 시스템은 `darwin-arm64`, `darwin-x64`, `linux-x64`, `linux-arm64`, `windows-x64`, `windows-arm64`의 여섯 플랫폼을 대상으로 한다. 바이너리는 플랫폼별 entry point와 `image-resize-worker.ts` 같은 worker script를 임베드한 상태에서 `bun build --compile`로 컴파일된다 [scripts/build-binaries.sh:124-141](), [.github/workflows/build-binaries.yml:46-47]().
- **Native 의존성 관리**: 클립보드 접근 같은 기능에는 native binding이 필요하므로, 빌드 스크립트 `build-binaries.sh`는 크로스 컴파일 단계에서 플랫폼 제한을 우회하기 위해 `--force`를 사용하여 모든 플랫폼별 native dependency(예: `@mariozechner/clipboard-darwin-arm64`)를 명시적으로 설치한다 [scripts/build-binaries.sh:91-108]().
- **릴리스 자동화**: 릴리스 노트는 `release-notes.mjs`를 사용해 `CHANGELOG.md`에서 자동 추출되며, 이 스크립트는 GitHub releases를 위한 버전 파싱과 링크 정규화를 처리한다 [.github/workflows/build-binaries.yml:49-54](), [packages/coding-agent/src/utils/changelog.ts:108-168]().
- **패키징**: 바이너리는 이미지 처리를 위한 `photon_rs_bg.wasm` 파일, 대화형 모드 테마, `export-html` 하위 시스템을 포함한 필수 assets와 함께 번들된다 [scripts/build-binaries.sh:143-198]().

전체 기술 세부 사항은 하위 페이지 [CI/CD and Binary Distribution](#10.1)를 참고한다.

### 빌드 파이프라인 개요

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

**출처:** [scripts/build-binaries.sh:1-198](), [.github/workflows/build-binaries.yml:1-83](), [packages/coding-agent/src/utils/changelog.ts:69-98]()

---

## 기여 Gate와 커뮤니티 워크플로

높은 품질을 유지하고 커뮤니티 상호작용을 규모 있게 관리하기 위해, `pi`는 자동화된 기여 gate를 적용한다.

- **새 기여 자동 닫기**: 승인 파일에 등재되지 않은 기여자의 모든 새 issue와 PR은 `issue-gate.yml` 및 `pr-gate.yml` workflow에 의해 자동으로 닫힌다 [.github/workflows/issue-gate.yml:1-120](), [.github/workflows/pr-gate.yml:1-127]().
- **Flat-File 권한**: `.github/APPROVED_CONTRIBUTORS` 파일은 기여자 권한의 source of truth 역할을 하며, GitHub handle을 `issue` 또는 `pr` capability에 매핑한다 [.github/APPROVED_CONTRIBUTORS:1-240]().
- **Maintainer 명령**: Maintainer는 `lgtm`(PR 권한) 또는 `lgtmi`(issue 권한)를 댓글로 남겨 기여자를 승인한다. 이는 `approve-contributor.yml`을 트리거하며, 이 workflow는 권한 파일을 자동으로 업데이트하고 변경을 commit한다 [.github/workflows/approve-contributor.yml:33-42](), [.github/workflows/approve-contributor.yml:138-146]().
- **품질 기준**: `CONTRIBUTING.md`는 "The One Rule"을 명시한다. 즉, 기여자는 자신의 코드를 이해해야 한다. 이 문서는 issue의 품질 기준과 AI가 생성한 "slop"에 대한 정책을 정의한다 [CONTRIBUTING.md:5-12]().

구현 세부 사항은 [Contribution Gate and Community Workflow](#10.2)를 참고한다.

### 권한 승인 흐름

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

**출처:** [.github/APPROVED_CONTRIBUTORS:1-5](), [.github/workflows/approve-contributor.yml:27-42](), [CONTRIBUTING.md:13-27]()

---

## 테스트 인프라

테스트 인프라는 다양한 환경과 LLM provider 전반에서 안정성을 보장한다.

- **CI 검증**: `ci.yml` workflow는 모든 push와 PR에서 실행되며, Ubuntu runner에서 `npm run build`, `npm run check`(linting/types), `npm test`를 수행한다 [.github/workflows/ci.yml:35-43]().
- **시스템 의존성**: CI와 로컬 테스트 환경에는 canvas와 이미지 처리를 위한 특정 시스템 패키지가 필요하며, 여기에는 `libcairo2-dev`, `fd-find`, `ripgrep`이 포함된다 [.github/workflows/ci.yml:26-31]().
- **Pre-commit Hooks**: 로컬 개발은 `.husky/pre-commit`으로 보호되며, 보통 push 전에 코드 품질을 보장하기 위한 checks를 트리거한다.
- **Provider 검증**: `pi-ai`에 추가되는 새 LLM provider는 프로젝트 지침에 정의된 특정 테스트를 통과해야 한다 [CONTRIBUTING.md:63-64]().

포괄적인 테스트 프레임워크 세부 사항은 [Testing Infrastructure](#10.3)를 참고한다.

---

# 인프라 매핑: 코드에서 시스템으로

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

**출처:** [.github/workflows/ci.yml:35-43](), [.github/workflows/build-binaries.yml:1-47](), [.github/APPROVED_CONTRIBUTORS:1-10](), [scripts/build-binaries.sh:137-140]()

---

자세한 내용은 하위 페이지를 방문한다.
- [CI/CD and Binary Distribution](#10.1)
- [Contribution Gate and Community Workflow](#10.2)
- [Testing Infrastructure](#10.3)
