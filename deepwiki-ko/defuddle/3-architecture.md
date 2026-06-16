---
type: deepwiki-translation
repo: defuddle
source: artifacts/defuddle/deepwiki/pages-md/3-architecture.md
deepwiki_url: https://deepwiki.com/kepano/defuddle/3-architecture
section: "3"
order: 3
---

# 아키텍처

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하는 맥락으로 사용되었습니다.

- [package-lock.json](package-lock.json)
- [package.json](package.json)
- [src/constants.ts](src/constants.ts)
- [src/defuddle.ts](src/defuddle.ts)
- [tsconfig.node.json](tsconfig.node.json)
- [webpack.config.js](webpack.config.js)

</details>



이 문서는 Defuddle의 상위 수준 아키텍처를 개요로 설명하며, 핵심 컴포넌트, 데이터 흐름, 시스템 구성을 포함합니다. 코드베이스의 여러 부분이 웹 페이지에서 콘텐츠를 추출하고 처리하기 위해 어떻게 함께 동작하는지 설명합니다.

라이브러리 사용 방법은 [Overview](#1)를 참조하세요. 콘텐츠가 추출되는 방식에 대한 자세한 내용은 [Content Extraction](#3)을 참조하세요.

## 시스템 개요

Defuddle은 HTML 문서를 처리해 주요 콘텐츠를 식별하고 추출하면서 잡음 요소, 광고, 내비게이션 요소를 제거하는 콘텐츠 추출 라이브러리입니다. 이 시스템은 알려진 웹사이트를 위한 특화 추출기와 일반 웹 콘텐츠를 위한 범용 추출 파이프라인을 갖춘 모듈식 아키텍처를 따릅니다.

### 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Input Sources"
        HTML["HTML Documents"]
        URL["Web URLs"]
        DOM["DOM Objects"]
    end
    
    subgraph "Defuddle Core System"
        MAIN["Defuddle Class<br/>Main Orchestrator"]
        META["MetadataExtractor<br/>Title, Author, etc."]
        REGISTRY["ExtractorRegistry<br/>Site-specific Handlers"]
        SCORER["ContentScorer<br/>Content vs Clutter"]
        STANDARD["standardizeContent<br/>HTML Normalization"]
    end
    
    subgraph "Specialized Extractors"
        TWITTER["TwitterExtractor"]
        YOUTUBE["YoutubeExtractor"] 
        GITHUB["GitHubExtractor"]
        CHATGPT["ChatGPTExtractor"]
        GROK["GrokExtractor"]
        GEMINI["GeminiExtractor"]
    end
    
    subgraph "Element Processing"
        IMAGES["Image Rules<br/>Picture/Figure Processing"]
        CODE["Code Block Rules<br/>Syntax Highlighting"]
        MATH["Math Rules<br/>LaTeX/MathML"]
        HEADINGS["Heading Rules<br/>Navigation Cleanup"]
    end
    
    subgraph "Output Processing"
        MARKDOWN["Markdown Converter<br/>HTML to Markdown"]
        CLEAN["Clean HTML Output"]
    end
    
    subgraph "Configuration & Constants"
        SELECTORS["Element Selectors<br/>Removal Patterns"]
        OPTIONS["DefuddleOptions<br/>Processing Configuration"]
    end
    
    HTML --> MAIN
    URL --> MAIN
    DOM --> MAIN
    
    MAIN --> META
    MAIN --> REGISTRY
    MAIN --> SCORER
    MAIN --> STANDARD
    
    REGISTRY --> TWITTER
    REGISTRY --> YOUTUBE
    REGISTRY --> GITHUB
    REGISTRY --> CHATGPT
    REGISTRY --> GROK
    REGISTRY --> GEMINI
    
    STANDARD --> IMAGES
    STANDARD --> CODE
    STANDARD --> MATH
    STANDARD --> HEADINGS
    
    MAIN --> MARKDOWN
    MAIN --> CLEAN
    
    SELECTORS --> SCORER
    SELECTORS --> STANDARD
    OPTIONS --> MAIN
```

출처: [src/defuddle.ts:1-14](), [src/defuddle.ts:21-35](), [src/defuddle.ts:40-59]()

### 콘텐츠 처리 파이프라인

```mermaid
flowchart TD
    A["Raw HTML Input"] --> B["Defuddle.parse"]
    B --> C{"Site-specific Extractor?"}
    
    C -->|Yes| D["ExtractorRegistry.findExtractor"]
    D --> E["Specialized Processing<br/>Twitter/YouTube/GitHub/etc."]
    E --> F["Return ExtractorResult"]
    
    C -->|No| G["Generic Pipeline"]
    G --> H["Schema.org Data Extraction"]
    G --> I["Meta Tags Collection"]
    G --> J["Mobile Style Evaluation"]
    G --> K["Small Image Detection"]
    
    H --> L["Document Cloning"]
    I --> L
    J --> L
    K --> L
    
    L --> M["Main Content Finding<br/>ENTRY_POINT_ELEMENTS"]
    M --> N["Small Image Removal"]
    N --> O["Hidden Element Removal"]
    O --> P["Content Scoring & Removal<br/>ContentScorer.scoreAndRemove"]
    P --> Q["Exact Selector Removal<br/>Ads, Navigation, etc."]
    Q --> R["Partial Selector Removal<br/>Pattern-based Clutter"]
    R --> S["Content Standardization"]
    
    S --> T["Element Rules Processing"]
    T --> U["Image Standardization"]
    T --> V["Code Block Standardization"]
    T --> W["Math Expression Processing"]
    T --> X["Heading Cleanup"]
    
    F --> Y["Metadata Extraction"]
    U --> Y
    V --> Y
    W --> Y
    X --> Y
    
    Y --> Z{"Output Format?"}
    Z -->|HTML| AA["Clean HTML Output"]
    Z -->|Markdown| BB["Markdown Conversion<br/>createMarkdownContent"]
    Z -->|Both| CC["HTML + Markdown"]
    
    AA --> DD["DefuddleResponse"]
    BB --> DD
    CC --> DD
```

출처: [src/defuddle.ts:40-186](), [src/defuddle.ts:64-175]()

## 핵심 컴포넌트

### 핵심 시스템 컴포넌트

`Defuddle` 클래스는 주요 오케스트레이터 역할을 하며, 잘 정의된 인터페이스를 통해 모든 추출 프로세스를 조율합니다.

```mermaid
classDiagram
    class Defuddle {
        -doc: Document
        -options: DefuddleOptions
        -debug: boolean
        +constructor(doc, options)
        +parse(): DefuddleResponse
        -parseInternal(overrideOptions): DefuddleResponse
        -findMainContent(doc): Element
        -removeBySelector(doc, removeExact, removePartial)
        -removeHiddenElements(doc)
        -findContentByScoring(doc): Element
        -applyMobileStyles(doc, styles)
        -findSmallImages(doc): Set~string~
        -removeSmallImages(doc, smallImages)
        -_evaluateMediaQueries(doc): StyleChange[]
        -_extractSchemaOrgData(doc): any
        -countWords(content): number
    }
    
    class DefuddleOptions {
        +debug?: boolean
        +url?: string
        +markdown?: boolean
        +separateMarkdown?: boolean
        +removeExactSelectors?: boolean
        +removePartialSelectors?: boolean
        +removeImages?: boolean
    }
    
    class DefuddleResponse {
        +content: string
        +contentMarkdown?: string
        +title: string
        +description: string
        +domain: string
        +favicon: string
        +image: string
        +published: string
        +author: string
        +site: string
        +schemaOrgData: any
        +wordCount: number
        +parseTime: number
        +extractorType?: string
        +metaTags?: MetaTagItem[]
    }
    
    Defuddle --> DefuddleOptions : uses
    Defuddle --> DefuddleResponse : returns
```

`Defuddle.parse()` 메서드는 정교한 추출 전략을 구현합니다.

1. **Metadata Collection**: 문서에서 Schema.org 데이터와 meta 태그를 추출합니다
2. **Site-Specific Detection**: `ExtractorRegistry.findExtractor()`를 사용해 특화 추출기를 찾습니다
3. **Fallback Processing**: 추출기를 찾지 못하면 범용 콘텐츠 추출을 적용합니다
4. **Retry Logic**: 초기 추출 결과의 콘텐츠가 적으면(200단어 미만), 덜 공격적인 잡음 제거 방식으로 재시도합니다
5. **Content Standardization**: `standardizeContent()`를 적용해 HTML 구조를 정규화합니다
6. **Response Generation**: 콘텐츠와 메타데이터가 포함된 구조화된 `DefuddleResponse`를 반환합니다

출처: [src/defuddle.ts:21-35](), [src/defuddle.ts:40-59](), [src/defuddle.ts:64-186](), [src/types.ts:1-83]()

### 추출 알고리즘 구현

추출 프로세스는 fallback 메커니즘을 포함한 2단계 접근 방식을 구현합니다.

```mermaid
flowchart TD
    A["Defuddle.parse()"] --> B["Extract metadata<br/>schemaOrgData, pageMetaTags"]
    B --> C["ExtractorRegistry.findExtractor(doc, url, schemaOrgData)"]
    C --> D{"extractor && extractor.canExtract()"}
    
    D -->|Yes| E["extractor.extract()"]
    E --> E1["Return ExtractedContent"]
    E1 --> F["Build DefuddleResponse with<br/>extracted.contentHtml"]
    
    D -->|No| G["Generic Extraction Pipeline"]
    
    G --> G1["_evaluateMediaQueries(doc)"]
    G1 --> G2["findSmallImages(doc)"]
    G2 --> G3["Clone document"]
    G3 --> G4["applyMobileStyles(clone, mobileStyles)"]
    G4 --> G5["findMainContent(clone)"]
    G5 --> G6["removeSmallImages(clone, smallImages)"]
    G6 --> G7["removeHiddenElements(clone)"]
    G7 --> G8["ContentScorer.scoreAndRemove(clone, debug)"]
    G8 --> G9["removeBySelector(clone, options)"]
    G9 --> G10["standardizeContent(mainContent, metadata, doc, debug)"]
    G10 --> H["DefuddleResponse"]
    
    F --> I{"wordCount < 200?"}
    H --> I
    I -->|Yes| J["parseInternal with<br/>removePartialSelectors: false"]
    J --> K["Return result with more content"]
    I -->|No| L["Return original result"]
    
    K --> M["Final DefuddleResponse"]
    L --> M
```

이 알고리즘에는 여러 최적화 전략이 포함됩니다.
- **Document Cloning**: 원본 문서는 보존하고 복제본을 수정합니다
- **Mobile Style Application**: CSS media query를 평가하고 적용해 모바일 콘텐츠 탐지를 개선합니다
- **Batch Processing**: 숨김 요소 제거와 작은 이미지 탐지는 성능을 위해 batching을 사용합니다
- **Retry Mechanism**: 추출 결과가 최소한의 콘텐츠만 생성하면, 잡음 제거 수준을 낮춰 재시도합니다

출처: [src/defuddle.ts:40-59](), [src/defuddle.ts:64-186](), [src/defuddle.ts:122-164]()

### 콘텐츠 점수화 시스템

`ContentScorer`는 여러 점수화 요인을 사용하는 heuristic 기반 콘텐츠 식별을 구현합니다.

```mermaid
flowchart TD
    A["ContentScorer.scoreAndRemove(clone, debug)"] --> B["Iterate through all elements"]
    B --> C["ContentScorer.scoreElement(element)"]
    
    C --> D["Calculate text density"]
    C --> E["Calculate link density"]
    C --> F["Analyze paragraph content"]
    C --> G["Check content indicators"]
    C --> H["Check navigation indicators"]
    C --> I["Evaluate element position"]
    
    D --> J["Combine scores"]
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
    
    J --> K{"Overall score < 0?"}
    K -->|Yes| L["Mark element for removal"]
    K -->|No| M["Keep element"]
    
    L --> N["Add to removal set"]
    M --> O["Continue to next element"]
    N --> O
    
    O --> P{"More elements?"}
    P -->|Yes| B
    P -->|No| Q["Remove all marked elements"]
    
    subgraph "Scoring Factors"
        SF1["Text-to-HTML ratio"]
        SF2["Link density thresholds"]
        SF3["Paragraph vs other element ratio"]
        SF4["Content keywords in class/id"]
        SF5["Navigation keywords in class/id"]
        SF6["Element depth and siblings"]
    end
    
    D -.-> SF1
    E -.-> SF2
    F -.-> SF3
    G -.-> SF4
    H -.-> SF5
    I -.-> SF6
```

`ContentScorer.findBestElement()` 메서드는 여러 후보가 있을 때 가장 가능성 높은 콘텐츠 컨테이너를 식별하기 위한 요소 순위화 기능도 제공합니다.

출처: [src/defuddle.ts:155](), [src/defuddle.ts:603-607](), [src/defuddle.ts:654]()

### 사이트별 추출기 시스템

`ExtractorRegistry`는 알려진 웹사이트를 위한 특화 추출기로 domain 기반 routing을 제공합니다.

```mermaid
graph TB
    subgraph "URL Input Processing"
        URL["Input URL"] --> DOMAIN["Domain Extraction"]
        DOMAIN --> CACHE{"Domain Cache Hit?"}
        CACHE -->|Yes| CACHED["Cached Extractor"]
        CACHE -->|No| PATTERNS["Pattern Matching"]
    end
    
    subgraph "Extractor Registry"
        PATTERNS --> TWITTER_PATTERNS["twitter.com, x.com/*"]
        PATTERNS --> REDDIT_PATTERNS["reddit.com variants"]
        PATTERNS --> YOUTUBE_PATTERNS["youtube.com/watch*"]
        PATTERNS --> GITHUB_PATTERNS["github.com/*"]
        PATTERNS --> CHATGPT_PATTERNS["chatgpt.com/(c|share)/*"]
        PATTERNS --> GROK_PATTERNS["grok.com/(chat|share)*"]
        PATTERNS --> GEMINI_PATTERNS["gemini.google.com/app/*"]
    end
    
    subgraph "Specialized Extractors"
        TWITTER_PATTERNS --> TWITTER_EXT["TwitterExtractor<br/>• Tweet threads<br/>• Media extraction<br/>• Quote tweets"]
        REDDIT_PATTERNS --> REDDIT_EXT["RedditExtractor<br/>• Post content<br/>• Comment threads"]
        YOUTUBE_PATTERNS --> YOUTUBE_EXT["YoutubeExtractor<br/>• Video metadata<br/>• Embed generation"]
        GITHUB_PATTERNS --> GITHUB_EXT["GitHubExtractor<br/>• Issue content<br/>• Comment processing"]
        CHATGPT_PATTERNS --> CHATGPT_EXT["ChatGPTExtractor<br/>• Conversation messages<br/>• Citation processing"]
        GROK_PATTERNS --> GROK_EXT["GrokExtractor<br/>• Message extraction<br/>• Footnote handling"]
        GEMINI_PATTERNS --> GEMINI_EXT["GeminiExtractor<br/>• Query/response pairs<br/>• Source references"]
    end
    
    subgraph "Base Classes"
        BASE["BaseExtractor<br/>Abstract Base"]
        CONV["ConversationExtractor<br/>Chat-based Content"]
        
        BASE --> TWITTER_EXT
        BASE --> REDDIT_EXT
        BASE --> YOUTUBE_EXT
        BASE --> GITHUB_EXT
        CONV --> CHATGPT_EXT
        CONV --> GROK_EXT
        CONV --> GEMINI_EXT
        BASE --> CONV
    end
    
    subgraph "Output"
        CACHED --> RESULT["ExtractorResult"]
        TWITTER_EXT --> RESULT
        REDDIT_EXT --> RESULT
        YOUTUBE_EXT --> RESULT
        GITHUB_EXT --> RESULT
        CHATGPT_EXT --> RESULT
        GROK_EXT --> RESULT
        GEMINI_EXT --> RESULT
        
        RESULT --> STANDARDIZED["Standardized Content<br/>+ Metadata"]
    end
```

각 추출기는 `canExtract()`와 `extract()` 메서드를 구현하며, 콘텐츠 구조와 메타데이터에 대한 사이트별 최적화가 포함된 `ExtractedContent`를 반환합니다.

출처: [src/defuddle.ts:97-118]()

### 콘텐츠 표준화 파이프라인

`standardizeContent()` 함수는 여러 처리 단계를 통해 포괄적인 HTML 정규화를 적용합니다.

```mermaid
flowchart TD
    A["mainContent element"] --> B["standardizeContent(mainContent, metadata, doc, debug)"]
    
    B --> C["Phase 1: Basic Cleanup"]
    C --> C1["standardizeSpaces"]
    C --> C2["removeHtmlComments"]
    C --> C3["standardizeHeadings"]
    C --> C4["standardizeFootnotes"]
    
    B --> D["Phase 2: Element Processing"]
    D --> D1["standardizeElements"]
    D1 --> D2["Apply Element-Specific Rules"]
    
    D2 --> D3["imageRules<br/>Picture/Figure Processing"]
    D2 --> D4["mathRules<br/>LaTeX/MathML Conversion"]
    D2 --> D5["codeBlockRules<br/>Syntax Highlighting Cleanup"]
    D2 --> D6["headingRules<br/>Navigation Cleanup"]
    
    B --> E["Phase 3: Structure Cleanup"]
    E --> E1["flattenWrapperElements"]
    E --> E2["stripUnwantedAttributes"]
    E --> E3["removeEmptyElements"]
    
    C1 --> F["Normalized Content"]
    C2 --> F
    C3 --> F
    C4 --> F
    D3 --> F
    D4 --> F
    D5 --> F
    D6 --> F
    E1 --> F
    E2 --> F
    E3 --> F
    
    subgraph "Element Rules Processing"
        ER1["Image standardization:<br/>• Converts <picture> to <img><br/>• Handles lazy loading<br/>• Processes srcset"]
        ER2["Math standardization:<br/>• MathML to LaTeX<br/>• Inline math detection<br/>• Block math formatting"]
        ER3["Code standardization:<br/>• Syntax highlighter cleanup<br/>• Language detection<br/>• Pre/code normalization"]
        ER4["Heading standardization:<br/>• Navigation removal<br/>• Anchor link cleanup<br/>• Hierarchy validation"]
    end
    
    D3 -.-> ER1
    D4 -.-> ER2
    D5 -.-> ER3
    D6 -.-> ER4
```

표준화 프로세스는 서로 다른 원본 웹사이트와 콘텐츠 관리 시스템 전반에서 일관된 HTML 구조를 보장합니다.

출처: [src/defuddle.ts:163]()

## 배포 아키텍처

Defuddle은 서로 다른 배포 시나리오에 최적화된 세 가지 배포 번들을 제공합니다.

### 번들 구성

```mermaid
graph TB
    subgraph "Source Code"
        SRC["TypeScript Source Files<br/>src/**/*.ts"]
        TYPES["Type Definitions<br/>DefuddleOptions, DefuddleResponse"]
        TESTS["Test Suite<br/>Fixture-based Testing"]
    end
    
    subgraph "Build System"
        WEBPACK["Webpack Configuration<br/>Multiple Bundle Targets"]
        TSC["TypeScript Compiler<br/>Type Generation"]
        TERSER["Code Minification<br/>Production Optimization"]
    end
    
    subgraph "Distribution Bundles"
        CORE["Core Bundle (index.js)<br/>• Browser-focused<br/>• External math deps<br/>• Zero dependencies"]
        FULL["Full Bundle (index.full.js)<br/>• All features included<br/>• Math processing built-in<br/>• Self-contained"]
        NODE["Node.js Bundle (node.js)<br/>• Server-side optimized<br/>• JSDOM integration<br/>• Full math support"]
    end
    
    subgraph "Runtime Dependencies"
        JSDOM["JSDOM<br/>Server-side DOM"]
        MATHLIBS["Math Libraries<br/>mathml-to-latex, temml"]
        TURNDOWN["Turndown<br/>HTML to Markdown"]
    end
    
    subgraph "Development & Deployment"
        PLAYGROUND["GitHub Pages Playground<br/>Interactive Testing"]
        CI["GitHub Actions<br/>Automated Deployment"]
        NPM["NPM Registry<br/>Package Distribution"]
    end
    
    SRC --> WEBPACK
    SRC --> TSC
    TYPES --> TSC
    
    WEBPACK --> CORE
    WEBPACK --> FULL
    TSC --> NODE
    
    CORE -.->|External| MATHLIBS
    FULL --> MATHLIBS
    NODE --> JSDOM
    NODE --> MATHLIBS
    NODE --> TURNDOWN
    
    WEBPACK --> PLAYGROUND
    CI --> PLAYGROUND
    CI --> NPM
    
    TESTS --> CI
```

### 번들 비교

| 번들 | 대상 | 엔트리 포인트 | 의존성 | 사용 사례 |
|--------|--------|-------------|--------------|----------|
| Core | 브라우저 | `./dist/index.js` | 없음 | 가벼운 브라우저 통합 |
| Full | 브라우저 | `./dist/index.full.js` | mathml-to-latex, temml | 완전한 브라우저 기능 |
| Node.js | 서버 | `./dist/node.js` | jsdom, turndown | 서버 측 처리 |

모듈식 아키텍처를 통해 개발자는 배포 요구사항과 의존성 제약에 따라 적절한 번들을 선택할 수 있습니다.

출처: 빌드 시스템 분석과 패키지 구조 기반

## 통합 인터페이스

Defuddle은 다른 시스템과 통합하기 위한 인터페이스를 제공합니다.

### 타입 시스템 아키텍처

라이브러리의 타입 시스템은 설정과 데이터 교환을 위한 포괄적인 인터페이스를 제공합니다.

#### 핵심 설정 타입

| 인터페이스 | 목적 | 주요 속성 |
|-----------|---------|----------------|
| `DefuddleOptions` | 추출 설정 | `debug`, `url`, `markdown`, `removeExactSelectors`, `removePartialSelectors`, `removeImages` |
| `DefuddleResponse` | 추출 결과 | `content`, `title`, `description`, `wordCount`, `parseTime`, `extractorType` |
| `DefuddleMetadata` | 문서 메타데이터 | `title`, `description`, `domain`, `favicon`, `image`, `published`, `author`, `site` |

#### 추출기 시스템 타입

| 인터페이스 | 목적 | 주요 속성 |
|-----------|---------|----------------|
| `ExtractedContent` | 추출기 출력 | `title`, `author`, `published`, `content`, `contentHtml`, `variables` |
| `ExtractorVariables` | 동적 메타데이터 | 추출기별 데이터를 위한 key-value 쌍 |
| `MetaTagItem` | HTML meta 태그 | `name`, `property`, `content` |

#### 타입 관계

```mermaid
classDiagram
    class DefuddleOptions {
        +debug?: boolean
        +url?: string
        +markdown?: boolean
        +separateMarkdown?: boolean
        +removeExactSelectors?: boolean
        +removePartialSelectors?: boolean
        +removeImages?: boolean
    }
    
    class DefuddleMetadata {
        +title: string
        +description: string
        +domain: string
        +favicon: string
        +image: string
        +parseTime: number
        +published: string
        +author: string
        +site: string
        +schemaOrgData: any
        +wordCount: number
    }
    
    class DefuddleResponse {
        +content: string
        +contentMarkdown?: string
        +extractorType?: string
        +metaTags?: MetaTagItem[]
    }
    
    class ExtractedContent {
        +title?: string
        +author?: string
        +published?: string
        +content?: string
        +contentHtml?: string
        +variables?: ExtractorVariables
    }
    
    DefuddleResponse --|> DefuddleMetadata : extends
    DefuddleOptions --> DefuddleResponse : configures
    ExtractedContent --> DefuddleResponse : transforms to
```

출처: [src/types.ts:1-83]()

## 데이터 흐름 요약

문서에서 콘텐츠를 추출할 때 Defuddle은 다음 순서를 따릅니다.

1. 먼저 문서에서 메타데이터(제목, 작성자 등)를 추출합니다
2. 사이트별 추출기가 존재하며 문서를 처리할 수 있는지 확인합니다
   - 가능하면 추출기를 사용해 콘텐츠와 메타데이터를 가져옵니다
3. 추출기가 없거나 추출이 실패하면 범용 추출을 적용합니다.
   - 추출을 개선하기 위해 모바일 스타일을 평가하고 적용합니다
   - 주요 콘텐츠 컨테이너를 찾습니다
   - 작은 이미지와 숨김 요소를 제거합니다
   - 콘텐츠 점수화를 적용해 콘텐츠가 아닌 블록을 제거합니다
   - 미리 정의된 selector를 사용해 잡음 요소를 제거합니다
   - 콘텐츠를 표준화합니다
4. 추출된 콘텐츠와 메타데이터를 `DefuddleResponse`로 반환합니다

출처: [src/defuddle.ts:64-164]()
