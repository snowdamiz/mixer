"""Metadata-only compiler checks of the corrected isolated const recipe."""
from collections import defaultdict
from pathlib import Path
import json,os,shutil,signal,subprocess,time
from correct import ROOT,INPUT,NEW_VM,canonical,sha,save,custody,build
from probe import RUSTC,members

def bounded(argv,env,cwd,timeout=55):
    started=time.monotonic();p=subprocess.Popen(argv,cwd=cwd,env=env,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed=False;actions=[]
    try:out,err=p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed=True
        try:os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL owned group')
        except ProcessLookupError:pass
        out,err=p.communicate()
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    return out,err,{'argv':argv,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-started,
        'timeout_seconds':timeout,'timed_out':timed,'owned_process_group':p.pid,'new_session':True,
        'child_reaped':True,'owned_group_absent':absent,'cleanup_actions':actions}

def run(label,code,unit=False,negative=False):
    binding=custody();command=ROOT/'commands'/label;command.mkdir(parents=True,exist_ok=False)
    work=ROOT/'owned-work';work.mkdir(exist_ok=True)
    vm=work/label/'vm';assert not vm.exists();shutil.copytree(NEW_VM,vm)
    source=vm/'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    seam='\nmod corrected_const_recipe_control {\n'+code+'\n'
    if negative:seam+='const _:u64=u64::MAX.checked_add(COMMON_EXTRA).expect("required overflow refusal");\n'
    seam+='}\n';source.write_text(source.read_text()+seam)
    if negative:(ROOT/'overflow-negative-seam.rs').write_text(seam)
    preimage={'members':members(vm),'driver_sha256':sha(Path(__file__).read_bytes())}
    assert len(preimage['members'])==144
    (command/'source-preimage.json').write_text(json.dumps(preimage,indent=2,sort_keys=True)+'\n')
    version_out,version_err,version_receipt=bounded([str(RUSTC),'--version','--verbose'],
        {'PATH':'/usr/bin:/bin'},ROOT,10)
    assert version_receipt['exit_code']==0 and version_receipt['owned_group_absent']
    artifact=work/(label+'.rmeta')
    argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
          '-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
        argv+=['--cfg','feature="'+feature+'"']
    argv+=(['--test'] if unit else ['--crate-type','rlib'])+[str(vm/'src/lib.rs'),'--emit=metadata','-o',str(artifact)]
    env={'PATH':'/usr/bin:/bin','TMPDIR':str(work),'CARGO_MANIFEST_DIR':str(vm),'RUSTC_BOOTSTRAP':'1',
         'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version_out),
         'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(preimage)),'MIXER_LOADER_COMMAND_SHA256':sha(canonical(argv))}
    env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
    try:
        out,err,receipt=bounded(argv,env,ROOT.parent.parent)
        (command/'stdout').write_bytes(out);(command/'stderr').write_bytes(err)
        receipt.update(schema=1,environment=env,rustc_version=version_out.decode(),
            rustc_version_command=version_receipt,compiler_sha256=sha(RUSTC.read_bytes()),
            source_binding=binding,source_tree_with_const_seam_sha256=sha(canonical(preimage['members'])),
            stdout_sha256=sha(out),stderr_sha256=sha(err),
            expected_result='E0080 checked arithmetic refusal' if negative else 'metadata compilation only',
            scope='isolated const-only source seam; no engine/VM/writer/native/device/simulator/emulator/UI/capture/process inventory or Git mutation')
        if artifact.exists():receipt['removed_metadata_artifact']={'bytes':artifact.stat().st_size,'sha256':sha(artifact.read_bytes())}
        (command/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        assert receipt['owned_group_absent'] and receipt['child_reaped'] and not receipt['timed_out']
        if negative:assert receipt['exit_code']!=0 and 'E0080' in err.decode() and 'required overflow refusal' in err.decode()
        else:assert receipt['exit_code']==0
        print(json.dumps({'label':label,'exit_code':receipt['exit_code'],'timed_out':receipt['timed_out']}),flush=True)
    finally:
        shutil.rmtree(vm.parent)
        artifact.unlink(missing_ok=True)
    custody()

def main():
    d,_,_,_,_=build();groups={c:defaultdict(int) for c in d['formulas']}
    for r in d['roles']:
        for c,n in r['funding'].items():groups[c][r['template']]+=n
    groups['selected-unconditional']['accepted-encoder-pregrant']=d['encoder_join']['unconditional_bytes']
    groups['admitted-only']['accepted-encoder-admitted']=d['encoder_join']['admitted_only_bytes']
    names={'common-extra':'COMMON_EXTRA','selected-unconditional':'SELECTED_UNCONDITIONAL','admitted-only':'ADMITTED_ONLY'}
    code='// Generated from the separately corrected source-role funding map.\n// Const-only review artifact; no runtime admission/floor selection.\n'
    for category,values in groups.items():
        code+='pub const '+names[category]+':u64=0u64\n'
        for key,n in values.items():
            if n:code+=' // '+key+'\n .checked_add('+str(n)+').expect("checked source-role sum")\n'
        code+=';\n'
    code+='pub const HOST_CALLER:u64='+str(d['host_caller_bytes'])+';\n'
    code+='pub const SELECTED_FROM_LEGACY:u64=COMMON_EXTRA.checked_add(SELECTED_UNCONDITIONAL).expect("selected sum");\n'
    code+='pub const ADMITTED_FROM_LEGACY:u64=SELECTED_FROM_LEGACY.checked_add(ADMITTED_ONLY).expect("phase sum");\n'
    code+='pub const HOST_ADMITTED_FROM_LEGACY:u64=ADMITTED_FROM_LEGACY.checked_add(HOST_CALLER).expect("host sum");\n'
    code+='const _:()=assert!(COMMON_EXTRA==78240 && SELECTED_UNCONDITIONAL==941467 && ADMITTED_ONLY==430175 && HOST_CALLER==81327 && HOST_ADMITTED_FROM_LEGACY==1531209);\n'
    (ROOT/'checked-recipe-constants.rs').write_text(code)
    run('corrected-constant-recipe-production',code)
    run('corrected-constant-recipe-unit',code,unit=True)
    run('corrected-constant-recipe-overflow-negative',code,negative=True)
    work=ROOT/'owned-work';assert not list(work.iterdir());work.rmdir()
    save('recipe-control-results.json',{'schema':1,'positive_contexts':['production','cfg(test)'],
         'overflow_negative':'expected E0080 at checked u64 fold','runtime_invocations':0,
         'source_artifact':'checked-recipe-constants.rs','source_layouts_recollected':False,
         'integration':'isolated const-only seam; original source, budgets, placeholders, WorkAuditPending and actual writer route untouched',
         'owned_scratch_removed':True,'all_owned_groups_absent_and_reaped':True})

if __name__=='__main__':main()
