"""Separately selected Node-only extension of the immutable V7 prelaunch facade."""
from pathlib import Path
import sys,os,json,hashlib,shutil,datetime,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;V7=HERE.parent/'swift-calls-dispatch/v7-fixture-expectations'
sys.path.insert(0,str(V7));import qualified_runtime as q
c=q.c;BASE=q.Prelaunch;ROOTS=[];PROVENANCE=HERE/'node-provenance.json';SEAL=HERE/'review-seal.json'
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def environment(env):
 bad={k:v for k,v in env.items()if v and(k.startswith('NODE_')or'DYLD_'in k or k in ['LD_PRELOAD','LD_LIBRARY_PATH'])};assert not bad,('unsupported injection environment',sorted(bad))
def verify(env,data,full):
 environment(env);resolved=shutil.which('node',path=env['PATH']);assert resolved==data['resolvedPATH'];actual=Path(resolved).resolve();assert str(actual)==data['actualPath']and digest(actual)==data['executableSHA256']
 source=V7/'candidate'/data['oracleSource'];assert digest(source)==data['oracleSourceSHA256'];text=source.read_text();a=text.index('let script = r#"')+len('let script = r#"');b=text.index('"#;',a);script=text[a:b];assert data['scriptBytes']==971 and len(script.encode())==971 and script==data['script']and c.sha(script.encode())==data['scriptSHA256']and data['oracleArgv']==['node','-e',script]
 if full:
  assert str(Path(data['logicalSystemCacheDirectory']).resolve())==data['systemCacheDirectory'];root=Path(data['systemCacheDirectory']);assert {str(p)for p in root.iterdir()}==set(data['systemCacheFiles'])
  for item in [data['loader'],data['systemVersion']]:assert digest(item['path'])==item['sha256']
  for path,item in data['physicalLoadedSystemFiles'].items():assert Path(path).stat().st_size==item['bytes']and digest(path)==item['sha256']
  for path,item in data['systemCacheFiles'].items():assert Path(path).is_file()and Path(path).stat().st_size==item['bytes']and digest(path)==item['sha256'],('cache drift',path)
 return {'actualNodeSHA256':data['executableSHA256'],'versionPinnedByExactNodeBytes':data['version'],'scriptSHA256':data['scriptSHA256'],'fullLoaderCacheChecked':full,'systemCacheFiles':len(data['systemCacheFiles'])if full else 0,'systemCacheBytes':data['systemCacheBytes']if full else 0,'injectionEnvironmentEmpty':True,'checkedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def load(selection):
 assert digest(SEAL)==selection['nodeCompanionSealSHA256'];seal=json.loads(SEAL.read_bytes())
 for rel,item in seal['bindings'].items():assert digest(HERE/rel)==item['sha256']and (HERE/rel).stat().st_size==item['bytes']
 data=json.loads(PROVENANCE.read_bytes());assert data['baseProducerSealSHA256']==digest(V7/'review-seal.json')and data['baseDriverSHA256']==digest(V7/'qualified_runtime.py');return data
class OracleCargoRecorder:
 def __init__(self,child,owner,target):self.child=child;self.owner=owner;self.target=target
 def __getattr__(self,name):return getattr(self.child,name)
 def communicate(self,*args,**kwargs):
  stdout,stderr=self.child.communicate(*args,**kwargs)
  if self.child.returncode==0:
   rows=[json.loads(line)for line in stdout.decode().splitlines()if line.startswith('{')];art=[r for r in rows if r.get('reason')=='compiler-artifact'and r.get('executable')and r['target']['name']=='span_execution_oracle'];assert len(art)==1 and art[0]['fresh']is False and art[0]['profile']['test']is True
   exe=Path(art[0]['executable']);assert exe.is_absolute()and exe.is_relative_to(Path(self.target));self.owner.oracle[str(exe)]={'cargoArtifact':art[0],'sha256':digest(exe),'bytes':exe.stat().st_size};c.save(self.owner.root/'node-oracle-artifact-identities.json',self.owner.oracle)
  return stdout,stderr
class NodePrelaunch(BASE):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.node_selection=c.read_json(self.root/'root-selection.json');self.data=load(self.node_selection);self.node_checks=[];self.oracle={};ROOTS.append(self.root);c.save(self.root/'node-companion-seal.json',SEAL.read_bytes());c.save(self.root/'node-provenance.json',PROVENANCE.read_bytes());c.save(self.root/'node-companion.py',Path(__file__).read_bytes());c.save(self.root/'node-startup-check.json',verify(dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']),self.data,True))
 def Popen(self,argv,*args,**kwargs):
  event={'argv':list(argv),'pinsPassed':False,'ownedOracleArtifact':False}
  try:
   data=load(self.node_selection);relevant=str(argv[0])in self.oracle
   if relevant:
    assert list(argv[1:])in [['--list'],['--nocapture','--test-threads=1']];assert digest(argv[0])==self.oracle[str(argv[0])]['sha256'];event.update(ownedOracleArtifact=True,cargoArtifact=self.oracle[str(argv[0])])
   event.update(verify(kwargs['env'],data,relevant));event['pinsPassed']=True
  except BaseException:
   event['failure']=traceback.format_exc();self.events.append({'cargoTargetDir':kwargs['env']['CARGO_TARGET_DIR'],'argv':list(argv),'launched':False,'sourceAndToolPinsPassed':False,'nodePinFailure':event['failure']});raise
  finally:self.node_checks.append(event);c.save(self.root/'node-prelaunch-checks.json',self.node_checks)
  child=super().Popen(argv,*args,**kwargs)
  builds=[r['argv']for r in q.plan()if r['id']in ['frozen-span_execution_oracle-debug','frozen-span_execution_oracle-release']]
  return OracleCargoRecorder(child,self,kwargs['env']['CARGO_TARGET_DIR'])if list(argv)in builds else child
def main():
 at=sys.argv.index('--root-runtime-selection');selection=json.loads(Path(sys.argv[at+1]).read_bytes());load(selection)
 q.Prelaunch=NodePrelaunch;code=None;failure=None
 try:
  code=q.main();return code
 except BaseException:
  failure=traceback.format_exc()
  for root in ROOTS:c.save(root/'node-companion-failure.log',failure.encode())
  raise
 finally:
  try:
   data=load(selection);final=verify(dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']),data,True)
   for root in ROOTS:c.save(root/'node-companion-final.json',{'allNodePinsPassed':all(r['pinsPassed']for r in c.read_json(root/'node-prelaunch-checks.json')),'final':final,'baseDriverExitCode':code,'baseDriverRaised':failure is not None,'nodeCompanionSealSHA256':digest(SEAL),'rootAggregateAcceptancePending':True})
  except BaseException:
   for root in ROOTS:c.save(root/'node-companion-final-failure.log',traceback.format_exc().encode())
   raise
  finally:q.Prelaunch=BASE
if __name__=='__main__':raise SystemExit(main())
