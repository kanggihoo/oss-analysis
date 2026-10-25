# agent-memory 오픈소스 분석 가이드

- 작성일: 2026-10-25
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기, 기능 지도 → 범위 승인 → 기능 스펙). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

코딩 에이전트(Claude Code, Codex 등)에 붙는 **에이전트 메모리** 오픈소스를 같은 기준으로 분석해 비교한다. 비교 축은 gbrain 분석 때 정한 질문 ①~④(저장 위치·방식 / 호출 트리거 / 필요한 것만 LLM에 건네는 방법 / 자동 저장 판단)이다. 레포마다 `reports/<repo>/`에 overview(기능 지도)와 필요한 기능 스펙을 쓴다.

## 디렉터리

```text
agent-memory/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt, 실행 실험(<주제>-demos/) 등 도구 출력
└── reports/<repo>/       # overview.md, capabilities/, questions/, diagrams/, next.md
```

루트 `repos/`·`reports/`와 섞지 않는다(`herdr-plugin/`, `trading/`과 같은 방식). 이 폴더의 레포도 루트 `index.md`에 행을 둔다. 문서 안의 경로는 `agent-memory/…`처럼 루트 기준으로 쓰고, 문서 간 링크는 상대 경로를 쓴다.

## 분석 대상

| 이름 | URL | 하는 일 (README 기준, 코드 확인 전) | 상태 |
|---|---|---|---|
| gbrain | https://github.com/garrytan/gbrain | 마크다운 페이지 + 하이브리드 검색 + 사실·그래프 메모리를 CLI·MCP로 제공 | 기능 스펙 7개 ready (2026-10-24, 루트에서 이 폴더로 이동) |
| agentmemory | https://github.com/rohitg00/agentmemory | 훅으로 도구 사용을 자동 캡처하고 BM25+벡터+그래프로 검색해 돌려주는 코딩 에이전트용 영속 메모리 서버 | 기능 지도 작성 중 (2026-10-25) |

기준 SHA는 `repos.lock.tsv`, 각 overview의 frontmatter `sha`와 같다.
