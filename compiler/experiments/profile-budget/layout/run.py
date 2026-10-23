#!/usr/bin/env python3
"""Host-only layout/allocator/RSS measurements with unchanged production limits."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import tarfile
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location('qualification_support', ROOT / 'compiler/qualification_support.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
REVISION = '64123c509e861ddd522631b293eadebdaca11341'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='2026-10-22')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name, re.ASCII):
        raise ValueError('use a bounded ASCII output label')
    output = HERE.parent / 'local' / ('layout-' + args.name)
    evidence = HERE / 'evidence' / args.name
    output.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    env = helper.clean_environment()
    env['PATH'] = '/opt/homebrew/opt/rustup/bin' + os.pathsep + env['PATH']
    commands = []
    recorder = helper.CommandRecorder(evidence, commands, ROOT)
    git, cargo, rustc = [shutil.which(name, path=env['PATH']) for name in ['git', 'cargo', 'rustc']]
    record = {'schema_version': 1, 'status': 'running', 'revision': REVISION,
        'implementation_agent_selection': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'scope': 'macOS host diagnostics within unchanged production limits; no full Swift decode/execution or device qualification',
        'commands': commands, 'measurements': [], 'production_limits_changed': False,
        'allocator_scope': 'Rust requested live bytes/counts and observed maximums via System allocator wrapper; excludes allocator internal metadata/transient copies and native libraries',
        'rss_scope': 'Darwin /usr/bin/time -l process peak resident bytes, including test harness/native libraries; no steady-state app or OTA-relative claim'}
    probe_source = HERE / 'probe.rs'
    source_manifest = {str(path.relative_to(ROOT)): helper.digest(path) for path in
        [pathlib.Path(__file__), probe_source, ROOT / 'compiler/qualification_support.py']}
    def run(name, command, extra_env=None, **kwargs):
        actual_env = dict(env)
        if extra_env:
            actual_env.update(extra_env)
        value = recorder.run(name, command, env=actual_env, **kwargs)
        print(name + ': exit ' + str(commands[-1]['exitCode']), flush=True)
        return value
    try:
        archive = output / 'source.tar'
        run('source-export', [git, 'archive', '--format=tar', '--output=' + str(archive), REVISION, 'vm', 'contracts'])
        record['source_archive_sha256'] = helper.digest(archive)
        with tarfile.open(archive) as stream:
            stream.extractall(output / 'source', filter='data')
        source = output / 'source/vm'
        original = {str(path.relative_to(source)): helper.digest(path) for path in source.rglob('*') if path.is_file()}
        # Add test-only observers; production limits and logic are unchanged.
        lib_path = source / 'src/lib.rs'
        execute_path = source / 'src/execute.rs'
        lib_path.write_text(lib_path.read_text() + '\n#[cfg(test)]\nmod measurements;\n')
        execute_path.write_text(execute_path.read_text() + '''
#[cfg(test)]
pub(crate) fn measurement_frame_layout() -> (usize, usize, usize, usize) {
    (std::mem::size_of::<Frame>(), std::mem::align_of::<Frame>(),
     std::mem::size_of::<Label>(), std::mem::align_of::<Label>())
}
''')
        shutil.copyfile(probe_source, source / 'src/measurements.rs')
        record['test_only_instrumentation'] = {'lib_append': '#[cfg(test)] mod measurements;',
            'execute_append': 'cfg(test) private Frame/Label size/alignment observer only',
            'probe_sha256': helper.digest(probe_source)}
        record['versions'] = {name: run('version-' + name, [path, '--version']).strip()
                              for name, path in [('cargo', cargo), ('rustc', rustc)]}
        record['host'] = {'os': run('host-os', ['/usr/bin/sw_vers']).strip(),
                          'architecture': run('host-architecture', ['/usr/bin/uname', '-m']).strip()}
        compiled = run('build-probe', [cargo, 'test', '--release', '--lib', '--no-run', '--message-format=json',
            '--manifest-path', source / 'Cargo.toml', '--target-dir', output / 'target'])
        artifacts = [helper.strict_json(line) for line in compiled.splitlines() if line.startswith('{')]
        binaries = [item['executable'] for item in artifacts if item.get('reason') == 'compiler-artifact'
                    and item.get('executable') and item['target']['name'] == 'mixer_vm']
        if len(binaries) != 1:
            raise ValueError('expected one isolated unit-test executable')
        binary = pathlib.Path(binaries[0])
        record['probe_binary'] = helper.tool_identity(binary)
        fixtures = output / 'fixtures'
        run('generate-fixtures', [binary, '--exact', 'measurements::generate', '--nocapture', '--test-threads=1'],
            extra_env={'MIXER_PROBE_FIXTURES': str(fixtures)})
        record['fixtures'] = {path.name: {'bytes': path.stat().st_size, 'sha256': helper.digest(path)}
                              for path in sorted(fixtures.glob('*.wasm'))}
        cases = [('empty', 'empty'), ('source-only', 'combined'), ('decode-only', 'combined'),
                 ('dense', 'dense'), ('many-functions', 'many-functions'), ('branches', 'branches'),
                 ('frames', 'frames'), ('globals', 'globals'), ('table', 'table'),
                 ('data', 'data'), ('data-retain', 'data'), ('combined', 'combined'),
                 ('sessions1', 'combined'), ('sessions16', 'combined')]
        for case, file in cases:
            text = run(case, ['/usr/bin/time', '-l', binary, '--exact', 'measurements::probe',
                 '--nocapture', '--test-threads=1'],
                 extra_env={'MIXER_PROBE_CASE': case, 'MIXER_PROBE_FILE': str(fixtures / (file + '.wasm'))}, timeout=60)
            lines = [line.partition('MEASURE_JSON ')[2] for line in text.splitlines() if 'MEASURE_JSON ' in line]
            if len(lines) != 1:
                raise ValueError('expected one structured measurement')
            result = helper.strict_json(lines[0])
            alignment = [line.partition('ALIGNMENT_JSON ')[2] for line in text.splitlines() if 'ALIGNMENT_JSON ' in line]
            if len(alignment) != 1:
                raise ValueError('expected one measured alignment record')
            result['layout']['alignments'] = helper.strict_json(alignment[0])
            stderr = (evidence / (case + '.stderr')).read_text()
            matches = re.findall(r'^\s*(\d+)\s+maximum resident set size\s*$', stderr, re.MULTILINE)
            if len(matches) != 1:
                raise ValueError('unrecognized Darwin time RSS output')
            result['process_max_rss_bytes'] = int(matches[0])
            base = result['phases'][0]['live_requested_bytes']
            result['phase_peak_requested_bytes_above_baseline'] = max(phase['peak_requested_bytes'] for phase in result['phases']) - base
            result['maximum_live_allocations_in_measurement_phases'] = max(phase['peak_live_allocations'] for phase in result['phases'])
            record['measurements'].append(result)
            print(json.dumps({'case': case, 'peak_requested_above_baseline': result['phase_peak_requested_bytes_above_baseline'],
                              'max_rss': result['process_max_rss_bytes']}), flush=True)
        for path, digest in original.items():
            if path not in ('src/lib.rs', 'src/execute.rs') and helper.digest(source / path) != digest:
                raise ValueError('production snapshot changed beyond test-only observer additions')
        if {path: helper.digest(ROOT / path) for path in source_manifest} != source_manifest:
            raise ValueError('measurement source changed during execution')
        record['source_manifest'] = source_manifest
        record['measurement_source_digest'] = hashlib.sha256(json.dumps(source_manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        actual = helper.strict_json((HERE.parent / 'evidence/2026-10-22-qualified/osize-compress-structure.json').read_text())
        matrix = helper.strict_json((HERE.parent / 'evidence/2026-10-22-qualified/receipt.json').read_text())
        instruction_count = next(item['summary']['instructions'] for item in matrix['variants'] if item['name'] == 'osize-compress')
        layout = record['measurements'][0]['layout']
        record['actual_corpus_estimates'] = {'scope': 'arithmetic lower bounds/estimates only; full corpus was not decoded or executed in this experiment',
            'defined_functions': actual['defined_functions'], 'instructions': instruction_count,
            'instruction_struct_bytes_at_len': instruction_count * layout['instruction'],
            'function_struct_bytes_at_len': actual['defined_functions'] * layout['function'],
            'retained_active_data_bytes_if_current_copy_model': actual['active_data_bytes'],
            'initial_linear_memory_bytes': actual['initial_linear_memory_bytes'],
            'minimum_combined_without_source_or_extra_capacity': instruction_count * layout['instruction'] + actual['defined_functions'] * layout['function'] + actual['active_data_bytes'] + actual['initial_linear_memory_bytes'],
            'largest_function_body_wire_bytes': actual['largest_function_bodies'][0]['body_bytes'],
            'wire_bytes_are_not_decoded_instruction_counts': True}
        record['status'] = 'all host probes passed within unchanged profile limits; full-corpus quantities are estimates only'
    except Exception as error:
        record['status'] = 'failed'
        record['failure'] = str(error)
        raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'layout': record['measurements'][0]['layout'],
                      'estimates': record['actual_corpus_estimates']}, indent=2))


if __name__ == '__main__':
    main()
