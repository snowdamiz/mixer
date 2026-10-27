#!/usr/bin/env python3
"""Independent loader146 source/MIR/cost cross-review; data execution only."""
from pathlib import Path
import collections
import copy
import gzip
import hashlib
import json
import platform
import re
import sys
sys.dont_write_bytecode = True
from evaluator import evaluate, Refused, type_width, MAX
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V=ROOT/'verification'
NEW=V/'swift-guarded-snapshot-loader-work-source146'
OLD=V/'swift-guarded-snapshot-loader-work'
FIX=V/'swift-guarded-snapshot-loader-work-correction'
PRIOR=V/'swift-guarded-snapshot-loader-work-independent'
COMP=V/'swift-guarded-snapshot-host-composition'
DESC=V/'swift-guarded-snapshot-descriptor-rebinding'
checks=[]
inputs={}
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'


def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def check(label,value):
    if not value:raise AssertionError(label)
    checks.append(label)
def read(path):
    b=path.read_bytes();inputs[path.relative_to(ROOT).as_posix()]={'bytes':len(b),'sha256':sha(b)};return b
def load(path):return json.loads(read(path))
def sealed(folder,digest):
    check('seal '+str(folder.relative_to(ROOT)),sha(read(folder/'seal.json'))==digest)
    s=load(folder/'seal.json')
    for m in s['members']:
        b=read(folder/m['path']);check('member '+folder.name+'/'+m['path'],len(b)==m['bytes'] and sha(b)==m['sha256'])
    return s
def counted(b):
    count=int.from_bytes(b[:8],'little');at=8;out=[]
    for _ in range(count):
        n=int.from_bytes(b[at:at+8],'little');at+=8;out.append(b[at:at+n].decode());at+=n
    check('counted preimage fully consumed',at==len(b));return out
def norm(text,prefix):
    # Exact known root relocation only. No source-span/literal/comment erasure.
    text=text.replace(prefix+'/', '<VM>/')
    return '\n'.join(re.sub(r'DefId\(\d+:\d+ ~','DefId(<index> ~',line) if line.lstrip().startswith('//') else line for line in text.splitlines())
def functions(text,prefix):
    result=collections.defaultdict(list)
    for m in re.finditer(r'^fn ',text,re.M):
        end=text.index('\n}\n',m.start())+3
        body=text[m.start():end];head=body.splitlines()[0];name=head[3:head.index('(')]
        result[norm(name,prefix)].append((name,body,m.start(),end))
    return result
def statements(body):
    result=[];active=False
    for line in body.splitlines():
        if re.fullmatch(r'    bb\d+(?: \(cleanup\))?: \{',line):active=True
        elif line=='    }':active=False
        elif active and line.strip():
            code=line.split(' // ',1)[0].strip()
            if code:result.append(code)
    return result
def compiled_constant(text):
    locations=list(re.finditer(r'^const COMPILED: \[Option<&str>; 5\] = \{',text,re.M))
    check('one exact five-key COMPILED definition',len(locations)==1)
    at=locations[0].start();return text[at:text.index('\n}\n',at)+3]
def edge_target(edge):
    target=edge['target']
    for prefix in ('type-slice equality closed callbacks: ','type-option equality closed callbacks: '):
        if target.startswith(prefix):return target[len(prefix):]
    return target


def audit():
    check('root release hash',sha(read(V/'swift-semantic-adapter-root-review/guarded-snapshot-loader-work-source146-independent-release.json'))=='bfac9857159e1ca070e08f6698d8a27d124abf0279e9657b19c1fd5e5104ec30')
    pre=sealed(HERE/'preaccess','f135ff01574b7597fcb467a571e8f912f6661d0740ba5974a453f13efe6010b7')
    check('same independent evaluator as before access',sha(read(HERE/'evaluator.py'))==pre['independent_evaluator_sha256'])
    sealed(NEW,'1aacaaff5795625739811b2502476c22567c2b5a3bcc9fb096e61fa5c147c976')
    sealed(OLD,'0550b44baf9f576d8379e1dd93f89ea9bd5b48ff7367762ae008181d29d2c30c')
    sealed(FIX,'b7142125a8b00f0fbf9ade17d2c7697e42c1ef20d972a995dddfd452e92eff4e')
    sealed(PRIOR/'review','28d14ca65eed39ac22b01f562ccc74178f3ee361c2c0a73d16e0da9b122f4be5')
    sealed(PRIOR/'correction-review','5b15b973477808ff0aeafb00b53006b763d71f5b30d71de5995854aa5193e876')
    sealed(PRIOR/'source146-preaccess','96dd7fc1f0d502816847fc94d46a00917a7e954416f41334bcadc8af70187b75')
    manifest=load(NEW/'source146-manifest.json');host=load(NEW/'host11-manifest.json')
    check('accepted exact146 manifest',manifest==load(COMP/'source-manifest.json') and sha(canonical(manifest['members']))==manifest['tree_sha256']==SOURCE and len(manifest['members'])==146)
    check('exact host11 manifest',host==load(COMP/'host-support-manifest.json') and sha(canonical(host['members']))==host['tree_sha256']=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2' and len(host['members'])==11)
    references=load(NEW/'source-reference-map.json')['members'];source={}
    check('exact reference-map member roster',[{k:r[k] for k in ('path','bytes','sha256')} for r in references]==manifest['members'])
    for r in references:
        check('reference stays in frozen source providers '+r['path'],r['source'].startswith(('verification/swift-guarded-snapshot-funding-implementation/source/vm/','verification/swift-guarded-snapshot-descriptor-rebinding/overlay/vm/','verification/swift-guarded-snapshot-host-composition/overlay/vm/')))
        b=read(ROOT/r['source']);check('actual146 source '+r['path'],len(b)==r['bytes'] and sha(b)==r['sha256']);source[r['path']]=b
    for r in host['members']:
        b=read(V/'swift-real-profile-loader-binding/host'/r['path']);check('host source '+r['path'],len(b)==r['bytes'] and sha(b)==r['sha256'])
    owners=load(OLD/'source-body-ledger.json')['nodes'];owner_changes=[]
    for name,r in owners.items():
        s=r['source'];old_file=read(ROOT/s['path']);relative=s['path'].split('/source/vm/')[-1].split('/overlay/vm/')[-1]
        old=b''.join(old_file.splitlines(True)[s['line']-1:s['end_line']]).strip()
        new=b''.join(source[relative].splitlines(True)[s['line']-1:s['end_line']]).strip()
        check('accepted source owner '+name,len(old)==s['bytes'] and sha(old)==s['sha256'])
        if old!=new:
            check('sole exact source count delta '+name,name=='build' and old.count(b'word(b, 32) != 145')==1 and old.replace(b'word(b, 32) != 145',b'word(b, 32) != 146',1)==new)
            owner_changes.append(name)
    check('all129 source owners one changed',len(owners)==129 and owner_changes==['build'])
    loops=load(OLD/'loop-audit.json')['rows']
    for i,r in enumerate(loops):
        relative=r['path'].split('/source/vm/')[-1].split('/overlay/vm/')[-1]
        check('audited actual loop source retained '+str(i),source[relative].decode().splitlines()[r['line']-1]==r['source_line'])
    check('all40 source loop sites retain bounds',len(loops)==40)

    receipt=load(NEW/'compiler-receipt.json');old_receipt=load(OLD/'compiler-receipt.json')
    preimage=load(NEW/'preimages/manifest.json');binding=load(NEW/'preimages/binding.json')
    keys=('MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256')
    argvraw,envraw=read(NEW/'preimages/argv.bin'),read(NEW/'preimages/environment.bin')
    expected=[sha(read(NEW/'preimages/manifest.json')),sha(argvraw),sha(envraw),preimage['compiler']['sha256'],sha(read(NEW/'compiler-version.stdout'))]
    check('all five fresh nonempty compile keys',all(re.fullmatch(r'[0-9a-f]{64}',v) for v in expected) and dict(zip(keys,expected))==binding['compile_keys']==receipt['compile_identity_keys'])
    check('all argv preimage bytes',counted(argvraw)==receipt['argv'])
    environment=dict(x.split('=',1) for x in counted(envraw));environment.update(zip(keys,expected))
    check('all clean environment preimage bytes',environment==receipt['environment'])
    check('compiler distribution and tools',preimage['distribution']==manifest and preimage['host_support']==host and expected[3]==receipt['compiler_sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0' and receipt['compiler_version'].encode()==read(NEW/'compiler-version.stdout'))
    check('fresh production preopt typed compile flags',receipt['exit_code']==0 and receipt['direct_child_waited'] and receipt['owned_group_absent'] and not receipt['timed_out'] and not receipt['test_overlay'] and not receipt['product_runtime'] and receipt['no_WASI_route'] and receipt['metadata']['bytes']==25578040 and receipt['metadata']['nonempty'] and all(x in receipt['argv'] for x in ('-Zmir-opt-level=0','-Zmir-include-spans=yes','mixer_bootstrap_one_fixture_v1','panic=unwind','overflow-checks=yes','aarch64-apple-darwin')))
    for out in ('stdout','stderr'):
        b=read(NEW/('compiler.'+out));claim=receipt['output'][out];check('compiler '+out+' output custody',sha(b)==claim['sha256'] and len(b)==claim['bytes'])
    whole=gzip.decompress(read(NEW/'whole-source146.mir.gz'))
    check('full76655228B raw MIR custody',len(whole)==76655228 and sha(whole)==receipt['MIR']['raw_sha256']=='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2')
    whole_text=whole.decode()
    old_whole=gzip.decompress(read(OLD/'whole-source.mir.gz')).decode()
    old_selected=gzip.decompress(read(OLD/'selected-definitions.mir.gz')).decode()
    fresh_selected=gzip.decompress(read(NEW/'selected-definitions146.mir.gz')).decode()
    old_prefix=old_receipt['environment']['CARGO_MANIFEST_DIR'];fresh_prefix=receipt['environment']['CARGO_MANIFEST_DIR']
    olddefs=functions(old_selected,old_prefix);freshdefs=functions(whole_text,fresh_prefix);selecteddefs=functions(fresh_selected,fresh_prefix)
    oldx=load(OLD/'mir-extraction.json');newx=load(NEW/'mir-extraction146.json')
    check('complete219 extraction identity',len(olddefs)==len(selecteddefs)==len(oldx['functions'])==len(newx['functions'])==219)
    mapping=[];selected_names=set();new_statements={}
    for old_name,record in oldx['functions'].items():
        key=norm(old_name,old_prefix);old_items=olddefs[key];new_items=freshdefs[key];subset=selecteddefs[key]
        check('one actual retained definition '+key,len(old_items)==len(new_items)==len(subset)==1)
        _,before,_,_=old_items[0];new_name,after,start,end=new_items[0];selected_names.add(new_name)
        check('complete fresh selection byte custody '+key,subset[0][1]==after and whole_text[newx['functions'][new_name]['start']:newx['functions'][new_name]['end']]==after and sha(after.encode())==newx['functions'][new_name]['sha256'])
        a,b=norm(before,old_prefix),norm(after,fresh_prefix)
        expected_body=a.replace('const 145_u64','const 146_u64',1) if key=='parse_build' else a
        check('entire statement type capture projection and comment identity '+key,expected_body==b)
        check('actual selected record owner and type/call shape '+key,newx['functions'][new_name]['owner']==record['owner'] and norm(canonical(newx['functions'][new_name]['locals']).decode(),fresh_prefix)==norm(canonical(record['locals']).decode(),old_prefix) and norm(canonical(newx['functions'][new_name]['calls']).decode(),fresh_prefix)==norm(canonical(record['calls']).decode(),old_prefix))
        ss=statements(after);new_statements[new_name]=ss
        expected_statements=[x.replace('const 145_u64','const 146_u64',1) for x in record['statements']] if key=='parse_build' else record['statements']
        check('independently extracted full statement sequence '+key,norm(canonical(ss).decode(),fresh_prefix)==norm(canonical(expected_statements).decode(),old_prefix))
        mapping.append({'identity':key,'owner':record['owner'],'old_sha256':sha(before.encode()),'new_sha256':sha(after.encode()),'normalized_equal':a==b,'count_only':a!=b})
    check('no extra/missing selected identities',selected_names==set(newx['functions']))
    check('exact218 full bodies and one count body',sum(r['normalized_equal'] for r in mapping)==218 and [r['identity'] for r in mapping if r['count_only']]==['parse_build'])
    const_before,const_after=compiled_constant(old_whole),compiled_constant(whole_text)
    old_values=re.findall(r'= const "([0-9a-f]{64})";',const_before);new_values=re.findall(r'= const "([0-9a-f]{64})";',const_after)
    check('five actual identity bytes retain Some/hex branches',old_values==[old_receipt['environment'][k] for k in keys] and new_values==expected and const_before.count('::Some(')==const_after.count('::Some(')==5)
    rewritten=const_before
    for a,b in zip(old_values,new_values):rewritten=rewritten.replace(a,b)
    check('only explicitly bound constant bytes change',norm(rewritten,old_prefix)==norm(const_after,fresh_prefix))
    build=new_statements['parse_build'];guard=[x for x in build if '146_u64' in x]
    check('u64 count is only equality predicate',guard==['_15 = Ne(move _16, const 146_u64);'] and build[build.index(guard[0])+1]=='switchInt(move _15) -> [0: bb9, otherwise: bb8];')
    uses=[x for x in build if re.search(r'\b_15\b',x) and not x.startswith(('StorageLive','StorageDead'))]
    check('count result cannot drive loops allocations hashes reads or credits',uses==guard+['switchInt(move _15) -> [0: bb9, otherwise: bb8];'])
    guard_truth=[{'count':n,'old_refuses':n!=145,'new_refuses':n!=146} for n in (0,1,144,145,146,147,MAX)]
    check('count semantics differs only145/146', [r['count'] for r in guard_truth if r['old_refuses']!=r['new_refuses']]==[145,146])

    old_ledger=load(FIX/'mir-ledger.json');ledger=load(NEW/'mir-ledger.json')
    for k in old_ledger:
        if k not in ('nodes','source_tree_sha256','parent_mir_sha256'):
            check('all static closure shape roots primitive tables '+k,norm(canonical(old_ledger[k]).decode(),old_prefix)==norm(canonical(ledger[k]).decode(),fresh_prefix))
    new_by_key={norm(n,fresh_prefix):(n,r) for n,r in ledger['nodes'].items()}
    for n,r in old_ledger['nodes'].items():
        key=norm(n,old_prefix);fresh_name,fresh_row=new_by_key[key]
        check('actual mapped MIR body fingerprint '+key,fresh_row['mir_sha256']==newx['functions'][fresh_name]['sha256'])
        for term in r:
            if term!='mir_sha256':check('all unchanged actual cost terms '+key+' '+term,norm(canonical(r[term]).decode(),old_prefix)==norm(canonical(fresh_row[term]).decode(),fresh_prefix))
    check('exact graph identity closure',len(ledger['nodes'])==len(new_by_key)==219 and ledger['source_tree_sha256']==SOURCE and ledger['parent_mir_sha256']==sha(whole))
    callbacks=[]
    for name,ss in new_statements.items():
        targets=[]
        for code in ss:
            match=re.search(r'(<.* as PartialEq.*>::(?:eq|ne))\(',code)
            if match and re.search(r'\bType\b',match[1]):targets.append(match[1])
        for target in targets:
            width=type_width(target);edges=[e for e in ledger['nodes'][name]['calls'] if edge_target(e)==target]
            check('actual receiver-specific Type callback '+name+target,edges and all(e['multiplicity']==width for e in edges))
            callbacks.append({'function':name,'target':target,'width':width})
    slices=[r for r in callbacks if r['width']==128]
    check('two actual resolver slice callbacks128',len(slices)==2 and all(ledger['nodes'][r['function']]['owner']=='wresolve' for r in slices))
    eq_nodes={e['callee'] for r in slices for e in ledger['nodes'][r['function']]['calls'] if edge_target(e)==r['target']}
    check('actual authored Type equality104',len(eq_nodes)==1 and all(ledger['nodes'][n]['local_actions']==104 and not ledger['nodes'][n]['calls'] and not ledger['nodes'][n]['native'] for n in eq_nodes))
    geometry=load(NEW/'cap-geometry.json');baseline=evaluate(geometry,ledger)
    check('independent checked cap quote',baseline=={'wrapper':97394558768720,'coefficient':1748020339,'W_loader':895083809874789059,'visited':219,'operational_grant':False})
    grid=[]
    for b in (0,1,2,31,128,4096,1000000,511999999,512000000):
        for scale in (0,1,2):
            g=dict(geometry,credits=b)
            if scale==0:g.update(source=0,validator_source=0,build=0,session=0,executable=0,metadata=0,scratch=0)
            if scale==1:g.update(source=17,validator_source=17,build=4097,session=13,executable=4096,metadata=32,scratch=16)
            result=evaluate(g,ledger);prior=evaluate(g,old_ledger)
            check('independent varied geometry/credit numeric '+str((b,scale)),result==prior)
            grid.append({'B':b,'scale':scale,**result})
    bad=copy.deepcopy(ledger)
    for n,r in bad['nodes'].items():
        if r['owner']=='wresolve':
            for e in r['calls']:
                if edge_target(e)=='<&[Type] as PartialEq>::ne':e['multiplicity']=1
    original_bad=evaluate(geometry,bad)
    check('restoring rejected callbacks reproduces old defect',original_bad['coefficient']==1747993923 and original_bad['W_loader']==895070284882762643 and baseline['W_loader']-original_bad['W_loader']==13524992026416)
    negatives=[]
    for kind in ('unknown-callee','cycle','local-omission','zero-callback','overflow'):
        altered=copy.deepcopy(ledger);root=altered['roots']['loader'];node=altered['nodes'][root]
        if kind=='unknown-callee':node['calls'].append({'callee':'unreviewed','multiplicity':1,'target':'unreviewed'})
        elif kind=='cycle':node['calls'].append({'callee':root,'multiplicity':1,'target':'cycle'})
        elif kind=='local-omission':node['local_actions']-=1
        elif kind=='zero-callback':node['calls'][0]['multiplicity']=0
        elif kind=='overflow':node['native'].append({'count':MAX,'extent':MAX})
        try:evaluate(geometry,altered)
        except (Refused,KeyError):check('negative graph refusal '+kind,True);negatives.append(kind)
        else:raise AssertionError('negative accepted '+kind)
    cleanup=load(NEW/'cleanup.json')
    check('frozen owned cleanup scope',cleanup['owned_scratch_removed'] and cleanup['owned_compiler_group_absent'] and cleanup['one_whole_source_compiler_direct_child_waited'] and cleanup['removed']=={'files':148,'bytes':121910262} and cleanup['full_MIR_losslessly_archived'] and cleanup['typed_metadata_nonempty_hashed_then_removed'] and not cleanup['global_process_inventory'] and not cleanup['other_projects_touched'] and not cleanup['product_runtime'] and cleanup['native_UI_capture_simulator_emulator_instances_started']==0)
    prior_values=load(PRIOR/'review/projected-value-ledger.json');native=load(PRIOR/'review/native-audit.json');credit=load(PRIOR/'review/graph-and-controls.json')
    check('compose settled actual-site proofs only after mapping',len(prior_values['all_dereference_statements'])==1456 and len(prior_values['projected_stores'])==37 and credit['partition_cases']==972 and native['checks_passed']==320)
    return {'schema':1,'status':'independently-accepted-bounded-source146-loader-work-component-only','source_tree_sha256':SOURCE,'source_members':146,'host_members':11,'baseline':baseline,'mapped_full_definitions':219,'identical_full_definitions':218,'count_only_definition':'parse_build','source_owners':129,'source_owner_changes':owner_changes,'loop_sites':40,'composed_actual_dereferences':1456,'composed_projected_stores':37,'composed_credit_partitions':972,'composed_native_controls':320,'generic_reference_base_claim_accepted':False,'native_slack_reassigned':False,'mapping':mapping,'Type_callbacks':callbacks,'count_guard':{'actual_operation':guard,'only_nonlifetime_uses':uses,'truth_control':guard_truth,'cardinality_driving':False},'identity_bytes':[{'key':k,'old':a,'new':b,'bytes':64} for k,a,b in zip(keys,old_values,new_values)],'credit_geometry_grid':grid,'rejected_callback_countermodel':original_bad,'negative_controls':negatives,'normalization':['exact bound old/new compiler VM roots only','numeric DefId crate/index only on compiler comment lines; symbol/crate hash retained','no source-span, literal, instruction, type or general comment erasure'],'new_compiler_or_product_or_native_execution':False,'preaccess_before_candidate_read':True,'operational_grant':False,'genuine_fixture_qualified':False,'whole_host_quote_or_GA':False,'pending':['immutable actual fixture/executable/build/session/process/caller binding','complete preexisting P0 funding/work/storage','P1 caller setup and all P2-P5 work/storage/backing/retirement','selected policy, quote and actual enforcement','native FieldLog OTA customer operational GA'], 'python':platform.python_version()}


def main():
    report=audit();report['checks']=len(checks)
    outputs={'review.json':report,'checks.json':{'checks':len(checks),'labels':checks},'input-custody.json':{'files':inputs}}
    for name,data in outputs.items():
        expected=(json.dumps(data,sort_keys=True,indent=2)+'\n').encode()
        if '--check-only' in sys.argv:
            if (HERE/name).read_bytes()!=expected:raise AssertionError('frozen output mismatch '+name)
        else:(HERE/name).write_bytes(expected)
    print(json.dumps({'passed':True,'checks':len(checks),'status':report['status'],'source_tree_sha256':SOURCE,'mode':'check-only' if '--check-only' in sys.argv else 'review'}))
if __name__=='__main__':main()
