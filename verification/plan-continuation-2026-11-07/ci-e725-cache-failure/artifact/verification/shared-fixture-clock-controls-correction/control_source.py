"""Exact one-line correction to the frozen runner-control source; no runner overlay."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / 'verification/cache-fixture-shared-input-candidate-v2/test_runner.py'
SOURCE_BYTES = 27413
SOURCE_SHA256 = 'e7ce50d89ef974d26d8c7a449f84964d6df36d7a279df6013dba932937f4e257'
BEFORE = b'  clock=types.SimpleNamespace(monotonic=mock.Mock(return_value=100.0))\n'
AFTER = BEFORE + b'  c.deadline=clock.monotonic()+20\n'


def control_source(corrected=True):
    for path in [*reversed(FROZEN.parents), FROZEN]:
        if path.is_symlink():
            raise RuntimeError('Frozen control source symlink forbidden')
    if not FROZEN.is_file():
        raise RuntimeError('Frozen control source must be regular')
    source = FROZEN.read_bytes()
    if len(source) != SOURCE_BYTES or hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('Frozen control source preimage differs')
    if source.count(BEFORE) != 1 or AFTER in source:
        raise RuntimeError('Exact clock correction preimage differs')
    return source.replace(BEFORE, AFTER, 1) if corrected else source
