#!/usr/bin/env python3
"""Independent, read-only review of retained compiler/source evidence.

Imports only the Python standard library. Never runs another program. The MIR
parser accounts for the entire input and compares every non-probe body. Allocation
IDs are constrained by references in corresponding operation roles, then by
relocations and uniquely identified remaining payloads; declaration order and ID
arithmetic are not used to authorize an allocation pairing.
"""
import collections
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C = ROOT / 'verification/swift-guarded-snapshot-scoped-binding-source'
O = ROOT / 'verification/swift-guarded-snapshot-outer-parent-independent'
P = ROOT / 'verification/swift-guarded-snapshot-outer-parent-source'
S = ROOT / 'verification/swift-guarded-snapshot-outer-parent-work-storage'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
SOURCE_TREE = '69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7'
OLD_TREE = '27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
SEAL = '84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2'
RELEASE = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-scoped-binding-source-frozen-release.json'
COST = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-outer-parent-work-storage-host-acceptance.json'
TYPES = ('ReviewedFixtureBindingV1','FrozenFixtureV1','ImmutableIdentityPreimageV1',
         'ImmutableFixtureIdentitiesV1','PreexistingImmutableBindingV1','OneFixtureOuterRequestV1')
PROBES = ('outer_parent_layout_query_v1','outer_parent_account_layout_query_v1',
          'scoped_result_layout_query_v1','scoped_local_binding_compiles_v1')
LITERAL_COMMENT = re.compile(r"'(?:[^'\\\n]|\\.)'|\"(?:[^\"\\]|\\.)*\"|//[^\n]*")
ALLOCATION = re.compile(r'\balloc\d+\b')
SPAN = re.compile(r'(?<=<impl at )<SOURCE>/([^\s:]+):\d+:\d+: \d+:\d+(?=>)')
LIFETIME = re.compile(r'\b('+'|'.join(TYPES)+r")(?:::)?<'_>")
PATHS = (str(O/'owned-work/compiler-metadata-mir/vm'),str(C/'owned-work/positive/vm'))

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(d): return json.dumps(d, sort_keys=True,separators=(',',':')).encode()
def read(p): return json.loads(p.read_bytes())
def row(name,b): return dict(path=name,bytes=len(b),sha256=sha(b))
def require(condition,message):
    if not condition: raise AssertionError(message)

def manifest(source):
    members=[row(n,source[n]) for n in sorted(source,key=Path)]
    return dict(schema=1,member_count=len(members),members=members,tree_sha256=sha(canonical(members)))

def outside_literals(text,change,remove_comments=False):
    """Lex literal/comment regions before applying any display transformation."""
    out=[]; end=0
    for m in LITERAL_COMMENT.finditer(text):
        out.append(change(text[end:m.start()]))
        if not m.group().startswith('//') or not remove_comments: out.append(m.group())
        end=m.end()
    out.append(change(text[end:]))
    return ''.join(out)

def norm(block):
    if block.startswith('alloc'):
        # No comment/lifetime/span/path normalization of raw allocation data.
        return block
    def change(text):
        for prefix in PATHS: text=text.replace(prefix,'<SOURCE>')
        text=SPAN.sub(r'<SOURCE>/\1:<DISPLAY-SPAN>',text)
        text=LIFETIME.sub(r'\1',text)
        return text.replace("selected_outer_request_v1::<'_>",'selected_outer_request_v1')
    text=outside_literals(block,change,remove_comments=True)
    return '\n'.join(x.rstrip() for x in text.splitlines() if x.strip())

def allocation_parts(block):
    """Retain string literals and allocation ASCII displays byte-for-byte.

    Only allocNNN syntax in an allocation header/relocation field is a reference.
    A raw ASCII display at the right of the last box separator is ordinary data.
    """
    refs=[]
    def replace(text):
        def take(m): refs.append(m.group()); return '<ALLOCATION-REFERENCE>'
        return ALLOCATION.sub(take,text)
    if block.startswith('alloc'):
        lines=block.splitlines();out=[replace(lines[0])]
        for line in lines[1:]:
            if '│' in line:
                left,sep,ascii_display=line.rpartition('│')
                out.append(replace(left)+sep+ascii_display)
            else: out.append(replace(line))
        return '\n'.join(out),refs
    return outside_literals(block,replace),refs

def parse_mir(text):
    blocks=[];pending=[];outside_comments=0;covered=0
    for number,line in enumerate(text.splitlines(keepends=True),1):
        covered+=len(line)
        stripped=line.rstrip('\r\n')
        if pending:
            require(bool(stripped) or line.isspace(),f'bad line {number}')
            pending.append(line)
            if stripped=='}':
                blocks.append(''.join(pending).rstrip('\r\n'));pending=[]
            elif stripped and not stripped[0].isspace():
                raise AssertionError(f'unrecognized top-level interior at line {number}: {stripped[:100]}')
        elif not stripped.strip(): pass
        elif stripped.startswith('//'): outside_comments+=1
        else:
            if stripped.endswith(';') and (stripped.startswith(('const ','static ')) or '::{constant#' in stripped):
                blocks.append(stripped)
                continue
            require(stripped.endswith(' {'),f'uncovered MIR line {number}: {stripped[:150]}')
            require(stripped.startswith(('fn ','const ','static ','alloc')) or '::{constant#' in stripped,
                    f'unknown MIR construct {number}: {stripped[:100]}')
            pending=[line]
    require(not pending,'unterminated MIR body')
    require(covered==len(text),'MIR parser coverage')
    return blocks,dict(characters=covered,blocks=len(blocks),outside_comment_lines=outside_comments,uncovered_noncomment_characters=0)

def inert(block):
    header=block.split('\n',1)[0]
    return any(header.startswith('fn '+n+'(') or header.startswith(n+'::{constant#') for n in PROBES)

def compare_blocks(old_blocks,new_blocks):
    old=[norm(x) for x in old_blocks if not inert(x)]
    new=[norm(x) for x in new_blocks if not inert(x)]
    require(len(old)==len(new),'production block count changed')
    od={};nd={};pairs=[];mapping={};inverse={};constraints=0;origins=collections.Counter()
    old_context=collections.defaultdict(set);new_context=collections.defaultdict(set)
    current_old=current_new=None;allocation_occurrences=[]
    def bind(a,b,origin):
        nonlocal constraints
        constraints+=1
        require(mapping.get(a,b)==b,f'one old allocation mapped to two targets: {a}')
        require(inverse.get(b,a)==a,f'two old allocations merged into {b}')
        if a not in mapping: mapping[a]=b;inverse[b]=a;origins[origin]+=1
    def pair(a,b,origin):
        af,ar=allocation_parts(a);bf,br=allocation_parts(b)
        require(af==bf,f'non-display MIR difference {a[:160]}\n'+''.join(difflib.unified_diff(af.splitlines(True),bf.splitlines(True)))[:2400])
        require(len(ar)==len(br),'reference occurrence count')
        for x,y in zip(ar,br): bind(x,y,origin)
    for index,(a,b) in enumerate(zip(old,new)):
        aa=a.startswith('alloc');ba=b.startswith('alloc');require(aa==ba,'allocation/production ordering changed')
        if aa:
            ai=ALLOCATION.match(a).group();bi=ALLOCATION.match(b).group()
            require(od.get(ai,a)==a and nd.get(bi,b)==b,'repeated allocation ID with different payload')
            od[ai]=a;nd[bi]=b
            old_context[ai].add(current_old);new_context[bi].add(current_new)
            allocation_occurrences.append((ai,bi))
        else:
            pair(a,b,'production_reference_role');pairs.append(dict(index=index,header=a.split('\n',1)[0],normalized_sha256=sha(a.encode())))
            current_old=sha(allocation_parts(a)[0].encode());current_new=sha(allocation_parts(b)[0].encode())
    processed=set()
    def follow():
        while True:
            todo=[(a,b) for a,b in mapping.items() if a not in processed and a in od]
            if not todo: break
            for a,b in todo:
                require(b in nd,'mapped relocation target has no candidate block')
                pair(od[a],nd[b],'relocation_reference_role');processed.add(a)
    follow()
    # Match any unreachable allocation by its complete payload shape, not its
    # ordinal or the observed allocation-number offset. Ambiguity fails closed.
    while len(processed)<len(od):
        left=collections.defaultdict(list);right=collections.defaultdict(list)
        for a in od.keys()-processed: left[(allocation_parts(od[a])[0],tuple(sorted(old_context[a])))].append(a)
        for b in nd.keys()-set(inverse): right[(allocation_parts(nd[b])[0],tuple(sorted(new_context[b])))].append(b)
        progress=False
        for shape,names in left.items():
            choices=right.get(shape,[])
            if len(names)==len(choices)==1:
                bind(names[0],choices[0],'unique_complete_payload_and_production_context');progress=True
        require(progress,'unresolved ambiguous/unmatched allocation identities')
        follow()
    require(set(mapping)==set(od),'old reference/header coverage differs')
    require(set(inverse)==set(nd),'candidate reference/header coverage differs')
    allocation_rows=[]
    for a in od:
        b=mapping[a];pair(od[a],nd[b],'final_allocation_check')
        allocation_rows.append(dict(accepted=a,candidate=b,shape_sha256=sha(allocation_parts(od[a])[0].encode())))
    # Positional headers are validated after independently derived role/graph
    # mapping; never used to derive it.
    require(all(mapping[a]==b for a,b in allocation_occurrences),'allocation occurrence differs from independently verified graph mapping')
    return dict(production_functions=sum(x.startswith('fn ') for x in old),
        production_other_bodies=sum(not x.startswith(('fn ','alloc')) for x in old),
        allocations=len(allocation_occurrences),distinct_allocation_ids=len(od),production_total=len(old),
        normalized_nonallocation_rows=pairs,allocation_rows=allocation_rows,
        allocation_mapping=mapping,allocation_derivation=dict(origins),reference_constraints=constraints,
        allocation_payload_extents_alignment_rawbytes_relocations_exact=True,
        allocation_id_offset_observed=sorted({int(b[5:])-int(a[5:]) for a,b in mapping.items()}),
        allocation_mapping_depends_on_offset_or_ordinal=False,equality=True)

def custody():
    require(sha((C/'seal.json').read_bytes())==SEAL,'candidate seal identity')
    require(sha(RELEASE.read_bytes())=='bcf7c5bc242f5d12ee404d9234ee5de88abf8ed07b8cfe8e7cbe69cd8200a8ae','root release identity')
    require(sha(COST.read_bytes())=='8b6190049be7d5c995b6bd01c477454e503ac1dcad518602370416f510779d9c','old cost acceptance identity')
    sealed=read(C/'seal.json')
    paths=sorted(x for x in C.rglob('*') if x.is_file() and x.name!='seal.json')
    require(not any(x.is_symlink() for x in C.rglob('*')),'candidate symlink')
    members=[row(str(x.relative_to(C)),x.read_bytes()) for x in paths]
    require(members==sealed['members'],'candidate sealed members')
    require(sha(canonical(members))==sealed['tree_sha256'],'candidate packet tree')
    require(len(members)==200 and sum(x['bytes'] for x in members)==24834896,'candidate member extent')
    require(all(stat.S_IMODE(x.stat().st_mode)==0o444 for x in paths+[C/'seal.json']),'candidate file modes')
    require(all(stat.S_IMODE(x.stat().st_mode)==0o555 for x in [C]+[y for y in C.rglob('*') if y.is_dir()]),'candidate directory modes')
    accepted={};origins=read(C/'accepted-source-custody.json')
    require(len(origins)==146 and len({x['path'] for x in origins})==146,'source custody membership')
    for x in origins:
        origin=ROOT/x['origin'];b=origin.read_bytes()
        require(row(x['path'],b)=={k:x[k] for k in ('path','bytes','sha256')},'accepted source origin '+x['path'])
        accepted[x['path']]=b
    require(manifest(accepted)==read(C/'accepted-source-manifest.json')==read(P/'source-manifest.json'),'accepted manifest')
    require(manifest(accepted)['tree_sha256']==OLD_TREE,'accepted source tree')
    require(sha(accepted[PROFILE])=='b19bca0a2f5ad193fc782061a2f345bd75b9414408643823b8f7691c89bc150f','accepted effective overlay profile')
    candidate={x['path']:(C/x['path']).read_bytes() for x in members if x['path'].startswith('source/vm/')}
    candidate={n.removeprefix('source/vm/'):b for n,b in candidate.items()}
    require(manifest(candidate)==read(C/'source-manifest.json'),'candidate source manifest')
    require(manifest(candidate)['tree_sha256']==SOURCE_TREE and len(candidate)==146,'candidate source tree')
    require([n for n in accepted if accepted[n]!=candidate[n]]==[PROFILE],'non-profile source change')
    result=accepted[PROFILE].decode()
    for e in read(C/'exact-edits.json'):
        require(result.count(e['before'])==e['occurrences'],'edit count')
        result=result.replace(e['before'],e['after'])
    require(result.encode()==candidate[PROFILE],'full explicit source edits')
    patch=''.join(difflib.unified_diff(accepted[PROFILE].decode().splitlines(True),candidate[PROFILE].decode().splitlines(True),fromfile='accepted/'+PROFILE,tofile='candidate/'+PROFILE))
    require(patch==(C/'source-delta.patch').read_text(),'source patch exact')
    require(len(candidate[PROFILE])==61298 and sha(candidate[PROFILE])=='23c2c169f993795ed7b89a5d4b4cf50946505007868347bff83d41a609e1d617','candidate profile identity')
    query_sources={}
    for mode in ('positive','negative'):
        query=dict(candidate)
        require(query[PROFILE].endswith(b'\n}\n}\n'),'query insertion anchor')
        tail=b'\n'.join((C/n).read_bytes() for n in ('query-layout.inc.rs','query-result-layout.inc.rs',mode+'.inc.rs'))
        query[PROFILE]=query[PROFILE][:-4]+b'\n'+tail+b'}\n}\n'
        query[ACCOUNT]+=b'\n'+(C/'query-account-layout.inc.rs').read_bytes()
        require(manifest(query)==read(C/(mode+'-source-manifest.json')),'query source exact '+mode)
        query_sources[mode]=query
    for n in ('query-layout.inc.rs','query-account-layout.inc.rs'): require((C/n).read_bytes()==(O/n).read_bytes(),'unchanged layout tail '+n)
    require((C/'accepted-result-layout.inc.rs').read_bytes()==(S/'query-result-layout.inc.rs').read_bytes(),'Result original retained')
    return accepted,candidate,query_sources,dict(seal_sha256=SEAL,members=len(members),member_bytes=sum(x['bytes'] for x in members),
        source_members=146,accepted_tree_sha256=OLD_TREE,candidate_tree_sha256=SOURCE_TREE,unchanged_members=145,
        profile_only_lifetime_annotation_and_comment_edits=True,query_manifests_reconstructed=True,source_overlay_custody=True,
        packet_read_only_modes=True,root_release_sha256=sha(RELEASE.read_bytes()),old_cost_acceptance_sha256=sha(COST.read_bytes()))

def compiler_evidence(queries):
    accepted_plan=read(O/'compiler-plan.json');receipts=[]
    for mode,code in (('positive',0),('negative',1)):
        plan=read(C/(mode+'-compiler-plan.json'));r=read(C/('commands/compiler-'+mode+'/receipt.json'))
        require(all(r[k]==v for k,v in plan.items()),'receipt differs from predeclared compiler plan')
        work=C/'owned-work'/mode
        expected_argv=[str(work/'vm/src/lib.rs') if x.endswith('/vm/src/lib.rs') else ('--emit=metadata='+str(work/'query.rmeta')+(',mir='+str(work/'query.mir') if mode=='positive' else '')) if x.startswith('--emit=') else x for x in accepted_plan['argv']]
        require(plan['argv']==expected_argv,'compiler argv other than exact scratch/output change')
        expected_env=dict(accepted_plan['environment'],CARGO_MANIFEST_DIR=str(work/'vm'),TMPDIR=str(work))
        require(plan['environment']==expected_env,'compiler environment other than exact scratch change')
        require(sha(Path(plan['compiler_path']).read_bytes())==plan['compiler_sha256']==accepted_plan['compiler_sha256'],'exact compiler executable bytes')
        require(sha(plan['compiler_version_preimage'].encode())==plan['compiler_version_sha256']==accepted_plan['compiler_version_sha256'],'retained compiler version binding')
        require(plan['source_revision']==accepted_plan['source_revision']=='975b2e3ef25255a882e7476780caa2e844ce928d','frozen origin revision')
        require(plan['candidate_tree_sha256']==SOURCE_TREE and plan['query_tree_sha256']==manifest(queries[mode])['tree_sha256'],'source/compile identity')
        require(plan['runner_sha256']==sha((C/'compile_once.py').read_bytes()),'compiler runner identity')
        require(r['state']=='complete' and r['exit_code']==code and r['compiler_invocations']==1,'compiler terminal status')
        for k in ('child_reaped','owned_group_absent','owned_scratch_removed','expected_terminal_status_observed'):require(r[k],k)
        for k in ('timed_out','cfg_test','codegen','product_test_native_runtime'):require(not r[k],k)
        require(r['retries']==0 and r['child_timeout_seconds']==55 and r['elapsed_seconds']<55,'compiler bounds')
        require(r['owned_pid']==r['owned_pgid'] and r['owned_pid']>0,'exact owned compiler group')
        require(not work.exists() and not (C/'owned-work').exists(),'compiler scratch remains')
        for stream in ('stdout','stderr'):
            data=(C/('commands/compiler-'+mode)/stream).read_bytes()
            require(len(data)==r[stream+'_bytes'] and sha(data)==r[stream+'_sha256'],'retained compiler stream')
        receipts.append(dict(mode=mode,exit_code=code,seconds=r['elapsed_seconds'],compiler_invocations=1,terminal_cleanup_complete=True,
            plan_sha256=sha((C/(mode+'-compiler-plan.json')).read_bytes()),receipt_sha256=sha((C/('commands/compiler-'+mode+'/receipt.json')).read_bytes())))
    return dict(compiler_invocations=2,new_compiler_invocations=0,production_cfg=True,accepted_options_target_environment_preserved=True,
                receipts=receipts,scope='retained compiler-only metadata and MIR; no machine-code/runtime/native qualification')

def layouts_and_probes(old,new,queries):
    rows=[]
    for filename,name in (('query-layout.inc.rs',PROBES[0]),('query-account-layout.inc.rs',PROBES[1]),('query-result-layout.inc.rs',PROBES[2])):
        declarations=(C/filename).read_text()
        names=re.findall(r'^\s+_(\w+): \[u8;',declarations,re.M)
        matches=[x for x in new if x.startswith('fn '+name+'(')]
        require(len(matches)==1,'active layout query body')
        values=[int(x) for x in re.findall(r'_\d+: \[u8; (\d+)\]',matches[0].split('\n',1)[0])]
        require(len(names)==len(values),'layout signature arity')
        rows.extend(dict(query=k,observed=v) for k,v in zip(names,values))
    require(len(rows)==46 and rows[:44]==read(O/'commands/compiler-metadata-mir/layouts.json')['rows'],'44 layouts unchanged')
    require(rows[-2:]==[dict(query='selection_result_size',observed=8),dict(query='selection_result_align',observed=8)],'Result 8/8 layout')
    require(rows==read(C/'layouts.json')['rows'],'producer layout observations')
    probe=[x for x in new if x.startswith('fn scoped_local_binding_compiles_v1(')]
    require(len(probe)==1,'positive probe is active in production cfg')
    probe=norm(probe[0])
    require('-> OuterResultV1 {' in probe and '&_1;' in probe and 'consume_outer_request_v1(move ' in probe,'positive local borrow through consume')
    callers=[x.split('\n',1)[0] for x in new if not x.startswith('fn scoped_local_binding_compiles_v1(') and re.search(r'= scoped_local_binding_compiles_v1(?:[<(])',x)]
    require(not callers,'inert probe has caller')
    source=queries['negative'][PROFILE].decode().splitlines()
    diagnostic=(C/'commands/compiler-negative/stderr').read_text()
    expected=['E0515','E0515','E0506','E0505','E0382']
    sections=re.split(r'(?=^error\[E\d+\]:)',diagnostic,flags=re.M)[1:]
    require([re.match(r'error\[(E\d+)\]',s).group(1) for s in sections]==expected,'negative diagnostic exact order/count')
    expected_lines=['OneFixtureOuterRequestV1 { preexisting: &preexisting }','ImmutableIdentityPreimageV1 { bytes: &bytes, sha256: [0; 32] }','bytes[0] = 1;','drop(bytes);','consume_outer_request_v1(request);']
    spans=[]
    for section,line in zip(sections,expected_lines):
        match=re.search(r'--> ([^\n]+):(\d+):(\d+)\n',section)
        require(match is not None,'missing actual compiler diagnostic span')
        require(match.group(1)==str(C/'owned-work/negative/vm'/PROFILE),'negative span source identity')
        number=int(match.group(2));require(source[number-1].strip()==line,'negative span/source mismatch')
        spans.append(dict(line=number,source=line))
    return dict(rows=rows,original_44_equal=True,result_8_8=True,
        positive_probe_production_MIR_present=True,positive_probe_no_caller=True,positive_probe_normalized_sha256=sha(probe.encode()),
        negative_codes=expected,negative_actual_source_spans=spans,no_new_compiler_needed=True)

def adversarial_controls():
    tests=[]
    def reject(name,action):
        try: action()
        except AssertionError: tests.append(dict(name=name,expected='rejected',observed='rejected'));return
        raise AssertionError('adversarial control incorrectly accepted: '+name)
    base='fn f(_1: FrozenFixtureV1) -> usize {\n    bb0: {\n        _0 = const 7_usize;\n        return;\n    }\n}'
    for name,mutant in [('constant',base.replace('7_usize','8_usize')),('place',base.replace('_0 =','_2 =')),
        ('move',base.replace('const 7_usize','move _1')),('CFG',base.replace('return;','goto -> bb1;')),
        ('drop',base.replace('return;','drop(_1) -> [return: bb1, unwind continue];')),
        ('type',base.replace('usize','u64'))]: reject(name,lambda mutant=mutant:compare_blocks([base],[mutant]))
    literal='fn f() {\n    _0 = const "FrozenFixtureV1::<\'_> // alloc27 '+PATHS[0]+'";\n}'
    for name,mutant in [('literal-type',literal.replace('FrozenFixtureBinding','BadBinding').replace('FrozenFixtureV1','FrozenFixtureV2')),
                         ('literal-path',literal.replace(PATHS[0],PATHS[1])),('literal-comment',literal.replace('// alloc27','// alloc28'))]:
        reject(name,lambda mutant=mutant:compare_blocks([literal],[mutant]))
    old=['fn f() {\n    _0 = const {alloc1: &u8};\n}', 'alloc1 (size: 8, align: 8) {\n    pointer alloc2\n}', 'alloc2 (size: 1, align: 1) {\n    01 │ .\n}']
    # Synthetic replacement is deliberately explicit to avoid replacement overlap.
    new=['fn f() {\n    _0 = const {alloc11: &u8};\n}', 'alloc11 (size: 8, align: 8) {\n    pointer alloc12\n}', 'alloc12 (size: 1, align: 1) {\n    01 │ .\n}']
    require(compare_blocks(old,new)['equality'],'arbitrary allocation-ID rename should pass')
    tests.append(dict(name='arbitrary-not-plus-four-ID-map',expected='accepted',observed='accepted'))
    for name,index,before,after in [('allocation-byte',2,'01','02'),('allocation-extent',2,'size: 1','size: 2'),
        ('allocation-alignment',2,'align: 1','align: 2'),('relocation-target',1,'pointer alloc12','pointer alloc11'),
        ('allocation-ASCII',2,'│ .','│ alloc12'),('allocation-header',2,'size: 1','static: forged, size: 1')]:
        mutation=list(new);mutation[index]=mutation[index].replace(before,after)
        reject(name,lambda mutation=mutation:compare_blocks(old,mutation))
    reject('uncovered-top-level',lambda:parse_mir(base+'\nunclassified_mir_operation\n'))
    reject('unterminated-MIR',lambda:parse_mir(base[:-1]))
    reject('production-extra-body',lambda:compare_blocks([base],[base,base.replace('fn f','fn g')]))
    for name,mutant in [('unrelated-lifetime',base.replace('FrozenFixtureV1',"OtherType<'_>")),
        ('mutable-lifetime',base.replace('FrozenFixtureV1',"&mut FrozenFixtureV1<'_>")),
        ('static-lifetime',base.replace('FrozenFixtureV1',"FrozenFixtureV1<'static>")),
        ('lifetime-variance-callback',base.replace('FrozenFixtureV1',"fn(FrozenFixtureV1<'_>)"))]:
        reject(name,lambda mutant=mutant:compare_blocks([base],[mutant]))
    require(not inert(base.replace('fn f','fn scoped_local_binding_compiles_v1_extra')),'inert prefix overmatch')
    require(not inert(base.replace('fn f','fn consume_outer_request_v1')),'production exclusion')
    tests.append(dict(name='exact-probe-name-only',expected='accepted',observed='accepted'))
    require(norm(base.replace('FrozenFixtureV1',"FrozenFixtureV1<'_>"))==norm(base),'reviewed anonymous lifetime display')
    tests.append(dict(name='reviewed-anonymous-lifetime-display',expected='accepted',observed='accepted'))
    return tests

def derive():
    accepted,candidate,queries,source=custody()
    compiler=compiler_evidence(queries)
    old_gz=(O/'commands/compiler-metadata-mir/query.mir.gz').read_bytes()
    new_gz=(C/'commands/compiler-positive/query.mir.gz').read_bytes()
    require(sha(old_gz)=='a4578f8057adbd11c5cccc2db439db80d8d7dc12adaa2cffcae16ef8c2d2d958','accepted MIR gzip identity')
    require(sha(new_gz)=='394400c084d27694f6706026861cf09a414ed1630b7ccdf875d7dd27d1aba8f7','candidate MIR gzip identity')
    ob=gzip.decompress(old_gz);nb=gzip.decompress(new_gz)
    require(sha(ob)=='822f8f178e71e7ff594158ae08123a2172c3d7f5ee930c6eeba9ce71b6b62ddf','accepted raw MIR identity')
    require(sha(nb)=='9501d7d03a8a1ab793ebc493643828bf049a6e7100bad95a180b6d269251b6a9','candidate raw MIR identity')
    old,oc=parse_mir(ob.decode());new,nc=parse_mir(nb.decode())
    mir=compare_blocks(old,new)
    require((mir['production_functions'],mir['production_other_bodies'],mir['allocations'],mir['production_total'])==(2020,2033,1953,6006),'complete production MIR counts')
    excluded={}
    for label,blocks in (('accepted',old),('candidate',new)):
        items=[x.split('\n',1)[0] for x in blocks if inert(x)]
        excluded[label]=items
        require(not any(not any(x.startswith('fn '+n+'(') or x.startswith(n+'::{constant#') for n in PROBES) for x in items),'probe exclusion scope')
    probe=layouts_and_probes(old,new,queries)
    controls=adversarial_controls()
    failures=read(C/'preliminary-failures.json')
    require(len(failures)==3 and all(x['exit_code']==1 and x['compiler_invocations']==0 for x in failures),'preserved failed host attempts')
    require(read(C/'attempts/initial-mir-comparison.json')['differing_blocks']==1966,'first comparator failure preimage')
    require(read(C/'attempts/second-mir-comparison.json')['differing_blocks']==1,'second comparator failure preimage')
    require(sha((C/'attempts/second-review.py').read_bytes())==read(C/'commands/mir-layout-review/receipt.json')['script_sha256'],'failed comparator script binding')
    require(sha((C/'review.py').read_bytes())==read(C/'commands/mir-layout-review-final/receipt.json')['script_sha256'],'final comparator script binding')
    return dict(schema=1,status='independent-scoped-source-lifetime-and-retained-compiler-evidence-pass',
        source=source,compiler=compiler,mir=dict(mir,accepted_coverage=oc,candidate_coverage=nc,excluded_complete_probe_headers=excluded,
            candidate_raw_sha256=sha(nb),accepted_raw_sha256=sha(ob)),layouts_and_ownership_probes=probe,
        adversarial_controls=controls,preserved_failed_preparation_and_offline_comparators=failures,
        review_scope=dict(source_lifetime_change=True,all_production_MIR_operations_preserved=True,inline_layouts_preserved=True,
            only_frozen_old_source_cost_acceptance=True,recommendation='The old conditional logical-source work and inline-layout counts correspond to this candidate through exhaustive MIR/layout equality; any newsource pricing acceptance must explicitly name this source tree. No operational rebind is authorized.',
            operational_provider=False,root_authority=False,whole_work_storage_pricing_rebind=False,P0_funding=False,
            executable_closure=False,healthy_cleanup=False,native_runtime=False,FieldLog=False,OTA=False,GA=False),
        pending=['actual immutable input provider and complete immutable identity review','native path/native byte body correspondence',
            'whole source work/storage pricing rebind and future provider/launcher backing','actual root policy/account/whole quote/P0 provisioning',
            'whole compiled executable/caller/std closure and healthy cleanup','native runtime/device/UI/capture: paused',
            'FieldLog immutable separate published package, OTA and GA qualification'])

if __name__=='__main__':
    require(sys.argv[1:]==['--derive'],'read-only --derive only')
    print(json.dumps(derive(),sort_keys=True,indent=2))
