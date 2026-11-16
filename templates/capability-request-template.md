# 기능 스펙 요청 템플릿 (Capability Request Template)

feature map의 한 행을 스펙으로 쓰게 할 때 쓴다. 단계와 완료 조건은 [OSS_ANALYSIS_WORKFLOW.md 4장](../OSS_ANALYSIS_WORKFLOW.md#4-기능-스펙), 섹션별 작성 규칙은 [capability-spec-template.md](capability-spec-template.md) 주석에 있다. 아래 블록을 복사해 `<...>`만 채운다. 서브에이전트에 맡기든 한 세션에서 순서대로 쓰든 같은 항목을 쓴다.

---

## 1. 스펙 작성 지시 (feature map 한 행 → 스펙 하나)

`reports/<repo>/overview.md` 2절 feature map에서 승인된 행을 옮겨 채운다.

```text
레포: <repo>    기준 SHA: <전체 SHA>
분석 목적: <overview 1절의 목적>
기능: <feature map의 기능 이름>
사용자 동작·경계: <feature map 칸>
진입점·처음 읽을 코드: <feature map 칸>
선행 스펙: <없음 | capabilities/<slug>.md>
출력: reports/<repo>/capabilities/<기능-slug>.md

AGENTS.md와 OSS_ANALYSIS_WORKFLOW.md 4장대로 원본 동작을 스펙으로 써.
읽기 기본값은 2장 3번을 따르고, 진입점에서 시작해 필요하면 호출자·피호출자로 좁게 따라가.
출력 파일 말고 overview·index·log 같은 공용 파일은 고치지 마.
범위를 줄이거나 승인 범위 밖으로 빼야 하면 먼저 물어봐.
미결정은 워크플로 4장 3번의 U-ID 표로 쓰고, "없다" 주장은 7장대로 검색 범위를 2.1에 적어.

끝나면 보고해:
0. 보고 전에 `python scripts/check.py <repo>`를 돌려 자기 스펙 줄에 ERROR가 없는지 확인한다(다른 파일의 상태 불일치는 메인이 통합하며 처리하니 고치지 마).
1. status(작성자는 `draft`로 두고, `ready`는 메인의 원본 대조 점검 뒤에 정한다)와 남은 미결정
2. feature map 보정 제안: 경계 변경 / 새 기능 후보 / 새 선행 관계 (각각 근거 위치)
3. 고위험 R-ID 후보: 상태를 바꾸는 규칙, 실패 처리, "없다/전부다" 주장, 검증 수준 `추론` (메인이 점검 때 참고하되 표본은 직접 고른다)
```
