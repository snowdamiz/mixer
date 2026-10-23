#!/usr/bin/env python3
"""Pinned, non-authorizing one-body-at-a-time decoder allocation diagnostics."""
import sys
sys.dont_write_bytecode = True
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
from summarize import summarize, attribute
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location('qualification_support', ROOT / 'compiler/qualification_support.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
REVISION = '64123c509e861ddd522631b293eadebdaca11341'
ARTIFACT = ROOT / 'compiler/experiments/profile-budget/local/2026-10-22-qualified/build-osize-compress/wasm32-unknown-wasip1/release/fieldlog-corpus.wasm'
LINK_MAP = HERE.parent / 'local/2026-10-22-qualified/osize-compress.map'
LINK_MAP_HASH = '8eaa353aca7ed3549b04c1f89ba22a19f7a42a247a44ab7173b725f7e61e6cd5'
ARTIFACT_HASH = '19ac88f26f0daf34b64acb3c5b895fc79b52701368fc4c532ac8ede5844fee75'
INPUTS = {
    'command': {'artifact': ARTIFACT, 'sha256': ARTIFACT_HASH, 'bytes': 52_008_982,
                'link_map': LINK_MAP, 'link_map_sha256': LINK_MAP_HASH,
                'functions': 79_837, 'instructions': 6_505_962, 'body_bytes': 13_869_023},
    'reactor': {'artifact': ROOT / 'compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm',
                'sha256': '24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994', 'bytes': 53_777_114,
                'link_map': ROOT / 'compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/reactor.map',
                'link_map_sha256': '4a0b71f0b462798fef168824952d2a74d2a3956425e5380667eb9e85bde48746',
                'functions': 79_832, 'instructions': 6_505_659, 'body_bytes': 15_635_455},
}
DECODE_OBSERVER = '''
#[cfg(test)]
pub(crate) fn measurement_decode_body(bytes: &[u8], base: usize, function: u32, limits: &Limits, inv: &mut Inventory) -> Result<(Vec<Type>,Vec<Instruction>),Error> {
    limits.check()?;
    if bytes.len() > limits.module_bytes { return Err(Error::new("limit", "individual diagnostic body exceeds existing byte ceiling", Some(function), base)); }
    let mut b=Reader::at(bytes,base); b.function=Some(function); let mut locals=vec![];
    for _ in 0..b.count(limits.locals)? { let n=b.count(limits.locals.saturating_sub(locals.len()))?; let ty=b.ty(limits.profile)?; locals.extend(std::iter::repeat_n(ty,n)); }
    let mut count=0; let code=decode_code(&mut b,limits,inv,&mut count)?; b.end()?; Ok((locals,code))
}
'''
VALIDATE_OBSERVER = '''
#[cfg(test)]
pub(crate) fn measurement_validator_layout() -> (usize,usize) { (std::mem::size_of::<Control>(),std::mem::size_of::<Validator>()) }
'''


def select_input(kind='command', artifact=None, supplied_sha256=None):
    """Only the two retained immutable artifacts are diagnostic inputs."""
    if kind not in INPUTS:
        raise ValueError('unknown pinned input')
    selected = dict(INPUTS[kind])
    if supplied_sha256 is not None and supplied_sha256 != selected['sha256']:
        raise ValueError('supplied SHA-256 does not equal selected immutable pin')
    selected['artifact'] = Path(artifact if artifact is not None else selected['artifact']).resolve()
    selected['link_map'] = selected['link_map'].resolve()
    return selected


def validate_input(selected):
    artifact, link_map = selected['artifact'], selected['link_map']
    if not artifact.is_file() or not link_map.is_file():
        raise ValueError('pinned artifact and compiler link map must be regular files')
    if artifact.stat().st_size != selected['bytes'] or helper.digest(artifact) != selected['sha256']:
        raise ValueError('only unchanged selected pinned full Swift artifact is measurable')
    if helper.digest(link_map) != selected['link_map_sha256']:
        raise ValueError('pinned compiler link map missing or changed')


def validate_complete_inventory(selected, observed, statistics):
    if (observed['source_bytes'] != selected['bytes']
            or observed['functions'] != selected['functions']
            or statistics['function_count'] != selected['functions']
            or statistics['raw_instruction_count'] != selected['instructions']
            or statistics['wire_body_bytes'] != selected['body_bytes']):
        raise ValueError('complete raw inventory disagrees with selected immutable artifact')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='2026-10-22')
    parser.add_argument('--input', choices=sorted(INPUTS), default='command')
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--artifact-sha256')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name, re.ASCII):
        raise ValueError('bounded ASCII label required')
    selected = select_input(args.input, args.artifact, args.artifact_sha256)
    validate_input(selected)
    artifact, link_map = selected['artifact'], selected['link_map']
    work = HERE.parent / 'local' / ('functions-' + args.name)
    evidence = (HERE / 'evidence' if args.input == 'command' else ROOT / 'verification/swift-reactor-function-diagnostics') / args.name
    work.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    env = helper.clean_environment()
    env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env['PATH']
    commands = []
    recorder = helper.CommandRecorder(evidence, commands, ROOT)
    sources = {str(path.relative_to(ROOT)): helper.digest(path) for path in [Path(__file__), HERE / 'probe.rs', HERE / 'summarize.py', HERE / 'test_summary.py', HERE / 'test_inputs.py', HERE / 'README.md', ROOT / 'compiler/qualification_support.py']}
    record = {'schema': 1, 'authorization': False, 'status': 'running', 'model': 'gpt-6.1-sol', 'reasoning': 'xhigh',
              'scope': 'read-only metadata, scalar-arity operand-height inventory and unchanged-ceiling individual body diagnostics; not a Module decode/type validation/instantiation/execution or device qualification',
              'input': args.input, 'valid': False,
              'observedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'vm_revision': REVISION, 'source_manifest': sources, 'commands': commands,
              'production_limits_changed': False,
              'artifact': {'path': str(artifact), 'bytes': artifact.stat().st_size, 'sha256': selected['sha256']},
              'link_map': {'path': str(link_map), 'bytes': link_map.stat().st_size, 'sha256': selected['link_map_sha256']},
              'allocator_scope': 'direct Rust requested live/maximum bytes and counts; excludes allocator internal metadata and transient realloc copies/native libraries',
              'rss_scope': 'Darwin process maximum RSS including harness/source/index/libraries; no app steady-state/OTA comparison'}
    def run(name, command, extra_env=None, **kwargs):
        actual = dict(env)
        if extra_env: actual.update(extra_env)
        value = recorder.run(name, command, env=actual, **kwargs)
        print(name + ': exit ' + str(commands[-1]['exitCode']), flush=True)
        return value
    try:
        run('summary-negative-tests', [sys.executable, '-B', HERE / 'test_summary.py'])
        run('input-pin-tests', [sys.executable, '-B', HERE / 'test_inputs.py'])
        source_tar = work / 'source.tar'
        git = shutil.which('git', path=env['PATH'])
        record['mixer_revision'] = run('mixer-revision', [git, 'rev-parse', 'HEAD']).strip()
        record['dirty_tree'] = run('mixer-dirty-tree', [git, 'status', '--short'])
        run('source-export', [git, 'archive', '--format=tar', '--output=' + str(source_tar), REVISION, 'vm', 'contracts'])
        record['source_archive_sha256'] = helper.digest(source_tar)
        with tarfile.open(source_tar) as stream: stream.extractall(work / 'source', filter='data')
        vm = work / 'source/vm'
        original = {str(p.relative_to(vm)): helper.digest(p) for p in vm.rglob('*') if p.is_file()}
        appends = {'src/lib.rs': '\n#[cfg(test)]\nmod body_budget;\n', 'src/decode.rs': DECODE_OBSERVER, 'src/validate.rs': VALIDATE_OBSERVER}
        for path, appended in appends.items():
            target = vm / path
            target.write_text(target.read_text() + appended)
        shutil.copyfile(HERE / 'probe.rs', vm / 'src/body_budget.rs')
        record['test_only_appends_sha256'] = {path: hashlib.sha256(value.encode()).hexdigest() for path, value in appends.items()}
        cargo, rustc = [shutil.which(tool, path=env['PATH']) for tool in ('cargo', 'rustc')]
        record['tools'] = {name: helper.tool_identity(path) for name, path in [('cargo', cargo), ('rustc', rustc), ('python', sys.executable), ('git', git), ('time', '/usr/bin/time')]}
        record['versions'] = {tool: run('version-' + tool, [path, '--version']).strip() for tool, path in [('cargo', cargo), ('rustc', rustc)]}
        record['host'] = {'os': run('host-os', ['/usr/bin/sw_vers']).strip(), 'architecture': run('host-architecture', ['/usr/bin/uname', '-m']).strip()}
        compiled = run('build-probe', [cargo, 'test', '--offline', '--release', '--lib', '--no-run', '--message-format=json', '--manifest-path', vm / 'Cargo.toml', '--target-dir', HERE.parent / 'local/functions-diagnostic-target'])
        binaries = [value['executable'] for line in compiled.splitlines() if line.startswith('{')
                    for value in [helper.strict_json(line)] if value.get('reason') == 'compiler-artifact' and value.get('executable') and value['target']['name'] == 'mixer_vm']
        if len(binaries) != 1: raise ValueError('expected one isolated test binary')
        compiled_binary = Path(binaries[0])
        # A later run reuses Cargo's target path. Preserve this run's exact tool
        # before that path can be overwritten by another exported source root.
        tools = work / 'tools'
        tools.mkdir()
        binary = tools / 'mixer-vm-body-probe'
        shutil.copy2(compiled_binary, binary)
        record['binary'] = helper.tool_identity(binary)
        if helper.digest(compiled_binary) != record['binary']['sha256']:
            raise ValueError('retained diagnostic executable mismatch')
        run('original-negative-tests', [binary, 'body_budget::tests::', '--nocapture', '--test-threads=1'])
        local_artifact = work / 'candidate.wasm'; shutil.copyfile(artifact, local_artifact)
        if helper.digest(local_artifact) != selected['sha256']: raise ValueError('copied artifact mismatch')
        csv = work / 'functions.csv'
        output = run('measure-candidate', ['/usr/bin/time', '-l', binary, '--exact', 'body_budget::measure_candidate', '--nocapture', '--test-threads=1'],
                     extra_env={'MIXER_FUNCTION_SOURCE': str(local_artifact), 'MIXER_FUNCTION_CSV': str(csv), 'MIXER_FUNCTION_EXPECTED_BYTES': str(selected['bytes'])}, timeout=180)
        summaries = [line.partition('SUMMARY_JSON ')[2] for line in output.splitlines() if 'SUMMARY_JSON ' in line]
        if len(summaries) != 1: raise ValueError('expected exactly one measurement summary')
        observed = helper.strict_json(summaries[0]); record['observed'] = observed
        resources = [line.partition('RESOURCE_JSON ')[2] for line in output.splitlines() if 'RESOURCE_JSON ' in line]
        if len(resources) != 1: raise ValueError('expected one actual resource observation')
        record['resources'] = helper.strict_json(resources[0])
        statistics = summarize(csv, observed)
        validate_complete_inventory(selected, observed, statistics)
        attribution = attribute(csv, link_map, statistics)
        (evidence / 'function-attribution.json').write_text(json.dumps(attribution, indent=2) + '\n')
        record['function_attribution'] = {'path': 'function-attribution.json', 'sha256': helper.digest(evidence / 'function-attribution.json')}
        (evidence / 'statistics.json').write_text(json.dumps(statistics, indent=2) + '\n')
        record['statistics'] = {'path': 'statistics.json', 'sha256': helper.digest(evidence / 'statistics.json')}
        zipped = evidence / 'functions.csv.gz'
        with csv.open('rb') as source, zipped.open('wb') as dest:
            with gzip.GzipFile(fileobj=dest, mode='wb', filename='', compresslevel=9, mtime=0) as compressed:
                shutil.copyfileobj(source, compressed)
        record['all_functions'] = {'path': zipped.name, 'gzipBytes': zipped.stat().st_size, 'gzipSHA256': helper.digest(zipped), 'rawBytes': csv.stat().st_size, 'rawSHA256': helper.digest(csv)}
        stderr = (evidence / 'measure-candidate.stderr').read_text()
        rss = re.findall(r'^\s*(\d+)\s+maximum resident set size\s*$', stderr, re.MULTILINE)
        if len(rss) != 1: raise ValueError('unknown Darwin peak RSS output')
        record['process_max_rss_bytes'] = int(rss[0])
        for path, digest in original.items():
            file = vm / path
            if path in appends:
                expected = appends[path].encode()
                data = file.read_bytes()
                if not data.endswith(expected) or hashlib.sha256(data[:-len(expected)]).hexdigest() != digest: raise ValueError('unexpected production edit: ' + path)
            elif helper.digest(file) != digest: raise ValueError('production export changed: ' + path)
        if helper.digest(local_artifact) != selected['sha256'] or helper.digest(artifact) != selected['sha256']: raise ValueError('artifact changed during diagnostic')
        validate_input(selected)
        if any(helper.digest(ROOT / path) != digest for path, digest in sources.items()): raise ValueError('probe source changed during run')
        record['source_digest'] = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        record['status'] = 'measurement complete; per-body rejections recorded; no module authorization or execution'
    except Exception as error:
        record['status'] = 'failed'; record['failure'] = str(error); raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'functions': observed['functions'], 'decoded': observed['successful_bodies'], 'source_digest': record['source_digest'], 'max_rss': record['process_max_rss_bytes']}, indent=2))


if __name__ == '__main__': main()
