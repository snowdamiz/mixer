from pathlib import Path
import json,hashlib,subprocess
root=Path('/Users/andreyyurlov/Documents/dev/mixer');base=Path('/tmp/mixer-next-delivery');selected=set();seals=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,filename,relative in [
 ('apple-toggle-keyboard-focus-v6-preparation','packet-seal.json',False),
 ('apple-toggle-keyboard-focus-v6-independent-review','review-seal.json',False),
 ('apple-toggle-keyboard-focus-v6-analysis','analysis-seal.json',False),
 ('swift-reactor-lifecycle-accounting','seal.json',True),
 ('swift-reactor-lifecycle-accounting-independent-review','seal.json',True),
 ('swift-reactor-lifecycle-runtime','seal.json',True),
 ('stripe-resource-linux-compiler-metadata-v2','seal.json',False),
 ('stripe-resource-linux-compiler-metadata-v3','seal.json',False),
 ('stripe-resource-linux-compiler-acquisition','seal.json',False),
]:
 seal=root/'verification'/name/filename;data=json.loads(seal.read_text());selected.add(str(seal.relative_to(root)))
 for path,digest in data['files'].items():
  p=(seal.parent if relative else root)/path
  assert p.is_file() and not p.is_symlink() and sha(p)==digest,str(p)
  selected.add(str(p.relative_to(root)))
 seals.append({'path':str(seal.relative_to(root)),'sha256':sha(seal),'files':len(data['files'])})
for name in ['github-ci-06147f0e-engine','github-delivery-06147f0e','native-lifecycle-metadata-checkpoint','apple-toggle-keyboard-focus-v6-root-review','swift-reactor-lifecycle-accounting-root-review','swift-reactor-lifecycle-contract-root-review','swift-lifecycle-delivery-transport']:
 for p in (root/'verification'/name).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:selected.add(str(p.relative_to(root)))
runtime=json.loads((root/'verification/apple-toggle-keyboard-focus-v6-root-review/runtime-review.json').read_text())
for name,info in runtime['evidenceFiles'].items():
 assert sha(root/name)==info['sha256'] and (root/name).stat().st_size==info['bytes'];selected.add(name)
for name in ['PLAN.md','STATUS.md','THIRD_PARTY.yml','work-graph.json','gates/ga.json','docs/swift-reactor-lifecycle-accounting.md','docs/swift-reactor-lifecycle-accounting-independent-review.md','docs/swift-reactor-lifecycle-runtime.md']:
 selected.add(name)
prefix='verification/stripe-webhook-resource-ingress-root-review/'
for name in ['linux-compiler-acquisition-review.json','linux-compiler-acquisition-selection.json','linux-compiler-assembly-selection.json','linux-compiler-metadata-v2-review.json','linux-compiler-metadata-v2-review.stderr','linux-compiler-metadata-v2-review.stdout','linux-compiler-metadata-v3-review.json','linux-compiler-metadata-v3-review.stderr','linux-compiler-metadata-v3-review.stdout','linux-compiler-metadata-v3-selection.json','review_linux_metadata_v2.py','review_linux_metadata_v3.py','v3-lock-recheck.stderr','v3-lock-recheck.stdout','v3-retained-audit.stderr','v3-retained-audit.stdout']:
 selected.add(prefix+name)
transport=json.loads((root/'verification/swift-lifecycle-delivery-transport/transport-manifest.json').read_text())
for entry in transport['entries']:
 assert entry['path'] in selected and sha(root/entry['path'])==entry['sha256']
 selected.remove(entry['path'])
tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().strip('\0').split('\0'));dirty=set(subprocess.check_output(['git','diff','--name-only','-z'],cwd=root).decode().strip('\0').split('\0'))
selected={n for n in selected if n not in tracked or n in dirty};files={}
for name in sorted(selected):
 p=root/name;assert p.is_file() and not p.is_symlink(),name
 raw=p.read_bytes();assert len(raw)<99_000_000,(name,len(raw));assert p.suffix!='.deb',name
 files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'mode':'100755' if p.stat().st_mode&0o111 else '100644'}
m={'parent':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'files':files,'validatedSeals':seals,'exactRawPathsDeliveredThroughTransport':transport['excludedRawPaths'],'excludedActiveLanes':['swift-reactor-lifecycle-runtime-v2','apple-toggle-keyboard-focus-v7-preparation','stripe-resource-linux-compiler-assembly'],'officialDebArchivesExcluded':True}
Path(str(base)+'-manifest.json').write_text(json.dumps(m,indent=2)+'\n');Path(str(base)+'-paths').write_bytes(b'\0'.join(n.encode() for n in files)+b'\0')
print(json.dumps({'paths':len(files),'bytes':sum(x['bytes'] for x in files.values()),'maxBytes':max(x['bytes'] for x in files.values()),'seals':len(seals)}))
