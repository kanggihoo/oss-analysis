// 읽기 전용: 로컬 설치본(레포와 바이트 동일)의 recipes/scenarios.mjs를 import해 레시피 목록·신호를 덤프
import { publicGuideData } from '/Users/kkh/.claude/skills/archify/recipes/scenarios.mjs';
for (const r of publicGuideData()) console.log(r.id, '|', r.type, '|', r.proof, '|', r.presentation.preset, r.presentation.motion, '|', JSON.stringify(r.signals));
