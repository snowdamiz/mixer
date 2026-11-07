#!/usr/bin/env python3
"""Correct one independently authored fixture packing word; preserve all prior evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import struct

BASE = Path(__file__).resolve().parent
source = BASE / 'pre-access-vectors/run-1'
target = BASE / 'corrected-vectors/profile-correction-1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source / 'manifest.json') == '28fe5c0a510c5e414fb8b2e661ebe064612eda9e2d05f627a628ba3652f730a3'
shutil.copytree(source, target)
profile = bytearray((target / 'profile.bin').read_bytes())
offset = 512 + 17 * 32
assert struct.unpack_from('<Q', profile, offset)[0] == (1 << 32) | 2
struct.pack_into('<Q', profile, offset, (2 << 32) | 1)
(target / 'profile.bin').write_bytes(profile)
for case in json.loads((source / 'manifest.json').read_text())['vectors']:
    for suffix, expected in [('stream', case['stream_sha256']), ('context', case['context_sha256'])]:
        assert sha(target / (case['id'] + '.' + suffix + '.bin')) == expected
receipt = dict(schema=1, scope='Review fixture encoding correction only; no producer changes or expectation changes',
    original_manifest_sha256=sha(source/'manifest.json'), original_profile_sha256=sha(source/'profile.bin'),
    corrected_profile_sha256=sha(target/'profile.bin'), byte_offset=offset,
    original_word=(1<<32)|2, corrected_word=(2<<32)|1,
    explanation='Profile row packs defined in low32 and type in high32. Correct row17 to defined1/type2 instead of invalid defined2/type1.',
    unchanged_streams=33, unchanged_contexts=33, unchanged_behavioral_expectations=33,
    prior_failed_run='implementation-review-1/public/run-1',
    script_sha256=sha(Path(__file__)), product_executed_by_this_command=False)
(target / 'correction.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
shutil.copy2(__file__, target/'executed-correction.py')
print(json.dumps(receipt))
