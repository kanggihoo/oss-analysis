// 점검 2: 미리 만들어 둔 잠금 파일이 deliver / render 에 미치는 영향 (프로세스 kill 시뮬레이션은 하지 않는다).
// 설치본(레포와 바이트 동일)의 archify CLI만 쓴다. scratch 폴더(out/work-*)는 끝에 지운다. 결과: out/03-lock.txt
// 사용: node 03-lock-deliver-render.mjs
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skill = path.join(process.env.HOME, '.claude/skills/archify');
const cli = path.join(skill, 'bin/archify.mjs');
const out = path.join(here, 'out');
const lines = [];
const log = (s) => { lines.push(s); console.log(s); };
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 10);
const uuid = '11111111-1111-4111-8111-111111111111';
const env = { ...process.env, ARCHIFY_UPDATE_CHECK_DISABLED: '1' };

const input = path.join(out, '03-input.json');
fs.writeFileSync(input, fs.readFileSync(path.join(skill, 'examples/agent-run.lifecycle.json')));
const inputDoc = JSON.parse(fs.readFileSync(input, 'utf8')); inputDoc.meta.output = 'unused.html'; fs.writeFileSync(input, JSON.stringify(inputDoc));

function run(args, cwd) {
  const r = spawnSync('node', [cli, ...args], { encoding: 'utf8', cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
  return r;
}
function listing(dir) { return fs.readdirSync(dir).sort().map((n) => { const p = path.join(dir, n); const st = fs.lstatSync(p); return `${n}${st.isDirectory() ? '/' : ''}`; }).join(' '); }
function deliverJson(dir, extra = []) {
  const r = run(['deliver', 'lifecycle', input, path.join(dir, 'a.html'), '--json', ...extra], dir);
  let j = {}; try { j = JSON.parse(r.stdout); } catch {}
  return { r, j, summary: `exit=${r.status} ok=${j.ok} stage=${j.stage ?? '-'} provenance=${j.provenance ?? '-'} code=${(j.diagnostics || []).map((d) => d.code).join(',') || '-'}` };
}

const deadPid = 4194000; // 존재하지 않는 PID(확인: kill -0 실패)
try { process.kill(deadPid, 0); log('WARN: dead pid is alive'); } catch { /* ok */ }

const cases = [
  ['stale (valid v1, dead pid)', (d) => fs.writeFileSync(path.join(d, '.archify-delivery-lock.json'), JSON.stringify({ schemaVersion: 1, receiptId: uuid, pid: deadPid }) + '\n')],
  ['concurrent (valid v1, live pid)', (d) => fs.writeFileSync(path.join(d, '.archify-delivery-lock.json'), JSON.stringify({ schemaVersion: 1, receiptId: uuid, pid: process.pid }) + '\n')],
  ['invalid (not JSON)', (d) => fs.writeFileSync(path.join(d, '.archify-delivery-lock.json'), 'garbage\n')],
  ['invalid (directory)', (d) => fs.mkdirSync(path.join(d, '.archify-delivery-lock.json'))],
  ['invalid (empty file)', (d) => fs.writeFileSync(path.join(d, '.archify-delivery-lock.json'), '')],
  ['legacy lock a.delivery-lock.json (dead pid)', (d) => fs.writeFileSync(path.join(d, 'a.delivery-lock.json'), JSON.stringify({ schemaVersion: 1, receiptId: uuid, pid: deadPid }) + '\n')],
];

for (const withPrior of [false, true]) {
  log(`\n## 사전 산출물 ${withPrior ? '있음(HTML+current provenance)' : '없음'}`);
  for (const [name, setup] of cases) {
    const dir = path.join(out, `work-${withPrior ? 'p' : 'n'}-${cases.findIndex((c) => c[0] === name)}`);
    fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
    let before = '';
    if (withPrior) {
      const first = deliverJson(dir);
      if (first.j.ok !== true) { log(`  prior deliver failed: ${first.summary}`); continue; }
      before = `html=${sha(path.join(dir, 'a.html'))} prov=${sha(path.join(dir, 'a.delivery.json'))}`;
    }
    setup(dir);
    const filesBefore = listing(dir);
    const d = deliverJson(dir);
    const filesAfter = listing(dir);
    const after = withPrior ? `html=${sha(path.join(dir, 'a.html'))} prov=${sha(path.join(dir, 'a.delivery.json'))}` : '';
    log(`- ${name}: ${d.summary}`);
    log(`    files before: ${filesBefore}`);
    log(`    files after : ${filesAfter}`);
    if (withPrior) log(`    ${before} -> ${after}${before === after ? ' (불변)' : ' (변함)'}`);
    // stale lock evidence
    const ev = (d.j.diagnostics || [])[0]?.evidence; if (ev && (ev.pid || ev.lock)) log(`    evidence: ${JSON.stringify(ev).slice(0, 200)}`);
    // 같은 폴더에서 render(단일 파일 경로)는 잠금을 보지 않는다
    if (name.startsWith('stale')) {
      const r = run(['render', 'lifecycle', input, path.join(dir, 'r.html')], dir);
      log(`    render in same dir: exit=${r.status} created r.html=${fs.existsSync(path.join(dir, 'r.html'))} leftovers=${listing(dir).split(' ').filter((n) => /archify-(render|remove)/.test(n)).join(',') || '-'}`);
    }
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
fs.rmSync(input, { force: true });
fs.writeFileSync(path.join(out, '03-lock.txt'), lines.join('\n') + '\n');
