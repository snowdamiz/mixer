import hashlib,json,pathlib,subprocess
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer')
files=['PLAN.md','STATUS.md','work-graph.json','gates/ga.json',
'console/package.json','console/package-lock.json','console/tsconfig.json','console/THIRD_PARTY.yml',
'console/src/domain/release-check-summary.ts','console/tests/release-check-summary.test.mjs',
'docs/console-release-check-summary.md','.github/workflows/console.yml']
dirs=['verification/console-release-check-summary','verification/github-delivery-fb7eb45d']
for name in dirs:
 for p in sorted((root/name).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and not {'build','.build','.scratch'}.intersection(p.parts) and p.name!='.DS_Store':
   assert not p.is_symlink();files.append(str(p.relative_to(root)))
assert len(files)==len(set(files));files=sorted(files)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='fb7eb45d91d702f2ba21088a294859edb4f51484'
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
base=pathlib.Path('/tmp/mixer-console-summary-checkpoint')
pathlib.Path(str(base)+'-paths').write_bytes(b'\0'.join(f.encode()for f in manifest)+b'\0')
pathlib.Path(str(base)+'-manifest.json').write_text(json.dumps({'parent':head,'files':manifest},indent=2)+'\n')
print(json.dumps({'paths':len(manifest),'bytes':sum(x['bytes']for x in manifest.values()),'largestBytes':max(x['bytes']for x in manifest.values()),'parent':head}))
