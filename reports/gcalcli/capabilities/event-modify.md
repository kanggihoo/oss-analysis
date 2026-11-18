---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/gcal.py
  - gcalcli/cli.py
  - gcalcli/argparsers.py
  - gcalcli/validators.py
  - gcalcli/utils.py
  - gcalcli/config.py
  - gcalcli/printer.py
  - tests/test_gcalcli.py
depends:
  - event-query.md
  - input-parsing.md
  - calendar-selection.md
status: draft
---

# 일정 수정·삭제 (edit / delete)

> 검색어(와 선택적 시작·끝 시각)로 [event-query](event-query.md)의 `_search_for_events`가 찾은 일정을 하나씩 보여 주며 `work` 콜백으로 대화형 처리한다: `delete`는 `y/n/q` 확인(`--iamaexpert`면 확인 없이) 뒤 `events.delete`, `edit`는 메뉴 루프로 이벤트 dict의 제목·장소·시각·길이·알림·색·설명을 메모리에서 고친 뒤 `s`(저장)에서만 `events.patch`를 부른다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `cli.main`이 `delete`/`edit` 서브커맨드를 받아 `gcal.ModifyEvents(work, text[0], start, end[, expert])`를 부른다. `work`는 `delete`면 `_delete_event`, `edit`면 `_edit_event`다(R-01, R-02).
2. `ModifyEvents`가 검색어가 비면 `GcalcliError`로 거부하고(R-03), 아니면 `_search_for_events`로 목록을 얻어 `self.expert`를 저장한 뒤 `_iterate_events(year_date=True, work=work)`에 넘긴다(R-03, R-04).
3. `_iterate_events`는 [event-query R-10](event-query.md)대로 필터를 적용하고, 통과한 이벤트마다 일정을 출력(렌더링은 이 스펙 밖)한 **다음** `work(event)`를 부른다. 목록이 비면 `No Events Found...`만 내고 `work`는 한 번도 안 불린다(R-04).
4. `delete`: `--iamaexpert`면 바로 삭제, 아니면 `Delete? [N]o [y]es [q]uit: `를 묻는다. `y`면 삭제하고 `Deleted!`, 빈 입력·`n`이면 건너뛰어 다음 이벤트로, `q`면 프로세스 종료(0), 그 밖은 오류 종료(1)(R-05, R-06).
5. `edit`: `Edit?` 메뉴를 반복해서 묻고, 항목 하나를 고칠 때마다 이벤트 dict만 바꾼 뒤 이벤트를 다시 출력한다(R-07, R-10~R-17). `s`가 `patch` 본문(허용 키만)을 만들어 API에 보내고 `Saved!` 후 다음 이벤트로(R-08), `n`/빈 입력은 변경을 버리고 다음 이벤트로, `q`는 프로세스 종료(R-07, R-09).
6. 모든 이벤트를 지나면 `ModifyEvents`가 통과 수를 돌려주고 `cli`는 그 값을 버린다(R-04). API 실패(`HttpError` 등)는 잡히지 않고 프로세스가 traceback으로 끝난다(R-06, R-08).

### 1.2 범위·통합 지점 [필수]
- 제공: `ModifyEvents`, `_delete_event`·`delete`, `_edit_event`(메뉴 루프 전체), `_SetEventStartEnd`, `cli`·`argparsers`의 `edit`·`delete` 배선과 옵션, `patch`/`delete` API 호출과 실패 전달.
- 제외: 일정 조회·필터·내부 이벤트 표현의 생성([event-query](event-query.md)), 일정 출력 `_PrintEvent`의 렌더링 규칙(행 5. 이 스펙은 "언제 불리는가"만 쓴다), TSV 일괄 수정 `agendaupdate`(행 9), 일정 추가(`event-create.md`), 시각·길이 문자열 파싱과 검증기 본문([input-parsing](input-parsing.md)).
- 외부 의존·선행 계약:
  - 입력 이벤트: [event-query 1.3](event-query.md)의 내부 이벤트 표현(`s`·`e`·`gcalcli_cal`, API 필드). 이 스펙은 그 불변식이 `_SetEventStartEnd` 이후 **깨진다**는 것을 R-14~R-16에서 다룬다.
  - [input-parsing](input-parsing.md): `get_times_from_duration`(R-10), `get_time_from_str`·`get_timedelta_from_str`, `parse_reminder`(R-11), `get_input`(R-18), 검증기 `PARSABLE_DATE`·`PARSABLE_DURATION`·`STR_NOT_EMPTY`·`STR_ALLOW_EMPTY`·`REMINDER`·`VALID_COLORS`(R-19~R-21).
  - [calendar-selection R-11](calendar-selection.md): `_retry_with_backoff(request)`는 성공 시 응답 dict, 재시도 소진 시 `None`, 그 밖의 `HttpError`는 재전파. 이 스펙의 두 API 호출이 모두 이것을 거친다.
  - Google Calendar API `events.patch`·`events.delete`(외부. 서버 동작은 확인 한계).
  - stdin(`input()`), stdout/stderr(`printer`).
- 소유 상태·부작용: ① 이벤트 dict(`ModifyEvents`가 받은 목록의 원소)를 **제자리에서 변형**한다(`summary`·`location`·`description`·`colorId`·`reminders`·`start`·`end`·`s`). 목록은 다시 조회하지 않는다. ② `self.expert`(`ModifyEvents`가 대입하는 인스턴스 속성. `__init__`에는 없다). ③ `self.options['override_color']`를 `c`에서 `True`로 바꾼다(프로세스 수명 동안 이후 모든 이벤트의 출력 색에 영향). ④ 원격 캘린더의 이벤트(patch/delete). ⑤ stdout/stderr 출력, 프로세스 종료.

### 1.3 인터페이스와 데이터 의미 [필수]
**CLI (외부 계약)**

| 서브커맨드 | 위치 인자 | 옵션 | 비고 |
|---|---|---|---|
| `edit` | `text`(필수, `nargs=1`) `[start] [end]`(`get_time_from_str` 타입) | `--calendar`(복수 허용, calendars_parser), `--details`, 출력 옵션(`--tsv`·`--json`·`--nostarted`·`--nodeclined`·`--override-color`·색·`--width`·`--military` 등) | `--iamaexpert` **없음**. `--allday`·`--default-reminders` **없음**(R-02) |
| `delete` | 같음 | `--calendar`, 출력 옵션, **`--iamaexpert`**(`store_true`, 기본 False, help `Probably not`) | `--details` 없음(`self.details`는 `{}`) |

- `--tsv`·`--json`은 두 서브커맨드가 받아도 `ModifyEvents` 경로는 `options['tsv']`·`['json']`를 읽지 않는다(R-04). 
- `start`·`end`를 생략하면 `None`이 그대로 `_search_for_events`로 가 시간 범위 없이 검색한다(R-03).

**함수**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `ModifyEvents(work, search_text, start=None, end=None, expert=False)` | callable, str, `datetime\|None`×2, bool → int(통과 수) | R-03, R-04 |
| `_delete_event(event)` | Event → None | R-05, R-06. `self.expert` 필요(`ModifyEvents`가 설정) |
| `delete(cal_id, event_id)` | str, str → None | `events().delete(calendarId, eventId)`를 `_retry_with_backoff`로 실행. 반환값은 버린다 |
| `_edit_event(event)` | Event → None | R-07~R-17 |
| `_SetEventStartEnd(start, end, event)` | ISO 문자열 둘, Event → 같은 Event 객체 | R-14~R-16 |

**편집 메뉴 입력 (프롬프트 원문: `Edit?\n[N]o [s]ave [q]uit [t]itle [l]ocation [w]hen len[g]th [r]eminder [c]olor [d]escr: `, magenta)**

| 입력(대소문자 무시, **strip 안 함**) | 동작 | 상세 |
|---|---|---|
| (빈 줄), `n` | 이 이벤트 건너뛰기(변경 버림) | R-07 |
| `s` | 저장(patch) | R-08 |
| `q` | 프로세스 종료 | R-09 |
| `t` / `l` / `d` | 제목 / 장소 / 설명 | R-10 |
| `c` | 색 | R-11 |
| `r` | 알림 | R-12 |
| `w` | 시작 시각(길이 유지) | R-13 |
| `g` | 길이(시작 유지) | R-17 |
| 그 밖 | `Error: invalid input\n` 후 종료 코드 1 | R-07 |

메뉴에는 **참석자·종일 토글·`--allday` 같은 항목이 없다**(R-19).

**`patch` 본문 키(R-08)**: `summary`, `location`, `start`, `end`, `reminders`, `description`, `colorId` 중 이벤트 dict에 **존재하는** 것만. `gcalcli_cal`·`s`·`e`·`attendees` 등은 보내지 않는다.

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `cli.main`의 `delete` 분기 | `gcal.ModifyEvents(gcal._delete_event, text[0], start=start, end=end, expert=iamaexpert)`. 반환값은 버린다(종료 코드는 0, 예외·`sys.exit`가 없을 때) | 코드 확인 |
| R-02 | `edit`·`delete` 서브커맨드의 옵션 구성 | `edit`은 `parents=[calendars, details, output, search]`, `delete`는 `[calendars, output, search]` + `--iamaexpert`. `edit` 분기는 `expert`를 넘기지 않아 기본 `False`. `allday`·`default_reminders` 키는 `add`·`quick`·`import`의 파서(`--allday`, `remind_parser`)에만 정의돼 **`edit`·`delete`의 `self.options`에 없다**(config 쪽 네임스페이스 필드도 아님). 따라서 `self.options.get('allday')`는 항상 `None`, `self.options['default_reminders']`는 `KeyError`(R-12). 실행: `vars(parse_args(['edit','x']))`에 두 키가 없음. `--allday`를 `edit`에 주면 argparse 재파싱(`handle_unparsed`)이 실패해 사용법 출력 + 종료 1(추론: 전역 옵션만 재파싱하므로) | 코드 확인 + 실행 확인(R-02 키 부재) / 추론(`--allday` 거부 경로) |
| R-03 | `ModifyEvents` 시작 | 1) `search_text`가 거짓(빈 문자열·`None`)이면 `GcalcliError('The empty string would get *ALL* events')`를 **API 호출 전**에 던진다. `cli.main`이 `GcalcliError`를 잡아 stderr에 출력하고 종료 코드 1(event-query R-13·R-16과 같은 경로). 공백만 있는 문자열(`' '`)은 **거짓이 아니므로 통과**해 `q=' '`로 검색한다. 2) `event_list = self._search_for_events(start, end, search_text)`(`start`·`end`는 기본값 채움 없이 그대로 `None` 가능). 3) `self.expert = expert`(검색 **후**에 대입). 4) `return self._iterate_events(self.now, event_list, year_date=True, work=work)` | 코드 확인 |
| R-04 | `_iterate_events` 경유의 의미 | [event-query R-10](event-query.md)을 따른다. 이 스펙에 관련된 점: ① 목록이 비면 `\nNo Events Found...\n`(노랑)을 내고 0을 반환하며 `work`는 불리지 않는다(종료 코드 0). ② 목록이 있으면 이벤트마다 `--nostarted`(`s < self.now`)·`--nodeclined` 필터 → 통과 시 `selected += 1` → 머리글(`year_date=True`라 매번 `\n%Y-%m-%d`) 출력 → `_PrintEvent` → **그 뒤** `work(event)`. 즉 사용자는 일정을 본 뒤에 프롬프트를 받는다. ③ 필터로 건너뛴 이벤트에는 `work`가 불리지 않는다. ④ 목록은 한 번 만든 스냅샷이다: 삭제·수정 결과로 재조회하지 않고, 같은 일정이 여러 캘린더에 있으면 캘린더 수만큼 별개 이벤트로 차례로 나온다(각각 자기 `gcalcli_cal.id`로 처리됨). ⑤ `work`가 던진 예외·`sys.exit`는 반복을 끝내고 전파된다(남은 이벤트는 처리되지 않는다). `ModifyEvents`는 `tsv`·`json`을 읽지 않으므로 그 옵션을 줘도 일반 출력이다 | 코드 확인 |
| R-05 | `_delete_event(event)` 확인 | `cal_id = event['gcalcli_cal']['id']`, `event_id = event['id']`. ① `self.expert` 참: 프롬프트 없이 `delete` 호출 후 `Deleted!\n`(빨강) 출력, 반환. ② 아니면 `Delete? [N]o [y]es [q]uit: `(magenta)를 내고 `input()` 한 줄(strip 안 함, 대소문자 무시): 빈 줄·`n` → 아무것도 안 하고 반환(다음 이벤트). `y` → `delete` 호출, `Deleted!\n`. `q` → `\n`을 stdout에 쓰고 `sys.exit(0)`(남은 이벤트 처리 안 함, 이미 삭제한 것은 유지). 그 밖(`' y'`, `yes`, `x` 포함) → stderr에 `Error: invalid input\n`, stdout에 `\n`, `sys.exit(1)`. 재질문 없음. 실행으로 `y`/`n`/빈 줄/`q`/`z`/expert 확인 | 코드 확인 + 실행 확인(스텁 API) |
| R-06 | `delete` API 호출과 실패 | `self.get_events().delete(calendarId=cal_id, eventId=event_id)`를 `_retry_with_backoff`로 실행([calendar-selection R-11](calendar-selection.md)). `events.list(singleEvents=True)`로 전개된 이벤트라 `event['id']`는 **인스턴스 id**일 수 있고(반복 일정이면 그 인스턴스만 대상인지는 API 소관, 미확인 U-04), 이 호출은 `id`만 쓴다. `HttpError`(재시도 대상 아님)는 그대로 전파돼 traceback으로 프로세스가 끝나고 `Deleted!`는 출력되지 않는다. 재시도가 소진돼 `None`이 반환돼도 반환값을 검사하지 않으므로 **`Deleted!`가 출력된다**(조용한 실패; 소진 조건은 calendar-selection R-11: `code == '403'` 문자열 비교 + `rateLimitExceeded`류 reason). 삭제 후 이벤트 dict는 목록에 남아 있다 | 코드 확인 / 추론(API 반복 일정 의미) |
| R-07 | `_edit_event` 메뉴 루프와 분기 순서 | `while True`로 메뉴 프롬프트→`val = input()`(strip 안 함)→`val.lower()`로 아래 **순서대로** 판정: ① 빈 줄 또는 `n` → `return`(수정 내용은 이 이벤트 dict에만 있고 API에 가지 않으며 버려진다; 다음 이벤트로). ② `c` ③ `s` ④ `not val or q`(빈 줄은 ①에서 이미 처리돼 **`q`만 도달**) ⑤ `t` ⑥ `l` ⑦ `w` ⑧ `g` ⑨ `r` ⑩ `d` ⑪ 그 밖 → stderr `Error: invalid input\n`, stdout `\n`, `sys.exit(1)`(그때까지의 수정은 저장되지 않고 이후 이벤트도 처리되지 않는다). ⑪을 제외한 `c`·`t`·`l`·`w`·`g`·`r`·`d` 분기가 끝나면(그 분기가 `return`·종료·예외로 빠지지 않았다면) 루프 끝에서 `_PrintEvent(event, event['s'].strftime('\n%Y-%m-%d'))`로 현재 상태를 다시 출력하고 메뉴로 돌아간다. 즉 한 이벤트에 대해 `s`·`n`·`q`·오류 중 하나가 나올 때까지 여러 항목을 고칠 수 있다 | 코드 확인 + 실행 확인 |
| R-08 | `s`(저장) | `mod_event = {k: event[k] for k in ['summary','location','start','end','reminders','description','colorId'] if k in event}`(이 순서로 존재하는 것만). `self._retry_with_backoff(self.get_events().patch(calendarId=event['gcalcli_cal']['id'], eventId=event['id'], body=mod_event))` 후 `Saved!\n`(빨강) 출력, `return`(다음 이벤트). 아무것도 안 고치고 `s`를 눌러도 patch가 간다(변경 감지 없음). 변경하지 않은 `start`·`end`도 API에서 받은 그대로 본문에 들어간다. 실패 처리는 R-06과 같다: `HttpError` 전파(`Saved!` 없음), 재시도 소진 `None`이어도 `Saved!` 출력. 서버가 본문의 `null` 필드(R-14의 `date: None`)나 `end < start`를 어떻게 처리하는지는 미확인(U-01) | 코드 확인 + 실행 확인(스텁 본문) / 미확인(서버) |
| R-09 | `q`(편집) | `sys.stdout.write('\n')` 후 `sys.exit(0)`. 현재 이벤트의 미저장 수정은 버려지고 남은 이벤트는 처리되지 않는다. 이미 저장·삭제된 것은 유지 | 코드 확인 + 실행 확인 |
| R-10 | `t`·`l`·`d` | `t`: `get_input('Title: ', STR_NOT_EMPTY)`(빈 문자열 거부·재질문, 공백만은 통과) → `val.strip()`이 비어 있지 않을 때만 `event['summary'] = val.strip()`. `l`: `Location: `, `STR_ALLOW_EMPTY` → strip 후 비어 있으면 **변경 없음**. `d`: `Description: `, `STR_ALLOW_EMPTY`, 같은 규칙으로 `event['description']`. 따라서 장소·설명을 **지우는 방법이 없다**(빈 입력은 no-op) | 코드 확인 |
| R-11 | `c`(색) | `get_input('Color: ', VALID_COLORS)`: 허용값은 소문자 정확 일치의 11개(C-06) 또는 빈 문자열, 그 밖은 `Expected colors are: ...` 오류 후 재질문. 결과가 비어 있지 않으면 `self.options['override_color'] = True`(이후 **모든** 이벤트의 출력에 override 색이 적용됨; 이 인스턴스 수명 동안 유지)와 `event['colorId'] = str(색 목록 인덱스 + 1)`. 빈 입력은 no-op | 코드 확인 + 실행 확인(`sage`→`'2'`) |
| R-12 | `r`(알림) | `Enter a valid reminder or '.' toend: `(원문 문자열에 공백 없이 `to` `end`가 붙음)을 `REMINDER` 검증기로 `.`가 나올 때까지 반복해 `rem`(원문 문자열 목록, 빈 줄은 검증기가 거부)에 모은다. 그 뒤 `if rem or not self.options['default_reminders']:` — **`rem`이 비어 있으면(`.`만 입력) `self.options['default_reminders']`를 읽는데 `edit`의 옵션에 이 키가 없어 `KeyError`**(R-02)로 traceback 종료(수정 전체 버려짐; 실행 확인). `rem`이 비어 있지 않으면 단락 평가로 키를 읽지 않고 `event['reminders'] = {'useDefault': False, 'overrides': [{'minutes': n, 'method': m}, ...]}`(각 `r`을 `parse_reminder`; [input-parsing R-11](input-parsing.md))로 **통째 교체**한다. `useDefault: True` 분기는 CLI에서 도달 불가(`default_reminders`가 참일 수 없음) | 코드 확인 + 실행 확인 |
| R-13 | `w`(시각) | 1) `get_input('When: ', PARSABLE_DATE).strip()`(검증은 원문, 결과만 strip). 비어 있으면(검증기가 대개 막으므로 공백만 입력한 경우 정도) 아무것도 안 한다. 2) `td = event['e'] - event['s']`, `length = td.days*1440 + td.seconds/60`(**분, float**). 3) `all_day = self.options.get('allday')`(CLI에서는 항상 `None`, R-02). 4) `new_start, new_end = get_times_from_duration(val, duration=length, allday=all_day)`: 비종일이므로 `start = get_time_from_str(val)`(**날짜 없는 입력은 "오늘"**, 시각 없는 입력은 00:00. input-parsing R-01), `end = start + timedelta(minutes=length)`, 둘 다 `isoformat()`(오프셋 포함). 이 호출의 `ValueError`는 `err_msg(str(exc))` 후 **`sys.exit(1)`**(재질문 없음). 5) `event = self._SetEventStartEnd(new_start, new_end, event)`. 길이는 **`s`·`e` 값**으로 계산하므로 R-15의 stale `e`에 영향을 받는다. **종일 이벤트(`start.date`)**: `s`/`e`는 현지 자정이라 `length`가 `일수*1440`분 → 시각 `val`에서 시작하는 **시각 지정(timed) 일정으로 바뀐다**(`date`→`None`, `timeZone`은 캘린더 tz, R-14). 종일을 유지하는 경로는 없다 | 코드 확인 + 실행 확인(종일 이벤트 `w` → `2024-05-02T10:00`~`2024-05-03T10:00`) |
| R-14 | `_SetEventStartEnd(start, end, event)` 본문 | ① `event['s'] = parse(start)`(`dateutil.parser.parse`. `start`가 오프셋을 가진 ISO면 **tzoffset tz-aware**, 날짜만(`YYYY-MM-DD`)이면 **naive**. event-query가 보장하던 `tzlocal()`이 아니다). ② `event['e'] - parse(end)` — **대입이 아니라 뺄셈 식문장**이라 결과가 버려지고 `event['e']`는 **갱신되지 않는다**(R-15). ③ `self.options.get('allday')`가 참이면 `event['start'] = {'date': start, 'dateTime': None, 'timeZone': None}`, `event['end']`도 같은 꼴(R-16). ④ 아니면 `event['start'] = {'date': None, 'dateTime': start, 'timeZone': event['gcalcli_cal']['timeZone']}`, `event['end'] = {'date': None, 'dateTime': end, 'timeZone': 같은 캘린더 tz}`. `timeZone`은 **이벤트 원래 tz가 아니라 캘린더 tz**다. ⑤ 같은 `event` 객체를 반환한다(호출자가 `event = ...`로 다시 대입하지만 동일 객체). `patch` 본문(R-08)은 `s`·`e`가 아니라 `start`·`end`에서 만들어지므로 **첫 수정의 API 본문은 올바르다** | 코드 확인 + 실행 확인 |
| R-15 | stale `e`: `w`·`g` 성공 뒤 `event['e']`의 영향 | `event['e']`는 편집 전 값 그대로이고 `event['s']`만 새 시작이다. 이후 ① **다음 `w`의 `length = e_old - s_new`**: 길이가 맞지 않다. 실행(원래 10:00~11:00, 오프셋 +09:00): `w 14:00` → 본문 end 15:00(정상) → 이어서 `w 16:00`이면 `length = 11:00-14:00 = -180분` → 본문 `start 16:00`, **`end 13:00`**(시작보다 이르다) → 이어서 `w 18:00`이면 `-300분` → `end 13:00`. `s`로 저장하면 이 본문이 그대로 API로 간다(수락 여부 U-01). ② `g`로 끝만 바꾼 뒤 `w`: 새 길이가 아니라 `e_old - s_new`를 쓴다(예: `g 2h` 후 `w 14:00` → end 15:00이지 16:00이 아니다; 실행 확인). ③ 편집 뒤 `_PrintEvent`(R-07 말미)가 stale `e`를 쓴다(`--details end`의 종료 시각, `happening_now`, `is_all_day` 판정 모두 `s`/`e`). ④ `g`는 `s`·`e`를 쓰지 않고 `event['start']['dateTime']`(갱신된 문자열)을 쓰므로 영향이 없다(R-17). ⑤ tz: 비종일 경로에서 새 `s`는 tzoffset-aware, stale `e`는 tzlocal-aware라 뺄셈 자체는 가능하다(둘 다 aware). **naive가 되는 것은 종일 경로뿐**이며 거기서는 R-16처럼 `TypeError`가 난다 | 코드 확인 + 실행 확인 |
| R-16 | 종일 경로(`options['allday']` 참) | CLI의 `edit`·`delete`에서는 **도달 불가**(R-02). `GoogleCalendarInterface`를 직접 `allday=True` 옵션으로 만들어 쓰는 호출자만 해당. 그 경우 ① `w`: `get_times_from_duration(..., duration=length(**분**), allday=True)`는 `duration`을 **일**로 읽어([input-parsing R-10](input-parsing.md)) `length` 분 수를 일수로 더한다(1일 종일 이벤트 → `length=1440` → 시작+1440일: 실행으로 `('2024-05-02', '2028-04-11')`)하고 날짜(`YYYY-MM-DD`)만 반환. ② 이어서 `_SetEventStartEnd`: `event['s'] = parse('2024-05-02')`가 **naive**가 되고, 다음 줄 `event['e'] - parse(end)`가 **aware(`e`) − naive**라 `TypeError: can't subtract offset-naive and offset-aware datetimes`로 끝난다(실행 확인). `s`는 이미 naive로 덮인 뒤라 이벤트 dict가 깨진 상태로 예외가 전파되고(`ValueError`만 잡는 `w`의 `except`는 이 호출을 감싸지 않음) `date` 분기(1028-1033행)는 성공한 적이 없다. 즉 종일 분기는 `e`가 aware인 한(event-query 1.3) 사실상 **완주 불가능한 코드**다 | 코드 확인 + 실행 확인 |
| R-17 | `g`(길이) | 1) `get_input('Length (mins or human readable): ', PARSABLE_DURATION)`. 이 검증기는 **빈 문자열을 통과**시킨다(`get_timedelta_from_str('')` = `timedelta(0)`, input-parsing R-08). 2) `if val: all_day = self.options.get('allday')` — `all_day`는 **`if val`일 때만 대입**된다. 3) `try:` 안에서 `get_times_from_duration(event['start']['dateTime'], duration=val, allday=all_day)` → `_SetEventStartEnd(new_start, new_end, event)`. `except ValueError`는 `err_msg`만 내고 **루프를 계속**한다(`w`의 `sys.exit(1)`과 다르다). 사례: (a) `val`이 비고 이 `_edit_event` 호출에서 `all_day`가 **아직 한 번도 대입되지 않았으면** `allday=all_day`를 평가할 때 `UnboundLocalError`(실행 확인; `ValueError`가 아니라 잡히지 않아 traceback 종료). (b) `val`이 비고 `all_day`가 이전 `w`(비공백 입력) 또는 이전 비어 있지 않은 `g`에서 대입돼 있으면 `duration=''` → 길이 0 → **`end == start`인 0길이 일정**이 된다(실행 확인). (c) `val`이 비어 있지 않으면 `end = start + 파싱된 기간`(`start`는 현재 `start.dateTime` 문자열을 다시 파싱해 isoformat). (d) 이벤트가 **API 종일 이벤트**(`start`에 `date`만 있고 `dateTime` 없음)이면 `event['start']['dateTime']`이 `KeyError`(실행 확인: 스텁 이벤트 `{'start': {'date': ...}}`; 실제 API가 종일 이벤트에 `date`만 주는 것은 event-query R-04가 읽는 형태이며 외부 사실은 미확인) → traceback 종료. 이미 `w`로 `dateTime`이 생긴 뒤에는 동작한다 | 코드 확인 + 실행 확인 |
| R-18 | 종일 일정에 대한 `edit` 종합 | 종일 이벤트(`start.date`/`end.date`)에서: `t`·`l`·`d`·`c`·`r`은 동작하고 `s`는 변경 안 한 `start`·`end`(`{'date': ...}` 그대로)와 함께 patch한다. `w`는 시각 지정 일정으로 **변환**(R-13). `g`는 `KeyError`(R-17(d)). 종일을 종일로 유지하며 날짜나 길이를 바꾸는 경로는 CLI에 없다 | 코드 확인 + 실행 확인 |
| R-19 | 메뉴 범위 | 편집 가능 항목은 `t·l·w·g·r·c·d`뿐이다. **참석자(`attendees`)를 고치는 항목은 없고 patch 키 목록에도 없다**(요청문의 "참석자"는 원본에 없음). 검색: `grep -n "attendees" gcalcli/gcal.py`에서 `_edit_event`(1044-1160행)·`_SetEventStartEnd` 안에 없음(`_DeclinedEvent`·출력부에만 있음). 놓칠 가능성: 동적 키 접근 | 코드 확인(부재: 위 검색 범위) |
| R-20 | 원본 테스트 | `tests/test_gcalcli.py:281-284 test_modify_event`는 `ModifyEvents(gcal._edit_event, ...)`가 빈 결과에서 `0`을 반환하는지만 본다. 대화 분기·삭제·patch는 테스트가 없다(`grep -rn "_edit_event\|_delete_event\|ModifyEvents" tests` 범위 `tests/`) | 코드 확인(검색) |

- 불변식: ① patch/delete API는 사용자 입력 `s`·`y`(또는 expert)에서만 호출된다. 메뉴의 다른 항목은 메모리의 dict만 바꾼다(R-07, R-08). ② 한 이벤트 처리가 끝나는 경우는 `return`(건너뜀·저장·삭제 완료·`n`), `sys.exit`(`q`·잘못된 입력·`w`의 시각 오류), 예외뿐이다. 프로세스를 끝내는 경우 남은 이벤트는 처리되지 않는다. ③ **종료 코드**: 정상 완료·`q`·빈 결과는 0, 잘못된 메뉴/확인 입력·빈 검색어(`GcalcliError`)·`w` 시각 오류·SIGINT(`cli.py:450-455`, `Signal caught, bye!`)는 1, 그 밖의 예외(`KeyError`·`UnboundLocalError`·`HttpError`·`EOFError`)는 Python 기본(traceback, 1). 전제: 위 R-ID. ④ `s`·`e`는 `_SetEventStartEnd` 호출 뒤 event-query 1.3의 불변식(tz-aware, `e`가 편집된 끝)을 만족하지 않는다(R-14~R-16).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-08, R-15 | 서버가 `start`·`end`의 `date: null`·`timeZone`이 캘린더 tz인 본문, 그리고 `end < start`(R-15의 두 번째 `w`)를 어떻게 처리하는가(수락·거부·보정). 거부되면 어떤 `HttpError`가 나는가 | 재구현이 같은 본문을 보내도 서버 응답에 따라 사용자 경험이 달라진다. 거부 시 R-06처럼 traceback으로 끝난다는 서술이 맞는지 | Calendar API `events.patch` 문서(`null` 필드 삭제 의미, 시각 검증)를 읽거나 실제 계정으로 patch 실행. 이 환경은 API 호출 불가 |
| U-02 | R-06, R-08 | `HttpError`의 `content`가 JSON이 아니거나 `error['errors']`가 없을 때(`_retry_with_backoff`의 `json.loads`/인덱싱 실패)는 어떻게 되는가 | 오류 메시지 형태. 이 스펙은 "전파"로만 쓴다 | calendar-selection R-11의 U-ID와 같은 확인 필요. 실제 오류 응답 샘플 |
| U-03 | R-04, R-06 | 같은 이벤트가 여러 선택 캘린더에 있을 때(초대 사본 등) 한쪽 삭제가 다른 쪽에 영향을 주는가 | 삭제 반복 시 두 번째에서 404가 나는지 | 실제 계정 확인(외부 동작) |
| U-04 | R-06, R-08 | `singleEvents=True`로 전개된 반복 일정의 인스턴스 id에 `delete`/`patch`하면 그 인스턴스만 바뀌는가 | "이 일정만" vs "전체"의 의미 | Calendar API 문서(Instances·recurring events) 또는 실제 확인 |

- 확인 한계: Google Calendar API를 호출할 수 없어 `patch`/`delete`의 서버 응답은 확인하지 않았다. R-05~R-17의 "실행 확인"은 **스텁 환경**이다: 임시 venv(`/tmp`, 저장소 밖)에 의존성을 설치하고, 실제 `argparsers.get_argument_parser()`로 만든 `edit`/`delete` 옵션으로 `GoogleCalendarInterface`를 `__new__`로 만든 뒤 `get_events()`를 요청 기록 객체로, `_PrintEvent`를 간단한 출력으로 바꾸고 `input()`을 스크립트 입력으로 바꿔 `_edit_event`·`_delete_event`를 직접 호출했다. 따라서 **`ModifyEvents`→`_search_for_events`→실제 `_PrintEvent` 전체를 이은 실행은 하지 않았다**(그 부분은 줄 추적). 사용한 이벤트는 `+09:00`·`Asia/Seoul` 캘린더 한 개의 가짜 이벤트다. 로케일·tz가 다른 환경에서 isoformat 오프셋 표기는 달라질 수 있다.

### 1.5 필수 코드 참조 [필수]
기준 SHA `405639c27639a82a13538ad72ae012e76942530c`. 라이선스는 overview 1절을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/gcal.py:989-1022` `delete`, `_delete_event` | 확인 프롬프트 분기와 `delete` API 호출, `Deleted!` 출력 위치 | R-05, R-06 |
| C-02 | `gcalcli/gcal.py:1024-1042` `_SetEventStartEnd` | `s` 덮어쓰기, 버려지는 `e` 뺄셈, 종일/비종일 `start`·`end` 본문 | R-14~R-16 |
| C-03 | `gcalcli/gcal.py:1044-1160` `_edit_event` | 메뉴 분기 순서, `s`의 patch 본문 구성, 항목별 처리, 루프 말미 재출력. **이 함수의 분기 순서와 변수 수명(`all_day`가 `if val:` 안에서만 대입, `rem` 빈 목록의 `default_reminders` 접근)이 R-07~R-17의 핵심이라 글로 풀지 않고 이 범위를 그대로 따른다** | R-07~R-13, R-17 |
| C-04 | `gcalcli/gcal.py:1505-1513` `ModifyEvents` | 빈 검색어 거부, 검색 → `self.expert` 대입 → `_iterate_events(year_date=True, work)` | R-03, R-04 |
| C-05 | `gcalcli/cli.py:315-326` | `delete`·`edit` 분기의 인자 배선 | R-01 |
| C-06 | `gcalcli/validators.py:11-23` `VALID_OVERRIDE_COLORS`, `get_override_color_id` | 색 이름 11개(순서 = `colorId` 1~11)와 id 변환 | R-11 |
| C-07 | `gcalcli/argparsers.py:484-506` | `edit`·`delete` 서브커맨드의 `parents`와 `--iamaexpert` | R-02 |

`_iterate_events`·`_search_for_events`·`get_input`·검증기·`get_times_from_duration`·`parse_reminder`·`_retry_with_backoff`는 선행 스펙의 C-ID/R-ID를 쓴다(1.2). `_PrintEvent` 본문은 행 5다.

### 1.6 수락 사례 [필수]
출처: 구현에서 도출. 실행 사례(T-02~T-12)는 1.4 확인 한계의 스텁 환경(가짜 이벤트 10:00~11:00 +09:00, 캘린더 tz `Asia/Seoul`, API는 요청 기록)에서 수행했으며, 네트워크·서버 응답·실제 `_PrintEvent` 렌더링은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03 | `delete ""`, `edit ""` | `GcalcliError('The empty string would get *ALL* events')`, 종료 1, API 호출 없음. `delete " "`은 이 오류 없이 검색으로 진행 |
| T-02 | R-05 | `delete`, 입력 `y` / `n` / 빈 줄 / `q` / `z` | `delete` 요청 1회 + `Deleted!` / 요청 없음, 다음 이벤트 / 요청 없음, 다음 이벤트 / 요청 없음, 종료 0 / 요청 없음, `Error: invalid input`, 종료 1 |
| T-03 | R-05 | `delete --iamaexpert`, 입력 없음 | 프롬프트 없이 `delete` 요청 1회 + `Deleted!` |
| T-04 | R-07 | `edit`, 입력 `x` / `q` / `n` | 종료 1 / 종료 0 / API 없이 반환 |
| T-05 | R-08, R-11 | `edit`, 입력 `c`, `sage`, `s` | 재출력 후 `patch` 본문 `{'summary','start','end','colorId': '2'}`(원본에 있던 키만) + `Saved!` |
| T-06 | R-12 | `edit`, 입력 `r`, `10m`, `.`, `s` | 본문 `reminders: {'useDefault': False, 'overrides': [{'minutes': 10, 'method': 'popup'}]}` |
| T-07 | R-12 | `edit`, 입력 `r`, `.` | `KeyError: 'default_reminders'`, API 호출 없음 |
| T-08 | R-13, R-14 | 10:00~11:00 이벤트, `w`, `2024-05-01 14:00`, `s` | 본문 `start.dateTime=...T14:00:00+09:00`, `end.dateTime=...T15:00:00+09:00`, 둘 다 `date: None`, `timeZone: Asia/Seoul`. 메모리의 `event['e']`는 여전히 11:00 |
| T-09 | R-15 | 위 이벤트, `w 14:00`, `w 16:00`, `s` | 본문 `start 16:00`, **`end 13:00`**. 세 번째 `w 18:00`이면 `end 13:00` |
| T-10 | R-15 | 위 이벤트, `g`, `2h`, `w`, `2024-05-01 14:00`, `s` | 본문 `end 15:00`(16:00이 아님) |
| T-11 | R-17 | 위 이벤트, `g`, (빈 줄) | `UnboundLocalError`(`all_day`). 같은 입력을 `w 14:00` 뒤에 하면 `start == end == 14:00` |
| T-12 | R-13, R-17, R-18 | 종일 이벤트(`start={'date': '2024-05-01'}`, `end={'date': '2024-05-02'}`), `w`, `2024-05-02 10:00`, `s` / 또는 `g`, `1h` | 본문 `start 2024-05-02T10:00 +09:00`~`end 2024-05-03T10:00 +09:00`(timed로 변환) / `KeyError: 'dateTime'` |
| T-13 | R-16 | `options['allday']=True`로 `_SetEventStartEnd('2024-05-02','2024-05-03', 종일이벤트)` | `TypeError`(aware − naive). 그 전에 `event['s']`는 naive 자정으로 덮여 있음 |
| T-14 | R-10 | `edit`, `l`, 빈 줄 / `t`, 공백만 | 둘 다 `location`·`summary` 변경 없음(재질문은 `t`의 완전 빈 문자열에만) |
| T-15 | R-04 | 검색 결과 0건 | `No Events Found...`, `work` 미호출, 종료 0 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@405639c `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-05(`cli.py:315-326`) | 줄 추적 |
| R-02 | C-07(`argparsers.py:484-506`), `argparsers.py:271-293`(`remind_parser`), `argparsers.py:594-596,641-646`(`add`), `config.py:27-66`, `cli.py:186-208` | 줄 추적. 부재 주장: `grep -rn "default_reminders\|'allday'\|\.allday" gcalcli` → 정의는 `argparsers.py:288`(remind_parser)·`641-643`(add)뿐이고 `edit`/`delete` parents에 없음, config 필드는 `client_id`·`default_calendars`·`ignore_calendars`·`week_start` 등. 놓칠 가능성: `deprecations.py`의 `--default_reminders`(`OPTIONS['remind']`)도 `get_remind_parser`에만 붙음. 실행: 임시 venv에서 `vars(get_argument_parser().parse_args(['edit','x']))`에 `allday`·`default_reminders` 없음 확인(config 네임스페이스는 합치지 않음 — `cli.py:195-203`의 필드 목록이 위와 같음을 줄로 확인) |
| R-03 | C-04(`gcal.py:1505-1513`), `cli.py:393-395`, event-query R-13·R-16·R-18 | 줄 추적 |
| R-04 | event-query C-03(`gcal.py:1162-1192`), `cli.py:315-326`, `gcal.py:1511` | 줄 추적. `tsv`·`json` 미읽음: `ModifyEvents`·`_iterate_events` 본문에 `options.get('tsv'|'json')` 없음(읽은 범위 `gcal.py:1162-1192, 1505-1513`) |
| R-05 | C-01(`gcal.py:996-1022`), 실행 | 줄 추적 + 스텁 실행(T-02, T-03). `Error: invalid input`이 stderr인지는 `printer.err_msg`가 `file=sys.stderr`(`printer.py:93-94`)임을 줄로 확인 |
| R-06 | C-01(`gcal.py:989-994`), `gcal.py:135-149` | 줄 추적. `None` 반환 시 `Deleted!` 출력은 코드 구조상(반환값 미검사)으로 확인, 실제 소진 상황은 재현하지 않음. 반복 일정 의미는 외부(U-04) |
| R-07 | C-03(`gcal.py:1044-1160`) | 줄 추적 + 스텁 실행(T-04). `elif not val or val.lower() == 'q'`(1082)의 `not val`이 죽은 조건임은 ① 분기(1052)로 빈 줄이 먼저 반환되기 때문 |
| R-08 | C-03(`gcal.py:1062-1081`) | 줄 추적 + 스텁 실행(T-05). 서버 응답은 U-01 |
| R-09 | C-03(`gcal.py:1082-1084`) | 줄 추적 + 스텁 실행 |
| R-10 | C-03(`gcal.py:1086-1099, 1148-1151`), input-parsing R-21 | 줄 추적 + 스텁 실행(T-14는 줄 추적 위주) |
| R-11 | C-03(`gcal.py:1056-1061`), C-06 | 줄 추적 + 스텁 실행(T-05). `override_color` 옵션은 `argparsers.py:237-242`(`--override-color`, 출력 옵션)에서 기본 False로 정의되고 `c`가 `True`로 바꿈 |
| R-12 | C-03(`gcal.py:1126-1146`), R-02 근거 | 줄 추적 + 스텁 실행(T-06, T-07). `.`만 입력 시 `KeyError`는 `edit`의 `self.options`에 키가 없다는 R-02에 의존 |
| R-13 | C-03(`gcal.py:1096-1108`), input-parsing C-05(`utils.py:68-93`) | 줄 추적 + 스텁 실행(T-08, T-12). "날짜 없는 입력은 오늘"은 input-parsing R-01(`default=zero_oclock_today`)을 따름 |
| R-14 | C-02(`gcal.py:1024-1042`) | 줄 추적 + 스텁 실행(T-08). `event['e'] - parse(end)`는 `gcal.py:1026`에서 대입 없는 식문장(주의: 호출 시 `e`가 aware이고 `parse(end)`가 naive이면 `TypeError`, R-16). 부재 주장: `_SetEventStartEnd`가 `event['e']`에 대입하지 않음 — `grep -n "\['e'\] *=" gcalcli/gcal.py` → 대입은 `_GetAllEvents`(`1226-1228` 부근)뿐이고 `_SetEventStartEnd` 안에 없음(범위 `gcalcli/*.py`; 이 SHA의 event-query R-08도 같은 결론) |
| R-15 | C-02, C-03(`gcal.py:1099-1108, 1158-1160`), `gcal.py:815-816, 842` | 줄 추적 + 스텁 실행(T-09, T-10). `_PrintEvent`가 `s`·`e`를 읽는 위치(`815-816`, `842`)는 읽었으나 렌더링 전체는 행 5 |
| R-16 | C-02, C-03, input-parsing R-10 | 줄 추적 + 실행(`get_times_from_duration('2024-05-02 10:00', duration=1440.0, allday=True)` → `('2024-05-02', '2028-04-11')`; `_SetEventStartEnd` allday → `TypeError`, T-13). `allday` 도달 불가는 R-02 |
| R-17 | C-03(`gcal.py:1110-1124`), input-parsing R-08 | 줄 추적 + 스텁 실행(T-11, T-12). 변수 수명은 Python 지역 변수 규칙(함수 하나 안에서 `while` 반복 사이 유지) |
| R-18 | R-13, R-17 | 위 R-ID 종합 |
| R-19 | C-03 | 부재 주장 검색 `grep -n "attendees" gcalcli/gcal.py`(범위 `gcal.py` 전체; `_edit_event` 안에 없음) |
| R-20 | `tests/test_gcalcli.py:281-284` | 사례 1개만 열람. `grep -rn "_edit_event\|_delete_event\|ModifyEvents" tests`(범위 `tests/`)로 다른 호출 없음 확인. 놓칠 가능성: `tests/cli/test.bats`는 열지 않음 |
| T-01~T-15 | 위 R-ID 근거 | T-02~T-14의 실행 사례는 스텁 환경 |

### 2.2 코드 읽는 순서 [선택]
`cli.py:315-326`(배선) → `gcal.py:1505-1513 ModifyEvents` → `gcal.py:1162-1192 _iterate_events`(event-query) → `gcal.py:996-1022 _delete_event` 또는 `gcal.py:1044-1160 _edit_event`(`s` 분기 1062-1081 → `w`/`g` 1096-1124 → `_SetEventStartEnd` 1024-1042). `_edit_event`는 단일 함수 안에서 지역 변수(`event`, `val`, `all_day`, `rem`)가 `while` 반복 사이에 살아 있다는 점이 R-17의 열쇠다.

### 2.4 검토 기록 [필수, ready 스펙]
- **작성자 점검**: `edit`/`delete`의 실제 argparse 옵션으로 `_edit_event`·`_delete_event`를 스텁 API와 스크립트 입력으로 직접 실행해 R-02, R-05, R-12~R-17을 확인했다(임시 venv, 저장소 밖. `ModifyEvents`부터 `_PrintEvent`까지 이은 실행은 하지 않고 줄 추적).
- **메인 세션 점검(2026-11-18)**: `check.py` 통과, `repos/gcalcli` 변경 없음. 고위험 이상 동작을 원본 줄로 대조해 일치: `g` 경로에서 `all_day`가 `if val:` 안에서만 대입됨(`gcal.py:1111-1117`), edit에서 읽는 `self.options['default_reminders']`(`gcal.py:1137`)가 edit 옵션에 없음, 참석자 수정 메뉴 없음(`attendees`는 `AddEvent` 1492와 출력 885·898에만 있음), `--allday`는 `add` 서브커맨드(`argparsers.py:641`)에만 있음.
- **독립 검토 미수행**: 이 스펙에 의존하는 스펙이 없고 계획(3·4·6만)에 따랐다. 원본 이상 동작 후보가 많아(R-12, R-14~R-17) 필요하면 R-12·R-15·R-17부터 독립 검토를 돌린다.
- **대조하지 않은 R-ID**: 위에서 실행·대조하지 않은 나머지.
- **status를 `draft`로 유지하는 이유**: U-01~U-04가 열려 있고(서버 동작) 선행 스펙도 `draft`다.
- 재구현: 미수행.
