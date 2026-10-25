// gbrain@63f62b2 page-storage-and-import demo. 순수 함수만, 네트워크·DB 없음.
// 실행: deno run --no-remote --allow-read --allow-write=<scratch> --allow-env demo-pure.mts <scratch-dir>
// 실제 소스는 import 하거나(recursive.ts, utils.ts, preconditions.ts) 줄 범위를 잘라 임시 모듈로 만들어 돌린다.
// 대체한 것: markdown.ts는 js-yaml(npm) 때문에 import 불가 -> splitBody 구간(846-1008)만 잘라 실행.
//            capture-content.ts는 data-frontmatter(npm) 때문에 -> defaultSlug 등 순수 구간만 잘라 실행하고
//            computeContentHash(Bun.CryptoHasher)만 node:crypto sha256 hex로 대체(같은 SHA-256 hex).
//            token-estimate.ts는 @dqbd/tiktoken이 없어 len/4 폴백으로 동작(실제 설치에서는 cl100k 계산).
const R = '/Users/kkh/Desktop/oss-analysis/agent-memory/repos/gbrain/src/core/';
const scratch = Deno.args[0];
const lines = (f: string) => Deno.readTextFileSync(R + f).split('\n');
const slice = (f: string, a: number, b: number) => lines(f).slice(a - 1, b).join('\n');
const out: Record<string, unknown> = {};
const t = async (name: string, fn: () => unknown) => { try { out[name] = await fn(); } catch (e: any) { out[name] = `THROWS ${e.name}: ${e.message}`; } };

// ---- A. splitBody (markdown.ts:846-1008 + FENCE_TOGGLE_RE:1250) ----
const mdSrc = `import { findLineOutsideFencedCode } from '${R}fence-scan.ts';\n`
  + slice('markdown.ts', 1250, 1250) + '\n' + slice('markdown.ts', 846, 1008)
  .replace(/^export function /gm, 'export function ');
Deno.writeTextFileSync(scratch + '/split-body.mts', mdSrc);
const { splitBody } = await import(scratch + '/split-body.mts');
const sb = (s: string) => { const r = splitBody(s); return { truth: r.compiled_truth, timeline: r.timeline }; };
await t('split: <!-- timeline --> marker', () => sb('Alice is a founder.\n\n<!-- timeline -->\n\n- 2024-01-02: met'));
await t('split: --- timeline --- decorated', () => sb('Body\n--- timeline ---\n- 2024: x'));
await t('split: bare --- then ## Timeline', () => sb('Body\n\n---\n\n## Timeline\n- 2024-05-01: a'));
await t('split: bare --- horizontal rule only (NO split)', () => sb('Part one\n\n---\n\nPart two'));
await t('split: bare --- then ## History prose (split by rule 3, heading kept as separator? see timeline text)', () => sb('Body\n---\n## History\nProse about history.'));
await t('split: no sentinel, bare ## Timeline of dated bullets (rule 4: heading kept in timeline)', () => sb('Body text\n\n## Timeline\n- 2024-05-01: a\n- 2023: b\n\n## Other\nkept in truth'));
await t('split: no sentinel, ## History prose (NO split)', () => sb('Body\n\n## History\nWe started in a garage.\n'));
await t('split: marker inside code fence (ignored)', () => sb('Intro\n```\n<!-- timeline -->\n```\nmore'));
await t('split: ## Timeline as first content (NO split)', () => sb('## Timeline\n- 2024-05-01: a'));

// ---- B. chunkText (real chunkers/recursive.ts) ----
const rec: any = await import(R + 'chunkers/recursive.ts');
const words = (n: number, w = 'word') => Array.from({ length: n }, (_, i) => `${w}${i}`).join(' ');
const para = (n: number, per = 40) => Array.from({ length: Math.ceil(n / per) }, (_, p) => words(per, `p${p}w`)).join('\n\n');
const shape = (cs: any[]) => cs.map(c => ({ i: c.index, words: c.text.split(/\s+/).filter(Boolean).length, chars: c.text.length, startsWith: c.text.slice(0, 14) }));
await t('chunk: 250 words -> 1 chunk', () => shape(rec.chunkText(words(250))));
await t('chunk: 301 words one paragraph', () => shape(rec.chunkText(words(301))));
await t('chunk: 900 words in 40-word paragraphs (target 300, limit 450, overlap 50)', () => shape(rec.chunkText(para(900))));
await t('chunk: 7000-char whitespace-less string (maxChars 6000 sliding window)', () => shape(rec.chunkText('a'.repeat(7000))));
await t('chunk: empty / whitespace', () => [rec.chunkText(''), rec.chunkText('  \n ')]);
await t('chunk: takes fence removed before chunking (facts fence not exercised here)', () => {
  const body = 'Intro line.\n\n<!--- gbrain:takes:begin -->\n| # | claim |\n|---|---|\n| 1 | secret take |\n<!--- gbrain:takes:end -->\n\nOutro line.';
  return rec.chunkText(body).map((c: any) => c.text);
});
await t('constants', () => ({ MARKDOWN_CHUNKER_VERSION: rec.MARKDOWN_CHUNKER_VERSION }));

// ---- C. contentHash (real utils.ts) ----
const u: any = await import(R + 'utils.ts');
const base = { title: 'T', type: 'note', compiled_truth: 'x', timeline: '', frontmatter: { a: 1 }, tags: ['b', 'a'] };
await t('hash: baseline', () => u.contentHash(base));
await t('hash: same + captured_at/ingested_at/trust_tier (ephemeral keys ignored)', () => u.contentHash({ ...base, frontmatter: { a: 1, captured_at: 'now', ingested_at: 'x', trust_tier: 'agent' } }) === u.contentHash(base));
await t('hash: tags order irrelevant', () => u.contentHash({ ...base, tags: ['a', 'b'] }) === u.contentHash(base));
await t('hash: other frontmatter key changes it', () => u.contentHash({ ...base, frontmatter: { a: 1, b: 2 } }) === u.contentHash(base));
await t('hash: timeline undefined == ""', () => u.contentHash({ ...base, timeline: undefined }) === u.contentHash(base));
await t('HASH_EPHEMERAL_FRONTMATTER_KEYS', () => u.HASH_EPHEMERAL_FRONTMATTER_KEYS);

// ---- D. request_id mapping (real persistence/preconditions.ts) ----
const pc: any = await import(R + 'persistence/preconditions.ts').catch((e: Error) => ({ importError: e.message.split('\n')[0] }));
await t('request_id: import', () => pc.importError ?? 'ok');
if (!pc.importError) {
  await t('request_id: UUID passes through lowercased', () => pc.parseWriteRequestId('3F6A2C1E-9B47-4D2A-8E5F-7C0B1D9A6E24'));
  await t('request_id: non-UUID -> deterministic UUIDv5 (twice same)', () => [pc.parseWriteRequestId('remember-acme-1'), pc.parseWriteRequestId('remember-acme-1')]);
  await t('request_id: space -> invalid_params', () => pc.parseWriteRequestId('has space'));
  await t('request_id: 129 chars -> invalid_params', () => pc.parseWriteRequestId('a'.repeat(129)));
  await t('precondition: expected_revision + force', () => pc.parseMutationPrecondition({ expected_revision: '3f6a2c1e-9b47-4d2a-8e5f-7c0b1d9a6e24', force: true }));
  await t('precondition: expected_revision not UUID', () => pc.parseMutationPrecondition({ expected_revision: 'abc' }));
  await t('precondition: none', () => pc.parseMutationPrecondition({}));
}
// page-state/types.ts assertPageRevision / PageRevisionConflictError code
const ps: any = await import(R + 'page-state/types.ts').catch((e: Error) => ({ importError: e.message.split('\n')[0] }));
await t('revision: import', () => ps.importError ?? 'ok');
if (!ps.importError) {
  const rev = '3f6a2c1e-9b47-4d2a-8e5f-7c0b1d9a6e24', other = '00000000-0000-4000-8000-000000000000';
  const code = (snap: any, pre: any) => { try { ps.assertPageRevision(snap, pre); return 'ok'; } catch (e: any) { return e.code ?? e.message; } };
  await t('revision: exists, no expected -> code', () => code({ revision: rev }, {}));
  await t('revision: exists, matching expected', () => code({ revision: rev }, { expectedRevision: rev }));
  await t('revision: exists, stale expected -> code', () => code({ revision: rev }, { expectedRevision: other }));
  await t('revision: absent, no expected (create)', () => code(null, {}));
  await t('revision: absent, expected given -> code', () => code(null, { expectedRevision: rev }));
  await t('revision: exists, force', () => code({ revision: rev }, { force: true }));
}

// ---- E. capture helpers (capture-content.ts 줄 범위 잘라 실행; computeContentHash만 대체) ----
const capSrc = `import { createHash } from 'node:crypto';\nconst computeContentHash = (c: string) => createHash('sha256').update(c).digest('hex');\n`
  + slice('capture-content.ts', 37, 49) + '\n' + slice('capture-content.ts', 162, 165) + '\n' + slice('capture-content.ts', 174, 181);
Deno.writeTextFileSync(scratch + '/capture-helpers.mts', capSrc);
const cap: any = await import(scratch + '/capture-helpers.mts');
await t('capture: defaultSlug note (2026-10-23)', () => cap.defaultSlug(cap.normalizeForHash('  Hello\r\nWorld  '), new Date('2026-10-23T05:00:00Z')));
await t('capture: defaultSlug diary/event prefix', () => [cap.defaultSlug('x', new Date('2026-10-23T05:00:00Z'), 'diary'), cap.defaultSlug('x', new Date('2026-10-23T05:00:00Z'), 'event')]);
await t('capture: normalizeForHash CRLF/BOM/NFKC', () => cap.normalizeForHash('﻿  ＡＢＣ\r\nx  '));
await t('capture: deriveTitle 80 cap + heading strip', () => [cap.deriveTitle('\n\n## Hello world\nbody'), cap.deriveTitle('x'.repeat(100)).length, cap.deriveTitle('---\n---\n')]);

// ---- F. import path -> slug (real sync.ts slugifyPath/hyphenFoldedSlug) ----
const sy: any = await import(R + 'sync.ts');
await t('slugifyPath', () => Object.fromEntries(['People/Alice Example.md', 'notes/v1.0.0.md', '_index.md', 'Daily/2024-03-15 Standup.md', '한글/메모.md', 'Apple Notes/2017-05-03 ohmygreen.md', 'a--b.md', 'Café Notes.mdx'].map(x => [x, sy.slugifyPath(x)])));
await t('hyphenFoldedSlug (put_page refuses a NEW slug this changes)', () => ({ 'notes/x---y': sy.hyphenFoldedSlug('notes/x---y'), 'notes/x-': sy.hyphenFoldedSlug('notes/x-'), 'notes/ok': sy.hyphenFoldedSlug('notes/ok') }));

console.log(JSON.stringify(out, null, 1));
