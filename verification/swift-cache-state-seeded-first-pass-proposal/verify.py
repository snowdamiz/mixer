#!/usr/bin/env python3
"""Independent custody/count/mathematical checks; import no producer or Mixer."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def read(n): return json.loads((HERE/n).read_text())
def count(ops):
    return {'scalars':sum(o['kind']=='scalar' for o in ops),'copies':sum(o['kind']=='copy' for o in ops)}

def independent_merge(times,mask):
    # Finite mathematics only, with ordinary sorted-list merging independent of
    # producer cached heads. Real MAX remains a valid key;255 is an index tail.
    values=[]
    for i in range(0,64,2):
        left=i if mask&(1<<i) else 255
        right=i+1 if mask&(1<<(i+1)) else 255
        if right==255 or (left!=255 and times[left]<=times[right]): values.extend([left,right])
        else: values.extend([right,left])
    comparisons=32
    for width in [2,4,8,16,32]:
        nxt=[]
        for base in range(0,64,width*2):
            left=values[base:base+width]
            right=values[base+width:base+width*2]
            while left and right:
                comparisons+=1
                take_left=right[0]==255 or (left[0]!=255 and times[left[0]]<=times[right[0]])
                nxt.append(left.pop(0) if take_left else right.pop(0))
            nxt+=left+right
        values=nxt
    eligible=[i for i in range(64) if mask&(1<<i)]
    expected=sorted(eligible,key=lambda i:(times[i],i))+[255]*(64-len(eligible))
    assert values==expected
    assert len(values)==64 and comparisons<=321
    return values,comparisons

def main():
    bindings=read('input-bindings.json')
    for item in bindings['inputs']:
        b=(ROOT/item['path']).read_bytes()
        assert len(b)==item['bytes'] and sha(b)==item['sha256']
    assert sha(json.dumps(bindings['inputs'],sort_keys=True,separators=(',',':')).encode())==bindings['input_tree_digest']
    old=json.loads((ROOT/'verification/swift-cache-state-fixed-array-merge-proposal/seal.json').read_text())
    assert old['member_count']==18 and old['member_bytes']==2799286
    for item in old['members']:
        b=(ROOT/item['path']).read_bytes()
        assert len(b)==item['bytes'] and sha(b)==item['sha256']
    source=(HERE/'source/cache_state.rs.txt').read_text()
    merge=(HERE/'source/merge.rs.txt').read_text()
    frozen=(ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').read_text()
    assert sha(frozen.encode())=='0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
    assembly=read('source-assembly.json')
    assert sha(source.encode())==assembly['proposed_sha256']
    assert sha(merge.encode())==assembly['merge_sha256'] and merge in source
    assert source[source.index('fn cleanup('):]==frozen[frozen.index('fn cleanup('):]
    marker='            sq(c, 10, mask);'
    assert source[source.index(marker):]==frozen[frozen.index(marker):]
    marker='    let body = w[6] as usize;'; call='            merge(c);'
    assert source[source.index(marker):source.index(call)]==frozen[frozen.index(marker):frozen.index(call)]
    oldmerge=(ROOT/'verification/swift-cache-state-fixed-array-merge-proposal/source/merge.rs.txt').read_text()
    marker='            let source: &[u8; 64] = indices[512..576].first_chunk::<64>().expect("index64");'
    at=oldmerge.index(marker); start=oldmerge.rfind('    {\n        let output = {',0,at)
    assert merge.endswith(oldmerge[start:])
    assert sha(oldmerge[start:].encode())==assembly['retained_five_pass_suffix_sha256']
    assert merge.count('let take_left = if s.ri >= 255 {')==320
    assert merge.count('let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };')==32
    assert merge.count('{ second },')==32
    assert merge.count('.copy_from_slice(&output);')==6
    assert 'let eligibility = ld(c, 640);' in merge
    assert 'let mut eligibility = 0u64;' in source
    assert 'if occupied == 1 && pins == 0 { eligibility |= 1u64 << slot; }' in source
    assert 'index_bytes[128..136].copy_from_slice(&eligibility.to_le_bytes());' in source
    assert 'index_bytes[slot] =' not in source and 'index_bytes[512 + slot] =' not in source
    assert 'while slot < 64 {\n            timestamp_words[slot] = 0u64.to_le_bytes();' in source
    assert merge.count('indices[512..576].copy_from_slice(&output);')==3
    assert merge.count('indices[0..64].copy_from_slice(&output);')==3
    firstpass=merge[:merge.index(marker)]
    # The consumer mask operands are literal one-hot64; no hidden shift or
    # dependency on optimizer simplification supplies this representation.
    for i in range(64):
        name='left' if i%2==0 else 'right'
        assert f'let {name} = if eligibility & 0x{1<<i:016x}u64 != 0 {{ {i}u8 }} else {{ u8::MAX }};' in firstpass
        assert f'u64::from_le_bytes(timestamps[{i}usize])' in firstpass
    assert 'indices[' not in firstpass[firstpass.index('let mut second'):firstpass.index('indices[512..576].copy_from_slice')]
    assert 'unsafe' not in merge and 'macro_rules!' not in merge
    witness=read('g2-witness.json')
    assert witness['kind']==1 and witness['eligibility_mask']==0
    residents=witness['residents'];pins=witness['pins'];prior=witness['prior']
    assert len(residents)==len(pins)==64
    assert sum(r['bytes'] for r in residents)==prior['resident_bytes']==64
    assert sum(r['pins'] for r in residents)==prior['pin_count']==64
    assert len({r['function'] for r in residents})==64
    for i,(r,p) in enumerate(zip(residents,pins)):
        assert r['occupied']==1 and r['pins']==1 and r['bytes']==1
        assert r['generation']==r['reserved']==0
        assert p['entry']==i and p['nonce']==i+1 < prior['next_nonce']==65
    assert all(not(r['occupied']==1 and r['pins']==0) for r in residents)
    # Independently derived exact selected subtrace. No loop/guard/mask/setup
    # source is made free: all is explicitly omitted positive work.
    # Each fat-slice array8 Index costs21 plus its fully evaluated index; LE
    # scalar call/result/return costs5. Offsets are7/10, cast offsets9/12.
    resident_load_scalars=(21+7+5)+6*(21+10+5)
    pin_load_scalars=(21+7+5)+(21+10+5)+(21+9+5)+(21+12+5)
    timestamp_scalars=21+1+4
    checked_scalars=2+6+5
    release_scalars=20+1+1+2+1+2
    assert (resident_load_scalars,pin_load_scalars,timestamp_scalars,checked_scalars,release_scalars)==(249,142,26,13,27)
    s=64*(resident_load_scalars+pin_load_scalars+timestamp_scalars+checked_scalars+release_scalars)
    c=64*(7+4+1+1)
    assert s==29248 and c==832 and (s+15)//16+c==2660
    necessary=read('necessary-bound.json')
    assert necessary['necessary_scalars']==s and necessary['necessary_complete_copies']==c
    assert necessary['necessary_groups']==2660>necessary['cap']==2560
    assert necessary['over_cap']==100 and not necessary['complete_G2_G3_G4_G5_upper_ledger_built']
    templates=read('component-templates.json')
    for name,ops in templates['templates'].items(): assert count(ops)==templates['counts'][name]
    expected={'resident7_loads':(249,7),'pin4_loads':(142,4),'timestamp_assignment':(26,1),
              'successful_checked_add':(13,1),'release_kind_short_circuit':(27,0),
              'old_eligible_head':(68,1),'seeded_head0':(36,1),'seeded_choice':(18,0)}
    for n,(sc,cp) in expected.items(): assert templates['counts'][n]=={'scalars':sc,'copies':cp}
    assert [o['bytes'] for o in templates['templates']['successful_checked_add'] if o['kind']=='copy']==[16]
    raw=gzip.decompress((HERE/'finite-subtrace-ledger.json.gz').read_bytes())
    summary=read('subtrace-summary.json')
    assert len(raw)==summary['bytes_decompressed'] and sha(raw)==summary['sha256_decompressed']
    packet=json.loads(raw);events=packet['events'];em={e['id']:e for e in events};used=[]
    assert len(em)==len(events)==summary['event_count']
    for group in packet['groups']:
        members=[em[n] for n in group['events']];used+=group['events']
        assert all(e['kind']==group['kind'] and e['owner']==group['owner'] for e in members)
        if group['kind']=='scalar': assert 1<=len(members)<=16
        else: assert len(members)==1 and members[0]['bytes']==group['bytes']<=128
    assert len(used)==len(set(used))==len(events) and set(used)==set(em)
    for owner in ['G2','G3','G4']:
        sc=sum(e['owner']==owner and e['kind']=='scalar' for e in events)
        cp=sum(e['owner']==owner and e['kind']=='copy' for e in events)
        got=packet['totals'][owner]
        assert got['scalars']==sc and got['copies']==cp and got['groups']==(sc+15)//16+cp
    assert packet['totals']['G2']['groups']==2660
    assert packet['totals']['G3']['groups']==2443 and packet['totals']['G4']['groups']==543
    # Complete finite input families retain all64 outputs and tails; these are
    # mathematical checks, never execution of the proposed source.
    limit=(1<<64)-1
    masks=[0,1,1<<63,limit,0xaaaaaaaaaaaaaaaa,0x5555555555555555]
    masks += [(1<<n)-1 for n in range(1,65)]
    time_families=[list(range(64)),list(reversed(range(64))),[0]*64,[limit]*64,
                   [limit if i%2 else 0 for i in range(64)],[int(format(i,'06b')[::-1],2) for i in range(64)]]
    cases=0
    for mask in masks:
        for times in time_families: independent_merge(times,mask);cases+=1
    merge_w=read('merge-witness.json')
    final,comparisons=independent_merge(merge_w['timestamps'],limit)
    assert final==merge_w['output'] and comparisons==321
    assert [p['comparisons'] for p in merge_w['passes']]==[32,48,56,60,62,63]
    # Eligible MAX and absent255 coexist and remain distinguishable.
    final,_=independent_merge([limit]*64,3)
    assert final==[0,1]+[255]*62
    print(json.dumps({'verified':'custody, exact source bindings, grouped lower-bound arithmetic and independent finite mathematics only',
        'command':[sys.executable,'-B',str(HERE/'verify.py')],'python':sys.version,
        'source_revision':assembly['base_sha256'],'input_tree_digest':bindings['input_tree_digest'],
        'G2_necessary_groups':2660,'G2_cap':2560,'G2_over_cap':100,
        'G3_finite_subtrace_groups':2443,'G4_finite_subtrace_groups':543,
        'mathematical_cases':cases+2,'all_counted_events_grouped_once':True,
        'complete_source_upper_layout_lifetime_implementation_or_GA_accepted':False,
        'compiler_or_product_runtime_executed':False},indent=2))

if __name__=='__main__': main()
