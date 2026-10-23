#!/usr/bin/env python3
"""Probe preexisting staging file links with review-owned outside sentinels."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys

OUT=pathlib.Path(__file__).resolve().parent
label=sys.argv[1]
DRIVER=pathlib.Path(sys.argv[2]).resolve()
BASE=OUT/('.local/staging-leaf-'+label)
BASE.mkdir()
config={'schema':1,'name':'SafeApp','application':'dev.mixer.review','language':'swift','targets':['android'],'toolchainLock':'mixer.lock','capabilities':[],'updates':{'activation':'cold-start','compatibility':'exact-runtime-fingerprint','requireArtifactSignature':True,'requireAssignmentSignature':True}}
empty=hashlib.sha256(b'').hexdigest()
results=[]
for kind in ['symlink','hardlink']:
    root=BASE/kind
    for relative in ['Generated/MixerSDK','Generated/MixerAndroid','Resources','.mixer/android-build']:(root/relative).mkdir(parents=True,exist_ok=True)
    (root/'mixer.lock').write_text(json.dumps({'schema':1,'sdkDigest':empty,'android':{'adapterDigest':empty,'toolchain':{}}}))
    (root/'mixer.yml').write_text(json.dumps(config))
    sentinel=BASE/(kind+'-outside-sentinel.txt'); sentinel.write_text('sentinel')
    target=root/'.mixer/android-build/build-input.json.tmp'
    if kind=='symlink':target.symlink_to(sentinel)
    else:os.link(sentinel,target)
    command=[sys.executable,str(DRIVER),'build',str(root)]
    process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=OUT/('staging-leaf-'+label+'-'+kind+'.log');log.write_bytes(process.stdout)
    results.append({'kind':kind,'command':command,'exit_code':process.returncode,'output':log.name,'output_sha256':hashlib.sha256(process.stdout).hexdigest(),'sentinel_preserved':sentinel.read_text()=='sentinel','observed_outside_bytes':sentinel.read_text()})
(OUT/('staging-leaf-'+label+'.json')).write_text(json.dumps({'driver_sha256':hashlib.sha256(DRIVER.read_bytes()).hexdigest(),'results':results},indent=2)+'\n')
print(json.dumps(results,indent=2))
