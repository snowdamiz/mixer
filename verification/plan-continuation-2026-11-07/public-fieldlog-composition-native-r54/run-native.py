import json,os,pathlib,subprocess,time
p=pathlib.Path(__file__).parent;c=json.loads((p/'runtime-plan.json').read_text());started=time.monotonic();commands=[];child=None;verified=False;result={'passed':False,'scope':c['scope']}
def run(name,args,timeout=30,check=True):
 t=time.monotonic()
 with (p/(name+'.stdout')).open('wb') as out,(p/(name+'.stderr')).open('wb') as err:
  r=subprocess.run(args,stdout=out,stderr=err,timeout=timeout)
 commands.append({'name':name,'argv':args,'exitCode':r.returncode,'elapsedSeconds':time.monotonic()-t})
 (p/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 if check and r.returncode: raise RuntimeError(name+' exit '+str(r.returncode))
 return (p/(name+'.stdout')).read_text()
def adb(name,args,timeout=30,check=True): return run(name,[c['adb'],'-s',c['serial']]+args,timeout,check)
try:
 devices=run('baseline-devices',[c['adb'],'devices','-l'])
 baseline_devices=[s.strip() for s in devices.splitlines()[1:] if s.strip()]
 result['protectedExternalDevicesBefore']=baseline_devices
 if any(s.split()[0]==c['serial'] for s in baseline_devices): raise RuntimeError('Owned serial already present; preserve and do not launch duplicate')
 e=os.environ.copy();e.update(ANDROID_HOME=c['sdk'],ANDROID_SDK_ROOT=c['sdk'],ANDROID_AVD_HOME=c['avdHome'])
 with (p/'emulator.stdout').open('wb') as out,(p/'emulator.stderr').open('wb') as err:
  child=subprocess.Popen(c['emulatorArgv'],env=e,stdout=out,stderr=err,start_new_session=True)
 (p/'emulator-ownership.json').write_text(json.dumps({'pid':child.pid,'serial':c['serial'],'argv':c['emulatorArgv'],'ownedRoot':c['ownedRoot']},indent=2)+'\n')
 adb('wait-device',['wait-for-device'],50)
 name=adb('owned-avd-name',['emu','avd','name'])
 if c['avdName'] not in name.splitlines(): raise RuntimeError('Owned AVD identity mismatch')
 verified=True
 for i in range(60):
  if adb('boot-%02d'%i,['shell','getprop','sys.boot_completed'],5).strip()=='1':break
  time.sleep(.5)
 else: raise RuntimeError('Boot deadline exceeded')
 adb('power-before',['shell','dumpsys','power'],15,False)
 adb('wake-owned-device',['shell','input','keyevent','KEYCODE_WAKEUP'],15)
 adb('dismiss-owned-keyguard',['shell','wm','dismiss-keyguard'],15)
 adb('power-after',['shell','dumpsys','power'],15,False)
 adb('install',['install','-r',c['signedAPK']],35)
 output=adb('instrument',['shell','am','instrument','-w',c['package']+'/dev.mixer.android.FieldLogInstrumentation'],120)
 result['instrumentationPassed']=c['expectedPASS'] in output and 'INSTRUMENTATION_CODE: -1' in output
 adb('workspace',['shell','run-as',c['package'],'cat','files/fieldlog-public-workspace/workspace.json'],15,False)
 adb('owner-state-log',['logcat','-d','-v','threadtime','-s','FieldLogOwnerR17:D','FieldLogHostR12:E','*:S'],15,False)
 adb('crash-log',['logcat','-d','-b','crash','-t','100'],15,False)
 result['passed']=result['instrumentationPassed']
except Exception as error:result['error']=repr(error)
finally:
 if verified:
  for label,argv in [('final-context-log',['logcat','-d','-v','threadtime','-s','FieldLogPremiseR36:D','FieldLogPublicR42:E','FieldLogCompositionR53:I','FieldLogContextR24:D','FieldLogOwnerR17:D','FieldLogHostR12:E','AndroidRuntime:E','*:S']),('final-activities',['shell','dumpsys','activity','activities']),('final-crash-log',['logcat','-d','-b','crash','-t','100'])]:
   try:adb(label,argv,15,False)
   except Exception as error:result[label+'Error']=repr(error)
  try:adb('force-stop',['shell','am','force-stop',c['package']],15)
  except Exception as error:result['forceStopError']=repr(error)
  try:adb('emulator-quit',['emu','kill'],15)
  except Exception as error:result['emulatorQuitError']=repr(error)
 if child is not None:
  try:code=child.wait(timeout=20)
  except subprocess.TimeoutExpired:
   child.terminate()
   try:code=child.wait(timeout=10)
   except subprocess.TimeoutExpired:child.kill();code=child.wait(timeout=10)
  result['emulatorExitCode']=code
 try:result['devicesAfter']=run('devices-after',[c['adb'],'devices','-l'],15)
 except Exception as error:result['devicesAfterError']=repr(error)
 external_after=[s.strip() for s in result.get('devicesAfter','').splitlines()[1:] if s.strip() and s.split()[0]!=c['serial']]
 result['externalBaselineUnchanged']=sorted(external_after)==sorted(result.get('protectedExternalDevicesBefore',[]))
 result['physicalDeviceTargetedCommands']=0
 if not result['externalBaselineUnchanged']:result['passed']=False;result['cleanupFailure']='External device baseline changed; coordinate before further native work'
 result['elapsedSeconds']=time.monotonic()-started
 (p/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
