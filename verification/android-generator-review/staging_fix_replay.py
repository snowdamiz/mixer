#!/usr/bin/env python3
"""Independently replay confirmed staging escapes and deeper static link hazards."""
import hashlib
import json
import os
import pathlib
import runpy
import subprocess
import sys
import time

OUT=pathlib.Path(__file__).resolve().parent
DRIVER=OUT/'.local/source-repair/cli/Sources/MixerBuild/Resources/android-build.py'
BASE=OUT/'.local/staging-repair';BASE.mkdir()
module=runpy.run_path(str(DRIVER))
config={'schema':1,'name':'SafeApp','application':'dev.mixer.review','language':'swift','targets':['android'],'toolchainLock':'mixer.lock','capabilities':[],'updates':{'activation':'cold-start','compatibility':'exact-runtime-fingerprint','requireArtifactSignature':True,'requireAssignmentSignature':True}}
empty=hashlib.sha256(b'').hexdigest()
results=[]
def fixture(name):
    root=BASE/name
    for relative in ['Generated/MixerSDK','Generated/MixerAndroid','Resources']:(root/relative).mkdir(parents=True)
    (root/'mixer.lock').write_text(json.dumps({'schema':1,'sdkDigest':empty,'android':{'adapterDigest':empty,'toolchain':{}}}))
    (root/'mixer.yml').write_text(json.dumps(config))
    return root

def run(name,root,sentinels):
    command=[sys.executable,str(DRIVER),'build',str(root)]
    start=time.monotonic();p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
    elapsed=time.monotonic()-start
    log=OUT/('staging-fixed-'+name+'.log');log.write_bytes(p.stdout)
    preserved={str(path.relative_to(BASE)):path.read_text()=='sentinel' for path in sentinels}
    result={'name':name,'command':command,'exit_code':p.returncode,'elapsed_seconds':elapsed,'output':log.name,'output_sha256':hashlib.sha256(p.stdout).hexdigest(),'sentinels_preserved':preserved}
    results.append(result)
    assert p.returncode!=0 and b'Unsafe Android staging' in p.stdout,(name,p.stdout)
    assert all(preserved.values()),name
    assert not (root/'.mixer/android-build/build-input.json').exists(),name
for placement in ['mixer-parent','build-output']:
    root=fixture(placement);external=BASE/('external-'+placement);external.mkdir()
    output=external/'android-build' if placement=='mixer-parent' else external;output.mkdir(exist_ok=True)
    sentinels=[output/'build-receipt.json',output/'SafeApp-unsigned.apk']
    for path in sentinels:path.write_text('sentinel')
    if placement=='mixer-parent':(root/'.mixer').symlink_to(external,target_is_directory=True)
    else:(root/'.mixer').mkdir();(root/'.mixer/android-build').symlink_to(external,target_is_directory=True)
    run(placement,root,sentinels)
for kind in ['symlink','hardlink']:
    root=fixture('tmp-'+kind);output=root/'.mixer/android-build';output.mkdir(parents=True)
    sentinel=BASE/('tmp-'+kind+'-outside.txt');sentinel.write_text('sentinel');target=output/'build-input.json.tmp'
    if kind=='symlink':target.symlink_to(sentinel)
    else:os.link(sentinel,target)
    run('tmp-'+kind,root,[sentinel])
root=fixture('deep-escape');output=root/'.mixer/android-build';(output/'swift/cache').mkdir(parents=True)
outside=BASE/'deep-outside';outside.mkdir();sentinel=outside/'preserve.txt';sentinel.write_text('sentinel')
(output/'swift/cache/link').symlink_to(outside,target_is_directory=True)
run('deep-escape',root,[sentinel])
root=fixture('fifo');output=root/'.mixer/android-build';output.mkdir(parents=True);os.mkfifo(output/'build-input.json.tmp')
run('fifo',root,[])
for placement in ['mixer-file','output-file']:
    root=fixture(placement)
    if placement=='mixer-file':sentinel=root/'.mixer'
    else:(root/'.mixer').mkdir();sentinel=root/'.mixer/android-build'
    sentinel.write_text('sentinel');run(placement,root,[sentinel])
root=fixture('internal-positive');output=root/'.mixer/android-build';(output/'swift/arm64/release').mkdir(parents=True)
(output/'swift/release').symlink_to(output/'swift/arm64/release',target_is_directory=True)
assert module['checked_output'](root)==output
results.append({'name':'internal-swiftpm-link-positive','accepted':True})
receipt={'revision':json.loads((OUT/'freeze-repair.json').read_text())['revision'],'driver_sha256':hashlib.sha256(DRIVER.read_bytes()).hexdigest(),'results':results,'scope':'Four original confirmed exploit shapes plus deep staging link/FIFO/non-directory checks preserve isolated sentinels; local static preflight only, no concurrent same-user isolation claim.'}
(OUT/'staging-fix-replay.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
