---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-19
updated: 2026-11-19
sources:
  - cli-hub/setup.py
  - cli-hub/cli_hub/cli.py
  - cli-hub/cli_hub/registry.py
  - cli-hub/cli_hub/installer.py
  - cli-hub/cli_hub/analytics.py
  - registry.json
  - public_registry.json
---

# [Q] `cli-anything-hub`(`cli-hub`)는 무엇이고, README의 설치 흐름은 실제와 같은가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 동작 흐름 `코드 확인` + 실행 확인(Windows, venv). 개별 CLI의 내부 동작은 `미확인`

---

## 1. 질문 및 결론

- **질문**: README는 `pip install cli-anything-hub`를 먼저 하고 `cli-hub install <name>`으로 CLI를 설치하라고 한다. `cli-hub`는 무엇을 하는 도구이고, README 설명이 실제와 일치하는가.
- **핵심 결론**: `cli-hub`는 CLI-Anything이 만든 CLI와 외부 CLI의 **registry(목록 JSON)를 받아 와서 설치·갱신·삭제·실행하는 package manager**다. 대상 소프트웨어를 직접 다루지 않고, registry에 적힌 설치 명령을 대신 실행할 뿐이다. README의 흐름(`list` → `install` → `launch`)은 실행 결과와 일치했다. 다만 목록이 README 표보다 훨씬 크고(103개), README에 없는 명령 3개와 기본 활성 상태의 사용 통계 전송이 있다.

---

## 2. 동작 설명

### 2.1 구성 요소

- **패키지**: `cli-hub/setup.py`의 `version="0.4.1"`. PyPI 이름은 `cli-anything-hub`, 설치되는 명령은 `cli-hub`다.
- **registry**: `registry.py:9-10`이 두 URL에서 JSON을 받는다. `https://hkuds.github.io/CLI-Anything/registry.json`(harness, 79개)과 `.../public_registry.json`(public, 24개)이다. 받은 JSON을 `~/.cli-hub/`에 1시간(`CACHE_TTL = 3600`) 캐시하고, 네트워크가 실패하면 캐시를 쓴다(`registry.py:36-52`).
- **두 registry의 차이**: `fetch_all_clis`가 두 목록을 합치며 각 항목에 `_source` 값을 붙인다. `harness`는 CLI-Anything 방식으로 만든 CLI이고, `public`은 다른 곳에서 배포하는 CLI(공식 CLI 포함)다.

### 2.2 명령

`cli.py`에 등록된 명령은 `install`, `uninstall`, `update`, `list`, `search`, `info`, `launch`, `can`, `matrix`, `previews`다. README 명령 표에는 앞의 7개만 있고, `can`(작업에 맞는 capability 검색), `matrix`(여러 CLI를 묶은 workflow 설치), `previews`(preview bundle 조회)는 없다. 이 3개의 내부 동작은 읽지 않았다(`미확인`).

### 2.3 `install`이 하는 일

`install_cli`가 registry에서 항목을 찾고 `_perform_action`(`installer.py:301-312`)이 strategy를 골라 실행한다. strategy는 `_install_strategy`(`installer.py:106-119`)가 정한다.

1. 항목에 `install_strategy`가 있으면 그것을 쓴다.
2. 없고 `harness` 소속이면 `pip`다.
3. `public` 소속이면 `npm_package`나 `package_manager`를 보고 `npm`, `uv`, `bundled`를 고르고, 해당이 없으면 `command`(항목의 `install_cmd`를 그대로 실행)다.

`pip` strategy는 `sys.executable -m pip install`에 `install_cmd`의 `pip install ` 뒷부분을 붙여 실행한다(`installer.py:184-193`). 예를 들어 `mermaid`의 `install_cmd`는 `pip install git+https://github.com/HKUDS/CLI-Anything.git#subdirectory=mermaid/agent-harness`다. **PyPI 패키지가 아니라 GitHub의 `mermaid/agent-harness/` 폴더를 pip이 직접 받아 설치한다.** harness 항목 79개 중 66개가 이 레포의 하위 폴더를 이 방식으로 설치한다. 나머지는 `sketch`(이 레포 폴더, npm)와 외부 12개(PyPI, 외부 GitHub, cargo)다([q2](./q2-hub-catalog.md) 4절).

### 2.4 `launch`

`launch`는 `shutil.which(entry_point)`로 PATH에서 실행 파일을 찾고, 없으면 "먼저 install하라"는 오류를 낸 뒤 `os.execvp`로 그 프로그램을 실행한다(`cli.py:301-325`). 설치되지 않은 상태에서 `launch`하면 설치를 대신 해 주지 않는다.

### 2.5 사용 통계 전송

`analytics.py`는 PostHog(`https://us.i.posthog.com`)로 이벤트를 보낸다. `CLI_HUB_NO_ANALYTICS`가 `1`/`true`/`yes`가 아니면 켜져 있다(`analytics.py:85`). 즉 **기본값은 전송이다.** `cli.py`가 `track_first_run`, `track_install`, `track_launch`, `track_visit` 등을 호출하고, 이벤트에는 `platform`(OS 이름)이 들어간다. `CLAUDE_CODE`, `CODEX`, `CURSOR_*` 같은 환경 변수와 부모 프로세스 이름으로 어떤 에이전트가 호출했는지도 판별한다(`analytics.py:24-60`, `143`). 전송 내용 전체(이벤트별 속성)는 읽지 않았다. 끄려면 `CLI_HUB_NO_ANALYTICS=1`을 설정한다.

---

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 버전 | `cli-hub/setup.py:53` | `version="0.4.1"` | 설치된 `pip show` 결과와 일치 |
| registry URL·캐시 | `cli-hub/cli_hub/registry.py:9-52` | `REGISTRY_URL`, `_fetch_json` | 원격 JSON, 1시간 캐시, 실패 시 캐시 |
| 병합 | `cli-hub/cli_hub/registry.py` | `fetch_all_clis` | harness + public, `_source` 태그 |
| strategy 결정 | `cli-hub/cli_hub/installer.py:106-119` | `_install_strategy` | harness는 pip, public은 npm/uv/bundled/command |
| pip 설치 | `cli-hub/cli_hub/installer.py:184-193` | `_pip_install` | `install_cmd`를 `pip install`로 실행 |
| 실행 | `cli-hub/cli_hub/cli.py:301-325` | `launch` | PATH 검사 후 `os.execvp` |
| 통계 | `cli-hub/cli_hub/analytics.py:85`, `:143` | `CLI_HUB_NO_ANALYTICS` | 기본 전송, 에이전트 환경 변수 판별 |

---

## 4. 검증 과정 및 실행 결과

Windows 11, Python 3.12.13, scratchpad의 새 venv에서 실행했다. `repos/CLI-Anything`(`34f5195`)은 변경하지 않았다.

```bash
pip install cli-anything-hub          # → 0.4.1
cli-hub --help                        # 명령 10개 (2.2절)
cli-hub list | grep -cE '^\s{5}\S'    # → 103
cli-hub info drawio                   # Requires: draw.io desktop app / Source: harness
cli-hub install mermaid               # ✓ Installed Mermaid (cli-anything-mermaid)
cli-anything-mermaid --json project new -o t.json
```

- `pip list`에 `cli-anything-hub 0.4.1`, `cli-anything-mermaid 1.0.0`이 나타났다.
- `--json project new`는 `{"action": "new_project", "sample": "flowchart", ...}` JSON을 출력했다. README의 `--json` flag와 `project`/`diagram`/`export`/`session`/`repl` 하위 명령 구조와 일치한다.
- **원격 registry와 로컬 파일 비교**: `~/.cli-hub/`에 캐시된 원격 JSON을 `repos/CLI-Anything`의 `registry.json`·`public_registry.json`과 비교했다. 항목 이름과 필드가 모두 같다(차이 0). 두 파일의 `meta.updated`는 `2026-06-19`(harness)와 `2026-08-20`(public)이고, 레포 HEAD 커밋일은 `2026-09-22`다. 즉 registry는 HEAD보다 오래된 상태다(날짜 `meta.updated`는 사람이 갱신하는 값인지 자동인지 `미확인`).
- Windows에서 pip이 `cp949` 인코딩 오류 로그(`--- Logging error ---`)를 냈지만 설치는 성공했다. `PYTHONUTF8=1`을 설정하면 이 로그를 피할 수 있다.

**실행 부작용(보고)**: 처음 실행 때 `CLI_HUB_NO_ANALYTICS`를 설정하지 않아 `track_first_run`과 `track_install` 이벤트가 PostHog로 전송됐을 가능성이 있다(전송 성공 여부는 확인하지 못함). 홈 디렉터리에 `~/.cli-hub/`(캐시, `installed.json`, `.analytics_id`)가 만들어졌다.

---

## 5. 남은 질문 및 추가 조사 사항

- [ ] `can`, `matrix`, `previews` 명령의 동작과 `matrix_registry.json` 구조
- [ ] 전송되는 통계 이벤트의 속성 전체(`analytics.py:214-380`)
- [ ] registry `meta.updated`가 HEAD보다 오래된 이유(갱신 절차)와 `harness`/`public`을 나누는 기준
