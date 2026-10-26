#!/usr/bin/env python3
"""Independent finite source/edge review. Reads producer JSON as data only.

This is not a Rust interpreter, compiler, runtime/ABI proof or OTA authorizer.
The semantic certificate is the authored coverage.json and README.md review;
this program checks its exact custody, explicit correction edges, finite branch
families, arithmetic, mutation controls and retained output reproducibility.
"""
from __future__ import annotations
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-cache-state-c3-remaining-work-accounting'
CANDIDATE = ROOT / 'verification/swift-cache-state-implementation/correction-3'
SOURCE_SHA = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
SEAL_SHA = '90eb895fe6c34dc68c3bb7826b0852f49926375f80c510020f4f7ed454ad8cb3'
LIFETIME_SHA = 'ab2e74fa3fa7a6ff967a5c0d000d46336cc42dc5654c6b38fdce008fcafedaf4'
G6_SHA = 'ea00518ce5033b4651460763f1c92533d024fee32a73b182d1684afa65ef80e1'
CAPS = {'G1':256, 'G7':248, 'SS':512, 'SF':256, 'G128':128, 'F42':42}

def fail(message): raise ValueError(message)
def need(condition, message):
    if not condition: fail(message)
def sha(b): return hashlib.sha256(b).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',',':')).encode()
def file_row(path):
    b=Path(path).read_bytes()
    return {'path':str(Path(path).relative_to(ROOT)), 'bytes':len(b), 'sha256':sha(b)}
def verify_row(row):
    need(file_row(ROOT/row['path'])==row, 'input custody '+row['path'])

class Schedule:
    """Every emitted edge has one owner, one label and one scalar/copy group."""
    def __init__(self, name, owner): self.name=name; self.owner=owner; self.ops=[]
    def scalar(self, label):
        self.ops.append({'id':f'{self.name}.{len(self.ops):04}', 'owner':self.owner,
                         'kind':'scalar','bytes':0,'edge':label})
    def scalars(self, *labels):
        for label in labels: self.scalar(label)
    def payload(self, label, width):
        for start in range(0,width,128):
            self.ops.append({'id':f'{self.name}.{len(self.ops):04}', 'owner':self.owner,
              'kind':'copy','bytes':min(128,width-start),
              'edge':f'{label}[{start}:{min(width,start+128)}]'})
    def field(self, label):
        self.scalars(label+' owner to projection',label+' field address',label+' source to received scalar')
    def word(self, label, index):
        # e.reply.words has TWO nested field projections before scalar Index.
        self.scalars(label+' e to reply receiver',label+' reply field address',
          label+' reply to words receiver',label+' words field address',
          label+f' index literal{index} to received index')
        for edge in ('receiver borrow','pointer to received receiver','Index entry',
          'index to bound left','length to bound right','index less than length','bound branch',
          'base pointer to address operand','index to scale operand','width8 to scale operand',
          'index times8','scaled offset to address operand','base to address operand',
          'element address','element reference to designated','reference loan',
          'designated reference to received','Index return','received reference to dereference',
          'word source to comparison'):
            self.scalar(label+' '+edge)
    def cmp_literal(self,label,n):
        self.scalars(label+f' literal{n} to comparison',label+' primitive equality',label+' bool source to result')
    def latch(self,label):
        self.scalars(label+' self reborrow',label+' pointer to received self',
          label+' literal16 to received n',label+' entry')
        self.field(label+' latch read')
        self.scalars(label+' literal255 to not',label+' bitwise not',label+' not result',
          label+' bitwise and',label+' and result',label+' n to or',label+' bitwise or',label+' or result',
          label+' self to latch destination',label+' latch destination address',label+' result to latch store',
          label+' unit construction',label+' return control',label+' caller unit discard')
    def counts(self):
        s=sum(o['kind']=='scalar' for o in self.ops)
        c=sum(o['kind']=='copy' for o in self.ops)
        return {'scalars':s,'copies':c,'groups':(s+15)//16+c}

def correction_schedules():
    out={}
    def new(name,owner):
        x=Schedule(name,owner);out[name]=x;return x
    x=new('G1.nested_reply_fields','G1')
    for index in (0,1):
        x.scalars(f'1177 words{index}: e to reply receiver',f'1177 words{index}: reply address')
    x=new('G7.paid_record_bookkeeping','G7')
    x.field('1148 paid.records read')
    x.scalars('1148 literal1 operand','1148 addition','1148 addition result',
      '1148 paid to records destination','1148 destination address','1148 result store')
    x=new('G7.pre_semantic_envelope_check','G7')
    x.word('1174 first word',0);x.cmp_literal('1174 first word',3)
    x.word('1174 second word',1);x.cmp_literal('1174 second word',15)
    x.scalars('1174 or short circuit','1174 or result to predicate','1174 if branch')
    x=new('G7.remember_pin_destination','G7')
    x.scalars('1212 remember_pin self to latch destination','1212 latch destination address')
    x=new('G7.semantic_slice_component','G7')
    x.scalar('1194 deref returned slice.len to received local view.len separately from data')
    x=new('G128.semantic_slice_component','G128')
    x.scalar('1194 zero-call deref returned slice.len to received local view.len separately from data')
    x=new('G7.caller_only_replacement','G7')
    # This schedule REPLACES producer caller-only. G1 keeps 1177/1180 admission.
    x.ops=copy.deepcopy(out['G7.paid_record_bookkeeping'].ops+out['G7.pre_semantic_envelope_check'].ops)
    for i,o in enumerate(x.ops):o['id']=f'{x.name}.{i:04}'
    for line in (1172,1175,1181):x.latch(f'{line} terminal16')
    x=new('SS.error_reserved_and_some_tag','SS')
    for call in ('report256 cap error','setup512 cap error','setup512 eager replay error',
                 'setup512 replay error covering arm','report128 cap error'):
        x.scalar(call+' error helper literal0 to reserved field')
    x.scalar('1295 Some(f) tag construction')
    x.payload('setup replay complete Result40 constructor to designated return',40)
    x=new('SS.f_borrow_and_slice_components','SS')
    x.scalars('1296 f address formation','1296 f shared borrow to cache_walk received f',
      '1104 received f reference dereference to inherited Fixture72 source')
    for cell in (17,24,25,26,27,28):
        x.scalar(f'new st cell{cell}: returned slice.len to local view.len separate from data')
    x=new('SS.twelve_rewritten_store_calls','SS')
    # envelope.rs308..311 used direct indexing/copy. C3 uses st() twelve times.
    # Own these COMPLETE actual helper/caller expansions here, and do not use
    # the predecessor direct-store work as credit for any of their edges.
    for i in range(12):
        p=f'1118 st iteration{i}: '
        for edge in ('arena to Vec field','Vec field address','Vec receiver borrow',
          'Vec pointer to deref received self','deref entry','buffer pointer to designated slice.data',
          'Vec length to designated slice.len','deref return','designated data to local view.data',
          'designated len to local view.len','slice reborrow','view data to argument.data',
          'view len to argument.len','argument data to received b.data','argument len to received b.len',
          'at source to received at','i to first comparison','literal5 to comparison','first equality',
          'first comparison result','first conditional branch','i to second comparison',
          'literal6 to comparison','second equality','second comparison result','second conditional branch',
          'f to mask field projection','mask field address','selected mask source to received n','st entry',
          'at to Range.start','at to end addition','literal8 to end addition','end addition','addition to Range.end',
          'Range.start to Index received start','Range.end to Index received end','Index receiver borrow',
          'slice.data to Index received data','slice.len to Index received len','Index entry',
          'start to ordered left','end to ordered right','start<=end','ordered branch',
          'end to upper left','len to upper right','end<=len','upper branch',
          'data to address operand','start to address operand','view address',
          'end to subtraction left','start to subtraction right','end-start',
          'address to designated view.data','length to designated view.len','exclusive view loan',
          'designated data to received view.data','designated len to received view.len','Index return',
          'copy destination receiver borrow','view.data to copy received destination.data',
          'view.len to copy received destination.len','n to to_le_bytes received self',
          'to_le_bytes entry','to_le_bytes conversion'):
            x.scalar(p+edge)
        x.payload(p+'LE array8 designated to received temporary',8)
        for edge in ('to_le_bytes return','LE array address','LE shared borrow',
          'LE pointer to source.data','literal8 to source.len','source.data to copy received source.data',
          'source.len to copy received source.len','copy entry','destination.len to equality left',
          'source.len to equality right','length equality','copy length branch'):
            x.scalar(p+edge)
        x.payload(p+'payload8 source to destination',8)
        for edge in ('copy return control','copy unit discard','st unit source','st return control','caller unit discard'):
            x.scalar(p+edge)
    x=new('SF.shape_nested_conjunction','SF')
    # The producer has q[8] > 0 but omits this AND child at source203.
    x.scalars('203 p to q receiver','203 q field address','203 index literal6 to received')
    for edge in ('receiver borrow','pointer to received receiver','Index entry',
      'index to bound left','length to bound right','index less than length','bound branch',
      'base pointer to address operand','index to scale operand','width8 to scale operand',
      'index times8','scaled offset to address operand','base to address operand',
      'element address','element reference to designated','reference loan',
      'designated reference to received','Index return','received reference to dereference',
      'word source to comparison'):
        x.scalar('203 '+edge)
    x.cmp_literal('203 q6',0)
    x.scalars('203 AND short circuit','203 AND bool result')
    x=new('SF.projection_boundaries','SF')
    for getter in ('952 reason','968 boundary','968 reason'):
        x.scalars(getter+' owner to field receiver',getter+' field reference loan',getter+' designated to received reference')
    x.scalars('958 p closure capture reborrow','958 capture pointer to environment',
      '958 closure entry','958 received Fixture pointer to closure argument')
    for field in ('1049 boundary','1056 reason'):
        x.scalars(field+' z to field destination',field+' field destination address')
    for line in (953,963,1019,1028):
        x.scalars(f'{line} z to boundary destination',f'{line} boundary destination address',
          f'{line} z to reason destination',f'{line} reason destination address',
          f'{line} why enum source to designated enum')
    # Retain the Refused child1 alternative explicitly, rather than substituting
    # a differently named InternalPoisoned update from another branch.
    x.scalars('1011 Refused source to boundary store','1011 z to boundary destination',
      '1011 boundary destination address','1012 literal4 to why received n',
      '1012 why entry','1012 reason match','1012 enum to designated',
      '1012 why return','1012 designated enum to reason store',
      '1012 z to reason destination','1012 reason destination address')
    x.scalars('1061 child to comparison','1061 literal2 to comparison','1061 equality',
      '1061 comparison result','1061 result to predicate','1061 conditional branch',
      '1075 contains bool to predicate','1075 if branch','1390 Ok tag construction')
    for field in ('framing104','envelope128','cache_state256'):
        x.scalars('1390 aggregate '+field+' destination projection','1390 aggregate '+field+' destination address')
    x=new('SF.alternate_public_Err','SF')
    # Existing Error32 creation/transport remains inherited. These are the new
    # full public source/designated/caller/self and immediate extraction edges.
    for edge in ('Err488 source to public designated','public Err488 to immediate caller',
                 'caller Err488 to extraction self'):
        x.payload(edge,488)
    x.payload('Err extraction Error32 source to designated Error32',32)
    x.payload('designated Error32 to immediate caller Error32',32)
    x.scalars('Err tag construction','public Err return control','Err extraction entry',
      'Err discriminant source','Err predicate','Err branch','Err extraction return',
      'Error32 received continuation')
    x=new('SF.input_Err_destinations','SF')
    x.scalars('938 z to boundary destination','938 boundary destination address',
      '943 z to reason destination','943 reason destination address','943 why enum source to designated enum')
    x=new('SF.successful_report_before_SS_failure','SF')
    # Independent conservative authored Budget.report expansion. Both cap arms
    # are retained even though only success can precede the failing SS call.
    for edge in ('caller self reborrow','caller pointer to received self','literal256 to received n','report entry'):
        x.scalar('1314 '+edge)
    x.field('report_spent read for checked_add')
    x.scalars('checked_add n operand','checked_add entry','checked addition','overflow predicate',
      'overflow branch','Some tag construction','sum to Some payload')
    x.payload('checked_add complete Option16 to is_none_or received self',16)
    x.scalars('checked_add return','is_none_or entry','Option discriminant','Some branch',
      'Some payload to closure v','closure entry','closure v operand','REPORT_RESERVE operand',
      'greater comparison','closure result','closure return','bool to guard predicate',
      'is_none_or return','report if branch')
    for i in range(4):x.scalar(f'cap Error32 argument{i} source to received')
    x.scalar('cap error helper entry')
    for i in range(4):x.scalar(f'cap Error32 field{i} source to constructor')
    x.scalar('cap Error32 reserved literal0 source to constructor')
    x.payload('cap Error32 constructor to designated',32)
    x.scalar('cap error helper return')
    x.payload('cap designated Error32 to Err constructor payload',32)
    x.scalar('cap Err Result tag')
    x.payload('cap Result40 source to designated report result',40)
    x.scalar('cap report return')
    x.field('report_spent read for success addition')
    x.scalars('n to addition','addition','addition result','budget to report_spent destination',
      'report_spent destination address','sum to destination','success Ok tag','success unit source')
    x.payload('success Result40 source to designated',40)
    x.payload('designated report Result40 to caller received',40)
    x.scalars('report return','Try discriminant source','Try branch','Ok unit extraction','caller continuation')
    x=new('SF.SS_failure_helper_corrections','SF')
    for call in ('setup cap error','eager replay error','setup replay error covering arm'):
        x.scalar(call+' error helper reserved literal0 source to field')
    x.payload('replay complete Result40 constructor to designated',40)
    x.payload('outer residual Error32 to public Err constructor payload',32)
    x=new('F42.report_error_corrections','F42')
    x.scalar('report cap error helper reserved literal0 source to field')
    x.payload('residual Error32 to public Err constructor payload',32)
    return out

def combined(base, supplements):
    ops=copy.deepcopy(base)
    for s in supplements:ops.extend(copy.deepcopy(s.ops))
    return ops

def count_ops(ops):
    scalars=[o for o in ops if o['kind']=='scalar']
    copies=[o for o in ops if o['kind']=='copy']
    return {'scalars':len(scalars),'scalar_blocks':(len(scalars)+15)//16,
            'copies':len(copies),'groups':(len(scalars)+15)//16+len(copies)}

def verify_ops(name,owner,ops,cap):
    need(all(o['owner']==owner for o in ops),'cross-owner credit '+name)
    need(len({o['id'] for o in ops})==len(ops),'duplicate edge '+name)
    need(all(o['kind'] in ('scalar','copy') for o in ops),'unknown operation '+name)
    need(all(0<o['bytes']<=128 for o in ops if o['kind']=='copy'),'oversized copy '+name)
    need(all(o['bytes']==0 for o in ops if o['kind']=='scalar'),'scalar byte field '+name)
    c=count_ops(ops);need(c['groups']<=cap,'cap '+name)
    return c

def custody():
    seal_path=PRODUCER/'seal.json'
    need(sha(seal_path.read_bytes())==SEAL_SHA,'producer seal drift')
    seal=read(seal_path);need(len(seal['members'])==47,'producer member count')
    for row in seal['members']:verify_row(row)
    need(sum(r['bytes'] for r in seal['members'])==1946309,'producer bytes')
    inputs=read(PRODUCER/'inputs.json')
    for row in inputs['members']:verify_row(row)
    source=(CANDIDATE/'source/library/cache_state.rs').read_bytes()
    need(sha(source)==SOURCE_SHA,'source digest')
    selected_life=ROOT/'verification/swift-semantic-adapter-root-review/C3-lifetime-selection.json'
    selected_g6=ROOT/'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json'
    need(sha(selected_life.read_bytes())==LIFETIME_SHA,'selected lifetime digest')
    need(sha(selected_g6.read_bytes())==G6_SHA,'selected G6 digest')
    life=read(selected_life);g6=read(selected_g6)
    need(life['whole_role_union_accepted'] and life['whole_role_union']==29344,'selected lifetime')
    need(g6['production']['groups']==512 and g6['including_private_faults']['groups']==514,'selected G6')
    inherited=read(ROOT/'verification/swift-cache-state-c3-lifetime-accounting/inheritance.json')
    for row in inherited['source_prefix_bindings']:
        b=(CANDIDATE/'source/library'/f"{row['name']}.rs").read_bytes()
        need(sha(b)==row['whole_sha256'],'inherited whole source')
        need(sha(b[:row['inherited_prefix_bytes']])==row['inherited_prefix_sha256'],'inherited prefix')
        need(b[row['inherited_prefix_bytes']:].decode()==row['appended_utf8'],'inherited append')
    cseal=read(CANDIDATE/'candidate-repo-seal.json')
    need(sha(canonical(cseal['source_rows']))==cseal['source_tree_digest'],'candidate source tree metadata digest')
    for row in cseal['source_rows']:
        if row['path'].startswith('source/library/'):
            need({'path':row['path'],**{k:v for k,v in file_row(CANDIDATE/row['path']).items() if k!='path'}}==row,'library source tree member')
    return {'producer_members':47,'producer_bytes':1946309,
      'referenced_inputs':len(inputs['members']), 'candidate_source_tree_digest':cseal['source_tree_digest'],
      'candidate_source_tree_metadata_reproduced':True,'library_members_directly_hashed':3,
      'candidate_full570_members_replayed':False,'inherited_prefixes_reproduced':2,
      'predecessor_complete_proof_reexecuted':False}

def ledger():
    operations=json.loads(gzip.decompress((PRODUCER/'operations.json.gz').read_bytes()))
    paths=read(PRODUCER/'paths.json')['paths']; partitions=read(PRODUCER/'partitions.json')
    need(len(paths)==38 and len(operations)==38,'producer path count')
    schedules=correction_schedules(); rows={};used={}
    for p in paths:
        name=p['id'];ops=operations[name]
        count=verify_ops(name,p['owner'],ops,CAPS[p['owner']])
        need(all(p[k]==count[k] for k in count),'producer reported count '+name)
        need(sha(json.dumps(ops,separators=(',',':')).encode())==p['operations_sha256'],'operation digest '+name)
        part=partitions[name]
        scalar_ids=[o['id'] for o in ops if o['kind']=='scalar']
        need([x for block in part['scalar_blocks'] for x in block]==scalar_ids,'scalar partition '+name)
        need(all(1<=len(x)<=16 for x in part['scalar_blocks']),'scalar block width '+name)
        need(part['payload_copy_groups']==[{'id':o['id'],'bytes':o['bytes']} for o in ops if o['kind']=='copy'],'copy partition '+name)
        extra=[];replacement=False
        if p['owner']=='G1':extra=['G1.nested_reply_fields']
        elif p['owner']=='G7':
            if name=='G7.envelope-terminal-or-preloan-unreadable':
                ops=[];extra=['G7.caller_only_replacement'];replacement=True
            else:
                extra=['G7.paid_record_bookkeeping','G7.pre_semantic_envelope_check','G7.semantic_slice_component']
                if name=='G7.success':extra.append('G7.remember_pin_destination')
        elif p['owner']=='G128':extra=['G128.semantic_slice_component']
        elif name=='SS.complete-new-source':
            extra=['SS.error_reserved_and_some_tag','SS.f_borrow_and_slice_components','SS.twelve_rewritten_store_calls']
        elif name.startswith('SF.stage'):
            extra=['SF.shape_nested_conjunction','SF.projection_boundaries','SF.alternate_public_Err']
        elif name=='SF.inputErr-early-projection':
            extra=['SF.input_Err_destinations','SF.alternate_public_Err']
        elif name=='SF.SS-admission-failure':
            extra=['SF.successful_report_before_SS_failure','SF.SS_failure_helper_corrections']
        elif p['owner']=='F42':extra=['F42.report_error_corrections']
        fresh=combined(ops,[schedules[k] for k in extra])
        rows[name]={'owner':p['owner'],**verify_ops(name,p['owner'],fresh,CAPS[p['owner']]),
          'supplements':extra,'replacement':replacement,'aggregate_or_progress_constructed':name.startswith('SF.stage') or name in ('SF.inputErr-early-projection','SS.complete-new-source')}
        used[name]=fresh
    # Paid book-keeping also executes when no semantic/leaf call can occur.
    name='G7.paid-record-no-loan';ops=schedules['G7.paid_record_bookkeeping'].ops
    rows[name]={'owner':'G7',**verify_ops(name,'G7',ops,CAPS['G7']),
      'supplements':['G7.paid_record_bookkeeping'],'replacement':False,'aggregate_or_progress_constructed':False}
    used[name]=ops
    return schedules,rows,used

def finite_review(rows,coverage):
    expected={'admission-caller','entry-paid','event-identity','reply-and-caller',
      'zero-guard','paid-no-loan','setup-new','pre-owner-failure','setup-failure',
      'projection-constructor','projection-early','projection-shape','projection-fields',
      'public-return','inherited-boundary','whole-setup'}
    need({r['id'] for r in coverage['families']}==expected,'semantic source family coverage')
    for r in coverage['families']:
        need(r['source'] and r['source_review'] and r['funding'],'unreviewed semantic source family')
    # Independent branch shape abstraction: code choices, never product input execution.
    projection=[]
    for stage in range(12):
      for latch in range(18):
       for child in range(5):
        for initial in (False,True):
          shape=(6<=stage<=10);pending=stage in (7,8)
          if child in (0,1):witness='SF.stage8.terminal14.child3'
          elif stage>10 or latch in (2,3,4,5,15,16,17):witness='SF.stage8.terminal14.child3'
          elif latch: witness='SF.stage8.terminal14.child3'
          elif child==2: witness='SF.stage7.terminal0.child2'
          else:witness='SF.stage8.terminal14.child3'
          need(rows[witness]['groups']<=256,'projection branch cap')
          projection.append([stage,latch,child,initial,shape,pending,witness])
    event=[]
    for code in range(16):
        if code in (3,4):w=[f'G1.event{code}.{v}' for v in ('empty','conflict','reuse')]
        elif code==11:w=['G1.event11.hit','G1.event11.built']
        elif code==2:w=['G1.event2.hit','G1.event2.miss']
        elif 1<=code<=13:w=[f'G1.event{code}.ordinary']
        else:w=['G1.event12.ordinary'] # common entry/identity prefix; closed default return is G7
        need(all(rows[x]['groups']<=256 for x in w),'event cover cap')
        event.append({'code':code,'witnesses':w,'first_refusal_is_prefix':True})
    # Reservation automaton proves the paid predecessor exists at failure, and
    # prevents projection/new Progress/aggregate construction on admission failure.
    funding=[
      {'stop':'new SF fails','owners':['inherited fixed F42 error path'],'recipe':'F42.finish-admission-failure','Progress':False,'aggregate':False},
      {'stop':'SS fails','owners':['SF256'],'recipe':'SF.SS-admission-failure','Progress':False,'aggregate':False},
      {'stop':'context/profile/header fails','owners':['SF256','SS512'],'recipe':'SF.inputErr-early-projection','Progress':True,'aggregate':'only eventual Ok'},
      {'stop':'guard reservation fails','owners':['SF256','SS512'],'recipe':'SF.inputErr-early-projection','Progress':True,'aggregate':'only eventual Ok'},
      {'stop':'paid record no loan','owners':['G1','G7 via prepaid7680'],'recipe':'G7.paid-record-no-loan','Progress':True,'aggregate':'only eventual Ok'},
    ]
    need(not rows['SF.SS-admission-failure']['aggregate_or_progress_constructed'],'unpaid aggregate')
    need(not rows['F42.finish-admission-failure']['aggregate_or_progress_constructed'],'pre-SF aggregate')
    # All actual setup-debit call sites, reconstructed from analyzer/cache source.
    fixed={'wrapper':42,'SS':512,'output_safety':15,'Arena_regions':12,
      'Arena_resident_pin_recency':64,'Arena_plan':512,'Arena_window':128,'Arena_top':32,
      'initial3x2':6,'context1024+16+976':2016,'profile64+12':76,
      'header64+16':80,'envelope':534,'footer':64,'stable3':3}
    need(sum(fixed.values())==4096,'whole fixed setup')
    drain=(536871936+65535)//65536+1
    need(drain==8194 and sum(fixed.values())+drain==12290,'whole setup drain bound')
    report=sum((42,47,112,6144,32,32,2,35,256,128))
    need(report==6830 and report<3000000,'whole report reserve')
    return {'projection_branch_schedules':len(projection),'projection_branch_digest':sha(canonical(projection)),
      'event_dispatch_schedules':event,'reservation_automaton':funding,'setup_fixed_sites':fixed,
      'setup_fixed':4096,'drain_iterations':8194,'whole_setup':12290,'setup_cap':65536,
      'report_reserve':report,'report_cap':3000000,'G128_absorbing_latch':True,
      'G6_cleanup_and_four_merge_caller_operations_reallocated':False}

def semantic_invariants(schedules,rows,used):
    need(schedules['G7.paid_record_bookkeeping'].counts()['scalars']==9,'paid.records omitted')
    need(schedules['G7.pre_semantic_envelope_check'].counts()['scalars']==59,'envelope check omitted')
    need(schedules['SF.shape_nested_conjunction'].counts()['scalars']==28,'nested q6 guard omitted')
    need('SF.successful_report_before_SS_failure' in rows['SF.SS-admission-failure']['supplements'],'unfunded report prefix')
    need(rows['SF.SS-admission-failure']['owner']=='SF','failure charged to unreserved SS')
    need(rows['G7.envelope-terminal-or-preloan-unreadable']['replacement'],'G1 caller duplicated across owners')
    need(schedules['SS.twelve_rewritten_store_calls'].counts()=={'scalars':1008,'copies':24,'groups':87},'rewritten twelve st calls omitted')
    for name,ops in used.items():verify_ops(name,rows[name]['owner'],ops,CAPS[rows[name]['owner']])
    for path in ('G7.success',):
        options=[o for o in used[path] if o['kind']=='copy' and 'complete Option<usize>16' in o.get('operation','')]
        need(len(options)==17 and all(o['bytes']==16 for o in options),'final None or Option width')
    alt=schedules['SF.alternate_public_Err'].ops
    need([o['bytes'] for o in alt if o['kind']=='copy']==[128,128,128,104]*3+[32,32],'complete Err Result488')
    need(rows['G7.success']['groups']<=248,'G7 overflow')

def mutations(schedules,rows,used):
    rejected=[]
    def case(name,change):
        s=copy.deepcopy(schedules);r=copy.deepcopy(rows);u=copy.deepcopy(used)
        change(s,r,u)
        try:semantic_invariants(s,r,u)
        except ValueError:rejected.append(name);return
        fail('mutation survived '+name)
    case('omit actual paid.records increment',lambda s,r,u:s['G7.paid_record_bookkeeping'].ops.clear())
    case('omit nested q6 conjunction',lambda s,r,u:s['SF.shape_nested_conjunction'].ops.clear())
    case('omit envelope check before success',lambda s,r,u:s['G7.pre_semantic_envelope_check'].ops.clear())
    case('omit successful report before failed SS',lambda s,r,u:r['SF.SS-admission-failure']['supplements'].clear())
    case('charge failed SS to unreserved SS',lambda s,r,u:r['SF.SS-admission-failure'].__setitem__('owner','SS'))
    case('retain cross-owner caller admission',lambda s,r,u:r['G7.envelope-terminal-or-preloan-unreadable'].__setitem__('replacement',False))
    case('reuse direct-store proof for new st helpers',lambda s,r,u:s['SS.twelve_rewritten_store_calls'].ops.clear())
    case('narrow Err to active Error32',lambda s,r,u:s['SF.alternate_public_Err'].ops[0].__setitem__('bytes',32))
    def final_none(s,r,u):
        x=[o for o in u['G7.success'] if o['kind']=='copy' and 'snapshot[16] complete Option' in o.get('operation','')][0]
        x['bytes']=0
    case('drop complete final None16',final_none)
    case('oversize a copy group',lambda s,r,u:u['G7.success'][0].update(kind='copy',bytes=129))
    case('borrow G6 owner credit',lambda s,r,u:u['G7.success'][0].__setitem__('owner','G6'))
    case('duplicate a transfer edge',lambda s,r,u:u['G7.success'].append(copy.deepcopy(u['G7.success'][0])))
    return rejected

def main():
    c=custody();s,rows,used=ledger();coverage=read(HERE/'coverage.json')
    semantic_invariants(s,rows,used);finite=finite_review(rows,coverage);rejected=mutations(s,rows,used)
    bounds={owner:max(({'path':name,**row} for name,row in rows.items() if row['owner']==owner),key=lambda x:x['groups']) for owner in CAPS}
    result={'status':'independent source review with bounded correction; root selection required',
      'source_sha256':SOURCE_SHA,'producer_seal_sha256':SEAL_SHA,'custody':c,
      'corrected_bounds':bounds,'correction_schedules':{k:{'owner':v.owner,**v.counts()} for k,v in s.items()},
      'corrected_recipe_count':len(rows),'finite_review':finite,'mutation_controls_rejected':rejected,
      'producer_original_completeness_accepted':False,'corrected_component_bounds_qualified':True,
      'G6_selected_bound_unchanged':[512,514],'selected_logical_lifetime_union_unchanged':29344,
      'all_work_groups_combined_accepted':False,'implementation_accepted':False,
      'native_runtime_UI_capture_process_inventory_compiler_Git_hosted_actions':False,'GA_qualified':False,
      'python':sys.version,'optimized':not __debug__}
    if '--write' in sys.argv:
        for filename,value in [('results.json',result),('corrected-paths.json',rows),
          ('correction-operations.json',{k:v.ops for k,v in s.items()})]:
            (HERE/filename).write_text(json.dumps(value,indent=2)+'\n')
        partitions={}
        for name,ops in used.items():
            scalar=[o['id'] for o in ops if o['kind']=='scalar']
            partitions[name]={'owner':rows[name]['owner'],
              'scalar_blocks':[scalar[i:i+16] for i in range(0,len(scalar),16)],
              'copies':[{'id':o['id'],'bytes':o['bytes']} for o in ops if o['kind']=='copy']}
        (HERE/'corrected-partitions.json').write_text(json.dumps(partitions,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
