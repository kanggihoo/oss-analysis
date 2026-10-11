# OpenAlice — 질문·답변 검증 기록

- 분석 SHA: `87bc415260aaac92a072d89a1c6440268a3efdf1`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 1
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | `simulate`·`calculate` 도구가 에이전트에게 닿는 경로(MCP 포함)가 있는가 | Q1 | 해소 | R1 |
| R1-Q2 | CCXT `getFundingRate`가 에이전트 CLI로 노출되는가 | Q1 | 없음 확정 | R1 |
| R1-Q3 | 한국 심볼(`005930.KS`)이 검색→barId→봉 조회까지 통과하는 코드 경로 | Q1 | 해소 | R1 |
| R1-Q4 | FMP 키가 없을 때 `equityGetRatios`의 실제 동작 | Q2 | 해소 | R1 |
| R1-Q5 | RSS 조회 인덱스가 재시작 시 디스크에서 복구되는가, 조회 가능한 최대 과거 범위 | Q2 | 해소 | R1 |
| R1-Q6 | 발사 마커가 "디스패치 성공"과 "실행 성공" 중 언제 기록되는가 | Q3 | 해소 | R1 |
| R1-Q7 | 앱 중단 중 놓친 cron 슬롯이 재시작 후 발사되는가 | Q3 | 해소 | R1 |
| R1-Q8 | 헤드리스 Issue에서 `agent` 생략 시 쓰이는 런타임의 기본값 | Q4-2 | 해소 | R1 |
| R1-Q9 | `allowAiTrading=true`일 때 AI push가 브로커까지 가는 경로와 중간 게이트 | Q4-5 / Q6 | 해소 | R1 |
| R1-Q10 | 에이전트가 `allowAiTrading`을 스스로 켤 수 있는 경로가 있는가 | Q4-5 / Q6 | 해소 | R1 |
| R1-Q11 | 사후 수익률 채점 장치가 정말 없는가 (조사 범위 확장) | Q4-7 | 없음 확정 | R1 |
| R1-Q12 | 어댑터가 에이전트 런타임의 웹 검색을 켜거나 끄는 인자를 넘기는가 | Q5 | 없음 확정 | R1 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. `simulate`·`calculate` 도구의 도달 경로
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` 1.1절 표 마지막 행과 바로 아래 문단은 두 도구가 ToolCenter에 등록되지만 `CLI_EXPORTS`에 없어서 "MCP 서버로만 닿을 수 있다는 것은 `추론`", 워크스페이스가 `/mcp/:wsId`를 쓰는지는 `미확인`이라고 적었다. `03-decision.md` 4-7절은 이 전제로 `simulate`를 "CLI에 노출되지 않음"이라고 다시 썼고, `next.md` 미확인 체크리스트의 "MCP 경로" 항목도 같은 내용이다. 이 도구가 에이전트에게 닿지 않으면 데이터 인벤토리에서 빠져야 한다.
- 질문: 고정 SHA 기준으로 Chat 템플릿 워크스페이스에서 실행되는 에이전트(대화형·헤드리스)가 `simulate` 또는 `calculate` 도구를 호출할 수 있는 경로가 하나라도 있는가? (`.mcp.json` 생성, 어댑터 실행 인자의 MCP 설정, `bootstrap.mjs`/`_common.mjs`, MCP 서버 `enabled` 기본값을 바꾸는 코드 포함)
- 답변 완료 조건: 경로가 있다면 MCP 설정 파일을 생성하거나 어댑터에 넘기는 `파일:라인`과 원문, 그리고 MCP 서버 활성 조건. 없다면 `.mcp`, `mcpServers`, `/mcp/`, `enableAllProjectMcpServers` 등으로 `src/workspaces/`, `src/server/`, `default/` 전체를 grep한 조사 범위.

#### R1-Q2. CCXT `getFundingRate`의 에이전트 노출 여부
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` 1.2절 "코인 전용 / 펀딩비" 행은 UTA ToolCenter에 `trading-ccxt` 그룹으로 등록된다는 것까지 확인했지만, `alice-uta` CLI로 노출되지 않는다는 부분은 "것으로 보임"(`추론`)으로 끝났다. `05-boundary-and-fit.md` 7.4절도 이 전제를 그대로 쓴다.
- 질문: `getFundingRate`(또는 `trading-ccxt` 그룹)를 에이전트가 `alice-uta` CLI나 다른 경로로 호출할 수 있는가?
- 답변 완료 조건: `alice-uta` CLI 노출 목록(`cli-commands.ts` 또는 UTA 쪽 export)에서 해당 도구가 있거나 없음을 보여주는 `파일:라인` 원문. UTA 서비스 ToolCenter 도구를 CLI 게이트웨이가 자동 노출하는 코드가 있다면 그 위치도.

#### R1-Q3. 한국 심볼의 검색→봉 조회 경로
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` 1.4절 "한국" 행은 yfinance 벤더 설명문의 "KR (.KS)" 문구만 근거로 "입력이 가능하다는 것이 설계 의도"라고 적었고 검증은 `추론`이다. `next.md` 미확인 체크리스트에도 "한국 `.KS` 실제 동작"이 남아 있다. 우리 시스템(키움)과 직접 관련된다.
- 질문: 에이전트가 `alice market search`로 `005930.KS`(또는 "Samsung")를 찾고 그 결과로 `alice market bars`를 부를 때, 심볼 검색 결과에 한국 종목이 포함되고 `yfinance|005930.KS` 같은 barId로 봉 조회가 진행되는 코드 경로가 있는가? 접미사 `.KS`/`.KQ`를 거부하거나 변환하는 분기가 있는가?
- 답변 완료 조건: `aggregate-search.ts`와 yfinance equity 검색·historical fetcher에서 심볼을 처리하는 `파일:라인`과 원문. 실제 Yahoo 응답 내용은 정적 확인 불가로 분리해서 적는다.

#### R1-Q4. FMP 키가 없을 때 `equityGetRatios` 동작
- GUIDE 항목: Q2
- 왜 묻는가: `00-overview.md` 7절 표의 `traderhub/SKILL.md:10-12` 행과 `next.md` 미확인 체크리스트는 "`provider: 'fmp'` 고정이고 hub 대체가 없다"까지만 확인하고 키가 없을 때 실패 형태는 `추론`이라고 했다. 스킬 문서는 "no API keys needed"라고 주장하므로 문서와 코드의 모순 여부가 이 답에 달려 있다.
- 질문: FMP 키가 설정되지 않은 상태에서 `traderhub equity ratios`를 호출하면, 요청 전에 코드가 키 부재를 감지해 오류를 내는가, 키 없이 FMP에 요청을 보내는가, 아니면 hub 키 프록시 같은 대체 경로를 타는가?
- 답변 완료 조건: `tool/equity.ts`의 해당 호출에서 opentypebb FMP fetcher의 자격 증명 확인까지 따라간 호출 순서와 각 단계 `파일:라인` 원문, 그리고 `credential-map.ts`에서 FMP가 hub 센티널 대상인지 아닌지를 보여주는 라인.

#### R1-Q5. RSS 조회 인덱스의 재시작 복구와 최대 과거 범위
- GUIDE 항목: Q2
- 왜 묻는가: `01-data.md` 2.4·2.5절과 `04-research.md` 5-4절은 조회 인덱스가 "메모리 2000건·7일"이고 디스크 JSONL은 보관하지만 검색 도구는 인덱스만 본다고 적었다. 그런데 앱을 재시작하면 메모리 버퍼가 비는지, 디스크에서 최근분을 다시 읽어 채우는지가 적혀 있지 않다. 이것에 따라 재시작 직후 `grepRss`/`windowRss` 결과가 비는지가 달라지고, `next.md` "분석 중 생긴 질문" 3번(retrospective의 과거 뉴스 요구)도 여기에 걸려 있다.
- 질문: 프로세스 시작 시 `news/store.ts`는 디스크 JSONL에서 메모리 인덱스를 복구하는가? 복구한다면 어떤 기준(건수, 기간)으로 몇 건을 올리는가?
- 답변 완료 조건: store 초기화 함수의 `파일:라인`과 원문, 그 함수를 부르는 호출처(`main.ts` 등), 복구 시 적용되는 2000건·7일 상수의 위치.

#### R1-Q6. 발사 마커 기록 시점: 디스패치 성공인가 실행 성공인가
- GUIDE 항목: Q3
- 왜 묻는가: `02-schedule.md` 3.2절은 "디스패치가 성공한 뒤에만 마커를 씀"(`scanner.ts:385`)이라고 적었고, `03-decision.md` 4-6절 "헤드리스 실행 실패" 행은 "발사 마커는 쓰지 않음(다음 틱에 재시도 대상으로 남음)"이라고 적었다. 앞의 것은 프로세스를 띄운 시점, 뒤의 것은 실행 결과가 실패인 경우를 말하는 것으로 읽혀 두 문서가 서로 다른 동작을 주장한다. 실행이 실패할 때마다 다음 틱에 다시 발사되는지(반복 발사)가 이 답에 달려 있다.
- 질문: `dispatchIssue`가 반환하는 시점은 헤드리스 프로세스를 띄운 직후인가, 프로세스가 끝난 뒤인가? 그리고 헤드리스 프로세스가 비정상 종료(오류 코드, timeout)해도 마커는 이미 기록된 상태인가?
- 답변 완료 조건: `dispatchIssue`의 반환 지점과 그 안에서 프로세스 시작을 await하는지 완료를 await하는지 보여주는 `파일:라인` 원문, 마커 기록 라인, 그리고 실행 실패 시 마커를 지우거나 재발사를 유도하는 코드가 있는지(없으면 조사 범위).

#### R1-Q7. 앱이 꺼져 있던 동안 놓친 cron 슬롯의 처리
- GUIDE 항목: Q3
- 왜 묻는가: `02-schedule.md` 3.2절 안에서 세 문장이 서로 맞물리지 않는다. "`cron`은 `now − 스캔간격`을 기준(방금 지난 슬롯만 잡음)", "중단 중 놓친 창은 다음 스캔에서 한 번만 발사(큐가 아님)", "놓친 발사(busy/용량)는 기본 catch-up". 앞 문장대로라면 앱이 몇 시간 꺼져 있던 동안의 cron 슬롯은 재시작 후 잡히지 않고, 뒤 두 문장대로라면 한 번 발사된다. 처음 읽는 사람은 "08:30 장전 분석이 PC가 꺼져 있었다면 켜질 때 실행되는가"에 답할 수 없다.
- 질문: `cron` 일정이고 `catchUp`을 지정하지 않은 Issue에서, 앱이 해당 cron 슬롯 시각을 포함해 수 시간 꺼져 있다가 다시 켜지면 첫 스캔에서 그 슬롯이 발사되는가? 마커가 있는 경우와 없는 경우(처음 보는 Issue)를 나눠서.
- 답변 완료 조건: `isDue`/`computeNextRun`에서 cron 기준점을 정하는 분기의 `파일:라인` 원문, 마커가 있을 때 기준점이 마커인지 `now − 간격`인지, `catchUp`(및 `noteCronMiss`)이 앱 중단 상황에도 적용되는지에 대한 코드 근거.

#### R1-Q8. 헤드리스 Issue에서 `agent`를 생략했을 때의 런타임
- GUIDE 항목: Q4-2
- 왜 묻는가: `03-decision.md` 4-2절 "기본 에이전트" 행은 헤드리스 기본 런타임이 `issueDefaultAgent` 설정이라고만 적고 그 기본값을 적지 않았다(`config.ts:237`). 판단 주체가 어느 LLM CLI인지가 이 레포 판단 흐름의 출발점인데, 기본값과 미설정 시 해석 순서가 비어 있다.
- 질문: Issue frontmatter에 `agent`가 없고 사용자가 설정을 바꾸지 않은 경우, 스캐너가 헤드리스 실행에 쓰는 어댑터는 무엇이며 어떤 순서로 결정되는가? (Issue `agent` → 소유 세션 → 워크스페이스 템플릿 `defaultAgents` → `issueDefaultAgent` 등)
- 답변 완료 조건: `issueDefaultAgent` 스키마 기본값 원문(`config.ts`), 스캐너/디스패치에서 어댑터를 해석하는 함수의 `파일:라인`과 분기 순서 원문.

#### R1-Q9. `allowAiTrading=true`일 때 AI push가 브로커까지 가는 경로
- GUIDE 항목: Q4-5 / Q6
- 왜 묻는가: `03-decision.md` 4-5절과 `05-boundary-and-fit.md` 6.1절은 `trading.ts:833-845`를 근거로 "AI가 직접 push"한다고 적었지만, 그 다음 단계(메인 프로세스 → UTA 서비스 HTTP → `UnifiedTradingAccount` push)에서 `expectedPendingHash` 요구, 인증, 가드 외에 추가 게이트가 있는지는 확인하지 않았다. `next.md` "분석 중 생긴 질문" 1번이 이 내용이다. 문서와 주석("only humans can push")이 틀렸다는 판단이 이 경로 전체에 기대고 있다.
- 질문: `allowAiTrading=true`일 때 `tradingPush` 도구 호출이 브로커 주문 전송까지 이어지는 호출 순서는 무엇이며, 그 사이에 사람 승인·해시 확인·인증 토큰 등 실행을 막을 수 있는 게이트가 있는가?
- 답변 완료 조건: `tool/trading.ts`의 push 분기부터 UTA 서비스의 push 처리 함수까지 호출 순서대로 `파일:라인`과 원문. AI 경로가 `expectedPendingHash`를 어떻게 채우는지(자동으로 현재 해시를 넣는지)도 포함.

#### R1-Q10. 에이전트가 `allowAiTrading`을 스스로 켤 수 있는가
- GUIDE 항목: Q4-5 / Q6
- 왜 묻는가: `03-decision.md` 4-1절과 `05-boundary-and-fit.md` 6.1절은 매니지드 실행이 `--dangerously-skip-permissions`와 샌드박스 비활성으로 돌아 "안전 경계는 UTA 쪽 승인에 있다"고 했고, 승인 면제 조건은 "UI에서 위험 경고+이중 확인 뒤에만 켜짐"(`추론`, 주석 근거)이라고 적었다. 그러나 에이전트가 설정 파일을 직접 쓰거나 설정 변경 도구·HTTP 라우트를 호출해서 이 스위치를 켤 수 있다면 "기본은 사람 승인"이라는 결론이 약해진다.
- 질문: 에이전트(셸·파일 쓰기 가능, 워크스페이스 디렉터리에서 실행)가 `allowAiTrading`을 `true`로 바꿀 수 있는 경로가 있는가? (설정 파일이 저장되는 위치와 워크스페이스 디렉터리의 관계, 설정 변경 HTTP 라우트의 인증 유무, ToolCenter/CLI의 설정 변경 도구)
- 답변 완료 조건: `allowAiTrading`이 저장되는 파일 경로와 로드·실시간 반영 코드(`main.ts:249-256` 근처) 원문, 설정 쓰기 라우트의 `파일:라인`과 인증 처리 원문, CLI/도구 중 설정을 쓰는 것이 있는지(없으면 `allowAiTrading`, `trading.json`, `writeConfig` 등 grep 범위).

#### R1-Q11. 사후 수익률 채점 장치 부재의 재확인
- GUIDE 항목: Q4-7
- 왜 묻는가: `03-decision.md` 4-7절 "사후 수익률 채점" 행과 `next.md` 미확인 체크리스트 마지막 항목은 `hit-rate, outcome, post-mortem, scorecard` 네 키워드로만 "없음"을 확인했다고 스스로 적었다. 조사 범위가 좁아서 "없음 확정"으로 보기 어렵다. 특히 UTA 쪽 스냅샷 스케줄(`02-schedule.md` 3.3절)이나 정기 리포트 루틴이 과거 commit 이후 손익을 계산하는지 확인되지 않았다.
- 질문: 과거 판단(TradingGit 커밋, thesis 노트, Inbox 리포트, 정기 루틴)을 이후 가격이나 손익과 대조해 자동으로 평가·기록하는 코드가 `src`, `services`, `default/skills` 어디에도 없는가?
- 답변 완료 조건: 있다면 위치와 원문. 없다면 확장 패턴(예: `pnl`, `realized`, `performance`, `evaluate`, `review`, `backtest`, `retro`, `score`, `accuracy`, `benchmark`, `snapshot`)과 대상 디렉터리, 그리고 UTA 스냅샷 스케줄이 저장하는 내용과 그것을 판단 평가에 쓰는 소비처 유무.

#### R1-Q12. 어댑터가 런타임 웹 검색을 켜거나 끄는가
- GUIDE 항목: Q5
- 왜 묻는가: `04-research.md` 5-1절 마지막 행은 Codex 어댑터가 `web_search` 이벤트를 표시용으로 파싱한다는 것만 확인하고 "이 레포가 켜고 끄지 않는다"고 결론 냈으며, 런타임이 실제로 검색한다는 부분은 `추론`이다. 그런데 "켜고 끄지 않는다"는 부분은 정적으로 확인 가능하다(어댑터가 넘기는 실행 인자·설정). `00-overview.md` 핵심 발견 5도 같은 전제를 쓴다.
- 질문: 9개 어댑터 중 claude, codex 두 어댑터가 대화형·헤드리스 실행 시 넘기는 인자와 설정(예: Claude Code의 `--allowedTools`/`--disallowedTools`, Codex의 `--search`나 `web_search` 관련 config)에 웹 검색·웹 읽기 도구를 켜거나 막는 항목이 있는가?
- 답변 완료 조건: `adapters/claude.ts`, `adapters/codex.ts`(및 Codex app-server 전송 코드)에서 실행 명령·설정을 합성하는 `파일:라인`과 원문 전체 인자 목록, 그리고 웹 관련 항목의 유무. 런타임 기본 동작(인자가 없을 때 검색이 켜지는지)은 정적 확인 불가로 분리해서 적는다.

### 답변 (답변자)

#### R1-Q1 답변
- 결론: **확정**. 기본 설정(MCP 꺼짐)에서는 Chat 워크스페이스의 어떤 에이전트(대화형·헤드리스)도 에이전트 도구 인터페이스로는 `simulate`/`calculate`에 닿지 못한다. MCP를 켠 경우에 한해 **Codex 대화형·Web 세션**만 MCP로 닿는다(Claude와 모든 헤드리스는 MCP 배선이 없다). 이와 별개로, 셸을 쓰는 에이전트가 loopback HTTP `/api/tools/:name/execute`를 직접 호출하면 MCP·CLI 게이트를 우회해 두 도구를 실행할 수 있는 코드 경로가 존재한다. 보고서 정정 필요: `01-data.md` 1.1절 "MCP 서버로만 닿을 수 있다는 것은 추론 / 워크스페이스가 `/mcp/:wsId`를 쓰는지 미확인"은 아래 사실로 대체돼야 하고, `.mcp.json`은 워크스페이스에 주입되지 않는다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/main.ts:247`, `:274` | `toolCenter.register` | `toolCenter.register(createThinkingTools(), 'thinking')` / `toolCenter.register(createSimulateTools(barService), 'simulate')` | 코드 확인 |
  | `src/tool/thinking.ts:16`, `src/tool/simulate.ts:18` | 도구 이름 | `calculate: tool({` (수식 계산기, `thinking` 그룹) / `simulate: tool({` (진입 1회+청산 규칙 1개 백테스트) | 코드 확인 |
  | `src/server/cli-commands.ts:52-58`, `:267`, `:271` | `CLI_EXPORTS` data/uta | analysis 그룹은 `'search-bars': 'searchBars', quant: 'calculateQuant', snapshot: 'marketSnapshot'`뿐. 파일 전체에 `simulate`는 `'price-change': 'simulatePriceChange'`(MockBroker 전용) 한 곳, `calculate`(수식)는 없음. `// cron: deliberately NOT exported — scheduling stays MCP-only.` | 코드 확인 |
  | `src/server/cli.ts:295-296`, `:303` | `/invoke` 게이트 | `if (!mappedToolNames(c.req.param('export')).has(toolName)) { return c.json({ error: \`Unknown CLI command tool: ...\` }, 404)` → CLI로는 매핑된 도구만 실행 | 코드 확인 |
  | `src/core/config.ts:355-358` | `mcpSchema` | `enabled: z.boolean().default(false), port: ...default(3001)` — MCP 기본 꺼짐 | 코드 확인 |
  | `src/main.ts:337-346`, `:351-362` | MCP 활성 조건 | `const mcpEnabled = envMcpEnabled === '1' \|\| ((envMcpEnabled === undefined \|\| envMcpEnabled === '') && config.mcp.enabled === true)`; `const mcpBaseUrl = mcpEnabled ? \`http://127.0.0.1:${config.mcp.port}/mcp\` : undefined`; 켜지면 `new McpPlugin(...)`, 꺼지면 `LocalToolGatewayPlugin`(CLI 전용) | 코드 확인 |
  | `apps/desktop/src/main.ts:853`, `:944` | 데스크톱 | `const mcpEnabled = parseEnabledEnv(process.env['OPENALICE_MCP_ENABLED']) ?? mcpFile.enabled` → 자식에 `OPENALICE_MCP_ENABLED: mcpEnabled ? '1' : '0'` | 코드 확인 |
  | `src/server/mcp.ts:81-92`, `:208-213` | 전역 `/mcp` | `const tools = await toolCenter.getMcpTools()` 후 전 도구 `mcp.registerTool(...)`; `app.all('/mcp', ...)`. `src/core/tool-center.ts:45-47`의 `getMcpTools()`는 `getVercelTools()`(tools.json의 disabled만 제외)이므로 `simulate`·`calculate`가 포함됨 | 코드 확인 |
  | `src/server/mcp.ts:215-242` | `/mcp/:wsId` | `workspaceToolCenter.build({workspaceId: wsId, ...})` — 워크스페이스 도구(issue/inbox/peer 등)만 노출하는 별도 카탈로그. `simulate`·`calculate`는 여기에 없음 | 코드 확인 |
  | `src/workspaces/service.ts:1256` | spawn env | `...(opts.mcpBaseUrl ? { OPENALICE_MCP_URL: opts.mcpBaseUrl } : {}),` — MCP 꺼짐이면 env 자체가 없음. `src/workspaces/spawn-env.ts:27`은 상속된 `'OPENALICE_MCP_URL'`을 STRIP 목록에 넣어 외부 값이 새지 않게 함 | 코드 확인 |
  | `src/workspaces/adapters/codex.ts:702-720` | `codexMcpConfigArgs` | `const mcpUrl = ctx.env['OPENALICE_MCP_URL']; if (!mcpUrl) return [];` … `` `mcp_servers.openalice.url="${mcpUrl}"` ``, `` `mcp_servers.openalice-workspace.url="${mcpUrl}/${workspaceId}"` `` — 전역 `/mcp`(두 도구 포함)와 `/mcp/:wsId` 둘 다 등록 | 코드 확인 |
  | `codex.ts:239-251`, `:301-312`, `:685` | 대화형·Web | `composeCommand`→`codexMcpHead`(685행에 `...codexMcpConfigArgs(ctx)`), `composeWebCommand`(306행 `...codexMcpConfigArgs(ctx)`) | 코드 확인 |
  | `codex.ts:255-262`, `:263-297` | 헤드리스 | `// Headless codex is CLI-MODE, NOT MCP: \`codex exec\` cancels EVERY MCP tool call ...` / `// No mcp_servers head` — 헤드리스에는 MCP 플래그가 없음 | 코드 확인 |
  | `adapters/claude.ts:80`, `:235-236`, `:264-280`, `:290-304` | Claude | 인자는 `'--settings', AUTOTRUST_SETTINGS, '--dangerously-skip-permissions'`와 모델·effort뿐이며 `--mcp-config`가 없음. `AUTOTRUST_SETTINGS = '{"enableAllProjectMcpServers":true,"sandbox":{"enabled":false}}'`는 `.mcp.json`이 있을 때의 신뢰 설정일 뿐 서버를 만들지 않음. 156-157·254-256행 주석("MCP wiring for claude is handled by the template's `.mcp.json`")은 낡은 주석 | 코드 확인 |
  | `src/workspaces/context-injector.spec.ts:49-53`; `tests/integration/workspace-creation/workspace-creation.spec.ts:147-148`, `:256-262` | 주입 테스트 | `describe('injectWorkspaceContext — no MCP injection (CLI-only)'` / `it('never writes .mcp.json, even for a tool-bearing template'` / `expect(existsSync(join(dir, '.mcp.json'))).toBe(false);`. `context-injector.ts`·`workspace-creator.ts`·`templates/chat/bootstrap.mjs`에 `.mcp.json`/`mcpServers` 쓰기 코드 없음(grep 0건) | 코드 확인 |
  | `.mcp.json`(레포 루트) | 개발용 | `"url": "${OPENALICE_MCP_URL:-http://127.0.0.1:47332/mcp}"` — OpenAlice 소스 레포 자체를 Claude Code로 열 때의 설정. 워크스페이스는 `~/.openalice/workspaces/<id>`(`src/workspaces/config.ts:78-81`)에 만들어지므로 해당 없음 | 코드 확인 |
  | `src/webui/plugin.ts:231-235`, `:274`; `src/webui/routes/tools.ts:56-76`; `src/webui/middleware/auth.ts:79-85` | HTTP 직접 호출 | `app.route('/api/tools', createToolsRoutes(ctx.toolCenter))`, `app.post('/:name/execute', ...)`가 `toolCenter.get(name)`의 모든 도구(`simulate`·`calculate`·`tradingPush` 포함)를 실행. 인증은 `trustedProxies.size === 0`이고 loopback이며 Origin 헤더가 없으면 통과 | 코드 확인 |

- 동작 설명:
  1. 두 도구는 `main.ts`에서 메인 프로세스 ToolCenter에 등록된다(`simulate`=그룹 `simulate`, `calculate`=그룹 `thinking`).
  2. CLI(`alice`/`traderhub`/`alice-uta`)는 `/cli/:wsId/:export/invoke`에서 `mappedToolNames`에 든 도구만 실행한다. 두 도구는 매핑에 없어서 404다.
  3. MCP는 `mcp.enabled`(기본 false) 또는 `OPENALICE_MCP_ENABLED=1`일 때만 서버가 뜨고 `OPENALICE_MCP_URL`이 spawn env에 들어간다. 이때 Codex 어댑터만 `-c mcp_servers.openalice.url=...`로 전역 `/mcp`를 등록하므로, Codex 대화형 TUI와 Web(app-server) 세션은 두 도구를 호출할 수 있다. 헤드리스 Codex는 MCP 플래그가 없고(`codex exec`는 사람 승인이 없어 MCP 호출을 취소함), Claude 어댑터는 `--mcp-config`도 `.mcp.json` 주입도 하지 않는다.
  4. 따라서 "Chat 템플릿 + 기본 설정 + Claude 또는 헤드리스" 조합에서 에이전트 도구 인터페이스로 닿는 경로는 0개다. 다만 에이전트가 셸에서 `curl -X POST http://127.0.0.1:<web포트>/api/tools/simulate/execute`를 직접 치는 경로는 코드상 열려 있다(웹 포트 기본 47331, 인증 우회 조건은 Q10 참조). 이 경로는 스킬 문서가 안내하는 경로가 아니다.
- 조사 범위: `grep -rniI "mcp"`를 `src/`, `default/`, `services/`, `apps/`, `packages/`, `ui/`, `scripts/` 전체에 실행하고 `.mcp.json`·`mcpServers`·`/mcp/`·`enableAllProjectMcpServers`·`OPENALICE_MCP_URL`·`OPENALICE_MCP_ENABLED`·`mcp_servers`를 따로 grep. 어댑터 9종(`adapters/*.ts`)의 mcp 언급 전수 확인(claude·codex 외에는 `opencode.ts:245`, `pi.ts:209-218`의 "CLI-only, MCP 없음" 주석뿐이고 `web-session/acp-transport.ts:55`는 `mcpServers: []`). `src/workspaces/templates/{chat,auto-quant-v2,auto-prediction}/`에 `.mcp.json` 쓰기 없음. 호출 체인: `main.ts:337`(활성 판정) → `service.ts:1256`(env) → `spawn-env.ts:27`(strip) → `codex.ts:702`(플래그) 순으로 끝까지 추적.

#### R1-Q2 답변
- 결론: **없음 확정**. `getFundingRate`(`trading-ccxt` 그룹)는 UTA 서비스 프로세스 안의 별도 `ToolCenter`에 등록될 뿐, 그 ToolCenter를 읽는 코드(HTTP 라우트, MCP, CLI 게이트웨이)가 없다. 에이전트는 `alice-uta` CLI로도, 다른 어떤 경로로도 호출할 수 없다. 보고서의 "것으로 보임"은 "없음 확정"으로 올려도 된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `services/uta/src/domain/trading/brokers/ccxt/ccxt-tools.ts:42` | `getFundingRate: tool({` | 도구 정의(설명에 "CCXT/crypto accounts only"). `createCcxtProviderTools(manager)`가 `getFundingRate`와 `getOrderBook`을 반환 | 코드 확인 |
  | `services/uta/src/domain/trading/uta-manager.ts:107`, `:137` | 등록 | `this.toolCenter?.register(createCcxtProviderTools(this), 'trading-ccxt')` | 코드 확인 |
  | `services/uta/src/main.ts:66-67`, `:90` | UTA 전용 ToolCenter | `const toolCenter = new ToolCenter()` / `const utaManager = new UTAManager({ eventLog, toolCenter })` / `utaManager.registerCcxtToolsIfNeeded()` | 코드 확인 |
  | `services/uta/src/main.ts:169-174`, `services/uta/src/types.ts:20-30` | 라우트 컨텍스트 | `const tradingCtx: UTAEngineContext = { utaManager, fxService, snapshotService }` — `toolCenter`는 라우트에 전달되지 않음 | 코드 확인 |
  | `src/services/uta-client/UTAManagerSDK.ts:60-61` | 메인 프로세스 쪽 | `/** No-op on the Alice side; UTA owns the CCXT tool registration. */ registerCcxtToolsIfNeeded(): void { /* no-op */ }` | 코드 확인 |
  | `src/server/cli-commands.ts:212-262` | `alice-uta` 목록 | account(list/info/portfolio), contract(search/details/quote/expand/option-contracts/option-chain/`'order-book': 'getOrderBook'`), order, position, git, market(`clock`), sim(`price-change`). `getFundingRate`/`funding` 없음 | 코드 확인 |
  | `src/tool/trading.ts:498-507` | `getOrderBook` | 메인 프로세스의 일반 거래 도구로 별도 구현(`uta.getOrderBook(request)` → HTTP). 즉 같은 CCXT 그룹의 호가창은 노출되지만 펀딩비는 노출되지 않음 | 코드 확인 |
  | `src/server/cli.ts:295-296` | 게이트 | CLI는 `mappedToolNames`에 있는 도구만 실행 | 코드 확인 |

- 동작 설명: CCXT 계정이 연결되면 UTA 서비스가 자기 ToolCenter에 `getFundingRate`·`getOrderBook`을 등록한다(`uta-manager.ts:107/137`). 그러나 UTA 서비스가 외부에 여는 것은 `/api/trading`, `/api/simulator`, `/__uta/*` 라우트뿐이고(`services/uta/src/main.ts:150-176`) 라우트 컨텍스트에 ToolCenter가 없다. 메인 프로세스(OpenAlice 본체)의 ToolCenter에는 `createTradingTools`로 만든 `getOrderBook`은 있으나 `getFundingRate`는 없고, 메인 쪽 `UTAManagerSDK.registerCcxtToolsIfNeeded`는 no-op이다. 그래서 CLI(`alice-uta`), MCP(`/mcp`), `/api/tools/:name/execute`(메인 ToolCenter 기준) 어디에도 이 도구가 없다. `CcxtBroker.getFundingRate`(`CcxtBroker.ts:1360`)는 UTA 안의 브로커 메서드로만 존재한다. 보고서 `05-boundary-and-fit.md` 7.4절의 "펀딩비는 에이전트에 안 닿는다"는 전제는 맞다.
- 조사 범위: `grep -rn "getFundingRate|trading-ccxt|createCcxtProviderTools|registerCcxtToolsIfNeeded|funding"`를 `src/`, `services/`, `default/`, `packages/uta-protocol`에서 실행. `ToolCenter`를 import하는 `services/` 파일 전수(`uta/src/main.ts`, `uta-manager.ts` 두 곳뿐)와 `toolCenter` 사용처 전수 확인(읽기 호출 `get/getVercelTools/getMcpTools/getInventory`는 services에 0건). UTA HTTP 라우트(`routes-trading.ts`, `routes-simulator.ts`, `routes-trading-wallet`)에서 `tool|funding|invoke|exec` 패턴 0건. 메인 `src/`의 `getFundingRate` 0건(`src/domain/market-data/reference/term-structure.ts`, `src/tool/economy.ts`의 `funding` 언급은 다른 의미).

#### R1-Q3 답변
- 결론: **확정**(코드 경로). `005930.KS`를 막거나 변환하는 코드는 어디에도 없고, `yfinance|005930.KS`라는 barId로 봉 조회까지 같은 경로로 흘러간다. 한국 종목 전용 분기·벤더도 없다(오직 Yahoo 심볼 그대로 전달). 단, Yahoo 응답 자체(검색에 삼성전자가 잡히는지, 차트 데이터가 오는지)는 **정적 확인 불가**로 분리한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/server/cli-commands.ts:43-45` | CLI 매핑 | `search: 'marketSearchForResearch', 'search-bars': 'searchBars', bars: 'getMarketBars'` | 코드 확인 |
  | `src/tool/market.ts:37-43` | `marketSearchForResearch` | `const results = await aggregateSymbolSearch(deps, query, limit ?? 20)` | 코드 확인 |
  | `src/main.ts:211-216` | 벤더 목록 | `return [...new Set([md.providers.equity, ...md.extraVendors])]` (`providers.equity` 기본 `'yfinance'`: `core/config.ts:315`) | 코드 확인 |
  | `src/domain/market-data/aggregate-search.ts:89`, `:93-95` | 로컬 SEC 인덱스 | `const primaryEquity = equityVendors[0] ?? 'yfinance'`; `deps.symbolIndex.search(q, boundedLimit)`. 인덱스는 `symbol-index.ts:40` `const SOURCES = ['sec'] as const`(미국 전용)이라 한국 종목은 안 걸림 | 코드 확인 |
  | `aggregate-search.ts:111-117` | 온라인 equity 검색 | `deps.equityClient.search({ query: q, provider: v, is_symbol: false })` — 활성 벤더마다(기본 yfinance) 호출 | 코드 확인 |
  | `aggregate-search.ts:132-146` | 병합 | `const key = \`${vendor}\|${sym.toUpperCase()}\``…`equityOnlineResults.push({ ...r, symbol: sym, assetClass: 'equity', sourceId: vendor })` — 접미사 필터·변환 없음 | 코드 확인 |
  | `packages/opentypebb/src/providers/yfinance/models/equity-search.ts:42-52` | Yahoo 검색 | `const quotes = await searchYahooFinance(query.query)` … `.filter((q: any) => q.quoteType === 'EQUITY')` → `symbol: q.symbol ?? ''`. 헤더 주석에 "reaches global exchanges — China A-shares (600519.SS), Taiwan (2330.TW), Vietnam (VIC.VN), HK" (KR은 예시에 없음) | 코드 확인 |
  | `yfinance/utils/helpers.ts:373-383` | `searchYahooFinance` | `(yf as any).search(query, { quotesCount: 20, newsCount: 0 }, { validateResult: false })` | 코드 확인 |
  | `src/domain/market-data/bars/bar-service.ts:332-352` | `searchBars` | `barId: formatBarId(provider, symbol)` → `yfinance\|005930.KS` (`types.ts:45-47`: `` `${sourceId}|${nativeSymbol}` ``) | 코드 확인 |
  | `bar-service.ts:419-423`, `:424-447` | `getBars` | 심볼+assetClass면 `getVendorBars(deps.vendorProviders[ref.assetClass]=yfinance, ...)`. barId면 `parseBarId`(`types.ts:39-43`, 첫 `\|`로 분리) → `utaManager.has('yfinance')` 아님 → assetClass 없으면 `aggregateSymbolSearch`로 정확 일치(`String(hit.symbol ?? hit.id ?? '') === parsed.nativeSymbol` 및 sourceId 일치) 확인 → `return getVendorBars(parsed.sourceId, assetClass!, parsed.nativeSymbol, opts)` | 코드 확인 |
  | `bar-service.ts:226` | 호출 | `raw = await deps.equityClient.getHistorical(p({ interval: opts.interval }))` | 코드 확인 |
  | `yfinance/models/equity-historical.ts:44`, `:50` | historical fetcher | `const symbols = query.symbol.split(',')...` → `getHistoricalData(sym, {...})`; `helpers.ts:305` `yf.chart(symbol, { period1, period2, interval, includePrePost })` — 심볼을 그대로 Yahoo에 전달 | 코드 확인 |
  | `packages/opentypebb/src/standard-models/equity-historical.ts:9` | 심볼 정규화 | `symbol: z.string().transform((v) => v.toUpperCase())` — 대문자화만 함(`.KS`는 그대로) | 코드 확인 |
  | `yfinance/index.ts:55-56` | 벤더 설명 | `coverage: 'Global default — US, plus CN (.SS/.SZ), HK (.HK), TW (.TW/.TWO), JP (.T), KR (.KS), EU and more.'` (문구일 뿐 기능 분기는 아님). yfinance 프로바이더에 `credentials`가 없어 키 없이 호출됨 | 코드 확인 |

- 동작 설명: `alice market search "005930.KS"` → `marketSearchForResearch` → `aggregateSymbolSearch`가 (1) SEC 로컬 인덱스(미국 전용, 0건), (2) 활성 equity 벤더(기본 yfinance)의 Yahoo `/v1/finance/search`를 호출해 `EQUITY` 타입 결과를 `{symbol, name, assetClass:'equity', sourceId:'yfinance'}`로 합친다. 결과에는 barId 필드가 없으므로 `alice market search-bars 005930.KS`(`searchBars`)가 같은 검색을 돌린 뒤 `barId: 'yfinance|005930.KS'`를 만들어 준다. `alice market bars --barId 'yfinance|005930.KS' [--asset-class equity]`는 `getBars`에서 vendor 분기로 가 `yf.chart('005930.KS', ...)`를 호출한다. assetClass를 생략하면 검색으로 정확 일치 심볼을 한 번 더 확인하고(실패 시 `Cannot uniquely resolve asset class ...`, 이때는 assetClass를 명시하라는 메시지), `symbol`+`assetClass: equity`로 부르면 검색 없이 바로 yfinance로 간다. 한국용 분기(`.KS`/`.KQ` 거부·변환)는 `src`·`packages`·`services` 어디에도 없다. `equity.ts:32`의 `.TW/.TWO` 라우팅만 대만 전용으로 존재한다.
- 정적 확인 불가(분리 기재):
  - 갈리는 곳: `searchYahooFinance`(`helpers.ts:379-381`)가 받는 Yahoo 응답, `yf.chart`(`helpers.ts:305`)가 돌려주는 데이터.
  - 경우의 수: (a) Yahoo가 `005930.KS`(EQUITY)를 반환 → 검색·barId 생성·barId 단독 조회 모두 통과. (b) 반환 못함(검색어 "Samsung" 등이 안 잡히거나 429/crumb 오류) → 검색은 빈 결과/오류이나 `symbol`+`assetClass` 직접 조회나 `--asset-class equity`가 있는 barId 조회는 통과 가능. (c) 차트가 비면 `emptyHistoricalError`/`classifyYahooFetchError`(`helpers.ts:310-318`)로 오류가 전달됨. 이 중 어느 쪽인지는 실행 시점의 Yahoo 응답에 달려 있다.
  - 이 레포는 키움(또는 KRX) 브로커·벤더가 없다(`grep -rniE "kiwoom|krx|kospi|kosdaq|upbit|bithumb"`의 `src/services/packages/default` 결과: 경제지표·OECD 국가 목록 언급뿐).
- 조사 범위: `grep -rnE "\.KS|\.KQ|\.SS|\.HK|\.TW|suffix"` (`src/domain/market-data`, `src/tool`, `packages/opentypebb`), `aggregate-search.ts`·`bar-service.ts`·`types.ts`·`market.ts`·`quant.ts:17-26`·`market-bars.ts`·yfinance `equity-search/equity-historical/helpers` 전체 열람. 벤더 디렉터리(`packages/opentypebb/src/providers/`: bls cboe deribit eastmoney ecb econdb eia federal_reserve fmp imf intrinio multpl oecd sec twse yfinance)에 KR 전용 없음.

#### R1-Q4 답변
- 결론: **확정**. FMP 키가 없으면 **요청을 보내기 전에** opentypebb `QueryExecutor.filterCredentials`가 키 부재를 감지해 `OpenBBError("Missing credential 'fmp_api_key'. Check https://financialmodelingprep.com to get it.")`를 던진다. 키 없이 FMP로 요청하지 않고, hub 대체 경로도 없다(FMP는 hub 센티널 대상이 아님). 따라서 `traderhub/SKILL.md`의 "Data is served hub-first ... with local fallback — no API keys needed"는 `equity ratios`에 대해서는 **코드와 모순**이다(보고서의 `provider: 'fmp'` 고정 지적은 맞음).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `default/skills/traderhub/SKILL.md:12-13` | 스킬 문구 | `balance sheet". Data is served hub-first (hosted TraderHub) with local fallback — no API keys needed.` | 코드 확인 |
  | `src/server/cli-commands.ts:84` (traderhub.equity) | 매핑 | `ratios: 'equityGetRatios'` | 코드 확인 |
  | `src/tool/equity.ts:104`, `:107` | `equityGetRatios` | `const params: Record<string, unknown> = { symbol, provider: 'fmp', ttm: ttm ?? 'include' }` / `return await equityClient.getFinancialRatios(params)` | 코드 확인 |
  | `src/domain/market-data/client/typebb/equity-client.ts:96-98` | 클라이언트 | `return this.request<FinancialRatiosData>('/fundamental/ratios', params)` | 코드 확인 |
  | `src/domain/market-data/client/typebb/base-client.ts:35-43` | `request` | `const provider = (params.provider as string) ?? this.defaultProvider` … `return this.executor.execute(provider, model, cleanParams, this.credentials)` | 코드 확인 |
  | `src/main.ts:187`, `:232` | 자격증명·허브 래퍼 | `const credentials = buildSDKCredentials(config.marketData.providerKeys, config.marketData.hub)`; `equityClient = withHubCalendars(equityClient, config.marketData.hub)` | 코드 확인 |
  | `src/domain/market-data/hub-data.ts:16-20`, `:58-62` | 허브 범위 | `getCalendarEarnings`/`getCalendarIpo`/`getCalendarDividend` 세 개만 프록시. `getFinancialRatios`는 `Reflect.get(target, prop, target)`로 원본 그대로 | 코드 확인 |
  | `src/domain/market-data/credential-map.ts:17`, `:56-60` | 센티널 | `fmp: 'fmp_api_key'`는 사용자 키 매핑뿐이고, 허브 센티널은 `for (const field of ['federal_reserve_api_key', 'eia_api_key', 'bls_api_key'])`에만 `hub:<baseUrl>`을 채움 — FMP 없음 | 코드 확인 |
  | `packages/opentypebb/src/providers/fmp/index.ts:79`, `:83` | FMP 프로바이더 | `website: 'https://financialmodelingprep.com'`, `credentials: ['api_key']` → `provider.ts:82-87`이 `fmp_api_key`로 접두 | 코드 확인 |
  | `packages/opentypebb/src/core/provider/abstract/fetcher.ts:68` | 기본값 | `static requireCredentials = true`. `fmp/models/financial-ratios.ts`에는 override 없음(grep 0건) | 코드 확인 |
  | `packages/opentypebb/src/core/provider/query-executor.ts:51-78`, `:97-102` | 검증 | `if (!v) { if (requireCredentials) { ... throw new OpenBBError(\`Missing credential '${c}'.${extraMsg}\`) } }` → `execute`가 `fetcher.fetchData(...)` 호출 **전에** `filterCredentials(...)` 실행 | 코드 확인 |
  | `src/core/mcp-export.ts:115-135`, `src/server/cli.ts:340-345` | 오류 전달 | `text: \`Error: ${message}\``, `isError: true` → `return c.json({ error: text \|\| 'tool error' }, 500)` | 코드 확인 |
  | `src/workspaces/cli/bin/openalice-cli.cjs:168-174`, `:434-437` | CLI 종료 | `fail(msg)` → `process.stderr.write(BIN + ': ' + msg + '\n'); process.exit(1)` | 코드 확인 |
  | `src/core/config.ts:25-50` | 키 출처 | `~/.openalice/provider-keys.json`(또는 `OPENALICE_GLOBAL_DIR`)의 전역 키가 `providerKeys` 빈 칸을 채움 — 이것이 유일한 키 공급원(UI 설정 포함) | 코드 확인 |

- 동작 설명: `traderhub equity ratios --symbol X` → CLI 게이트웨이 `/invoke` → `equityGetRatios.execute` → `provider: 'fmp'` 고정 → `executor.execute('fmp','FinancialRatios',...)` → `filterCredentials`가 `provider.credentials=['fmp_api_key']`를 검사. 로컬 설정·전역 키 파일 어디에도 FMP 키가 없으면 `creds['fmp_api_key']`가 비어 있어 즉시 `OpenBBError`가 던져지고, 네트워크 요청(`https://financialmodelingprep.com/stable/ratios...`, `financial-ratios.ts:94-100`)은 발생하지 않는다. 사용자에게는 stderr에 `traderhub: Error: Missing credential 'fmp_api_key'. Check https://financialmodelingprep.com to get it.`가 찍히고 종료 코드 1이다. 키가 있으나 무효하면 다른 경로다: `financial-ratios.ts:103-104`의 `getDataMany(...).catch(() => [])`가 오류를 삼키고 빈 결과면 `EmptyDataError('No data found for given symbols.')`(141행)가 난다(참고).
- 조사 범위: `src/tool/equity.ts`, `equity-client.ts`, `base-client.ts`, `route-map.ts`, `main.ts:180-235`, `hub-data.ts` 전체, `credential-map.ts` 전체, opentypebb `fetcher.ts`·`query-executor.ts`·`provider.ts`·`fmp/index.ts`·`fmp/models/financial-ratios.ts`, `cli.ts`·`mcp-export.ts`·`openalice-cli.cjs`의 오류 경로. `grep -rn "requireCredentials"`로 FMP 모델의 override 유무 확인.

#### R1-Q5 답변
- 결론: **확정**. `NewsCollectorStore.init()`가 프로세스 시작 시(`main.ts:169`) 디스크 JSONL을 읽어 인덱스를 복구한다. 기준은 "`pubTs`가 지금−7일 이후인 레코드만 올리고, 그중 최신 2000건만 유지"(둘 다 기본값이며 `news.json`으로 변경 가능)다. 복구 후 런타임에는 시간 기반 제거가 없고 건수 제한만 있다. 따라서 재시작해도 최근 분은 비지 않는다. 또 `readRss`(id 조회)는 인덱스가 아니라 디스크 전체를 본다 — 보고서의 "검색 도구는 인덱스만 본다"는 `globRss/grepRss/windowRss`에만 해당하므로 `readRss`에 대해서는 보고서 정정 필요.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/main.ts:165-169` | 생성·초기화 | `const newsStore = new NewsCollectorStore({ maxInMemory: config.news.maxInMemory, retentionDays: config.news.retentionDays })` / `await newsStore.init()` (유일한 호출처, 뉴스 활성 여부와 무관하게 항상 실행) | 코드 확인 |
  | `src/domain/news/store.ts:21-23` | 상수 | `DEFAULT_LOG_PATH = dataPath('news-collector', 'news.jsonl')`, `DEFAULT_MAX_IN_MEMORY = 2000`, `DEFAULT_RETENTION_DAYS = 7` | 코드 확인 |
  | `src/domain/news/config.ts:24`, `:26` | 설정 기본값 | `maxInMemory: z.number().int().positive().default(2000)`, `retentionDays: z.number().int().positive().default(7)` (`main.ts`가 이 값을 store에 전달) | 코드 확인 |
  | `store.ts:74-121` | `init()` | `raw = await readFile(this.logPath, 'utf-8')`; `const retentionCutoff = Date.now() - this.retentionDays * 24 * 60 * 60 * 1000`; 각 줄 `this.dedupSet.add(record.dedupKey)`(전체 이력); `if (record.pubTs >= retentionCutoff) { this.buffer.push(record) }`; `this.buffer.sort(...)`; `if (this.buffer.length > this.maxInMemory) { this.buffer = this.buffer.slice(-this.maxInMemory) }` | 코드 확인 |
  | `store.ts:118-120` | 로그 | `news-collector-store: recovered ${this.dedupSet.size} dedup keys, ${this.buffer.length} items in memory` | 코드 확인 |
  | `store.ts:176-188` | 런타임 | 디스크 `appendFile` 후 `this.buffer.push(record)`, `if (this.buffer.length > this.maxInMemory) { this.buffer = this.buffer.slice(-this.maxInMemory) }` — 나이 기준 제거 없음, 디스크 파일은 append-only(정리·압축 코드 없음) | 코드 확인 |
  | `store.ts:229-257` | `getNewsV2` | `this.buffer.filter(...)`만 사용 — 인덱스 전용. `lookback`은 `parseLookback`의 `h`/`d`만 허용 | 코드 확인 |
  | `store.ts:260-279` | `getNewsById` | 버퍼에 없으면 `createReadStream(this.logPath ...)`로 디스크를 줄 단위로 스캔해 `record?.seq === id`를 찾음 | 코드 확인 |
  | `src/domain/news/query/archive.ts:208`, `:257-258`, `:299-310` | 도구 설명·호출 | `globRss/grepRss/windowRss`는 `provider.getNewsV2(...)`; `readRss`는 `provider.getNewsById ? await provider.getNewsById(id) : ...` ("The collector can retrieve retained disk records even after they leave the recent search index.") | 코드 확인 |
  | `main.ts:265-267`, `:421-438` | 수집·등록 | `if (config.news.enabled) { toolCenter.register(createNewsArchiveTools(newsStore), 'rss') }`; 수집기는 `config.news.feeds.length > 0`일 때만 시작 | 코드 확인 |

- 동작 설명: 앱 시작 → `main.ts:169` `init()` → JSONL 전체를 읽으며 모든 `dedupKey`를 `dedupSet`에 넣고(재시작해도 과거 기사 재수집·중복 방지), `pubTs`가 7일 이내인 기록만 버퍼에 올린 뒤 `pubTs` 오름차순 정렬하고 2000건 초과분은 오래된 것부터 버린다. 이후 검색 도구는 이 버퍼만 본다. 그러므로 `windowRss`로 조회 가능한 최대 과거 범위는 (a) 재시작 직후: `min(7일, 최신 2000건)`, (b) 장기 실행 중: 최신 2000건(7일 제한 없음 — 런타임엔 나이 필터가 없고 기사량이 적으면 7일보다 오래된 것도 남음)이다. 발행 시각(`pubTs`)이 오래된 기사를 피드가 새로 내려주는 경우, 런타임에는 올라가지만 재시작 후 7일을 넘었으면 빠진다. 7일보다 과거(예: retrospective 스킬의 "4월 초" 뉴스)는 `readRss`로 id를 직접 알 때만 디스크에서 읽을 수 있고, 검색·창 조회로는 불가능하다 — `next.md`의 3번 질문에 대한 답.
- 조사 범위: `src/domain/news/` 전체(`store.ts`, `config.ts`, `query/archive.ts`, `collector/`, `index.ts`), `src/tool/news.ts`(re-export), `main.ts` 165-169·265-267·327-457(호출처 전수), `grep -rn "newsStore\|NewsCollectorStore"`.

#### R1-Q6 답변
- 결론: **확정**. `dispatchIssue`는 헤드리스 프로세스가 **끝난 뒤가 아니라**, 실행 레코드를 만들고 `runHeadlessTaskMethod(...)`를 **await 없이 시작시킨 직후** `{taskId, resumeId}`를 반환한다. 마커(`markers.set`)는 그 반환 직후 기록되므로, 프로세스가 비정상 종료·timeout·기동 실패를 해도 마커는 **이미 기록된 상태**이고 다음 틱에 자동 재발사되지 않는다(재시도는 사람이 `alice issue retry`로만). **보고서 정정 필요**: `03-decision.md` 4-6절 "헤드리스 실행 실패" 행의 "발사 마커는 쓰지 않음(다음 틱에 재시도 대상으로 남음)"은 틀렸다. 마커를 쓰지 않는 경우는 "디스패치 **자체**가 throw한 경우(용량 초과·busy·어댑터 headless 미지원·resume 불가 등)"뿐이다. `02-schedule.md` 3.2절 "디스패치가 성공한 뒤에만 마커를 씀"은 "실행 성공"이 아니라 "디스패치 수락"이라는 뜻으로 정확히 고쳐 써야 한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/workspaces/schedule/scanner.ts:373-392` | `fire` | `const { taskId: runId } = await this.dispatchIssue(...)` 다음 줄 `await this.deps.markers.set(issueWorkspace.id, taskId, nowMs)` | 코드 확인 |
  | `scanner.ts:393-402` | 예외 | `catch (err) { // Capacity / busy: every stays due with no marker... await this.noteCronMiss(...); this.deps.logger.info('schedule.fire_skipped', ...)` | 코드 확인 |
  | `scanner.ts:571-583`, `:617` | 디스패치 | `await this.deps.dispatch(executionWorkspace, adapter, what, origin, ...)` 후 `return result` | 코드 확인 |
  | `src/workspaces/service.ts:2392` | 주입 | `dispatch: dispatchHeadlessTaskMethod,` | 코드 확인 |
  | `service.ts:2124-2129` | 비동기 시작 | `await dispatchDelivery.accepted(rec);` 직후 `// Fire-and-forget: run to natural exit, then fill the record.` / `const completion = runHeadlessTaskMethod(ws, adapter, prompt, timeoutMs, {` — `await`가 없음 | 코드 확인 |
  | `service.ts:2311-2316` | 반환 | `headlessDispatchCompletions.add(completion); void completion.then(...)` ... `return { taskId: rec.taskId, resumeId: rec.resumeId };` — `completion`은 기다리지 않음 | 코드 확인 |
  | `service.ts:2151-2186`, `:2190-2198` | 종료 후 처리 | `.then(async (r) => { ... const status = headlessTaskStatus(r); ... headlessTasks.complete(rec.taskId, { status, ... exitCode, killed ...})`; `r.processStarted === false`면 `runtime.spawn_failed` 기록 — 이후에도 마커는 건드리지 않음 | 코드 확인 |
  | `src/workspaces/headless-task.ts:130-143`, `:524` | 실패 판정 | `if (result.killed \|\| result.exitCode !== 0) return 'failed'`; timeout은 `const softKill = timeoutMs === undefined ? undefined : setTimeout(() => { killed = true; terminate(); }, timeoutMs)` | 코드 확인 |
  | `src/workspaces/schedule/marker-store.ts:73-82`, `:85-94` | 마커 API | `set`, `hold`, `prune`만 있고 삭제·초기화 메서드는 없음. `src` 전체에서 `markers.set/hold`는 `scanner.ts:385`, `:421`, `:424`뿐 | 코드 확인 |
  | `scanner.spec.ts:375-394` | 테스트 | `it('does not repeat an occurrence after dispatch registered a run that later fails'` — 주석 "Dispatch acceptance means the durable run exists. Its asynchronous launch/result may fail later, but that is one recorded occurrence and must not turn the scanner interval into an automatic retry loop." 후 `expect(dispatch).toHaveBeenCalledTimes(1)`, `expect(markers.get('w1','t1')).toBe(NOW)` | 코드 확인 |
  | `service.ts:2368-2371`, `scanner.ts:184-230` | 수동 재시도 | `canRetryIssueRun`은 최신 run이 `failed`/`interrupted`일 때만 true; `runIssueNow`(= `alice issue run/retry`)는 마커를 건드리지 않음(주석 "without touching its firing marker") | 코드 확인 |
  | `scanner.ts:584-607` | 예외적 경계 | `@new-then-resume`에서 `claimFreshSession`이 없으면 `throw new Error('Issue @new-then-resume ownership cannot be persisted ...')` — 이 경우 워커는 이미 시작됐는데 마커가 안 써짐(`this.deps.claimFreshSession`이 주입되는 실제 서비스(`service.ts:2393`)에서는 해당 없음). claim 쓰기 실패는 `logger.warn`만 하고 정상 진행(마커 기록) | 코드 확인 |

- 동작 설명: 틱 → `scanWorkspace`가 due를 판정(`scanner.ts:327`) → `fire` → `dispatchIssue`(스캐너 자체 중복 방지 `dispatchingIssues`, `isIssueRunning`, 어댑터 해석, headless 지원 확인) → `dispatchHeadlessTaskMethod`: 용량(`MAX_CONCURRENT_HEADLESS`) 확인, 세션 확보, `headlessTasks.create`로 실행 레코드 생성, 비동기로 프로세스 실행 시작 후 `{taskId, resumeId}` 반환 → `fire`가 마커를 `nowMs`로 기록. 프로세스의 종료 코드·timeout·기동 실패는 이후 `.then`/`.catch`에서 레코드(`failed`/`interrupted`)로만 남는다. 결과적으로: (1) 디스패치 도중 throw(용량·busy·resume 불가 등) → 마커 없음 → `every`는 다음 틱에 다시 due, `cron`은 catch-up이면 `held` 커서가 남아 다음 틱에 재시도(`noteCronMiss`), (2) 실행 실패 → 마커 있음 → 다음 예정 시각(마커+간격 또는 다음 cron 슬롯)까지 재발사 없음. "반복 발사"는 (1)에서만 일어난다.
- 조사 범위: `scanner.ts`(전체), `marker-store.ts`, `schedule/declaration.ts`, `service.ts:1713-1730·1890-2352·2367-2455`, `headless-task.ts`, `scanner.spec.ts` 해당 케이스. `grep -rnE "markers\.(set|hold|delete|clear)|scheduleMarkers\.|retryOfTaskId|autoRetry|auto-retry"`로 마커 삭제·자동 재시도 코드 부재 확인.

#### R1-Q7 답변
- 결론: **확정**. 마커(마지막 발사 기록)가 **있으면** 앱이 몇 시간 꺼져 있었더라도 재시작 후 **첫 스캔에서 놓친 슬롯을 한 번 발사**한다(여러 슬롯이 밀려 있어도 한 번, 큐 아님). `catchUp`을 지정하지 않으면(`undefined`) 이 동작이 기본이고, `catchUp: false`여도 **앱 중단**에는 영향이 없다(`catchUp`은 "발사 시도가 용량/busy로 거부된 경우"에만 슬롯을 소비할지 정함). 마커가 **없으면**(처음 보는 Issue, 마커 파일 유실, 또는 마커가 prune된 경우) 기준점이 `now − 스캔간격(60초)`이라 지난 슬롯은 잡히지 않고 이미 지나 있으면 발사되지 않는다. 08:30 장전 분석 질문의 답: 한 번이라도 발사된 적 있는 Issue라면 PC를 14:00에 켰을 때 첫 스캔(켠 뒤 약 1분 후)에 08:30 슬롯이 발사된다(장전이 아니라 14:00에 실행됨).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/workspaces/schedule/declaration.ts:88-101` | `fireBase` | `if (when.kind !== 'cron') return lastFiredAtMs ?? 0` / `if (heldAtMs !== null && (lastFiredAtMs === null \|\| heldAtMs >= lastFiredAtMs)) { return heldAtMs }` / `if (lastFiredAtMs !== null) return lastFiredAtMs` / `return nowMs - lookbackMs` | 코드 확인 |
  | `src/workspaces/schedule/scanner.ts:353-358` | `isDue` | `const next = computeNextRun(when, fireBase(when, last, nowMs, this.intervalMs, held)); return next !== null && next <= nowMs` (`lookbackMs`=`this.intervalMs`=기본 `DEFAULT_INTERVAL_MS = 60_000`, `scanner.ts:62`) | 코드 확인 |
  | `src/core/schedule-expr.ts:76-77`, `:88-101` | `computeNextRun`(cron) | `afterMs` 이후 첫 cron 시각(`CronExpressionParser.parse(expr, { currentDate: new Date(afterMs), tz })` → `parsed.next().getTime()`) — 마커 직후 첫 슬롯 하나만 반환 | 코드 확인 |
  | `scanner.ts:385` | 발사 후 마커 | `await this.deps.markers.set(issueWorkspace.id, taskId, nowMs)` — 마커는 "슬롯 시각"이 아니라 **발사 시점 `nowMs`**이므로 밀린 슬롯 전체가 소비됨 | 코드 확인 |
  | `src/core/schedule-expr.ts:41-43` | `scheduleCatchesUp` | `return schedule.kind !== 'cron' \|\| schedule.catchUp !== false` | 코드 확인 |
  | `scanner.ts:405-425` | `noteCronMiss` | `fire`의 `catch`(디스패치 throw)에서만 호출. `if (!scheduleCatchesUp(when)) { ... await this.deps.markers.hold(wsId, taskId, nowMs); return }` / `if (last === null) await this.deps.markers.hold(wsId, taskId, dueAt - 1)` — 코드 어디에도 "앱 시작 시 밀린 슬롯을 버린다"는 분기는 없음 | 코드 확인 |
  | `scanner.spec.ts:694-715` | 테스트 | `it('consumes every elapsed cron slot when catchUp is false'` — 마커가 `NOW - 10 * 60_000`(오래된 마커)인데 `catchUp: false`여도 `expect(dispatch).toHaveBeenCalledTimes(1)`(오래된 슬롯을 한 번 시도), 디스패치가 거부되면 `getHeld`가 `NOW`로 소비됨 | 코드 확인 |
  | `scanner.spec.ts:631-645` | 마커 없음 | `it('fires a never-fired cron issue whose occurrence is within the last tick (not never)'` / `it('does not fire a never-fired cron whose next occurrence is far in the future'` | 코드 확인 |
  | `src/workspaces/schedule/marker-store.ts:44-58`, `:9-11` | 영속 | `load`는 파일이 없거나 깨지면 `// missing or corrupt -> start clean`. 파일은 `service.ts:2364`의 `join(config.launcherRoot, 'state', 'schedule-markers.json')`. 헤더 주석 "a window missed during downtime fires exactly once on the next scan (the marker is one timestamp, not a queue of missed windows)" | 코드 확인 |
  | `scanner.ts:278`, `marker-store.ts:85-94` | prune | 한 스캔에서 보이지 않은 키(Issue 삭제·`when` 제거·워크스페이스 제거)의 마커를 삭제 — 이후 다시 만들면 "마커 없음" 경우가 됨 | 코드 확인 |
  | `src/workspaces/service.ts:3300`, `scanner.ts:159-163`, `:240-245` | 첫 스캔 시점 | `scheduleScanner.start()` → `arm()`이 `setTimeout(..., this.intervalMs)`이므로 첫 스캔은 시작 약 60초 후(생성 즉시 스캔하지 않음) | 코드 확인 |

- 동작 설명 (`cron`, `catchUp` 미지정, 08:30 평일 슬롯이 꺼진 동안 지나감):
  | 경우 | 기준점(`fireBase`) | 재시작 후 첫 스캔 | 결과 |
  |---|---|---|---|
  | 마커 있음(과거에 한 번 이상 발사) | `lastFiredAtMs`(마커) | 다음 슬롯(마커 이후 첫 cron 시각) ≤ now → due | **1회 발사**, 마커=그 시점 → 밀린 슬롯 다수여도 1회 |
  | 마커 있음 + `catchUp: false` | 동일(마커) | 동일 | **1회 발사**(앱 중단엔 `catchUp` 무관). 발사 시도가 용량/busy로 거부될 때만 `held=now`로 슬롯 소비 |
  | 마커 없음(처음/prune/마커 파일 유실) | `now − 60000` | 그 60초 안에 슬롯이 없으면 `next > now` | **발사 안 됨**(과거 슬롯 무시), 다음 정규 슬롯 대기 |
  | 마커 없음 + 직전 시도가 거부됨(`held` 있음) | `held`(`dueAt − 1`) | 해당 슬롯 due | 다음 스캔에서 발사(`catchUp` 기본) |
  | `every`/`at` | 마커 없으면 epoch(0) → 즉시 due, 마커 있으면 마커 + 간격 | — | 처음 보면 즉시 1회, 중단 후엔 1회(밀린 횟수만큼 반복 안 함) |
  `02-schedule.md` 3.2절의 세 문장은 서로 다른 경우를 가리킨다: "`now−스캔간격`"은 마커 없는 경우, "놓친 창은 한 번만"은 마커 있는 경우, "busy/용량 catch-up"은 `held` 경로. 모순이 아니라 경우의 구분을 명시해야 한다.
- 조사 범위: `scanner.ts` 전체, `schedule/declaration.ts:80-101`, `core/schedule-expr.ts` 전체, `marker-store.ts` 전체, `service.ts:2360-2370·3300`, `scanner.spec.ts`의 catchUp/마커 케이스. `grep -rn "scheduleCatchesUp\|noteCronMiss\|fireBase"`로 호출처 전수 확인(`scheduleCatchesUp`은 `noteCronMiss` 한 곳에서만 쓰임).

#### R1-Q8 답변
- 결론: **확정**. Issue frontmatter에 `agent`가 없고 설정을 바꾸지 않았다면, 소유 세션(assignee)이 정확한 `@resumeId`이면 그 세션의 에이전트가, 아니면 `resolveHeadlessDefaultAgentId`가 아래 순서로 결정한다. `issueDefaultAgent` 스키마 기본값은 `null`이고, 새 설치 + 워크스페이스에 `.alice/settings.json`이 없는 상태에서는 **내장 어댑터 등록 순서의 첫 에이전트 런타임 = `claude`**(Claude Code)로 귀결된다(설치 여부는 확인하지 않음). 단, 워크스페이스 템플릿 `defaultAgents`(`chat`: `["claude","codex"]`)는 이 해석 체인에 직접 들어가지 않고, 생성 시 자격증명 vault가 있을 때만 `.alice/settings.json`의 headless `defaultAgent`로 씨앗이 된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/config.ts:237` | 스키마 | `issueDefaultAgent: z.string().nullable().default(null),` (주석 "User-level default runtime for issue-triggered headless work"). `workspaceDefaultAgent`도 `:231` `.default(null)` | 코드 확인 |
  | `src/core/config.ts:1046-1049` | 읽기 | `readIssueDefaultAgent`: `return config.issueDefaultAgent ?? null` | 코드 확인 |
  | `src/webui/routes/config.ts:424-435` | 쓰기 | `app.put('/issue-default-agent', ...)`가 등록된 런타임 id일 때만 `writeIssueDefaultAgent(agent)` | 코드 확인 |
  | `src/workspaces/service.ts:2380-2391` | 스캐너 어댑터 해석 | `resolveAdapter: async (ws, agentId, resumeId) => { if (resumeId) { const identity = resumeRegistry.get(resumeId); ... return resolveAdapter(ws, identity.agent); } if (agentId) return resolveAdapter(ws, agentId); return resolveAdapter(ws, await resolveHeadlessDefaultAgentId(ws)); }` | 코드 확인 |
  | `service.ts:1130-1136` | `resolveAdapter` | `if (agentId) { const a = adapters.get(agentId); if (a) return a; } return adapters.resolve(null);` — 모르는 id면 레지스트리 기본(claude)로 폴백 | 코드 확인 |
  | `service.ts:1166-1177` | `resolveHeadlessDefaultAgentId` | `validRegisteredRuntime(runtimeSettings.ok ? resolveWorkspaceRuntimeAgent(runtimeSettings.settings, 'headless') ?? null : null) ?? validRegisteredRuntime(await readIssueDefaultAgent().catch(() => null)) ?? await resolveDefaultAgentId(wsMeta)` | 코드 확인 |
  | `service.ts:1148-1164` | `resolveDefaultAgentId` | interactive 설정 → `readWorkspaceDefaultAgent()` → `firstRegisteredRuntime()` 순 | 코드 확인 |
  | `service.ts:1138-1145` | 후보 필터 | `adapters.list().find(isAgentRuntime)?.id`; `isAgentRuntime`은 `cli-adapter.ts:496-498` `adapter.kind !== 'utility' && adapter.id !== 'shell'` (설치 상태를 보지 않음) | 코드 확인 |
  | `src/workspaces/workspace-runtime-settings.ts:190-196`, `:239-264` | 워크스페이스 설정 | `return configured?.defaultAgent ?? configured?.recent.agent` (`.alice/settings.json`, `:12`). `recent`는 fresh 헤드리스 자식이 spawn된 뒤 `rememberWorkspaceRuntimeBinding`이 기록(`service.ts:1853-1863`, 단 `preferenceFromBinding`이 null이 아닌 경우) | 코드 확인 |
  | `src/workspaces/adapters/index.ts:21-31`, `:32` | 등록 순서·기본 | `BUILTIN_ADAPTERS = [claudeAdapter, codexAdapter, cursorAdapter, agyAdapter, grokAdapter, ompAdapter, opencodeAdapter, piAdapter, shellAdapter]`; `registry.register(adapter, { default: adapter === claudeAdapter })` | 코드 확인 |
  | `src/workspaces/workspace-creator.ts:255-299` | 템플릿 씨앗 | vault 자격증명이 있고 호환될 때만 `settings.runtime.headless.defaultAgent = template.defaultAgents.find(...) ?? rememberedAgents[0]`를 `.alice/settings.json`에 기록. 없으면 쓰지 않음 | 코드 확인 |
  | `src/workspaces/issues/declaration.ts:254-260` | 세션 소유 제약 | 정확한 `@resumeId` assignee가 있으면 `agent` override 금지("assigned Session has a fixed Agent runtime") | 코드 확인 |

- 동작 설명(결정 순서, `agent` 생략·헤드리스 스캐너 발사):
  1. assignee가 정확한 `@resumeId` → 그 세션의 `identity.agent`(Claude/Codex/…)를 그대로 사용(retired/deleted면 오류).
  2. 아니면 Issue `agent`(있을 때, 등록된 id가 아니면 레지스트리 기본=claude).
  3. 둘 다 없으면 `resolveHeadlessDefaultAgentId`: ① 워크스페이스 `.alice/settings.json`의 `runtime.headless.defaultAgent`, 없으면 `recent.agent` → ② 전역 `ai-provider-manager.json`의 `issueDefaultAgent`(기본 null) → ③ `resolveDefaultAgentId`: 워크스페이스 interactive 설정(`defaultAgent`/`recent.agent`) → 전역 `workspaceDefaultAgent`(기본 null) → 등록 순서 첫 에이전트 런타임(claude).
  4. 새 설치(자격증명 vault 없음, 첫 헤드리스 실행 전)에서는 ①②③의 앞부분이 모두 비어 `claude`가 된다. 첫 헤드리스 자식이 뜬 뒤에는 그 에이전트가 `recent`로 기록되어 이후 기본이 된다.
  보고서 `03-decision.md` 4-2절의 "기본 에이전트 = `issueDefaultAgent` 설정"은 순서의 일부일 뿐이고(우선순위 2위), 미설정 시 최종 기본은 claude이며 워크스페이스 설정이 `issueDefaultAgent`보다 우선한다는 점을 보완해야 한다.
- 조사 범위: `grep -rn "issueDefaultAgent\|resolveHeadlessDefaultAgentId\|readIssueDefaultAgent\|workspaceDefaultAgent"`, `service.ts:1100-1180·2367-2395`, `cli-adapter.ts:496-535`(`AdapterRegistry`), `adapters/index.ts`, `workspace-runtime-settings.ts`, `workspace-creator.ts:255-299`, `templates/chat/template.json`(`"defaultAgents": ["claude", "codex"]`), `conversation-control.ts:310`(다른 호출처 확인).

#### R1-Q9 답변
- 결론: **확정**. `allowAiTrading=true`이면 `tradingPush`가 사람 승인 없이 브로커 주문 전송까지 이어진다. 중간에 남는 게이트는 사람 승인이 아니라 (a) 거래 모드(`readonly`) 차단, (b) 계정 `readOnly`/disabled/offline, (c) `expectedPendingHash` 일치(AI 경로는 현재 해시를 **자동으로** 채움), (d) 계정별 가드(max-position-size·cooldown·symbol-whitelist, 설정된 경우만), (e) 워크스페이스 CLI 그룹 정책이다. 인증 토큰·사람 확인 단계는 이 경로에 없다. 주석 "the AI tool is hollowed out, only humans can push"(`routes-trading.ts:502`)는 이 설정이 켜지면 사실과 다르다. 추가 발견: `allowAiTrading` 게이트는 `tradingPush` **도구 층에만** 있고, UTA HTTP `/wallet/push`와 메인의 `/api/trading/*` 프록시는 이 값을 보지 않는다(Q10 참조).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/server/cli-commands.ts:212-262` | CLI 노출 | `git: { status: 'tradingStatus', log: 'tradingLog', show: 'tradingShow', commit: 'tradingCommit', push: 'tradingPush', reject: 'tradingReject', sync: 'tradingSync' }` → `alice-uta git push` | 코드 확인 |
  | `src/server/cli.ts:295-303` | CLI 게이트 | 매핑 확인 + 워크스페이스 정책 `cliGroupEnabled(policy, r.exp.binary, group)`가 false면 `403 CLI command disabled by Workspace configuration`. 기본(`.alice/alice-harness-config.json` 없음) = `DEFAULT_ALICE_HARNESS_CONFIG`(`{ schemaVersion: 1, cli: {} }`) → 전부 허용(`alice-harness-policy.ts:19`, `:37-40`) | 코드 확인 |
  | `src/workspaces/adapters/claude.ts:236`, `:274`; `codex.ts:34-39`, `:280-282` | 런타임 승인 없음 | `'--dangerously-skip-permissions'`; `'--sandbox', 'danger-full-access', '--ask-for-approval', 'never'`; 헤드리스 `approval_policy="never"`, `sandbox_mode="danger-full-access"` — 셸 명령(`alice-uta git push`)에 런타임 승인 프롬프트 없음 | 코드 확인 |
  | `src/main.ts:249-256` | 도구 생성 | `createTradingTools(utaManager, () => config.agent.allowAiTrading)` (라이브 getter) | 코드 확인 |
  | `src/core/config.ts:249` | 기본값 | `allowAiTrading: z.boolean().default(false)` | 코드 확인 |
  | `src/tool/trading.ts:808-820` | 선행 검사 | `const targets = await manager.resolve(source)`; `const pending = statuses.filter(({ status }) => status.pendingMessage)`; 없으면 오류/메시지 반환 | 코드 확인 |
  | `src/tool/trading.ts:821-832` | allowAiTrading 게이트 | `if (!allowAiTrading()) { return { message: 'Push requires manual approval (AI trading is disabled). Tell the user to review and approve ...', pending: ... } }` | 코드 확인 |
  | `src/tool/trading.ts:833-845` | 실행 | `Promise.all(pending.map(async ({ uta, status }) => { ... if (!status.pendingHash) { return { source: uta.id, error: 'Pending commit has no hash; ...' } } return { source: uta.id, ...compactPushResult(await uta.push(status.pendingHash)) }` — 해시는 `uta.status()`(`UTAAccountSDK.ts:256`, `GET /wallet/status`)가 돌려준 **현재 `pendingHash`를 그대로** 넣음 | 코드 확인 |
  | `src/services/uta-client/UTAAccountSDK.ts:287-293`, `:398-401` | 메인→UTA | `async push(expectedPendingHash) { this.assertVenueWritable(); return this.client.post(\`/api/trading/uta/${id}/wallet/push\`, { expectedPendingHash }) }`; `assertVenueWritable`는 `readonlyMutationReason()`이 있으면 throw (`services/trading-mode.ts:70-73`: `mode === 'readonly'` → 'Trading mode is readonly; venue-mutating broker writes are disabled.', `main.ts:160`) | 코드 확인 |
  | `services/uta/src/http/routes-trading.ts:503-519` | UTA 라우트 | `app.post('/uta/:id/wallet/push', ...)`: `if (!uta.status().pendingMessage) return ... 'Nothing to push'`; `readExpectedPendingHash(body)` 없으면 409 `PENDING_HASH_REQUIRED`; `const result = await uta.push(expectedPendingHash)`. 인증 미들웨어 없음(`services/uta/src/main.ts`에 `app.use` 없음, `hostname: '127.0.0.1'`, `:183-187`), `trading-proxy.ts` 헤더 "v1 has no auth between the two — UTA is bound to 127.0.0.1 only" | 코드 확인 |
  | `services/uta/src/domain/trading/UnifiedTradingAccount.ts:793-804` | `push` | `this._assertCanMutateAccount('push')`(readOnly·keyless면 `BrokerError('CONFIG', ... is read-only ...)`, `:558-563`); disabled/offline이면 throw; `const result = await this.git.push(expectedPendingHash)`; `_onPostPush`(스냅샷) | 코드 확인 |
  | `services/uta/src/domain/trading/git/TradingGit.ts:119-127`, `:241-249` | 해시 확인 | `assertPrepared('push')`, `beginWrite`: `if (!expectedPendingHash \|\| expectedPendingHash !== this.pendingHash) { throw new PendingHashConflictError('Pending commit changed') }` — 인자가 현재 해시와 같으면 통과 | 코드 확인 |
  | `TradingGit.ts:129-155`; `UnifiedTradingAccount.ts:179-199` | 연산 실행 | `for (const op of operations) { const raw = await this.config.executeOperation(op) ...}` → `dispatcher`가 `_assertCanMutateAccount(op.action)` 후 `broker.placeOrder(op.contract, op.order, op.tpsl)`/`modifyOrder`/`closePosition`/`cancelOrder`; 앞에 `createGuardPipeline(dispatcher, broker, resolveGuards(options.guards ?? []))` — 가드가 거부하면 `{success:false, error:'[guard:<name>] ...'}` | 코드 확인 |
  | `services/uta/src/domain/trading/guards/registry.ts:6-10` | 가드 종류 | `max-position-size`, `cooldown`, `symbol-whitelist` (계정 설정에 기재해야 적용, `core/config.ts` `guards` 기본 `[]`) | 코드 확인 |

- 동작 설명(호출 순서): `alice-uta git push [--source X]`(셸) → `/cli/:wsId/uta/invoke`(그룹 정책 통과) → `tradingPush.execute` → `manager.resolve(source)` → 각 계정 `status()`(HTTP `GET .../wallet/status`) → 커밋(`pendingMessage`) 없으면 종료 → `allowAiTrading()` false면 "수동 승인 필요" 메시지로 종료, true면 → 각 계정에 대해 `status.pendingHash`를 그대로 `uta.push(hash)` → `assertVenueWritable`(readonly 모드면 throw) → `POST /api/trading/uta/:id/wallet/push {expectedPendingHash}` → UTA 서비스 라우트 → `UnifiedTradingAccount.push`(readOnly/disabled/offline 확인) → `TradingGit.push`(해시 일치 확인, 자기가 방금 읽은 해시이므로 통과) → 연산마다 가드 파이프라인 → `broker.placeOrder` 등 → 실제 브로커 주문. 사람 승인·토큰은 어디에도 없다. 계정별 실패는 `handleBrokerError`로 개별 결과에 담긴다.
- 조사 범위: `tool/trading.ts` 전체(push 관련 호출 `\.push(`는 `uta.push` 한 곳), `services/uta-client/UTAAccountSDK.ts`·`UTAManagerSDK.ts`, `services/uta/src/http/routes-trading.ts`(wallet/push·commit·stage), `UnifiedTradingAccount.ts`, `TradingGit.ts`, `guards/*`, `trading-mode.ts`, `trading-proxy.ts`, `alice-harness-policy.ts`, 어댑터 승인 플래그.

#### R1-Q10 답변
- 결론: **확정**. 에이전트가 `allowAiTrading`을 `true`로 만들 수 있는 코드 경로가 **있다**(두 가지). (1) 설정 쓰기 HTTP 라우트 `PUT /api/config/agent`(웹 포트): 서버 쪽에 위험 경고·이중 확인 검증이 없고(그 확인은 UI 컴포넌트에만 있음), 인증은 loopback·무Origin 요청이면 통과한다(신뢰 프록시 미설정 시). (2) 설정 파일 `<OPENALICE_HOME>/data/config/agent.json`(기본 `~/.openalice/data/config/agent.json`)을 에이전트가 직접 쓰는 경로: 에이전트는 샌드박스 없이 같은 OS 사용자로 실행되고, 파일 변경은 재시작 또는 다음 설정 PUT/로드 때 반영된다. ToolCenter/CLI 도구 중에는 이 값을 쓰는 것이 **없다**. 따라서 "기본은 사람 승인" 결론은 "에이전트가 의도적으로 우회하지 않는 한"이라는 단서가 붙어야 한다(보고서 `03-decision.md` 4-1절 `추론` 항목 보강 필요).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/config.ts:12`, `:555`, `:1096-1106`, `:1062-1094` | 저장 위치 | `const CONFIG_DIR = dataPath('config')`; `agent: await parseAndSeed(files[1], agentSchema, raws[1])`(`'agent.json'`); `writeConfigSection(section, data)`: `schema.parse(data)` 후 `writeFile(resolve(CONFIG_DIR, sectionFiles[section]), ...)`. `core/paths.ts:43-45` `dataPath()` = `<USER_DATA_HOME>/data/...`, 기본 `~/.openalice` | 코드 확인 |
  | `src/core/config.ts:244-249` | 필드 | `allowAiTrading: z.boolean().default(false)` — "Gated in the UI behind a danger warning + double-confirm." | 코드 확인 |
  | `src/webui/routes/config.ts:440-456` | 쓰기 라우트 | `app.put('/:section', async (c) => { ... const body = await c.req.json(); const validated = await writeConfigSection(section, body); if (opts?.ctx) { const fresh = await loadConfig(); Object.assign(opts.ctx.config, fresh) }` — 섹션·값에 대한 추가 확인 없음 | 코드 확인 |
  | `src/main.ts:398-410`, `:249-256` | 실시간 반영 | `ctx: EngineContext = { config, ... }` 즉 라우트가 갱신하는 `ctx.config`와 도구 getter가 읽는 `config`가 **같은 객체**; `() => config.agent.allowAiTrading` | 코드 확인 |
  | `src/webui/plugin.ts:225-235`, `:250` | 인증 | `app.use('*', createAuthMiddleware({ trustedProxies, csrfTrustedOrigins, disabled: authDisabled }))`; `app.route('/api/config', createConfigRoutes({ ctx }))` | 코드 확인 |
  | `src/webui/middleware/auth.ts:79-85` | loopback 통과 | `if (trustedProxies.size === 0) { const clientIp = getSocketRemoteAddress(c); const origin = c.req.header('origin'); if (clientIp && isLoopbackIp(clientIp) && (!origin \|\| isTrustedLocalOrigin(origin))) { return next() } }` — `curl`은 Origin이 없어 통과 | 코드 확인 |
  | `ui/src/pages/AgentPermissionsPage.tsx:197-209`, `:235-246` | 이중 확인 | `api.config.updateSection('agent', { ...config.agent, allowAiTrading: v })` 는 `onToggle(true)` → `ConfirmDialog`(variant danger)에서만 호출 — 서버가 아닌 UI 로직 | 코드 확인 |
  | `src/workspaces/config.ts:78-82`, `workspaces/service.ts:1087` | 워크스페이스 위치 | `resolveLauncherRoot` = `join(OPENALICE_HOME ?? userDataHome, 'workspaces')`, `workspacesRoot: \`${config.launcherRoot}/workspaces\`` — 설정 파일(`.../data/config`)은 같은 `~/.openalice` 아래의 형제 디렉터리 | 코드 확인 |
  | `claude.ts:80`, `:236`; `codex.ts:34-39`, `:280-282`; `codex-app-server-transport.ts:66-67` | 샌드박스·승인 없음 | `{"enableAllProjectMcpServers":true,"sandbox":{"enabled":false}}`, `--dangerously-skip-permissions`; `--sandbox danger-full-access --ask-for-approval never`; app-server `approvalPolicy: 'never', sandbox: 'danger-full-access'` | 코드 확인 |
  | `src/core/config.ts:540-585` | 로드 시점 | `loadConfig()`는 시작 시(`main.ts:98`)와 `/api/config` 라우트(GET `:101`, PUT 후 `:453`)에서만 호출. 파일 감시(watch) 코드 없음 | 코드 확인 |

- 동작 설명:
  | 경로 | 조건 | 효과 |
  |---|---|---|
  | `PUT http://127.0.0.1:<웹 포트>/api/config/agent` (본문 `{"maxSteps":20,"allowAiTrading":true,"claudeCode":{...}}`) | `OPENALICE_TRUSTED_PROXIES` 미설정 + `OPENALICE_DISABLE_AUTH` 무관, 요청에 Origin 없음(curl 기본). 웹 포트 기본 47331(`config.ts:366`), `ports.json`·환경변수로 다를 수 있음 | 파일 기록 + `Object.assign(ctx.config, loadConfig())`로 **즉시** `tradingPush` 게이트 해제 |
  | 같은 요청, 신뢰 프록시가 설정된 배포(`OPENALICE_TRUSTED_PROXIES` 있음) | loopback 통과가 꺼져 세션 쿠키 필요(`auth.ts:75-95`) | 쿠키 없으면 401 — 이 경로는 막힘 |
  | `~/.openalice/data/config/agent.json` 직접 수정 | 에이전트의 파일 쓰기 권한(위 샌드박스 없음) | 재시작 또는 이후 어떤 `PUT /api/config/*`(사람의 설정 저장 포함)·`loadConfig` 때 반영 |
  | ToolCenter·CLI 도구 | `src/tool/*.ts`에서 `core/config`를 쓰는 것은 `domain/market-data/vendors.ts`의 `updateExtraVendors`(market-data.json의 `extraVendors`만) — `allowAiTrading`·`agent.json`을 쓰는 도구 없음. `alice-uta`·`alice` CLI에 설정 변경 verb 없음 | 불가 |
  또한 Q9에서 보았듯 `POST /api/trading/uta/:id/wallet/push`(웹 포트 프록시 `trading-proxy.ts:115-130`, 읽기 전용 모드에서만 차단) 또는 UTA 서비스(기본 `127.0.0.1:47333`, `url.ts:13`, 인증 없음)를 직접 호출하면 `allowAiTrading`을 건드리지 않고도 push가 가능하다(`expectedPendingHash`는 `/wallet/status`에서 읽음). 즉 안전 경계는 "에이전트가 안내된 CLI만 쓴다"는 가정에 기대고 있다.
- 정적 확인 불가(분리): 위 HTTP 경로의 성립은 배포 환경변수(`OPENALICE_TRUSTED_PROXIES`, `OPENALICE_DISABLE_AUTH`, 웹 포트)에 달려 있고 에이전트가 실제로 그 포트를 아는지·시도하는지는 실행 결과다. 코드상 경로 존재 자체는 위 표대로 확정이다.
- 조사 범위: `grep -rn "allowAiTrading\|agent.json"`(`src`, `apps`, `packages`, `services`, `ui/src`), `writeConfigSection` 호출처 전수(`webui/routes/config.ts:447`, `webui/routes/tools.ts:26`만), `core/config.ts` 로드·쓰기 함수, `webui/plugin.ts` 라우트 마운트(`:230-274`), `webui/routes/trading-proxy.ts`, `auth.ts` 전체, `src/tool/*.ts`의 `core/config` import(0건), `alice-harness-policy.ts`.

#### R1-Q11 답변
- 결론: **없음 확정**. 질문이 지정한 `src`·`services`·`default/skills`(그리고 `packages/`, `ui/src`)에는 과거 판단(TradingGit 커밋, thesis 노트, Inbox 리포트, 정기 루틴)을 이후 가격·손익과 자동 대조해 평가·기록하는 코드가 없다. 가까워 보이는 장치는 모두 아래 표의 다른 용도다. 단 템플릿 `auto-quant-v2`·`auto-prediction`은 이 레포가 아니라 외부 저장소(`Auto-Quant-V2`, `Auto-Prediction`, 고정 커밋)를 clone하므로 그 내부 평가 기능은 이 레포의 코드로는 **정적 확인 불가**이며 질문 범위 밖이다.
- 근거(가까운 장치와 판단 평가용이 아닌 이유):

  | 위치 | 식별자 | 내용 (원문 인용 요약) | 판단 평가용? |
  |---|---|---|---|
  | `src/domain/analysis/simulate.ts:1-25`, `src/tool/simulate.ts:18` | `simulate` | "the 'if I'd entered here, with this exit, what happened' backtest" — 에이전트가 **그때그때 호출**해 진입일+청산 규칙 1개를 시뮬레이션. 과거 커밋/노트를 읽지 않고 기록도 남기지 않음 | 아니오(수동·무상태, MCP/HTTP 외엔 에이전트에 안 닿음: Q1) |
  | `default/skills/retrospective/SKILL.md` | 스킬 | "Subjective retrospective / time-machine analysis ..." — 에이전트가 `alice analysis snapshot --asOf`와 `windowRss`로 **수동 복기**하는 절차 문서. 점수 계산·저장 코드 없음 | 아니오(절차 문서) |
  | `src/tool/snapshot.ts:21`, `src/domain/analysis/snapshot.ts` | `marketSnapshot` | as-of 시점 시세 요약(룩어헤드 방지) | 아니오(조회 도구) |
  | `services/uta/src/domain/trading/snapshot/types.ts:1-60`, `scheduler.ts`, `service.ts`; `core/config.ts:373-381` | UTA 스냅샷 | 계정 상태(`netLiquidation`, `unrealizedPnL`, `realizedPnL`, 포지션, 미체결 주문)를 `trigger: 'scheduled' \| 'post-push' \| 'post-reject' \| 'manual'`로 저장, 기본 `every: '15m'`. 소비처는 `routes-trading.ts:641-700`의 `/uta/:id/snapshots`, `/snapshots/equity-curve`(UI 자산 곡선)뿐. 커밋·판단과 연결(귀속)하는 코드와 `alice-uta`/메인 ToolCenter 도구 없음 | 아니오(계정 NAV 시계열, 판단 단위 평가 아님) |
  | `src/tool/trading.ts:610-639`, `:873-899` | `tradingLog/Show`, `orderHistory/tradeHistory` | 커밋 이력·주문 수명주기·체결 조회 (`description: 'View your trading decision history'`) — 사후 수익률 계산 없음 | 아니오(원장 조회) |
  | `services/uta/src/domain/trading/position-math.ts`, `UnifiedTradingAccount.ts`(`realizedPnL`/`unrealizedPnL`) | 포지션 손익 | 현재 포지션의 평가손익 필드 | 아니오(포지션 현황) |
  | `src/core/routine-follow-up-store.ts:30-60`, `src/webui/routes/office.ts:162-230` | 루틴 팔로업 | `outcome: 'maintain-plan' \| 'revise-plan' \| 'evidence-unavailable'` + 280자 이하 메모를 **사람이 UI에서** 기록하는 "결정 영수증". 가격·수익률 비교 없음 | 아니오(결정 로그) |
  | `src/domain/analysis/sector-rotation.ts` (`rotation_score`, z-score) | 섹터 점수 | ETF 섹터 로테이션 점수 | 아니오(시장 분석) |

- 조사 범위: 대상 `src`, `services`, `default`, `packages`(`opentypebb` 포함), `ui/src`(i18n·demo 제외), 확장자 `ts/tsx/md/json/mjs`. 패턴(대소문자 무시): `hit.?rate`, `outcome`, `post.?mortem`, `scorecard`, `backtest`, `retro`, `accuracy`, `benchmark`, `evaluat`, `track.?record`, `win.?rate`, `realized`, `unrealized`, `pnl`, `scor(e|ing)`, `grade`, `calibrat`, `brier`, `sharpe`, `drawdown`, `forward.?return`, `since (commit|decision)`, `review(ed)?At|reviewDue|follow.?up`. 결과: `hit.?rate`·`post.?mortem`·`scorecard`·`accuracy`·`track.?record`·`win.?rate`·`calibrat`·`brier`·`sharpe`·`drawdown`·`forward.?return` 0건; 나머지는 위 표의 파일 또는 무관한 사용(`matchScore`/`fuzzy-rank` 검색 점수, 템플릿 `upgrade` 등). 질문이 요청한 UTA 스냅샷 스케줄: 저장 내용 = 위 표, 소비처 = UI 곡선 라우트뿐(`grep -rniE "snapshots|equity-curve"` 결과 `src/`의 도구·CLI에 0건). `default/skills/` 14개 스킬(`alice`, `alice-analysis`, `alice-uta`, `build-thesis`, `delegate-autoquant`, `file-delivery`, `market-data`, `opencli-reader`, `retrospective`, `scan-value-chain`, `sector-rotation`, `self-scheduling`, `traderhub`, `workspace-manager`)과 `templates/chat/files/instruction.md`에서 "과거 판단을 이후 결과로 채점"하라는 절차를 요구하는 문장 없음(`retrospective`는 사용자가 요청한 복기 한정).

#### R1-Q12 답변
- 결론: **없음 확정**. claude·codex 어댑터는 대화형·헤드리스·Web 어느 실행에서도 웹 검색·웹 읽기 도구를 켜거나 막는 인자·설정을 넘기지 않는다(`--allowedTools`/`--disallowedTools`/`--tools`/`--search`/`web_search` 설정 모두 없음). 코드가 하는 것은 Codex의 `web_search` 이벤트를 **표시용으로 파싱**하는 것뿐이다. 런타임 기본 동작(인자가 없을 때 실제로 검색이 되는지)은 **정적 확인 불가**로 분리한다. 부수 발견: `core/config.ts:250-269`의 `agent.claudeCode.allowedTools/disallowedTools`(기본에 `mcp__claude_ai_Figma__*` 등)는 스키마에만 있고 어디서도 읽히지 않는 **죽은 설정**이다(Claude 인자에 전달되지 않음).
- 근거(실행 명령 합성, 전체 인자):

  | 위치 | 모드 | 합성 결과 (원문) | 웹 관련 항목 |
  |---|---|---|---|
  | `src/workspaces/adapters/claude.ts:235-236`(+`:215-229`) | 대화형 | `[...base, '--settings', AUTOTRUST_SETTINGS, '--dangerously-skip-permissions', ...interactiveArgs]` (+ 신규 시 `'--', initialPrompt`, 재개 시 `'--resume', sessionId`). `base`=`['claude']`(`workspaces/config.ts:145-163`, `WEB_TERMINAL_COMMAND`로 변경 가능). `interactiveArgs`=`[--setting-sources=project(vault일 때), --model, --effort]` | 없음 |
  | `claude.ts:264-280` | 헤드리스 | `[...base, '--settings', AUTOTRUST_SETTINGS, '--dangerously-skip-permissions', ...headlessArgs, (--resume id), '-p', '--output-format', 'stream-json', '--verbose', '--', prompt]` | 없음 |
  | `claude.ts:290-304` | Web | `[...base, '--settings', AUTOTRUST_SETTINGS, '--dangerously-skip-permissions', ...webArgs, (--append-system-prompt), (--resume id \| --session-id uuid), '-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--include-partial-messages', '--permission-prompt-tool', 'stdio']` | 없음 |
  | `claude.ts:80` | 설정 JSON | `const AUTOTRUST_SETTINGS = '{"enableAllProjectMcpServers":true,"sandbox":{"enabled":false}}'` — 도구 허용/차단 키 없음 | 없음 |
  | `claude.ts:398-440` | 워크스페이스 파일 | `writeAiConfig`는 `.claude/settings.local.json`의 `env.ANTHROPIC_BASE_URL/API_KEY/AUTH_TOKEN`, `model`만 소유(주석 "permissions and every unknown project setting remain untouched") | 없음 |
  | `src/workspaces/adapters/codex.ts:33-39`, `:239-251`, `:685` | 대화형 | `['codex', ...selection, '--sandbox', 'danger-full-access', '--ask-for-approval', 'never', '-c', 'allow_login_shell=false', '-c', 'projects={ "<cwd>" = { trust_level = "trusted" } }', ...MCP 플래그(있을 때)]` + `interactiveArgs`(`--model`, `-c model_reasoning_effort=..`, 커스텀 provider `-c model_provider...`) | 없음 |
  | `codex.ts:263-297` | 헤드리스 | `['codex', ...headlessArgs, (--model), (-c model_reasoning_effort=..), (-c model_provider=..), '-c', 'approval_policy="never"', '-c', 'sandbox_mode="danger-full-access"', '-c', 'allow_login_shell=false', '-c', 'projects={...}', 'exec', ('resume', ...), '--json', '--', prompt]` | 없음 |
  | `codex.ts:301-312`, `src/workspaces/web-session/codex-app-server-transport.ts:62-72` | Web | `['codex', ...webArgs, ...MCP 플래그, '-c','allow_login_shell=false', '-c','projects=...', 'app-server', '--listen', 'stdio://']`; 스레드 시작 옵션 `{ cwd, approvalPolicy: 'never', sandbox: 'danger-full-access', (model) }` | 없음 |
  | `codex.ts:441-480` | 네이티브 설정 | `.codex/config.toml`에는 `model`, `model_reasoning_effort` 최상위 키만 소유(`:470`, `:472`) | 없음 |
  | `codex.ts:413-416`, `codex-app-server-transport.ts:201-202`, `:261` | 표시용 파싱 | `if (record['type'] === 'web_search') { ... return [{ type: 'tool-start', id, name: 'Web search', input }] }`; `case 'webSearch': this.builder.toolCall(id, 'web_search', { query: raw['query'] })` | 이벤트 표시만(켜기/끄기 아님) |
  | `src/core/config.ts:250-269` | 죽은 설정 | `claudeCode: z.object({ allowedTools: ..., disallowedTools: ...default([ 'Task', ..., 'mcp__claude_ai_Figma__*' ]), maxTurns: ...})` — `src` 전체에서 이 필드를 읽는 코드 없음(`ui/src/api/types.ts:215`의 타입 선언뿐) | 사용 안 됨 |
  | `src/workspaces/templates/chat/files/instruction.md`, `default/skills/opencli-reader/SKILL.md:6-8` | 문서 | 웹 검색 사용·금지에 대한 지시 없음. opencli-reader는 "one source-access option alongside the Coding Agent's browser, search and other available tools"라고만 언급 | 없음 |

- 동작 설명: 세 모드 모두 모델·effort·자격증명·승인/샌드박스(전면 허용)·신뢰·MCP(Codex만, 조건부)·재개 인자만 만들고 웹/검색 도구 인자는 한 번도 추가하지 않는다. 따라서 웹 검색의 가용성은 전적으로 (a) 에이전트 CLI의 내장 기본값, (b) 사용자의 전역 CLI 설정(`~/.claude`, `~/.codex/config.toml`; 네이티브 로그인 모드에서는 OpenAlice가 `CODEX_HOME`을 바꾸지 않음, `codex.ts:150-170`)에 달려 있다. 보고서 `04-research.md` 5-1절 "이 레포가 켜고 끄지 않는다"는 정적으로 확인된 사실이다. `00-overview.md` 핵심 발견 5의 전제도 유지된다(단 "런타임이 실제로 검색한다"는 부분은 코드가 보장하지 않음).
- 정적 확인 불가(분리):
  - 갈리는 곳: Claude Code/Codex 바이너리의 내부 기본값과 사용자 전역 설정(레포 밖).
  - 경우의 수: (a) 기본값이 웹 도구를 허용 → 헤드리스(`--dangerously-skip-permissions`/`never`)에서 승인 없이 사용 가능, (b) 해당 버전/계정/설정에서 비활성 → 사용 불가. 이 레포의 코드는 어느 쪽도 강제하지 않는다.
- 조사 범위: `grep -rniE "allowedTools|disallowedTools|allowed-tools|--search|web_search|websearch|webfetch|web-search|tools\.web"`를 `src`, `apps`, `packages/cli`, `default`(ts/mjs/cjs/md/json)에서 실행(위 표의 파일 외 0건). `claude.ts`·`codex.ts` 전체 열람과 `service.ts:1300-1320`(`adapter.composeCommand(config.command, ...)` 호출), `workspaces/config.ts`(`parseCommand` 기본 `['claude']`), 나머지 어댑터(`cursor/agy/grok/omp/opencode/pi`)의 웹 도구 인자 없음 grep.

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 해소 | `config.ts:355-358`(MCP `enabled` 기본 false), `main.ts:337-346`(활성 조건), `codex.ts:702-720`(전역 `/mcp` 등록), `service.ts:1256`(env 주입), `claude.ts:80`, `webui/routes/tools.ts:56-76`(이름으로 임의 도구 실행)을 직접 열어 확인함. 완료 조건(MCP 설정을 넘기는 위치·활성 조건, 그리고 grep 범위)을 모두 채움. 결론이 "기본 설정에서는 도구 인터페이스로 닿지 않음 / MCP를 켜면 Codex 대화형·Web만 닿음 / loopback HTTP 직접 호출 경로는 있음"으로 경우별로 확정됨 |
| R1-Q2 | 없음 확정 | `UTAManagerSDK.ts:60-61`(no-op), `uta-manager.ts:107`(UTA 쪽 ToolCenter에만 등록), `services/uta/src/main.ts:169-174`(라우트 컨텍스트에 toolCenter 없음)를 확인함. `cli-commands.ts`와 `src/` 전체를 직접 grep해 `getFundingRate`·`funding`이 0건임을 재확인함. CLI·MCP·`/api/tools`가 모두 메인 ToolCenter만 본다는 경로 추적까지 있어 조사 범위가 충분함 |
| R1-Q3 | 해소 | `aggregate-search.ts:132-146`(접미사 필터·변환 없음), `standard-models/equity-historical.ts:9`(대문자화만), `yfinance/index.ts:55-56`(KR 문구)를 확인함. 정적 부분(검색→`yfinance\|005930.KS`→`yf.chart`, `.KS`/`.KQ` 분기 없음)이 끝까지 확정됐고, 남은 부분(Yahoo가 무엇을 돌려주는지)은 외부 API 응답이라 분리 기재가 타당함 |
| R1-Q4 | 해소 | `equity.ts:104-107`(`provider: 'fmp'` 고정), `credential-map.ts:56-60`(hub 센티널은 fed/eia/bls만), `query-executor.ts:51-78`·`:97-102`(fetch 전에 `Missing credential` throw)를 확인함. 완료 조건의 호출 순서·센티널 여부를 모두 충족하고, 스킬 문서와의 모순이 확정됨 |
| R1-Q5 | 해소 | `main.ts:165-169`(시작 시 `init()`), `store.ts:21-23`(2000·7일 상수), `store.ts:95-112`(7일 이내만 버퍼 적재 후 정렬)를 확인함. 복구 기준·호출처·상수 위치를 모두 제시함. `readRss`가 디스크를 본다는 추가 사실은 보고서 정정 대상 |
| R1-Q6 | 해소 | `scanner.ts:380-385`(디스패치 반환 직후 `markers.set`), `service.ts:2124-2130`(await 없이 `runHeadlessTaskMethod` 시작), `service.ts:2311-2316`(완료를 기다리지 않고 반환)을 확인함. 실행 실패 시 마커를 지우는 코드가 없다는 점도 마커 API와 grep 범위로 뒷받침됨. `03-decision.md` 4-6절이 틀렸음이 확정됨 |
| R1-Q7 | 해소 | `declaration.ts:88-101`(`fireBase`: 마커 있으면 마커, 없으면 `now−lookback`), `schedule-expr.ts:41-43`(`catchUp`은 `noteCronMiss`에서만 쓰임)을 확인함. 마커 있음/없음/`catchUp:false`/held 네 경우가 코드와 테스트 근거로 구분됨 |
| R1-Q8 | 해소 | `config.ts:237`(`issueDefaultAgent` 기본 null), `service.ts:1166-1177`(워크스페이스 headless 설정 → `issueDefaultAgent` → `resolveDefaultAgentId` 순서), `adapters/index.ts:21-32`(claude가 레지스트리 기본)를 확인함. 스키마 기본값과 해석 순서 원문을 모두 갖춤 |
| R1-Q9 | 해소 | `trading.ts:805-846`을 직접 열어 확인함. `allowAiTrading()`이 false일 때만 수동 승인 메시지로 끝나고, true면 `uta.status()`의 `pendingHash`를 그대로 `uta.push()`에 넘김(해시 게이트는 사실상 자동 통과). `routes-trading.ts:502-517`(주석 "only humans can push", 인증 없음)과 `services/uta/src/main.ts:183-187`(`hostname: '127.0.0.1'`)에서 `app.use` 인증 미들웨어가 없음을 grep으로 확인함. 남는 게이트(readonly 모드, 계정 readOnly/disabled, 가드, CLI 그룹 정책)의 목록과 위치가 완료 조건을 충족함 |
| R1-Q10 | 해소 | 보안 주장을 직접 추적함. `webui/plugin.ts:225-276`: `/api/config`, `/api/trading`(UTA 프록시), `/api/tools`가 모두 같은 `createAuthMiddleware` 뒤에 붙음. `auth.ts:79-85`: `trustedProxies`가 비어 있고 loopback이며 Origin이 없으면 세션 없이 통과함. `routes/config.ts:440-454`: `PUT /:section`은 섹션 이름만 검사하고 `writeConfigSection` 후 `Object.assign(ctx.config, fresh)`를 함. `main.ts:249-256`·`:398-410`: 도구 getter와 `ctx`가 같은 `config` 객체라 즉시 반영됨. `trading-proxy.ts` 헤더 주석("v1 has no auth between the two")과 `app.all('*')`이 lite·readonly만 막는다는 점도 확인함 → `/wallet/push` 직접 호출로 `allowAiTrading` 게이트를 우회하는 경로가 코드상 존재함. 보충 확인: `loadConfig()` 호출처를 grep한 결과(`main.ts:98`, `config.ts:101`, `:453`, `trading-config.ts:96`), ctx에 반영(`Object.assign`)하는 곳은 `config.ts:454` 한 곳뿐임. 따라서 `agent.json`을 직접 고친 경우에는 재시작하거나 아무 섹션이든 `PUT /api/config/*`가 일어나야 반영된다(GET만으로는 반영되지 않음). 답변의 "·loadConfig 때"는 이렇게 좁혀 읽어야 함. 환경변수(`OPENALICE_TRUSTED_PROXIES` 등)에 따라 갈리는 부분은 런타임 설정이므로 분리 기재가 타당함 |
| R1-Q11 | 없음 확정 | 확장 패턴을 `src services default packages ui/src`에 직접 다시 grep함. 답변은 `track.?record`가 0건이라고 했지만 실제로는 `packages/opentypebb/.../estimates-router.ts:43`("get their forecast track record")에 1건이 있음. 이것은 외부 애널리스트 추정치를 조회하는 엔드포인트 설명이라 자기 판단 채점과 무관하므로 결론에는 영향이 없음. UTA 스냅샷의 저장 내용과 소비처(UI 곡선 라우트뿐)도 제시돼 조사 범위가 충분함. 외부 템플릿 저장소의 내부 평가는 이 레포 범위 밖임 |
| R1-Q12 | 없음 확정 | `claude.ts:264-280`(헤드리스 전체 인자), `claude.ts:80`(설정 JSON)을 확인함. `allowedTools|disallowedTools|claudeCode`를 `src ui/src`에 grep한 결과가 `config.ts:250-261` 정의와 UI 타입·데모뿐이라, 이 설정이 실행 인자로 쓰이지 않는 죽은 설정임도 확인함. 런타임 기본값은 레포 밖 바이너리와 사용자 설정에 달려 있어 분리 기재가 타당함 |

새 질문 없음: Q9와 Q10에서 드러난 우회 경로(`PUT /api/config/agent`, `/api/trading/.../wallet/push`, UTA 직접 호출)는 인증 미들웨어, 라우트, 실시간 반영 코드까지 정적으로 끝까지 추적됨. 에이전트가 실제로 그 포트를 쓰는지는 실행 결과라 질문 대상이 아님(QA_GUIDE 4.2).

---

## 최종 정리 (질문자)

- 총 라운드: 1 / 총 질문: 12 / 해소 9 · 없음 확정 3 · 정적 확인 불가 0 (Q3·Q10·Q12의 외부 의존 부분은 각 답변 안에 분리 기재)
- 핵심 확정 사실:
  1. **AI 매매 게이트는 도구 층에만 있다.** `tradingPush`는 `allowAiTrading`(기본 false, `config.ts:249`)이 true일 때만 push하며, 그때 현재 `pendingHash`를 자동으로 넣어 사람 승인 없이 브로커까지 간다(`tool/trading.ts:821-845`). UTA의 `/wallet/push`(`routes-trading.ts:502-517`)와 메인의 `/api/trading/*` 프록시는 이 값을 보지 않는다.
  2. **에이전트가 게이트를 스스로 풀 수 있는 코드 경로가 있다.** 신뢰 프록시를 설정하지 않은 기본 배포에서는 loopback·무Origin 요청이 인증 없이 통과한다(`auth.ts:79-85`). 따라서 `PUT /api/config/agent`(`routes/config.ts:440-454`)로 `allowAiTrading`을 켜면 즉시 반영된다. "위험 경고+이중 확인"은 UI(`AgentPermissionsPage.tsx`)에만 있다. 에이전트는 샌드박스와 승인 없이 실행된다(`claude.ts:80`, `:236`, `codex.ts:34-39`).
  3. `simulate`/`calculate`는 기본 설정(MCP 꺼짐)에서 에이전트 도구 인터페이스로는 닿지 않는다. MCP를 켜면 Codex 대화형·Web만 닿는다(`codex.ts:702-720`). 다만 loopback `/api/tools/:name/execute`로는 어떤 도구든 실행할 수 있다(`webui/routes/tools.ts:56-76`).
  4. CCXT `getFundingRate`는 UTA 프로세스 내부 ToolCenter에만 있고, 에이전트에게 닿는 경로가 없다(`UTAManagerSDK.ts:60-61`, `services/uta/src/main.ts:169-174`).
  5. FMP 키가 없으면 `traderhub equity ratios`는 요청 전에 `Missing credential 'fmp_api_key'`로 실패한다(`query-executor.ts:51-78`). 스킬 문서의 "no API keys needed"와 모순된다.
  6. 뉴스 인덱스는 재시작 시 디스크에서 "7일 이내, 최신 2000건"으로 복구된다(`store.ts:74-121`, `main.ts:169`). `readRss`(id 조회)는 디스크 전체를 본다.
  7. 발사 마커는 실행 결과가 아니라 디스패치를 수락한 직후에 기록된다(`scanner.ts:385`, `service.ts:2124-2316`). 실행이 실패해도 자동 재발사는 없다.
  8. cron 기준점은 마커가 있으면 마커, 없으면 `now−60초`다(`declaration.ts:88-101`). 꺼져 있던 동안 놓친 슬롯은 마커가 있을 때만 재시작 후 한 번 발사된다. `catchUp`은 앱 중단과 무관하다.
  9. 헤드리스 기본 런타임의 결정 순서는 워크스페이스 headless 설정 → `issueDefaultAgent`(기본 null) → interactive 설정·`workspaceDefaultAgent` → 등록 순서 첫 런타임 `claude`다(`service.ts:1166-1177`, `adapters/index.ts:32`).
  10. 어댑터는 웹 검색을 켜거나 끄지 않는다. `agent.claudeCode.allowedTools/disallowedTools`는 읽는 곳이 없는 죽은 설정이다(`config.ts:250-269`).

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `01-data.md` 1.1절 표 마지막 행과 아래 문단, `next.md` 미확인 "MCP 경로" | MCP로만 닿는다(추론), `/mcp/:wsId` 사용 여부는 미확인 | MCP는 기본 꺼짐. 켜면 Codex 대화형·Web만 전역 `/mcp`로 두 도구에 닿음. Claude와 모든 헤드리스는 MCP 배선이 없고 `.mcp.json`도 주입되지 않음. `/mcp/:wsId`는 워크스페이스 도구 전용. 별도로 loopback `/api/tools/:name/execute` 경로가 있음. 미확인 항목은 삭제 | R1-Q1 |
| `03-decision.md` 4-7절 `simulate` | "CLI에 노출되지 않음" | 위 내용으로 보강(기본 설정에서 도구 인터페이스로는 도달 불가) | R1-Q1 |
| `01-data.md` 1.2절 "코인 전용 / 펀딩비" 행 | `alice-uta`로 노출되지 않는 것으로 보임(추론) | 없음 확정: UTA 내부 ToolCenter에만 등록되고 노출 경로 없음(`UTAManagerSDK.ts:60-61`) | R1-Q2 |
| `01-data.md` 1.4절 "한국" 행, `next.md` "한국 `.KS` 실제 동작" | 설계 의도(추론) | 코드 경로 확정: `.KS`를 거부·변환하는 분기 없이 `yfinance\|005930.KS` → `yf.chart`로 그대로 전달. 실제 Yahoo 응답만 정적 확인 불가. KR 전용 벤더·브로커는 없음 | R1-Q3 |
| `00-overview.md` 7절 `traderhub/SKILL.md:10-12` 행, `next.md` 미확인 | 키가 없을 때 실패 형태(추론) | 요청 전에 `OpenBBError("Missing credential 'fmp_api_key'...")`, 종료 코드 1. hub 대체 없음. 스킬 문서와 모순 확정 | R1-Q4 |
| `01-data.md` 2.4·2.5절, `04-research.md` 5-4절 | 메모리 2000건·7일이고 검색 도구는 인덱스만 봄 | 시작 시 디스크 JSONL에서 "7일 이내, 최신 2000건"을 복구함. 런타임에는 건수 제한만 있음. `readRss`(id)는 디스크 전체를 조회하고 `glob/grep/windowRss`만 인덱스를 봄 | R1-Q5 |
| `next.md` "분석 중 생긴 질문" 3번 | retrospective의 과거 뉴스 | 7일보다 오래된 뉴스는 검색·창 조회 불가. id를 알 때만 `readRss`로 읽을 수 있음 | R1-Q5 |
| `03-decision.md` 4-6절 "헤드리스 실행 실패" 행 | 발사 마커를 쓰지 않음(다음 틱에 재시도) | 틀림. 마커는 디스패치 수락 직후 기록되며 실행 실패 시 자동 재발사 없음(수동 `alice issue retry`만). 마커를 쓰지 않는 것은 디스패치 자체가 throw한 경우(용량·busy 등)뿐 | R1-Q6 |
| `02-schedule.md` 3.2절 "디스패치가 성공한 뒤에만 마커를 씀" | 의미가 모호함 | "디스패치 수락(프로세스 시작 요청) 직후"로 명시 | R1-Q6 |
| `02-schedule.md` 3.2절 cron 세 문장 | 서로 모순처럼 읽힘 | 경우 구분: 마커 없음 → `now−60초` 기준이라 지난 슬롯 무시 / 마커 있음 → 재시작 후 첫 스캔(약 60초 뒤)에 1회 발사 / busy·용량 거부 → `held` catch-up. `catchUp`은 앱 중단에 영향 없음 | R1-Q7 |
| `03-decision.md` 4-2절 "기본 에이전트" 행 | `issueDefaultAgent` 설정 | 결정 순서: Issue assignee 세션 → Issue `agent` → 워크스페이스 headless 설정(`defaultAgent`/`recent`) → `issueDefaultAgent`(기본 null) → interactive 설정·`workspaceDefaultAgent` → `claude`. 새 설치에서의 기본은 `claude` | R1-Q8 |
| `03-decision.md` 4-5절, `05-boundary-and-fit.md` 6.1절, `next.md` 질문 1번 | AI가 직접 push(중간 게이트 미확인) | 확정: `allowAiTrading=true`면 현재 `pendingHash`가 자동으로 들어가 사람 승인 없이 브로커까지 감. 남는 게이트는 readonly 모드, 계정 readOnly/disabled/offline, 가드(설정된 경우만), CLI 그룹 정책. UTA push 라우트의 "only humans can push" 주석은 사실과 다름 | R1-Q9 |
| `03-decision.md` 4-1절, `05-boundary-and-fit.md` 6.1절 | 승인 면제는 UI 위험 경고+이중 확인 뒤에만 켜짐(추론), 안전 경계는 UTA 승인 | 정정: 이중 확인은 UI에만 있음. 기본 배포(신뢰 프록시 없음)에서는 loopback `PUT /api/config/agent`로 인증 없이 켤 수 있고 즉시 반영됨. `agent.json`을 직접 고치면 재시작이나 다음 설정 PUT 때 반영됨. 또 `/api/trading/uta/:id/wallet/push`나 UTA(127.0.0.1, 인증 없음)를 직접 부르면 `allowAiTrading`과 무관하게 push됨. 즉 안전 경계는 "에이전트가 안내된 CLI만 쓴다"는 가정에 기댐 | R1-Q10 |
| `03-decision.md` 4-7절 "사후 수익률 채점" 행, `next.md` 미확인 마지막 항목 | 4개 키워드로 "없음" | 없음 확정(확장 패턴과 범위는 R1-Q11 조사 범위 참조). UTA 스냅샷은 계정 NAV 시계열이고 소비처는 UI 자산 곡선뿐 | R1-Q11 |
| `04-research.md` 5-1절 마지막 행, `00-overview.md` 핵심 발견 5 | 켜고 끄지 않음(일부 추론) | claude·codex 어댑터 인자에 웹 관련 항목이 없음을 확정. 실제 검색 가능 여부는 런타임 기본값에 달림. `agent.claudeCode.allowedTools/disallowedTools`는 죽은 설정이라는 점 추가 | R1-Q12 |
