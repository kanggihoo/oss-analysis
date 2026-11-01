#!/bin/sh
# deliver+check+browser-check one example per type; record check names, exit codes, composition summary, browser readerFit/min text px
A=/Users/kkh/.claude/skills/archify/bin/archify.mjs
cd "$(dirname "$0")"; rm -rf types; mkdir types
run() { t=$1; n=$2; src=$3
  node $A deliver $t $src types/$n.html --json >types/$n.deliver.json 2>/dev/null; d=$?
  node $A check types/$n.html --json --require-provenance >types/$n.check.json; c=$?
  node $A browser-check types/$n.html --json --require-provenance >types/$n.bc.json; b=$?
  python3 - "$t" "$n" $d $c $b <<'PY'
import json,sys
t,n,d,c,b=sys.argv[1:]
ch=json.load(open(f'types/{n}.check.json')); bc=json.load(open(f'types/{n}.bc.json'))
comp=ch.get('composition',{})
v=bc.get('containment',{}).get('viewports',[])
print(f"{t:13s} deliver={d} check={c} browser={b} checks={len(ch.get('checks',[]))} compSummary={comp.get('summary')} profile={comp.get('profile')} warn={[i['code'] for i in comp.get('issues',[])]} | fit={v[0].get('readerFit') if v else None} minTextPx={round(v[0]['minimumProjectedNodeTextPx'],2) if v and v[0].get('minimumProjectedNodeTextPx') else None} disp={[x['overflowDisposition'] for x in v]}")
PY
}
E=/Users/kkh/Desktop/oss-analysis/visualization/repos/archify/archify/examples
run architecture architecture $E/brand-aware-delivery.architecture.json
run sequence sequence $E/cache-miss-request.sequence.json
run workflow workflow $E/release-delivery.workflow.json
run workflow workflow2 inputs/alltypes/agent-tool-call.workflow.json
run lifecycle lifecycle inputs/alltypes/agent-run.lifecycle.json
run tree tree inputs/alltypes/archify-repository.tree.json
run waterfall waterfall inputs/alltypes/checkout-request.waterfall.json
run dataflow dataflow inputs/alltypes/event-stream.dataflow.json
run erd erd inputs/alltypes/orders.erd.json
run timeline timeline inputs/alltypes/payment-incident.timeline.json
run class class inputs/alltypes/payments.class.json
