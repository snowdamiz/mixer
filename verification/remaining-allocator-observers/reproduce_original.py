#!/usr/bin/env python3
"""Replay the exact originals, then instrument only unrelated worker scheduling."""
from datetime import datetime, timezone
import hashlib, io, json, os
from pathlib import Path
import subprocess, tarfile, tempfile
root=Path(__file__).resolve().parents[2]
evidence=Path(__file__).resolve().parent
original=(evidence/'original/experimental_capability_guest_allocations.rs').read_text()
noise=r'''
// Reproduction-only unrelated worker; this is not a claimed hosted CI stack.
static NOISE_COMMAND: AtomicUsize = AtomicUsize::new(0);
static NOISE_DONE: AtomicBool = AtomicBool::new(false);
static NOISE_ALLOCATED: AtomicBool = AtomicBool::new(false);
struct OriginalNoise(Option<std::thread::JoinHandle<()>>);
impl OriginalNoise {
    fn new() -> Self {
        let worker = std::thread::spawn(|| {
            let allocator: &dyn GlobalAlloc = std::hint::black_box(&Probe);
            let layout = Layout::from_size_align(900, 1).unwrap();
            let mut held = std::ptr::null_mut();
            loop {
                match NOISE_COMMAND.load(SeqCst) {
                    1 => {
                        // Three transient bytes plus one retained 900-byte
                        // allocation produce the same four-call/900-byte delta
                        // as the hosted log, with a deliberately synthetic stack.
                        let transient = Layout::from_size_align(1, 1).unwrap();
                        for _ in 0..3 {
                            let pointer = unsafe { allocator.alloc(transient) };
                            if !pointer.is_null() { unsafe { allocator.dealloc(pointer, transient) }; }
                        }
                        held = unsafe { allocator.alloc(layout) };
                        NOISE_ALLOCATED.store(!held.is_null(), SeqCst);
                        NOISE_COMMAND.store(0, SeqCst);
                        NOISE_DONE.store(true, SeqCst);
                    }
                    2 => {
                        // A refused first background request consumes ordinal 1
                        // globally, so the intended guest request is accepted.
                        held = unsafe { allocator.alloc(layout) };
                        NOISE_ALLOCATED.store(!held.is_null(), SeqCst);
                        NOISE_COMMAND.store(0, SeqCst);
                        NOISE_DONE.store(true, SeqCst);
                    }
                    3 => {
                        if !held.is_null() { unsafe { allocator.dealloc(held, layout) }; }
                        return;
                    }
                    _ => std::hint::spin_loop(),
                }
            }
        });
        Self(Some(worker))
    }
    fn allocate(&self, command: usize) {
        NOISE_DONE.store(false, SeqCst);
        NOISE_COMMAND.store(command, SeqCst);
        while !NOISE_DONE.load(SeqCst) { std::hint::spin_loop(); }
    }
}
impl Drop for OriginalNoise {
    fn drop(&mut self) {
        NOISE_COMMAND.store(3, SeqCst);
        self.0.take().unwrap().join().unwrap();
    }
}
'''
base_export=(evidence/'original/baseline-vm-snapshot.tar').read_bytes()
private=Path(tempfile.mkdtemp(prefix='mixer-original-remaining-observers-'))
env=dict(os.environ);env['PATH']='/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin:'+env['PATH'];env.pop('MIXER_ALLOCATOR_NOISE',None);env['CARGO_TARGET_DIR']=str(private/'target')
cmd=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-capability-native experimental-stream-validation','--test','experimental_capability_guest_allocations']
receipt={'observed_utc':datetime.now(timezone.utc).isoformat(),'baseline_revision':'020f909f2a32553b79ba7068a1798c85d97426b4','baseline_vm_export_sha256':hashlib.sha256(base_export).hexdigest(),'environment':{'CARGO_TARGET_DIR':env['CARGO_TARGET_DIR']},'tools':{n:subprocess.check_output(c,env=env,text=True).strip() for n,c in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V'])]},'cases':[],'scope':'Synthetic worker demonstrates original instrumentation defects. Hosted four-call/900-byte allocation origin remains unattributed. No product, physical-device or GA qualification.'}
for mode in ('baseline','live','fault'):
    source=original
    if mode!='baseline':
        source=source.replace('#[test]\n',noise+'\n#[test]\n',1)
        source=source.replace('    let w = wasm();','    let noise = OriginalNoise::new();\n    let w = wasm();',1)
        if mode=='live':
            anchor='    let base = begin(0);\n    for t in &mut tokens {'
            replacement='    let base = begin(0);\n    noise.allocate(1);\n    for t in &mut tokens {'
        else:
            anchor='    let base = begin(1);\n    let failure = g'
            replacement='    let base = begin(1);\n    noise.allocate(2);\n    println!("original fault worker allocated={};calls_before_guest={}", NOISE_ALLOCATED.load(SeqCst), CALLS.load(SeqCst));\n    let failure = g'
        assert source.count(anchor)==1
        source=source.replace(anchor,replacement,1)
        (evidence/f'original/noisy-{mode}-experimental_capability_guest_allocations.rs').write_text(source)
    snapshot=private/mode;snapshot.mkdir()
    with tarfile.open(fileobj=io.BytesIO(base_export)) as archive:archive.extractall(snapshot,filter='data')
    target=snapshot/'vm/tests/experimental_capability_guest_allocations.rs';assert target.read_text()==original;target.write_text(source)
    files={str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(snapshot.rglob('*')) if p.is_file()}
    digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    archive_path=evidence/f'original/{mode}-tested-vm-snapshot.tar'
    with tarfile.open(archive_path,'w') as archive:archive.add(snapshot/'vm',arcname='vm')
    for p in snapshot.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
    snapshot.chmod(0o555)
    for release in (False,True):
        name='original-'+mode+('-release' if release else '-debug');path=evidence/f'logs/{name}.log'
        command=cmd+(['--release'] if release else [])
        if mode=='baseline':command+=['--test','capability_ffi_allocations','--test','experimental_allocations']
        command+=['--','--nocapture']
        with path.open('w') as log:
            log.write('CWD: '+str(snapshot)+'\nCOMMAND: '+' '.join(command)+'\n');log.flush()
            result=subprocess.run(command,cwd=snapshot,env=env,stdout=log,stderr=subprocess.STDOUT)
            log.write(f'\nEXIT: {result.returncode}\n')
        after={str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(snapshot.rglob('*')) if p.is_file()}
        receipt['cases'].append({'name':name,'mode':mode,'private_source':str(snapshot),'full_snapshot':str(archive_path.relative_to(root)),'full_snapshot_sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),'source_sha256':digest,'source_files':files,'source_stable':after==files,'command':command,'exit':result.returncode,'expected_exit':0 if mode=='baseline' else 101,'log':str(path.relative_to(root)),'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        print(f'{name}: exit={result.returncode}',flush=True)
(evidence/'original-replay-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(any(c['exit']!=c['expected_exit'] for c in receipt['cases']))
