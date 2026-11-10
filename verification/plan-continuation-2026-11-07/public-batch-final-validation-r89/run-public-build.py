from pathlib import Path
import hashlib,json,os,subprocess,tempfile,time
p=Path(__file__).resolve().parent;root=p.parents[2];c=json.loads((p/'cli-result.json').read_text());assert c['exitCode']==0 and c['groupAbsent'] and not c['suiteHold']
owned=Path(tempfile.mkdtemp(prefix='mixer-public-final-r89-',dir='/Users/andreyyurlov/.t3/userdata'));(owned/'tmp').mkdir();project=owned/'PublicFinal';cli=Path(c['ownedScratch'])/'build/debug/mixer';swift=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
env=os.environ.copy();env.update(DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',SDKROOT='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk',TMPDIR=str(owned/'tmp')+'/',PATH=str(Path(c['ownedScratch'])/'bin')+':'+str(swift.parent)+':'+env['PATH'],SWIFT_EXEC=str(swift.parent/'swiftc'),ANDROID_HOME='/opt/homebrew/share/android-commandlinetools',JAVA_HOME='/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
selection={'owned':str(owned),'project':str(project),'CLI_SHA256':hashlib.sha256(cli.read_bytes()).hexdigest(),'source116':c['source116'],'scope':'Fresh explicit public-v3 project through full production CLI; unsigned APK cross-build only, no devices/signing/GA'};(p/'public-build-selection.json').write_text(json.dumps(selection,indent=2)+'\n');rows=[]
for label,args in [('create',[str(cli),'create','PublicFinal','--platform','android','--android-host','public-v3','--application','example.r89.publicapp','--sdk-path',str(root/'sdk'),'--android-adapter-path',str(root/'native/android'),'--directory',str(project)]),('build',[str(cli),'build','--platform','android','--directory',str(project)])]:
 started=time.monotonic()
 with (p/('public-'+label+'.stdout')).open('wb') as out,(p/('public-'+label+'.stderr')).open('wb') as err:
  child=subprocess.Popen(args,cwd=root,env=env,stdout=out,stderr=err,start_new_session=True);row={'label':label,'argv':args,'pid':child.pid,'pgid':child.pid};rows.append(row);(p/'public-build-commands.json').write_text(json.dumps(rows,indent=2)+'\n');code=child.wait()
 try:os.killpg(child.pid,0);absent=False
 except ProcessLookupError:absent=True
 row.update(exitCode=code,groupAbsent=absent,seconds=time.monotonic()-started);(p/'public-build-commands.json').write_text(json.dumps(rows,indent=2)+'\n')
 if code or not absent:raise RuntimeError(label+' failed; preserve owned outputs')
apks=list(project.glob('.mixer/android-build/*-unsigned.apk'));assert len(apks)==1
receipts=[]
for file in (owned/'tmp').glob('mixer-command-receipts-*/command-*/receipt.json'):
 d=json.loads(file.read_text());assert d['state']=='TERMINAL';receipts.append({'path':str(file),'receipt':d})
(p/'public-build-inner-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
result={'status':'PASS_FULL_CLI_CREATE_AND_PUBLIC_V3_ANDROID_BUILD','source116':c['source116'],'unsignedAPK':str(apks[0]),'APK_SHA256':hashlib.sha256(apks[0].read_bytes()).hexdigest(),'seconds':sum(r['seconds'] for r in rows),'innerTerminalReceipts':len(receipts),'allOuterGroupsAbsent':True,'deviceCommands':0,'signed':False,'GA':False}
(p/'public-build-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
