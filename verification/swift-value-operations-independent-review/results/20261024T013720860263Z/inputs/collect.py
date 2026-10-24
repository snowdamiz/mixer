#!/usr/bin/env python3
"""Read-only independent evidence replay and fresh native private-route probes."""
from pathlib import Path
import datetime, hashlib, json, os, re, shutil, subprocess, sys, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-executor-operations'
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / 'results' / STAMP
BUILD = HERE / 'build' / STAMP
OUT.mkdir(parents=True)
BUILD.mkdir(parents=True)
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
encode = lambda x: (json.dumps(x, sort_keys=True, indent=2) + '\n').encode()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda x: hashlib.sha256(encode(x)).hexdigest()
def manifest(p):
    return {str(x.relative_to(p)): sha(x) for x in sorted(p.rglob('*')) if x.is_file()}

commands = []
binaries = []
source = {}
receipt = dict(schema=1, status='failed', observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               scope='macOS aarch64 native private zero-frame value operations; no device, full target, publication or GA gate',
               commands=commands, binaries=binaries)

def command(name, argv, cwd, target=None, closure=None, wanted=0):
    if closure is not None:
        assert manifest(cwd) == closure, 'source changed before ' + name
    env = dict(ENV)
    if target is not None: env['CARGO_TARGET_DIR'] = str(target)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    log = OUT / (name + '.log')
    log.write_bytes(result.stdout)
    commands.append(dict(name=name, argv=argv, cwd=str(cwd), target=str(target) if target else None,
                         startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         exit=result.returncode, log=log.name, logSHA256=sha(log), sourceBeforeAfterVerified=closure is not None))
    if closure is not None:
        assert manifest(cwd) == closure, 'source changed after ' + name
    print(name, result.returncode, flush=True)
    assert result.returncode == wanted, result.stdout.decode(errors='replace')[-12000:]
    return result.stdout.decode(errors='replace')

def extract(archive, destination):
    with tarfile.open(archive) as tf: tf.extractall(destination, filter='data')
    return destination / 'vm'

def tests(label, dest, closure, flags, release, selected):
    target = BUILD / (label + '-target')
    argv = ['cargo', 'test', '--locked', '--offline', '--lib', '--no-run', '--message-format=json', *flags]
    if release: argv.append('--release')
    output = command(label + '-build', argv, dest, target, closure)
    artifacts = []
    for line in output.splitlines():
        try: obj = json.loads(line)
        except ValueError: continue
        if obj.get('reason') == 'compiler-artifact' and obj.get('profile', {}).get('test') and obj.get('executable'):
            artifacts.append(Path(obj['executable']))
    assert len(artifacts) == 1
    executable = artifacts[0]
    listed = command(label + '-list', [str(executable), '--list'], dest, target, closure)
    identities = [s[:-6] for s in listed.splitlines() if s.endswith(': test')]
    chosen = [s for s in identities if selected in s]
    assert len(chosen) == (11 if 'independent_values_' in selected else 12)
    run = command(label + '-run', [str(executable), selected, '--test-threads=1'], dest, target, closure)
    actual = re.findall(r'^test ([^ ]+) \.\.\. ok$', run, re.M)
    assert sorted(actual) == sorted(chosen)
    summary = re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;', run)
    assert summary == [(str(len(chosen)), '0')]
    row = dict(label=label, path=str(executable), sha256=sha(executable), kind='derived-independent-tests' if 'independent' in selected else 'unmodified-product-selected-tests',
               listedTests=identities, selectedTests=chosen, passed=len(actual), ignored=0,
               buildCommand=label+'-build', listCommand=label+'-list', runCommand=label+'-run', sourceTreeSHA256=digest(closure))
    binaries.append(row)

try:
    seal = json.loads((PRODUCER/'seal.json').read_text())
    receipt['producerSealSHA256'] = sha(PRODUCER/'seal.json')
    # Every sealed producer file is read and hashed. No producer artifact is modified.
    for name, expected in seal['files'].items(): assert sha(ROOT/name) == expected, name
    candidates = [p for p in (PRODUCER/'results').iterdir() if (p/'receipt.json').exists()
                  and json.loads((p/'receipt.json').read_text()).get('status', '').startswith('passed-private-zero-frame-')]
    saved = max(candidates)
    producer = json.loads((saved/'receipt.json').read_text())
    source = json.loads((saved/'candidate-manifest.json').read_text())
    assert digest(source) == seal['sourceTreeSHA256'] == producer['candidateSourceTreeSHA256']
    assert all(sha(ROOT/'vm'/p) == expected for p, expected in source.items())
    receipt['sourceRevision'] = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    receipt['sourceTreeSHA256'] = digest(source)
    receipt['sourceCount'] = len(source)
    receipt['producerResults'] = str(saved.relative_to(ROOT))
    (OUT/'inputs').mkdir()
    for name in ['collect.py','verify.py','audit_accounting.py','inputs/independent_tests.rs']:
        p = HERE/name
        (OUT/'inputs'/p.name).write_bytes(p.read_bytes())
    for name in ['seal.json']:
        (OUT/'inputs'/('producer-'+name)).write_bytes((PRODUCER/name).read_bytes())
    for name in ['receipt.json','candidate-manifest.json','baseline-product-closure.json','candidate-product-closure.json','baseline-layout-closure.json','candidate-layout-closure.json','binding-map.json','verified-summary.json']:
        (OUT/'inputs'/('producer-'+name)).write_bytes((saved/name).read_bytes())
    for name in ['collect.py','owner-layout-probe.rs','operation-layout-probe.rs']:
        (OUT/'inputs'/('producer-'+name)).write_bytes((saved/'inputs'/name).read_bytes())
    for name in ['candidate-source.tar.gz','baseline-source.tar']:
        shutil.copyfile(saved/name, OUT/name)
    (OUT/'source-manifest.json').write_bytes(encode(source))
    assert sha(OUT/'candidate-source.tar.gz') == producer['candidateSourceArchiveSHA256']
    assert sha(OUT/'baseline-source.tar') == producer['baselineSourceArchiveSHA256']
    command('rustc-version', ['rustc','-vV'], ROOT)
    command('cargo-version', ['cargo','-V'], ROOT)
    command('python-version', ['python3','--version'], ROOT)
    # Independent checks of raw evidence, including actual executable hashes/lists.
    original_commands = {r['name']: r for r in producer['commands']}
    for row in original_commands.values():
        assert sha(saved/row['log']) == row['logSHA256']
        assert row['exit'] == (101 if row['name'].endswith('clippy-broad') else 0)
    (OUT/'producer-logs').mkdir()
    for row in original_commands.values():
        shutil.copyfile(saved/row['log'], OUT/'producer-logs'/row['log'])
    old_binary_checks = []
    for index, row in enumerate(producer['binaries']):
        executable = Path(row['path'])
        assert sha(executable) == row['sha256']
        listed = command('producer-binary-'+str(index)+'-list', [str(executable),'--list'], Path(original_commands[row['listCommand']]['cwd']))
        identities = [s for s in listed.splitlines() if s.endswith(': test')]
        assert identities == row['runtimeTests']
        runtime = (saved/original_commands[row['runCommand']]['log']).read_text()
        counts = re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;',runtime)
        assert len(counts) == 1 and sum(map(int,counts[0])) == len(identities)
        old_binary_checks.append(dict(sha256=row['sha256'], target=row['target'], configuration=row['configuration'], listed=len(identities), passed=int(counts[0][0]), ignored=int(counts[0][1])))
    receipt['producerBinaryChecks'] = old_binary_checks
    baseline = extract(OUT/'baseline-source.tar', BUILD/'baseline-source')
    product = extract(OUT/'candidate-source.tar.gz', BUILD/'product-source')
    baseline_closure = manifest(baseline)
    assert baseline_closure == json.loads((saved/'baseline-product-closure.json').read_text())
    assert manifest(product) == source
    changed = sorted(p for p in set(source)|set(baseline_closure) if source.get(p) != baseline_closure.get(p))
    assert changed == sorted(['src/experimental/execution/borrowed.rs', 'src/experimental_swift_reactor/execution.rs', 'src/experimental_swift_reactor/execution_tests.rs', 'src/experimental_swift_reactor/value_operations.rs', 'src/experimental_swift_reactor/value_operation_tests.rs'])
    assert source['src/experimental/execution/mod.rs'] == baseline_closure['src/experimental/execution/mod.rs']
    shared = []
    for tree in [baseline, product]:
        body = (tree/'src/experimental/execution/borrowed.rs').read_text()
        shared.append(body[body.index('    if saturating {',body.index(' fn numeric<')):])
    assert shared[0] == shared[1]
    receipt['changedSourceFiles'] = changed
    receipt['frozenOwnerAndPrimitiveBodyLiteral'] = True
    # Compare original raw layout observations, not just the generated summary.
    layouts = []
    for after in [r for r in producer['layouts'] if r['label'] == 'candidate']:
        before = next(r for r in producer['layouts'] if r['label'] == 'baseline' and all(r[k]==after[k] for k in ['configuration','profile','cfg']))
        assert [r for r in before['records'] if r.startswith('value_owner')] == [r for r in after['records'] if r.startswith('value_owner')]
        values = lambda r: {x.split('|')[1]:int(x.split('|')[2]) for x in r['records'] if x.startswith('value_bounds|')}
        b, a = values(before), values(after)
        assert a['header'] == b['header'] + a['permanent']
        assert a['construction'] == b['construction']
        assert a['phase'] == a['declared_operation'] + a['active']
        layouts.append(dict(configuration=after['configuration'],profile=after['profile'],cfg=after['cfg'],before=b,after=a))
    assert len(layouts) == 8
    receipt['producerRawLayoutsVerified'] = layouts
    for profile in ['debug','release']:
        for config, flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
            tests('product-'+config+'-'+profile, product, source, flags, profile=='release', 'swift_values_')
    # Only test-module wiring is appended. No production function or layout is instrumented.
    derived = extract(OUT/'candidate-source.tar.gz', BUILD/'independent-test-source')
    operation = derived/'src/experimental_swift_reactor/value_operations.rs'
    glue = '\n#[cfg(test)] #[path = "independent_value_review_tests.rs"] mod independent_value_review_tests;\n'
    operation.write_text(operation.read_text()+glue)
    (operation.parent/'independent_value_review_tests.rs').write_bytes((OUT/'inputs/independent_tests.rs').read_bytes())
    derived_closure = manifest(derived)
    assert all(derived_closure[p]==expected for p,expected in source.items() if p!='src/experimental_swift_reactor/value_operations.rs')
    assert operation.read_bytes() == (product/'src/experimental_swift_reactor/value_operations.rs').read_bytes()+glue.encode()
    (OUT/'derived-source-manifest.json').write_bytes(encode(derived_closure))
    with tarfile.open(OUT/'derived-test-source.tar.gz','w:gz') as tf:
        for p in sorted(derived.rglob('*')):
            if p.is_file(): tf.add(p,arcname='vm/'+str(p.relative_to(derived)),recursive=False)
    for profile in ['debug','release']:
        for config, flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
            tests('independent-'+config+'-'+profile, derived, derived_closure, flags, profile=='release', 'independent_values_')
    assert all(sha(ROOT/'vm'/p)==expected for p,expected in source.items())
    receipt['status'] = 'passed-selected-native-outcomes-accounting-review-separate'
except Exception as exc:
    receipt['failure'] = str(exc)
    raise
finally:
    (OUT/'receipt.json').write_bytes(encode(receipt))
    print(str(OUT), flush=True)
