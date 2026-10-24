#!/usr/bin/env python3
"""Independent review runner. Writes only this packet and one owned scratch root."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, shutil, subprocess, sys, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-control-behavior-implementation'
SCRATCH = Path('/tmp/mixer-swift-control-behavior-independent-review-20261024')
BASE, VM, PROBES, META = [SCRATCH / x for x in ['baseline-vm', 'candidate-vm', 'probe-vm', 'metadata-vm']]
def enc(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def manifest(root):
    names = [root / x for x in ['Cargo.toml', 'Cargo.lock']]
    for sub in ['src', 'tests', 'include']: names += sorted(p for p in (root/sub).rglob('*') if p.is_file())
    return {str(p.relative_to(root)): sha(p) for p in names}
def digest(value): return hashlib.sha256(enc(value)).hexdigest()
def env(target='target'):
    result = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR=str(SCRATCH / target))
    for name in ['RUSTFLAGS', 'RUSTC_BOOTSTRAP']: result.pop(name, None)
    return result
def run(name, args, cwd=VM, extra=None, target='target'):
    out = HERE / 'commands' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + name)
    out.mkdir(parents=True)
    used = env(target)
    if extra: used.update(extra)
    tree = manifest(cwd) if (cwd/'Cargo.toml').exists() else None
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(args, cwd=cwd, env=used, capture_output=True)
    for stream in ['stdout', 'stderr']:
        with gzip.open(out/(stream+'.gz'), 'wb') as f: f.write(getattr(result, stream))
    receipt = dict(name=name, argv=args, cwd=str(cwd), startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), exitCode=result.returncode, sourceTreeSHA256=digest(tree) if tree else None, sourceManifest=tree, environment={k:used[k] for k in ['PATH','CARGO_TARGET_DIR','RUSTFLAGS','RUSTC_BOOTSTRAP'] if k in used}, stdoutSHA256=hashlib.sha256(result.stdout).hexdigest(), stderrSHA256=hashlib.sha256(result.stderr).hexdigest())
    (out/'receipt.json').write_bytes(enc(receipt))
    print(name, result.returncode, out.relative_to(HERE), flush=True)
    if result.returncode: print(result.stderr.decode()[-2500:] + result.stdout.decode()[-4000:], flush=True)
    return result, out
def extract(root, archive):
    root.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            assert member.isfile() and member.name.startswith('vm/') and '..' not in Path(member.name).parts
            dst=root/member.name[3:];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(source.extractfile(member).read())
def setup():
    assert not SCRATCH.exists(), 'owned scratch already exists; do not sweep unknown contents'
    SCRATCH.mkdir()
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in [PRODUCER/'receipt.json',PRODUCER/'seal.json',PRODUCER/'verify.py',PRODUCER/'source.patch',PRODUCER/'candidate-2-delta.patch',PRODUCER/'baseline-source.tar.gz',PRODUCER/'implementation-source.tar.gz',ROOT/'docs/swift-control-behavior-implementation.md',ROOT/'docs/swift-control-invocation-contract.md',ROOT/'verification/swift-control-invocation-root-review/candidate-2-acceptance.json']}
    assert inputs[str((PRODUCER/'seal.json').relative_to(ROOT))]=='b5c7184b31f70c9361d769b5cf568be148985f6662bed56ddf130c9c86ac33b9'
    assert inputs[str((PRODUCER/'receipt.json').relative_to(ROOT))]=='42bd019420f161655213f2ae77cf986c7245dd6abae329ad4d45f6acb17e2d47'
    live=manifest(ROOT/'vm');assert digest(live)=='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
    extract(BASE,PRODUCER/'baseline-source.tar.gz');assert manifest(BASE)==live
    shutil.copytree(BASE,VM)
    p,_=run('apply-exact-source-patch',['git','apply','--no-index','--whitespace=error',str(PRODUCER/'source.patch')],VM)
    assert p.returncode==0
    assert digest(manifest(VM))=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'
    alternate=SCRATCH/'accepted-candidate-2-vm';shutil.copytree(BASE,alternate)
    p,_=run('apply-accepted-candidate-2',['git','apply','--no-index','--whitespace=error',str(PRODUCER/'accepted-candidate-2.patch')],alternate);assert p.returncode==0
    assert digest(manifest(alternate))=='e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d'
    p,_=run('apply-candidate-2-delta',['git','apply','--no-index','--whitespace=error',str(PRODUCER/'candidate-2-delta.patch')],alternate);assert p.returncode==0
    assert manifest(alternate)==manifest(VM)
    archived=SCRATCH/'archived-vm';extract(archived,PRODUCER/'implementation-source.tar.gz');assert manifest(archived)==manifest(VM)
    (HERE/'inputs.json').write_bytes(enc(dict(inputs=inputs,liveManifest=live,baselineClosure=digest(manifest(BASE)),candidateClosure=digest(manifest(VM)),sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),scratch=str(SCRATCH))))
def matrix(probes=False):
    source=PROBES if probes else VM
    for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for release in [False,True]:
            args=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),('review_' if probes else 'experimental_swift_reactor::execution::'),'--','--nocapture','--test-threads=1']
            p,_=run(('probes-' if probes else '')+config+('-release' if release else '-debug'),args,source)
            assert p.returncode==0
    if probes:return
    for config,flags in [('span',['--features','experimental-span-execution']),('all',['--all-features'])]:
        for release in [False,True]:
            p,_=run(config+('-release' if release else '-debug')+'-frozen',['cargo','test','--test','span_control_extraction','--locked','--offline',*flags,*(['--release'] if release else []),'--','--nocapture','--test-threads=1'])
            assert p.returncode==0
    for config,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for release in [False,True]:
            p,_=run(config+('-release' if release else '-debug')+'-check',['cargo','check','--lib','--locked','--offline',*flags,*(['--release'] if release else [])])
            assert p.returncode==0
    p,_=run('format',['cargo','fmt','--all','--','--check']);assert p.returncode==0
def probes():
    if not PROBES.exists():shutil.copytree(VM,PROBES)
    filename=PROBES/'src/experimental_swift_reactor/control_operations_tests.rs'
    original=(VM/'src/experimental_swift_reactor/control_operations_tests.rs').read_text()
    filename.write_text(original+'\n'+(HERE/'independent_probes.rs').read_text())
    (HERE/'probe-manifest.json').write_bytes(enc(manifest(PROBES)))
    matrix(True)
if __name__=='__main__':
    {'setup':setup,'matrix':matrix,'probes':probes}[sys.argv[1]]()
