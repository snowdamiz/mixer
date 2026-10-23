#!/usr/bin/env python3
"""Independent frozen-source appearance review. No device/native-publication work."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from build_corpus import build

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/ui-appearance-foundation/candidate-1'
ARCHIVE = PRODUCER / 'inputs'
EXPECTED_TREE = '2a72523ed49f8695ac321c1f0f256640f66cb445504fc893d53066d0c82f6185'
NAMES = ['AppearanceValuesV1.swift', 'AppearanceDescriptorV1.swift', 'AppearanceMetricMathV1.swift', 'AppearanceDefaultV1.swift']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'candidate-1'
    assert label not in ['.', '..'] and '/' not in label
    out = HERE / label
    out.mkdir(exist_ok=False)
    lock = json.loads((PRODUCER / 'input-lock.json').read_text())
    assert len(lock['files']) == 59
    digest = sha(json.dumps(lock['files'], sort_keys=True, separators=(',', ':')).encode())
    assert digest == lock['tree_sha256'] == EXPECTED_TREE
    for relative, expected in lock['files'].items():
        assert sha((ARCHIVE / relative).read_bytes()) == expected, relative
    # Verify actual live product bytes equal the reviewed frozen candidate.
    product_paths = ['sdk/Sources/MixerUI/' + name for name in NAMES] + ['sdk/Tests/MixerUITests/AppearanceV1Tests.swift']
    for relative in product_paths:
        assert sha((ROOT / relative).read_bytes()) == lock['files'][relative], relative
    sources = []
    for name in NAMES:
        data = (ARCHIVE / 'sdk/Sources/MixerUI' / name).read_bytes()
        path = out / 'derived/sdk/Sources/MixerUI' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        sources.append(path)
    derived_main = out / 'derived/main.swift'
    derived_main.write_bytes((HERE / 'main.swift').read_bytes())
    corpus = build(ARCHIVE, out)
    receipt = dict(status='running', observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        producer_source_tree_sha256=digest, producer_source_files_verified=59,
        live_product_files_verified=5, product_sha256={p:lock['files'][p] for p in product_paths},
        reviewed_input_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [
            PRODUCER / 'receipt.json', PRODUCER / 'input-lock.json',
            ROOT / 'verification/ui-shared-appearance-root-review/acceptance.json',
            ROOT / 'docs/ui-shared-appearance-contract.md',
            ROOT / 'verification/ui-shared-appearance-contract/v2/foundation-seam.md',
            ROOT / 'verification/ui-shared-appearance-contract/v2/descriptor-schema.json',
            ROOT / 'verification/ui-shared-appearance-contract/v2/AppearanceV1Declarations.swift']},
        independent_corpus=corpus, commands=[], results={},
        scope='Independent public Swift data-codec, whole-graph validation, canonical default and checked math review against frozen candidate. Host Debug (-Onone) and Release (-O) executable probes only. No renderer, native font/resource, bundle/APK, signed installation, device/parity, FieldLog, release or GA acceptance.',
        limits=['The schema is a specification input; schema mutation expectations use an independently written interpreter plus prose semantic checks, never the sealed design Python oracle or producer test helpers.',
                'All fontSFNT entries, including unreferenced entries, require scale1/und/neutral. This review records the preserved design Python oracle gap as an addendum; it does not alter historical evidence.',
                'Programmatic bound-before-allocation conclusions combine hostile raw-value execution with source inspection; caller-owned hostile strings/arrays necessarily already exist before codec entry.',
                'spacing64 intentionally follows the exact frozen floor(value*64+0.5) Double formula; a below-first-tie nextDown value yields1 after floating-point addition. This is explicitly recorded and tested.'])

    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, args):
        argv = [str(x) for x in args]
        start = time.monotonic()
        result = subprocess.run(argv, cwd=out, env=dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer'),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        log = out / (name + '.log')
        log.write_bytes(result.stdout)
        receipt['commands'].append(dict(name=name, argv=argv, cwd=str(out), exit_code=result.returncode,
            elapsed_seconds=time.monotonic()-start, environment_overrides={'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},
            log=str(log.relative_to(ROOT)), log_sha256=sha(result.stdout)))
        save()
        print(name, result.returncode, flush=True)
        if result.returncode:
            receipt['status'] = 'failed: ' + name
            save()
            raise RuntimeError(receipt['status'])
        return result.stdout

    save()
    run('python-version', ['python3', '--version'])
    run('swift-version', ['swiftc', '--version'])
    run('xcode-version', ['xcodebuild', '-version'])
    for mode, flag in [('debug','-Onone'), ('release','-O')]:
        binary = out / ('probe-' + mode)
        run('compile-' + mode, ['swiftc', '-swift-version', '6', '-warnings-as-errors', flag, '-g', '-module-cache-path',
            out / '.build/module-cache', *sources, derived_main, '-o', binary])
        raw = run('probe-' + mode, [binary, out / corpus['corpus'], out / ('embedded-default-' + mode + '.json')])
        summary = json.loads(raw)
        assert not summary['failures']
        receipt['results'][mode] = summary
        default = (out / ('embedded-default-' + mode + '.json')).read_bytes()
        assert len(default) == 1906 and sha(default) == 'e94f6988744bde16b83001db8e5047aeac4f15f6b045f99a4660445e7e2062d2'
    for path, expected in lock['files'].items():
        assert sha((ARCHIVE / path).read_bytes()) == expected, path
    for path in product_paths:
        assert sha((ROOT / path).read_bytes()) == lock['files'][path], path
    receipt['review_artifacts'] = {str(p.relative_to(ROOT)):dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
        for p in [HERE/'build_corpus.py', HERE/'main.swift', HERE/'verify.py', out/corpus['packed_corpus'], derived_main,
                  out/'embedded-default-debug.json', out/'embedded-default-release.json'] + sources}
    receipt.update(status='passed', completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save()
    print(json.dumps(dict(status=receipt['status'], corpus=corpus, results=receipt['results'])), flush=True)


if __name__ == '__main__':
    main()
