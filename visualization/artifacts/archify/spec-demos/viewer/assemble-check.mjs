// 템플릿 소스 분할 규칙의 독립 재구현. 레포의 scripts/generate-viewer.mjs를 실행하지 않고,
// 스펙 1.5에 적은 규칙(마커 1회 치환, CSS만 4칸 들여쓰기, export.js 안의 EXPORT_CLEANUP 중첩 마커 먼저 확장)만으로
// viewer/*를 합쳐 archify/assets/template.html과 바이트 비교한다. 읽기 전용.
import fs from 'node:fs';
import path from 'node:path';
const root = process.argv[2];
const read = (f) => fs.readFileSync(path.join(root, f), 'utf8');
const frags = [
  ['/* ARCHIFY:VIEWER_CSS */', 'viewer/viewer.css', 4], ['/* ARCHIFY:EXPORT */', 'viewer/export.js'],
  ['/* ARCHIFY:READER_LAYOUT */', 'viewer/reader-layout.js'], ['/* ARCHIFY:CHROME_LAYOUT */', 'viewer/viewer-chrome-layout.js'],
  ['/* ARCHIFY:CAMERA */', 'viewer/viewer-camera.js'], ['/* ARCHIFY:RADAR */', 'viewer/semantic-radar.js'],
  ['/* ARCHIFY:MOTION_GOVERNOR */', 'viewer/motion-governor.js'], ['/* ARCHIFY:NODE_FINDER */', 'viewer/node-finder.js'],
  ['/* ARCHIFY:NODE_OUTLINE */', 'viewer/node-outline.js'], ['/* ARCHIFY:TREE_BRANCHES */', 'viewer/tree-branches.js'],
  ['/* ARCHIFY:FOCUS */', 'viewer/focus.js'], ['/* ARCHIFY:INTENT_TRACE */', 'viewer/intent-trace.js'],
  ['/* ARCHIFY:SEMANTIC_LENS */', 'viewer/semantic-lens.js'], ['/* ARCHIFY:ROUTE_PROBE */', 'viewer/route-probe.js'],
  ['/* ARCHIFY:EXPORT_CLEANUP */', 'viewer/export-cleanup.js'],
];
let out = read('viewer/template.source.html');
for (const [marker, file, indent = 0] of frags) {
  const parts = out.split(marker);
  if (parts.length !== 2) throw new Error('marker count != 1: ' + marker);
  let src = read(file);
  if (indent) src = src.split('\n').map((l) => (l.length ? ' '.repeat(indent) + l : l)).join('\n');
  let tail = parts[1];
  if (indent && tail.startsWith('\n')) tail = tail.slice(1);
  out = parts[0] + src + tail;
}
const built = Buffer.from(out);
const committed = fs.readFileSync(path.join(root, 'archify/assets/template.html'));
console.log('rebuilt bytes  :', built.length);
console.log('committed bytes:', committed.length);
console.log('byte-identical :', built.equals(committed));
const left = out.match(/\/\* ARCHIFY:[A-Z_]+ \*\//g);
console.log('leftover JS/CSS markers:', left ? left.join(',') : 'none');
console.log('HTML comment slots left in output:', (out.match(/<!-- ARCHIFY:[A-Z_]+ -->/g) || []).join(', '));
console.log('guided-views.js used:', frags.some(([, f]) => f.includes('guided-views')), '| "guided-view" in template.html:', committed.toString().includes('guided-view'));
