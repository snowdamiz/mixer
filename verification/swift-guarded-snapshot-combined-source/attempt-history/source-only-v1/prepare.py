"""Source-only composition of frozen components. Does not compile or dispatch Rust."""
from pathlib import Path
import difflib
import hashlib
import itertools
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERIFICATION = ROOT / 'verification'
BASE = VERIFICATION / 'swift-guarded-snapshot-funding-implementation'
COMMON = VERIFICATION / 'swift-guarded-snapshot-work-common-correction'
PHASE = VERIFICATION / 'swift-guarded-snapshot-phase-retention'
DESCRIPTOR = VERIFICATION / 'swift-guarded-snapshot-descriptor-rebinding'
SUPPORT = VERIFICATION / 'swift-real-profile-loader-binding'
REVIEW = VERIFICATION / 'swift-semantic-adapter-root-review'
CONTROL = 'src/experimental_swift_reactor/control.rs'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
HELPER = 'src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
BASE_TREE = '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
COMMON_TREE = '3d7c4e7d557da60e7e111e59f7178d7db300e1018aa781d941b7cd90369cc43b'
PHASE_TREE = '9c654ec4967f184bcc262c36ac4d65067a3f9d48107f7f9e72789f4cd88960fd'
DESCRIPTOR_TREE = '450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a'
SUPPORT_TREE = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
COMPILE_KEYS = [
    'MIXER_LOADER_MANIFEST_SHA256', 'MIXER_LOADER_COMMAND_SHA256',
    'MIXER_LOADER_COMPILE_ENV_SHA256', 'MIXER_LOADER_COMPILER_SHA256',
    'MIXER_LOADER_COMPILER_VERSION_SHA256',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def write(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def row(path, data):
    return dict(path=path, bytes=len(data), sha256=sha(data))


def roster(source):
    members = [row(name, source[name]) for name in sorted(source, key=Path)]
    return dict(schema=1, members=members, member_count=len(members),
                tree_sha256=sha(canonical(members)))


def sealed(folder, expected, selected=None):
    raw = (folder / 'seal.json').read_bytes()
    assert sha(raw) == expected, folder
    seal = json.loads(raw)
    members = {r['path']: r for r in seal['members']}
    assert len(members) == seal['member_count']
    tree_key = 'manifest_sha256' if 'manifest_sha256' in seal else 'tree_sha256'
    assert sha(canonical(seal['members'])) == seal[tree_key]
    names = list(members) if selected is None else selected
    for name in names:
        assert row(name, (folder / name).read_bytes()) == members[name], (folder, name)
    return dict(path=str(folder.relative_to(ROOT)), seal_sha256=expected,
                frozen_member_count=seal['member_count'], verified_members=len(names),
                verified_bytes=sum(members[name]['bytes'] for name in names),
                whole_packet_verified=selected is None)


def acceptance(name, expected):
    path = REVIEW / name
    raw = path.read_bytes()
    assert sha(raw) == expected, path
    return dict(path=str(path.relative_to(ROOT)), sha256=expected,
                status=json.loads(raw)['status'])


def source_manifest(folder, expected):
    manifest = json.loads((folder / 'source-manifest.json').read_bytes())
    assert len(manifest['members']) == (145 if folder == DESCRIPTOR else 144)
    assert sha(canonical(manifest['members'])) == expected
    return manifest['members']


def inputs():
    custody = [
        sealed(BASE, 'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'),
        sealed(COMMON, 'c679b12e5a82c5cd6746f87d8615cb19c6cba00f1d72625cad334bb11adc1422'),
        sealed(PHASE, '623b5ec0b8ef7c2f68b344c191f9a6d2f5fd93b3085c7f0b4ae02c960c895001'),
        sealed(DESCRIPTOR, '5e11885ef1a1189dc10ef8de5b82f4cd969573a8a1130e0a25f146725c23d7ea'),
    ]
    releases = [
        acceptance('guarded-snapshot-funding-host-acceptance.json', '17789ef30bb818f91a928941162029a12c75ca7dddd33e8cfc073ec4950a615f'),
        acceptance('guarded-snapshot-work-common-independent-release.json', 'a57e64c32beaa2b472e8148772d66633f9214754e414e25088ed0e2cdcab93f9'),
        acceptance('guarded-snapshot-phase-retention-host-acceptance.json', '814e60d6dc9a9ee38039e86b1873bf65cd44bbe608dc37919ff39ee8eef84519'),
        acceptance('guarded-snapshot-descriptor-rebinding-host-acceptance.json', 'fafea2179a953a39535193197cc9dd7a82738d22203b8a598b2501fd47550ef6'),
    ]
    base_rows = source_manifest(BASE, BASE_TREE)
    base = {r['path']: (BASE / 'source/vm' / r['path']).read_bytes() for r in base_rows}
    assert roster(base)['members'] == base_rows
    common = dict(base)
    common[CONTROL] = (COMMON / 'overlay' / CONTROL).read_bytes()
    phase = {r['path']: (PHASE / 'source/vm' / r['path']).read_bytes()
             for r in source_manifest(PHASE, PHASE_TREE)}
    descriptor = dict(base)
    for name in [PROFILE, LOADER, HELPER]:
        descriptor[name] = (DESCRIPTOR / 'overlay/vm' / name).read_bytes()
    for folder, source, expected in [(COMMON, common, COMMON_TREE), (PHASE, phase, PHASE_TREE),
                                     (DESCRIPTOR, descriptor, DESCRIPTOR_TREE)]:
        assert roster(source)['members'] == source_manifest(folder, expected)
    host_manifest = json.loads((DESCRIPTOR / 'host-support-manifest.json').read_bytes())
    assert host_manifest['member_count'] == 11
    assert sha(canonical(host_manifest['members'])) == host_manifest['tree_sha256'] == SUPPORT_TREE
    support_paths = ['host/' + r['path'] for r in host_manifest['members']]
    custody.append(sealed(SUPPORT, 'e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2', support_paths))
    hosts = {r['path']: (SUPPORT / 'host' / r['path']).read_bytes() for r in host_manifest['members']}
    assert roster(hosts) == host_manifest
    return base, {'common': common, 'phase': phase, 'descriptor': descriptor}, hosts, custody, releases


def component_operations(base, candidate):
    operations = []
    for name in sorted(candidate, key=Path):
        if base.get(name) == candidate[name]:
            continue
        if name not in base:
            operations.append(dict(path=name, old=None, new=candidate[name]))
            continue
        before, after = base[name].splitlines(True), candidate[name].splitlines(True)
        matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
        for group in matcher.get_grouped_opcodes(3):
            old = b''.join(before[group[0][1]:group[-1][2]])
            new = b''.join(after[group[0][3]:group[-1][4]])
            assert old and base[name].count(old) == 1
            operations.append(dict(path=name, old=old, new=new))
    return operations


def apply(source, operations):
    source = dict(source)
    for op in operations:
        if op['old'] is None:
            assert op['path'] not in source
            source[op['path']] = op['new']
        else:
            assert source[op['path']].count(op['old']) == 1, op['path']
            source[op['path']] = source[op['path']].replace(op['old'], op['new'], 1)
    return source


def between(data, start, end):
    assert data.count(start) == 1 and data.count(end) == 1
    return data[data.index(start):data.index(end)]


def compose():
    base, components, hosts, custody, releases = inputs()
    operations = {name: component_operations(base, source) for name, source in components.items()}
    for name in components:
        assert apply(base, operations[name]) == components[name]
    permutations = []
    combined = None
    for order in itertools.permutations(components):
        source = dict(base)
        for name in order:
            source = apply(source, operations[name])
        if combined is None:
            combined = source
        assert source == combined, order
        permutations.append(dict(order=list(order), source_tree_sha256=roster(source)['tree_sha256']))
    changed = [name for name in combined if base.get(name) != combined[name]]
    assert set(changed) == {CONTROL, PROFILE, LOADER, HELPER}
    assert len(combined) == 145
    assert sha(combined[HELPER]) == 'ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a'
    assert len(combined[HELPER]) == 853
    assert sum(data.count(b'checked_snapshot_emission_bound_v1') for name, data in combined.items() if name != HELPER) == 0
    assert combined[PROFILE].count(b'mod emission_bound_v1;') == 1
    assert between(combined[PROFILE], b'fn proposed_emission_work_v1(', b'fn begin_snapshot_v1(') == between(base[PROFILE], b'fn proposed_emission_work_v1(', b'fn begin_snapshot_v1(')
    # The common component's whole core admission prefix and failure cleanup are
    # identical. The only further control change is the accepted commit result.
    retention = json.loads((PHASE / 'preparation.json').read_bytes())['exact_replacements']
    expected_control = components['common'][CONTROL]
    assert retention[0]['path'] == CONTROL
    assert expected_control.count(retention[0]['old'].encode()) == 1
    expected_control = expected_control.replace(retention[0]['old'].encode(), retention[0]['new'].encode(), 1)
    assert combined[CONTROL] == expected_control
    assert combined[LOADER].replace(b'if word(b, 32) != 145\n', b'if word(b, 32) != 144\n') == base[LOADER]
    declaration = b'// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n'
    assert combined[PROFILE].replace(declaration, b'', 1) == components['phase'][PROFILE]
    normalizer_start = b'    pub(crate) fn end_construction_phase_with_wasi'
    if normalizer_start not in base[CONTROL]:
        normalizer_start = b'    fn end_construction_phase_with_wasi'
    # Exact byte comparison of the unchanged normalizer is recorded separately.
    index = base[CONTROL].find(b'fn end_construction_phase_with_wasi')
    assert index >= 0
    opening = base[CONTROL].index(b'{', index)
    depth = 1
    closing = opening + 1
    while depth:
        if base[CONTROL][closing:closing+1] == b'{': depth += 1
        elif base[CONTROL][closing:closing+1] == b'}': depth -= 1
        closing += 1
    normalizer = base[CONTROL][index:closing]
    assert combined[CONTROL].count(normalizer) == 1
    constants = between(combined[CONTROL], b'const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1', b'/// Common named-source foundation:')
    assert constants == between(components['common'][CONTROL], b'const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1', b'/// Common named-source foundation:')
    checks = dict(schema=1, source_members=145, changed_paths=sorted(changed),
        six_component_orders_identical=permutations, exact_component_reconstruction=True,
        each_patch_unique_exact_context=True, only_accepted_seven_retention_replacements=True,
        common_whole_control_preserved_except_accepted_commit_return=True,
        normalizer_unchanged_sha256=sha(normalizer), constants_block_unchanged_from_common_sha256=sha(constants),
        C=79676, S=941467, A=430175, H=81327, fixed_selected_work=451814442,
        ordinary_shared_source_predicate_actions=3, ordinary_successful_execution_work=0,
        ordinary_and_failed_counter_paths_unchanged_from_common=True,
        selected_source_memory_totals_unchanged_from_common=True,
        WorkAuditPending_preserved=True, helper_unused=True, helper_bytes=853, helper_sha256=sha(combined[HELPER]),
        host_support_members=11, host_support_tree_sha256=SUPPORT_TREE,
        source_only_checks_are_not_runtime_or_OTA_authority=True)
    return base, combined, hosts, custody, releases, checks, operations


def checked_candidate():
    base, source, hosts, custody, releases, checks, operations = compose()
    assert roster(source) == json.loads((HERE / 'source-manifest.json').read_bytes())
    assert roster(hosts) == json.loads((HERE / 'host-support-manifest.json').read_bytes())
    for name in checks['changed_paths']:
        assert (HERE / 'overlay/vm' / name).read_bytes() == source[name]
    return source, hosts


def materialize(destination):
    assert destination.is_relative_to(HERE / 'owned-work')
    assert not destination.exists()
    source, hosts = checked_candidate()
    for name, data in source.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return source, hosts


def main():
    assert not (HERE / 'seal.json').exists(), 'Never mutate a frozen packet'
    base, combined, hosts, custody, releases, checks, operations = compose()
    for name in checks['changed_paths']:
        path = HERE / 'overlay/vm' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(combined[name])
    write('source-manifest.json', roster(combined))
    write('host-support-manifest.json', roster(hosts))
    write('input-custody.json', dict(schema=1, inputs=custody, releases=releases,
        common_acceptance='pending; root permits provisional source composition only',
        base_source_tree_sha256=BASE_TREE, no_active_other_lane_read=True,
        host_support_is_separate_from_runner_tools_and_SDK=True))
    write('source-controls.json', checks)
    write('component-operations.json', {name: [dict(path=op['path'], old_bytes=0 if op['old'] is None else len(op['old']),
        old_sha256=None if op['old'] is None else sha(op['old']), new_bytes=len(op['new']), new_sha256=sha(op['new']))
        for op in ops] for name, ops in operations.items()})
    delta = ''.join(''.join(difflib.unified_diff(base.get(name, b'').decode().splitlines(True),
        combined[name].decode().splitlines(True), fromfile='accepted-funding-source144/' + name,
        tofile='combined-source145/' + name)) for name in checks['changed_paths'])
    (HERE / 'source-delta.patch').write_text(delta)
    write('preparation.json', dict(schema=1, status='provisional-source-only-awaiting-root-common-acceptance-and-compiler-release',
        source_tree_sha256=roster(combined)['tree_sha256'], source_members=145,
        compact_overlay_bytes=sum(len(combined[name]) for name in checks['changed_paths']),
        changed_paths=checks['changed_paths'], base_source_tree_sha256=BASE_TREE,
        recipe='Accepted funding144 + frozen common-correction control + seven accepted retention replacements + exact accepted descriptor helper/module/count edits',
        compile_identity_keys=COMPILE_KEYS, all_five_compile_key_values='pending fresh command/compiler/environment; none borrowed',
        compile_commands=0, Rust_runtime_commands=0, final_seal='pending final authorized checks',
        canonical_or_git_changed=False, native_device_UI_capture_or_global_process_inventory=False,
        actual_loader_guest_cache_scope_construct_or_writer_executed=False,
        bootstrap_H_or_complete_funding_or_healthy_cleanup_or_real_writer_qualified=False,
        WorkAuditPending_preserved=True, helper_unused=True, native_checks='paused and pending'))
    write('source-only-command.json', dict(schema=1, argv=[sys.executable, str(HERE / 'prepare.py')],
        python_version=sys.version, python_executable=sys.executable,
        script_sha256=sha(Path(__file__).read_bytes()), source_tree_sha256=roster(combined)['tree_sha256'],
        scope='Input custody, exact bytes, component commutativity and compact overlay only; no compilation or Rust execution',
        exit_code=0))
    print(json.dumps(dict(prepared=True, source_members=145, source_tree_sha256=roster(combined)['tree_sha256'],
        changed_paths=checks['changed_paths'], compact_overlay_bytes=sum(len(combined[name]) for name in checks['changed_paths']),
        compile_commands=0, Rust_runtime_commands=0)))


if __name__ == '__main__':
    main()
