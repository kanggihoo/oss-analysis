---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/cli.py
  - gcalcli/gcal.py
  - gcalcli/argparsers.py
  - gcalcli/validators.py
  - gcalcli/utils.py
  - gcalcli/details.py
  - tests/test_gcalcli.py
  - tests/_utils.py
  - tests/cli/test.bats
  - tests/cli/__snapshot__/test-04-test_can_run_add.snap
depends:
  - input-parsing.md
  - calendar-selection.md
status: draft
---

# 일정 추가 (quick / add)

> `quick`은 자연어 한 줄을 Google Calendar `events.quickAdd`에 넘기고, `add`는 제목·장소·시각·길이(또는 끝)·종일 여부·설명·참석자·알림·색을 인자나 대화형 입력으로 받아 `events.insert` 요청 본문을 만들어 일정을 하나 만든다. 둘 다 여러 캘린더가 선택돼 있으면 대상 캘린더를 번호로 묻는다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

`quick`:
1. `cli.py:main`이 `quick <text>`를 받는다. `text`가 빈 문자열이면 오류 출력 후 종료 코드 1.
2. `QuickAddEvent`가 대상 캘린더를 정한다(`_prompt_for_calendar`: 하나면 그것, 여럿이면 번호 프롬프트).
3. `events.quickAdd(calendarId, text)`를 호출한다. 문장 해석(제목·시각)은 전부 Google 서버가 한다.
4. `--reminder`가 있거나 `--default-reminders`가 없으면 `events.patch`로 알림만 덮어쓴다(요청이 2번 나간다).
5. `--details url`이면 `New event added: <htmlLink>`를 초록색으로 출력한다.

`add`:
1. `--noprompt`가 아니면(기본) `run_add_prompt`가 비어(None) 있는 값을 `get_input`으로 채운다. 비어 있는 값이 하나도 없으면 아무것도 묻지 않는다(R-06).
2. `get_times_from_duration`([input-parsing](input-parsing.md) C-05)이 `when`·`duration`·`end`·`allday`로 시작·끝 ISO 문자열 둘을 만든다. 실패하면 오류 출력 후 같은 예외를 다시 던진다.
3. `AddEvent`가 대상 캘린더를 정한다(**프롬프트가 모두 끝난 뒤** 이 시점에 묻는다).
4. 요청 본문(1.3 표)을 만든다: 종일 여부에 따라 `start`/`end` 모양이 갈리고, 장소·설명·색은 값이 있을 때만 넣고, 참석자는 항상 넣고, 알림은 `_add_reminders` 조건에 따라 넣는다.
5. `events.insert(calendarId, body)`를 `_retry_with_backoff`로 실행한다. `--details url`이면 링크를 출력한다.

### 1.2 범위·통합 지점
- 제공: `quick`, `add` 두 서브커맨드의 전 과정. `add`의 인자 정의, 프롬프트 발동 조건, 본문 구성, 대상 캘린더 프롬프트(`_prompt_for_calendar`), 알림 본문 구성(`_add_reminders`), 색 id 변환.
- 제외: 시각·기간·알림 문자열의 해석 규칙과 `get_input`·검증기 동작([input-parsing](input-parsing.md) R-01~R-21), 캘린더 선택 목록 `self.cals`가 만들어지는 과정과 `_retry_with_backoff`([calendar-selection](calendar-selection.md) R-08·R-09·R-11), 수정·삭제(feature map 행 8), ICS 가져오기(`_add_reminders`가 `import`에서도 쓰이지만 `import`는 범위 밖: `gcal.py:1644`).
- 외부 의존: Google Calendar API v3 `events.quickAdd`, `events.insert`, `events.patch`(인증은 [oauth-auth](oauth-auth.md)). stdin(프롬프트), stdout/stderr(`printer`).
- 소유 상태·부작용: 원격에 일정 1개 생성(`quick`은 조건부로 patch 1회 추가). 로컬 파일·캐시는 바꾸지 않는다. `run_add_prompt`는 `parsed_args`를 직접 바꾼다(`title`, `where`, `when`, `duration`, `description`, `reminders` 리스트에 append).

### 1.3 인터페이스와 데이터 의미

**CLI 옵션**(원문 이름 그대로. 두 서브커맨드는 `--calendar`, `--details`, `--reminder`, `--default-reminders`를 공유한다)

| 옵션 | 서브커맨드 | 타입·기본값 | 의미·제약 |
|---|---|---|---|
| `text` (위치 인자) | quick | string, 필수 | 자연어 한 줄 |
| `--calendar` | quick, add | string, 기본 None | 단일 값(`action=store`). 해석은 calendar-selection·config-resolution |
| `--details` | quick, add | 누적 dict, 기본 `{}` | 여기서는 `url`만 쓴다(`details.get('url')`) |
| `--reminder` | quick, add | 문자열 리스트(append), 기본 `[]` | argparse `type=validreminder`가 형식 검증, 값은 **원문 문자열** 그대로 저장([input-parsing](input-parsing.md) R-13) |
| `--default-reminders` | quick, add | bool, 기본 False | R-14 |
| `--title` | add | string, 기본 None | |
| `--where` | add | string, 기본 None | |
| `--when` | add | string, 기본 None | 시각 문자열 |
| `--duration` | add | **int**, 기본 None | 분(`--allday`면 일). `--end`와 상호 배타 |
| `--end` | add | string, 기본 None | 끝 시각 문자열. `--duration`과 상호 배타(argparse `add_mutually_exclusive_group`: 둘 다 주면 argparse 오류, 종료 코드 2) |
| `--description` | add | string, 기본 None | |
| `--allday` | add | store_true, 기본 False | 종일 일정 |
| `--who` | add | string 리스트(append), 기본 `[]` | 참석자 이메일(검증 없음) |
| `--color` | add | string, 기본 None, dest `event_color` | **argparse에서는 검증하지 않는다**(`choices` 없음). 목록은 help 문구에만 있다 |
| `--noprompt` | add | store_false, dest `prompt`, 기본 True | 주면 `run_add_prompt`를 부르지 않는다 |

**`events.insert` 요청 본문**(`AddEvent`가 만드는 dict. `calendarId`는 URL 쪽 인자이므로 본문이 아니다)

| 본문 필드 | 값 | 조건 |
|---|---|---|
| `summary` | `title` 그대로 | **항상**. `title`이 None이어도 키는 있고 값이 None |
| `start` | 종일: `{'date': start}` / 아니면 `{'dateTime': start, 'timeZone': <대상 캘린더>['timeZone']}` | 항상. 종일 여부는 `AddEvent`가 `self.options['allday']`(= `--allday`)로 정한다 |
| `end` | `start`와 같은 모양, 값은 `end` 인자 | 항상 |
| `location` | `where` | `where`가 truthy일 때만(`''`·None이면 키 없음) |
| `description` | `descr` | `descr`가 truthy일 때만 |
| `colorId` | `get_override_color_id(color)`: 색 이름의 목록 위치+1을 **문자열**로(lavender=`'1'` … tomato=`'11'`) | `color`가 truthy일 때만. 목록에 없으면 `ValueError`(R-12) |
| `attendees` | `[{'email': w} for w in who]` | **항상**(참석자가 없으면 `[]`). `who`는 문자열 리스트여야 하며 문자열 하나를 넘기면 글자마다 하나씩 생긴다(테스트가 `who='anyone'`을 넘김) |
| `reminders` | `{'useDefault': False, 'overrides': [{'minutes': n, 'method': m}, …]}` | `reminders` 리스트가 비어 있지 않거나 `default_reminders`가 거짓일 때(R-14). 아니면 키 없음(= Google 기본 알림) |

`start`/`end` 인자는 `get_times_from_duration`의 반환값(ISO 문자열)이다. 종일이면 `YYYY-MM-DD`, 아니면 로컬 tz 오프셋이 붙은 `YYYY-MM-DDTHH:MM:SS±hh:mm`(`when` 문자열에 tz가 있으면 그 tz)다. 두 값이 어떻게 계산되는지는 [input-parsing](input-parsing.md) R-10.

**`quick` 알림 patch 본문**: `{'reminders': {'useDefault': False, 'overrides': [{'minutes': n, 'method': m}, …]}}`. `calendarId`와 `eventId`(quickAdd 응답의 `id`)는 URL 인자.

**반환**: `QuickAddEvent`·`AddEvent`는 API 응답 dict를 돌려준다(`_retry_with_backoff`가 `None`이면 `None`). `cli.py`는 반환값을 쓰지 않는다.

**프롬프트 출력**(`run_add_prompt`): 시작 안내 `Prompting for unfilled values.\nRun with --noprompt to leave them unfilled without prompting.\n`(`printer.msg`). 프롬프트 문구는 C-01 그대로. 대상 캘린더 목록 출력은 `printer`가 아닌 `print`(stdout).

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `quick`, `text`가 빈 문자열(`''`) | `printer.err_msg('Error: invalid event text\n')` 후 `sys.exit(1)`. API 호출·프롬프트 없음. 공백만 있는 문자열은 통과한다. `QuickAddEvent` 자체도 `not event_text`이면 `GcalcliError('event_text is required for a quickAdd')`를 던지지만 CLI는 앞에서 걸러서 도달하지 않는다. 위치 인자가 없으면 argparse 오류 | 코드 확인 |
| R-02 | `quick` 정상 경로 | 순서: ① `_prompt_for_calendar(self.cals)`로 캘린더 결정 → ② `events().quickAdd(calendarId=calendar['id'], text=event_text)`를 `_retry_with_backoff`로 실행 → ③ R-03 → ④ R-18. 본문에는 `text`만 있고 `sendUpdates` 등 다른 인자는 없다. `--color`·`--who`·`--allday`는 `quick`에 없다 | 코드 확인 |
| R-03 | `quick`의 알림 patch | `reminders`(리스트)가 비어 있지 않거나 `default_reminders`가 거짓이면 `events().patch(calendarId, eventId=new_event['id'], body={'reminders': {useDefault: False, overrides: [...]}})`를 실행하고 **반환값 `new_event`를 patch 응답으로 교체**한다. 그래서 `--reminder`도 `--default-reminders`도 없는 기본 `quick`은 `overrides: []`로 patch해 **알림을 전부 끈다**. `--default-reminders`만 있고 `--reminder`가 없으면 patch하지 않는다(Google 기본 알림). 각 `r`은 `parse_reminder(r)`로 `(n, m)`(분, 방식)이 된다. patch 실패(`HttpError`)는 전파되고 이미 만들어진 일정은 남는다 | 코드 확인 |
| R-04 | `_prompt_for_calendar(cals)` | ① `cals`가 비면 `GcalcliError('No available calendar to use')`. ② `len(cals)==1`이면 그 캘린더를 **권한 확인 없이** 돌려준다(읽기 전용이어도). ③ 둘 이상이면 `self.cals` 중 `accessRole`이 `owner` 또는 `writer`인 것만 모아 `'<번호> <summary>'`를 줄마다 `print`하고(번호는 0부터), `get_input(printer, 'Specify calendar from above: ', STR_TO_INT)`로 정수 문자열을 받아 `list[int(val)]`을 돌려준다. 범위를 벗어나면(`IndexError`) `GcalcliError('Invalid selection from the list above: <val>\n')`. 음수는 파이썬 음수 인덱스로 통과한다(`-1`=마지막). 쓰기 권한 캘린더가 0개면 목록이 비어 어떤 입력이든 위 오류. 프롬프트 번호는 `cals`가 아니라 **필터된 목록** 기준이다 | 코드 확인 |
| R-05 | `add`, `--prompt`(기본)일 때만 | `cli.py`가 `run_add_prompt`를 부른다. `--noprompt`이면 부르지 않고 인자 그대로 다음 단계로 간다. | 코드 확인 |
| R-06 | `run_add_prompt` 시작: 프롬프트를 할지 | 아래 6개 값 중 **하나라도 None이면** 안내문을 출력하고 프롬프트 단계로 간다. 전부 None이 아니면 **아무 출력 없이 즉시 반환**한다. 값: `title`, `where`, `when`, `(duration or end)`, `description`, `(reminders or default_reminders)`. 주의 ① `duration or end`는 `--duration 0`이면 `0 or None`=None이라 프롬프트 단계로 간다(이때 R-07의 길이 프롬프트는 `duration is None`이 거짓이라 건너뛴다). ② 마지막 값은 `[] or False`=`False`, 비어 있지 않은 리스트, `True` 중 하나라 **절대 None이 아니다**. 그래서 다른 값이 모두 채워졌다면 `--reminder`·`--default-reminders` 없이도 알림 프롬프트가 뜨지 않는다. `where=''`·`title=''`처럼 빈 문자열은 None이 아니므로 채워진 것으로 본다 | 코드 확인 |
| R-07 | 프롬프트 단계(R-06 통과 후) | 아래 순서로 각각 **해당 값이 None일 때만** 묻는다(`get_input`, [input-parsing](input-parsing.md) R-18). ① `title`: `Title: `, `STR_NOT_EMPTY`. ② `where`: `Location: `, `STR_ALLOW_EMPTY`. ③ `when`: `When (? for help): `, `PARSABLE_DATE`, `?`이면 `Expected format: <DATE_INPUT_DESCRIPTION>`. ④ `duration is None and end is None`이면: `--allday`면 `Duration (days): ` 아니면 `Duration (human readable): `, 둘 다 `PARSABLE_DURATION`; 결과(**문자열**)를 `duration`에 저장. ⑤ `description`: `Description: `, `STR_ALLOW_EMPTY`. ⑥ R-08. 색(`--color`)·참석자(`--who`)·종일(`--allday`)은 프롬프트가 없다. 프롬프트로 받은 값은 검증기가 입력 문자열을 **그대로** 돌려주므로 `title`·`when`·`duration` 모두 strip되지 않은 원문이다. 종일의 길이 프롬프트도 분 단위 파서(`PARSABLE_DURATION`)로 검증하므로 `2h`는 통과했다가 R-10에서 `float('2h')` 실패로 끝난다 | 코드 확인 |
| R-08 | 알림 프롬프트 | 프롬프트 단계에 들어왔고 `not reminders and not default_reminders`일 때만 루프: `Enter a valid reminder or "." to end: `를 `REMINDER` 검증기로 반복해서 묻는다. `.`이면 종료. 아니면 `parse_reminder`의 `(n, m)`을 `f'{n} {m}'`(분 단위로 환산된 정수, 방식)으로 `parsed_args.reminders`에 append한다(예: `1h` → `'60 popup'`). 빈 입력은 검증기가 거부하므로 알림 0개로 끝내려면 `.`를 입력해야 한다. 이 루프는 R-06의 게이트와 별개라서, 다른 값이 하나라도 비어 프롬프트 단계에 들어오면 `--reminder`가 없는 한 **항상** 뜬다. `--noprompt`이면 뜨지 않는다 | 코드 확인 |
| R-09 | `add`, 시각 계산 | `get_times_from_duration(when, duration=duration, end=end, allday=allday)` 결과를 `(estart, eend)`로 받는다. `ValueError`면 `printer.err_msg(str(exc))` 후 **같은 예외를 re-raise**해 프로세스가 traceback으로 끝난다(`main`의 `except`는 `GcalcliError`만 잡는다. 종료 코드 1은 파이썬 기본). 이 시점에는 API 호출이 없다. 계산 규칙은 [input-parsing](input-parsing.md) R-10 | 코드 확인 |
| R-10 | `--noprompt`로 비어 있는 값이 있을 때 | `when`이 None이면 `get_time_from_str(None)`이 예외를 내 `ValueError('Date and time is invalid: None\n')`(R-09로 종료). `duration`·`end` 둘 다 None이면 시작은 통과하고 종일이 아니면 `Duration time is invalid: None\n`, 종일이면 `Duration time (days) is invalid: None\n`(R-09로 종료). 즉 **`--noprompt`에서는 `--when`과 (`--duration` 또는 `--end`)가 사실상 필수**다. `title`·`where`·`description`이 None이면 오류 없이 진행하고 `title` None은 본문 `summary: None`이 된다(`where`·`description` None은 키 생략, R-11). `--duration 0`은 정수 0이라 R-09를 통과하고(`timedelta(0)` / 종일은 `float(0)`) 시작=끝인 일정을 만든다 | 코드 확인 |
| R-11 | `AddEvent` 본문 구성 순서와 조건 | 1.3 표대로: `_prompt_for_calendar` **먼저**(캘린더가 없거나 선택이 잘못되면 본문을 만들기 전에 `GcalcliError`) → `summary` → `start`·`end`(`self.options['allday']`면 `{'date': ...}`, 아니면 `{'dateTime': ..., 'timeZone': calendar['timeZone']}`) → `location`(truthy) → `description`(truthy) → `colorId`(truthy) → `attendees`(항상) → `_add_reminders`. `timeZone`은 **선택된 캘린더**의 값이고 `dateTime`에는 이미 오프셋이 붙어 있다 | 코드 확인 |
| R-12 | `--color` | `color`가 truthy면 `str(VALID_OVERRIDE_COLORS.index(color) + 1)`. 11개 이름 외(대소문자 포함)는 `list.index`의 `ValueError`가 **`AddEvent` 안에서** 나고 `main`이 잡지 않아 traceback으로 끝난다. 이때 캘린더 프롬프트는 이미 끝났고 `insert`는 호출되지 않는다. 빈 문자열 `--color ''`는 falsy라 색 없이 진행한다. `--color`는 argparse·`run_add_prompt` 어디서도 검증하지 않는다(검증기 `VALID_COLORS`는 `edit`에서만 쓰인다) | 코드 확인(검증기 사용처: `grep -n VALID_COLORS gcalcli/*.py`: 정의 `validators.py`, 사용 `gcal.py:1057`만) |
| R-13 | 종일(`--allday`)의 `start`/`end` | `AddEvent`는 받은 문자열을 `{'date': ...}`에 그대로 넣는다. `--duration N`이면 R-09가 `start.date()`, `(start+N일).date()`를 만들어 **끝 날짜는 배타**(N=1이면 다음 날)다. **`--end`를 함께 주면** `get_times_from_duration`이 날짜로 자르지 않고 시각 포함 ISO를 돌려주므로(input-parsing T-16) `{'date': '2025-03-01T00:00:00+09:00'}`처럼 `date` 필드에 날짜시간 문자열이 들어간다. `--duration`을 받는 종일 길이는 일 단위이고 프롬프트 경로의 소수·문자열(`'1.5'`)도 허용된다(`.date()`로 잘림) | 코드 확인. `--allday --end`의 API 응답은 미확인(U-02) |
| R-14 | 알림 본문 `_add_reminders(event, reminders)` | `if reminders or not self.options['default_reminders']:`이면 `event['reminders'] = {'useDefault': False, 'overrides': []}`를 만들고 `reminders`의 각 `r`에 `parse_reminder(r)`로 `(n, m)`을 얻어 `{'minutes': n, 'method': m}`를 **입력 순서대로** 덧붙인다. 아니면 `reminders` 키를 만들지 않는다. 결과: ① `--reminder` 있음 → 그 목록만(기본 알림 대체), `--default-reminders`가 함께 있어도 무시된다. ② 둘 다 없음 → `overrides: []`(알림 없음). ③ `--default-reminders`만 → 키 생략(캘린더 기본 알림). `--reminder`는 여러 번 줄 수 있고 `append`라 순서대로 누적된다. 중복·개수·분 상한 검사는 없다(Google 쪽 제한은 U-03). `reminders`가 None이고 `default_reminders`가 거짓이면 `for r in None`으로 `TypeError`가 나지만 CLI는 항상 리스트를 넘긴다(argparse 기본 `[]`) | 코드 확인. 부재 주장(상한·중복 검사 없음)은 `gcal.py:425-433`·`utils.py:36-54` 범위 확인 |
| R-15 | 참석자 | `--who`를 여러 번 주면 입력 순서대로 `attendees`가 된다. 이메일 형식 검증·중복 제거·`self` 포함 처리 없음. 없으면 `attendees: []`가 **본문에 항상 포함**된다. `sendUpdates`를 보내지 않으므로 초대 메일 발송 여부는 API 기본에 달려 있다(U-04) | 코드 확인 / 발송은 미확인 |
| R-16 | `insert` 실행 | `events().insert(calendarId=calendar['id'], body=event)`를 `_retry_with_backoff`로 실행한다. 재시도·`HttpError` 전파·**5회 모두 재시도 조건이면 `None` 반환**은 [calendar-selection](calendar-selection.md) R-11을 따른다. 응답이 `None`이면 `AddEvent`는 오류 없이 `None`을 돌려주고(`--details url`이 없을 때) CLI는 종료 코드 0, 일정은 만들어지지 않았다. `quick`은 `None`이면 `new_event['id']`(또는 `htmlLink`)에서 `TypeError`가 난다 | 코드 확인(경로 추적). 실제 발생 가능성은 calendar-selection U-02 |
| R-17 | 오류 전달 | `GcalcliError`(캘린더 없음·선택 오류·`quick` 빈 텍스트 내부 검사)는 `main`이 `printer.err_msg(str(exc))` 후 `sys.exit(1)`. `ValueError`(R-09·R-12), `HttpError`, `EOFError`/`KeyboardInterrupt`(프롬프트), `TypeError`는 잡히지 않고 traceback. argparse 오류(`--duration abc`, `--duration`+`--end`, 형식이 틀린 `--reminder`)는 종료 코드 2 | 코드 확인 / argparse 종료 코드는 표준 동작(추론) |
| R-18 | 결과 출력 | `self.details.get('url')`이 참(`--details url` 또는 `--details all`)이면 `New event added: <new_event['htmlLink']>\n`를 초록색으로 출력한다. 아니면 성공 시 **아무것도 출력하지 않는다**(두 서브커맨드 공통). `quick`은 patch 응답, `add`는 insert 응답의 `htmlLink`를 쓴다 | 코드 확인 |
| R-19 | 프롬프트가 일정 생성 전에 끝나는 순서 | `add`는 모든 `get_input` 프롬프트(R-07·R-08) → 시각 계산(R-09) → 캘린더 프롬프트(R-04) 순이다. 그래서 시각이 잘못돼도 캘린더는 묻지 않고, 캘린더 선택 오류는 앞서 입력한 값을 모두 버린다. `quick`은 캘린더 프롬프트만 있다 | 코드 확인 |

- 불변식: 일정 생성 API(`insert` 또는 `quickAdd`)는 `_prompt_for_calendar`·시각 계산·색 변환이 모두 성공한 뒤에만 호출된다(`add`). `quick`은 `quickAdd`를 먼저 부르고 알림 patch가 그 뒤라 patch만 실패한 부분 성공 상태가 가능하다.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-02, R-03 | `quickAdd`가 자연어를 어떻게 해석하는가(제목·시각·종일 판정·시간대)? 기본 알림이 붙는가? | `quick`의 결과 일정은 서버가 정한다. 재구현은 문자열을 그대로 넘기면 되고 해석 규칙은 필요 없지만, 알림 patch(R-03)가 덮어쓰는 대상이 서버 기본 알림이라는 전제는 미확인 | Google `events.quickAdd` 공식 문서와 실제 호출 |
| U-02 | R-10, R-13 | `summary: null` 본문, 종일 `{'date': '<시각 포함 ISO>'}`, 시작=끝인 종일 일정(`--allday --duration 0`)을 Google이 받아 주는가? | 거부하면 원본은 `HttpError` traceback을 낸다. 재구현이 사전 검사를 둘지, 원본처럼 서버 오류를 그대로 낼지 | 실제 API 호출 또는 공식 `Events` 리소스 문서 |
| U-03 | R-14 | `reminders.overrides`의 개수·분 상한·`sms` 방식 허용 범위와 위반 시 응답 | 원본은 사전 검사가 없다. 재구현이 검사를 넣을 필요가 있는지 | 공식 문서(`reminders.overrides[]`) |
| U-04 | R-15 | `insert`가 `sendUpdates` 없이 참석자 `attendees`를 넣으면 초대 메일이 가는가? | 재구현이 `sendUpdates`를 보낼지, 원본과 같은 기본 동작인지 | 공식 문서의 `sendUpdates` 기본값 |
| U-05 | R-11 | `calendarList` 항목에 `timeZone`이 항상 있는가? 없으면 `calendar['timeZone']`이 `KeyError` | 원본은 `.get` 없이 인덱싱한다 | calendar-selection U-01과 같은 확인 |

- 확인 한계: Google API를 호출하지 않았다. 본문 필드의 수용 여부(U-02~U-04)와 `quickAdd` 해석(U-01)은 클라이언트 쪽 코드가 "그렇게 보낸다"는 사실만 확인했다. 대화형 프롬프트와 stdin 동작은 코드로 읽었고, 원본 `bats` 스냅샷(`can run add`)이 같은 흐름을 보여 준다(T-09). 실행은 하지 않았다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/cli.py:105-152` `run_add_prompt` | 프롬프트 게이트 조건, 프롬프트 순서·문구·검증기, 알림 루프 | R-06~R-08 |
| C-02 | `gcalcli/cli.py:278-307` `main`의 `quick`·`add` 분기 | 호출 순서, `ValueError` 처리 | R-01, R-05, R-09 |
| C-03 | `gcalcli/gcal.py:1408-1426` `_prompt_for_calendar` | 캘린더 선택 프롬프트 | R-04 |
| C-04 | `gcalcli/gcal.py:1428-1465` `QuickAddEvent` | quickAdd 호출, 알림 patch 조건·본문, 링크 출력 | R-02, R-03, R-18 |
| C-05 | `gcalcli/gcal.py:1467-1505` `AddEvent` | 요청 본문 구성 전체 | R-11~R-13, R-15, R-16, R-18 |
| C-06 | `gcalcli/gcal.py:425-433` `_add_reminders` | 알림 본문 조건·구성 | R-14 |
| C-07 | `gcalcli/argparsers.py:272-293` `get_remind_parser`, `585-655` `quick`·`add` 등록 | 옵션 이름·타입·기본값·상호 배타 | 1.3, R-05 |

재사용(이 스펙에서 다시 쓰지 않음): `get_times_from_duration` = [input-parsing](input-parsing.md) C-05, `parse_reminder`·`REMINDER_REGEX` = input-parsing C-01·C-02, `get_input`·`get_override_color_id`·`VALID_OVERRIDE_COLORS` = input-parsing C-06, 검증기 `STR_NOT_EMPTY`·`STR_ALLOW_EMPTY`·`STR_TO_INT`·`PARSABLE_DATE`·`PARSABLE_DURATION`·`REMINDER` = input-parsing C-07, `validreminder` = input-parsing C-08, `_retry_with_backoff` = [calendar-selection](calendar-selection.md) C-03. `get_events()`(`gcal.py:319`)는 인증된 서비스의 `events()` 리소스를 돌려주는 접근자다(인증은 oauth-auth).

### 1.6 수락 사례
출처: 사례별 표기. 대체: Google API 없음. 요청 본문과 호출 순서만 검증하고 서버 응답은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-02, R-03 | 캘린더 1개, `quick "lunch tomorrow"` (`--reminder` 없음, `--default-reminders` 없음) | `quickAdd(text='lunch tomorrow')` 다음 `patch(body={'reminders':{'useDefault':False,'overrides':[]}})` | 구현에서 도출 |
| T-02 | R-03 | 같은 입력 + `--default-reminders` | `quickAdd`만, patch 없음 | 구현에서 도출 |
| T-03 | R-03, R-14 | `quick "x" --reminder "5m sms" --reminder "1h"` | patch 본문 `overrides == [{'minutes':5,'method':'sms'},{'minutes':60,'method':'popup'}]` | 구현에서 도출 (원본 테스트 `test_quick_add`는 `['5m sms']`로 quickAdd 후 patch 호출만 확인) |
| T-04 | R-04 | `self.cals`에 owner·writer·reader 3개, 프롬프트에 `1` | 목록은 owner·writer 둘만 `0 …`, `1 …`로 출력, 선택은 writer. 읽기 전용은 선택지에 없다 | 구현에서 도출 (원본 테스트 `test_add_event_with_cal_prompt`는 2개 캘린더·입력 `0`으로 출력 패턴만 확인) |
| T-05 | R-04 | 캘린더 1개(reader 권한) | 프롬프트 없이 그 캘린더로 진행 | 구현에서 도출 |
| T-06 | R-04 | 캘린더 2개, 프롬프트에 `5` / `x` | `5`: `GcalcliError('Invalid selection from the list above: 5\n')` 종료 코드 1. `x`: `Input here must be a number.`로 다시 묻는다 | 구현에서 도출 |
| T-07 | R-06 | `add --title t --where w --when "tomorrow 3pm" --duration 30 --description d` (알림 인자 없음, `--prompt` 기본) | 안내문·프롬프트 **없음**(알림 항목은 None이 될 수 없다), 알림 `overrides: []` | 구현에서 도출 |
| T-08 | R-06~R-08 | `add --title t --where w --when tomorrow --duration 30` (설명 없음) | 안내문 후 `Description: `만 묻고, 이어서 알림 프롬프트 루프가 뜬다(`.`로 종료하면 `overrides: []`) | 구현에서 도출 |
| T-09 | R-06~R-08, R-19 | stdin `sometitle\n\ntomorrow\n\n\n.`, 인자 없음, 캘린더 0개(원본 bats는 userless 모드) | 프롬프트 순서 `Title: `→`Location: `→`When (? for help): `→`Duration (human readable): `→`Description: `→`Enter a valid reminder or "." to end: ` 후 `No available calendar to use`, 종료 코드 1. 빈 길이 입력은 `timedelta(0)`로 통과한다 | 원본 테스트 열람(`tests/cli/test.bats` "can run add", 스냅샷 `test-04-test_can_run_add.snap`). 실행 안 함 |
| T-10 | R-10 | `add --noprompt --title t --when tomorrow` | `Duration time is invalid: None`(stderr), traceback `ValueError`, API 호출 없음 | 구현에서 도출 |
| T-11 | R-10 | `add --noprompt --when tomorrow --duration 30` (title 없음) | `insert` 본문에 `summary: None`, `location`·`description` 키 없음, `attendees: []`, `reminders.overrides: []` | 구현에서 도출 |
| T-12 | R-13 | `add --allday --when 2025-03-01 --duration 2 --title t` | 본문 `start={'date':'2025-03-01'}`, `end={'date':'2025-03-03'}` | 구현에서 도출 (input-parsing T-14 참조) |
| T-13 | R-11 | `add --when "2025-03-01 15:00" --duration 90` 캘린더 `timeZone='Asia/Seoul'` | `start={'dateTime':'2025-03-01T15:00:00+09:00', 'timeZone':'Asia/Seoul'}`, `end`는 16:30. 오프셋은 실행 머신 로컬 tz 의존 | 구현에서 도출 |
| T-14 | R-12 | `--color banana` / `--color Banana` / `--color ''` | `colorId: '5'` / `ValueError`(insert 없음) / 색 키 없음 | 구현에서 도출 |
| T-15 | R-14 | `--reminder 1d --reminder "10m email"`, `--default-reminders` 포함 | `overrides == [{'minutes':1440,'method':'popup'},{'minutes':10,'method':'email'}]`, `useDefault: False` | 구현에서 도출 |
| T-16 | R-18 | `--details url` + 성공 | stdout에 초록 `New event added: <htmlLink>`. 없으면 출력 없음 | 구현에서 도출 |
| T-17 | R-11 | `AddEvent(who='anyone')`처럼 문자열 | `attendees`가 글자 하나씩 7개 | 원본 테스트 열람(`tests/test_gcalcli.py:99-115`: 본문에 `summary`·`start`·`end`가 있는지만 단언). 글자 분해는 코드에서 도출 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@405639c `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02(`cli.py:278-286`), C-04(`gcal.py:1428-1431`), `argparsers.py:592` | 줄 추적 |
| R-02, R-03 | C-04(`gcal.py:1433-1459`) | 줄 추적. `_retry_with_backoff` 인자는 `HttpRequest`(`.execute()`). "기본 `quick`이 알림을 끈다"는 `default_reminders` 기본 False(`argparsers.py:286-292`)와 조건식에서 도출 |
| R-04 | C-03(`gcal.py:1408-1426`), 원본 테스트 `tests/test_gcalcli.py:118-146`(2개 캘린더, 입력 `0`, 출력 패턴) | 줄 추적. 음수 인덱스·쓰기 권한 0개 경로는 파이썬 규칙에서 도출, 테스트 없음. `self.cals` 생성은 calendar-selection R-08·R-09 |
| R-05, R-06 | C-01(`cli.py:105-123`), C-02(`cli.py:288-290`) | 줄 추적. "reminders 항목은 절대 None이 아니다"는 argparse 기본값 `[]`(`argparsers.py:274-278`)·`False`(`argparsers.py:286-290`)와 `or` 평가에서 도출. 부재 주장(None이 될 경로 없음): 범위 `gcalcli/cli.py`·`argparsers.py`·`config.py`, `grep -n "reminder" gcalcli/config.py`가 매치 없음. 놓칠 가능성: rc 파일(`@경로`)·config.toml이 namespace를 덮어쓰는 경로(`config.py`에 reminders 키가 없다는 것까지만 확인) |
| R-07, R-08 | C-01(`cli.py:124-152`), input-parsing R-18~R-21 | 줄 추적 + 원본 스냅샷으로 문구·순서 일치 확인(T-09) |
| R-09, R-10 | C-02(`cli.py:292-301`), `utils.py:68-93`(input-parsing C-05) | `get_time_from_str(None)`의 `re.match(None)` `TypeError`가 `except Exception`에 잡혀 `ValueError`가 된다는 것은 줄 추적(`utils.py:72-75`)과 파이썬 규칙. 실행은 하지 않음. input-parsing `1.1`의 `--noprompt` 서술(`Duration time is invalid: None`)은 비종일에서만 맞고 종일은 `(days)` 문구다(보정 제안 참조) |
| R-11 | C-05(`gcal.py:1467-1500`) | 줄 추적. 본문 필드 존재는 원본 테스트 `CallMatcher('insert', body_has_fields={'summary','start','end'})`와 일치 |
| R-12 | C-05(`gcal.py:1485-1486`), input-parsing C-06, 사용처 검색 `grep -n VALID_COLORS gcalcli/*.py` | 기준 SHA에서 `gcalcli/*.py` 범위 검색. 놓칠 가능성: 다른 디렉터리(없음, `gcalcli/` 단일 패키지)·동적 참조 |
| R-13 | C-05(`gcal.py:1474-1482`), `utils.py:76-93`, input-parsing T-14·T-16·T-17 | `self.options['allday']`는 `GoogleCalendarInterface(**vars(parsed_args))`(`cli.py`의 `GoogleCalendarInterface(... **vars(parsed_args))` 생성부)로 들어온 `--allday` 값(`gcal.py:80-81`, `options`). API 수용은 미확인(U-02) |
| R-14 | C-06(`gcal.py:425-433`), 호출 `gcal.py:1494`(add), `1443-1450`(quick, 본문 중복 구현), `parse_reminder`(input-parsing C-02) | 줄 추적. `quick`은 `_add_reminders`를 쓰지 않고 같은 로직을 복제했다(본문 모양은 같고 patch 본문은 `{'reminders': ...}`로 한 겹 감싼다). `import`의 `1644`는 범위 밖 |
| R-15 | C-05(`gcal.py:1488`), 원본 테스트 `who='anyone'` | 줄 추적 |
| R-16 | C-05(`gcal.py:1495-1497`), calendar-selection R-11 | 줄 추적. `None` 경로는 `_retry_with_backoff`(`gcal.py:135-149`)의 끝 `return None`에서 도출 |
| R-17 | C-02, `cli.py:393-395` `except GcalcliError`(`main` 끝), `exceptions.py` | 줄 추적. 종료 코드 2는 argparse 표준(`tests/cli/test.bats` "can run"이 서브커맨드 누락 시 2를 단언하는 것과 같은 경로) |
| R-18 | C-04(`gcal.py:1461-1463`), C-05(`gcal.py:1499-1501`), `argparsers.py:96-107,129-138` `DetailsAction` | 줄 추적. `details.py`의 `DETAILS`에 `url` 포함은 `Url` 핸들러(`details.py` `HANDLERS`)에서 확인 |
| R-19 | C-02(`cli.py:288-307`), C-05(`gcal.py:1469`) | 줄 추적 |
| T-01~T-08, T-10~T-16 | 해당 R-ID의 근거 | 구현에서 도출. 실행하지 않음 |
| T-09 | `tests/cli/test.bats:34-42`, `tests/cli/__snapshot__/test-04-test_can_run_add.snap` | 원본 테스트 열람. 스냅샷 첫 줄 `1`은 종료 코드, 마지막은 `No available calendar to use` |

문서와 구현의 차이: `quick` 서브커맨드 설명은 "A single --calendar must be specified"(`argparsers.py:589-590`)지만 코드는 캘린더가 여럿이면 번호로 묻는다(R-04). `add`의 `--allday` help는 "The time part of the --when will be ignored"인데 `--end`를 함께 주면 시각이 무시되지 않는다(R-13). `--duration` help는 "(or days if --allday)"인데 프롬프트 경로는 분 단위 파서로 검증한다(R-07).

### 2.2 코드 읽는 순서
`cli.py:278-307`(분기) → `run_add_prompt`(`cli.py:105-152`) → `utils.get_times_from_duration`(`utils.py:68-93`) → `gcal.AddEvent`(`gcal.py:1467-1505`) → `_prompt_for_calendar`(`gcal.py:1408-1426`) → `_add_reminders`(`gcal.py:425-433`) → `QuickAddEvent`(`gcal.py:1428-1465`). 옵션 정의는 `argparsers.py:585-655`.

### 2.3 비교·재사용 출처
없음.

### 2.4 검토 기록
- **작성자 자체 점검**: R-06·R-10·R-13의 분기를 코드 줄과 대조.
- **메인 세션 점검(2026-11-18)**: `check.py` 통과. R-03·R-14(`QuickAddEvent`가 알림 조건 `reminders or not default_reminders`를 복제한 `gcal.py:1443-1450`), R-06(`reminders or default_reminders`가 `[] or False`라 `is None`이 되지 않음), R-10의 `Duration time (days) is invalid` 분기(`utils.py:79-83`)를 원본 줄과 대조해 일치. 독립 검토는 의존하는 스펙이 없어 돌리지 않았다.
- **status를 `draft`로 유지하는 이유**: U-01~U-05가 열려 있고(Google API 호출 필요) 선행 스펙 calendar-selection·input-parsing도 `draft`다.
