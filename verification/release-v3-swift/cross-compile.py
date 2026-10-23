#!/usr/bin/env python3
"""Compile the exact frozen v3 Swift library for official SDKs; never execute a device."""
from pathlib import Path
import concurrent.futures
import datetime
import hashlib
import json
import os
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PIN='534414332fd4ec0731f781dc43faef56cb99c8b98022db64ea1545b5105d0388'
HOST_RECEIPT='253bf3912fe52262b5e837f2c3a51ea656b13eafe32dd59f991ccf53748484ff'
OFFICIAL='/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'

def sha(data):return hashlib.sha256(data).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)

def main():
    out=HERE/'2026-10-23-candidate-1-cross';out.mkdir(exist_ok=False)
    host=HERE/'2026-10-23-candidate-1'
    raw=(host/'receipt.json').read_bytes();require(sha(raw)==HOST_RECEIPT,'exact host receipt')
    baseline=json.loads(raw);require(baseline['source_manifest_sha256']==PIN,'source pin')
    source=Path(baseline['immutable_source_export']);work=source.parent
    def unchanged():
        for relative,digest in baseline['source_files'].items():
            require(sha((ROOT/relative).read_bytes())==digest,'live input '+relative)
            require(sha((source/relative).read_bytes())==digest,'frozen input '+relative)
    unchanged()
    receipt={'status':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_manifest_sha256':PIN,
             'host_receipt_sha256':HOST_RECEIPT,'source_export':str(source),'driver_sha256':sha(Path(__file__).read_bytes()),'commands':[],
             'scope':'Official iOS/Android library module/object compilation only, no final app link, platform run, device/signing or publication evidence'}
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    apple=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    android=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    def run(name,argv,env):
        began=time.monotonic()
        try:r=subprocess.run(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300);data,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as e:data,code=(e.stdout or b'')+b'\nCross compile timeout\n',124
        log=out/(name+'.log');log.write_bytes(data)
        return {'name':name,'argv':argv,'cwd':str(source),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},'exit_code':code,'elapsed_seconds':time.monotonic()-began,'log':str(log.relative_to(ROOT)),'sha256':sha(data)}
    save()
    for job in [('official-swift-version',[OFFICIAL,'--version'],android),('iphoneos-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],apple),('android-sdk-list',[OFFICIAL,'sdk','list','--swift-sdks-path','/Users/andreyyurlov/.swiftpm/swift-sdks'],android)]:
        row=run(*job);receipt['commands'].append(row);save();require(row['exit_code']==0,row['name'])
    sdk=(out/'iphoneos-sdk.log').read_text().strip()
    jobs=[('ios-module',['swift','build','--package-path',str(source/'updates'),'--scratch-path',str(work/'ios-module'),'--triple','arm64-apple-ios17.0','--sdk',sdk,'-c','release','--target','MixerUpdates','-Xswiftc','-warnings-as-errors'],apple),
          ('android-module',[OFFICIAL,'build','--package-path',str(source/'updates'),'--scratch-path',str(work/'android-module'),'--swift-sdks-path','/Users/andreyyurlov/.swiftpm/swift-sdks','--swift-sdk','aarch64-unknown-linux-android28','-c','release','--target','MixerUpdates','-Xswiftc','-warnings-as-errors'],android)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for row in pool.map(lambda job:run(*job),jobs):
            receipt['commands'].append(row);save();print(row['name']+': '+str(row['exit_code']),flush=True)
    unchanged();artifacts={}
    for target in ['ios','android']:
        folder=work/(target+'-module')
        modules=sorted(p for p in folder.rglob('*.swiftmodule') if p.is_file() and (p.parent.name=='MixerUpdates.swiftmodule' or p.name=='MixerUpdates.swiftmodule'))
        objects=sorted(p for p in folder.rglob('*.o') if p.name in ['MixerUpdates.o','VerifierV3.swift.o','VerifierV3.o'])
        require(modules and objects,target+' expected actual module/object artifacts')
        artifacts[target]=[{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(set(modules+objects))]
    receipt['artifacts']=artifacts;receipt['source_and_export_unchanged']=True
    receipt['status']='official SDK module/object compile checks passed' if all(c['exit_code']==0 for c in receipt['commands']) else 'failed cross check preserved'
    receipt['completed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
    require(receipt['status'].endswith('passed'),'cross compile failure')
    print(json.dumps({'status':receipt['status'],'receipt_sha256':sha((out/'receipt.json').read_bytes())}))

if __name__=='__main__':main()
