#!/usr/bin/env python3
"""Seal all retained review evidence, or independently verify the existing seal."""
import datetime,gzip,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def data_digest(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
if sys.argv[1:]==['--verify']:
    seal=json.loads((HERE/'seal.json').read_bytes())
    actual={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and '.build' not in p.parts and p!=HERE/'seal.json'}
    assert actual==seal['files'];assert data_digest(actual)==seal['tree_sha256']
    print(json.dumps({'status':'verified','files':len(actual),'tree_sha256':seal['tree_sha256']},sort_keys=True));sys.exit(0)
assert not (HERE/'seal.json').exists(),'Do not overwrite a sealed review'
main=json.loads((HERE/'candidate-1/receipt.json').read_bytes());env=json.loads((HERE/'environment-1/receipt.json').read_bytes())
assert main['status']==env['status']=='passed'
assert main['swift_debug_release_equal'] and main['all_java_mode_outputs_equal']
for candidate,receipt in [('candidate-1',main),('environment-1',env)]:
    for p,digest in receipt['source_manifest'].items():
        assert sha((ROOT/p).read_bytes())==sha((HERE/candidate/'inputs'/p).read_bytes())==digest,p
    for c in receipt['commands']:
        assert c['exit_code']==0;assert sha((ROOT/c['output']).read_bytes())==c['output_sha256']
for p,digest in json.loads((HERE/'candidate-1/producer-evidence-bindings.json').read_bytes()).items():assert sha((ROOT/p).read_bytes())==digest,p
for mode in ['debug','release']:
    for key,suffix in [('tsv','.tsv.gz'),('values','.values.jsonl.gz')]:
        raw=gzip.decompress((HERE/'candidate-1'/(mode+'-oracle'+suffix)).read_bytes())
        assert sha(raw)==main[mode+'_oracle'][key]['sha256']
    for execution in ['default','interpreted']:
        archive=(HERE/'candidate-1'/(mode+'-'+execution+'.jsonl.gz')).read_bytes()
        assert sha(archive)==main[mode+'_'+execution]['archive_sha256']
        assert sha(gzip.decompress(archive))==main[mode+'_'+execution]['sha256']
acceptance={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'decision':'accepted-independent-private-immutable-appearance-data-review',
 'reviewer':'android_resolution_independent_review','root_integration_acceptance':'pending separate root decision',
 'source_revision':main['source_revision'],'source_manifest_sha256':main['source_manifest_sha256'],
 'java_resolver_sha256':main['source_manifest']['native/android/app/src/dev/mixer/android/AppearanceResolutionV1.java'],
 'swift_resolver_sha256':main['source_manifest']['sdk/Sources/MixerUI/AppearanceResolutionV1.swift'],
 'canonical_descriptor_sha256':main['source_manifest']['verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json'],
 'bindings':{p:sha((HERE/p).read_bytes()) for p in ['candidate-1/receipt.json','environment-1/receipt.json','candidate-1/producer-evidence-bindings.json','README.md','ReviewOracle.swift','ReviewProbe.java','make_review_cases.py','check_review_outputs.py','verify.py','EnvironmentProbe.java','verify_environment.py','seal.py']},
 'source_bindings':main['source_manifest'],'source_stability_checks':main['unchanged_source_checks'],
 'producer_evidence_stability_checks':main['unchanged_producer_evidence_checks'],'environment_source_stability_checks':env['unchanged_source_checks'],
 'modes':['Swift Debug / Java default','Swift Debug / Java -Xint','Swift Release / Java default','Swift Release / Java -Xint'],
 'cases_per_mode':187,'common_admitted_per_mode':98,'malformed_rejected_per_mode':86,'known_packet_boundaries_per_mode':3,
 'nodes_per_mode':4432,'styles_per_mode':17728,'java_assertions_per_mode':595286,'independent_contract_assertions_per_mode':40756,'direct_environment_assertions_per_java_mode':214,
 'immutable_containers_per_mode':16535,'final_fields_per_mode':440433,'extra_identity_packet_probes_per_mode':6,
 'swift_debug_release_equal':True,'all_java_mode_outputs_equal':True,'java_release17_class_major':61,
 'actionable_blockers':[],
 'known_pending_packet_boundaries':['explicit hStack firstTextBaseline','explicit hStack lastTextBaseline','nested scrolling list'],
 'limits':'Host pure data only. Provisional sharedCandidate1. No ART, native widget/resource/font/display/signing/geometry/raster/interaction/accessibility/IME/device/FieldLog/store/customer/operational/GA authority. All GA gates remain open; phones stay disconnected.',
 'seal_command':'python3 -B verification/android-appearance-resolution-independent-review/seal.py'}
(HERE/'acceptance.json').write_text(json.dumps(acceptance,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and '.build' not in p.parts and p!=HERE/'seal.json'}
seal={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'tree_sha256':data_digest(files),'excludes':'Ephemeral .build directories only; compiled hashes are retained in runtime receipts.'}
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'status':'sealed','files':len(files),'tree_sha256':seal['tree_sha256'],'acceptance_sha256':sha((HERE/'acceptance.json').read_bytes())},sort_keys=True))
