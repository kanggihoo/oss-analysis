---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
---

# Next Session Plan: promptfoo

- **상위 개요**: [overview.md](./overview.md)
- **목적**: 내 스킬(SKILL.md)을 여러 모델에서 평가하고, 개선하고, 모델 적합도를 기록하는 환경을 만드는 데 쓸 부분의 원본 동작을 스펙으로 정리한다. 승인 범위와 제외 행은 overview 1절.

---

## 1. 이번 세션에서 확인한 범위

기능 스펙 15개를 모두 썼고 전부 `ready`다(실행 확인은 없고 코드 읽기와 일부 테스트 사례명 기준).

- 공유 계약: [provider-contract](./capabilities/provider-contract.md), [skill-calls-metadata](./capabilities/skill-calls-metadata.md), [eval-records](./capabilities/eval-records.md), [default-providers](./capabilities/default-providers.md)
- 기능: [config-loading](./capabilities/config-loading.md)(설정 스키마 계약 포함), [assertion-family](./capabilities/assertion-family.md)(어서션 핸들러 계약 포함), [model-graded-matchers](./capabilities/model-graded-matchers.md), [agent-providers](./capabilities/agent-providers.md), [response-cache](./capabilities/response-cache.md), [script-bridges](./capabilities/script-bridges.md), [generate-datasets](./capabilities/generate-datasets.md), [eval-run](./capabilities/eval-run.md), [results-store](./capabilities/results-store.md), [prompt-optimize](./capabilities/prompt-optimize.md), [web-ui](./capabilities/web-ui.md)(범위 제한: 결과 조회·비교·평점 API와 화면)

---

## 2. 해결되지 않은 남은 질문 (확인 한계)

외부 라이브러리·SDK 동작이거나 실행이 필요해 코드 읽기로 닫지 못한 것이다.

- [ ] Claude Agent SDK의 스킬 발견·로딩, 사용자 홈 스킬 노출 여부, 권한 모드 실제 동작 (agent-providers, skill-calls-metadata)
- [ ] Codex SDK의 `sandbox_mode`·`approval_policy` 기본값, OpenCode SDK의 `{error}` 던짐/반환 (agent-providers)
- [ ] Node `execFile` 오류 `message`에 stdout이 들어가는지(Go provider 오류 문구) (script-bridges R-19)
- [ ] commander `--no-cache`에 기본값을 줄 때 `cache` 기본이 false가 되는지 (generate-datasets R-06, 추론)
- [ ] zod `prefault(0)`이 CLI `--delay` 생략 시 0을 채워 설정 파일 `delay`가 CLI 경로에서 도달하지 않는지 (eval-run)
- [ ] `{{env.X}}` 렌더 값이 `evals.config`에 실제로 저장되는지 (results-store R-37, 추론: 환경변수 참조로 쓴 API 키가 DB에 남을 가능성)
- [ ] `listen(port)` host 미지정 시 모든 인터페이스에 바인딩되는지 (web-ui, Node 문서 기반 추론)
- [ ] 같은 입력으로 `--suggest-prompts`를 n회 부를 때 캐시 키가 같아 같은 변형이 나오는지 (eval-run R-12)

---

## 3. 기능 스펙 후보 (승인 범위 밖)

| 기능 | 근거 | 상태 |
|---|---|---|
| `agent-workspace` (`copy_working_dir`, `workspaceDiff`) | `src/providers/agentWorkspace.ts`(773줄), agent-providers R-52·R-53 | **사용자 결정 대기.** 에이전트가 파일을 어떻게 바꿨는지 기록하는 데 직접 쓸 부분. 지금은 요약만 있음 |
| 비밀 정제(sanitizer) 공유 계약 | `src/util/sanitizer.ts`, results-store R-37~R-41, web-ui | 후보. 저장·출력·공유·서버가 같이 쓴다 |
| 트레이스 기반 어서션(`trajectory:*`) | `src/assertions/trajectory.ts`, model-graded-matchers 보고 | 후보. 도구 호출 순서·인자·단계 수 채점 |
| 스케줄러 | `src/scheduler/*`, eval-run R-25 | 후보. 동시성 적응, 429 재시도 |
| `repeatStability` 점수 분산 | eval-run R-52 | 원본은 Wilson 구간뿐. 점수 분산은 직접 설계 |
| 커스텀 타깃 provider(http 등), Node API, 레드팀 | overview 지도 | 범위 밖 |

---

## 4. 다음에 볼 곳

이 레포의 스펙 작성은 끝났다. 다음 단계는 스펙이 아니라 **환경 설계**다. promptfoo에서 가져올 것과 직접 만들 것을 나눈다.

- 직접 만들어야 하는 것(원본에 없음, 스펙으로 확인): 모델·스킬 버전별 시간순 조회와 회귀 계산, 심판 점수 안정성 측정(반복·순서 교대·심판 교체), 자기 채점 회피, 평가 실행에 라벨을 붙여 나중에 거르는 방법, 채점 모델 비용 기록.
- 먼저 정할 것: `promptfoo view`를 그대로 쓸지, API만 재사용하거나 대시보드를 새로 만들지(web-ui 적용 메모).

---

## 5. 참고 사항

- 이번 세션에서 선행 스펙 정정 3건이 있었다: config-loading의 변수 파일 오류 시점, provider-contract의 `PROMPTFOO_DELAY_MS` 도달 경로, eval-run의 `--suggest-prompts` 호출 수. 각각 해당 스펙 2.1에 이력이 있다.
- 지도 행 이름 보정 후보: "에이전트 SDK 프로바이더 + 스킬 호출 메타"는 skill-calls-metadata가 별도 스펙으로 빠졌으니 "에이전트 SDK 프로바이더"로 줄일 수 있고, Codex app-server·Codex Security도 `skillCalls` 생산자다.
