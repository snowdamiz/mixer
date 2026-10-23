#!/usr/bin/env python3
"""Public-C independent review using exact frozen inputs and attested archives."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FREEZE = ROOT / 'vm/verification/capability-native/source-freeze.sha256'
FREEZE_SHA = '76372fd254e646141e991b3289b14c8380f13ea68602b21d4aa746080fddc8cf'
ARCHIVES = {
    'debug': ('vm/target/capability-native-review-final-v2/debug/libmixer_vm.a', 'd3c49dffd0fc6dea2d86f9d280c5d8fa5a7cb48a2916eb3152a4b1552dd9d2d7'),
    'release': ('vm/target/capability-native-review-final-v2/release/libmixer_vm.a', 'db04bf0baa4a844f12facbda682a557fef4e467e8a2f213c8341e00f60ac9f58'),
}


def sha(data): return hashlib.sha256(data).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def command(name, args, cwd, scope, timeout=60):
    args = [str(arg) for arg in args]
    started = now()
    try:
        result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        output, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as error:
        output, code = (error.stdout or b'') + b'\nReview command timed out\n', 124
    path = OUT / (name + '.log'); path.write_bytes(output)
    record = {'name': name, 'command': args, 'cwd': str(cwd), 'started_at': started, 'ended_at': now(),
              'exit_code': code, 'output': str(path.relative_to(ROOT)), 'output_sha256': sha(output), 'scope': scope}
    print(name + ': ' + str(code), flush=True)
    return record


def main():
    frozen = FREEZE.read_bytes(); assert sha(frozen) == FREEZE_SHA
    records = []
    for line in frozen.decode().splitlines():
        digest, relative = line.split('  ', 1)
        assert len(digest) == 64
        content = (ROOT / relative).read_bytes()
        assert sha(content) == digest, relative
        records.append({'path': relative, 'bytes': len(content), 'sha256': digest})
    assert len(records) == 90
    (OUT / 'source-freeze.sha256').write_bytes(frozen)
    with tempfile.TemporaryDirectory(prefix='mixer-native-c-review-') as temporary:
        base = Path(temporary); source = base / 'source'; source.mkdir()
        for record in records:
            target = source / record['path']; target.parent.mkdir(parents=True, exist_ok=True)
            content = (ROOT / record['path']).read_bytes(); assert sha(content) == record['sha256']
            target.write_bytes(content)
        archives = {}
        for configuration, (relative, digest) in ARCHIVES.items():
            data = (ROOT / relative).read_bytes(); assert sha(data) == digest
            destination = base / ('native-' + configuration + '.a'); destination.write_bytes(data)
            archives[configuration] = {'path': relative, 'sha256': digest, 'bytes': len(data), 'copy': destination}
        assert FREEZE.read_bytes() == frozen
        commands = [command('fixtures-create', ['python3', OUT / 'make-fixtures.py', base / 'fixtures'], base,
                            'Original tiny Wasm builder; no generated/borrowed engine fixtures')]
        fixtures = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted((base / 'fixtures').glob('*.wasm'))]
        clang = subprocess.check_output(['xcrun', '--find', 'clang'], text=True).strip()
        sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
        commands += [command('version-clang', [clang, '--version'], base, 'Observed official host C compiler'),
                     command('version-python', ['python3', '--version'], base, 'Observed independent review runner'),
                     command('version-host', ['uname', '-sm'], base, 'Observed host execution scope'),
                     command('version-sdk', ['xcrun', '--sdk', 'macosx', '--show-sdk-path'], base, 'Observed explicit host SDK')]
        runs = []
        for configuration, archive in archives.items():
            binary = base / ('public-' + configuration)
            commands.append(command('public-' + configuration + '-build', [clang, '-std=c11', '-Wall', '-Wextra', '-Werror',
                '-O0' if configuration == 'debug' else '-O2', '-g', '-isysroot', sdk, '-pthread', '-I', source / 'vm/include',
                OUT / 'public_client.c', archive['copy'], '-o', binary], base,
                'Independent actual public C compile/link to frozen ' + configuration + ' native-feature archive; no Rust rebuild'))
            if commands[-1]['exit_code'] == 0:
                commands.append(command('public-' + configuration + '-run', [binary, base / 'fixtures/capability.wasm', base / 'fixtures/legacy.wasm'], base,
                    'Actual public C boundary; shared pool, ownership/close/ack, aliases/no-write/ranges, family rejection and 96 races', timeout=45))
                if commands[-1]['exit_code'] == 0:
                    output = (ROOT / commands[-1]['output']).read_text().splitlines()[-1]
                    runs.append({'configuration': configuration, 'binary_sha256': sha(binary.read_bytes()), 'result': json.loads(output)})
        unchanged = all(sha((source / r['path']).read_bytes()) == r['sha256'] for r in records)
        live_matches = all(sha((ROOT / r['path']).read_bytes()) == r['sha256'] for r in records)
        archive_records = {key: {k: v for k, v in record.items() if k != 'copy'} for key, record in archives.items()}
        passed = unchanged and live_matches and len(runs) == 2 and all(c['exit_code'] == 0 for c in commands)
        review_sources = {name: sha((OUT / name).read_bytes()) for name in ['review.py', 'public_client.c', 'make-fixtures.py']}
        receipt = {'schema': 1, 'created_at': now(), 'freeze_sha256': FREEZE_SHA, 'source': records,
                   'source_export_unchanged': unchanged, 'live_source_matches_at_end': live_matches,
                   'archive_provenance': 'Owner-supplied stable native-only archives matched root/owner SHA256; copied before linking; owner matrix receipt must complete provenance',
                   'archives': archive_records, 'review_source_sha256': review_sources, 'fixtures': fixtures, 'commands': commands, 'runs': runs,
                   'independent_public_checks_passed': passed, 'owner_matrix_audit_pending': True,
                   'pre_freeze_findings': ['after-ack/existing-terminal precedence clarified without mailbox behavior change',
                                          'expire and other published-session API unwind guards added before freeze',
                                          'quarantined close/cancel cleanup exception documented and tested before freeze'],
                   'source_review': {'shared_registry_synchronized_drop': 'Transient Arc drop under registry while retained matching Live/Closing Arc prevents final destruction; counts/quarantine checked there; final drop in Reclaiming outside registry',
                                     'locks': 'registry never takes ledger/mailbox; guest instance->mailbox and native ledger->mailbox have no reverse edge found',
                                     'quarantine': 'monotonic failure latch; armed local commit/unwind guard cannot clear concurrent quarantine',
                                     'tickets': 'Fixed eight owning entries; only Call increments; first actual ack decrements; stale mailbox identity consulted even when ledger remembers ack'},
                   'scope': 'Independent public C host tests and source review only, using frozen source/header/archive inputs; no native I/O or devices',
                   'limitations': ['Public races are bounded stress, not exhaustive model checking; owner barrier/unwind/poison/destructor tests require separate receipt audit',
                                   'No new TLS/network/storage guest bridge, scheduler, full Swift async, C/JNI mobile execution, signing/store/FieldLog/GA qualification',
                                   'Numeric pointer preflight does not validate dangling pointers; invalid numeric wrap/alias cases are rejected before dereference under the declared contract',
                                   'System allocator/OOM aborts and foreign framework code are outside the reviewed no-unwind/panic containment scope'],
                   'phones_disconnected_no_device_commands': True, 'production_edits_or_push': False}
        (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'independent_public_checks_passed': passed, 'source_export_unchanged': unchanged, 'live_source_matches': live_matches, 'owner_matrix_audit_pending': True}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__': raise SystemExit(main())
