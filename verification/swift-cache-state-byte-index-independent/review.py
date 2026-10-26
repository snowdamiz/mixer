#!/usr/bin/env python3
"""Independent finite source/model audit. Never imports or executes producer code."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import difflib
import hashlib
import itertools
import json
import platform
import random
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROPOSAL = ROOT / 'verification/swift-cache-state-byte-index-proposal'
C3 = ROOT / 'verification/swift-cache-state-implementation/correction-3'
MAX = 2**64 - 1
ABSENT_BYTE = 255

def sha(data): return hashlib.sha256(data).hexdigest()
def write(name, value): (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def identity(path):
    raw=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)), 'bytes':len(raw), 'sha256':sha(raw)}

def seal_check(folder, name, expected, count, size):
    seal=folder/name; raw=seal.read_bytes()
    assert sha(raw)==expected, (seal,sha(raw))
    obj=json.loads(raw); rows=obj.get('members',obj.get('files'))
    assert len(rows)==count and sum(x['bytes'] for x in rows)==size
    for row in rows:
        p=ROOT/row['path']
        if not p.exists(): p=folder/row['path']
        b=p.read_bytes()
        assert len(b)==row['bytes'] and sha(b)==row['sha256'], p
    return {'seal':identity(seal), 'member_count':count, 'member_bytes':size, 'all_members_verified':True}

def extract(text, start, end):
    a=text.index(start); b=text.index(end,a)
    return text[a:b],a,b

def source_checks():
    old=(C3/'source/library/cache_state.rs').read_text()
    new=(PROPOSAL/'source/cache_state.rs.txt').read_text()
    assert sha(old.encode())=='0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
    assert sha(new.encode())=='0b6ab81f1fc65742171b1023d2929e9dc8536d5cb66388ea2aa36109f5fa715d'
    bounds=[
        ('merge','fn merge(', 'fn merge(', '#[cfg(test)]\nstatic COMMIT_FAULT'),
        ('G2','    // Shared one-pass bounded probes;', '    // G2. This lexical shared arena view', '    let body = w[6] as usize;'),
        ('G5','            // The preceding checked base+request guard', '            // G5. Exact prior successful', '            sq(c, 10, mask);')]
    old_mask=old; new_mask=new; rows=[]
    for label,oldstart,newstart,end in bounds:
        a,oa,ob=extract(old,oldstart,end); b,na,nb=extract(new,newstart,end)
        rows.append({'region':label,'old_lines':[old.count('\n',0,oa)+1,old.count('\n',0,ob)],
                     'new_lines':[new.count('\n',0,na)+1,new.count('\n',0,nb)],
                     'old_sha256':sha(a.encode()),'new_sha256':sha(b.encode())})
        old_mask=old_mask.replace(a,'<REVIEWED:'+label+'>\n',1)
        new_mask=new_mask.replace(b,'<REVIEWED:'+label+'>\n',1)
    assert old_mask==new_mask
    cleanup_old=old[old.index('fn cleanup('):]
    cleanup_new=new[new.index('fn cleanup('):]
    assert cleanup_old==cleanup_new
    assert ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='C3/cache_state.rs',tofile='PROPOSED/cache_state.rs'))==(PROPOSAL/'proposed.diff').read_text()
    merge=extract(new,'fn merge(', '#[cfg(test)]\nstatic COMMIT_FAULT')[0]
    # Exact expression bindings, rather than a replay of the producer assembly.
    required=[
        'let (time_bytes, indices) = c.split_at_mut(512);',
        'let (timestamps, _) = time_bytes.as_chunks::<8>();',
        'let mut src = 0;', 'let mut dst = 512;',
        'while width < 64 {','while base < 64 {','while out < end {',
        'let a = indices[src + left];','let b = indices[src + right];',
        'b == u8::MAX','a != u8::MAX',
        'u64::from_le_bytes(timestamps[a as usize])',
        '<= u64::from_le_bytes(timestamps[b as usize])',
        'indices[dst + out] = indices[src + left];',
        'indices[dst + out] = indices[src + right];',
        'left += 1;','right += 1;','out += 1;',
        'let old_src = src;','src = dst;','dst = old_src;','width *= 2;']
    assert all(x in merge for x in required)
    assert merge.count('indices[dst + out] = indices[src +')==2
    probes=extract(new,bounds[1][2],bounds[1][3])[0]
    assert probes.count('index_bytes[512 + slot] = u8::MAX;')==2
    assert 'index_bytes[slot] = if occupied == 1 && pins == 0 { slot as u8 } else { u8::MAX };' in probes
    assert 'timestamp_words[slot] = last_used.to_le_bytes();' in probes
    assert 'timestamp_words[slot] = 0u64.to_le_bytes();' in probes
    prefix=extract(new,bounds[2][2],bounds[2][3])[0]
    assert prefix.index('if slot_byte == u8::MAX')<prefix.index('let slot = slot_byte as u64;')
    assert 'remaining.checked_sub(bytes)' in prefix
    assert 'mask |= 1 << slot;' in prefix and 'destination = slot;' in prefix
    for i in range(16):
        assert cleanup_new.count(f'c[{i*128}..{(i+1)*128}].copy_from_slice(&[0u8; 128]);')==1
    restore_sources=[7729816,7729832,7729840,7729848,7729856,7729864,
                     7729872,7730272,7730280,7730288,7731040,7731048]
    for i,at in enumerate(restore_sources):
        assert cleanup_new.count(f'c[{888+i*8}..{896+i*8}].copy_from_slice(&b[{at}..{at+8}]);')==1
    return {'old_source':identity(C3/'source/library/cache_state.rs'),
            'proposed_source':identity(PROPOSAL/'source/cache_state.rs.txt'),
            'changed_regions_only':rows,'masked_all_other_source_identical':True,
            'G6_body_and_actual_outer_caller_boundary_identical':True,
            'cleanup_and_entire_suffix_sha256':sha(cleanup_old.encode()),
            'exact_twelve_restore_and_sixteen_anonymous_clear_preserved':True,
            'restore_arena_addresses':restore_sources,
            'source_expression_to_independent_model_bindings':required,
            'Rust_compilation_or_borrow_acceptance':False}

class Trace:
    """Selected component model: every operand, result, reference edge explicit."""
    def __init__(self): self.events=[]
    def op(self,*names): self.events.extend(names)
    def value(self,name,target): self.op(f'{name} source -> {target}')
    def binary(self,op,left,right,target):
        self.value(left,op+' left operand');self.value(right,op+' right operand')
        self.op('primitive '+op,op+' result source -> '+target)
    def guard(self,op,left,right):
        self.binary(op,left,right,'condition value')
        self.op('condition source -> if predicate','conditional branch')
    def index(self,name,offset,write=False,slice_receiver=True,byte=True):
        self.binary('+',*offset,name+' received index')
        self.op(name+' receiver reborrow',name+' receiver.data source -> received receiver.data')
        if slice_receiver: self.op(name+' receiver.len source -> received receiver.len')
        self.op(name+' entry control',name+' index -> bounds left',name+' length -> bounds right',
                name+' bounds comparison',name+' bounds branch',
                name+' data -> address operand',name+' index -> scaling operand',
                name+' width1 -> scaling operand',name+' index*1',
                name+' scaled offset -> pointer-add operand',name+' data -> pointer-add operand',name+' address addition',
                name+' address -> returned reference source',name+' indexed loan creation',
                name+' returned reference -> caller received reference',name+' return control')
        if write:
            self.op(name+' received RHS byte -> destination byte scalar store',
                    name+' unit result production',name+' statement continuation')
        else: self.op(name+' received reference dereference -> byte source',name+' byte source -> RHS received value')

def g4_bound():
    read=Trace(); read.index('RHS',('src','selected_side'))
    store=Trace();store.index('LHS',('dst','out'),write=True)
    # The restricted floor drops dynamic receiver length transfers and all
    # size-one scaling detail: no stronger than the selected G6 byte IndexMut
    # template and scalar fixed-array Index20. This is a necessary lower bound,
    # not a conservative impossible-path overestimate.
    read_floor_events=[
        'receiver reborrow','receiver thin pointer transfer','Index entry',
        'received index -> bound operand','length -> bound operand','bounds comparison','bounds branch',
        'pointer -> address operand','index -> scaling operand','element width -> scaling operand','scale',
        'scaled offset -> pointer-add operand','pointer -> pointer-add operand','address formation',
        'address -> returned reference','loan creation','returned reference -> received reference','Index return',
        'reference dereference -> scalar source','scalar source -> RHS received value']
    store_floor_events=[
        'receiver reborrow','receiver thin pointer transfer','IndexMut entry',
        'index -> bound operand','length -> bound operand','bounds comparison','bounds branch',
        'pointer -> address operand','index -> address operand','byte address formation',
        'address -> returned mutable reference','exclusive loan creation','returned reference -> received reference','IndexMut return',
        'received RHS -> byte store','assignment unit production','assignment continuation']
    offset_events=['left source -> + operand','right source -> + operand','primitive +','+ result -> received index']
    assert len(read_floor_events)==20 and len(store_floor_events)==17
    selected_floor_read=len(read_floor_events)+len(offset_events)
    selected_floor_store=len(store_floor_events)+len(offset_events)
    floor=(selected_floor_read+selected_floor_store)*384
    assert (len(read.events),len(store.events))==(25,26)
    complete=Trace()
    complete.guard('<','out','end')
    complete.guard('==','left','mid')
    complete.guard('==','right','end')
    complete.op('selected bool source -> take_left binding','take_left source -> chosen if predicate','chosen-side branch')
    complete.events+=read.events+store.events
    complete.binary('+','selected_side','literal1','selected_side store')
    complete.op('side assignment unit result','side statement continuation')
    complete.binary('+','out','literal1','out store')
    complete.op('out assignment unit result','out statement continuation')
    # Union bound pays both exhaustion guards per output, although first may
    # short circuit. Its cap failure alone would not prove impossibility; the
    # necessary assignment floor above independently proves it.
    rows=[('three initial bindings',3,1),('outer guard including final false',6,7),
          ('base initializer',1,6),('base guard including per-pass final false',6,69),
          ('left/mid/end/right/out initializers',14,63),
          ('output body including both exhaustion guards',len(complete.events),384),
          ('output final false',6,63),('base=end store and unit/continuation',3,63),
          ('swap old/src/dst values and assignment continuations',7,6),
          ('width*=2 operands/result/store/unit/continuation',6,6)]
    total=sum(per*n for _,per,n in rows)
    return {'owner':'G4','cap':768,'producer_claim':{'scalars':11636,'groups':728},
            'selected_model_assignment_necessary_floor':{
                'read_scalars_per_output':selected_floor_read,
                'write_scalars_per_output':selected_floor_store,
                'guaranteed_outputs':384,'scalars':floor,'scalar_groups':(floor+15)//16,
                'excludes_all_loop_exhaustion_choice_pass_setup_and_final_false_work':True,
                'also_omits_dynamic_slice_len_receive_and_size_one_scaling_details':True},
            'complete_conservative_source_upper':{'rows':[
                {'site':label,'scalars_each':per,'occurrences':n,'scalars':per*n} for label,per,n in rows],
                'scalars':total,'scalar_groups':(total+15)//16,'copies':0,
                'claim_exact_maximum':False},
            'RHS_exact_component_events':read.events,'LHS_exact_component_events':store.events,
            'selected_reference_read_floor_events':read_floor_events,
            'selected_reference_write_floor_events':store_floor_events,
            'selected_offset_events':offset_events,
            'upper_output_events':complete.events,
            'necessary_floor_exceeds_cap':(floor+15)//16>768,
            'numeric_ceiling_change_permitted':False}

def merge_source_model(times, eligible):
    # Execute only the finite mathematical source model, never Rust or producer.
    image=bytearray([0x5a])*2048
    for i in range(64):
        image[i*8:i*8+8]=times[i].to_bytes(8,'little')
        image[512+i]=i if i in eligible else 255
        image[1024+i]=255
    pad_before=(image[576:1024],image[1088:1536])
    src,dst,width=0,512,1
    comparisons=0; path_counts=Counter(); emitted=0
    while width<64:
        base=0
        while base<64:
            left=base;mid=base+width;end=base+2*width;right=mid;out=base
            assert end<=64
            while out<end:
                if left==mid: take_left=False;path_counts['left_exhausted']+=1
                elif right==end: take_left=True;path_counts['right_exhausted']+=1
                else:
                    comparisons+=1
                    a=image[512+src+left];b=image[512+src+right]
                    assert a==255 or a<64
                    assert b==255 or b<64
                    take_left=b==255 or a!=255 and int.from_bytes(image[a*8:a*8+8],'little')<=int.from_bytes(image[b*8:b*8+8],'little')
                    path_counts['pair_comparison']+=1
                chosen=left if take_left else right
                assert chosen<(mid if take_left else end)
                image[512+dst+out]=image[512+src+chosen]
                if take_left: left+=1
                else: right+=1
                out+=1;emitted+=1
            base=end
        src,dst=dst,src;width*=2
    assert src==0 and emitted==384
    assert pad_before==(image[576:1024],image[1088:1536])
    return list(image[512:576]),comparisons,dict(path_counts)

def prefix_source_model(order, weights, total, headroom, first_empty):
    remaining=total; mask=0; destination=first_empty
    i=0
    while i<64:
        if remaining<=headroom and destination!=MAX:break
        slot_byte=order[i]
        if slot_byte==255:break
        slot=slot_byte
        if remaining<weights[slot]: return {'refusal':13}
        remaining-=weights[slot];mask|=1<<slot;destination=slot;i+=1
    return {'remaining':remaining,'mask':mask,'destination':destination,
            'feasible':destination!=MAX and remaining<=headroom,'selected_count':i}

def prefix_oracle(eligible,times,weights,total,headroom,first_empty):
    ranked=sorted(eligible,key=lambda i:(times[i],i))
    # Choose the shortest prefix satisfying both destination and headroom, or
    # the complete available prefix. Enumeration is independent of the loop.
    candidates=[]
    for k in range(len(ranked)+1):
        selected=ranked[:k]; remaining=total-sum(weights[x] for x in selected)
        destination=selected[-1] if selected else first_empty
        feasible=destination!=MAX and remaining<=headroom
        candidates.append({'remaining':remaining,'mask':sum(1<<x for x in selected),
                           'destination':destination,'feasible':feasible,'selected_count':k})
        if feasible:return candidates[-1]
    return candidates[-1]

def models():
    rng=random.Random(0x1D3EED)
    sort_count=0;prefix_count=0;max_cmp=0;witness=None
    cases=[]
    # Exhaustive small order/tie patterns and eligibility at both ends, including
    # actual slot63. Other slots are absent; no shortened merge is substituted.
    selected_slots=[0,1,2,63]
    for vals in itertools.product((0,2**63,MAX),repeat=4):
        times=[9]*64
        for i,x in zip(selected_slots,vals):times[i]=x
        for mask in range(16):cases.append((times,{i for bit,i in enumerate(selected_slots) if mask>>bit&1}))
    for configured in range(1,65):
        for mode in range(5):
            times=([int(f'{i:06b}'[::-1],2) for i in range(64)] if mode==0 else
                   [MAX]*64 if mode==1 else [2**63+i%3 for i in range(64)] if mode==2 else
                   list(reversed(range(64))) if mode==3 else [rng.getrandbits(64) for _ in range(64)])
            for count in range(configured+1):
                eligible=set(rng.sample(range(configured),count))
                cases.append((times,eligible))
    for times,eligible in cases:
        actual,cmp,path=merge_source_model(times,eligible)
        expected=sorted(eligible,key=lambda i:(times[i],i))+[255]*(64-len(eligible))
        assert actual==expected
        sort_count+=1
        if cmp>max_cmp:max_cmp=cmp;witness={'times':times,'eligible':sorted(eligible),'path_counts':path}
        weights={i:rng.randrange(1,65) for i in range(64)}
        total=sum(weights.values())
        for empty in (MAX,63):
            for headroom in (0,total//2,total,total+1):
                a=prefix_source_model(actual,weights,total,headroom,empty)
                o=prefix_oracle(eligible,times,weights,total,headroom,empty)
                assert a==o,(a,o)
                prefix_count+=1
    assert max_cmp==321
    # Deliberate corrupted total exercises the unchanged checked-sub refusal.
    assert prefix_source_model([63]+[255]*63,{63:2},1,0,MAX)=={'refusal':13}
    addresses=0
    for row in range(64):
        for base,stride,fields in ((7680000,64,8),(7684096,48,6)):
            for field in range(fields):
                index=base//8+row*(stride//8)+field
                assert index*8==base+row*stride+field*8
                assert index<8388608//8;addresses+=1
    cleanup_count=0
    for configured in range(1,65):
        raw=bytearray(rng.getrandbits(8) for _ in range(2048))
        padding=(raw[576:1024],raw[1088:1536])
        for slot in range(64):
            raw[slot*8:slot*8+8]=(MAX if slot<configured else 0).to_bytes(8,'little')
            raw[512+slot]=slot if slot<configured else 255
            raw[1024+slot]=255
        assert padding==(raw[576:1024],raw[1088:1536])
        payload=bytes(rng.getrandbits(8) for _ in range(96))
        for start in range(0,2048,128):raw[start:start+128]=bytes(128)
        for i in range(12):raw[888+i*8:896+i*8]=payload[i*8:(i+1)*8]
        oracle=bytearray(2048);oracle[888:984]=payload
        assert raw==oracle;cleanup_count+=1
    return {'source_model_only':True,'sort_cases':sort_count,'prefix_cases':prefix_count,
            'maximum_comparisons':max_cmp,'moves_per_sort':384,'attaining_witness':witness,
            'arena_address_cases':addresses,'zero_full_pinned_all_tail_unsigned_MAX_ties_slot63_covered':True,
            'candidate_padding_and_cleanup_cases':cleanup_count,
            'checked_sub_underflow_refusal_covered':True,
            'Rust_or_compiler_execution':False}

def main():
    receipt={'at':datetime.now(timezone.utc).isoformat(),'python':sys.version,
             'command':'python3 -B verification/swift-cache-state-byte-index-independent/review.py',
             'source_only':True,'product_or_compiler_or_native_or_capture_execution':False,
             'producer_script_import_or_execution':False,'frozen_packet_mutation':False}
    receipt['custody']=[
        seal_check(PROPOSAL,'seal.json','d4cad24a902d5a8551fa51a93b445382be59027e129ac2f65408bd22666ae736',63,4046162),
        seal_check(C3,'candidate-repo-seal.json','7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f',570,15387058),
        seal_check(ROOT/'verification/swift-cache-state-g6-complete','seal.json','c806b2967e37978403641c0172f3d70013b1e74c0d28128236f26fb618812597',14,565517),
        seal_check(ROOT/'verification/swift-cache-state-g6-complete-independent','seal.json','2813d055b2350902dd3b5deeab8c3a34a662d30d5ecdf25974fc13c624c44c73',11,73343)]
    selection=ROOT/'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json'
    assert identity(selection)['sha256']=='ea00518ce5033b4651460763f1c92533d024fee32a73b182d1684afa65ef80e1'
    receipt['G6_root_selected_component_model']=identity(selection)
    receipt['binding_inputs']=[identity(ROOT/p) for p in (
        'AGENTS.md',
        'docs/swift-semantic-adapter-prerequisite.md',
        'docs/swift-cache-state-clear128-selection.md',
        'docs/swift-cache-state-g6-accounting-selection.md',
        'verification/swift-cache-state-g6-complete/source-model.json',
        'verification/swift-cache-state-g6-complete/ledger.py',
        'verification/swift-cache-state-g6-complete-independent/audit.py')]
    write('custody.json',receipt)
    write('source-checks.json',source_checks())
    write('G4-independent-bound.json',g4_bound())
    write('model-results.json',models())
    print(json.dumps({'custody':'passed','source_seams':'passed','models':'passed',
          'G4_selected_necessary_floor':g4_bound()['selected_model_assignment_necessary_floor'],
          'recommendation':'required revision; unchanged G4 cap768 cannot fund this source under selected component grammar',
          'implementation_or_compiler_acceptance':False},indent=2))

if __name__=='__main__':main()
