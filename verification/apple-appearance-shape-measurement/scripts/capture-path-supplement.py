#!/usr/bin/env python3
"""One bounded own-simulator run for cell-height-constrained public path candidates."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
commands=[]
def command(name,args):
    name='supplement-'+name;log=ROOT/'logs'/f'{name}.log';start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(name,flush=True)
    with log.open('w') as out:result=subprocess.run(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
    commands.append(dict(name=name,argv=args,cwd=str(ROOT),startedUTC=start,finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=result.returncode,output=str(log.relative_to(ROOT))))
    (ROOT/'commands-supplement.json').write_text(json.dumps(commands,indent=2)+'\n')
    assert result.returncode==0,log
    return log.read_text().strip()
simulator=json.loads((ROOT/'simulator.json').read_text())['udid']
assert simulator!='1A7E942B-CF97-4DBB-8786-1D982744EBE4'
def sim(name,*args):return command(name,['xcrun','simctl',*args])
sources=[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for folder in ['instrumented-sdk','harness'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and 'xcuserdata' not in p.parts]
(ROOT/'source-lock-stage2.json').write_text(json.dumps({'files':sources},indent=2)+'\n')
sim('boot','boot',simulator);sim('bootstatus','bootstatus',simulator,'-b')
command('build',['xcodebuild','-project',str(ROOT/'harness/MixerAppearanceShapes.xcodeproj'),'-scheme','MixerAppearanceShapes','-configuration','Debug','-sdk','iphonesimulator','-destination','platform=iOS Simulator,id='+simulator,'-derivedDataPath',str(ROOT/'build/Debug'),'CODE_SIGNING_ALLOWED=NO','build'])
app=ROOT/'build/Debug/Build/Products/Debug-iphonesimulator/MixerAppearanceShapes.app'
sim('install','install',simulator,str(app))
container=Path(sim('container','get_app_container',simulator,'dev.mixer.appearanceshapes','data'))
sim('appearance','ui',simulator,'appearance','light');sim('size','ui',simulator,'content_size','large')
documents=container/'Documents';(documents/'measurements.json').unlink(missing_ok=True)
sim('launch','launch','--terminate-running-process',simulator,'dev.mixer.appearanceshapes','--fixture','controls')
deadline=time.monotonic()+30
while not (documents/'measurements.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('Missing measurement')
    time.sleep(.25)
time.sleep(2)
folder=ROOT/'path-supplement';folder.mkdir(exist_ok=True)
for name in ['measurements.json','environment.json','candidate-paths.json','track-continuous-r14.png','thumb-continuous-r12.png','group-continuous-r26.png','cell52-continuous-r26.png','cell63third-continuous-r26.png','cell101-continuous-r26.png']:
    shutil.copy2(documents/name,folder/name)
sim('screenshot','io',simulator,'screenshot','--type=png','--mask=black',str(folder/'screenshot.png'))
sim('shutdown','shutdown',simulator)
print('Captured one public-path supplement; no physical device or parity qualification.')
