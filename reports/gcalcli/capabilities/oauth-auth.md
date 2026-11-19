---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/auth.py
  - gcalcli/gcal.py
  - gcalcli/utils.py
  - gcalcli/cli.py
  - gcalcli/argparsers.py
  - gcalcli/config.py
  - gcalcli/printer.py
  - docs/api-auth.md
  - README.md
  - ChangeLog
  - pyproject.toml
  - tests/test_auth.py
  - tests/conftest.py
  - tests/data/legacy_oauth_creds.json
depends:
  - config-resolution.md
status: draft
---

# OAuth 인증·토큰

> 사용자가 만든 Google Cloud OAuth client-id/secret으로 로컬 포트 OAuth 흐름(`InstalledAppFlow`)을 돌려 Calendar 전체 스코프 토큰을 얻고, `oauth` 파일에 pickle로 저장·재사용하며, 옛 JSON 토큰을 pickle로 이전하고, `init`과 `util inspect-auth`를 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 인증이 필요한 시점은 세 곳이다. (a) `gcalcli init`은 `GoogleCalendarInterface`를 `do_eager_init=False`로 만들고 곧바로 `SetupAuth()`를 부른다(R-01). (b) 그 밖의 gcal 커맨드는 생성자에서 `_get_cached()`를 부르고, **캘린더 캐시가 없을 때만** `get_cal_service()` → `_google_auth()`로 인증에 이른다(R-02). (c) 이미 만들어진 인터페이스에서 `get_cal_service()`를 처음 부르는 모든 호출(이벤트 조회 등)도 같은 경로다.
2. `_google_auth()`는 메모리의 `credentials`가 없으면 `_load_credentials()`로 `oauth` 파일(경로는 [config-resolution](config-resolution.md) R-13이 정한다)을 읽는다(R-03). 파일이 없으면 `"Not yet authenticated."`를 출력하고 `SetupAuth()`로 흐름을 자동 시작한다(R-02).
3. `_load_credentials()`는 파일을 pickle로 읽고, `UnpicklingError`/`EOFError`면 옛 JSON 형식으로 다시 읽어 `Credentials`로 바꾼 뒤 **같은 경로에 pickle로 덮어쓴다**(R-04~R-06). 둘 다 실패하면 안내문을 stderr에 내고 원래 예외를 다시 던진다(R-05).
4. `SetupAuth()`: 이미 토큰이 있으면 덮어쓸지 묻고(`y`만 수락, R-07), 없으면(또는 `y`) 안내문 출력 → 없는 client-id/secret은 `input()`으로 묻고 → `auth.authenticate()` 호출(R-08, R-09).
5. `authenticate()`는 `InstalledAppFlow`로 임의의 빈 포트에서 로컬 서버를 열고(브라우저는 열지 않는다) 사용자가 URL을 열어 승인하길 기다린다. 포트 충돌(errno 98)이면 최대 5회까지 다른 포트로 재시도한다(R-10, R-11). `--noauth_local_server`이면 원격 포트 전달 안내를 매 시도마다 먼저 출력한다(R-12).
6. 받은 `Credentials` 객체를 `oauth` 파일에 pickle로 저장한다(R-13). 그 뒤 `refresh_if_expired`를 한 번 부른다(R-14).
7. `get_cal_service()`가 `build('calendar', 'v3', credentials=...)`로 API 서비스 객체를 만들어 인터페이스에 보관한다(R-15). 이후 토큰 만료 갱신은 코드가 아니라 google-auth/googleapiclient가 메모리에서 처리하고 파일에는 다시 쓰지 않는다(R-14).
8. `gcalcli util inspect-auth`는 gcal 객체 없이 `oauth` 파일을 읽어 메타데이터만 출력한다(R-16~R-18).

### 1.2 범위·통합 지점 [필수]
- 제공: 첫 인증·재인증 흐름(`init`, 자동 트리거), 토큰 저장·재사용, 옛 JSON 토큰 이전, `--noauth_local_server` 안내, `util inspect-auth`, `get_cal_service()`(API 서비스 객체 생성·보관).
- 제외: `oauth`·`cache` 경로 후보·legacy(`~/.gcalcli_oauth`) 이동 규칙([config-resolution](config-resolution.md) R-13 소유). 이 스펙은 `data_file_path('oauth')`가 돌려준 **경로 하나**를 소비한다. 캘린더 API 호출 본문(`calendarList().list`, 이벤트 API)은 [calendar-selection](calendar-selection.md)과 이후 스펙 소유. `--client-id`가 `config.toml`의 `[auth] client-id`에서 오는 합성 규칙은 config-resolution 소유다(이 스펙은 최종 `options['client_id']`·`options['client_secret']`만 읽는다).
- 외부 의존: `google_auth_oauthlib.flow.InstalledAppFlow`(`from_client_config`, `run_local_server`), `google.oauth2.credentials.Credentials`, `google.auth.transport.requests.Request`, `googleapiclient.discovery.build`(Calendar v3 discovery 문서를 가져온다), 표준 `pickle`·`socket`. `pyproject.toml`은 `google_auth_oauthlib`·`google-api-python-client>=1.4`를 버전 상한 없이 의존으로 적는다. 이 분석 환경에는 이 라이브러리들이 없다(`ModuleNotFoundError: google`).
- 소유 상태·부작용: ① `oauth` 파일 생성·덮어쓰기·`.bak` 이름 변경 ② `SetupAuth`의 재인증이 `cache` 파일을 삭제(R-07) ③ 인스턴스 속성 `credentials`, `cal_service`(1.3) ④ stdout·stderr 안내문, stdin 입력. 네트워크: 승인 URL(사용자의 브라우저), 로컬 HTTP 서버, 토큰 교환·갱신(Google).

### 1.3 인터페이스와 데이터 의미 [필수]
| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `GoogleCalendarInterface.credentials` | `Credentials` object or None | 클래스 기본값 None, 인스턴스마다 `_load_credentials`/`SetupAuth`가 채운다. 프로세스 수명. `_google_auth()`가 반환하는 값 |
| `GoogleCalendarInterface.cal_service` | googleapiclient `Resource` or None | 첫 `get_cal_service()`에서 한 번 만들고 재사용. userless 모드면 만들지 않고 `None`을 반환(R-15) |
| `GoogleCalendarInterface.userless_mode` | bool | 생성 인자. 환경변수 `GCALCLI_USERLESS_MODE`가 비어 있지 않으면 `cli.main`이 True로 넘긴다(`cli.py:231`). 테스트용 우회 |
| `oauth` 파일 | pickle 직렬화된 `google.oauth2.credentials.Credentials` 하나 | 기록 시 `pickle.dump(credentials, f)`(기본 프로토콜). 파일 권한을 따로 설정하지 않는다(프로세스 umask). 내용에 `refresh_token`·`client_secret`이 들어간다(추론: `Credentials`가 보관하는 필드. 코드는 `creds_from_legacy_json`이 넘기는 키로만 확인) |
| 옛 `oauth` JSON(legacy) | JSON object | 키 중 `access_token`(필수), `client_id`, `client_secret`, `refresh_token`, `token_uri`, `scopes`만 사용(C-01). 나머지(`token_expiry`, `id_token`, `_class` 등)는 버린다 |
| OAuth client 설정 | `installed` 형식 dict | `auth_uri=https://accounts.google.com/o/oauth2/auth`, `token_uri=https://oauth2.googleapis.com/token`, `redirect_uris=["http://localhost"]` 고정. 사용자 값은 `client_id`, `client_secret`뿐(C-01) |
| 스코프 | 문자열 하나 | `https://www.googleapis.com/auth/calendar`(Calendar 읽기·쓰기 전체). 로드한 토큰의 스코프와 이 값을 비교하지 않는다 |
| `--client-id` / `--client-secret` | string, 기본 None | 최종 options의 `client_id`·`client_secret`. secret은 `config.toml`로 설정할 수 없다(`config.py` docstring) |
| `--noauth_local_server` | flag, dest `auth_local_server`, 기본 True | **철자는 밑줄**(argparsers.py:27). 켜면 `auth_local_server=False`. 하이픈 철자 `--noauth-local-server`는 option이 아니다(R-12) |
| `auth.authenticate(client_id, client_secret, printer, local)` | → `Credentials` | 로컬 서버 흐름. 예외는 R-11 |
| `auth.refresh_if_expired(credentials)` | → None | `credentials.expired`가 참이면 `credentials.refresh(Request())`. 결과를 저장하지 않는다 |
| `auth.creds_from_legacy_json(data)` | dict → `Credentials` | C-01. `data['access_token']` 없으면 `KeyError` |
| `utils.inspect_auth()` | → ordered dict | 키 순서 `path`, `format`, `client_id`, `scopes`, `valid`, `token_state`, `expiry`, `expired`(자격 객체에 속성이 있는 것만). 값은 `str`화 없이 원본 객체 |

출력 채널: 안내·프롬프트는 `printer.msg`(stdout), 오류는 `printer.err_msg`(stderr, brightred), 디버그는 `printer.debug_msg`(stderr, yellow). 입력은 모두 `input()`(echo 켜짐, secret도 숨기지 않는다).

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `gcalcli init` | `config`·`util`이 아니므로 gcal 객체를 `do_eager_init=False`로 만들어 `_get_cached()`를 건너뛰고(그래서 캘린더 목록·API 호출 없음) `SetupAuth()`만 실행한다. `init`은 인증 외 부작용이 없다. `GcalcliError`는 stderr 메시지 후 exit 1(`cli.py:393-395`) | 코드 확인 |
| R-02 | `init`이 아닌 gcal 커맨드(예: `list`, `agenda`) | 생성자가 `_get_cached()`를 부른다(userless가 아닐 때). **캐시 파일을 읽어 성공하면 인증 코드가 전혀 실행되지 않는다**(토큰 파일이 없어도). 캐시를 못 읽을 때(없음·`--nocache`·`--refresh`)만 `get_cal_service()` → `_google_auth()`가 불리고, 토큰 파일이 없으면 `Not yet authenticated.\n`(stdout) 후 `SetupAuth()`를 자동 실행한다(주석: 나중에 "init을 실행하라"는 실패로 바뀔 수 있다는 TODO). `docs/api-auth.md`의 "`--client-id=... list`가 안내를 시작한다"는 캐시가 없을 때만 참이다 | 코드 확인 |
| R-03 | `_load_credentials()`, `oauth` 파일 경로 = `data_file_path('oauth')` | userless면 즉시 반환(자격 None). 경로가 존재하지 않으면 반환하고 `credentials`는 None으로 남는다(오류 아님). 존재하면 `rb`로 열어 `pickle.load`를 시도. 성공하면 반환값을 **타입·필드 검증 없이** `self.credentials`로 쓴다. `data_file_path` 호출은 legacy 이동 같은 경로 규칙의 부작용을 그대로 일으킨다(config-resolution R-13) | 코드 확인 |
| R-04 | pickle 읽기가 `UnpicklingError` 또는 `EOFError` | 파일 처음으로 `seek(0)` 후 `json.load` → `creds_from_legacy_json`. 성공하면 `needs_write=True`로 `oauth` 파일 부모 디렉터리를 만들고 같은 경로에 `pickle.dump`로 **덮어쓴다**(이전 후 `.bak` 같은 백업은 없다). 메시지는 없다 | 코드 확인 |
| R-05 | 위 JSON 폴백이 `OSError`/`ValueError`(JSON 파싱 오류, 유니코드 오류 포함)/`EOFError`로 실패 | `credentials`가 비어 있으면 stderr(`err_msg`)에 `Couldn't parse <경로>.\nThe file may be corrupt or be incompatible with this version of gcalcli. It probably has to be removed and provisioning done again.\n`를 출력하고 **원래의 pickle 예외를 다시 던진다**. `GcalcliError`가 아니므로 `main`이 잡지 않아 traceback으로 종료한다. 자동 재인증으로 넘어가지 않는다 | 코드 확인 |
| R-06 | R-04/R-05에서 처리되지 않는 실패 | `except` 목록 밖의 예외는 가공 없이 전파한다: JSON은 유효하지만 `access_token` 키가 없으면 `KeyError`, JSON이 object가 아니면 `AttributeError`(`data.items`), pickle이 `AttributeError`·`ImportError`·`ModuleNotFoundError` 등을 내면(예: 다른 버전 google-auth 클래스 경로) 그대로. 이들은 안내문 없이 traceback | 코드 확인(전파 경로) / 추론(어떤 pickle 오류가 실제로 나는지) |
| R-07 | `SetupAuth()` 시작: `_load_credentials()` 후 `credentials`가 이미 있음 | stdout에 `Credentials already configured. `, 이어서 magenta로 `Ignore and refresh? [N]o [y]es: `를 내고 `input()`을 읽는다. 값이 **정확히 `y`/`Y`**(`val.lower()=='y'`)이고 userless가 아니면: `oauth` 파일이 있으면 `.with_suffix('.bak')`로 이름을 바꾸고(디버그 메시지 `Moving existing oauth creds aside from ... to ...`; 파일명이 `oauth`라 `oauth.bak`), `data_file_path('cache')`의 **캐시 파일을 삭제**(`unlink(missing_ok=True)`)하고 `credentials=None`으로 새 흐름을 시작한다. 그 밖의 입력(빈 줄, `yes`, `n` 모두)은 `Aborting, keeping existing credentials...`(개행 없음)를 출력하고 갱신 없이 반환한다. 이 반환은 `refresh_if_expired`도 건너뛴다. EOF 입력이면 `EOFError` 전파 | 코드 확인 |
| R-08 | 토큰이 없을 때의 `SetupAuth` 안내 | 순서대로 stdout에: `Starting auth flow...`(yellow), `NOTE: See https://github.com/insanum/gcalcli/blob/HEAD/docs/api-auth.md for help/troubleshooting.`. `options['client_id']`·`['client_secret']` 중 **`is None`인 것**만 `missing_info`에 모아 `You'll be asked for a client_id and client_secret that you should have set up for yourself in Google dev console.`(해당 항목만 `and`로 연결)를 출력하고 `Client ID: `/`Client Secret: `(magenta)로 `input()`을 받는다. 입력값은 비어 있어도 검증하지 않고 그대로 쓴다(빈 문자열 `--client-id ''`는 None이 아니므로 묻지 않는다). 이어서 `Now click the link below and follow directions to authenticate.`(yellow), `You will likely see a security warning page and need to click "Advanced" and "Go to gcalcli (unsafe)" to proceed.` | 코드 확인 |
| R-09 | userless 모드의 `SetupAuth` | R-08의 안내와 프롬프트를 다 출력한 뒤 `Skipping actual authentication (running in userless mode)`를 내고 `authenticate`·저장 없이 반환(`credentials`는 None) | 코드 확인 |
| R-10 | `authenticate()`의 flow 구성 | `InstalledAppFlow.from_client_config(client_config=C-01의 installed dict, scopes=[calendar])`. 서버 쪽 동의 화면·client 종류(Desktop app)는 사용자가 Cloud Console에서 설정한다(`docs/api-auth.md`). 코드는 PKCE·`access_type`·`prompt` 같은 추가 인자를 넘기지 않는다(라이브러리 기본값) | 코드 확인(인자) / 미확인(라이브러리 기본 동작 U-02) |
| R-11 | 로컬 서버 시도 루프(C-01) | `credentials is None`인 동안 반복: `_free_local_port()`(`bind(('',0))`로 OS가 정한 빈 포트 번호를 얻고 소켓을 닫음. 닫은 뒤 다시 바인드하므로 경쟁 가능)로 포트를 정하고 `flow.run_local_server(open_browser=False, port=port)`를 부른다(URL 출력·승인 대기는 라이브러리 몫). `OSError`의 `errno == 98`이고 시도 횟수가 4 미만이면 stdout에 `Port {port} in use, trying another port...`(개행 없음)를 내고 횟수를 올려 **새 포트로 재시도**한다. 즉 최대 5번 시도하고 5번째 실패는 그대로 던진다. errno가 98이 아니면(다른 `OSError`) 즉시 던진다. `98`은 Linux의 `EADDRINUSE` 값이다(다른 OS는 값이 달라 재시도하지 않는다: 추론). `RecursionError`는 `OSError('Failed to fetch credentials. If this is a nonstandard gcalcli install, please try again with a system-installed gcalcli as a workaround.\nDetails: https://github.com/insanum/gcalcli/issues/735.')`로 바꿔 던진다. 사용자 거부·시간 초과·토큰 교환 실패는 라이브러리 예외로 전파되고 재시도하지 않는다 | 코드 확인 |
| R-12 | `--noauth_local_server`(`auth_local_server=False`) | `local=False`면 시작 시 `Note: Behavior of the `--noauth-local-server` option has changed! Starting local server, but providing instructions for connecting to it remotely...\n`를 출력한다. 서버는 여전히 이 컴퓨터에서 열린다. **시도마다**(포트 재시도 포함) 그 포트 번호로 `Option 1 (outbound):`(yellow) + `ssh username@host -L <port>:localhost:<port> BROWSER=open $BROWSER 'https://the-url-below'` 안내, `Option 2 (outbound):`(yellow) + `ssh username@host -fN -R <port>:localhost:<port> ; BROWSER=open $BROWSER https://the-url-below'` 안내(두 번째 명령의 따옴표는 원문 그대로 앞쪽 따옴표가 빠져 있다)를 출력한다. 정확한 문장은 C-01. 옵션 철자는 `--noauth_local_server`(밑줄)뿐이다: 하이픈 철자를 주면 서브커맨드 파서에 없는 인자가 되고, 전역 옵션 재해석(`handle_unparsed`)에서도 모르는 인자라 argparse 오류(exit 2)가 난다(최소 argparse 재현으로 미인식 확인, gcalcli 전체 실행은 하지 않음). 안내문의 하이픈 철자와 옵션 철자가 불일치한다 | 코드 확인 + 부분 재현 |
| R-13 | `authenticate`가 `Credentials`를 반환 | `oauth_filepath.parent.mkdir(parents=True, exist_ok=True)` 후 `open(path,'wb')`로 **직접 덮어써** `pickle.dump`(임시 파일·원자적 교체·권한 설정 없음, 쓰다가 중단되면 파일이 깨질 수 있다: 추론). 경로는 `SetupAuth` 시작 시 `data_file_path('oauth')`로 한 번 얻은 값(`functools.cache`라 같은 인스턴스·같은 이름은 같은 결과) | 코드 확인 / 추론(중단 시 상태) |
| R-14 | 토큰 갱신 | gcalcli 코드가 `refresh_if_expired`를 부르는 곳은 `SetupAuth` 끝 한 곳뿐이고, 그 결과를 **파일에 다시 쓰지 않는다**. `_google_auth`가 파일에서 로드한 토큰에는 코드가 갱신을 호출하지 않으므로, 만료된 access token의 갱신은 `build(..., credentials=...)`가 만든 HTTP 클라이언트에 맡긴다(라이브러리 동작은 U-01). `pickle.dump`는 로드·인증 직후 한 번뿐이라 갱신된 토큰은 프로세스 종료와 함께 사라진다. `SetupAuth`가 `y`로 갱신 취소(R-07)하면 `refresh_if_expired`를 건너뛴다. 갱신 실패(`RefreshError` 등)를 잡는 코드는 이 레포의 `gcalcli/*.py` 어디에도 없다(`grep -rn 'RefreshError\|invalid_grant' gcalcli/*.py` 0건) → 전파. 성공 시 stderr에 디버그 `Successfully loaded credentials\n` | 코드 확인 / 추론(실제 갱신 동작은 외부 U-01) |
| R-15 | `get_cal_service()` | `cal_service`가 없고 userless가 아니면 `build(serviceName='calendar', version='v3', credentials=self._google_auth())`를 호출해 속성에 저장한다. userless면 `None` 반환. 같은 인스턴스는 이후 재사용한다. `get_events()`는 `get_cal_service().events()` | 코드 확인 |
| R-16 | `util inspect-auth`(`cli.py:377-391`) | gcal 객체 없이 `utils.inspect_auth()`를 호출한다. 경로 후보는 `env.data_file_paths('oauth', env.config_dir())`로, **`--config-folder` 옵션을 쓰지 않고** 환경 규칙의 `config_dir()`만 쓴다(`GoogleCalendarInterface.data_file_path`는 옵션을 쓰므로 둘이 다를 수 있다). 후보 중 **존재하는 첫 경로**를 `path`(`shorten_path`)로 기록하고 legacy 이동은 하지 않는다. 존재하는 후보가 없으면 빈 dict | 코드 확인 |
| R-17 | inspect-auth의 파일 해석 | `pickle.load` 성공이면 `format='pickle'`, `UnpicklingError`/`EOFError`이면 JSON 폴백(성공 시 `format='json'`, 파일은 **다시 쓰지 않는다**). 둘 다 실패(`OSError`/`ValueError`/`EOFError`)하면 `format='unknown'`. 이어 `creds`에 `client_id`, `scopes`, `valid`, `token_state`, `expiry`, `expired` 속성이 **있는 것만** 이 순서로 dict에 넣는다(속성 유무는 `hasattr`, 라이브러리 버전에 따라 `token_state`가 없을 수 있다: 미확인). 토큰 값 자체는 출력하지 않는다 | 코드 확인 |
| R-18 | inspect-auth 출력·실패 | 각 항목을 `printer.msg("<k>: <v>\n")`로 stdout에 출력. `format`이 `unknown`이 아니면 추가로 빈 줄 + ``The grant's entry under https://myaccount.google.com/connections should also list creation time and other info Google provides on the access grant.`` + `Hint: filter by "Access to: Calendar" if you have trouble finding the right one.`를 출력. 파일이 없어 dict가 비면(`format` 키 없음) stderr에 `No existing auth token found\n`만 내고 **exit 0**. **파일은 있으나 해석 불가(format='unknown')인 경우**: `creds`가 한 번도 대입되지 않은 상태에서 `hasattr(creds, k)`를 평가해 `UnboundLocalError`가 나고 traceback으로 종료한다(코드 경로 추적. `else: No existing auth token found` 분기는 `unknown`일 때도 도달하지 못한다). JSON이 유효하나 `access_token`이 없을 때 `KeyError`도 잡히지 않는다 | 코드 확인(경로 추적, 실행은 하지 않음) |
| R-19 | 위험한 입력 | `oauth` 파일은 `pickle.load`로 읽으므로 신뢰할 수 없는 파일이면 임의 코드가 실행된다(`_load_credentials`, `inspect_auth` 둘 다). 코드에 방어가 없다 | 코드 확인 |
| R-20 | 프로세스 종료 규칙 | `GcalcliError`만 `main`이 잡아 stderr 출력 + exit 1. 이 스펙의 실패(R-05, R-06, R-11, R-14, R-18의 예외)는 모두 `GcalcliError`가 아니므로 traceback과 exit 1이다. SIGINT는 `Signal caught, bye!`(stderr) + exit 1(`cli.py:450-455`) | 코드 확인 |

- 불변식: 로컬 서버 흐름의 결과물은 항상 이 레포가 정한 단일 스코프 `calendar`뿐이다. `oauth` 파일은 pickle 형식으로만 **쓰이며**(JSON은 읽기 전용 이전 대상), 쓰기는 R-04, R-13 두 곳뿐이다(`grep -n 'pickle.dump' gcalcli/gcal.py` → 226, 304, 362: 362는 cache).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-14, R-06 | `build(credentials=Credentials)`가 만든 클라이언트가 만료·미설정(`expiry=None`) access token을 어떻게 갱신하는가(요청 전 `expired` 검사 vs 401 응답 후 갱신)? 옛 JSON에서 이전한 `Credentials`는 `expiry`가 비어 있어 `expired`가 거짓이다. `refresh_token`·`client_secret` 없는 자격은? | 재구현이 같은 라이브러리를 쓰면 무관하나, 직접 구현하면 만료 처리·재저장 정책을 정해야 한다. 이전 직후 첫 호출이 실패하는지 | google-auth·google-api-python-client 소스 또는 실제 만료 토큰으로 실행(이 환경에 미설치, 계정 필요) |
| U-02 | R-10~R-12 | `run_local_server`의 기본 동작: 바인드 호스트(`localhost` vs 모든 인터페이스), 타임아웃, 사용자 거부·`state` 불일치 시 반환값/예외, 성공 페이지, `refresh_token` 발급 조건(`access_type=offline`·`prompt=consent`) | 원격 포트 전달 안내가 실제로 통하는지, 첫 승인에서 `refresh_token`이 오는지 | google_auth_oauthlib 소스 확인 또는 실제 승인 실행 |

- 확인 한계: Google 계정과 Cloud OAuth client가 필요하므로 `init`·승인·토큰 교환·갱신·API 호출은 실행하지 못했다. 위 규칙은 코드 경로 읽기와, argparse 철자 최소 재현(R-12)에 한정된다. 이 환경에 `google*` 패키지가 없어 `Credentials` 필드·pickle 호환성은 코드가 넘기는 키로만 확인했다. 원본 테스트 `tests/test_auth.py::test_legacy_certs`는 열람만 했고 실행하지 않았다. Google 쪽(동의 화면 "unsafe" 경고, 테스트 사용자 제한, 토큰 유효기간)은 `docs/api-auth.md`의 주장이며 코드로 검증하지 못했다(미확인).

### 1.5 필수 코드 참조 [필수]
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/auth.py:1-96` 전체 | `authenticate`(client_config·스코프·로컬 서버 루프·포트 재시도·`--noauth_local_server` 안내문 정확한 문장), `_free_local_port`, `refresh_if_expired`, `creds_from_legacy_json`(허용 키 5개) | R-04, R-10~R-12, R-14 |
| C-02 | `gcalcli/gcal.py:178-226` `_google_auth`, `_load_credentials` | 자동 트리거와 로드·폴백·오류 분기 | R-02~R-06 |
| C-03 | `gcalcli/gcal.py:228-307` `SetupAuth` | 덮어쓰기 질문, `.bak`·캐시 삭제, 프롬프트 순서·문구, 저장 | R-07~R-09, R-13, R-14 |
| C-04 | `gcalcli/gcal.py:309-320` `get_cal_service`, `get_events` | 서비스 생성·보관 | R-15 |
| C-05 | `gcalcli/utils.py:242-276` `inspect_auth` | 경로 선택, 형식 판별, 출력 키 목록·순서 | R-16~R-18 |
| C-06 | `gcalcli/cli.py:244-247`, `377-395` | `init` 분기, `util inspect-auth` 출력, 오류 처리 | R-01, R-16, R-18, R-20 |

`data_file_path`(`gcal.py:151-176`)와 `env.data_file_paths`는 [config-resolution](config-resolution.md) C-01·C-11을 쓴다. 이 스펙의 C-ID 범위에서 쓰이는 프로젝트 내부 helper는 `Printer.msg/err_msg/debug_msg`(출력 채널은 1.3), `utils.shorten_path`(경로 표시용 홈 축약)뿐이다.

### 1.6 수락 사례 [필수]
출처: 사례별 표기. 모두 실제 Google 호출 없이 코드 경로에서 도출했으며 실행하지 않았다(대체: 네트워크·계정 없음 → 라이브러리 동작과 실제 승인은 검증하지 않는다).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | `list`, 캐시 파일 있음, `oauth` 파일 없음 | 인증 안내 없이 목록 표시(캐시에서). 구현에서 도출 |
| T-02 | R-02, R-08, R-13 | `--client-id X list --nocache`, `oauth` 없음, 입력 `secret` | `Not yet authenticated.` → 안내문 → `Client Secret: `만 묻고(Client ID는 이미 있음) → 승인 → `oauth` pickle 생성 → 목록. 구현에서 도출 |
| T-03 | R-04 | `oauth`가 `tests/data/legacy_oauth_creds.json`(JSON)이고 `get_cal_service()` 호출 | 파일이 pickle로 바뀌어 `pickle.load`가 성공하고 서비스 객체가 만들어진다. 원본 테스트 열람(`tests/test_auth.py`, 실행 안 함; 테스트는 `data_file_path`를 스텁해 경로 규칙은 검증하지 않는다) |
| T-04 | R-05 | `oauth` 내용이 `garbage` | stderr에 `Couldn't parse ...` 후 `UnpicklingError` traceback, exit 1, 파일은 그대로. 구현에서 도출 |
| T-05 | R-07 | `init`, 토큰 있음, 입력 `yes` | `Aborting, keeping existing credentials...` 후 종료, 파일 변경 없음(`y`만 갱신). 구현에서 도출 |
| T-06 | R-07 | `init`, 토큰 있음, 입력 `y` | `oauth`→`oauth.bak`, `cache` 파일 삭제, 새 인증 흐름. 구현에서 도출 |
| T-07 | R-11 | `authenticate`에서 첫 포트가 errno 98 | `Port N in use, trying another port...` 출력 후 새 포트로 재시도, 5번째까지 실패하면 `OSError` 전파. 구현에서 도출 |
| T-08 | R-12 | `--noauth-local-server`(하이픈) | argparse "unrecognized arguments" 오류, exit 2. 최소 argparse 재현으로 확인 |
| T-09 | R-16, R-18 | `oauth` 없음, `util inspect-auth` | stderr `No existing auth token found`, exit 0, stdout 비어 있음. 구현에서 도출 |
| T-10 | R-18 | `oauth`가 `garbage`, `util inspect-auth` | `UnboundLocalError` traceback. 구현에서 도출(경로 추적) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (repo@405639c `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `cli.py:229-249`, `argparsers.py:459-464`, `gcal.py:94-102` | 줄 추적. 문서·README(`gcalcli --client-id=... init`)와 일치 |
| R-02 | `gcal.py:99-100,322-362,309-317,178-189`, `docs/api-auth.md:49-63`, `README.md:112-127` | 줄 추적. 캐시 읽기 성공 시 `return`(339행)으로 `get_cal_service` 미호출. 문서와 구현 차이: 문서는 첫 `list`가 항상 인증을 안내한다고 읽히지만 캐시가 있으면 그렇지 않다. `grep -n 'get_cal_service()\|_google_auth()' gcalcli/*.py`로 인증 진입점 전수(호출처는 `gcal.py` 안뿐). 놓칠 가능성: 동적 호출 |
| R-03 | C-02, `tests/conftest.py:177-191`(테스트가 `data_file_path`를 스텁) | 줄 추적 |
| R-04 | C-02 | 줄 추적. 원본 테스트 `tests/test_auth.py:12-28`와 `tests/data/legacy_oauth_creds.json`(oauth2client 형식 JSON, `_class: OAuth2Credentials`)로 사용처 확인. 실행 안 함 |
| R-05 | C-02(`gcal.py:206-221`) | 줄 추적. 예외 이름은 `pickle` 모듈 문서에 근거(실행 없음) |
| R-06 | C-01(`creds_from_legacy_json`), C-02 | 줄 추적: `data['access_token']`(`auth.py:96`), `data.items()`(`:85`). pickle이 던지는 다른 예외는 코드가 잡지 않는다는 사실만 확인(어떤 상황에서 나는지는 추론) |
| R-07 | C-03(`gcal.py:232-252`), `pathlib.Path.with_suffix` | 줄 추적. `with_suffix('.bak')`가 이름 `oauth`에 대해 `oauth.bak`이 되는 것은 표준 라이브러리 동작(추론, 실행 안 함). 기존 `.bak`이 있을 때의 `rename` 동작은 OS별(POSIX 덮어씀, Windows는 오류)이며 코드는 처리하지 않는다 |
| R-08 | C-03(`gcal.py:254-289`) | 줄 추적 |
| R-09 | C-03(`gcal.py:290-295`) | 줄 추적 |
| R-10 | C-01(`auth.py:12-24`), `docs/api-auth.md` | 줄 추적. 라이브러리 기본값은 미확인(U-02) |
| R-11 | C-01(`auth.py:31-67,70-75`) | 줄 추적. `errno 98`의 OS 의존은 추론(Linux `EADDRINUSE`=98은 일반 지식). `attempt_num < 4` 계산: 0~4번째 시도 중 0~3번째 실패는 재시도, 4번째 실패는 전파 → 총 5회 |
| R-12 | C-01(`auth.py:25-30,36-50`), `argparsers.py:27-34`, `docs/man1/gcalcli.1:17,82`, `tests/cli/__snapshot__/test-02-test_prints_correct_help.snap:3,69`(도움말 스냅샷도 밑줄), `ChangeLog:17`, `cli.py:215-221`·`argparsers.py:357-366` | 줄 추적. 하이픈 철자는 `grep -rn 'noauth' gcalcli docs README.md`로 `auth.py:27`의 메시지 한 곳에만 있음(범위: gcalcli/, docs/, README.md). 재현: 같은 `action='store_false'`·dest를 가진 최소 `argparse` 파서에서 `--noauth-local-server`는 미인식 인자로 남고 `--noauth_local_server`는 인식됨(`python3 -I` 일회성 스니펫, gcalcli 코드는 실행하지 않음). gcalcli 전체 경로에서 exit 2가 되는 것은 `handle_unparsed`의 `parse_args` 동작(argparse 규칙)으로 추론. 안내문의 두 번째 `ssh` 명령은 따옴표가 한쪽만 열려 있다(`auth.py:48-49` 원문) |
| R-13 | C-03(`gcal.py:296-304`) | 줄 추적. `grep -n 'chmod\|os.replace\|tempfile' gcalcli/*.py` → 0건(범위 `gcalcli/*.py`)이라 권한 설정·원자적 교체 없음 |
| R-14 | C-01, C-03(`gcal.py:306-307`), `grep -n 'refresh_if_expired' gcalcli/*.py` → 호출처 `gcal.py:306` 한 곳, `grep -n 'pickle.dump' gcalcli/*.py` → `gcal.py:226,304,362`뿐, `grep -rn 'RefreshError\|invalid_grant' gcalcli/*.py` → 0건 | 줄 추적. 부재 주장: 범위 `gcalcli/*.py`, 기준 SHA, 놓칠 가능성은 라이브러리 내부의 자동 갱신·저장(코드 밖). ChangeLog 4.5.0의 "Improve auth issue handling and error messaging for invalid OAuth token issues"가 있으나 해당 처리 코드는 이 범위에서 찾지 못했다(찾지 못함 ≠ 없음) |
| R-15 | C-04 | 줄 추적 |
| R-16 | C-05(`utils.py:242-249`), C-06, `env.py:15-39`(config-resolution C-01) | 줄 추적. `cli.py:378`가 인자 없이 `inspect_auth()`를 부르는 것과 `utils.py:245`가 `env.config_dir()`를 쓰는 것을 확인 |
| R-17 | C-05(`utils.py:250-276`) | 줄 추적. `token_state`·`expiry` 속성은 설치된 google-auth 버전에 의존(미확인) |
| R-18 | C-05, C-06(`cli.py:377-391`), `printer.py:34-43` | 줄 추적으로 `creds` 미대입 경로 확인(`utils.py:253-266`). 실행은 하지 않았다(google 패키지 없음, `utils`가 `parsedatetime`·`babel` 등을 import해서 이 환경에서 모듈을 불러올 수 없음). 놓칠 가능성: 그 경로의 `creds`가 외부에서 미리 정의되는 경우 없음(함수 지역변수) |
| R-19 | `gcal.py:203`, `utils.py:253` | 줄 추적. 부재 주장("방어 없음"): `grep -n 'pickle' gcalcli/*.py` 전수, `RestrictedUnpickler`·서명 검증 없음 |
| R-20 | `cli.py:393-395,450-455`, `exceptions.py:1-2` | 줄 추적. `grep -n 'GcalcliError' gcalcli/auth.py gcalcli/utils.py` → 0건 |
| T-01~T-10 | 위 R-ID 근거. T-03만 원본 테스트 열람 | 나머지는 구현에서 도출, 실행 없음 |

### 2.4 검토 기록 [필수, ready 스펙]
(`draft`이므로 해당 없음. 작성자 자체 점검: R-02, R-07, R-11, R-12, R-18의 인용 줄을 다시 열어 주장과 맞춰 봤다. 독립 검토와 재구현은 미수행.)

## 적용 메모 [선택]
없음(분석 목적 미정).
