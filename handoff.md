# Handoff

- 작성일: 2026-10-26
- 기준 커밋: 이 문서를 커밋하기 직전 HEAD `fe9b968`(main). 이 문서와 같은 커밋에 아래 변경이 모두 들어간다.
- 규칙의 원본은 [AGENTS.md](AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](OSS_ANALYSIS_WORKFLOW.md). 이 문서는 "지금 어디까지 왔고 다음에 무엇을 하나"만 다룬다.

## 1. 지금 바로 이어서 할 일 (사용자 결정 대기)

모두 **스펙 범위 승인 전**이다. 승인 없이 기능 스펙(`capabilities/`)을 쓰지 않는다(워크플로 2장 6번).

| 레포 | 지도 | 해야 할 것 | 시작점 |
|---|---|---|---|
| DeepTutor (`ai-learning/`) | 53행(핵심 33/부속 20), 공유 계약 8 | 범위 승인. 제안: 1~4(턴·루프·도구·컨텍스트), 10·11(마스터리), 14·15(메모리·저널), 17·18(KB·RAG), 부속은 전부 제외 | [overview](ai-learning/reports/DeepTutor/overview.md) 2절, [next](ai-learning/reports/DeepTutor/next.md) |
| learnharness (`ai-learning/`) | 29행(핵심 19/부속 10), 공유 계약 6 | 범위 승인. 제안: 프로버·계획·교사·연습·추출·그래프 원장·도구 레지스트리 + 세션 턴 파이프라인과 공유 계약. 연습 세션은 문서와 실제가 달라 코드 기준으로 쓴다(확인 필요) | [overview](ai-learning/reports/learnharness/overview.md) 2절, [next](ai-learning/reports/learnharness/next.md) |
| claude-video | 10행(핵심 9/부속 1), 공유 계약 4 | 범위 승인 | [overview](reports/claude-video/overview.md), [next](reports/claude-video/next.md) |
| agentmemory (`agent-memory/`) | 38행(핵심 30/부속 8), 공유 계약 6 | 범위 승인 | [overview](agent-memory/reports/agentmemory/overview.md), [next](agent-memory/reports/agentmemory/next.md) |
| teamai-cli | — | 기능 스펙 후보 "배포 대상 제어"(q1 근거, 새 SHA `a44493f` 재확인 필요) 승인 여부, q2(packages·mcp) 결과를 스펙 후보로 올릴지 | [next](reports/teamai-cli/next.md) 3절 |

DeepTutor·learnharness 승인 요청문 전체(표·결정 3개)는 이 세션 대화에 있었고 요약은 위 표와 같다. 부속 행을 스펙으로 쓸지는 행마다 따로 묻는다.

## 2. 이번에 정리한 변경 (git status 기준, 모두 `log.md`에 기록됨)

| 묶음 | 변경 | log.md 항목 |
|---|---|---|
| ai-learning/ 신설 | `GUIDE.md`, `repos.lock.tsv`, DeepTutor·learnharness `overview`·`next`·`diagrams/`·`artifacts/` (24개 파일), `.gitignore`에 `/ai-learning/repos/` | 2026-10-25 ingest ai-learning |
| claude-video 신규 | `reports/claude-video/`, `artifacts/claude-video/` (11개 파일) | 2026-10-25 ingest claude-video |
| agent-memory/ 신설 + gbrain 이동 | `agent-memory/`(46개 파일, agentmemory 신규 포함). 루트 `reports|artifacts/gbrain` 11개 파일 삭제 = 이동이며 `agent-memory/reports/gbrain/`에 있음 | 2026-10-25 workflow gbrain 이동, ingest agentmemory |
| skills-manager | `reports/skills-manager/capabilities/`(스펙 5개 ready), `overview`·`next` 수정, `artifacts/skills-manager/skill-*-demos/`, `repo-metadata.txt`(SHA `7a22192`) | 2026-10-24 capability |
| teamai-cli | `questions/q2-packages-and-mcp-sync.md`, `packages-mcp-demos/`, `overview`·`next` 수정, `repo-metadata.txt`(SHA `a44493f`) | 2026-10-24 ingest |
| herdr-plugin | `reports|artifacts/{collie,herdr-mobile-relay,ovis}`, `reports/mobile-remote-comparison.md`, `GUIDE.md`·`repos.lock.tsv` 수정 | 2026-10-24 update, 2026-10-25 update |
| prompt-eval | `GUIDE.md` "구현 준비 점검" 절 추가 | 2026-10-24 review |
| 루트 | `index.md`, `log.md` | — |

확인 결과: 위 모든 변경이 `log.md`에 대응 항목이 있다. 다만 `claude-video`와 `agentmemory`·`ai-learning`의 항목은 서로 다른 세션이 쓴 것이라 이번 세션은 `claude-video` 내용을 읽어 검증하지 않았다(파일 존재와 `index.md`·`log.md` 행만 확인).

## 3. 알아 둘 것

- **원본 clone은 커밋하지 않는다.** `repos/`, `agent-memory/repos/`, `ai-learning/repos/` 등은 `.gitignore` 대상이다. 다른 PC에서 이어 가려면 각 폴더의 `repos.lock.tsv`(또는 `artifacts/<repo>/repo-metadata.txt`)의 URL·SHA로 다시 clone한다.
- **구조도 시각 검토는 레포마다 한두 장만** 이미지로 봤다. 나머지는 archify 산출물 검증과 Chrome 자동 측정(넘침 없음)뿐이다.
- **서브에이전트가 쓴 overview**(DeepTutor, learnharness)는 메인 세션이 LICENSE·라우트 수 등 일부만 직접 확인했다. 나머지 `코드 확인` 주장은 재검증 전이다. 스펙 단계에서 해당 행을 쓸 때 다시 연다.
- 세션 중 `Read`된 대상 레포의 `AGENTS.md`(learnharness, DeepTutor의 개발자용 지침)는 이 작업과 무관해 따르지 않았다.
- prompt-eval은 스펙 21개가 `ready`이고 구현 전 사용자 결정 7개가 남아 있다([prompt-eval/GUIDE.md](prompt-eval/GUIDE.md) "구현 준비 점검").
- 이 문서는 사람이 읽는 인수인계용이다. 새 세션은 `AGENTS.md` → `index.md` → 해당 레포 `next.md` 순으로 읽으면 된다.
