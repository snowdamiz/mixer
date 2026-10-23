#!/usr/bin/env python3
"""Check only allocator-test overlays against the retained foundation revision."""
from datetime import datetime, timezone
import hashlib, io, json, os
from pathlib import Path
import subprocess, tarfile, tempfile
root = Path(__file__).resolve().parents[2]
evidence = Path(__file__).resolve().parent
env = dict(os.environ)
env['PATH'] = '/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin:' + env['PATH']
env.pop('MIXER_ALLOCATOR_NOISE', None)
baseline = '020f909f2a32553b79ba7068a1798c85d97426b4'
export = (evidence/'original/baseline-vm-snapshot.tar').read_bytes()
private = Path(tempfile.mkdtemp(prefix='mixer-remaining-observers-'))
snapshot = private/'source'; snapshot.mkdir()
with tarfile.open(fileobj=io.BytesIO(export)) as archive: archive.extractall(snapshot, filter='data')
paths = ['vm/tests/experimental_capability_guest_allocations.rs', 'vm/tests/capability_ffi_allocations.rs', 'vm/tests/experimental_allocations.rs', 'vm/tests/common/legacy_allocation_observer.rs']
overlay = {}
for name in paths:
    content = (root/name).read_bytes(); (snapshot/name).write_bytes(content)
    overlay[name] = hashlib.sha256(content).hexdigest()
def source():
    manifest = {str(p.relative_to(snapshot)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(snapshot.rglob('*')) if p.is_file()}
    return {'sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), 'files': manifest}
archive_path = evidence/'tested-vm-snapshot.tar'
with tarfile.open(archive_path, 'w') as archive: archive.add(snapshot/'vm', arcname='vm')
for p in snapshot.rglob('*'): p.chmod(0o555 if p.is_dir() else 0o444)
snapshot.chmod(0o555)
env['CARGO_TARGET_DIR'] = str(private/'target')
base = ['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-capability-native experimental-stream-validation','--test','experimental_capability_guest_allocations','--test','capability_ffi_allocations','--test','experimental_allocations']
commands = []
for release in (False,True):
    for noisy in (False,True):
        name = ('release' if release else 'debug') + ('-noise' if noisy else '-baseline')
        commands.append((name,base+(['--release'] if release else [])+['--','--nocapture'],noisy))
commands.append(('clippy', ['cargo','clippy']+base[2:]+['--','-D','warnings'],False))
receipt = {'observed_utc':datetime.now(timezone.utc).isoformat(),'baseline_revision':baseline,'worktree_revision_at_capture':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'private_source':str(snapshot),'baseline_vm_export_sha256':hashlib.sha256(export).hexdigest(),'environment':{'CARGO_TARGET_DIR':env['CARGO_TARGET_DIR']},'overlay':overlay,'unchanged_pointer_ledger_sha256':hashlib.sha256((snapshot/'vm/tests/common/allocation_observer.rs').read_bytes()).hexdigest(),'full_snapshot':str(archive_path.relative_to(root)),'full_snapshot_sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),'tools':{name:subprocess.check_output(cmd,cwd=snapshot,env=env,text=True).strip() for name,cmd in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('clippy',['cargo','clippy','-V'])]},'source_before':source(),'checks':[],'scope':'Test infrastructure only; immutable foundation plus exactly four named test overlays. No device, published-package, release, or GA qualification.'}
for name,cmd,noisy in commands:
    check_env = dict(env)
    if noisy: check_env['MIXER_ALLOCATOR_NOISE']='1'
    before=source()['sha256']; path=evidence/f'logs/{name}.log'
    with path.open('w') as log:
        log.write('CWD: '+str(snapshot)+'\nCOMMAND: '+('MIXER_ALLOCATOR_NOISE=1 ' if noisy else '')+' '.join(cmd)+'\n');log.flush()
        result=subprocess.run(cmd,cwd=snapshot,env=check_env,stdout=log,stderr=subprocess.STDOUT)
        log.write(f'\nEXIT: {result.returncode}\n')
    receipt['checks'].append({'name':name,'command':cmd,'environment':{'MIXER_ALLOCATOR_NOISE':'1'} if noisy else {},'exit':result.returncode,'source_before_sha256':before,'source_after_sha256':source()['sha256'],'log':str(path.relative_to(root)),'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    print(f'{name}: exit={result.returncode}',flush=True)
receipt['source_after']=source();receipt['source_stable']=receipt['source_before']==receipt['source_after']
(evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(any(c['exit']!=0 for c in receipt['checks']))
