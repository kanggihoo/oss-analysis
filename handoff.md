# Handoff

- 작성일: 2026-10-26
- 기준 커밋: 이 문서를 커밋하기 직전 HEAD `fe9b968`(main). 이 문서와 같은 커밋에 아래 변경이 모두 들어간다.
- 규칙의 원본은 [AGENTS.md](AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](OSS_ANALYSIS_WORKFLOW.md). 이 문서는 "지금 어디까지 왔고 다음에 무엇을 하나"만 다룬다.

## 1. 지금 바로 이어서 할 일 (사용자 결정 대기)

모두 **스펙 범위 승인 전**이다. 승인 없이 기능 스펙(`capabilities/`)을 쓰지 않는다(워크플로 2장 6번).

| 레포 | feature map | 해야 할 것 | 시작점 |
|---|---|---|---|
| DeepTutor (`ai-learning/`) | 53행(핵심 33/부속 20), 공유 계약 8 | 범위 승인. 제안: 1~4(턴·루프·도구·컨텍스트), 10·11(마스터리), 14·15(메모리·저널), 17·18(KB·RAG), 부속은 전부 제외 | [overview](ai-learning/reports/DeepTutor/overview.md) 2절, [next](ai-learning/reports/DeepTutor/next.md) |
| learnharness (`ai-learning/`) | 29행(핵심 19/부속 10), 공유 계약 6 | 범위 승인. 제안: 프로버·계획·교사·연습·추출·그래프 원장·도구 레지스트리 + 세션 턴 파이프라인과 공유 계약. 연습 세션은 문서와 실제가 달라 코드 기준으로 쓴다(확인 필요) | [overview](ai-learning/reports/learnharness/overview.md) 2절, [next](ai-learning/reports/learnharness/next.md) |
| claude-video | 11행(핵심 10/부속 1), 공유 계약 4 | 범위 승인. 결정 사항은 1.2 | [overview](reports/claude-video/overview.md), [next](reports/claude-video/next.md) |
| agentmemory (`agent-memory/`) | 38행(핵심 30/부속 8), 공유 계약 6 | 범위 승인 | [overview](agent-memory/reports/agentmemory/overview.md), [next](agent-memory/reports/agentmemory/next.md) |
| teamai-cli | — | 기능 스펙 후보 "배포 대상 제어"(q1 근거, 새 SHA `a44493f` 재확인 필요) 승인 여부, q2(packages·mcp) 결과를 스펙 후보로 올릴지 | [next](reports/teamai-cli/next.md) 3절 |

### 1.1 DeepTutor·learnharness 승인 요청 (2026-10-25 제안, 아직 답 없음)

> **2026-10-27 진행**: 아래 제안 대신 스킬화 관점 feature map에서 learnharness 행 2·3·4·5 + S2(ready 5)와 DeepTutor 행 10 중 상태·게이트·복습 스케줄러(ready 2)를 스펙으로 썼고 재구현 검증까지 마쳤다(각 overview 2절 "재구현 검증 결과"). 다음은 각 `next.md` 4절.
> **2026-10-27 보류**: 사용자가 목적을 "Claude Code 안의 가벼운 학습 스킬"로 바꿨다. 아래 제안(제품 기능 기준)은 쓰지 않고, 각 overview 2절 "스킬화 관점 feature map"의 재구성 제안으로 다시 승인받는다. 아래 내용은 제품 전체 feature map 기준 기록으로 남긴다.

아래 행 이름은 각 overview 2절 "기능" 칸의 줄임말이다(2026-10-26에 행 수·구분·공유 계약 S1~S8을 overview와 대조해 일치 확인). 구분(핵심/부속)과 선행은 feature map 작성자(서브에이전트)의 제안이다.

**사용자가 정할 것 3가지**

1. **범위**: 아래 제안대로 쓸지. 제안에 없는 핵심 행은 `미작성`으로 남긴다.
2. **부속 행**: 스펙으로 쓸 것이 있는지. 행마다 따로 묻고, 답이 없으면 전부 제외로 적는다(기본 제안은 제외).
3. **learnharness 연습 세션**: `docs/architecture.md`는 `PracticeStore`와 분할기→생성기→채점기를 설명하지만 코드에는 없다(코드 확인). 실제는 `kind:"practice"` 세션과 `problem`/`conclude` 두 도구다. 스펙을 코드 기준으로 써도 되는지.

승인되면 overview 1절 "스펙 범위"에 승인 행·제외 행(이유: 사용자 제외)을 적고 4장으로 간다(`oss-repo-spec` 5단계). 선행·공유 계약을 먼저 쓴다.

**learnharness 제안 범위** (핵심 8행 + 공유 계약)

- 세션 턴 파이프라인 (선행으로 필요)
- 이해도 측정(프로버), 의존 관계 계획, 가르치기(교사), 연습 세션
- 세션 추출 파이프라인, 그래프 원장·파생 뷰·배치
- 도구 레지스트리·인자 복구
- 공유 계약: 세션 기록(S1), 질문·답변(S2), 그래프 원장(S3). 필요하면 설정(S4), job·steer(S5), 데이터·키 위치(S6)
- 제외 제안(부속 10행): 구독 연결(ChatGPT·Copilot·Grok), 웹 검색 어댑터(Tavily·Brave), 음성 받아쓰기, 사용량·비용 집계, 세션 관리·찾기·내보내기·단축키, Electron 셸, 인앱 업데이트, 패키징·릴리스, 에이전트 스킬 `learnharness`, 개발·마이그레이션 스크립트
- feature map에는 있지만 제안에서 빠진 핵심: 학습자 입력 채널, 프롬프트 조립·오버라이드, 컨텍스트 컴팩션, job 프로토콜·wake, 조사 계열·산출물 계열 하위 에이전트, 노트 가져오기, 그래프 화면, 삭제와 정리, 모델 슬롯·키·카탈로그, 실시간 알림(SSE)

**DeepTutor 제안 범위** (핵심 10행 + 공유 계약)

- 턴 접수·저장·재생, 채팅 에이전트 루프, 도구 레지스트리·장착 규칙, 대화 컨텍스트 조립
- 마스터리 엔진, 마스터리 튜터 루프
- 3계층 메모리, 학습 저널·시작 제안
- 지식베이스 수명주기·소스 동기화, RAG 엔진 패밀리(llamaindex·pageindex·graphrag·lightrag를 한 행으로 묶음)
- 공유 계약: 턴(S1), 도구(S2), 와이어 프로토콜(S3), 계정·워크스페이스 스코프(S4), 설정(S5), RAG(S6), 루프 확장(S7), 세션 저장소(S8) 중 위 행이 쓰는 것
- 제외 제안: 부속 20행 전체(연결형 외부 지식 소스, MarginNote4 브리지, KB 검색 품질 평가, 파일 라이브러리, Partner 그룹, 대화 기록 가져오기, 스킬·스킬 허브, 페르소나, MCP 서비스, CLI 앱, 코드 실행 샌드박스, 플러그인 플랫폼, 음성 어댑터, 이미지·영상 생성 어댑터, 콘텐츠 워크스페이스, 실행·배포·업데이트, 스케줄, 태스크 보드, Whisper 연습방 UI, 개발·검증 스크립트·CI)
- feature map에는 있지만 제안에서 빠진 핵심 예: 딥 리서치, 딥 퀘스천, 딥 솔브·질문 인터뷰, 시각화, 오디오 오버뷰, 연습·문제 노트북, 코스, 노트북, 몰입형 읽기, 영상 학습, 북 엔진, 공동집필, Partner 런타임, IM 채널 어댑터, 서브에이전트 상담, 멀티유저·인증, 설정·모델 카탈로그, LLM·임베딩·웹 검색 provider 패밀리, 웹 UI, CLI·SDK 파사드

**제안 근거**: 비교 축(학습자 상태 / 수업 진행 / 자료 연결 / 모델·데이터)에 직접 닿는 행을 골랐다(`ai-learning/GUIDE.md`). 이 선택은 feature map 작성자의 권고이고 사용자가 정한 것이 아니다.

구분·선행의 원본은 overview 2절이다. 이 문서의 목록과 어긋나면 overview를 따른다.

### 1.2 claude-video 승인 요청 (2026-10-25 요청, 아직 답 없음)

`/watch`(영상 URL·파일 → 프레임·전사문·Gemini 답)를 분석한 것이다. 기준 `03ceb42`(v0.3.2), MIT. 행 이름은 [overview](reports/claude-video/overview.md) 2절 "기능" 칸 그대로다.

**사용자가 정할 것 3가지**

1. **범위**: 핵심 10행을 모두 스펙으로 쓸지, 일부만 쓸지(일부면 번호로 지정). 제안은 전체다. 코드가 약 2,800줄로 작아 행마다 스펙이 짧게 끝난다.
2. **부속 행 11 (패키징·배포)**: 스펙으로 쓸지. 행마다 따로 묻는다. 기본은 제외.
3. **행 5(클라우드 Whisper)와 행 6(로컬 WhisperX) 분리 유지 여부**: 둘 다 "오디오 → 세그먼트"를 구현하지만 6은 별도 venv·sentinel이라는 고유 상태가 있어 나눴다. 합쳐도 되면 알려 준다. 답이 없으면 분리 유지.

| # | 행 | 구분 | 선행 |
|---|---|---|---|
| 1 | 설정 해석 | 핵심 | 없음 |
| 2 | 소스 획득 (URL·로컬 파일) | 핵심 | 없음 |
| 3 | 자막 파싱·전사 세그먼트 | 핵심 | 없음 |
| 4 | 프레임 선택·추출 | 핵심 | 없음 |
| 5 | 클라우드 Whisper 전사 | 핵심 | 3 |
| 6 | 로컬 WhisperX 전사 | 핵심 | 3 |
| 7 | Gemini 엔진 | 핵심 | 1, 2 |
| 8 | local 엔진 오케스트레이션·보고서 | 핵심 | 1~7 |
| 9 | 설정 점검·설치 (setup.py + SessionStart hook) | 핵심 | 1 |
| 10 | `/watch` 에이전트 호출 규약 (SKILL.md) | 핵심 | 8, 9 |
| 11 | 패키징·배포 | 부속 | 없음 |

- 공유 계약 4건(전사 세그먼트, 프레임 레코드, 설정 dict, 보고서 형식)은 별도 스펙 없이 소유 행(3, 4, 1, 8)의 1.3에 둔다(제안).
- 승인되면 overview 1절 "스펙 범위"에 승인 행·제외 행을 적고 4장으로 간다. 선행이 없는 1~4는 서브에이전트로 병렬 작성 가능하다([next](reports/claude-video/next.md) 4절).
- **주의**: `watch.py`·`config.py`·`SKILL.md`만 전문을 읽었고 나머지 스크립트 본문은 일부만 읽었다. 행 2~7·9의 `코드 확인`은 진입점 수준이므로 스펙 단계에서 다시 읽는다. 외부 도구(yt-dlp, ffmpeg)와 API는 실행하지 않았다.

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
