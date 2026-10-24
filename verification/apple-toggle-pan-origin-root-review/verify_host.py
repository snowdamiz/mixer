"""Root replay of exact sealed candidate controls; never starts a native instance."""
import datetime,hashlib,json,os,pathlib,shutil,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent/'host-1'
PRODUCER=ROOT/'verification/apple-toggle-pan-origin-correction'
DEV=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=PRODUCER/'packet-seal.json';sealed=sha(seal);files=json.loads(seal.read_text())['files']
def verify():
 assert sha(seal)==sealed
 for name,digest in files.items():assert sha(ROOT/name)==digest,name
verify();OUT.mkdir(exist_ok=False);commands=[];scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-pan-origin-root-')).resolve();identity=scratch.stat();env={**os.environ,'DEVELOPER_DIR':str(DEV),'PYTHONDONTWRITEBYTECODE':'1'}
def run(args,cwd=ROOT):
 args=list(map(str,args));started=time.monotonic();p=subprocess.run(args,cwd=cwd,env=env,text=True,capture_output=True,timeout=180)
 commands.append(dict(argv=args,cwd=str(cwd),exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr,elapsedSeconds=time.monotonic()-started))
 (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 assert p.returncode==0,p.stdout+p.stderr
 return p.stdout
try:
 result=json.loads(run(['python3','-B',PRODUCER/'harness.py','verify']))
 run(['python3','-B','-m','unittest','test_controls','test_durability'],cwd=PRODUCER)
 assert 'Ran 92 tests' in commands[-1]['stderr'] and commands[-1]['stderr'].rstrip().endswith('OK')
 version=run(['/usr/bin/xcrun','swiftc','--version'])
 source=PRODUCER/'app/source'
 for module,libs in [('MixerCore',[]),('MixerUI',['MixerCore'])]:
  run(['/usr/bin/xcrun','swiftc','-swift-version','6','-emit-library','-emit-module','-module-name',module,'-emit-module-path',scratch/(module+'.swiftmodule'),'-o',scratch/('lib'+module+'.dylib'),'-I',scratch,'-L',scratch]+sorted((source/'sdk/Sources'/module).glob('*.swift'))+['-l'+x for x in libs]+['-Xlinker','-install_name','-Xlinker',scratch/('lib'+module+'.dylib')])
 run(['/usr/bin/xcrun','swiftc','-swift-version','6','-parse-as-library',PRODUCER/'policy-probe.swift',source/'Prototype/TogglePanPolicy.swift',source/'Prototype/TogglePanAdmission.swift',source/'Prototype/AppearanceNativePathsV2.swift','-I',scratch,'-L',scratch,'-lMixerCore','-lMixerUI','-o',scratch/'policy-probe'])
 payload=run([scratch/'policy-probe']);policy=json.loads(payload);assert policy['pass'] is True and len(policy['checks'])==58 and all(v['pass'] is True for v in policy['checks'])
 (OUT/'policy-result.json').write_text(payload)
 verify()
 receipt={'schema':1,'status':'root-host-controls-passed-native-pending','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevisionContext':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sealSHA256':sealed,'sealedFiles':len(files),'pythonHostControls':92,'swiftHostControls':58,'swiftVersion':version,'producerVerification':result,'nativeExecuted':False,'bindings':{str(seal.relative_to(ROOT)):sealed,str(pathlib.Path(__file__).resolve().relative_to(ROOT)):sha(pathlib.Path(__file__))}}
finally:
 entries=[p for p in scratch.rglob('*') if p.is_file()];count=len(entries);size=sum(p.stat().st_size for p in entries)
 assert scratch.stat().st_dev==identity.st_dev and scratch.stat().st_ino==identity.st_ino and not scratch.is_symlink()
 shutil.rmtree(scratch);cleanup={'path':str(scratch),'device':identity.st_dev,'inode':identity.st_ino,'files':count,'bytes':size,'removed':not scratch.exists()}
 (OUT/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
receipt['cleanup']=cleanup
for p in [OUT/'commands.json',OUT/'policy-result.json',OUT/'cleanup.json']:receipt['bindings'][str(p.relative_to(ROOT))]=sha(p)
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('bindings','producerVerification')}))
