---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-04
updated: 2026-11-05
---

# Next Session Plan: hyperresearch

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 기준 고정(`aece65f`, MIT), feature map 20행, 공유 계약 3개, 구조도 1개(archify 4게이트 통과)
- [x] 읽은 것: README 전문, `pyproject.toml`, 진입 스킬 `skills/hyperresearch.md` 전문, 단계 스킬 18개의 설명·절 제목, `cli/__init__.py`·`cli/main.py`, `core/runs.py`·`core/codex.py`·`core/hooks.py`·`cli/fetch.py`·`core/fetcher.py`·`web/base.py` 등의 진입 함수와 일부 본문
- [x] 단계 스킬·서브에이전트 프롬프트 본문은 3~17행 스펙을 쓰며 읽었다(각 스펙 `sources`). 행 1·2·18·19·20 코드는 아직 안 읽었다.

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [x] **분석 목적**: 2026-11-05 확인 — 독립 분석, 조사 방식과 결과 전처리·산출 과정. 스펙 용도(재구현·학습 자료 등)는 미확인. 권장 범위는 이에 맞춰 행 3~9, 11~17로 고쳤다.
- [x] (부분 답: `verify_run`이 `response_format`으로 `word_targets`를 읽음, [run-manifest-gate](capabilities/run-manifest-gate.md) 2.1) dissertation 티어에서 어떤 프로필 값이 실제로 읽히는지(README·진입 스킬은 "읽는 곳 없음(#103)", 로드맵 문서는 Phase 3 완료)
- [x] (답: 아니오. [web-providers](capabilities/web-providers.md) R-08) 모든 외부 요청 호출부가 `safe_http.safe_get`을 거치는지(crawl4ai 브라우저 lane과 `scholar/base.py` `_http_get`, `core/scholar.py` `_http_get_json`, `core/embed.py` `_http_embed`는 따로 확인 필요)
- [x] (답: [subagent-roster](capabilities/subagent-roster.md) 표) 서브에이전트 프롬프트가 부르는 `hyperresearch` 명령 목록과 순서
- [ ] `cli/research.py` 단발 `research <주제>` 명령이 파이프라인과 어떤 관계인지(레거시인지)
- [ ] README 벤치마크(DRACO 77.7) 주장은 코드로 확인할 수 없다

---

## 3. 기능 스펙 후보

승인 범위 3~17행의 스펙 15개를 썼다(ready 12 / draft 3). 새 후보: `research/wrapper_contract.json`(하니스 외부 계약, lint와 분해 단계가 읽는데 소유 스펙 없음, [verification-battery](capabilities/verification-battery.md) 보고). 승인 여부는 사용자 결정이다.

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음 단계: draft 3개(4·5·6행)의 미결정을 닫는다. 4행 미결정 2건은 원본이 정하지 않은 값(챕터 모드의 단계별 변형, 전역 step 6·11 기록 키)이라 코드를 더 읽어도 답이 안 나올 수 있다. 그 경우 "구현자가 정해야 하는 값"으로 적고 4행을 ready로 올리면 5·6행도 올릴 수 있다. 5·6행 미결정 8건씩은 각 스펙 1.4를 본다.

- 사용자 결정: `wrapper_contract.json` 스펙 추가 여부, 재구현 검증(워크플로 4장 6번) 수행 여부.
- 아직 안 읽은 영역: 행 1·2(설치·프로필·레버), 18(에스컬레이션), 19·20. 사용자가 범위에 넣으면 그때 읽는다.
---

## 5. 참고 사항 및 후속 제안

- 이 레포의 "행동"은 프롬프트 텍스트가 정하는 흐름과 CLI가 보장하는 계약 두 층이다. 프롬프트 층은 실행 없이는 검증할 수 없으니(LLM이 읽어야 동작) 스펙에서는 "프롬프트가 요구하는 산출물과 CLI가 검사하는 산출물"의 일치 여부를 확인 한계로 적는 편이 정직하다.
- `repos/hyperresearch`는 `--depth 50` shallow clone이다. 기준 SHA 이후 변경은 `git fetch` 후 `git diff --name-status aece65f..<새 SHA>`로 본다.
