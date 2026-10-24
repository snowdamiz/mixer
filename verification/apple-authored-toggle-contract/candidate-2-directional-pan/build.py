#!/usr/bin/env python3
"""Build the sealed owned-source toggle app. Does not boot any simulator."""
import pathlib,subprocess,json,hashlib,shutil,tarfile,datetime
PACKET=pathlib.Path(__file__).resolve().parent
ROOT=PACKET.parents[1]
SOURCE=PACKET/'source'
BUILD=PACKET/'build'
BUILD.mkdir(exist_ok=True)
commands=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):
 r=subprocess.run(list(map(str,args)),cwd=ROOT,text=True,capture_output=True)
 commands.append(dict(argv=list(map(str,args)),exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 (PACKET/'build-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout.strip()
revision=run(['git','rev-parse','HEAD']);tree=run(['git','rev-parse','HEAD^{tree}'])
run(['xcodebuild','-version']);run(['xcrun','swiftc','--version']);sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path'])
lock=dict(revision=revision,gitTree=tree,scope='Owned source closure for isolated carrier prototype; no product edits',sha256={str(p.relative_to(SOURCE)):digest(p) for p in sorted(SOURCE.rglob('*')) if p.is_file()})
lock['closureSHA256']=hashlib.sha256(json.dumps(lock['sha256'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
(PACKET/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
common=['xcrun','swiftc','-target','arm64-apple-ios26.0-simulator','-sdk',sdk,'-swift-version','6','-I',BUILD,'-L',BUILD]
for module,libs in [('MixerCore',[]),('MixerUI',['MixerCore'])]:
 run(common+['-emit-library','-emit-module','-module-name',module,'-emit-module-path',BUILD/(module+'.swiftmodule'),'-o',BUILD/('lib'+module+'.dylib')]+sorted((SOURCE/'sdk/Sources'/module).glob('*.swift'))+['-l'+x for x in libs]+['-Xlinker','-install_name','-Xlinker','@rpath/lib'+module+'.dylib'])
app=BUILD/'MixerAuthoredToggle.app'
app.mkdir(exist_ok=True);(app/'Frameworks').mkdir(exist_ok=True)
shutil.copy2(SOURCE/'Prototype/Info.plist',app/'Info.plist')
for module in ['MixerCore','MixerUI']:
 dest=app/'Frameworks'/('lib'+module+'.dylib');shutil.copy2(BUILD/('lib'+module+'.dylib'),dest)
 run(['codesign','--force','--sign','-',dest])
run(common+sorted((SOURCE/'Prototype').glob('*.swift'))+['-o',app/'MixerAuthoredToggle','-lMixerCore','-lMixerUI','-Xlinker','-rpath','-Xlinker','@executable_path/Frameworks','-framework','UIKit'])
run(['codesign','--force','--sign','-',app])
with tarfile.open(PACKET/'built-app.tar.gz','w:gz') as archive:archive.add(app,arcname=app.name)
manifest=dict(archive='built-app.tar.gz',archiveSHA256=digest(PACKET/'built-app.tar.gz'),deploymentTarget='arm64-apple-ios26.0-simulator',files={str(p.relative_to(app)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in sorted(app.rglob('*')) if p.is_file()})
(PACKET/'built-app-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(app=str(app),sourceClosureSHA256=lock['closureSHA256'],archiveSHA256=manifest['archiveSHA256']),indent=2))
