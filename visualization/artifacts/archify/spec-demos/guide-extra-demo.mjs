// 읽기 전용: 중복 신호, 최대 점수, 레시피 유형 분포 (설치본 import)
import { publicGuideData, recommendScenario } from '/Users/kkh/.claude/skills/archify/recipes/scenarios.mjs';
const norm = (v) => String(v).normalize('NFKC').toLowerCase().replace(/[\s_]+/g, ' ').trim();
const data = publicGuideData();
const types = {};
for (const r of data) types[r.type] = (types[r.type] || 0) + 1;
console.log('types', JSON.stringify(types));
for (const r of data) {
  const seen = new Map();
  for (const [s] of r.signals) seen.set(norm(s), (seen.get(norm(s)) || 0) + 1);
  const dup = [...seen].filter(([, n]) => n > 1).map(([s]) => s);
  const total = r.signals.reduce((a, [, w]) => a + w, 0);
  if (dup.length) console.log('duplicate signals in', r.id, dup);
  console.log(r.id, 'signals', r.signals.length, 'sumWeights', total);
}
const w = recommendScenario('webhook');
console.log('webhook =>', w.confidence, JSON.stringify(w.matchedSignals), w.recommendation.id);
const e = recommendScenario('database_schema');
console.log('database_schema =>', e.confidence, JSON.stringify(e.matchedSignals), e.recommendation.id);
const z = recommendScenario('   ');
console.log('blank =>', z.confidence, z.recommendation.id, z.lang);
const l = recommendScenario('api request', { lang: 'zh' });
console.log('lang override =>', l.lang, l.recommendation.title);
