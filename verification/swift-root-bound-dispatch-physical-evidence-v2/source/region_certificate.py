"""Finite saved-artifact certificate mechanics, never a capacity or policy grant.

This does not decode LLVM/assembly semantics. Actual local geometry requires a
trusted invocation digest of root's approval of the exact independently reviewed
map and accepted capture/diagnostic custody. Input labels cannot approve a map.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

U64=(1<<64)-1
I64_MIN=-(1<<63)
I64_MAX=(1<<63)-1
MAX_FILES=192
MAX_TOTAL=320*1024*1024
MAX_JSON=2*1024*1024
TARGETS=('Caller','Closure','Dispatch','Body')
PHASES=('body_active','body_returned','action_returned','child_wrapped','caller_returned')
SOURCE_PREFIX='verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm/'
SOURCE_ROOT='/Users/andreyyurlov/Documents/dev/mixer/'+SOURCE_PREFIX.rstrip('/')
CURRENT_BINDING={
    'source_tree':'91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'compiler_commit':'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4','target':'aarch64-apple-darwin',
    'features':['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache'],
    'fixture_cfg':'mixer_bootstrap_one_fixture_v1','opt_level':0,'mir_opt_level':0,
    'overflow_checks':True,'panic':'unwind','codegen_units':1,'debuginfo':2,
    'capture_plan_sha256':'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184',
    'argv_sha256':'4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa',
}
FRONTIER_SHA='3a4138c82c8b370e8f844ddff10218e6465dd5ba006f3fe3c072e62c8c26f76a'
WARNINGS=(
    ('unused_imports','unused import: `OwnedCorrelationOutcomeV1`'),
    ('unused_imports','unused imports: `BorrowedOwnerDataV1` and `selected_bootstrap_ledger_v1`'),
    ('deprecated','use of deprecated method `std::sync::atomic::Atomic::<u64>::fetch_update`: renamed to `try_update` for consistency'),
)
REQUIRED_BLOBS={'ir','asm','stdout','stderr','source_manifest','frontier','mir','capture_observation',
    'capture_acceptance','diagnostic_policy','semantic_review','independent_seal'}
PARTITIONS=('acquisition_operation','acquisition_cleanup','acquisition_storage','P0','C0','C1','C2','C3','C4','C5')
CHILD_BACKINGS=tuple('file'+str(i) for i in range(5))+('executable','proof','error','cancellation','claims')
BACKINGS=('acquisition_inputs','acquisition_paths','p0_binding')+CHILD_BACKINGS
ROLES={'R':('Body',13624),'C':('Dispatch',13640),'O':('Caller',13640),
    'FCaller':('Caller',None),'FClosure':('Closure',None),'FDispatch':('Dispatch',None),'FBody':('Body',None)}
REQUIREMENTS={
    'carrier_setup':('R',(1,2)),'carrier_loaded':('R',(1,2)),
    'child':('C',(3,)),'outer':('O',(4,)),
    'caller_frame':('FCaller',(0,1,2,3,4)),'closure_frame':('FClosure',(0,1)),
    'dispatch_frame':('FDispatch',(0,1,2,3)),'body_frame':('FBody',(0,1)),
}

class Refusal(Exception):
    pass

class ArtifactBytes(dict):
    def __init__(self,values):super().__init__(values);self.span_bytes_remaining=512*1024*1024
    def reserve_span(self,size):
        need(size<=16*1024*1024 and size<=self.span_bytes_remaining,'aggregate evidence hash bound')
        self.span_bytes_remaining-=size

def need(condition,reason):
    if not condition:raise Refusal(reason)

def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def same(left,right):return canonical(left)==canonical(right)
def integer(value,low=0,high=U64):
    need(type(value) is int and low<=value<=high,'integer or unit range');return value
def text(value,maximum=1024):
    need(type(value) is str and 0<len(value)<=maximum,'text range');return value
def boolean(value):need(type(value) is bool,'boolean type');return value
def sha(value):
    need(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'sha256');return value
def obj(value,fields):
    need(type(value) is dict and set(value)==set(fields.split()),'closed object fields');return value
def sequence(value,maximum=128):need(type(value) is list and len(value)<=maximum,'list bound');return value
def checked_add(left,right,low=0,high=U64):return integer(left+right,low,high)
def unique(pairs):
    result={}
    for key,value in pairs:
        need(key not in result,'duplicate JSON key');result[key]=value
    return result
def strict(raw):
    need(type(raw) is bytes and len(raw)<=MAX_JSON,'JSON byte bound')
    try:return json.loads(raw.decode('utf-8'),object_pairs_hook=unique,
        parse_constant=lambda _:(_ for _ in ()).throw(Refusal('nonfinite JSON')))
    except (ValueError,UnicodeError,RecursionError) as error:raise Refusal('invalid JSON') from error
def relative(value):
    text(value,512);need('\\' not in value and ':' not in value and not value.startswith('/'),'relative path')
    need(all(part not in ('','.','..') for part in value.split('/')),'relative path component');return value
def pin(name,raw):return {'name':name,'bytes':len(raw),'sha256':digest(raw)}
def pins(blobs):return [pin(name,blobs[name]) for name in sorted(blobs)]
def validate_pins(rows):
    found={};total=0
    for item in sequence(rows,MAX_FILES):
        obj(item,'name bytes sha256');name=relative(item['name']);need(name not in found,'duplicate member')
        need(not any(name.startswith(old+'/') or old.startswith(name+'/') for old in found),'path/member collision')
        size=integer(item['bytes'],0,MAX_TOTAL);sha(item['sha256']);total=checked_add(total,size,0,MAX_TOTAL);found[name]=item
    need(bool(found),'empty input pin set');return found

@dataclass(frozen=True)
class Invocation:
    """This argument comes from the root-released command, outside all input data."""
    expected_approval_sha256: str|None
    synthetic: bool=False

class FilesystemInputs:
    """Read only named regular files below an explicit root, with no symlink walk."""
    def __init__(self,root):
        self.root=Path(root);need(self.root.is_absolute(),'absolute explicit input root')
    def _read(self,name,limit):
        parts=relative(name).split('/');directory=None;leaf=None
        try:
            directory=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            for part in parts[:-1]:
                child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                os.close(directory);directory=child
            leaf=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
            before=os.fstat(leaf);need(stat.S_ISREG(before.st_mode) and before.st_size<=limit,'regular file prehash size bound')
            pieces=[];remaining=limit
            while remaining:
                chunk=os.read(leaf,min(262144,remaining))
                if not chunk:break
                pieces.append(chunk);remaining-=len(chunk)
            after=os.fstat(leaf)
            identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            need(identity(before)==identity(after),'file changed while reading')
            return b''.join(pieces),identity(after)
        except OSError as error:raise Refusal('input file custody') from error
        finally:
            if leaf is not None:os.close(leaf)
            if directory is not None:os.close(directory)
    def snapshot(self,name,maximum):
        raw,identity=self._read(name,maximum+1)
        need(len(raw)<=maximum,'snapshot byte bound');return (len(raw),digest(raw),identity)
    def read(self,name,limit):return self._read(name,limit)[0]

def read_saved(port,expected):
    """Bound before hashing; hash the actual memory bytes, then recheck every path."""
    rows=validate_pins(expected);blobs={};before={}
    for name,item in rows.items():
        before[name]=port.snapshot(name,item['bytes'])
        need(before[name][:2]==(item['bytes'],item['sha256']),'pre-read path pin')
        raw=port.read(name,item['bytes']+1)
        need(type(raw) is bytes and len(raw)==item['bytes'] and digest(raw)==item['sha256'],'in-memory byte pin')
        blobs[name]=raw
    for name,item in rows.items():need(port.snapshot(name,item['bytes'])==before[name],'post-read path pin')
    return blobs

def anchor(value,blobs):
    obj(value,'artifact begin end sha256');name=value['artifact'];need(name in ('ir','asm'),'anchor artifact')
    begin=integer(value['begin'],0,len(blobs[name]));end=integer(value['end'],0,len(blobs[name]))
    need(begin<end,'empty or reversed artifact span')
    need(type(blobs) is ArtifactBytes,'internal artifact budget');blobs.reserve_span(end-begin)
    need(digest(blobs[name][begin:end])==sha(value['sha256']),'artifact span pin')
    return (name,begin,end,value['sha256'])
def anchors(values,blobs):
    result=[anchor(value,blobs) for value in sequence(values,64)]
    need(result and len(set(result))==len(result),'empty or duplicate evidence spans');return result
def inside(child,parent):return child[0]==parent[0] and parent[1]<=child[1]<child[2]<=parent[2]

def source_binding(blobs,frontier,binding,synthetic):
    if synthetic:obj(frontier,'targets')
    manifest=obj(strict(blobs['source_manifest']),'schema changed member_count members new_distribution_members tree_sha256')
    need(manifest['schema']==1 and type(manifest['schema']) is int,'source schema')
    need(integer(manifest['new_distribution_members'])==0,'new source distribution member')
    changed=sequence(manifest['changed'],146)
    need(all(type(name) is str for name in changed) and len(set(changed))==len(changed),'source changed roster')
    members=sequence(manifest['members'],146);need(integer(manifest['member_count'],1,146)==len(members),'source member count')
    need(digest(canonical(members))==manifest['tree_sha256']==binding['source_tree'],'source tree pin')
    names=set()
    for member in members:
        obj(member,'path bytes sha256');name='source/'+relative(member['path']);need(name not in names,'source collision');names.add(name)
        integer(member['bytes'],0,MAX_TOTAL);sha(member['sha256'])
        need(name in blobs and pin(name,blobs[name])=={'name':name,'bytes':member['bytes'],'sha256':member['sha256']},'source memory pin')
    need(set(blobs)==REQUIRED_BLOBS|names,'unknown or missing bundle input')
    if not synthetic:need(len(members)==146 and digest(blobs['frontier'])==FRONTIER_SHA,'actual frontier pin')
    rows={}
    for target in sequence(frontier['targets'],4):
        if synthetic:obj(target,'id source retained_MIR')
        identity=target['id'];need(identity in TARGETS and identity not in rows,'frontier target identity');rows[identity]=target
        for scope,blob in [(target['source'],None),(target['retained_MIR'],'mir')]:
            if synthetic:obj(scope,'file byte_begin byte_end span_sha256')
            file=scope['file']
            obj(file,'path bytes sha256')
            integer(file['bytes'],0,MAX_TOTAL);sha(file['sha256']);text(file['path'],1024)
            if blob is None:
                need(file['path'].startswith(SOURCE_PREFIX),'frontier source prefix');blob='source/'+relative(file['path'][len(SOURCE_PREFIX):])
            need(blob in blobs and file['bytes']==len(blobs[blob]) and file['sha256']==digest(blobs[blob]),'frontier file pin')
            begin=integer(scope['byte_begin'],0,len(blobs[blob]));end=integer(scope['byte_end'],0,len(blobs[blob]))
            need(begin<end and digest(blobs[blob][begin:end])==scope['span_sha256'],'frontier scope pin')
    need(set(rows)==set(TARGETS),'incomplete frontier')
    return rows

def diagnostic_spans(record,blobs):
    stack=[record];nodes=0
    while stack:
        node=stack.pop();nodes+=1;need(nodes<=256 and type(node) is dict,'diagnostic tree bound')
        for span in sequence(node.get('spans',[]),64):
            need(type(span) is dict and type(span.get('file_name')) is str,'diagnostic span schema')
            file=span['file_name'];need(file.startswith(SOURCE_ROOT+'/'),'diagnostic source root')
            name='source/'+relative(file[len(SOURCE_ROOT)+1:]);need(name in blobs,'diagnostic source member')
            raw=blobs[name];begin=integer(span['byte_start'],0,len(raw));end=integer(span['byte_end'],0,len(raw));need(begin<=end,'diagnostic source range')
            lines=raw.splitlines();first=integer(span['line_start'],1,len(lines));last=integer(span['line_end'],first,len(lines))
            need(first==raw[:begin].count(b'\n')+1 and last==raw[:end].count(b'\n')+1,'diagnostic source line')
            for item,line in zip(sequence(span['text'],64),lines[first-1:last]):need(item['text']==line.decode('utf-8'),'diagnostic source text')
            need(len(span['text'])==last-first+1,'diagnostic source text length')
        stack.extend(sequence(node.get('children',[]),64))

def capture_custody(blobs,binding):
    policy=obj(strict(blobs['diagnostic_policy']),'schema status source_tree records')
    need(type(policy['schema']) is int and policy['schema']==1 and policy['status']=='frozen-exact-source-bound-baseline-diagnostics' and policy['source_tree']==binding['source_tree'],'diagnostic policy')
    records=sequence(policy['records'],4);need(len(records)==4,'whole diagnostic stream')
    need(len(blobs['stdout'])==0,'unexpected compiler stdout')
    need(len(blobs['stderr'])<=2*1024*1024,'stderr bound')
    actual=[strict(line) for line in blobs['stderr'].splitlines()]
    need(same(actual,records),'exact diagnostic stream')
    for record,(code,message) in zip(records[:3],WARNINGS):
        need(type(record) is dict and type(record.get('code')) is dict,'warning record type')
        need(record.get('level')=='warning' and record.get('message')==message and record['code'].get('code')==code,'baseline warning identity')
        diagnostic_spans(record,blobs)
    need(type(records[3]) is dict and records[3].get('message')=='3 warnings emitted' and records[3].get('code') is None and records[3].get('level')=='warning','exact successful warning summary')
    output_pins=[pin(name,blobs[name]) for name in ('ir','asm','stdout','stderr')]
    observation=obj(strict(blobs['capture_observation']),'schema status binding compiler_exit outputs source_manifest_sha256 owned_groups_closed cleanup_complete bounds_met truncated capture_complete')
    need(same(observation,{'schema':1,'status':'captured-artifacts-only','binding':binding,'compiler_exit':0,'outputs':output_pins,
        'source_manifest_sha256':digest(blobs['source_manifest']),'owned_groups_closed':True,'cleanup_complete':True,'bounds_met':True,'truncated':False,'capture_complete':True}),'accepted capture observation')
    acceptance=obj(strict(blobs['capture_acceptance']),'schema status observation_sha256 diagnostic_policy_sha256 source_manifest_sha256 binding_sha256 outputs local_geometry_only complete_capacity_accepted')
    need(same(acceptance,{'schema':1,'status':'accepted-capture-custody-only','observation_sha256':digest(blobs['capture_observation']),
        'diagnostic_policy_sha256':digest(blobs['diagnostic_policy']),'source_manifest_sha256':digest(blobs['source_manifest']),
        'binding_sha256':digest(canonical(binding)),'outputs':output_pins,'local_geometry_only':True,'complete_capacity_accepted':False}),'capture acceptance join')
    need(len(blobs['ir'])+len(blobs['asm'])<=256*1024*1024,'generated artifact bound')

def approve(certificate,blobs,approval_raw,invocation):
    if invocation.expected_approval_sha256 is None:
        need(approval_raw is None,'untrusted approval supplied');return False
    expected=sha(invocation.expected_approval_sha256)
    need(type(approval_raw) is bytes and len(approval_raw)<=MAX_JSON and digest(approval_raw)==expected,'external root approval hash')
    approval=obj(strict(approval_raw),'schema status certificate_sha256 semantic_map_sha256 independent_seal_sha256 semantic_review_sha256 capture_acceptance_sha256 binding_sha256 inputs local_geometry_only complete_capacity_accepted')
    need(same(approval,{'schema':1,'status':'root-approved-exact-local-region-map','certificate_sha256':digest(certificate),
        'semantic_map_sha256':digest(canonical(strict(certificate)['semantic_map'])),'independent_seal_sha256':digest(blobs['independent_seal']),
        'semantic_review_sha256':digest(blobs['semantic_review']),'capture_acceptance_sha256':digest(blobs['capture_acceptance']),
        'binding_sha256':digest(canonical(strict(certificate)['binding'])),'inputs':pins(blobs),
        'local_geometry_only':True,'complete_capacity_accepted':False}),'root approval join')
    seal=obj(strict(blobs['independent_seal']),'schema status members tree_sha256')
    need(type(seal['schema']) is int and seal['schema']==1 and seal['status']=='frozen-independent-semantic-map-review','independent seal schema')
    members=sequence(seal['members'],64);seen=set();bound_review=False
    for member in members:
        obj(member,'path bytes sha256');name=relative(member['path']);need(name not in seen,'independent seal collision');seen.add(name)
        integer(member['bytes'],0,MAX_TOTAL);sha(member['sha256'])
        if name=='semantic-review.json':
            need(member['bytes']==len(blobs['semantic_review']) and member['sha256']==digest(blobs['semantic_review']),'independent sealed review bytes');bound_review=True
    need(bound_review and sha(seal['tree_sha256'])==digest(canonical(members)),'independent seal review binding')
    review=obj(strict(blobs['semantic_review']),'schema status semantic_map_sha256 binding_sha256 capture_acceptance_sha256 targets whole_cfg_and_exits_checked outgoing_edges_exhaustive')
    need(same(review,{'schema':1,'status':'independently-reviewed-whole-function-region-map',
        'semantic_map_sha256':approval['semantic_map_sha256'],'binding_sha256':approval['binding_sha256'],
        'capture_acceptance_sha256':approval['capture_acceptance_sha256'],
        'targets':list(TARGETS),'whole_cfg_and_exits_checked':True,'outgoing_edges_exhaustive':True}),'independent semantic review join')
    return True

def union_width(spans):
    ordered=sorted(spans);total=0;current=None
    for begin,end in ordered:
        integer(begin);integer(end);need(begin<=end,'reversed union span')
        if current is None:current=(begin,end)
        elif begin<=current[1]:current=(current[0],max(current[1],end))
        else:total=checked_add(total,current[1]-current[0]);current=(begin,end)
    return checked_add(total,0 if current is None else current[1]-current[0])

def merge_congruence(current,modulus,residue):
    # All moduli are powers of two, so compatibility is equality modulo the
    # smaller modulus. Required region alignment is a constraint, not evidence.
    if current is None:return (modulus,residue)
    old_modulus,old_residue=current
    need((residue-old_residue)%min(modulus,old_modulus)==0,'contradictory physical alignment')
    return (modulus,residue) if modulus>old_modulus else current

def geometry(mapping,blobs,frontier_rows):
    obj(mapping,'claims targets phases arenas regions relations coverage return_chain edges backings transfers retained_partitions')
    need(same(mapping['claims'],{'unit':'bytes','local_geometry_only':True,'complete_capacity_accepted':False,'padding_writes_required':False}),'geometry scope/units')
    need(mapping['phases']==list(PHASES),'closed phase set');need(mapping['retained_partitions']==list(PARTITIONS),'all retained partitions required')
    missing=[]
    def unknown(scope,reason):
        item={'scope':scope,'reason':reason}
        if item not in missing:missing.append(item)
    targets={};native_spans={'ir':[],'asm':[]};symbols=set()
    for target in sequence(mapping['targets'],4):
        obj(target,'id frontier_sha256 symbol ir_function asm_function normal_exits cleanup_exits whole_cfg_reviewed admitted_monomorphization')
        name=target['id'];need(name in TARGETS and name not in targets,'duplicate or unknown native target')
        need(target['frontier_sha256']==digest(canonical(frontier_rows[name])),'exact source/MIR target binding')
        symbol=text(target['symbol']);need(symbol not in symbols,'ambiguous native symbol');symbols.add(symbol)
        ranges=[]
        for key in ('ir_function','asm_function'):
            value=anchor(target[key],blobs);need(value[0]==('ir' if key=='ir_function' else 'asm'),'function artifact kind')
            need(symbol.encode() in blobs[value[0]][value[1]:value[2]],'native symbol span')
            need(not any(value[1]<right and left<value[2] for left,right in native_spans[value[0]]),'overlapping function slices')
            native_spans[value[0]].append((value[1],value[2]));ranges.append(value)
        normal=anchors(target['normal_exits'],blobs)
        cleanup=[anchor(value,blobs) for value in sequence(target['cleanup_exits'],32)]
        need(len(set(normal+cleanup))==len(normal+cleanup),'duplicate native exit')
        need(all(inside(value,ranges[1]) for value in normal+cleanup),'native exit outside whole function')
        if not boolean(target['whole_cfg_reviewed']):unknown('local','whole CFG '+name)
        if name=='Dispatch':need(target['admitted_monomorphization'] is True,'actual admitted dispatch monomorphization')
        else:need(target['admitted_monomorphization'] is None,'unexpected monomorphization label')
        targets[name]={'ranges':ranges,'exits':normal+cleanup,'normal':normal,'cleanup':cleanup}
    for name in TARGETS:
        if name not in targets:unknown('local','missing/DCE target '+name)
    arenas={}
    for value in sequence(mapping['arenas'],16):
        obj(value,'id base entry_min entry_max rebase reviewed_rebase evidence physical_alignment')
        name=text(value['id'],64);need(name not in arenas,'duplicate arena')
        need(value['base'] in ('CallerEntrySP','ClosureEntrySP','DispatchEntrySP','BodyEntrySP','ReturnDestination'),'arena base')
        low=integer(value['entry_min'],I64_MIN,0);high=integer(value['entry_max'],low,I64_MAX)
        need(integer(value['rebase'])==-low,'explicit signed SP rebase');checked_add(high,-low)
        if not boolean(value['reviewed_rebase']):unknown('local','unreviewed rebase '+name)
        anchors(value['evidence'],blobs)
        physical=value['physical_alignment']
        if physical is not None:
            obj(physical,'modulus residue reviewed evidence')
            modulus=integer(physical['modulus'],1,U64);need(modulus&(modulus-1)==0,'physical alignment modulus')
            integer(physical['residue'],0,modulus-1)
            if boolean(physical['reviewed']):anchors(physical['evidence'],blobs)
            else:
                for proof in sequence(physical['evidence'],64):anchor(proof,blobs)
        arenas[name]=value
    regions={};by_role={}
    for value in sequence(mapping['regions'],32):
        obj(value,'id role target arena offset capacity alignment begin end evidence frame')
        identity=text(value['id'],64);role=value['role'];need(role in ROLES and identity not in regions and role not in by_role,'region identity/role')
        need(value['target']==ROLES[role][0],'region target role')
        begin=integer(value['begin'],0,4);end=integer(value['end'],1,5);need(begin<end,'region lifetime')
        align=integer(value['alignment'],1,U64);need(align&(align-1)==0 and align>=8,'region alignment')
        offset=integer(value['offset'],I64_MIN,I64_MAX)
        proofs=anchors(value['evidence'],blobs)
        if value['target'] in targets:need(all(any(inside(proof,r) for r in targets[value['target']]['ranges']) for proof in proofs),'region evidence outside target')
        arena=value['arena']
        if arena is None:unknown('local','unknown arena '+identity)
        else:need(arena in arenas,'unbound arena')
        capacity=value['capacity']
        if capacity is None:unknown('local','unknown capacity '+identity)
        else:
            integer(capacity,1,U64);minimum=ROLES[role][1]
            if minimum is not None:need(capacity>=minimum,'undersized complete carrier/child')
            if arena is not None:
                a=arenas[arena];normalized=checked_add(offset,a['rebase']);finish=checked_add(normalized,capacity)
                need(offset>=a['entry_min'] and finish<=a['entry_max']+a['rebase'],'out-of-arena extent')
        if role.startswith('F'):
            frame=value['frame']
            if frame is None:unknown('local','unknown native frame '+role)
            else:
                obj(frame,'kind complete components paths unresolved_local_edges')
                need(frame['kind'] in ('assembly_all_paths','llvm_allocas','unknown'),'frame evidence kind')
                need(type(frame['components']) is list and len(set(frame['components']))==len(frame['components']),'frame components')
                need(all(value in ('saved_state','padding','spills','outgoing') for value in frame['components']),'unknown frame component')
                if frame['kind']!='assembly_all_paths' or not boolean(frame['complete']) or set(frame['components'])!={'saved_state','padding','spills','outgoing'}:
                    unknown('local','incomplete native frame '+role)
                paths=sequence(frame['paths'],64);exits=[];lowest=0
                for path in paths:
                    obj(path,'exit steps');exit_span=anchor(path['exit'],blobs);exits.append(exit_span);sp=0
                    for step in sequence(path['steps'],128):
                        obj(step,'before delta after evidence');before=integer(step['before'],I64_MIN,0);delta=integer(step['delta'],I64_MIN,I64_MAX)
                        after=integer(step['after'],I64_MIN,0);need(before==sp and checked_add(before,delta,I64_MIN,I64_MAX)==after,'signed SP step/rebase arithmetic')
                        proof=anchor(step['evidence'],blobs)
                        if value['target'] in targets:need(inside(proof,targets[value['target']]['ranges'][1]),'SP evidence outside native function')
                        sp=after;lowest=min(lowest,sp)
                    need(sp==0,'native exit does not restore entry SP')
                if value['target'] not in targets or len(set(exits))!=len(exits) or set(exits)!=set(targets[value['target']]['exits']):unknown('local','unmapped native exits '+role)
                if capacity is None or capacity!=-lowest or offset!=lowest:unknown('local','native reservation does not cover full reviewed SP extrema '+role)
                if sequence(frame['unresolved_local_edges'],64):unknown('local','unresolved native adjustments '+role)
        else:need(value['frame'] is None,'carrier is not native frame')
        regions[identity]=value;by_role[role]=value
    for name,a in arenas.items():
        if a['base']=='ReturnDestination':continue
        role='F'+a['base'][:-len('EntrySP')];frame=by_role.get(role)
        if frame is None or frame['arena']!=name:
            unknown('local','native arena lacks its complete frame '+name);continue
        if frame['capacity'] is None or a['entry_min']!=frame['offset'] or a['entry_max']!=0 or frame['capacity']!=-a['entry_min']:
            unknown('local','native arena/frame reservation mismatch '+name)
        for region in regions.values():
            if region['arena']==name:need(frame['begin']<=region['begin']<region['end']<=frame['end'],'slot outlives containing native frame')
    for role,region in by_role.items():
        if role.startswith('F') and region['arena'] is not None:
            need(arenas[region['arena']]['base']==region['target']+'EntrySP','frame uses wrong entry-SP base')
    coverage={}
    for value in sequence(mapping['coverage'],8):
        obj(value,'requirement region phases allocated_representation')
        key=value['requirement'];need(key in REQUIREMENTS and key not in coverage,'coverage identity');coverage[key]=value
        role,phases=REQUIREMENTS[key];need(same(value['phases'],list(phases)) and value['allocated_representation'] is True,'allocated capacity/lifetime coverage')
        identity=value['region']
        if identity is None or identity not in regions:unknown('local','missing representation '+key)
        else:
            region=regions[identity];need(region['role']==role,'wrong coverage shape')
            if any(not region['begin']<=phase<region['end'] for phase in phases):unknown('local','expired representation '+key)
    for key in REQUIREMENTS:
        if key not in coverage:unknown('local','missing coverage '+key)
    chains={}
    expected_chain={('Body','Closure','R'),('Closure','Dispatch','R'),('Dispatch','Caller','C')}
    for value in sequence(mapping['return_chain'],3):
        obj(value,'from_target to_target value state evidence argument');key=(value['from_target'],value['to_target'],value['value'])
        need(key in expected_chain and key not in chains,'return-chain identity');chains[key]=value
        need(value['state'] in ('resolved','unknown'),'return provenance state');text(value['argument'],4096)
        anchors(value['evidence'],blobs)
        if value['state']=='unknown':unknown('local','unresolved sret/PHI/cast/copy '+str(key))
    if set(chains)!=expected_chain:unknown('local','missing return-pointer chain')
    edges={}
    for value in sequence(mapping['edges'],128):
        obj(value,'id target destination kind unresolved_local_effect evidence')
        identity=text(value['id'],64);need(identity not in edges and value['target'] in TARGETS,'edge identity')
        need(value['destination'] in TARGETS+('outside','unknown') and value['kind'] in ('call','indirect','dynamic','probe','cleanup','destruction'),'edge kind')
        anchors(value['evidence'],blobs);edges[identity]=value
        if boolean(value['unresolved_local_effect']):unknown('local','unresolved local edge '+identity)
        if value['destination'] in ('outside','unknown') or value['kind']!='call':unknown('transitive','outgoing/cleanup peak '+identity)
    if not any(edge['target']=='Body' and edge['destination']=='outside' for edge in edges.values()):unknown('local','missing Body outgoing frontier')
    unknown('transitive','destruction/unwind continuation outside this frontier')
    # One semantic backing obligation survives R -> C; these are not physical
    # allocation identities or accepted bounds. Source-conditional absence is
    # not turned into a zero-byte capacity.
    backing={}
    for value in sequence(mapping['backings'],13):
        obj(value,'key id capacity_bytes destruction_complete conditional_source_obligation')
        key=value['key'];identity=text(value['id'],64)
        need(key in BACKINGS and key not in backing and all(old['id']!=identity for old in backing.values()),'backing identity')
        need(value['capacity_bytes'] is None and value['destruction_complete'] is False and value['conditional_source_obligation'] is True,'backing capacity/destruction remains pending')
        backing[key]=value;unknown('backing','actual capacity/final destruction '+key)
    need(set(backing)==set(BACKINGS),'missing whole backing obligation')
    transfers=set()
    for value in sequence(mapping['transfers'],20):
        obj(value,'key backing_id from_owner to_owner');key=value['key'];pair=(key,value['from_owner'],value['to_owner'])
        need(key in CHILD_BACKINGS and pair not in transfers and (value['from_owner'],value['to_owner']) in (('Body','R'),('R','C')),'backing transfer')
        need(value['backing_id']==backing[key]['id'],'transfer minted backing identity');transfers.add(pair)
    need(transfers=={(key,a,b) for key in CHILD_BACKINGS for a,b in (('Body','R'),('R','C'))},'complete retained backing transfer')
    # Explicit same-base graph, with checked signed origins. Distinct integers
    # are not disjointness; an unknown/absent active relation blocks the union.
    graph={name:[] for name in arenas};relations={};disjoint=set()
    for value in sequence(mapping['relations'],120):
        obj(value,'left right kind right_minus_left reviewed evidence');left=value['left'];right=value['right']
        need(left in arenas and right in arenas and left!=right,'relation arena');pair=tuple(sorted((left,right)))
        need(pair not in relations,'duplicate arena relation');relations[pair]=value
        need(value['kind'] in ('same_base','disjoint','unknown'),'closed relation kind')
        reviewed=boolean(value['reviewed'])
        if value['kind']=='unknown':need(value['right_minus_left'] is None,'unknown relation offset');continue
        anchors(value['evidence'],blobs)
        if not reviewed:continue
        if value['kind']=='same_base':
            delta=integer(value['right_minus_left'],I64_MIN+1,I64_MAX)
            graph[left].append((right,delta));graph[right].append((left,-delta))
        else:need(value['right_minus_left'] is None,'disjoint relation offset');disjoint.add(pair)
    component={};origin={}
    for root in arenas:
        if root in component:continue
        component[root]=root;origin[root]=0;pending=[root]
        while pending:
            left=pending.pop()
            for right,delta in graph[left]:
                proposed=checked_add(origin[left],delta,I64_MIN,I64_MAX)
                if right in component:need(component[right]==root and origin[right]==proposed,'contradictory same-base relation')
                else:component[right]=root;origin[right]=proposed;pending.append(right)
    for left,right in disjoint:need(component[left]!=component[right],'contradictory physical relation')
    # Congruences refer to actual symbolic entry bases. Numerical entry_min /
    # rebase changes coordinates only; it supplies no physical alignment fact.
    known={};required={};starts={}
    for name,a in arenas.items():
        fact=a['physical_alignment']
        if fact is not None and fact['reviewed']:
            modulus=fact['modulus'];residue=(fact['residue']-origin[name]%modulus)%modulus
            group=component[name];known[group]=merge_congruence(known.get(group),modulus,residue)
    for identity,value in regions.items():
        if value['arena'] is None:continue
        name=value['arena'];group=component[name]
        start=checked_add(origin[name],value['offset'],I64_MIN,I64_MAX);starts[identity]=start
        modulus=value['alignment'];residue=(-start)%modulus
        required[group]=merge_congruence(required.get(group),modulus,residue)
    for group,(modulus,residue) in required.items():
        if group in known:merge_congruence(known[group],modulus,residue)
    for identity,value in regions.items():
        if value['arena'] is None:continue
        proof=known.get(component[value['arena']]);modulus=value['alignment'];residue=(-starts[identity])%modulus
        if proof is None or proof[0]<modulus:unknown('local','unsupported physical alignment '+identity)
        else:need(proof[1]%modulus==residue,'contradictory physical alignment')
    phase_bytes=[]
    for phase in range(5):
        live=[value for value in regions.values() if value['begin']<=phase<value['end']]
        active=sorted({value['arena'] for value in live if value['arena'] is not None})
        for i,left in enumerate(active):
            for right in active[i+1:]:
                if component[left]!=component[right] and tuple(sorted((left,right))) not in disjoint:
                    unknown('local','unknown active arena relation '+left+'/'+right+' phase '+str(phase))
        groups={}
        for value in live:
            if value['arena'] is None or value['capacity'] is None:continue
            arena=value['arena'];start=starts[value['id']]
            finish=checked_add(start,value['capacity'],I64_MIN,I64_MAX)
            groups.setdefault(component[arena],[]).append((start,finish))
        total=0
        for spans in groups.values():
            low=min(begin for begin,_ in spans);normalized=[]
            for begin,end in spans:normalized.append((integer(begin-low),integer(end-low)))
            total=checked_add(total,union_width(normalized))
        phase_bytes.append(total)
    local_closed=not any(item['scope']=='local' for item in missing)
    return phase_bytes if local_closed else None,missing

def _verify(certificate_raw,blobs,approval_raw,invocation):
    need(type(invocation) is Invocation and type(invocation.synthetic) is bool,'trusted invocation type')
    need(type(blobs) is dict and len(blobs)<=MAX_FILES and REQUIRED_BLOBS<=set(blobs),'bundle members')
    total=0
    for name,raw in blobs.items():
        relative(name);need(type(raw) is bytes,'immutable input bytes');total=checked_add(total,len(raw),0,MAX_TOTAL)
    blobs=ArtifactBytes(blobs)
    certificate=obj(strict(certificate_raw),'schema binding semantic_map')
    need(type(certificate['schema']) is int and certificate['schema']==1,'certificate schema')
    binding=certificate['binding'];obj(binding,'source_tree compiler_commit target features fixture_cfg opt_level mir_opt_level overflow_checks panic codegen_units debuginfo capture_plan_sha256 argv_sha256')
    sha(binding['source_tree']);expected_binding=dict(CURRENT_BINDING)
    if invocation.synthetic:expected_binding['source_tree']=binding['source_tree']
    need(same(binding,expected_binding),'source/compiler/cfg/inspection binding')
    need(len(blobs['ir'])+len(blobs['asm'])<=256*1024*1024 and len(blobs['stdout'])<=1048576 and len(blobs['stderr'])<=2097152,'capture type/aggregate prehash bounds')
    frontier=strict(blobs['frontier']);frontier_rows=source_binding(blobs,frontier,binding,invocation.synthetic)
    capture_custody(blobs,binding)
    approved=approve(certificate_raw,blobs,approval_raw,invocation)
    values,missing=geometry(certificate['semantic_map'],blobs,frontier_rows)
    if not approved:missing.append({'scope':'approval','reason':'external trusted root approval absent'})
    permitted=invocation.synthetic or approved
    if not permitted:values=None
    status='synthetic_local_geometry' if invocation.synthetic else ('reviewed_local_geometry_with_explicit_missing_facts' if approved else 'unreviewed_local_region_candidate')
    return {'status':status,'local_geometry_only':True,'complete_capacity_accepted':False,'synthetic':invocation.synthetic,
        'trusted_approval_matched':approved,'closed_local_phase_bytes':values,'local_peak_bytes':None if values is None else max(values),
        'certificate_sha256':digest(certificate_raw),'semantic_map_sha256':digest(canonical(certificate['semantic_map'])),
        'input_pin_set_sha256':digest(canonical(pins(blobs))),'expected_external_approval_sha256':invocation.expected_approval_sha256,
        'capture_acceptance_sha256':digest(blobs['capture_acceptance']),'independent_seal_sha256':digest(blobs['independent_seal']),
        'missing':missing+[{'scope':'authority','reason':'work prices, all retained quote terms, root durability and product integration pending'}]}

def verify(certificate_raw,blobs,approval_raw=None,invocation=None):
    """No file or process side effect. An absent external approval grants nothing."""
    try:return _verify(certificate_raw,blobs,approval_raw,invocation or Invocation(None))
    except (Refusal,KeyError,TypeError,ValueError,OverflowError,RecursionError) as error:
        return {'status':'incomplete_or_invalid','local_geometry_only':True,'complete_capacity_accepted':False,
            'synthetic':type(invocation) is Invocation and invocation.synthetic is True,'trusted_approval_matched':False,
            'closed_local_phase_bytes':None,'local_peak_bytes':None,'missing':[{'scope':'invalid','reason':str(error)[:256]}]}
