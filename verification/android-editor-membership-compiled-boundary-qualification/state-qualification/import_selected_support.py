from pathlib import Path
import datetime, hashlib, json, shutil, signal

S = Path(__file__).resolve().parent
Q = S.parent
R = Q.parents[1]
D = S / 'full-candidate-v1'
OUT = S / 'selected-support-custody.json'
if OUT.exists():
    raise SystemExit('retained import receipt exists')
signal.alarm(60)

def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

packets = [
    ('verification/android-editor-preservation-membership-independent/actual-review/review-seal.json', '8d51b0e6d04b152621e9e6f9ad3b6c46b3301853ed5d0c545fd4781a66c36c6d'),
    ('verification/android-renderer-finite-membership-controls/seal.json', 'e901741635c6827b0d14b70c51248ea64a5a4071defd0d8a4c58c9fbdb904f93'),
    ('verification/android-renderer-finite-ledger-constructor/seal.json', '43ee31803039e416efa224e8ae67654b27d073035587da11c66a3d6b8adf9fd6'),
    ('verification/android-editor-membership-compiled-boundary-qualification/passive-return-probe-v4/seal.json', '8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8'),
]
receipts = []
for name, expected in packets:
    seal = R / name
    assert identity(seal)['sha256'] == expected, name
    payload = json.loads(seal.read_bytes())
    members = payload['members']
    if isinstance(members, list):
        assert len({item['path'] for item in members}) == len(members)
        members = {item['path']: {'bytes': item['bytes'], 'sha256': item['sha256']} for item in members}
    actual = {str(path.relative_to(seal.parent)) for path in seal.parent.rglob('*') if path.is_file() and path != seal}
    assert actual == set(members), (name, sorted(actual - set(members)), sorted(set(members) - actual))
    total = 0
    for rel, item in members.items():
        path = seal.parent / rel
        assert not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(seal.parent.resolve())
        assert identity(path) == item, (name, rel)
        total += item['bytes']
    receipts.append({'seal': name, 'seal_sha256': expected, 'members_verified': len(members), 'member_bytes': total, 'closed_pathset': True})

selections = {
    'verification/android-editor-boundary-root-review/passive-return-probe-v4-acceptance.json': 'cb9b8481827d4e5966e68292b447f610f67061cff9b997bf32da8c26f0ffec16',
    'verification/android-editor-boundary-root-review/renderer-finite-controls-selection.json': 'bec646c6b6d40e722795108349fd21e1156fb3504a29e64cd726d5c2da6adcc0',
    'verification/android-editor-boundary-root-review/renderer-ledger-constructor-selection.json': 'e069338e0c3273b8f270614aa4b938f3271d293efccc560337017fc389a5b7e7',
}
for name, expected in selections.items():
    assert identity(R / name)['sha256'] == expected

copies = [
    'verification/android-editor-preservation-membership-independent/actual-review/independent-controls/IndependentMembershipControls.java',
    'verification/android-editor-preservation-membership-independent/actual-review/selected-controls/SelectedIdentityMembershipReviewControls.java',
    'verification/android-editor-preservation-membership-independent/actual-review/selected-controls/IndependentOwnForwardControls.java',
    'verification/android-renderer-finite-membership-controls/FiniteMembershipControls.java',
    'verification/android-renderer-finite-ledger-constructor/FiniteRendererLedgerConstructorControls.java',
]
copied = []
for name in copies:
    source = R / name
    destination = D / source.name
    assert not destination.exists(), destination
    shutil.copyfile(source, destination)
    assert identity(destination) == identity(source)
    copied.append({'source': name, 'destination': str(destination.relative_to(R)), **identity(destination)})
OUT.write_text(json.dumps({'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'packets': receipts, 'selections': selections, 'copied_unmodified': copied, 'scope': 'Exact selected finite/original control source custody. Fresh execution and full semantic/closure qualification pending.'}, indent=2) + '\n')
signal.alarm(0)
print(json.dumps({'verified_members': sum(item['members_verified'] for item in receipts), 'copied_sources': len(copied)}))
