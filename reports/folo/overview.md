# folo Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/RSSNext/folo`
- **분석 Commit SHA**: `44f0e5df06eba774afe1f1aea30d90a742da5dec`
- **분석 일자**: `2026-09-14`
- **작업트리 상태**: `clean`
- **분석 목적**: 학습 + 설계 참고 (RSSHub와 짝을 이루는 "AI RSS 리더" 클라이언트의 구조 이해). 1차 분석 범위는 모노레포 전체 구조(apps/*·packages/* 의존 관계) — 사용자 확인.

---

## 2. 프로젝트 개요

Folo(구 Follow)는 "Follow everything in one place"를 표방하는 RSS/콘텐츠 리더다. pnpm+Turborepo 모노레포로 `apps/desktop`(Electron), `apps/mobile`(React Native), `apps/landing`, `apps/ota`(자체 업데이트 서버), `apps/ssr`, `apps/cli`를 포함하고, 공통 로직은 `packages/internal/*`(database, store, hooks, models 등)에 있다.

**핵심 확인 사항(코드 확인)**: 이 레포는 **클라이언트 전용**이다 — `apps/desktop/layer/renderer/src/lib/api-client.ts`가 `env.VITE_API_URL`이라는 외부 백엔드 API를 호출하는 구조이고, 실제 피드 크롤링/AI 요약/DB 서버 로직은 이 레포에 없다(별도 비공개 백엔드로 추정, 미확인). RSSHub처럼 "서버+라우트"를 통째로 볼 수 있는 레포가 아니라 "그 백엔드를 소비하는 멀티플랫폼 클라이언트 모음"이라는 점이 RSSHub 분석과의 가장 큰 구조적 차이다.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도 및 대표 실행 흐름 다이어그램입니다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 모노레포 전체 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | apps/* + packages/* 의존 관계, client-sdk를 통한 외부 백엔드 경계 (commit `44f0e5df` 기준 코드 확인) |
| 공유 패키지 상세 구조도 | [packages.json](./diagrams/packages.json) | [packages.html](./diagrams/packages.html) | `packages/internal/*` 내부의 실제 의존 그래프 — shared가 data track(models→database→store)과 UI track(hooks→components)으로 갈라지는 지점까지 확대 |

### 그림 읽는 가이드
1. **최상단**: `Foundation packages`(types/configs/utils/logger) → `Domain packages`(shared/models/hooks/UI) → `Data layer`(database+store)로 이어지는 **하나의 공통 의존 스택**이 desktop/mobile/ssr 세 앱에 동일하게 재사용된다.
2. **오른쪽 열**: `client-sdk`(외부 npm 패키지)가 `Backend API`(이 레포에 없음, `VITE_API_URL`)를 호출하고, `Domain packages`도 이 client-sdk를 통해 타입 있는 API를 쓴다 — "백엔드가 이 레포 밖에 있다"는 사실이 이 그림의 핵심.
3. **Electron만 특이**: `desktop: main`(Electron 메인 프로세스)과 `desktop: renderer`(실제 UI)가 별도 패키지로 나뉘어 있고 IPC 타입으로 연결된다. `landing`/`ota`는 내부 패키지 의존이 전혀 없는 완전 독립 배포 단위.
4. **1차 지도라 단순화한 부분**: `Domain packages`에 실제로는 `shared`/`models`/`hooks`/`components` 4개 패키지가 합쳐져 있고, `desktop: main`이 client-sdk/readability를 직접 쓰는 화살표는 카드 설명으로만 남기고 그림에서 뺐다 — 미확인 영역.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

*(아직 없음 — 그림을 보고 궁금한 부분이 생기면 이 표에 추가)*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/folo.md](../../wiki/projects/folo.md)
