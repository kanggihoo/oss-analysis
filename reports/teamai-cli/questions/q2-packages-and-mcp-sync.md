---
sha: "a44493f6ec20e32197a1bca4c3e000be2cd6fe70"
created: 2026-10-24
updated: 2026-10-24
sources:
  - src/pkg/register-command.ts
  - src/pkg/commands.ts
  - src/pkg/manifest.ts
  - src/pkg/types.ts
  - src/pkg/pkg-hint.ts
  - src/pkg/env-detect.ts
  - src/pkg/adapters/base.ts
  - src/pkg/adapters/npm.ts
  - src/pkg/adapters/claude-plugin.ts
  - src/utils/exec.ts
  - src/plugin-lifecycle.ts
  - src/resources/marketplace.ts
  - src/local-agent.ts
  - src/hook-handlers.ts
  - src/index.ts
  - src/push.ts
  - src/pull.ts
  - src/mcp-cmd.ts
  - src/resources/mcp.ts
  - src/resources/mcp-format.ts
  - src/mcp-reconcile.ts
  - src/mcp-resolved-files.ts
  - src/mcp-git-exclude.ts
  - src/utils/mcp-manifest.ts
  - src/doctor-delivery.ts
  - src/types.ts
  - docs/guide/sharing.md
---

# [Q] teamai의 `packages`와 `mcp`: 남의 플러그인·MCP를 선언해 두고 기기마다 동기화할 수 있나? 원본 변경을 감지하나?

> **결론**: 둘 다 "선언 → 설치"는 하지만 **업스트림(원본) 변경 감지는 없고, "무엇이 바뀌었나"를 보여 주는 diff도 없다.** 감지하는 것은 (1) 선언 자체가 바뀌었는지(`packages`는 선언 해시, `mcp`는 렌더한 엔트리 해시)와 (2) `doctor`가 보는 선언 대비 설치 불일치뿐이고, 그나마 버전 문자열 비교 수준이다. 고정(pin)한 버전을 내 기기들에 맞춰 놓는 용도로는 쓸 만하지만, "남의 스킬·플러그인이 바뀌었나"를 알려 주는 도구는 아니다.

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: `코드 확인` 위주. 순수 함수 일부만 `실행 확인`(4절). `claude` CLI, npm, 앱은 실행하지 않았다. 외부 시스템의 실제 동작은 `미확인`.
- **기준 SHA**: `a44493f` (`repos/teamai-cli`, 작업트리 clean)
- 읽은 것: `src/pkg/*`, `src/pkg/adapters/*`, `src/mcp-*.ts`, `src/resources/mcp*.ts`, 호출부 일부(`pull.ts`, `hook-handlers.ts`, `index.ts`), 문서 `docs/guide/sharing.md`. 테스트는 사례명 검색만 했고 열지 않았다(테스트를 읽은 것은 실행 확인이 아니다).

---

## 1. 질문 및 결론

- **질문**: 개인 스킬 저장소(`my-skills`)처럼, 남이 만든 Claude 플러그인과 MCP 서버를 선언만 해 두면 내 기기들에 설치·동기화되는가? 원본이 바뀌었는지, 무엇이 바뀌었는지 알 수 있는가?
- **핵심 결론**

| 질문 | `packages` (npm, Claude 플러그인) | `mcp` (MCP 서버 주입) |
|---|---|---|
| 선언만 하면 기기에 설치되나 | 된다. 단 **수동**: pull 뒤 `teamai packages`를 직접 실행해야 한다. 세션 시작 때 "선언이 바뀌었다"는 안내만 나온다 (`코드 확인`) | 된다. **pull이 자동**으로 각 AI 도구 설정 파일에 쓴다 (기본 `autoApply: true`) (`코드 확인`) |
| 선언이 바뀐 것을 감지하나 | 한다. 선언 해시 vs 락 해시, 불일치 여부(참/거짓)만 안다 (`코드 확인`) | 한다. 렌더한 엔트리 해시 vs 기록된 해시, 바뀌면 `updated` (`코드 확인`) |
| 설치된 것이 선언과 다른지 | `doctor`에서만, 버전 문자열·범위 비교 (`코드 확인`) | `doctor`에서 깊은 비교. 단 **사용자가 손으로 고친 관리 항목**은 pull이 되돌리지 않는다 (`코드 확인` + `추론`) |
| **업스트림에 새 버전이 있는지** | **감지 안 함** (`코드 확인`) | **감지 안 함**. 선언에 버전 필드조차 없다 (`코드 확인`) |
| **무엇이 바뀌었는지(diff)** | 안 보여 줌. 개수만 알림 (`코드 확인`) | 안 보여 줌. `added/updated/removed 도구/서버` 한 줄 (`코드 확인`) |

---

## 2. 동작 설명

용어를 먼저 정한다.

- **선언**: 팀(여기서는 내 개인) 저장소의 `teamai.yaml`(`packages`)과 `mcp/mcp.yaml`에 적은 "이게 설치돼 있어야 한다"는 목록.
- **락(lock)**: `teamai.lock`. teamai가 설치 직후 남기는 기록 파일. (npm의 package-lock처럼 "고정"이 아니라 아래 A2에서 보듯 **기록**에 가깝다.)
- **마켓플레이스**: Claude Code 플러그인 목록을 담은 저장소(예: `anthropics/claude-plugins-official`). 플러그인은 `플러그인이름@마켓플레이스이름`으로 부른다.
- **관리 매니페스트**: MCP에서 teamai가 쓴 항목의 이름과 해시를 적어 두는 `managed-mcp.json`.
- **엔트리 해시**: 도구 설정 파일에 쓰는 서버 항목 하나를 JSON으로 만든 뒤 sha1 앞 16자리를 취한 값.

### A. `packages`

#### A1. 선언 형식 (`코드 확인`)

```yaml
packages:                          # teamai.yaml의 한 키 (src/pkg/manifest.ts:90-105가 이 키만 읽음)
  npm:
    - name: typescript             # 필수, 공백 불가
      version: "*"                 # 선택, 기본 "*"
      global: true                 # 선택: 기기 전체 CLI로 설치
      registry: https://...        # 선택: http(s)만, 계정 정보 포함 금지
  claude:
    marketplaces:
      - name: claude-plugins-official      # 필수, 중복 불가
        repo: anthropics/claude-plugins-official   # 필수 (문자열)
        ref: v1.0                          # 선택
    plugins:
      - name: code-review@claude-plugins-official  # 필수, plugin@marketplace 형식
        version: "1.2.0"                   # 선택
        scope: user                        # 선택: user | project | local
```

| 항목 | 규칙 | 근거 |
|---|---|---|
| 알 수 없는 키 | 모두 거부(`.strict()`) | `src/pkg/types.ts:26,32,38,43,48` |
| npm `version` | 기본 `'*'`. 설치할 때 `name@version`으로 그대로 전달, `'*'`이면 이름만 | `types.ts:10`, `npm.ts:82-84` |
| 플러그인 이름 | `plugin@marketplace` 형식이고 그 마켓플레이스가 `marketplaces`에 선언돼 있어야 함 | `types.ts:67-83` |
| 마켓플레이스 `ref` | 마켓플레이스 소스 문자열에 붙여 전달(`repo@ref`, URL이면 `repo#ref`) | `claude-plugin.ts:40-46` |
| 플러그인 `version` | **설치 인자에 들어가지 않는다.** `doctor` 비교에만 쓰인다 | 설치 인자 `claude-plugin.ts:248-252`, 비교 `276-292` |
| `repo` 문자열 해석 | GitHub 약식·URL·경로 중 무엇을 받는지는 Claude CLI가 정함 | `미확인` |
| 공식 마켓플레이스 | `claude-plugins-official`은 이름만 써도 `anthropics/claude-plugins-official`로 보충 | `commands.ts:34-36,102-105` |

- 버전 고정 여부 정리: npm은 `version`으로 **고정 가능**. 마켓플레이스는 `ref`로 고정을 **요청**한다(실제 적용은 Claude CLI에 달림, `미확인`). **플러그인 `version`은 고정이 아니라 검사용**이다.
- 명령으로 선언을 추가할 수도 있다: `teamai packages install <대상>`은 `teamai.yaml`에 선언을 쓴 뒤 설치한다 (`commands.ts:127-174,272-275`). 쓴 선언을 팀에 올리려면 `teamai push`가 필요하고, push는 `packages` 키가 유효한지만 검사한다 (`push.ts:940-955`, `docs/guide/sharing.md:263-284`).

#### A2. 설치 흐름 (`코드 확인`)

`teamai packages [target]` → `pkgInstall()` (`register-command.ts:39-54`, `commands.ts:184`)

| 단계 | 내부 동작 | 근거 |
|---|---|---|
| 1 | 팀 저장소 로컬 복제본에서 `teamai.yaml`의 `packages`를 읽고, 락 위치(데이터 홈)를 정함 | `commands.ts:188-191` |
| 2 | `target`이 있으면 선언 객체를 메모리에서 수정, 선언이 하나도 없으면 "No packages are declared"로 종료 | `commands.ts:205-209` |
| 3 | 스키마 검증 (실패하면 예외) | `commands.ts:176-182,210` |
| 4 | 이전 락을 읽고 새 락을 만든다. `target` 없이 실행했을 때만 `declarationHash`를 현재 선언의 sha256으로 갱신 | `commands.ts:212-242`, 해시 `manifest.ts:138-174` |
| 5 (npm) | (전역 여부, 레지스트리)별로 묶어 `npm install [--global] name@ver ... [--registry url]` 실행. 프로젝트용은 pnpm이면 `pnpm add`. 로컬 설치는 현재 폴더에 `package.json`이 있어야 함 | `npm.ts:185-232` |
| 5' (npm 스냅샷) | 로컬은 `package-lock.json`(pnpm이면 `pnpm list --json`), 전역은 `npm list --global --depth=0 --json`에서 선언된 이름의 버전·integrity를 뽑는다 | `npm.ts:117-178` |
| 6 (Claude) | `claude plugin --help`(5초 제한)가 성공해야 진행 → `claude plugin marketplace list --json` → 선언된 마켓플레이스마다 없으면 `claude plugin marketplace add <repo[@ref]> --scope <범위>` → 플러그인마다 `claude plugin install <이름> --scope <범위> --yes` | `claude-plugin.ts:84-91,189-257` |
| 6' (Claude 스냅샷) | `claude plugin list --json`, `marketplace list --json`에서 선언된 것만 골라 락에 기록 | `claude-plugin.ts:125-160` |
| 7 | `teamai.lock`(YAML) 저장 | `commands.ts:276-277`, `manifest.ts:134-136` |

- **환경 감지는 설치 경로에서 쓰이지 않는다.** `detectPackageEnvironment()`(`node`/`npm`/`claude --version` 확인)는 `doctor` 보고서에서만 호출된다 (`env-detect.ts:14-27`, 호출 `commands.ts:314`, 코드 전체 검색 결과 다른 호출 없음). 설치 때는 어댑터가 각자 확인한다(`claude plugin --help`, `package.json` 존재).
- **외부 명령은 셸 없이 인자 배열로 실행**한다 (`shell: false`, `src/utils/exec.ts:30-36`).
- **어디에 무엇이 저장되나**
  - 락은 작업 폴더가 아니라 **데이터 홈**의 `teamai.lock`에 둔다 (`manifest.ts:24-26,28-39`). 데이터 홈이 user 범위에서 `~/.teamai`인지는 `types.ts:2933-2934`의 주석 근거이고, 실제 경로 계산은 열어 보지 않았다 (`추론`).
  - 락 내용: `declarationHash`, (user 범위일 때) 프로젝트별 npm 선언 해시, npm 항목(이름·**설치된** 버전·integrity·resolved), 마켓플레이스(이름·source·repo·ref·설치 경로), 플러그인(id·버전·scope·enabled·설치 경로) (`types.ts:93-132`).
  - **락은 다음 설치의 입력이 아니다.** 이전 락의 `packages`는 Claude 마켓플레이스 비교에만 읽히고(`previousPackages`, `claude-plugin.ts:200-214,305-306`), npm 항목과 플러그인 버전은 읽는 곳이 `src/pkg` 안에 없다(검색 결과). 그래서 락은 npm package-lock 같은 "재현용 고정"이 아니라 **마지막 설치 결과의 기록**이다.
  - 락은 git에 올라가는 파일이 아니다(데이터 홈). 그래서 락 변경 이력을 git으로 볼 수도 없다 (`코드 확인`: 락 위치 + 덮어쓰기. 이력 부재는 `추론`).

#### A3. 변경 감지

| 감지 대상 | 하는가 | 기준 | 사용자에게 보이는 것 | 수준 |
|---|---|---|---|---|
| **선언이 바뀜** (팀 저장소의 `packages`) | 한다 | 현재 선언 해시 ≠ 락의 `declarationHash` (락이 없어도 불일치) | 세션 시작에 에이전트 컨텍스트로 "Team package declarations changed (npm 2개 and Claude plugin 1개). Review ... run `teamai packages`" 한 번. **어떤 항목이 바뀌었는지는 없고 개수만** | `코드 확인` |
| **설치된 것이 선언과 다름** | `doctor`에서만 | npm: 락/전역 목록의 버전이 선언 범위를 만족하는지(`semver`), Claude 플러그인: 선언 `version`이 있을 때 `claude plugin list`의 버전과 문자열 비교, 마켓플레이스: 등록 여부·소스 일치·ref | `✔/✖ 이름 declared X, installed Y` 줄 | `코드 확인` |
| **업스트림에 새 버전** | **안 한다** | 레지스트리 조회, `claude plugin update`, `marketplace update`가 `src/pkg`에 없다 (검색 결과). npm 주석도 dist-tag(`latest`, `next`)는 레지스트리 없이 검사 불가라고 적었다 (`npm.ts:74-80`) | 없음 | `코드 확인`(검색) |
| **무엇이 바뀌었나(diff)** | **안 한다** | `--dry-run`은 실행할 명령을 출력할 뿐(`[dry-run] Would run: ...`) | 설치 후에는 npm·claude의 출력 스트림과 "wrote teamai.lock" 한 줄 | `코드 확인` |

- **선언 해시의 중요한 성질**: 선언 텍스트만의 해시다(키 순서는 무시하고 정렬해서 해시, `manifest.ts:138-159`). 업스트림에 새 버전이 나와도 입력이 같으므로 해시는 변할 수 없다. 4절 실행 A에서 확인했다 (`실행 확인`).
- **알림 경로**: SessionStart 훅이 `computePackageHintState`로 비교(`pkg-hint.ts:56-89`) → 세션당·해시당 한 번만(`pkg-hint.ts:118-156`). 백그라운드 pull이 선언을 바꿨으면 pull 전후 해시를 비교해 다음 프롬프트에 안내(`pkg-hint.ts:158-191`, `hook-handlers.ts:138-150,517-530`). `TEAMAI_PACKAGE_HINT_DISABLED=1`이면 끈다 (`pkg-hint.ts:74`).
- 안내문에 "TeamAI never installs third-party package or plugin code automatically at SessionStart"라고 적혀 있다(`pkg-hint.ts:36`). 즉 **남의 코드를 자동 설치하지 않는 것이 의도**다. 이 의도는 문구 근거이고 이유는 `추론`.
- `teamai packages` 자체는 "무엇이 다른지" 계산하지 않고 선언된 것을 **매번 전부 다시 설치 명령으로 실행**한다. 건너뛰는 것은 이미 맞게 등록된 마켓플레이스뿐이다 (`claude-plugin.ts:229`). 이미 설치된 플러그인에 `claude plugin install`을 다시 하면 갱신되는지는 Claude CLI의 동작이라 `미확인`.

#### A4. 갱신·제거, 사용자 설치와의 구분

| 상황 | 설치된 것에 일어나는 일 | 근거 | 수준 |
|---|---|---|---|
| npm `version` 선언을 바꿈 | 다음 `teamai packages`가 `npm install name@새버전` 실행 | `npm.ts:82-84,224` | `코드 확인` |
| 마켓플레이스 `repo`/`ref`를 바꿈 | 기존 마켓플레이스를 `remove`한 뒤 `add`로 교체 | `claude-plugin.ts:203-245` | `코드 확인` |
| 플러그인 `version` 선언을 바꿈 | **아무것도 적용되지 않음**(설치 인자에 없음). `doctor`가 불일치로 표시 | `claude-plugin.ts:248-252,276-292` | `코드 확인` |
| 선언에서 항목을 **지움** | **아무것도 제거되지 않음.** `src/pkg`에 uninstall 호출이 없고, 락은 선언된 것만 다시 기록하므로 락에서만 사라진다 | 검색 결과, `claude-plugin.ts:136-158`, `npm.ts:91-101` | `코드 확인`(검색) |
| `teamai uninstall` | `packages` 관련 코드 참조가 없다(`uninstall.ts` 검색) | | `코드 확인`(검색 수준, 파일 전체를 읽지는 않음) |

- **사용자가 직접 설치한 플러그인과 teamai가 설치한 것을 구분하는 표식은 없다.** 소유권 = "teamai.yaml에 선언돼 있는가"뿐이다. 락도 선언된 이름만 걸러 기록한다 (`claude-plugin.ts:130-135`). 제거를 하지 않으니 보호할 필요가 없는 설계로 읽힌다 (`추론`).
- 주의할 부작용: 선언한 마켓플레이스와 **같은 이름**으로 사용자가 이미 다른 소스를 등록해 두었다면, teamai는 그것을 `remove`하고 선언한 소스로 다시 등록한다 (`claude-plugin.ts:206-228`, 같은 `--scope`). `코드 확인`.

#### A5. 실패·부분 실패·오프라인·명령 부재

| 상황 | 동작 | 근거 | 수준 |
|---|---|---|---|
| 명령 하나가 비정상 종료 | 즉시 예외. `pkgInstall`에 `try/catch`가 없어 **락이 저장되지 않는다** (`target`을 준 경우 선언 파일 수정도 저장 안 됨) | npm `npm.ts:229-231`, 마켓플레이스 `claude-plugin.ts:239-244`, 플러그인 `258-263`, 저장 `commands.ts:272-277` | `코드 확인` |
| 부분 실패 | npm이 먼저 실행되므로(`commands.ts:244-266`) Claude 쪽이 실패해도 npm 설치는 남는다. 락이 없으므로 다음 세션에서 같은 안내가 계속 나온다 | | `코드 확인`(저장 순서) + `추론`(안내 지속) |
| `claude` CLI 없음 | 설치: `Claude plugin CLI is unavailable...` 예외 (`--dry-run`에서는 이 검사 없이 명령만 출력). `doctor`: `✖ Claude Code not found` | `claude-plugin.ts:170-193`, `commands.ts:319-327` | `코드 확인` |
| 조회 명령 실패 | `plugin list`/`marketplace list`가 실패하거나 JSON이 아니면 **빈 목록**으로 취급. "CLI 실패"와 "설치 안 됨"을 구분하지 못하고, 성공한 설치 뒤 스냅샷이 비면 락에 빈 플러그인 목록이 기록될 수 있다 | `claude-plugin.ts:93-119` | `코드 확인` |
| 제한 시간 | npm 10분, Claude 설치 명령 120초 | `npm.ts:226`, `claude-plugin.ts:235-237,255` | `코드 확인` |
| 오프라인 | 오프라인 전용 처리는 없다. 실패는 위 "명령 비정상 종료"로 흐른다. Claude CLI·npm이 오프라인에서 어떻게 반응하는지는 외부 동작 | | 처리 부재 `코드 확인`, 외부 동작 `미확인` |

#### A 보충: 이름이 비슷하지만 이 질문과 상관없는 두 가지

- `src/plugin-lifecycle.ts`: **Claude 플러그인이 아니다.** HTTP 소스(관리 백엔드)의 `get-config` 응답이 주는 "슬러그별 셸 명령(install/run/uninstall, 선택 version)"을 조정(reconcile)하는 엔진이다 (`plugin-lifecycle.ts:9-20,254-278`). 숨김 명령 `teamai source reconcile-plugins`가 부르고(`index.ts:656-662`), 실제로는 세션 시작 때 12시간 간격으로 분리된 워커를 띄운다 (`local-agent.ts:1183,1208-1223,1226-1276`). 여기에는 변경 감지가 있다: `version` 문자열 비교와, install·update·run 명령 텍스트의 sha256 지문(`cmdFingerprint`) 비교로 갱신하고, 목록에서 빠진 것은 `uninstall_cmd`로 제거하며, 실패 후 10분 쿨다운이 있다 (`plugin-lifecycle.ts:76,92-96,133-152,196-210`). 단 서버가 명령 문자열을 내려주는 구조라서 내 용도(남의 마켓플레이스 플러그인)와는 다른 문제를 푼다. 상태 파일의 정확한 위치는 읽지 않았다 (`미확인`).
- `src/resources/marketplace.ts`: 팀 저장소의 `.codebuddy-plugin/marketplace.json`을 `skills/` 폴더에 맞춰 다시 생성한다 (`marketplace.ts:17,67-157`, 호출 `push.ts:728-735`). 플러그인을 **내보내는** 쪽(CodeBuddy)이고 가져오는 기능이 아니다 (`코드 확인`).

### B. `mcp`

#### B1. `mcp/mcp.yaml` 형식과 도구별 주입 형식 (`코드 확인`)

```yaml
# mcp/mcp.yaml  (프로젝트별: mcp/<ns>/mcp.yaml)
servers:
  - name: local-formatter         # 필수. 영숫자, -, _
    transport: stdio              # 필수. stdio | http | sse
    command: npx                  # stdio면 필수
    args: ["-y", "@acme/formatter-mcp"]
    env: { FORMATTER_MODE: strict }
    requires: [npx]               # PATH에 있어야 할 실행 파일
    tools: [claude, cursor]       # 생략하면 MCP 지원 도구 전체
  - name: gpu-analysis
    transport: http               # http/sse면 url 필수
    url: https://example.com/api/mcp
    headers: { Authorization: "Bearer ${GPU_ANALYSIS_TOKEN}" }
    timeout: 600000
```

- 필드 정의: `src/resources/mcp.ts:19-48` (그 밖에 `description`, 폐기된 `roles`, 제거된 `projects`). 예시는 `docs/guide/sharing.md:206-224`.
- **버전·패키지 필드가 없다.** 서버 버전을 고정하려면 `args`에 `@acme/formatter-mcp@1.4.0`처럼 직접 적어야 한다. 해시가 이 문자열에만 반응함을 4절 실행 C에서 확인했다 (`실행 확인`).

도구별 형식 차이의 요지 (한 `McpServerDef`를 도구마다 다른 모양으로 렌더, `mcp-format.ts:1-17,289-303`):

| 도구 | 파일 | 모양의 특징 | 근거 |
|---|---|---|---|
| Claude | 사용자 `~/.claude.json`의 `mcpServers`, 프로젝트 `.mcp.json`. 프로젝트 사용 중에는 `.claude.json`의 `projects[<키>].mcpServers`(로컬 범위)를 쓰는 경우도 있다 | `{ type, command, args, env }` 또는 `{ type, url, headers }` | `types.ts:401`, `mcp-format.ts:191-202`, `mcp-reconcile.ts:314-325,713-722` |
| Codex | `~/.codex/config.toml`, 프로젝트도 `.codex/config.toml` | JSON이 아니라 TOML 표 `[mcp_servers.<이름>]`(`command`, `args`, `startup_timeout_sec`, 하위 `.env` 표). **SSE는 지원 안 함**. 파일 전체를 다시 쓰지 않고 해당 블록만 텍스트로 교체해 주석을 보존 | `types.ts:408-415`, `mcp-format.ts:60,312-346`, `mcp-reconcile.ts:816-832` |
| Cursor | `.cursor/mcp.json` | `type` 생략(stdio), 변수 문법 `${env:NAME}` | `types.ts:440`, `mcp-format.ts:205-227` |
| OpenCode | `mcp` 키 | `type: local/remote`, `command`가 배열, `environment`, `enabled: true` | `mcp-format.ts:39,271-287` |
| Copilot | `mcp-config.json`, 프로젝트 `.github/mcp.json` | `type: local/http`, `tools: ["*"]` | `types.ts:10-11,451-452`, `mcp-format.ts:248-263` |
| CodeBuddy 계열 | 각자 파일 | `transportType` 대신 `type`, `timeout` | `mcp-format.ts:229-245` |

도구마다 경로가 정의돼 있어야 쓰며, 경로를 모르는 도구는 건너뛴다(`types.ts:396-398`, 주석). 설치되지 않은 도구는 `Skipping MCP sync ... tool not installed`로 건너뛴다 (`mcp-reconcile.ts:597-600`).

#### B2. 주입·제거 흐름과 "관리 항목" 표시 (`코드 확인`)

`teamai pull`(또는 `teamai mcp inject`) → `reconcileMcpForConfig()` → `reconcileTargets()` (`pull.ts:3863-3867`, `mcp-cmd.ts:133-151`, `mcp-reconcile.ts:2012-2057,2368`)

| 단계 | 입력 → 내부 동작 → 결과 | 근거 |
|---|---|---|
| 1 | `mcp/mcp.yaml`과 활성 네임스페이스 파일을 읽어 서버 정의 목록(`teamDefs`)을 만든다. 파싱 실패·이름 중복이면 **아무것도 바꾸지 않고** 중단(빈 집합으로 맞추면 설치된 것이 전부 지워지기 때문) | `mcp-reconcile.ts:2394-2404` |
| 2 | `autoApply`가 꺼져 있으면 "Run `teamai mcp inject` to apply" 안내만 하고 끝 | `mcp-reconcile.ts:2406-2409`, 기본값 `types.ts:152-155,213-221` |
| 3 | 도구별 대상 파일 결정(설치 감지, 사용자 제외 설정) | `mcp-reconcile.ts:555-620,2410-2414` |
| 4 | 도구마다 "원하는 항목 집합"을 만든다. 거르는 순서: `tools:` 대상 → 사용자 제외 → 도구가 지원하는 transport → 정책(`allowedCommands`/`allowedHosts`) → `requires` PATH → `${VAR}` 치환. 걸리면 `skipped`와 이유 | `mcp-reconcile.ts:920-977` |
| 5 | 관리 매니페스트를 읽고, 도구 파일의 서버 맵만 수정해서 쓴다(다른 키는 그대로 유지). 읽을 수 없는 파일은 건드리지 않고 건너뜀 | `mcp-reconcile.ts:2416,2770-2891` |
| 6 | 매니페스트 저장: `{이름, 엔트리 해시, ...}` | `mcp-reconcile.ts:2633-2643` |

**관리 항목 표시**: 항목 안에 표식을 넣지 않는다(MCP 항목에는 안전하게 넣을 자유 텍스트 칸이 없다는 설명, `types.ts:1344-1353`, `mcp-reconcile.ts:100-103`). 대신 **밖의 매니페스트**가 이름을 기록한다.

- 사용자 범위: `<데이터 홈>/managed-mcp.json`, 프로젝트 범위: 워크트리마다 `<데이터 홈>/workspaces/<id>/managed-mcp.json` (`types.ts:1455-1470`).
- 레코드: `{ name, hash, resolved?, file?, ... }`, `hash`는 엔트리 해시(렌더한 항목의 sha1 앞 16자리) (`types.ts:1380-1408`, `mcp-format.ts:348-351`).
- 프로젝트 범위에는 별도로 "해석된 값을 쓴 파일" 목록 `managed-mcp-files.json`이 있다 (`mcp-resolved-files.ts:61-65`).

**사용자가 직접 넣은 항목의 보호**

| 상황 | 동작 | 근거 |
|---|---|---|
| 같은 이름의 항목이 이미 있고 매니페스트에 기록이 없음 | 소유자를 판정한다. (a) 같은 파일을 읽는 다른 도구의 기록이 주장하면 그 도구 것, (b) 지금 teamai가 렌더한 결과 또는 **팀 저장소 git 이력에 있던 과거 어느 버전의 렌더**와 같으면 teamai 것(입양), (c) 아니면 사용자 것. 사용자 것이면 **건드리지 않고** `skipped: a server with this name already exists and is not managed by teamai` | `mcp-reconcile.ts:132,1051-1081,2803-2810` |
| 위 충돌을 덮어쓰고 싶음 | `teamai mcp inject --force` | `index.ts:917-926`, `mcp-reconcile.ts:2803` |
| 팀이 mcp.yaml에서 서버를 지움 | 기록이 있는 항목은 파일에서 삭제. 기록이 없어도 과거 팀 버전과 똑같은 항목이면 삭제 | `mcp-reconcile.ts:2845-2848,2857-2865` |
| `teamai mcp remove`/uninstall(전체 제거) | 기록된 항목만 지우되, **teamai가 쓴 뒤 사용자가 바꾼 항목은 경고하고 남긴다**(파일의 현재 해시 ≠ 기록 해시) | `mcp-cmd.ts:154-167`, `mcp-reconcile.ts:2831-2838` |
| Codex TOML | 같은 규칙. 블록 단위로 교체·삭제 | `mcp-reconcile.ts:3520-3610` |

#### B3. 변경 감지 (`코드 확인`, 결론은 표시)

| 질문 | 답 | 근거 |
|---|---|---|
| 선언이 바뀌었는지 | pull마다 **원하는 항목을 다시 렌더**하고 그 해시를 기록된 해시와 비교. 다르면 파일에 쓰고 `updated`, 같으면 건드리지 않음. 변수가 해석된 값(토큰)도 해시에 들어가므로 **토큰을 바꿔도 `updated`** | `mcp-reconcile.ts:2800-2829`, 실행 B |
| 보여 주는 것 | `added/updated/removed <도구>/<서버>` 줄과 `skipped ... — 이유`. 필드 단위 diff 없음. `mcp inject --dry-run`으로 쓰기 없이 미리 볼 수 있음 | `mcp-cmd.ts:123-151`, `mcp-reconcile.ts:2867` |
| 사용자가 **손으로 고친 관리 항목** | 비교 대상이 파일의 현재 내용이 아니라 **기록된 해시**다(`ownedHash.get(name) === hash`, `2821`). 그래서 선언이 안 바뀌었으면 손으로 고친 내용이 **그대로 남고 pull은 아무 말도 하지 않는다**. 선언이 바뀌면 덮어쓴다. `--force`도 이 경우를 되돌리지 않는다(`--force`는 기록 없는 항목에만 관여, `2803`) | 비교식 `코드 확인`, 동작 결론 `추론`(실행 안 함) |
| `doctor` | 설치된 항목을 렌더 결과와 깊은 비교(`isDeepStrictEqual`)해 `not the team's definition`으로 표시. 고치는 안내는 "run `teamai pull`"인데, 위 이유로 pull이 편집된 관리 항목을 되돌리지 않을 수 있다 | `doctor-delivery.ts:1540-1556,1590-1594` 비교·안내문 `코드 확인`, 안내가 실제로 효과 없는지는 `추론` |
| 필요한 변수가 비어 있음 | 서버를 `skipped: unresolved variable(s)`. 값이 비는 변수가 모두 "선언된 시크릿"이면 기존 항목을 유지(`kept`). 아니면 원하는 집합에서 빠지므로 **이미 쓴 항목이 제거**된다 | `mcp-reconcile.ts:958-969,2507,2831-2855` (합성은 `추론`) |
| **업스트림(MCP 서버 패키지) 변경** | **감지하지 않는다.** 버전 필드가 없고, 레지스트리·네트워크 호출이 `mcp-*` 파일들에 없다(검색 결과 0건). `requires`는 실행 파일이 PATH에 있는지만 본다. `npx -y 패키지`처럼 버전 없이 적으면 어떤 버전이 실행되는지는 npx 동작이라 teamai 밖이다 | `mcp-reconcile.ts:273-287`, `mcp.ts:19-36` / npx 동작 `미확인` |
| 팀 저장소 쪽 변화 | pull이 팀 저장소를 갱신한 뒤 매번 위 비교를 한다(`pullItem`은 no-op, 주입은 별도 단계). 변경 이력은 git으로 볼 수 있다 | `resources/mcp.ts:160-163`, 이력 열람은 `추론` |

- 알림 비대칭: **`packages`는 남의 코드라서 자동 설치하지 않지만 `mcp`는 기본으로 자동 반영**한다. `autoApply: false`와 `allowedCommands`로 막을 수 있다 (`types.ts:152-160`, `mcp-reconcile.ts:260-270`). 설계 의도는 `추론`.

#### B4. 시크릿·환경변수 치환과 git 보호 (`코드 확인`)

```text
mcp.yaml:  Authorization: "Bearer ${GH_TOKEN}"
   │  변수 표 = 팀 env 변수 + 멤버 값 + (선언된 시크릿은 멤버의 시크릿 저장소) + 프로세스 환경
   ▼
렌더 때 평문으로 치환 → { "headers": { "Authorization": "Bearer ghp_..." } } 을 도구 설정 파일에 기록
   ▼
git: 프로젝트 안의 파일이면 .git/info/exclude에 먼저 등록. 못 하면 쓰지 않고 경고
```

| 항목 | 동작 | 근거 |
|---|---|---|
| 치환 대상 | `url`, `command`, `args`, `headers`, `env` 안의 `${VAR}` | `mcp-format.ts:125-140,159-185` |
| 변수 출처 | 팀 `env/env.yaml` 변수, 멤버가 설정한 값, 선언된 시크릿(`env/secrets.yaml`)은 멤버의 시크릿 저장소, 그 밖의 키는 프로세스 환경 | `mcp-reconcile.ts:180-240`, `docs/guide/sharing.md:226` |
| 항상 평문 | `supportsEnvExpansion`은 항상 `false`. 주석: GUI로 띄운 IDE는 셸 환경변수를 상속하지 않아 `${VAR}`를 그대로 두면 인증이 실패하므로 평문으로 쓴다 | `mcp-format.ts:71-89` |
| 파일 권한 | 해석된 값이 든 설정은 새로 만들면 0600, 기존 파일은 조인다 | `mcp-reconcile.ts:2869,2877,2884,3612-3620`, `mcp-format.ts:78-81` |
| git 보호 (프로젝트 범위) | 해석된 값이 들어갈 파일은 쓰기 **전에** `.git/info/exclude`에 등록(팀의 `.gitignore`는 건드리지 않음). git이 이미 추적 중이면 실패로 보고 **쓰지 않고** 경고, 파일은 그대로 둔다 | `mcp-git-exclude.ts:17-24,114-128`, `mcp-reconcile.ts:2509-2530` |
| 사용자 범위 | `~/.claude.json` 같은 홈 파일은 저장소 밖이라 제외 처리 불필요 | `mcp-git-exclude.ts:36-46` |
| 매니페스트에 값이 남나 | 해시(16자리)만 기록하고 값 자체는 쓰지 않는다 | `types.ts:1380-1383` |
| 팀 저장소에는 | `${VAR}` 참조만 있고 값은 없다 | `docs/guide/sharing.md:226` |

- Codex의 HTTP 헤더에는 `${VAR}`를 환경변수 참조(`bearer_token_env_var` 등)로 옮기는 코드가 있다(`mcp-format.ts:91-121`). 그러나 치환이 항상 먼저 일어나므로 이 경로는 실제 주입에서는 쓰이지 않는 것으로 보인다 (`추론`).

---

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| packages 진입점 | `src/pkg/register-command.ts:26-57` | `registerPackagesCommand()` | `packages [target]`과 `packages install [target]` 등록 |
| packages 핵심 | `src/pkg/commands.ts:184-278` | `pkgInstall()` | 선언 로드 → 어댑터 설치 → 락 저장 |
| 선언 스키마 | `src/pkg/types.ts:6-84` | `NpmSpecSchema`, `ClaudePluginSpecSchema`, `PackageManifestSchema` | 필드·검증 |
| 락 | `src/pkg/manifest.ts:24-80,124-186` | `packageLockDir`, `loadPackageLock`, `packageDeclarationHash` | 데이터 홈의 `teamai.lock`, 선언 해시 |
| npm 어댑터 | `src/pkg/adapters/npm.ts:106-263` | `NpmAdapter` | `npm install`/`pnpm add`, 스냅샷, 상태 |
| Claude 어댑터 | `src/pkg/adapters/claude-plugin.ts:77-361` | `ClaudePluginAdapter` | `claude plugin ...` 실행, 스냅샷, 상태 |
| 환경 감지 | `src/pkg/env-detect.ts:14-27` | `detectPackageEnvironment()` | `doctor` 전용 |
| 선언 변경 알림 | `src/pkg/pkg-hint.ts:21-191` | `computePackageHintState` 외 | 해시 비교 후 세션 안내 |
| 실행기 | `src/utils/exec.ts:25-99` | `execCommand`, `probeBinary` | `shell: false` 인자 배열 실행 |
| (무관) 백엔드 플러그인 | `src/plugin-lifecycle.ts:122-211`, `src/local-agent.ts:1226-1276` | `reconcilePlugins`, `runPluginReconcileWorker` | 셸 명령 기반 조정, 지문 비교 |
| (무관) 마켓플레이스 생성 | `src/resources/marketplace.ts:67-157` | `refreshMarketplace()` | CodeBuddy 마켓플레이스 JSON 재생성 |
| mcp 진입점 | `src/index.ts:904-935`, `src/mcp-cmd.ts:34-168` | `mcpList/mcpInject/mcpRemove` | 목록·주입·제거 |
| mcp 스키마 | `src/resources/mcp.ts:19-117` | `McpYamlSchema`, `teamMcpToDef` | 서버 정의 |
| 도구별 렌더 | `src/resources/mcp-format.ts:189-351` | `renderJsonEntry`, `renderCodexBlock`, `entryHash` | 형식 차이, 해시 |
| 조정 엔진 | `src/mcp-reconcile.ts:920-977,2012-2057,2368-2651` | `desiredMcpForTarget`, `reconcileTargets` | 원하는 집합, 적용, 기록 |
| 소유 판정 | `src/mcp-reconcile.ts:1051-1081,2770-2891` | `judgeUnrecordedMcpEntry`, `applyJson` | 사용자 항목 보호 |
| 매니페스트 | `src/types.ts:1380-1411,1466-1470`, `src/utils/mcp-manifest.ts:44-130` | `ManagedMcpRecord`, `managedMcpManifestPath` | 소유 기록 |
| 시크릿·git | `src/mcp-git-exclude.ts:36-128`, `src/mcp-resolved-files.ts:61-110`, `src/mcp-reconcile.ts:2509-2530` | `carriesResolvedValue`, `ensureExcludedFromGit` | 평문 파일 git 제외 |
| 자동 적용 | `src/pull.ts:3855-3891`, `src/types.ts:152-160,213-221` | pull의 MCP 단계, `getMcpSharing` | `autoApply` 기본 true |
| 편집 감지(doctor) | `src/doctor-delivery.ts:1534-1600` | `buildMcpDeliveryChecks` | 선언 대비 설치 비교 |

---

## 4. 검증 과정 및 실행 결과

- **수행한 명령** (순수 함수만. 네트워크, `claude` CLI, `npm`, 빌드, 앱 실행은 하지 않음):
  ```bash
  /Users/kkh/Desktop/oss-analysis/artifacts/teamai-cli/packages-mcp-demos/run.sh
  ```
- **복사한 소스**: `src/pkg/manifest.ts:138-159`(정렬 후 sha256), `src/resources/mcp-format.ts:125-146,155-202,348-351`(`${VAR}` 치환, Claude 렌더, `entryHash`). `git show a44493f:<경로> | sed -n`으로 줄을 뽑아 이어 붙인다. **대체한 부분**: import 문은 `type` 선언으로 바꿨고, `placeholderValue`(`148-153`)는 Windows 대소문자 보조 탐색(`sameEnvName`)을 빼고 `Object.hasOwn` 조회만 남겼다.
- **스크립트와 출력**: `artifacts/teamai-cli/packages-mcp-demos/`의 `run.sh`, `demo.ts`, `copied.ts`, `output.txt`
- **실행 결과** (`output.txt`, 토큰은 가짜 값):
  ```text
  == A. packages: declarationHash는 선언 텍스트의 해시일 뿐 ==
  base == reordered : true        # 키 순서를 바꿔도 같은 해시
  base == pinned    : false       # 플러그인 version을 추가하면 해시가 바뀜
  version 1.2.0 -> 1.3.0          # 해시 bc1103c2905e -> 4345a91e8342

  == B. mcp: ${VAR}를 평문으로 풀고 entryHash를 만든다 ==
  rendered entry : {"type":"http","url":"https://example.com/mcp","headers":{"Authorization":"Bearer ghp_SECRET1234567890"}}
  entryHash      : e608e5f90680aa95
  토큰 교체 후 entryHash : 84971f7471596dfc     # 값이 바뀌어도 해시가 바뀜
  변수 없으면 missing: ["GH_TOKEN"]

  == C. mcp: stdio 서버의 버전은 args 문자열일 뿐 ==
  고정 없음 hash : f834065dd45a9f5f
  @1.4.0 hash   : 1a1c744c997704d0
  ```
- **판단 근거**
  - A: 해시 입력에 "업스트림 최신 버전"이 들어갈 자리가 없다. 선언을 고쳐야만 바뀐다. 따라서 선언 해시는 업스트림 변경을 감지할 수 없다 (`실행 확인` + 코드의 입력 구조).
  - B: 엔트리 해시는 평문으로 치환한 값까지 포함한다. 시크릿 로테이션도 `updated`가 되는 이유다.
  - C: 서버 버전은 사용자가 `args`에 쓴 문자열일 뿐이고, 해시는 그 문자열에만 반응한다.
- **실행하지 않은 것**: `reconcileTargets` 전체 흐름(손으로 고친 관리 항목이 pull에서 유지되는지), 실제 `claude plugin install`의 갱신 동작, 오프라인 반응, 테스트 스위트. 모두 `미확인` 또는 `추론`으로 표시했다.

---

## 5. 종합: 내 용도에 쓸 만한가 (`추론` 포함)

용도: 개인 저장소에 "남이 만든 플러그인·MCP"를 선언해 두고 내 기기들에 설치·동기화.

| 필요 | `packages` | `mcp` | 평가 |
|---|---|---|---|
| 선언해 두면 새 기기에 설치 | `teamai init <개인 저장소>` 뒤 `teamai packages`. Claude 마켓플레이스 등록·플러그인 설치를 `claude` CLI로 위임 | `teamai pull`로 자동 | 된다. 단 `packages`는 수동 단계가 남는다 |
| 원하는 버전 고정 | npm은 가능. 마켓플레이스는 `ref`(적용 여부 `미확인`). **플러그인 `version`은 고정 아님** | `args`에 직접 `@버전` | 플러그인 고정은 마켓플레이스 `ref`에 기대야 한다 (`추론`) |
| 원본이 바뀌었는지 | 없음 | 없음 | **부족** |
| 무엇이 바뀌었는지 | 없음(개수만) | 없음(`updated` 한 줄) | **부족** |
| 선언에서 지우면 제거 | 안 지운다 | 지운다(기록된 것만) | `packages`는 정리가 수동 |
| 사용자가 설치한 것 보호 | 표식 없음. 같은 이름 마켓플레이스는 교체됨 | 기록 매니페스트와 소유 판정으로 보호 | `mcp`가 훨씬 정교 |

부족한 점 (내 용도 기준):

1. **업스트림 변경 감지 없음**: 새 버전 조회(`npm view`, `claude plugin update`/마켓플레이스 갱신 확인, 원격 커밋 비교)가 어느 쪽에도 없다. teamai는 "선언한 것이 설치돼 있는가"만 다룬다.
2. **diff 없음**: 해시 불일치는 참/거짓일 뿐이다. 락(`teamai.lock`)은 마지막 결과만 덮어쓰고 git 밖에 있어 이력이 없다.
3. **`packages`의 플러그인 버전은 선언돼도 적용되지 않는다**(검사용). 고정하려면 마켓플레이스 `ref`를 쓰고, 그 효과는 Claude CLI에 달려 있다 (`미확인`).
4. **정리(제거) 부재**: `packages`는 선언에서 지워도 설치된 것이 남는다.
5. **MCP 시크릿은 평문으로 기기 파일에 쓰인다**. 프로젝트 파일은 git 제외로 막지만, 개인 기기 파일 자체의 노출은 파일 권한(0600)에 의존한다.

내 용도에 맞게 쓰는 방법 (`추론`): teamai의 감지 기능에 기대지 말고 **"고정하고, 올릴 때만 내 저장소에서 바꾼다"** 방식으로 쓰면 된다. npm `version`·마켓플레이스 `ref`·MCP `args`의 `@버전`을 정확히 적어 두면, 내 저장소의 git diff가 곧 "무엇이 바뀌었나"가 된다. 원본이 바뀌었는지 알려 주는 부분은 따로 만들어야 한다. 이때 `plugin-lifecycle.ts`의 방식(해결된 명령·버전의 sha256 지문을 저장해 두고 비교)과 MCP의 "소유 기록 + 렌더 해시" 방식이 설계 참고가 된다.

---

## 6. 남은 질문 및 추가 조사 사항

- [ ] `claude plugin install <이름> --scope --yes`를 이미 설치된 플러그인에 다시 실행하면 갱신되는지, `claude plugin marketplace add <repo>@<ref>`의 ref가 어떻게 적용되는지, `claude plugin list --json`의 실제 필드 (`미확인`, `claude` CLI 실행 승인이 필요하다 — 9장)
- [ ] 마켓플레이스 `ref`로 고정해도 그 안의 플러그인이 가리키는 소스(다른 저장소·커밋)까지 고정되는지 (Claude 쪽 동작, `미확인`)
- [ ] 손으로 고친 관리 MCP 항목이 `teamai pull` 뒤에도 유지되는지 실제 실행으로 확인 (`reconcileTargets`는 임시 HOME에서 `mcp-reconcile` 단위 사례로 돌릴 수 있는지 확인 필요). 테스트 사례명 중 `mcp-reconcile.test.ts`의 "does not overwrite a user-owned server with a colliding name"만 확인했다
- [ ] user 범위 데이터 홈의 실제 경로(`~/.teamai`)와 `packageLockDir`이 돌려주는 위치 (`types.ts:2933-2934` 주석 근거, 계산 로직 미확인)
- [ ] `teamai packages install <대상>`만 실행한 뒤(`target` 있음) `declarationHash`가 갱신되지 않아 안내가 남는지 (`commands.ts:229-242`로 보면 그렇게 읽히나 실행 안 함, `추론`)
- [ ] `local-agent`의 플러그인 상태 파일 위치와 `readPluginState` 형식 (`미확인`)
- [ ] 기능 스펙 후보: (1) `packages` 선언→어댑터 설치→락 스냅샷→해시 알림, (2) `mcp` 소유 매니페스트 기반 reconcile (엔트리 해시, 소유 판정, 평문 시크릿 git 제외)
