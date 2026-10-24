import hashlib,json,pathlib,subprocess
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer')
files=['PLAN.md','STATUS.md','work-graph.json','gates/ga.json',
'docs/swift-host-operation-implementation.md','docs/swift-host-operation-review.md','docs/swift-host-operation-integration-checkpoint.md',
'docs/android-pointer-oracle-repair.md','docs/android-pointer-oracle-repair-review.md','docs/android-pointer-timing-correction.md','docs/android-pointer-native-checkpoint.md',
'docs/stripe-raw-body-contract.md','docs/stripe-raw-body-direction.md','docs/stripe-raw-body-capture.md',
'verification/swift-cleanup-diagnostic-root-review/host-baseline-direction.json']
changed=['src/experimental_swift_reactor/bulk_memory_operations_tests.rs','src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/control_operations_tests.rs','src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/frame_operations.rs','src/experimental_swift_reactor/frame_operations_tests.rs','src/experimental_swift_reactor/host_operation_tests.rs','src/experimental_swift_reactor/memory_operations_tests.rs','src/experimental_wasi/accounted.rs','src/experimental_wasi/tests.rs']
files+=['vm/'+p for p in changed]
dirs=['verification/github-delivery-11133e60','verification/github-ci-11133e60-engine','verification/github-ci-11133e60-phoenix',
'verification/swift-host-operation','verification/swift-host-operation-review','verification/swift-host-operation-root-review','verification/swift-host-operation-root-integration','verification/swift-host-operation-checkpoint',
'verification/android-pointer-oracle-repair','verification/android-pointer-oracle-repair-review','verification/android-pointer-oracle-root-review','verification/android-pointer-timing-correction','verification/android-pointer-timing-root-review','verification/android-pointer-native-root-review',
'verification/stripe-raw-body-contract','verification/stripe-raw-body-root-review','verification/stripe-raw-body-capture']
for name in dirs:
 for p in sorted((root/name).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and '.build' not in p.parts and p.name!='.DS_Store':
   assert not p.is_symlink();files.append(str(p.relative_to(root)))
assert len(files)==len(set(files));files=sorted(files)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='11133e60551c46c9ea3aa4eac7356ea32d44fc72'
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
base=pathlib.Path('/tmp/mixer-host-operation-checkpoint')
pathlib.Path(str(base)+'-paths').write_bytes(b'\0'.join(f.encode()for f in manifest)+b'\0')
pathlib.Path(str(base)+'-manifest.json').write_text(json.dumps({'parent':head,'files':manifest},indent=2)+'\n')
print(json.dumps({'paths':len(manifest),'bytes':sum(x['bytes']for x in manifest.values()),'largestBytes':max(x['bytes']for x in manifest.values()),'parent':head}))
