"""Verify only the isolated closed input tree; never fall back to live workspace."""
import hashlib
import json
from pathlib import Path
import stat

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
V3_HANDOFF='f50006ea6fbe274eac4a78c214a33da4b77c4249b0ef2e8a19f1e0c4200e18f1'
V3_PACKET='89e4b9b819bacc7ba69aee1fa2344245bf2eb26a3b8ed72a33a169f574f3fd60'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
stable=lambda value:(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def row(path):
    assert path.resolve()==path, path
    info=path.lstat();assert stat.S_ISREG(info.st_mode) and info.st_nlink==1,path
    raw=path.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(raw),'sha256':sha(raw)}

def verify():
    assert (ROOT/'closed-v5-root.json').is_file(), 'Execution requires an isolated closed-packet root'
    meta=json.loads((BASE/'input-bindings.json').read_bytes())
    assert sha(stable(meta['bindings']))==meta['bindingTreeSHA256']
    assert set(meta['storage'])==set(meta['bindings'])
    observed={}
    for name,expected in meta['bindings'].items():
        stored=Path(meta['storage'][name])
        assert not stored.is_absolute() and '..' not in stored.parts, name
        assert not any(word in str(stored).lower() for word in ('hosted','catalog','authority-driver','worker-transport')),name
        path=ROOT/stored
        assert path.is_relative_to(ROOT),name
        observed[name]=row(path);assert observed[name]==expected,name
    folder=ROOT/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures'
    prefix=str(folder.relative_to(ROOT))+'/'
    expected_names={name[len(prefix):] for name in meta['bindings'] if name.startswith(prefix)}
    assert {p.name for p in folder.iterdir()}==expected_names, 'Unlisted or missing frozen capture fixture'
    return observed
