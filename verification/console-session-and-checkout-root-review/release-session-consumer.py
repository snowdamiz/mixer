"""Verify the frozen producer bytes and release independent review, not acceptance."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/console-browser-session-consumer'
DEST = OUT / 'session-consumer-frozen-release.json'

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

assert not DEST.exists(), 'One-shot; do not replay'
seal = json.loads((PACKET / 'seal.json').read_bytes())
assert seal['evidence_digest_sha256'] == 'c19baeea77aa8d9a53e436a16ad4fd39b5a9781b206ec4f152e843b5785fcb99'
names = {'seal.json'}
for item in seal['files']:
    name = PurePosixPath(item['path'])
    assert not name.is_absolute() and '..' not in name.parts and str(name) not in names
    actual = row(PACKET / name)
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
    names.add(str(name))
assert {str(path.relative_to(PACKET)) for path in PACKET.rglob('*') if path.is_file()} == names
manifest = json.loads((PACKET / 'source-manifest.json').read_bytes())
assert manifest['source_digest_sha256'] == '7cd673b6b2c729c60586b0506ef57e0d063183046c76ffab5c44f6b3f88314b8'
assert len(manifest['files']) == 65
for item in manifest['files']:
    assert row(ROOT / item['path']) == item
    copy_path = PACKET / 'frozen-inputs' / item['path']
    actual = row(copy_path)
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
receipt = json.loads((PACKET / 'receipt.json').read_bytes())
assert receipt['source_manifest_sha256'] == row(PACKET / 'source-manifest.json')['sha256']
assert len(receipt['owned_files']) == 8
assert receipt['producer_validation']['complete_console_regression']['outer_pass'] == 149
assert receipt['cleanup']['all_captured_command_and_version_groups_absent']
assert all(not attempt['timed_out'] and attempt['cleanup']['group_absent_after_cleanup'] for attempt in receipt['attempts'])
assert [attempt['exit_code'] for attempt in receipt['attempts']] == [1,1,0,0,0,0]
preaccess = ROOT / 'verification/console-browser-session-consumer-independent'
assert row(preaccess / 'preaccess-oracles.md')['sha256'] == '58969cf14bb489ff3d3ddce7b2963ee3d762b153facc344beb4bd933a9491f36'
value = {'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).relative_to(ROOT))],
    'status':'producer-candidate-released-for-independent-review-only','implementation_accepted':False,
    'seal':row(PACKET/'seal.json'),'evidence_members_verified':len(seal['files']),
    'source_manifest':row(PACKET/'source-manifest.json'),'source_files_verified':65,
    'owned_files':receipt['owned_files'],'producer_receipt':row(PACKET/'receipt.json'),
    'producer_outer_tests_passed':149,'nested_new_Solid_tests_passed':10,'nested_existing_Solid_tests_passed':4,
    'typecheck_and_production_build_passed':True,'original_failed_attempts_preserved':2,
    'preaccess_oracles':row(preaccess/'preaccess-oracles.md'),'independent_probes_prepared':42,
    'independent_review_ownership':str(preaccess.relative_to(ROOT)),
    'scope':'Host synthetic session metadata and event fixtures, actual cookie client and Solid integration. Backend session/cookie endpoints absent; browser/provider/native/GA remain pending.',
    'compiler_lane':'free after corrected Rust producer terminal roster; independent console host review next',
    'root_test_replay':False,'GA_verified':0}
with DEST.open('x') as stream:
    json.dump(value,stream,indent=2)
    stream.write('\n')
w=json.loads((ROOT/'work-graph.json').read_bytes())
g=json.loads((ROOT/'gates/ga.json').read_bytes())
for target in [w['packages'][13],g['gates'][21]]:
    target['browserSessionConsumer'].update({'status':'producer-frozen-independent-review-active','root_frozen_release':row(DEST),
        'source_digest':manifest['source_digest_sha256'],'producer_outer_tests_passed':149,
        'nested_new_Solid_tests_passed':10,'nested_existing_Solid_tests_passed':4,
        'implementation_accepted':False,'independent_review_ownership':str(preaccess.relative_to(ROOT))})
for name,data in [('work-graph.json',w),('gates/ga.json',g)]:
    (ROOT/name).write_text(json.dumps(data,indent=2)+'\n')
for name in ['PLAN.md','STATUS.md']:
    path=ROOT/name
    text=path.read_text()
    old='The strict frontend session consumer is selected and implementation is active; current missing server endpoints must continue producing unavailable state.'
    new='The strict frontend session consumer is frozen for independent review: all 149 outer producer host tests, ten new and four existing nested Solid tests, typecheck and production build pass. Root verifies all 65 selected source files and the frozen evidence. Two initial failed attempts remain preserved. Current missing server endpoints still produce unavailable state; implementation acceptance remains pending.'
    assert text.count(old)==1
    path.write_text(text.replace(old,new))
subprocess.run(['git','diff','--check','--','PLAN.md','STATUS.md','work-graph.json','gates/ga.json'],cwd=ROOT,timeout=10,check=True)
print(json.dumps({'producer_evidence_members_verified':len(seal['files']),'selected_source_files_verified':65,'released_for_independent_review':True,'implementation_accepted':False}))
