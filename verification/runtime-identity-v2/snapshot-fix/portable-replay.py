#!/usr/bin/env python3
"""Deterministic scanner/decode boundary gate, isolated test exports only."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();output=args.output.absolute();output.mkdir(parents=True,exist_ok=False)
original=output/'pristine';original.mkdir()
BASE='aca686bfc72b8f18db727de5307977fb51790e0a'
manifest=json.loads((ROOT/'verification/runtime-identity-v2/candidate-inputs-v2.json').read_bytes())
for name,want in manifest['files'].items():
    raw=(ROOT/name).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=want:raise ValueError('fixed source mismatch '+name)
    dest=original/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
for prefix in ['updates/Sources','updates/Tests','updates/Package.swift','updates/Package.resolved','contracts','capabilities/schema','vm/include/mixer_vm.h','vm/include/mixer_vm_capability.h','activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json']:
    paths=subprocess.check_output(['git','--no-replace-objects','ls-tree','-r','--name-only',BASE,prefix],cwd=ROOT).decode().splitlines()
    for name in paths:
        raw=subprocess.check_output(['git','--no-replace-objects','show',BASE+':'+name],cwd=ROOT)
        dest=original/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=HERE/'OldCapabilityRuntimeIdentity.swift.txt'
if sha(old)!='8fe3feae4f1e7d1e114c60c860b9f9a423cfdc0e8f88779d1f519edb286738c6':raise ValueError('old parser pin mismatch')
receipt={'schema':1,'scope':'TEST-ONLY deterministic derived StrictJSON scanner/decode hook; no production hook/source edit; no concurrent pointer read/write. Copy is not an atomic external-buffer snapshot guarantee.','old_parser_sha256':sha(old),'fixed_parser_sha256':sha(ROOT/'runtime-identity/Sources/MixerRuntimeIdentity/CapabilityRuntimeIdentity.swift'),'commands':[]}
hook='''        // INDEPENDENT TEST EXPORT ONLY: mutate external caller storage after scan.
        if let address = ProcessInfo.processInfo.environment["MIXER_IDENTITY_REVIEW_ADDRESS"],
           let value = UInt(address), let pointer = UnsafeMutableRawPointer(bitPattern: value),
           let path = ProcessInfo.processInfo.environment["MIXER_IDENTITY_REVIEW_REPLACEMENT"] {
            let replacement = try Data(contentsOf: URL(fileURLWithPath: path))
            replacement.withUnsafeBytes { bytes in
                if let base = bytes.baseAddress { pointer.copyMemory(from: base, byteCount: bytes.count) }
            }
        }
'''
for variant in ['old','fixed']:
    export=output/variant;shutil.copytree(original,export,ignore=shutil.ignore_patterns('.build','.swiftpm','__pycache__'))
    parser=export/'runtime-identity/Sources/MixerRuntimeIdentity/CapabilityRuntimeIdentity.swift'
    shutil.copyfile(old if variant=='old' else ROOT/'runtime-identity/Sources/MixerRuntimeIdentity/CapabilityRuntimeIdentity.swift',parser)
    scanner=export/'updates/Sources/MixerUpdates/StrictJSON.swift';text=scanner.read_text();needle='        return try JSONDecoder().decode(type, from: data)'
    if text.count(needle)!=1:raise ValueError('boundary instrumentation mismatch')
    scanner.write_text(text.replace(needle,hook+needle))
    test=export/'runtime-identity/Tests/MixerRuntimeIdentityTests/ReviewSnapshotBoundary.swift'
    shutil.copyfile(HERE/'ReviewSnapshotBoundary.swift',test)
    env=dict(os.environ);env['MIXER_IDENTITY_REVIEW_EXPECTED_FUEL']='777777' if variant=='old' else '1000000'
    cmd=['/usr/bin/swift','test','--package-path',str(export/'runtime-identity'),'--filter','ReviewSnapshotBoundary']
    run=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
    (output/(variant+'.log')).write_bytes(run.stdout)
    receipt['commands'].append({'argv':cmd,'exit_code':run.returncode,'expected_fuel':env['MIXER_IDENTITY_REVIEW_EXPECTED_FUEL'],'instrumented_scanner_sha256':sha(scanner),'test_sha256':sha(test),'log_sha256':hashlib.sha256(run.stdout).hexdigest()})
    if run.returncode:raise ValueError(variant+' boundary probe failed')
receipt['result']='Old parser accepted unscanned duplicate-key replacement fuel777777; fixed parser retained scanned owned snapshot fuel1000000. Both reject replacement when scanned normally.'
receipt['script_sha256']=sha(Path(__file__));(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['result'])
