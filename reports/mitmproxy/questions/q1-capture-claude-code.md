# Q1. Claude Code의 API 요청을 mitmproxy로 실제로 캡처할 수 있는가?

- **상위 개요**: [overview.md](../overview.md) / [docs-guide.md](../docs-guide.md)
- **실험 일자**: 2026-10-15, Windows 11, mitmproxy 12.2.3 (`uv tool install mitmproxy`), Claude Code 2.1.300
- **검증 수준**: `실행 확인` (이 PC에서 직접 실행)

## 결론

**가능하다.** Claude Code 프로세스 하나에만 환경변수 두 개를 주면, 시스템 CA 등록 없이 HTTPS 요청 본문까지 복호화해서 볼 수 있다. 그리고 **system prompt는 `/v1/messages` 요청 본문의 `system` 필드에 그대로 들어 있다.** 즉 JSONL 로그에 없는 것은 "저장하지 않아서"이지 네트워크에서도 숨겨진 것이 아니다.

## 재현 절차

1. 설치: `uv tool install mitmproxy` (사용자 영역 설치, `~/.local/bin`에 `mitmdump`, `mitmproxy`, `mitmweb`)
2. 프록시 실행 (**로컬 전용으로 바인딩**): `mitmdump --listen-host 127.0.0.1 --listen-port 18080 -w <저장파일>`
   - 처음 실행 때 `~/.mitmproxy/`에 CA 파일 생성됨
   - `--listen-host`를 주지 않으면 `0.0.0.0`에 열려 같은 네트워크의 다른 기기가 접속할 수 있음(이번에 첫 실행에서 확인하고 다시 띄움)
3. Claude Code에 프록시와 CA를 **해당 프로세스에만** 적용:
   ```bash
   HTTPS_PROXY=http://127.0.0.1:18080 \
   NODE_EXTRA_CA_CERTS="$HOME/.mitmproxy/mitmproxy-ca-cert.pem" \
   claude -p "Reply with exactly one word: pong"
   ```
4. 결과: 응답 `pong` 정상 수신, 프록시에 요청 기록됨.
5. 분석: `mitmdump -nq -r <저장파일> -s <요약 스크립트>`로 요청 구조 확인 (스크립트는 헤더를 출력하지 않음)

Windows 시스템 인증서 저장소에는 아무것도 등록하지 않았다(`NODE_EXTRA_CA_CERTS`만 사용).

## 실제로 진행한 순서 (CLI → GUI)

"CLI에서 설정한 것이 GUI로 이어지는" 구조가 아니다. **프록시 본체는 하나이고 화면(프런트엔드)만 다르다.** `mitmdump`(CLI), `mitmproxy`(터미널 UI), `mitmweb`(브라우저 UI)는 같은 코어이며 같은 옵션과 같은 CA(`~/.mitmproxy`)를 쓴다. 같은 포트를 쓰므로 **동시에 하나만** 띄울 수 있다.

| 단계 | 한 일 | 명령 |
|---|---|---|
| 1 | 설치 (세 도구가 한 번에 설치됨) | `uv tool install mitmproxy` |
| 2 | CLI(`mitmdump`)로 프록시 기동. 로그가 터미널에 바로 보여 동작 확인이 가장 빠름. 이때 CA 자동 생성 | `mitmdump --listen-host 127.0.0.1 --listen-port 18080 -w claude.flows` |
| 3 | 프록시·복호화 확인 (curl) | `curl --ssl-no-revoke -x http://127.0.0.1:18080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com/` |
| 4 | Claude Code를 프록시 경유로 실행 (프로세스 한정 환경변수) | `HTTPS_PROXY=... NODE_EXTRA_CA_CERTS=... claude -p "..."` |
| 5 | 저장된 flow를 스크립트로 분석 | `mitmdump -nq -r claude.flows -s summarize.py` |
| 6 | `mitmdump` 종료 후 같은 포트로 GUI 기동. 저장한 캡처를 불러와 화면에 바로 표시 | `mitmweb --listen-host 127.0.0.1 --listen-port 18080 --web-host 127.0.0.1 --web-port 18081 -r claude.flows` |

- GUI만 쓰고 싶다면 2~3단계 없이 6단계의 `mitmweb`부터 시작하면 된다(`-r`은 선택). `mitmweb`은 기본으로 브라우저를 열고, 접속 URL에 **일회용 토큰**이 붙는다(로그가 버퍼링되면 `PYTHONUNBUFFERED=1`로 URL을 볼 수 있음).
- 이후 새 요청은 별도 터미널에서 4단계 환경변수를 붙여 `claude`를 실행하면 화면에 실시간으로 추가된다.

### 용어: `-w`와 `-r`
- `-w <파일>`: 지나간 모든 flow를 **파일로 저장**(write). 캡처 자체에는 필수가 아니고 나중에 분석·재생하기 위한 것. 파일에는 토큰과 대화 내용이 평문으로 들어간다.
- `-r <파일>`: 저장한 flow를 **읽어 들임**(read). `mitmdump -n`(프록시 포트를 열지 않음)과 함께 쓰면 분석 전용, `mitmweb -r`이면 GUI에 불러오기.

### Claude Code 쪽 프록시 설정 (공식 문서 확인: `code.claude.com/docs/en/network-config`)
- **별도의 프록시 전용 설정 항목은 없다.** 프록시 설정이 곧 **표준 환경변수**다: `HTTPS_PROXY`(권장), `HTTP_PROXY`, `NO_PROXY`. 소문자 변형도 되며 `https_proxy` → `HTTPS_PROXY` → `http_proxy` → `HTTP_PROXY` 순으로 처음 설정된 것을 사용.
- 같은 변수를 `~/.claude/settings.json`의 `env` 블록에 넣어도 된다(문서: 이 페이지의 모든 환경변수는 settings.json으로도 설정 가능). 지속 적용이 필요할 때 쓰며, 이번에는 쓰지 않았다.
- **환경변수는 시작 시 한 번만 읽는다.** 실행 중인 세션은 나중에 바꾼 셸 환경을 반영하지 않는다.
- **SOCKS 프록시는 지원하지 않는다**(문서 명시). 프록시 URL이 파싱 불가(예: `http://` 누락)이면 시작 시 오류로 멈춘다.
- **CA 신뢰**: 기본값은 번들된 Mozilla CA + **OS 인증서 저장소**(`CLAUDE_CODE_CERT_STORE=bundled,system`). 그래서 OS 저장소에 mitmproxy CA를 등록하면 `NODE_EXTRA_CA_CERTS` 없이도 동작할 수 있다(문서: 네이티브 설치는 OS 저장소 읽기 가능, npm 설치는 Node 22.15+ 필요). 이번에는 OS 등록을 피하고 `NODE_EXTRA_CA_CERTS`로 **추가 CA만** 신뢰시켰다.
- **확인 방법**: `/status`(Proxy 행, Additional CA cert 행), `claude --debug`(로그에 `CA certs: Appended extra certificates from NODE_EXTRA_CA_CERTS`). 이번 실험은 이 확인 없이 실제 요청이 프록시에 잡히는 것으로 검증함.
- **백그라운드 에이전트 주의**: `claude agents`, `--bg`는 공용 supervisor 프로세스가 호스팅하므로 셸 변수가 적용되지 않을 수 있다. 이 경우 settings.json의 `env`에 넣어야 한다.
- 문서의 네트워크 요구 목록에 이번 캡처에서 본 도메인이 그대로 나온다(`api.anthropic.com`, `mcp-proxy.anthropic.com`, Datadog 텔레메트리 등). Datadog 두 호스트는 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`/`DISABLE_TELEMETRY`로 끌 수 있다고 문서가 안내.

## 관찰 결과

### Claude Code가 보내는 요청 (한 번의 `-p` 호출 동안, 도메인과 경로만)

| 분류 | 요청 | 비고 |
|---|---|---|
| **모델 호출** | `POST api.anthropic.com/v1/messages` | 요청 본문 약 84KB, 스트리밍(`stream: true`) |
| 설정·정책 | `GET /api/claude_code/settings`, `/policy_limits`, `/api/claude_cli/bootstrap`, `/api/claude_code_penguin_mode` | |
| 기능 플래그 | `POST /api/eval/sdk-...` | 응답 약 145KB |
| 계정 | `GET /api/oauth/organizations/<org>/skills/list-skills`, `plugins/list-plugins`, `marketplaces` | claude.ai 동기화 skills 목록 등 |
| MCP | `GET /mcp-registry/v0/servers`(여러 번), `GET /v1/mcp_servers`, `POST mcp-proxy.anthropic.com/v1/mcp/<서버>` | 등록된 claude.ai 커넥터와 통신 |
| 텔레메트리 | `POST /api/claude_code/metrics`, `/api/event_logging/v2/batch`(요청 최대 약 460KB), `POST http-intake.logs.us5.datadoghq.com/api/v2/logs` | 제3자 도메인(Datadog)으로도 전송 시도 흔적 |

→ 모델 호출 외에도 설정 조회, MCP, 텔레메트리 요청이 함께 나간다.

### `/v1/messages` 요청 구조

- 최상위 키: `model`, `messages`, `system`, `tools`, `metadata`, `max_tokens`, `thinking`, `context_management`, `output_config`, `thread`, `diagnostics`, `stream`
- `model`: `claude-sonnet-5-5`, `max_tokens`: 128000
- **`system`: 4개 블록 배열** (글자 수 192 / 62 / 2025 / 4850)
  - 블록0: 빌링 헤더 성격의 문자열(`x-anthropic-billing-header: cc_version=...`)
  - 블록1: "You are a Claude agent, built on Anthropic's Claude Agent SDK."
  - 블록2, 3: 행동 지침 본문
  - 즉 `-p` 모드의 system prompt는 한 덩어리가 아니라 **블록 여러 개**로 구성됨
- `tools`: 17개(`Agent`, `Bash`, `Edit`, `Glob`, `Grep`, `Read`, `Skill` 등). 내장 도구 정의가 요청마다 포함됨
- `messages`: 2개

### 요청 본문 상세 (mitmweb에서 내려받은 `messages` 파일, 84,484B 분석)

mitmweb의 Request 본문을 파일로 내려받아(`Downloads\messages`) 파싱했다. 같은 요청(`stream: true`)이며 **요청은 일반 JSON POST, 응답만 SSE**다.

| 영역 | 크기(글자) | 내용 |
|---|---|---|
| `system` (4블록) | 7,129 | 블록0 빌링 헤더 192 / 블록1 62 / 블록2 2,025 (`cache_control`: `ephemeral`, ttl 1h, **scope global**) / 블록3 4,850 (`ephemeral`, ttl 1h) |
| `tools` (17개) | 44,118 | 큰 순서로 PowerShell 9,016 / Workflow 5,434 / Agent 4,944 / ScheduleWakeup 4,698 / Bash 3,635 / Grep 3,347 … / `DeferredToolPlaceholder`, `advisor`(작음) |
| `messages` | 29,948 | **2개**. `[0]` role=user: system-reminder 블록 2개(계정·환경 컨텍스트, 커밋 attribution 지침) + 실제 프롬프트 33자. `[1]` role=**system**: 약 28.7KB의 환경·지침 텍스트 + 내용이 빈 `tool_addition` 블록 3개(마지막에 `cache_control` 1h) |
| 기타 키 | — | `thinking: {type: adaptive, display: omitted}`, `context_management`(`clear_thinking_20251015`), `output_config.effort: medium`, `metadata.user_id`, `thread`, `diagnostics` |

해석(`추론` 포함):
- **system prompt이 `system` 필드 하나에만 있지 않다.** 일부 지침이 `messages`에 role=system 메시지로도 들어간다(이번 `-p` 호출 기준). `/context`의 "System prompt 2.8k 토큰" 같은 항목은 이 중 일부만 해당할 수 있다(미확인).
- **프롬프트 캐싱 지점이 보인다**: `system` 블록2(전역 범위), 블록3, `messages[1]`의 마지막 블록에 `cache_control`(1시간 ttl)이 붙어 있다. 사용자·프로젝트별로 변하는 부분과 고정 부분을 나눠 캐시하는 구조로 보인다(추론).
- **요청마다 사용자 정보가 평문으로 포함된다**: 이메일, 작업 디렉터리, OS, git 상태, 로드된 skills·도구 목록, 메모리 파일 내용 등. 캡처 파일·내려받은 본문 공유 시 주의.
- **도구 정의가 `system`보다 6배 크다**(44k vs 7k 글자). 컨텍스트 비용의 상당 부분이 도구 스키마다.
- 응답은 SSE 스트림이라 요청 본문과 달리 `event:`/`data:` 줄로 나뉘어 도착한다(응답 본문 분석은 미수행).

### `/context` 출력과의 비교

대화형 세션의 `/context`는 system prompt 2.8k 토큰, system tools 25.4k 토큰으로 보고했다. 이번 캡처는 `-p` 모드의 짧은 호출이라 도구 17개, system 약 7천 글자로 **구성이 다르다**(대화형 세션은 훨씬 크다). 두 숫자를 직접 비교하려면 대화형 세션을 캡처해야 한다.

## 해석과 한계

- **정정(2026-10-15, 실행 확인)**: 처음에는 "JSONL에 system prompt가 없어서 claude-devtools가 못 보여준다"고 추정했으나 **틀렸다**. Claude Code 2.1.300의 세션 JSONL에는 요청 쪽 정보를 담은 레코드가 있다.
  - `api-request-shape`: `shape` 안에 `system`(블록 3개: 57/2,025/6,311자)과 `tools`(20~21개, JSON 약 9만 자)가 들어 있음(대화형 세션 `daa2f2cd-...jsonl`에서 확인, 2건)
  - `attachment`(`prompt_snapshot`): system prompt 문구가 포함된 약 7.5KB~78KB 레코드(대화형·`-p` 모두)
  - `api-request-blob`(해시로 참조되는 요청 메시지 본문), `api-request`(`shapeHash`, `requestDigest`, `cacheControl` 등 요약)
  - 그 외 `attachment`의 하위 타입으로 `environment`, `deferred_tools_delta`, `mcp_instructions_delta`, `skill_listing`, `session_context` 등 요청에 주입되는 컨텍스트가 별도 레코드로 저장됨
  - **claude-devtools 소스(`1486f20`)에는 `prompt_snapshot`, `api-request*` 처리가 없다**(`grep` 결과 0건). 따라서 앱이 system prompt를 못 보여주는 이유는 "로그에 없어서"가 아니라 **새 레코드 타입을 해석하지 않아서**일 가능성이 높다(앱은 이 레코드들이 생기기 전 형식을 기준으로 만들어졌다고 `추론`). 다만 `shape`가 요청 본문 전체와 같은지, 버전별로 언제부터 생겼는지는 미확인.
  - 이 `cache_control`은 JSONL에서 검색되지 않았다(요청 본문에는 있음). 즉 **JSONL이 요청 본문의 완전한 사본은 아니다**.
- 네트워크 캡처의 가치는 그대로다: 실제로 전송된 **원본 바이트**(헤더, `cache_control`, 순서, 응답 SSE 이벤트, 텔레메트리 등 JSONL에 없는 통신)를 본다.
- 한 번의 `-p` 호출만 확인했다. **대화형 모드**, 서브에이전트, 도구 사용 턴, 압축(compaction) 시의 요청은 미확인.
- Claude Code 버전(2.1.300)에 따라 요청 구조가 바뀔 수 있다.
- 응답 본문(SSE 스트림), `thinking` 설정, `context_management`의 의미는 이번에 분석하지 않았다.

## 보안·정리 사항

- 캡처 파일에는 **OAuth 토큰, 대화 내용, 조직 ID**가 평문으로 들어 있다. 레포 밖 scratchpad에 두었고 공유·커밋 금지.
- `~/.mitmproxy/mitmproxy-ca.pem`에 CA 개인키가 있다. 시스템에 신뢰 등록은 하지 않았으므로 이 CA를 신뢰하는 프로그램은 `NODE_EXTRA_CA_CERTS`를 준 프로세스뿐이다.
- 정리: `uv tool uninstall mitmproxy`, `~/.mitmproxy` 삭제, 캡처 파일 삭제.

## 다음에 확인할 것

- [ ] 대화형 `claude` 세션 캡처 후 `/context` 수치와 비교
- [ ] 도구 호출이 있는 여러 턴에서 `messages`와 `system`이 어떻게 변하는지(캐시 제어 필드 등)
- [ ] 응답 SSE 스트림이 mitmproxy에서 어떻게 보이는지(스트리밍 옵션 영향)
- [ ] `mitmweb`(GUI)로 같은 캡처 시도
