---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/gcal.py
  - gcalcli/printer.py
  - gcalcli/argparsers.py
  - gcalcli/cli.py
  - gcalcli/utils.py
  - gcalcli/deprecations.py
  - gcalcli/details.py
  - tests/test_gcalcli.py
  - tests/test_printer.py
depends:
  - event-query.md
  - calendar-selection.md
  - input-parsing.md
status: draft
---

# 출력 렌더링 (텍스트 아젠다 + ASCII 달력)

> 내부 이벤트 목록(`s`·`e`·`gcalcli_cal`, [event-query](event-query.md) 1.3)을 `--width`·`--military`·`--details`·색 옵션·`--lineart`·`--nocolor`에 맞춰 (a) `agenda`·`search`·`updates`·`conflicts`의 날짜별 텍스트 아젠다(`_PrintEvent`)로, (b) `calw`·`calm`의 요일 열 격자 달력(`CalQuery`→`_GraphEvents`, 단어 줄바꿈·유니코드 폭·오늘 강조 포함)으로 터미널에 쓰는 `Printer` 기반 렌더러.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `cli.main`이 `--conky`·`--nocolor`·`--lineart`로 `Printer`를 만들고 `GoogleCalendarInterface(printer=…, **vars(parsed_args))`에 넘긴다. 생성자가 달력 폭 `width['cal']`·열 폭 `width['day']`·열 수 `days`를 정한다(R-01, R-08).
2. 텍스트 경로: [event-query](event-query.md) R-10의 `_iterate_events`가 필터를 통과한 이벤트마다 `_PrintEvent(event, prefix)`를 부른다. `_PrintEvent`는 prefix → 색 결정 → 시간·제목 한 줄 → `--details`가 켠 부가 줄 순으로 쓴다(R-10~R-15).
3. 달력 경로: `CalQuery(cmd, start_text, count)`가 시작 날짜를 자정으로 맞추고 주(`calw`) 또는 월(`calm`) 경계로 `start`·`end`·주 수를 정한 뒤 `_search_for_events`로 목록을 받아 `_GraphEvents`에 넘긴다(R-16, R-17).
4. `_GraphEvents`는 앞쪽의 `s < start` 이벤트를 버리고, 테두리·(월 제목)·요일 머리글을 쓴 뒤, 주마다 날짜 줄 → `_get_week_events`가 만든 요일별 `EventTitle` 목록 → 줄 단위 출력(셀 한 줄씩, 폭 초과분은 `_get_cut_index`로 잘라 다음 줄) → 구분선/바닥선을 쓴다(R-18~R-22).
5. 모든 출력은 `Printer.msg`/`art_msg`를 거친다. 색이 켜져 있으면 `색코드 + 문자열 + default 코드`로 감싸고, 꺼져 있으면 문자열만 쓴다(R-02~R-04).

### 1.2 범위·통합 지점 [필수]
- 제공: `Printer`(색 표·conky·선 그리기 문자), `valid_color_name`, 텍스트 아젠다 한 이벤트의 출력(`_PrintEvent`, `--details` 줄), 달력 출력(`CalQuery`·`_GraphEvents`·`_get_week_events`·`_format_title`·`_cal_weekday_num`·`_event_time_in_range`·`_event_spans_time`·`_printed_len`·`_word_cut`·`_next_cut`·`_get_cut_index`), 출력 옵션(`--width`·`--military`·`--override-color`·`--color-*`·`--nocolor`·`--lineart`·`--conky`·`--details`·`--monday`·`--noweekend`)의 의미.
- 제외: `--tsv`·`--json` 직렬화 `_tsv`·`_json`과 `details.py`의 `Handler.get/data`(행 9. 이 스펙은 텍스트 경로가 읽는 키만), 일정 조회·정렬·`--nostarted`/`--nodeclined` 필터·"No Events Found"·`ShowConflicts`([event-query](event-query.md)), 수정·삭제 대화형 흐름(행 8. `_iterate_events(…, year_date=True, work=…)`와 `_PrintEvent(event, '\n%Y-%m-%d')`를 호출하는 경계만 정의: 호출자가 `prefix` 문자열을 정하고 `_PrintEvent`는 그대로 쓴다), `ListAllCalendars`·`--calendar #색` 해석·`_calendar_color`([calendar-selection](calendar-selection.md) R-10), `is_all_day`·`days_since_epoch`·`get_time_from_str`·`validwidth`·`get_auto_width`·`locale_has_24_hours`·`set_locale`([input-parsing](input-parsing.md)).
- 외부 의존·선행 계약: 이벤트 표현은 event-query 1.3(특히 종일 이벤트의 `e`는 배타적 끝날짜 자정). 시계 `self.now`는 event-query R-17(클래스 속성, import 시 1회). 터미널 폭은 argparse 기본값 `get_terminal_size().columns`. 로케일은 프로세스 시작 시 `utils.py:21`의 `locale.setlocale(LC_ALL, '')`(환경 로케일)와 `--locale`(파싱 후 `set_locale`)가 정하고, 이 스펙은 `strftime` 결과(`%a %b %A %B %p`)를 그대로 쓴다.
- 소유 상태·부작용: 표준 출력(`Printer.msg`의 `file`)과 표준 오류(`err_msg`·`debug_msg`)에 쓰는 것이 전부다. 이벤트·옵션·캐시는 바꾸지 않는다. 인스턴스 상태는 `width`, `days`, `printer`, `details`뿐이고 생성자에서 한 번 정해진다.

### 1.3 인터페이스와 데이터 의미 [필수]
입력 이벤트는 event-query 1.3의 내부 이벤트 표현이다. 이 스펙이 읽는 키: `s`, `e`, `summary`, `gcalcli_cal`(`summary`·`id`·`accessRole`·`colorSpec`), `colorId`, `htmlLink`, `hangoutLink`, `conferenceData.entryPoints[]`, `location`, `organizer`, `attendees[]`, `attachments[]`, `reminders`, `creator.email`, `description`.

| 연산·데이터 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `Printer(conky=False, use_color=True, art_style='ascii')` | → printer | R-01~R-05. `art_style`은 `fancy`·`unicode`·`ascii`. 모르는 값은 `KeyError` |
| `Printer.msg(msg, colorname='default', file=sys.stdout)` | 문자열을 `file`에 씀(개행·flush 없음) | R-02. `file` 기본값은 **함수 정의 시점의** `sys.stdout` |
| `Printer.art_msg(arttag, colorname, file)` | `art[arttag]`를 `msg`로 씀 | R-04. 태그: `hrz vrt lrc urc ulc llc crs lte rte bte ute` |
| `valid_color_name(value)` | → value 또는 `argparse.ArgumentTypeError` | R-05 |
| `_PrintEvent(event, prefix)` | → None | R-10~R-15. `prefix`가 거짓(None·빈 문자열)이면 공백 10칸 |
| `CalQuery(cmd, start_text='', count=1)` | → None | R-16, R-17. `cmd`는 `'calw'`·`'calm'` |
| `_GraphEvents(cmd, start_datetime, count, event_list)` | → None | R-18~R-22. `event_list`는 `s` 오름차순이어야 한다(R-18) |
| `_get_week_events(start_dt, end_dt, event_list)` | → 길이 7인 `list[list[EventTitle]]` | R-20. `EventTitle(title, color)`; 제목이 `'\n'`으로 시작 |
| `_get_cut_index(event_string)` | → `(출력 폭, 잘라 낼 문자 수)` | R-21 |

**CLI (외부 계약)**

| 옵션 | 위치 | 기본값·의미 |
|---|---|---|
| `--conky` / `--nocolor`(dest `color`, store_false) / `--lineart {fancy,unicode,ascii}` | 프로그램 수준(`argparsers.py:77-93`) | `False` / `True` / **`fancy`**. `Printer`의 클래스 기본 `ascii`와 CLI 기본 `fancy`가 다르다 |
| `--color-owner`(`cyan`) `--color-writer`(`cyan`) `--color-reader`(`magenta`) `--color-freebusy`(`default`) `--color-date`(`yellow`) `--color-now-marker`(`brightred`) `--color-border`(`white`) `--color-title`(`brightyellow`) | `color_parser`를 부모로 둔 `list`와 출력 파서를 쓰는 `agenda`·`search`·`updates`·`conflicts`·`calw`·`calm` | `valid_color_name` 검증, dest는 `color_<이름>`(`-`→`_`). 옛 철자 `--color_owner` 등은 숨김 deprecated 별칭(`deprecations.py:79-90`, 경고 동작은 확인하지 않음) |
| `--width/-w N` | 출력 파서 | 기본 `get_terminal_size().columns`(파서 **구성 시점**). 문자열로 준 값만 `validwidth`(30 미만 오류). 기본값은 검증되지 않아 터미널이 30칸 미만이면 그대로 쓰인다 |
| `--military` / `--no-military` | 출력 파서 | 기본 `locale_has_24_hours()`(파서 구성 시점 — `--locale`보다 먼저). 마지막 옵션 승리 |
| `--override-color` | 출력 파서 | `False`. 이벤트 `colorId`가 있을 때 이벤트 색을 쓴다(R-09) |
| `--tsv`·`--json`·`--nostarted`·`--nodeclined` | 출력 파서 | event-query R-10·R-11. `calw`·`calm`은 파서에 있어도 **읽지 않는다**(R-22) |
| `--details {id,time,length,url,conference,title,location,description,calendar,email,attendees,action,reminders,attachments,end,all}` | `details_parser`(`argparsers.py:99-138`) | 반복 가능, `all`은 `DETAILS` 전체. 텍스트 경로가 쓰는 키는 R-12~R-13 |
| `--monday`(dest `week_start`, 값 `WeekStart.MONDAY`) / `--noweekend`(dest `cal_weekend`, store_false) | `calw`·`calm`의 `cal_query_parser`(`argparsers.py:296-315`) | 주 시작 기본은 config `output.week-start`(기본 sunday, [config-resolution](config-resolution.md)) / `cal_weekend=True` |
| `calw [start] [weeks]` / `calm [start]` | `argparsers.py:560-585` | `start`는 문자열 그대로 `CalQuery`로, `weeks`는 `int` 기본 1 |

### 1.4 행동 규칙과 남은 질문 [필수]

**A. Printer·색·선 그리기**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Printer(conky, use_color, art_style)` 생성 | `use_color`·`conky` 저장, `art = ART_CHARS[art_style]`. CLI는 `Printer(conky=--conky, use_color=--nocolor의 color, art_style=--lineart)`를 만든다. 모듈 전역 `PRINTER = Printer()`(ascii·색 켬·conky 끔)는 `GoogleCalendarInterface`의 기본 `printer`다. 알 수 없는 `art_style`은 `KeyError` | 코드 확인 |
| R-02 | `msg(msg, colorname, file)` | `use_color`가 참이면 `colors[colorname] + msg + colors['default']`, 거짓이면 `msg`만 `file.write`한다. 개행·flush를 더하지 않는다. `colorname`이 표에 없으면(`use_color` 참일 때만) `KeyError`. `None`은 `'default'`와 같은 코드. `file` 기본값은 정의 시점에 묶인 `sys.stdout` 객체다. `err_msg`는 `brightred`, `debug_msg`는 `yellow`로 stderr에 쓴다 | 코드 확인 + 원본 테스트 열람(`tests/test_printer.py`) |
| R-03 | 색 표 `colors` (C-01) | 17개 이름(`default black red green yellow blue magenta cyan white` + `bright*` 8개) + `None`. 일반 색은 `\033[0;3Xm`, bright는 `\033[3X;1m`, default는 `\033[0m`. `conky=True`면 `${color <name>}`(default는 `${color}`)이고 **bright 색은 일반 색과 같은 문자열**이 된다 | 코드 확인 + 원본 테스트 열람 |
| R-04 | `art_msg(tag, color)`와 선 그리기 문자 | `msg(art[tag], color)`와 같다(색을 입힌다). `fancy`의 문자는 VT100 선 그리기 시퀀스(`\033(0` + 문자 + `\033(B`), `unicode`는 `─│┘┐┌└┼├┤┴┬`, `ascii`는 `-`·`\|`·`+`. 선 문자열은 **색 코드가 아니므로 `--nocolor`로 지워지지 않는다**: `--nocolor --lineart fancy`는 색 없이 이스케이프 시퀀스는 그대로 낸다 | 코드 확인 + 실행 확인(구현 재현 스크립트) |
| R-05 | `valid_color_name(value)` | `COLOR_NAMES`(R-03의 17개 이름 집합)에 없으면 `ArgumentTypeError('<value> is not a valid color. Valid colours are: …')`. 나열 순서는 `set` 순회 순서라 실행마다 다를 수 있다. `--color-*`와 `--calendar 이름#색`([calendar-selection](calendar-selection.md) R-01)이 이 함수를 쓴다 | 코드 확인 + 원본 테스트 열람 |

**B. 폭·옵션 기본값**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | `--width` 기본 | 터미널 열 수(파서 구성 시점). 명시한 값만 30 이상 검증된다. 비 TTY의 `get_terminal_size()` 대체값(보통 80)은 표준 라이브러리 동작이며 확인 한계 | 코드 확인 |
| R-07 | `--military` 기본 | `locale_has_24_hours()` 결과. **`main`이 파서를 만든 뒤 `--locale`을 적용하므로** `--locale`은 기본값에 영향이 없다. `utils.py:21`의 환경 로케일 기준이다 | 코드 확인 |
| R-08 | 생성자 기하 | `days = 7`(`cal_weekend` 참 또는 키 없음) 아니면 `5`. `width['cal'] = int(options.get('width', 80))`. `width['day'] = int((cal - days - 1) / days)`가 9보다 크면 그 값, 아니면 **10**. 따라서 `--width 80`(7열)은 day=10, 격자 총폭은 `7*10+8=78`이며 요청 폭보다 좁거나(열 수로 나눈 내림) 최소폭 때문에 넓을 수 있다. `width['cal']`은 달력 열 폭과 무관하게 `--details description` 상자 폭(R-14)에 쓰인다 | 코드 확인 + 실행 확인 |

**C. 텍스트 아젠다**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-09 | 이벤트 색 결정(`_PrintEvent`) | `happening_now = s <= now <= e`(둘 다 포함), `all_day = is_all_day(event)`([input-parsing](input-parsing.md) R-23). `--override-color`이고 `event.get('colorId')`가 참이면: `happening_now`이고 종일이 아니면 `color_now_marker`, 아니면 `_calendar_color(event, override_color=True)`. 그 외: `happening_now`이고 종일이 아니면 `color_now_marker`, 아니면 `_calendar_color(event)`. 종일 이벤트는 진행 중이어도 강조되지 않는다. `colorId`가 1~11 밖이면 `KeyError`(calendar-selection R-10) | 코드 확인 |
| R-10 | `_PrintEvent` 첫 줄 | `prefix`(거짓이면 `' ' * 10`)를 `color_date`로 쓴 뒤 이벤트 줄을 이벤트 색으로 쓴다. 종일: `'  ' + '%-W' % '' + '  ' + 제목 + '\n'`(W=`military`면 5, 아니면 7). 시간 있음: `'  %-W   %-W  제목\n'`(시작 시각, 빈 끝). `--details end`가 켜져 있으면 가운데 `'   '`가 `' - '`가 되고 끝 시각이 들어간다. 제목은 `_valid_title(event).strip()`: `summary`가 없거나 공백뿐이면 `(No title)`. 제목 속 개행은 이스케이프하지 않는다 | 코드 확인 + 실행 확인 |
| R-11 | 시각 문자열 `agenda_time_fmt(dt, military)` (C-08) | 24시간: `strftime('%H:%M').lstrip('0')`이라 `09:05`→`9:05`, **`00:05`→`:05`**(자정 직후 선행 0을 모두 벗긴다). 12시간: `strftime('%I:%M').lstrip('0') + strftime('%p').lower()`(`12:30pm`, `1:00pm`). `%p`는 로케일 값이라 AM/PM이 빈 로케일이면 접미사가 없다. 달력의 `_format_title`(R-20)은 24시간에서 `lstrip`을 하지 않아 `00:05`로 달라진다 | 코드 확인 + 실행 확인 |
| R-12 | `--details` 부가 줄, 공통 | 이벤트 줄 다음에 **고정 순서**로 `details`(dict)에서 켠 것만, 각 줄은 `' ' * 19 + '  ' + 라벨…\n`(들여쓰기 19칸) 형태이고 색은 `'default'`다. 순서: `calendar`, `url`(`Link:` 다음 `Hangout Link:`), `conference`, `location`, `attendees`, `attachments`, `length`, `reminders`, `email`, `description`. `id`·`time`·`title`·`action`·`end`가 켜져 있어도 부가 줄은 없다(`end`는 R-10의 시간 칸). `time`·`title`은 켜지 않아도 항상 출력된다. 줄 형식 전부는 C-06 | 코드 확인 |
| R-13 | 부가 줄별 조건 | `calendar`: `gcalcli_cal.summary`. `url`: 키가 있을 때만. `conference`: `conferenceData` 있으면 `entryPoints` 항목마다 `<entryPointType>: <uri>`. `location`: strip 후 비어 있지 않을 때. `attendees`: `attendees` 키가 있을 때 `Attendees:` 다음, `organizer`에 `self`가 없으면 organizer 한 줄, 이어 `self`가 없는 참석자마다 `<displayName 또는 'Not Provided'>: <<email 또는 'Not Provided'>>`. `attachments`: `title`·`fileUrl`. `length`: `str(e - s)`(예 `1:30:00`, `1 day, 0:00:00`). `reminders`: `useDefault`가 `True`면 `Reminder: (default)`, 아니면 `overrides` 항목마다 `Reminder: <method> <분> minutes`. `email`: `creator.email`이 비어 있지 않을 때 | 코드 확인 |
| R-14 | `--details description` | `description.strip()`이 비어 있지 않을 때 `Description:` 라벨, 위 테두리, 줄 감싸기 상자, 아래 테두리. 상자 폭은 `width['cal']`(달력 열 폭이 아니다), 들여쓰기 `19+2`칸, `textwrap.TextWrapper(width=cal-2)`로 줄 단위(`\n` 분할)로 감싸고 `ljust` 후 양쪽에 `art['vrt']`를 넣는다. 테두리는 `art['ulc' 'hrz' 'urc']`/`['llc' 'hrz' 'lrc']`. `box=True`가 하드코딩이라 박스 없는 분기는 도달하지 않는다. 상세는 C-06 | 코드 확인 |
| R-15 | 텍스트 경로 실패 | 출력은 **줄 단위로 즉시** 쓰이므로 중간에 예외가 나면 그 이벤트의 앞 줄까지 이미 나가 있다. 예외는 `GcalcliError`가 아니어서 `cli.main`이 잡지 않고(`cli.py:393-395`는 `GcalcliError`만) 트레이스백으로 끝난다. 원인: `attendees`가 있는데 `organizer`가 없음(`KeyError`), `conferenceData`에 `entryPoints`/`entryPointType`/`uri` 없음, `reminders`에 `useDefault` 키가 없음 또는 override에 `method`·`minutes` 없음, `--details calendar`인데 `gcalcli_cal` 없음, `--override-color`에서 모르는 `colorId` | 코드 확인 |

**D. 달력(calw·calm)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-16 | `CalQuery` 시작·범위 (C-07) | `start_text`가 비면 `self.now`의 현지 자정, 아니면 `get_time_from_str(start_text)`의 자정(`replace(hour=0,…)`). 파싱이 **어떤 예외든** 나면 stderr에 `Error: failed to parse start time '<text>'\n`(brightred)을 쓰고 **None 반환**(조회·출력 없음, 종료 코드는 0). `calw`: `start -= _cal_weekday_num(start)`일, `end = start + count*7일`. `calm`: `start`는 그 달 1일 자정, `end`는 다음 달 1일(12월은 다음 해 1월), `count = ceil((일 수 + offset_days) / 7)`, `offset_days`는 `%w`(일=0)이고 `week_start`가 MONDAY면 `(x-1+7)%7`. 이어 `_search_for_events(start, end, None)`로 조회하고 `_GraphEvents(cmd, start, count, list)` 호출. **`--noweekend`일 때도 `calm`의 `offset_days`는 `week_start`만 본다**(원본 주석 TODO) | 코드 확인 |
| R-17 | `_cal_weekday_num(day)` (C-02) | `int(day.strftime('%w'))`(일=0)이되, `week_start == MONDAY` **또는 `cal_weekend`가 거짓**이면 월=0으로 바꾼다(`(n-1+7)%7`). 즉 `--noweekend`는 `--monday`를 암시한다. `--noweekend`에서 토·일 이벤트의 번호는 5·6이라 출력 열(0~4)에 없고 **조용히 사라진다** | 코드 확인 + 실행 확인 |
| R-18 | `_GraphEvents` 머리 (C-05) | 앞에서부터 `event_list[0]['s'] < start_datetime`인 이벤트를 모두 버린다(목록이 `s` 정렬이라는 가정; 첫 이벤트가 범위 안이면 이후는 검사하지 않는다). 요일명은 `date(2001,1,1+i).strftime('%A')`(2001-01-01=월요일, 로케일), `week_start != MONDAY` 또는 `cal_weekend` 거짓이면 `names[6:]+names[:6]`로 일요일 시작으로 돌린다(5열이면 이 회전은 월~금 그대로). `calw`: 위 테두리(`ulc,ute,urc`). `calm`: `ulc,hrz,urc` 선, `%B %Y` 월 제목(폭 `width['day']*days+days-1`까지 공백 채움, 색 `color_date`), `lte,ute,rte` 선. 이어 `vrt` + 요일명(`day` 폭 공백 채움, `color_date`)을 열마다, `lte,crs,rte` 구분선. 선·세로줄은 `color_border`, 모든 폭 계산은 `_printed_len` | 코드 확인 + 실행 확인 |
| R-19 | 날짜 줄 | `calm`이면 먼저 `start_datetime -= _cal_weekday_num(start)`일(그 달 1일이 속한 주의 첫날). 주마다 열 j의 날짜 `d`: `calw`는 `%d %b`, `calm`은 `%d`이되 **그 날의 `%b`가 처음의 달 약자와 다르면 빈 문자열**(앞·뒤 달 날짜 비움). 오늘(`self.now.strftime('%d%b%Y')`가 같은 날)이면 색을 `color_now_marker`로, `d += ' **'`. 오른쪽을 `day` 폭까지 공백 채운다(넘치면 채우지 않고 자르지도 않는다 → 테두리가 밀림). `vrt`는 `color_border` | 코드 확인 + 실행 확인 |
| R-20 | `_get_week_events(start_dt, end_dt, event_list)` (C-03) | 주 하나(`[start_dt, end_dt)`, 7일)의 요일별 `EventTitle` 목록. 이벤트마다 ① 포함: `s`가 `[start_dt, end_dt)`에 있거나(`_event_time_in_range`: `start <= t < end`), **종일 이벤트**가 `start_dt` 전에 시작해 `start_dt` 이후까지 이어질 때(`_event_spans_time`: `e_start < t and e_end >= t`; 종일의 `e_end`는 `e - 1일`). ② 색: 아래 "지금 표시"가 아니면 R-09와 같은 `--override-color` 규칙의 이벤트 색(진행 중 강조 없음). ③ 제목 `_format_title(event, allday)`(C-02): 종일은 제목만, 24시간은 `'%H:%M 제목'`, 12시간은 `'%I:%M'`의 선행 0 제거 + `%p` 소문자 + 공백 + 제목(`9:00am Standup`). ④ 종일이고 `s < e-1일`이면 `[요일(s) … 요일(e-1일)]` 열 전부에 추가(`e-1일 > end_dt`면 6열까지; **`요일(s) > 끝 열`이면 시작 열을 0으로**), 아니면 `s`의 요일 열에만 추가. 모든 항목의 제목은 `'\n'`으로 시작하고, 요일 번호는 R-17이다. | 코드 확인 + 실행 확인 |
| R-20a | R-20의 "지금 표시" | `self.now`가 `[start_dt, end_dt]`에 있고(`end_dt` 포함) 아직 표시되지 않았다면, 이벤트를 `s` 순으로 보며: (i) `days_since_epoch(now) < days_since_epoch(event.s)`(**시각을 포함한 실수 일수** 비교, 같은 날 뒤쪽 시각도 해당)이면 그 이벤트의 `s` 요일 열에 `EventTitle('\n' + '-' * width['day'], color_now_marker)`를 이벤트 항목 **앞에** 추가하고 이후 표시 없음; (ii) 아니면 `s <= now <= e`이고 **종일이 아니면** 그 이벤트 색을 `color_now_marker`로 바꾸고 이후 표시 없음. 표시되지 않으면 선도 없다(이벤트가 모두 과거이거나 이번 주에 `now` 이후 이벤트가 없을 때). 종일 이벤트는 (ii)에서 제외되지만 (i)에서는 후보가 된다 | 코드 확인 + 실행 확인 |
| R-20b | 종일 다일 이벤트의 열 범위의 경계 사례 | 위 ④ 때문에 주 첫날(일요일 시작이면 일요일)에 **끝나는** 종일 이벤트(예: 금~일)는 `end_dt` 비교가 `>` 라 `끝 열 = 요일(e-1일) = 0`, `시작 열(5) > 0` → 시작 열을 0으로 바꿔 **0열(첫 열) 한 칸에만** 그려진다(금·토 열에는 없음). 또 이전 주에서 이어지는 이벤트가 이 주 끝을 넘으면 열 범위는 `s`의 요일부터 6까지다(첫 열부터가 아니다) | 코드 확인 + 실행 확인(첫 사례만) |
| R-21 | 줄 나누기 (C-04) | `_printed_len(s) = Σ UNIWIDTH[east_asian_width(c)]`(`W`·`F`=2, `N`·`Na`·`H`·`A`=1; 결합 문자·로케일 모호 폭을 따로 다루지 않는다). `_get_cut_index(t)` → `(폭, 문자 수)`: ① `t`에 `\n`이 있고 **문자 인덱스**가 `<= width['day']`이면 그 앞까지(`\n`만 맨 앞이면 `(0,0)`); ② `_printed_len(t) <= width['day']`이면 전체; ③ 아니면 `_next_cut`: 공백 분리 단어를 누적해 다음 단어가 폭 이상이 되면 그 앞 단어까지(`len(' '.join(words[:i]))`로 잘라 **원문의 연속 공백·개행 폭을 무시**한다), 첫 단어가 넘치면 `_word_cut`으로 단어 안에서 `폭 >= width['day']`가 되는 첫 글자 뒤에서 자른다(폭 2 문자가 걸리면 **`width['day']+1`까지 나갈 수 있다**). 잘라 낸 뒤 나머지는 `strip()`하고 다음 줄에 이어 쓴다(이어진 줄은 들여쓰기·접두 없음) | 코드 확인 + 원본 테스트 열람 + 실행 확인 |
| R-22 | 주 본문 출력과 마무리 (C-05) | 주마다 날짜 줄 뒤, 열마다 `week_events[j]`의 첫 `EventTitle`을 `_get_cut_index`로 잘라 `제목[:cut] + 공백(폭-출력폭)`을 **그 항목 색**으로, 이어 `vrt`(`color_border`)를 쓰는 것을 줄마다 반복한다(항목이 없는 열은 `' ' * day + vrt`를 `color_border`로). 잘라 낸 나머지가 비면(`strip()` 후) 항목을 제거한다. 모든 열이 비어 있는 **줄도 한 번 출력**하고 끝낸다(항목이 `'\n'`으로 시작하므로 이벤트 앞에는 빈 셀 줄이 하나 생기고, 주마다 마지막에 빈 줄 하나가 남는다). 주 사이는 `lte,crs,rte` 구분선, 마지막 주는 `llc,bte,lrc` 바닥선. `count <= 0`이면 머리만 쓰고 바닥선이 없다. `--nostarted`·`--nodeclined`·`--tsv`·`--json`·`--details`는 `calw`·`calm`에서 읽지 않는다(코드에 참조 없음: `_GraphEvents`·`_get_week_events` 본문 범위). `--override-color`와 `--military`·`--color-*`·`--width`는 쓴다 | 코드 확인 + 실행 확인 |

- 불변식: 한 줄에서 열 j의 셀은 `day` 폭을 넘지 않는 것이 의도지만, `_word_cut`의 폭 2 문자 초과·`d`/요일명이 `day`보다 긴 경우(R-19)·결합 문자에서는 깨질 수 있다(U-03).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-06, R-07 | 비 TTY(파이프) 출력에서 `get_terminal_size()`가 돌려주는 열 수와, `locale_has_24_hours()`가 실제 로케일마다 어떤 값을 내는가(`nl_langinfo(T_FMT)`에 `'20'`) | `--width`·`--military` 기본값. 코드는 호출만 하며 값은 실행 환경 의존 | 대상 로케일·터미널에서 `python -c` 실행(여기서는 `C`·환경 로케일 두 경우만 `True`) |
| U-02 | R-11 | 로케일이 `%p`를 빈 문자열로 돌려줄 때(예 일부 glibc 로케일) 12시간 표기의 접미사 | 접미사 없는 `1:00` 출력이 정상인지 | glibc `de_DE.UTF-8` 등에서 `strftime('%p')` 실행. 코드는 그 값을 그대로 쓴다 |
| U-03 | R-21 | 결합 문자(폭 0)·모호 폭(`A`)·이모지 ZWJ 시퀀스에서 `_printed_len`이 터미널 실제 폭과 어긋날 때의 정렬 | 구현이 같은 `east_asian_width` 표를 쓰면 원본과 같은 어긋남을 재현한다 | 해당 문자열로 실제 터미널에서 확인 |

- 확인 한계: 실제 터미널·로케일을 쓰지 못했다. 사례는 `TZ=UTC`, `LC_ALL=C`(환경 로케일), 유럽 날짜 기준 2026-11-15(일)~21(토) 주에서 이벤트를 직접 만든 dict로 `_PrintEvent`·`_GraphEvents`를 호출해 얻었고(Calendar API·인증 없음, `userless_mode`로 생성자 호출, 의존 패키지 최신 버전을 임시 환경에 설치), 색 코드는 `use_color=False`로 지워 비교했다. `fancy` 선은 문자열 비교만 했다. 터미널에서 이스케이프가 실제로 어떻게 보이는지, `--locale` 적용 뒤 요일·월 이름은 실행하지 않았다. 호출 경로의 `cli.main`·argparse 배선은 코드로만 확인했다(실행 안 함).

### 1.5 필수 코드 참조 [필수]
라이선스: overview 1절을 따른다(이 문서는 줄 범위만 가리킨다).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/printer.py:1-101` | `COLOR_NAMES`·`ART_CHARS` 표(세 스타일의 11개 태그), `valid_color_name`, `Printer`(색 표·conky 표·`msg`·`err_msg`·`debug_msg`·`art_msg`) | R-01~R-05 |
| C-02 | `gcalcli/gcal.py:397-423` `_cal_weekday_num`, `_event_time_in_range`, `_event_spans_time`, `_format_title` | 요일 번호 변환, 구간 판정 두 개, 달력 제목 문자열 | R-17, R-20 |
| C-03 | `gcalcli/gcal.py:435-522` `_get_week_events` | 포함 조건, 지금 표시, 종일 다일 열 범위 | R-20, R-20a, R-20b |
| C-04 | `gcalcli/gcal.py:68`, `44`, `524-575` `UNIWIDTH`, `EventTitle`, `_printed_len`, `_word_cut`, `_next_cut`, `_get_cut_index` | 폭 계산, 자르기 알고리즘 | R-21 |
| C-05 | `gcalcli/gcal.py:577-725` `_GraphEvents` | 테두리·제목·요일·날짜 줄·본문 루프·구분선 | R-18, R-19, R-22 |
| C-06 | `gcalcli/gcal.py:779-987` `_PrintEvent`(내부 `_format_descr` 포함) | 줄 형식 문자열 전부, 순서, 설명 상자 | R-09~R-15 |
| C-07 | `gcalcli/gcal.py:1363-1406` `CalQuery` | 시작·끝·주 수 계산, 파싱 실패 처리 | R-16 |
| C-08 | `gcalcli/utils.py:182-185` `agenda_time_fmt` | 아젠다 시각 문자열(24시간 `lstrip`) | R-11 |
| C-09 | `gcalcli/argparsers.py:77-93`, `129-138`, `185-243`, `246-267`, `296-315`, `560-585`; `gcalcli/cli.py:210-213`, `269-278`; `gcalcli/gcal.py:78-92` | 옵션 정의·기본값, `Printer` 생성, `calw`/`calm` 배선, 생성자의 폭 계산 | 1.3, R-01, R-06~R-08 |

`days_since_epoch`·`is_all_day`·`validwidth`·`get_auto_width`·`locale_has_24_hours`는 [input-parsing](input-parsing.md)(R-23, R-24 등), `_calendar_color`는 [calendar-selection](calendar-selection.md) C-04가 소유한다.

### 1.6 수락 사례 [필수]
출처: T-01~T-06은 구현에서 도출하고 실행으로 확인(위 확인 한계의 환경), T-07은 원본 테스트 열람(`tests/test_gcalcli.py:377-392`), T-08은 `tests/test_printer.py`. 대체: Calendar API·인증 없이 이벤트 dict를 직접 만들고 `use_color=False`·`LC_ALL=C`·`TZ=UTC`·`width['cal']=80`(day=10)로 호출했다. 터미널에서의 실제 표시·로케일별 이름은 검증하지 않는다. 대표 이벤트(캘린더 `Cal`, owner): 2026-11-18(수) 10:30을 `now`로 한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-09~R-11, R-13 | 12시간, `--details end,length,calendar`. 이벤트 09:00~10:00 `Standup`(프리픽스 `'\nWed Nov 18'`) | `\nWed Nov 18  9:00am  - 10:00am  Standup\n` 뒤에 `' '*19 + '  Calendar: Cal\n'`, `' '*19 + '  Length: 1:00:00\n'`. 이 이벤트는 `e < now`이므로 이벤트 색은 `calendar` 색. 10:00~11:30 이벤트는 `happening_now`라 `color_now_marker` |
| T-02 | R-10, R-11 | 24시간(`--military`). 같은 날 00:05~00:45 `Midnight` | 이벤트 줄의 시각은 `:05`(`'  %-5s   %-5s  %s'`로 `:05` + 공백 + 제목), 같은 이벤트가 달력에서는 `00:05 Midnight`. 종일 이벤트 `Holiday`(`s`=`e-1일` 자정, prefix 있음): `Mon Nov 16` 뒤에 시간 칸 없이 `         Holiday`(공백 9칸: 2+5+2) |
| T-03 | R-08, R-18~R-20, R-22 | 12시간, ascii, 폭 80, 일요일 시작, `calw`, 시작 2026-11-15(일), 이벤트: `Holiday`(월 종일), `Standup` 09:00, `Design review with a very long title` 10:00, `Lunch` 13:00(수) | 헤더 `+----------+…+`(+는 7+1개), `\|Sunday    \|Monday …\|Saturday  \|`, 날짜 줄 `\|15 Nov    \|16 Nov    \|17 Nov    \|18 Nov ** \|…`. 수요일 열: 빈 셀, `9:00am`, `Standup`, 빈 셀, `10:00am`, `Design`, `review`, `with a`, `very long`, `title`, 빈 셀, `1:00pm`, `Lunch`, 빈 셀(10:00 이벤트는 `now`=10:30을 포함하므로 지금 선은 없다). 월요일 열: 빈 셀, `Holiday` |
| T-04 | R-20a | T-03에서 `now`를 12:00로 바꾼다 | 수요일 열의 `Lunch`(13:00) 앞에 셀 하나가 `----------`(대시 10개)로 채워진다. 지금이 어떤 이벤트에도 속하지 않고 이후 이벤트가 있기 때문이다. 10:00~11:30 이벤트는 강조되지 않는다 |
| T-05 | R-20b | 일요일 시작 주, 종일 `Trip` 금(11-20)~일(11-22) (`e`=11-23) | 첫 열(일요일)에만 `Trip`이 나오고 금·토 열에는 없다 |
| T-06 | R-17, R-08 | `--noweekend --monday`, `calw`, 시작 11-16(월), 토요일 09:00 이벤트와 수요일 이벤트 | `days=5`, `width['day']=int((80-5-1)/5)=14`, 열 헤더 월~금, 토요일 이벤트는 어디에도 나오지 않는다 |
| T-07 | R-21 | `width['day']=10`: `_next_cut('first looooong')`, `('tooooooooooooooooooooooooloooooooooong')`, `('one two three four')`, `('樹貞 fun fun fun')`. 추가: `_get_cut_index('\n-----')`, `'aaaa  bbbb cc dd'` | `(5,5)`, `(10,10)`, `(7,7)`, `(8,6)`(원본 테스트), 추가 두 개는 `(0,0)`, `(9,9)`(연속 공백 때문에 `bbbb`가 `bbb`와 `b`로 갈린다) |
| T-08 | R-02~R-05 | `Printer().msg('msg','red',file=buf)`, `Printer(conky=True).msg('msg','red',…)`, 모든 `COLOR_NAMES`로 `msg`; `Printer(use_color=False, art_style='fancy').art_msg('vrt','white',…)` | `'\033[0;31mmsg\033[0m'`, `'${color red}msg${color}'`, `colors[name] + 'msg' + '\033[0m'`(원본 테스트); 마지막은 색 없이 `'\033(0x\033(B'` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@405639c) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01(`printer.py:67-70`), `cli.py:210-213`, `gcal.py:47`(`PRINTER`), 생성자 `gcal.py:73-80` | 줄 추적 |
| R-02 | C-01(`printer.py:85-101`), `tests/test_printer.py:20-60` | 줄 추적 + 테스트 열람(실행 안 함). `file=sys.stdout` 기본값이 정의 시점에 묶인다는 것은 파이썬 의미론이며 이 레포 테스트가 `capsys`로 어떻게 보는지는 열지 않음 |
| R-03 | C-01(`printer.py:4-9`, `67-83`) | 줄 추적 + 실행으로 비교 |
| R-04 | C-01(`printer.py:10-47`, `99-101`), `gcal.py:577-725`의 `art_msg`·`msg(… + art[…])` | 실행: `fancy`·`use_color=False`의 `art_msg` 출력이 시퀀스 그대로임을 repr로 확인 |
| R-05 | C-01(`printer.py:56-60`), `tests/test_printer.py:15-17`, `deprecations.py:60-90`, `cli.py:85-102`(`parse_cal_names`) | 줄 추적. 에러 메시지의 나열 순서는 `COLOR_NAMES`가 `set`이라는 코드 사실에서 |
| R-06, R-07 | `argparsers.py:141-160`, `185-243`, `cli.py:155-156`(파서가 `main` 첫 줄에서 구성), `cli.py:224-225`(`--locale`은 파싱 뒤 적용), `utils.py:21` | 줄 추적. 값 자체는 U-01 |
| R-08 | `gcal.py:78-92` | 줄 추적 + 실행(80→10, 5열→14) |
| R-09 | C-06(`gcal.py:812-833`), calendar-selection R-10 | 줄 추적. `now`는 event-query R-17 |
| R-10 | C-06(`gcal.py:835-849`), `utils.py:182-185` | 줄 추적 + 실행 |
| R-11 | C-08, C-02(`gcal.py:415-423`) | 줄 추적 + 실행(`:05`). `%p` 빈 값은 U-02 |
| R-12, R-13 | C-06(`gcal.py:851-958`) | 줄 추적. `--details` 선택지는 `details.py:395`의 `DETAILS`와 `argparsers.py:129-138` |
| R-14 | C-06(`gcal.py:781-806`, `944-987`) | 줄 추적 + 실행(상자 모양) |
| R-15 | C-06, `cli.py:393-395`(`except GcalcliError`만) | 줄 추적. "다른 예외 처리는 없다"는 부재 주장: `grep -n "except" gcalcli/cli.py gcalcli/gcal.py`로 `_PrintEvent` 호출 경로를 보았고 `_PrintEvent`를 감싸는 `try`가 없다(범위 `gcalcli/`). 외부 래퍼·`sys.excepthook` 가능성은 확인하지 않음 |
| R-16 | C-07(`gcal.py:1363-1406`), `cli.py:269-278`, `argparsers.py:560-585` | 줄 추적 |
| R-17 | C-02(`gcal.py:397-407`), `gcal.py:84-87`(`days`) | 줄 추적 + 실행(토요일 이벤트 소실) |
| R-18 | C-05(`gcal.py:577-641`) | 줄 추적 + 실행. 부재 주장 "`details`·`ignore_*`를 읽지 않는다": `sed -n 435,725p gcalcli/gcal.py`의 본문에서 `self.details`·`ignore_started`·`ignore_declined`·`tsv`·`json`이 없음(범위 해당 줄). 매크로·동적 접근 가능성은 낮음 |
| R-19 | C-05(`gcal.py:643-675`) | 줄 추적 + 실행. `calm`의 월 경계는 `%b` 비교라 로케일 약자가 같은 다른 달(드문 로케일)은 확인 안 함 |
| R-20, R-20a, R-20b | C-03(`gcal.py:435-522`), C-02 | 줄 추적 + 실행(마커 선, 일요일 끝 종일 이벤트가 0열만 차지하는 사례). 이전 주에서 이어져 주 끝을 넘는 이벤트가 `s`의 요일부터만 그려진다는 점은 코드 추적만(실행하지 않음). 이어지는 이벤트가 주 중간에 끝나는 사례(수~다음 주 화)는 실행해 0열부터 끝 열까지 그려짐을 확인 |
| R-21 | C-04(`gcal.py:524-575`), `tests/test_gcalcli.py:377-392` | 줄 추적 + 테스트 열람 + 실행(5개 입력). `_word_cut`의 폭 초과는 코드 추적(실행 안 함) |
| R-22 | C-05(`gcal.py:677-725`) | 줄 추적 + 실행. `tests/test_gcalcli.py:79-95`는 `calw`·`calm` 출력이 `color_border` 코드 + `ulc` + `hrz*day`로 시작하는지만 본다(열람) |
| T-01~T-06 | 위 확인 한계의 실행 | 직접 만든 dict·고정 `now` 호출 결과를 옮겼다. T-01의 색 코드는 `use_color=False`로 지워 비교하지 못한 부분이 있다(이벤트 색 판단은 코드 추적) |
| T-07, T-08 | `tests/test_gcalcli.py:377-392`, `tests/test_printer.py` | 원본 테스트 열람 + 위 두 추가 입력은 직접 실행 |

### 2.2 코드 읽는 순서 [선택]
`cli.py:210-213`(Printer 생성) → `gcal.py:73-92`(폭) → 텍스트: `_iterate_events`(event-query C-03) → `_PrintEvent`(C-06) → `agenda_time_fmt`(C-08). 달력: `CalQuery`(C-07) → `_GraphEvents`(C-05) → `_get_week_events`(C-03) → 줄 나누기(C-04). `_tsv`·`_json`(`gcal.py:727-777`)은 이 스펙 밖이다.

### 2.3 비교·재사용 출처 [선택]
원본 코드를 복사하지 않았다. 다른 레포의 같은 기능 스펙은 없다.

### 2.4 검토 기록
- **작성자 점검**: 원본을 임시 환경(`/tmp/gc`, `userless_mode`, `TZ=UTC`·`LC_ALL=C`, 이벤트 dict 직접 구성)에서 실행해 T-01~T-06과 R-ID 상당수를 실제 출력으로 확인했다. 실행은 `repos/`를 바꾸지 않았다(`git status` 깨끗).
- **메인 세션 점검(2026-11-18)**: `check.py` 통과. 고위험 R-11(`agenda_time_fmt`의 `lstrip('0')`로 24시간 `00:05`가 `:05`가 됨)을 `utils.py:182-185`로 대조해 일치. 아래 보강은 작성자 보고 그대로이며 독립 검토로 재확인하지 않았다: R-20b 주 첫날에 끝나는 종일 다일 이벤트가 첫 열 한 칸에만 그려짐(실행 재현 T-05), `--noweekend`가 `--monday`를 암시하고 토·일 이벤트가 조용히 사라짐, `--nocolor`가 `fancy` 선의 VT100 시퀀스는 지우지 않음.
- **독립 검토 미수행**: 이 스펙에 의존하는 스펙 8·9가 있어 규칙상 대상이지만, 계획(3·4·6만)에 따라 생략했다. 필요하면 R-20a·R-20b·R-21·R-22(달력 레이아웃)부터 돌린다.
- **status를 `draft`로 유지하는 이유**: U-01~U-03(로케일·터미널 의존)이 열려 있고 선행 스펙들도 `draft`다.

## 적용 메모 [선택]
없음(원본 동작만 기술).
