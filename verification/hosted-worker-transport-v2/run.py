#!/usr/bin/env python3
"""V2 client-only collection; each unknown-death case gets a fresh BEAM."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REVIEW_SHA = '5c4e1605be31b6ba1de6feff18794c071d1dbc2dc9fee72102cf86145f46f7c7'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def command(name, arguments, attempt):
    started = time.monotonic()
    environment = {'PATH': os.environ['PATH'], 'LANG': 'C.UTF-8', 'ERL_CRASH_DUMP': '/dev/null', 'ERL_CRASH_DUMP_SECONDS': '0'}
    process = subprocess.Popen(arguments, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = process.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
    finally:
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    assert len(out) <= 2_097_152 and len(err) <= 2_097_152
    stem = attempt+'-'+name
    (HERE/(stem+'.stdout')).write_bytes(out)
    (HERE/(stem+'.stderr')).write_bytes(err)
    row = {'name': name, 'arguments': arguments, 'cwd': str(ROOT), 'exit_code': process.returncode,
      'duration_ms': round((time.monotonic()-started)*1000), 'stdout': stem+'.stdout', 'stdout_sha256': sha(HERE/(stem+'.stdout')),
      'stderr': stem+'.stderr', 'stderr_sha256': sha(HERE/(stem+'.stderr')), 'cleanup': 'owned fresh command group disposed'}
    print(json.dumps({'command': name, 'exit_code': process.returncode}), flush=True)
    return row

def main():
    attempts = [int(p.name.split('-')[1]) for p in HERE.glob('collection-*-commands.json')]
    attempt = 'collection-'+str(max(attempts, default=0)+1)
    paths = list((HERE/'candidate').rglob('*.ex')) + list((HERE/'candidate').rglob('*.exs'))
    paths += list(HERE.glob('*.exs')) + list(HERE.glob('*.py')) + [HERE/'check_vectors.js', HERE/'context-map.json', HERE/'upstream-read-map.json', HERE/'locked-dependency-map.json']
    paths += [p for p in (HERE/'locked').rglob('*') if p.is_file()]
    paths += [p for p in (HERE/'upstream').rglob('*') if p.is_file()]
    paths += [ROOT/'docs/hosted-worker-transport-v2.md', ROOT/'THIRD_PARTY.yml']
    paths = sorted(set(paths))
    rows = [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p), 'size': p.stat().st_size} for p in paths]
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    save(attempt+'-source-map.json', {'schema': 2, 'source_digest': digest, 'inputs': rows})
    review = HERE/'upstream/verification/hosted-worker-transport-independent-review/receipt.json'
    assert sha(review) == REVIEW_SHA
    archive = HERE/(attempt+'-inputs.tar.gz')
    with tarfile.open(archive, 'w:gz') as output:
        for path in paths: output.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    elixir = shutil.which('elixir')
    prefix = [elixir, '--erl', '+S 2:2 +SDcpu 1 +SDio 1']
    for dependency in ['mint', 'jason', 'hpax']:
        prefix += ['-pa', str(HERE/'locked/hosted/_build/test/lib'/dependency/'ebin')]
    commands, tests = [], []
    jobs = [('elixir-version', [elixir, '--version']), ('openssl-version', [shutil.which('openssl'), 'version']), ('node-version', [shutil.which('node'), '--version'])]
    jobs += [('baseline-controls', prefix+[str(HERE/'compile_and_test.exs')])]
    cases = sorted(p.name.removesuffix('_test.exs') for p in (HERE/'candidate/test/fault_cases').glob('*_test.exs'))
    assert len(cases) == 18
    jobs += [('fault-'+name, prefix+[str(HERE/'compile_and_test.exs'), 'fault', name]) for name in cases]
    jobs += [('generate-vectors', prefix+['-pa', str(HERE/'build/test'), str(HERE/'generate_vectors.exs')]), ('check-vectors', [shutil.which('node'), str(HERE/'check_vectors.js')]), ('production-exports', prefix+[str(HERE/'production_exports.exs')])]
    try:
        for name, arguments in jobs:
            row = command(name, arguments, attempt)
            commands.append(row)
            save(attempt+'-commands.json', {'schema': 2, 'commands': commands})
            assert row['exit_code'] == 0, 'failed command: '+name
            if name == 'baseline-controls' or name.startswith('fault-'):
                result = json.loads((HERE/row['stdout']).read_text().strip().splitlines()[-1])
                assert result['failures'] == result['skipped'] == result['excluded'] == 0
                assert result['frozen_modules_loaded'] == []
                assert result['tests'] == (24 if name == 'baseline-controls' else 1)
                tests.append({'group': name, **result})
        assert sum(r['tests'] for r in tests) == 42
        vector_row = next(r for r in commands if r['name'] == 'check-vectors')
        vectors = json.loads((HERE/vector_row['stdout']).read_text())
        assert vectors['vectors'] == 36
        production_row = next(r for r in commands if r['name'] == 'production-exports')
        exports = json.loads((HERE/production_row['stdout']).read_text())
        assert all(exports[k] for k in ['fixture_start_absent', 'marker_reset_api_absent', 'phase_barrier_branches_absent', 'test_helpers_not_compiled'])
        assert exports['frozen_modules_loaded'] == []
        assert all(sha(ROOT/r['path']) == r['sha256'] for r in rows), 'source drift during collection'
        compiled = [{'path': str(p.relative_to(HERE)), 'sha256': sha(p), 'size': p.stat().st_size} for p in sorted((HERE/'build').rglob('*.beam'))]
        save(attempt+'-compiled-artifacts.json', {'schema': 2, 'artifacts': compiled})
        result = {'schema': 2, 'status': 'v2-isolated-candidate-awaiting-independent-review', 'source_digest': digest,
          'base_revision': json.loads(review.read_text())['source_revision'], 'current_git_revision': 'not-queried-by-instruction',
          'platform': platform.platform(), 'input_count': len(rows), 'tests': 42, 'test_groups': tests, 'vectors': vectors,
          'production_exports': exports, 'upstream_review_sha256': REVIEW_SHA, 'input_archive': archive.name,
          'input_archive_sha256': sha(archive), 'source_map': attempt+'-source-map.json', 'commands': attempt+'-commands.json',
          'frozen_v1_and_live_hosted_modified': False,
          'cleanup': {'owned_command_groups_disposed': True, 'whole_test_BEAM_domain_disposal_resets_quarantine': True,
            'product_marker_reset_used': False, 'fixture_resource_and_key_cleanup': 'executable assertions in every successful group',
            'cloud_database_native_hosted_app_git_used': False},
          'pending': ['independent V2 replay', 'live root startup integration and complete hosted release/CI',
            'hard resource/native TLS/crash core and deployment retention policy', 'durable real controller/provider execution',
            'tenant/source/result/artifact authority', 'Cloudflare Linux and external Apple macOS workers', 'signing/native/dogfood/GA']}
        save(attempt+'-result.json', result)
    except BaseException:
        save(attempt+'-failed.json', {'status': 'failed-or-incomplete', 'source_digest': digest, 'commands': commands, 'tests_observed': tests})
        raise
    finally:
        if (HERE/'build').exists(): shutil.rmtree(HERE/'build')
    outputs = [p for p in HERE.iterdir() if p.is_file() and
      (p.suffix in ['.stdout', '.stderr', '.http', '.json'] or
       (p.name.startswith('attempt-') and p.name.endswith('.tar.gz'))) and p.name != 'receipt.json']
    output_map = [{'path': p.name, 'sha256': sha(p), 'size': p.stat().st_size} for p in sorted(outputs)]
    output_archive = HERE/(attempt+'-outputs.tar.gz')
    with tarfile.open(output_archive, 'w:gz') as output:
        for path in outputs: output.add(path, arcname=path.name, recursive=False)
    result.update({'output_archive': output_archive.name, 'output_archive_sha256': sha(output_archive), 'output_bindings': output_map})
    result['cleanup']['owned_build_directory_removed'] = not (HERE/'build').exists()
    save('receipt.json', result)
    print(json.dumps({'status': result['status'], 'tests': 42, 'vectors': 36, 'inputs': len(rows), 'source_digest': digest}))

if __name__ == '__main__': main()
