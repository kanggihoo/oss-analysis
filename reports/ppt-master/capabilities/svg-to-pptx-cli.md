---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-17
updated: 2026-11-17
sources:
  - skills/ppt-master/scripts/svg_to_pptx.py
  - skills/ppt-master/scripts/svg_to_pptx/__init__.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/discovery.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/dimensions.py
  - skills/ppt-master/scripts/svg_to_pptx/pptx_package/notes.py
  - skills/ppt-master/scripts/svg_to_pptx/animation_config.py
  - skills/ppt-master/scripts/svg_to_pptx/drawingml/converter.py
  - skills/ppt-master/scripts/svg_to_pptx/drawingml/elements.py
  - skills/ppt-master/scripts/svg_to_pptx/drawingml/theme_fonts.py
  - skills/ppt-master/scripts/svg_to_pptx/drawingml/theme_colors.py
  - skills/ppt-master/scripts/svg_to_pptx/native_objects/__init__.py
  - skills/ppt-master/scripts/svg_to_pptx/native_objects/workbook.py
  - skills/ppt-master/scripts/svg_to_pptx/shape_boolean.py
  - skills/ppt-master/scripts/svg_to_pptx/text_outline.py
  - skills/ppt-master/scripts/animation_config.py
  - skills/ppt-master/scripts/pptx_animations.py
  - skills/ppt-master/scripts/pptx_transitions.py
  - skills/ppt-master/scripts/pptx_opc_validation.py
  - skills/ppt-master/scripts/pptx_delivery_check.py
  - skills/ppt-master/scripts/attribution_guard.py
  - skills/ppt-master/scripts/console_encoding.py
  - skills/ppt-master/scripts/workflow_transcript.py
  - skills/ppt-master/scripts/slide_roster.py
  - skills/ppt-master/scripts/project_utils.py
  - skills/ppt-master/scripts/config.py
  - skills/ppt-master/requirements.txt
  - skills/ppt-master/references/animations.md
  - skills/ppt-master/scripts/docs/pptx-animations.md
  - skills/ppt-master/scripts/docs/svg-pipeline.md
  - skills/ppt-master/workflows/generate-pptx.md
depends:
  - ../capabilities/svg-authoring-and-quality.md
  - ../capabilities/generate-default-pipeline.md
status: ready
---

# svg_to_pptx 호출 규약과 코드 위치 안내 (전환·애니메이션 `animations.json` 형식 포함)

> `svg_to_pptx.py <project_path>`에 프로젝트 디렉터리(`svg_output/`의 SVG와 선택 입력 `animations.json`·`notes/`·`spec_lock.md` 등)를 주면 `exports/<project>_<timestamp>.pptx`와 `validation/<같은 이름>.report.json`(옵션에 따라 `.trace.json`)을 만드는 CLI의 입력·출력·옵션·실패 규약과, 변환 내부를 읽을 때 어느 소스를 열면 되는지의 위치 안내다.

<!--
경로 표기: `skills/ppt-master/...`는 repos/ppt-master 기준, SKILL_DIR = repos/ppt-master/skills/ppt-master. 레포 루트의 `docs/...`는 그대로 쓴다.
용어: "exporter" = `svg_to_pptx.py` → `svg_to_pptx/pptx_package/cli.py`의 `main`. "gate" = 선행 스펙의 C4(final 품질 보고서) 검사. "sidecar" = `animations.json`.
범위 제한: 변환 내부(SVG→DrawingML 규칙, 약 57,700줄)는 풀지 않는다. 1.5의 "풀이 범위" 열에 영역마다 명시한다.
C1(프로젝트 디렉터리 레이아웃)은 [generate-default-pipeline.md](generate-default-pipeline.md) 1.3.5(`C1. 프로젝트 디렉터리 레이아웃`)가 정본이다(이 스펙을 마칠 때 파일이 생겨 있어 항목명·경로 표기를 맞췄다). 이 스펙은 `depends`에 넣지 않고, 이 스펙이 읽는 항목만 1.3(C)에 둔다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

실패 시점의 순서가 중요하다. `spec_lock.md` 검사는 gate보다 앞서고, 애니메이션 config 검증은 gate보다 뒤다(1.3 (I)).

1. agent가 `python3 skills/ppt-master/scripts/svg_to_pptx.py <project_path> [옵션]`을 실행한다. 선행으로 `svg_quality_checker.py ... --stage final --json`이 통과 보고서를 써 두어야 한다([선행 스펙](svg-authoring-and-quality.md) C4).
2. wrapper가 import 시점과 `main` 진입 시점에 무결성 검사(attribution guard)를 돌리고, 실패하면 exit 78로 끝난다(R-01). 그 다음 argparse와 옵션 조합 검사, 프로젝트 경로·`spec_lock.md`·canvas viewBox·theme 사전 조건 검사가 이어진다(R-03~R-06).
3. `svg_output/`의 직계 `*.svg`를 숫자순으로 로스터에 올리고(R-07), 기본 경로면 gate를 적용한다(R-08).
4. 변환 전에 발표자 노트 매칭, 내레이션 오디오 매칭(존재만), `animations.json` 로드·검증, 전환·애니메이션 설정 해석을 끝낸다. 여기서의 오류는 모두 `Error:` 한 줄과 exit 1이고 출력 파일은 없다(R-10~R-18).
5. `create_pptx_with_native_svg`가 임시 작업 디렉터리에서 python-pptx로 빈 슬라이드 base를 만들고, 슬라이드마다 SVG를 DrawingML로 바꿔 슬라이드 XML에 노트·전환·타이밍을 붙이고, 임시 zip을 검증한 뒤에야 `exports/`로 옮긴다(R-19, R-20).
6. 성공하면 `svg_output/`을 `backup/<timestamp>/svg_output/`에 복사하고(R-22), 옵션에 따라 trace를 쓴다(R-23).
7. postflight가 ZIP 무결성과 슬라이드 수만 확인하고 `validation/<stem>.report.json`을 쓴 뒤 요약을 출력하고 exit 0이다. postflight가 실패하면 이미 게시된 PPTX는 지워지지 않는다(R-21).

### 1.2 범위·통합 지점 [필수]

- 제공: (a) CLI 전체(위치 인자, 옵션, 기본값, 잘못된 값 처리), (b) 입력 파일·출력 파일·종료 코드·환경 의존, (c) `animations.json` 형식과 전환(`-t`)·객체 애니메이션(`-a`) 규약, (d) 변환 내부를 읽을 때의 코드 위치 안내(1.5).
- 제외: SVG→DrawingML 변환 내부 규칙(도형·텍스트·스타일·차트·표·수식·프리셋 도형 매핑)은 위치만 안내한다. `--roundtrip`(Edit Native PPTX 경로), 내레이션 오디오·타이밍 생성(`--recorded-narration` 등 narration 옵션은 존재만 표에 적음), 템플릿 structured 모드 상세(옵션 `--pptx-structure`와 입력 파일 존재만), `--enable-dangerous-nonconforming-svg-export`의 정규화 규칙, 개별 효과 키·전환 키의 옵션 값 목록(레지스트리 위치만 안내).
- 외부 의존·선행 계약: 선행 스펙 [svg-authoring-and-quality](svg-authoring-and-quality.md)의 C4(final 보고서)와 C3(SVG 작성 계약). C1(프로젝트 디렉터리)·C2는 [generate-default-pipeline.md](generate-default-pipeline.md) 1.3.5가 정본이고 1.3(C)에 이 스펙이 읽는 항목만 둔다. **코드 의존**: `svg_to_pptx/` 패키지는 "PPTX → SVG 가져오기" 범위에서 제외한 `scripts/pptx_to_svg/` 모듈을 import한다. 모듈 최상위 import는 `preset_authoring`(`drawingml/converter.py:32`, `drawingml/elements.py:34`, `pptx_package/template_structure.py:33`, `shape_boolean.py:35`), `emu_units`·`preset_registry_to_svg`·`preset_svg_markup`(`shape_boolean.py:34-40`)이고, 함수 안(지연) import는 `converter`·`ooxml_loader`(`pptx_package/cli.py:565`, `:1883`), `notes_import`·`ooxml_loader`(`builder.py:8788-8789`), `preset_authoring`(`drawingml/utils.py:3070`)이다. 그래서 `svg_to_pptx`만 따로 가져가려면 최소 `pptx_to_svg/`의 이 모듈들이 필요하다(검색: `grep -rn "from pptx_to_svg\|import pptx_to_svg" skills/ppt-master/scripts/svg_to_pptx`, 이 디렉터리 안만 확인). `spec_lock.md`의 일부 필드(C2)를 읽으므로 필드는 R-06에 적는다.
- 소유 상태·부작용: 프로젝트 안에 `exports/*.pptx`, `validation/<stem>.report.json`, 선택적 `validation/<stem>.trace.json`, `backup/<timestamp>/svg_output/`을 만든다. `validation/workflow.log`가 이미 있으면 이 명령의 stdout·stderr를 그 파일에 덧붙인다(R-02). 소스 SVG·`animations.json`·`notes/`는 읽기만 한다. 임시 작업 디렉터리는 성공·실패와 관계없이 지운다.

### 1.3 인터페이스와 데이터 의미 [필수]

**(A) 호출 형식**

```bash
python3 skills/ppt-master/scripts/svg_to_pptx.py <project_path> [옵션]
python3 skills/ppt-master/scripts/animation_config.py {scaffold|list-groups|validate} <project_path>   # animations.json 보조 CLI
python3 skills/ppt-master/scripts/pptx_animations.py {--list|--describe <효과>|--describe-transition <효과>|--demo}   # 레지스트리 조회
```

`svg_to_pptx` 패키지의 공개 API는 `main()`, `convert_svg_to_slide_shapes()`, `create_pptx_with_native_svg()` 셋이며 lazy import다(`__init__.py`). 이 스펙의 계약은 CLI다.

**(B) `svg_to_pptx.py` CLI.** 기본값 열의 `—`는 인자 없음, `None`은 "지정하지 않음"이며 이후 `animations.json`·내장 기본값으로 풀린다(R-12).

| 옵션 | 기본값 | 의미 | 잘못된 값 처리 |
|---|---|---|---|
| `project_path` (위치 인자, 필수) | — | 프로젝트 디렉터리 | 경로가 없으면 stdout에 `Error: Path does not exist: …`, exit 1(stderr가 아니다) |
| `-o`, `--output` | `None` | 출력 `.pptx` 경로(CWD 기준). 주면 `exports/` 이름 규칙과 backup이 모두 꺼진다(R-09, R-22). 부모 디렉터리는 만든다 | — |
| `-s`, `--source` | `None`(= `output` = `svg_output/`) | SVG 소스. `output`→`svg_output`, `final`→`svg_final`, 그 밖은 프로젝트 하위 디렉터리 이름. 기본값 외를 주면 진단 모드가 된다(R-07) | 디렉터리가 없거나 SVG가 0개면 `Error: No SVG files found…` exit 1(폴백 없음) |
| `-f`, `--format` | `None` | 모든 SVG의 canvas가 이 등록 포맷(`config.py`의 `CANVAS_FORMATS` 키, 예: `ppt169`)과 같아야 함 | 키가 아니면 argparse exit 2. viewBox 불일치는 `Error:` exit 1(R-26) |
| `-q`, `--quiet` | off | 진행·postflight 요약 출력을 줄인다. 오류 출력은 그대로(R-24) | — |
| `--quick-generate` | off | lockless Quick 프로젝트용. `spec_lock.md` 없이 SVG 로스터에서 canvas·flat/structured를 추론, gate는 그대로 적용, 노트는 `--with-notes`를 줘야 켜진다 | `--source`가 기본값이 아니거나 `--pptx-structure`가 있으면 exit 1(R-04) |
| `--primary-language TAG` | `None` | 덱 언어(BCP-47). `spec_lock.md`의 `communication.primary_language`와 첫 페이지 루트 `lang`보다 우선 | 형식 오류면 `Error:` exit 1. 어디에도 선언이 없으면 경고만 하고 계속(R-06) |
| `--pptx-structure` | `None` | `structured`/`flat`만 유효. `None`이면 `spec_lock.md`의 `## pptx_structure` `- mode:`를 읽음. 상세는 제외 범위 | `baseline/template/preserve/generated`는 마이그레이션 오류로 exit 1. 락이 `structured`가 아닌데 `structured` 요청도 exit 1(R-06) |
| `--reflow-text` / `--merge-paragraphs` / `--no-merge` | 셋 다 off = preserve | 텍스트 프레임 정책(reflow, reflow의 호환 별칭, 시각 줄마다 프레임) | 셋은 상호 배타. 같이 주면 argparse exit 2 |
| `--conversion-trace [PATH]` | `None` | 슬라이드별 변환 진단 JSON. PATH 없으면 `validation/<출력 stem>.trace.json`, 상대 PATH는 프로젝트 루트 기준(R-23) | — |
| `--native-charts-and-tables` (`--native-objects`는 폐기 예정 별칭, 경고 출력) | off | `data-pptx-replace-with` 마커의 차트·표를 PowerPoint 네이티브 Chart/Table로 대체. 기본 이름에 `_native_charts_tables` 접미사. 수식은 이 옵션과 무관하게 항상 네이티브(R-28) | 페이로드 검증 실패 시 `Error:` 목록과 exit 1 |
| `--no-image-optimize` | off | 래스터 이미지를 원본 바이트로 임베드 | — |
| `--image-max-dimension` | `2560` | 래스터 상한(px) | 1 미만이면 `Error:` exit 1 |
| `--image-sizing` | `cap` | `cap`=리사이즈·EXIF 보정이 필요할 때만 재인코딩, `display`=SVG 표시 크기 기준 압축 | `cap/display` 외 argparse exit 2 |
| `--image-scale` | `2.0` | `display`일 때 SVG px당 이미지 픽셀 | 1 미만이면 `Error:` exit 1 |
| `--image-quality` | `85` | 재인코딩 JPEG 품질 | 1~100 밖이면 `Error:` exit 1 |
| `-t`, `--transition` | `None`→`fade` | 페이지 전환 효과 키(1.3 (H)). `none`이면 전환 효과 없음 | choices 밖이면 argparse exit 2 |
| `--transition-duration` | `None`→`0.4` 초 | 전환 시간 | 음수·비유한수는 argparse exit 2. 효과가 `none`이 아닌데 0이면 `Error:` exit 1 |
| `--auto-advance` | `None` | 자동 넘김 초(클릭 넘김은 유지, `-t none`과 함께 써도 유지) | 음수는 argparse exit 2 |
| `--kiosk` | off | 클릭·키보드 넘김을 무시하는 반복 쇼. 기본 이름에 `_kiosk` 접미사 | — |
| `-a`, `--animation` | `None`→`none` | 객체 애니메이션: `none`, 효과 키 232개, `auto`/`mixed`/`random`(1.3 (G)). 명시한 `none`은 sidecar의 그룹 효과까지 모두 끈다(R-13) | choices 밖이면 argparse exit 2 |
| `--animation-duration` | `None`→`0.4` | 객체 효과 시간(초) | 0 이하는 argparse exit 2 |
| `--animation-trigger` | `None`→`after-previous` | `on-click`/`with-previous`/`after-previous` | choices 밖이면 argparse exit 2 |
| `--animation-stagger` | `None`→`0.5` | `after-previous`에서 요소 간 지연(초) | 음수는 argparse exit 2 |
| `--animation-config` | `None` | sidecar 경로(프로젝트 상대). 없으면 `<project>/animations.json`이 있을 때만 자동 사용 | 빈 문자열은 exit 1. 지정한 파일이 없으면 `Error: Animation config does not exist` exit 1. `--no-animations`와 배타(exit 2) |
| `--no-animations` | off | 전환과 객체 애니메이션을 모두 제거(내레이션 오디오·넘김 타이밍은 유지) | 전환·애니메이션 옵션(`-t`, `--transition-duration`, `-a`, `--animation-duration`, `--animation-trigger`, `--animation-stagger`)과 같이 주면 exit 1 |
| `--with-notes` / `--no-notes` | 둘 다 off | 기본은 노트 임베드 켜짐(Quick은 꺼짐). `--with-notes`는 Quick에서만 의미가 있고 다른 경로에서는 효과가 없다 | 상호 배타(exit 2) |
| narration 옵션: `--narration-audio-dir`, `--use-narration-timings`, `--recorded-narration`, `--narration-padding`(0.5), `--narration-start-floor`(0.8), `--inherit-motion-from` | off/`None` | 내레이션 오디오 임베드·타이밍. 존재만 적음(제외 범위). `--recorded-narration`은 기본 이름에 `_narrated` | `--inherit-motion-from`은 `--recorded-narration` 필요(exit 1) |
| `--roundtrip` | off | 제외 범위(Edit Native PPTX) | — |
| `--enable-dangerous-nonconforming-svg-export` | off | 호환 정규화 후 엄격 변환. gate가 꺼지고 trace가 자동으로 써짐. 상세는 제외 | `--roundtrip`/`--quick-generate`와 같이 주면 exit 1 |

**(C) 입력 파일·디렉터리.** 만드는 주체는 이 CLI 밖이다.

| 경로 | 필수 | 만드는 단계 | 이 CLI가 읽는 방식 |
|---|---|---|---|
| `svg_output/*.svg` | 필수 | agent(Executor), 선행 스펙 C3 | 직계 `*.svg`만, 숫자 파일명 순(R-07). 파일 stem이 노트·sidecar·내레이션 매칭 키 |
| `validation/svg_quality_report.json` | 기본 경로에서 필수 | `svg_quality_checker.py --stage final --json` | gate(R-08, 선행 스펙 C4) |
| `spec_lock.md` | 기본 경로에서 필수(Quick·진단·호환 모드 제외) | Strategist(C2) | R-06의 필드 |
| `images/…` | SVG가 참조할 때 | 이미지 확보 단계 | `<image href>`는 SVG 파일 기준 상대 경로, 프로젝트 밖이면 거부(R-25) |
| `notes/<svg stem>.md` 또는 `notes/slideNN.md` | 선택 | `total_md_split.py`(Step 7.1, 이 스펙 밖) | R-10 |
| `animations.json` | 선택 | `animation_config.py scaffold` + agent 편집 | 1.3 (G) |
| `metadata.json` | 선택 | 생성 주체 미확인(U-03) | docProps 필드(R-27) |
| `sounds/<ns>/<file>.wav` | sidecar가 참조할 때 | `sound_sync.py`(이 스펙 밖) | sidecar의 프로젝트 상대 경로 |
| `validation/workflow.log` | 선택 | `project_manager.py init`이 첫 기록을 씀(C1 스펙 1.3.5 인용, `project_management/cli.py:1412`는 이 스펙이 직접 열지 않음), 수동 메모는 `workflow_log.py` | 있으면 stdout·stderr를 덧붙임(R-02) |
| `templates/source_themes.json`, `page_plan.json`, `authoring-svg-flat/` | 해당 모드만 | 템플릿·roundtrip 경로 | `page_plan.json`이 있는데 `--roundtrip`이 아니면 exit 1(R-05). 나머지 상세는 제외 |
| `--recorded-narration`·`--narration-audio-dir`의 오디오 디렉터리 | 해당 옵션만 | 내레이션 단계(제외) | 슬라이드마다 `.m4a/.mp3/.wav` 하나(존재만 적음) |

**(D) 출력 파일**

| 출력 | 경로·이름 | 쓰는 시점·조건 |
|---|---|---|
| PPTX | 기본 `<project>/exports/<name>_<YYYYMMDD_HHMMSS>[_native_charts_tables][_narrated][_kiosk].pptx`. `<name>`은 디렉터리 이름에서 끝의 `_YYYYMMDD`와 `_<canvas format>`을 떼어 낸 값(예: `deck_ppt169_20261117` → `deck`). 타임스탬프는 로컬 시각, 초 단위. `-o`를 주면 그 경로 그대로 | 검증을 모두 통과한 뒤 마지막에 한 번 게시(R-20) |
| postflight 보고서 | `<project>/validation/<PPTX stem>.report.json`(`-o`를 줘도 프로젝트의 `validation/`, stem은 `-o` 파일 stem) | 성공 후 postflight 통과 시(R-21). 스키마 `ppt-master.pptx-postflight-report.v1` |
| trace | R-23 | `--conversion-trace`가 있거나 호환 모드일 때. PPTX 게시 뒤에 씀 |
| backup | `<project>/backup/<timestamp>/svg_output/`(+네이티브 payload store가 있으면 같은 상대 경로로 복사) | 성공 후, `-o`·`-s`(기본 외)가 없을 때만(R-22) |
| 콘솔 | 진행 줄, `[POSTFLIGHT] status=… quality_gate=… slides=… warning_categories=…`, `[PPTX] <경로>`, `[REPORT] <경로>` | `-q`가 아닐 때 |

postflight 보고서의 최상위 키: `schema`, `status`(`passed` / `passed-with-warnings` / `failed`), `output{path,bytes}`, `source{svg_slide_count, layout_definition_count, fingerprint, authoring_roundtrip}`, `package{zip_integrity, corrupt_member, slides, notes, masters, layouts}`, `checks{…}`, `quality`(gate 컨텍스트), `resources`(미해결 `{{token}}`, 폰트 스택, 이미지 종류별 개수), `export_policy`, `deck_motion`, `backup_path`, `conversion_trace_path`.

**(E) 종료 코드**

| exit | 조건 |
|---|---|
| 0 | 변환·게시·postflight 성공. 보고서 `status`가 `passed-with-warnings`여도 0. gate가 적용되지 않은 경로(`-s` 기본 외, 호환 모드)에서 보고서가 `failed`로 기록돼도 0이다(R-21) |
| 1 | 코드가 `return 1`로 끝내는 모든 오류: 사전 조건(R-04~R-06), SVG 없음, gate 실패(R-08), 노트 읽기 실패, animations.json 오류(R-11, R-17, R-18), `ValueError`·`TemplateStructureError` 계열 변환 오류, postflight 실패(게시된 PPTX가 남음, R-21). 그리고 `main`이 잡지 않는 예외(`RuntimeError` 계열)의 Python traceback(R-19) |
| 2 | argparse 오류: 알 수 없는 옵션, choices 밖 값, `type` 변환 실패(음수 등), 배타 그룹 위반 |
| 78 | 무결성 검사 실패(R-01). 보조 검사는 메시지 없이 78 |

**(F) 환경 의존** (`skills/ppt-master/requirements.txt`, 레포 루트 `requirements.txt`는 `-r`로 이를 가리킴. Python 3.10~3.14는 `docs/faq.md` 문서 선언이고 코드 확인 아님)

| 패키지 | 용도 | 없을 때 |
|---|---|---|
| `python-pptx>=0.6.21` | 빈 슬라이드 base 생성(`prs.save`)에만 쓰임 | `builder.py`가 import 시점에 로드하므로 시작 즉시 ImportError |
| `Pillow>=9.0.0` | 래스터 이미지 검증·최적화 | 래스터(PNG/JPG 등) href 검증이 실패해 변환 오류. SVG·EMF·WMF 이미지는 영향 없음(R-25) |
| `XlsxWriter>=3.0.0` / `openpyxl>=3.1.0` | 네이티브 차트 임베드 워크북 | 둘 다 optional import. 둘 다 없을 때의 동작은 확인하지 않음 |
| `skia-pathops>=0.9.2`, `uharfbuzz>=0.50.0` | Shape Boolean·텍스트 outline 연산 | 해당 기능을 쓰는 SVG에서만 `RuntimeError`(R-19) |
| `ffprobe`/`ffmpeg` | 내레이션 길이 | 내레이션 옵션에서만 필요(제외) |
| `PyYAML` 등 | 템플릿 등록용 | 이 CLI 무관 |

**(G) `animations.json` 형식.** 파일 위치는 `<project>/animations.json`(또는 `--animation-config`). 슬라이드 키는 SVG 파일 stem, 그룹 키는 그 SVG 루트 직계 `<g id>`다. 알 수 없는 필드는 어느 층에서나 오류다.

| 층 | 키 | 값·제약 |
|---|---|---|
| 최상위 | `version` | 생략하면 1, 1이 아니면 `Unsupported animation config version` |
| | `defaults` | `{transition, animation}`만 허용 |
| | `slides` | `{<slide-stem>: {…}}`. 목록에 없는 슬라이드는 `defaults`를 상속 |
| 슬라이드 | `transition`, `animation`, `groups`, `morph`만 허용 | 각각 object |
| `transition`(defaults·slide) | `effect` | 전환 키(1.3 (H)) 또는 `none`(시각 효과만 제거, `auto_advance`는 유지) |
| | `effect_options` | 선택한 효과가 지원하는 옵션만, 반드시 명시적 `effect`와 함께 |
| | `duration` | 초, `effect`가 `none`이 아니면 0보다 큼 |
| | `auto_advance` | 초, 0 이상 |
| | `sound` | 프로젝트 상대 `.wav` 경로 또는 `null`(슬라이드에서 `null`이면 상속된 소리를 지움) |
| `animation`(defaults·slide) | `effect` | 효과 키, `auto`, `mixed`, `random`, `none` |
| | `effect_options`, `duration`(>0), `stagger`(≥0), `trigger` | `trigger`는 `on-click`/`with-previous`/`after-previous` |
| | 타이밍·완료 필드 | `repeat_count`, `repeat_duration`, `auto_reverse`, `rewind`, `accelerate`, `decelerate`, `bounce_end`, `restart`(`always`/`when-not-active`/`never`), `after_effect`(`none`/`dim`/`hide`/`hide-on-next-click`), `sound` |
| `groups.<group-id>` | `{}` | 자리표시자. 아무 동작도 하지 않음 |
| | 단일 효과 객체 | 아래 row 필드를 직접 가짐. `effect: "none"`이면 그 그룹을 시퀀스에서 뺌 |
| | `{"effects": [row, …]}` | 빈 배열 불가, `effects` 외 필드와 함께 쓸 수 없음, 모든 row에 `effect` 필수. 같은 그룹에 여러 row 가능 |
| row | `effect` | 효과 키 또는 모드 |
| | `order` | 양의 정수(bool 불가). 생략하면 SVG 순서상 앞쪽에서 가장 가까이 명시된 order를 이어받음(맨 앞이면 0) |
| | `delay`(≥0), `duration`(>0), `trigger`, `effect_options`, 타이밍·완료 필드, `sound` | 생략한 값은 슬라이드 `animation`→`defaults.animation`→CLI 기본값 순으로 상속 |
| | `trigger_shape` | 다른 그룹 id. PowerPoint의 "On Click of". `on-click`을 의미하고, 명시 `trigger`가 있으면 `on-click`이어야 하며, `effect: none`과 못 쓴다 |
| `morph` | `from`, `pairs` | `from`은 직전 슬라이드 stem, `pairs`는 `{<key>: {from: <그룹>, to: <그룹>}}`(비어 있으면 안 됨). 같은 슬라이드에 `transition.effect: morph`가 명시돼야 하고 `morph_by`는 `object`만 가능 |

예시(최소 형태와 morph 한 쌍):

```json
{
  "version": 1,
  "defaults": {"transition": {"effect": "fade", "duration": 0.4}},
  "slides": {
    "03_threshold": {
      "groups": {
        "risk-marker": {"effects": [
          {"effect": "entrance_fade", "order": 1, "duration": 0.25},
          {"effect": "exit_fade", "order": 2, "duration": 0.3}
        ]}
      }
    },
    "04_detail": {
      "transition": {"effect": "morph", "effect_options": {"morph_by": "object"}},
      "morph": {"from": "03_threshold", "pairs": {"hero": {"from": "hero-a", "to": "hero-b"}}}
    }
  }
}
```

효과 키 레지스트리와 검증:

| 알고 싶은 것 | 위치·명령 |
|---|---|
| 객체 효과 키 전체(203개 canonical: entrance 53, emphasis 33, path 64, exit 53) | `skills/ppt-master/scripts/pptx_animation_presets.json`(데이터), 로더·개수 강제 `pptx_animations.py:219-371`. `python3 scripts/pptx_animations.py --list` |
| 호환 입력 29개 짧은 이름(`fade`, `fly_left`, `wipe_up` …) | `pptx_animations.py:101-131` `ANIMATION_ALIASES`. 새 출력은 canonical만 쓴다. CLI·sidecar 입력은 canonical 203 + 별칭 29 = 232 키 + `auto/mixed/random` + `none` |
| 한 효과의 옵션 값·타이밍 계약 | `python3 scripts/pptx_animations.py --describe <effect>` |
| 전환 키 48개 + 호환 8개(`strips circle diamond newsflash plus pull wedge wheel`) | `pptx_transitions.py:73-455`(스펙·카테고리), `:816-884`(레지스트리 조립, 48개 개수 강제), `python3 scripts/pptx_animations.py --list`, 효과별 옵션 `--describe-transition <effect>` |
| sidecar 필드 원문 | `skills/ppt-master/scripts/docs/pptx-animations.md` §8, `skills/ppt-master/references/animations.md` §2·§2.1 |
| 검증 | `python3 scripts/animation_config.py validate <project> [-c <config>]`: 필드·값 오류와 참조 오류(없는 슬라이드·그룹 등)를 export와 같은 함수로 검사. 오류면 exit 1, `animations.json`이 없으면 "No animations.json found…" 출력 후 exit 0 |
| 그룹 id 확인, 틀 만들기 | `animation_config.py list-groups <project>`(슬라이드당 한 줄), `scaffold <project> [-o path] [--force]`(기존 파일이 있으면 `--force` 없이 exit 1) |

**(H) 전환 `-t`와 객체 애니메이션 `-a`의 기본값 요약**

| 항목 | 기본 | 끄는 법 | 비고 |
|---|---|---|---|
| 페이지 전환 | `fade`, 0.4초 | `-t none`(자동 넘김은 유지) 또는 `--no-animations` | 키 48개(+호환 8개). `morph`는 `morph.pairs`와 함께 쓰면 결정적 매칭, 없으면 PowerPoint 휴리스틱 |
| 객체 애니메이션 | `none`(꺼짐) | `-a none`(sidecar 그룹 효과까지 모두 끔) | 켜는 법은 `-a auto`·`-a <효과>` 또는 sidecar |
| `auto`(R-15) | 그룹 id의 부분 문자열로 효과를 고름. 이미지 계열 id는 6개 풀을 순환 | | 규칙 본문은 C-13 |
| 시작 방식 | `after-previous`, 간격 0.5초 | | 같은 슬라이드에서 보통 한 방식을 쓰라는 것은 문서 권고 |

**(I) `main`의 오류 발생 순서.** 같은 입력에 오류가 둘이면 위의 것이 먼저 나온다.

| 순서 | 검사 | 종료 |
|---|---|---|
| 1 | 무결성(R-01), argparse | 78, 2 |
| 2 | 옵션 조합(R-04), `--animation-config` 빈 값 | 1 |
| 3 | 프로젝트 경로, `page_plan.json`(R-05) | 1 |
| 4 | `spec_lock.md` 존재, 언어, 구조 모드, theme, 이미지 옵션 범위(R-06, R-25) | 1 |
| 5 | canvas viewBox 선언, SVG 로스터(R-07, R-26) | 1 |
| 6 | **gate**(R-08) | 1 |
| 7 | 네이티브 마커 사전검사(`--native-charts-and-tables` 페이로드 등) | 1 |
| 8 | 출력 디렉터리 생성, 노트, 내레이션, **animations.json 로드·검증**(R-10~R-18) | 1 |
| 9 | 변환·검증·게시(R-19, R-20) | 1 또는 traceback |
| 10 | backup, postflight(R-21, R-22) | 1(게시된 파일 남음) 또는 0 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 어떤 경로로든 `svg_to_pptx.py`를 실행 | `attribution_guard`의 검사를 통과해야 진행한다. 조건은 `SKILL.md` frontmatter의 `copyright`·`license`·`official_repository` 값이 고정 문자열과 같고 `sponsors` 필드가 하나, `SKILL.md` 안에 `python3 "${SKILL_DIR}/scripts/attribution_guard.py"` 표식이 정확히 하나, `LICENSE`·`SPONSORS.md`·`SPONSORS_CN.md` 존재, `LICENSE`의 sha256 일치, 지정된 9개 스크립트 파일이 가드를 import·호출함, `console_encoding.py`의 보조 신원 검사 통과다. 실패하면 stderr에 한 줄 메시지를 내고 exit 78(보조 검사는 메시지 없이 78). 한 파일만 복사해 쓰면 실패할 수 있다 | 코드 확인(조건 목록). 실제 실행해 통과를 본 적은 없음(확인 한계). 부분 차용 시 취급은 적용 메모 |
| R-02 | 실행 시 `PPT_MASTER_PROJECT_PATH`, argv, CWD와 그 조상 중 `validation/workflow.log` 파일이 이미 있는 디렉터리가 있다 | stdout·stderr를 그 로그에 덧붙이는 tee가 붙는다(일부 줄은 요약·생략되며 세부 규칙은 읽지 않음). 환경변수 `PPT_MASTER_DISABLE_WORKFLOW_TRANSCRIPT`가 설정되면 하지 않는다. 로그 파일을 열 수 없으면 경고만 하고 계속. 로그가 없으면 아무것도 쓰지 않는다. 이 동작은 `main` 이전, wrapper import 시점에 설치된다 | 코드 확인 |
| R-03 | 알 수 없는 옵션, choices 밖 값, 음수 등 `type` 실패, 배타 옵션 동시 지정 | argparse 표준 오류와 exit 2. 어떤 파일도 쓰지 않는다 | 코드 확인 |
| R-04 | 옵션 조합 오류: `--inherit-motion-from`+(`--recorded-narration` 없음 또는 `--no-animations`), 호환 export+(`--roundtrip`·`--quick-generate`·`--pptx-structure`≠`flat`), `--quick-generate`+(`-s` 기본 외·`--pptx-structure`), 진단·호환 소스+`--pptx-structure`≠`flat`, `--no-animations`+전환·애니메이션 옵션 | `Error: …` stderr와 exit 1. 이후 단계는 실행되지 않는다. 진단 소스(`-s` 기본 외)와 호환 export는 구조가 `flat`으로 강제된다 | 코드 확인 |
| R-05 | 프로젝트 경로가 없다 / `page_plan.json`이 있는데 `--roundtrip`이 아니다 | 앞은 stdout에, 뒤는 stderr에 `Error:` 후 exit 1 | 코드 확인 |
| R-06 | 기본(release) 경로(`--quick-generate`·`-s` 기본 외·호환 export가 모두 아님) | `spec_lock.md`가 없으면 `Error: spec_lock.md is required for release SVG export` exit 1. 락에 `canvas.viewBox`가 없어도 exit 1. `## pptx_structure` 절의 `- mode:`가 없으면 경고 후 `flat`(구버전 락 호환), `flat`/`structured` 외 값은 마이그레이션 오류. `flat`·`structured`는 락에 theme 계약이 있어야 한다: `## typography`의 `font_family`(또는 `title_family`와 `body_family` 둘 다)와 `## colors`의 hex 색 행이 하나 이상. 없으면 누락 필드를 적어 exit 1. 언어는 `--primary-language` > 락의 `communication.primary_language` > 첫 페이지 루트 `lang` 순이고 모두 없으면 경고만 한다. 락의 행 형식은 `- key: value`다 | 코드 확인 |
| R-07 | SVG 소스 선택 | 소스는 `svg_output/`의 직계 `*.svg`를 숫자 파일명 순으로(선행 스펙 C-11). `-s`는 alias(`output`, `final`) 또는 하위 디렉터리 이름이고 `-s output`은 기본값과 같다. 요청한 디렉터리가 없거나 SVG가 0개면 폴백 없이 exit 1. `-s`가 기본 외이면 진단 소스로 취급: gate 미적용, 락 불필요, 구조 `flat`, backup 없음 | 코드 확인 |
| R-08 | gate | 적용 조건은 `(--quick-generate 이거나 -s가 없음/output) 이고 호환 export가 아님`. `--roundtrip`은 `-s`가 내부적으로 `authoring-svg-flat`으로 바뀌어 적용되지 않는다. 보고서 상태가 `passed`가 아니면 stderr에 상태명을 담은 오류와 재실행 명령을 내고 exit 1, 출력·backup·보고서는 없다. 판정 세부는 [선행 스펙](svg-authoring-and-quality.md)의 R-17·R-18·R-19·R-20을 따르고 여기서 다시 풀지 않는다 | 코드 확인 |
| R-09 | 출력 경로 | `-o`가 없으면 `<project>/exports/<name>_<타임스탬프>{접미사}.pptx`. `<name>`은 `parse_project_name`이 끝의 `_YYYYMMDD`와 `_<format>`을 떼어 낸 값(없으면 디렉터리 이름 전체). 접미사는 `_native_charts_tables`·`_narrated`·`_kiosk`가 이 순서로 조합된다. 타임스탬프는 `%Y%m%d_%H%M%S` 로컬 시각이라 같은 초에 두 번 실행하면 같은 경로가 되어 앞 파일이 덮어써질 수 있다 | 코드 확인(이름 규칙), 추론(같은 초 충돌: 덮어쓰기 방지 코드를 찾지 못함) |
| R-10 | 노트 | `--no-notes`가 아니면(Quick은 `--with-notes`가 있어야) `notes/*.md`를 읽는다. 매칭은 ①파일 stem이 SVG stem과 같음(우선) ②stem에서 `re.search(r'slide[_]?(\d+)')`가 찾은 번호가 n번째 SVG를 가리킴(`--roundtrip`이 아닐 때). 둘 다 맞으면 ①이 이기고 stderr에 안내. 내용이 공백뿐이면 건너뛴다. 읽기·디코딩 실패는 exit 1. 변환은 Markdown→평문(`#` 제목 줄은 텍스트+빈 줄, `- `는 `• `, `**`/`__` 굵게 제거). `total.md`처럼 어느 SVG에도 안 맞는 파일은 무시된다 | 코드 확인 |
| R-11 | sidecar 로드·검증 | `--no-animations`가 아니면 `--animation-config` 또는 `<project>/animations.json`(없으면 `None`, 에러 아님)을 읽는다. JSON이 object가 아니거나 `version`≠1이거나 JSON 오류면 `Error: Failed to load animation config`. 이어서 필드·값 검증(알 수 없는 필드, 효과·트리거·시간 범위 등)과 참조 검증을 하고 하나라도 오류면 모두 출력하고 exit 1. 변환·게시 전이라 PPTX는 없다 | 코드 확인 |
| R-12 | 설정 우선순위 | 같은 항목이 여러 곳에 있으면 CLI에서 명시한 값 > sidecar 슬라이드 > sidecar `defaults` > 내장 기본값. 전환: `-t`를 주면 모든 슬라이드의 sidecar `transition.effect`가 무시되고, `--transition-duration`·`--auto-advance`도 각각 같다. 객체 애니메이션: 슬라이드 `animation`의 `effect`·`duration`·`stagger`·`trigger`는 해당 CLI 플래그가 있으면 CLI가 이기며, `groups`의 row 필드는 그 위에서 row별로 우선한다 | 코드 확인 |
| R-13 | `-a none`을 명시 / `-a`를 생략 / `--no-animations` | `-a none` 명시: sidecar에 개별 그룹 효과가 있어도 모든 객체 애니메이션을 만들지 않는다(전환은 유지). `-a` 생략: 슬라이드 `animation.effect`가 `none`이어도 `groups`의 명시적 효과는 적용된다. `--no-animations`: 전환까지 `none`으로 만들고 sidecar를 읽지 않는다 | 코드 확인 |
| R-14 | 전환 기본 | 지정이 없으면 `fade`, 0.4초. `none`이면 `p:transition`을 쓰지 않되 `--auto-advance`가 있으면 타이밍은 쓴다. 효과가 `none`이 아니면 duration은 0보다 커야 한다(0이면 exit 1). 알 수 없는 효과는 다른 효과로 바뀌지 않고 오류다 | 코드 확인 |
| R-15 | 객체 애니메이션 기본·모드 | 기본 `none`. `auto`는 그룹 id를 소문자로 보아 이미지 키워드(`hero`·`figure-`·`image`·`img-`·`kpi`)면 6개 풀을 순환, 그 외 부분 문자열 패턴(title/chart/card- 등)이면 고정 효과, 아무것도 안 맞으면 4개 풀(fade·wipe·fly·zoom)을 순환한다. `mixed`는 첫 요소 `entrance_fade` 뒤 16개 풀을 순환, `random`은 같은 16개 풀에서 고른다. `random`의 시드는 (애니메이션 모드, sidecar 내용, SVG 파일 이름들)에서 정해져 같은 입력이면 같은 선택이다. 모드는 entrance만 고르고 emphasis·path·exit는 명시 키로만 쓴다 | 코드 확인 |
| R-16 | row 타이밍 | `order`로 정렬하고 같으면 SVG 그룹 순서, 그 다음 `effects[]` 인덱스. `order`를 안 쓴 그룹은 앞쪽에서 가장 가까이 명시된 order를 이어받는다. row `delay` 기본: `trigger_shape`가 있으면 0, `after-previous`이고 메인 시퀀스에 앞선 row가 있으면 `stagger`, 그 외 0. row `duration` 기본은 슬라이드 `animation` 값. `after-previous`·`with-previous`의 시작 기준 같은 의미 세부는 `scripts/docs/pptx-animations.md` §8 | 코드 확인(기본값·정렬), 의미 세부는 문서 |
| R-17 | sidecar 참조 | 슬라이드 키는 로스터의 SVG stem이어야 하고 없으면 `references missing slide`, 그룹 키는 그 SVG의 루트 직계 `<g>`의 id여야 하며 없으면 `references a missing group`, id가 중복이면 그 슬라이드는 오류, `data-pptx-layer` 그룹이나 숨은 그룹을 대상으로 하면 오류, 모두 export를 막는다. id 없는 직계 그룹은 경고만 한다. chrome 성격의 id(`background`, `header`, `footer`, `logo`, `watermark`, `rule` 등)는 scaffold·list-groups에서 빠지지만 sidecar에 명시하면 애니메이션할 수 있다. `trigger_shape`가 가리키는 그룹이 없으면 오류 | 코드 확인(참조 검증 함수 전체 열람), chrome id 목록은 문서·코드 상수 일부 |
| R-18 | morph | `slides.<id>.morph`가 있으면 같은 슬라이드에 `transition.effect: morph`가 명시돼야 하고, `from`은 비지 않은 stem, `pairs`는 비지 않은 object, 키는 공백·`!!` 접두·제어문자가 없는 이름, 같은 그룹이 두 키에 중복 배정될 수 없다. export가 쌍을 읽어 검증하고 실패하면 다른 방식으로 대체하지 않는다. 쌍을 선언한 도착 슬라이드의 해소된 전환이 "object 기준 Morph"가 아니면(예: CLI `-t push`가 모든 슬라이드에 전환을 덮어씀) 변환이 `ValueError`로 중단하고 `Error: animations.json slide "<stem>" declares deterministic Morph pairs, but the resolved transition is not Morph by object`를 출력해 exit 1이다 | 코드 확인(sidecar 검증, `builder.py:7687-7699` 직접 읽음) |
| R-19 | 변환 중 오류 | 슬라이드 변환에서 예외가 나면 PPTX는 게시되지 않는다. 그러나 오류 클래스에 따라 출력 모양이 다르다: `ValueError`(canvas 계약 위반 `CanvasContractError`, 값 검증 등)와 `TemplateStructureError`는 `Error: …` 한 줄과 exit 1. SVG가 DrawingML로 충실히 바뀌지 않을 때 쓰는 `SvgNativeConversionError`, 이미지 검증 실패, 패키지·전환·애니메이션 검증 실패(`RuntimeError`), 선택 의존성 누락은 모두 `RuntimeError` 계열이라 `main`의 `except (TemplateStructureError, ValueError)`에 잡히지 않아 Python traceback과 exit 1이다. `-q`가 아니면 traceback 직전에 `[n/N] <file>.svg - Error: <메시지>` 줄이 나온다. 임시 작업 디렉터리는 항상 지워진다 | 코드 확인 |
| R-20 | 게시 | 전체 슬라이드를 처리한 뒤 임시 zip을 만들고 `Content_Types`·관계 대상 검증(`verify_internal_relationships`), 전환 패키지·Morph 쌍·애니메이션 패키지 검증을 통과해야 `shutil.move`로 출력 경로에 옮긴다. 하나라도 실패하면 출력 경로에는 새 파일이 없다. trace는 게시 뒤에 쓴다 | 코드 확인 |
| R-21 | postflight | 게시 뒤 검사는 둘뿐이다: 출력이 읽을 수 있는 ZIP이고 `testzip`이 통과, `ppt/slides/slide*.xml` 개수가 SVG 개수와 같음. 하나라도 실패하면 보고서는 쓰지 않고 `Error: generated PPTX failed postflight validation and must not be used`와 `Invalid output remains at: <경로>`를 내고 exit 1이며 PPTX는 남는다. 통과하면 `validation/<stem>.report.json`을 쓴다. `status`는 gate가 `failed`면 `failed`, 아래가 모두 깨끗하면 `passed`, 아니면 `passed-with-warnings`다: gate `passed`, 미해결 `{{token}}` 없음, `://` 외부 이미지 없음, 제네릭 전용 폰트 스택 없음, 비안전 폰트 face 없음, gate의 introduced 경고 0, 호환 export 아님. `checks`의 나머지 항목(`transitions`, `animations`, `project_svg_contract` 등)은 검사 결과가 아니라 고정 문자열 `enforced-at-build`다. 보고서 쓰기가 `OSError`로 실패해도 exit 1이고 PPTX는 남는다 | 코드 확인 |
| R-22 | backup | 변환이 성공했고 `-o`가 없고 진단 소스가 아니면 `svg_output/`을 `backup/<타임스탬프>/svg_output/`로 통째 복사한다. 복사 실패는 경고만 하고 계속(결과 exit 0). 네이티브 payload store 파일이 있으면 `backup/<ts>/` 아래 같은 상대 경로에 복사한다. 복사는 postflight보다 앞이라 postflight가 실패해도 backup은 남는다 | 코드 확인 |
| R-23 | trace | `--conversion-trace`가 없고 호환 export도 아니면 trace를 쓰지 않는다. PATH 없이 주면 `validation/<출력 stem>.trace.json`, 상대 PATH는 프로젝트 루트 기준, 절대 PATH는 그대로. 내용은 `{output, slide_count, project_contract.mode, slides[]}`이고 슬라이드 항목에 해석된 전환·애니메이션이 들어 있다. postflight 보고서의 `conversion_trace_path`는 파일이 실제로 있을 때만 채운다 | 코드 확인 |
| R-24 | `-q` | 진행 출력과 `[POSTFLIGHT]`·`[PPTX]`·`[REPORT]` 요약이 나오지 않는다. 오류 메시지는 나온다. 그러므로 `-q`로 실행한 호출자는 PPTX 경로를 출력에서 얻을 수 없고 `exports/` 목록이나 보고서로 찾아야 한다 | 코드 확인 |
| R-25 | 이미지 | `<image>`에는 `href`(또는 `xlink:href`)가 정확히 하나 필요하고 `width`·`height`는 양수여야 한다. 외부 href는 해당 SVG 기준 상대 경로로만 풀리고 프로젝트 밖이거나 파일이 없으면 변환 오류(R-19)다. 지원 확장자는 bmp·emf·gif·jpg/jpeg·png·svg·tif/tiff·webp·wmf이고 내용이 확장자와 맞는지 검증한다. 래스터 검증과 최적화는 Pillow가 필요하며 Pillow가 없으면 래스터 이미지는 검증 실패다. 기본 `cap`은 가장 긴 변이 `--image-max-dimension`(2560)을 넘거나 EXIF 방향 보정이 필요할 때만 재인코딩하고 그 외는 원본 바이트를 쓴다. 애니메이션 GIF·WebP는 원본 그대로 둔다 | 코드 확인(검증·분기), 크기 계산식 `_fit_full_image_target`은 열지 않음 |
| R-26 | canvas | 모든 페이지의 viewBox가 같아야 한다. 락이 있으면 락의 `canvas.viewBox`와도 같아야 하고, `-f`를 주면 그 포맷의 viewBox와도 같아야 하며(락과 `-f`가 다르면 오류), 어긋나면 `CanvasContractError`(exit 1, `Error:`). 슬라이드 크기는 viewBox px × 9,525 EMU(= 914,400/96) | 코드 확인 |
| R-27 | 문서 속성 | `<project>/metadata.json`이 object이면 `title`·`subject`·`creator`·`keywords`·`description`·`language`·`category`·`contentStatus`·`company`·`manager`를 `docProps`에 쓴다(문자열이고 비어 있지 않을 때만). 파일이 깨졌거나 object가 아니면 경고 후 무시한다. 슬라이드 수·내보낸 시각·형식은 항상 기계가 채운다. 없으면 제목 등은 빈 값이다. 이 파일은 파이프라인의 어느 단계도 만들지 않는 선택 입력이라 호출자가 필요하면 직접 만든다 | 코드 확인(생성 코드·문서 모두 찾지 못함, 2.1) |
| R-28 | 차트·표·수식 | 기본 export는 차트·표 마커 그룹도 SVG에서 만든 DrawingML 도형으로 낸다. `--native-charts-and-tables`가 있어야 `data-pptx-replace-with` 마커가 네이티브 Chart/Table 개체로 바뀐다(검증 실패 시 exit 1, 폴백 전용 객체는 도형으로 낸다는 경고). 수식 마커는 옵션과 무관하게 항상 네이티브 Office Math로 나가고 `mc:Fallback`에 도형 대체를 둔다(문서 주장) | 코드 확인(옵션 분기), 수식 부분은 문서 주장(미확인) |
| R-29 | 호출만 있는 옵션 | `--roundtrip`, 호환 export, 내레이션 옵션, `--pptx-structure`는 이 스펙이 규약만 다룬다. 내레이션: `--recorded-narration`은 오디오 디렉터리가 없거나 슬라이드마다 오디오가 없으면 exit 1, 온클릭 객체 애니메이션과 함께 쓰면 exit 1 | 코드 확인(조건만) |
| R-30 | 비교 불변성 | 같은 입력으로 두 번 실행해도 파일 이름의 타임스탬프와 `docProps`의 내보낸 시각이 달라 PPTX 바이트는 같지 않다. 내용 선택(`random` 효과 등)은 R-15대로 결정적이다 | 코드 확인(타임스탬프), 바이트 비교는 하지 않음 |
| R-31 | `pptx_delivery_check.py` | `svg_to_pptx`는 호출하지 않는다. 완성된 PPTX 하나를 받아 읽기 전용으로 점검해 JSON을 stdout에 내고 `status`가 `failed`면 exit 1인 별도 CLI다. Default 생성 파이프라인의 Step 7은 이 CLI를 부르지 않고, Edit Native PPTX 문서가 부른다 | 코드 확인(호출처 검색 범위는 2.1) |

- 불변식: 출력 경로에 새 PPTX가 있으면 임시 zip이 검증을 통과한 것이다(R-20). 단 그 PPTX가 postflight(R-21)까지 통과했다는 뜻은 아니다. exit 1이면서 PPTX가 있을 수 있는 유일한 경우가 postflight 실패와 postflight 보고서 쓰기 실패다. exit 0이면 PPTX와 `report.json`이 둘 다 있다.
- 미결정: 없음

- 확인 한계: 실행하지 않았다(의존성·무실행 규칙). 위 동작은 모두 코드 읽기에서 도출했고 실제 출력·exit code는 확인하지 못했다. `builder.py` 8,810줄·`elements.py` 5,719줄·`native_objects/` 등 변환 내부는 열지 않았고(호출 규약에 필요한 줄만 열람), 효과별 옵션·전환별 옵션 값은 레지스트리 JSON·`--describe` 출력을 보지 않았다. 외부 시스템(PowerPoint가 결과 파일을 어떻게 여는지)은 확인하지 못했다.

### 1.5 필수 코드 참조 [필수]

라이선스는 MIT(overview 1절)이므로 인용 가능. 아래 영역의 **내부는 이 스펙에서 풀지 않는다**. "풀이 범위"가 "호출 규약만"이면 위치 안내만 하고 내부 규칙은 읽는 사람이 해당 코드를 열어야 한다. 각 경로는 `skills/ppt-master/scripts/` 아래다.

| C-ID | 알고 싶은 것 | 파일:줄 범위 · 심볼 (크기) | 가져갈 것·형식 / 풀이 범위 | 관련 R-ID |
|---|---|---|---|---|
| C-01 | CLI 진입(wrapper)과 공개 API | `skills/ppt-master/scripts/svg_to_pptx.py:1-31`, `skills/ppt-master/scripts/svg_to_pptx/__init__.py:1-37` (31줄, 37줄) | 호출 형식, lazy import. 전부 읽어도 됨 | R-01 |
| C-02 | CLI 옵션 정의(이름·기본값·choices·배타 그룹) | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:1996-2353` `main`의 argparse 구간 (358줄) | 옵션 표(1.3 B)의 원본. 그대로 옮겨 가도 되는 선언 코드. 호출 규약은 이 스펙, 인자 해석 이후는 아래 C-03 이하 | R-03 |
| C-03 | 옵션 조합 검사, 사전 조건, 출력 경로, canvas, SVG 로스터 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2354-2770` (417줄) | 오류 메시지와 exit 1 분기 순서(1.3 I). 분기가 많고 roundtrip·quick·진단 모드가 섞여 있어 이 스펙은 기본·Quick·진단 경로만 풀고 roundtrip 분기(2402-2420, 2455-2481, 2557-2582, 2714-2719)는 풀지 않음 | R-04~R-09, R-26 |
| C-04 | 품질 gate 적용 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3160-3186`, `:1251-1347` | 선행 스펙 C-08~C-10과 같은 코드. 다시 풀지 않음 | R-08 |
| C-05 | 노트·내레이션·animations.json 로드와 설정 해석 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3322-3741` (420줄) | 오류 분기, CLI>sidecar>기본값 우선순위 코드. narration 분기(3335-3395, 3743-3765)는 제외 범위 | R-10~R-16 |
| C-06 | 빌더 호출, backup, postflight, 보고서 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3767-3953`, `:1412-1567`, `:1176-1248` (합 약 500줄) | 게시 이후 흐름과 보고서 키 목록의 원본. 전부 읽어도 됨 | R-21~R-24, R-27 |
| C-07 | 패키지 조립 전체(빈 base → 슬라이드 → 검증 → 게시) | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:6791-8810` `create_pptx_with_native_svg` (2,020줄). 이정표: canvas 7102, 임시 디렉터리 7266, base 7296, 슬라이드 루프 시작 7393, 변환 호출 7769, 슬라이드 XML 8050, 관계 검증 8664, 재패키징 8692, 패키지 검증 8722-8756, 게시 8758, trace 8761-8776, 반환 8807 | 흐름 이정표만. 내부 규칙(6791행 앞의 약 6,600줄 보조 함수 — roundtrip·템플릿·구조형 — 와 함수 본문 전체)은 이 스펙에서 풀지 않음 | R-19, R-20, R-26 |
| C-08 | 슬라이드 하나의 SVG→DrawingML 변환 진입 | `skills/ppt-master/scripts/svg_to_pptx/drawingml/converter.py:2032-2615` `convert_svg_to_slide_shapes` (584줄). 반환: `(slide_xml, media_files, rel_entries, anim_targets, package_files, content_type_overrides)`. 요소 분기 `:1883-1977` `convert_element`, 그룹 `:1209-1546` `convert_g` | 입력(SVG 경로, 옵션)과 반환 튜플 형식만. 내부 변환 규칙은 풀지 않음 | R-19 |
| C-09 | 도형·텍스트·이미지 요소별 변환 | `skills/ppt-master/scripts/svg_to_pptx/drawingml/elements.py` (5,719줄): `convert_rect` 1278, `convert_circle` 1483, `convert_line` 1644, `convert_path` 1811, `convert_polygon` 1899, `convert_polyline` 1976, `convert_text` 3189-3798(610줄), `convert_image` 4983-5140(158줄), `convert_ellipse` 5141, `convert_nested_svg` 5600-5719 | 위치 안내. 풀이 없음 | — |
| C-10 | 스타일·경로·텍스트 속성·하이퍼링크·theme | `skills/ppt-master/scripts/svg_to_pptx/drawingml/styles.py`(782줄), `paths.py`(847줄), `text_properties.py`(796줄), `hyperlinks.py`(162줄), `theme_colors.py`(283줄), `theme_fonts.py`(502줄), `utils.py`(3,886줄) | 위치 안내. 풀이 없음. SVG↔PowerPoint 대응표는 레포 `docs/powerpoint-svg-mapping.md`(354줄)가 이미 있으니 그 문서를 연다(옮겨 적지 않음) | — |
| C-11 | 차트·표·수식 | `skills/ppt-master/scripts/svg_to_pptx/native_objects/__init__.py:744-786` `convert_native_object`(진입), 같은 디렉터리의 `chart_xml.py`(1,741줄), `chart_data.py`(1,711줄), `chart_style.py`(1,696줄), `table.py`(2,058줄), `formula*.py`(7개, 합 5,185줄), `workbook.py`(216줄). 패키지 합 16,160줄 | 진입 위치만. 풀이 없음. 수식 LaTeX 컴파일 확인 명령은 `scripts/docs/svg-pipeline.md` "Native formula compiler" | R-28 |
| C-12 | 프리셋 도형 데이터(C5)와 이를 쓰는 곳 | `skills/ppt-master/scripts/pptx_shapes/`(py 합 2,366줄, 데이터 `data/presetShapeDefinitions.xml` 19,898줄, `data/presetShapeSemantics.json` 1,217줄), 소비처: `svg_to_pptx/drawingml/{converter,elements,styles,utils}.py`, `native_objects/{__init__,fallback_hash}.py`. 각 데이터 파일은 별도 라이선스(`data/LICENSE-*`) | 위치 안내. 풀이 없음 | — |
| C-13 | 객체 효과 레지스트리·`-a auto/mixed/random` 선택 규칙 | `skills/ppt-master/scripts/pptx_animations.py:101-131`(호환 별칭 29), `:219-371`(로더, 개수 강제), `:375-384`(`ANIMATIONS`·모드·트리거 상수), `:1040-1119`(풀·의미 패턴), `:2001-2055`(`pick_animation_effect`), 시퀀스 XML `:1850-2000`, 검증 `:3192-3558`, CLI `:3797-3869`. 데이터 `pptx_animation_presets.json`(3,440줄) | `auto/mixed/random`의 선택 규칙은 `:1040-1119`와 `:2001-2055`가 글보다 짧고 정확하니 그대로 읽는다. XML 작성기 내부는 풀지 않음 | R-15, R-16 |
| C-14 | 전환 레지스트리·XML | `skills/ppt-master/scripts/pptx_transitions.py:66-67`(기본 시간·상한), `:73-455`, `:816-884`(48개 레지스트리, 호환 별칭), `:979-1002` `validate_seconds`, `:1282-1391` `create_transition_xml`, `:2317-2455` `validate_generated_transition_xml`, `:2627-2693` `validate_pptx_transition_package`, `:2712-2859` `validate_pptx_morph_pairs` (파일 3,204줄) | 위치 안내. XML 규칙은 풀지 않음. 문서: `scripts/docs/pptx-transitions.md`(333줄) | R-14, R-18 |
| C-15 | sidecar 로드·검증·scaffold | `skills/ppt-master/scripts/svg_to_pptx/animation_config.py:436-457`(로드), `:710-748`·`:750-824`(전환 검증), `:826-933`(morph), `:1049-1291`(애니메이션 검증, 허용 필드 `:52-63`), `:1570-1789`(참조 검증), `:1813-1910`(scaffold·list-groups), 파일 1,910줄. CLI wrapper `skills/ppt-master/scripts/animation_config.py:1-160` | 필드·오류 규칙의 정본. 1.3 (G)가 이 코드의 요약이고 충돌하면 코드가 기준. 그룹 스캔(`:257-333`)·chrome id 판정은 풀지 않음 | R-11, R-17, R-18 |
| C-16 | 설정 우선순위의 슬라이드 단위 해석, 시퀀스 대상 생성 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:5770-5906`(`_slide_transition_settings`·`_slide_animation_settings`), `:5908-6152` `_build_sequence_targets`, `:7705-7708`(`-a none` hard disable) | row 정렬·기본 delay·상속 필드 코드가 글보다 정확하니 읽는다 | R-12, R-13, R-16 |
| C-17 | 발표자 노트 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/discovery.py:61-135` `find_notes_files`, `notes.py:17-63` `markdown_to_plain_text`, `builder.py:2152-2216` `_apply_slide_notes`, 노트 XML `notes.py:64-184` | 매칭·변환 규칙은 R-10에 있음. 노트 XML 구조는 풀지 않음 | R-10 |
| C-18 | 이미지 처리·크기 제한 | `skills/ppt-master/scripts/svg_to_pptx/drawingml/elements.py:104-121`(경로 해석), `:289-318`(내용 검증), `:375-416`(`load_project_image_source`), `:4589-4691`(`_fit_full_image_target`), `:4730-4803`(`_optimize_image_for_pptx`) | 해석·검증 규칙은 R-25. 크기 계산식은 풀지 않음 | R-25 |
| C-19 | canvas·프로젝트 이름 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/dimensions.py:139-189` `resolve_svg_canvas`, `skills/ppt-master/scripts/project_utils.py:111-167` `parse_project_name`, `skills/ppt-master/scripts/config.py:166-` `CANVAS_FORMATS` | 짧고 자기완결적이라 그대로 읽어도 됨 | R-09, R-26 |
| C-20 | 패키지 구조 검증, 관계 검증, 완성 파일 점검 | `skills/ppt-master/scripts/pptx_opc_validation.py:265-346` `verify_internal_relationships`(파일 346줄), `skills/ppt-master/scripts/pptx_delivery_check.py:727-1150` `audit_pptx_delivery`·`:1153-1170` CLI(파일 1,170줄), 템플릿 구조 검증 `svg_to_pptx/pptx_package/template_structure.py`(3,759줄)·`template_validation.py`(1,536줄) | `pptx_delivery_check`는 호출 규약만(R-31). 템플릿 구조 검증은 제외 범위 | R-20, R-31 |
| C-21 | 무결성 가드, 로그 tee | `skills/ppt-master/scripts/attribution_guard.py:25-205`, `skills/ppt-master/scripts/console_encoding.py:11-88`, `skills/ppt-master/scripts/workflow_transcript.py:27-30,85-96,302-347` | 조건 목록은 R-01·R-02. 부분 차용 시 반드시 읽어야 하는 코드 | R-01, R-02 |
| C-22 | 사용 문서 | `skills/ppt-master/scripts/docs/svg-pipeline.md:884-1137`(`svg_to_pptx.py` 절 254줄), `skills/ppt-master/scripts/docs/pptx-animations.md`(320줄, §8 sidecar 필드), `skills/ppt-master/references/animations.md`(263줄), `docs/powerpoint-svg-mapping.md`(354줄) | 문서는 구현과 어긋날 수 있어 2.1의 차이를 먼저 본다 | R-11~R-18 |

### 1.6 수락 사례 [필수]

출처: 모두 구현 읽기에서 도출(실행·원본 테스트 미열람). `<P>`는 프로젝트 디렉터리, "gate 통과"는 `<P>/validation/svg_quality_report.json`이 현재 `svg_output/`에 대해 `passed`라는 뜻이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-06, R-08, R-09, R-21, R-22 | `<P>`=`projects/deck_ppt169_20261117`, `spec_lock.md`(viewBox·theme·mode 있음), SVG 3장, gate 통과, 옵션 없음 | exit 0. `exports/deck_<YYYYMMDD_HHMMSS>.pptx`, `validation/deck_<…>.report.json`(`status` `passed` 또는 `passed-with-warnings`, `package.slides`=3), `backup/<…>/svg_output/` 3장. 콘솔에 `[POSTFLIGHT]`·`[PPTX]`·`[REPORT]` |
| T-02 | R-06, R-08 | `<P>/spec_lock.md` 없음, gate 보고서도 없음, 옵션 없음 | `Error: spec_lock.md is required for release SVG export` exit 1(gate 오류보다 먼저). 어떤 출력도 없음 |
| T-03 | R-08 | gate 통과 후 SVG 한 장을 한 글자 수정하고 옵션 없이 실행 | 선행 스펙 T-03과 같은 `stale` 오류와 재실행 명령, exit 1, 새 PPTX·backup·보고서 없음 |
| T-04 | R-12, R-14 | `animations.json`에 슬라이드별 `transition.effect`가 다르고 `-t push --transition-duration 1.0`으로 실행 | 모든 슬라이드가 `push` 1.0초(sidecar의 슬라이드별 전환 무시) |
| T-05 | R-14 | `-t none --auto-advance 5` | `p:transition` 시각 효과는 없고 자동 넘김 5초 타이밍은 기록됨, exit 0 |
| T-06 | R-14 | `-t fade --transition-duration 0` | `Error:`(duration은 0보다 커야 함) exit 1 |
| T-07 | R-13 | sidecar에 `groups.card-1.effects[{effect: entrance_fade}]`, `-a` 없이 실행 / `-a none`으로 실행 | 앞은 `card-1`에 entrance_fade 시퀀스가 생기고, 뒤는 객체 애니메이션이 하나도 없음(전환은 유지) |
| T-08 | R-13 | `--no-animations -t push` | `Error: --no-animations cannot be combined with transition or object-animation overrides.` exit 1 |
| T-09 | R-11, R-17 | sidecar `slides`에 SVG stem에 없는 `"99_nope"` 키, gate 통과 | `animations.json references missing slide: 99_nope` 오류로 exit 1, PPTX 없음. `animation_config.py validate`도 같은 오류, exit 1 |
| T-10 | R-11 | sidecar 슬라이드 객체에 알 수 없는 키 `"groupz"` | `animations.json slide "…" has unknown field: groupz` exit 1 |
| T-11 | R-19, R-25 | SVG의 `<image href="../images/missing.png">` 파일 없음 | `[n/N] 03.svg - Error: …`(비 `-q`) 후 traceback, exit 1, `exports/`에 새 파일 없음 |
| T-12 | R-09, R-22 | `-o /tmp/out.pptx`로 실행 | `/tmp/out.pptx` 생성, `<P>/exports/`에 새 파일 없음, `<P>/backup/` 새 폴더 없음, 보고서는 `<P>/validation/out.report.json` |
| T-13 | R-07, R-08 | `-s final`(svg_final 존재), 락 없음 | gate·락 검사 없이 `svg_final/`을 변환, 구조 `flat`, backup 없음. 보고서 `quality_gate`는 비통과로 기록되어 `status`가 `passed-with-warnings` 또는 `failed`, exit 0 |
| T-14 | R-10 | `notes/03_x.md`와 `notes/slide03.md`가 둘 다 있고 SVG 3번째가 `03_x.svg` | `03_x.md`가 쓰이고 stderr에 `Note: 03_x.svg uses filename-matched notes … instead of index-matched …` |
| T-15 | R-24 | 성공 케이스를 `-q`로 실행 | PPTX·보고서는 만들어지지만 `[POSTFLIGHT]`·`[PPTX]`·`[REPORT]` 출력 없음, exit 0 |
| T-16 | R-01 | `SKILL.md`의 `license:` 줄 값을 바꾸고 실행 | stderr `PPT Master skill integrity check failed…`, exit 78 |
| T-17 | R-25, 환경 | Pillow 미설치, SVG가 PNG를 참조 | 이미지 검증 실패(`invalid project image`), R-19 형태로 exit 1. SVG 이미지만 쓰는 덱은 영향 없음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `skills/ppt-master/scripts/svg_to_pptx.py:23-31`, `skills/ppt-master/scripts/attribution_guard.py:25-205`, `skills/ppt-master/scripts/console_encoding.py:59-66`, `:82-88`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:1986` | 상수·함수 전체 열람. 실행하지 않아 통과 여부는 미확인(확인 한계). exit 78은 `attribution_guard.py:205`와 `console_encoding.py:66`에서 직접 확인. 9개 필수 파일 목록은 `attribution_guard.py:41-51` |
| R-02 | `skills/ppt-master/scripts/workflow_transcript.py:27-30`, `:85-96`, `:302-347`, `skills/ppt-master/scripts/svg_to_pptx.py:27`, `skills/ppt-master/scripts/console_encoding.py:82-88` | 로그 요약·생략 규칙(`_CRITICAL_MARKERS` 등)은 읽지 않음. 생성 주체는 C1 스펙(1.3.5)의 인용으로 `init`이 첫 기록을 씀(직접 열람 안 함). 검색: `grep -rn "workflow.log\|WORKFLOW_LOG_RELATIVE_PATH" scripts --include='*.py'`(tests 제외)에서 `workflow_log.py`와 `workflow_transcript.py`만 나옴. 놓쳤을 가능성: 다른 확장자·셸 스크립트·문서의 생성 지시 |
| R-03 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2130-2158`, `:2230-2245`, `:2285-2318` | argparse 종료 코드 2는 표준 라이브러리 동작이고 코드에서 `SystemExit`를 재정의하지 않음을 확인 |
| R-04 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2354-2449`, `:3397-3413` | 전체 열람 |
| R-05 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2451-2481` | 경로 없음 메시지가 `print(...)`(stdout)임을 확인 |
| R-06 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:958-970`, `:1642-1717`, `:2488-2632`, `skills/ppt-master/scripts/svg_to_pptx/drawingml/theme_fonts.py:166-208`, `skills/ppt-master/scripts/svg_to_pptx/drawingml/theme_colors.py:124-212` | `parse_lock`(`update_spec.py`)의 파싱 규칙은 열지 않음. theme 필드는 위 두 함수가 읽는 행 형식 `- key: value`와 절 이름 `typography`·`colors`로 확인 |
| R-07 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/discovery.py:16-58`, `skills/ppt-master/scripts/slide_roster.py:45-47`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2422-2449`, `:2736-2770` | 선행 스펙 C-11과 같은 로스터 |
| R-08 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3160-3186`, `:2402-2420` | 판정 본문은 선행 스펙을 인용. `--roundtrip`은 `args.source`가 2419행에서 `authoring-svg-flat`으로 바뀌어 3162행 조건이 거짓이 됨(선행 스펙 U-03의 전제 정정, 2.1 아래 표) |
| R-09 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2682-2712`, `skills/ppt-master/scripts/project_utils.py:111-237` | 이름 파싱 규칙은 전체 열람. 같은 초 충돌 방지 코드 검색은 `cli.py` 2691-2712와 `builder.py:8758` `shutil.move` 확인으로 갈음했고 전체 파일 검색은 안 함. `shutil.move`가 기존 경로를 덮어쓰는 것은 표준 동작에 기댄 추론 |
| R-10 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/discovery.py:61-135`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/notes.py:17-63`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2439-2440`, `:3326-3333`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:2152-2216` | 전체 열람. `slide_(\d+)` 매칭은 stem 어디서든 `re.search`로 찾음에 유의 |
| R-11 | `skills/ppt-master/scripts/svg_to_pptx/animation_config.py:436-457`, `:1049-1091`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3415-3494`, `skills/ppt-master/scripts/animation_config.py:120-153` | 검증 함수 열람. 값 범위의 세부(`_animation_parameter_errors` 533-683, `_resolved_animation_parameter_errors` 1325-1423)는 읽지 않음 |
| R-12 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:5770-5906`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3521-3741` | `cli_overrides` 플래그가 CLI 지정 여부로만 켜지는 것을 `cli.py:3691-3722`에서 확인 |
| R-13 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:7705-7708`, `:7862-7870`, `:5971-5974`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3529-3532`, `:3446-3453` | `references/animations.md` §2 표와 같다 |
| R-14 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3528-3614`, `skills/ppt-master/scripts/pptx_transitions.py:66-67`, `:979-1002` | `none` 전환의 `p:transition` 생략·타이밍 유지는 `builder.py:7842-7861`의 `create_transition_xml` 호출 조건(`slide_transition is not None or slide_auto_advance is not None or …`)으로 확인 |
| R-15 | `skills/ppt-master/scripts/pptx_animations.py:1040-1119`, `:2001-2055`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:7418-7431` | 풀·패턴·시드 생성 전체 열람 |
| R-16 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:5908-6152` | 정렬·delay 기본·상속 필드 열람. 시작 시점 의미(beat 계산)는 `pptx-animations.md` §8 문서만 읽음 |
| R-17 | `skills/ppt-master/scripts/svg_to_pptx/animation_config.py:257-333`, `:1570-1789`, `:1145-1210`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3477-3494` | 경고(`has no id`)와 오류의 분류는 `cli.py:3483-3490`의 문자열 필터로 확인. chrome id 목록은 `animation_config.py:64-82`(상수) |
| R-18 | `skills/ppt-master/scripts/svg_to_pptx/animation_config.py:826-933`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:7041`, `:8731-8736`, `skills/ppt-master/scripts/pptx_transitions.py:2712-2859` | 도착 슬라이드의 전환 불일치 오류(`builder.py:7687-7699`)와 `resolve_morph_pairs`(`svg_to_pptx/animation_config.py:1036-1046`)는 직접 읽음. `validate_pptx_morph_pairs` 본문은 읽지 않음 |
| R-19 | `skills/ppt-master/scripts/svg_to_pptx/drawingml/converter.py:138-139`, `:288-308`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3869-3879`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:8330-8335`, `:8722-8756`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/template_structure.py:179`, `skills/ppt-master/scripts/svg_to_pptx/canvas_contract.py:13` | 예외 클래스의 상속(`SvgNativeConversionError(RuntimeError)`, `CanvasContractError(ValueError)`, `TemplateStructureError(RuntimeError)`)과 `main`의 `except` 절을 대조. 주의: `TemplateStructureError`는 `RuntimeError`지만 `except` 절에 이름으로 들어 있어 잡힌다. 슬라이드 단위 변환 오류가 모두 `RuntimeError`인지는 `converter.py` 전체 `raise`를 훑지 않았고, 열람한 `_require_*` 계열과 `SvgNativeConversionError`만 확인 |
| R-20 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:8664-8776`, `:7266`, `:5423-5465` | 전체 열람 |
| R-21 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:1156-1175`, `:1412-1567`, `:3915-3953` | 전체 열람. 문서(overview 3절)가 말하는 "postflight 검증"의 실체가 두 검사뿐임을 정정 |
| R-22 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2693-2712`, `:3883-3913` | 전체 열람. 복사가 `svg_output/` 아래 중첩(`backup/<ts>/svg_output/`)임 |
| R-23 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3852-3868`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:8761-8776`, `:7432` | trace 내부 필드는 열지 않음 |
| R-24 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3324`, `:3950-3951` | 전체 열람 |
| R-25 | `skills/ppt-master/scripts/svg_to_pptx/drawingml/elements.py:104-121`, `:289-318`, `:375-470`, `:4730-4803`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2672-2680` | `_fit_full_image_target` 4589-4691의 계산식은 읽지 않음. 지원 확장자는 `elements.py:124-148` 딕셔너리 |
| R-26 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/dimensions.py:139-189`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2721-2732`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:7102` | `EMU_PER_PIXEL`은 `dimensions.py:33` |
| R-27 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3767-3788`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:6432-6510` | `metadata.json`을 설명하는 문서는 `grep -rn "metadata.json" --include='*.md' skills/ppt-master`(templates·icons 하위 제외)에서 찾지 못함. 놓쳤을 가능성: `templates/` 하위 문서와 스크립트 주석. 추가 확인(메인): `grep -rn "metadata\.json" skills/ppt-master/scripts skills/ppt-master/references skills/ppt-master/workflows skills/ppt-master/templates docs`(tests·`image_manifest`·`brands_index` 제외)에서 `pptx_package/cli.py`와 `builder.py`의 읽기 코드·주석만 나왔다. 쓰기 코드와 문서는 없음 |
| R-28 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2169-2187`, `:2704`, `:3268-3320`, `skills/ppt-master/scripts/docs/svg-pipeline.md:884-1137` | 수식 "항상 네이티브" 서술은 문서에서만 읽음 |
| R-29 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:3335-3395`, `:3743-3765`, `:2380-2400` | 조건 분기만 열람 |
| R-30 | `skills/ppt-master/scripts/svg_to_pptx/pptx_package/cli.py:2691`, `skills/ppt-master/scripts/svg_to_pptx/pptx_package/builder.py:6432-6470` | 바이트 비교 실행은 없음 |
| R-31 | `skills/ppt-master/scripts/pptx_delivery_check.py:1153-1170`, `skills/ppt-master/workflows/edit-native-pptx.md:161` | 검색: `grep -rn "pptx_delivery_check" skills/ppt-master/scripts --include='*.py'`에서 자기 자신과 tests만 나오고, `svg_to_pptx` 패키지에서는 호출이 없음. 문서 검색(`workflows`, `references`, `SKILL.md`, `scripts/docs`, `docs`, `README.md`)에서 `edit-native-pptx.md`와 `svg-pipeline.md:326`만. 놓쳤을 가능성: 셸 호출, 다른 문서 경로 |
| T-01~T-17 | 해당 R-ID의 근거 줄에서 도출 | 모두 실행하지 못함. T-13은 보고서 `status`를 코드에서 계산해 도출 |

**"없다·전부다" 주장과 검색.** (1) "python-pptx는 빈 base 생성에만 쓰인다": `grep -rnE "^\s*(from pptx(\.| )|import pptx\b)" skills/ppt-master/scripts --include='*.py'`(tests 제외)에서 `svg_to_pptx` 패키지는 `builder.py:28` 하나만 나오고 쓰임은 `:7296` `Presentation()`·`prs.save`. 라운드트립 복제 경로(`pptx_ooxml.clone`)는 python-pptx가 아니다. 동적 import는 찾지 못함. (2) "`pptx_shapes`를 쓰는 곳": `grep -rn "pptx_shapes\|preset_shape_svg" skills/ppt-master/scripts/svg_to_pptx --include='*.py'`가 `native_objects/{__init__,fallback_hash}.py`, `drawingml/{utils,elements,converter,styles}.py`를 돌려줌. (3) "`-a` 생략·`-a none` 구분": `builder.py:7705-7708` 단일 위치, 다른 위치에서 `animation_cli_overrides['animation']`를 읽는지는 `cli.py:3706-3709` 외에 검색하지 않음.

**문서·구현·기존 문서의 차이**(구현을 사실로 썼다).

| 문서 | 문서의 말 | 구현 |
|---|---|---|
| 선행 스펙 U-03, overview 3절 | `--roundtrip` 내보내기에서도 gate가 적용될 수 있다는 전제 | `args.roundtrip`이면 `args.source`를 `authoring-svg-flat`으로 바꾸므로(`cli.py:2419`) `release_quality_gate`는 거짓(`cli.py:3160-3163`). gate는 적용되지 않는다 |
| overview 3절 | 성공하면 `svg_output/`을 `backup/<timestamp>/`에 복사 | `backup/<timestamp>/svg_output/`로 중첩 복사하고(`cli.py:3891`), `-o`나 기본 외 `-s`가 있으면 복사하지 않는다(`cli.py:2711-2712`) |
| overview 3절, `generate-pptx.md` Step 7.3 | postflight 검증 실패 시 종료하고 파일은 남는다. 성공 기준은 보고서 `passed`/`passed-with-warnings` | 맞다. 다만 "postflight 검증"이 확인하는 것은 ZIP 무결성·슬라이드 수 둘뿐이고 나머지 `checks`는 `enforced-at-build` 문자열이다. gate를 적용하지 않은 경로에서는 보고서 `status`가 `failed`여도 exit 0이다(`cli.py:1458-1459`, `:3953`) |
| `scripts/docs/svg-pipeline.md` (svg_to_pptx 절) | `metadata.json` 설명 없음 | 구현은 `metadata.json`을 읽는다(`cli.py:3769`). 문서에서 설명을 찾지 못함(R-27) |

### 2.2 코드 읽는 순서 [선택]

1. `svg_to_pptx.py` → `svg_to_pptx/pptx_package/cli.py` `main`(1984~): 1.3 (I) 순서표를 옆에 두고 C-02~C-06을 위에서 아래로 읽는다. 호출 규약은 여기서 끝난다.
2. 변환 내부가 필요하면 `builder.py:6791`의 이정표(C-07) → `drawingml/converter.py:2032`(C-08) → 필요한 요소만 `elements.py`(C-09). 한 슬라이드가 `slide_xml.py:8`(`create_slide_xml_with_svg`, 138줄 파일)에서 XML로 감싸지고 전환 조각·타이밍 조각이 `</p:sld>` 앞에 순서대로(전환 먼저, 타이밍 나중) 문자열로 삽입된다는 점만 알면 된다(`builder.py` 주석 7825 부근).
3. 전환·애니메이션을 직접 만들 일이 있으면 sidecar 형식(1.3 G)과 C-13~C-16, 문서 `pptx-animations.md` §8을 본다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 점검만(선행 스펙 `svg-authoring-and-quality`·`generate-default-pipeline`이 모두 `ready`가 된 뒤 `ready`로 올림). 이 스펙에 `depends`로 의존하는 스펙이 없어(다른 스펙은 이 스펙을 참조하지 않음) 독립 검토는 돌리지 않았다.
- 대조한 R-ID: R-01(가드 exit 78과 9개 필수 파일 목록 직접 확인), R-09·R-22(출력 경로와 backup 위치, `cli.py:2697-2707`·`3883-3913`을 앞서 직접 읽음), R-18(morph 전환 불일치 오류, `builder.py:7687-7699` 직접 읽음), R-19(`SvgNativeConversionError`가 `RuntimeError`이고 `main`의 except가 `ValueError`·`TemplateStructureError`만 잡는 것 확인), R-21(postflight 실패 시 파일 보존·exit 1 확인), R-27(생성 코드·문서 부재 검색), python-pptx가 `builder.py`에서만 import됨(`grep -rn "^from pptx\|^import pptx" svg_to_pptx`). 미결정 U-02·U-03은 코드로 해소했고 U-01은 적용 메모로 옮겼다.
- 대조하지 않은 R-ID: 그 외 전부. 특히 CLI 옵션 표의 기본값 일부, 애니메이션·전환 옵션의 세부, `validate_pptx_morph_pairs` 본문, 변환 내부(범위 밖)는 작성자 확인만 있다.
- 재구현: 미수행

## 적용 메모 [선택]

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01 | (미결정, 사용자 결정 필요) 이 레포를 스킬 폴더 그대로 쓰면 가드를 통과한다. `svg_to_pptx` 패키지만 떼어 쓰거나 가드가 요구하는 파일(`LICENSE`, `SPONSORS*.md`, 9개 스크립트, `SKILL.md` 표식)을 빼면 exit 78로 막힌다 | 가드는 코드로 우회 가능 여부를 알 수 없고, MIT 라이선스와 attribution 파일 유지 의무의 경계는 라이선스 조항을 읽고 사용자가 정해야 한다 | 연동 환경이 agent 기반이면 스킬 전체를 설치하는 경로가 가장 단순하다 |
| R-18 | 같은 sidecar에 morph 쌍이 있으면 CLI `-t`를 주지 않는다 | `-t`가 모든 슬라이드 전환을 덮어써 Morph 쌍 검증이 실패한다 | 없음(원본 동작 그대로) |
