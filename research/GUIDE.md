# 리서치 에이전트 오픈소스 분석 가이드

- 작성일: 2026-11-04
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

웹을 검색·수집해 보고서를 쓰는 리서치 에이전트 오픈소스를 분석한다. 첫 대상은 **gpt-researcher**, 두 번째는 **hyperresearch**(Claude Code·Codex용 deep research 하니스). 레포끼리 비교하지 않고 각각 독립적으로 분석한다. hyperresearch의 분석 목적은 "어떤 식으로 조사하는가"와 "조사 결과를 어떻게 전처리해 결과물을 만드는가"다(2026-11-05 사용자 확인). 스펙을 어디에 쓸지는 아직 정해지지 않았다.

## 디렉터리

```text
research/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt, 오프라인 실행 데모
└── reports/<repo>/       # overview.md, capabilities/, questions/, diagrams/
```

루트 `repos/`·`reports/`와 섞지 않는다. 이 폴더의 레포는 루트 `index.md`에 `<repo> (research/)` 이름으로 행을 둔다.

## 분석 대상

| 이름 | URL | 기준 SHA |
|---|---|---|
| gpt-researcher | https://github.com/assafelovic/gpt-researcher | `3582a68` |
| hyperresearch | https://github.com/jordan-gibbs/hyperresearch | `aece65f` (MIT, `repos/hyperresearch/LICENSE`) |
