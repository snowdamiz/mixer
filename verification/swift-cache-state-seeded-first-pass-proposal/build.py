#!/usr/bin/env python3
"""Finite source/primitive proposal. Never import, compile, or execute Mixer Rust."""
from __future__ import annotations
import datetime
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-cache-state-fixed-array-merge-proposal'
C3 = ROOT / 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs'
BASE = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
OLD_SEAL = '7617d00155a50807ecdd92a4841ab51225fee25a4f116f98c34341eaba3a30d6'
CAPS = {'G2': 2560, 'G3': 2568, 'G4': 768, 'G5': 640}

def sha(b): return hashlib.sha256(b).hexdigest()
def dump(name, value): (HERE/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def info(p):
    b = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(b), 'sha256': sha(b)}
def scalar(*names): return [{'kind': 'scalar', 'bytes': 0, 'operation': n} for n in names]
def copy(n, width):
    assert 0 < width <= 128
    return [{'kind': 'copy', 'bytes': width, 'operation': n}]
def v(n, target): return scalar(f'{n} value source -> {target}')
def k(n, target): return scalar(f'literal {n} source -> {target}')
def field(n, target):
    return scalar(f'{n} parent pointer -> field projection operand', f'{n} field address projection',
                  f'{n} field source -> {target}')
def store(n): return scalar(f'{n} parent pointer -> destination projection operand', f'{n} destination field address projection')
def binary(op, a, b, target): return a+b+scalar(f'primitive {op}', f'{op} result source -> {target}')
def cast(ty, a, target): return a+scalar(f'primitive cast {ty}', f'{ty} result source -> {target}')
def guard(a): return a+scalar('condition result source -> if predicate', 'if control branch')

def index(base, expr, target, *, byte=False, fat=False, projected=False, mutable=False):
    # The selected Index20 core, with one actual length-field transfer for a
    # fat slice. Fixed length remains a predicate operand. No scaling elision.
    ops = scalar(f'{base} parent pointer -> field projection', f'{base} array-reference field address projection') if projected else []
    ops += expr
    core = scalar(f'{base} Index receiver borrow', f'{base} pointer -> Index received receiver')
    if fat: core += scalar(f'{base} len -> Index received receiver.len')
    core += scalar('Index entry control', 'received index -> upper predicate left',
        f'{"received" if fat else "fixed"} length -> upper predicate right', 'index<length predicate',
        'index check branch', 'received pointer -> address operand', 'received index -> scaling operand',
        f'element width{1 if byte else 8} -> scaling operand', 'index*width',
        'scaled offset -> pointer-add operand', 'received pointer -> pointer-add operand', 'element address formation',
        'element address -> returned reference source', 'indexed reference loan creation',
        'returned reference -> caller received reference', 'Index return control')
    core += scalar('received reference dereference -> scalar source', f'indexed scalar source -> {target}') if byte else scalar(
        'received array reference -> dereference address operand',
        f'dereferenced array {"destination" if mutable else "source"} address projection')
    assert len(core) == 20 + int(fat)
    return ops+core

def le_load(base, expr, target, **kwargs):
    return index(base, expr, 'LE received array8', **kwargs)+copy(
        f'{base} complete indexed array8 source -> from_le_bytes received array8', 8)+scalar(
        'from_le_bytes entry control', 'u64 from_le_bytes conversion',
        'converted word -> from_le_bytes designated return source', 'from_le_bytes return control',
        f'from_le_bytes returned word -> {target}')

def old_head(side):
    ops = index('s.indices', field(f's.{side}p', 'Index received index'), 'index binding', byte=True, projected=True)
    conv = cast('u16', v('index', 'cast received operand'), f's.{side}i')
    ops += conv[:-1]+store(f's.{side}i')+conv[-1:]
    ops += guard(binary('!=', v('index', '!= left'), k('u8::MAX', '!= right'), 'condition source'))
    ops += index('s.timestamps', cast('usize', v('index', 'cast received operand'), 'Index received index'),
                 'LE received array8', projected=True)
    ops += copy('s.timestamps complete indexed array8 -> from_le_bytes received array8', 8)
    ops += scalar('from_le_bytes entry control', 'u64 from_le_bytes conversion',
                  'converted word -> from_le_bytes designated return source', 'from_le_bytes return control')
    ops += store(f's.{side}t')+scalar(f'from_le_bytes returned word -> s.{side}t')
    return ops

def old_choice(right_tail, left_eligible):
    ops = guard(binary('>=', field('s.ri', '>= left'), k('255', '>= right'), 'condition source'))
    if right_tail:
        ops += binary('!=', field('s.li', '!= left'), k('256', '!= right'), 'take_left binding')
    else:
        ops += binary('<', field('s.li', '< left'), k('255', '< right'), 'and left source')
        ops += scalar('and short-circuit branch')
        ops += binary('<=', field('s.lt', '<= left'), field('s.rt', '<= right'), 'take_left binding') if left_eligible else scalar(
            'short-circuited false source -> take_left binding')
    return ops+guard(v('take_left', 'condition source'))

def old_emit(side):
    return cast('u8', field(f's.{side}i', 'cast received operand'), 'out binding')+store(f's.{side}p')+binary(
        '+', field(f's.{side}p', '+ left'), k('1', '+ right'), f's.{side}p')+guard(binary(
        '<', field(f's.{side}p', '< left'), field(f's.{side}e', '< right'), 'condition source'))

def rangeview(base, start, end, exclusive=False):
    return k(start, 'Range.start source')+k(end, 'Range.end source')+scalar(
        'Range.start -> Index received start', 'Range.end -> Index received end',
        f'{base} Index receiver borrow creation', f'{base} data -> Index received receiver.data',
        f'{base} len -> Index received receiver.len', 'Index entry control',
        'start -> ordered predicate left', 'end -> ordered predicate right', 'start<=end predicate', 'ordered branch',
        'end -> upper predicate left', 'received len -> upper predicate right', 'end<=len predicate', 'upper branch',
        'base data -> address operand', 'start -> address operand', 'view address formation',
        'end -> length subtraction left', 'start -> length subtraction right', 'length=end-start',
        'address result -> returned view.data', 'length result -> returned view.len',
        f'projected {"exclusive" if exclusive else "shared"} view loan creation',
        'returned view.data -> caller received view.data', 'returned view.len -> caller received view.len', 'Index return control')

def output_copy(dst):
    return rangeview('indices', dst, dst+64, True)+scalar(
        'copy receiver reborrow', 'destination view.data -> copy received receiver.data',
        'destination view.len -> copy received receiver.len', 'output array address formation',
        'output array reborrow creation', 'output array address -> slice.data source',
        'output array length64 -> slice.len source', 'source slice.data -> copy received source.data',
        'source slice.len -> copy received source.len', 'copy entry control',
        'copy receiver.len -> equality left', 'copy source.len -> equality right',
        'source/destination length equality', 'copy length check branch')+copy(
        'actual output64 source -> existing Candidate destination64', 64)+scalar(
        'copy unit/control returned -> caller', 'unit discard and statement continuation')

def seeded_head(slot):
    mask = f'0x{1 << slot:016x}u64'
    ops = guard(binary('!=', binary('&', v('eligibility', '& left'), k(mask, '& right'), '!= left'),
                       k('0', '!= right'), 'condition source'))
    ops += k(f'{slot}u8', 'left/right binding')
    ops += le_load('timestamps', k(f'{slot}usize', 'Index received index'), 'lt/rt binding')
    return ops

def seeded_choice():
    return guard(binary('==', v('right', '== left'), k('u8::MAX', '== right'), 'condition source'))+binary(
        '!=', v('left', '!= left'), k('u8::MAX', '!= right'), 'and left source')+scalar(
        'and short-circuit branch')+binary('<=', v('lt', '<= left'), v('rt', '<= right'), 'take_left binding')+guard(
        v('take_left', 'condition source'))

def seeded_source(old):
    # Width1 has statically known singleton run order. No initial A seed is read.
    pre = old[:old.index('    {\n        let output = {')]
    pre = pre.replace('// UNSELECTED, FAILED SOURCE-ONLY FIXED-ARRAY REFINEMENT. Never compiled or run.',
                      '// UNSELECTED SOURCE-ONLY SEEDED WIDTH1 PROPOSAL. Never compiled or run.')
    pre = pre.replace('    let (time_bytes, indices) = c.split_at_mut(512);',
                      '    let eligibility = ld(c, 640);\n    let (time_bytes, indices) = c.split_at_mut(512);')
    lines = ['    {', '        let output = {', '            let mut second = u8::MAX;', '            [']
    positions = []
    for slot in range(0, 64, 2):
        positions.append({'pair': slot//2, 'left_slot': slot, 'right_slot': slot+1,
                          'left_mask': f'0x{1<<slot:016x}', 'right_mask': f'0x{1<<(slot+1):016x}',
                          'first_line_in_width1': len(lines)+1})
        lines += ['                {', f'                    // width1 pair{slot//2}; literals are actual source operands.',
                  f'                    let left = if eligibility & 0x{1<<slot:016x}u64 != 0 {{ {slot}u8 }} else {{ u8::MAX }};',
                  f'                    let right = if eligibility & 0x{1<<(slot+1):016x}u64 != 0 {{ {slot+1}u8 }} else {{ u8::MAX }};',
                  f'                    let lt = u64::from_le_bytes(timestamps[{slot}usize]);',
                  f'                    let rt = u64::from_le_bytes(timestamps[{slot+1}usize]);',
                  '                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };',
                  '                    if take_left { second = right; left } else { second = left; right }',
                  '                },', '                { second },']
    lines += ['            ]', '        };', '        indices[512..576].copy_from_slice(&output);', '    }']
    # The five remaining pass bodies are byte-identical to the failed packet.
    marker = '            let source: &[u8; 64] = indices[512..576].first_chunk::<64>().expect("index64");'
    marker_at = old.index(marker)
    suffix_at = old.rfind('    {\n        let output = {', 0, marker_at)
    assert suffix_at > 0
    return pre+'\n'.join(lines)+'\n'+old[suffix_at:], positions, old[suffix_at:]

class Trace:
    def __init__(self): self.events=[]; self.segments=[]
    def add(self, owner, site, ops):
        first = len(self.events)
        for n, op in enumerate(ops): self.events.append(dict(op, id=f'{owner}.{len(self.events):06}', owner=owner, site=site, local_ordinal=n))
        self.segments.append({'owner': owner, 'site': site, 'first': first, 'count': len(ops)})
    def totals(self):
        out = {}
        for owner in ['G2', 'G3', 'G4']:
            s=sum(e['owner']==owner and e['kind']=='scalar' for e in self.events)
            c=sum(e['owner']==owner and e['kind']=='copy' for e in self.events)
            out[owner]={'scalars':s, 'copies':c, 'scalar_groups':(s+15)//16,
                        'groups':(s+15)//16+c, 'cap':CAPS[owner]}
        return out

def offset(base, idx, stride, extra=0, converted=False):
    i=cast('usize', v(idx,'cast operand'), '* left') if converted else v(idx,'* left')
    expr=binary('+',v(base,'+ left'),binary('*',i,k(stride,'* right'),'+ right'),'Index received index')
    return binary('+',expr,k(extra,'+ right'),'Index received index') if extra else expr

def g2_templates():
    resident=[]
    for n in [0,1,2,3,6,7,4]:
        resident+=le_load('arena_words',offset('resident_word_base','slot',8,n),f'resident field{n} operand/binding',fat=True)
    timestamp=index('timestamp_words',v('slot','Index received index'),'indexed destination array8',fat=True,mutable=True)+scalar(
        'last_used source -> to_le_bytes received self', 'to_le_bytes entry control', 'u64 to_le_bytes conversion',
        'to_le_bytes return control')+copy('to_le_bytes complete returned array8 -> indexed timestamp destination array8',8)
    checked=v('total','checked_add received self')+v('bytes','checked_add received argument')+scalar(
        'checked_add entry control','checked addition arithmetic','overflow predicate','overflow branch',
        'Some tag source construction','arithmetic result -> Some payload source')+copy(
        'complete Option<u64>16 source -> checked_add received Option16',16)+scalar(
        'checked_add return control','received Option.tag -> pattern operand','Some pattern predicate',
        'pattern control branch','received Some payload -> sum binding')
    pin=le_load('arena_words',offset('pin_word_base','pin',6),'entry binding',fat=True)
    pin+=le_load('arena_words',offset('pin_word_base','pin',6,1),'nonce binding',fat=True)
    pin+=le_load('arena_words',offset('resident_word_base','entry',8,converted=True),'occupied comparison operand',fat=True)
    pin+=le_load('arena_words',offset('resident_word_base','entry',8,3,converted=True),'pins comparison operand',fat=True)
    # Fixed array w:&[u64;16], not a fat slice or an array8 payload. Its scalar
    # core still has20 operations and width8 scaling, then actual == operands.
    release=index('w',k('1','Index received index'),'== left',byte=False)
    release[-2:]=scalar('received reference dereference -> scalar source','indexed scalar source -> == left')
    release+=k('12','== right')+scalar('primitive ==','== result -> and-left source',
        'and short-circuit false branch','short-circuited false source -> if predicate','if control branch')
    return {'resident7_loads':resident,'timestamp_assignment':timestamp,'successful_checked_add':checked,
            'pin4_loads':pin,'release_kind_short_circuit':release}

def merge_witness(t):
    times=[int(format(i,'06b')[::-1],2) for i in range(64)]
    indices=[]
    t.add('G4','width1.second-initializer',k('u8::MAX','second binding'))
    for base in range(0,64,2):
        for slot in [base,base+1]: t.add('G3',f'width1.pair{base//2}.head{slot}',seeded_head(slot))
        t.add('G3',f'width1.pair{base//2}.choice',seeded_choice())
        t.add('G4',f'width1.pair{base//2}.two-output-values',v('right','second binding')+v('left','first output element')+v('second','second output element'))
        indices += sorted([base,base+1],key=lambda i:(times[i],i))
    t.add('G4','width1.output-constructor',copy('array64 constructor -> received output64',64))
    t.add('G4','width1.output-copy',output_copy(512))
    passes=[{'width':1,'comparisons':32,'timestamp_loads':64,'outputs':64}]
    for p in range(1,6):
        width=1<<p; src,dst=(0,512) if p%2==0 else (512,0)
        t.add('G4',f'p{p}.source-range',rangeview('indices',src,src+64))
        out=[]; comparisons=loads=exhaustions=0
        for base in range(0,64,2*width):
            if base:
                for name,n in [('lp',base),('le',base+width),('rp',base+width),('re',base+2*width)]:
                    t.add('G4',f'p{p}.run{base}.reset-{name}',store('s.'+name)+k(n,'s.'+name))
            pos={'l':base,'r':base+width}; end={'l':base+width,'r':base+2*width}; h={}; stamps={}
            def load(side):
                nonlocal loads
                h[side]=indices[pos[side]]; stamps[side]=times[h[side]]; loads+=1
                t.add('G3',f'p{p}.out{len(out)}.load-{side}',old_head(side))
            load('l'); load('r')
            for _ in range(2*width):
                if h['l']!=256 and h['r']!=256: comparisons+=1
                right_tail=h['r']>=255; left_eligible=h['l']<255
                take=h['l']!=256 if right_tail else left_eligible and stamps['l']<=stamps['r']
                t.add('G3',f'p{p}.out{len(out)}.choice',old_choice(right_tail,left_eligible))
                side='l' if take else 'r'; emitted=h[side]
                t.add('G4',f'p{p}.out{len(out)}.emit',old_emit(side))
                pos[side]+=1
                if pos[side]<end[side]: load(side)
                else:
                    h[side]=256; exhaustions+=1
                    t.add('G3',f'p{p}.out{len(out)}.exhausted',store('s.'+side+'i')+k(256,'s.'+side+'i'))
                t.add('G4',f'p{p}.out{len(out)}.result',v('out','inline block result -> output element'))
                out.append(emitted)
        t.add('G4',f'p{p}.constructor',copy('array64 constructor -> received output64',64))
        t.add('G4',f'p{p}.output-copy',output_copy(dst))
        indices=out; passes.append({'width':width,'comparisons':comparisons,'timestamp_loads':loads,
                                   'outputs':64,'exhaustions':exhaustions})
    assert indices==sorted(range(64),key=lambda i:(times[i],i))
    return {'name':'all64 eligible six-bit reversal timestamps','timestamps':times,'eligibility_mask':(1<<64)-1,
            'output':indices,'passes':passes,'owner_maxima_not_one_G2_G3_joint_path':True}

def main():
    assert sha(C3.read_bytes())==BASE
    assert sha((OLD/'seal.json').read_bytes())==OLD_SEAL
    seal=json.loads((OLD/'seal.json').read_text())
    assert seal['member_count']==18 and seal['member_bytes']==2799286
    for member in seal['members']: assert info(ROOT/member['path'])==member
    inputs=[C3,ROOT/'AGENTS.md',ROOT/'docs/swift-semantic-adapter-prerequisite.md',
        ROOT/'docs/swift-cache-state-g6-accounting-selection.md',ROOT/'verification/swift-cache-state-g6-complete/ledger.py',
        ROOT/'verification/swift-cache-state-g6-complete-independent/receiver-correction.json',
        ROOT/'verification/swift-cache-state-byte-index-independent/ownership-addendum.json',OLD/'seal.json']
    inputs += [ROOT/m['path'] for m in seal['members']]
    bindings=[info(p) for p in inputs]
    dump('input-bindings.json',{'schema':1,'inputs':bindings,'old_all18_members_verified':True,
        'old_member_bytes':2799286,'input_tree_digest':sha(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()),
        'input_code_imported_or_executed':False})
    merge,pairs,retained=seeded_source((OLD/'source/merge.rs.txt').read_text())
    (HERE/'source/merge.rs.txt').write_text(merge)
    candidate=(OLD/'source/cache_state.rs.txt').read_text()
    oldmerge=(OLD/'source/merge.rs.txt').read_text()
    assert candidate.count(oldmerge)==1
    candidate=candidate.replace(oldmerge,merge)
    original=C3.read_text()
    candidate=candidate.replace('        let mut slot = 0;','        let mut eligibility = 0u64;\n        let mut slot = 0;',1)
    candidate=candidate.replace('            index_bytes[slot] = if occupied == 1 && pins == 0 { slot as u8 } else { u8::MAX };\n            index_bytes[512 + slot] = u8::MAX;',
        '            if occupied == 1 && pins == 0 { eligibility |= 1u64 << slot; }',1)
    candidate=candidate.replace('            index_bytes[slot] = u8::MAX;\n            index_bytes[512 + slot] = u8::MAX;\n','',1)
    needle='            pin += 1;\n        }\n    }\n    if release_nonce_matches'
    replacement='            pin += 1;\n        }\n        // Unselected scratch amendment: original bytes640..648, outside A/B64.\n        index_bytes[128..136].copy_from_slice(&eligibility.to_le_bytes());\n    }\n    if release_nonce_matches'
    assert candidate.count(needle)==1
    candidate=candidate.replace(needle,replacement)
    (HERE/'source/cache_state.rs.txt').write_text(candidate)
    (HERE/'proposed.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),
        fromfile='FROZEN_C3/cache_state.rs',tofile='UNSELECTED_FAILED_SEEDED_FIRST_PASS/cache_state.rs')))
    marker='            sq(c, 10, mask);'
    assert original[original.index('fn cleanup('):]==candidate[candidate.index('fn cleanup('):]
    assert original[original.index(marker):]==candidate[candidate.index(marker):]
    event='    let body = w[6] as usize;'; call='            merge(c);'
    assert original[original.index(event):original.index(call)]==candidate[candidate.index(event):candidate.index(call)]
    assert original[original.index(call):original.index('            // The preceding checked base+request guard')]==candidate[candidate.index(call):candidate.index('            // G5.')]
    dump('source-assembly.json',{'schema':1,'base_sha256':BASE,'proposed_sha256':sha(candidate.encode()),
        'merge_sha256':sha(merge.encode()),'retained_five_pass_suffix_sha256':sha(retained.encode()),
        'retained_five_pass_suffix_byte_identical':True,'cleanup_and_suffix_byte_identical':True,
        'cleanup_and_suffix_sha256':sha(original[original.index('fn cleanup('):].encode()),
        'G6_post_prefix_suffix_byte_identical':True,'G6_post_prefix_sha256':sha(original[original.index(marker):].encode()),
        'G6_four_caller_only_operations_unchanged':True,'G6_event_staging_and_merge_call_identical':True,
        'G5_source_ideas_retained_without_numeric_acceptance':True,'compiled_or_executed':False})
    dump('layout-amendment.json',{'schema':1,'selected':False,'Candidate_bytes':2048,
        'original_scratch_0_through_1535_only':True,'timestamps':{'offset':0,'bytes':512},
        'A64':{'offset':512,'bytes':64},'B64':{'offset':1024,'bytes':64},
        'eligibility_mask':{'offset':640,'bytes':8,'producer':'actual G2 occupied==1 && pins==0; dynamic1u64<<slot primitive; zero initially',
                            'consumer':'ld(c,640) before width1; explicit64 constant masks; no index A read before overwrite'},
        'unused_original_scratch_bytes_are_not_new_capacity':True,
        'rows_and_scalars_1536_plus_unchanged':True,'cleanup_unchanged':True,
        'width1_output':'B1024','remaining_pass_outputs':['A512','B1024','A512','B1024','A512'],
        'full_timestamp_MAX_preserved':True,'ineligible_or_tail_index':'u8::MAX255','exhausted_head_only':'u16 256',
        'no_initial_A_or_B_seeding':True,'control_addition_cap':1280,'wire_addition_cap':256,
        'role_union_cap':29344,'role_union_or_layout_fit_verified':False,
        'new_owners_proposed_only':['G2 eligibility u64 source8, update operands and returned array8',
            'G3 received eligibility u64 via existing ld/call places','G3 width1 lexical left/right u8,lt/rt u64,take_left bool',
            'G4 second u8, array64 constructor source64 and received output64'],
        'complete_affected_lifetime_and_full_role_ledger':'not built after G2 necessary obstruction'})
    dump('expansion.json',{'schema':1,'strategy':'all source-written, no Rust macro or new helper',
        'width1_pair_count':32,'width1_output_count':64,'width1_constant_mask_count':64,'width1_pairs':pairs,
        'later_source_written_emit_blocks':320,'remaining_five_passes_identical':True,
        'source_derived_mask_not_authority_boolean':True,'actual_dynamic_mask_producer_shift_retained':True})

    templates=g2_templates()
    templates.update({'old_eligible_head':old_head('l'),'old_pair_choice':old_choice(False,True),
        'old_tail_choice':old_choice(True,True),'old_left_exhausted_choice':old_choice(False,False),
        'old_emit':old_emit('l'),'seeded_head0':seeded_head(0),'seeded_choice':seeded_choice(),
        'output_copy':output_copy(512)})
    counts={name:{'scalars':sum(x['kind']=='scalar' for x in ops),'copies':sum(x['kind']=='copy' for x in ops)} for name,ops in templates.items()}
    assert counts['resident7_loads']=={'scalars':249,'copies':7}
    assert counts['timestamp_assignment']=={'scalars':26,'copies':1}
    assert counts['successful_checked_add']=={'scalars':13,'copies':1}
    assert counts['pin4_loads']=={'scalars':142,'copies':4}
    assert counts['release_kind_short_circuit']=={'scalars':27,'copies':0}
    assert counts['old_eligible_head']=={'scalars':68,'copies':1}
    assert counts['seeded_head0']=={'scalars':36,'copies':1}
    assert counts['seeded_choice']=={'scalars':18,'copies':0}
    dump('component-templates.json',{'schema':1,'grammar':'selected Trace.e/Index20/full array and Option source->received model',
        'no_primitive_or_operand_discount':True,'fixed_array_Index_core_scalars':20,'fat_slice_Index_core_scalars':21,
        'full_Option16_rule':'Each actual Option<u64>/Option<usize> source->received is a complete16B copy, including finalNone where present.',
        'timestamp_assignment':'one complete returned array8 -> indexed destination8 copy; no invented second temporary',
        'source_and_received_are_distinct_places':True,'counts':counts,'templates':templates})
    trace=Trace()
    for slot in range(64):
        for name in ['resident7_loads','timestamp_assignment','successful_checked_add']:
            trace.add('G2',f'AcquireBegin.resident{slot}.{name}',templates[name])
    for pin in range(64):
        for name in ['pin4_loads','release_kind_short_circuit']:
            trace.add('G2',f'AcquireBegin.pin{pin}.{name}',templates[name])
    witness=merge_witness(trace)
    totals=trace.totals()
    assert totals['G2']=={'scalars':29248,'copies':832,'scalar_groups':1828,'groups':2660,'cap':2560}
    assert totals['G3']['groups']<=2568 and totals['G4']['groups']<=768
    positive_g2=['all loop conditions/advances and final false exits','all ordinary resident and pin validity guards outside counted release-kind condition',
        'all resident_pins/live_tokens/count/found updates','all mask initialization/eligibility checks/update/shift and complete mask store',
        'all as_chunks/split tuples, fixed-array/slice views, Region constants and casts',
        'all post-probe totals/pin checks, refusal/return/reply boundaries','all tail timestamp stores on shorter slot configurations']
    positive_merge=['mask ld helper full range/first_chunk/expect/array and scalar transfers',
        'split_at_mut/as_chunks/full tuple source/received and7 first_chunk/expect view construction boundaries',
        'five complete cursor source/received constructors and field operands','inline block statement units/continuations',
        'callee merge implicit unit construction and return (G4); caller four operations stayG6',
        'all affected G5 full Option16/prefix/tail/refusal work']
    dump('necessary-bound.json',{'schema':1,'result':'FAIL STOP: actual-source G2 necessary subtrace exceeds cap',
        'owner':'G2','cap':2560,'necessary_scalars':29248,'necessary_complete_copies':832,
        'scalar_groups':1828,'necessary_groups':2660,'over_cap':100,'all64_resident_and_pin_iterations':True,
        'formula_scalars':'64*(249+26+13+142+27)','formula_copies':'64*(7+1+1+4)',
        'actual_path':'AcquireBegin1;64 occupied residents each pins1;64 live pins entry0..63 nonce1..64; nextnonce65; no release-kind RHS',
        'excluded_positive_work':positive_g2,'not_universal_impossibility_proof':True,
        'initial_merge_subtrace_under_caps_but_not_upper':{'G3':totals['G3'],'G4':totals['G4']},
        'complete_G2_G3_G4_G5_upper_ledger_built':False,'reason_no_complete_upper':'G2 necessary obstruction already proves rejection; no complete all-group pass can follow from this source',
        'no_cap_reassignment_or_owner_spare':True})
    dump('g2-witness.json',{'schema':1,'kind':1,'label':'finite valid-state source obstruction, no Rust execution or real profile claim',
        'fixture_config':{'slots':64,'pins':64,'entry':1,'base':0,'capacity':128},
        'residents':[{'slot':i,'occupied':1,'function':i,'bytes':1,'pins':1,'last_used':i,'generation':0,'reserved':0} for i in range(64)],
        'pins':[{'pin':i,'entry':i,'nonce':i+1} for i in range(64)],
        'prior':{'resident_count':64,'resident_bytes':64,'pin_count':64,'next_nonce':65,'idle':True},
        'record':{'kind':1,'requested_function':80000,'operation':65},
        'reachability_argument':'64 distinct successful builds/publications held pinned, then idle AcquireBegin; entry capacity1,total64,capacity128 permit each prior build. AcquireBegin may name undefined function and does not require a free token; Lookup later refuses.',
        'eligibility_mask':0,'all_checked_add_successful':True,'all_live_pin_backlinks_valid':True,
        'w1_eq12_is_false_all64':True,'this_is_not_the_all_eligible_merge_witness':True})
    dump('merge-witness.json',dict(witness,schema=1,counted_subtrace_totals={'G3':totals['G3'],'G4':totals['G4']},
        excluded_positive_work=positive_merge,whole_G3_G4_upper_or_implementation_accepted=False))
    groups=[]
    for owner in ['G2','G3','G4']:
        ids=[e['id'] for e in trace.events if e['owner']==owner and e['kind']=='scalar']
        groups += [{'owner':owner,'kind':'scalar','events':ids[n:n+16]} for n in range(0,len(ids),16)]
        groups += [{'owner':owner,'kind':'copy','events':[e['id']],'bytes':e['bytes']} for e in trace.events if e['owner']==owner and e['kind']=='copy']
    assert len({n for g in groups for n in g['events']})==len(trace.events)
    packet={'schema':1,'scope':'finite necessary subtraces only, group maxima use separate valid paths',
            'events':trace.events,'segments':trace.segments,'groups':groups,'totals':totals}
    raw=json.dumps(packet,sort_keys=True,separators=(',',':')).encode()
    (HERE/'finite-subtrace-ledger.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    dump('subtrace-summary.json',{'schema':1,'totals':totals,'event_count':len(trace.events),'bytes_decompressed':len(raw),
        'sha256_decompressed':sha(raw),'all_counted_events_grouped_once':True,'scalar_group_max':16,'copy_max_bytes':64,
        'full_upper_ledger':False,'G2_positive_omissions':positive_g2,'G3_G4_positive_omissions':positive_merge})
    dump('run.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[sys.executable,'-B',str(HERE/'build.py')],'python':sys.version,'platform':platform.platform(),
        'source_revision':BASE,'input_tree_digest':sha(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()),
        'scope':'source custody/assembly and finite authored-source arithmetic only',
        'result':'FAIL STOP G2 lower bound2660>2560 by100; no complete upper/role ledger claimed',
        'compiler_product_runtime_native_UI_capture_process_inventory_Git_hosted':False,
        'product_frozen_packets_root_metadata_mutated':False,'cleanup':'No instance, build directory or runtime process started; only new owned source packet written.',
        'implementation_or_GA_accepted':False})
    print(json.dumps({'result':'FAIL STOP G2 obstruction','totals':totals,'source_sha256':sha(candidate.encode()),
        'complete_upper_or_role_union_accepted':False,'compiler_or_product_runtime_executed':False},indent=2))

if __name__=='__main__': main()
