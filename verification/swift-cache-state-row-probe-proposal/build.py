#!/usr/bin/env python3
"""Own source/math only. No Rust, compiler, hosted harness, or product execution."""
from __future__ import annotations
import datetime, difflib, gzip, hashlib, json, platform, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SEED=ROOT/'verification/swift-cache-state-seeded-first-pass-proposal'
C3=ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs'
SEED_SOURCE='d8ee1d1e4f802a96c69291cc2eabd4de71f9b3b8b47850cd48563a8fb5058186'
SEED_SEAL='b27e1ee4d0a55d35ac6fff5c1d7d7256019e4caea3b17dce000a77021b0475f1'
CAP=2560
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(n,x): (HERE/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def ops(*names): return [{'kind':'scalar','bytes':0,'operation':n} for n in names]
def cp(n,w):
    assert 0<w<=128
    return [{'kind':'copy','bytes':w,'operation':n}]
def val(n,t): return ops(f'{n} value source -> {t}')
def lit(n,t): return ops(f'literal {n} source -> {t}')
def ref(n,t): return ops(f'{n} reference -> dereference address operand',f'{n} dereferenced scalar source -> {t}')
def fld(n,t): return ops(f'{n} owner pointer -> field projection operand',f'{n} field address projection',f'{n} field source -> {t}')
def region(n,t): return ops(f'{n} constant Region.base -> materialized source field',f'{n} constant Region.rows -> materialized source field',f'{n} constant Region.stride -> materialized source field')+fld(n,t)
def bi(op,a,b,t='condition source'): return a+b+ops(f'primitive {op}',f'{op} result source -> {t}')
def cast(ty,a,t): return a+ops(f'primitive cast {ty}',f'{ty} result source -> {t}')
def cond(parts,total=None):
    # List is the ACTUALLY evaluated short-circuit prefix. Final value is a
    # direct if result; preceding children each pay their short-circuit edge.
    out=[]
    for i,p in enumerate(parts):
        out+=p
        if i+1<(len(parts) if total is None else total): out+=ops(f'short-circuit decision[{i}]')
    return out+ops('condition result source -> if predicate','if control branch')
def add(n,a): return bi('+',val(n,'+ left'),a,n)
def pattern(n,fields):
    out=ops(f'{n} reference source -> array-pattern received reference','array-pattern entry control')
    for f in fields: out+=ops(f'{n} row pointer -> {f} field projection operand',f'{f} array-pattern field address projection',f'{f} projected reference -> named binding')
    return out+ops('array-pattern successful statement continuation')
def index(n,e,t,width,*,fat=False):
    out=e+ops(f'{n} Index receiver borrow',f'{n} pointer -> Index received receiver')
    if fat: out+=ops(f'{n} len -> Index received receiver.len')
    return out+ops('Index entry control','received index -> upper predicate left',f'{"received" if fat else "fixed"} length -> upper predicate right','index<length predicate','index check branch','received pointer -> address operand','received index -> scaling operand',f'element width{width} -> scaling operand','index*width','scaled offset -> pointer-add operand','received pointer -> pointer-add operand','element address formation','element address -> returned reference source','indexed reference loan creation','returned reference -> caller received reference','Index return control','received array reference -> dereference address operand',f'dereferenced array address projection -> {t}')
def row(n,e,t,width): return index(n,e,t,width)+ops('explicit row shared reborrow creation',f'row pointer source -> {t}')
def le(n,t): return ops(f'{n} reference -> dereference address operand',f'{n} dereferenced array source address projection')+cp(f'{n} complete array8 source -> from_le_bytes received array8',8)+ops('from_le_bytes entry control','u64 from_le_bytes conversion','converted word -> from_le_bytes designated output','from_le_bytes return control',f'from_le_bytes output -> {t}')
def checked(ok):
    return val('total','checked_add received self')+val('bytes','checked_add received argument')+ops('checked_add entry control','checked addition arithmetic','overflow predicate','overflow branch',f'{"Some" if ok else "None"} Option tag source construction')+(ops('arithmetic result -> Some payload source') if ok else [])+cp('complete Option<u64>16 source -> checked_add received Option16',16)+ops('checked_add return control','received Option.tag -> pattern operand','Some pattern predicate','pattern control branch')+(ops('received Some payload -> sum binding') if ok else [])
def refusal(reason):
    # Whole reject edge is deliberately retained as bounding slack here; G7's
    # actual reply ownership is unchanged and must not also be claimed as G2.
    return lit(reason,'reject received reason')+ops('reject entry control','literal2 -> reply.status source','received reason -> reply.reason source','SEMANTIC_RECORD source -> reply.debit source')+cp('complete SemanticReply24 source -> caller received reply24 (bounding slack)',24)+ops('reject return control','caller received reply -> semantic designated return','semantic return control','G2 lexical borrow scope exit')
def increment(n): return add(n,lit(1,'+ right'))
def while_test(n,r): return cond([bi('<',val(n,'< left'),r)])
def statement_end(n): return ops(f'{n} statement unit construction',f'{n} statement continuation')
def rangeview(n,start,end):
    return start+end+ops('Range.start -> Index received start','Range.end -> Index received end',f'{n} Index receiver borrow creation',f'{n} data -> Index received receiver.data',f'{n} len -> Index received receiver.len','Index entry control','start -> ordered predicate left','end -> ordered predicate right','start<=end predicate','ordered branch','end -> upper predicate left','received len -> upper predicate right','end<=len predicate','upper branch','base data -> address operand','start -> address operand','view address formation','end -> length subtraction left','start -> length subtraction right','length=end-start','address result -> returned view.data','length result -> returned view.len','projected view loan creation','returned view.data -> caller received view.data','returned view.len -> caller received view.len','Index return control')
def chunks(n,width,mutable=False):
    # Whole safe as_chunks API source abstraction: full tuple source/receive
    # fields, quotient/remainder, length and address checks. No standard-library
    # machine-code proof is asserted or required by selected authored grammar.
    return ops(f'{n} receiver reborrow',f'{n} data -> as_chunks received receiver.data',f'{n} len -> as_chunks received receiver.len','as_chunks entry control',f'literal{width} -> nonzero predicate operand','literal0 -> nonzero predicate operand','chunk width !=0 predicate','nonzero guard branch','received len -> quotient left',f'literal{width} -> quotient right','chunk quotient','quotient -> chunk_count source','received len -> remainder left',f'literal{width} -> remainder right','chunk remainder','remainder -> tail_count source','received data -> chunk-slice pointer source','chunk_count -> chunk-slice length source','chunk_count -> scaled-tail-offset left',f'literal{width} -> scaled-tail-offset right','tail offset multiplication','received data -> tail-address left','tail offset -> tail-address right','tail address formation','tail address -> tail-slice pointer source','tail_count -> tail-slice length source','chunk pointer -> full tuple received chunk.data','chunk len -> full tuple received chunk.len','tail pointer -> full tuple received tail.data','tail len -> full tuple received tail.len','as_chunks return control','received chunk.data -> named chunk binding.data','received chunk.len -> named chunk binding.len','received tail.data -> wildcard drop operand','received tail.len -> wildcard drop operand','tuple pattern continuation')
def first(n,width,mutable=False):
    return ops(f'{n} receiver reborrow',f'{n} data -> first_chunk received receiver.data',f'{n} len -> first_chunk received receiver.len','first_chunk entry control',f'literal{width} -> first_chunk width predicate','receiver.len -> first_chunk length predicate','first_chunk length>=width predicate','first_chunk success branch','borrow returned fixed array reference','Some pointer source construction','complete Option<&array>8 source pointer -> caller received Option8','first_chunk return control','caller Option pointer -> expect received self','static expect text address -> message.data source','static expect text length -> message.len source','message.data -> expect received message.data','message.len -> expect received message.len','expect entry control','Option pointer -> tag predicate','Some tag predicate','expect Some branch','unwrapped array pointer source -> returned reference','returned array reference -> caller received reference','expect return control','returned array pointer -> named fixed-array binding')
def split():
    return ops('Candidate array pointer -> split_at_mut received receiver','Candidate reborrow creation','literal512 -> split received mid','split_at_mut entry control','received mid -> upper predicate left','fixed Candidate length2048 -> upper predicate right','mid<=len predicate','split bounds branch','Candidate pointer -> left tuple field source.data','literal512 -> left tuple field source.len','Candidate pointer -> right-address operand','mid -> right-address operand','right address formation','right address -> right tuple field source.data','fixed2048 -> right-length left','mid -> right-length right','right length subtraction','right length -> right tuple field source.len','left data -> full tuple received left.data','left len -> full tuple received left.len','right data -> full tuple received right.data','right len -> full tuple received right.len','split return control','left data -> time_bytes binding.data','left len -> time_bytes binding.len','right data -> index_bytes binding.data','right len -> index_bytes binding.len','split tuple pattern continuation')
def prelude():
    out=[]
    # These unchanged outer G2 values survive to function scope end.
    for n in ['total','count','found','first_empty','first_pin','resident_pins','live_tokens','release_nonce_matches']:
        out+=lit('ABSENT' if n in ['found','first_empty','first_pin'] else 0,f'{n} binding')
    out+=ops('G2 lexical block entry')+chunks('b',8)
    for n,region_name,count,width in [('resident','RESIDENT.base',512,8),('pin','PIN.base',384,6)]:
        start=bi('/',region(region_name,'/ left'),lit(8,'/ right'),'Range.start source')
        end=bi('+',bi('/',region(region_name,'/ left'),lit(8,'/ right'),'+ left'),lit(count,'+ right'),'Range.end source')
        out+=rangeview('arena_words',start,end)+chunks(n+'_word_range',width)+first(n+'_chunks',64)
    out+=split()+chunks('time_bytes',8,True)+first('timestamp_chunks',64,True)
    out+=pattern('w',['record_kind','requested_function','release_nonce'])
    out+=ops('p owner pointer -> q field projection operand','p.q field address projection','p.q explicit shared array reborrow creation')+pattern('p.q',['prior_count','prior_total','prior_pins','next_nonce'])
    for n in ['slots','pins','entry']: out+=fld('f.'+n,'configured_'+n+' binding')
    out+=cast('usize',val('configured_slots','cast operand'),'resident_limit binding')+cast('usize',val('configured_pins','cast operand'),'pin_limit binding')+lit(0,'eligibility binding')+lit(0,'slot binding')
    return out
def resident(path):
    # Refusal points retain exactly the short-circuited source prefix.
    out=row('resident_rows',val('slot','Index received index'),'row binding',64)+pattern('row',['occupied_le','function_le','bytes_le','pins_le','last_used_le','reserved6_le','reserved7_le'])
    for n in ['occupied','function','bytes','pins']: out+=le(n+'_le',n+' binding')
    valid=[bi('>',val('occupied','> left'),lit(1,'> right')),bi('>',val('pins','> left'),val('configured_pins','> right')),bi('!=',le('reserved6_le','!= left'),lit(0,'!= right')),bi('!=',le('reserved7_le','!= left'),lit(0,'!= right'))]
    if path.startswith('invalid-header'):
        return out+cond(valid[:int(path[-1])+1],4)+refusal(13)
    out+=cond(valid)+cond([bi('==',val('occupied','== left'),lit(1,'== right'))])
    if path.startswith(('occupied','invalid-body','overflow','duplicate')):
        out+=add('resident_pins',val('pins','+ right'))
        body=[bi('>=',val('function','>= left'),lit(80000,'>= right')),bi('==',val('bytes','== left'),lit(0,'== right')),bi('>',val('bytes','> left'),val('configured_entry','> right'))]
        if path.startswith('invalid-body'): return out+cond(body[:int(path[-1])+1],3)+refusal(13)
        out+=cond(body)+checked(path!='overflow')
        if path=='overflow': return out+refusal(10)
        out+=val('sum','total binding')+increment('count')+cond([bi('==',val('function','== left'),ref('requested_function','== right'))])
        if path in ['occupied-match','occupied-match-eligible','duplicate']:
            out+=cond([bi('!=',val('found','!= left'),lit('ABSENT','!= right'))])
            if path=='duplicate': return out+refusal(7)
            out+=cast('u64',val('slot','cast operand'),'found binding')
    else:
        empty=[bi('!=',val('function','!= left'),lit('ABSENT','!= right')),bi('!=',val('bytes','!= left'),lit(0,'!= right')),bi('!=',val('pins','!= left'),lit(0,'!= right'))]
        if path.startswith('invalid-empty'): return out+cond(empty[:int(path[-1])+1],3)+refusal(13)
        out+=cond(empty)+cond([bi('==',val('first_empty','== left'),lit('ABSENT','== right'))])
        if path=='empty-first': out+=cast('u64',val('slot','cast operand'),'first_empty binding')
    out+=index('timestamp_words',val('slot','Index received index'),'timestamp destination8',8)+ops('last_used_le reference -> dereference source address','timestamp array8 source address projection')+cp('actual resident last_used complete array8 -> indexed timestamp destination8',8)+statement_end('timestamp assignment')
    elig=[bi('==',val('occupied','== left'),lit(1,'== right'))]
    if path.startswith('occupied'): elig+=[bi('==',val('pins','== left'),lit(0,'== right'))]
    out+=cond(elig,2)
    if path in ['occupied-eligible','occupied-match-eligible']: out+=bi('|',val('eligibility','| left'),bi('<<',lit('1u64','<< left'),val('slot','<< right'),'| right'),'eligibility binding')
    return out+increment('slot')+ops('resident while body implicit unit','resident while back control')
def tail():
    return index('timestamp_words',val('slot','Index received index'),'timestamp destination8',8)+lit('0u64','to_le_bytes received self')+ops('to_le_bytes entry control','u64 to_le_bytes conversion','to_le_bytes return control')+cp('to_le_bytes complete returned array8 -> indexed timestamp destination8',8)+statement_end('tail timestamp assignment')+increment('slot')+ops('tail while body implicit unit','tail while back control')
def pin(path):
    out=row('pin_rows',val('pin','Index received index'),'row binding',48)+pattern('row',['entry_le','nonce_le'])+le('entry_le','entry binding')+le('nonce_le','nonce binding')+cond([bi('==',val('entry','== left'),lit('ABSENT','== right'))])
    if path.startswith('empty'):
        out+=cond([bi('!=',val('nonce','!= left'),lit(0,'!= right'))])
        if path=='empty-invalid-nonce': return out+refusal(13)
        out+=cond([bi('==',val('first_pin','== left'),lit('ABSENT','== right'))])
        if path=='empty-first': out+=cast('u64',val('pin','cast operand'),'first_pin binding')
    else:
        header=[bi('>=',val('entry','>= left'),val('configured_slots','>= right')),bi('==',val('nonce','== left'),lit(0,'== right')),bi('>=',val('nonce','>= left'),ref('next_nonce','>= right'))]
        if path.startswith('invalid-header'): return out+cond(header[:int(path[-1])+1],3)+refusal(13)
        out+=cond(header)+row('resident_rows',cast('usize',val('entry','cast operand'),'Index received index'),'back_row binding',64)+pattern('back_row',['back_occupied_le','back_pins_le'])
        backlink=[bi('!=',le('back_occupied_le','!= left'),lit(1,'!= right')),bi('==',le('back_pins_le','== left'),lit(0,'== right'))]
        if path.startswith('invalid-backlink'): return out+cond(backlink[:int(path[-1])+1],2)+refusal(13)
        out+=cond(backlink)+increment('live_tokens')
        release=[bi('==',ref('record_kind','== left'),lit(12,'== right'))]
        if path!='live-nonrelease': release+=[bi('==',val('nonce','== left'),ref('release_nonce','== right'))]
        out+=cond(release,2)
        if path=='live-release-match': out+=increment('release_nonce_matches')
    return out+increment('pin')+ops('pin while body implicit unit','pin while back control')
def mask_store():
    return rangeview('index_bytes',lit(128,'Range.start source'),lit(136,'Range.end source'))+ops('destination view exclusive copy reborrow','destination view.data -> copy received receiver.data','destination view.len -> copy received receiver.len')+val('eligibility','to_le_bytes received self')+ops('to_le_bytes entry control','u64 to_le_bytes conversion')+cp('to_le_bytes complete returned array8 -> received LE temporary8',8)+ops('to_le_bytes return control','LE temporary array address formation','LE temporary shared borrow creation','LE address -> source slice.data','literal8 -> source slice.len','source slice.data -> copy received source.data','source slice.len -> copy received source.len','copy entry control','receiver.len -> length equality left','source.len -> length equality right','source/destination length equality','copy length branch')+cp('LE temporary complete8 source -> actual mask destination8',8)+ops('copy unit/control return -> caller','copy statement continuation')
def post(path):
    checks=[[bi('>',val('release_nonce_matches','> left'),lit(1,'> right'))],[bi('!=',val('resident_pins','!= left'),ref('prior_pins','!= right')),bi('!=',val('live_tokens','!= left'),ref('prior_pins','!= right'))],[bi('!=',val('count','!= left'),ref('prior_count','!= right')),bi('!=',val('total','!= left'),ref('prior_total','!= right')),bi('>',ref('prior_pins','> left'),val('configured_pins','> right')),bi('==',ref('next_nonce','== left'),lit(0,'== right'))]]
    out=[]
    for i,parts in enumerate(checks):
        if path.startswith(f'fail{i}.'):
            return out+cond(parts[:int(path.split('.')[1])+1],len(parts))+refusal(11 if i==0 else 13)
        out+=cond(parts)
    return out+ops('G2 lexical block implicit unit','G2 lexical block exit continuation')
def counts(xs):
    s=sum(x['kind']=='scalar' for x in xs); c=sum(x['kind']=='copy' for x in xs)
    return {'scalars':s,'copies':c,'scalar_groups':(s+15)//16,'groups':(s+15)//16+c}
def cost(xs): return counts(xs)['scalars']+16*counts(xs)['copies']

def main():
    seedseal=SEED/'seal.json'; seedsource=SEED/'source/cache_state.rs.txt'
    assert sha(seedseal.read_bytes())==SEED_SEAL
    assert sha(seedsource.read_bytes())==SEED_SOURCE
    assert sha(C3.read_bytes())=='0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
    seed=seedsource.read_text(); begin=seed.index('    // G2. This lexical shared arena view')
    end=seed.index('    let body = w[6] as usize;',begin)
    fragment=(HERE/'g2.rs.txt').read_text(); proposed=seed[:begin]+fragment+seed[end:]
    (HERE/'source').mkdir(exist_ok=True)
    (HERE/'source/cache_state.rs.txt').write_text(proposed)
    (HERE/'proposed.diff').write_text(''.join(difflib.unified_diff(seed.splitlines(True),proposed.splitlines(True),fromfile='unselected-seeded/source/cache_state.rs.txt',tofile='unselected-row-probe/source/cache_state.rs.txt')))
    inputs=[ROOT/'AGENTS.md',C3,C3.parent/'analyzer.rs',seedseal,seedsource,ROOT/'docs/swift-semantic-adapter-prerequisite.md',ROOT/'docs/swift-cache-state-implementation-review-plan.md',ROOT/'verification/swift-cache-state-g6-complete/ledger.py',ROOT/'verification/swift-cache-state-c3-lifetime-accounting/phases.json',ROOT/'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json',ROOT/'verification/swift-semantic-adapter-root-review/C3-lifetime-selection.json']
    bindings=[{'path':str(p.relative_to(ROOT)),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in inputs]
    dump('inputs.json',{'schema':1,'inputs':bindings,'tree_digest':sha(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()),'seeded_source_only_unselected':True,'seeded_packet_not_imported_or_executed':True})
    dump('source-assembly.json',{'schema':1,'source_sha256':sha(proposed.encode()),'seeded_sha256':SEED_SOURCE,'correction3_sha256':sha(C3.read_bytes()),'prefix_byte_identical':seed[:begin]==proposed[:begin],'suffix_byte_identical':seed[end:]==proposed[begin+len(fragment):],'prefix_sha256':sha(seed[:begin].encode()),'suffix_sha256':sha(seed[end:].encode()),'source_region':'G2 lexical block and its three common post-probe invariant checks only; scratch-seeded merge and later G5/G6 untouched','no_G6_or_C3_inheritance_for_changed_G2_helpers_callers':True,'not_selected':True})
    regions={'arena':8388608,'resident_base':7680000,'resident_rows':64,'resident_stride':64,'pin_base':7684096,'pin_rows':64,'pin_stride':48}
    assert regions['resident_base']%8==0 and regions['pin_base']%8==0
    assert regions['resident_base']+64*64==regions['pin_base']
    assert regions['pin_base']+64*48<=regions['arena']
    dump('range-and-coverage.json',{'schema':1,'fixed_regions':regions,'arena_word_count':1048576,'resident_word_range':[960000,960512],'resident_nested_chunk_count':64,'resident_first_chunk_width':64,'pin_word_range':[960512,960896],'pin_nested_chunk_count':64,'pin_first_chunk_width':64,'timestamp_candidate_range':[0,512],'timestamp_word_count':64,'candidate_split_right_range':[512,2048],'mask_right_view_range':[128,136],'mask_actual_candidate_range':[640,648],'selected_preconditions':'semantic G128 rejects arena.len !=8388608 beforeG2; G1 rejects fixture slots/pins outside1..64; fixed constants and Candidate2048 unchanged','all_first_chunk_and_expect_success_proved':True,'panic_or_bounds_failure_paths':'unreachable for source-admitted arena/Candidate/config; checks are still charged, never optimizer-elided','backlink_index_precondition':'entry>=configured_slots rejects before resident_rows[entry as usize]; configured_slots<=64 proves fixed row index','as_chunks_nonzero_widths':[8,6],'required_decodes_in_source_order':'resident0,1,2,3 always; resident6/7 lazily after prior header predicates; timestamp4 only after full row validation; generation5 unexamined; pin0,1 always; backlink0 then3 lazy only after entry and nonce guards','preserved_reasons':{'resident_header_or_shape':13,'byte_total_overflow':10,'duplicate_requested_resident':7,'pin_shape_or_backlink':13,'duplicate_release_nonce':11,'aggregate_invariant':13},'branch_coverage':'6 resident continuation patterns +12 resident terminal patterns;5 pin continuation patterns +6 pin terminal patterns;7 common terminal checks +success; all0..63 early prefixes and all1..64 configurations','success_dominators_are_relaxations':'64 occupied requested/eligible rows and64matching release tokens cannot all be a valid accepted state; their branch union is used solely as a conservative upper and never as a reachable witness','groups_and_calls_beyond_G2':'G1/G7/setup/finish/guard not accepted here; full reject reply counted only as G2 bounding slack, leaves actual G7 ownership unchanged; G3-G5 and remaining changed sort lifetimes pending','cleanup':'shared arena and exclusive Candidate subviews all end at actualG2 block exit, including return. They cannot coexist with later mutable arena commit or merge borrow.'})
    resnames=['occupied-other','occupied-match','occupied-eligible','occupied-match-eligible','empty-first','empty-later']
    resfaults=[f'invalid-header{i}' for i in range(4)]+[f'invalid-body{i}' for i in range(3)]+['overflow','duplicate']+[f'invalid-empty{i}' for i in range(3)]
    pinnames=['empty-first','empty-later','live-nonrelease','live-release-other','live-release-match']
    pinfaults=['empty-invalid-nonce']+[f'invalid-header{i}' for i in range(3)]+[f'invalid-backlink{i}' for i in range(2)]
    postnames=['success']+[f'fail{i}.{j}' for i,n in enumerate([1,2,4]) for j in range(n)]
    templates={'prelude':prelude(),'resident-test':while_test('slot',val('resident_limit','< right')),'tail-test':while_test('slot',lit(64,'< right')),'tail-body':tail(),'pin-init':lit(0,'pin binding'),'pin-test':while_test('pin',val('pin_limit','< right')),'mask-store':mask_store()}
    templates.update({'resident.'+n:resident(n) for n in resnames+resfaults})
    templates.update({'pin.'+n:pin(n) for n in pinnames+pinfaults})
    templates.update({'post.'+n:post(n) for n in postnames})
    summary={n:counts(xs) for n,xs in templates.items()}
    dump('components.json',{'schema':1,'grammar':'selected Trace.e, fixed Index20 / fat Index21; source/received scalar edges; distinct complete array8 and Option16 payload copies; full niche Option8 pointer fields; no optimizer omission','source_order_preserved':True,'templates':templates,'counts':summary})
    # Dominating recipes: all legal configurations 1..64 x1..64, each prefix,
    # every terminal/refusal point. Per-iteration branch maxima intentionally
    # relax uniqueness/reachability constraints and only increase upper work.
    rmax=max(resnames,key=lambda n:cost(templates['resident.'+n])); pmax=max(pinnames,key=lambda n:cost(templates['pin.'+n])); postmax=max(postnames,key=lambda n:cost(templates['post.'+n]))
    def seq(items):
        out=[]
        for name,n in items: out+=templates[name]*n
        return out
    recipes=[]
    def recipe(label,items,domain):
        s=sum(summary[k]['scalars']*n for k,n in items); c=sum(summary[k]['copies']*n for k,n in items)
        cs={'scalars':s,'copies':c,'scalar_groups':(s+15)//16,'groups':(s+15)//16+c}
        recipes.append({'label':label,'components':[{'component':k,'repeat':n} for k,n in items if n],'domain':domain,**cs})
    for n in range(1,65):
        rprefix=[('prelude',1),('resident-test',n+1),('resident.'+rmax,n),('tail-test',65-n),('tail-body',64-n),('pin-init',1)]
        for m in range(1,65):
            recipe(f'complete.n{n}.m{m}',rprefix+[('pin-test',m+1),('pin.'+pmax,m),('mask-store',1),('post.'+postmax,1)],{'slots':n,'pins':m,'all_post_paths_dominated_by':postmax})
    for k in range(64):
        for fault in resfaults:
            recipe(f'resident-stop.{k}.{fault}',[('prelude',1),('resident-test',k+1),('resident.'+rmax,k),('resident.'+fault,1)],{'successful_resident_prefix':k,'remaining_loops_not_entered':True})
    for n in range(1,65):
        for k in range(64):
            for fault in pinfaults:
                recipe(f'pin-stop.n{n}.{k}.{fault}',[('prelude',1),('resident-test',n+1),('resident.'+rmax,n),('tail-test',65-n),('tail-body',64-n),('pin-init',1),('pin-test',k+1),('pin.'+pmax,k),('pin.'+fault,1)],{'slots':n,'successful_pin_prefix':k,'remaining_pins_not_entered':True})
    maxrecipe=max(recipes,key=lambda x:x['groups'])
    dump('upper-bound.json',{'schema':1,'status':'conservative complete G2 authored-source upper' if maxrecipe['groups']<=CAP else 'finite conservative upper exceeds cap; no pass','cap':CAP,'maximum':maxrecipe,'recipe_count':len(recipes),'resident_success_dominator':rmax,'pin_success_dominator':pmax,'post_dominator':postmax,'branch_dominance_weight':'scalars+16*copies; equivalent to ceil(scalars/16)+copies, no per-iteration rounding restriction imposed by selected global pooling grammar','all_1_to64_slot_and_pin_configurations':True,'all_early_refusal_prefixes_covered':True,'G3_G4_G5_not_assessed':True,'complete_implementation_or_role_union_accepted':False})
    raw=(json.dumps({'schema':1,'recipes':recipes},sort_keys=True,separators=(',',':'))+'\n').encode(); (HERE/'recipes.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    # The actual necessary witness remains the prior64 occupied/pinned path.
    items=[('prelude',1),('resident-test',65),('resident.occupied-other',64),('tail-test',1),('pin-init',1),('pin-test',65),('pin.live-nonrelease',64),('mask-store',1),('post.success',1)]
    witness=seq(items)
    dump('g2-witness.json',{'schema':1,'fixture':{'slots':64,'pins':64,'entry':1,'base':0,'capacity':128},'state':{'resident_count':64,'resident_bytes':64,'pin_count':64,'next_nonce':65,'idle':True},'residents':[{'slot':i,'occupied':1,'function':i,'bytes':1,'pins':1,'last_used':i,'generation':0,'reserved6':0,'reserved7':0} for i in range(64)],'pins':[{'pin':i,'entry':i,'nonce':i+1} for i in range(64)],'record':{'kind':1,'operation':65,'requested_function':80000},'reachability':'64 successful builds/publications retained pinned; previous valid finite witness; AcquireBegin permits undefined requested body until later Lookup','components':[{'component':k,'repeat':n} for k,n in items],**counts(witness),'actual_Rust_executed':False})
    # Freeze the chosen dominating complete trace into disjoint named groups.
    trace=seq([(x['component'],x['repeat']) for x in maxrecipe['components']]); scalars=[]; copies=[]
    for i,x in enumerate(trace):
        x={'id':f'G2.{i:06}',**x}
        if x['kind']=='scalar': scalars.append(x)
        else: copies.append(x)
    groups=[{'kind':'scalar','events':scalars[i:i+16]} for i in range(0,len(scalars),16)]+[{'kind':'copy','events':[x],'bytes':x['bytes']} for x in copies]
    assert len(groups)==maxrecipe['groups'] and all(len(x['events'])<=16 if x['kind']=='scalar' else x['bytes']<=128 for x in groups)
    raw=(json.dumps({'schema':1,'path':maxrecipe['label'],'groups':groups},sort_keys=True,separators=(',',':'))+'\n').encode(); (HERE/'complete-upper-ledger.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    dump('build-receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(HERE/'build.py')],'python':sys.version,'platform':platform.platform(),'source_sha256':sha(proposed.encode()),'input_tree_digest':sha(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()),'scope':'own Python source/math only; source copied as text, never imported/compiled/executed','compiler_product_runtime_native_UI_capture_process_inventory_Git_hosted':False,'cleanup':'No process, native instance or build directory started. Only assigned proposal folder written.'})
    print(json.dumps({'G2_witness':counts(witness),'G2_upper':{k:maxrecipe[k] for k in ['label','scalars','copies','groups']},'cap':CAP,'template_counts':summary,'source_sha256':sha(proposed.encode())},indent=2))
if __name__=='__main__': main()
