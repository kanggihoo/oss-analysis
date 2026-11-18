---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/gcal.py
  - gcalcli/conflicts.py
  - gcalcli/_types.py
  - gcalcli/argparsers.py
  - gcalcli/cli.py
  - gcalcli/utils.py
  - tests/test_conflicts.py
  - tests/test_gcalcli.py
  - tests/conftest.py
depends:
  - calendar-selection.md
  - input-parsing.md
status: draft
---

# 일정 조회·검색·갱신분·충돌 (내부 이벤트 표현)

> 선택된 캘린더(`self.cals`)마다 Calendar API `events.list`를 시작·끝·검색어로 페이지 끝까지 호출해 취소·2038년 이후 일정을 거르고, 각 이벤트 dict에 현지 시각 `s`·`e`와 소속 캘린더 `gcalcli_cal`을 덧붙여 `s` 순으로 합친 **내부 이벤트 목록**을 만들고, 그 목록으로 `agenda`·`search`·`updates`·`conflicts` 네 서브커맨드의 필터(`--nostarted`, `--nodeclined`, 갱신 시각, 겹침)를 적용해 출력 단계에 넘긴다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `cli.main`이 [config-resolution](config-resolution.md)·[calendar-selection](calendar-selection.md)으로 `GoogleCalendarInterface`(이하 gcal)를 만들어 `self.cals`를 확정한다. 서브커맨드 인자(`start`·`end`·`since`·`text`)는 argparse가 [input-parsing](input-parsing.md)의 `get_time_from_str`로 tz-aware datetime으로 바꿔 둔다(R-16).
2. 서브커맨드 메서드(`AgendaQuery`/`TextQuery`/`UpdatesQuery`/`ConflictsQuery`)가 누락된 `start`·`end`를 기본값으로 채운다(R-12~R-15).
3. `_search_for_events(start, end, text)`가 `self.cals` 순서대로 `_GetAllEvents`를 돌려 한 목록으로 모은 뒤 `s`로 안정 정렬한다(R-07).
4. `_GetAllEvents`는 캘린더 하나에 대해 `events().list(..., singleEvents=True, pageToken)`을 `nextPageToken`이 없을 때까지 호출하고, 이벤트마다 `gcalcli_cal` 부착 → 취소 건너뛰기 → `s`·`e` 변환 → `s >= end` 제외 → 2038년 제외 순서로 처리해 통과한 것만 내보낸다(R-01~R-06).
5. 커맨드별 후처리: `agenda`·`search`는 `tsv`/`json` 옵션이면 직렬화 함수, 아니면 `_iterate_events`로 보낸다(R-11). `updates`는 `updated >= since`만 남기고(R-14), `conflicts`는 `_iterate_events`에 `ShowConflicts`를 `work`로 걸어 겹치는 앞선 일정을 추가 출력한다(R-15).
6. `_iterate_events`가 `--nostarted`·`--nodeclined`를 적용하고 통과한 이벤트마다 `_PrintEvent`를 부르고 통과 수를 돌려준다(R-10). 렌더링 자체는 이 스펙 밖이다.

### 1.2 범위·통합 지점 [필수]
- 제공: 위 네 서브커맨드의 조회 흐름, `_GetAllEvents`·`_search_for_events`(다른 스펙이 재사용), `_DeclinedEvent`, `_iterate_events`의 필터·카운트·`work` 훅, `ShowConflicts`, **내부 이벤트 표현**(1.3).
- 제외: 출력 렌더링 `_PrintEvent`·`_GraphEvents`(행 5), TSV/JSON 직렬화 `_tsv`·`_json`의 필드·포맷(행 9; 이 스펙은 필터가 중복되어 있다는 사실과 호출 조건만 R-11에 쓴다), 수정·삭제 흐름(행 8), 캘린더 선택(calendar-selection), 시각 문자열 파싱·`localize_datetime`의 정의(input-parsing).
- 외부 의존·선행 계약: `self.cals`(calendar-selection 1.3: `all_cals` 항목 dict의 별칭 목록, 중복 가능), `_retry_with_backoff`(calendar-selection R-11: 성공 시 응답 dict, 재시도 소진 시 `None`, 그 밖에는 예외), `utils.localize_datetime`·`utils.get_time_from_str`(input-parsing), `dateutil.parser.parse`·`relativedelta`, 시계 `self.now`(R-17), Google Calendar API `events.list`.
- 소유 상태·부작용: API 응답 이벤트 dict를 **제자리에서 변형**한다(`gcalcli_cal`, `s`, `e` 키 추가). 이 스펙이 만드는 영속 상태는 없다. `updates`는 stdout에 `Updates since: ...` 줄을 직접 `print`한다(R-14). 출력은 `printer`·stdout.

### 1.3 인터페이스와 데이터 의미 [필수]
**내부 이벤트 표현 (스펙 5·8·9의 선행 계약)**

`_GetAllEvents`가 내보내는 이벤트 하나. 타입은 `_types.Event`(타입 힌트상 Google `Event` + `gcalcli_cal`, `s`, `e`; 런타임에는 `dict[str, Any]`).

| 키 | 타입 | 불변식·의미 |
|---|---|---|
| (API 필드 전부) | Google `Event` 리소스 dict | 응답 그대로. 이 스펙이 코드로 읽는 키: `status`, `start`·`end`(`dateTime` 또는 `date`), `updated`, `attendees[]`(`self`, `email`, `responseStatus`). 이벤트에 `start`·`end`가 있다고 가정한다(R-03) |
| `gcalcli_cal` | `CalendarListEntry` dict | 이 이벤트를 가져온 `self.cals` 항목과 **같은 객체**(복사 아님). `_GetAllEvents`에 넘긴 `cal` 인자. 이 스펙 밖 코드가 읽는 키: `id`, `summary`, `timeZone`, `accessRole`, `colorSpec`. **조회가 소유자**다. 취소된 이벤트에도 붙지만 그런 이벤트는 내보내지 않는다 |
| `s` | tz-aware `datetime` | 시작. tzinfo는 항상 `dateutil.tz.tzlocal()`(R-04). 종일 이벤트는 **현지 자정**(UTC 자정이 아님) |
| `e` | tz-aware `datetime` | 끝. `s`와 같은 규칙. 종일 이벤트는 API의 `end.date`(배타적 끝날짜) 현지 자정이라 `e - s`가 일 수가 된다 |

- `_search_for_events`가 돌려주는 목록의 불변식: 모든 원소가 위 표를 만족하고, `s` 오름차순이다(같은 `s`끼리는 `self.cals` 순서 → 페이지 순서 → 페이지 안 순서: Python 안정 정렬). `e`는 정렬에 쓰지 않으므로 `e` 순서는 보장되지 않는다. `s.year < 2038`이고 `e.year < 2038`이다. `status != 'cancelled'`다. `end`가 주어졌다면 `s < end`다. **`s >= start`와 `e > start`는 보장하지 않는다**(R-05). 같은 실제 일정이 선택된 캘린더 둘 이상에 있으면 캘린더 수만큼 **별개 dict**로 중복된다(`id`가 같고 `gcalcli_cal`이 다름).
- 이 불변식이 성립하는 시점은 `_search_for_events` 반환 직후까지다. 이후 스펙 8의 `_SetEventStartEnd`(`gcal.py:1024-1026`)가 `event['s']`를 `dateutil.parse(문자열)` 결과로 **덮어쓰므로**(tz 보장 없음) 편집 뒤의 이벤트는 이 계약 밖이다(스펙 8이 다룬다).

**연산**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `_GetAllEvents(cal, start, end, search_text)` | `CalendarListEntry`, `datetime\|None`, `datetime\|None`, `str\|None` → **generator** of Event | R-01~R-06. 지연 평가: 소비하는 만큼 페이지를 요청한다 |
| `_search_for_events(start, end, search_text)` | 같은 인자 → `list[Event]` | R-07. 호출자: `_display_queried_events`(agenda·search), `UpdatesQuery`, `ConflictsQuery`, `CalQuery`(calw·calm), `ModifyEvents`(edit·delete), `Remind`(R-18) |
| `_DeclinedEvent(event)` | Event → bool | R-09 |
| `_iterate_events(start_datetime, event_list, year_date=False, work=None)` | → int(선택 수) | R-10. `start_datetime`은 쓰이지 않는다 |
| `ShowConflicts(show)` | `show`: callable 또는 None(None이면 `print(e)`) | `show_conflicts(latest_event)`, R-15 |
| `AgendaQuery(start=None, end=None)` / `TextQuery(search_text='', start=None, end=None)` / `UpdatesQuery(last_updated_datetime, start=None, end=None)` / `ConflictsQuery(search_text='', start=None, end=None)` | | R-12~R-15 |

**CLI (외부 계약)**

| 서브커맨드 | 위치 인자 | 옵션 |
|---|---|---|
| `agenda` | `[start] [end]` (둘 다 선택, `get_time_from_str`) | `--calendar`(calendars_parser), `--details`, 출력 옵션 중 `--tsv`·`--json`·`--nostarted`·`--nodeclined`(기본 False) 등 |
| `search` | `text`(**필수**, `nargs=1` → 리스트) `[start] [end]` | 같음 |
| `updates` | `since`(**필수**) `[start] [end]` | 같음 |
| `conflicts` | `[text] [start] [end]` | 같음 |

네 서브커맨드 모두 `parents=[calendars_parser, details_parser, output_parser, <위 파서>]`(`argparsers.py:473-558`). `--nostarted`는 dest `ignore_started`, `--nodeclined`는 dest `ignore_declined`(`argparsers.py:202-215`). 위치 인자 파서의 시각 인자는 `utils.get_time_from_str`이라 tz-aware다(input-parsing).

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `_GetAllEvents`의 API 요청 | `events().list`를 `calendarId=cal['id']`, `timeMin=start.isoformat()`(`start`가 거짓이면 `None`), `timeMax=end.isoformat()`(같음), `q=search_text`(거짓이면 `None`), `singleEvents=True`, `pageToken`으로 호출한다. `orderBy`·`maxResults`·`showDeleted`·`timeZone`은 보내지 않는다. 호출은 `_retry_with_backoff`를 거친다. `None` 값 인자는 API 클라이언트가 요청에 싣지 않는다(googleapiclient 동작: 추론) | 코드 확인 / 추론(None 생략) |
| R-02 | 페이지네이션 | 첫 호출 `pageToken=None`. 응답마다 `events.get('items', [])`를 처리하고 `nextPageToken`을 읽어 없거나 빈 값이면 종료, 있으면 같은 인자에 그 토큰으로 다시 호출한다. 한 캘린더의 이벤트는 페이지 순서대로 내보낸다. `_retry_with_backoff`가 `None`(재시도 소진)을 돌려주면 `None.get`으로 `AttributeError`가 나고(재시도 소진 시 조용한 빈 결과가 아니라 예외), `HttpError`는 그대로 전파된다. 재시도·오류 변환은 없다. 한 페이지를 처리하는 도중 예외가 나면 그 전까지 내보낸 이벤트는 호출자(`list.extend`)가 이미 일부 받았더라도 `_search_for_events`가 예외로 끝나 **결과 목록 전체가 버려진다** | 코드 확인 |
| R-03 | 이벤트별 처리 순서 | 1) `event['gcalcli_cal'] = cal` 대입(취소 이벤트도 대입된다). 2) `'status' in event and event['status'] == 'cancelled'`이면 이 이벤트를 **건너뛴다**(이 시점까지 `start`·`end` 키를 읽지 않으므로 `start`가 없는 취소 이벤트도 안전). 3) `s` 계산·현지화. 4) `e` 계산·현지화. 5) `end`가 참이고 `s >= end`이면 건너뛴다. 6) `s.year >= 2038` 또는 `e.year >= 2038`이면 건너뛴다. 7) 통과분을 `yield`. 취소가 아닌데 `start`/`end`에 `dateTime`·`date`가 모두 없으면 `KeyError`로 전체 조회가 실패한다 | 코드 확인 |
| R-04 | `s`·`e` 변환 | `start`/`end`에 `'dateTime'` 키가 있으면 `parse(dateTime)`(API가 주는 RFC 3339 오프셋 포함 → tz-aware), 없으면 `parse(date)`(`YYYY-MM-DD` → **tz 없는 naive datetime, 자정**). 결과를 `utils.localize_datetime`에 넘긴다: tzinfo가 `None`이면 `replace(tzinfo=tzlocal())`(**같은 시계 숫자를 유지하고 현지 시간대만 붙임**, 즉 종일 이벤트는 UTC 자정이 아니라 현지 자정), tz-aware이면 `astimezone(tzlocal())`(시각 보존, 현지 표시로 변환). 따라서 `s`·`e`는 어느 경우든 tzinfo가 `tzlocal()`이다. `start.timeZone` 필드와 캘린더 `timeZone`은 쓰지 않는다 | 코드 확인 |
| R-05 | 시작 시각 필터 `end and s >= end` | `end`가 거짓(`None`)이면 필터 없음. 참이면 현지화된 `s`가 `end` 이상인 이벤트를 제외한다. 의도 주석: Google이 종일 이벤트 시각을 현지가 아닌 UTC 기준으로 가정하는 것 같아 `timeMax`가 걸러 주지 못한 "끝 이후에 시작하는 종일 이벤트"를 걸러낸다. **반대쪽(`start`)에는 대응 필터가 없다**: `timeMin`은 API만이 적용하므로 현지 자정으로 해석한 종일 이벤트가 `start` 전에 끝나 있어도(`e <= start`, 또는 `s < start`) API가 돌려주면 그대로 통과한다. API가 `timeMin`/`timeMax`를 어떻게 해석하는지(종일 이벤트를 UTC 날짜로 보는지)는 미확인(U-01) | 코드 확인 / 외부 동작 미확인 |
| R-06 | 2038년 필터 | `s.year >= 2038 or e.year >= 2038`이면 제외(`dateutil`의 파싱 오류를 피하려는 주석). 현지화 **후**의 연도로 판정한다(UTC 12-31 늦은 시각이 현지 2038-01-01이 될 수 있다). `parse` 자체가 던지는 예외는 잡지 않는다. 반복 일정(`singleEvents=True`로 인스턴스 전개)의 먼 미래 인스턴스를 거르는 것이 실사용 효과(추론) | 코드 확인 / 추론(실사용 효과) |
| R-07 | `_search_for_events` | `event_list = []`; `self.cals`를 순서대로 돌며 `_GetAllEvents(cal, start, end, search_text=search_text)`를 소진해 `extend`; 끝나면 `event_list.sort(key=lambda x: x['s'])`. 캘린더 수만큼 **직렬 호출**이다(병렬 없음). `self.cals`가 비면 API 호출 없이 `[]`. 중복 제거·`updated` 정렬·`e` 보조 정렬 없음. 같은 `cals` 항목이 중복돼 있으면(calendar-selection R-09) 같은 이벤트가 중복해서 두 번 조회된다 | 코드 확인 |
| R-08 | 다른 스펙이 이 목록을 변형하는 경우 | `_GraphEvents`는 `while ... event_list[0]['s'] < start_datetime: event_list = event_list[1:]`로 지역 이름을 슬라이싱으로 다시 바인딩하므로 호출자의 목록은 변형되지 않는다(`gcal.py:583`). 이 스펙의 함수는 목록을 정렬 외에 변형하지 않는다. 이벤트 dict의 `s`·`e`·`gcalcli_cal` 변형은 `_SetEventStartEnd`(스펙 8)뿐이다. 그 함수는 `s`를 문자열 `parse` 결과로 덮고(`gcal.py:1025`) `e`는 대입이 아닌 뺄셈 식(`event['e'] - parse(end)`, 1026)이라 갱신하지 않으며, `event['start']`·`['end']` API 필드를 통째로 교체한다(1030-1041). 그래서 편집 뒤에는 `s`만 새 값, `e`는 옛 값, `start`/`end`는 새 값인 불일치 상태가 되어 이 절의 불변식이 깨진다(`grep -n "\['s'\] *=\|\['e'\] *=\|\['gcalcli_cal'\] *=" gcalcli/*.py` → `gcal.py:1025`(`_SetEventStartEnd`)와 `1209-1228`(`_GetAllEvents`)뿐. `1026`은 `event['e'] - parse(end)`로 대입이 아니라 결과가 버려지는 식이라 `e`는 갱신되지 않는다) | 코드 확인(범위 `gcalcli/*.py`, 동적 접근 제외) |
| R-09 | `_DeclinedEvent(event)` | `event.get('attendees', [])`에서 `'self' in a`(키 존재만, 값 무관) **또는** `a['email'] == event['gcalcli_cal']['id']`인 참석자 중 `responseStatus == 'declined'`인 것이 하나라도 있으면 True. 참석자가 없으면 False. 같은 캘린더 id가 아닌 이메일의 `declined`는 무시(단 `self` 키가 있으면 포함). `self` 키가 없고 `email` 키도 없는 참석자는 `KeyError`, 조건에 맞는데 `responseStatus` 키가 없으면 `KeyError` | 코드 확인 + 원본 테스트 열람 |
| R-10 | `_iterate_events` | 1) `event_list`가 비어 있으면 stderr가 아닌 `printer.msg('\nNo Events Found...\n', 'yellow')`를 내고 0 반환(필터 이전 검사). 2) 목록 순서대로 이벤트마다: `options['ignore_started']`가 참이고 `event['s'] < self.now`이면 건너뜀(strict 미만; 오늘 시작한 종일 이벤트는 `s`가 현지 자정이라 "시작됨"). `options['ignore_declined']`가 참이고 `_DeclinedEvent`면 건너뜀. 3) 통과하면 `selected += 1`; 날짜 머리글 `day_format`(`year_date`가 참이면 `'\n%Y-%m-%d'`, 아니면 `'\n%a %b %d'`)으로 `s`를 포맷해 `year_date`이거나 이전 이벤트와 날짜 문자열이 다르면 `prefix`로 `_PrintEvent(event, prefix)`에 넘기고 아니면 `prefix=None`. 4) `work`가 주어졌으면 `_PrintEvent` **뒤에** `work(event)`. 5) `selected`를 반환. 모두 필터로 걸러져도 "No Events Found" 메시지는 나오지 않고 0을 반환한다. `ignore_started`·`ignore_declined` 키가 `options`에 없으면 `KeyError` | 코드 확인 |
| R-11 | `_display_queried_events(start, end, search, year_date)` | `events = _search_for_events(start, end, search)` 후: `options.get('tsv')`가 참이면 `_tsv(start, events)`를 반환, 아니면 `options.get('json')`이 참이면 `_json`, 아니면 `_iterate_events(start, events, year_date=year_date)`. 즉 **tsv가 json보다 우선**한다. `_tsv`·`_json`은 `_iterate_events`와 **별도로** 같은 `ignore_started`·`ignore_declined` 필터를 같은 순서·조건으로 복제하고(`gcal.py:740-743`, `760-763`) "No Events Found" 메시지를 내지 않는다(내용은 행 9). 이 분기는 `agenda`와 `search`만 탄다. `updates`·`conflicts`는 `--tsv`/`--json`을 받아도 **무시하고** 항상 텍스트 경로를 쓴다(R-14, R-15) | 코드 확인 |
| R-12 | `AgendaQuery(start, end)` | `start`가 거짓이면 `self.now`를 현지 자정으로(`replace(hour=0,minute=0,second=0,microsecond=0)`). `end`가 거짓이면 `start + timedelta(days=5)`(`agenda_length`, 클래스 상수 5, `start`가 인자였어도 그 기준). `_display_queried_events(start, end)`(검색어 없음, `year_date=False`)의 반환을 그대로 돌려준다. `start`를 주고 `end`를 주지 않으면 `start`로부터 5일, `end`만 주고 `start`를 주지 않는 CLI 입력은 불가능(위치 인자라 `start`가 먼저) | 코드 확인 |
| R-13 | `TextQuery(search_text, start, end)` | `search_text`가 거짓(빈 문자열·`None`)이면 `GcalcliError('Search text is required.')`(cli가 stderr에 출력하고 종료 코드 1). 아니면 `_display_queried_events(start, end, search_text, True)`(`year_date=True`). **`start`·`end`를 채우지 않는다**: 생략하면 `timeMin`·`timeMax` 없이 캘린더 전체 기간을 조회한다. 검색어는 `q`로 서버에 보내며 gcalcli가 로컬에서 다시 거르지 않는다. 대소문자 무시는 서버 동작이다(argparse description이 "case insensitive search"라 하나 코드 근거 없음: U-02). cli는 `parsed_args.text[0]`을 넘긴다 | 코드 확인 / 서버 동작 미확인 |
| R-14 | `UpdatesQuery(last_updated_datetime, start, end)` | `start` 없으면 `self.now`의 현지 자정. `end` 없으면 `(start + relativedelta(months=+1)).replace(day=1)`: **`start`의 시·분·초를 유지한 채 다음 달 1일**(예: `start`가 15일 14:30이면 `end`는 다음 달 1일 14:30; `start`가 기본 자정이면 다음 달 1일 자정). `event_list = _search_for_events(start, end, None)` 후 `utils.get_time_from_str(e['updated']) >= last_updated_datetime`인 이벤트만 남긴다(`updated` 문자열을 다시 파싱; 키가 없으면 `KeyError`; 서버가 주는 UTC `Z` 문자열이 tz-aware로 파싱된다는 전제: 추론). 그다음 stdout에 `print('Updates since:', last_updated_datetime, 'events starting', start, 'until', end)`(공백 구분, datetime의 `str` 형식)를 **`_iterate_events` 호출 직전에** 출력한다(필터 후 비어 있어도 출력). 마지막으로 `_iterate_events(start, event_list, year_date=False)`의 반환. 변경분 기준이 **일정의 시작 시각이 `[start, end)`에 드는 이벤트 중** `updated`가 최근인 것이다. 삭제된 일정은 R-03의 취소 건너뛰기와 `showDeleted` 미설정 때문에 나타나지 않는다(추론: API 기본값). `--tsv`/`--json`은 무시 | 코드 확인 / 추론(API 기본값) |
| R-15 | `ConflictsQuery(search_text, start, end)` + `ShowConflicts` | `start` 없으면 현지 자정, `end` 없으면 `start + timedelta(days=30)`(`conflicts_lookahead_days`). `search_text`는 `None`이어도 허용(빈 문자열이면 `q` 생략). `_search_for_events(start, end, search_text)` → `ShowConflicts(lambda e: self._PrintEvent(e, '\t !!! Conflict: '))` → `_iterate_events(start, event_list, year_date=False, work=show_conflicts.show_conflicts)`. `show_conflicts(latest)`(정렬된 순서로만 호출됨): `start = latest['s']`; `active_events` 중 `event['e'] > start`인 각각에 `show(event)`; 그다음 `active_events`를 `e > start`인 것만 남기도록 다시 만들고 `latest`를 뒤에 추가. 따라서 (a) 겹침 판정은 **`이전.e > 이후.s` strict**라 끝과 시작이 맞닿으면(`e == s`) 충돌이 아니다, (b) 충돌 줄로 출력되는 것은 **먼저 시작한 이벤트**이고, 나중 이벤트는 `_iterate_events`가 그 직전에 평소처럼 출력한다(출력 순서: 나중 이벤트, 이어서 겹친 앞선 이벤트마다 `\t !!! Conflict: ` 접두), (c) 쌍(앞, 뒤)이 겹치면 `뒤`가 처리되는 시점에 `앞`이 한 번 출력된다(`앞`이 `active`에 남아 있는 한 겹치는 뒤 이벤트마다 반복 출력), (d) `--nostarted`/`--nodeclined`로 건너뛴 이벤트는 `work`를 거치지 않으므로 충돌 비교에서도 빠진다, (e) 종일 이벤트도 일반 이벤트처럼 `[s,e)` 구간으로 비교되어 그날의 모든 일정과 겹친다, (f) 서로 다른 캘린더 간 충돌도 잡는다. `ShowConflicts.active_events`는 클래스 속성 `[]`이지만 첫 호출에서 인스턴스 속성으로 대체되어 클래스 쪽 리스트는 변하지 않는다. 반환값은 `_iterate_events`의 통과 수(충돌 수가 아님). `--tsv`/`--json` 무시 | 코드 확인 + 원본 테스트 열람 |
| R-16 | CLI 배선 | `cli.py:251-267, 309-312`: `agenda` → `AgendaQuery(start=args.start, end=args.end)`, `updates` → `UpdatesQuery(last_updated_datetime=args.since, start, end)`, `conflicts` → `ConflictsQuery(search_text=args.text, start, end)`, `search` → `TextQuery(args.text[0], start, end)`. 반환값은 버려진다. `GcalcliError`는 `printer.err_msg`로 stderr 출력 후 종료 코드 1, 그 밖의 예외(`HttpError`, `KeyError`, `AttributeError`)는 처리되지 않고 traceback. `search`의 `text`가 없으면 argparse가 종료 코드 2의 usage 오류(원본 테스트: `SystemExit`). `updates`의 `since`가 없어도 같음. `since`·`start`·`end` 파싱 실패는 `ValueError` → argparse의 `invalid ... value` 오류(argparse 동작: 추론) | 코드 확인 / 추론(argparse 오류 문구) |
| R-17 | 시계 `self.now` | `GoogleCalendarInterface.now = datetime.now(tzlocal())`는 **클래스 속성**으로 모듈 import 시 한 번 정해진다(`gcal.py:53`). 인스턴스·메서드 어디서도 재대입하지 않는다(`grep -n "\.now *=" gcalcli/*.py tests/*.py` → 없음, 범위 `gcalcli/`·`tests/`). 모든 기본 `start`와 `--nostarted`(`s < now`)가 이 값을 쓴다. 프로세스 한 번에 한 서브커맨드만 실행하므로 보통 실행 시작 시각이지만, 장시간 실행·import 후 대기에서는 오래된 값이다 | 코드 확인 |
| R-18 | `_search_for_events`를 쓰는 다른 호출처 | `CalQuery`(calw·calm: 주/월 경계로 `start`·`end` 계산, `search_text=None`), `ModifyEvents`(edit·delete: **빈 검색어는 `GcalcliError('The empty string would get *ALL* events')`**, `start`/`end`는 그대로 `None` 가능), `Remind`(`start=self.now`, `end=now+분+5분`, 텍스트 없음). 이들은 이 스펙의 정렬·필터를 그대로 상속하고, 각자 후처리(출력·수정·`event['s'] < self.now` 재검사)는 해당 스펙에 있다. `grep -n "_search_for_events(" gcalcli/*.py` → `gcal.py` 정의 1, 호출 6(`1288,1311,1330,1404,1510,1526`) | 코드 확인 |

- 불변식: R-03~R-06 필터를 통과한 이벤트만 목록에 들어간다. 목록은 `s` 오름차순이고 모든 `s`·`e`가 tz-aware `tzlocal()`이다(`_search_for_events` 반환 시점). `gcalcli_cal`은 `self.cals` 항목의 별칭이다.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-01, R-05 | Calendar API가 `timeMin`/`timeMax`(RFC 3339 오프셋 포함)를 종일 이벤트에 어떻게 적용하는가(종일 이벤트를 UTC 날짜 기준 구간으로 보는가), `timeMax`가 시작 시각 기준 배타적인가, `timeMin`이 종료 시각 기준인가? | 재구현이 서버 없이 필터를 흉내 낼 때 `start` 쪽 종일 이벤트 포함 여부와 `end` 필터의 필요성 | Calendar API v3 `events.list` 문서 확인 또는 UTC와 다른 시간대 계정으로 종일 이벤트 조회 실행 |
| U-02 | R-13 | `q`가 어떤 필드(요약·설명·장소·참석자 등)를 대소문자 무시로 부분 일치시키는가? | `search`의 일치 범위, 재구현에서 서버 없이 검색할 때의 규칙 | Calendar API `events.list`의 `q` 문서 확인(이 스펙에서는 가져오지 않았음) 또는 실행 |
| U-03 | R-02, R-14 | `events.list`의 기본 `maxResults`(페이지 크기)와 `showDeleted` 기본값, `updated`의 실제 형식 | 페이지 수, 삭제 일정 비노출 근거, `updated` 파싱 | 같은 문서 확인 |

- 확인 한계: Google API 호출이 필요한 부분(요청 파라미터의 서버 쪽 해석, 페이지 크기, `q` 일치 범위, 취소 이벤트가 실제로 오는 조건, `updated` 형식)은 실행하지 못했다. `dateutil`·`googleapiclient`는 이 환경에 설치돼 있지 않아 `parse`·`localize_datetime` 결과는 코드 경로와 input-parsing 스펙으로 판단했다. 원본 테스트는 `tests/test_conflicts.py`(3개), `tests/test_gcalcli.py`의 `test_agenda`·`test_updates`·`test_conflicts`·`_DeclinedEvent` 5개, `tests/conftest.py`를 열람했고 실행하지 않았다. `test_agenda` 등은 API를 스텁으로 대체해 빈 결과(반환 0)만 확인하므로 R-03~R-07의 필터·정렬은 원본 테스트로 검증되지 않는다(`mock_event`는 `_search_for_events` 전체를 대체).

### 1.5 필수 코드 참조 [필수]
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/gcal.py:1194-1248` `_GetAllEvents` | 요청 인자, 페이지 루프, 이벤트별 처리 순서, 필터 조건 | R-01~R-06 |
| C-02 | `gcalcli/gcal.py:1250-1261` `_search_for_events`, `_DeclinedEvent` | 캘린더 순회·정렬, declined 판정식 | R-07, R-09 |
| C-03 | `gcalcli/gcal.py:1162-1192` `_iterate_events` | 필터 순서, 머리글 포맷, `work` 훅 시점 | R-10 |
| C-04 | `gcalcli/gcal.py:1286-1346` `_display_queried_events`, `TextQuery`, `UpdatesQuery`, `ConflictsQuery`, `AgendaQuery` | 기본 범위 계산, 분기 우선순위 | R-11~R-15 |
| C-05 | `gcalcli/conflicts.py:1-24` `ShowConflicts` | 겹침 판정·활성 목록 갱신 | R-15 |
| C-06 | `gcalcli/_types.py:1-29` `Event` | 이벤트 확장 키 선언 | 1.3 |
| C-07 | `gcalcli/cli.py:251-267`, `309-312` | 서브커맨드 배선 | R-16 |
| C-08 | `gcalcli/argparsers.py:318-353`, `202-215`, `473-560` | `updates`·`conflicts`·`start_end`·`search` 위치 인자, `--nostarted`·`--nodeclined`, 서브커맨드 등록 | 1.3, R-16 |
| C-09 | `gcalcli/utils.py:201-207` `localize_datetime` | tz 없음/있음 분기 | R-04 (정의 소유는 input-parsing R-22) |

`self.now`·`agenda_length`·`conflicts_lookahead_days`는 `gcalcli/gcal.py:50-55`(C-04의 상수 근거). `get_time_from_str`·`localize_datetime`·`is_all_day`는 [input-parsing](input-parsing.md)을 쓴다.

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(R-09·R-15의 일부는 원본 테스트 열람, 표시). 대체: Google API 없음 → `events().list(...).execute()` 응답을 가정한 dict로 대체하며 서버의 `timeMin`/`timeMax`/`q` 필터링과 실제 페이지 크기는 검증하지 않는다. 지역 시간대는 `tzlocal()`이 가리키는 값으로 가정한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | 캘린더 하나, API가 2페이지(`nextPageToken='p2'` → 없음) 반환, 각 페이지 이벤트 1개 | `list` 호출 두 번(두 번째는 `pageToken='p2'`), 이벤트 2개를 페이지 순서로 내보냄 |
| T-02 | R-03 | 이벤트 A `status='cancelled'`(`start` 키 없음), 이벤트 B 정상 | A는 제외, 오류 없음. B만 `s`·`e`·`gcalcli_cal` 가짐 |
| T-03 | R-04 | 종일 이벤트 `start.date='2024-03-05'`, `end.date='2024-03-06'`, 현지 UTC+9 | `s`=2024-03-05 00:00+09:00, `e`=2024-03-06 00:00+09:00(UTC 자정 변환 없음). 모두 tzinfo가 `tzlocal()` |
| T-04 | R-04 | `start.dateTime='2024-03-05T00:00:00Z'`, 현지 UTC+9 | `s`=2024-03-05 09:00+09:00 |
| T-05 | R-05 | `end`=2024-03-06 00:00+09:00, API가 종일 이벤트(`start.date='2024-03-06'`)도 돌려줌 | `s`=2024-03-06 00:00+09:00 `>= end`라 제외 |
| T-06 | R-05 | `start`=2024-03-06 00:00+09:00, API가 `start.date='2024-03-04'`, `end.date='2024-03-05'` 종일 이벤트를 돌려줌 | 제외되지 않고 목록에 포함(`start` 쪽 필터 없음) |
| T-07 | R-06 | `end.dateTime`이 `2038-01-01T00:00:00Z`인 이벤트 | 제외(현지 `e.year >= 2038`일 때). UTC-5 현지면 `e`=2037-12-31 19:00이라 **포함** |
| T-08 | R-07 | `cals=[X, Y]`, X에 `s`=10:00·09:00, Y에 `s`=09:00·08:00 | 결과 `s` 순: 08:00(Y), 09:00(X), 09:00(Y), 10:00(X). 같은 09:00은 X 먼저(안정 정렬). 각 항목 `gcalcli_cal`은 소속 캘린더 |
| T-09 | R-09 | `gcalcli_cal.id='u@x.com'`, 참석자 `[{'email':'o@y.com','self':True,'responseStatus':'declined'}]` | True. 원본 테스트 열람(`test_declined_event_aliased_attendee`). 같은 참석자가 `declined`이고 `email='u@x.com'`이면 `self` 없이도 True, 다른 이메일 + `self` 없음이면 False |
| T-10 | R-10 | `ignore_started=True`, `now`=10:00, 이벤트 `s`=09:00·10:00·11:00 | 10:00과 11:00만 통과(strict `<`), 반환 2. 목록이 빈 경우는 반환 0과 "No Events Found" |
| T-11 | R-10 | `ignore_started=True`이고 모든 이벤트가 이미 시작됨 | 반환 0, "No Events Found" 메시지 없음 |
| T-12 | R-11 | `agenda --tsv --json` | `_tsv`만 호출됨(json 무시) |
| T-13 | R-12 | 인자 없이 `agenda`, `now`=2024-03-05 14:00 | `start`=2024-03-05 00:00(현지), `end`=2024-03-10 00:00 |
| T-14 | R-13 | `search ""` 또는 `TextQuery('')` | `GcalcliError('Search text is required.')`, stderr 메시지, 종료 코드 1. `search`를 인자 없이 호출하면 argparse 오류(종료 코드 2). 빈 검색어 거부는 원본 테스트 열람(`test_search_parser`는 `SystemExit`만 확인) |
| T-15 | R-14 | `updates 2024-03-01`, `now`=2024-03-15 14:30, 시작 인자 없음 | `start`=2024-03-15 00:00, `end`=2024-04-01 00:00. `start`를 `2024-03-15 14:30`으로 주면 `end`=2024-04-01 14:30 |
| T-16 | R-14 | `since`=2024-03-01 00:00+09:00, 이벤트 `updated='2024-02-28T10:00:00.000Z'`와 `'2024-03-02T10:00:00.000Z'` | 뒤의 것만 남는다. 비어 있어도 `Updates since: 2024-03-01 00:00:00+09:00 events starting ... until ...` 줄은 출력 |
| T-17 | R-15 | A 14:15–15:15, B 14:30–16:15, C 15:30–16:15 (정렬됨) | A 출력; B 출력 후 A가 `\t !!! Conflict: `로 출력; C 출력 후 B만 충돌로 출력(A는 `e`=15:15 ≤ 15:30이라 제외). 원본 테스트 열람(`test_conflicts.py`는 A·B 겹침, A·C 비겹침을 각각 확인) |
| T-18 | R-15 | D 15:15–16:00이 A(14:15–15:15) 직후 | 충돌 아님(`A.e > D.s`가 거짓) |
| T-19 | R-15 | 두 번째 이벤트가 `--nodeclined`로 건너뛰어짐 | 그 이벤트는 `show_conflicts`에 전달되지 않아 다른 이벤트와의 충돌로도 나타나지 않음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@405639c `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | C-01(`gcal.py:1194-1207`, `1246-1248`), `gcal.py:135-149` | 줄 추적. `None` 인자 생략은 googleapiclient 동작이라 추론(이 환경에 미설치). 부재 주장(`orderBy`·`maxResults`·`showDeleted` 미사용): `grep -n "orderBy\|maxResults\|showDeleted" gcalcli/*.py` → 이 호출에 없음(범위 `gcalcli/*.py`) |
| R-03 | C-01(`gcal.py:1209-1244`) | 줄 추적 |
| R-04 | C-01(`gcal.py:1213-1228`), C-09(`utils.py:201-207`) | 줄 추적. `parse('2024-03-05')`가 naive 자정을 주고 `parse('...Z')`가 tz-aware를 준다는 것은 dateutil 동작(추론, 미설치로 실행 안 함). 종일 이벤트가 "UTC로 가정된다"는 주석은 코드가 아니라 작성자 주장 |
| R-05 | C-01(`gcal.py:1230-1233` 주석 포함) | 줄 추적. `start` 쪽 필터 부재: `grep -n "s'\] *<\|'e'\] *<=" gcalcli/gcal.py`에서 `_GetAllEvents` 안에 없음(범위 `_GetAllEvents` 본문). 서버 해석은 미확인(U-01) |
| R-06 | C-01(`gcal.py:1236-1242` 주석 포함) | 줄 추적 |
| R-07 | C-02(`gcal.py:1250-1256`) | 줄 추적. 안정 정렬은 Python `list.sort` 보장(표준) |
| R-08 | `gcal.py:583`, `gcal.py:1024-1026`, `gcal.py:1209-1228` | 부재 주장 검색 `grep -n "\['s'\] *=\|\['e'\] *=\|\['gcalcli_cal'\] *=" gcalcli/*.py`. 놓칠 가능성: 동적 키 접근, `details.py`가 이벤트에 쓰는 경로(행 9)는 별도 확인하지 않음 |
| R-09 | C-02(`gcal.py:1258-1261`), `tests/test_gcalcli.py:196-279` | 줄 추적 + 테스트 5개 열람(실행 안 함) |
| R-10 | C-03(`gcal.py:1162-1192`) | 줄 추적 |
| R-11 | C-04(`gcal.py:1286-1295`), `gcal.py:727-777` | 줄 추적. `updates`·`conflicts`가 `_display_queried_events`를 거치지 않음은 C-04 본문으로 확인 |
| R-12 | C-04(`gcal.py:1339-1346`), `gcal.py:53-55` | 줄 추적 |
| R-13 | C-04(`gcal.py:1297-1302`), `argparsers.py:473-482` | 줄 추적. 대소문자 무시 설명은 argparse description 문구 |
| R-14 | C-04(`gcal.py:1304-1321`) | 줄 추적. `relativedelta(months=+1)`와 `replace(day=1)` 결과는 코드 읽기로 계산(실행 안 함). `updated` tz-aware 가정은 추론 |
| R-15 | C-04(`gcal.py:1323-1337`), C-05, `tests/test_conflicts.py:24-45` | 줄 추적 + 테스트 열람. 클래스 속성 리스트가 변하지 않는다는 주장은 `ShowConflicts.show_conflicts`에서 리스트에 `append`가 인스턴스 속성 재대입 뒤에만 일어난다는 코드 사실(첫 `for`는 읽기 전용) |
| R-16 | C-07, C-08, `cli.py:393-395`(`GcalcliError` 처리), `tests/test_argparsers.py:54-80` | 줄 추적. argparse 오류 종료 코드 2는 표준 동작(추론) |
| R-17 | `gcal.py:53`; `grep -n "\.now *=" gcalcli/*.py tests/*.py` | 부재 주장: 위 검색, 범위 `gcalcli/`·`tests/`. 놓칠 가능성: `setattr`·monkeypatch(테스트가 `datetime`을 패치하는지는 열지 않음) |
| R-18 | `gcal.py:1288,1311,1330,1404,1510,1526`, `grep -n "_search_for_events(" gcalcli/*.py` | 검색 결과 대조 |
| T-01~T-19 | 위 R-ID 근거 | T-09·T-14의 일부·T-17의 일부만 원본 테스트 열람. 나머지는 구현에서 도출, 실행 안 함 |

### 2.2 코드 읽는 순서 [선택]
`cli.py:251-267` → `gcal.py:1339-1346`(`AgendaQuery`) → `1286-1295` → `1250-1256` → `1194-1248`(핵심) → `1162-1192` → `conflicts.py`. 이 전략은 이벤트를 전부 메모리에 모은 뒤 정렬하고 필터를 렌더링 단계(`_iterate_events`/`_tsv`/`_json`)에서 적용하는 구조다(필터가 서버 쪽이 아니라 클라이언트 쪽: 코드 확인).

### 2.4 검토 기록 [필수, ready 스펙]
- **작성자 자체 점검**: R-03~R-06, R-10, R-14, R-15의 인용 줄을 다시 열어 맞춰 봤다.
- **메인 세션 점검(2026-11-18)**: `_SetEventStartEnd`의 `event['e'] - parse(end)`가 대입이 아닌 뺄셈임, `now`가 클래스 속성(`gcal.py:53`)임, `_event_time_in_range`·`_event_spans_time`이 달력 렌더러에서만 쓰임을 원본 줄로 확인.
- **독립 검토(읽기 전용 서브에이전트, 2026-11-18)**: R-01~R-18 전부와 1.3 불변식을 대조했다. 실질 반례 없음. 인용 줄 15개 표본 중 범위가 넓었던 3곳(`argparsers.py` 473-558, `cli.py` 393-395, `tests/test_gcalcli.py` 196-279)은 고쳤다. 부정확했던 R-08의 "pop" 표현도 고쳤다. `s`·`e`·`gcalcli_cal`을 쓰는 곳 전수(`gcal.py` 1025, 1209·1215·1218·1220·1223·1226·1228)와 `.now =` 재대입 없음을 grep으로 재확인했다. 보강 사항(본문에 아래 R-ID 칸에서 보충): R-09 `_DeclinedEvent`는 `self` 없이 `email`만 있고 `gcalcli_cal`에 `id`가 없는 경로에서도 `KeyError`가 난다. R-14는 필터 후 목록이 비어도 `Updates since:` 줄이 출력되고, 이어서 `_iterate_events`가 `No Events Found`도 출력한다. R-18의 호출자 `ModifyEvents`도 `_iterate_events(self.now, ..., year_date=True, work=work)`를 쓰므로 edit·delete도 `--nostarted`·`--nodeclined` 필터와 `No Events Found` 경로를 탄다. 구현자가 비어 있다고 느낄 수 있는 점: `now` 고정 방법(클래스 속성이라 인스턴스 주입 가능)과 `updated`를 `get_time_from_str`(기본값 오늘 자정)로 파싱한다는 점(영향 작음).
- **대조하지 않은 것**: T-01~T-16·T-19의 가정 응답 시나리오 실행, Google API 해석(U-01~U-03), dateutil 결과(미설치).
- **status를 `draft`로 유지하는 이유**: U-01~U-03이 열려 있고 선행 스펙 calendar-selection·input-parsing도 `draft`다.

## 적용 메모 [선택]
없음(분석 목적 미정).
