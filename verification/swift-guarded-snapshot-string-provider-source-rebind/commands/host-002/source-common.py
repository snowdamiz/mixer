"""Owned, offline source/MIR rebind utilities. No compiler or runtime entry."""
from pathlib import Path
import collections, gzip, hashlib, importlib.util, json, re, sys
sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
OLD = V / 'swift-guarded-snapshot-string-exact-binding-correction'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
TREES = ['690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
 '27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3',
 '69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7',
 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d']
PINS = {
 'swift-guarded-snapshot-string-exact-binding-correction': '4eb0437b5ed1f7ec056340ffac08a0221cfd5f6f216a9d3aebb6fd4d25cc5f4b',
 'swift-guarded-snapshot-string-exact-binding-independent': '5cc1e09727426ae84ef0c078c7a20153886d72495a1b4949ee31f69e6a37c956',
 'swift-guarded-snapshot-scoped-binding-source': '84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2',
 'swift-guarded-snapshot-scoped-binding-independent': 'e11d9eff0eda83ccf46563526e3c7025172cc8e05513b4a9ba1a5a0d9c13344a',
 'swift-guarded-snapshot-owned-provider-work-storage': '28ba8099ce8b57f91cd46baac21f130986000ecbbf7df07b16e6bf061fc342d1',
 'swift-guarded-snapshot-owned-provider-work-storage-independent': 'aeb00877856dacca762ba9c885d043ed4b785cabe811e8f31251eaa55e4ada6b',
}
ROOT_PINS = {
 'guarded-snapshot-string-exact-binding-host-acceptance.json':'273dcc49104e828609298ca30f5a19b0162ba56092b49e1fdb46375a1f3b003d',
 'guarded-snapshot-scoped-binding-source-host-acceptance.json':'1bc55306a1f6cf220660efa8ab9e34485d610ae806ebd56a1733d892ddfcd2e1',
 'guarded-snapshot-owned-binding-provider-host-acceptance.json':'998a7f6de2918e6b643360b4e67475fdc9a468d69792eb5cda3bb773272fcba3',
 'guarded-snapshot-owned-provider-work-storage-host-acceptance.json':'64f53d4ee70bb98b7684bc3dcf1f53b5e5b86c34c1a82a2930d362cdcc9d647a',
}
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def row(path,b): return {'path':str(path),'bytes':len(b),'sha256':sha(b)}
def load(p): return json.loads(p.read_bytes())
def require(ok,label):
 if not ok: raise ValueError(label)
def module(p,name):
 spec=importlib.util.spec_from_file_location(name,p);mod=importlib.util.module_from_spec(spec)
 sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
def accepted_modules():
 # Import read-only analytical functions, never frozen preparation/compile runners.
 sys.path.insert(0,str(OLD))
 m=module(OLD/'mir_graph.py','mir_graph');t=module(OLD/'type_contracts.py','type_contracts')
 s=module(V/'swift-guarded-snapshot-scoped-binding-independent/audit.py','scoped_audit')
 return m,t,s
def source_tables():
 ref=load(V/'swift-guarded-snapshot-loader-work-source146/source-reference-map.json')['members']
 a={x['path']:(R/x['source']).read_bytes() for x in ref}
 out=load(V/'swift-guarded-snapshot-outer-parent-source/source-custody.json')
 b={x['path']:(R/x['origin']).read_bytes() for x in out}
 manifest=load(V/'swift-guarded-snapshot-scoped-binding-source/source-manifest.json')
 c={x['path']:(V/'swift-guarded-snapshot-scoped-binding-source/source/vm'/x['path']).read_bytes() for x in manifest['members']}
 ref=load(V/'swift-guarded-snapshot-owned-binding-provider/proposed-source-custody.json')
 d={x['path']:(R/x['origin']).read_bytes() for x in ref}
 for table,tree in zip((a,b,c,d),TREES):
  members=[row(n,table[n]) for n in sorted(table,key=Path)]
  require(len(members)==146 and sha(canon(members))==tree,'source146 lineage tree:'+tree)
 return a,b,c,d
MIRS = [
 'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz',
 'swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/query.mir.gz',
 'swift-guarded-snapshot-scoped-binding-source/commands/compiler-positive/query.mir.gz',
 'swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout/query.mir.gz']
def mir_texts(): return [gzip.decompress((V/p).read_bytes()).decode() for p in MIRS]
def custody():
 files={};seals=[]
 def add(p):
  b=p.read_bytes();files[str(p.relative_to(R))]=row(p.relative_to(R),b);return b
 for name,digest in PINS.items():
  folder=V/name;raw=add(folder/'seal.json');require(sha(raw)==digest,'input seal:'+name)
  seal=json.loads(raw);actual=[]
  for p in sorted(folder.rglob('*')):
   require(not p.is_symlink(),'input symlink:'+str(p))
   if p.is_file() and p.name!='seal.json':actual.append(row(p.relative_to(folder),add(p)))
  require(actual==seal['members'],'complete sealed membership:'+name)
  seals.append({'path':str(folder.relative_to(R)),'sha256':digest,'members':len(actual),'bytes':sum(x['bytes'] for x in actual)})
 for name,digest in ROOT_PINS.items():require(sha(add(V/'swift-semantic-adapter-root-review'/name))==digest,'root acceptance:'+name)
 # Upstream packets and source origins are immutable inputs even where a prior
 # accepted seal already recursively bound them. Exact membership is pinned below.
 for folder in ('swift-guarded-snapshot-outer-parent-source','swift-guarded-snapshot-outer-parent-independent','swift-guarded-snapshot-owned-binding-provider','swift-guarded-snapshot-owned-provider-independent'):
  seal=load(V/folder/'seal.json');add(V/folder/'seal.json')
  for x in seal['members']:require(row(x['path'],add(V/folder/x['path']))==x,'lineage sealed member:'+folder+'/'+x['path'])
 for path in MIRS:add(V/path)
 for path,key,field in [
 ('swift-guarded-snapshot-loader-work-source146/source-reference-map.json','members','source'),
 ('swift-guarded-snapshot-outer-parent-source/source-custody.json',None,'origin'),
 ('swift-guarded-snapshot-owned-binding-provider/proposed-source-custody.json',None,'origin')]:
  data=json.loads(add(V/path));data=data[key] if key else data
  for x in data:require(row(x['path'],add(R/x[field]))=={k:x[k] for k in ('path','bytes','sha256')},'source origin:'+x['path'])
 for x in load(V/'swift-guarded-snapshot-scoped-binding-source/source-manifest.json')['members']:add(V/'swift-guarded-snapshot-scoped-binding-source/source/vm'/x['path'])
 for name in ('source146-manifest.json','compiler-receipt.json','host11-manifest.json'):add(V/'swift-guarded-snapshot-loader-work-source146'/name)
 host=load(V/'swift-guarded-snapshot-loader-work-source146/host11-manifest.json')
 require(sha(canon(host['members']))=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2','host11 identity')
 for x in host['members']:require(row(x['path'],add(V/'swift-real-profile-loader-binding/host'/x['path']))==x,'host11 member')
 return {'schema':1,'packets':seals,'members':[files[k] for k in sorted(files)],'member_table_sha256':sha(canon([files[k] for k in sorted(files)]))}
def save(name,value,check=False):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 if check:require((D/name).read_bytes()==raw,'rederived artifact:'+name)
 else:(D/name).write_bytes(raw)
