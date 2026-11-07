#!/usr/bin/env python3
"""Own exact-prefix host probes. No producer runner or test is executed."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import traceback
from admit_frozen import verify_seal, SOURCE_SHA

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
ADMITTED = OWN / 'commands/frozen-admission-1/inputs'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def main():
    name = sys.argv[1]
    if not name.startswith('accounting-') or '/' in name or '..' in name: raise ValueError('fresh own run name required')
    run = OWN / 'commands' / name
    run.mkdir(parents=True, exist_ok=False)
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'invocation': sys.orig_argv,
              'scope': 'seven independent accounting host probes against exact frozen source prefixes',
              'status': 'started', 'commands': [], 'sources': [], 'product_acceptance': False,
              'native_capture_process_or_device_discovery': False, 'producer_tests_or_scripts_executed': False}
    binary = run / 'build/accounting-probe'
    def call(name, argv):
        p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
        (run / (name + '.stdout.txt')).write_text(p.stdout)
        (run / (name + '.stderr.txt')).write_text(p.stderr)
        result['commands'].append({'name': name, 'argv': argv, 'exit_code': p.returncode, 'stdout': name+'.stdout.txt', 'stderr': name+'.stderr.txt'})
        if p.returncode: raise RuntimeError(f'{name} failed; raw outputs retained')
        return p.stdout
    try:
        result['before'] = verify_seal()
        call('revision', ['git', 'rev-parse', 'HEAD'])
        call('python-version', [sys.executable, '--version'])
        call('rustc-version', [str(RUSTC), '--version', '--verbose'])
        result['tools'] = []
        for path in [Path(sys.executable).resolve(), RUSTC.resolve()]:
            data = path.read_bytes(); result['tools'].append({'path': str(path), 'bytes': len(data), 'sha256': sha(data)})
        build = run / 'build'
        (build/'src').mkdir(parents=True)
        for relative in ['src/analyzer.rs', 'src/envelope.rs']:
            data = (ADMITTED/relative).read_bytes()
            if sha(data) != SOURCE_SHA[relative]: raise ValueError('admitted source drift')
            extra = (b'\npub fn run_accounting_review() { fixture_envelope::accounting_review::run(); }\n'
                     if relative.endswith('analyzer.rs') else b'\n#[path = "../accounting_probes.rs"]\npub(crate) mod accounting_review;\n')
            target = build/relative; target.write_bytes(data + extra)
            result['sources'].append({'path': str(target.relative_to(ROOT)), 'frozen_prefix_bytes': len(data), 'frozen_prefix_sha256': sha(data), 'complete_bytes': len(data+extra), 'complete_sha256': sha(data+extra), 'change': 'append own probe-access module only; frozen prefix unchanged'})
        for name in ['accounting_probes.rs', 'run_frozen.py', 'admit_frozen.py']:
            data = (OWN/name).read_bytes()
            if name.endswith('.rs'): (build/name).write_bytes(data)
            result['sources'].append({'path': str((OWN/name).relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
        driver = build/'driver.rs'
        driver.write_text('#[path = "src/analyzer.rs"]\npub mod analyzer;\nfn main() { analyzer::run_accounting_review(); }\n')
        result['sources'].append({'path': str(driver.relative_to(ROOT)), 'bytes': driver.stat().st_size, 'sha256': sha(driver.read_bytes())})
        baseline = ROOT/'verification/swift-ordered-retention-analyzer-envelope/inputs/accepted-inventory.json'
        data = baseline.read_bytes()
        if sha(data) != '28f4c947715993c80f6d03297b9050ad38046d18fa4d94561463ab54a18bb2b1': raise ValueError('baseline inventory drift')
        (run/'accepted-inventory.json').write_bytes(data)
        result['baseline_inventory'] = {'path': str(baseline.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}
        call('compile', [str(RUSTC), '--edition=2024', '-Dwarnings', str(driver), '-o', str(binary)])
        result['binary'] = {'bytes': binary.stat().st_size, 'sha256': sha(binary.read_bytes())}
        out = call('probes', [str(binary)])
        if 'ACCOUNTING_PROBES_PASSED=7 PRODUCT_ACCEPTANCE=0' not in out: raise ValueError('probe success marker absent')
        result['after'] = verify_seal()
        result['status'] = 'seven-host-accounting-probes-passed-source-accounting-review-pending'
        result['probe_methods_passed'] = 7
    except BaseException as exc:
        result['status'] = 'failed-attempt-retained'
        result['error'] = f'{type(exc).__name__}: {exc}'
        (run/'runner.stderr.txt').write_text(traceback.format_exc())
        raise
    finally:
        if binary.exists(): binary.unlink()
        result['cleanup'] = 'All synchronous rustc/probe children returned and were reaped. Owned executable removed after hashing; exact build source and raw output retained. No product/native/capture/process/device discovery.'
        write_json(run/'receipt.json', result)
    print(json.dumps({'status': result['status'], 'probe_methods_passed': result.get('probe_methods_passed', 0), 'product_acceptance': False}, sort_keys=True))

if __name__ == '__main__': main()
