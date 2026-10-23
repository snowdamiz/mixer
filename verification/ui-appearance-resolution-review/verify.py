#!/usr/bin/env python3
"""Independent frozen-source public-API adversarial review. No device discovery."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/ui-appearance-resolution/candidate-2'
OUT = HERE / 'candidate-2'
EXPECTED = 'a629acb9755307753e7d9dd6e424fde97c4b72641c8b1242241348526b624859'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    OUT.mkdir(exist_ok=True)
    lock_bytes = (PRODUCER / 'input-lock.json').read_bytes()
    producer_bytes = (PRODUCER / 'receipt.json').read_bytes()
    lock = json.loads(lock_bytes)
    collection = sha(json.dumps(lock['files'], sort_keys=True, separators=(',', ':')).encode())
    assert collection == lock['source_tree_sha256'] == EXPECTED
    assert json.loads(producer_bytes)['source_tree_sha256'] == EXPECTED
    for name, expected in lock['files'].items():
        data = (PRODUCER / 'inputs' / name).read_bytes()
        assert sha(data) == expected, name
        assert sha((ROOT / name).read_bytes()) == expected, name
        dest = OUT / 'inputs' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == data, name
        else:
            dest.write_bytes(data)
    (OUT / 'producer-input-lock.json').write_bytes(lock_bytes)
    (OUT / 'producer-receipt.json').write_bytes(producer_bytes)
    owned_files = ['Package.swift', 'Review/Review.swift', 'verify.py']
    authored = {p: sha((HERE / p).read_bytes()) for p in owned_files}
    review_digest = sha(json.dumps(authored, sort_keys=True, separators=(',', ':')).encode())
    receipt = dict(
        format='mixer.ui-appearance-resolution-independent-review.1',
        status='running', started_at=utc(),
        head_at_start=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        head_tree_at_start=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
        producer_source_collection_sha256=collection, producer_source_files=lock['files'],
        producer_receipt_sha256=sha(producer_bytes), producer_input_lock_sha256=sha(lock_bytes),
        review_sources=authored, review_source_collection_sha256=review_digest,
        commands=[], results={},
        scope='Independent public-API pure data correctness review, all ten current kinds, provisional sharedCandidate1 only. Frozen source. Debug and optimized Release adversarial host execution. No renderer, native resource capture, signing, installed support, display/input/health authority, device, visual parity, immutable FieldLog release or GA qualification.',
        physical_devices=dict(discovered=False, used=False, reconnection_requested=False),
        pending=['native support and consumption', 'native shaping and layout growth', 'native resource capture and packaging',
                 'provisional token approval against Apple reference', 'native interaction, accessibility and IME',
                 'physical iOS/Android appearance parity', 'signed integration and release authority',
                 'immutable published FieldLog package consumption', 'store, customer, operational and GA gates'])

    def save():
        (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, argv, cwd=HERE):
        env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
        start = time.monotonic()
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=600)
        logfile = OUT / (name + '.log')
        logfile.write_bytes(result.stdout)
        receipt['commands'].append(dict(name=name, argv=list(map(str, argv)), cwd=str(cwd),
            environment_overrides={'DEVELOPER_DIR': env['DEVELOPER_DIR']}, exit_code=result.returncode,
            elapsed_seconds=time.monotonic() - start, log=str(logfile.relative_to(ROOT)), log_sha256=sha(result.stdout)))
        save()
        print(name, result.returncode, flush=True)
        if result.returncode:
            receipt.update(status='failed', failed_command=name, completed_at=utc())
            save()
            print(result.stdout.decode(errors='replace'), flush=True)
            raise SystemExit(result.returncode)
        return result.stdout.decode(errors='replace')

    save()
    run('python-version', ['python3', '--version'])
    run('swift-version', ['swift', '--version'])
    run('xcode-version', ['xcodebuild', '-version'])
    for mode in ['debug', 'release']:
        output = run('independent-' + mode, ['swift', 'run', '--package-path', HERE,
            '-c', mode, '-Xswiftc', '-warnings-as-errors', 'Review'])
        results = [json.loads(line.removeprefix('REVIEW_RESULT ')) for line in output.splitlines()
                   if line.startswith('REVIEW_RESULT ')]
        assert len(results) == 1 and results[0]['status'] == 'passed'
        receipt['results'][mode] = results[0]
        save()
    assert receipt['results']['debug'] == receipt['results']['release']
    checks = 0
    for name, expected in lock['files'].items():
        for path in [ROOT / name, PRODUCER / 'inputs' / name, OUT / 'inputs' / name]:
            assert sha(path.read_bytes()) == expected, str(path)
            checks += 1
    for name, expected in authored.items():
        assert sha((HERE / name).read_bytes()) == expected, name
        checks += 1
    receipt.update(status='passed-pure-data-independent-review-only', completed_at=utc(),
                   unchanged_exact_input_checks=checks, blockers=[])
    save()
    print('PASS', OUT / 'receipt.json', flush=True)


if __name__ == '__main__':
    main()
