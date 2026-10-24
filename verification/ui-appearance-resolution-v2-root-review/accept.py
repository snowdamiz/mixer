from pathlib import Path
import datetime, hashlib, json, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
bindings = {}
def read(relative):
    return json.loads((ROOT / relative).read_text())
def bind(relative, expected=None):
    actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    if expected is not None and actual != expected:
        raise RuntimeError('Binding mismatch: ' + relative)
    bindings[relative] = actual
    return actual

producer_base = 'verification/ui-appearance-resolution-v2/candidate-1/'
review_base = 'verification/ui-appearance-resolution-v2-independent-review/'
producer = read(producer_base + 'receipt.json')
review = read(review_base + 'review.json')
execution = read(review_base + 'candidate-4/receipt.json')
count = read(producer_base + 'count-audit.json')
assert producer['status'] == 'passed-pure-v2-data-and-compilation-only'
assert review['status'] == 'accepted-pure-data-scope-only' and not review['findings']
assert execution['status'] == 'passed-independent-pure-data-review'
assert producer['sourceTreeSHA256'] == review['sourceTreeSHA256'] == execution['sourceTreeSHA256']
assert producer['inputManifest'] == execution['inputManifest']
assert review['producerTestsPerBuild'] == 127 and review['producerNewResolutionTestsPerBuild'] == 21
assert review['baselineCasesPerBuild'] == 133 and len(review['mutationMismatchCases']) == 6
assert all(n > 0 for n in review['mutationMismatchCases'].values())
for relative, digest in review['bindings'].items():
    bind(relative, digest)
for receipt, base in [(producer, producer_base), (execution, review_base + 'candidate-4/')]:
    for relative, digest in receipt['inputManifest'].items():
        bind(relative, digest)
        bind(base + 'inputs/' + relative, digest)
    for command in receipt['commands']:
        expected = command.get('expectedExitCode', 1 if command.get('expectedFailure') else 0)
        assert command['exitCode'] == expected, command['name']
        bind(command['log'], command['sha256'])
    for relative, artifact in receipt['outputs'].items():
        assert (ROOT / relative).stat().st_size == artifact['bytes']
        bind(relative, artifact['sha256'])
for relative, digest in count['bindings'].items():
    bind(relative, digest)
for relative in [producer_base + 'receipt.json', producer_base + 'count-audit.json', review_base + 'review.json']:
    bind(relative)
bind(str(Path(__file__).relative_to(ROOT)))
result = dict(schema=1, status='accepted-pure-v2-resolution', reviewer='root',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    sourceTreeSHA256=producer['sourceTreeSHA256'],
    sdkTestsPerBuild=127, newSDKTestsPerBuild=21, independentCasesPerBuild=133,
    independentNodeRecordsPerBuild=7858, independentPaintStatesPerBuild=31432,
    detectedSemanticMutations=review['mutationMismatchCases'],
    validation='Bound all live/frozen inputs, producer and independent final command logs and compiled outputs; reviewed standard validation, derived frontier, inherited state, list/section placement and exact identity handling. Producer iOS/official Android compiles are retained compilation evidence.',
    historicalFailures='Producer original first-target count107 superseded by bound audit127. Independent attempts1-3 are corrected harness failures; retained unchanged.',
    limits=['Pure immutable data only: no actual native resources, font coverage, measurement, rendering or appearance acceptance.',
            'No native capture/support authority, atomic native transaction or stale-environment enforcement.',
            'No signed V2, physical design parity, published FieldLog or GA qualification.'],
    bindings=dict(sorted(bindings.items())))
(HERE / 'acceptance.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status=result['status'], bindings=len(bindings))))
