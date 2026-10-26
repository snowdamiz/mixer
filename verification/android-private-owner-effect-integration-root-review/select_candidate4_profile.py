"""Select exact frozen4 source pairing for bounded CLI implementation/validation."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(name):
    n = PurePosixPath(name)
    assert not n.is_absolute() and '..' not in n.parts
    p = ROOT
    for part in n.parts:
        p /= part
        assert not p.is_symlink()
    assert p.is_file()
    return p
checkpoint = safe('verification/android-private-owner-independent-review/implementation-review-3/checkpoint-first10/manifest.json')
assert sha(checkpoint) == 'd12dd7f879ab399900d26f5fbd559254ac495d4c4f6fe94b6430ab0ca6945087'
seal = json.loads(checkpoint.read_bytes())
for name, m in seal['files'].items():
    p = safe(name)
    assert p.stat().st_size == m['bytes'] and sha(p) == m['sha256']
assert len(seal['files']) == 181 and sum(m['bytes'] for m in seal['files'].values()) == 2285541
r = json.loads((checkpoint.parent / 'receipt.json').read_bytes())
assert r['unique_controls'] == 10 and r['actual_assertions'] == 55
assert all(c['exit_code'] == 0 for c in r['controls'])
admission = OUT / 'candidate-4-admission.json'
assert sha(admission) == 'dabbcb66df621c37238d358adb54c89abfce006c399f4ad4eba1373c746eb5ea'
candidate = ROOT / 'verification/android-private-owner-integration-implementation/candidate-4'
assert sha(candidate / 'manifest.json') == r['candidate_manifest_sha256']
for name, m in json.loads((candidate / 'source-map.json').read_bytes()).items():
    p = safe(name)
    assert p.stat().st_size == m['bytes'] and sha(p) == m['sha256']
profile = candidate / 'profile-proposal.json'
assert sha(profile) == 'fa20572d64d0cec8e2bbfd959df6a2993b4e231cca6f3f8009761bd0b2678d62'
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': sys.argv, 'python': sys.version, 'script_sha256': sha(Path(__file__)),
    'context_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'status': 'exact-frozen4-profile-selected-for-CLI-rebinding-and-bounded-host-validation',
    'candidate_admission': admission.relative_to(ROOT).as_posix(), 'candidate_admission_sha256': sha(admission),
    'candidate_manifest_sha256': r['candidate_manifest_sha256'], 'canonical_sources_reverified': 309,
    'independent_checkpoint': checkpoint.relative_to(ROOT).as_posix(), 'independent_checkpoint_sha256': sha(checkpoint),
    'independent_members_verified': 181, 'independent_bytes_verified': 2285541,
    'independent_controls_passed': 10, 'independent_assertions': 55,
    'profile_proposal': profile.relative_to(ROOT).as_posix(), 'profile_proposal_sha256': sha(profile),
    'profile_id': 'mixer.android-source-pair.3', 'adapter_members':22,'sdk_members':22,
    'adapter_projection_sha256':'57606aa94648f3b43f1bd84cc5d7479be133e3ff3c948d4830b1645466f348f6',
    'sdk_projection_sha256':'4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7',
    'ownership':['cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/Resources/android-build.py','cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift','cli/Tests/MixerBuildTests/AndroidProjectTests.swift','cli/build-tests/test_android_sdk_compatibility.py','verification/android-private-owner-profile3-integration/candidate4-qualification/**','docs/android-private-owner-profile3-integration.md'],
    'selected_scope':'Replace only candidate3 adapter identities/projection with exact frozen4 proposal, preserving compiled ID3, SDK/default/wire. Validate actual isolated Debug/Release CLI, common preaccess, direct driver, copied exports and app-owned host consumer. No lock auto-migration.',
    'supersedes_CLI_validation_hold':'candidate-3-gate-finding-and-hold.json for these exact frozen4 bytes only; candidate3 remains rejected',
    'native_source_mutations_authorized':False,'CLI_validation_authorized':True,'canonical_delivery_authorized_by_this_receipt':False,
    'full_independent_source_barrier_legacy_matrix_pending':True,'implementation_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False,
}
path=OUT/'candidate-4-profile-selection.json'
assert not path.exists()
path.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path)}))
