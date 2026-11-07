#!/usr/bin/env python3
"""Fresh actual layouts only. Never runs budget-dependent proposal behavior."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import traceback
from admit_proposal import verify_proposal
from prepare_baseline import verify_old_seals

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
INPUT = OWN/'commands/proposal-admission-1/inputs'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def main():
    run = OWN/'commands/proposal-layout-1'; run.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'invocation': sys.orig_argv,
               'status': 'started', 'commands': [], 'sources': [], 'cost_dependent_behavior_executed': False,
               'producer_tests_or_scripts_executed': False, 'numeric_selection': False,
               'native_capture_process_or_device_discovery': False}
    binary = run/'build/layout-probe'
    def call(name, argv):
        p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
        (run/(name+'.stdout.txt')).write_text(p.stdout); (run/(name+'.stderr.txt')).write_text(p.stderr)
        receipt['commands'].append({'name': name, 'argv': argv, 'exit_code': p.returncode})
        if p.returncode: raise RuntimeError(f'{name} failed; raw output retained')
        return p.stdout
    try:
        receipt['proposal_before'] = verify_proposal(); receipt['old_before'] = verify_old_seals()
        call('revision', ['git', 'rev-parse', 'HEAD']); call('python-version', [sys.executable, '--version'])
        call('rustc-version', [str(RUSTC), '--version', '--verbose'])
        receipt['tools'] = [{'path': str(p.resolve()), 'bytes': len(p.resolve().read_bytes()), 'sha256': sha(p.resolve().read_bytes())} for p in [Path(sys.executable), RUSTC]]
        build = run/'build'; (build/'src').mkdir(parents=True)
        for name, target_name, expected, append in [
            ('source-analyzer.rs', 'analyzer.rs', '1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b', b'\npub fn run_layout_review() { fixture_envelope::proposal_layout::run(); }\n'),
            ('source-envelope.rs', 'envelope.rs', 'e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535', b'\n#[path = "../proposal_layout.rs"]\npub(crate) mod proposal_layout;\n'),
        ]:
            data = (INPUT/name).read_bytes(); assert sha(data) == expected
            target = build/'src'/target_name; target.write_bytes(data+append)
            receipt['sources'].append({'path': str(target.relative_to(ROOT)), 'frozen_prefix_bytes': len(data), 'frozen_prefix_sha256': sha(data), 'complete_sha256': sha(data+append), 'change': 'only append own layout-access module'})
        data = (OWN/'proposal_layout.rs').read_bytes(); (build/'proposal_layout.rs').write_bytes(data)
        receipt['sources'].append({'path': str((OWN/'proposal_layout.rs').relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
        driver = build/'driver.rs'; driver.write_text('#[path = "src/analyzer.rs"]\npub mod analyzer;\nfn main() { analyzer::run_layout_review(); }\n')
        receipt['sources'].append({'path': str(driver.relative_to(ROOT)), 'bytes': driver.stat().st_size, 'sha256': sha(driver.read_bytes())})
        call('compile', [str(RUSTC), '--edition=2024', '-Dwarnings', str(driver), '-o', str(binary)])
        receipt['binary'] = {'bytes': binary.stat().st_size, 'sha256': sha(binary.read_bytes())}
        out = call('layout', [str(binary)]); assert 'PROBE_TYPES=32 COST_DEPENDENT_BEHAVIOR_EXECUTED=0 NUMERIC_SELECTION=0' in out
        receipt['proposal_after'] = verify_proposal(); receipt['old_after'] = verify_old_seals()
        receipt['status'] = '32-actual-layouts-pass-unit-result40-proposal-source-audit-separate'
    except BaseException as exc:
        receipt['status'] = 'failed-attempt-retained'; receipt['error'] = f'{type(exc).__name__}: {exc}'
        (run/'runner.stderr.txt').write_text(traceback.format_exc()); raise
    finally:
        if binary.exists(): binary.unlink()
        receipt['cleanup'] = 'Synchronous compiler/layout children returned and were reaped. Own executable hashed then removed; exact source prefixes and raw outputs retained. No budget-dependent library function, producer runner/test, native/capture/process/device work.'
        write_json(run/'receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'cost_dependent_behavior_executed': False, 'numeric_selection': False}, sort_keys=True))
if __name__ == '__main__': main()
