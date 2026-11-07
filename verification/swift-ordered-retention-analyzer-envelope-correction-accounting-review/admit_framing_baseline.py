#!/usr/bin/env python3
"""Pin the accepted framing source/step declaration; no baseline replay."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import sys
from admit_proposal import verify_proposal

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
SEAL = ROOT/'verification/swift-ordered-retention-analyzer-library/seal.json'
EXPECTED = '777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63'
def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    run = OWN/'commands/framing-baseline-admission-1'; run.mkdir(parents=True, exist_ok=False)
    raw = SEAL.read_bytes(); assert sha(raw) == EXPECTED
    seal = json.loads(raw); members = {m['path']: m for m in seal['members']}
    selected = ['docs/swift-ordered-retention-analyzer-library.md', 'verification/swift-ordered-retention-analyzer-library/src/analyzer.rs']
    copies = []
    for relative in selected:
        item = members[relative]; data = (ROOT/relative).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']
        target = run/Path(relative).name; target.write_bytes(data)
        copies.append({'path': relative, 'bytes': len(data), 'sha256': sha(data), 'copy': str(target.relative_to(ROOT))})
    (run/'accepted-seal.json').write_bytes(raw)
    source = (run/'analyzer.rs').read_bytes()
    candidate = (OWN/'commands/proposal-admission-1/inputs/source-analyzer.rs').read_bytes()
    assert candidate.startswith(source)
    assert b'const RECORD_STEPS: u64 = 22;' in source
    assert b'ordinary records22' in (run/'swift-ordered-retention-analyzer-library.md').read_bytes()
    assert sha(SEAL.read_bytes()) == EXPECTED
    verify_proposal()
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'invocation': sys.orig_argv,
               'status': 'accepted-framing-source-and22declaration-pinned-no-baseline-reproving',
               'accepted_seal_sha256': EXPECTED, 'copies': copies,
               'accepted_source_exact_prefix': True, 'baseline_runtime_replayed': False,
               'producer_code_executed': False, 'numeric_selection': False,
               'native_capture_process_or_device_discovery': False}
    (run/'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'status': receipt['status'], 'copies': len(copies)}, sort_keys=True))
if __name__ == '__main__': main()
