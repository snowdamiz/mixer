import datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer');base=pathlib.Path('/tmp/mixer-native-transport-checkpoint')
m=json.loads(pathlib.Path(str(base)+'-manifest.json').read_text());paths=list(m['files']);commands=[]
def run(argv):
 r=subprocess.run(argv,cwd=root,capture_output=True,text=True)
 commands.append({'argv':argv,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if r.returncode: raise RuntimeError(r.stdout+r.stderr)
 return r.stdout.strip()
def snapshot_check():
 for name,entry in m['files'].items():
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==entry['sha256'],name
try:
 assert run(['git','rev-parse','HEAD'])==m['parent']
 assert run(['git','ls-remote','origin','refs/heads/main']).split()[0]==m['parent']
 snapshot_check()
 run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'])
 run(['git','add','-f','--pathspec-from-file='+str(base)+'-paths','--pathspec-file-nul'])
 staged=run(['git','diff','--cached','--name-only','-z']).strip('\0').split('\0');assert set(staged)==set(paths)
 snapshot_check()
 run(['git','diff','--cached','--check','--','hosted','docs','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'])
 run(['git','commit','--only','--pathspec-from-file='+str(base)+'-paths','--pathspec-file-nul','-m','Integrate private webhook transport and retain native toggle diagnostics'])
 head=run(['git','rev-parse','HEAD']);assert run(['git','rev-parse','HEAD^'])==m['parent']
 changed=run(['git','diff-tree','--no-commit-id','--name-only','-r','-z','HEAD']).strip('\0').split('\0');assert set(changed)==set(paths)
 tree=subprocess.check_output(['git','ls-tree','-r','-z','HEAD'],cwd=root);blobs={}
 for record in tree.split(b'\0'):
  if record:
   meta,name=record.split(b'\t',1);blobs[name.decode()]=meta.decode().split()[2]
 for name,entry in m['files'].items(): assert blobs[name]==entry['blob'],name
 snapshot_check()
 run(['git','push','origin','HEAD:main'])
 assert run(['git','ls-remote','origin','refs/heads/main']).split()[0]==head
 result={'schema':1,'status':'committed-pushed-exact-paths-and-blobs-verified','sourceRevision':head,'parent':m['parent'],'pathCount':len(paths),'bytes':sum(e['bytes'] for e in m['files'].values()),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands}
 pathlib.Path(str(base)+'-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='commands'}))
finally:
 pathlib.Path(str(base)+'-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
