// gbrain@63f62b2 hybrid-search demo. 순수 함수만, 네트워크·DB 없음.
// 실행: deno run --no-remote --allow-read --allow-write=<scratch> --allow-env demo-pure.mts <scratch-dir>
// 실제 소스를 import 하거나(rrf-page-fusion, fusion-lists, intent-weights, dedup, token-budget, cosine-rescore,
// query-intent, source-boost, sql-ranking, keyword-statement, exact-scan, query-cache, snippet-cap, lean-rows, score-contract)
// 줄 범위를 잘라 임시 모듈로 만들어 돌린다.
// 대체한 것:
//  - hybrid.ts는 import 불가(백그라운드 워크 등록 등) -> compiledTruthBoost(124-132), rrfFusionWeighted(1449-1485),
//    cacheScopeKey(1402-1407)만 잘라 실행. COMPILED_TRUTH_BOOST=2.0(58행)은 상수 그대로 주입.
//  - mode.ts는 JSON import 때문에 불가 -> 80-944행(타입, MODE_BUNDLES, resolveSearchMode)을 잘라 실행.
//    DEFAULT_RERANKER_MODEL='voyage:rerank-3-lite'(ai/defaults.ts:19), DEFAULT_RERANK_GATE='off'(crag.ts:291),
//    DEFAULT_RERANK_GATE_MIN_GAP=0.05(crag.ts:294), DEFAULT_RELATIONAL_RERANK_PIN=3(relational-rerank-pin.ts:75)는 값만 주입,
//    lookupRerankerRecipeDefaultTimeout은 voyage 레시피에 default_timeout_ms가 없으므로 undefined 반환으로 대체.
//  - rerank.ts는 zod 때문에 불가 -> 10-271행을 잘라 실행. RerankError/BudgetExhausted/logRerankFailure/estimateTokens/
//    truncateUtf8/warnOncePerProcess는 대체물(가짜 공급자 rerankerFn으로 호출).
//  - expansion.ts는 zod 때문에 불가 -> 16-85행을 잘라 실행. gateway.expand/isAvailable은 대체물, countCJKAwareWords는 실제 cjk.ts.
//  - cosineReScore는 실제 모듈, 엔진은 executeRaw만 가진 가짜(SQL 결과 대신 미리 정한 cosine 행을 돌려줌).
//  - ops/context.ts sourceScopeOpts는 649-672행을 잘라 실행, opError/noSourceGrantError는 대체물.
const R = '/Users/kkh/Desktop/oss-analysis/agent-memory/repos/gbrain/src/core/';
const scratch = Deno.args[0];
const lines = (f: string) => Deno.readTextFileSync(R + f).split('\n');
const slice = (f: string, a: number, b: number) => lines(f).slice(a - 1, b).join('\n');
const out: Record<string, unknown> = {};
const t = async (name: string, fn: () => unknown) => { try { out[name] = await fn(); } catch (e: any) { out[name] = `THROWS ${e.name}: ${e.message}`; } };
const row = (slug: string, chunk_id: number, chunk_source = 'compiled_truth', extra: Record<string, unknown> = {}) =>
  ({ slug, page_id: Math.abs(hash(slug)), title: slug, type: 'note', chunk_text: `text of ${slug}#${chunk_id}`, chunk_source, chunk_id, chunk_index: 0, score: 0, stale: false, source_id: 'default', ...extra });
function hash(s: string) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return h; }
const ids = (rs: any[]) => rs.map(r => `${r.slug}#${r.chunk_id}`);
const scores = (rs: any[]) => rs.map(r => `${r.slug}#${r.chunk_id}=${(+r.score).toFixed(4)}`);

// ---- A. RRF (rrf-page-fusion.ts 실제 + hybrid.ts 잘라냄) ----
const hy = `import { accumulateRrf } from '${R}search/rrf-page-fusion.ts';\nconst COMPILED_TRUTH_BOOST = 2.0;\n`
  + `type SearchResult = any; type FusionListEntry = any; type RrfEntry = any; type RrfAttribution = any;\n`
  + slice('search/hybrid.ts', 124, 132) + '\n' + slice('search/hybrid.ts', 1402, 1407) + '\n' + slice('search/hybrid.ts', 1423, 1435) + '\n' + slice('search/hybrid.ts', 1449, 1485);
Deno.writeTextFileSync(scratch + '/hybrid-slice.mts', hy);
const H: any = await import(scratch + '/hybrid-slice.mts');
const fl: any = await import(R + 'search/fusion-lists.ts');
const iw: any = await import(R + 'search/intent-weights.ts');
await t('rrf: effectiveRrfK(60, w) for intent weights', () => ({
  entity_keyword: iw.effectiveRrfK(60, iw.weightsForIntent('entity').keywordWeight),
  concept_keyword: iw.effectiveRrfK(60, iw.weightsForIntent('concept').keywordWeight),
  concept_vector: iw.effectiveRrfK(60, iw.weightsForIntent('concept').vectorWeight),
  general: iw.weightsForIntent('general'), event: iw.weightsForIntent('event'), temporal: iw.weightsForIntent('temporal'),
}));
{
  // vector 목록: A#1(ct), B#2(ct), A#3(timeline); keyword 목록: B#2, C#4
  const vec = [row('A', 1), row('B', 2), row('A', 3, 'timeline')];
  const kw = [row('B', 2), row('C', 4, 'timeline')];
  await t('rrf: page-level vote, no boost (detail != low)', () => scores(H.rrfFusionWeighted([{ list: vec, k: 60, arm: 'vector' }, { list: kw, k: 60, arm: 'keyword' }], false)));
  await t('rrf: explicit low -> compiled_truth x2.0 after normalize', () => scores(H.rrfFusionWeighted([{ list: vec, k: 60 }, { list: kw, k: 60 }], true)));
  await t('rrf: auto-low tilt 1.2', () => scores(H.rrfFusionWeighted([{ list: vec, k: 60 }, { list: kw, k: 60 }], 1.2)));
  await t('rrf: weight 0.5 on keyword list', () => scores(H.rrfFusionWeighted([{ list: vec, k: 60 }, { list: kw, k: 60, weight: 0.5 }], false)));
  await t('rrf: synthetic chunkless title row never gets compiled_truth boost', () => H.compiledTruthBoost({ chunk_id: 0, chunk_text: '', chunk_source: 'compiled_truth' }, true));
  await t('rrf: single list normalized to rank-1 = 1.0', () => scores(H.rrfFusionWeighted([{ list: vec, k: 60 }], false)));
  await t('rrf: RRF_K=60 constant check (1/(60+0))', () => 1 / 60);
}
// composeFusionLists: 역할별 k/weight
await t('compose: expansion budget null (legacy) vs 1.0, 2 variants', () => {
  const mk = (n: string) => [row(n, 1)];
  const arms = [{ list: mk('o'), role: 'original' }, { list: mk('v1'), role: 'variant' }, { list: mk('v2'), role: 'variant' }];
  const ks = { vectorK: 60, textRrfK: 60, imageRrfK: 60, keywordK: 60, baseRrfK: 60 };
  const run = (b: number | null) => fl.composeFusionLists({ arms, keywordFusionList: mk('k'), titleFusionList: [], relationalList: [], includeRelational: true, ks, knobs: { expansionVariantBudget: b } })
    .map((e: any) => `${e.arm}:k=${e.k}${e.weight !== undefined ? ',w=' + e.weight : ''}`);
  return { legacy_null: run(null), budget_1: run(1), budget_0_5: run(0.5) };
});
await t('compose: title list only if non-empty; relational only if non-empty', () => {
  const ks = { vectorK: 60, textRrfK: 60, imageRrfK: 60, keywordK: 50, baseRrfK: 60 };
  return fl.composeFusionLists({ arms: [{ list: [row('o', 1)], role: 'original' }], keywordFusionList: [row('k', 1)], titleFusionList: [row('t', 0)], relationalList: [row('r', 5)], includeRelational: true, ks, knobs: { expansionVariantBudget: null } }).map((e: any) => `${e.arm}:k=${e.k}`);
});

// ---- B. cosine re-score (실제 모듈 + 가짜 엔진) ----
const cr: any = await import(R + 'search/cosine-rescore.ts');
await t('cosine: blended = 0.7*normRrf + 0.3*cosine; unhydrated -> cosine 0', async () => {
  const fused = [{ ...row('A', 1), score: 0.04 }, { ...row('B', 2), score: 0.02 }, { ...row('C', 3), score: 0.01 }];
  const eng: any = { executeRaw: async () => [{ id: 1, cosine: 0.5 }, { id: 2, cosine: 0.9 }] }; // chunk 3은 hydrate 안 됨
  const r = await cr.cosineReScore(eng, fused, new Float32Array([1, 0]), 'embedding');
  return r.map((x: any) => `${x.slug}#${x.chunk_id} score=${x.score.toFixed(4)} cosine=${x.cosine}`);
});
await t('cosine: no row hydrated -> input untouched; sql failure -> js fallback; both fail -> input untouched', async () => {
  const fused = [{ ...row('A', 1), score: 0.04 }];
  const none = await cr.cosineReScore({ executeRaw: async () => [] }, fused, new Float32Array([1, 0]));
  const fb = await cr.cosineReScore({ executeRaw: async () => { throw Object.assign(new Error('x'), { code: '42P01' }); }, getEmbeddingsByChunkIds: async () => new Map([[1, new Float32Array([1, 0])]]) }, fused, new Float32Array([1, 0]));
  const dead = await cr.cosineReScore({ executeRaw: async () => { throw new Error('x'); }, getEmbeddingsByChunkIds: async () => { throw new Error('y'); } }, fused, new Float32Array([1, 0]));
  return { none_same_object: none === fused, js_fallback_score: fb[0].score, js_fallback_cosine: fb[0].cosine, dead_same_object: dead === fused };
});

// ---- C. dedup (실제 dedup.ts) ----
const dd: any = await import(R + 'search/dedup.ts');
const ch = (slug: string, chunk_id: number, score: number, chunk_source = 'timeline', type = 'note', text = `unique words ${slug} ${chunk_id}`) =>
  ({ ...row(slug, chunk_id, chunk_source), score, type, chunk_text: text });
await t('dedup: 5 chunks of one page -> at most 2 kept (+ compiled_truth guarantee appended)', () => {
  const rs = [ch('p', 1, 0.9), ch('p', 2, 0.8), ch('p', 3, 0.7), ch('p', 4, 0.6), ch('p', 5, 0.5, 'compiled_truth')];
  return { out: ids(dd.dedupResults(rs)) };
});
await t('dedup: same-page Jaccard > 0.85 dropped; cross-page near-duplicates both kept', () => {
  const same = 'a b c d e f g h i j';
  const rs = [ch('p', 1, 0.9, 'compiled_truth', 'note', same), ch('p', 2, 0.8, 'compiled_truth', 'note', same + ' k'), ch('q', 3, 0.7, 'compiled_truth', 'note', same)];
  return ids(dd.dedupResults(rs));
});
await t('dedup: type ratio 60% (only when >1 type)', () => {
  const rs = [...Array.from({ length: 8 }, (_, i) => ch(`n${i}`, i + 1, 0.9 - i * 0.01, 'compiled_truth', 'note')), ch('c1', 20, 0.5, 'compiled_truth', 'company'), ch('c2', 21, 0.4, 'compiled_truth', 'company')];
  return { kept_types: dd.dedupResults(rs).reduce((m: any, r: any) => (m[r.type] = (m[r.type] ?? 0) + 1, m), {}) };
});
await t('dedup: one type only -> ratio cap not applied', () => dd.dedupResults(Array.from({ length: 4 }, (_, i) => ch(`n${i}`, i + 1, 0.9 - i * 0.01, 'compiled_truth', 'note'))).length);
await t('dedup: same slug in two sources are two pages', () => ids(dd.dedupResults([{ ...ch('x', 1, 0.9), source_id: 's1' }, { ...ch('x', 2, 0.8), source_id: 's2' }, { ...ch('x', 3, 0.7), source_id: 's1' }, { ...ch('x', 4, 0.6), source_id: 's1' }])));

// ---- D. token budget (실제 token-budget.ts) ----
const tb: any = await import(R + 'search/token-budget.ts');
const big = (n: number) => 'x'.repeat(n * 4);
await t('budget: estimateTokens ascii/CJK', () => ({ ascii_8: tb.estimateTokens('abcdefgh'), ascii_9: tb.estimateTokens('abcdefghi'), cjk_3: tb.estimateTokens('日本語'), mixed: tb.estimateTokens('ab日本'), empty: tb.estimateTokens('') }));
await t('budget: skip oversize, keep packing (title cost counted)', () => {
  const rs = [{ ...row('a', 1), title: '', chunk_text: big(100) }, { ...row('b', 2), title: '', chunk_text: big(500) }, { ...row('c', 3), title: '', chunk_text: big(100) }];
  const r = tb.enforceTokenBudget(rs, 250); return { ids: ids(r.results), meta: r.meta };
});
await t('budget: head alone over budget -> 1 truncated copy (minKeep failsafe)', () => {
  const rs = [{ ...row('a', 1), title: 'T', chunk_text: big(1000) }, row('b', 2)];
  const r = tb.enforceTokenBudget(rs, 100); return { n: r.results.length, used: r.meta.used, truncated: r.meta.truncated, text_len: r.results[0].chunk_text.length, original_untouched: rs[0].chunk_text.length };
});
await t('budget: undefined or <=0 -> no-op', () => { const rs = [row('a', 1), row('b', 2)]; return [tb.enforceTokenBudget(rs, undefined).results.length, tb.enforceTokenBudget(rs, 0).results.length, tb.enforceTokenBudget(rs, -5).meta]; });
await t('budget: packToBudget stops at first oversize (memory verbs variant)', () => tb.packToBudget([1, 50, 1], (n: number) => n, 10).items);

// ---- E. reranker (rerank.ts 잘라냄 + 가짜 공급자) ----
const rrSrc = `import { createHash } from 'node:crypto';
type SearchResult = any; type RerankInput = any; type RerankMeta = any; type RerankResult = any; type RerankFailureReason = string;
export class RerankError extends Error { reason: string; constructor(m: string, reason: string) { super(m); this.reason = reason; } }
class BudgetExhausted extends Error {}
export const AUDIT: any[] = [];
const logRerankFailure = (x: any) => { AUDIT.push(x); };
const estimateTokens = (s: string) => Math.ceil(s.length / 4);
const truncateUtf8 = (s: string, n: number) => s.slice(0, n);
const warnOncePerProcess = (_k: string, _m: string) => {};
` + slice('search/rerank.ts', 10, 271);
Deno.writeTextFileSync(scratch + '/rerank-slice.mts', rrSrc);
const RR: any = await import(scratch + '/rerank-slice.mts');
const pool = () => ['A', 'B', 'C', 'D', 'E'].map((s, i) => row(s, i + 1));
const callOpts = (fn: any, extra: any = {}) => { const ev: any = { skip: null, fail: null, pass: null }; return { opts: { enabled: true, topNIn: 4, topNOut: null, rerankerFn: fn, onSkip: (r: string) => ev.skip = r, onFailure: (r: string) => ev.fail = r, onPassThrough: (r: string) => ev.pass = r, ...extra }, ev }; };
await t('rerank: head reordered by provider order, tail (past topNIn) keeps RRF position', async () => {
  const { opts, ev } = callOpts(async () => [{ index: 2, relevanceScore: 0.9 }, { index: 0, relevanceScore: 0.5 }, { index: 3, relevanceScore: 0.4 }, { index: 1, relevanceScore: 0.1 }]);
  const r = await RR.applyReranker('q', pool(), opts); return { order: ids(r), rerank_scores: r.map((x: any) => x.rerank_score), delta: r.map((x: any) => x.reranker_delta), ev };
});
await t('rerank: exact score ties keep input (fused) order', async () => {
  const { opts } = callOpts(async () => [{ index: 3, relevanceScore: 0.7 }, { index: 1, relevanceScore: 0.7 }, { index: 0, relevanceScore: 0.7 }, { index: 2, relevanceScore: 0.2 }]);
  return ids(await RR.applyReranker('q', pool(), opts));
});
await t('rerank: topNOut truncates; items provider omitted are appended at end of head', async () => {
  const { opts } = callOpts(async () => [{ index: 1, relevanceScore: 0.9 }], { topNOut: 3 });
  return ids(await RR.applyReranker('q', pool(), opts));
});
await t('rerank: no_key -> input returned, onSkip, no audit row', async () => {
  const { opts, ev } = callOpts(async () => { throw new RR.RerankError('no key', 'no_key'); }); RR.AUDIT.length = 0;
  const p = pool(); const r = await RR.applyReranker('q', p, opts); return { same_object: r === p, ev, audit_rows: RR.AUDIT.length };
});
await t('rerank: timeout / auth / budget / unknown -> input returned, onFailure reason, audit row', async () => {
  const res: any = {};
  for (const [name, err] of [['timeout', new RR.RerankError('t', 'timeout')], ['auth', new RR.RerankError('a', 'auth')], ['rate_limit', new RR.RerankError('r', 'rate_limit')], ['network', new RR.RerankError('n', 'network')], ['plain Error', new Error('boom')]] as const) {
    const { opts, ev } = callOpts(async () => { throw err; }); RR.AUDIT.length = 0; const p = pool(); const r = await RR.applyReranker('q', p, opts);
    res[name] = { same_object: r === p, fail: ev.fail, audit_reason: RR.AUDIT[0]?.reason };
  }
  return res;
});
await t('rerank: provider returns empty array / non-array -> pass-through with reason', async () => {
  const res: any = {};
  for (const [name, val] of [['empty', []], ['non_array', { results: [] }]] as const) { const { opts, ev } = callOpts(async () => val); const p = pool(); const r = await RR.applyReranker('q', p, opts); res[name] = { same_object: r === p, pass: ev.pass }; }
  return res;
});
await t('rerank: disabled / empty input / topNIn<=0 -> input as is, provider not called', async () => {
  let called = 0; const fn = async () => { called++; return []; };
  const p = pool();
  const a = await RR.applyReranker('q', p, { enabled: false, topNIn: 4, topNOut: null, rerankerFn: fn });
  const b = await RR.applyReranker('q', [], { enabled: true, topNIn: 4, topNOut: null, rerankerFn: fn });
  const c = await RR.applyReranker('q', p, { enabled: true, topNIn: 0, topNOut: null, rerankerFn: fn });
  return { a_same: a === p, b_len: b.length, c_same: c === p, called };
});
await t('rerank: document sent = chunk_text (title if empty), capped by capRerankDoc', async () => {
  const sent: any[] = []; const p = [{ ...row('A', 1), chunk_text: '' }, { ...row('B', 2), chunk_text: 'b'.repeat(3000) }];
  await RR.applyReranker('q', p, { enabled: true, topNIn: 2, topNOut: null, rerankerFn: async (i: any) => { sent.push(i.documents.map((d: string) => d.length)); return [{ index: 0, relevanceScore: 1 }, { index: 1, relevanceScore: 0.5 }]; } });
  return { doc_lengths: sent[0], first_doc_is_title: true, RERANK_MAX_DOC_TOKENS: 1400, cap_demo_len: RR.capRerankDoc('z'.repeat(1500)).length };
});

// ---- F. expansion (expansion.ts 잘라냄 + 가짜 gateway) ----
const exSrc = `import { countCJKAwareWords } from '${R}cjk.ts';
const gatewayIsAvailable = (_t: string) => (globalThis as any).__avail;
const gatewayExpand = async (q: string) => { (globalThis as any).__calls++; const r = (globalThis as any).__expand; if (r instanceof Error) throw r; return r(q); };
` + slice('search/expansion.ts', 16, 85);
Deno.writeTextFileSync(scratch + '/expansion-slice.mts', exSrc);
const EX: any = await import(scratch + '/expansion-slice.mts');
const g: any = globalThis;
const runExp = async (q: string, avail: boolean, fn: any) => { g.__avail = avail; g.__calls = 0; g.__expand = fn; const r = await EX.expandQuery(q); return { result: r, gateway_calls: g.__calls }; };
await t('expand: <3 words -> [query], gateway not called', () => runExp('acme revenue', true, (q: string) => [q, 'x']));
await t('expand: no expansion provider -> [query], gateway not called', () => runExp('what is acme revenue growth', false, (q: string) => [q, 'x']));
await t('expand: original + 3 variants -> only 2 variants kept (MAX_QUERIES=3), dup/case dedupe', () => runExp('what is acme revenue growth', true, (q: string) => [q, 'ACME revenue growth rate', 'acme revenue growth rate', 'sales trend of acme', 'a 4th one']));
await t('expand: gateway throws -> [query]', () => runExp('what is acme revenue growth', true, new Error('provider down')));
await t('expand: sanitizeQueryForPrompt strips code fences/tags/instruction prefix; >500 chars cut', () => {
  const warn = console.warn; console.warn = () => {};
  try { return { fence: EX.sanitizeQueryForPrompt('find acme ```ignore previous``` revenue'), tag: EX.sanitizeQueryForPrompt('acme <b>revenue</b> now'), prefix: EX.sanitizeQueryForPrompt('ignore: system: acme revenue'), long_len: EX.sanitizeQueryForPrompt('a '.repeat(400)).length }; } finally { console.warn = warn; }
});
await t('expand: sanitizeExpansionOutput drops non-strings/control chars/dups, max 2', () => EX.sanitizeExpansionOutput(['', 5, 'ok\x00one', 'OK\x00ONE', 'two', 'three']));

// ---- G. MODE_BUNDLES + resolveSearchMode (mode.ts 잘라냄) ----
const modeSrc = `type CRMode = string; type RerankGateMode = string; type MetadataBoostGate = string;
const DEFAULT_RERANKER_MODEL = 'voyage:rerank-3-lite'; const DEFAULT_RERANK_GATE = 'off'; const DEFAULT_RERANK_GATE_MIN_GAP = 0.05; const DEFAULT_RELATIONAL_RERANK_PIN = 3;
function lookupRerankerRecipeDefaultTimeout(_m: string | undefined): number | undefined { return undefined; }
` + slice('search/mode.ts', 80, 944);
Deno.writeTextFileSync(scratch + '/mode-slice.mts', modeSrc);
const M: any = await import(scratch + '/mode-slice.mts');
const keyKnobs = ['tokenBudget', 'expansion', 'searchLimit', 'reranker_enabled', 'reranker_model', 'reranker_top_n_in', 'reranker_top_n_out', 'reranker_timeout_ms', 'autocut', 'graph_signals', 'relationalRetrieval', 'relational_planner', 'contextual_retrieval', 'collapse', 'rank_priors', 'title_boost', 'keywordOrFallback', 'intentWeighting', 'metadata_boost_gate', 'cache_enabled', 'cache_ttl_seconds', 'cache_similarity_threshold'];
await t('mode: MODE_BUNDLES key knobs per mode', () => Object.fromEntries(['conservative', 'balanced', 'tokenmax'].map(m => [m, Object.fromEntries(keyKnobs.map(k => [k, M.MODE_BUNDLES[m][k]]))])));
await t('mode: knobs that differ between bundles (all keys)', () => {
  const keys = Object.keys(M.MODE_BUNDLES.balanced); const diff: any = {};
  for (const k of keys) { const v = ['conservative', 'balanced', 'tokenmax'].map(m => M.MODE_BUNDLES[m][k]); if (new Set(v.map(x => JSON.stringify(x))).size > 1) diff[k] = v; }
  return { bundle_key_count: keys.length, differing: diff };
});
await t('mode: resolve chain per-call > override > bundle', () => {
  const r = M.resolveSearchMode({ mode: 'tokenmax', overrides: { searchLimit: 7, reranker_enabled: false }, perCall: { searchLimit: 3 } });
  return { searchLimit: r.searchLimit, reranker_enabled: r.reranker_enabled, tokenBudget: r.tokenBudget, resolved_mode: r.resolved_mode };
});
await t('mode: unset/invalid/uppercase mode', () => ({ unset: M.resolveSearchMode({}).resolved_mode, invalid: [M.resolveSearchMode({ mode: 'turbo' }).resolved_mode, M.resolveSearchMode({ mode: 'turbo' }).mode_valid], upper_trim: M.resolveSearchMode({ mode: '  TokenMax ' }).resolved_mode }));
await t('mode: tokenBudget undefined in tokenmax stays undefined unless override', () => [M.resolveSearchMode({ mode: 'tokenmax' }).tokenBudget, M.resolveSearchMode({ mode: 'tokenmax', overrides: { tokenBudget: 9000 } }).tokenBudget]);

// ---- H. 의도 분류 (실제 query-intent.ts) ----
const qi: any = await import(R + 'search/query-intent.ts');
await t('intent: classifyQuery samples', () => Object.fromEntries(['who is alice-example', 'when did we last meet acme', 'acme raised $5M announcement', 'what is the ownership economy', 'everything about acme', 'catch me up on acme today', 'acme revenue', 'show me photos of the offsite'].map(q => { const c = qi.classifyQuery(q); return [q, `${c.intent}/detail=${c.suggestedDetail}/rec=${c.suggestedRecency}/sal=${c.suggestedSalience}/mod=${c.suggestedModality}`]; })));

// ---- I. 소스 범위·가시성 (ops/context.ts 잘라냄, sql-ranking/keyword-statement 실제) ----
const ctxSrc = `const NO_SOURCES = '__none__', ALL_SOURCES = '__all__';
type OperationContext = any;
const noSourceGrantError = (_a: unknown, _b: unknown) => new Error('no_source_grant');
const opError = (code: string, msg: string) => Object.assign(new Error(msg), { code });
const sourceGrantFix = (_a: unknown) => ({});
` + slice('ops/context.ts', 649, 672);
Deno.writeTextFileSync(scratch + '/ctx-slice.mts', ctxSrc);
const CX: any = await import(scratch + '/ctx-slice.mts');
const sc = (ctx: any) => { try { return CX.sourceScopeOpts(ctx); } catch (e: any) { return `THROWS ${e.code ?? e.message}`; } };
await t('scope: sourceScopeOpts ladder', () => ({
  federated_array_wins_over_scalar: sc({ remote: true, sourceId: 'a', auth: { allowedSources: ['x', 'y'] } }),
  scalar: sc({ remote: true, sourceId: 'a' }),
  neither_local: sc({ remote: false }),
  empty_array_local_no_scalar: sc({ remote: false, auth: { allowedSources: [] } }),
  empty_array_remote_no_scalar: sc({ remote: true, auth: { allowedSources: [] } }),
  empty_array_remote_with_scalar: sc({ remote: true, sourceId: 'a', auth: { allowedSources: [] } }),
  all_sentinel_local: sc({ remote: false, sourceId: '__all__' }),
  all_sentinel_remote_stays_literal: sc({ remote: true, sourceId: '__all__' }),
  none_sentinel: sc({ remote: true, sourceId: '__none__' }),
  remote_unset_no_auth: sc({ remote: true }),
}));
const sr: any = await import(R + 'search/sql-ranking.ts');
const kws: any = await import(R + 'search/keyword-statement.ts');
await t('visibility: buildVisibilityClause text (every arm adds this)', () => sr.buildVisibilityClause('p', 's', { chunkAlias: 'cc' }).replace(/\s+/g, ' '));
await t('visibility: remote adds safe-chunk + (excludePrivate) private filter', () => sr.buildVisibilityClause('p', 's', { requireSafeChunks: true, excludePrivate: true }).replace(/\s+/g, ' '));
await t('scope SQL: keyword where for sourceIds / [] / sourceId / none (params shown)', () => {
  const w = (o: any) => { const m = kws.buildKeywordMatch('acme revenue', o); return { has_source_clause: /p\.source_id/.test(m.where), params: m.params.slice(1) }; };
  return { sourceIds_ab: w({ sourceIds: ['a', 'b'] }), sourceIds_empty_array: w({ sourceIds: [] }), sourceId_a: w({ sourceId: 'a' }), none: w({}), both_array_and_scalar: w({ sourceIds: ['a'], sourceId: 'z' }) };
});
await t('keyword SQL: websearch_to_tsquery on chunk vector, text modality only; CJK -> LIKE AND', () => ({
  ascii_pred: kws.buildKeywordMatch('acme revenue', {}).where.split(' AND p.')[0].trim().slice(0, 80),
  modality_text_only: /cc\.modality = 'text'/.test(kws.buildKeywordMatch('acme', {}).where),
  cjk_pred: kws.buildKeywordMatch('日本 売上', {}).where.slice(0, 90),
  blank_query_null: kws.buildKeywordMatch('   ', {}),
}));
await t('keyword OR fallback builder (zero strict rows -> one retry, tagged keyword_relaxed)', () => ({
  three_terms: sr.buildOrFallbackWebsearchQuery('acme revenue growth'), single_term: sr.buildOrFallbackWebsearchQuery('acme'),
  quoted_phrase_no_fallback: sr.buildOrFallbackWebsearchQuery('"acme revenue"'), negation_no_fallback: sr.buildOrFallbackWebsearchQuery('acme -revenue'),
  dedup_and_drop_or_and: sr.buildOrFallbackWebsearchQuery('Acme acme OR growth AND x'), interior_hyphen_ok: sr.buildOrFallbackWebsearchQuery('foo-bar baz'),
  websearch_bound_long_term_count: sr.boundWebsearchQuery(Array.from({ length: 300 }, (_, i) => 'w' + i).join(' ')).split(' ').length,
}));
const sb: any = await import(R + 'search/source-boost.ts');
await t('source boost: defaults, config merge, none, env, hard excludes', () => ({
  hard_excludes: sb.resolveHardExcludes(), include_opt_back: sb.resolveHardExcludes(undefined, ['test/'], ''),
  default_people: sb.resolveBoostMap('', null)['people/'], config_override: sb.resolveBoostMap('', 'wiki/:1.3,people/:2.0')['people/'],
  none_drops_defaults: Object.keys(sb.resolveBoostMap('', 'none,wiki/:1.3')), factor_case_high_bypass: sr.buildSourceFactorCase('p.slug', { 'people/': 1.2 }, 'high'),
  factor_case_default: sr.buildSourceFactorCase('p.slug', { 'people/': 1.2, 'people/x/': 2 }, undefined, 'unv').replace(/\s+/g, ' '),
}));
await t('limits: perArmPoolLimit = min(max(2*limit, 50, offset+limit), 100)', async () => {
  const ep: any = await import(R + 'search/eval-pool-depth.ts');
  return { limit10: ep.perArmPoolLimit(10, 0, 50), limit25: ep.perArmPoolLimit(25, 0, 50), limit50: ep.perArmPoolLimit(50, 0, 50), limit20_offset90: ep.perArmPoolLimit(20, 90, 50), limit200: ep.perArmPoolLimit(200, 0, 50), cap: ep.searchLimitCap() };
});

// ---- J. 행 모양: snippet cap, lean rows, score contract (실제) ----
const sn: any = await import(R + 'search/snippet-cap.ts');
const ln: any = await import(R + 'search/lean-rows.ts');
const sf: any = await import(R + 'search/score-contract.ts');
await t('snippet: resultChunkCap precedence and marker', () => {
  const cap = (a: unknown, b: number) => sn.resultChunkCap(a, b);
  const r = sn.applySnippetCap([{ slug: 'p', chunk_id: 9, chunk_index: 2, chunk_text: 'x'.repeat(20) }, { slug: 'q', chunk_id: 1, chunk_index: 0, chunk_text: 'short' }], 10);
  return { explicit_0: cap(0, 0), explicit_50: cap(50, 0), no_explicit_no_cap: cap(undefined, 0), subagent_cap_300: cap(undefined, 300), RESULT_CHUNK_CHARS: sn.RESULT_CHUNK_CHARS, rows: r.map((x: any) => x.chunk_text) };
});
await t('lean rows: remote default keeps only agent-facing fields; local = full', () => {
  const full = { ...row('p', 3), score: 0.123456, cosine: 0.8, base_score: 0.1, keyword_hit: true, effective_date: '2026-01-02', rerank_score: 0.9 };
  return { lean: ln.leanRow(full), remote_default: ln.resultRowsFor({ remote: true }, undefined), local_default: ln.resultRowsFor({ remote: false }, undefined), remote_fields_full: ln.resultRowsFor({ remote: true }, 'full') };
});
await t('score contract: reranked list -> returned score = rerank score, non-increasing; fused_score keeps old', () => {
  // 실제 파이프라인의 reranked 목록은 rerank 점수 내림차순이다. 마지막 c는 rerank 점수가 없는(이름 매칭 등 주입된) 행.
  const rows = [{ slug: 'b', score: 0.9, rerank_score: 0.8 }, { slug: 'a', score: 0.5, rerank_score: 0.4 }, { slug: 'c', score: 0.1 }];
  return { reranked: sf.scoresFollowRank(rows), not_reranked_unchanged: sf.scoresFollowRank([{ slug: 'x', score: 0.3 }, { slug: 'y', score: 0.2 }]) };
});

// ---- K. 의미 캐시 (query-cache.ts 실제, DB 없음) ----
const qc: any = await import(R + 'search/query-cache.ts');
await t('cache: availability hard-off; defaults; row id; text guard', () => ({
  semanticResultCacheAvailable: qc.semanticResultCacheAvailable(), DEFAULT_SIMILARITY_THRESHOLD: qc.DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_TTL_SECONDS: qc.DEFAULT_TTL_SECONDS,
  row_id_same_inputs: qc.cacheRowId('q', 's', 'k') === qc.cacheRowId('q', 's', 'k'), row_id_diff_knobs: qc.cacheRowId('q', 's', 'k1') === qc.cacheRowId('q', 's', 'k2'), row_id_len: qc.cacheRowId('q', 's', 'k').length,
  guard_equal_after_normalize: qc.cacheTextGuard('Who  is ACME', 'who is acme'), guard_dice_pass: qc.cacheTextGuard('who is acme corp', 'who is acme'), guard_reject: qc.cacheTextGuard('apple pie recipe', 'quarterly revenue'),
  scope_key_federated: H.cacheScopeKey({ sourceIds: ['b', 'a'] }), scope_key_scalar: H.cacheScopeKey({ sourceId: 'a' }), scope_key_unscoped: H.cacheScopeKey({}),
  filter_by_scope: H.filterResultsByCallerScope([{ source_id: 'a' }, { source_id: 'b' }, {}], { sourceIds: ['a'] }).length,
}));

// ---- L. search_exact (exact-scan.ts 실제) ----
const es: any = await import(R + 'search/exact-scan.ts');
await t('exact: phrase -> POSIX regex (words in order, any whitespace), constants', () => ({
  p1: es.phrasePattern('quarterly  board\tpack'), p2: es.phrasePattern('INV-2024.0042 (v2)'), blank: es.phrasePattern('  '),
  limits: { EXACT_DEFAULT_LIMIT: es.EXACT_DEFAULT_LIMIT, EXACT_MAX_LIMIT: es.EXACT_MAX_LIMIT, EXACT_DEFAULT_SECONDS: es.EXACT_DEFAULT_SECONDS, EXACT_MAX_SECONDS: es.EXACT_MAX_SECONDS, EXACT_MAX_PHRASE_CHARS: es.EXACT_MAX_PHRASE_CHARS, EXACT_SNIPPETS_PER_PAGE: es.EXACT_SNIPPETS_PER_PAGE },
}));
await t('exact: scan statement page filters (remote adds safe-chunk gap rule)', () => {
  const base = { phrase: 'x y', excludeSlugPrefixes: ['test/'], excludePrivate: false, remote: false, limit: 10, deadlineMs: 0 };
  const s = es.buildExactBatchStatement(base, 0, 100).sql; const sr2 = es.buildExactBatchStatement({ ...base, remote: true, sourceIds: ['a'] }, 0, 100).sql;
  return { local_filters: ['deleted_at IS NULL', 'NOT s.archived', "? 'quarantine'", 'pinned_question', 'LIKE'].map(f => [f, s.includes(f)]), remote_has_unsealed: sr2.includes("'unsealed'"), local_has_unsealed: s.includes("'unsealed'"), source_clause: /p\.source_id = ANY/.test(sr2) };
});
await t('exact: run with scripted engine -> complete / limit / gaps', async () => {
  const mk = (n: number, gap: string | null = null) => ({ page_id: n, slug: `s${n}`, source_id: 'default', title: `T${n}`, type: 'note', gap, matching_chunks: gap ? null : 1, snippets: gap ? null : [{ chunk_index: 0, chunk_source: 'compiled_truth', text: 'hit' }] });
  const run = (rows: any[], limit = 10, extra: any = {}) => es.runExactScan({ executeRaw: async (_s: string, p: any[]) => rows.filter(r => r.page_id > p[0]).slice(0, p[1]) }, { phrase: 'x', excludeSlugPrefixes: [], excludePrivate: false, remote: false, limit, deadlineMs: Date.now() + 5000, batchPages: 2, ...extra })
    .then((r: any) => ({ matches: r.matches.map((m: any) => m.slug), complete: r.complete, reasons: r.incomplete_reasons, resume_after: r.resume_after, scanned: r.pages_scanned, unreadable: r.unreadable.total }));
  return { all_match: await run([mk(1), mk(2), mk(3)]), limit_hit: await run([mk(1), mk(2), mk(3)], 2), with_gap: await run([mk(1), mk(2, 'unchunked'), mk(3)]), deadline_passed: await run([mk(1)], 10, { deadlineMs: Date.now() - 1 }) };
});

Deno.writeTextFileSync(scratch + '/out.json', JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
