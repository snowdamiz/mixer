#!/usr/bin/env python3
"""Freeze this owned producer foundation; this grants no review acceptance."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'verification/swift-ordered-retention-analyzer-library'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as file:
        while block:=file.read(65536):h.update(block)
    return h.hexdigest()
def write(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def row(path):return {'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path)}

def main():
    assert not (PACKET/'seal.json').exists(), 'Frozen packets are immutable; do not refreeze in place'
    run=PACKET/'commands/run-8'; receipt=json.loads((run/'result.json').read_bytes());assert receipt['passed']
    for source in receipt['sources_after']:assert row(ROOT/source['path'])==source
    input_paths=[
        'AGENTS.md','PLAN.md','mixer-product-plan.md',
        'docs/swift-ordered-retention-analyzer.md','docs/swift-ordered-retention-analyzer-review.md',
        'verification/swift-ordered-retention-analyzer-design/interface_schema.py',
        'verification/swift-ordered-retention-analyzer-root-review/acceptance.json',
        'verification/swift-ordered-retention-analyzer-design/inputs/verification__swift-ordered-retention-diagnostic-rust__writer.rs',
        'verification/swift-ordered-retention-analyzer-design/inputs/verification__swift-ordered-retention-diagnostic-rust__observer.rs',
        'verification/swift-ordered-retention-analyzer-design/inputs/verification__swift-ordered-retention-diagnostic-rust__source-code-table.json',
    ]
    inputs=[]
    for relative in input_paths:
        source=ROOT/relative;destination=PACKET/'inputs'/relative.replace('/','__')
        assert not destination.exists();shutil.copy2(source,destination)
        inputs.append({**row(source),'snapshot':str(destination.relative_to(ROOT))})
    write(PACKET/'inputs/manifest.json',inputs)
    bootstrap=[
      {'scope':'read-only initial environment discovery','command':'cat verification/swift-ordered-retention-analyzer-design/input* verification/swift-ordered-retention-analyzer-design/*receipt*; git rev-parse HEAD; rustc --version --verbose',
       'observed_stderr':'zsh:1: no matches found: verification/swift-ordered-retention-analyzer-design/*receipt*\nzsh:1: command not found: rustc\n',
       'resolution':'Use the exact compiler path from the accepted design receipt; no PATH/toolchain mutation'},
      {'scope':'read-only source discovery','command':'rg -n rustc verification/swift-ordered-retention-analyzer-design/commands/run-3/executed-runner.py',
       'observed_stderr':'rg: verification/swift-ordered-retention-analyzer-design/commands/run-3/executed-runner.py: No such file or directory (os error 2)\n',
       'resolution':'Read the existing run-3 result.json; no missing file fabricated'},
      {'scope':'first owned runner attempt','command':'/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-ordered-retention-analyzer-library/run_checks.py',
       'observed_failure':'run-1 AssertionError at assert len(sidecars)==17: final directory contains13; remaining4 are candidate-completion-6',
       'resolution':'Preserve run-1 runner/source/result; enumerate both immutable stream subdirectories in subsequent runs'},
      {'scope':'owned inventory prose patch','tool':'apply_patch',
       'observed_failure':'apply_patch verification failed: Failed to find expected lines in logical-inventory.md: caller receiving/move places. Its21',
       'resolution':'Read the actual lines and applied exact correction; failed patch changed no file'},
    ]
    write(PACKET/'commands/bootstrap/failed-discovery-and-edit-attempts.json',bootstrap)
    (PACKET/'commands/run-1/runner-exception.tool-output.txt').write_text('Preserved from initial tool output (runner-v1 did not capture its own exception):\n'
      '{"run": 1, "passed": false, "result": "verification/swift-ordered-retention-analyzer-library/commands/run-1/result.json"}\n'
      'Traceback (most recent call last):\n'
      '  File "/Users/andreyyurlov/Documents/dev/mixer/verification/swift-ordered-retention-analyzer-library/run_checks.py", line 106, in <module>\n'
      "    if __name__ == '__main__': main()\n"
      '                               ~~~~^^\n'
      '  File "/Users/andreyyurlov/Documents/dev/mixer/verification/swift-ordered-retention-analyzer-library/run_checks.py", line 72, in main\n'
      "    sidecars = sorted(history.glob('*.sidecar.json')); assert len(sidecars) == 17\n"
      '                                                              ^^^^^^^^^^^^^^^^^^^\nAssertionError\n')
    assert not any(path.is_file() for path in (PACKET/'scratch').rglob('*'))
    versions={name:(run/(name+'.stdout')).read_text() for name in ['rust-version','python-version']}
    inventory=json.loads((PACKET/'logical-inventory.json').read_bytes())
    source_manifest=[row(PACKET/relative) for relative in ['src/analyzer.rs','tests/fixture_tests.rs','inventory.py','run_checks.py','freeze.py','logical-inventory.md']]+[row(ROOT/'docs/swift-ordered-retention-analyzer-library.md')]
    final={'schema':1,'at_unix':time.time(),'status':'producer-fixture-foundation-frozen-for-independent-review',
      'scope':'First safe-File library boundary only; closed framing is not semantic prefix validity',
      'revision_start':receipt['revision_start'],'revision_end':receipt['revision_end'],
      'source_tree_sha256':hashlib.sha256(json.dumps(source_manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
      'source_manifest':source_manifest,'tested_library_tree_sha256':receipt['source_tree_sha256'],
      'final_test_receipt':str((run/'result.json').relative_to(ROOT)),'producer_methods':20,
      'explicit_record_field_negatives':249,'all_field_header_footer_words':64,
      'historical_sidecars_invalid_failure15':17,'historical_footer_grammar_refused':7,'historical_footer_only_observed':10,
      'versions':versions,'tools':receipt['tools'],'upstream_before':receipt['upstream_before'],'upstream_after':receipt['upstream_after'],
      'steps_ceiling':268435456,'arena_bytes':8388608,'transient_ceiling':65536,'rust_report_bytes':49152,'aggregate_report_ceiling':65536,
      'inventory':{'named_role_upper':inventory['named_role_upper_total'],'reserved':inventory['reserved_total'],'unused_margin':inventory['unassigned_margin'],'kind':inventory['kind']},
      'allocation_count':1,'public_api':'analyze_fixture(&mut File,&mut File,&mut File,&mut File)->Result<ReplayOutcome,AnalyzerError>',
      'context_schema':'MIXFIX01 fixture-only 8192; not VerifiedBindingView','fullReplayAccepted':False,'storedPrefixValidated':False,
      'semantic_metrics_available':False,'real_adapters_available':False,'self_acceptance':False,
      'withheld':['semantic acquisition FSM/cache/token/eviction policy','source-bound failure code/kind/resource/stage applicability','real profile/selection/original-result/custody adapters','cryptographic verification','host acceptance record/classifier','CLI/inherited FD adoption','source preparer','writer correction/live VM/Cargo/dependencies','target driver/full Swift workload','native/device/signing/store/customer/operations/published-package FieldLog/GA'],
      'cleanup':receipt['cleanup'],'failed_attempts_preserved':['bootstrap tool outputs','run-1 runner assertion','run-2 five fixture test failures','run-4 one fixture test ordering failure'],
      'note':'Root commits/pushes metadata only after separate review; no semantic or GA gate promoted'}
    write(PACKET/'final-receipt.json',final)
    excluded={PACKET/'seal.json',PACKET/'seal.sha256'}
    members=sorted([ROOT/'docs/swift-ordered-retention-analyzer-library.md']+[p for p in PACKET.rglob('*') if p.is_file() and p not in excluded])
    seal={'schema':1,'scope':final['scope'],'excluded':[str(p.relative_to(ROOT)) for p in sorted(excluded)],'members':[row(p) for p in members]}
    write(PACKET/'seal.json',seal);digest=sha(PACKET/'seal.json');(PACKET/'seal.sha256').write_text(digest+'  seal.json\n')
    for member in seal['members']:assert row(ROOT/member['path'])==member
    print(json.dumps({'seal_sha256':digest,'members':len(members),'bytes':sum(member['bytes'] for member in seal['members']),'producer_methods':20,'self_acceptance':False}))

if __name__=='__main__':main()
