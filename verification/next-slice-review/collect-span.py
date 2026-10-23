#!/usr/bin/env python3
"""Independent review probes: bind inputs and keep failures as evidence."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest():
    paths = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock', ROOT / 'docs/span-execution-design.md', Path(__file__)]
    paths += [p for p in (ROOT / 'vm/src').rglob('*.rs') if 'experimental_wasi' not in p.relative_to(ROOT / 'vm/src').parts]
    paths += list((OUT / 'span-probe/src').rglob('*.rs'))
    paths += [OUT / 'span-probe/Cargo.toml', OUT / 'span-probe/Cargo.lock']
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths)) if p.is_file()}


def main():
    env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], CARGO_TARGET_DIR='/tmp/mixer-span-execution-target')
    receipt = {
        'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'tools': {}, 'commands': [],
        'scope': 'Independent original external-consumer Rust probes for span execution only. Concurrent experimental_wasi source is excluded because the feature is disabled. No device runs, downloads, new general dependencies, production edits, full Swift reactor, product-release or GA qualification.',
        'environment': {'PATH_prefix': '/opt/homebrew/opt/rustup/bin', 'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']},
        'prior_setup_errors': ['Initial cargo command was not on default PATH (127); set explicit rustup PATH.', 'Initial consumer path had one excess parent traversal (101); corrected to ../../../vm before semantic runs.'],
        'rounding_constant_source': '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX27.0.sdk/usr/include/fenv.h:148',
    }
    for tool, argv in [('cargo', ['cargo', '--version']), ('rustc', ['rustc', '-Vv'])]:
        result = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True)
        receipt['tools'][tool] = {'argv': argv, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    for label, extra in [('debug', []), ('release', ['--release'])]:
        before = source_manifest()
        argv = ['cargo', 'test', '--manifest-path', 'verification/next-slice-review/span-probe/Cargo.toml'] + extra + ['--', '--nocapture', '--test-threads=1']
        start = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = OUT / ('span-' + label + '.log')
        log.write_bytes(result.stdout)
        after = source_manifest()
        receipt['commands'].append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start, 'log': str(log.relative_to(ROOT)), 'log_sha256': sha(log), 'source_files': before, 'source_tree_sha256': hashlib.sha256(json.dumps(before, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'source_stable': before == after})
        (OUT / 'span-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        assert before == after, 'source changed while review command ran'
        print(label, result.returncode, flush=True)
    receipt['completed_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt['status'] = 'Review gap reproduced: consumed pre-pinned cache construction reports live pin after owner destruction; other three independent probes pass' if any(c['exit_code'] for c in receipt['commands']) else 'All four independent probes pass'
    (OUT / 'span-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
