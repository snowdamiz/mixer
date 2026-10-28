"""Sixteen synthetic control families. These fixtures approve no actual artifact."""
import copy
from pathlib import Path
import tempfile
import unittest

import region_certificate as r

def encoded(value):return r.canonical(value)
def span(blobs,name,needle):
    raw=blobs[name];begin=raw.index(needle);return {'artifact':name,'begin':begin,'end':begin+len(needle),'sha256':r.digest(needle)}
def region(case,role):return next(v for v in case['cert']['semantic_map']['regions'] if v['role']==role)
def arena(case,identity):return next(v for v in case['cert']['semantic_map']['arenas'] if v['id']==identity)
def discard_arena(case,identity):
    m=case['cert']['semantic_map'];m['arenas']=[v for v in m['arenas'] if v['id']!=identity]
    m['relations']=[v for v in m['relations'] if identity not in (v['left'],v['right'])]

def fixture():
    # No compiler output is embedded or read. Symbols and instructions are
    # deliberately synthetic text, not a physical model of the real function.
    source=b'synthetic source, not an actual Mixer source file\n'
    mir=b'synthetic MIR template, not a native instantiation\n'
    irs={name:('define @'+name+' { synthetic }\n').encode() for name in r.TARGETS}
    assemblies={name:(name+':\nadjust_'+name+'\nrestore_'+name+'\nret_'+name+'\n').encode() for name in r.TARGETS}
    blobs={'ir':b''.join(irs.values()),'asm':b''.join(assemblies.values()),'stdout':b'',
        'source/fixture.rs':source,'mir':mir}
    members=[{'path':'fixture.rs','bytes':len(source),'sha256':r.digest(source)}]
    manifest={'schema':1,'changed':[],'member_count':1,'members':members,'new_distribution_members':0,'tree_sha256':r.digest(encoded(members))}
    blobs['source_manifest']=encoded(manifest)
    binding=copy.deepcopy(r.CURRENT_BINDING);binding['source_tree']=manifest['tree_sha256']
    scopes=[]
    for name in r.TARGETS:
        scopes.append({'id':name,
            'source':{'file':{'path':r.SOURCE_PREFIX+'fixture.rs','bytes':len(source),'sha256':r.digest(source)},'byte_begin':0,'byte_end':len(source),'span_sha256':r.digest(source)},
            'retained_MIR':{'file':{'path':'synthetic.mir','bytes':len(mir),'sha256':r.digest(mir)},'byte_begin':0,'byte_end':len(mir),'span_sha256':r.digest(mir)}})
    blobs['frontier']=encoded({'targets':scopes})
    records=[]
    for code,message in r.WARNINGS:
        records.append({'level':'warning','message':message,'code':{'code':code},'children':[],
            'spans':[{'file_name':r.SOURCE_ROOT+'/fixture.rs','byte_start':0,'byte_end':9,'line_start':1,'line_end':1,
                'text':[{'text':source.rstrip(b'\n').decode()}]}]})
    records.append({'level':'warning','message':'3 warnings emitted','code':None})
    blobs['stderr']=b''.join(encoded(v)+b'\n' for v in records)
    blobs['diagnostic_policy']=encoded({'schema':1,'status':'frozen-exact-source-bound-baseline-diagnostics','source_tree':binding['source_tree'],'records':records})
    mapping={'claims':{'unit':'bytes','local_geometry_only':True,'complete_capacity_accepted':False,'padding_writes_required':False},
        'phases':list(r.PHASES),'targets':[],'arenas':[],'regions':[],'relations':[],'coverage':[],
        'return_chain':[],'edges':[],'backings':[],'transfers':[],'retained_partitions':list(r.PARTITIONS)}
    for name,target in zip(r.TARGETS,scopes):
        mapping['targets'].append({'id':name,'frontier_sha256':r.digest(encoded(target)),'symbol':name,
            'ir_function':span(blobs,'ir',irs[name]),'asm_function':span(blobs,'asm',assemblies[name]),
            'normal_exits':[span(blobs,'asm',('ret_'+name).encode())],'cleanup_exits':[],
            'whole_cfg_reviewed':True,'admitted_monomorphization':True if name=='Dispatch' else None})
    lives={'R':(1,3),'C':(3,4),'O':(4,5),'FCaller':(0,5),'FClosure':(0,2),'FDispatch':(0,4),'FBody':(0,2)}
    frames={'FCaller':256,'FClosure':128,'FDispatch':32768,'FBody':32768}
    for role,(target,minimum) in r.ROLES.items():
        capacity=minimum if minimum is not None else frames[role]
        identity='A_'+role;proof=span(blobs,'asm',assemblies[target]);frame=None
        mapping['arenas'].append({'id':identity,'base':target+'EntrySP' if role.startswith('F') else 'ReturnDestination',
            'entry_min':-capacity,'entry_max':0,'rebase':capacity,'reviewed_rebase':True,'evidence':[proof]})
        if role.startswith('F'):
            frame={'kind':'assembly_all_paths','complete':True,'components':['saved_state','padding','spills','outgoing'],
                'paths':[{'exit':span(blobs,'asm',('ret_'+target).encode()),'steps':[
                    {'before':0,'delta':-capacity,'after':-capacity,'evidence':span(blobs,'asm',('adjust_'+target).encode())},
                    {'before':-capacity,'delta':capacity,'after':0,'evidence':span(blobs,'asm',('restore_'+target).encode())}]}],
                'unresolved_local_edges':[]}
        begin,end=lives[role]
        mapping['regions'].append({'id':role,'role':role,'target':target,'arena':identity,'offset':-capacity,'capacity':capacity,
            'alignment':8,'begin':begin,'end':end,'evidence':[proof],'frame':frame})
    names=sorted(v['id'] for v in mapping['arenas'])
    proof=span(blobs,'asm',assemblies['Body'])
    for i,left in enumerate(names):
        for right in names[i+1:]:mapping['relations'].append({'left':left,'right':right,'kind':'disjoint','right_minus_left':None,'reviewed':True,'evidence':[proof]})
    for key,(role,phases) in r.REQUIREMENTS.items():
        mapping['coverage'].append({'requirement':key,'region':role,'phases':list(phases),'allocated_representation':True})
    for a,b,value in [('Body','Closure','R'),('Closure','Dispatch','R'),('Dispatch','Caller','C')]:
        mapping['return_chain'].append({'from_target':a,'to_target':b,'value':value,'state':'resolved','evidence':[span(blobs,'ir',irs[a])],
            'argument':'Synthetic mapping hypothesis only; not an instruction-semantics proof.'})
    for a,b in [('Caller','Dispatch'),('Dispatch','Closure'),('Closure','Body'),('Body','outside')]:
        mapping['edges'].append({'id':a+'_'+b,'target':a,'destination':b,'kind':'call','unresolved_local_effect':False,'evidence':[span(blobs,'ir',irs[a])]})
    for key in r.BACKINGS:
        mapping['backings'].append({'key':key,'id':'B_'+key,'capacity_bytes':None,'destruction_complete':False,'conditional_source_obligation':True})
    for key in r.CHILD_BACKINGS:
        for a,b in [('Body','R'),('R','C')]:mapping['transfers'].append({'key':key,'backing_id':'B_'+key,'from_owner':a,'to_owner':b})
    return {'cert':{'schema':1,'binding':binding,'semantic_map':mapping},'blobs':blobs}

def refresh_capture(case):
    blobs=case['blobs'];binding=case['cert']['binding'];outputs=[r.pin(name,blobs[name]) for name in ('ir','asm','stdout','stderr')]
    blobs['capture_observation']=encoded({'schema':1,'status':'captured-artifacts-only','binding':binding,'compiler_exit':0,'outputs':outputs,
        'source_manifest_sha256':r.digest(blobs['source_manifest']),'owned_groups_closed':True,'cleanup_complete':True,'bounds_met':True,'truncated':False,'capture_complete':True})
    blobs['capture_acceptance']=encoded({'schema':1,'status':'accepted-capture-custody-only','observation_sha256':r.digest(blobs['capture_observation']),
        'diagnostic_policy_sha256':r.digest(blobs['diagnostic_policy']),'source_manifest_sha256':r.digest(blobs['source_manifest']),
        'binding_sha256':r.digest(encoded(binding)),'outputs':outputs,'local_geometry_only':True,'complete_capacity_accepted':False})

def authorize(case):
    # This envelope is created by the synthetic test, outside the certificate.
    # Invocation.synthetic=True prevents it from approving actual geometry.
    blobs=case['blobs'];certificate=encoded(case['cert']);binding_hash=r.digest(encoded(case['cert']['binding']))
    map_hash=r.digest(encoded(case['cert']['semantic_map']))
    blobs['semantic_review']=encoded({'schema':1,'status':'independently-reviewed-whole-function-region-map','semantic_map_sha256':map_hash,
        'binding_sha256':binding_hash,'capture_acceptance_sha256':r.digest(blobs['capture_acceptance']),
        'targets':list(r.TARGETS),'whole_cfg_and_exits_checked':True,'outgoing_edges_exhaustive':True})
    members=[{'path':'semantic-review.json','bytes':len(blobs['semantic_review']),'sha256':r.digest(blobs['semantic_review'])}]
    blobs['independent_seal']=encoded({'schema':1,'status':'frozen-independent-semantic-map-review','members':members,'tree_sha256':r.digest(encoded(members))})
    approval=encoded({'schema':1,'status':'root-approved-exact-local-region-map','certificate_sha256':r.digest(certificate),'semantic_map_sha256':map_hash,
        'independent_seal_sha256':r.digest(blobs['independent_seal']),'semantic_review_sha256':r.digest(blobs['semantic_review']),
        'capture_acceptance_sha256':r.digest(blobs['capture_acceptance']),'binding_sha256':binding_hash,'inputs':r.pins(blobs),
        'local_geometry_only':True,'complete_capacity_accepted':False})
    return certificate,blobs,approval,r.Invocation(r.digest(approval),synthetic=True)

def evaluate(case,hook=None):
    refresh_capture(case)
    if hook:hook(case)
    return r.verify(*authorize(case))

def diagnostics(case,change):
    policy=r.strict(case['blobs']['diagnostic_policy']);change(policy['records'])
    case['blobs']['diagnostic_policy']=encoded(policy)
    case['blobs']['stderr']=b''.join(encoded(v)+b'\n' for v in policy['records'])

class MemoryPort:
    def __init__(self,data,read_override=None,change_after_read=False):
        self.data=data;self.override=read_override;self.change=change_after_read;self.did_read=False;self.limits=[]
    def snapshot(self,name,maximum):
        raw=self.data[name];return (len(raw),r.digest(raw),('changed' if self.change and self.did_read else 'same',))
    def read(self,name,limit):
        self.did_read=True;self.limits.append(limit);return self.data[name] if self.override is None else self.override

class RegionCertificateControls(unittest.TestCase):
    def scoped(self,result):
        self.assertIs(result['local_geometry_only'],True);self.assertIs(result['complete_capacity_accepted'],False)
        return result
    def closed(self,case):
        result=self.scoped(evaluate(case));self.assertEqual(result['status'],'synthetic_local_geometry')
        self.assertTrue(result['synthetic']);self.assertTrue(result['trusted_approval_matched']);self.assertIsNotNone(result['closed_local_phase_bytes']);return result
    def invalid(self,case,hook=None):
        result=self.scoped(evaluate(case,hook));self.assertEqual(result['status'],'incomplete_or_invalid');self.assertIsNone(result['closed_local_phase_bytes']);return result
    def incomplete(self,case):
        result=self.scoped(evaluate(case));self.assertEqual(result['status'],'synthetic_local_geometry');self.assertIsNone(result['closed_local_phase_bytes']);return result

    def test_p01_closed_grammar_and_typed_numbers(self):
        for raw in [b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}']:
            with self.assertRaises(r.Refusal):r.strict(raw)
        for mutate in [lambda c:c['cert'].update(unknown=1),lambda c:c['cert'].update(schema=True),
            lambda c:region(c,'R').update(capacity=True),lambda c:region(c,'R').update(capacity=13624.0),
            lambda c:c['cert']['semantic_map']['claims'].update(complete_capacity_accepted=0),
            lambda c:c['cert']['semantic_map']['arenas'].append(copy.deepcopy(c['cert']['semantic_map']['arenas'][0]))]:
            case=fixture();mutate(case);self.invalid(case)
        for rows in [[r.pin('x',b'a'),r.pin('x',b'a')],[r.pin('x',b'a'),r.pin('x/y',b'b')],[r.pin('../escape',b'a')]]:
            with self.assertRaises(r.Refusal):r.validate_pins(rows)
        def boolean_exit(case):
            o=r.strict(case['blobs']['capture_observation']);o['compiler_exit']=False;case['blobs']['capture_observation']=encoded(o)
        self.invalid(fixture(),boolean_exit)

    def test_p02_bounded_actual_memory_and_path_custody(self):
        data={'x':b'good'};expected=[r.pin('x',b'good')];port=MemoryPort(data)
        self.assertEqual(r.read_saved(port,expected),data);self.assertEqual(port.limits,[5])
        for port in [MemoryPort(data,b'evil'),MemoryPort(data,b'good!'),MemoryPort(data,change_after_read=True)]:
            with self.assertRaises(r.Refusal):r.read_saved(port,expected)
        scratch=Path(__file__).resolve().parents[1]/'command'
        self.assertTrue(scratch.is_dir(),'Root must create the bounded owned test output directory.')
        with tempfile.TemporaryDirectory(prefix='synthetic-reader-',dir=scratch) as directory:
            root=Path(directory);(root/'x').write_bytes(b'good');actual=r.FilesystemInputs(root)
            self.assertEqual(r.read_saved(actual,expected),data)
            (root/'alias').symlink_to(root/'x')
            with self.assertRaises(r.Refusal):r.read_saved(actual,[r.pin('alias',b'good')])
            (root/'sub').symlink_to(root,target_is_directory=True)
            with self.assertRaises(r.Refusal):r.read_saved(actual,[r.pin('sub/x',b'good')])

    def test_p03_unique_actual_frontier_and_no_proxy_instantiation(self):
        case=fixture();case['cert']['semantic_map']['targets'].pop();self.incomplete(case)
        case=fixture();case['cert']['semantic_map']['targets'][1]['symbol']='Caller';self.invalid(case)
        case=fixture();case['cert']['semantic_map']['targets'][1]['frontier_sha256']='0'*64;self.invalid(case)
        case=fixture();case['cert']['semantic_map']['targets'][2]['admitted_monomorphization']=False;self.invalid(case)
        for key,value in [('target','another-target'),('compiler_commit','another-compiler'),('fixture_cfg','proxy_fixture')]:
            case=fixture();case['cert']['binding'][key]=value;self.invalid(case)
        case=fixture();refresh_capture(case);certificate,blobs,approval,invocation=authorize(case)
        # Fake source and approvals cannot become actual geometry by toggling a label.
        result=self.scoped(r.verify(certificate,blobs,approval,r.Invocation(invocation.expected_approval_sha256,synthetic=False)))
        self.assertEqual(result['status'],'incomplete_or_invalid')

    def test_p04_allocated_complete_carrier_without_padding_writes(self):
        baseline=self.closed(fixture());self.assertFalse(fixture()['cert']['semantic_map']['claims']['padding_writes_required'])
        self.assertGreaterEqual(baseline['local_peak_bytes'],13624)
        case=fixture();region(case,'R')['capacity']=13623;self.invalid(case)
        case=fixture();case['cert']['semantic_map']['regions']=[v for v in case['cert']['semantic_map']['regions'] if v['role']!='R'];self.incomplete(case)
        case=fixture();region(case,'R')['end']=2;self.incomplete(case)
        case=fixture();case['cert']['semantic_map']['coverage'][0]['allocated_representation']=False;self.invalid(case)

    def test_p05_child_and_outer_result_are_complete_distinct_obligations(self):
        case=fixture();region(case,'C')['capacity']=13639;self.invalid(case)
        case=fixture();case['cert']['semantic_map']['regions']=[v for v in case['cert']['semantic_map']['regions'] if v['role']!='O'];self.incomplete(case)
        case=fixture();region(case,'O')['capacity']=8;self.invalid(case)
        case=fixture();region(case,'O')['arena']=None;self.incomplete(case)
        self.closed(fixture())

    def test_p06_body_frame_never_defaults_to_eight_or_alloca_sum(self):
        for modify in [lambda f:f.update(frame=None),lambda f:f.update(capacity=None),lambda f:f.update(capacity=8),
            lambda f:f['frame'].update(kind='llvm_allocas'),lambda f:f['frame'].update(complete=False),
            lambda f:f['frame'].update(paths=[])]:
            case=fixture();modify(region(case,'FBody'));self.incomplete(case)
        case=fixture();region(case,'FBody')['frame']['paths'][0]['steps'].pop();self.invalid(case)

    def test_p07_sret_phi_cast_and_copy_provenance_unknowns(self):
        for index in range(3):
            case=fixture();chain=case['cert']['semantic_map']['return_chain'][index]
            chain['state']='unknown';chain['argument']='ReviewedBound-looking label cannot resolve a PHI/cast/copy.';self.incomplete(case)
        case=fixture();case['cert']['semantic_map']['return_chain'].pop();self.incomplete(case)
        case=fixture();case['cert']['semantic_map']['return_chain'][0]['evidence'][0]['sha256']='0'*64;self.invalid(case)

    def test_p08_only_explicit_reviewed_arena_relations(self):
        case=fixture();case['cert']['semantic_map']['relations']=[];self.incomplete(case)
        case=fixture();rel=next(v for v in case['cert']['semantic_map']['relations'] if {v['left'],v['right']}=={'A_R','A_FBody'})
        rel.update(kind='unknown',right_minus_left=None,reviewed=False,evidence=[]);self.incomplete(case)
        case=fixture()
        for rel in case['cert']['semantic_map']['relations']:rel['reviewed']=False
        self.incomplete(case)
        case=fixture();region(case,'R')['arena']='numeric-id-with-no-evidence';self.invalid(case)

    def test_p09_checked_signed_sp_rebase_geometry_and_units(self):
        for modify in [lambda c:region(c,'R').update(offset=r.I64_MAX),lambda c:region(c,'R').update(capacity=r.U64),
            lambda c:region(c,'R').update(alignment=3),lambda c:region(c,'R').update(offset=-13623),
            lambda c:arena(c,'A_R').update(rebase=0),lambda c:c['cert']['semantic_map']['claims'].update(unit='work')]:
            case=fixture();modify(case);self.invalid(case)
        case=fixture();region(case,'FBody')['frame']['paths'][0]['steps'][0]['after']=-32760;self.invalid(case)
        case=fixture();arena(case,'A_R')['reviewed_rebase']=False;self.incomplete(case)
        small=r.ArtifactBytes({'ir':b'ab','asm':b''});small.span_bytes_remaining=1
        with self.assertRaises(r.Refusal):r.anchor(span(small,'ir',b'ab'),small)
        self.closed(fixture()) # Explicit negative entry-relative offsets and rebases.

    def test_p10_partial_contained_and_disjoint_unions(self):
        self.assertEqual(r.union_width([(0,48),(32,80)]),80)
        self.assertEqual(r.union_width([(0,48),(8,16)]),48)
        self.assertEqual(r.union_width([(0,48),(90,100)]),58)
        with self.assertRaises(r.Refusal):r.union_width([(8,7)])
        with self.assertRaises(r.Refusal):r.checked_add(r.U64,1)
        separate=fixture();region(separate,'R')['end']=4;separate_bytes=self.closed(separate)['closed_local_phase_bytes'][3]
        contained=fixture();old=region(contained,'R')['arena'];region(contained,'R').update(arena='A_C',offset=-13640,end=4);discard_arena(contained,old)
        contained_bytes=self.closed(contained)['closed_local_phase_bytes'][3]
        self.assertEqual(separate_bytes-contained_bytes,13624)
        partial=copy.deepcopy(contained);region(partial,'R')['offset']=-13608;arena(partial,'A_C')['entry_max']=16
        self.assertEqual(self.closed(partial)['closed_local_phase_bytes'][3],contained_bytes+16)
        contradictory=fixture();pairs={tuple(sorted((v['left'],v['right']))):v for v in contradictory['cert']['semantic_map']['relations']}
        for a,b,delta in [('A_C','A_O',0),('A_O','A_R',0),('A_C','A_R',8)]:pairs[tuple(sorted((a,b)))].update(kind='same_base',right_minus_left=delta)
        self.invalid(contradictory)

    def test_p11_narrow_phase_coverage_is_required_before_wrapping(self):
        case=fixture();region(case,'C')['begin']=0
        case['cert']['semantic_map']['regions']=[v for v in case['cert']['semantic_map']['regions'] if v['role']!='R'];self.incomplete(case)
        case=fixture();region(case,'FBody')['end']=1;self.incomplete(case)
        case=fixture();region(case,'R')['begin']=2;self.incomplete(case)
        case=fixture();case['cert']['semantic_map']['coverage'].pop();self.incomplete(case)

    def test_p12_frame_containment_counts_once_and_cannot_outlive_frame(self):
        baseline=self.closed(fixture())['closed_local_phase_bytes'][1]
        case=fixture();old=region(case,'R')['arena'];region(case,'R').update(arena='A_FDispatch',offset=-32760);discard_arena(case,old)
        self.assertEqual(self.closed(case)['closed_local_phase_bytes'][1],baseline-13624)
        expired=copy.deepcopy(case);region(expired,'R')['end']=5;self.invalid(expired)
        case=fixture();region(case,'FBody')['frame']['components'].remove('outgoing');self.incomplete(case)
        case=fixture();region(case,'FBody')['frame']['unresolved_local_edges']=['unmapped outgoing slot'];self.incomplete(case)
        case=fixture();region(case,'FBody')['arena']='A_FCaller';self.invalid(case)

    def test_p13_transitive_cleanup_dynamic_and_destruction_stay_missing(self):
        result=self.closed(fixture());self.assertTrue(any(v['scope']=='transitive' for v in result['missing']))
        for kind in ['indirect','dynamic','probe','cleanup','destruction']:
            case=fixture();edge=case['cert']['semantic_map']['edges'][-1];edge['kind']=kind
            result=self.closed(case);self.assertTrue(any('outgoing/cleanup' in v['reason'] for v in result['missing']))
            edge['unresolved_local_effect']=True;self.incomplete(case)
        case=fixture();case['cert']['semantic_map']['edges'][-1]['callee_peak_bytes']=0;self.invalid(case)

    def test_p14_backing_identity_survives_and_no_unknown_bound_is_zero(self):
        case=fixture();result=self.closed(case)
        self.assertEqual(sum(v['scope']=='backing' for v in result['missing']),13)
        case=fixture();case['cert']['semantic_map']['transfers'][0]['backing_id']='new-after-move';self.invalid(case)
        case=fixture();case['cert']['semantic_map']['backings'][0]['capacity_bytes']=0;self.invalid(case)
        case=fixture();case['cert']['semantic_map']['backings'].pop();self.invalid(case)
        case=fixture();case['cert']['semantic_map']['retained_partitions'].remove('P0');self.invalid(case)

    def test_p15_external_approval_and_independent_custody_join(self):
        case=fixture();refresh_capture(case);certificate,blobs,approval,invocation=authorize(case)
        result=self.scoped(r.verify(certificate,blobs,approval,invocation));self.assertTrue(result['trusted_approval_matched']);self.assertTrue(result['synthetic'])
        result=self.scoped(r.verify(certificate,blobs,None,r.Invocation(None,synthetic=True)));self.assertFalse(result['trusted_approval_matched'])
        for wrong in [r.Invocation('0'*64,synthetic=True),r.Invocation(None,synthetic=True)]:
            result=self.scoped(r.verify(certificate,blobs,approval,wrong));self.assertEqual(result['status'],'incomplete_or_invalid')
        for field in ['certificate_sha256','semantic_map_sha256','independent_seal_sha256','capture_acceptance_sha256']:
            altered=r.strict(approval);altered[field]='0'*64;raw=encoded(altered)
            result=self.scoped(r.verify(certificate,blobs,raw,r.Invocation(r.digest(raw),synthetic=True)));self.assertEqual(result['status'],'incomplete_or_invalid')
        case=fixture();case['cert']['expected_approval_sha256']='self-approved';self.invalid(case)
        case=fixture();region(case,'R')['ReviewedBound']=True;self.invalid(case)
        for key in ['whole_cfg_and_exits_checked','outgoing_edges_exhaustive']:
            case=fixture();refresh_capture(case);certificate,blobs,approval,invocation=authorize(case)
            review=r.strict(blobs['semantic_review']);review[key]=False;blobs['semantic_review']=encoded(review)
            # Old trusted approval cannot be silently rebound to changed review bytes.
            result=self.scoped(r.verify(certificate,blobs,approval,invocation));self.assertEqual(result['status'],'incomplete_or_invalid')

    def test_p16_capture_whole_stream_limits_and_no_fallback(self):
        for key,value in [('compiler_exit',1),('truncated',True),('bounds_met',False),('owned_groups_closed',False),('capture_complete',False)]:
            def change(case,key=key,value=value):
                o=r.strict(case['blobs']['capture_observation']);o[key]=value;case['blobs']['capture_observation']=encoded(o)
            self.invalid(fixture(),change)
        for change in [lambda rows:rows.pop(0),lambda rows:rows.append(copy.deepcopy(rows[0])),
            lambda rows:rows[0].update(message='another warning'),lambda rows:rows[0].update(code={'code':'other'}),
            lambda rows:rows[0]['spans'][0].update(byte_start=9999),lambda rows:rows[-1].update(message='2 warnings emitted')]:
            case=fixture();diagnostics(case,change);self.invalid(case)
        case=fixture();case['blobs']['stdout']=b'unexpected';self.invalid(case)
        case=fixture();refresh_capture(case);certificate,blobs,approval,invocation=authorize(case)
        blobs['ir']+=b'changed after approval';self.assertEqual(self.scoped(r.verify(certificate,blobs,approval,invocation))['status'],'incomplete_or_invalid')
        with self.assertRaises(r.Refusal):r.validate_pins([{'name':'too_big','bytes':r.MAX_TOTAL+1,'sha256':'0'*64}])

if __name__=='__main__':unittest.main(verbosity=2)
