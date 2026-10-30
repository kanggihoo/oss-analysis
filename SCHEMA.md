# SCHEMA

Updated: 2026-10-22

루트의 `index.md`·`log.md` 형식과 `reports/` 문서 frontmatter 규칙이다. 분석 내용은 모두 `reports/<repo>/`에 쓴다. 2026-10-16 이전에 있던 `wiki/` 폴더(projects, concepts 등)는 삭제했고, 원문은 `git show b52364d:<경로>`로 볼 수 있다.

## index.md

- 분석한 레포마다 한 줄: 레포 이름, 기준 SHA(7자리), `reports/<repo>/overview.md` 링크, 기능 스펙 링크.
- 주제 폴더의 레포는 이름 칸을 `<repo> (<주제>/)`로 쓴다(예: `DeepTutor (ai-learning/)`). `scripts/check.py`가 이 형식으로 행을 찾는다.
- 기능 스펙 링크 뒤에는 상태를 `(ready)`·`(draft)`로 붙이거나, 모두 같으면 칸 끝에 `(모두 ready)`처럼 한 번 쓴다.
- 레포를 새로 분석하거나 기준 SHA를 올리거나 기능 스펙을 추가하면 그 줄을 고친다.
- 맨 위 `Last updated`를 갱신한다.

## log.md

- 작업 한 묶음마다 맨 아래에 추가한다. 이미 쓴 항목은 고치지 않는다.
- 형식: `## [YYYY-MM-DD] <종류> | <제목>` 다음에 무엇을 읽고, 실행하고, 어떤 파일을 바꿨는지 2~4줄.
- 종류: `ingest`(새 레포), `update`(기존 레포 갱신), `capability`(기능 스펙), `workflow`(규칙·템플릿 변경).

## reports 문서 frontmatter

`reports/<repo>/` 아래 문서는 맨 위에 frontmatter를 둔다. 파일 경로나 git으로 알 수 있는 것은 넣지 않는다.

```yaml
---
sha: "<전체 커밋 SHA>"        # 모든 문서. 이 문서가 기준으로 삼은 커밋
created: YYYY-MM-DD           # 모든 문서. 처음 쓴 날
updated: YYYY-MM-DD           # 모든 문서. 내용을 마지막으로 바꾸거나 다시 확인한 날
sources:                      # questions/, <패키지>/NN-주제.md, capabilities/
  - <repos/<repo>/ 기준 상대 경로>
depends:                      # capabilities/만. 선행 스펙 (이 파일 기준 상대 경로)
  - <../capabilities/<slug>.md>
status: draft | ready         # capabilities/만
reimplementation: 미실행      # capabilities/만. 실행하면 언어·범위·결과 링크
---
```

| 필드 | 규칙 |
|---|---|
| `sha` | 같은 레포 안에서도 문서마다 다를 수 있다. 새 커밋에서 다시 확인하면 올린다. |
| `created` | 바꾸지 않는다. |
| `updated` | 내용이 바뀌거나 코드·실행으로 다시 확인했을 때 바꾼다. 링크·오타·형식만 고칠 때는 바꾸지 않는다. |
| `sources` | 본문에서 인용하거나 판단 근거로 쓴 원본 파일을 적는다. 테스트·설정·문서도 근거로 썼으면 넣고, 열어 보기만 한 파일은 넣지 않는다. 레포가 업데이트됐을 때 다시 볼 문서를 찾는 기준이다(`OSS_ANALYSIS_WORKFLOW.md` 5장). |
| `depends` | 재구현에 필요한 계약을 가진 다른 스펙. 런타임 호출 관계 전체가 아니고, 스펙 안에서 경계만 정의한 의존은 넣지 않는다. 선행 스펙이 바뀌면 재검토 대상이다. 없으면 `[]`. |
| `status` | `ready` = 선언한 범위에서 행동 규칙이 정해졌고, 1.5 코드 참조와 선행 스펙이 해소됐고(선행 스펙도 `ready`), 구현을 막는 모순·미결정이 없음. 실행으로 원본과 같은지 검증했다는 뜻은 아니다. 이전 형식(A/B, "채택" 열) 스펙의 `ready`는 우리가 정한 계약 기준이다. |
| `reimplementation` | `templates/capability-request-template.md` 2번 요청으로 검증한 결과 링크. 결과 문서에는 제공 범위, 테스트 결과, 원본과 비교한 사례, 관찰한 차이, 미검증 범위를 적는다. |

넣지 않는 것: `title`(본문 첫 제목), `type`(파일 이름·폴더), `repo`(경로), `url`(`artifacts/<repo>/repo-metadata.txt`), 문서 전체 검증 수준(주장마다, 기능 스펙은 R-ID마다 본문에 붙임).

기존 문서에는 한꺼번에 붙이지 않고, 새로 쓰거나 내용을 고치는 문서부터 붙인다.
