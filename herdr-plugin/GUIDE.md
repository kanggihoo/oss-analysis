# herdr 플러그인 오픈소스 분석 가이드

- 작성일: 2026-10-22
- 상위 규칙: [AGENTS.md](../AGENTS.md), [OSS_ANALYSIS_WORKFLOW.md](../OSS_ANALYSIS_WORKFLOW.md)를 그대로 따른다(코드 근거, 검증 수준 표기). 이 문서는 이 폴더에만 해당하는 차이를 다룬다.

## 목적과 범위

herdr(코딩 에이전트용 터미널 멀티플렉서)에 붙일 수 있는 플러그인 오픈소스들이 **herdr와 어떻게 연동하는지**(매니페스트 선언, 이벤트 훅, 소켓·CLI 호출)와 각자의 기능을 정리한다. 레포마다 `overview.md`(기능 지도)까지만 쓰고, 기능 스펙과 archify 구조도는 만들지 않는다(사용자 지시, 2026-10-22). 구조는 overview 3절 "구조 해설"을 글로 쓴다.

## 디렉터리

```text
herdr-plugin/
├── GUIDE.md              # 이 문서
├── repos.lock.tsv        # 분석 대상과 기준 SHA
├── repos/<repo>/         # 원본 clone (Git 추적 제외, 읽기만)
├── artifacts/<repo>/     # repo-metadata.txt 등 도구 출력
└── reports/<repo>/       # overview.md
```

루트 `repos/`·`reports/`와 섞지 않는다(`trading/`과 같은 방식). 이 폴더의 레포도 루트 `index.md`에 행을 둔다.

## 분석 대상

| 이름 | URL | 하는 일 (README 기준, 코드 확인 전) |
|---|---|---|
| herdr-bar | https://github.com/jeffarese/herdr-bar | Cmd+K 커맨드 바, 에이전트 아이콘, 퍼지 검색, 자동 탭 제목 |
| herdr-projects | https://github.com/eliasstravik/herdr-projects | 태스크 보드, 태스크별 에이전트 위임 |
| herdr-nvim | https://github.com/ChmaraX/herdr-nvim | nvim 사이드바, 에이전트 주석·코멘트 |
| herdr-auto-title | https://github.com/kryptamine/herdr-auto-title | 탭 제목 자동 생성 |
| herdr-mobile-relay | https://github.com/0cv/herdr-mobile-relay | 폰에서 에이전트 모니터링·승인 응답·터미널 보기, E2EE 전송, 푸시 |
| ovis | https://github.com/devswha/ovis | 폰·웹에서 herdr 레이아웃·채팅·승인 카드·알림, 원격 PC, 푸시 릴레이 |
| collie | https://github.com/AltanS/collie | 웹 대시보드(답장·Ask 카드·STT·히스토리), 멀티플렉서 어댑터, 푸시 |

기준 SHA는 `repos.lock.tsv`, 각 overview의 frontmatter `sha`와 같다.

## 비교 문서

- [모바일 원격 제어 비교와 추천](reports/mobile-remote-comparison.md): herdr-mobile-relay, ovis, collie의 연결 방식·설치·모바일 UX 비교와 추천(2026-10-24).
- [ovis 설치와 폰 접속 가이드(macOS·Windows)](reports/ovis/install-and-mobile-access.md): 플러그인 설치, 텔레메트리 끄기, Tailscale로 폰 접속(2026-10-25).
