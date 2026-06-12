---
type: deepwiki-translation
repo: langfuse
source: artifacts/langfuse/deepwiki/pages-md/6-data-ingestion-pipeline.md
deepwiki_url: https://deepwiki.com/langfuse/langfuse/6-data-ingestion-pipeline
section: "6"
order: 26
---

# 데이터 수집 파이프라인

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하는 컨텍스트로 사용되었습니다.

- [fern/apis/server/definition/ingestion.yml](fern/apis/server/definition/ingestion.yml)
- [packages/shared/clickhouse/scripts/dev-tables.sh](packages/shared/clickhouse/scripts/dev-tables.sh)
- [packages/shared/src/server/auth/types.ts](packages/shared/src/server/auth/types.ts)
- [packages/shared/src/server/headerPropagation.ts](packages/shared/src/server/headerPropagation.ts)
- [packages/shared/src/server/ingestion/types.ts](packages/shared/src/server/ingestion/types.ts)
- [packages/shared/src/server/instrumentation/index.ts](packages/shared/src/server/instrumentation/index.ts)
- [packages/shared/src/server/queries/clickhouse-sql/clickhouse-filter.ts](packages/shared/src/server/queries/clickhouse-sql/clickhouse-filter.ts)
- [packages/shared/src/server/redis/eventPropagationQueue.ts](packages/shared/src/server/redis/eventPropagationQueue.ts)
- [packages/shared/src/server/repositories/definitions.ts](packages/shared/src/server/repositories/definitions.ts)
- [packages/shared/src/server/test-utils/tracing-factory.ts](packages/shared/src/server/test-utils/tracing-factory.ts)
- [packages/shared/src/utils/json.ts](packages/shared/src/utils/json.ts)
- [web/src/__tests__/server/unit/api-auth-span.servertest.ts](web/src/__tests__/server/unit/api-auth-span.servertest.ts)
- [web/src/__tests__/server/unit/langfuse-context-propagation.servertest.ts](web/src/__tests__/server/unit/langfuse-context-propagation.servertest.ts)
- [web/src/features/public-api/server/apiAuth.ts](web/src/features/public-api/server/apiAuth.ts)
- [web/src/features/public-api/server/createAuthedProjectAPIRoute.ts](web/src/features/public-api/server/createAuthedProjectAPIRoute.ts)
- [web/src/pages/api/public/ingestion.ts](web/src/pages/api/public/ingestion.ts)
- [worker/src/backgroundMigrations/backfillEventsHistoric.ts](worker/src/backgroundMigrations/backfillEventsHistoric.ts)
- [worker/src/backgroundMigrations/backfillEventsHistoricFromParts.ts](worker/src/backgroundMigrations/backfillEventsHistoricFromParts.ts)
- [worker/src/backgroundMigrations/backfillExperimentsHistoric.ts](worker/src/backgroundMigrations/backfillExperimentsHistoric.ts)
- [worker/src/features/eventPropagation/handleEventPropagationJob.ts](worker/src/features/eventPropagation/handleEventPropagationJob.ts)
- [worker/src/features/eventPropagation/handleExperimentBackfill.ts](worker/src/features/eventPropagation/handleExperimentBackfill.ts)
- [worker/src/services/IngestionService/index.ts](worker/src/services/IngestionService/index.ts)
- [worker/src/services/IngestionService/tests/IngestionService.integration.test.ts](worker/src/services/IngestionService/tests/IngestionService.integration.test.ts)
- [worker/src/services/IngestionService/tests/calculateTokenCost.unit.test.ts](worker/src/services/IngestionService/tests/calculateTokenCost.unit.test.ts)
- [worker/src/services/IngestionService/tests/utils.unit.test.ts](worker/src/services/IngestionService/tests/utils.unit.test.ts)
- [worker/src/services/IngestionService/utils.ts](worker/src/services/IngestionService/utils.ts)

</details>



## 목적과 범위

이 문서는 Langfuse에서 observability event를 수신, 검증, 저장하는 데이터 수집 시스템을 설명합니다. 수집 파이프라인은 두 가지 주요 입력 형식, 즉 native Langfuse SDK events와 OpenTelemetry(OTLP) traces를 처리하며, 둘 모두를 저장과 쿼리를 위한 통합 event format으로 변환합니다.

파이프라인은 decoupled architecture를 사용한 대용량 데이터 처리를 위해 설계되었습니다. web layer가 초기 수락과 durability(S3)를 처리하고, background worker가 무거운 처리, model cost calculation, persistence를 담당합니다.

**범위:**
- event ingestion을 위한 HTTP API endpoint(`/api/public/ingestion`) [[web/src/pages/api/public/ingestion.ts:50-53]()]
- `ApiAuthService`를 통한 event validation 및 multi-tenant authentication [[web/src/features/public-api/server/apiAuth.ts:90-94]()]
- S3 기반 durability layer 및 deduplication logic [[web/src/pages/api/public/ingestion.ts:42-45]()]
- BullMQ를 통한 queue-based asynchronous processing [[worker/src/services/IngestionService/index.ts:28-29]()]
- staging table에서 final events architecture로의 event propagation [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:58-60]()]

## 아키텍처 개요

수집 아키텍처는 `web` service의 public API handler부터 데이터를 처리하고 저장하는 background worker까지 걸쳐 있습니다. Langfuse는 raw observations가 처리되어 ClickHouse에 저장되는 event-sourcing pattern을 활용합니다.

### 시스템 흐름 다이어그램
다음 다이어그램은 외부 SDK에서 내부 code entity와 storage까지의 흐름을 보여줍니다.

```mermaid
graph TB
    subgraph "Ingestion Endpoints (web/src/pages/api/public)"
        [SDK] -->|"POST /ingestion"| [ingestion_handler]
        [OTel_Collector] -->|"POST /otel/v1/traces"| [otel_traces_handler]
    end
    
    subgraph "Validation & Auth (web/src/features/public-api/server)"
        [ingestion_handler] --> [ApiAuthService_verifyAuthHeaderAndReturnScope]
        [ApiAuthService_verifyAuthHeaderAndReturnScope] --> [RateLimitService_rateLimitRequest]
    end
    
    subgraph "Processing Logic"
        [RateLimitService_rateLimitRequest] --> [processEventBatch]
        [processEventBatch] --> [StorageService_S3]
    end
    
    subgraph "Queue Layer (Redis/BullMQ)"
        [processEventBatch] --> [IngestionQueue]
        [otel_traces_handler] --> [OtelIngestionQueue]
    end
    
    subgraph "Worker Processing (worker/src/services)"
        [IngestionQueue] --> [IngestionService]
        [OtelIngestionQueue] --> [OtelIngestionProcessor]
        [IngestionService] --> [ClickhouseWriter]
    end

    subgraph "ClickHouse Storage"
        [ClickhouseWriter] --> [observations_batch_staging]
        [observations_batch_staging] --> [handleEventPropagationJob]
        [handleEventPropagationJob] --> [events_full]
    end
```

**출처:**
- [[web/src/pages/api/public/ingestion.ts:50-139]()]
- [[web/src/features/public-api/server/apiAuth.ts:90-206]()]
- [[worker/src/services/IngestionService/index.ts:148-194]()]
- [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:140-185]()]

## 수집 엔드포인트

### Native SDK Ingestion Endpoint
**Route:** `POST /api/public/ingestion`
native ingestion endpoint는 Langfuse event batch를 받습니다. Project-level API key를 검증하기 위해 `ApiAuthService`를 사용하고, ingestion quota를 enforce하기 위해 `RateLimitService`를 사용합니다 [[web/src/pages/api/public/ingestion.ts:76-111]()]. `bodyParser`는 최대 4.5mb payload를 처리하도록 구성됩니다 [[web/src/pages/api/public/ingestion.ts:26-32]()]. Batch 내 개별 event의 성공과 오류를 포함하는 `207 Multi-Status` response를 반환합니다 [[web/src/pages/api/public/ingestion.ts:139]()]. 

### OpenTelemetry(OTLP) Endpoint
**Route:** `POST /api/public/otel/v1/traces`
이 endpoint는 OTLP traces를 받습니다. 수집은 OTel span을 `GENERATION`, `SPAN`, `EVENT` 같은 Langfuse entity로 변환하는 `OtelIngestionProcessor`를 통해 비동기적으로 처리됩니다.

## Event Processing 및 Validation

### IngestionService
`IngestionService`는 worker에서 ingestion event를 처리하는 핵심 component입니다. 다음과 같은 heavy lifting을 수행합니다.
- **Prompt Lookup:** event를 prompt version과 matching합니다 [[worker/src/services/IngestionService/index.ts:226-233]()]. 
- **Usage Enrichment:** `tokenCountAsync`를 사용해 token count와 cost를 계산합니다 [[worker/src/services/IngestionService/index.ts:54-55]()]. 
- **Entity Merging:** trace, observation, score update를 merge합니다 [[worker/src/services/IngestionService/index.ts:148-194]()]. 

### 데이터 Entity Association Diagram
이 다이어그램은 code entity가 ingestion 및 storage layer와 상호작용하는 방식을 보여주며, 특히 `IngestionService`와 `ClickhouseWriter`의 책임을 강조합니다.

```mermaid
graph TD
    subgraph "Ingestion Logic"
        [processEventBatch]
        [IngestionService_createEventRecord]
        [PromptService_getPrompt]
    end

    subgraph "Storage & Persistence"
        [ClickhouseWriter_enqueue]
        [observations_batch_staging]
        [events_full]
    end

    [processEventBatch] --> [IngestionService_createEventRecord]
    [IngestionService_createEventRecord] --> [PromptService_getPrompt]
    [IngestionService_createEventRecord] --> [ClickhouseWriter_enqueue]
    [ClickhouseWriter_enqueue] --> [observations_batch_staging]
    [observations_batch_staging] --> [handleEventPropagationJob]
    [handleEventPropagationJob] --> [events_full]
```

**출처:**
- [[worker/src/services/IngestionService/index.ts:211-233]()]
- [[worker/src/services/ClickhouseWriter/index.ts:1-10]()]
- [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:185-200]()]

## Event Propagation System

Langfuse는 "Dual Write" 또는 propagation strategy를 통해 high-throughput write와 eventual consistency를 관리하는 견고한 아키텍처를 활용합니다.

1.  **Staging Table:** Observations는 먼저 ClickHouse의 `observations_batch_staging` table에 기록됩니다. 이 table은 효율적인 batch processing을 위해 3분 partition을 사용합니다 [[packages/shared/clickhouse/scripts/dev-tables.sh:81-130]()]. 
2.  **Propagation Job:** `handleEventPropagationJob`은 이러한 partition을 처리하기 위해 주기적으로 실행됩니다 [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:58-60]()]. 
3.  **Trace Enrichment:** Propagation 중 staging observations는 trace metadata(user ID, session ID, tags)와 join되어 `events_full` table의 완전히 enrich된 record를 생성합니다 [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:140-185]()]. 
4.  **Backfill Support:** 시스템에는 legacy data를 새로운 events architecture로 migrate하기 위한 `BackfillEventsHistoric` 같은 historic backfill mechanism이 포함됩니다 [[worker/src/backgroundMigrations/backfillEventsHistoric.ts:175-180]()]. 

## 하위 페이지
자세한 구현 세부사항은 다음 하위 페이지를 참조하세요.
- [Ingestion Overview](#6.1) — API request에서 S3 및 Queue까지의 상세 흐름.
- [Ingestion API Endpoints](#6.2) — `/api/public/ingestion` 및 OTel endpoint 문서.
- [Event Processing & Validation](#6.3) — `processEventBatch`, deduplication, Zod validation 세부사항.
- [Event Enrichment & Masking](#6.4) — `IngestionService`의 PII masking, tokenization, cost calculation logic.
- [Event Propagation System](#6.5) — staging-to-events propagation mechanics 및 consistency guarantee.
- [OpenTelemetry Ingestion](#6.6) — OTLP span을 Langfuse entity로 mapping.
