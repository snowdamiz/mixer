#!/usr/bin/env python3
"""Reconstruct only the accepted sealed source and append independent controls."""
from pathlib import Path
import difflib, hashlib, json, tarfile

H = Path(__file__).resolve().parent
R = H.parent.parent
C = H.parent / 'swift-cache-current-attribution-observer'
P = H.parent / 'swift-plan-cache-remaining-work-diagnosis'
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_text())
dump = lambda p, x: p.write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')
assert sha((C/'seal.json').read_bytes()) == 'e4a520641fbad904381bc7438feb0baee4dfca7d716806262da80ac4b20f0305'
seal = load(C/'seal.json')
assert len(seal['files']) == 43
for n, d in seal['files'].items():
    assert sha((C/n).read_bytes()) == d, n
for n, d in seal['externalFiles'].items():
    assert sha((R/n).read_bytes()) == d, n
assert sha((P/'seal.json').read_bytes()) == '3a52d3f20cf852da7521fc3345a177ef6f8a7f157ebf2da7e3e63d01bc725b3d'
parent = load(P/'seal.json')
assert len(parent['files']) == 46
for n, d in parent['files'].items():
    assert sha((P/n).read_bytes()) == d, n
base = load(C/'baseline-manifest.json')
assert sha((C/'baseline-manifest.json').read_bytes()) == '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
candidate = load(C/'copied-source-manifest.json')
assert sha((C/'copied-source-manifest.json').read_bytes()) == 'b825aa00bbc545863c7ab9bc12b0c8745395869ca44e533b541da8766e8a5bbb'
assert sha((C/'isolated-source.tar.gz').read_bytes()) == 'cdbf6b5826a354fa7796d3f4e4573b2fe62a213e4f3f5adf944cc2d2e44fbf18'
with tarfile.open(C/'isolated-source.tar.gz', 'r:gz') as t:
    members = t.getmembers()
    assert len(members) == len(candidate) == len(base) == 132
    assert len(set(m.name for m in members)) == 132
    assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    source = {m.name: t.extractfile(m).read() for m in members}
assert {n: sha(b) for n,b in source.items()} == candidate
changed = sorted(n for n in base if base[n] != candidate[n])
assert changed == ['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
original = {n: (P/'originals'/n).read_bytes() for n in changed}
assert all(sha(original[n]) == base[n] for n in changed)
patch = ''.join(''.join(difflib.unified_diff(original[n].decode().splitlines(True),source[n].decode().splitlines(True),fromfile='accepted/'+n,tofile='isolated/'+n)) for n in changed)
assert patch.encode() == (C/'instrumentation.patch').read_bytes()
assert sha(patch.encode()) == '0c0f99d5c38db3f39c9cc05be898a82f88634928ccbe1e009ffd6f772e3d531b'
testpath = changed[2]
assert source[testpath] == original[testpath] + b'\n' + (C/'observer-and-controls.rs').read_bytes()
# The preceding diagnosis changed only these same three files. Recover its
# exact accepted VM baseline without reading a live VM directory.
with tarfile.open(P/'isolated-source.tar.gz', 'r:gz') as t:
    prior = {m.name:t.extractfile(m).read() for m in t.getmembers()}
baseline = dict(prior)
baseline.update(original)
assert {n:sha(b) for n,b in baseline.items()} == base
assert all(source[n] == baseline[n] for n in source if n not in changed)
assert b'[dependencies]' not in source['Cargo.toml'] and b'build =' not in source['Cargo.toml']
assert 'build.rs' not in source
for n in ['AGENTS.md','PLAN.md','STATUS.md']:
    out = H/'context'/n
    out.parent.mkdir(exist_ok=True)
    out.write_bytes((R/n).read_bytes())
audit = {'candidateSealSHA256':sha((C/'seal.json').read_bytes()),'candidateMembers':len(seal['files']),
    'parentMembers':len(parent['files']),'sourceFiles':len(source),'unchangedBaselineFiles':129,
    'changedFiles':changed,'baselineClosure':sha((C/'baseline-manifest.json').read_bytes()),
    'candidateSourceManifestSHA256':sha((C/'copied-source-manifest.json').read_bytes()),
    'minimalPatchSHA256':sha(patch.encode()),'candidateArchiveSHA256':sha((C/'isolated-source.tar.gz').read_bytes()),
    'originalTestsPrefixByteIdentical':True,'liveSourceRead':False,'gitQueried':False,
    'contextRevisionProvidedByRoot':'6b8aba350224ed19f678669bdbea6b359d8de68b',
    'contextArchives':{n:sha((H/'context'/n).read_bytes()) for n in ['AGENTS.md','PLAN.md','STATUS.md']}}
dump(H/'source-audit.json',audit)
S = H/'owned-source'
assert not S.exists()
S.mkdir()
for n,b in source.items():
    p=S/n
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(b)
test = (H/'independent-controls.rs').read_bytes()
(S/testpath).write_bytes(source[testpath]+b'\n'+test)
manifest = {str(p.relative_to(S)):sha(p.read_bytes()) for p in sorted(S.rglob('*')) if p.is_file()}
dump(H/'review-source-manifest.json',manifest)
dump(H/'review-source-delta.json',{'parentManifestSHA256':sha((C/'copied-source-manifest.json').read_bytes()),
    'changedFiles':[n for n in manifest if manifest[n]!=candidate[n]],
    'appendedControlSHA256':sha(test),'reviewManifestSHA256':sha((H/'review-source-manifest.json').read_bytes())})
for n in ['owned-target','owned-tmp']:
    p=H/n
    assert not p.exists()
    p.mkdir()
dump(H/'cleanup-identities.json',{n:{'device':(H/n).stat().st_dev,'inode':(H/n).stat().st_ino} for n in ['owned-source','owned-target','owned-tmp']})
print(json.dumps(audit,sort_keys=True))
