"""Add Node provenance checks to the immutable V7 qualification driver.
No base check is removed; root must explicitly bind this companion and metadata.
The companion itself performs no Mixer/oracle run without the root-selected base
main function. The original oracle script and fixtures stay byte-identical.
"""
from pathlib import Path
import sys,json,hashlib,shutil,datetime
sys.dont_write_bytecode=True
import qualified_runtime as q
c=q.c
BASE=q.Prelaunch
PROVENANCE=c.HERE/'qualification-node-provenance.json'
ROOTS=[]

def pin(env,expected):
 assert c.sha(PROVENANCE.read_bytes())==expected['nodeProvenanceSHA256']and c.sha(Path(__file__).read_bytes())==expected['qualificationCompanionSHA256']
 data=c.read_json(PROVENANCE);resolved=shutil.which('node',path=env['PATH']);assert resolved==data['resolvedPATH']
 actual=Path(resolved).resolve();assert str(actual)==data['actualPath']and c.sha(actual.read_bytes())==data['executableSHA256']
 source=(c.HERE/'candidate'/data['source']).read_bytes();assert c.sha(source)==data['sourceSHA256']
 text=source.decode();start=text.index('let script = r#"')+len('let script = r#"');end=text.index('"#;',start);script=text[start:end];assert script==data['script']and c.sha(script.encode())==data['scriptSHA256']and data['oracleArgv']==['node','-e',script]
 return {'resolvedPATH':resolved,'actualPath':str(actual),'executableSHA256':data['executableSHA256'],'versionPinnedByActualBytes':data['versionCommand']['stdout'].strip(),'scriptSHA256':data['scriptSHA256'],'sourceSHA256':data['sourceSHA256'],'checkedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}

class NodePinnedPrelaunch(BASE):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.node_checks=[];self.aux_selection=c.read_json(self.root/'root-selection.json');ROOTS.append(self.root);c.save(self.root/'node-provenance.json',PROVENANCE.read_bytes());c.save(self.root/'qualification-companion.py',Path(__file__).read_bytes())
 def Popen(self,argv,*args,**kwargs):
  event={'argv':list(argv),'pinsPassed':False}
  try:event.update(pin(kwargs['env'],self.aux_selection));event['pinsPassed']=True
  except BaseException:
   import traceback;event['failure']=traceback.format_exc();self.events.append({'cargoTargetDir':kwargs['env']['CARGO_TARGET_DIR'],'argv':list(argv),'launched':False,'sourceAndToolPinsPassed':False,'nodePinFailure':event['failure']});raise
  finally:self.node_checks.append(event);c.save(self.root/'node-prelaunch-checks.json',self.node_checks)
  return super().Popen(argv,*args,**kwargs)

def main():
 # The base parser/driver still validates source, seal, its own hash and the
 # actual generated plan. These two additional bindings are companion-specific.
 at=sys.argv.index('--root-runtime-selection');selection=json.loads(Path(sys.argv[at+1]).read_bytes());assert selection['qualificationCompanionSHA256']==c.sha(Path(__file__).read_bytes())and selection['nodeProvenanceSHA256']==c.sha(PROVENANCE.read_bytes())
 q.Prelaunch=NodePinnedPrelaunch
 try:
  result=q.main()
  final=pin({'PATH':'/opt/homebrew/opt/rustup/bin:'+__import__('os').environ['PATH']},selection)
  for root in ROOTS:c.save(root/'companion-final.json',{'allCompanionPinsPassed':all(x['pinsPassed']for x in c.read_json(root/'node-prelaunch-checks.json')),'finalNodePin':final,'qualificationCompanionSHA256':c.sha(Path(__file__).read_bytes()),'nodeProvenanceSHA256':c.sha(PROVENANCE.read_bytes()),'baseDriverExitCode':result,'rootAggregateAcceptancePending':True})
  return result
 except BaseException:
  import traceback
  for root in ROOTS:c.save(root/'companion-failure.log',traceback.format_exc().encode())
  raise
 finally:q.Prelaunch=BASE
if __name__=='__main__':raise SystemExit(main())
