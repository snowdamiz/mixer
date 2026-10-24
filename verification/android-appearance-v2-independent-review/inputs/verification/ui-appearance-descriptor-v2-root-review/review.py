from pathlib import Path
import base64,copy,datetime,hashlib,importlib.util,json,os,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SOURCE=ROOT/'verification/ui-appearance-descriptor-v2/candidate-1'
SNAP=SOURCE/'inputs';BUILD=HERE/'build';BUILD.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((SOURCE/'receipt.json').read_text());bindings={};commands=[];status='failed';counts={}
if r['status']!='passed-data-only':raise RuntimeError('producer not ready')
for p,h in r['inputManifest'].items():
 for f in [ROOT/p,SNAP/p]:
  if sha(f)!=h:raise RuntimeError('input changed '+str(f))
  bindings[str(f.relative_to(ROOT))]=h
for c in r['commands']:
 if c['exit']!=0 or sha(ROOT/c['log'])!=c['sha256']:raise RuntimeError('producer command/log mismatch')
 bindings[c['log']]=c['sha256']
contract=ROOT/'verification/ui-measured-appearance-v2-contract'
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('contract',contract/'scripts/check-contract.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
for p in [contract/'scripts/check-contract.py',contract/'descriptor-schema.json',contract/'shape-definitions.json',contract/'mixer-measured-default-v2.json',HERE/'review.py',HERE/'Consumer.swift',SOURCE/'receipt.json']:
 bindings[str(p.relative_to(ROOT))]=sha(p)
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
cases=[];names=set()
def add(name,data):
 if not isinstance(data,bytes):data=canonical(data)
 if name in names:raise RuntimeError('duplicate case')
 names.add(name)
 try:model.read(data);expected='accept'
 except (ValueError,RecursionError):expected='reject'
 cases.append((name,data,expected))
def changed(root,path,value):
 d=copy.deepcopy(root);node=d
 for p in path[:-1]:node=node[p]
 node[path[-1]]=value
 return d
base=json.loads((contract/'mixer-measured-default-v2.json').read_text());add('default',base)
paths=[]
def walk(value,path=()):
 paths.append((path,value))
 if type(value) is dict:
  for k,v in value.items():walk(v,path+(k,))
 elif type(value) is list:
  for i,v in enumerate(value):walk(v,path+(i,))
walk(base)
for index,(path,value) in enumerate(paths):
 if type(value) is dict:
  d=copy.deepcopy(value);d['unrecognized']=0;add(f'object-extra-{index}',changed(base,path,d) if path else d)
  for key in value:
   d=copy.deepcopy(value);del d[key];add(f'object-missing-{index}-{key}',changed(base,path,d) if path else d)
  if path:add(f'object-wrong-{index}',changed(base,path,[]))
 elif type(value) is int:
  for n in [0,1,63,64,16384,65536,65537,2147483647,4294967295,18446744073709551616,-1]:
   add(f'int-{index}-{n}',changed(base,path,n))
  add(f'int-bool-{index}',changed(base,path,True))
 elif type(value) is str:
  for j,text in enumerate(['',' ','unknown','x'*513,'é','\u0000']):add(f'string-{index}-{j}',changed(base,path,text))
  if value.startswith('#'):
   for j,text in enumerate(['#11223344','#A0B1C2D3','#00000000','#FFFFFFFF','#abcdefFF']):add(f'color-{index}-{j}',changed(base,path,text))
platform={'format':base['format'],'id':'platform.choice','mode':'platformSpecific','resources':[],'iOS':base['theme'],'android':copy.deepcopy(base['theme']),'reason':'Explicit app design'}
platform['android']['light']['canvas']='#123456FF';add('platform',platform)
for reason in ['',' ',' leading','trailing ','two  spaces','quote" and slash\\','x'*513]:
 d=copy.deepcopy(platform);d['reason']=reason;add('platform-reason-'+str(len(names)),d)
resource={'id':'font','kind':'fontSFNT','path':'assets/type.ttf','sha256':'a'*64,'bytes':1,'provenance':'Synthetic metadata only','scale':1,'locale':'und','direction':'neutral'}
font=copy.deepcopy(base);font['resources']=[resource];font['theme']['typography']['font']={'kind':'bundled','fallback':'none','faces':[{'resourceID':'font','postScriptName':'Synthetic-'+str(w),'weight':w,'style':'normal'} for w in [400,600,700]]};add('bundled',font)
for key,values in {'path':['../x','x/../y','.hidden/x','x//y','x/','/x','x.y/z-_.t','X.Y/Z.ttf'],'bytes':[0,4194304,4194305],'scale':[0,1,2],'locale':['und','en','en-US'],'direction':['neutral','leftToRight','rightToLeft'],'sha256':['a'*64,'A'*64,'a'*63],'provenance':['',' ',' leading','good','quoted"slash\\']}.items():
 for i,v in enumerate(values):add(f'font-resource-{key}-{i}',changed(font,('resources',0,key),v))
for n in [0,1,2,3,16,17]:
 d=copy.deepcopy(font);d['theme']['typography']['font']['faces']=d['theme']['typography']['font']['faces'][:n] if n<=3 else d['theme']['typography']['font']['faces']*6
 add('font-face-count-'+str(n),d)
for i in range(3):
 d=copy.deepcopy(font);d['theme']['typography']['font']['faces'][i]['style']='italic';add('font-missing-normal-'+str(i),d)
wire=canonical(base)
for name,data in [('noLF',wire[:-1]),('twoLF',wire+b'\n'),('space',b' '+wire),('trailing',wire+b'0'),('bom',b'\xef\xbb\xbf'+wire),('v1',(ROOT/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json').read_bytes()),('duplicate',wire.replace(b'{',b'{"id":"shadow",',1)),('overflow',wire.replace(b'1088',b'18446744073709551616',1)),('exponent',wire.replace(b'1088',b'1e3',1)),('negative',wire.replace(b'1088',b'-1',1)),('nul',wire+b'\0'),('invalidUTF8',b'\xff'),('depth',b'['*21+b'0'+b']'*21+b'\n'),('array65',canonical([0]*65))]:add(name,data)
manifest=[{'name':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'expected':expected} for name,data,expected in cases]
(HERE/'corpus-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
payload=b''.join(base64.b64encode(data)+b'\n' for _,data,_ in cases)
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
def run(name,argv,input=None):
 argv=[str(x) for x in argv];p=subprocess.run(argv,cwd=SNAP,env=env,input=input,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
 log=HERE/(name+'.log');log.write_bytes(p.stdout);commands.append({'name':name,'argv':argv,'cwd':str(SNAP),'exit':p.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
 print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stdout.decode()[-3000:])
 return p.stdout.decode()
try:
 run('swift-version',['swiftc','--version'])
 for mode,opt in [('debug','-Onone'),('release','-O')]:
  folder=BUILD/mode;folder.mkdir()
  flags=['-swift-version','6','-warnings-as-errors',opt,'-module-cache-path',folder/'cache','-I',folder]
  for module in ['MixerCore','MixerUI']:
   run(mode+'-'+module,['swiftc',*flags,'-parse-as-library','-emit-module','-emit-library','-module-name',module,'-emit-module-path',folder/(module+'.swiftmodule'),'-o',folder/('lib'+module+'.dylib'),'-L',folder,*(['-lMixerCore'] if module=='MixerUI' else []),'-Xlinker','-rpath','-Xlinker',folder,*sorted((SNAP/'sdk/Sources'/module).glob('*.swift'))])
  exe=folder/'consumer';run(mode+'-compile',['swiftc',*flags,HERE/'Consumer.swift','-L',folder,'-lMixerUI','-lMixerCore','-Xlinker','-rpath','-Xlinker',folder,'-o',exe])
  answers=run(mode+'-corpus',[exe],payload).splitlines()
  if len(answers)!=len(cases):raise RuntimeError('output count mismatch')
  mismatches=[{'name':name,'expected':expected,'actual':actual} for (name,_,expected),actual in zip(cases,answers) if expected!=actual]
  if mismatches:
   (HERE/(mode+'-mismatches.json')).write_text(json.dumps(mismatches,indent=2)+'\n');raise RuntimeError(str(mismatches[:12]))
  counts[mode]={'total':len(cases),'accept':answers.count('accept'),'reject':answers.count('reject')}
 for p,h in bindings.items():
  if sha(ROOT/p)!=h:raise RuntimeError('binding changed '+p)
 status='accepted-v2-descriptor-data'
finally:
 bindings[str((HERE/'corpus-manifest.json').relative_to(ROOT))]=sha(HERE/'corpus-manifest.json')
 out={'status':status,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':r['sourceRevision'],'reviewer':'root','bindings':bindings,'commands':commands,'corpus':counts,'scope':'Independent frozen-schema admissibility oracle and exact canonical roundtrip through separately compiled actual Swift V2 codec; producer full106 SDK tests/profile and public/mobile module inputs audited. No resource/native/default renderer/signed/physical/GA authority.'}
 (HERE/'acceptance.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print('PASS',counts)
