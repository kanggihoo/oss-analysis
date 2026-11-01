#!/bin/sh
# provenance mismatch / missing sidecar / skipped / out-dir / usage errors. Installed archify (byte-identical to repo archify/).
A="node /Users/kkh/.claude/skills/archify/bin/archify.mjs"
cd "$(dirname "$0")"; rm -rf prov; mkdir -p prov
summ() { python3 -c "
import json,sys
j=json.load(sys.stdin)
print('  ok=',j.get('ok'),'status=',j.get('status'),'provenance=',j.get('provenance'),'codes=',[d['code'] for d in j.get('diagnostics',[])],'chrome=',(j.get('chrome') or {}).get('status'))" ; }
$A deliver architecture inputs/brand-aware-delivery.architecture.json prov/a.html --json >/dev/null 2>&1; echo "deliver exit=$?"; ls prov
echo "P0 pristine: check --require-provenance"; $A check prov/a.html --require-provenance | summ; echo "  exit=${PIPESTATUS:-?}"
$A check prov/a.html --require-provenance >/dev/null; echo "  exit=$?"
cp prov/a.html prov/a.orig.html
printf '\n' >> prov/a.html
echo "P1 one byte appended: check --require-provenance"; $A check prov/a.html --require-provenance | summ; $A check prov/a.html --require-provenance >/dev/null; echo "  exit=$?"
echo "P1b same without the flag"; $A check prov/a.html | summ; $A check prov/a.html >/dev/null; echo "  exit=$?"
echo "P1c browser-check --require-provenance (must fail before Chrome)"; $A browser-check prov/a.html --json --require-provenance | summ; $A browser-check prov/a.html --json --require-provenance >/dev/null; echo "  exit=$?"; ls prov
python3 -c "
import json;j=json.load(open('prov/a.browser-check.json'));print('  persisted receipt keys:',sorted(j));print('  diagnostics[0].evidence:',j['diagnostics'][0]['evidence'])"
echo "P2 sidecar deleted, artifact restored"; cp prov/a.orig.html prov/a.html; mv prov/a.delivery.json prov/a.delivery.json.bak
$A check prov/a.html | summ; $A check prov/a.html >/dev/null; echo "  no flag exit=$?"
$A check prov/a.html --require-provenance | summ; $A check prov/a.html --require-provenance >/dev/null; echo "  flag exit=$?"
$A browser-check prov/a.html --json --require-provenance | summ; $A browser-check prov/a.html --json --require-provenance >/dev/null; echo "  browser-check flag exit=$?"
mv prov/a.delivery.json.bak prov/a.delivery.json
echo "P2b sidecar status=failed? (hand-edit sidecar)"; python3 - <<'PY'
import json
p='prov/a.delivery.json'; j=json.load(open(p)); j['artifact']['sha256']='0'*64; json.dump(j,open(p,'w'))
PY
$A check prov/a.html | summ; $A check prov/a.html >/dev/null; echo "  exit=$?"
echo "P3 ARCHIFY_CHROME=/nonexistent -> skipped"; ARCHIFY_CHROME=/nonexistent/chrome $A browser-check work/font_7.3.html --json --out-dir prov/evid | summ; ARCHIFY_CHROME=/nonexistent/chrome $A browser-check work/font_7.3.html --json --out-dir prov/evid >/dev/null; echo "  exit=$?"; ls prov/evid
echo "P4 unreadable file"; $A check prov/missing.html | head -c 400; $A check prov/missing.html >/dev/null 2>&1; echo "  check exit=$?"
$A browser-check prov/missing.html --json | summ; $A browser-check prov/missing.html --json >/dev/null 2>&1; echo "  browser-check exit=$?"
echo "P5 usage"; $A check >/dev/null 2>&1; echo "  check (no args) exit=$?"; $A check a.html b.html >/dev/null 2>&1; echo "  check 2 files exit=$?"; $A check x.html --bogus >/dev/null 2>&1; echo "  check --bogus exit=$?"; $A browser-check x.html --bogus >/dev/null 2>&1; echo "  browser-check --bogus exit=$?"; $A browser-check >/dev/null 2>&1; echo "  browser-check (no args) exit=$?"; $A check x.html --json >/dev/null 2>&1; echo "  check x.html --json (missing file) exit=$?"
