"""Independent review support. Standard library only; no product execution."""
from pathlib import Path
import hashlib, json, os, stat, sys
sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
V = R/'verification'
C = V/'swift-guarded-snapshot-string-provider-source-rebind'
RELEASE = V/'swift-semantic-adapter-root-review/guarded-snapshot-string-provider-source-rebind-frozen-release.json'
SEAL = '3782b36c05e5ef0d4037cdac26834b31f3db1978250ba25abd2a869e4c5b90ab'
RELEASE_SHA = '19a3314e3ec55fc348d13c1e4ddd165b7e0cc3709bd031eb5f46f6577ea80b0e'
TREES = ['690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3','69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7','acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d']
MIRS = ['swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz','swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/query.mir.gz','swift-guarded-snapshot-scoped-binding-source/commands/compiler-positive/query.mir.gz','swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout/query.mir.gz']
PROFILE='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT='src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def read(p): return json.loads(p.read_bytes())
def require(ok,why):
    if not ok: raise AssertionError(why)
def row(p,b): return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def save(name,x): (D/name).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def custody():
    require(sha((C/'seal.json').read_bytes())==SEAL,'candidate seal pin')
    require(sha(RELEASE.read_bytes())==RELEASE_SHA,'root custody release pin')
    seal=read(C/'seal.json'); files={}; members=[]
    for p in sorted(C.rglob('*')):
        require(not p.is_symlink(),'candidate symlink')
        if p.is_file():
            require(stat.S_IMODE(p.stat().st_mode)==0o444,'candidate file write mode')
            b=p.read_bytes();files[str(p.relative_to(R))]=row(p.relative_to(R),b)
            if p.name!='seal.json':members.append(row(p.relative_to(C),b))
        else:require(stat.S_IMODE(p.stat().st_mode)==0o555,'candidate directory write mode')
    require(stat.S_IMODE(C.stat().st_mode)==0o555,'candidate root write mode')
    require(members==seal['members'] and len(members)==657 and sum(x['bytes'] for x in members)==128097360,'complete candidate membership')
    require(sha(canon(members))==seal['member_table_sha256'],'candidate member digest')
    for x in read(C/'input-custody.json')['members']:
        p=R/x['path'];require(not p.is_symlink(),'transitive input symlink')
        b=p.read_bytes();require(row(x['path'],b)==x,'transitive frozen input '+x['path']);files[x['path']]=x
    files[str(RELEASE.relative_to(R))]=row(RELEASE.relative_to(R),RELEASE.read_bytes())
    return {'schema':1,'candidate_seal_sha256':SEAL,'release_sha256':RELEASE_SHA,'members':[files[k] for k in sorted(files)],'member_table_sha256':sha(canon([files[k] for k in sorted(files)]))}
