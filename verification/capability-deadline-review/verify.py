#!/usr/bin/env python3
"""Small direct-compiler probe; no production edits, SPM, devices or endpoints."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SCRATCH=ROOT/'.build/capability-deadline-review'
SOURCE=SCRATCH/'original'
DERIVED=SCRATCH/'derived'
BUILD=SCRATCH/'build'
for p in [SOURCE,DERIVED,BUILD]:p.mkdir(parents=True,exist_ok=True)
INPUTS=['sdk/Sources/MixerCore/JSONInputGuard.swift']+['sdk/Sources/MixerCapabilities/'+x for x in ['Host.swift','Wire.swift','GeneratedModels.swift','GeneratedHostAdapters.swift','CapabilityExitLease.swift','InstalledCapabilityAdapters.swift','AppPrivateKeyValueStore.swift','URLSessionHTTPTransport.swift','NativeIO/lock.c','NativeIO/include/MixerCapabilityIO.h']]
def sha(b):return hashlib.sha256(b).hexdigest()
receipt={'schema':1,'scope':'Read-only production review; small captured-source deterministic watchdog scheduling experiment; unmodified Host control plus derived delayed-watchdog Host; installed local storage only; no network/device/build-system/publication actions','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':[],'sources':{}}
for rel in INPUTS:
 data=(ROOT/rel).read_bytes();dst=SOURCE/rel;dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists(): assert dst.read_bytes()==data, rel+' changed from the original immutable capture'
 else: dst.write_bytes(data)
 dst.chmod(0o444);receipt['sources'][rel]=sha(data)
manifest=''.join(h+'  '+p+'\n' for p,h in sorted(receipt['sources'].items()))
(OUT/'source-manifest.sha256').write_text(manifest);receipt['source_digest']=sha(manifest.encode())
original=(SOURCE/'sdk/Sources/MixerCapabilities/Host.swift').read_text()
needle='''        slots[index].timer = Task.detached { [weak self] in
            do { try await Task.sleep(nanoseconds: UInt64(timeout) * 1_000_000) } catch { return }'''
assert original.count(needle)==1
changed=original.replace(needle,'''        slots[index].timer = Task.detached { [weak self] in
            await ReviewHooks.beforeWatchdogSleep() // TEST ONLY: withhold watchdog scheduling
            do { try await Task.sleep(nanoseconds: UInt64(timeout) * 1_000_000) } catch { return }''')
(DERIVED/'Host.swift').write_text(changed)
import difflib
(OUT/'test-only-watchdog.patch').write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),changed.splitlines(keepends=True),fromfile='original/Host.swift',tofile='derived/Host.swift')))
receipt['derived_host_sha256']=sha(changed.encode());receipt['probe_sha256']=sha((OUT/'Probe.swift').read_bytes());receipt['driver_sha256']=sha(Path(__file__).read_bytes())
(SCRATCH/'c-module').mkdir(exist_ok=True)
header=SOURCE/'sdk/Sources/MixerCapabilities/NativeIO/include/MixerCapabilityIO.h'
(SCRATCH/'c-module/module.modulemap').write_text('module MixerCapabilityIO { header "'+str(header)+'" export * }\n')
def save():(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,args,env=None):
 start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=OUT/(name+'.log');log.write_bytes(p.stdout);receipt['commands'].append({'name':name,'argv':list(map(str,args)),'exit_code':p.returncode,'elapsed_seconds':round(time.monotonic()-start,6),'log':str(log.relative_to(ROOT)),'log_sha256':sha(p.stdout)});save();print(name+': exit '+str(p.returncode),flush=True)
 if p.returncode:print(p.stdout.decode(errors='replace')[-12000:],flush=True);raise SystemExit(p.returncode)
 return p.stdout.decode(errors='replace')
run('version-swift',['swiftc','--version']);run('version-clang',['clang','--version']);run('version-host',['uname','-a']);run('version-python',['python3','--version'])
run('compile-json-guard',['swiftc','-swift-version','6','-parse-as-library','-emit-library','-emit-module','-module-name','MixerCore',SOURCE/INPUTS[0],'-emit-module-path',BUILD/'MixerCore.swiftmodule','-o',BUILD/'libMixerCore.dylib'])
run('compile-owned-native-lock',['clang','-c',SOURCE/'sdk/Sources/MixerCapabilities/NativeIO/lock.c','-I',header.parent,'-o',BUILD/'lock.o'])
cap=[SOURCE/p for p in INPUTS if p.endswith('.swift') and '/MixerCapabilities/' in p and not p.endswith('/Host.swift')]
for mode,host in [('control',SOURCE/'sdk/Sources/MixerCapabilities/Host.swift'),('delayed',DERIVED/'Host.swift')]:
 executable=BUILD/('deadline-'+mode)
 args=['swiftc','-swift-version','6','-parse-as-library','-I',BUILD,'-I',SCRATCH/'c-module','-L',BUILD,'-lMixerCore','-Xlinker','-rpath','-Xlinker',BUILD]+cap+[host,OUT/'Probe.swift',BUILD/'lock.o','-o',executable]
 run('compile-'+mode,args)
 store=SCRATCH/('store-'+mode);store.mkdir(exist_ok=True)
 output=run('run-'+mode,[executable,'normal-watchdog' if mode=='control' else 'delayed-watchdog',store])
 print(output.strip(),flush=True)
for rel,expected in receipt['sources'].items():assert sha((ROOT/rel).read_bytes())==expected,rel
receipt['production_inputs_unchanged_after_probe']=True
receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['result']='Delayed-watchdog captured-copy experiment reproduced late host success; original-host control delivered deadlineExceeded and preserved installed exit retention';save()
