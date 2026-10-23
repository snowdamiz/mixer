#!/usr/bin/env python3
"""Run exact frozen synthetic tests in an isolated complete baseline checkout."""
from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TREE = HERE / 'tree'
def sha(data): return hashlib.sha256(data).hexdigest()
def manifest():
    return {str(p.relative_to(TREE)): sha(p.read_bytes()) for p in sorted((TREE / 'vm').rglob('*')) if p.is_file()}
before = manifest()
(HERE / 'full-vm-input-manifest.json').write_text(json.dumps(before, indent=2)+'\n')
env = os.environ | {'PATH':'/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'],
                    'CARGO_TARGET_DIR':str(HERE / 'build'), 'TMPDIR':str(HERE / 'tmp')}
(HERE / 'tmp').mkdir(exist_ok=True)
coverage = json.loads((ROOT / 'verification/swift-function-cache/coverage-map.json').read_text())
commands = []
for mode in ['debug','release']:
    for case in coverage['tests']:
        name = 'experimental_swift_reactor::cache_tests::' + case['name']
        argv = ['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--all-features','--lib']
        if mode == 'release': argv += ['--release']
        argv += [name, '--', '--exact', '--nocapture', '--test-threads=1']
        started = time.monotonic()
        result = subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True)
        output = result.stdout + result.stderr
        log = f'frozen-{mode}-{case["name"]}.log'
        (HERE / log).write_text(output)
        exact = bool(re.search(r'test result: ok\. 1 passed; 0 failed;',output))
        commands.append({'argv':argv,'cwd':str(TREE),'environment':{k:env[k] for k in ['PATH','CARGO_TARGET_DIR','TMPDIR']},'exit_code':result.returncode,'seconds':time.monotonic()-started,'output':log,'output_sha256':sha(output.encode()),'exact_one_passed':exact})
        (HERE / 'frozen-runs.json').write_text(json.dumps({'commands':commands,'input_manifest_sha256':sha(json.dumps(before,sort_keys=True).encode()),'source_unchanged':manifest()==before},indent=2)+'\n')
        print(f'{mode} {case["name"]}: exit={result.returncode} exact_one={exact}',flush=True)
        if result.returncode != 0 or not exact: raise SystemExit(1)
assert manifest() == before
