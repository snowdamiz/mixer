#!/usr/bin/env python3
"""Dedicated installed simulator, exact source-bound internal consumer receipts."""
import argparse, pathlib, subprocess, json, hashlib, tempfile, shutil, time, os, sys, tarfile
ROOT=pathlib.Path(__file__).resolve().parents[3]
SOURCE=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'verification/apple-native-appearance-v2'
BUILD=pathlib.Path('/tmp/mixer-native-appearance-v2-build')
parser=argparse.ArgumentParser(); parser.add_argument('--keep-simulator',action='store_true'); parser.add_argument('--simulator'); parser.add_argument('--output',default=str(OUT/'candidate-1'))
args=parser.parse_args(); OUT=pathlib.Path(args.output); OUT.mkdir(parents=True,exist_ok=True)
commands=[]
def run(*argv,check=True):
    start=time.time(); result=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
    commands.append(dict(argv=list(map(str,argv)),exitCode=result.returncode,stdout=result.stdout,stderr=result.stderr,elapsedSeconds=round(time.time()-start,3)))
    (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    if check and result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return result.stdout.strip()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def wait_stage(container,stage):
    for _ in range(160):
        marker=container/'Documents/stage.txt'
        if marker.exists() and marker.read_text()==stage: return
        time.sleep(.1)
    raise RuntimeError('No stage: '+stage)
inputs=sorted((ROOT/'sdk/Sources/MixerCore').glob('*.swift'))+sorted((ROOT/'sdk/Sources/MixerUI').glob('*.swift'))+sorted((ROOT/'sdk/Sources/MixerApple').glob('Appearance*V2.swift'))+sorted(SOURCE.glob('*'))+[ROOT/'AGENTS.md',ROOT/'docs/ui-measured-appearance-v2-contract.md',ROOT/'docs/native-appearance-v2-staging.md',ROOT/'docs/apple-native-field-paint-probe.md']
inputs=[p for p in inputs if p.is_file()]
lock=dict(revision=run('git','rev-parse','HEAD'),tree=run('git','rev-parse','HEAD^{tree}'),dirtyPaths=run('git','status','--short'),sha256={str(p.relative_to(ROOT)):digest(p) for p in inputs})
for source in inputs:
    destination=OUT/'inputs'/source.relative_to(ROOT); destination.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,destination)
(OUT/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
run('xcodebuild','-version');run('xcrun','swiftc','--version')
run('python3',str(SOURCE/'build-check.py'))
shutil.copy2(ROOT/'verification/apple-native-appearance-v2/build-commands.json',OUT/'build-commands.json')
sdk=run('xcrun','--sdk','iphonesimulator','--show-sdk-path')
# Host-only descriptor emitter calls the one Swift codec/default, never a second maintained table.
host=BUILD/'host';host.mkdir(exist_ok=True)
for module, sources, libs in [('MixerCore', sorted((ROOT/'sdk/Sources/MixerCore').glob('*.swift')), []),('MixerUI', sorted((ROOT/'sdk/Sources/MixerUI').glob('*.swift')), ['MixerCore'])]:
    run('xcrun','swiftc','-emit-library','-emit-module','-module-name',module,'-emit-module-path',str(host/(module+'.swiftmodule')),'-o',str(host/('lib'+module+'.dylib')),'-I',str(host),'-L',str(host),*map(str,sources),*['-l'+x for x in libs],'-Xlinker','-install_name','-Xlinker',str(host/('lib'+module+'.dylib')))
run('xcrun','swiftc',str(SOURCE/'default-descriptor.swift'),str(SOURCE/'Fixture.swift'),'-I',str(host),'-L',str(host),'-lMixerCore','-lMixerUI','-o',str(host/'emit'))
run(str(host/'emit'),str(OUT/'descriptor.json'),str(OUT/'unsupported-resources.json'),str(OUT/'fixture-native-packet.bin'),str(OUT/'short-rows-descriptor.json'))
work=pathlib.Path(tempfile.mkdtemp(prefix='mixer-appearance-v2-'));app=work/'MixerAppearanceV2.app';app.mkdir();(app/'Frameworks').mkdir()
shutil.copy2(SOURCE/'Info.plist',app/'Info.plist')
(app/'MixerAppearanceV2').mkdir();shutil.copy2(OUT/'descriptor.json',app/'MixerAppearanceV2/descriptor.json')
for fixture,bytes_ in [('BadDescriptor',b'{}\n'),('UnsupportedResources',(OUT/'unsupported-resources.json').read_bytes()),('ShortRows',(OUT/'short-rows-descriptor.json').read_bytes())]:
    directory=app/(fixture+'.bundle');directory.mkdir();(directory/'MixerAppearanceV2').mkdir()
    (directory/'Info.plist').write_text('<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict><key>CFBundleIdentifier</key><string>dev.mixer.fixture.'+fixture+'</string></dict></plist>')
    (directory/'MixerAppearanceV2/descriptor.json').write_bytes(bytes_)
for name in ['MixerCore','MixerUI','MixerAppearanceInternal']:
    shutil.copy2(BUILD/('lib'+name+'.dylib'),app/'Frameworks'/('lib'+name+'.dylib'))
    run('codesign','--force','--sign','-',str(app/'Frameworks'/('lib'+name+'.dylib')))
run('xcrun','swiftc',str(SOURCE/'main.swift'),str(SOURCE/'Fixture.swift'),str(SOURCE/'CoverGeometryRegression.swift'),'-o',str(app/'MixerAppearanceV2Harness'),'-target','arm64-apple-ios17.0-simulator','-sdk',sdk,'-swift-version','6','-I',str(BUILD),'-L',str(BUILD),'-lMixerCore','-lMixerUI','-lMixerAppearanceInternal','-Xlinker','-rpath','-Xlinker','@executable_path/Frameworks','-framework','UIKit')
run('codesign','--force','--sign','-',str(app))
(OUT/'built-app.json').write_text(json.dumps(dict(binarySHA256=digest(app/'MixerAppearanceV2Harness'),libraries={p.name:digest(p) for p in (app/'Frameworks').glob('*')},descriptorSHA256=digest(app/'MixerAppearanceV2/descriptor.json'),deploymentTarget='arm64-apple-ios17.0-simulator'),indent=2)+'\n')
artifactFiles={str(p.relative_to(app)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in app.rglob('*') if p.is_file()}
with tarfile.open(OUT/'built-app.tar.gz','w:gz') as archive: archive.add(app,arcname=app.name)
(OUT/'built-app-manifest.json').write_text(json.dumps(dict(archive='built-app.tar.gz',sha256=digest(OUT/'built-app.tar.gz'),files=artifactFiles),indent=2)+'\n')
before=json.loads(run('xcrun','simctl','list','devices','--json'))
runtimes=json.loads(run('xcrun','simctl','list','runtimes','--json'))['runtimes']
runtime=next(x for x in runtimes if x.get('isAvailable') and x['version']=='26.5')
sim=args.simulator or run('xcrun','simctl','create','MixerAppearanceV2Consumer','com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',runtime['identifier'])
if args.simulator:
    matches=[device for key,values in before['devices'].items() if key==runtime['identifier'] for device in values if device['udid']==sim]
    if len(matches)!=1: raise RuntimeError('Explicit owned simulator absent or wrong runtime')
lifecycle=dict(ownedSimulator=sim,runtime=runtime,before=before)
(OUT/'simulator-lifecycle.json').write_text(json.dumps(lifecycle,indent=2)+'\n')
try:
    if not args.simulator: run('xcrun','simctl','boot',sim)
    run('xcrun','simctl','bootstatus',sim,'-b')
    run('xcrun','simctl','status_bar',sim,'override','--time','9:41','--dataNetwork','wifi','--wifiMode','active','--wifiBars','3','--batteryState','charged','--batteryLevel','100')
    run('xcrun','simctl','install',sim,str(app))
    container=pathlib.Path(run('xcrun','simctl','get_app_container',sim,'dev.mixer.verification.appearancev2','data'))
    for name in ['stage.txt','command.txt','observations.json']:
        (container/'Documents'/name).unlink(missing_ok=True)
    run('xcrun','simctl','launch','--terminate-running-process',sim,'dev.mixer.verification.appearancev2')
    wait_stage(container,'initial');time.sleep(10)
    run('xcrun','simctl','io',sim,'screenshot',str(OUT/'initial.png'))
    stages=['focus','selection','ordinary','ancestor-move','composition','environment','stale','native-state-stale','interaction-stale',*['profile-'+p for p in ['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5','l']],'authoritative-bindings','contrast','contrast-restore','accessibility','short-rows','dark','rtl','restore-environment','selectable-rtl','outside-section','cover-final-coordinates','baseline-regressions','unsupported-contexts','selectable-retention','callback','pressed','normal','toggle-input','toggle-reset','caret','blink-a','blink-b','blink-c','blink-d','scroll','scroll-update','scroll-top','foreign-fault','disabled','interactive']
    for stage in stages:
        (container/'Documents/command.txt').write_text(stage)
        commands.append(dict(operation='writeNativeHarnessControlFile',stage=stage))
        wait_stage(container,stage);time.sleep(.31 if stage.startswith('blink-') else .15)
        run('xcrun','simctl','io',sim,'screenshot',str(OUT/(stage+'.png')))
    for name in ['observations.json','fixture-document.json','fixture-native-packet.bin','fixture-frames-roles-states.json','outside-section-native-hierarchy.png']:
        shutil.copy2(container/'Documents'/name,OUT/name)
    result=json.loads((OUT/'observations.json').read_text())
    failed=[x for x in result['checks'] if not x['pass']]
    (OUT/'result.json').write_text(json.dumps(dict(checkCount=len(result['checks']),failed=failed,simulator=sim,scope='Actual installed internal UIKit module consumer, simulator development evidence; no public facade/signing/physical/keyboard IME/VoiceOver qualification'),indent=2)+'\n')
    print(json.dumps(dict(output=str(OUT),simulator=sim,container=str(container),failed=failed),indent=2))
    if failed: sys.exit(1)
finally:
    if not args.keep_simulator:
        run('xcrun','simctl','shutdown',sim,check=False);run('xcrun','simctl','delete',sim,check=False)
        lifecycle['cleanedUp']=True
    else: lifecycle['keptForInteraction']=True
    lifecycle['after']=json.loads(run('xcrun','simctl','list','devices','--json'))
    (OUT/'simulator-lifecycle.json').write_text(json.dumps(lifecycle,indent=2)+'\n')
    shutil.rmtree(work)
