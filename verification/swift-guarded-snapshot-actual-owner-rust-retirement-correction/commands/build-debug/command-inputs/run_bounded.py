"""Selected finite commands. Run only after root explicitly releases compiler lane."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,sys,time
from probes import PROBES
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-implementation'
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
EXPECTED_TOOL='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def row(path,base=ROOT):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def rows(base):return [row(p,base) for p in sorted(base.rglob('*')) if p.is_file()]
def write(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def bound_inputs():
    paths={PRODUCER/'seal.json',PRODUCER/'final-source-manifest.json',HERE/'historical-independent/seal.json'}
    original=json.loads((PRODUCER/'final-source-manifest.json').read_text())
    for member in original['members']:
        path=PRODUCER/'source/vm'/member['path'];actual=row(path,PRODUCER/'source/vm');assert actual==member;paths.add(path)
    for path in (PRODUCER/'source/host').rglob('*'):
        if path.is_file():paths.add(path)
    independent=HERE/'historical-independent'
    sealed=json.loads((independent/'seal.json').read_text())
    assert sha((independent/'seal.json').read_bytes())=='e9d55089795d317048040be973e518ff9ce841d7f39cb1449b930d7ae066990c'
    for member in sealed['members']:
        path=independent/member['path'];assert row(path,independent)==member;paths.add(path)
    for name in ['guarded-snapshot-actual-owner-Rust-implementation-selection.json','guarded-snapshot-actual-owner-Rust-contract-amendment.json','guarded-snapshot-actual-owner-Rust-H09-H10-amendment.json','guarded-snapshot-actual-owner-Rust-frozen-release.json']:
        paths.add(ROOT/'verification/swift-semantic-adapter-root-review'/name)
    return [row(path) for path in sorted(paths)]
def prepare_negative(name):
    scope,fragment,diagnostics=PROBES[name];base=HERE/'probes'/name;base.mkdir(parents=True,exist_ok=False)
    shutil.copytree(HERE/'source',base/'source')
    source=base/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    text=source.read_text()
    if scope=='inline':
        anchor='    // OWNER_PROBE_INSERTION';assert text.count(anchor)==1;text=text.replace(anchor,fragment)
    else:text+=fragment
    source.write_text(text)
    write(base/'probe.json',{'id':name,'scope':scope,'fragment':fragment,'intended_diagnostics':diagnostics,'positive_controls':'Corrected test h22 and actual production caller source; no Clone/Copy addition.','source_manifest':rows(base/'source'),'source_tree':digest(rows(base/'source'))})
    return base/'source'
def run(name):
    whole_start=time.monotonic()
    assert sys.argv[2:] == ['--root-compiler-lane-released'], 'Root lane release required.'
    roster=json.loads((HERE/'proposed-command-roster.json').read_text())
    candidates=[c for c in roster['commands'] if c['id']==name];assert len(candidates)==1
    selected=candidates[0];kind=selected['kind'];argv=selected['argv']
    actual_source=rows(HERE/'source/vm');assert digest(actual_source)==roster['source146_tree']
    assert digest(rows(HERE/'source/host'))==roster['host11_tree']
    assert row(TOOL)['sha256']==EXPECTED_TOOL
    source=prepare_negative(name) if kind=='compiler-negative' else HERE/'source'
    out=HERE/'commands'/name;out.mkdir(parents=True,exist_ok=False)
    build=HERE/'build';build.mkdir(exist_ok=True)
    env={'PATH':'/usr/bin:/bin','RUSTC_BOOTSTRAP':'1','SDKROOT':roster['environment']['SDKROOT'],'CARGO_MANIFEST_DIR':str(source/'vm'),'TMPDIR':str(build),'LANG':'C','LC_ALL':'C','TZ':'UTC'}
    before=bound_inputs();source_before=rows(source);tool_before=row(Path(argv[0]))
    write(out/'input-before.json',before);write(out/'source-manifest.json',{'members':source_before,'tree_sha256':digest(source_before)})
    tool_version='queried by exact version command' if kind=='version' else json.loads((HERE/'toolchain.json').read_text())
    write(out/'plan.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'id':name,'kind':kind,'argv':argv,'cwd':str(ROOT),'environment':env,'tool':tool_before,'tool_version':tool_version,'source_tree':digest(source_before),'source146_tree':roster['source146_tree'],'source_attribution':'Root-released producer immutable final source plus this exact two-member correction; no contemporaneous Git HEAD claim.','frozen_producer_seal':'3592011c00794c12dcb76cecc41d4d2913e01a3d6e97612f3ce90f10cb4e5e23','root_selected_budget':{'compiler':9,'host':2},'root_lane_release_explicit':True,'timeout_seconds':55,'child_deadline_seconds':51,'stdout_stderr_each_limit_bytes':4194304,'parent_pid':os.getpid(),'parent_pgid':os.getpgrp(),'native_fixture_UI_capture':False,'old_layout_or_MIR_prices_authoritative':False})
    for own in sorted(HERE.iterdir()):
        if own.is_file() and own.suffix in ('.py','.json','.md'):
            destination=out/'command-inputs'/own.name;destination.parent.mkdir(exist_ok=True);destination.write_bytes(own.read_bytes())
    for member in ['vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs','vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs']:
        destination=out/'source'/member;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes((source/member).read_bytes())
    reason=None;cleaned_descendants=False;start=time.monotonic()
    with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
        process=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
        while process.poll() is None:
            if time.monotonic()-whole_start>51:reason='deadline';break
            if any((out/n).stat().st_size>4194304 for n in ['stdout','stderr']):reason='output-limit';break
            time.sleep(.05)
        if reason:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        code=process.wait(timeout=max(.1,54-(time.monotonic()-whole_start)))
        try:os.killpg(process.pid,0);os.killpg(process.pid,signal.SIGKILL);cleaned_descendants=True
        except ProcessLookupError:pass
        while time.monotonic()-whole_start<54:
            try:os.killpg(process.pid,0)
            except ProcessLookupError:break
            time.sleep(.05)
    try:os.killpg(process.pid,0);absent=False
    except ProcessLookupError:absent=True
    after=bound_inputs();write(out/'input-after.json',after)
    receipt={'schema':1,'id':name,'kind':kind,'exit':code,'reason':reason,'seconds':time.monotonic()-whole_start,'child_seconds':time.monotonic()-start,'owned_pid':process.pid,'owned_pgid':process.pid,'child_reaped':process.returncode is not None,'exact_owned_group_absent':absent,'descendants_cleaned':cleaned_descendants,'stdout':row(out/'stdout'),'stderr':row(out/'stderr'),'source_unchanged':source_before==rows(source),'input_unchanged':before==after,'tool_unchanged':tool_before==row(Path(argv[0])),'output_within_caps':all((out/n).stat().st_size<=4194304 for n in ['stdout','stderr']),'native_fixture_UI_capture':False}
    if kind=='compiler-negative':
        stderr=(out/'stderr').read_text();receipt['intended_diagnostics']=selected['intended_diagnostics'];receipt['intended_diagnostics_found']=all(d in stderr for d in selected['intended_diagnostics']);receipt['negative_rmeta_created']=(HERE/'probes'/name/'negative.rmeta').exists()
    write(out/'receipt.json',receipt)
    assert reason is None and absent and receipt['child_reaped'] and receipt['source_unchanged'] and receipt['input_unchanged'] and receipt['tool_unchanged'] and receipt['output_within_caps'] and receipt['seconds']<=55,receipt
    if kind=='version':
        assert code==0;write(HERE/'toolchain.json',{'tool':row(TOOL),'version':(out/'stdout').read_text(),'SDKROOT':env['SDKROOT']})
    elif kind=='compiler-negative':assert code!=0 and receipt['intended_diagnostics_found'] and not receipt['negative_rmeta_created'],receipt
    else:assert code==0,receipt
    print(json.dumps({key:receipt[key] for key in ['id','kind','exit','seconds','exact_owned_group_absent']}))
if __name__=='__main__':run(sys.argv[1])
