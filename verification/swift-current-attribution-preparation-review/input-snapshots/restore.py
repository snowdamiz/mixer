#!/usr/bin/env python3
"""Restore exact review products only. No compiler, validation, guest or target execution."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,os,subprocess,sys
H=Path(__file__).resolve().parent
# The sealed preparation must verify before any reconstruction writes.
subprocess.run([sys.executable,'-B',str(H/'verify.py')],check=True,timeout=30)
spec=importlib.util.spec_from_file_location('fresh_attribution_driver',H/'diagnostic.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
assert not driver.SCRATCH.exists() and not driver.BINARY.exists()
assert not (H/'root-selection.json').exists() and not (H/'target-attempt-started.json').exists()
source=driver.reconstructed_source()
manifest=json.loads((H/'copied-build-manifest.json').read_text())
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==manifest
with gzip.open(str(driver.BINARY)+'.gz','rb') as stream:binary=stream.read()
info=json.loads((H/'binary.json').read_text())['retained']
assert len(binary)==info['bytes'] and hashlib.sha256(binary).hexdigest()==info['sha256']
driver.SCRATCH.mkdir(mode=0o700);(driver.SCRATCH/'tmp').mkdir(mode=0o700)
for n,b in source.items():
    path=driver.SOURCE/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
driver.BINARY.write_bytes(binary);driver.BINARY.chmod(0o700)
assert driver.assert_baseline()==manifest and driver.identity(driver.BINARY)==info
print(json.dumps({'sourceAndExecutableRestoredForRootReview':True,'sourceManifestSHA256':driver.sha(H/'copied-build-manifest.json'),'binarySHA256':info['sha256'],'rootSelectionCreated':False,'targetExecuted':False,'rootMustSeparatelySelectExactCommand':True}))
