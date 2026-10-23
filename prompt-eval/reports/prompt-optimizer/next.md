---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
---

# Next Session Plan: prompt-optimizer

- **상위 개요**: [overview.md](./overview.md)
- **목적**: 내 스킬(SKILL.md)을 평가하고 개선하는 환경을 만드는 데 쓸 부분의 원본 동작을 스펙으로 정리한다. 승인 범위와 제외 행은 overview 1절.
- **라이선스 주의**: AGPL-3.0-only. 스펙은 코드·템플릿 본문을 복사하지 않고 `파일:줄`로 가리킨다.

---

## 1. 이번 세션에서 확인한 범위

기능 스펙 6개를 모두 썼고 전부 `ready`다(실행 확인 없음).

[template-rendering](./capabilities/template-rendering.md)(공유 계약), [history-chain](./capabilities/history-chain.md), [prompt-optimize](./capabilities/prompt-optimize.md), [llm-evaluation](./capabilities/llm-evaluation.md)(평가 요청·응답 계약 포함), [iterate-rewrite](./capabilities/iterate-rewrite.md), [calibration-script](./capabilities/calibration-script.md)

---

## 2. 해결되지 않은 남은 질문 (확인 한계)

- [ ] `mustache`·`jsonrepair` 라이브러리 내부 동작(복구 범위, 이스케이프 문자 집합, 없는 변수 처리) (template-rendering, llm-evaluation)
- [ ] Gemini·DeepSeek·Chrome 내장 어댑터의 스트리밍 오류 전달(`onError` 횟수) (prompt-optimize R-13·R-22, iterate-rewrite R-08)
- [ ] Anthropic SDK가 `error` 이벤트를 실제로 내는지(2회 vs 3회) (추론)
- [ ] 중국어 판 템플릿 본문과 pro·image 템플릿 변형
- [ ] `iterate`·재작성 입력을 모델이 어떻게 따르는지(두 지시가 충돌할 때) (iterate-rewrite R-28, 실행 필요)
- [ ] 커밋된 `latest/` 보정 기록(2026-03-22, Windows 환경)이 이 SHA의 코드와 일치하는지 (calibration-script)

---

## 3. 기능 스펙 후보 (승인 범위 밖)

| 기능 | 근거 | 상태 |
|---|---|---|
| 평가 결과 세션 저장 | `packages/ui/src/types/evaluation.ts` `PersistedEvaluationResults`(유형별 최신 1건만 보관) | llm-evaluation에 데이터 모양만 포함. 별도 스펙은 후보 |
| 모델 관리·LLM 어댑터 | `llm/adapters/*`(16종) | 경계로만 다룸. promptfoo provider가 대신함 |
| 이미지 모드(템플릿 본문 참고용) | `default-templates/image-optimize/*` | 범위 밖. 이미지 프롬프트 스킬을 만들 때 참고만 |
| Pro 모드·변수 서비스·MCP 서버·데스크톱·확장·Docker | overview 지도 | 범위 밖 |

---

## 4. 다음에 볼 곳

이 레포의 스펙 작성은 끝났다. 다음 단계는 **환경 설계**다.

- 가져올 만한 것: 심판 응답 JSON 계약과 파싱 강등 규칙(llm-evaluation), 평가 결과→재작성 입력문 압축 규칙(iterate-rewrite), 버전 체인 데이터 모델(history-chain), 템플릿 렌더링 계약.
- 직접 만들어야 하는 것(원본에 없음, 스펙으로 확인): 자동 평가→재작성 루프, 평가 점수를 버전 기록에 붙이는 일, 모델별 점수 이력(compare 평가는 전체 점수 하나뿐), 심판 안정성 측정(보정 스크립트는 측정 방법이 아님), 심판-대상 모델 분리 강제.
- 먼저 정할 것: promptfoo `optimize`(닫힌 루프, 옵션 없음)와 이 레포의 수동 연결 중 어느 쪽 개선 기능을 기반으로 할지.

---

## 5. 참고 사항

- 이번 세션에서 template-rendering의 R-17(기본 템플릿 선택)이 prompt-optimize로 확정됐다. 기본 템플릿은 `DEFAULT_TEMPLATES`가 아니라 유형별 목록 첫 번째다.
- 지도 서술 정정 목록은 overview 5절 "스펙 작성 후 정정·보강".
