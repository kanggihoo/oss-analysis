# agent-browser

AI 에이전트를 위한 브라우저 자동화 CLI. 빠른 네이티브 Rust CLI.

## 설치

### 전역 설치 (권장)

### Homebrew (macOS)

```bash
brew install agent-browser
agent-browser install  # Chrome for Testing에서 Chrome 다운로드 (최초 1회만 실행)
```

### Cargo (Rust)

```bash
cargo install agent-browser
agent-browser install  # Chrome for Testing에서 Chrome 다운로드 (최초 1회만 실행)
```

### 업데이트

최신 버전으로 업그레이드합니다:

```bash
agent-browser upgrade
```

사용자의 설치 방법(npm, Homebrew 또는 Cargo)을 감지하고 적절한 업데이트 명령을 자동으로 실행합니다.

### 요구사항

- **Chrome** - [Chrome for Testing](https://developer.chrome.com/blog/chrome-for-testing/)(구글 공식 자동화 채널)에서 Chrome을 다운로드하려면 `agent-browser install`을 실행하세요. 기존의 Chrome, Brave, Playwright 및 Puppeteer 설치도 자동으로 감지됩니다. 데몬을 실행하는 데는 Playwright나 Node.js가 필요하지 않습니다.
- **Node.js 24+ 및 pnpm 11+** - 소스에서 빌드할 때만 필요합니다.
- **Rust** - 소스에서 빌드할 때만 필요합니다 (위의 '소스에서 빌드' 참조).

## 빠른 시작

```bash
agent-browser open example.com
agent-browser snapshot                    # 참조(ref)가 포함된 접근성 트리 가져오기
agent-browser click @e2                   # 스냅샷의 참조를 사용하여 클릭
agent-browser fill @e3 "test@example.com" # 참조를 사용하여 값 입력
agent-browser get text @e1                # 참조를 사용하여 텍스트 가져오기
agent-browser screenshot page.png
agent-browser close
```

동의 배너나 모달 같이 다른 요소가 대상의 클릭 지점을 가리고 있는 경우 클릭은 조기에 실패합니다. 보고된 가리고 있는 요소를 닫거나 조작한 후, 기존 참조를 다시 시도하기 전에 스냅샷을 새로 가져오십시오.

헤드리스(Headless) 크로미움 스크린샷은 일관된 이미지 출력을 위해 네이티브 스크롤바를 숨깁니다. 네이티브 스크롤바를 계속 표시하려면 실행 시 `--hide-scrollbars false`를 전달하세요.

### 기존 선택자 (지원됨)

```bash
agent-browser click "#submit"
agent-browser fill "#email" "test@example.com"
agent-browser find role button click --name "Submit"
```

## 명령어

### 핵심 명령어

```bash
agent-browser open                    # 브라우저 실행 (탐색 없음; about:blank 상태로 대기)
agent-browser open <url>              # 실행 + URL로 이동 (별칭: goto, navigate)
agent-browser click <sel>             # 요소 클릭 (새 탭에서 열려면 --new-tab 추가)
agent-browser dblclick <sel>          # 요소 더블 클릭
agent-browser focus <sel>             # 요소에 포커스 지정
agent-browser type <sel> <text>       # 요소에 입력
agent-browser fill <sel> <text>       # 지운 후 입력
agent-browser press <key>             # 키 누르기 (Enter, Tab, Control+a 등) (별칭: key)
agent-browser keyboard type <text>    # 실제 키스트로크로 입력 (선택자 없음, 현재 포커스 대상)
agent-browser keyboard inserttext <text>  # 키 이벤트 없이 텍스트 삽입 (선택자 없음)
agent-browser keydown <key>           # 키 누르고 있기
agent-browser keyup <key>             # 키 떼기
agent-browser hover <sel>             # 요소 위에 마우스 올리기 (호버)
agent-browser select <sel> <val>      # 드롭다운 옵션 선택
agent-browser check <sel>             # 체크박스 체크
agent-browser uncheck <sel>           # 체크박스 해제
agent-browser scroll <dir> [px]       # 스크롤 (up/down/left/right, --selector <sel>)
agent-browser scrollintoview <sel>    # 요소를 화면 안으로 스크롤 (별칭: scrollinto)
agent-browser drag <src> <tgt>        # 드래그 앤 드롭
agent-browser upload <sel> <files>    # 파일 업로드
agent-browser screenshot [path]       # 스크린샷 캡처 (전체 페이지는 --full, 경로가 없으면 임시 디렉토리에 저장)
agent-browser screenshot --annotate   # 번호가 매겨진 요소 레이블이 포함된 주석 스크린샷
agent-browser screenshot --screenshot-dir ./shots    # 사용자 지정 디렉토리에 저장
agent-browser screenshot --screenshot-format jpeg --screenshot-quality 80
agent-browser pdf <path>              # PDF로 저장
agent-browser snapshot                # 참조가 포함된 접근성 트리 (AI에 가장 적합)
agent-browser eval <js>               # JavaScript 실행 (base64는 -b, 파이프 입력은 --stdin)
agent-browser connect <port>          # CDP를 통해 브라우저에 연결
agent-browser stream enable [--port <port>]  # 런타임 WebSocket 스트리밍 시작
agent-browser stream status           # 런타임 스트리밍 상태 및 바인딩된 포트 표시
agent-browser stream disable          # 런타임 WebSocket 스트리밍 중지
agent-browser close                   # 브라우저 닫기 (별칭: quit, exit)
agent-browser close --all             # 모든 활성 세션 닫기
agent-browser chat "<instruction>"    # AI 채팅: 자연어 브라우저 제어 (단일 실행)
agent-browser chat                    # AI 채팅: 대화형 REPL 모드
```

### 정보 가져오기

```bash
agent-browser get text <sel>          # 텍스트 콘텐츠 가져오기
agent-browser get html <sel>          # innerHTML 가져오기
agent-browser get value <sel>         # input 값 가져오기
agent-browser get attr <sel> <attr>   # 속성 가져오기
agent-browser get title               # 페이지 제목 가져오기
agent-browser get url                 # 현재 URL 가져오기
agent-browser get cdp-url             # CDP WebSocket URL 가져오기 (DevTools, 디버깅용)
agent-browser get count <sel>         # 일치하는 요소 수 세기
agent-browser get box <sel>           # 바운딩 박스(위치 및 크기) 가져오기
agent-browser get styles <sel>        # 계산된 스타일(computed styles) 가져오기
```

### 상태 확인

```bash
agent-browser is visible <sel>        # 표시 여부 확인
agent-browser is enabled <sel>        # 활성화 여부 확인
agent-browser is checked <sel>        # 체크 여부 확인
```

### 요소 찾기 (시맨틱 로케이터)

```bash
agent-browser find role <role> <action> [value]       # ARIA 역할로 찾기
agent-browser find text <text> <action>               # 텍스트 콘텐츠로 찾기
agent-browser find label <label> <action> [value]     # 레이블로 찾기
agent-browser find placeholder <ph> <action> [value]  # 플레이스홀더로 찾기
agent-browser find alt <text> <action>                # alt 텍스트로 찾기
agent-browser find title <text> <action>              # title 속성으로 찾기
agent-browser find testid <id> <action> [value]       # data-testid로 찾기
agent-browser find first <sel> <action> [value]       # 첫 번째 일치 요소
agent-browser find last <sel> <action> [value]        # 마지막 일치 요소
agent-browser find nth <n> <sel> <action> [value]     # N번째 일치 요소
```

**동작(Actions):** `click`, `fill`, `type`, `hover`, `focus`, `check`, `uncheck`, `text`

**옵션(Options):** `--name <name>` (접근 가능한 이름으로 역할 필터링), `--exact` (정확히 일치하는 텍스트 요구)

**예시:**

```bash
agent-browser find role button click --name "Submit"
agent-browser find text "Sign In" click
agent-browser find label "Email" fill "test@test.com"
agent-browser find first ".item" click
agent-browser find nth 2 "a" text
```

### 대기 (Wait)

```bash
agent-browser wait <selector>         # 요소가 표시될 때까지 대기
agent-browser wait <ms>               # 지정된 시간(밀리초) 동안 대기
agent-browser wait --text "Welcome"   # 텍스트가 나타날 때까지 대기 (부분 일치)
agent-browser wait --url "**/dash"    # URL 패턴 대기
agent-browser wait --load networkidle # 로드 상태 대기
agent-browser wait --fn "window.ready === true"  # JS 조건이 참이 될 때까지 대기

# 텍스트/요소가 사라질 때까지 대기
agent-browser wait --fn "!document.body.innerText.includes('Loading...')"
agent-browser wait "#spinner" --state hidden
```

**로드 상태:** `load`, `domcontentloaded`, `networkidle`

### 일괄 실행 (Batch Execution)

한 번의 호출로 여러 명령을 실행합니다. 명령은 따옴표로 묶인 인수로 전달하거나 stdin을 통해 JSON으로 파이프할 수 있습니다. 이를 통해 다단계 워크플로우를 실행할 때 명령별 프로세스 시작 오버헤드를 방지할 수 있습니다.

```bash
# 인수 모드: 따옴표로 묶인 각 인수가 하나의 전체 명령이 됩니다.
agent-browser batch "open https://example.com" "snapshot -i" "screenshot"

# 첫 번째 오류 발생 시 중지하려면 --bail 사용
agent-browser batch --bail "open https://example.com" "click @e1" "screenshot"

# Stdin 모드: 명령을 JSON으로 파이프 입력
echo '[
  ["open", "https://example.com"],
  ["snapshot", "-i"],
  ["click", "@e1"],
  ["screenshot", "result.png"]
]' | agent-browser batch --json
```

### 클립보드

```bash
agent-browser clipboard read                      # 클립보드에서 텍스트 읽기
agent-browser clipboard write "Hello, World!"     # 클립보드에 텍스트 쓰기
agent-browser clipboard copy                      # 현재 선택 영역 복사 (Ctrl+C)
agent-browser clipboard paste                     # 클립보드에서 붙여넣기 (Ctrl+V)
```

### 마우스 제어

```bash
agent-browser mouse move <x> <y>      # 마우스 이동
agent-browser mouse down [button]     # 버튼 누르기 (left/right/middle)
agent-browser mouse up [button]       # 버튼 떼기
agent-browser mouse wheel <dy> [dx]   # 스크롤 휠 작동
```

### 브라우저 설정

```bash
agent-browser set viewport <w> <h> [scale]  # 뷰포트 크기 설정 (레티나 디스플레이 등은 scale에 2 지정)
agent-browser set device <name>       # 기기 에뮬레이션 ("iPhone 14" 등)
agent-browser set geo <lat> <lng>     # 지리적 위치 설정
agent-browser set offline [on|off]    # 오프라인 모드 토글
agent-browser set headers <json>      # 추가 HTTP 헤더 설정
agent-browser set credentials <u> <p> # HTTP 기본 인증 정보 설정
agent-browser set media [dark|light]  # 색상 스키마 에뮬레이션
```

### 쿠키 및 스토리지

```bash
agent-browser cookies                 # 모든 쿠키 가져오기
agent-browser cookies set <name> <val> # 쿠키 설정
agent-browser cookies set --curl <file> # Copy-as-cURL 덤프, JSON 배열 또는 일반 Cookie 헤더에서 쿠키 가져오기 (자동 감지)
agent-browser cookies clear           # 쿠키 지우기

agent-browser storage local           # 모든 localStorage 가져오기
agent-browser storage local <key>     # 특정 키의 값 가져오기
agent-browser storage local set <k> <v>  # 값 설정
agent-browser storage local clear     # 모든 localStorage 지우기

agent-browser storage session         # sessionStorage에 대해 위와 동일하게 작동
```

### 네트워크

```bash
agent-browser network route <url>              # 요청 가로채기(라우팅)
agent-browser network route <url> --abort      # 요청 차단
agent-browser network route <url> --body <json>  # 모의(Mock) 응답 반환
agent-browser network route '*' --abort --resource-type script  # 스크립트만 차단
agent-browser network unroute [url]            # 라우팅 해제
agent-browser network requests                 # 추적된 요청 보기
agent-browser network requests --filter api    # 요청 필터링
agent-browser network requests --type xhr,fetch  # 리소스 유형별 필터링
agent-browser network requests --method POST   # HTTP 메서드별 필터링
agent-browser network requests --status 2xx    # 상태 코드별 필터링 (200, 2xx, 400-499)
agent-browser network request <requestId>      # 전체 요청/응답 상세 내용 보기
agent-browser network har start                # HAR 기록 시작
agent-browser network har stop [output.har]    # HAR 기록 중지 및 저장 (생략 시 임시 경로)
```

### 탭 및 창

```bash
agent-browser tab                              # 탭 목록 (`tabId` 및 옵션으로 레이블 표시)
agent-browser tab new [url]                    # 새 탭 열기 (선택적으로 URL 지정)
agent-browser tab new --label docs [url]       # 사용자 지정 레이블이 지정된 새 탭 열기
agent-browser tab <t<N>|label>                 # ID 또는 레이블로 탭 전환
agent-browser tab close [t<N>|label]           # 탭 닫기 (기본값은 활성 탭)
agent-browser window new                       # 새 창 열기
```

탭 ID는 `t1`, `t2`, `t3` 형식의 고정된 문자열입니다. 세션 내에서 절대 재사용되지 않으므로, 다른 탭이 열리거나 닫힌 후에도 스크립트와 에이전트가 동일한 탭을 계속 참조할 수 있습니다. `tab 2`와 같은 상대적인 정수 인덱스는 **허용되지 않습니다**. `t` 접두사는 인덱스와 핸들을 명확히 구분하고 요소 참조에 사용되는 `@e1` 규칙을 미러링합니다.

또한 기억하기 쉬운 레이블(`docs`, `app`, `admin`)을 할당하고 ID와 혼용할 수 있습니다. 레이블은 자동 생성되지 않으며 페이지를 이동하더라도 변경되지 않습니다. 사용자가 직접 이름 짓고 관리할 수 있습니다:

```bash
agent-browser tab new --label docs https://docs.example.com
agent-browser tab docs               # docs 탭으로 전환
agent-browser snapshot               # docs 탭의 참조(ref)들을 수집
agent-browser click @e3              # docs 탭의 참조를 사용하여 클릭
agent-browser tab close docs         # 레이블로 탭 닫기
```

### 프레임

```bash
agent-browser frame <sel>             # iframe으로 전환
agent-browser frame main              # 메인 프레임으로 복귀
```

### 대화 상자 (Dialogs)

```bash
agent-browser dialog accept [text]    # 수락 (선택적으로 프롬프트 텍스트 입력 가능)
agent-browser dialog dismiss          # 취소
agent-browser dialog status           # 대화 상자가 현재 열려 있는지 확인
```

기본적으로 `alert` 및 `beforeunload` 대화 상자는 에이전트의 작동을 방해하지 않도록 자동으로 수락됩니다. `confirm` 및 `prompt` 대화 상자는 계속 명시적인 처리가 필요합니다. 자동 처리를 비활성화하려면 `--no-auto-dialog` (또는 `AGENT_BROWSER_NO_AUTO_DIALOG=1`)를 사용하십시오.

JavaScript 대화 상자가 대기 중일 때 모든 명령의 응답에는 대화 상자 유형과 메시지가 포함된 `warning` 필드가 추가됩니다.

### 차이점 비교 (Diff)

```bash
agent-browser diff snapshot                              # 현재 스냅샷과 이전 스냅샷 비교
agent-browser diff snapshot --baseline before.txt        # 현재 스냅샷과 저장된 스냅샷 파일 비교
agent-browser diff snapshot --selector "#main" --compact # 특정 영역 스냅샷 비교
agent-browser diff screenshot --baseline before.png      # 기준 이미지와 시각적 픽셀 차이 비교
agent-browser diff screenshot --baseline b.png -o d.png  # 차이 이미지를 커스텀 경로에 저장
agent-browser diff screenshot --baseline b.png -t 0.2    # 색상 임계값 조절 (0-1)
agent-browser diff url https://v1.com https://v2.com     # 두 URL 비교 (스냅샷 비교)
agent-browser diff url https://v1.com https://v2.com --screenshot  # 시각적 차이 비교도 포함
agent-browser diff url https://v1.com https://v2.com --wait-until networkidle  # 커스텀 대기 전략
agent-browser diff url https://v1.com https://v2.com --selector "#main"  # 특정 요소로 범위 제한
```

### 디버그

```bash
agent-browser trace start             # 추적(Trace) 기록 시작
agent-browser trace stop [path]       # 추적 기록 중지 및 저장
agent-browser profiler start          # Chrome DevTools 프로파일링 시작
agent-browser profiler stop [path]    # 프로파일링 중지 및 저장 (.json)
agent-browser console                 # 콘솔 메시지 보기 (log, error, warn, info)
agent-browser console --json          # 프로그래밍 방식 접근을 위해 원시 CDP 인수가 포함된 JSON 출력
agent-browser console --clear         # 콘솔 비우기
agent-browser errors                  # 페이지 오류 보기 (처리되지 않은 JavaScript 예외)
agent-browser errors --clear          # 오류 기록 비우기
agent-browser highlight <sel>         # 요소 강조 표시 (하이라이트)
agent-browser inspect                 # 활성 페이지에 대한 Chrome DevTools 열기
agent-browser state save <path>       # 인증 상태 저장
agent-browser state load <path>       # 인증 상태 불러오기
agent-browser state list              # 저장된 상태 파일 목록 표시
agent-browser state show <file>       # 상태 요약 표시
agent-browser state rename <old> <new> # 상태 파일 이름 변경
agent-browser state clear [name]      # 세션의 상태 초기화
agent-browser state clear --all       # 모든 저장된 상태 초기화
agent-browser state clean --older-than <days>  # 오래된 상태 파일 삭제
```

### 탐색 (Navigation)

```bash
agent-browser back                    # 뒤로 가기
agent-browser forward                 # 앞으로 가기
agent-browser reload                  # 페이지 새로고침
agent-browser pushstate <url>         # SPA 클라이언트 측 탐색; window.next.router.push를 자동으로 감지하며,
                                      # 실패 시 history.pushState + popstate로 돌아갑니다.
```

### 탐색 전 설정 (Pre-navigation setup)

일부 흐름(SSR 디버깅, 보호된 오리진에 대한 인증 쿠키 설정, 초기화 스크립트 등록 등)은 첫 페이지 탐색 *전에* 브라우저 상태를 설정해야 합니다. URL 없이 `open`을 사용하여 브라우저를 실행한 후 쿠키/경로/초기화 스크립트를 준비하고 탐색을 진행하십시오. `batch` 명령을 사용하면 한 번의 CLI 호출로 이 모든 작업을 처리할 수 있습니다:

```bash
agent-browser batch \
  '["open"]' \
  '["network","route","*","--abort","--resource-type","script"]' \
  '["cookies","set","--curl","cookies.curl","--domain","localhost"]' \
  '["navigate","http://localhost:3000/target"]'
```

`batch`를 사용하지 않으면 동일한 시퀀스가 데몬을 재사용하는 세 개의 명령으로 나뉩니다 (속도는 빠르지만 여러 번 호출해야 함).

### React / Web Vitals

agent-browser는 수준 높은 React 내부 탐색 및 범용 Web Vitals 지표 수집 기능을 제공합니다. React 명령을 사용하려면 실행 시 React DevTools 훅이 설치되어 있어야 합니다. Web Vitals와 pushstate는 프레임워크에 구애받지 않고 작동합니다.

```bash
agent-browser open --enable react-devtools <url>   # React 훅이 설치된 상태로 실행
agent-browser react tree                           # 전체 컴포넌트 트리 가져오기
agent-browser react inspect <fiberId>              # props, hooks, state, 소스 확인
agent-browser react renders start                  # 파이버 렌더링 기록 시작
agent-browser react renders stop [--json]          # 기록 중지 및 프로필 출력 (원시 데이터는 --json)
agent-browser react suspense [--only-dynamic] [--json]  # Suspense 경계 및 분류기
                                                         # --only-dynamic은 "정적(static)" 목록을 숨김
agent-browser vitals [url] [--json]                # LCP/CLS/TTFB/FCP/INP + 하이드레이션(hydration) 요약
```

각 `react ...` 하위 명령은 브라우저 실행 시 `--enable react-devtools`가 전달되어 있어야 작동합니다 (바이너리에 React DevTools `installHook.js`가 임베디드되어 있음). 이 옵션이 없으면 `React DevTools hook not installed - relaunch with --enable react-devtools` 오류가 발생합니다.

Next.js, Remix, Vite+React, CRA, TanStack Start, React Native Web 등 모든 React 앱에서 작동합니다. `vitals`와 `pushstate`는 프레임워크와 상관없이 작동합니다. `vitals`는 기본적으로 요약을 출력하지만, 전체 구조화된 페이로드를 얻으려면 `--json`을 지정하세요.

### 초기화 스크립트 (Init scripts)

```bash
agent-browser open --init-script <path>           # 첫 탐색 전에 페이지 초기화 스크립트 등록
                                                   # (여러 개 지정 가능, AGENT_BROWSER_INIT_SCRIPTS 환경 변수로도 설정 가능)
agent-browser addinitscript <js>                  # 런타임에 등록 (식별자 반환)
agent-browser removeinitscript <identifier>       # 이전에 등록된 초기화 스크립트 제거
```

### 설정 및 검사 (Setup)

```bash
agent-browser install                 # Chrome for Testing(구글 공식 자동화 채널)에서 Chrome 다운로드
agent-browser install --with-deps     # 시스템 의존성도 함께 설치 (Linux)
agent-browser upgrade                 # agent-browser를 최신 버전으로 업그레이드
agent-browser doctor                  # 설치 상태 진단 및 오래된 데몬 파일 자동 청소
agent-browser doctor --fix            # 파괴적인 수리 작업도 함께 실행 (Chrome 재설치, 이전 상태 삭제 등...)
agent-browser doctor --offline --quick  # 네트워크 프로브 및 실제 실행 테스트 건너뛰기
```

`doctor`는 환경, Chrome 설치 상태, 데몬 상태, 설정 파일, 암호화 키, 제공업체, 네트워크 접근성을 확인하고 실제 헤드리스 브라우저 실행 테스트를 진행합니다. 오래된 소켓/pid 사이드카 파일은 자동으로 청소됩니다. 결과는 에이전트에서 활용할 수 있도록 `--json`으로도 제공됩니다.

### 스킬 (Skills)

```bash
agent-browser skills                  # 사용 가능한 스킬 목록 표시
agent-browser skills list             # 위와 동일
agent-browser skills get <name>       # 스킬의 전체 콘텐츠 출력
agent-browser skills get <name> --full  # 참조 및 템플릿 포함
agent-browser skills get --all        # 모든 스킬 출력
agent-browser skills path [name]      # 스킬 디렉토리 경로 출력
```

설치된 CLI 버전과 항상 일치하도록 패키징된 스킬 콘텐츠를 제공합니다. AI 에이전트는 캐시된 복사본에 의존하는 대신 이 기능을 통해 최신 지침을 얻을 수 있습니다. 스킬 디렉토리 경로를 무시하고 다른 경로를 사용하려면 `AGENT_BROWSER_SKILLS_DIR`을 설정하십시오.

## 인증 (Authentication)

agent-browser는 매번 다시 로그인할 필요가 없도록 로그인 세션을 유지하는 여러 가지 방법을 제공합니다.

### 빠른 요약

| 방식 | 가장 적합한 경우 | 플래그 / 환경 변수 |
|---|---|---|
| **Chrome 프로필 재사용** | 별도의 설정 없이 기존 Chrome 로그인 상태(쿠키, 세션)를 그대로 사용 | `--profile <이름>` / `AGENT_BROWSER_PROFILE` |
| **지속성 프로필** | 재시작 후에도 전체 브라우저 상태(쿠키, IndexedDB, 서비스 워커, 캐시)를 유지 | `--profile <경로>` / `AGENT_BROWSER_PROFILE` |
| **세션 지속성** | 세션 이름을 지정하여 쿠키 + localStorage를 자동 저장 및 복원 | `--session-name <이름>` / `AGENT_BROWSER_SESSION_NAME` |
| **브라우저에서 직접 가져오기** | 이미 로그인되어 있는 Chrome 세션에서 인증 정보 추출 | `--auto-connect` + `state save` |
| **상태 파일** | 시작 시 이전에 저장된 상태 JSON 파일을 로드 | `--state <경로>` / `AGENT_BROWSER_STATE` |
| **인증 금고 (Vault)** | 자격 증명을 로컬에 암호화하여 저장하고 세션 이름으로 로그인 | `auth save` / `auth login` |

### 본인 브라우저에서 인증 정보 가져오기

Chrome에서 이미 특정 사이트에 로그인되어 있는 경우, 해당 인증 상태를 가져와 재사용할 수 있습니다:

```bash
# 1. 원격 디버깅이 활성화된 상태로 Chrome 실행
#    macOS:
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222
#    또는 --auto-connect를 사용하여 이미 실행 중인 Chrome을 탐색하도록 합니다.

# 2. 연결하여 인증된 상태를 저장
agent-browser --auto-connect state save ./my-auth.json

# 3. 향후 세션에서 저장된 인증 정보 사용
agent-browser --state ./my-auth.json open https://app.example.com/dashboard

# 4. 또는 자동 지속성을 위해 --session-name 사용
agent-browser --session-name myapp state load ./my-auth.json
# 이제부터 --session-name myapp은 이 상태를 자동으로 저장/복원합니다.
```

> **보안 참고 사항:**
> - `--remote-debugging-port`는 localhost의 브라우저에 대한 제어 권한을 노출합니다. 임의의 로컬 프로세스가 연결할 수 있으므로, 신뢰할 수 있는 장치에서만 사용하고 완료되면 Chrome을 닫으십시오.
> - 상태 파일에는 세션 토큰이 일반 텍스트로 들어있습니다. `.gitignore`에 추가하고 더 이상 필요하지 않으면 삭제하십시오. 로컬 저장 시 암호화하려면 `AGENT_BROWSER_ENCRYPTION_KEY`를 설정하세요 ([상태 암호화](#상태-암호화) 참조).

로그인 흐름, OAuth, 2FA, 쿠키 기반 인증 및 인증 금고(vault)에 대한 자세한 내용은 [인증 문서](docs/src/app/sessions/page.mdx)를 참조하십시오.

## 세션 (Sessions)

격리된 여러 브라우저 인스턴스를 실행합니다:

```bash
# 서로 다른 세션 실행
agent-browser --session agent1 open site-a.com
agent-browser --session agent2 open site-b.com

# 또는 환경 변수를 통해 지정
AGENT_BROWSER_SESSION=agent1 agent-browser click "#btn"

# 활성 세션 목록 표시
agent-browser session list
# 출력 예시:
# Active sessions:
# -> default
#    agent1

# 현재 세션 표시
agent-browser session
```

각 세션은 개별적인 다음 항목들을 가집니다:

- 브라우저 인스턴스
- 쿠키 및 스토리지
- 탐색 기록 (History)
- 인증 상태

## Chrome 프로필 재사용 (Chrome Profile Reuse)

기존 로그인 상태를 사용하는 가장 빠른 방법은 Chrome 프로필 이름을 `--profile`에 전달하는 것입니다:

```bash
# 사용 가능한 Chrome 프로필 목록 표시
agent-browser profiles

# 기본 Chrome 프로필의 로그인 상태 재사용
agent-browser --profile Default open https://gmail.com

# 명명된 프로필 사용 (표시 이름 또는 디렉토리 이름)
agent-browser --profile "Work" open https://app.example.com

# 또는 환경 변수를 통해 지정
AGENT_BROWSER_PROFILE=Default agent-browser open https://gmail.com
```

이 방식은 Chrome 프로필을 임시 디렉토리로 복사하여(읽기 전용 스냅샷이며 원본 프로필을 변경하지 않음) 기존 쿠키 및 세션 정보와 함께 브라우저가 실행되도록 합니다.

> **참고:** Windows에서는 Chrome이 실행 중인 경우 일부 프로필 파일이 잠길 수 있으므로, `--profile <이름>`을 사용하기 전에 Chrome을 닫으십시오.

## 지속성 프로필 (Persistent Profiles)

브라우저가 재시작되어도 상태를 유지하는 지속성 커스텀 프로필 디렉토리를 사용하려면 `--profile`에 경로를 전달하십시오:

```bash
# 지속성 프로필 디렉토리 사용
agent-browser --profile ~/.myapp-profile open myapp.com

# 한 번 로그인하면 다음에도 인증된 세션이 재사용됨
agent-browser --profile ~/.myapp-profile open myapp.com/dashboard

# 또는 환경 변수를 통해 지정
AGENT_BROWSER_PROFILE=~/.myapp-profile agent-browser open myapp.com
```

프로필 디렉토리에는 다음 정보들이 저장됩니다:

- 쿠키 및 localStorage
- IndexedDB 데이터
- 서비스 워커
- 브라우저 캐시
- 로그인 세션

**팁**: 브라우저 상태를 서로 격리하기 위해 프로젝트별로 다른 프로필 경로를 사용하십시오.

## 세션 지속성 (Session Persistence)

대신 `--session-name`을 사용하면 브라우저 재시작 시 쿠키 및 localStorage를 자동으로 저장하고 복원할 수 있습니다:

```bash
# "twitter" 세션의 상태 자동 저장/로드
agent-browser --session-name twitter open twitter.com

# 한 번 로그인하면 세션 상태가 자동으로 유지됨
# 상태 파일은 ~/.agent-browser/sessions/ 에 저장됩니다.

# 또는 환경 변수를 통해 설정
export AGENT_BROWSER_SESSION_NAME=twitter
agent-browser open twitter.com
```

### 상태 암호화

AES-256-GCM을 사용하여 저장된 세션 데이터를 로컬에서 암호화합니다:

```bash
# 키 생성 예시: openssl rand -hex 32
export AGENT_BROWSER_ENCRYPTION_KEY=<64자의-16진수-키>

# 이제 세션 상태 파일이 자동으로 암호화됩니다.
agent-browser --session-name secure open example.com
```

| 변수 | 설명 |
|---|---|
| `AGENT_BROWSER_SESSION_NAME` | 자동 저장/로드 상태 지속성에 사용할 세션 이름 |
| `AGENT_BROWSER_ENCRYPTION_KEY` | AES-256-GCM 암호화를 위한 64자 16진수 키 |
| `AGENT_BROWSER_STATE_EXPIRE_DAYS` | N일보다 오래된 상태 자동 삭제 (기본값: 30) |

## 보안 (Security)

agent-browser는 안전한 AI 에이전트 배포를 위한 보안 기능을 포함하고 있습니다. 모든 기능은 선택 사항(opt-in)이며, 명시적으로 활성화하기 전까지 기존 워크플로우에 영향을 주지 않습니다:

- **인증 금고 (Authentication Vault)**: 자격 증명을 로컬에 안전하게 암호화하여 저장하고 이름으로 참조합니다. LLM에 비밀번호가 절대 노출되지 않습니다. `auth login`은 페이지가 `load`될 때까지 탐색한 후 로그인 폼 선택자가 나타날 때까지 대기합니다 (SPA 친화적이며 타임아웃은 기본 작업 타임아웃을 따릅니다). `AGENT_BROWSER_ENCRYPTION_KEY`가 설정되지 않은 경우 `~/.agent-browser/.encryption-key`에 키가 자동 생성됩니다: `echo "pass" | agent-browser auth save github --url https://github.com/login --username user --password-stdin` 실행 후 `agent-browser auth login github` 사용.
- **콘텐츠 경계 마커 (Content Boundary Markers)**: LLM이 도구 출력과 신뢰할 수 없는 콘텐츠를 구별할 수 있도록 페이지 출력을 구분 기호로 래핑합니다: `--content-boundaries`
- **도메인 허용 목록 (Domain Allowlist)**: 신뢰할 수 있는 도메인으로의 탐색만 제한합니다 (`*.example.com`과 같은 와일드카드는 기본 도메인도 함께 찾습니다): `--allowed-domains "example.com,*.example.com"`. 허용되지 않은 도메인에 대한 하위 리소스 요청(스크립트, 이미지, fetch) 및 WebSocket/EventSource 연결도 모두 차단됩니다. 대상 페이지가 의존하는 CDN 도메인이 있다면 함께 포함해야 합니다 (예: `*.cdn.example.com`).
- **작업 정책 (Action Policy)**: 정적 정책 파일로 파괴적인 작업을 제한합니다: `--action-policy ./policy.json`
- **작업 확인 (Action Confirmation)**: 민감한 카테고리의 작업에 대해 명시적인 승인을 요구합니다: `--confirm-actions eval,download`
- **출력 길이 제한**: 컨텍스트 폭주를 방지합니다: `--max-output 50000`

| 변수 | 설명 |
|---|---|
| `AGENT_BROWSER_CONTENT_BOUNDARIES` | 페이지 출력을 경계 마커로 감싸기 |
| `AGENT_BROWSER_MAX_OUTPUT` | 페이지 출력의 최대 문자 수 설정 |
| `AGENT_BROWSER_ALLOWED_DOMAINS` | 쉼표로 구분된 허용 도메인 패턴 목록 |
| `AGENT_BROWSER_ACTION_POLICY` | 작업 정책 JSON 파일의 경로 |
| `AGENT_BROWSER_CONFIRM_ACTIONS` | 확인이 필요한 작업 범주 목록 |
| `AGENT_BROWSER_CONFIRM_INTERACTIVE` | 대화형 확인 프롬프트 활성화 |

자세한 내용은 [보안 문서](https://agent-browser.dev/security)를 참조하십시오.

## 스냅샷 옵션 (Snapshot Options)

`snapshot` 명령은 출력 크기를 줄이기 위한 필터링을 지원합니다:

```bash
agent-browser snapshot                    # 전체 접근성 트리
agent-browser snapshot -i                 # 상호작용 가능한 요소만 표시 (버튼, 입력 필드, 링크)
agent-browser snapshot -i --urls          # 링크 URL을 포함하여 상호작용 가능한 요소 표시
agent-browser snapshot -c                 # 컴팩트 모드 (비어있는 구조적 요소 제거)
agent-browser snapshot -d 3               # 트리 깊이를 3레벨로 제한
agent-browser snapshot -s "#main"         # 특정 CSS 선택자 영역으로 범위 한정
agent-browser snapshot -i -c -d 5         # 여러 옵션 결합
```

| 옵션 | 설명 |
|---|---|
| `-i, --interactive` | 상호작용 가능한 요소만 표시 (버튼, 링크, 입력창 등) |
| `-u, --urls` | 링크 요소에 대해 href URL 포함 |
| `-c, --compact` | 비어 있는 구조적 요소 제거 |
| `-d, --depth <n>` | 트리 탐색 깊이 제한 |
| `-s, --selector <sel>` | 특정 CSS 선택자로 한정 |

## 주석 처리된 스크린샷 (Annotated Screenshots)

`--annotate` 플래그는 스크린샷의 상호작용 가능한 요소 위에 번호가 매겨진 레이블을 오버레이합니다. 각 레이블 `[N]`은 `@eN` 참조에 일치하므로 시각적 및 텍스트 기반 워크플로우 모두에서 동일한 참조를 사용할 수 있습니다.

주석 스크린샷은 CDP 기반 브라우저 경로(Chrome/Lightpanda)에서 지원됩니다. Safari/WebDriver 백엔드는 아직 `--annotate`를 지원하지 않습니다.

```bash
agent-browser screenshot --annotate
# -> 스크린샷이 /tmp/screenshot-2026-02-17T12-00-00-abc123.png 에 저장되었습니다.
#    [1] @e1 button "Submit"
#    [2] @e2 link "Home"
#    [3] @e3 textbox "Email"
```

주석 스크린샷이 저장된 후 참조가 캐시되므로 요소들과 즉시 상호작용할 수 있습니다:

```bash
agent-browser screenshot --annotate ./page.png
agent-browser click @e2     # [2]로 레이블 지정된 "Home" 링크 클릭
```

이 기능은 시각적 레이아웃, 레이블이 없는 아이콘 버튼, 캔버스 요소 또는 텍스트 접근성 트리가 캡처할 수 없는 시각적 상태를 추론할 수 있는 다중 모드(Multimodal) AI 모델에 매우 유용합니다.

## 옵션 (Options)

| 옵션 | 설명 |
|---|---|
| `--session <name>` | 격리된 세션 사용 (또는 `AGENT_BROWSER_SESSION` 환경 변수 사용) |
| `--session-name <name>` | 세션 상태 자동 저장/복원 (또는 `AGENT_BROWSER_SESSION_NAME` 환경 변수 사용) |
| `--profile <name\|path>` | Chrome 프로필 이름 또는 지속성 디렉토리 경로 (또는 `AGENT_BROWSER_PROFILE` 환경 변수 사용) |
| `--state <path>` | JSON 파일로부터 스토리지 상태 로드 (또는 `AGENT_BROWSER_STATE` 환경 변수 사용) |
| `--headers <json>` | URL 오리진으로 범위가 제한된 HTTP 헤더 설정 |
| `--executable-path <path>` | 커스텀 브라우저 실행 파일 경로 (또는 `AGENT_BROWSER_EXECUTABLE_PATH` 환경 변수 사용) |
| `--extension <path>` | 브라우저 확장 프로그램 로드 (여러 번 지정 가능, `AGENT_BROWSER_EXTENSIONS` 환경 변수 사용 가능) |
| `--init-script <path>` | 첫 페이지 탐색 전에 페이지 초기화 스크립트 등록 (여러 번 지정 가능, `AGENT_BROWSER_INIT_SCRIPTS` 환경 변수 사용 가능) |
| `--enable <feature>` | 내장 초기화 스크립트: `react-devtools` (여러 개 지정 시 쉼표 사용, `AGENT_BROWSER_ENABLE` 환경 변수 사용 가능) |
| `--args <args>` | 브라우저 실행 인수, 쉼표나 개행문자로 구분 (또는 `AGENT_BROWSER_ARGS` 환경 변수 사용) |
| `--user-agent <ua>` | 사용자 지정 User-Agent 문자열 (또는 `AGENT_BROWSER_USER_AGENT` 환경 변수 사용) |
| `--proxy <url>` | 인증 정보가 포함될 수 있는 프록시 서버 URL (또는 `AGENT_BROWSER_PROXY` 환경 변수 사용) |
| `--proxy-bypass <hosts>` | 프록시를 우회할 호스트 목록 (또는 `AGENT_BROWSER_PROXY_BYPASS` 환경 변수 사용) |
| `--ignore-https-errors` | HTTPS 인증서 오류 무시 (자체 서명된 인증서 등에 유용) |
| `--allow-file-access` | file:// URL이 로컬 파일에 액세스하도록 허용 (Chromium만 해당) |
| `--hide-scrollbars <bool>` | 헤드리스 크로미움 스크린샷에서 네이티브 스크롤바 숨기기 여부, 기본값은 참 (또는 `AGENT_BROWSER_HIDE_SCROLLBARS` 환경 변수 사용) |
| `-p, --provider <name>` | 클라우드 브라우저 서비스 제공업체 (또는 `AGENT_BROWSER_PROVIDER` 환경 변수 사용) |
| `--device <name>` | iOS 기기 이름, 예: "iPhone 15 Pro" (또는 `AGENT_BROWSER_IOS_DEVICE` 환경 변수 사용) |
| `--json` | JSON 형식 출력 (에이전트용) |
| `--annotate` | 번호가 매겨진 요소 레이블이 포함된 주석 스크린샷 생성 (또는 `AGENT_BROWSER_ANNOTATE` 환경 변수 사용) |
| `--screenshot-dir <path>` | 기본 스크린샷 저장 디렉토리 (또는 `AGENT_BROWSER_SCREENSHOT_DIR` 환경 변수 사용) |
| `--screenshot-quality <n>` | JPEG 화질 0-100 (또는 `AGENT_BROWSER_SCREENSHOT_QUALITY` 환경 변수 사용) |
| `--screenshot-format <fmt>` | 스크린샷 포맷: `png`, `jpeg` (또는 `AGENT_BROWSER_SCREENSHOT_FORMAT` 환경 변수 사용) |
| `--headed` | 브라우저 창 띄우기 (헤드리스 해제) (또는 `AGENT_BROWSER_HEADED` 환경 변수 사용) |
| `--cdp <port\|url>` | Chrome DevTools Protocol(CDP) 포트 또는 WebSocket URL을 통한 연결 |
| `--auto-connect` | 실행 중인 Chrome 자동 검색 및 연결 (또는 `AGENT_BROWSER_AUTO_CONNECT` 환경 변수 사용) |
| `--color-scheme <scheme>` | 색상 스키마: `dark`, `light`, `no-preference` (또는 `AGENT_BROWSER_COLOR_SCHEME` 환경 변수 사용) |
| `--download-path <path>` | 기본 다운로드 디렉토리 (또는 `AGENT_BROWSER_DOWNLOAD_PATH` 환경 변수 사용) |
| `--content-boundaries` | LLM 보안을 위해 페이지 출력을 경계 마커로 감싸기 (또는 `AGENT_BROWSER_CONTENT_BOUNDARIES` 환경 변수 사용) |
| `--max-output <chars>` | 페이지 출력을 N글자로 잘라내기 (또는 `AGENT_BROWSER_MAX_OUTPUT` 환경 변수 사용) |
| `--allowed-domains <list>` | 쉼표로 구분된 허용 도메인 패턴 목록 (또는 `AGENT_BROWSER_ALLOWED_DOMAINS` 환경 변수 사용) |
| `--action-policy <path>` | 작업 정책 JSON 파일 경로 (또는 `AGENT_BROWSER_ACTION_POLICY` 환경 변수 사용) |
| `--confirm-actions <list>` | 확인이 필요한 작업 범주 목록 (또는 `AGENT_BROWSER_CONFIRM_ACTIONS` 환경 변수 사용) |
| `--confirm-interactive` | 대화형 확인 프롬프트 활성화; stdin이 TTY가 아닐 경우 자동으로 거부됨 (또는 `AGENT_BROWSER_CONFIRM_INTERACTIVE` 환경 변수 사용) |
| `--engine <name>` | 브라우저 엔진: `chrome` (기본값), `lightpanda` (또는 `AGENT_BROWSER_ENGINE` 환경 변수 사용) |
| `--no-auto-dialog` | `alert`/`beforeunload` 대화 상자의 자동 닫기 비활성화 (또는 `AGENT_BROWSER_NO_AUTO_DIALOG` 환경 변수 사용) |
| `--model <name>` | 채팅 명령어에 사용할 AI 모델 이름 (또는 `AI_GATEWAY_MODEL` 환경 변수 사용) |
| `-v`, `--verbose` | 도구 명령어와 원시 결과물 출력 (채팅 시) |
| `-q`, `--quiet` | AI의 텍스트 답변만 표시하고 도구 호출 숨기기 (채팅 시) |
| `--config <path>` | 커스텀 설정 파일 사용 (또는 `AGENT_BROWSER_CONFIG` 환경 변수 사용) |
| `--debug` | 디버그 정보 출력 |

## 관찰 가능성 대시보드 (Observability Dashboard)

라이브 뷰포트와 명령어 액티비티 피드를 보여주는 로컬 웹 대시보드를 통해 agent-browser 세션을 실시간으로 모니터링할 수 있습니다.

```bash
# 대시보드 서버 시작 (포트 4848번으로 백그라운드에서 실행)
agent-browser dashboard start
agent-browser dashboard start --port 8080   # 커스텀 포트

# 이제 모든 세션이 자동으로 대시보드에 노출됩니다.
agent-browser open example.com

# 대시보드 정지
agent-browser dashboard stop
```

대시보드는 브라우저 세션과 무관하게 4848 포트에서 독립적인 백그라운드 프로세스로 동작합니다. 어떠한 세션도 실행 중이지 않을 때도 작동 가능하며, `http://localhost:4848`이나 대시보드 서버로 연결되는 프록시/포워딩 URL(예: `https://dashboard.agent-browser.localhost` 혹은 Coder 작업 공간 URL)을 통해 접속할 수 있습니다. 브라우저는 대시보드 오리진에 계속 머물러 있으며, 세션별 탭, 상태 및 스트림 트래픽은 내부적으로 프록시 처리되므로 세션 포트를 외부로 노출할 필요가 없습니다.

대시보드에 표시되는 정보는 다음과 같습니다:
- **라이브 뷰포트**: 브라우저로부터 실시간으로 전달되는 JPEG 프레임
- **액티비티 피드**: 타임스탬프 및 세부 정보를 접거나 펼쳐 볼 수 있는 시간순 명령어/결과 스트림
- **콘솔 출력**: 브라우저 콘솔 메시지 (log, warn, error)
- **세션 생성**: UI 상에서 로컬 엔진(Chrome, Lightpanda) 또는 클라우드 서비스(AgentCore, Browserbase, Browserless, Browser Use, Kernel)를 통한 새 세션 생성
- **AI 채팅**: 대시보드 내에서 직접 AI 어시스턴트와 채팅 (Vercel AI Gateway 설정 필요)

### AI 채팅

대시보드에는 Vercel AI Gateway 기반의 선택적인 AI 채팅 패널이 포함되어 있습니다. 동일한 기능을 CLI에서 `chat` 명령어로 직접 수행할 수도 있습니다. AI 채팅을 활성화하려면 다음 환경 변수를 설정하십시오:

```bash
export AI_GATEWAY_API_KEY=gw_your_key_here
export AI_GATEWAY_MODEL=anthropic/claude-sonnet-4.6           # 선택 사항, 기본값임
export AI_GATEWAY_URL=https://ai-gateway.vercel.sh           # 선택 사항, 기본값임
```

**CLI 사용법:**

```bash
agent-browser chat "open google.com and search for cats"     # 단발성 실행
agent-browser chat                                           # 대화형 REPL
agent-browser -q chat "summarize this page"                  # Quiet 모드 (텍스트 답변만 표시)
agent-browser -v chat "fill in the login form"               # Verbose 모드 (도구 명령어 출력 포함)
agent-browser --model openai/gpt-4o chat "take a screenshot" # AI 모델 명시적 변경
```

`chat` 명령어는 자연어 지시 사항을 agent-browser 명령어로 번역하여 실행하고 AI 답변을 스트리밍합니다. 대화형 모드에서는 `quit`를 입력하면 종료됩니다. 에이전트 개발이나 자동화 처리를 위해 구조화된 출력이 필요하다면 `--json`을 지정하세요.

**대시보드 사용법:**

대시보드 내에서는 Chat 탭이 항상 표시됩니다. `AI_GATEWAY_API_KEY`가 설정되어 있으면 Rust 서버는 게이트웨이로 요청을 프록시하고 Vercel AI SDK의 UI Message Stream 프로토콜을 사용해 대답을 스트리밍합니다. 키가 설정되어 있지 않은 채 메시지를 전송하면 오류가 화면에 인라인으로 표시됩니다.

## 설정 (Configuration)

매 명령마다 플래그를 반복해서 설정하는 대신 `agent-browser.json` 파일을 생성하여 지속성 기본값을 설정할 수 있습니다.

**위치 (우선순위가 낮음에서 높음 순):**

1. `~/.agent-browser/config.json`: 사용자 레벨 기본값
2. `./agent-browser.json`: 프로젝트 레벨 덮어쓰기 (현재 작업 디렉토리 기준)
3. `AGENT_BROWSER_*` 환경 변수가 설정 파일 값을 덮어씁니다.
4. CLI 플래그가 모든 설정을 최종적으로 덮어씁니다.

**`agent-browser.json` 작성 예시:**

```json
{
  "headed": true,
  "proxy": "http://localhost:8080",
  "profile": "./browser-data",
  "userAgent": "my-agent/1.0",
  "hideScrollbars": false,
  "ignoreHttpsErrors": true
}
```

기본 설정 파일 대신 임의의 설정 파일을 지정해 로드하려면 `--config <경로>` 또는 `AGENT_BROWSER_CONFIG`를 사용하세요:

```bash
agent-browser --config ./ci-config.json open example.com
AGENT_BROWSER_CONFIG=./ci-config.json agent-browser open example.com
```

위 옵션 테이블의 모든 설정 항목은 카멜 케이스(camelCase) 키 형식을 적용하여 설정 파일에 기재할 수 있습니다 (예: `--executable-path`는 `"executablePath"`, `--proxy-bypass`는 `"proxyBypass"`가 됨). 알 수 없는 키는 향후 호환성을 보장하기 위해 무시됩니다.

IDE 자동 완성 및 유효성 검사를 위해 [JSON 스키마](agent-browser.schema.json) 파일이 준비되어 있습니다. 이를 활성화하려면 설정 파일에 `$schema` 키를 지정하세요:

```json
{
  "$schema": "https://agent-browser.dev/schema.json",
  "headed": true
}
```

불리언(Boolean) 타입 플래그는 설정 파일의 값을 무시하도록 `true` 또는 `false`를 명시적으로 입력받을 수 있습니다. 예컨대 `--headed false`를 주면 설정 파일의 `"headed": true` 값이 무시됩니다. 값이 없는 `--headed`는 `--headed true`와 동등하게 처리됩니다.

검색 위치에 설정 파일이 없으면 오류 없이 자동으로 무시됩니다. 다만 `--config <경로>`로 지정한 파일이 존재하지 않거나 유효하지 않으면 에러를 내며 종료됩니다. 사용자 설정과 프로젝트 설정에서 확장 프로그램(Extensions)은 덮어써지지 않고 합쳐져(concatenated) 로드됩니다.

> **팁:** 만약 프로젝트별 `agent-browser.json` 파일에 실행 환경에 특화된 정보(특정 경로, 프록시 설정 등)가 담겨 있다면 `.gitignore`에 등록하는 것을 권장합니다.

## 기본 시간 초과 (Default Timeout)

표준 작업(클릭, 대기, 폼 채우기 등)에 대한 기본 타임아웃은 25초입니다. 이는 CLI의 30초 IPC 읽기 타임아웃보다 일부러 낮게 책정되어 있어, CLI가 EAGAIN과 함께 시간 초과되어 종료되지 않고 데몬이 제대로 된 오류를 반환하게 도와줍니다.

환경 변수를 이용해 기본 타임아웃을 변경할 수 있습니다:

```bash
# 느린 페이지를 위해 더 긴 타임아웃 설정 (밀리초 단위)
export AGENT_BROWSER_DEFAULT_TIMEOUT=45000
```

> **참고:** 이 값을 30000(30초) 이상으로 설정하면 동작이 느려질 때 CLI의 읽기 타임아웃이 먼저 발생하여 EAGAIN 오류가 생길 수 있습니다. CLI는 일시적인 네트워크 오류에 대해 자동으로 재시도하겠지만 응답 시간이 지연될 수 있습니다.

| 변수 | 설명 |
|---|---|
| `AGENT_BROWSER_DEFAULT_TIMEOUT` | 기본 타임아웃(밀리초 단위, 기본값: 25000) |

## 선택자 (Selectors)

### 참조 (Refs) (AI에 최적화 및 권장됨)

참조(Refs)는 스냅샷으로부터 결정론적인(deterministic) 요소 선택을 가능하게 합니다:

```bash
# 1. 참조가 포함된 스냅샷 획득
agent-browser snapshot
# 출력 예시:
# - heading "Example Domain" [ref=e1] [level=1]
# - button "Submit" [ref=e2]
# - textbox "Email" [ref=e3]
# - link "Learn more" [ref=e4]

# 2. 참조를 사용하여 인터랙션 수행
agent-browser click @e2                   # 버튼 클릭
agent-browser fill @e3 "test@example.com" # 텍스트 박스 채우기
agent-browser get text @e1                # 헤더 텍스트 가져오기
agent-browser hover @e4                   # 링크 위에 마우스 올리기
```

참조 클릭이 오버레이 레이어에 의해 가로막히는 경우, `covered by <div#consent-banner>`와 같이 가리고 있는 요소를 알리는 문구가 포함된 에러가 발생합니다. 먼저 해당 배너나 모달 컨트롤을 클릭해 화면에서 치운 후, 다시 참조를 사용하기 전에 `snapshot`을 한 번 더 실행하십시오.

**왜 참조를 사용해야 하나요?**

- **결정론적(Deterministic)**: 참조는 스냅샷 시점의 정확한 요소를 가리킵니다.
- **빠름**: DOM에 대한 반복적인 쿼리가 필요하지 않습니다.
- **AI 친화적**: 스냅샷 + 참조 방식은 LLM에 최적화된 작동 방식입니다.

### CSS 선택자

```bash
agent-browser click "#id"
agent-browser click ".class"
agent-browser click "div > button"
```

### 텍스트 및 XPath

```bash
agent-browser click "text=Submit"
agent-browser click "xpath=//button"
```

### 시맨틱 로케이터 (Semantic Locators)

```bash
agent-browser find role button click --name "Submit"
agent-browser find label "Email" fill "test@test.com"
```

## 에이전트 모드 (Agent Mode)

에이전트 프로그램이 해석하기 적합하도록 `--json`을 지정해 JSON 형식의 데이터를 출력합니다:

```bash
agent-browser snapshot --json
# 반환 결과: {"success":true,"data":{"snapshot":"...","refs":{"e1":{"role":"heading","name":"Title"},...}}}

agent-browser get text @e1 --json
agent-browser is visible @e2 --json
```

### 최적의 AI 워크플로우

```bash
# 1. 페이지 탐색 후 스냅샷 가져오기
agent-browser open example.com
agent-browser snapshot -i --json   # AI가 접근성 트리와 참조(refs) 목록을 해석함

# 2. AI가 스냅샷에서 대상 참조 식별
# 3. 해당 참조로 액션 수행
agent-browser click @e2
agent-browser fill @e3 "input text"

# 4. 페이지 상태가 바뀌면 새로운 스냅샷 가져오기
agent-browser snapshot -i --json
```

### 명령어 체이닝 (Command Chaining)

쉘 상에서 `&&`로 여러 명령어를 엮어 하나의 쉘 호출 내에서 실행할 수 있습니다. 브라우저가 백그라운드 데몬으로 계속 실행 중이므로 체이닝 방식은 안전하면서도 훨씬 효율적입니다:

```bash
# 페이지를 열고 네트워크가 유휴(idle) 상태가 될 때까지 기다린 후 스냅샷 찍기를 한 번에 처리
agent-browser open example.com && agent-browser wait --load networkidle && agent-browser snapshot -i

# 여러 조작 명령어 엮기
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "pass" && agent-browser click @e3

# 탐색 후 스크린샷 캡처
agent-browser open example.com && agent-browser wait --load networkidle && agent-browser screenshot page.png
```

중간 출력 결과가 필요 없는 경우에 `&&`를 사용하십시오. 반면, 후속 조작 전에 이전 결과물(예: 참조 식별을 위한 스냅샷 정보)의 파싱이 필요하다면 명령을 분리하여 각각 실행하십시오.

## Headed 모드

디버깅을 위해 브라우저 화면(창)을 띄워서 볼 수 있습니다:

```bash
agent-browser open example.com --headed
```

헤드리스 모드로 실행하는 대신 브라우저 창을 화면에 직접 띄웁니다.

> **참고:** 브라우저 확장 프로그램은 헤드리스 모드(Chrome의 `--headless=new`)와 headed 모드 모두에서 작동합니다.

## 인증된 세션 (Authenticated Sessions)

`--headers`를 지정하면 특정 오리진 영역에 강제할 HTTP 헤더를 설정할 수 있으므로, 복잡한 로그인 과정 없이 다이렉트로 인증할 수 있습니다:

```bash
# api.example.com 오리진으로 보낼 때만 적용되는 헤더
agent-browser open api.example.com --headers '{"Authorization": "Bearer <token>"}'

# api.example.com 으로 요청이 전송될 때 인증 헤더가 포함됨
agent-browser snapshot -i --json
agent-browser click @e2

# 다른 도메인으로 이동 시 해당 헤더가 전송되지 않음 (안전함!)
agent-browser open other-site.com
```

이 방식은 다음과 같은 상황에 유용합니다:

- **로그인 절차 건너뛰기** - 화면 조작 대신 요청 헤더를 통해 세션 인증 처리
- **사용자 전환** - 다른 인증 토큰으로 새 세션을 띄워 사용자 변경
- **API 테스트** - 보호 장치가 적용된 엔드포인트에 바로 액세스
- **보안** - 지정한 오리진 범위 내에서만 작동하고 다른 도메인으로 유출되지 않음

여러 오리진 각각에 대해 별도의 헤더를 매기려면 각 `open` 시점에 `--headers`를 설정하십시오:

```bash
agent-browser open api.example.com --headers '{"Authorization": "Bearer token1"}'
agent-browser open api.acme.com --headers '{"Authorization": "Bearer token2"}'
```

모든 도메인에 적용되는 전역 헤더를 등록하려면 `set headers`를 사용하십시오:

```bash
agent-browser set headers '{"X-Custom-Header": "value"}'
```

## 커스텀 브라우저 실행 파일 (Custom Browser Executable)

동봉된 기본 Chromium 대신 이미 설치된 임의의 브라우저 실행 파일을 가리킬 수 있습니다. 다음 상황에 필요합니다:

- **서버리스 배포**: `@sparticuz/chromium` 같이 용량이 가벼운 Chromium 빌드 이용 (약 50MB vs 기본 684MB)
- **로컬 브라우저 연동**: PC에 이미 설치되어 있는 Chrome/Chromium 인스턴스 사용
- **커스텀 빌드**: 따로 수정되거나 패치된 브라우저 엔진 사용

### CLI 사용법

```bash
# 플래그 지정
agent-browser --executable-path /path/to/chromium open example.com

# 환경 변수로 지정
AGENT_BROWSER_EXECUTABLE_PATH=/path/to/chromium agent-browser open example.com
```

### 서버리스 (Vercel)

임시 Vercel Sandbox 마이크로VM 상에서 agent-browser와 Chrome을 함께 실행합니다. 외부 서버는 따로 필요하지 않습니다:

```typescript
import { Sandbox } from "@vercel/sandbox";

const sandbox = await Sandbox.create({ runtime: "node24" });
await sandbox.runCommand("agent-browser", ["open", "https://example.com"]);
const result = await sandbox.runCommand("agent-browser", ["screenshot", "--json"]);
await sandbox.stop();
```

동작하는 데모 페이지와 Vercel 배포 버튼을 보려면 [환경 예시(examples/environments/)](examples/environments/)를 참고하십시오.

### 서버리스 (AWS Lambda)

```typescript
import chromium from '@sparticuz/chromium';
import { execSync } from 'child_process';

export async function handler() {
  const executablePath = await chromium.executablePath();
  const result = execSync(
    `AGENT_BROWSER_EXECUTABLE_PATH=${executablePath} agent-browser open https://example.com && agent-browser snapshot -i --json`,
    { encoding: 'utf-8' }
  );
  return JSON.parse(result);
}
```

## 로컬 파일 (Local Files)

`file://` URL 구조를 사용해 PC 내의 로컬 파일(PDF, HTML 등)을 열고 조작할 수 있습니다:

```bash
# 파일 액세스 허용 (JavaScript가 로컬 파일에 접근하는 데 필수)
agent-browser --allow-file-access open file:///path/to/document.pdf
agent-browser --allow-file-access open file:///path/to/page.html

# 로컬 PDF의 스크린샷 캡처
agent-browser --allow-file-access open file:///Users/me/report.pdf
agent-browser screenshot report.png
```

`--allow-file-access` 플래그는 Chromium에 내부 플래그(`--allow-file-access-from-files`, `--allow-file-access`)를 덧붙여서 `file://` 도메인의 자바스크립트가 다음 작업을 하도록 허용합니다:

- 로컬 파일 로드 및 렌더링
- JavaScript (XHR, fetch)를 통해 다른 로컬 파일에 접근
- 로컬 자원(이미지, 스크립트, CSS 스타일시트) 로드

**참고:** 이 플래그는 크로미움(Chromium) 엔진에서만 작동하며, 보안을 위해 기본적으로는 해제되어 있습니다.

## CDP 모드

Chrome DevTools Protocol(CDP)을 사용하여 이미 구동 중인 브라우저 세션에 접속합니다:

```bash
# 브라우저 실행: google-chrome --remote-debugging-port=9222

# 최초 1회 연결을 맺은 후, 그 다음부터는 --cdp 없이도 제어 가능
agent-browser connect 9222
agent-browser snapshot
agent-browser tab
agent-browser close

# 혹은 매 명령마다 --cdp를 전달하여 임시 연동 가능
agent-browser --cdp 9222 snapshot

# 원격 클라우드 브라우저 서비스의 WebSocket 주소로 연결
agent-browser --cdp "wss://your-browser-service.com/cdp?token=..." snapshot
```

`--cdp` 플래그는 다음 형태의 주소를 받습니다:

- `http://localhost:{port}`로 붙을 포트 번호 (예: `9222`)
- 외부 클라우드 브라우저 연결용 전체 WebSocket 주소 (예: `wss://...` 혹은 `ws://...`)

이를 활용하면 다음 플랫폼들을 통제할 수 있습니다:

- 일렉트론(Electron) 애플리케이션
- 원격 디버깅이 열려 있는 Chrome/Chromium 인스턴스
- WebView2 애플리케이션
- CDP 포트를 노출하고 있는 모든 브라우저

### 자동 연결 (Auto-Connect)

포트 번호를 일일이 기재하지 않아도 백그라운드에 켜져 있는 Chrome을 자동 감지해서 연결하려면 `--auto-connect`를 넘겨줍니다:

```bash
# 디버깅이 활성화된 채 켜져 있는 Chrome을 자동 감지해 접근
agent-browser --auto-connect open example.com
agent-browser --auto-connect snapshot

# 또는 환경 변수로 설정
AGENT_BROWSER_AUTO_CONNECT=1 agent-browser snapshot
```

자동 연결은 브라우저를 탐색할 때 다음 규칙을 거칩니다:

1. 기본 사용자 데이터 경로에서 Chrome의 `DevToolsActivePort` 파일을 분석하여 정보 획득
2. 탐색이 실패하면 널리 쓰이는 표준 디버깅 포트(9222, 9229)에 대해 스캔 시도
3. HTTP 기반 디바이스 탐색(`/json/version`, `/json/list`)에 실패하면 WebSocket으로 다이렉트 엑세스 시도

다음 상황에서 요긴하게 작동합니다:

- Chrome 144+ 버전에서 `chrome://inspect/#remote-debugging`을 통해 가변 포트로 원격 디버깅을 시작했을 때
- 별도의 설정 없이 실행 중인 기존 브라우저에 가볍게 달라붙고 싶을 때
- 현재 Chrome이 몇 번 포트를 점유하고 있는지 매번 파악하기 어려울 때

## 스트리밍 (브라우저 미리보기)

인간 관찰자가 실시간으로 AI의 작업을 바라보거나 중간에 공동 작업(pair-browsing)으로 참견할 수 있게 브라우저 뷰포트 화면을 WebSocket으로 외부에 뿌려줍니다.

### 스트리밍 제어

모든 브라우저 세션은 시동 시 임의의 포트로 WebSocket 스트림 서버를 자동 실행합니다. `stream status`를 호출해 현재 점유된 포트 번호와 연결 상태를 확인할 수 있습니다:

```bash
agent-browser stream status
```

고정된 특정 포트를 지정하여 시동하려면 `AGENT_BROWSER_STREAM_PORT`를 세팅하십시오:

```bash
AGENT_BROWSER_STREAM_PORT=9223 agent-browser open example.com
```

런타임 작동 중에 스트림 전송의 개시와 중단은 `stream enable`, `stream disable`, `stream status` 하위 명령어로 통제할 수 있습니다:

```bash
agent-browser stream enable --port 9223   # 해당 포트로 재개방
agent-browser stream disable              # 현재 세션의 스트림 방출 완전 종료
```

개방된 WebSocket 서버는 화면 프레임을 보내주며 가상 입력 키스트로크도 수신받아 브라우저로 반영합니다.

### WebSocket 프로토콜

`ws://localhost:9223` 주소로 접속해 비디오 프레임을 공급받거나 장치 동작 신호를 전달할 수 있습니다:

**수신 프레임 포맷:**

```json
{
  "type": "frame",
  "data": "<base64로 인코딩된 JPEG 이미지 데이터>",
  "metadata": {
    "deviceWidth": 1280,
    "deviceHeight": 720,
    "pageScaleFactor": 1,
    "offsetTop": 0,
    "scrollOffsetX": 0,
    "scrollOffsetY": 0
  }
}
```

**마우스 신호 전송 포맷:**

```json
{
  "type": "input_mouse",
  "eventType": "mousePressed",
  "x": 100,
  "y": 200,
  "button": "left",
  "clickCount": 1
}
```

**기보드 신호 전송 포맷:**

```json
{
  "type": "input_keyboard",
  "eventType": "keyDown",
  "key": "Enter",
  "code": "Enter"
}
```

**터치 신호 전송 포맷:**

```json
{
  "type": "input_touch",
  "eventType": "touchStart",
  "touchPoints": [{ "x": 100, "y": 200 }]
}
```

## 아키텍처

agent-browser는 클라이언트-데몬(Client-Daemon) 구조로 설계되었습니다:

1. **Rust CLI** - 사용자의 명령어를 해석하여 로컬 데몬과 통신
2. **Rust Daemon** - 별도의 Node.js 런타임 없이 CDP로 다이렉트 통신하는 순수 Rust 데몬

데몬은 최초 명령어 입력 시에 스스로 자동 구동되며, 연속적인 조작 명령을 빠르게 처리하기 위해 백그라운드에 계속 상주합니다. 일정 시간 동안 명령이 유입되지 않으면 스스로 브라우저를 닫고 자원을 반납하도록 설정하려면 `AGENT_BROWSER_IDLE_TIMEOUT_MS` 환경 변수에 시간(밀리초)을 입력하십시오.

**기본 브라우저 엔진:** 구글의 Chrome for Testing 버전을 활용합니다. `--engine` 설정을 넘겨서 `chrome` 혹은 초경량 `lightpanda` 엔진 중 하나로 교체할 수 있습니다. 지원 브라우저 계열: Chromium/Chrome (CDP 연동) 및 Safari (iOS 모바일 테스트용 WebDriver 연동).

## 지원 플랫폼

| 운영체제 및 아키텍처 | 바이너리 형태 |
|---|---|
| macOS ARM64 | 네이티브 Rust 빌드 |
| macOS x64 | 네이티브 Rust 빌드 |
| Linux ARM64 | 네이티브 Rust 빌드 |
| Linux x64 | 네이티브 Rust 빌드 |
| Windows x64 | 네이티브 Rust 빌드 |

## AI 에이전트와 함께 사용

### 에이전트에 가벼운 지침 주기

가장 단순한 통합 방법은 사용 중인 코딩 에이전트에 브라우저 도구가 있음을 명시하고 활용하도록 요구하는 것입니다:

```
agent-browser를 사용하여 로그인 워크플로우를 테스트해줘. 실행 가능한 전체 명령어 구조를 파악하려면 agent-browser --help 명령어를 돌려봐.
```

`--help` 도움말은 매우 상세하게 정비되어 있어 대부분의 에이전트는 도움말 출력을 읽고 스스로 기능을 이해합니다.

### AI 코딩 어시스턴트용 전용 스킬 등록 (권장)

어시스턴트 도구에 풍성한 컨텍스트와 사용법 규격을 심어주기 위해 스킬 저장소 라이브러리를 설치해 줍니다:

```bash
npx skills add vercel-labs/agent-browser
```

이 연동은 Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, Goose, OpenCode, Windsurf 등 다양한 코딩 도구와 호환됩니다. 스킬 명세는 원격지 저장소에서 직접 긁어오므로 도구 업데이트 상황이 자동으로 즉시 동기화됩니다. `node_modules` 아래에 생겨난 `SKILL.md` 파일을 수동으로 프로젝트에 카피해 두지 마십시오. 버전 파편화로 인해 기능이 작동하지 않을 수 있습니다.

### Claude Code

Claude Code 전용 스킬로 임베딩하려면 다음을 실행하세요:

```bash
npx skills add vercel-labs/agent-browser
```

이 명령은 `.claude/skills/agent-browser/SKILL.md` 경로에 얇은 스텁(stub) 파일을 설치합니다. 스텁은 의도적으로 최소한의 코드로 구현되어 있으며, 런타임에 Claude Code가 `agent-browser skills get core` 명령을 발동하여 실제 지침서 세부 내용을 꺼내 오도록 경로를 알려줍니다. 이 방식으로 동작 규칙을 관리하면 버전 업데이트에 기민하게 대응할 수 있어 버전 불일치 문제가 발생하지 않습니다.

### AGENTS.md / CLAUDE.md

더 안정적인 작동 유도를 위해 프로젝트 최상위나 전역으로 관리 중인 지침 가이드 파일에 아래 마크다운 서식을 심어두는 것을 권장합니다:

```markdown
## 브라우저 자동화 (Browser Automation)

웹 페이지 자동 통제가 필요할 경우 `agent-browser` 도구를 활용하십시오. 지원되는 전체 작동 커맨드는 `agent-browser --help`로 파악할 수 있습니다.

기본 워크플로우:

1. `agent-browser open <url>` - 지정 페이지 탐색
2. `agent-browser snapshot -i` - 대화형 상호작용 지점을 참조값(ref=@e1, @e2)과 함께 수집
3. `agent-browser click @e1` / `fill @e2 "입력값"` - 참조값을 겨냥해 목표 버튼이나 입력란 통제
4. 화면 내용이나 주소가 갱신되었다면 다시 `snapshot`을 따서 새로운 레이아웃 참조값 목록 갱신
```

## 통합 (Integrations)

### iOS Simulator

실제 모바일 환경에 근접한 테스트를 지원하기 위해 iOS 시뮬레이터 상의 실제 Mobile Safari 브라우저를 통제합니다. Xcode가 구성되어 있는 macOS 컴퓨터가 필요합니다.

**사전 환경 세팅:**

```bash
# Appium 및 XCUITest 드라이버 설치
npm install -g appium
appium driver install xcuitest
```

**사용법:**

```bash
# 구동할 수 있는 iOS 가상 장치 목록 출력
agent-browser device list

# 특정 기기를 선택하여 가상 기기 속 Safari 가동
agent-browser -p ios --device "iPhone 16 Pro" open https://example.com

# 제어 명령어 계열은 데스크톱 크롬 상태와 완전히 같습니다
agent-browser -p ios snapshot -i
agent-browser -p ios tap @e1
agent-browser -p ios fill @e2 "text"
agent-browser -p ios screenshot mobile.png

# 모바일 장치 전용 조작 커맨드
agent-browser -p ios swipe up
agent-browser -p ios swipe down 500

# 모바일 세션 닫기
agent-browser -p ios close
```

또는 환경 변수를 활용해 CLI 고정 옵션으로 설정할 수 있습니다:

```bash
export AGENT_BROWSER_PROVIDER=ios
export AGENT_BROWSER_IOS_DEVICE="iPhone 16 Pro"
agent-browser open https://example.com
```

| 변수 | 설명 |
|---|---|
| `AGENT_BROWSER_PROVIDER` | `ios` 값으로 지정하여 모바일 타게팅 활성화 |
| `AGENT_BROWSER_IOS_DEVICE` | 대상 기기 명칭 (예: "iPhone 16 Pro", "iPad Pro" 등) |
| `AGENT_BROWSER_IOS_UDID` | 기기 고유식별자 UDID (기기명 대신 지정하여 정밀 지목 가능) |

**지원 대상 기기:** Xcode 내에 추가 정의되어 사용 가능한 모든 iOS 시뮬레이터(iPhones, iPads)와 USB로 연결된 실제 iOS 기기.

**참고:** iOS 제공업체 모듈은 시뮬레이터를 부팅하고 Appium을 구동한 뒤 Safari를 가로채 통제합니다. 시뮬레이터 최초 시동에는 약 30~60초가 소요되며, 시동이 완료된 후 후속 명령어부터는 매우 빠르게 작동합니다.

#### 실제 물리 iOS 기기 연동법

USB 케이블로 Mac 컴퓨터에 꽂아둔 실제 아이폰이나 아이패드 통제도 지원합니다. 이를 위해서는 1회성 초기화 설정 과정이 필요합니다:

**1. 컴퓨터와 연결된 iOS 기기의 UDID 구하기:**

```bash
xcrun xctrace list devices
# 혹은
system_profiler SPUSBDataType | grep -A 5 "iPhone\|iPad"
```

**2. WebDriverAgent 코드 서명(Signing) 처리 (최초 1회):**

```bash
# WebDriverAgent Xcode 프로젝트 디렉토리로 이동
cd ~/.appium/node_modules/appium-xcuitest-driver/node_modules/appium-webdriveragent
open WebDriverAgent.xcodeproj
```

Xcode 프로그램 창이 열리면:

- 프로젝트 목록에서 `WebDriverAgentRunner` 타겟 선택
- Signing & Capabilities 설정 탭으로 진입
- 본인의 개발용 Apple Team 계정 연결 (무료 개발자 등급 계정도 가능)
- "Automatically manage signing" 항목 체크를 허용하여 Xcode가 인증 빌드 인증서를 자동 수립하게 함

**3. agent-browser 기동:**

```bash
# 기기를 USB로 연동한 뒤 명령어 주입:
agent-browser -p ios --device "<구한_DEVICE_UDID>" open https://example.com

# 등록 기기 명칭이 고유하다면 기기명 지정도 가능
agent-browser -p ios --device "홍길동의 iPhone" open https://example.com
```

**실제 기기 연동 시 참고 사항:**

- 첫 시동 시점에 WebDriverAgent 헬퍼 앱이 물리 기기에 강제 인스톨됩니다. (기기 화면에 '신뢰할 수 없는 개발자' 팝업이 뜨면 설정 앱에서 프로필을 신뢰해 주어야 함)
- 기기 화면이 항시 잠금 해제되어 있어야 하며 USB 물리 링크가 견고해야 함
- 시뮬레이터 모드에 비해 초기 채널 터널을 확보하는 링크 업 타임이 소폭 더 깁니다.
- 가상이 아닌 실물 기기 수준의 하드웨어 메모리 작동 및 Safari 렌더링 검사 가능

### Browserless

[Browserless](https://browserless.io)는 일회성 원격 세션 제어 API가 결합된 퍼블릭 브라우저 인프라스트럭처를 공급합니다. 도커 등 호스트 운영체제 사정으로 로컬 크롬을 구동하기 곤란한 CI 파이프라인에서 맹활약합니다.

포트나 데몬을 무시하고 원격 Browserless를 태우려면 `-p` 옵션을 지정합니다:

```bash
export BROWSERLESS_API_KEY="본인의_API_토큰"
agent-browser -p browserless open https://example.com
```

스크립팅을 돌릴 때 고정 환경 변수로 지정하려면:

```bash
export AGENT_BROWSER_PROVIDER=browserless
export BROWSERLESS_API_KEY="본인의_API_토큰"
agent-browser open https://example.com
```

사용 가능한 부가 제어용 환경 변수 옵션:

| 변수 | 설명 | 기본값 |
|---|---|---|
| `BROWSERLESS_API_URL` | 접속할 API 서버 경로 (별도 지리 영역이나 셀프 호스팅 용도) | `https://production-sfo.browserless.io` |
| `BROWSERLESS_BROWSER_TYPE` | 띄울 브라우저 엔진 유형 (chromium 혹은 chrome) | chromium |
| `BROWSERLESS_TTL` | 세션 활동 기한 생존 시간 (밀리초 단위) | `300000` |
| `BROWSERLESS_STEALTH` | 웹 크롤러 차단 우회 스텔스 기법 탑재 여부 | `true` |

활성화되면 로컬 데몬을 대신하여 원격 클라우드 세션 터널로 요청들이 연계되어 나가며, CLI 명령 조작 및 결과 회수 포맷은 로컬 작동 시와 완전히 동일합니다.

연동 토큰 키값은 [Browserless Dashboard](https://browserless.io) 가입 후 발급받을 수 있습니다.

### Browserbase

[Browserbase](https://browserbase.com)는 복잡한 AI 브라우징 에이전트 서비스를 실서비스 규모로 신속하게 올려주는 원격 클라우드 제어 서비스를 제안합니다.

서버 사정으로 브라우저를 로컬 구동하기 어려울 때 사용합니다:

```bash
export BROWSERBASE_API_KEY="본인의_API_키"
agent-browser -p browserbase open https://example.com
```

환경 변수 지정 방식:

```bash
export AGENT_BROWSER_PROVIDER=browserbase
export BROWSERBASE_API_KEY="본인의_API_키"
agent-browser open https://example.com
```

활성화되면 모든 브라우저 렌더링 지점은 Browserbase 프록시가 대리하며, 입출력 조작법은 로컬과 동일합니다.

API 키 발급은 [Browserbase Dashboard](https://browserbase.com/overview)에서 처리 가능합니다.

### Browser Use

[Browser Use](https://browser-use.com)는 AI 에이전트들을 위한 클라우드 브라우징 특화 프레임워크와 기기들을 제공합니다. 서버리스 및 배포 단계 등 격리된 샌드박스에서 돌릴 때 사용합니다.

```bash
export BROWSER_USE_API_KEY="본인의_API_키"
agent-browser -p browseruse open https://example.com
```

환경 변수 지정 방식:

```bash
export AGENT_BROWSER_PROVIDER=browseruse
export BROWSER_USE_API_KEY="본인의_API_키"
agent-browser open https://example.com
```

활성화 시 로컬 실행 파일 대신 Browser Use 클라우드에서 동작이 전개됩니다.

서비스 가입 및 토큰 생성은 [Browser Use Cloud Dashboard](https://cloud.browser-use.com/settings?tab=api-keys)에서 주관하며 가입 시 무료 크레딧을 받을 수 있습니다.

### Kernel

[Kernel](https://www.kernel.sh)은 봇 감지 무력화 스텔스 모드와 반영구적 사용자 프로필 기억 저장 공간이 설계된 AI 타겟 특화 원격 브라우저 플랫폼입니다.

```bash
export KERNEL_API_KEY="본인의_API_키"
agent-browser -p kernel open https://example.com
```

환경 변수 지정 방식:

```bash
export AGENT_BROWSER_PROVIDER=kernel
export KERNEL_API_KEY="본인의_API_키"
agent-browser open https://example.com
```

세부 튜닝용 환경 변수 옵션:

| 변수 | 설명 | 기본값 |
|---|---|---|
| `KERNEL_HEADLESS` | 원격 브라우저의 헤드리스 개방 통제 여부 | `true` |
| `KERNEL_STEALTH` | 크롤러 자동 탐지 필터 우회 기법 가동 여부 | `false` |
| `KERNEL_TIMEOUT_SECONDS` | 세션 생존 한계 기한 시간 (초 단위) | `300` |
| `KERNEL_PROFILE_NAME` | 쿠키나 로그인 상태를 저장 유지할 반영구 프로필 명칭 (없으면 자동 개설) | (지정 안 함) |

활성화하면 모든 통제 흐름은 Kernel 인프라로 수렴됩니다.

**프로필 상태 기억 장치:** `KERNEL_PROFILE_NAME` 변수를 선언해 두면 브라우저가 종료될 때까지 습득한 로그인 쿠키 및 내부 스토리지 정보가 Kernel 저장 백엔드에 안전하게 박제되어 보존됩니다. 따라서 다음번 신규 호출 시 동일 프로필 이름을 가리켜서 로그인 관문을 영속적으로 건너뛸 수 있습니다.

토큰 생성은 [Kernel Dashboard](https://dashboard.onkernel.com)에서 신청하십시오.

