---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/details.py
  - gcalcli/actions.py
  - gcalcli/gcal.py
  - gcalcli/argparsers.py
  - gcalcli/cli.py
  - gcalcli/exceptions.py
  - gcalcli/utils.py
depends:
  - event-query.md
  - output-rendering.md
  - input-parsing.md
status: draft
---

# 일정 세부 필드와 TSV 일괄 수정 (`--tsv`·`--json`·`agendaupdate`)

> `agenda`·`search`가 내부 이벤트 목록([event-query](event-query.md))을 필드 핸들러(`details.py`)의 `get`/`data`로 TSV·JSON에 직렬화하고, `agendaupdate`가 표준 입력(또는 파일)의 TSV를 행마다 `patch`/`insert`/`delete`/`ignore`로 실행해 같은 핸들러의 `patch`로 API 본문을 만들어 단일 캘린더에 보낸다. 출력과 입력 열 이름은 같지만 **왕복은 보장되지 않고**, 기본 출력(`time`·`title`)은 `agendaupdate`가 요구하는 `id` 열조차 없다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `agenda --tsv --details id [--details length ...]`가 `_display_queried_events`에서 `_tsv`로 간다. 열은 `--details`와 기본 `{time, title}`의 합집합이고 `HANDLERS` 등록 순서로 놓인다(R-01~R-03).
2. `_tsv`가 머리글 한 줄(열 이름 = 각 핸들러의 `fieldnames`)과 이벤트당 한 줄(`Handler.get` 결과를 탭으로 잇고 `\n`을 두 글자 `\n`으로 바꿈)을 쓴다(R-03, R-06). `--json`은 같은 핸들러의 `data`로 JSON 배열을 쓴다(R-04).
3. 사용자가 열 값을 고친 TSV를 `agendaupdate`에 넣는다(`--calendar` 하나 필수). `DictReader`(탭 방언)로 읽고 행마다 `action`(없으면 `patch`)을 판정한다(R-08, R-09).
4. `patch`는 `id`가 비면 `insert`로 넘기고, 아니면 열 순서대로 `FIELD_HANDLERS[열].patch`를 불러 `mod_event` 본문을 만든다. 읽기 전용 열(`html_link`·`hangout_link`·`calendar`)은 현재 이벤트를 `events.get`으로 한 번 읽어 비교만 한다(R-10, R-13).
5. `events.patch(calendarId, eventId, conferenceDataVersion=1, body)`를 `_retry_with_backoff`로 보낸다. `delete`는 `id`만 쓰고 `ignore`는 아무것도 안 한다(R-10, R-12).
6. 행 하나라도 예외(잘못된 `action`, 알 수 없는 열, 읽기 전용 불일치, 핸들러 버그)면 거기서 중단하고 앞 행의 API 호출은 되돌리지 않는다(R-14).

### 1.2 범위·통합 지점 [필수]
- 제공: `_tsv`·`_json` 직렬화, `details.py` 전체(`Handler` 계층, `HANDLERS`·`FIELD_HANDLERS`·`FIELDNAMES_READONLY`·`DETAILS`·`DETAILS_DEFAULT`·`ACTION_DEFAULT`), `actions.py` 전체(`patch`·`insert`·`delete`·`ignore`·`ACTIONS`·`CONFERENCE_DATA_VERSION`), `AgendaUpdate`, `--details`(`DetailsAction`)와 `agendaupdate` 서브커맨드의 인자 배선.
- 제외: 텍스트 아젠다·달력 출력과 `--details`가 `_PrintEvent`에 추가하는 줄([output-rendering](output-rendering.md) R-12), 일정 조회·정렬·내부 이벤트 표현 생성([event-query](event-query.md)), 대화형 수정(`event-modify`), 캘린더 선택·`_retry_with_backoff`([calendar-selection](calendar-selection.md) R-11), 시각·길이 파서(`get_timedelta_from_str` 등, [input-parsing](input-parsing.md)).
- 외부 의존·선행 계약:
  - [event-query 1.3](event-query.md)의 내부 이벤트: `s`·`e`(현지 tz-aware datetime), `gcalcli_cal`(캘린더 dict), API 원본 필드(`summary`·`id`·`htmlLink` 등). `get`/`data`가 읽는 것은 이 필드뿐이다.
  - [event-query R-11](event-query.md): `agenda`·`search`만 `_display_queried_events`를 거쳐 `_tsv`/`_json`에 닿고, `--tsv`가 `--json`보다 우선하며, 두 함수는 `ignore_started`·`ignore_declined` 필터를 복제한다. `updates`·`conflicts`는 `--tsv`·`--json`을 받아도 무시한다(R-01, R-05에서 재확인).
  - [calendar-selection R-11](calendar-selection.md): `_retry_with_backoff`는 성공 시 응답, 재시도 소진 시 `None`을 돌려주고 그 밖의 `HttpError`는 전파. 이 스펙의 모든 API 호출이 이것을 거치므로 소진 시 **조용히 성공으로 보인다**.
  - [input-parsing](input-parsing.md): `get_timedelta_from_str`(`Length.patch`), `is_all_day`(`Time.get`, [output-rendering](output-rendering.md)이 쓰는 같은 함수).
  - 외부: Google Calendar API `events.get`·`patch`·`insert`·`delete`(서버 동작은 확인 한계), `dateutil.parser.parse`·`isoparse`, `csv.DictReader`.
- 소유 상태·부작용: 표준 출력(`print`; `printer`를 거치지 않음)에 쓴다. `agendaupdate`는 원격 일정을 바꾼다. 모듈 전역 `details.TODAY`(import 시점의 오늘 날짜)가 `Time.patch`의 날짜 기본값이다(R-11). 그 밖에 소유 상태 없음. 이벤트 dict는 `get`/`data`가 바꾸지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]
**CLI (외부 계약)**

| 항목 | 정의 | 의미·제약 |
|---|---|---|
| `agenda`·`search`의 `--details {id,time,length,url,conference,title,location,description,calendar,email,attendees,action,reminders,attachments,end,all}` | `details_parser`, `DetailsAction`(append) | 반복 가능. `all`은 `DETAILS` 전체(위 15개). 잘못된 값은 argparse 오류(종료 2). `edit`·`updates`·`conflicts`도 같은 파서를 받으나 `--tsv`·`--json`은 `agenda`·`search`만 소비한다(R-01) |
| `--tsv`·`--json` | `output_parser`, `store_true`, 기본 False | 둘 다 주면 TSV(R-01). `--nostarted`·`--nodeclined`는 두 경로에 모두 적용(R-05) |
| `agendaupdate [--calendar NAME] [file]` | `parents=[calendar_parser]`(단일 `--calendar`), `file`은 `FileType('r', errors='replace')`, `nargs='?'`, 기본 `sys.stdin` | `--details`·`--tsv`·`--json`·출력 옵션이 **없다**(주면 argparse 오류). 인코딩은 로케일 기본, 디코딩 오류는 `?` 대체 |

**`Handler` 계약 (`details.py`)**: 클래스 메서드 `get(event) → list[string]`(TSV 셀, 길이 = `len(fieldnames)`), `data(event) → JSON 값`, `patch(cal, event, fieldname, value) → None`(`event`는 **API 본문 dict를 제자리 변형**; `cal`은 캘린더 dict). `fieldnames`는 이 핸들러가 내는 TSV 열 이름.

**핸들러 표** (`HANDLERS` 등록 순서 = TSV 열 순서)

| 키(`--details`·JSON 키) | TSV 열(`fieldnames`) | `get`(TSV 셀) | `data`(JSON 값) | `patch(fieldname, value)`가 `event`(본문)에 하는 일 | 읽기 전용 |
|---|---|---|---|---|---|
| `id` | `id` | `event.get('id','')` strip | 같은 문자열 | `body['id'] = value` | 아니오 |
| `time` | `start_date`, `start_time`, `end_date`, `end_time` | `s`·`e`를 `%Y-%m-%d`·`%H:%M`. `is_all_day`면 시각 칸 빈 문자열 | 위 네 이름의 dict | R-11 | 아니오 |
| `length` | `length` | `str(e - s)` (예 `1:30:00`, `1 day, 0:00:00`) | 같은 문자열 | R-12 | 아니오 |
| `url` | `html_link`, `hangout_link` | `htmlLink`, `hangoutLink` strip, 없으면 `''` | `{html_link, hangout_link}` | R-13 | **예**(둘 다) |
| `conference` | `conference_entry_point_type`, `conference_uri` | **첫** entry point의 `entryPointType`·`uri`. `conferenceData` 없으면 `['','']` | entry point 전부의 리스트 `{conference_entry_point_type, conference_uri, meeting_code, passcode, region_code}`(각 strip), 없으면 `[]` | R-15 | 아니오 |
| `title` | `title` | `summary`가 없거나 공백뿐이면 `(No title)`, 아니면 strip | 같은 문자열 | `body['summary'] = value` | 아니오 |
| `location` | `location` | `location` strip, 없으면 `''` | 같음 | `body['location'] = value` | 아니오 |
| `description` | `description` | `description` strip, 없으면 `''` | 같음 | `body['description'] = value` | 아니오 |
| `calendar` | `calendar` | `gcalcli_cal['summary']` strip | 같음 | 비교만(R-13) | **예** |
| `email` | `email` | `organizer.email` → `creator.email` → `gcalcli_cal['id']` 순 | 같음 | **정의 없음**(R-09) | 아니오 |
| `attendees` | `attendees` | 참석자 `email`을 `;`로 이음(상태 제외), `attendees` 키 없으면 `''` | `[{attendee_email, attendee_response_status}]` | R-16 | 아니오 |
| `action` | `action` | 항상 `'patch'`(`ACTION_DEFAULT`) | 같음 | **정의 없음**(R-09) | 아니오 |

`DETAILS` = 위 12개 키 + `reminders`·`attachments`·`end`. 뒤 셋은 `HANDLERS`에 없어 TSV·JSON에는 **아무 효과가 없다**(텍스트 경로에서만 쓰임, [output-rendering](output-rendering.md)). `HANDLERS_READONLY = {Url, Calendar}`, `FIELDNAMES_READONLY = {html_link, hangout_link, calendar}`, `FIELD_HANDLERS`는 모든 `fieldnames` → 핸들러 매핑이다. `DETAILS_DEFAULT = {time, title}`.

**TSV 형식**: 첫 줄은 머리글(열 이름을 탭으로 이음), 이어서 이벤트당 한 줄. 인용 부호·이스케이프는 없고 `\n`만 두 글자 `\n`으로 치환한다. **JSON 형식**: `[` 줄, 이벤트당 한 줄의 `json.dumps(row, default=str)`(구분은 앞 이벤트 뒤에 `,` 한 줄), `]` 줄. 이벤트가 없으면 TSV는 머리글만, JSON은 `[`·`]` 두 줄.

**`agendaupdate` 입력**: 탭 구분 `csv.DictReader`(`excel_tab`: 따옴표 `"` 해석, 이중 따옴표 이스케이프, 빈 줄 무시, CRLF 허용). 첫 줄이 머리글, 열 이름은 `FIELD_HANDLERS`의 키여야 한다.

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 경로 선택 | `agenda`·`search`만 `_display_queried_events`(`gcal.py:1286-1294`)의 `options.get('tsv')` → `_tsv`, 아니면 `options.get('json')` → `_json` 분기를 탄다(`tsv`가 `json`보다 우선, 둘 다 주면 TSV만 출력). `updates`·`conflicts`·`edit`·`delete`·`calw`·`calm`은 `--tsv`·`--json`을 받아도(`updates`·`conflicts`·`edit`은 파서에 있음) 읽지 않는다. `search`는 `TextQuery`(검색어 필수, event-query R-13)를 거친다. 이 서브커맨드들의 `--tsv` 처리는 event-query R-11·R-14·R-15와 일치 | 코드 확인 + 실행 확인(`parse_args`로 `agenda --tsv --json` → 둘 다 True) |
| R-02 | `--details` 해석 | `DetailsAction`이 값마다 `details[value] = True`(`all`이면 `DETAILS` 15개 전부). 이 dict는 `GoogleCalendarInterface.details`가 되고, `_tsv`·`_json`은 `keys = set(details) ∪ DETAILS_DEFAULT`를 쓴다. 따라서 `time`·`title`은 항상 나오고, `reminders`·`attachments`·`end`는 TSV·JSON에 **열을 만들지 않는다**. TSV 열 순서는 `--details` 인자 순서가 아니라 `HANDLERS` 순서다(`--details url --details id`와 `--details id --details url` 결과가 같다) | 코드 확인 + 실행 확인 |
| R-03 | `_tsv` 출력 | `handlers = [HANDLERS[k] for k in HANDLERS if k in keys]`. 머리글은 그 핸들러들의 `fieldnames`를 이은 탭 구분 한 줄(이벤트가 0건이어도 출력). 이벤트마다 R-05 필터 뒤 `'\t'.join(모든 handler.get(event))`에 `\n` → `\\n`(두 글자) 치환 후 `print`. **기본 출력**(`--details` 없음)은 `start_date start_time end_date end_time title`이고 `id`·`calendar`·`action` 열이 **없다**. 한 핸들러의 `get`이 예외를 내면 이미 쓴 줄은 남고 출력이 중단되며 종료 코드는 traceback(1)(R-14) | 코드 확인 + 실행 확인 |
| R-04 | `_json` 출력 | `print("[")` 뒤 이벤트마다(R-05 필터 뒤) `row = {key: HANDLERS[key].data(event) for key in keys if key in HANDLERS}`를 `json.dumps(row, default=str)`로 한 줄 출력, 둘째부터 앞에 `,` 한 줄, 끝에 `]`. **JSON 키 순서는 `set` 순회 순서**라서 프로세스마다(문자열 해시 무작위화) 달라질 수 있다 — 같은 입력이 같은 바이트를 보장하지 않는다. 값 구조는 TSV와 다르다(`time`은 4키 dict, `url`은 2키 dict, `conference`·`attendees`는 리스트, `action`은 상수 `"patch"`). `ensure_ascii` 기본이라 비ASCII는 `\uXXXX`. `agendaupdate`는 JSON을 읽지 않는다 | 코드 확인 + 실행 확인(키 순서는 한 프로세스의 두 호출에서 `HANDLERS` 순서와 달랐음; 무작위성은 해시 시드 추론) |
| R-05 | 필터 | `_tsv`·`_json` 모두 이벤트마다 `ignore_started and event['s'] < self.now`면 건너뛰고, 다음에 `ignore_declined and _DeclinedEvent(event)`면 건너뛴다(event-query R-10의 `_iterate_events` 필터와 같은 조건·순서의 복제). 건너뛴 이벤트가 전부여도 머리글(`[`)은 나가고 "No Events Found"는 없다 | 코드 확인 + 실행 확인 |
| R-06 | 줄바꿈·탭·따옴표의 왕복 | **쓰기**: 결합된 행 문자열에서 `\n`만 두 글자 `\n`으로 바꾼다(`\r`·탭·`"`은 그대로). **읽기**(`agendaupdate`): `\n` 이스케이프를 **되돌리지 않는다** — 열에 `L1\nL2`(두 글자)가 있으면 `summary`는 백슬래시 문자가 든 `L1\\nL2`가 된다. 값에 탭이 있으면 쓰기에서 셀이 갈라져 **같은 줄에 열 수보다 많은 셀**이 생기고, 읽기에서 `DictReader`가 남는 셀을 키 `None` 아래에 모아 `FIELD_HANDLERS[None]`이 `KeyError(None)`(R-14)을 낸다(탭이 있는 열 뒤의 열 값은 한 칸씩 밀린 채 읽힘). 값이 `"`로 시작하면 쓰기는 그대로지만 읽기는 따옴표 인용으로 해석해 따옴표를 벗긴다(`"hi" there` → `hi there`). 값에 `\r`가 있으면 파일 입력(universal newline)에서 행이 쪼개지고 `StringIO`에서는 `csv.Error`(`\r` 줄바꿈 미인용) — 실제 파일·stdin의 정확한 분해는 추론. 따라서 **개행·탭·선행 `"`·`\r`을 가진 제목·장소·설명은 왕복에서 손상되거나 실패한다** | 코드 확인 + 실행 확인(`\r` 파일 경우만 추론) |
| R-07 | 이벤트 하나의 `get`/`data` 예외 | `Conference.get`: `conferenceData`가 있는데 `entryPoints` 키가 없으면 `KeyError`, 빈 리스트면 `IndexError`가 **TSV 전체 출력을 중단**시킨다(`data`는 `.get('entryPoints', [])`라 `[]`를 돌려 JSON은 안전). `Time.get`·`Length.get`은 `s`·`e` 필수. `Calendar.get`·`Email.get`은 `gcalcli_cal` 필수. 제목 없는 이벤트는 `(No title)`이 값으로 출력되어, 그 TSV를 그대로 `agendaupdate`에 넣으면 제목이 문자열 `(No title)`로 바뀐다 | 코드 확인 + 실행 확인 |
| R-08 | `agendaupdate` 진입과 단일 캘린더 | `cli`가 `AgendaUpdate(parsed_args.file)`를 부른다. 첫 줄에서 `DictReader`를 만든 뒤 `len(self.cals) != 1`이면 `GcalcliError('Must specify a single calendar.')`(캘린더 0개 포함; 행을 읽기 전·API 호출 전; `cli.main`이 stderr 출력·종료 1). `--calendar` 지정·기본 캘린더 해석은 [calendar-selection](calendar-selection.md)과 `cli.set_resolved_calendars`(`--calendar` 하나만 허용되는 서브커맨드: 기본 캘린더가 2개 이상이면 무시하고 명시를 요구)를 따른다. 대상 캘린더 `cal`은 `self.cals[0]`(API 캘린더 dict, `id`·`summary`·`timeZone` 사용) | 코드 확인 |
| R-09 | 열 이름과 `action` 판정 | **열 이름 대응**: 출력 열 이름 집합 = `FIELD_HANDLERS` 키 집합(둘 다 `fieldnames`에서 나옴)이라 출력 머리글은 모두 `agendaupdate`가 알아듣는 이름이다. 그러나 `FIELD_HANDLERS`에 없는 이름(예 JSON 키 `attendee_email`, 오타)은 `KeyError(이름)`(R-14). **`action`**: 행마다 `row.get('action', 'patch')`. `ACTIONS = {patch, insert, delete, ignore}`(대소문자 구분)에 없거나 빈 문자열이면 `GcalcliError('Action "X" not supported.')`로 중단. 이어 `getattr(actions, action)(row, cal, self)`. **`action`·`email` 열은 `patch`·`insert`에서 항상 실패한다**: `Action`·`Email`은 `SingleFieldHandler.patch`를 상속하지만 `_patch`를 정의하지 않아 `AttributeError: type object 'Action' has no attribute '_patch'`가 난다. 그래서 `--details action`(또는 `all`)으로 만든 TSV는 `patch` 행에 쓸 수 없고, 명시 `action=patch`·`action=insert`는 동작하지 않는다. `delete`·`ignore`는 핸들러를 부르지 않으므로 `action` 열이 있어도 된다 | 코드 확인 + 실행 확인 |
| R-10 | `actions.patch` | 1) `event_id = row['id']`(`id` 열이 없으면 `KeyError('id')` — **`patch`가 기본 action이므로 `id` 열 없는 TSV는 모두 실패**, 신규 삽입 행도 `id` 열이 필요). 2) `event_id`가 빈 문자열이면 `insert`로 위임(R-11). 3) `_check_writable_fields`(R-12 끝). 4) 열 순서대로 `(fieldname, handler, value)`를 돌며: `fieldname in FIELDNAMES_READONLY`이면 현재 이벤트를 **행당 최대 1회** `events.get(calendarId, eventId)`로 읽어(지연 조회) `handler.patch(cal, curr_event, ...)`(비교만, R-13); 아니면 `handler.patch(cal, mod_event, ...)`. 5) `events.patch(calendarId=cal['id'], eventId=event_id, conferenceDataVersion=1, body=mod_event)`. **본문에는 `id` 열이 있으므로 항상 `'id': event_id`가 든다**(`ID.patch`가 씀). 모든 호출은 `_retry_with_backoff` 경유. 반환값 사용 없음 | 코드 확인 + 실행 확인 |
| R-11 | `Time.patch`(날짜·시각 열) | `fieldname`을 `_`로 나눠 `start`/`end`와 `date`/`time`으로 해석. **`*_date`**: `body[start|end] = {}`를 **새로 만들고**(앞서 쓴 같은 쪽 값은 사라짐) `parse(value, default=TODAY)`로 읽어 `{'date': 결과.isoformat(), 'dateTime': None}`. `TODAY`가 `datetime.date`라서 `dateutil`의 `default.replace(...)`가 `date`를 돌려주고 `date` 값은 `YYYY-MM-DD`가 된다(시각이 든 값, 예 `Dec 3 10:00`을 `*_date`에 넣으면 `date.replace`가 시·분 인자를 못 받아 `TypeError`). 값이 빈 문자열이면 `ParserError`, 해석 불가면 `ParserError`(모두 중단). `TODAY`는 모듈 import 시 `datetime.now().date()` — 연도·월 없는 입력(`12/25`)의 기본값이고 프로세스 수명 동안 고정. **`*_time`**: 값이 공백뿐이면 **아무것도 안 함**(종일 일정 유지). 아니면 같은 쪽의 `date`가 **이미 `body`에 있어야** 한다(앞선 열; 없으면 `KeyError('start'|'end')`), `parse(value, default=isoparse(date))`로 `dateTime = isoformat()`(오프셋 없는 naive 문자열, 예 `2026-12-01T10:30:00`), `date = None`, `timeZone = cal['timeZone']`. 종일 사례: `start_date=2026-12-01`, 빈 `start_time`, `end_date=2026-12-02`, 빈 `end_time` → `start={'date':'2026-12-01','dateTime':None}`, `end={'date':'2026-12-02','dateTime':None}`(`timeZone` 없음). 열 순서는 `*_date` → `*_time`이어야 한다(출력 머리글 순서가 이를 만족). `*_date`만 있고 `*_time` 열이 없으면 그 쪽을 종일 형태로 보낸다(timed 일정이라도) | 코드 확인 + 실행 확인(`TypeError`는 `dateutil` 설치본 실행) |
| R-12 | `Length.patch`와 충돌 검사 | `_check_writable_fields`: 행에 `length`와 (`end_date` 또는 `end_time`) 열이 **함께 있으면**(값이 비어도) `NotImplementedError`(메시지 없음; API 호출 전, `patch`·`insert` 모두). `Length.patch`: `body['start']`가 있어야 한다(없으면 `KeyError('start')` → `start_date`·`start_time`이 `length`보다 앞 열이어야 함). `start['date']`가 참(종일 시작)이면 `NotImplementedError`. 아니면 `end = {'date': None, 'dateTime': isoformat(start + get_timedelta_from_str(value)), 'timeZone': cal['timeZone']}`. `get_timedelta_from_str`([input-parsing](input-parsing.md))는 `1:30:00`·`1 day, 2:00:00`(`str(timedelta)` 출력 형식)·`90`(분)·`1h 30m`을 받아 출력 형식이 왕복된다. 빈 문자열은 0 길이(`end == start`), 해석 불가는 `ValueError` | 코드 확인 + 실행 확인 |
| R-13 | 읽기 전용 열 | `Url.patch`: `html_link`는 **무조건** `ReadonlyError(fieldname, '…Remove it from the input.')`(비교 불가를 이유로 열 제거를 안내); `hangout_link`는 현재 이벤트의 `hangoutLink`(없으면 `''`)와 값이 같으면 통과, 다르면 `ReadonlyCheckError`(`Current value "X" does not match update value "Y"`). `Calendar.patch`: `cal['summary']`(args의 대상 캘린더)와 값이 다르면 `ReadonlyCheckError`(이벤트 쪽 `gcalcli_cal`이 아니라 `cal`과 비교, 현재 이벤트 조회 결과는 쓰지 않지만 `events.get`은 일어난다). 통과하면 본문에 아무것도 안 쓴다. 이 예외는 `GcalcliError`가 아니라서 `cli.main`이 잡지 못해 **traceback으로 종료**한다(R-14). 효과: `--details url`로 낸 TSV는 `html_link` 열 때문에 `agendaupdate`에 못 쓴다(열을 지워야 함). **`insert`**: 읽기 전용 열이 하나라도 있으면(빈 값이어도) `ReadonlyError("Cannot specify value on insert.")`를 만들려 하지만 생성자가 인자 2개(`fieldname`, `message`)를 요구해 실제로는 `TypeError: __init__() missing 1 required positional argument: 'message'`가 난다 | 코드 확인 + 실행 확인 |
| R-14 | 행·열 형식 오류와 중단 | 행은 순서대로 처리되고 **오류가 나면 이후 행은 처리되지 않으며 이전 행의 API 호출은 유지**된다(트랜잭션·미리보기 없음). 구체: ① 알 수 없는 열 이름 → `KeyError(이름)`; ② 머리글보다 긴 행 → `KeyError(None)`; ③ 머리글보다 **짧은** 행 → 빠진 열 값은 `None`(`DictReader` 기본)으로 핸들러에 들어가 `summary`·`location` 등은 JSON `null`(예 `{'summary': None}`)로 patch(필드 삭제 의도가 아닌 우연; `None`을 `.strip()`하는 `Time` 열은 `AttributeError`·`TypeError`); ④ 첫 열 머리글에 BOM이 붙으면 `id`가 `'﻿id'`가 되어 `KeyError('id')`; ⑤ 머리글만 있거나 빈 입력이면 아무 일도 안 함; ⑥ 빈 줄은 무시. `GcalcliError`(R-08·R-09의 action 오류)만 `cli.main`이 `err_msg`로 출력하고 종료 코드 1, 나머지는 traceback | 코드 확인 + 실행 확인 |
| R-15 | `Conference.patch` | 값이 빈 문자열이면 아무것도 안 함. 아니면 `body['conferenceData']['entryPoints'][0][prop] = value`(`prop`은 `conference_entry_point_type` → `entryPointType`, `conference_uri` → `uri`; entry point가 없으면 빈 dict를 만들어 채움). 항상 **첫 entry point 하나만** 쓰고 `meetingCode`·`passcode`·`regionCode`는 쓸 수 없다. API 호출은 `conferenceDataVersion=1`을 붙인다(`createRequest` 같은 키는 만들지 않으므로 새 화상회의는 만들지 못하고 기존 데이터 수정만 의도된 형태 — 서버 동작은 U-03). `fieldnames`에 없는 `conference_*`·`meeting_code` 열은 `KeyError` | 코드 확인 + 실행 확인(서버 동작 제외) |
| R-16 | `Attendees` 왕복 | `get`은 이메일만 `;`로 잇는다(응답 상태 소실). `patch`는 값이 비면 무시, 아니면 `body['attendees'] = [{'attendees': value}]` — 키가 API의 `email`이 아니라 **열 이름 `attendees`** 이고 값은 `a@x;b@x` 한 문자열이다(`ATTENDEE_PROPS`는 `patch`에서 쓰이지 않음). 따라서 참석자가 있는 이벤트의 TSV를 되먹이면 잘못된 본문(`{'attendees': [{'attendees': 'a@x;b@x'}]}`)을 보낸다. 참석자가 없는 행(빈 열)은 안전 | 코드 확인 + 실행 확인(서버가 거부하는지는 U-02) |
| R-17 | 시각 왕복의 시간대·종일 | `Time.get`의 `s`·`e`는 event-query의 현지(`tzlocal()`) 시각이고 `Time.patch`는 같은 값을 **캘린더의 `timeZone`**으로 보낸다. 로컬 tz ≠ 캘린더 tz이면 수정하지 않은 행도 시각이 이동한다(추론: 두 코드 경로의 결합, 실제 tz 불일치는 재현 안 함). `is_all_day`는 `s`·`e`가 모두 00:00인 것을 종일로 본다(`utils.is_all_day`의 XXX 주석) — 자정~자정의 **시각 지정** 이벤트도 시각 칸이 빈 채 출력되어 왕복하면 종일 일정(`date`)으로 바뀐다. 출력된 종일 행(`end_date`는 API의 배타적 종료일)을 되먹이면 같은 `date` 값으로 patch(`dateTime: None`) | 코드 확인 + 실행 확인(tz 불일치는 추론) |
| R-18 | `insert` | `actions.insert`: `_check_writable_fields` → 열 순서대로 핸들러 `patch`(읽기 전용 열이 있으면 R-13의 `TypeError`) → `events.insert(calendarId=cal['id'], conferenceDataVersion=1, body=event)`. 본문에 `'id': ''`가 든다(`id` 열이 비어 있으므로). 도달 경로: `id`가 빈 `patch` 행(`action` 열 없이)만 성공한다. `action=insert`는 R-09의 `Action.patch` 버그로 항상 실패하고, `id` 열 없는 행은 R-10의 `KeyError('id')`다 | 코드 확인 + 실행 확인(서버의 `id: ''` 처리는 U-02) |
| R-19 | `delete`·`ignore` | `delete`: `interface.delete(cal['id'], row['id'])`(`gcal.py:989-994`, `events.delete`). `id` 열이 없으면 `KeyError('id')`, **빈 `id`면 `eventId=''`로 요청을 보낸다**(검증 없음). 다른 열은 읽지 않는다. `ignore`: 아무것도 안 하고 인자를 무시 | 코드 확인 + 실행 확인 |
| R-20 | 원본 테스트 | `tests/`에서 `tsv`·`agendaupdate`·`details`·`actions`를 파일명·내용으로 검색해 이 기능을 다루는 테스트를 찾지 못했다(`grep -rn "tsv\|agendaupdate\|details\|actions" tests` 범위 `tests/`; `tests/test_gcalcli.py`의 `json`은 데이터 파일 로드). 위 규칙은 코드와 스텁 실행이 근거 | 코드 확인(검색, 놓칠 가능성: 동적 호출) |

- 불변식: ① `agendaupdate`가 만드는 모든 API 호출은 `cal['id']`(`self.cals[0]`) 하나를 대상으로 한다(R-08). ② `get`/`data`는 이벤트를 바꾸지 않는다. ③ `patch` 핸들러는 `event`(본문)만 바꾸고, 읽기 전용 핸들러는 **어떤 경우에도 본문을 쓰지 않는다**(R-13). ④ 출력 열 이름 집합은 `agendaupdate`가 받는 열 이름 집합과 같다(R-09). 왕복 가능성(출력 → 입력 → 같은 일정)은 **불변식이 아니다**: R-06·R-07·R-09·R-13·R-16·R-17이 깨는 경우.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-11, R-17 | 서버가 `start: {'date': …, 'dateTime': null}`, `end`만 `date`·`start`는 `dateTime`인 혼합, 오프셋 없는 `dateTime`+`timeZone`을 어떻게 처리하는가(수락·거부·보정) | 재구현이 같은 본문을 보내도 결과가 갈린다(timed 일정에 종일 형태 `start`만 보내는 열 구성 포함) | Calendar API `events.patch` 실제 호출 또는 공식 문서의 `EventDateTime` 규칙 |
| U-02 | R-10, R-16, R-18 | 본문의 `id: ''`(insert), `id`가 경로와 같은 patch, `attendees: [{'attendees': …}]`를 서버가 어떻게 처리하는가 | insert가 실제로 성공하는지, 참석자 왕복이 오류인지 무시인지 | 실제 호출(외부 계정 필요) |
| U-03 | R-15 | `conferenceDataVersion=1`로 `entryPoints`만 있는 `conferenceData`를 patch하면 서버가 수정·무시·거부 중 무엇을 하는가 | 화상회의 열 쓰기의 실효 | 실제 호출 |
| U-04 | R-04 | JSON 키 순서의 무작위성이 모든 실행 환경에서 나타나는가(`PYTHONHASHSEED` 고정 시 어떤가) | 재구현이 키 순서를 고정해도 되는지(소비자는 키로 읽으므로 영향 작음) | `PYTHONHASHSEED=0`·다른 값으로 같은 입력을 여러 번 실행해 비교 |

- 확인 한계: Google Calendar API를 호출할 수 없어 서버 응답(U-01~U-03)은 확인하지 않았다. 아래 "실행 확인"은 **스텁 환경**이다: `/tmp`의 임시 venv에 의존성을 설치(저장소 미변경)하고, 가짜 이벤트(`s`·`e` Asia/Seoul, 캘린더 `{'id': 'c@x', 'summary': 'Work', 'timeZone': 'Asia/Seoul'}`)로 `GoogleCalendarInterface(userless_mode=True, do_eager_init=False, ...)`를 만들어 `_tsv`·`_json`을 stdout 캡처로, `AgendaUpdate`를 `get_events()`(요청 인자를 기록하는 가짜 `get`·`patch`·`insert`·`delete`)와 항등 `_retry_with_backoff`로 돌려 요청 인자를 관찰했다. 실제 argparse 파싱은 `get_argument_parser().parse_args`로 확인했다. 따라서 네트워크·재시도 소진(`None`)·실제 파일·stdin 인코딩은 검증하지 않았다. 테스트 파일은 `/tmp`에만 있고 저장소에는 없다.

### 1.5 필수 코드 참조 [필수]
기준 SHA `405639c27639a82a13538ad72ae012e76942530c`. 라이선스는 overview 1절을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/details.py:1-79` 상수·`_valid_title`·`Handler`·`SingleFieldHandler`·`SimpleSingleFieldHandler` | `get`/`data`/`patch` 계약, `strip`, `(No title)`, `ACTION_DEFAULT`, `URL_PROPS`·`ENTRY_POINT_PROPS` | R-03, R-07, R-09 |
| C-02 | `gcalcli/details.py:81-169` `Time`, `Length` | 날짜·시각 열 분해, `TODAY` 기본, `*_time` 빈 값 무시, 종일 표시, `Length` 계산 | R-11, R-12 |
| C-03 | `gcalcli/details.py:171-294` `Url`, `Conference`, `Attendees` | 읽기 전용 비교, 첫 entry point, 참석자 `patch`의 열 이름 키 | R-13, R-15, R-16 |
| C-04 | `gcalcli/details.py:296-396` `Title`~`Action`, `HANDLERS`, `HANDLERS_READONLY`, `FIELD_HANDLERS`, `FIELDNAMES_READONLY`, `DETAILS`, `DETAILS_DEFAULT` | 열 순서(등록 순서), `_patch` 미정의 클래스(`Email`·`Action`), `Calendar`의 비교 | R-02, R-09, R-13 |
| C-05 | `gcalcli/actions.py:1-106` | `_iter_field_handlers`, `_check_writable_fields`, `patch`·`insert`·`delete`·`ignore`, `ACTIONS`, `CONFERENCE_DATA_VERSION` | R-09, R-10, R-12, R-13, R-18, R-19 |
| C-06 | `gcalcli/gcal.py:727-776` `_tsv`, `_json` | 머리글·행 조립, `\n` 치환, 필터 복제, JSON 줄 구성 | R-03~R-06 |
| C-07 | `gcalcli/gcal.py:1286-1294` `_display_queried_events`, `gcal.py:1348-1359` `AgendaUpdate`, `gcal.py:989-994` `delete` | 분기 우선순위, 단일 캘린더 검사, `action` 판정과 디스패치, `delete` API | R-01, R-08, R-09, R-19 |
| C-08 | `gcalcli/argparsers.py:98-138`, `argparsers.py:520-531`, `gcalcli/cli.py:254-255` | `DetailsAction`·`--details` choices, `agendaupdate` 인자, `AgendaUpdate(parsed_args.file)` 배선 | R-01, R-02, R-08 |
| C-09 | `gcalcli/exceptions.py:11-22` `ReadonlyError`, `ReadonlyCheckError` | 메시지 형식, 생성자 인자 개수(2개) | R-13 |

`_retry_with_backoff`는 [calendar-selection R-11](calendar-selection.md), `is_all_day`·`get_timedelta_from_str`는 [input-parsing](input-parsing.md)의 규칙을 쓴다.

### 1.6 수락 사례 [필수]
출처: 구현에서 도출(스텁 실행, 1.4 확인 한계 환경). 서버 응답·재시도 소진·실제 stdin은 검증하지 않는다. 표의 이벤트는 `id=abc`, 제목 `Hello`, 2026-11-20 14:00~15:30(Asia/Seoul), 캘린더 `Work`.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02, R-03 | `--details` 없이 `_tsv` | `start_date\tstart_time\tend_date\tend_time\ttitle` 머리글 + `2026-11-20\t14:00\t2026-11-20\t15:30\tHello`. `id` 열 없음 |
| T-02 | R-02, R-03 | `--details id --details length --details description` | 머리글 `id start_date start_time end_date end_time length title description`(탭), 행 `abc … 1:30:00 Hello ⟨빈칸⟩` |
| T-03 | R-02, R-03 | `--details all`(`DETAILS` 15개) | 머리글에 `id start_date start_time end_date end_time length html_link hangout_link conference_entry_point_type conference_uri title location description calendar email attendees action`. `reminders`·`attachments`·`end`는 열 없음. 행의 `action`은 `patch`, `calendar`는 `Work`, `email`은 `c@x` |
| T-04 | R-04 | `_json`(`--details id --details attendees`), 이벤트 둘(참석자 `a@x` accepted 포함) | `[` / `{"id": "abc", "title": "Hello", "time": {...4키...}, "attendees": []}` / `,` / `{"id": "d2", …, "attendees": [{"attendee_email": "a@x", "attendee_response_status": "accepted"}]}` / `]`. 키 순서는 실행마다 다를 수 있음. 이벤트 0건 → `[\n]\n` |
| T-05 | R-05 | `ignore_started=True`, `now`=14:30, 이벤트 14:00 시작 | 그 이벤트는 행 없음, 머리글만 |
| T-06 | R-08, R-09, R-10, **대표 흐름** | `agenda --tsv --details id` 출력 `id\tstart_date\tstart_time\tend_date\tend_time\ttitle` / `abc\t2026-11-20\t14:00\t2026-11-20\t15:30\tHello`를 `16:00`·`17:00`·`New title`로 고쳐 `agendaupdate --calendar Work`에 입력 | 요청 1건: `events.patch(calendarId='c@x', eventId='abc', conferenceDataVersion=1, body={'id': 'abc', 'start': {'date': None, 'dateTime': '2026-11-20T16:00:00', 'timeZone': 'Asia/Seoul'}, 'end': {'date': None, 'dateTime': '2026-11-20T17:00:00', 'timeZone': 'Asia/Seoul'}, 'summary': 'New title'}})` |
| T-07 | R-09 | 열 `id`·`action`·`title`, `action=patch` 행 / `action=insert` 행 | 둘 다 `AttributeError: … 'Action' has no attribute '_patch'`, API 요청 없음. `action=ignore` → 요청 없음, 정상 종료. `action=delete` → `events.delete(eventId='abc')` |
| T-08 | R-09 | `action=PATCH` / `action=`(빈) | `GcalcliError('Action "PATCH" not supported.')` / `Action "" …`, 종료 1(CLI), 요청 없음 |
| T-09 | R-10 | `start_date\tstart_time\ttitle`(열 `id` 없음) | `KeyError: 'id'` |
| T-10 | R-18 | 열 `id`·`title`, 행 `\tNew`(빈 id) | `events.insert(conferenceDataVersion=1, body={'id': '', 'summary': 'New'})` (calendarId=`c@x`) |
| T-11 | R-13, R-18 | `id\ttitle\tcalendar`, 행 `abc\tT\tWork` / `abc\tT\tOther` / 빈 id 행 `\tN\tWork` | `events.get(eventId='abc')` 후 `events.patch(body={'id':'abc','summary':'T'})` / `ReadonlyCheckError`(`Current value "Work" does not match update value "Other"`), patch 없음 / `TypeError: ReadonlyError.__init__() missing 1 required positional argument: 'message'` |
| T-12 | R-13 | `id\thangout_link`, `abc\thl`(현재 `hangoutLink`=`hl`) / `id\thtml_link`, `abc\thttp://h` | `events.get` 후 `events.patch(body={'id':'abc'})` / `ReadonlyError`(`Field html_link is read-only. … Remove it from the input.`), patch 없음 |
| T-13 | R-12 | `id\tstart_date\tstart_time\tlength\tend_time`, `abc\t2026-11-20\t10:00\t60\t11:00` | `NotImplementedError`, 요청 없음 |
| T-14 | R-12 | 열 `id start_date start_time length`: `abc 2026-11-20 10:00 1:30:00` / 열 순서 `id length start_date start_time` | `end.dateTime='2026-11-20T11:30:00'` 본문 / `KeyError: 'start'` |
| T-15 | R-11 | 종일 행 `id start_date start_time end_date end_time`: `abc 2026-11-21 ⟨빈⟩ 2026-11-22 ⟨빈⟩` / 열 `id start_date`의 값이 빈 문자열 / 열 순서 `id start_time start_date`: `abc 10:00 2026-11-20` / 시각 포함 `Dec 3 10:00`을 `start_date`에 | `body.start={'date':'2026-11-21','dateTime':None}`, `end={'date':'2026-11-22','dateTime':None}` / `ParserError` / `KeyError: 'start'` / `TypeError`(`date.replace`) |
| T-16 | R-06 | 제목 `L1⟨개행⟩L2`·설명 `x⟨개행⟩y`인 이벤트의 `_tsv` 출력 후 그대로 `agendaupdate`(열 `id title`) | 출력 셀은 `L1\nL2`(백슬래시+n 두 글자). 입력하면 `summary: 'L1\\nL2'`(개행이 아니라 두 글자) |
| T-17 | R-06 | 제목 `Line1⟨개행⟩Line2⟨탭⟩Tab "q"`의 `_tsv`(열 `id title description`) | 한 줄에 셀 4개(`… Line1\nLine2`, `Tab "q"`, …). 입력하면 `KeyError: None` |
| T-18 | R-06 | 입력 제목 셀 `"hi" there` / `say "hi"` | `summary='hi there'` / `summary='say "hi"'` |
| T-19 | R-14 | 행 3개 `abc T` / `abc2 U` / 짧은 `abc3`(열 `id title`) / 행 2에 `action=foo`가 있는 입력 | 1~3행이 순서대로 patch(3행 `summary: None`) / 2행에서 `GcalcliError`, 1행 patch는 이미 전송됨, 3행 미처리 |
| T-20 | R-14 | 열 `id title`에 `abc\tT\textra` / 열 `id foo` / 머리글만 | `KeyError: None` / `KeyError: 'foo'` / 요청 없음 |
| T-21 | R-08 | `--calendar` 없이 `cals` 2개(또는 0개) | `GcalcliError('Must specify a single calendar.')`, 행 처리 전 |
| T-22 | R-16 | `id\tattendees`, `abc\ta@x;b@x` | `body={'id':'abc','attendees':[{'attendees':'a@x;b@x'}]}` |
| T-23 | R-07 | 제목 없는 이벤트(`summary` 공백)의 `_tsv --details id --details location` 출력을 그대로 입력 | 셀 `(No title)`; patch 본문 `summary: '(No title)'`, `location: ''` |
| T-24 | R-07 | `conferenceData={'entryPoints': []}`의 `Conference.get` / `{}`의 `get` / `data` | `IndexError` / `KeyError('entryPoints')` / `data`는 `[]` (`_tsv --details conference` 전체 중단) |
| T-25 | R-01 | `parse_args`: `agenda --tsv --json`, `search x --tsv --details all`, `updates --tsv`, `agendaupdate --details id` | 둘 다 True / `tsv=True`, `details` 15키 / `since` 누락으로 종료 2(옵션 자체는 파서에 있음) / 종료 2(옵션 없음) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@405639c `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-07(`gcal.py:1286-1294`), C-08(`argparsers.py:98-138, 187-200, 476-515`), `cli.py:254-310`, event-query R-11·R-14·R-15 | 줄 추적 + `parse_args` 실행(T-25). 부재 주장 "`updates`·`conflicts`·`edit`·`delete`가 `tsv`·`json`을 읽지 않음": `grep -n "get('tsv')\|get('json')" gcalcli` → `gcal.py:1288,1292`뿐(범위 `gcalcli/`; 놓칠 가능성: `options['tsv']` 직접 접근 — 같은 grep에서 `options\['tsv'\]` 없음) |
| R-02 | C-08(`argparsers.py:98-138`), C-04(`details.py:369-396`), C-06(`gcal.py:727-731, 752-754`) | 줄 추적 + 실행(T-01~T-03). 열 순서가 `HANDLERS` 순서라는 점은 리스트 컴프리헨션(`gcal.py:730`) 순서로 확인 |
| R-03 | C-06(`gcal.py:727-750`), C-01~C-04 | 줄 추적 + 스텁 실행(T-01~T-03, T-24) |
| R-04 | C-06(`gcal.py:752-776`) | 줄 추적 + 스텁 실행(T-04). 키 순서 무작위성은 `set` 순회 + 문자열 해시 무작위화로 인한 추론, 두 실행의 관찰(U-04) |
| R-05 | C-06(`gcal.py:740-743, 760-763`), `gcal.py:1258-1261` `_DeclinedEvent`, event-query R-10 | 줄 추적 + 스텁 실행(T-05; `ignore_declined`는 `self` 표시 참석자 `declined`로 실행해 행 제외 확인) |
| R-06 | C-06(`gcal.py:749`), C-07(`gcal.py:1349`), `csv.excel_tab` | 줄 추적 + 스텁 실행(T-16~T-18). `\r`: `StringIO`에서 `csv.Error` 관찰, 실제 파일·stdin의 universal newline 분해는 파이썬 `open` 기본 동작에서의 추론. 역변환 부재 주장: `grep -n "\\\\\\\\n\|replace(" gcalcli/gcal.py gcalcli/actions.py gcalcli/details.py` → `gcal.py:749` 쓰기 쪽뿐(범위: 세 파일) |
| R-07 | C-01(`details.py:24-28`), C-03(`details.py:205-227`), C-04(`details.py:339-350`), 실행(T-23, T-24) | 줄 추적 + 스텁 실행 |
| R-08 | C-07(`gcal.py:1348-1359`), `cli.py:254-255, 398-433`, C-08(`argparsers.py:520-531`) | 줄 추적 + `parse_args` 실행(T-21은 `cals`를 직접 대입한 스텁). 실제 `--calendar` 해석은 calendar-selection |
| R-09 | C-04(`details.py:53-67, 339-366`), C-05(`actions.py:9-13, 30-68`), C-07 | 줄 추적 + 스텁 실행(T-07, T-08). 버그 근거: `grep -n "_patch" gcalcli/details.py` → `SingleFieldHandler.patch`·`SimpleSingleFieldHandler._patch`·`Title._patch`만, `Email`·`Action`·`Calendar`(`patch` 재정의로 우회)에 `_patch` 없음 |
| R-10 | C-05(`actions.py:30-68`), 실행(T-06, T-09) | 줄 추적 + 스텁 실행. 본문 `id` 포함은 `ID.patch`가 `SimpleSingleFieldHandler._patch`로 `event['id']`를 씀(`details.py:69-79, 353-356`) |
| R-11 | C-02(`details.py:81-138`) | 줄 추적 + 스텁 실행(T-15, T-06). `TODAY` 정의 `details.py:14`; 부재 주장: `TODAY`가 다른 곳에서 갱신되지 않음 — `grep -rn "TODAY" gcalcli` → 정의 `details.py:14`와 사용 `details.py:118`뿐 |
| R-12 | C-05(`actions.py:15-27`), C-02(`details.py:140-169`), input-parsing(`utils.py:142-175`) | 줄 추적 + 스텁 실행(T-13, T-14) |
| R-13 | C-03(`details.py:171-203`), C-04(`details.py:322-336`), C-09(`exceptions.py:11-22`), C-05(`actions.py:43-58, 79-80`), `cli.py:64-66` | 줄 추적 + 스텁 실행(T-11, T-12). 예외가 `GcalcliError`가 아님은 `exceptions.py`의 상속(`Exception`) + `cli.py:64`의 `except GcalcliError`로 확인 |
| R-14 | C-05, C-07, `csv.DictReader` 기본(`restkey=None`, `restval=None`) | 스텁 실행(T-19, T-20). BOM·짧은 행은 실행으로 확인 |
| R-15 | C-03(`details.py:205-255`), C-05(`actions.py:6`) | 줄 추적 + 스텁 실행. 서버 동작은 U-03 |
| R-16 | C-03(`details.py:257-294`) | 줄 추적 + 스텁 실행(T-22). `ATTENDEE_PROPS`가 `patch`에서 안 쓰임은 줄로 확인(`details.py:262-264`는 `data`에서만 사용) |
| R-17 | C-02(`details.py:81-138`), `utils.py:188-198` `is_all_day`, event-query 1.3(`s`·`e`는 `tzlocal()` 변환) | 줄 추적. 시간대 불일치는 두 코드 경로를 결합한 추론, 종일/자정 혼동은 `utils.py`의 XXX 주석 + 스텁(T-15) |
| R-18 | C-05(`actions.py:71-91`) | 줄 추적 + 스텁 실행(T-10, T-11) |
| R-19 | C-05(`actions.py:94-103`), C-07(`gcal.py:989-994`) | 줄 추적 + 스텁 실행 |
| R-20 | 파일명 검색 `ls tests`(`test_argparsers.py`·`test_auth.py`·`test_conflicts.py`·`test_gcalcli.py`·`test_input_validation.py`·`test_printer.py`·`test_utils.py`, `cli/`, `data/`) + 내용 grep | 검색 범위 `tests/`. 사례 본문은 열지 않았다(경계·오류를 코드로 정했음) |
| T-01~T-25 | `/tmp`의 임시 스텁 스크립트(저장소 밖, 보존하지 않음). 환경은 1.4 확인 한계 | 요청 인자는 가짜 `Ev` 객체가 기록한 `calendarId` 제외 값.  |

### 2.2 코드 읽는 순서 [선택]
`argparsers.py`의 `DetailsAction`·`agendaupdate` 정의 → `details.py`(`Handler` 계층 → `HANDLERS`·`FIELD_HANDLERS`) → `gcal.py`의 `_tsv`·`_json`·`AgendaUpdate` → `actions.py`. `Handler`는 읽기(`get`/`data`)와 쓰기(`patch`)를 한 클래스에 두고, 쓰기는 "API 본문 dict를 순서 의존적으로 채우는" 방식이라(`Length`가 `Time`이 만든 `start`를 읽음) 열 순서가 의미를 가진다는 점이 구현 전략이다.

### 2.4 검토 기록 [필수, ready 스펙]
- **작성자 점검**: /tmp 임시 venv에서 Google API를 스텁으로 바꿔 `_tsv`·`_json`·`AgendaUpdate`와 핸들러를 직접 실행하고 `parse_args`도 돌려 관찰했다(서버 응답 제외). `tests/`에는 이 기능을 다루는 테스트가 없다.
- **메인 세션 점검(2026-11-18)**: `check.py` 통과, `repos/gcalcli` 변경 없음. 고위험 R-09를 원본으로 대조해 일치: `Action`·`Email`은 `SingleFieldHandler`를 상속하지만 `_patch`를 정의하지 않는다(`details.py`에서 `_patch` 정의는 `SimpleSingleFieldHandler` 77행과 `Title` 306행뿐). 그래서 `patch`·`insert` 행에 이 열이 있으면 `AttributeError`가 된다. `actions.patch`가 `row['id']`를 읽으므로(`actions.py:32`) 기본 출력(`time`·`title`)에는 `id` 열이 없어 `--details id`가 필요하다는 점도 확인했다.
- **독립 검토 미수행**: 이 스펙에 의존하는 스펙이 없고 계획(3·4·6만)에 따랐다. 이상 동작 후보가 많아(R-06, R-09, R-11~R-13, R-16, R-17) 필요하면 이 R-ID부터 독립 검토를 돌린다.
- **status를 `draft`로 유지하는 이유**: U-01~U-04(서버 동작·키 순서)가 열려 있고 선행 스펙이 `draft`다.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| (없음) | 원본의 버그(R-09·R-13·R-16·R-18)를 고치는 판단은 이 스펙에서 하지 않는다 | 본문은 기준 SHA의 동작이다 | — |
