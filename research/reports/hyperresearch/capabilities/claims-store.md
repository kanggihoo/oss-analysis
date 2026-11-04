---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/core/claims.py
  - src/hyperresearch/cli/claims_cmd.py
  - src/hyperresearch/core/db.py
  - src/hyperresearch/core/sync.py
  - src/hyperresearch/core/hooks.py
  - src/hyperresearch/core/citecheck.py
  - src/hyperresearch/cli/lint.py
  - src/hyperresearch/skills/hyperresearch-2-width-sweep.md
  - src/hyperresearch/skills/hyperresearch-9-evidence-digest.md
depends:
  - vault-store.md
status: ready
---

# 클레임 저장소

> fetcher 서브에이전트가 소스 노트마다 쓴 `claims-<note-id>.json`을 `claims`(+`claims_fts`) 테이블로 멱등하게 적재하고, 클레임 검색·문헌 매트릭스·공통 대상 묶음을 조회하는 CLI(`hyperresearch claims …`)를 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 소스 하나를 `fetch`로 노트화하고 읽은 fetcher가 프롬프트 지시(R-21)에 따라 Write 도구로 `research/runs/<vault_tag>/temp/claims-<note-id>.json`을 쓴다. 파일 안 클레임은 LLM이 소스 본문을 읽고 뽑은 것이다. CLI는 그 내용을 만들지 않는다.
2. 2단계 끝(2.7)에서 오케스트레이터가 `hyperresearch claims ingest --tag <vault_tag> -j`를 부른다. 먼저 `auto_sync`로 노트가 DB에 있게 한다.
3. 적재기가 `--tag`가 가리키는 런의 `temp/`(없으면 레거시 `research/temp/`와 모든 `research/runs/*/temp/`)에서 `claims-*.json`을 찾는다.
4. 파일마다 파일 이름에서 노트 id를 얻고, 노트가 DB에 있고 크기가 8 MiB 이하인지 확인하고 JSON을 읽는다.
5. 클레임마다 텍스트의 sha256 앞 16자(hex)를 키로 `(note_id, claim_hash)`가 이미 있으면 건너뛰고, 없으면 `claims`와 `claims_fts`에 넣는다. 갱신은 하지 않는다.
6. 이후 `claims search`(FTS)·`claims list`·`claims matrix`·`claims targets`가 DB에서 질의에 답한다. 소비자(cite-check 기계 분류, numeric-consistency)는 DB를 직접 읽는다(경계).

### 1.2 범위·통합 지점
- 제공: 클레임 JSON 파일 포맷과 검증, 적재 규칙(`ingest_claims_file`·`ingest_claims_dir`), `claims`·`claims_fts` 테이블 의미, `search_claims`·`list_claims`·`literature_matrix`·`render_matrix_markdown`·`group_by_target`, `hyperresearch claims` 명령 5개, fetcher 프롬프트가 클레임 JSON을 만들게 지시하는 방법.
- 제외(경계만):
  - 클레임을 쓰는 소비자 규칙은 각 행이 소유한다. cite-check 기계 분류(`citecheck.triage_pairs`)와 numeric-consistency(`lint._check_numeric_consistency`)는 행 10, 증거 다이제스트(9단계)·모순 그래프(3단계)는 행 6, 중복 근거 감사(2.6)는 행 5다. 여기서는 그들이 `claims` 테이블에서 무엇을 읽는지만 R-23에 적는다.
  - `notes` 테이블·노트 스키마·동기화는 `capabilities/vault-store.md`(선행). 노트가 먼저 DB에 있어야 하고, 노트 삭제·id 변경이 클레임에 미치는 영향은 R-20에서 확인한다.
  - fetcher 프롬프트의 클레임 외 지시(Phase 2 primary 추적, 요약 길이, 태그 규칙)와 fetcher 로스터는 행 3·5다.
  - `quality_score` 같은 노트 점수 계산은 `capabilities/source-quality.md`. 매트릭스는 그 값을 읽기만 한다.
- 외부 의존·선행 계약: `vault-store.md`의 `Vault.discover`·`Vault.db`·`auto_sync`·`notes`·`claims`·`claims_fts` DDL(`claims`는 거기 C-01에 있고, 이 스펙이 칼럼 의미를 소유한다). 호출자가 `research/runs/<tag>/temp/`에 파일을 쓴다.
- 소유 상태·부작용: `claims`·`claims_fts` 행(적재만 추가. 삭제·갱신 경로 없음). 매트릭스는 `--out` 파일을 쓴다. JSON 파일은 읽기만 하고 지우지 않는다.

### 1.3 인터페이스와 데이터 의미

**클레임 파일** `claims-<note-id>.json` (외부 계약):

| 항목 | 규칙 |
|---|---|
| 위치 | `research/runs/<vault_tag>/temp/`(현재 계약). 레거시 `research/temp/`도 읽는다. 청크 런은 `research/runs/<tag>/chapters/<id>/temp/`를 쓰지만 기본 스캔은 거기를 보지 않는다(경계: 행 4). |
| 파일 이름 | `claims-` 접두 + 노트 id + `.json`. 노트 id = `Path.stem`에서 `claims-`를 뗀 나머지. 접두가 없으면 거부. |
| 최상위 | 클레임 객체의 배열, 또는 `{"claims": [...]}`. 객체가 아닌 원소는 버린다. 다른 모양이면 클레임 0개(오류 아님). |
| 인코딩·크기 | UTF-8(BOM 허용), 8 MiB(`8*1024*1024`바이트) 초과 시 읽기 전에 거부. |
| 클레임 객체 필드 | 아래 표. 표에 없는 키는 무시. |

| 필드 | 적재 규칙 | `claims` 칼럼 |
|---|---|---|
| `claim`(없으면 `text`) | 문자열만 인정, `strip` 후 20,000자 컷. 비면 건너뜀 | `claim` (필수) |
| (유도) | `sha256(claim.strip())` hex 앞 16자 | `claim_hash` |
| `quoted_support` | 문자열만, `strip`·20,000자 컷, 비면 NULL | `quoted_support` |
| `numbers` | 값이 truthy(비어 있지 않음)면 `json.dumps(값)`의 앞 20,000자, 아니면 NULL | `numbers`(JSON 텍스트) |
| `confidence` | 불리언·null→NULL, 숫자는 그대로, 문자열은 20,000자 컷(`strip` 안 함), 그 밖→NULL | `confidence` |
| `evidence_type`, `stance_target`, `stance` | 문자열만, `strip`·20,000자 컷, 비면 NULL | 같은 이름 |
| (인자) | `--tag` 값 또는 NULL | `vault_tag` |
| (유도) | 적재 시각 UTC ISO | `ingested_at` |

`scope_conditions`·`entities`·`time_period`·`region`·`source_note_id` 등 프롬프트가 만들게 하는 다른 필드는 DB에 들어가지 않는다(R-22).

**`claims` 테이블**: `id` INTEGER PK AUTOINCREMENT, `note_id` NOT NULL→`notes(id)` ON DELETE CASCADE, `claim` NOT NULL, `claim_hash` NOT NULL, `quoted_support`, `numbers`, `confidence`, `evidence_type`, `stance_target`, `stance`, `vault_tag`, `ingested_at` NOT NULL, UNIQUE(`note_id`, `claim_hash`). 인덱스: `note_id`, `vault_tag`, `stance_target`. 값 어휘 제약은 DB에 없다(프롬프트가 `stance`=supports|refutes|neutral, `evidence_type`=empirical|theoretical|anecdotal|expert-opinion|statistical|legal|historical, `confidence`=high|medium|low를 요구할 뿐이다). **`claims_fts`**: FTS5(`claim_id` UNINDEXED, `claim`, `quoted_support`), `porter unicode61`. 클레임 한 행당 FTS 한 행이고 `claim_id`가 `claims.id`다.

**함수**

| 연산 | 입력 → 출력 | 의미 |
|---|---|---|
| `ingest_claims_file(conn, path, vault_tag=None)` | → `{file, note_id, ingested, skipped, errors[str]}` | 파일 하나 적재(커밋은 호출자가) |
| `default_claims_dirs(vault, vault_tag=None)` | → `[Path]` | R-12 |
| `discover_claims_files(vault, vault_tag=None)` | → 정렬된 `[Path]` | R-13 |
| `ingest_claims_dir(vault, temp_dir=None, vault_tag=None)` | → `{files, ingested, skipped, errors[str], scanned[str], hint?}` | `temp_dir`가 있으면 그 디렉터리의 `claims-*.json`만(재귀 없음), 없으면 기본 스캔. 끝에 `commit` |
| `search_claims(conn, query, limit=20)` | → `[dict]` | R-17 |
| `list_claims(conn, note_id=None, vault_tag=None, limit=100)` | → `[dict]` | `id` 순, 필터는 AND |
| `literature_matrix(conn, vault_tag=None)` / `render_matrix_markdown(rows)` | → `[dict]` / 문자열 | R-18 |
| `group_by_target(conn, vault_tag=None, min_sources=2)` | → `[dict]` | R-19 |

**CLI** (`hyperresearch claims …`, JSON 봉투는 `vault-store.md` 1.3):

| 명령 | 옵션·인자 | 출력 |
|---|---|---|
| `claims ingest [PATHS...]` | `--tag/-t`, `--json/-j` | data `{files, ingested, skipped, errors, [scanned, hint]}`. 텍스트: `Ingested: N claims (M already present) from F file(s)`, 힌트·오류는 줄마다 |
| `claims list` | `--note`, `--tag/-t`, `--limit/-n`(100), `--json/-j` | data `{claims:[{id, note_id, claim, quoted_support, numbers, confidence, evidence_type, stance_target, stance, vault_tag}]}`, count. 텍스트: `note_id claim[:120]`와 `N claims` |
| `claims search QUERY` | `--limit/-n`(20), `--json/-j` | data `{claims:[…list와 같은 필드]}`. 텍스트: 클레임 120자, `quoted_support`가 있으면 따옴표로 160자 |
| `claims matrix` | `--tag/-t`, `--out/-o`, `--json/-j` | data `{rows, written_to}`. 텍스트: 마크다운 표(`--out`이면 파일에도 씀) |
| `claims targets` | `--tag/-t`, `--min-sources`(2), `--json/-j` | data `{targets:[{stance_target, n_sources, n_claims, stances, quantified}]}` |

볼트가 없으면 모두 `NO_VAULT`(종료 1). `ingest`만 먼저 `auto_sync`를 한다.

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 파일 이름이 `claims-…`로 시작하지 않음 | `errors`에 `filename does not match claims-<note-id>.json`, 적재 0 | 코드 확인 |
| R-02 | 이름에서 얻은 노트 id가 `notes`에 없음 | `errors`에 `note '<id>' not in vault (sync first?)`, 파일을 읽지 않음 | 코드 확인 |
| R-03 | 파일 크기 > 8 MiB(`stat` 실패 포함) | 크기 초과는 `claims file is N bytes (limit 8388608); skipped`, `stat` 실패는 `unreadable JSON: …`. 읽지 않음 | 코드 확인 |
| R-04 | JSON 파싱 실패(문법·읽기·디코딩·재귀 깊이) | `unreadable JSON: …`, 적재 0 | 코드 확인 |
| R-05 | 최상위가 배열이거나 `{"claims": 배열}` | 딕셔너리 원소만 처리. 그 밖의 최상위, `claims`가 배열이 아닌 객체는 0건이며 오류 없음 | 코드 확인 |
| R-06 | 클레임의 텍스트 | `claim` 키의 문자열, 비었으면 `text` 키의 문자열. 문자열이 아니거나 `strip` 후 빈 값이면 `skipped += 1` 하고 다음으로 | 코드 확인 |
| R-07 | 같은 노트에 같은 `claim_hash` | `INSERT OR IGNORE`가 무시 → `skipped += 1`, FTS 삽입 없음. 먼저 들어간 행이 유지되어 다른 필드(`quoted_support`·`vault_tag`·`confidence` 등)가 바뀐 재적재는 반영되지 않는다. 문장이 조금이라도 달라지면 새 행이 생기고 옛 행은 남는다 | 코드 확인 |
| R-08 | 새 클레임 행 | 1.3 필드 표대로 칼럼을 채워 `claims`에 넣고 같은 트랜잭션에서 `claims_fts(claim_id=lastrowid, claim, quoted_support=문자열 또는 '')`를 넣은 뒤 `ingested += 1` | 코드 확인 |
| R-09 | 클레임 하나의 `sqlite3.Error` | 전체를 중단하지 않고 `errors`에 `claim <hash> not stored: …`, `skipped += 1` | 코드 확인 |
| R-10 | `ingest_claims_file` 단독 | 커밋하지 않는다. `ingest_claims_dir`는 끝에 `commit`, CLI의 경로 지정 경로는 루프 뒤 `commit` | 코드 확인 |
| R-11 | 재적재(같은 파일) | `ingested=0`, `skipped=파일 안 딕셔너리 원소 수`(유효 클레임은 중복, 무효 클레임은 매번 건너뜀). 멱등 | 코드 확인 |
| R-12 | `default_claims_dirs`, `vault_tag` 지정 | `research/runs/<tag>/temp`가 디렉터리이고 `research/runs/` 아래로 해석되면 그 하나만. 아니면(태그가 `..`·절대 경로·런 폴더 없음) 폴백으로 `research/temp` + `research/runs/` 아래 각 하위 디렉터리의 `temp`(정렬)를 모두 스캔. 폴백이어도 모든 행에 그 `vault_tag`가 찍힌다. 경로는 `vault.root/"research"` 고정 | 코드 확인 |
| R-13 | `discover_claims_files` | 디렉터리마다 `claims-*.json`(비재귀, 정렬)을 모으고, 볼트 루트 밖으로 해석되는 파일(심볼릭 링크)은 버리며, 해석된 경로 기준으로 중복을 제거해 정렬해 돌려준다 | 코드 확인 |
| R-14 | `ingest_claims_dir` 결과 | `files`=발견 수, `ingested`·`skipped` 합계, 오류는 `"<파일이름>: <오류>"`, `scanned`=스캔한 디렉터리. 파일이 0개면 `hint`(`no claims-*.json found under … pass --tag <vault_tag> or the files explicitly`) | 코드 확인 |
| R-15 | `claims ingest` | `auto_sync` 후, 경로 인자가 있으면 각 파일에 `ingest_claims_file`(요약에는 `scanned`·`hint` 없음, `files`=인자 수), 없으면 `ingest_claims_dir(vault, vault_tag=…)`. `--tag`는 `vault_tag` 스탬프이면서 기본 스캔 범위를 좁힌다 | 코드 확인 |
| R-16 | `claims list` | `auto_sync` 없이 `id` 오름차순, `--note`·`--tag` AND 필터, `LIMIT --limit` | 코드 확인 |
| R-17 | `claims search` | 질의를 가공하지 않고 `claims_fts MATCH ?`에 넣고 `claims`와 `claim_id=c.id`로 조인해 `ORDER BY rank LIMIT`. 질의 문법 오류의 처리 코드가 없어 `sqlite3.OperationalError`가 그대로 난다. 노트가 지워져 `claims`에서 사라진 FTS 행은 조인에서 빠져 결과에 안 나온다 | 코드 확인 |
| R-18 | `literature_matrix` | `claims`⋈`notes`를 `n.id`로 묶어 행마다 `id, title, tier, content_type, venue, citation_count, is_retracted, quality_score, created, source, n_claims, n_empirical`(evidence_type이 `empirical`·`statistical`인 수), `n_quantified`(`numbers` NOT NULL인 수). `--tag`면 `c.vault_tag`로 거른다. 각 행에 `key_claim`=그 노트의 클레임 중 정렬 키(empirical·statistical 우선 → `numbers` 있음 우선 → `confidence='high'` 우선 → `id`)가 가장 앞선 `claim`(이 서브쿼리는 `vault_tag`로 거르지 않는다). `quality_score` 내림차순, NULL은 맨 뒤. 마크다운: 헤더 `\| Source \| Tier \| Type \| Venue \| Cites \| Quality \| Claims (emp/quant) \| Key finding \|`, 행은 `[[id]]`(철회면 뒤에 ` **RETRACTED**`), tier·type·venue는 없으면 `-`, Cites 없으면 `-`, Quality는 `%.2f`(없으면 `-`), `n (emp/quant)`, key finding은 `\|`→`/`·140자 컷 | 코드 확인 |
| R-19 | `group_by_target` | `stance_target`이 NULL·빈 문자열이 아닌 클레임을 정확히(대소문자·공백 그대로) 같은 `stance_target`끼리 묶어 서로 다른 `note_id`가 `min_sources` 이상인 대상만 `n_sources` 내림차순으로 낸다. 그룹마다 `n_claims`, `stances`(stance별 개수, 없으면 `unspecified`), `quantified`(`numbers`가 있는 클레임의 `{note_id, numbers=JSON 파싱값}`, 파싱 실패는 버림). `--tag`는 모든 질의에 적용 | 코드 확인 |
| R-20 | 노트 수명 | 노트 삭제는 `claims`를 CASCADE로 지우고 `claims_fts` 행은 남는다(조회엔 안 보임). 노트 id 변경은 `claims.note_id`를 새 id로 옮긴다(파일 이름은 그대로) | 코드 확인 |
| R-21 | fetcher 프롬프트(`hyperresearch-fetcher`, 도구 Bash·Read·Write·WebSearch) | 본문을 `note show -j`로 읽고 품질 판정·요약·태그를 한 뒤 소스마다(Phase 2에서 추가로 가져온 소스 포함) `research/runs/<vault_tag>/temp/claims-<note-id>.json`을 쓴다. 한 클레임은 `claim`(한 문장, 반증 가능), `stance`(supports\|refutes\|neutral), `stance_target`, `evidence_type`, `scope_conditions`, `quoted_support`(소스 원문 그대로 최대 두 문장, "가장 중요한 필드"), `numbers`(문자열 배열), `entities`, `time_period`, `region`, `confidence`(high\|medium\|low), `source_note_id`. 개수 상한: 짧은 소스 3~8, 중간 8~15, 긴 소스 15~25개, 사소한 클레임 금지. 기간이 지정된 질의(예: Q3 2024)에서는 해당 기간 공시 원문을 가져와 표의 수치를 `numbers`에 반올림 없이 그대로 적는다 | 코드 확인 |
| R-22 | 프롬프트가 요구하나 저장되지 않는 것 | `scope_conditions`, `entities`, `time_period`, `region`, `source_note_id`는 `claims`에 칼럼이 없어 적재 시 버려진다. 노트 id는 항상 파일 이름에서 얻는다. 프롬프트가 파일 최상위를 배열로 쓰라고 말하지 않아도 적재기는 배열·`{claims}` 둘 다 받는다 | 코드 확인 |
| R-23 | 소비자(경계) | DB를 읽는 곳: `citecheck.triage_pairs`가 인용된 노트의 `claim`·`quoted_support`를 읽고(`numbers`는 안 읽음), `lint._check_numeric_consistency`가 모든 노트의 `claim`·`quoted_support`·`numbers`를 한 덩어리로 읽는다. 파일을 직접 읽는 곳: 2.6 중복 근거 감사, 3단계 모순 그래프, 9단계 증거 다이제스트(`confidence=high`이거나 `evidence_type`이 empirical·statistical인 클레임을 우선), depth-investigator. cite-checker 프롬프트는 `claims search "<key phrase>" -j`를 wrong-source 후보 찾기에 쓰라고 한다 | 코드 확인 |
| R-24 | 적재 호출 시점 | 스킬·프롬프트·CLI를 통틀어 `claims ingest`를 부르라고 적힌 곳은 2.7(2단계 끝) 한 군데뿐이다. 13단계 갭 페치 fetcher가 같은 경로에 쓴 클레임을 다시 적재하라는 지시는 코드에 없다 | 코드 확인(검색 결과) / 호스트가 실제로 다시 부르는지는 미확인 |

- 불변식: (1) `claims`에서 `(note_id, claim_hash)`는 유일하다. (2) `claims.note_id`는 항상 존재하는 `notes.id`를 가리킨다(외래키). (3) 같은 파일을 여러 번 적재해도 행 수는 늘지 않는다(문장이 같다면).
- 미결정: 없음.
- 확인 한계: 코드를 실행하지 않았다. `confidence`에 숫자가 들어올 때 SQLite가 `TEXT` 칼럼 친화성 때문에 문자열로 저장한다는 것은 SQLite 규칙에서의 추론이다(T-07). fetcher가 실제로 만드는 파일의 외피(배열인지 `{claims}`인지)는 실행 기록이 없어 확인하지 못했다.

### 1.5 필수 코드 참조
`~` = `research/repos/hyperresearch/src/hyperresearch/`

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `~/core/claims.py:23-83` 상수, `_claim_hash`, `_text_field`, `_scalar_field`, `_under`, `_note_id_from_filename`, `_iter_claim_dicts` | 크기·필드 상한, 해시, 필드 강제 변환, 파일 모양 허용 | R-01 R-05 R-06 R-07 |
| C-02 | `~/core/claims.py:86-157` `ingest_claims_file` | 검증 순서, INSERT OR IGNORE, FTS 삽입, 오류 수집 | R-01~R-11 |
| C-03 | `~/core/claims.py:160-244` `_glob_claims`, `default_claims_dirs`, `discover_claims_files`, `ingest_claims_dir` | 스캔 디렉터리 결정, 심볼릭 링크 제외, 요약·힌트 | R-12 R-13 R-14 |
| C-04 | `~/core/claims.py:247-281` `search_claims`, `list_claims` | FTS 질의 SQL, 목록 필터 | R-16 R-17 |
| C-05 | `~/core/claims.py:284-339` `literature_matrix`, `render_matrix_markdown` | 집계 SQL, `key_claim` 정렬, 마크다운 표 | R-18 |
| C-06 | `~/core/claims.py:342-391` `group_by_target` | 대상 묶음 SQL·후처리 | R-19 |
| C-07 | `~/cli/claims_cmd.py:28-170` | 옵션, 출력 모양, 경로 지정 적재, 매트릭스 파일 쓰기 | R-15 R-16 R-17 R-18 R-19 |
| C-08 | `~/core/db.py:117-135`, `:212-217` `claims`, `claims_fts` DDL | 테이블·인덱스·FTS(`vault-store.md` C-01과 같은 정의) | R-08 R-20 |
| C-09 | `~/core/hooks.py:2962-2975`, `:3000-3033`, `:3127-3147` `RESEARCHER_AGENT` | fetcher 프롬프트의 frontmatter(이름·도구), 기간 지정 공시 규칙, 클레임 JSON 지시 전문 | R-21 |

### 1.6 수락 사례
출처: 모두 구현에서 도출(원본 테스트는 열지 않음). 손계산이며 실행하지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-06 R-07 R-08 | 노트 `a`가 DB에 있고 `claims-a.json`=`[{"claim":"X is 5"},{"claim":" X is 5 "},{"claim":""},{"text":"Y"},{"claim":7}]` | `ingested=2`(`X is 5`, `Y`), `skipped=3`(공백만 다른 중복, 빈 문자열, 숫자) |
| T-02 | R-05 | `{"claims":[{"claim":"Z"}]}` / `{"foo":[]}` / `"abc"` | 첫째는 1건 적재. 나머지는 0건, 오류 없음 |
| T-03 | R-01 R-02 | `claims.json`, 또는 `claims-nonexistent.json`(노트 없음) | 각각 `filename does not match …`, `note 'nonexistent' not in vault (sync first?)` |
| T-04 | R-11 | T-01 파일을 한 번 더 적재 | `ingested=0`, `skipped=5`(원소 3개는 이미 있는 중복, 2개는 무효라 매번 건너뜀) |
| T-05 | R-08 | `{"claim":"c","numbers":["$2,062","73.09%"],"confidence":"high","stance":"supports"}` | `numbers`=`["$2,062", "73.09%"]`(JSON 텍스트, `json.dumps` 기본 구분자), `confidence="high"`, `quoted_support` NULL, `claims_fts.quoted_support=''` |
| T-06 | R-08 | `{"claim":"c","numbers":[],"confidence":true,"evidence_type":"  "}` | `numbers` NULL, `confidence` NULL, `evidence_type` NULL |
| T-07 | R-08 | `{"claim":"c","confidence":0.9}` | `confidence`는 숫자 0.9로 바인딩되나 칼럼이 `TEXT`라 `'0.9'`로 저장(추론) |
| T-08 | R-12 | `research/runs/r1/temp/`가 있고 `--tag r1` / `--tag nope`(런 없음) | 앞은 `r1/temp`만 스캔. 뒤는 `research/temp`와 모든 `runs/*/temp` 스캔, 모든 행에 `vault_tag='nope'` |
| T-09 | R-17 | `claims search "foo AND"` | 질의 문법 오류로 `sqlite3.OperationalError`가 처리 없이 전파(트레이스백). `claims search "retrain*"`는 접두 일치 |
| T-10 | R-18 | 소스 A(quality 0.8, 클레임 3개 중 empirical 2, `numbers` 1), B(quality NULL, 클레임 1) | 행 순서 A, B. A 표 행의 "Claims" 칸 `3 (2/1)`, B의 Quality 칸 `-`. `--out`을 주면 같은 표가 파일에 쓰이고 JSON 모드면 `written_to`에 경로 |
| T-11 | R-19 | 노트 a·b 모두 `stance_target="GPU price"`(stance supports, refutes), `numbers` 하나만 있음 | `targets=[{stance_target:"GPU price", n_sources:2, n_claims:2, stances:{supports:1, refutes:1}, quantified:[{note_id, numbers:[…]}]}]`. `--min-sources 3`이면 빈 목록 |
| T-12 | R-20 | 노트 a의 파일을 지우고 `sync` 후 `claims list --note a` | 0건. `claims search`에 a의 문장이 더 이상 나오지 않는다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
`~` = `research/repos/hyperresearch/src/hyperresearch/`, 기준 repo@aece65f.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02(`claims.py:88-92`), `:67-72` `_note_id_from_filename` | 직접 읽음 |
| R-02 | C-02(`claims.py:94-97`) | 직접 읽음 |
| R-03 | C-02(`claims.py:99-108`), 상수 `:26` | 직접 읽음 |
| R-04 | C-02(`claims.py:109-113`) | 직접 읽음 |
| R-05 | C-01(`claims.py:75-83`) | 직접 읽음 |
| R-06 | C-01(`claims.py:34-44`), C-02(`claims.py:116-120`) | 직접 읽음 |
| R-07 | C-02(`claims.py:121-151`), `core/db.py:130` UNIQUE | 직접 읽음 |
| R-08 | C-02(`claims.py:122-149`), C-01(`claims.py:47-55`) | 직접 읽음 |
| R-09 | C-02(`claims.py:152-156`) | 직접 읽음. FTS 삽입이 실패하면 `claims` 행이 이미 들어가 있는 채로 `skipped`로 센다(같은 `try` 안, 롤백 없음). 영향은 추론 |
| R-10 | C-02(함수에 `commit` 없음), C-03(`claims.py:243`), C-07(`claims_cmd.py:60`) | 직접 읽음 |
| R-11 | R-07의 귀결 | 직접 읽음 |
| R-12 | C-03(`claims.py:164-187`) | 직접 읽음. `ingest_claims_dir`의 `temp_dir` 인자는 CLI가 쓰지 않는다 |
| R-13 | C-03(`claims.py:160-205`) | 직접 읽음 |
| R-14 | C-03(`claims.py:208-244`) | 직접 읽음 |
| R-15 | C-07(`claims_cmd.py:28-74`) | 직접 읽음 |
| R-16 | C-07(`claims_cmd.py:77-95`), C-04(`claims.py:260-281`) | 직접 읽음 |
| R-17 | C-04(`claims.py:247-257`), C-07(`claims_cmd.py:98-119`) | 직접 읽음. FTS5 `rank`의 의미는 SQLite 지식(추론) |
| R-18 | C-05, C-07(`claims_cmd.py:122-147`) | 직접 읽음 |
| R-19 | C-06, C-07(`claims_cmd.py:150-170`) | 직접 읽음 |
| R-20 | `~/core/sync.py:372-373`·`:540-544`, `~/core/db.py:119` | 직접 읽음. `claims_fts`에 삭제문이 없음을 `grep claims_fts`로 확인 |
| R-21 | C-09, `~/core/hooks.py:4021-4026`(`RESEARCHER_AGENT.format(hpr_path=…)`로 설치) | 프롬프트 원문을 읽음. 호스트가 실제로 이를 따르는지는 이 레포로 확인할 수 없다(미확인). 설치 시 `<< p.* >>` 값이 채워지는 곳은 행 2 |
| R-22 | C-02(저장하는 키 목록), C-09(`hooks.py:3127-3144`) | 두 목록을 대조 |
| R-23 | `~/core/citecheck.py:255-310`, `~/cli/lint.py:148-197`, `~/core/hooks.py:3533`, `~/skills/hyperresearch-9-evidence-digest.md:25-35`, `~/skills/hyperresearch-3-contradiction-graph.md:25-33`, `~/skills/hyperresearch-2-width-sweep.md:209-214` | 각 호출 위치와 읽는 칼럼만 확인. 판정 알고리즘 자체는 행 10·6 |
| R-24 | `~/skills/hyperresearch-2-width-sweep.md:231`, `~/skills/hyperresearch-13-gap-fetch.md:69-71` | `grep -rn "claims ingest"`(skills, hooks)와 `grep -rn ingest_claims`(src)로 호출처가 CLI 한 곳과 2.7 한 줄임을 확인. 호스트의 임의 호출은 코드로 알 수 없다 |
| T-01~T-12 | R-ID와 같은 위치 | 손계산. T-04의 숫자는 T-01 파일의 5개 원소(재적재 시 중복 3, 무효 2)에서 나온다 |

**문서와 구현의 차이**
- `docs/roadmap-2.0/phase-2-source-ranking.md:101`은 `hpr claims ingest research/temp/claims-*.json`과 `claims list --search "<text>"`를 말한다. 구현의 `claims list`에는 `--search` 옵션이 없고 검색은 별도 명령 `claims search`다. 기본 스캔 위치도 `research/runs/<tag>/temp/`가 우선이다. 코드 확인.
- `core/claims.py` 머리 주석은 "수집 후 `ingest`가 멱등이고 행은 (note_id, sha256(claim)[:16])"이라고 하며 맞다. 다만 이 키 때문에 "갱신"이 없다는 점(R-07)은 문서에 안 적혀 있다. 코드 확인.
- fetcher 프롬프트가 클레임에 요구하는 필드 11개 중 5개는 DB에 저장되지 않는다(R-22). 프롬프트는 이 사실을 알리지 않는다. 코드 확인.

### 2.2 코드 읽는 순서
`~/core/claims.py`(`ingest_claims_file` → `ingest_claims_dir`·`default_claims_dirs` → 질의 함수 4개) → `~/cli/claims_cmd.py` → `~/core/hooks.py:2962` 이후 fetcher 프롬프트의 6번 항목 → 소비자 `~/core/citecheck.py:255`, `~/cli/lint.py:148`. 원본의 전략: 파일은 에이전트(적대적 페이지에서 만든 출력)가 쓰므로 크기·필드 길이·타입을 모두 방어적으로 강제하고, 한 클레임의 오류가 파일 전체를 멈추지 않게 한다.
