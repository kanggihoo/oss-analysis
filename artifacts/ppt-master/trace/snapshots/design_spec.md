<!-- ppt-master-schema: design-spec/v1 -->
# 백엔드 개발자 포트폴리오 (김도윤, 가상 샘플) - Design Spec

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | portfolio_demo_20261119 |
| Canvas Format | ppt169 (1280×720) |
| Page Count | 7 |
| Primary Language | ko-KR |
| Target Audience | 백엔드 채용 담당자와 면접관 |
| Communication Intent | 4년차 백엔드 개발자의 문제 해결 방식을 프로젝트 근거와 함께 소개하고 면접 기회를 얻는다 |
| Desired Audience Outcome | 두 프로젝트의 문제, 조치, 수치 결과를 이해하고 면접에서 더 물어볼 질문을 갖는다 |
| Core Message / Ask / Action | 측정으로 병목을 찾아 수치로 개선하는 백엔드 개발자 |
| Delivery Context | 화면 공유 면접 발표 약 5분이 주이고, 사후 PDF로 읽는 것이 보조 |
| Artifact Afterlife | 지원서 첨부 자료 |
| Reading Mode | balanced |
| Content Strategy | Balanced default (`content_divergence` blank). 모든 사실과 수치는 `sources/portfolio.md`에 있는 것만 쓴다. 소스는 검증용 가상 샘플이다 |
| Design Style | Evidence first: custom mode(pyramid 기반) + custom visual style(swiss-minimal 기반) |
| AI Image Acquisition Path | not applicable (image source none) |
| Generation Mode | continuous |
| Spec Refinement | disabled |
| Speaker Notes | enabled — final Stage-2 proactive policy (`proactive_speaker_notes: true`) |
| Custom Animations | disabled — final Stage-2 proactive policy (`proactive_custom_animations: false`) |
| Narration Audio | disabled — final Stage-2 proactive policy (`proactive_narration_audio: false`) |
| Created Date | 2026-11-19 |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| Format | ppt169 |
| Dimensions | 1280 × 720 |
| viewBox | `0 0 1280 720` |
| Margins | 64 px on all sides |
| Content Area | x 64–1216, y 64–656 (1152 × 592) |

## III. Visual Theme

### Theme Style

- **Mode**: custom
- **Mode References**: pyramid
- **Mode Behavior**: Use pyramid as the only basis. Every page title states a finding in a full sentence, for example 'p95 latency fell from 1.8 s to 0.4 s'. Each project gets a problem and cause page, then an action and result page, so the interviewer reads the answer before the process. Keep the closing page to one sentence of direction and contact lines.
- **Visual style**: custom
- **Visual Style References**: swiss-minimal
- **Visual Style Behavior**: Use swiss-minimal as the only basis: a modular grid, square corners, single-weight rules, near-white field, and one oversized numeral or color column per page that zones the layout. The accent color marks only the 'after' number. No gradients, no shadows, no decorative badges.
- **Theme**: 근거 우선 격자. 흰색에 가까운 바탕, 페이지마다 남색 영역 하나, 주황은 "개선 후" 수치에만 쓴다
- **Tone**: 차분하고 엄밀하며 결과 숫자가 먼저 보이는 보고서 어조

### Color Scheme

| Role | HEX | Purpose |
| --- | --- | --- |
| Background | #FFFFFF | 페이지 바탕 |
| Secondary background | #F3F5F8 | 표의 줄무늬, 보조 영역, 카드 없는 패널 바탕 |
| Primary | #17305A | 제목, 격자 영역(남색 기둥·블록), 표 머리글 |
| Accent | #E58A00 | "개선 후" 수치와 규칙선 하나. 글자로는 남색 바탕 위(대비 4.96:1)에서만 쓰고 흰 바탕 위 작은 글자로는 쓰지 않는다(대비 2.64:1) |
| Secondary accent | #5A7FB0 | 보조 선, "개선 전" 수치의 큰 글자와 규칙. 본문 글자로는 쓰지 않는다(흰 바탕 대비 4.12:1) |
| Body text | #1B2330 | 본문 글자 |
| Secondary text | #566176 | 캡션, 주석, 각주 |
| Divider | #D3D9E2 | 얇은 규칙선, 표 경계선 |

## IV. Typography System

### Font Plan

| Role | Character (Reference) | Primary | English if non-English | Fallback tail |
| --- | --- | --- | --- | --- |
| Title | 한글 고딕, 굵은 두께, 좌측 정렬 | Malgun Gothic | Arial | sans-serif |
| Body | 한글 고딕, 보통 두께 | Malgun Gothic | Arial | sans-serif |

- **Title stack**: Malgun Gothic, Arial, sans-serif
- **Body stack**: Malgun Gothic, Arial, sans-serif

### Font Size Hierarchy

| Purpose | Anchor Size (px) |
| --- | ---: |
| Body | 24 |
| Title | 42 |
| Subtitle | 32 |
| Annotation | 18 |
| Footnote | 16 |
| Cover title | 72 |
| Display | 96 |

## V. Layout Principles

### Deck-wide Direction

- **Hierarchy direction**: 제목의 결론 문장을 먼저 읽고, 큰 수치로 시선이 내려간 뒤, 원인·조치 같은 근거를 작은 글자로 읽는다
- **Composition tendency**: 보이는 또는 암시된 모듈 격자에 맞춘 비대칭 분할. 남색 기둥 하나가 페이지를 구역으로 나누고 내용은 한 축에 맞춰 붙인다
- **Cross-page continuity**: 프로젝트 페이지(P03~P05)마다 같은 위치에 큰 수치(Display)가 오고, 바뀌는 값만 달라진다. 남색 기둥의 폭과 위치는 페이지 역할에 따라 바뀐다
- **Spacing posture**: variable by page rhythm (표지와 맺음말은 여백이 크고, 프로젝트 페이지는 촘촘하다)
- **Spacing anchors**: page margin 64 px, block gap 24 px, column gutter 32 px, corner radius 0 px, body leading 36 px

## VI. Icon Usage Specification

- **Primary bundled library**: tabler-outline
- **Stroke Width**: 2

| Icon Path | Suitable Scenarios |
| --- | --- |
| tabler-outline/gauge | 응답 시간, 성능 지표 |
| tabler-outline/database | DB, 쿼리, 인덱스 |
| tabler-outline/rocket | 배포, 출시 |
| tabler-outline/server | 서버, 인프라 |
| tabler-outline/mail | 이메일 연락처 |
| tabler-outline/user | 사람, 역할 |
| tabler-outline/code | 코드, 구현 |
| tabler-outline/chart-line | 개선 추이, 모니터링 |
| tabler-outline/git-branch | 파이프라인, 브랜치 전환 |
| tabler-outline/check | 완료, 결과 확인 |

## VII. Visualization Reference List

| Page | Family | Template | Usage |
| --- | --- | --- | --- |
| P06 | table | record_table | 기술 영역별 수준과 근거를 행(영역)과 고정 열(수준, 근거)로 비교한다 |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Image pattern | Crop Policy | Acquire Via | Status | Reference | text_policy | page_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## IX. Content Outline

### Part 1: 소개

#### Slide 01 - 표지

- **Audience move**: 이 발표가 누구의 무슨 이야기인지 모르는 상태 → 성능을 숫자로 개선한 개발자라는 인상으로 들어온다
- **Relationships**: 주장 제목 → 근거 수치(1.8초 → 0.4초) 순서. 이름·직군은 주장 제목에 속하는 소개 줄
- **Composition**: 큰 수치 "1.8초 → 0.4초"가 남색 기둥 안에 놓이고, 제목과 이름은 그 옆에서 한 축에 정렬된다. 일반적인 콘텐츠 카드 배치는 피한다
- **Title**: 측정으로 병목을 찾아 수치로 개선합니다
- **Core message**: 김도윤은 느린 API를 측정으로 찾아 고치는 4년차 백엔드 개발자다
- **Content**: 부제 "백엔드 개발자 김도윤 · 경력 4년" / 대표 수치 "p95 1.8초 → 0.4초" / 각주 "검증용 가상 샘플"
- **Cover impact**: hook(binding) = 주문 조회 API p95 응답 시간 1.8초 → 0.4초. composition은 Reference로 위 Composition 줄을 따른다

#### Slide 02 - 소개

- **Audience move**: 이름과 직군만 아는 상태 → 주 스택과 관심 분야를 알고 뒤의 프로젝트를 어떤 기준으로 볼지 안다
- **Relationships**: 소개 문장(parent) 아래에 주 스택, 관심 분야 두 묶음이 membership으로 속한다
- **Title**: 4년차 백엔드 개발자, 느린 API를 측정으로 찾아 고칩니다
- **Core message**: 스택은 Python 중심이고 관심은 성능 개선, 관측성, 배포 자동화다
- **Content**: 한 줄 요약 "느린 API를 측정으로 찾아 고치는 개발자" / 주 스택 Python · FastAPI · PostgreSQL · Redis · AWS / 관심 분야 성능 개선 · 관측성(observability) · 배포 자동화

### Part 2: 대표 프로젝트

#### Slide 03 - 주문 API: 문제와 원인

- **Audience move**: 문제가 있었다는 것만 아는 상태 → 느려진 원인 세 가지를 안다
- **Relationships**: 문제(p95 1.8초) → 원인 세 가지(N+1 쿼리, 인덱스 누락, 동일 상품 정보 반복 조회)의 순서. 원인 세 개는 같은 위계의 membership
- **Composition**: 큰 수치 "1.8초"가 남색 기둥에 서고, 원인 세 가지가 옆 열에 나란히 놓인다
- **Title**: 피크 시간 주문 조회 p95가 1.8초까지 느려진 원인은 세 가지였습니다
- **Core message**: 병목은 쿼리 수, 인덱스, 반복 조회의 세 곳에 있었다
- **Content**: 프로젝트 "주문 API 응답 속도 개선 (2025)" / 문제 "피크 시간대 주문 조회 API의 p95 1.8초" / 원인 N+1 쿼리 · 인덱스 누락 · 동일 상품 정보 반복 조회 / 내 역할 "원인 분석, 쿼리·인덱스 수정, cache 설계 (3인 팀 중 담당)"

#### Slide 04 - 주문 API: 조치와 결과

- **Audience move**: 원인을 아는 상태 → 어떤 조치로 얼마나 개선됐는지 숫자로 안다
- **Relationships**: 조치 세 가지가 각각 앞 페이지의 원인 세 가지에 대응(link). 결과 두 쌍은 개선 전 → 개선 후의 contrast
- **Composition**: "1.8초 → 0.4초"가 가장 크게 놓이고 "DB CPU 70% → 35%"가 그 아래에 작게 놓인다. 조치 세 가지는 한 열에 나열된다
- **Title**: 쿼리·인덱스·cache 조치로 p95가 1.8초에서 0.4초로 줄었습니다
- **Core message**: 세 조치로 p95는 1.8초에서 0.4초가 되고 DB CPU 사용률은 70%에서 35%가 됐다
- **Content**: 조치 `selectinload`로 쿼리 수 감소 · 복합 인덱스 추가 · Redis 상품 cache 도입 / 결과 p95 1.8초 → 0.4초, DB CPU 사용률 70% → 35%

#### Slide 05 - 배포 파이프라인 자동화

- **Audience move**: 앞 프로젝트가 성능 개선이었다는 것만 아는 상태 → 배포 자동화로 시간과 횟수가 어떻게 달라졌는지 안다
- **Relationships**: 문제(수동 배포 40분, 원복 절차는 문서에만 존재) → 조치(test → build → deploy, blue/green 전환, 실패 시 자동 rollback) → 결과의 순서. 결과 두 쌍은 개선 전 → 개선 후의 contrast
- **Composition**: 문제·조치·결과가 왼쪽에서 오른쪽으로 읽히는 세 구역이고, 결과 쪽 구역에 큰 수치가 온다
- **Title**: 수동 배포 40분을 8분으로 줄이고 월 배포를 4회에서 22회로 늘렸습니다
- **Core message**: 자동 배포 파이프라인으로 배포 시간은 40분에서 8분이 되고 월 배포 횟수는 4회에서 22회가 됐다
- **Content**: 프로젝트 "배포 파이프라인 자동화 (2024)" / 문제 수동 배포 40분, 원복 절차가 문서에만 존재 / 조치 GitHub Actions로 test → build → deploy 구성 · blue/green 전환 · 실패 시 자동 rollback / 결과 배포 시간 40분 → 8분, 월 평균 배포 횟수 4회 → 22회 / 내 역할 "파이프라인 설계와 구현 (단독)"

### Part 3: 역량과 맺음

#### Slide 06 - 기술 역량

- **Audience move**: 프로젝트에서 한 일을 아는 상태 → 영역별 수준과 그 근거를 한눈에 안다
- **Relationships**: 영역 다섯 개가 같은 위계의 membership이고, 각 영역에 수준과 근거가 한 쌍으로 붙는다
- **Title**: Python·PostgreSQL은 상, Redis·AWS·관측성은 중 수준입니다
- **Core message**: 핵심 역량은 Python/FastAPI와 PostgreSQL이고 나머지는 실무에서 적용해 본 중간 수준이다
- **Content**: 표 "영역 / 수준 / 근거" 다섯 행. Python / FastAPI 상 사내 API 12개 설계·운영 · PostgreSQL 상 쿼리 튜닝, 인덱스 설계 · Redis 중 cache, 분산 lock 적용 · AWS (ECS, RDS) 중 서비스 배포와 모니터링 구성 · 관측성 중 Prometheus·Grafana 대시보드 구성
- **Visualization**: skills-table = 영역별 수준·근거 표(table/record_table)
- **Native-ready**: skills-table=yes

#### Slide 07 - 맺음

- **Audience move**: 두 프로젝트와 역량을 아는 상태 → 이 사람이 어떤 엔지니어인지 한 문장으로 기억하고 연락 방법을 안다
- **Relationships**: 핵심 문장(parent) 아래에 연락처 두 줄(이메일, GitHub)이 membership으로 속한다
- **Composition**: 핵심 문장이 큰 글자로 한 축에 놓이고, 연락처 두 줄은 하단에 작게 붙는다
- **Title**: 데이터로 병목을 찾는 백엔드 엔지니어가 되겠습니다
- **Core message**: 앞으로도 측정으로 병목을 찾고 수치로 확인하는 방식으로 일한다
- **Content**: 핵심 문장 "데이터 기반으로 병목을 찾는 백엔드 엔지니어" / 이메일 example@example.com (샘플) / GitHub github.com/example (샘플)
- **Closing impact**: takeaway(binding) = "데이터 기반으로 병목을 찾는 백엔드 엔지니어". composition은 Reference로 위 Composition 줄을 따른다

## X. Speaker Notes Requirements

- **Generation**: enabled
- **Filename**: match each SVG filename under `notes/`
- **Content**: 각 페이지의 핵심 주장과 수치를 말로 풀어 쓴다. 소스에 없는 수치나 경험은 추가하지 않고, 페이지에 없는 설명은 "면접에서 더 물어볼 질문"을 유도하는 한두 문장으로만 보탠다
- **Total duration**: 약 5분 (페이지당 40~50초)
- **Notes style**: conversational
- **Presentation purpose**: 4년차 백엔드 개발자의 문제 해결 방식을 프로젝트 근거와 함께 소개하고 면접 기회를 얻는다
