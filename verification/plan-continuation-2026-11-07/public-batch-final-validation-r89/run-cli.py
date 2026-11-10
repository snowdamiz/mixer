from pathlib import Path
import hashlib,json,os,shlex,subprocess,tempfile,time
p=Path(__file__).resolve().parent;root=p.parents[2];c=json.loads((p/'selection-six.json').read_text())
manifest=json.loads((root/'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/source-inputs.json').read_text())
assert len(manifest)==116 and hashlib.sha256(''.join(rel+'\0'+pin['sha256']+'\n' for rel,pin in sorted(manifest.items())).encode()).hexdigest()==c['source116']
assert all(hashlib.sha256((root/rel).read_bytes()).hexdigest()==pin['sha256'] for rel,pin in manifest.items())
owned=Path(json.loads((root/'verification/plan-continuation-2026-11-07/public-batch-installed-delivery-r87/cli-result.json').read_text())['ownedScratch'])
for n in ['tmp','bin']:(owned/n).mkdir(exist_ok=True)
swift=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
launcher=owned/'bin/swift';selected=shlex.quote(str(swift))
launcher.write_text('#!/bin/sh\nif [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then\n  exec '+selected+' "$@" 2>&1\nfi\nexec '+selected+' "$@"\n');launcher.chmod(0o700)
e=os.environ.copy();e.update(DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',SDKROOT='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk',TMPDIR=str(owned/'tmp')+'/',PATH=str(owned/'bin')+':'+str(swift.parent)+':'+e['PATH'],SWIFT_EXEC=str(swift.parent/'swiftc'),MIXER_STORE_TEST_CLI=str(owned/'build/debug/mixer'),MIXER_STORE_CUSTODY_DIR=str(p/'cli-children'),MIXER_SUITE_HOLD=str(p/'CLI-SUITE-HOLD.json'),ANDROID_HOME='/opt/homebrew/share/android-commandlinetools',JAVA_HOME='/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
argv=[str(swift),'test','--package-path','cli','--scratch-path',str(owned/'build'),'--disable-sandbox','-j','2'];started=time.monotonic()
row={'argv':argv,'cwd':str(root),'ownedScratch':str(owned),'source116':c['source116'],'testEnvironment':{k:e[k] for k in ['MIXER_STORE_TEST_CLI','MIXER_STORE_CUSTODY_DIR','MIXER_SUITE_HOLD']}}
with (p/'cli.log').open('wb') as log:
 child=subprocess.Popen(argv,cwd=root,env=e,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);row.update(pid=child.pid,pgid=child.pid)
 (p/'cli-command.json').write_text(json.dumps(row,indent=2)+'\n')
 code=child.wait()
try:os.killpg(child.pid,0);absent=False
except ProcessLookupError:absent=True
row.update(exitCode=code,groupAbsent=absent,elapsedSeconds=time.monotonic()-started,suiteHold=(p/'CLI-SUITE-HOLD.json').exists())
cli=owned/'build/debug/mixer'
if cli.is_file():row['CLI_SHA256']=hashlib.sha256(cli.read_bytes()).hexdigest()
(p/'cli-result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
