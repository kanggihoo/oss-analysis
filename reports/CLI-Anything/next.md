---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-18
updated: 2026-11-18
---

# Next Session Plan: CLI-Anything

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone(`34f5195`), 라이선스, feature map 9행(핵심 5 / 부속 4), 공유 계약 2
- [x] 2026-11-18 사용자 승인: 행 1~5. 처음 제안한 8행을 5행으로 합침
- [x] 기능 스펙 5개 작성(모두 `draft`): [harness-sop](./capabilities/harness-sop.md), [harness-contract](./capabilities/harness-contract.md), [harness-families](./capabilities/harness-families.md), [skill-packaging](./capabilities/skill-packaging.md), [registry-schema](./capabilities/registry-schema.md). 서브에이전트 5명이 병렬로 작성
- [x] 메인 세션 표본 점검 6건 일치: `session.py:129-144` undo 미저장, `gimp_cli.py:439-446` `canvas dpi`에 `snapshot` 없음, `export.py:67-84` Pillow fallback, `generate_meta_skill.py:12` 출력 경로, obs-studio 검색 0건, `repl_skin.py:131-156` skill id 규칙
- [x] 2026-11-19 질문 2건: [q1-cli-hub](./questions/q1-cli-hub.md), [q2-hub-catalog](./questions/q2-hub-catalog.md). `artifacts/CLI-Anything/hub-catalog.tsv`(103행). venv에서 `mermaid`만 설치·실행
- [ ] 구조도(archify) 미작성, 독립 검토와 재구현 미수행, `validate_root_skills.py` 실행 안 함(권한 분류기가 거부, 우회하지 않음)
- 서브에이전트가 scratchpad에서 한 실행: gimp·firefly-iii·jumpserver 복사본 실행과 godot·gimp wheel 빌드(contract), `generate_meta_skill.py` 실행(registry-schema). `repos/CLI-Anything`은 변경 없음(`git status` 0줄)

---

## 2. 해결되지 않은 남은 질문 (스펙의 U-ID)

| 스펙 | 미결정 | 닫는 방법 |
|---|---|---|
| harness-sop | U-01~05: 명령 문서의 `./HARNESS.md` 기준 경로, 앱 이름만 줬을 때 거절 동작, `validate` FAIL 조건, build 중 테스트 실패 시 재시도, `[_resolve_cli]` 줄이 없을 때 | 에이전트로 `/cli-anything`을 실제로 돌린 기록이 필요 |
| harness-families | U-01~03: 분류 기준(앱 호출 코드 유무 vs 주된 작업), exa의 `sdk`/`http`, `mixed` 임계 | 사용자 결정(분류 철학) |
| skill-packaging | U-01: `npx skills add --skill <id>`가 디렉터리 이름과 frontmatter `name` 중 무엇으로 매칭하나 | vercel-labs/skills의 `docs/commands.md`, `docs/creating-skills.md` 확인 |
| registry-schema | U-01: sketch·clibrowser의 비pip `install_cmd`가 `pip` 경로로 갈 때 실제 설치 성공 여부, U-02: 업로드 URL 동일성 | 설치 실행, secret이라 확인 불가 가능성 |
| harness-contract | 없음 | — |

---

## 3. 기능 스펙 후보

승인된 5개를 모두 썼다. 아래는 스펙 작성 중 나온 후보로, 목적(방법론 이해) 밖이라 필요할 때만 다룬다.

| 후보 | 근거 |
|---|---|
| macrocli 라우터(백엔드 7종 우선순위 선택) | `macrocli/agent-harness/cli_anything/macrocli/core/routing.py:41-87` |
| zotero 4채널(SQLite 읽기, HTTP 2종, 앱 기동, 실험적 쓰기) | `zotero/agent-harness/ZOTERO.md`, `core/discovery.py` |
| lldb 세션 서버(소켓으로 상태 유지) | `lldb/agent-harness/cli_anything/lldb/utils/session_client.py:118-131` |
| 하니스 안 복제 생성기 `mubu/agent-harness/skill_generator.py`, `zotero/agent-harness/skill_generator.py` | 열지 않음 |
| registry 항목 추가 검증 단계(없는 단계) | registry-schema 적용 메모 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음에 할 일은 `draft` 5개의 `ready` 승격 여부다. 미결정이 있는 4개는 위 표대로 닫혀야 하고, 미결정이 없는 `harness-contract`는 다른 스펙이 `depends`로 의존하므로 독립 검토(워크플로 4장 5번)가 필요하다.

### 막힌 경로

| 시도 | 결과 | 재개 조건 |
|---|---|---|
| `validate_root_skills.py` 실행으로 기준 SHA의 `skills/` 통과 여부 확인 | 권한 분류기가 거부, 실행 안 함 | 사용자가 실행을 허용하면 |
| `skill_generator.py`를 레포 안에서 실행 | 실행 안 함(registry-schema 쪽은 scratchpad에서 `generate_meta_skill.py`만 실행) | 사용자 허용 |
| 하니스 backend 실행(GIMP, Blender 등) | 앱 미설치 | 앱 설치 후 |
| `/cli-anything` 실제 실행으로 harness-sop 미결정 닫기 | 하지 않음 | 사용자가 에이전트 실행을 허용하면 |

---

## 5. 참고 사항 및 후속 제안

- 구조도는 그리지 않았다. 필요하면 범위 승인 후 archify로 `overview` 3절을 채운다.
- [harness-catalog.tsv](../../artifacts/CLI-Anything/harness-catalog.tsv)의 `backend_tags`는 문자열 휴리스틱이라 24행이 틀린다. 정정안은 harness-families 2.1(c)에 있고 TSV는 고치지 않았다.
- 레포는 shallow clone(`--depth 50`)이라 `git log` 이력 기반 확인은 제한된다.
