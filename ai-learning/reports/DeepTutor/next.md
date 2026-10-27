---
sha: "a31d82624c27d75f4e771d4fcb78dce16470b383"
created: 2026-10-25
updated: 2026-10-27
---

# Next Session Plan: DeepTutor

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] LICENSE 4개(루트 Apache-2.0, `web/vendor/thinking-orbs` MIT, `web/public/provider-icons`의 MIT·CC BY-NC 4.0)를 직접 읽고 기록
- [x] 추적 파일 3,875개 구성과 배포 단위(루트 패키지·`deeptutor_cli`·`web/`·`packaging/deeptutor-cli`·컨테이너·예제 플러그인) 파악
- [x] 턴 실행 경로: WS `unified_websocket` → `TurnApplicationService.start_turn` → `_run_turn` → `TurnEngine.execute` → `ChatOrchestrator` → 캡빌리티(코드 확인). CLI도 `DeepTutorApp`으로 같은 길, Partner만 엔진 직접 호출
- [x] 등록부 전수 집계: 턴 캡빌리티 11, 루프 확장 14, 내장 도구 101, RAG 공급자 9, LLM 제공자 스펙 45, 임베딩 7·검색 14·음성 6·이미지 3·영상 2·파싱 7·서브에이전트 11·채널 16
- [x] 마스터리 정책(`is_mastered`·`next_objective`·게이트 상수·복습 간격표)과 연습 스케줄러 `schedule` 전문, 메모리 쓰기 경로(`write_memory`, L3 참조 주입 `executor.py:572`)
- [x] 기능 지도 53행(핵심 33·부속 20)·공유 계약 8, 구조도(`diagrams/structure.{json,html}`) 산출물 검증·브라우저 확인
- [x] 스펙 범위 승인(2026-10-27, 행 10 일부) — `capabilities/mastery-engine.md`·`review-scheduler.md` draft 작성, C-ID 31건 기준 SHA 존재 확인

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 루프 확장 14개가 `AgentLoop` 어느 훅에서 도구·프롬프트·사전 탐색을 얹는가(`capabilities/protocol.py` 훅 호출 순서)
- [ ] `compose_enabled_tools`의 장착 규칙이 `docs/guides/tools-surface.md` 서술과 이 SHA에서 일치하는가(문서 기준 SHA가 v1.6.12로 다름)
- [ ] L2·L3 메모리 통합이 자동으로 도는 경로가 정말 없는가(grep상 `api/routers/memory.py` 밖 호출처 없음). 워크벤치 UI가 호출하는 방식 확인 필요
- [ ] 마스터리 `service.py`의 `grade_interaction`·`register_question`·경로 리스 흐름과 `tools.py`의 도구별 실패 처리
- [ ] 세션 저장소 `turn_events` 영속과 코디네이터 재생(`after_seq`)의 일관성 규칙, 재시작 복구(`recover_once`)
- [ ] Partner가 턴 서비스를 거치지 않을 때 대화 저장·사용량 집계가 어디서 일어나는가(`PartnerSessionStore`)
- [ ] README의 "사용자별 비공개 파트너 세션", "API 키가 모델을 거치지 않는다" 등 주장의 코드 대조

---

## 3. 기능 스펙 후보

아직 사용자가 승인한 스펙 범위가 없다. 이 세션 지도 기준으로 `ai-learning/GUIDE.md` 비교 축(학습자 상태·수업 진행·자료 연결·모델·데이터)에 가장 가까운 후보를 적어 둔다(승인 요청용 제안이며, 확정이 아님).

| 기능 | 근거 | 상태 |
|---|---|---|
| 마스터리 엔진(10): 상태·게이트·증거 기록, 복습 스케줄러 | [capabilities/mastery-engine.md](./capabilities/mastery-engine.md), [capabilities/review-scheduler.md](./capabilities/review-scheduler.md) | **ready 2개**(2026-10-27 승인·작성, 같은 날 재구현 검증 후 보강). 마스터리 튜터 루프(11)와 경로 생성 `topic_generation.py`는 미승인 |
| 3계층 메모리(14), 학습 저널(15), 컨텍스트 조립(4) | 지도 14·15·4행 | 승인 대기. 학습자 상태가 다음 대화에 쓰이는 경로 |
| 턴 접수·저장·재생(1), 채팅 에이전트 루프(2), 도구 레지스트리(3) | 지도 1~3행 | 승인 대기. 모든 기능의 선행 |
| 지식베이스·RAG 엔진(17·18) | 지도 17·18행 | 승인 대기. 자료 연결 축 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

승인 범위 스펙 2개는 ready이고 재구현 검증(51 테스트, 원본과 순수 계산 8,075사례 비교 불일치 0)을 마쳤다. 남은 일: 보강한 `service.py` 경로 규칙(R-14~R-24, T-29~T-46)으로 재구현을 다시 돌려 원본과 비교하기. 아래는 이 스펙들이 draft였을 때의 확인 순서로, 1~2번은 해소됐다(`prerequisite_ids`는 R-21, `register_question`은 R-22). 기록용으로 남긴다: ① `deeptutor/learning/objective_relations.py`와 `service.py`에서 `prerequisite_ids`를 읽어 진행을 막는 코드가 있는지 확인(`mastery-engine.md` R-07 미결정) ② `service.py` `register_question`·`_grade_group`(1412-1567)·`repair_question`(2356~)과 `lesson_evidence.py`는 읽지 않았으니 단일 문항 경로에 영향이 없는지 확인 ③ 가능하면 원본 순수 함수를 읽기 전용으로 호출해 `review-scheduler` T-ID를 `실행 확인`으로 올린다(이번에는 호출이 거부되어 손 계산만 했다). 경로 생성 `topic_generation.py`는 미승인 후보다. 아래 표는 이전 세션 기준 후보다.

다음에 쓸 기능 스펙: 승인 범위는 끝났다. 후보는 `마스터리 튜터 루프`(행 11, `capabilities/mastery/loop.py` 901줄 미읽음)와 `경로 생성`(`learning/topic_generation.py`). 둘 다 사용자 승인이 필요하다.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `deeptutor/learning/service.py` | `LearningService.grade_and_record`·`grade_interaction`·`register_question` | 채점 → 증거 기록 → 숙달도 갱신 흐름, 실패·충돌 처리 |
| `deeptutor/learning/policy.py` | `next_objective`·`is_mastered`·`map_summary` | 게이트 판정과 다음 목표 선택의 전체 분기 |
| `deeptutor/capabilities/mastery/tools.py` | `MasteryQuizTool.execute`·`MasteryGradeTool.execute` | 튜터가 문제를 내고 채점하는 도구 계약 |
| `deeptutor/agents/loop/agent_loop.py` | `AgentLoop._run_loop` | 라운드 반복·강제 종결·DSML 폴백 |
| `deeptutor/capabilities/protocol.py` | `LoopExtension` 훅 | 루프 확장이 도구·프롬프트를 얹는 지점 |
| `deeptutor/services/session/turns/executor.py` | `_run_turn` 전체 | 컨텍스트 조립 → 엔진 → 이벤트 영속의 순서 |
| `deeptutor/services/memory/consolidator/modes/update.py` | `run_update` | L1→L2 통합 프롬프트·가드 |

---

## 5. 참고 사항 및 후속 제안

- 코드·서버는 실행하지 않았고 의존성도 설치하지 않았다(읽기만). 구조도 산출물 검증과 `visual-check`만 archify 스킬 도구(Node, Chrome)로 실행했다.
- `docs/guides/tools-surface.md`·`docs-for-user/*`·`AGENTS.md`는 레포 안 문서지만 이 SHA와 어긋난 부분이 있어(overview 2절 "문서와 구현의 차이") 후보로만 읽는다.
- 선택 의존성(manim·MinerU·docling·lightrag·graphrag)은 설치하지 않아 해당 경로는 `미확인`이다.
- 구조도 sidecar(스크린샷·접촉 시트·receipt)는 `ai-learning/artifacts/DeepTutor/structure-visual-check/`에 있다. dark와 2048×1320 화면은 자동 측정만 했고 이미지로 보지 않았다.
- 같은 폴더 `learnharness`와 비교할 때는 overview 2절의 "비교 축 후보 위치"를 출발점으로 쓴다.
