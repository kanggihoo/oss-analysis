# 기능 스펙 요청 템플릿 (Capability Request Template)

여러 오픈소스가 같은 기능을 어떻게 구현했는지 언어 중립 스펙으로 정리할 때 쓴다.
양식은 [capability-spec-template.md](capability-spec-template.md), 절차는 [OSS_ANALYSIS_WORKFLOW.md 8장](../OSS_ANALYSIS_WORKFLOW.md#8-기능-스펙-capability-spec). 아래 블록을 복사해 `<...>`만 채워 전달한다.

---

## 1. 스펙 작성 요청 (Agent A: 원본 코드를 읽고 스펙을 쓴다)

```text
기능: <예: 이벤트 스트림과 최종 결과 제공>
비교 레포: <repo1, repo2>   (하나여도 됨)
적용 목적: <이 기능을 어디에, 어떤 조건으로 쓰려는지>
           (A3 '채택' 판단과 A4 기본 정책을 정하는 기준이 된다)

AGENTS.md와 templates/capability-spec-template.md를 따르고,
기존 reports/<repo>와 wiki를 먼저 확인해.

1. 각 레포의 분석 commit SHA와 작업트리 상태를 확인해 source_revisions에 적어.
2. 근거의 기준은 repos/<repo>의 원본 코드야.
   reports에 없는 동작은 코드로 직접 확인하고, 확인 과정은 reports/<repo>/questions/에 남겨.
3. A(재구현 계약)는 A만 떼어 줘도 다른 언어로 구현할 수 있게 써.
   - 코드, 파일 경로, 특정 언어 표현(Promise, goroutine 등)을 넣지 마. 의미로 적어.
   - 타입은 중립 표현으로 쓰되 단위·누락·순서·공유 여부처럼 결과에 영향을 주는 의미는 반드시 적어.
4. 원본에서 관찰한 동작(B1)과 우리가 채택할 동작(A3 '채택')을 구분해.
   원본의 약점은 그대로 요구사항으로 올리지 말고 '변경'으로 표시하고 이유를 B1에 적어.
5. 모르는 것은 지어내지 마. A3 '원본 검증'에 미확인으로 두거나 '미결정'에 적어.
6. A5 수락 사례는 원본 레포의 테스트 파일을 먼저 찾아 출처로 쓰고, 부족하면 계약에서 도출해.
7. B1·B2의 코드 위치는 직접 열어 확인한 것만 repo@SHA `파일:라인` `심볼` 형식으로 적어.
8. wiki/capabilities/<기능-slug>.md에 저장해. 200줄을 넘으면 하위 기능으로 나눠.
9. 마무리할 때:
   - A만 읽고 구현한다고 가정했을 때 막힐 질문을 목록으로 보고해.
   - wiki/index.md와 wiki/log.md를 갱신해.
```

---

## 2. 재구현 검증 요청 (Agent B: 스펙의 A만 보고 구현한다)

먼저 A 부분만 별도 파일로 떼어 낸다. B(코드 위치)가 섞이면 클린룸 검증이 되지 않는다.

```bash
sed '/^## B\./,$d' wiki/capabilities/<기능-slug>.md > <작업 폴더>/spec-a.md
```

```text
spec-a.md만 읽고 <언어>로 이 기능을 구현해. 작업 폴더: <작업 폴더>
oss-analysis의 repos/, reports/, wiki/는 열지 마.

1. A5 수락 사례를 먼저 테스트로 작성하고, 그다음 구현해.
2. 스펙이 모호하거나 빠져서 추측으로 정한 부분은 전부 목록으로 남겨.
   (요구사항 ID, 무엇을 추측했는지, 어떻게 정했는지)
3. 끝나면 테스트 결과와 추측 목록을 보고해.
```

결과 반영:
- 추측 목록 → 스펙의 A3 '미결정' 또는 A2·A3 보강
- 통과 여부 → frontmatter `verification.reimplementation`에 언어·범위·결과 기록
