"""Read-only verification of exact source/support/compile/descriptor evidence."""
from pathlib import Path
import json
import struct
import sys

sys.dont_write_bytecode = True
from prepare import HERE, KEYS, LOADER_PATH, PHASE_PATH, HELPER_PATH, sha, canonical, roster, inputs, checked_candidate
from run import packed, packed_environment

def read(path):
    return json.loads(path.read_bytes())

def main():
    source, hosts, custody = checked_candidate()
    base, _, _ = inputs()
    checks = {}
    def check(name, value):
        assert value, name
        checks[name] = True
    check('exact_source145_and_host11_frozen_custody', len(source) == 145 and len(hosts) == 11)
    check('only_two_changed_source_members_and_one_exact_helper',
          {name for name in base if source[name] != base[name]} == {LOADER_PATH, PHASE_PATH}
          and set(source) - set(base) == {HELPER_PATH})
    check('loader_only_literal144_to145', source[LOADER_PATH].replace(b'if word(b, 32) != 145\n', b'if word(b, 32) != 144\n') == base[LOADER_PATH])
    check('phase_only_adds_unused_private_module', source[PHASE_PATH].replace(b'// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n', b'') == base[PHASE_PATH])
    check('emission_helper_exact_accepted_sha256', sha(source[HELPER_PATH]) == 'ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a')
    results = read(HERE / 'results.json')
    index = read(HERE / 'command-index.json')
    check('exact22_final_commands', len(index) == results['commands'] == 22)
    commands = {}
    for item in index:
        p = HERE / 'commands' / item['label'] / 'receipt.json'
        check('receipt_' + item['label'], sha(p.read_bytes()) == item['receipt']['sha256'])
        receipt = read(p)
        assert item['expectation_met'] and receipt['expectation_met']
        assert receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['exit_code'] == 0
        for kind in ['stdout', 'stderr']:
            b = (p.parent / kind).read_bytes()
            assert sha(b) == receipt[kind]['sha256'] and len(b) == receipt[kind]['bytes']
        commands[item['label']] = receipt
    artifacts = {item['label']: item for item in results['artifacts_measured_then_removed']}
    check('all12_compiler_artifacts_measured', len(artifacts) == 12)
    for label, artifact in artifacts.items():
        p = HERE / 'preimages' / label
        binding = read(p / 'binding.json')
        manifest = read(p / 'manifest.json')
        argv = (p / 'argv.bin').read_bytes()
        environment = (p / 'environment.bin').read_bytes()
        version = (p / 'compiler-version.txt').read_bytes()
        parts = [canonical(manifest), argv, environment, version]
        receipt = commands[label]
        check('preimage_' + label,
              manifest['distribution'] == roster(source) and manifest['host_support'] == roster(hosts)
              and argv == packed(receipt['argv'])
              and environment == packed_environment({k: v for k, v in receipt['environment'].items() if k not in KEYS}))
        values = [sha(parts[0]), sha(parts[1]), sha(parts[2]), results['compiler']['sha256'], sha(parts[3])]
        assert binding['compile_keys'] == dict(zip(KEYS, values))
        actual = {k: receipt['environment'][k] for k in KEYS if k in receipt['environment']}
        assert binding['actual_compile_identity_keys'] == actual
        variant = binding['negative_identity_variant']
        expected = dict(zip(KEYS, values))
        if variant == 'missing':
            del expected[KEYS[0]]
        elif variant == 'malformed':
            expected[KEYS[0]] = 'G' * 64
        elif variant == 'stale':
            expected[KEYS[0]] = '0' * 64
        assert actual == expected
        descriptor = (p / 'build-preimage.bin').read_bytes()
        assert descriptor[:8] == b'MIXLBD01'
        for at, value in [(8, 1), (16, 512), (24, len(descriptor)), (32, 145), (40, 11), (80, artifact['bytes'])]:
            assert struct.unpack_from('<Q', descriptor, at)[0] == value
        cursor = 512
        for i, part in enumerate(parts):
            assert struct.unpack_from('<Q', descriptor, 48 + 8 * i)[0] == len(part)
            assert descriptor[cursor:cursor + len(part)] == part
            assert descriptor[152 + 32 * i:184 + 32 * i].hex() == sha(part)
            cursor += len(part)
        assert cursor == len(descriptor)
        assert descriptor[280:312].hex() == results['compiler']['sha256']
        assert descriptor[312:344].hex() == artifact['sha256']
        assert not Path(artifact['path']).exists()
        check('independent_keys_and_build_bytes_' + label, True)
    for mode in ['debug', 'optimized']:
        p = HERE / 'commands' / ('pure-' + mode + '-bound-controls') / 'stdout'
        assert b'descriptor_controls=41' in p.read_bytes()
        for variant in ['missing', 'malformed', 'stale']:
            p = HERE / 'commands' / ('pure-' + mode + '-' + variant + '-controls') / 'stdout'
            assert ('identity_negative=' + variant).encode() in p.read_bytes()
    check('82_finite_pure_controls_and_six_negative_identity_builds', True)
    closure = read(HERE / 'build-input-manifest.json')
    check('orchestration_is_separate_from_exact11_support_members',
          len(closure['host_support']['members']) == 11 and 'orchestration' in closure and 'tools' in closure)
    for item in closure['orchestration']:
        assert sha(Path(item['path']).read_bytes()) == item['sha256']
    check('final_runner_prepare_controls_proposal_identity', True)
    extraction = read(HERE / 'extraction.json')
    assert extraction['validator_error_type_is_stubbed'] and not extraction['type_layout_claim']
    for item in extraction['fragments']:
        assert item['source_sha256'] == sha(source[LOADER_PATH]) and item['verbatim_from_candidate']
    check('no_harness_layout_or_genuine_loader_claim', not results['type_layout_claim'] and not results['actual_loader_ingress_executed'])
    cleanup = read(HERE / 'cleanup.json')
    check('owned_children_reaped_and_owned_scratch_removed', cleanup['completed'] and cleanup['recorded_owned_child_groups_absent'] and cleanup['owned_scratch_removed'] and not (HERE / 'owned-work').exists())
    old = HERE / 'attempt-history/pure-scaffold-v1'
    failure = read(old / 'commands/pure-debug-bound/receipt.json')
    check('original_failed_scaffold_compiler_evidence_preserved',
          not failure['expectation_met'] and failure['exit_code'] != 0
          and b'too many leading `super`' in (old / 'commands/pure-debug-bound/stderr').read_bytes())
    check('failed_scaffold_scratch_cleanup_recorded', read(old / 'postfailure-cleanup.json')['scratch_removed_after_recording'])
    check('original_preparation_ordering_assertion_preserved', not read(HERE / 'attempt-history/preparation-ordering-v1/receipt.json')['expectation_met'])
    if (HERE / 'seal.json').exists():
        seal = read(HERE / 'seal.json')
        members = seal['members']
        assert len(members) == seal['member_count']
        assert sum(item['bytes'] for item in members) == seal['member_bytes']
        assert sha(canonical(members)) == seal['tree_sha256']
        actual_paths = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()}
        assert actual_paths == {item['path'] for item in members} | {'seal.json'}
        for item in members:
            b = (HERE / item['path']).read_bytes()
            assert len(b) == item['bytes'] and sha(b) == item['sha256'], item['path']
        check('complete_frozen_packet_member_closure', True)
    print(json.dumps({'schema': 1, 'verification_groups': len(checks), 'all_pass': True,
        'source_tree_sha256': roster(source)['tree_sha256'], 'host_support_tree_sha256': roster(hosts)['tree_sha256'],
        'final_commands': 22, 'metadata_builds': 4, 'pure_bound_controls': 82,
        'private_identity_negative_builds_and_runs': 6,
        'engine_VM_writer_or_actual_loader_admission': False}, sort_keys=True))

if __name__ == '__main__':
    main()
