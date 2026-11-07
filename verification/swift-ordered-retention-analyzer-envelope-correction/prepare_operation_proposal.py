#!/usr/bin/env python3
"""Owned proposal construction only. Does not compile, execute source or replay tests.
Expression occurrence inventories aid review; independent source review is required.
"""
from pathlib import Path
import hashlib,json,re,math,shutil,datetime
P=Path(__file__).resolve().parent
D=P/'commands/operation-ledger-proposal-1'
S=P/'src/envelope.rs'; A=P/'src/analyzer.rs'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,x): (D/name).write_text(json.dumps(x,indent=2)+'\n')
rows=[]
def row(id,phase,source,atoms=(),copies=(),repeat=1,note=''):
    atoms=[{'operation':a,'count':n} for a,n in atoms]
    copies=[{'edge':e,'bytes':b,'count':n} for e,b,n in copies]
    assert all(n['count']>=0 for n in atoms)
    assert all(0<c['bytes']<=128 for c in copies)
    scalar=sum(a['count'] for a in atoms)
    cr=sum(c['count'] for c in copies)
    r={'id':id,'phase':phase,'source':source,'scalar_atoms':atoms,'scalar_operations':scalar,'scalar_groups':math.ceil(scalar/16),'copies':copies,'copy_groups':cr,'repeat':repeat,'groups':repeat*(math.ceil(scalar/16)+cr),'note':note}
    rows.append(r);return r
# Fixed semantic primitives are caller-visible Rust operations, not lowered CPU work.
# The expression scanner only expands the explicitly selected expression strings.
# Every occurrence inventory is emitted; it cannot authorize a cost or release.
arr=re.compile(r'(?:p\.reply\.words|prior|next|w)\[([0-9]+)\]')
tok=re.compile(r'0x[0-9A-Fa-f_]+|[0-9][0-9_]*|[A-Za-z_][A-Za-z_0-9]*(?:::[A-Za-z_0-9]+)*(?:\.[A-Za-z_0-9]+)*|&&|\|\||==|!=|<=|>=|<<|>>|[!<>&|+*/%-]')
def expr_atoms(expr):
    out=[]
    spans=[]
    for m in arr.finditer(expr):
        base=m.group(0).split('[')[0]
        count=6+base.count('.')
        out.append((f'{m.group(0)}: base/native borrow, index argument, bounds compare, bounds branch, address/native return, scalar load'+(' plus two explicit member selections' if count==8 else ''),count))
        spans.append((m.start(),m.end()))
    rest=expr
    for a,b in reversed(spans):rest=rest[:a]+' '*(b-a)+rest[b:]
    for m in tok.finditer(rest):
        t=m.group(0)
        if t=='as':out.append(('scalar cast',1))
        elif t in ('&&','||'):out.append((f'{t} short-circuit control',1))
        elif t in ('==','!=','<=','>=','<','>','<<','>>','&','|','+','-','*','/','%','!'):out.append((f'{t} scalar operator',1))
        else:out.append((f'{t}: native operand read/materialization',1))
    return out

def expr_row(id,phase,source,expr,extra=(),note=''):
    r=row(id,phase,source,expr_atoms(expr)+list(extra),note=note)
    r['expression']=expr
    return r

def groups(ids):return sum(next(r['groups'] for r in rows if r['id']==i) for i in ids)
# LEAF: every block has its own rounded scalar capacity. Unused credits cannot
# be reused by another block. Mutually exclusive reply edges use one maximum,
# because the function returns once; transition branches below are all reserved.
leaf=[]
def lr(*a,**k):r=row(*a,phase='leaf',**k);leaf.append(r['id']);return r
lr('L01',source='envelope.rs:127-137 entry through whole-slice preflight',atoms=[('four native parameter receiving/binding operations',4),('steps.remaining load, threshold load, comparison, underfunded binding',4),('steps.spent load, zero materialize, compare, branch',4),('!underfunded and branch',2),('remaining load, threshold load, subtraction, remaining store',4),('threshold load and spent store',2),('arena native receiver/length return, bound materialize, comparison, branch',5)])
lr('L02',source='envelope.rs:138-139 fixed local initialization',atoms=[('prior zero materialization and twelve scalar element stores',13),('word zero materialization and eight scalar byte stores',9)],copies=[('prior96 source literal -> prior local',96,1)])
read_atoms=[('mutable word/native borrow formation',1),('two Range endpoint materializations and two field stores',4),('shared arena reborrow/argument preparation',1),('range bounds checks and branch (start<=end,end<=length)',4),('source slice/native result binding',1),('copy length equality check/branch',2),('copy call/return control',2),('prior destination base/index argument/bounds comparison/branch/address/store',6),('word8 scalar source/read and LE argument/return/decode handling',4)]
read_copies=[('Range16 literal -> Index argument',16,1),('shared arena slice16 -> Index receiver',16,1),('Index returned slice16 -> caller result',16,1),('caller source slice16 -> copy_from_slice source argument',16,1),('word mutable unsized slice16 -> copy_from_slice receiver',16,1),('source range8 -> word8 data',8,1)]
lr('L03',source='envelope.rs:140-151 twelve separately written prior reads',atoms=read_atoms,copies=read_copies,repeat=12,note='No loop/CELLS indexing/Pair/checked arithmetic remains. Explicitly includes both Index return and later copy argument edges; no source/destination double charge for a single edge.')
lr('L04',source='envelope.rs:152 guard dispatch (normal funded branch)',atoms=[('underfunded read and branch',2)])
r=expr_row('L05','leaf','envelope.rs:153 retained invariants','prior[7] > 10 || prior[4] > 5 || prior[5] >= 64 || prior[6] >= 64 || prior[10] > 1 || prior[11] > 1',[('if dispatch',1)]);leaf.append(r['id'])
lr('L06',source='envelope.rs:154-155 record borrow binding and shape call',atoms=[('record.words member load/native local binding',2),('shape native argument preparation/transfer and call/return control',4),('returned boolean negation and if dispatch',2)])
shape_common=[]
for id,source,expr,extra in [
 ('H01','envelope.rs:106','w[1]',[('k store',1)]),
 ('H02','envelope.rs:106','w[6]',[('f store',1)]),
 ('H03','envelope.rs:107','k == 0 || k > 14 || w[2] > 5',[('if dispatch',1)]),
 ('H04','envelope.rs:108','w[7] == ABSENT && w[8] == ABSENT && w[9] == ABSENT',[('absent store',1)]),
 ('H05','envelope.rs:109','w[10] == ABSENT && w[11] == ABSENT && w[12] == 0',[('no_slots store',1)]),
 ('H06','envelope.rs:110','f < 80_000 && w[7] != ABSENT && w[8] != ABSENT && w[9] <= u32::MAX as u64 && w[7] <= ABSENT - w[8]',[('full store',1)]),
]: shape_common.append(expr_row(id,'shape',source,expr,extra)['id'])
row('H07','shape','envelope.rs:111-123 closed match dispatch',atoms=[('fourteen possible kind tests: kind read, pattern materialization, comparison, branch',56),('wildcard branch/boolean return',2)])
shape_common.append('H07')
shape_exprs=[
'w[3] > 0 && f < 80_000 && absent && no_slots && w[13] == 0 && w[14] == 0 && w[15] == 0',
'w[3] > 0 && full && w[11] == ABSENT && w[12] == 0 && w[14] == 0 && w[15] == 0 && ((w[13] == 0 && w[10] == ABSENT) || (w[13] == 1 && w[10] < 64))',
'w[3] > 0 && full && no_slots && w[13] == 0 && w[14] == 0 && w[15] == (f & 511)',
'w[3] > 0 && full && no_slots && w[15] == (f & 511) && (((w[13] == 0 || w[13] == 2) && w[14] == ABSENT) || (w[13] == 1 && w[14] < 80_000 && w[14] != f))',
'w[3] > 0 && full && no_slots && w[13] > 0 && w[14] <= w[15] && w[13] <= w[15] - w[14]',
'w[3] > 0 && full && w[10] < 64 && w[11] == ABSENT && w[12] == 0 && w[13] > 0 && w[14] == 0 && w[15] == 0',
'w[3] > 0 && full && w[10] < 64 && w[11] == ABSENT && w[12] == 0 && w[13] > 0 && w[14] == 0 && w[15] == 0',
'w[3] > 0 && full && w[10] < 64 && w[11] == ABSENT && w[12] == 0 && w[13] > 0 && w[14] == 0 && w[15] == 0',
'w[3] > 0 && full && no_slots && w[13] > 0 && w[14] == 0 && w[15] == 0',
'w[3] > 0 && full && no_slots && w[13] > 0 && w[14] == 0 && w[15] == 0',
'w[3] > 0 && full && w[10] < 64 && w[11] < 64 && w[12] > 0 && w[13] <= 1 && w[14] > 0 && w[15] > 0 && w[15] <= 64',
'w[3] == 0 && f < 80_000 && w[7] != ABSENT && w[8] == ABSENT && w[9] <= u32::MAX as u64 && w[10] < 64 && w[11] < 64 && w[12] > 0 && w[13] > 0 && w[14] == 0 && w[15] < 64',
'w[3] == 0 && f == ABSENT && absent && no_slots && w[13] == w[2] && w[14] == 0 && w[15] == 0',
'absent && (f == ABSENT || f < 80_000) && no_slots && w[13] > 0 && w[13] <= 21 && w[14] > 0 && w[14] <= 24 && w[15] > 0 && w[15] <= 6'
]
shape_arms=[]
for i,e in enumerate(shape_exprs,1):shape_arms.append(expr_row(f'HA{i:02}','shape-arm',f'envelope.rs:112-122 selected kind{i}',e,[('boolean return control',1)])['id'])
shape_total=groups(shape_common)+max(groups([i]) for i in shape_arms)
# Separate linked subtotal, not a second charge of H rows.
lr('L07',source='shape helper H01-H07 plus selected HA arm',note=f'LINKED subtotal, charged once: common={groups(shape_common)}, maximum one arm={max(groups([i]) for i in shape_arms)}. Selection is a single Rust match; no execution can use two arms.')['linked_groups']=shape_total
rows[-1]['groups']=shape_total
for id,source,e in [('L08','envelope.rs:156','prior[0] == ABSENT || w[0] != prior[0] + 1 || w[4] < prior[1] || w[5] < prior[2]'),('L09','envelope.rs:157','prior[4] == 5')]:
 leaf.append(expr_row(id,'leaf',source,e,[('if dispatch',1)])['id'])
lr('L10',source='envelope.rs:158',copies=[('prior96 -> next96',96,1)])
# Explicit static union of all transition predicates: safe upper, each named
# alternative has a disjoint reserved row; inactive credits are never reused.
transition=[]
conds=[
(159,'w[1] == 13'),(160,'prior[7] != 0 || w[2] <= prior[4] || prior[5] & (1 << w[2]) != 0'),
(163,'w[2] != prior[4]'),(164,'w[1] == 12'),(165,'prior[7] != 0'),(166,'w[1] == 14'),(167,'w[3] == 0'),
(168,'prior[7] != 0 || prior[10] != 0'),(171,'prior[7] == 0 || prior[11] != 0 || prior[10] != 0 || w[3] != prior[8]'),
(175,'prior[10] != 0 || prior[11] != 0'),(176,'w[1] == 1'),(177,'prior[7] != 0 || prior[4] >= 4 || prior[3] == ABSENT || w[3] != prior[3] + 1'),
(180,'w[3] != prior[8] || w[6] != prior[9]'),(181,'w[1] == 2'),(182,'prior[7] != 1'),(183,'w[13] == 1'),(184,'w[1] == 11'),
(185,'!((prior[7] == 2 && w[13] == 0) || (prior[7] == 10 && w[13] == 1))'),(189,'prior[7] != before')]
for n,(line,e) in enumerate(conds,1):transition.append(expr_row(f'TP{n:02}','transition',f'envelope.rs:{line}',e,[('if/else dispatch',1)])['id'])
assigns=[(161,'4','w[2]'),(169,'10','1'),(172,'7','0'),(172,'11','1'),(178,'7','1'),(178,'3','w[3]'),(178,'8','w[3]'),(178,'9','w[6]'),(183,'7','2'),(183,'7','3'),(186,'7','0'),(190,'7','after'),(195,'0','w[0]'),(195,'1','w[4]'),(195,'2','w[5]')]
for n,(line,cell,e) in enumerate(assigns,1):transition.append(row(f'TS{n:02}','transition',f'envelope.rs:{line} next[{cell}] store',atoms=expr_atoms(e)+[('destination base/native borrow,index,bounds comparison,bounds branch,address,store',6)])['id'])
transition.append(row('TC01','transition','envelope.rs:161 compound mask assignment',atoms=expr_atoms('next[5] | (1 << w[2])')+[('single already indexed destination scalar store',1)])['id'])
transition.append(row('TC02','transition','envelope.rs:188 complete closed stage match',atoms=[('w[1] array read primitive',6),('eight kind tests: operand read, pattern, compare, branch',32),('sixteen before/after literal source reads and field stores',32),('before/after binding reads and stores',4),('wildcard branch/native control',2)],copies=[('selected (before,after)16 tuple -> destructuring binding',16,1)])['id'])
lr('L11',source='transition TP/TS/TC static union',note='LINKED subtotal charged once. All branch-specific rows remain reserved on every record; no inactive transition credit is reused.')['linked_groups']=groups(transition)
rows[-1]['groups']=groups(transition)
stage_atoms=[('next scalar base/index argument,bounds check/branch,address,load',6),('LE native argument/return and decode handling',3),('two Range endpoints and two field stores',4),('candidate native mutable reborrow',1),('range bounds comparisons and branch',4),('copy receiver/source native preparation and dispatch/return',3),('copy length equality/branch',2)]
stage_copies=[('destination Range16 -> IndexMut argument',16,1),('candidate slice16 -> IndexMut receiver',16,1),('IndexMut returned slice16 -> caller result',16,1),('caller destination slice16 -> copy receiver',16,1),('temporary LE array8 unsized slice16 -> copy source argument',16,1),('LE array8 -> candidate8 data',8,1)]
lr('L12',source='envelope.rs:200-211 twelve fixed candidate stores',atoms=stage_atoms,copies=stage_copies,repeat=12)
commit_atoms=[('four Range endpoints and four field stores',8),('two shared/mutable native reborrows',2),('two range bounds pairs and branches',8),('copy native preparation/dispatch/return',3),('copy length equality/branch',2)]
commit_copies=[('arena destination Range16 -> IndexMut argument',16,1),('candidate source Range16 -> Index argument',16,1),('arena slice16 -> IndexMut receiver',16,1),('candidate slice16 -> Index receiver',16,1),('IndexMut returned slice16 -> caller result',16,1),('Index returned slice16 -> caller result',16,1),('caller destination slice16 -> copy receiver',16,1),('caller source slice16 -> copy argument',16,1),('candidate8 -> arena8 data',8,1)]
lr('L13',source='envelope.rs:213-224 twelve fixed commit copies',atoms=commit_atoms,copies=commit_copies,repeat=12)
reply_row=row('RH01','reply','envelope.rs:99-100 complete fixed reply',atoms=[('eleven s[index] native indexed read primitives',66),('three native parameter reads (status,reason,debit)',3),('two zero literal reads',2),('sixteen scalar field stores in fresh words',16)],copies=[('words128 source -> Reply128 constructor',128,1),('Reply128 return -> leaf call result',128,1)])
poison_row=row('RH02','poison-reply','envelope.rs:102-103 complete fixed poison reply',atoms=[('fifteen literal source reads plus debit parameter read',16),('sixteen scalar field stores',16)],copies=[('words128 source -> Reply128 constructor',128,1),('Reply128 return -> caller result',128,1)])
lr('L14',source='all observe leaf returns; reply/poison helper and caller',atoms=[('four native call operands and four argument transfers',8),('call and return control',2)],copies=[('complete leaf Reply128 return -> walk received128',128,1)],note='Exactly one function return is possible; helper maximum RH01/RH02 is attached below. A caller source/destination for the same return is one edge, not two.')['helper_groups']=max(reply_row['groups'],poison_row['groups'])
rows[-1]['groups']+=max(reply_row['groups'],poison_row['groups'])
L=groups(leaf)
# Guard executes at most once. It shares source templates, not main prepaid credits.
guard_ids=['L01','L02','L03','L04','L14'];G=groups(guard_ids)
# Added record wrapper; unchanged loop/preflight/decode/record_fields/coordinate,
# including inherited Budget.replay invocation, stay bound to old framing22.
w=[]
def wr(id,source,atoms=(),copies=(),note=''):
 r=row(id,'wrapper-record',source,atoms,copies,note=note);w.append(id);return r
wr('W01','envelope.rs:313 cumulative debit',atoms=[('p native owner/member selection',1),('p.debit read, RECORD_ENVELOPE read,add,store',4)])
wr('W02','envelope.rs:318 and leaf_pending285-288',atoms=[('p native borrow argument/call/result/branch',5),('p.reply_valid read,zero literal,comparison,branch',4),('p.reply_valid read,one literal,comparison,shortcircuit branch',4),('p.reply.words[0] native indexed read with member selections',8),('three literal,compare,shortcircuit branch',3),('p.reply.words[1] native indexed read with member selections',8),('fifteen literal,comparison,if branch',3),('last p.reply.words[0] indexed read',8),('one literal,compare,boolean return',3)])
wr('W03','envelope.rs:319 immutable record construction',atoms=[('native w borrow,words field store,record binding store',3)])
wr('W04','envelope.rs:320 StepBudget construction',atoms=[('two native source reads and two scalar field stores',4)],copies=[('StepBudget16 constructor -> steps local',16,1)])
wr('W05','envelope.rs:321 leaf arguments; leaf return already in L14',atoms=[('arena Vec native borrow/member selection',2),('candidate native borrow+argument',2),('record native borrow+argument',2),('steps native borrow+argument',2),('call/return control',2)],copies=[('Vec-to-slice16 view result -> walk argument temporary',16,1),('slice16 temporary -> leaf arena argument',16,1)])
wr('W06','envelope.rs:322 install then validity',atoms=[('p.reply member destination selection',1),('one literal materialization and reply_valid store',2)],copies=[('received Reply128 -> p.reply128',128,1)])
wr('W07','envelope.rs:323 reply_debit_valid call/return and audit branch',atoms=[('p.reply native member borrow and argument transfer',3),('steps native borrow and argument transfer',2),('call/return control,result negation,if branch',4)])
normal=expr_row('DV01','debit-audit','envelope.rs:291','steps.remaining == 0 && steps.spent == RECORD_ENVELOPE && reply.words[13] == RECORD_ENVELOPE',[('normal-disjunct branch',1)])
# Array prefix reply.words has one member selection, manually primitive7.
# Scanner does not expand reply.words; replace this explicit row with full atoms.
normal['scalar_atoms']=[{'operation':'three field/native source reads remaining/spent/threshold and two zero/threshold operands','count':7},{'operation':'reply.words[13] native indexed read primitive plus one member selection','count':7},{'operation':'three comparisons,two conjunction branches,disjunct branch','count':6}]
normal['scalar_operations']=20;normal['scalar_groups']=2;normal['groups']=2
under=row('DV02','debit-audit','envelope.rs:292 guard disjunct',atoms=[('remaining/spent fields plus threshold/zero sources',4),('three reply.words indexed scalar reads, each primitive6 plus member selection1',21),('three RHS constant source reads',3),('five comparisons,four conjunction branches,boolean return',10)])
wr('W08','reply_debit_valid body DV01+DV02',note='LINKED static upper: both disjunct source rows are separately reserved; no normal/guard pooling.')['linked_groups']=normal['groups']+under['groups'];rows[-1]['groups']=normal['groups']+under['groups']
wr('W09','envelope.rs:323 audit failure poison construction+install',atoms=[('threshold read/native argument/call/return',4),('p.reply destination member selection',1)],copies=[('poison call result128 -> p.reply128',128,1)],note='RH02 helper source/return is separate below; error-path reserve always remains paid.')['helper_groups']=poison_row['groups'];rows[-1]['groups']+=poison_row['groups']
W=groups(w);B=22+L+W
# New fixed calls into old Budget implementation. They are newly repeated calls,
# so their cost is not hidden in inherited framing22. Explicit full-value Options.
row('BR01','budget-helper','analyzer.rs:166-168 Budget.replay',atoms=[('self/n native parameter receiving',2),('replay_left load,n read and two native arithmetic argument handoffs',4),('checked subtraction,overflow split,Option discriminator branch',3),('four eager error operands plus argument transfers',8),('error helper five stores,four native parameter reads,zero read',10),('ok_or discriminator/payload handoff and ? tag/branch',5),('replay_left store and replay_spent load,n read,addition,store',5),('Ok return/native control',1)],copies=[('checked_sub Option<u64>16 -> ok_or source temporary',16,1),('Option16 temporary -> ok_or self argument',16,1),('error32 helper return -> ok_or argument temporary',32,1),('error32 argument temporary -> ok_or error argument',32,1),('ok_or Result<u64,Error>40 -> ? temporary',40,1),('error32 ? payload -> propagated error temporary',32,1),('complete helper Result<(),Error>32 -> caller',32,1)])
row('BS01','budget-helper','analyzer.rs:170-172 Budget.setup excluding nested replay',atoms=[('self/n native parameter receiving',2),('setup_spent/n source reads plus arithmetic argument handoffs',4),('checked addition,overflow split',2),('Option tag/payload handoff,closure parameter,cap operand,comparison,closure return,if branch',7),('four error operands plus argument transfers',8),('error helper five stores,four parameter reads,zero read',10),('self native borrow,n native read+argument,call/return',5),('? tag/branch plus setup_spent load,n read,add,store and Ok control',7)],copies=[('checked_add Option16 -> is_none_or source temporary',16,1),('Option16 -> is_none_or self argument',16,1),('fixed error32 helper return -> Err payload temporary',32,1),('fixed error32 -> propagated Err payload',32,1),('nested replay error32 ? payload -> setup propagated error',32,1),('complete setup Result32 -> caller',32,1)])
row('BP01','budget-helper','analyzer.rs:178-180 Budget.report',atoms=[('self/n parameter receiving',2),('report_spent/n reads and arithmetic argument handoffs',4),('checked addition,overflow split',2),('Option tag/payload handoff,closure param,reserve operand,comparison,closure return,if branch',7),('four error operands plus argument transfers',8),('error helper five stores,four parameter reads,zero read',10),('report_spent read,n read,addition,store,Ok control',5)],copies=[('checked_add Option16 -> is_none_or temporary',16,1),('Option16 -> is_none_or self argument',16,1),('fixed error32 helper return -> Err payload temporary',32,1),('fixed error32 -> Err payload',32,1),('complete report Result32 -> caller',32,1)])
BR=groups(['BR01']);BS=groups(['BS01'])+BR;BP=groups(['BP01'])
# Candidate setup: historical534 is retained because this complete bound fits it.
setup=[]
def sr(id,source,atoms=(),copies=(),repeat=1,note=''):
 r=row(id,'envelope-setup',source,atoms,copies,repeat,note);setup.append(id);return r
sr('S01','envelope.rs:299-301 three new setup/report/guard calls',atoms=[('three native budget borrows,three n read/argument pairs,three call/return pairs',15),('three ? tag/branch tests',6),('two cumulative debit updates, each field read/constant/add/store',8)],copies=[('three possible returned Error32 payloads -> walk Err temporaries',32,3),('walk Result32 -> observe_inputs caller on setup failure',32,1)],note=f'LINKED new Budget bodies setup{BS}+report{BP}+guard-report{BP} attached below; only one failure can return.')['helper_groups']=BS+2*BP;rows[-1]['groups']+=BS+2*BP
sr('S02','envelope.rs:302 Candidate2048 literal initialization',atoms=[('zero literal source plus2048 scalar byte stores',2049)],copies=[('candidate literal source2048 -> retained candidate destination, sixteen disjoint fixed128 chunks',128,16)],note='Unlike old source-level illustrative256+256 schedule, this actual bound counts each byte zero store, then every full literal/destination transfer once. No compiler elision or per-record reinitialization assumed.')
sr('S03','envelope.rs:304 length check/error path',atoms=[('arena member/native length call/return,equality operands,compare,if branch',7),('four error operands+arguments',8),('error helper five stores,four parameter reads,zero read',10)],copies=[('Error32 helper -> error temporary',32,1),('Error32 temporary -> Err payload',32,1),('walk Result32 -> input caller',32,1)])
sr('S04','envelope.rs:305 for0..12 loop setup',atoms=[('two endpoints and two Range field stores',4)],copies=[('Range16 constructor -> iterator source',16,1),('Range16 -> IntoIterator argument',16,1),('Range16 IntoIterator return -> retained iterator',16,1)])
sr('S05','envelope.rs:305 for loop next/condition/body handoff',atoms=[('native iterator receiver/argument/call',3),('start/end loads,compare,branch,increment,store,return control',7),('Option tag/payload/native i binding and branch/backedge',5)],copies=[('next Option<usize>16 -> caller match temporary',16,1)],repeat=13,note='Twelve Some plus final None are charged; each listed operation is reserved even on final terminating next.')
sr('S06','envelope.rs:306-308 selected-cell initializer body',atoms=[('i source/constants/comparisons/two branches and three alternative result operands/bind',11),('f.mask native field load for selected cell',1),('SCALAR.base source plus CELLS[i] indexed read primitive6,multiplier source,multiply,add,at binding',11),('at source and8source,addition plus Range endpoint field stores',5),('value native source,LE argument/return/decode',4),('Vec/member native reborrow',2),('range bound comparisons/branches,copy equality/branch,call/return',8)],copies=stage_copies,repeat=12,note='Same six IndexMut/Range/slice/data transfer template as L12, with runtime at bookkeeping named here. Constant f.mask branch is charged even when zero initialization applies.')
setup_actual=groups(setup)
# Wrapper setup T: two new outer reservation calls and new retained Progress.
t=[]
def tr(id,source,atoms=(),copies=(),note=''):
 r=row(id,'wrapper-setup',source,atoms,copies,note=note);t.append(id);return r
tr('T01','envelope.rs:361 setup(T),report(F) new reservation call/control',atoms=[('two native budget borrows,n read+argument and call/return groups',10),('two ? tag and branch operations',4)],copies=[('each possible Error32 ? payload -> outer Err temporary',32,2),('core Error32 Err payload -> Result232 return split128+104',128,1),('core Error32 Err payload -> Result232 second104',104,1),('core Result232 -> public Result232 chunk128',128,1),('core Result232 -> public Result232 chunk104',104,1),('public Result232 -> external caller chunk128',128,1),('public Result232 -> external caller chunk104',104,1)],note='LINKED Budget setup/report bodies attached; failure returns no aggregate. The fixed complete Result232 transfers reserve both chunks even for Err.')['helper_groups']=BS+BP;rows[-1]['groups']+=BS+BP
tr('T02','envelope.rs:365 Progress absent backing initializer',atoms=[('zero source and sixteen words zero element stores',17),('reply_valid/debit zero reads and scalar stores',4)],copies=[('words128 literal -> Reply128 backing field',128,1),('Progress144 constructor -> retained p first128',128,1),('Progress144 constructor -> retained p remaining16',16,1)],note='Zero backing is never Observed; no reply_valid1 store here.')
tr('T03','envelope.rs:366,347,353,295 added progress borrowing chain',atoms=[('three p native borrow/argument receiving pairs',6),('three corresponding native parameter local bindings',3)])
T=groups(t)
# COMPLETE finish E: propose replacing historical8, avoiding an opaque assignment
# of private finalizer overflow to wrapper F. Rows remain source-separated.
finish=[]
def fr(id,source,atoms=(),copies=(),note=''):
 r=row(id,'envelope-finish',source,atoms,copies,note=note);finish.append(id);return r
fr('E01','envelope.rs:375,253 finalizer argument/entry and returned input-error branch256-258',atoms=[('four native argument borrows/receiving plus call/return control',10),('input Result borrow/discriminant/match/error-payload native reference',4),('e.code loads twice,two code operands,two comparisons,two branches',8),('fixed reason binding and project native arguments/call/return',8)])
expr_row('EF02','finish-expression','envelope.rs:260','s.flags > 1 || !((s.complete && !s.limited) || (s.limited && !s.complete))',[('two borrowed Result<bool> discriminant checks,two bool payload reads and success comparisons',8),('if dispatch',1)])
fr('E02','envelope.rs:260-264 complete/limited/input eligibility,absent/unsupported Progress',atoms=[('EF02 eligibility expression linked atoms',next(r['scalar_operations'] for r in rows if r['id']=='EF02')),('p.reply_valid twice: native member loads,two constants,two comparisons,two branches',8)])
fr('E03','envelope.rs:266-267 poison-first dispatch',atoms=expr_atoms('p.reply.words[0] == 3 || p.reply.words[1] == 15')+[('if branch; limited field read/conditional branch; two boundary literal operands',5)])
expr_row('EF04','finish-expression','envelope.rs:269-272 state/status support','p.reply.words[0] < 1 || p.reply.words[0] > 2 || p.reply.words[1] > 14 || (p.reply.words[0] == 1 && p.reply.words[1] != 0) || (p.reply.words[0] == 2 && p.reply.words[1] == 0) || p.reply.words[3] > 10 || p.reply.words[4] > 5 || p.reply.words[5] >= 64 || p.reply.words[9] > 1 || p.reply.words[10] > 1',[('if dispatch',1)])
fr('E04','envelope.rs:269-274 actual RangeInclusive support predicate',atoms=[('EF04 scalar predicate upper including two tests for contains',next(r['scalar_operations'] for r in rows if r['id']=='EF04')),('actual RangeInclusive1..=2 constructor three fields and two literal sources',5),('actual range receiver/native reference,word native reference,contains call/return,negation',6)],copies=[('RangeInclusive<u64>24 constructor -> contains receiver temporary',24,1)],note='EF04 replaces the scalar part of actual contains with both comparisons, then also pays actual range constructor/borrow. This conservatively duplicates scalar support comparisons, explicitly named and never reused.')
fr('E05','envelope.rs:275-279 limited/refused/CAP dispatch and fixed reason call',atoms=[('limited field load and branch',2),('two p.reply.words[0] indexed reads with nested member selections',16),('two kind2 constants/comparisons/branches',6),('s.flags native read,one literal,compare,branch',4),('p.reply.words[1] indexed reason read and native argument/call/return handoff',11)])
reason=row('EH01','finish-helper','envelope.rs:228-239 reason_from_leaf',atoms=[('sixteen possible discriminator tests: input read,literal operand,comparison,branch',64),('selected enum native materialization and return control',2)])
fr('E06','envelope.rs:275-278 optional reason conversion EH01',note='Exactly one reason_from_leaf call can execute; reserve its complete maximum regardless of branch.')['helper_groups']=reason['groups'];rows[-1]['groups']=reason['groups']
word=row('EH02','finish-helper','envelope.rs:92-97 word_at checked tail/first_chunk',atoms=[('native bytes/offset parameter receiving',2),('offset read and RangeFrom scalar field store',2),('get native argument/index bounds compare/branch/Option tag handling',6),('tail native binding,first_chunk native receiver/argument,8literal,range length compare/branch,Option tag/native array binding',9),('array8 source read,LE native argument/decode/return',4),('status/value source reads and two Pair field stores',4),('two fixed failure Pair zero values plus fields and return control',5)],copies=[('slice16 argument -> get receiver',16,1),('get Option<&[u8]>16 return -> caller match',16,1),('Some tail slice16 -> tail binding',16,1),('tail slice16 -> first_chunk receiver',16,1),('complete Pair16 constructor -> function return/caller',16,1)],note='RangeFrom<usize> and Option<&[u8;8]> are native8 values. Pair16/slice16/Option-slice16 transfers use separate whole-copy units. Source byte array8->LE argument is one native8 operation, not sixteen assumed CPU loads.')
fr('E07','envelope.rs:280 word_at call/helper',atoms=[('Vec/member native receiver and coercion source preparation',2),('SCALAR.base read,CELLS[6] primitive read6,8source,multiply,add',10),('offset native argument,call/return control',3)],copies=[('Vec-to-slice16 view -> word_at argument',16,1)],note='EH02 attached below; Pair return already EH02, not a second receiving copy.')['helper_groups']=word['groups'];rows[-1]['groups']+=word['groups']
fr('E08','envelope.rs:281-283 closed boundary check',atoms=[('expected.status native read,one literal,compare,branch',4)]+expr_atoms('p.reply.words[3] == 0 && p.reply.words[4] == 5 && p.reply.words[5] == expected.value')+[('if/else dispatch',1)])
projection=row('EH03','finish-helper','envelope.rs:241-251 full projection',atoms=[('p.reply.words native fixed-array borrow binding',3),('eleven extent source reads and conditional branches',22),('eleven true indexed scalar reads primitive6',66),('eleven false zero source materializations',11),('sixteen scalar destination field stores',16),('boundary/reason/debit native source reads plus two authority zero reads',5)],copies=[('Observation128 constructor -> project return/caller',128,1)],note='Both alternatives in each conditional are explicitly reserved, never shared with other fields. No heap/error text or public arbitrary verified input.')
fr('E09','all mutually exclusive finalize->project calls',atoms=[('four native argument preparations/transfers',8),('call and return control',2)],note='Exactly one project executes because every preceding branch returns. EH03 attached once, separate from other helper returns.')['helper_groups']=projection['groups'];rows[-1]['groups']+=projection['groups']
fr('E10','finalize return into core envelope local',copies=[('complete Observation128 finalize return -> core envelope',128,1)])
E=groups(finish)
# Remaining fixed public wrapper F: baseline original outcome/report work stays
# original accepted scope; changed complete aggregate/error returns are separate.
f=[]
def ff(id,source,atoms=(),copies=(),note=''):
 r=row(id,'wrapper-final',source,atoms,copies,note=note);f.append(id);return r
ff('F01','envelope.rs:379,383-384 complete aggregate and success Result moves',atoms=[('core/public function native File parameter receiving and argument transfers',8),('public STEP_LIMIT read/argument and call/return control',4),('aggregate/Ok constructor and return control',3)],copies=[('ReplayOutcome104 -> aggregate framing field',104,1),('Observation128 -> aggregate envelope field',128,1),('Outcome232 constructor -> Ok Result232 chunk128',128,1),('Outcome232 constructor -> Ok Result232 chunk104',104,1),('core Result232 -> public Result232 chunk128',128,1),('core Result232 -> public Result232 chunk104',104,1),('public Result232 -> external caller chunk128',128,1),('public Result232 -> external caller chunk104',104,1)])
ff('F02','envelope.rs:362-366 inherited fixed calls changed aggregate error destination',atoms=[('four inherited ? receiving tests native tag/control (Budget.new,output_safety,Arena,new reservations)',8)],copies=[('four possible Error32 ? payloads -> outer aggregate Err temporary',32,4),('core Err complete Result232 -> public chunk128',128,1),('core Err complete Result232 -> public chunk104',104,1),('public Err Result232 -> caller chunk128',128,1),('public Err Result232 -> caller chunk104',104,1)],note='Error alternatives are explicitly reserved separately from success return; none can upgrade input/framing observation.')
ff('F03','envelope.rs:366,347,353 changed internal call Result/error propagation',atoms=[('two renamed calls retain baseline parameter handling; added p control/borrow is T03',0),('three fixed Result discriminant/native return handling operations',3)],copies=[('walk Result<(),Error>32 -> observe_inputs receiving',32,1),('observe_inputs Result<bool,Error>40 -> core result local',40,1)],note='Conservative full changed caller return edges added explicitly, although underlying pre-existing framing already has equivalent source. No baseline22 transfer removed.')
ff('F04','envelope.rs:377-378 output failure changed Result232 returns',atoms=[('write_report returned Result tag/branch; budget.used call/return/limit load/compare/branch',8),('error(BUDGET) native arguments and helper field stores',18)],copies=[('write_report Error32 ? payload -> core Err payload',32,1),('error32 helper -> budget Err payload',32,1),('core Result232 error return chunk128',128,1),('core Result232 error return chunk104',104,1),('public Result232 error return chunk128',128,1),('public Result232 error return chunk104',104,1)],note='Outer Err always carries no aggregate; these error source rows remain reserved even on success.')
F=groups(f)
# Address/lifetime table is actual typed source storage, not physical stack/RSS.
starts=[7729816,7729832,7729840,7729848,7729856,7729864,7729872,7730272,7730280,7730288,7731040,7731048]
sourcehash=sha(S)
summary={'schema':1,'status':'unselected-strict-source-operation-upper-bound-proposal-no-replay','source_sha256':sourcehash,'analyzer_sha256':sha(A),'historical_unqualified':{'leaf':128,'W':42,'B':192,'G':36,'T':20,'finish':8,'F':44,'leaf_authored111_rejected':True},'proposed':{'leaf':L,'W':W,'B':B,'G':G,'T':T,'finish':E,'F':F,'setup_selected':534,'setup_actual_bound':setup_actual},'leaf_upper_minus_current128':L-128,'leaf_upper_is_not_minimal_lower_bound':True,'selection_changes_require_root':True,'public_formula':f'534*S+{E}*F+{L}*N','public_formula_S':'main setup534 reservation succeeded','public_formula_F':'proposed complete finish reservation succeeded','public_formula_N':'main B reservation succeeded, even if subsequent framing/read fails or leaf latches','zero_leaf_complete_or_limited':{'reply_valid':0,'boundary':'Unavailable','reason':'EnvelopeUnavailable','all_extent_fields':0,'debit_if_setup_and_finish_paid':534+E},'main_cumulative_debit_on_private_guard':L,'private_guard_debit':0,'refunds':False,'limits':{'step':268435456,'setup':65536,'report':3000000,'IO':263584,'preflight':8192,'arena':8388608,'transient':65536,'reserved_transient':41984},'feasibility':{'B_le_preflight':B<=8192,'setup_actual_le_534':setup_actual<=534,'outer_T_plus_envelope534_le_setupcap':T+534<=65536,'finish_plus_G_plus_F_le_reportreserve':E+G+F<=3000000,'preflight_margin':8192-B,'fixed_new_report_reservation':E+G+F,'no_full_cap_prefix_promised':True},'meaning':'Conservative caller-visible Rust operation bound. Not CPU, compiler lowering, native performance, semantic replay, binding or release authority. Numeric values require independent audit and explicit root selection before source constant change or cost-dependent replay.'}
assert setup_actual<=534
# Total setup budget profile baseline: old setup cap remains enforced atomically;
# this arithmetic does not invent available capacity for IO/drain/profile paths.
summary['feasibility']['remaining_setupcap_after_new_outer_T_and_leaf534']=65536-T-534
summary['feasibility']['remaining_reportreserve_after_new_fixed']=3000000-E-G-F
summary['feasibility']['steps_before_records_lower_bound']=1048576+640000+T+534+E+G+F
summary['feasibility']['arithmetic_record_upper_ignoring_other_existing_costs']=(268435456-summary['feasibility']['steps_before_records_lower_bound'])//B
summary['feasibility']['arithmetic_record_upper_note']='Only a coarse upper capacity, NOT a guaranteed observed prefix: unchanged profile/setup/IO/report/drain calls still consume their original reserves and mandatory8192 preflight remains. No selected32155 or full4,194,304 capacity.'
write('operation-ledger.json',{'schema':1,'source_sha256':sourcehash,'status':'proposed-requires-independent-source-audit','group_rule':'<=16 named bounded scalar operations OR one actual source-level transfer/copy<=128B per group; each block rounds independently; no reuse/refund/hiddenpadding','counting_primitives':{'indexed_u64_read':'native base/borrow1,index argument1,bounds compare1,bounds branch1,address/native reference return1,scalar load1; additional explicit nested member selections separately','indexed_u64_write':'native base/borrow1,index argument1,bounds compare1,bounds branch1,address/native reference return1,scalar store1','native_argument':'one explicit native operand read and one source->parameter transfer unless already in primitive; native8 values are scalar operations','whole_value_copy':'one per actual source-level transfer edge for16+ byte handles/aggregates or actual fixed data copy. Edge source and destination do not count twice. Larger aggregate transfer split into disjoint<=128B pieces. No compiler scalarization/elision assumption.','standard_primitives':'Caller-visible Rust Index/IndexMut/copy_from_slice/checked arithmetic operations; no claim about standard library machine instructions or memcpy internals. Bounds/equality/control counted separately from fixed copy.','expression_occurrence_inventory':'Review aid over explicitly selected source expressions, not source authorization or a substitute for independent audit. Every selected expression and atom emitted.','static_branch_unions':'Some transition/error blocks reserve every named alternative, each once, to form a deliberately conservative upper; unused alternative groups are not reused by other work. Single-return/match maxima have explicit one-execution invariants.'},'rows':rows,'charge_composition':{'leaf_rows':leaf,'leaf_total':L,'guard_shared_rows':guard_ids,'guard_total':G,'wrapper_record_rows':w,'wrapper_record_total':W,'setup_rows':setup,'setup_actual_bound':setup_actual,'wrapper_setup_rows':t,'wrapper_setup_total':T,'finish_rows':finish,'finish_total':E,'wrapper_final_rows':f,'wrapper_final_total':F,'budget_helper_setup_total':BS,'budget_helper_report_total':BP,'budget_helper_replay_total':BR},'no_nested_doublecharge':'linked_groups/helper_groups are attached to parent row once; child rows are explanatory and not charged again in composition totals. Leaf return->received lives only in L14. received->Progress is W06. Guard shares source templates but uses its separate reserve, never L prepaid credits.'})
write('numeric-proposal.json',summary)
write('ranges-and-lifetimes.json',{'schema':1,'source_sha256':sourcehash,'ranges':[{'cell':c,'start':v,'end':v+8,'candidate_start':888+8*i,'candidate_end':896+8*i}for i,(c,v)in enumerate(zip([7,9,10,11,12,13,14,64,65,66,160,161],starts))],'checks':['arena.len>=7731056 occurs before all reads/staging/semantic writes','one exclusive arena slice remains identical with unchanged length through commit','no allocator/I/O/callback/Vec mutation or alias escapes in leaf','Candidate2048 sized owner proves fixed888..984 destinations before staging','all source/destination intervals are8bytes, disjoint within each role','word8 initialized once per leaf, reused twelve times; prior96 and next96 bounded locals','private record is thin immutable borrow of framing-owned w128; never public arbitraryword constructor','all borrowed input/candidate/steps views end at reply return before next record/finalize','new word8 temporary consumes existing fixed helper-local lease; no new retained owner','Progress reply_valid stays0 throughcandidate/cell initialization, becomes1 only after complete received reply is installed','retained poison status3 OR reason15 suppresses every later leaf call; firstStepsRefused likewise stops leaf','underfunded guard uses no arena/candidate mutation, returns prior-state debit0; paid main leaf subdivision remains reserved'], 'actual_known_layouts_historical_probe_not_new_measurement':{'Reply':128,'Progress':144,'Observation':128,'Outcome':232,'ResultOutcome':232,'StepBudget':16,'Pair':16,'decodedborrow':8,'word':8,'slice':16,'Range':16,'RangeInclusiveU64':24,'OptionSlice':16,'OptionArrayBorrow':8,'arrayborrow':8,'Metadata':144,'Stamp':72,'AnalyzerError':32,'ReplayOutcome':104},'fresh_layout_execution_pending':True,'memory_caps_unchanged':{'arena':8388608,'transient':65536,'transient_reservation':41984},'source_scope_no_new_owner':'Same retained candidate2048, existingframing/Reader/metadata/Stamp/report owners.12Pair prior loop removed; local word8 is leased within prior approved helper scratch. No real binding/semanticmetric/report authority.'})
# Snapshot all proposal dependencies before review. Do not snapshot a mutable
# parent receipt or execute collectors from the old producer.
for p in [S,A,P/'tests/correction_tests.rs',P/'tests/envelope_tests.rs',Path(__file__).resolve()]:
 dest=D/('source-'+p.name);shutil.copy2(p,dest)
for p in sorted((P/'inputs').glob('root-*.json')):shutil.copy2(p,D/p.name)
write('scope.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'correction proposal only; no cost-dependent Rust/Python replay and no constant selection','root':str(P),'source_files':['src/analyzer.rs','src/envelope.rs'],'new_regression_test_methods':2,'old_envelope_tests_retained_exact':sha(P/'tests/envelope_tests.rs')==sha(P.parent/'swift-ordered-retention-analyzer-envelope/tests/envelope_tests.rs'),'pending':['independent numeric/source audit','explicit root cost-contract selection','fresh actual Rust layout probes','meaningful R1/overflow tests','full44+20+2 separate producer replay and finite oracle validation','upstream byte preservation and cleanup receipt'],'no_native_or_UI_or_capture_or_device_or_process_discovery':True,'no_product_engine_CLI_custody_semantic_or_release_authority':True})
write('manifest.json',{'schema':1,'members':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(D.iterdir())if p.is_file()and p.name not in ('manifest.json','receipt.json')]})
write('receipt.json',{'schema':1,'status':'immutable-operation-proposal-1-awaiting-independent-review','manifest_sha256':sha(D/'manifest.json'),'source_sha256':sourcehash,'numeric_proposal_sha256':sha(D/'numeric-proposal.json'),'ledger_sha256':sha(D/'operation-ledger.json'),'constants_selected':False,'cost_dependent_replay_run':False,'counts':{'rows':len(rows),'members_excluding_manifest_receipt':len(json.loads((D/'manifest.json').read_text())['members'])}})
print(json.dumps({'receipt':json.loads((D/'receipt.json').read_text()),'proposed':summary['proposed'],'shortfall_upper':L-128,'feasibility':summary['feasibility']},indent=2))
