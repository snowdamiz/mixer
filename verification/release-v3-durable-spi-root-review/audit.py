#!/usr/bin/env python3
"""Read-only audit of the sealed metadata candidate; write only root's receipt."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = ROOT / 'verification/release-v3-durable-spi'
sha = lambda value: hashlib.sha256(value).hexdigest()
digest = lambda path: sha(path.read_bytes())

def require(ok, label):
    if not ok:
        raise RuntimeError(label)

def main():
    final = OWNER / 'final-receipt.json'
    require(digest(final) == '7f0a737eb8e544c849a1e11bde4a4c0187c613c0774e8f9ef3c1bb2034007e41', 'owner seal')
    sealed = json.loads(final.read_text())
    path = OWNER / '2026-10-23-candidate-1/receipt.json'
    require(digest(path) == sealed['qualification_receipt_sha256'], 'qualification receipt')
    r = json.loads(path.read_text())
    require(len(r['source_files']) == 71 and len(r['commands']) == 31, 'expected matrix')
    for name, expected in r['source_files'].items():
        require(digest(ROOT / name) == expected, 'live source ' + name)
        require(digest(Path(r['immutable_source_export']) / name) == expected, 'export source ' + name)
    for command in r['commands']:
        raw = (ROOT / command['log']).read_bytes()
        require(sha(raw) == command['sha256'], 'command log ' + command['name'])
        require(command['exit_code'] == command['expected_exit'], 'command result ' + command['name'])
        if 'expected_tests' in command:
            seen = [int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed', raw)]
            require(seen == [command['expected_tests']], 'test count ' + command['name'])
        if 'required_diagnostic_fragment' in command:
            require(command['required_diagnostic_fragment'].encode() in raw, 'negative diagnostic')
    artifact_count = 0
    for artifacts in r['artifacts'].values():
        for artifact in artifacts:
            p = Path(artifact['path'])
            require(p.stat().st_size == artifact['bytes'] and digest(p) == artifact['sha256'], 'retained artifact ' + str(p))
            artifact_count += 1
    for name, expected in r['preserved_old_updates_files'].items():
        old = subprocess.check_output(['git', 'show', r['baseline_revision'] + ':' + name], cwd=ROOT)
        require(sha(old) == expected and (ROOT / name).read_bytes() == old, 'baseline bytes ' + name)
    source = (ROOT / 'updates/Sources/MixerUpdates/VerifierV3.swift').read_text()
    pattern = r'(?m)^[ \t]*// BEGIN additive CapabilityDurableV3 metadata SPI\.\n[\s\S]*?^[ \t]*// END additive CapabilityDurableV3 metadata SPI\.\n\n?'
    require(len(re.findall(pattern, source)) == 3, 'exact three additive blocks')
    require(sha(re.sub(pattern, '', source).encode()) == r['baseline_v3_sha256'], 'existing v3 bytes')
    manifest = OWNER / 'evidence-manifest.sha256'
    require(digest(manifest) == sealed['evidence_manifest_sha256'], 'owner evidence manifest')
    rows = manifest.read_text().splitlines()
    require(len(rows) == sealed['evidence_files'] == 87, 'owner evidence count')
    for row in rows:
        expected, name = row.split('  ', 1)
        require(digest(OWNER / name) == expected, 'owner evidence ' + name)
    commands = json.loads((HERE / 'commands.json').read_text())
    require(len(commands) == 2 and all(c['exit_code'] == 0 for c in commands), 'root commands')
    require('PASS 204 independent SPI metadata checks' in (HERE / 'probe.log').read_text(), 'root probe result')
    binary = ROOT / 'updates/.build/root-durable-spi-review'
    archive = Path(commands[0]['argv'][commands[0]['argv'].index('-L') + 1]) / 'libMixerUpdates.a'
    receipt = {
        'status': 'root source and sealed-evidence audit passed; 204 independent external SPI checks passed',
        'owner_final_receipt_sha256': digest(final), 'owner_qualification_receipt_sha256': digest(path),
        'source_manifest_sha256': r['source_manifest_sha256'], 'sources_verified': 71,
        'old_files_verified': len(r['preserved_old_updates_files']), 'existing_v3_bytes_exact': True,
        'owner_commands_verified': 31, 'owner_evidence_files_verified': 87, 'retained_artifacts_verified': artifact_count,
        'probe_checks': 204, 'shared_retained_manifest_cases': 154, 'shared_offer_assignment_cases': 36,
        'commands': commands, 'binary': {'path': str(binary), 'sha256': digest(binary)},
        'linked_release_archive': {'path': str(archive), 'sha256': digest(archive)},
        'evidence_sha256': {p.name: digest(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'receipt.json'},
        'scope': 'Original non-testable external consumer using SPI, standard signing and shared malformed-input corpus; immutable candidate source/log/artifact audit.',
        'limitations': [
            'Retained evidence checks signatures and payload, not actual committed-health provenance; private updater integration remains required.',
            'The retained path omits only root time windows. Current-time methods remain strict; revoked roots and foreign verifier contexts are rejected.',
            'No guest execution, durable selection, production publication, final app link, physical device or GA qualification.',
            'Retained actual artifacts are identified, not claimed bit-reproducible. Host Debug products were subsequently rebuilt for TSan; root linked Release.'
        ]
    }
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('status', 'sources_verified', 'owner_commands_verified', 'probe_checks')}, indent=2))

if __name__ == '__main__':
    main()
