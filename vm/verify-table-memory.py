#!/usr/bin/env python3
"""Reproduce table-memory-v3 host evidence; no release authorization or device claim."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'vm/verification/table-memory-v3'
CORPUS_SHA256 = '3308fc08ae16bd7247be67b14bd7ea8af754c2610641d517936aa5570f325964'
FROZEN_PROFILES = {
    'contracts/vm-profile-v1.json': '813a54a4e198a73d49afffe7c8d9cf54f6e76bfca80dd6556a439a4bdf1bdf4c',
    'vm/profiles/numeric-v2.json': '4eb10d61ddc0092bec5f40b40cc3473ae3443491e7bdfe49b9cae80b58e09d57',
}


class Reader:
    """Bounded original structural measurement helper, not executable validation."""
    def __init__(self, data):
        self.data, self.pos = memoryview(data), 0

    def take(self, count):
        if count < 0 or self.pos + count > len(self.data):
            raise ValueError('structural measurement exceeds section')
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value

    def byte(self):
        return self.take(1)[0]

    def uint(self):
        value = 0
        for shift in range(0, 35, 7):
            byte = self.byte()
            if shift == 28 and byte & 0xf0:
                raise ValueError('u32 overflow')
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError('unterminated u32')

    def count(self):
        count = self.uint()
        if count > 1_000_000:
            raise ValueError('measurement vector ceiling exceeded')
        return count

    def offset(self):
        if self.byte() != 0x41:
            raise ValueError('measurement supports i32.const offsets only')
        value = 0
        for shift in range(0, 35, 7):
            byte = self.byte()
            payload = byte & 127
            if shift == 28 and 7 < payload < 0x78:
                raise ValueError('i32 overflow')
            value |= payload << shift
            if byte < 128:
                if self.byte() != 0x0b:
                    raise ValueError('extended constant expression')
                return value & 0xffff_ffff
        raise ValueError('unterminated i32')

    def limits(self):
        flags = self.byte()
        if flags > 1:
            raise ValueError('measurement supports i32 unshared limits only')
        minimum = self.uint()
        maximum = self.uint() if flags else None
        return {'flags': flags, 'minimum': minimum, 'maximum': maximum}

    def end(self):
        if self.pos != len(self.data):
            raise ValueError('trailing measured section bytes')


def structure(data):
    if len(data) > 128 * 1024 * 1024:
        raise ValueError('structural inspector byte ceiling exceeded')
    reader = Reader(data)
    if reader.take(8) != b'\0asm\x01\0\0\0':
        raise ValueError('not Wasm version one')
    result = {'scope': 'selected section structural measurements only; not module validation or execution',
              'sections': [], 'tables': [], 'memories': [], 'elements': [], 'data': []}
    seen = set()
    while reader.pos < len(data):
        section_id = reader.byte()
        size = reader.uint()
        section = Reader(reader.take(size))
        if section_id > 12 or (section_id and section_id in seen):
            raise ValueError('unknown/duplicate measured section')
        seen.add(section_id)
        result['sections'].append({'id': section_id, 'bytes': size})
        if section_id in (1, 2, 3, 6, 7, 10):
            key = {1: 'declared_types', 2: 'declared_imports', 3: 'defined_functions',
                   6: 'declared_globals', 7: 'declared_exports', 10: 'code_bodies'}[section_id]
            result[key] = section.count()
        elif section_id in (4, 5):
            for _ in range(section.count()):
                if section_id == 4:
                    element_type = section.byte()
                    if element_type != 0x70:
                        raise ValueError('measurement supports funcref tables only')
                    result['tables'].append({'element_type': 'funcref', **section.limits()})
                else:
                    result['memories'].append(section.limits())
            section.end()
        elif section_id in (9, 11):
            for _ in range(section.count()):
                flags = section.uint()
                if flags not in (0, 2):
                    raise ValueError('measurement supports active index/data segments only')
                index = section.uint() if flags == 2 else 0
                offset = section.offset()
                if section_id == 9:
                    if flags == 2 and section.byte() != 0:
                        raise ValueError('measurement supports function-index elements only')
                    count = section.count()
                    for _ in range(count):
                        section.uint()
                    result['elements'].append({'flags': flags, 'table_index': index,
                                               'offset': offset, 'function_entries': count})
                else:
                    count = section.uint()
                    section.take(count)
                    result['data'].append({'flags': flags, 'memory_index': index,
                                           'offset': offset, 'bytes': count})
            section.end()
    return result


def source():
    files = [f for f in (ROOT / 'vm').rglob('*') if f.is_file()
             and not set(f.relative_to(ROOT / 'vm').parts) & {'target', 'verification', '__pycache__'}]
    files.append(ROOT / 'contracts/vm-profile-v1.json')
    return {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', default='verification/local/fieldlog-corpus-qualified/.build/wasm/wasm32-unknown-wasip1/release/fieldlog-corpus.wasm')
    args = parser.parse_args()
    corpus = (ROOT / args.corpus).resolve()
    if not corpus.is_file():
        raise FileNotFoundError('supply the pinned actual FieldLog artifact via --corpus; no substitute qualifies')
    data = corpus.read_bytes()
    corpus_hash = hashlib.sha256(data).hexdigest()
    if corpus_hash != CORPUS_SHA256:
        raise ValueError('FieldLog artifact identity differs from the measured pinned corpus')
    measured = structure(data)
    OUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PATH'] = '/opt/homebrew/opt/rustup/bin' + os.pathsep + env['PATH']
    commands = []

    def run(name, command, expected=0):
        command = list(map(str, command))
        result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        path = OUT / (name + '.log')
        # Preserve content; normalize trailing blank lines in checked-in text logs.
        path.write_text(result.stdout.rstrip() + '\n' if result.stdout else '')
        commands.append({'name': name, 'command': command, 'exit_code': result.returncode,
                         'output': str(path.relative_to(ROOT))})
        if result.returncode != expected:
            raise RuntimeError(name + ' failed: ' + result.stdout)
        print(name + ': passed', flush=True)
        return result.stdout

    start = source()
    for path, digest in FROZEN_PROFILES.items():
        if start[path] != digest:
            raise ValueError('frozen profile changed: ' + path)
    head = run('base-revision', ['git', 'rev-parse', 'HEAD']).strip()
    run('format', ['cargo', 'fmt', '--manifest-path', 'vm/Cargo.toml', '--', '--check'])
    unit = run('host-tests', ['cargo', 'test', '--manifest-path', 'vm/Cargo.toml'])
    passed = sum(map(int, re.findall(r'test result: ok\. (\d+) passed', unit)))
    integer = run('integer-oracle', ['cargo', 'test', '--manifest-path', 'vm/Cargo.toml',
                                    '--test', 'differential', '--', '--ignored', '--nocapture'])
    oracle_counts = {}
    for name, test, prefix in [('float', 'float_differential', 'numeric-v2'),
                               ('table-memory', 'table_memory_differential', 'table-memory-v3')]:
        for build in ['debug', 'release']:
            flags = ['--release'] if build == 'release' else []
            output = run(name + '-oracle-' + build, ['cargo', 'test', *flags, '--manifest-path',
                         'vm/Cargo.toml', '--test', test, '--', '--ignored', '--nocapture'])
            count = sum(map(int, re.findall(prefix + r' differential cases matched: (\d+)', output)))
            if not count:
                raise ValueError('oracle did not report cases')
            oracle_counts[name + '-' + build] = count
        if oracle_counts[name + '-debug'] != oracle_counts[name + '-release']:
            raise ValueError('debug/release oracle case counts differ')
    run('clippy', ['cargo', 'clippy', '--manifest-path', 'vm/Cargo.toml', '--all-targets', '--', '-D', 'warnings'])
    run('release-build', ['cargo', 'build', '--release', '--manifest-path', 'vm/Cargo.toml'])
    c_outputs = {}
    for name, file in [('integer', 'ffi_smoke.c'), ('numeric', 'ffi_numeric_smoke.c'),
                       ('table-memory', 'ffi_table_memory_smoke.c')]:
        executable = 'vm/target/ffi-' + name + '-smoke'
        run('c-' + name + '-build', ['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
            '-I', 'vm/include', 'vm/tests/' + file, 'vm/target/release/libmixer_vm.a', '-o', executable])
        c_outputs[name] = run('c-' + name + '-run', [executable]).strip()
    output = run('fieldlog-inventory', ['vm/target/release/mixer-vm', '--profile',
                 'mixer-table-memory-v3', 'inventory', corpus], expected=2)
    inventory = json.loads(output)
    if not inventory['inventory_complete'] or inventory['valid'] or inventory['error']['code'] != 'limit':
        raise ValueError('expected complete non-authorizing inventory and strict profile rejection')
    if hashlib.sha256(corpus.read_bytes()).hexdigest() != corpus_hash:
        raise ValueError('artifact changed during verification')
    (OUT / 'fieldlog-inventory.json').write_text(output)
    (OUT / 'fieldlog-structure.json').write_text(json.dumps(measured, indent=2) + '\n')
    versions = {name: run('version-' + name, cmd).strip() for name, cmd in {
        'cargo': ['cargo', '--version'], 'rustc': ['rustc', '--version'],
        'node': ['node', '--version'], 'clang': ['clang', '--version'],
        'python': ['python3', '--version'], 'macos': ['sw_vers'], 'architecture': ['uname', '-m']}.items()}
    finish = source()
    if start != finish:
        raise ValueError('source changed during verification; rerun from stable source')
    manifest = ''.join(f'{digest}  {path}\n' for path, digest in finish.items())
    (OUT / 'source-manifest.sha256').write_text(manifest)
    receipt = {
        'schema_version': 1, 'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'implementation_agent_selection': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'independent_review': False, 'base_revision_at_start': head,
        'source_tree_digest': hashlib.sha256(manifest.encode()).hexdigest(),
        'source_manifest': 'vm/verification/table-memory-v3/source-manifest.sha256',
        'source_scope': 'vm/** excluding target/verification/__pycache__ plus frozen contracts/vm-profile-v1.json',
        'frozen_profile_sha256': FROZEN_PROFILES,
        'command_environment': {'PATH_prefix': '/opt/homebrew/opt/rustup/bin'},
        'tool_versions': versions, 'commands': commands,
        'structural_measurement': {'command': ['python3', 'vm/verify-table-memory.py', '--corpus', str(corpus)],
            'output': 'vm/verification/table-memory-v3/fieldlog-structure.json', 'authorization': False},
        'results': {'host_tests_passed': passed,
            'integer_differential_execution_cases': sum(map(int, re.findall(r'differential cases matched: (\d+)', integer))),
            'oracle_case_counts': oracle_counts, 'c_abi_outputs': c_outputs,
            'format_and_clippy': 'passed',
            'old_profiles': 'frozen contracts unchanged; old-profile rejection unit/CLI/C tests pass',
            'v3': 'tables/active elements/indirect calls/copy/fill with bounds/type/control/fuel/depth/host-call/cancellation tests passed'},
        'fieldlog_corpus': {'path': os.path.relpath(corpus, ROOT), 'bytes': len(data), 'sha256': corpus_hash,
            'source_revision': '1587d2d4f02ab2dad9914df97f878727dd622296',
            'profile': inventory['profile'], 'valid': inventory['valid'],
            'inventory_complete': inventory['inventory_complete'], 'imports': len(inventory['imports']),
            'primary_opcodes': len(inventory['opcodes']),
            'instruction_occurrences': sum(x['count'] for x in inventory['opcodes']),
            'extended_opcodes': inventory['extended_opcodes'], 'rejection': inventory['error'],
            'owned_vm_execution_qualified': False,
            'remaining': ['source/function/global/instruction/memory budgets exceeded',
                          'all 34 WASI imports remain unsupported', 'bounded Swift runtime/SDK integration unqualified']},
        'qualified_execution_target': 'macOS arm64 development host only; no v3 physical-device claim',
        'open_gates': ['independent v3 review', 'standards suites', 'continuous coverage-guided fuzzing',
            'v3 physical iOS/Android embedding', 'non-default CPU/platform qualification',
            'remaining table/reference/bulk-memory forms as actually required', 'bounded WASI/Swift runtime adapters',
            'actual corpus resource budgets and owned-VM execution', 'Swift source maps/debugger',
            'FieldLog OTA coverage', 'W08/D3/GA']}
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'source_tree_digest': receipt['source_tree_digest'],
                      'host_tests_passed': passed, 'oracle_case_counts': oracle_counts,
                      'full_swift_qualified': False}, indent=2))


if __name__ == '__main__':
    main()
