import hashlib,json,pathlib,subprocess
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer')
files=['PLAN.md','STATUS.md','work-graph.json','gates/ga.json','docs/android-coordinator-join-runtime-status.md',
'docs/android-emulator-boot-diagnosis.md','docs/android-coordinator-wifi-runner.md','docs/android-coordinator-click-fixture.md','docs/android-coordinator-apk-packaging.md','docs/android-coordinator-join-acceptance.md',
'docs/swift-memory-growth-contract.md','docs/swift-memory-growth-implementation.md','docs/swift-host-dispatch-contract.md','docs/swift-host-dispatch-layout-replay.md','docs/swift-host-dispatch-contract-acceptance.md']
dirs=['verification/android-emulator-boot-diagnosis','verification/android-coordinator-wifi-runner','verification/android-coordinator-click-fixture','verification/android-coordinator-apk-packaging','verification/android-coordinator-join-root-review','verification/swift-memory-growth','verification/swift-memory-growth-root-review','verification/swift-host-dispatch-contract','verification/swift-host-dispatch-layout-replay','verification/swift-host-dispatch-root-review','verification/github-delivery-a1f78d1e','verification/github-ci-a1f78d1e-engine','verification/native-join-growth-checkpoint']
for name in dirs:
 for p in sorted((root/name).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and '.build' not in p.parts and p.name!='.DS_Store':
   assert not p.is_symlink();files.append(str(p.relative_to(root)))
assert len(files)==len(set(files));files=sorted(files)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343'
assert subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()=='main'
assert subprocess.check_output(['git','rev-parse','--show-object-format'],cwd=root,text=True).strip()=='sha1'
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=root,text=True).strip()
tracked={}
for line in subprocess.check_output(['git','ls-tree','-r','-z','HEAD'],cwd=root).split(b'\0'):
 if line:
  meta,name=line.split(b'\t',1);tracked[name.decode()]=meta.decode().split()[2]
manifest={}
for f in files:
 data=(root/f).read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 if tracked.get(f)==blob:continue
 assert len(data)<95_000_000,f
 manifest[f]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'blob':blob}
assert manifest
base=pathlib.Path('/tmp/mixer-native-checkpoint')
pathlib.Path(str(base)+'-paths').write_bytes(b'\0'.join(f.encode()for f in manifest)+b'\0')
pathlib.Path(str(base)+'-manifest.json').write_text(json.dumps({'parent':head,'files':manifest},indent=2)+'\n')
print(json.dumps({'paths':len(manifest),'bytes':sum(x['bytes']for x in manifest.values()),'largestBytes':max(x['bytes']for x in manifest.values()),'parent':head}))
