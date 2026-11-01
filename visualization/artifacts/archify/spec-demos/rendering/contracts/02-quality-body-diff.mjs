// 점검 1 보충: --quality 와 meta.quality_profile 이 루트 속성뿐 아니라 SVG "본문"에도 같은 영향을 주는지.
// (a) architecture·sequence: --quality showcase (meta 없음) vs meta.quality_profile=showcase 의 본문 차이 (루트 <svg ...> 태그는 제외하고 비교)
// (b) 잘못된 값: CLI --quality foo, 렌더러 직접 실행 ARCHIFY_QUALITY_PROFILE=foo
// 사용: node 02-quality-body-diff.mjs  (결과: out/02-body-diff.txt). HTML은 즉시 삭제.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skill = path.join(process.env.HOME, '.claude/skills/archify');
const cli = path.join(skill, 'bin/archify.mjs');
const out = path.join(here, 'out');
const lines = [];
const log = (s) => { lines.push(s); console.log(s); };

function render(type, example, metaPatch, args, env = {}) {
  const doc = JSON.parse(fs.readFileSync(path.join(skill, 'examples', example), 'utf8'));
  for (const [k, v] of Object.entries(metaPatch)) { if (v === null) delete doc.meta[k]; else doc.meta[k] = v; }
  const input = path.join(out, 'b-in.json'); const output = path.join(out, 'b-out.html');
  fs.writeFileSync(input, JSON.stringify(doc));
  fs.rmSync(output, { force: true });
  const r = type.direct
    ? spawnSync('node', [path.join(skill, `renderers/${type.name}/render-${type.name}.mjs`), input, output], { encoding: 'utf8', env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] })
    : spawnSync('node', [cli, 'render', type.name, input, output, ...args], { encoding: 'utf8', env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  const html = fs.existsSync(output) ? fs.readFileSync(output, 'utf8') : null;
  fs.rmSync(output, { force: true }); fs.rmSync(input, { force: true });
  return { status: r.status, stderr: r.stderr, html };
}
const body = (html) => html.match(/<svg\b[\s\S]*?<\/svg>/)[0].replace(/^<svg\b[^>]*>/, '<svg ROOT>');
const rootTag = (html) => html.match(/<svg\b[^>]*>/)[0].replace(/viewBox="[^"]*"/, '').replace(/\s+/g, ' ');

function diffCount(a, b) {
  const A = a.split('\n'), B = b.split('\n'); let n = 0; const ex = [];
  for (let i = 0; i < Math.max(A.length, B.length); i++) if (A[i] !== B[i]) { n++; if (ex.length < 3) ex.push([A[i], B[i]]); }
  return { n, total: Math.max(A.length, B.length), ex };
}

// (a)
for (const [name, example, label] of [['architecture', 'production-deployment.architecture.json', 'boundaries+labels'], ['architecture', 'web-app.architecture.json', 'web-app'], ['sequence', 'cache-miss-request.sequence.json', 'sequence']]) {
  const cli_ = render({ name }, example, { quality_profile: null }, ['--quality', 'showcase']);
  const meta = render({ name }, example, { quality_profile: 'showcase' }, []);
  if (!cli_.html || !meta.html) { log(`${name}/${label}: render failed cli=${cli_.status} meta=${meta.status} ${(cli_.stderr || meta.stderr).split('\n')[0]}`); continue; }
  const d = diffCount(body(cli_.html), body(meta.html));
  log(`${name}/${label}: root(cli-showcase)==root(meta-showcase)? ${rootTag(cli_.html) === rootTag(meta.html)} | body diff lines ${d.n}/${d.total}`);
  d.ex.forEach(([x, y]) => { log(`   cli : ${String(x).trim().slice(0, 150)}`); log(`   meta: ${String(y).trim().slice(0, 150)}`); });
  const conflict = render({ name }, example, { quality_profile: 'showcase' }, ['--quality', 'standard']);
  const metaStd = render({ name }, example, { quality_profile: 'standard' }, []);
  if (conflict.html && metaStd.html) {
    const d2 = diffCount(body(conflict.html), body(metaStd.html));
    log(`   [cli standard + meta showcase] vs [meta standard]: root attr ${rootTag(conflict.html).match(/data-quality-profile="[^"]*"/)} vs ${rootTag(metaStd.html).match(/data-quality-profile="[^"]*"/)} | body diff lines ${d2.n}/${d2.total}`);
  }
}
// (b)
{
  const r = render({ name: 'architecture' }, 'web-app.architecture.json', { quality_profile: null }, ['--quality', 'foo']);
  log(`CLI --quality foo: exit=${r.status} stderr=${r.stderr.split('\n')[0].slice(0, 160)}`);
  const d = render({ name: 'architecture', direct: true }, 'web-app.architecture.json', { quality_profile: null }, [], { ARCHIFY_QUALITY_PROFILE: 'foo' });
  log(`direct renderer ARCHIFY_QUALITY_PROFILE=foo: exit=${d.status} root=${d.html ? rootTag(d.html).match(/data-quality-[a-z]+="[^"]*"/g) : d.stderr.split('\n')[0]}`);
  const e = render({ name: 'architecture', direct: true }, 'web-app.architecture.json', { quality_profile: 'showcase' }, [], { ARCHIFY_QUALITY_PROFILE: 'standard' });
  log(`direct renderer env=standard + meta=showcase: exit=${e.status} root=${e.html ? rootTag(e.html).match(/data-quality-[a-z]+="[^"]*"/g) : ''}`);
}
fs.writeFileSync(path.join(out, '02-body-diff.txt'), lines.join('\n') + '\n');
