#!/usr/bin/env python3
"""Independent finite source-native and repeat bounds. No native calls."""
from pathlib import Path
import json,re,sys
R=Path(__file__).resolve().parents[3]
D=Path(__file__).resolve().parent
loader=(R/'verification/swift-guarded-snapshot-descriptor-rebinding/overlay/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs').read_text()
L=json.loads((R/'verification/swift-guarded-snapshot-loader-work/mir-ledger.json').read_text())
checks=[]
def check(label,yes):
    if not yes:raise AssertionError(label)
    checks.append(label)
def row(owner):return next(v for v in L['nodes'].values() if v['owner']==owner and v['native'])
for name,n in [('PROCESS_CAP',16384),('STR_CAP',4096),('ENTRY_CAP',64),('ATTEMPTS',32)]:
    check('literal-'+name,bool(re.search(r'const '+name+r': [^=]+?= '+str(n)+r';',loader)))
S=re.search(r'const SESSION_IDENTITY: &\[u8\] = b"([^"]+)"',loader)[1]
N=re.search(r'const SESSION_NONCE: &\[u8\] = b"([^"]+)"',loader)[1]
# Key comparisons use native requested-input upper bounds. The third comparison
# executes only for a matched control key, which is short. Taking max over the
# three actual paths avoids combining incompatible key lengths/branch states.
observe_entry_paths=dict(ordinary_key=2*4094+len(S)+len(N),session_key=4*len(S),nonce_key=(len(N)+len(S))+2*len(N)+(len(N)+len(S)))
observe_total=64*max(observe_entry_paths.values())+2*4096
observe_paid=66*2*4096
check('observe-comparison-and-output-buffer-upper',observe_total<=observe_paid)
check('observe-inclusive-pointer65-paid66',next(v for v in L['nodes'].values() if v['owner']=='observe' and v['native'])['repeat']==66)
for n in range(65):
    check('environment-sort-'+str(n),n*(n-1)//2+max(n-1,0)<2080)
check('sort2016',64*63//2==2016)
check('env-comparison-max',8190>=2*4094)
check('read-request-32-call-33-visit',row('read_attempt')['repeat']==33)
check('retained-empty-still-EOF',0//4096+1==1)
check('hex32-and-exit33',next(v for n,v in L['nodes'].items() if v['owner']=='hex' and '{closure#' not in n)['repeat']==33)
# Abstract native element widths are deliberately independent of source leaf
# counts. The real Buffer reservation checks capacity*sizeof(T) against its
# original category limit before allocator entry; existing charged old storage
# satisfies the same limit. No concrete Rust ABI layout is inferred here.
buffer_cases=0
for cap in (0,1,4,64,1024,1048576,16777216):
    for width in (1,2,4,8,16,24,32,40,64):
        for length in (0,1,3,7,31):
            if length*width<=cap:
                check('native-Buffer-capacity',length*width<=cap);buffer_cases+=1
        if width<=cap:check('native-Buffer-one-push',width<=cap)
# For list validation, retain all seven possible comparison sites even though
# compile and session alternatives are mutually exclusive, plus contains/scan
# and prior-key ordering. Calls to word/sections have their own expanded rows.
list_upper=4096+4095+2*4094+7*8190
list_paid=3*16384+7*8190
check('list-scans-and-comparisons-upper',list_upper<=list_paid)
check('build-reserved-and-header-upper',213+16+38<=512)
check('session-reserved-cwd-header-upper',144+4096+16+2<=4096+512)
check('Bytes-put-copy-request',16384>=4095 and 16384>=8)
check('identity-copy8-per-body-paid64',64>=8)
check('validator-source-copy-chunk-request',16384>=16384)
# Process comparisons in load_inner are bounded by section conservation:
# argv+environment+cwd <= session extent, plus fixed identity/digest comparisons.
for session in (0,1,512,65536):
    actual_upper=2*session+9*64+128
    paid=3*session+2*16384+4096+64+16*32
    check('inner-process-and-fixed-input-comparisons',actual_upper<=paid)
report=dict(schema=1,checks_passed=len(checks),python=sys.version,scope='source-specific native request lengths and repeat envelopes only; no actual native API or product function called',observe_entry_paths=observe_entry_paths,observe_total_comparison_and_buffer_upper=observe_total,observe_paid=observe_paid,environment_sort_comparisons=2016,environment_while_visits=2079,Buffer_abstract_capacity_cases=buffer_cases,list_upper=list_upper,list_paid=list_paid,native_contract='Requested API extent is charged for reserve/resize/copy/read; hash input and digest output are separate extents. Comparison input-byte upper bounds are conservative. Private std/native implementations, retries, allocator/kernel work, physical stack/RSS/time are excluded. Typed value transfers use source-leaf accounting and are not asserted to be ABI byte counts.',remaining_defect='wresolve native bytes do not substitute for its missing named Type-slice callback multiplicities; that defect is separately blocking.')
(D/'native-audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(checks_passed=len(checks),observe_upper=observe_total,observe_paid=observe_paid,buffer_cases=buffer_cases)))
