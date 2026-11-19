---
sha: "4afe78de1e51162c01c946dcf080e6a266685a01"
created: 2026-11-17
updated: 2026-11-17
sources:
  - package.json
  - packages/ai/src/models.generated.ts
  - packages/ai/src/providers/openai.models.ts
---

# Q9: 테스트를 제외한 소스 코드 줄 수

- **결론 (`코드 확인`, 파일 집계)**: 현재 checkout의 `packages/*/src`와 `apps/*/src`에서 평가 패키지, 테스트·fixture·예제, 파일 첫 3줄에 자동 생성 표시가 있는 파일을 제외하면 **294,645줄, 1,244개 파일**이다. 기존 학습 순서인 `ai`·`agent`·`coding-agent` 세 패키지는 **113,990줄**이다. 공백 줄과 주석을 포함한 물리적 줄 수다.

| 범위 | 전체 줄 | 공백 아닌 줄 | 파일 |
|---|---:|---:|---:|
| packages/ai | 28,188 | 25,795 | 166 |
| packages/agent | 2,548 | 2,315 | 6 |
| packages/coding-agent | 83,254 | 75,428 | 268 |
| 위 세 패키지 합계 | 113,990 | 103,538 | 440 |
| 나머지 packages와 apps | 180,655 | 167,154 | 804 |
| 전체 | 294,645 | 270,692 | 1,244 |

## 집계 기준과 한계

- `git ls-files`가 나열한 현재 작업트리 파일 중 `packages/*/src/**`, `apps/*/src/**`만 센다. checkout은 위 SHA이고 작업트리는 집계 전 clean이었다. `package.json`의 workspaces와 build 목록을 보고 범위를 정했다 (`코드 확인`).
- 확장자 `ts`, `tsx`, `js`, `jsx`, `mjs`, `cjs`, `css`, `rs`, `c`, `h`, `cc`, `cpp`만 포함한다. `.d.ts`, 경로의 `test`, `tests`, `__tests__`, `fixtures`, `__fixtures__`, `examples`, `generated`, 파일명의 `.test.`·`.spec.`, `packages/evals`를 제외한다.
- 첫 3줄에 `auto-generated` 또는 `automatically generated`가 있는 파일 44개, 918줄을 제외했다. `models.generated.ts`와 `providers/openai.models.ts`는 실제로 자동 생성 표시가 있다 (`코드 확인`). 표시가 없는 생성물은 남을 수 있다.
- `src` 바깥의 런타임 파일, 선언 파일, JSON 등 데이터는 빠진다. 반대로 `src`의 개발용 코드나 사용되지 않는 코드가 남을 수 있다. 각 파일의 실행 도달성이나 주석만인 줄은 검사하지 않았으므로 실제 실행되는 명령문 수가 아니라 **규칙 기반 대략치**다 (`추론`).
- 재현: 작업 공간 루트에서 `python3 artifacts/pi/line-count/count.py`. 이 스크립트는 checkout의 현재 파일을 읽으므로 이후 수정 시 결과가 달라진다.

기능의 진입점·핵심 처리·실패 처리를 조사한 질문이 아니므로 기능 스펙 트리거는 없다.
