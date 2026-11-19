---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
---

# gcalcli Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/insanum/gcalcli`
- **작업트리 상태**: Clean (`artifacts/gcalcli/repo-metadata.txt`). 기준 커밋 `405639c`(main, 2025-10-24, `git describe` = `v4.5.1-8-g405639c`). `ChangeLog` 맨 위는 v4.5.2(미릴리스, "Support oauth (and cache) files in $GCALCLI_CONFIG dir").
- **분석 목적**: **미정**. feature map은 "구조 이해용"으로 썼다. 목적이 정해지면 `next.md`에서 행을 조정한다.
- **라이선스**: MIT — `LICENSE`(파일 확인: "Copyright (c) 2019 Eric Davis, Brian Hartvigsen, Joshua Crowgey"). `pyproject.toml`도 MIT. 하위 LICENSE 없음.
- **분석 대상 제품**: Python 패키지 `gcalcli`(CLI `gcalcli` = `gcalcli.cli:main`, `pyproject.toml`) 하나. 선택 extra `vobject`(ICS 가져오기용). 배포 단위는 PyPI와 `docs/man1/gcalcli.1` man 페이지뿐이고 서버·UI는 없다.
- **스펙 범위**: 승인(2026-11-18, 행 1~9) · 제외: 10 ICS 가져오기, 11 리마인드 — 사용자 제외. 구조도는 아직 없다.

---

## 2. 프로젝트 개요

Google Calendar API v3를 터미널에서 쓰는 CLI다. 일정 조회(agenda, 검색, 갱신분, 충돌), ASCII 주·월 달력, 일정 추가(자연어 quick add 포함)·수정·삭제, ICS/vCal 가져오기, cron용 리마인드 실행을 한 프로그램으로 제공한다(`README.md` Features, 서브커맨드 목록은 `argparsers.py:get_argument_parser`와 대조). 인증은 **사용자가 직접 만든 Google Cloud OAuth 클라이언트**로 한다(`README.md` "You currently have to use your own Calendar API token", `docs/api-auth.md`).

호출 경로(코드 확인): `cli.py:main`이 rc 파일(`gcalclirc`)과 `config.toml`을 argparse namespace에 합치고 → `GoogleCalendarInterface`(`gcal.py`)를 만들어 → 서브커맨드 이름으로 `SetupAuth`·`ListAllCalendars`·`AgendaQuery` 등을 호출한다(`cli.py` 140~340행대 분기). 코드 규모는 `gcalcli/*.py` 17개 파일 4,650줄이고 `gcal.py`(1,715줄)가 거의 모든 동작을 가진 한 클래스다. 테스트는 `tests/` 27개 파일 약 4,600줄이 있다(열지 않음).

### Feature map

기준: 서브커맨드 등록부(`argparsers.py`의 `sub.add_parser` 호출), `gcal.py`의 공개 메서드, `cli.py` 분기, 각 모듈의 최상위 정의를 대조했다. 함수 본문은 일부만 읽었고 대부분 `추론`이다.

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 설정·옵션 해석 | 명령줄 + `gcalclirc` 플래그 파일(`@경로`) + `config.toml`(pydantic) + 환경변수(`GCALCLI_CONFIG`)를 합침. 옛 camelCase 옵션(`--configFolder`, `--defaultCalendar`)은 **경고만 내고 값은 무시**(코드 확인: `deprecations.py` 밖에서 읽는 곳 없음, 2026-11-18 정정). 기본·무시 캘린더 해석(`set_resolved_calendars`)과 데이터 파일 경로 규칙(`env.data_file_paths`, `gcal.py` `data_file_path`의 legacy 이동)도 이 행이 소유. `config edit`, `util config-schema` | `cli.py` `main`, `config.py` `Config`·`AuthSection`·`CalendarsSection`·`OutputSection`, `env.py` `config_dir`·`data_file_paths`, `deprecations.py`, `argparsers.py` | 없음 | 핵심 | [config-resolution](capabilities/config-resolution.md) · draft | 진입점·구조 코드 확인 / 병합 우선순위 일부 확인 |
| 2 | OAuth 인증·토큰 | `init` 또는 **캐시 미스 시**(캐시 읽기에 성공하면 `get_cal_service`가 불리지 않아 토큰 파일 없이도 `list` 동작: 2026-11-18 정정) 사용자 client-id/secret으로 로컬 포트 OAuth 흐름. 옵션 철자는 **`--noauth_local_server`(밑줄)**, 안내문만 하이픈. 원격 포트 전달 안내. 토큰 저장·갱신·옛 JSON 토큰 이전, `util inspect-auth`(`--config-folder`를 무시하고 `env.config_dir()`만 사용; 경로 규칙은 행 1 소유) | `auth.py` `authenticate`·`refresh_if_expired`·`creds_from_legacy_json`, `gcal.py` `_google_auth`·`_load_credentials`·`SetupAuth`, `utils.py` `inspect_auth`, `docs/api-auth.md` | 1 | 핵심 | [oauth-auth](capabilities/oauth-auth.md) · draft | 진입점 코드 확인 / 흐름 일부 읽음 |
| 3 | 캘린더 목록·선택·캐시 | `list`로 접근 가능한 캘린더 표시. `--calendar 이름#색` 선택은 정확 일치 우선, 아니면 정규식(대소문자 무시). 목록은 pickle 캐시, `util reset-cache`(경로 규칙은 행 1 소유), API 재시도 백오프 | `gcal.py` `_select_cals`·`_get_cached`·`_retry_with_backoff`·`ListAllCalendars`, `gcal.py` `_calendar_color`(이벤트 출력 색도 결정), `cli.py` `parse_cal_names`·`rsplit_unescaped_hash`·`CalName`(`set_resolved_calendars`는 행 1 소유) | 2 | 핵심 | [calendar-selection](capabilities/calendar-selection.md) · draft | 선택·캐시 코드 확인 / 재시도 본문 미확인 |
| 4 | 일정 조회·검색(agenda/search/updates/conflicts) | 시작·끝 범위로 일정 목록, 텍스트 검색, 마지막 갱신 이후 변경분, 겹치는 일정 찾기. 취소된 일정·2038년 이후 제외, 거절한 일정 처리 | `gcal.py` `_GetAllEvents`·`_search_for_events`·`AgendaQuery`·`TextQuery`·`UpdatesQuery`·`ConflictsQuery`·`_DeclinedEvent`, `conflicts.py` `ShowConflicts`(`updates`·`conflicts`는 `--tsv`·`--json`을 무시하고 `agenda`·`search`만 행 9의 직렬화에 닿음: 스펙 4 R-11·14·15) | 3, 6 | 핵심 | [event-query](capabilities/event-query.md) · draft | `_GetAllEvents` 본문 코드 확인 |
| 5 | 출력 렌더링(텍스트·TSV·JSON·ASCII 달력) | 일정을 색·폭·`--details` 필드에 맞춰 텍스트로, `calw`·`calm`은 격자 달력으로 출력(TSV·JSON 직렬화는 행 9 소유, 2026-11-18 경계 변경) | `gcal.py` `_PrintEvent`·`_GraphEvents`·`CalQuery`·`_get_week_events`·`_event_time_in_range`·`_event_spans_time`(달력 렌더러 전용, 행 4에서 이동)·`_word_cut`, `printer.py` `Printer`·`valid_color_name`, `utils.py` `agenda_time_fmt`, `gcal.py` 생성자의 폭 계산(`width['day']`), `argparsers.py` `get_output_parser`·`get_color_parser`·`get_details_parser`·`get_cal_query_parser`와 전역 `--conky`·`--nocolor`·`--lineart` | 4 | 핵심 | [output-rendering](capabilities/output-rendering.md) · draft | 함수 목록 코드 확인 / 레이아웃 계산 미확인 |
| 6 | 날짜·기간·알림 입력 파싱 | "내일 3pm", "2h30m", `10m popup` 같은 사람 입력을 시각·기간·알림으로. 로케일의 일/월 순서와 24시간제 반영. 사용자 입력 검증 | `utils.py` `get_time_from_str`·`get_timedelta_from_str`·`get_times_from_duration`·`parse_reminder`·`REMINDER_REGEX`, `validators.py` `get_input`·검증기 7개, `argparsers.py` `validwidth`·`validreminder` | 없음 | 핵심 | [input-parsing](capabilities/input-parsing.md) · draft | 함수 목록 코드 확인 / 내부 추론(`parsedatetime`·`dateutil` 의존) |
| 7 | 일정 추가(quick/add) | `quick`은 자연어 한 줄을 Google `quickAdd`에 전달. `add`는 제목·장소·시각·길이·종일(`--allday`)·설명·알림·색을 인자로 받고, 프롬프트는 `--noprompt`가 없으면 기본으로 켜져 비어 있는 값을 묻는다(종일 여부·색·참석자는 프롬프트 없음; 스펙 7 R-06·07). `QuickAddEvent`는 `_add_reminders`를 쓰지 않고 같은 로직을 복제 | `gcal.py` `QuickAddEvent`·`AddEvent`·`_add_reminders`·`_prompt_for_calendar`, `cli.py` `run_add_prompt`, `validators.py` `get_input` | 3, 6 | 핵심 | [event-create](capabilities/event-create.md) · draft | 진입점 코드 확인 / 내부 추론 |
| 8 | 일정 수정·삭제(edit/delete) | 검색어로 일정을 찾아 하나씩 대화형으로 수정·삭제(`--iamaexpert`로 확인 생략). 빈 검색어는 거부 | `gcal.py` `ModifyEvents`·`_iterate_events`·`_edit_event`·`_delete_event`·`_SetEventStartEnd` | 4, 6 | 핵심 | [event-modify](capabilities/event-modify.md) · draft | 코드 확인 + 스텁 API 실행(스펙 8). 원본 이상 동작 후보: `_SetEventStartEnd` 1026행의 뺄셈, edit에는 `allday`·`default_reminders` 옵션이 없어 `w`·`r` 경로가 깨짐, `g`의 `all_day` 미정의, 참석자 수정 없음 |
| 9 | 일정 세부 필드와 TSV 일괄 수정(agendaupdate) | agenda를 TSV로 내보내고(`_tsv`; `--json`의 `_json`도 같은 핸들러), 수정한 TSV를 표준 입력으로 `agendaupdate`에 넣으면 행마다 `patch`/`insert`/`delete`/`ignore`. 필드별 `Handler`가 읽기(`get`/`data`)와 쓰기(`patch`)를 가진다. 단일 캘린더 필수 | `details.py` `Handler`·`Time`·`Length`·`Url`·`Conference`·`Attendees`·`Title`·`HANDLERS`·`DETAILS_DEFAULT`, `actions.py` `patch`·`insert`·`delete`·`ACTIONS`, `gcal.py` `AgendaUpdate`·`_tsv`·`_json` | 4, 5 | 핵심 | [agenda-tsv-roundtrip](capabilities/agenda-tsv-roundtrip.md) · draft | 코드 확인 + 스텁 실행(서버 응답 제외). 알려진 이상 동작: `action`·`email` 열은 `patch`·`insert`에서 항상 `AttributeError`, 개행·탭·`"`의 왕복 손상, 기본 출력에 `id` 열이 없어 `--details id` 필요(스펙 9 R-06·R-09) |
| 10 | ICS/vCal 가져오기 | 파일 또는 표준 입력의 ICS를 단일 캘린더에 가져온다. 선택 설치 `vobject` 필요. 중복 방지용 새 import API 대 `--use-legacy-import`, `--dump`로 내용만 확인 | `ics.py` `get_ics_data`·`CreateEventFromVOBJ`·`dump_partial_ical`, `gcal.py` `ImportICS`·`_event_should_use_new_import_api` | 3 | 핵심 | `capabilities/ics-import.md` · 미작성 | 분기 코드 확인 / 변환 규칙 미확인 |
| 11 | 리마인드 실행(remind) | 지금부터 N분 안에 시작하는 일정을 모아 외부 명령을 `os.fork` + `execvp`로 실행. `%s`가 일정 메시지로 치환. 알림 시각을 지키는 옵션 | `gcal.py` `Remind`, `argparsers.py` `get_remind_parser` | 4 | 핵심 | `capabilities/remind.md` · 미작성 | `Remind` 본문 전체 읽음(코드 확인) |

**통합 검토(2026-11-18)**: 스펙 9개의 선행 관계에 순환이 없다(1 → 2 → 3 → 4·7 → 5·8 → 9, 6은 독립 선행). 공유 계약 정의가 서로 같다: 내부 이벤트 표현(`s`·`e`·`gcalcli_cal`)은 스펙 4가 정의하고 5·8·9가 그대로 쓰며, `self.cals`·`all_cals`·`colorSpec`은 스펙 3, 데이터 파일 경로는 스펙 1이 소유하고 2·3이 링크한다. 점검한 범위(선행 목록, 이벤트 표현·캘린더 상태·경로 소유, 서브커맨드별 옵션 유무, 보고된 이상 동작의 일관성)에서는 서로 모순되는 서술을 찾지 못했다. 스펙 9개를 줄 단위로 교차 대조한 것은 아니다. 대표 흐름 하나: `gcalcli agenda`(행 1이 옵션·config를 합침) → 행 2 인증(캐시 미스 시) → 행 3이 캘린더 목록을 캐시에서 읽어 이름·정규식으로 선택 → 행 6이 시작·끝 문자열을 시각으로 파싱 → 행 4가 `_GetAllEvents`로 페이지를 돌며 `s`·`e`·`gcalcli_cal`을 붙여 `s` 순으로 정렬 → `--tsv`면 행 9의 `_tsv`, 아니면 행 5의 `_iterate_events`/`_PrintEvent`로 출력. 쓰기 경로는 `add`(행 7)가 행 6 파서와 행 3 선택을, `edit`/`delete`(행 8)가 행 4의 이벤트 표현을, `agendaupdate`(행 9)가 `agenda --tsv --details id` 출력을 입력으로 받는다. 원본의 알려진 이상 동작(예: 행 8의 `_SetEventStartEnd` 뺄셈 버그)이 불변식을 깨는 지점은 각 스펙에 적혀 있다.

**공유 계약**

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 내부 이벤트 표현: API가 준 이벤트 dict에 `s`·`e`(현지 시각 datetime), `gcalcli_cal`(소속 캘린더)을 덧붙인 형태 | 4, 5, 8, 9, 11 | `gcal.py` `_GetAllEvents`, `_types.py` `Event` | 행 4에 포함 | 코드 확인 |
| 옵션 dict(`GoogleCalendarInterface.options`)와 `printer` | 3~11 | `gcal.py` `__init__`(70행), `printer.py` | 별도 스펙 없음 | 추론 |
| 데이터 파일 경로(`oauth`, `cache`) | 2, 3 | `env.py` `data_file_paths`, `gcal.py` `data_file_path` | 행 1·2에 포함 | 함수 존재 코드 확인 |

**대조한 범위와 미탐색 영역**
- 대조: `README.md` 전체 중 앞 140줄(Features, 서브커맨드, 초기 설정), `ChangeLog` 앞 30줄, `pyproject.toml`, `docs/api-auth.md` 앞 25줄, `cli.py` 앞 140줄과 분기 전체의 `grep`, `argparsers.py`의 서브커맨드 등록부, `gcal.py`의 모든 메서드 이름과 `_select_cals`·`_get_cached`·`_GetAllEvents`·`Remind`·`ImportICS` 앞부분·`AgendaUpdate`·`ModifyEvents`, 모든 모듈의 최상위 정의.
- README의 서브커맨드 목록(init, list, edit, agenda, updates, calw, calm, quick, add, import, remind)에는 없지만 코드에 있는 것: `delete`, `search`, `conflicts`, `agendaupdate`, `config edit`, `util config-schema|reset-cache|inspect-auth`(`argparsers.py` 등록부, `cli.py` 분기: 코드 확인). 이 중 `agendaupdate`·`conflicts`는 `gcal.py`에 메서드가 있다.
- 미탐색: `gcal.py`의 출력 레이아웃(`_GraphEvents`, `_PrintEvent`, `_word_cut` 등 500~1000행대), `_edit_event`, `_delete_event`, `QuickAddEvent`, `AddEvent` 본문, `ics.py` 변환 규칙, `details.py`의 필드별 핸들러 내부, `utils.py`의 파싱 본문, `argparsers.py`의 옵션 목록, `tests/`(27개 파일), `docs/man1/gcalcli.1`, `.github/`, `stubs/`.
- 실행은 하지 않았다(Google OAuth 클라이언트가 필요하고, 사용자 계정에 접근하는 도구이므로 실행에는 허용이 필요하다).

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

미작성. 읽는 순서 제안: `cli.py:main`(설정 병합과 분기) → `gcal.py:GoogleCalendarInterface.__init__`·`_select_cals`·`_get_cached` → 조회 경로(`AgendaQuery` → `_search_for_events` → `_GetAllEvents` → `_iterate_events`/`_PrintEvent`) → 쓰기 경로(`AddEvent`, `ModifyEvents`, `AgendaUpdate`+`actions.py`) → `ics.py`.

---

## 4. 질문 (Questions)

- [Q1: TSV란 무엇이고 ICS 가져오기·리마인드는 무엇인가](./questions/q1-tsv-ics-remind.md) - *TSV는 agenda 출력과 `agendaupdate` 입력에 쓰는 탭 구분 표, ICS는 초대 파일 가져오기, remind는 cron이 부르면 N분 내 일정을 외부 명령에 넘기는 기능*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸(전부 미작성)
