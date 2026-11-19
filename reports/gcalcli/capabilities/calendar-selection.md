---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/gcal.py
  - gcalcli/cli.py
  - gcalcli/argparsers.py
  - gcalcli/printer.py
  - gcalcli/_types.py
  - gcalcli/env.py
  - gcalcli/actions.py
  - tests/test_gcalcli.py
  - tests/conftest.py
depends:
  - oauth-auth.md
  - config-resolution.md
status: draft
---

# 캘린더 목록·선택·캐시

> 인증된 Calendar API에서 접근 가능한 캘린더 목록(`calendarList`)을 받아 `accessRole` 순으로 정렬해 pickle 캐시에 저장·재사용하고, `list`로 표시하며, `--calendar 이름#색` 목록을 정확 일치 우선·아니면 정규식(대소문자 무시)으로 골라 이후 모든 일정 커맨드가 쓰는 `self.cals`를 만들고, API 호출에 재시도 백오프(`_retry_with_backoff`)를 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `cli.main`이 [config-resolution](config-resolution.md) R-18의 `set_resolved_calendars`로 `cal_names`(이름 문자열 → `CalName(name, color)` 목록)와 `ignore_calendars`를 확정하고 `GoogleCalendarInterface(cal_names=..., **options)`를 만든다. 이 스펙은 `parse_cal_names`의 `name#색` 해석과 그 뒤를 맡는다(R-01~R-03).
2. 생성자: `userless`가 아니고 `do_eager_init`(= `command != 'init'`)이면 `_get_cached()`로 `self.cache`·`self.all_cals`를 채운다(R-04~R-07). 그다음 `_select_cals(cal_names)`로 `self.cals`를 만든다(R-08~R-10).
3. `_get_cached()`: `--refresh`면 캐시 파일 삭제 → `--nocache`가 아니면 캐시 파일을 읽어 `all_cals`를 복원하고 끝. 못 읽으면 `calendarList().list`를 페이지 끝까지 호출(R-11 재시도 포함)해 모으고 `accessRole`로 안정 정렬한 뒤, 캐시 사용이면 `cache` 파일에 pickle로 쓴다. 캐시 미사용 경로(`--nocache`)는 파일을 읽지도 쓰지도 않는다(R-04~R-06).
4. `_select_cals`: 이름이 없으면 `ignore_calendars`에 있는 summary를 뺀 모든 캘린더가 `cals`. 이름이 있으면 이름마다 정확 일치 1개(첫 항목) 또는 정규식 일치 전부를 `cals`에 더하고, 고른 캘린더 dict에 `colorSpec`을 심는다(R-08, R-09).
5. 서브커맨드가 `self.cals`(일정 조회·추가 등)나 `self.all_cals`(`list`)를 읽는다. `list`는 `ListAllCalendars()`가 `all_cals` 전체를 `Access  Title` 표로 stdout에 출력한다(R-12).
6. `util reset-cache`는 gcal 객체 없이 후보 경로 전부에서 `cache` 파일을 지운다(R-13).

### 1.2 범위·통합 지점 [필수]
- 제공: 캘린더 목록 취득·정렬·캐시, `--calendar` 이름·색 해석(`parse_cal_names`, `rsplit_unescaped_hash`), `_select_cals`, `list`(`ListAllCalendars`), `util reset-cache`, `_retry_with_backoff`, 이후 스펙이 쓰는 공유 상태 `cals`·`all_cals`·`cache`의 정의(1.3), 색 결정 `_calendar_color`.
- 제외: `default_calendars`/`ignore_calendars`/`global_calendars` 중 어느 이름 목록을 쓸지의 결정과 ignore 목록의 명시 이름 제거(config-resolution R-18 소유. 이 스펙은 그 결과 `cal_names`·`options['ignore_calendars']`를 입력으로 받는다). 일정 조회·추가 등 이벤트 API 호출(후속 스펙; 그들이 `_retry_with_backoff`·`cals`를 소비한다). 캐시·`oauth` 파일 경로 규칙과 legacy 이동(config-resolution R-13 소유; 이 스펙은 `data_file_path('cache')`가 준 경로 하나를 소비한다). 인증(`get_cal_service`가 인증 완료된 서비스 객체를 돌려준다는 것만 [oauth-auth](oauth-auth.md) R-02·R-15에 기댄다).
- 외부 의존: `googleapiclient`의 `calendarList().list(pageToken=...)` 요청 객체와 `.execute()`, `HttpError`(`.content` bytes JSON), 표준 `pickle`·`re`·`time`·`random`. 시계: `time.sleep`. 네트워크: Google Calendar API.
- 소유 상태·부작용: `cache` 파일(생성·삭제), 인스턴스 속성 `cache`·`all_cals`·`cals`, `all_cals` 항목 dict에 `colorSpec` 키 삽입(R-09), stdout 목록 출력, stderr 디버그 메시지(색 접미사 해석 실패).

### 1.3 인터페이스와 데이터 의미 [필수]
**공유 상태(스펙 4·7·8의 선행 계약)**

| 데이터 | 타입 | 만들어지는 때·수명·소유권 |
|---|---|---|
| `CalName` | namedtuple(`name: str`, `color: str`) | `cli.py:58`. `parse_cal_names`가 만든다. `color`는 `valid_color_name` 통과 값 또는 `'default'` |
| `self.all_cals` | list of CalendarListEntry dict | `_get_cached()`가 인스턴스에 새로 대입(`= []` 후 채움 또는 캐시에서 복원). 클래스 기본값 `[]`(`gcal.py:52`)는 `_get_cached`가 안 불리는 경우(`init`, userless)에만 보이고, 어디서도 제자리 수정되지 않는다. **필터링 안 된 접근 가능한 모든 캘린더**(ignore된 것 포함), `accessRole` 문자열 오름차순(`freeBusyReader < owner < reader < writer`) 안정 정렬. 항목 dict는 `id`, `summary`, `accessRole`, `timeZone` 등을 갖고(코드가 읽는 키만 확인: `id`·`summary`·`accessRole`·`timeZone`), 선택 시 `colorSpec`이 추가될 수 있다. 인스턴스(= 프로세스) 수명. 호출자별 복사는 없다 |
| `self.cals` | list of CalendarListEntry dict | `__init__`이 `[]`로 만들고 `_select_cals`가 **한 번** 채운다(`self.cals = ...` 또는 `+=`가 `gcal.py` 안에서 이것뿐: `grep -n 'self\.cals *\(=\|+=\)\|cals\.\(append\|extend\)' gcalcli/*.py`). 항목은 `all_cals`의 **같은 dict 객체**(별칭, 복사 아님). 순서 = 선택 이름 순서 × (이름 안에서는 `all_cals` 순서). **중복 제거 없음**(여러 이름이 같은 캘린더에 맞으면 중복 항목). `init`·userless·ignore로 전부 제외되면 `[]` |
| `self.cache` | dict, 사실상 `{'all_cals': list}` | `_get_cached()`가 매번 `{}`로 초기화 후 캐시 파일에서 복원하거나 새로 만든다. `'all_cals'` 키가 값으로 가리키는 리스트는 `self.all_cals`와 **같은 객체**. 이 키 외에는 아무 코드도 쓰지 않는다(`grep -n 'self\.cache\[' gcalcli/*.py` → 337, 359행뿐). 클래스 기본값 `{}`(`gcal.py:51`)는 `_get_cached` 전에만 보인다. 만료(TTL)·버전 필드가 없다 |
| `event['gcalcli_cal']` | `cals` 항목 dict 참조 | 이벤트 조회가 붙인다(`gcal.py:1209`, 후속 스펙). `_calendar_color`가 읽는다 |
| `colorSpec` | `all_cals` 항목 dict의 키(str) | `_select_cals`가 심는다(R-09). **캐시 파일에는 저장되지 않는다**: 캐시 쓰기(`gcal.py:358-362`)는 `_select_cals`보다 먼저라서다 |

**연산**

| 연산 | 입력·출력 | 의미·제약 |
|---|---|---|
| `rsplit_unescaped_hash(s)` | str → `(str, str\|None)` | 정규식 C-01로 **마지막 이스케이프되지 않은 `#`** 앞뒤로 나눈다. 일치하면 두 부분 모두 `\x` → `x`로 이스케이프 해제. `#`가 없거나 뒷부분에 이스케이프 안 된 `#`가 있는 형태가 아니면 `(s, None)`(해제하지 않고 원문 그대로) |
| `parse_cal_names(names, printer)` | list[str] → list[CalName] | 이름마다 `rsplit_unescaped_hash`. 뒷부분이 `COLOR_NAMES`(`default black red green yellow blue magenta cyan white brightblack brightred brightgreen brightyellow brightblue brightmagenta brightcyan brightwhite`)에 있으면 `(앞부분, 색)`, 아니면 **입력 문자열 전체**가 이름이고 색은 `'default'`(stderr 디버그 메시지). 결과는 이름(키)을 중복 제거하며 첫 등장 순서를 유지하고 값은 **마지막 색**(dict) |
| `GoogleCalendarInterface(cal_names=(), printer, userless_mode, do_eager_init, **options)` | | 필요한 options 키: `ignore_calendars`(없으면 `KeyError`), `use_cache`, `refresh_cache`, `config_folder`, `color_title`, `color_owner/writer/reader/freebusy`. `cal_names`는 `CalName` 순회 가능 객체 |
| `_get_cached()` | → None | `self.cache`·`self.all_cals`를 새로 만든다. 동작은 R-04~R-07 |
| `_select_cals(names)` | → None | `self.cals`가 이미 비어 있지 않으면 `GcalcliError('this object should not already have cals')`(생성자만 호출하므로 도달 불가: 추론, 2.1) |
| `_retry_with_backoff(request)` | `HttpRequest` → 응답 dict or None | R-11. 클래스 속성 `max_retries = 5` |
| `ListAllCalendars()` | → None | R-12 |
| `_calendar_color(event, override_color=False)` | → color name | C-04. `event['gcalcli_cal']`이 없으면 `'default'` |
| CLI | `--calendar NAME[#COLOR]` | 여러 번 가능(`calendars_parser`, `action='append'`) 또는 한 번(`calendar_parser`, `store`). `--refresh`(dest `refresh_cache`, 기본 False), `--nocache`(dest `use_cache`, `store_false`, 기본 True), `util reset-cache` |

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `rsplit_unescaped_hash` 입력 | C-01 정규식대로. 예(최소 재현으로 확인): `a#red`→`('a','red')`, `a#b#c`→`('a#b','c')`, `a\#b`→`('a\#b', None)`(`#`가 이스케이프돼 있어 분할 안 됨, **백슬래시가 남는다**), `a\#b#red`→`('a#b','red')`, `#red`→`('','red')`, `a#`→`('a','')`, `a##red`→`('a#','red')` | 코드 확인 + 재현 |
| R-02 | `parse_cal_names`: 뒷부분이 유효 색 | `CalName(앞부분, 색)`. 앞부분은 이스케이프 해제된 값이라 `a\#b#red`는 이름 `a#b` | 코드 확인 |
| R-03 | `parse_cal_names`: 뒷부분이 있는데 색이 아님(`a#b#c`, `a#`) 또는 `#`가 없음 | 이름 = **원래 입력 문자열 그대로**(이스케이프 해제 안 됨. `a\#b#c`면 `a\#b#c` 전체), 색 `default`. 뒷부분이 있었던 경우만 stderr에 디버그 `Using entire name '<입력>' as cal name.\nChange '<앞부분>' to a valid color name if intended to be a color (or otherwise consider escaping "#" chars to "\#").\n`. `printer=None`이면(테스트) 디버그 시 `AttributeError`. 같은 이름이 여러 번 오면 한 항목으로 합쳐지고 마지막 색이 이긴다 | 코드 확인 |
| R-04 | `_get_cached()` 첫 부분 | `data_file_path('cache')`로 경로를 얻는다(`--nocache`여도 호출하므로 config-resolution R-13의 legacy 이동 부작용이 일어난다). `refresh_cache`가 참이면 캐시 파일을 `unlink(missing_ok=True)`(`--nocache`와 무관). 그다음 `cache={}`, `all_cals=[]`로 초기화 | 코드 확인 |
| R-05 | `use_cache` 참 + 캐시 파일 읽기 | `pickle.load` 후 `self.cache['all_cals']`를 `all_cals`로 쓰고 **즉시 반환**(API 호출 없음, 인증 코드 미실행: oauth-auth R-02). 내용 검증 없음. 파일이 없거나 읽기 `IOError`(`OSError` 별칭)면 R-06으로 진행(`pass`). 그 밖의 예외(손상된 pickle: `UnpicklingError`/`EOFError`, `KeyError('all_cals')` 등)는 잡지 않아 traceback으로 종료하며, 복구 수단은 `--refresh`나 `util reset-cache` | 코드 확인 |
| R-06 | 캐시 미사용·미존재 | `calendarList().list(pageToken=page_token)`를 `_retry_with_backoff`로 호출, 응답 `items`를 `all_cals`에 이어 붙이고 `nextPageToken`이 없을 때까지 반복(인자는 `pageToken` 하나뿐, 다른 필터 없음). 끝나면 `all_cals.sort(key=accessRole)`(안정 정렬: 같은 role은 API 순서 유지). `use_cache` 참이면 `cache['all_cals']=all_cals`로 두고 부모 디렉터리를 만든 뒤 `wb`로 직접 `pickle.dump`(원자적 교체 없음). `--nocache`면 파일을 쓰지 않는다. 오류(`HttpError` 재전파 또는 R-11의 `None` 반환 → `None['items']` `TypeError`)는 전파 | 코드 확인 |
| R-07 | 캐시 신선도 | 캐시는 만료되지 않는다. 지워지는 경우는 `--refresh`, `util reset-cache`, `SetupAuth`의 재인증(oauth-auth R-07)뿐이다(`grep -n 'unlink' gcalcli/*.py`: `gcal.py:248,326`, `cli.py:370`). 캐시에는 `all_cals`만 있어 인증 계정이 바뀌어도 이전 계정의 목록이 남는다(추론: 계정 식별자가 캐시에 없음) | 코드 확인 / 추론 |
| R-08 | `_select_cals`, `selected_names`가 비어 있음 | `cals = [c for c in all_cals if c['summary'] not in options['ignore_calendars']]`(summary **정확 일치**, 대소문자 구분). `all_cals`가 비어 있으면 `cals=[]` | 코드 확인 |
| R-09 | `_select_cals`, 이름 있음: 이름(CalName)마다 `all_cals`를 순서대로 순회 | ① `cal_name.name == summary`(정확, 대소문자 구분)이면 그 항목 **하나만**으로 `matches`를 대체하고 `colorSpec=cal_name.color`를 심고 순회 종료(첫 정확 일치). ② 아니면 `re.search(cal_name.name, summary, re.I)`(부분 일치 검색, 대소문자 무시)가 참이면 `matches`에 추가하고 `colorSpec` 심기. 순회가 끝나면 `cals += matches`. 이름 간 중복 제거 없음: 서로 다른 두 이름이 같은 캘린더에 맞으면 같은 dict가 `cals`에 두 번 들어가고, `colorSpec`은 별칭이라 먼저 맞은 항목의 색까지 나중 이름의 색으로 덮인다. **이름이 있을 때는 `ignore_calendars`를 전혀 참조하지 않는다**(R-08의 ignore는 이름 없음 경로에만 적용). **정확 일치가 나중 항목이면 앞서 정규식으로 맞은 항목은 `matches`에서 빠지지만 그 항목의 `colorSpec`은 이미 바뀐 채로 남는다**(`all_cals`는 변경된 상태; 선택되지 않으므로 영향은 `list` 출력 색과 후속 접근에 한정: 추론). 이름이 정규식으로 해석 불가(`re.error`)면 비-`GcalcliError`로 전파(traceback). **어떤 이름도 일치하지 않으면 아무 메시지 없이 `cals`에 아무것도 더하지 않는다**(모든 이름이 불일치하면 `cals=[]`, 에러 없음). 정규식 메타문자(`.`, `*`, `+`)가 이름에 있으면 정확 일치가 아니어도 의도치 않게 맞을 수 있다(예: `j*`는 거의 모든 summary에 일치) | 코드 확인 |
| R-10 | 색 결정 `_calendar_color(event, override)` (C-04) | `event['gcalcli_cal']`이 없으면 `'default'`. `override_color`면 `ansi_codes[event['colorId']]`(1~11 → 색 이름 표). 아니면 `cal['colorSpec']`이 참이면 그 값(문자열 `'default'`도 참이므로 `#색` 없이 선택돼도 `colorSpec='default'`가 접근 role별 색을 **가린다**), 아니면 `accessRole`별 `options['color_owner'/'color_writer'/'color_reader'/'color_freebusy']`, 모르는 role은 `'default'` | 코드 확인 |
| R-11 | `_retry_with_backoff(request)` | `for n in range(5)`: `request.execute()`를 시도해 성공하면 응답 반환. `HttpError`면 `json.loads(e.content)['error']`에서 `error.get('code') == '403'`(**문자열** `'403'`과 비교)이고 `error['errors'][0]['reason']`이 `rateLimitExceeded` 또는 `userRateLimitExceeded`이면 `sleep((2**n) + random.random())`초 후 재시도(대기 1~2, 2~3, 4~5, 8~9, 16~17초), 그렇지 않으면 즉시 같은 `HttpError`를 다시 던진다. 5번 모두 재시도 조건이면 **`None`을 반환**한다(오류 없이). `HttpError` 외 예외(네트워크 등)는 재시도 없이 전파한다. **구현상 비교 대상이 문자열 `'403'`인데 Google API 오류 JSON의 `code`는 숫자 403이라고 공식 문서에 나와 있어, 실제 rate-limit 응답에서는 조건이 거짓이 되어 재시도 없이 바로 던져질 가능성이 높다**(코드 확인 + 공식 문서 확인(`developers.google.com/workspace/calendar/api/guides/errors`의 403 `rateLimitExceeded` 예시는 `"code": 403` 숫자); 실제 응답 실행은 안 함). `content`가 JSON이 아니면 `JSONDecodeError`, `error` 키가 없으면(`None.get`) `AttributeError`가 `HttpError` 대신 난다. `errors[0]`은 `and` 단락 평가 때문에 `code == '403'`일 때만 접근되므로 `errors`가 비어 있는 `TypeError`/`IndexError` 경로는 그 조건에서만 난다(숫자 403이 실제라면 `errors`는 접근되지 않는다) | 코드 확인 / 외부 문서 확인(숫자 code) / 추론(실제 동작) |
| R-12 | `ListAllCalendars()` (`list` 커맨드) | `all_cals`가 비면 `max()` 때문에 `ValueError`. 아니면 `access_len=max(len(accessRole) 들, len('Access'))`, 형식 `' %<access_len>s  %s\n'`로 헤더 `Access`·`Title`, 구분선 `------`·`-----`을 `color_title` 색으로, 이어 **`all_cals` 전체**(`cals`·`--calendar`와 무관, 정렬 순서 그대로)를 `accessRole` 오른쪽 정렬 + summary로 출력. `ignore_calendars`에 정확히 있는 summary에는 ` (ignored)`를 붙인다(config-resolution R-18의 명시 선택 제거가 반영된 목록). 행 색은 `_calendar_color(cal)`인데 캘린더 dict에는 `gcalcli_cal`이 없어 **항상 `'default'`**다(`--calendar x#red`·`color_*` 옵션이 `list` 출력에 반영되지 않는다). 출력은 stdout | 코드 확인(경로 추적, 실행 안 함) |
| R-13 | `util reset-cache` | `env.data_file_paths('cache', parsed_args.config_folder)`가 돌려주는 후보 **전부**(config 디렉터리 후보는 존재할 때만 포함되고, 표준 데이터 디렉터리 후보는 항상, legacy는 존재할 때만) 중 존재하는 파일마다 stdout에 `Deleting cache file from <경로>...\n` 후 삭제. 하나도 없으면 `No cache file found. Exiting without deleting anything...\n`. gcal 객체를 만들지 않아 API·인증·legacy 이동이 없다. 종료 코드 0. `oauth`는 건드리지 않는다. `data_file_path`와 달리 첫 후보만이 아니라 모든 후보를 지운다 | 코드 확인 |
| R-14 | `_retry_with_backoff` 호출처 | 이 스펙의 `calendarList().list`(`gcal.py:346`) 외에 이벤트 API 호출처들이 쓴다(후속 스펙). 호출처가 `None` 반환을 처리하는지는 호출처별로 다르다(이 스펙 범위 밖, 위 R-06은 처리하지 않는다) | 코드 확인(호출 목록: `grep -n '_retry_with_backoff(' gcalcli/*.py` → `gcal.py` 9줄(정의 1 + 호출 8)+`actions.py` 3곳) |

- 불변식: 생성자 반환 후 `self.cals`의 모든 항목은 `self.all_cals`의 항목 객체와 같은 객체이다(복사 없음). `all_cals`는 `accessRole` 정렬 상태로 시작한다. `cache` 파일은 `all_cals`만 담는다.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-06, R-12 | `calendarList().list`가 기본으로 돌려주는 항목 범위(숨김·삭제된 캘린더 포함 여부), 한 페이지 크기, 응답 항목에 항상 있는 필드(`accessRole`, `summary`, `id`, `timeZone`)는 무엇인가? | `list` 출력 내용, `accessRole` 키 누락 시 정렬 `KeyError` | Calendar API v3 `CalendarList.list` 문서(웹)로 확인하거나 계정으로 실행 |
| U-02 | R-11 | `googleapiclient`의 `HttpError.content`가 실제로 숫자 `code`를 담는지(공식 오류 문서는 숫자). 숫자이면 이 구현의 재시도는 실제로 동작하지 않는다는 결론이 맞는가? 의도(문자열 비교가 버그인지)는 코드 밖 | 재구현에서 "원본 재현"이면 재시도가 없는 동작이고, "의도 재현"이면 숫자 비교다 | 실제 rate limit 응답 또는 googleapiclient 소스 확인. 이 환경에는 미설치 |

- 확인 한계: 계정·네트워크가 없어 캐시 생성, `list` 출력, rate-limit 재시도는 실행하지 못했다. `rsplit_unescaped_hash`의 분할 결과만 같은 정규식을 `python3 -I`로 최소 재현해 확인했다(R-01). `ListAllCalendars`와 `_calendar_color`의 결론은 코드 경로 추적이다. 원본 테스트는 `tests/test_gcalcli.py`의 `test_list`, `test_parse_cal_names`와 `tests/conftest.py`(`_get_cached` 대체)를 열람했고 실행하지 않았다.

### 1.5 필수 코드 참조 [필수]
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/cli.py:58`, `66-102` `CalName`, `rsplit_unescaped_hash`, `parse_cal_names` | 분할 정규식, 색 판정·디버그 문구(`{name!r}`·`{p1!r}`라 따옴표·백슬래시가 repr 형태로 나온다: 예 `a\#b#c`는 `'a\\#b#c'`), 중복 이름 병합 | R-01~R-03 |
| C-02 | `gcalcli/gcal.py:50-62`, `70-133` 클래스 속성, `__init__`, `_select_cals` | 공유 상태 초기화·선택 알고리즘 | R-08, R-09, 1.3 |
| C-03 | `gcalcli/gcal.py:135-149` `_retry_with_backoff` | 재시도 조건·대기식·`None` 반환 | R-11 |
| C-04 | `gcalcli/gcal.py:322-362` `_get_cached`, `364-395` `_calendar_color` | 캐시 읽기·쓰기·페이지 루프·정렬, 색 결정 표 | R-04~R-06, R-10 |
| C-05 | `gcalcli/gcal.py:1263-1284` `ListAllCalendars` | 열 폭·헤더·`(ignored)` 표기 | R-12 |
| C-06 | `gcalcli/cli.py:361-376` | `util reset-cache` 동작·문구 | R-13 |
| C-07 | `gcalcli/printer.py:4-8` `COLOR_NAMES`, `47-52` `valid_color_name` | 색 이름 집합과 검증 | R-02, R-03 |
| C-08 | `gcalcli/argparsers.py:65-76,153-181` | `--refresh`/`--nocache` dest·기본값, `--calendar` append/store | 1.3 |

`data_file_path`(`gcal.py:151-176`)와 `env.data_file_paths`는 [config-resolution](config-resolution.md) C-01·C-11을 쓴다. `COLOR_NAMES`는 set이라 오류 메시지의 색 나열 순서는 실행마다 다를 수 있다(추론: 해시 무작위화).

### 1.6 수락 사례 [필수]
출처: 사례별 표기. 대체: 실제 Google API 없음 → 캘린더 응답은 가정한 목록으로 대체하며, 실제 응답 형식과 네트워크 오류는 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-03 | `parse_cal_names(['a\\#b'])`, `['a#b#c']`, `['work#brightblue']` | `a\#b`(색 default, 디버그 없음), `a#b#c`(전체 이름, 디버그 메시지), `work`+`brightblue`. 구현에서 도출 + 정규식 재현 |
| T-02 | R-09 | `all_cals` = [`work`, `work2`, `Home`], `cal_names=[CalName('work','red')]` | 정확 일치 `work` 하나만 `cals`, `colorSpec='red'`(정규식으로도 맞는 `work2`는 제외). 구현에서 도출 |
| T-03 | R-09 | 같은 목록, `CalName('WORK','default')` | 정확 일치 아님, 정규식(대소문자 무시)으로 `work`·`work2` 둘 다 `cals`(`all_cals` 순). 구현에서 도출 |
| T-04 | R-09 | `CalName('zzz','default')` | `cals=[]`, 메시지·오류 없음. 구현에서 도출 |
| T-05 | R-08 | 이름 없음, `ignore_calendars=['Home']` | `cals=[work, work2]`. 구현에서 도출 |
| T-06 | R-05, R-06 | 캐시 파일 없음, `use_cache` 참 | API 목록을 받아 정렬하고 캐시 파일 생성. 다음 실행은 파일에서 복원해 API·인증 없이 끝. 구현에서 도출(실행 안 함) |
| T-07 | R-05 | 캐시 파일이 `garbage` | `UnpicklingError` traceback, 파일 유지. `gcalcli util reset-cache` 후 정상. 구현에서 도출 |
| T-08 | R-12 | `list` + 6개 캘린더(테스트 데이터 `cal_list.json`) | 출력 줄 수 = 6 + 3(헤더, 구분선, 끝 빈 조각). 원본 테스트 열람(`tests/test_gcalcli.py:test_list`) |
| T-09 | R-13 | 표준 데이터 디렉터리와 `~/.gcalcli_cache`에 캐시 둘 | 둘 다 삭제 메시지 후 삭제, 둘 다 없으면 `No cache file found...`. 구현에서 도출 |
| T-10 | R-11 | 요청이 `HttpError`(403, 숫자 `code`, `rateLimitExceeded`) | 재시도 없이 즉시 `HttpError` 전파(원본 재현). 문자열 `'403'` 응답이면 5회 재시도 후 `None`. 구현에서 도출 + 외부 문서 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@405639c `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01(`cli.py:66-82`) | 같은 정규식을 `python3 -I` 일회성 스니펫으로 실행해 예시 7개 확인(gcalcli import 없음) |
| R-02, R-03 | C-01(`cli.py:85-102`), C-07 | 줄 추적. `a\#b`는 정규식 `^((?:\\.|[^\\])*)[#]((?:\\.|[^#\\])*)$`가 안 맞아 `(s, None)`이 돼 이스케이프가 해제되지 않음을 재현으로 확인. `p2 is None`이면 `except`에 들어가지 않으므로 디버그 메시지도 없음. 테스트에서 `printer=None`을 넘기는 사례(`tests/test_gcalcli.py:99,140` 등)는 디버그 경로를 타지 않는 입력 |
| R-04 | C-04(`gcal.py:322-331`), `gcal.py:151-176` | 줄 추적 |
| R-05 | C-04(`gcal.py:331-341`) | 줄 추적. `IOError`는 Python 3에서 `OSError` 별칭(표준 동작). 손상 파일 예외 전파는 코드에 해당 `except`가 없다는 사실로 확인 |
| R-06 | C-04(`gcal.py:344-362`) | 줄 추적. `_retry_with_backoff`가 `None`이면 `cal_list['items']`에서 `TypeError`(코드 경로 추적) |
| R-07 | `gcal.py:248,326`, `cli.py:370`, `grep -n 'unlink' gcalcli/*.py` | 부재 주장(다른 삭제·만료 없음): 범위 `gcalcli/*.py`, 기준 SHA. 놓칠 가능성: 파일 시스템 외부 정리. TTL 부재는 `cache` dict에 키가 `all_cals`뿐인 것과 `grep -n 'self\.cache\[' gcalcli/*.py`로 확인 |
| R-08, R-09 | C-02(`gcal.py:104-133`), `tests/test_gcalcli.py:352-370` | 줄 추적. 테스트는 `j*`·정확 이름이 `AgendaQuery()==0`까지만 확인하고 선택 결과는 검증하지 않음(TODO 주석). "일치 없음 → 조용히 무시"는 `else`/오류 분기가 없다는 사실로 확인. `_select_cals` 가드(`self.cals` 비어있지 않음) 도달 불가: `grep -n '_select_cals(' gcalcli/*.py` → 호출처 `gcal.py:102` 하나(생성자, `self.cals=[]` 직후). 놓칠 가능성: 외부 코드가 직접 호출 |
| R-10 | C-04(`gcal.py:364-395`), `gcal.py:496-500,821-825` 호출처 | 줄 추적. `colorSpec='default'`가 truthy라는 것은 비어 있지 않은 문자열이라는 Python 규칙. `set_resolved_calendars`가 이름에 색이 없으면 `'default'`를 `CalName.color`로 넘기는 경로는 R-02/R-03(`cal_color='default'`) |
| R-11 | C-03(`gcal.py:135-149`), 외부: `developers.google.com/workspace/calendar/api/guides/errors`(WebFetch로 확인, 공식 문서) | 줄 추적. 재시도가 실제로 동작하는지는 실응답 필요(U-02). `time.sleep` 식은 코드 그대로(`2**n + random.random()`) |
| R-12 | C-05(`gcal.py:1263-1284`), `gcal.py:364-381`, `tests/test_gcalcli.py:34-47` | 줄 추적: `ListAllCalendars`의 `cal`은 `calendarList` 항목이고 `gcalcli_cal` 키가 없어 `'default'`(`gcal.py:378-379`). `grep -n 'gcalcli_cal' gcalcli/gcal.py`로 키를 넣는 곳이 `1209`(이벤트 조회)뿐임 확인. 테스트는 색 코드 포함 헤더 일치와 줄 수만 확인하고 행 색은 검증하지 않음 |
| R-13 | C-06, `env.py:15-39` | 줄 추적 |
| R-14 | `grep -n '_retry_with_backoff(' gcalcli/*.py`: `gcal.py:135,346,990,1071,1197,1435,1452,1497,1670`, `actions.py:48,60,84` | 줄 추적 |
| T-01~T-10 | 위 R-ID 근거 | T-08만 원본 테스트 열람. 나머지는 구현에서 도출, 실행 없음 |

### 2.4 검토 기록 [필수, ready 스펙]
- **작성자 자체 점검**: R-03, R-09, R-11, R-12의 인용 줄을 다시 열어 맞춰 봤다.
- **독립 검토(읽기 전용 서브에이전트, 2026-11-18)**: R-01~R-14 전부와 1.3 공유 상태 5개 항목, C-01~C-08 인용 줄(15개 이상 표본)을 대조했다. 중대한 불일치 없음. 공유 상태 계약(`cals`가 `all_cals` 항목의 별칭, `colorSpec`이 캐시에 저장되지 않음, `gcalcli_cal`은 `gcal.py:1209` 한 곳에서만 쓰임)은 호출 순서와 전수 grep으로 확인됐다. 보강 5건은 본문에 반영했다: 이름 경로의 `ignore_calendars` 미참조, 중복 선택 시 `colorSpec` 덮어쓰기, R-03 디버그 문구의 repr 형태, R-11 예외의 단락 평가 조건, `data_file_path`가 `functools.cache`로 인스턴스별 메모이즈됨(재호출 시 legacy 이동이 반복되지 않음).
- **대조하지 않은 것**: T-01~T-10 실행(코드 추적만), U-01·U-02의 외부 API 사실(Google 계정·네트워크 필요).
- **status를 `draft`로 유지하는 이유**: U-01·U-02가 열려 있고 선행 스펙 oauth-auth·config-resolution도 `draft`다.

## 적용 메모 [선택]
없음(분석 목적 미정).
