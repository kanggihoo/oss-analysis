---
sha: "538eb3a757db94826cb90c4297279e50c5dd0f83"
created: 2026-11-18
updated: 2026-11-18
---

# Next Session Plan: rea-video

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone(`538eb3a`)·라이선스 기록, feature map 20행(핵심 19/부속 1)·공유 계약 5건(overview 2절)
- [ ] 분석 목적 결정
- [ ] 구조도(archify)
- [ ] 사용자 스펙 범위 승인(overview 1절 "스펙 범위"는 "feature map만")

## 2. 해결되지 않은 남은 질문

- [ ] 목적이 없다. 후보: (a) 판정 로직 학습, (b) `claude-video`와 비교(영상 읽기 쪽), (c) `capsule-cinema` 연결 검증. 목적에 따라 20행을 합칠 수 있다(예: 4·5·6·7·8·10은 부속 취급).
- [ ] README 수치(정확도, 모델 크기)와 실행 동작은 확인하지 않았다. 실행하려면 ffmpeg와 onnx 모델 다운로드(수십~백수십 MB)가 필요하므로 허용이 필요하다.

## 3. 기능 스펙 후보

목적이 없어서 권장 범위를 내지 못했다. 임시 제안: 2(판정)·4(리뷰 루프)·12(VIDEO.md)·13(계획)·17(capsule 연결)과 공유 계약 `breakdown.json`·라벨 체계.

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

`pipeline.py` `decompose`(126~490행) 본문 → `classify.py` `deterministic`(183행)·`fuse`(521행) → `cli.py` `cmd_review`·`cmd_apply_review` → `generation.py` `plan_generation`. `skills/rea-video/references/`는 리뷰 규칙(`review.md`, `taxonomy.md`)부터.
