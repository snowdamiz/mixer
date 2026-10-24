#!/usr/bin/env python3
"""Independent read-only host evidence audit; no compiler, VM, or test body."""
from pathlib import Path
import collections, datetime, gzip, hashlib, json, os, re, shutil, subprocess, sys, tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
P = ROOT / 'verification/swift-reactor-lifecycle-accounting'
BASE = '3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3'
FINAL = '0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f'
DISC = '779f94a6599e43a12674a7d3b20743e5df1bb23249130ed5af8453b1dd868832'
SEAL = '02b53f531a4cb4852cc7e99104d13bb09e969f9d6b018c4d5d8fd6cd0d3dbbdd'
PREFIX = 'experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::'
ROLES = {'source', 'argument', 'returned', 'caller'}
sha = lambda b: hashlib.sha256(b).hexdigest()
enc = lambda x: (json.dumps(x, sort_keys=True, indent=2) + '\n').encode()
read = lambda path: json.loads(path.read_bytes())
save = lambda name, value: (OUT / name).write_bytes(value if isinstance(value, bytes) else enc(value))

def manifest(folder):
    return {str(f.relative_to(folder)): sha(f.read_bytes()) for f in sorted(folder.rglob('*')) if f.is_file()}

def normalize(value):
    if isinstance(value, str):
        return re.sub(r'DefId\(\d+:\d+ ~ ', 'DefId(<session> ~ ', value)
    if isinstance(value, list): return [normalize(x) for x in value]
    if isinstance(value, dict): return {k: normalize(v) for k, v in value.items()}
    return value

def run(label, argv):
    begin = datetime.datetime.now(datetime.timezone.utc).isoformat()
    done = subprocess.run(argv, cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    save(label + '.stdout', done.stdout); save(label + '.stderr', done.stderr)
    row = {'label': label, 'argv': argv, 'cwd': str(ROOT), 'startedUTC': begin,
           'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'exitCode': done.returncode, 'stdoutSHA256': sha(done.stdout), 'stderrSHA256': sha(done.stderr)}
    save(label + '.command.json', row)
    assert done.returncode == 0, row
    return done.stdout.decode()

def snapshot(label):
    sealed = read(P/'seal.json')
    assert sha((P/'seal.json').read_bytes()) == SEAL
    actual = manifest(P); del actual['seal.json']
    assert actual == sealed['files'] and len(actual) == 1905
    assert sha(enc(actual)) == sealed['closureSHA256'] == 'aafd88cf053743e2560788bfb877adbabdbdece86f3fb77e972baf100dc2dd2d'
    base, final = read(P/'baseline-manifest.json'), read(P/'candidate-final-manifest.json')
    assert manifest(P/'baseline') == base and sha(enc(base)) == BASE and len(base) == 130
    assert manifest(P/'candidate') == final and sha(enc(final)) == FINAL and len(final) == 132
    assert all(sha((ROOT/'vm'/f).read_bytes()) == h for f, h in base.items())
    assert {f for f,h in final.items() if base.get(f) != h} == {
        'src/experimental_swift_reactor/lifecycle.rs', 'src/experimental_swift_reactor/lifecycle_tests.rs',
        'src/experimental_swift_reactor/memory_growth_operations.rs'}
    inputs = read(P/'input-bindings.json')
    for f,h in inputs.items(): assert sha((ROOT/f).read_bytes()) == sha((P/'inputs'/f).read_bytes()) == h
    assert sha((ROOT/'docs/swift-reactor-lifecycle-accounting.md').read_bytes()) == read(P/'receipt.json')['documentSHA256']
    result = {'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'sealSHA256': SEAL,
              'packetFiles': len(actual), 'packetClosure': sealed['closureSHA256'], 'baselineClosure': BASE,
              'candidateClosure': FINAL, 'baselineLiveExact': True, 'inputBindingsExact': True}
    save(label + '.json', result)
    return result

def query(config, discovery=False):
    q = read(P/('discovery-final-preinstall' if discovery else '')/('exact-query-'+config+'.json'))
    assert q['exitCode'] == 0 and q['sourceClosure'] == (DISC if discovery else FINAL)
    folder = P/q['attempt']
    raw = gzip.decompress((folder/'exact-layouts.jsonl.gz').read_bytes())
    assert sha(raw) == q['sha256'] and len(raw) == q['bytes']
    records = [json.loads(line) for line in raw.splitlines()]
    assert len(records) == q['records']
    assert sha(enc(read(folder/'source-manifest.json'))) == q['sourceClosure']
    command = read(folder/'command.json')
    assert command['exitCode'] == 0 and command['sourceUnchanged'] and not command['remainingGroup']
    return q, records

def indexed(records):
    bodies, locals_, constants, funcs, declarations, graphs = {}, {}, collections.defaultdict(list), collections.defaultdict(list), {}, {}
    for r in records:
        k = (r.get('path'),r.get('promoted'))
        if r['kind'] == 'body': assert k not in bodies; bodies[k] = r
        elif r['kind'] == 'local': assert (*k,r['local']) not in locals_; locals_[(*k,r['local'])] = r
        elif r['kind'] == 'constant-operand': constants[k].append(r)
        elif r['kind'] == 'FnDef': funcs[k].append(r)
        elif r['kind'] == 'declaration': assert r['path'] not in declarations; declarations[r['path']] = r
        elif r['kind'] == 'type-graph': graphs[r['identity']] = r['graph']
    return bodies,locals_,constants,funcs,declarations,graphs

def audit_annotations(cfg, q, records, tables):
    bodies,ls,cs,fs,ds,graphs = tables
    parent = ds[PREFIX+'LifecyclePermanentPositions']; variant = parent['layout']['variants'][0]
    fields = dict(zip(variant['fieldNames'],variant['fields']))
    annotations = {}; retained = {}
    proofs = json.loads(gzip.decompress((P/'annotation-const-proofs.json.gz').read_bytes()))
    for proof in proofs:
        if proof['config'] == cfg: retained[(proof['body']['path'],proof['body']['promoted'])] = proof
    for key,b in bodies.items():
        # Candidate set is derived by the actual parent field relation, then the
        # complete body and local/operand records are checked individually.
        path,promoted = key
        if not path.startswith(PREFIX+'LifecyclePermanentPositions::'): continue
        suffix = path[len(PREFIX+'LifecyclePermanentPositions::'):]
        fieldname,marker = suffix.rsplit('::',1)
        assert marker == '{constant#0}' and fieldname in fields and promoted is None
        field = fields[fieldname]; graph = graphs[field['identity']]
        assert graph['kind'] == 'Ref' and graph['pointee']['kind'] == 'Array' and graph['pointee']['length'] == 6
        localrows = [v for k,v in ls.items() if k[:2] == key]
        assert len(localrows) == 1 and localrows[0]['local'] == 0
        assert localrows[0]['layout']['identity'] == 'usize' and localrows[0]['layout']['bytes'] == 8
        assert len(cs[key]) == 1 and cs[key][0]['layout']['identity'] == 'usize' and not fs[key]
        # Complete MIR grammar for these CTFE bodies, with only source comments removed.
        lines = [x.split('//',1)[0].strip() for x in b['mir'].splitlines()]
        lines = [x for x in lines if x]
        assert lines[1:] == ['let mut _0: usize;', 'bb0: {', '_0 = const 6_usize;', 'return;', '}', '}'], (key, lines)
        proof = retained[key]
        assert proof['body'] == b and proof['exactParentDeclaration'] == parent['path'] and proof['parentDefPathHash'] == parent['defPathHash']
        assert proof['fieldName'] == fieldname and proof['actualParentFieldLayout'] == field and proof['actualParentFieldGraph'] == graph
        assert proof['actualReturnLocal'] == localrows[0] and proof['actualConstantOperand'] == cs[key][0]
        assert proof['actualLength'] == 6 and proof['runtimeByteCredit'] == 0 and proof['noFunctionItemOrCall']
        assert proof['querySHA256'] == q['sha256']
        annotations[key] = {'field':fieldname,'bodySHA256':sha(b['mir'].encode()),'parentFieldIdentity':field['identity']}
    assert set(annotations) == set(retained) and len(annotations) == 48
    return annotations

def audit_roles():
    old = read(P/'inventory.json'); new = read(P/'inventory-final.json')
    oldby = {r['field']:r for r in old}; newby = {r['field']:r for r in new}
    assert len(oldby) == len(newby) == 21364 and set(oldby) == set(newby)
    finite = read(P/'discovery-final-preinstall/finite-proposal.json'); extra = read(P/'additional-finite-proposal.json')
    assert len(finite) == 248 and len(extra) == 8
    assert sha(enc(finite)) == 'd2e3a767f9381edb06df667239562d104a1666c7c0cb503d818f83fa70e59d77'
    assert (P/'finite-proposal.json').read_bytes() == (P/'discovery-final-preinstall/finite-proposal.json').read_bytes()
    assert sha(enc(extra)) == 'eafa3a37fd3676a61eab25fb8f8838bdcf1369a4bbc618209cb953073a2df557'
    selected = {r['field'] for r in finite + extra}; extras = {r['field'] for r in extra}
    assert len(selected) == 256
    assert {r['field'] for r in new if r['method'].startswith('finite-')} == selected
    for r in extra:
        assert r['layout']['bytes'] == r['layout']['alignment'] == 8 and 'RawVecInner' in r['mirType']
        assert r['config'] in ['swift-release-unit','all-release-unit'] and r['local'] == 18
    position_changes = 0; body_changes = 0; count_bodies = 0; annotations_total = 0; fnitems = 0; witnesses = 0
    contexts = []; proof_rows = []
    for cfg in [f+'-'+p+'-'+u for f in ['swift','all'] for p in ['debug','release'] for u in ['production','unit']]:
        qo,ro = query(cfg,True); qn,rn = query(cfg); tb = indexed(rn); bo,lo,co,fo,do,go = indexed(ro)
        bn,ln,cn,fn,dn,gn = tb
        annotations = audit_annotations(cfg,qn,rn,tb); annotations_total += len(annotations)
        runtime = {k:v for k,v in bn.items() if k not in annotations}
        assert set(runtime) == set(bo)
        count_bodies += len(runtime)
        body_changes += sum(sha(bo[k]['mir'].encode()) != sha(v['mir'].encode()) for k,v in runtime.items())
        current = [r for r in new if r['config'] == cfg]
        grouped = collections.defaultdict(list)
        for r in current:
            key = (r['body'],r['promoted']); body = runtime[key]
            assert r['querySHA256'] == qn['sha256'] and r['bodyDefPathHash'] == body['defPathHash'] and r['bodySHA256'] == sha(body['mir'].encode())
            assert r['ownerClass'] == ('active' if '::execute_phase' in r['body'] or '::tests::runtime_' in r['body'] else 'permanent')
            assert r['unitOnly'] == cfg.endswith('-unit') and r['position'] in ROLES
            if r['kind'] in ['canonical','authored-alias']:
                actual = ln[(*key,r['local'])]
                assert r['sourceInfo'] == actual['sourceInfo']
                if r['kind'] == 'canonical': assert r['binding'] == '_'+str(r['local'])
                else: assert (r['binding'],'_'+str(r['local'])) in re.findall(r'debug (\w+) => (_\d+);',body['mir'])
                layout = actual['layout']
            elif r['kind'] == 'constant-operand':
                index = int(r['binding'].rsplit(':',1)[1]); actual = cn[key][index]
                assert r['binding'] == actual['location']+':'+str(index) and r['source'] == actual['constant']; layout = actual['layout']
            else:
                assert r['kind'] == 'captured-alias' and r['local'] == 1
                capture = ln[(*key,1)]['captureLayout']; field = capture['fields'][r['capture']]
                assert r['binding'] == 'capture_'+str(r['capture'])
                layout = {'type':field['type'],'identity':field['identity'],'bytes':field['bytes'],'alignment':field['alignment'],
                          'fields':[],'variants':[],'captureFieldOf':capture['identity'],'captureOffset':field['offset']}
            assert r['layout'] == layout and r['actualIdentity'] == layout['identity'] and r['actualType'] == layout['type']
            a = oldby[r['field']]
            assert a['querySHA256'] == qo['sha256'] and a['bodySHA256'] == sha(bo[key]['mir'].encode())
            assert a['actualIdentity'] == r['actualIdentity'] and normalize(a['layout']) == normalize(r['layout'])
            for k in ['config','body','promoted','binding','kind','position','mirType','ownerClass']: assert a[k] == r[k]
            if r['field'] in extras: assert a['method'] == 'exact-typed' and r['method'] == 'finite-proposed-private-std'
            else: assert a['method'] == r['method']
            position_changes += a.get('sourceInfo') != r.get('sourceInfo')
            grouped[(*key,r['kind'],r['binding'])].append(r)
        assert all(len(v)==4 and {r['position'] for r in v} == ROLES for v in grouped.values())
        # Exact completeness over compiler callback indexes, independent of field-name generation.
        assert {k[:2]+('canonical','_'+str(k[2])) for k in ln if k[:2] in runtime} == {k for k in grouped if k[2]=='canonical'}
        assert {(k[0],k[1],'constant-operand',v['location']+':'+str(i)) for k in runtime for i,v in enumerate(cn[k])} == {k for k in grouped if k[2]=='constant-operand'}
        assert {(k[0],k[1],'authored-alias',a) for k,v in runtime.items() for a,_ in re.findall(r'debug (\w+) => (_\d+);',v['mir'])} == {k for k in grouped if k[2]=='authored-alias'}
        expected_captures = {(k[0],k[1],'captured-alias','capture_'+str(f['index'])) for k in runtime if (*k,1) in ln and ln[(*k,1)]['captureLayout'] is not None for f in ln[(*k,1)]['captureLayout']['fields']}
        assert expected_captures == {k for k in grouped if k[2]=='captured-alias'}
        for k,items in fn.items():
            if k not in runtime: continue
            for item in items:
                assert item['layout']['bytes'] == 0 and item['layout']['identity'].startswith('FnDef(')
                fnitems += 1
        fields = {}
        for name,d in dn.items():
            if name.rsplit('::',1)[-1] not in ['LifecycleActivePositions','LifecyclePermanentPositions','LifecycleNeverActivePositions','LifecycleNeverPermanentPositions']: continue
            v = d['layout']['variants'][0]
            for name,f in zip(v['fieldNames'],v['fields']): assert name not in fields; fields[name] = f
        installed = {r['field'] for r in new if not r['method'].startswith('finite-') and (not r.get('unitOnly',False) or cfg.endswith('-unit'))}
        assert set(fields) == installed
        for r in current + [r for r in new if r['config']=='source']:
            if r['field'] in selected: continue
            f = fields[r['field']]
            if r['config'] != 'source':
                assert f['identity'] == r['actualIdentity'] and f['bytes'] == r['layout']['bytes'] and f['alignment'] == r['layout']['alignment']
            else:
                assert f['type'] != '()' and f['bytes'] > 0
            witnesses += 1
        contexts.append({'config':cfg,'discoveryQuerySHA256':qo['sha256'],'finalQuerySHA256':qn['sha256'],
                         'runtimeBodies':len(runtime),'annotationBodies':len(annotations),'roles':len(current),
                         'allLocalsConstantsAliasesCapturesHaveFourRoles':True,'installedTypedFields':len(fields)})
        proof_rows += [{'config':cfg,**v,'body':k[0],'promoted':k[1]} for k,v in annotations.items()]
    assert count_bodies == 268 and body_changes == 96 and position_changes == 7216 and annotations_total == 384 and witnesses == 21416
    numeric = read(P/'numeric-positions.json'); ends = collections.defaultdict(int)
    assert len(numeric) == 256 and {r['field'] for r in numeric} == selected
    for r in numeric:
        target = newby[r['field']]; assert r['actualIdentity'] == target['actualIdentity'] and normalize(r['layout']) == normalize(target['layout'])
        size,align = r['layout']['bytes'],r['layout']['alignment']; component=r['component']
        assert r['relativeOffset'] == (ends[component]+align-1)//align*align
        assert r['exclusiveEnd'] == r['relativeOffset']+size; ends[component]=r['exclusiveEnd']
    assert dict(ends) == {'permanent-production':320,'permanent-unit':880,'active-unit':320}
    save('annotation-audit.json',proof_rows)
    save('raw-role-audit.json',{'contexts':contexts,'runtimeBodies':count_bodies,'roles':len(new),'bodySHAChanges':body_changes,
         'sourceInfoChanges':position_changes,'actualTypeOrLayoutChanges':0,'runtimePositionAddRemove':0,'annotations':annotations_total,
         'typedAndNeverWitnesses':witnesses,'actualZeroByteFnDefRecords':fnitems,'finitePositions':256,'finiteComponentEnds':dict(ends)})

def audit_pairs():
    pairs=read(P/'paired-layouts.json'); assert len(pairs)==8
    results=[]
    for pair in pairs:
        owners={}; totals={}
        for label,closure in [('baseline',BASE),('candidate',FINAL)]:
            row=pair[label]; folder=P/row['attempt']; projection=read(folder/'source-projection.json')
            assert row['sourceClosure']==projection['originalClosure']==closure
            original=projection['originalManifest']; assert sha(enc(original))==closure
            assert original==read(P/('baseline-manifest.json' if label=='baseline' else 'candidate-final-manifest.json'))
            packed={}
            with tarfile.open(folder/'source.tar.gz') as archive:
                for member in archive.getmembers(): assert member.isfile(); packed[member.name]=archive.extractfile(member).read()
            assert {f:sha(b)for f,b in packed.items()}==projection['probeManifest']
            for f,h in original.items():
                source=(P/label/f).read_bytes()
                if f==projection['source']:
                    assert packed[f].startswith(source) and sha(source)==projection['prefixSHA256']
                    suffix=packed[f][len(source):]; assert sha(suffix)==projection['appendedSHA256']
                    assert suffix.startswith(b'\n// Metadata-only compiler layout projection. Never instantiated.\n#[allow(dead_code)]\nstruct LifecycleFormulaProbe {\n')
                else: assert packed[f]==source
            assert set(packed)==set(original)
            raw=gzip.decompress((folder/'exact-layouts.jsonl.gz').read_bytes()); assert sha(raw)==row['querySHA256']
            records=[json.loads(x)for x in raw.splitlines()]; declarations={r['path']:r for r in records if r['kind']=='declaration'}
            probe=next(v for k,v in declarations.items()if k.endswith('::LifecycleFormulaProbe'))['layout']['variants'][0]
            actual={n:f['bytes']for n,f in zip(probe['fieldNames'],probe['fields'])};assert actual==row['totals'];totals[label]=actual
            owners[label]={k:v for k,v in declarations.items()if '::lifecycle::'not in k and not k.endswith('::LifecycleFormulaProbe')}
            assert owners[label]==row['owners']
        a,b=totals['baseline'],totals['candidate']
        assert set(owners['baseline'])==set(pair['comparisons'])
        for name,left in owners['baseline'].items(): assert normalize(left['layout'])==normalize(owners['candidate'][name]['layout']),name
        for key in ['original_growth_active','original_growth_permanent','frame_frozen_active','frame_frozen_permanent','ticket_max']:assert a[key]==b[key]
        assert a['ticket_max']==b['ticket_max']==86
        for total,addition in [('header','lifecycle_permanent'),('frame','lifecycle_active'),('growth_permanent','lifecycle_permanent'),('growth_active','lifecycle_active')]:assert b[total]==a[total]+b[addition]
        assert (b['header'],b['frame'])==((11694120,31278808)if pair['context'].endswith('-unit')else(6464992,15847432))
        results.append({'context':pair['context'],'baselineOwners':len(owners['baseline']),'allOriginalFullLayoutsExact':True,
                        'baselineQuerySHA256':pair['baseline']['querySHA256'],'candidateQuerySHA256':pair['candidate']['querySHA256'],
                        'allSourcePrefixesExact':True,'totals':b})
    save('paired-layout-audit.json',results)

def audit_commands():
    commands=read(P/'command-index.json');assert len(commands)==57
    failures=[r for r in commands if r['exitCode']!=0];assert len(failures)==4
    lists=read(P/'test-inventories.json');assert len(lists)==4
    for r in lists:
        folder=P/r['attempt']; output=gzip.decompress((folder/'list-stdout.gz').read_bytes()).decode()
        tests=[line[:-6]for line in output.splitlines()if line.endswith(': test')]
        assert r['argv'][1:]==['--list'] and r['sourceClosure']==FINAL and r['testBodiesExecuted']==r['vmExecutions']==0
        assert len(tests)==r['allTestCount']==(335 if r['context'].startswith('swift')else 365)
        assert [t for t in tests if '::swift_lifecycle_sl'in t]==r['lifecycleTests'] and len(r['lifecycleTests'])==23
        artifacts=read(folder/'artifacts.json'); match=[a for a in artifacts if a['sha256']==r['executableSHA256']]
        assert len(match)==1 and sha(gzip.decompress((folder/match[0]['path']).read_bytes()))==r['executableSHA256']
        assert read(folder/'list-cleanup.json')['removed']
    clippy=[r for r in commands if r['label'].startswith('production-clippy-')];assert len(clippy)==2 and all(r['exitCode']==0 and r['argv'][-2:]==['-D','warnings']for r in clippy)
    formatted=[r for r in commands if r['label']=='new-source-formatting-check'];assert len(formatted)==1 and formatted[0]['exitCode']==0
    coverage=read(P/'authored-coverage.json');assert coverage['testsExecuted']==0 and len(coverage['rows'])==23
    assert 'unsupported' in next(r for r in coverage['rows']if r['id']=='SL12')['remaining']
    assert (P/'planned-matrix-unchanged.json').read_bytes()==(ROOT/'verification/swift-reactor-lifecycle-contract/matrix.json').read_bytes()
    save('command-and-coverage-audit.json',{'commands':57,'preservedFailures':4,'listOnlyBinaries':4,'lifecycleTestsEach':23,
         'producerTestBodiesExecuted':0,'independentTestBodiesExecuted':0,'productionClippy':2,'newFileFormatCheck':1,
         'entireCoverageLedgerPreserved':True,'allRowsRemainPartlyAuthoredUnqualified':True,'SL12GuestTableMutationUnsupportedUnrun':True})

def main():
    snapshot('before')
    versions={}
    for name,argv in [('python',[sys.executable,'--version']),('rustc',['/opt/homebrew/opt/rustup/bin/rustc','-vV']),('cargo',['/opt/homebrew/opt/rustup/bin/cargo','-V']),('rustfmt',['/opt/homebrew/opt/rustup/bin/rustfmt','--version']),('uname',['/usr/bin/uname','-a'])]:
        versions[name]={'argv':argv,'stdout':run('version-'+name,argv),'executableSHA256':sha(Path(argv[0]).read_bytes())}
    save('tool-versions.json',versions)
    run('producer-live-replay-before',[sys.executable,'-B',str(P/'verify.py'),'--live'])
    audit_roles();audit_pairs();audit_commands()
    run('producer-live-replay-after',[sys.executable,'-B',str(P/'verify.py'),'--live'])
    snapshot('after')
    save('execution.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'scriptSHA256':sha(Path(__file__).read_bytes()),'sourceCandidateClosure':FINAL,'success':True,
         'independentCompilerCommands':0,'independentVMExecutions':0,'independentTestBodiesExecuted':0,
         'nativeInstancesCreated':0,'scratchCreated':False,'scratchCleanup':'No scratch, target, overlay, executable or native instance created.'})
    print(json.dumps({'verified':True,'runtimeBodies':268,'rolePositions':21364,'annotationsIndividuallyBound':384,
                      'pairedCompilerLayouts':16,'vmExecutions':0,'testBodiesExecuted':0},indent=2))

if __name__=='__main__':main()
