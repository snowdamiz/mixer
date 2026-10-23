"""Bounded read-only evidence collection; no builds, admission, or publication."""
import datetime
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED = '24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
REACTOR = ROOT / 'compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def identity(path):
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    arguments = parser.parse_args()
    assert arguments.name and all(character.isalnum() or character in '-_' for character in arguments.name)
    output = HERE / arguments.name
    output.mkdir(exist_ok=False)
    receipt = {'schemaVersion': 1, 'observedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'authorization': False, 'ownedExecution': False, 'deviceRun': False, 'commands': [], 'sourceManifest': {}, 'tools': {}}
    def run(name, command):
        result = subprocess.run([str(value) for value in command], cwd=ROOT, capture_output=True, timeout=60)
        stdout, stderr = output / (name + '.stdout'), output / (name + '.stderr')
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        receipt['commands'].append({'name': name, 'argv': [str(value) for value in command], 'cwd': str(ROOT), 'exitCode': result.returncode, 'stdout': identity(stdout), 'stderr': identity(stderr)})
        return result
    try:
        node = Path(shutil.which('node')).resolve()
        # Preserve the exact existing tool before another lane rebuilds Cargo's
        # mutable target path. This remains a diagnostic, not a source-built pin.
        original_vm = ROOT / 'vm/target/release/mixer-vm'
        retained = HERE / '.build' / arguments.name
        retained.mkdir(parents=True, exist_ok=False)
        vm = retained / 'mixer-vm'
        before = digest(original_vm)
        shutil.copy2(original_vm, vm)
        assert digest(vm) == before == digest(original_vm)
        receipt['tools'] = {name: identity(path) for name, path in [('python', Path(sys.executable)), ('node', node), ('ownedInventory', vm)]}
        receipt['versions'] = {'python': sys.version, 'node': run('version-node', [node, '--version']).stdout.decode().strip()}
        receipt['ownedToolScope'] = 'Existing local owned executable, hashed; no new build or current-HEAD binary correspondence asserted.'
        receipt['revision'] = run('revision', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
        receipt['tree'] = run('tree', ['git', 'status', '--short']).stdout.decode()
        receipt['reactor'] = identity(REACTOR)
        assert receipt['reactor']['sha256'] == EXPECTED
        for relative in ['AGENTS.md', 'mixer-product-plan.md', 'verification/fieldlog-reactor-root-review.json', 'verification/swift-guest-next-root-review.json', 'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/receipt.json', 'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json', 'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/structure.json', 'compiler/experiments/profile-budget/functions/README.md', 'docs/span-function-cache-design.md', 'verification/span-function-cache-root-review/receipt.json', 'vm/src/lib.rs', 'vm/src/execute.rs', 'vm/src/experimental/mod.rs', 'vm/src/experimental/account.rs', 'vm/src/experimental/reader.rs', 'vm/src/experimental/metadata.rs', 'vm/src/experimental/validate.rs', 'vm/src/experimental/cache/mod.rs', 'vm/src/experimental/cache/decode.rs']:
            receipt['sourceManifest'][relative] = digest(ROOT / relative)
        if (ROOT / 'docs/swift-guest-execution-next.md').exists():
            receipt['sourceManifest']['docs/swift-guest-execution-next.md'] = digest(ROOT / 'docs/swift-guest-execution-next.md')
        official_header = Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle/swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1/WASI.sdk/include/wasm32-wasip1/wasi/api.h')
        receipt['officialWASIHeader'] = identity(official_header)
        for filename in ['collect.py', 'probe.mjs']:
            receipt['sourceManifest'][str((HERE / filename).relative_to(ROOT))] = digest(HERE / filename)
        receipt['sourceManifestDigest'] = hashlib.sha256(json.dumps(receipt['sourceManifest'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        strict = run('owned-strict', [vm, 'validate', REACTOR])
        # Inventory is diagnostic even when it traverses the complete binary.
        inv = run('owned-inventory', [vm, 'inventory', '--profile', 'mixer-table-memory-v3', REACTOR])
        receipt['strict'] = json.loads(strict.stdout)
        receipt['inventory'] = json.loads(inv.stdout)
        assert strict.returncode != 0 and receipt['strict']['error']['message'] == 'module byte limit exceeded'
        assert inv.returncode != 0 and receipt['inventory']['inventory_complete'] is True
        assert receipt['inventory']['inventory_error'] is None and receipt['inventory']['valid'] is False
        result = run('reference-probe', [node, '--no-warnings', HERE / 'probe.mjs', REACTOR, EXPECTED])
        assert result.returncode == 0, result.stderr.decode()
        prefix = 'EXECUTION_NEXT_DIAGNOSTIC '
        records = [line[len(prefix):] for line in result.stderr.decode().splitlines() if line.startswith(prefix)]
        assert len(records) == 1
        receipt['reference'] = json.loads(records[0])
        expected = json.load((ROOT / 'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/receipt.json').open())['expectedObservation']
        observed = [json.loads(line) for line in result.stdout.decode().splitlines() if line.startswith('{')]
        assert observed == [expected, expected]
        receipt['completeObservationEquality'] = True
        structure = json.load((ROOT / 'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/structure.json').open())
        receipt['staticLowerBounds'] = {'sourceBytes': REACTOR.stat().st_size, 'functionsIncludingImports': structure['defined_functions'] + structure['imports'], 'globals': structure['globals'], 'instructions': sum(value['count'] for value in receipt['inventory']['opcodes']), 'initialMemoryPages': structure['memories'][0]['minimum'], 'declaredMemoryMaximumPages': structure['memories'][0]['maximum'], 'sourceCopyPlusSectionSpanWorkCredits': REACTOR.stat().st_size + sum(section['payload_bytes'] for section in structure['sections']), 'workScope': 'Arithmetic lower bound from existing code charging source copy and every section span; excludes subsequent metadata/body/data/type traversal. This is not a run of a widened validator.'}
        receipt['strictExitCode'] = strict.returncode
        receipt['inventoryExitCode'] = inv.returncode
        receipt['status'] = 'read-only-reference-and-rejection-diagnostics-passed'
    except BaseException as error:
        receipt['status'] = 'failed'
        receipt['error'] = repr(error)
        raise
    finally:
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')

if __name__ == '__main__':
    main()
