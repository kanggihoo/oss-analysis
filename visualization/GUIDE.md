# 시각화 오픈소스 분석 가이드

- 작성일: 2026-11-01
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

다이어그램·설명 페이지를 만드는 시각화 도구를 분석한다. 첫 대상은 **archify**, 두 번째는 **stack-diagram**이다. archify는 이 작업 공간이 구조도(`reports/<repo>/diagrams/`)를 그릴 때 쓰는 `archify` 스킬의 원본 레포다. stack-diagram은 로고와 템플릿으로 스택 다이어그램을 만드는 스킬이고 갤러리 사이트(`site/`)를 함께 배포한다.

- 분석 목적(스펙을 어디에 쓸지): **미정**. 사용자가 정하면 여기에 적는다(예: "스킬이 내부에서 어떻게 검증·렌더링하는지 이해", "재구현"). feature map 세밀도와 권장 범위가 이 목적으로 정해진다.
- 현재 단계: archify는 기능 스펙까지 있다. stack-diagram은 2026-11-10에 feature map 14행과 구조도까지 썼고 범위 승인을 기다린다.

## 디렉터리

```text
visualization/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt 등 도구 출력
└── reports/<repo>/       # overview.md, diagrams/
```

루트 `repos/`·`reports/`와 섞지 않는다. 이 폴더의 레포도 루트 `index.md`에 `<repo> (visualization/)` 이름으로 행을 둔다(overview를 쓸 때 추가).

## 분석 대상

| 이름 | URL | 라이선스 (파일 확인) |
|---|---|---|
| archify | https://github.com/tt-a1i/archify | Apache-2.0 (`repos/archify/LICENSE`). 과거 MIT 부여분은 `LICENSE-MIT`·`NOTICE`에 유지(README 484~488행 기준) |
| stack-diagram | https://github.com/caru-ini/stack-diagram | MIT (`repos/stack-diagram/LICENSE`). 폰트는 OFL 1.1(`skills/stack-diagram/assets/fonts/OFL-*.txt`) |

기준 SHA는 `repos.lock.tsv`와 같다(archify main 2026-10-31, stack-diagram main 2026-11-09).

## 먼저 볼 곳 (후보, 코드로 확인 전)

`git ls-files` 최상위 디렉터리 이름만 본 것이고 역할은 `미확인`이다.

| 위치 | 파일 수 | 읽을 이유 |
|---|---|---|
| `archify/` | 206 | 스킬 본체 후보 |
| `bin/`, `scripts/`, `tools/` | — | 검증·렌더·내보내기 CLI 후보(`bin`은 ls로 확인, 파일 수 미집계) |
| `explainer/`, `delta/`, `viewer/` | — | 설명 페이지·변경 비교·뷰어 후보 |
| `integrations/`, `.agents/` | 29, 24 | 에이전트별 설치 방식 후보 |
| `website/`, `docs/`, `journal/`, `experiments/`, `benchmarks/` | — | 문서·배포 사이트·실험(부속 후보) |

## 로컬 설치본과의 관계

이 작업 공간의 `.agents/skills/archify`(`~/.claude/skills/archify`가 가리킴)가 이 레포와 같은 버전인지는 `미확인`이다. 분석 근거는 항상 `repos/archify` 기준 SHA의 코드다.
