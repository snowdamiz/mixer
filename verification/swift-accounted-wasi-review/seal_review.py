#!/usr/bin/env python3
"""Audit retained evidence bindings and seal the independent scoped decision."""
import datetime
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
CHECKS = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, success, **detail):
    CHECKS.append(dict(name=name, success=bool(success), **detail))


def descriptor(item, name):
    path = pathlib.Path(item['path'])
    if not path.is_absolute():
        path = ROOT / path
    check(name, path.is_file() and sha(path) == item['sha256']
          and ('bytes' not in item or path.stat().st_size == item['bytes']), path=str(path))


def local_receipt(path):
    data = json.loads(path.read_text())
    for command in data['commands']:
        for stream in ['stdout', 'stderr']:
            descriptor(command[stream], str(path.relative_to(ROOT)) + ':' + command['label'] + ':' + stream)
    for item in data.get('toolchain_files', []):
        descriptor(item, str(path.relative_to(ROOT)) + ':tool:' + item['path'])
    for key in ['snapshot_manifest', 'overlay_manifest', 'probe', 'source', 'source_manifests']:
        if isinstance(data.get(key), dict):
            descriptor(data[key], str(path.relative_to(ROOT)) + ':' + key)
    return data


owner_path = ROOT / 'verification/swift-accounted-wasi/final-v2/receipt.json'
owner = local_receipt(owner_path)
check('original canonical owner receipt digest', sha(owner_path) == 'd08ecf98930baa2981a76fcf931691a047a3351c123be455cbc6a022b885ae34')
descriptor(owner['source_manifest'], 'owner canonical source manifest binding')
owner_manifest = json.loads((ROOT / owner['source_manifest']['path']).read_text())
encoded = json.dumps(owner_manifest['files'], sort_keys=True, separators=(',', ':')).encode()
check('owner canonical tree digest', hashlib.sha256(encoded).hexdigest() == owner['source_tree_sha256'] == '05246b3a817a31cd243694224438008b002492faf29fc220846a796f5cbbdec2')
# Compare historical source to the historical review snapshot, not the repaired checkout.
for item in owner_manifest['files']:
    historical = BASE / '.build/original' / item['path']
    target = historical if historical.is_file() else ROOT / item['path']
    check('owner source:' + item['path'], target.is_file() and sha(target) == item['sha256'])

support_receipts = []
for relative in ['verification/swift-wasi-control-boundary/isolated-2/receipt.json',
                 'verification/swift-accounted-wasi-root-review/combined-3/receipt.json']:
    path = ROOT / relative
    data = json.loads(path.read_text())
    source = pathlib.Path(data['source'])
    for name, expected in data['source_files'].items():
        target = source / name
        check(relative + ':source:' + name, target.is_file() and sha(target) == expected)
    for command in data['commands']:
        descriptor(dict(path=command['log'], sha256=command['sha256']), relative + ':log:' + command['label'])
        check(relative + ':exit:' + command['label'], command['exit'] == 0 and command['source_stable'])
    check(relative + ':source archive', sha(ROOT / data['source_archive']) == data['source_archive_sha256'])
    collector_path = path.parent.parent / ('collect.py')
    check(relative + ':collector', collector_path.is_file() and sha(collector_path) == data['collector_sha256'])
    support_receipts.append(dict(path=relative, sha256=sha(path), passed=data.get('passed', True)))

independent = {}
for stage in ['original', 'repaired', 'final']:
    path = BASE / stage / 'receipt.json'
    data = local_receipt(path)
    check(stage + ':expectations', data['expectations_met'] and data['source_stable'])
    independent[stage] = dict(path=str(path.relative_to(ROOT)), sha256=sha(path))
parity_path = BASE / 'standalone-parity/receipt.json'
parity = local_receipt(parity_path)
check('external frozen-route parity', parity['success'] and parity['all_observations_equal'])

final_manifest = json.loads((BASE / 'final-source-manifest.json').read_text())
root_combined = json.loads((ROOT / 'verification/swift-accounted-wasi-root-review/combined-3/receipt.json').read_text())
for item in final_manifest['files']:
    check('final checkout:' + item['path'], sha(ROOT / item['path']) == item['sha256'])
    check('root combined source:' + item['path'], root_combined['source_files'].get(item['path']) == item['sha256'])
check('final root combined passed', root_combined['passed'])

wiring = b'#[cfg(feature = "experimental-swift-reactor")]\npub(crate) mod accounted;\n'
frozen = '020f909f2a32553b79ba7068a1798c85d97426b4'
for name in ['mod.rs', 'tests.rs', 'descriptor.rs', 'platform.rs']:
    relative = 'vm/src/experimental_wasi/' + name
    old = subprocess.check_output(['git', 'show', frozen + ':' + relative], cwd=ROOT)
    current = (ROOT / relative).read_bytes()
    if name == 'mod.rs':
        check('exact additive private wiring count', current.count(wiring) == 1)
        current = current.replace(wiring, b'')
    check('exact frozen standalone bytes:' + name, current == old)
check('accepted execution design unchanged', sha(ROOT / 'docs/swift-reactor-execution-stage-design.md') == '59708209438de44811f0ba7efa941ca9c9778067159e94728031f5a44a9af07b')

audit = dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             total_checks=len(CHECKS), passed=all(item['success'] for item in CHECKS), checks=CHECKS)
(BASE / 'binding-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
decision = dict(observed_utc=audit['observed_utc'],
    decision='Approve only the private accounted WASI prerequisite at the final source manifest; no remaining actionable source defect found in this scope.',
    accepted=audit['passed'], final_source_manifest=dict(path=str((BASE / 'final-source-manifest.json').relative_to(ROOT)), sha256=sha(BASE / 'final-source-manifest.json')),
    final_tree_sha256=final_manifest['tree_sha256'], binding_audit=dict(path=str((BASE / 'binding-audit.json').relative_to(ROOT)), sha256=sha(BASE / 'binding-audit.json')),
    baseline_revision=frozen, current_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
    independent_receipts=independent, standalone_parity=dict(path=str(parity_path.relative_to(ROOT)), sha256=sha(parity_path)), support_receipts=support_receipts,
    resolved_findings=[dict(priority='P2', title='First cleanup invariant lost the actual WASI observation',
        original='A successful ArgsSizesGet enters the context once, consuming work=69 and transfer=8. Cleanup first against a foreign control returned an immutable failure with wasi=None.',
        reproduction='The identical independent cleanup-first probe fails in original Debug/Release and passes in repaired/final Debug/Release.',
        fix='Root captures the actual context usage before cleanup and carries it through observed drop/refund/fault helpers; old helpers delegate None. All actual storage is still dropped before any refund.',
        accounting='The final persistent cleanup reservation explicitly includes six Option<WasiUsage> copies for local and observed call transfers; the frozen standalone context layout and constructor remain exact.')],
    verified_scope=[
        'One borrowed construction phase enlarges the existing control ticket before named wrappers; Rust rejects access/drop of the control while the phase remains active. Completion restores exactly the earlier bound; omission remains conservatively charged.',
        'Header and four buffers have inline non-Clone reservation tickets; nonuniform 13/13/17/17-byte admission and real allocator-null ordinals release all partial storage without allocation. Empty capacities retain tickets without allocating.',
        'Cleanup destroys each actual Vec and then the actual owner/header before refund; foreign cleanup destroys storage but cannot create room in either ledger. Terminal cleanup spends no work, allocates nothing, and retains the first failure.',
        'Only unchanged context counters meter actual WASI work/calls/transfer; the sealed owner pairing rejects foreign controls and the independent shared host counter refuses before adapter entry. No reconstructed/summed meter is authoritative.',
        'All 34 descriptors and four argument variants preserve exact standalone outcomes/memory/usage/captures. Seven actual in-adapter cancellation check ordinals preserve output rollback and immutable terminal causes. Guest exit including zero and u32::MAX remains terminal.',
        'Seven external privacy negatives reject access to private owner/phase/control/tickets/header helper, accounted standalone construction and deadline escape. Old-route external layout and all 136 observations match the frozen foundation in all eight configurations.',
        'Root combined final source matches every one of the 58 independently pinned VM files and passes its Debug/Release all-feature/oracle/lint/format commands; original owner and isolated-helper evidence is retained and audited as historical scope.'
    ],
    explicit_limits=[
        'Private prerequisite only. No Swift executable owner, cache/executor composition, actual 53,777,114-byte reactor allocation/initialize/invoke, or corpus qualification.',
        'Cancellation/deadline is cooperative. Original owner tests exercise actual OS random/clocks and earliest deadline inside the unchanged context; independent probes add deterministic cancellation and expired carried-deadline coverage, not hard preemption.',
        'Requested logical capacities and conservative named Rust object reservations exclude allocator overhead, RSS, compiler stack measurement and unowned caller allocations.',
        'The historical canonical owner receipt predates the cleanup diagnostics and reservation repair; final acceptance binds the independent final manifest and root combined-3, rather than relabeling that earlier receipt.',
        'No physical phones were discovered or used. Mobile/signing/store/publication/separate-repository FieldLog consumption/operational/GA evidence remains pending and is not implied.',
        'Review-only sources and evidence were written solely under verification/swift-accounted-wasi-review; no product edits, commits or pushes were performed by this reviewer.'
    ])
(BASE / 'receipt.json').write_text(json.dumps(decision, indent=2) + '\n')
print(json.dumps(dict(accepted=decision['accepted'], audit_checks=audit['total_checks'], failures=[x for x in CHECKS if not x['success']], receipt=str(BASE / 'receipt.json'))))
raise SystemExit(0 if decision['accepted'] else 1)
