"""Verify released preaccess inputs and seal only this bounded independent packet."""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import signal
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
ROOT_REVIEW = 'verification/swift-semantic-adapter-root-review/'
INPUTS = {
    ROOT_REVIEW + 'guarded-snapshot-composition-source-preparation-selection.json': '9aefd86c679ee13a232315bb3a3a15e59fd3bba8e358139e7bbdffbd24e1573c',
    ROOT_REVIEW + 'guarded-snapshot-composition-interface-direction.json': '87c5e62198270a04266cd897f141bef254ad6b3593a9e952e86bc08c79e5e51d',
    ROOT_REVIEW + 'guarded-snapshot-encoder-host-acceptance.json': '4d0eb23c7306e4d63d039f989391e59e45a928be98ece531f69f543952eb15cb',
    ROOT_REVIEW + 'guarded-snapshot-encoder-layout-composition-release.json': '6f241f56431eec5f1d192fc97df51adcaea960c9feea211c214b053a202f7ebb',
    ROOT_REVIEW + 'guarded-snapshot-admission-correction-host-acceptance.json': 'a64934fac867f371c670b81b6a49fde0cc0d20691951f5fa723eca5f74ee8d7b',
    'verification/swift-guarded-snapshot-encoder-implementation/seal.json': 'eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f',
    'verification/swift-guarded-snapshot-encoder-implementation/final-source-manifest.json': '1d4c432a2cbfa7ef8af7fc8e7c13df263a0275296a5fe11a412715c3cd580e46',
    'verification/swift-guarded-snapshot-encoder-independent/candidate-review/seal.json': '0558e60b968e9f9bcab1294c47dc278abd4541131a406d00c1a50e412ac3a635',
    'verification/swift-guarded-snapshot-encoder-independent/candidate-review/source-place-addendum.json': 'c63de76852dc11819935856021ad325208946dd8008e0910dd508a70b9460ce8',
    'verification/swift-guarded-snapshot-export-admission-correction/seal.json': '3812896d87c86c9fe70446494ca48d57d4a848ea4da885e41b877b47388049f5',
}


def identity(path, relative=None):
    data = path.read_bytes()
    return {'path': relative or str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def command(argv, seconds=15):
    process = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    return {'argv': argv, 'timeout_seconds': seconds, 'timed_out': timed_out, 'exit_code': process.returncode,
            'stdout': stdout.decode(), 'stderr': stderr.decode(), 'direct_child_reaped': process.poll() is not None}


def main():
    refs = []
    for relative, expected in INPUTS.items():
        row = identity(ROOT / relative)
        assert row['sha256'] == expected, row
        refs.append(row)
    accepted = ROOT / 'verification/swift-guarded-snapshot-encoder-implementation'
    seal = json.loads((accepted / 'seal.json').read_text())
    source = [row for row in seal['members'] if row['path'].startswith('source/')]
    for row in source:
        assert identity(accepted / row['path'], row['path']) == row
    assert len(source) == 144
    relevant_source = [row for row in source if row['path'].endswith(('experimental/swift.rs', 'initial_profile_v1.rs', 'initial_profile_v1/selected.rs'))]
    correction = ROOT / 'verification/swift-guarded-snapshot-export-admission-correction'
    correction_seal = json.loads((correction / 'seal.json').read_text())
    correction_names = {'design-correction.md', 'prototype/initial_append.rs', 'prototype/control_append.rs'}
    for row in correction_seal['members']:
        if row['path'] in correction_names:
            assert identity(correction / row['path'], row['path']) == row
            refs.append(identity(correction / row['path']))
    revision = command(['git', 'rev-parse', 'HEAD'])
    assert revision['exit_code'] == 0
    oracle = command([sys.executable, '-B', str(OUT / 'arithmetic_controls.py')])
    assert oracle['exit_code'] == 0, oracle
    save('arithmetic-results.json', json.loads(oracle['stdout']))
    save('receipt.json', {
        'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'preaccess-criteria-sealed-await-exact-frozen-composition-candidate',
        'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())],
        'python': sys.version, 'platform': platform.platform(), 'source_revision_command': revision,
        'source_revision': revision['stdout'].strip(), 'inputs': refs,
        'accepted_encoder_source_members_verified': len(source),
        'accepted_encoder_source_tree_sha256': '447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43',
        'accepted_relevant_source_read': relevant_source,
        'arithmetic_oracle_command': oracle,
        'earlier_command_failure_retained': {'command': 'rustc --version --verbose', 'stderr': 'zsh:1: command not found: rustc', 'scope': 'PATH lookup only; no compiler process started; no compiler evidence claimed'},
        'active_composition_or_work_audit_read': False,
        'hosted_or_stopped_harness_imported_or_executed': False,
        'genuine_writer_executed': False, 'complete_floor_selected': False,
        'new_compiler_lifetime_controls': 'pending exact frozen candidate and bounded actual-type controls',
        'paused_surfaces_used': False, 'git_mutations': False,
        'scope': 'independent preaccess criteria and synthetic arithmetic controls only',
    })
    members = [identity(path, str(path.relative_to(OUT))) for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'seal.json']
    stream = ''.join(f"{row['path']}\0{row['bytes']}\0{row['sha256']}\n" for row in members).encode()
    result = {'schema': 1, 'member_count': len(members), 'bytes': sum(row['bytes'] for row in members), 'members': members,
              'tree_sha256': hashlib.sha256(stream).hexdigest(), 'tree_digest_format': 'path NUL decimal-bytes NUL sha256 newline in sorted path order',
              'scope': 'preaccess only; no composition acceptance, storage floor or writer release'}
    save('seal.json', result)
    print(json.dumps(identity(OUT / 'seal.json')))


if __name__ == '__main__':
    main()
