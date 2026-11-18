---
sha: "538eb3a757db94826cb90c4297279e50c5dd0f83"
created: 2026-11-18
updated: 2026-11-18
sources:
  - rea_video/review.py
  - rea_video/survey.py
  - rea_video/cli.py
  - rea_video/pipeline.py
  - skills/rea-video/SKILL.md
---

# [Q2] 4번(agent 리뷰 루프)은 API 없이 Claude Code 같은 agent 안에서 쓸 수 있나

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 정적 읽기. 루프를 실제로 돌려 보지 않았다.

## 1. 결론

**맞다. 별도 API 없이 Claude Code 같은 이미지를 볼 수 있는 agent 안에서 동작하도록 설계되어 있다.** 이 루프는 네트워크 호출이 아니라 **파일 주고받기**다.

- `review.py` 상단 docstring이 "Agent-as-VLM: a multimodal agent looks at the shot images and answers the same questions the VLM would"라고 쓴다. `review.py`·`survey.py`의 `import` 목록에는 `urllib`·`http` 등 네트워크 모듈이 없다(grep 확인). API 호출은 `vlm.py`에만 있다 (`코드 확인`).
- 그림을 "보는" 주체가 **지금 대화 중인 agent 자신의 모델**이다. 그래서 별도 키는 필요 없지만, 이미지 해석에 쓰는 토큰은 그 agent(사용자의 Claude 사용량)가 쓴다. 이 비용은 코드에 드러나지 않는 추론이다.
- `SKILL.md`는 agent가 이미지를 볼 수 없으면 `references/review.md`의 "볼 수 없을 때 규칙"을 따르라고 한다(`SKILL.md` 0절, 읽은 범위 `코드 확인` / 규칙 본문 `미확인`).

## 2. 루프의 모양

```text
rea-video survey ref.mp4 -o out/ref   ──► status: "waiting" + 이미지 경로 + 답을 써야 할 파일 경로
   agent가 이미지를 보고 답 JSON(JEV 형식: 선택지·확률)을 파일에 쓴다
rea-video survey ref.mp4 -o out/ref   ──► (같은 명령을 다시) … 단계가 끝나면 status: "done"
rea-video decompose ref.mp4 -o out/ref  ──► survey 결과로 shot을 나눠 분해
rea-video review out/ref              ──► review_tasks.json(shot별 볼 이미지·도구 판정·우선순위) + review_answers.json(빈 답 양식)
   agent가 shot마다 label_probs, 설명, 연기, 서사 등을 채운다
rea-video apply-review out/ref --by <이름> ──► 규칙 확률과 융합해 breakdown.json·보고서를 다시 씀
```

| 단계 | 근거 | 검증 수준 |
|---|---|---|
| `survey.run`은 답이 없는 작업을 `status: "waiting"`과 파일 경로로 돌려주고, `asker`(VLM)를 넘기면 즉시 처리한다 | `survey.py` `run`의 docstring과 `waiting()` | 코드 확인 |
| VLM 경로의 `asker`는 같은 질문을 이미지와 함께 API로 보낸다(`vlm_asker`). 즉 **같은 질문지를 사람(agent)이 파일로 답하느냐 VLM이 API로 답하느냐**만 다르다 | `survey.py` `vlm_asker` | 코드 확인 |
| `review.build_tasks`가 만드는 지시문은 `SHOT_PROMPT`에서 분류 기준·혼동 사례를 그대로 잘라 쓴다(두 경로가 같은 질문) | `review.py` `LABEL_GUIDE`·`CONFUSIONS` | 코드 확인 |
| agent 답은 `AGENT_WEIGHT = 0.85`만큼 균등 쪽으로 완화한 뒤 융합한다. 프레임 반복·AIGC 라벨 같은 강한 증거는 여전히 이긴다 | `review.py` 상수, `SKILL.md` | 상수 코드 확인 / 융합 결과 `미확인` |

## 3. 한계

- 루프 자체는 API가 필요 없지만 `rea-video`의 다른 부분(ffmpeg, onnx 모델 다운로드)은 로컬 설치가 필요하다. [Q4](q4-asr-resources.md) 참조.
- agent가 이미지를 보지 못하면 이 길은 쓸 수 없다(→ VLM API 또는 규칙만).
- README의 "agent 리뷰로 99~100%"는 문서 수치이고 재현하지 않았다.
