#!/usr/bin/env python3
"""finalize --json 요약(stdout JSON)에서 수리 루프가 읽는 필드만 한 블록으로 줄여 출력한다."""
import json,sys
raw=open(sys.argv[1]).read()
try: j=json.loads(raw)
except Exception: print('  (stdout이 JSON 아님)', raw[:200].replace('\n',' / ')); sys.exit()
print(f"  status={j.get('status')} ok={j.get('ok')} failedStage={j.get('failedStage')} gates={j.get('gates')}")
ds=j.get('diagnostics',[])
ds_sum=j.get('diagnosticSummary')
if ds_sum: print('  diagnosticSummary',json.dumps(ds_sum))
for x in ds:
    print(f"  - [{x.get('severity')}] {x['code']} subject={json.dumps(x.get('subject'),ensure_ascii=False)[:150]}")
    print(f"      message: {x['message'][:230]!r}")
    for f in x.get('supportedFixes',[]): print(f"      fix: {f[:260]}")
for k in ('nextAction','visualReviewRecommendation','layoutReviewRecommendation'):
    if k in j: print(f"  {k}: {json.dumps(j[k],ensure_ascii=False)[:700]}")
