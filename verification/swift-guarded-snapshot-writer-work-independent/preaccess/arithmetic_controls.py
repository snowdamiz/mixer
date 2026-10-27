#!/usr/bin/env python3
"""Independent finite source-event controls; does not import or run product code."""
from pathlib import Path
import json, hashlib, sys, platform
from collections import Counter
BASE=Path(__file__).resolve().parent
MAX=(1<<64)-1
CAPS=[67108864,512,8192,34,79966,8192,4096,4096,4096]
WIDTH=[0,3,1,5,3,4,4,4,4]
checks=[]
def check(name,condition,**details):
    assert condition,(name,details)
    checks.append(dict(name=name,passed=True,**details))
def shape(c):
    assert len(c)==9 and all(0<=n<=limit for n,limit in zip(c,CAPS))
    records=sum(c[1:]);words=sum(n*w for n,w in zip(c,WIDTH))
    extent=2560+c[0]+8*words
    return dict(records=records,words=words,extent=extent,blocks=(extent+4095)//4096)
def events(B,attempts,positive):
    return dict(attempts=attempts,stop=12+5*B+2*attempts,native=3+attempts,
        fill=4096*B,getters=attempts+positive+3*B+2,checked_increments=attempts+2*positive+B)
for source in [0,1,7,8,1535,1536,1537,4095,4096,CAPS[0]]:
    for counts in [[source]+[0]*8,[source]+CAPS[1:]]:
        s=shape(counts);B=s['blocks']
        for A in [B,2*B,31*B,32*B]:
            for V in [0,A//2,A]:
                x=events(B,A,V)
                check('bounded-events',A<=32*B and x['stop']<=12+69*B and x['getters']<=67*B+2 and x['native']<=3+32*B,shape=s,events=x)
        for n in [1,2,31,32]:
            # n attempts may be positive partial writes, Interrupted, or mixed.
            # All branches share one pre/post observation per actual write.
            for terminal in ['completed','interrupted-exhaustion','positive-short-exhaustion','zero','overreported','io','post-stop']:
                prefix=10+4+2*n
                after=prefix+(1 if terminal=='completed' else 0)+(2 if terminal=='completed' and B==1 else 0)
                check('failure-prefix',after<=events(B,32*B,32*B)['stop'],attempts=n,terminal=terminal,prefix_stop=after)
maxshape=shape(CAPS)
check('original-cap-extent',maxshape['extent']==69765152 and maxshape['blocks']==17033,shape=maxshape)
check('shape-operation-counts',8+8+2+1==19 and 8+1==9)
check('pairing-ticket-counts',dict(pair_none=4+4+4+3,pair_wasi=4+4+4+10+3,pre_none=4+4+4+3+3,pre_wasi=4+4+4+10+3+3,complete_none=4+4+4+3+6,complete_wasi=4+4+4+10+3+6)==dict(pair_none=15,pair_wasi=25,pre_none=18,pre_wasi=28,complete_none=21,complete_wasi=31))
# Leaf structure controls are independent of physical ABI/layout.
wasi=6+7;reservation=8*2+2;live=6*2;validation=10
usage=reservation+live+5+2+4+validation+(1+wasi)
failure=1+1+1+2+2+3+1+1+2+1+3+2+usage+(1+usage)
check('nested-copy-leaves',wasi==13 and reservation==18 and live==12 and usage==65 and failure==151 and 1+failure==152,usage=usage,failure=failure,stop=1+failure)
# Checked operations must refuse overflow; no wrapping can enlarge authority.
def add(a,b): return a+b if a<=MAX-b else None
def mul(a,b): return a*b if b==0 or a<=MAX//b else None
for a,b,expected in [(0,0,0),(MAX,0,MAX),(MAX,1,None),(MAX-1,1,MAX)]:
    check('checked-u64-add',add(a,b)==expected,a=a,b=b,expected=expected)
for a,b,expected in [(0,MAX,0),(MAX,1,MAX),(MAX,2,None),(MAX//8,8,(MAX//8)*8)]:
    check('checked-u64-mul',mul(a,b)==expected,a=a,b=b,expected=expected)
families=dict(Counter(c['name'] for c in checks))
results=dict(schema=1,status='independent-preaccess-controls-pass',count=len(checks),python=sys.version,platform=platform.platform(),maximum_shape=maxshape,families=families,all_checks_sha256=hashlib.sha256(json.dumps(checks,sort_keys=True,separators=(',',':')).encode()).hexdigest(),structural_leaf_reference=dict(reservations=reservation,live=live,wasi=wasi,validation=validation,usage=usage,failure=failure,stop=1+failure),maximum_events=events(maxshape['blocks'],32*maxshape['blocks'],32*maxshape['blocks']),scope='Python arithmetic and immutable source-event controls only; no product runtime or work selection')
(BASE/'arithmetic-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(status=results['status'],checks=len(checks),maximum_shape=maxshape)))
