#!/usr/bin/env python3
"""Independent arithmetic and finite source-model checks; no producer imports."""
from __future__ import annotations
import copy, datetime, gzip, hashlib, json, platform, random, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAX=(1<<64)-1
def sha(b): return hashlib.sha256(b).hexdigest()
def read(n): return json.loads((HERE/n).read_text())
def dump(n,x): (HERE/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def require(ok,msg):
    if not ok: raise ValueError(msg)
def tally(xs):
    s=sum(x['kind']=='scalar' for x in xs); c=sum(x['kind']=='copy' for x in xs)
    return s,c,(s+15)//16+c

# Separately hand-expanded source component totals. This checker neither imports
# the producer nor calls its expression/Trace builders. Pointer and Range fields
# are scalar edges; real array8/Option16 payload movements remain distinct copies.
EXPECTED={
 'prelude':(397,0),'resident-test':(6,0),'tail-test':(6,0),'tail-body':(33,1),
 'pin-init':(1,0),'pin-test':(6,0),'mask-store':(48,2),
 'resident.occupied-other':(201,8),'resident.occupied-match':(210,8),
 'resident.occupied-eligible':(208,8),'resident.occupied-match-eligible':(217,8),
 'resident.empty-first':(177,7),'resident.empty-later':(174,7),
 'resident.invalid-header0':(91,5),'resident.invalid-header1':(96,5),
 'resident.invalid-header2':(107,6),'resident.invalid-header3':(117,7),
 'resident.invalid-body0':(134,7),'resident.invalid-body1':(139,7),
 'resident.invalid-body2':(143,7),'resident.overflow':(154,8),
 'resident.duplicate':(174,8),'resident.invalid-empty0':(130,7),
 'resident.invalid-empty1':(135,7),'resident.invalid-empty2':(139,7),
 'pin.empty-first':(73,2),'pin.empty-later':(70,2),'pin.live-nonrelease':(144,4),
 'pin.live-release-other':(149,4),'pin.live-release-match':(153,4),
 'pin.empty-invalid-nonce':(67,3),'pin.invalid-header0':(68,3),
 'pin.invalid-header1':(73,3),'pin.invalid-header2':(78,3),
 'pin.invalid-backlink0':(125,4),'pin.invalid-backlink1':(135,5),
 'post.success':(46,0),'post.fail0.0':(15,1),'post.fail1.0':(23,1),
 'post.fail1.1':(28,1),'post.fail2.0':(36,1),'post.fail2.1':(42,1),
 'post.fail2.2':(48,1),'post.fail2.3':(53,1),
}
def arithmetic(components,upper,recipes,ledger):
    ts=components['templates']; require(set(ts)==set(EXPECTED),'component coverage drift')
    for n,xs in ts.items():
        s,c,g=tally(xs); require((s,c)==EXPECTED[n],f'hand arithmetic mismatch {n}')
        require(all(x['bytes']==0 if x['kind']=='scalar' else 0<x['bytes']<=128 for x in xs),'copy rule')
        require(components['counts'][n]=={'scalars':s,'copies':c,'scalar_groups':(s+15)//16,'groups':g},'summary drift')
    require(upper['cap']==2560,'cap drift')
    require(len(recipes)==29440,'finite recipe count drift')
    maxgroups=-1; complete=set(); rfaults=set(); pfaults=set()
    for r in recipes:
        s=sum(EXPECTED[x['component']][0]*x['repeat'] for x in r['components'])
        c=sum(EXPECTED[x['component']][1]*x['repeat'] for x in r['components'])
        g=(s+15)//16+c
        require((s,c,g)==(r['scalars'],r['copies'],r['groups']),'recipe arithmetic drift')
        maxgroups=max(maxgroups,g)
        if r['label'].startswith('complete.'):
            complete.add((r['domain']['slots'],r['domain']['pins']))
        elif r['label'].startswith('resident-stop.'):
            rfaults.add(r['components'][-1]['component'])
        else: pfaults.add(r['components'][-1]['component'])
    require(complete=={(n,m) for n in range(1,65) for m in range(1,65)},'configuration omitted')
    require(len(rfaults)==12 and len(pfaults)==6,'refusal family omitted')
    require(maxgroups==2332 and maxgroups<=2560,'complete upper over cap/drift')
    # Independently derive the dominating complete and actual witness arithmetic.
    s=397+65*6+64*217+6+1+65*6+64*153+48+53
    c=64*8+64*4+2+1
    require((s,c,(s+15)//16+c)==(24965,771,2332),'upper hand equation')
    sw=397+65*6+64*201+6+1+65*6+64*144+48+46
    cw=64*8+64*4+2
    require((sw,cw,(sw+15)//16+cw)==(23358,770,2230),'witness hand equation')
    # The weight is monotone under every alternative, including full copies.
    rw=lambda n: EXPECTED[n][0]+16*EXPECTED[n][1]
    require(all(rw(n)<=rw('resident.occupied-match-eligible') for n in ts if n.startswith('resident.') and not any(q in n for q in ['invalid','overflow','duplicate'])),'resident domination')
    require(all(rw(n)<=rw('pin.live-release-match') for n in ts if n.startswith('pin.') and not any(q in n for q in ['invalid'])),'pin domination')
    require(all(rw(n)<=rw('post.fail2.3') for n in ts if n.startswith('post.')),'post domination')
    seen=[]; sc=cp=0
    for g in ledger['groups']:
        require(g['kind'] in ['scalar','copy'],'group kind')
        require(1<=len(g['events'])<=16 if g['kind']=='scalar' else len(g['events'])==1 and 0<g['bytes']<=128,'group width')
        for e in g['events']:
            seen.append(e['id']); sc+=e['kind']=='scalar'; cp+=e['kind']=='copy'
    require(len(set(seen))==len(seen),'duplicate event')
    require((sc,cp,len(ledger['groups']))==(24965,771,2332),'expanded grouping drift')
    require(upper['complete_implementation_or_role_union_accepted'] is False,'acceptance overclaim')
    return {'components':len(ts),'recipes':len(recipes),'complete_configurations':len(complete),'resident_refusal_families':len(rfaults),'pin_refusal_families':len(pfaults),'upper_scalars':s,'upper_copies':c,'upper_groups':2332,'witness_groups':2230,'groups_checked':len(ledger['groups'])}

def fixture(n=1,m=1):
    return {'slots':n,'pin_limit':m,'entry_cap':MAX,'residents':[[0,MAX,0,0,0,0,0,0] for _ in range(n)],'pins':[[MAX,0,0,0,0,0] for _ in range(m)],'q_count':0,'q_total':0,'q_pins':0,'next_nonce':1,'kind':1,'requested':MAX,'release':0}
def probe(s,mode):
    """Independent logical control-flow model, two independently read layouts.

    This is an offline finite relation check and cannot authorize Rust semantics,
    compilation, an accepted candidate, OTA, or runtime execution.
    """
    reads=[]; scratch=[None]*64; mask=0
    raw_r=[b''.join(x.to_bytes(8,'little') for x in r) for r in s['residents']]
    raw_p=[b''.join(x.to_bytes(8,'little') for x in r) for r in s['pins']]
    def resident(i,j):
        reads.append(('resident',i,j))
        if mode=='old': return s['residents'][i][j]
        # Typed rows/fields are borrowed without loading payload. Loading the
        # chosen word preserves exact safe LE bits and the lazy read sequence.
        row=tuple(raw_r[i][k:k+8] for k in range(0,64,8))
        return int.from_bytes(row[j],'little')
    def pinword(i,j):
        reads.append(('pin',i,j))
        return s['pins'][i][j] if mode=='old' else int.from_bytes(raw_p[i][j*8:j*8+8],'little')
    total=count=resident_pins=live=matches=0; found=first_empty=first_pin=MAX
    def result(reason): return {'reason':reason,'total':total,'count':count,'resident_pins':resident_pins,'live':live,'matches':matches,'found':found,'first_empty':first_empty,'first_pin':first_pin,'mask':mask,'scratch':scratch,'reads':reads}
    for i in range(s['slots']):
        occ=resident(i,0); function=resident(i,1); size=resident(i,2); pins=resident(i,3)
        if occ>1 or pins>s['pin_limit'] or resident(i,6)!=0 or resident(i,7)!=0: return result(13)
        if occ==1:
            resident_pins+=pins
            if function>=80000 or size==0 or size>s['entry_cap']: return result(13)
            if total+size>MAX: return result(10)
            total+=size; count+=1
            if function==s['requested']:
                if found!=MAX: return result(7)
                found=i
        elif function!=MAX or size!=0 or pins!=0: return result(13)
        elif first_empty==MAX: first_empty=i
        if mode=='old': scratch[i]=resident(i,4).to_bytes(8,'little')
        else:
            reads.append(('resident',i,4)); scratch[i]=raw_r[i][32:40]
        if occ==1 and pins==0: mask|=1<<i
    for i in range(s['slots'],64): scratch[i]=(0).to_bytes(8,'little')
    for i in range(s['pin_limit']):
        entry=pinword(i,0); nonce=pinword(i,1)
        if entry==MAX:
            if nonce!=0: return result(13)
            if first_pin==MAX: first_pin=i
        else:
            if entry>=s['slots'] or nonce==0 or nonce>=s['next_nonce'] or resident(entry,0)!=1 or resident(entry,3)==0: return result(13)
            live+=1
            if s['kind']==12 and nonce==s['release']: matches+=1
    if matches>1: return result(11)
    if resident_pins!=s['q_pins'] or live!=s['q_pins']: return result(13)
    if count!=s['q_count'] or total!=s['q_total'] or s['q_pins']>s['pin_limit'] or s['next_nonce']==0: return result(13)
    return result(0)

def finite_cases():
    cases=[]
    def case(name,s,reason): cases.append((name,s,reason))
    for n in [1,2,63,64]:
        for m in [1,2,63,64]: case(f'empty.n{n}.m{m}',fixture(n,m),0)
    # All64 eligible timestamps include MAX; this only checks G2 transport.
    s=fixture(64,64); s.update(q_count=64,q_total=64,requested=80000)
    for i,r in enumerate(s['residents']): r[:]=[1,i,1,0,MAX if i%2 else i,MAX,0,0]
    case('eligible64.timestampMAX.generationIgnored',s,0)
    s=fixture(64,64); s.update(q_count=64,q_total=64,q_pins=64,next_nonce=65,requested=80000)
    for i,r in enumerate(s['residents']): r[:]=[1,i,1,1,i,0,0,0]; s['pins'][i][:2]=[i,i+1]
    case('necessary64.pinnedAcquireBegin',s,0)
    occupied=fixture(); occupied.update(q_count=1,q_total=1,requested=5)
    occupied['residents'][0][:]=[1,5,1,0,MAX,0,0,0]
    for field,values in [(0,[2,MAX]),(1,[80000,MAX]),(2,[0]),(3,[2,MAX]),(6,[1,MAX]),(7,[1,MAX])]:
        for v in values:
            s=copy.deepcopy(occupied); s['residents'][0][field]=v; case(f'resident.field{field}.{v}',s,13)
    s=copy.deepcopy(occupied); s['entry_cap']=0; case('resident.entryBound',s,13)
    for field,values in [(1,[0,79999]),(2,[1,MAX]),(3,[1])]:
        for v in values:
            s=fixture(); s['residents'][0][field]=v; case(f'empty.field{field}.{v}',s,13)
    s=fixture(2,1); s.update(q_count=2,q_total=2,requested=3)
    s['residents']=[[1,3,1,0,0,0,0,0],[1,3,1,0,MAX,0,0,0]]; case('resident.duplicateRequested',s,7)
    s=fixture(2,1); s.update(q_count=2,q_total=MAX,requested=3)
    s['residents']=[[1,1,MAX,0,0,0,0,0],[1,2,1,0,MAX,0,0,0]]; case('resident.totalOverflow',s,10)
    pinned=fixture(); pinned.update(q_count=1,q_total=1,q_pins=1,next_nonce=2,requested=5)
    pinned['residents'][0][:]=[1,5,1,1,MAX,0,0,0]; pinned['pins'][0][:2]=[0,1]
    for n,entry,nonce,why in [('absentNonzero',MAX,1,13),('entryOnePast',1,1,13),('entryMAXminus1',MAX-1,1,13),('nonceZero',0,0,13),('nonceEqualNext',0,2,13),('nonceMAX',0,MAX,13)]:
        s=copy.deepcopy(pinned); s['pins'][0][:2]=[entry,nonce]; case('pin.'+n,s,why)
    s=fixture(1,1); s['pins'][0][:2]=[0,1]; s['next_nonce']=2; case('pin.backlinkUnoccupied',s,13)
    s=copy.deepcopy(pinned); s['residents'][0][3]=0; case('pin.backlinkZeroPins',s,13)
    for name,value in [('q_count',0),('q_total',0),('q_pins',0),('next_nonce',0)]:
        s=copy.deepcopy(pinned); s[name]=value; case('post.'+name,s,13)
    for kind in [1,2,3,4,5,6,7,8,9,10,11,12,13]:
        s=copy.deepcopy(pinned); s.update(kind=kind,release=1); case(f'kind{kind}.oneMatchingNonce',s,0)
    s=fixture(1,2); s.update(q_count=1,q_total=1,q_pins=2,next_nonce=MAX,kind=12,release=MAX-1)
    s['residents'][0][:]=[1,5,1,2,MAX,0,0,0]; s['pins']=[[0,MAX-1,0,0,0,0],[0,MAX-1,0,0,0,0]]
    case('release.duplicateNonceRefuses',s,11)
    s=copy.deepcopy(s); s['kind']=1; case('nonrelease.duplicateNoncePreserved',s,0)
    s=copy.deepcopy(pinned); s['next_nonce']=MAX; s['pins'][0][1]=MAX-1; case('nonce.MAXminus1.allowed',s,0)
    # Finite transitive state actions: empty->build/pin->extra pin->release->
    # no-pin eligibility->empty. Each step is checked independently against
    # expected aggregate state; this is model-only, not a Rust transition test.
    t=fixture(1,2); case('state0.empty',copy.deepcopy(t),0)
    t.update(q_count=1,q_total=7,q_pins=1,next_nonce=2); t['residents'][0]=[1,4,7,1,0,0,0,0]; t['pins'][0][:2]=[0,1]; case('state1.publishPinned',copy.deepcopy(t),0)
    t.update(q_pins=2,next_nonce=3); t['residents'][0][3]=2; t['pins'][1][:2]=[0,2]; case('state2.secondPin',copy.deepcopy(t),0)
    t['residents'][0][3]=1; t['pins'][0][:2]=[MAX,0]; t['q_pins']=1; case('state3.firstRelease',copy.deepcopy(t),0)
    t['residents'][0][3]=0; t['pins'][1][:2]=[MAX,0]; t['q_pins']=0; case('state4.unpinnedEligible',copy.deepcopy(t),0)
    t['residents'][0]=[0,MAX,0,0,MAX,MAX,0,0]; t.update(q_count=0,q_total=0); case('state5.evictedMAXtimestamp',copy.deepcopy(t),0)
    outputs=[]
    for name,s,why in cases:
        a=probe(s,'old'); b=probe(s,'row')
        require(a==b,'finite old/row relation '+name)
        require(a['reason']==why,'independent expected reason '+name)
        outputs.append({'name':name,'expected_reason':why,'observed_reason':a['reason'],'required_read_count':len(a['reads']),'required_read_sequence_sha256':sha(json.dumps(a['reads'],separators=(',',':')).encode()),'state_and_partial_scratch_equal':True,'timestamp_MAX_present':any(r[4]==MAX for r in s['residents'])})
    # Bijection is exact for arbitrary eight-byte words. 64 basis-bit words,
    # their complements, zero/MAX and256 deterministic full-width samples.
    rng=random.Random(0x726f7770726f6265)
    words=[0,MAX]+[1<<i for i in range(64)]+[MAX^(1<<i) for i in range(64)]+[rng.getrandbits(64) for _ in range(256)]
    for w in words:
        encoded=w.to_bytes(8,'little'); require(int.from_bytes(encoded,'little').to_bytes(8,'little')==encoded,'LE transport identity')
    return {'cases':outputs,'case_count':len(outputs),'timestamp_identity_cases':len(words),'semantic_authority':'finite offline logical source relation only, not Rust execution or implementation acceptance'}

def lifetimes():
    base={'cache_body.p':144,'cache_inputs.new_argument_sources':24,'cache_inputs.new_received':24,'cache_walk.new_argument_sources':16,'cache_walk.new_received':16,'cache_walk.f_source':8,'cache_walk.f_received':8,'cache_walk.arena_outer_pointer':8,'cache_walk.loan':16,'cache_walk.semantic_steps':16,'semantic.argument_sources':48,'semantic.received_parameters':48,'semantic.w_and_f':16,'semantic.eleven_outer_scalar_locals':88}
    require(sum(base.values())==480,'base control arithmetic')
    block={'arena_words':16,'resident_chunks':16,'resident_rows':8,'pin_chunks':16,'pin_rows':8,'time_bytes':16,'index_bytes':16,'timestamp_chunks':16,'timestamp_words':8,'record_kind_ref':8,'requested_function_ref':8,'release_nonce_ref':8,'prior_count_ref':8,'prior_total_ref':8,'prior_pins_ref':8,'next_nonce_ref':8,'configured_slots':8,'configured_pins':8,'configured_entry':8,'resident_limit':8,'pin_limit':8,'eligibility':8,'slot':8}
    require(sum(block.values())==232,'G2 lexical locals arithmetic')
    resident={'row':8,'seven_word_field_refs':56,'occupied_function_bytes_pins':32,'sum_named_binding':8}
    pin={'pin':8,'row':8,'entry_nonce_refs':16,'entry_nonce_words':16,'back_row':8,'back_occupied_and_pin_refs':16}
    # These are complete actual API object capacities. Source payload bytes in
    # arena/Candidate and named output binding aliases are not allocated again.
    chunks_t={'receiver_source':16,'receiver_received':16,'width_operand':8,'nonzero_operand_pair_and_bool':17,'quotient_operand_pair':16,'quotient_result':8,'remainder_operand_pair':16,'remainder_result':8,'chunk_count':8,'tail_count':8,'tail_offset_operand_pair':16,'tail_offset_result':8,'tail_address_operand_pair':16,'tail_address_result':8,'tuple_constructor_source':32,'tuple_designated_return':32,'tuple_caller_received':32}
    first_t={'receiver_source':16,'receiver_received':16,'width_operand':8,'length_operands_and_bool':17,'Option_pointer_constructor':8,'Option_pointer_designated_return':8,'Option_pointer_received':8,'expect_self_argument_source':8,'expect_self_received':8,'expect_message_source':16,'expect_message_received':16,'expect_return_reference_source':8,'expect_return_reference_received':8}
    index_t={'receiver_source':8,'receiver_received':8,'index_source':8,'index_received':8,'bound_operand_pair_and_bool':17,'scale_operand_pair_and_result':24,'address_operand_pair_and_result':24,'reference_return_source':8,'reference_return_received':8,'explicit_row_reborrow_source':8,'explicit_row_reborrow_received':8}
    le_t={'array_argument_received':8,'converted_word_source':8,'designated_word_return':8,'caller_word_received':8,'source_pointer_operand':8,'received_pointer_operand':8}
    checked_t={'self_argument_source':8,'self_received':8,'rhs_argument_source':8,'rhs_received':8,'sum_arithmetic':8,'overflow_bool':1,'Option_constructor':16,'Option_designated_return':16,'Option_received':16,'Some_pattern_bool':1}
    range_t={'Range_source':16,'Range_received':16,'receiver_source':16,'receiver_received':16,'view_return_source':16,'view_received':16,'predicate_operand_pair_and_bool':17,'address_result':8,'length_result':8}
    copy_t={'destination_receiver_received':16,'source_receiver_received':16,'shared_source_fat_view':16,'predicate_pair_and_bool':17,'complete_unit_controls':3}
    reply_t={'reason_argument_source':8,'reason_received':8,'complete_reply_constructor':24,'complete_reply_designated_return':24,'complete_reply_received':24}
    primitive={'active_operands_and_result':24,'predicate_result_source_and_received':2,'retained_short_circuit_outer_operand':8}
    ts={'as_chunks':chunks_t,'first_chunk_expect':first_t,'Index_fixed_row':index_t,'LE_decode':le_t,'checked_Option16':checked_t,'range_view':range_t,'copy':copy_t,'reject_reply':reply_t,'primitive':primitive,'LE_encode':{'self_received':8,'array_constructor':8,'array_designated_return':8,'array_received_temporary':8}}
    phases=[]
    def phase(name,named,temps):
        places={**{f'base.{k}':v for k,v in base.items()},**{f'block.{k}':v for k,v in named.items()}}
        for t in temps:
            for n,v in ts[t].items(): places[f'{t}.{n}']=v
        phases.append({'id':name,'places':places,'added_Control':sum(places.values()),'added_Wire':24,'added_Setup':80,'added_Report':0,'lifetime_scope':'all named locals retained to lexical scope end; active API source/received/return objects coexist, no last-use retirement'})
    # Conservatively keep all232 block locals already live even on earlier
    # construction calls. Early phases therefore overbound true scopes.
    phase('view.as_chunks',block,['as_chunks','range_view','primitive'])
    phase('view.first_chunk_expect',block,['first_chunk_expect','primitive'])
    phase('resident.row_index',{**block,**resident},['Index_fixed_row','primitive'])
    phase('resident.LE_or_checked',{**block,**resident},['LE_decode','checked_Option16','primitive'])
    phase('resident.refusal',{**block,**resident},['reject_reply','checked_Option16','primitive'])
    phase('pin.backlink_index',{**block,**pin},['Index_fixed_row','primitive'])
    phase('pin.LE_or_refusal',{**block,**pin},['LE_decode','reject_reply','primitive'])
    phase('mask.store',{**block,'pin':8},['range_view','copy','LE_encode','primitive'])
    phase('post.refusal',{**block,'pin':8},['reject_reply','primitive'])
    maximum=max(p['added_Control'] for p in phases)
    require(maximum<=1280,'changed G2 Control allowance')
    return {'schema':1,'scope':'changed G2 phases only; unchanged caller objects enumerated from selected exact C3 semantic.resident.helper prefix; entire changed proposal and merge lifetime remains unselected','selected_C3_source_sha256':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8','caller_Control_base':480,'block_named_Control':232,'G2_maximum_added_Control':maximum,'G2_Control_allowance':1280,'G2_added_Wire':24,'G2_Wire_allowance':256,'G2_added_Setup':80,'G2_Setup_allowance':256,'new_Candidate_or_arena_payload':0,'source_payload_aliases':'all resident/pin words alias existing arena; all timestamp/index/mask destinations alias sole Candidate2048; borrowed row64/48 is a reference8, never an additional row payload','complete_capacity_rules':'array8 full received payload; Option16 source+designated return+received; niche Option_ref8 all full pointers; all tuple32 source/return/received; all slice16/Range16 source/receive; source and named returned binding are aliases only where stated','phases':phases,'whole_role_union_accepted':False,'machine_stack_or_libstd_bound':False,'changed_sort_lifetimes_accepted':False}

def main():
    comp=read('components.json'); upper=read('upper-bound.json')
    recipes=json.loads(gzip.decompress((HERE/'recipes.json.gz').read_bytes()))['recipes']
    ledger=json.loads(gzip.decompress((HERE/'complete-upper-ledger.json.gz').read_bytes()))
    result=arithmetic(comp,upper,recipes,ledger)
    mutations=[]
    for name,mutate in [('missing array8',lambda c,u,r,l:c['templates']['resident.occupied-other'].pop(next(i for i,x in enumerate(c['templates']['resident.occupied-other']) if x['kind']=='copy'))),('cap increase',lambda c,u,r,l:u.update(cap=2561)),('omit refusal family',lambda c,u,r,l:r.pop(next(i for i,x in enumerate(r) if x['label'].startswith('pin-stop.')))),('duplicate scalar event',lambda c,u,r,l:l['groups'][1]['events'].__setitem__(0,l['groups'][0]['events'][0])),('implementation acceptance overclaim',lambda c,u,r,l:u.update(complete_implementation_or_role_union_accepted=True))]:
        c,u,r,l=copy.deepcopy((comp,upper,recipes,ledger)); mutate(c,u,r,l)
        try: arithmetic(c,u,r,l)
        except ValueError: mutations.append({'case':name,'rejected':True})
        else: raise ValueError('mutation not rejected '+name)
    sem=finite_cases(); life=lifetimes()
    dump('finite-cases.json',sem); dump('G2-lifetimes.json',life)
    assembly=read('source-assembly.json'); source=(HERE/'source/cache_state.rs.txt').read_bytes()
    require(sha(source)==assembly['source_sha256'],'source digest drift')
    for binding in read('inputs.json')['inputs']:
        p=ROOT/binding['path']; require(sha(p.read_bytes())==binding['sha256'],'input drift '+binding['path'])
    receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(HERE/'check.py')],'python':sys.version,'platform':platform.platform(),'producer_imported':False,'arithmetic':result,'finite_source_relation_cases':sem['case_count'],'timestamp_identity_cases':sem['timestamp_identity_cases'],'G2_Control_max':life['G2_maximum_added_Control'],'mutations':mutations,'source_sha256':sha(source),'status':'finite independent arithmetic/source-model checks passed; root selection and independent source review required','Rust_compiler_runtime_native_UI_capture_process_inventory_Git_hosted':False,'all_group_implementation_or_GA_accepted':False}
    dump('check-result.json',receipt); print(json.dumps(receipt,indent=2))
if __name__=='__main__': main()
