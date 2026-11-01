#!/bin/bash
# 인용만 한(@code 아님) 레포 근거가 줄 범위 밖일 때 validate 가 통과하는지, 발췌가 HTML 에 실리는지 확인. 결과는 out/cite/.
cd "$(dirname "$0")"; . ./env.sh; O=out/cite; mkdir -p $O
$A finalize explainer in/cite-bad-lines.archify.md $O/cite.html --repo-root $R --json > $O/cite.json 2>/dev/null; echo "rc=$?"
python3 - $O/cite.html <<'P'
import re,json,sys
h=open(sys.argv[1]).read()
b=json.loads(re.search(r'id="archify-explainer-prepared">(.*?)</script>',h,re.S).group(1))
s=b['preparedSources']['sources']['s1']
print({k:(v if k!='text' else '<text>') for k,v in s.items()}, 'has_text', 'text' in s, 'deps', [d['kind'] for d in b['dependencies']])
P
