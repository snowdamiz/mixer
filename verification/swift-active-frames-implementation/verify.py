#!/usr/bin/env python3
"""Offline evidence integrity/source binding replay. No compiler or binary runs.

Invoke from any directory. Disposable build/ targets and original absolute
command paths are deliberately not needed. Actual-source completeness and
runtime correctness still require independent review; this verifier does not
infer those properties from syntax, aggregate bytes, or a passing receipt.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import tarfile

HERE = Path(__file__).resolve().parent


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def read(path):
    return json.loads(path.read_text())


def ref(value):
    path = HERE / value['path']
    assert path.is_relative_to(HERE) and sha(path) == value['sha256'], value
    return path


def archive(path):
    result = {}
    with tarfile.open(path) as stream:
        for member in stream:
            assert member.isfile() and not Path(member.name).is_absolute()
            assert '..' not in Path(member.name).parts and member.name not in result
            result[member.name] = stream.extractfile(member).read()
    return result


def source(path, manifest_path, expected_tree):
    manifest = read(manifest_path)
    assert sha_bytes(encoded(manifest)) == expected_tree
    contents = archive(path)
    assert {name.removeprefix('vm/'): sha_bytes(value) for name, value in contents.items()} == manifest
    return contents


def artifacts(directory):
    index = read(directory / 'qualifying-artifacts.json')
    path = directory / 'qualifying-artifacts.tar.gz'
    assert sha(path) == index['archiveSHA256']
    members = archive(path)
    assert len(members) == len(index['members'])
    for item in index['members']:
        assert sha_bytes(members[item['member']]) == item['sha256']
    return index


def command_outputs(path):
    receipt = read(path)
    names = set()
    for item in receipt['commands']:
        assert item['name'] not in names
        names.add(item['name'])
        for stream in ['stdout', 'stderr']:
            assert sha(path.parent / item[stream]) == item[stream + 'SHA256']
    return receipt


def verify(check_worktree=False):
    final = read(HERE / 'final-receipt.json')
    for name in ['implementationDocument', 'caseResults', 'retainedAttempts', 'processCleanup']:
        ref(final[name])
    independent = read(ref(final['independentReview']['decision']))
    ref(final['independentReview']['seal'])
    assert independent['status'] == 'independent-review-complete-root-acceptance-pending-at-user-pause'
    assert not independent['remainingBlockingReviewFindings']
    cleanup = read(ref(final['processCleanup']))
    assert cleanup['buildDirectoryAbsent'] and not cleanup['processesStopped']
    assert not cleanup['after']['matchingOwnedBuildProcesses']
    assert not cleanup['otherProjectsTouched']
    final_tree = final['finalSource']['sourceTreeSHA256']
    baseline_tree = final['baselineSource']['sourceTreeSHA256']
    assert final_tree == '4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
    assert independent['sourceTreeSHA256'] == final_tree
    assert baseline_tree == '4df46815f8a9b30db00dda35ed97603da229ac3be957d3f27df38ed2ac56a7c9'
    frozen = source(ref(final['finalSource']['archive']), ref(final['finalSource']['manifest']), final_tree)
    baseline = source(ref(final['baselineSource']['archive']), ref(final['baselineSource']['manifest']), baseline_tree)
    assert len(frozen) == 119 and len(baseline) == 117
    freeze = read(ref(final['finalSource']['freeze']))
    assert freeze['sourceArchiveSHA256'] == final['finalSource']['archive']['sha256']
    assert freeze['sourceTreeSHA256'] == final_tree
    if check_worktree:
        root = HERE.parents[1]
        assert all(sha(root / name) == sha_bytes(value) for name, value in frozen.items())
    main_path, meta_path = ref(final['hostReceipt']), ref(final['metadataReceipt'])
    main, metadata = command_outputs(main_path), command_outputs(meta_path)
    assert main['status'].startswith('passed-') and metadata['status'].startswith('passed-')
    assert main['sourceFreeze'] == metadata['sourceFreeze'] == freeze
    for variant in main['variants']:
        assert sha(main_path.parent / variant['archive']) == variant['archiveSHA256']
        source(main_path.parent / variant['archive'], main_path.parent / variant['manifest'], variant['sourceTreeSHA256'])
    index = artifacts(main_path.parent)
    metadata_index = artifacts(meta_path.parent)
    assert len(index['members']) == 100 and len(metadata_index['members']) == 8
    assert len(main['binaries']) == 92 and len(main['abi']) == 8
    commands = {item['name']: item for item in main['commands']}
    assert len(commands) == 229 and len(final['commands']) == 229
    for mapping in final['commands']:
        selected = commands[mapping['name']]
        assert selected['sourceTreeSHA256'] == mapping['sourceTreeSHA256']
        for stream in ['stdout', 'stderr']:
            assert sha(ref(mapping[stream])) == selected[stream + 'SHA256']
        assert mapping['executionOrigin'] == mapping['importChain'][-1]
        previous = None
        for link in mapping['importChain']:
            receipt_path = ref(link['receipt'])
            candidate = next(item for item in read(receipt_path)['commands'] if item['name'] == mapping['name'])
            assert candidate['sourceTreeSHA256'] == link['sourceTreeSHA256'] == mapping['sourceTreeSHA256']
            for stream in ['stdout', 'stderr']:
                assert sha(receipt_path.parent / candidate[stream]) == candidate[stream + 'SHA256']
            if previous:
                assert Path(previous['reusedFromReceipt']).name == receipt_path.name
                assert Path(previous['reusedFromReceipt']).parent.name == receipt_path.parent.name
                for key in ['argv', 'startedUTC', 'completedUTC', 'exitCode',
                            'sourceTreeSHA256', 'stdoutSHA256', 'stderrSHA256']:
                    assert previous[key] == candidate[key]
            previous = candidate
        assert not previous.get('reusedFromReceipt')
        assert mapping['reused'] == (len(mapping['importChain']) > 1)
    assert sum(item['reused'] for item in final['commands']) == 204
    assert sum(not item['reused'] for item in final['commands']) == 25
    new_identities = set()
    total_candidate_passed = 0
    for comparison in main['comparisons']:
        identity_sets, trace_sets, count_sets = {}, {}, {}
        for variant, tree in [('baseline', baseline_tree), ('candidate', final_tree)]:
            label = variant + '-' + comparison['config'] + '-' + comparison['profile']
            items = [item for item in main['binaries'] if item['label'] == label]
            identities, traces, counts = [], [], []
            for item in items:
                run_command, listing_command = commands[item['runCommand']], commands[item['listCommand']]
                assert run_command['sourceTreeSHA256'] == listing_command['sourceTreeSHA256'] == tree
                if variant == 'candidate':
                    mapping = next(row for row in final['commands'] if row['name'] == item['runCommand'])
                    assert mapping['executionOrigin']['receipt']['path'] == 'results/20261024T050048420640Z/receipt.json'
                listing = (main_path.parent / listing_command['stdout']).read_text()
                assert [line for line in listing.splitlines() if line.endswith(': test')] == item['runtimeTests']
                identities += item['runtimeTests']
                run = (main_path.parent / run_command['stdout']).read_text()
                summary = re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', run)
                assert len(summary) == 1 and summary[0][0] == 'ok' and summary[0][2] == '0'
                counts.append(dict(target=item['target'], passed=int(summary[0][1]), ignored=int(summary[0][3])))
                traces += [line[line.index(marker):] for line in run.splitlines()
                           for marker in ['control_trace ', 'numeric_trace '] if marker in line]
                assert any(row['label'] == label and row['sha256'] == item['sha256'] and row['sourceTreeSHA256'] == tree for row in index['members'])
            # Legacy receipts preserve original Cargo artifact order. Compare
            # counts by target; traces must have the actual stable order.
            assert sorted(counts, key=lambda row: row['target']) == sorted(comparison[variant + 'Counts'], key=lambda row: row['target'])
            identity_sets[variant], trace_sets[variant], count_sets[variant] = set(identities), traces, counts
        added = identity_sets['candidate'] - identity_sets['baseline']
        assert added == set(comparison['addedTests']) and len(added) == 22
        assert not identity_sets['baseline'] - identity_sets['candidate']
        assert all('frame_operations::tests::af' in item for item in added)
        assert trace_sets['candidate'] == trace_sets['baseline']
        assert sha_bytes(encoded(trace_sets['candidate'])) == comparison['frozenTraceSHA256']
        new_identities |= added
        total_candidate_passed += sum(row['passed'] for row in count_sets['candidate'])
    assert len(new_identities) == 22 and len(main['comparisons']) == 4
    # ABI export logs are preserved actual outputs from fresh final-source
    # builds, not a claim based only on Rust public source declarations.
    for config in ['swift', 'all']:
        for profile in ['debug', 'release']:
            exports = []
            for variant in ['baseline', 'candidate']:
                label = variant + '-' + config + '-' + profile + '-abi'
                item = next(row for row in main['abi'] if row['label'] == label)
                output = (main_path.parent / commands[label + '-exports']['stdout']).read_text()
                assert sorted(line for line in output.splitlines() if line.startswith('_mixer_')) == item['exports']
                exports.append(item['exports'])
            assert exports[0] == exports[1]
    assert read(main_path.parent / 'baseline-frozen-methods.json') == read(main_path.parent / 'candidate-frozen-methods.json')
    lint = read(main_path.parent / 'broad-clippy-identities.json')
    assert lint['baseline'] == lint['candidate'] and len(lint['candidate']) == 26
    for item in main['commands']:
        if item['name'].startswith(('baseline-', 'candidate-')) and 'clippy' not in item['name']:
            assert item['exitCode'] == 0
    # Derived layout source appends only metadata helpers. Exact product bytes
    # precede each append, with one separate example invoking that helper.
    derived = metadata['variants'][0]
    assert sha(meta_path.parent / derived['archive']) == derived['archiveSHA256']
    layout = source(meta_path.parent / derived['archive'], meta_path.parent / 'layout-source-manifest.json', derived['sourceTreeSHA256'])
    appended = {
        'vm/src/experimental_swift_reactor/frame_operations.rs': b'\n' + (meta_path.parent / 'layout-probe.rs.txt').read_bytes(),
        'vm/src/experimental_swift_reactor/execution.rs': b'\npub(super) fn af_layout_probe(){frame_operations::af_layout_probe();}\n#[cfg(test)] #[test] fn af_layout_only(){frame_operations::af_layout_probe();}\n',
        'vm/src/experimental_swift_reactor/mod.rs': b'\npub(crate) fn af_layout_probe(){execution::af_layout_probe();}\n',
        'vm/src/lib.rs': b'\npub fn af_layout_probe(){experimental_swift_reactor::af_layout_probe();}\n',
    }
    for name, value in frozen.items():
        assert layout[name] == value + appended.get(name, b''), name
    assert set(layout) - set(frozen) == {'vm/examples/af-layout.rs'}
    assert layout['vm/examples/af-layout.rs'] == b'fn main(){mixer_vm::af_layout_probe();}\n'
    supplemental = read(HERE / 'implementation-inventory-schema.json')
    accepted = read(HERE / 'frozen-inventory-schema.json')
    assert len(supplemental) == 16804 and len(accepted) == 1061
    assert len(set(row['field'] for row in supplemental)) == len(supplemental)
    for record in metadata['typedMIR']:
        assert record['sourceTreeSHA256'] == final_tree
        assert sha(meta_path.parent / record['path']) == record['sha256']
        actual = read(meta_path.parent / (record['config'] + '-typed-roles.json'))
        saved = [row for row in supplemental if row['config'] == record['config'] and row['field'].startswith('mir_')]
        comparable = lambda rows: [{key: value for key, value in row.items() if key != 'mirLine'} for row in rows]
        assert comparable(actual) == comparable(saved)
        assert len(actual) == record['positions'] and record['exactSavedTypedRolesEqual']
    bound_groups = {}
    for layout_record in metadata['layouts']:
        unit = layout_record['mode'] == 'unit'
        selected = accepted + [row for row in supplemental if unit or row['config'] != 'unit']
        assert layout_record['fieldCount'] == len(selected) == (17865 if unit else 9345)
        fields, intervals = {}, {}
        for line in layout_record['records']:
            if not line.startswith('AF_FIELD|'):
                continue
            _, owner, field, offset, size, align = line.split('|')
            offset, size, align = int(offset), int(size), int(align)
            assert align > 0 and offset % align == 0 and (owner, field) not in fields
            fields[(owner, field)] = (offset, size, align)
            if size:
                intervals.setdefault(owner, []).append((offset, offset + size))
        assert len(fields) == len(selected)
        expected_names = {
            ('PermanentPositions' if row['envelope'] == 'permanent' else 'ActivePositions', row['field'])
            for row in accepted
        } | {
            ('ImplementationPermanentPositions' if row['envelope'] == 'permanent' else 'ImplementationActivePositions', row['field'])
            for row in supplemental if unit or row['config'] != 'unit'
        }
        assert set(fields) == expected_names
        bounds = list(map(int, next(line for line in layout_record['records'] if line.startswith('AF_BOUNDS|')).split('|')[1:]))
        sizes = list(map(int, next(line for line in layout_record['records'] if line.startswith('AF_SIZES|')).split('|')[1:]))
        owners = ['PermanentPositions', 'ActivePositions', 'ImplementationPermanentPositions', 'ImplementationActivePositions']
        for owner, size in zip(owners, sizes):
            ordered = sorted(intervals[owner])
            assert all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:]))
            assert max(end for _, end in ordered) <= size
        assert bounds[0] == sizes[0] and bounds[1] == sizes[1]
        assert bounds[2] == sizes[0] + sizes[2] and bounds[3] == sizes[1] + sizes[3]
        assert bounds[4] == bounds[3] + bounds[5] and bounds[5] == 119576 and bounds[8] == 424
        assert bounds[0] == (175336 if unit else 175144) and bounds[1] == 240776
        assert bounds[2:5] == ([1945656, 1505296, 1624872] if unit else [1086648, 929872, 1049448])
        assert next(line for line in layout_record['records'] if line.startswith('AF_STATE|')) == ('AF_STATE|0|112|4640|56' if unit else 'AF_STATE|0|112|4592|56')
        assert layout_record['binarySHA256'] == next(row['sha256'] for row in metadata_index['members'] if row['label'] == layout_record['label'])
        bound_groups.setdefault(layout_record['mode'], []).append(bounds)
    assert len(metadata['layouts']) == 8 and all(len(rows) == 4 and all(row == rows[0] for row in rows) for rows in bound_groups.values())
    assert all(not value for value in final['scope'].values())
    seal = HERE / 'seal.json'
    sealed_files = None
    if seal.exists():
        packet = read(seal)
        for name, expected in packet['files'].items():
            path = HERE / name
            assert path.is_relative_to(HERE) and sha(path) == expected, name
        assert sha_bytes(encoded(packet['files'])) == packet['filesTreeSHA256']
        sealed_files = len(packet['files'])
    return dict(status='passed-offline-evidence-integrity-and-source-binding',
                finalCandidateTree=final_tree, baselineTree=baseline_tree,
                runtimeConfigurations=4, newFrameTestIdentities=22,
                candidatePassedExecutions=total_candidate_passed,
                retainedProductBinaries=92, retainedABIDylibs=8,
                compiledLayouts=8, retainedMetadataBinaries=8,
                commands=229, importedCommands=204, newlyExecutedCommands=25,
                originalFrozenFields=1061, positiveSupplementalFields=16804,
                worktreeChecked=check_worktree, sealedFiles=sealed_files,
                scope='Offline hashes, real archived inputs, command lineage, test outputs, ABI observations and compiled offsets only; independent actual-source/algorithm acceptance remains separate.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-worktree', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify(args.check_worktree)
    if args.report:
        args.report.write_bytes(encoded(result))
    print(json.dumps(result, sort_keys=True, indent=2))
