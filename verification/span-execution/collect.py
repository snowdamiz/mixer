#!/usr/bin/env python3
"""Local Rust-only qualification; no device, publication or fixture downloads."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ENV = dict(os.environ)
ENV['PATH'] = '/opt/homebrew/opt/rustup/bin:' + ENV.get('PATH', '')
ENV['CARGO_TARGET_DIR'] = '/tmp/mixer-span-execution-target'

def command(args):
    return subprocess.run(args, cwd=ROOT, env=ENV, text=True, capture_output=True)

def sources():
    paths = [ROOT / 'AGENTS.md', ROOT / 'mixer-product-plan.md', ROOT / 'docs/span-execution-design.md', ROOT / 'docs/swift-guest-execution-next.md', ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock', ROOT / 'vm/tests/common/mod.rs']
    paths.extend((ROOT / 'vm/src').rglob('*.rs'))
    paths.extend((ROOT / 'vm/tests').glob('span_execution*.rs'))
    paths.extend((ROOT / 'verification/span-execution').glob('*.py'))
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths)) if p.is_file()}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    (OUT / ('source-' + digest + '.json')).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return digest

TOOLS = {}
for tool, args in [('rustc', ['--version', '--verbose']), ('cargo', ['--version']), ('node', ['--version']), ('python3', ['--version'])]:
    found = shutil.which(tool, path=ENV['PATH'])
    result = command([tool] + args)
    TOOLS[tool] = {'path': found, 'sha256': hashlib.sha256(Path(found).resolve().read_bytes()).hexdigest() if found else None, 'version': result.stdout.strip(), 'stderr': result.stderr.strip(), 'returncode': result.returncode}

cargo = ['cargo', 'test', '--manifest-path', 'vm/Cargo.toml']
features = ['experimental-stream-validation', 'experimental-function-cache', 'experimental-span-execution', 'experimental-span-execution,experimental-capability-native']
commands = [('debug-default', cargo)]
commands += [('debug-' + feature.replace(',', '-'), cargo + ['--features', feature]) for feature in features]
commands += [('release-default', cargo + ['--release'])]
commands += [('release-' + feature.replace(',', '-'), cargo + ['--release', '--features', feature]) for feature in features]
commands += [
    ('focused-clippy', ['cargo','clippy','--manifest-path','vm/Cargo.toml','--features',features[-1],'--lib','--bin','mixer-vm','--test','span_execution','--test','span_execution_allocations','--test','span_execution_oracle','--','-D','warnings']),
    ('debug-observations',cargo + ['--features',features[-1],'--test','span_execution','--test','span_execution_allocations','--test','span_execution_oracle','--','--nocapture']),
    ('release-observations',cargo + ['--release','--features',features[-1],'--test','span_execution','--test','span_execution_allocations','--test','span_execution_oracle','--','--nocapture']),
    ('stream-node-oracle',cargo + ['--features','experimental-stream-validation','--test','experimental_oracle','--','--ignored','--nocapture']),
]
receipt = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_revision': command(['git','rev-parse','HEAD']).stdout.strip(), 'status_at_start':command(['git','status','--porcelain']).stdout.splitlines(), 'tools': TOOLS, 'environment':{'PATH':ENV['PATH'],'CARGO_TARGET_DIR':ENV['CARGO_TARGET_DIR']}, 'scope':'Original independently authored v1/v2/v3 Rust cache-owned execution probes and existing local Rust regressions. Node is development oracle only. No WASI admission, full Swift reactor execution, physical-device or product-release qualification.', 'commands':[]}
for label,args in commands:
    before = sources()
    start = time.monotonic()
    result = command(args)
    elapsed = time.monotonic() - start
    stdout_path = label + '.stdout.txt'
    stderr_path = label + '.stderr.txt'
    (OUT / stdout_path).write_text(result.stdout)
    (OUT / stderr_path).write_text(result.stderr)
    after = sources()
    receipt['commands'].append({'label':label,'argv':args,'returncode':result.returncode,'elapsed_seconds':elapsed,'source_digest_before':before,'source_digest_after':after,'source_stable':before==after,'stdout':stdout_path,'stderr':stderr_path,'stdout_sha256':hashlib.sha256(result.stdout.encode()).hexdigest(),'stderr_sha256':hashlib.sha256(result.stderr.encode()).hexdigest()})
    (OUT / 'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(label, 'exit='+str(result.returncode), 'seconds='+str(round(elapsed,3)), 'source_stable='+str(before==after), flush=True)
    if result.returncode:
        print(result.stdout[-5000:], result.stderr[-5000:], flush=True)
        raise SystemExit(result.returncode)
receipt['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt['passed']=True
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
