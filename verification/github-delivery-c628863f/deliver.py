import datetime,hashlib,json,pathlib,subprocess,os
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer');base=pathlib.Path('/tmp/mixer-next-delivery')
m=json.loads(pathlib.Path(str(base)+'-manifest.json').read_text());paths=list(m['files']);commands=[]
def run(argv):
 r=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=1800 if argv[:2]==['git','push'] else 300)
 commands.append({'argv':argv,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if r.returncode: raise RuntimeError(r.stdout+r.stderr)
 return r.stdout.strip()
def snapshot_check():
 for name,entry in m['files'].items():
  p=root/name
  if entry['mode']=='120000':
   assert p.is_symlink(),name
   raw=os.readlink(p).encode()
  else:
   assert p.is_file() and not p.is_symlink(),name
   raw=p.read_bytes();assert ('100755' if p.stat().st_mode&0o111 else '100644')==entry['mode'],name
  assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256'],name
try:
 assert run(['git','rev-parse','HEAD'])==m['parent']
 assert run(['git','branch','--show-current'])=='main'
 assert run(['git','ls-remote','origin','refs/heads/main']).split()[0]==m['parent']
 assert not run(['git','diff','--cached','--name-only'])
 snapshot_check()
 run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'])
 run(['git','add','-f','--pathspec-from-file='+str(base)+'-paths','--pathspec-file-nul'])
 staged=run(['git','diff','--cached','--name-only','-z']).strip('\0').split('\0');assert set(staged)==set(paths)
 snapshot_check()
 run(['git','diff','--cached','--check','--','native','docs','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'])
 run(['git','commit','--only','--pathspec-from-file='+str(base)+'-paths','--pathspec-file-nul','-m','Record lifecycle accounting and native setup failure evidence'])
 head=run(['git','rev-parse','HEAD']);assert run(['git','rev-parse','HEAD^'])==m['parent']
 changed=run(['git','diff-tree','--no-commit-id','--name-only','-r','-z','HEAD']).strip('\0').split('\0');assert set(changed)==set(paths)
 tree=subprocess.check_output(['git','ls-tree','-r','-z','HEAD'],cwd=root);blobs={}
 for record in tree.split(b'\0'):
  if record:
   meta,name=record.split(b'\t',1);mode,_,blob=meta.decode().split();blobs[name.decode()]=(mode,blob)
 for name,entry in m['files'].items(): assert blobs[name]==(entry['mode'],entry['blob']),name
 snapshot_check()
 run(['git','push','origin','HEAD:main'])
 assert run(['git','ls-remote','origin','refs/heads/main']).split()[0]==head
 result={'schema':1,'status':'committed-pushed-exact-paths-modes-and-blobs-verified','sourceRevision':head,'parent':m['parent'],'pathCount':len(paths),'bytes':sum(e['bytes'] for e in m['files'].values()),'symlinks':sum(e['mode']=='120000' for e in m['files'].values()),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands}
 pathlib.Path(str(base)+'-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='commands'}))
finally:
 pathlib.Path(str(base)+'-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
