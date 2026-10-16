# 기능 스펙 요청 템플릿 (Capability Request Template)

레포 하나가 구현한 기능을 언어 중립 스펙으로 정리할 때 쓴다. 단계와 완료 조건은 [OSS_ANALYSIS_WORKFLOW.md 4장](../OSS_ANALYSIS_WORKFLOW.md#4-기능-스펙), 섹션별 작성 규칙은 [capability-spec-template.md](capability-spec-template.md) 주석에 있다. 아래 블록을 복사해 `<...>`만 채워 전달한다.

---

## 1. 스펙 작성 요청 (Agent A: 원본 코드를 읽고 스펙을 쓴다)

```text
기능: <예: Claude Code 세션 로그 탐색과 읽기>
레포: <repo>
적용 목적: <이 기능을 어디에, 어떤 조건으로 쓰려는지. A3 '채택'의 판단 기준>

AGENTS.md와 OSS_ANALYSIS_WORKFLOW.md 4장대로 스펙을 써.
끝나면 A만 읽고 구현할 때 막힐 질문 중 남은 것을 보고해.
```

---

## 2. 재구현 검증 요청 (Agent B: 스펙의 A만 보고 구현한다)

먼저 A 부분만 별도 파일로 떼어 낸다. frontmatter(원본 파일 경로)와 B(코드 위치)가 섞이면 클린룸 검증이 되지 않는다.

```bash
sed -e '1{/^---$/!q}' -e '1,/^---$/d' reports/<repo>/capabilities/<기능-slug>.md | sed '/^## B\./,$d' > <작업 폴더>/spec-a.md
```

```text
spec-a.md만 읽고 <언어>로 이 기능을 구현해. 작업 폴더: <작업 폴더>
읽고 쓰는 파일은 spec-a.md와 작업 폴더 안의 파일뿐이다(oss-analysis의 repos/, artifacts/, reports/, 루트 문서는 범위 밖).

1. A5 수락 사례를 먼저 테스트로 작성하고, 그다음 구현해.
2. 스펙이 모호하거나 빠져서 추측으로 정한 부분은 전부 목록으로 남겨.
   (요구사항 ID, 무엇을 추측했는지, 어떻게 정했는지)
3. 끝나면 테스트 결과와 추측 목록을 보고해.
```

결과 반영은 [OSS_ANALYSIS_WORKFLOW.md 4장](../OSS_ANALYSIS_WORKFLOW.md#4-기능-스펙) 5번을 따른다.
