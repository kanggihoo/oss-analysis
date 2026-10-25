---
sha: "5e4491326143c1f37c7a19631af966d18a960e52"
created: 2026-10-25
updated: 2026-10-25
sources:
  - INSTALL.md
  - docs/guide.md
  - install.ps1
  - herdr-plugin.toml
  - scripts/plugin.ts
  - scripts/plugin.ps1
  - server/telemetry.ts
---

# ovis 설치와 폰 접속 가이드 (macOS · Windows)

- **상위 개요**: [overview.md](overview.md)
- **목적**: 노트북에서 이미 돌고 있는 herdr에 ovis 플러그인을 설치하고, Tailscale로 폰에서 접속한다. 텔레메트리(익명 사용 통계 전송)는 첫 실행 전에 끈다.
- **검증 수준**: `코드 확인`은 기준 SHA의 코드·매니페스트를 직접 읽어 확인한 것, `추론`은 `INSTALL.md`·`docs/guide.md` 문서만 근거인 것, `미확인`은 ovis 문서에 없는 일반 지식이다. 이 문서는 읽기만 하고 실제로 설치·실행하지 않았으므로 `실행 확인`은 없다. 경로는 `repos/ovis/` 기준이다.

## 1. 한눈에 보기

1. herdr 0.9.0 이상이 실행 중인지, Bun과 Git이 있는지 확인한다.
2. 플러그인을 설치한다.
3. 설정 파일에 텔레메트리 끄기를 쓴다.
4. 서버를 시작하고 `/api/health`로 확인한다.
5. `Phone setup` 액션으로 Tailscale HTTPS 주소와 QR을 만든다.
6. 폰에서 QR을 스캔하고 홈 화면에 설치한 뒤 알림을 켠다.

### 구조

ovis 서버는 노트북에서 `127.0.0.1:7317`로만 열린다. 폰은 이 주소로 직접 못 들어오므로 `tailscale serve`가 Tailscale 안에서만 열리는 HTTPS 주소를 이 포트로 이어 준다. 인터넷 전체에 공개하는 `tailscale funnel`은 쓰지 않는다(`INSTALL.md` 5절, `추론`).

### 플랫폼 차이 요약

| | macOS | Windows |
|---|---|---|
| 지원 | 지원(`herdr-plugin.toml` `platforms`에 `macos`, 코드 확인) | Windows x64만 지원(`install.ps1:6-8`, 코드 확인) |
| 필요한 것 | herdr 0.9.0+, Bun 1.4+, Node 18+ | herdr 0.9.0+, Bun 1.4+, **Git for Windows**. Node는 불필요 |
| 명령어 셸 | 터미널(zsh) | PowerShell |
| 액션 이름 | `start` `stop` `status` `phone` | `start-windows` `stop-windows` `status-windows` `phone-windows` |
| 터미널 화면 | herdr에 직접 붙는 라이브 터미널 | "화면 미러" 방식(`INSTALL.md` 1절, `추론`). 세부 차이는 미확인 |
| 원라이너 | `curl -fsSL https://ovis.sh/install.sh \| sh` | `irm https://ovis.sh/install.ps1 \| iex` |

Windows 액션이 별도로 있는 이유는 매니페스트가 플랫폼별로 명령을 따로 선언하기 때문이다(`herdr-plugin.toml:34-110`, 코드 확인). `[[startup]]`이 선언돼 있어서 설치 후에는 herdr가 시작될 때 ovis도 자동으로 올라온다(코드 확인).

## 2. macOS

### 2.1 준비 확인

```bash
herdr --version          # 0.9.0 이상
herdr status server      # 서버가 실행 중이어야 함
bun --version            # 1.4 이상
node --version           # 18 이상
git --version
tailscale status         # PC가 tailnet에 연결돼 있는지
```

- Bun이 없으면 `curl -fsSL https://bun.sh/install | bash`로 설치한다(`INSTALL.md` 1절, `추론`). 설치 위치는 `~/.bun/bin`이다.
- herdr가 `bun`이나 `node`를 못 찾는다고 하면, herdr를 띄운 셸의 PATH에 이 둘이 있어야 한다. PATH를 고친 셸에서 herdr를 다시 시작한다(`INSTALL.md` 3A절, `추론`).
- Tailscale 명령줄 `tailscale`이 없으면 Tailscale 설치 방식에 따라 CLI를 따로 연결해야 할 수 있다. 이 부분은 ovis 문서에 없는 일반 지식이다(`미확인`).

### 2.2 설치와 텔레메트리 끄기

한 줄 설치 스크립트 대신 플러그인 설치를 쓴다. 원라이너는 원격 스크립트를 내려받아 실행하고 Tailscale 설정까지 바꾸기 때문이다(`INSTALL.md` 2절, `추론`).

```bash
# 1) 설치. herdr가 clone, bun install, bun run build를 하며 1분쯤 걸린다.
herdr plugin install devswha/ovis --yes

# 2) 설정 파일에 텔레메트리 끄기를 쓴다. 쉘 환경변수가 아니라 플러그인 설정 파일이다.
CONFIG_DIR="$(herdr plugin config-dir devswha.ovis)"
mkdir -p "$CONFIG_DIR"
printf 'OVIS_TELEMETRY=0\nDO_NOT_TRACK=1\n' >> "$CONFIG_DIR/env"

# 3) 서버 시작
herdr plugin action invoke devswha.ovis.start
```

- 설정 파일은 `KEY=value` 줄로 쓰고, 파일 이름은 `env`(점 없음)다. 0.3.25 이후 체크아웃은 `.env`도 읽고 둘 다 있으면 `.env`가 우선한다(`INSTALL.md` 3A절, `추론`).
- `start` 액션은 요청을 큐에 넣고 확인 JSON만 출력한다. 실제 출력은 `herdr plugin log list`로 볼 수 있다(`추론`).

### 2.3 확인

```bash
curl -s http://127.0.0.1:7317/api/health     # "ok":true 이면 정상
herdr plugin action invoke devswha.ovis.status
herdr plugin log list
```

- 포트 7317이 이미 쓰이면 서버가 다음 포트(17317, 27317, 37317, 47317)를 고르고 그 포트를 기억한다(`docs/guide.md` 설정 표 `PORT`, `추론`). 이 경우 `/api/health`는 그 포트로 확인한다.
- 설정 파일 읽힘 여부는 `bun "$root/scripts/plugin.ts" status`가 읽은 파일을 출력해 알려 준다(`INSTALL.md` 3A절, `추론`). `$root`는 `herdr plugin list --json`의 `devswha.ovis` 항목 `plugin_root`다.

### 2.4 폰 접속 주소 만들기

```bash
herdr plugin action invoke devswha.ovis.phone
```

herdr 안에 `Phone setup` 창이 열린다. 이 창은 Tailscale이 켜져 있고 아직 서빙하지 않았으면 `tailscale serve`를 실행하고, 되돌리는 방법과 함께 주소를 QR로 보여 준다(`herdr-plugin.toml:84-110`, `INSTALL.md` 5절).

직접 하려면 다음과 같다.

```bash
tailscale serve --bg --https=443 http://127.0.0.1:7317
```

브라우저에서 `http://127.0.0.1:7317` → **Settings → Phone & devices**에서도 QR을 볼 수 있다.

## 3. Windows

### 3.1 준비 확인 (PowerShell)

```powershell
herdr --version          # 0.9.0 이상
herdr status server
bun --version            # 1.4 이상
git --version            # Git for Windows 필요
tailscale status
```

- Windows x64만 지원한다. 다른 아키텍처는 설치 스크립트가 중단한다(`install.ps1:6-8`, 코드 확인).
- Git for Windows가 없으면 설치 스크립트가 중단한다(`install.ps1:23-25`, 코드 확인). 설치처는 <https://git-scm.com/download/win>이다.
- Bun이 herdr 실행 중에 설치돼도 herdr 재시작이 필요 없다. 플러그인 실행기가 매번 현재 사용자 PATH와 `%USERPROFILE%\.bun\bin`을 읽는다(`scripts/plugin.ps1:1-6`, 코드 확인).
- Node는 필요 없다(`INSTALL.md` 1절, `추론`).

### 3.2 설치와 텔레메트리 끄기

```powershell
# 1) 설치
herdr plugin install devswha/ovis --yes

# 2) 설정 파일에 텔레메트리 끄기를 쓴다
$ConfigDir = herdr plugin config-dir devswha.ovis
New-Item -ItemType Directory -Force $ConfigDir | Out-Null
Add-Content -Path "$ConfigDir\env" -Value "OVIS_TELEMETRY=0","DO_NOT_TRACK=1" -Encoding ascii

# 3) 서버 시작
herdr plugin action invoke devswha.ovis.start-windows
```

- `-Encoding ascii`를 쓰는 이유: Windows PowerShell 5.1에서 `>`나 기본 인코딩으로 쓰면 UTF-16이나 BOM이 붙을 수 있어 설정 파일이 안 읽힐 수 있다. 이는 일반 지식이라 `미확인`이다. 전부 ASCII 문자라 ascii로 써도 안전하다.
- Windows에서 `herdr plugin config-dir`가 `\` 경로를 돌려주는지는 직접 확인하지 못했다(`미확인`). 경로가 이상하면 `$ConfigDir` 값을 출력해 보고 `env` 파일을 그 폴더에 만든다.
- 원라이너(`irm https://ovis.sh/install.ps1 | iex`)를 쓰면 없는 herdr와 Bun을 사용자 영역에 설치해 준다(`install.ps1:27-60`, 코드 확인). 스크립트 내용은 직접 읽고 쓰는 것이 안전하다.

### 3.3 확인

```powershell
curl.exe -s http://127.0.0.1:7317/api/health     # PowerShell의 curl 별칭 대신 curl.exe
herdr plugin action invoke devswha.ovis.status-windows
herdr plugin log list
```

- PowerShell에서 `curl`은 `Invoke-WebRequest` 별칭이라 `curl.exe`를 써야 한다(일반 지식, `미확인`).
- 서버가 시작에 실패하면 `plugin.ps1`이 `server.log`의 끝부분을 오류로 보여 준다(`scripts/plugin.ps1:28-34`, 코드 확인).
- Windows는 7317이 Hyper-V·WSL2·Docker에 예약돼 있으면 다음 포트를 고르고 기억한다(`docs/guide.md` `PORT` 설명, `추론`).

### 3.4 폰 접속 주소 만들기

```powershell
herdr plugin action invoke devswha.ovis.phone-windows
```

macOS와 같은 `Phone setup` 창이 열린다(`herdr-plugin.toml:91-110`, 코드 확인). 직접 하려면 다음과 같다. 포트가 7317이 아닐 수 있으니 3.3에서 확인한 포트를 쓴다.

```powershell
tailscale serve --bg --https=443 http://127.0.0.1:7317
```

## 4. 폰에서 접속하기 (macOS · Windows 공통)

1. 폰에 Tailscale 앱을 설치하고 PC와 같은 계정으로 로그인해서 켜 둔다.
2. 폰 카메라로 `Phone setup` 창의 QR을 스캔하거나, 출력된 주소(`https://<PC이름>.<tailnet>.ts.net`)를 폰 브라우저에 입력한다.
3. 같은 Tailscale 계정의 내 기기는 본인으로 인정돼 설정 없이 들어온다. 다른 계정이거나 태그가 붙은 기기는 거부되거나 페어링이 필요하다(`INSTALL.md` 5절, `추론`).
4. 페어링을 요구하면 PC에서 **Settings → Phone & devices**의 6자리 코드를 폰에 한 번 입력한다. 화면 없는 PC에서는 아래로 코드를 터미널에 띄운다.
   - macOS: `bun "$root/scripts/plugin.ts" pair`
   - Windows: `bun "$root\scripts\plugin.ts" pair` (`plugin.ts`가 `pair` 명령을 처리한다. `scripts/plugin.ts:685`, 코드 확인)
5. 내 폰인데도 코드를 요구하면, 같은 계정 하나만 쓰는 tailnet에서 설정 파일에 `OVIS_TAILSCALE_SERVE_ONLY=1`을 추가하고 재시작하면 코드 없이 들어온다(`INSTALL.md` 5절, `추론`).
6. 브라우저 메뉴에서 **홈 화면에 추가**(Android Chrome은 **앱 설치**)를 한다. HTTPS 주소여야 설치와 알림이 된다(`INSTALL.md` 5절, `추론`).
7. 설치한 앱을 열고 **Settings**에서 알림 권한을 허용한다. 입력 대기·완료·터미널 종료 때 푸시가 온다(`overview.md` F10).

여기서 `$root`는 다음으로 구한다.

```bash
# macOS
root=$(herdr plugin list --json | bun -e 'const d = JSON.parse(await Bun.stdin.text()); console.log(d.result.plugins.find((p) => p.plugin_id === "devswha.ovis")?.plugin_root ?? "")')
```

```powershell
# Windows
$root = ((herdr plugin list --json | ConvertFrom-Json).result.plugins | Where-Object { $_.plugin_id -eq 'devswha.ovis' } | Select-Object -First 1).plugin_root
```

Windows 쪽 명령은 `install.ps1`의 `Find-Plugin` 함수와 같은 방식이다(`install.ps1:66-69`, 코드 확인).

## 5. 텔레메트리 상세

| 항목 | 내용 | 검증 수준 |
|---|---|---|
| 기본값 | 켜짐 | 코드 확인 (`server/telemetry.ts:182`) |
| 막는 방법 | `OVIS_TELEMETRY`가 `0`/`false`/`off`/`no`이거나, `DO_NOT_TRACK`이 있고 `0`이 아니면 전송 안 함. `CI`나 herdr 테스트 환경에서도 막힘 | 코드 확인 (`server/telemetry.ts:79-85`) |
| 전송 시점 | 안내 화면을 본 시각(`notice_seen_at`)이 기록돼야 하고, 그 뒤 10분이 지나야 전송 | 코드 확인 (`server/telemetry.ts:26`(유예 10분), `:350-365,415-425`(전송 조건)) |
| 환경변수의 위치 | 플러그인은 `config-dir`의 `env` 파일. 소스 설치는 서버를 시작하는 명령의 환경 | 추론 (`INSTALL.md`) |
| 앱에서 확인 | Settings → About → Anonymous usage counts에서 다음 메시지와 스위치를 볼 수 있다. 환경변수가 스위치보다 우선 | 추론 (`docs/guide.md`) |
| 받는 쪽 | `herdr-web-ui-telemetry.devswha.workers.dev` | 코드 확인 (`overview.md` 외부 호출 소절) |

설정 파일을 서버 시작 전에 만들면 어느 시점에도 전송되지 않는다. 이미 시작했다면 stop → start로 재시작하면 환경변수가 적용된다.

## 6. 문제가 생기면

| 증상 | 확인할 것 |
|---|---|
| `bun`/`node`를 못 찾는다는 설치 오류 | herdr를 띄운 셸의 PATH에 Bun이 있는지. macOS는 PATH를 고친 셸에서 herdr를 다시 시작. Windows는 사용자 PATH를 매번 읽으므로 보통 재시작 불필요 |
| `installing over a locally linked plugin is refused` | `herdr plugin unlink devswha.ovis` 후 다시 설치 |
| 연결 거부 | 서버 미실행. `status` 액션과 `herdr plugin log list`, 상태 폴더의 `server.log` 확인 |
| 폰에서 화면은 보이지만 앱 설치·알림이 안 됨 | HTTPS 주소인지 확인(`http://`이면 안 됨) |
| herdr 소켓 오류 | herdr가 실행 중인지. 이름 있는 세션이면 `HERDR_SOCKET`으로 지정 |

위 표는 `INSTALL.md` 3~4절을 근거로 한 `추론`이다.

## 7. 업데이트와 제거

```bash
# macOS 업데이트(앱 안): Settings → About → Update and restart
# 재설치로 업데이트하려면:
herdr plugin install devswha/ovis --yes
herdr plugin action invoke devswha.ovis.stop
herdr plugin action invoke devswha.ovis.start

# macOS 제거
herdr plugin action invoke devswha.ovis.stop
herdr plugin uninstall devswha.ovis
```

```powershell
# Windows 제거
herdr plugin action invoke devswha.ovis.stop-windows
herdr plugin uninstall devswha.ovis
```

- 자동 업데이트(`OVIS_AUTO_UPDATE`)는 기본 `0`이다. 앱은 새 릴리스를 10초 뒤 처음 확인하고 이후 5분마다 확인한다(`docs/guide.md`, `추론`).
- 제거해도 상태 폴더(푸시 키·기기 목록, 기본 `~/.config/ovis`)와 플러그인 설정 폴더(토큰이 있을 수 있음)는 남는다. 지우려면 직접 지운다(`INSTALL.md` Uninstall, `추론`). Windows의 정확한 상태 폴더 위치는 미확인이다.

## 8. 남은 확인 사항

- [ ] 실제 macOS·Windows에서 설치해 `/api/health`, `Phone setup`, 폰 접속, 푸시 도착을 확인하기(`실행 확인` 없음).
- [ ] macOS에서 Tailscale CLI 연결 방식과 `tailscale serve`의 HTTPS 인증서 활성화 안내.
- [ ] Windows에서 `herdr plugin config-dir` 출력 형식과 `env` 파일 인코딩이 실제로 읽히는지.
- [ ] Windows 화면 미러 방식이 라이브 터미널과 어떻게 다른지(`docs/guide.md` 터미널 절).
- [ ] iPhone에서 푸시를 받으려면 홈 화면 설치가 필요한지(ovis 문서 미확인).
