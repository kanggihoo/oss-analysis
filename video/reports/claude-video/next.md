---
sha: "03ceb42f7fa2c4439aca01752118044baabffb8f"
created: 2026-10-25
updated: 2026-10-25
---

# Next Session Plan: claude-video

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone·SHA·라이선스 기록, 기능 지도 11행(overview 2절), 구조도 하나(overview 3절)
- [ ] 사용자 스펙 범위 승인(overview 1절 "스펙 범위"는 아직 "승인 전")

---

## 2. 해결되지 않은 남은 질문

- [ ] 지도 표에서 "미확인"으로 적은 함수 내부(`download.py` `fetch_captions`·`select_caption`, `frames.py` ffmpeg 호출·중복 제거, `whisper.py` `_post_whisper`·`transcribe_chunks`, `gemini.py` `ask`, `local_whisperx.py`, `setup.py` 설치 단계)는 스펙 단계에서 읽는다.

---

## 3. 기능 스펙 후보

지도의 모든 행이 `미작성`이다. 승인된 행이 정해지면 여기 대신 4절에 순서를 적는다.

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

승인 후 쓸 순서(제안): 설정 해석 → 자막 파싱·전사 세그먼트 → 소스 획득 → 프레임 선택·추출 → 클라우드 Whisper / 로컬 WhisperX → Gemini 엔진 → 설정 점검·설치 → local 엔진 오케스트레이션·보고서 → `/watch` 에이전트 호출 규약. 선행이 없는 행(설정 해석, 소스 획득, 자막 파싱, 프레임 선택)은 서브에이전트로 병렬 작성 가능.
