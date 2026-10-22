#!/usr/bin/env python3
"""Full Swift FieldLog size experiments. No production or owned-VM authorization."""
import sys
sys.dont_write_bytecode = True
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import tarfile
from analyze import wasm, link_map, object_data, initialized_contribution

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SWIFT = pathlib.Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
SDK_HOME = pathlib.Path('/Users/andreyyurlov/.swiftpm/swift-sdks')
SDK = SDK_HOME / 'swift-6.3.3-RELEASE_wasm.artifactbundle/swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1'
REVISION = '1587d2d4f02ab2dad9914df97f878727dd622296'
BASELINE_SHA = '3308fc08ae16bd7247be67b14bd7ea8af754c2610641d517936aa5570f325964'
ARCHIVE_SHA = '3f64fd8ff770a5f5e3a233d7170cccdc54c27ea0abb6a273948b260399e291eb'
HARNESS_SHA = '344168377051c105e60eb84388c54d48c2259224157ac68a1f877ac36a8e7c59'
helper_path = ROOT / 'compiler/qualification_support.py'
spec = importlib.util.spec_from_file_location('qualification_support', helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def identity(path):
    path = pathlib.Path(path)
    return {'path': os.path.relpath(path, ROOT), 'bytes': path.stat().st_size, 'sha256': helper.digest(path)}


def source_manifest():
    files = [HERE / name for name in ['DESIGN.md', 'run.py', 'analyze.py', 'test_analysis.py', 'oracle.mjs']]
    files.append(helper_path)
    return {str(path.relative_to(ROOT)): helper.digest(path) for path in files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='2026-10-22')
    parser.add_argument('--fieldlog', type=pathlib.Path, default='/Users/andreyyurlov/Documents/dev/fieldlog')
    parser.add_argument('--baseline', type=pathlib.Path, default=ROOT / 'verification/local/fieldlog-corpus-qualified/.build/wasm/wasm32-unknown-wasip1/release/fieldlog-corpus.wasm')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name, re.ASCII):
        parser.error('name must be a bounded ASCII path component')
    output = HERE / 'local' / args.name
    evidence = HERE / 'evidence' / args.name
    output.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    env = helper.clean_environment()
    env['DEVELOPER_DIR'] = '/Applications/Xcode_26.6.app/Contents/Developer'
    commands = []
    recorder = helper.CommandRecorder(evidence, commands, ROOT)
    start_sources = source_manifest()
    receipt = {'schema_version': 1, 'status': 'running', 'commands': commands,
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'implementation_agent_selection': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'independent_review': False, 'full_sdk': True, 'embedded_swift': False,
        'owned_vm_execution_qualified': False, 'device_or_ota_qualified': False,
        'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR'], 'ambient_tool_overrides': 'removed'},
        'timing_scope': 'Mac command wall time during concurrent development; no performance, p95, startup or RSS qualification',
        'variants': [], 'tools': {}, 'limitations': [
            'One actual model executable/harness, not a representative dogfood patch corpus or final MixerGuest feature module',
            'Host/Node model observations do not qualify all app behavior, UI/effects, physical embedding, or owned full Swift execution',
            'Strip-debug/all lose debugging information; original source maps/debugger remain unresolved',
            'Installed SDK/tool hashes identify observed inputs, not complete reproducible source-build or supply-chain attestation',
            'ICU data retained by the supported SDK is not proven individually needed by every exercised operation; no custom removal attempted']}

    def run(name, command, **kwargs):
        result = recorder.run(name, command, env=env, **kwargs)
        print(name + ': exit ' + str(commands[-1]['exitCode']), flush=True)
        return result

    def save(name, value):
        path = evidence / (name + '.json')
        path.write_text(json.dumps(value, indent=2) + '\n')
        return identity(path)

    def oracle(name, artifact):
        raw = run(name, [receipt['tools']['node']['path'], '--no-warnings', HERE / 'oracle.mjs', artifact])
        value = helper.model_observations(helper.strict_json(raw))
        stderr = (evidence / (name + '.stderr')).read_text()
        memory_lines = [line[15:] for line in stderr.splitlines() if line.startswith('PROFILE_MEMORY ')]
        if len(memory_lines) != 1:
            raise ValueError('missing/duplicate oracle memory observation')
        return value, helper.strict_json(memory_lines[0])

    sdk_inputs = {}
    try:
        git = shutil.which('git', path=env['PATH'])
        node = shutil.which('node', path=env['PATH'])
        python = pathlib.Path(sys.executable)
        llvm = SWIFT.parent
        tools = {'swift': SWIFT, 'node': node, 'git': git, 'python': python,
                 'wasm_ld': llvm / 'wasm-ld', 'objcopy': llvm / 'llvm-objcopy',
                 'ar': llvm / 'llvm-ar', 'objdump': llvm / 'llvm-objdump'}
        receipt['tools'] = {name: helper.tool_identity(path) for name, path in tools.items()}
        for name, args0 in [('swift-help', [SWIFT, 'build', '--help']), ('compiler-help', [llvm / 'swiftc', '-help']),
                            ('linker-help', [llvm / 'wasm-ld', '--help'])]:
            run(name, args0)
        receipt['versions'] = {name: run('version-' + name, [path, '--version']).strip()
                               for name, path in tools.items() if name in ['swift', 'node', 'objcopy', 'wasm_ld', 'python']}
        receipt['host'] = {'os': run('host-os', ['/usr/bin/sw_vers']).strip(),
                           'architecture': run('host-architecture', ['/usr/bin/uname', '-m']).strip()}
        run('measurement-tests', [python, '-B', '-m', 'unittest', 'discover', '-s', HERE, '-p', 'test_analysis.py', '-v'])
        receipt['mixer_base_revision'] = run('mixer-revision', [git, 'rev-parse', 'HEAD']).strip()
        baseline = args.baseline.absolute()
        if helper.digest(baseline) != BASELINE_SHA:
            raise ValueError('pristine baseline hash differs')
        receipt['pristine_baseline'] = identity(baseline)
        expected, memory = oracle('pristine-baseline-oracle', baseline)
        receipt['expected_model_observations'] = expected
        receipt['pristine_baseline_memory'] = memory
        receipt['fieldlog_revision'] = run('fieldlog-revision', [git, '-C', args.fieldlog.absolute(), 'rev-parse', '--verify', '--end-of-options', REVISION + '^{commit}']).strip()
        if receipt['fieldlog_revision'] != REVISION:
            raise ValueError('source revision mismatch')
        archive = output / 'fieldlog-source.tar'
        run('fieldlog-export', [git, '-C', args.fieldlog.absolute(), 'archive', '--format=tar', '--output=' + str(archive), REVISION])
        if helper.digest(archive) != ARCHIVE_SHA:
            raise ValueError('immutable source archive mismatch')
        package = output / 'package'
        package.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(package / 'fieldlog', filter='data')
        source_paths = sorted(path for path in (package / 'fieldlog').rglob('*') if path.is_file())
        source_hashes = {str(path.relative_to(package / 'fieldlog')): helper.digest(path) for path in source_paths}
        save('fieldlog-source-manifest', source_hashes)
        harness = package / 'Sources/FieldLogCorpus/main.swift'
        harness.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / 'compiler/Fixtures/FieldLogCorpus/main.swift', harness)
        if helper.digest(harness) != HARNESS_SHA:
            raise ValueError('established harness changed')
        shutil.copyfile(ROOT / 'verification/local/fieldlog-corpus-qualified/Package.swift', package / 'Package.swift')
        receipt['source_inputs'] = {'archive': identity(archive), 'harness': identity(harness), 'package': identity(package / 'Package.swift')}
        sdk_files = [SDK_HOME / 'swift-6.3.3-RELEASE_wasm.artifactbundle/info.json', SDK / 'swift-sdk.json', SDK / 'toolset.json',
                     SDK / 'swift.xctoolchain/usr/lib/swift_static/wasi/static-executable-args.lnk']
        sdk_inputs.update({str(path): helper.digest(path) for path in sdk_files})
        native_scratch = output / 'build-native'
        run('native-build', [SWIFT, 'build', '--package-path', package, '--scratch-path', native_scratch, '-c', 'release', '-j', '4'], timeout=300)
        native = native_scratch / 'release/fieldlog-corpus'
        observed = helper.model_observations(helper.strict_json(run('native-run', [native])))
        if observed != expected:
            raise ValueError('native model observations differ from pristine baseline')
        receipt['native_binary'] = identity(native)
        receipt['native_observation_comparison'] = 'exact full object matched pristine Wasm baseline'
        vm_source = ROOT / 'vm/target/release/mixer-vm'
        vm_before = helper.tool_identity(vm_source)
        vm = output / 'mixer-vm'
        shutil.copyfile(vm_source, vm); vm.chmod(0o500)
        if helper.digest(vm) != vm_before['sha256'] or helper.tool_identity(vm_source) != vm_before:
            raise ValueError('VM snapshot changed while copying')
        receipt['owned_vm_snapshot'] = {'source': vm_before, 'snapshot': helper.tool_identity(vm), 'authorization': False}

        def inspect_variant(name, artifact, flags, link=None):
            data = artifact.read_bytes()
            compressed = gzip.compress(data, compresslevel=9, mtime=0)
            gz = output / (name + '.wasm.gz')
            gz.write_bytes(compressed)
            measured = wasm(data)
            value, memory = oracle(name + '-oracle', artifact)
            if value != expected:
                raise ValueError(name + ' model observation mismatch')
            inventory = helper.strict_json(run(name + '-inventory', [vm, '--profile', 'mixer-table-memory-v3', 'inventory', artifact], expected=(0, 2)))
            if inventory['valid'] or not inventory['inventory_complete'] or commands[-1]['exitCode'] != 2:
                raise ValueError('expected complete non-authorizing inventory and strict rejection')
            result = {'name': name, 'artifact': identity(artifact), 'gzip9_mtime0': identity(gz), 'flags': flags,
                'behavior': 'exact established full observation object matched native and pristine baseline',
                'observations': value, 'linear_memory': memory,
                'structure': save(name + '-structure', measured),
                'summary': {'defined_functions': measured['defined_functions'], 'globals': measured['globals'],
                    'active_data_bytes': measured['active_data_bytes'], 'initial_pages': measured['memories'][0]['minimum'],
                    'maximum_pages': measured['memories'][0]['maximum'], 'table_minimum': measured['tables'][0]['minimum'],
                    'instructions': sum(item['count'] for item in inventory['opcodes']), 'imports': len(inventory['imports']),
                    'custom_sections': [item['name'] for item in measured['sections'] if item['id'] == 0]},
                'strict_owned_profile': {'profile': inventory['profile'], 'valid': inventory['valid'], 'error': inventory['error'], 'authorization': False}}
            if link:
                attribution = link_map(link.read_text())
                result['link_map'] = identity(link)
                result['attribution'] = save(name + '-attribution', attribution)
                for item in attribution['archives_and_objects']:
                    path = pathlib.Path(item['input'])
                    if path.is_file() and SDK_HOME in path.parents:
                        sdk_inputs[str(path)] = helper.digest(path)
                if name == 'release':
                    icu = next(item for item in attribution['largest_initialized_data_inputs'] if '.rodata.icudt76_dat' in item['input'])
                    blob, payload_offset = initialized_contribution(data, measured, icu)
                    receipt['icu_linked_data'] = {**icu, 'actual_payload_file_offset': payload_offset,
                        'offset_scope': 'linear-memory VMA mapped through binary active segment; linker-reported DATA file offset is diagnostic only',
                        'sha256': hashlib.sha256(blob).hexdigest(),
                        'gzip9_mtime0_bytes': len(gzip.compress(blob, compresslevel=9, mtime=0)),
                        'assessment': 'retained immutable supported-SDK packaged locale data; not proved individually required or safely removable'}
            receipt['variants'].append(result)
            print(json.dumps({'variant': name, 'bytes': len(data), 'gzip9': len(compressed), 'initial_pages': measured['memories'][0]['minimum']}), flush=True)
            return result

        inspect_variant('pristine', baseline, ['pre-existing unmodified release artifact'])
        size_flags = ['-Xswiftc', '-Osize', '-Xswiftc', '-gnone', '-Xswiftc', '-whole-module-optimization']
        variants = [('release', []), ('osize', size_flags),
            ('osize-gc', size_flags + ['-Xlinker', '--gc-sections']),
            ('osize-link-strip-debug', size_flags + ['-Xlinker', '--strip-debug']),
            ('osize-link-strip-all', size_flags + ['-Xlinker', '--strip-all']),
            ('osize-compress', size_flags + ['-Xlinker', '--strip-all', '-Xlinker', '--compress-relocations'])]
        builds = {}
        for name, flags in variants:
            scratch = output / ('build-' + name)
            link = output / (name + '.map')
            why = output / (name + '.why-extract.tsv')
            command = [SWIFT, 'build', '--package-path', package, '--scratch-path', scratch,
                '--swift-sdks-path', SDK_HOME, '--swift-sdk', 'swift-6.3.3-RELEASE_wasm', '-c', 'release', '-j', '4', '-v',
                '-Xlinker', '--Map=' + str(link), '-Xlinker', '--why-extract=' + str(why), *flags]
            if name == 'release':
                command.extend(['-Xlinker', '--trace-symbol=icudt76_dat'])
            build_output = run(name + '-build', command, timeout=300)
            artifact = scratch / 'wasm32-unknown-wasip1/release/fieldlog-corpus.wasm'
            result = inspect_variant(name, artifact, flags, link)
            result['why_extract'] = identity(why)
            lines = why.read_text().splitlines()
            save(name + '-icu-extraction', {'header': lines[0],
                'matching_chain_rows': [line for line in lines[1:] if 'icu_packaged_data' in line or 'icudt76_dat' in line],
                'symbol_trace_rows': [line for line in build_output.splitlines() if 'icudt76_dat' in line and '--trace-symbol' not in line]})
            builds[name] = artifact
            if name in ('release', 'osize'):
                for mode in ['debug', 'all']:
                    dest = output / (name + '-objcopy-strip-' + mode + '.wasm')
                    run(name + '-objcopy-' + mode, [tools['objcopy'], '--strip-' + mode, artifact, dest])
                    inspect_variant(name + '-objcopy-' + mode, dest, ['llvm-objcopy --strip-' + mode, 'source: ' + name])
        # Explicit failed ceiling experiment, never treated as an executable candidate.
        run('four-mib-limit-build', [SWIFT, 'build', '--package-path', package, '--scratch-path', output / 'build-four-mib-limit',
            '--swift-sdks-path', SDK_HOME, '--swift-sdk', 'swift-6.3.3-RELEASE_wasm', '-c', 'release', '-j', '4',
            *size_flags, '-Xlinker', '--max-memory=4194304'], expected=(1,), timeout=300)
        receipt['four_mib_memory_ceiling'] = 'link rejected; exact diagnostic retained; no budget relaxation'
        # Independently identify the SDK packaged data, without modifying/rebuilding the SDK.
        icu_archive = SDK / 'swift.xctoolchain/usr/lib/swift_static/wasi/lib_FoundationICU.a'
        sdk_inputs[str(icu_archive)] = helper.digest(icu_archive)
        # llvm-ar p writes binary to stdout, so use the owned runner's streamed evidence file.
        run('icu-member-list', [tools['ar'], 't', icu_archive])
        icu_obj = output / 'icu_packaged_data.cpp.obj'
        import subprocess
        command = [str(tools['ar']), 'p', str(icu_archive), 'icu_packaged_data.cpp.obj']
        with icu_obj.open('xb') as stream:
            process = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.PIPE, timeout=30)
        if process.returncode:
            raise ValueError('official archive extraction failed')
        receipt['icu_archive_extraction'] = {'command': command, 'exit_code': process.returncode,
            'archive': identity(icu_archive), 'object': identity(icu_obj)}
        # llvm-objdump exposes DATA as a core section; the input contribution's
        # .rodata name is not a separate section that llvm-objcopy can dump.
        run('icu-object-sections', [tools['objdump'], '-h', icu_obj])
        run('icu-named-dump-unsupported', [tools['objcopy'],
            '--dump-section=.rodata.icudt76_dat=' + str(output / 'unsupported.bin'), icu_obj], expected=(1,))
        if identity(icu_obj) != receipt['icu_archive_extraction']['object']:
            raise ValueError('inspection changed the extracted archive object')
        object_bytes = icu_obj.read_bytes()
        segments = object_data(object_bytes)
        if len(segments) != 1 or segments[0]['sha256'] != receipt['icu_linked_data']['sha256']:
            raise ValueError('SDK object data does not match retained linked immutable payload')
        segment = segments[0]
        dump = output / 'icu-data.bin'
        dump.write_bytes(object_bytes[segment['file_offset']:segment['file_offset'] + segment['bytes']])
        receipt['icu_linked_data']['object_measurement'] = segments
        receipt['icu_linked_data']['object_extraction_scope'] = 'bounded owned metadata reader of official llvm-ar member; exact data hash equals linked contribution; not executable validation'
        receipt['icu_linked_data']['sdk_object_payload'] = identity(dump)
        receipt['sdk_inputs'] = [{'path': key, 'sha256': digest} for key, digest in sorted(sdk_inputs.items())]
        for path, digest in sdk_inputs.items():
            if helper.digest(path) != digest:
                raise ValueError('SDK input changed during experiment')
        for name, tool in receipt['tools'].items():
            if helper.tool_identity(tool['path']) != tool:
                raise ValueError(name + ' tool changed during experiment')
        for result in receipt['variants']:
            for key in ['artifact', 'gzip9_mtime0']:
                if identity(ROOT / result[key]['path']) != result[key]:
                    raise ValueError(result['name'] + ' artifact changed during experiment')
        if any(helper.digest(package / 'fieldlog' / path) != digest for path, digest in source_hashes.items()):
            raise ValueError('exported FieldLog source changed during experiment')
        if helper.digest(baseline) != BASELINE_SHA or helper.digest(harness) != HARNESS_SHA:
            raise ValueError('baseline/harness changed during experiment')
        if source_manifest() != start_sources:
            raise ValueError('experiment source changed during run')
        receipt['experiment_source_manifest'] = save('experiment-source-manifest', start_sources)
        receipt['experiment_source_digest'] = hashlib.sha256(json.dumps(start_sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        smallest = min(receipt['variants'], key=lambda value: value['gzip9_mtime0']['bytes'])
        receipt['smallest_measured_variant'] = smallest['name']
        receipt['budget_comparison'] = {'scope': 'single complete model executable diagnostics, not p95 patch corpus or app RSS',
            'compressed_target_bytes': 3 * 1024 * 1024, 'smallest_gzip9_bytes': smallest['gzip9_mtime0']['bytes'],
            'over_target_bytes': smallest['gzip9_mtime0']['bytes'] - 3 * 1024 * 1024,
            'ratio_to_target': smallest['gzip9_mtime0']['bytes'] / (3 * 1024 * 1024),
            'initial_linear_memory_bytes': smallest['linear_memory']['beforeStartBytes'],
            'linear_memory_after_corpus_bytes': smallest['linear_memory']['afterStartBytes'],
            'added_ota_rss_budget_bytes': 30 * 1024 * 1024,
            'rss_qualified': False, 'vm_ceilings_changed': False}
        receipt['status'] = 'model-observations-matched-all-executable-variants; package/runtime gaps remain'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['failure'] = str(error)
        raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'smallest': receipt['smallest_measured_variant'],
                      'budget_comparison': receipt['budget_comparison']}, indent=2))


if __name__ == '__main__':
    main()
