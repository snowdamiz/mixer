#!/usr/bin/env python3
"""Build D/R and capture only a dedicated simulator, never discover phones."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, time
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'apple-appearance-reference'
LOGS = ROOT / 'logs'
LOGS.mkdir(exist_ok=True)
COMMANDS = []
def command(name, args):
    path = LOGS / (name + '.log')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(name, flush=True)
    with path.open('w') as stream:
        result = subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    COMMANDS.append(dict(name=name, argv=args, cwd=str(ROOT), startedUTC=started,
        finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), exitCode=result.returncode,
        output=str(path.relative_to(ROOT))))
    (ROOT / 'commands.json').write_text(json.dumps(COMMANDS, indent=2)+'\n')
    if result.returncode: raise RuntimeError(f'{name} failed; see {path}')
    return path.read_text()
def sim(name, *args): return command(name, ['xcrun', 'simctl', *args])
def files(path): return [dict(path=str(p.relative_to(path)), bytes=p.stat().st_size,
    sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(path.rglob('*')) if p.is_file()]
command('baseline-seal-before', ['python3', str(BASE/'scripts/verify-seal.py')])
command('prepare', ['python3', str(ROOT/'scripts/prepare.py')])
for name,args in [('xcode-version',['xcodebuild','-version']), ('swift-version',['xcrun','swift','--version']),
    ('sdk-version',['xcrun','--sdk','iphonesimulator','--show-sdk-version']),
    ('sdk-path',['xcrun','--sdk','iphonesimulator','--show-sdk-path']), ('host-version',['sw_vers']),
    ('git-revision',['git','rev-parse','HEAD']), ('git-tree',['git','rev-parse','HEAD^{tree}'])]: command(name,args)
# Simulator inventory is simulator-only. A separate named simulator avoids changing
# the immutable reference simulator's app or preferences.
if not (ROOT/'simulator.json').exists():
    identifier = sim('simulator-create','create','MixerAppearanceMeasurement',
        'com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro','com.apple.CoreSimulator.SimRuntime.iOS-27-0').strip()
    (ROOT/'simulator.json').write_text(json.dumps(dict(udid=identifier, name='MixerAppearanceMeasurement',
        deviceType='com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro', runtime='com.apple.CoreSimulator.SimRuntime.iOS-27-0'), indent=2)+'\n')
SIMULATOR = json.loads((ROOT/'simulator.json').read_text())['udid']
devices = json.loads(sim('simulator-inventory','list','devices','available','--json'))
selected = [(r,d) for r,ds in devices['devices'].items() for d in ds if d['udid']==SIMULATOR]
assert len(selected)==1 and selected[0][1]['name']=='MixerAppearanceMeasurement'
runtime,device = selected[0]
runtimes = json.loads(sim('runtime-inventory','list','runtimes','--json'))
info = json.loads((ROOT/'simulator.json').read_text())
info.update(device=device, runtimeDetails=next(r for r in runtimes['runtimes'] if r['identifier']==runtime))
(ROOT/'simulator.json').write_text(json.dumps(info,indent=2)+'\n')
if device['state']!='Booted': sim('boot','boot',SIMULATOR)
sim('bootstatus','bootstatus',SIMULATOR,'-b')
sim('status-bar','status_bar',SIMULATOR,'override','--time','9:41','--dataNetwork','wifi','--wifiMode','active','--wifiBars','3',
    '--cellularMode','active','--cellularBars','4','--batteryState','charged','--batteryLevel','100')
sim('increase-contrast','ui',SIMULATOR,'increase_contrast','disabled')
cases = [('typography','large',False,'typography'),('controls','large',False,'controls'),('layouts','large',False,'layouts'),
    ('rtl-large','accessibility-medium',True,'rtl-large'),('typography','accessibility-medium',False,'typography-accessibility'),
    ('controls','accessibility-medium',False,'controls-accessibility')]
captures=[]; apps=[]
for configuration in ['Debug','Release']:
    command('build-'+configuration.lower(), ['xcodebuild','-project',str(ROOT/'harness/MixerAppearanceMeasurement.xcodeproj'),
        '-scheme','MixerAppearanceMeasurement','-configuration',configuration,'-sdk','iphonesimulator',
        '-destination','platform=iOS Simulator,id='+SIMULATOR,'-derivedDataPath',str(ROOT/'build'/configuration),
        'CODE_SIGNING_ALLOWED=NO','build'])
    app=ROOT/f'build/{configuration}/Build/Products/{configuration}-iphonesimulator/MixerAppearanceMeasurement.app'
    apps.append(dict(configuration=configuration,files=files(app)))
    sim('install-'+configuration.lower(),'install',SIMULATOR,str(app))
    container=Path(sim('data-container-'+configuration.lower(),'get_app_container',SIMULATOR,'dev.mixer.appearancemeasurement','data').strip())
    for fixture,size,rtl,profile in cases:
        for appearance in ['light','dark']:
            name=configuration.lower()+'/'+profile+'-'+appearance
            prefix=name.replace('/','-'); folder=ROOT/'captures'/name;folder.mkdir(parents=True,exist_ok=True)
            sim(prefix+'-appearance-set','ui',SIMULATOR,'appearance',appearance)
            sim(prefix+'-size-set','ui',SIMULATOR,'content_size',size)
            sim(prefix+'-appearance-observed','ui',SIMULATOR,'appearance')
            sim(prefix+'-size-observed','ui',SIMULATOR,'content_size')
            documents=container/'Documents'
            for file in ['measurements.json','environment.json','rendered-document.json','fixture-validation.json']:
                (documents/file).unlink(missing_ok=True)
            args=['launch','--terminate-running-process',SIMULATOR,'dev.mixer.appearancemeasurement','--fixture',fixture]
            if rtl: args.append('--rtl')
            sim(prefix+'-launch',*args)
            deadline=time.monotonic()+30
            while not (documents/'measurements.json').exists():
                if time.monotonic()>deadline: raise RuntimeError('No measurement receipt: '+name)
                time.sleep(.25)
            time.sleep(2)
            for file in ['measurements.json','environment.json','rendered-document.json','fixture-validation.json']:
                shutil.copy2(documents/file,folder/file)
            environment=json.loads((folder/'environment.json').read_text())
            assert environment['fixture']==fixture and environment['swiftUIColorScheme']==appearance
            assert environment['swiftUILayoutDirection']==('rightToLeft' if rtl else 'leftToRight')
            assert (folder/'rendered-document.json').read_bytes()==(ROOT/'harness/Fixtures'/f'{fixture}.json').read_bytes()
            sim(prefix+'-screenshot','io',SIMULATOR,'screenshot','--type=png','--mask=black',str(folder/'screenshot.png'))
            captures.append(dict(name=name,fixture=fixture,profile=profile,configuration=configuration,requestedAppearance=appearance,
                requestedContentSize=size,requestedDirection='rightToLeft' if rtl else 'leftToRight',files=files(folder)))
            (ROOT/'capture-manifest.json').write_text(json.dumps(dict(captures=captures),indent=2)+'\n')
(ROOT/'built-app-manifest.json').write_text(json.dumps(dict(apps=apps),indent=2)+'\n')
command('baseline-seal-after',['python3',str(BASE/'scripts/verify-seal.py')])
print('Captured 24 instrumented screenshots and measurements; no parity qualification.',flush=True)
