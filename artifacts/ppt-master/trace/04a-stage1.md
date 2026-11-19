# ppt-master 실행 trace: Step 4 Stage 1 (소통 계약 + 템플릿 선택)

- 기준: `repos/ppt-master` `3af3e8e`, 프로젝트 `projects/portfolio_demo_20261119`
- 실행 일자: 2026-11-19
- 방식: 브라우저 확인 화면(UI branch). 사용자가 화면에서 직접 확정했다.

## 호출과 결과

| # | 시각 | 호출 | 결과 |
|---|---|---|---|
| 1 | 15:15 | agent가 `confirm_ui/recommendations.stage1.json`을 직접 씀 | 파일 생성. `lang: en`, `primary_language: ko-KR`, 소통 계약 초안 7개, `template_options{default_mode: free_design, explicit_workspace_roots: []}`, `revision: 1` |
| 2 | 15:15:52 | `server.py <project> --daemon` | 종료 0. `http://127.0.0.1:5050`, `pid=24220`. 브라우저 실행 요청을 OS가 수락 |
| 3 | 15:15:55~56 | 브라우저가 서버에 요청 | `/`, `static/app.js`, `/api/session`, `/api/catalogs`, `/api/recommendations` 등 200. `favicon.ico`는 404 |
| 4 | 15:16:01 | `server.py <project> --wait-only --wait-stage stage1 --wait-timeout 1800` (백그라운드) | 아래 "예상과 다르게 동작한 것" 참고 |
| 5 | 15:23:31 | 사용자가 화면에서 **Confirm contract & template choice** 제출 | `POST /api/confirm` 200. `result.json`, `template_selection.json` 생성 |
| 6 | 15:23:32 | `--wait-only` 종료 | 종료 코드 0. `[NEXT] Stage 1 is intermediate: install the selected roots (if any), author fresh Stage 2, then wait for final confirmation.` |

## 만들어진 파일 (`confirm_ui/`)

- `recommendations.stage1.json` (agent가 씀, 1018 bytes)
- `result.json` (서버가 씀, `stage: stage1`, `status: stage1-confirmed`, `confirmed_at: 2026-11-19T15:23:31`). 담긴 값은 초안과 같다: canvas `ppt169`, audience, communication_intent, audience_outcome, core_message, delivery_context, artifact_afterlife, `content_divergence: ""`, `primary_language: ko-KR`. `stage1_sha256`과 `selection_sha256`도 들어 있다.
- `template_selection.json` (서버가 씀): `mode: free_design`, `selections: []`, `root_snapshots: []`, `status: confirmed`. `selection_sha256`은 `result.json`의 값과 같다(`5624f593...`).
- `session.json`: 서버가 갱신하는 상태 파일. 확정 직후 `status: waiting_agent`, `expected_stage: stage2`, `recommendation_file: recommendations.stage2.json`, `template_status: ready`, `template_install_version: null`.
- `server.log`

이전 스펙 `template-candidate-selection`의 R-12(`free_design` 제출 → `selections: []`, `selection_sha256`을 `result.json`에 복사)가 실제 화면 제출에서도 그대로 나왔다. 이 스펙에서 "브라우저 미실행"으로 남아 있던 부분 중 `free_design` 확정 경로가 실행으로 확인됐다. 사용자가 화면에서 템플릿 후보를 봤는지, `templates`를 눌러 봤는지는 이 파일들에서 알 수 없다.

## 예상과 다르게 동작한 것

서버가 두 번 시작됐다. `server.log`에 `running at http://127.0.0.1:5050`이 15:15:52와 15:16:02에 두 번 있다. `--wait-only`의 출력은 다음과 같다.

```
[15:16:03] started confirm UI in background: http://127.0.0.1:5050 (pid=51488)
[15:16:03] recovered confirm UI for wait-only at http://127.0.0.1:5050; the browser polling should resume
```

`--wait-only`는 원래 새 서버를 띄우지 않고 떠 있는 서버를 붙잡는 명령이다(코드 주석 "No child is launched here"). 그런데 이번에는 `--daemon`이 만든 `pid=24220` 서버가 이미 없는 것으로 판단하고 `--help`에 적힌 "recover a dead server" 경로로 `pid=51488` 서버를 새로 띄웠다. 사용자 제출은 이 새 서버가 받았다(`15:23:31 POST /api/confirm`).

- 첫 서버가 왜 사라졌는지는 확인하지 못했다. 가능성 하나는 `--daemon`을 실행한 shell 호출이 끝날 때 하위 프로세스가 같이 정리된 것인데 `추론`이다. 로그에 종료 원인은 없다.
- 복구 경로가 있어서 사용자 입장에서는 같은 주소로 계속 쓸 수 있었고, 확정도 정상으로 끝났다.
- 서버 `idle timeout`은 900초다. 이 값이 Stage 2 대기 중에 서버를 내리는지는 확인하지 않았다.

## 다음

서버(`pid=51488`)는 아직 떠 있고 `session.json`이 `waiting_agent`로 Stage 2를 기다린다. `free_design`이라 `apply_template.py`는 건너뛴다. 다음은 Stage 2 권고(`recommendations.stage2.json`)를 쓰는 단계이고, 그 전에 `strategist-image.md`, `modes/_index.md`, `visual-styles/_index.md`, `image-renderings/_index.md`, `icons/README.md`, `charts/chart-vocabulary.md`, `tables/table-vocabulary.md`를 읽어야 한다(`generate-pptx.md` Step 4).
