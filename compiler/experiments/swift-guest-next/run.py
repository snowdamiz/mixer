#!/usr/bin/env python3
"""Bounded retained-corpus/import/linker diagnostics; never executes the owned VM."""
import argparse
import csv
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SDK = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle/swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1')
SWIFTC = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
PRIOR = ROOT / 'compiler/experiments/profile-budget/evidence/2026-10-22-qualified'
CANDIDATE = ROOT / 'compiler/experiments/profile-budget/local/functions-2026-10-22-qualified/candidate.wasm'
EXPECTED = dict(codableRoundTrip=True, committedEntries=1, completionBasisPoints=5000,
    emptyTitleRejected=True, pendingChanges=1503, reordered=True, repeatedCommitRejected=True,
    reportIncludesEntry=True, status='passed', taskCount=1000, unicodePreserved=True)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def identity(path):
    path = Path(path)
    return dict(path=str(path), resolved=str(path.resolve()), bytes=path.stat().st_size, sha256=digest(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='2026-10-23-observed')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name, re.ASCII):
        parser.error('name must be a bounded ASCII path component')
    evidence = HERE / 'evidence' / args.name
    local = HERE / 'local' / args.name
    evidence.mkdir(parents=True, exist_ok=False)
    local.mkdir(parents=True, exist_ok=False)
    node = shutil.which('node')
    if not node:
        raise ValueError('Node platform tool missing')
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('SWIFT_', 'LLVM_', 'DYLD_')) or key in ('NODE_OPTIONS', 'NODE_PATH', 'LD_PRELOAD'):
            env.pop(key)
    env['DEVELOPER_DIR'] = '/Applications/Xcode_26.6.app/Contents/Developer'
    commands = []
    receipt = dict(schemaVersion=1, observedAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='running', authorization=False, ownedVMExecution=False, deviceRun=False,
        selectedAgent=dict(model='gpt-6.1-sol', reasoningEffort='xhigh'), independentReview=False,
        commands=commands, tools={name: identity(path) for name, path in
            [('node', Path(node)), ('swiftc', SWIFTC), ('wasm-ld', SWIFTC.parent / 'wasm-ld'), ('python', Path(sys.executable))]})
    source_names = ['run.py', 'trace.mjs', 'trace_support.mjs', 'test_trace.mjs', 'ReactorProbe.swift', 'reactor_oracle.mjs']
    receipt['sourceManifest'] = {name: digest(HERE / name) for name in source_names}
    receipt['sourceManifestDigest'] = hashlib.sha256(json.dumps(receipt['sourceManifest'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def run(name, command, expected=0):
        command = [str(x) for x in command]
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=90)
        if len(result.stdout) + len(result.stderr) > 1024 * 1024:
            raise ValueError('diagnostic output exceeded one MiB')
        stdout, stderr = evidence / (name + '.stdout'), evidence / (name + '.stderr')
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        commands.append(dict(name=name, command=command, cwd=str(ROOT), exitCode=result.returncode,
            stdout=identity(stdout), stderr=identity(stderr)))
        if result.returncode != expected:
            raise ValueError(f'{name}: unexpected exit {result.returncode}')
        return result.stdout.decode()

    try:
        receipt['revision'] = run('revision', ['git', 'rev-parse', 'HEAD']).strip()
        receipt['versions'] = dict(node=run('version-node', [node, '--version']).strip(),
            swift=run('version-swiftc', [SWIFTC, '--version']).strip(),
            linker=run('version-linker', [SWIFTC.parent / 'wasm-ld', '--version']).strip(),
            python=sys.version)
        receipt['host'] = run('host', ['/usr/bin/sw_vers']).strip()
        run('trace-tests', [node, '--test', HERE / 'test_trace.mjs'])
        receipt['candidate'] = identity(CANDIDATE)
        if receipt['candidate']['bytes'] != 52008982 or receipt['candidate']['sha256'] != '19ac88f26f0daf34b64acb3c5b895fc79b52701368fc4c532ac8ede5844fee75':
            raise ValueError('frozen candidate identity mismatch')
        actual = json.loads(run('retained-corpus-trace', [node, '--no-warnings', HERE / 'trace.mjs', CANDIDATE]))
        if actual != EXPECTED:
            raise ValueError('full original observation object differs')
        lines = (evidence / 'retained-corpus-trace.stderr').read_text().splitlines()
        trace = [json.loads(line.removeprefix('SWIFT_GUEST_TRACE ')) for line in lines if line.startswith('SWIFT_GUEST_TRACE ')]
        if len(trace) != 1 or trace[0]['exitCode'] != 0:
            raise ValueError('missing or failed trace')
        (evidence / 'trace.json').write_text(json.dumps(trace[0], indent=2) + '\n')
        receipt['observations'] = actual
        receipt['trace'] = identity(evidence / 'trace.json')
        source = CANDIDATE.read_bytes()
        # Prior owned binary reader supplies the file/VMA relation; exact payload hash is checked again.
        structure = json.loads((PRIOR / 'osize-compress-structure.json').read_text())
        icu = trace[0]['memory']['icuExtent']
        segments = [item for item in structure['data'] if item['offset'] <= icu['start'] and
            item['offset'] + item['bytes'] >= icu['start'] + icu['bytes']]
        if len(segments) != 1:
            raise ValueError('ambiguous ICU segment mapping')
        segment = segments[0]
        offset = segment['file_offset'] + icu['start'] - segment['offset']
        payload = source[offset:offset + icu['bytes']]
        if hashlib.sha256(payload).hexdigest() != icu['sha256']:
            raise ValueError('ICU file span identity mismatch')
        remainder = source[:offset] + source[offset + icu['bytes']:]
        receipt['transferPartition'] = dict(scope='diagnostic byte partition, not a valid Wasm module or release artifact; no data removed from any executable',
            fullRawBytes=len(source), fullGzip9Bytes=len(gzip.compress(source, compresslevel=9, mtime=0)),
            icuRawBytes=len(payload), icuGzip9Bytes=len(gzip.compress(payload, compresslevel=9, mtime=0)),
            remainderRawBytes=len(remainder), remainderGzip9Bytes=len(gzip.compress(remainder, compresslevel=9, mtime=0)),
            icuFileOffset=offset, priorStructure=identity(PRIOR / 'osize-compress-structure.json'))
        why_path = ROOT / 'compiler/experiments/profile-budget/local/2026-10-22-qualified/osize-compress.why-extract.tsv'
        with why_path.open() as stream:
            rows = list(csv.DictReader(stream, delimiter='\t'))
        receipt['foundationRootReferences'] = [row for row in rows if 'FieldLogModels.build/Workspace.swift.o' in row['reference'] and 'libFoundation.a(' in row['extracted']]
        receipt['whyExtract'] = identity(why_path)
        # Attribute sampled dynamic stacks only after rechecking the earlier all-body
        # map relation (function order, wire size and five-byte output offset bias).
        map_path = why_path.with_name('osize-compress.map')
        csv_path = ROOT / 'compiler/experiments/profile-budget/functions/evidence/2026-10-22-qualified/functions.csv.gz'
        mapped = []
        in_code = False
        for line in map_path.open():
            match = re.fullmatch(r'\s*(?:-|[0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)( +)(.*)\n?', line)
            if not match:
                continue
            offset_hex, size_hex, spaces, name = match.groups()
            if len(spaces) == 1:
                in_code = name == 'CODE'
            elif in_code and len(spaces) == 9:
                mapped.append((int(offset_hex, 16), int(size_hex, 16), name))
        with gzip.open(csv_path, 'rt') as stream:
            body_rows = list(csv.DictReader(stream))
        if len(body_rows) != len(mapped) or len(mapped) != 79837:
            raise ValueError('unqualified function mapping count')
        names = {}
        for body, (offset, size, name) in zip(body_rows, mapped):
            wire = int(body['wire_bytes'])
            prefix = max(1, (wire.bit_length() + 6) // 7)
            if size != wire + prefix or int(body['body_offset']) - prefix - offset != 5:
                raise ValueError('unqualified function mapping position')
            names[int(body['function'])] = name
        samples = []
        for sample in trace[0]['imports']['random_get'].get('sampleStacks', []):
            frames = [int(value) for value in re.findall(r'wasm-function\[(\d+)\]', sample['stack'])]
            samples.append(dict(call=sample['call'], requestedBytes=sample['requestedBytes'],
                frames=[dict(function=index, input=names.get(index, 'imported function')) for index in frames]))
        receipt['randomCallsiteSamples'] = dict(scope='ten bounded samples, not complete dynamic coverage; numeric Node stack frames mapped only after all-body link-map/wire verification',
            linkMap=identity(map_path), bodyCSV=identity(csv_path), samples=samples)
        resource = SDK / 'swift.xctoolchain/usr/lib/swift_static'
        artifact = local / 'reactor.wasm'
        command = [SWIFTC, '-v', '-target', 'wasm32-unknown-wasip1', '-sdk', SDK / 'WASI.sdk',
            '-resource-dir', resource, '-Xclang-linker', '-resource-dir', '-Xclang-linker', resource / 'clang',
            '-static-stdlib', '-parse-as-library', '-Osize', '-gnone',
            '-Xclang-linker', '-mexec-model=reactor', '-Xlinker', '--export=mixer_linker_probe_add',
            '-Xlinker', '--strip-all', HERE / 'ReactorProbe.swift', '-o', artifact]
        run('reactor-build', command)
        reactor = json.loads(run('reactor-oracle', [node, '--no-warnings', HERE / 'reactor_oracle.mjs', artifact]))
        receipt['reactorProbe'] = dict(scope='original scalar linker probe only; not FieldLog, language, full Swift runtime execution or owned VM qualification',
            artifact=identity(artifact), gzip9Bytes=len(gzip.compress(artifact.read_bytes(), compresslevel=9, mtime=0)), oracle=reactor)
        vm_tool = ROOT / 'vm/target/release/mixer-vm'
        receipt['tools']['ownedInventoryTool'] = identity(vm_tool)
        inventory = json.loads(run('reactor-owned-inventory', [vm_tool, '--profile', 'mixer-table-memory-v3', 'inventory', artifact], expected=2))
        if inventory['valid'] or not inventory['inventory_complete']:
            raise ValueError('unexpected reactor inventory/admission')
        receipt['reactorProbe']['ownedInventory'] = inventory
        receipt['reactorProbe']['maximumNesting'] = None
        receipt['reactorProbe']['maximumNestingScope'] = 'current bounded inventory tool does not expose raw nesting; no inference from opcode counts'
        sdk_lib = SDK / 'swift.xctoolchain/usr/lib'
        receipt['sdkSharedModuleCandidates'] = [str(p.relative_to(sdk_lib)) for p in sdk_lib.rglob('*') if p.is_file() and p.suffix in ('.so', '.dylib', '.wasm')]
        receipt['officialSDKInputs'] = [identity(path) for path in [SDK / 'swift-sdk.json', SDK / 'toolset.json',
            SDK / 'WASI.sdk/include/wasm32-wasip1/wasi/api.h', SDK / 'WASI.sdk/lib/wasm32-wasip1/crt1-reactor.o',
            resource / 'wasi/static-executable-args.lnk']]
        if receipt['sourceManifest'] != {name: digest(HERE / name) for name in source_names}:
            raise ValueError('diagnostic sources changed during run')
        receipt['status'] = 'passed-diagnostic-only'
        receipt['limitations'] = ['Node development oracle only; no owned full Swift execution or admission',
            'one unchanged model corpus; no feature/UI/effect graph, async runtime, device, store, immutable consumer release or GA claim',
            'before/after writes only; restored/interim writes, peak memory and physical RSS unobserved',
            'uninvoked imports remain required by linked module and must have explicit bounded policies',
            'partition remainder is invalid Wasm; it tests transfer arithmetic only and removes nothing from runnable artifacts',
            'reactor probe is deliberately scalar and establishes linker model only, not application feasibility or budget']
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(status=receipt['status'], evidence=str(evidence))))


if __name__ == '__main__':
    main()
