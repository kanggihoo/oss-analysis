// gbrain@63f62b2 fact-extraction demo. 순수 함수만, LLM·네트워크·DB 호출 없음.
// 실행: deno run --no-remote --no-check --allow-read --allow-write=<scratch> --allow-env demo-pure.mts <scratch-dir>
// 실제 소스를 import 한 것: facts/writeback-gate.ts, facts/writeback-config.ts(resolveWritebackConfig는 getConfig만 가진 가짜 엔진으로 호출),
//   facts/writeback-instructions.ts, facts/eligibility.ts, facts/supersession-threshold.ts, facts/extract-from-fence.ts,
//   facts/conversation-windows.ts, facts/conversation-types.ts, facts/drain-config.ts, facts/visibility.ts, facts/notability-filter.ts,
//   facts/queue.ts(FactsQueue), think/sanitize.ts(INJECTION_PATTERNS, restoreNeutralized), secret-scan.ts(redactFindings), facts-fence.ts(parseFactsFence).
// 줄 범위를 잘라 임시 모듈로 만들어 돌린 것(스크래치에 생성; zod 등 설치되지 않은 의존 때문에 통째로는 import 불가):
//   - facts/extract.ts 143-148, 193-228, 250-263, 337-455, 458, 908-1022 (추출 프롬프트 조립, 정크 필터, 익명 화자 판정, JSON 파서, clampConfidence)
//   - facts/capture-dedup.ts 34-122 (캡처 레인 상수, claimsDiverge, cosineVerdict, wouldDedupSamePage, claimNamesEntity, canonicalConversationKey)
//   - facts/classify.ts 51-64 (cosineSimilarity)
// 대체한 것: extract.ts 조각의 타입(FactKind 등)은 string/any 별칭. capture-dedup 조각의 normalizeAlias·corpusFileSessionId는 실제 모듈을 import.
// 실행하지 못한 것: chat/embed 호출, DB, SQL(지문 함수 gbrain_fact_fingerprint 포함), 훅 프로세스, IPC, 잡 큐 SQL, 드레인 루프.
const SRC = '/Users/kkh/Desktop/oss-analysis/agent-memory/repos/gbrain/src/';
const R = SRC + 'core/';
const scratch = Deno.args[0];
const lines = (f: string) => Deno.readTextFileSync(SRC + f).split('\n');
const slice = (f: string, a: number, b: number) => lines(f).slice(a - 1, b).join('\n');
const out: Record<string, unknown> = {};
const t = async (name: string, fn: () => unknown) => { try { out[name] = await fn(); } catch (e: any) { out[name] = `THROWS ${e.name}: ${e.message}`; } };
const mod = async (name: string, body: string) => { const p = `${scratch}/${name}.mts`; Deno.writeTextFileSync(p, body); return await import('file://' + p); };

// ---- A. Stop-hook 게이트 (writeback-gate.ts 실제) ----
const G: any = await import(R + 'facts/writeback-gate.ts');
await t('gate: gateWritebackTurn 입력별 판정', () => {
  const cases: Record<string, string> = {
    thanks: 'Thanks!',
    ack_phrase: 'okay sounds good thanks so much',
    short_en: 'I like tea',
    short_cjk_12: '我对花生过敏我对花生过敏',
    cjk_6: '我对花生过敏',
    slash: '/compact please summarize everything we did',
    question_only: 'Where should I put the config file? And how do I reload it?',
    question_plus_fact: 'I moved to Berlin last month. Where should I put the config file?',
    fenced_only: '```\nls -la\ntotal 0\n```\n',
    quoted: '> I am leaving YC next month and moving to Paris\n> really',
    durable_fact: "I'm leaving YC next month and I gave up alcohol.",
    bulk: 'x '.repeat(4100),
  };
  return Object.fromEntries(Object.entries(cases).map(([k, v]) => { const r = G.gateWritebackTurn(v); return [k, r.ok ? { ok: true, normalized_len: r.normalized.length, hash24_len: r.hash24.length } : r]; }));
});
await t('gate: 상수와 사유 목록', () => ({ MIN_TURN_CHARS: G.MIN_TURN_CHARS, MIN_TURN_CHARS_CJK: G.MIN_TURN_CHARS_CJK, MAX_TURN_CHARS: G.MAX_TURN_CHARS, reasons: G.WRITEBACK_SKIP_REASONS }));
await t('gate: 같은 턴은 같은 hash24 (공백 정규화 뒤)', () => {
  const a = G.gateWritebackTurn("I'm leaving YC next month   and I gave up alcohol."); const b = G.gateWritebackTurn("I'm leaving YC next month and I gave up alcohol.");
  return { same: a.hash24 === b.hash24, hash24: a.hash24 };
});

// ---- B. memory.auto_writeback 게이트 (writeback-config.ts 실제) ----
const W: any = await import(R + 'facts/writeback-config.ts');
const fakeEngine = (rows: Record<string, string | null>, fail = false) => ({ getConfig: async (k: string) => { if (fail) throw new Error('db down'); return rows[k] ?? null; } });
const fileCfg = (v: string | undefined) => (v === undefined ? {} : { memory: { auto_writeback: v } });
await t('capture-gate: DB/파일 평면 조합별 레인 동작 (resolveWritebackConfig {gate:true} + captureGateDecision)', async () => {
  const scenarios: Array<[string, any, any, boolean]> = [
    ['unset', {}, fileCfg(undefined), false],
    ['db off', { 'memory.auto_writeback': 'off' }, fileCfg('off'), false],
    ['db salient', { 'memory.auto_writeback': 'salient' }, fileCfg('salient'), false],
    ['db all', { 'memory.auto_writeback': 'all' }, fileCfg('all'), false],
    ['db garbage', { 'memory.auto_writeback': 'sure' }, fileCfg(undefined), false],
    ['db absent + file on (drift)', {}, fileCfg('salient'), false],
    ['db absent + file off', {}, fileCfg('off'), false],
    ['db read fails', {}, fileCfg(undefined), true],
  ];
  const res: Record<string, unknown> = {};
  for (const [name, rows, f, fail] of scenarios) {
    const cfg = await W.resolveWritebackConfig(fakeEngine(rows, fail), f, { gate: true });
    res[name] = { mode: cfg.mode, flags: { read_error: cfg.read_error, plane_drift: cfg.plane_drift, off_unsynced: cfg.off_unsynced, mode_valid: cfg.mode_valid }, lanes: Object.fromEntries(W.CAPTURE_GATE_LANES.map((l: string) => { const d = W.captureGateDecision(cfg, l); return [l, `${d.action} (${d.reason})`]; })) };
  }
  return res;
});
await t('writeback-config: 파일 평면(훅 자식) 해석 - 기본 off, ttl 기본값', () => ({
  unset: W.resolveWritebackConfigFromFile({}), salient: W.resolveWritebackConfigFromFile({ memory: { auto_writeback: ' Salient ' } }),
  bad: W.resolveWritebackConfigFromFile({ memory: { auto_writeback: 'yes' } }), DEFAULT_TRANSIENT_TTL: W.DEFAULT_TRANSIENT_TTL, AUTO_WRITEBACK_KEY: W.AUTO_WRITEBACK_KEY,
}));
await t('writeback-config: visibilityPostureFromRaw (미설정=world, world 이외 값=private)', () => Object.fromEntries([undefined, null, '', 'world', 'World', 'private', 'garbage'].map(v => [String(v), W.visibilityPostureFromRaw(v as any)])));
const WI: any = await import(R + 'facts/writeback-instructions.ts');
await t('instructions: ambient writeback 절 (salient/world, all/private)', () => ({
  salient_world: WI.buildAmbientWritebackSection({ mode: 'salient', transientTtl: '3d', visibility: 'world', extractFactsAvailable: true }),
  all_private_noextract: WI.buildAmbientWritebackSection({ mode: 'all', transientTtl: '3d', visibility: 'private', extractFactsAvailable: false }),
}));

// ---- C. 페이지 쓰기 백스톱 적격성 (eligibility.ts 실제) ----
const E: any = await import(R + 'facts/eligibility.ts');
await t('eligibility: isFactsBackstopEligible', () => {
  const body = 'x'.repeat(100);
  const page = (type: string, extra: any = {}, truth = body) => ({ type, compiled_truth: truth, frontmatter: extra });
  return {
    note_ok: E.isFactsBackstopEligible('notes/a', page('note')),
    short: E.isFactsBackstopEligible('notes/a', page('note', {}, 'x'.repeat(79))),
    exactly_80: E.isFactsBackstopEligible('notes/a', page('note', {}, 'x'.repeat(80))),
    concept: E.isFactsBackstopEligible('concepts/a', page('concept')),
    code: E.isFactsBackstopEligible('src/a.ts', page('code')),
    conversation_type: E.isFactsBackstopEligible('chats/a', page('conversation')),
    meetings_prefix_rescue: E.isFactsBackstopEligible('meetings/2026-05-09-foo', page('concept')),
    dream_generated: E.isFactsBackstopEligible('notes/a', page('note', { dream_generated: true })),
    opted_out: E.isFactsBackstopEligible('notes/a', page('note', { facts_backstop: 'off' })),
    subagent_ns: E.isFactsBackstopEligible('wiki/agents/x', page('note')),
    quarantined: E.isFactsBackstopEligible('notes/a', page('note', { quarantine: true })),
    no_page: E.isFactsBackstopEligible('notes/a', null),
    conversation_pipeline_types: E.CONVERSATION_PIPELINE_TYPES, enable_key: E.CONVERSATION_PIPELINE_ENABLE_KEY, rescue: E.BACKSTOP_RESCUE_SLUG_PREFIXES,
  };
});

// ---- D. 추출기 (extract.ts 줄 범위 잘라 실행) ----
const x = await mod('extract-slice', `
import { observationDateLine, observationDateRule, parseExtractedEventDate } from '${R}ai/date-grounding.ts';
import { stripReasoningBlocks } from '${R}llm-json.ts';
import { INJECTION_PATTERNS, restoreNeutralized } from '${R}think/sanitize.ts';
type FactKind = string; type FactAttribution = string; type BrainEngine = any;
${slice('core/facts/extract.ts', 143, 148)}
${slice('core/facts/extract.ts', 193, 228)}
${slice('core/facts/extract.ts', 250, 263)}
${slice('core/facts/extract.ts', 337, 455)}
${slice('core/facts/extract.ts', 458, 458)}
${slice('core/facts/extract.ts', 908, 1022)}
export { renderExtractorSystem, parseExtractorJsonDetailed, clampConfidence };
`);
await t('extract: 시스템 프롬프트 전문 (admitsLow=true, 변형 둘 다 켬)', () => x.buildExtractorSystem(true, { dateGrounding: true, attribution: true }));
await t('extract: 시스템 프롬프트 차이 (admitsLow=false 쪽만 다른 줄)', () => {
  const a = x.buildExtractorSystem(true).split('\n'); const b = x.buildExtractorSystem(false).split('\n');
  return { only_in_admits_low: a.filter((l: string) => !b.includes(l)), only_in_skips_low: b.filter((l: string) => !a.includes(l)), length_chars: [x.buildExtractorSystem(true).length, x.buildExtractorSystem(false).length] };
});
await t('extract: 상수', () => ({ kinds: x.ALL_EXTRACT_KINDS, ENTITY_HINTS_CAP: x.ENTITY_HINTS_CAP, MAX_TURN_TEXT_CHARS: x.MAX_TURN_TEXT_CHARS }));
await t('extract: 정크 필터 isJunkFact (kind별)', () => {
  const c: Array<[string, string?]> = [
    ["Now let me write an oracle that checks it"], ["I'll send the deck by Friday", 'commitment'], ["I'll send the deck by Friday", 'fact'],
    ["The user is asking about pricing"], ["You've hit your org's monthly spend limit."], ["Alice wants a monthly spend limit of $200"],
    ["Bob's API rate limit exceeded 1000 rpm"], ["Another agent is concurrently rewriting src/a.ts"], ['   '], ['Prefers async over meetings'],
  ];
  return c.map(([text, kind]) => ({ text, kind: kind ?? null, junk: x.isJunkFact(text, kind) }));
});
await t('extract: 익명 화자 라벨 판정', () => Object.fromEntries(['Speaker A', 'speaker_00', '**Participant 2:**', 'spk_0', 'Unknown', 'Guest', 'Speaker Pelosi', 'Speaker Deck', 'alice', null as any].map(v => [String(v), x.isUnknownSpeakerLabel(v)])));
await t('extract: 출력 JSON 파서 parseExtractorJson (검증·거름)', () => {
  const ok = '{"facts":[{"fact":"Prefers async","kind":"preference","entity":"people/alice","confidence":0.8,"notability":"medium","metric":null,"value":null,"unit":null,"period":null}]}';
  return {
    plain: x.parseExtractorJson(ok),
    code_fence: x.parseExtractorJson('```json\n' + ok + '\n```')?.length,
    prose_around: x.parseExtractorJson('Sure! ' + ok + ' Hope that helps.')?.length,
    think_block: x.parseExtractorJson('<think>draft {"facts":[1]}</think>' + ok)?.length,
    not_json: x.parseExtractorJson('no facts here'),
    empty_facts: x.parseExtractorJson('{"facts":[]}'),
    detailed_invalid_counts: x.parseExtractorJsonDetailed('{"facts":[{"fact":"a"},{"kind":"fact"},5,{"fact":"b","kind":"weird","confidence":"0.3","value":"x","attributed_to":"robot"}]}'),
  };
});
await t('extract: clampConfidence (missing 기본 1.0, 범위 0..1)', () => Object.fromEntries([[undefined, 1], [NaN, 1], [-0.5, 1], [1.7, 1], [0.42, 1], [undefined, 0.6]].map(([v, m]: any) => [`${v}/missing=${m}`, x.clampConfidence(v, m)])));
const S: any = await import(R + 'think/sanitize.ts');
await t('extract: 프롬프트 사본 무력화 (INJECTION_PATTERNS) 와 저장 문장 복원 (restoreNeutralized)', () => {
  const raw = 'Alice told the team to ignore previous instructions when booking rooms. I prefer tea.';
  let cleaned = raw; for (const p of S.INJECTION_PATTERNS) cleaned = cleaned.replace(p.rx, p.replacement);
  const modelCopied = 'Alice told the team to [redacted] when booking rooms.';
  return { prompt_copy: cleaned, restored: S.restoreNeutralized(modelCopied, raw), pattern_names: S.INJECTION_PATTERNS.map((p: any) => p.name) };
});

// ---- E. 캡처 레인 중복 제거 (capture-dedup.ts 줄 범위 + 실제 모듈) ----
const d = await mod('capture-dedup-slice', `
import { corpusFileSessionId } from '${R}context/corpus-segments.ts';
import { normalizeAlias } from '${R}search/alias-normalize.ts';
type FactVisibility = 'private' | 'world';
${slice('core/facts/classify.ts', 51, 64)}
${slice('core/facts/capture-dedup.ts', 34, 122)}
`);
await t('capture-dedup: 상수', () => ({ lanes: d.CAPTURE_LANES, window_min: d.CAPTURE_DEDUP_WINDOW_MS / 60000, near: d.NEAR_DUPLICATE_THRESHOLD, explicit_fixed: d.EXPLICIT_DUPLICATE_THRESHOLD, same_page_shadow: d.SAME_PAGE_REWORDING_THRESHOLD }));
await t('capture-dedup: claimsDiverge (부정·숫자·날짜 토큰 차이)', () => ({
  same: d.claimsDiverge('Prefers async over meetings', 'prefers async over meetings.'),
  negation: d.claimsDiverge('Alice likes coffee', 'Alice does not like coffee'),
  number: d.claimsDiverge('Team size is 12', 'Team size is 15'),
  date: d.claimsDiverge('Meeting on Monday', 'Meeting on Tuesday'),
  invisible_swap: d.claimsDiverge('Moved to Lisbon', 'Moved to Porto'),
}));
await t('capture-dedup: cosineVerdict (레인별)', () => ({
  explicit_calibrated_hit: d.cosineVerdict('mcp:put_page', 0.96, 'a', 'b', 0.95),
  explicit_below: d.cosineVerdict('mcp:put_page', 0.94, 'a', 'b', 0.95),
  explicit_uncalibrated_null: d.cosineVerdict('mcp:put_page', 0.999, 'a', 'b', null),
  capture_high_never_duplicate: d.cosineVerdict('hook:writeback', 0.999, 'Lives in Seoul', 'Lives in Seoul now', 0.95),
  capture_near: d.cosineVerdict('sweep:corpus', 0.93, 'Lives in Seoul', 'Lives in Seoul', 0.95),
  capture_near_but_diverges: d.cosineVerdict('hook:compact', 0.95, 'Team size is 12', 'Team size is 15', 0.95),
  capture_low: d.cosineVerdict('hook:compact', 0.9, 'a', 'b', 0.95),
}));
await t('capture-dedup: 같은 대화 키 (canonicalConversationKey)', () => ({
  sweep_prefixed: d.canonicalConversationKey('sweep:corpus:sess1.txt'), plain: d.canonicalConversationKey('sess1'), none: d.canonicalConversationKey(null),
}));
await t('capture-dedup: claimNamesEntity (이름 단어 단위 포함)', () => ({
  yes: d.claimNamesEntity('Acme raised $5M', ['Acme']), part_of_word: d.claimNamesEntity('Acmeville raised $5M', ['Acme']), empty: d.claimNamesEntity('x', ['']),
}));
await t('capture-dedup: wouldDedupSamePage (그림자 규칙, 삭제하지 않음)', () => {
  const ctx = { source: 'mcp:put_page', sessionId: 'put_page:notes/a', visibility: 'private' };
  const ex = { source: 'mcp:put_page', source_session: 'put_page:notes/a', visibility: 'private', fact: 'Moved to Lisbon in May' };
  return { reworded: d.wouldDedupSamePage(ctx, ex, 0.9, 'Relocated to Lisbon in May'), capture_lane: d.wouldDedupSamePage({ ...ctx, source: 'hook:compact' }, ex, 0.9, 'x'), below: d.wouldDedupSamePage(ctx, ex, 0.8, 'x') };
});

// ---- F. 모델별 코사인 임계값 (supersession-threshold.ts 실제) ----
const ST: any = await import(R + 'facts/supersession-threshold.ts');
await t('threshold: resolveSupersessionThreshold', () => ({
  voyage: ST.resolveSupersessionThreshold('voyage:voyage-4', 1024), openai: ST.resolveSupersessionThreshold('openai:text-embedding-3-large', 1536),
  override: ST.resolveSupersessionThreshold('openai:text-embedding-3-large', 1536, ST.parseThresholdOverrides('{"openai:text-embedding-3-large@1536": 0.97}')),
  off: ST.resolveSupersessionThreshold('voyage:voyage-4', 1024, ST.parseThresholdOverrides('{"voyage:voyage-4@1024": "off"}')),
  bad_overrides_ignored: [...ST.parseThresholdOverrides('{"a@1": 2, "b@1": "x", "c@1": 0.9}').entries()],
}));

// ---- G. 펜스 행 -> facts 행 투영 (extract-from-fence.ts 실제) ----
const FE: any = await import(R + 'facts/extract-from-fence.ts');
const FF: any = await import(R + 'facts-fence.ts');
await t('fence-projection: extractFactsFromFenceText (활성·취소선·forgotten 행)', () => {
  const body = ['<!--- gbrain:facts:begin -->', '', '| # | claim | kind | confidence | visibility | notability | valid_from | valid_until | source | context |', '|---|---|---|---|---|---|---|---|---|---|',
    '| 1 | Prefers async | preference | 0.9 | world | medium | 2026-10-01 | | user told me | |',
    '| 2 | ~~Lives in Tokyo~~ | fact | 1.0 | world | medium | 2020-01-01 | | chat | superseded by #3 |',
    '| 3 | Lives in Seoul | fact | 1.0 | world | medium | 2026-10-02 | | chat | |',
    '| 4 | ~~Likes jazz~~ | preference | 0.5 | private | low | 2020-01-01 | | chat | forgotten: user asked |',
    '| 5 | No source row | fact | 1.0 | private | medium | | | | |',
    '<!--- gbrain:facts:end -->'].join('\n');
  const parsed = FF.parseFactsFence(body);
  const rows = FE.extractFactsFromFenceText(parsed.facts, 'people/alice', 'default', { nowOverride: new Date('2026-10-24T00:00:00Z') });
  return { warnings: parsed.warnings, rows: rows.map((r: any) => ({ row_num: r.row_num, fact: r.fact, kind: r.kind, vis: r.visibility, valid_from: r.valid_from?.toISOString() ?? null, valid_until: r.valid_until?.toISOString() ?? null, expired_at: r.expired_at?.toISOString() ?? null, superseded_by_row: r.superseded_by_row ?? null, source: r.source, entity_slug: r.entity_slug })) };
});
await t('fence-projection: duplicateActiveFenceRows / normalizeMetricLabel', () => {
  const mk = (rowNum: number, claim: string, active = true, source = 's') => ({ rowNum, claim, active, source });
  return { dup: [...FE.duplicateActiveFenceRows([mk(1, 'A'), mk(2, 'A'), mk(3, 'A', false), mk(4, 'A', true, 'other')])], metric: ['MRR', 'Monthly Recurring Revenue', 'Net Promoter Score', ' ', undefined].map(v => FE.normalizeMetricLabel(v as any)), default_source: FE.FENCE_SOURCE_DEFAULT };
});

// ---- H. 대화 창 분할 (conversation-windows.ts 실제) ----
const CW: any = await import(R + 'facts/conversation-windows.ts');
await t('conversation: splitIntoSegments (30분 간격, 단독 메시지 제외, 30개 상한)', () => {
  const m = (min: number, speaker: string, text: string) => ({ speaker, timestamp: new Date(Date.UTC(2026, 9, 1, 9, min)).toISOString(), text });
  const msgs = [m(0, 'Alice', 'Hi'), m(5, 'Bob', 'Hello'), m(10, 'Alice', 'We ship Friday'), m(100, 'Alice', 'Lone message after a gap'), m(200, 'Bob', 'Back'), m(203, 'Alice', 'Again')];
  const segs = CW.splitIntoSegments(msgs, { pageTitle: 'Standup' });
  return { consts: { gap: CW.DEFAULT_SEGMENT_GAP_MINUTES, max_messages: CW.DEFAULT_SEGMENT_MAX_MESSAGES, min: CW.MIN_SEGMENT_MESSAGES, char_limit: CW.SEGMENT_TEXT_CHAR_LIMIT }, segments: segs.map((s: any) => ({ start: s.startIso, end: s.endIso, n: s.messages.length, participants: s.participants })), rendered_first: CW.renderSegmentForExtraction ? CW.renderSegmentForExtraction('Standup', segs[0]) : null };
});
const CT: any = await import(R + 'facts/conversation-types.ts');
await t('conversation: 적격 페이지 판정', () => ({
  allowed: CT.ALLOWED_TYPES,
  meeting_ok: CT.isConversationFactsEligiblePage({ type: 'meeting', frontmatter: {} }, CT.pageTypesForAllowed(CT.ALLOWED_TYPES)),
  parseable_false: CT.isConversationFactsEligiblePage({ type: 'meeting', frontmatter: { conversation_parseable: false } }, CT.pageTypesForAllowed(CT.ALLOWED_TYPES)),
  strict_meeting: CT.isConversationFactsEligiblePage({ type: 'meeting', frontmatter: {} }, CT.pageTypesForAllowed(CT.ALLOWED_TYPES), true),
  note_type: CT.isConversationFactsEligiblePage({ type: 'note', frontmatter: {} }, CT.pageTypesForAllowed(CT.ALLOWED_TYPES)),
}));

// ---- I. 드레인 설정 (drain-config.ts 실제) ----
const DC: any = await import(R + 'facts/drain-config.ts');
await t('drain-config: 키·기본값·검증', () => ({ keys: Object.fromEntries(Object.entries(DC.FACTS_DRAIN_KEYS).map(([k, v]: any) => [k, `default ${v.fallback} in [${v.min}, ${v.max}]${v.integer ? ' int' : ''}`])),
  validate: ['0.005', '0.01', '1', '100', '101', 'abc'].map(v => [v, DC.validateFactsDrainConfigValue('facts.drain_budget_usd', v)]), max_jobs_frac: DC.validateFactsDrainConfigValue('facts.drain_max_jobs', '2.5') }));

// ---- J. 가시성 기본값 (visibility.ts 실제) ----
const V: any = await import(R + 'facts/visibility.ts');
await t('visibility: resolveDefaultVisibility / resolveVisibilityParam / tightenToPage', async () => {
  const eng = (v: any, fail = false) => ({ getConfig: async () => { if (fail) throw new Error('x'); return v; } });
  return { default_unset: await V.resolveDefaultVisibility(eng(null)), default_world: await V.resolveDefaultVisibility(eng(' World ')), default_garbage: await V.resolveDefaultVisibility(eng('public')), default_error: await V.resolveDefaultVisibility(eng(null, true)),
    param_world_explicit: await V.resolveVisibilityParam(eng(null), 'world'), param_private_over_world_default: await V.resolveVisibilityParam(eng('world'), 'private'), param_unset_uses_config: await V.resolveVisibilityParam(eng('world'), undefined), param_garbage: await V.resolveVisibilityParam(eng('world'), 'secret'),
    tighten_public_page: V.tightenToPage('world', { type: 'note', frontmatter: {} }), tighten_private_page: V.tightenToPage('world', { type: 'note', frontmatter: { visibility: 'private' } }), tighten_access_private: V.tightenToPage('world', { type: 'note', frontmatter: { access: 'private' } }) };
});

// ---- K. 페이지 쓰기 노터빌리티 필터 설정 (notability-filter.ts 실제) ----
const NF: any = await import(R + 'facts/notability-filter.ts');
await t('notability: 필터 어휘와 기본값', async () => ({ filters: NF.NOTABILITY_FILTERS, coerce: ['all', 'high-only', 'medium-and-up', 'x', undefined].map(v => NF.coerceNotabilityFilter(v)), key: NF.PAGE_WRITE_NOTABILITY_FILTER_KEY,
  resolved_unset: await NF.resolvePageWriteNotabilityFilter({ getConfig: async () => null }), resolved_bad: await NF.resolvePageWriteNotabilityFilter({ getConfig: async () => 'weird' }), resolved_high: await NF.resolvePageWriteNotabilityFilter({ getConfig: async () => ' High-Only ' }) }));

// ---- L. 인프로세스 큐 (queue.ts 실제) ----
const Q: any = await import(R + 'facts/queue.ts');
await t('queue: 세션별 직렬화와 용량 초과 시 오래된 것 폐기', async () => {
  const q = new Q.FactsQueue({ cap: 3, perSessionInflightCap: 1 });
  const order: string[] = []; let release!: () => void; const gate = new Promise<void>(r => { release = r; });
  const mk = (name: string, wait = false) => async () => { order.push(`start:${name}`); if (wait) await gate; order.push(`end:${name}`); };
  q.enqueue(mk('a1', true), 'sess-a'); q.enqueue(mk('a2'), 'sess-a'); q.enqueue(mk('b1'), 'sess-b');
  await new Promise(r => setTimeout(r, 20));
  const mid = [...order];
  const depthAfterOverflow: number[] = [q.enqueue(mk('c1'), 'sess-a'), q.enqueue(mk('c2'), 'sess-a'), q.enqueue(mk('c3'), 'sess-a'), q.enqueue(mk('c4'), 'sess-a')];
  const counters = q.getCounters();
  release(); await new Promise(r => setTimeout(r, 50));
  return { mid_order: mid, depthAfterOverflow, counters_after_overflow: counters, final_order: order };
});

// ---- M. 비밀 스캔 (secret-scan.ts 실제; 캡처 레인이 은행에 넣기 전에 쓰는 함수) ----
const SS: any = await import(R + 'secret-scan.ts');
await t('secret-scan: redactFindings 입력/출력 형태 (형식을 보이려는 가짜 키)', () => {
  const r = SS.redactFindings('my key is sk-ant-api03-' + 'A'.repeat(40) + ' and I prefer tea');
  return { text: r.text, n: r.redactions.length };
});

Deno.writeTextFileSync(scratch + '/out.json', JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
