#!/usr/bin/env python3
"""Selected additive SQL tests in one owned disposable PostgreSQL 17 instance."""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import tempfile
import uuid

REPO = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
PG = pathlib.Path('/opt/homebrew/opt/postgresql@17/bin').resolve()
ATTEMPT = BASE / 'attempts' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-') + uuid.uuid4().hex[:8])
ATTEMPT.mkdir(parents=True)
SOURCES = [
    'hosted/lib/mixer_hosted/browser_auth/storage_schema.ex',
    'hosted/lib/mixer_hosted/browser_auth/activation_preparation_schema.ex',
    'hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex',
    'hosted/lib/mixer_hosted/browser_auth/catalog.ex',
    'hosted/lib/mixer_hosted/browser_auth/catalog_manifest.ex',
    'hosted/lib/mixer_hosted/browser_auth/vault.ex',
    'hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex',
    'hosted/test/mixer_hosted/browser_auth/storage_fixture.exs',
    'hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs',
    'hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs',
    'hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs',
    'hosted/priv/repo/migrations/20261025000007_add_browser_sessions.exs',
    'hosted/mix.exs', 'hosted/mix.lock',
    'docs/hosted-browser-lifecycle-runtime-contract.md',
    'docs/hosted-browser-activation-preparation-sql.md',
    'verification/hosted-browser-activation-preparation-sql/run.py',
    'verification/hosted-browser-activation-preparation-sql/sql_test.exs',
]
# The hosted application's own ebin is deliberately excluded. Only ordinary
# allowlisted source below is compiled; locked general-purpose beams are reused.
DEPENDENCIES = sorted(p / 'ebin' for p in (REPO / 'hosted/_build/test/lib').iterdir()
                      if p.name != 'mixer_hosted' and (p / 'ebin').is_dir())
BEAMS = sorted(p for directory in DEPENDENCIES for p in directory.glob('*.beam'))
assert BEAMS, 'Existing dependency beams required; no broad build permitted'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest():
    return {'sources': {s: sha(REPO / s) for s in SOURCES},
            'dependency_beams': {str(p.relative_to(REPO)): sha(p) for p in BEAMS}}

before = manifest()
for source in SOURCES:
    target = ATTEMPT / 'inputs' / source
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / source, target)
(ATTEMPT / 'source-manifest.json').write_text(json.dumps(before, indent=2) + '\n')
commands = []
scratch = None
stopped = True
passed = False
revision = None

def run(name, command, env=None, timeout=30, check=True):
    command = [str(x) for x in command]
    p = subprocess.Popen(command, cwd=REPO, env=env, text=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
    timed_out = False
    try:
        output, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, signal.SIGKILL)
        output, _ = p.communicate(timeout=5)
    (ATTEMPT / (name + '.log')).write_text(output)
    commands.append({'name': name, 'command': command, 'timeout_seconds': timeout,
                     'timed_out': timed_out, 'exit_code': p.returncode, 'output': name + '.log'})
    if check and (p.returncode or timed_out):
        print(output[-20000:])
        raise RuntimeError(name + ' failed')
    return p.returncode, output

try:
    _, head = run('git-head', ['git', 'rev-parse', 'HEAD'])
    revision = head.strip()
    run('postgres-version', [PG / 'postgres', '--version'])
    run('elixir-version', ['elixir', '--version'])
    scratch = pathlib.Path(tempfile.mkdtemp(prefix='mixer-activation-preparation-'))
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    run('initdb', [PG / 'initdb', '-D', scratch / 'data', '-U', 'browser_admin', '-A', 'trust', '--no-locale', '-E', 'UTF8'])
    run('postgres-start', [PG / 'pg_ctl', '-D', scratch / 'data', '-l', ATTEMPT / 'postgres.log', '-o',
                          f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", '-w', 'start'], timeout=15)
    psql = [PG / 'psql', '-X', '-h', '127.0.0.1', '-p', port, '-U', 'browser_admin', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1']
    run('roles', psql + ['-c', '''CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;'''])
    run('database', [PG / 'createdb', '-h', '127.0.0.1', '-p', port, '-U', 'browser_admin', '-O', 'browser_schema_owner', 'browser_storage'])
    env = os.environ.copy()
    env['MIXER_BROWSER_STORAGE_PORT'] = str(port)
    env['MIXER_ACTIVATION_PREPARATION_OUTPUT'] = str(ATTEMPT)
    inputs = ATTEMPT / 'inputs'
    command = ['elixir']
    for directory in DEPENDENCIES:
        command += ['-pa', directory]
    for source in ['storage_schema.ex', 'activation_preparation_schema.ex', 'vault.ex',
                   'stored_snapshot.ex', 'activation_preparation.ex', 'catalog_manifest.ex', 'catalog.ex']:
        command += ['-r', inputs / 'hosted/lib/mixer_hosted/browser_auth' / source]
    runner = ATTEMPT / 'selected_runner.exs'
    runner.write_text('ExUnit.start(autorun: false, seed: 0, max_cases: 1)\n' +
                      'Code.require_file(' + json.dumps(str(inputs / 'verification/hosted-browser-activation-preparation-sql/sql_test.exs')) + ')\n' +
                      'r = ExUnit.run()\nFile.write!(' + json.dumps(str(ATTEMPT / 'tests.json')) + ', Jason.encode!(r))\n' +
                      'System.halt(if r.total >= 20 and r.failures == 0 and r.skipped == 0 and r.excluded == 0 and Map.get(r, :invalid, 0) == 0, do: 0, else: 1)\n')
    command += [runner]
    run('selected-exunit', command, env=env, timeout=60)
    passed = True
finally:
    if scratch is not None and (scratch / 'data/postmaster.pid').exists():
        code, _ = run('postgres-stop', [PG / 'pg_ctl', '-D', scratch / 'data', '-m', 'immediate', '-w', 'stop'], timeout=15, check=False)
        stopped = code == 0 and not (scratch / 'data/postmaster.pid').exists()
    if scratch is not None and stopped:
        shutil.rmtree(scratch)
    after = manifest()
    (ATTEMPT / 'source-manifest-after.json').write_text(json.dumps(after, indent=2) + '\n')
    receipt = {'version': 1, 'head': revision, 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_manifest': 'source-manifest.json', 'source_manifest_sha256': sha(ATTEMPT / 'source-manifest.json'),
               'source_unchanged': before == after, 'commands': commands,
               'selected_tests_passed': passed and before == after,
               'cleanup': {'owned_postgres_stopped': stopped, 'owned_scratch_removed': scratch is None or not scratch.exists()},
               'scope': 'Synthetic loopback PostgreSQL 17, additive activation preparation SQL only, selected ordinary 3/4/6/7 migrations and fixture, explicit sources plus locked dependency beams. No broad hosted harness or frozen lane, production wiring, provider, network custody, UI, capture or native runtime.',
               'pending': ['Independent review and combined version-2 catalog owner', 'Ordinary migration integration', 'ClaimOwner/current verifier/OIDC/provider composition', 'Neon/operator deployment', 'Customer browser and FieldLog qualification', 'Paused native and physical checks', 'GA acceptance']}
    (ATTEMPT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (BASE / 'latest.json').write_text(json.dumps({'mutable_pointer_only': True, 'attempt': str(ATTEMPT.relative_to(BASE))}, indent=2) + '\n')
    print(str(ATTEMPT.relative_to(REPO)))
if not passed or before != after or not stopped:
    raise SystemExit(1)
