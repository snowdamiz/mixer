import hashlib,json,pathlib,subprocess,os
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer')
base=pathlib.Path('/tmp/mixer-v7-delivery')
sha=lambda data:hashlib.sha256(data).hexdigest()
files=set(['PLAN.md','STATUS.md','work-graph.json','gates/ga.json','docs/swift-dispatch-v7-runtime-checkpoint.md'])
links={}
def bound(folder,bindings):
 for name,item in bindings.items():
  p=folder/name;raw=p.read_bytes();assert not p.is_symlink() and sha(raw)==item['sha256'] and len(raw)==item['bytes'],str(p)
  files.add(str(p.relative_to(root)))
v7=root/'verification/swift-calls-dispatch/v7-fixture-expectations'
s=json.loads((v7/'review-seal.json').read_bytes());assert sha((v7/'review-seal.json').read_bytes())=='79089f1ef382a14e02fbbbf0a6e6dcd0a67158bcfa5354d565a5b037b1d149b2'
bound(v7,s['bindings']);files.add(str((v7/'review-seal.json').relative_to(root)))
h=json.loads((v7/'v6-history-bindings.json').read_bytes());bound((v7/h['path']).resolve(),h['files'])
for item in json.loads((v7/'shared-evidence-links.json').read_bytes()):
 p=v7/item['path'];assert p.is_symlink() and os.readlink(p)==item['target'] and p.resolve()==(v7/item['resolvedRelativePath']).resolve()
 assert p.resolve().is_relative_to(root/'verification/swift-calls-dispatch') and p.resolve().is_dir()
 links[str(p.relative_to(root))]=item['target'];files.add(str(p.relative_to(root)))
for name,expected in [('swift-calls-dispatch-v7-independent-review','32faeb9b870bac88cbd7815e9b709776adfbb006b3f73f61c5747b2d74783779'),('swift-calls-dispatch-node-oracle-qualification','1480be97d75e506abf1ed8402182e6fdb8e5914f6bdd87cf9d6e293e24dd64b4')]:
 folder=root/'verification'/name;p=folder/'review-seal.json';assert sha(p.read_bytes())==expected
 seal=json.loads(p.read_bytes());bound(folder,seal['bindings']);bound(root,seal.get('documents',{}));files.add(str(p.relative_to(root)))
review=root/'verification/swift-calls-dispatch-root-review'
supplement=json.loads((review/'v7-supplemental-history.json').read_bytes());bound(root,supplement['files'])
for name in ['v7-supplemental-history.json','v7-runtime-selection.json','sealed-v7/receipt.json','sealed-v7/read-only.stdout','sealed-v7/read-only.stderr']:
 files.add(str((review/name).relative_to(root)))
for folder in ['verification/github-ci-3f6be79b-engine','verification/github-ci-6291ea80-engine','verification/github-ci-9a9c0e00-engine','verification/github-delivery-9a9c0e00','verification/swift-calls-dispatch-root-review/checkpoint-policy']:
 for p in (root/folder).rglob('*'):
  if p.is_file():assert not p.is_symlink();files.add(str(p.relative_to(root)))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='9a9c0e000234b07a92c4484979d3587f7f24df48'
assert subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()=='main'
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=root,text=True).strip()
tracked={}
for record in subprocess.check_output(['git','ls-tree','-r','-z','HEAD'],cwd=root).split(b'\0'):
 if record:
  meta,name=record.split(b'\t',1);mode,_,blob=meta.decode().split();tracked[name.decode()]=(mode,blob)
manifest={}
for name in sorted(files):
 p=root/name
 if name in links:raw=links[name].encode();mode='120000'
 else:
  assert p.is_file() and not p.is_symlink(),name
  assert not any(q.is_symlink() for q in p.parents),name
  raw=p.read_bytes();mode='100755' if p.stat().st_mode&0o111 else '100644'
 assert len(raw)<95_000_000,name
 blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 if tracked.get(name)==(mode,blob):continue
 manifest[name]={'sha256':sha(raw),'bytes':len(raw),'blob':blob,'mode':mode}
assert manifest
pathlib.Path(str(base)+'-paths').write_bytes(b'\0'.join(n.encode() for n in manifest)+b'\0')
pathlib.Path(str(base)+'-manifest.json').write_text(json.dumps({'parent':head,'files':manifest},indent=2)+'\n')
print(json.dumps({'paths':len(manifest),'logicalBytes':sum(v['bytes'] for v in manifest.values()),'symlinks':sum(v['mode']=='120000' for v in manifest.values()),'largestBytes':max(v['bytes'] for v in manifest.values()),'parent':head}))
