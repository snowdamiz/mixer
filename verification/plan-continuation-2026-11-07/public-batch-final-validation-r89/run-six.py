import json,os,pathlib,subprocess,time
p=pathlib.Path(__file__).parent;e=os.environ.copy();c=json.loads((p/'selection-six.json').read_text());b=pathlib.Path(c['ownedWork']);e.update(DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',SDKROOT='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk',TMPDIR=str(b/'tmp')+'/',PYTHONDONTWRITEBYTECODE='1',JAVA_HOME='/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home',MIXER_SWIFT_IDENTITY_DIAGNOSTICS='1');e.pop('JAVA_TOOL_OPTIONS',None);e['PATH']='/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin:'+e['PATH'];t=time.monotonic()
args=['python3','-B','scripts/ci/check-android-generated-java.py','--swift','/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift','--swift-sdks','/Users/andreyyurlov/.swiftpm/swift-sdks','--android-artifact','/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android','--jdk',e['JAVA_HOME'],'--android-sdk','/opt/homebrew/share/android-commandlinetools','--output',str(p/'six-consumers'),'--execute-toolchains']
from hashlib import sha256
owning=pathlib.Path(c['root'])/'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/source-inputs.json'
files=json.loads(owning.read_text())
assert len(files)==c['sourceCount']
assert sha256(''.join(path+'\0'+pin['sha256']+'\n' for path,pin in sorted(files.items())).encode()).hexdigest()==c['source116']
assert all(sha256((pathlib.Path(c['root'])/path).read_bytes()).hexdigest()==pin['sha256'] for path,pin in files.items())
with (p/'six-consumers.stdout').open('wb') as out,(p/'six-consumers.stderr').open('wb') as err:
 child=subprocess.Popen(args,cwd=c['root'],env=e,stdout=out,stderr=err,start_new_session=True)
 (p/'six-command.json').write_text(json.dumps({'pid':child.pid,'argv':args,'cwd':c['root'],'source116':c['source116'],'productCommandBudgetSeconds':2400},indent=2)+'\n')
 code=child.wait()
r={'exitCode':code,'elapsedSeconds':time.monotonic()-t,'source116':c['source116']}
try:os.killpg(child.pid,0);r['outerGroupAbsent']=False
except ProcessLookupError:r['outerGroupAbsent']=True
(p/'six-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
