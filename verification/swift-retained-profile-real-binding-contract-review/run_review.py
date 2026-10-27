"""Reproduce bounded frozen-data review; writes only this review directory."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT/'verification/swift-retained-profile-real-binding-preparation'
EXPECTED='e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')

def sha(data):return hashlib.sha256(data).hexdigest()
def identity(path):
    p=Path(path);data=p.read_bytes()
    return {'path':str(p),'bytes':len(data),'sha256':sha(data)}
def custody():
    data=(FROZEN/'seal.json').read_bytes();assert sha(data)==EXPECTED
    seal=json.loads(data)
    assert len(seal['members'])==seal['member_count']==69
    assert sum(m['bytes'] for m in seal['members'])==seal['member_bytes']==859841
    for m in seal['members']:
        data=(FROZEN/m['path']).read_bytes()
        assert len(data)==m['bytes'] and sha(data)==m['sha256'],m['path']
    actual={str(p.relative_to(FROZEN)) for p in FROZEN.rglob('*') if p.is_file()}
    assert actual=={m['path'] for m in seal['members']}|{'seal.json'}
    return {'seal_sha256':EXPECTED,'members':69,'bytes':859841,'exact_file_set':True}
def declarations():
    evidence=json.loads((FROZEN/'source-evidence.json').read_text())
    fragments=evidence['actual_data_declarations']['fragments']
    data=b'#![allow(dead_code)]\n'
    for item in fragments:
        source=(FROZEN/'inputs'/item['path']).read_bytes()
        a,b=item['first_line'],item['last_line']
        data+=f"// Exact {item['path']}:{a}-{b}\n".encode()+b''.join(source.splitlines(keepends=True)[a-1:b])
    assert data==(FROZEN/'actual_data_records.rs').read_bytes()
    return {'exact_extracted_declarations':True,'fragments':fragments,'bytes':len(data),'sha256':sha(data)}

def main():
    before=custody();extraction=declarations();receipts=[]
    source_names=['codec_controls.rs','context_gap_controls.py','run_review.py']
    source_before={name:identity(HERE/name) for name in source_names}
    logs=HERE/'logs';logs.mkdir(exist_ok=True)
    def run(label,args,cwd):
        started=time.monotonic()
        result=subprocess.run([str(x) for x in args],cwd=cwd,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=45)
        for suffix,data in [('stdout',result.stdout),('stderr',result.stderr)]:
            (logs/f'{label}.{suffix}').write_bytes(data)
        receipts.append({'label':label,'argv':[str(x) for x in args],'cwd':str(cwd),
            'timeout_seconds':45,'elapsed_seconds':time.monotonic()-started,'exit_code':result.returncode,
            'terminally_waited':True,'stdout':identity(logs/f'{label}.stdout'),'stderr':identity(logs/f'{label}.stderr')})
        (HERE/'command-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
        assert result.returncode==0,label
        return result.stdout.decode()
    revision=run('revision',['git','rev-parse','HEAD'],ROOT).strip()
    rust_version=run('rustc-version',[RUSTC,'-Vv'],HERE)
    scratch=Path(tempfile.mkdtemp(prefix='scratch-',dir=HERE))
    binaries=[]
    try:
        for name in ['actual_data_records.rs','context_contract.py','test_context_contract.py']:
            shutil.copyfile(FROZEN/name,scratch/name)
        shutil.copyfile(HERE/'context_gap_controls.py',scratch/'context_gap_controls.py')
        (scratch/'review.rs').write_bytes((FROZEN/'typed_wire_proposal.rs').read_bytes()+b'\n'+(HERE/'codec_controls.rs').read_bytes())
        for mode,flags in [('debug',[]),('optimized',['-O'])]:
            binary=scratch/f'codec-{mode}'
            run(f'compile-{mode}',[RUSTC,'--edition=2021','--test',scratch/'review.rs',*flags,'-o',binary],HERE)
            binaries.append(identity(binary))
            run(f'codec-{mode}',[binary,'--test-threads=1'],HERE)
        run('python-context',[sys.executable,'-B','-m','unittest','-v','test_context_contract.py','context_gap_controls.py'],scratch)
    finally:shutil.rmtree(scratch)
    assert custody()==before
    own_sources={name:identity(HERE/name) for name in source_names}
    assert own_sources==source_before,'review source changed during checks'
    report={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'closed-independent-contract-review-controls-pass','frozen_custody_before_after':before,
        'declaration_extraction':extraction,'git_revision_context':revision,
        'source_revision_caveat':'Concurrent repository revision is context only; reviewed bytes are the sealed packet and own source digests.',
        'frozen_source_revision_context':json.loads((FROZEN/'seal.json').read_text())['source_revision_context'],
        'review_sources':own_sources,'review_source_tree_sha256':sha(json.dumps(own_sources,sort_keys=True,separators=(',',':')).encode()),
        'python_version':sys.version,'python_identity':identity(Path(sys.executable).resolve()),
        'rustc_version':rust_version,'rustc_identity':identity(RUSTC),'platform':platform.platform(),
        'binaries_executed_then_removed':binaries,'commands':len(receipts),
        'rust_methods_each_mode':21,'frozen_rust_methods_each_mode':14,'independent_rust_methods_each_mode':7,
        'python_methods':15,'frozen_python_methods':12,'independent_framing_gap_methods':3,
        'scratch_removed':not scratch.exists(),'actual_product_behavior_executed':False,
        'native_runtime_simulator_emulator_UI_capture_process_inventory_used':False,
        'forbidden_harness_or_active_lane_read':False,'canonical_index_or_git_mutation':False,
        'provenance_semantic_replay_FieldLog_OTA_GA_accepted':False}
    (HERE/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ['status','commands','rust_methods_each_mode','python_methods','scratch_removed']}))

if __name__=='__main__':main()
