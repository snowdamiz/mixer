"""Own exact-PID/PGID host-only commands, each bounded to 55 seconds."""
from pathlib import Path
import datetime, json, os, signal, subprocess, sys, time
sys.dont_write_bytecode = True
from custody import HERE, ROOT, TREE, canonical, row, sha, snapshot, need

def main():
    label, script, *args = sys.argv[1:]
    need(label.replace('-', '').isalnum() and script in ('independent_tests.py', 'finalize.py', 'audit.py'), 'own bounded command allowlist')
    destination = HERE / 'commands' / label
    destination.mkdir(parents=True, exist_ok=False)
    before = snapshot()
    (destination / 'inputs-before.json').write_bytes(canonical(before) + b'\n')
    programs = [row(p) for p in sorted(HERE.glob('*.py'))]
    (destination / 'source-programs').mkdir()
    for p in HERE.glob('*.py'):
        (destination / 'source-programs' / p.name).write_bytes(p.read_bytes())
    argv = [sys.executable, '-B', str(HERE / script), *args]
    environment = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0', 'LC_ALL': 'C', 'LANG': 'C'}
    began = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clock = time.monotonic()
    child = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=2)
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    (destination / 'stdout').write_bytes(stdout)
    (destination / 'stderr').write_bytes(stderr)
    after = snapshot()
    (destination / 'inputs-after.json').write_bytes(canonical(after) + b'\n')
    receipt = {'schema': 1, 'started': began, 'elapsed_seconds': time.monotonic() - clock,
               'argv': argv, 'cwd': str(ROOT), 'environment': environment, 'timeout_seconds': 55,
               'tool_version': sys.version, 'python_executable': str(Path(sys.executable).resolve()),
               'python_executable_sha256': sha(Path(sys.executable).resolve().read_bytes()),
               'source146_tree_sha256': TREE, 'source_programs': programs,
               'source_program_tree_sha256': sha(canonical(programs)),
               'inputs_before': row(destination / 'inputs-before.json'), 'inputs_after': row(destination / 'inputs-after.json'),
               'exact_frozen_inputs_before_after_unchanged': before == after,
               'owned_PID': child.pid, 'owned_PGID': child.pid, 'waited_and_reaped': child.poll() is not None,
               'owned_group_absent': absent, 'timed_out': timed_out, 'exit_code': child.returncode,
               'stdout': row(destination / 'stdout'), 'stderr': row(destination / 'stderr'),
               'scope': 'targeted offline independent partial-source contract checks only',
               'compiler_native_UI_capture_phone_global_inventory_Git_or_other_lane_mutations': False}
    (destination / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'label': label, 'exit_code': child.returncode, 'seconds': receipt['elapsed_seconds'], 'owned_PID': child.pid,
                      'owned_PGID': child.pid, 'group_absent': absent, 'custody_unchanged': before == after,
                      'stdout': stdout.decode(errors='replace')[-5000:], 'stderr': stderr.decode(errors='replace')[-5000:]}))
    if child.returncode or timed_out or not absent or before != after:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
