# ppt-master 실행 trace: Step 4 마무리 (아이콘 pool → design_spec.md → spec_lock.md → validate)

- 기준: `repos/ppt-master` `3af3e8e`, 프로젝트 `projects/portfolio_demo_20261119`
- 실행 일자: 2026-11-19
- 앞 단계: [04b-stage2.md](04b-stage2.md). Stage 2 확정(`result.json` `stage: final`)
- 산출물 사본: [`snapshots/`](snapshots/) 에 `design_spec.md`, `spec_lock.md`, `result.final.json`, `recommendations.stage2.json`을 복사해 두었다. 원본은 `repos/` 아래라 `commit`되지 않는다.

## 1. agent가 한 일 (순서대로)

| # | 호출 | 받은 것 | 나온 것 |
|---|---|---|---|
| 1 | `result.json` 읽기(한 번) | Stage 1·2의 확정값 전체 | agent context에 보관. 이후 다시 열지 않는다(워크플로 규칙) |
| 2 | `templates/design_spec_reference.md` 읽기 (196줄) | I~X절 구조, 필드 규칙 | 설계서 형식 |
| 3 | `references/plan-core.md` §3·§4·§6.1 읽기 | 페이지 수·내용·cover/closing impact·팔레트 규칙 | 로스터 작성 기준 |
| 4 | `templates/spec_lock_reference.md` + `templates/schemas/spec_lock.schema.json`의 키 목록 + `templates/scaffolds/spec_lock.md` 읽기 | lock 섹션과 키 | lock 형식 |
| 5 | `icon_sync.py <project> tabler-outline/{gauge,database,rocket,server,mail,user,code,chart-line,git-branch,check}` | 아이콘 이름 10개 | `icons/tabler-outline/*.svg` 10개. 종료 0, `+` 10줄 (`04c-icon-sync.out`) |
| 6 | `design_spec.md`를 한 번에 씀 (208줄) | 1~4의 내용 + `sources/portfolio.md` | `design_spec.md` (I~X절, 7페이지 로스터) |
| 7 | 설계서를 확정값과 대조 (Gate 1) | `result.json` vs `design_spec.md` | 34개 검사 전부 일치 (아래 3절) |
| 8 | `spec_lock.md`를 한 번에 씀 (68줄) | 승인된 설계서 | `spec_lock.md` |
| 9 | `project_manager.py validate <project>` | 프로젝트 폴더 | 종료 0. `[OK] Project structure is valid, with warnings.` 경고 1개: `svg_output directory is empty, no SVG files found` (`04c-validate.out`) |

설계서와 lock을 쓰는 스크립트는 없다. 둘 다 agent가 직접 쓴 파일이고, `validate`가 형식만 검사한다. `validate`는 의미(확정값과의 일치)를 검사하지 않는다는 점이 `spec_lock_reference.md` §5에 적혀 있고, 그래서 7번의 대조를 agent가 따로 했다.

## 2. 무엇을 정했나 (agent의 판단)

확정값이 정하지 않은 것을 agent가 정했다. 이 부분은 다음 run에서 다르게 나올 수 있다.

- **7페이지 로스터**: 표지 / 소개 / 주문 API 문제·원인 / 주문 API 조치·결과 / 배포 파이프라인 / 기술 역량 / 맺음. 소스 5개 절을 pyramid 규칙(프로젝트마다 "문제·원인" 다음 "조치·결과")에 맞춰 나눴다.
- **page_rhythm**: P01 `anchor`, P02 `breathing`, P03~P06 `dense`, P07 `anchor`.
- **표 하나**: P06 기술 역량을 `table/record_table`로 두고 §VII, §IX `Visualization`, `Native-ready: skills-table=yes`, lock `page_visualizations`에 기록했다. 차트는 쓰지 않았다(값이 도형 길이를 정하는 데이터는 1.8초→0.4초 같은 두 값 비교뿐이라 큰 숫자로 처리).
- **보조 색 두 개 도출**: `secondary_text #566176`(흰 바탕 대비 6.24:1), `divider #D3D9E2`. `design_spec_reference`가 §III에 이 두 역할을 요구한다.
- **크기 anchor 추가**: 확정값에는 `title 42`, `subtitle 32`, `annotation 18`, `body 24`가 있었고, `footnote 16`, `cover_title 72`, `display 96`을 agent가 더했다(plan-core §6.2가 "반복되는 역할은 모두 선언"하라고 해서).
- **spacing anchors**: 여백 64, 블록 간격 24, 열 간격 32, 모서리 반경 0, 본문 행간 36 (swiss-minimal의 직각 모서리에 맞춤).
- **아이콘 10개**: 소스에서 연상되는 물체로 골랐다(`gauge`, `database`, `rocket` 등). 페이지 배정은 하지 않았다.

### 색 대비 점검 (plan-core §6.1: 본문 4.5:1 이상)

Stage 2에서 읽지 않았던 §6.1을 이번에 읽고 계산했다(상대 휘도식 직접 계산).

| 조합 | 대비 | 판정 |
|---|---|---|
| 본문 `#1B2330` / 흰색 | 15.79 | 통과 |
| 남색 `#17305A` / 흰색 | 13.07 | 통과 |
| 보조 글자 `#566176` / 흰색 | 6.24 | 통과 |
| 주황 `#E58A00` / 흰색 | **2.64** | 본문 기준 미달 |
| 주황 `#E58A00` / 남색 | 4.96 | 통과 |
| 보조 강조 `#5A7FB0` / 흰색 | **4.12** | 본문 기준 미달 |

확정된 팔레트 값을 agent가 바꾸지 않고, 사용 규칙으로 막았다. 설계서 §III에 "accent는 글자로는 남색 바탕 위에서만, 흰 바탕 위 작은 글자로 쓰지 않는다", "secondary accent는 본문 글자로 쓰지 않는다"를 적었다. 이 규칙이 Step 6의 SVG와 체크에서 지켜지는지는 아직 확인하지 않았다.

## 3. Gate 1 대조 결과

`result.json`의 값이 `design_spec.md`와 `spec_lock.md`에 그대로 있는지 스크립트로 34개를 확인했고 모두 일치했다. 대상: Stage 1의 7개 문장, `mode_behavior`(설계서와 lock), `visual_style_behavior`(설계서와 lock), 팔레트 6색(설계서와 lock 각각), `body_size 24`와 `sizes`, 페이지 수 7과 `#### Slide` 7개, canvas, 아이콘 library, 노트·애니메이션·내레이션 `true`/`false`/`false`, 생성 방식 `continuous`.

이 대조는 "문자열이 있는가"만 본 것이다. 의미가 맞는지(예: 문장이 확정 의도를 왜곡하지 않았는지)는 읽어서 판단한 것이고 기계로 검사하지 않았다.

## 4. 문서 선언과 달랐던 점, 확인하지 못한 것

- **`design_spec.md` 중복 줄**: 처음에 §IX Slide 06에 `Visualization`과 `Native-ready` 줄 두 곳에 키 맵을 적었다가 `Native-ready` 한 곳만 남기도록 고쳤다. `validate`가 이 중복을 잡았는지는 확인하지 못했다(고친 뒤에 돌렸다).
- **`Native-ready: skills-table=yes`가 Step 6에서 마커 그룹과 JSON child를 요구한다**(`generate-pptx.md` Step 6의 "Before the gate, every Native-ready `<key>=yes` has its draw-time marker group and JSON child"). 아직 해당 형식을 읽지 않았다. 이 요구가 실제로 final gate에서 막는지는 Step 6에서 확인한다.
- **확인 안내 문구**: 워크플로가 확정 뒤 "Spec-refinement note"(설계서 검토를 원하면 알려 달라는 1줄)를 항상 붙이라고 하는데, 이 run에서는 사용자에게 그 안내를 하지 않았다(`refine_spec: false`가 확정된 상태). 문서 규칙상 누락일 수 있다.
- **`validate`의 경고**: `svg_output`이 비어 있다는 경고뿐이다. Step 6 전이라 정상이다.
- **Step 5(이미지 확보)**: `image_usage: none`, §VIII 데이터 행 없음이라 트리거 조건(`Acquire Via ai/web/slice` 행)에 해당하지 않는다. 문서 규칙대로 건너뛴다. 이 trace는 Step 5를 실행 검증하지 않는다.

## 다음

Step 6(Executor): `executor-base.md` 등 필수 reference를 읽고, 설계 파라미터 확인 메시지와 live preview 서버 기동 후, 페이지를 `svg_output/`에 SVG로 쓴다. P05 뒤 early gate, 7장 완성 뒤 final gate(`svg_quality_checker.py`).
