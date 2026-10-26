"""Execute only the root-admitted seven seeded guard witnesses, serially."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREP = HERE.parent / 'execution-preparation'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('sealed_review_harness', PREP / 'harness.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
ADMISSION = ROOT / 'verification/swift-semantic-adapter-root-review/private-guard-review-admission.json'
ADMISSION_SHA = 'd52cb249fff84ed893e0f919cefff9095288a725ada60fa06db64743e893a586'
OUT = HERE / 'private-guard-run-1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(path, digest, size=None):
    raw = path.read_bytes()
    require(h.sha(raw) == digest, 'source/hash mismatch: ' + str(path))
    if size is not None:
        require(len(raw) == size, 'source/size mismatch: ' + str(path))
    return raw


def succeeded(receipt):
    return (receipt['exit_code'] == 0 and not receipt['timed_out']
            and not receipt['output_truncated'] and receipt['spawn_failure'] is None)


def main():
    require(not OUT.exists(), 'refuse to overwrite prior run')
    OUT.mkdir()
    source = OUT / 'source'
    source.mkdir()
    commands = OUT / 'commands'
    commands.mkdir()
    binaries = []
    cleanup = []
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'script_sha256': h.sha(Path(__file__).read_bytes()),
              'python': sys.version, 'command': sys.argv,
              'scope': 'seven deliberately seeded private shape/projection witnesses in two modes',
              'public_reachability_established': False, 'product_source_changed': False,
              'candidate_harness_or_models_executed': False, 'native_runtime_or_capture_started': False,
              'modes': [], 'preflight_failure': None}
    try:
        admission_raw = checked(ADMISSION, ADMISSION_SHA)
        (OUT / 'root-admission.json').write_bytes(admission_raw)
        a = json.loads(admission_raw)
        require(a['status'] == 'admitted-seven-private-seeded-finalizer-guard-witnesses', 'admission status')
        require(ROOT / a['output_directory'] == OUT, 'output scope')
        proposal = ROOT / a['proposal_seal']
        seal = json.loads(checked(proposal, a['proposal_seal_sha256']))
        require(seal['member_count'] == len(seal['members']) == a['verified_members'] == 5, 'proposal count')
        require(sum(m['bytes'] for m in seal['members']) == seal['member_bytes'] == a['verified_bytes'], 'proposal size')
        for m in seal['members']:
            checked(ROOT / m['path'], m['sha256'], m['bytes'])
        proposal_dir = proposal.parent
        delta = json.loads((proposal_dir / 'delta.json').read_bytes())
        expected = json.loads((proposal_dir / 'expected-cases.json').read_bytes())['cases']
        require([c['id'] for c in expected] == a['cases'], 'seven admitted identities')
        require(len(set(a['cases'])) == 7, 'duplicate case')
        for c in expected:
            require(len(c['expected_words']) == 32 and all(type(v) == int and 0 <= v < 2**64 for v in c['expected_words']), 'full32')
        baseline = HERE / 'candidate-snapshot/verification/swift-cache-state-implementation/source/library'
        product = ROOT / 'verification/swift-cache-state-implementation/source/library'
        source_receipt = []
        for name, suffix in delta['append_only_utf8'].items():
            require(name in ('analyzer.rs', 'envelope.rs', 'cache_state.rs'), 'closed source map')
            raw = checked(baseline / name, delta['baseline_sha256'][name])
            checked(product / name, delta['baseline_sha256'][name])
            transformed = raw + suffix.encode('utf-8')
            bound = a['transformed_source_hashes'][name]
            require(len(transformed) == bound['bytes'] and h.sha(transformed) == bound['sha256'], 'exact admitted append delta')
            (source / name).write_bytes(transformed)
            source_receipt.append({'name': name, 'baseline_sha256': h.sha(raw), 'transformed_sha256': h.sha(transformed), 'bytes': len(transformed)})
        glue = checked(proposal_dir / delta['additional_file'], a['glue_source_sha256'])
        (source / delta['additional_file']).write_bytes(glue)
        shutil.copyfile(proposal_dir / 'expected-cases.json', OUT / 'expected-cases.json')
        h.write_json(OUT / 'source-receipt.json', {'members': source_receipt, 'glue_sha256': h.sha(glue), 'delta_sha256': h.sha((proposal_dir / 'delta.json').read_bytes()), 'admission_sha256': ADMISSION_SHA, 'no_cfg_test': True})
        compiler = Path(a['rustc'])
        checked(compiler, a['rustc_sha256'])
        version = h.bounded([str(compiler), '-vV'], source, commands, 'rustc-version')
        require(succeeded(version), 'compiler version failed')
        require(Path(version['stdout']).read_text() == a['rustc_version'], 'bound compiler version mismatch')
        h.write_json(OUT / 'tool-receipt.json', {'rustc': str(compiler), 'sha256': a['rustc_sha256'], 'version_command': version, 'python': sys.version, 'sealed_harness_sha256': h.sha((PREP / 'harness.py').read_bytes())})
        for mode in a['compiler_modes']:
            require(mode in ('default', 'optimized'), 'closed mode map')
            binary = OUT / ('private-guard-' + mode)
            binaries.append(binary)
            argv = [str(compiler), '--edition=2021', '--crate-name', 'independent_guard_review', str(source / 'analyzer.rs'), '-o', str(binary)]
            if mode == 'optimized':
                argv.append('-O')
            compile_receipt = h.bounded(argv, source, commands, mode + '-compile')
            mr = {'mode': mode, 'compile_succeeded': succeeded(compile_receipt), 'binary_sha256': None, 'cases': [], 'protocol_failure': None}
            result['modes'].append(mr)
            if not mr['compile_succeeded']:
                continue
            mr['binary_sha256'] = h.sha(binary.read_bytes())
            run_receipt = h.bounded([str(binary)], source, commands, mode + '-run')
            mr['run_succeeded'] = succeeded(run_receipt)
            try:
                require(mr['run_succeeded'], 'binary execution failed')
                observed = [json.loads(line) for line in Path(run_receipt['stdout']).read_text().splitlines()]
                require([v['id'] for v in observed] == a['cases'], 'closed emitted case identities/order')
                for e, o in zip(expected, observed):
                    require(set(o) == {'id', 'shape_guard', 'words'} and type(o['shape_guard']) == bool, 'closed emitted protocol')
                    require(len(o['words']) == 32 and all(type(v) == int and 0 <= v < 2**64 for v in o['words']), 'emitted full32')
                    differences = [{'word': i, 'expected': want, 'observed': got} for i, (want, got) in enumerate(zip(e['expected_words'], o['words'])) if want != got]
                    mr['cases'].append({'id': e['id'], 'expected_shape': e['expected_shape'], 'observed_shape': o['shape_guard'], 'shape_matches': e['expected_shape'] == o['shape_guard'], 'full32_matches': not differences, 'differences': differences, 'expected_words': e['expected_words'], 'observed_words': o['words']})
            except Exception as exc:
                mr['protocol_failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        for name, digest in delta['baseline_sha256'].items():
            checked(product / name, digest)
        result['product_baseline_hashes_unchanged_after'] = delta['baseline_sha256']
    except Exception as exc:
        result['preflight_failure'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        for binary in binaries:
            if binary.exists():
                raw = binary.read_bytes()
                item = {'path': str(binary), 'bytes': len(raw), 'sha256': h.sha(raw), 'all_owned_commands_returned': True}
                binary.unlink()
                item['removed'] = not binary.exists()
                cleanup.append(item)
        h.write_json(OUT / 'cleanup.json', {'owned_binary_products': cleanup, 'preserved': 'overlay source, exact expectations, commands and raw stdout/stderr, comparisons', 'unrelated_paths_removed': False})
        result['case_observations'] = sum(len(m['cases']) for m in result['modes'])
        result['passing_case_observations'] = sum(c['shape_matches'] and c['full32_matches'] for m in result['modes'] for c in m['cases'])
        result['failing_case_observations'] = result['case_observations'] - result['passing_case_observations']
        result['implementation_accepted'] = False
        h.write_json(OUT / 'summary.json', result)
    print(json.dumps({'preflight_failure': result['preflight_failure'], 'observations': result['case_observations'], 'passing': result['passing_case_observations'], 'failing': result['failing_case_observations'], 'summary': str(OUT / 'summary.json')}))
    return 0 if result['preflight_failure'] is None and result['case_observations'] == 14 and result['failing_case_observations'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
