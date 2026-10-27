"""Prepare only exact frozen source145/host11 overlays; no compiler/runtime dispatch."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FUNDING = ROOT / 'verification/swift-guarded-snapshot-funding-implementation'
EMISSION = ROOT / 'verification/swift-guarded-snapshot-emission-bound-implementation'
LOADER = ROOT / 'verification/swift-real-profile-loader-binding'
LOADER_PATH = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
PHASE_PATH = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
HELPER_PATH = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
KEYS = ['MIXER_LOADER_MANIFEST_SHA256', 'MIXER_LOADER_COMMAND_SHA256',
        'MIXER_LOADER_COMPILE_ENV_SHA256', 'MIXER_LOADER_COMPILER_SHA256',
        'MIXER_LOADER_COMPILER_VERSION_SHA256']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}

def roster(paths):
    members = [{'path': name, 'bytes': len(data), 'sha256': sha(data)}
               for name, data in sorted(paths.items(), key=lambda item: Path(item[0]))]
    return {'schema': 1, 'member_count': len(members), 'members': members,
            'tree_sha256': sha(canonical(members))}

def sealed(path, expected, selected=None):
    raw = (path / 'seal.json').read_bytes()
    assert sha(raw) == expected, path
    seal = json.loads(raw)
    members = {m['path']: m for m in seal['members']}
    assert len(members) == seal['member_count']
    names = sorted(members if selected is None else selected)
    for name in names:
        actual = identity(path / name)
        assert all(actual[k] == members[name][k] for k in ['bytes', 'sha256']), name
    return {'path': str(path.relative_to(ROOT)), 'seal_sha256': expected,
            'sealed_members': seal['member_count'], 'verified_members': names,
            'whole_packet_verified': selected is None}

def inputs():
    custody = []
    custody.append(sealed(FUNDING, 'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'))
    custody.append(sealed(EMISSION, 'e92026187ef181ddbcc178e53611ce5e4aa0111c613e9c8ad3a4aca58ff8ffcc'))
    support = json.loads((LOADER / 'baseline-host-support-manifest.json').read_bytes())
    support_paths = [m['retained_path'] for m in support['members']]
    custody.append(sealed(LOADER, 'e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2',
                          support_paths + ['baseline-host-support-manifest.json', 'CONTRACT.md', 'run_checks.py']))
    source = {str(p.relative_to(FUNDING / 'source/vm')): p.read_bytes()
              for p in (FUNDING / 'source/vm').rglob('*') if p.is_file()}
    prior = json.loads((FUNDING / 'source-manifest.json').read_bytes())
    measured = roster(source)
    assert measured['member_count'] == 144
    assert measured['members'] == prior['members']
    assert measured['tree_sha256'] == prior['source_tree_sha256'] == '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
    hosts = {m['retained_path'][5:]: (LOADER / m['retained_path']).read_bytes() for m in support['members']}
    assert len(hosts) == 11
    for m in support['members']:
        data = hosts[m['retained_path'][5:]]
        assert len(data) == m['bytes'] and sha(data) == m['sha256']
    return source, hosts, custody

def compose(source):
    source = dict(source)
    old = b'if word(b, 32) != 144\n'
    assert source[LOADER_PATH].count(old) == 1
    source[LOADER_PATH] = source[LOADER_PATH].replace(old, b'if word(b, 32) != 145\n')
    marker = b'fn proposed_emission_work_v1('
    assert source[PHASE_PATH].count(marker) == 1
    source[PHASE_PATH] = source[PHASE_PATH].replace(marker,
        b'// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n' + marker)
    helper = (EMISSION / 'overlay/vm' / HELPER_PATH).read_bytes()
    assert sha(helper) == 'ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a'
    assert HELPER_PATH not in source
    source[HELPER_PATH] = helper
    assert len(source) == 145
    return source

def checked_candidate():
    base, hosts, custody = inputs()
    source = compose(base)
    assert roster(source) == json.loads((HERE / 'source-manifest.json').read_bytes())
    assert roster(hosts) == json.loads((HERE / 'host-support-manifest.json').read_bytes())
    for name in [LOADER_PATH, PHASE_PATH, HELPER_PATH]:
        assert (HERE / 'overlay/vm' / name).read_bytes() == source[name]
    assert source[LOADER_PATH].replace(b'if word(b, 32) != 145\n', b'if word(b, 32) != 144\n') == base[LOADER_PATH]
    assert source[PHASE_PATH].replace(b'// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n', b'') == base[PHASE_PATH]
    return source, hosts, custody

def materialize(destination):
    source, hosts, custody = checked_candidate()
    assert not destination.exists()
    for name, data in source.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return source, hosts, custody

def main():
    assert not (HERE / 'seal.json').exists(), 'Never mutate a frozen packet'
    base, hosts, custody = inputs()
    source = compose(base)
    for name in [LOADER_PATH, PHASE_PATH, HELPER_PATH]:
        path = HERE / 'overlay/vm' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source[name])
    write(HERE / 'source-manifest.json', roster(source))
    write(HERE / 'host-support-manifest.json', roster(hosts))
    write(HERE / 'input-custody.json', {'schema': 1, 'inputs': custody,
        'baseline_tree_sha256': roster(base)['tree_sha256'],
        'candidate_tree_sha256': roster(source)['tree_sha256'],
        'host_support_tree_sha256': roster(hosts)['tree_sha256'],
        'host_support_members': 11, 'orchestration_is_not_host_support': True})
    delta = ''.join(''.join(difflib.unified_diff(base.get(name, b'').decode().splitlines(True),
        source[name].decode().splitlines(True), fromfile='funding-source144/' + name,
        tofile='descriptor-source145/' + name)) for name in [LOADER_PATH, PHASE_PATH, HELPER_PATH])
    (HERE / 'source-delta.patch').write_text(delta)
    write(HERE / 'proposal.json', {'schema': 1, 'ownership': str(HERE.relative_to(ROOT)),
        'changed_or_added_product_paths': [LOADER_PATH, PHASE_PATH, HELPER_PATH],
        'loader_change': 'Literal distribution count 144 -> 145 only; host11 unchanged',
        'support': 'Exact unchanged eleven frozen loader support members; runner/tools/SDK are separate orchestration',
        'compile_keys': KEYS,
        'identity_contract': 'Manifest, counted argv, counted clean environment, compiler executable, compiler version SHA256 independently injected through existing option_env keys',
        'phase_retention_change': False, 'helper_delegation': False,
        'engine_VM_writer_dispatch': False, 'WorkAuditPending_preserved': True,
        'root_proposal_delivered_before_compiler': True})
    print(json.dumps({'prepared': True, 'source': roster(source)['tree_sha256'],
                      'members': 145, 'support': roster(hosts)['tree_sha256'], 'support_members': 11}))

if __name__ == '__main__':
    main()
