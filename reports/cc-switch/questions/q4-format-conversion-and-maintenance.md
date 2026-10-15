# [Q] Claude Code로 Gemini를 쓰려면 프록시가 형식 변환까지 하는가, 유지보수 부담은

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `d35726e`
- **검증 수준**: `코드 확인` (함수 시그니처, 파일 규모, git 이력 수치). 변환 정확도는 `미확인`(실행 안 함)

## 1. 질문 및 결론

- **질문**: provider마다 도구 목록과 응답 구조가 다를 텐데, 변환도 프록시가 담당하는가? 변경이 생기면 계속 수정해야 하는가?
- **핵심 결론**: 맞다. 프록시가 요청/응답/스트리밍을 양방향 변환한다. 변환 코드가 크고 이력상 계속 고쳐지고 있어 유지보수 부담이 크다.

## 2. 동작 설명

```
Claude Code ─ Anthropic 요청 ─▶ 프록시 ─ anthropic_to_gemini() ─▶ Gemini
Claude Code ◀─ Anthropic 응답 ─ 프록시 ◀─ gemini_to_anthropic() ─ Gemini
```

- provider 카드의 "Upstream Format"(Anthropic Messages / OpenAI Chat / OpenAI Responses / Gemini Native)으로 어댑터를 고른다 (README FAQ).
- 변환 항목: JSON 구조, 스트리밍 SSE 재조립(`streaming_gemini.rs`), 도구 스키마(`gemini_schema.rs`)와 도구 호출 id 합성(`synthesize_tool_call_id`), 토큰 사용량 포맷(`build_anthropic_usage`).
- 대응되지 않는 기능을 위한 보정 모듈이 따로 있다 (`rectify_tool_call_args`, thinking/media 보정). 호환성이 완전하지 않다는 신호(추론).

## 3. 코드 근거

| 구분 | 파일 | 식별자 | 설명 |
|---|---|---|---|
| 요청 변환 | `proxy/providers/transform_gemini.rs:50` | `anthropic_to_gemini` | Anthropic → Gemini |
| 응답 변환 | `proxy/providers/transform_gemini.rs:127` | `gemini_to_anthropic` | Gemini → Anthropic |
| 스트림 변환 | `proxy/providers/streaming_gemini.rs:237` | `create_anthropic_sse_stream_from_gemini` | SSE 재조립 |
| 규모 | `proxy/providers/transform*.rs` | - | 변환 관련 파일 합계 약 2.7만 줄 |

## 4. 검증 결과 (git 이력)

- `proxy/providers/` 커밋 193개 (2025-12-05 ~ 2026-10-06), 그중 2026-07 이후 83개.
- `transform_gemini.rs` 최근 커밋 제목: `resolve functionResponse.name and replay thought_signature for synthesized tool call IDs`, `correct usage accounting on format-conversion paths`, `extend tool-result media handling to all conversion bridges`. 제목만 확인했고 diff는 안 봤다.

## 5. 남은 질문

- [ ] provider별 변환 코드의 fix 비율(가장 자주 깨지는 경로)
- [ ] 실제로 Claude Code → Gemini 경로를 실행해 본 품질 (미실행)
