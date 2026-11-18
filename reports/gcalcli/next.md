---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
---

# Next Session Plan: gcalcli

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone(`405639c`, full)·라이선스(MIT) 기록, feature map 11행·공유 계약 3건
- [x] 범위 승인(행 1~9, 10·11 제외) 후 기능 스펙 9개 작성(전부 `draft`), 독립 검토 3건(스펙 3·4·6), 통합 검토(overview 2절)
- [ ] 분석 목적 결정
- [ ] 구조도(archify)

## 2. 해결되지 않은 남은 질문

- [ ] 목적이 없다. 후보: (a) 구현 학습, (b) agent나 스크립트가 달력을 다루는 도구로 도입 검토(이 경우 OAuth 설정과 `--json`·`--tsv` 출력, `agendaupdate` 왕복이 핵심), (c) 재구현.
- [ ] `docs/man1/gcalcli.1`과 `README.md` 뒷부분(사용 예, FAQ)은 읽지 않았다. 문서와 구현의 차이를 찾으려면 읽어야 한다.
- [ ] README 서브커맨드 목록에 없는 `delete`·`search`·`conflicts`·`agendaupdate`·`config`·`util`은 코드에는 있다(overview 2절).

## 2.1 스펙 진행 상태 (2026-11-18)

9개 모두 `draft`다. `ready`로 올리려면 막힌 것: (a) 미결정이 열려 있음 — 대부분 Google API 응답, 외부 라이브러리(dateutil, parsedatetime, babel, platformdirs, googleapiclient) 동작, 로케일·터미널 값이라 **패키지 설치·실행 허용이 필요**하다. 일부 스펙은 임시 venv(저장소 밖)에서 스텁으로 실행해 확인했다. (b) 선행 스펙이 `draft`이면 `ready`가 될 수 없다. 독립 검토는 3·4·6에만 했고 1·2·5·7·8·9는 메인 점검만 했다(각 스펙 2.4).

원본 이상 동작(스펙에 기록됨): `_SetEventStartEnd`의 `e` 미갱신, edit의 `allday`·`default_reminders` 옵션 부재, `g`의 `all_day` 미정의, 재시도 조건의 `'403'` 문자열 비교, `action`·`email` 열의 `patch` 실패, `inf`·큰 값 `OverflowError` 전파.

## 3. 기능 스펙 후보

제외한 행: 10 ICS 가져오기, 11 리마인드(사용자 제외, 미작성). 필요하면 이 둘을 같은 절차로 추가한다.

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

`gcal.py` `_GraphEvents`(577행)·`_PrintEvent`(779행)·`_edit_event`(1044행), `details.py` 핸들러 내부, `ics.py` `CreateEventFromVOBJ`, `utils.py` `get_time_from_str`, `argparsers.py` 옵션 목록과 `README.md` 140줄 이후.
