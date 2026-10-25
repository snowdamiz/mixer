#!/usr/bin/env python3
"""Selected v1/v2 function/type checks on one owned disposable PostgreSQL17."""
import argparse
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
PG = Path('/opt/homebrew/Cellar/postgresql@17/17.11/bin')
DEPS = ['telemetry', 'decimal', 'db_connection', 'ecto', 'ecto_sql', 'postgrex', 'jason']
BROWSER = 'hosted/lib/mixer_hosted/browser_auth/'
MIGRATIONS = ['20261025000003_add_customer_authorization.exs',
              '20261025000004_add_authorization_state_revisions.exs',
              '20261025000006_add_customer_workspace_discovery.exs',
              '20261025000007_add_browser_sessions.exs']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['pre-fix-proof', 'v2', 'v1-regression'], default='v2')
    args = parser.parse_args()
    test, expected = {'pre-fix-proof': ('verification/hosted-browser-catalog-v2/pre_fix_proof.exs', 3),
                      'v2': ('verification/hosted-browser-catalog-v2/catalog_v2_test.exs', 30),
                      'v1-regression': ('verification/hosted-browser-catalog-admission/function_surface_spec.exs', 26)}[args.phase]
    modules = [BROWSER + n for n in ['storage_schema.ex', 'catalog_manifest.ex', 'catalog.ex']]
    if args.phase != 'pre-fix-proof':
        modules = [BROWSER + n for n in ['storage_schema.ex', 'activation_preparation_schema.ex',
                   'catalog_manifest.ex', 'catalog_manifest_v2.ex', 'catalog.ex']]
    sources = modules + [BROWSER + 'activation_preparation.ex',
        'hosted/test/mixer_hosted/browser_auth/storage_fixture.exs',
        'docs/hosted-browser-lifecycle-runtime-contract.md', 'hosted/mix.lock',
        'verification/hosted-browser-catalog-v2/run.py', test]
    sources += ['hosted/priv/repo/migrations/' + n for n in MIGRATIONS]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-') + uuid.uuid4().hex[:8]
    out = BASE / 'attempts' / (args.phase + '-' + stamp)
    inputs = out / 'inputs'
    inputs.mkdir(parents=True)
    env = dict(os.environ, ERL_FLAGS='+S 2:2', MIX_ENV='test')
    receipt = {'schema': 1, 'phase': args.phase, 'commands': [], 'cleanup': {},
        'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Selected ordinary sources and accepted reused storage fixture/migrations only; one synthetic PostgreSQL17 loopback instance; no broad hosted harness, frozen catalog-inspector/authority-driver/rejected WorkerV2, application caller/readiness/Store, production/provider/customer, native/UI/capture/phone activity.',
        'pending': ['Independent PostgreSQL16 review', 'Relation/index/constraint/trigger/policy/grants admission',
                    'Trusted Store owner and original operation deadline provenance', 'Migration and runtime owner wiring',
                    'Neon/operator/provider/customer/FieldLog/GA qualification', 'Paused native runtime/capture and final physical matrix']}
    scratch = None
    stopped = True
    compiled = out / 'compiled'

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
        entry.update(stdout=label + '.stdout', stderr=label + '.stderr')
        if check and (entry['exit_code'] != 0 or entry['timed_out']):
            raise RuntimeError(label + ' failed')
        return entry['exit_code'], stdout

    try:
        manifest = {}
        for rel in sources:
            target = inputs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
            manifest[rel] = sha(target)
        receipt['sources_sha256'] = manifest
        receipt['source_tree_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        paths = [ROOT / 'hosted/_build/test/lib' / n / 'ebin' for n in DEPS]
        beams = {str(p.relative_to(ROOT)): sha(p) for directory in paths for p in sorted(directory.iterdir()) if p.is_file()}
        assert beams
        (out / 'dependency-beams.json').write_text(json.dumps(beams, indent=2) + '\n')
        receipt['dependency_manifest_sha256'] = sha(out / 'dependency-beams.json')
        _, head = run('git-head', ['git', '-C', ROOT, 'rev-parse', 'HEAD'])
        receipt['head'] = head.decode().strip()
        for label, argv in [('python-version', ['python3', '--version']), ('elixir-version', ['elixir', '--version']),
                            ('mix-version', ['mix', '--version']), ('postgres-version', [PG / 'postgres', '--version'])]:
            run(label, argv)
        compiled.mkdir()
        compile_command = ['elixirc'] + [arg for p in paths for arg in ['-pa', p]] + ['--warnings-as-errors', '-o', compiled] + [inputs / rel for rel in modules]
        run('selected-compile', compile_command)
        run('actual-mix-format', ['mix', 'format', '--check-formatted'] + [inputs / rel for rel in modules + [test]])
        scratch = Path(tempfile.mkdtemp(prefix='mixer-browser-catalog-v2-'))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        receipt['owned_postgres'] = {'scratch': str(scratch), 'host': '127.0.0.1', 'port': port, 'pg_bin': str(PG)}
        run('initdb', [PG / 'initdb', '-D', scratch / 'data', '-U', 'browser_admin', '-A', 'trust', '--no-locale', '-E', 'UTF8'])
        run('postgres-start', [PG / 'pg_ctl', '-D', scratch / 'data', '-l', out / 'postgres.log', '-o', f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", '-w', 'start'], timeout=15)
        psql = [PG / 'psql', '-X', '-h', '127.0.0.1', '-p', port, '-U', 'browser_admin', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1']
        roles = [('browser_schema_owner', 'NOLOGIN'), ('browser_writer', 'NOLOGIN'), ('browser_lifecycle', 'LOGIN'),
                 ('browser_ordinary', 'LOGIN'), ('surface_neighbor', 'NOLOGIN')]
        run('roles', psql + ['-c', ';'.join('CREATE ROLE ' + n + ' ' + login + ' NOSUPERUSER NOBYPASSRLS NOINHERIT' for n, login in roles)])
        run('database', [PG / 'createdb', '-h', '127.0.0.1', '-p', port, '-U', 'browser_admin', '-O', 'browser_schema_owner', 'browser_storage'])
        env['MIXER_BROWSER_STORAGE_PORT'] = str(port)
        result = out / 'result.json'
        entrypoint = out / 'selected_runner.exs'
        entrypoint.write_text('ExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(test) + ')\nr=ExUnit.run()\nFile.write!(' + json.dumps(str(result)) + ',Jason.encode!(r))\nSystem.halt(if r.total==' + str(expected) + ' and r.failures==0 and r.skipped==0 and r.excluded==0 and Map.get(r,:invalid,0)==0, do: 0, else: 1)\n')
        command = ['elixir'] + [arg for p in paths for arg in ['-pa', p]] + [arg for rel in modules for arg in ['-r', inputs / rel]] + [entrypoint]
        code, _ = run('selected-tests', command, check=False, timeout=90)
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
        receipt['source_changes_during_run'] = [rel for rel, value in receipt.get('sources_sha256', {}).items() if sha(ROOT / rel) != value]
        receipt['dependency_changes_during_run'] = [rel for rel, value in locals().get('beams', {}).items() if sha(ROOT / rel) != value]
        receipt['success'] = receipt.get('tests_passed', False) and not receipt.get('failure') and all(receipt['cleanup'].values()) and not receipt['source_changes_during_run'] and not receipt['dependency_changes_during_run']
        receipt['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt['outputs_sha256'] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        (BASE / (args.phase + '-latest.json')).write_text(json.dumps({'mutable_pointer_only': True, 'attempt': str(out.relative_to(BASE))}, indent=2) + '\n')
        print(str(out.relative_to(ROOT)))
        print(json.dumps({k: receipt.get(k) for k in ['success', 'tests', 'failure', 'cleanup']}))
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
