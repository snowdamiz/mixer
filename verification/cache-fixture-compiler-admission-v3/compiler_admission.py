#!/usr/bin/env python3
"""File-only admission for one explicit remote rustup install and one v2 fixture.

The workflow owns process execution and its two-minute provisioning timeout.
This module never starts, discovers, signals, or waits on a process.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TOOLCHAIN = '1.98.1-aarch64-apple-darwin'
INSTALL_ARGV = ['rustup', 'toolchain', 'install', TOOLCHAIN,
                '--profile', 'minimal', '--no-self-update']


def need(value, message):
    if not value:
        raise RuntimeError(message)


def context(env):
    need(env.get('GITHUB_ACTIONS') == 'true', 'Remote GitHub Actions only')
    need(env.get('RUNNER_OS') == 'macOS' and env.get('RUNNER_ARCH') == 'ARM64',
         'Declared macOS ARM64 host required')
    need(env.get('GITHUB_RUN_ATTEMPT') == '1', 'No workflow rerun admitted')
    need(env.get('RUSTUP_TOOLCHAIN') == TOOLCHAIN
         and env.get('RUSTUP_AUTO_INSTALL') == '0', 'Exact compiler/no auto install required')
    need(env.get('RUSTUP_DIST_SERVER') == 'https://static.rust-lang.org'
         and env.get('RUSTUP_UPDATE_ROOT') == 'https://static.rust-lang.org/rustup',
         'Official Rust distribution endpoints required')
    run = env.get('GITHUB_RUN_ID', '')
    head = env.get('GITHUB_SHA', '')
    need(run.isascii() and run.isdigit() and len(head) == 40
         and all(c in '0123456789abcdef' for c in head), 'Run/revision identity required')
    temp = Path(env.get('RUNNER_TEMP', ''))
    need(temp.is_absolute() and '..' not in temp.parts, 'Absolute runner temporary root required')
    home = temp / ('mixer-fixture-rustup-' + run + '-1')
    need(env.get('RUSTUP_HOME') == str(home), 'Exact job-owned Rustup home required')
    return {'run_id': run, 'attempt': 1, 'head': head, 'toolchain': TOOLCHAIN,
            'rustup_home': str(home), 'install_argv': INSTALL_ARGV}


def no_symlinks(path):
    for part in [*reversed(path.parents), path]:
        need(not part.is_symlink(), 'Symlink forbidden: ' + str(part))


def read_json(path):
    no_symlinks(path)
    return json.loads(path.read_text())


def write_new(path, value):
    no_symlinks(path)
    with path.open('x') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')


def stream_bindings(logs):
    result = {}
    for name in ['rustup-version.stdout', 'rustup-version.stderr',
                 'rustup-install.stdout', 'rustup-install.stderr']:
        item = logs / name
        no_symlinks(item)
        need(item.is_file(), 'Missing regular provisioning output: ' + name)
        raw = item.read_bytes()
        result[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return result


def begin(env, logs):
    selected = context(env)
    no_symlinks(logs)
    need(logs.is_dir(), 'Existing owned evidence directory required')
    need(not (logs / 'provision-start.json').exists(), 'Provisioning already attempted')
    home = Path(selected['rustup_home'])
    no_symlinks(home)
    need(not home.exists(), 'Fresh job-owned Rustup home required')
    home.mkdir()
    write_new(logs / 'provision-start.json', {
        'schema': 1, 'context': selected, 'python': sys.version,
        'provisioning_step_minutes': 2, 'automatic_retries': 0,
        'descendant_custody': 'not independently observed',
        'toolchain_cleanup': 'retained in job-owned RUSTUP_HOME for runner disposal; disposal unverified'})
    return selected


def finish(env, logs, status):
    selected = context(env)
    start = read_json(logs / 'provision-start.json')
    need(start['context'] == selected, 'Provisioning context changed')
    need(type(status) is int and 0 <= status <= 255, 'Shell exit status required')
    streams = stream_bindings(logs)
    write_new(logs / 'provision-result.json', {
        'schema': 1, 'context': selected, 'install_exit': status,
        'install_command_returned_to_shell': True, 'streams': streams,
        'compiler_identity': 'pending unchanged v2 driver sysroot/version checks',
        'all_rustup_descendants_reaped': 'not established'})
    need(status == 0, 'Explicit Rustup install failed; fixture forbidden')
    return selected


def claim(env, logs):
    selected = context(env)
    need(read_json(logs / 'provision-start.json')['context'] == selected,
         'Provisioning start context changed')
    result = read_json(logs / 'provision-result.json')
    need(result['context'] == selected and result['install_exit'] == 0
         and result['install_command_returned_to_shell'] is True,
         'Successful explicit install required before fixture')
    need(result['streams'] == stream_bindings(logs), 'Provisioning evidence changed')
    write_new(logs / 'fixture-claim.json', {
        'schema': 1, 'context': selected, 'maximum_fixture_invocations': 1,
        'fixture_execution_observed': False,
        'scope': 'One launch admitted; actual completion is only in the unchanged v2 runner receipt'})
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['begin', 'finish', 'claim'])
    parser.add_argument('--status', type=int)
    args = parser.parse_args()
    logs = HERE / 'logs'
    if args.stage == 'begin':
        result = begin(os.environ, logs)
    elif args.stage == 'finish':
        result = finish(os.environ, logs, args.status)
    else:
        result = claim(os.environ, logs)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
