---
sha: "b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9"
created: 2026-10-25
updated: 2026-10-27
---

# Next Session Plan: learnharness

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 2026-10-27 기능 스펙 5개 작성(`capabilities/`: question-answer-contract, probe-measurement, plan-tree, teaching-cycle, practice-session), 모두 ready. C-ID 61건 기준 SHA 존재 확인, 대표 흐름·통합 검토는 overview 2절 "스킬화 관점 지도" 끝
- [x] 라이선스: 루트 `LICENSE`와 `skills/learnharness/LICENSE` 모두 AGPL-3.0 본문, 서로 바이트 동일(`cmp`)
- [x] `git ls-files` 전체 훑기, README·`docs/architecture.md`(앞 약 230줄)·`docs/development.md`·`docs/desktop-release.md`·`package.json`·`config.ts`
- [x] 턴 합성 루트 `src/server/chat-handler.ts` 전체, 에이전트 3종 팩토리 `teacher-agent.ts`, 도구 구성 `tools.ts`·`tools/{probe,practice,plan}.ts`, 프롬프트 조립 규칙
- [x] 그래프: `mergeFindings`, 추출 파이프라인 헤더·추출기 스키마, 추출 트리거(`turn-service.ts`), 원장 스토어 헤더, 스킬 `SKILL.md`·`data-format.md`
- [x] 배포 입구: Electron `main.cjs` 앞부분·업데이터, `electron-builder.yml`, `next.config.ts`, `proxy.ts`
- [x] 라우트 30개 전수(경로·메서드), 구조도(archify) 1개, 기능 지도 29행(핵심 19 / 부속 10) + 공유 계약 6

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 이해도 측정의 결과(`probe_done` 평가, 확신도, 사고글)가 다음 세션에 어떻게 이어지나? 그래프에는 안 들어가고, 프로버가 `list_sessions`/`list_propositions`로 이름만 읽는다 — 이전 세션 대화를 직접 읽는 경로가 에이전트 도구에 있는지(`read` 도구가 `data/chats`를 읽을 수 있는지)와 컴팩션 요약이 평가를 어떻게 담는지 확인
- [ ] 감사기(auditor)의 탐색 루프와 동일성 판정 기준("equivalence bias") — `extraction.ts` `AUDITOR_INSTRUCTIONS`·`runAuditor`
- [ ] 교사 프롬프트 `teacher/20-teaching.md`·`30-question-principles.md`·`40-jobs.md`·`50-demos.md`와 `prober`/`practice` 독트린의 나머지 — 에이전트 행동을 정하는 핵심 텍스트
- [ ] `src/core/native-messages.ts` `toLlmMessages`·`danglingQuestionOf`·`activeProblemOf`: 기록 → 모델 입력 변환 규칙, `src/server/pi/ui-stream.ts` 스트림 형식
- [ ] 학습자 파일 도구(`read/ls/find/grep`, `fs-shared.ts`)의 경로 제한
- [ ] `docs/architecture.md` 뒷부분(약 330줄)과 `vision.md`·`teaching-methodology.md`·`probe-teach-split.md`는 후보 문서 — 코드와 대조해 읽을지 결정
- [ ] 설정의 "Auto-update" 토글이 정말 어디서도 쓰이지 않는지(`electron/main.cjs` 나머지 본문 확인 필요, 현재는 grep으로만 확인)

---

## 3. 기능 스펙 후보

범위 승인 전이라 아직 후보를 확정하지 않았다. 사용자의 분석 목적(이해도 측정 → 계획 → 가르치기 → 연습 흐름, 지식 그래프, 에이전트 도구 구성)에 가까운 행은 다음과 같다(제안일 뿐이며 승인은 사용자가 한다):

| 기능 | 근거 | 상태 |
|---|---|---|
| 2. 이해도 측정, 3. 의존 관계 계획, 4. 가르치기, 5. 연습 세션, S2 질문·답변 계약 | [capabilities/](./capabilities/) | **ready 5개**(2026-10-27 승인·작성, 같은 날 재구현 검증 후 보강). 행 6의 확신도·사고 필드는 S2에 흡수 |
| 13. 세션 추출 파이프라인, 15. 그래프 원장·파생 뷰, (14. 노트 가져오기) | [overview 2절 지도](./overview.md#기능-지도) | 미승인(스킬화 관점에서는 기록 형식 참고용) |
| 1. 세션 턴 파이프라인(다음 첫 후보: 입력 게이트·`continue`·`text` 처리), 8. 도구 레지스트리와 인자 복구(`heal.ts`·`argument-heal.ts` 소유), 10. job 프로토콜과 wake(`probe_done` 핸드오프 발화 시점 확정) | 스펙 작성 작업자 보고 | 미승인 |
| 부속 10행(19~21, 23~29) | 같음 | 제외로 기록(사용자 별도 답 없음) |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

승인 범위 스펙은 모두 썼고 재구현 검증(83+36 테스트)을 마쳤다. 남은 검증: ① 보강 뒤 규칙으로 재구현을 다시 돌리기 ② 원본(TypeScript, Node에서 직접 실행 가능한 것으로 보임 — 미확인)과 같은 입력으로 출력 비교(`plan_init` 해석기, `buildAnswer`, 시드 섞기 등). 다음 후보: 행 10 `src/server/jobs.ts`의 wake 파이프라인을 읽어 `probe-measurement.md` R-10(핸드오프 발화 시점, 현재 `추론`)을 코드 확인으로 올린다. 그다음 행 1 세션 턴 파이프라인. 아래 표는 이전 세션 기준 후보다.

다음에 쓸 기능 스펙은 승인 후 정한다(지도 순서대로, 선행 계약부터: S1·S2 → 2 → 3 → 4 → 5).

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/agent/subagents/extraction.ts` | `AUDITOR_INSTRUCTIONS`, `runAuditor`, `EXTRACTION_CORE` | 그래프 쓰기의 두 LLM 단계 프롬프트·검증 규칙 |
| `src/core/native-messages.ts` | `toLlmMessages`, `danglingQuestionOf`, `activeProblemOf`, `hasProbeDone` | 기록 → 모델 입력 투영, 질문·문제 게이트의 기준 |
| `src/core/question-core.ts` | `buildAnswer`(693)·`isCorrect`(664)·`shuffleOptions`(595)·`compactAnswerForModel`(764), `QuestionAnswerData` | 답 객체와 채점 계약(공유 계약 S2) |
| `src/agent/prompts/teacher/20-teaching.md` 외 | — | 교사 행동 규칙 전체 |
| `src/server/jobs.ts` | `deliverJobResult`(198), `pump`(446), `settleSteers`(338), `recoverStaleJobs` | wake 파이프라인의 정확한 상태 전이 |
| `src/core/compaction.ts` | 컷 선택·요약 프롬프트 | 이해도 정보가 요약에 어떻게 남는지 |
| `src/server/pi/ui-stream.ts` | `runPiTurn` | 턴 스트림·재접속 계약 |
| `components/session-core.ts` | 세션 클라이언트 상태 머신 | UI 쪽 입력 이벤트·재시도(409) 처리 |

---

## 5. 참고 사항 및 후속 제안

- 문서(`docs/architecture.md` 등)는 구현보다 앞서거나 뒤처진 부분이 많다(overview 2절 "문서와 구현의 차이" 9건). 스펙은 코드 기준으로 쓰고 문서는 후보로만 읽는다.
- 레포 `AGENTS.md`는 레포 개발자용 지침("추측 금지, 질문 먼저" 등)이라 이 분석 작업에는 적용하지 않았다.
- 구조도 부산물(스크린샷·접촉 시트·receipt)은 `ai-learning/artifacts/learnharness/structure-visual-check/`에 있다.
- 코드·서버를 실행하지 않았고 의존성을 설치하지 않았다. 실행 실험이 필요하면 `data/` 대신 `LH_DATA_DIR`을 임시 경로로 지정해야 사용자 데이터를 건드리지 않는다(`config.ts`).
