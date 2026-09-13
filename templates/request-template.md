# AI 분석 요청 템플릿 (Request Template)

새로운 오픈소스 레포 분석을 시작하거나 추가 분석을 요청할 때 이 내용을 복사하여 프롬프트로 전달합니다.

---

```text
대상: <repo URL>
목적: <학습 / 설계 참고 / 도입 검토>

AGENTS.md와 OSS_ANALYSIS_WORKFLOW.md를 따르고,
기존 reports와 wiki를 먼저 확인해.

1. 분석 commit SHA와 작업트리 상태를 기록해.
2. archify로 주요 구조도와 대표 실행 흐름을 만들어.
3. 핵심 관계는 코드로 확인하고 미확인 범위를 표시해.
4. JSON·HTML과 overview.md를 reports/<repo>/에 저장해.
5. 그림을 읽는 순서와 후속 질문 3~5개를 제안해.
6. 이후 질문의 상세 답변은 reports에 기록하고,
   재사용할 핵심 지식은 wiki에 반영해.
7. 마무리할 때 next.md와 wiki 목록·로그를 갱신해.
```
