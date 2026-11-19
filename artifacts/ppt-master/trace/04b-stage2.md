# ppt-master 실행 trace: Step 4 Stage 2 (최종 해결안 + 제작 옵션)

- 기준: `repos/ppt-master` `3af3e8e`, 프로젝트 `projects/portfolio_demo_20261119`
- 실행 일자: 2026-11-19
- 앞 단계: [04a-stage1.md](04a-stage1.md). Stage 1은 `free_design`으로 확정(`selection_sha256` `5624f593…`)
- 방식: 브라우저 확인 화면. agent가 `recommendations.stage2.json`을 쓰고 사용자가 화면에서 확정했다.

## 1. agent가 한 일

### 읽은 문서 (Stage 2를 쓰기 전)

`generate-pptx.md` Step 4는 Stage 2 전에 "planning-capability block" 7개를 읽으라고 한다. 실제로 읽은 범위는 다음과 같고, 전부 읽은 것은 아니다.

| 문서 | 읽은 범위 |
|---|---|
| `references/strategist-image.md` | 앞부분과 §2(AI Image Strategy) |
| `references/modes/_index.md` | 전체(58줄) |
| `references/visual-styles/_index.md` | 앞 70줄 (카탈로그 표 일부) |
| `references/image-renderings/_index.md` | 앞 60줄 |
| `templates/icons/README.md` | 앞 30줄 |
| `templates/charts/chart-vocabulary.md` | 앞 30줄 |
| `templates/tables/table-vocabulary.md` | 전체(21줄) |

방향 세 개의 기반으로 고른 문서는 한 번씩만 열었다: `modes/{pyramid,narrative,showcase}.md`, `visual-styles/{swiss-minimal,editorial,soft-rounded}.md`, `image-renderings/{minimalist-swiss,editorial,flat}.md`. 파일마다 앞 28줄만 읽었다. 그 밖에 `strategist.md` 86~200줄, `confirm_ui.md` 340~470줄, `plan-core.md` §6.2의 글꼴 목록(Korean sans `Malgun Gothic`, serif `Batang`)을 읽었다.

읽지 않은 것: `plan-core.md` §6.1(팔레트 규칙: 대비, 비율, 기억 앵커). 색은 이 규칙과 대조하지 않고 정했다. 설계서를 쓸 때 대조한다.

### 만든 파일

`confirm_ui/recommendations.stage2.json`(6686 bytes) 하나를 agent가 직접 썼다. 내용:

- `selection_sha256`: `template_selection.json`의 값을 복사
- `lang: en`(UI 언어). 카드의 이름·설명·behavior를 영어로 썼다. 덱 본문 언어는 Stage 1 확정대로 `ko-KR`
- `recommend.delivery_purpose: balanced`, `image_usage: ["none"]`, `generation_mode: continuous`
- `page_count: "7"` (6장 이하면 Step 6의 early gate를 건너뛰므로, 그 gate도 실행해 보려고 7로 했다. 내용상의 이유는 아니다)
- `proactive_speaker_notes: true`, `proactive_custom_animations: false`, `proactive_narration_audio: false`, `refine_spec: false`, `design_spec_depth: brief`
- `design_directions`: 방향 3개, `selected: 0`

| # | id | mode 기반 | visual style 기반 | 색 | 글꼴 | 아이콘 |
|---|---|---|---|---|---|---|
| 0 | `evidence-first` (추천) | pyramid | swiss-minimal | 남색 `#17305A` + 주황 `#E58A00` | Malgun Gothic + Arial | tabler-outline |
| 1 | `case-study-editorial` | narrative | editorial | 녹색 `#2E4A3D` + 벽돌색 `#B4532A` | Batang+Georgia 제목, Malgun Gothic+Arial 본문 | phosphor-duotone |
| 2 | `friendly-showcase` | showcase | soft-rounded | 파랑 `#2B58E8` + 주황 `#FF8440` | Malgun Gothic + Arial | tabler-filled |

세 방향은 모두 `mode`, `visual_style`, `image_strategy.rendering`을 리터럴 `custom`으로 두고, 각 기반 하나를 behavior 문장에 이름으로 적었다. 색은 `catalogs.json`에 목록이 없고 agent가 직접 만든 값이다(`catalogs.json`의 `_comment`: "Color, coordinated typography recommendations, and generated-image style remain generative").

## 2. 서버가 한 일

agent는 서버에 HTTP를 보내지 않는다. 파일을 쓰면 서버가 그 파일을 읽는다.

- 브라우저가 `/api/session`을 1~2초 간격으로 부른다. 서버는 이때마다 `confirm_ui/` 폴더 상태를 다시 계산해 `session.json`에 쓴다(`_sync_session_state`).
- 이 계산에서 `recommendation_version`은 `recommendations.stage2.json` 내용의 sha256이다(`server.py:_file_version`). 파일이 없으면 null이고, 있으면 값이 생기며 서버가 `recommendation_stage: stage2`로 바꾼다.
- 브라우저가 `/api/recommendations`를 요청할 때 서버가 그 시점에 파일을 읽어 검증하고 돌려준다(`get_recommendations`). 파일이 없으면 404, 검증에 실패하면 `recommendation_error`.
- 쓴 직후 확인: `/api/health`가 `recommendation_stage: stage2`, `recommendation_error: null`, `status: ready_user`.

화면의 visual style 참고 이미지는 서버가 `static/style_previews/<id>.svg` 18개를 그대로 내려 주는 것이다(서버 로그 `GET /static/style_previews/ink-notes.svg 200` 등). agent가 만들지 않았다.

## 3. 시간순 기록

| 시각 | 사건 |
|---|---|
| 15:27 | `recommendations.stage2.json` 작성 |
| 15:27:21 | 브라우저 `GET /api/recommendations` → **404** (파일이 서버에 인식되기 전으로 추정) |
| 15:27:54 | `--wait-only`(final) 시작 |
| 15:42:52 | 서버 로그 `idle for 900s, shutting down`. `--wait-only` 종료 코드 1 (`confirm server is no longer running before stage=final was confirmed`). 이 사이 사용자 확정 없음 |
| 15:43:13 | `--wait-only --timeout 0 --wait-timeout 3600`으로 재시도. 서버 복구(`pid=27072`), **약 4초 뒤 사라짐**(15:43:19 이후 로그 없음, 종료 메시지 없음). `--wait-only` 종료 코드 1 |
| 15:43 | PowerShell `Start-Process -WindowStyle Hidden`로 `server.py <project> --timeout 0` 직접 실행. 서버 pid 45264(런처 pid 2752). Bash 호출이 끝난 뒤에도 `stage2`, `ready_user`로 생존 확인 |
| 15:44:12 | `--wait-only --timeout 0 --wait-timeout 3600` 시작(retry2) |
| 15:44:23 | 브라우저가 `style_previews/*.svg` 18개 요청 |
| 15:48:04 | 사용자가 **Confirm final plan** 제출 → `POST /api/confirm` 200, `final confirmation written to .../result.json`, 이어서 `POST /api/shutdown` 200, `shutting down (confirmed)`. `--wait-only` 종료 코드 0 |
| 15:48:17 | `server.py --shutdown` → "no confirm server running — nothing to stop" |

## 4. 결과

`result.json`: `stage: final`, `status: confirmed`, `confirmed_at: 2026-11-19T15:48:04`. 값은 `selected: 0`인 `evidence-first`와 같다. `mode_behavior`, `visual_style_behavior`, 팔레트 6색, 글꼴 `Malgun Gothic + Arial`, `body_size: 24`, `image_usage: ["none"]`, `page_count: "7"`, 노트 `true`/애니메이션 `false`/내레이션 `false`, `generation_mode: continuous`, `refine_spec: false`, `design_spec_depth: brief`가 모두 agent가 보낸 값이다.

`result.json`에 agent가 쓰지 않은 `typography.sizes`(`title 42`, `subtitle 32`, `annotation 18`)와 `heading/body.sample_primary`, `sample_english`(빈 문자열), `note`, `body_size_unit: "px"`가 있다. 화면이나 서버가 본문 24px에서 계산해 넣은 것으로 보이는데 누가 넣었는지는 확인하지 않았다. 사용자가 카드를 직접 수정했는지도 `result.json`만으로는 알 수 없다.

## 5. 예상과 다르게 동작한 것: 서버 수명

- `--daemon`의 기본 idle 자동 종료는 900초다. 사람이 화면을 읽고 확정하는 데 15분이 넘으면 서버가 내려가고, 그러면 `--wait-only`가 종료 코드 1로 끝난다.
- `--wait-only`는 죽은 서버를 같은 포트(5050)로 복구해 띄운다. Stage 1에서는 이 복구 서버가 20분 가까이 살아 있었다. Stage 2 재시도(15:43)에서는 복구 서버가 4초 만에 사라졌다.
- 서버가 사라진 경우는 Stage 1의 첫 `--daemon`(pid 24220)과 Stage 2의 복구 서버(pid 27072) 두 번이고, 둘 다 agent가 Bash 도구로 띄운 프로세스였다. Stage 1 때 복구 서버(pid 51488)는 같은 방식으로 띄웠지만 살아 있었다. 원인은 확인하지 못했다. 종료 메시지가 로그에 없다.
- 마지막 서버는 Bash와 분리해 PowerShell로 직접 띄웠고 정상적으로 끝났다. 이 방식은 문서의 `--daemon` 절차와 다르다.
- 백그라운드 작업 알림이 "exit code 0"이라고 한 경우가 있었다. 우리가 명령 뒤에 붙인 `echo "EXIT=$?"`의 종료 코드였고, 실제 `--wait-only`의 종료 코드는 출력 파일의 `EXIT=` 줄이 정확하다.

## 6. 확인하지 못한 것

- Stage 2 화면에서 사용자가 무엇을 눌렀고 바꿨는지
- `typography.sizes` 등을 누가 `result.json`에 넣었는지
- 복구 서버가 4초 만에 사라진 원인
- `strategist-image.md`와 세 개의 index, `icons`, `charts` 문서를 문서가 요구하는 만큼 끝까지 읽지 않은 영향(색은 §6.1 대조 전)
- 서버 `--timeout 0`이 확정 직후 `POST /api/shutdown`을 막는지(막지 않았다는 것만 확인: 15:48:04에 정상 종료)

## 다음

`result.json`을 한 번 읽었으므로 `design_spec.md`(I~X절)를 쓴다. 쓰기 전 `templates/design_spec_reference.md`를 읽고, `design_spec.md`를 확정값과 대조(Gate 1)한 뒤 `spec_lock.md`를 쓰고 `project_manager.py validate`를 돌린다.
