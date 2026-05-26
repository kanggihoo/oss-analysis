# hermes-agent 문서 중심 분석

분석 기준: 사용자가 요청한 대로 코드 구현을 깊게 읽기보다 루트 README, 공식 문서 사이트의 `website/docs`, 릴리스 노트, `CONTRIBUTING.md`, `pyproject.toml`, `package.json`을 중심으로 확인했다. 코드 파일은 엔트리포인트와 패키지 구성 확인 용도로만 참조했다.

주요 근거 문서:

- `hermes-agent/README.md`
- `hermes-agent/website/docs/index.md`
- `hermes-agent/website/docs/getting-started/quickstart.md`
- `hermes-agent/website/docs/getting-started/installation.md`
- `hermes-agent/website/docs/user-guide/cli.md`
- `hermes-agent/website/docs/user-guide/tui.md`
- `hermes-agent/website/docs/user-guide/configuration.md`
- `hermes-agent/website/docs/user-guide/messaging/index.md`
- `hermes-agent/website/docs/user-guide/features/overview.md`
- `hermes-agent/website/docs/user-guide/features/tools.md`
- `hermes-agent/website/docs/user-guide/features/skills.md`
- `hermes-agent/website/docs/user-guide/features/memory.md`
- `hermes-agent/website/docs/user-guide/features/cron.md`
- `hermes-agent/website/docs/user-guide/features/delegation.md`
- `hermes-agent/website/docs/user-guide/features/code-execution.md`
- `hermes-agent/website/docs/user-guide/features/mcp.md`
- `hermes-agent/website/docs/user-guide/features/plugins.md`
- `hermes-agent/website/docs/user-guide/features/api-server.md`
- `hermes-agent/website/docs/user-guide/features/acp.md`
- `hermes-agent/website/docs/user-guide/features/web-dashboard.md`
- `hermes-agent/website/docs/user-guide/security.md`
- `hermes-agent/website/docs/developer-guide/architecture.md`
- `hermes-agent/website/docs/reference/cli-commands.md`
- `hermes-agent/CONTRIBUTING.md`
- `hermes-agent/AGENTS.md`
- `hermes-agent/pyproject.toml`
- `hermes-agent/package.json`

## 1. 프로젝트의 목적

`hermes-agent`는 Nous Research가 만든 자가 개선형 AI 에이전트 런타임이다. 단순 채팅 래퍼나 IDE 전용 코파일럿이 아니라, 터미널/파일/웹/브라우저/메시징/스케줄러/스킬/메모리/플러그인을 묶어 장기 실행 가능한 개인 또는 팀용 에이전트로 쓰는 것을 목표로 한다.

문서에서 반복되는 핵심 표현은 "self-improving AI agent"와 "closed learning loop"다. 즉 에이전트가 대화와 작업 경험을 통해 메모리를 관리하고, 반복 가능한 절차를 스킬로 만들거나 개선하며, 과거 세션을 검색하고, 사용자의 환경과 선호를 축적하는 구조를 지향한다.

## 2. 프로젝트 유형과 사용 방식

유형은 대형 Python 중심 에이전트 애플리케이션이자 CLI/TUI, 메시징 게이트웨이, 웹 대시보드, API 서버, ACP 편집기 통합, 플러그인/스킬 생태계를 함께 가진 혼합형 프로젝트다.

사용자는 보통 다음 진입점 중 하나로 쓴다.

- 로컬 대화형 에이전트: `hermes` 또는 `hermes --tui`
- 일회성 명령: `hermes chat -q "..."` 또는 순수 출력용 `hermes -z "..."`
- 모델/프로바이더 설정: `hermes model`
- 전체 설정 마법사: `hermes setup`
- 메시징 봇: `hermes gateway setup`, `hermes gateway`
- 스케줄 작업: `hermes cron ...` 또는 채팅에서 자연어로 일정 등록
- 웹 관리 UI: `hermes dashboard`
- 편집기 에이전트: `hermes acp`
- OpenAI 호환 백엔드: 게이트웨이의 API server

## 3. 핵심 기능

문서 기준 핵심 기능은 다음과 같다.

- 대화형 CLI 및 현대적 TUI: 멀티라인 입력, slash command, 세션 resume, interrupt, streaming tool output, 모델/세션 picker.
- 다중 LLM provider: Nous Portal, OpenAI Codex, GitHub Copilot, Anthropic, OpenRouter, Gemini, Kimi, MiniMax, DeepSeek, Hugging Face, Bedrock, custom endpoint 등.
- 도구와 toolset: 웹 검색, 터미널, 파일 읽기/패치, 브라우저 자동화, vision, image/video generation, TTS, memory, session search, cron, delegation, MCP 등 70개 이상 도구를 toolset으로 묶어 플랫폼별 활성화.
- 터미널 백엔드: local, Docker, SSH, Singularity/Apptainer, Modal, Daytona, Vercel Sandbox.
- 지속 메모리: `~/.hermes/memories/MEMORY.md`, `USER.md`, SQLite 기반 세션 검색, 외부 메모리 provider.
- 스킬 시스템: `~/.hermes/skills/` 중심의 절차형 지식 문서. 스킬은 slash command가 되며 agentskills.io 표준과 호환.
- 메시징 게이트웨이: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, Mattermost, Home Assistant, Teams, Google Chat, LINE 등 다수 플랫폼.
- Cron 자동화: 자연어 또는 cron 표현식으로 에이전트 작업을 예약하고 결과를 플랫폼/파일로 전달.
- Subagent delegation: 독립 컨텍스트를 가진 하위 에이전트를 병렬로 실행.
- Code execution: Python 스크립트가 Hermes 도구를 RPC로 호출해 다단계 작업을 한 턴으로 압축.
- MCP 통합: stdio/HTTP MCP 서버의 외부 도구를 Hermes 도구로 자동 등록.
- 플러그인 시스템: 도구, hook, slash command, CLI command, provider, memory backend, context engine, gateway platform 등을 확장.
- 보안 장치: 위험 명령 승인, hardline blocklist, gateway allowlist/DM pairing, 컨테이너 격리, context file injection scanning.
- 연구/학습 데이터: batch processing, trajectory export, RL training용 데이터 생성.

## 4. 실행/사용 진입점

`pyproject.toml`의 console script는 다음 세 가지다.

- `hermes = hermes_cli.main:main`: 주 CLI 진입점. 대부분의 사용자 명령이 여기로 들어간다.
- `hermes-agent = run_agent:main`: 핵심 에이전트 실행 진입점.
- `hermes-acp = acp_adapter.entry:main`: ACP editor integration 진입점.

문서에서 추천하는 첫 사용 순서는 다음이다.

1. 설치: `pip install hermes-agent` 또는 git installer.
2. 모델 설정: `hermes model`.
3. 첫 대화: `hermes` 또는 `hermes --tui`.
4. 세션 확인: `hermes --continue`.
5. 이후 필요에 따라 `hermes gateway setup`, `hermes tools`, `hermes skills`, `hermes dashboard`, `hermes acp`를 추가한다.

## 5. 주요 모듈과 책임

문서가 제시한 내부 구조 기준 주요 책임은 다음과 같다.

- `run_agent.py`: `AIAgent` 핵심 conversation loop. prompt 구성, provider 선택, tool call 반복, fallback, compression, persistence를 관장.
- `cli.py`: classic interactive CLI.
- `hermes_cli/`: `hermes` 하위 명령, config, setup wizard, auth, model switching, skills hub, tools config, plugins, callbacks.
- `agent/`: prompt builder, context compression, prompt caching, auxiliary model, memory manager, model metadata, display, skill command.
- `tools/`: tool registry와 각 도구 구현. terminal/file/web/browser/code execution/delegation/MCP 등.
- `gateway/`: messaging gateway. 플랫폼 adapter, session store, delivery, pairing, hook, status.
- `cron/`: scheduled job 저장/실행.
- `acp_adapter/`: VS Code/Zed/JetBrains용 ACP server.
- `plugins/`: memory provider, context engine, model provider, image generation backend, platform plugin 등.
- `skills/`: 설치 시 기본 복사되는 bundled skills.
- `optional-skills/`: hub에서 명시 설치하는 공식 선택형 skills.
- `ui-tui/`, `tui_gateway/`: React/Ink 기반 현대적 TUI와 Python backend.
- `website/`: Docusaurus 문서 사이트.
- `tests/`: 문서상 약 17k 테스트, 로컬 파일 수 기준 1,148개 테스트 관련 파일.

## 6. 핵심 개념과 용어

- Agent loop: LLM 호출, 도구 호출, 도구 결과 반영, 최종 응답까지 반복하는 동기 실행 루프.
- Tool: LLM이 호출할 수 있는 함수. 예: `terminal`, `read_file`, `web_search`, `delegate_task`.
- Toolset: 도구 묶음. 플랫폼/세션별로 enable/disable 가능.
- Skill: 필요할 때 로드되는 Markdown 지식/절차 문서. slash command로 호출 가능.
- Memory: 항상 주입되는 작은 장기 메모리. `MEMORY.md`, `USER.md`.
- Session search: SQLite/FTS5 기반 과거 대화 검색.
- Gateway: 여러 메시징 플랫폼과 에이전트 세션을 연결하는 장기 실행 프로세스.
- Cron job: 일정에 따라 새 에이전트 세션을 만들고 결과를 전달하는 자동 작업.
- Delegation: 별도 컨텍스트 하위 에이전트에게 작업을 위임.
- execute_code: Python 스크립트가 Hermes 도구를 RPC로 호출하는 실행 모드.
- MCP server: 외부 도구 서버. Hermes는 `mcp_<server>_<tool>` 형식으로 등록한다.
- Plugin: Hermes 자체를 수정하지 않고 도구/훅/명령/provider 등을 추가하는 확장 단위.
- ACP: 편집기와 agent를 연결하는 JSON-RPC/stdio 기반 통합 방식.
- HERMES_HOME: 기본적으로 `~/.hermes/`이며 config, env, skills, memories, sessions, logs가 저장된다.

## 7. 입력/데이터/상태/제어 흐름

CLI 흐름:

1. 사용자가 `hermes` 또는 `hermes chat`으로 메시지를 입력한다.
2. `HermesCLI`가 입력과 slash command를 처리한다.
3. `AIAgent.run_conversation()`이 시스템 프롬프트를 구성한다.
4. provider resolver가 모델/인증/API mode를 결정한다.
5. LLM이 응답하거나 도구 호출을 요청한다.
6. `model_tools.handle_function_call()`이 registry를 통해 도구를 실행한다.
7. 도구 결과가 대화에 추가되고 루프가 반복된다.
8. 최종 응답과 세션은 SQLite/session log에 저장된다.

Gateway 흐름:

1. 플랫폼 adapter가 Telegram/Discord/Slack 등의 메시지를 받는다.
2. Gateway가 사용자를 authorize하고 chat별 session key를 찾는다.
3. 해당 session history로 `AIAgent`를 실행한다.
4. 결과를 원래 플랫폼으로 다시 전달한다.

Cron 흐름:

1. Gateway scheduler가 60초마다 due job을 확인한다.
2. 각 job은 새 `AIAgent` 세션에서 실행된다.
3. job에 연결된 skill이 있으면 주입된다.
4. 결과는 origin, local file, 특정 플랫폼 또는 `all` 대상으로 전달된다.

## 8. 설정 및 환경 구성

설정은 `~/.hermes/` 아래에 모인다.

- `config.yaml`: 모델, terminal backend, compression, memory, toolsets, delegation 등 일반 설정.
- `.env`: API key, bot token, secret.
- `auth.json` 또는 provider별 auth store: OAuth credential.
- `SOUL.md`: 전역 agent personality.
- `skills/`: 활성 skills.
- `memories/`: `MEMORY.md`, `USER.md`.
- `state.db`: SQLite session DB.
- `cron/`, `sessions/`, `logs/`: 예약 작업, 세션 로그, 로그.

우선순위는 CLI arguments, `config.yaml`, `.env`, built-in defaults 순이다. 문서상 원칙은 secret은 `.env`, 일반 설정은 `config.yaml`에 둔다. `hermes config set`은 key 성격에 따라 저장 위치를 자동 분기한다.

### Docker 기반 실행/격리 방식

문서에는 Docker가 두 가지 방식으로 등장한다.

1. **Hermes 자체를 Docker 컨테이너 안에서 실행하는 방식**
   - 근거 문서: `website/docs/user-guide/docker.md`
   - gateway/dashboard를 장기 실행 서비스처럼 배포할 때 적합하다.
   - `docker run`, `docker compose`, volume, port, inference server 네트워킹, resource limit 등이 문서화되어 있다.

2. **Hermes는 호스트에서 실행하고, terminal/file/code execution 도구만 Docker backend에서 실행하는 방식**
   - 근거 문서: `website/docs/user-guide/configuration.md`, `website/docs/user-guide/features/tools.md`, `website/docs/user-guide/security.md`
   - 설정 예:

```bash
hermes config set terminal.backend docker
```

```yaml
terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
  docker_forward_env: []
  docker_mount_cwd_to_workspace: false
  container_persistent: true
```

Docker backend의 중요한 동작 특성:

- 명령마다 새 컨테이너를 만드는 방식이 아니다.
- Hermes가 첫 사용 시 하나의 장기 실행 컨테이너를 만들고, 이후 terminal/file/`execute_code` 호출을 `docker exec`로 같은 컨테이너에 보낸다.
- `/new`, `/reset`, `delegate_task` subagent 사이에서도 Hermes 프로세스 생명주기 동안 같은 컨테이너가 공유될 수 있다.
- 컨테이너 내부의 `/workspace` 파일, 설치한 패키지, 환경 변경은 다음 tool call에도 이어질 수 있다.
- parallel subagent가 같은 컨테이너를 공유하면 `cd`, env 변경, 같은 경로 쓰기 등이 충돌할 수 있다.

보안상 의미:

- `terminal.backend: local`이면 agent의 shell/file 작업이 사용자 PC 권한으로 직접 실행된다.
- Docker backend는 그 실행 표면을 컨테이너 안으로 옮겨 호스트 파일/환경에 대한 직접 접근을 줄인다.
- 기본적으로 현재 호스트 작업 디렉터리는 컨테이너에 자동 mount되지 않는다. 필요하면 `docker_mount_cwd_to_workspace: true` 또는 `docker_volumes`로 명시해야 한다.
- 기본적으로 임의의 호스트 credential/env var도 컨테이너에 전달되지 않는다. 필요한 값만 `docker_forward_env`에 명시한다.
- `docker_forward_env`나 skill-declared env var로 전달한 secret은 컨테이너 내부 명령에서 읽을 수 있으므로 노출 가능한 것으로 취급해야 한다.
- 보안 문서상 Docker/Singularity/Modal/Daytona/Vercel backend에서는 컨테이너 자체를 보안 경계로 간주하기 때문에 dangerous command approval이 skip될 수 있다.

따라서 개인 PC에서 처음 실험할 때의 보수적 권장값은 다음이다.

```yaml
terminal:
  backend: docker
  docker_mount_cwd_to_workspace: false
  docker_forward_env: []
```

필요한 프로젝트 폴더만 별도 sandbox 경로로 mount하고, API key/SSH key/홈 디렉터리 전체를 컨테이너에 넘기지 않는 방식이 안전하다.

## 9. 의존성 구조

Python 패키지 기준:

- Python 3.11 이상 필요.
- 핵심 의존성은 `openai`, `httpx`, `rich`, `pydantic`, `prompt_toolkit`, `croniter`, `PyJWT`, `psutil` 등.
- provider/search/TTS/voice/messaging/cloud backend는 optional extras와 lazy dependency로 분리되어 있다.
- `[all]` extra는 cron, CLI, dev, pty, mcp, homeassistant, sms, acp, google, web, youtube 등을 포함한다.
- 테스트 도구는 `pytest`, `pytest-asyncio`, `pytest-xdist`, `ruff`, `ty`.

Node 쪽:

- 루트 `package.json`은 `agent-browser`에 의존하며 Node 20 이상을 요구한다.
- TUI, website, web dashboard, WhatsApp bridge는 각각 별도 `package.json`을 가진다.
- 설치 문서는 Node 22가 브라우저 도구/WhatsApp/TUI 등에 쓰인다고 설명한다.

저장소 규모:

- 제외 경로를 빼고 확인한 파일 확장자는 `.py` 1,747개, `.md` 984개, `.ts` 318개, `.tsx` 89개, `.yaml` 83개가 주요 비중이다.
- 상위 파일 수 디렉터리는 `tests`, `skills`, `website`, `ui-tui`, `optional-skills`, `plugins`, `web`, `agent`, `tools`, `hermes_cli`, `gateway` 순이다.

## 10. 빌드/실행/테스트 방식

사용자 설치:

```bash
pip install hermes-agent
hermes postinstall
hermes model
hermes
```

또는 git installer:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes
```

Windows native는 PowerShell installer가 있으며 문서상 early beta다. 가장 검증된 Windows 경로는 WSL2로 안내한다.

개발 설치:

```bash
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
uv venv venv --python 3.11
uv pip install -e ".[all,dev]"
npm install
hermes doctor
hermes chat -q "Hello"
```

테스트:

```bash
scripts/run_tests.sh
pytest tests/ -v
```

`pyproject.toml` 기준 pytest 기본 설정은 `testpaths = ["tests"]`, `addopts = "-m 'not integration' -n auto"`다.

## 11. 에러 처리와 디버깅 사인

문서상 사용자가 문제를 만났을 때의 진단 루틴은 다음 명령이 중심이다.

- `hermes doctor`: config/dependency 진단.
- `hermes model`: provider/model/auth 재설정.
- `hermes setup`: 전체 setup 재실행.
- `hermes sessions list`, `hermes --continue`: 세션 문제 확인.
- `hermes gateway status`: gateway 문제 확인.
- `hermes logs`: agent/gateway/error log 확인.
- `hermes dump`, `hermes debug`: 지원 요청용 상태 덤프/업로드.

일반 실패 모드는 provider auth/model 선택 오류, custom endpoint 설정 오류, gateway token/allowlist 오류, 세션 profile mismatch, 과도한 routing/fallback 설정, config migration 누락이다.

## 12. 확장하거나 기여할 때 봐야 할 구조

기여자가 먼저 볼 문서/파일:

1. `website/docs/developer-guide/architecture.md`
2. `website/docs/developer-guide/agent-loop.md`
3. `website/docs/developer-guide/prompt-assembly.md`
4. `website/docs/developer-guide/provider-runtime.md`
5. `website/docs/developer-guide/tools-runtime.md`
6. `website/docs/developer-guide/session-storage.md`
7. `website/docs/developer-guide/gateway-internals.md`
8. `website/docs/developer-guide/creating-skills.md`
9. `website/docs/guides/build-a-hermes-plugin.md`
10. `CONTRIBUTING.md`
11. `AGENTS.md`

기능을 확장할 때의 선택 기준:

- 반복 가능한 절차/지식이면 Skill.
- LLM이 호출해야 하는 함수형 능력이면 Tool 또는 Plugin tool.
- 외부 도구 서버가 이미 있으면 MCP.
- 새 메시징 플랫폼이면 gateway platform plugin 또는 `gateway/platforms`.
- 새 LLM provider는 model provider plugin 또는 provider runtime 문서.
- 새 memory backend는 memory provider plugin.
- 내부 핵심 기능으로 편입할 때만 `tools/`와 `toolsets.py`를 수정한다.

## 13. 처음 기여자가 먼저 읽어야 할 파일

- 사용자로 쓰려면: `README.md`, `website/docs/getting-started/quickstart.md`, `website/docs/user-guide/cli.md`, `website/docs/user-guide/tui.md`, `website/docs/user-guide/configuration.md`.
- 봇/자동화로 쓰려면: `website/docs/user-guide/messaging/index.md`, `website/docs/user-guide/features/cron.md`, `website/docs/user-guide/features/security.md`.
- 도구/기능을 이해하려면: `website/docs/user-guide/features/tools.md`, `skills.md`, `memory.md`, `mcp.md`, `plugins.md`.
- 내부 구조를 이해하려면: `website/docs/developer-guide/architecture.md`, `CONTRIBUTING.md`, `AGENTS.md`.
- 실행 진입점을 확인하려면: `pyproject.toml`의 `[project.scripts]`.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

이번 분석은 `.md` 문서 중심이므로 다음은 확인 필요로 남긴다.

- 문서에 나온 모든 명령/옵션이 현재 코드와 완전히 일치하는지: 일부는 빠르게 변화하는 프로젝트 특성상 코드 확인이 필요하다.
- provider 수, tool 수, messaging platform 수의 정확한 최신 개수: 문서마다 "40+", "70+", "20+"처럼 표현이 다르다. 전체 registry를 코드로 집계하면 더 정확하다.
- Windows native의 실제 안정성: 문서는 early beta로 명시한다.
- API server, dashboard, ACP, TUI의 실제 런타임 호환성: optional extras와 Node/PTY/브라우저 설치 상태에 따라 달라진다.
- 보안 경계의 실제 강도: 문서상 구조는 확인했지만 보안 감사는 수행하지 않았다.
