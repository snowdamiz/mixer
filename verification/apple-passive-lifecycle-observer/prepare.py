#!/usr/bin/env python3
"""Package the owned source scratch; no imports/execution of upstream code."""
import datetime, difflib, gzip, hashlib, io, json, pathlib, tarfile
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()
def stable(value): return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
def write(name, value): (HERE / name).write_bytes(stable(value))
bindings = {}
inputs = [
    'verification/apple-reference-focus-lifecycle-diagnosis/handoff.json',
    'verification/apple-reference-focus-lifecycle-diagnosis/experiment.json',
    'verification/apple-focus-system-native-result/handoff.json',
    'verification/apple-focus-system-observation/review-source-package.tar.gz',
    'verification/apple-focus-system-native-result/result.json',
    'verification/apple-focus-system-runtime-preparation/native-run-v8-d9a1ae2b-ef02-4db2-b2ff-4979213c8236/runtime/captures/0001-after-1.json',
]
for name in inputs:
    b = (ROOT / name).read_bytes(); bindings[name] = {'bytes':len(b), 'sha256':sha(b)}
assert bindings[inputs[0]]['sha256'] == '0e54a5c61dbefe9908b53c1f1a5d96440187b3d9cd561395337e7a89f4896452'
assert bindings[inputs[2]]['sha256'] == '0d4ff885c95e54386cd06e53794077defa7acac5cf63525583a8053f053c90de'
assert bindings[inputs[3]]['sha256'] == 'd1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda'
with tarfile.open(ROOT / inputs[3]) as t:
    baseline = {m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
    modes = {m.name:m.mode for m in t.getmembers() if m.isfile()}
candidate = {str(p.relative_to(HERE/'scratch')):p.read_bytes() for p in sorted((HERE/'scratch').rglob('*')) if p.is_file()}
assert len(baseline) == 40 and len(candidate) == 42
changed = [name for name in baseline if candidate[name] != baseline[name]]
added = sorted(set(candidate) - set(baseline))
assert changed == ['accepted/source/Prototype/main.swift']
assert added == ['accepted/source/Prototype/PassiveLifecycleData.swift', 'accepted/source/Prototype/PassiveLifecycleObserver.swift']
patch = []
for name in sorted(changed + added):
    patch.extend(difflib.unified_diff(baseline.get(name,b'').decode().splitlines(keepends=True), candidate[name].decode().splitlines(keepends=True), fromfile='a/'+name if name in baseline else '/dev/null', tofile='b/'+name))
(HERE/'source.patch').write_text(''.join(patch))
out = io.BytesIO()
with gzip.GzipFile(fileobj=out,mode='wb',filename='',mtime=0) as gz:
    with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as t:
        for name,b in sorted(candidate.items()):
            m=tarfile.TarInfo(name); m.size=len(b); m.mode=modes.get(name,0o444); m.mtime=0
            t.addfile(m,io.BytesIO(b))
(HERE/'review-source-package.tar.gz').write_bytes(out.getvalue())
members={name:{'bytes':len(b),'sha256':sha(b)} for name,b in sorted(candidate.items())}
write('input-bindings.json',bindings)
write('source-manifest.json',{'schema':1,'baselineMembers':40,'candidateMembers':42,'unchangedMembers':39,'changedMembers':changed,'addedMembers':added,'sourceArchiveSHA256':sha(out.getvalue()),'memberTreeSHA256':sha(stable(members)),'members':members})
print(json.dumps({'sourceArchiveSHA256':sha(out.getvalue()),'candidateMembers':42,'changedExistingMembers':changed,'addedMembers':added},sort_keys=True))
