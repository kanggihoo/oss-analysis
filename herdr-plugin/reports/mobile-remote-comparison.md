---
sha:
  herdr-mobile-relay: "278b8c2697e47d9b3da0e0e311841123b78226de"
  ovis: "5e4491326143c1f37c7a19631af966d18a960e52"
  collie: "c6a690d817bf8035092e69f4a7429f26b225a66a"
created: 2026-10-24
updated: 2026-10-24
sources:
  - herdr-mobile-relay/QUICKSTART.md
  - herdr-mobile-relay/images/home.jpeg
  - ovis/INSTALL.md
  - ovis/app/store/android/screenshots/phone-2-chat.png
  - ovis/docs/media/look-prompt.png
  - collie/README.md
  - collie/assets/dashboard.png
  - collie/assets/ask-question.png
---

# 모바일에서 herdr 원격 제어: relay · ovis · collie 비교와 추천

세 레포의 개별 기능은 각 `overview.md`에 있다. 이 문서는 "노트북에서 herdr가 돌고, 자리를 비운 동안 폰으로 AI에게 작업을 내리고, 진행을 보고, 가끔 승인·선택에 답한다"는 사용 목적으로 고르기 위해 연결 방식·설치·UX를 비교하고 추천 한 가지를 남긴다.

- 개별 분석: [herdr-mobile-relay](herdr-mobile-relay/overview.md) · [ovis](ovis/overview.md) · [collie](collie/overview.md)
- frontmatter `sha`는 레포별 기준 SHA다(여러 레포를 다루는 문서라 한 값이 아니라 맵으로 적었다).
- **검증 수준 범례**: `코드 확인`은 각 overview에서 코드로 확인한 항목, `추론`은 스크린샷·문서로 판단한 항목이다. 이 문서의 UX 평가는 실행하지 않고 레포가 올려 둔 스크린샷(홍보·스토어용 이미지)만 봤으므로 전부 `추론`이다. `실행 확인`은 없다.

## 1. 사용 조건

- 노트북에서 herdr 실행. 이미 Tailscale 설치됨.
- 폰에서 하려는 일: AI에게 작업 지시, 진행 상황 확인, AI가 응답을 요구할 때 선택.
- 가볍게 쓰고 싶음(많은 기능은 필요 없음). 모바일 UX/UI가 좋아야 함.

## 2. 폰과 PC가 연결되는 방식

| | 연결 경로 | 페어링(폰 등록) | 검증 수준 |
|---|---|---|---|
| **herdr-mobile-relay** | ① Cloudflare 터널(임시 또는 고정 도메인) ② 공동체 게이트웨이(프로젝트가 운영하는 무료 공유 중계 서버) ③ 게이트웨이로 시작해 폰↔PC 직접 연결(WebRTC)로 갈아타기. 어느 경로든 위에 종단간 암호화(E2EE)를 한 겹 더 씌움 | 설정 메뉴에서 QR을 띄우고 폰으로 스캔 | 코드 확인 (relay overview F13~F15) |
| **ovis** | `tailscale serve`로 Tailscale 안에서만 열리는 HTTPS 주소. 폰에도 Tailscale 필요 | `Phone setup` 창의 QR, 또는 페어링 코드·토큰 | 코드 확인 (ovis overview F11, F12) |
| **collie** | ovis와 비슷하게 `tailscale serve` 매핑 하나(코드에서 "정문"). 자기 리버스 프록시·Cloudflare Access를 쓰려면 `COLLIE_SKIP_SERVE=1` | 터미널에서 `collie pair` → 일회용 코드·QR. 접근 조건 여러 개가 AND로 겹침 | 코드 확인 (collie overview F12, F24) |

- Tailscale은 내 기기끼리만 통하는 사설 네트워크다. 외부 서버를 거치지 않고 인터넷에 포트를 열지 않는다.
- relay는 Tailscale을 쓰지 않는다. PC가 Cloudflare나 게이트웨이로 바깥 연결을 먼저 열고, 폰이 그 통로로 들어온다. 중간 서버는 암호문만 전달한다.
- 푸시 알림은 셋 다 Web Push(브라우저 푸시)다.

## 3. 설치와 초기 설정

| | 설치 | 필요한 것 | 비고 |
|---|---|---|---|
| relay | `herdr plugin install 0cv/herdr-mobile-relay` 후 설정 메뉴에서 연결 방식 선택 | Python·Node·Go·sudo 불필요(릴리스 바이너리를 받음) | 임시 터널은 실행할 때마다 주소가 바뀌어 새 QR이 필요. 고정 주소는 Cloudflare에 도메인 등록과 마법사 필요. 게이트웨이 경로는 폰 앱 화면을 `HERDR_PHONE_APP_URL`이나 `make web-deploy`로 따로 구해야 함 |
| ovis | `herdr plugin install devswha/ovis --yes`, 또는 `curl -fsSL https://ovis.sh/install.sh \| sh` | Bun 1.4+, Node 18+(Linux/macOS), herdr 0.9.0+ | 원라이너는 `tailscale serve` 설정과 QR 출력까지 처리하고, 없는 herdr·Bun·Node를 사용자 영역에 설치함. Tailscale 설정을 바꾸므로 동의가 필요 |
| collie | `curl -fsSL https://colliepwa.dev/install.sh \| sh` | Bun, Tailscale | 기능이 많아(기능 지도 37행) 첫 인상은 무겁지만 쓰는 기능만 쓰면 됨 |

검증 수준: relay는 QUICKSTART 문서 기준(`추론`; 설치 스크립트 동작은 relay overview 주장 3에서 `코드 확인`), ovis는 INSTALL.md 기준(`추론`), collie는 README 기준(`추론`).

## 4. 모바일 UX 비교

스크린샷 출처: relay `images/home.jpeg`, collie `assets/dashboard.png`·`assets/ask-question.png`, ovis `app/store/android/screenshots/phone-2-chat.png`·`docs/media/look-prompt.png`.

| | 홈 화면 | 승인 화면 |
|---|---|---|
| **ovis** | Claude 앱 같은 채팅 화면. 하단 "Message Claude…" 입력창과 모델 선택, 상단 채팅/터미널 전환 토글. 작업 로그는 "Worked for 2m · 1 edit · 2 commands"처럼 접혀 있음 | "INPUT NEEDED" 카드에 Yes / Yes and don't ask again / No 버튼 |
| **collie** | 프로젝트별 칩 아래 "1 needs you / 5 working / 1 done" 요약. 에이전트마다 Claude/Codex 아이콘과 경과 시간 | 큰 번호 버튼 3개. 위쪽에는 터미널 출력이 그대로 보임. 하단에 Keys/Type/Quick/Agent 바 |
| **relay** | 폴더별 카드에 탭 수·에이전트 수·경과 시간. 위쪽에 검색·+·기록·설정 아이콘 | 목록 중심 화면, 승인은 폼 |

- 셋 다 다크 테마의 모바일 우선 화면이고 승인 카드가 있다.
- collie는 대시보드형이라 "누가 나를 기다리나"를 한눈에 보기 좋고, ovis는 채팅형이라 "작업을 내리는" 흐름이 자연스럽다.
- 검증 수준: 전부 `추론`(스크린샷만 봄).

## 5. 추천: ovis

이전 대화에서는 보안·라이선스 기준으로 collie를 골랐다. "화장실 갔다 오는 동안 AI에게 작업 지시, 진행 확인, 가끔 선택", "UX가 좋아야 함"이라는 기준이면 ovis가 더 맞다.

1. 채팅 화면이라 폰에서 작업을 내리는 흐름이 Claude나 ChatGPT 앱과 같다.
2. 터미널 출력 대신 대화로 접어 보여 줘서 폰에서 읽기 편하다. collie는 승인 화면에서 터미널 텍스트가 그대로 보인다.
3. 필요하면 진짜 터미널 보기로 전환할 수 있어서 막혔을 때 탈출구가 있다.
4. 설치가 한 줄이고 Tailscale 연결과 QR까지 같이 처리한다.

### 주의할 점

- **텔레메트리가 기본 켜짐이다.** 설치·업데이트 때와 하루 한 번 활성 메시지(에이전트 종류)를 보내고, 안내 화면을 본 뒤 10분이 지나야 전송된다. 끄려면 환경변수 `OVIS_TELEMETRY=0`이나 `DO_NOT_TRACK=1`, 또는 설정 화면 스위치를 쓴다. 켜 두는 게 싫으면 설치 직후에 끈다. (코드 확인: ovis overview 주장 20, `server/telemetry.ts:79-85,182`)
- **푸시 알림이 외부 푸시 서비스를 거친다.** 내용은 암호화돼서 나간다. (코드 확인: ovis overview 외부 호출 소절)
- **필요한 것이 Bun, Node, herdr 0.9.0 이상이다.** collie(Bun, Tailscale)보다 하나 더 필요하지만 이미 herdr를 쓰고 있으면 큰 부담은 아니다.
- **코드 확인 범위가 얕다.** 파일이 2227개라 대부분의 기능을 진입점까지만 읽었고, UX는 스크린샷으로만 봤다.

### 상황별로 갈리는 경우

- 승인 대기 상태를 한눈에 모아 보는 것이 더 중요하면 **collie**(대시보드 요약). 보안 면에서는 비밀값 마스킹, 감사 로그, 허용 목록 기반 실행이 있고 MIT 라이선스다.
- Tailscale을 못 쓰거나 안 쓰고 싶으면 **relay**(중계 서버가 내용을 못 보는 E2EE). 라이선스는 AGPL-3.0-or-later이고, 설치 때 서명 검증 없이 릴리스 바이너리를 받으며 QR 링크에 릴레이 키가 들어간다(relay overview 보안 소절).

설치와 폰 접속 절차(macOS·Windows)는 [ovis 설치와 폰 접속 가이드](ovis/install-and-mobile-access.md)에 따로 정리했다.

## 6. 남은 확인 사항

- [ ] 실제로 ovis를 설치해 폰에서 작업 지시·승인 응답·푸시 도착을 확인하기(`실행 확인` 없음).
- [ ] ovis의 `OVIS_TELEMETRY=0`이 설치 시점의 첫 전송까지 막는지(코드 `server/telemetry.ts`의 설치 이벤트 경로).
- [ ] collie의 "Full reply" 카드·History 화면이 채팅형 UX로 충분한지(스크린샷 미확인).
