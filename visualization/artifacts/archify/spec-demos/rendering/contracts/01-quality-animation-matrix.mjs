// 점검 1: meta.animation / --quality / meta.quality_profile 조합이 SVG 루트 속성과 SVG 본문에 미치는 영향.
// 설치본(레포와 바이트 동일)의 archify render + check-render-output만 쓴다. HTML은 만든 즉시 지운다.
// 사용: node 01-quality-animation-matrix.mjs   (결과: out/01-matrix.tsv, out/01-matrix.json)
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skill = path.join(process.env.HOME, '.claude/skills/archify');
const cli = path.join(skill, 'bin/archify.mjs');
const checker = path.join(skill, 'scripts/check-render-output.mjs');
const out = path.join(here, 'out');
fs.mkdirSync(out, { recursive: true });

const EXAMPLES = {
  architecture: 'web-app.architecture.json',
  workflow: 'agent-tool-call.workflow.json',
  sequence: 'cache-miss-request.sequence.json',
  dataflow: 'product-analytics.dataflow.json',
  lifecycle: 'agent-run.lifecycle.json',
  erd: 'orders.erd.json',
  class: 'payments.class.json',
  tree: 'payment-platform.tree.json',
  timeline: 'payment-incident.timeline.json',
  waterfall: 'checkout-request.waterfall.json',
};
// 조건: meta 덮어쓰기(null=키 삭제), CLI 옵션
const CONDS = [
  { id: 'base', meta: { quality_profile: null, animation: null }, args: [] },
  { id: 'anim-none', meta: { quality_profile: null, animation: 'none' }, args: [] },
  { id: 'anim-trace', meta: { quality_profile: null, animation: 'trace' }, args: [] },
  { id: 'cli-showcase', meta: { quality_profile: null, animation: null }, args: ['--quality', 'showcase'] },
  { id: 'cli-standard', meta: { quality_profile: null, animation: null }, args: ['--quality', 'standard'] },
  { id: 'meta-showcase', meta: { quality_profile: 'showcase', animation: null }, args: [] },
  { id: 'meta-standard', meta: { quality_profile: 'standard', animation: null }, args: [] },
  { id: 'cli-std+meta-show', meta: { quality_profile: 'showcase', animation: null }, args: ['--quality', 'standard'] },
  { id: 'cli-show+meta-std', meta: { quality_profile: 'standard', animation: null }, args: ['--quality', 'showcase'] },
];
const ROOT_ATTRS = ['data-animation', 'data-quality-profile', 'data-quality-gates', 'data-layout-contract', 'data-motion-choreography', 'data-reader-fit', 'data-engineering-profile'];

function rootAttrs(html) {
  const root = html.match(/<svg\b[^>]*>/)?.[0] || '';
  const o = {};
  for (const a of ROOT_ATTRS) { const m = root.match(new RegExp(`\\s${a}="([^"]*)"`)); o[a] = m ? m[1] : '-'; }
  return o;
}

const rows = [];
for (const [type, ex] of Object.entries(EXAMPLES)) {
  const base = JSON.parse(fs.readFileSync(path.join(skill, 'examples', ex), 'utf8'));
  for (const c of CONDS) {
    const doc = structuredClone(base);
    for (const [k, v] of Object.entries(c.meta)) { if (v === null) delete doc.meta[k]; else doc.meta[k] = v; }
    const input = path.join(out, `m-${type}-${c.id}.json`);
    const output = path.join(out, `m-${type}-${c.id}.html`);
    fs.writeFileSync(input, JSON.stringify(doc));
    const r = spawnSync('node', [cli, 'render', type, input, output, ...c.args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    const row = { type, cond: c.id, render_exit: r.status };
    if (r.status === 0 && fs.existsSync(output)) {
      const html = fs.readFileSync(output, 'utf8');
      const svg = html.match(/<svg\b[\s\S]*?<\/svg>/)?.[0] || '';
      Object.assign(row, rootAttrs(html));
      row.svg_sha = crypto.createHash('sha256').update(svg).digest('hex').slice(0, 10);
      row.animate_marks = (svg.match(/data-animate="/g) || []).length;
      const chk = spawnSync('node', [checker, output], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
      row.check_exit = chk.status;
      try { const j = JSON.parse(chk.stdout); row.check_profile = j.composition?.profile; row.check_errors = j.composition?.summary?.errors; row.check_warnings = j.composition?.summary?.warnings; row.check_failed = j.checks.filter((x) => !x.ok).map((x) => x.name).join(','); } catch { row.check_failed = 'unparsed'; }
      fs.rmSync(output);
    } else {
      row.stderr_first = (r.stderr.split('\n').find((l) => l.startsWith('[')) || r.stderr.split('\n')[0] || '').slice(0, 100);
    }
    fs.rmSync(input, { force: true });
    rows.push(row);
  }
}
fs.writeFileSync(path.join(out, '01-matrix.json'), JSON.stringify(rows, null, 1));
const cols = ['type', 'cond', 'render_exit', ...ROOT_ATTRS, 'svg_sha', 'animate_marks', 'check_exit', 'check_profile', 'check_errors', 'check_warnings', 'check_failed', 'stderr_first'];
fs.writeFileSync(path.join(out, '01-matrix.tsv'), [cols.join('\t'), ...rows.map((r) => cols.map((c) => r[c] ?? '').join('\t'))].join('\n') + '\n');
console.log(`rows=${rows.length}`);
