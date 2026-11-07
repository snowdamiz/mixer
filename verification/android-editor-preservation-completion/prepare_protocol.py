#!/usr/bin/env python3
"""Prepare/freeze only this lane's immutable protocol subpacket; no product edit."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import sys

D = Path(__file__).resolve().parent
R = D.parents[1]
P = D / 'protocol-1'
C = R / 'verification/android-editor-focus-history-correction'
F = R / 'verification/android-editor-focus-history-independent/actual-review/findings-1'


def ident(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def verify(base, expected):
    seal = base / 'seal.json'
    assert ident(seal)['sha256'] == expected, str(seal)
    document = json.loads(seal.read_bytes())
    count = size = 0
    for member in document['members']:
        name = Path(member['path'])
        assert not name.is_absolute() and '..' not in name.parts
        path = base / name
        assert path.resolve().is_relative_to(base.resolve())
        assert ident(path) == {'bytes': member['bytes'], 'sha256': member['sha256']}, str(path)
        count += 1
        size += member['bytes']
    return document, {'path': str(seal.relative_to(R)), **ident(seal),
                      'members_verified': count, 'member_bytes_verified': size}


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    assert ident(source) == ident(target)


if sys.argv[1:] == ['prepare']:
    assert not P.exists(), 'Protocol destination exists; use a new immutable subpacket'
    candidate, producer = verify(C, '2ebf7634886be778b06ecdfa0ab2a9ac69d14a473b88a7f6ea623ccddfcd5af8')
    findings, independent = verify(F, 'a0cf5e8bff8ffee66f277b5e83c76b2778db13bd8eac558ae3ef65cdc007f5fd')
    assert producer['members_verified'] == 5325 and producer['member_bytes_verified'] == 24030540
    assert independent['members_verified'] == 22 and independent['member_bytes_verified'] == 1416134
    requirements = R / 'verification/android-editor-boundary-root-review/preservation-completion-requirements.md'
    assert ident(requirements)['sha256'] == '91159240131bc0a107f321e3571345755c24c9651ed8ad7b3cc63ba784103187'
    sources = {p.name: ident(p) for p in sorted((C / 'source').glob('*.java'))}
    assert len(sources) == 16
    digest = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert digest == candidate['product_source_tree_digest'] == '2d0a89dac0c629b7257a75dfa42dee3794f021c558300f968fc4d8baaaecba01'
    for source in sorted((F / 'source').glob('*.java')):
        assert ident(source) == sources[source.name], 'Independent finding source differs: ' + source.name
    P.mkdir()
    for name in ('protocol.md', 'test-plan.md', 'prepare_protocol.py'):
        copy(D / name, P / name)
    for name in ('AGENTS.md', 'PLAN.md', 'mixer-product-plan.md'):
        copy(R / name, P / 'inputs/workspace' / name)
    for source in sorted((C / 'source').glob('*.java')):
        copy(source, P / 'inputs/source' / source.name)
    for source in sorted((C / 'tests').glob('*.java')):
        copy(source, P / 'inputs/prior-tests' / source.name)
    for name in ('seal.json', 'findings.md', 'controls/FocusHistoryControls.java'):
        copy(F / name, P / 'inputs/findings-1' / name)
    contracts = (
        'cleanup-contract-selection.json', 'replacement-amendment.md',
        'replacement-dispatch-amendment.md', 'focus-history-amendment.md',
        'focus-history-internal-protocol.md', 'focus-history-event-reentry-amendment.md',
        'focus-history-protocol-selection.json', 'focus-history-event-reentry-selection.json',
        'preservation-completion-requirements.md',
    )
    B = R / 'verification/android-editor-boundary-root-review'
    for name in contracts:
        copy(B / name, P / 'inputs/contracts' / name)
    copy(R / 'verification/android-editor-cleanup-contract-independent/required-addendum.md',
         P / 'inputs/contracts/cleanup-required-addendum.md')
    copied = {str(p.relative_to(P / 'inputs')): ident(p)
              for p in sorted((P / 'inputs').rglob('*')) if p.is_file()}
    save(P / 'input-custody.json', {
        'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_context_revision_supplied_only': '4e7c21ee82def176bfe857dba2fa243eb8b4ebb1',
        'git_accessed': False, 'producer': producer, 'permitted_findings': independent,
        'product_tree': digest, 'product_files': sources, 'copied_inputs': copied,
        'other_active_actual_review_read_enumerated_or_hashed': False,
        'native_ui_capture_or_process_inventory_started_or_queried': False,
    })
    save(P / 'preparation-receipt.json', {
        'schema': 1, 'argv': [sys.executable, str(Path(__file__).relative_to(R)), 'prepare'],
        'python': sys.version, 'executable': str(Path(sys.executable).resolve()),
        'script': ident(Path(__file__)), 'status': 'protocol-input-custody-passed',
        'scope': 'Offline sealed input verification and exact protocol/test design only',
        'requested_lane_model': 'gpt-6.1-sol', 'requested_reasoning_effort': 'xhigh',
        'product_source_edited': False, 'product_execution_or_compilation_performed': False,
        'dependent_implementation_selected': False, 'canonical_native_publicV2_OTA_or_GA_accepted': False,
        'commands_spawned_by_script': [], 'scratch_created': False, 'cleanup_required': False,
        'cleanup': 'No child, native instance, compiler output or scratch created; no process inventory performed',
        'preparatory_lookup_limit': 'One read-only rg lookup used an absent FocusHistoryTests.java name; actual FocusHistoryControls.java was then read. No product command failed.',
        'pending': ['Root and independent protocol/signature selection',
                    'Complete-source derivative, host/cross tests and independent actual-source review',
                    'Native runtime/UI/capture/physical checks remain paused',
                    'Canonical/publicV2/OTA/FieldLog/store/operations/GA acceptance'],
    })
    print(json.dumps({'status': 'protocol-input-custody-passed', 'producer_members': 5325,
                      'finding_members': 22, 'product_files': 16, 'product_tree': digest}, sort_keys=True))
elif sys.argv[1:] == ['freeze']:
    assert P.is_dir() and not (P / 'seal.json').exists()
    copy(D / 'prepare.stdout', P / 'commands/prepare.stdout')
    copy(D / 'prepare.stderr', P / 'commands/prepare.stderr')
    assert not (D / 'prepare.stderr').read_bytes()
    output = json.loads((D / 'prepare.stdout').read_bytes())
    assert output['status'] == 'protocol-input-custody-passed'
    assert ident(D / 'protocol.md') == ident(P / 'protocol.md')
    assert ident(D / 'test-plan.md') == ident(P / 'test-plan.md')
    assert ident(Path(__file__)) == ident(P / 'prepare_protocol.py')
    members = [{'path': str(p.relative_to(P)), **ident(p)}
               for p in sorted(P.rglob('*')) if p.is_file()]
    document = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'scope': 'Standalone private preservation outcome protocol and prospective actual-source test contract only',
                'verdict': 'recommend-for-independent-design-review',
                'product_tree': output['product_tree'], 'implementation_selected': False,
                'native_or_GA_accepted': False, 'members': members,
                'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members)}
    save(P / 'seal.json', document)
    print(json.dumps({'status': 'frozen-design-only', 'seal': str((P / 'seal.json').relative_to(R)),
                      **ident(P / 'seal.json'), 'member_count': document['member_count'],
                      'member_bytes': document['member_bytes']}, sort_keys=True))
else:
    raise SystemExit('Expected prepare or freeze')
