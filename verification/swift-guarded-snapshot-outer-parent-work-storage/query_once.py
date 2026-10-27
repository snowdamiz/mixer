#!/usr/bin/env python3
"""One root-coordinated, production-only two-observation layout diagnostic."""
import datetime, hashlib, json, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
SOURCE = V / 'swift-guarded-snapshot-outer-parent-source'
BASE = V / 'swift-guarded-snapshot-funding-implementation/source/vm'
OLD = V / 'swift-guarded-snapshot-host-composition'
OUT = HERE / 'commands/result-layout'
WORK = HERE / 'owned-work/result-layout'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(a): return json.dumps(a, sort_keys=True, separators=(',', ':')).encode()
def row(p, b): return {'path': p, 'bytes': len(b), 'sha256': sha(b)}
def write(p, a):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(a, sort_keys=True, indent=2)+'\n')
def context():
    source = {}
    for m in json.loads((OLD/'source-manifest.json').read_bytes())['members']:
        p = OLD/'overlay/vm'/m['path']
        if not p.is_file(): p = BASE/m['path']
        b = p.read_bytes()
        assert row(m['path'], b) == m
        source[m['path']] = b
    source[PROFILE] = (SOURCE/'overlay/vm'/PROFILE).read_bytes()
    candidate = [row(p,source[p]) for p in sorted(source,key=Path)]
    assert sha(canon(candidate)) == '27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
    snippet = (SOURCE/'outer-parent.inc.rs').read_bytes()
    tail = (HERE/'query-result-layout.inc.rs').read_bytes()
    assert source[PROFILE].count(snippet) == 1 and snippet.endswith(b'}\n')
    source[PROFILE] = source[PROFILE].replace(snippet,snippet[:-2]+b'\n'+tail+b'}\n')
    members = [row(p,source[p]) for p in sorted(source,key=Path)]
    manifest = {'members':members,'member_count':len(members),'tree_sha256':sha(canon(members))}
    retained = json.loads((V/'swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/receipt.json').read_bytes())
    assert sha(RUSTC.read_bytes()) == retained['compiler_sha256']
    argv = retained['argv'][:-2]+['--emit=metadata='+str(WORK/'query.rmeta')]
    argv[argv.index('--crate-type')+2] = str(WORK/'vm/src/lib.rs')
    env = {**retained['environment'],'CARGO_MANIFEST_DIR':str(WORK/'vm'),'TMPDIR':str(WORK)}
    plan = {'schema':1,'argv':argv,'argv_sha256':sha(canon(argv)),'environment':env,'environment_sha256':sha(canon(env)),
        'cwd':str(ROOT),'query_tail':row('query-result-layout.inc.rs',tail),'candidate_tree':sha(canon(candidate)),
        'query_tree':manifest['tree_sha256'],'compiler_path':str(RUSTC),'compiler_sha256':retained['compiler_sha256'],
        'compiler_version_preimage':retained['compiler_version_preimage'],'compiler_version_sha256':retained['compiler_version_sha256'],
        'runner_sha256':sha(Path(__file__).read_bytes()),'python_version':sys.version,
        'authorization':'Root reserved sole compiler slot for exactly two direct size/alignment observations of Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>; no retry.',
        'expected_exit_code':1,'expected_error_codes':['E0308','E0308'],'timeout_seconds':60,'compiler_invocations_authorized':1,
        'cfg_test':False,'metadata_only':True,'runtime':False,'codegen_or_executable':False,'native_UI_capture':False,'global_process_inventory':False,
        'source_revision_from_root_acceptance':'a32d056355ec2f417e9ef7a73788b420176377b6'}
    return source, manifest, plan
def group(pid):
    try: os.killpg(pid,0); return True
    except ProcessLookupError: return False
def main():
    source, manifest, plan = context()
    if sys.argv[1:] == ['--plan']:
        assert not OUT.exists() and not WORK.exists()
        write(HERE/'query-plan.json',plan);write(HERE/'query-source-manifest.json',manifest)
        print(json.dumps({'plan_sha256':sha((HERE/'query-plan.json').read_bytes()),'query_tree':manifest['tree_sha256'],'tail_sha256':plan['query_tail']['sha256'],'argv_sha256':plan['argv_sha256'],'environment_sha256':plan['environment_sha256']}));return
    assert sys.argv[1:] == ['--run-once']
    assert json.loads((HERE/'query-plan.json').read_bytes()) == plan
    assert json.loads((HERE/'query-source-manifest.json').read_bytes()) == manifest
    assert not OUT.exists() and not WORK.exists(),'one-shot query cannot retry'
    OUT.mkdir(parents=True);WORK.mkdir(parents=True)
    for p,b in source.items():
        d=WORK/'vm'/p;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(b)
    receipt={**plan,'compiler_invocations':0,'owned_pid':None,'owned_pgid':None,'exit_code':None,'timed_out':False,'child_reaped':False,'owned_group_absent':None,'owned_scratch_removed':False,'query_success':False,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(OUT/'receipt.json',receipt);child=None;start=time.monotonic()
    try:
        with (OUT/'stdout').open('wb') as stdout,(OUT/'stderr').open('wb') as stderr:
            child=subprocess.Popen(plan['argv'],cwd=ROOT,env=plan['environment'],stdout=stdout,stderr=stderr,start_new_session=True)
            receipt.update(compiler_invocations=1,owned_pid=child.pid,owned_pgid=child.pid);write(OUT/'receipt.json',receipt)
            try: child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                receipt['timed_out']=True;os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            receipt.update(exit_code=child.returncode,elapsed_seconds=time.monotonic()-start,child_reaped=True)
        write(OUT/'receipt.json',receipt) # Terminal facts survive postprocessing failure.
        for name in ['stdout','stderr']:receipt[name]=row(name,(OUT/name).read_bytes())
        err=(OUT/'stderr').read_text();codes=re.findall(r'^error\[(E\d+)\]',err,re.M)
        assert receipt['exit_code']==1 and not receipt['timed_out'] and codes==['E0308','E0308'],codes
        observations=[]
        for name in ['SIZE','ALIGN']:
            part=next(s for s in err.split('error[E0308]') if 'OUTER_RESULT_REQUEST_'+name in s)
            numbers=re.findall(r'found one with a size of (\d+)',part)
            assert len(numbers)==1
            observations.append({'query':name.lower(),'observed':int(numbers[0]),'type':'Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>'})
        assert [o['observed'] for o in observations]==[8,8]
        write(OUT/'layouts.json',{'schema':1,'rows':observations,'native_or_dynamic_backing':False})
        receipt.update(query_success=True,expected_diagnostic_exit_observed=True)
    except BaseException as e:receipt['recorder_error']=repr(e)
    finally:
        if child is not None:
            if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5);receipt.update(child_reaped=True,exit_code=child.returncode)
            if group(child.pid):os.killpg(child.pid,signal.SIGKILL)
            receipt['owned_group_absent']=not group(child.pid)
        shutil.rmtree(WORK)
        if WORK.parent.exists() and not any(WORK.parent.iterdir()):WORK.parent.rmdir()
        receipt.update(owned_scratch_removed=not WORK.exists(),finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        write(OUT/'receipt.json',receipt)
    print(json.dumps({k:receipt.get(k) for k in ['query_success','exit_code','elapsed_seconds','timed_out','child_reaped','owned_group_absent','owned_scratch_removed','recorder_error']}))
    assert receipt['query_success'] and receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['owned_scratch_removed']
if __name__=='__main__':main()
