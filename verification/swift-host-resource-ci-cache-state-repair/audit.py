#!/usr/bin/env python3
"""Recheck the isolated proposal against immutable incident and retained raw bytes."""
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'runs/focused-2'
INCIDENT = ROOT / 'verification/swift-host-resource-ci-cache-state/artifact-cache-state.stdout'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise RuntimeError(message)


def tree(rows):
    return digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())


receipt = json.loads((OUT / 'receipt.json').read_bytes())
retention = json.loads((OUT / 'retention.json').read_bytes())
need(digest(INCIDENT.read_bytes()) == '2dd78d33633fca8c05ba8eed1c2551b6fd023541d0648becacb0456346a39c9c', 'Incident identity')
need(receipt['status'] == 'passed-focused-fixture-proposal' and not receipt['errors'], 'Focused disposition')
need(receipt['cleanup']['removed'] and receipt['cleanup']['groups_returned'], 'Owned cleanup')
need(not (OUT / 'scratch').exists(), 'Focused scratch remains')
need(digest((OUT / 'executed-qualify.py').read_bytes()) == receipt['runner_sha256'], 'Executed harness identity')
need(digest((HERE / 'qualify.py').read_bytes()) == receipt['runner_sha256'], 'Candidate harness changed')
need(receipt['active_elapsed_seconds'] < 600 and receipt['cleanup_elapsed_seconds'] < 60, 'Unchanged bounds')
for command in receipt['commands']:
    need(command['exit'] == 0 and command['child_returned'] and command['owned_group_gone']
         and not command['timed_out'] and not command['output_capped'], 'Command did not pass cleanly')
    need(command['effective_timeout_seconds'] <= 60 and command['per_child_limit_seconds'] == 60, 'Child bounds')
    for stream in ['stdout', 'stderr']:
        raw = (OUT / 'commands' / (command['name'] + '.' + stream)).read_bytes()
        need(digest(raw) == command[stream + '_sha256'], 'Raw command output identity')
rows = retention['files']
need(len(rows) == len({row['path'] for row in rows}), 'Duplicate retained path')
retained = {}
for row in rows:
    compressed = (OUT / row['content']).read_bytes()
    need(digest(compressed) == row['retained_sha256'], 'Retained content identity')
    raw = gzip.decompress(compressed) if row['encoding'] == 'gzip' else compressed
    need(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'Retained raw bytes identity')
    retained[row['path']] = raw
proposed = (HERE / 'proposal/independent_tests.rs').read_bytes()
need(digest(proposed) == receipt['proposal']['proposed_sha256'], 'Proposal identity')
with zipfile.ZipFile(INCIDENT) as archive:
    original = archive.read('pack/source/regression/independent_tests.rs')
    original_manifest = json.loads(archive.read('pack/manifest.json'))
    original_manifest_sha256 = digest(archive.read('pack/manifest.json'))
    exact_rows = []
    instrumented_rows = []
    unchanged = []
    for member in original_manifest['members']:
        if not member['path'].startswith('source/'):
            continue
        name = member['path'].removeprefix('source/')
        original_bytes = archive.read('pack/' + member['path'])
        observed = retained['source/' + name]
        if name == 'regression/independent_tests.rs':
            instrumented = observed
            exact_bytes = proposed
        else:
            need(observed == original_bytes, 'Unapproved copied source change: ' + name)
            unchanged.append(name)
            exact_bytes = original_bytes
        exact_rows.append(dict(path=name, bytes=len(exact_bytes), sha256=digest(exact_bytes)))
        instrumented_rows.append(dict(path=name, bytes=len(observed), sha256=digest(observed)))
need(len(exact_rows) == len([name for name in retained if name.startswith('source/')]), 'Source roster closure')
start = proposed.index(b'fn context_schema_scalar_reserved_and_lengths() {')
end = proposed.index(b'\n#[test]', start)
method = proposed[start:end]
need(method.count(b'baseline.clone()') == 3 and method.count(b'let baseline=Fixture::new();\n') == 1, 'Bounded source correction')
restored = method.replace(b'    let baseline=Fixture::new();\n', b'').replace(b'baseline.clone()', b'Fixture::new()')
need(proposed[:start] + restored + proposed[end:] == original, 'Any source/assertion change beyond baseline and clones')
control = (HERE / 'oracle_controls.rs').read_bytes()
need(instrumented.endswith(control), 'Oracle control suffix identity')
stripped = instrumented[:-len(control)]
for line in [b'    fixture_repair_oracle::check(f, framing, label);\n',
             b'    fixture_repair_oracle::fresh(&mut stream,&mut profile,&mut context,&mut output);\n',
             b'    fixture_repair_oracle::completed(&path);\n']:
    need(stripped.count(line) == 1, 'One oracle insertion required')
    stripped = stripped.replace(line, b'', 1)
need(stripped == proposed, 'Oracle instrumentation changed original assertions')
need(digest(instrumented) == receipt['instrumented_source_sha256'], 'Instrumented source identity')
marker = b'REPAIR_ORACLE exact_input_cases=1003 fresh_file_cases=1003 completed_case_cleanups=1003'
need((OUT / 'commands/oracle-debug-context.stdout').read_bytes().count(marker) == 1, 'Oracle complete closure marker')
exact_rows.sort(key=lambda row: row['path'])
instrumented_rows.sort(key=lambda row: row['path'])
result = dict(status='passed-read-only-evidence-audit', original_incident_failure_preserved=True,
              original_incident_artifact_sha256=digest(INCIDENT.read_bytes()),
              original_pack_manifest_sha256=original_manifest_sha256,
              original_source_revision=receipt['source_revision'], original_git_tree=receipt['source_tree'],
              proposed_source_sha256=digest(proposed), exact_proposal_source_tree_sha256=tree(exact_rows),
              instrumented_source_tree_sha256=tree(instrumented_rows),
              exact_proposal_source_roster=exact_rows, unchanged_source_files=unchanged,
              only_proposed_change='One Fixture::new baseline plus three clone substitutions in the context method',
              all_original_run_and_report_assertions_preserved=True, oracle_suffix_sha256=digest(control),
              all_retained_bytes_and_command_stream_hashes_verified=True,
              compiler_products_hashed_and_removed=retention['compiler_products_hashed_before_removal'],
              bounds=dict(child_seconds=60, active_seconds=600, cleanup_seconds=60),
              native_runtime_started=False, global_process_inventory=False,
              pending=['Canonical repin and provenance review', 'Fresh full fixture run', 'Fresh CI Rust 1.98.1 qualification'],
              performance_equivalence_claimed=False)
(HERE / 'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: result[key] for key in ['status', 'proposed_source_sha256', 'exact_proposal_source_tree_sha256',
                                            'instrumented_source_tree_sha256', 'pending']}))
