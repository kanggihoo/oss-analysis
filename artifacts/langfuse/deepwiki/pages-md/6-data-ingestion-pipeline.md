# Data Ingestion Pipeline

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

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



## Purpose and Scope

This document describes the data ingestion system responsible for receiving, validating, and storing observability events in Langfuse. The ingestion pipeline handles two primary input formats: native Langfuse SDK events and OpenTelemetry (OTLP) traces, converting both into a unified event format for storage and querying.

The pipeline is designed for high-volume data processing using a decoupled architecture where the web layer handles initial acceptance and durability (S3), while background workers handle heavy processing, model cost calculation, and persistence.

**Scope:**
- HTTP API endpoints for event ingestion (`/api/public/ingestion`) [[web/src/pages/api/public/ingestion.ts:50-53]()]
- Event validation and multi-tenant authentication via `ApiAuthService` [[web/src/features/public-api/server/apiAuth.ts:90-94]()]
- S3-based durability layer and deduplication logic [[web/src/pages/api/public/ingestion.ts:42-45]()]
- Queue-based asynchronous processing via BullMQ [[worker/src/services/IngestionService/index.ts:28-29]()]
- Event propagation from staging tables to the final events architecture [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:58-60]()]

## Architecture Overview

The ingestion architecture spans from the public API handlers in the `web` service to background workers that process and persist data. Langfuse utilizes an event-sourcing pattern where raw observations are processed and stored in ClickHouse.

### System Flow Diagram
The following diagram illustrates the flow from external SDKs to internal code entities and storage.

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

**Sources:**
- [[web/src/pages/api/public/ingestion.ts:50-139]()]
- [[web/src/features/public-api/server/apiAuth.ts:90-206]()]
- [[worker/src/services/IngestionService/index.ts:148-194]()]
- [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:140-185]()]

## Ingestion Endpoints

### Native SDK Ingestion Endpoint
**Route:** `POST /api/public/ingestion`
The native ingestion endpoint accepts batches of Langfuse events. It uses `ApiAuthService` to verify project-level API keys and `RateLimitService` to enforce ingestion quotas [[web/src/pages/api/public/ingestion.ts:76-111]()]. The `bodyParser` is configured to handle up to 4.5mb payloads [[web/src/pages/api/public/ingestion.ts:26-32]()]. It returns a `207 Multi-Status` response containing successes and errors for individual events in the batch [[web/src/pages/api/public/ingestion.ts:139]()].

### OpenTelemetry (OTLP) Endpoint
**Route:** `POST /api/public/otel/v1/traces`
This endpoint accepts OTLP traces. Ingestion is handled asynchronously via the `OtelIngestionProcessor` which manages the conversion of OTel spans into Langfuse entities like `GENERATION`, `SPAN`, or `EVENT`.

## Event Processing and Validation

### IngestionService
The `IngestionService` is the core component for processing ingestion events in the worker. It performs heavy lifting such as:
- **Prompt Lookup:** Matching events to prompt versions [[worker/src/services/IngestionService/index.ts:226-233]()].
- **Usage Enrichment:** Calculating token counts and costs using `tokenCountAsync` [[worker/src/services/IngestionService/index.ts:54-55]()].
- **Entity Merging:** Merging trace, observation, and score updates [[worker/src/services/IngestionService/index.ts:148-194]()].

### Data Entity Association Diagram
This diagram shows how code entities interact with the ingestion and storage layers, specifically highlighting the `IngestionService` and `ClickhouseWriter` responsibilities.

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

**Sources:**
- [[worker/src/services/IngestionService/index.ts:211-233]()]
- [[worker/src/services/ClickhouseWriter/index.ts:1-10]()]
- [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:185-200]()]

## Event Propagation System

Langfuse utilizes a robust architecture to manage high-throughput writes and eventual consistency via a "Dual Write" or propagation strategy.

1.  **Staging Table:** Observations are first written to the `observations_batch_staging` table in ClickHouse, which uses 3-minute partitions for efficient batch processing [[packages/shared/clickhouse/scripts/dev-tables.sh:81-130]()].
2.  **Propagation Job:** The `handleEventPropagationJob` runs periodically to process these partitions [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:58-60]()].
3.  **Trace Enrichment:** During propagation, staging observations are joined with trace metadata (user ID, session ID, tags) to create fully enriched records in the `events_full` table [[worker/src/features/eventPropagation/handleEventPropagationJob.ts:140-185]()].
4.  **Backfill Support:** The system includes mechanisms for historic backfills, such as `BackfillEventsHistoric`, to migrate legacy data into the new events architecture [[worker/src/backgroundMigrations/backfillEventsHistoric.ts:175-180]()].

## Child Pages
For detailed implementation specifics, refer to the following sub-pages:
- [Ingestion Overview](#6.1) — Detailed flow from API request through S3 and Queue.
- [Ingestion API Endpoints](#6.2) — Documentation of `/api/public/ingestion` and OTel endpoints.
- [Event Processing & Validation](#6.3) — Details on `processEventBatch`, deduplication, and Zod validation.
- [Event Enrichment & Masking](#6.4) — PII masking, tokenization, and cost calculation logic in `IngestionService`.
- [Event Propagation System](#6.5) — The staging-to-events propagation mechanics and consistency guarantees.
- [OpenTelemetry Ingestion](#6.6) — Mapping OTLP spans to Langfuse entities.
