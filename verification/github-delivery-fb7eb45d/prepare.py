import hashlib,json,pathlib,subprocess
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer')
files=['PLAN.md','STATUS.md','work-graph.json','gates/ga.json',
'docs/android-toggle-scroll-extent-fix.md','docs/android-toggle-scroll-reset-fix.md',
'docs/apple-toggle-native-failure-analysis.md','docs/apple-toggle-diagnostic-runtime-retry.md',
'docs/native-toggle-diagnostics-progress.md','docs/stripe-webhook-resource-ingress-contract.md',
'docs/swift-optimized-accounting-contract-audit.md',
'verification/swift-calls-dispatch-root-review/optimized-accounting-amendment.json',
'verification/swift-calls-dispatch-root-review/compiler-layout-tooling-amendment.json',
'verification/swift-calls-dispatch-root-review/compiler-discovered-closure-amendment.json',
'verification/swift-calls-dispatch-root-review/compiler-discovered-closure-positions.json']
dirs=['verification/android-toggle-scroll-extent-fix','verification/android-toggle-scroll-extent-root-review',
'verification/android-toggle-scroll-reset-fix','verification/android-toggle-scroll-reset-root-review',
'verification/apple-toggle-native-failure-analysis','verification/apple-toggle-diagnostic-runtime-retry',
'verification/apple-toggle-diagnostic-root-review','verification/native-toggle-diagnostics-progress',
'verification/stripe-webhook-resource-ingress-contract','verification/stripe-webhook-resource-ingress-root-review',
'verification/swift-optimized-accounting-contract-audit','verification/github-ci-09ee31ff-engine',
'verification/github-ci-bbed074d-engine','verification/github-ci-bbed074d-phoenix','verification/github-delivery-bbed074d']
for name in dirs:
 for p in sorted((root/name).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and not {'build','.build','.scratch'}.intersection(p.parts) and p.name!='.DS_Store':
   assert not p.is_symlink();files.append(str(p.relative_to(root)))
assert len(files)==len(set(files));files=sorted(files)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='bbed074d3bd2453bbcc0807f05219d042cedd738'
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
base=pathlib.Path('/tmp/mixer-native-diagnostics-checkpoint')
pathlib.Path(str(base)+'-paths').write_bytes(b'\0'.join(f.encode()for f in manifest)+b'\0')
pathlib.Path(str(base)+'-manifest.json').write_text(json.dumps({'parent':head,'files':manifest},indent=2)+'\n')
print(json.dumps({'paths':len(manifest),'bytes':sum(x['bytes']for x in manifest.values()),'largestBytes':max(x['bytes']for x in manifest.values()),'parent':head}))
