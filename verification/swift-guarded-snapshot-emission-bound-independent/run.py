#!/usr/bin/env python3
"""Fresh bounded pure arithmetic controls. Never imports a producer runner."""
from pathlib import Path
import datetime,hashlib,json,os,platform,shutil,signal,subprocess,sys,time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PRODUCER=ROOT/'verification/swift-guarded-snapshot-emission-bound-implementation'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
HELPER=PRODUCER/'overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def emit(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def preimage(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}
def command(name,args,cwd,env,expected=0,required=None,sources=()):
    folder=HERE/'commands'/name
    folder.mkdir(parents=True,exist_ok=False)
    before=[preimage(p) for p in sources]
    started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    start=time.monotonic();timed_out=False;actions=[]
    child=subprocess.Popen([str(x) for x in args],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:out,err=child.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timed_out=True
        os.killpg(child.pid,signal.SIGKILL);actions.append('SIGKILL only owned group '+str(child.pid))
        out,err=child.communicate(timeout=5)
    (folder/'stdout').write_bytes(out);(folder/'stderr').write_bytes(err)
    stable=before==[preimage(p) for p in sources]
    met=child.returncode==expected and not timed_out and stable
    if required:met=met and required.encode() in out+err
    receipt={'schema':1,'argv':[str(x) for x in args],'cwd':str(cwd),'environment':env,
        'started_at_utc':started_at,'elapsed_seconds':time.monotonic()-start,
        'owned_pid_and_pgid':child.pid,'timeout_seconds':45,'timed_out':timed_out,
        'expected_exit':expected,'exit_code':child.returncode,'required_output':required,'expectation_met':met,
        'stdout_bytes':len(out),'stdout_sha256':sha(out),'stderr_bytes':len(err),'stderr_sha256':sha(err),
        'source_preimages_before':before,'source_preimages_unchanged_after':stable,
        'owned_child_reaped':True,'timeout_cleanup_actions':actions,'global_process_inventory_used':False,
        'scope':'Compiler or independent pure helper/geometry controls only; no VM/encoder/writer entrypoint.'}
    emit(folder/'receipt.json',receipt)
    print(json.dumps({'case':name,'exit':child.returncode,'expectation_met':met}),flush=True)
    if not met:raise AssertionError((name,receipt))
    return out

def main():
    scratch=HERE/'owned-scratch'
    assert not scratch.exists(),'Preserve prior scratch and diagnose before retry'
    scratch.mkdir()
    env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch)}
    cleanup=[]
    try:
        version=command('rustc-version',[RUSTC,'-vV'],ROOT,env,sources=[RUSTC])
        (HERE/'rustc-version.txt').write_bytes(version)
        command('source-reconstruction',[sys.executable,HERE/'review.py'],ROOT,env,sources=[HERE/'review.py',HELPER])
        head=command('source-revision',['/usr/bin/git','rev-parse','HEAD'],ROOT,env)
        emit(HERE/'toolchain.json',{'schema':1,'python_executable':sys.executable,'python_version':sys.version,
            'platform':platform.platform(),'rustc':preimage(RUSTC),'rustc_version_sha256':sha(version),
            'git_HEAD':head.decode().strip(),'root_tree_is_concurrent':True,
            'actual_execution_source_binding':'Exact frozen candidate/helper and reconstructed declarations; current repository HEAD does not replace their tree digests.'})
        sources=[HERE/'host/controls.rs',HERE/'host/source-types.rs',HELPER]
        for opt,name in [(0,'debug'),(3,'optimized')]:
            binary=scratch/(name+'-controls')
            command(name+'-compile',[RUSTC,'--crate-name','mixer_independent_emission','--edition=2021','--target','aarch64-apple-darwin',
                '--error-format=json','-C','opt-level='+str(opt),'-C','overflow-checks=yes','--test',sources[0],'-o',binary],ROOT,env,sources=sources)
            emit(HERE/'commands'/(name+'-compile')/'artifact.json',preimage(binary))
            command(name+'-run',[binary,'--test-threads=1','--nocapture'],ROOT,env,required='6 passed; 0 failed',sources=sources)
            binary.unlink();cleanup.append(str(binary))
        (HERE/'negative').mkdir(exist_ok=True)
        source=HELPER.read_text()
        main_source=(HERE/'host/controls.rs').read_text()
        old_path='../../swift-guarded-snapshot-emission-bound-implementation/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
        mutations=[('coefficient','299_377u64','299_376u64','independent::exact_components_and_geometry_endpoints'),
            ('wrapping','shape.blocks.checked_mul(299_377u64)','Some(shape.blocks.wrapping_mul(299_377u64))','independent::checked_order_edges_and_adjacent_successes')]
        for name,old,new,test in mutations:
            assert source.count(old)==1
            mutant=HERE/'negative'/(name+'.rs');mutant.write_text(source.replace(old,new))
            driver=HERE/'negative'/(name+'-controls.rs')
            driver.write_text(main_source.replace('include!("source-types.rs")','include!("../host/source-types.rs")').replace(old_path,name+'.rs'))
            emit(HERE/'negative'/(name+'.json'),{'schema':1,'mutation':{'from':old,'to':new},'original':preimage(HELPER),'mutant':preimage(mutant),
                'driver':preimage(driver),'expected':'Compile succeeds; selected independent test fails with101. Mutant is not a candidate or runtime fixture.'})
            binary=scratch/(name+'-negative')
            inputs=[driver,mutant,HERE/'host/source-types.rs']
            command(name+'-negative-compile',[RUSTC,'--crate-name','mixer_negative_emission','--edition=2021','--target','aarch64-apple-darwin',
                '--error-format=json','-C','opt-level=0','-C','overflow-checks=yes','--test',driver,'-o',binary],ROOT,env,sources=inputs)
            command(name+'-negative-run',[binary,'--test-threads=1','--nocapture','--exact',test],ROOT,env,101,required='1 failed',sources=inputs)
            binary.unlink();cleanup.append(str(binary))
        emit(HERE/'run-results.json',{'schema':1,'status':'all-fresh-expected-results-met','positive_modes':['debug','optimized'],
            'positive_groups_each':6,'retained_expected_negatives':['coefficient101','wrapping101'],
            'functions_executed':['exact checked_snapshot_emission_bound_v1','exact snapshot_shape_v1','exact checked_add_v1','exact checked_mul_v1'],
            'product_runtime_entrypoints_executed':False,'fresh_full_metadata_compilation':False,
            'work_storage_or_writer_selected':False,'native_UI_capture_process_inventory':False})
    finally:
        # Only children started above are waited/killed. No process enumeration.
        # This exact scratch tree was newly created here; it contains no external data.
        shutil.rmtree(scratch)
        emit(HERE/'cleanup.json',{'schema':1,'owned_scratch':str(scratch),'removed':not scratch.exists(),
            'binary_paths_removed':cleanup,'all_owned_children_reaped_before_removal':True,
            'only_owned_known_process_groups_addressed':True,'global_process_inventory_used':False,
            'other_projects_preserved':True,'native_or_capture_processes_started':False})

if __name__=='__main__':main()
