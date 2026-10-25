#!/usr/bin/env python3
"""Remove this packet's compiler target only; retain source/binary for later selection."""
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import os
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepared_driver',HERE/'diagnostic.py')
driver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
assert not (HERE/'preparation-products-cleanup.json').exists()
assert not (HERE/'target-attempt-started.json').exists()
assert not (HERE/'commands/target-once').exists()
assert not (HERE/'root-selection.json').exists()
driver.assert_baseline()
driver.assert_inputs()
assert driver.identity(driver.BINARY)==driver.read(HERE/'binary.json')['retained']
observations=[]
for pattern in ('commands/*/receipt.json','outer-preparation-commands/*/receipt.json'):
    for path in sorted(HERE.glob(pattern)):
        receipt=driver.read(path)
        assert receipt['passed'] and receipt['rawStreamEOFConfirmed']
        assert receipt['finalGroupObservation']['state']=='absent'
        current=driver.observe_group(receipt['processGroup'])
        assert current['state']=='absent'
        observations.append({'receipt':str(path.relative_to(HERE)), 'processGroup':receipt['processGroup'], 'currentObservation':current})

def directory_identity(path):
    assert path.is_dir() and not path.is_symlink()
    stat=path.stat()
    return {'path':str(path),'resolvedPath':str(path.resolve()),'device':stat.st_dev,'inode':stat.st_ino}

scratch=directory_identity(driver.SCRATCH)
source=directory_identity(driver.SOURCE)
target=directory_identity(driver.TARGET)
assert driver.TARGET.parent==driver.SCRATCH and driver.TARGET.name=='target'
assert driver.TARGET.resolve()==driver.SCRATCH.resolve()/'target'
product_manifest={str(p.relative_to(driver.TARGET)):driver.identity(p) for p in sorted(driver.TARGET.rglob('*')) if p.is_file()}
assert all(not p.is_symlink() for p in driver.TARGET.rglob('*'))
driver.save('compiler-products-manifest.json',product_manifest)
version=subprocess.run(['/usr/sbin/lsof','-v'],capture_output=True,timeout=10)
(HERE/'lsof-version.stdout').write_bytes(version.stdout)
(HERE/'lsof-version.stderr').write_bytes(version.stderr)
holders=[]
for name,path,recursive in [('precleanup-target',driver.TARGET,True),('precleanup-scratch',driver.SCRATCH,True),('precleanup-binary',driver.BINARY,False)]:
    argv=['/usr/sbin/lsof','-nP']+(['+D'] if recursive else [])+[str(path)]
    result=subprocess.run(argv,capture_output=True,timeout=30)
    (HERE/(name+'-holders.stdout')).write_bytes(result.stdout)
    (HERE/(name+'-holders.stderr')).write_bytes(result.stderr)
    observation={'argv':argv,'exitCode':result.returncode,'stdout':driver.identity(HERE/(name+'-holders.stdout')),'stderr':driver.identity(HERE/(name+'-holders.stderr'))}
    holders.append(observation)
    assert result.returncode==1 and not result.stdout and not result.stderr
assert directory_identity(driver.TARGET)==target
assert directory_identity(driver.SCRATCH)==scratch
assert directory_identity(driver.SOURCE)==source
binary=driver.identity(driver.BINARY)
archive=Path(str(driver.BINARY)+'.gz')
assert not archive.exists()
with driver.BINARY.open('rb') as stream, gzip.GzipFile(filename=str(archive),mode='wb',mtime=0) as output:
    shutil.copyfileobj(stream,output)
with gzip.open(archive,'rb') as stream:
    uncompressed=stream.read()
assert len(uncompressed)==binary['bytes'] and hashlib.sha256(uncompressed).hexdigest()==binary['sha256']
assert driver.identity(driver.BINARY)==binary
before={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope':'this owned compiler target only; copied runtime source and selected binary retained; no target execution',
    'pid':os.getpid(),'processGroup':os.getpgid(0),'ownedGroupObservations':observations,
    'scratchIdentity':scratch,'retainedSourceIdentity':source,'removedTargetIdentity':target,
    'holders':holders,'lsof':driver.identity('/usr/sbin/lsof'),
    'lsofVersionExitCode':version.returncode,'binary':binary,'compressedBinary':driver.identity(archive),
    'compilerProductsManifestSHA256':driver.sha(HERE/'compiler-products-manifest.json'),
    'logicalBytesToRemove':sum(info['bytes'] for info in product_manifest.values()),
    'targetAttempted':False,'otherProjectsTouched':False}
driver.save('preparation-products-before-cleanup.json',before)
assert directory_identity(driver.TARGET)==target
assert directory_identity(driver.SCRATCH)==scratch
shutil.rmtree(driver.TARGET)
assert not driver.TARGET.exists()
assert directory_identity(driver.SCRATCH)==scratch
assert directory_identity(driver.SOURCE)==source
driver.assert_baseline()
driver.assert_inputs()
assert driver.identity(driver.BINARY)==binary
for item in observations:
    assert driver.observe_group(item['processGroup'])['state']=='absent'
driver.save('preparation-products-cleanup.json',before | {
    'removedCompilerTarget':True,'compilerTargetAbsent':True,'ownedScratchRetained':True,
    'ownedScratchMeaning':'runtime preparation source/tmp only; compiler target removed; required for unchanged later driver',
    'originalAndCompressedBinaryRetained':True,'sourceUnchanged':True,'allEarlierOwnedGroupsAbsent':True,
    'deviceInodeStable':True,'holdersEmpty':True,'noSignalsSent':True})
print(json.dumps({'compilerTargetRemoved':True,'logicalBytesRemoved':before['logicalBytesToRemove'],
    'retainedBinaryBytes':binary['bytes'],'compressedBinaryBytes':archive.stat().st_size,
    'sourceRetainedForUnchangedDispatch':True,'targetAttempted':False}))
