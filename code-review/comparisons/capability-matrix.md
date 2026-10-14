# 기능 비교 매트릭스 (공통 비교 기준 11항목)

- 작성일: 2026-10-13
- 정정 반영: 2026-10-13 보고서 정정 반영
- 대상 SHA (`../repos.lock.tsv`와 일치)
  - pr-agent: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63`
  - open-code-review: `57273a9ea28548b94b3d67c247ff13a63c01fc47`
  - kodus-ai: `45676c5fe7ac016b6206ccea006e459677d92842`
- 기준: 각 레포 `reports/<repo>/00`~`07`, `next.md` (근거 줄 번호는 보고서에 있고 여기에는 복제하지 않는다). 세 보고서 모두 **정적 추적만** 했다(설치·실행·모델 호출 없음). 이 문서도 실행 결과가 아니다.
- 칸 읽는 법: **지원 수준(지원/부분 지원/미지원/미확인)** — 결론 한 줄 — [보고서 절 링크]. 지원 수준 정의는 `../GUIDE.md` 3.3절. 점수·순위는 매기지 않는다. 전문 영역이 다른 프로젝트(pr-agent=diff·Provider, open-code-review=루프·도구, kodus-ai=SaaS 전체)를 한 축으로 줄 세우지 않는다.
- 이 문서에서 보고서 표기를 그대로 옮기지 않고 정리한 칸에는 "※"를 붙이고 아래 "표기 메모"에 이유를 적었다.

---

## 1. 비교 표

| 항목 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| **Agent Loop** (Q4) | **미지원.** 모델 요청은 `[system, user]` 두 메시지, `tools`/`tool_choice` 없음. 있는 것은 재시도·모델 fallback·청크 병렬 호출·`/improve`의 생성→자기 반성 2단계뿐(도구 반복 아님). [02#q4](../reports/pr-agent/02-context-loop-verify.md#q4) | **지원.** 파일 1개 = 하위 작업, 파일당 Main Tool-Calling 루프(최대 30라운드). 종료 정상=`task_done`뿐, 도구 호출 없음은 종료가 아니라 재요청(라운드 소모). 컨텍스트 60%/80% 압축. 모델 교체 fallback·총 비용 상한·취소 경로 없음. [02#q4](../reports/open-code-review/02-context-loop-verify.md#q4) | **지원.** finder / 후보별 verifier / synthesis / heavy resample이 AI SDK 도구 호출 루프(`stepCountIs` + 예산·완료 게이트·강제 제출 정책). Kody Rules 판정은 루프가 아니라 도구 없는 1회 호출의 반복. 한계: 실행당 토큰·금액 상한 없음, 파이프라인 실행기는 취소 신호를 보지 않음(추론). [02#q4](../reports/kodus-ai/02-context-loop-verify.md#q4) |
| **동적 탐색** (Q3) | **미지원.** 고정 문맥 확장(주변 줄, 지침 파일, 티켓, 이전 finding)만 지원. 모델이 요청하는 파일·검색·AST/LSP·MCP 경로 없음. [02#q3](../reports/pr-agent/02-context-loop-verify.md#q3) | **지원(텍스트 검색 수준).** 모델이 `file_read`/`file_find`/`code_search`(`git grep`)/`file_read_diff` 호출. 심볼 의미는 모르고 모델이 추론. 프롬프트가 "다른 파일에서 발견한 문제는 코멘트하지 말라"고 지시. [02#q3](../reports/open-code-review/02-context-loop-verify.md#q3) | **부분 지원(조건부; 보고서 표기 "지원(조건부)").** 샌드박스 체크아웃이 있을 때만 `grep`(rg)/`readFile`/`listDir`/`findFile`/`checkTypes`/`getCallers`를 모델이 호출. 체크아웃이 없으면 도구 없이 diff만(self-contained). `getCallers`는 사전 계산된 call graph 문자열 파서. [02#q3](../reports/kodus-ai/02-context-loop-verify.md#q3), [샌드박스 사용 조건](../reports/kodus-ai/02-context-loop-verify.md#sandbox) ※ |
| **코드 접근** (Q2) | **부분 지원(변경 파일 한정)** ※. Provider API로 변경 파일의 base/head 본문 수집(50개 초과 시 본문 생략). 리뷰 경로에 clone·샌드박스 없음, 변경 파일 외 임의 파일 조회 경로 없음. 수집 중 PR 변경은 감지하나 게시 직전 SHA 재확인은 없음. [01#q2a](../reports/pr-agent/01-execution-and-diff.md#q2a) | **부분 지원.** 로컬 git 작업 트리만(엔진은 clone·fetch 안 함). 도구는 `git show <ref>:<path>`/`git grep <ref>`로 ref 기준 읽기. ref를 SHA로 고정하지 않음(존재 확인만), workspace 모드는 diff는 시작 시점 스냅샷·`file_read`는 호출 시점 디스크. [01#q2](../reports/open-code-review/01-execution-and-diff.md#q2) | **부분 지원.** 파일·패치는 Provider API, 탐색용 체크아웃은 샌드박스(`git fetch --depth=1` 후 PR ref; local/E2B/null 선택). Head SHA가 하나로 고정되지 않음(목록=라이브, 본문=브랜치명, 체크아웃=그 시점 팁, 댓글 앵커=웹훅 head). [01#q2](../reports/kodus-ai/01-execution-and-diff.md#q2) |
| **Diff 처리** (Q2) | **지원**(부분 잘림 diff 미감지 등 예외 있음). `FilePatchInfo`, 정규식 기반 주변 줄 확장(앞 5/뒤 1, 동적 문맥 최대 10줄, AST 아님), 토큰 예산 압축·(옵션)청크, 번호 붙은 hunk, GitHub/GitLab 인라인 위치 변환. 빈 patch만 복구하고 일부만 잘린 patch는 감지 못 함. [01#q2b](../reports/pr-agent/01-execution-and-diff.md#q2b) | **부분 지원.** `git diff -U3`를 정규식으로 파싱, 문맥 확장 없음. 큰 파일(47110 토큰 초과)은 분할·압축 없이 통째 제외. 줄 번호는 모델이 `existing_code`를 주고 프로그램이 3단으로 복원하나 side(옛/새) 정보가 없음. [01#q2](../reports/open-code-review/01-execution-and-diff.md#q2) | **부분 지원.** Provider hunk를 그대로 사용(활성 경로에 주변 줄 확장 알고리즘 없음), 번호 붙은 diff, 토큰 예산(4글자≈1토큰 추정)으로 파일 배치 분할, finding 줄이 hunk와 겹쳐야 유지, GitLab position·3회 위치 보정 재시도. GitHub 빌더가 rename 구경로를 버리고 Provider가 자른 diff는 복구하지 않음. [01#q2](../reports/kodus-ai/01-execution-and-diff.md#q2) |
| **검증** (Q5) | **부분 지원**(`/review`는 미지원, `/improve`만). `/review`는 스키마 경고뿐. `/improve`는 같은 diff만 보는 자기 반성 점수 + 적용 가능성·Python 문법 검사. 추가 파일 접근 없음, 실제 경로와 연결된 evals 없음. [02#q5](../reports/pr-agent/02-context-loop-verify.md#q5) | **부분 지원.** 파일별 1회 diff-only 반증 필터(같은 모델·새 대화·도구 없음, 추가 파일 못 읽음). diff로 입증 안 되면 의심스러워도 통과시키도록 설계. 파일 간·재실행 간 중복 제거 없음, evals 미발견. [02#q5](../reports/open-code-review/02-context-loop-verify.md#q5) | **부분 지원.** finder 직후 후보별 verifier Agent Loop가 같은 도구로 추가 파일을 읽고 반증 시에만 제거(기본 KEEP, 실패도 KEEP). 같은 모델 슬롯. 결정적 필터·LLM dedup·severity 필터 있음. evals 있음(도구 출력은 녹화본 재생). [02#q5](../reports/kodus-ai/02-context-loop-verify.md#q5) |
| **증분 리뷰** (Q6) | **지원(시각 기반; 보고서 표기)** ※. 기준은 "마지막으로 리뷰한 SHA"가 아니라 이전 리뷰 댓글 게시 시각 이후 커밋. 앵커 없으면 전체 리뷰로 폴백. 오래된 결과 폐기 없음, 중복 방지(delivery ID, PR 슬롯)는 프로세스 로컬·옵트인. [03#q6](../reports/pr-agent/03-incremental-memory-rules.md#q6) | **미지원.** 마지막 리뷰 SHA·이전 코멘트 상태 없음. 예제 워크플로는 `opened`만 구독하고 `concurrency`로 이전 실행을 취소할 뿐. [03#q6](../reports/open-code-review/03-incremental-memory-rules.md#q6) | **부분 지원.** 직전 SUCCESS 실행의 `lastAnalyzedCommit` 기준, 고아 커밋(리베이스)은 전체 리뷰로 폴백. 이벤트 단위 SHA 멱등 키 없음, 실행 중 Head 변경 취소 없음, 충돌한 비명령 실행은 조용히 버려짐. [03#q6](../reports/kodus-ai/03-incremental-memory-rules.md#q6) |
| **장기 메모리** (Q7) | **같은 PR만 지원 / PR 간 미지원.** finding 상태(ACTIVE/RESOLVED)를 리뷰 댓글의 숨은 HTML 주석에 저장해 다음 실행 프롬프트에 주입 + 사람이 resolve한 스레드 읽기. `similar-issue`는 GitHub 이슈 검색이며 팀 메모리 아님, `push_outputs`는 쓰기 전용. [03#q7](../reports/pr-agent/03-incremental-memory-rules.md#q7) | **미지원.** 세션 JSONL은 쓰기만 있고 읽는 코드는 `ocr viewer`뿐(다음 리뷰 입력이 되지 않음). 실행 내 압축 요약은 영속 아님. [03#q7](../reports/open-code-review/03-incremental-memory-rules.md#q7) | **피드백 학습은 미지원 / 규칙형 메모리는 부분 지원.** 반응 수집·임베딩 필터 코드는 있으나 읽기 진입점 `KodyFineTuningStage`가 파이프라인에 등록되지 않음(공식 문서도 비활성 명시). `type: MEMORY` 규칙(수동/MCP/채팅)과 사람 PR 댓글에서 규칙 생성은 쓰기·읽기 경로 모두 있음. [03#q7](../reports/kodus-ai/03-incremental-memory-rules.md#q7) ※ |
| **팀 규칙** (Q8) | **부분 지원.** 커스텀 프롬프트(`extra_instructions`), 지침 파일(기본 `AGENTS.md`), 계층형 `.pr_agent.toml`(호스트→조직→저장소→디렉터리→명령 인자). 저장·승인·버전 관리·피드백에서의 추출 없음. 경로별 적용은 모델이 알아서 판단. [03#q8](../reports/pr-agent/03-incremental-memory-rules.md#q8) | **부분 지원.** 4계층 JSON(custom > project > global > 내장)의 경로 glob→자연어 체크리스트. 첫 일치 하나만 쓰고 병합 없음. 승인·버전·팀 범위 없음. 규칙을 PR head 작업 트리에서 읽어 신뢰 경계 문제(보고서 의견). [03#q8](../reports/open-code-review/03-incremental-memory-rules.md#q8) | **부분 지원.** Mongo 조직 문서의 규칙 배열(전역/저장소/디렉터리/path), 승인 게이트(기본 off), 소프트 삭제, 감사 로그, 저장소 파일 동기화, 사람 댓글에서 규칙 생성. 우선순위·충돌 해결·버전 이력·팀 범위 없음. **핵심 구현이 `libs/ee/`(상용).** [03#q8](../reports/kodus-ai/03-incremental-memory-rules.md#q8) |
| **Jira** (Q9) | **부분 지원.** 제목·설명·브랜치에서 키 추출 → Jira Cloud 조회 → 텍스트를 프롬프트에 삽입 → 모델이 diff만 보고 충족/미충족 분류. 요구사항별 근거 탐색·이번 PR 범위 구분 없음. [03#q9](../reports/pr-agent/03-incremental-memory-rules.md#q9) | **미지원**(`--background` 텍스트 슬롯만 부분 지원). 이슈 식별·인증·필드 추출·조건별 판정 모두 없음(찾은 범위는 보고서에). [03#q9](../reports/open-code-review/03-incremental-memory-rules.md#q9) | **부분 지원.** 직접 연동 어댑터는 없고 MCP 경유 별도 Business Logic 단계(샌드박스보다 앞, 도구 없는 1회 호출, 기준별 IMPLEMENTED/MISSING/PARTIAL 판정은 PR diff 한정). 티켓 내용은 메인 리뷰 입력에 들어가지 않음. [03#q9](../reports/kodus-ai/03-incremental-memory-rules.md#q9) |
| **SaaS** (Q10) | **부분 지원**(서명·토큰 검증·이벤트 필터) / 큐·격리 **미지원.** GitHub HMAC·GitLab 토큰 검증 있음. 프로세스 내 `BackgroundTasks`, 큐·ack·재시도·실패 저장·테넌트 격리 계층 없음. 단일 운영자가 한 벌 자격증명으로 여러 저장소를 처리하는 구조. [04](../reports/pr-agent/04-saas-and-isolation.md) (Q10-1~5절) | **미지원 / 해당 없음**(단일 사용자 CLI). 서비스 워커화 시 분리할 TUI·홈 디렉터리·환경변수·전역 상태·`internal/` import 경계를 정리했음. [04#q10](../reports/open-code-review/04-saas-and-isolation.md#q10) | **부분 지원.** 트랜잭셔널 outbox + inbox + RabbitMQ 지연 재시도 + DLX + 리퍼 + 드레인은 견고. GitHub/GitLab/Bitbucket/Forgejo 웹훅 서명·시크릿 검증 없음(Azure만 공유 토큰), 조직 격리는 앱 수준(RLS 없음, 큐·outbox에 조직 컬럼 없음), 파이프라인 오류가 삼켜져 잡이 COMPLETED로 끝날 수 있음. [04](../reports/kodus-ai/04-saas-and-isolation.md) (1~3절) |
| **의존성** (Q11) ※ | Python 3.12+. base에 litellm(==1.104.0, 버전 결합 강함)·tiktoken 등, Provider SDK는 extras, 벡터 DB는 `similar-issue` 그룹. 필수 외부는 LLM API와 Git 호스팅 API뿐(DB·큐·샌드박스 요구 없음). `anthropic`은 `pr_agent/`에 직접 import 없음(LiteLLM 내부 사용 여부 미확인), `GitPython`은 GitHub/GitLab 경로에서 미사용. MIT. [05](../reports/pr-agent/05-dependencies.md) | Go 1.25 단일 정적 바이너리. 필수 외부는 LLM API + `git` + 로컬 git 저장소. 직접 의존 16개 모듈(SDK 2종, tiktoken-go, doublestar, Bubble Tea 계열 3(리뷰 엔진은 미의존), OTel 계열). MCP·AWS·cobra는 이 SHA에 없음. 해석 버전은 `go.sum` 대조(`go list`·`go mod graph` 미실행). Apache-2.0. [05](../reports/open-code-review/05-dependencies.md) | TypeScript/NestJS. 필수 PostgreSQL(+vector 확장), MongoDB, RabbitMQ(delayed-message 플러그인; 앱 요구이며 prod compose에는 서비스가 없고 외부 제공 가정은 추론, [05 §4.1](../reports/kodus-ai/05-dependencies.md#rabbitmq-compose)), `git`·`rg`, LLM API. E2B·Morph·Exa·Langfuse는 선택. 백엔드 의존성은 루트 `package.json`에 몰려 있고 선언만 있는 패키지 다수. **AGPL-3.0 + 상용 `ee/`**, 리뷰 파이프라인 조립·실행 진입·설정 로더·규칙 서비스가 ee. [05](../reports/kodus-ai/05-dependencies.md), [라이선스 경계](../reports/kodus-ai/05-dependencies.md#license) |

### 표기 메모 (※)

- **의존성 행**은 지원 수준이 아니라 "필수/선택 구성과 라이선스"를 적었다. 기능 대비 상세는 `dependency-matrix.md`(별도 문서)가 다룬다.
- **pr-agent 코드 접근**: 보고서 요약표는 "지원(변경 파일 한정)"이고 같은 문서가 "저장소 전체 접근 = 미지원"이라고 적는다. GUIDE 3.3절 정의(일부 경로만 있으면 부분 지원)에 맞춰 이 문서에서는 "부분 지원(변경 파일 한정)"으로 옮겼다.
- **kodus-ai 동적 탐색**: 보고서 표기는 "지원(조건부)". 샌드박스가 없으면 불가능하므로 GUIDE 3.3절 정의에 맞춰 "부분 지원(조건부)"로 옮겼다. 보고서가 명시한 `null` 샌드박스 경우(도구는 있지만 호출이 모두 오류)는 추론이다.
- **pr-agent 증분 리뷰 "지원(시각 기반)"**: 판정 기준이 kodus-ai보다 느슨하다. pr-agent도 오래된 결과 폐기가 없고 중복 방지가 프로세스 로컬·옵트인이며 시각 기반 비교는 리베이스·커밋 날짜에 취약하다(보고서 추론). kodus-ai(부분 지원)와 같은 기준으로 읽으면 둘 다 "부분 이상"이다. 둘의 라벨 차이를 기능 우열로 읽지 말 것.
- **kodus-ai 장기 메모리**: "피드백 학습 미지원"은 **Kodus가 게시한 댓글에 대한 반응·답글·resolve에서 파생하는 PR 간 학습**이 없다는 뜻이다. 사람 리뷰어의 PR 댓글에서 규칙을 만드는 cron(쓰기+읽기 있음)은 별개로 존재한다.

---

## 2. 항목별 차이의 핵심

1. **Agent Loop** — 세 레포가 다른 "루프의 단위"를 가진다. pr-agent는 루프 자체가 없고(단발 + 청크 병렬), open-code-review는 파일 하나의 대화 안에서 도구를 반복하며, kodus-ai는 고정 순서 파이프라인(약 18단계) 안의 한 단계(`AgentReviewStage`)가 finder/verifier 루프다. 종료·예산·취소 장치는 kodus-ai가 정책 객체로 가장 세분화돼 있고, open-code-review는 라운드·컨텍스트 비율·파일당 시간 3개 한도뿐이다.
2. **동적 탐색** — 탐색 수단은 모두 텍스트 검색 수준이다(pr-agent 없음, open-code-review `git grep`, kodus-ai `ripgrep` + call graph 문자열). 차이는 "누가 코드를 확보하느냐"다. open-code-review는 로컬 clone이 이미 있다고 가정하고, kodus-ai는 샌드박스 체크아웃을 직접 만들며(없으면 diff만), pr-agent는 clone 자체를 하지 않는다.
3. **코드 접근** — 세 곳 모두 리뷰 시작 시점의 SHA 하나로 모든 읽기를 고정하지 않는다(pr-agent는 수집 중 변경 감지만, open-code-review는 ref 이름 사용, kodus-ai는 읽기 지점마다 SHA가 다름). 접근 수단은 API(pr-agent) / 로컬 git(open-code-review) / API + 샌드박스(kodus-ai)로 갈린다.
4. **Diff 처리** — "주변 줄 확장"은 pr-agent에만 알고리즘이 있고(앞 5/뒤 1/동적 10줄), 나머지 둘은 확장 대신 모델의 파일 읽기에 맡긴다. 대형 변경 처리는 pr-agent(압축→청크)가 가장 두껍고, open-code-review는 큰 파일을 제외하고, kodus-ai는 파일 단위 배치로 나눈다. 인라인 위치 변환의 완성도는 pr-agent(GitHub·GitLab 모두)와 kodus-ai가 높고 open-code-review는 엔진 밖 예제 YAML에 있다.
5. **검증** — 세 곳의 검증기는 모두 "추가 근거를 다시 찾아 확인"하는 독립 단계가 아니다. open-code-review는 도구 없이 diff만 보고, pr-agent `/improve`는 같은 diff만 보며, kodus-ai는 도구는 있지만 같은 모델 슬롯이고 기본 KEEP이다. 자세한 비교는 [`context-strategies.md`](context-strategies.md) 3절.
6. **증분 리뷰** — 기준점이 제각각이다: 이전 리뷰 댓글 시각(pr-agent) / 없음(open-code-review) / 직전 SUCCESS 실행의 마지막 분석 커밋(kodus-ai). 세 곳 모두 실행 중 Head 변경 시 결과를 폐기·취소하지 않는다.
7. **장기 메모리** — 쓰기와 읽기가 둘 다 이어진 PR 간 메모리는 어디에도 "피드백 학습"으로는 없다. pr-agent는 한 PR 안, open-code-review는 기록만, kodus-ai는 학습 코드가 비활성이고 규칙형 메모리·사람 댓글 기반 규칙 생성만 동작한다.
8. **팀 규칙** — pr-agent는 git에 커밋된 설정 파일, open-code-review는 로컬 JSON 파일, kodus-ai만 DB(Mongo)에 저장·승인·감사 로그가 있다. 단 kodus-ai도 우선순위·버전·팀 범위가 없고 핵심 서비스가 ee다. 세 곳 모두 규칙을 "경로로 선별해 코드가 적용"하기보다 자연어 규칙을 프롬프트에 넣고 모델이 적용한다(kodus-ai는 detector가 후보를 LLM judge로 라우팅하는 정도).
9. **Jira** — 세 곳 모두 요구사항 텍스트를 넣는 단계에서 멈춘다. pr-agent는 메인 리뷰 입력에 넣고, kodus-ai는 별도 단계에서 diff 한정 판정을 하며 메인 입력에는 넣지 않고, open-code-review는 수동 `--background`다. "요구사항별로 저장소에서 구현 근거를 찾는 판정"은 없다.
10. **SaaS** — kodus-ai만 큐 기반 서비스 실행 구조를 갖췄다. pr-agent는 서버는 있으나 큐·격리가 없고, open-code-review는 CLI다. 서명 검증은 pr-agent(GitHub HMAC, GitLab 토큰)에는 있고 kodus-ai(Azure 제외)에는 없다는 점이 반대 방향의 차이다.
11. **의존성** — 운영 부담이 레포 성격대로 갈린다: open-code-review(바이너리 + git + LLM), pr-agent(Python + LLM + Git API), kodus-ai(Postgres·Mongo·RabbitMQ + git/rg + LLM + 라이선스 검토).

---

## 3. 세 레포 모두 "부분 지원" 또는 "미지원"인 영역 (= 직접 만들 영역)

이 절의 결론은 위 표에서 도출한 **분석자 정리**다. "없음"은 각 보고서가 밝힌 범위 안의 결론이다(검색 실패만으로 단정하지 않았다는 보고서의 전제를 따름). 우리 서비스에서 어떻게 채울지는 `adoption-for-us.md`에서 다룬다.

| 영역 | 세 레포의 상태 | 근거 |
|---|---|---|
| **Head SHA 고정 + 실행 중 새 푸시 시 취소·폐기** | pr-agent 게시 직전 재확인 없음 / open-code-review ref 이름 사용, 취소 경로 없음 / kodus-ai 읽기 지점마다 SHA가 다르고 취소 없음 | [pr-agent 03#q6](../reports/pr-agent/03-incremental-memory-rules.md#q6), [OCR 01#q2](../reports/open-code-review/01-execution-and-diff.md#q2), [kodus 01#q2](../reports/kodus-ai/01-execution-and-diff.md#q2) |
| **독립 검증자** (다른 모델·다른 문맥으로 추가 근거를 탐색하고, 근거 위치 없는 확정을 막음) | pr-agent 같은 diff만(`/improve`) / OCR diff만·도구 없음·통과 쪽으로 설계 / kodus-ai 도구는 있으나 같은 모델 슬롯·기본 KEEP | 각 보고서 Q5 |
| **심볼 단위 탐색** (참조·정의·구현체를 도구가 직접 이해) | pr-agent 탐색 도구 없음 / OCR `git grep` + 모델 추론 / kodus-ai `rg` + 외부 CLI가 만든 call graph를 고정 문맥으로 주입(`getCallers`는 문자열 파서) | 각 보고서 Q3 |
| **변경하지 않은 코드에서 발견한 결함 보고 허용** | 세 곳 모두 보고 대상을 변경 줄에 묶는다(pr-agent 추측 금지 프롬프트, OCR "다른 파일 발견 무시", kodus-ai hunk와 겹치지 않으면 폐기). 상세는 `context-strategies.md` 4절 | 각 보고서 Q3 |
| **파일 간 종합 리뷰** | pr-agent 청크는 독립 호출, OCR 파일별 대화 분리·종합 패스 없음, kodus-ai 배치는 그 배치 diff만 봄(전체 체크아웃은 도구로 접근 가능) | pr-agent 02#q3 3.4절, OCR 02#q3 3.5절, kodus 02#q3 3.5절 |
| **Kody/봇 댓글에 대한 사용자 반응(답글·반박·resolve·수정)에서 파생하는 PR 간 메모리** (쓰기→저장→조회→수명 관리) | pr-agent 같은 PR 안만 / OCR 기록만 / kodus-ai 반응 카운터 수집·임베딩 필터 코드가 있으나 비활성. 세 곳 모두 신뢰도·만료·충돌 처리 없음 | 각 보고서 Q7 |
| **Jira 요구사항별 구현 근거 판정 + 이번 PR 범위 구분** | pr-agent 텍스트 입력 + diff 한정 판정 / OCR 수동 텍스트 / kodus-ai diff 한정 판정(저장소 근거 탐색 없음). 이번 PR 범위 구분은 세 곳 모두 없음 | 각 보고서 Q9 |
| **팀 규칙 관리** (우선순위·충돌 해결, 버전 이력, 팀 범위, 코드가 경로로 규칙을 선별) | 세 곳 모두 일부 없음. kodus-ai만 저장·승인·감사가 있으나 구현이 ee | 각 보고서 Q8 |
| **웹훅 서명 검증 + 테넌트 격리 + 장애 복구를 모두 갖춘 서비스 기반** | pr-agent: 서명은 있고 큐·격리 없음 / OCR: 해당 없음 / kodus-ai: 큐·복구는 있고 서명 없음, 격리는 앱 수준 | 각 보고서 Q10 |
| **실행당 토큰·금액 상한과 취소 제어** | OCR·kodus-ai는 실행당 총량 상한 없음을 확인. pr-agent는 호출 수·입력 토큰 상한(청크 3, 재시도 2, `max_model_tokens`)은 있으나 금액 상한은 확인하지 못함 | OCR 04#q10, kodus 02#q4, pr-agent 02#q4 |

---

## 4. 이 문서의 신뢰도와 보고서 간 불일치

### 4.1 검증 강도가 낮은 부분

- **kodus-ai 줄 번호**: 2026-10-13 보고서 정정에서 02~05의 `path:range` 인용(02 약 198, 03 약 205, 04 약 155 중 약 150, 05 약 95, 합계 약 650개)을 모두 열어 범위·식별자를 대조했고 약 30건을 정정했다. **아직 재대조하지 못한 범위**: 01 전체, 02의 긴 범위(`agent-tools.factory.ts:300-1757`, `agent-review.stage.ts:992-1508` 등), 03·04의 긴 범위(경계·핵심 식별자만 확인), 05의 파일명만 인용한 `agent-tools.factory.ts`·`structured-output-repair.ts`(각 문서 머리와 [`next.md`](../reports/kodus-ai/next.md) 참조). 이 문서가 인용하는 근거는 모두 링크로만 연결했으며, 그 범위의 줄은 인용 전에 다시 열 것. kodus-ai 문서 머리의 검증 수준 숫자는 검증 열이 있는 표의 행을 스크립트로 센 값(2026-10-13 재집계)이다.
- **세 보고서 모두 실행 확인 0건**: 루프 종료 양상, 오탐률, 실제 모델 행동은 확인되지 않았다.
- **open-code-review 의존성의 해석 버전**은 `go.sum` 대조이며 모듈 그래프 명령은 실행하지 않았다(`../reports/open-code-review/05-dependencies.md` 상단).

### 4.2 이 문서 작성 중 `repos/`를 읽기 전용으로 직접 다시 확인한 것

세 레포 모두 `git rev-parse HEAD`가 `repos.lock.tsv`와 일치함을 확인했다. 아래는 보고서 주장과 일치했다(상세는 `context-strategies.md` 5절).

- open-code-review: 도구 이름 목록(`internal/tool/definitions.go`), "도구 호출 없음 → 재요청" 분기, 최대 라운드 소진 시 `nil` 반환, Review Filter가 `Tools` 없이 호출됨(`internal/agent/agent.go`), `DiffContextLines = 3`.
- kodus-ai: 파이프라인 단계 목록(KodyFineTuning 단계 없음), `buildAgentTools`가 `remoteCommands` 없으면 `{}` 반환, verifier가 finder와 같은 `modelId`·`tools`로 생성됨, 완료 게이트가 `criticalTotal > 0`일 때만 거부, `RunStatus` 값, `finishReason` 불일치.
- pr-agent: 주변 줄 확장 기본값과 동적 문맥 탐색 루프, `/improve`의 자기 반성 호출 구조.

### 4.3 보고서 간 모순·불일치 (이 문서 작성 중 발견)

| # | 내용 | 위치 | 처리 |
|---|---|---|---|
| 1 | open-code-review 도구 개수 표기: **정정 완료.** 기준은 [OC 00 1절](../reports/open-code-review/00-overview.md)(`Tool` 값 7개 = 모델 호출 가능 6개 + 내부 `Unknown` 1개, Provider 등록 5개, `task_done`은 직접 처리). 이 문서의 "모델이 호출하는 도구 6개(task_done 포함)"와 일치 | OC 00 1절 | 정정 완료 |
| 2 | 증분 리뷰 판정 기준이 레포마다 다르다(위 표기 메모) | pr-agent 00 5절 vs kodus 00 5절 | 라벨을 그대로 옮기고 메모를 붙임 |
| 3 | open-code-review `02`·`01`·`03`은 앵커를 `{#q3}` 형식으로 쓰고 pr-agent·kodus-ai는 `<a id>`를 쓴다. 일부 마크다운 렌더러(GitHub 포함)에서는 `{#q3}`가 앵커로 동작하지 않을 수 있다 | OCR 보고서 | 이 문서도 같은 `#q3` 형식으로 링크했다. 링크가 안 맞으면 절 제목으로 이동할 것 |
| 4 | 문서 머리의 검증 수준 집계: 각 보고서가 2026-10-13에 집계 기준을 머리에 명시하고 재집계했다. 기준은 레포마다 다르다(open-code-review: 증거 표 행 단위·검증 칸 첫 판정, pr-agent: 머리 줄 제외 본문 문자열 출현 횟수, kodus-ai: 검증 열이 있는 표의 행 스크립트 집계) | 각 보고서 머리 | 이 문서는 집계 숫자를 쓰지 않았고, 레포 간 숫자는 비교하지 말 것 |
| 5 | kodus-ai 재시도 횟수가 코드·문서·설정마다 다르다(핸들러 상수 2 / 설정 로더 기본 5 / `.env.example` 3 / `AGENTS.md` "max 5"). 실효값은 런타임 미관측 | kodus 00 7절, 04 2.2절 | 이 문서는 재시도 횟수를 비교 칸에 쓰지 않았다 |
| 6 | kodus-ai 문서·주석 불일치(verifier 프롬프트 "4 tool-call steps" vs 설정 5/10, `evals/kody-rules/README.md`의 "same agent loop" vs 도구 없는 judge 등)가 보고서 안에 이미 기록돼 있다 | kodus 00 7절, 02 5.2절 | 코드 기준 값을 사용 |
| 7 | open-code-review `02` 3.3절의 "`code_search`의 `--max-count`는 파일당 상한이라 도구 설명과 어긋난다"는 git 동작에 근거한 **추론**이며 실행으로 확인되지 않았다(`next.md` 체크리스트에 있음) | OCR 02, next | 이 문서에서 인용하지 않음 |

### 4.4 판단하지 않은 것

- 점수·순위, "어느 레포가 더 낫다"는 결론은 쓰지 않았다.
- 보고서에 없는 사실은 추가하지 않았다. 위 4.2의 직접 확인은 보고서 주장의 재대조이지 새 사실 추가가 아니다.
