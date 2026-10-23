#!/usr/bin/env python3
"""Independent, host-only activation review against hashed source snapshots."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('qualification_support', ROOT / 'compiler/qualification_support.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
VM_REVISION = '64123c509e861ddd522631b293eadebdaca11341'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='2026-10-22')
    parser.add_argument('--revision', help='optional immutable integrated activation commit')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name, re.ASCII):
        raise ValueError('bounded ASCII label required')
    work = HERE / '.build' / args.name
    evidence = HERE / 'evidence' / args.name
    work.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    env = helper.clean_environment()
    env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env['PATH']
    commands = []
    recorder = helper.CommandRecorder(evidence, commands, ROOT)
    record = {'schema': 1, 'status': 'running', 'reviewer': {'model': 'gpt-6.1-sol', 'reasoning': 'xhigh'},
              'scope': 'independent read-only source review and original host adversarial probes; no device or full Swift execution claim',
              'commands': commands, 'vm_revision': VM_REVISION}
    def run(name, command, **kwargs):
        result = recorder.run(name, command, env=env, **kwargs)
        print(name + ': exit ' + str(commands[-1]['exitCode']), flush=True)
        return result
    try:
        record['base_commit'] = run('base-commit', [shutil.which('git', path=env['PATH']), 'rev-parse', 'HEAD']).strip()
        source = work / 'source'
        input_root = ROOT
        if args.revision:
            git = shutil.which('git', path=env['PATH'])
            revision = run('reviewed-commit', [git, 'rev-parse', args.revision + '^{commit}']).strip()
            archive = work / 'reviewed-source.tar'
            run('reviewed-export', [git, 'archive', '--format=tar', '--output=' + str(archive), revision,
                                    'activation', 'runtime', 'updates'])
            record['reviewed_commit'] = revision
            record['reviewed_archive_sha256'] = helper.digest(archive)
            input_root = work / 'exported'
            with tarfile.open(archive) as stream:
                stream.extractall(input_root, filter='data')
        manifest = {}
        for package in ('activation', 'runtime', 'updates'):
            for relative in ('Package.swift', 'Package.resolved', 'Sources', 'Tests'):
                original = input_root / package / relative
                if not original.exists():
                    continue
                files = sorted(original.rglob('*')) if original.is_dir() else [original]
                for file in files:
                    if not file.is_file():
                        continue
                    key = str(file.relative_to(input_root))
                    destination = source / key
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(file, destination)
                    manifest[key] = helper.digest(destination)
        # No production code is changed in the snapshot; only one new test file is added.
        review = source / 'activation/Tests/MixerActivationTests/IndependentReview.swift'
        shutil.copyfile(HERE / 'ReviewTests.swift', review)
        record['source_manifest'] = manifest
        record['source_digest'] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        record['original_review_test_sha256'] = helper.digest(review)
        record['runner_sha256'] = helper.digest(Path(__file__))
        record['helper_sha256'] = helper.digest(ROOT / 'compiler/qualification_support.py')
        run('build-fixed-vm', [sys.executable, '-B', ROOT / 'runtime/build-vm.py', '--revision', VM_REVISION,
                              '--target', 'host', '--output', work / 'native-vm'], timeout=300)
        vm = helper.strict_json((work / 'native-vm/receipt.json').read_text())
        record['vm_build'] = vm
        shutil.copyfile(work / 'native-vm/receipt.json', evidence / 'vm-build-receipt.json')
        shutil.copyfile(work / 'native-vm/build.log', evidence / 'vm-build.log')
        record['swift'] = run('swift-version', ['/usr/bin/xcrun', 'swift', '--version']).strip()
        record['os'] = run('host-os', ['/usr/bin/sw_vers']).strip()
        command = ['/usr/bin/xcrun', 'swift', 'test', '--build-system', 'native', '--package-path', source / 'activation',
                   '--scratch-path', work / 'swift-build', '-Xlinker', '-L' + str(work / 'native-vm/lib')]
        run('baseline-tests', command + ['--skip', 'IndependentActivationReview'], timeout=300)
        run('independent-tests', command + ['--filter', 'IndependentActivationReview'], timeout=180)
        for name in ('baseline-tests', 'independent-tests'):
            text = (evidence / (name + '.stdout')).read_text() + (evidence / (name + '.stderr')).read_text()
            found = re.findall(r'Test run with (\d+) tests?.*?passed', text)
            if len(found) != 1:
                raise ValueError('missing successful Swift Testing count in ' + name)
            record[name + '_function_count'] = int(found[0])
            parameter_counts = [int(value) for value in re.findall(r'with (\d+) test cases passed', text)]
            record[name + '_case_count'] = int(found[0]) + sum(value - 1 for value in parameter_counts)
        for key, digest in manifest.items():
            if helper.digest(source / key) != digest:
                raise ValueError('frozen source changed while reviewed: ' + key)
        if helper.digest(review) != record['original_review_test_sha256']:
            raise ValueError('review tests changed during execution')
        record['source_files_changed_on_live_tree_since_snapshot'] = [key for key, digest in manifest.items()
            if not (ROOT / key).exists() or helper.digest(ROOT / key) != digest]
        record['status'] = 'host baseline and original adversarial tests passed; findings documented separately'
    except Exception as error:
        record['status'] = 'failed'
        record['failure'] = str(error)
        raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({k: record[k] for k in ('status', 'source_digest', 'baseline-tests_function_count', 'baseline-tests_case_count', 'independent-tests_function_count', 'independent-tests_case_count')}, indent=2))


if __name__ == '__main__':
    main()
