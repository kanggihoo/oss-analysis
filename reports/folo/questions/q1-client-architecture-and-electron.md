# [Q] Folo는 "숨겨진 SDK로 데이터만 보여주는 멀티플랫폼 대시보드"인가? 그리고 웹이 있는데 왜 Electron인가?

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `44f0e5df06eba774afe1f1aea30d90a742da5dec`
- **검증 수준**: 코드 확인 (일부 백엔드 구현 추정은 `추론`으로 표시)

---

## 1. 질문 및 결론

- **질문 1**: Folo는 내부에 숨겨진 SDK로 여러 플랫폼(Electron/웹/mac/Windows)에서 데이터를 보는 대시보드 같은 구조인가?
- **질문 2**: 웹을 이미 지원하는데도 굳이 Electron으로 데스크톱 앱을 만드는 이유는?
- **핵심 결론 1**: "하나의 호스팅 백엔드를 여러 클라이언트가 SDK로 소비한다"는 큰 그림은 맞다. 다만 (a) SDK는 숨겨진 게 아니라 **공개 npm 패키지**이고 숨겨진 건 백엔드 구현이며, (b) 각 플랫폼이 **로컬 SQLite DB를 직접 굴리는 offline-first 구조**라 단순 대시보드보다 훨씬 무겁다.
- **핵심 결론 2**: Electron은 "웹의 중복 구현"이 아니라 **같은 React 코드베이스(`@follow/web`)를 감싸는 껍데기**다. 추가로 얻는 건 브라우저가 원천적으로 못 하는 OS 권한들(트레이/독, 파일시스템 쓰기, 네트워크 프록시, 쿠키 소유, CLI 세션 공유, 자체 자동·핫 업데이트)이다.

---

## 2. 동작 설명

- 관련 다이어그램: [structure.html](../diagrams/structure.html), [packages.html](../diagrams/packages.html)

### (1) SDK는 숨겨진 게 아니라 공개 npm 패키지

`@follow-app/client-sdk@0.3.95`는 `pnpm-lock.yaml`에 sha512 integrity 해시와 함께 일반 레지스트리 의존성으로 잡혀 있다. 즉 **API의 타입/모양은 공개**되어 있고, 비공개인 것은 그 뒤의 **백엔드 구현**(크롤링·AI·DB 서버)이다.

흥미로운 단서: 이 SDK의 의존성에 `hono`와 `@folo-services/drizzle`이 들어 있다 → 백엔드도 Hono 기반이고 DB 스키마를 클라이언트와 공유하는 구조로 **추론**된다(백엔드 코드 미공개이므로 미확인).

호출부는 매우 얇다:

```ts
// apps/desktop/layer/renderer/src/lib/api-client.ts
export const followClient = new FollowClient({
  baseURL: env.VITE_API_URL,
  fetch: async (input, options = {}) => { /* Electron이면 IPC 프록시 */ },
})
```

### (2) 대시보드가 아니라 offline-first — 플랫폼마다 진짜 로컬 SQLite

`packages/internal/database`가 drizzle ORM 위에서 플랫폼별로 다른 SQLite 엔진을 쓴다. 스키마(`schemas/`)와 마이그레이터(`migrator.ts`)는 공유한다.

| 플랫폼 | 엔진 | 파일 |
|---|---|---|
| 데스크톱/웹 | wa-sqlite (WASM SQLite) + IndexedDB VFS | `src/db.desktop.ts` |
| 모바일 | expo-sqlite (네이티브) | `src/db.rn.ts` |

WASM SQLite를 고른 이유는 **브라우저와 Electron renderer 양쪽에서 같은 DB 코드가 돌아가야 하기 때문**으로 추론된다. 기사 본문 추출도 서버가 아니라 로컬에서 한다(`@follow-app/readability` = Mozilla Readability 패치본).

### (3) 플랫폼 구성: 클라이언트는 4개가 아니라 2개 코드베이스

- **React 코드베이스 1개** = `apps/desktop/layer/renderer` (패키지명이 다름 아닌 **`@follow/web`**) → 웹 + Electron 데스크톱(mac/Windows/Linux) 공용
- **React Native 코드베이스 1개** = `apps/mobile` → iOS/Android
- 둘 다 `packages/internal/*` 공유

즉 mac/Windows/Linux는 별개 클라이언트가 아니라 Electron 빌드 타깃일 뿐이다.

### (4) 그래서 왜 Electron인가 — 브라우저가 못 하는 것들

`apps/desktop/layer/main`(Electron 메인 프로세스)이 renderer에 IPC로 제공하는 기능들이 곧 Electron을 쓰는 이유다:

| 기능 | 코드 근거 | 브라우저로 가능한가 |
|---|---|---|
| 시스템 트레이 / macOS 독 배지 | `lib/tray.ts` (`new Tray`), `lib/dock.ts` | 불가 |
| Obsidian 볼트에 마크다운 파일 쓰기 | `ipc/services/integration.ts` → `fsp.writeFile(filePath, markdown)` | 불가(임의 경로 쓰기) |
| 네트워크 프록시 설정 | `lib/proxy.ts` → `session.defaultSession.setProxy()` | 불가 |
| 인증 쿠키를 메인 프로세스가 소유 + API 호출 IPC 프록시 | `lib/auth-cookies.ts`, `api-client.ts`의 `fetchWithElectronAuth` | 제한적(서드파티 쿠키/CORS 제약) |
| CLI(`apps/cli`)와 로그인 세션 공유 | `lib/cli-login-token.ts`, `lib/cli-session-sync.ts` | 불가 |
| 자체 자동 업데이트 + renderer 번들 핫 업데이트 | `updater/` (`hot-updater.ts`, `windows-updater.ts`) + `apps/ota` | 불필요/불가 |
| 네이티브 메뉴 | `menu.ts`, `ipc/services/menu.ts` | 불가 |

핵심은 **한계비용이 작다는 점**이다. renderer는 웹앱 그대로이므로 Electron을 위해 추가로 유지하는 건 `layer/main` 패키지 하나뿐이고, 그 대가로 위 OS 권한들을 얻는다.

---

### (5) 스택 정정: Hono는 데스크톱 앱과 무관하다

"Hono + RN + Electron으로 데스크톱 앱"이라는 정리는 사실과 다르다. 이 레포에서 `hono`를 의존성으로 갖는 패키지는 **`apps/ota`와 `apps/ssr` 두 개뿐**이다(전 package.json grep 확인). RN은 모바일 전용이라 데스크톱과 섞이지 않는다.

| 빌드 타깃 | 실제 스택 |
|---|---|
| 데스크톱(mac/Win/Linux) | Electron 껍데기 + React (`@follow/web` renderer) |
| 웹 | 위와 **동일한** React 코드 |
| 모바일(iOS/Android) | React Native |
| ssr, ota | Hono (이 레포 안의 작은 Node 서비스) |
| 실제 백엔드(`api.folo.is`) | 이 레포에 없음 |

### (6) SDK를 임의로 호출해도 되는가

- **기술적으로는 가능**: `@follow-app/client-sdk`는 공개 npm 패키지이고 호출부도 `new FollowClient({ baseURL })` 한 줄이다.
- **다만 인증이 필요**: better-auth 기반이라 대부분 엔드포인트가 세션 토큰을 요구한다(`signIn.email`/`magicLink`/소셜 로그인).
- **대상이 상용 서비스**: 기본 API URL이 `https://api.folo.is`(`packages/internal/shared/src/env.common.ts`)이고, `auth.ts`에 **Stripe 구독 플러그인**(`stripeClient({ subscription: true })`)이 붙어 있다 → 유료 플랜이 있는 실서비스.
- **AGPL은 서버 사용 권한을 주지 않는다**: 라이선스는 클라이언트 소스에 대한 것이고, 그들의 서버 이용은 ToS 영역이다. 본인 계정으로 본인이 쓰는 건 클라이언트가 하는 일과 동일하지만, 별도 서비스/봇을 만들어 돌리는 건 남의 인프라 무임승차라 약관 위반·계정 차단 리스크가 있다.
- **안정성 보장 없음**: 공개 API 문서가 없고 SDK 버전이 `0.3.95`로 핀 고정되어 있다 — 언제든 깨질 수 있다.
- **참고**: `apps/desktop/.env.example`에는 `VITE_API_URL=http://localhost:3000`이 들어 있어 자체 백엔드를 붙이는 것 자체는 상정되어 있으나, 그 백엔드 구현은 이 레포에 없다.

---

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| SDK 공개 여부 | `pnpm-lock.yaml` | `@follow-app/client-sdk@0.3.95` + sha512 | 레지스트리 의존성(비공개 아님) |
| SDK 의존성 단서 | `pnpm-lock.yaml` | `hono`, `@folo-services/drizzle` | 백엔드도 Hono/drizzle 추론 |
| API 호출부 | `apps/desktop/layer/renderer/src/lib/api-client.ts` | `FollowClient`, `fetchWithElectronAuth` | baseURL=`VITE_API_URL`, Electron은 IPC 프록시 |
| 로컬 DB(데스크톱/웹) | `packages/internal/database/src/db.desktop.ts` | `wa-sqlite`, `IDBMirrorVFS` | WASM SQLite + IndexedDB |
| 로컬 DB(모바일) | `packages/internal/database/src/db.rn.ts` | `drizzle-orm/expo-sqlite` | 네이티브 SQLite |
| 웹=데스크톱 renderer | `apps/desktop/layer/renderer/package.json` | `"name": "@follow/web"` | 같은 코드베이스 |
| 트레이 | `apps/desktop/layer/main/src/lib/tray.ts` | `new Tray`, `setContextMenu` | OS 트레이 |
| 파일시스템 | `apps/desktop/layer/main/src/ipc/services/integration.ts` | `fsp.writeFile` | Obsidian 노트 저장 |
| 프록시 | `apps/desktop/layer/main/src/lib/proxy.ts` | `session.defaultSession.setProxy` | 앱 레벨 프록시 |
| CLI 세션 공유 | `apps/desktop/layer/main/src/lib/cli-session-sync.ts` | — | `apps/cli`와 로그인 공유 |
| 업데이터 | `apps/desktop/layer/main/src/updater/` | `hot-updater.ts` | renderer 번들 핫 업데이트 |
| Hono 사용처 | `apps/ota/package.json`, `apps/ssr/package.json` | `"hono"` | 데스크톱 앱과 무관, 이 둘만 사용 |
| 기본 API URL | `packages/internal/shared/src/env.common.ts` | `API_URL: "https://api.folo.is"` | prod/dev/staging/local 분기 |
| 상용 서비스 근거 | `packages/internal/shared/src/auth.ts` | `stripeClient({ subscription: true })` | 유료 구독 플랜 존재 |

---

## 4. 검증 과정

- **수행한 작업**: 위 파일 직접 열람 + `grep`으로 `writeFile`/`setProxy`/`Tray`/`wa-sqlite`/`expo-sqlite` 사용처 확인. 빌드/실행은 하지 않음(의존성 미설치).
- **판단 근거**: Electron 전용 기능들은 모두 `apps/desktop/layer/main`에만 존재하고 renderer(웹 코드)에는 없다 → "웹으로는 불가능한 것만 main에 둔다"는 경계가 코드상 명확히 드러남.

---

## 5. 남은 질문

- [ ] 백엔드가 실제로 Hono/drizzle인지, 그리고 RSSHub 같은 크롤링 엔진을 자체적으로 돌리는지 (SDK 의존성 기반 추론 단계 — 검증 불가, 미공개)
- [ ] `store`(상태)와 `database`(로컬 SQLite) 사이의 동기화 전략: 언제 서버와 sync하고 충돌은 어떻게 푸는지
- [ ] 웹 버전은 로컬 SQLite(WASM)를 쓰는데 브라우저 저장소 용량 제한/초기화는 어떻게 다루는지
