#!/usr/bin/env python3
"""Fresh source/context-isolated metadata replay. Never invokes guest/WASI."""
from pathlib import Path
import collections, datetime, gzip, hashlib, json, os, re, shutil, subprocess, tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT/'verification/swift-host-dispatch-contract'
enc=lambda value:(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
sha=lambda data:hashlib.sha256(data).hexdigest()
def save(name,value):
    p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(enc(value))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def manifest(vm):
    paths=[vm/'Cargo.toml',vm/'Cargo.lock']
    for name in ['src','tests','include']:paths+=sorted(p for p in (vm/name).rglob('*') if p.is_file())
    return {str(p.relative_to(vm)):sha(p.read_bytes()) for p in paths}
def digest(value):return sha(enc(value))
def command(name,argv,vm,expected,environment=None,cwd=None):
    out=HERE/'commands'/name;out.mkdir(parents=True,exist_ok=False)
    before=manifest(vm);assert digest(before)==expected,(name,'source-before')
    env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
    for key in ['RUSTFLAGS','RUSTC_BOOTSTRAP','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS']:env.pop(key,None)
    if environment:env.update(environment)
    started=now()
    p=subprocess.run(argv,cwd=cwd or vm,env=env,capture_output=True,timeout=900)
    after=manifest(vm);assert before==after,(name,'source-after')
    for stream in ['stdout','stderr']:
        with gzip.open(out/(stream+'.gz'),'wb') as z:z.write(getattr(p,stream))
    row=dict(argv=argv,cwd=str(cwd or vm),startedUTC=started,completedUTC=now(),exitCode=p.returncode,
        sourceTreeBeforeSHA256=digest(before),sourceTreeAfterSHA256=digest(after),sourceUnchanged=before==after,
        expectedSourceTreeSHA256=expected,sourceFiles=len(before),
        sourceManifestSHA256=sha(enc(before)),stdoutSHA256=sha(p.stdout),stderrSHA256=sha(p.stderr),
        environment={k:env[k] for k in ['PATH','RUSTUP_TOOLCHAIN','CARGO_TARGET_DIR'] if k in env},
        removedEnvironment=['RUSTFLAGS','RUSTC_BOOTSTRAP','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS'])
    (out/'receipt.json').write_bytes(enc(row));(out/'source-manifest.json').write_bytes(enc(before))
    print(name,p.returncode,flush=True)
    if p.returncode:
        print(p.stderr.decode(errors='replace')[-6000:],flush=True)
        raise RuntimeError(name)
    return p,row
def parse(output):
    result={k:{} for k in ['types','classes','fields','totals','owners']}
    for line in output.splitlines():
        if 'HC_' not in line:continue
        kind,name,*values=line[line.index('HC_'):].split();values=list(map(int,values))
        category={'HC_TYPE':'types','HC_CLASS':'classes','HC_FIELD':'fields','HC_TOTAL':'totals','HC_OWNER':'owners'}[kind]
        assert name not in result[category],(kind,name)
        result[category][name]=(dict(bytes=values[0],alignment=values[1]) if category in ['types','classes']
            else dict(offset=values[0],bytes=values[1],alignment=values[2]) if category=='fields' else values[0])
    return result
def reconstruct(label,scratch,frozen_receipt):
    source=FROZEN/('metadata-'+label+'-source.tar.gz')
    expected_manifest=json.loads((FROZEN/('metadata-'+label+'-source-manifest.json')).read_text())
    expected=frozen_receipt['sourceArchives']['metadata-'+label]['sourceTreeSHA256']
    assert digest(expected_manifest)==expected
    assert sha(source.read_bytes())==frozen_receipt['sourceArchives']['metadata-'+label]['archiveSHA256']
    inputs=HERE/'inputs';inputs.mkdir(exist_ok=True)
    shutil.copy2(source,inputs/('metadata-'+label+'-source.tar.gz'))
    shutil.copy2(FROZEN/('metadata-'+label+'-source-manifest.json'),inputs/('metadata-'+label+'-source-manifest.json'))
    vm=scratch/('source-'+expected);vm.mkdir()
    with tarfile.open(source) as tar:
        members=tar.getmembers();assert all(x.isfile() for x in members)
        assert {x.name for x in members}==set(expected_manifest)
        for member in members:
            assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            data=tar.extractfile(member).read();assert sha(data)==expected_manifest[member.name]
            p=vm/member.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    assert manifest(vm)==expected_manifest
    return vm,expected
def verify_fields(layout,schema,unit):
    expected={row['field'] for row in schema if unit or row['config']!='unit'}
    assert set(layout['fields'])==expected
    end={}
    for row in sorted((row for row in schema if row['field'] in expected),key=lambda row:(row['ownerClass'],layout['fields'][row['field']]['offset'])):
        value=layout['fields'][row['field']];cls=row['ownerClass']
        assert value['offset']>=end.get(cls,0)
        assert value['offset']%value['alignment']==0
        end[cls]=value['offset']+value['bytes']
        assert end[cls]<=layout['classes'][cls]['bytes']
def run_context(label,vm,expected,features,profile,unit,scratch,old_layouts,schema):
    kind='unit' if unit else 'production';name='-'.join([label,features,profile,kind])
    target=scratch/('target-'+expected+'-'+features+'-'+profile+'-'+kind)
    assert not target.exists(),target
    target.mkdir()
    env={'CARGO_TARGET_DIR':str(target)}
    flags=['--features','experimental-swift-reactor'] if features=='swift' else ['--all-features']
    release=['--release'] if profile=='release' else []
    argv=(['cargo','test','--lib','--no-run','--offline','--locked',*flags,*release,'--message-format=json-render-diagnostics'] if unit
        else ['cargo','build','--bin','host_contract_layout','--offline','--locked',*flags,*release,'--message-format=json-render-diagnostics'])
    compiled,build_receipt=command('build-'+name,argv,vm,expected,env)
    messages=[json.loads(line) for line in compiled.stdout.decode().splitlines() if line]
    selected=[m for m in messages if m.get('reason')=='compiler-artifact' and m.get('executable')
        and ((unit and m['profile']['test'] and m['target']['name']=='mixer_vm' and m['target']['src_path'].endswith('/src/lib.rs'))
             or (not unit and m['target']['name']=='host_contract_layout' and 'bin' in m['target']['kind']))]
    assert len(selected)==1,(name,selected)
    artifact=selected[0];executable=Path(artifact['executable'])
    assert executable.is_file() and executable.resolve().is_relative_to(scratch.resolve())
    assert artifact['fresh'] is False,(name,'fresh target unexpectedly reused compiler artifact')
    binary_hash=sha(executable.read_bytes());binary_size=executable.stat().st_size
    artifact_dir=HERE/'artifacts'/name;artifact_dir.mkdir(parents=True)
    (artifact_dir/'cargo-artifact.json').write_bytes(enc(artifact))
    with gzip.open(artifact_dir/'executable.gz','wb') as z:z.write(executable.read_bytes())
    assert sha(gzip.decompress((artifact_dir/'executable.gz').read_bytes()))==binary_hash
    list_receipt=None;tests=None
    if unit:
        listed,list_receipt=command('testlist-'+name,[str(executable),'--list'],vm,expected,env)
        assert sha(executable.read_bytes())==binary_hash
        tests=[line.removesuffix(': test') for line in listed.stdout.decode().splitlines() if line.endswith(': test')]
        wanted='experimental_swift_reactor::execution::frame_operations::host_contract_layout_only'
        assert tests.count(wanted)==1 and len(tests)==(201 if features=='swift' else 230),(name,len(tests))
        save('artifacts/'+name+'/testlist.json',tests)
        args=[str(executable),'--exact',wanted,'--nocapture','--test-threads=1']
    else:args=[str(executable)]
    pre_run_hash=sha(executable.read_bytes());assert pre_run_hash==binary_hash
    output,run_receipt=command('execute-'+name,args,vm,expected,env)
    post_run_hash=sha(executable.read_bytes());assert post_run_hash==binary_hash
    if unit:assert re.search(r'test result: ok\. 1 passed; 0 failed;',output.stdout.decode())
    layout=parse(output.stdout.decode())
    proposed=next(x for x in old_layouts if (x['label'],x['features'],x['profile'],x['unit'])==(label,features,profile,unit))
    assert layout=={k:proposed[k] for k in layout},(name,'layout differs from frozen proposal')
    if label=='candidate':verify_fields(layout,schema,unit)
    assert layout['totals']['ticket_max']==86
    assert layout['totals']['state_limit']==134217728 and layout['totals']['combined_limit']==268435456
    record=dict(context=name,label=label,features=features,profile=profile,unit=unit,
        sourceTreeSHA256=expected,sourceFiles=len(manifest(vm)),cargoTarget=str(target),targetCreatedEmpty=True,
        cargoArtifactFresh=artifact['fresh'],cargoArtifact='artifacts/'+name+'/cargo-artifact.json',
        exactExecutablePath=str(executable),executableSHA256=binary_hash,executableBytes=binary_size,
        retainedExecutable='artifacts/'+name+'/executable.gz',executableBeforeListSHA256=binary_hash if unit else None,
        executableAfterListSHA256=binary_hash if unit else None,executableBeforeRunSHA256=pre_run_hash,
        executableAfterRunSHA256=post_run_hash,fullUnitTestList='artifacts/'+name+'/testlist.json' if unit else None,
        fullUnitTestCount=len(tests) if tests is not None else None,
        buildCommand='commands/build-'+name+'/receipt.json',listCommand='commands/testlist-'+name+'/receipt.json' if unit else None,
        executeCommand='commands/execute-'+name+'/receipt.json',layout=layout,
        matchesFrozenProposalExactly=True,authoritativeSourceBoundReplay=True,
        hostOperationExecuted=False,scope='Only metadata printing; unit --list executes no test and exact test runs one layout function.')
    save('contexts/'+name+'.json',record)
    return record
def main():
    assert not (HERE/'session.json').exists(),'Use a new unique evidence directory for another replay.'
    frozen_receipt=json.loads((FROZEN/'receipt.json').read_text())
    frozen_before={name:sha((ROOT/name).read_bytes()) for name in frozen_receipt['bindings']}
    assert frozen_before==frozen_receipt['bindings']
    frozen_receipt_sha=sha((FROZEN/'receipt.json').read_bytes())
    scratch=Path('/tmp/mixer-host-layout-replay-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    scratch.mkdir();save('session.json',dict(scratch=str(scratch),startedUTC=now(),root=str(ROOT),frozenReceiptSHA256=frozen_receipt_sha))
    sources={label:reconstruct(label,scratch,frozen_receipt) for label in ['baseline','candidate']}
    save('source-closures.json',{label:expected for label,(vm,expected) in sources.items()})
    schema=json.loads((FROZEN/'inventory-schema.json').read_text());old_layouts=json.loads((FROZEN/'layouts.json').read_text())
    shutil.copy2(FROZEN/'inventory-schema.json',HERE/'inputs/inventory-schema.json')
    # Prior values are comparison declarations only, not executable provenance.
    shutil.copy2(FROZEN/'layouts.json',HERE/'inputs/historical-proposed-layouts.json')
    base,base_sha=sources['baseline']
    for name,argv in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('host',['uname','-a']),('python',['python3','--version'])]:
        command('tool-'+name,argv,base,base_sha)
    records=[]
    for label,(vm,expected) in sources.items():
        for features in ['swift','all']:
            for profile in ['debug','release']:
                for unit in [False,True]:
                    records.append(run_context(label,vm,expected,features,profile,unit,scratch,old_layouts,schema))
                    save('layouts.json',records)
    for record in records:
        if record['label']!='candidate':continue
        base=next(x for x in records if (x['label'],x['features'],x['profile'],x['unit'])==('baseline',record['features'],record['profile'],record['unit']))
        for key in ['types','owners']:assert base['layout'][key]==record['layout'][key]
        for key,value in base['layout']['totals'].items():assert record['layout']['totals'][key]==value
        if record['unit']:
            assert json.loads((HERE/base['fullUnitTestList']).read_text())==json.loads((HERE/record['fullUnitTestList']).read_text())
    frozen_after={name:sha((ROOT/name).read_bytes()) for name in frozen_receipt['bindings']}
    assert frozen_after==frozen_before and sha((FROZEN/'receipt.json').read_bytes())==frozen_receipt_sha
    save('replay-summary.json',dict(status='fresh-source-and-context-isolated-layout-replay-complete',
        contexts=16,unitFullTestLists=8,retainedExactExecutables=16,
        compilerTargetsDistinct=len({x['cargoTarget'] for x in records})==16,
        exactFinalArchivedSourcesReconstructed=True,allFilesCheckedBeforeAfterEveryCommand=True,
        allNumericLayoutFieldsMatchFrozenProposal=True,allOwnerLayoutsMatchFreshBaseline=True,
        priorAmbiguousMetadataOutputsUsedAsFinalSourceAcceptanceEvidence=False,
        historicalValuesUsedOnlyAsProposedNumericComparison=True,frozenPacketUnchanged=True,
        frozenReceiptSHA256=frozen_receipt_sha,sourceClosures={label:expected for label,(vm,expected) in sources.items()},
        hostOperationExecuted=False,runtimeAccepted=False,accountingIntegrated=False,Ready=False,publicInvocation=False,
        limitations=['Metadata only; no host import or interpreter runs.','These remain pre-growth proposed additive bounds, requiring rebase/re-measure after accepted growth integration.']))
    print('16 isolated source-bound contexts complete; binaries/testlists retained',flush=True)
if __name__=='__main__':main()
