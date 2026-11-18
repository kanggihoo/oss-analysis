---
sha: "538eb3a757db94826cb90c4297279e50c5dd0f83"
created: 2026-11-18
updated: 2026-11-18
sources:
  - rea_video/vlm.py
  - rea_video/pipeline.py
  - rea_video/cli.py
  - rea_video/survey.py
  - docs/cli.md
---

# [Q1] feature map 3번(VLM 판독자)은 무슨 내용인가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 정적 읽기. VLM을 호출해 보지 않았다.

## 1. 결론

- VLM 판독자는 **shot의 키프레임 이미지(와 선택적으로 짧은 클립)를 외부 멀티모달 모델 API에 보내 "이 shot은 실사인가 AI인가 3D인가"를 묻고 JSON 답을 받아 오는 선택 기능**이다. 기본값은 꺼짐이다(`pipeline.decompose(use_vlm=False)`, CLI는 `--vlm` 또는 `prefs vlm on`일 때만 켠다: `cli.py` `cmd_decompose`) (`코드 확인`).
- 확정 규칙(2번 행)이 못 보는 것, 곧 손가락·글자·물리·질감 깜빡임 같은 "눈으로 봐야 아는 것"을 맡긴다. 결과는 직접 라벨이 되지 않고 `classify.fuse`로 규칙 확률과 섞인다(`코드 확인`: 함수 존재. 섞는 수식은 `미확인`).

## 2. 어떻게 동작하나

| 항목 | 내용 | 근거 | 검증 수준 |
|---|---|---|---|
| 클라이언트 | OpenAI 호환 `/chat/completions` 형식. SDK 없이 `urllib`·`http.client`로 직접 POST. Gemini 프록시, Doubao, GPT, Qwen-VL 등 아무거나 | `vlm.py` 상단 docstring, `import`, `VLMClient._post` | 코드 확인 |
| 설정 | `REA_VLM_BASE_URL`·`REA_VLM_API_KEY`·`REA_VLM_MODEL` 우선, 없으면 capsule-cinema의 `VIDEO_ANALYSIS_*`, `GEMINI3_*`. 모델은 쉼표로 여러 개 적어 예비로 쓴다. `REA_VLM_MEDIA=both|video|frames`가 무엇을 보낼지 정한다 | `vlm.py` `VLMConfig.from_env` | 코드 확인 |
| 보내는 것 | shot마다 첫 프레임, 콘택트 시트, 마지막 프레임 이미지 + (설정에 따라) 짧은 mp4를 data URI로. 점프컷으로 이어진 같은 촬영분은 한 클립으로 묶어 한 번만 묻는다 | `pipeline.py` `run_unit`, `vlm_units`(최대 `max_shots_vlm`=60회) | 코드 확인 |
| 질문 | `SHOT_PROMPT`(shot 단위: 제작 방식, 삽입 소재, 연기, 촬영 방식)와 `WHOLE_PROMPT`(영상 전체: 구조, 문구, 소리, 서사). 프롬프트에 `aspects/` 차원의 질문이 자동으로 들어간다 | `vlm.py` `SHOT_PROMPT`·`WHOLE_PROMPT` 치환 | 코드 확인 |
| 실패 처리 | 모든 호출이 실패해도 멈추지 않고 "VLM 꺼짐과 같음"으로 기록한다. 설정 오타는 시작할 때 막는다(`REA_VLM_MEDIA` 오타 → 조용한 텍스트 전용 실행 방지) | `cli.py` `_check_vlm_config`, `pipeline.py` `vlm_info["status"]` | 코드 확인 |
| 캐시 | 응답을 `cache_dir`에 저장(키에 API 키는 넣지 않음) | `vlm.py` `VLMClient.__init__`, 209행 주석 | 코드 확인(저장 형식 미확인) |
| 응답 정규화 | `normalize_shot_result`·`normalize_whole`·`take_results`가 모델의 느슨한 JSON을 고정 구조로 맞춘다 | `vlm.py` | 함수 존재 코드 확인 / 내용 미확인 |

## 3. 연결

- VLM이 꺼져 있어도 `survey`·`review`(4번 행)로 agent가 같은 역할을 하는 길이 있다. [Q2](q2-agent-review-without-api.md) 참조.
- `--vlm`이 켜진 `decompose`는 `survey`도 VLM에게 시킨다(`pipeline.py` 148행 `vlm_asker`). 즉 VLM은 shot 질문과 컷 개요 검토 두 군데에 쓰인다.

## 4. 미확인

- 응답 JSON의 정확한 필드, 확률 융합 수식, 재시도·타임아웃 정책(`vlm.py` 본문 대부분)은 읽지 않았다.
