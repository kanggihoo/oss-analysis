import fs from 'node:fs';
const html = fs.readFileSync(process.argv[2], 'utf8');
const root = (html.match(/<html[^>]*>/) || [''])[0];
const svg = (html.match(/<svg[^>]*data-animation[^>]*>/) || [''])[0];
const pick = (s, names) => names.map(n => { const m = s.match(new RegExp(`\\s(${n})="([^"]*)"`)); return m ? `${n}=${m[2]}` : null; }).filter(Boolean).join(' ');
console.log('  html:', pick(root, ['data-theme','data-present','data-embed','data-motion','data-guide-open']));
console.log('  svg :', pick(svg, ['data-focus-active','data-reach-active','data-lens-active','data-route-active','data-route-mode','data-animation']));
