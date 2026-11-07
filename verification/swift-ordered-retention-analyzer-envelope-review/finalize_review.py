#!/usr/bin/env python3
"""Seal this rejected-candidate review and all retained scoped evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
DOC = ROOT / 'docs/swift-ordered-retention-analyzer-envelope-review.md'
PRODUCER = ROOT / 'verification/swift-ordered-retention-analyzer-envelope'
SEAL = 'ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae'

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(65536): digest.update(block)
    return digest.hexdigest()

def member(path):
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=sha(path))

def check_seal(path, digest, count):
    assert sha(path)==digest
    value=json.loads(path.read_text()); assert len(value['members'])==count
    for row in value['members']:
        p=ROOT/row['path']; assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
    return dict(path=str(path.relative_to(ROOT)),sha256=digest,members=count,bytes=sum(row['bytes'] for row in value['members']))

def main():
    producer=check_seal(PRODUCER/'seal.json',SEAL,796)
    original=json.loads((BASE/'implementation-review-1/frozen-final-receipt.json').read_text())
    upstream=[]
    for packet in original['upstream_before']:
        upstream.append(check_seal(ROOT/'verification'/packet['packet']/'seal.json',packet['sha256'],packet['members']))
    assert sum(row['members'] for row in upstream)==2512
    assert not (BASE/'scratch').exists()
    assert not list(BASE.rglob('__pycache__'))
    public=BASE/'implementation-review-1/public/run-2/receipt.json'
    private=BASE/'implementation-review-1/private/run-2/receipt.json'
    api=BASE/'implementation-review-1/api-probes/run-1/receipt.json'
    assert json.loads(public.read_text())['passed']
    assert json.loads(api.read_text())['passed']
    private_stdout=BASE/'implementation-review-1/private/run-2/private-tests.stdout'
    assert '9 passed; 1 failed' in private_stdout.read_text()
    owned_sources=[BASE/name for name in ['prepare.py','prepare_vectors.py','prepare_public_harness.py','public_fixture_harness.rs',
        'generated_public_cases.rs','correct_profile_vector.py','run_public.py','private_boundary_tests.rs','run_private.py','finalize_review.py']]
    rows=[member(p) for p in owned_sources]
    receipt=dict(schema=1,at_unix=time.time(),command=[sys.executable,'-B',str(Path(__file__).relative_to(ROOT))],
        python=sys.version,revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        verdict='withhold-frozen-candidate-acceptance-R1-private-poison-latch',
        scope='Independent separate safeFile fixture-envelope boundary/source review only',
        producer=producer,upstream=upstream,upstream_members_unchanged=2512,
        producer_source_tree_sha256='ebd0ff925a58b36dd22f7f7012b6693a854ddd4ce29eac7116963175d027a3ec',
        producer_source_hashes=original['source_hashes'],review_sources=rows,
        review_source_tree_sha256=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        public=dict(methods_passed=33,receipt=str(public.relative_to(ROOT)),receipt_sha256=sha(public),
            pre_access_expectations_unchanged=True,profile_word_correction='corrected-vectors/profile-correction-1/correction.json'),
        api=dict(positive_compiles=1,expected_negative_compiles=5,receipt=str(api.relative_to(ROOT)),receipt_sha256=sha(api)),
        private=dict(methods_passed=9,methods_failed=1,methods_attempted=10,receipt=str(private.relative_to(ROOT)),receipt_sha256=sha(private),
            failed_control='review_poison_marker_prevents_any_later_leaf_call',failure_stdout_sha256=sha(private_stdout)),
        finding=dict(id='R1',accepted_by_root=True,scope='Private defensive/fault contract; normal public constructor emits consistentstatus3/reason15',
            summary='finalize recognizes reason15 poison with staleObservedstatus1, but leaf_pending permits another leaf call for same retainedreply',
            receipt='implementation-review-1/finding-R1.json',receipt_sha256=sha(BASE/'implementation-review-1/finding-R1.json')),
        independent64_regression=dict(status='unqualified-timeout',methods_qualified=0,limit_seconds=60,partial_stdout_available=False,
            evidence='implementation-review-1/private/run-1',limitation='First runner failed to persist TimeoutExpired stdout; killed/reaped direct Rust test child, no child subprocess launch path',
            root_stopped_additional_replay_on_rejected_candidate=True),
        cleanup=dict(owned_scratch_absent=True,bytecode_absent=True,children_returned_or_timeout_killed_reaped=True,
            initial_timeout='Direct child killed/reaped by subprocess.run; no separate owned group existed, no shared-group kill attempted',
            corrected_runner='Dedicated owned sessions; timeout output retained, killpg+communicate/reap before exactscratch archive/removal',
            process_discovery=False),
        producer_mutations_by_reviewer=0,root_metadata_mutations=0,actual_ga_gate_or_reviewer_promotions=0,
        combined_lifetime_qualified=False,combined_debit_preflight_qualified=False,
        resource_review='Separate dedicated accounting lane; proposed G36/T20/F44/B192 and leaf111 remain unaccepted by this review',
        storedPrefixValidated=False,fullReplayAccepted=False,semanticMetricsValid=False,
        native_capture_or_device_execution=False,product_target_execution=False,
        preserved_history=['P1/P2 original proposal findings','zero-call reply-valid addendum','prepaid underfunded guard coordination',
            'original33vectors and failed profile packing attempt','exact one-word correctedprofile','both public attempts',
            'combined64timeout with missingpartialstdout limitation','private9pass/1fail and acceptedR1'],
        withheld=['Corrected producer source and separate exactfreeze review','Complete independent64 regression','Detailed combined resource proof',
            'Semantic acquisition/token/resident/victim/plan/metrics and sourcefailureapplicability','Real binding/profile/selection/originalresult/crypto/custody',
            'FD/CLI/sourcepreparer/hostauthority','Writer repair/liveVM/fullSwift target','Compiler/native/device/signing/store/customer/operations/publishedFieldLog/GA'])
    final=BASE/'final-receipt.json';final.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    excluded={BASE/'seal.json',BASE/'seal.sha256'}
    paths=[DOC]+[p for p in BASE.rglob('*') if p.is_file() and p not in excluded]
    assert all(not p.is_symlink() for p in paths)
    members=[member(p) for p in sorted(paths,key=lambda p:str(p.relative_to(ROOT)))]
    seal=BASE/'seal.json'
    seal.write_text(json.dumps(dict(schema=1,scope='Frozen independent rejected-candidate review; no acceptance authority',
        excluded=[str(p.relative_to(ROOT)) for p in sorted(excluded)],members=members),indent=2,sort_keys=True)+'\n')
    digest=sha(seal);(BASE/'seal.sha256').write_text(digest+'  '+str(seal.relative_to(ROOT))+'\n')
    for row in members:
        p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
    print(json.dumps(dict(seal_sha256=digest,members=len(members),bytes=sum(row['bytes'] for row in members),
        final_receipt_sha256=sha(final),public33=True,api_positive=1,api_expected_negative=5,private_passed=9,private_failed=1,independent64='unqualified-timeout',verdict=receipt['verdict'])))

if __name__=='__main__':main()
