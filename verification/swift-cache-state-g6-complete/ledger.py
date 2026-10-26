#!/usr/bin/env python3
"""Source-model ledger only. Never imports, compiles, or runs Mixer code."""
from __future__ import annotations
import contextlib
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'verification/swift-semantic-adapter-root-review/clear128-anonymous-proposal/cache_state.rs'
SOURCE_SHA = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
REVIEW = ROOT / 'verification/swift-cache-state-g6-independent-review'
SELECTION = ROOT / 'verification/swift-semantic-adapter-root-review/clear128-correction3-selection.json'
EXPECTED = {
    SOURCE: SOURCE_SHA,
    REVIEW/'seal.json': '21343e183de35954dc39f74c27dbca01afed0f91793fac9d3d68ae1682a199e9',
    SELECTION: '1fc73e9daa6ba38009fa4f30a68285b0ee0977169198a8f3da0be1b94a606c4e',
    ROOT/'docs/swift-cache-state-clear128-selection.md': 'd101318adea51e0de069c9cbd443d08a9dd21e17ba23b12b73bdb0083e2fd946',
    ROOT/'verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json': '7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f',
}

def digest(b): return hashlib.sha256(b).hexdigest()
def write(name, value): (HERE/name).write_text(json.dumps(value, indent=2)+'\n')
def info(p):
    b=p.read_bytes()
    return {'path':str(p.relative_to(ROOT)), 'bytes':len(b), 'sha256':digest(b)}

# An expression encoding is source notation for a ledger, not an interpreter of
# record data. Paths are authored separately; arithmetic is NEVER performed on
# Mixer records by this tool.
def V(n): return ('value',n)
def K(n): return ('literal',str(n))
def F(n): return ('field',n)
def I(n,i): return ('index',n,K(i) if isinstance(i,int) else i)
def B(op,a,b): return ('binary',op,a,b)
def U(op,a): return ('unary',op,a)
def CAST(a,ty): return ('cast',ty,a)
def LOAD(kind,*args): return ('load',kind,*args)
def SELECT(condition,selected): return ('select',condition,selected)
def CONVERT(a): return ('convert',a)

class Trace:
    def __init__(self,name):
        self.name=name; self.ops=[]; self.owner='G6'; self.line=0; self.label='entry'; self.segments=[]
    def op(self,text,kind='scalar',width=0):
        self.ops.append({'id':f'{self.name}.{len(self.ops):05}', 'owner':self.owner,
                         'line':self.line,'site':self.label,'operation':text,
                         'kind':kind,'bytes':width})
    def opset(self,*texts):
        for t in texts: self.op(t)
    def copy(self,text,width):
        assert 0<width<=128
        self.op(text,'copy',width)
    @contextlib.contextmanager
    def site(self,line,label,owner='G6'):
        previous=(self.line,self.label,self.owner); self.line=line; self.label=label; self.owner=owner
        begin=len(self.ops)
        yield
        block=self.ops[begin:]
        self.segments.append({'line':line,'site':label,'owner':owner,'first_operation':begin,'operation_count':len(block),
                              'scalars':sum(x['kind']=='scalar' for x in block),'copies':sum(x['kind']=='copy' for x in block),
                              'ordered_operations_sha256':digest(json.dumps(block,separators=(',',':')).encode())})
        self.line,self.label,self.owner=previous
    def e(self,a,target):
        kind=a[0]
        if kind in ('value','literal'):
            self.op(f'{kind} {a[1]} source -> {target}')
        elif kind=='field':
            if a[1].startswith(('RESIDENT.','PIN.','PLAN.','SCALAR.','rr.Region.','pr.Region.','pl.Region.')):
                self.opset(f'{a[1]} constant Region.base -> materialized source field',
                           f'{a[1]} constant Region.rows -> materialized source field',
                           f'{a[1]} constant Region.stride -> materialized source field')
            self.opset(f'{a[1]} owner pointer -> field projection operand',f'{a[1]} field address projection',f'{a[1]} field source -> {target}')
        elif kind=='index':
            _,base,index=a
            if '.' in base:
                self.opset(f'{base} parent pointer -> field projection',f'{base} array field address projection')
            self.e(index,f'{base} Index received index')
            self.opset(f'{base} scalar Index receiver borrow',f'{base} thin pointer -> Index received receiver','scalar Index entry control',
                'received index -> upper predicate left',f'{base} fixed element length -> upper predicate right','index<length predicate','index check branch',
                f'{base} pointer -> address operand','received index -> scaling operand','element width8 -> scaling operand','index*8',
                'scaled offset -> pointer-add operand',f'{base} pointer -> pointer-add operand','element address formation',
                'element address -> returned reference source','indexed reference loan creation',
                'returned indexed reference -> caller received reference','scalar Index return control',
                'received reference dereference -> scalar value source',f'indexed scalar source -> {target}')
        elif kind=='binary':
            _,op,l,r=a; self.e(l,f'{op} left received operand'); self.e(r,f'{op} right received operand')
            self.opset(f'primitive {op}',f'{op} result source -> {target}')
        elif kind in ('unary','cast'):
            _,op,v=a; self.e(v,f'{op} received operand'); self.opset(f'primitive {op}',f'{op} result source -> {target}')
        elif kind=='load':
            _,name,*args=a
            if name=='ld': self.ld(args[0],args[1],target)
            elif name=='cq': self.cq(args[0],target)
            else: self.rowload(name,args[0],args[1],target)
        elif kind=='select': self.choose(a[1],a[2],target)
        elif kind=='convert':
            self.e(a[1],'u64::from received bool'); self.opset('bool->u64 conversion entry','bool->u64 conversion',
                f'converted u64 source -> {target}','conversion return control')
        else: raise AssertionError(a)
    def guard(self,*exprs,logic='or'):
        for n,e in enumerate(exprs):
            self.e(e,f'{logic} child[{n}] source')
            if n+1<len(exprs): self.op(f'{logic} short-circuit branch[{n}]')
        self.opset(f'{logic} result source -> if predicate','if control branch')
    def choose(self,condition,selected,target):
        self.guard(condition); self.e(selected,target)
    def handle(self,base,target,array=False):
        if array:
            self.opset(f'{base} array address formation',f'{base} reborrow creation',f'{base} address -> slice.data source',
                       f'{base} array length2048 -> slice.len source',f'slice.data -> {target}.data',f'slice.len -> {target}.len')
        else:
            self.opset(f'{base} slice reborrow',f'{base}.data -> argument.data source',f'{base}.len -> argument.len source',
                       f'argument.data source -> {target}.data',f'argument.len source -> {target}.len')
    def thin(self,base,target): self.opset(f'{base} thin reference reborrow',f'{base} pointer source -> {target}')
    def rangeview(self,base,start,end,array=False,exclusive=False):
        self.e(start,f'{base} Range.start source'); self.e(end,f'{base} Range.end source')
        self.opset('Range.start -> Index received start','Range.end -> Index received end',f'{base} Index receiver borrow creation',
                   f'{base} receiver.data -> Index received receiver.data')
        if not array: self.op(f'{base} receiver.len -> Index received receiver.len')
        self.opset('Index operation entry control','received start -> ordered predicate left','received end -> ordered predicate right',
                   'start<=end predicate','ordered check branch','received end -> upper predicate left',
                   f'{base} length source -> upper predicate right','end<=length predicate','upper check branch',
                   f'{base} base pointer -> address operand','received start -> address operand','view address formation',
                   'received end -> length-subtraction left','received start -> length-subtraction right','view length end-start',
                   'address result -> returned view.data','length result -> returned view.len',
                   f'projected {"exclusive" if exclusive else "shared"} view loan creation',
                   'returned view.data -> caller received view.data','returned view.len -> caller received view.len','Index return control')
    def copytail(self,width):
        self.opset('copy entry control','copy receiver.len -> equality left','copy source.len -> equality right',
                   'source/destination length equality','copy length check branch')
        self.copy('actual source payload -> destination payload',width)
        self.opset('copy unit/control returned -> caller','unit discard and statement continuation')
    def direct(self,dst,ds,de,src,ss,se,width):
        self.rangeview(dst,ds,de,array=dst=='c',exclusive=True)
        self.opset('copy receiver reborrow','destination view.data -> copy receiver.data','destination view.len -> copy receiver.len')
        self.rangeview(src,ss,se,array=src=='c')
        self.opset('explicit shared source slice reborrow','source view.data -> copy source.data','source view.len -> copy source.len')
        self.copytail(width)
    def stbody(self):
        self.rangeview('st.b',V('st.at'),B('+',V('st.at'),K(8)),exclusive=True)
        self.opset('copy receiver reborrow','destination view.data -> copy receiver.data','destination view.len -> copy receiver.len',
                   'st.n source -> to_le_bytes received self','to_le_bytes entry control','u64 to_le_bytes conversion')
        self.copy('to_le_bytes full returned array8 -> received LE temporary8',8)
        self.opset('to_le_bytes return control','LE array address formation','shared LE-array borrow','LE array address -> source view.data',
                   'LE array length8 -> source view.len','source view.data -> copy received source.data','source view.len -> copy received source.len')
        self.copytail(8)
        self.unit_return('st')
    def unit_return(self,name): self.opset(f'{name} implicit unit source construction',f'{name} unit/control return -> caller',f'{name} unit discard and caller continuation')
    def st(self,at,n,base='c'):
        self.handle(base,'st.received_b',array=base=='c'); self.e(at,'st.received_at'); self.e(n,'st.received_n')
        self.op('st entry control'); self.stbody()
    def sq(self,i,n):
        self.thin('c','sq.received_c'); self.e(i,'sq.received_i'); self.e(n,'sq.received_n'); self.op('sq entry control')
        self.handle('sq.c','st.received_b',array=True)
        self.e(B('+',K('SC1688'),B('*',K(8),V('sq.i'))),'st.received_at'); self.e(V('sq.n'),'st.received_n')
        self.op('nested st entry control'); self.stbody(); self.unit_return('sq')
    def ldbody(self,target):
        self.rangeview('ld.b',V('ld.at'),B('+',V('ld.at'),K(8)))
        self.opset('first_chunk receiver reborrow','slice.data -> first_chunk receiver.data','slice.len -> first_chunk receiver.len','first_chunk entry control',
                   'width8 source -> first_chunk length predicate','receiver.len -> first_chunk length predicate','first_chunk length>=8 predicate','first_chunk success branch',
                   'borrow returned array8 reference','Some pointer source construction','complete Option<&array8> pointer -> caller received Option pointer','first_chunk return control',
                   'caller received Option pointer -> expect received self',
                   'static expect text address -> message.data source','static expect text length -> message.len source',
                   'message.data -> expect received message.data','message.len -> expect received message.len','expect entry control',
                   'Option pointer -> tag predicate','Some tag predicate','expect Some branch','unwrapped array pointer source -> returned reference',
                   'returned array reference -> caller received reference','expect return control')
        self.opset('received array reference -> dereference address operand','dereferenced array source address projection')
        self.copy('dereferenced array8 source -> from_le_bytes full received argument8',8)
        self.opset('from_le_bytes entry control','u64 from_le_bytes conversion','decoded word -> ld designated output','from_le_bytes return control',
                   f'ld output -> {target}','ld return control')
    def ld(self,base,at,target):
        self.handle(base,'ld.received_b',array=base=='c'); self.e(at,'ld.received_at'); self.op('ld entry control'); self.ldbody(target)
    def cq(self,i,target):
        self.thin('c','cq.received_c'); self.e(i,'cq.received_i'); self.op('cq entry control')
        self.ld('c',B('+',K('SC1688'),B('*',K(8),V('cq.i'))),'cq designated output')
        self.opset(f'cq output source -> {target}','cq return control')
    def rowload(self,kind,row,field,target):
        stride={'rr':64,'pr':48,'pl':40}[kind]
        self.handle('b',f'{kind}.received_b'); self.e(row,f'{kind}.received_row'); self.e(field,f'{kind}.received_field'); self.op(f'{kind} entry control')
        offset=B('+',B('+',F(f'{kind}.Region.base'),B('*',K(stride),V(f'{kind}.row'))),B('*',K(8),V(f'{kind}.field')))
        self.ld('b',offset,f'{kind} designated output'); self.opset(f'{kind} output -> {target}',f'{kind} return control')
    def within(self):
        self.e(K(1944),'within Range.start source'); self.e(K(2008),'within Range.end source'); self.e(K(1536),'within received destination')
        self.opset('within Range.start -> received start','within Range.end -> received end','Candidate within receiver reborrow',
                   'Candidate pointer -> within received receiver','within entry control','start -> ordered left','end -> ordered right','start<=end predicate','ordered branch',
                   'end -> upper left','Candidate length2048 -> upper right','end<=length predicate','source upper branch',
                   'end -> count left','start -> count right','count=end-start','count -> received count local',
                   'destination -> destination-check left','Candidate length2048 -> destination-check right','destination<=length predicate','destination-check branch',
                   'Candidate length2048 -> subtraction left','destination -> subtraction right','available=length-destination',
                   'count -> fit predicate left','available -> fit predicate right','count<=available predicate','fit branch',
                   'Candidate base -> source-address left','start -> source-address right','source address formation',
                   'Candidate base -> destination-address left','destination -> destination-address right','destination address formation')
        self.copy('copy_within complete source64 -> destination64, overlap-safe primitive',64)
        self.opset('within unit/control return -> caller','unit discard and statement continuation')
    def checked(self,op,l,r,name,success=True):
        self.e(l,f'{name} checked receiver'); self.e(r,f'{name} checked argument')
        self.opset(f'checked_{op} entry control',f'checked {op} arithmetic',f'checked {op} overflow predicate','overflow branch',
                   f'{"Some" if success else "None"} Option tag source construction')
        if success: self.op(f'arithmetic result -> {name} Some payload source')
        self.copy(f'complete Option<u64>16 source -> {name} received Option16',16)
        self.opset(f'checked_{op} return control',f'{name} received Option.tag -> pattern operand','Some pattern predicate','pattern control branch')
        if success: self.op(f'{name} received Some payload -> {name} binding')
    def loop(self,count,body,label):
        self.opset(f'{label} literal0 -> Range.start source',f'{label} literal{count} -> Range.end source',
                   f'{label} Range.start -> IntoIterator received.start',f'{label} Range.end -> IntoIterator received.end',
                   f'{label} IntoIterator entry control',f'{label} received Range.start -> returned iterator.start source',
                   f'{label} received Range.end -> returned iterator.end source',f'{label} iterator.start source -> received iterator.start',
                   f'{label} iterator.end source -> received iterator.end',f'{label} IntoIterator return control',
                   f'{label} received iterator.start -> iterator binding.start',f'{label} received iterator.end -> iterator binding.end')
        for i in range(count+1):
            self.opset(f'{label}[{i}] iterator exclusive borrow',f'{label}[{i}] iterator pointer -> next received self',f'{label}[{i}] next entry control',
                       f'{label}[{i}] current -> guard left',f'{label}[{i}] end -> guard right',f'{label}[{i}] current<end predicate',f'{label}[{i}] next guard branch')
            if i<count:
                self.opset(f'{label}[{i}] current -> Some payload source',f'{label}[{i}] Some tag source',f'{label}[{i}] current -> increment operand',
                           f'{label}[{i}] literal1 -> increment operand',f'{label}[{i}] iterator increment',f'{label}[{i}] increment result -> iterator.current')
            else: self.op(f'{label}[{i}] None tag source')
            self.copy(f'{label}[{i}] complete Option<usize>16 next source -> caller received16',16)
            self.opset(f'{label}[{i}] next return control',f'{label}[{i}] received Option.tag -> pattern operand',f'{label}[{i}] Some pattern predicate',f'{label}[{i}] for pattern branch')
            if i<count:
                self.op(f'{label}[{i}] Some payload source -> i binding'); body(i)
                self.opset(f'{label}[{i}] loop body implicit unit construction',f'{label}[{i}] loop back control')
        self.opset(f'{label} loop result unit construction',f'{label} for-statement continuation')

def w(i): return I('w',i)
def q(i): return I('p.q',i)
def cmp(op,a,b): return B(op,a,b)
def row(kind,slot,field): return LOAD(kind,slot,K(field))
def cq(i): return LOAD('cq',K(i))
def assign(t,n,e): t.e(e,f'local {n} received binding')

def event(t,kind,variant='',stop=''):
    # Ordinary admission/control retains G1 ownership. Including it in a looser
    # all-owned-operation upper is bounding slack, never a second G6 debit.
    with t.site(350,'three delta flag initializers','G1'):
        for n in ('resident_delta','pin_delta','plan_delta'): assign(t,n,K('ABSENT'))
    with t.site(452,'event match admission','G1'):
        t.e(w(1),'event match input'); t.op('one closed event match dispatch')
    def admit(line,label,*exprs):
        with t.site(line,label,'G1'): t.guard(*exprs)
    def store(line,fn,*args):
        with t.site(line,f'event{kind}.{fn}'): getattr(t,fn)(*args)
    def delta(line,name,value):
        with t.site(line,f'{name} install'): assign(t,name,value)
    if kind==1:
        for line,i,n in [(454,16,'ABSENT'),(455,17,'ABSENT'),(456,18,0),(457,10,0),(458,11,0),(459,12,0),(460,13,'ABSENT'),(461,14,'ABSENT'),(462,15,0)]: store(line,'sq',K(i),K(n))
    elif kind==2:
        admit(465,'nonce admission',cmp('==',q(9),K('ABSENT')))
        admit(468,'free pin admission',cmp('==',V('first_pin'),K('ABSENT')))
        with t.site(471,'lookup admission','G1'):
            t.guard(cmp('==',w(13),K(0)),cmp('!=',V('found'),K('ABSENT')),logic='and')
            t.guard(cmp('==',w(13),K(1)),cmp('!=',V('found'),w(10)),logic='and')
            t.opset('first conjunction result -> disjunction left','second conjunction result -> disjunction right','closed disjunction control branch')
        store(474,'sq',K(16),V('first_pin')); store(475,'sq',K(17),V('found'))
    elif kind in (3,4):
        outcome=2 if variant=='reuse' else 1
        with t.site(478,'plan cell/outcome admission','G1'):
            assign(t,'cell',CAST(B('&',w(6),K(511)),'usize'))
            assign(t,'prior',row('pl',V('cell'),0))
            t.guard(cmp('==',V('prior'),K('ABSENT'))); t.guard(cmp('==',V('prior'),w(6)))
            assign(t,'outcome',K(outcome))
            t.guard(cmp('==',V('outcome'),K(2)))
            if outcome==2: t.guard(*[cmp('!=',row('pl',V('cell'),i),w(6+i)) for i in (1,2,3)])
            t.guard(cmp('==',w(1),K(4)))
            if kind==4:
                t.guard(cmp('!=',w(13),V('outcome')))
                t.choose(cmp('==',V('outcome'),K(1)),V('prior') if outcome==1 else K('ABSENT'),'outcome-derived w14 comparator right')
                t.e(w(14),'w14 comparator left'); t.opset('w14!=derived predicate','w14 predicate branch')
                t.guard(cmp('!=',V('outcome'),K(2)))
        if kind==4 and outcome!=2:
            with t.site(497,'five-word plan staging loop'):
                def planbody(i):
                    if i==0: n=w(6)
                    else:
                        n=SELECT(cmp('<',V('i'),K(4)),I('w',B('+',K(6),V('i'))) if i<4 else K(0))
                    t.st(B('+',K(1648),B('*',V('i'),K(8))),SELECT(cmp('==',V('i'),K(0)),n))
                t.loop(5,planbody,'plan-stage')
            delta(510,'plan_delta',CAST(V('cell'),'u64'))
    elif kind==5:
        with t.site(515,'MissReady plan/byte admission','G1'):
            assign(t,'cell',CAST(B('&',w(6),K(511)),'usize'))
            t.guard(*[cmp('!=',row('pl',V('cell'),i),w(6+i)) for i in (0,1,2,3)])
            t.guard(cmp('!=',row('pl',V('cell'),4),K(0)),cmp('!=',row('pl',V('cell'),4),w(13)),logic='and')
            t.guard(cmp('==',w(13),K(0)),cmp('>',w(13),F('f.entry')),cmp('!=',w(14),F('f.base')),cmp('!=',w(15),F('f.capacity')))
            t.checked('add',F('f.base'),w(13),'capacity',True)
            t.opset('received Option tag -> is_none_or dispatch','is_none_or Some branch','Some payload -> closure v received',
                       'closure environment capacity field borrow')
            t.e(cmp('>',V('v'),F('f.capacity')),'closure bool result'); t.opset('closure return control','is_none_or result -> if predicate','if branch')
        with t.site(534,'plan source row staging'):
            start=B('+',F('PLAN.base'),B('*',K(40),V('cell')))
            t.direct('c',K(1648),K(1688),'b',start,B('+',start,K(40)),40)
        store(535,'st',K(1680),w(13)); delta(536,'plan_delta',CAST(V('cell'),'u64')); store(537,'sq',K(18),w(13))
        with t.site(538,'merge caller-only boundary'):
            t.thin('c','merge received c'); t.opset('merge call entry boundary; body owned G3/G4','merge received-unit statement continuation; implicit unit/callee return owned G4')
        # Exact headroom/prefix/feasibility source body542..561 belongs G5.
        if stop=='prefix-refusal': return False
        for line,i,n in [(562,10,V('mask')),(563,11,K(0)),(564,12,K(0)),(565,13,K('ABSENT'))]: store(line,'sq',K(i),n)
        with t.site(566,'feasible destination argument'):
            t.sq(K(14),SELECT(V('feasible'),V('destination') if variant!='infeasible' else K('ABSENT')))
        with t.site(567,'feasibility scalar conversion'):
            t.sq(K(15),CONVERT(V('feasible')))
    elif kind in (6,7,8):
        with t.site(570,'eviction identity/admission','G1'):
            t.guard(cmp('!=',q(15),K(1)))
            assign(t,'outstanding',B('&',q(10),U('!',q(12))))
            t.guard(cmp('==',V('outstanding'),K(0)))
            t.e(V('outstanding'),'trailing_zeros receiver'); t.opset('trailing_zeros entry','trailing_zeros primitive','trailing_zeros returned scalar')
            assign(t,'expected',CAST(V('trailing_zeros result'),'u64'))
            t.guard(cmp('!=',w(10),V('expected')),cmp('>=',V('expected'),F('f.slots')))
            assign(t,'slot',CAST(V('expected'),'usize')); t.guard(cmp('==',w(1),K(6)))
            if kind==6: t.guard(cmp('!=',row('rr',V('slot'),0),K(1)),cmp('!=',row('rr',V('slot'),3),K(0)),cmp('!=',row('rr',V('slot'),2),w(13)))
            else:
                t.guard(cmp('==',w(1),K(7)))
                if kind==7: t.guard(cmp('!=',q(13),V('expected')),cmp('!=',row('rr',V('slot'),0),K(1)),cmp('!=',row('rr',V('slot'),3),K(0)),cmp('!=',row('rr',V('slot'),2),w(13)))
                else:
                    t.guard(cmp('!=',q(13),V('expected')),cmp('==',B('&',q(11),B('<<',K(1),V('expected'))),K(0)),cmp('!=',row('rr',V('slot'),0),K(0)))
                    t.guard(cmp('!=',w(13),LOAD('ld','b',B('+',F('SCALAR.base'),B('*',K(138),K(8))))))
        if kind==6: store(587,'sq',K(13),V('expected'))
        elif kind==7:
            with t.site(596,'evicted resident zero source'): t.within()
            store(597,'st',K(1544),K('ABSENT')); delta(598,'resident_delta',V('expected'))
            store(599,'sq',K(6),B('-',V('count'),K(1))); store(600,'sq',K(7),B('-',V('total'),w(13)))
            store(601,'sq',K(11),B('|',q(11),B('<<',K(1),V('expected'))))
        else:
            store(610,'sq',K(12),B('|',q(12),B('<<',K(1),V('expected')))); store(611,'sq',K(13),K('ABSENT'))
    elif kind in (9,10):
        admit(615,'built boundary admission',cmp('!=',q(15),K(1)),cmp('!=',q(12),q(10)),cmp('!=',w(13),cq(18)))
    elif kind==11:
        admit(620,'publication nonce admission',cmp('!=',w(12),q(9)),cmp('==',q(9),K('ABSENT')))
        admit(623,'publication free pin admission',cmp('!=',V('first_pin'),cq(16)),cmp('!=',w(11),V('first_pin')),cmp('>=',V('first_pin'),F('f.pins')))
        with t.site(626,'publication slot identity','G1'):
            t.choose(cmp('==',w(13),K(0)),cq(17) if variant=='hit' else q(14),'slot initializer')
            assign(t,'slot',V('slot initializer')); t.guard(cmp('>=',V('slot'),F('f.slots')),cmp('!=',w(10),V('slot')))
            assign(t,'slot',CAST(V('slot'),'usize')); t.guard(cmp('==',w(13),K(0)))
            if variant=='hit': t.guard(cmp('!=',row('rr',V('slot'),0),K(1)),cmp('!=',row('rr',V('slot'),1),w(6)),cmp('!=',row('rr',V('slot'),2),w(14)))
            else: t.guard(cmp('!=',q(15),K(1)),cmp('!=',q(10),q(12)),cmp('!=',row('rr',V('slot'),0),K(0)),cmp('!=',w(14),cq(18)))
        if variant=='hit':
            with t.site(635,'hit resident source row'):
                start=B('+',F('RESIDENT.base'),B('*',V('slot'),K(64)))
                t.direct('c',K(1536),K(1600),'b',start,B('+',start,K(64)),64)
        else:
            with t.site(642,'built resident zero-tail source'): t.within()
            for line,at,n in [(643,1536,K(1)),(644,1544,w(6)),(645,1552,w(14)),(646,1576,w(3))]: store(line,'st',K(at),n)
            store(647,'sq',K(6),B('+',V('count'),K(1)))
            with t.site(648,'new staged resident-byte Option'):
                t.checked('add',V('total'),w(14),'sum',stop!='sum-refusal')
            if stop=='sum-refusal': return False
            store(651,'sq',K(7),V('sum'))
        with t.site(653,'new staged pin computation'):
            assign(t,'prior_pins',LOAD('ld','c',K(1560)))
            t.checked('add',V('prior_pins'),K(1),'pins',stop!='pin-overflow')
            if stop=='pin-overflow': return False
            t.guard(cmp('!=',w(15),V('pins')),cmp('>',V('pins'),F('f.pins')),cmp('==',q(8),F('f.pins')))
        if stop=='pin-refusal': return False
        for line,at,n in [(660,1560,V('pins')),(661,1568,w(4)),(662,1600,CAST(V('slot'),'u64')),(663,1608,w(12)),
                          (664,1616,w(3)),(665,1624,w(3)),(666,1632,w(4)),(667,1640,w(5))]: store(line,'st',K(at),n)
        delta(668,'resident_delta',CAST(V('slot'),'u64')); delta(669,'pin_delta',V('first_pin'))
        store(670,'sq',K(8),B('+',q(8),K(1))); store(671,'sq',K(9),B('+',q(9),K(1)))
    elif kind==12:
        with t.site(674,'release identity/admission','G1'):
            assign(t,'slot',CAST(w(10),'usize')); assign(t,'pin',CAST(w(11),'usize'))
            t.guard(cmp('>=',V('slot'),CAST(F('f.slots'),'usize')),cmp('>=',V('pin'),CAST(F('f.pins'),'usize')),
                    cmp('!=',row('pr',V('pin'),0),w(10)),cmp('!=',row('pr',V('pin'),1),w(12)))
            t.guard(cmp('!=',row('rr',V('slot'),0),K(1)),cmp('!=',row('rr',V('slot'),1),w(6)),cmp('!=',row('rr',V('slot'),2),w(13)),
                    cmp('==',row('rr',V('slot'),3),K(0)),cmp('==',q(8),K(0)),cmp('!=',w(15),B('-',row('rr',V('slot'),3),K(1))))
        with t.site(692,'release resident source row'):
            start=B('+',F('RESIDENT.base'),B('*',V('slot'),K(64)))
            t.direct('c',K(1536),K(1600),'b',start,B('+',start,K(64)),64)
        store(694,'st',K(1560),w(15))
        with t.site(695,'six-word pin reset staging loop'):
            def pinbody(i):
                t.st(B('+',K(1600),B('*',V('i'),K(8))),SELECT(cmp('==',V('i'),K(0)),K('ABSENT') if i==0 else K(0)))
            t.loop(6,pinbody,'pin-reset')
        delta(698,'resident_delta',w(10)); delta(699,'pin_delta',w(11)); store(700,'sq',K(8),B('-',q(8),K(1)))
    elif kind!=13: raise AssertionError(kind)
    return True

def final_commit(t,kind,variant,commit_fault=False,instrumented=False):
    for line,i,j in [(707,0,0),(708,1,4),(709,2,5)]:
        with t.site(line,'final coordinate sq'): t.sq(K(i),w(j))
    stage0=kind in (11,12,13)
    with t.site(710,'successor stage dispatch'):
        t.e(w(1),'stage match received input'); t.op('one closed stage match dispatch')
        if kind==2: t.guard(cmp('==',w(13),K(1)))
        stages={1:1,2:2 if variant=='lookup-hit' else 3,3:4,4:5,5:6,6:7,7:8,8:6,9:9,10:10,11:0,12:0,13:0}
        assign(t,'stage',K(stages[kind]))
    with t.site(728,'final stage sq'): t.sq(K(3),V('stage'))
    with t.site(729,'final operation sq'):
        t.sq(K(4),SELECT(cmp('==',V('stage'),K(0)),K(0) if stage0 else w(3)))
    with t.site(730,'final function sq'):
        t.sq(K(5),SELECT(cmp('==',V('stage'),K(0)),K('ABSENT') if stage0 else w(6)))
    resident=kind in (7,11,12); pin=kind in (11,12); plan=kind==5 or (kind==4 and variant!='reuse')
    for line,name,stride,width,base,ss,se,present in [
        (734,'resident_delta',64,64,'RESIDENT',1536,1600,resident),
        (745,'pin_delta',48,48,'PIN',1600,1648,pin),(749,'plan_delta',40,40,'PLAN',1648,1688,plan)]:
        with t.site(line,name+' commit guard'):
            t.guard(cmp('!=',V(name),K('ABSENT')))
            if present:
                assign(t,'at',B('+',F(base+'.base'),B('*',CAST(V(name),'usize'),K(stride))))
                t.direct('b',V('at'),B('+',V('at'),K(width)),'c',K(ss),K(se),width)
                if name=='resident_delta':
                    t.op('commit_succeeded call entry')
                    if instrumented or commit_fault: atomic_fault(t,'COMMIT_FAULT',negate=True)
                    else: t.op('production true literal -> commit_succeeded output')
                    t.opset('commit_succeeded output -> caller received bool','commit_succeeded return control','received bool -> ! operand','boolean !', '! result -> if predicate','commit failure branch')
                    if commit_fault: return
    # The source has12 literal already-LE copies, not loads/conversions.
    src=[1736,1744,1752,1760,1768,1776,1784,1792,1800,1808,1824,1832]
    dst=[7729928,7729936,7729944,7729896,7730784,7730800,7730808,7730856,7730432,7730888,7730328,7730384]
    for i,(s,d) in enumerate(zip(src,dst)):
        with t.site(753+i,f'literal scalar commit[{i}]'): t.direct('b',K(d),K(d+8),'c',K(s),K(s+8),8)
    with t.site(765,'pending-byte commit guard'):
        t.guard(cmp('==',w(1),K(6)))
        if kind==6: t.st(B('+',F('SCALAR.base'),B('*',K(138),K(8))),w(13),base='b')
    # All complete success/poison SemanticReply construction and moves belongG7.

def atomic_fault(t,name,negate=False):
    t.opset(f'{name} address formation',f'{name} receiver borrow',f'{name} pointer -> swap received receiver','literal false -> swap received value',
            'Ordering::Relaxed source -> swap received ordering','atomic swap entry','standard atomic swap primitive','swap returned bool -> caller received bool','atomic swap return control')
    if negate: t.opset('swap bool -> negation operand','boolean !','negation result -> commit return source')

def cleanup(t,clear_model,bad_length=False,cleanup_fault=False,instrumented=False):
    with t.site(1227,'actual cleanup caller and prologue'):
        t.opset('arena received pointer -> bytes field projection','arena.bytes Vec field address projection','Vec shared borrow creation','Vec pointer -> Deref received receiver',
                'Vec Deref entry control','Vec data field source -> returned slice.data','Vec len field source -> returned slice.len',
                'returned Vec slice.data -> caller received.data','returned Vec slice.len -> caller received.len','Vec Deref return control',
                'cleanup shared b argument reborrow','caller slice.data -> cleanup received b.data','caller slice.len -> cleanup received b.len',
                'Candidate cleanup exclusive argument borrow','Candidate pointer -> cleanup received c','cleanup entry control')
        t.opset('b.len receiver reborrow','b.data -> len received receiver.data','b.len -> len received receiver.len','len call entry',
                'len field source -> len designated output','len return control','len output -> != left operand','ARENA_BYTES literal -> != right operand',
                'length!=ARENA_BYTES predicate','cleanup length branch')
    if not bad_length:
        metadata=clear_model['per_store_metadata']; init=clear_model['per_initializer_component_edges']
        for i in range(16):
            with t.site(781+i,f'anonymous clear128[{i}]'):
                for op in metadata[:30]: t.op(f'{op["id"]}: {op["operation"]}')
                for op in init: t.op(f'{op["id"]}: {op["operation"]}')
                for op in metadata[30:41]: t.op(f'{op["id"]}: {op["operation"]}')
                t.copy('actual anonymous array128 -> Candidate destination128',128)
                for op in metadata[41:]: t.op(f'{op["id"]}: {op["operation"]}')
        src=[7729816,7729832,7729840,7729848,7729856,7729864,7729872,7730272,7730280,7730288,7731040,7731048]
        for i,s in enumerate(src):
            with t.site(797+i,f'literal envelope restore[{i}]'):
                t.direct('c',K(888+i*8),K(896+i*8),'b',K(s),K(s+8),8)
        if cleanup_fault or instrumented:
            with t.site(810,'private cfg(test) cleanup fault supplement'):
                atomic_fault(t,'CLEANUP_FAULT'); t.opset('atomic result -> private fault if predicate','private fault branch')
        if cleanup_fault:
            with t.site(811,'private cfg(test) cleanup corruption'):
                # Scalar byte assignment, not a second complete array payload.
                t.e(K('0x51'),'byte assignment received RHS value')
                t.e(K(0),'Candidate byte Index received index')
                t.opset('Candidate byte Index borrow','Candidate pointer -> IndexMut receiver','byte IndexMut entry',
                        'index -> bound left','Candidate length2048 -> bound right','index<length predicate','byte bound branch',
                        'Candidate pointer -> address operand','index -> address operand','byte address formation',
                        'byte address -> returned mutable reference source','projected exclusive byte loan',
                        'returned byte reference -> caller received byte reference','byte IndexMut return control',
                        'received RHS byte value -> destination byte scalar store','byte assignment unit result production','byte-store statement continuation')
    with t.site(779 if bad_length else 812 if cleanup_fault else 814,'cleanup bool return and caller guard'):
        t.opset(f'literal {not (bad_length or cleanup_fault)} -> cleanup bool output','cleanup output bool -> caller received bool',
                'cleanup return control','received bool -> ! operand','boolean !','! result -> caller if predicate','caller cleanup if branch')
    # Conditional absorbing latch installation belongsG7 (or G128 for guard cause).

def totals(t):
    actual=[x for x in t.ops if x['owner']=='G6']; scalar=[x for x in actual if x['kind']=='scalar']; copies=[x for x in actual if x['kind']=='copy']
    boundscalars=sum(x['kind']=='scalar' for x in t.ops); boundcopies=sum(x['kind']=='copy' for x in t.ops)
    return {'actual_G6_scalars':len(scalar),'actual_G6_payload_groups':len(copies),'actual_G6_scalar_blocks':math.ceil(len(scalar)/16),
            'actual_G6_groups':math.ceil(len(scalar)/16)+len(copies),
            'conservative_including_owned_G1_slack_scalars':boundscalars,'conservative_including_owned_G1_slack_copies':boundcopies,
            'conservative_group_bound':math.ceil(boundscalars/16)+boundcopies,
            'G6_ordered_ids_sha256':digest(('\n'.join(x['id'] for x in actual)+'\n').encode()),
            'G6_scalar_partition_rule':'Filter owner=G6 and kind=scalar in authored operation order; consecutive groups[k*16:(k+1)*16]. No G1 operation is in these blocks.',
            'last_scalar_block_length':len(scalar)%16 or 16 if scalar else 0,
            'all_G6_operation_ids_unique':len({x['id'] for x in actual})==len(actual)}

def make_traces(model):
    traces=[]
    specs=[(1,''),(2,'lookup-new'),(2,'lookup-hit'),(3,'reuse'),(3,'collision'),(4,'reuse'),(4,'collision'),(5,'feasible'),(5,'infeasible'),
           (6,''),(7,''),(8,''),(9,''),(10,''),(11,'hit'),(11,'built'),(12,''),(13,'')]
    for kind,variant in specs:
        name=f'event{kind}'+('.'+variant if variant else '')
        for mode in ['production','instrumented-success','instrumented-cleanup-failure']:
            t=Trace(name+'.'+mode); assert event(t,kind,variant)
            final_commit(t,kind,variant,instrumented=mode!='production')
            cleanup(t,model,cleanup_fault=mode=='instrumented-cleanup-failure',instrumented=mode!='production'); traces.append(t)
    for kind,variant,stop in [(5,'feasible','prefix-refusal'),(11,'built','sum-refusal'),(11,'built','pin-overflow'),
                              (11,'built','pin-refusal'),(11,'hit','pin-overflow'),(11,'hit','pin-refusal')]:
        for instrumented in (False,True):
            t=Trace(f'event{kind}.{variant}.{stop}'+('.instrumented' if instrumented else ''))
            assert not event(t,kind,variant,stop); cleanup(t,model,instrumented=instrumented); traces.append(t)
    for kind,variant in [(7,''),(11,'hit'),(11,'built'),(12,'')]:
        t=Trace(f'event{kind}.'+variant+'.private-commit-failure'); assert event(t,kind,variant)
        final_commit(t,kind,variant,True,True); cleanup(t,model,instrumented=True); traces.append(t)
    for name,bad in [('prestage-refusal',False),('zero-debit-guard-after-loan',False),('invalid-length-cleanup',True)]:
        t=Trace(name); cleanup(t,model,bad_length=bad); traces.append(t)
    return traces


def local_places():
    return {
      'schema':1,'source_sha256':SOURCE_SHA,
      'scope':'Source-semantic places and conservative lexical/statement/call scopes; not compiler stack, RSS, ABI or acceptance of29344 union.',
      'lifetime_rules':[
        'Each source/received endpoint is a distinct place when the model has an actual transfer; an edge is counted once. Whole byte payload source aliases existing Candidate/arena storage unless explicitly described as a produced array/Option.',
        'No named local is retired merely at last use. Use its source lexical block end; no optimizer, slot reuse, promotion, or elision assumption.',
        'Each statement temporary is conservatively live from its production until that expression statement ends, unless its callee return ends the callee-owned output earlier. Source and destination coexist during an actual transfer.',
        'Scalar literal/operand/result places are instantiated per expression/operation ID; width<=8 each, bool1, unit0. Both operands and produced result are distinct where a primitive uses them. They remain within that primitive call/expression statement and may overlap its active helper frames.',
        'Two-word Range and fat-view places use separate8-byte fields in operations but remain complete16-byte owners in this place inventory.',
        'A full Option16 has its complete source and received16 owners during transfer, not only active tag/payload bytes; its inactive bytes are covered by the fixed-copy debit. A pointer-niche Option<&array8> is the complete8-byte source/received pointer place.',
      ],
      'leaf_named_places':[
        {'names':['b','c','loan','p','steps'],'types':['&mut[u8]','&mut Candidate2048','&Loan','&Progress','&mut StepBudget'],'bytes':[16,8,8,8,8],'scope':'semantic received parameters through semantic return; not alive in callee after caller starts cleanup'},
        {'names':['w','f'],'types':['&[u64;16]','&Fixture'],'bytes':[8,8],'scope':'semantic block let bindings through semantic return; initialized/owned G1'},
        {'names':['resident_delta','pin_delta','plan_delta'],'type':'u64','bytes_each':8,'scope':'semantic350..773, all3 simultaneous; initializers G1, later assignments/reads G6'},
        {'names':['total','count','found','first_empty','first_pin','resident_pins','live_tokens','release_nonce_matches'],'type':'u64','bytes_each':8,'scope':'semantic block through return; born G1/G2, their new G6 argument reads remain separate'},
        {'names':['stage'],'type':'u64','bytes_each':8,'scope':'let710 through semantic return773; overlaps3 delta flags and all commit calls'},
        {'names':['at'],'type':'usize','bytes_each':8,'scope':'one distinct binding per resident734..744, pin745..748 or plan749..752 if block. These at locals are mutually sequential, not simultaneous across blocks.'},
      ],
      'event_arm_places':[
        {'arm':'3|4','places':{'cell':8,'prior':8,'outcome':8},'scope':'arm477..513; ownG1. On5-word plan stage, Range iterator16 and i8 are additional G6 locals. All end before common final stage710.'},
        {'arm':'5','places':{'cell':8,'headroom':8,'remaining':8,'mask':8,'destination':8,'feasible':1},'scope':'arm514..568. cellG1; prefix locals G5; final scalar argument reads G6. Merge callee completes before prefix; no merge helper frame overlaps final sq.'},
        {'arm':'6..=8','places':{'outstanding':8,'expected':8,'slot':8},'scope':'arm569..613; source admissionG1; arguments and staged calculationsG6. All dead by common final stage.'},
        {'arm':'11','places':{'slot626_u64':8,'slot630_usize_shadow':8,'prior_pins653':8,'pins654':8},'scope':'arm619..672. Both slot bindings conservatively coexist through arm end despite shadow. prior_pins and pins coexist with both slots and st/sq frames.'},
        {'arm':'11 built inner else','places':{'sum648':8},'scope':'else637..652; checked Option16 temporary source/received during648. sum ends before prior_pins653 exists, by actual lexical block.'},
        {'arm':'12','places':{'slot674':8,'pin675':8},'scope':'arm673..701; ownG1. Pin-reset iterator16 and per-iteration i8 add G6 locals; all arm locals end before common final stage.'},
      ],
      'helper_frames':[
        {'template':'st','received':{'b_fat':16,'at':8,'n':8},'caller_sources':{'b_fat':16,'at_value':8,'n_value':8},
         'extra':{'to_le_bytes_received_self':8,'to_le_bytes_return_array_source':8,'received_LE_array_temporary':8},
         'scope':'All st parameters live throughout call. LE array source8 exists in to_le_bytes call and overlaps received8 only at return transfer; received8 survives source borrow/copy until st inner statement ends. No returned array source survives callee return. Destination bytes alias existing Candidate/arena.'},
        {'template':'sq','received':{'c_thin':8,'i':8,'n':8},'caller_sources':{'c_thin':8,'i':8,'n':8},
         'scope':'sq caller source and received endpoints overlap argument transfer; received parameters remain while nested st frame is active. SC+8*i operator word operands/results belong to forwarding argument expression; nested st params are distinct.'},
        {'template':'ld','received':{'b_fat':16,'at':8},'caller_sources':{'b_fat':16,'at':8},
         'extra':{'first_chunk_receiver':16,'Option_ref_array_output_source':8,'Option_ref_array_caller_received':8,'expect_self_received':8,'expect_message_source_fat':16,'expect_message_received_fat':16,'expect_return_reference_source':8,'expect_return_reference_received':8,'from_le_bytes_received_array':8,'decoded_word_source':8,'ld_designated_output':8,'caller_word_received':8},
         'scope':'Whole ld return expression. first_chunk/expect return owners end at their callee exits; received chain values conservatively survive expression end. Array source is the proved borrowed8 bytes of existing storage, not a new zero initializer; from_le_bytes receives the full by-value array8. Message static text bytes remain static; only pointer/length source and received views are transient.'},
        {'template':'cq','received':{'c_thin':8,'i':8},'caller_sources':{'c_thin':8,'i':8},'scope':'cq frame remains during nested ld; scalar offset expression and scalar returned/received word each instantiated separately.'},
        {'template':'rr/pr/pl','received':{'b_fat':16,'row':8,'field':8},'caller_sources':{'b_fat':16,'row':8,'field':8},'scope':'These frames retain G1 ownership in the conservative admission supertrace. G6 new pins uses ld directly. Their offset operands and output words remain source/received owners; no G1 work is charged to G6.'},
      ],
      'index_copy_place_templates':[
        {'template':'one scalar array Index','places':{'source_index_usize':8,'received_index_usize':8,'receiver_borrow_source_thin':8,'receiver_received_thin':8,'returned_reference_source':8,'caller_received_reference':8,'loaded_word_source':8,'actual_argument_or_binding_received':8},'scope':'one indexed scalar expression including its returned reference/dereference; references end at expression statement. If p.q is projected, field address operand is an additional word; q payload is never copied as128 here.'},
        {'template':'one slice Range Index','places':{'Range_source':16,'Range_received':16,'receiver_borrow_source':16,'receiver_received':16,'returned_view_source':16,'caller_received_view':16},'scope':'one Index call/return within expression; Candidate-array receiver uses8+8 in place of16+16. Both Range fields and each view pointer/length are independently counted.'},
        {'template':'copy_from_slice','places':{'copy_receiver_source_view':16,'copy_received_receiver':16,'source_shared_reference':8,'source_view_source':16,'copy_received_source_view':16},'scope':'source argument evaluation through copy return; the two complete payload endpoints alias existing arrays except produced LE/anonymous arrays explicitly listed. Returned unit and discarded unit occupy0 bytes and have charged control operations.'},
        {'template':'scalar primitive','places':{'left_operand_up_to':8,'right_operand_up_to':8,'result_source_up_to':8,'result_received_up_to':8,'predicate_bool':1},'scope':'each generated operator occurrence/operation ID inside its source expression; unary/cast uses one operand. These are conservative typed source slots, not simultaneously summed with every earlier completed primitive in a statement.'},
        {'template':'Region constant base projection','places':{'materialized_constant_Region_source_value':24,'projected_base_word':8},'scope':'Conservatively materialize all3 constant fields in one24B source value for the field projection expression;3 component edges are charged. It ends at that expression statement, and only the base word is passed onward. No Region24 by-value argument is inferred. f fields refer to received immutable Fixture72 and are scalar reads, never full Fixture movement.'},
      ],
      'loop_places':[
        {'names':['Range source','IntoIterator received Range','returned iterator source','caller received iterator','mutable iterator binding'],'bytes_each':16,'scope':'setup transfer chain; source and received coexist at each step, each preceding callee owner ends at its return. Mutable iterator binding persists to final None/for exit.'},
        {'names':['next receiver borrow source','next receiver received'],'bytes_each':8,'scope':'each actual next call, with persistent iterator binding16'},
        {'names':['next Option source','caller received Option'],'bytes_each':16,'scope':'each actual next return including final None, during complete16B transfer; received Option ends after current pattern/body iteration; next source ends at call return'},
        {'names':['i'],'bytes_each':8,'scope':'Some pattern binding for one body iteration only; successive i bindings and helper frames do not overlap. iterator16 remains while st frame runs.'},
      ],
      'cleanup_phase':{
        'caller_still_live':{'Paid':24,'Loan':16,'semantic_steps':16,'received_SemanticReply':24,'record_words_w':128,'record_handle':8,'Candidate':2048,'arena_Vec_handle':24},
        'caller_scope':'cache_walk admitted-loan else block1171..1230. Received reply/Loan/StepBudget remain lexically live through cleanup; they are existing control roles, not reassigned to wire. Candidate and arena payload are existing owners.',
        'cleanup_source_handles':{'b_shared_fat':16,'c_exclusive_thin':8},'cleanup_received_handles':{'b_shared_fat':16,'c_exclusive_thin':8},
        'Vec_coercion_places':{'Vec_reference_source':8,'Deref_received_Vec_reference':8,'returned_slice_source':16,'caller_received_slice':16},
        'anonymous_clear':{'array_instances_per_statement':1,'array_bytes':128,'repeat_operand_bytes':1,'repeat_length_operand_bytes':8,'statement_instances':16,'simultaneous_arrays':1,
            'scope':'Each sole anonymous array begins during its own repeat initialization and ends at that clear expression statement. No named array receiver, by-value array helper parameter or second initializer-array source exists. It cannot overlap the next anonymous array or any restore statement.'},
        'clear_metadata':'Use selected independent review complete place template: Range source/received32, Candidate Index receiver source/received16, destination view source/received/copy receiver48, shared array reference/source/received fat views40, predicate operand pair/bool17. Caller/received cleanup handles and repeat inputs are additional, explicit; no helper192/whole29344 union acceptance.',
        'restore':'No anonymous clear array survives. Twelve sequential direct-copy statement templates with source arena bytes8 and destination Candidate bytes8 aliases; all Range/view owners remain full16B types.',
        'return_bool_places':{'cleanup_output_source':1,'caller_received':1,'not_operand':1,'not_result_source':1,'caller_if_predicate':1},
        'return_scope':'after restores/private fault, or early invalid-length return before any clear. No clear temporary survives this phase. The conditional terminal latch belongsG7 for ordinary/fault cleanup cause orG128 for zero-debit guard cause.'},
      'private_fault_places':{'atomic_receiver_borrow_source':8,'atomic_received_receiver':8,'swap_value_bool':1,'ordering_value_up_to':8,'returned_bool_source':1,'returned_bool_received':1,'not_operand':1,'not_result_source':1,
          'scope':'cfg(test) standard atomic call and returned bool branch; globals COMMIT_FAULT/CLEANUP_FAULT are static existing storage, not new local arrays. Cleanup corruption additionally has byte IndexMut source/received thin references and destination byte aliases existing Candidate.'},
      'phase_order':['event arm staging (sq/st/ld nested frames)','arm exit ends all arm locals','final stage8 and delta flags24 plus sequential commit call frames','semantic callee returns; all its local/helper frames end','caller ordinary/guard reply audit in G7/G128','cleanup call, guard','sixteen statement-scoped anonymous128 arrays in sequence','twelve restores in sequence','optional private fault','bool return/caller ! branch then G7/G128 latch effect'],
      'complete_G6_local_category_inventory':True,'full_29344_union_accepted':False,'role_fit_for_helper192_control_wire_accepted':False,
    }


def main():
    for p,h in EXPECTED.items(): assert digest(p.read_bytes())==h,str(p)
    verified=[]
    for p in [REVIEW/'seal.json',SOURCE.parent/'seal.json',ROOT/'verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json']:
        manifest=json.loads(p.read_text())
        for m in manifest['members']: assert info(ROOT/m['path'])==m,m['path']
        verified.append({'seal':info(p),'member_count':len(manifest['members']),'member_bytes':sum(m['bytes'] for m in manifest['members'])})
    source=SOURCE.read_text(); model=json.loads((REVIEW/'clear-block-ledger.json').read_text())
    assert model['anonymous']['scalars']==2768 and model['anonymous']['complete_clear_block_groups']==189
    assert all(f'c[{i*128}..{(i+1)*128}].copy_from_slice(&[0u8; 128]);' in source for i in range(16))
    traces=make_traces(model)
    rows=[]
    for t in traces:
        summary=totals(t)
        assert summary['all_G6_operation_ids_unique']
        scalars=[x for x in t.ops if x['owner']=='G6' and x['kind']=='scalar']
        blocks=[scalars[i:i+16] for i in range(0,len(scalars),16)]
        assert all(0<len(b)<=16 for b in blocks)
        assert [x for b in blocks for x in b]==scalars
        rows.append({'path':t.name,**summary,'segments':t.segments})
    maximum=max(rows,key=lambda x:x['actual_G6_groups']); conservative=max(rows,key=lambda x:x['conservative_group_bound'])
    at=datetime.now(timezone.utc).isoformat()
    custody={'schema':1,'at':at,'command':[sys.executable,'-B',str(Path(__file__).resolve())],
             'python':sys.version,'platform':platform.platform(),'HEAD_context_only':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'source':info(SOURCE),'selection':info(SELECTION),'input_seals_verified':verified,
             'runtime_compiler_product_executions':0,'owned_scope':['verification/swift-cache-state-g6-complete/**']}
    write('custody.json',custody)
    segment_bytes=(json.dumps({'schema':1,'source_sha256':SOURCE_SHA,'paths':rows},separators=(',',':'))+'\n').encode()
    (HERE/'path-segments.json.gz').write_bytes(gzip.compress(segment_bytes,mtime=0))
    write('paths.json',{'schema':1,'source_sha256':SOURCE_SHA,'paths':[{k:v for k,v in row.items() if k!='segments'} for row in rows],'maximum_actual_G6':{k:v for k,v in maximum.items() if k!='segments'},
        'maximum_with_G1_bounding_slack':{k:v for k,v in conservative.items() if k!='segments'},
        'cap':640,'complete_source_model_bound_claimed':maximum['actual_G6_groups']<=640,
        'not_implementation_acceptance':True})
    # Full operation table for the extremal actual-G6 path; other paths are
    # reproducibly expanded by this sealed static source grammar and hashed rows.
    extremal=next(t for t in traces if t.name==maximum['path'])
    operation_bytes=(json.dumps({'schema':1,'source_sha256':SOURCE_SHA,'path':extremal.name,'operations':extremal.ops},separators=(',',':'))+'\n').encode()
    (HERE/'extremal-operations.json.gz').write_bytes(gzip.compress(operation_bytes,mtime=0))
    legacy=HERE/'extremal-operations.json'
    if legacy.exists(): legacy.unlink() # This lane's own pre-seal generated draft only.
    write('local-places.json',local_places())
    template_specs=[('st Candidate/value',lambda x:x.st(K(1536),V('word'))),('sq literal/value',lambda x:x.sq(K(6),V('word'))),
        ('ld Candidate/literal',lambda x:x.ld('c',K(1560),'binding')),('cq literal',lambda x:x.cq(K(16),'binding')),
        ('rr literal field',lambda x:x.rowload('rr',V('slot'),K(0),'binding')),
        ('literal Candidate->arena8',lambda x:x.direct('b',K(7729928),K(7729936),'c',K(1736),K(1744),8)),
        ('literal arena->Candidate8',lambda x:x.direct('c',K(888),K(896),'b',K(7729816),K(7729824),8)),
        ('copy_within64',lambda x:x.within()),('indexed record word',lambda x:x.e(w(6),'argument'))]
    template_rows=[]
    for name,fn in template_specs:
        tr=Trace('template.'+name); fn(tr)
        template_rows.append({'name':name,'scalars':sum(o['kind']=='scalar' for o in tr.ops),
            'copies':sum(o['kind']=='copy' for o in tr.ops),'operations':tr.ops})
    write('operation-templates.json',{'schema':1,'source_sha256':SOURCE_SHA,'templates':template_rows,
        'literal_clear128':{'scalars':173,'copies':1,'template_source':info(REVIEW/'clear-block-ledger.json')},
        'numeric_template_counts_not_site_rounding':True})
    write('source-model.json',{'schema':1,'source_sha256':SOURCE_SHA,'selected_clear_model':info(REVIEW/'clear-block-ledger.json'),
        'grammar':'ledger.py Trace methods supply named component expansions. Each expression/operator/handle/range/view/loop/Option/function boundary is expanded; complete payload copies independent of scalar units.',
        'transfer_rule':'Source and received endpoints are one transfer edge. Range/view field construction followed by actual by-value receive are different edges, never the same edge twice.',
        'array_repeat_rule':'Anonymous clear constructors charge130 scalar initialization fields per statement and no fictitious initializer-array copy;16 real128B payload stores.',
        'standard_builtin_scope':'Authored semantic primitive expansion; no compiler ABI, machine, libstd implementation, or allocator/callback lowering claim.',
        'helper_definition_lines':{'ld':[149,155],'st':[156,158],'cq':[159,161],'sq':[162,164],'rr':[165,167],'pr':[168,170],'pl':[171,173]},
        'function_items':'Static function/method items are zero-sized callee names; each actual call entry and return control is charged. No fictitious indirect function pointer or callback is inferred.',
        'constant_Region_rule':'All3 Region fields are conservatively materialized by scalar edges into a complete24B source value at each constant-base projection; base extraction still separately charged. No promotion or constant-folded initialization omission.',
        'excluded_bodies_with_real_owners':{'initial/admission/prior/probes':'G1/G2','merge body':'G3/G4','headroom/prefix/feasibility542..561':'G5',
            'paid complete SemanticReply and caller audit/latch':'G7','zero-debit complete guard reply/received/caller terminal':'G128',
            'post-loan actual cleanup even after guard':'G6'},
        'G1_bounding_slack':'All retained G1 event identity/admission and initial delta flag operations keep ownerG1. They appear only in a separately labeled looser arithmetic comparison and never in actual G6 scalar partitions.',
        'loop_model':'Only actual event4 five-word staging/event12 six-word reset loops appear in G6; all entries, next calls, complete Option16 returns, iteration guards/advances and final None included.',
        'complete_Option_rule':'Option<u64>/Option<usize> by-value source->received movement is one full16B copy debit; active tag/payload construction and actual pattern work separately scalar. No incomplete inactive arm is called a full scalar.',
        'private_fault_model':'Atomic swap treated as one standard atomic primitive plus explicit receiver/value/ordering/call/return/control; test-only supplemental paths shown, zero runtime execution.',
        'failure_coverage':'Prestage refusals share cleanup; partial staging refusal points enumerated. Later ordinary refusals are prefixes of those event stage traces. Private commit failure stops after first resident copy. Invalid cleanup length skips all writes. Postrestore injected failure adds its byte scalar store and false return.',
        'full_Result':'No Result is born/moved in G6; all actual G6 Options, arrays and scalar/boolean returns are explicitly present. Outer Result40 and final aggregate Results retain wrapper/finish ownership.',
        'numeric_caps_unchanged':[256,2560,2568,768,640,640,248],
        'full_29344_lifetime_union_accepted':False,'product_runtime_acceptance':False})
    write('range-safety.json',{'schema':1,'source_sha256':SOURCE_SHA,
        'admitted_slice':'same exclusive non-resizable arena slice from pre-loan exact8,388,608-byte check through semantic and cleanup; Candidate type exactly2048. No callback or resize capability in any G6 helper.',
        'constant_Candidate_sites':'all source-sites are fixed st addresses1536..1680; sq indices0..18 place1688+8*i..+8 ending1840; reserved copy1944..2008 to1536..1600; ld prior pin1560..1568; cq constants16/17/18 end1840; all<=2048.',
        'literal_copies':'12 scalar commits753..764 and12 restores797..808 exact source statements; endpoints are inside frozen exact arena and Candidate. Independent C2 endpoint equivalence remains input evidence, not a work oracle.',
        'row_source_ranges':'G1 config slots/pins1..64; slot/pin admission proves indexes before G6 source-row copies; plan cell=(w6&511) usize<512. Resident64,Pin48,Plan40 regions frozen in analyzer. Row offset operations and repeated base projections remain charged.',
        'arithmetic_guards':'G1 prior validation proves nonchecked staging count +/-1, pin +/-1, mask shifts and nonce+1 within u64/usize. total.checked_add and prior_pins.checked_add may refuse and are explicitly represented by complete Option16. No overflow omission due to release mode.',
        'clear':'16 literal0<=start<end<=2048 ranges, exactly128B; sole anonymous source each128B, all checks charged. first_chunk/expect in G6 ld receives an exact8-byte proved range; None/panic unavailable after these source preconditions.',
        'failure_controls':'Pre-loan refusal performs no scratch access; actual cleanup still accounted after admitted-loan guard returns. Invalid cleanup length returns false before writes. Private commit/cleanup fault supplements preserve paid poison behavior; complete reply/latch belongsG7 or zero-debitG128.',
        'not_source_only_OTA_authority':True,'physical_or_runtime_validation_run':False})
    result={'schema':1,'at':at,'static_checker':'source hash/seals/selected-clear identity/operation uniqueness/ordered <=16 partitions/path arithmetic',
            'path_count':len(rows),'maximum_G6_path':maximum['path'],'maximum_G6_groups':maximum['actual_G6_groups'],
            'maximum_conservative_with_G1_slack':conservative['conservative_group_bound'],'within640':maximum['actual_G6_groups']<=640,
            'runtime_compiler_product_executions':0,'implementation_acceptance':False,'whole_lifetime_acceptance':False}
    write('static-validation.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
