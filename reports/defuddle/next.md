---
sha: "556d74e8c8fd68c49912d4b11a4ae9ec04d7b2b5"
created: 2026-10-23
updated: 2026-10-23
---

# Next Session Plan: defuddle

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 레포 재clone 및 현재 HEAD(`556d74e`) 메타데이터 갱신
- [x] 이전 캡처(`9db7260`) 대비 변경점 비교(`git diff --stat`)
- [x] 기능 지도 작성 (핵심 8행 + 부속 2행 + 공유 계약 1건)
- [x] archify 전체 모듈 구조도 1개 (finalize 자동 검증 통과)

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] README Options 표에 없는 `removeContentPatterns` 옵션의 전체 동작(코드에는 있음, 문서화 안 됨)
- [ ] 24개 사이트별 추출기 각각의 세부 DOM 파싱 로직(지도 단계에서는 등록 목록만 확인)
- [ ] website API 키·Durable Object 과금 흐름의 실제 운영 동작(동시성, 장애 복구) — 코드만 읽었고 실행 검증 없음

---

## 3. 기능 스펙 후보

2026-10-23 세션에서 사용자에게 스펙 범위를 물었고, "지도만 유지(스펙 보류)"로 답해 핵심 8행 모두 보류됐다. `defuddle.md 웹 서비스`, `API 키 발급·과금`(부속 2행)은 "제외"로 확정(라이브러리 본체와 별개인 호스팅 서비스).

| 기능 | 근거 | 상태 |
|---|---|---|
| 핵심 추출 파이프라인 외 7개 (overview 2절 "핵심" 행 전부) | [overview.md 2절 기능 지도](./overview.md#기능-지도) | 보류 — 다음 세션에서 기능 스펙을 요청받으면 2장 6번대로 지도 요약을 다시 보여주고 범위를 확정한 뒤 4장 시작 |
| defuddle.md 웹 서비스 / API 키·과금 | [overview.md 2절 기능 지도](./overview.md#기능-지도) | 제외 확정(사용자 제외) — 다시 묻지 않음 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

범위가 승인되면 선행 관계 순서대로 쓴다: 핵심 추출 파이프라인 → 사이트별 추출기 패밀리 → HTML 표준화 → 메타데이터 추출 → (마크다운 변환, 라이브러리 임베딩 진입점, CLI, 프론트매터 빌더) → (defuddle.md 웹 서비스, API 키·과금).

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/defuddle.ts` | `Defuddle.parse()`/`parseInternal()`/`_parseWithRetries()` | 재시도 단계 순서·종료 조건, R-ID 단위 규칙화 |
| `src/extractor-registry.ts`, `src/extractors/_base.ts` | `findExtractor`/`BaseExtractor` 계약 | 공통 계약(동기/비동기) 확정 후 패밀리 스펙 작성 |
| `src/standardize.ts` | `standardizeContent()` | elements/removals 호출 순서와 각 단계의 실패 전달 방식 |

---

## 5. 참고 사항 및 후속 제안

- `repos/defuddle`는 `.gitignore` 대상이라 세션마다 사라질 수 있다. 다음에 이 레포를 다시 볼 때는 5장 절차대로 fetch/pull부터 하고, 없으면 재clone 후 SHA를 비교한다.
- `artifacts/defuddle/github-metadata.json`은 이전 SHA(`9db7260`) 시점 그대로다(이번 세션에서 갱신 안 함). 필요해지면 다시 받는다.
- website(`defuddle.md`)는 독립 배포 단위(Cloudflare Worker, 자체 `package.json`/`wrangler.toml`)이므로 스펙 범위를 물을 때 "부속"으로 별도 확인한다.
