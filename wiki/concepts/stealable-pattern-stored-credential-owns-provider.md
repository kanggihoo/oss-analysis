---
title: "Stealable Pattern: Stored Credential Owns the Provider"
created: 2026-10-06
updated: 2026-10-06
type: concept
tags: [architecture, pattern, security, agent-framework, developer-tools]
sources:
  - reports/pi/ai/04-auth.md
  - reports/pi/ai/04-01-auth-env-and-storage.md
  - artifacts/pi/ai-demos/auth-owner-demo.ts
  - artifacts/pi/ai-demos/auth-resolve-demo.ts
  - repos/pi/packages/ai/src/auth/resolve.ts
  - repos/pi/packages/ai/src/auth/types.ts
  - repos/pi/packages/ai/src/auth/credential-store.ts
  - repos/pi/packages/coding-agent/src/core/auth-storage.ts
confidence: high
---

# Stealable Pattern: Stored Credential Owns the Provider

여러 인증 출처(호출 옵션, 저장된 로그인, 환경변수)를 한곳에서 합치되 **조용한 폴백을 막는** 규칙이다. 출처는 [[pi]]의 `auth/resolve.ts`다.

## 규칙 세 가지
1. **한 함수가 순서를 정한다**: 호출 옵션 > 저장된 credential > 환경변수(ambient). 통신 코드는 최종 `apiKey`, `headers`만 받는다(`resolveProviderAuth`, `resolve.ts:33-93`).
2. **저장된 것이 있으면 그 provider는 저장된 것이 소유한다.** 환경변수는 저장된 것이 없을 때만 본다. 갱신이 실패하거나 그 유형을 처리할 방법이 없어도 환경변수로 넘어가지 않고 오류를 낸다(`resolve.ts:24-28`, `:70-93`).
3. **쓰기는 직렬화된 `modify` 하나뿐**이고, 토큰 갱신은 그 락 안에서 **다시 확인**한다(double-checked locking). 만료 5분 전부터 갱신 대상이다(`resolve.ts:102-162`, `types.ts:65-94`).

## 실행으로 확인 (`artifacts/pi/ai-demos/`)
| 경우 | 결과 |
|---|---|
| 유효한 OAuth + 환경변수 키 | OAuth 토큰을 쓰고 환경변수는 무시 |
| 만료 임박 OAuth + 갱신 실패 + 환경변수 키 | `[oauth] OAuth refresh failed ...` **오류**, 환경변수로 넘어가지 않음 |
| 저장된 OAuth인데 provider에 oauth 처리기 없음 | `undefined`("설정 안 됨") |
| 저장된 것 없음 + 환경변수 | 환경변수를 씀 |
| 만료 임박 토큰으로 동시 5개 호출 | `refresh`는 **1번**, 5개 모두 새 토큰 |

## 왜 좋은가
- 구독 로그인(월 정액)으로 쓰는 사용자가 있는데 로그인이 만료되면 조용히 종량제 API 키로 바뀌어 **요금이나 계정이 달라지는 일**을 막는다(이유는 주석의 "silent"에서 읽은 `추론`).
- 동시 요청이 많은 에이전트에서 토큰 갱신이 이중으로 일어나지 않는다.
- 저장소는 인터페이스(`read`, `list`, `modify`, `delete`)이고 기본 구현은 메모리뿐이라, 앱이 파일 저장(권한 `0o600`, 파일 락)을 끼워 넣는다(`coding-agent/src/core/auth-storage.ts`).
- 로그인 방식(브라우저, 디바이스 코드)이 달라도 결과는 같은 `OAuthCredential`이고 같은 경로로 저장된다.

## 주의
- 상태 화면용 `source` 라벨이 호출 옵션으로 준 키도 `"stored credential"`로 표시한다(옵션 키를 가짜 credential로 감싸서 넘기기 때문, 실험으로 확인).
- 토큰은 평문 JSON으로 저장된다. 파일 권한에 의존한다.
- 환경변수만 쓰는 CI에서는 저장된 것이 없어 규칙 2가 영향을 주지 않는다.

관련: [[pi]], [[pi-ai-provider-api-separation]], [[stealable-pattern-async-event-stream-with-final-result]].
