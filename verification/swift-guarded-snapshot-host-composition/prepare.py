"""Exact frozen source union; no compiler or product dispatch on import."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
BASE = V / 'swift-guarded-snapshot-funding-implementation'
COMBINED = V / 'swift-guarded-snapshot-combined-source'
ACCOUNT_PACKET = V / 'swift-guarded-snapshot-host-account-entry'
BOOT = V / 'swift-guarded-snapshot-bootstrap-host-boundary'
SUPPORT = V / 'swift-real-profile-loader-binding'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
CONTROL = 'src/experimental_swift_reactor/control.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
HELPER = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
COMPILE_KEYS = ['MIXER_LOADER_MANIFEST_SHA256', 'MIXER_LOADER_COMMAND_SHA256',
 'MIXER_LOADER_COMPILE_ENV_SHA256', 'MIXER_LOADER_COMPILER_SHA256',
 'MIXER_LOADER_COMPILER_VERSION_SHA256']

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def row(name, data): return dict(path=name, bytes=len(data), sha256=sha(data))
def roster(source):
    rows = [row(name, source[name]) for name in sorted(source, key=Path)]
    return dict(schema=1, members=rows, member_count=len(rows), tree_sha256=sha(canonical(rows)))
def write(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def checked_json(path, expected):
    data = path.read_bytes()
    assert sha(data) == expected, path
    return json.loads(data)
def seal(folder, expected):
    value = checked_json(folder / 'seal.json', expected)
    members = value['members']
    assert len(members) == value['member_count']
    for item in members:
        assert row(item['path'], (folder/item['path']).read_bytes()) == item, (folder, item['path'])
    return dict(path=str(folder.relative_to(ROOT)), seal_sha256=expected,
        verified_members=len(members), verified_bytes=sum(item['bytes'] for item in members))
def load_manifest(folder, expected):
    value = json.loads((folder/'source-manifest.json').read_bytes())
    assert sha(canonical(value['members'])) == expected
    return value['members']

def compose():
    releases=[]
    for name, digest in [
      ('guarded-snapshot-host-composition-next-source-release.json','2f112a66bb382c7bce38866ac993acf95be01a939cf0d863cf9b98c60e3597ad'),
      ('guarded-snapshot-host-account-host-acceptance.json','8bb780193f9039174b7f1dd503f6572f8cca9bf6ec01f81722ed3f25aa9d927a'),
      ('guarded-snapshot-combined-host-acceptance.json','f522358c5c3f474b2c10f23c7710e4296d9e287001eae09a50eeb591ba3f68b2')]:
        path=V/'swift-semantic-adapter-root-review'/name
        accepted=checked_json(path,digest)
        releases.append(dict(path=str(path.relative_to(ROOT)),sha256=digest,status=accepted['status']))
    custody=[seal(COMBINED,'2eb3dab82f2b492b491e9f80e1d05fb0f8745e41c452f4f3bc777a33b62e8bdc'),
             seal(ACCOUNT_PACKET,'6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3'),
             seal(BOOT,'00f5bf754a13317ac18dd9959a1db4a9b025b16c72fc99a9d4cfddfcc7cb4dba')]
    checked_json(BASE/'seal.json','e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7')
    base_rows=load_manifest(BASE,'7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b')
    base={item['path']:(BASE/'source/vm'/item['path']).read_bytes() for item in base_rows}
    assert roster(base)['members']==base_rows and len(base)==144
    combined=dict(base)
    for item in load_manifest(COMBINED,'270cf2c4b2e72452470d2b6cacea9f87d3c02bd0ab5916ea7b579614a799892a'):
        if base.get(item['path']) is None or row(item['path'],base[item['path']])!=item:
            combined[item['path']]=(COMBINED/'overlay/vm'/item['path']).read_bytes()
    assert roster(combined)['members']==load_manifest(COMBINED,'270cf2c4b2e72452470d2b6cacea9f87d3c02bd0ab5916ea7b579614a799892a')
    bootstrap=(BOOT/'driver.inc.rs').read_bytes()
    entry=(ACCOUNT_PACKET/'entry.inc.rs').read_bytes()
    account=(ACCOUNT_PACKET/'host_account.rs').read_bytes()
    distinct=dict(base)
    distinct[PROFILE]+=b'\n\n'+bootstrap+b'\n\n'+entry
    distinct[ACCOUNT]=account
    assert roster(distinct)['members']==load_manifest(ACCOUNT_PACKET,'5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b')
    exact=dict(combined)
    assert ACCOUNT not in exact and HELPER not in distinct
    exact[ACCOUNT]=account
    exact[PROFILE]+=b'\n\n'+bootstrap+b'\n\n'+entry
    expected_count=len(set(combined)|set(distinct))
    assert expected_count==146 and len(exact)==expected_count
    before=b'if word(b, 32) != '+str(len(combined)).encode()+b'\n'
    after=b'if word(b, 32) != '+str(expected_count).encode()+b'\n'
    assert exact[LOADER].count(before)==1
    exact[LOADER]=exact[LOADER].replace(before,after,1)
    assert exact[CONTROL]==combined[CONTROL]
    assert exact[PROFILE]==combined[PROFILE]+b'\n\n'+bootstrap+b'\n\n'+entry
    assert exact[ACCOUNT]==account and exact[HELPER]==combined[HELPER]
    assert exact[LOADER].replace(after,before,1)==combined[LOADER]
    assert sum(data.count(b'checked_snapshot_emission_bound_v1') for name,data in exact.items() if name!=HELPER)==0
    assert b'Err(AError::WorkAuditPending)' in exact[PROFILE]
    assert b'Err(RefusalV1::WholeQuotePending)' in account
    assert b'Err(RefusalV1::RootPolicyPending)' in account
    hosts=json.loads((COMBINED/'host-support-manifest.json').read_bytes())
    host={item['path']:(SUPPORT/'host'/item['path']).read_bytes() for item in hosts['members']}
    assert roster(host)==hosts
    assert hosts['member_count']==11 and hosts['tree_sha256']=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
    custody.append(dict(path=str(BASE.relative_to(ROOT)),source_members_verified=144,
        source_bytes_verified=sum(item['bytes'] for item in base_rows),
        source_tree_sha256=roster(base)['tree_sha256'],full_packet_reverified=False))
    controls=dict(schema=1,source_members=expected_count,
        source_tree_sha256=roster(exact)['tree_sha256'],
        union_derivation=dict(base=144,combined_addition=[HELPER],account_addition=[ACCOUNT],union=expected_count),
        combined_control_byte_identical=True,leaf_account_entry_byte_identical=True,
        profile_only_coordinated_appends=True,loader_only_derived_count_literal=True,
        loader_before_count=len(combined),loader_after_count=expected_count,
        WorkAuditPending_preserved=True,root_policy_and_whole_quote_pending=True,
        helper_undispatched=True,selected_execution_work=451814442,
        selected_unit_construction=1469366,admitted_unit_construction=1899541,
        phase_A=430175,C=79676,S=941467,H=81327,
        no_healthy_cleanup_or_whole_quote_or_operational_authority=True)
    return base,exact,host,dict(schema=1,inputs=custody,releases=releases),controls

def checked_candidate():
    base,source,hosts,custody,controls=compose()
    assert roster(source)==json.loads((HERE/'source-manifest.json').read_bytes())
    assert roster(hosts)==json.loads((HERE/'host-support-manifest.json').read_bytes())
    for name in source:
        if source[name]!=base.get(name):
            assert (HERE/'overlay/vm'/name).read_bytes()==source[name]
    return source,hosts

def main():
    assert not (HERE/'seal.json').exists()
    base,source,host,custody,controls=compose()
    for name,data in source.items():
        if data!=base.get(name):
            path=HERE/'overlay/vm'/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
    write('source-manifest.json',roster(source))
    write('host-support-manifest.json',roster(host))
    write('input-bindings.json',custody)
    write('source-controls.json',controls)
    delta=''
    for name in sorted(source,key=Path):
        if source[name]!=combined_data(base,name):
            delta+=''.join(difflib.unified_diff(combined_data(base,name).decode().splitlines(True),source[name].decode().splitlines(True),fromfile='accepted-combined145/'+name,tofile='host-composition146/'+name))
    (HERE/'combined145-to-composed146.patch').write_text(delta)
    print(json.dumps({k:controls[k] for k in ['source_members','source_tree_sha256','loader_after_count']}))

def combined_data(base,name):
    overlay=COMBINED/'overlay/vm'/name
    return overlay.read_bytes() if overlay.exists() else base.get(name,b'')

if __name__=='__main__': main()
