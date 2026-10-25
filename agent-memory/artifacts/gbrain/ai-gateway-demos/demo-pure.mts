// pure functions only, no network or keys. run: deno run --no-remote --allow-read demo-pure.mts
const R = '/Users/kkh/Desktop/oss-analysis/agent-memory/repos/gbrain/src/core/';
const { parseModelId, resolveRecipe, assertTouchpoint, embeddingDimsForModel } = await import(R + 'ai/model-resolver.ts');
const { planEmbedRequests, truncateEmbedInputs } = await import(R + 'ai/embed-batch-plan.ts');
const { screenEmbeddings } = await import(R + 'ai/embedding-guard.ts');
const cf: any = await import(R + 'ai/chat-fallback.ts').catch((e: Error) => ({ importError: e.message.split('\n')[0] }));
const { normalizeChatFallbackChain, chatFallbackAttempts } = cf;
const rc: any = await import(R + 'budget/reservation-cost.ts').catch((e: Error) => ({ importError: e.message.split('\n')[0] }));
const out: Record<string, unknown> = {};
const t = (name: string, fn: () => unknown) => { try { out[name] = fn(); } catch (e: any) { out[name] = `THROWS ${e.name}: ${e.message}`; } };

t('parse colon', () => parseModelId('openrouter:anthropic/claude-sonnet-4-6'));
t('parse slash', () => parseModelId('anthropic/claude-sonnet-4-6'));
t('parse bare', () => parseModelId('claude-sonnet-4-6'));
t('alias', () => resolveRecipe('anthropic:claude-haiku-4-5').parsed);
t('unknown provider', () => resolveRecipe('nope:x').parsed);
t('anthropic embedding touchpoint', () => assertTouchpoint(resolveRecipe('anthropic:claude-sonnet-4-6').recipe, 'embedding', 'x'));
t('dims openai', () => embeddingDimsForModel(resolveRecipe('openai:text-embedding-3-small').recipe, 'text-embedding-3-small'));
t('dims voyage default', () => embeddingDimsForModel(resolveRecipe('voyage:voyage-4').recipe, 'voyage-4'));
t('truncate 8000', () => truncateEmbedInputs(['a'.repeat(9000), null, undefined]).map(s => s.length));
t('plan voyage (1 char/token, 0.5 safety => 60000 token budget)', () => planEmbedRequests(['x'.repeat(8000), ...Array(10).fill('y'.repeat(8000))], resolveRecipe('voyage:voyage-4').recipe, 0.5).map(b => b.length));
t('plan openai (100K*0.8 tokens, 4 chars/token)', () => planEmbedRequests(Array(100).fill('z'.repeat(8000)), resolveRecipe('openai:text-embedding-3-small').recipe, 0.8).map(b => b.length));
t('plan ollama (no_batch_cap => 16 items)', () => planEmbedRequests(Array(40).fill('q'), resolveRecipe('ollama:bge-m3').recipe, 0.8).map(b => b.length));
t('screen empty/zero', () => screenEmbeddings(['a', ' ', 'c'], [0, 2], [new Float32Array([1, 0]), new Float32Array([0, 0])], 'demo:m'));
t('fallback chain normalize', () => cf.importError ?? normalizeChatFallbackChain(' openai:gpt-5.2 , ,anthropic:claude-sonnet-4-6 '));
t('fallback attempts dedupe', () => cf.importError ?? chatFallbackAttempts('anthropic:a', ['openai:b', 'anthropic:a', 'google:c']));
t('import reservation-cost', () => rc.importError ?? 'ok');
if (!rc.importError) {
  t('cost chat anthropic:claude-sonnet-4-6 (1M in, 0 out)', () => rc.usageCostUsd('anthropic:claude-sonnet-4-6', 1_000_000, 0, 'chat'));
  t('cost chat alias anthropic:claude-haiku-4-5 (1M in)', () => rc.usageCostUsd('anthropic:claude-haiku-4-5', 1_000_000, 0, 'chat'));
  t('cost embed voyage:voyage-4 (1M in)', () => rc.usageCostUsd('voyage:voyage-4', 1_000_000, 0, 'embed'));
  t('cost embed ollama:bge-m3 (free local)', () => rc.usageCostUsd('ollama:bge-m3', 1_000_000, 0, 'embed'));
  t('cost embed litellm:x (unpriced => null)', () => rc.usageCostUsd('litellm:x', 1_000_000, 0, 'embed'));
  t('cost chat ollama:llama3 (free local)', () => rc.usageCostUsd('ollama:llama3', 1_000_000, 1_000_000, 'chat'));
  t('cost chat litellm:gpt-4o (unpriced => null)', () => rc.usageCostUsd('litellm:gpt-4o', 1, 1, 'chat'));
  t('cost with override', () => rc.usageCostUsd('litellm:gpt-4o', 1_000_000, 1_000_000, 'chat', { 'litellm:gpt-4o': { input: 2.5, output: 10 } }));
  t('wildcard allowed for per-token provider?', () => rc.isAllowedPricingOverrideKey('openai:*'));
  t('wildcard allowed for claude-cli?', () => rc.isAllowedPricingOverrideKey('claude-cli:*'));
}
console.log(JSON.stringify(out, null, 1));
