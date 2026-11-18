---
sha: "538eb3a757db94826cb90c4297279e50c5dd0f83"
created: 2026-11-18
updated: 2026-11-18
---

# rea-video Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/JuneYaooo/rea-video`
- **작업트리 상태**: Clean (`video/artifacts/rea-video/repo-metadata.txt`). 기준 커밋 `538eb3a` (main, 2026-11-17, `pyproject.toml` 버전 0.1.0). 로컬 clone은 `video/repos/rea-video`(Git 추적 제외)이고, 다른 환경에서 이미 한 clone 기록과 같은 SHA로 다시 받았다.
- **분석 목적**: **미정**. [video/GUIDE.md](../../GUIDE.md)의 "영상을 읽는 쪽" 비교 대상이고, README가 말하는 `capsule-cinema` 연결(분해 결과 → 재제작)이 관심사다. 목적이 없어서 feature map은 "구조 이해용 중간 세밀도"로 썼다. 목적이 정해지면 4절 `next.md`에서 행을 합치거나 쪼갠다.
- **라이선스**: Apache-2.0 — `LICENSE`(파일 확인, 하위 LICENSE 없음). `NOTICE` 파일이 따로 있다(본문 미열람). 모델 가중치는 별도 라이선스다: 음성 효과 분리 BandIt v2는 CC BY-SA 4.0(`docs/cli.md`, 미확인).
- **분석 대상 제품**: Python 패키지 `rea_video`(CLI `rea-video` = `rea_video.cli:main`, `pyproject.toml`) 하나. 같은 레포 안의 배포 단위는 agent skill(`skills/rea-video/`), Claude Code plugin 메타(`.claude-plugin/`), 설치 스크립트(`scripts/install_skill.sh`)다. 외부 의존 레포: `capsule-cinema`(생성 실행), `videomd`(PyPI 패키지, 포맷 검증).
- **스펙 범위**: feature map만(2026-11-18 요청). 범위 승인·구조도는 하지 않았다.

---

## 2. 프로젝트 개요

영상 한 편을 받아 **shot마다 "어떻게 만들어졌나"(실사 / AI 영상 / 3D / 코드 렌더 / 화면 녹화 / 정지 이미지 움직임 등 11개 안팎 라벨)를 증거와 함께 판정**하고, 자막·스티커 같은 편집 레이어, 소리(음성·배경음·효과음), 촬영 방식(구도·조명·색보정·편집)을 분해한 뒤, 사용자가 고른 영상 생성 모델에 맞춰 **재제작 계획**(생성 단위, 프롬프트, 필요한 참조 이미지)을 낸다. 결과는 사람용 `report.html/pdf`와 에이전트용 **VIDEO.md 패키지**로 나뉜다(`README.md`, `docs/decompose.md`: 모두 문서 근거).

Claude Code 같은 agent 안에서 쓰도록 설계됐다. 이미지를 볼 수 있는 agent가 VLM 역할을 대신하는 **리뷰 루프**(`survey`/`review`/`apply-review`)가 핵심 사용 방식이고, VLM API는 선택이다. 판정은 확정 규칙(프레임 반복, 센서 노이즈, 메타데이터의 AIGC 라벨 등)에 외부 판독자(VLM, agent)의 확률을 융합해서 낸다(`classify.fuse`, `pipeline._vlm_gate` 등: 함수 존재만 코드 확인, 융합 수식은 미확인).

핵심 호출 경로(코드 확인: `cli.py:cmd_decompose` → `pipeline.py:decompose` import 목록): `media.video_info`/`probe.provenance` → `shots.build_track`/`detect_shots` → `features`·`overlay`·`packaging`·`assets`·`audio`/`stems`/`speech` 병렬 수집 → (선택) `vlm.VLMClient` → `classify.deterministic`/`fuse`/`decide` → `pipeline.finalize`(계획·보고서·VIDEO.md 생성). `finalize`는 `apply-review`·`correct`·`eval`에서도 다시 불린다(`pipeline.py` `_FINALIZE_ONLY` 주석, 부분 확인).

### Feature map

기준: 공개 CLI 서브커맨드 26개(`cli.py` `add_parser` 목록, 코드 확인)와 `rea_video/` 모듈 파일 이름(`git ls-files`)을 대조했다. 모듈 내부는 docstring과 함수 이름까지만 읽어서 대부분 **추론**이다.

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 입력 메타·shot 분할·전환 판정 | 영상 → 컨테이너 출처 단서(카메라 태그, 인코더, AIGC 라벨, C2PA), 컷 경계, 전환 종류(디졸브·와이프 등). 판정 자체는 포함하지 않음 | `media.py` `video_info`, `probe.py` `provenance`, `shots.py` `build_track`·`detect_shots`·`shots_from_cuts`, `transitions.py` `classify`. CLI `probe` | 없음 | 핵심 | `capabilities/shot-segmentation.md` · 미작성 | 진입점 코드 확인 / 내부 추론 |
| 2 | shot 제작방식 판정(결정 규칙 + 융합) | shot 특징 → 라벨 확률(실사·AI·3D·코드 렌더·화면 녹화·정지 움직임 등)과 증거, 낮은 확신 표시. VLM·agent 답을 확률로 합치는 규칙 포함 | `features.py` `shot_features`·`collect_samples`, `motion.py`, `faces.py`, `classify.py` `deterministic`·`fuse`·`decide`, `pipeline.py` `_vlm_gate`·`_agent_review_dispute` | 1 | 핵심 | `capabilities/shot-classification.md` · 미작성 | 진입점 코드 확인 / 규칙 내용 추론 |
| 3 | VLM 판독자 | `--vlm`일 때 shot·전체 영상을 OpenAI 호환 멀티모달 API로 질문하고 응답을 정규화. 호출 상한·묶음 규칙 포함 | `vlm.py` `VLMClient`·`VLMConfig`·`normalize_shot_result`, `pipeline.py` `vlm_units`, 환경변수 `REA_VLM_*`(`vlm.py` docstring) | 없음 | 핵심 | `capabilities/vlm-reader.md` · 미작성 | 진입점 코드 확인 / 내부 미확인 |
| 4 | agent 리뷰 루프(survey → review → apply-review) | 이미지를 볼 수 있는 agent가 VLM 역할. 전체 개요 시트로 컷 판단 → shot별 키프레임 질문 → JEV 형식 답 → 결론에 병합 | `cli.py` `cmd_survey`·`cmd_review`·`cmd_apply_review`, `survey.py` `run`·`detail_tasks`·`read_answer`, `review.py` `build_tasks`·`apply_answers` | 2 | 핵심 | `capabilities/agent-review-loop.md` · 미작성 | 진입점 코드 확인 / 내부 추론 |
| 5 | 편집 레이어(자막·화면 문구·스티커) 추출 | OCR + 밀집 프레임 비교 → 문구별 시작·끝·스타일, 스티커 위치, 효과음 정렬. SRT/ASS 내보내기 | `overlay.py`, `packaging.py` `analyze`·`build_cues`·`find_stickers`·`to_srt`·`to_ass`, `OCR_MAX` | 1 | 핵심 | `capabilities/overlay-packaging.md` · 미작성 | 함수 목록 코드 확인 / 내부 추론 |
| 6 | 실제 소재 검출 | shot 안에 박힌 스크린샷·사진·영상 조각과 shot 전체가 실사/녹화인지 판정 → 사용자가 직접 제공해야 하는 소재 목록(`user_assets`) | `assets.py` `detect_embedded`·`material_summary`, `docs/decompose.md` 2.1 | 2, 5 | 핵심 | `capabilities/real-material-detection.md` · 미작성 | 진입점 코드 확인 / 내부 추론 |
| 7 | 소리 분리·분석 | 소리 → 원음/인성/배경음/효과음 4트랙, BPM·조성·섹션, 효과음 후보, 컷의 박자 일치율, AI 음악 vs 곡 라이브러리 판단 | `stems.py` `extract_stems`, `effects.py`, `audio.py` `analyze_audio`·`merge_audio_with_vlm`, `sound_source.py` `classify_sound_sources`, `prosody.py`. CLI `stems`. onnx 모델 자동 다운로드 | 없음 | 핵심 | `capabilities/audio-analysis.md` · 미작성 | 진입점 코드 확인 / 수치·모델 문서 근거만 |
| 8 | 음성 인식·화자 분리 | 대사와 시간(자막이 없어도), 화자별 음성 트랙, 누가 말했는지 | `speech.py`(sherpa-onnx SenseVoice), `speakers.py` `available`·`name_speakers`·`write_tracks`. 선택 extra `[asr]` | 7 | 핵심 | `capabilities/speech-and-speakers.md` · 미작성 | 진입점 코드 확인 / 내부 미확인 |
| 9 | 촬영 방식 분석(aspects 플러그인 패밀리) | shot·영상별 구도·카메라·조명·색보정·편집 리듬·형식(구술형·탁상 촬영·손에 든 소품·vlog 등). 새 차원을 모듈 하나로 추가 | `aspects/__init__.py`, `aspects/base.py` `Aspect`·`REGISTRY`, `framing`·`camera`·`lighting`·`grade`·`editing`·`fmt`, `docs/dev/aspects.md` | 1, 2 | 핵심 | `capabilities/camera-aspects.md` · 미작성 | 레지스트리 구조 코드 확인 / 각 측정 추론 |
| 10 | 연기·서사·등장 요소(보고서 재료) | 인물 감정·표정·말투, shot의 서사 역할(주의 끌기·결론 등), 인물·장소·소품 목록, 영상 종류와 제작 단계 가이드 | `performance.py`, `narrative.py`, `entities.py`, `playbook.py`, `production.py` | 2, 4 | 핵심 | `capabilities/narrative-and-cast.md` · 미작성 | 모듈 존재·docstring만 / 추론 |
| 11 | breakdown 조립·보고서(report.html/md/pdf) | 모든 결과를 `breakdown.json`으로 묶고 사람용 보고서·콘택트 시트·스토리보드·PDF 출력 | `pipeline.py` `decompose`·`finalize`, `report.py`, `visual.py` `shot_sheet`·`storyboard`, `pdf.py`. CLI `decompose`·`summary`·`pdf` | 1~10 | 핵심 | `capabilities/breakdown-and-report.md` · 미작성 | 호출 경로 코드 확인 / 출력 형식 미확인 |
| 12 | VIDEO.md 패키지(에이전트용 읽기 형식) | breakdown → `VIDEO.md` + `video/`(타임라인, shot 파일, 리듬). 층별로 읽어 토큰 절약. 검증 | `videomd.py` `write`·`read`·`check`, `docs/videomd.md`, 의존 `videomd` 패키지. CLI `videomd` | 11 | 핵심 | `capabilities/videomd-package.md` · 미작성 | 진입점 코드 확인 / 형식은 외부 스펙 |
| 13 | 모델 능력 지도·재제작 계획 | 사용자가 고른 생성 모델 → 생성 단위로 shot 묶기, 프롬프트 초안·린트, 참조 이미지 목록, 라우팅(R01~R21 등) | `capabilities/*.yaml`·`models/*.yaml`·`schema.json`, `plan.py` `Planner`·`LABEL_ROUTE`, `generation.py` `plan_generation`·`pack`·`lint_prompt`, `scripts/validate_capabilities.py`. CLI `plan`·`models` | 2, 11 | 핵심 | `capabilities/remake-planning.md` · 미작성 | YAML·함수 목록 코드 확인 / 규칙 추론 |
| 14 | 재제작 실행·원본 타임라인 조립 | 정지 이미지는 로컬 재구성, 생성된 shot은 원본 길이·속도에 맞춰 조립, 비교 영상 출력. 남은 shot은 원본 임시 사용 | `remake.py` `render_still_motion`·`fit_to_original`·`assemble`. CLI `remake`·`assemble` | 13 | 핵심 | `capabilities/remake-assembly.md` · 미작성 | 함수 목록 코드 확인 / 내부 추론 |
| 15 | 코드 렌더 shot 재제작(측정→스펙→렌더→채점) | 모션 그래픽 shot의 장면·레이어를 측정해 `code/spec.json`+`render.py`를 만들고, 원본과 프레임 단위로 비교 | `layers.py` `measure`·`compare`, `motion.py`, `code_remake.py` `build_spec`·`code_remake`, `redraw.py` `Redraw`. CLI `frames`·`code-remake`·`compare` | 2 | 핵심 | `capabilities/code-render-remake.md` · 미작성 | 진입점 코드 확인 / 내부 추론 |
| 16 | 동작 중심 shot의 드라이브 영상 | 춤·격투 shot의 자막·스티커를 지우고 비트에 맞춰 분할 → 동작 이전 영상 모델 입력, `--join`으로 복귀 | `dance.py`, `drive.py` `drive`·`join`·`cut_points`, 선택 깊이 모델. CLI `drive` | 13 | 핵심 | `capabilities/motion-drive.md` · 미작성 | 진입점 코드 확인 / 내부 추론 |
| 17 | capsule-cinema 연결 | 계획을 capsule-cinema 작업으로 변환·실행(유료, `--dry-run` 선행), 분해 결과로 capsule 초안 생성. capsule-cinema의 Python 환경에서 실행 | `integrations/capsule_cinema.py` `export_capsule_analysis`·`build_remake_jobs`, `run_remake.py`, `to_capsule.py`, `cli.py` `_capsule_python`·`_run_integration`. CLI `capsule`·`remake-plan`·`remake-run`·`capsule-draft` | 13 | 핵심 | `capabilities/capsule-bridge.md` · 미작성 | 진입점 코드 확인 / 상대 레포 쪽 미확인(GUIDE 비교 지점) |
| 18 | 사용자 기억·교정 | 사용자 선호, 판정 교정 기록, 같은 패턴 재검토 힌트, 교정을 평가 샘플로 내보내기 | `memory.py` `correct`·`reapply`·`patterns`·`hint_for`·`export_labels`, `~/.rea-video`(`REA_VIDEO_HOME`). CLI `correct`·`prefs`·`memory` | 11 | 핵심 | `capabilities/memory-and-correction.md` · 미작성 | 진입점 코드 확인 / 내부 추론 |
| 19 | agent skill·설치 배포 | SKILL.md 워크플로(① memory → survey → decompose → review → 교정 후 인도), references 13개, 플러그인 메타, 다중 agent 디렉터리 링크 설치 | `skills/rea-video/SKILL.md`, `skills/rea-video/references/*`, `.claude-plugin/{plugin,marketplace}.json`, `scripts/install_skill.sh`, `AGENTS.md` | 11 | 핵심 | `capabilities/agent-skill-contract.md` · 미작성 | SKILL.md 1~70행 읽음 코드 확인 / references 미열람 |
| 20 | 정확도 평가 도구 | 라벨 yaml과 비교해 shot 정확도·컷 F1 측정, 결과 문서 | `evaluate.py`, `eval/*.yaml`, `eval/RESULTS.md`, `eval/agent_test/`. CLI `eval` | 11 | 부속 | `capabilities/eval-harness.md` · 미작성 | 존재 코드 확인 / 수치는 문서 주장 |

**공유 계약** (여러 기능이 같이 쓰는 데이터·형식)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| `breakdown.json` 구조(shot 목록, 확률, summary, audio, 패키징 레이어) | 2~20 거의 전부 | `pipeline.py` `decompose`·`finalize`, `SCHEMA`(`__init__.py`) | `capabilities/breakdown-schema.md` · 미작성 | 생산자 코드 확인 / 필드 목록 미확인 |
| 출력 디렉터리 레이아웃(`shots/`, `stems/`, `remake/`, `code/`, `drive/`) | 1, 7, 11~16 | `cli.py` 서브커맨드의 `-o`와 각 모듈의 경로 | 별도 스펙 없음 | 추론(디렉터리 이름은 `docs/cli.md`) |
| 라벨 체계(`LABEL_ZH`, 그룹 `group_of`)와 라우트 규칙 | 2, 6, 13, 14, 15 | `classify.py` `LABEL_ZH`·`group_of`, `plan.py` `LABEL_ROUTE` | `capabilities/label-taxonomy.md` · 미작성 | 코드 확인(표가 `docs/decompose.md`와 같음) |
| 모델 능력 지도 형식(원자 단위 → 모델 필드) | 13, 17 | `capabilities/schema.json`, `primitives.yaml`, `routing.yaml` | 13에 포함 | 파일 확인 |
| i18n(`T`, `LangDict`, `set_lang`) | 3, 5, 11, 13 | `i18n.py` | 별도 스펙 없음 | 추론 |

**대조한 범위와 미탐색 영역**
- 대조: `README.md` 전체, `AGENTS.md`, `pyproject.toml`, `docs/cli.md` 앞 80행, `docs/decompose.md` 앞 60행, `docs/replicate.md` 앞 40행, `docs/capsule-cinema.md`, `docs/dev/aspects.md` 앞 40행, `eval/RESULTS.md` 앞 25행, `rea_video/capabilities/README.md` 앞 30행, `routing.yaml` 앞 20행, `skills/rea-video/SKILL.md` 앞 70행, `cli.py` 서브커맨드 등록부와 `cmd_decompose`, `pipeline.py` import·`decompose` 앞부분·`_FINALIZE_ONLY`, 모든 `rea_video/*.py` 모듈의 docstring과 최상위 함수 이름.
- 문서와 구현의 차이: 아직 찾지 못했다. README의 정확도 표(98~100%)·모델 크기·원 모델 수치는 **문서 주장이고 실행 확인 안 함**. `docs/capsule-cinema.md`는 "원본 shot 하나에 호출 하나"라고 쓰고, `docs/replicate.md`는 여러 shot을 한 번에 생성하는 프롬프트는 수동 경로뿐이라고 쓴다(미확인).
- 미탐색: 모든 `.py` 함수 본문(규칙·임계값·융합 수식), `report.py`·`packaging.py`의 세부, `rea_video/capabilities/models/*.yaml`·`prompting.yaml` 내용, `skills/rea-video/references/` 13개, `docs/videomd.md` 후반, `docs/what-it-detects.md`, `docs/cases*`(사례 이미지·보고서), `NOTICE`, `i18n/` 번역본, `.github/`. 테스트(`tests/`)는 레포에 없다(`AGENTS.md`: .gitignore 처리).
- 실행은 하지 않았다(ffmpeg·onnx 모델 다운로드 필요). 샘플 영상은 `docs/cases/videos/`에 7개 추적되어 있다(재압축본이라 README 수치와 다를 수 있다고 README가 밝힘).

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

미작성. 범위 승인 후 필요하면 그린다. 읽는 순서 제안: `cli.py:main`(서브커맨드 지도) → `pipeline.py:decompose`(호출 순서) → `classify.py`(판정) → `plan.py`/`generation.py`(재제작 계획) → `integrations/`(capsule-cinema).

---

## 4. 질문 (Questions)

- [Q1: VLM 판독자(3번)는 무슨 내용인가](./questions/q1-vlm-reader.md) - *shot 키프레임을 OpenAI 호환 멀티모달 API에 보내 제작 방식을 묻는 선택 기능. 기본 꺼짐*
- [Q2: agent 리뷰 루프(4번)는 API 없이 쓸 수 있나](./questions/q2-agent-review-without-api.md) - *된다. 네트워크 호출 없이 파일로 질문·답을 주고받고 agent 자신이 VLM 역할*
- [Q3: 실제 소재 검출(6번)은 어떻게 하나](./questions/q3-real-material-detection.md) - *라벨로 shot 전체를, 블록 질감·사각형·OCR로 삽입 조각을 판정. 사진은 미확정으로 남김*
- [Q4: 음성 인식·화자 분리에 API 키나 GPU가 필요한가](./questions/q4-asr-resources.md) - *둘 다 불필요, CPU onnx. `[asr]` 설치와 첫 실행 모델 다운로드만 필요*
- [Q5: 코드 양은 어느 정도인가](./questions/q5-code-size.md) - *Python 약 22,000줄, 행별 줄 수 표*
- [Q6: 10~16번(보고서 재료 → 재제작)은 어떤 과정인가](./questions/q6-remake-stages.md) - *해석 → 보고서·VIDEO.md → 생성 단위 계획 → 원본 타임라인 조립, 코드 렌더·동작 shot은 별도 경로*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸(전부 미작성)
- 같은 폴더 비교 대상: [claude-video](../claude-video/overview.md), [hyperframes](../hyperframes/overview.md). 상대 레포 `capsule-cinema`는 clone만 되어 있다.
