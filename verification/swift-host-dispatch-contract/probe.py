#!/usr/bin/env python3
"""Isolated compiler-only seam evidence. Never invokes a guest/host operation."""
from pathlib import Path
import datetime, difflib, gzip, hashlib, json, os, re, shutil, subprocess, sys, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
enc = lambda value: (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
sha = lambda data: hashlib.sha256(data).hexdigest()
def manifest(vm):
    files = [vm/'Cargo.toml', vm/'Cargo.lock']
    for name in ['src', 'tests', 'include']:
        files += sorted(p for p in (vm/name).rglob('*') if p.is_file())
    return {str(p.relative_to(vm)): sha(p.read_bytes()) for p in files}
def digest(value): return sha(enc(value))
def save(name, value): (HERE/name).write_bytes(enc(value))
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(name, argv, cwd=None, extra=None, expect=0):
    out = HERE/'commands'/name
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
    env.pop('RUSTFLAGS', None); env.pop('RUSTC_BOOTSTRAP', None)
    if cwd: env['CARGO_TARGET_DIR'] = str(SCRATCH/('target-'+name))
    if extra: env.update(extra)
    before = manifest(cwd) if cwd else None
    started = now()
    p = subprocess.run(argv, cwd=cwd or ROOT, env=env, capture_output=True, timeout=900)
    for stream in ['stdout', 'stderr']:
        with gzip.open(out/(stream+'.gz'), 'wb') as z: z.write(getattr(p, stream))
    receipt = dict(argv=argv, cwd=str(cwd or ROOT), startedUTC=started, completedUTC=now(),
        exitCode=p.returncode, expectedExitCode=expect, sourceTreeSHA256=digest(before) if before else None,
        sourceUnchanged=before==manifest(cwd) if cwd else None,
        stdoutSHA256=sha(p.stdout), stderrSHA256=sha(p.stderr),
        environment={k:env[k] for k in ['PATH','CARGO_TARGET_DIR','RUSTC_BOOTSTRAP','RUSTFLAGS'] if k in env})
    (out/'receipt.json').write_bytes(enc(receipt))
    if before: (out/'source-manifest.json').write_bytes(enc(before))
    print(name, p.returncode, flush=True)
    if p.returncode != expect:
        print(p.stderr.decode(errors='replace')[-7000:], flush=True)
        raise RuntimeError(name)
    assert receipt['sourceUnchanged'] is not False
    return p
def archive(label):
    vm = SCRATCH/label
    m = manifest(vm)
    save(label+'-source-manifest.json', m)
    with tarfile.open(HERE/(label+'-source.tar.gz'), 'w:gz') as tar:
        for name in m: tar.add(vm/name, arcname=name)
    return digest(m)
def setup():
    global SCRATCH
    SCRATCH = Path('/tmp/mixer-host-contract-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    SCRATCH.mkdir()
    save('session.json', dict(scratch=str(SCRATCH), startedUTC=now(), root=str(ROOT)))
    base = SCRATCH/'baseline'; base.mkdir()
    for name in manifest(ROOT/'vm'):
        target=base/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'vm'/name,target)
    actual = digest(manifest(base))
    assert actual == '96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d', actual
    candidate = SCRATCH/'candidate'; shutil.copytree(base,candidate)
    p = candidate/'src/experimental_swift_reactor/frame_operations.rs'
    p.write_text(p.read_text()+'\nmod host_contract_probe {\n'+(HERE/'proposal.rs').read_text()+'\n}\n')
    save('source-closures.json', {label:archive(label) for label in ['baseline','candidate']})
    for name,argv in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('host',['uname','-a']),('git',['git','rev-parse','HEAD']),('python',['python3','--version'])]: run('tool-'+name,argv)
    print(SCRATCH,flush=True)
def check():
    for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for profile in ['debug','release']:
            run('check-'+features+'-'+profile,['cargo','check','--lib','--offline','--locked',*flags,*(['--release'] if profile=='release' else [])],SCRATCH/'candidate')
def mir():
    for unit in [False,True]:
        name = 'mir-'+('unit' if unit else 'production')
        argv = ['cargo','test','--lib','--no-run','--all-features','--offline','--locked'] if unit else ['cargo','rustc','--lib','--all-features','--offline','--locked','--','--emit=mir','-Zmir-include-spans=yes']
        extra={'RUSTC_BOOTSTRAP':'1'}
        if unit: extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
        run(name,argv,SCRATCH/'candidate',extra)
        found = [p for p in (SCRATCH/('target-'+name)/'debug/deps').glob('*.mir') if '::host_contract_inner(' in p.read_text()]
        assert len(found)==1,found
        with gzip.open(HERE/(name+'.mir.gz'),'wb') as z:z.write(found[0].read_bytes())
def negative():
    prefix=sys.argv[2] if len(sys.argv)>2 else 'negative'
    fragments={
      'arguments': '''fn forbidden_arguments(phase: &mut FrameOperationPhase<'_>) {
 let arguments = &phase.phase.parts.values[..];
 phase.phase.parts.values.truncate(0);
 std::hint::black_box(arguments);
}''',
      'cache-view': '''fn forbidden_view(phase: &mut FrameOperationPhase<'_>, slot: &mut Option<Result<(),SwiftRunFailure>>) {
 let frame = phase.phase.parts.frames.last().unwrap();
 let view = phase.phase.parts.cache.view(&frame.pin,phase.phase.operation.control,Some(&*phase.phase.operation.wasi)).unwrap();
 let _ = phase.host_contract_operation(0,slot);
 std::hint::black_box(view.instructions.len());
}''',
      'cache-phase': '''fn forbidden_cache_phase(phase: &mut FrameOperationPhase<'_>) {
 let cache_phase = phase.phase.parts.cache.prepare_operation(phase.phase.operation.control,Some(&*phase.phase.operation.wasi),phase.phase.operation.cursor).unwrap();
 let _ = phase.phase.operation.wasi.dispatch(phase.phase.operation.control,WasiFunction::FdClose,&[],phase.phase.parts.memory,phase.phase.operation.cursor);
 std::hint::black_box(cache_phase);
}''',
    }
    results={}
    for name,code in fragments.items():
        vm=SCRATCH/(prefix+'-'+name);shutil.copytree(SCRATCH/'candidate',vm)
        p=vm/'src/experimental_swift_reactor/frame_operations.rs'
        p.write_text(p.read_text()+'\nmod forbidden_borrow {\nuse super::*;use crate::experimental_wasi::WasiFunction;\n'+code+'\n}\n')
        result=run(prefix+'-'+name,['cargo','check','--lib','--offline','--locked','--features','experimental-swift-reactor'],vm,expect=101)
        codes=sorted(set(re.findall(r'error\[(E\d+)\]',result.stderr.decode())))
        assert codes and set(codes)<={'E0499','E0502'},codes
        results[name]=dict(errorCodes=codes,sourceTreeSHA256=archive(prefix+'-'+name),actualBorrowRejection=True)
    save(prefix+'-borrows.json',results)
if __name__=='__main__':
    command=sys.argv[1]
    if command=='setup': setup()
    else:
        SCRATCH=Path(json.loads((HERE/'session.json').read_text())['scratch'])
        {'check':check,'mir':mir,'negative':negative}[command]()
