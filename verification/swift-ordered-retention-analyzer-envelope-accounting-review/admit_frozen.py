#!/usr/bin/env python3
"""Verify frozen bytes and copy bounded review closure; execute no producer code."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import traceback

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/swift-ordered-retention-analyzer-envelope'
SEAL_SHA = 'ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae'
SOURCE_SHA = {
    'src/analyzer.rs': '1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b',
    'src/envelope.rs': '80eb9830ed78b1122ff3ec0723e1ce20afb46fd4a4e5abf80c60c4883a65a84e',
    'tests/fixture_tests.rs': 'a2980d7586c88b0a76aa9aef2a74789d516186e562078ecb8522bf2b6c05b6f2',
    'tests/envelope_tests.rs': 'ea6aa417dc282b251eb280f45013a95cc97543181e883bebb254c7895c095c57',
    'tests/independent_tests.rs': 'f5a56f984fb087edc86a50388a3b014902c965dae6a3787031fc1c56f269891d',
    'tests/private_io_tests.rs': '432533ea0760b3860d74f763dd3ce6eb3a8c63377cdd53f697153df75012eb18',
    'source-accounting.md': '3348b6c06b5e5511018840070c2d1c2b3cbe691ffe83adcab3e931bc64ea0d9d',
    'logical-inventory.json': '5507871189d3876b6d19406d782869b8355c5f6c5545f1f654d1a17db5af0bb7',
    'step-inventory.json': '449f06a0ec183269cee75c13cc1c77b2f68719762845473106e42f72f6199d15',
}

def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def verify_seal():
    raw = (PACKET / 'seal.json').read_bytes()
    if sha(raw) != SEAL_SHA: raise ValueError('seal mismatch')
    seal = json.loads(raw)
    count = 0
    total = 0
    for item in seal['members']:
        path = ROOT / item['path']
        if not path.is_relative_to(ROOT): raise ValueError('member outside root')
        data = path.read_bytes()
        if len(data) != item['bytes'] or sha(data) != item['sha256']:
            raise ValueError(f'sealed member mismatch: {item["path"]}')
        count += 1
        total += len(data)
    if (count, total) != (796, 148892063): raise ValueError('frozen member count/bytes mismatch')
    return {'seal_sha256': SEAL_SHA, 'members': count, 'bytes': total}

def main():
    run = OWN / 'commands/frozen-admission-1'
    run.mkdir(parents=True, exist_ok=False)
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'invocation': sys.orig_argv,
              'scope': 'frozen admission and bounded source copies only', 'product_execution': False,
              'native_capture_process_or_device_discovery': False, 'status': 'started'}
    try:
        result['before'] = verify_seal()
        dest = run / 'inputs'
        dest.mkdir()
        members = {item['path']: item for item in json.loads((PACKET/'seal.json').read_bytes())['members']}
        result['copies'] = []
        for relative in list(SOURCE_SHA) + ['final-receipt.json', 'seal.json', 'seal.sha256']:
            path = PACKET / relative
            data = path.read_bytes()
            expected = SOURCE_SHA.get(relative)
            if expected is None and relative not in ['seal.json', 'seal.sha256']:
                expected = members[str(path.relative_to(ROOT))]['sha256']
            if expected and sha(data) != expected: raise ValueError(f'input mismatch: {relative}')
            target = dest / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            result['copies'].append({'path': str(path.relative_to(ROOT)), 'copy': str(target.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
        p = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, capture_output=True, check=False)
        result['revision_context'] = {'argv': ['git', 'rev-parse', 'HEAD'], 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
        result['independent_closure_tree_sha256'] = sha(json.dumps(result['copies'], sort_keys=True, separators=(',', ':')).encode())
        result['after'] = verify_seal()
        result['status'] = 'frozen-closure-admitted-for-bounded-review-not-accepted'
        output = json.dumps({'status': result['status'], 'seal_sha256': SEAL_SHA, 'members': result['after']['members'], 'copies': len(result['copies'])}, sort_keys=True)+'\n'
        (run/'stdout.txt').write_text(output)
        (run/'stderr.txt').write_text('')
        write_json(run/'receipt.json', result)
        print(output, end='')
    except BaseException as exc:
        result['status'] = 'failed-attempt-retained'
        result['error'] = f'{type(exc).__name__}: {exc}'
        write_json(run/'receipt.json', result)
        (run/'stderr.txt').write_text(traceback.format_exc())
        raise

if __name__ == '__main__': main()
