---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-01
updated: 2026-11-02
---

# Next Session Plan: archify

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션 결과 (2026-11-02, 작업을 여기서 중단)

- feature map 12행 전체를 스펙으로 썼다: [capabilities/](./capabilities/) 16개 파일(12행 + `rendering` 하위 4개). **ready 13 / draft 3**. 상태는 [overview.md](./overview.md) 2절 "스펙·상태" 칸이 기준이다.
- ready(13): artifact-choice, type-routing, input-validation, rendering, rendering-architecture-routing, rendering-workflow, rendering-contracts, delivery, verification-gates, finalize-orchestration, repair-loop, explainer, viewer.
- 실행 확인은 설치본 CLI(레포 `archify/`와 `diff -rq` 차이 없음)로 했고 입력·출력은 `../../artifacts/archify/spec-demos/`에 있다. 레포 clone의 코드는 직접 실행하지 않았다.

## 2. 미정이거나 다시 해야 하는 것

**draft 스펙 3개**

| 스펙 | 남은 일 |
|---|---|
| [rendering-other-types](./capabilities/rendering-other-types.md) | U-01~U-06 해소 문구를 썼지만 편집이 도중에 끊겨 정합을 검증하지 못했다. 1.5 C-ID(C-36~C-43), 1.6 T-ID(T-22~T-32), 2.1 행이 본문 R-41~R-47과 맞는지 확인하고 ready로 올린다. |
| [authoring-contract](./capabilities/authoring-contract.md) | R-18(치수 예산 `32+14(k−1)`, `6.5×단위+21`, 1240px 중 진단으로 강제되는 것)이 미결정. 부분 실행 기록만 `spec-demos/authoring-budget/`(`run.py`, `run.out.txt`)에 있고 스펙에는 반영하지 못했다. 단서: 코드에서 찾은 건 `desktop-readability.mjs:7`의 1.55 비율뿐. input-validation이 ready라 depends 승격도 판단한다. |
| [auxiliary-commands](./capabilities/auxiliary-commands.md) | `brands capture`(R-17), update 확인(R-21), recover(R-22), `examples`(R-20)는 인터페이스 수준만 확인했다. compare·migrate·preview는 조사 끝, preview는 서버를 띄우지 않았다. |

**아직 하지 않은 것**

- 통합 검토(워크플로 4장 5번) 4항목 중 4번: 기능을 가로지르는 대표 흐름 하나를 입력부터 결과까지 글로 잇기. 스펙 간 교차 정합도 q1~q3·overview 반영 수준에서 끝났고 12개 문서 전체를 서로 대조하지는 않았다.
- 재구현 검증(4장 6번): 어느 스펙도 하지 않았다(`reimplementation: 미실행`). 시작점 후보는 ready인 `input-validation`. workflow 재구현은 R-13(수리 후보)·R-21(피드백 루프)이 막히기 쉽다.

**feature map 보정 제안 (판단 대기, 미반영)**

- 행 6 아래 하위 스펙 4개를 표 행으로 둘지(지금은 행 6 칸의 링크만).
- 출력 쓰기 기본 연산(`atomic-output.mjs`의 하드링크 백업→격리 제거→link)은 render·finalize·preview·explainer·deliver가 공유한다. 소유 행을 정하거나 `rendering-contracts`의 비교표를 공유 계약으로 지정.
- 출력 경로·사이드 파일 규칙(`output-path`, `portable-path`)을 별도 공유 계약 행으로 분리할지.
- 행 5 → 행 6: 타입별 구조·참조·레이아웃 검증은 `loadDiagram`이 아니라 각 렌더러 소관. `path-semantics.mjs`는 SVG가 아니라 OS 경로 비교라 행 6 진입점에서 행 7로 이동.
- 행 10 선행에 5·6 추가, 행 12는 행 7에 설명용 의존, 행 11의 가이드 뷰 제거(템플릿에 없음), 브랜드 마크(`brand-marks.mjs`, `archify brands`)를 새 행 후보로.
- `routeMeetsCompositionFloors`(구간 하한 micro 8·interior 16)가 렌더러와 검증 게이트에서 같은 predicate를 쓰는지 연결.

**원본 문서와 구현의 차이 (구현이 사실, 스펙에 기록됨)**

- `schemas/README.md:27`의 `meta.animation: trace` opt-in은 틀림: 렌더러가 읽지 않고 `data-animation="trace"`가 항상 붙는다.
- `authoring-defaults.md:39`의 "`meta.output` 필수"는 5개 타입에만 맞다. `schemas/README.md`도 동일.
- `explainer-authoring.md`의 본문 다이어그램 4개 상한과 `@metric` 필수 필드는 코드에 없거나 다르다.
- `delivery-contract.md`의 stdout "compact JSON 한 개"는 `--json`일 때만.
- 지시문끼리 충돌: `delivery-contract.md:11`(`--quality showcase` 재실행) vs `SKILL.md:44`(`meta.quality_profile`과 같은 값), `SKILL.md:93`(위치 수리 2회차 금지) vs `architecture-layout-repair.md:18`(bounded second repair 허용).

**확인하지 못한 환경·동작**

- `--quality`만 줬을 때 architecture·sequence 본문은 `meta.quality_profile`만 봐서 정적 검사와 어긋난다(코드·일부 실행 확인). 영향 범위의 전수 실행은 안 했다.
- 사람 눈 시각 검토 없음. `inspect-sequence-width` 권고는 fixed 5명 입력 1건만 실행했다.
- 브라우저: viewer의 호버·패닝·실제 클립보드·Safari/Firefox, explainer Ask의 `navigator.clipboard` 없음 경로(추론: 복사가 안 됐는데 "복사됨" 토스트가 뜰 수 있음).
- 네트워크 update 경로, Windows 분기, 프로세스 kill·잠금 경쟁은 실행하지 않았다(코드 확인만, 잠금 파일을 미리 만든 12건은 실행).
- 레포 clone의 `bin/archify.mjs` 직접 실행은 자동 승인에서 거부됐고 설치본으로 대체했다.

## 3. 다음 세션 시작 순서

1. 이 문서와 overview 2절 상태 칸을 읽는다.
2. `rendering-other-types` 정합 확인 → `authoring-contract` R-18 → `auxiliary-commands` 내부 순서로 draft를 닫는다.
3. 통합 검토 4번(대표 흐름)을 쓰고 feature map 보정 제안의 판단을 받는다.
4. 필요하면 재구현 검증.

## 4. 참고

- `../../artifacts/archify/spec-demos/input-validation/`의 임시 git 저장소는 `setup-repo.sh`로 재생성된다(`.gitignore`에서 제외).
- 로컬 설치본: `node ~/.claude/skills/archify/bin/archify.mjs ... --repo-root visualization/repos/archify`.
