구직자가 서류 통과 이후 최종 합격까지 도달할 수 있도록 돕는 **면접 준비(Interview Preparation) 및 경험 은행(Story Bank) 시스템**에 대해 정리해 드립니다.

이 하위 시스템은 일회성 면접 대비에 그치지 않고, **구직자가 채용 공고를 분석할 때마다 개인의 강점 스토리를 데이터베이스에 지속적으로 누적하여 구직 활동이 반복될수록 면접 역량이 점진적으로 향상되도록 설계**된 누적형 시스템입니다.

---

## 1. 지속 축적형 경험 데이터베이스: `story-bank.md`

이 시스템의 핵심 저장소는 [story-bank.md](file:///Users/kkh/Desktop/oss-analysis/artifacts/career-ops/interview-prep/story-bank.md) 파일입니다. 

### 1) STAR+R 프레임워크 (성찰 요소의 도입)
일반적인 STAR 기법(Situation, Task, Action, Result)에 **`Reflection (성찰)`** 요소를 결합한 **STAR+R** 양식을 강제합니다.
*   **성찰(Reflection)의 목적**: 주니어는 "무엇을 했는가(Result)"에 집중하는 반면, 시니어/스태프급 인재는 "무엇을 배웠고, 다시 한다면 어떤 부분을 개선할 것인가"를 설명할 수 있어야 합니다. AI는 이 성찰 영역을 정교하게 다듬어 지원자의 시니어리티(경력의 깊이)를 강조합니다.

### 2) 스토리 harvesting(수집) 및 누적 플로우
1.  **평가 단계**: 사용자가 단일 공고 평가([modes/oferta.md](file:///Users/kkh/Desktop/oss-analysis/artifacts/career-ops/modes/oferta.md))를 돌리면, AI가 **Block F (Interview Plan)** 섹션에서 해당 공고 요구사항에 맞는 면접용 STAR+R 시나리오를 6~10개 자동 생성합니다.
2.  **데이터베이스 누적**: AI는 생성된 스토리가 기존 [story-bank.md](file:///Users/kkh/Desktop/oss-analysis/artifacts/career-ops/interview-prep/story-bank.md)에 이미 존재하는지 대조한 뒤, **존재하지 않는 새로운 성공 스토리일 경우 데이터베이스 하단에 실시간으로 보존(Harvesting)하여 축적**합니다.
3.  **구조화 분할**: 축적된 스토리들은 `Conflict(갈등 해결)`, `Leadership(리더십)`, `Technical Debt(기술 부채 해결)` 등의 **행동 주제(Theme)별로 정리**되어 면접 직전 구직자가 필요한 질문 유형에 맞춰 즉시 꺼내 연습할 수 있게 돕습니다.

---

## 2. 직무 유형(Archetype)별 스토리 프레이밍

AI는 식별된 공고의 아키타입(Archetype)에 맞추어 사용자의 동일한 프로젝트 경험이라도 강조하는 포인트를 완전히 다르게 가공하여 면접 대비책을 세워 줍니다.

*   **AI Forward Deployed (고객 현장 배포)**: 프로토타입 설계부터 프로덕션 배포까지의 **'배포 속도'** 및 **'고객 직면 비즈니스 임팩트'**를 강조.
*   **AI Solutions Architect (솔루션 아키텍트)**: 복잡한 엔터프라이즈 환경에서의 **'아키텍처 트레이드오프 결정'** 및 **'시스템 연동/통합성'**을 강조.
*   **AI Platform / LLMOps**: 대규모 실서비스의 **'성능 지표(Metrics)'**, **'평가 시스템(Evals)'**, **'모니터링 신뢰성'**을 강조.
*   **Agentic / Automation (에이전트 설계)**: 멀티 에이전트 오케스트레이션 설계 시의 **'예외 처리'** 및 **'HITL(인간 개입 루프)'** 설계를 강조.
*   **Technical AI PM**: 비즈니스 가치 발굴(Discovery) 및 **'제품 기획 의사결정의 논리'**를 강조.

---

## 3. 기업 밀착형 정보 조사 도구 (`deep.md` & `interview-prep.md`)

서류 합격 후 면접 일정이 잡혔을 때, AI가 기업의 깊숙한 핵심 정보와 면접관의 성향을 리서치하도록 돕는 두 가지 특화 모드가 작동합니다.

### 1) 심층 리서치 프롬프트 빌더 ([modes/deep.md](file:///Users/kkh/Desktop/oss-analysis/artifacts/career-ops/modes/deep.md))
구직자가 Perplexity나 ChatGPT Plus 같은 최 고성능 추론 AI 시스템에 직접 입력할 수 있는 **'심층 기업 분석용 명령문(Prompt)'을 고도로 합성하여 출력**해 줍니다.
*   **6대 분석 도메인**: 
    1. AI 전략(기술 블로그 분석 및 사용 중인 ML 스택 추적)
    2. 기업 동향(최근 6개월간의 투자 유치, 경영진 교체 여부)
    3. 엔지니어링 문화(배포 주기, 모노레포 사용 여부 등)
    4. 잠재적 병목(시스템 안정성 및 스케일링 비용 문제 이슈 탐지)
    5. 시장 경쟁력(경쟁사 대비 기술적 해자)
    6. 이력 매핑(구직자의 이력이 기업의 당면 과제를 해결하는 포지셔닝 설계)
*   **언어 자동 판별**: 사용자가 설정한 [config/profile.yml](file:///Users/kkh/Desktop/oss-analysis/artifacts/career-ops/config/profile.yml)의 거주 언어나 현재 프롬프트 언어를 추적하여 리서치 명령문을 최적의 언어로 자동 출력합니다.

### 2) 면접관 맞춤형 전략 수집 ([modes/interview-prep.md](file:///Users/kkh/Desktop/oss-analysis/artifacts/career-ops/modes/interview-prep.md))
*   **Recruiter 면접 대비**: Glassdoor/Levels.fyi 정보를 크롤링하여 연봉 밴드 정보를 파악하고 인사담당자의 프로세스 타임라인에 대응합니다.
*   **Hiring Manager 면접 대비**: 회사의 기술 블로그와 제품 로드맵을 웹 스크랩하여 채용을 결정하는 매니저의 핵심 가려운 부분을 긁어줄 준비를 합니다.
*   **Peer(엔지니어 팀원) 면접 대비**: LeetCode 예상 빈출 유형, Blind 사이트의 실제 면접 후기 및 기술 질문 허들을 크롤링하여 면접 방어벽을 세웁니다.