# packages/agent 파일 역할 정리 (소스 읽기 전용 가이드)

이 문서는 `repos/pi/packages/agent` 내 55개 파일의 역할을 `fork` 후 구현 흐름을 이해하기 쉽도록 정리한 것입니다.

- 기준: `git ls-files packages/agent/` 기준 55개 파일
- 마지막 커밋 기준(현재 저장소): `packages/agent`는 `@earendil-works/pi-agent-core` 패키지
- 범위: 기능 구현/동작 이해에 필요한 핵심 개요(테스트 커버리지 상세 동작은 테스트 파일 내에서 확인)

---

## 전체 구조 한눈에 보기

`agent` 패키지는 큰 흐름이 3층입니다.

1. **런타임 API 층**: `Agent`/`agent-loop`로 실제 대화-생성-도구실행의 기본 동작을 담당
2. **상태/세션/수명관리 하네스 층**: `AgentHarness`, session 저장소, compaction/branch summary, 훅/리소스/스킬/세션 이벤트로 영속성과 구조화 보장
3. **테스트/문서 층**: 동작 보장과 설계 의도 기록

아래는 각 파일 역할입니다.

---

## 1) 패키지 메타/문서

- `packages/agent/README.md`
  - 패키지 전체 개요, 설치/사용법, API 노출 포인트, 사용 예시, 의도 정리
  - `fork` 후 먼저 읽을 입문 문서

- `packages/agent/CHANGELOG.md`
  - 버전별 변경 이력
  - API/동작 영향이 큰 변경 추적용(안정성 판단 근거)

- `packages/agent/package.json`
  - 패키지 메타데이터, 의존성, 빌드/테스트 스크립트, exports
  - `@earendil-works/pi-agent-core`가 어떤 entrypoint(`dist/index.js`, `dist/index.d.ts`)를 배포하는지 정의

---

## 2) 핵심 문서(구현 방향/설계 의사결정)

- `packages/agent/docs/agent-harness.md`
  - `AgentHarness`의 라이프사이클 규칙, phase(`idle/turn/...`), 세션 플러시 규칙, 테스트 조직 가이드
  - 실제 구현이 따라가야 할 핵심 제약 조건 기록

- `packages/agent/docs/durable-harness.md`
  - 세션 로그 기반의 반영구성 모델, 복구 정책(마지막 동작 미완료 처리) 설계
  - 어떤 상태를 durable로 둬야 하는지, 어떤 건 세션 기반으로 복구 가능한지 정리

- `packages/agent/docs/hooks.md`
  - 이벤트/훅 타입 설계 및 `observe`/`on`/`emit` 처리 규칙
  - 결과 반환형 이벤트를 가진 훅 체이닝 방식, 확장성 포인트

- `packages/agent/docs/observability.md`
  - 트레이스/스팬 개념, 이벤트 설계, `pi.ai`/`pi.agent` 이벤트 이름 규칙 제안
  - 추적/메트릭 연동을 위한 구조

---

## 3) 진입점 및 공용 API

- `packages/agent/src/index.ts`
  - 공개 API barrel(`export *`).
  - 상위 앱에서 임포트할 진입점의 중심

- `packages/agent/src/node.ts`
  - Node 런타임용 진입점. Node 의존 환경에서 `NodeExecutionEnv`를 노출
  - 브라우저/Node 호환성 구분 포인트

- `packages/agent/src/types.ts`
  - `AgentMessage`, 이벤트 타입, 도구/큐/라이프사이클 등 **공통 타입 정합성**의 핵심
  - `Agent` 수준의 핵심 타입을 정의해 하네스/테스트와 인터페이스를 고정

---

## 4) 에이전트 핵심 동작

- `packages/agent/src/agent.ts`
  - `Agent` 클래스(유저 관점 API)의 본체
  - 상태 보관(`state`), 실행 API(`prompt`/`promptFromTemplate`/`nextTurn` 등), 이벤트 구독, 도구 큐(steering/follow-up), Abort/재시도 진입점
  - 기본 동작의 기본형을 익히기에 핵심 파일

- `packages/agent/src/agent-loop.ts`
  - 실제 턴 루프(LLM 호출 + 메시지 스트림 처리 + 도구 실행 + 다음 턴 여부 판정)
  - `agent-loop` vs `agentLoopContinue` 분리로 초기 프롬프트 진입과 이어지는 재시작 동작 구분

- `packages/agent/src/proxy.ts`
  - 외부 LLM 프록시 서버 경유 스트림 처리용 유틸
  - 직접 모델 호출이 아닌 앱이 프록시 서버를 쓰는 경우의 경량 진입점

- `packages/agent/src/harness/messages.ts`
  - 메시지 변환/포맷 유틸(요약 메시지 prefix/suffix 생성, bash 출력 텍스트 변환 등)
  - 대화 기록의 시스템 메시지/요약 메시지 표준 형식 담당

- `packages/agent/src/harness/system-prompt.ts`
  - 스킬 목록 등을 시스템 프롬프트로 형식화해 모델에게 전달
  - 모델에게 넘길 컨텍스트 조립 포인트

- `packages/agent/src/harness/prompt-templates.ts`
  - `prompt` 템플릿 로딩(`loadPromptTemplates`), 서브소싱, 인자 치환, 파싱
  - 템플릿 기반 실행 입력 생성

- `packages/agent/src/harness/skills.ts`
  - `skill` 로딩, 템플릿 포맷팅(`formatSkillInvocation`), 진단 메시지 처리
  - 에이전트가 특정 명령/절차를 수행할 때 필요한 리소스 파싱 담당

---

## 5) 상태/세션 하네스(가장 중요한 구조화 포인트)

### 하네스 본체

- `packages/agent/src/harness/agent-harness.ts`
  - `AgentHarness` (트랜잭션/세션/설정/리소스/훅/스트림 옵션/운영 phase 제어)
  - 대규모 아키텍처를 이해할 때 가장 중요한 “운영 오케스트레이터”
  - `Agent`보다 상위 수준에서 session durability/phase(운영 상태), queue 정합성, compaction/이동(branch navigation) 등을 관리

### compaction 관련

- `packages/agent/src/harness/compaction/compaction.ts`
  - 대화 압축(compaction) 실행, 언제 압축할지 판단, summary 생성 준비 등
  - 긴 context 또는 메모리 한계 대응 핵심 로직

- `packages/agent/src/harness/compaction/branch-summarization.ts`
  - 브랜치 요약 생성(과거 경로 정리), summary 메시지 생성/수집
  - 트리 기반 세션에서 요약이 필요한 시나리오 지원

- `packages/agent/src/harness/compaction/utils.ts`
  - compaction/branch 처리에서 파일 경로 집계 유틸, 메시지에서 파일 오퍼레이션 추출 등 보조

### 세션 저장/저장소 계층

- `packages/agent/src/harness/session/types.ts` *(경로: 타입 파일은 `src/harness/types.ts` 전체에 통합)*
  - 여기서 다루는 타입(세션 entry, 에러, hooks 이벤트 result/error 코드 포함)이 session/harness 전반의 계약을 고정

- `packages/agent/src/harness/session/session.ts`
  - 세션 도메인 객체(트리 entry 파생, 메시지/라벨/커스텀 엔트리/leaf 이동 등) 계층의 핵심
  - 세션 mutation API의 동작 규칙 정리

- `packages/agent/src/harness/session/repo-utils.ts`
  - 세션/entry 헬퍼(아이디 생성, fork를 위한 경로 계산, 파일시스템 에러 변환)
  - repo 계층에서 중복 사용하는 순수 로직 모음

- `packages/agent/src/harness/session/memory-storage.ts`
  - 메모리 상의 SessionStorage 구현
  - 테스트/임시 실행에서 빠르게 session 동작 확인

- `packages/agent/src/harness/session/jsonl-storage.ts`
  - JSONL 기반 durable storage의 실제 입출력 파서/저장 구현
  - 헤더/엔트리 유효성 검증, 엔트리 append, entry 조회 흐름

- `packages/agent/src/harness/session/memory-repo.ts`
  - session 저장소 레이어의 in-memory 버전
  - 생성/열기/listing/forking을 메모리로 수행

- `packages/agent/src/harness/session/jsonl-repo.ts`
  - session repository 레이어의 durable 버전
  - JSONL 파일 기반 저장소 생성/열기/목록/메타 관리

- `packages/agent/src/harness/session/uuid.ts`
  - uuidv7 생성 유틸
  - entry id 생성 및 충돌 회피에서 사용

---

## 6) 실행환경/도구/유틸

- `packages/agent/src/harness/env/nodejs.ts`
  - Node 전용 환경 어댑터 (`spawn`, shell, 파일시스템, 시간 계산 등)
  - 브라우저/Node 분기 설계의 핵심 진입점

- `packages/agent/src/harness/utils/shell-output.ts`
  - shell 출력 캡처, 출력 제한/정리 유틸
  - 도구 실행 결과가 과도하게 커지는 것을 제어

- `packages/agent/src/harness/utils/truncate.ts`
  - 텍스트/바이트 기반 truncation utility
  - 로그·도구출력 안정적으로 자르는 공통 함수

---

## 7) 테스트/스크립트/도구 (실행 검증, 수정 영향도 판단에 중요)

- `packages/agent/test/agent-loop.test.ts`
  - 저수준 루프 동작(`agent-loop`) 전반 테스트

- `packages/agent/test/agent.test.ts`
  - `Agent` 공개 API 및 상태 변경/이벤트 경로 테스트

- `packages/agent/test/e2e.test.ts`
  - faux provider 기반 end-to-end 동작 보증

- `packages/agent/test/harness/agent-harness.test.ts`
  - `AgentHarness` 핵심 lifecycle, compact/navigate/session write 흐름 테스트

- `packages/agent/test/harness/agent-harness-stream.test.ts`
  - 스트림 옵션/훅이 있는 하네스 실행 경로 테스트

- `packages/agent/test/harness/compaction.test.ts`
  - compaction/branch 요약 경로 회귀 테스트

- `packages/agent/test/harness/nodejs-env.test.ts`
  - `NodeExecutionEnv`의 파일/쉘 관련 동작 검증

- `packages/agent/test/harness/prompt-templates.test.ts`
  - 템플릿 로딩/포맷팅/구문/에러 경로 검증

- `packages/agent/test/harness/repo.test.ts`
  - repo 계층(in-memory/jsonl) 기본 동작 테스트

- `packages/agent/test/harness/resource-formatting.test.ts`
  - prompt template/skill 포맷팅 헬퍼 결과 형식 검사

- `packages/agent/test/harness/session.test.ts`
  - session 객체/스토리지 경로 테스트

- `packages/agent/test/harness/session-uuid.test.ts`
  - uuidv7 생성 규격/시간 단조성 검증

- `packages/agent/test/harness/storage.test.ts`
  - 저장소 입출력/메타/entry append 일관성 테스트

- `packages/agent/test/harness/session-test-utils.ts`
  - 테스트에서 공통으로 쓰는 메시지/임시디렉토리 헬퍼
  - 테스트 유지보수 시 재사용되는 내부 도구

- `packages/agent/test/harness/skills.test.ts`
  - skill 로딩 파이프라인 검증

- `packages/agent/test/harness/system-prompt.test.ts`
  - 시스템 프롬프트 포맷 변환 규칙 검증

- `packages/agent/test/harness/truncate.test.ts`
  - truncation 동작의 경계값/안전성 테스트

- `packages/agent/test/scratch/simple.ts`
  - 실험/수동 확인용 스크립트(정식 테스트 아님)

- `packages/agent/test/utils/calculate.ts`
  - 예시 계산 툴 정의(테스트에서 계산 툴 동작 확인용)

- `packages/agent/test/utils/get-current-time.ts`
  - 테스트용 시간 툴 도구(예시/헬퍼)

---

## 8) 빌드/테스트 설정

- `packages/agent/tsconfig.build.json`
  - 빌드용 TS 설정, 출력 경로, 경로 별칭(`@earendil-works/pi-ai` 참조)

- `packages/agent/vitest.config.ts`
  - 기본 Vitest 실행 규칙

- `packages/agent/vitest.harness.config.ts`
  - 하네스 테스트만 별도 실행하도록 include/coverage 설정 분리

---

## 9) `fork` 후 공부/구현을 위해 추천하는 읽는 순서

1. `README.md` → 패키지 전반 목적 파악
2. `src/index.ts`, `src/types.ts`, `src/node.ts` → 공개 API/타입/진입점 파악
3. `src/agent.ts` + `src/agent-loop.ts` → 에이전트 실행 기본 루프 이해
4. `src/harness/agent-harness.ts` + `src/harness/session/session.ts` + session 계열 파일들 → 영속성/복구성 이해
5. `src/harness/compaction/*` → 대화 압축/요약/트리 이동 규칙 이해
6. 관련 테스트 파일(`test/harness/*.test.ts`, `test/*.test.ts`)로 동작 검증 루프 확인

---

## 참고

- 현재 기준으로 테스트/소스 역할을 분리하면, `packages/agent`는 총 55개 파일 중
  - 문서/설정 11개(README/CHANGELOG/docs/package scripts/config)
  - 실행 코드 20개
  - 테스트/테스트 유틸 24개
  정도로 나눠 볼 수 있습니다.
- 위 분류는 동작 구조를 이해하기 위한 “의미 기반 지도”입니다. 실제 수정 시에는
  1) 타입 계약(`src/harness/types.ts`, `src/types.ts`) 먼저,
  2) 상태 경계(`session` 계열),
  3) 공개 API(`agent.ts`)를 역순이 아닌 **타입→상태→API** 순으로 고치는 게 충돌을 줄입니다.
