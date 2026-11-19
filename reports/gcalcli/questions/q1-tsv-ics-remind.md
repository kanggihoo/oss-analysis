---
sha: "405639c27639a82a13538ad72ae012e76942530c"
created: 2026-11-18
updated: 2026-11-18
sources:
  - gcalcli/gcal.py
  - gcalcli/details.py
  - gcalcli/actions.py
  - gcalcli/ics.py
  - gcalcli/argparsers.py
  - README.md
---

# [Q1] TSV란 무엇이고, 10번(ICS/vCal 가져오기)·11번(리마인드)은 무엇인가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 인용한 함수는 본문을 읽었다(`코드 확인`). 실행하지 않았다.

## 1. TSV

- **TSV = Tab-Separated Values**: 쉼표 대신 탭 문자로 칸을 나누는 표 형식 텍스트다. CSV와 같은 용도인데 일정 제목 안의 쉼표가 칸을 깨지 않는다.
- gcalcli에서는 두 곳에 나온다.
  1. **출력**: `agenda --tsv`가 일정 목록을 TSV로 찍는다. 첫 줄은 헤더(`handler.fieldnames`), 이후 일정마다 한 줄이고 줄바꿈은 `\n` 문자열로 바꾼다(`gcal.py` `_tsv`). 열은 `--details`로 고른 필드와 기본값 `time`·`title`(`details.py` `DETAILS_DEFAULT`)이다.
  2. **입력**: `agendaupdate`는 표준 입력으로 TSV를 읽어(`csv.DictReader`, `excel_tab`) 행마다 `action` 열 값(`patch`·`insert`·`delete`·`ignore`, 기본 `patch`)을 실행한다. 단일 캘린더만 허용한다(`gcal.py` `AgendaUpdate`, `actions.py`). 그래서 "agenda를 TSV로 내보내 → 스프레드시트나 스크립트로 고쳐서 → `agendaupdate`로 되돌려 넣는" 왕복이 가능하다. 읽기 전용 필드는 `insert`에서 값을 주면 오류다(`actions.insert`의 `ReadonlyError`).
- 같은 필드 핸들러(`details.py` `HANDLERS`: id, time, length, url, conference, title, location, description, calendar 등)가 출력(`get`/`data`)과 수정(`patch`)을 모두 맡는다. JSON 출력(`agenda --json`)도 같은 핸들러의 `data`를 쓴다(`gcal.py` `_json`).
- 예: `gcalcli agenda --tsv --details id --details title` → 다음 형태의 표(열 이름과 순서는 핸들러의 `fieldnames`가 정하므로 이 예의 이름은 설명용이다).

```text
id    start_date  start_time  end_date  end_time  title
abc1  2026-11-19  10:00       2026-11-19 10:30    스탠드업
```

## 2. 10번: ICS/vCal 가져오기

- **ICS(iCalendar, `.ics`)**는 일정 하나 이상을 담는 표준 텍스트 파일이다. 메일로 오는 회의 초대 첨부가 이 형식이고, README는 Microsoft Exchange 초대를 예로 든다(`README.md` 10행). vCal은 그 옛 형식이다.
- `gcalcli import 파일.ics`는 이 파일을 읽어 **한 캘린더에 일정으로 넣는다**. 파일이 없으면 표준 입력을 읽는다(`gcal.py` `ImportICS`).
- 동작 순서(`코드 확인`):
  1. `vobject` 패키지가 없으면 안내 후 종료한다(`pip install gcalcli[vobject]` 선택 extra).
  2. `ics.get_ics_data`가 `vobject`로 파싱해 `VEVENT`마다 Google 일정 본문 dict를 만든다(`CreateEventFromVOBJ`: summary, location, 시작·끝, 반복 `RRULE` 등). `dtstart`가 없는 일정은 오류를 내고 건너뛴다.
  3. `-v`(verbose)면 일정마다 `[S]kip [i]mport [q]uit`를 묻는다. `--dump`는 내용만 보여 주고 가져오지 않는다. 알림은 `--reminder`로 덧붙인다.
  4. 가져오기는 두 API 중 하나다. 본인이 참석자이고 `iCalUID`가 있으면 **`events.import_`**(중복을 막는 새 방식), 아니면 `events.insert`(`_event_should_use_new_import_api`). `--use-legacy-import`로 옛 방식을 강제한다.
  5. 중복(`reason == 'duplicate'`)은 건너뛰고, 실패한 일정은 모아서 `dump_partial_ical`로 별도 ICS에 저장하고 경로를 알려 준다.
- 메일 클라이언트의 첨부파일 처리기로 연결해 쓰는 용도다(README 기능 목록, 219~233행의 예). 이 예는 내용을 열지 않았다.

## 3. 11번: 리마인드(`remind`)

- **지금부터 N분 안에 시작할 일정을 찾아 외부 명령을 실행**하는 기능이다. gcalcli가 상주하지 않으므로 **cron 같은 스케줄러가 주기적으로 `gcalcli remind`를 부르는 방식**이 전제다(README 245~280행 부근에 `*/10 * * * * /usr/bin/gcalcli remind` 예가 있다. 줄 번호는 `grep` 확인, 본문은 읽지 않음).
- 동작(`gcal.py` `Remind` 전체 읽음, `코드 확인`):
  1. 현재 시각부터 `minutes + 5`분까지 일정을 검색한다.
  2. 이미 시작한 일정은 건너뛴다. `--use-reminders`이면 일정에 설정된 알림 시각이 아직 안 온 일정도 건너뛴다.
  3. 남은 일정을 `시각  제목` 줄로 이어 메시지를 만든다.
  4. 메시지가 있으면 `os.fork()` 후 `execvp`로 명령을 실행하고, 명령 인자에 `%s`가 있으면 그 자리에 메시지가 들어간다. 기본 명령은 코드에서 확인하지 못했다(`argparsers.py` 등록부를 읽어야 함).
- 한계(코드에서 보이는 것): 상태를 저장하지 않으므로 같은 일정이 시간 창 안에 있는 동안 cron이 돌 때마다 반복해서 알린다(README도 "still inside" 시 다시 알린다고 적은 것으로 grep 줄에서 보임, 본문 미확인). 중복 알림 방지 기록이 없다는 것은 `Remind`에서 저장 코드가 없다는 읽기 결과이고 실행 확인은 아니다.
- 이 알림은 Google 쪽 알림(이메일·팝업·SMS)이 아니라 **로컬에서 명령을 실행**하는 것이다. `--reminder`로 일정에 붙이는 Google 알림(`gcalcli add --reminder`, 7번 행)과 이름이 비슷하지만 다른 기능이다.
