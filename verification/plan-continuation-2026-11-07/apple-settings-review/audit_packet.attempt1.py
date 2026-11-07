#!/usr/bin/env python3
"""Read-only audit of exact packet/source/product bindings."""
import hashlib
import json
from pathlib import Path
import stat
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIX = HERE.parent / 'apple-settings-fix'
BUILD = REPO / 'verification/apple-passive-lifecycle-sendable-correction/build-attempt-1'
PREP = REPO / 'verification/apple-passive-lifecycle-runtime-preparation'
REL = 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_bytes())
stable = lambda v: (json.dumps(v, sort_keys=True, indent=2) + '\n').encode()


def payload(path, prefix=''):
    result = {}
    with tarfile.open(path) as archive:
        for entry in archive:
            assert entry.name.startswith(prefix)
            name = entry.name.removeprefix(prefix)
            assert name not in result and '..' not in Path(name).parts and not Path(name).is_absolute()
            if entry.isdir():
                continue
            assert entry.isfile(), (entry.name, entry.type)
            value = archive.extractfile(entry).read()
            result[name] = (value, {'kind': 'file', 'mode': entry.mode, 'bytes': len(value), 'sha256': sha(value)})
    return result


packet = read(FIX / 'candidate-packet.json')
handoff = read(FIX / 'handoff.json')
assert sha((FIX / 'candidate-packet.json').read_bytes()) == handoff['packetSHA256']
member_hashes = {}
for name, row in handoff['members'].items():
    path = FIX / name
    data = path.read_bytes()
    assert path.resolve() == path and not path.is_symlink()
    assert len(data) == row['bytes'] and sha(data) == row['sha256'], name
    assert stat.S_IMODE(path.stat().st_mode) == row['mode'], name
    member_hashes[name] = sha(data)
bindings = {}
for key, row in packet.items():
    if isinstance(row, dict) and set(row) == {'path', 'bytes', 'sha256'}:
        path = REPO / row['path']
        raw = path.read_bytes()
        assert not path.is_symlink() and path.resolve() == path
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], key
        bindings[key] = row
baseline = payload(REPO / packet['baselineRuntimeArchive']['path'], 'selected/')
candidate = payload(FIX / 'candidate-runtime-sources.tar.gz', 'selected/')
assert set(baseline) == set(candidate) == set(packet['runtimeFiles'])
assert {n: row for n, (_, row) in candidate.items()} == packet['runtimeFiles']
assert {n: row for n, (_, row) in baseline.items()} == read(PREP / 'runtime-source-manifest.json')['files']
changed = [n for n in baseline if baseline[n] != candidate[n]]
assert changed == [REL], changed
for name, (data, _) in baseline.items():
    assert (FIX / 'baseline-runtime' / name).read_bytes() == data
assert candidate[REL][0] == (FIX / 'candidate/settings_telemetry.py').read_bytes()
selection = read(FIX / 'candidate-selection-template.json')
expected = read(PREP / 'selection-template.json')
expected['files'][REL] = candidate[REL][1]['sha256']
assert selection == expected
assert selection['files'] == {n: row['sha256'] for n, (_, row) in candidate.items()}
assert selection['methods'] == ['test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab']
assert selection['cases'] == ['keyboard-enabled-off']
compiled = payload(REPO / packet['baselineCompileArchive']['path'])
source_manifest = read(BUILD / 'source-manifest.json')
assert {n: row for n, (_, row) in compiled.items()} == source_manifest['sources']
for name, (data, _) in compiled.items():
    assert data == (FIX / 'baseline-compile' / name).read_bytes()
products = payload(REPO / packet['productArchive']['path'])
product_manifest = read(BUILD / 'product-manifest.json')
assert {n: row for n, (_, row) in products.items()} == product_manifest['products']
assert product_manifest == selection['productManifest']
assert product_manifest['sourceTreeSHA256'] == source_manifest['sourceTreeSHA256'] == packet['sourceTreeSHA256']
# The template retains a historical absolute path. Verify its actual target too.
literal_product = Path(selection['productArchive'])
assert sha(literal_product.read_bytes()) == packet['productArchive']['sha256']
result = dict(passed=True, handoffMembersVerified=len(member_hashes), packetSHA256=handoff['packetSHA256'],
              bindings=bindings, changedRuntimeFiles=changed, runtimeFilesUnchanged=len(candidate)-1,
              compileSourcesVerified=len(compiled), productFilesVerified=len(products),
              sourceTreeSHA256=packet['sourceTreeSHA256'],
              candidateRuntimeTreeSHA256=sha(stable(packet['runtimeFiles'])),
              baselineSourceSHA256=baseline[REL][1]['sha256'], candidateSourceSHA256=candidate[REL][1]['sha256'],
              selectionOnlyChangedCandidateSourceHash=True, literalProductPathMatches=True,
              literalProductPath=str(literal_product), methods=selection['methods'], cases=selection['cases'],
              memberHashes=member_hashes, noPackagingScriptsExecuted=True)
(HERE / 'packet-audit.json').write_bytes(stable(result))
print(json.dumps({k: v for k, v in result.items() if k not in ['memberHashes', 'bindings']}, indent=2))
