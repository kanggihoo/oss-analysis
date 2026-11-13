---
sha: "916a0e1cd5f4a84de4ec7e485386c7d9941d7e00"
created: 2026-11-10
updated: 2026-11-10
sources:
  - plugin.json
  - .claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - .agents/plugins/marketplace.json
  - skills/k-humanizer/agents/openai.yaml
  - skills/k-humanizer-resume/agents/openai.yaml
  - skills/k-humanizer/SKILL.md
  - skills/k-humanizer-resume/SKILL.md
  - README.md
  - CHANGELOG.md
  - .github/workflows/validate.yml
depends:
  - ./response-format.md
status: ready
---

# 스킬 메타데이터·플러그인 배포

> 두 스킬을 Claude Code·Codex 플러그인과 개별 스킬로 설치할 수 있게 하는 메타데이터 파일(frontmatter, `agents/openai.yaml`, 매니페스트 4개)과 설치 명령을 정의한다.

<!-- 이 레포의 "구현"은 메타데이터 파일이다. 파일이 짧고 자기완결적이라 필드 목록은 글로 쓰고 원문은 C-ID로 넘긴다. 호스트(Claude Code·Codex·`npx skills`)가 이 파일을 어떻게 읽는지는 외부 시스템이라 확인하지 못했다(1.4 확인 한계). 검증 수준 `코드 확인` = 파일을 직접 읽음. -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 사용자가 설치 명령을 실행한다: Claude Code(`claude plugin marketplace add …` → `claude plugin install k-humanizer@k-humanizer`), Codex(`codex plugin marketplace add …` → `codex plugin add k-humanizer@k-humanizer`), 그 밖의 에이전트(`npx skills add … --skill <이름> --full-depth`).
2. 마켓플레이스 파일이 레포 루트(`./`)를 `k-humanizer` 플러그인 하나로 등록한다.
3. 플러그인 안의 스킬 두 개(`skills/k-humanizer`, `skills/k-humanizer-resume`)가 호스트에 노출된다.
4. 호스트는 각 `SKILL.md`의 `name`·`description`과 `agents/openai.yaml`의 표시 정보·기본 프롬프트·암묵 호출 허용 정책으로 스킬을 보여 주고 호출 여부를 정한다.

### 1.2 범위·통합 지점
- 제공: 파일별 필드 정의, 설치 명령, 파일 간 일관성 규칙, CI에서 검사되는 범위.
- 제외: 플러그인 로더·`npx skills`·호스트가 이 파일들을 실제로 어떻게 읽는지(외부 시스템), 스킬 본문의 규칙([response-format](./response-format.md)의 라우팅 포함).
- 외부 의존·선행 계약: 스킬 이름과 `description`(S4, [response-format](./response-format.md) C-03·C-04). Claude Code·Codex 플러그인 시스템과 `npx skills` CLI는 외부다.
- 소유 상태·부작용: 없음(정적 파일). 설치는 호스트가 한다.

### 1.3 인터페이스와 데이터 의미
| 파일 | 주요 필드 | 의미·제약 |
|---|---|---|
| `skills/<스킬>/SKILL.md` frontmatter | `name`, `description` | `name`은 `k-humanizer`, `k-humanizer-resume`(디렉터리 이름과 같음). `description`은 다루는 작업과 제외·위임 대상을 말해 호출 판단에 쓰인다 |
| `skills/<스킬>/agents/openai.yaml` | `interface.display_name`, `interface.short_description`, `interface.default_prompt`, `policy.allow_implicit_invocation` | 표시 이름 `K-Humanizer`·`K-Humanizer Resume`, 한 줄 설명(영어), 기본 프롬프트는 `Use $k-humanizer …` / `Use $k-humanizer-resume …` 형식이며 금액·날짜·정책·이름·플레이스홀더를 유지하라는 지시를 담는다. 두 스킬 모두 암묵 호출 허용(`true`) |
| `.claude-plugin/marketplace.json` | `name: "k-humanizer"`, `description`, `owner.name`, `plugins[]`(`name`, `source: "./"`, `description`) | 마켓플레이스 이름과 플러그인 이름이 모두 `k-humanizer`라서 설치 명령이 `k-humanizer@k-humanizer`가 된다 |
| `.claude-plugin/plugin.json` | `name`, `displayName`, `description`, `author`, `homepage`, `repository`, `license: "MIT"`, `keywords` | `version` 필드가 없다 |
| `.agents/plugins/marketplace.json` | `name`, `interface.displayName`, `plugins[]`(`name`, `source.source: "local"`, `source.path: "./"`, `policy.installation: "AVAILABLE"`, `policy.authentication: "ON_INSTALL"`, `category: "Productivity"`) | Codex용 마켓플레이스. 플러그인 소스는 로컬 루트 |
| `plugin.json` (루트) | `$schema`(agent-plugins 1.0.0), `name`, `version: "0.5.0"`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `extensions."com.openai".interface`(`displayName`, `shortDescription`, `longDescription`, `developerName`, `category`, `defaultPrompt`[2개: 번역 프롬프트 하나, 이력서 프롬프트 하나], `websiteURL`) | 매니페스트 중 버전이 있는 유일한 파일. `longDescription`이 두 스킬을 모두 설명한다 |

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | Claude Code에서 설치 | `.claude-plugin/marketplace.json`이 마켓플레이스 `k-humanizer`에 플러그인 `k-humanizer`(소스 레포 루트)를 등록한다. 명령은 `claude plugin marketplace add evergreentree97/K-Humanizer`, `claude plugin install k-humanizer@k-humanizer` | 코드 확인 (파일·README), 호스트 동작은 미확인 |
| R-02 | Codex에서 설치 | `.agents/plugins/marketplace.json`이 같은 이름의 플러그인을 로컬 소스 `./`, 설치 `AVAILABLE`, 인증 `ON_INSTALL`, 분류 `Productivity`로 등록한다. 명령은 `codex plugin marketplace add evergreentree97/K-Humanizer`, `codex plugin add k-humanizer@k-humanizer` | 코드 확인 (파일·README), 호스트 동작은 미확인 |
| R-03 | 플러그인이 노출하는 스킬 | 어느 매니페스트도 스킬 경로를 나열하지 않는다. README는 플러그인으로 두 스킬을 함께 설치한다고 쓰므로, 호스트가 `skills/` 아래 디렉터리를 자동으로 찾는다고 읽어야 한다 | 추론 |
| R-04 | 스킬 호출 메타데이터 | 각 스킬의 `SKILL.md` frontmatter(`name`, `description`)가 스킬을 식별·설명하고, `agents/openai.yaml`이 표시 정보와 기본 프롬프트를 주며 `allow_implicit_invocation: true`로 사용자가 이름을 말하지 않아도 호출될 수 있게 한다 | 코드 확인 (파일), 호출 판단은 호스트 |
| R-05 | 그 밖의 에이전트(Cursor 등)에서 설치 | `npx skills add evergreentree97/K-Humanizer --skill k-humanizer --full-depth`, 이력서 스킬은 `--skill k-humanizer-resume`로 각각 설치한다 | 코드 확인 (README), CLI 동작은 미확인 |
| R-06 | 웹 채팅·API | 링크만 주면 모델이 파일을 읽지 못할 수 있으므로 `SKILL.md`와 필요한 참조 파일(비즈니스 한국어, 한국어 글쓰기 사례 등)의 텍스트를 직접 붙여 넣는다. 결과는 모델·설정에 따라 다르다 | 코드 확인 (README) |
| R-07 | 매니페스트 간 공통 필드 | `name: k-humanizer`, 작성자 이름 `evergreen_ricky`와 URL, `homepage`, `repository`, `license: MIT`, `keywords`가 `.claude-plugin/plugin.json`과 루트 `plugin.json`에서 같다 | 코드 확인 |
| R-08 | CI | `validate.yml`은 `.github/**/*.yml`과 `skills/**/*.yaml`만 YAML로 파싱한다. JSON 매니페스트 4개는 CI가 검사하지 않는다 | 코드 확인 |

- 불변식: 설치 명령의 `k-humanizer@k-humanizer`는 마켓플레이스 이름과 플러그인 이름이 같다는 사실에 의존한다(R-01, R-02).
- 미결정: 없음.
- 확인 한계: 파일 내용과 README의 명령은 직접 읽었다. Claude Code·Codex·`npx skills`가 이 파일을 실제로 어떻게 읽고 스킬을 노출하는지, 설치가 되는지는 확인하지 않았다(외부 시스템, 실행하지 않음). R-03은 구조에서 한 추론이다.

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `.claude-plugin/marketplace.json:1-14` | Claude Code 마켓플레이스 전문 | R-01 |
| C-02 | `.claude-plugin/plugin.json:1-13` | Claude Code 플러그인 메타데이터 전문 | R-01, R-07 |
| C-03 | `.agents/plugins/marketplace.json:1-20` | Codex 마켓플레이스 전문 | R-02 |
| C-04 | `plugin.json:1-30` | 루트 플러그인 정의(`version`, `extensions."com.openai".interface`) 전문 | R-04, R-07 |
| C-05 | `skills/k-humanizer/agents/openai.yaml:1-7`, `skills/k-humanizer-resume/agents/openai.yaml:1-7` | 표시 정보·기본 프롬프트·정책 | R-04 |
| C-06 | `skills/k-humanizer/SKILL.md:1-4`, `skills/k-humanizer-resume/SKILL.md:1-4` | frontmatter `name`·`description` | R-04 |
| C-07 | `README.md:40-72` | 설치 명령 4개와 웹·API 사용 안내 | R-01, R-02, R-05, R-06 |
| C-08 | `.github/workflows/validate.yml:33-37` | YAML 검사 단계(검사 범위) | R-08 |

### 1.6 수락 사례
출처: 구현에서 도출(파일 내용에서 확인되는 일관성).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `marketplace.json`의 `name`과 `plugins[0].name`을 비교 | 둘 다 `k-humanizer`. 설치 명령이 `k-humanizer@k-humanizer` |
| T-02 | R-07 | 두 매니페스트의 `author.name`, `homepage`, `repository`, `license`, `keywords`를 비교 | 모두 같다 |
| T-03 | R-04 | 두 `openai.yaml`의 `policy.allow_implicit_invocation` | 둘 다 `true` |
| T-04 | R-04, R-06 | 루트 `plugin.json`의 `defaultPrompt` 두 개와 `openai.yaml`의 `default_prompt` | `plugin.json`은 번역 프롬프트와 이력서 프롬프트 한 개씩. `openai.yaml`은 스킬마다 `$<스킬 이름>`으로 시작하는 프롬프트 하나씩 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@916a0e1) | 확인 방법·한계 |
|---|---|---|
| R-01 | `.claude-plugin/marketplace.json:1-14`, `README.md:45-49` | 직접 읽음 |
| R-02 | `.agents/plugins/marketplace.json:1-20`, `README.md:52-56` | 직접 읽음 |
| R-03 | `plugin.json:1-30`, 마켓플레이스 2개, `README.md:42` | 어느 파일에도 스킬 경로 필드가 없음을 확인하고 자동 탐색으로 추론 |
| R-04 | `skills/*/agents/openai.yaml:1-7`, `skills/*/SKILL.md:1-4` | 직접 읽음 |
| R-05, R-06 | `README.md:58-72` | 직접 읽음. `README.en.md`는 같은 명령을 쓴다(`README.en.md:48-68`에서 `grep`으로 확인, 본문은 열지 않음) |
| R-07 | `.claude-plugin/plugin.json:5-12`, `plugin.json:6-13` | 필드를 대조 |
| R-08 | `.github/workflows/validate.yml:33-37` | 직접 읽음 |
| T-01~T-04 | 위 근거의 적용 | 구현에서 도출 |
| 문서 차이 | `plugin.json:5`, `.claude-plugin/plugin.json:4`, `CHANGELOG.md:8-10`, 태그 `v0.5.0` | **차이 3건**. (1) 설명 문장이 매니페스트마다 다르다: 루트 `plugin.json`의 `description`은 이력서 스킬을 언급하지 않고(`longDescription`만 언급), `.claude-plugin/plugin.json`과 두 마켓플레이스는 이력서 스킬을 언급한다. (2) 버전은 루트 `plugin.json`에만 `0.5.0`으로 있고 `.claude-plugin/plugin.json`에는 없다. 플러그인 패키징은 `CHANGELOG.md`의 "Unreleased"에 있는데 `plugin.json`은 마지막 릴리스 태그와 같은 `0.5.0`이다. (3) CI는 JSON 매니페스트를 검사하지 않는다(R-08) |

### 2.2 코드 읽는 순서
README 설치 절(`:40-72`) → 마켓플레이스 2개 → 루트 `plugin.json` → `openai.yaml` 2개 → 각 `SKILL.md` frontmatter.

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| — | 없음 | — | — |
