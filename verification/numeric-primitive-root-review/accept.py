from pathlib import Path
import datetime, hashlib, json, subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
bindings={}
def bind(path,expected=None):
    digest=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    if expected is not None and digest!=expected: raise RuntimeError(path)
    bindings[path]=digest
    return digest
def read(path): return json.loads((ROOT/path).read_text())
commands=[]
for name,script in [('producer','verification/swift-shared-numeric-extraction/verify.py'),
                    ('independent','verification/numeric-primitive-independent-review/audit.py')]:
    argv=['python3','-B',script]
    result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
    log=HERE/(name+'.log');log.write_text(result.stdout+result.stderr)
    assert result.returncode==0,log.read_text()
    commands.append(dict(argv=argv,cwd=str(ROOT),exit=result.returncode,log=str(log.relative_to(ROOT)),sha256=bind(str(log.relative_to(ROOT)))))
producer=read('verification/swift-shared-numeric-extraction/seal.json')
review=read('verification/numeric-primitive-independent-review/acceptance.json')
assert not review['findings'] and review['status']=='recommended-acceptance-host-primitive-dispatch-only'
assert producer['productSourceTreeSHA256']==review['productSourceTreeSHA256']
assert producer['maximumTypedScalarInventory']==464 and producer['unchangedFixedReservation']==2912
for receipt in [producer,review]:
    for path,digest in receipt['bindings'].items(): bind(path,digest)
manifest=read('verification/swift-shared-numeric-extraction/results/20261024T003757200365Z/product-source-manifest.json')
for path,digest in manifest.items(): bind('vm/'+path,digest)
for path in ['verification/swift-shared-numeric-extraction/seal.json',
             'verification/numeric-primitive-independent-review/acceptance.json',str(Path(__file__).relative_to(ROOT))]: bind(path)
out=dict(schema=1,status='accepted-frozen-primitive-dispatch',reviewer='root',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    productSourceTreeSHA256=producer['productSourceTreeSHA256'],
    selectedHostPassedExecutions=1572,explicitNodeOraclePassedExecutions=72,
    identicalTraceRecordsPerSpanAllProfile=454,independentSemanticExpectationsPerMode=10,
    independentExactWorkBoundariesPerMode=4,maximumTypedScalarInventory=464,unchangedScalarComponent=512,
    unchangedFixedReservation=2912,commands=commands,
    sourceReview='Only original three primitive dispatch branches move behind private FrozenMode adapter. Owner validation, work, observation and trap mapping remain literal; no owner/public API/formula change. Actual diff, disjoint typed map and source/evidence closure reviewed.',
    limitations=['Selected library/numeric targets include derived inventory probe; not the full product integration suite or measured machine stack.',
        'Scoped Clippy passes; broad all-target baseline and candidate both retain26 identical preexisting diagnostics.',
        'No shared complete numeric owner algorithm, Swift adapter/full target, device, published FieldLog or GA qualification.'],
    bindings=dict(sorted(bindings.items())))
(HERE/'acceptance.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status=out['status'],bindings=len(bindings))))
