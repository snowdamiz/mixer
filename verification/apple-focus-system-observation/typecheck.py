#!/usr/bin/env python3
"""Pinned-SDK source typechecking only; no native execution or app product."""
import datetime,hashlib,json,os,pathlib,shutil,subprocess,time,sys
HERE=pathlib.Path(__file__).resolve().parent
SWIFT=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk')
SCRATCH=HERE/'.owned-typecheck'
assert not SCRATCH.exists()
SCRATCH.mkdir();(SCRATCH/'tmp').mkdir();(SCRATCH/'cache').mkdir()
ATTEMPT=HERE/('typecheck-attempt-'+(sys.argv[1] if len(sys.argv)>1 else '1'));ATTEMPT.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
def stable(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
inputs={}
for root in ['inputs/accepted','candidate/accepted']:
 for p in sorted((HERE/root).rglob('*.swift')):
  b=p.read_bytes();inputs[str(p.relative_to(HERE))]={'bytes':len(b),'sha256':sha(b)}
source_digest=sha(stable(inputs))
env=os.environ.copy();explicit={'TMPDIR':str(SCRATCH/'tmp')+'/', 'CLANG_MODULE_CACHE_PATH':str(SCRATCH/'cache'),'SWIFT_MODULECACHE_PATH':str(SCRATCH/'cache'),'DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer','LC_ALL':'C'};env.update(explicit)
commands=[]
def run(name,args,timeout=55):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();timedout=False
 try:
  r=subprocess.run([str(x) for x in args],cwd=HERE,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
  out,err,code=r.stdout,r.stderr,r.returncode
 except subprocess.TimeoutExpired as e:
  out,err,code=e.stdout or b'',e.stderr or b'',None;timedout=True
 (ATTEMPT/(name+'.stdout')).write_bytes(out);(ATTEMPT/(name+'.stderr')).write_bytes(err)
 commands.append({'name':name,'argv':[str(x) for x in args],'cwd':str(HERE),'explicitEnvironment':explicit,'startedUTC':started,'elapsedSeconds':time.monotonic()-t,'timeoutSeconds':timeout,'timedOut':timedout,'exitCode':code,'stdoutSHA256':sha(out),'stderrSHA256':sha(err),'sourceTreeSHA256':source_digest})
 (ATTEMPT/'commands.json').write_bytes(stable(commands))
 print(json.dumps({'command':name,'exitCode':code,'timedOut':timedout,'stderrBytes':len(err)}),flush=True)
 return code==0
base=[SWIFT,'-sdk',SDK,'-target','arm64-apple-ios26.0-simulator','-swift-version','6','-module-cache-path',SCRATCH/'cache','-I',SCRATCH]
passed=False
try:
 assert run('swift-version',[SWIFT,'--version'])
 accepted=HERE/'inputs/accepted/source'
 for module in ['MixerCore','MixerUI']:
  sources=sorted((accepted/'sdk/Sources'/module).glob('*.swift'))
  assert run('dependency-'+module,base+['-parse-as-library','-emit-module','-module-name',module,'-emit-module-path',SCRATCH/(module+'.swiftmodule')]+sources)
 # Check unchanged and derivative complete Prototype source closures, insertion sites included.
 assert run('baseline-prototype',base+['-typecheck']+sorted((accepted/'Prototype').glob('*.swift')))
 assert run('candidate-prototype',base+['-typecheck']+sorted((HERE/'candidate/accepted/source/Prototype').glob('*.swift')))
 framework='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks'
 assert run('unchanged-harness-four',base+['-typecheck','-module-name','MixerSettingsDiagnostic','-F',framework,'-I','/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/usr/lib']+sorted((HERE/'candidate/accepted/harness/UITests').glob('*.swift')))
 passed=True
finally:
 settings=SDK/'SDKSettings.json'
 (ATTEMPT/'sdk-settings.json').write_bytes(settings.read_bytes())
 (ATTEMPT/'source-bindings.json').write_bytes(stable(inputs))
 shutil.rmtree(SCRATCH)
 result={'schema':1,'passed':passed,'scope':'Source typechecking only; temporary dependency modules; no app link/build/install/run or native query','sourceTreeSHA256':source_digest,'sdk':str(SDK),'sdkSettingsSHA256':sha(settings.read_bytes()),'scratchRemoved':not SCRATCH.exists(),'physicalPhones':'disconnected-deferred','nativeAttempts':0,'nativeQueries':0,'appProducts':0,'commands':len(commands),'searchPathReferenceSHA256':sha((HERE/'inputs/prior-typecheck-command.json').read_bytes())}
 (ATTEMPT/'receipt.json').write_bytes(stable(result));print(json.dumps(result,sort_keys=True),flush=True)
