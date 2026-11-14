#!/bin/bash
S=${DRC_OUT:-$(mktemp -d)}
kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o $S/drc.json f133-dongle.kicad_pcb 2>&1 | grep -v Typsnitt | tail -1
python3 - <<P
import json,collections,re
d=json.load(open('$S/drc.json'))
c=collections.Counter((v['severity'],v['type']) for v in d.get('violations',[]))
print(dict(('%s/%s'%k,n) for k,n in c.items()))
for v in d.get('violations',[]):
    if not v['type'].startswith('silk') and not v['type'].startswith('lib_'):
        print('  ',v['type'],(v['description'][:60]+' :: '+' | '.join(i['description'] for i in v.get('items',[])))[:230])
u=collections.Counter()
for v in d.get('unconnected_items',[]):
    m=re.search(r'\[([^\]]+)\]',v['items'][0]['description']); u[m.group(1) if m else '?']+=1
print('unconnected',len(d.get('unconnected_items',[])),dict(u))
P
