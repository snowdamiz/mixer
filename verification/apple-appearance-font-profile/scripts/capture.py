#!/usr/bin/env python3
"""Collect actual native font preferences and one bounded candidate matrix."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,time
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'apple-appearance-measurement'
SIM='1A7E942B-CF97-4DBB-8786-1D982744EBE4';BUNDLE='dev.mixer.appearancefontprofile'
LOGS=ROOT/'logs';LOGS.mkdir(exist_ok=True);COMMANDS=[]
def command(name,args):
 p=LOGS/(name+'.log');started=datetime.datetime.now(datetime.timezone.utc).isoformat();print(name,flush=True)
 with p.open('w') as out:r=subprocess.run(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
 COMMANDS.append(dict(name=name,argv=args,cwd=str(ROOT),startedUTC=started,finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=r.returncode,output=str(p.relative_to(ROOT))))
 (ROOT/'commands.json').write_text(json.dumps(COMMANDS,indent=2)+'\n')
 if r.returncode:raise RuntimeError(name+' failed: '+p.read_text())
 return p.read_text()
def sim(name,*args):return command(name,['xcrun','simctl',*args])
def entries(path):return [dict(path=str(p.relative_to(path)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(path.rglob('*')) if p.is_file()]
def sources():return [dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for folder in ['instrumented-sdk','harness'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '.xcworkspace' not in str(p) and 'xcuserdata' not in p.parts]
def digest(items):return hashlib.sha256(json.dumps(items,sort_keys=True,separators=(',',':')).encode()).hexdigest()
command('prior-seal-before',['python3',str(BASE/'scripts/verify-seal.py')]);command('prepare',['python3',str(ROOT/'scripts/prepare.py')])
for name,args in [('xcode-version',['xcodebuild','-version']),('swift-version',['xcrun','swift','--version']),('sdk-version',['xcrun','--sdk','iphonesimulator','--show-sdk-version']),('sdk-path',['xcrun','--sdk','iphonesimulator','--show-sdk-path']),('host-version',['sw_vers']),('git-revision',['git','rev-parse','HEAD']),('git-tree',['git','rev-parse','HEAD^{tree}'])]:command(name,args)
devices=json.loads(sim('simulator-only-inventory','list','devices','available','--json'))
selected=[(r,d) for r,ds in devices['devices'].items() for d in ds if d['udid']==SIM]
assert len(selected)==1 and selected[0][1]['name']=='MixerAppearanceMeasurement'
(ROOT/'simulator.json').write_text(json.dumps(dict(udid=SIM,runtime=selected[0][0],device=selected[0][1]),indent=2)+'\n')
if selected[0][1]['state']!='Booted':sim('boot','boot',SIM)
sim('bootstatus','bootstatus',SIM,'-b');sim('status-bar','status_bar',SIM,'override','--time','9:41','--dataNetwork','wifi','--wifiMode','active','--wifiBars','3','--cellularMode','active','--cellularBars','4','--batteryState','charged','--batteryLevel','100');sim('contrast','ui',SIM,'increase_contrast','disabled')
preferences=[('xs','extra-small','xSmall'),('s','small','small'),('m','medium','medium'),('l','large','large'),('xl','extra-large','xLarge'),('xxl','extra-extra-large','xxLarge'),('xxxl','extra-extra-extra-large','xxxLarge'),('a1','accessibility-medium','accessibility1'),('a2','accessibility-large','accessibility2'),('a3','accessibility-extra-large','accessibility3'),('a4','accessibility-extra-extra-large','accessibility4'),('a5','accessibility-extra-extra-extra-large','accessibility5')]
cases=[('typography','large',False,'typography'),('controls','large',False,'controls'),('layouts','large',False,'layouts'),('rtl-large','accessibility-medium',True,'rtl-large'),('typography','accessibility-medium',False,'typography-accessibility'),('controls','accessibility-medium',False,'controls-accessibility')]
profiles=[];captures=[];apps=[];source_before=sources()
def observe(configuration,name,fixture,size,appearance,rtl,candidate,png,container):
 folder=ROOT/'observations'/configuration.lower()/name;folder.mkdir(parents=True,exist_ok=True);prefix=configuration.lower()+'-'+name
 sim(prefix+'-appearance-set','ui',SIM,'appearance',appearance);sim(prefix+'-size-set','ui',SIM,'content_size',size)
 sim(prefix+'-appearance-observed','ui',SIM,'appearance');sim(prefix+'-size-observed','ui',SIM,'content_size')
 files=['measurements.json','environment.json','rendered-document.json','fixture-validation.json','font-profile.json']
 for filename in files:(container/'Documents'/filename).unlink(missing_ok=True)
 args=['launch','--terminate-running-process',SIM,BUNDLE,'--fixture',fixture]
 if rtl:args+=['--rtl']
 if candidate:args+=['--candidate-fonts']
 sim(prefix+'-launch',*args);deadline=time.monotonic()+30
 while not (container/'Documents/font-profile.json').exists():
  if time.monotonic()>deadline:raise RuntimeError('Missing native font profile: '+name)
  time.sleep(.25)
 time.sleep(1.5)
 for filename in files:shutil.copy2(container/'Documents'/filename,folder/filename)
 env=json.loads((folder/'environment.json').read_text());fp=json.loads((folder/'font-profile.json').read_text())
 assert env['swiftUIColorScheme']==appearance and env['swiftUILayoutDirection']==('rightToLeft' if rtl else 'leftToRight')
 assert fp['candidateFontsApplied']==candidate and (folder/'rendered-document.json').read_bytes()==(ROOT/'harness/Fixtures'/f'{fixture}.json').read_bytes()
 if png:sim(prefix+'-png','io',SIM,'screenshot','--type=png','--mask=black',str(folder/'screenshot.png'))
 return dict(name=name,path=str(folder.relative_to(ROOT)),configuration=configuration,fixture=fixture,requestedContentSize=size,requestedAppearance=appearance,rtl=rtl,candidateFontsApplied=candidate,files=entries(folder))
for configuration in ['Debug','Release']:
 command('build-'+configuration.lower(),['xcodebuild','-project',str(ROOT/'harness/MixerAppearanceFontProfile.xcodeproj'),'-scheme','MixerAppearanceFontProfile','-configuration',configuration,'-sdk','iphonesimulator','-destination','platform=iOS Simulator,id='+SIM,'-derivedDataPath',str(ROOT/'build'/configuration),'CODE_SIGNING_ALLOWED=NO','build'])
 app=ROOT/f'build/{configuration}/Build/Products/{configuration}-iphonesimulator/MixerAppearanceFontProfile.app';apps.append(dict(configuration=configuration,files=entries(app)))
 sim('install-'+configuration.lower(),'install',SIM,str(app));container=Path(sim('container-'+configuration.lower(),'get_app_container',SIM,BUNDLE,'data').strip())
 for profile,size,dynamic in preferences:
  result=observe(configuration,'profile-'+profile,'typography',size,'light',False,False,False,container);result.update(profileID=profile,expectedSwiftUIDynamicTypeSize=dynamic);profiles.append(result)
  (ROOT/'observation-manifest.json').write_text(json.dumps(dict(preferences=preferences,profiles=profiles,captures=captures),indent=2)+'\n')
 if configuration=='Debug':
  for fixture,size,rtl,profile,appearance in [('typography','large',False,'typography','light'),('controls','large',False,'controls','dark'),('rtl-large','accessibility-medium',True,'rtl-large','light')]:
   result=observe(configuration,'control-'+profile+'-'+appearance,fixture,size,appearance,rtl,False,True,container);result.update(baselineCase=profile+'-'+appearance);captures.append(result)
 for fixture,size,rtl,profile in cases:
  for appearance in ['light','dark']:
   if configuration=='Release' and (profile,appearance) not in [('typography','light'),('controls','dark'),('rtl-large','light')]:continue
   result=observe(configuration,'candidate-'+profile+'-'+appearance,fixture,size,appearance,rtl,True,True,container);result.update(baselineCase=profile+'-'+appearance);captures.append(result)
   (ROOT/'observation-manifest.json').write_text(json.dumps(dict(preferences=preferences,profiles=profiles,captures=captures),indent=2)+'\n')
source_after=sources();assert source_before==source_after,'source changed during D/R capture'
(ROOT/'capture-source-lock.json').write_text(json.dumps(dict(files=source_before,sourceCollectionSHA256=digest(source_before),sourceStableAcrossBuildAndCapture=True),indent=2)+'\n')
(ROOT/'built-app-manifest.json').write_text(json.dumps(dict(apps=apps),indent=2)+'\n')
command('prior-seal-after',['python3',str(BASE/'scripts/verify-seal.py')])
print('24 native profile exports,3 unmodified PNG controls,12 Debug candidate PNGs and3 Release repeats collected.',flush=True)
