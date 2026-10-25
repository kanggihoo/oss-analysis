---
sha: "03ceb42f7fa2c4439aca01752118044baabffb8f"
created: 2026-10-25
updated: 2026-10-25
---

# claude-video (watch) Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/bradautomates/claude-video`
- **작업트리 상태**: Clean (`artifacts/claude-video/repo-metadata.txt`). 기준 커밋 `03ceb42` (main, 2026-09-25, 스킬 버전 0.3.2).
- **분석 목적**: 요청문에 목적이 없었다. 이 작업 공간의 기본 목적인 "기능 스펙화(재구현 가능 수준)"로 진행한다. 목적을 바꾸려면 알려 달라.
- **라이선스**: MIT (`LICENSE`, Copyright (c) 2026 Bradley Bonanno). 하위 디렉터리에 다른 LICENSE 없음(`find . -name LICENSE`로 확인). `.claude-plugin/plugin.json`·`.codex-plugin/plugin.json`의 `license`도 `MIT`.
- **분석 대상 제품**: 루트 하나. 제품은 슬래시 명령 `/watch`로 호출되는 Agent Skill이며 CLI가 아니다(`AGENTS.md` Orientation). 배포 단위는 `skills/watch/`(SKILL.md + `scripts/` 표준 라이브러리 Python) 하나, 그 위에 Claude Code 플러그인(`.claude-plugin/`, `hooks/`), Codex 플러그인(`.codex-plugin/`, `.agents/plugins/`), claude.ai 업로드 번들(`build-skill.sh`)이 얹힌다. 중첩 패키지·별도 서버 없음.
- **스펙 범위**: 아직 승인 전 · 제외: 없음

---

## 2. 프로젝트 개요

에이전트(Claude Code, Codex 등)는 영상을 직접 볼 수 없다. `/watch`는 영상 URL이나 로컬 파일을 받아 **에이전트가 읽을 수 있는 증거**로 바꾼다. 두 엔진이 있다.

- **local 엔진**: `yt-dlp`로 캡션과 미디어를 받고, `ffmpeg`로 시간 표시가 붙은 프레임을 뽑고, 캡션이 없으면 Whisper(WhisperX 로컬 / Groq·OpenAI 클라우드)로 전사한다. 결과는 마크다운 보고서(프레임 파일 경로 목록 + 전사문)이고, 에이전트가 프레임을 하나씩 Read해서 본다.
- **gemini 엔진**: `GEMINI_API_KEY`가 있으면 영상을 Google에 넘겨 Gemini가 본 답을 보고서에 담는다. 에이전트는 그 답을 전달한다.

엔진은 자동으로 바뀌지 않는다. Gemini가 실패해도 local로 몰래 넘어가지 않는다(`SKILL.md` "No silent fallback", `watch.py:run_gemini` 오류 반환).

### 기능 지도

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 설정 해석 | 환경변수 → `~/.config/watch/.env` → 기본값 순으로 설정을 읽고, 엔진을 정하고, API 키를 찾는다. 설정 파일 쓰기(`write_settings`)도 포함. 프레임 상한(`frame_cap`)도 여기 있다. 설정 파일을 쓰는 마법사 흐름은 포함하지 않음 | `skills/watch/scripts/config.py` `get_config`, `resolve_engine`, `load_api_key`, `load_gemini_key`, `parse_env`, `write_settings` | 없음 | 핵심 | `capabilities/config-resolution.md` · 미작성 | 코드 확인(`get_config`·키 조회·`resolve_engine`·`frame_cap`) / 미확인(`read_env_text`·`parse_env`·`write_settings` 내부) |
| 소스 획득 (URL·로컬 파일) | URL이면 yt-dlp로 메타데이터와 캡션 한 트랙을 받고(`fetch_captions`), 필요하면 미디어를 받는다(`download_url`). 로컬 경로면 그대로 쓴다. 쿠키 옵션, 완료된 최종 경로 검증, 실행마다 새 디렉터리. 프레임·전사 처리는 포함하지 않음 | `download.py` `download`, `fetch_captions`, `select_caption`, `download_url`, `resolve_local`, `auth_args` | 없음 | 핵심 | `capabilities/source-acquisition.md` · 미작성 | 코드 확인(`download_url`·`download`) / 미확인(`fetch_captions`·`select_caption` 내부) |
| 자막 파싱·전사 세그먼트 | WebVTT를 `{start,end,text}` 세그먼트 목록으로 바꾸고, 겹침 중복 제거, 구간 필터, `[MM:SS] text` 형식으로 내보낸다. 세그먼트 검증(`normalize_segments`)과 `Segments`(gaps·no_speech 부가 정보)도 여기 있다. 전사 호출은 포함하지 않음 | `transcribe.py` `parse_vtt`, `filter_range`, `format_transcript`, `normalize_segments`, `Segments` | 없음 | 핵심 | `capabilities/transcript-segments.md` · 미작성 | 코드 확인(`normalize_segments`·`Segments`) / 미확인(`parse_vtt`·`_dedupe`·`format_transcript` 내부) |
| 프레임 선택·추출 | 영상과 옵션(detail, 구간, fps, 해상도, 큐 시각)을 받아 ffmpeg로 프레임을 뽑는다. 자동 fps, scene 선택과 uniform 대체, 키프레임 모드, 16×16 썸네일 중복 제거, 큐 시각 프레임, 병합. 영상 다운로드·보고서 출력은 포함하지 않음 | `frames.py` `extract_scene_or_uniform`, `extract_keyframes`, `extract_at_timestamps`, `merge_frames`, `auto_fps`, `auto_fps_focus`, `get_metadata`, `parse_time`, `validate_controls` | 없음 | 핵심 | `capabilities/frame-extraction.md` · 미작성 | 코드 확인(상수·`auto_fps*`·`_emitted_frames`·독스트링) / 미확인(ffmpeg 호출 인자, 중복 제거 구현 내부) |
| 클라우드 Whisper 전사 | 영상에서 mono 16kHz mp3를 뽑아 Groq 또는 OpenAI 전사 API에 올리고, 24,000,000바이트 예산을 넘으면 청크로 나눠 시간 오프셋을 복원한다. 실패한 청크는 gap으로 보고. 로컬 WhisperX는 포함하지 않음(다음 행) | `whisper.py` `transcribe_video`, `plan_chunks`, `split_audio`, `transcribe_chunks`, `_post_whisper`, `shift_segments` | 자막 파싱·전사 세그먼트 | 핵심 | `capabilities/cloud-whisper.md` · 미작성 | 코드 확인(`transcribe_video`·`shift_segments`·상수) / 미확인(`_post_whisper` 재시도, `transcribe_chunks` gap 처리 내부) |
| 로컬 WhisperX 전사 | 미리 설치된 별도 venv의 `whisperx` 실행 파일을 하위 프로세스로 돌려 오디오 전체를 전사한다. 모델·장치·compute type·배치·언어·타임아웃 설정, 준비 sentinel 확인, 실패 시 클라우드로 넘어가지 않음. 설치 자체는 포함하지 않음(설정 점검·설치 행) | `local_whisperx.py` `transcribe_audio`, `settings`, `executable_path`, `command`, `run_inference` | 자막 파싱·전사 세그먼트 | 핵심 | `capabilities/local-whisperx.md` · 미작성 | 코드 확인(`transcribe_audio` 호출 경로는 `whisper.py:transcribe_video`) / 미확인(내부) |
| Gemini 엔진 | YouTube URL은 그대로, 그 밖은 Files API로 올려 Gemini에 질문하고 답과 처리 방식을 받는다. 업로드한 파일은 답 뒤에 삭제하고 삭제 실패는 경고. 범주별 오류(`Gemini auth` 등)로 실패 보고. `watch.py:run_gemini`의 보고서 출력 포함 | `gemini.py` `ask`, `upload_file`, `delete_file`, `is_youtube`, `build_prompt`; `watch.py` `run_gemini` | 설정 해석, 소스 획득 | 핵심 | `capabilities/gemini-engine.md` · 미작성 | 코드 확인(`run_gemini`·`upload_file`·`delete_file`) / 미확인(`ask`·`_call`·오류 범주 내부) |
| local 엔진 오케스트레이션·보고서 | `watch.py <source> [옵션]`을 받아 엔진 선택 → (local) 캡션 확인 → 미디어 다운로드 → 메타데이터 → 프레임 → 필요 시 전사 폴백 → 구간 필터 → 마크다운 보고서 출력. 부분 실패는 `Unavailable evidence`로 남기고 종료 코드를 정한다. 각 단계의 내부 규칙은 포함하지 않음(선행 행) | `watch.py` `main` | 설정 해석, 소스 획득, 자막 파싱·전사 세그먼트, 프레임 선택·추출, 클라우드 Whisper 전사, 로컬 WhisperX 전사, Gemini 엔진(엔진 분기만) | 핵심 | `capabilities/local-engine-report.md` · 미작성 | 코드 확인(`main` 전체를 읽음) |
| 설정 점검·설치 (setup.py + SessionStart hook) | `setup.py --check/--json/--install-whisperx/--backend/--engine/--detail`로 바이너리·키·엔진·WhisperX 준비 상태를 JSON으로 알리고, macOS는 brew로 설치, 나머지는 명령 안내, WhisperX는 uv로 Python 3.12 venv 설치와 워밍업. 첫 실행 표시. Claude Code 전용 hook은 `--check` 결과만 안내 | `setup.py` `main`, `_status`, `cmd_check`, `cmd_json`, `cmd_install`, `install_whisperx`; `hooks/hooks.json`, `hooks/scripts/check-setup.sh` | 설정 해석 | 핵심 | `capabilities/setup-preflight.md` · 미작성 | 코드 확인(`main`·`_status`·`cmd_check`·`cmd_json`·hook 스크립트) / 미확인(`install_whisperx`·`_install_macos`·uv 설치 내부) |
| `/watch` 에이전트 호출 규약 (SKILL.md) | 에이전트가 따르는 절차: 세션 첫 실행에 `setup.py --json`, 첫 실행 질문(엔진→detail→전사 백엔드), `watch.py "<source>" --question "<질문>"` 실행, 보고서의 프레임을 전부 Read, 큐 시각 재실행(`--timestamps`), 오류·부분 증거 처리, 비밀·삭제 금지 규칙. 코드가 아니라 프롬프트 계약 | `skills/watch/SKILL.md` (본문 전체) | local 엔진 오케스트레이션·보고서, 설정 점검·설치 | 핵심 | `capabilities/skill-protocol.md` · 미작성 | 코드 확인(SKILL.md 전문을 읽음, 규약 항목을 `watch.py`·`setup.py`와 대조한 것은 일부) |
| 패키징·배포 (플러그인·마켓플레이스·번들) | Claude Code 마켓플레이스·플러그인 매니페스트, Codex 매니페스트·마켓플레이스, `.skillignore`, claude.ai용 `dist/watch.skill` 빌드, 태그 푸시 릴리스, 개발용 플러그인 캐시 동기화 | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `skills/watch/scripts/build-skill.sh`, `.github/workflows/release.yml`, `dev-sync.sh`, `.skillignore` | 없음 | 부속 | `capabilities/packaging-distribution.md` · 미작성 | 코드 확인(매니페스트 4개·`build-skill.sh`·release.yml 앞부분) / 미확인(`dev-sync.sh`, `tests.yml`) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 전사 세그먼트 `{start, end, text}`(초 단위, 시작 시각 비내림차순, 빈 텍스트 불가) + 부가 정보 `gaps`·`no_speech` | 자막 파싱, 클라우드 Whisper, 로컬 WhisperX, local 엔진 보고서 | `transcribe.py` `normalize_segments`, `Segments` | 행 "자막 파싱·전사 세그먼트"가 소유 · 미작성 | 코드 확인 |
| 프레임 레코드 `{index, timestamp_seconds, path, reason}` | 프레임 선택·추출, local 엔진 보고서 | `frames.py` `_emitted_frames` | 행 "프레임 선택·추출"이 소유 · 미작성 | 코드 확인 |
| 설정 dict와 `WATCH_*`/`*_API_KEY` 이름 | 설정 해석, 설정 점검·설치, 오케스트레이션, Gemini, WhisperX | `config.py` `get_config` | 행 "설정 해석"이 소유 · 미작성 | 코드 확인 |
| 보고서 마크다운 형식(`# watch: video report`, `## Frames`, `## Transcript`, `## Unavailable evidence`, `## Answer (from Gemini)`) | local 엔진 오케스트레이션, Gemini 엔진, SKILL.md 규약 | `watch.py` `main`·`run_gemini` 출력부 | 행 "local 엔진 오케스트레이션·보고서"와 "Gemini 엔진"이 각자 소유 · 미작성 | 코드 확인 |

공유 계약은 별도 스펙 파일을 만들지 않고 소유 행의 스펙 1.3에 둔다(제안). 스펙 단계에서 순환이 생기면 분리한다.

**대조한 범위와 미탐색 영역**
- 대조: README 기능 설명(엔진·detail·자막·인증·WhisperX), `SKILL.md` 옵션 표 vs `watch.py` argparse 옵션(`--max-frames --resolution --fps --detail --timestamps --start --end --out-dir --no-whisper --whisper --no-dedup --sub-lang --cookies --cookies-from-browser --engine --question`, 모두 일치), `setup.py` 모드, 매니페스트 4개, `hooks.json`, `.skillignore`, `CHANGELOG.md` 0.3.x. `git ls-files` 전체 이름 훑기.
- 문서와 구현의 차이: 아직 발견하지 못했다(대조 항목별 세부 값은 스펙 단계에서 확인). 한 가지 메모: `watch.py`는 `--engine gemini`일 때 `--start/--end`를 Gemini clip으로 넘기고(`run_gemini` clip), 나머지 local 전용 옵션은 `Ignored local options`로 알린다(`LOCAL_ONLY_FLAGS`, `watch.py:29-30`). README·SKILL.md 설명과 같다.
- 미탐색: `tests/`(17개, 파일명만 확인), `.github/workflows/tests.yml`, `dev-sync.sh`, `docs/images/`, `.gitattributes`·`.gitignore`. 각 스크립트의 함수 본문은 위 지도 표의 "검증 수준" 칸에 적은 범위까지만 읽었다(`watch.py`·`config.py`·`SKILL.md` 전문, `download.py` `download_url`, `whisper.py` `transcribe_video`, `gemini.py` `upload_file`·`delete_file`, `setup.py` `_status`·`main`, `frames.py` 상수·fps·`_emitted_frames` 등). 외부 도구(yt-dlp, ffmpeg, WhisperX, Gemini/Groq/OpenAI API)는 실행하지 않았다.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 에이전트 → watch.py → 엔진별 하위 모듈 |

검증 구분: `archify deliver`(작업 사양·산출물 9개 검사 통과, `--repo-root`로 소스 근거 14건 확인) / `visual-check`(Chrome 자동 측정 통과, 1440×900·2048×1320 light·dark 스크린샷, 결과는 `artifacts/claude-video/structure-visual-check/`) / 시각 검토(1440×900 light 한 장을 직접 봄, 나머지 크기는 보지 않음).

### 그림 해설

**읽는 순서**
1. 왼쪽 `에이전트 + SKILL.md`: 사용자가 `/watch`를 치면 에이전트가 SKILL.md 절차대로 `setup.py --json`을 한 번 돌리고, `watch.py`를 실행한다.
2. `watch.py`: 설정(`config.py`)을 읽고 엔진을 고른다. 위쪽 갈래는 gemini, 오른쪽 갈래는 local.
3. local 갈래: `download.py` → (`frames.py`, `transcribe.py`). 캡션이 없을 때만 아래 `whisper.py`가 불린다.

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 에이전트 + SKILL.md | 호출 절차 규약. 코드가 아니라 모델이 읽는 지침 | 입력: 사용자 요청. 출력: `watch.py` 명령, 보고서의 프레임을 Read | `skills/watch/SKILL.md:10-168` | 코드 확인 |
| watch.py | 인자 파싱, 엔진 선택, local 파이프라인 오케스트레이션, 보고서 출력 | 입력: source와 옵션. 출력: stdout 마크다운, 종료 코드 | `watch.py:main` (94-422), `run_gemini` (33-91) | 코드 확인 |
| config.py | `WATCH_*` 설정, 키 조회, 엔진 결정 | 입력: 환경변수·`~/.config/watch/.env`. 출력: 설정 dict, 키 | `config.py:get_config`(132), `resolve_engine`(123), `load_gemini_key`(112) | 코드 확인 |
| setup.py (+hook) | 바이너리·키·엔진·백엔드 준비 상태 점검, 설치 | 입력: 플래그. 출력: JSON 상태, 종료 코드 0/2/3 | `setup.py:main`(315), `_status`(144); `hooks/scripts/check-setup.sh` | 코드 확인 |
| download.py | yt-dlp로 캡션·미디어 획득, 로컬 경로 통과 | 입력: source, 쿠키 옵션. 출력: `{video_path, subtitle_path, info, ...}` | `download.py:download`(199), `fetch_captions`(134), `download_url`(165) | 코드 확인(`download`·`download_url`) |
| frames.py | ffmpeg 프레임 선택·추출·중복 제거 | 입력: video_path, detail, 구간, 큐 시각. 출력: 프레임 레코드 목록 | `frames.py:extract_scene_or_uniform`(517), `extract_keyframes`(584), `extract_at_timestamps`(330) | 코드 확인(시그니처·독스트링), 내부 미확인 |
| transcribe.py | VTT 파싱, 세그먼트 검증·필터·포맷 | 입력: VTT 경로. 출력: 세그먼트 목록 | `transcribe.py:parse_vtt`(52), `normalize_segments`(26) | 코드 확인(`normalize_segments`) |
| whisper.py | 클라우드 전사와 WhisperX 분기, 청크 | 입력: video_path, backend, key. 출력: 세그먼트 목록과 사용한 backend | `whisper.py:transcribe_video`(347) | 코드 확인 |
| local_whisperx.py | 별도 venv의 whisperx 하위 프로세스 실행 | 입력: 오디오 파일. 출력: 세그먼트 목록 | `local_whisperx.py:transcribe_audio`(132) | 코드 확인(호출 경로) |
| gemini.py | Files API 업로드, Gemini 질문, 삭제 | 입력: 영상 참조, 질문, 키. 출력: 답 텍스트·토큰 수·처리 방식 | `gemini.py:ask`(100), `upload_file`(119), `delete_file`(156) | 코드 확인(`upload_file`·`delete_file`) |
| Google Gemini API | 외부 시스템. 영상 이해 | 영상 URI + 프롬프트 → 텍스트 | `gemini.py:20-21` (엔드포인트 상수) | 코드 확인(클라이언트가 그렇게 가정함), 서버 동작 미확인 |

**실행 흐름: local 엔진으로 URL 한 건 보기**
1. 설정과 엔진 결정 — 입력 `argv`, 환경, `.env` → 처리 `get_config`, `load_gemini_key`, `resolve_engine` → 출력 엔진 `local` (`watch.py:151-166`)
2. 캡션 확인 — URL이면 `fetch_captions`, 있으면 `parse_vtt`로 세그먼트 (`watch.py:183-195`)
3. 미디어 — `detail == transcript`이고 캡션이 있거나 백엔드가 `none`이면 URL 다운로드를 건너뜀. 아니면 `download` (`watch.py:197-209`)
4. 메타데이터와 구간 계산 — `get_metadata`, `auto_fps`/`auto_fps_focus` (`watch.py:211-238`)
5. 프레임 — 큐 시각 먼저 `extract_at_timestamps`, 남은 예산으로 `extract_keyframes`(efficient) 또는 `extract_scene_or_uniform` (`watch.py:240-264`)
6. 전사 폴백 — 캡션이 없고 백엔드가 `none`이 아니며 오디오가 있으면 `transcribe_video` (`watch.py:266-289`)
7. 보고서 — 구간 필터 후 stdout에 마크다운, 오류가 있고 증거가 하나도 없으면 종료 코드 1 (`watch.py:290-422`)

**미확인 영역**
- 외부 도구·API의 실제 동작(yt-dlp 캡션 선택 결과, ffmpeg 필터 출력, Whisper·Gemini 응답)은 실행하지 않았다.
- `setup.py` 설치 단계, 패키징 파일은 그림에서 제외했다.
- hook은 setup.py 노드의 sublabel에 합쳤다(별도 노드 없음).

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸
