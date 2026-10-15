# REA (Reverse Engineer Anything) Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/morluto/rea`
- **분석 Commit SHA**: `60c08802a7b6d2195121114a9e4224492f138185`
- **분석 일자**: `2026-10-14`
- **작업트리 상태**: `Clean`
- **분석 목적**: 학습 (MCP 서버 / Evidence 기반 도구 설계 이해)
- **패키지**: `rea-agents` 6.4.0, TypeScript, MIT, Node >=22.19 (코드 확인: `package.json`)
- **범위**: 빌드·실행 없이 README, `AGENTS.md`, `docs/`, 일부 `src/`만 읽은 1차 분석

검증 수준 표기: **코드 확인** / **문서 확인**(README·docs 기준, 코드 미대조) / **추론** / **미확인**

---

## 2. 프로젝트 개요

REA는 **에이전트가 리버스 엔지니어링을 하도록 연결해 주는 로컬 도구 모음**이다. 새 분석 알고리즘 하나가 아니라, 두 가지를 합친 것이다.

1. **기존 도구를 감싸는 어댑터**: Hopper, Ghidra, IDA(네이티브), JADX(APK), objdump, Rizin, WABT(WASM), tshark(pcap), Binwalk(펌웨어) 등을 브리지·프로세스 호출로 조작한다. 이 도구들은 사용자가 직접 설치해야 한다(BYO). (문서 확인: README, `AGENTS.md`, `docs/architecture.mermaid`)
2. **자체 구현 분석기**: JS/Electron(AST 기반 모듈·IPC 그래프), .NET 메타데이터·CIL, Go/Rust 바이너리 메타데이터, source map, SQLite 등은 외부 엔진 없이 동작한다. (문서 확인: README 표. `src/domain/javascript/`에 파일 약 200개로 규모는 코드 확인)

그 위에 **Evidence 모델**이 얹힌다. 결과를 관찰 / 파생 / 추론 / 미확인으로 구분하고 출처(provenance)를 붙여 서버가 보관한다. (문서 확인: `AGENTS.md`. `src/domain/evidence.ts` 내용은 미확인)

REA 자체의 역할은 "읽고 근거를 돌려주는 것"이고, 결과를 해석해 설명하거나 코드를 쓰는 일은 REA를 호출하는 에이전트(Claude 등)의 모델이 한다.

### 라이선스·의존 도구 (일반 지식, 코드 확인 아님)

| 도구 | 오픈소스 | 비고 |
|---|---|---|
| Ghidra | 예 (Apache 2.0, NSA 공개) | 무료 |
| IDA | 아니요 (Hex-Rays 상용) | 제한된 무료판 있음 |
| Hopper | 아니요 (상용) | demo 모드 또는 라이선스 활성화 (문서 확인: README FAQ) |

---

## 3. 시작점: CLI와 MCP

- 사용자 진입점은 `scripts/rea.mjs` 하나이고, `package.json`의 `bin`(`rea`, `rea-agents`)이 이 파일을 가리킨다. (코드 확인)
- 인자가 `mcp`/`--mcp`면 `dist/mcp/main.js`(소스 `src/main.ts`)를, 그 외 명령은 `dist/cli-runtime/cli.js`(소스 `src/cli.ts`)를 로드한다. 컴파일된 `dist/`가 없으면 `npm ci && npm run build:cached` 안내 후 종료한다. (코드 확인)
- 두 경로는 같은 `src/application/` workflow를 공유한다. (문서 확인: README·`AGENTS.md`. 서비스 함수에 MCP/CLI 의존이 없는 것은 코드 확인, CLI 쪽 호출 지점 `src/cli/javascriptApplicationAnalysis.ts`는 내용 미확인)

### CLI와 MCP를 둘 다 두는 이유

둘은 **택일**이다. 에이전트로 쓰면 MCP만, 사람이 터미널·스크립트로 쓰면 CLI만 쓴다.

| 구분 | CLI | MCP |
|---|---|---|
| 프로세스 | 명령 하나 실행 후 종료 (one-shot) | 에이전트가 띄워 두는 장시간 stdio 서버 |
| 상태 | 종료하면 메모리 상태 소멸 | `src/main.ts`가 `BinarySession`을 프로세스 수명 동안 보유 (코드 확인) |
| 결과 전달 | stdout/JSON | Evidence를 서버가 보관, 에이전트는 `evidence_id`로 요약·부분·페이지 조회 (코드 확인: `src/contracts/promptContracts.ts`) |
| 호출 방식 | 셸 문자열 | 타입 있는 tool 스키마 (추론: 에이전트 친화) |

따라서 한 번짜리 분석은 둘이 같지만, 바이너리를 열어 둔 세션 재사용과 큰 결과의 부분 조회는 MCP의 장점이다. CLI의 snapshot 기능이 이를 어디까지 상쇄하는지는 미확인.

---

## 4. 분석 대상 범위

README 표 기준(문서 확인). 대상마다 필요한 외부 도구와 지원 OS가 다르고, Linux 전용·x64 전용 기능이 많다.

| 분류 | 대상 | 비고 |
|---|---|---|
| 데스크탑·실행 파일 | 네이티브 바이너리, macOS 앱 번들, Electron, .NET, Go/Rust | 프로세스 관찰, Frida 문서도 존재 (Frida는 파일명만 확인) |
| 웹 | 웹사이트(CDP), HAR/SAZ 캡처, pcap | 아래 "웹 분석 방식" 참고 |
| 모바일 | Android APK, 리소스(Apktool), Flutter, adb 기기, JEB | iOS 전용 행은 표에 없음 (미확인) |
| 기타 | 펌웨어, WASM, EVM 바이트코드, SQLite, 크래시 덤프 | |

### 웹 분석 방식 (문서 확인: `docs/browser-observation.md`)

- 사용자가 쓰는 Chrome 계열 브라우저에 CDP로 붙어 **이미 열린 페이지를 수동적으로 관찰**한다. 일반 브라우저 자동화나 원격 조종이 아니라고 문서가 명시한다.
- 수집: DOM, 접근성 노드, 스크립트, 리소스, 네트워크·콘솔 메타데이터, WebSocket 프레임 크기, 선택적으로 스크립트 소스.
- `analyze_web_bundle`은 수집한 스크립트를 실행하지 않고 파싱해 chunk 관계, route·endpoint 후보, vendor 지문을 뽑는다.
- "로컬"은 분석 프로그램이 내 컴퓨터에서 돈다는 뜻이다. 대상 사이트가 로컬에 있어야 한다는 뜻이 아니다. 데이터를 REA가 외부로 올리지는 않지만 결과는 에이전트(모델 제공자)에게 전달된다. (문서 확인: README FAQ)
- 서버 공격이나 원격 스캔 도구가 아니다. (문서 확인: `AGENTS.md` "local-only")

---

## 5. "되돌린다"의 의미

### Electron / JS (일반 지식 + 문서 확인)

- Electron 앱 코드는 보통 `app.asar`(압축·암호화 없는 아카이브) 또는 풀린 `app/` 폴더에 들어 있고, webpack·esbuild로 합쳐지고 minify된 JS다. 소스는 남아 있으나 읽기 어렵다.
- REA가 돌려주는 것은 원본 소스가 아니라 **구조 지도**다: 모듈, import, source map, route, IPC, 네이티브 add-on 관계. (문서 확인: README 표, `architecture.mermaid`의 "AST-only bundle projection")
- source map이 있으면 원래 파일 구조 복원에 쓰인다. (`src/javascript/sourceMaps/` 존재 확인, 동작 세부는 미확인)
- 정확한 복원 범위는 `docs/javascript-recovery.md`, `javascript-artifact-reconstruction.md`를 읽어야 안다. (미확인)

### 네이티브 바이너리 (일반 지식)

- 컴파일은 변수명, 주석, 타입 이름, 구조 정보를 버린다. 컴파일러 종류를 알아도 버려진 정보는 계산으로 복원되지 않는다.
- 도구가 할 수 있는 것: 디스어셈블(기계어 → 어셈블리), 디컴파일(어셈블리 → C 비슷한 의사코드, 변수명은 `local_18` 같은 임의 이름), 호출·문자열 참조 추적. 심볼이 남은 빌드는 훨씬 읽기 쉽고 stripped 빌드는 이름이 없다.
- 컴파일러 패턴은 디컴파일러가 구조를 추정하는 데 쓰인다. Go/Rust는 바이너리에 메타데이터(컴파일러 버전, 모듈, crate)가 남는다. (문서 확인: README 표)

### 사실과 추론의 구분

- 도구가 뽑은 의사코드, 호출 관계, 문자열, import, IPC 채널은 **관찰·파생 사실**이다.
- "이 함수는 라이선스 검사로 보인다" 같은 의미 해석은 AI의 **추론**이다.
- REA가 Evidence에서 둘을 구분해 표시하는 것은 AI 결론을 어디까지 믿을지 따지기 위해서다. (문서 확인. 구현은 미확인)

---

## 6. 에이전트와의 역할 분담

1. 사용자가 에이전트에게 분석 또는 구현을 요청한다.
2. 에이전트가 REA를 호출한다 (MCP 또는 CLI).
3. REA가 Evidence를 돌려주고 에이전트가 의미를 추론한다.
4. 부족하면 REA를 다시 호출해 깊게 파고든다.
5. 이해가 끝나면 에이전트가 코드를 쓰고 테스트한다. 이 단계에서 REA는 개입하지 않는다.

REA는 3번까지를 담당한다. 최종 산출물은 요청에 따라 설명(분석만) 또는 구현 코드(README 첫 예시)다. README는 DX-Ball 사례에서 의사코드를 C로 다시 쓰고 원본 x86 케이스 3,205개를 통과시켰다고 하나 재현하지 않았다. (문서 확인만)

`npx rea-agents setup`은 MCP 등록과 함께 `.agents/skills/reverse-engineer-anything/` 스킬(조사 방법을 알려 주는 지침서)을 설치한다. 도구 실행은 MCP tool이 하고, 스킬은 그 위의 안내 역할이다. (문서 확인)

---

## 7. 아키텍처 (코드 구조)

`AGENTS.md`의 의존 방향 규칙: domain/contracts → provider adapter → application workflow → CLI/MCP adapter. (문서 확인)

### 대표 흐름: MCP `analyze_javascript_application` (코드 확인)

`src/application/javascript/JavaScriptApplicationService.ts`의 `analyzeJavaScriptApplication`:

1. zod `strictObject` 스키마로 입력 검증
2. `reconstructJavaScriptArtifact`로 파일 inventory·파싱 후 그래프와 `electron_summary` 생성
3. `parseOwnedJavaScriptApplicationAnalysisSteps`로 결과와 교차 바인딩 검증
4. 결과를 해시한 Evidence로 생성
5. 취소(`ArtifactReaderFailure` reason `cancelled`) 시 부분 결과를 Evidence로 만들어 오류에 `retainPartialObservation`으로 첨부

도구 등록은 `src/server/registerElectronTools.ts`(`toolContract("analyze_javascript_application")` 바인딩)에서 한다. `runElectronTool` 내부와 `reconstructJavaScriptArtifact` 내부는 미확인.

### 다이어그램

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 진입점 → composition → server/application → provider → process/domain |
| 대표 실행 흐름 | [flow.json](./diagrams/flow.json) | [flow.html](./diagrams/flow.html) | MCP `analyze_javascript_application` 호출 |

- archify `deliver`는 두 장 모두 통과했다. 브라우저 `visual-check`와 눈으로 하는 검토는 하지 않았다.
- 구조도의 화살표 대부분은 `docs/architecture.mermaid`를 따른 것이고 import 단위 검증은 하지 않았다. (문서 확인 수준)

---

## 8. 미확인 영역과 후속 질문

- [Q1] Evidence 모델(`src/domain/evidence.ts`)은 관찰·파생·추론·미확인을 어떻게 표현하는가
- [Q2] `BinarySession` + `AnalysisProviderRegistry`는 "deep provider 하나, fallback 없음"을 어떻게 강제하는가
- [Q3] `src/process/`의 프로세스 소유·정리 규칙을 provider들이 어떻게 재사용하는가
- [Q4] contracts(`toolContract`)와 handler 바인딩, MCP tool 노출 범위
- [Q5] 취소 시 부분 Evidence 보존 패턴이 다른 workflow에도 일관된가
- CLI의 snapshot 기능과 MCP 세션의 실제 차이, iOS 지원 여부, JS 복원의 정확한 범위

## 9. 연계 링크

- 다음 세션 계획: [next.md](./next.md)
- 위키: [wiki/projects/rea.md](../../wiki/projects/rea.md)
