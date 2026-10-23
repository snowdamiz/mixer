#!/usr/bin/env python3
"""Independent bounded host review; writes only this review's evidence directory."""
from datetime import datetime, timezone
import hashlib, io, json, os, platform, shutil, subprocess, tarfile, tempfile
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[1]
owner = root / 'verification/remaining-allocator-observers'
baseline = '020f909f2a32553b79ba7068a1798c85d97426b4'
overlays = ['vm/tests/experimental_capability_guest_allocations.rs',
            'vm/tests/capability_ffi_allocations.rs', 'vm/tests/experimental_allocations.rs',
            'vm/tests/common/legacy_allocation_observer.rs']
env = dict(os.environ)
env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env['PATH']
for key in ['MIXER_ALLOCATOR_NOISE', 'MIXER_GUEST_ARC_OOM_SIZE']:
    env.pop(key, None)
private = Path(tempfile.mkdtemp(prefix='mixer-independent-observer-review-'))
env['CARGO_TARGET_DIR'] = str(private/'target-repaired')
checks = []
def sha(data): return hashlib.sha256(data).hexdigest()
def check(name, passed):
    checks.append({'name': name, 'passed': bool(passed)})
    if not passed: raise AssertionError(name)
def manifest(path):
    return {str(p.relative_to(path)): sha(p.read_bytes()) for p in sorted(path.rglob('*')) if p.is_file()}
def tree_digest(files): return sha(json.dumps(files, sort_keys=True).encode())
def archive_files(data):
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        return {m.name: sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
def freeze(path):
    for p in path.rglob('*'): p.chmod(0o555 if p.is_dir() else 0o444)
    path.chmod(0o555)

owner_manifest = json.loads((owner/'evidence-manifest.json').read_text())
owner_bindings = {}
for name, digest in owner_manifest['files'].items():
    actual = sha((owner/name).read_bytes())
    check('owner evidence identity: '+name, actual == digest)
    owner_bindings[name] = actual
owner_bindings['evidence-manifest.json'] = sha((owner/'evidence-manifest.json').read_bytes())
owner_receipt = json.loads((owner/'receipt.json').read_text())
base_export = subprocess.check_output(['git','archive','--format=tar',baseline,'vm'],cwd=root)
check('owner original archive equals exact baseline git export', base_export == (owner/'original/baseline-vm-snapshot.tar').read_bytes())
(here/'baseline-vm-snapshot.tar').write_bytes(base_export)
snapshots = {}
for name in ['original', 'repaired']:
    path = private/name; path.mkdir()
    with tarfile.open(fileobj=io.BytesIO(base_export)) as archive: archive.extractall(path, filter='data')
    snapshots[name] = path
for name in overlays:
    content = (root/name).read_bytes(); destination = snapshots['repaired']/name
    destination.write_bytes(content)
    check('current overlay equals reviewed owner source: '+name, sha(content) == owner_receipt['overlay'][name])
for name in ['legacy_allocation_observer.rs', 'allocation_observer.rs']:
    shutil.copyfile(snapshots['repaired']/'vm/tests/common'/name, here/'probe-support'/name)
base_files = manifest(snapshots['original']); repaired_files = manifest(snapshots['repaired'])
changed = {p for p in set(base_files)|set(repaired_files) if base_files.get(p)!=repaired_files.get(p)}
check('exactly the four named test overlays differ', changed == set(overlays))
check('independent repaired manifest equals owner tested tree', repaired_files == owner_receipt['source_before']['files'])
check('common pointer ownership implementation unchanged', base_files['vm/tests/common/allocation_observer.rs'] == repaired_files['vm/tests/common/allocation_observer.rs'])
with tarfile.open(here/'tested-vm-snapshot.tar','w') as archive: archive.add(snapshots['repaired']/'vm',arcname='vm')
for path in snapshots.values(): freeze(path)
(here/'source-manifest.json').write_text(json.dumps({'baseline_revision':baseline, 'original_files':base_files, 'repaired_files':repaired_files, 'original_tree_sha256':tree_digest(base_files), 'repaired_tree_sha256':tree_digest(repaired_files)},indent=2)+'\n')

def assertions(source):
    # Complete macro invocations are compared literally, including messages.
    import re
    values=[]
    for found in re.finditer(r'\bassert(?:_eq|_ne)?!\s*\(',source):
        start=found.start(); cursor=found.end(); depth=1; string=False; escape=False
        while depth:
            c=source[cursor]; cursor+=1
            if string:
                if escape: escape=False
                elif c=='\\': escape=True
                elif c=='"': string=False
            elif c=='"': string=True
            elif c=='(': depth+=1
            elif c==')': depth-=1
        values.append(source[start:cursor])
    return values
assertion_counts={}
for name in overlays[:3]:
    old=assertions((snapshots['original']/name).read_text())
    new=assertions((snapshots['repaired']/name).read_text())
    check('literal assertion invocations unchanged: '+name,old==new)
    assertion_counts[name]=len(old)
check('all 69 original assertions preserved',sum(assertion_counts.values())==69)
prefixes=('native validate-only','native create32pages','native post allocation refusal',
          'constructor requested allocation events=','fallible argument allocation refusal:',
          'eight argument/completion payloads:','ready-poll/ack allocation calls=',
          'close/drop/last-ticket-ack allocation calls=','all 12 allocation ordinals','observation ')
def measurements(text): return [line for line in text.splitlines() if line.startswith(prefixes)]
commands=[]
def run(name, args, cwd, noisy=False, timeout=240):
    current_env=dict(env)
    if cwd == snapshots['original']: current_env['CARGO_TARGET_DIR'] = str(private/'target-original')
    if noisy: current_env['MIXER_ALLOCATOR_NOISE']='1'
    before=manifest(cwd) if cwd in snapshots.values() else None
    logfile=here/'logs'/(name+'.log')
    with logfile.open('w') as log:
        log.write('CWD: '+str(cwd)+'\nCOMMAND: '+repr(args)+'\nENV: '+repr({'PATH':current_env['PATH'],'CARGO_TARGET_DIR':current_env['CARGO_TARGET_DIR'],'MIXER_ALLOCATOR_NOISE':current_env.get('MIXER_ALLOCATOR_NOISE')})+'\nTIMEOUT_SECONDS: '+str(timeout)+'\n');log.flush()
        try:
            result=subprocess.run(args,cwd=cwd,env=current_env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code='timeout'
        log.write('\nEXIT: '+str(code)+'\n')
    after=manifest(cwd) if before is not None else None
    if before is not None: check('immutable source throughout '+name,before==after)
    commands.append({'name':name,'command':args,'cwd':str(cwd),'noise':noisy,'timeout_seconds':timeout,'exit':code,'source_tree_sha256':tree_digest(before) if before is not None else tree_digest(repaired_files),'source_stable':before==after,'log':str(logfile.relative_to(root)),'log_sha256':sha(logfile.read_bytes())})
    print(name+': '+str(code),flush=True)
    check('command passed: '+name,code==0)
    return logfile.read_text()

tools={name:subprocess.check_output(args,env=env,text=True).strip() for name,args in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('python',['python3','--version'])]}
base_command=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-capability-native experimental-stream-validation','--test','experimental_capability_guest_allocations','--test','capability_ffi_allocations','--test','experimental_allocations']
reference=None; measurement_runs={}; slots={}; derived_runs={}
for release in [False,True]:
    mode='release' if release else 'debug'
    args=base_command+(['--release'] if release else [])+['--','--nocapture']
    text=run('original-'+mode,args,snapshots['original'])
    current=measurements(text)
    if reference is None: reference=current
    check('original 17 measurement lines preserved: '+mode,len(current)==17 and current==reference)
    measurement_runs['original-'+mode]=current
    for noisy in [False,True]:
        name='repaired-'+mode+('-noise' if noisy else '-baseline')
        text=run(name,args,snapshots['repaired'],noisy)
        current=measurements(text); measurement_runs[name]=current
        check('exact original measurements: '+name,current==reference)
        check('three original test functions pass: '+name,text.count('test result: ok. 1 passed; 0 failed; 0 ignored')==3)
        check('guest Shared Arc OOM still aborts: '+name,'known Shared Arc OOM abort: status=signal: 6 (SIGABRT)' in text and 'memory allocation of 1016 bytes failed' in text)
        import re
        slots[name]=[int(x) for x in re.findall(r'observer maximum ownership slots=(\d+) capacity=4096',text)]
        check('bounded pointer ledger in all three tests: '+name,len(slots[name])==3 and max(slots[name])<4096)
    dependencies=private/'target-repaired'/mode/'deps'
    libraries=list(dependencies.glob('libmixer_vm-*.rlib'))
    check('exactly one independently built library: '+mode,len(libraries)==1)
    binary=private/('derived-'+mode)
    run('compile-derived-'+mode,['rustc','--edition=2021','--test',str(here/'derived.rs'),'--extern','mixer_vm='+str(libraries[0]),'-L','dependency='+str(dependencies),'-C','opt-level='+('3' if release else '0'),'-C','overflow-checks=yes','-o',str(binary)],here)
    for noisy in [False,True]:
        name='derived-'+mode+('-noise' if noisy else '-baseline')
        text=run(name,[str(binary),'--nocapture'],here,noisy,45)
        check('independent derived contract checks execute: '+name,'independent observer checks=43;' in text and 'test result: ok. 1 passed; 0 failed; 0 ignored' in text)
        derived_runs[name]={'binary_sha256':sha(binary.read_bytes()),'checks':43}

for name,digest in owner_bindings.items():check('owner evidence remained stable: '+name,sha((owner/name).read_bytes())==digest)
for name,digest in owner_receipt['overlay'].items():check('live reviewed source remained stable: '+name,sha((root/name).read_bytes())==digest)
receipt={'observed_utc':datetime.now(timezone.utc).isoformat(),'status':'passed','baseline_revision':baseline,'worktree_revision_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'tools':tools,'platform':platform.platform(),'private_source':{k:str(v) for k,v in snapshots.items()},'original_tree_sha256':tree_digest(base_files),'repaired_tree_sha256':tree_digest(repaired_files),'source_file_count':len(repaired_files),'overlay':owner_receipt['overlay'],'unchanged_pointer_ledger_sha256':repaired_files['vm/tests/common/allocation_observer.rs'],'assertion_counts':assertion_counts,'measurement_runs':measurement_runs,'max_slots_in_order_ffi_stream_guest':slots,'derived_runs':derived_runs,'owner_evidence_bindings':owner_bindings,'commands':commands,'checks':checks,'limitations':['Single synchronous owner per test executable; allocation workers require explicit ownership.','Requested-byte accounting only; no process RSS or portable ABI size guarantee.','Synthetic exact 900-byte/four-call replay demonstrates observer susceptibility; hosted allocation stack and thread remain unknown.','Host Debug/Release only. No physical device discovery or runs performed; physical iOS/Android gates remain pending.','No product engine edits, dependency changes, publication, signing, immutable published consumer, customer, operational, release or GA qualification.']}
(here/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PASS: '+str(len(checks))+' independent evidence/contract checks',flush=True)
