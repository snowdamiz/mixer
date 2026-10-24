#!/usr/bin/env python3
"""Refine only the test-inclusive public prefix packet; retain prior evidence."""
from pathlib import Path
import json, hashlib, tarfile, subprocess
# Reuse the exact host-only runner definitions without executing its old matrix.
HERE = Path(__file__).resolve().parent
runner = HERE/'collect.py'
namespace={'__file__':str(runner),'__name__':'_frozen_runner_definitions'}
exec(compile(runner.read_text().split("(OUT/'inputs').mkdir()",1)[0],str(runner),'exec'),namespace)
globals().update(namespace)
PRIOR=HERE/'results/20261024T032202022153Z'
old=json.loads((PRIOR/'receipt.json').read_text())
STATUS='failed-trap-prefix-refinement'
(OUT/'inputs').mkdir()
for name in ['refine_trap.py','collect.py','private_probes.rs']:
    (OUT/'inputs'/name).write_bytes((HERE/name).read_bytes())
try:
    assert old['status']=='host-bounded-executable-parity-complete-root-review-pending'
    save('inherited-receipt.json',old)
    old_variants={}
    for item in old['variants']:
        with tarfile.open(PRIOR/item['archive']) as tar:
            old_variants[item['name']]={m.name.removeprefix('vm/'):tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    candidate=dict(old_variants['candidate']);candidate['tests/span_control_extraction.rs']=(ROOT/'vm/tests/span_control_extraction.rs').read_bytes()
    baseline=dict(old_variants['baseline']);baseline['tests/span_control_extraction.rs']=candidate['tests/span_control_extraction.rs']
    variants={name:freeze(name,files) for name,files in [('baseline',baseline),('candidate',candidate)]}
    assert {name for name in candidate if candidate[name]!=old_variants['candidate'][name]}=={'tests/span_control_extraction.rs'}
    save('tools.json',json.loads((PRIOR/'tools.json').read_text()))
    for mode,feature in [('span',['--features','experimental-span-execution']),('all',['--all-features'])]:
        for profile,release in [('debug',False),('release',True)]:
            outputs={}
            for name in ['baseline','candidate']:
                outputs[name]=build_tests(name+'-'+mode+'-'+profile,variants[name],feature,release,['span_control_extraction'])['span_control_extraction']
            def traces(text):
                result=[]
                for line in text.splitlines():
                    for marker in ['control_trace ','control_warm ','control_validation_ceiling ']:
                        at=line.find(marker)
                        if at>=0:result.append(line[at:]);break
                return result
            left,right=traces(outputs['baseline']),traces(outputs['candidate'])
            assert left==right
            PARITY.append(dict(mode=mode,profile=profile,target='span_control_extraction',records=len(left),traceSHA256=hashlib.sha256(encoded(left)).hexdigest()))
    for name,data in candidate.items(): assert (ROOT/'vm'/name).read_bytes()==data,name
    STATUS='host-bounded-executable-parity-complete-root-review-pending'
finally:
    receipt=dict(schema=2,status=STATUS,sourceRevision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),acceptedBaselineTreeSHA256=old['acceptedBaselineTreeSHA256'],variants=VARIANTS,commands=COMMANDS,binaries=BINARIES,parity=PARITY,inheritedReceipt='../20261024T032202022153Z/receipt.json',inheritedReceiptSHA256=sha(PRIOR/'receipt.json'),inheritedScope={'include':['All successful final candidate Frozen regressions: span_execution, span_execution_allocations, span_numeric_extraction in four configurations','Corrected baseline/candidate mod.rs-only actual-owner private probes in four configurations','Twelve Swift-value regressions in Swift/all features x Debug/Release','Eight ordinary feature/profile checks, fmt, Clippy','Exact archived baseline Frozen regression outputs explicitly inherited by the prior packet'],'exclude':['Prior span_control_extraction runtime results: replaced by this complete refined six-test matrix','All first-attempt extra-file/lib-alias derived probes: excluded from qualifying scope'],'dependencyProof':'Only tests/span_control_extraction.rs changed; no inherited regression/unit/library target compiles or imports that integration-test file. Complete before/after manifests and archives retained.'},productHooksAdded=False,swiftInvocation=False,nativeRuntime=False,physicalRuntime=False,publication=False,gaAcceptance=False,limitations=old['limitations'])
    save('receipt.json',receipt)
    print(str(OUT/'receipt.json'),flush=True)
