---
title: Folo
created: 2026-09-14
updated: 2026-09-14
type: project
tags: [open-source, project, architecture, developer-tools, pattern]
sources: [repos/folo/package.json, repos/folo/pnpm-workspace.yaml, repos/folo/pnpm-lock.yaml, repos/folo/apps/desktop/layer/renderer/package.json, repos/folo/apps/desktop/layer/renderer/src/lib/api-client.ts, repos/folo/apps/desktop/layer/main/src/lib/tray.ts, repos/folo/apps/desktop/layer/main/src/lib/proxy.ts, repos/folo/apps/desktop/layer/main/src/ipc/services/integration.ts, repos/folo/packages/internal/database/src/db.desktop.ts, repos/folo/packages/internal/database/src/db.rn.ts, repos/folo/packages/internal/shared/src/env.common.ts, repos/folo/packages/internal/shared/src/auth.ts, reports/folo/overview.md, reports/folo/questions/q1-client-architecture-and-electron.md]
confidence: high
---

# Folo

Folo(구 Follow)는 RSS/콘텐츠 피드를 한 타임라인에서 읽는 멀티플랫폼 리더다. 이 페이지는 로컬 checkout `repos/folo/`(commit `44f0e5df06eba774afe1f1aea30d90a742da5dec`)의 source로 검증한 요약이며, 상세 근거는 [reports/folo/overview.md](../../reports/folo/overview.md)와 [q1 문서](../../reports/folo/questions/q1-client-architecture-and-electron.md)에 있다. 다이어그램은 복제하지 않고 링크한다: [structure.html](../../reports/folo/diagrams/structure.html), [packages.html](../../reports/folo/diagrams/packages.html).

## 한 줄 정의

**"피드를 만드는" 엔진이 아니라 "피드를 읽는" 클라이언트다** — 그리고 이 레포에 있는 건 클라이언트뿐이다. [[rsshub]]와 정확히 반대편에 서 있다.

> 이 페이지의 결론은 `repos/` 로컬 source 검증에 기반한다 ([[evidence-backed-analysis]]). reports/wiki 역할 분담은 [[workspace-boundaries]]를 따른다.

## Verification snapshot

- Repository: `https://github.com/RSSNext/folo`
- Local checkout: `repos/folo/`
- Verified commit: `44f0e5df06eba774afe1f1aea30d90a742da5dec`
- License: AGPL-3.0-only (단, 라이선스는 클라이언트 소스에만 적용되고 `api.folo.is` 서버 이용 권한과는 무관)

## 가장 중요한 구조적 사실: 클라이언트 전용 레포

실제 백엔드(피드 크롤링·AI 요약·계정·DB)는 이 레포에 **없다**. 모든 앱은 `@follow-app/client-sdk`라는 **공개 npm 패키지**를 통해 `https://api.folo.is`를 호출한다(`packages/internal/shared/src/env.common.ts`). 즉 공개된 것은 **API의 모양(타입)**이고 비공개인 것은 **백엔드 구현**이다.

- 호출부는 얇다: `new FollowClient({ baseURL: env.VITE_API_URL })` (`apps/desktop/layer/renderer/src/lib/api-client.ts`)
- 인증은 better-auth, 유료 플랜은 Stripe 구독 플러그인으로 붙어 있다 (`packages/internal/shared/src/auth.ts`)
- SDK의 의존성에 `hono`와 `@folo-services/drizzle`이 있어 백엔드도 Hono/drizzle 기반일 가능성이 높다 — **추론**(백엔드 미공개로 검증 불가)

## 빌드 타깃과 실제 스택

| 타깃 | 스택 | 비고 |
|---|---|---|
| 데스크톱(mac/Win/Linux) | Electron 껍데기 + React | renderer 패키지명이 **`@follow/web`** |
| 웹 | **위와 동일한** React 코드 | 코드베이스 재사용 |
| 모바일(iOS/Android) | React Native | `apps/mobile` |
| ssr, ota | Hono | 이 레포 안의 작은 Node 서비스 |

즉 클라이언트 코드베이스는 4개가 아니라 **2개**(React 웹/데스크톱 + RN 모바일)이고, 둘 다 `packages/internal/*`를 공유한다.

## 패키지 의존 구조

`shared`를 뿌리로 두 갈래로 갈라진다 ([packages.html](../../reports/folo/diagrams/packages.html) 참고):

- **Data track**: `models` → `database`(로컬 SQLite) → `store`(상태)
- **UI track**: `hooks` → `components`
- 외부 경계는 **`shared` 한 곳만** `client-sdk`를 직접 만진다 — 하위 패키지는 간접적으로만 API에 접근한다.

## 여기서 가져올 만한 것 (재사용 가치)

UI/UX보다 **구조 패턴**이 훨씬 값어치 있다. UI는 자체 디자인 시스템·Tailwind 설정에 깊게 묶여 있어 통째로 뜯어오기 어렵다.

1. **하나의 React 코드베이스로 웹 + Electron 데스크톱** — renderer가 곧 웹앱(`@follow/web`)이고, 브라우저가 못 하는 것만 `layer/main`에 두고 IPC로 노출한다. Electron 유지 비용이 `layer/main` 패키지 하나로 제한된다.
2. **스키마 하나 / 엔진 둘의 offline-first 로컬 DB** — drizzle ORM 위에서 데스크톱·웹은 wa-sqlite(WASM+IndexedDB VFS), 모바일은 expo-sqlite를 쓰고 `schemas/`와 `migrator.ts`는 공유한다. WASM SQLite 선택은 "브라우저와 Electron renderer가 같은 DB 코드를 돌려야 해서"로 추론된다.
3. **API 경계를 한 패키지로 좁히기** — `shared`만 SDK를 만지는 규칙. 백엔드가 바뀌어도 파급 범위가 한 패키지로 제한된다.
4. **타입 있는 API 클라이언트를 npm 패키지로 발행** — 백엔드와 클라이언트가 스키마/타입을 공유하는 방식. 직접 작은 백엔드를 만들 때도 그대로 쓸 만한 패턴이다.
5. **Electron 핫 업데이트(OTA)** — 앱스토어 심사 없이 renderer 번들만 교체하는 구조(`updater/hot-updater.ts` + `apps/ota`).

반대로 **가져올 수 없는 것**: 피드 수집·AI 요약 등 실제 데이터 파이프라인 전부(비공개). 그 영역은 [[rsshub]] 쪽에서 봐야 한다.

## 관련 페이지

- [[rsshub]] — 피드를 *만드는* 쪽. Folo와 정확히 상보 관계이며, README에서도 서로를 추천한다.
