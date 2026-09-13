---
type: deepwiki-translation
repo: ponytail
source: artifacts/ponytail/deepwiki/pages-md/7-maintenance-and-tooling.md
deepwiki_url: https://deepwiki.com/DietrichGebert/ponytail/7-maintenance-and-tooling
section: "7"
order: 26
---

# 유지보수 및 도구

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성할 때 참고 자료로 사용되었습니다:

- [.agents/rules/ponytail.md](.agents/rules/ponytail.md)
- [.github/FUNDING.yml](.github/FUNDING.yml)
- [.github/workflows/test.yml](.github/workflows/test.yml)
- [.kiro/steering/ponytail.md](.kiro/steering/ponytail.md)
- [benchmarks/behavior.js](benchmarks/behavior.js)
- [benchmarks/behavior.yaml](benchmarks/behavior.yaml)
- [benchmarks/correctness.js](benchmarks/correctness.js)
- [package.json](package.json)
- [scripts/check-rule-copies.js](scripts/check-rule-copies.js)

</details>



이 섹션은 Ponytail의 플랫폼 간 일관성과 신뢰성을 유지하는 데 필요한 개발자용 인프라를 다룹니다. Ponytail은 여러 AI 에이전트(Claude Code, Codex, Cursor, Windsurf 등)에 걸친 분산 규칙 집합으로 동작하므로, 특수한 도구를 통해 핵심 로직이 호스트별 형식 간에 어긋나지 않도록 보장합니다.

## 규칙 동기화

Ponytail은 규칙 배포를 위해 허브 앤 스포크(hub-and-spoke) 모델을 사용합니다. `AGENTS.md`는 규칙 집합의 기준 원본으로 사용되며 [[scripts/check-rule-copies.js:15-16]](), 이후 `.cursor/rules/ponytail.mdc` 및 `.clinerules/ponytail.md` 같은 플랫폼별 파일로 미러링됩니다.

`scripts/check-rule-copies.js` 유틸리티는 이러한 복사본의 검증을 자동화합니다. 이 스크립트는 두 가지 주요 검사를 수행합니다:
1.  **바이트 단위 비교**: 호스트별 frontmatter를 제거하고 규칙 본문을 `AGENTS.md`와 비교합니다 [[scripts/check-rule-copies.js:19-36]]().
2.  **불변성 검증**: `SKILL.md`(런타임 기준 원본)는 compact rule 파일과 구조가 다르므로, 스크립트는 특정 "하중을 받는" 문구가 모든 버전에서 그대로 유지되는지 확인합니다 [[scripts/check-rule-copies.js:43-67]]().

### 규칙 불변식
| 불변 문구 | 목적 |
| :--- | :--- |
| `naive heuristic` | 의도적인 단순화를 위한 "ceiling-comment" 규칙을 보호합니다 [[scripts/check-rule-copies.js:44]](). |
| `ONE runnable check` | "test reflex" 요구 사항이 사라지지 않도록 보장합니다 [[scripts/check-rule-copies.js:45]](). |
| `flimsier algorithm` | "robust-variant" 규칙(lazy != broken)을 보호합니다 [[scripts/check-rule-copies.js:46]](). |
| `input validation at trust boundaries` | 보안 및 데이터 손실 방지 규칙이 확실한 경계로 유지되도록 보장합니다 [[scripts/check-rule-copies.js:51]](). |

동기화 로직과 추적되는 전체 파일 목록은 **[규칙 동기화(check-rule-copies.js)](#7.1)**를 참조하세요.

**출처:** [scripts/check-rule-copies.js:1-75](), [.kiro/steering/ponytail.md:1-30](), [.agents/rules/ponytail.md:1-25]()

---

## 훅 테스트 및 CI

Claude Code와 Codex의 상태 및 모드 전환을 관리하는 Node.js 훅의 무결성은 전용 테스트 스위트로 검증됩니다. `package.json`은 `node --test`를 사용해 테스트 진입점을 정의합니다 [[package.json:8]]().

### 코드 엔티티 관계: 훅 테스트
다음 다이어그램은 테스트 환경 설정과 실제 훅 실행 흐름을 연결해 보여줍니다.

**제목: 훅 실행 및 환경 모킹**
```mermaid
graph TD
    subgraph "Test Runner (hooks.test.js)"
        ["run_helper"] -- "spawns" --> ["child_process.spawnSync"]
        ["env_mocking"] -- "sets" --> ["PONYTAIL_DEFAULT_MODE"]
    end

    subgraph "Hook Scripts"
        ["child_process.spawnSync"] -- "executes" --> ["ponytail-activate.js"]
        ["child_process.spawnSync"] -- "executes" --> ["ponytail-mode-tracker.js"]
    end

    subgraph "State Persistence"
        ["ponytail-activate.js"] -- "writes" --> ["ponytail-active_flag"]
        ["ponytail-mode-tracker.js"] -- "updates" --> ["ponytail-active_flag"]
    end
```

`.github/workflows/test.yml`에 정의된 CI 파이프라인은 모든 push와 pull request가 규칙 동기화와 기능 테스트를 모두 검증하도록 보장합니다 [[.github/workflows/test.yml:9-30]]().

테스트 러너와 환경 변수 모킹에 대한 자세한 내용은 **[훅 테스트 및 CI](#7.2)**를 참조하세요.

**출처:** [package.json:1-15](), [.github/workflows/test.yml:1-30]()

---

## 마켓플레이스 및 플러그인 매니페스트

여러 에이전트 생태계에서 발견과 설치를 지원하기 위해, Ponytail은 여러 개의 매니페스트 파일을 유지합니다. 이 파일들은 플러그인의 식별자, 소유자, 각 마켓플레이스용 진입점을 정의합니다.

### 매니페스트 배포
| 파일 경로 | 대상 플랫폼 | 역할 |
| :--- | :--- | :--- |
| `.claude-plugin/marketplace.json` | Claude Code | 이름, 설명, 생산성 카테고리를 정의합니다. |
| `package.json` | Pi Agent | `pi-extension/index.js`와 `skills/` 디렉터리를 등록합니다 [[package.json:10-13]](). |
| `.github/plugin/plugin.json` | Copilot | GitHub Copilot Extensions용 매니페스트입니다. |

### 코드 엔티티 관계: 플러그인 등록
이 다이어그램은 매니페스트를 통해 자연어 설명이 기본 코드와 어떻게 연결되는지 보여줍니다.

**제목: 매니페스트에서 코드로의 매핑**
```mermaid
graph LR
    subgraph "Marketplace Manifests"
        ["package.json"] -- "defines" --> ["pi_property"]
        ["marketplace.json"] -- "configures" --> ["claude_plugin"]
    end

    subgraph "Code Entities"
        ["pi_property"] -- "points_to" --> ["pi-extension/index.js"]
        ["pi_property"] -- "points_to" --> ["skills_directory"]
        ["claude_plugin"] -- "triggers" --> ["ponytail-activate.js"]
    end

    subgraph "Skill Implementation"
        ["skills_directory"] -- "contains" --> ["SKILL.md"]
        ["SKILL.md"] -- "referenced_by" --> ["check-rule-copies.js"]
    end
```

이러한 매니페스트의 구조와 각 에이전트의 마켓플레이스에 플러그인을 등록하는 방식에 대한 자세한 내용은 **[마켓플레이스 및 플러그인 매니페스트](#7.3)**를 참조하세요.

**출처:** [package.json:1-15](), [scripts/check-rule-copies.js:58-60]()

---

## OpenClaw 스킬 빌드

Ponytail은 OpenClaw 플랫폼을 위한 특수한 빌드 프로세스를 제공합니다. `build-openclaw-skills.js` 스크립트는 핵심 스킬을 OpenClaw가 요구하는 형식으로 변환하며, YAML frontmatter와 설명 길이 제한(≤160자)을 충족하도록 보장합니다.

`openclaw-skills.test.js` 스위트는 드리프트를 막는 가드 역할을 하며, 생성된 스킬이 원본 `SKILL.md` 파일과 본문이 그대로 일치하는지 검증합니다.

빌드 스크립트와 검증 로직에 대한 자세한 내용은 **[OpenClaw 스킬 빌드(build-openclaw-skills.js)](#7.4)**를 참조하세요.

**출처:** [scripts/check-rule-copies.js:38-42]()
