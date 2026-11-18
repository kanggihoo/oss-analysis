---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-17
updated: 2026-11-17
---

# ppt-master Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/hugohe3/ppt-master` (branch `main`, 기준 SHA `3af3e8e`, 커밋 날짜 2026-11-15, `SKILL.md` metadata version 6.9.0)
- **작업트리 상태**: Clean
- **분석 목적**: 구조 파악·이해 + 기존 시스템에 연동할 부분 차용(2026-11-17 사용자 확정). 기존 시스템은 agent 기반 환경(agent가 `SKILL.md`를 읽고 스크립트를 직접 실행)이고, 확정·미리보기 화면은 이 레포의 것을 그대로 쓴다. 스펙은 "무엇을 넣으면 무엇이 나오는가"를 쓰고, 큰 코드(`svg_to_pptx` 등)는 어느 소스를 보면 되는지 위치만 안내한다. 이미지는 외부 API를 직접 구현하므로 파일 규약만 쓴다
- **라이선스**: MIT (Copyright 2025-2026 Hugo He) — `repos/ppt-master/LICENSE`, `repos/ppt-master/skills/ppt-master/LICENSE`(같은 MIT). 번들 데이터에 별도 라이선스가 있다: `skills/ppt-master/scripts/pptx_shapes/data/LICENSE-OPEN-XML-SDK-MIT.txt`, `LICENSE-APACHE-2.0.txt`. 아이콘(tabler·simple-icons·phosphor·chunk)과 효과음(kenney·bigsoundbank)은 각자 출처의 라이선스를 가질 수 있으나 이 단계에서 열지 않았다(미확인)
- **분석 대상 제품**: 레포는 "skill 패키지"이고 앱·서비스가 아니다(`AGENTS.md` "Compatibility Boundary"). 배포 입구는 둘이다. (1) `skills/ppt-master/`: agent가 읽는 SKILL.md·workflows·references와 agent가 호출하는 Python scripts. (2) `.claude-plugin/marketplace.json` + `skills/.claude-plugin/`: Claude Code plugin 등록(`git-subdir`, path `skills`). 상위 `docs/`는 사용자 문서다. 파일 13,174개 중 13,061개가 `skills/ppt-master/` 아래이고, 대부분은 아이콘·효과음·템플릿 자산이다(`templates/icons` 약 11,300개)
- **스펙 범위**: 2026-11-17 승인. 행 4(Default 생성 파이프라인, 공유 계약 C1·C2 포함), 6(SVG 작성 계약·품질 검사, C3·C4 포함, 15행 흡수), 8(`svg_to_pptx` 호출 규약과 코드 위치 안내, 12행의 `animations.json` 형식 포함), 9(이미지 파일 규약만), 14(확정·미리보기 화면) · 제외: 1(4행에 한 절로 포함), 2·3·5·7·10(승인 범위 밖, 추천 기본값), 11·13(이유: 사용자 제외), 16·17(부속), C5(8행 코드 위치 안내에 포함)

> 이 레포의 `AGENTS.md`·`CLAUDE.md`는 레포 자체를 고치는 개발자용 지침이다. 이 작업은 읽기 분석이라 따르지 않았다.

---

## 2. 프로젝트 개요

ppt-master는 **agent(Claude Code·Codex 등)가 읽고 따르는 워크플로(markdown 문서 묶음)와, 그 워크플로가 호출하는 Python 도구 묶음**이다. 사용자가 PDF·DOCX·URL·주제를 주면 agent가 문서를 읽으며 (1) 소스를 Markdown으로 변환하고 (2) 디자인 명세(`design_spec.md`, `spec_lock.md`)를 세우고 (3) 페이지마다 SVG를 손으로 쓴 뒤 (4) `svg_to_pptx.py`가 SVG를 DrawingML(PowerPoint 네이티브 도형·차트·표)로 변환해 `.pptx`를 낸다. LLM을 호출하는 코드는 이미지 생성·TTS 같은 주변 도구뿐이고, 슬라이드 내용·디자인을 정하는 것은 이 레포 밖의 agent다(근거: `skills/ppt-master/SKILL.md` 서두 "routed presentation workflow", `workflows/generate-pptx.md` Step 4·6의 역할 전환). 이 해석은 문서 선언 기준이다.

최상위 경로는 셋이다(`workflows/routing.md` 2절): **Generate PPTX**(새로 생성; Default/Quick 두 런타임과 Image to PPTX·Beautify 두 profile), **Create Template**(brand·style·layout·deck 4종 재사용 workspace), **Edit Native PPTX**(기존 deck을 `pptx_to_svg.py --roundtrip` workspace로 가져와 바뀐 페이지만 재작성).

### Feature map

<!--
한 행 = 스펙 하나의 작업 단위. 검증 수준은 이번 세션 기준이다: 진입점 파일 존재·크기·문서 선언까지만 읽었고 구현 본문은 읽지 않았다.
-->

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 진입 규율·경로 선택 | agent가 SKILL.md를 읽고 무결성 검사 후 3개 최상위 경로 중 하나와 profile을 고른다. 포함 안 함: 각 경로 절차 | `skills/ppt-master/SKILL.md`, `workflows/routing.md`, `scripts/attribution_guard.py` `require_skill_integrity` | 없음 | 핵심 | — (4행 스펙에 경로 선택 절로 포함) | 문서 선언은 코드 확인(SKILL.md·routing.md 전문). attribution_guard 본문 미확인 |
| 2 | 소스 변환 | PDF·DOCX·XLSX·PPTX·EPUB·HTML·LaTeX·URL → Markdown + conversion profile. 포함 안 함: 프로젝트 import | `scripts/source_to_md.py`(619줄) → `scripts/source_to_md/_dispatcher.py`, `pdf_to_md.py`, `doc_to_md.py`, `excel_to_md.py`, `ppt_to_md.py`, `web_to_md.py` | 없음 | 핵심 | — (제외: agent가 `source_to_md.py`를 그대로 사용) | 추론(README·generate-pptx Step 1 표와 파일 목록. 본문 미확인) |
| 3 | 프로젝트 관리 | `init`·`import-sources`·`validate`로 `projects/<name>_<date>` 만들기와 검증, 워크플로 로그 | `scripts/project_manager.py` → `scripts/project_management/cli.py`, `paths.py`, `project_specs.py`, `spec_blocks.py`, `page_context.py`, `scripts/workflow_log.py` | 2 | 핵심 | — (제외: 레이아웃은 C1로 4행 스펙에 포함) | 코드 확인(wrapper 전문과 사용법). 구현 미확인 |
| 4 | Default 생성 파이프라인 | Step 1~7: 소스 → Strategist(2단계 사용자 확인, `design_spec.md`·`spec_lock.md`) → 이미지 → Executor(페이지별 SVG) → 후처리·내보내기. 포함 안 함: 각 단계 도구 | `workflows/generate-pptx.md`, `references/strategist*.md`, `references/executor-*.md`, `references/plan-core.md`, `references/modes/*.md`, `scripts/update_spec.py`, `scripts/total_md_split.py` | 1, 3 | 핵심 | [`capabilities/generate-default-pipeline.md`](./capabilities/generate-default-pipeline.md) · ready (C1·C2 포함, 1행 경로 선택 절 포함) | 코드 확인(generate-pptx.md의 단계 제목·Step 7), 나머지 추론 |
| 5 | Quick 생성·profile | 전략·확인·spec 없이 SVG를 직접 써서 내보내는 짧은 경로. Image to PPTX(래스터 페이지 → 레이어 PPTX)와 Beautify(1:1 재디자인)는 profile | `workflows/profiles/quick-generate.md`, `image-to-pptx.md`, `beautify-pptx.md`, `scripts/image_layers.py`, `scripts/image_ocr.py` | 4 | 핵심 | — (제외) | 추론(routing.md 3절 표만) |
| 6 | SVG 작성 계약·품질 검사 | agent가 쓸 SVG의 허용 문법과 `svg_quality_checker.py --stage final` 보고서. exporter가 이 보고서를 요구한다 | `references/shared-standards-core.md`, `scripts/docs/svg-contract.md`, `scripts/svg_quality_checker.py`(63줄) → `scripts/svg_quality/checker.py`, `svg_contracts.py`, `scripts/svg_authoring_contract.py`, `scripts/svg_authoring_view.py`, `scripts/text_measure.py` | 없음 | 핵심 | [`capabilities/svg-authoring-and-quality.md`](./capabilities/svg-authoring-and-quality.md) · ready (C3·C4 포함, 15행 흡수) | 추론(AGENTS.md 명령 표, Step 7 문구) |
| 7 | SVG 후처리 (`finalize_svg`) | `svg_output/` → 자체 포함 `svg_final/` 미리보기(아이콘·이미지 임베드, 크롭, tspan 평탄화 등). 없어도 내보내기를 막지 않음 | `scripts/finalize_svg.py`(504줄) → `scripts/svg_finalize/{embed_icons,embed_images,crop_images,align_embed_images,fix_image_aspect,flatten_tspan,svg_rect_to_path}.py`, `scripts/icon_sync.py` | 6 | 핵심 | — (제외: 내보내기를 막지 않는 미리보기) | 추론(Step 7.2 문구와 모듈 이름) |
| 8 | SVG → PPTX 변환기 | SVG 요소를 DrawingML 네이티브 도형·텍스트·그림·차트·표·수식으로 바꿔 OPC 패키지를 만든다. `--roundtrip`이면 원본 객체를 복원. 코드 규모 가장 큼 | `scripts/svg_to_pptx.py`(wrapper, 31줄) → `scripts/svg_to_pptx/{pptx_package,drawingml,native_objects}/`, `scripts/pptx_shapes/`, `scripts/preset_shape_svg.py`, `scripts/shape_boolean_svg.py`, `scripts/pptx_opc_validation.py`, `scripts/pptx_delivery_check.py` | 6 | 핵심 | [`capabilities/svg-to-pptx-cli.md`](./capabilities/svg-to-pptx-cli.md) · ready (호출 규약과 코드 위치 안내, 12행 `animations.json` 형식 포함) | 코드 확인(wrapper 전문, `pptx_package/cli.py` `main`의 품질 gate·호출 순서, `builder.py` 패키징 흐름). 도형·텍스트·차트 매핑 규칙 미확인 |
| 9 | 이미지 확보 | AI 이미지 생성(15개 backend), 무료 이미지 검색(Openverse·Pexels·Pixabay·Wikimedia), 후처리(slice·rotate·워터마크 제거·분석) | `scripts/image_gen.py`(1,538줄) → `scripts/image_backends/backend_*.py`, `scripts/image_search.py`(2,927줄) → `scripts/image_sources/`, `scripts/slice_images.py`, `scripts/image_treat.py`, `scripts/analyze_images.py`, `workflows/stages/web-image-review.md`, `references/image-*.md` | 3 | 핵심 | [`capabilities/image-file-contract.md`](./capabilities/image-file-contract.md) · ready (파일 규약만) | 코드 확인(backend·provider 파일 목록), 동작은 추론 |
| 10 | 템플릿 시스템 | Create Template(brand·style·layout·deck 4종 workspace 만들기·등록)과 Default Stage 1에서의 적용. 번들 라이브러리(`templates/{brands,styles,layouts,decks}` + index.json) | `workflows/create-template.md`(384줄)와 `create-template/*.md`, `scripts/register_template.py`(1,498줄), `scripts/mirror_template_materialize.py`(3,612줄), `scripts/apply_template.py`, `scripts/pptx_template_import.py`, `scripts/template_import/`, `workflows/stages/apply-template-workspace.md`, `templates/*_index.json` | 4(적용 쪽), 8 | 핵심 | — (제외: 템플릿 미사용 가정) | 추론(routing.md 4·5·7절) |
| 11 | Edit Native PPTX (round-trip) | 기존 `.pptx` → `pptx_to_svg.py --roundtrip` workspace → 바뀐 페이지만 재작성, 나머지는 바이트 그대로 복원 → 새 PPTX | `workflows/edit-native-pptx.md`(175줄), `scripts/pptx_to_svg.py` → `scripts/pptx_to_svg/converter.py`, `slide_to_svg.py`, `scripts/pptx_ooxml/`, `scripts/pptx_workspace.py`, `scripts/authoring_roundtrip.py`(2,379줄), `scripts/pptx_intake.py` | 8 | 핵심 | — (제외: 사용자 결정) | 코드 확인(edit-native-pptx.md 1절까지), 구현 미확인 |
| 12 | 전환·애니메이션 | 페이지 전환, auto-advance, 객체 애니메이션(`animations.json`)을 PPTX에 기록 | `references/animations.md`, `workflows/stages/customize-animations.md`, `scripts/pptx_animations.py`(3,869줄), `scripts/pptx_transitions.py`(3,204줄), `scripts/animation_config.py`, `scripts/pptx_animation_presets.json`, `scripts/sound_sync.py` | 8 | 핵심 | — (8행 스펙의 `animations.json` 형식에 포함) | 추론 |
| 13 | 내레이션·영상 | 발표 노트 → TTS 6종(edge·elevenlabs·minimax·qwen·cosyvoice·openai) → 타이밍 동기화 → 내레이션 PPTX/MP4 | `workflows/stages/generate-audio.md`, `scripts/notes_to_audio.py` → `scripts/tts_backends/`, `scripts/narration_sync.py`(2,245줄), `scripts/powerpoint_video.py`, `scripts/video_motion_plan.py`, `scripts/video_sound_mix.py`, `scripts/video_subtitles.py`, `references/video-design.md` | 8, 12 | 핵심 | — (제외: 사용자 결정) | 추론 |
| 14 | 사용자 확인·미리보기 UI | 로컬 웹 서버 3종: Stage 1/2 확인 화면, spec 리뷰·주석, 라이브 SVG 편집·주석 반영 | `scripts/confirm_ui/server.py`(2,986줄), `scripts/spec_review/server.py`, `scripts/check_spec_annotations.py`, `scripts/svg_editor/server.py`(1,682줄), `scripts/check_annotations.py`, `workflows/stages/live-preview.md`, `references/confirm-surface.md` | 4 | 핵심 | [`capabilities/confirm-and-preview-ui.md`](./capabilities/confirm-and-preview-ui.md) · ready | 추론 |
| 15 | 품질 게이트 stage | 차트 검증, 시각 검토, 실패 복구 | `workflows/stages/verify-charts.md`, `visual-review.md`, `workflows/governance/failure-recovery.md`, `scripts/visual_review.py`, `scripts/chart_recall.py`, `scripts/visualization_recall.py` | 4, 6 | 핵심 | — (6행 스펙에 흡수) | 추론 |
| 16 | 설치·갱신·유지보수 도구 | `update_repo.py`(레포 갱신), `prompt_audit.py`(프롬프트 길이·거버넌스 lint, maintainer 전용), `batch_validate.py`, `generate_examples_index.py`, plugin 등록 | `scripts/update_repo.py`, `scripts/prompt_audit.py`+`prompt_audit_manifest.json`, `.claude-plugin/marketplace.json`, `skills/.claude-plugin/` | 없음 | 부속 | — (부속, 제외) | 추론 |
| 17 | 번들 자산 | 아이콘 5종 라이브러리, 효과음 3종, 차트·표 템플릿, 캔버스 형식. 스크립트가 아니라 데이터 | `templates/icons/`, `templates/sounds/`, `templates/charts/`, `templates/tables/`, `references/canvas-formats.md` | 없음 | 부속 | — (부속, 제외) | 코드 확인(디렉터리 목록·개수). 라이선스 미확인 |

**공유 계약** (여러 기능이 같이 쓰는 것. 이번 세션에서는 이름만 확인했고 본문은 열지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| C1 프로젝트 디렉터리 레이아웃(`sources/ svg_output/ svg_final/ notes/ images/ exports/ validation/`, `animations.json`) | 3, 4, 5, 7, 8, 12, 13, 14 | `scripts/project_management/paths.py`, `scripts/docs/project.md` | 별도 스펙 없음(3행 1.3에 둠, 제안) · 미작성 | 추론 |
| C2 `design_spec.md`(§I~§IX) + `spec_lock.md` | 4, 5(Quick은 없음), 6, 10, 14 | `templates/design_spec_reference.md`, `templates/spec_lock_reference.md`, `scripts/project_specs.py`, `scripts/project_management/spec_blocks.py` | 4행 1.3에 둠(제안) · 미작성 | 추론 |
| C3 SVG 작성 계약(허용 요소·`data-*` 마커·native 마커) | 5, 6, 7, 8, 11 | `scripts/docs/svg-contract.md`, `references/semantic-svg.md`, `references/native-*.md` | 6행에 둠(제안) · 미작성 | 추론 |
| C4 final 품질 보고서(`validation/*.report.json`) | 6, 8 | `scripts/svg_quality/`, Step 7.3 문구 | 6행에 둠(제안) · 미작성 | 코드 확인(generate-pptx.md Step 7.3: exporter가 `final` 보고서를 요구하고 없거나 낡으면 nonzero) |
| C5 `pptx_shapes` 프리셋·수식 데이터(187 프리셋, Open XML SDK 데이터) | 8, 10, 11 | `scripts/pptx_shapes/{registry,loader,formula,semantics}.py`, `pptx_shapes/data/` | 8행에 둠(제안) · 미작성 | 추론 |

**대조한 범위와 미탐색 영역**

- **대조**: `README.md` 앞 200줄(포지셔닝·Quick Start 입구), `SKILL.md` 전문, `workflows/routing.md`·`index.md` 전문, `generate-pptx.md`의 Step 1·2 전문과 Step 7, `edit-native-pptx.md` 서두, `AGENTS.md` 전문(레포 쪽), `scripts/README.md` 앞 66줄, `scripts/svg_to_pptx.py`·`project_manager.py` wrapper, `git ls-files` 디렉터리 집계, 각 하위 패키지 파일 목록, `.claude-plugin/marketplace.json`. 문서 17개와 scripts 하위 패키지 14개의 이름으로 행을 나눴다.
- **문서와 구현의 차이**: 아직 대조하지 않았다.
- **미탐색**: (a) 구현 본문 전부. 어떤 `.py`도 wrapper 외에는 열지 않았다. 코드 규모는 `skills/ppt-master/scripts/` Python 255개 파일 188,288줄(테스트 `scripts/tests/` 121개 27,611줄 제외, 2026-11-17 `git ls-files '*.py'`와 `wc -l`로 측정)이다. 이 중 `svg_to_pptx/` 패키지가 57,727줄로 가장 크고 `scripts/` 직속 파일이 59,757줄이다. 단일 파일 최대는 `svg_quality/checker.py` 10,318줄, 다음이 `svg_to_pptx/pptx_package/builder.py` 8,810줄이다. 이 책의 앞 판에 적었던 "약 60,000줄"은 직속 파일만 센 값이라 틀렸다. (b) `references/`의 role 문서 본문(strategist·executor 계열), `workflows/create-template*`·`profiles/*`·`stages/*` 본문. (c) `docs/`(사용자 문서)와 README 200줄 이후. (d) `scripts/tests/`(129개), `templates/` 하위 내용, `.github/`, `docs/rules/`는 워크플로 2장 3번 기본 제외. (e) 외부 도구·API(이미지 생성 provider, TTS provider)는 실행하지 않았다.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 과정과 주체 구분 (Default 생성 경로) | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 색으로 AI(agent) 판단·작성 / 스크립트 / 사용자 / 파일 / 외부 API를 구분한 17노드 구조도 |

검증: archify `finalize`의 validate·deliver·check·browser-check 통과(`--repo-root`로 인용 줄 대조 포함)와 `visual-check` 캡처(2048×1320 라이트 이미지)를 눈으로 훑어 배치·라벨 겹침이 없음을 확인했다. 전문 시각 검토는 아니다. 이 그림은 먼저 그린 모듈 중심 구조도를 대체한다.

### 그림 해설

"AI"는 레포 밖에서 `SKILL.md`·workflow 문서를 읽고 따르는 agent(LLM)다. 이 레포의 코드는 LLM을 직접 부르지 않는다(내보내기 경로 기준 확인, 아래 미확인 참고).

**읽는 순서**
1. 위 줄을 왼쪽에서 오른쪽으로: 사용자 확정 → Strategist → spec 파일 → Executor → `svg_output/`.
2. 둘째 줄을 왼쪽에서 오른쪽으로: 소스 변환 → 프로젝트 → (이미지) → 편집기 → 품질 검사.
3. `svg_quality_checker`에서 `svg_to_pptx`로 내려와 `exports/*.pptx`로 끝난다. 사용자 수정과 PowerPoint 직접 편집은 이 흐름에 옆에서 들어온다.

**전체 과정과 주체** (`workflows/generate-pptx.md` Step 1~7)

| 단계 | AI(agent) | 스크립트 | 사용자 |
|---|---|---|---|
| 1 소스 변환 (`:32`) | 조사가 필요한지 판단하고 조사 | `source_to_md.py`가 변환 | — |
| 2 프로젝트 초기화 (`:53`) | 명령 실행만 | `project_manager.py init`·`import-sources` | — |
| 3 템플릿 후보 준비 (`:72`) | 후보 범위를 `recommendations.stage1.json`에 담음 | 서버가 템플릿 index를 읽음 | — |
| 4 Strategist (`:91`) | 청중·구성·디자인 판단, Stage 1 권장안, Stage 2 해결안 3개, `design_spec.md`·`spec_lock.md` 작성 | `confirm_ui/server.py`(확인 화면), `project_manager.py validate` | **Stage 1·2 확정(필수 gate)**, 선택적으로 spec 검토 |
| 5 이미지 (`:183`, 조건부) | 프롬프트·검색어 작성, 웹 후보 선택 | `image_gen.py`가 외부 이미지 API 호출, `image_search.py`, `slice_images.py` | — |
| 6 Executor (`:220`) | **페이지별 SVG 작성**, 발표자 노트 작성, 검사 위반 수정 | `svg_quality_checker`가 early(5페이지 뒤)·final 판정 | 선택적으로 시각 검토 요청 |
| 7 내보내기 (`:320`) | 명령 실행과 경고 보고 | `total_md_split.py`, `finalize_svg.py`, `svg_to_pptx.py` | — |
| 개정 | 수정할 층을 정해 고침 | 같은 검사·변환 재실행 | 수정 요청 |

**구조도: 노드별 역할**

| 노드 | 주체 | 맡은 일 | 근거 (`파일:줄`) | 검증 수준 |
|---|---|---|---|---|
| 사용자 | 사용자 | 요청과 소스를 주고 Stage 1·2를 확정. AI는 대신 확정하지 않는다 | `skills/ppt-master/workflows/generate-pptx.md:128` | 코드 확인(문서 선언) |
| confirm_ui | 스크립트 | Stage 1·2 확인 화면을 띄우고 `result.json`을 기록(AI가 쓰지 않는 사용자 영수증) | `scripts/confirm_ui/server.py:2804`, `generate-pptx.md:133-140` | 코드 확인(진입·문서). 서버 내부 미확인 |
| Strategist | AI | 소스·이미지 분석을 읽고 설계안을 만들어 `design_spec.md`(I~X절)와 `spec_lock.md`를 씀 | `generate-pptx.md:91`, `:156-170` | 코드 확인(문서 선언). 실제 프롬프트(`references/strategist.md`)는 미확인 |
| design_spec · lock | 파일 | 페이지 목록(§IX)·이미지 행(§VIII)·색·폰트 등 이후 단계의 기준 | `generate-pptx.md:156-170` | 코드 확인(문서 선언) |
| Executor | AI | `design_spec.md §IX` 순서대로 페이지마다 SVG를 `svg_output/`에 직접 씀 | `generate-pptx.md:220`, `:247` | 코드 확인(문서 선언). `executor-base.md` 미확인 |
| svg_output/ | 파일 | 페이지의 최종 모습을 담는 정지 SVG. 움직임은 담지 않는다 | `generate-pptx.md:247` | 코드 확인(문서 선언) |
| source_to_md | 스크립트 | 문서·URL을 Markdown으로 변환 | `scripts/source_to_md.py:581` | 추론 |
| project_manager | 스크립트 | 프로젝트 만들기, 소스 가져오기, 검증 | `scripts/project_management/cli.py:1292-1314` | 코드 확인(하위 명령). 구현 미확인 |
| 프로젝트 디렉터리 | 파일 | 도구들이 파일로 주고받는 공유 저장소(`sources/`, `images/` 등) | `scripts/project_management/cli.py:288` | 코드 확인(생성 함수). 전체 목록 미확인 |
| 이미지 생성·검색 | 외부 API | AI 이미지 생성(여러 provider)과 무료 이미지 검색. 프롬프트는 AI가 쓴다 | `scripts/image_gen.py:1275`, `generate-pptx.md:183` | 추론 |
| svg_editor | 스크립트 | 브라우저 편집기. Direct edit는 AI 없이 `svg_output/`을 고치고, 주석은 AI가 읽어 반영 | `scripts/svg_editor/server.py:1503`, `workflows/stages/live-preview.md:5` | 코드 확인(문서 선언과 진입). 구현 미확인 |
| 사용자 (수정) | 사용자 | 편집기에서 미세 수정하거나 주석을 단다. 재내보내기는 채팅으로 요청 | `live-preview.md:5` | 코드 확인(문서 선언) |
| svg_quality_checker | 스크립트 | `final` 보고서를 `validation/svg_quality_report.json`에 씀 | `scripts/svg_quality/cli.py:168` | 코드 확인(진입·보고서 경로). 검사 규칙 미확인 |
| 움직임 설계 | AI | 의미 단위로 객체를 묶고 순서·효과를 정해 `animations.json`을 씀. 기본은 꺼져 있고 요청이나 설정이 있을 때만 | `workflows/stages/customize-animations.md:1`, `scripts/animation_config.py:77` | 코드 확인(문서 선언). 지정 가능한 효과 목록은 미확인 |
| svg_to_pptx | 스크립트 | 품질 보고서가 통과가 아니면 중단. 통과하면 SVG를 DrawingML로 바꾸고 `p:transition`·애니메이션 XML을 덧붙여 PPTX를 만든다 | `scripts/svg_to_pptx/pptx_package/cli.py:3160-3170`, `builder.py:6791`, `scripts/pptx_transitions.py:1290` | 코드 확인(호출 순서). 도형·텍스트·차트 매핑과 애니메이션 XML 세부 미확인 |
| exports/*.pptx | 파일 | 타임스탬프가 붙은 새 파일로 매번 쓴다 | `cli.py:2697-2707` | 코드 확인 |
| PowerPoint | 사용자 | 결과 `.pptx`를 직접 편집. 이 수정은 `svg_output/`로 되돌아가지 않는다(추정: 내보내기가 새 파일을 쓰기 때문) | `docs/why-ppt-master.md:39` | 추론 |

**실행 흐름: svg_to_pptx 내보내기** (`svg_to_pptx/pptx_package/cli.py:1984` `main`)
1. 시작 — `require_skill_integrity()` 호출 후 argparse. 입력 프로젝트 경로, 출력 `exports/`(기본), `-s`로 다른 SVG 디렉터리 선택(`cli.py:1984-2014`)
2. 품질 gate — 기본 내보내기와 `--quick-generate`는 현재 `svg_output/`에 대한 passing `final` 보고서를 요구한다. 없으면 오류와 `svg_quality_checker.py ... --stage final --json` 실행 안내를 출력하고 종료한다(`cli.py:3160-3170`). 구조도의 "SVG + 보고서" 간선이 이 입력 둘을 한 줄로 그린 것이다
3. 변환 — `create_pptx_with_native_svg`가 python-pptx로 빈 슬라이드 base를 만들어 풀고(`builder.py:7296-7311`), 슬라이드마다 `convert_svg_to_slide_shapes`로 슬라이드 XML과 미디어·관계를 얻어(`:7769`) `create_slide_xml_with_svg`를 거쳐 XML을 쓴 뒤(`:8050`), `[Content_Types].xml`을 갱신하고(`:8545`) 임시 zip으로 재패키징한다(`:8693`)
4. 마무리 — 성공하고 `-o`·기본 외 `-s`가 없으면 `svg_output/`을 `backup/<timestamp>/svg_output/`에 복사하고 postflight 보고서를 쓴다. postflight 검증의 실체는 ZIP 무결성과 슬라이드 수 두 가지이고 보고서 `checks`의 나머지는 고정 문자열 `enforced-at-build`다(`cli.py:1489-1500`). postflight 검증이 실패하면 "must not be used" 오류로 종료하고 잘못된 파일은 그대로 남긴다(`cli.py:3917-3935`)

**움직임** — SVG는 정지 화면이라 움직임을 담지 못한다. 페이지 전환은 내보내기 옵션(기본 fade 0.4초)으로, 객체 애니메이션은 기본 꺼짐이고 `-a auto` 또는 `animations.json` 사이드카로 켠다. 둘 다 `svg_to_pptx`가 PowerPoint XML로 덧붙인다(`references/animations.md` §1~2, `scripts/docs/pptx-animations.md` 소유권 표). 연속 동작은 키프레임 없이 두 정적 페이지를 Morph 전환으로 잇는다.

**미확인 영역**
- 그림에 넣지 않은 것: `finalize_svg`(svg_final 미리보기), 내레이션·영상, Create Template, Edit Native PPTX(`pptx_to_svg --roundtrip`), Quick·Image to PPTX·Beautify 경로, `attribution_guard`(모든 주요 CLI가 시작할 때 호출하고 실패 시 중단. 판정 조건은 읽지 않음)
- AI 노드 3개의 실제 프롬프트(`references/strategist.md`, `executor-base.md`, `customize-animations.md` 본문)는 열지 않았다
- `source_to_md`, `image_gen`, `svg_editor`, `confirm_ui` 내부는 진입 함수만 확인했다
- "LLM을 직접 부르지 않는다"는 내보내기 경로(`pptx_package/cli.py` `main`과 `builder.py` 패키징 흐름)에서만 확인했고, `builder.py` 8,810줄 전체와 다른 스크립트는 읽지 않았다

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸. 현재 전부 미작성
- **기준 메타데이터**: [repo-metadata.txt](../../artifacts/ppt-master/repo-metadata.txt)
- **기존 후보 자료**: [DeepWiki 출력](../../artifacts/ppt-master/deepwiki/pages-md/1-overview.md)(33페이지). 후보일 뿐이며, 이 feature map은 DeepWiki를 읽지 않고 원본 구조로 썼다
