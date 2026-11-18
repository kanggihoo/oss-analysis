# 영상 오픈소스 분석 가이드

- 작성일: 2026-11-18
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

영상을 입력으로 읽거나 출력으로 만드는 도구를 분석한다. 비교 축은 두 가지다.

- **영상을 읽는 쪽**: 영상에서 프레임, 전사문, shot 단위 분석을 뽑아 agent가 쓰게 한다. `claude-video`(`/watch` skill), `rea-video`(shot별 실사·AI·코드 판별)가 여기에 든다.
- **영상을 만드는 쪽**: 코드나 recipe로 영상을 렌더링하거나 생성한다. `hyperframes`(HTML 렌더링)가 여기에 든다. `capsule-cinema`(영상 recipe로 AI 쇼츠 제작)는 후보다.

`rea-video`의 README는 분해 결과를 `capsule-cinema`로 넘겨 재제작한다고 설명한다. 그래서 두 축이 이어지는 지점(읽은 결과를 만드는 쪽이 받는 형식)이 비교의 관심사다. 이 연결은 README 기준이라 `미확인`이고, 코드로 확인하면 여기에 적는다.

- 분석 목적: 레포마다 다르다. `hyperframes`는 학습, `claude-video`는 요청 때 기본값(기능 스펙화), `rea-video`는 **미정**이다. 사용자가 정하면 여기에 적는다.
- 현재 단계: `claude-video`는 feature map과 구조도까지 있고 범위 승인을 기다린다. `hyperframes`는 기능 스펙 8개가 있다. `rea-video`와 `capsule-cinema`는 clone만 했고 overview는 아직 없다.

## 디렉터리

```text
video/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt 등 도구 출력
└── reports/<repo>/       # overview.md, capabilities/, diagrams/
```

루트 `repos/`·`reports/`와 섞지 않는다. 이 폴더의 레포는 루트 `index.md`에 `<repo> (video/)` 이름으로 행을 둔다.

`claude-video`와 `hyperframes`는 2026-11-18에 루트 `reports/`·`artifacts/`·`repos/`에서 옮겨 왔다. 두 폴더 안의 상대 링크는 레포 폴더 안에서만 닫혀 있어 그대로 유효하다. `repo-metadata.txt`의 `repo_dir=repos/<repo>`는 이 폴더 기준으로 읽는다.

## 분석 대상

| 이름 | URL | 라이선스 (파일 확인) | 상태 |
|---|---|---|---|
| claude-video | https://github.com/bradautomates/claude-video | MIT (`overview.md` 1절) | 분석함. 로컬 clone 없음(`repos/claude-video` 없음) |
| hyperframes | https://github.com/heygen-com/hyperframes | Apache-2.0 (`overview.md` 1절) | 분석함 |
| rea-video | https://github.com/JuneYaooo/rea-video | Apache-2.0 (`repos/rea-video/LICENSE`) | clone 완료(`538eb3a`, 2026-11-18). 분석 시작 전 |
| capsule-cinema | https://github.com/JuneYaooo/capsule-cinema | Apache-2.0 (`repos/capsule-cinema/LICENSE`) | clone 완료(`7dc9161`, 2026-11-18). 분석 시작 전 |

기준 SHA는 `repos.lock.tsv`와 같다.

## 먼저 볼 곳

레포마다 `reports/<repo>/overview.md`와 `next.md`에서 시작한다. `rea-video`는 README가 가리키는 `rea_video/`(CLI 본체), `rea_video/capabilities/`(모델 capability 표), `eval/`, `docs/videomd.md`를 먼저 열어 역할을 코드로 확인한다(모두 `미확인`).
