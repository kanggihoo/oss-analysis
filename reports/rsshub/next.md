# Next Session Plan: rsshub

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`
- **작성/갱신 일자**: `2026-09-24`

---

## 1. 이번까지 확인한 범위

- [x] 계층 구조(entrypoint → app-bootstrap → registry → routes)와 분리 기준 — [Q1](./questions/q1-layered-architecture.md)
- [x] worker 실행 모델 / bootstrap 개념 / registry-routes 디스패치 / 사이트 문서화 방식 — [Q2](./questions/q2-worker-model-and-plugin-dispatch.md)
- [x] 지원 사이트/라우트 정적 카탈로그(1,906 사이트 / 3,462 라우트, 브라우저 3.0%, 중국어권 58.2%) — [routes-catalog-overview.md](./routes-catalog-overview.md)
- [x] vps-info(signal-archive) 적용 범위 및 provider 선정 — [Q3](./questions/q3-vps-info-adoption.md)
- [x] vps-info TypeScript 재설계 기준 재검토, 위키 주장 재검증, `allowEmpty`·`ofetch` 재시도 설정 확인 — [Q4](./questions/q4-vps-info-typescript-redesign.md)

---

## 2. 남은 질문

- [ ] Q3 5장의 daily.dev GraphQL 스케치를 실제로 호출해 200/필드 구조 **실행 확인** (`version: 54` 고정값이 상향됐거나 익명 쿼리가 막혔을 가능성)
- [ ] `middleware/cache.ts`의 요청 합류 구현 세부(xxhash 키 생성, 동시 요청 병합 지점) — vps-info에는 불필요하다고 결론냈지만 패턴 자체는 미검증
- [x] `errors/` 핸들러의 상태 코드 매핑 (`RejectError`→403, `NotFoundError`→404, 나머지 503) — Q4. vps-info는 컨테이너를 쓰지 않으므로 관측 경로로는 쓰지 않음
- [ ] `config.requestRetry` 기본값과 `x-prefer-proxy` 헤더의 프록시 전환 방식

---

## 3. 다음에 볼 파일 및 함수

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `lib/middleware/cache.ts` | 캐시 키 생성 / 합류 | 요청 합류 구현 방식 검증 |
| `lib/errors/index.ts` | 에러 → 응답 변환 | 라우트 실패 시 HTTP 상태와 본문 형태 |
| `lib/routes/daily/utils.tsx` | `getData()` / `getList()` | daily.dev GraphQL 비공식 엔드포인트의 취약 지점(스키마 변경 내성) |

---

## 4. 참고 사항

- Q3의 vps-info 쪽 서술은 옛 Python 구조 기준이다. 현재 구조는 Q4와 vps-info `docs/adr/0005`–`0009`를 본다.
- Q3의 실행 계획은 vps-info 레포(`/Users/kkh/Desktop/vps/vps-info`) 변경을 수반한다. 이 워크스페이스에는 **코드를 넣지 않고** 설계 판단만 보관한다.
- `diygod/rsshub`(chromium 미포함)과 `diygod/rsshub:chromium-bundled`는 별도 태그다. Tier A 라우트는 전부 전자면 충분하다.
