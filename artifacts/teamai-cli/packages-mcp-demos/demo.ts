import { packageSetHash, resolvePlaceholders, renderClaude, entryHash } from './copied.ts';

const h = (x: unknown) => String(x).slice(0, 12);

console.log('== A. packages: declarationHash는 선언 텍스트의 해시일 뿐 ==');
const base = { claude: { marketplaces: [{ name: 'm', repo: 'acme/m' }], plugins: [{ name: 'p@m' }] } };
const reordered = { claude: { plugins: [{ name: 'p@m' }], marketplaces: [{ repo: 'acme/m', name: 'm' }] } };
const pinned = { claude: { marketplaces: [{ name: 'm', repo: 'acme/m' }], plugins: [{ name: 'p@m', version: '1.2.0' }] } };
const pinned2 = { claude: { marketplaces: [{ name: 'm', repo: 'acme/m' }], plugins: [{ name: 'p@m', version: '1.3.0' }] } };
console.log('base            ', h(packageSetHash(base)));
console.log('key order 바꿈   ', h(packageSetHash(reordered)), '(같음이어야 함)');
console.log('version 1.2.0   ', h(packageSetHash(pinned)));
console.log('version 1.3.0   ', h(packageSetHash(pinned2)));
console.log('base == reordered :', packageSetHash(base) === packageSetHash(reordered));
console.log('base == pinned    :', packageSetHash(base) === packageSetHash(pinned));
console.log('(업스트림이 p@m 새 버전을 냈다는 정보는 입력에 없다 -> 해시가 변할 수 없음)');

console.log('\n== B. mcp: ${VAR}를 평문으로 풀고 entryHash를 만든다 ==');
const def = { name: 'gh', transport: 'http', url: 'https://example.com/mcp', headers: { Authorization: 'Bearer ${GH_TOKEN}' } };
const { def: resolved, missing } = resolvePlaceholders(def, { GH_TOKEN: 'ghp_SECRET1234567890' });
const entry = renderClaude(resolved);
console.log('missing        :', JSON.stringify(missing));
console.log('rendered entry :', JSON.stringify(entry));
console.log('entryHash      :', entryHash(entry), '(sha1 앞 16자리)');
console.log('값이 바뀌면(토큰 교체) entryHash도 바뀜:',
  entryHash(renderClaude(resolvePlaceholders(def, { GH_TOKEN: 'ghp_OTHER1234567890' }).def)));
console.log('변수 없으면 missing:', JSON.stringify(resolvePlaceholders(def, {}).missing));

console.log('\n== C. mcp: stdio 서버의 버전은 args 문자열일 뿐 ==');
const s1 = { name: 'f', transport: 'stdio', command: 'npx', args: ['-y', '@acme/formatter-mcp'] };
const s2 = { ...s1, args: ['-y', '@acme/formatter-mcp@1.4.0'] };
console.log('고정 없음 hash :', entryHash(renderClaude(s1)));
console.log('@1.4.0 hash   :', entryHash(renderClaude(s2)));
console.log('(args에 쓴 문자열이 바뀌어야 해시가 변함. npm 쪽 최신 버전이 바뀌어도 해시는 같음)');
