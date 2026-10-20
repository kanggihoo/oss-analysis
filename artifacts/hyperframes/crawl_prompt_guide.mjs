// Prompt Guide(.md)를 사이트에서 받아 레벨별 폴더에 순서 번호로 저장한다.
// 목록·순서는 repos/hyperframes/docs/docs.json의 "Prompt Guide" 그룹. 사용: node crawl_prompt_guide.mjs
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const BASE = "https://hyperframes.heygen.com";
const OUT = join(here, "prompt-guide");
const docs = JSON.parse(readFileSync(join(here, "../../repos/hyperframes/docs/docs.json"), "utf8"));

const find = (n) => {
  if (Array.isArray(n)) return n.map(find).find(Boolean);
  if (n && typeof n === "object") return n.group === "Prompt Guide" ? n : Object.values(n).map(find).find(Boolean);
};
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

// 최상위 문자열 = 폴더 없는 페이지, 객체 = 레벨 그룹
const items = [];
let top = 0;
for (const p of find(docs.navigation).pages) {
  if (typeof p === "string") items.push({ dir: "", n: ++top, page: p });
  else p.pages.forEach((page, i) => items.push({ dir: slug(p.group), n: i + 1, page, group: p.group }));
}

const manifest = [];
for (const [idx, it] of items.entries()) {
  const url = `${BASE}/${it.page}.md`;
  const res = await fetch(url);
  const text = await res.text();
  if (!res.ok || !(res.headers.get("content-type") ?? "").includes("markdown") || !text.trim())
    throw new Error(`${url}: ${res.status} ${res.headers.get("content-type")}`);
  const name = `${String(it.n).padStart(2, "0")}-${it.page.split("/").pop()}.md`;
  mkdirSync(join(OUT, it.dir), { recursive: true });
  writeFileSync(join(OUT, it.dir, name), text);
  manifest.push({ order: idx + 1, group: it.group ?? null, file: join(it.dir, name), url, bytes: Buffer.byteLength(text) });
  await new Promise((r) => setTimeout(r, 200));
}
writeFileSync(join(OUT, "manifest.json"), JSON.stringify({ fetched: new Date().toISOString().slice(0, 10), pages: manifest }, null, 2));
console.log(`${manifest.length} pages`);
