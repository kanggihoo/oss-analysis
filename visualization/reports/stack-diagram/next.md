---
sha: "5af3b095fff7109c905c5284dc510dc06588bade"
created: 2026-11-10
updated: 2026-11-10
---

# Next Session Plan: stack-diagram

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone, 기준 SHA, 라이선스(MIT, 폰트는 OFL 1.1 별도)
- [x] 스킬 본체 전체: `SKILL.md`, `scripts/` 4개, `references/` 2개, `template.html` 앞뒤
- [x] 갤러리 제출 경로: `intake.ts`, `submit.ts`, `challenge.ts`, `files.ts`, `moderation.ts` 앞부분, `schema.ts` 앞부분
- [x] feature map 14행, 공유 계약 4개, 구조도 1장

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 분석 목적이 미정이다. archify와의 비교인지, 템플릿 방식 재구현인지에 따라 부속 행 포함 여부가 바뀐다.
- [ ] 로고 수집이 실제 네트워크에서 어느 출처로 성공하는지는 실행하지 않아 모른다.
- [ ] 구조도의 시각 검토를 하지 않았다.

## 3. 기능 스펙 후보

없음. 범위 승인 전이라 스펙을 쓰지 않는다.

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

승인이 오면 먼저 쓸 스펙: `로고 수집: 브랜드 체인`(행 2) → `capabilities/icon-fetch-brands.md`, 이어서 공유 계약 C1 `icons-manifest`, 행 3, 5.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `skills/stack-diagram/scripts/fetch_icons.py` 60~146행 | `GCP_PRODUCTS`, `AZURE_ALIASES` | 행 3 스펙에 필요한 별칭 표 |
| `skills/stack-diagram/assets/template.html` 160행 이전 CSS | 클래스·토큰 | 행 4 템플릿 계약 |
| `site/src/features/submit/server/pow.ts`, `meta.ts`, `png.ts` | `verifyProof`, `parseMeta`, `diagramSize` | 부속 행 9를 승인하면 |

## 5. 참고 사항 및 후속 제안

- archify와 달리 렌더러가 코드에 없고 에이전트가 HTML 좌표를 직접 쓴다. 스펙의 재현 기준은 "스크립트가 하는 일"과 "템플릿이 요구하는 규약"으로 나뉜다.
