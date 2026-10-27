"""Frozen correction commands, each a direct ordinary-Python child <=60seconds."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def ident(path):
    import hashlib
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    output = HERE / 'run1'
    output.mkdir(exist_ok=False)
    commands = [('controls', [sys.executable, '-B', str(HERE / 'run_controls.py'), '--output', str(HERE / 'controls-run1')]), ('compact-pass', [sys.executable, '-B', str(HERE / 'check_descriptor_joins.py'), '--output', str(HERE / 'facets-run1')])]
    records = []
    for label, argv in commands:
        start = time.monotonic()
        timeout = False
        try:
            child = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
            code, stdout, stderr = child.returncode, child.stdout, child.stderr
        except subprocess.TimeoutExpired as failure:
            timeout = True
            code, stdout, stderr = None, failure.stdout or b'', failure.stderr or b''
        (output / (label + '.stdout')).write_bytes(stdout)
        (output / (label + '.stderr')).write_bytes(stderr)
        records.append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'exit': code, 'timeout_seconds': 60, 'timeout': timeout, 'elapsed_seconds': time.monotonic() - start, 'direct_child_reaped': True, 'stdout': ident(output / (label + '.stdout')), 'stderr': ident(output / (label + '.stderr'))})
        if timeout or label == 'controls' and code != 0:
            break
    accepted_command_scope = len(records) == 2 and records[0]['exit'] == 0 and records[1]['exit'] == 1 and not any(x['timeout'] for x in records)
    report = json.loads((HERE / 'facets-run1/descriptor-facets.json').read_text()) if (HERE / 'facets-run1/descriptor-facets.json').is_file() else None
    expected_findings = False
    if report is not None:
        expected_findings = [(x['row'], x['state'], x['file'].rsplit('/', 1)[-1]) for x in report['findings']] == [(3, 'terminal-before-return', 'boundary-162.rows.jsonl.gz.compact.jsonl'), (5, 'dirty-before-return', 'boundary-162.rows.jsonl.gz.compact.jsonl')]
        expected_findings = expected_findings and report['counts']['recorded_selected_native_completions'] == 665 and report['counts']['native_completion_rows'] == 663 and report['counts']['missing_selected_native_completion'] == 844 and report['counts']['no_selected_rows'] == 108
    complete = accepted_command_scope and expected_findings
    receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'completed-selected-correction-with-two-preserved-attribution-findings; not-qualified' if complete else 'failed-or-unexpected-correction-result', 'commands': records, 'python': sys.version, 'python_executable': sys.executable, 'source_seal': ident(HERE / 'source-seal.json'), 'source_tree_digest': json.loads((HERE / 'source-seal.json').read_text())['source_tree_digest'], 'source_revision_context_from_pinned_acceptance': json.loads((ROOT / 'verification/android-editor-boundary-root-review/finite-observation-consistency-acceptance.json').read_text())['source_revision_context'], 'prepared_input_manifest': ident(HERE / 'prepared-input-manifest.json'), 'compact_pass_exit1_explicitly_retained': bool(complete), 'known_two_findings_preserved': expected_findings, 'cleanup': {'all_direct_children_reaped': True, 'scratch_created': False, 'native_or_capture_processes_started': False, 'owned_simulator_emulator_instances_started': False, 'process_inventories_performed': False}, 'scope': 'Finite control correction and one compact-data pass only; no Java/product/native/full-auditor execution, bytecode cache access or original packet mutation.', 'independent_review': 'pending', 'whole_subject_or_execution_native_OTA_GA_accepted': False}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'commands': [{'label': x['label'], 'exit': x['exit'], 'timeout': x['timeout'], 'seconds': x['elapsed_seconds']} for x in records]}))
    return 0 if complete else 1


if __name__ == '__main__':
    sys.exit(main())
