#!/usr/bin/env python3
"""Audit and seal this scoped metadata SPI evidence without running production."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,why):
    if not ok:raise RuntimeError(why)

def main():
    receipt=HERE/'2026-10-23-candidate-1/receipt.json'
    raw=receipt.read_bytes();r=json.loads(raw)
    require(sha(raw)=='7c96522e85e95c1f485c3d141bed09f864e1a2d4b32e5811604dbd33a967bd53','frozen qualification receipt')
    require(len(r['commands'])==31 and len(r['source_files'])==71,'bounded expected matrix')
    for p,d in r['source_files'].items():
        require(sha((ROOT/p).read_bytes())==d,'live source '+p)
        require(sha((Path(r['immutable_source_export'])/p).read_bytes())==d,'export source '+p)
    for command in r['commands']:
        log=(ROOT/command['log']).read_bytes()
        require(sha(log)==command['sha256'],'command log '+command['name'])
        require(command['exit_code']==command['expected_exit'],'command result '+command['name'])
        if 'expected_tests' in command:
            seen=[int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',log)]
            require(seen==[command['expected_tests']],'test count '+command['name'])
        if 'required_diagnostic_fragment' in command:
            require(command['required_diagnostic_fragment'].encode() in log,'negative diagnostic '+command['name'])
    for target,outputs in r['artifacts'].items():
        for a in outputs:
            p=Path(a['path']);require(p.stat().st_size==a['bytes'] and sha(p.read_bytes())==a['sha256'],'actual '+target+' artifact '+str(p))
    for p,d in r['preserved_old_updates_files'].items():
        old=subprocess.check_output(['git','show',r['baseline_revision']+':'+p],cwd=ROOT)
        require(sha(old)==d and (ROOT/p).read_bytes()==old,'old preservation '+p)
    source=(ROOT/'updates/Sources/MixerUpdates/VerifierV3.swift').read_text()
    restored=re.sub(r'(?m)^[ \t]*// BEGIN additive CapabilityDurableV3 metadata SPI\.\n[\s\S]*?^[ \t]*// END additive CapabilityDurableV3 metadata SPI\.\n\n?', '', source).encode()
    require(sha(restored)==r['baseline_v3_sha256'],'existing v3 source preservation')
    rows={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*'))
        if p.is_file() and p.name not in ['final-receipt.json','evidence-manifest.sha256'] and '__pycache__' not in p.parts}
    manifest=''.join(d+'  '+p+'\n' for p,d in sorted(rows.items())).encode()
    (HERE/'evidence-manifest.sha256').write_bytes(manifest)
    final={'status':'scoped owner qualification audited; independent review pending','qualification_receipt_sha256':sha(raw),
        'production_source_sha256':r['source_files']['updates/Sources/MixerUpdates/VerifierV3.swift'],
        'test_source_sha256':r['source_files']['updates/Tests/MixerUpdatesTests/VerifierV3DurableSPITests.swift'],
        'source_manifest_sha256':r['source_manifest_sha256'],'source_and_export_hashes_verified':len(r['source_files']),
        'old_files_verified':len(r['preserved_old_updates_files']),'existing_v3_bytes_restored_exact':True,
        'command_logs_verified':len(r['commands']),'evidence_files':len(rows),'evidence_manifest_sha256':sha(manifest),
        'artifacts_verified':sum(map(len,r['artifacts'].values())),
        'scope':r['scope'],'limitations':r['limitations']}
    (HERE/'final-receipt.json').write_text(json.dumps(final,indent=2)+'\n')
    print(json.dumps(final,indent=2))
    print('final-receipt-sha256 '+sha((HERE/'final-receipt.json').read_bytes()))

if __name__=='__main__':main()
