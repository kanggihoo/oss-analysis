---
sha: "e40f40652d5690c4d9f928c4794c673a99f2cd0e"
created: 2026-10-26
updated: 2026-10-26
---

# roast-room 개요 (질문 단위 분석, 기능 지도 미작성)

## 1. 기본 정보

- **URL**: https://github.com/nateherkai/roast-room
- **목적**: 사용자 질문 하나("AI끼리 어떻게 대화하나, mesh 통신이 있나")에 답하기. 새 레포 전체 분석(2장)은 하지 않았다.
- **라이선스**: 루트 `LICENSE` MIT. 하위 LICENSE는 `app/public/vendor/jspdf-LICENSE.txt`, `app/public/brand/fonts/OFL.txt`(`git ls-files`로 확인, 본문은 안 읽음).
- **기준 SHA**: `e40f406`(main, 2026-10-21).
- **한 줄 정체**: Claude Code 스킬(`/roast-room`) + 역할별 서브에이전트 12개(`.claude/agents/council-*.md`) + 진행을 보여 주는 로컬 웹앱(`app/`). `코드 확인`

## 2. 기능 지도

미작성. 필요하면 2장 3~4번부터 한다.

## 4. 질문 목록

| 질문 | 한 줄 결론 |
|---|---|
| [q1 좌석 간 대화와 "mesh" 통신](questions/q1-seat-communication.md) | 좌석끼리 직접 통신은 없다. 의장(메인 세션)이 파일에 카드를 모아 다음 라운드 프롬프트로 다시 나눠 주는 hub-and-spoke다. |
