#!/usr/bin/env python3
"""Pinned, non-authorizing one-body-at-a-time decoder allocation diagnostics."""
import sys
sys.dont_write_bytecode = True
import argparse
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='2026-10-22')
    parser.add_argument('--artifact', type=Path, default=ARTIFACT)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.name, re.ASCII):
        raise ValueError('bounded ASCII label required')
    artifact = args.artifact.resolve()
    if helper.digest(LINK_MAP) != LINK_MAP_HASH: raise ValueError('pinned compiler link map missing or changed')
    if artifact.stat().st_size != 52_008_982 or helper.digest(artifact) != ARTIFACT_HASH:
        raise ValueError('only unchanged pinned smallest full Swift candidate is measurable')
    work = HERE.parent / 'local' / ('functions-' + args.name)
    evidence = HERE / 'evidence' / args.name
    work.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    env = helper.clean_environment()
    env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env['PATH']
    commands = []
    recorder = helper.CommandRecorder(evidence, commands, ROOT)
    sources = {str(path.relative_to(ROOT)): helper.digest(path) for path in [Path(__file__), HERE / 'probe.rs', HERE / 'summarize.py', HERE / 'test_summary.py', ROOT / 'compiler/qualification_support.py']}
    record = {'schema': 1, 'authorization': False, 'status': 'running', 'model': 'gpt-6.1-sol', 'reasoning': 'xhigh',
              'scope': 'read-only metadata and unchanged-ceiling individual body diagnostics; not a Module decode/type validation/instantiation/execution or device qualification',
              'vm_revision': REVISION, 'source_manifest': sources, 'commands': commands,
              'production_limits_changed': False,
              'artifact': {'path': str(artifact), 'bytes': artifact.stat().st_size, 'sha256': ARTIFACT_HASH},
              'link_map': {'path': str(LINK_MAP), 'bytes': LINK_MAP.stat().st_size, 'sha256': LINK_MAP_HASH},
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
        source_tar = work / 'source.tar'
        git = shutil.which('git', path=env['PATH'])
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
        record['versions'] = {tool: run('version-' + tool, [path, '--version']).strip() for tool, path in [('cargo', cargo), ('rustc', rustc)]}
        record['host'] = {'os': run('host-os', ['/usr/bin/sw_vers']).strip(), 'architecture': run('host-architecture', ['/usr/bin/uname', '-m']).strip()}
        compiled = run('build-probe', [cargo, 'test', '--release', '--lib', '--no-run', '--message-format=json', '--manifest-path', vm / 'Cargo.toml', '--target-dir', work / 'target'])
        binaries = [value['executable'] for line in compiled.splitlines() if line.startswith('{')
                    for value in [helper.strict_json(line)] if value.get('reason') == 'compiler-artifact' and value.get('executable') and value['target']['name'] == 'mixer_vm']
        if len(binaries) != 1: raise ValueError('expected one isolated test binary')
        binary = Path(binaries[0]); record['binary'] = helper.tool_identity(binary)
        run('original-negative-tests', [binary, 'body_budget::tests::', '--nocapture', '--test-threads=1'])
        local_artifact = work / 'candidate.wasm'; shutil.copyfile(artifact, local_artifact)
        if helper.digest(local_artifact) != ARTIFACT_HASH: raise ValueError('copied artifact mismatch')
        csv = work / 'functions.csv'
        output = run('measure-candidate', ['/usr/bin/time', '-l', binary, '--exact', 'body_budget::measure_candidate', '--nocapture', '--test-threads=1'],
                     extra_env={'MIXER_FUNCTION_SOURCE': str(local_artifact), 'MIXER_FUNCTION_CSV': str(csv)}, timeout=180)
        summaries = [line.partition('SUMMARY_JSON ')[2] for line in output.splitlines() if 'SUMMARY_JSON ' in line]
        if len(summaries) != 1: raise ValueError('expected exactly one measurement summary')
        observed = helper.strict_json(summaries[0]); record['observed'] = observed
        resources = [line.partition('RESOURCE_JSON ')[2] for line in output.splitlines() if 'RESOURCE_JSON ' in line]
        if len(resources) != 1: raise ValueError('expected one actual resource observation')
        record['resources'] = helper.strict_json(resources[0])
        statistics = summarize(csv, observed)
        if statistics['raw_instruction_count'] != 6_505_962 or statistics['wire_body_bytes'] != 13_869_023: raise ValueError('raw inventory disagrees with established immutable artifact')
        attribution = attribute(csv, LINK_MAP, statistics)
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
        if helper.digest(local_artifact) != ARTIFACT_HASH or helper.digest(artifact) != ARTIFACT_HASH: raise ValueError('artifact changed during diagnostic')
        if any(helper.digest(ROOT / path) != digest for path, digest in sources.items()): raise ValueError('probe source changed during run')
        record['source_digest'] = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        record['status'] = 'measurement complete; per-body rejections recorded; no module authorization or execution'
    except Exception as error:
        record['status'] = 'failed'; record['failure'] = str(error); raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'functions': observed['functions'], 'decoded': observed['successful_bodies'], 'source_digest': record['source_digest'], 'max_rss': record['process_max_rss_bytes']}, indent=2))


if __name__ == '__main__': main()
