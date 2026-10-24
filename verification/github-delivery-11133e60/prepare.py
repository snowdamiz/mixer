import hashlib,json,pathlib,subprocess
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer')
files=['PLAN.md','STATUS.md','work-graph.json','gates/ga.json',
'docs/swift-cleanup-diagnostic-contract.md','docs/android-pointer-fixture.md','docs/android-pointer-fixture-review.md',
'docs/stripe-webhook-signature-contract.md','docs/stripe-webhook-signature-evidence.md','docs/stripe-webhook-signature-review.md','docs/stripe-webhook-signature-integration.md',
'hosted/lib/mixer_hosted/billing/webhook_signature.ex','hosted/test/mixer_hosted/billing/webhook_signature_test.exs','hosted/test/fixtures/billing/webhook-signature.json']
dirs=['verification/github-delivery-d4909e27','verification/github-ci-d4909e27-engine',
'verification/swift-cleanup-diagnostic-contract','verification/swift-cleanup-diagnostic-root-review',
'verification/android-obsolete-build-cleanup','verification/android-pointer-fixture','verification/android-pointer-fixture-review','verification/android-pointer-fixture-root-review',
'verification/stripe-webhook-signature','verification/stripe-webhook-signature-review','verification/stripe-webhook-signature-integration','verification/stripe-signature-checkpoint']
for name in dirs:
 for p in sorted((root/name).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and '.build' not in p.parts and p.name!='.DS_Store':
   assert not p.is_symlink();files.append(str(p.relative_to(root)))
assert len(files)==len(set(files));files=sorted(files)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='d4909e275df7e757a5218cc0a88112f4fc3f088b'
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
base=pathlib.Path('/tmp/mixer-stripe-checkpoint')
pathlib.Path(str(base)+'-paths').write_bytes(b'\0'.join(f.encode()for f in manifest)+b'\0')
pathlib.Path(str(base)+'-manifest.json').write_text(json.dumps({'parent':head,'files':manifest},indent=2)+'\n')
print(json.dumps({'paths':len(manifest),'bytes':sum(x['bytes']for x in manifest.values()),'largestBytes':max(x['bytes']for x in manifest.values()),'parent':head}))
