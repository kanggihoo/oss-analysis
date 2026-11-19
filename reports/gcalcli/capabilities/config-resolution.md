---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/cli.py
  - gcalcli/config.py
  - gcalcli/env.py
  - gcalcli/deprecations.py
  - gcalcli/argparsers.py
  - gcalcli/gcal.py
  - gcalcli/utils.py
  - gcalcli/printer.py
  - data/config-schema.json
  - README.md
  - ChangeLog
  - pyproject.toml
depends: []
status: draft
---

# 설정·옵션 해석

> 명령줄 인자, `gcalclirc` 플래그 파일(`@경로`), `config.toml`(pydantic 모델), 환경변수 `GCALCLI_CONFIG`를 합쳐 하나의 argparse namespace(= 이후 모든 서브커맨드가 읽는 options)를 만들고, `config edit`·`util config-schema`와 데이터 파일 경로 규칙을 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 프로세스 시작 시 `get_argument_parser()`가 전역 옵션(`PROGRAM_OPTIONS`)과 deprecated 옵션을 단 parser를 만든다. `--config-folder`의 기본값은 이때 `env.config_dir()`로 정해진다(R-01, R-12).
2. **1차 파싱**: 자동 rc 파일(`~/.gcalclirc`, `<config_dir>/gcalclirc`, 있는 것만)을 `@경로`로 argv 앞에 붙여 `parse_known_args`한다. 목적은 `--config-folder`와 `--noincluderc`(`includeRc`) 값을 알아내는 것이다(R-05).
3. `config_folder`를 `expanduser`하고, rc 경로를 `~/.gcalclirc` + `<config_folder>/gcalclirc`로 다시 계산한다(R-06).
4. `env.config_file()`이 가리키는 `config.toml`을 읽어 `Config`로 검증하고(없으면 기본 `Config()`), namespace로 바꾼다. `week_start`는 따로 빼서 `None`으로 둔다(R-02~R-04, R-09).
5. **2차 파싱**: `includeRc`가 참이면 rc 파일 인자를 argv 앞에 붙이고, config namespace를 시작 namespace로 삼아 다시 `parse_known_args`한다. 이 순서가 우선순위를 만든다(R-07, R-08, R-11).
6. `week_start`가 `None`이면 config 값을 되돌려 넣고, `config_folder`를 다시 `expanduser`한다(R-09).
7. 남은 인자(`unparsed`)는 전역 옵션만 가진 작은 parser로 한 번 더 해석한다(R-16). 이어서 Printer·locale·calendar 목록(`default_calendars`/`ignore_calendars` 반영)을 정한다(R-17, R-18).
8. 서브커맨드가 `config`·`util`이면 gcal 객체 없이 분기해 `config edit`(R-19), `util config-schema`(R-20)를 실행한다. 그 밖의 커맨드는 `**vars(parsed_args)` 전체를 options로 `GoogleCalendarInterface`에 넘기고, 그 안에서 `config_folder`가 데이터 파일 경로 결정에 쓰인다(R-13, R-21).

### 1.2 범위·통합 지점 [필수]
- 제공: 위 합성 규칙, `config.toml` 스키마, `config edit`, `util config-schema`, deprecated 옵션 경고, 데이터 파일 경로 후보와 해소 규칙.
- 제외: 인증 흐름(`auth.py`, `gcal.py`의 `_load_credentials`·`SetupAuth`), 서브커맨드별 동작, 서브커맨드 전용 옵션의 의미(`--details`, `--tsv` 등). `util reset-cache`·`util inspect-auth`는 데이터 파일 경로 규칙을 *소비하는 쪽*이라 R-13에서 호출 사실만 쓰고 동작은 쓰지 않는다. 이유: 요청 경계가 "config edit, util config-schema"까지다.
- 외부 의존: Python `argparse`(subparser가 namespace 값을 덮어쓰는 동작, `fromfile_prefix_chars`, `append` action이 기존 리스트를 복사해 이어 붙이는 동작), `platformdirs`(`user_config_dir`, `user_data_path`), `tomllib`/`tomli`, `pydantic` v2. 이들의 세부 동작은 해당 라이브러리 몫이고, 이 스펙은 gcalcli가 기대하는 결과만 쓴다.
- 소유 상태·부작용: 프로세스 내 parsed namespace(options). 파일 변경은 `config edit`가 `config.toml`(과 상위 디렉터리)을 만드는 것, `data_file_path`가 legacy 데이터 파일을 새 경로로 옮기는 것(R-13) 둘이다. `config.toml`·`gcalclirc`를 읽기만 하고 고쳐 쓰지는 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]
외부 계약(이름은 원문 그대로):

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `GCALCLI_CONFIG` | env, string | 비어 있지 않으면 설정 경로. 기존 **파일**이면 그 파일이 config 파일이고 부모가 config 디렉터리. 그 외(없는 경로 포함)는 **디렉터리**로 보고 `<경로>/config.toml`. `~` 확장 없음(R-01) |
| `--config-folder` | `pathlib.Path`, 기본 `shorten_path(env.config_dir())` | deprecated(help 문구). rc 경로와 데이터 파일 디렉터리에만 영향. `config.toml` 위치에는 영향 없음(R-12) |
| `--noincluderc` | flag, dest `includeRc`, 기본 true | 2차 파싱에서 자동 rc 파일을 빼는 스위치(R-11) |
| `--client-id` / `--client-secret` / `--default-calendar`(dest `default_calendars`, append) / `--calendar`(전역, dest `global_calendars`, append) / `--locale` / `--refresh` / `--nocache` / `--conky` / `--nocolor` / `--lineart` / `--noauth_local_server` | `PROGRAM_OPTIONS` 정의 | 전역 옵션 목록은 C-05. 이 스펙은 값이 합쳐지는 방식만 다룬다 |
| `@경로` | argv 토큰 | argparse 표준 파일 인자(`fromfile_prefix_chars='@'`). 한 줄이 인자 하나(R-10) |
| `config.toml` 섹션 | `[auth] client-id`(string), `[calendars] default-calendars`·`ignore-calendars`(string list), `[output] week-start`(`"sunday"`\|`"monday"`, 기본 `sunday`) | 키는 하이픈 alias만 인식. 모르는 키·섹션은 무시(R-03) |
| config namespace | 속성 `client_id`, `default_calendars`, `ignore_calendars`, `week_start` | `Config.to_argparse_namespace()`의 결과. 하이픈이 아닌 필드명(R-04) |
| `Config.json_schema()` | → map | `util config-schema`가 출력. 커밋된 `data/config-schema.json`과 같다(R-20) |
| `env.data_file_paths(name, config_dir)` | → list of (path, category int) | category 1=config 디렉터리, 0=표준 데이터 디렉터리, -1=legacy(R-13) |
| options | `vars(parsed_args)` | 합성 결과 전체. 서브커맨드 파서가 정의한 옵션도 같은 namespace에 있다 |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `GCALCLI_CONFIG` 해석(C-01) | 미설정 또는 빈 문자열이면 `platformdirs.user_config_dir('gcalcli')`가 config 디렉터리, `<그 경로>/config.toml`이 config 파일. 설정돼 있고 `is_file()`이면 config 파일=그 경로, 디렉터리=부모. 설정돼 있지만 파일이 아니면(없거나 디렉터리) 경로가 디렉터리이고 config 파일은 `<경로>/config.toml`. 값에 `expanduser`를 하지 않는다(셸이 확장하지 않은 `~`는 리터럴 상대경로) | 코드 확인 |
| R-02 | `config.toml` 로드(C-08 174-195행) | 파일 위치는 `env.config_file()`만으로 정해진다(`--config-folder`·rc는 영향 없음). 파일이 있으면 바이너리로 열어 `tomllib.load` → `Config(**dict)`, 없으면 기본 `Config()`. 파싱·검증 오류(`TOMLDecodeError`, pydantic `ValidationError`)는 main에서 잡지 않아 예외가 그대로 전파되고(traceback, 프로세스 종료), 이 경우 서브커맨드 실행·Printer 생성 전에 끝난다 | 코드 확인 (예외 전파는 `try` 부재 확인; 오류 종류는 실행 확인, 한계 참조) |
| R-03 | `Config` 스키마(C-02) | 입력 키는 alias(`client-id`, `default-calendars`, `ignore-calendars`, `week-start`)만 인식한다. 필드명 형태(`client_id`)나 모르는 키·섹션은 오류 없이 무시되어 기본값이 쓰인다. `week-start`는 정확히 `"sunday"`/`"monday"`(소문자)만 허용하고 `"Monday"`·`"tuesday"`는 `ValidationError`. `default-calendars`에 문자열 하나를 주면(리스트가 아니면) `ValidationError`. 섹션을 통째로 생략하면 섹션 기본값 | 코드 확인 + 실행 확인(pydantic 2.13.4, 레포 `config.py` 사본) |
| R-04 | config → namespace(C-02 93-101행) | namespace 속성은 `client_id`, `default_calendars`, `ignore_calendars`, `week_start`(`WeekStart` enum 값). 파일이 없어도 이 네 속성이 모두 있다(기본: `None`, `[]`, `[]`, `SUNDAY`) | 코드 확인 |
| R-05 | 1차 파싱(C-08 159-172행) | 자동 rc 경로 = `~/.gcalclirc`, `env.config_dir()/gcalclirc`(`--config-folder` 아님). 존재하는 것만 `@경로`로 argv 앞에 이 순서대로 붙여 `parse_known_args`. `--noincluderc`가 argv에 있어도 이 단계에서는 rc가 항상 읽힌다. 결과는 `config_folder`·`includeRc`를 얻는 데만 쓰이고 최종 namespace가 아니다. 파싱 중 일반 `Exception`은 `str(e)`를 stderr에, 이어 usage를 출력하고 exit 1. argparse 자체 오류(필수 서브커맨드 누락, 알 수 없는 choice 등)는 `SystemExit(2)`라 이 `except`에 걸리지 않고 argparse가 직접 usage·메시지를 출력하고 exit 2 | 코드 확인 + 실행 확인(argparse 사본) |
| R-06 | 1차 파싱 직후(C-08 174-186행) | `config_folder`가 truthy면 `expanduser`. rc 경로를 재계산: `[~/.gcalclirc, <config_folder>/gcalclirc]` 중 존재하는 것. (`config_folder` 기본값이 항상 truthy라 두 번째 경로는 실질적으로 항상 후보) 코드 주석: rc 파일 안의 `--noincluderc`나 `--config-folder` 재지정은 이상하게 해석될 수 있으니 하지 말라 | 코드 확인 |
| R-07 | 2차 파싱 값 우선순위(C-08 196-204행) | 단일 값 옵션(store·store_const·store_true/false)은 나중에 파싱된 것이 이긴다. 시작 namespace가 config 값이므로 **기본값 < config.toml < `~/.gcalclirc` < `<config_folder>/gcalclirc` < 명령줄 인자** 순이다. (`parse_known_args(argv, namespace=...)`: argparse는 namespace에 이미 있는 속성에는 parser 기본값을 쓰지 않는다. `client_id`가 config에 없을 때 `None`이 되는 것도 이 경로) | 코드 확인 + 실행 확인(argparse 사본) |
| R-08 | 리스트 옵션 합성 | `--default-calendar`는 `append`라 config의 `default-calendars` 리스트를 **대체하지 않고 뒤에 이어 붙인다**(config → rc들 → 명령줄 순서로 누적). 같은 이유로 rc와 명령줄의 `--default-calendar`도 누적. `--calendar`(전역, `global_calendars`)는 config 대응이 없고 rc+명령줄이 누적. `ignore_calendars`는 config 전용(대응 CLI 옵션 없음)이고 R-18에서만 변형 | 코드 확인(append 누적은 실행 확인, 한계 참조) |
| R-09 | `week_start`(C-08 196-206행, C-06) | config의 `week_start`를 변수로 빼고 namespace 값을 `None`으로 만든 뒤 파싱, 파싱 후 `None`이면 config 값을 복원. `--monday`(서브커맨드 `calw`·`calm`의 cal_query 옵션)만 `MONDAY`로 설정하고 CLI에는 "sunday로 되돌리는" 옵션이 없으므로, config가 `monday`면 명령줄로 `sunday`를 지정할 수 없다. 해당 옵션이 없는 서브커맨드에서도 최종 `week_start`는 config 값(기본 `SUNDAY`). 원문 TODO: `# TODO: Figure out why week_start from opts_from_config getting through.` — 저자도 이유를 모른다고 적었다. 우리의 해석(추론): 서브파서가 `--monday`의 기본값 `None`을 namespace에 써 넣어 config 값을 덮어쓰므로(그래서 `argparsers.py`가 이 옵션에 default를 일부러 주지 않았다고 주석), 임시로 `None`을 심고 복원하는 우회로 최종 결과를 맞춘다 | 코드 확인(동작) / 추론(TODO의 원인) |
| R-10 | rc·`@` 파일 형식 | 별도 파서 없이 argparse 기본 규칙: 파일의 **한 줄이 인자 토큰 하나**. 따라서 `--client-id=X`처럼 `=`로 붙여야 하고 `--client-id X`(공백 구분 한 줄)는 한 토큰 `"--client-id X"`가 되어 오류. (README: "long options require an equal sign") `convert_arg_line_to_args`를 오버라이드하지 않았다. 존재하지 않는 rc 경로는 `exists()` 검사로 아예 안 붙인다. 사용자가 직접 쓴 `@경로`가 읽기 실패하면 argparse 오류(exit 2) | 코드 확인 + 실행 확인(argparse 사본) |
| R-11 | `--noincluderc` | dest `includeRc`, `store_false`. 1차 파싱 결과의 `includeRc`가 거짓일 때만 2차 파싱에서 `fromfile_args`를 붙이지 않는다. rc 파일 안에 `--noincluderc`가 있어도 1차 파싱에서 값이 잡혀 같은 효과. 명령줄에만 있는 경우 1차 파싱은 여전히 rc를 읽으므로 rc 파일의 인자 오류는 `--noincluderc`를 줘도 1차에서 난다. `--noincluderc`일 때 2차 파싱의 최종 `config_folder`는 rc 없이 정해진 값(명령줄 또는 기본값)이라, rc가 지정한 `--config-folder`는 최종값에서 빠진다(단 R-06의 rc 경로 재계산은 1차 값을 썼다) | 코드 확인 |
| R-12 | `--config-folder` | `type=pathlib.Path`, 기본값은 **parser 생성 시점의** `shorten_path(env.config_dir())`(홈 아래면 `~/...` 형태 Path). 1차·2차 파싱 후마다 `expanduser`. 영향 범위: ① 2차 rc 후보 `<config_folder>/gcalclirc` ② `GoogleCalendarInterface`의 `options['config_folder']` → 데이터 파일 config 디렉터리 후보(R-13) ③ `util reset-cache`. `config.toml`을 읽는 위치는 바꾸지 **않는다** | 코드 확인 |
| R-13 | 데이터 파일 경로(`oauth`, `cache`)(C-01, C-11) | `data_file_paths(name, config_dir)` 후보 순서: ① `config_dir/name`(config_dir가 있고 **파일이 존재할 때만**, category 1) ② `<platformdirs.user_data_path('gcalcli')>/name`(항상, category 0) ③ `~/.gcalcli_<name>`(존재할 때만, category -1). `GoogleCalendarInterface.data_file_path(name)`은 후보를 순서대로 보고 category ≥ 0이면서 존재하는 첫 경로를 반환. 없으면 legacy(-1)가 있을 때 "Moving ... from legacy path ..." 메시지(stdout) 후 category 0 경로의 부모 디렉터리를 만들고 `shutil.move`로 옮긴 뒤 category 0 경로를 반환. legacy도 없으면 category 0 경로를 반환(파일은 만들지 않음). 결과는 함수 인스턴스 캐시(`functools.cache`). 따라서 config 디렉터리에 데이터 파일이 **이미 있어야** 그쪽을 쓰고, 새 파일은 항상 표준 데이터 디렉터리에 생긴다. gcal 쪽은 `options['config_folder']`(R-12)를, `utils.inspect_auth`는 `env.config_dir()`를 config_dir로 넘긴다(`--config-folder`를 무시) | 코드 확인 |
| R-14 | snake_case deprecated 옵션(C-04) | 전역(main parser): `--client_id`, `--client_secret`. 서브커맨드(color_parser): `--color_owner` `--color_writer` `--color_reader` `--color_freebusy` `--color_date` `--color_now_marker` `--color_border` `--color_title`. 서브커맨드(remind_parser): `--default_reminders`. 사용하면 stderr에 `WARNING: <옵션> has been deprecated and will be removed in a future release.` + `Please use "<옵션에서 _를 -로 바꾼 것>", instead.`(brightred, 모듈 전역 `Printer()` 기본 설정이라 `--nocolor`와 무관하게 색 코드 포함)를 출력하고 값은 새 옵션과 같은 dest에 저장한다(`--client_id`→`client_id` 등). 이름이 `_`에서 `-`로 바뀌었을 뿐이라 dest가 같다. 값 타입은 `BASE_OPTS`가 정한다(program: str, color: `valid_color_name`, remind: store_true 변형) | 코드 확인 |
| R-15 | camelCase deprecated 옵션(C-04) | `--configFolder`, `--defaultCalendar`는 경고 메시지에 `CAMELS` 표의 새 이름(`--config-folder`, `--default-calendar`)을 제안하지만, **값은 새 옵션으로 변환되지 않는다**. argparse가 dest를 `configFolder`·`defaultCalendar`로 만들고 코드 어디서도 읽지 않으므로 효과가 없다. `OPTIONS`의 `'action': DeprecatedAppend`도 `parser_allow_deprecated`가 `BASE_OPTS`의 action만 쓰기 때문에 사용되지 않는다(실제 action은 `DeprecatedStore`). 즉 이 옵션은 "경고만 하고 무시"된다 | 코드 확인 (부재 주장: 2.1 참고) |
| R-16 | 남은 인자 재해석(C-07, C-08 215-221행) | 2차 파싱 후 `unparsed`가 비어 있지 않으면 `PROGRAM_OPTIONS`만 가진 새 `ArgumentParser`로 `parse_args(unparsed, namespace=parsed_args)`. 서브커맨드 뒤에 놓인 전역 옵션(예: `agenda --client-id X`처럼 agenda 파서가 모르는 전역 옵션)을 구제하는 장치. deprecated 옵션은 이 parser에 없다. 여기서 알 수 없는 인자는 argparse 오류로 exit 2, 일반 `Exception`은 stderr+usage 후 exit 1 | 코드 확인 |
| R-17 | 옵션 확정 후 즉시 처리(C-08 210-227행) | `Printer(conky, use_color=color, art_style=lineart)` 생성. `--locale`이 비어 있지 않으면 `utils.set_locale`, `ValueError`는 stderr에 메시지만 내고 계속 진행 | 코드 확인 |
| R-18 | calendar 목록 확정(C-09, C-10) | 서브커맨드에 `calendar`/`calendars` 속성이 하나도 없으면 `[]` 반환(`ignore_calendars` 처리도 건너뜀). 단일형(`calendar`: `agendaupdate`·`quick`·`add`·`import`)은 `calendars=[calendar]`로 반영. 명시된 `calendars`가 비었으면 `global_calendars` → `default_calendars` 순으로 첫 비어 있지 않은 목록을 쓰되, 단일형인데 목록 길이가 2 이상이면 stderr 디버그 메시지를 내고 그 목록은 건너뛴다. 이름은 `name#color`로 해석(마지막 이스케이프되지 않은 `#` 뒤가 유효 색 이름일 때만 색, 아니면 전체가 이름이며 디버그 메시지). 마지막으로 `ignore_calendars`에서 명시적으로 고른 이름을 **제자리(`[:]`)로 제거**한다. 단일형에서 `calendars`가 2개 이상이라는 오류 분기(`Multiple target calendars specified!`)는 현재 parser들로는 도달할 수 없다(추론) | 코드 확인 / 추론(도달 불가) |
| R-19 | `config edit`(C-12) | gcal 객체를 만들지 않는다. `Launching <shorten_path(config_file)> in a text editor...`를 stdout에 출력. 파일이 없으면 부모 디렉터리를 `parents=True, exist_ok=True`로 만들고 `EMPTY_CONFIG_TOML`(`#:schema <URL>` 한 줄 + 빈 줄)을 쓴다. 이어 `utils.launch_editor`: Windows는 `os.startfile(path,'edit')`, 그 외는 `editor` → `$EDITOR` → `xdg-open` → `open` 순으로 `subprocess.call`, `OSError`면 다음 후보, 모두 실패하면 `OSError('No editor/launcher detected ...')`(main이 `GcalcliError`만 잡으므로 전파). 파일 위치는 R-01의 `env.config_file()` | 코드 확인 |
| R-20 | `util config-schema`(C-12, C-03) | gcal 객체 없이 stderr에 안내 디버그 메시지, stdout에 `json.dumps(Config.json_schema(), indent=2)` 출력. 스키마는 pydantic `model_json_schema()` 결과를 `$schema, title, description, type, items, $defs, properties` 순으로 재정렬(나머지 키는 정렬). 레포의 `data/config-schema.json`과 (pydantic 2.13.4에서) 문자열이 같다 | 코드 확인 + 실행 확인(한계 참조) |
| R-21 | 서브커맨드 경계 | `command`가 `config`·`util`이면 `gcal=None`. 그 밖의 모든 커맨드는 R-07의 최종 namespace 전체를 `**vars(parsed_args)`로 `GoogleCalendarInterface`에 options로 전달(`do_eager_init`은 `command != 'init'`). 즉 이 스펙의 합성 결과가 서브커맨드 스펙들의 공통 입력 | 코드 확인 |

- 불변식: 최종 우선순위는 단일 값 옵션에서 R-07 순서를 따른다(`week_start`는 R-09 예외). 리스트 `append` 옵션은 우선순위가 아니라 누적(R-08).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-01, R-13 | `platformdirs.user_config_dir('gcalcli')`·`user_data_path('gcalcli')`가 OS별로 정확히 어떤 경로인가(Linux의 `XDG_*` 처리, macOS·Windows 경로)? | 기본 config·데이터 디렉터리 값. Python 재사용이면 라이브러리가 해결하지만 다른 언어 구현이면 경로를 정해야 한다 | platformdirs 소스·문서 확인 또는 각 OS에서 실행(이 환경에는 platformdirs 미설치) |

- 확인 한계:
  - `gcalcli` 전체는 실행하지 못했다(이 환경에 `platformdirs` 등 의존이 없어 import 불가). 대신 ① `config.py`를 `/tmp`로 복사해 pydantic 2.13.4로 R-03·R-04·R-20을 실행했고, ② argparse 동작(R-05·R-07~R-10, R-15의 dest)은 같은 구조의 최소 parser를 **Python 3.14.8**에서 실행해 확인했다. 지원 하한은 Python ≥3.10(`pyproject.toml`)이라 서브파서가 namespace를 덮어쓰는 방식 등 argparse 내부 동작이 버전에 따라 다를 수 있고 이는 확인하지 않았다. 실제 `gcalcli` 바이너리로의 종단 실행은 없다.
  - pydantic 검증 오류의 메시지 모양·강제 변환(예: `client-id`에 정수)은 버전 의존이고 확인하지 않았다.
  - `config edit`의 실제 편집기 실행, `util config-schema` 출력의 다른 pydantic 버전에서의 동일성은 확인하지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스는 overview 1절(MIT)을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gcalcli/env.py:1-60` 전체 | `default_data_dir`, `data_file_paths`(후보 순서·category), `explicit_config_path`, `config_dir`, `config_file` | R-01, R-13 |
| C-02 | `gcalcli/config.py:18-101` `AuthSection`·`CalendarsSection`·`WeekStart`·`OutputSection`·`Config.from_toml`·`to_argparse_namespace` | 스키마(alias·기본값), TOML 로드, namespace 변환 | R-03, R-04 |
| C-03 | `gcalcli/config.py:103-131` `json_schema`·`schema_entity_ordered` | 스키마 키 정렬 규칙 | R-20 |
| C-04 | `gcalcli/deprecations.py:9-115` | `CAMELS`, 경고 문구, `Deprecated*` action, `BASE_OPTS`·`OPTIONS`·`parser_allow_deprecated` | R-14, R-15 |
| C-05 | `gcalcli/argparsers.py:20-95` `PROGRAM_OPTIONS`, `402-434` `get_argument_parser`(`fromfile_prefix_chars='@'` 포함) | 전역 옵션 이름·dest·기본값, parser 생성 순서 | R-05, R-10, R-11, R-12, R-16 |
| C-06 | `gcalcli/argparsers.py:296-315` `get_cal_query_parser` | `--monday`는 default 없이 `week_start`에 `MONDAY` 설정 | R-09 |
| C-07 | `gcalcli/argparsers.py:357-366` `handle_unparsed` | 전역 옵션 전용 재해석 | R-16 |
| C-08 | `gcalcli/cli.py:155-229` `main` 앞부분(1·2차 파싱, config 로드, week_start 우회) | 합성 순서 전체. 원문 TODO 주석 포함 | R-02, R-05~R-09, R-11, R-12, R-16, R-17 |
| C-09 | `gcalcli/cli.py:398-447` `set_resolved_calendars` | calendar 선택·ignore 제거 | R-18 |
| C-10 | `gcalcli/cli.py:66-102` `rsplit_unescaped_hash`·`parse_cal_names` (+ `printer.py:47-52` `valid_color_name`) | `name#color` 해석 | R-18 |
| C-11 | `gcalcli/gcal.py:151-176` `data_file_path` | 데이터 파일 해소·legacy 이동 | R-13 |
| C-12 | `gcalcli/cli.py:60-63` `EMPTY_CONFIG_TOML`, `340-360` `config`·`util config-schema` 분기, `gcalcli/utils.py:210-239` `launch_editor`·`shorten_path` | 두 서브커맨드와 보조 helper | R-19, R-20 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트 열람 없음). T-02~T-04, T-06은 사본 실행으로 부분 확인, 나머지는 코드 추적.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-04 | env·rc·config.toml 모두 없음, `gcalcli agenda` | config_file=`<user_config_dir>/config.toml`(없음), config namespace는 기본값, 최종 `week_start=SUNDAY`, `default_calendars=[]`, `client_id=None` |
| T-02 | R-01 | `GCALCLI_CONFIG=/x/my.toml`이 **존재하는 파일** | config 파일=`/x/my.toml`, config 디렉터리=`/x`. 같은 값이 존재하지 않는 경로면 config 파일=`/x/my.toml/config.toml`, 디렉터리=`/x/my.toml` |
| T-03 | R-03 | `[auth]\nclient_id="x"`, `[bogus]\na=1`, `[output]\nweek-start="Monday"` 각각 | 앞 둘은 오류 없이 무시되어 `client_id=None`. 마지막은 `ValidationError` traceback으로 종료 |
| T-04 | R-08 | `[calendars] default-calendars=["A"]`, `gcalcli --default-calendar B agenda` | `default_calendars == ["A","B"]` |
| T-05 | R-09 | config `week-start="monday"`; (a) `gcalcli calw` (b) `gcalcli agenda` (c) 설정 없음 + `gcalcli calw --monday` | (a)(b)(c) 모두 최종 `MONDAY`. config monday인 상태에서 sunday로 바꾸는 명령줄 방법은 없음 |
| T-06 | R-11 | `~/.gcalclirc`에 `--nocolor`, `gcalcli --noincluderc agenda` | 최종 `color=True`(rc 미반영). rc 파일 내용에 인자 오류가 있으면 이 경우에도 1차 파싱에서 오류 |
| T-07 | R-10 | rc 파일에 `--client-id=X`와 `--default-calendar Y`(공백) 두 줄 | 첫 줄 적용. 둘째 줄은 토큰 `"--default-calendar Y"` 하나라 argparse 오류(exit 2) |
| T-08 | R-15 | `gcalcli --configFolder /x agenda` | stderr에 `WARNING: --configFolder has been deprecated ... Please use "--config-folder", instead.`, 최종 `config_folder`는 기본값 그대로(`/x` 미반영) |
| T-09 | R-14 | `gcalcli --client_id X agenda` | stderr에 `Please use "--client-id", instead.` 경고, `client_id == "X"` |
| T-10 | R-13 | `config_folder/oauth` 없음, `<data_dir>/oauth` 없음, `~/.gcalcli_oauth` 있음 | `Moving oauth file from legacy path ... to <data_dir>/oauth...` 출력 후 파일 이동, 이후 경로는 `<data_dir>/oauth`. `config_folder/oauth`가 있으면 그것이 우선하고 이동은 없음 |
| T-11 | R-18 | config `default-calendars=["A","B"]`, `gcalcli add ...`(`--calendar` 없음) | 단일형이라 목록 길이 2를 건너뛰고(stderr 디버그) `calendars=[]` → 이름 목록 비어 있음 |
| T-12 | R-18 | config `ignore-calendars=["X"]`, `gcalcli agenda --calendar X` | 이름 목록 `[X]`, `ignore_calendars`에서 `X`가 제거되어 `[]` |
| T-13 | R-19 | config 파일과 부모 디렉터리가 없음, `gcalcli config edit` | 부모 디렉터리 생성, 파일에 `#:schema ...` 한 줄+빈 줄 기록, 편집기 호출 |
| T-14 | R-20 | `gcalcli util config-schema` | stdout에 들여쓰기 2칸 JSON(`$schema` 키가 맨 앞), `data/config-schema.json`과 동일 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
repo@405639c. 줄 번호는 모두 기준 SHA.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 (`env.py:40-60`) | 코드 읽기. 빈 문자열은 `if config_path`(`:54`, `:58`)·`if from_env`로 미설정 취급. `expanduser` 호출 없음은 `env.py` 전체에서 확인 |
| R-02 | `cli.py:188-195`, `env.py:52-60` | `main` 안에 `try`가 1·2차 파싱과 서브커맨드 분기에만 있고 `from_toml` 호출은 밖(`:190-191`). 오류 종류는 R-03 실행 결과(`TOMLDecodeError`, `ValidationError`). **문서와 구현 차이**: `--config-folder` help("Optional directory used to load config files")와 달리 `config.toml`은 이 옵션의 영향을 받지 않는다 |
| R-03 | `config.py:18-86` | `Field(alias=...)`만 있고 `populate_by_name`·`extra` 설정이 없음(`grep -n 'populate_by_name\|extra' config.py` → `json_schema_extra`뿐). `/tmp`에서 `cfg.Config.from_toml`을 실행한 결과로 확인(snake_case 무시, 대소문자·값 검증 오류, 문자열 리스트 위반). pydantic 버전은 `pyproject.toml`에 하한 없음 |
| R-04 | `config.py:93-101` | `vars(model)`은 필드명 기준이라 alias가 아님. 실행 확인 |
| R-05 | `cli.py:155-172`, `argparsers.py:41-45` | 줄 추적. `SystemExit` 비포착은 stdlib 성질이고 최소 parser에서 exit 2 확인 |
| R-06 | `cli.py:174-186`(주석 176-179 포함) | 줄 추적 |
| R-07 | `cli.py:196-204` | 줄 추적 + 최소 parser 실행(`namespace` 속성이 있으면 기본값으로 덮어쓰지 않음, CLI 값이 override) |
| R-08 | `argparsers.py:56-63`(`default: []`, `append`), `cli.py:202` | 최소 parser 실행 결과 `['A','B']`(Python 3.14). `append`가 기존 속성을 복사해 이어 붙이는 것은 stdlib 성질이라 3.10~3.13에서의 동일성은 확인하지 않음. 부재 주장 없음. **TOML 외에 `ignore-calendars`에 대응하는 CLI 옵션이 없다**는 주장: `grep -n 'ignore' gcalcli/argparsers.py` 결과가 `ignore_started`·`ignore_declined`(이벤트 필터, 별개)뿐. 놓칠 수 있는 곳: 동적 등록 없음(parser 등록은 `argparsers.py` 한 파일) |
| R-09 | `cli.py:196-206`, `argparsers.py:296-315`(주석 304-305) | 최소 parser 실행(A): 서브파서가 `week_start=None`으로 namespace를 덮어씀, 서브커맨드 미해당(B)에서는 값 유지. 원인은 추론인 이유: 저자 TODO가 원인을 확정하지 않았고, 우리 설명은 실행으로 얻은 재현이지 저자 의도 확인이 아님. 우회 없이도 `calw`에서 config 값이 사라지는 것은 재현됨 |
| R-10 | `argparsers.py:423`(`fromfile_prefix_chars='@'`), `README.md` "Using cli args from a file" | `grep -rn convert_arg_line gcalcli/` 결과 없음(범위: `gcalcli/*.py`). 최소 parser로 `--a b` 한 줄이 `invalid choice: '--client_id x'`로 실패함을 확인 |
| R-11 | `argparsers.py:41-45`, `cli.py:165-172,200-201` | 줄 추적. **문서와 구현**: `ChangeLog`는 "`--noincluderc` now skips gcalclirc files unconditionally"인데, 1차 파싱은 항상 rc를 읽고 최종 반영만 막는다(오류 가능성·`config_folder` 영향이 남음). `README`는 "automatically loaded unconditionally"라고 쓰고 `--noincluderc`를 언급하지 않는다. 한 줄 요약: 구현을 사실로 썼다 |
| R-12 | `argparsers.py:35-40`, `cli.py:174-175,207-208`, `gcal.py:153` | 줄 추적. `grep -rn config_folder gcalcli/*.py`로 사용처 전수 확인: `cli.py`, `argparsers.py`, `gcal.py:153`뿐(`util reset-cache`는 `cli.py:364`). 놓칠 가능성: 동적 `getattr`/`options` 문자열 키 접근(`options.get('config_folder')`는 확인됨, 다른 문자열 조합은 못 봄) |
| R-13 | C-01, C-11, `utils.py:245`, `cli.py:363-371` | 줄 추적. **문서와 구현 차이**: `env.data_file_paths` docstring은 legacy 경로를 "there's no config dir"일 때만이라고 쓰지만 코드는 legacy가 존재하면 config 디렉터리 유무와 상관없이 후보에 넣는다(`env.py:34-36`). 실질 결과는 `data_file_path`가 category ≥ 0을 우선하므로 같다. `data_file_path` 호출처: `grep -n 'data_file_path(' gcalcli/*.py` → `gcal.py:196,229,247,323`(`oauth`·`cache`)뿐 |
| R-14 | C-04, `argparsers.py:246-293`(`@parser_allow_deprecated` 적용 위치 `:246`, `:270`, `:402`) | 줄 추적. 옵션별 dest는 argparse가 첫 긴 옵션 이름의 `-`→`_` 치환으로 만든 값이라 snake_case는 새 옵션의 dest와 일치(`gcal.py:387`이 `options['color_owner']`를 읽음). 실행은 하지 않음 |
| R-15 | C-04, `grep -rn 'configFolder\|defaultCalendar' gcalcli/*.py`(deprecations.py 밖에서 0건) | "읽는 곳 없음"은 부재 주장: 검색 범위 `gcalcli/*.py`, 기준 SHA. 놓칠 가능성: 문자열 조합으로 만든 동적 접근(찾지 못함), `**vars(parsed_args)`로 옵션 전체가 gcal에 넘어가므로 `options` 딕셔너리 접근도 위 grep이 포괄. dest가 `configFolder`가 되는 것은 argparse 규칙(최소 parser 실행으로 확인: `--configFolder /x` → `configFolder='/x'`). **문서와 구현 차이(feature map 1행)**: feature map은 "옛 camelCase 옵션은 경고와 함께 변환"이라 썼지만 구현은 변환하지 않는다. 경고 문구도 `deprecations.py:13-22`로만 확인했고 실행하지 않았다 |
| R-16 | C-07, `cli.py:215-221` | 줄 추적 |
| R-17 | `cli.py:210-227` | 줄 추적 |
| R-18 | C-09, C-10, `argparsers.py:412-414,468-690`(단일형 사용처 `:522,587,596,659`) | 줄 추적. 도달 불가 주장(추론): 단일형 parser는 `--calendar` `store`(`:174-181`)뿐이라 `calendars`가 최대 1개. 검색: `grep -n "calendar_parser" argparsers.py`. 놓칠 가능성: 추후 parser 추가, namespace에 `calendars`를 직접 넣는 경로(없음을 확인하지 못함) |
| R-19 | C-12 | 줄 추적. `ChangeLog:6`: 디렉터리 없을 때 `FileNotFoundError` 수정. 편집기 실행은 하지 않음 |
| R-20 | C-12, C-03 | `data/config-schema.json`과 `Config.json_schema()`를 `/tmp` 사본으로 비교해 일치 확인(pydantic 2.13.4) |
| R-21 | `cli.py:231-242` | 줄 추적 |
| T-01~T-14 | 위 R-ID 근거 | T-03·T-04·T-05·T-07·T-14는 사본 실행(config.py·argparse 최소 parser)로 결과 확인, 나머지는 코드 추적으로 도출 |

### 2.2 코드 읽는 순서 [선택]
`env.py`(경로 규칙) → `config.py`(스키마) → `argparsers.py:20-95`와 `402-434`(전역 옵션·parser 구성) → `cli.py:155-229`(합성 순서, 가장 중요) → `deprecations.py` → `gcal.py:151-176`(데이터 파일). 원본의 전략: config를 먼저 namespace로 만들어 parser의 시작 상태로 쓰는 것(override 규칙을 argparse에 위임). 그래서 `append`가 누적되고 `week_start`에 우회가 필요해졌다.

### 2.4 검토 기록 [필수, ready 스펙]
draft이므로 작성하지 않는다(워크플로 4장 5번 이후에 채운다).

## 적용 메모 [선택]
없음(원본 동작만 기록).
