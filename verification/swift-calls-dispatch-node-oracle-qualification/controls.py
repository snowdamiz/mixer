"""Pure failure controls: file reads and synthetic Cargo metadata, no VM/compiler."""
from pathlib import Path
import sys,json,os,copy,tempfile,time,hashlib
import companion as n
H=n.HERE;D=json.loads(n.PROVENANCE.read_bytes());ENV=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);rows=[]
def reject(name,fn):
 try:fn()
 except (AssertionError,KeyError):rows.append({'name':name,'rejected':True})
 else:raise AssertionError('negative control accepted: '+name)
for key in ['NODE_OPTIONS','NODE_PATH','NODE_V8_COVERAGE','DYLD_LIBRARY_PATH','DYLD_INSERT_LIBRARIES','__XPC_DYLD_INSERT_LIBRARIES','LD_PRELOAD','LD_LIBRARY_PATH']:
 reject('injected-'+key,lambda key=key:n.verify(dict(ENV,**{key:'injected'}),D,False))
for key,value in [('resolvedPATH','/unsupported/node'),('actualPath','/unsupported/node'),('executableSHA256','0'*64),('oracleSourceSHA256','0'*64),('scriptSHA256','0'*64),('scriptBytes',972),('oracleArgv',['node','-p','process.version'])]:
 d=copy.deepcopy(D);d[key]=value;reject('changed-'+key,lambda d=d:n.verify(ENV,d,False))
d=copy.deepcopy(D);d['logicalSystemCacheDirectory']='/unsupported';reject('changed-cache-resolution',lambda:n.verify(ENV,d,True))
d=copy.deepcopy(D);d['systemCacheFiles'].pop(next(iter(d['systemCacheFiles'])));reject('missing-cache-file-binding',lambda:n.verify(ENV,d,True))
d=copy.deepcopy(D);d['loader']['sha256']='0'*64;reject('changed-loader-bytes',lambda:n.verify(ENV,d,True))
d=copy.deepcopy(D);d['systemVersion']['sha256']='0'*64;reject('changed-os-version-bytes',lambda:n.verify(ENV,d,True))
d=copy.deepcopy(D);d['systemCacheFiles'][next(iter(d['systemCacheFiles']))]['sha256']='0'*64;reject('changed-cache-bytes',lambda:n.verify(ENV,d,True))
# A named-looking executable never establishes ownership. Only one fresh actual
# Cargo artifact, the fixed target, test profile and owned target directory do.
with tempfile.TemporaryDirectory(prefix='mixer-node-companion-controls-')as tmp:
 root=Path(tmp);exe=root/'target/deps/span_execution_oracle-control';exe.parent.mkdir(parents=True);exe.write_bytes(b'metadata-only-not-an-executable')
 artifact={'reason':'compiler-artifact','target':{'name':'span_execution_oracle'},'executable':str(exe),'fresh':False,'profile':{'test':True}}
 class Child:
  returncode=0
  def __init__(self,row):self.row=row
  def communicate(self):return(json.dumps(self.row)+'\n').encode(),b''
 class Owner:pass
 owner=Owner();owner.root=H/'controls-cargo';owner.oracle={}
 n.OracleCargoRecorder(Child(artifact),owner,str(root/'target')).communicate();assert owner.oracle[str(exe)]['sha256']==hashlib.sha256(exe.read_bytes()).hexdigest()
 for label,field,value in [('wrong-target','target',{'name':'span_execution_oracle_fake'}),('stale-executable','fresh',True),('not-test-profile','profile',{'test':False}),('foreign-executable','executable','/outside/owned/target')]:
  a=copy.deepcopy(artifact);a[field]=value;reject(label,lambda a=a:n.OracleCargoRecorder(Child(a),owner,str(root/'target')).communicate())
# Execute the unchanged base event builder using a synthetic Popen handle and
# metadata-only sysroot reply. No compiler or child process is launched.
from types import SimpleNamespace
base_root=H/'controls-base-event';base_root.mkdir(exist_ok=True);n.c.save(base_root/'root-selection.json',{'nodeCompanionSealSHA256':'synthetic-control-only'})
fake_seal=base_root/'synthetic-seal.json';n.c.save(fake_seal,{'syntheticControlOnly':True})
old_load,old_verify,old_seal,old_real=n.load,n.verify,n.SEAL,n.q.REAL
try:
 n.load=lambda _:D;n.verify=lambda *a,**kw:{'syntheticStartupOnly':True};n.SEAL=fake_seal
 obj=n.NodePrelaunch(base_root,n.c.read_json(n.V7/'review-seal.json'),'a'*64)
 class FakeChild:pid=987654321
 n.q.REAL=SimpleNamespace(check_output=lambda *a,**kw:obj.expected['actualCompiler']['sysroot']+'\n',Popen=lambda *a,**kw:FakeChild())
 env=dict(ENV,CARGO_TARGET_DIR=str(base_root/'target'))
 for key in ['RUSTC_BOOTSTRAP','RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_ENCODED_RUSTFLAGS','RUSTC']:env.pop(key,None)
 n.BASE.Popen(obj,['synthetic-control-no-process'],cwd=n.V7/'candidate',env=env,start_new_session=True)
 event=n.c.read_json(base_root/'prelaunch/000.json');assert type(event['rootSelectionSHA256'])is str and event['rootSelectionSHA256']=='a'*64 and obj.selection=='a'*64
 rows.append({'name':'inherited-root-selection-exact-sha-string','rejected':True,'meaning':'prior dict-overwrite mutation prevented; actual unchanged base event builder preserves exact SHA string','syntheticHandleOnly':True,'noProcessLaunched':True})
finally:n.load,n.verify,n.SEAL,n.q.REAL=old_load,old_verify,old_seal,old_real
start=time.monotonic();basic=n.verify(ENV,D,False);full=n.verify(ENV,D,True);seconds=time.monotonic()-start
n.c.save(H/'controls.json',{'controls':rows,'allRejected':all(r['rejected']for r in rows),'positiveBasic':basic,'positiveFullLoaderCache':full,'positiveVerificationSeconds':seconds,'syntheticCargoArtifactOnly':True,'dummyTargetRemoved':not Path(tmp).exists(),'compilerCompilationExecuted':False,'wasmExecuted':False,'nativeInstancesCreated':0,'baseSourceCompilerChecksUnchanged':True,'pythonVersion':sys.version,'argv':[sys.executable,'-B',str(Path(__file__))],'sourceSHA256':n.digest(__file__)})
print(len(rows),'negative controls rejected; exact Node/loader/cache/source positive check passed in',round(seconds,3),'seconds; no VM/compiler/native execution')
