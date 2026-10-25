#!/usr/bin/env python3
"""Exact selected source closure; one owned PostgreSQL 17 fixture, always cleaned."""
import datetime as dt
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
DEPS = ['telemetry', 'decimal', 'db_connection', 'ecto', 'ecto_sql', 'postgrex', 'jason',
        'oban', 'jose', 'mint', 'hpax']
IDENTITY = ['encoding', 'bounded_json', 'trust_snapshot', 'manifest', 'startup_config',
            'admission', 'global_address', 'http_freshness', 'http_wire_guard', 'dns_resolver', 'bounded_tcp',
            'jwks_transport', 'fetch_flight', 'key_owner']
BROWSER = ['vault', 'stored_snapshot', 'config', 'configuration_digest', 'custody',
           'runtime_config', 'storage_schema', 'activation_preparation',
           'activation_preparation_schema', 'catalog_manifest', 'catalog_manifest_v2',
           'catalog', 'relation_manifest', 'relation_catalog', 'preauth_draft',
           'lifecycle_repo', 'store', 'runtime_owner', 'protocol']
SOURCES = (['hosted/lib/mixer_hosted/identity/' + p + '.ex' for p in IDENTITY] +
           ['hosted/lib/mixer_hosted/' + p + '.ex' for p in ['runtime_config', 'repo']] +
           ['hosted/lib/mixer_hosted/browser_auth/' + p + '.ex' for p in BROWSER] +
           ['hosted/lib/mixer_hosted/customer_artifacts/schema.ex'])
OWN = ['hosted/lib/mixer_hosted/browser_auth/' + p + '.ex' for p in
       ['lifecycle_repo', 'preauth_draft', 'store', 'runtime_owner']]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(hashes):
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    out = BASE / 'attempts' / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + uuid.uuid4().hex[:6])
    out.mkdir(parents=True)
    scratch = Path(tempfile.mkdtemp(prefix='mixer-browser-preauth-store-'))
    receipt = {'schema': 1, 'commands': [], 'owned_scratch': str(scratch), 'cleanup': {},
               'scope': 'Exact ordinary selected modules, fixed production Store/RuntimeOwner, actual accepted default KeyOwner and synthetic restricted PostgreSQL 17 roles. No rewritten product or injected clock/Repo/provider/callback. Manual trusted synthetic RuntimeConfig at localhost random port bypasses constructor TLS/5432 deployment qualification only in fixture.'}
    env = {k: v for k, v in os.environ.items() if k in ['PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR']}
    env.update(ERL_FLAGS='+S 2:2 +SDcpu 1 +SDio 1', MIX_ENV='test', ERL_CRASH_DUMP=str(scratch / 'erl.dump'))
    sources = set(SOURCES + OWN + ['AGENTS.md', 'hosted/mix.exs', 'hosted/mix.lock',
        'docs/hosted-browser-preauth-store.md', 'docs/hosted-browser-lifecycle-runtime-contract.md',
        'verification/hosted-browser-preauth-store/run.py',
        'verification/hosted-browser-preauth-store/install.exs',
        'verification/hosted-browser-preauth-store/seal.py',
        'verification/hosted-browser-preauth-store/live.exs',
        'hosted/priv/browser_auth/relation_surface_v1_pg16.json',
        'hosted/priv/browser_auth/relation_surface_v1_pg17.json'])
    migrations = ['20261024000000_add_oban', '20261025000000_add_build_journals',
        '20261025000001_add_build_admission', '20261025000002_add_build_aggregate_limits',
        '20261025000003_add_customer_authorization', '20261025000004_add_authorization_state_revisions',
        '20261025000005_add_customer_artifact_storage', '20261025000006_add_customer_workspace_discovery',
        '20261025000007_add_browser_sessions', '20261025000008_add_browser_activation_preparation']
    sources.update('hosted/priv/repo/migrations/' + name + '.exs' for name in migrations)
    before = {p: sha(ROOT / p) for p in sorted(sources)}
    receipt['sources'] = before
    receipt['source_tree_sha256'] = tree(before)
    for p in before:
        dest = out / 'inputs' / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / p, dest)
    depdirs = [ROOT / 'hosted/_build/test/lib' / d / 'ebin' for d in DEPS]
    dependencies = {str(p.relative_to(ROOT)): sha(p) for d in depdirs for p in sorted(d.glob('*')) if p.is_file()}
    receipt['dependencies'] = dependencies
    receipt['dependency_tree_sha256'] = tree(dependencies)

    def run(label, argv, data=None, check=True, timeout=55, cwd=ROOT):
        argv = list(map(str, argv))
        command = {'label': label, 'argv': argv, 'cwd': str(cwd), 'timeout_seconds': timeout}
        receipt['commands'].append(command)
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE if data is not None else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = proc.communicate(data.encode() if isinstance(data, str) else data, timeout=timeout)
            command['timed_out'] = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate(timeout=5)
            command['timed_out'] = True
        (out / (label + '.stdout')).write_bytes(stdout)
        (out / (label + '.stderr')).write_bytes(stderr)
        command['exit'] = proc.returncode
        print(label + ': exit ' + str(proc.returncode), flush=True)
        if check and (proc.returncode or command['timed_out']):
            raise RuntimeError(label + ' failed')
        return proc.returncode, stdout.decode()

    try:
        frozen = {'hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex': 'f71d79b92065d2137363f10de89c137b95ce5758b0e4c21b88faaeb8a779fcfc',
                  'hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex': '3f83abc969225d07f0569ea0317a80a11371f0068519208d5cf110a6c430d33d'}
        if any(before[p] != h for p, h in frozen.items()):
            raise RuntimeError('accepted relation source pin mismatch')
        for d in depdirs:
            if not d.is_dir():
                raise RuntimeError('missing selected dependency ' + d.name)
        _, revision = run('revision', ['git', 'rev-parse', 'HEAD'])
        receipt['revision'] = revision.strip()
        run('elixir-version', ['elixir', '--version'])
        run('python-version', ['python3', '--version'])
        run('postgres-version', [PG / 'postgres', '--version'])
        # Run the actual Mix formatter from an empty project, no hosted discovery.
        formatting = OWN + ['verification/hosted-browser-preauth-store/install.exs',
        'verification/hosted-browser-preauth-store/seal.py', 'verification/hosted-browser-preauth-store/live.exs']
        for p in formatting:
            shutil.copy2(ROOT / p, scratch / Path(p).name)
        run('mix-format', ['mix', 'format', '--check-formatted'] + [Path(p).name for p in formatting], cwd=scratch)
        args = ['elixir'] + [a for d in depdirs for a in ['-pa', d]]
        (scratch / 'ebin').mkdir()
        compile_code = 'Mix.start(); Mix.env(:test); case Kernel.ParallelCompiler.compile_to_path(tl(System.argv()),hd(System.argv()),warnings_as_errors: true, return_diagnostics: true) do {:ok,_,%{compile_warnings: [], runtime_warnings: []}} -> :ok; _ -> System.halt(1) end'
        run('selected-compile', args + ['-e', compile_code, scratch / 'ebin'] + SOURCES)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env.update(PREAUTH_PORT=str(port), PREAUTH_OUTPUT=str(out))
        receipt['port'] = port
        run('initdb', [PG / 'initdb', '-D', scratch / 'data', '-U', 'browser_admin', '-A', 'trust', '--no-locale', '-E', 'UTF8'])
        run('postgres-start', [PG / 'pg_ctl', '-D', scratch / 'data', '-l', out / 'postgres.log', '-o', f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", '-w', 'start'])
        psql = [PG / 'psql', '-X', '-q', '-A', '-t', '-h', '127.0.0.1', '-p', port, '-U', 'browser_admin', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1']
        roles = [('browser_schema_owner', 'NOLOGIN'), ('browser_writer', 'NOLOGIN'), ('browser_lifecycle', 'LOGIN'), ('browser_ordinary', 'LOGIN')]
        run('roles', psql, data=';'.join('CREATE ROLE ' + r + ' ' + login + ' NOSUPERUSER NOBYPASSRLS NOINHERIT' for r, login in roles) + ';')
        run('database', psql, data='CREATE DATABASE browser_storage OWNER browser_schema_owner;')
        elixir = ['elixir'] + [a for d in depdirs + [scratch / 'ebin'] for a in ['-pa', d]]
        run('install', elixir + [BASE / 'install.exs'])
        run('live', elixir + [BASE / 'live.exs'], timeout=55)
        receipt['checks'] = json.loads((out / 'checks.json').read_text())
        if len(receipt['checks']) != 23 or not all(c['passed'] for c in receipt['checks']):
            raise RuntimeError('expected exactly 23 passing bounded methods')
        beam_cleanup = json.loads((out / 'beam-cleanup.json').read_text())
        if not all(beam_cleanup.values()):
            raise RuntimeError('owned BEAM cleanup failed')
        receipt['passed'] = True
    except Exception as error:
        receipt['failure'] = str(error)
    finally:
        if (scratch / 'data/postmaster.pid').exists():
            run('postgres-stop', [PG / 'pg_ctl', '-D', scratch / 'data', '-m', 'immediate', '-w', 'stop'], check=False, timeout=15)
        if (scratch / 'data').exists():
            status_code, _ = run('postmaster-status', [PG / 'pg_ctl', '-D', scratch / 'data', 'status'], check=False)
            receipt['cleanup']['postmaster_status_nonrunning'] = status_code == 3
        receipt['cleanup']['postmaster_absent'] = not (scratch / 'data/postmaster.pid').exists()
        if receipt['cleanup']['postmaster_absent']:
            shutil.rmtree(scratch)
        receipt['cleanup']['owned_scratch_absent'] = not scratch.exists()
        receipt['cleanup']['no_native_capture_browser_phone_or_provider_started'] = True
        receipt['source_changes'] = [p for p, h in before.items() if sha(ROOT / p) != h]
        receipt['dependency_changes'] = [p for p, h in dependencies.items() if sha(ROOT / p) != h]
        receipt['success'] = receipt.get('passed', False) and all(receipt['cleanup'].values()) and not receipt['source_changes'] and not receipt['dependency_changes']
        receipt['outputs'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file() and 'inputs' not in p.relative_to(out).parts}
        receipt['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print(out.relative_to(ROOT), flush=True)
        print(json.dumps({k: receipt.get(k) for k in ['success', 'failure', 'cleanup']}), flush=True)
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
