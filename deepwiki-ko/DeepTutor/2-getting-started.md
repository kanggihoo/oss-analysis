---
type: deepwiki-translation
repo: DeepTutor
source: artifacts/DeepTutor/deepwiki/pages-md/2-getting-started.md
deepwiki_url: https://deepwiki.com/HKUDS/DeepTutor/2-getting-started
section: "2"
order: 2
---

# 시작하기

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성할 때 참고한 컨텍스트로 사용되었습니다:

- [.gitattributes](.gitattributes)
- [.github/pull_request_template.md](.github/pull_request_template.md)
- [.github/workflows/pypi-release.yml](.github/workflows/pypi-release.yml)
- [.gitignore](.gitignore)
- [.secrets.baseline](.secrets.baseline)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [Dockerfile](Dockerfile)
- [deeptutor/api/run_server.py](deeptutor/api/run_server.py)
- [deeptutor_cli/main.py](deeptutor_cli/main.py)
- [requirements.txt](requirements.txt)
- [requirements/dev.txt](requirements/dev.txt)
- [requirements/math-animator.txt](requirements/math-animator.txt)
- [web/app/(workspace)/page.tsx](web/app/(workspace)/page.tsx)

</details>



이 문서는 DeepTutor의 설치, 배포, 초기 구성을 위한 고수준 안내를 제공합니다. 여기에는 필수 요건, 주요 설치 방식(Docker 및 CLI 기반), 그리고 내장 초기화 및 실행 스크립트를 사용한 필수 환경 설정이 포함됩니다.

멀티스테이지 빌드와 supervisord 설정을 포함한 자세한 Docker 배포 지침은 [Docker Deployment](#2.1)를 참고하세요. 환경 변수, YAML 설정, LLM 제공자 설정에 대한 종합 안내는 [Configuration Guide](#2.2)를 참고하세요.

---

## 필수 요건

DeepTutor는 배포 방식에 따라 서로 다른 의존성을 요구합니다. 이 시스템에는 런타임 파일 구성을 돕는 `deeptutor init` 명령이 포함되어 있습니다 [deeptutor_cli/main.py:16-16]().

### Docker 배포(권장)

| 요구 사항 | 최소 버전 | 목적 |
|------------|-----------------|---------|
| Docker | 20.10+ | 컨테이너 런타임 |
| Docker Compose | 2.0+ | 다중 컨테이너 오케스트레이션 |
| 사용 가능 메모리 | 4GB+ | 프론트엔드와 백엔드를 함께 실행 |

### 수동 설치

| 요구 사항 | 최소 버전 | 목적 |
|------------|-----------------|---------|
| Python | 3.11 | 백엔드 런타임 [Dockerfile:63-63](), [requirements.txt:4-4]() |
| Node.js | 22 | 프론트엔드 빌드 및 런타임 [Dockerfile:23-23](), [Dockerfile:58-58]() |
| npm | 최신 | 프론트엔드 패키지 관리 [Dockerfile:143-145]() |
| Rust/Cargo | 최신 | `tiktoken` 및 vision 패키지 빌드에 필요 [Dockerfile:89-92]() |
| 시스템 Libs | - | `libgl1`, `libglib2.0-0` for OpenCV and vision [Dockerfile:127-138]() |

**Sources:** [Dockerfile:23-138](), [requirements.txt:4-4](), [deeptutor_cli/main.py:16-16]()

---

## Installation Architecture Overview

The following diagram maps the installation and startup process to the scripts and entities within the codebase.

### Deployment Flow: Natural Language to Code Entity

```mermaid
graph TB
    subgraph "Configuration_Layer"
        ["deeptutor_init"] -- "register_init" --> ["deeptutor_cli.init_cmd"]
        ["pyproject.toml"] -- "defines_extras" --> ["pip_install"]
    end

    subgraph "Docker_Deployment"
        ["Dockerfile"] -- "multi_stage_build" --> ["production_stage"]
        ["supervisord"] -- "spawn" --> ["start-backend.sh"]
        ["supervisord"] -- "spawn" --> ["web/server.js"]
    end

    subgraph "CLI_Runtime"
        ["deeptutor_start"] -- "calls" --> ["deeptutor.runtime.launcher:start"]
        ["deeptutor_serve"] -- "calls" --> ["deeptutor.api.main:app"]
        ["deeptutor_chat"] -- "REPL" --> ["deeptutor_cli.chat:register"]
    end

    subgraph "Data_Persistence"
        ["data/user/workspace"]
        ["data/knowledge_bases"]
        ["data/memory"]
    end

    ["start-backend.sh"] -- "exec" --> ["deeptutor.api.main:app"]
    ["deeptutor.api.main:app"] -- "io" --> ["data/user/workspace"]
```

**Sources:** [deeptutor_cli/main.py:113-162](), [Dockerfile:103-187](), [requirements.txt:1-20](), [deeptutor_cli/main.py:12-24]()

---

## 1단계: 저장소 설정

저장소를 복제하고 환경을 준비합니다. `deeptutor` CLI는 `typer`를 통해 설정과 실행을 위한 통합 인터페이스를 제공합니다 [deeptutor_cli/main.py:29-34]().

```bash
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Recommended: Setup virtual environment and install
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[all]"
```

이 시스템은 `RunMode`를 사용해 `CLI`와 `SERVER` 실행 경로를 구분합니다 [deeptutor_cli/main.py:26-26](), [deeptutor/api/run_server.py:40-40](). 기여자의 경우 분기 전략을 준수해야 하며, 일반 기능은 `dev`, 테넌트 관련 격리는 `multi-user`를 대상으로 해야 합니다 [CONTRIBUTING.md:32-60]().

**Sources:** [deeptutor_cli/main.py:26-34](), [CONTRIBUTING.md:32-60](), [CONTRIBUTING.md:98-109](), [requirements.txt:11-18]()

---

## 2단계: 필수 설정

DeepTutor는 LLM 및 Embedding 제공자에 대한 구성이 필요합니다. 초기 런타임 설정은 첫 시작 시 `data/user/settings` 아래에 생성됩니다 [Dockerfile:13-13]().

### 디렉터리 구조와 영속성

이 시스템은 영속성을 위해 구조화된 `data/` 디렉터리를 초기화하며, 일반적으로 버전 관리에서 제외됩니다 [Dockerfile:167-181](), [.gitignore:8-13]().

| 디렉터리 | 코드 참조 | 목적 |
|-----------|----------------|---------|
| `data/user/settings` | [Dockerfile:168-168]() | 설정 및 제공자 프로필 |
| `data/knowledge_bases` | [Dockerfile:181-181]() | 벡터 저장소 및 RAG 문서 |
| `data/memory` | [Dockerfile:169-169]() | 경량 영속 메모리 |
| `data/user/workspace/chat` | [Dockerfile:174-174]() | 세션별 채팅 데이터 |

**Sources:** [Dockerfile:167-181](), [.gitignore:8-13]()

---

## 3단계: 배포 방식

### 옵션 A: Docker (프로덕션)
`Dockerfile`은 프로덕션용 이미지를 만들기 위해 멀티스테이지 빌드를 사용합니다 [Dockerfile:1-15]().
1. **frontend-builder**: Next.js를 `standalone` 모드로 빌드합니다 [Dockerfile:23-50]().
2. **python-base**: 시스템 의존성(OpenCV, Rust)과 Python 요구사항을 설치합니다 [Dockerfile:63-98]().
3. **production**: 플랫폼과 일치하는 Node 런타임과 Python 환경을 결합하고, `supervisord`가 이를 관리합니다 [Dockerfile:103-187]().

시작하려면:
```bash
docker build -t deeptutor:local .
docker run -p 3782:3782 -p 8001:8001 -v deeptutor-data:/app/data deeptutor:local
```
**Sources:** [Dockerfile:1-187]()

### 옵션 B: 수동 / CLI (개발)
개발용으로는 CLI `start` 명령을 사용해 백엔드와 프론트엔드를 함께 시작할 수 있습니다 [deeptutor_cli/main.py:113-121]().

```bash
# Launch both backend and frontend
deeptutor start

# Or start just the API server
deeptutor serve --reload
```

`serve` 명령은 시스템을 자동으로 `RunMode.SERVER`로 전환하고 [deeptutor_cli/main.py:133-133]() `uvicorn`을 시작합니다 [deeptutor_cli/main.py:154-160]().

**Sources:** [deeptutor_cli/main.py:113-160](), [deeptutor/api/run_server.py:30-69]()

---

## 시스템 구성 요소 매핑

```mermaid
graph LR
    subgraph "Client_Space"
        ["Browser_UI"]
        ["deeptutor_chat_REPL"]
    end

    subgraph "Application_Runtime"
        ["Next.js_Frontend"]
        ["FastAPI_Backend"]
        ["RunMode_SERVER"]
        ["RunMode_CLI"]
    end

    subgraph "Data_Persistence"
        ["data/memory"]
        ["data/knowledge_bases"]
        ["data/user/workspace/chat"]
    end

    ["Browser_UI"] -- "HTTP" --> ["Next.js_Frontend"]
    ["Next.js_Frontend"] -- "API" --> ["FastAPI_Backend"]
    ["deeptutor_chat_REPL"] -- "Local_Invoke" --> ["RunMode_CLI"]
    ["FastAPI_Backend"] -- "Storage" --> ["data/user/workspace/chat"]
```

**Sources:** [deeptutor_cli/main.py:26-27](), [deeptutor/api/run_server.py:40-41](), [Dockerfile:167-181](), [web/app/(workspace)/page.tsx:10-30]()
