#!/usr/bin/env python3
"""Finite authored-source accounting model. No Rust, old collector, or harness execution."""
from __future__ import annotations
import contextlib
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs'
SOURCE_SHA = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
CAPS = {'G1':256, 'G7':248, 'SS':512, 'SF':256, 'G128':128, 'F42':42}

def sha(data): return hashlib.sha256(data).hexdigest()
def save(name, data): (HERE/name).write_text(json.dumps(data,indent=2)+'\n')
def V(n): return ('value',str(n))
def K(n): return ('literal',str(n))
def F(n): return ('field',n)
def I(n,i): return ('index',n,K(i) if isinstance(i,int) else i)
def B(op,a,b): return ('binary',op,a,b)
def U(op,a): return ('unary',op,a)
def C(a,ty='usize'): return ('cast',ty,a)
def L(kind,*args): return ('load',kind,*args)
def Q(i): return I('p.q',i)
def W(i): return I('w',i)

class Trace:
    def __init__(self,name,owner): self.name=name; self.owner=owner; self.ops=[]; self.line=0; self.site='entry'; self.sites=[]
    def op(self,s,kind='scalar',width=0):
        self.ops.append({'id':f'{self.name}.{len(self.ops):05d}','owner':self.owner,'line':self.line,'site':self.site,'operation':s,'kind':kind,'bytes':width})
    def many(self,*items):
        for x in items: self.op(x)
    def copy(self,name,width):
        for at in range(0,width,128): self.op(f'{name} bytes[{at}:{min(at+128,width)}]','copy',min(128,width-at))
    @contextlib.contextmanager
    def at(self,line,name):
        old=(self.line,self.site); self.line=line; self.site=name; start=len(self.ops)
        yield
        self.sites.append({'line':line,'site':name,'first':start,'count':len(self.ops)-start})
        self.line,self.site=old
    def e(self,x,target):
        tag=x[0]
        if tag in ('value','literal'): self.op(f'{tag} {x[1]} source -> {target}')
        elif tag=='field':
            if '.base' in x[1] and x[1].split('.')[0] in ('FUNCTION','SCALAR','RESIDENT','PIN','PLAN','rr.Region','pr.Region','pl.Region'):
                self.many('Region.base constant -> source field','Region.rows constant -> source field','Region.stride constant -> source field')
            self.many(f'{x[1]} owner pointer -> field operand',f'{x[1]} field address formation',f'{x[1]} source -> {target}')
        elif tag=='index':
            _,base,index=x
            if '.' in base: self.many(f'{base} owner pointer -> field operand',f'{base} array field address formation')
            self.e(index,f'{base} Index received index')
            self.many(f'{base} scalar Index receiver borrow',f'{base} pointer -> received receiver','Index entry control','received index -> bound left','length -> bound right','index<length','index check branch','base pointer -> address operand','received index -> scaling operand','width8 -> scaling operand','index*8','scaled offset -> address operand','base pointer -> address operand','element address formation','element address -> returned reference','indexed reference loan creation','returned reference -> received reference','Index return control','received reference -> dereference source',f'indexed scalar source -> {target}')
        elif tag in ('binary','unary','cast'):
            self.e(x[2],f'{x[1]} received operand1')
            if tag=='binary': self.e(x[3],f'{x[1]} received operand2')
            self.many(f'primitive {x[1]}',f'{x[1]} result source -> {target}')
        elif tag=='load':
            if x[1]=='cq':
                self.thin('c','cq.received_c'); self.e(x[2],'cq.received_i'); self.op('cq entry control')
                self.ld('c',B('+',K(1688),B('*',K(8),V('cq.i'))),'cq designated output',array=True)
                self.many(f'cq designated output -> {target}','cq return control')
            elif x[1]=='ld': self.ld(x[2],x[3],target,array=x[2]=='c')
            else:
                kind=x[1]; stride={'rr':64,'pr':48,'pl':40}[kind]
                self.handle('b',f'{kind}.received_b'); self.e(x[2],f'{kind}.received_row'); self.e(x[3],f'{kind}.received_field'); self.op(f'{kind} entry control')
                self.ld('b',B('+',B('+',F({'rr':'RESIDENT','pr':'PIN','pl':'PLAN'}[kind]+'.base'),B('*',K(stride),V(kind+'.row'))),B('*',K(8),V(kind+'.field'))),kind+' designated output')
                self.many(f'{kind} output source -> {target}',f'{kind} return control')
        else: raise ValueError(tag)
    def check(self,*xs,logic='or'):
        for i,x in enumerate(xs):
            self.e(x,f'{logic} child{i} source')
            if i<len(xs)-1:self.op(f'{logic} short circuit branch{i}')
        self.many(f'{logic} result -> if predicate','if control branch')
    def terminal(self):
        self.thin('p','terminal.received_self'); self.op('terminal entry control'); self.e(B('&',F('p.latch'),K(255)),'terminal designated output'); self.many('terminal output -> caller received u64','terminal return control')
        return V('received terminal')
    def thin(self,base,target):
        if '.' in base:self.many(f'{base} parent pointer -> field operand',f'{base} field address formation')
        self.many(f'{base} reference reborrow',f'{base} pointer source -> {target}')
    def handle(self,base,target,array=False):
        if base=='arena.bytes':
            self.many('arena pointer -> Vec field projection','Vec field address formation','Vec receiver shared/exclusive borrow','Vec pointer -> slice conversion received self','Vec slice conversion entry','Vec buffer pointer -> returned slice.data','Vec length -> returned slice.len','slice conversion return control','returned slice components -> local view')
        if array:self.many(f'{base} array address formation',f'{base} array reborrow',f'{base} array pointer -> view.data source',f'{base} length2048 -> view.len source',f'view.data -> {target}.data',f'view.len -> {target}.len')
        else:self.many(f'{base} slice reborrow',f'{base}.data -> argument.data source',f'{base}.len -> argument.len source',f'argument.data -> {target}.data',f'argument.len -> {target}.len')
    def view(self,base,start,end,exclusive=False):
        self.e(start,'Range.start source'); self.e(end,'Range.end source')
        self.many('Range.start -> Index received start','Range.end -> Index received end','Index receiver borrow','slice.data -> Index received data','slice.len -> Index received len','Index entry control','received start -> ordered left','received end -> ordered right','start<=end','ordered branch','received end -> upper left','received len -> upper right','end<=len','upper branch','received data -> address left','received start -> address right','view address formation','received end -> subtraction left','received start -> subtraction right','view length end-start','address result -> returned view.data','length result -> returned view.len',f'{"exclusive" if exclusive else "shared"} view loan creation','returned view.data -> caller received data','returned view.len -> caller received len','Index return control')
    def ld(self,base,offset,target,array=False):
        self.handle(base,'ld.received_b',array); self.e(offset,'ld.received_at'); self.op('ld entry control')
        self.view('ld.b',V('ld.at'),B('+',V('ld.at'),K(8)))
        self.many('first_chunk receiver reborrow','view.data -> first_chunk received data','view.len -> first_chunk received len','first_chunk entry control','width8 -> length predicate','received len -> length predicate','len>=8','first_chunk branch','returned array8 reference loan','Some pointer source construction','complete Option reference8 source -> received Option8','first_chunk return control','received Option8 -> expect received self','expect message address -> source.data','expect message length -> source.len','message.data -> received message.data','message.len -> received message.len','expect entry control','Option pointer -> tag operand','Some predicate','expect branch','unwrapped pointer -> returned reference','returned reference -> received reference','expect return control','received reference -> dereference address','array8 source address formation')
        self.copy('dereferenced array8 -> from_le_bytes received argument8',8)
        self.many('from_le_bytes entry control','u64 from_le_bytes','decoded word -> ld designated output','from_le_bytes return control',f'ld output -> {target}','ld return control')
    def st(self,at,n):
        self.handle('arena.bytes','st.received_b'); self.e(at,'st.received_at'); self.e(n,'st.received_n'); self.op('st entry control')
        self.view('st.b',V('st.at'),B('+',V('st.at'),K(8)),True)
        self.many('copy receiver reborrow','view.data -> copy received destination.data','view.len -> copy received destination.len','n -> to_le_bytes received self','to_le_bytes entry control','u64 to_le_bytes')
        self.copy('LE array8 designated -> received temporary8',8)
        self.many('to_le_bytes return control','LE array address formation','LE array shared borrow','LE array pointer -> source.data','LE array length8 -> source.len','source.data -> copy received source.data','source.len -> copy received source.len','copy entry control','destination.len -> equality left','source.len -> equality right','length equality','copy check branch')
        self.copy('source payload8 -> destination8',8)
        self.many('copy unit/control -> caller','copy unit discard','st unit source construction','st unit/control -> caller','st unit discard and continuation')
    def write_index(self,base,index,value):
        self.e(value,base+' assignment received rhs')
        if '.' in base:self.many(base+' owner pointer -> field operand',base+' array field address formation')
        self.e(K(index) if isinstance(index,int) else index,base+' IndexMut received index')
        self.many(base+' exclusive receiver borrow','pointer -> IndexMut received receiver','IndexMut entry control','received index -> bound left','array length -> bound right','index<length','bound branch','pointer -> address left','index -> scaling left','width8 -> scaling right','index*8','scaled offset -> address right','pointer -> address left','element address formation','exclusive element reference loan','returned reference -> received reference','IndexMut return control','received rhs -> indexed destination')
    def loop(self,n,label,body):
        self.many(label+' literal0 -> Range.start',label+f' literal{n} -> Range.end','Range.start -> IntoIterator received start','Range.end -> IntoIterator received end','IntoIterator entry control','received start -> returned iterator.start','received end -> returned iterator.end','returned iterator.start -> received iterator.start','returned iterator.end -> received iterator.end','IntoIterator return control','received iterator.start -> local iterator.start','received iterator.end -> local iterator.end')
        for i in range(n+1):
            self.many(label+f'[{i}] iterator exclusive borrow','iterator pointer -> next received self','next entry control','iterator.current -> guard left','iterator.end -> guard right','current<end','next guard branch')
            if i<n:self.many('current -> Some payload source','Some tag source','current -> increment left','one -> increment right','iterator increment','result -> iterator.current')
            else:self.op('None tag source')
            self.copy(f'{label}[{i}] complete Option<usize>16 -> caller received16',16)
            self.many('next return control','received Option.tag -> pattern operand','Some pattern predicate','pattern branch')
            if i<n:
                self.op('Some payload -> loop index local'); body(i); self.many('body unit source construction','loop back control')
        self.many('loop result unit source construction','for statement continuation')
    def range_contains(self,a,b,value):
        self.e(K(a),'RangeInclusive.start source'); self.e(K(b),'RangeInclusive.end source'); self.op('RangeInclusive exhausted false source')
        self.many('range receiver borrow','range pointer -> contains received self'); self.e(value,'contains needle source'); self.many('needle shared borrow','needle pointer -> contains received needle','contains entry control','start -> lower left','needle -> lower right','start<=needle','lower short circuit branch','needle -> upper left','end -> upper right','needle<=end','contains result source -> caller received bool','contains return control')
        return V('received contains bool')
    def reply(self,form,debit):
        # complete helper and leaf return boundaries, including non-Copy value24
        if form!='inline':self.e(K(13 if form=='reject' else debit),form+' received argument'); self.op(form+' entry control')
        for field in ('status','reason','debit'):self.e(V(form+'.'+field),f'SemanticReply constructor.{field}')
        if form!='inline':
            self.copy('SemanticReply24 helper source -> helper designated24',24); self.op('helper return control'); self.copy('helper designated24 -> semantic received helper Reply24',24)
        self.copy('SemanticReply24 source -> semantic designated24',24); self.op('semantic return control'); self.copy('semantic designated24 -> cache_walk received24',24)
    def latch(self):
        self.thin('p','latch_terminal received self'); self.e(V('terminal reason'),'latch_terminal received n'); self.op('latch_terminal entry control')
        self.e(B('|',B('&',F('p.latch'),U('!',K(255))),V('n')),'p.latch assignment rhs')
        self.many('p owner -> latch destination projection','latch field address formation','rhs -> latch field store','latch unit source','latch unit/control -> caller','unit discard')
    def budget_body(self,kind):
        """Conservative full authored Budget helper body, all early error arms.

        Original helper bodies are inherited source, but each NEW invocation is
        real work. Include its operations here rather than treating reuse free.
        Success and failure constructors are unioned; no guessed libstd body.
        """
        field='report_spent' if kind=='report' else 'setup_spent'
        self.e(F('budget.'+field),'checked_add received self');self.e(V('n'),'checked_add received n')
        self.many('budget checked_add entry','checked addition','overflow predicate','overflow branch','Some tag source','sum -> Some payload')
        self.copy('budget complete Option<u64>16 source -> is_none_or received16',16)
        self.many('checked_add return','is_none_or entry','Option discriminant predicate','Some branch','Some payload -> closure v','closure entry')
        self.e(B('>',V('v'),K('REPORT_RESERVE' if kind=='report' else 'SETUP_CAP')),'closure bool source')
        self.many('closure return control','is_none_or returned bool -> guard predicate','is_none_or return','budget if branch')
        self.error_union(kind+'.cap-error')
        if kind=='setup':
            self.thin('budget','replay received self');self.e(V('n'),'replay received n');self.op('replay entry')
            self.e(F('budget.replay_left'),'checked_sub received self');self.e(V('n'),'checked_sub received n');self.many('checked_sub entry','checked subtraction','overflow predicate','overflow branch','Some tag source','difference -> Some payload source');self.copy('replay complete Option<u64>16 source -> ok_or received16',16);self.op('checked_sub return')
            # ok_or eagerly constructs its Error32 argument on success too.
            for i in range(4):self.e(K('replay error field'+str(i)),'error helper received argument'+str(i))
            self.op('error entry')
            for i in range(4):self.e(V('error arg'+str(i)),'Error32 constructor field'+str(i))
            self.copy('Error32 source -> error designated32',32);self.op('error return');self.copy('error designated32 -> ok_or received Error32',32)
            self.many('ok_or entry','Option tag predicate','Some branch','Some scalar -> Ok payload source','Ok Result tag source');self.copy('complete Result<u64,Error>40 source -> Try received40',40);self.many('ok_or return','Try tag predicate','Try branch','Ok payload source -> replay_left assignment rhs','budget owner -> replay_left destination','replay_left field address','rhs -> replay_left destination')
            self.e(B('+',F('budget.replay_spent'),V('n')),'replay_spent assignment rhs');self.many('budget owner -> replay_spent destination','replay_spent address','rhs -> replay_spent destination','Ok unit Result tag source','Ok unit source');self.copy('replay complete Result40 source -> caller received40',40);self.many('replay return','setup Try discriminant','setup Try branch','unit extraction')
            self.error_union('setup.replay-error')
        self.e(B('+',F('budget.'+field),V('n')),field+' assignment rhs');self.many('budget owner -> '+field+' destination',field+' address','rhs -> '+field+' destination','Ok unit Result tag source','Ok unit source');self.copy('budget complete Result40 source -> helper designated40',40)
    def error_union(self,label):
        for i in range(4):self.e(K(label+'.field'+str(i)),'error helper received arg'+str(i))
        self.op('error entry')
        for i in range(4):self.e(V('error arg'+str(i)),'Error32 constructor field'+str(i))
        self.copy(label+' Error32 constructor -> error designated32',32);self.op('error return');self.copy(label+' Error32 designated -> Err constructor payload32',32);self.op('Err Result tag construction');self.copy(label+' full unit Result40 source -> helper designated40',40);self.op('error-arm helper return control')
    def summary(self):
        scalars=sum(x['kind']=='scalar' for x in self.ops); copies=sum(x['kind']=='copy' for x in self.ops)
        return {'id':self.name,'owner':self.owner,'scalars':scalars,'scalar_blocks':(scalars+15)//16,'copies':copies,'groups':(scalars+15)//16+copies,'operation_count':len(self.ops),'operations_sha256':sha(json.dumps(self.ops,separators=(',',':')).encode()),'sites':self.sites}

def g1(event,variant=''):
    t=Trace(f'G1.event{event}.{variant or "ordinary"}','G1')
    with t.at(1158,'new caller admission and actual private loan creation'):
        t.check(B('!=',t.terminal(),K(16)))
        t.check(B('==',t.terminal(),K(0)),B('==',I('e.reply.words',0),K(1)),B('==',I('e.reply.words',1),K(0)),logic='and')
        t.many('arena Vec pointer -> slice source.data','arena Vec length -> slice source.len','slice shared len receiver borrow','slice.data -> len received data','slice.len -> len received len','len entry','len source -> designated usize','len return','designated usize -> caller received length')
        t.check(B('!=',V('received arena length'),K('ARENA_BYTES')))
        t.thin('record','Loan constructor.record');t.e(V('f pointer'),'Loan constructor.config');t.copy('Loan16 constructor -> loan local16',16)
        t.e(K(7680),'StepBudget constructor.remaining');t.e(K(0),'StepBudget constructor.spent');t.copy('StepBudget16 constructor -> semantic_steps local16',16)
    with t.at(314,'paid entry readability and budget checks'):
        t.many('b shared reborrow','slice receiver.data -> len received data','slice receiver.len -> len received len','len entry','received len -> returned length','len return control')
        t.check(B('!=',V('received length'),K('ARENA_BYTES')),B('!=',F('steps.spent'),K(0)))
        t.check(B('<',F('steps.remaining'),K(7680))); t.e(B('-',F('steps.remaining'),K(7680)),'steps.remaining destination');t.e(K(7680),'steps.spent destination')
        t.many('steps owner -> remaining destination projection','remaining field address','remaining result -> destination field','steps owner -> spent destination projection','spent field address','spent result -> destination field')
        t.e(F('loan.record.words'),'w local pointer'); t.e(F('loan.config'),'f local pointer')
        t.many('loan.record intermediate owner projection','loan.record field address','record pointer -> nested words owner')
    with t.at(328,'private config prior controls'):
        terminal=t.terminal()
        t.check(B('==',F('f.slots'),K(0)),B('>',F('f.slots'),K(64)),B('==',F('f.pins'),K(0)),B('>',F('f.pins'),K(64)),B('!=',terminal,K(0)),B('>',B('>>',F('p.latch'),K(8)),F('f.pins')),B('>',Q(3),K(10)))
        t.check(B('==',W(1),K(14)))
    with t.at(350,'initial delta flags'):
        for x in ('resident_delta','pin_delta','plan_delta'):t.e(K('ABSENT'),x+' local')
    with t.at(441,'defined fixture body closed-event identity'):
        t.e(C(W(6)),'body local'); t.e(W(1),'matches input'); t.many('closed 1|13 pattern match','matches bool source','logical negation','if short circuit branch')
        if event not in (1,13):
            t.check(B('>=',V('body'),K(80000)))
            # same full first_chunk4/unwrap/from_le_bytes structure as ld; explicit width4 copy.
            start=B('+',B('+',F('FUNCTION.base'),B('*',V('body'),K(96))),K(20));end=B('+',B('+',F('FUNCTION.base'),B('*',V('body'),K(96))),K(24))
            t.view('b',start,end)
            t.many('first_chunk4 receiver reborrow','view.data -> received.data','view.len -> received.len','first_chunk4 entry','width4 -> predicate','len -> predicate','len>=4','success branch','array4 reference loan','Some pointer source','complete Option reference8 -> received8','first_chunk4 return','received Option8 -> unwrap self','unwrap entry','Option tag operand','Some predicate','unwrap branch','payload pointer -> returned reference','returned reference -> received reference','unwrap return','array source address formation')
            t.copy('array4 source -> from_le_bytes received array4',4);t.many('from_le_bytes4 entry','u32 conversion','decoded u32 -> compare operand','from_le_bytes return','literal1 -> compare right','identity!=1','identity branch')
    with t.at(452,'closed event dispatch'):
        t.e(W(1),'event match input');t.op('closed event dispatch')
    row=lambda k,s,i:L(k,s,K(i))
    def ck(line,*xs):
        with t.at(line,'event admission predicates'):t.check(*xs)
    if event==2:
        ck(465,B('==',Q(9),K('ABSENT')));ck(468,B('==',V('first_pin'),K('ABSENT')))
        with t.at(471,'lookup alternative selected source path'):
            t.check(B('==',W(13),K(0)),B('!=',V('found'),K('ABSENT')),logic='and')
            t.check(B('==',W(13),K(1)),B('!=',V('found'),W(10)),logic='and')
            t.op('outer alternative branch')
    elif event in (3,4):
        with t.at(478,'plan cell prior/outcome'):
            t.e(C(B('&',W(6),K(511))),'cell local');t.e(row('pl',V('cell'),0),'prior local');t.check(B('==',V('prior'),K('ABSENT')))
            if variant!='empty':t.check(B('==',V('prior'),W(6)))
            t.e(K({'empty':0,'conflict':1,'reuse':2}[variant]),'outcome local');t.check(B('==',V('outcome'),K(2)))
            if variant=='reuse':t.check(*[B('!=',row('pl',V('cell'),i),W(6+i)) for i in (1,2,3)])
            t.check(B('==',W(1),K(4)))
            if event==4:
                t.check(B('==',V('outcome'),K(1)));t.check(B('!=',W(13),V('outcome')),B('!=',W(14),V('prior') if variant=='conflict' else K('ABSENT'))); t.check(B('!=',V('outcome'),K(2)))
    elif event==5:
        with t.at(515,'MissReady plan identity and readiness'):
            t.e(C(B('&',W(6),K(511))),'cell local');t.check(*[B('!=',row('pl',V('cell'),i),W(6+i)) for i in (0,1,2,3)])
            t.check(B('!=',row('pl',V('cell'),4),K(0)),B('!=',row('pl',V('cell'),4),W(13)),logic='and')
            t.check(B('==',W(13),K(0)),B('>',W(13),F('f.entry')),B('!=',W(14),F('f.base')),B('!=',W(15),F('f.capacity')))
            t.e(F('f.base'),'checked_add received self');t.e(W(13),'checked_add received argument');t.many('checked_add entry','checked add','overflow predicate','overflow branch','Some tag source','sum -> Some payload source');t.copy('complete Option<u64>16 -> is_none_or received self16',16)
            t.many('checked_add return control','closure environment capacity borrow','is_none_or entry','Option tag source','Some branch','Some payload -> closure v argument','closure entry');t.e(B('>',V('v'),F('f.capacity')),'closure designated bool');t.many('closure return control','closure bool -> is_none_or bool','is_none_or return control','is_none_or bool -> if predicate','if branch')
    elif event in (6,7,8):
        ck(570,B('!=',Q(15),K(1)))
        with t.at(573,'outstanding and strict slot'):
            t.e(B('&',Q(10),U('!',Q(12))),'outstanding local');t.check(B('==',V('outstanding'),K(0)))
            t.e(V('outstanding'),'trailing_zeros received self');t.many('trailing_zeros entry','trailing_zeros primitive','result -> returned scalar','trailing_zeros return');t.e(C(V('trailing_zeros result'),'u64'),'expected local')
            t.check(B('!=',W(10),V('expected')),B('>=',V('expected'),F('f.slots')));t.e(C(V('expected')),'slot local');t.check(B('==',W(1),K(6)))
        if event==6:ck(584,B('!=',row('rr',V('slot'),0),K(1)),B('!=',row('rr',V('slot'),3),K(0)),B('!=',row('rr',V('slot'),2),W(13)))
        else:
            ck(588,B('==',W(1),K(7)))
            if event==7:ck(589,B('!=',Q(13),V('expected')),B('!=',row('rr',V('slot'),0),K(1)),B('!=',row('rr',V('slot'),3),K(0)),B('!=',row('rr',V('slot'),2),W(13)))
            else:
                ck(603,B('!=',Q(13),V('expected')),B('==',B('&',Q(11),B('<<',K(1),V('expected'))),K(0)),B('!=',row('rr',V('slot'),0),K(0)))
                ck(607,B('!=',W(13),L('ld','b',B('+',F('SCALAR.base'),B('*',K(138),K(8))))))
    elif event in (9,10):ck(615,B('!=',Q(15),K(1)),B('!=',Q(12),Q(10)),B('!=',W(13),L('cq',K(18))))
    elif event==11:
        ck(620,B('!=',W(12),Q(9)),B('==',Q(9),K('ABSENT')));ck(623,B('!=',V('first_pin'),L('cq',K(16))),B('!=',W(11),V('first_pin')),B('>=',V('first_pin'),F('f.pins')))
        with t.at(626,'publication slot choice and identity'):
            t.check(B('==',W(13),K(0)));t.e(L('cq',K(17)) if variant=='hit' else Q(14),'slot source');t.check(B('>=',V('slot'),F('f.slots')),B('!=',W(10),V('slot')));t.e(C(V('slot')),'shadowed slot local');t.check(B('==',W(13),K(0)))
            if variant=='hit':t.check(B('!=',row('rr',V('slot'),0),K(1)),B('!=',row('rr',V('slot'),1),W(6)),B('!=',row('rr',V('slot'),2),W(14)))
            else:t.check(B('!=',Q(15),K(1)),B('!=',Q(10),Q(12)),B('!=',row('rr',V('slot'),0),K(0)),B('!=',W(14),L('cq',K(18))))
        ck(657,B('!=',W(15),V('pins')),B('>',V('pins'),F('f.pins')),B('==',Q(8),F('f.pins')))
    elif event==12:
        with t.at(674,'release slot and complete token/resident joins'):
            t.e(C(W(10)),'slot local');t.e(C(W(11)),'pin local')
            t.check(B('>=',V('slot'),C(F('f.slots'))),B('>=',V('pin'),C(F('f.pins'))),B('!=',row('pr',V('pin'),0),W(10)),B('!=',row('pr',V('pin'),1),W(12)))
            t.check(B('!=',row('rr',V('slot'),0),K(1)),B('!=',row('rr',V('slot'),1),W(6)),B('!=',row('rr',V('slot'),2),W(13)),B('==',row('rr',V('slot'),3),K(0)),B('==',Q(8),K(0)),B('!=',W(15),B('-',row('rr',V('slot'),3),K(1))))
    return t

def g7(form='success',owner='G7'):
    t=Trace(owner+'.'+form,owner)
    with t.at(1193,'actual semantic call boundaries'):
        t.handle('arena.bytes','semantic.received_b');t.thin('candidate','semantic.received_c');t.thin('loan','semantic.received_loan');t.thin('p','semantic.received_p');t.thin('semantic_steps','semantic.received_steps');t.op('semantic call entry')
    if owner=='G128':
        with t.at(314,'zero-debit terminal guard prefix'):
            t.many('b slice reborrow','b.data -> len received data','b.len -> len received len','len entry','len source -> returned length','len return')
            if form=='short-arena-poison':t.check(B('!=',V('length'),K('ARENA_BYTES')))
            else:t.check(B('!=',V('length'),K('ARENA_BYTES')),B('!=',F('steps.spent'),K(0)))
            if form=='underfunded':t.check(B('<',F('steps.remaining'),K(7680)))
    if form=='readiness-reject':
        with t.at(616,'actual repeated readiness-rejection reason calculation'):
            t.check(B('!=',W(13),L('cq',K(18))));t.e(K(10),'reject received reason source')
    with t.at(768 if form=='success' else 174,'complete SemanticReply constructor and returns'):t.reply('inline' if form in ('success','underfunded','commit-poison') else ('poison' if 'poison' in form else 'reject'),0 if owner=='G128' else 7680)
    with t.at(1200,'calls increment and actual caller reply audit'):
        t.e(B('+',F('p.calls'),K(1)),'p.calls destination')
        t.many('p owner -> calls destination projection','calls field address','calls result -> destination field')
        t.check(B('==',F('received.status'),K(1)))
        if form=='success':
            t.check(B('==',F('received.reason'),K(0)),B('==',F('received.debit'),K(7680)),B('==',F('semantic_steps.spent'),K(7680)),B('==',F('semantic_steps.remaining'),K(0)),logic='and')
            with t.at(1209,'complete caller successor snapshot loop'):
                t.loop(16,'snapshot',lambda i:t.write_index('p.q',V('i'),L('cq',V('i'))))
                t.e(L('cq',K(16)),'remember_pin received n');t.thin('p','remember_pin received self');t.op('remember_pin entry');t.check(B('==',V('n'),K('ABSENT')));t.e(B('|',B('&',F('p.latch'),K(255)),B('<<',B('+',V('n'),K(1)),K(8))),'latch destination');t.many('remember_pin field store','unit source','unit/control -> caller','unit discard')
        else:
            t.check(B('==',F('received.status'),K(2)))
            if 'poison' not in form:
                t.check(B('==',F('received.reason'),K(1)));t.range_contains(6,14,F('received.reason'));t.many('reason alternatives result -> conjunction','conjunction short circuit')
                t.check(B('==',F('received.debit'),K(7680)),B('==',F('semantic_steps.spent'),K(7680)),B('==',F('semantic_steps.remaining'),K(0)),logic='and')
                if form=='underfunded':t.check(B('==',F('received.reason'),K(1)),B('==',F('received.debit'),K(0)),B('==',F('semantic_steps.spent'),K(0)),B('<',F('semantic_steps.remaining'),K(7680)),logic='and')
            t.latch()
    # The cleanup call/boolean and cleanup-fault latch belong to selected G6.
    return t

def shape(t,stage=7,latch=0):
    t.thin('p.q','shape_q received q');t.e(F('p.calls'),'shape_q received calls');term=t.terminal();t.e(term,'shape_q received latch');t.e(F('s.framed'),'shape_q received n');t.thin('f','shape_q received f');t.op('shape_q entry')
    t.check(B('>',Q(0),V('n')),B('>',V('calls'),V('n')),B('>',Q(3),K(10)),B('>',Q(6),F('f.slots')),B('>',Q(8),F('f.pins')),B('==',Q(9),K(0)),B('!=',B('==',Q(6),K(0)),B('==',Q(7),K(0))),B('>',Q(8),K(0)))
    t.check(B('!=',Q(3),K(0)))
    if stage:t.check(B('==',Q(4),K(0)),B('>=',Q(5),K(80000)))
    contains=t.range_contains(6,10,Q(3));t.check(contains)
    if 6<=stage<=10:
        t.e(F('f.slots'),'selected_mask received slots');t.op('selected_mask entry');t.check(B('==',V('slots'),K(64)));t.e(B('-',B('<<',K(1),V('slots')),K(1)),'selected_mask return');t.many('selected_mask return control','selected_mask received u64')
        t.check(B('!=',B('&',B('|',B('|',Q(10),Q(11)),Q(12)),U('!',V('mask'))),K(0)),B('!=',B('&',Q(11),U('!',Q(10))),K(0)),B('!=',B('&',Q(12),U('!',Q(11))),K(0)))
        t.check(B('>',Q(15),K(1)),B('==',Q(15),K(1)),B('>=',Q(14),F('f.slots')))
        t.check(B('==',Q(3),K(7)))
        if stage!=7:t.check(B('==',Q(3),K(8)))
        if stage in (7,8):t.check(B('!=',Q(15),K(1)),B('>=',Q(13),F('f.slots')),B('==',B('&',Q(10),B('<<',K(1),Q(13))),K(0)))
    t.check(B('==',Q(0),K(0)))
    # Keep the full initial-q conditional as covering work even on noninitial
    # recipes. It is deliberately explicit slack, never an exact-path claim.
    t.check(*[B('!=',Q(i),K(1 if i==9 else 0)) for i in (1,2,3,6,7,8,9)])
    t.check(B('==',V('latch'),K(0)))
    if latch==0:t.check(B('==',V('calls'),Q(0)),B('==',Q(0),V('n')),B('>',V('calls'),K(0)),logic='and')
    else:
        t.check(B('==',V('latch'),K(1)));t.range_contains(6,14,V('latch'));t.check(B('==',V('calls'),B('+',Q(0),K(1))),B('<=',V('calls'),V('n')),logic='and')
    t.many('shape_q bool source -> caller received bool','shape_q return control')

def sf(stage=7,terminal=0,child=3):
    t=Trace(f'SF.stage{stage}.terminal{terminal}.child{child}','SF')
    with t.at(1366,'projection actual caller arguments'):
        for name in ('p','paid','s','result','envelope'):t.thin(name,'projection received '+name)
        t.thin('config','as_ref received self');t.op('Option.as_ref entry');t.many('Option tag operand','Some branch','Fixture payload address','Fixture reference borrow','complete Option<&Fixture>8 -> designated8','as_ref return','Option pointer8 -> projection received f');t.op('projection entry')
    with t.at(928,'zero observation constructor'):
        t.e(K('Unavailable'),'constructor.boundary');t.e(K(5),'why received n');t.op('why entry');t.many('closed reason match','reason source -> designated enum','why return control','enum8 -> constructor.reason')
        t.e(K(0),'repeat scalar source');t.e(K(30),'repeat length source')
        for i in range(30):t.op(f'repeat source -> extent[{i}] source')
        t.copy('extent240 source -> observation constructor.extent240',240);t.copy('observation constructor256 -> z256',256)
        t.write_index('z.extent',19,B('+',B('+',B('*',K(512),F('paid.setup')),B('*',K(256),F('paid.finish'))),B('*',K(7680),F('paid.records'))));t.write_index('z.extent',20,F('paid.setup'));t.write_index('z.extent',21,F('paid.finish'))
    with t.at(937,'ordered projection T01..T09 admission'):
        t.many('input Result40 reference -> pattern operand','Err tag predicate','Err branch')
        t.thin('env','env.reason received self');t.many('reason getter entry','reason field address','reason reference -> caller received reference','reason getter return','InternalPoisoned pattern match');t.check(B('==',t.terminal(),K(16)))
        t.check(B('>',B('>>',F('p.latch'),K(8)),K(64)))
        t.many('Option<&Fixture> source -> is_some_and received self','closure environment p borrow','is_some_and entry','Some tag predicate','Some branch','Fixture pointer -> closure v');t.e(B('>',B('>>',F('p.latch'),K(8)),F('v.pins')),'closure result');t.many('closure return','is_some_and bool return','or short circuit')
        t.check(B('>',F('p.calls'),F('paid.records')),B('==',F('p.calls'),K(0)))
        t.check(B('!=',t.terminal(),K(0)))
        t.check(B('!=',t.terminal(),K(0)),B('!=',t.terminal(),K(1)),U('!',t.range_contains(6,14,t.terminal())),logic='and')
        t.thin('env','boundary getter self');t.thin('env','reason getter self');t.many('boundary getter entry','boundary field reference source -> received reference','boundary getter return','reason getter entry','reason field reference source -> received reference','reason getter return','pair source of two references','closed child match dispatch')
        t.many('input Ok(true) pattern','input tag/value predicate','s.complete field operand','s.complete predicate','s.limited field operand','not limited predicate','s.flags field operand','flags closed predicate','child source -> child local')
        t.check(B('==',V('child'),K(0)));t.check(B('==',V('child'),K(1)));t.check(B('==',F('p.calls'),K(0)));t.check(B('==',t.terminal(),K(0)));t.many('Some f pattern operand','Some predicate','Some branch','Some pointer -> f local')
        t.check(B('>',F('p.calls'),F('paid.records')),B('>',F('s.framed'),F('paid.records')))
        shape(t,stage,terminal)
        t.many('shape result -> not operand','logical not','or short circuit');t.check(B('==',t.terminal(),K(0)),B('==',V('child'),K(4)),B('!=',Q(3),K(0)),logic='and')
    with t.at(1032,'projection final fields'):
        t.thin('p.q','q local');t.e(I('q',3),'stage local');t.e(B('!=',V('stage'),K(0)),'active local');t.e(t.range_contains(6,10,V('stage')),'planned local');t.check(B('==',V('stage'),K(7)),B('==',V('stage'),K(8)));t.e(V('pending result'),'pending local')
        for v in (14,1,0):t.check(B('==',t.terminal(),K(v)))
        t.check(B('==',V('child'),K(2)));t.check(B('==',V('child'),K(3)));t.e(K('boundary selected'),'z.boundary store')
        t.check(B('!=',t.terminal(),K(0)));t.check(B('==',V('child'),K(2)));t.e(t.terminal() if terminal else K(0),'why received n');t.many('why entry','closed reason dispatch','reason -> designated enum','why return control','enum -> z.reason')
        values={0:F('s.framed'),1:I('q',0),2:B('+',I('q',0),K(1)) if terminal else B('+',F('s.framed'),K(1)) if child==2 else K(0),3:I('q',0),4:I('q',1),5:I('q',2),6:I('q',4) if stage else K(0),7:I('q',5) if stage else K('ABSENT'),8:I('q',6),9:I('q',7),10:I('q',8),11:I('q',9),12:B('&',I('q',5),K(511)) if 3<=stage<=10 else K('ABSENT'),13:I('q',10) if 6<=stage<=10 else K(0),14:I('q',11) if 6<=stage<=10 else K(0),15:I('q',12) if 6<=stage<=10 else K(0),16:I('q',13) if stage in (7,8) else K('ABSENT'),17:I('q',14) if 6<=stage<=10 else K('ABSENT'),18:B('+',I('q',0),K(1)) if terminal==14 else K(0),22:K(1),23:V('bool->u64 result')}
        for i,value in values.items():
            if i in (2,18):t.check(B('!=',t.terminal(),K(0)))
            if i in (6,7):t.check(V('active'))
            if i==12:t.range_contains(3,10,V('stage'))
            if i in (13,14,15,17):t.check(V('planned'))
            if i==17:t.check(B('==',I('q',15),K(1)))
            if i==16:t.check(V('pending'))
            if i==23:t.check(B('!=',t.terminal(),K(0)),B('!=',V('child'),K(4)));t.many('u64::from received bool','conversion entry','bool->u64','converted bool source -> result','conversion return')
            t.write_index('z.extent',i,value)
        # Complete alternate early projection assignments and why(16) are
        # explicitly covered as additional union work. They replace this tail
        # on those paths; retaining both can only increase the bound.
        for line in (953,963,1019,1028):
            t.e(K('InternalPoisoned'),'alternate z.boundary source');t.e(K(16),'alternate why received n');t.many('alternate why entry','alternate closed reason dispatch','alternate reason enum -> z.reason','alternate why return')
    with t.at(1088,'complete observation return and outer Result/caller chain'):
        t.copy('z256 -> projection designated256',256);t.op('projection return control');t.copy('projection designated256 -> cache_state received256',256)
        # existing framing/envelope values are retained as separate source fields.
        for name,width in [('framing',104),('envelope',128),('cache_state',256)]:t.copy(name+' source -> aggregate constructor field',width)
        t.copy('aggregate constructor488 -> Ok Result source488',488);t.copy('complete Ok Result488 -> public designated Result488',488);t.op('public return control');t.copy('public designated Result488 -> external caller received Result488',488)
        t.copy('external complete Result488 -> extraction received self488',488);t.many('extraction entry','Ok discriminant operand','Ok branch');t.copy('Ok aggregate488 -> extraction designated aggregate488',488);t.op('extraction return control');t.copy('designated aggregate488 -> external aggregate received488',488)
    return t

def ss():
    t=Trace('SS.complete-new-source','SS')
    with t.at(1314,'new reservation calls and Result40 source/received paths'):
        for name in ('report256','setup512','report128'):
            t.line={'report256':1314,'setup512':1315,'report128':1110}[name]
            t.thin('budget',name+' received self');t.e(K(name),name+' received n');t.op(name+' call entry');t.budget_body('setup' if name.startswith('setup') else 'report');t.copy(name+' complete Result40 source -> received40',40);t.many(name+' return control','Result tag -> Try operand','Try branch','Ok unit extraction','unit continuation')
    with t.at(1316,'new wrapper source constructors and call edges'):
        for name,n in [('Paid',3),('Progress',18)]:
            for i in range(n):t.e(K(1 if name=='Paid' and i<2 else 0),name+f' constructor field{i}')
            if name=='Progress':
                t.e(K(0),'q repeat source');t.e(K(16),'q repeat length');t.copy('q repeat array128 -> Progress constructor.q128',128)
            t.copy(name+' constructor source -> local received',24 if name=='Paid' else 144)
        t.many('None Option<Fixture> tag source');t.copy('complete Option<Fixture> source -> config local',80)
        for name in ('p','paid','config'):t.thin(name,'cache_inputs received '+name)
        t.copy('Fixture72 source -> Some constructor payload72',72);t.copy('Some(f) complete Option<Fixture>80 -> config destination80',80)
        for name in ('p','paid'):t.thin(name,'cache_walk received '+name)
    with t.at(1130,'new fixed scalar defaults and views'):
        for i,value in [(5,'ABSENT'),(9,1),(13,'ABSENT'),(14,'ABSENT')]:t.write_index('p.q',i,K(value))
        for cell,value in [(17,K(1)),(24,F('f.slots')),(25,F('f.pins')),(26,F('f.base')),(27,F('f.capacity')),(28,F('f.entry'))]:t.st(B('+',F('SCALAR.base'),B('*',K(cell),K(8))),value)
    with t.at(1183,'per-record semantic dispatch new borrows/source values paid by G1'):
        # This is a declaration boundary map only; no record work charged to SS.
        t.op('setup fixed p/paid/config views end initialization')
    return t

def caller_only():
    t=Trace('G7.envelope-terminal-or-preloan-unreadable','G7')
    with t.at(1171,'new p latching after existing envelope validator'):
        t.latch();t.check(B('==',I('e.reply.words',0),K(3)),B('==',I('e.reply.words',1),K(15)));t.latch()
        t.check(B('==',t.terminal(),K(0)),B('==',I('e.reply.words',0),K(1)),B('==',I('e.reply.words',1),K(0)),logic='and')
        t.many('arena slice data source -> len received data','arena slice length source -> len received len','len entry','length -> designated usize','len return control','length -> caller received usize');t.check(B('!=',V('length'),K('ARENA_BYTES')));t.latch()
    return t

def finish_error():
    t=Trace('SF.inputErr-early-projection','SF')
    # An actual T01 early-projection branch. Constructor/paid debit initialization
    # is shared source with sf(); copy just that source-generated site, not a
    # numeric asserted total. No product code is imported/executed.
    base=sf(0,0,4)
    for op in base.ops:
        if op['site'] in ('projection actual caller arguments','zero observation constructor'):
            t.line=op['line'];t.site=op['site'];t.op(op['operation'],op['kind'],op['bytes'])
    with t.at(937,'actual input Err code dispatch'):
        t.many('input Result reference -> Err pattern','Err discriminant predicate','Err branch','Error32 payload reference -> e binding');t.check(B('==',F('e.code'),K('BUDGET')));t.e(K('AnalysisLimited/Unavailable selected enum'),'z.boundary store');t.check(B('==',F('e.code'),K('BINDING')));t.check(B('==',F('e.code'),K('BUDGET')));t.e(K(3),'why received n');t.many('why entry','closed reason dispatch','reason enum -> z.reason','why return')
    with t.at(950,'early projection full value and public Result/caller chain'):
        for op in base.ops:
            if op['site']=='complete observation return and outer Result/caller chain':t.op(op['operation'],op['kind'],op['bytes'])
    return t

def early(name='finish-admission-failure'):
    t=Trace('F42.'+name,'F42')
    with t.at(1309,'inherited error body with complete public Result488'):
        t.thin('budget','report received self');t.e(K(256),'report received n');t.op('report entry');t.budget_body('report')
        t.copy('report complete Result40 designated -> caller received40',40);t.op('report return control')
        t.many('existing Budget/wrapper failed Result discriminant operand','Try failure branch','Error32 source -> FromResidual received error source','FromResidual entry control')
        t.copy('original Error32 source -> residual received Error32',32)
        t.many('Err constructor tag source','Error32 payload source -> Err constructor payload')
        t.copy('complete Err Result488 source -> public designated Result488',488);t.op('public return control');t.copy('public designated Result488 -> external caller Result488',488)
        t.copy('external complete Result488 -> extraction received self488',488);t.many('extraction entry','Err discriminant operand','Err branch');t.copy('active Error32 -> designated Error32',32);t.op('extraction return');t.copy('designated Error32 -> caller received Error32',32)
    return t

def setup_failure():
    t=Trace('SF.SS-admission-failure','SF')
    with t.at(1315,'SS failure after successful SF reservation'):
        t.thin('budget','setup received self');t.e(K(512),'setup received n');t.op('setup entry');t.budget_body('setup');t.copy('setup complete Result40 designated -> caller received40',40);t.op('setup return')
    # Full public Error suffix is still required, without an aggregate payload.
    base=early()
    start=False
    for op in base.ops:
        if op['operation']=='existing Budget/wrapper failed Result discriminant operand':start=True
        if not start:continue
        t.line=op['line'];t.site='SS-failure complete public Error suffix';t.op(op['operation'],op['kind'],op['bytes'])
    return t

def build():
    if sha(SOURCE.read_bytes())!=SOURCE_SHA:raise ValueError('frozen source drift')
    paths=[]
    for e in range(1,14):
        variants=('empty','conflict','reuse') if e in (3,4) else ('hit','built') if e==11 else ('miss','hit') if e==2 else ('',)
        paths.extend(g1(e,v) for v in variants)
    paths.extend(g7(x) for x in ('success','reject','readiness-reject','paid-poison','commit-poison'))
    paths.extend(g7(x,'G128') for x in ('invalid-spent-poison','short-arena-poison','underfunded'))
    paths.extend(sf(s,n,c) for s,n,c in [(0,0,4),(7,0,3),(8,14,3),(7,6,3),(0,1,2),(7,0,2)])
    paths.extend([ss(),early(),setup_failure(),caller_only(),finish_error()])
    return paths

def main():
    paths=build();rows=[t.summary() for t in paths]
    save('paths.json',{'schema':1,'source_sha256':SOURCE_SHA,'paths':rows,'caps':CAPS,'maxima':{owner:max((r for r in rows if r['owner']==owner),key=lambda r:r['groups']) for owner in CAPS},'status':'unselected producer source accounting proposal; review required'})
    with gzip.GzipFile(filename=str(HERE/'operations.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps({t.name:t.ops for t in paths},separators=(',',':')).encode())
    partitions={}
    for t in paths:
        scalar=[o['id'] for o in t.ops if o['kind']=='scalar'];copies=[{'id':o['id'],'bytes':o['bytes']} for o in t.ops if o['kind']=='copy']
        partitions[t.name]={'owner':t.owner,'scalar_blocks':[scalar[i:i+16] for i in range(0,len(scalar),16)],'payload_copy_groups':copies}
    save('partitions.json',partitions)
    templates=[]
    for name,fn in [('ld Candidate/literal',lambda t:t.ld('c',K(0),'target',True)),('cq literal',lambda t:t.e(L('cq',K(0)),'target')),('rr literal field',lambda t:t.e(L('rr',K(0),K(0)),'target')),('indexed record word',lambda t:t.e(I('w',1),'target')),('IndexMut p.q literal/value',lambda t:t.write_index('p.q',1,K(1))),('st slice/literal/value',lambda t:t.st(K(1),K(1)))]:
        t=Trace('template.'+name,'SS');fn(t);templates.append({'name':name,**t.summary(),'operations':t.ops})
    save('templates.json',{'templates':templates,'component_scope':'Independently authored source expression/index/view/helper expansion; selected G6 reference is checked as data, never imported/executed'})
    print(json.dumps({owner:max(r['groups'] for r in rows if r['owner']==owner) for owner in CAPS},sort_keys=True))

if __name__=='__main__':main()
