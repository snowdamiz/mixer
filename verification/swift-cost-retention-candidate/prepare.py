#!/usr/bin/env python3
"""Fresh bounded copies of the ordinary live VM; no historical source restore."""
import hashlib, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
EXPECTED = '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
def digest(data): return hashlib.sha256(data).hexdigest()
def write(path, obj): path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
paths = sorted(set(subprocess.check_output(['git','ls-files','--','vm/Cargo.toml','vm/Cargo.lock','vm/src','vm/tests','vm/include'], cwd=ROOT, text=True).splitlines()))
manifest = {str(pathlib.Path(p).relative_to('vm')): digest((ROOT/p).read_bytes()) for p in paths}
encoded = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
if len(paths) != 132 or digest(encoded) != EXPECTED:
    raise SystemExit(f'live source closure mismatch: {len(paths)} {digest(encoded)}')
if (OUT/'.scratch').exists(): raise SystemExit('scratch already exists')
for mode in ['baseline','candidate']:
    dest = OUT/'.scratch'/mode
    for rel in manifest:
        target = dest/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/'vm'/rel, target)
(OUT/'baseline-manifest.json').write_bytes(encoded)
write(OUT/'inputs.json', {'schema':1, 'contextualHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'liveVMClosure':EXPECTED, 'fileCount':len(paths), 'source':'ordinary live vm files read directly, never restored from a historical archive', 'limits':{'entries':64,'pins':64,'tickets':86,'cacheBytes':16777216,'entryBytes':8388608,'cacheWork':64000000,'combinedBytes':268435456}, 'scope':'finite host cache tests only; no full target, native, provider, network, new dependency or frozen hosted lane'})
print(f'copied {len(paths)} live files twice; closure {EXPECTED}')
