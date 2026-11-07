#!/usr/bin/env python3
"""Pre-access bookkeeping only: never reads mutable correction packet."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import traceback

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
DOC = ROOT/'docs/swift-ordered-retention-analyzer-envelope-correction-accounting-review.md'
INPUTS = {
    'verification/swift-ordered-retention-analyzer-envelope-root-review/copy-unit-clarification.json': '87bc80cee002a3993edd5e368397ea717b0add57b17a2074b5b8ffc799f3f9d8',
    'verification/swift-ordered-retention-analyzer-envelope-root-review/revision-selection.json': '1184dffc486d9ff227677f942b3e4666a922975e08a6fa29edc84df5386e672d',
    'verification/swift-ordered-retention-analyzer-envelope/seal.json': 'ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae',
    'verification/swift-ordered-retention-analyzer-envelope-accounting-review/seal.json': '225d35ccd2c76c6306f7be21d3931c57a47ba6263897ba1847bfe7995226bf7f',
}
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def verify_old_seals():
    result = []
    for relative, expected in INPUTS.items():
        if not relative.endswith('/seal.json'): continue
        raw = (ROOT/relative).read_bytes()
        if sha(raw) != expected: raise ValueError('immutable old seal drift')
        seal = json.loads(raw)
        total = 0
        for member in seal['members']:
            data = (ROOT/member['path']).read_bytes()
            if len(data) != member['bytes'] or sha(data) != member['sha256']: raise ValueError(f'old sealed member drift: {member["path"]}')
            total += len(data)
        result.append({'path': relative, 'sha256': expected, 'members': len(seal['members']), 'bytes': total})
    return result

def main():
    run = OWN/'commands/preaccess-1'
    run.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'invocation': sys.orig_argv,
               'status': 'started', 'inputs': [], 'commands': [],
               'scope': 'amended accounting pre-access rules and immutable-history custody only',
               'mutable_correction_packet_read': False, 'new_runtime_probe_executed': False,
               'historical_seven_probes_reclassified': False, 'numeric_amendment_selected': False,
               'product_acceptance': False, 'combined_lifetime_qualified': False, 'combined_debit_preflight_qualified': False,
               'native_capture_process_or_device_discovery': False}
    try:
        receipt['before'] = verify_old_seals()
        dest = run/'inputs'; dest.mkdir()
        for relative, expected in INPUTS.items():
            data = (ROOT/relative).read_bytes()
            if sha(data) != expected: raise ValueError(f'pinned input drift: {relative}')
            target = dest/relative.replace('/', '__'); target.write_bytes(data)
            receipt['inputs'].append({'path': relative, 'copy': str(target.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
        for name, argv in [('revision', ['git', 'rev-parse', 'HEAD']), ('python-version', [sys.executable, '--version'])]:
            p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
            (run/(name+'.stdout.txt')).write_text(p.stdout); (run/(name+'.stderr.txt')).write_text(p.stderr)
            receipt['commands'].append({'name': name, 'argv': argv, 'exit_code': p.returncode})
            if p.returncode: raise RuntimeError('bookkeeping command failed')
        path = Path(sys.executable).resolve(); data = path.read_bytes()
        receipt['tool'] = {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}
        receipt['review_sources'] = [{'path': str(path.relative_to(ROOT)), 'bytes': len(path.read_bytes()), 'sha256': sha(path.read_bytes())} for path in [Path(__file__).resolve(), DOC]]
        receipt['consulted_input_tree_sha256'] = sha(json.dumps(receipt['inputs'], sort_keys=True, separators=(',', ':')).encode())
        receipt['transfer_examples'] = [
            {'actual_copy_edges': 1, 'complete_edge_bytes': [16], 'concurrent_place_bytes': [16, 16], 'step_copy_groups': 1, 'logical_bytes': 32},
            {'actual_copy_edges': 2, 'complete_edge_bytes': [16, 16], 'concurrent_place_bytes': [16, 16, 16], 'step_copy_groups': 2, 'logical_bytes': 48},
        ]
        for case in receipt['transfer_examples']:
            assert case['actual_copy_edges'] == case['step_copy_groups']
            assert sum(case['concurrent_place_bytes']) == case['logical_bytes']
            assert all(0 < n <= 128 for n in case['complete_edge_bytes'])
        receipt['required_coverage'] = ['operation and transfer IDs without source/destination double counting', 'complete values and lexical lifetime places', 'exact accepted framing22 source/ledger/call crosswalk', 'all added repeated changed work charged independently', 'strict leaf total and explicit contract-amendment boundary if above128', 'no historical runtime test promoted to amended pass']
        receipt['after'] = verify_old_seals()
        assert receipt['before'] == receipt['after']
        receipt['status'] = 'preaccess-baseline-ready-awaiting-frozen-amended-proposal'
        output = json.dumps({'status': receipt['status'], 'pinned_inputs': len(receipt['inputs']), 'old_sealed_members_unchanged': sum(x['members'] for x in receipt['after']), 'new_runtime_probe_executed': False, 'numeric_amendment_selected': False}, sort_keys=True)+'\n'
        (run/'stdout.txt').write_text(output); (run/'stderr.txt').write_text('')
        print(output, end='')
    except BaseException as exc:
        receipt['status'] = 'failed-bookkeeping-attempt-retained'; receipt['error'] = f'{type(exc).__name__}: {exc}'
        (run/'stderr.txt').write_text(traceback.format_exc())
        raise
    finally:
        receipt['cleanup'] = 'Only immutable copies and bookkeeping outputs created. Both synchronous bookkeeping children returned/reaped; no runtime product/native/capture/simulator/process/device work or cleanup.'
        write_json(run/'receipt.json', receipt)

if __name__ == '__main__': main()
