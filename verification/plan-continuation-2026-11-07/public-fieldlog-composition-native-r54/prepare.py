import hashlib,json,os,pathlib,re,secrets,shutil,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[3];base=root/'verification/plan-continuation-2026-11-07';p=pathlib.Path(__file__).parent
source=base/'public-fieldlog-native-composition-r53';b=json.loads((source/'build-result.json').read_text());unsigned=pathlib.Path(b['apk']);assert b['buildPassed'] is True and hashlib.sha256(unsigned.read_bytes()).hexdigest()==b['sha256']
assert not (p/'runtime-plan.json').exists() and not (p/'emulator-ownership.json').exists()
c=json.loads((base/'fieldlog-final-owner-cleanup-protected-baseline-r22/runtime-plan.json').read_text());signed=p/'FieldLog-native-composition-r53-debug.apk'
keydir=pathlib.Path(tempfile.mkdtemp(prefix='mixer-r54-debug-key-',dir='/Users/andreyyurlov/.t3/userdata'));os.chmod(keydir,0o700)
e=os.environ.copy();e['JAVA_HOME']=c['javaHome'];e['MIXER_R29_DEV_PASSWORD']=secrets.token_urlsafe(24);e.pop('JAVA_TOOL_OPTIONS',None)
key=str(keydir/'debug.keystore');tool=pathlib.Path(c['sdk'])/'build-tools/37.0.0/apksigner'
commands=[[str(pathlib.Path(c['javaHome'])/'bin/keytool'),'-genkeypair','-keystore',key,'-storepass:env','MIXER_R29_DEV_PASSWORD','-keypass:env','MIXER_R29_DEV_PASSWORD','-alias','mixer-local-debug','-keyalg','RSA','-keysize','2048','-validity','30','-dname','CN=Mixer local development,O=Mixer,C=US'],[str(tool),'sign','--ks',key,'--ks-key-alias','mixer-local-debug','--ks-pass','env:MIXER_R29_DEV_PASSWORD','--key-pass','env:MIXER_R29_DEV_PASSWORD','--v4-signing-enabled','false','--out',str(signed),str(unsigned)],[str(tool),'verify','--verbose',str(signed)]];results=[]
try:
 for i,a in enumerate(commands):
  with (p/('sign-'+str(i)+'.stdout')).open('wb') as out,(p/('sign-'+str(i)+'.stderr')).open('wb') as err:r=subprocess.run(a,env=e,stdout=out,stderr=err,timeout=30)
  results.append({'argv':a,'exitCode':r.returncode});assert r.returncode==0
finally:
 shutil.rmtree(keydir);e.pop('MIXER_R29_DEV_PASSWORD',None)
(p/'signing.json').write_text(json.dumps({'commands':results,'privateDevelopmentKeyRemoved':True,'productionSigning':False,'signedAPKSHA256':hashlib.sha256(signed.read_bytes()).hexdigest()},indent=2)+'\n')
c.update(sourceAPK=str(unsigned),sourceAPKSHA256=b['sha256'],signedAPK=str(signed),package=b['package'],expectedPASS=b['expectedPASS'],scope='Actual public SDK FieldLog native InputConnection composition/selection/save/reopen; original handoff/final-ledger assertions retained; API37 arm64 development emulator',physicalDeviceTestingAuthorized=False)
script=(base/'public-surface-revoke-diagnostic-r46/run-native.py').read_text()
script=script.replace("'FieldLogPublicR42:E'","'FieldLogPublicR42:E','FieldLogCompositionR53:I'")
script=script.replace("],90)","],120)")
(p/'runtime-plan.json').write_text(json.dumps(c,indent=2)+'\n');(p/'run-native.py').write_text(script)
print(json.dumps({'signedAPK':str(signed),'sourceSHA256':b['sha256'],'component':b['instrumentationComponent'],'privateKeyRemoved':True}))
