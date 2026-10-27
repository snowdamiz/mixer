"""Three fresh external metadata controls against the canonical reactor library."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time
import run as bounded

case = sys.argv[1]
probes = {
    'public-validator-positive': (
        'extern crate mixer_vm;\nfn main(){let _=std::mem::size_of::<mixer_vm::experimental_swift_reactor::SwiftValidationBudget>();}\n', []),
    'codec-private-negative': (
        'extern crate mixer_vm;\nuse mixer_vm::experimental_swift_reactor::diagnostic_result_v1::decode_result_v1;\nfn main(){}\n', ['E0603']),
    'row-helper-private-negative': (
        'extern crate mixer_vm;\nuse mixer_vm::experimental_swift_reactor::diagnostic_profile::write_profile_row_body_v1;\nfn main(){}\n', ['E0603']),
}
source, expected = probes[case]
artifacts = sorted((bounded.OWNED / 'target/debug/deps').glob('libmixer_vm-*.rmeta'))
assert len(artifacts) == 1, artifacts
artifact = artifacts[0]
directory = bounded.HERE / 'commands' / case
directory.mkdir(parents=True, exist_ok=False)
probe = directory / 'probe.rs'
probe.write_text(source)
before = bounded.members()
assert before == json.loads((bounded.HERE / 'source-manifest.json').read_text())['members']
env = {'PATH': str(bounded.BIN) + ':/usr/bin:/bin',
       'TMPDIR': str(bounded.OWNED / 'tmp'), 'LANG': 'C', 'LC_ALL': 'C'}
output = bounded.OWNED / (case + '.rmeta')
argv = [str(bounded.BIN / 'rustc'), '--edition=2021', '--error-format=json',
        '--emit=metadata', '--extern', 'mixer_vm=' + str(artifact),
        '-L', 'dependency=' + str(artifact.parent), str(probe), '-o', str(output)]
preimage = {'schema': 1, 'case': case, 'argv': argv, 'cwd': str(bounded.ROOT),
            'environment': env, 'timeout_seconds': 30,
            'source_tree_sha256': bounded.sha(bounded.compact(before)),
            'source_manifest_sha256': bounded.sha((bounded.HERE / 'source-manifest.json').read_bytes()),
            'supervisor_sha256': bounded.sha(Path(__file__).read_bytes()),
            'helper_sha256': bounded.sha((bounded.HERE / 'run.py').read_bytes()),
            'probe_sha256': bounded.sha(probe.read_bytes()),
            'canonical_reactor_metadata': {'path': str(artifact), 'bytes': artifact.stat().st_size,
                                          'sha256': bounded.sha(artifact.read_bytes())},
            'expected_error_codes': expected}
(directory / 'preimage.json').write_text(json.dumps(preimage, indent=2) + '\n')
started = time.monotonic()
process = subprocess.Popen(argv, cwd=bounded.ROOT, env=env, start_new_session=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
timed_out = False
actions = []
try:
    stdout, stderr = process.communicate(timeout=30)
except subprocess.TimeoutExpired:
    timed_out = True
    os.killpg(process.pid, signal.SIGKILL)
    actions.append('SIGKILL timed-out owned compiler group')
    stdout, stderr = process.communicate(timeout=3)
try:
    os.killpg(process.pid, 0)
    group_absent = False
except ProcessLookupError:
    group_absent = True
if not group_absent:
    os.killpg(process.pid, signal.SIGKILL)
    actions.append('SIGKILL remaining owned compiler group; case stays failed')
errors = []
for line in stderr.splitlines():
    message = json.loads(line)
    if message.get('level') == 'error' and message.get('code'):
        errors.append(message['code']['code'])
success = (not timed_out and group_absent and before == bounded.members()
           and ((process.returncode == 0 and not expected)
                or (process.returncode != 0 and errors == expected)))
emitted = {'bytes': output.stat().st_size, 'sha256': bounded.sha(output.read_bytes())} if output.exists() else None
output.unlink(missing_ok=True)
(directory / 'stdout').write_bytes(stdout)
(directory / 'stderr').write_bytes(stderr)
receipt = {**preimage, 'exit_code': process.returncode, 'observed_error_codes': errors,
           'success': success, 'timed_out': timed_out, 'owned_process_group': process.pid,
           'direct_owned_child_reaped': process.poll() is not None,
           'owned_group_absent': group_absent, 'source_unchanged_after': before == bounded.members(),
           'elapsed_seconds': time.monotonic() - started, 'cleanup_actions': actions,
           'stdout_sha256': bounded.sha(stdout), 'stderr_sha256': bounded.sha(stderr),
           'emitted_metadata': emitted, 'owned_metadata_removed': not output.exists()}
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'case': case, 'success': success, 'exit_code': process.returncode,
                  'errors': errors, 'owned_group_absent': group_absent}, sort_keys=True))
raise SystemExit(0 if success else 1)
