#!/usr/bin/env python3
"""Bind root source review to real producer/reviewer/host test observations."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys, tarfile
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sha = lambda value: hashlib.sha256(value).hexdigest()
files = {}
def bind(path, expected=None):
    path = Path(path)
    if not path.is_absolute(): path = ROOT / path
    value = sha(path.read_bytes())
    if expected is not None: assert value == expected, path
    files[str(path.relative_to(ROOT))] = value
    return path
def read(path): return json.loads(bind(path).read_text())
def archive(path, expected):
    with tarfile.open(bind(path)) as stream:
        members = stream.getmembers()
        assert len(members) == len(expected)
        assert {m.name for m in members} == set(expected)
        for member in members:
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert sha(stream.extractfile(member).read()) == expected[member.name], member.name

def main():
    manifest = read('verification/hosted-token-verifier/source-manifest.json')
    for item in manifest['files']: bind(item['path'], item['sha256'])
    aggregate = sha(''.join(f"{i['sha256']}  {i['path']}\n" for i in sorted(manifest['files'], key=lambda i:i['path'])).encode())
    assert aggregate == manifest['aggregate_sha256'] == '7ed3970197eca3840d16655b2b770829a8534d0b42a73af49f0fdebff95b7407'
    producer = read('verification/hosted-token-verifier/receipt.json')
    assert producer['success'] and producer['source_unchanged_during_run']
    assert producer['source_aggregate_sha256'] == aggregate
    for item in producer['inputs']: bind(item['path'], item['sha256'])
    for command in producer['checks']:
        assert command['exit_code'] == 0
        for stream in ['stdout','stderr']: bind(command[stream]['path'], command[stream]['sha256'])
    assert 'Result: 16 passed' in bind('verification/hosted-token-verifier/tests.stdout').read_text()
    cleanup = read('verification/hosted-token-verifier/cleanup.json')
    assert cleanup['path_absent_after_cleanup'] and cleanup['source_unchanged']
    base = Path('verification/hosted-token-verifier-review/run-2')
    reviewer = read(base / 'receipt.json')
    assert reviewer['result'] == 'pass' and reviewer['source_unchanged_after_test'] and reviewer['cleanup']['scratch_removed']
    assert reviewer['producer_aggregate_sha256'] == aggregate
    for name,digest in reviewer['artifacts'].items(): bind(base/name,digest)
    for command in reviewer['commands']:
        assert command['exit_code'] == 0
        bind(base/command['log'],command['sha256'])
    for name,digest in read(base/'input-manifest.json').items(): bind(name,digest)
    product = {i['path']:i['sha256'] for i in manifest['files'] if i['path'].startswith('hosted/lib/')}
    archive(base/'product-source.tar.gz', product)
    assert 'Result: 23 passed' in bind(base/'tests.log').read_text()
    closeout = read('verification/hosted-token-verifier-review/closeout.json')
    assert not closeout['actionable_product_findings']
    host = read(OUT/'host-2/receipt.json')
    assert host['status'] == 'passed' and all(host['cleanup'].values())
    for path,digest in host['inputs'].items(): bind('hosted/'+path,digest)
    for command in host['commands']:
        assert command['exit_code'] == command.get('expected_exit_code',0)
        bind(OUT/'host-2'/command['log'],command['sha256'])
    bind(OUT/'host-2/source.tar.gz',host['source_archive_sha256'])
    archive(OUT/'host-2/source.tar.gz',host['inputs'])
    assert 'Result: 24 passed' in bind(OUT/'host-2/tests.log').read_text()
    selection=read('verification/hosted-verifier-dependency/root-selection.json')
    for path,digest in selection['inputs'].items(): bind(path,digest)
    for path in ['docs/hosted-token-verifier.md','docs/hosted-token-verifier-review.md',str(Path(__file__).relative_to(ROOT))]:bind(path)
    receipt=dict(schema=1,decision='accepted-pure-RS256-token-verifier-development-slice',reviewer='root',
        observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sourceAggregateSHA256=aggregate,hostedSourceTreeSHA256=host['source_tree_sha256'],
        command=[sys.executable,str(Path(__file__).resolve())],pythonVersion=sys.version,
        evidence=dict(producerScopedTests=16,independentAdversarialTests=23,rootFullSuiteTests=24,rootFoundationTests=8,
            rootIdentityTests=16,packagedProductionReleaseBuilt=True,missingConfigurationRejected=True),
        manualSourceReview=[
            'Reviewed all six product modules and producer/independent tests. Byte limits precede JSON decode; ordered decoded pairs reject duplicates at every admitted depth before map conversion.',
            'Fixed alg/typ/kid-only header and atomic whole-JWKS validation select one public RSA key. Standard JOSE verify_strict checks original compact bytes; exact verified payload is matched before claims become identity.',
            'Issuer/client/audience/type/time requirements and class-specific lifetime ceilings are explicit; no signed tenant/role/kind grant survives in VerifiedIdentity. Unknown scopes create no permission.',
            'Snapshot freshness and disable results are explicit pure inputs. There is no runtime authority activation, transport/cache, authenticated endpoint or database-policy bypass claimed.'
        ],
        collectorCorrection='host-1 passed the same product tests with the legacy foundation-only receipt wording. host-2 reran after correcting only collector scope text; host-2 is the complete current hosted source receipt. Counts are not summed.',
        files=dict(sorted(files.items())),remaining=['Configured adapter and active profile/key ownership','Authenticated bounded HTTPS JWKS transport/cache and provider qualification','Principal/credential revocation, authoritative membership/RLS, private artifact HTTP and audit/idempotency integration','Linux hosted CI for this commit','Native/device and all full product/GA gates'],
        warnings=['JOSE OTP29 deprecated-catch warnings remain recorded'],gaGatePassed=False)
    (OUT/'acceptance.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(decision=receipt['decision'],bindings=len(files),rootTests=24,independentTests=23)))
if __name__ == '__main__':main()
