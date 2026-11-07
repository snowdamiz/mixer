#!/usr/bin/env python3
"""Own bookkeeping only; never imports or executes producer/product inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
INPUTS = {
    'docs/swift-ordered-retention-analyzer-fsm-contract.md': '110b68a334d2ced33d9776c0a2854b56e35707bfc4d7a00ec019636bf23a2f1a',
    'verification/swift-ordered-retention-analyzer-fsm-contract/model.py': '15480f7b67bd3705cd485a51dd1b5c87e64cb0fa6854414d9fa2daa7595ed488',
    'verification/swift-ordered-retention-analyzer-envelope/commands/preparation-2/proposal.md': '32e3c49a1640c15f807c45f6a24c09c6c595e1e4f79f69c2938f47d31275be7d',
    'verification/swift-ordered-retention-analyzer-envelope-root-review/interface-selection.json': '3058c7a0c3dfed57842014874db94b8014c6e8beee4386cce6478b6615634e64',
    'verification/swift-ordered-retention-analyzer-envelope-root-review/implementation-accounting-addendum.json': '242b19079476ab4ee8437f4e7df04d8ebb584e899f7dab7bef537c8330f526dc',
    'verification/swift-ordered-retention-analyzer-library/src/analyzer.rs': 'ce8f3013f7ecc9ccdb5ca88db75b7019f6af24cff995907d5d95012edb5d1757',
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def command(argv: list[str]) -> dict[str, object]:
    p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
    return {'argv': argv, 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

def main() -> None:
    name = sys.argv[1]
    if not name.startswith('preaccess-') or '/' in name or '..' in name:
        raise ValueError('fresh owned preaccess run name required')
    run = OWN / 'commands' / name
    run.mkdir(parents=True, exist_ok=False)
    snapshots = run / 'inputs'
    snapshots.mkdir()
    result: dict[str, object] = {
        'schema': 1,
        'at': datetime.now(timezone.utc).isoformat(),
        'status': 'started',
        'scope': 'independent pre-access accounting obligations; no product execution or acceptance',
        'invocation': sys.orig_argv,
        'commands': [],
        'inputs': [],
        'checks': [],
        'pending': ['frozen implementation', 'complete Rust layouts', 'combined lexical inventory', 'numeric W', 'numeric G', 'numeric additional fixed setup/final work', 'combined preflight qualification'],
        'product_acceptance': False,
        'combined_lifetime_qualified': False,
        'combined_debit_preflight_qualified': False,
        'native_capture_device_or_process_discovery': False,
        'producer_or_product_execution': False,
        'cleanup': 'Only immutable source copies and bookkeeping receipts are created. No disposable native, capture, simulator or product process is started or queried.',
    }
    try:
        for argv in [['git', 'rev-parse', 'HEAD'], [sys.executable, '--version'], [str(RUSTC), '--version', '--verbose']]:
            item = command(argv)
            result['commands'].append(item)
            if item['exit_code'] != 0:
                raise RuntimeError(f'bookkeeping tool command failed: {argv!r}')
        result['host'] = {'system': platform.system(), 'machine': platform.machine()}
        result['review_source'] = []
        for path in [Path(__file__).resolve(), ROOT / 'docs/swift-ordered-retention-analyzer-envelope-accounting-review.md']:
            data = path.read_bytes()
            result['review_source'].append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
        result['tool_files'] = []
        for path in [Path(sys.executable).resolve(), RUSTC.resolve()]:
            data = path.read_bytes()
            result['tool_files'].append({'path': str(path), 'bytes': len(data), 'sha256': sha(data)})
        for relative, expected in INPUTS.items():
            data = (ROOT / relative).read_bytes()
            actual = sha(data)
            copy = snapshots / relative.replace('/', '__')
            copy.write_bytes(data)
            item = {'path': relative, 'bytes': len(data), 'sha256': actual, 'expected_sha256': expected, 'copy': str(copy.relative_to(ROOT))}
            result['inputs'].append(item)
            if actual != expected:
                raise RuntimeError(f'pinned input mismatch: {relative}')
        manifest = [{'path': item['path'], 'bytes': item['bytes'], 'sha256': item['sha256']} for item in result['inputs']]
        result['consulted_input_tree_sha256'] = sha(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())

        def check(name: str, condition: bool, evidence: object) -> None:
            result['checks'].append({'name': name, 'pass': condition, 'evidence': evidence})
            if not condition:
                raise AssertionError(name)

        check('existing transient reservation arithmetic', 41984 + 23552 == 65536, {'reserved': 41984, 'unassigned_not_spendable': 23552, 'ceiling': 65536})
        check('fixed report plus future host arithmetic', 49152 + 8192 == 57344 <= 65536, {'report': 49152, 'future_host': 8192, 'aggregate': 57344})
        cells = [7, 9, 10, 11, 12, 13, 14, 64, 65, 66, 160, 161]
        check('exact twelve distinct selected cells', len(cells) == len(set(cells)) == 12 and max(cells) < 512, cells)
        check('candidate payload confined to bytes888through983', 888 + 12 * 8 == 984 and 984 < 2048, {'start': 888, 'exclusive_end': 984, 'payload_bytes': 96, 'complete_owner': 2048})
        schedule = [16, 12, 12, 24, 12, 12, 12, 12, 4, 12]
        check('accepted fixed leaf groups total128', sum(schedule) == 128, schedule)
        check('candidate setup total534', 256 + 256 + 12 + 2 + 4 + 4 == 534, [256, 256, 12, 2, 4, 4])
        check('no-call debit542', 534 + 8 == 542, {'S': 1, 'F': 1, 'N': 0, 'reply_valid': 0, 'debit': 542})
        debit_cases = []
        for s, f, n in [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 1, 3), (1, 1, 4194304)]:
            debit_cases.append({'S': s, 'F': f, 'N': n, 'debit': 534*s + 8*f + 128*n})
        check('public debit finite boundary cases', [v['debit'] for v in debit_cases] == [0, 534, 542, 670, 926, 536871454], debit_cases)
        check('public counter bound is not capacity', debit_cases[-1]['debit'] < 2**64, {'u64_safe': True, 'achievable_record_count_claimed': False})
        check('wrapper W remains unselected', 8192 - 22 - 128 == 8042, {'maximum_arithmetic_W_only': 8042, 'selected_W': None, 'padding_bucket_permitted': False, 'mandatory_preflight': 8192})
        check('fixed reserved ceiling arithmetic', 1048576 + 640000 + 65536 + 263584 + 3000000 == 5017696, {'fixed_ceiling_sum': 5017696, 'available_replay_not_promised': 268435456 - 5017696})
        result['planned_probes'] = [
            'actual complete Rust layouts including Results Options constructors references and callers',
            'lexical phase and helper-chain reconciliation within existing assigned groups',
            'candidate single owner source lifetime payload canaries and all selected arena writes',
            'setup finish G and extra fixed reservation-before-mutation failures',
            'private underfund first/later calls remaining0 127 128 129 prior reads debit0 no mutation latch',
            'main preflight8191 8192 and B-1 B B+1 strict admission',
            'decode-failure and latch-skip prepaid128 no refunds truthful cumulative debit',
            'source-derived128 W G setup final operations with all copy/move and error branches',
            'report total steps includes all charged work before final step serialization',
        ]
        for item in result['inputs']:
            if sha((ROOT / item['path']).read_bytes()) != item['sha256']:
                raise RuntimeError(f'input changed during bookkeeping: {item["path"]}')
        result['before_after_inputs_match'] = True
        result['status'] = 'pre-access-obligations-established-awaiting-frozen-source'
        write_json(run / 'result.json', result)
        output = json.dumps({'status': result['status'], 'checks': len(result['checks']), 'inputs': len(result['inputs']), 'tree_sha256': result['consulted_input_tree_sha256'], 'product_acceptance': False}, sort_keys=True) + '\n'
        (run / 'stdout.txt').write_text(output)
        (run / 'stderr.txt').write_text('')
        print(output, end='')
    except BaseException as exc:
        result['status'] = 'failed-attempt-retained'
        result['error'] = f'{type(exc).__name__}: {exc}'
        write_json(run / 'result.json', result)
        (run / 'stdout.txt').write_text('')
        (run / 'stderr.txt').write_text(traceback.format_exc())
        raise

if __name__ == '__main__':
    main()
