#!/usr/bin/env python3
"""Offline preparation only; never launches Elixir, Mix, a compiler, or tests."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import ast
import hashlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

START = time.monotonic()
DEADLINE = START + 55
ROOT = Path(__file__).resolve().parents[2]
LANE = Path(__file__).resolve().parent
PREPARED = LANE / 'prepared-1'
CONTRACT = ROOT / 'verification/console-key-owner-lifecycle-contract'


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError('offline preparation exceeded 55 seconds')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            budget()
            value = stream.read(262144)
            if not value:
                return h.hexdigest()
            h.update(value)


def pin(path, relative=None):
    budget()
    return {'path': str(relative if relative is not None else path),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def strict(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key: ' + key)
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(), object_pairs_hook=strict,
                      parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def main():
    if PREPARED.exists():
        raise ValueError('prepared-1 already exists; immutable after preparation')
    amendment = CONTRACT / 'membership-amendment.json'
    if digest(amendment) != '6291f022b841804797a4431c6d3af9853fac4d11db549975b1386ea664ced5da':
        raise ValueError('selected contract amendment differs')
    packet = load(amendment)
    if len(packet['files']) != 33:
        raise ValueError('expected exact 33 contract members')
    if sorted(str(p.relative_to(CONTRACT)) for p in CONTRACT.rglob('*') if p.is_file()) != sorted(
            [item['path'] for item in packet['files']] + ['membership-amendment.json']):
        raise ValueError('contract membership differs')
    for item in packet['files']:
        if pin(CONTRACT / item['path'], item['path']) != item:
            raise ValueError('contract member differs: ' + item['path'])
    for path in ['key_owner.ex', 'admission.ex']:
        before = LANE / 'beforeimages/hosted/lib/mixer_hosted/identity' / path
        selected = CONTRACT / 'inputs/hosted/lib/mixer_hosted/identity' / path
        if before.read_bytes() != selected.read_bytes():
            raise ValueError('initial beforeimage differs: ' + path)
    for name in ['runner.py', 'prepare.py', 'audit.py']:
        ast.parse((LANE / name).read_text(), filename=name)
    PREPARED.mkdir()
    copied = []

    def copy(source, relative):
        budget()
        destination = PREPARED / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        copied.append(pin(destination, relative))

    sources = sorted(str(p.relative_to(ROOT)) for p in
                     (ROOT / 'hosted/lib/mixer_hosted/identity').glob('*.ex')
                     if p.name != 'startup_config.ex')
    if len(sources) != 18:
        raise ValueError('source closure must contain exactly 18 ordinary identity sources')
    test = 'hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs'
    canonical = sources + [test, 'hosted/mix.lock', 'THIRD_PARTY.yml', 'AGENTS.md']
    canonical += [str(p.relative_to(ROOT)) for p in
                  [amendment, CONTRACT / 'contract.md', CONTRACT / 'prospective-tests.json',
                   ROOT / 'verification/console-session-and-checkout-root-review/next-lifecycle-and-layout-selection.json']]
    for path in canonical:
        copy(ROOT / path, 'inputs/' + path)
    for file in ['runner.py', 'bootstrap.exs', 'bootstrap-original.exs', 'compile-common.exs',
                 'prepare.py', 'audit.py', 'README.md', 'beforeimage-check.json']:
        copy(LANE / file, file)
    replacements = {}
    for path in ['key_owner.ex', 'admission.ex']:
        source = 'hosted/lib/mixer_hosted/identity/' + path
        destination = 'beforeimages/' + source
        copy(LANE / destination, destination)
        replacements[source] = destination
    system_roots = Path('/etc/ssl/cert.pem')
    roots = system_roots.read_bytes()
    begin = roots.index(b'-----BEGIN CERTIFICATE-----')
    end = roots.index(b'-----END CERTIFICATE-----', begin) + len(b'-----END CERTIFICATE-----')
    selected_root = roots[begin:end] + b'\n'
    (PREPARED / 'root.pem').write_bytes(selected_root)
    copied.append(pin(PREPARED / 'root.pem', 'root.pem'))
    dependencies = []
    for name, version in [('decimal', '3.2.0'), ('jason', '1.4.5'), ('jose', '1.11.12'),
                          ('hpax', '1.1.0'), ('mint', '1.11.0')]:
        ebin = ROOT / 'hosted/_build/test/lib' / name / 'ebin'
        files = sorted(p for p in ebin.iterdir() if p.is_file())
        if not files or any(p.suffix not in ['.beam', '.app'] for p in files):
            raise ValueError('unexpected dependency ebin membership: ' + name)
        lock_entry = next(line.strip() for line in (ROOT / 'hosted/mix.lock').read_text().splitlines()
                          if line.strip().startswith('"' + name + '":'))
        if '"' + version + '"' not in lock_entry:
            raise ValueError('dependency lock version differs: ' + name)
        dependencies.append({'name': name, 'version': version, 'lock_entry': lock_entry,
                             'files': [pin(p, str(p.relative_to(ROOT))) for p in files]})
        for file in files:
            canonical.append(str(file.relative_to(ROOT)))
            copy(file, 'dependencies/' + name + '/ebin/' + file.name)
    elixir_root = Path('/opt/homebrew/Cellar/elixir/1.20.4/lib/elixir')
    erl_root = Path('/opt/homebrew/Cellar/erlang/29.1.1_2/lib/erlang')
    tools = {Path(sys.executable).resolve(),
             Path('/bin/sh'), Path('/usr/bin/dirname'), Path('/usr/bin/basename'), Path('/usr/bin/readlink'),
             elixir_root / 'bin/elixir', erl_root / 'bin/erl',
             erl_root / 'erts-17.1/bin/erlexec', erl_root / 'erts-17.1/bin/beam.smp',
             erl_root / 'erts-17.1/bin/erl_child_setup', erl_root / 'erts-17.1/bin/inet_gethost',
             erl_root / 'releases/29/OTP_VERSION', erl_root / 'bin/start_clean.boot',
             erl_root / 'bin/start_clean.script'}
    tools.update(p.resolve() for p in elixir_root.glob('lib/*/ebin/*') if p.is_file())
    for application in ['kernel', 'stdlib', 'compiler', 'public_key', 'crypto', 'asn1', 'ssl']:
        dirs = list((erl_root / 'lib').glob(application + '-*'))
        if len(dirs) != 1:
            raise ValueError('ambiguous OTP application path: ' + application)
        tools.update(p.resolve() for p in (dirs[0] / 'ebin').iterdir() if p.is_file())
        if (dirs[0] / 'priv/lib').exists():
            tools.update(p.resolve() for p in (dirs[0] / 'priv/lib').rglob('*') if p.is_file())
    for module in list(sys.modules.values()):
        file = getattr(module, '__file__', None)
        if file:
            path = Path(file).resolve()
            if path.is_file() and '/Python.framework/' in str(path):
                tools.add(path)
    python_library = Path(sys.executable).resolve().parent.parent / 'Python'
    if python_library.is_file():
        tools.add(python_library)
    canonical_pins = [pin(ROOT / path, path) for path in sorted(set(canonical))]
    selected_tree = hashlib.sha256(''.join(
        p['path'] + '\0' + str(p['bytes']) + '\0' + p['sha256'] + '\n'
        for p in canonical_pins).encode()).hexdigest()
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                              text=True, check=True, timeout=min(3, DEADLINE - time.monotonic())).stdout.strip()
    tree = subprocess.run(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, capture_output=True,
                          text=True, check=True, timeout=min(3, DEADLINE - time.monotonic())).stdout.strip()
    cleanups = ['KOL04-cleanup.json', 'KOL06-cleanup.json'] + [
        'Elixir.MixerHosted.Identity.KeyOwnerLifecycleTest.KOL' + number + 'Owner-cleanup.json'
        for number in ['01', '02', '03', '05', '07']]
    plan = {
        'schema': 1, 'status': 'frozen-awaiting-independent-root-review-no-runtime-release',
        'created_at': datetime.now(timezone.utc).isoformat(), 'workspace_root': str(ROOT),
        'source_revision': revision, 'source_git_tree': tree, 'source_tree_sha256': selected_tree,
        'source_tree_scope': 'Ordered exact canonical_inputs path, bytes and SHA256; current selected working-tree bytes, not all workspace files.',
        'source_roster': sources, 'test_source': test, 'canonical_inputs': canonical_pins,
        'prepared_files': sorted(copied, key=lambda x: x['path']),
        'dependencies': dependencies, 'tools': [pin(p) for p in sorted(tools)],
        'tool_version_expectations': {'elixir': '1.20.4', 'otp_release': '29', 'erlang_package': '29.1.1_2',
                                      'python': sys.version.split()[0], 'runtime_versions_observed': False},
        'tool_pin_scope': 'Selected executable, boot, Elixir ebin, relevant OTP ebin/NIF and loaded Python support bytes. macOS system shared libraries are environment-owned, not hermetically copied.',
        'elixir': str(elixir_root / 'bin/elixir'), 'boot': str(erl_root / 'bin/start_clean'),
        'environment': {'PATH': '/opt/homebrew/Cellar/erlang/29.1.1_2/bin:/usr/bin:/bin',
                        'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8', 'MIX_ENV': 'test',
                        'ERL_CRASH_DUMP': '/dev/null', 'ERL_CRASH_DUMP_SECONDS': '0'},
        'environment_inherited': [], 'root_certificate_provenance': {'source': str(system_roots),
            'source_sha256': digest(system_roots), 'selection': 'First complete PEM certificate, used only for valid disabled-profile initialization; no TLS connection.'},
        'phases': [
            {'id': 'original', 'bootstrap': 'bootstrap-original.exs', 'source_replacements': replacements,
             'expected': 'Exact original graceful-parent-stop defect reproduced; fail-closed dead pointer remains until this isolated VM exits.',
             'required_artifacts': ['runtime.json', 'original-regression.json', 'original-cleanup.json']},
            {'id': 'corrected', 'bootstrap': 'bootstrap.exs', 'source_replacements': {},
             'expected': 'Seven KOL01-KOL07 tests, zero failures/skipped/excluded, no compiler warnings, exact owned process and admission cleanup.',
             'required_artifacts': ['runtime.json', 'exunit-result.json', 'postconditions.json'] + cleanups}],
        'limits': {'total_seconds': 55, 'work_seconds': 40, 'cleanup_cutoff_seconds': 46,
                   'finalization_cutoff_seconds': 52, 'phase_output_bytes': 262144, 'combined_output_bytes': 524288,
                   'artifact_bytes': 16384},
        'execution': {'command': [str(Path(sys.executable).resolve()), '-B', str(PREPARED / 'runner.py'),
                                  '--release', '{root-authored-exact-plan-release.json}'],
                      'output_directory': str(LANE / 'executions/candidate-1'),
                      'root_release_required': True, 'single_execution': True, 'compiler_or_runtime_invocations_so_far': 0},
        'cleanup': 'Exact retained child PIDs and their newly created process groups only. Scratch deletion requires confirmed child reap and group absence; otherwise preserve scratch and fail. No process inventory, native instances, UI, capture or unrelated processes.',
        'scope': 'Socket-free host-only ordinary KeyOwnerSupervisor/Admission lifecycle with disabled profiles; original defect control followed by corrected KOL01-KOL07. No product application, fixture constructor, authentication success collaborator, database, provider fetch or network fixture.',
        'pending': ['Independent plan/runner/source review and separate root runtime release',
                    'Actual host compilation and original/corrected execution',
                    'KOL08 real flight/TLS drain and KOL09 active-flight worker-supervisor fault',
                    'Application startup/HTTP/browser/session/provider integration, production operation and GA',
                    'Native/UI/capture/physical devices remain paused'],
        'atomic_compare_and_erase_claim': False}
    write_json(PREPARED / 'execution-plan.json', plan)
    members = [pin(p, str(p.relative_to(PREPARED))) for p in sorted(PREPARED.rglob('*')) if p.is_file()]
    freeze = {'schema': 1, 'status': 'frozen-awaiting-independent-review-unexecuted',
              'sole_excluded_relative_path': 'freeze.json', 'files': members,
              'tree_sha256': hashlib.sha256(''.join(p['path'] + '\0' + str(p['bytes']) + '\0' + p['sha256'] + '\n' for p in members).encode()).hexdigest(),
              'execution_plan_sha256': digest(PREPARED / 'execution-plan.json'),
              'contract_amendment_sha256': digest(amendment), 'compiler_or_runtime_invocations': 0}
    write_json(PREPARED / 'freeze.json', freeze)
    print(json.dumps({'status': freeze['status'], 'plan_sha256': freeze['execution_plan_sha256'],
                      'freeze_sha256': digest(PREPARED / 'freeze.json'), 'members': len(members),
                      'sources': len(sources), 'dependency_apps': len(dependencies),
                      'tools': len(tools), 'elapsed_seconds': round(time.monotonic() - START, 6)}))


if __name__ == '__main__':
    main()
