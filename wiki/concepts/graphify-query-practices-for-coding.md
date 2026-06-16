---
title: graphify Query Practices for Coding Work
created: 2026-06-15
updated: 2026-06-15
type: concept
tags: [graphify, cli, commands, developer-tools, workflow, evidence]
sources:
  - repos/graphify/graphify/serve.py
  - repos/graphify/graphify/__main__.py
  - repos/graphify/graphify/querylog.py
  - repos/graphify/graphify/skill.md
  - repos/graphify/tools/skillgen/fragments/references/query/cli.md
  - /Users/kkh/.codex/skills/graphify/skill.md
  - /Users/kkh/.codex/skills/graphify/references/query.md
  - actual command: uv run python -m graphify --help
confidence: high
---

# graphify Query Practices for Coding Work

이 페이지는 [[graphify-extract-query-mechanics]]와 [[graphify-cli-reference]]의 실전 보강이다. 코딩 작업에서 사람은 `/graphify`로 skill을 트리거하지만, 실제 효과는 AI가 사용자 의도를 `graphify query "..."`, `graphify explain`, `graphify path`, `graphify affected`에 맞는 graph vocabulary 질의로 바꾸는지에 달려 있다.

확인 기준은 `repos/graphify` commit `8a04560`의 source와 `uv run python -m graphify --help` 출력이다. `query` 동작은 `repos/graphify/graphify/serve.py`의 lexical scoring + BFS/DFS traversal이고, terminal routing은 `repos/graphify/graphify/__main__.py`의 `query` branch가 담당한다.

## 핵심 원칙

`graphify query`는 LLM semantic search가 아니다. 질문 문자열을 token으로 나눈 뒤 node label, node id, `source_file`에 exact/prefix/substring/IDF scoring을 적용하고 seed node 주변을 BFS 또는 DFS로 순회한다. 따라서 코딩 작업 질문은 다음 형태가 가장 잘 맞는다.

```text
[실제 class/function/module/file 식별자] + [도메인 영어 keyword] + [관계 의도]
```

예시:

```bash
graphify query "AuthService JwtProvider LoginController token exception response" --context call --dfs --budget 3000
graphify explain "AuthService"
graphify path "LoginController" "UserRepository"
graphify affected "AuthService" --depth 3
```

한국어 원문만 넣는 방식은 취약하다.

```bash
# 취약: graph label과 한국어 token이 겹치지 않으면 seed를 못 찾음
graphify query "인증 흐름이 어떻게 동작해?"
```

## 사람이 `/graphify`로 요청할 때의 좋은 형태

사람은 graph query 문자열을 직접 완성하려고 하기보다, 작업 의도와 단서를 주고 AI에게 vocabulary 확장을 요구하는 편이 좋다.

```text
/graphify 기존 graphify-out/graph.json을 사용해서 query-first로 조사해줘. 재빌드하지 마.

작업:
로그인 실패 시 500이 나는 문제를 고치고 싶어.

단서:
- auth, login, token, exception, response
- LoginController 또는 AuthService가 있을 수 있음

요청:
내 한국어 문장을 그대로 graphify query에 넣지 말고,
graph node label/source_file vocabulary에서 관련 token을 먼저 고른 뒤
expanded query를 만들어 graphify query/explain/path/affected CLI를 실행해줘.
선택한 token과 source_location 기반 수정 후보를 같이 보여줘.
```

## AI가 따라야 할 query 생성 절차

1. `graphify-out/graph.json`이 있으면 새 extraction보다 query-first를 우선한다.
2. 사용자 질문을 그대로 CLI에 넣기 전에 graph vocabulary를 확인한다.
3. node label/source_file에 실제 존재하는 token 중 최대 5~12개를 고른다.
4. 한국어/추상어는 graph 안의 실제 영어 identifier로 매핑하되, 존재하지 않는 token은 만들지 않는다.
5. 넓은 구조는 `query`, 특정 node는 `explain`, 두 entity 연결은 `path`, 변경 영향은 `affected`를 고른다.
6. `call`, `import`, `field`, `parameter`, `return`, `generic` 같은 관계 의도는 가능하면 `--context`로 명시한다.
7. 결과는 graph output의 `NODE`, `EDGE`, `source_location`, confidence tag 안에서만 설명한다.
8. 실제 수정 전에는 source file을 직접 읽어 검증한다. graph edge는 수정 후보이지 최종 사실이 아니다.

## Codex skill 설치본과 최신 source의 차이

현재 `/Users/kkh/.codex/skills/graphify/skill.md` 설치본은 기존 graph가 있을 때 `graphify query "<question>"`를 바로 실행하라는 fast path가 강하다. `/Users/kkh/.codex/skills/graphify/references/query.md`도 BFS/DFS와 `source_location` 인용 규칙은 설명하지만, 질문을 graph vocabulary로 먼저 확장하라는 요구는 약하다.

반면 `repos/graphify/graphify/skill.md` 최신 source에는 다음 보정이 들어 있다.

```text
Before traversal, expand the question against the graph's own vocabulary
so a wording mismatch does not collapse the answer to noise.
```

그리고 `repos/graphify/tools/skillgen/fragments/references/query/cli.md`는 constrained query expansion을 REQUIRED로 정의한다. 요지는 “binary 내부에는 stemming, synonym, cross-language match가 없으니, graph node label에서 vocabulary를 추출하고 그 안에 있는 token만 골라 expanded query를 만들라”는 것이다.

따라서 한국어 중심 사용 환경에서는 `/graphify` 요청에 다음 문장을 넣는 것이 안전하다.

```text
한국어 원문을 그대로 query하지 말고 graph vocabulary에서 token을 선택해 expanded query를 만든 뒤 실행해줘.
```

## 코딩 작업별 CLI 선택

| 작업 의도 | 우선 명령 | 예시 |
|---|---|---|
| 관련 구조 넓게 찾기 | `query` BFS | `graphify query "upload profile image validation config" --budget 3000` |
| 호출 흐름 추적 | `query --dfs --context call` | `graphify query "LoginController AuthService JwtProvider" --context call --dfs --budget 3000` |
| 특정 node 주변 이해 | `explain` | `graphify explain "AuthService"` |
| 두 컴포넌트 연결 확인 | `path` | `graphify path "LoginController" "UserRepository"` |
| 리팩터링 영향 분석 | `affected` | `graphify affected "UserService" --depth 3` |
| 결과를 feedback loop에 저장 | `save-result` | `graphify save-result --question Q --answer A --type query --nodes AuthService` |

## 한국어/영어 차이

사람은 한국어로 물어도 되지만, 실제 `graphify query` 문자열은 대개 영어 identifier 중심이어야 한다. 예를 들어 `인증`, `흐름`, `응답` 같은 한국어 token은 source graph label과 겹치지 않을 수 있다. AI는 이를 `auth`, `token`, `login`, `request`, `response`, `controller`, `service` 같은 실제 graph vocabulary로 확장해야 한다.

단, “그럴듯한 영어 단어”를 만들면 안 된다. 최신 query reference의 원칙은 graph vocabulary 안에 있는 token만 고르는 것이다. 사용자가 말한 개념에 대응하는 token이 graph에 없으면 “해당 vocabulary가 graph에 없다”고 보고하고, 무리하게 search를 꾸미지 않는다.

## 관련 페이지

- [[graphify]]
- [[graphify-cli-reference]]
- [[graphify-extract-query-mechanics]]
- [[graphify-agent-skill-integration]]
- [[graphify-graph-analysis]]
- [[evidence-backed-analysis]]
