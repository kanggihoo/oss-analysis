# Q1. 혼자 쓰면서 프로젝트별로 나눠 관리할 수 있나? 프로젝트마다 조금씩 다르면?

- 기준 commit: `6147818` (`repos/teamai-cli`, report 1차 기준 `7ba8bcc`보다 7 commit 뒤)
- 읽은 것: `docs/guide/distribution.md`, `src/namespace-resolver.ts`, `src/resource-namespaces.ts`, `src/resources/desired.ts`, `src/init.ts:316`, `src/projects.ts`
- 검증 수준: 코드 확인 + 문서 근거. 실행 안 함.

## 짧은 결론

- **가능하다.** "팀"은 저장소 하나를 가리키는 이름일 뿐이라 혼자서도 쓸 수 있다. 개인 저장소 하나에 `manifest/projects.yaml`을 두고 프로젝트마다 폴더(namespace)를 나누면 된다. role은 설정하지 않아도 된다.
- **프로젝트마다 조금 다른 경우**: 공통 버전은 루트(`skills/x/`)에 두고, 다른 버전은 같은 이름으로 `skills/<project>/x/`에 둔다. 그러면 그 프로젝트에서만 **파일 전체가 교체**된다. 일부만 덮어쓰는 병합은 없다.

## 1. 동작 방식

### 폴더 규칙 (코드 확인, `src/namespace-resolver.ts:1-12`)

```text
<type>/        루트: 모두에게 배포
<type>/<ns>/   <ns>가 활성인 곳에만 배포 (활성 = role ∪ project)
```

- 활성 namespace의 항목은 **같은 이름의 루트 항목을 통째로 교체**한다.
- 같은 이름이 같은 곳에 두 개 있거나, 활성 namespace 두 곳에 있으면 **충돌**로 처리한다. 이때 그 타입은 이번 pull에서 멈추고 이미 설치된 것을 유지한다 (`src/resources/desired.ts`의 `DeliveryConflict` 주석).
- 예외로 rules와 `claudemd`는 경로를 유지하므로, 서로 다른 namespace에 같은 이름이 있어도 둘 다 배포된다. 다만 루트의 같은 이름 항목은 교체된다 (`resolveRootOverrides`, `src/namespace-resolver.ts`).

### 프로젝트를 정하지 않은 폴더 (코드 확인, `src/resource-namespaces.ts`)

- `projects.yaml`이 있으면, 프로젝트가 지정되지 않은 폴더는 **루트 공통 자산만** 받는다. 다른 프로젝트 자산이 섞여 들어오지 않는다.
- 프로젝트 지정을 해제하면 그 프로젝트의 자산을 정리한다. 다만 로컬에서 수정한 사본은 남긴다 (`inactiveSkillSources`로 바이트 비교, `src/resources/desired.ts`).
- role도 project도 없고 `projects.yaml`도 없을 때만 예전처럼 전부 배포한다 (`return null`).

### 프로젝트가 가질 수 있는 자산 (문서 근거, `docs/guide/distribution.md`)

`knowledge`(rules, claudemd), `skills`, `learnings`, `agents`, `env`, `hooks`, `mcp`, `models`, `docs`, `wiki`

## 2. 혼자 쓸 때의 구성 예

```text
my-ai/                        ← 개인 teamai 저장소
├─ teamai.yaml
├─ manifest/projects.yaml     ← blog, api 선언
├─ skills/
│  ├─ commit-helper/          ← 공통
│  ├─ test-runner/            ← 공통 기본판
│  └─ api/test-runner/        ← api 프로젝트에서만 이 버전으로 교체
└─ rules/
   ├─ coding-style.md         ← 공통
   └─ api/extra-style.md      ← api에서만 추가 (교체가 아니라 추가)
```

```bash
cd ~/work/api && teamai init <my-ai repo> && teamai projects set api && teamai pull
cd ~/work/blog && teamai init <my-ai repo> && teamai projects set blog && teamai pull
```

- 프로젝트 선택은 폴더(작업 공간) 단위로 저장된다고 문서가 설명한다 ("After this directory is set to that project"). 저장 위치는 `미확인`.

## 3. "조금씩 다를 때"의 선택지

| 상황 | 방법 | 이유 |
|---|---|---|
| 규칙을 **덧붙이기**만 하면 됨 | `rules/<project>/추가.md`를 새 이름으로 둔다 | 교체 없이 공통 + 추가가 함께 배포된다. 가장 관리가 쉽다 (`추론`) |
| skill 내용이 **조금 다름** | `skills/<project>/<같은이름>/`에 사본을 둔다 | 통째 교체만 되므로 공통판을 고치면 사본도 직접 고쳐야 한다 |
| 값(경로, 포트, 키)만 다름 | `env/<project>/env.yaml` | skill 본문은 공통으로 두고 차이를 변수로 뺀다 (`추론`: skill이 env를 읽도록 써야 함) |
| 그 프로젝트에만 필요 | 저장소 안 `.teamai/`(self 모드, `teamai init .`) | 프로젝트 저장소가 곧 자산 저장소가 된다. 공통은 `--scope user`로 따로 받는다 (`--inherit-user-scope`) |

- 통째 교체라서 사본이 많아질수록 공통판과 어긋나기 쉽다. 차이는 가능하면 **추가 규칙 파일이나 env**로 빼는 편이 낫다 (`추론`).

## 미확인

- 프로젝트 선택이 저장되는 정확한 파일 위치 (`config.yaml`이 어느 data partition에 있는지)
- self 모드(`.teamai/`)와 `--scope user` 공통 저장소를 같이 쓸 때 같은 이름 항목의 우선순위
- `teamai push`가 namespace 폴더에 올리는 방식 (혼자 쓸 때 PR 대신 직접 push가 되는지)
- 실제 실행 확인
