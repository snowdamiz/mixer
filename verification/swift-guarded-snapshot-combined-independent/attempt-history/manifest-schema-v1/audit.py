"""Independent read-only reconciliation of the frozen combined packet."""
from pathlib import Path
import difflib
import hashlib
import itertools
import json
import os
import struct
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V = ROOT / 'verification'
P = V / 'swift-guarded-snapshot-combined-source'
BASE = V / 'swift-guarded-snapshot-funding-implementation'
COMMON = V / 'swift-guarded-snapshot-work-common-correction'
PHASE = V / 'swift-guarded-snapshot-phase-retention'
DESC = V / 'swift-guarded-snapshot-descriptor-rebinding'
REVIEW = V / 'swift-semantic-adapter-root-review'
CONTROL = 'src/experimental_swift_reactor/control.rs'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
HELPER = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
KEYS = ['MIXER_LOADER_MANIFEST_SHA256', 'MIXER_LOADER_COMMAND_SHA256',
        'MIXER_LOADER_COMPILE_ENV_SHA256', 'MIXER_LOADER_COMPILER_SHA256',
        'MIXER_LOADER_COMPILER_VERSION_SHA256']
TREE = '270cf2c4b2e72452470d2b6cacea9f87d3c02bd0ab5916ea7b579614a799892a'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'


def digest(b):
    return hashlib.sha256(b).hexdigest()


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':')).encode()


def read(p):
    return json.loads(p.read_bytes())


def write(name, value):
    p = HERE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def row(name, b):
    return dict(path=name, bytes=len(b), sha256=digest(b))


def roster(source):
    members = [row(n, source[n]) for n in sorted(source, key=Path)]
    return dict(schema=1, member_count=len(members), members=members,
                tree_sha256=digest(canon(members)))


def verify_seal(folder, expected, selected=None):
    seal_bytes = (folder / 'seal.json').read_bytes()
    assert digest(seal_bytes) == expected, folder
    seal = json.loads(seal_bytes)
    rows = seal['members']
    assert len(rows) == seal['member_count'] == len({r['path'] for r in rows})
    for field in ('manifest_sha256', 'tree_sha256'):
        if field in seal:
            assert seal[field] == digest(canon(rows))
    selected_rows = rows if selected is None else [r for r in rows if r['path'] in selected]
    assert selected is None or len(selected_rows) == len(selected)
    for r in selected_rows:
        path = folder / r['path']
        assert path.resolve().is_relative_to(folder.resolve()) and not path.is_symlink()
        assert row(r['path'], path.read_bytes()) == r, path
    return dict(path=str(folder.relative_to(ROOT)), seal_sha256=expected,
                verified_members=len(selected_rows), verified_bytes=sum(r['bytes'] for r in selected_rows),
                complete=selected is None)


def checked_sources():
    base_rows = read(BASE / 'source-manifest.json')
    base = {r['path']: (BASE / 'source/vm' / r['path']).read_bytes() for r in base_rows['members']}
    assert roster(base) == base_rows and len(base) == 144
    source = dict(base)
    for path in (CONTROL, PROFILE, LOADER, HELPER):
        source[path] = (P / 'overlay/vm' / path).read_bytes()
    assert roster(source) == read(P / 'source-manifest.json')
    assert roster(source)['tree_sha256'] == TREE and len(source) == 145
    host_rows = read(P / 'host-support-manifest.json')
    support = V / 'swift-real-profile-loader-binding'
    hosts = {r['path']: (support / 'host' / r['path']).read_bytes() for r in host_rows['members']}
    assert roster(hosts) == host_rows and len(hosts) == 11
    assert roster(hosts)['tree_sha256'] == HOST
    return base, source, hosts


def unpack(blob):
    assert len(blob) >= 8
    count = struct.unpack_from('<Q', blob)[0]
    values, offset = [], 8
    for _ in range(count):
        assert offset + 8 <= len(blob)
        size = struct.unpack_from('<Q', blob, offset)[0]
        offset += 8
        assert offset + size <= len(blob)
        values.append(blob[offset:offset+size])
        offset += size
    assert offset == len(blob)
    return values


def inspect():
    release = REVIEW / 'guarded-snapshot-combined-independent-release.json'
    assert digest(release.read_bytes()) == '6f27017ee31d9d4bc6b2866920313440d5f0fe88524dcf875e02a38e43478885'
    packets = [verify_seal(P, '2eb3dab82f2b492b491e9f80e1d05fb0f8745e41c452f4f3bc777a33b62e8bdc')]
    for folder, sha in [(BASE, 'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'),
                        (COMMON, 'c679b12e5a82c5cd6746f87d8615cb19c6cba00f1d72625cad334bb11adc1422'),
                        (PHASE, '623b5ec0b8ef7c2f68b344c191f9a6d2f5fd93b3085c7f0b4ae02c960c895001'),
                        (DESC, '5e11885ef1a1189dc10ef8de5b82f4cd969573a8a1130e0a25f146725c23d7ea')]:
        packets.append(verify_seal(folder, sha))
    base, source, hosts = checked_sources()
    packets.append(verify_seal(V / 'swift-real-profile-loader-binding',
        'e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2',
        {'host/' + p for p in hosts}))
    acceptances = []
    for name, expected in [('guarded-snapshot-work-admission-host-acceptance.json', 'c08376ad082af1b12fed92571d23f2544d52dad389096b62790a4073b7b3a8b3'),
                           ('guarded-snapshot-phase-retention-host-acceptance.json', '814e60d6dc9a9ee38039e86b1873bf65cd44bbe608dc37919ff39ee8eef84519'),
                           ('guarded-snapshot-descriptor-rebinding-host-acceptance.json', 'fafea2179a953a39535193197cc9dd7a82738d22203b8a598b2501fd47550ef6')]:
        raw = (REVIEW / name).read_bytes()
        assert digest(raw) == expected
        acceptances.append(dict(path=name, sha256=expected, status=json.loads(raw)['status']))
    common = dict(base)
    common[CONTROL] = (COMMON / 'overlay' / CONTROL).read_bytes()
    assert roster(common) == read(COMMON / 'source-manifest.json')
    phase = {r['path']: (PHASE / 'source/vm' / r['path']).read_bytes()
             for r in read(PHASE / 'source-manifest.json')['members']}
    assert roster(phase) == read(PHASE / 'source-manifest.json')
    descriptor = dict(base)
    for path in (PROFILE, LOADER, HELPER):
        descriptor[path] = (DESC / 'overlay/vm' / path).read_bytes()
    assert roster(descriptor) == read(DESC / 'source-manifest.json')
    components = dict(common=common, phase=phase, descriptor=descriptor)
    edits = {}
    for label, component in components.items():
        changes = []
        for name in sorted(component, key=Path):
            if name not in base:
                changes.append((name, None, component[name]))
                continue
            old_lines, new_lines = base[name].splitlines(True), component[name].splitlines(True)
            for tag, i, j, a, b in difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes():
                if tag != 'equal':
                    # Context-free changed spans must be unique in each composition.
                    old = b''.join(old_lines[i:j])
                    new = b''.join(new_lines[a:b])
                    if not old:
                        # Anchor additive descriptor declaration with its preceding line.
                        assert i > 0 and a > 0
                        old, new = old_lines[i-1], new_lines[a-1] + new
                    changes.append((name, old, new))
        edits[label] = changes
    order_results = []
    for order in itertools.permutations(components):
        result = dict(base)
        for label in order:
            for name, old, new in edits[label]:
                if old is None:
                    assert name not in result
                    result[name] = new
                else:
                    assert result[name].count(old) == 1, (order, name)
                    result[name] = result[name].replace(old, new, 1)
        assert result == source
        order_results.append(dict(order=order, tree_sha256=roster(result)['tree_sha256']))
    changed = [name for name in source if source[name] != base.get(name)]
    assert set(changed) == {CONTROL, PROFILE, LOADER, HELPER}
    assert sum(len(source[n]) for n in changed) == 180134
    loader = source[LOADER]
    assert loader.replace(b'if word(b, 32) != 145\n', b'if word(b, 32) != 144\n', 1) == base[LOADER]
    assert loader.count(b'if word(b, 32) != 145\n') == 1
    assert loader.count(b'|| word(b, 40) != 11\n') == 1
    for key in KEYS:
        assert loader.count(('option_env!("' + key + '")').encode()) == 1
    assert len(source[HELPER]) == 853
    assert sum(v.count(b'checked_snapshot_emission_bound_v1') for n, v in source.items() if n != HELPER) == 0
    assert source[PROFILE].count(b'return Err(AError::WorkAuditPending);') == 1
    overlay = read(P / 'test-overlay-manifest.json')
    tests = dict(source)
    for operation in overlay['append_operations']:
        name = operation['path']
        assert row(name, tests[name])['sha256'] == operation['base_sha256']
        assert len(tests[name]) == operation['base_bytes']
        part = Path(operation['append']['path'])
        assert part.parent == P and row(str(part), part.read_bytes()) == operation['append']
        tests[name] += part.read_bytes()
        assert row(name, tests[name]) == operation['resulting']
    assert roster(tests) == overlay['source']
    assert roster(tests)['tree_sha256'] == '07921fe0190c2539c15283499b72fd469798b877cf56f05e01788867bc192136'
    assert overlay['exact_product_source'] == roster(source)
    for name in ('profile-tests.inc.rs', 'cache-tests.inc.rs'):
        assert (P / name).read_bytes() == (PHASE / name).read_bytes()
    builds = []
    for label in ('metadata-production', 'metadata-unit', 'interactions-debug', 'interactions-optimized'):
        pre = P / 'preimages' / label
        manifest_bytes = (pre / 'manifest.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        binding = read(pre / 'binding.json')
        command = read(P / 'commands' / label / 'receipt.json')
        argv = (pre / 'argv.bin').read_bytes()
        environment = (pre / 'environment.bin').read_bytes()
        version = (pre / 'compiler-version.txt').read_bytes()
        assert manifest_bytes == canon(manifest) and len(manifest_bytes) <= 65536
        assert manifest['distribution'] == roster(source)
        assert manifest['compiled_source'] == roster(tests if label.startswith('interactions') else source)
        assert manifest['host_support'] == roster(hosts)
        assert unpack(argv) == [os.fsencode(v) for v in command['argv']]
        bare = {k: v for k, v in command['environment'].items() if k not in KEYS}
        assert unpack(environment) == [os.fsencode(k + '=' + v) for k, v in sorted(bare.items())]
        expected = dict(zip(KEYS, (digest(manifest_bytes), digest(argv), digest(environment),
                                   manifest['tools']['rustc']['sha256'], digest(version))))
        assert binding['compile_identity_keys'] == expected
        assert {k: command['environment'][k] for k in KEYS} == expected
        for item in [manifest['tools']['rustc'], manifest['tools']['python'], manifest['tools']['cc'],
                     *manifest['tools']['SDK_headers'], *manifest['orchestration']]:
            assert row(item['path'], Path(item['path']).read_bytes()) == item, item['path']
        # Recorded live command terminality is reconciled; old numeric PIDs are
        # never reprobed because ownership can change through PID reuse.
        for kind in (label, label + '-rustc-version'):
            rec = read(P / 'commands' / kind / 'receipt.json')
            assert rec['exit_code'] == 0 and rec['expectation_met'] and rec['child_reaped'] and rec['owned_group_absent']
            assert not rec['timed_out_or_output_limited']
            for stream in ('stdout', 'stderr'):
                assert digest((P / 'commands' / kind / stream).read_bytes()) == rec[stream + '_sha256']
        artifact = read(P / 'commands' / label / 'artifact.json')
        assert not Path(artifact['path']).exists()
        cleanup = read(P / 'commands' / label / 'cleanup.json')
        assert cleanup['completed'] and cleanup['owned_scratch_removed'] and cleanup['recorded_owned_groups_absent']
        if label == 'metadata-unit':
            assert artifact['bytes'] == 0 and artifact['sha256'] == digest(b'')
            assert read(pre / 'output-limitation.json')
        elif label == 'metadata-production':
            assert artifact['bytes'] == 24482879
        else:
            test = read(P / 'commands' / (label + '-tests') / 'receipt.json')
            stdout = (P / 'commands' / (label + '-tests') / 'stdout').read_bytes()
            assert test['argv'][1:] == ['combined_source_interaction_', '--nocapture', '--test-threads=1']
            assert b'4 passed; 0 failed; 0 ignored; 0 measured; 468 filtered out' in stdout
            assert digest(stdout) == test['stdout_sha256'] and test['exit_code'] == 0
        builds.append(dict(label=label, manifest_sha256=digest(manifest_bytes),
            five_keys_reconciled=True, artifact_bytes=artifact['bytes'],
            artifact_sha256=artifact['sha256'], scope='unit typechecking only; zero-byte metadata' if label == 'metadata-unit' else manifest['qualification_scope']))
    assert not (P / 'owned-work').exists()
    return dict(schema=1, root_release_sha256=digest(release.read_bytes()), packets=packets,
        acceptances=acceptances, source_members=len(source), source_tree_sha256=TREE,
        host_members=len(hosts), host_tree_sha256=HOST, overlay_files=len(changed), overlay_bytes=180134,
        six_orders=order_results, producer_builds=builds, producer_tests_each_mode=4,
        descriptor_source_count=145, descriptor_host_count=11, descriptor_code_otherwise_exact=True,
        helper_unused=True, WorkAuditPending=True, prior_assumptions_preserved=dict(preparation=2, metadata_extent_verifier=1),
        no_native_or_global_inventory=True, no_runtime_loader_or_selected_provenance_claim=True)


if __name__ == '__main__':
    result = inspect()
    write('audit-results.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('six_orders', 'producer_builds', 'packets', 'acceptances')}, sort_keys=True))
