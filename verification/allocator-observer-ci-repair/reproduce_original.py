#!/usr/bin/env python3
"""Exercise the preserved original observer in a private immutable baseline export."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

root = Path(__file__).resolve().parents[2]
evidence = Path(__file__).resolve().parent
original = (evidence / 'original/span_function_cache_allocations.rs').read_text()
mode = sys.argv[1]
if mode not in ('live', 'fault'):
    raise SystemExit('expected live or fault')
noise = r'''
// Deterministic reproduction only: independent allocation on a different thread.
static NOISE_COMMAND: AtomicUsize = AtomicUsize::new(0);
static NOISE_DONE: AtomicUsize = AtomicUsize::new(0);
static NOISE_ALLOCATED: AtomicBool = AtomicBool::new(false);
struct OriginalNoise(Option<std::thread::JoinHandle<()>>);
impl OriginalNoise {
    fn new() -> Self {
        let worker = std::thread::spawn(|| {
            let layout = Layout::from_size_align(900, 1).unwrap();
            let mut held = std::ptr::null_mut();
            NOISE_DONE.store(1, SeqCst);
            loop {
                match NOISE_COMMAND.load(SeqCst) {
                    1 => {
                        held = unsafe { std::alloc::alloc(layout) };
                        NOISE_ALLOCATED.store(!held.is_null(), SeqCst);
                        NOISE_DONE.store(2, SeqCst);
                        while NOISE_COMMAND.load(SeqCst) == 1 {
                            std::hint::spin_loop();
                        }
                    }
                    2 => {
                        if !held.is_null() {
                            unsafe { std::alloc::dealloc(held, layout) };
                        }
                        return;
                    }
                    _ => std::hint::spin_loop(),
                }
            }
        });
        while NOISE_DONE.load(SeqCst) != 1 {
            std::hint::spin_loop();
        }
        Self(Some(worker))
    }
    fn allocate(&self) {
        NOISE_COMMAND.store(1, SeqCst);
        while NOISE_DONE.load(SeqCst) != 2 {
            std::hint::spin_loop();
        }
    }
}
impl Drop for OriginalNoise {
    fn drop(&mut self) {
        NOISE_COMMAND.store(2, SeqCst);
        self.0.take().unwrap().join().unwrap();
    }
}
'''
source = original.replace('#[test]\n', noise + '\n#[test]\n', 1)
source = source.replace('    let bytes = bytes();', '    let noise = OriginalNoise::new();\n    let bytes = bytes();', 1)
needle = '''        let spans = proof(&bytes);
        begin(ordinal, 0, &cancel);
        let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
        finish();'''
if mode == 'live':
    replacement = '''        let spans = proof(&bytes);
        if ordinal == 1 { noise.allocate(); }
        begin(ordinal, 0, &cancel);
        let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
        finish();
        println!("original live reproduction: background_allocated={} requested_calls={}", NOISE_ALLOCATED.load(SeqCst), CALLS.load(SeqCst));'''
else:
    replacement = '''        let spans = proof(&bytes);
        begin(ordinal, 0, &cancel);
        if ordinal == 1 { noise.allocate(); }
        let result = FunctionCache::new(spans, CacheBudget::default(), &cancel);
        finish();
        println!("original fault reproduction: background_allocated={} requested_calls={}", NOISE_ALLOCATED.load(SeqCst), CALLS.load(SeqCst));'''
if source.count(needle) != 1:
    raise SystemExit('original source anchor changed')
source = source.replace(needle, replacement, 1)
(evidence / f'original/noisy-{mode}-span_function_cache_allocations.rs').write_text(source)
baseline = subprocess.check_output(['git', 'rev-parse', 'e299f1a'], cwd=root, text=True).strip()
export = subprocess.check_output(['git', 'archive', '--format=tar', baseline, 'vm'], cwd=root)
(evidence/'original/baseline-vm-snapshot.tar').write_bytes(export)
private = Path(tempfile.mkdtemp(prefix='mixer-original-observer-'))
snapshot = private/'source'
snapshot.mkdir()
with tarfile.open(fileobj=io.BytesIO(export)) as archive:
    archive.extractall(snapshot, filter='data')
target = snapshot/'vm/tests/span_function_cache_allocations.rs'
if target.read_text() != original:
    raise SystemExit('preserved original does not match selected baseline')
target.write_text(source)
manifest = {str(path.relative_to(snapshot)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(snapshot.rglob('*')) if path.is_file()}
digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
for path in snapshot.rglob('*'):
    path.chmod(0o555 if path.is_dir() else 0o444)
snapshot.chmod(0o555)
cmd = ['cargo', 'test', '--locked', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-span-execution', '--test', 'span_function_cache_allocations', '--', '--nocapture']
env = dict(os.environ)
env['PATH'] = '/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin:' + env['PATH']
env['CARGO_TARGET_DIR'] = str(private/'target')
env.pop('MIXER_ALLOCATOR_NOISE', None)
path = evidence / f'logs/original-noisy-{mode}.log'
with path.open('w') as log:
    log.write('CWD: ' + str(snapshot) + '\n')
    log.write('COMMAND: ' + ' '.join(cmd) + '\n')
    log.flush()
    result = subprocess.run(cmd, cwd=snapshot, env=env, stdout=log, stderr=subprocess.STDOUT)
    log.write(f'\nEXIT: {result.returncode}\n')
receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'baseline_revision': baseline,
    'baseline_vm_export_sha256': hashlib.sha256(export).hexdigest(),
    'private_source': str(snapshot),
    'command': cmd,
    'environment': {'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']},
    'tools': {tool: subprocess.check_output(command, cwd=snapshot, env=env, text=True).strip() for tool,command in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V'])]},
    'source_sha256': digest,
    'source_files': manifest,
    'overlay': {str(target.relative_to(snapshot)): hashlib.sha256(source.encode()).hexdigest()},
    'log': str(path.relative_to(root)),
    'log_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'exit': result.returncode,
    'expected': 'An original-observer test failure caused by independently synchronized background allocation; not evidence of a product leak.',
}
(evidence/f'original-noisy-{mode}-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(f'{mode}: exit={result.returncode} log=logs/original-noisy-{mode}.log')
raise SystemExit(result.returncode != 101)
