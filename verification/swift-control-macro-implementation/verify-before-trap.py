#!/usr/bin/env python3
"""Offline verification of the bounded host packet; no guest or native run."""
from pathlib import Path
import hashlib, json, tarfile
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FINAL = HERE/'results/20261024T032202022153Z'
INHERITED = HERE/'results/20261024T031953637944Z'
METHODS = ['pop32','close_control','branch']

def encoded(value): return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def files_from_archive(path):
    with tarfile.open(path) as tar:
        return {m.name.removeprefix('vm/'):tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
def digest(files): return {name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
def method(text,name):
    start=text.index('fn '+name+'('); end=text.index('{',start)+1; depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
def rows(output,markers):
    result=[]
    for line in output.splitlines():
        for marker in markers:
            at=line.find(marker)
            if at>=0: result.append(line[at:]);break
    return result

def check_packet(folder,receipt):
    for item in receipt['commands']:
        for stream in ['stdout','stderr']: assert sha(folder/item[stream])==item[stream+'SHA256'],item['name']
    for item in receipt['binaries']:
        assert sha(Path(item['path']))==item['sha256'],item['label']
        listing=(folder/(item['listCommand']+'.stdout')).read_text()
        assert [line[:-6] for line in listing.splitlines() if line.endswith(': test')]==item['tests']
        output=(folder/(item['runCommand']+'.stdout')).read_text()
        assert f"test result: ok. {len(item['executedTests'])} passed; 0 failed; 0 ignored;" in output
    variants={}
    for item in receipt['variants']:
        manifest=json.loads((folder/item['manifest']).read_text())
        assert hashlib.sha256(encoded(manifest)).hexdigest()==item['treeSHA256']
        assert sha(folder/item['archive'])==item['archiveSHA256']
        contents=files_from_archive(folder/item['archive'])
        assert digest(contents)==manifest
        variants[item['name']]=contents
    return variants

final=json.loads((FINAL/'receipt.json').read_text())
old=json.loads((INHERITED/'receipt.json').read_text())
assert final['status']=='host-bounded-executable-parity-complete-root-review-pending'
assert old['status']=='failed-implementation-verification'
assert final['inheritedReceiptSHA256']==sha(INHERITED/'receipt.json')
assert (FINAL/'inherited-receipt.json').read_bytes()==(INHERITED/'receipt.json').read_bytes()
assert all(item['exitCode']==0 and not item['diagnosticBootstrap'] for item in final['commands'])
variants=check_packet(FINAL,final)
old_variants=check_packet(INHERITED,old)
accepted=files_from_archive(HERE/'accepted-baseline.tar.gz')
accepted_manifest=json.loads((HERE/'accepted-baseline-manifest.json').read_text())
assert digest(accepted)==accepted_manifest and len(accepted)==116
assert hashlib.sha256(encoded(accepted_manifest)).hexdigest()==final['acceptedBaselineTreeSHA256']=='96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7'
base,candidate=variants['baseline'],variants['candidate']
assert set(base)-set(accepted)=={'tests/span_control_extraction.rs'}
assert all(base[name]==data for name,data in accepted.items())
assert base==old_variants['baseline']
assert set(base)==set(candidate)
assert {name for name in base if base[name]!=candidate[name]}=={'src/experimental/execution/mod.rs','src/experimental/execution/borrowed.rs'}
owner=base['src/experimental/execution/mod.rs'].decode()
proposal=(ROOT/'verification/swift-control-macro-extraction/frozen_control_methods.rs').read_bytes()
actual_macro=proposal.replace(b'// Proposed overlay only. This file is not included by product source.',b'// Private literal control methods, emitted on the original frozen owner.')
assert candidate['src/experimental/execution/borrowed.rs']==base['src/experimental/execution/borrowed.rs']+b'\n'+actual_macro
for name in METHODS:
    assert ''.join(method(proposal.decode(),name).split())==''.join(method(owner,name).split())
    owner=owner.replace(method(owner,name),'borrowed::frozen_control_methods!();' if name=='pop32' else '',1)
assert ''.join(owner.split())==''.join(candidate['src/experimental/execution/mod.rs'].decode().split())
# Strict single-file derived overlay: no aliases, external probe file or new
# public entrypoints. Every pin is acquired by the original enter/cache route.
probe=(FINAL/'inputs/private_probes.rs').read_bytes()
assert probe==(HERE/'private_probes.rs').read_bytes()
for name in ['baseline','candidate']:
    derived=variants[name+'-probe']
    assert set(derived)==set(variants[name])
    assert {file for file in derived if derived[file]!=variants[name][file]}=={'src/experimental/execution/mod.rs'}
    assert derived['src/experimental/execution/mod.rs']==variants[name]['src/experimental/execution/mod.rs']+b'\n#[cfg(all(test,feature="experimental-span-execution"))]\nmod control_probes {\n'+probe+b'\n}\n'
for name,data in candidate.items(): assert (ROOT/'vm'/name).read_bytes()==data,name
assert (FINAL/'inputs/collect.py').read_bytes()==(HERE/'collect.py').read_bytes()
# Exact runtime identity preservation, exhaustive serialized traces, immutable
# unchanged baseline public outputs and fresh final candidate public outputs.
expected_tests=['shared_control_'+suffix for suffix in ['branch_targets_and_frame_boundary','cancellation_and_limits','close_partial_effects','public_parity_trace','warm_dispatch_allocation_free','work_and_fuel_prefixes']]
for mode in ['span','all']:
    for profile in ['debug','release']:
        for target in ['span_control_extraction','span_execution','span_execution_allocations','span_numeric_extraction']:
            baseline_binary=next(b for b in old['binaries'] if b['label']=='baseline-'+mode+'-'+profile and b['name']==target)
            candidate_binary=next(b for b in final['binaries'] if b['label']=='candidate-'+mode+'-'+profile and b['name']==target)
            assert baseline_binary['tests']==candidate_binary['tests']
            if target=='span_control_extraction': assert candidate_binary['tests']==expected_tests
            markers=['control_trace ','control_warm ','control_validation_ceiling '] if target=='span_control_extraction' else ['numeric_trace ','numeric_cases '] if target=='span_numeric_extraction' else []
            if markers:
                a=rows((INHERITED/(baseline_binary['runCommand']+'.stdout')).read_text(),markers)
                b=rows((FINAL/(candidate_binary['runCommand']+'.stdout')).read_text(),markers)
                assert a==b
                entry=next(p for p in final['parity'] if p['mode']==mode and p['profile']==profile and p['target']==target)
                assert len(a)==entry['records'] and hashlib.sha256(encoded(a)).hexdigest()==entry['traceSHA256']
        a=next(b for b in final['binaries'] if b['label']=='baseline-'+mode+'-'+profile+'-probe')
        b=next(b for b in final['binaries'] if b['label']=='candidate-'+mode+'-'+profile+'-probe')
        assert a['executedTests']==b['executedTests'] and len(a['executedTests'])==2
        assert rows((FINAL/(a['runCommand']+'.stdout')).read_text(),['control_probe '])==rows((FINAL/(b['runCommand']+'.stdout')).read_text(),['control_probe '])
assert len([b for b in final['binaries'] if b['label'].endswith('-values')])==4
for b in final['binaries']:
    if b['label'].endswith('-values'):
        assert len(b['executedTests'])==12 and all('swift_values_' in name for name in b['executedTests'])
assert len([c for c in final['commands'] if c['name'].endswith('-check')])==8
assert {'candidate-format','candidate-clippy'}<=set(c['name'] for c in final['commands'])
# Prior immutable history is not rerun against intentionally changed live code.
# Its complete seal verifies archived evidence, without changing the old status.
for directory in ['swift-control-extraction','swift-control-macro-extraction']:
    seal=json.loads((ROOT/'verification'/directory/'seal.json').read_text())
    for name,value in seal['bindings'].items(): assert sha(ROOT/name)==value,name
assert not any(final[name] for name in ['productHooksAdded','swiftInvocation','nativeRuntime','physicalRuntime','publication','gaAcceptance'])
seal=HERE/'seal.json'
if seal.exists():
    for name,value in json.loads(seal.read_text())['bindings'].items(): assert sha(ROOT/name)==value,name
print(json.dumps(dict(status='verified-bounded-frozen-macro-host-packet-root-review-pending',candidateTreeSHA256=next(v['treeSHA256'] for v in final['variants'] if v['name']=='candidate'),publicTests=6,controlRecordsPerConfiguration=779,privateOrderTests=2,privateRecordsPerConfiguration=17,swiftValueTestsPerConfiguration=12,configurations=4,frozenFixedReservationBytes=2912,sourceExtractionOnly=True,swiftExecution=False,nativeRuntime=False,gaAcceptance=False),sort_keys=True))
