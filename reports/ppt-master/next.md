---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-17
updated: 2026-11-17
---

# Next Session Plan: ppt-master

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone, 기준 SHA·라이선스, feature map 17행, 구조도(전체 과정과 주체 구분)
- [x] 분석 목적 확정(구조 파악·이해 + 기존 agent 환경에 연동할 부분 차용)과 스펙 범위 승인(2026-11-17)
- [x] 기능 스펙 5개 `ready`: 행 4 `generate-default-pipeline`(C1·C2 포함), 행 6 `svg-authoring-and-quality`(C3·C4 포함), 행 8 `svg-to-pptx-cli`, 행 9 `image-file-contract`, 행 14 `confirm-and-preview-ui`
- [x] 독립 검토를 돌린 것: 6행, 4행(다른 스펙이 `depends`로 의존). 8·9·14행은 메인 점검만

---

## 2. 해결되지 않은 남은 질문

- [ ] **무결성 가드와 부분 차용**(`svg-to-pptx-cli` 적용 메모): 스킬 폴더를 통째로 설치하면 가드를 통과한다. `svg_to_pptx/` 패키지만 떼어 쓰거나 `LICENSE`·`SPONSORS*.md`·9개 스크립트·`SKILL.md` 표식을 빼면 exit 78로 막힌다. 라이선스 조항을 읽고 사용자가 결정한다.
- [ ] `svg_to_pptx/`는 제외한 `scripts/pptx_to_svg/` 모듈(`preset_authoring`, `emu_units`, `preset_registry_to_svg`, `preset_svg_markup`, `converter`, `ooxml_loader`, `notes_import`)을 import한다(`svg-to-pptx-cli` 1.2). 이 부분만 떼어 쓰려면 이 모듈들이 필요하다.
- [ ] 확정 화면의 신뢰 경계: 서버는 `result.json` 작성자를 구분하지 않는다(`confirm-and-preview-ui` R-04). agent 환경에서 어디에 경계를 둘지는 연동 설계의 결정이다.
- [ ] `ready` 스펙 중 8·9·14행은 독립 검토를 하지 않았다. 구현 전에 필요하면 돌린다. 9행은 `svg-authoring-and-quality`의 크레딧 규칙과 `image-file-contract`의 R-12·R-20~R-22가 같은지 대조하지 않았다.
- [ ] 원본 대조를 하지 않은 R-ID가 많다(대부분 문서 선언 R-ID, 각 스펙 2.4 참조). 라이브 미리보기 자동 갱신은 브라우저에서 확인하지 않았다.
- [ ] 번들 아이콘·효과음의 라이선스(overview 1절).

---

## 3. 기능 스펙 후보

승인 범위 밖에서 기록한 후보(근거 있는 것만): `formula` 이미지(수식 렌더)는 코드만 허용하고 문서 정의가 없다(`image-file-contract`의 "원본이 정하지 않은 것"). `metadata.json`(docProps 입력)은 파이프라인이 만들지 않는 선택 입력이다(`svg-to-pptx-cli` R-27). 둘 다 스펙으로 올리지 않았다.

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

스펙 5개가 `ready`라서 지금 쓸 스펙은 없다. 재구현 검증(워크플로 4장)은 기본으로 하지 않았고 사용자가 승인할 때만 한다. 범위를 늘린다면 후보는 7행(`finalize_svg`, 내보내기를 막지 않는 미리보기), 2행(`source_to_md`), 12행(전환·애니메이션 효과 목록)이다.

### 막힌 경로

없음.

---

## 5. 참고 사항 및 후속 제안

- 분석 목적이 정해지면 권장 범위를 다시 잡는다. 잠정 권장(내부 구조 이해 기준): 행 4(Default 파이프라인), 6(SVG 계약·품질 검사), 8(SVG→PPTX 변환기)과 공유 계약 S2~S4. 행 8은 규모가 커서 분리가 필요하다.
- `artifacts/ppt-master/deepwiki/`가 이미 있다. 후보 자료이며 코드로 확인하기 전에는 근거로 쓰지 않는다.
- 레포 자체의 `AGENTS.md`는 개발자용 지침이라 따르지 않았다.
