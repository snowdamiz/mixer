#!/usr/bin/env python3
"""Independent immutable original-owner host test collector; never edits live VM."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
encoded = lambda obj: (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
digest = lambda obj: hashlib.sha256(encoded(obj)).hexdigest()


def manifest(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-archive', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--producer-seal', type=Path, required=True)
    parser.add_argument('--reuse-product-result', type=Path)
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = HERE / 'results' / stamp
    build = HERE / 'build' / stamp
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    (out / 'inputs').mkdir()
    for source, name in [
        (args.source_archive, 'candidate-source.tar.gz'),
        (args.source_manifest, 'candidate-manifest.json'),
        (args.producer_seal, 'producer-seal.json'),
        (HERE / 'inputs/producer-baseline-source.tar.gz', 'baseline-source.tar.gz'),
        (HERE / 'inputs/producer-baseline-manifest.json', 'baseline-manifest.json'),
        (HERE / 'collect.py', 'collect.py'),
        (HERE / 'independent-probes.rs', 'independent-probes.rs'),
        (HERE / 'independent-fault-probes.rs', 'independent-fault-probes.rs'),
    ]:
        shutil.copyfile(source, out / 'inputs' / name)
    commands, binaries, comparisons, closures = [], [], [], {}
    environment = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
    environment.pop('RUSTC_BOOTSTRAP', None)
    portable = out / 'qualifying-artifacts.tar.gz'
    status = 'failed'
    reused_product = None

    def run(name, argv, cwd, target=None, closure=None, expected_error=None):
        if closure is not None:
            assert manifest(cwd) == closure, 'source changed before ' + name
        env = dict(environment)
        if target is not None:
            env['CARGO_TARGET_DIR'] = str(target)
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=1200)
        for stream in ['stdout', 'stderr']:
            (out / (name + '.' + stream)).write_bytes(getattr(result, stream))
        commands.append(dict(name=name, argv=argv, cwd=str(cwd), target=str(target) if target else None,
            startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            exitCode=result.returncode, expectedError=expected_error, sourceTreeSHA256=digest(closure) if closure else None,
            stdout=name+'.stdout', stdoutSHA256=sha(out/(name+'.stdout')),
            stderr=name+'.stderr', stderrSHA256=sha(out/(name+'.stderr'))))
        if closure is not None:
            assert manifest(cwd) == closure, 'source changed after ' + name
        print(name, result.returncode, flush=True)
        if expected_error is not None:
            assert result.returncode != 0 and expected_error in (result.stdout + result.stderr).decode(errors='replace'), (name, result.returncode)
        elif result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-6000:])
        return result.stdout.decode(errors='replace')

    def extract(label):
        dest = build / label
        with tarfile.open(out/'inputs'/(label+'-source.tar.gz')) as archive:
            archive.extractall(dest, filter='data')
        vm = dest / 'vm' if (dest / 'vm/Cargo.toml').is_file() else dest
        actual = manifest(vm)
        expected = json.loads((out/'inputs'/(label+'-manifest.json')).read_text())
        assert actual == expected, label + ' source manifest mismatch'
        closures[label] = actual
        return vm

    def configuration(label, vm, feature, profile, archive, probe=False):
        name = '-'.join([label, feature, profile])
        target = build / (name + '-target')
        flags = ['--all-features'] if feature == 'all' else ['--features', 'experimental-swift-reactor']
        if profile == 'release':
            flags += ['--release']
        closure = closures[label]
        output = run(name+'-build', ['cargo','test','--locked','--offline','--lib','--no-run','--message-format=json',*flags], vm, target, closure)
        found = []
        for line in output.splitlines():
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if obj.get('reason') == 'compiler-artifact' and obj.get('executable') and obj.get('profile', {}).get('test'):
                found.append(Path(obj['executable']))
        assert len(found) == 1
        binary = found[0]
        selector = ['independent_af_'] if probe else []
        listed = run(name+'-list', [str(binary), *selector, '--list'], vm, target, closure)
        tests = [line.removesuffix(': test') for line in listed.splitlines() if line.endswith(': test')]
        assert tests
        output = run(name+'-run', [str(binary), *selector, '--test-threads=1'], vm, target, closure)
        summary = re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', output)
        assert len(summary) == 1 and summary[0] == ('ok', str(len(tests)), '0', '0'), (name, summary)
        member = 'unit/' + name
        archive.add(binary, arcname=member, recursive=False)
        binaries.append(dict(configuration=name, kind='unit-executable', member=member, sha256=sha(binary), tests=tests, passed=len(tests), runCommand=name+'-run'))
        if not probe:
            run(name+'-library', ['cargo','build','--locked','--offline','--lib',*flags], vm, target, closure)
            library = target / profile / 'libmixer_vm.dylib'
            exports = run(name+'-exports', ['nm','-gU',str(library)], vm, target, closure)
            symbols = sorted(line.split()[-1] for line in exports.splitlines() if line.split() and line.split()[-1].startswith('_mixer_'))
            member = 'abi/' + name + '.dylib'
            archive.add(library, arcname=member, recursive=False)
            binaries.append(dict(configuration=name, kind='abi-library', member=member, sha256=sha(library), exportedMixerSymbols=symbols))
            return tests, symbols
        return tests, None

    try:
        run('rustc-version', ['rustc','-vV'], ROOT)
        run('cargo-version', ['cargo','-V'], ROOT)
        run('python-version', ['python3','--version'], ROOT)
        run('revision', ['git','rev-parse','HEAD'], ROOT)
        sources = {label: extract(label) for label in ['baseline', 'candidate']}
        original_common = (sources['baseline']/'src/experimental/execution/mod.rs').read_bytes()
        candidate_common = (sources['candidate']/'src/experimental/execution/mod.rs').read_bytes()
        marker = b'impl Control {\n'
        start = candidate_common.index(marker)
        end = candidate_common.index(b'#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]\npub(crate) struct Frame', start)
        added = candidate_common[start:end]
        assert b'fn function_entry' in added and b'fn decoded_fixture' in added
        assert candidate_common[:start] + candidate_common[end:] == original_common
        (out/'literal-frozen-parity.json').write_bytes(encoded(dict(
            originalSHA256=sha(sources['baseline']/'src/experimental/execution/mod.rs'),
            candidateSHA256=sha(sources['candidate']/'src/experimental/execution/mod.rs'),
            approvedInsertedControlImplSHA256=hashlib.sha256(added).hexdigest(),
            everyOriginalByteUnchanged=True,
            originalSharedPrimitiveSHA256=sha(sources['baseline']/'src/experimental/execution/borrowed.rs'),
            candidateSharedPrimitiveSHA256=sha(sources['candidate']/'src/experimental/execution/borrowed.rs'))))
        assert closures['baseline']['src/experimental/execution/borrowed.rs'] == closures['candidate']['src/experimental/execution/borrowed.rs']
        outcomes = {}
        with tarfile.open(portable, 'w:gz') as archive:
            if args.reuse_product_result:
                prior = args.reuse_product_result.resolve()
                prior_receipt = json.loads((prior/'receipt.json').read_text())
                for label in ['baseline','candidate']:
                    assert prior_receipt['sourceTreeSHA256'][label] == digest(closures[label])
                assert (prior/'rustc-version.stdout').read_bytes() == (out/'rustc-version.stdout').read_bytes()
                assert sha(prior/'qualifying-artifacts.tar.gz') == prior_receipt['qualifyingArchiveSHA256']
                for command in prior_receipt['commands']:
                    if not command['name'].startswith(('baseline-','candidate-')): continue
                    assert command['exitCode'] == 0
                    for stream in ['stdout','stderr']:
                        assert sha(prior/command[stream]) == command[stream+'SHA256']
                        shutil.copyfile(prior/command[stream],out/command[stream])
                    commands.append(command)
                with tarfile.open(prior/'qualifying-artifacts.tar.gz') as prior_archive:
                    for binary in prior_receipt['binaries']:
                        assert binary['configuration'].startswith(('baseline-','candidate-'))
                        member = prior_archive.getmember(binary['member'])
                        data = prior_archive.extractfile(member).read()
                        assert hashlib.sha256(data).hexdigest() == binary['sha256']
                        import io
                        archive.addfile(member,io.BytesIO(data))
                        binaries.append(binary)
                for label in ['baseline','candidate']:
                    for feature in ['swift','all']:
                        for profile in ['debug','release']:
                            name='-'.join([label,feature,profile])
                            unit=[b for b in binaries if b['configuration']==name and b['kind']=='unit-executable']
                            abi=[b for b in binaries if b['configuration']==name and b['kind']=='abi-library']
                            assert len(unit)==len(abi)==1
                            outcomes[(label,feature,profile)]=(unit[0]['tests'],abi[0]['exportedMixerSymbols'])
                shutil.copyfile(prior/'receipt.json',out/'inputs/reused-product-receipt.json')
                reused_product=dict(path=str(prior),receiptSHA256=sha(prior/'receipt.json'),reason='Unmodified baseline/candidate tests and ABI all passed; only independent test harness Debug formatting assertion changed')
            else:
                for label, vm in sources.items():
                    for feature in ['swift', 'all']:
                        for profile in ['debug','release']:
                            outcomes[(label,feature,profile)] = configuration(label,vm,feature,profile,archive)
            for feature in ['swift','all']:
                for profile in ['debug','release']:
                    before, after = outcomes[('baseline',feature,profile)], outcomes[('candidate',feature,profile)]
                    assert set(before[0]) <= set(after[0]), 'pre-existing unit test removed'
                    assert before[1] == after[1], 'public Mixer C exports changed'
                    comparisons.append(dict(feature=feature,profile=profile,baselineTests=len(before[0]),candidateTests=len(after[0]),addedTests=sorted(set(after[0])-set(before[0])),publicMixerCExportsEqual=True))
            vm = build / 'independent' / 'vm'
            shutil.copytree(sources['candidate'], vm)
            module = vm / 'src/experimental_swift_reactor/frame_operations.rs'
            module.write_bytes(module.read_bytes() + b'\n#[cfg(test)]\n#[path="independent_active_frame_review_tests.rs"]\nmod independent_review_tests;\n')
            shutil.copyfile(out/'inputs/independent-probes.rs', vm/'src/experimental_swift_reactor/independent_active_frame_review_tests.rs')
            fault_module = vm/'src/experimental_swift_reactor/frame_operations_tests.rs'
            fault_module.write_bytes(fault_module.read_bytes() + b'\n#[path="independent_active_frame_fault_review_tests.rs"]\nmod independent_fault_review_tests;\n')
            shutil.copyfile(out/'inputs/independent-fault-probes.rs', vm/'src/experimental_swift_reactor/independent_active_frame_fault_review_tests.rs')
            closures['independent'] = manifest(vm)
            (out/'independent-manifest.json').write_bytes(encoded(closures['independent']))
            with tarfile.open(out/'independent-source.tar.gz', 'w:gz') as source_archive:
                for file in sorted(vm.rglob('*')):
                    if file.is_file():
                        source_archive.add(file, arcname='vm/'+str(file.relative_to(vm)), recursive=False)
            for feature in ['swift','all']:
                for profile in ['debug','release']:
                    configuration('independent',vm,feature,profile,archive,True)
        private_vm = build/'private-parent'/'vm'
        shutil.copytree(sources['candidate'], private_vm)
        private_execution = private_vm/'src/experimental_swift_reactor/execution.rs'
        private_execution.write_bytes(private_execution.read_bytes() + b'\nfn independent_forbidden_inherited_value_access(phase: &mut frame_operations::FrameOperationPhase<\'_>) { let _ = &mut phase.phase; }\n')
        closures['private-parent'] = manifest(private_vm)
        (out/'private-parent-manifest.json').write_bytes(encoded(closures['private-parent']))
        with tarfile.open(out/'private-parent-source.tar.gz','w:gz') as private_archive:
            for file in sorted(private_vm.rglob('*')):
                if file.is_file(): private_archive.add(file,arcname='vm/'+str(file.relative_to(private_vm)),recursive=False)
        run('private-parent-inherited-value-rejection', ['cargo','check','--locked','--offline','--lib','--features','experimental-swift-reactor'], private_vm, build/'private-parent-target', closures['private-parent'], 'error[E0616]')
        status = 'passed-host-original-owner-review-matrix'
    finally:
        receipt = dict(schema=1,status=status,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            scope='Native macOS command-line host tests only; no native app, simulator, emulator, physical device, GA, invoke or full Swift acceptance',
            commands=commands,binaries=binaries,comparisons=comparisons,
            sourceTreeSHA256={label:digest(value) for label,value in closures.items()},
            inputs={str(p.relative_to(out)):sha(p) for p in sorted((out/'inputs').rglob('*')) if p.is_file()},
            qualifyingArchiveSHA256=sha(portable) if portable.is_file() else None,
            ownedBuildScratch=str(build), cleanup='pending')
        receipt['reusedProductEvidence']=reused_product
        (out/'receipt.json').write_bytes(encoded(receipt))
        print(str(out/'receipt.json'), flush=True)


if __name__ == '__main__':
    main()
