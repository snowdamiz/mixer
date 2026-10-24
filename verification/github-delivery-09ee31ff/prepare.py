import hashlib,json,pathlib,subprocess
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer')
files=['PLAN.md','STATUS.md','work-graph.json','gates/ga.json',
'hosted/lib/mixer_hosted/billing/webhook_transport.ex',
'docs/android-authored-toggle-supplement-repair.md','docs/apple-authored-toggle-contract.md',
'docs/apple-authored-toggle-runtime-preflight.md','docs/native-toggle-diagnostics-checkpoint.md',
'docs/stripe-webhook-transport-implementation.md','docs/stripe-webhook-transport-review.md',
'docs/stripe-webhook-transport-composition.md','docs/stripe-webhook-transport-integration.md',
'verification/swift-calls-dispatch-root-review/owner-preflight-amendment.json']
dirs=['verification/android-authored-toggle-supplement-repair','verification/android-authored-toggle-supplement-root-review',
'verification/apple-authored-toggle-contract','verification/apple-authored-toggle-root-review',
'verification/apple-authored-toggle-runtime-preflight','verification/apple-authored-toggle-native-root-review',
'verification/apple-native-resume-2026-10-24','verification/stripe-webhook-transport',
'verification/stripe-webhook-transport-review','verification/stripe-webhook-transport-composition',
'verification/stripe-webhook-transport-integration','verification/github-delivery-2f715b10',
'verification/native-diagnostics-transport-checkpoint']
for name in dirs:
 for p in sorted((root/name).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and not {'build','.build','.scratch'}.intersection(p.parts) and p.name!='.DS_Store':
   assert not p.is_symlink();files.append(str(p.relative_to(root)))
assert len(files)==len(set(files));files=sorted(files)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='2f715b10e707de26b89c9bef44831a43c7aa3c62'
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
base=pathlib.Path('/tmp/mixer-native-transport-checkpoint')
pathlib.Path(str(base)+'-paths').write_bytes(b'\0'.join(f.encode()for f in manifest)+b'\0')
pathlib.Path(str(base)+'-manifest.json').write_text(json.dumps({'parent':head,'files':manifest},indent=2)+'\n')
print(json.dumps({'paths':len(manifest),'bytes':sum(x['bytes']for x in manifest.values()),'largestBytes':max(x['bytes']for x in manifest.values()),'parent':head}))
