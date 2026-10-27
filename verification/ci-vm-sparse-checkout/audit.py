"""One-shot local sparse checkout/input audit. No compiler or native execution."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = 'a96712bbd79ff4c0709d2811dd2846b4a0ea0096'
SCRATCH = OUT / 'owned-scratch'
assert not (OUT / 'receipt.json').exists() and not SCRATCH.exists()
sha = lambda data: hashlib.sha256(data).hexdigest()
env = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
       'LC_ALL': 'C', 'LANG': 'C', 'PYTHONDONTWRITEBYTECODE': '1',
       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_TERMINAL_PROMPT': '0'}
receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'base': BASE,
    'scope': 'Actual local Git sparse materialization, complete selected blob custody and Python fixture/generator checks only; remote fetch and VM/C/compiler execution remain unrun',
    'python': sys.version, 'python_sha256': sha(Path(sys.executable).resolve().read_bytes()),
    'script_sha256': sha(Path(__file__).read_bytes()), 'environment': env, 'commands': [],
    'native_or_compiler_or_runtime_started': False, 'global_process_inventory': False}

def save():
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

def run(name, argv, cwd=ROOT, stdin=None):
    assert not (OUT / (name + '.stdout')).exists()
    start = time.monotonic()
    child = subprocess.Popen([str(a) for a in argv], cwd=cwd, env=env,
        stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed = False
    try:
        stdout, stderr = child.communicate(input=stdin, timeout=45)
    except subprocess.TimeoutExpired:
        timed = True
        os.killpg(child.pid, signal.SIGTERM)
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=5)
    try:
        os.killpg(child.pid, 0); absent = False
    except ProcessLookupError:
        absent = True
    for suffix, data in [('stdout', stdout), ('stderr', stderr)]:
        with (OUT / (name + '.' + suffix)).open('xb') as stream:
            stream.write(data)
    receipt['commands'].append({'name': name, 'argv': [str(a) for a in argv], 'cwd': str(cwd),
        'stdin_sha256': sha(stdin) if stdin is not None else None,
        'exit': child.returncode, 'timed_out': timed, 'elapsed_seconds': time.monotonic() - start,
        'owned_child_reaped': True, 'owned_group_absent': absent,
        'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)})
    save()
    assert child.returncode == 0 and not timed and absent, name
    return stdout

workflow = ROOT / '.github/workflows/verify.yml'
before_workflow = workflow.read_bytes()
receipt['workflow_before_sha256'] = sha(before_workflow)
old = run('original-workflow', ['git', 'show', BASE + ':.github/workflows/verify.yml'])
old_vm = old.decode().split('  vm:\n', 1)[1].split('  services:\n', 1)[0]
new_vm = before_workflow.decode().split('  vm:\n', 1)[1].split('  services:\n', 1)[0]
insert = new_vm.split('      - uses: actions/checkout@v4\n', 1)[1].split('      - name: Record owned VM host tools\n', 1)[0]
assert new_vm.replace(insert, '', 1) == old_vm, 'only checkout inputs may change'
assert before_workflow.decode().replace(insert, '', 1) == old.decode(), 'other jobs unchanged'
patterns = [line.strip() for line in insert.splitlines() if line.strip().startswith('/')]
assert len(patterns) == len(set(patterns)) == 10
assert 'sparse-checkout-cone-mode: false' in insert and all('..' not in p for p in patterns)
with (OUT / 'sparse-patterns.txt').open('x') as stream:
    stream.write('\n'.join(patterns) + '\n')
paths = [p.strip('/') for p in patterns]
selected_tree = run('selected-tree', ['git', 'ls-tree', '-rzl', BASE, '--', *paths])
entries = []
for record in selected_tree.split(b'\0'):
    if not record: continue
    meta, relative = record.split(b'\t', 1)
    mode, kind, oid, size = meta.decode().split()
    assert kind == 'blob' and mode in ('100644', '100755')
    path = relative.decode()
    body = (ROOT / path).read_bytes()
    assert len(body) == int(size)
    entries.append({'path': path, 'bytes': len(body), 'sha256': sha(body), 'git_blob': oid})
receipt['selected_files'] = len(entries)
receipt['selected_bytes'] = sum(x['bytes'] for x in entries)
with (OUT / 'inputs.json').open('x') as stream:
    json.dump(entries, stream, indent=2); stream.write('\n')
receipt['inputs_sha256'] = sha((OUT / 'inputs.json').read_bytes())
SCRATCH.mkdir()
checkout = SCRATCH / 'checkout'
try:
    run('git-version', ['git', '--version'])
    run('clone', ['git', 'clone', '--shared', '--no-checkout', '--single-branch', '--branch', 'main', str(ROOT), str(checkout)])
    run('sparse', ['git', 'sparse-checkout', 'set', '--no-cone', '--stdin'], cwd=checkout,
        stdin=('\n'.join(patterns) + '\n').encode())
    run('checkout', ['git', 'checkout', '--detach', BASE], cwd=checkout)
    assert run('revision', ['git', 'rev-parse', 'HEAD'], cwd=checkout).decode().strip() == BASE
    actual = {str(p.relative_to(checkout)) for p in checkout.rglob('*') if p.is_file() and '.git' not in p.relative_to(checkout).parts}
    assert actual == {x['path'] for x in entries}, 'actual sparse file inventory differs'
    for item in entries:
        assert sha((checkout / item['path']).read_bytes()) == item['sha256'], item['path']
    # Every repo-local C include used by this job must resolve within selection.
    c_roots = ['vm/include', 'vm/tests', 'native/android/signed-guest-ui/transport',
               'verification/android-transport-review', 'verification/android-facade-transport-review',
               'verification/capability-native-review', 'experimental-capability-runtime/build-tests']
    checked_includes = []
    for relative in sorted(actual):
        if not relative.endswith(('.c', '.h')) or not any(relative.startswith(p + '/') for p in c_roots): continue
        file = checkout / relative
        for include in re.findall(r'^\s*#\s*include\s*"([^"]+)"', file.read_text(), re.M):
            candidates = [file.parent / include, checkout / 'vm/include' / include]
            assert any(p.is_file() for p in candidates), (relative, include)
            checked_includes.append([relative, include])
    receipt['repo_local_C_includes_resolved'] = checked_includes
    run('fixed-terminals', [sys.executable, '-B', 'vm/tools/generate-capability-terminals.py'], cwd=checkout)
    run('public-client-fixtures', [sys.executable, '-B', 'verification/capability-native-review/make-fixtures.py', str(SCRATCH / 'fixtures')], cwd=checkout)
    fixture_rows = []
    for path in sorted((SCRATCH / 'fixtures').iterdir()):
        body = path.read_bytes()
        assert body[:8] == b'\x00asm\x01\x00\x00\x00' and 8 < len(body) < 4096
        fixture_rows.append({'name': path.name, 'bytes': len(body), 'sha256': sha(body)})
    assert [r['name'] for r in fixture_rows] == ['capability.wasm', 'legacy.wasm']
    receipt['public_client_fixtures'] = fixture_rows
    assert not run('selected-tracked-clean', ['git', 'status', '--porcelain', '--untracked-files=no'], cwd=checkout)
    for item in entries:
        assert sha((ROOT / item['path']).read_bytes()) == sha((checkout / item['path']).read_bytes()) == item['sha256']
    assert workflow.read_bytes() == before_workflow
    receipt['inputs_and_workflow_unchanged'] = True
    receipt['result'] = 'local-sparse-materialization-and-offline-generators-pass'
finally:
    shutil.rmtree(SCRATCH)
    receipt['owned_scratch_removed'] = not SCRATCH.exists()
    save()
print(json.dumps({'result': receipt.get('result'), 'selected_files': len(entries),
                  'selected_bytes': receipt['selected_bytes'], 'commands': len(receipt['commands']),
                  'owned_scratch_removed': receipt['owned_scratch_removed']}))
