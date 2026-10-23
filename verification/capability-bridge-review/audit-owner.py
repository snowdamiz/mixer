#!/usr/bin/env python3
"""Read-only binding audit of the exact candidate5 implementation receipts."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = ROOT / 'experimental-capability-runtime/verification/2026-10-23-candidate-5'
OUT = HERE / 'candidate-5'
EXPECTED_RECEIPT = '6194e77ab6119f2d91d18f0a374a04fc99bd018019ae9c1e1a81e6e3e02fd07e'
EXPECTED_MANIFEST = '070f626acd4cfc99ec2bdeb9b1e1dc45da228548d3f6458fb8fbe1b7bbca4b4d'
EXPECTED_BUILDER = '2744db5cb31d67286b4cf81bbfe9b8be6df8db95f7feb9d6e246801eb20f8b91'
NATIVE = 'b25e3b7de2391a80d12e7fd75e60903495bec120'


def sha(data): return hashlib.sha256(data).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)

def main():
    target = OUT / 'owner-audit.json'
    require(not target.exists(), 'preserve earlier owner audit')
    bindings = []
    def bind(path, expected=None, category='input'):
        path = Path(path)
        data = path.read_bytes(); actual = sha(data)
        require(expected is None or actual == expected, str(path) + ': digest mismatch')
        bindings.append({'category': category, 'path': str(path), 'sha256': actual, 'bytes': len(data)})
        return data
    raw = bind(OWNER / 'receipt.json', EXPECTED_RECEIPT, 'owner-receipt')
    receipt = json.loads(raw)
    require(receipt['status'] == 'scoped_checks_passed', 'owner status')
    require(receipt['nativeRevision'] == NATIVE, 'native revision')
    require(receipt['sourceManifestSHA256'] == EXPECTED_MANIFEST, 'source manifest receipt pin')
    require(all(receipt[k] is True for k in ['sourceUnchangedDuringRun','exportUnchangedDuringRun','nativeArtifactsUnchangedDuringRun']), 'owner immutable flags')
    manifest = bind(OWNER / 'source-manifest.sha256', EXPECTED_MANIFEST, 'source-manifest')
    entries = {line.split('  ',1)[1]:line.split('  ',1)[0] for line in manifest.decode().splitlines()}
    require(entries == receipt['source'] and len(entries) == 55, '55 source entries match receipt')
    for relative, digest in entries.items():
        bind(ROOT / relative, digest, 'current-source')
        bind(Path(receipt['frozenSourceExport']) / relative, digest, 'frozen-source')
    stage = Path(receipt['stageRoot'])
    require(len(receipt['nativeArtifacts']) == 4, 'four staged targets')
    for name, artifacts in receipt['nativeArtifacts'].items():
        for relative, digest in artifacts.items(): bind(stage / relative, digest, 'native-artifact')
        staged = json.loads((stage / name / 'receipt.json').read_text())
        require(staged['source_revision'] == NATIVE and staged['source_file_count'] == 81, 'native source revision/count')
        require(staged['source_manifest_sha256'] == '47ecc06679f61be0da8a53839830be72876889bb90c9a8e5834c8661f9312aa6', 'native source manifest')
        for header in ['mixer_vm.h','mixer_vm_capability.h']:
            baseline = subprocess.check_output(['git','show', NATIVE + ':vm/include/' + header], cwd=ROOT)
            require((stage / name / 'include' / header).read_bytes() == baseline, 'exact committed header')
    builder = ROOT / 'experimental-capability-runtime/build-verification/2026-10-23-final-v3/receipt.json'
    bind(builder, EXPECTED_BUILDER, 'reused-builder-receipt')
    require(json.loads(builder.read_text())['source_revision'] == NATIVE, 'builder revision')
    commands = receipt['commands']
    require(len(commands) == 18 and len({c['name'] for c in commands}) == 18, '18 distinct commands')
    expected_counts = {'bridge-debug':16,'bridge-release':16,'bridge-tsan':16,'measurement-filtered':1}
    for command in commands:
        require(command['exitCode'] == 0, 'nonzero owner command')
        data = bind(OWNER / command['log'], command['logSHA256'], 'owner-log')
        if command['name'] in expected_counts:
            actual = [int(v) for v in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',data)]
            require(actual == [expected_counts[command['name']]] == command['passedTests'], 'raw test count')
            require(command['testCountsMatch'] is True, 'test counts match flag')
    tls = []
    for mode in ['debug','release','tsan']:
        folder = OWNER / (mode + '-loopback')
        details = json.loads(bind(folder / 'receipt.json', category='tls-receipt'))
        bind(folder / 'command.log', details['output_sha256'], 'tls-full-test-log')
        bind(folder / 'certificate-generation.log', category='tls-certificate-generation-log')
        observations = details['observations']
        require(details['exit_code'] == 0 and details['server_stopped'], 'TLS fixture stopped/success command')
        require(observations['tcp_accepts'] >= 1 and observations['tls_failures'] >= 1 and observations['application_requests'] == 0, 'normal-trust TLS rejection')
        tls.append({'mode':mode,'observations':observations,'scope':'Negative real normal-trust TLS only; not HTTPS success'})
    require(len(receipt['linkedConsumers']) == 4, 'four linked consumers')
    for name, binary in receipt['linkedConsumers'].items():
        data = bind(binary['path'], binary['sha256'], 'linked-consumer')
        require(len(data) == binary['bytes'], 'binary length')
        text = (OWNER / (name + '-binary-file.log')).read_text()
        require(('ELF 64-bit' in text and 'ARM aarch64' in text) if name == 'android' else ('Mach-O 64-bit' in text and 'arm64' in text), 'architecture ' + name)
    # Audit the actual verbose consumer link commands, not only Package.swift's declaration.
    public = json.loads((OUT / 'public-receipt.json').read_text())
    link_lines = []
    for command in public['commands']:
        if command['name'] not in ['public-debug','public-release']: continue
        data = bind(ROOT / command['log'], command['sha256'], 'independent-public-link-log')
        lines = [line for line in data.decode(errors='replace').splitlines() if 'swiftc ' in line and ' -o ' in line and '-lmixer_vm_capability_experimental' in line]
        require(lines, 'actual experimental Swift final link line')
        for line in lines:
            require(line.split().count('-lmixer_vm_capability_experimental') == 1, 'one native archive link')
            require('-lmixer_vm' not in line.split() and 'MixerRuntime' not in line, 'no legacy/default runtime co-link')
        link_lines += [{'mode':command['name'],'line':line} for line in lines]
    bind(OWNER / 'receipt.json', EXPECTED_RECEIPT, 'owner-receipt-after-audit')
    report = {'status':'exact owner source/log/artifact binding checks passed',
              'owner_receipt_sha256':EXPECTED_RECEIPT,'source_manifest_sha256':EXPECTED_MANIFEST,
              'native_revision':NATIVE,'source_files':55,'owner_commands':18,
              'reused_builder_receipt_sha256':EXPECTED_BUILDER,'bindings':bindings,
              'actual_independent_swift_link_lines':link_lines,'normal_trust_tls_negative':tls,
              'scope':'Read-only audit; reuses owner host/platform build receipts. No Rust/cross/device rerun.',
              'limitations':receipt['limitations'],'script_sha256':sha(Path(__file__).read_bytes())}
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'bindings':len(bindings),'receipt':str(target),'sha256':sha(target.read_bytes())}))

if __name__ == '__main__': main()
