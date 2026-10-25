#!/usr/bin/env python3
"""Actual additive Ecto migration/operator upgrade, selected PostgreSQL17 only."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PG = Path('/opt/homebrew/opt/postgresql@17/bin').resolve()
DEPS = ['telemetry', 'decimal', 'db_connection', 'ecto', 'ecto_sql', 'postgrex', 'jason', 'oban']
BROWSER = 'hosted/lib/mixer_hosted/browser_auth/'
MODULES = [BROWSER + n for n in ['storage_schema.ex', 'activation_preparation_schema.ex',
    'catalog_manifest.ex', 'catalog_manifest_v2.ex', 'catalog.ex']] + ['hosted/lib/mixer_hosted/customer_artifacts/schema.ex']
MIGRATIONS = ['20261024000000_add_oban.exs', '20261025000000_add_build_journals.exs',
    '20261025000001_add_build_admission.exs', '20261025000002_add_build_aggregate_limits.exs',
    '20261025000003_add_customer_authorization.exs', '20261025000004_add_authorization_state_revisions.exs',
    '20261025000005_add_customer_artifact_storage.exs', '20261025000006_add_customer_workspace_discovery.exs',
    '20261025000007_add_browser_sessions.exs', '20261025000008_add_browser_activation_preparation.exs']
TEST = 'verification/hosted-browser-activation-preparation-migration/operator_upgrade_test.exs'
SOURCES = MODULES + [BROWSER + 'activation_preparation.ex',
    'hosted/test/mixer_hosted/browser_auth/storage_fixture.exs',
    'hosted/test/mixer_hosted/browser_auth/migration_spec.exs',
    'hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py',
    'docs/hosted-browser-lifecycle-runtime-contract.md', 'hosted/mix.lock',
    'docs/hosted-browser-activation-preparation-migration.md',
    'verification/hosted-browser-activation-preparation-migration/run.py', TEST]
SOURCES += ['hosted/priv/repo/migrations/' + n for n in MIGRATIONS]
SOURCES += ['hosted/test/foundation_integration_test.exs'] + [
    f'hosted/test/mixer_hosted/builds/{name}_test.exs' for name in ['admission', 'coordinator', 'aggregate_admission']]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-') + uuid.uuid4().hex[:8]
    out = BASE / 'operator-attempts' / stamp
    inputs = out / 'inputs'
    inputs.mkdir(parents=True)
    env = dict(os.environ, ERL_FLAGS='+S 2:2', MIX_ENV='test', MIXER_MIGRATION_UPGRADE_OUTPUT=str(out))
    receipt = {'schema': 1, 'commands': [], 'cleanup': {}, 'dependencies': DEPS,
        'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Actual ordinary Ecto migration 00008 and upgrade-only provisioning on one dedicated synthetic browser_admin connection. Explicit fixed catalog versions and exact baseline preservation. Eight named locked dependency directories; selected source copies only. No broad hosted harness/application, frozen inspector/authority-driver/rejected Worker transport, production/operator deployment, provider/customer/native/UI/capture/phone activity.',
        'synthetic_identities': {'installer': 'browser_admin SET ROLE browser_schema_owner (restricted NOLOGIN owner)',
            'upgrader_and_post_provision_rollback': 'browser_admin (synthetic local PostgreSQL superuser)',
            'writer': 'browser_writer (restricted NOLOGIN)', 'lifecycle': 'browser_lifecycle (restricted LOGIN)',
            'ordinary': 'browser_ordinary (restricted LOGIN)'},
        'pending': ['Independent migration review', 'Full relation admission', 'Trusted Store owner and deadline/rollback provenance',
                    'Runtime pool/custody/current access/OIDC/provider/HTTP/console',
                    'Neon/operator/customer/FieldLog/GA qualification', 'Paused native runtime/capture and final physical matrix']}
    scratch = None
    stopped = True
    compiled = out / 'compiled'
    manifest = {}
    beams = {}

    def run(label, argv, check=True, timeout=30, cwd=inputs):
        argv = [str(x) for x in argv]
        entry = {'name': label, 'argv': argv, 'cwd': str(cwd), 'timeout_seconds': timeout}
        receipt['commands'].append(entry)
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                entry['timed_out'] = False
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                stdout, stderr = proc.communicate(timeout=5)
                entry['timed_out'] = True
            entry['exit_code'] = proc.returncode
        except OSError as error:
            stdout, stderr = b'', str(error).encode()
            entry.update(exit_code=None, timed_out=False, spawn_error=type(error).__name__)
        (out / (label + '.stdout')).write_bytes(stdout)
        (out / (label + '.stderr')).write_bytes(stderr)
        entry.update(stdout=label + '.stdout', stderr=label + '.stderr',
                     stdout_sha256=hashlib.sha256(stdout).hexdigest(), stderr_sha256=hashlib.sha256(stderr).hexdigest())
        if check and (entry['exit_code'] != 0 or entry['timed_out']):
            raise RuntimeError(label + ' failed')
        return entry['exit_code'], stdout

    try:
        assert set(MIGRATIONS) == {p.name for p in (ROOT / 'hosted/priv/repo/migrations').iterdir() if p.is_file()}
        for rel in SOURCES:
            target = inputs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
            manifest[rel] = sha(target)
        receipt['sources_sha256'] = manifest
        receipt['source_tree_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        paths = [ROOT / 'hosted/_build/test/lib' / n / 'ebin' for n in DEPS]
        assert all(directory.is_dir() for directory in paths)
        beams = {str(p.relative_to(ROOT)): sha(p) for directory in paths for p in sorted(directory.iterdir()) if p.is_file()}
        (out / 'dependency-beams.json').write_text(json.dumps(beams, indent=2) + '\n')
        receipt['dependency_manifest_sha256'] = sha(out / 'dependency-beams.json')
        _, head = run('git-head', ['git', '-C', ROOT, 'rev-parse', 'HEAD'])
        receipt['head'] = head.decode().strip()
        for label, argv in [('python-version', ['python3', '--version']), ('elixir-version', ['elixir', '--version']),
                            ('mix-version', ['mix', '--version']), ('postgres-version', [PG / 'postgres', '--version'])]:
            run(label, argv)
        compiled.mkdir()
        pa = [arg for p in paths for arg in ['-pa', p]]
        run('selected-compile', ['elixirc'] + pa + ['--warnings-as-errors', '-o', compiled] + [inputs / rel for rel in MODULES])
        formatted = MODULES + [BROWSER + 'activation_preparation.ex', TEST,
            'hosted/test/mixer_hosted/browser_auth/migration_spec.exs', 'hosted/test/foundation_integration_test.exs']
        formatted += ['hosted/priv/repo/migrations/' + n for n in MIGRATIONS]
        formatted += [f'hosted/test/mixer_hosted/builds/{n}_test.exs' for n in ['admission', 'coordinator', 'aggregate_admission']]
        run('actual-mix-format', ['mix', 'format', '--check-formatted'] + [inputs / rel for rel in formatted])
        scratch = Path(tempfile.mkdtemp(prefix='mixer-browser-migration-upgrade-'))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        receipt['owned_postgres'] = {'scratch': str(scratch), 'host': '127.0.0.1', 'port': port, 'pg_bin': str(PG)}
        run('initdb', [PG / 'initdb', '-D', scratch / 'data', '-U', 'browser_admin', '-A', 'trust', '--no-locale', '-E', 'UTF8'])
        run('postgres-start', [PG / 'pg_ctl', '-D', scratch / 'data', '-l', out / 'postgres.log', '-o', f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", '-w', 'start'], timeout=15)
        psql = [PG / 'psql', '-X', '-h', '127.0.0.1', '-p', port, '-U', 'browser_admin', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1']
        roles = [('browser_schema_owner', 'NOLOGIN'), ('browser_writer', 'NOLOGIN'), ('browser_lifecycle', 'LOGIN'),
                 ('browser_ordinary', 'LOGIN'), ('migration_neighbor', 'NOLOGIN')]
        run('roles', psql + ['-c', ';'.join('CREATE ROLE ' + n + ' ' + login + ' NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEROLE NOCREATEDB NOREPLICATION' for n, login in roles)])
        run('database', [PG / 'createdb', '-h', '127.0.0.1', '-p', port, '-U', 'browser_admin', '-O', 'browser_schema_owner', 'browser_storage'])
        env['MIXER_BROWSER_STORAGE_PORT'] = str(port)
        result = out / 'result.json'
        entrypoint = out / 'selected_runner.exs'
        entrypoint.write_text('Code.compiler_options(warnings_as_errors: true)\nExUnit.start(autorun: false, seed: 0, max_cases: 1, trace: true)\nCode.require_file(' + json.dumps(str(inputs / TEST)) + ')\nr=ExUnit.run()\nFile.write!(' + json.dumps(str(result)) + ',Jason.encode!(r))\nSystem.halt(if r.total==6 and r.failures==0 and r.skipped==0 and r.excluded==0 and Map.get(r,:invalid,0)==0, do: 0, else: 1)\n')
        code, _ = run('selected-tests', ['elixir'] + pa + ['-pa', compiled, entrypoint], check=False, timeout=90)
        receipt['tests_passed'] = code == 0
        if result.exists():
            receipt['tests'] = json.loads(result.read_text())
    except Exception as error:
        receipt['failure'] = str(error)
    finally:
        if scratch is not None and (scratch / 'data/postmaster.pid').exists():
            code, _ = run('postgres-stop', [PG / 'pg_ctl', '-D', scratch / 'data', '-m', 'immediate', '-w', 'stop'], check=False, timeout=15)
            stopped = code == 0 and not (scratch / 'data/postmaster.pid').exists()
        if scratch is not None and stopped:
            shutil.rmtree(scratch)
        receipt['cleanup'].update(owned_postgres_stopped=stopped, owned_scratch_removed=scratch is None or not scratch.exists())
        if compiled.exists():
            (out / 'compiled-products.json').write_text(json.dumps({p.name: sha(p) for p in sorted(compiled.iterdir()) if p.is_file()}, indent=2) + '\n')
            shutil.rmtree(compiled)
        receipt['cleanup']['owned_compile_products_removed'] = not compiled.exists()
        receipt['source_changes_during_run'] = [rel for rel, value in manifest.items() if sha(ROOT / rel) != value]
        receipt['dependency_changes_during_run'] = [rel for rel, value in beams.items() if sha(ROOT / rel) != value]
        receipt['success'] = receipt.get('tests_passed', False) and not receipt.get('failure') and all(receipt['cleanup'].values()) and not receipt['source_changes_during_run'] and not receipt['dependency_changes_during_run']
        receipt['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt['outputs_sha256'] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        (BASE / 'operator-latest.json').write_text(json.dumps({'mutable_pointer_only': True, 'attempt': str(out.relative_to(BASE))}, indent=2) + '\n')
        print(str(out.relative_to(ROOT)))
        print(json.dumps({k: receipt.get(k) for k in ['success', 'tests', 'failure', 'cleanup']}))
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
