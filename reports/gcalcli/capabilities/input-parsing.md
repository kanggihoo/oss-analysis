---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/utils.py
  - gcalcli/validators.py
  - gcalcli/argparsers.py
  - gcalcli/exceptions.py
  - gcalcli/cli.py
  - gcalcli/gcal.py
  - gcalcli/details.py
  - pyproject.toml
  - tests/test_utils.py
  - tests/test_input_validation.py
depends: []
status: draft
---

# 날짜·기간·알림 입력 파싱

> 사람이 쓴 문자열("tomorrow 3pm", "2h30m", "10m popup", "1:10")을 시각(datetime)·기간(timedelta)·알림(분, 방식)으로 바꾸고, 로케일(일/월 순서, 24시간제)을 반영하며, 대화형 입력 루프(`get_input`)와 검증기로 잘못된 입력을 다시 묻는 기능.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 호출자(argparse `type=`, 대화형 프롬프트, `get_times_from_duration`)가 문자열 하나를 넘긴다. 이 스펙은 그 문자열을 해석하는 부분만 맡고 서브커맨드 흐름은 제외한다.
2. 시각: `get_time_from_str`이 먼저 `dateutil`로 파싱한다. 시작이 `NN-NN-`이면 로케일의 일/월 순서를 `dayfirst`로 넘긴다. `ValueError`가 나면 `parsedatetime`으로 다시 해석한다. 둘 다 실패하면 `ValueError`.
3. 기간: `get_timedelta_from_str`이 (a) 숫자 = 분, (b) `DURATION_REGEX`(`2d 1h 3m 10s`, `2d:1h:3m`), (c) `parsedatetime`(`1:10`, `2 days 1 hour …`) 순서로 시도한다.
4. 시작+기간/끝: `get_times_from_duration`이 시작 문자열과 기간(또는 끝, 종일 여부)을 받아 ISO 8601 문자열 두 개로 돌려준다.
5. 알림: `parse_reminder`가 `REMINDER_REGEX`로 `"<숫자>[w|d|h|m] [popup|email|sms]"`를 `(분, 방식)`으로 바꾼다. 맞지 않으면 `None`이다.
6. 대화형: `get_input`이 프롬프트를 띄우고 검증기가 `ValidationError`를 내면 오류를 보여 주고 같은 프롬프트로 다시 묻는다. `?` 입력은 도움말을 보여 준다.
7. 로케일: `argparsers.locale_has_24_hours`가 `--military` 기본값을, `get_auto_width`가 `--width` 기본값을 정한다. `validwidth`가 30 미만을 거부한다.

### 1.2 범위·통합 지점
- 제공: 위 파싱 함수들, 검증기 모음(`validators.py` 전체), `validwidth`·`validreminder`·`locale_has_24_hours`·`get_auto_width`, 시각 보조 함수 `set_locale`·`localize_datetime`·`is_all_day`·`days_since_epoch`.
- 제외: 이 파서를 부르는 서브커맨드의 흐름(agenda/add/edit 조회·추가·수정). 호출 위치는 R-ID 경계 설명에서만 언급한다.
- 외부 의존: `dateutil.parser.parse`, `dateutil.tz.tzlocal`, `parsedatetime.Calendar`(`parse`, `parseDT`), `babel`(`Locale`, `default_locale`). `pyproject.toml`은 버전 상한·하한 없이 이름만 의존으로 적는다(`parsedatetime`, `python-dateutil`, `babel`; 코드 확인, 30~37행). 이 분석 환경에는 세 라이브러리가 설치돼 있지 않아(`ModuleNotFoundError: parsedatetime` 확인) 라이브러리 동작은 실행으로 확인하지 못했다(확인 한계).
- 소유 상태·부작용: `utils`를 import하면 `locale.setlocale(LC_ALL, '')`가 실행되고 `Calendar()` 인스턴스 두 개(`fuzzy_date_parse`, `fuzzy_datetime_parse`)가 모듈 전역으로 만들어진다. `set_locale`은 프로세스 로케일을 바꾼다. 그 외 함수는 순수 함수이고, 시계(`datetime.now`)와 환경(로케일, 터미널 크기)을 읽는다. `get_input`은 stdin/printer를 쓴다.

### 1.3 인터페이스와 데이터 의미
| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `get_time_from_str(when)` | string → tz-aware datetime | 실패 시 `ValueError('Date and time is invalid: <when>')`. 누락 필드는 "오늘 00:00(로컬 tz)"에서 채운다. |
| `get_timedelta_from_str(delta)` | string → timedelta | 실패 시 `ValueError('Duration is invalid: <delta>')`. 숫자는 분. |
| `get_times_from_duration(when, duration=0, end=None, allday=False)` | string, string/number, optional string, bool → (string, string) | 둘 다 `isoformat()` 결과. 종일이면 날짜(`YYYY-MM-DD`)만. 실패는 `ValueError`(메시지 R-10). |
| `parse_reminder(rem)` | string → (int minutes, string method) 또는 `None` | 방식 기본 `popup`. 주(w)·일(d)·시(h)는 분으로 환산, 접미사 없음/`m`은 그대로. |
| `REMINDER_REGEX` | 정규식 | `^(\d+)([wdhm]?)(?:\s+(popup|email|sms))?$` (C-01) |
| `DURATION_REGEX` | 컴파일된 정규식 | 일·시·분·초 그룹, 각각 소수 허용, 구분자 공백·`:` (C-01) |
| `set_locale(new_locale)` | string → 없음 | `locale.setlocale(LC_ALL, new_locale)`. `locale.Error`를 `ValueError`로 바꾼다. |
| `_is_dayfirst_locale()` | → bool | 로케일의 short date 패턴에서 `M`·`d` 중 먼저 나오는 쪽이 `d`이면 True. |
| `localize_datetime(dt)` | datetime/date → 같은 종류 | R-22 |
| `is_all_day(event)` | event(`s`,`e` datetime) → bool | R-23 |
| `days_since_epoch(dt)` | datetime → float(일) | R-24 |
| `validwidth(value)` | string → int | argparse `type`. 30 미만이면 `ArgumentTypeError('Width must be a number >= 30')`. 정수가 아니면 `int()`의 `ValueError`(argparse가 "invalid validwidth value"류 오류로 변환; argparse 동작은 추론). |
| `validreminder(value)` | string → 원래 string | `parse_reminder`가 `None`이면 `ArgumentTypeError('Not a valid reminder string: <value>')`. 반환은 입력 그대로(파싱 결과가 아니다). |
| `locale_has_24_hours()` | → bool | `time(20)`을 `nl_langinfo(T_FMT)`로 포맷해 `'20'`이 들어 있으면 True. `AttributeError`(예: Windows)면 False. |
| `get_auto_width()` | → int | `shutil.get_terminal_size().columns`. |
| `get_input(printer, prompt, validator_func, help=None)` | → 검증기 반환값 | R-18 |
| 검증기(`STR_NOT_EMPTY`, `STR_ALLOW_EMPTY`, `STR_TO_INT`, `PARSABLE_DATE`, `PARSABLE_DURATION`, `VALID_COLORS`, `REMINDER`) | string → 입력 그대로 | `ValidationError(message)`. 파싱 결과가 아니라 **입력 문자열을 그대로** 돌려준다. 호출자가 다시 파싱한다. |
| `get_override_color_id(color)` | string → string | `str(VALID_OVERRIDE_COLORS.index(color) + 1)`. 목록에 없으면 `ValueError`(list.index). |
| `VALID_OVERRIDE_COLORS` | 목록 | lavender, sage, grape, flamingo, banana, tangerine, peacock, graphite, blueberry, basil, tomato (순서가 id) |
| `DATE_INPUT_DESCRIPTION` | string | `a date (e.g. 2019-12-31, tomorrow 10am, 2nd Jan, Jan 4th, etc) or valid time if today` |

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `get_time_from_str(when)` 호출 | `dateutil.parser.parse(when, default=<오늘 00:00 로컬 tz>, dayfirst=<R-02>)`를 먼저 시도한다. 성공하면 그 값을 반환한다(시·분·초·tz 중 문자열에 없는 필드는 default에서 채워진다는 것은 dateutil의 `default` 의미). `ValueError`일 때만 R-04의 fallback으로 간다. | 코드 확인(호출 구조) / 추론(dateutil의 default 채움) |
| R-02 | `when`이 정규식 `^\d{1,2}-\d{1,2}-`로 시작 | `dayfirst = _is_dayfirst_locale()`(True/False). 시작하지 않으면(예: `2019-12-31`, `3/4/2025`, `tomorrow`) `dayfirst=None`을 넘긴다. 즉 로케일은 "`NN-NN-`로 시작하는 입력"에만 반영된다. `NN/NN/…`(슬래시)는 로케일을 보지 않는다. | 코드 확인 |
| R-03 | `_is_dayfirst_locale()` | `babel.Locale(babel.default_locale('LC_TIME'))`의 `date_formats['short'].pattern`에서 `M|d|$` 첫 매치가 `d`이면 True, `M`이거나 패턴에 둘 다 없으면 False. `babel.UnknownLocaleError`면 False. 그 외 예외는 잡지 않는다. | 코드 확인(함수 구조) / 추론(babel이 환경변수에서 로케일을 읽는 방식) |
| R-04 | dateutil이 `ValueError`를 낸 뒤 | `parsedatetime.Calendar().parse(when)`의 `(struct, result)`에서 `result`가 falsy(0)이면 `ValueError('Date and time is invalid: <when>')`. truthy이면 `datetime.fromtimestamp(time.mktime(struct), tzlocal())`(struct를 로컬 시각으로 보고 로컬 tz를 붙임). result 값(1 날짜/2 시간/3 둘 다)은 구분하지 않는다. | 코드 확인 |
| R-05 | dateutil이 `ValueError`가 아닌 예외를 냄 | `get_time_from_str`는 잡지 않아 그대로 전파된다(fallback도 안 간다). 어떤 입력이 그런 예외를 내는지는 라이브러리 확인이 필요하다(U-04). | 코드 확인(잡는 예외 종류) |
| R-06 | `get_timedelta_from_str(delta)` | 1) `timedelta(minutes=float(delta))`. `float`가 `ValueError`이면 다음 단계. 2) `DURATION_REGEX.match(delta)`가 매치하면 이름 있는 그룹 중 값이 있는 것만 `float`로 바꿔 `timedelta(**그룹)`. 그 변환이 `ValueError`이면 다음 단계. 3) `fuzzy_datetime_parse(delta, sourceTime=datetime.min)`의 `result`가 truthy이면 `dt - datetime.min`. 모두 실패하면 `ValueError('Duration is invalid: <delta>')`. | 코드 확인 |
| R-07 | R-06 1단계의 경계 | 음수(`-5`), 지수(`1e3`), 소수(`3.5`), 숫자 사이 `_`(`1_0`=10분)가 모두 분으로 받아들여진다(음수 timedelta도 반환). `nan`은 `timedelta`가 `ValueError`를 내 다음 단계로 간다. `inf`·`1e400`은 `OverflowError`가 나는데 `except ValueError`만 있어 **전파된다**(R-06의 `Duration is invalid`로 바뀌지 않는다). 무한대만의 문제가 아니다: 유한한 큰 값(`1e20`)도 `timedelta`가 `OverflowError`를 내고, 2단계도 `99999999999999d`처럼 정규식과 `float`를 통과한 큰 값이 `timedelta(days=…)`에서 같은 예외로 전파된다(`except ValueError`뿐, `utils.py:166`). `get_times_from_duration`은 `except Exception`이라 메시지로 바꾸지만 `PARSABLE_DURATION`은 `ValueError`만 잡아 대화형 입력이 크래시한다(R-19). `None`이 들어가면 `float(None)`의 `TypeError`도 R-06 단독으로는 잡히지 않는다(`get_times_from_duration`의 `except Exception`이 `Duration time is invalid: None`으로 바꾼다). | 코드 확인 + 실행 확인(stdlib `float`/`timedelta`, 함수 본문 로직을 복제해 재현) |
| R-08 | R-06 2단계의 경계 | 빈 문자열 `''`과 공백만 있는 문자열은 1단계에서 실패하지만 정규식이 모든 그룹 선택적이라 매치해 **`timedelta(0)`**을 반환한다(fallback에 가지 않는다). 단위는 소문자 `d|day|days`, `h|hour|hours`, `m|min|mins|minute|minutes`, `s|sec|secs|second|seconds`만 받고, 순서는 일→시→분→초 고정이다. 숫자와 단위 사이 공백(`1 h`, `2 days 1 hour …`)은 정규식 불일치라 3단계로 간다. 그룹 구분자는 공백·`:`의 0회 이상이라 `1h:`도 1시간. `1.2.3h`는 정규식은 매치하나 `float`가 실패해 3단계로 간다. | 코드 확인 + 실행 확인(정규식·float 재현) |
| R-09 | R-06 3단계 | `parsedatetime`이 어떤 문자열을 기간으로 읽는지는 라이브러리 소관이다. 원본 테스트는 `'1:10'`=1h10m, `'2 days 1 hour 2 minutes 40 seconds'`=2d1h2m40s, `'junk'`→`ValueError('Duration is invalid: junk')`를 단언한다(정규식 단계로는 앞의 두 입력이 매치하지 않으므로 이 값들은 3단계 결과다. 1단계는 float 실패, 2단계는 `1:10`이 단위 없음이라 불일치, 둘째는 숫자-단위 사이 공백). `result`가 truthy이기만 하면 결과가 날짜성(예: "tomorrow")이어도 `dt - datetime.min`을 반환한다. | 원본 테스트 열람(`tests/test_utils.py:13-32`) / 코드 확인(분기) / 추론(날짜성 입력의 결과) |
| R-10 | `get_times_from_duration(when, duration=0, end=None, allday=False)` | 1) `get_time_from_str(when)`의 **모든 예외**를 `ValueError('Date and time is invalid: <when>\n')`로 바꾼다. 2) `end`가 None이 아니면 `stop = get_time_from_str(end)`(예외를 바꾸지 않아 메시지에 `\n`이 없고, `duration`·`allday`는 무시된다. 종일이어도 날짜로 자르지 않고 시각 포함 ISO). 3) `allday`면 `stop = start + timedelta(days=float(duration))`, 실패(`Exception` 전부)는 `ValueError('Duration time (days) is invalid: <duration>\n')`, 이어서 `start=start.date()`, `stop=stop.date()`(소수 일수는 날짜로 자를 때 잘림). 4) 아니면 `stop = start + get_timedelta_from_str(duration)`, 실패(`Exception` 전부)는 `ValueError('Duration time is invalid: <duration>\n')`. 5) `(start.isoformat(), stop.isoformat())` 반환. | 코드 확인 |
| R-11 | `parse_reminder(rem)` | `re.match(REMINDER_REGEX, rem)`가 None이면 `None`(예외 없음). 매치하면 `n=int(그룹1)`; 그룹2가 `w`면 `n*7*24*60`, `d`면 `n*24*60`, `h`면 `n*60`, `m`이거나 비어 있으면 `n` 그대로. 그룹3이 없으면 `'popup'`. 반환 `(n, method)`. 0은 유효(`(0,'popup')`). 상한은 코드에 없다. | 코드 확인 |
| R-12 | `REMINDER_REGEX`의 경계 | 대소문자 구분(`10M`, `Popup` 불일치). 숫자는 `\d+`라 부호·소수 불가(`-5`, `1.5h`, `1h30m` 불일치), 접미사는 한 글자만, 앞뒤 공백 불일치(` 10m`, `10m popup `). 숫자와 방식 사이는 `\s+`라 탭·여러 칸 허용. `$`는 끝 개행 직전에도 매치하므로 **`'10m\n'`이 매치**한다. `\d`는 유니코드 숫자(`٣m`)를 허용하고 `int()`가 변환한다. | 실행 확인(정규식 재현, stdlib) |
| R-13 | `validreminder(value)` | `parse_reminder(value)`가 None이면 `argparse.ArgumentTypeError`, 아니면 `value`(원문)를 반환한다. 튜플은 truthy라 `0` 등도 통과한다. | 코드 확인 |
| R-14 | `validwidth(value)` | `int(value)`(실패하면 `ValueError`가 argparse로 전파) 후 30 미만이면 `ArgumentTypeError('Width must be a number >= 30')`. 상한 없음. 반환은 int. | 코드 확인 / 추론(argparse의 `ValueError` 처리) |
| R-15 | `locale_has_24_hours()` | `datetime.time(20).strftime(locale.nl_langinfo(locale.T_FMT))`에 `'20'`이 부분 문자열로 있으면 True. `nl_langinfo`가 없어 `AttributeError`이면 False. 12시간제 포맷(`08:00:00 PM`)은 `'20'`이 없다고 보고 False. 평가 시점의 프로세스 로케일을 쓴다. | 코드 확인 |
| R-16 | `--width`/`--military` 기본값의 평가 시점 | `get_output_parser`가 호출될 때 `get_auto_width()`와 `locale_has_24_hours()`를 한 번 평가해 기본값으로 고정한다. `cli.py:main`은 `get_argument_parser()`를 먼저 부르고 `--locale` 적용(`set_locale`)은 그 이후(`cli.py:223-227`)이므로 `--locale`은 이 두 기본값에 영향을 주지 않는다. `--military`와 `--no-military`는 같은 dest(`military`)에 같은 기본값을 둔다. | 코드 확인(호출 순서) |
| R-17 | `set_locale(new_locale)` | `locale.Error`를 `ValueError('Error: <원문>!\n Check supported locales of your system.\n')`로 바꾼다. 호출자(`cli.py:223-227`)는 이를 잡아 `printer.err_msg`로 출력만 하고 진행한다. | 코드 확인 |
| R-18 | `get_input(printer, prompt, validator_func, help=None)` | `printer.msg(prompt, 'magenta')` 후 무한 루프: `input()`으로 한 줄 읽는다. 입력을 `strip()`한 결과가 `'?'`이고 `help`가 있으면 `printer.msg(f'{help}\n')`와 프롬프트를 다시 출력하고 계속한다(검증기 호출 없음). 아니면 **strip하지 않은 원문**을 `validator_func`에 넘기고 그 반환값을 반환한다. `ValidationError`이면 `e.message`를 red로 출력하고 프롬프트를 다시 출력하며 반복한다. 그 외 예외(`EOFError`, `KeyboardInterrupt`, 검증기가 던지는 `ValueError`)는 전파된다. `help=None`이면 `?`도 일반 입력으로 검증기에 간다. | 코드 확인 |
| R-19 | `PARSABLE_DATE`·`PARSABLE_DURATION` | 각각 `get_time_from_str`/`get_timedelta_from_str`을 호출해 **`ValueError`만** `ValidationError`로 바꾼다(메시지: 날짜 `Expected format: <DATE_INPUT_DESCRIPTION>. (Ctrl-C to exit)\n`, 기간 `Expected format: a duration (e.g. 1m, 1s, 1h3m)(Ctrl-C to exit)\n`, 사이 공백·마침표 없음). 성공하면 입력 문자열을 그대로 반환한다. R-07의 `OverflowError`, R-05의 비-`ValueError`는 `get_input` 밖으로 전파되어 프로세스를 끝낼 수 있다. | 코드 확인 / 추론(실제 크래시 입력은 U-04) |
| R-20 | `REMINDER` 검증기 | `re.match(REMINDER_REGEX, input_str)`가 매치하거나 입력이 정확히 `'.'`이면 입력 그대로 반환, 아니면 `ValidationError('Expected format: <number><w|d|h|m> <popup|email|sms>. (Ctrl-C to exit)\n')`. 빈 문자열은 거부. `'.'`이 "입력 끝"이라는 의미는 호출자(`cli.py:145-151`)가 해석한다. | 코드 확인 |
| R-21 | 나머지 검증기 | `STR_NOT_EMPTY`: `None` 또는 `''`만 거부(공백만 있는 문자열은 통과, 메시지 `Input here cannot be empty. (Ctrl-C to exit)\n`). `STR_ALLOW_EMPTY`: 전부 통과. `STR_TO_INT`: `int(input_str)`이 성공하면 원문 반환(`' 5 '`도 통과), 실패 시 `Input here must be a number. (Ctrl-C to exit)\n`. `VALID_COLORS`: `VALID_OVERRIDE_COLORS` 11개 또는 `''`만 통과(대소문자 구분), 실패 시 색 목록을 나열한 `Expected colors are: …. (Ctrl-C to exit)\n`. | 코드 확인 |
| R-22 | `localize_datetime(dt)` | `tzinfo` 속성이 없는 객체(`date`)는 그대로 반환. `tzinfo is None`이면 시각은 그대로 두고 `tzlocal()`을 붙인다. tz가 있으면 `astimezone(tzlocal())`로 변환. | 코드 확인 |
| R-23 | `is_all_day(event)` | `event['s']`와 `event['e']` 둘 다 hour==0이고 minute==0이면 True. 날짜·초·길이는 보지 않는다. 자정에 시작해 자정에 끝나는 일반 일정과 구분되지 않는다(소스 주석 XXX). | 코드 확인 |
| R-24 | `days_since_epoch(dt)` | `calendar.timegm(dt.timetuple()) / 86400`. `timetuple()`은 tz 변환 없이 달력 필드를 쓰므로 tz-aware라도 벽시계 필드를 UTC로 본 값이다. 1970-01-01 00:00은 0, naive 1970-12-31은 364. | 코드 확인 + 원본 테스트 열람(`tests/test_utils.py:67-70`) |

- 불변식: 시각 함수의 반환 datetime은 항상 tz-aware이다(R-01 default가 tz-aware, R-04가 `tzlocal()`을 붙임). 단 문자열이 명시적 tz를 가지면 그 tz가 남는다는 것은 추론이다. 검증기는 입력 문자열을 변형하지 않는다(R-18~R-21).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-01, R-02 | `dayfirst=None`을 dateutil이 "미지정(기본 False)"으로 취급하는가. `NN-NN-` 규칙이 2자리 연도형(`19-12-31`)까지 일/월 우선으로 바꾸는가. | 재구현자가 `dayfirst`를 None/False 중 무엇으로 넘겨야 같은 결과인지, `YY-MM-DD`의 결과를 모른다. | `python-dateutil` 설치 후 `parse('19-12-31', dayfirst=True/None)`와 `parse('03-04-2025', dayfirst=True/None)`를 실행. dateutil 소스의 `_parse`에서 `dayfirst is None` 처리 확인. |
| U-02 | R-03 | `babel.default_locale('LC_TIME')`이 `None`(환경변수 없음)이거나 `C`/`POSIX`일 때 `babel.Locale(...)`이 `UnknownLocaleError`를 내는가, 다른 예외(`TypeError` 등)를 내는가. 후자면 `get_time_from_str('01-02-2025')`가 크래시한다. | 로케일 미설정 환경에서의 실패 처리를 정할 수 없다. | `babel` 설치 후 `LANG`·`LC_ALL`·`LC_TIME` 없이/`C`로 `_is_dayfirst_locale()` 실행. |
| U-03 | R-04, R-09 | `parsedatetime`이 `result`를 낼 때 날짜만 읽은 입력("tomorrow")의 시각 성분은 현재 시각인가 00:00인가. 문장 일부만 해석되는 입력("tomorrow blah")도 `result`가 truthy인가. 기간 fallback에서 `10 m`, `1 h`, `1h 30`, 숫자-단위 사이 공백이 어떻게 읽히는가. | "내일 3pm" 외의 입력에서 시각·기간 결과를 재현할 수 없다. | `parsedatetime` 설치 후 `Calendar().parse`/`parseDT`를 위 입력으로 실행하고 `(struct, result)`를 기록. |
| U-04 | R-05, R-19 | dateutil이 `ValueError`가 아닌 예외(`OverflowError` 등)를 내는 입력이 있는가(예: 매우 큰 정수 문자열). 있으면 `PARSABLE_DATE`가 크래시한다. 현재 SHA에서 `dateutil` 어떤 버전이 이 동작을 내는가. | 검증기가 "모든 잘못된 입력"을 재질문으로 처리한다고 가정하면 틀린다. | `python-dateutil`로 `parse('99999999999999999999')`·`parse('2025-13-45')` 등을 실행. `pyproject.toml`에 버전 고정이 없어 설치 버전별로 다를 수 있다. |

- 확인 한계:
  - 이 환경에는 `parsedatetime`·`python-dateutil`·`babel`이 설치돼 있지 않다(`import parsedatetime` → `ModuleNotFoundError`, `pyproject.toml`은 버전 미지정, `uv.lock` 없음). 따라서 dateutil·parsedatetime·babel이 내는 실제 값은 실행으로 확인하지 못했다. 1.6의 사례 중 "실행 확인"은 `re`·`float`·`timedelta`(stdlib)로 원본 정규식과 분기를 복제해 돌린 것이고 원본 함수 자체를 실행한 것이 아니다.
  - `time.mktime`·`tzlocal()`은 실행 머신의 로컬 시간대에 따라 달라진다. DST 경계 입력(존재하지 않는 시각 등)의 결과는 확인하지 못했다.
  - 원본 테스트는 실행하지 않았다(`test_get_time_from_str`은 `'7am tomorrow'`가 truthy임만 단언, 실제 값 단언 없음).
  - `--locale`이 babel의 로케일 판정에 영향을 주는지(babel이 `os.environ`에서 읽는지, Python의 `locale` 모듈 상태를 보는지)는 babel 소스를 보지 않아 추론이다. 코드상 `_is_dayfirst_locale`은 `locale.setlocale` 상태를 직접 읽지 않고 `babel.default_locale`만 쓴다.

### 1.5 필수 코드 참조
라이선스 MIT(overview 1절)라 인용 가능.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/utils.py:26-33` `REMINDER_REGEX`, `DURATION_REGEX` | 알림·기간 정규식 두 개 전체 | R-08, R-11, R-12, R-20 |
| C-02 | `gcalcli/utils.py:36-54` `parse_reminder` | 단위 환산(w/d/h → 분)과 기본 방식 | R-11 |
| C-03 | `gcalcli/utils.py:96-139` `_is_dayfirst_locale`, `get_time_from_str` | dayfirst 판정, dateutil → parsedatetime fallback | R-01~R-05 |
| C-04 | `gcalcli/utils.py:142-174` `get_timedelta_from_str` | 3단계 기간 파서와 예외 처리 | R-06~R-09 |
| C-05 | `gcalcli/utils.py:68-93` `get_times_from_duration` | 시작/끝/기간/종일 조합과 오류 메시지 | R-10 |
| C-06 | `gcalcli/validators.py:13-39` | 색 목록, `DATE_INPUT_DESCRIPTION`, `get_override_color_id`, `get_input` 루프 | R-18, R-21 |
| C-07 | `gcalcli/validators.py:42-146` | 검증기 7개와 별칭 상수 | R-19~R-21 |
| C-08 | `gcalcli/argparsers.py:110-126`, `141-152` `validwidth`, `validreminder`, `locale_has_24_hours`, `get_auto_width` | 폭 최소값 30, 24시간제 판정, 터미널 폭 | R-13~R-15 |
| C-09 | `gcalcli/utils.py:57-65`, `177-207` `set_locale`, `days_since_epoch`, `is_all_day`, `localize_datetime` | 로케일 오류 변환, 날짜·tz 보조 함수 | R-17, R-22~R-24 |

### 1.6 수락 사례
출처: 구현에서 도출. 단, 표기가 "원본 테스트 열람"인 사례는 `tests/test_utils.py`에서 가져왔다. 검증 열의 "실행"은 stdlib로 원본 정규식·분기를 복제해 돌린 결과이며, "추론"은 라이브러리 설치 없이 코드·라이브러리 의미로 짐작한 것이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 검증 |
|---|---|---|---|---|
| T-01 | R-06 | `get_timedelta_from_str('3.5h')`, `'1'`, `'1m'`, `'1h1m'`, `'2d:1h:3m'`, `'2d 1h 3m 10s'` | 3h30m, 1분, 1분, 1h1m, 2d1h3m, 2d1h3m10s | 실행(분기 복제), 원본 테스트 열람 |
| T-02 | R-09 | `'1:10'`, `'2 days 1 hour 2 minutes 40 seconds'` | 1h10m, 2d1h2m40s (정규식 단계 실패 후 parsedatetime) | 원본 테스트 열람(실행 안 함), 정규식 불일치는 실행 |
| T-03 | R-06, R-09 | `'junk'` | `ValueError('Duration is invalid: junk')` | 원본 테스트 열람 |
| T-04 | R-08 | `''`, `'  '` | `timedelta(0)` (오류 아님) | 실행(복제) |
| T-05 | R-07 | `'-5'`, `'1e3'`, `'1_0'`, `'3.5'`, `'.5h'` | -5분, 1000분(16:40:00), 10분, 3분30초, 30분 | 실행(복제) |
| T-06 | R-07 | `'inf'`, `'1e400'` | `OverflowError` 전파(함수 밖). `'nan'`은 parsedatetime 단계로 간다 | 실행(복제) |
| T-07 | R-08 | `'1.2.3h'`, `'1h 30'`, `'1 h'`, `'1H'`, `'1m1h'`, `'1h 1h'`, `'10 m'` | 정규식 단계에서 실패하거나 float 실패 후 parsedatetime 단계로 간다. 최종값은 U-03 | 실행(정규식·float까지), 최종값 미확인 |
| T-08 | R-11, R-12 | `parse_reminder('10m popup')`, `'10 popup'`, `'10'`, `'5w'`, `'0'`, `'2h email'` | `(10,'popup')`, `(10,'popup')`, `(10,'popup')`, `(50400,'popup')`, `(0,'popup')`, `(120,'email')` | 실행(정규식), 환산은 코드 확인 |
| T-09 | R-12 | `'10M'`, `'10m Popup'`, `'-5'`, `'1.5h'`, `'1h30m'`, `''`, `' 10m'`, `'10m popup '` | 모두 `None` | 실행 |
| T-10 | R-12 | `'10m\n'`, `'10m\tpopup'`, `'10m  sms'` | 매치: `(10,'popup')`, `(10,'popup')`, `(10,'sms')` | 실행 |
| T-11 | R-13 | `validreminder('meaningless')` | `ArgumentTypeError('Not a valid reminder string: meaningless')`; `validreminder('10m sms')` = `'10m sms'`(문자열 그대로) | 코드 확인 |
| T-12 | R-20 | `REMINDER('.')`, `REMINDER('10 popup')`, `REMINDER('')`, `REMINDER('meaningless')` | 입력 그대로, 입력 그대로, `ValidationError`, `ValidationError` | 코드 확인(원본 테스트는 `ValidationError`가 나는 것만 단언) |
| T-13 | R-10 | `get_times_from_duration('1970-01-01T00:00:00+00:00', duration=120)` (`'2h'`, `'120m'`도) | `('1970-01-01T00:00:00+00:00','1970-01-01T02:00:00+00:00')` | 원본 테스트 열람(실행 안 함) |
| T-14 | R-10 | 같은 `when`, `duration=1`, `allday=True` | `('1970-01-01','1970-01-02')` | 원본 테스트 열람 |
| T-15 | R-10 | `get_times_from_duration('this is not a date')`, `duration='not a duration'`(`allday` 여부 무관) | `ValueError` (메시지 끝 `\n`) | 원본 테스트 열람(메시지는 코드 확인) |
| T-16 | R-10 | `when='2025-03-01'`, `end='2025-03-03'`, `allday=True` | 종일이어도 두 값 모두 **시각 포함 ISO**(`...T00:00:00+<로컬 오프셋>`). `duration`은 무시 | 코드 확인(분기 순서), 실행 안 함 |
| T-17 | R-10 | `when='2025-03-01'`, `duration='1.5'`, `allday=True` | `('2025-03-01','2025-03-02')` (1.5일 후가 3/2 12:00이므로 `.date()`로 잘림) | 코드 확인, 실행 안 함 |
| T-18 | R-10 | `when='2025-03-01'`, `duration='2h'`, `allday=True` | `ValueError('Duration time (days) is invalid: 2h\n')` (종일에서는 `float(duration)`만 허용) | 코드 확인 |
| T-19 | R-02 | `YYYY-MM-DD` 형태 `'2019-12-31'` | `dayfirst=None`으로 dateutil 호출(로케일 무관). 정규식 `^\d{1,2}-\d{1,2}-`는 `20`뒤가 `1`이라 불일치 | 코드 확인(정규식 불일치는 실행), 결과값은 추론 |
| T-20 | R-02, R-03 | 일 우선 로케일(예: `de_DE`)에서 `'03-04-2025'`; 월 우선(`en_US`)에서 같은 입력; 어느 로케일에서나 `'03/04/2025'` | 일 우선: dayfirst=True → 4월 3일로 해석될 것. 월 우선: 3월 4일. 슬래시 형식은 로케일 무관(dayfirst=None)해서 3월 4일일 것 | 추론(U-01) |
| T-21 | R-01, R-04 | `'tomorrow 3pm'` 또는 `'7am tomorrow'` | dateutil `ValueError`(추론) → parsedatetime fallback에서 내일 해당 시각, 로컬 tz. 원본 테스트는 `'7am tomorrow'` 반환값이 truthy임만 단언 | 원본 테스트 열람(truthy만), 값 추론(U-03) |
| T-22 | R-01 | `'3pm'`, `'10:30'`, `'Jan 4th'` | dateutil 성공 가정 시 누락 필드는 오늘 00:00에서 채움: 오늘 15:00, 오늘 10:30, 올해 1월 4일 00:00 | 추론(dateutil default 의미) |
| T-23 | R-04 | `'blah blah'` | dateutil `ValueError` → parsedatetime `result==0` → `ValueError('Date and time is invalid: blah blah')`. 테스트도 `'NON-DATE STR'`에 `ValidationError`를 단언 | 코드 확인, 검증기 쪽은 원본 테스트 열람 |
| T-24 | R-18, R-19 | `get_input(printer,'When (? for help): ', PARSABLE_DATE, help=H)`에 입력 `?`, `garbage`, `2nd January` 순서 | `?` → `H` 출력 후 재프롬프트(검증기 미호출). `garbage` → red `Expected format: ... (Ctrl-C to exit)` 후 재프롬프트. `2nd January` → 입력 문자열 `'2nd January'` 반환 | 코드 확인(조합), 파싱 성공은 추론 |
| T-25 | R-18 | `help=None`에서 입력 `?` | 일반 입력으로 검증기에 전달 | 코드 확인 |
| T-26 | R-19 | `PARSABLE_DURATION('1m')`, `'1h2m'`, `'NON-DATE STR'` | `'1m'`, `'1h2m'`, `ValidationError`(메시지는 위 R-19 문자열) | 원본 테스트 열람(`tests/test_input_validation.py:51-67`) |
| T-27 | R-21 | `STR_NOT_EMPTY('   ')`, `STR_TO_INT(' 5 ')`, `VALID_COLORS('')`, `VALID_COLORS('Sage')` | 통과, 통과, 통과, `ValidationError` | 코드 확인 |
| T-28 | R-14 | `validwidth('29')`, `'30'`, `'abc'` | `ArgumentTypeError`, `30`, `ValueError`(argparse가 오류로 변환) | 코드 확인 |
| T-29 | R-17 | `set_locale('not_a_real_locale')` | `ValueError` | 원본 테스트 열람(`tests/test_utils.py:72-74`) |
| T-30 | R-22 | `localize_datetime(datetime.now())`, UTC aware datetime, `date` 객체 | tz가 `tzlocal()`로 붙음, `astimezone`으로 변환, `date`는 그대로 | 원본 테스트 열람(앞 둘의 `tzinfo is not None`만), `date`는 코드 확인 |
| T-31 | R-23 | s=2025-01-01 00:00:30, e=2025-01-02 00:00 | True (초는 보지 않음). s=00:00, e=23:59 → False | 코드 확인 |
| T-32 | R-24 | `datetime(1970,1,1,0,tzinfo=UTC)`, `datetime(1970,12,31)` | `0`, `364` | 원본 테스트 열람 |
| T-33 | R-15, R-16 | `nl_langinfo(T_FMT)`가 `%H:%M:%S`인 로케일 / `%I:%M:%S %p` 로케일 / `nl_langinfo` 없는 플랫폼 | True / False / False. `--no-military` 지정 시 `military=False` | 코드 확인, 로케일별 T_FMT는 미실행 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
repo@405639c27639a82a13538ad72ae012e76942530c 기준.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-02, R-04, R-05 | C-03 (`utils.py:116-139`) | 본문 직접 읽음. dateutil의 `default` 채움 의미와 `dayfirst=None` 처리는 라이브러리 미설치라 추론(U-01). |
| R-03 | `utils.py:96-113` | `babel.default_locale`의 환경변수 읽기는 추론. 예외 종류는 U-02. |
| R-06~R-09 | C-04 (`utils.py:142-174`), C-01 | 본문 읽음. float·정규식·timedelta 거동은 `python3` stdlib로 분기를 복제 실행(원본 함수 자체는 import 불가라 미실행). parsedatetime 단계는 `tests/test_utils.py:13-32` 열람 외 확인 못 함. |
| R-10 | C-05 (`utils.py:68-93`), 호출자 `cli.py:292-301`, `gcal.py:1103-1120` | 본문 읽음. `end`가 있으면 `allday`를 무시한다는 점은 분기 순서(코드 확인). 호출자가 `ValueError`를 어떻게 다루는지는 이 스펙 밖(`cli.py`는 오류 출력 후 re-raise, `gcal.py` `_edit_event` 경로는 오류 출력 후 `sys.exit(1)` 또는 계속). |
| R-11~R-13, R-20 | C-01, C-02, `argparsers.py:120-126`, `validators.py:127-137` | 정규식은 `re` 실행으로 확인(T-08~T-10). "상한 없음"은 부재 주장: 검색 범위 `gcalcli/utils.py`, `argparsers.py`, `validators.py` 안에서 `parse_reminder` 결과에 대한 최댓값 비교를 찾지 못함(`grep -rn parse_reminder gcalcli` 호출처 `gcal.py:430,1141,1448`, `cli.py:151`; 호출자 쪽 검증은 이 스펙 밖). Google 쪽 제한은 확인하지 않음. |
| R-14, R-15, R-16 | C-08, `argparsers.py:218-235`, `cli.py:223-227` | 본문 읽음. 호출 순서는 `main`의 `get_argument_parser()` → `--locale` 적용 순서를 읽어 확인(`cli.py`의 `parser = get_argument_parser()`가 `main`의 첫 문장). |
| R-17 | C-09 (`utils.py:57-65`), `cli.py:223-227`, `tests/test_utils.py:72-74` | 코드와 테스트가 일치. |
| R-18~R-21 | C-06, C-07 | 본문 읽음. 사용처: `cli.py:130-151`(add --prompt), `gcal.py:1097-1131`(edit), `gcal.py:1421`(`STR_TO_INT`, 호출자 쪽). "사용처 전부" 주장은 하지 않는다. 문서 docstring과 코드 차이: `non_blank_str_validator` docstring "len > 1"인데 코드는 `None`/`''`만 거부(공백 문자열 통과). `parsable_date_validator` docstring은 "dateutil"이라 하지만 실제 `get_time_from_str`은 parsedatetime fallback도 쓴다. 원본 테스트(`tests/test_input_validation.py:36-48`)의 date 검증기 테스트는 `PARSABLE_DATE(input()) == ...`에 `assert`가 없어 성공 경로는 검증하지 않는다. |
| R-22~R-24 | C-09, `tests/test_utils.py:67-83`, 호출처 `gcal.py:445,816,470-471,1220,1228`, `details.py:99`, `ics.py` | 본문 읽음. 호출처는 일부만 확인, "사용처 전부" 주장 없음. |
| T-01~T-03, T-13~T-15, T-26, T-29, T-30, T-32 | `tests/test_utils.py`, `tests/test_input_validation.py` | 원본 테스트를 열어 사례를 가져옴. 실행은 하지 않음. |
| T-04~T-10 | 복제 스크립트(임시, 저장 안 함) | 원본 정규식 문자열과 `get_timedelta_from_str` 1·2단계를 복제해 `python3`로 실행. 원본 함수 호출은 아님. |
| 나머지 T | 코드 확인 또는 추론(표의 마지막 열) | 마지막 열 참조. |

### 2.2 코드 읽는 순서
`utils.py:116` `get_time_from_str` → 96 `_is_dayfirst_locale` → 142 `get_timedelta_from_str`(26-33 정규식) → 68 `get_times_from_duration` → 36 `parse_reminder` → `validators.py` 전체(`get_input` 26행, 검증기 42행~) → `argparsers.py` 110-126, 141-152, 그리고 `--width`(218)·`--military`(223)·`--reminder`(272) 등록부. 호출자 확인용: `cli.py:130-151`, `gcal.py:1097-1141`.

### 2.3 비교·재사용 출처
없음(다른 레포에 같은 기능 스펙 없음). 원본 코드를 복사하지 않았다.

### 2.4 검토 기록
- **메인 세션 점검(2026-11-18)**: `check.py` 통과, 고위험 R-07·R-08·R-12·R-16·R-17을 원본 줄과 대조해 일치.
- **독립 검토(읽기 전용 서브에이전트, 2026-11-18)**: R-01~R-24와 T-04~T-10 전부 대조. 반증된 R-ID 없음. 인용 줄 약 30개 표본 중 어긋난 2건(`cli.py` 223-227, `validators.py` 13-39)은 고쳤다. 아래 누락 4건은 본문에 반영했다.
  - 큰 유한값의 `OverflowError`(R-07에 추가).
  - CLI `--duration`은 `type=int`라 분(`--allday`면 일) 단위 정수만 받는다(`argparsers.py:624-627`). `2h` 같은 사람 기간은 대화형 프롬프트(`cli.py:136-138`)와 edit의 `g` 경로로만 들어온다. `--noprompt`이고 `--duration`·`--end`가 없으면 `duration=None`이 들어가 종일이 아니면 `Duration time is invalid: None`, 종일이면 `Duration time (days) is invalid: None`이 된다(`utils.py:79-83`; 스펙 event-create가 발견).
  - 호출자 쪽 관찰(이 스펙 범위 밖): edit의 `w` 경로가 분 단위 값(`gcal.py:1099-1104`)을 `duration`으로 넘기는데 `allday`이면 R-10 3단계가 일 단위로 읽는다. 별개 버그 후보로 행 8 스펙에서 다룬다.
  - `DURATION_REGEX`의 `$`도 끝 개행을 허용한다(`1h\n` 매치, 복제 실행). 실사용 영향은 작다(`input()`이 개행을 제거).
- **대조하지 않은 것**: U-01~U-04와 T-20~T-22(dateutil·parsedatetime·babel 미설치로 판단 불가), T-33의 로케일별 값, `ics.py`의 호출처, `quick` 등 `parse_reminder`를 안 쓰는 경로.
- **status를 `draft`로 유지하는 이유**: U-01~U-04가 열려 있다(라이브러리 동작 확인 필요). 이 4건이 닫히면 `ready` 후보다.

## 적용 메모
없음(재구현 목적 미정). 재구현 시 고려할 원본 특이점: R-07의 `OverflowError` 전파, R-10의 `end`가 `allday`를 무시, R-16의 `--locale`이 기본값에 반영되지 않는 순서.
