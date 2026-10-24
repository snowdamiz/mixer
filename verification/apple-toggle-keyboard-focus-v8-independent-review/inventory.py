"""Independent byte inventory; no build/runtime/native tool queries."""
import datetime
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys
import time

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];V8=ROOT/'verification/apple-toggle-keyboard-focus-v8-preparation';V7=ROOT/'verification/apple-toggle-keyboard-focus-v7-preparation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,x:p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
PINS={'verification/apple-toggle-keyboard-focus-v8-preparation/packet-seal.json':'46e2c5a61fcce4137595da36af6d120ef476b2fb5889a1bd8cfb38d70f7a9b0f','verification/apple-toggle-keyboard-focus-v7-root-review/v8-persistence-selection.json':'b607b64d146e88d743da05739e341de24d01d3228d53c949f9dc72419c411fa4','verification/apple-toggle-keyboard-focus-v7-independent-review/review-seal.json':'6aacb2434dddd1ab41eecd2bd8f3c54b074322fdf372886adf6d4464452e91f3'}


def inventory():
    inputs=dict(PINS);seal=read(V8/'packet-seal.json');assert len(seal['files'])==110
    inputs.update(seal['files']);bound=read(V8/'input-bindings.json');assert len(bound)==913;inputs.update(bound)
    inputs['verification/apple-toggle-keyboard-focus-v7-independent-review/host_checks.py']=sha(ROOT/'verification/apple-toggle-keyboard-focus-v7-independent-review/host_checks.py')
    canonical=pathlib.Path(sys.executable).resolve();inputs[str(canonical)]=sha(canonical)
    links=[]
    for name,expected in inputs.items():
        path=pathlib.Path(name) if name.startswith('/') else ROOT/name
        assert path.is_file() and sha(path)==expected,name
        if path.is_symlink():links.append(dict(path=str(path),linkText=str(path.readlink()),resolved=str(path.resolve()),sha256=sha(path)))
    for name,expected in PINS.items():assert sha(ROOT/name)==expected,name
    copies=read(V8/'immutable-reuse.json')['exactCopies'];assert len(copies)==43
    for a,b in copies.items():assert sha(ROOT/a)==sha(ROOT/b),(a,b)
    runner=read(V8/'build-products-manifest.json');products=V7/'build/Build/Products';tree={}
    for path in sorted(products.rglob('*')):
        info=path.lstat();value=dict(mode=format(stat.S_IMODE(info.st_mode),'04o'))
        assert not path.is_symlink(),str(path)
        if stat.S_ISDIR(info.st_mode):value['kind']='directory'
        elif stat.S_ISREG(info.st_mode):value.update(kind='file',bytes=info.st_size,sha256=sha(path))
        else:raise AssertionError('Unexpected product type: '+str(path))
        tree[str(path.relative_to(products))]=value
    assert tree==runner['products']
    assert hashlib.sha256(json.dumps(tree,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==runner['productTreeSHA256']
    assert sha(V7/'test-runner-products.tar.gz')==runner['productArchiveSHA256']
    write(HERE/'review-inputs.json',inputs);write(HERE/'tool-link-bindings.json',links)
    result=dict(schema='mixer.apple-keyboard.v8-independent-input-inventory.1',observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),producerSealedFilesVerified=len(seal['files']),producerBoundInputsVerified=len(bound),deduplicatedReviewInputs=len(inputs),exactImmutableCopiesVerified=len(copies),runnerProductEntriesVerified=len(tree),runnerSourceTreeSHA256=runner['sourceTreeSHA256'],runnerProductTreeSHA256=runner['productTreeSHA256'],runnerArchiveSHA256=runner['productArchiveSHA256'],appArchiveSHA256=sha(V8/'built-app.tar.gz'),sourceRevisionContext=runner['sourceRevisionContext'],currentGitHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),pythonVersion=sys.version,pythonExecutable=sys.executable,pythonCanonical=str(canonical),pythonSHA256=sha(canonical),nativeExecuted=False,nativeInstancesQueried=False,runnerRecompiled=False,appRecompiled=False)
    write(HERE/'inventory.json',result);print(json.dumps(result,sort_keys=True))

if __name__=='__main__':inventory()
