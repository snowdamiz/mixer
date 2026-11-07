#!/usr/bin/env python3
"""Independent pre-access evidence; reads accepted packets, never new producer code."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
EXPECTED = {
    'swift-ordered-retention-analyzer-library': ('777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63', 270),
    'swift-ordered-retention-analyzer-library-review': ('a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e', 624),
    'swift-ordered-retention-analyzer-fsm-contract': ('bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193', 245),
    'swift-ordered-retention-analyzer-fsm-contract-review': ('101e6c9a67e41cce0e3c82c67ba92ef8025da19376b0578f8ddcdd694fb67212', 528),
}
SOURCES = [
    'AGENTS.md', 'PLAN.md', 'mixer-product-plan.md',
    'docs/swift-ordered-retention-analyzer-library.md',
    'docs/swift-ordered-retention-analyzer-library-review.md',
    'docs/swift-ordered-retention-analyzer-fsm-contract.md',
    'docs/swift-ordered-retention-analyzer-fsm-contract-review.md',
    'verification/swift-ordered-retention-analyzer-library/src/analyzer.rs',
    'verification/swift-ordered-retention-analyzer-library/tests/fixture_tests.rs',
    'verification/swift-ordered-retention-analyzer-library-root-review/acceptance.json',
    'verification/swift-ordered-retention-analyzer-fsm-root-review/acceptance.json',
]

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(65536):
            h.update(block)
    return h.hexdigest()

def describe(path):
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=sha(path))

def seals():
    rows = []
    for name, (expected_hash, expected_count) in EXPECTED.items():
        path = ROOT / 'verification' / name / 'seal.json'
        assert sha(path) == expected_hash, name
        packet = json.loads(path.read_bytes())
        assert len(packet['members']) == expected_count, name
        for member in packet['members']:
            owned = ROOT / member['path']
            assert owned.stat().st_size == member['bytes'], member['path']
            assert sha(owned) == member['sha256'], member['path']
        rows.append(dict(packet=name, seal_sha256=expected_hash, members=expected_count,
                         bytes=sum(member['bytes'] for member in packet['members'])))
    return rows

def main():
    name = sys.argv[1]
    assert name.startswith('run-') and name[4:].isdigit()
    run = BASE / 'preparation' / name
    run.mkdir(parents=True)
    shutil.copy2(__file__, run / 'executed-prepare.py')
    receipt = dict(schema=1, at_unix=time.time(), scope='pre-access accepted-source review only',
                   new_proposal_read=False, new_implementation_read=False,
                   product_tests_executed=False, native_or_capture_processes_started=False,
                   native_or_unrelated_processes_queried=False, commands=[], passed=False)

    def command(label, args):
        result = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=60)
        (run / (label + '.stdout')).write_bytes(result.stdout)
        (run / (label + '.stderr')).write_bytes(result.stderr)
        receipt['commands'].append(dict(label=label, argv=[str(arg) for arg in args],
            cwd=str(ROOT), returncode=result.returncode, timeout_seconds=60,
            stdout_sha256=sha(run / (label + '.stdout')),
            stderr_sha256=sha(run / (label + '.stderr'))))
        return result

    try:
        receipt['revision_start'] = command('revision-start', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
        receipt['upstream_before'] = seals()
        for label, args in [('python-version', [sys.executable, '--version']),
                            ('rust-version', [str(RUSTC), '--version', '--verbose']),
                            ('git-version', ['git', '--version']),
                            ('host', ['uname', '-srm'])]:
            assert command(label, args).returncode == 0, label
        receipt['tools'] = dict(
            python=dict(path=sys.executable, version=sys.version, sha256=sha(Path(sys.executable))),
            rustc=dict(path=str(RUSTC), sha256=sha(RUSTC)))
        rows = []
        for relative in SOURCES:
            source = ROOT / relative
            target = run / 'accepted-inputs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            rows.append(describe(source))
        receipt['source_closure'] = rows
        receipt['source_tree_sha256'] = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        receipt['independent_vector_plan'] = describe(BASE / 'vector-plan.json')
        receipt['prior_discovery_observation'] = dict(
            command='python3 --version; rustc --version --verbose; git --version; uname -srm',
            rustc_on_default_PATH='command not found',
            correction='Use exact rustc executable from accepted host receipt; no installation or PATH change')
        receipt['upstream_after'] = seals()
        assert receipt['upstream_before'] == receipt['upstream_after']
        receipt['revision_end'] = command('revision-end', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
        receipt['owned_scratch'] = 'none created; synchronous tool-identity commands returned'
        receipt['passed'] = True
    finally:
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(passed=receipt['passed'], accepted_members=sum(x['members'] for x in receipt['upstream_after']),
                          source_tree_sha256=receipt['source_tree_sha256'], receipt=str((run / 'receipt.json').relative_to(ROOT)))))

if __name__ == '__main__':
    main()
