---
sha: "916a0e1cd5f4a84de4ec7e485386c7d9941d7e00"
created: 2026-11-10
updated: 2026-11-10
---

# Next Session Plan: K-Humanizer

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 기준 고정: clone(전체 44 commits), SHA `916a0e1`, MIT, v0.5.0, `artifacts/K-Humanizer/repo-metadata.txt`
- [x] 두 `SKILL.md` 전문, references 9개 전문(`patterns`, `business-korean`, `native-writing`, `evaluation`, 이력서 5개)
- [x] 매니페스트 4개, `openai.yaml` 2개, 검증 스크립트 4개 전문, CI 워크플로, `docs/validation-plan.md` 전문, README, `CHANGELOG.md` 0.3.0~Unreleased
- [x] 비즈니스 fixture 첫 행과 도메인·모드·행동 분포(`grep`으로 셈), 2026-11-07 보고서 전문(2차 작업에서 읽음), 2026-08-25 기준선 전문, `scripts/test_*.py` 3개(골든셋·점수 기록 전문, 보충셋 1-60·137-210줄)
- [x] feature map 16행(핵심 13 / 부속 3), 공유 계약 4, 구조도 1장
- [x] 범위 승인(2026-11-10, 1차 권장대로 행 1~7, 9 / 2차 행 8, 10~13, 15, 16 / 3차 행 14)과 기능 스펙 16개 작성(모두 ready), 통합 검토 2회
- [ ] 분석 목적 확인 (아직 안 받음, 기본 목적으로 진행함)

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 분석 목적이 무엇인가: 재구현 / 한국어 글쓰기 스킬 설계 참고 / 도입 검토. 답에 따라 행 14(플러그인 배포)를 추가할지, 이미 쓴 스펙 중 어느 것이 핵심인지 우선순위가 갈린다
- [ ] 검증 스크립트와 unittest를 실행해도 되는가. 이번 세션은 권한 설정으로 거부돼 정적 읽기만 했다. 허용되면 `validate_business_set.py`가 32건·커버리지 15쌍을 실제로 통과하는지 확인한다(읽은 코드로는 통과해야 한다)
- [ ] 스킬이 LLM에서 실제로 어떻게 동작하는가는 확인하지 못했다. 보고서(`business-review.md`)는 읽어 스펙의 확인 한계에 옮겼지만, 원자료 `.jsonl`(출력·검토 행)을 열어 사례별로 확인하지는 않았다
- [ ] `evaluation.md:219-221`의 fixture 30건 표기는 갱신 누락으로 판단했다(실제 32건). 레포 이슈로 알릴지는 사용자 결정(이 작업 공간 규칙 밖)
- [ ] `golden_set.v0.jsonl` 본문과 `test_validate_business_set.py` 60-137줄은 열지 않았다(행 15 스펙은 검증기 코드와 건수로 썼다)

## 3. 기능 스펙 후보

질문 문서가 없어 해당 없음. feature map 16행의 스펙이 모두 ready다. 남은 후보 없음.

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

승인 범위는 끝났다. 남은 선택지:

- 재구현 검증(워크플로 4장 6번)은 사용자가 요청할 때만 한다: 스펙 16개만 읽는 서브에이전트가 같은 스킬(두 `SKILL.md`와 references)을 다시 쓰고 원본과 대조해 스펙의 빈틈을 찾는다.
- 검증 스크립트·unittest 실행이 허용되면 행 15의 규칙과 사례(T-01~T-09)를 실제 출력으로 확인한다.
