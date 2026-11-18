---
sha: "538eb3a757db94826cb90c4297279e50c5dd0f83"
created: 2026-11-18
updated: 2026-11-18
sources:
  - rea_video/performance.py
  - rea_video/narrative.py
  - rea_video/entities.py
  - rea_video/playbook.py
  - rea_video/production.py
  - rea_video/pipeline.py
  - rea_video/videomd.py
  - rea_video/plan.py
  - rea_video/generation.py
  - rea_video/remake.py
  - rea_video/code_remake.py
  - rea_video/dance.py
  - rea_video/drive.py
---

# [Q6] feature map 10~16번(보고서 재료 → 재제작)은 어떤 과정인가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 모듈 docstring과 진입 함수 본문(`finalize` 앞부분, `videomd.write`, `generation.choose_strategy`·`pack`·`plan_generation`, `remake.assemble`, `code_remake.code_remake`, `drive` 앞부분)까지 읽음(`코드 확인`). 규칙 세부, 프롬프트 초안 생성, 워프·렌더 알고리즘은 `미확인`. 실행하지 않았다.

## 1. 흐름

```text
1~9번의 shot별 사실 → 10 해석(연기·서사·등장·영상 종류) → 11 breakdown.json + report(사람용)
                                                        → 12 VIDEO.md + video/(agent용)
                         → 13 재제작 계획 → 14 조립 / 15 코드 렌더 재제작 / 16 동작 드라이브
```

## 2. 행별 요약

| 행 | 핵심 | 근거 |
|---|---|---|
| 10 | 연기·서사·등장은 **측정이 아니라 읽은 사람의 판단**(agent 리뷰 또는 VLM, 둘 다 있으면 agent 우선). 연기는 감정 단어 대신 눈·눈썹·입·손의 보이는 단서를 시간 변화로 기록(영상 모델이 감정 단어를 못 다루므로). 서사는 shot별 역할을 매겨 순서를 보존. `playbook`은 측정값으로 영상 종류를 정하고 종류가 단계 목록을 정함, 데이터 없는 단계는 뺌. `production`은 AI→생성 단위, 실사→장면별 촬영 세트업, 코드·화면→연속 구간 합성, 정지→로컬 재구성으로 묶음 | 각 모듈 docstring |
| 11 | `finalize`가 저장된 특징과 VLM 답으로 모든 shot을 재분류하고 계획·요약을 쓰고 `breakdown.json`과 보고서를 냄. 디코딩을 다시 하지 않아 `apply-review`·`correct`·`eval`이 반복 호출. 엔진 미지정 시 기본 `seedance2.0`으로 계획 | `pipeline.py:729`, `1127` |
| 12 | 출력 디렉터리가 패키지. L0 카드 → L1 개요·지도 → L2 `video/<주제>.md`(`timeline.md`는 한 줄 한 shot) → L3 `video/shots/NN.md` → L4 원본 데이터. 키 끝 `~`는 추론. 쓸 때마다 `video/`를 지우고 다시 만듦 | `videomd.py` docstring, `write` |
| 13 | `Planner`가 `routing.yaml`+`models/*.yaml`(+사용자 모델 파일이 우선)로 라벨별 경로·후보 모델을 정함. `plan_generation`은 breakdown·재제작 의도·모델 한계로 생성 단위를 만듦. 전략 우선순위: `remix`(참조 영상) > `keyframes`(다중 shot+참조 이미지) > `frames`(첫 프레임) > `text`. `pack`은 동적 계획법으로 호출 수를 최소화(이야기 단락·장면 전환에서 자르면 가점, 3초 미만 벌점). `checks()`가 과금 전에 한도 초과 등을 경고. 프롬프트는 단위별 초안 + agent가 쓰는 최종본(`remake/prompts.json`) | `plan.py:279`, `generation.py` |
| 14 | `assemble`이 원본 shot 순서대로 조각을 고름: 생성 클립 → 원본 길이에 프레임 단위로 맞춤(`fit_to_original`), 정지 이미지 → 측정한 줌·팬으로 로컬 렌더, 코드 렌더 → `code_video` 또는 원본, 그 외 → 원본. 원본 오디오를 입히고 `remake.mp4`와 좌우 비교 `compare.mp4` 출력. 일부만 만들어도 전체가 나옴 | `remake.py` `assemble` |
| 15 | `frames`가 장면별 레이어를 측정 → `code-remake`가 `code/spec.json`(바탕·글로우·샘플 점·입자·움직임·등장 방식), `render.py`(`redraw.py` 복사), `overlays.ass`를 씀 → 원본 가운데 프레임에 양·밝기를 맞추고 렌더 후 `compare`로 점수. 기존 `spec.json`은 유지하고 `--reset`으로 재시작. "완성"이 아니라 측정값으로 만든 첫 초안 | `code_remake.py` |
| 16 | 춤·격투·운동 shot은 첫·끝 프레임만 주면 안무가 사라지므로 원본 동작을 구동 입력으로 씀. 대상 여부는 픽셀로 알 수 없어 `performance.move`에 agent/VLM이 표시. `drive`는 자막·스티커를 지우고 12fps 프레임 변화량을 0.25초 평활해 조용한 순간·박자 근처에서 10초 안팎(선호 10, 최대 15, 최소 3)으로 분할. `join`이 생성 구간을 원본 길이로 이어 `remake/mine.json`에 씀. 구동 방식: 원본 참조·깊이·골격·점토 인형(모캡)·직접 촬영 | `dance.py`, `drive.py` |

## 3. 미확인

- 라우팅 규칙 R01~R21 내용, `build_unit`의 프롬프트 초안, `warp_map`(클립 워프), `layers.measure`, `redraw.Redraw`, 드라이브 깊이 모델.
- 이 단계 전체를 실제로 돌려 본 결과(생성은 capsule-cinema와 유료 모델 호출이 필요).
