---
sha: "538eb3a757db94826cb90c4297279e50c5dd0f83"
created: 2026-11-18
updated: 2026-11-18
sources:
  - rea_video/**/*.py
  - skills/rea-video/**
  - rea_video/capabilities/**/*.yaml
  - docs/*.md
---

# [Q5] 코드 양은 어느 정도인가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: `wc -l`로 센 줄 수라서 `코드 확인`. 줄 수는 난이도의 근사일 뿐이다.

## 1. 결론

Python 소스가 **약 22,000줄**(`rea_video/*.py` 전체, 하위 패키지 포함, 테스트는 레포에 없음). 여기에 능력 지도 YAML 약 4,200줄, agent skill 약 780줄(+ docs 약 1,260줄)이 있다. 규모는 중간 크기 단일 패키지이고, **한 파일이 큰 편**이다(`packaging.py` 1,950줄, `report.py` 1,300줄, `pipeline.py` 1,136줄, `survey.py` 1,080줄).

## 2. feature map 행별 줄 수 (Python)

| 행 | 기능 | 파일 | 줄 수 |
|---|---|---|---|
| 1 | 입력 메타·shot 분할·전환 | `media`, `probe`, `shots`, `transitions` | 1,653 |
| 2 | 제작방식 판정 | `features`, `motion`, `faces`, `classify` | 1,732 |
| 3 | VLM | `vlm` | 582 |
| 4 | agent 리뷰 루프 | `survey`, `review` | 1,436 |
| 5 | 편집 레이어 | `packaging`, `overlay` | 2,223 |
| 6 | 실제 소재 | `assets` | 273 |
| 7 | 소리 | `stems`, `effects`, `audio`, `sound_source`, `prosody` | 1,484 |
| 8 | 음성·화자 | `speech`, `speakers` | 762 |
| 9 | 촬영 방식 | `aspects/*` | 1,330 |
| 10 | 연기·서사·등장 | `performance`, `narrative`, `entities`, `playbook`, `production` | 1,728 |
| 11 | 조립·보고서 | `pipeline`, `report`, `visual`, `pdf` | 2,658 |
| 12 | VIDEO.md | `videomd` | 446 |
| 13 | 능력 지도 계획 | `plan`, `generation` (+ YAML 약 4,200) | 905 |
| 14 | 재제작 조립 | `remake` | 568 |
| 15 | 코드 렌더 재제작 | `layers`, `code_remake`, `redraw` | 957 |
| 16 | 동작 드라이브 | `dance`, `drive` | 852 |
| 17 | capsule 연결 | `integrations/*` | 505 |
| 18 | 기억·교정 | `memory` | 293 |
| 20 | 평가 | `evaluate` | 392 |
| — | CLI 껍데기(전 행 공유) | `cli` | 932 |
| 19 | skill 문서(Python 아님) | `skills/rea-video/**` | 781 |

(`i18n.py`, `util.py`, `entities` 중복 합산 등 일부 공용 파일은 행에 넣지 않았다. 합이 22,065와 정확히 맞지 않는다.)

## 3. 읽는 부담

- 줄 수가 많은 건 대부분 **규칙·임계값 표와 한·영 문구**(i18n)다. 이번 feature map은 진입점과 함수 이름까지만 읽었다.
- 스펙까지 쓰려면 행 하나에 대해 해당 파일 전체를 읽어야 한다(예: 5번 행은 2,200줄). 목적 밖 행(7, 8, 10 등)은 건너뛰는 편이 현실적이다. 목적이 정해지면 여기서 읽을 줄 수를 다시 센다.
