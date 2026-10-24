#!/usr/bin/env python3
"""Check archived bytes and actual compiler/runtime-list evidence; no interpreter."""
from pathlib import Path
import ast, datetime, hashlib, json, os, re, subprocess, sys, tarfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'results'
sha=lambda b:hashlib.sha256(b).hexdigest()
serialize=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
receipt=json.loads((OUT/'receipt.json').read_text())
assert receipt['status']=='passed-type-and-borrow-probes-only'
assert receipt['originalVMSourceBeforeAfterVerified']
manifest=json.loads((OUT/'source-manifest.json').read_text())
assert sha((OUT/'source-manifest.json').read_bytes())==receipt['sourceManifestSHA256']
assert sha(serialize(manifest))==receipt['baseSourceTreeDigest']
assert sha((OUT/'source.tar.gz').read_bytes())==receipt['archiveSHA256']
with tarfile.open(OUT/'source.tar.gz') as tf:
    raw={m.name.removeprefix('vm/'):tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
assert {n:sha(b) for n,b in raw.items()}==manifest
for name,digest in receipt['probeInputs'].items():
    assert sha((OUT/'probe-inputs'/name).read_bytes())==digest
    assert sha((HERE/name).read_bytes())==digest
collector=ast.parse((OUT/'probe-inputs/collect.py').read_text())
negative=next(ast.literal_eval(n.value) for n in collector.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id=='negative' for t in n.targets))
for variant in receipt['variants']:
    derived=dict(raw)
    if variant['name']!='base-layout':
        borrowed='src/experimental/execution/borrowed.rs'
        derived[borrowed]+=b'\n#[path = "algorithm_contract_probe.rs"]\npub(crate) mod algorithm_contract_probe;\n'
        derived['src/experimental/execution/algorithm_contract_probe.rs']=(OUT/'probe-inputs/common_probe.rs').read_bytes()
        derived['src/experimental_swift_reactor/execution.rs']+=b'\n'+(OUT/'probe-inputs/swift_probe.rs').read_bytes()+negative.get(variant['name'],'').encode()
    observed={n:sha(b) for n,b in derived.items()}
    assert observed==json.loads((ROOT/variant['manifest']).read_text())
    assert sha(serialize(observed))==variant['sourceTreeDigest']
commands=receipt['commands']
assert len(commands)==11
for command in commands:
    log=(ROOT/command['log']).read_bytes()
    assert sha(log)==command['sha256']
    if command['name'] in negative:
        assert command['exit']!=0
        expected={'view-cache-mutation':'error[E0502]',
            'view-static-escape':'error: lifetime may not live long enough',
            'wasi-dispatch-during-cache-phase':'error[E0499]'}[command['name']]
        assert expected in log.decode()
    else: assert command['exit']==0
positive=[c for c in commands if c['name'] in ['all-positive-debug','all-positive-release','swift-positive-debug','swift-positive-release']]
assert len({c['target'] for c in positive})==4
binary_receipts=[]
for command in positive:
    text=(ROOT/command['log']).read_text()
    match=re.search(r'Running unittests src/lib.rs \(([^\n]+)\)',text)
    assert match
    binary=Path(match.group(1));assert binary.is_relative_to(Path(command['target']))
    before=sha(binary.read_bytes())
    p=subprocess.run([str(binary),'shared_algorithm_contract','--list'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
    assert p.returncode==0
    assert sha(binary.read_bytes())==before
    names=[l for l in p.stdout.decode().splitlines() if l.endswith(': test')]
    expected=4 if command['name'].startswith('all') else 3
    assert len(names)==expected and all('shared_algorithm_contract' in n for n in names)
    log=OUT/(command['name']+'-runtime-list.log');log.write_bytes(p.stdout)
    binary_receipts.append(dict(command=command['name'],binary=str(binary),sha256=before,
        testCount=len(names),testNames=names,runtimeListSHA256=sha(p.stdout)))
comparison=json.loads((OUT/'frozen-layout-comparison.json').read_text())
assert comparison['equal'] and len(comparison['lines'])==41
# This is a source-bound artifact check, not additional compilation or semantics.
result=dict(schema='mixer-shared-algorithm-contract-artifact-check-v1',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='passed-artifact-bindings-and-runtime-test-lists-only',
    receiptSHA256=sha((OUT/'receipt.json').read_bytes()),sourceFiles=len(manifest),
    baseSourceTreeDigest=receipt['baseSourceTreeDigest'],variantsVerified=len(receipt['variants']),
    commandsVerified=len(commands),frozenLayoutLines=len(comparison['lines']),binaries=binary_receipts,
    contractSHA256=sha((ROOT/'docs/swift-shared-executor-algorithm-contract.md').read_bytes()),
    prerequisites={name:sha((ROOT/name).read_bytes()) for name in [
        'AGENTS.md','docs/swift-executor-stage-contract.md',
        'docs/swift-reactor-execution-stage-design.md',
        'verification/swift-executor-stage-acceptance.json',
        'docs/swift-executor-construction-acceptance.md']},
    pending=['Implementation, semantic/work/allocation parity and complete simultaneous accounting',
        'Remaining mode adapter bodies and root acceptance',
        'Full target execution, physical devices, published FieldLog and GA gates'])
evidence=OUT/'artifact-check.json'
if '--write' in sys.argv or not evidence.exists():
    evidence.write_bytes(serialize(result))
else:
    retained=json.loads(evidence.read_text())
    assert {k:v for k,v in retained.items() if k!='observedUTC'} == {k:v for k,v in result.items() if k!='observedUTC'}, 'retained artifact evidence differs'

print(json.dumps({k:result[k] for k in ['status','sourceFiles','variantsVerified','commandsVerified','frozenLayoutLines']},indent=2))
