---
type: deepwiki-translation
repo: DeepTutor
source: artifacts/DeepTutor/deepwiki/pages-md/12-api-layer.md
deepwiki_url: https://deepwiki.com/HKUDS/DeepTutor/12-api-layer
section: "12"
order: 51
---

# API 계층

<details>
<summary>관련 소스 파일</summary>

이 위키 페이지를 생성할 때 컨텍스트로 사용된 파일은 다음과 같습니다:

- [deeptutor/api/main.py](deeptutor/api/main.py)
- [deeptutor/api/routers/auth.py](deeptutor/api/routers/auth.py)
- [tests/api/test_auth_contextvar.py](tests/api/test_auth_contextvar.py)
- [tests/api/test_selective_access_log.py](tests/api/test_selective_access_log.py)
- [web/components/SessionList.tsx](web/components/SessionList.tsx)
- [web/components/sidebar/UtilitySidebar.tsx](web/components/sidebar/UtilitySidebar.tsx)
- [web/components/sidebar/WorkspaceSidebar.tsx](web/components/sidebar/WorkspaceSidebar.tsx)

</details>



API 계층은 Next.js 프런트엔드와 DeepTutor 백엔드 서비스 사이의 중심 통신 브리지 역할을 합니다. **FastAPI** 기반으로 구축된 이 계층은 상태 관리(settings, sessions, memory, knowledge bases)를 위한 HTTP REST 엔드포인트와 실시간 스트리밍 에이전트 상호작용을 위한 통합 WebSocket 인터페이스를 조율합니다.

## 아키텍처 개요

백엔드 진입점은 `deeptutor/api/main.py`에 정의되어 있으며, 여기서 FastAPI 애플리케이션을 초기화하고 핵심 서비스의 수명 주기를 관리합니다. 애플리케이션 수명 동안 `EventBus`, `TutorBotManager`, LLM 클라이언트가 올바르게 시작되고 종료되도록 보장합니다 [deeptutor/api/main.py:115-195]().

### 구성 요소 상호작용 다이어그램
이 다이어그램은 `FastAPI` 애플리케이션이 프런트엔드 요청을 내부 런타임 레지스트리와 서비스에 어떻게 연결하는지 보여줍니다.

```mermaid
graph TD
    subgraph "Frontend (Next.js)"
        [UI_Components]
        [WS_Client]
    end

    subgraph "API Layer (FastAPI)"
        [main.py_FastAPI_App]
        [unified_ws.py_Router]
        [settings.py_Router]
        [knowledge.py_Router]
        [auth.py_Router]
        [SafeOutputStaticFiles]
    end

    subgraph "Core Services"
        [ToolRegistry]
        [CapabilityRegistry]
        [EventBus]
        [KnowledgeBaseManager]
        [TutorBotManager]
    end

    [UI_Components] --> [settings.py_Router]
    [UI_Components] --> [knowledge.py_Router]
    [UI_Components] --> [auth.py_Router]
    [WS_Client] <--- "Streaming Events" ---> [unified_ws.py_Router]
    
    [main.py_FastAPI_App] --> [unified_ws.py_Router]
    [main.py_FastAPI_App] --> [settings.py_Router]
    [main.py_FastAPI_App] --> [knowledge.py_Router]
    [main.py_FastAPI_App] --> [auth.py_Router]
    
    [unified_ws.py_Router] --> [EventBus]
    [knowledge.py_Router] --> [KnowledgeBaseManager]
    [main.py_FastAPI_App] --> [ToolRegistry]
    [main.py_FastAPI_App] --> [CapabilityRegistry]
    [main.py_FastAPI_App] --> [TutorBotManager]
    [main.py_FastAPI_App] --> [SafeOutputStaticFiles]
```
**Sources:** [deeptutor/api/main.py:205-212](), [deeptutor/api/routers/auth.py:48-51](), [deeptutor/api/main.py:43-54]()

## 핵심 책임

### 1. 수명 주기 및 검증
시작 시 API 계층은 중요한 일관성 검사를 수행합니다. `validate_tool_consistency` 함수는 capability manifest에서 참조된 모든 도구가 실제로 `ToolRegistry`에 등록되어 있는지 검증합니다 [deeptutor/api/main.py:56-82](). 또한 하위 제공자 통합을 위해 `OPENAI_API_KEY` 같은 환경 변수가 사용 가능한지 확인하기 위해 `LLMClient`를 초기에 미리 초기화합니다 [deeptutor/api/main.py:129-136]().

### 2. 정적 artifact 제공
API에는 특수한 `SafeOutputStaticFiles` 마운트가 포함되어 있습니다. 이 구성 요소는 `PathService`를 통해 특정 경로를 화이트리스트로 지정하여 에이전트가 생성한 파일(예: Manim 애니메이션 또는 코드 실행 출력)에 대한 접근을 제한하고, 허가되지 않은 디렉터리 탐색을 방지합니다 [deeptutor/api/main.py:43-54]().

### 3. 인증 및 다중 사용자 범위
API 계층은 `deeptutor/api/routers/auth.py`를 통해 유연한 인증 시스템을 구현합니다. 로컬 SQLite/JSON 인증과 외부 **PocketBase** 통합을 모두 지원합니다 [deeptutor/api/routers/auth.py:29-44]().
* **Auth 가드:** `require_auth`(HTTP)와 `ws_require_auth`(WebSocket) 같은 재사용 가능한 의존성이 보안을 강제합니다 [deeptutor/api/routers/auth.py:183-207]().
* **컨텍스트 전파:** 인증 의존성은 `async def`로 선언되어 `ContextVar` 변경 사항(`CurrentUser` 설정)이 엔드포인트로 올바르게 전파되도록 하며, 시스템이 조용히 관리자 작업 공간으로 되돌아가 버릴 수 있는 문제를 방지합니다 [deeptutor/api/routers/auth.py:162-181](), [tests/api/test_auth_contextvar.py:1-19]().

### 데이터 엔티티 매핑
다음 다이어그램은 상위 수준 API 개념을 해당 구현 클래스와 데이터 구조에 매핑합니다.

```mermaid
classDiagram
    class FastAPI_App {
        +lifespan()
        +validate_tool_consistency()
    }
    class PathService {
        +is_public_output_path(path)
    }
    class TokenPayload {
        +user_id: str
        +username: str
        +role: str
    }
    class LoginRequest {
        +username: str
        +password: str
    }
    class RegisterRequest {
        +username: str
        +password: str
    }

    [FastAPI_App] --> [PathService] : uses for isolation
    [FastAPI_App] --> [TokenPayload] : verifies identity
    [auth.py_Router] --> [LoginRequest] : parses payload
    [auth.py_Router] --> [RegisterRequest] : handles signup
```
**Sources:** [deeptutor/api/main.py:43-82](), [deeptutor/api/routers/auth.py:33-71](), [deeptutor/api/routers/auth.py:183-207]()

## 하위 페이지

API 계층은 다음과 같은 특화 모듈로 더 나뉩니다:

### [Settings API](#12.1)
LLM 제공자, 검색 엔진, 시스템 전반의 기본 설정 구성을 관리합니다. 프런트엔드가 런타임 설정을 가져오고 업데이트할 수 있게 합니다.
자세한 내용은 [Settings API](#12.1)를 참고하세요.

### [Unified WebSocket and Session API](#12.2)
실시간 상호작용을 위한 주 인터페이스입니다. 턴 기반 실행과 세션 관리(list, rename, delete)를 포함한 양방향 이벤트 스트리밍을 처리하는 통합 엔드포인트를 다룹니다.
자세한 내용은 [Unified WebSocket and Session API](#12.2)를 참고하세요.

## 로깅 및 미들웨어
* **노이즈 억제:** API에는 WebSocket 연결/해제 메시지로 uvicorn 로그가 넘쳐나는 것을 방지하는 `_SuppressWsNoise` 필터가 포함되어 있습니다 [deeptutor/api/main.py:24-34]().
* **Access 로깅:** 특수 미들웨어는 200이 아닌 HTTP 응답이 uvicorn의 `AccessFormatter`가 요구하는 올바른 인자 개수로 기록되도록 하여 내부 로깅 오류를 방지합니다 [tests/api/test_selective_access_log.py:1-6]().

**Sources:** [deeptutor/api/main.py:1-212](), [deeptutor/api/routers/auth.py:1-207](), [tests/api/test_auth_contextvar.py:1-170](), [tests/api/test_selective_access_log.py:1-89]()
