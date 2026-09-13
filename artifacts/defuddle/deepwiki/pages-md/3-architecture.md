# Architecture

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [package-lock.json](package-lock.json)
- [package.json](package.json)
- [src/constants.ts](src/constants.ts)
- [src/defuddle.ts](src/defuddle.ts)
- [tsconfig.node.json](tsconfig.node.json)
- [webpack.config.js](webpack.config.js)

</details>



This document provides an overview of Defuddle's high-level architecture, including its key components, data flow, and system organization. It explains how the different parts of the codebase work together to extract and process content from web pages.

For information about using the library, see [Overview](#1). For details on how content is extracted, see [Content Extraction](#3).

## System Overview

Defuddle is a content extraction library that processes HTML documents to identify and extract main content while removing clutter, ads, and navigation elements. The system follows a modular architecture with specialized extractors for known websites and a generic extraction pipeline for general web content.

### Overall System Architecture

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

Sources: [src/defuddle.ts:1-14](), [src/defuddle.ts:21-35](), [src/defuddle.ts:40-59]()

### Content Processing Pipeline

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

Sources: [src/defuddle.ts:40-186](), [src/defuddle.ts:64-175]()

## Core Components

### Core System Components

The `Defuddle` class serves as the main orchestrator, coordinating all extraction processes through a well-defined interface.

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

The `Defuddle.parse()` method implements a sophisticated extraction strategy:

1. **Metadata Collection**: Extracts Schema.org data and meta tags from the document
2. **Site-Specific Detection**: Uses `ExtractorRegistry.findExtractor()` to find specialized extractors
3. **Fallback Processing**: If no extractor is found, applies generic content extraction
4. **Retry Logic**: If initial extraction yields little content (< 200 words), retries with less aggressive clutter removal
5. **Content Standardization**: Applies `standardizeContent()` to normalize HTML structure
6. **Response Generation**: Returns structured `DefuddleResponse` with content and metadata

Sources: [src/defuddle.ts:21-35](), [src/defuddle.ts:40-59](), [src/defuddle.ts:64-186](), [src/types.ts:1-83]()

### Extraction Algorithm Implementation

The extraction process implements a two-phase approach with fallback mechanisms:

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

The algorithm includes several optimization strategies:
- **Document Cloning**: Original document is preserved while a clone is modified
- **Mobile Style Application**: CSS media queries are evaluated and applied for better mobile content detection
- **Batch Processing**: Hidden element removal and small image detection use batching for performance
- **Retry Mechanism**: If extraction produces minimal content, retries with reduced clutter removal

Sources: [src/defuddle.ts:40-59](), [src/defuddle.ts:64-186](), [src/defuddle.ts:122-164]()

### Content Scoring System

The `ContentScorer` implements heuristic-based content identification using multiple scoring factors:

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

The `ContentScorer.findBestElement()` method also provides element ranking functionality for identifying the most likely content container when multiple candidates exist.

Sources: [src/defuddle.ts:155](), [src/defuddle.ts:603-607](), [src/defuddle.ts:654]()

### Site-Specific Extractor System

The `ExtractorRegistry` provides domain-based routing to specialized extractors for known websites:

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

Each extractor implements the `canExtract()` and `extract()` methods, returning `ExtractedContent` with site-specific optimizations for content structure and metadata.

Sources: [src/defuddle.ts:97-118]()

### Content Standardization Pipeline

The `standardizeContent()` function applies comprehensive HTML normalization through multiple processing phases:

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

The standardization process ensures consistent HTML structure across different source websites and content management systems.

Sources: [src/defuddle.ts:163]()

## Distribution Architecture

Defuddle provides three distribution bundles optimized for different deployment scenarios:

### Bundle Configuration

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

### Bundle Comparison

| Bundle | Target | Entry Point | Dependencies | Use Case |
|--------|--------|-------------|--------------|----------|
| Core | Browser | `./dist/index.js` | None | Lightweight browser integration |
| Full | Browser | `./dist/index.full.js` | mathml-to-latex, temml | Complete browser functionality |
| Node.js | Server | `./dist/node.js` | jsdom, turndown | Server-side processing |

The modular architecture allows developers to choose the appropriate bundle based on their deployment requirements and dependency constraints.

Sources: Based on build system analysis and package structure

## Integration Interfaces

Defuddle provides interfaces for integration with other systems:

### Type System Architecture

The library's type system provides comprehensive interfaces for configuration and data exchange:

#### Core Configuration Types

| Interface | Purpose | Key Properties |
|-----------|---------|----------------|
| `DefuddleOptions` | Extraction configuration | `debug`, `url`, `markdown`, `removeExactSelectors`, `removePartialSelectors`, `removeImages` |
| `DefuddleResponse` | Extraction results | `content`, `title`, `description`, `wordCount`, `parseTime`, `extractorType` |
| `DefuddleMetadata` | Document metadata | `title`, `description`, `domain`, `favicon`, `image`, `published`, `author`, `site` |

#### Extractor System Types

| Interface | Purpose | Key Properties |
|-----------|---------|----------------|
| `ExtractedContent` | Extractor output | `title`, `author`, `published`, `content`, `contentHtml`, `variables` |
| `ExtractorVariables` | Dynamic metadata | Key-value pairs for extractor-specific data |
| `MetaTagItem` | HTML meta tags | `name`, `property`, `content` |

#### Type Relationships

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

Sources: [src/types.ts:1-83]()

## Data Flow Summary

When extracting content from a document, Defuddle follows this sequence:

1. Extract metadata from the document first (title, author, etc.)
2. Check if a site-specific extractor exists and can handle the document
   - If yes, use the extractor to get content and metadata
3. If no extractor or extraction fails, apply generic extraction:
   - Evaluate and apply mobile styles to improve extraction
   - Find the main content container
   - Remove small images and hidden elements
   - Apply content scoring to remove non-content blocks
   - Remove clutter elements using predefined selectors
   - Standardize the content
4. Return the extracted content and metadata as a `DefuddleResponse`

Sources: [src/defuddle.ts:64-164]()
