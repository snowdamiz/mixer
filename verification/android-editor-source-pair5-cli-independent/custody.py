#!/usr/bin/env python3
"""Independent closed custody, fixed selected provenance, and promotion-set audit."""
import hashlib,json,pathlib,stat,subprocess,sys,datetime
R=pathlib.Path(__file__).resolve().parents[2]
P=R/'verification/android-editor-source-pair5-cli-integration'
O=pathlib.Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
def dump(n,x):(O/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
errors=[]
def check(x,m):
 if not x: errors.append(m)
def closed(p,expected):
 b=(p/'seal.json').read_bytes();check(H(b)==expected,str(p)+' seal identity')
 s=json.loads(b);rows=s['members'];paths=[x['path'] for x in rows]
 check(len(paths)==len(set(paths)),'duplicate members')
 observed=[];total=0
 for f in p.rglob('*'):
  k=f.relative_to(p).as_posix();st=f.lstat()
  if stat.S_ISDIR(st.st_mode):continue
  check(stat.S_ISREG(st.st_mode),'nonordinary '+k)
  if k!='seal.json':observed.append(k)
 check(set(observed)==set(paths),'closed membership '+str(set(observed)^set(paths)))
 for e in rows:
  f=p/e['path'];st=f.lstat();check(stat.S_ISREG(st.st_mode),'type '+e['path'])
  b=f.read_bytes();total+=len(b);check(len(b)==e['bytes'] and H(b)==e['sha256'],'identity '+e['path'])
 check(s['member_count']==len(rows) and s['member_bytes']==total,'seal totals')
 return {'seal_sha256':H((p/'seal.json').read_bytes()),'members':len(rows),'bytes':total}
cp=closed(P,'87cd2e4e14d0c444d308397dbd59dbe271419261f5d7fa2cd7201af35db18ecf')
rp=closed(R/'verification/android-editor-source-pair5-rebinding','088b6dd59bbfd91cd93e7c4cbb16ca1285018b0f6eb6045932b348f7beaf8864')
m=json.loads((P/'source-manifest.json').read_text())['members'];projection=H(''.join(e['path'].removeprefix('source/')+'\0'+e['sha256']+'\n' for e in sorted(m,key=lambda x:x['path'])).encode())
check(projection=='6ba31109183443ab62ef8ae9e36ae3e968ec3da383c67c4cc93aa6a2a9a5131a','source projection')
for e in m:
 f=P/e['path'];check(f.stat().st_size==e['bytes'] and H(f.read_bytes())==e['sha256'],'source '+e['path'])
inputs=json.loads((P/'inputs.json').read_text())['inputs'];initial={e['target']:e for e in inputs};final={e['path']:e for e in m};changed=[]
for k,v in final.items():
 check(k in initial,'source missing provenance '+k)
 if k in initial and v['sha256']!=initial[k]['sha256']:changed.append(k)
selected=json.loads((P/'promotion-targets.json').read_text())['changed']
check(set(changed)=={e['candidate'] for e in selected},'exact five changes')
for e in selected:
 check(H((R/e['canonical_target']).read_bytes())==e['original_sha256'],'canonical drift '+e['canonical_target'])
 check(final[e['candidate']]['sha256']==e['candidate_sha256'],'candidate identity '+e['candidate'])
profile=json.loads((P/'inputs/profile5.json').read_text())
for kind,root in [('sdk',P/'source/sdk'),('adapter',P/'source/native/android')]:
 files=profile[kind+'_files'];check(len(files)==(22 if kind=='sdk' else 24),'map count')
 d=H(''.join(k+'\0'+v['sha256']+'\n' for k,v in sorted(files.items())).encode());check(d==profile[kind+'_compatibility_sha256'],'map projection '+kind)
 for k,v in files.items():
  f=root/('engine/'+k if kind=='adapter' and k.startswith('Sources/') else k)
  check(f.stat().st_size==v['bytes'] and H(f.read_bytes())==v['sha256'],'selected map '+k)
check(profile['default_descriptor']=={'bytes':9587,'sha256':'1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'},'descriptor')
dump('custody.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'python':sys.version,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'candidate':cp,'rebinding':rp,'source_projection':projection,'source_members':len(m),'changed':changed,'errors':errors,'passed':not errors,'scope':'Content hashing only for closed custody; no hosted harness read as source, imported or executed.'})
print(json.dumps({'passed':not errors,'candidate':cp,'rebinding':rp,'source_projection':projection,'changed':len(changed),'errors':errors},indent=2));sys.exit(bool(errors))
