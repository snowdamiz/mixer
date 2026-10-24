from pathlib import Path
import datetime, gzip, hashlib, json, subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
bindings={}
def read(path): return json.loads((ROOT/path).read_text())
def bind(path, expected=None):
    value=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    if expected is not None and value != expected: raise RuntimeError(path)
    bindings[path]=value
    return value
commands=[]
for name,args in [
    ('producer-seal',['verification/android-appearance-v2-resolution/verify_seal.py','candidate-5','--with-binaries','--check-live']),
    ('independent-seal',['verification/android-v2-resolver-independent-review/verify_seal.py','candidate-3','--with-binaries','--check-live'])]:
    argv=['python3',*args]
    process=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
    log=HERE/(name+'.log');log.write_text(process.stdout+process.stderr)
    assert process.returncode==0,log.read_text()
    commands.append(dict(argv=argv,cwd=str(ROOT),exit=process.returncode,log=str(log.relative_to(ROOT)),sha256=bind(str(log.relative_to(ROOT)))))
producer_base='verification/android-appearance-v2-resolution/candidate-5/'
review_base='verification/android-v2-resolver-independent-review/candidate-3/'
producer=read(producer_base+'receipt.json');review=read(review_base+'receipt.json')
assert producer['status']=='passed-pure-data-only-awaiting-independent-review'
assert review['status']=='passed-host-data-independent-review' and not review['findings']
assert len(review['mutations'])==8
for receipt,base in [(producer,producer_base),(review,review_base)]:
    for relative,digest in receipt['inputManifest'].items(): bind(relative,digest)
    for relative,artifact in receipt['artifacts'].items():
        assert (ROOT/relative).stat().st_size==artifact['bytes']
        bind(relative,artifact['sha256'])
    for command in receipt['commands']:
        assert (command['exitCode']!=0)==bool(command.get('expectedNonzero',False))
        for stream in ['stdout','stderr']:
            artifact=command[stream]
            bind(artifact['path'],artifact.get('storedSHA256',artifact['sha256']))
            data=(ROOT/artifact['path']).read_bytes()
            if artifact['path'].endswith('.gz'): data=gzip.decompress(data)
            assert len(data)==artifact['bytes'] and hashlib.sha256(data).hexdigest()==artifact['sha256']
    bind(base+'receipt.json')
for relative,digest in read(producer_base+'artifact-seal.json')['bindings'].items(): bind(relative,digest)
dex=read('verification/android-v2-resolver-root-review/dex-compile/receipt.json')
assert dex['status']=='passed-android-java-dex-compile'
for relative,digest in dex['sourceManifest'].items(): bind(relative,digest)
for relative,digest in dex['artifacts'].items(): bind('verification/android-v2-resolver-root-review/'+relative,digest)
for command in dex['commands']:
    assert command['exit']==0
    bind(command['log'],command['sha256'])
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',
    'verification/android-appearance-v2-resolution','verification/android-v2-resolver-independent-review',
    'verification/android-v2-resolver-root-review','docs/android-appearance-v2-resolution.md'],cwd=ROOT,text=True).splitlines()
for relative in paths:
    if relative.endswith('/acceptance.json'):continue
    assert '/build/' not in relative and '/.build/' not in relative and '__pycache__' not in relative
    bind(relative)
result=dict(schema=1,status='accepted-android-v2-pure-resolution',reviewer='root',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    producerInputTreeSHA256=producer['inputTreeSHA256'],independentInputTreeSHA256=review['inputTreeSHA256'],
    differentialCases=185,differentialAccepted=170,differentialRejected=15,producerAssertionsPerJVMMode=510724,
    independentPreparationsPerJVMMode=23,independentRejectionsPerJVMMode=115,independentAssertionsPerJVMMode=6279,
    detectedSemanticMutations=8,auditedActualNodeRecords=4807,auditedActualPaintStates=19228,auditedProfileRolePairs=72,
    javaApplicationSources=len(dex['sourceManifest']),dexArtifactBindings=len(dex['artifacts']),commands=commands,
    sourceReview='Raw packet plus complete canonical descriptor admission, immutable output, bounded preorder/row/frontier references, exact UInt64 strings, strict raw environment and full-state/profile/section behavior inspected. Prior packet restrictions remain explicit; no Java default theme table.',
    rootAuditCorrection='Initial root audit compared compressed command-log bytes with their uncompressed digest and stopped. Corrected audit independently checks stored digest, decompressed size and original digest; no product change.',
    limits=['Data-only resolver; D8 compile for minimumAPI28 does not execute the resolver in Android ART.',
        'No native environment/resource/font/required-operation support, rendering/layout/transaction or display authority.',
        'No signed V2, physical design parity, published FieldLog or GA qualification.'],
    bindings=dict(sorted(bindings.items())))
(HERE/'acceptance.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status=result['status'],bindings=len(bindings))))
