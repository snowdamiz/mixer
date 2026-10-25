from pathlib import Path
import datetime, hashlib, json, os, platform, shutil, subprocess, sys

root = Path(__file__).resolve().parents[2]
packet = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')

def manifest(base):
    entries = []
    for path in sorted(base.rglob('*')):
        if path.is_file() and 'dist' not in path.relative_to(base).parts:
            data = path.read_bytes()
            entries.append({'path': str(path.relative_to(base)), 'sha256': sha(data), 'bytes': len(data)})
    return {'algorithm': 'sha256', 'sourceDigest': sha(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()), 'entries': entries}

def verify_inputs():
    bindings = json.loads((packet / 'frozen-bindings.json').read_text())['bindings']
    for entry in bindings:
        data = (root / entry['path']).read_bytes()
        assert sha(data) == entry['sha256'], entry['path']
        assert len(data) == entry['bytes'], entry['path']
    old = (root / 'verification/hosted-worker-pending-migration-history/candidate/src/engine.ts').read_bytes()
    new = (root / 'verification/hosted-worker-pending-migration-outbox/candidate/src/engine.ts').read_bytes()
    assert old.replace(b'r.registration_json===null&&r.registry_ack_version', b'r.registration_json===null&&r.track_outbox_json===null&&r.registry_ack_version', 1) == new
    production = []
    for p in sorted((packet / 'candidate/src').rglob('*')):
        if p.is_file():
            rel = p.relative_to(packet / 'candidate/src')
            assert p.read_bytes() == (root / 'verification/hosted-worker-pending-migration-outbox/candidate/src' / rel).read_bytes(), str(rel)
            production.append({'path': 'src/' + str(rel), 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size})
    return {'observedUTC': now(), 'bindingsVerified': len(bindings), 'productionFilesByteIdentical': len(production), 'production': production, 'exactOneNullOutboxCondition': True}

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
run = packet / 'runs' / stamp
run.mkdir(parents=True)
write(run / 'inputs-before.json', verify_inputs())
source = manifest(packet / 'candidate')
for e in source['entries']:
    target = run / 'source' / e['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((packet / 'candidate' / e['path']).read_bytes())
write(run / 'source-manifest.json', source)
node = str(Path(shutil.which('node')).resolve())
workerd = root / 'hosted-worker-controller/node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd'
commands = []

def command(name, args, extra=None):
    env = os.environ.copy()
    env.update(extra or {})
    record = {'name': name, 'command': args, 'cwd': str(root), 'startedUTC': now(), 'environment': extra or {}}
    with (run / (name + '.stdout.log')).open('w') as out, (run / (name + '.stderr.log')).open('w') as err:
        process = subprocess.run(args, cwd=root, env=env, stdout=out, stderr=err)
    record.update({'finishedUTC': now(), 'exitCode': process.returncode if process.returncode >= 0 else None, 'signal': -process.returncode if process.returncode < 0 else None, 'stdout': str((run / (name + '.stdout.log')).relative_to(root)), 'stderr': str((run / (name + '.stderr.log')).relative_to(root)), 'stdoutEOF': True, 'stderrEOF': True})
    commands.append(record)
    write(run / 'commands.json', commands)
    return process.returncode

command('node-version', [node, '--version'])
command('workerd-version', [str(workerd), '--version'])
command('package-versions', [node, '-e', "for(const name of ['miniflare','typescript','@cloudflare/workers-types'])console.log(name+' '+require('./hosted-worker-controller/node_modules/'+name+'/package.json').version)"])
versions = {'nodeExecutable': node, 'nodeExecutableSHA256': sha(Path(node).read_bytes()), 'workerdExecutable': str(workerd), 'workerdExecutableSHA256': sha(workerd.read_bytes()), 'python': sys.version, 'pythonExecutable': sys.executable, 'platform': platform.platform(), 'architecture': platform.machine(), 'versionOutputs': {n: (run / (n + '.stdout.log')).read_text().strip() for n in ['node-version', 'workerd-version', 'package-versions']}}
write(run / 'tool-versions.json', versions)
if command('build', [node, str(packet / 'candidate/build.mjs')]) == 0:
    command('acceptance', [node, str(packet / 'candidate/test/acceptance.mjs')], {'REVIEW_REPORT': str(run / 'acceptance-report.json')})
compiled = []
for p in sorted((packet / 'candidate/dist').rglob('*')):
    if p.is_file():
        rel = p.relative_to(packet / 'candidate/dist')
        data = p.read_bytes()
        target = run / 'compiled' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        compiled.append({'path': str(rel), 'sha256': sha(data), 'bytes': len(data)})
compiled_manifest = {'algorithm': 'sha256', 'compiledDigest': sha(json.dumps(compiled, sort_keys=True, separators=(',', ':')).encode()), 'entries': compiled}
write(run / 'compiled-manifest.json', compiled_manifest)
assert manifest(packet / 'candidate') == source
write(run / 'inputs-after.json', verify_inputs())
report = json.loads((run / 'acceptance-report.json').read_text()) if (run / 'acceptance-report.json').exists() else {'status': 'build-failed'}
summary = {'schema': 1, 'run': str(run.relative_to(root)), 'observedUTC': now(), 'status': report['status'], 'groupsRun': report.get('groupsRun', 0), 'groupsPassed': report.get('groupsPassed', 0), 'reviewSourceDigest': source['sourceDigest'], 'compiledDigest': compiled_manifest['compiledDigest'], 'commands': commands}
write(run / 'summary.json', summary)
write(packet / 'latest-run.json', summary)
print(json.dumps({k: v for k, v in summary.items() if k != 'commands'}, indent=2))
sys.exit(0 if summary['status'] == 'passed' else 1)
