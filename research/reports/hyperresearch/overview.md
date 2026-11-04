---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-04
updated: 2026-11-04
---

# hyperresearch Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/jordan-gibbs/hyperresearch`
- **작업트리 상태**: Clean (shallow clone `--depth 50`, 2026-11-04, 마지막 커밋 2026-10-28). `pyproject.toml` 버전은 0.13.0이고 `CHANGELOG.md`에는 0.13.0 뒤의 `[Unreleased]` 항목이 있다. 즉 기준 SHA는 0.13.0 릴리스보다 앞서 있다. (코드 확인)
- **분석 목적**: 사용자 확인(2026-11-05). `gpt-researcher`와 비교하지 않고 이 레포만 독립적으로 분석한다. 알고 싶은 것은 두 가지다. (1) **어떤 식으로 조사하는가** — 질문 분해, 검색·수집, 학술·OA 소스 확보. (2) **조사 결과를 어떻게 전처리해 결과물(보고서)을 만드는가** — 가져온 페이지를 노트로 정리하는 과정, 클레임·랭킹·증거 정리, 초안·합성·비평·패치. 스펙을 어디에 쓸지(재구현, 학습 자료 등)는 아직 듣지 못했다.
- **라이선스**: MIT — `LICENSE`(Copyright 2026 Jordan Gibbs), `pyproject.toml:10`(`license = "MIT"`)과 일치. `git ls-files`에서 LICENSE·COPYING·NOTICE 파일은 루트 `LICENSE` 하나뿐이다. (코드 확인)
- **분석 대상 제품**: 루트 Python 패키지 `hyperresearch`(`src/hyperresearch/`, CLI `hyperresearch`·`hpr`). 같은 레포의 별도 배포 단위: 플러그인 마켓플레이스 정의(`.claude-plugin/`, `.codex-plugin/`, `.agents/plugins/`)와 부트스트랩 스킬 `skills/deep-research/`, 벤치 하니스 `codex_bench/`, 로드맵 문서 `docs/roadmap-2.0/`. README가 말하는 호스팅 서비스 hyperresearch.ai는 이 레포에 코드가 없다. (코드 확인: `git ls-files`)
- **스펙 범위**: 승인(2026-11-05) — 행 3~17(핵심 15행. 18 에스컬레이션·1·2 설치·프로필·19·20 부속은 제외, 해당 스펙에서는 경계로만 다룸). 작성 완료(2026-11-05): ready 12 / draft 3(4·5·6행) / 승인 범위 내 미작성 0. 원래 권장안은 10을 뺀 13행이었고 사용자가 10까지 포함해 승인했다.

---

## 2. 프로젝트 개요

README는 hyperresearch를 "Claude Code와 OpenAI Codex용 deep research 하니스"로 소개한다(`README.md:3`). 한 번의 프롬프트로 16단계 파이프라인을 돌려 출처 이력이 붙은 보고서를 만들고, 읽은 모든 소스를 로컬 볼트에 남긴다고 한다(`README.md:19`).

코드를 읽고 확인한 구조는 이렇다. **Python 패키지는 LLM을 부르지 않는다.** `src/hyperresearch` 안에 `anthropic`·`openai` SDK import가 없다(grep 결과 0건. 임베딩만 `core/embed.py:59` `_http_embed`가 Voyage·OpenAI HTTP API를 직접 부른다). 파이프라인의 순서와 판단 기준은 `skills/*.md`(진입 스킬 1개 + 단계 스킬 18개 파일)와 `core/hooks.py` 안의 서브에이전트 프롬프트 상수에 텍스트로 있고, `hyperresearch install`이 프로필 값을 Jinja로 채워 사용자 프로젝트의 `.claude/`(또는 `.agents/`·`.codex/`)에 설치한다. 실행 중에는 호스트 에이전트(Claude Code·Codex)가 스킬을 읽고 서브에이전트를 spawn하며, 수집·저장·검색·검증 같은 결정적인 일만 Bash로 `hyperresearch` CLI를 부른다. (코드 확인: `core/hooks.py:3655`, `skills/hyperresearch.md:25-37`)

그래서 이 레포를 스펙으로 옮길 때 "행동"은 두 층이다. 프롬프트가 정하는 흐름(4~8행)과, CLI가 결정적으로 보장하는 계약(9~18행). 두 층의 접점은 `research/runs/<vault_tag>/`에 쌓이는 산출물 파일 이름과 노트 frontmatter다.

### Feature map

<!--
OSS_ANALYSIS_WORKFLOW.md 2장 4번. 한 행 = 스펙 하나의 작업 단위(디렉터리가 아니라 사용 목적과 검증 경계로 묶은 동작).
- 같은 계약을 구현한 플러그인·추출기류는 한 행(패밀리)으로 묶는다.
- 구분: 핵심 / 부속(라이브러리 본체와 별개인 호스팅 서비스·결제·관리 도구 등). 부속은 스펙으로 쓸지 사용자에게 따로 묻는다.
- 선행: 재구현에 필요한 다른 행의 계약(런타임 호출 관계가 아니다).
- 상태: 미작성(파일 없음, 경로는 코드 표기) / draft / ready. 스펙의 status를 요약하며 스펙을 고칠 때 같이 고친다.
- 분할과 경로는 제안이다. 4장에서 병합·분리하면 고치고 이유를 적는다.
- src 경로는 `repos/hyperresearch/src/hyperresearch/` 기준을 `~`로 줄여 쓴다.
-->

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 설치·플랫폼 어댑터 | `hyperresearch install [--target claude\|codex\|all] [--global] [--steps-only]` → 프로젝트에 볼트·훅·스킬·서브에이전트·`CLAUDE.md`/`AGENTS.md` 블록 설치. 같은 프롬프트를 Claude(마크다운 에이전트·Skill 도구)와 Codex(TOML 에이전트·단계 파일·Stop 훅)로 번역. 프롬프트 내용 자체는 제외 | `~/cli/install.py:19` `install`, `~/core/hooks.py:3655` `install_hooks`·`:3700` `install_global_hooks`·`:3800` `_install_claude_hook`, `~/core/platforms.py` `resolve_targets`, `~/core/codex.py:233` `agent_markdown_to_toml`·`:326` `merge_stop_hook`, `~/core/agent_docs.py:299` | 2 | 핵심 | `capabilities/install-platforms.md` · 미작성 | 코드 확인(진입점·설치 순서) / 전역 설치·`--steps-only`·`--create` 동작은 미확인 |
| 2 | 프로필·템플릿 렌더링·레버 | 스케일 기어(`light`·`full`·`premier`)와 `dissertation` 티어의 수치를 프로필로 두고, `<< p.x >>` 구분자 Jinja로 스킬·에이전트 프롬프트에 채움. 런 시작 때 step 1이 고른 레버(register·domain_notes·inference_depth)를 역할별 shim 파일 4개로 렌더링 | `~/core/profiles.py:112` `Profile`·`:463` `resolve_profile`, `~/core/render.py:50` `prompt_env`·`:85` `render_prompt`, `~/core/levers.py:198` `validate_levers`·`:235` `compose_shims`·`:290` `render_shims`, `~/cli/profile_cmd.py:107`, `~/cli/levers_cmd.py:35` | 없음 | 핵심 | `capabilities/profiles-levers.md` · 미작성 | 코드 확인(진입점·내장 프로필 4개) / 값별 의미는 미확인 |
| 3 | 서브에이전트 로스터 (패밀리 16개) | fetcher, loci-analyst, depth-investigator, source-analyst, corpus-critic, draft-orchestrator, synthesizer, 비평가 4종, patcher, polish-auditor, readability-recommender, cite-checker, browser-fetcher. 각각 역할 프롬프트·모델(`<< p.models.* >>`)·도구 목록을 가짐. patcher·polish-auditor는 `tools: Read, Edit`, synthesizer는 `Read, Write`로 잠금(Claude 쪽만 강제) | `~/core/hooks.py:130` `LOCI_ANALYST_AGENT` … `:3478` `CITE_CHECKER_AGENT`(각 상수 안 frontmatter `tools:`·`model:`), `:3616` `_agent_installers`, `:3871` `_MODEL_ROLE_RE`, `~/core/profiles.py:36` `ModelMap`, `~/core/profiles.py:74` `CodexModelMap`, `~/core/codex.py:123`~`:270`(Codex 번역) | 9, 17 (2는 경계) | 핵심 | [subagent-roster](capabilities/subagent-roster.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 4 | 진입 스킬·분해·티어 라우팅 | `/hyperresearch <질문>` → 부트스트랩(볼트 점검, `vault-tag`, `run init`, `query.md`, `scaffold.md`) → step 1 분해(원자 항목·커버리지 매트릭스·`pipeline_tier`·`response_format`·레버) → 티어별 단계 순서. dissertation만 step 1.5 챕터 분할 | `skills/hyperresearch.md:25-216`, `skills/hyperresearch-1-decompose.md`, `skills/hyperresearch-1-5-chapter-partition.md`, `~/cli/vault_tag.py:81`, `~/cli/run_cmd.py:44` `run_init` | 9 (2는 경계) | 핵심 | [entry-decompose](capabilities/entry-decompose.md) · draft | 코드 확인(R-ID별 수준은 스펙 1.4) / 미결정 2건(스펙 1.4) |
| 5 | 폭 탐색·갭 페치 (2, 13단계) | 검색 계획(폭·깊이·반대 관점) → URL 큐 → 유틸리티 점수 선별 → fetcher 병렬 웨이브 → 커버리지·중복 근거 점검 → 랭킹 신호 저장. 13단계는 비평가가 지적한 빈 곳만 최대 5개 추가 fetch | `skills/hyperresearch-2-width-sweep.md`(2.1~2.8 절), `skills/hyperresearch-13-gap-fetch.md` | 3, 4, 9, 11, 13, 15, 16, 17 (18은 경계) | 핵심 | [width-sweep](capabilities/width-sweep.md) · draft | 코드 확인(R-ID별 수준은 스펙 1.4) / 미결정 8건(스펙 1.4) |
| 6 | 깊이 분석 (3~9단계, full 티어) | 모순 그래프 → loci 분석(점수·소스 예산) → 위치별 depth-investigator가 "Committed position" 보간 노트 작성 → 교차 조정(`comparisons.md`) → 전문가 이견(`source-tensions.json`) → 코퍼스 비평가의 "무엇이 뒤집을까" 점검과 보충 fetch → 증거 다이제스트 | `skills/hyperresearch-3-contradiction-graph.md` … `skills/hyperresearch-9-evidence-digest.md` | 3, 5, 9, 15, 16, 17 | 핵심 | [depth-analysis](capabilities/depth-analysis.md) · draft | 코드 확인(R-ID별 수준은 스펙 1.4) / 미결정 8건(스펙 1.4) |
| 7 | 초안·합성 (10, 11단계) | 각도 3개를 정하고 각도별 소스 20~50개 큐레이션 → draft-orchestrator 3개가 병렬로 초안 → 오케스트레이터가 사실 충돌 점검·계획·개요 → synthesizer가 두 패스로 최종 보고서 작성. light 티어는 단일 초안 | `skills/hyperresearch-10-triple-draft.md`, `skills/hyperresearch-11-synthesize.md` | 3, 9, 15, 16 (4·6은 경계) | 핵심 | [draft-synthesis](capabilities/draft-synthesis.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 8 | 비평·패치·인용 검사·다듬기 (12, 14, 14.5, 15, 16단계) | 비평가 4종 병렬 → findings JSON → patcher가 "수술적 Edit"만 적용(재생성 금지) → 인용-문장 결합 검사와 2차 패치 → 위생·군더더기 제거 → 가독성 권고 선택 적용 | `skills/hyperresearch-12-critics.md`, `-14-patcher.md`, `-14-5-cite-check.md`, `-15-polish.md`, `-16-readability-audit.md` | 3, 7, 9, 10, 15, 17 | 핵심 | [critique-patch-polish](capabilities/critique-patch-polish.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 9 | 런 매니페스트·재개·예산·ship gate | 런마다 `research/runs/<tag>/run.json`·`events.jsonl`. 단계 상태, 지출·개수 상한, 중단 후 `run resume`이 다음 단계 지시. `run finish`가 `verify_run` 통과 시에만 `done`, 실패는 `blocked`. Codex Stop 훅이 런이 진행 중이면 세션 종료를 막음 | `~/core/runs.py:97` `init_run`·`:240` `set_step`·`:469` `resume_position`·`:649` `verify_run`·`:847` `finish_run`, `~/cli/run_cmd.py:184` `run_resume`·`:249` `run_stop_gate`·`:576` `run_finish`, `~/core/codex.py:359` `stop_gate_decision` | 없음 | 핵심 | [run-manifest-gate](capabilities/run-manifest-gate.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 10 | 콘텐츠 검증 배터리 |  `hyperresearch lint` 규칙 26개(실질 24개, `stale-indexes`·`duplicate-ids`는 빈 규칙): quote-integrity(인용문이 볼트 노트에 FTS5 토큰 구문으로 있나), 철회 논문 인용, numeric-consistency, instruction-coverage 등. 필수 제목·길이(±20%)·인용 밀도·스캐폴드 누출은 lint가 아니라 `verify_run`(행 9)의 검사다. cite-check은 문장-인용 쌍을 뽑아 기계 분류하고 모호한 것만 에이전트에 보냄 | `~/cli/lint.py:17` `RULES`·`:110` `_check_quote_integrity`·`:150`·`:200`, `~/core/citecheck.py:178` `extract_pairs`·`:257` `triage_pairs`·`:353` `write_pairs_file`, `~/cli/citecheck_cmd.py:15` | 9, 15, 17 (4는 경계) | 핵심 | [verification-battery](capabilities/verification-battery.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 11 | fetch 엔진 | `hyperresearch fetch <url>`·`fetch-batch` → 중복 URL 거부 → provider로 가져옴 → 로그인 벽·정크(캡차·바이너리·빈 페이지) 판정 → DOI 추출 → 얇으면 OA 복구 → 노트 저장·인덱싱 → 막힌 URL은 에스컬레이션 큐로. 단발 `research <주제>` 명령은 별도 경로 (정정: 정크 판정과 에스컬레이션은 `fetch`와 MCP `fetch_url`에만 있고 `fetch-batch`·`research`에는 없다. 로그인 벽 판정은 둘에도 있다. 근거는 fetch-engine 스펙) | `~/cli/fetch.py:207` `fetch`·`:672` `_escalate_blocked`, `~/core/fetcher.py:86` `fetch_and_save`·`:110` `prepare_fetch`·`:155` `save_fetched`, `~/web/base.py:75` `looks_like_login_wall`·`:104` `looks_like_junk`, `~/cli/fetch_batch.py:21`, `~/cli/research.py:22` | 12, 14, 15, 16 (18은 경계) | 핵심 | [fetch-engine](capabilities/fetch-engine.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 12 | 웹 프로바이더 패밀리 | `[web] provider` 설정이 builtin(기본, `search`는 `NotImplementedError`, `web/builtin.py:200`)·crawl4ai·exa·tavily·parallel·serply 중 하나를 고름. builtin 경로의 요청은 SSRF 관문 `safe_get`을 지남(스킴·사설 IP·파서 불일치·리다이렉트). 외부 API provider의 `fetch`, 학술 API, 임베딩 호출은 관문 밖이고 자격증명 검사는 OA의 `check_oa_url`에만 있음. PDF는 공용 lane. `setup`이 로그인 프로필 TUI | `~/web/base.py:185` `get_provider`·`:54` `WebResult`, `~/web/safe_http.py:289` `check_url`·`:354` `safe_get`, `~/web/pdf.py:142` `extract_pdf`, `~/web/crawl4ai_provider.py:228` `Crawl4AIProvider`, `~/cli/setup.py:18` | 없음 | 핵심 | [web-providers](capabilities/web-providers.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 13 | 학술 검색 클라이언트 | `hpr scholar search <질의>` → 등록된 소스 8개(RePEc는 `available()`이 항상 False라 검색 가능한 것은 7개. OpenAlex·Crossref·CORE·RePEc·DOAB·ClinicalTrials·EDGAR·FRED)를 하나씩 조회 → DOI·정규화 제목+연도로 병합 → `work_type` 태그. 공유 캐시·호스트별 속도 제한. RePEc는 검색 API가 없어 안내만 | `~/cli/scholar_cmd.py:42` `scholar_search`·`:170`, `~/scholar/registry.py:22` `_REGISTRY`, `~/scholar/base.py:113` `Paper`·`:311` `SearchProvider`, `~/scholar/dedup.py:143` `merge_papers`, `~/scholar/providers/` 8개 | 없음 | 핵심 | [scholar-search](capabilities/scholar-search.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 14 | OA 전문 복구 | 얇은 페이지(<6000자)나 읽기 실패 페이지에 DOI가 있으면 Unpaywall → Europe PMC → CORE 순으로 합법 오픈액세스 사본을 찾아 본문을 대체하고, 대체 사실을 배너·frontmatter·출력에 남김. 복구 불가 시 기존 동작 유지 | `~/core/oa.py:187` `needs_oa_recovery`·`:215` `iter_oa_candidates`·`:835` `recover_full_text`·`:859` `rescue_full_text`, `~/core/scholar.py:67` `extract_doi`, `~/core/config.py:164` `ScholarSettings` | 12, 13, 16 | 핵심 | [oa-recovery](capabilities/oa-recovery.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 15 | 볼트 저장·동기화·검색 | 노트는 `research/notes/*.md`(frontmatter+본문)가 원본이고 SQLite는 재구성 가능한 캐시. `sync`가 파일↔DB를 맞추고, 검색은 FTS5(+선택 임베딩 RRF). 웹에서 가져온 본문은 `note show`·`search`가 `<untrusted-source>` 울타리로 감쌈 | `~/core/vault.py:48` `Vault`, `~/core/db.py:230`·`:240` 스키마(`SCHEMA_VERSION = 13`), `~/core/sync.py:84` `compute_sync_plan`·`:148` `execute_sync`, `~/search/fts.py:66` `search_fts`, `~/core/embed.py:170` `semantic_search`, `~/core/untrusted.py:42` `wrap_body`, `~/cli/note.py:164` | 없음 | 핵심 | [vault-store](capabilities/vault-store.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 16 | 소스 품질: 랭킹·독립성·철회 | `sources score`가 DOI 노트에 인용 수·철회 여부를 채우고, `quality_score`=티어·유틸리티·권위·PageRank의 재정규화 합. `graph rank`는 링크 그래프 PageRank. `independence`는 URL·본문(MinHash)·와이어 문구로 파생 사본을 묶어 합의 표를 하나로 셈. 철회는 ship 직전에 캐시 없이 재확인 | `~/core/quality.py:56` `compute_quality_scores`, `~/core/graphrank.py:61` `compute_centrality`, `~/core/scholar.py:406` `score_sources`, `~/core/independence.py:61` `compute_independence`, `~/cli/sources.py:100`·`:171`·`:218` | 15 | 핵심 | [source-quality](capabilities/source-quality.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 17 | 클레임 저장소 | fetcher가 쓴 `claims-<note-id>.json`을 `claims`(+FTS) 테이블로 적재, "어느 소스가 X를 가장 잘 뒷받침하나" 질의, 문헌 매트릭스·공통 대상 묶음. cite-check 기계 분류와 numeric-consistency의 바탕 | `~/core/claims.py:86` `ingest_claims_file`·`:208` `ingest_claims_dir`·`:247` `search_claims`·`:284` `literature_matrix`, `~/cli/claims_cmd.py:28` | 15 | 핵심 | [claims-store](capabilities/claims-store.md) · ready | 코드 확인(R-ID별 수준은 스펙 1.4) / 확인 한계는 스펙 1.4 |
| 18 | 에스컬레이션 큐·브라우저 레인 | 막힌 fetch(로그인·봇 벽)는 버리지 않고 `escalations` 테이블에 enqueue. browser-fetcher가 사용자의 실제 Chrome을 직렬로 몰아 비움. 캡차·2FA·로그인은 `needs_human`으로 모아 사용자에게 한 번에 전달. Codex에는 이 레인이 없음 | `~/core/escalation.py:34` `enqueue`·`:60` `maybe_enqueue_blocked_fetch`·`:93` `claim_next`, `~/cli/escalation_cmd.py:39`~`:268`, `~/core/hooks.py:3352` `BROWSER_FETCHER_AGENT`, `~/cli/fetch.py:672` | 11, 3 | 핵심 | `capabilities/escalation-lane.md` · 미작성 | 코드 확인(큐 함수·명령 목록) / 브라우저 에이전트 절차는 미확인 |
| 19 | 볼트 운영 도구 패밀리 | 노트 CRUD·태그·토픽 트리·인덱스 페이지·배치 상태 변경·중복 탐지·위키링크 자동 삽입·export/import·git·watch·repair·archive-run·템플릿·config·assets. 파이프라인 안에서는 일부(`note show`, `search`, `archive-run`, `lint`)만 불림 | `~/cli/__init__.py:44-152`(등록부), `~/cli/note.py:19`~`:662`, `~/cli/batch.py:100`~, `~/indexgen/generator.py`, `~/core/linker.py`, `~/cli/archive.py:96`, `~/cli/repair.py:13`, `~/cli/import_cmd.py:14` | 15 | 부속 | `capabilities/vault-tools.md` · 미작성 | 코드 확인(등록부) / 명령 본문은 미확인 |
| 20 | 외부 입구·배포 입구·벤치 | MCP 서버(stdio, 도구 13개)와 로컬 웹 UI(`serve`, stdlib HTTP :8080)가 같은 볼트를 읽고 씀. 플러그인 마켓플레이스 2종과 부트스트랩 스킬 `deep-research`가 `pip install` 뒤 `install`을 대신 실행. `codex_bench/`는 DeepResearch-Bench를 Codex로 돌리는 하니스 | `~/mcp/server.py:13` `FastMCP`(`@server.tool` 13개), `~/serve/server.py:343` `HyperresearchHandler`·`:605` `run_server`, `skills/deep-research/SKILL.md`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `codex_bench/harness.py` | 15 | 부속 | `capabilities/external-entries.md` · 미작성 | 코드 확인(도구 개수·라우트 분기·파일 존재) / 각 도구·페이지 동작은 미확인 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1. 런 작업 공간과 산출물 이름 (`research/runs/<tag>/`: `run.json`, `query.md`, `scaffold.md`, `prompt-decomposition.json`, `loci.json`, `comparisons.md`, `critic-findings-*.json`, `patch-log.json`, `polish-log.json`, `cite-check-findings.json`, `temp/`) | 4~10 | `skills/hyperresearch.md:225-241`(단계별 산출물), `~/core/runs.py:1-12`·`:649-847`(`verify_run`이 이름을 검사), `~/core/vault.py:31` `validate_run_tag` | [run-manifest-gate](capabilities/run-manifest-gate.md) 1.3 · ready | 코드 확인(산출물 이름 목록, `verify_run` 검사 이름) / 각 파일의 필드는 미확인 |
| S2. 노트 스키마 (frontmatter 필드, `NoteStatus`·`NoteType`·`Tier`·`ContentType` 어휘, DB CHECK 제약, OA 대체 필드 `oa_*`) | 5, 10, 11, 14~17 | `~/models/note.py:13`~`:40`, `~/core/frontmatter.py`, `~/core/note.py:97` `write_note`, `~/core/db.py:240` | [vault-store](capabilities/vault-store.md) 1.3 · ready | 코드 확인(열거형 4개 위치) / 필드 전체는 미확인 |
| S3. `WebResult` (url·title·content·raw_html·metadata·media·links·screenshot·raw_bytes) | 11, 12, 14, 18 | `~/web/base.py:54` | [web-providers](capabilities/web-providers.md) 1.3 · ready | 코드 확인(필드 목록) |

**대조한 범위와 미탐색 영역**
- 대조: README의 16단계 표와 `skills/hyperresearch.md` 표(둘 다 같은 단계 번호·티어), README 서브에이전트 표 16개와 `core/hooks.py` frontmatter `name:` 16개(이름 일치), README에 예시로 나온 명령(install·setup·search·fetch·run·scholar·sources·claims·escalation·profile·levers 등)과 `cli/__init__.py:44-152` 등록부(루트 명령 19개, 하위 앱 22개), README의 MCP "도구 13개"와 `@server.tool` 13개, README의 웹 프로바이더 6종과 `web/base.py:185` `get_provider`, README의 학술 소스 8개와 `scholar/registry.py:22` `_REGISTRY`.
- 문서와 구현의 차이:
  - Python 버전: README는 "3.11–3.14", `pyproject.toml:11`은 `<3.15`인데, `cli/__init__.py:13`은 3.14 이상에서 "아직 지원하지 않는다"는 경고를 stderr에 낸다(Crawl4AI 상류 이슈). 코드 확인.
  - dissertation 티어: README(`README.md:167`)와 진입 스킬(`skills/hyperresearch.md:94`)은 길이·읽기 예산·인용 목표가 "설정돼 있지만 아직 읽는 곳이 없다(#103)"고 쓰고, `docs/roadmap-2.0/README.md`는 Phase 3 "dissertation scale"을 완료로 표시한다. 그런데 `verify_run`이 `response_format` 키로 `word_targets`를 읽으므로 "읽는 곳이 없다"는 부정확하다. 다만 step 1이 `dissertation` 형식을 내지 않아 dissertation 런은 argumentative 5000~10000단어 ±20% 기준으로 측정된다(추론, [run-manifest-gate](capabilities/run-manifest-gate.md) 2.1).
  - `core/hooks.py:3667` 주석은 "roster (as of v7)"인데 스킬·진입 문구는 V8이다(오래된 주석). 코드 확인.
- 스펙 작성 중 발견한 차이(구현을 사실로 썼다. 세부는 각 스펙 2.1):
  - SSRF 관문은 builtin 경로와 OA 복구에만 있다. exa·tavily·parallel·serply의 `fetch`, 학술 API, 임베딩 호출은 관문 밖이다([web-providers](capabilities/web-providers.md)). `next.md`의 "모든 외부 요청이 `safe_get`을 거치나"에 대한 답은 아니오다.
  - `core/fetcher.py`의 `fetch_and_save`는 호출처가 없다. `looks_like_login_wall`은 부분 문자열 매칭이라 `Association`(`sso`) 같은 제목도 로그인 벽으로 본다([fetch-engine](capabilities/fetch-engine.md)).
  - "verbatim" 인용 검사의 실제 구현은 FTS5 porter 토큰 구문 일치다. `lint`는 error여도 종료 코드가 0이다. `audit-gate`·`scaffold-prompt`는 V8에서 사실상 무동작이다([verification-battery](capabilities/verification-battery.md)).
  - README의 "SQLite 색인 완전 재구성 가능"과 달리 `sources`·`assets`·`claims`·파생 점수는 DB에만 있다. `independence`는 MinHash가 아니라 정확 자카드이고 `quality_score`에 반영되지 않는다. fetcher 프롬프트가 요구하는 클레임 필드 11개 중 5개는 DB에 저장되지 않는다([vault-store](capabilities/vault-store.md), [source-quality](capabilities/source-quality.md), [claims-store](capabilities/claims-store.md)).
  - 소스 8개 중 RePEc는 검색이 불가능하다. 단계 스킬이 언급하는 Semantic Scholar·arXiv·PubMed는 `scholar search`에 없다([scholar-search](capabilities/scholar-search.md), [width-sweep](capabilities/width-sweep.md)).
  - 서브에이전트 프롬프트 3개(instruction-critic·readability-recommender·corpus-critic)는 설치 때 `.format`을 거치지 않아 JSON 예시에 `{{`가 남는다(추론). cite-check findings 스키마는 patcher 프롬프트의 설명과 다르다. `<untrusted-source>` 규칙은 일부 프롬프트에만 있다([subagent-roster](capabilities/subagent-roster.md)).
  - step 4의 "light는 step 9로 건너뛴다"는 낡은 문구이고 실제 순서는 2→10이다. synthesizer 패스 1은 `[N]`, 패스 2는 위키링크를 요구한다([width-sweep](capabilities/width-sweep.md), [draft-synthesis](capabilities/draft-synthesis.md)).
- 미탐색(스펙 작성으로 단계 스킬·서브에이전트 프롬프트·lint 규칙 본문은 읽었다. 각 스펙 `sources` 참조): `tests/`(104개 파일, 기본 제외), `docs/roadmap-2.0/phase-*.md`, `docs/source-search.md`, `example-reports/`, `assets/`, CI·기여 문서, `core/migrations.py`, `core/templates.py`, `core/enrich.py`, `core/patterns.py`, `core/similarity.py`, 행 1·2·18·19·20의 코드. README의 벤치마크(DRACO 순위) 주장은 코드로 확인할 수 없다.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

archify로 도출한 주요 구조도(필수)입니다. 실행 흐름도는 그리지 않았습니다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 사용자 → 호스트 에이전트 → 설치된 스킬·에이전트, 호스트가 Bash로 부르는 CLI와 그 아래 모듈, 볼트 |

검증: archify `finalize`의 validate·deliver·check·browser-check 4개 게이트 통과(`structure.finalize.json`, 검사한 SHA `aece65f`). 1차 실행에서 `oa → net`과 `fetch → vault`가 교차한다는 권고가 나와 노드 위치만 바꿔 다시 돌렸고, 2차는 권고 없이 통과했다. 이후 스펙 작성 중 드러난 두 라벨(학술 소스 수, `safe_get`이 builtin 경로 관문이라는 점)을 고쳐 한 번 더 finalize했고(3차) 4게이트 통과·진단 0건이다. 화면 캡처를 사람이 눈으로 확인하지는 않았다(visual review 미실시).

### 그림 해설

**읽는 순서**
1. 왼쪽 위 줄: 설치기가 스킬·에이전트 프롬프트를 설치한다. 왼쪽 아래 줄: 사용자 질문이 호스트 에이전트로 들어가고, 호스트가 설치된 스킬을 읽고 서브에이전트를 띄운다.
2. 호스트 → `hyperresearch CLI`: 호스트와 서브에이전트가 Bash로 CLI를 부르는 지점이다. 파이프라인에서 결정적인 일은 모두 여기서 시작한다.
3. CLI 오른쪽 열: 학술 검색, fetch 엔진(+OA 복구), 런·ship gate, 검증 배터리, 소스 품질. 오른쪽 끝에 외부 서비스(위)와 볼트(아래).

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 설치기 | 프로필 값을 채워 스킬·에이전트·훅을 사용자 프로젝트에 씀 | 입력: 대상 플랫폼, 프로필, 볼트 경로. 출력: `.claude/`·`.agents/`·`.codex/` 파일 | `~/cli/install.py:19`, `~/core/hooks.py:3655`, `~/core/render.py:85` | 코드 확인(진입점·설치 순서) |
| 스킬·에이전트 (설치된 프롬프트) | 진입 스킬이 단계 순서·티어를 정하고 단계 스킬 18개가 절차를, 서브에이전트 16개가 역할을 정함 | 호스트가 읽음. 산출물 파일 이름으로 서로 연결 | `skills/hyperresearch.md:59-80`, `~/core/hooks.py:3616`·`:4388` | 코드 확인(목록) / 본문 미확인 |
| 호스트 에이전트 | 오케스트레이터. 스킬을 읽고 서브에이전트를 spawn하고 CLI를 부름. Codex는 Stop 훅이 진행 중인 런을 종료하지 못하게 막음 | 입력: 사용자 질문. 출력: `final_report_<tag>.md` | `skills/hyperresearch.md:25-37`, `~/core/codex.py:359` | 코드 확인(스킬 지시·훅 판정) / 호스트 내부는 범위 밖 |
| hyperresearch CLI | typer 앱. 명령과 하위 앱을 등록 | 입력: 호스트의 Bash 호출, 출력: `--json` 결과 | `~/cli/__init__.py:44-152`, `pyproject.toml:65-67` | 코드 확인(등록부) |
| 학술 검색 | 소스 8개를 순차 조회·병합 | 입력: 질의·범위·연도. 출력: 병합된 `Paper` 목록 | `~/cli/scholar_cmd.py:42`, `~/scholar/registry.py:22`, `~/scholar/dedup.py:143` | 코드 확인(진입점) |
| fetch 엔진 | URL 하나를 가져와 판정하고 노트로 저장, 막히면 에스컬레이션 | 입력: URL·태그·`--suggested-by`. 출력: 노트, 큐 항목 | `~/cli/fetch.py:207`, `~/core/fetcher.py:86`, `~/web/base.py:185` | 코드 확인(분기 이름) |
| OA 전문 복구 | 얇은 페이지·실패 페이지를 오픈액세스 사본으로 대체 | 입력: DOI. 출력: 대체 본문과 `oa_*` 필드 | `~/core/oa.py:835`, `:859` | 코드 확인(시그니처·호출 위치) |
| 런·ship gate | 런 상태 저장, 재개, 완료 판정 | 입력: 단계 기록, 볼트. 출력: `run.json`, `passed` | `~/core/runs.py:97`, `:649`, `:847` | 코드 확인(진입점·검사 이름) |
| 검증 배터리 | 인용문·철회·인용 결합 검사. 런이 이 규칙을 직접 부름 | 입력: 최종 보고서, 볼트. 출력: 오류 목록 | `~/cli/lint.py:110`·`:200`, `~/core/citecheck.py:178`, `~/core/runs.py:789` | 코드 확인(호출 연결) |
| 소스 품질 | 점수·독립성·클레임 | 입력: 노트·DOI·클레임 JSON. 출력: 점수·클러스터·테이블 행 | `~/core/quality.py:56`, `~/core/independence.py:61`, `~/core/claims.py:208` | 코드 확인(진입점) |
| 볼트 | 마크다운 노트 + SQLite 인덱스(FTS, 링크, 클레임, 에스컬레이션 등 테이블 13개와 FTS 가상 테이블 2개) | 입력: 노트 파일. 출력: 검색·그래프 | `~/core/vault.py:48`, `~/core/db.py:230`, `~/core/sync.py:84` | 코드 확인(테이블 이름) |
| 웹·학술 API | 외부 요청 대상. builtin 경로의 요청만 `safe_get`/`check_url`을 지나고, 외부 API provider·학술 API·임베딩 호출은 관문 밖 | — | `~/web/safe_http.py:289`·`:354` | 코드 확인(web-providers 스펙 R-08에서 호출부 확인) |
| MCP·웹 UI | 같은 볼트를 읽고 씀(MCP 도구 13개, 웹 UI 라우트 `/`·`/note/`·`/tag/`·`/search`·`/graph`) | — | `~/mcp/server.py:13`, `~/serve/server.py:365`·`:605` | 코드 확인(등록·라우트 분기) |

**미확인 영역**
- 그림에 넣지 않은 것: 에스컬레이션 큐와 브라우저 레인(행 18), 프로필·레버 렌더링(행 2), Stop 훅 판정의 호출 경로, 플러그인 부트스트랩 스킬(행 20), 볼트 운영 도구(행 19). 웹 프로바이더 6종은 fetch 엔진 안에 묶었다.
- 서브에이전트가 CLI를 직접 부르는 줄은 따로 그리지 않았다(호스트 → CLI 한 줄로 표현). 서브에이전트별 호출 명령은 subagent-roster 스펙에 있다.
- 검증 배터리 → 볼트, 소스 품질 → 볼트 줄은 "그 모듈이 볼트 DB를 읽고 쓴다"는 뜻이고, 쓰는 컬럼은 확인하지 않았다.

---

## 4. 질문 (Questions)

사용자 질문의 답입니다. 확정된 동작은 기능 스펙에 반영하고 여기서는 결론만 적습니다.

사용자 질문은 아직 없다. 아래는 스펙 작성 결과 사용자 결정이 필요한 항목이다.

- **`research/wrapper_contract.json` 스펙 추가 여부**: 하니스가 두는 외부 계약 파일인데, lint(`lint.py:710-825`·`:1396-1510`)와 분해 단계가 읽는데도 소유 스펙이 없다. 새 기능 후보로 올릴지 정해야 한다([verification-battery](capabilities/verification-battery.md) 보고).
- **draft 3개의 미결정**: [entry-decompose](capabilities/entry-decompose.md) 2건(챕터 모드의 단계별 변형, 전역 step 6·11 기록 키), [width-sweep](capabilities/width-sweep.md) 8건, [depth-analysis](capabilities/depth-analysis.md) 8건. 대부분 원본이 정하지 않은 형식이다. 이 레포는 프롬프트가 규칙이라 코드를 더 읽어도 답이 나오지 않을 수 있다. 메인 세션이 판단해 "구현자가 정해야 하는 값"으로 닫을지 정해야 한다.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: [capabilities/](capabilities/) 15개(ready 12 / draft 3). 2절 feature map의 "스펙·상태" 칸에 링크
