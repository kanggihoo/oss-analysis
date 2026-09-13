---
type: deepwiki-translation
repo: knowledge-catalog
source: artifacts/knowledge-catalog/deepwiki/pages-md/1-overview.md
deepwiki_url: https://deepwiki.com/GoogleCloudPlatform/knowledge-catalog/1-overview
section: "1"
order: 1
---

# 개요

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하기 위한 컨텍스트로 사용되었습니다.

- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [LICENSE.md](LICENSE.md)
- [README.md](README.md)
- [samples/README.md](samples/README.md)
- [toolbox/README.md](toolbox/README.md)
- [toolbox/mdcode/src/libts/gcp/context.ts](toolbox/mdcode/src/libts/gcp/context.ts)
- [toolbox/mdcode/src/libts/tsconfig.json](toolbox/mdcode/src/libts/tsconfig.json)

</details>



[Knowledge Catalog](https://cloud.google.com/products/knowledge-catalog)(이전 명칭 Dataplex)는 AI 기반 데이터 카탈로그 및 메타데이터 관리 플랫폼입니다 [README.md:1-3](). 구조화 및 비구조화 데이터의 동적 지식 그래프를 제공하여 AI 에이전트에 비즈니스 컨텍스트를 제공합니다 [README.md:3-5]().

이 저장소에는 Knowledge Catalog 기능을 시연하고 컨텍스트 관리, 보강, 검색 솔루션 구축을 지원하도록 설계된 도구, 에이전트, 샘플이 포함되어 있습니다 [README.md:5-6]().

## 목적과 범위

이 저장소는 **Metadata as Code (MaC)** 및 **Agentic Enrichment** 워크플로를 구현하기 위한 기술적 기반 역할을 합니다. 이를 통해 엔지니어는 다음을 수행할 수 있습니다.
*   메타데이터를 버전 관리되는 소스 코드 아티팩트로 관리합니다 [toolbox/README.md:5-7]().
*   LLM을 사용해 데이터 자산에 대한 문서 생성과 유지 관리를 자동화합니다 [toolbox/README.md:9-12]().
*   로컬 메타데이터 작업 공간을 Google Cloud Knowledge Catalog 서비스와 동기화합니다 [toolbox/README.md:6-7]().

기본 정의와 데이터 모델 가이드는 [핵심 개념: Metadata as Code 및 Knowledge Catalog](#1.2)를 참조하세요.

## 시스템 아키텍처

이 저장소는 원시 데이터 자산(예: BigQuery 테이블)과 보강된 AI 준비 메타데이터 사이의 간극을 연결하는 여러 주요 구성 요소로 나뉩니다.

### 상위 수준 구성 요소 관계

다음 다이어그램은 핵심 도구가 Google Cloud 및 로컬 개발 환경과 어떻게 상호작용하는지 보여줍니다.

**시스템 구성 요소 맵**
```mermaid
graph TD
    subgraph "LocalWorkspace" ["Local Workspace (Code Entity Space)"]
        [kcmd_CLI] --> [CatalogSnapshot]
        [CatalogSnapshot] --> [Local_YAML_Files]
        [Local_YAML_Files] -.-> [Git_VCS]
    end

    subgraph "EnrichmentLayer" ["Enrichment Layer"]
        [Enrichment_Agents] -- "Updates" --> [Local_YAML_Files]
    end

    subgraph "GoogleCloud" ["Google Cloud (Service Space)"]
        [CatalogClient] -- "gRPC/REST" --> [Dataplex_API]
        [Dataplex_API] -- "Indexes" --> [BigQuery_Assets]
    end

    [kcmd_CLI] -- "Uses" --> [CatalogClient]
    [ApiContext] -- "Provides_Auth" --> [CatalogClient]
```
출처: [README.md:1-6](), [toolbox/README.md:1-13](), [toolbox/mdcode/src/libts/gcp/context.ts:10-47]()

### 데이터 및 메타데이터 흐름

아래 다이어그램은 `ApiContext`와 `CatalogClient`가 로컬 환경을 클라우드 서비스와 어떻게 연결하는지 보여줍니다.

**서비스 통합 다이어그램**
```mermaid
graph LR
    subgraph "Local_Runtime" ["Local Runtime"]
        [ApiContext_default] -- "execSync" --> [gcloud_CLI]
        [ApiContext_default] -- "populates" --> [ApiContext_instance]
    end

    subgraph "Metadata_Pipeline" ["Metadata Pipeline"]
        [kcmd] -- "calls" --> [CatalogClient]
        [ApiContext_instance] -- "auth_token" --> [CatalogClient]
        [CatalogClient] -- "HTTPS_Request" --> [Dataplex_Service]
    end
```
출처: [toolbox/mdcode/src/libts/gcp/context.ts:31-47](), [toolbox/README.md:5-7]()

## 주요 구성 요소

### 1. kcmd: Metadata as Code
`kcmd` 도구(`toolbox/mdcode`에 위치)는 메타데이터 관리를 위한 기본 인터페이스입니다. 이 도구는 카탈로그 항목(예: 테이블 설명 및 스키마)을 코드 아티팩트로 취급합니다.
*   **동기화:** GCP에서 로컬 YAML 파일로 메타데이터를 가져오고, 로컬 변경 사항을 다시 카탈로그로 푸시하는 기능을 지원합니다 [toolbox/README.md:5-7]().
*   **인증:** `ApiContext`를 사용하여 `gcloud` 명령을 감싸고, `cp.execSync`를 통해 프로젝트, 위치, 토큰 관리를 수행합니다 [toolbox/mdcode/src/libts/gcp/context.ts:10-47]().

### 2. 보강 에이전트
이 저장소는 메타데이터를 생성하고 발전시키기 위한 즉시 사용 가능한 에이전트를 제공합니다. 이러한 에이전트는 LLM을 사용해 데이터 자산을 분석하고 의미론적 설명을 생성합니다 [toolbox/README.md:9-12]().
*   **Python Agent:** `agents/enrichment`에 위치하며, 요약 및 관련성 라우팅을 위한 다단계 파이프라인을 지원합니다.
*   **TypeScript Agent:** `toolbox/enrichment`에 위치하며, 메타데이터 유지 관리를 위한 하네스를 제공합니다 [toolbox/README.md:9-12]().

### 3. Open Knowledge Format (OKF)
`okf/`에 위치한 지식 번들 구조화를 위한 벤더 중립 사양입니다. 서로 다른 AI 에이전트와 카탈로그 간 상호 운용성을 보장하기 위해 문서, 개념, 로그를 어떻게 구성해야 하는지 정의합니다.

### 4. 샘플 및 데모
도구의 실용적 구현 예시입니다.
*   **Discovery:** 카탈로그가 제공하는 Search API 위에 검색 및 탐색 에이전트를 구축합니다 [samples/README.md:6-9]().
*   **Enrichment Workflow:** 카탈로그에서 관리되는 자산에 대한 문서를 생성하고 보강하는 에이전트를 시연합니다 [samples/README.md:11-14]().

## 저장소 구조

코드베이스는 언어와 기능 영역별로 구성되어 있습니다. 디렉터리 레이아웃에 대한 자세한 설명과 환경 설정 방법은 [저장소 구조 및 시작하기](#1.1)를 참조하세요.

| Directory | Description |
| :--- | :--- |
| `agents/` | Python 기반 보강 에이전트와 LLM 파이프라인입니다. |
| `toolbox/` | `kcmd`(Metadata as Code)와 `kcagent`를 포함한 TypeScript 도구입니다 [toolbox/README.md:1-13](). |
| `okf/` | Open Knowledge Format 사양과 참조 에이전트입니다. |
| `samples/` | 검색, 탐색, 보강 워크플로의 데모입니다 [samples/README.md:1-15](). |

출처: [toolbox/README.md:1-13](), [samples/README.md:1-15](), [README.md:5-6]()

## 시작하기

저장소 작업을 시작하려면 다음을 수행합니다.
1.  **인증:** Google Cloud CLI가 구성되어 있는지 확인합니다. `ApiContext` 클래스는 `gcloud config get-value` 및 `gcloud auth application-default print-access-token`에 의존합니다 [toolbox/mdcode/src/libts/gcp/context.ts:6-42]().
2.  **환경:** 특정 도구 디렉터리의 설정 단계를 따릅니다(예: TypeScript의 경우 `toolbox/mdcode`, Python의 경우 `agents/enrichment`).
3.  **기여:** pull request를 제출하기 전에 [Contributing Guidelines](CONTRIBUTING.md)와 [Code of Conduct](CODE_OF_CONDUCT.md)를 검토합니다. 모든 제출물은 GitHub pull request를 통한 리뷰가 필요합니다 [CONTRIBUTING.md:27-32]().

자세한 설정 지침은 [저장소 구조 및 시작하기](#1.1)를 참조하세요.
