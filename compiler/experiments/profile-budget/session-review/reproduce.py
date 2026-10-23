#!/usr/bin/env python3
"""Run the frozen independent allocation-lifetime test on an immutable VM export."""
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
spec = importlib.util.spec_from_file_location('qualification_support', ROOT / 'compiler/qualification_support.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    parser.add_argument('--expect', choices=['quota-race', 'pass'], required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.revision, re.ASCII):
        raise ValueError('use a full frozen commit SHA')
    output = HERE.parent / 'local' / ('session-review-' + args.revision)
    evidence = HERE / 'evidence' / args.revision
    output.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    commands = []
    recorder = helper.CommandRecorder(evidence, commands, ROOT)
    env = helper.clean_environment()
    env['PATH'] = '/opt/homebrew/opt/rustup/bin' + os.pathsep + env['PATH']
    git = shutil.which('git', path=env['PATH'])
    cargo = shutil.which('cargo', path=env['PATH'])
    rustc = shutil.which('rustc', path=env['PATH'])
    record = {'schema_version': 1, 'status': 'running', 'revision': args.revision,
        'reviewer_selection': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'independent_of_session_implementation': True,
        'scope': 'host allocation-lifetime adversarial review; no device or full Swift qualification',
        'expected': args.expect, 'commands': commands,
        'source_rule': 'git archive frozen production source; add only this original independent integration test under a new name; no existing source edits'}
    def run(name, command, **kwargs):
        value = recorder.run(name, command, env=env, **kwargs)
        print(name + ': exit ' + str(commands[-1]['exitCode']), flush=True)
        return value
    try:
        revision = run('revision', [git, 'rev-parse', '--verify', '--end-of-options', args.revision + '^{commit}']).strip()
        if revision != args.revision:
            raise ValueError('revision differs')
        archive = output / 'source.tar'
        run('export', [git, 'archive', '--format=tar', '--output=' + str(archive), args.revision, 'vm', 'contracts'])
        record['source_archive_sha256'] = helper.digest(archive)
        with tarfile.open(archive) as stream:
            stream.extractall(output / 'source', filter='data')
        source = output / 'source/vm'
        test = HERE / 'review_session_lifetime.rs'
        before = {str(path.relative_to(source)): helper.digest(path) for path in source.rglob('*') if path.is_file()}
        shutil.copyfile(test, source / 'tests/independent_session_lifetime.rs')
        record['test_sha256'] = helper.digest(test)
        record['tool_versions'] = {name: run('version-' + name, [path, '--version']).strip()
                                  for name, path in [('cargo', cargo), ('rustc', rustc)]}
        for build in ['debug', 'release']:
            flags = ['--release'] if build == 'release' else []
            expected = 101 if args.expect == 'quota-race' else 0
            run(build + '-repro', [cargo, 'test', *flags, '--manifest-path', source / 'Cargo.toml',
                '--target-dir', output / 'target', '--test', 'independent_session_lifetime', '--', '--nocapture'], expected=(expected,))
            text = (evidence / (build + '-repro.stdout')).read_text() + (evidence / (build + '-repro.stderr')).read_text()
            if args.expect == 'quota-race':
                if 'left: 0' not in text or 'right: 3' not in text or 'test result: FAILED. 0 passed; 1 failed' not in text:
                    raise ValueError('failure did not match allocation-ceiling regression')
            elif 'test result: ok. 1 passed' not in text:
                raise ValueError('fixed source did not pass the exact original test')
        if any(helper.digest(source / path) != digest for path, digest in before.items()):
            raise ValueError('frozen production source changed')
        record['source_manifest'] = {str(path.relative_to(ROOT)): helper.digest(path) for path in
            [pathlib.Path(__file__), test, ROOT / 'compiler/qualification_support.py']}
        record['status'] = 'quota-race reproduced in debug and release' if args.expect == 'quota-race' else 'original allocation-lifetime regression passed in debug and release'
    except Exception as error:
        record['status'] = 'failed'
        record['failure'] = str(error)
        raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'revision': args.revision, 'status': record['status'], 'test_sha256': record['test_sha256']}))


if __name__ == '__main__':
    main()
