// gbrain@63f62b2 엔티티 이름 해소 체인 demo (memory-verbs 스펙 R-12, R-50~R-59의 근거). 네트워크·DB 없음.
// 실행: deno run --no-remote --allow-read --allow-write=<scratch> --allow-env demo-entity-resolution.mts <scratch-dir>
// 실제 소스를 import 한 것: entities/resolve.ts(resolveEntitySlug, resolveEntitySlugWithSource, resolveStrictEntityReference,
//   entityReferenceCandidates, findPrefixCandidates, followRetirement, slugify, looksLikeSlug, sameEntityName, hasNameSignal,
//   isIdentityEntity, isFactEntityPage, retiredPageSql, BASENAME_DIRS), entities/name-variants.ts, entities/exact-match-preference.ts,
//   search/alias-normalize.ts, verbs/entity-variants.ts(resolveNameVariant, isTitleStub).
// 줄 범위를 잘라 실행한 것: entities/resolve.ts 281-288(aliasSpellings), 340-351(isBareName); mentions/siblings.ts 22-60(siblingVerdict),
//   mentions/aliases.ts 294-297(titleName), mentions/policy.ts 25-26, 100-119(linkableTypesFor, canonicalTypeOf);
//   verbs/entity-card.ts 262-265(ARM_*), 386-394(후보 정렬), 835-845(lastTouchedMs).
// 대체한 것(중요):
//  - 엔진은 SQL 문자열의 모양으로 분기하는 인메모리 가짜(FakeEngine)다. 실제 SQL을 실행한 것이 아니다. 그래서 SQL 술어 자체
//    (예: `ILIKE`, `LIKE ANY`, 연결 수 서브쿼리, 소스·비공개 필터)는 검증하지 않았고, 가짜가 그 의미를 JS로 흉내 낸 결과만 본다.
//  - pg_trgm 유사도(`%`, `similarity`)는 흉내 내지 않고 42883 오류로 대체했다(트라이그램 없는 브레인과 같은 경로). 따라서
//    퍼지 팔·same_name 팔·근접 후보의 점수는 실행하지 못했다.
//  - 동명 후보가 둘 이상일 때 부르는 siblingCanonical은 zod 의존으로 import할 수 없어 같은 판정 함수 siblingVerdict만 잘라 돌렸다.
//  - 가짜 페이지·별칭은 형식을 보이려는 예시다.
const SRC = '/Users/kkh/Desktop/oss-analysis/agent-memory/repos/gbrain/src/core/';
const scratch = Deno.args[0];
const lines = (f: string) => Deno.readTextFileSync(SRC + f).split('\n');
const slice = (f: string, a: number, b: number) => lines(f).slice(a - 1, b).join('\n');
const out: Record<string, unknown> = {};
const t = async (name: string, fn: () => unknown) => { try { out[name] = await fn(); } catch (e: any) { out[name] = `THROWS ${e.name}: ${e.message}`; } };
const RS: any = await import(SRC + 'entities/resolve.ts');
const NV: any = await import(SRC + 'entities/name-variants.ts');
const EV: any = await import(SRC + 'verbs/entity-variants.ts');
const XP: any = await import(SRC + 'entities/exact-match-preference.ts');
const AN: any = await import(SRC + 'search/alias-normalize.ts');

// ---- A. 순수 함수 ----
await t('slugify / looksLikeSlug', () => ({
  slugify: ['Alice Example', 'Đăng Example', 'Café  Notes!', '  --A__b--  ', '한글 메모'].map((s: string) => [s, RS.slugify(s)]),
  looksLikeSlug: ['people/alice-example', 'People/Alice', 'alice example', '한글/메모', 'a.b'].map((s: string) => [s, RS.looksLikeSlug(s)]),
}));
await t('sameEntityName (같은 이름 토큰: 순서·대소문자·악센트·회사 접미 무시)', () => ({
  reordered: RS.sameEntityName('Example, Alice', 'Alice Example', 'people/alice-example'),
  acme_inc: RS.sameEntityName('Acme Inc', 'Acme', 'companies/acme'),
  alicia: RS.sameEntityName('Alicia Example', 'Alice Example', 'people/alice-example'),
  examples: RS.sameEntityName('Alice Examples', 'Alice Example', 'people/alice-example'),
  by_slug_basename: RS.sameEntityName('alice example', null, 'people/alice-example'),
}));
await t('isIdentityEntity / isFactEntityPage', () => ({
  identity: [['people/x', null], ['x', 'company'], ['meetings/x', 'meeting'], ['orgs/x', null]].map(([s, ty]: any) => [s, ty, RS.isIdentityEntity(s, ty)]),
  fact_entity: [['projects/x', null], ['x', 'concept'], ['x', 'deal'], ['meetings/x', 'meeting'], ['hosts/hive', 'host']].map(([s, ty]: any) => [s, ty, RS.isFactEntityPage(s, ty)]),
  BASENAME_DIRS: RS.BASENAME_DIRS,
}));
await t('hasNameSignal (퍼지 phantom 게이트: ≥6자 또는 2토큰 + 엔트로피 ≥1.5)', () => ['ai', 'aaaa', 'aaaaaa', 'alice', 'alexander', 'ab cd', 'hive'].map((s: string) => [s, RS.hasNameSignal(s)]));
await t('normalizeAlias', () => ['  Alice   Example ', '"Alice"', '[Allie]', 'ＡＬＩＣＥ', '   '].map((s: string) => [s, AN.normalizeAlias(s)]));
Deno.writeTextFileSync(scratch + '/resolve-slice.mts', `import { normalizeAlias } from '${SRC}search/alias-normalize.ts';\nimport { looksLikeSlug, slugify } from '${SRC}entities/resolve.ts';\n`
  + slice('entities/resolve.ts', 281, 288) + '\n' + slice('entities/resolve.ts', 340, 351) + '\nexport { aliasSpellings, isBareName };\n');
const RSL: any = await import(scratch + '/resolve-slice.mts');
await t('aliasSpellings (구분자 접기)', () => ['Alice Example', 'alice_example', 'people/alice-example', 'Saoirse'].map((s: string) => [s, RSL.aliasSpellings(s)]));
await t('isBareName', () => ['Alice', 'Alice Example', 'alice-example', 'people/alice', '!!!', '  Hive '].map((s: string) => [s, RSL.isBareName(s)]));
await t('exactMatchPreference', () => {
  const types = new Set(['person', 'company']);
  return [['people/alice-example', 'person', ['people/alice-example']], ['meetings/alice-sync', 'meeting', ['alice']], ['x/alice', 'person', ['alice']], ['x/alice', 'person', ['x/alice']]]
    .map(([slug, type, exact]: any) => [slug, type, XP.exactMatchPreference({ slug, type }, exact, types)]);
});

// ---- B. 이름 변형 매처(순수) ----
await t('name-variants: matchNameVariant 행렬', () => ([
  ['Alice Example', 'Alice Example'], ['Dr. Alice Example', 'Alice Example'], ['Example, Alice', 'Alice Example'], ['Example Alice', 'Alice Example'],
  ['Allie Example', 'Alice Example'], ['Bob Example', 'Robert Example'], ['A. Example', 'Alice Example'], ['Alice Exampel', 'Alice Example'],
  ['Example', 'Alice Example'], ['Exa', 'Alice Example'], ['Jon Example', 'Joe Example'], ['Alic Example', 'Alice Example'],
  ['Alice Example', 'Alice'], ['Mayor Example', 'Alice Example'], ['Alice Example Jr', 'Alice Example'],
] as Array<[string, string]>).map(([q, c]) => [q, c, NV.matchNameVariant(q, c)]));
await t('name-variants: parsePersonName / probeWords / editDistance / isTitleStub / 상수', () => ({
  parse: ['Dr. Alice Example', 'Mayor Example', 'Alice Smith-Jones III', 'people/dr-alice-example', 'CEO'].map((s: string) => [s, NV.parsePersonName(s)]),
  probe: [NV.probeWords('A. Example'), NV.probeWords('Dr. Alice Example')],
  edit: [NV.editDistance('example', 'exampel'), NV.editDistance('example', 'exmpl'), NV.editDistance('abc', 'abd')],
  stub: ['Mayor Example', 'Dr. Alice Example', 'Alice'].map((s: string) => [s, EV.isTitleStub(s)]),
  rank: NV.NAME_MATCH_RANK, weak: [...NV.WEAK_NAME_MATCHES], candidate_cap: EV.VARIANT_CANDIDATE_CAP,
}));

// ---- C. 인메모리 가짜 엔진 위에서 실제 해소 체인 ----
interface P { source_id: string; slug: string; title: string; type: string | null; frontmatter: Record<string, unknown>; conn: number }
const pg = (slug: string, title: string, type: string | null, conn = 0, fm: Record<string, unknown> = {}, source_id = 'default'): P => ({ source_id, slug, title, type, frontmatter: fm, conn });
const PAGES: P[] = [
  pg('people/alice-example', 'Alice Example', 'person', 10), pg('people/alice-smith', 'Alice Smith', 'person', 3),
  pg('people/bob-example', 'Bob Example', 'person', 5), pg('people/old-bob', 'Old Bob', 'person', 1, { superseded_by: '[[people/bob-example|Bob]]' }),
  pg('people/saoirse-x', 'Saoirse X', 'person', 2), pg('companies/acme-example', 'Acme Example', 'company', 4), pg('companies/acme-labs-50', 'Acme Labs', 'company', 2),
  pg('companies/acme-0', 'Acme', 'company', 1), pg('orgs/widget-co', 'Widget Co', 'organization', 1), pg('hosts/hive', 'Hive', 'host', 1),
  pg('meetings/2026-10-01-alice', 'Alice Example sync', 'meeting', 1), pg('concepts/zebra-telescope', 'Zebra Telescope', 'concept', 1),
  pg('people/mayor-example', 'Mayor Example', 'person', 1), pg('people/jordan-lee', 'Jordan Lee', 'person', 2), pg('companies/jordan-lee', 'Jordan Lee', 'company', 1),
];
const ALIASES: Array<{ alias_norm: string; slug: string; source_id: string }> = [
  { alias_norm: 'saoirse', slug: 'people/saoirse-x', source_id: 'default' }, { alias_norm: 'allie e', slug: 'people/alice-example', source_id: 'default' },
  { alias_norm: 'widget company', slug: 'orgs/widget-co', source_id: 'default' }, { alias_norm: 'stale', slug: 'people/deleted-page', source_id: 'default' },
];
const isRetired = (p: P) => ['false', 'no'].includes(String(p.frontmatter.canonical ?? '').toLowerCase()) || String(p.frontmatter.superseded_by ?? '').trim() !== ''
  || String(p.frontmatter.merged_into ?? '').trim() !== '' || /(^|[^a-z])(alias|redirect|redirected)([^a-z]|$)/.test(String(p.frontmatter.status ?? '').toLowerCase());
const likeRe = (pat: string) => new RegExp('^' + pat.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/%/g, '.*').replace(/_/g, '.') + '$', 'i');
const calls: string[] = [];
const fake: any = {
  kind: 'fake',
  async getConfig() { return null; },
  async resolveAliases(norms: string[], opts: any) {
    const m = new Map<string, Array<{ slug: string; source_id: string }>>();
    for (const n of norms) for (const a of ALIASES) if (a.alias_norm === n && a.source_id === opts.sourceId && PAGES.some(p => p.slug === a.slug)) m.set(n, [...(m.get(n) ?? []), { slug: a.slug, source_id: a.source_id }]);
    return m;
  },
  async executeRaw(sql: string, params: any[]) {
    const src = params[0];
    const live = (slug: string) => PAGES.find(p => p.source_id === src && p.slug === slug);
    if (sql.includes('AS retired') && sql.includes('p.slug = $2')) {
      const p = live(params[1]); if (!p) return [];
      const target = String(p.frontmatter.superseded_by ?? '').trim() || String(p.frontmatter.merged_into ?? '').trim() || null;
      return [{ slug: p.slug, type: p.type, retired: isRetired(p), target }];
    }
    if (sql.startsWith('SELECT slug FROM pages WHERE source_id = $1 AND slug = $2')) { // tryExactSlug
      const p = live(params[1]); const wantLive = /AND\s+NOT\s+\(lower/.test(sql);
      return p && (isRetired(p) !== wantLive) ? [{ slug: p.slug }] : [];
    }
    if (/^SELECT slug FROM pages\s+WHERE source_id = \$1 AND deleted_at IS NULL AND slug = ANY\(\$2::text\[\]\)/.test(sql)) { // basename / org variants
      const rows = (params[1] as string[]).flatMap(s => { const p = live(s); return p ? [{ slug: p.slug }] : []; });
      return /LIMIT 2/.test(sql) ? rows.slice(0, 2) : rows;
    }
    if (sql.includes('SELECT p.slug, p.type FROM pages p')) return (params[1] as string[]).flatMap(s => { const p = live(s); return p ? [{ slug: p.slug, type: p.type }] : []; });
    if (sql.includes('connection_count') && sql.includes('LIKE ANY')) {
      const res = (params[1] as string[]).map(likeRe);
      return PAGES.filter(p => p.source_id === src && !isRetired(p) && res.some(r => r.test(p.slug))).sort((a, b) => b.conn - a.conn || (a.slug < b.slug ? -1 : 1)).slice(0, 10).map(p => ({ slug: p.slug, connection_count: p.conn }));
    }
    if (sql.includes('DISTINCT split_part')) {
      const res = (params[1] as string[]).map(likeRe);
      return [...new Set(PAGES.filter(p => p.source_id === src && !isRetired(p) && res.some(r => r.test(p.slug))).map(p => p.slug.split('/')[0]))].slice(0, 2).map(dir => ({ dir }));
    }
    if (sql.includes('lower(title) = lower($3)')) {
      const res = (params[1] as string[]).map(likeRe);
      return PAGES.filter(p => p.source_id === src && !isRetired(p) && res.some(r => r.test(p.slug)) && p.title.toLowerCase() === String(params[2]).toLowerCase()).slice(0, 3).map(p => ({ slug: p.slug, title: p.title }));
    }
    if (sql.includes('ORDER BY p.slug LIMIT 5')) return (params[1] as string[]).flatMap(s => { const p = live(s); return p && !isRetired(p) ? [{ slug: p.slug }] : []; }).sort().slice(0, 5);
    if (sql.includes('probe_hits')) { // resolveNameVariant 후보 읽기
      const types: string[] = params[1]; const slugLikes = (params[2] as string[]).map(likeRe); const words = (params[3] as string[]).map(likeRe);
      return PAGES.filter(p => p.source_id === src && (types.includes(p.type ?? '') || slugLikes.some(r => r.test(p.slug))) && words.some(r => r.test(p.title) || r.test(p.slug)))
        .map(p => ({ ...p, probe_hits: words.filter(r => r.test(p.title) || r.test(p.slug)).length })).sort((a, b) => b.probe_hits - a.probe_hits || a.title.length - b.title.length || (a.slug < b.slug ? -1 : 1));
    }
    if (sql.includes('similarity(') || sql.includes('% $2') || sql.includes('lower(title) %')) { const e: any = new Error('function similarity does not exist'); e.code = '42883'; throw e; }
    calls.push(sql.slice(0, 80)); throw new Error('FakeEngine: unhandled SQL ' + sql.slice(0, 80));
  },
};
const sw = (r: any) => r === null ? null : `${r.slug} [${r.source}]`;
const safe = async (fn: () => Promise<unknown>) => { try { return await fn(); } catch (e: any) { return `THROWS ${String(e.message).split('\n')[0].slice(0, 90)}`; } };
const cases = ['people/alice-example', 'people/old-bob', 'Alice Example', 'alice example', 'saoirse', 'Saoirse', 'Allie E', 'Alice', 'Acme', 'hive', 'Zebra', 'companies/widget-co', 'widget company', 'stale', 'Nobody Person', 'People/Alice-Example', '', '   ', '!!!', 'Zebra Telescope', 'concepts/zebra-telescope', 'alice-example', '한글 메모', 'Мария', "O'Brien", 'Đức Example', 'Jordan Lee'];
await t('resolveEntitySlugWithSource (가짜 엔진, 퍼지 불가)', async () => Object.fromEntries(await Promise.all(cases.map(async c => [JSON.stringify(c), await safe(async () => sw(await RS.resolveEntitySlugWithSource(fake, 'default', c)))]))));
await t('resolveEntitySlug (slug만) = WithSource의 slug와 같은가', async () => {
  const diffs: string[] = [];
  for (const c of cases) { const a = await safe(() => RS.resolveEntitySlug(fake, 'default', c)); const b: any = await safe(() => RS.resolveEntitySlugWithSource(fake, 'default', c)); if (a !== (b?.slug ?? (typeof b === 'string' ? b : null))) diffs.push(`${JSON.stringify(c)}: slug-only=${JSON.stringify(a)} with-source=${JSON.stringify(typeof b === 'string' ? b : b?.slug)}`); }
  return { differences: diffs };
});
const strictCases = ['people/alice-example', 'people/old-bob', 'Alice Example', 'saoirse', 'Allie E', 'Alice', 'Acme', 'Nobody Person', 'companies/widget-co', 'Zebra Telescope', 'concepts/zebra-telescope', 'hive', '   '];
await t('resolveStrictEntityReference (sameName:true, 가짜 엔진; same_name 팔은 트라이그램 불가로 건너뜀)', async () =>
  Object.fromEntries(await Promise.all(strictCases.map(async c => [JSON.stringify(c), await RS.resolveStrictEntityReference(fake, 'default', c, { sameName: true })]))));
await t('resolveStrictEntityReference: 사실 엔티티가 아닌 페이지(회의)는 소스 팩 조회(mentions/policy.ts)가 필요 — zod 의존으로 import 불가라 실행하지 못함', async () =>
  RS.resolveStrictEntityReference(fake, 'default', 'meetings/2026-10-01-alice', { sameName: true }));
await t('entityReferenceCandidates (최대 5, slug 순)', async () => Object.fromEntries(await Promise.all(['Alice', 'Alice Example', 'Acme', 'Nobody Person', 'saoirse'].map(async c => [c, await RS.entityReferenceCandidates(fake, 'default', c)]))));
await t('findPrefixCandidates (연결 수 내림차순, slug 오름차순)', () => RS.findPrefixCandidates(fake, 'default', 'alice'));
await t('followRetirement', async () => ({ live: await RS.followRetirement(fake, 'default', 'people/bob-example'), retired: await RS.followRetirement(fake, 'default', 'people/old-bob'), missing: await RS.followRetirement(fake, 'default', 'people/none') }));
await t('retiredPageSql 문자열 (SQL은 실행 안 함)', () => RS.retiredPageSql('p'));

// ---- D. 이름 변형 팔 (resolveNameVariant, 가짜 엔진) ----
const variantOpts = { selectColumns: '*', privatePredicate: '', retirementPrivacy: '', entityTypes: new Set(['person', 'company', 'organization']) };
const vn = async (name: string) => { const r = await EV.resolveNameVariant(fake, 'default', name, variantOpts); return { hit: r.hit ? `${r.hit.row.slug} (${r.hit.kind})` : null, matches: r.matches.map((m: any) => `${m.row.slug} (${m.kind})`) }; };
await t('resolveNameVariant', async () => Object.fromEntries(await Promise.all(['Allie Example', 'Dr. Alice Example', 'Example', 'Alice Exampel', 'Robert Example', 'A. Example', 'Bob Examplx', 'a/b', 'one two three four five six'].map(async n => [n, await vn(n)]))));

// ---- E. 형제(sibling) 판정과 후보 정렬 (잘라냄) ----
Deno.writeTextFileSync(scratch + '/sibling-slice.mts', `import { normalizeAlias } from '${SRC}search/alias-normalize.ts';\ntype PackTypes = any; type MentionPolicy = any; type BrainEngine = any;\n`
  + slice('mentions/policy.ts', 25, 26) + '\n' + slice('mentions/policy.ts', 100, 119) + '\n' + slice('mentions/aliases.ts', 294, 297) + '\n'
  + slice('mentions/siblings.ts', 22, 60).replace(/^import .*$/gm, '') + '\n');
const SB: any = await import(scratch + '/sibling-slice.mts');
const pol = { siblingMerge: true, excludeSlugs: [] as string[] };
await t('siblingVerdict (정체 형제 판정; siblingCanonical은 group일 때만 가장 작은 slug)', () => {
  const co = (title: string, slug = title, type = 'company', identity?: string) => ({ slug, title, type, identity });
  return {
    group: SB.siblingVerdict([co('Account sheet: Widget Co', 'a'), co('CRM record: Widget Co', 'b')], null, pol),
    person: SB.siblingVerdict([co('Account sheet: A', 'a', 'person'), co('CRM record: A', 'b', 'person')], null, pol),
    type_mismatch: SB.siblingVerdict([co('Account sheet: W', 'a', 'company'), co('CRM record: W', 'b', 'organization')], null, pol),
    same_prefix: SB.siblingVerdict([co('CRM record: W', 'a'), co('CRM record: W', 'b')], null, pol),
    subject_mismatch: SB.siblingVerdict([co('Account sheet: W1', 'a'), co('CRM record: W2', 'b')], null, pol),
    separate: SB.siblingVerdict([co('Account sheet: W', 'a', 'company', 'separate'), co('CRM record: W', 'b')], null, pol),
    excluded: SB.siblingVerdict([co('Account sheet: W', 'a'), co('CRM record: W', 'b')], null, { siblingMerge: true, excludeSlugs: ['b'] }),
    disabled: SB.siblingVerdict([co('Account sheet: W', 'a'), co('CRM record: W', 'b')], null, { siblingMerge: false, excludeSlugs: [] }),
    capped: SB.siblingVerdict([co('P1: W', 'a'), co('P2: W', 'b'), co('P3: W', 'c'), co('P4: W', 'd')], null, pol),
    linkable_default: SB.linkableTypesFor(null, { typeAdds: [], typeRemoves: [] }),
    linkable_adds_removes: SB.linkableTypesFor(null, { typeAdds: ['deal'], typeRemoves: ['entity', 'organization'] }),
  };
});
Deno.writeTextFileSync(scratch + '/rank-slice.mts', `import { exactMatchPreference } from '${SRC}entities/exact-match-preference.ts';\ntype CardPageRow = any;\n`
  + slice('verbs/entity-card.ts', 262, 265) + '\n' + slice('verbs/entity-card.ts', 835, 845) + '\n'
  + `export function rank(rankBySlug: Map<string, number>, rowBySlug: Map<string, any>, exactSlugs: string[], entityTypes: Set<string>) {\n`
  + slice('verbs/entity-card.ts', 386, 394) + `\n  return candidates.map(c => c.slug);\n}\nexport { ARM_ALIAS, ARM_EXACT, ARM_SUFFIX };\n`);
const RK: any = await import(scratch + '/rank-slice.mts');
await t('entity 카드 후보 정렬(arm 순위 → 정확 일치 선호 → 최근 접촉)', () => {
  const row = (slug: string, type: string, updated: string, retrieved: string | null = null) => ({ slug, type, updated_at: updated, last_retrieved_at: retrieved });
  const rows = new Map<string, any>([
    ['people/alice-example', row('people/alice-example', 'person', '2026-01-01')], ['meetings/alice-sync', row('meetings/alice-sync', 'meeting', '2026-10-01')],
    ['companies/alice', row('companies/alice', 'company', '2026-02-01')], ['people/alice-old', row('people/alice-old', 'person', '2025-01-01', '2026-10-10')],
  ]);
  const types = new Set(['person', 'company']);
  return {
    consts: [RK.ARM_ALIAS, RK.ARM_EXACT, RK.ARM_SUFFIX],
    alias_beats_exact: RK.rank(new Map([['meetings/alice-sync', RK.ARM_EXACT], ['people/alice-example', RK.ARM_ALIAS]]), rows, ['alice'], types),
    exact_title_collision_prefers_entity_type: RK.rank(new Map([['meetings/alice-sync', RK.ARM_EXACT], ['companies/alice', RK.ARM_EXACT]]), rows, ['alice'], types),
    explicit_slug_stays_first: RK.rank(new Map([['companies/alice', RK.ARM_EXACT], ['people/alice-example', RK.ARM_EXACT]]), rows, ['people/alice-example'], types),
    recency_final_tiebreak_uses_max_of_updated_and_retrieved: RK.rank(new Map([['people/alice-example', RK.ARM_SUFFIX], ['people/alice-old', RK.ARM_SUFFIX]]), rows, ['alice'], types),
  };
});

await Deno.writeTextFile(scratch + '/out-entity.json', JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
