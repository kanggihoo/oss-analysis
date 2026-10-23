---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
sources:
  - packages/core/src/services/history/types.ts
  - packages/core/src/services/history/manager.ts
  - packages/core/src/services/history/errors.ts
  - packages/core/src/services/history/electron-proxy.ts
  - packages/core/src/services/storage/types.ts
  - packages/core/src/services/storage/adapter.ts
  - packages/core/src/constants/storage-keys.ts
  - packages/core/src/constants/error-codes.ts
  - packages/core/src/services/prompt/service.ts
  - packages/ui/src/composables/prompt/usePromptOptimizer.ts
  - packages/ui/src/composables/prompt/usePromptHistory.ts
  - packages/ui/src/composables/workspaces/useBasicWorkspaceLogic.ts
  - packages/ui/src/utils/history-source-binding.ts
  - packages/ui/src/types/evaluation.ts
depends: []
status: ready
reimplementation: 미실행
---

# 히스토리·버전 체인 (데이터 모델 중심)

> 최적화·반복 개선의 결과 한 건을 "기록(PromptRecord)"으로 만들어 체인(chainId) 안에 번호(version)를 붙여 쌓고, 체인 단위로 조회·삭제하는 저장 계약이다. 서비스는 저장하지 않고 호출자(UI)가 `createNewChain`·`addIteration`을 부른다.

경로 표기: 이 문서의 `파일:줄`은 모두 `repos/prompt-optimizer/` 기준이다. 라이선스는 AGPL-3.0-only(overview 1절)이므로 코드를 복사하지 않고 C-ID로 위치만 가리킨다. 설치·빌드·실행은 하지 않았고, 모든 검증 수준은 읽기 기준이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. UI가 최적화를 마치면(`PromptService`는 저장하지 않는다) 호출자가 기록 한 건을 만들어 `createNewChain`에 넘긴다. 매니저가 `chainId`(uuid v4)를 만들고 `version=1`, `previousId` 없음으로 저장한다.
2. 저장은 하나의 키(`prompt_history`) 아래 `PromptRecord[]` 전체를 JSON 문자열로 갱신하는 방식이다. 새 기록은 배열 맨 앞에 붙고, 배열이 50건을 넘으면 뒤쪽(먼저 들어온 쪽)이 잘린다.
3. 호출자가 사용자 요구사항(`iterationNote`)으로 반복 개선하거나 사용자가 결과를 직접 고치면 `addIteration`을 부른다. 매니저가 체인의 최고 버전을 찾아 `version+1`, `previousId=최고 버전 id`로 `type: 'iterate'` 기록을 추가한다.
4. 두 연산 모두 저장 후 `getChain`으로 체인을 다시 읽어 `{chainId, rootRecord(v1), currentRecord(최고 버전), versions(버전 오름차순)}`를 돌려준다. UI는 이를 상태(`currentChainId`, `currentVersions`, `currentVersionId`)에 넣는다.
5. 조회는 `getAllChains`(체인별, 최신 기록 시각 내림차순)·`getChain`·`getIterationChain`(`previousId`를 거슬러 올라간 목록)이다. 삭제는 기록 1건(`deleteRecord`), 체인 전체(`deleteChain`), 전체(`clearHistory`)다.
6. 저장 실패는 UI가 경고 토스트로만 알리고 화면의 결과는 유지된다.

### 1.2 범위·통합 지점 [필수]
- 제공: 기록(버전) 한 건의 데이터 모델, 체인 구성 규칙(번호·부모·정렬), 저장·조회·삭제 연산, 저장소 계약 위의 저장 방식, 개수 제한.
- 제외: 히스토리 UI 화면(`HistoryDrawer.vue` 등), 즐겨찾기, 데이터 가져오기·내보내기(`exportData`/`importData`/`validateData`는 읽었지만 스펙 범위 밖). 단, 가져오기가 요구하는 필드 집합은 R-03 비고에 한 줄 적었다.
- 외부 의존·선행 계약:
  - `IStorageProvider`(C-04): 매니저가 문자열 읽기·쓰기·삭제와 `updateData`를 쓴다. 구현은 Dexie·localStorage·파일·메모리(`services/storage/*StorageProvider.ts`)가 있고, 매니저는 어느 것인지 모른다.
  - `IModelManager.getModel(modelKey)`: `modelName` 채움에만 쓴다(R-03).
  - 시계: `Date.now()`, id: `uuid` v4.
  - 호출자: UI 합성 함수(`usePromptOptimizer.ts`, `useBasicWorkspaceLogic.ts` 등 이미지·컨텍스트 워크스페이스 포함 다수). 데스크톱은 렌더러가 `ElectronHistoryManagerProxy`(같은 인터페이스, IPC)로 부르고 실제 매니저는 메인 프로세스에서 돈다(`electron-proxy.ts`, `useAppInitializer.ts:147` — 프록시 선택 조건은 읽지 않음). MCP 서버도 매니저를 만들지만(`core-services.ts:88`) 호출 지점은 이 스펙에서 확인하지 않았다.
- 소유 상태·부작용: 저장소의 `prompt_history` 키 값 하나. 이 기능은 평가 점수를 소유하지 않는다(R-10).

### 1.3 인터페이스와 데이터 의미 [필수]

**PromptRecord (버전 1건)** — 필드는 C-01.

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `id` | string | 기록 id. 호출자가 만든다(UI는 uuid v4). 전체 기록에서 유일해야 한다(R-03). `addIteration`은 매니저가 uuid v4로 만든다. |
| `originalPrompt` | string | 그 버전을 만들 때 호출자가 넘긴 "원본 프롬프트". 체인 루트의 원본으로 고정되지 않고 버전마다 호출자가 넘긴 값이다(R-09). 빈 문자열 불가 |
| `optimizedPrompt` | string | 그 버전의 결과 프롬프트. 빈 문자열 불가 |
| `type` | `PromptRecordType`(13개 문자열) | `createNewChain`은 호출자 값, `addIteration`은 항상 `'iterate'`(R-02) |
| `chainId` | string | 소속 체인. 체인은 별도 레코드 없이 같은 `chainId`를 가진 기록들의 집합이다 |
| `version` | int | 체인 안 번호. 저장되는 첫 기록이 1. 0은 저장되지 않는다(R-09) |
| `previousId` | string? | 직전(=그때의 최고) 버전의 `id`. v1은 없음 |
| `timestamp` | int(ms epoch) | `createNewChain`은 호출자 값 또는 현재 시각, `addIteration`은 현재 시각 |
| `modelKey` | string | 이 버전을 만든 최적화·개선 모델 key. 테스트 대상 모델이 아니다(R-09) |
| `modelName` | string? | 저장 시점에 모델 관리자에서 조회한 표시 이름. 못 구하면 없음(R-03) |
| `templateId` | string | 사용한 템플릿 id. 반복 개선이면 iterate 템플릿 id. 수동 편집이면 현재 기록 값 또는 `'local-edit'` |
| `iterationNote` | string? | 반복 개선의 요구사항 문자열, 수동 편집이면 `'Manual edit'`/`'Direct fix'` |
| `metadata` | object? | 열린 맵. UI가 넣는 키는 R-09 |

**PromptRecordChain**(조회 결과, 저장되지 않는 파생 값): `chainId`, `rootRecord`(version 1), `currentRecord`(최고 version), `versions`(version 오름차순 전체). 호출마다 새로 읽어 만든 사본이다(저장소 문자열을 매번 `JSON.parse`).

**연산** (`IHistoryManager`, C-02 / 구현 C-05~C-09)

| 연산 | 입력 → 출력 | 비고 |
|---|---|---|
| `createNewChain(params)` | `params`: PromptRecord에서 `chainId`·`version`·`previousId`를 뺀 것(`id`는 호출자 제공) → 체인 | R-01 |
| `addIteration(params)` | `{chainId, originalPrompt, optimizedPrompt, modelKey, templateId, iterationNote?, metadata?}` → 체인 | R-02 |
| `addRecord(record)` | 완성된 기록 → void | 저수준. 검증·유일성·개수 제한을 여기서 한다(R-03, R-04) |
| `getRecords()` | → 저장 순서 그대로의 전체 기록 | 정렬하지 않는다 |
| `getRecord(id)` | → 기록 | 없으면 `RecordNotFoundError` |
| `getChain(chainId)` / `getAllChains()` / `getIterationChain(recordId)` | | R-05 |
| `deleteRecord(id)` / `deleteChain(chainId)` / `clearHistory()` | | R-06 |

오류 클래스(`errors.ts`)는 `HistoryError`(code, params) 계열이고 코드는 `error.history.{not_found,chain,record_not_found,storage,validation}`(`error-codes.ts:37-43`). 이 스펙에서 쓰는 것: `RecordNotFoundError`(record_not_found), `RecordValidationError`(validation), `HistoryStorageError`(storage; read/write/delete 구분), `HistoryError(CHAIN_ERROR)`(루트 없음).

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `createNewChain(params)` | `chainId`=새 uuid v4, `version`=1, `previousId`=없음, `timestamp`=`params.timestamp`가 falsy면 현재 시각. 나머지 필드는 `params` 그대로(`id`·`type`·`modelKey`·`templateId`·`metadata` 포함). `addRecord`로 저장한 뒤 `getChain`을 반환 | 코드 확인 |
| R-02 | `addIteration(params)` | 먼저 `getChain(params.chainId)`로 체인 존재를 확인(없으면 `RecordNotFoundError`, 루트 없으면 CHAIN_ERROR). 새 기록: `id`=새 uuid, `type`=항상 `'iterate'`(입력으로 받지 않음), `version`=**체인 최고 version+1**, `previousId`=**체인 최고 버전의 id**, `timestamp`=현재 시각, `originalPrompt`·`optimizedPrompt`·`modelKey`·`templateId`·`iterationNote`·`metadata`는 입력 그대로. 저장 후 `getChain` 반환. 호출자가 "현재 보고 있는 버전"이 최고가 아니어도 부모는 항상 최고 버전이다(분기 없음, 한 줄짜리 선형 체인) | 코드 확인 |
| R-03 | `addRecord(record)` | (1) `id`·`originalPrompt`·`optimizedPrompt`·`type`·`chainId`가 falsy이거나 `version`이 undefined면 `RecordValidationError`(오류 문자열 목록 포함). 즉 빈 문자열 프롬프트는 거부된다. `timestamp`·`modelKey`·`templateId`는 이 단계에서 검사하지 않는다. (2) `modelName`이 없고 `modelKey`가 있으면 `modelManager.getModel`로 이름을 조회해 **입력 객체에 직접 대입**한다(실패·없음이면 undefined). (3) 같은 `id`가 이미 있으면 `HistoryError(VALIDATION_ERROR)`. (4) 위 오류 외의 저장소 예외는 `HistoryStorageError`(read/write)로 바뀌어 던져진다. 비고: 가져오기용 `validateData`는 추가로 `timestamp`(number)·`modelKey`·`templateId`(string)를 요구한다 | 코드 확인 |
| R-04 | 기록 추가 | 새 기록을 배열 **맨 앞**에 붙이고 `slice(0, 50)`으로 **전체 기록 수를 50건**으로 제한한다. 한도는 체인별이 아니라 전체 합계이고 상수 `maxRecords = 50`(설정 불가). 초과분은 배열 뒤쪽, 즉 가장 먼저 추가된 기록부터 사라진다. 체인 안에서는 v1이 가장 먼저 추가되므로 오래된 체인의 낮은 버전부터 잘리고, 체인의 v1이 사라지면 그 체인은 R-05의 "루트 없음" 상태가 된다 | 코드 확인 |
| R-05 | 조회 | `getChain`: `chainId`로 거른 기록을 version 오름차순 정렬. 0건이면 `RecordNotFoundError`. `version===1` 기록이 없으면 `HistoryError(CHAIN_ERROR)`. `rootRecord`=version 1, `currentRecord`=정렬 마지막. `getAllChains`: `chainId`로 묶어 각각 같은 방식으로 만들되 **v1이 없는 체인은 조용히 건너뛴다**, 결과는 `currentRecord.timestamp` 내림차순. `getIterationChain(recordId)`: `previousId`를 따라 올라가며 앞에 붙이는 방식으로 오래된 것부터 반환, 없는 id를 만나면 거기서 멈춤(오류 없음, 시작 id가 없으면 빈 배열). `getRecords`는 저장 순서(최신 추가가 앞) 그대로이고, 저장 데이터가 없으면 빈 배열. 읽기 실패는 `HistoryStorageError(read)` | 코드 확인 |
| R-06 | 삭제 | `deleteRecord(id)`: 해당 기록 1건만 제거(없으면 `RecordNotFoundError`). 나머지 기록의 `previousId`·`version`은 고치지 않으므로 가운데 버전을 지우면 부모 링크가 끊기고 번호에 빈 틈이 생긴다. `deleteChain(chainId)`: 그 `chainId` 기록을 모두 제거, 하나도 없으면 `RecordNotFoundError`. `clearHistory()`: 키를 삭제. 저장 실패는 `HistoryStorageError(delete)`. **UI의 체인 삭제(`handleDeleteChain`)는 `deleteChain`이 아니라 체인의 각 버전에 `deleteRecord`를 반복 호출한다** | 코드 확인 |
| R-07 | 저장소 접점 | 값은 키 `prompt_history` 하나에 `PromptRecord[]`의 JSON 문자열이다. `addRecord`만 `StorageAdapter.updateData(key, modifier)`를 쓴다: 기반 provider에 `updateData`가 있으면 그것을 쓰고, 없으면 키별 비동기 잠금(30초 타임아웃) 아래 읽기→modifier→쓰기를 한다. `deleteRecord`·`deleteChain`은 `getItem`/`setItem`(`saveToStorage`)으로 읽고 고쳐 쓰며 잠금·`updateData`를 쓰지 않는다. `addIteration`의 "최고 버전 읽기"와 저장 사이도 원자적이지 않다 | 코드 확인 (경쟁 상황에서의 결과는 추론) |
| R-08 | 저장 위치가 아니라 호출자 경계 | 서비스(`PromptService.optimizePrompt`/`iteratePrompt` 등)는 기록을 쓰지 않는다. 서비스 코드 주석이 "저장은 UI층의 historyManager.createNewChain/addIteration"이라고 명시한다. UI는 스트림 완료 콜백에서 호출하고, 성공하면 반환 체인으로 `currentChainId`·`currentVersions`·`currentVersionId`를 갱신한다. 호출이 실패하면 경고 토스트만 띄우고 화면의 결과는 유지되며 기록은 남지 않는다. 체인이 아직 없는 상태에서 반복 개선·수동 편집이 일어나면 `addIteration`이 아니라 `createNewChain`으로 새 체인을 만든다 | 코드 확인 |
| R-09 | UI가 채우는 값(호출자 계약) | 최적화: `createNewChain({id: uuid, originalPrompt: 사용자 프롬프트, optimizedPrompt: 결과, type: optimize/userOptimize(+컨텍스트 모드는 해당 type), modelKey: 최적화 모델, templateId: 선택 템플릿, timestamp: 현재, metadata})`. 반복 개선: `addIteration({chainId, originalPrompt: 호출자가 넘긴 값, optimizedPrompt: 새 결과, iterationNote: 요구사항 입력, modelKey: 최적화 모델, templateId: iterate 템플릿 id, metadata})`. 수동 편집·패치 적용도 `addIteration`을 쓰며 `iterationNote`는 입력 또는 `'Manual edit'`/`'Direct fix'`, `modelKey`·`templateId`는 현재 선택 버전의 값을 이어받고 없으면 `'local-edit'`, `metadata.localEdit=true`·`localEditSource`(`'manual'` 기본). `metadata`에 들어가는 키(UI가 정한 것, 매니저는 검사하지 않음): `optimizationMode`, `functionMode`, `hasAdvancedContext`·`variableCount`·`messageCount`·`conversationSnapshot[]`(컨텍스트 모드), `localEdit`, `localEditSource`, `assetBinding`({assetId, versionId?, status}), `origin`({kind, id?, metadata?}). `handleAnalyze`가 만드는 "V0"는 version 0의 가상 기록으로 메모리에만 있고 저장되지 않는다. 버전 전환(`handleSwitchVersion`)은 UI 상태만 바꾸고 저장하지 않는다 | 코드 확인 |
| R-10 | 평가 점수 | **기록(`PromptRecord`)·체인·`metadata` 키 어디에도 점수나 평가 결과 필드가 없다**(`history/` 아래에서 score·evaluation 문자열 검색 결과 없음). 평가 결과는 별도로 세션 저장소의 `PersistedEvaluationResults`(`result`: 키→`EvaluationResponse`, `compare`, `prompt-only`, `prompt-iterate`)에 워크스페이스당 최신값만 들어가고, `result`의 키는 테스트 열 id(variantId)다. 버전 id·`chainId`로 묶이지 않는다. 다만 `metadata`가 열린 맵이라 점수를 넣어도 매니저가 거부하지 않는다 | 코드 확인 |

- 불변식: 저장된 모든 기록은 id가 유일하고 `originalPrompt`·`optimizedPrompt`가 비어 있지 않다(R-03). `addIteration`으로 만든 기록은 `type='iterate'`, `version`≥2이고 `previousId`가 있다(R-02). **그 외는 보장되지 않는다**: 체인에 v1이 항상 있다는 것(R-04, R-06), 버전 번호가 연속·유일하다는 것(R-06, R-07), `previousId`가 가리키는 기록이 존재한다는 것(R-06), 같은 체인의 `originalPrompt`가 같다는 것(R-09).
- 미결정: 없음
- 확인 한계: 실행·테스트 실행을 하지 않았다. 50건 한도가 화면에서 어떻게 보이는지(오래된 체인이 사라진 것으로 표시되는지, 경고가 있는지)는 UI를 읽지 않았다. 기반 provider(Dexie·파일 등)의 `updateData` 원자성은 provider 구현을 읽지 않아 매니저가 "있으면 위임한다"는 사실만 확인했다. 원본 테스트(`packages/core/tests/unit/history/manager.test.ts`, `import-export.test.ts`)는 파일명·사례명 검색까지만 했고 사례는 열지 않았다. 데스크톱 IPC 경로와 MCP 쪽 호출 여부는 확인하지 않았다. UI 호출자는 대표 2개(`usePromptOptimizer.ts`, `useBasicWorkspaceLogic.ts`)만 읽었고, 이미지·컨텍스트 워크스페이스의 호출은 같은 두 연산이라는 것까지만 검색으로 확인했다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/core/src/services/history/types.ts:6-19` `PromptRecordType`, `:24-68` `PromptRecord`, `:73-78` `PromptRecordChain` | 기록 필드 전체와 `type` 13개 값, 체인 파생 구조 | R-01, R-02, R-05, R-09 |
| C-02 | `packages/core/src/services/history/types.ts:85-116` `IHistoryManager` | 연산 시그니처. `addIteration` 입력에 `type`·`id`가 없음 | R-01, R-02 |
| C-03 | `packages/core/src/services/history/manager.ts:16` `maxRecords`, `:46-87` `addRecord`, `:190-203` `validateRecord` | 한도 50, 앞에 추가·`slice`, 유일성·필수 검사, `modelName` 조회, 오류 변환 | R-03, R-04 |
| C-04 | `packages/core/src/services/storage/types.ts:1-21` `IStorageProvider`, `packages/core/src/services/storage/adapter.ts:33-57` `updateData`, `:103-139` `acquireLock` | 저장소 계약(문자열 get/set/remove/clearAll, `updateData`, `batchUpdate`), 잠금 대체 구현과 30초 타임아웃 | R-07 |
| C-05 | `packages/core/src/services/history/manager.ts:210-228` `createNewChain` | 새 체인 생성 규칙 | R-01 |
| C-06 | `packages/core/src/services/history/manager.ts:235-271` `addIteration` | 버전·부모·type 부여 규칙 | R-02 |
| C-07 | `packages/core/src/services/history/manager.ts:278-317` `getChain`, `:323-362` `getAllChains`, `:151-165` `getIterationChain` | 정렬·루트 판정·루트 없는 체인 처리·체인 순서 | R-05 |
| C-08 | `packages/core/src/services/history/manager.ts:127-144` `deleteRecord`, `:368-377` `deleteChain`, `:170-176` `clearHistory`, `:182-184` `saveToStorage` | 삭제 연산과 비원자적 저장 | R-06, R-07 |
| C-09 | `packages/core/src/constants/storage-keys.ts:13` `PROMPT_HISTORY` | 저장 키 `prompt_history` | R-07 |
| C-10 | `packages/ui/src/composables/prompt/usePromptOptimizer.ts:165-195`, `:395-410`, `:440-495` | UI가 기록을 만드는 대표 3곳: 최적화 직후 `createNewChain`, 반복 개선 직후 `addIteration`, 수동 편집·패치의 `addIteration`(체인 없으면 `createNewChain`) | R-08, R-09 |
| C-11 | `packages/ui/src/composables/workspaces/useBasicWorkspaceLogic.ts:340-370`, `:440-475` | 같은 호출의 기본 모드 워크스페이스 버전(체인 id 유무로 `addIteration`/`createNewChain` 선택, 세션 저장소에 `chainId`·`versionId` 반영) | R-08, R-09 |
| C-12 | `packages/ui/src/composables/prompt/usePromptHistory.ts:93-115` `handleDeleteChain` | UI의 체인 삭제는 버전별 `deleteRecord` 반복 | R-06 |
| C-13 | `packages/ui/src/utils/history-source-binding.ts:58-79` | `metadata`에 `assetBinding`·`origin`을 합치는 규칙 | R-09 |
| C-14 | `packages/ui/src/types/evaluation.ts:10-15` `PersistedEvaluationResults` | 평가 결과가 기록이 아니라 세션 쪽 구조에 있다는 증거 | R-10 |
| C-15 | `packages/core/src/services/prompt/service.ts:161`, `:365`, `:580`, `:820`, `:1085` (주석) | 서비스가 히스토리를 저장하지 않고 UI에 맡긴다는 명시 | R-08 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 저장소는 메모리 provider, 모델 관리자는 `getModel`이 이름을 돌려주는 대체물로 가정하며, 따라서 실제 Dexie·파일 provider의 원자성은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 빈 저장소에서 `createNewChain({id:"a", originalPrompt:"p", optimizedPrompt:"q", type:"optimize", modelKey:"m", templateId:"t", timestamp:1000})` | `versions` 길이 1, `rootRecord`와 `currentRecord`가 같은 기록, `version`=1, `previousId` 없음, `timestamp`=1000, `chainId`는 uuid 형식 |
| T-02 | R-01 | 위와 같되 `timestamp: 0` | `timestamp`는 현재 시각(0이 아님) |
| T-03 | R-02 | T-01 체인에 `addIteration`을 2번(`iterationNote:"n1"`, `"n2"`) | `versions`의 version은 [1,2,3], v2.previousId=v1.id, v3.previousId=v2.id, v2·v3의 `type`='iterate', `currentRecord`=v3 |
| T-04 | R-02 | v1~v3 체인이 있고 UI가 v1을 보고 있는 상태에서 `addIteration` | 새 기록은 version 4, `previousId`=v3.id (v1 아님) |
| T-05 | R-02 | 없는 `chainId`로 `addIteration` | `RecordNotFoundError`, 저장소 변화 없음 |
| T-06 | R-03 | `addRecord`에 `originalPrompt: ""` | `RecordValidationError`, 저장소 변화 없음 |
| T-07 | R-03 | 이미 있는 `id`로 `addRecord` | `HistoryError`(code `error.history.validation`), 저장소 변화 없음 |
| T-08 | R-03 | `modelName` 없이 `modelKey:"m"`로 추가, 모델 관리자가 `getModel("m")`에서 `{name:"M"}`을 돌려줌 / 던짐 | 저장된 기록의 `modelName`이 "M" / 없음(추가 자체는 성공) |
| T-09 | R-04, R-05 | 체인 A를 3버전으로 만들고, 서로 다른 체인 48개(각 1기록)를 이어서 추가(총 51건) | 가장 먼저 추가된 A.v1이 사라진다. `getRecords` 길이 50, `getChain(A)`는 CHAIN_ERROR, `getAllChains`에는 A가 없음(A.v2·v3 기록은 저장소에 남아 있음), `addIteration(A)`는 CHAIN_ERROR |
| T-10 | R-05 | 체인 X(최신 기록 시각 100), 체인 Y(최신 기록 시각 200) | `getAllChains`는 [Y, X] 순서 |
| T-11 | R-05, R-06 | v1~v3 체인에서 v2를 `deleteRecord`한 뒤 `getIterationChain(v3.id)`와 `getChain` | `getIterationChain`은 [v3] 하나만(v3.previousId가 가리키는 v2가 없어 멈춤), `getChain.versions`는 version [1,3] |
| T-12 | R-06 | 존재하지 않는 `chainId`로 `deleteChain` / 존재하는 체인으로 `deleteChain` | `RecordNotFoundError` / 그 체인의 모든 기록 제거, 다른 체인은 그대로 |
| T-13 | R-07 | 서로 다른 두 체인을 `Promise.all`로 `createNewChain` | `updateData`(잠금) 덕에 두 기록이 모두 남는다(기반 provider가 `updateData`를 안 가진 경우). 한 체인에 `addIteration`을 동시에 두 번 하는 경우의 결과(같은 version이 두 번 생길 수 있음)는 원본에서 막지 않으며 이 사례로 기대값을 정하지 않는다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-05 `createNewChain` (`manager.ts:210-228`) | 코드 읽기 |
| R-02 | C-06 `addIteration` (`manager.ts:235-271`: `:257` `version: chain.currentRecord.version + 1`, `:258` `previousId: chain.currentRecord.id`, `:256` `type: 'iterate'`), C-02 | 코드 읽기. `currentRecord`는 `getChain`의 정렬 마지막(`manager.ts:303`)이라 "최고 버전" |
| R-03 | C-03 (`manager.ts:46-87`, `:190-203`) | 코드 읽기. `modelName` 대입이 입력 객체 변경임은 `:51-53`. 가져오기 비고는 `manager.ts:442-460` `validateData`(범위 밖이지만 필수 필드 대조용으로만 읽음) |
| R-04 | C-03 (`manager.ts:16`, `:71-74`) | 코드 읽기. "먼저 추가된 쪽이 잘린다"는 `[record, ...records]`(앞에 붙임)와 `slice(0,50)`의 조합으로 도출. T-09는 이 도출 위에서 구성한 사례이며 실행하지 않았다 |
| R-05 | C-07 (`manager.ts:278-317`, `:323-362`, `:151-165`), `:100` 주석("排序逻辑由调用者根据需求处理") | 코드 읽기 |
| R-06 | C-08 (`manager.ts:127-144`, `:368-377`, `:170-176`), C-12 (`usePromptHistory.ts:93-115`) | 코드 읽기. UI 체인 삭제가 `deleteRecord` 반복임은 `usePromptHistory.ts`에서 확인했고, `git grep deleteChain -- ui/src`에서 `historyManager.deleteChain`을 부르는 곳은 서비스 래핑(`useAppInitializer.ts:391`)뿐이었다 |
| R-07 | C-04, C-08, C-09 (`adapter.ts:33-57` 잠금 대체, `storage-keys.ts:13`) | 코드 읽기. 동시 호출 결과는 추론. provider 구현은 `implements IStorageProvider` 목록(`dexieStorageProvider.ts`, `fileStorageProvider.ts`, `localStorageProvider.ts`, `memoryStorageProvider.ts`)까지만 확인 |
| R-08 | C-15 (`prompt/service.ts` 주석 5곳), C-10 (`usePromptOptimizer.ts:165-195` 최적화 후 `createNewChain`과 `catch → toast.warning`, `:395-410` 반복 후 `addIteration`과 `catch → toast.warning`, `:440-495`), C-11 (`useBasicWorkspaceLogic.ts:340-370` 체인 id 없으면 `createNewChain`) | 코드 읽기. 대표 2파일만. `git grep`으로 `addIteration`·`createNewChain`의 호출 위치 전체(이미지 3개 워크스페이스, `useContextUserOptimization.ts`, `useConversationOptimization.ts`)를 목록화했으나 본문은 읽지 않음 |
| R-09 | C-10, C-11, C-13, `usePromptOptimizer.ts:80-81` `withSourceMetadata`, `:513-535` `handleAnalyze`(가상 V0, `version: 0`, "不写入历史记录" 주석), `:500-507` `handleSwitchVersion` | 코드 읽기. `metadata` 키 목록은 대표 호출에서 쓰는 키만이며 컨텍스트·대화 모드(`useConversationOptimization.ts`의 `conversationSnapshot.appliedVersion` 등)는 일부만 보았다 |
| R-10 | `history/` 디렉터리 `git grep -i 'score\|evaluation'` 결과 없음, C-14 (`types/evaluation.ts:10-15`), `useEvaluationHandler.ts:533` `clearResult('result', variantId)` | 코드 읽기와 검색. 세션 쪽 `result` 키가 variantId라는 것은 `:533` 한 곳 호출로 확인했고, 평가 결과를 저장하는 모든 경로를 따라가지는 않았다 |
| T-01~T-13 | 위 각 R-ID의 근거 | 구현에서 도출한 기대값, 실행하지 않음 |

문서와 구현의 차이: 없음(이 기능을 설명하는 README·`docs/`는 읽지 않았다). 코드 주석과 구현은 일치한다. 한 가지 눈에 띄는 불일치: `getRecord` 주석은 "null if not found"이지만 구현은 `RecordNotFoundError`를 던진다(`manager.ts:107-121`) — 구현을 사실로 썼다.

### 2.2 코드 읽는 순서 [선택]
`types.ts`(필드·인터페이스) → `manager.ts`의 `addRecord`(저장 규칙) → `createNewChain`/`addIteration` → `getChain`/`getAllChains` → `storage/adapter.ts` `updateData` → UI 호출 `usePromptOptimizer.ts`의 `onComplete` 두 곳. 원본의 구현 전략은 "체인 엔티티 없이 평평한 기록 배열 하나를 통째로 JSON으로 읽고 쓰고, 체인은 읽을 때마다 `chainId`로 묶어 재구성"이다. 캐시·인덱스는 없다.

## 적용 메모 [선택]
목적: 스킬(SKILL.md) v1→v2→v3 개선 과정과 각 점수를 기록할 때 이 모델에서 가져올 것.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-02, R-05 | 가져올 만한 것: `chainId`(스킬 하나의 개선 계보) + `version`(1부터) + `previousId`(부모) + `timestamp` + `iterationNote`(왜 고쳤나) + `templateId`(개선에 쓴 메타 프롬프트) + `modelKey`(개선을 수행한 모델). 체인을 별도 엔티티 없이 같은 `chainId`의 기록 모음으로 두고 읽을 때 재구성하는 방식도 단순하다 | 필요한 필드가 이미 갖춰져 있다 | 필드 이름·의미는 그대로 써도 된다. `originalPrompt`·`optimizedPrompt` 이름은 "입력 스킬 본문/결과 스킬 본문" 의미로 읽고, 스킬 파일의 경로·해시는 `metadata`에 둔다 |
| R-10 | 점수 필드를 버전에 직접 붙인다. 원본에는 없으므로 새로 설계해야 한다. 버전 id(또는 `chainId`+`version`)를 키로 `{평가 모델, 테스트 대상 모델, 케이스 id, 점수, 평가 응답 원문, 시각}` 목록을 둔다 | 원본의 평가 결과는 세션 안에서 테스트 열 id 키로 최신값만 보관돼 버전별 점수 이력이 안 남는다. 또 `PromptRecord.modelKey`는 개선 수행 모델이지 테스트 대상 모델이 아니다(R-09) — "모델 적합도"를 기록하려면 대상 모델을 따로 가져야 한다 | 새 데이터: 평가 기록(버전 id 외래키). 기록 1건이 여러 모델×케이스 점수를 가진다 |
| R-04 | 전체 50건 한도·잘리는 쪽을 그대로 가져오지 않는다 | 한도가 체인 단위가 아니라 전체 합계이고 v1부터 사라져 체인이 깨진다(루트 없음). 스킬 개선 이력은 보존이 목적이다 | 한도 없음 또는 체인 단위 보존 정책 |
| R-02 | 부모를 "최고 버전"으로 고정하는 규칙은 분기(같은 v1에서 갈라진 두 시도)를 못 쓴다. 필요하면 `parentId`를 입력으로 받는다 | 원본은 선형 체인만 보장 | `addIteration` 입력에 `parentId?`, 번호는 체인 단위 최대+1 유지 |
| R-02, R-07 | 버전 번호 부여와 저장을 한 트랜잭션(또는 잠금)으로 묶는다. 삭제 시 부모 링크 보정 또는 삭제 금지 | 원본은 읽기-쓰기가 분리돼 동시성·중간 삭제에서 번호·부모가 어긋날 수 있다 | `addIteration`의 읽기·쓰기 원자화, 삭제 정책 추가 |
| R-02 | `type`을 입력으로 받는다 | `addIteration`은 항상 `'iterate'`로 고정 | 필요할 때만 |
