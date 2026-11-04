---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
---

# Next Session Plan: book-to-skill

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 기준 고정(clone, SHA, MIT), overview 1절
- [x] feature map(15행 → 같은 날 8·9 병합으로 12행 + 공유 계약 S1), 구조도 1개(archify 자동 검사 통과)
- [x] 기능 스펙 8개 작성(모두 ready): extract-artifacts, input-and-env, pdf-extraction, pdf-text-cleanup, text-sanitize, structure-detection, generation-setup, skill-authoring
- [x] PDF 추출 경로(`utils.extract_single_file`, `parsers/pdf.py`, `pdf_inspector_integration.py`)와 `SKILL.md` 주요 단계를 정적으로 읽음
- 추출기 실행은 하지 않았다(권한 거부)

---

## 2. 해결되지 않은 남은 질문

- [ ] 실제 PDF(텍스트형·표 많은 책·스캔본)로 돌려 엔진별 결과와 `chapter_ranges` 품질 비교. 실행 권한이 필요하다
- [ ] Step 10 정리 뒤 마스터 `SKILL.md`의 `output_text` 경로가 끊기는 것이 의도인지([skill-authoring](./capabilities/skill-authoring.md) R-17, 근거는 있으나 가리지 못함)
- [ ] `chapter_ranges`는 `splitlines()` 줄 번호라서 `\f`·U+2028이 남으면 `sed`의 `\n` 줄 번호와 어긋날 수 있는지([structure-detection](./capabilities/structure-detection.md) R-27, 추론)
- [ ] Mode 3(사전 분석에서 생성)은 소유하는 feature map 행이 없다. 필요하면 새 행으로

---

## 3. 기능 스펙 후보

승인 범위 8개는 모두 ready다. 범위 밖 행:

| 행 | 상태 | 이유 |
|---|---|---|
| 6 PDF 쪽 단위 근거 | 미작성 | 쪽 인용이 필요할 때만. 소수 표기 표시가 여기 있다 |
| 7 비PDF 파서 | 미작성 | 목적 밖 |
| 10 갱신·재실행 가드 | 미작성 | 목적 밖. Step 5의 "기존 스킬 있음" 분기와 경계는 [generation-setup](./capabilities/generation-setup.md) 2.1 |
| 11 검증·설치·배포, 12 측정 | 미작성 | 부속 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음에 쓸 기능 스펙: 없음(승인 범위 완료). 범위를 넓히면 행 6 → `capabilities/pdf-page-sidecar.md`

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `book_to_skill/utils.py` | `_chapter_number`, `_structural_chapter_headings`, `_find_outline_chapter_start` | 장 감지의 판별 규칙(다국어·오탐 방어) |
| `book_to_skill/sanitize.py` | `is_invisible_codepoint`와 상수 표 | 어떤 문자를 지우는지 전체 목록 |
| `tools/scan_generated_skill.py` | 규칙 정의부 | 스킬 스캔이 잡는 것 |
| `tests/test_pdf_outline_chapters.py`, `tests/test_pdftotext_edge_only_boilerplate.py` | — | 의도된 동작의 근거(규칙 확정 시에만 연다) |

---

## 5. 참고 사항 및 후속 제안

- 사용자가 관심 있는 것은 PDF 전처리와 "AI가 책을 빠르게 설명하게 하는 것"이다. 추출 결과(`full_text.txt`, `chapter_ranges`)를 장 단위로 요약해 색인으로 한 장만 읽게 하는 설계가 이 도구의 핵심이다.
- 같은 목적의 주제 폴더는 아직 없다. `ai-learning/`은 AI 튜터 앱 비교용이라 맞지 않는다고 판단해 루트에 두었다.
