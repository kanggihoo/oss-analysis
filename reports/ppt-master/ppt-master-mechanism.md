# ppt-master 동작 원리 및 아키텍처 설명서

> 본 문서는 `reports/ppt-master/capabilities/`에 분석·기록된 기능 스펙 5종(`generate-default-pipeline.md`, `svg-authoring-and-quality.md`, `svg-to-pptx-cli.md`, `image-file-contract.md`, `confirm-and-preview-ui.md`)을 종합하여, **ppt-master가 실제로 어떻게 동작하고 파이프라인이 굴러가는지** 전체 메커니즘을 설명합니다.

---

## 1. 핵심 개념: ppt-master는 무엇인가?

ppt-master는 일반적인 독립 실행형 애플리케이션(SaaS, GUI 앱)이 아니라, **AI 에이전트(Claude Code, Codex 등)가 지침을 읽고 직접 실행하는 "스킬(Skill) 패키지 + 파이프라인 도구 모음"**입니다.

- **두뇌 (LLM/에이전트)**: 기획, 레이아웃 구상, 슬라이드 디자인 결정, SVG 코드 직접 작성
- **도구 및 규약 (ppt-master)**: 에이전트가 단계를 밟을 수 있는 엄격한 상태 머신(워크플로), 파일 계약(JSON/Markdown), 검증기(`svg_quality_checker`), 로컬 확인 웹 서버(`confirm_ui`), PPTX 변환기(`svg_to_pptx`)

```mermaid
flowchart LR
    A["입력 자료<br/>(PDF, DOCX, 텍스트)"] --> B["1. 소스 변환<br/>(Markdown화)"]
    B --> C["2. 기획 (Strategist)<br/>design_spec & spec_lock"]
    C --> D["3. 사용자 확정<br/>(confirm_ui 웹)"]
    D --> E["4. 슬라이드 작성 (Executor)<br/>페이지별 SVG 수기 생성"]
    E --> F["5. 품질 검증 (Gate)<br/>svg_quality_checker"]
    F --> G["6. PPTX 빌드<br/>svg_to_pptx.py"]
    G --> H["최종 PPTX 파일"]
```

---

## 2. 전체 동작 파이프라인 (Default Pipeline 7단계)

`generate-default-pipeline.md`에 명시된 기본 워크플로는 아래 7개 단계를 순차적으로 거칩니다.

### Step 1: 소스 intake 및 Markdown 변환
- **역할**: 사용자가 넘겨준 원본 파일(PDF, DOCX, PPTX, 웹 URL 등)을 `source_to_md.py`를 통해 구조화된 `source.md`로 변환합니다.
- 긴 글의 경우 `total_md_split.py`로 챕터/슬라이드 단위로 분할 준비를 마칩니다.

### Step 2: 프로젝트 초기화
- `project_manager.py init`을 호출하여 프로젝트 전용 격리 폴더(예: `output/<timestamp>_deck/`)를 생성합니다.
- 표준 폴더 구조(`sources/`, `specs/`, `images/`, `svg_output/`, `validation/`, `build/`)가 세팅됩니다.

### Step 3: 기획 및 디자인 명세 수립 (Strategist 역할)
에이전트가 전략가(Strategist) 모드로 전환하여 슬라이드 전체 구조를 기획하고 두 개의 핵심 계약 파일을 작성합니다.
1. **`specs/design_spec.md`**: 슬라이드별 제목, 전달 메시지, 레이아웃, 컬러 팔레트, 폰트, 필요한 이미지 목록(표) 정의
2. **`specs/spec_lock.md`**: 총 슬라이드 수, 16:9 캔버스 크기(1920x1080 등), 필수 금지 규칙 등을 잠금(Lock)하여 이후 단계에서 임의 변경 방지

### Step 4: 사용자 중간 확정 (Stage 1 / Stage 2 UI)
- 에이전트가 로컬에 `confirm_ui` 웹 서버를 백그라운드(`--daemon`)로 띄웁니다.
- 브라우저를 통해 사용자에게 기획안(슬라이드 구성, 테마 추천)을 보여주고 확정(`result.json`, `template_selection.json`)을 받습니다.
- 사용자가 승인하면 서버가 종료되고 다음 단계로 넘어갑니다.

### Step 5: 슬라이드 SVG 작성 (Executor 역할)
- 에이전트가 실행자(Executor) 모드로 전환하여 페이지마다 `svg_output/slide_001.svg`, `slide_002.svg` 형태로 SVG 코드를 직접 작성합니다.
- 이때 규약에 정의된 **시맨틱 SVG 태그**와 data 속성(`data-native="chart"`, `data-shape="rect"`, 텍스트 상자 규칙 등)을 엄격히 준수합니다.
- 필요한 외부 이미지는 `images/` 폴더 규약에 맞춰 배치하고 SVG 내 `<image>` 태그로 연결합니다.

### Step 6: 품질 검사 (Gatekeeper)
- `svg_quality_checker.py --stage final`을 실행합니다.
- 텍스트 오버플로우, 컬러 콘트라스트, 캔버스 크기 위반, 잘못된 태그 등이 있는지 자동 검증합니다.
- 검사 결과는 `validation/svg_quality_final_report.json`에 저장되며, **Pass하지 못하면 다음 단계(PPTX 변환)로의 진행이 원천 차단**됩니다.

### Step 7: 최종 PPTX 패키징
- `svg_to_pptx.py`를 호출하여 검증이 통과된 SVG들을 DrawingML 네이티브 도형/텍스트/차트가 담긴 최종 `.pptx` 파일로 변환합니다.

---

## 3. 핵심 모듈별 동작 원리

### 3.1. SVG 작성 규약 및 품질 검사 (`svg-authoring-and-quality.md`)
ppt-master의 핵심은 **"웹용 SVG를 파워포인트가 네이티브 개체로 이해할 수 있는 규격으로 작성하는 것"**입니다.

1. **시맨틱 태그 규칙**:
   - 일반 사각형/원: `<rect>`, `<circle>`, `<path>`를 사용하되 정해진 `data-shape` 속성 부여
   - 텍스트: 단순 `<text>`가 아닌 다단 문단 구조와 줄바꿈(`tspan`), 폰트 스타일 선언 준수
   - 차트 및 표: 픽셀 이미지가 아니라 `data-native="table"` 또는 `data-native="chart"` 메타데이터와 표 데이터를 인라인으로 작성
2. **품질 검사 게이트 (`svg_quality_checker.py`)**:
   - **Early 단계**: 기획 초기 1~2개 슬라이드 샘플 검사
   - **Final 단계**: 전 슬라이드 종합 검증 (1920x1080 뷰박스 준수, 텍스트 넘침, 유효하지 않은 SVG 요소 검출)
   - 결과 리포트에서 에러(Error)가 0건이어야만 PPTX 변환 도구가 작동하도록 설계되어 있습니다.

### 3.2. SVG → PPTX 변환 엔진 (`svg-to-pptx-cli.md`)
생성된 SVG를 단순 이미지로 PPTX에 붙이는 것이 아니라, **파워포인트 원본 도형(DrawingML)으로 1:1 역어셈블/변환**합니다.

- **OPC 패키징**: PPTX의 내부 구조인 Open Packaging Convention(XML, `.rels`, `[Content_Types].xml`, `ppt/slides/slide*.xml`)을 직접 조립
- **DrawingML 변환**:
  - SVG `<rect>`, `<path>` ➔ DrawingML `<p:sp>` (파워포인트 도형으로 변환되어 색상/크기 편집 가능)
  - SVG `<text>` ➔ DrawingML `<p:txBody>` (파워포인트 텍스트 상자로 변환되어 글자 수정 가능)
  - 애니메이션: 별도의 `specs/animations.json` 명세를 읽어 슬라이드 등장 애니메이션(페이드, 슬라이드 등)을 PPTX 네이티브 애니메이션 XML로 주입
- **무결성 검사**: 변환 완료 후 `pptx_opc_validation.py`를 통해 파워포인트 파일이 손상 없이 열리는지 사전 검증합니다.

### 3.3. 이미지 파일 계약 (`image-file-contract.md`)
외부 AI 이미지 생성기나 이미지 검색 도구가 파이프라인에 참여할 수 있도록 파일 계약(File Contract)을 분리해 두었습니다.

- **저장 위치**: 반드시 프로젝트 내 `images/` 디렉터리에 위치
- **파일명 규칙**: `slide_001_hero.png`처럼 슬라이드 번호 및 용도가 식별 가능해야 함
- **`manifest.json` 연동**: 이미지 출처(AI 생성 프롬프트, 라이선스, 대체 텍스트)를 기록하여 `design_spec.md §VIII`의 이미지 행과 1:1로 매칭
- 이를 통해 이미지 생성 도구가 어떤 백엔드(DALL-E, Midjourney, 로컬 검색 등)로 바뀌어도 전체 파이프라인이 깨지지 않습니다.

### 3.4. 사용자 확정 및 라이브 피드백 화면 (`confirm-and-preview-ui.md`)
에이전트가 독단적으로 전체 슬라이드를 완성하지 않도록 사용자 개입 인터페이스(Human-in-the-loop)를 제공합니다.

1. **`confirm_ui` (포트 8000 기본)**:
   - 기획서(`design_spec.md`) 작성 직후 브라우저에 팝업되어, 사용자가 슬라이드 목차와 테마 색상을 확인하고 승인/반려
2. **`svg_editor` / Live Preview**:
   - 슬라이드 작성 중 실시간 렌더링 미리보기 제공
   - 사용자가 직접 화면에서 위치를 수정하거나 주석(Annotation)을 남기면, `check_annotations.py`를 통해 에이전트가 주석을 읽고 SVG 코드를 재수정
3. **`spec_review`**:
   - 명세 수정이 필요할 때 명세 전용 뷰어를 띄워 피드백 수집

---

## 4. 요약: ppt-master가 일하는 방식 한 줄 요약

> **"에이전트가 기획자(Strategist)와 디자이너(Executor) 역할을 번갈아 수행하며 Markdown과 SVG를 손으로 쓰고, ppt-master의 Python 도구들이 웹 확인창(`confirm_ui`), 엄격한 품질 검사기(`svg_quality_checker`), 파워포인트 네이티브 변환기(`svg_to_pptx`) 역할을 맡아 실패 없는 PPTX 완성을 강제하는 오케스트레이션 시스템"**
