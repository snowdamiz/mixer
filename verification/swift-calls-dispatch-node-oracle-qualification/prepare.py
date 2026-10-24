"""Metadata-only Node/Apple loader closure capture; no Wasm/compiler execution."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,datetime,gzip,shutil,re
HERE=Path(__file__).resolve().parent;V7=HERE.parent/'swift-calls-dispatch/v7-fixture-expectations'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def save(name,x):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(x if isinstance(x,bytes)else enc(x))
records=[]
def command(name,argv,env=None):
 p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,start_new_session=True,env=env)
 try:out,err=p.communicate(timeout=30)
 except subprocess.TimeoutExpired:p.kill();out,err=p.communicate();raise
 row={'argv':argv,'group':p.pid,'exitCode':p.returncode,'stdoutSHA256':hashlib.sha256(out).hexdigest(),'stderrSHA256':hashlib.sha256(err).hexdigest(),'executable':str(Path(shutil.which(argv[0])or argv[0]).resolve())};row['executableSHA256']=digest(row['executable']);records.append(row);save('metadata-commands.json',records);save(name+'-stdout.gz',gzip.compress(out,mtime=0));save(name+'-stderr.gz',gzip.compress(err,mtime=0));assert p.returncode==0,(name,err);return out,err
bad={k:v for k,v in os.environ.items()if v and(k.startswith('NODE_')or'DYLD_'in k or k in ['LD_PRELOAD','LD_LIBRARY_PATH'])};assert not bad,sorted(bad)
resolved=Path(shutil.which('node'));actual=resolved.resolve();out,_=command('node-version',[str(actual),'--version']);direct,_=command('node-direct-dependencies',['/usr/bin/otool','-L',str(actual)]);platform,_=command('platform',['/usr/bin/sw_vers'])
env=dict(os.environ,DYLD_PRINT_LIBRARIES='1');_,trace=command('node-version-loader-trace',[str(actual),'--version'],env)
cache=Path('/System/Cryptexes/OS/System/Library/dyld').resolve();assert cache.is_dir();files={}
for p in sorted(cache.iterdir()):
 if not p.name.startswith('dyld_shared_cache_'):continue
 assert p.is_file();files[str(p)]={'sha256':digest(p),'bytes':p.stat().st_size}
assert files
roots=[]
for line in direct.decode().splitlines()[1:]:
 path=line.strip().split(' (compatibility ',1)[0];assert path.startswith(('/System/Library/','/usr/lib/')),path;roots.append(path)
loaded=[]
for line in trace.decode().splitlines():
 if not line.startswith('dyld['):continue
 parts=line.split('> ',1)
 if len(parts)==2:loaded.append(parts[1])
# Loader trace is retained raw, including actual image UUIDs. All OS cache bytes
# are pinned, rather than pretending Node's executable hash pins system images.
loader=Path('/usr/lib/dyld');system=Path('/System/Library/CoreServices/SystemVersion.plist');assert loader.is_file()and system.is_file()
source=V7/'candidate/tests/span_execution_oracle.rs';text=source.read_text();start=text.index('let script = r#"')+len('let script = r#"');end=text.index('"#;',start);script=text[start:end];assert len(script.encode())==971
save('node-provenance.json',{'schema':1,'baseProducerSealSHA256':digest(V7/'review-seal.json'),'baseDriverSHA256':digest(V7/'qualified_runtime.py'),'candidateSourceClosure':'78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237','resolvedPATH':str(resolved),'actualPath':str(actual),'executableSHA256':digest(actual),'executableBytes':actual.stat().st_size,'version':out.decode().strip(),'oracleSource':'tests/span_execution_oracle.rs','oracleSourceSHA256':digest(source),'script':script,'scriptSHA256':hashlib.sha256(script.encode()).hexdigest(),'scriptBytes':971,'oracleArgv':['node','-e',script],'directSystemDependencies':roots,'loaderTraceRaw':'node-version-loader-trace-stderr.gz','loaderTraceScope':'Installed Node --version only; full raw actual loader UUID/path output retained. Not a Wasm execution trace.','systemCacheDirectory':str(cache),'systemCacheFiles':files,'systemCacheBytes':sum(x['bytes']for x in files.values()),'loader':{'path':str(loader),'sha256':digest(loader)},'systemVersion':{'path':str(system),'sha256':digest(system),'swVers':platform.decode()},'injectionEnvironmentPolicy':'Every nonempty NODE_* or name containing DYLD_, plus LD_PRELOAD/LD_LIBRARY_PATH, rejects. Only this metadata probe internally sets exactly DYLD_PRINT_LIBRARIES=1, recorded here. Runtime permits none.','toolClosureScope':'Node executable plus installed Apple dynamic loader, full host dyld shared-cache file set/bytes, OS build/version and oracle source/script; executable hash alone is not a transitive dependency claim.','dependencies':'Existing THIRD_PARTY.yml Node.js/V8/WASI development-only entry and installed Apple platform tools; never linked into Mixer product.','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'compilerCompilationExecuted':False,'wasmExecuted':False,'runtimeSelected':False})
save('preparation-receipt.json',{'argv':[sys.executable,'-B',str(Path(__file__))],'sourceSHA256':digest(__file__),'pythonVersion':sys.version,'pythonExecutableSHA256':digest(sys.executable),'nodeVersionOnly':True,'compilerCompilationExecuted':False,'wasmExecuted':False,'nativeInstancesCreated':0,'sharedFilesModified':False,'cacheFiles':len(files),'cacheBytes':sum(x['bytes']for x in files.values()),'allMetadataCommandsExited':True})
print('Node metadata closure:',len(files),'system cache files,',sum(x['bytes']for x in files.values()),'bytes; no Wasm/compiler/native execution')
