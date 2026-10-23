#!/usr/bin/env python3
"""Verify the decoded-cache candidate and independent retained evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
load = lambda path: json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    owner_path = ROOT / 'verification/span-function-cache/2026-10-23-host/receipt.json'
    review_path = ROOT / 'verification/span-function-cache-review/2026-10-23-host-v2/receipt.json'
    owner, review = load(owner_path), load(review_path)
    for path, digest in review['source_files_sha256'].items():
        assert sha(ROOT / path) == digest, path
    assert all(review['source_files_sha256'][p] == h for p, h in owner['source_files_sha256'].items())
    assert set(review['source_files_sha256']) - set(owner['source_files_sha256']) == {'vm/include/mixer_vm_guest_ui.h'}
    for record in (owner, review):
        assert hashlib.sha256(json.dumps(record['source_files_sha256'], sort_keys=True).encode()).hexdigest() == record['source_manifest_sha256']
        for command in record['commands']:
            assert command['exit_code'] == 0
            assert sha(ROOT / command['output']) == command['output_sha256']
    assert review['status'] == 'passed' and review['source_stable']
    for path, digest in review['review_input_sha256'].items():
        assert sha(ROOT / path) == digest, path
    isolation = load(owner_path.parent / 'existing-source-isolation.json')
    for path, digest in isolation['files'].items():
        original = subprocess.check_output(['git', 'show', isolation['baseline'] + ':' + path], cwd=ROOT)
        assert hashlib.sha256(original).hexdigest() == digest
        current = (ROOT / path).read_bytes()
        if path in isolation['only_stripped_snippets']:
            snippet = isolation['only_stripped_snippets'][path].encode()
            assert current.count(snippet) == 1
            current = current.replace(snippet, b'', 1)
        assert current == original, path
    retained_path = ROOT / 'verification/span-function-cache-review/retained-artifacts.json'
    retained = load(retained_path)
    assert retained['source_receipt_sha256'] == sha(review_path)
    for artifact in retained['artifacts']:
        assert sha(Path(artifact['retained_path'])) == artifact['sha256']
        assert Path(artifact['retained_path']).stat().st_size == artifact['size_bytes']
        selected = next(a for a in review['artifacts'] if a['profile'] == artifact['profile'])
        assert selected['library_sha256'] == artifact['sha256']
    counts = {}
    for command in load(HERE / 'combined-commands.json'):
        assert command['exitCode'] == 0 and sha(ROOT / command['log']) == command['sha256']
        matches = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', (ROOT / command['log']).read_text())
        assert matches and all(int(failed) == 0 for _, failed, _ in matches)
        counts[command['mode']] = dict(passed=sum(int(n) for n, _, _ in matches), ignored=sum(int(n) for _, _, n in matches))
    evidence = {}
    for lane in ('span-function-cache', 'span-function-cache-review'):
        for path in sorted((ROOT / 'verification' / lane).rglob('*')):
            if path.is_file() and not {'.build', '__pycache__'}.intersection(path.parts):
                evidence[str(path.relative_to(ROOT))] = sha(path)
    record = {
        'status': 'root integration review and combined feature checks passed',
        'authorization': False,
        'audit_sha256': sha(Path(__file__)),
        'owner_receipt_sha256': sha(owner_path),
        'independent_receipt_sha256': sha(review_path),
        'owner_source_manifest_sha256': owner['source_manifest_sha256'],
        'verified_owner_sources': len(owner['source_files_sha256']),
        'verified_review_sources': len(review['source_files_sha256']),
        'verified_unchanged_baseline_files': len(isolation['files']),
        'verified_command_logs': len(owner['commands']) + len(review['commands']) + 2,
        'combined_commands_sha256': sha(HERE / 'combined-commands.json'),
        'combined_counts': counts,
        'ci_workflow_sha256': sha(ROOT / '.github/workflows/verify.yml'),
        'evidence_files': evidence,
        'findings': [],
        'scope': [
            'Root read cache constructor/pin/release and both decoder passes; independent reviewer exercised original public probes.',
            'Independent review tightened unpublished payload drop-before-reservation-release; sealed source includes the repair.',
            'Combined streaming/cache/native-capability debug and release runs pass; their ignored development oracles remain covered only by owner explicit cache-feature runs until hosted combined oracle jobs complete.',
            'A separately added uncompiled UI header is explicitly outside the cache owner candidate and included in independent source binding.',
            'Default routes, existing source/header/contracts and executor are unchanged; no native ABI/archive rebuild or guest execution bridge is claimed.',
            'Allocator request and reservation observations do not establish RSS, aggregate session memory, full Swift, physical device, published-package or GA qualification.'
        ]
    }
    output = HERE / 'receipt.json'
    if args.check:
        assert load(output) == record
    else:
        output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'receipt_sha256': sha(output), 'counts': counts, 'evidence_files': len(evidence)}))


if __name__ == '__main__':
    main()
