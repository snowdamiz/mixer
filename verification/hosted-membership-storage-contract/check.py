#!/usr/bin/env python3
"""Validate evidence integrity/required-case inventory, not product authorization."""
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
matrix = json.loads((HERE / 'required-matrix.json').read_text())
probe = json.loads((HERE / 'run-3/receipt.json').read_text())
assert matrix['status'] == 'required-not-executed-hosted-integration'
assert [c['id'] for c in matrix['cases']] == [f'HMS{i:02}' for i in range(1, 21)]
assert all(c['case'] and c['expected'] for c in matrix['cases'])
assert len(probe['cases']) == 19 and all(c['status'] == 'passed' for c in probe['cases'])
assert probe['cleanup']['postgres_stopped'] and probe['cleanup']['socket_removed']
assert not probe['cleanup']['other_clusters_touched']
for name in ['probe.py', 'probe.sql']:
    expected = probe['inputs'][str((HERE / name).relative_to(ROOT))]
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected

# Keep the original collector output intact. Its writer-stdin summary is
# recoverable exactly from the hashed executed source; retain that correction.
correction = {
    'scope': 'run-3 commands.json entry 24 used a descriptive stdin summary; exact executed SQL is retained below and in hashed probe.py',
    'entry': 24,
    'exact_stdin': "SET lock_timeout='2s'; UPDATE probe_auth.families SET active=false,revision=revision+1 WHERE id='p';\n",
    'changes_to_original_command_log': False,
}
(HERE / 'command-log-correction.json').write_text(json.dumps(correction, indent=2) + '\n')
sources = [
    'AGENTS.md', 'mixer-product-plan.md', 'docs/hosted-identity-contract.md',
    'docs/hosted-token-verifier.md', 'verification/hosted-identity-contract/root-acceptance.json',
    'verification/hosted-token-verifier-root-review/acceptance.json',
    'hosted/lib/mixer_hosted/identity/verified_identity.ex', 'hosted/mix.exs', 'hosted/mix.lock',
    'services/release/migrations/001_release.sql', 'services/release/README-v3.md',
    'services/release/server.go', 'services/release/store.go', 'services/release/storage.go',
    'services/release/versioned.go', 'services/protocol/protocol.go',
    'services/protocol/v2.go', 'services/protocol/v3.go', 'services/protocol/cbor.go',
    'docs/hosted-membership-storage-contract.md',
]
sources += [str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name not in ['receipt.json','source-manifest.json','check-output.log']]
# Include original probe receipts but not this collector's self-referential receipt.
sources += [str(p.relative_to(ROOT)) for p in HERE.glob('run-*/receipt.json')]
manifest = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(set(sources))}
(HERE / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
summary = 'PASS evidence integrity: 19 PostgreSQL pattern cases; 20 required hosted integration cases remain unexecuted.\n'
(HERE / 'check-output.log').write_text(summary)
receipt = {
    'schema': 1,
    'status': 'contract-candidate-with-passing-postgresql-pattern-probe',
    'reviewer': 'producer-only-root-freeze-pending',
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': [sys.executable, str(pathlib.Path(__file__).resolve())],
    'python': sys.version,
    'platform': platform.platform(),
    'revision': subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
    'source_manifest_sha256': hashlib.sha256((HERE/'source-manifest.json').read_bytes()).hexdigest(),
    'output_sha256': hashlib.sha256(summary.encode()).hexdigest(),
    'executed_pattern_probe': 'run-3/receipt.json',
    'executed_case_count': 19,
    'required_unexecuted_hosted_case_count': 20,
    'earlier_attempts': {
        'run-1': 'PostgreSQL could not start: Unix socket path exceeded OS bound; directory removed, log confirms shut down.',
        'run-2': 'Column UPDATE grant alone did not admit lock rows through RLS. Real race assertion failed; server stopped and directory removed.',
    },
    'corrections': ['command-log-correction.json preserves one original descriptive stdin entry and exact source-derived SQL; outputs unchanged.'],
    'limitations': [
        'Pattern SQL uses small synthetic probe tables/functions, not proposed complete hosted schema or production migrations.',
        'No hosted authorization, repository context, startup guard, HTTP/provider integration or protocol port was implemented or tested.',
        'No cloud/production resource, real credential, customer communication, UI/native runtime or physical phone activity.',
        'User resumed computer/simulator/emulator use while lane ran; this assigned lane remained host-only. Phones deferred.',
        'No GA gate verified; root/independent review and 20 full integration cases remain pending.',
    ],
    'cleanup': probe['cleanup'],
}
(HERE/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(summary, end='')
