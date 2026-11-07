#!/usr/bin/env python3
"""Offline byte preparation only; no compiler, runtime, OpenSSL or test launch."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import time

START = time.monotonic()
DEADLINE = START + 55
ROOT = Path(__file__).resolve().parents[2]
LANE = Path(__file__).resolve().parent
PREPARED = LANE / 'prepared-1'
ACCEPTED = ROOT / 'verification/console-key-owner-lifecycle-implementation/prepared-3'


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError('offline preparation exceeded 55 seconds')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            budget()
            block = stream.read(262144)
            if not block:
                return result.hexdigest()
            result.update(block)


def pin(path, relative=None):
    return {'path': str(path if relative is None else relative),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    if PREPARED.exists():
        raise ValueError('prepared-1 already exists; do not overwrite a frozen candidate')
    for file in ['prepare.py', 'runner.py', 'openssl-shim.py']:
        ast.parse((LANE / file).read_text(), filename=file)
    old = json.loads((ACCEPTED / 'execution-plan.json').read_text())
    old_members = {p['path']: p for p in old['prepared_files']}
    original = LANE / 'beforeimages/hosted/test/mixer_hosted/identity/key_owner_test.exs'
    before = json.loads((LANE / 'beforeimage.json').read_text())
    if digest(original) != before['sha256']:
        raise ValueError('original fixture helper bytes changed')
    PREPARED.mkdir()
    copied = []
    canonical = []

    def copy(source, relative, accepted_pin=None):
        budget()
        if accepted_pin is not None:
            actual = pin(source, accepted_pin['path'])
            if actual != accepted_pin:
                raise ValueError('accepted frozen input differs: ' + str(source))
        destination = PREPARED / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        copied.append(pin(destination, relative))

    # These exact accepted bytes intentionally exclude the actively edited
    # canonical KeyOwnerSupervisor and every other active product source.
    for source in old['source_roster']:
        relative = 'inputs/' + source
        copy(ACCEPTED / relative, relative, old_members[relative])
        canonical.append(pin(ACCEPTED / relative, str((ACCEPTED / relative).relative_to(ROOT))))
    test = 'hosted/test/mixer_hosted/identity/key_owner_test.exs'
    support = ['hosted/test/support/' + name for name in
               ['identity_tls_fixture.ex', 'identity_raw_fixture.ex', 'identity_dns_fixture.ex']]
    current = [test, *support, 'AGENTS.md', 'hosted/mix.lock', 'THIRD_PARTY.yml']
    for source in current:
        copy(ROOT / source, 'inputs/' + source)
        canonical.append(pin(ROOT / source, source))
    for name in ['runner.py', 'bootstrap.exs', 'prepare.py', 'README.md', 'beforeimage.json']:
        copy(LANE / name, name)
    copy(LANE / 'openssl-shim.py', 'tools/openssl')
    copy(original, 'beforeimages/' + test)
    diff = ''.join(difflib.unified_diff(original.read_text().splitlines(keepends=True),
                    (ROOT / test).read_text().splitlines(keepends=True),
                    fromfile='before/' + test, tofile='after/' + test))
    (PREPARED / 'canonical-change.diff').write_text(diff)
    copied.append(pin(PREPARED / 'canonical-change.diff', 'canonical-change.diff'))
    dependencies = []
    for dep in old['dependencies']:
        dependencies.append(dep)
        for item in dep['files']:
            relative = 'dependencies/' + dep['name'] + '/ebin/' + Path(item['path']).name
            copy(ACCEPTED / relative, relative, old_members[relative])
    tools = []
    for item in old['tools']:
        if pin(Path(item['path'])) != item:
            raise ValueError('accepted tool bytes differ: ' + item['path'])
        tools.append(item)
    openssl_root = Path('/opt/homebrew/Cellar/openssl@3/3.6.5')
    openssl_tools = {openssl_root / 'bin/openssl'}
    openssl_tools.update(p for p in (openssl_root / 'lib').rglob('*.dylib') if p.is_file())
    for library in ['libcrypto.3.dylib', 'libssl.3.dylib']:
        lexical = Path('/opt/homebrew/opt/openssl@3/lib') / library
        if lexical.resolve() != (openssl_root / 'lib' / library).resolve():
            raise ValueError('OpenSSL dynamic library symlink differs')
        openssl_tools.add(lexical)
    tools += [pin(path) for path in sorted(openssl_tools)]
    tools = sorted({p['path']: p for p in tools}.values(), key=lambda p: p['path'])
    sources = old['source_roster']
    if len(sources) != 18 or len(support) != 3:
        raise ValueError('exact source closure counts differ')
    bool_rule = lambda value=True: {'type': 'boolean', 'value': value}
    int_rule = lambda value: {'type': 'integer', 'value': value}
    string_rule = lambda value: {'type': 'string', 'value': value}
    tool = str(openssl_root / 'bin/openssl')
    schemas = {
        'schema': 1, 'required_artifacts': 8,
        'schemas': {
            'corrected/runtime.json': {
                'elixir': string_rule('1.20.4'), 'otp_release': string_rule('29'),
                'node': string_rule('nonode@nohost'), 'schedulers_online': int_rule(2),
                'product_application_started': bool_rule(False)},
            'corrected/exunit-result.json': {
                'total': int_rule(29), 'failures': int_rule(0),
                'skipped': int_rule(0), 'excluded': int_rule(22)},
            'corrected/selection.json': {
                'compiled_methods': int_rule(29), 'selected_methods': int_rule(7),
                'unselected_methods': int_rule(22), 'executed_methods': int_rule(7),
                'exact_names_present_once': bool_rule(), 'selection_is_full_suite': bool_rule(False)},
            'corrected/postconditions.json': {
                key: bool_rule() for key in ['fixture_owner_absent', 'fixture_workers_absent',
                    'fixture_admission_absent', 'default_owner_absent', 'default_repo_absent',
                    'product_application_not_started', 'ephemeral_fixture_key_directories_removed']}
        },
        'openssl_commands': [
            [tool, 'version'],
            [tool, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', '{fixture}/ca.key',
             '-out', '{fixture}/ca.pem', '-days', '1', '-subj', '/CN=Mixer Fixture CA'],
            [tool, 'req', '-new', '-newkey', 'rsa:2048', '-nodes', '-keyout', '{fixture}/leaf.key',
             '-out', '{fixture}/leaf.csr', '-subj', '/CN=jwks.fixture.invalid'],
            [tool, 'x509', '-req', '-in', '{fixture}/leaf.csr', '-CA', '{fixture}/ca.pem',
             '-CAkey', '{fixture}/ca.key', '-CAcreateserial', '-out', '{fixture}/leaf.pem',
             '-days', '1', '-extfile', '{fixture}/leaf.ext']
        ]
    }
    write(PREPARED / 'required-artifact-schemas.json', schemas)
    copied.append(pin(PREPARED / 'required-artifact-schemas.json', 'required-artifact-schemas.json'))
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                             text=True, check=True, timeout=min(3, DEADLINE - time.monotonic())).stdout.strip()
    if revision != 'fd92138ac0b8c4ecd0d872a9050204da5ceb5d2f':
        raise ValueError('root-provided source revision changed before freeze')
    canonical.sort(key=lambda p: p['path'])
    source_digest = hashlib.sha256(''.join(p['path'] + '\0' + str(p['bytes']) + '\0' + p['sha256'] + '\n'
                                         for p in canonical).encode()).hexdigest()
    plan = {
        'schema': 1, 'status': 'frozen-awaiting-independent-review-and-root-release-unexecuted',
        'created_at': datetime.now(timezone.utc).isoformat(), 'workspace_root': str(ROOT),
        'source_revision': revision, 'source_tree_sha256': source_digest,
        'source_tree_scope': 'Exact canonical_inputs byte closure; 18 accepted prepared-3 source files plus current test/support and scope documents; never active canonical product source.',
        'accepted_product_plan_sha256': digest(ACCEPTED / 'execution-plan.json'),
        'source_roster': sources, 'test_source': test, 'test_support': support,
        'canonical_inputs': canonical, 'prepared_files': sorted(copied, key=lambda p: p['path']),
        'dependencies': dependencies, 'tools': tools,
        'tool_version_expectations': {'elixir': '1.20.4', 'otp_release': '29',
            'erlang_package': '29.1.1_2', 'python': '3.14.8', 'openssl': '3.6.5',
            'elixir_otp_openssl_versions_observed_in_this_lane': False},
        'tool_pin_scope': 'Accepted executable/boot/Elixir/OTP/Python byte closure plus exact OpenSSL executable and package dynamic libraries. macOS system libraries and entropy are environment-owned.',
        'elixir': old['elixir'], 'boot': old['boot'],
        'environment': {**old['environment'],
            'PATH': '{scratch}/tools:/opt/homebrew/Cellar/erlang/29.1.1_2/bin:/usr/bin:/bin',
            'OPENSSL_CONF': '/dev/null',
            'OPENSSL_MODULES': str(openssl_root / 'lib/ossl-modules')},
        'environment_inherited': [],
        'phases': [{'id': 'corrected', 'bootstrap': 'bootstrap.exs', 'source_replacements': {},
            'expected': '19 frozen accepted product modules, three support modules and full canonical test module compile warning-free; seven included methods pass, 22 unselected methods excluded, no skipped tests; helper on_exit exact PID/table/name/pointer assertions pass; read-only formatting equality; local ephemeral TLS private keys removed.',
            'required_artifacts': ['runtime.json', 'exunit-result.json', 'selection.json', 'postconditions.json'] +
                                  ['openssl-%02d.json' % n for n in range(1, 5)]}],
        'selection': {'compiled_methods': 29, 'included_methods': 7, 'excluded_unselected_methods': 22,
            'include_filter': 'exclude [:test], include seven exact {:test, name_atom} filters; tag/name equality verified at runtime',
            'tests': [
                'K01 manifest limits and immutable identity transitions',
                'K08 cold storm single flight, admission and FIFO negative cache',
                'K08b eight configured profiles cannot open a fifth owned flight',
                'K09 actual HTTPS rotation and invalid-candidate retention',
                'K01b all-or-nothing versioned replacement and bounded churn tombstones',
                'K01 lifetime identity history survives expired cooldown tombstones',
                'K07g owner shutdown waits for suspended TLS controller cleanup']},
        'limits': {**old['limits'], 'openssl_seconds_per_command': 5, 'openssl_output_bytes_per_command': 8192},
        'execution': {'command': [str(Path(sys.executable).resolve()), '-B', str(PREPARED / 'runner.py'),
                                  '--release', '{root-authored-exact-plan-release.json}'],
            'output_directory': str(LANE / 'executions/candidate-1'), 'root_release_required': True,
            'single_execution': True, 'compiler_or_runtime_invocations_so_far': 0},
        'artifact_schemas': 'required-artifact-schemas.json',
        'cleanup': 'Each owner is a temporary ExUnit child started after its exact worker supervisor; infinity shutdown drains owner before worker teardown. on_exit contains only exact captured PID/table/name/pointer assertions. External runner retains only its newly created child process group; reaps it before removing exact owned scratch. No process inventory.',
        'scope': 'Host-only selected KeyOwnerTest fixture teardown correction, local loopback TLS/raw socket fixtures and ephemeral synthetic RSA keys. No Mix project or product application, Repo/database, provider endpoint, native instance, UI, capture, customer or operational qualification.',
        'pending': ['Independent review and separate root exact-plan runtime release',
            'Actual host compile/selected tests/formatting/OpenSSL execution',
            'Full default Phoenix CI after root delivery',
            'Native/UI/capture/physical-device checks remain paused; production and GA unqualified']
    }
    write(PREPARED / 'execution-plan.json', plan)
    members = [pin(path, str(path.relative_to(PREPARED))) for path in sorted(PREPARED.rglob('*')) if path.is_file()]
    write(PREPARED / 'freeze.json', {
        'schema': 1, 'status': 'frozen-unexecuted', 'sole_excluded_relative_path': 'freeze.json',
        'files': members, 'execution_plan_sha256': digest(PREPARED / 'execution-plan.json'),
        'tree_sha256': hashlib.sha256(''.join(p['path'] + '\0' + str(p['bytes']) + '\0' + p['sha256'] + '\n'
                                            for p in members).encode()).hexdigest(),
        'compiler_or_runtime_invocations': 0})
    print(json.dumps({'plan_sha256': digest(PREPARED / 'execution-plan.json'),
        'freeze_sha256': digest(PREPARED / 'freeze.json'), 'members': len(members),
        'tools': len(tools), 'selected': 7, 'unselected': 22,
        'elapsed_seconds': round(time.monotonic() - START, 6)}))


if __name__ == '__main__':
    main()
