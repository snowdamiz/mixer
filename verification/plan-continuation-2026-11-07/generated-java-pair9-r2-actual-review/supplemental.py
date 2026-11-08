#!/usr/bin/env python3
"""Pure-data exact command and source binding supplement. Writes only beside itself."""
import importlib.util
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('audit_helpers', OUT / 'audit.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
js, ident, check = a.js, a.ident, a.check
r = js(a.RUN / 'receipt.json')
s = js(a.ACTUAL / 'selection.json')
p = js(a.ACTUAL / 'result.json')
main = js(OUT / 'audit.json')
c = js(a.RUN / 'commands/commands.json')
by = {v['label']: v for v in c}
t = r['official_toolchain']
scratch = Path(r['cleanup']['owned_scratch_path'])
expected = {}
expected['revision'] = ['git', 'rev-parse', 'HEAD']
expected['git-tree'] = ['git', 'rev-parse', 'HEAD^{tree}']
python = '/opt/homebrew/opt/python@3.14/bin/python3.14'
check(str(Path(python).resolve()) == t['tools']['python']['path'] and ident(python)['sha256'] == t['tools']['python']['sha256'], 'Exact Python launcher resolves to hash-bound inspected executable')
for label in ['official-inspect', 'official-inspect-postflight']:
    expected[label] = [python, '-B', str(a.ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py'), 'inspect']
expected['d8-version'] = [t['tools']['d8']['path'], '--version']
for label in ['javap-version', 'javap-version-postflight']:
    expected[label] = [r['javap_tool']['path'], '-version']
for mode in ['debug', 'release']:
    build = scratch / ('producer-' + mode)
    flags = [r['selected_paths']['swift'], 'build', '--package-path', str(a.ROOT / 'cli'), '--scratch-path', str(build), '--disable-automatic-resolution', '-j', '2', '-c', mode]
    expected[mode + '-producer-build'] = flags + ['--product', 'mixer']
    expected[mode + '-producer-bin'] = flags + ['--show-bin-path']
    cli = str((Path(Path(by[mode + '-producer-bin']['logs']['stdout']['path']).read_text().strip()) / 'mixer').resolve())
    for phase in ['dependency', 'post-dependency']:
        for name in ['swift-asn1', 'swift-crypto']:
            prefix = mode + '-' + phase + '-' + name
            git = ['git', '-C', str(build / 'checkouts' / name)]
            expected[prefix + '-revision'] = git + ['rev-parse', 'HEAD']
            expected[prefix + '-status'] = git + ['status', '--porcelain', '--untracked-files=all']
    original = str(scratch / mode / 'original')
    expected[mode + '-create'] = [cli, 'create', 'GeneratedJavaApp', '--platform', 'android', '--directory', original, '--application', 'dev.mixer.generatedjava', '--sdk-path', str(a.ROOT / 'sdk'), '--android-adapter-path', str(a.ROOT / 'native/android')]
    expected[mode + '-export'] = [cli, 'export', str(scratch / mode / 'exported'), '--directory', original]
    for form in ['original', 'relocated', 'exported']:
        label = mode + '-' + form
        dest = a.RUN / label
        rec = js(dest / 'receipt.json')
        jar = t['distributions']['android_platform']['path'] + '/android.jar'
        sources = [str(scratch / mode / form / v) for v in sorted(rec['sources'])]
        classes = [str(dest / 'classes' / v) for v in sorted(rec['classes'])]
        expected[label + '-javac'] = [t['tools']['javac']['path'], '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-sourcepath', '', '-classpath', jar, '-d', str(dest / 'classes')] + sources
        expected[label + '-javap-members'] = [r['javap_tool']['path'], '-v', '-p', '-c', '-s'] + classes
        expected[label + '-d8'] = [t['tools']['d8']['path'], '--min-api', '28', '--lib', jar, '--output', str(dest / 'dex')] + classes
        expected[label + '-dexdump'] = [t['tools']['dexdump']['path'], str(dest / 'dex/classes.dex')]
        inv = js(dest / 'consumer-inventory.json')
        dirs = js(dest / 'consumer-directories.json')
        required_dirs = {str(parent) for path in inv for parent in Path(path).parents if str(parent) != '.'}
        permitted_empty = {'Resources'} if form != 'exported' else set()
        check(set(dirs) == required_dirs | permitted_empty, label + ': exact directory topology with source-defined empty Resources only in original/relocated')
    for case in ['sdk', 'adapter', 'descriptor', 'extra-java', 'profile', 'missing-lock']:
        root = scratch / mode / 'tamper' / case
        expected[mode + '-tamper-' + case] = [cli, 'build', '--platform', 'android', '--directory', str(root)]
        expected[mode + '-driver-tamper-' + case] = [python, '-B', str(root / 'Generated/MixerAndroid/android-build.py'), 'build', str(root)]
check(set(expected) == set(by) and len(expected) == 79, 'All 79 commands covered by independently constructed exact argv map')
for label, argv in expected.items():
    check(by[label]['argv'] == argv, label + ': complete exact argv, no additional flags or substitute executable')
check(p['consumers'] == r['consumers'] and p['tamper'] == r['tamper'] and p['cleanup'] == r['cleanup'], 'All parent summarized consumers, negatives and cleanup equal raw receipt')
check(p['commands'] == len(c) and p['allCommandCustodyTerminal'] and all(x['terminal_custody'] for x in c), 'Parent count/custody summary equal raw ledger')
check(sum('-tamper-' in x['label'] for x in c) == 24 and sum(len(v) for v in r['tamper'].values()) == 12, '12 case/mode combinations each refused by CLI and copied driver: 24 negative invocations')
check(ident(a.ROOT / 'verification/plan-continuation-2026-11-07/android-motion-thread-fix-r2/result.json')['sha256'] == s['candidateResultSHA256'], 'Frozen candidate result matches selection hash; no semantic verdict inferred')
check(js(a.ROOT / 'verification/plan-continuation-2026-11-07/android-motion-thread-fix-r2/final-source-map.json') == js(a.ACTUAL / 'implementation-source-map.json'), 'Parent implementation map equals frozen R2 final map')
check(all(v['outcome'] == 'absent' for v in (x['group_observation'] for x in c)) and all(x['stdout_eof'] and x['stderr_eof'] for x in c), 'EOF and positively observed group absence are distinct records for every command')
check(all(x['signal']['outcome'] == 'already-absent' for x in c), 'All recorded owned-group cleanup signals found groups already absent')
check(not scratch.exists(), 'Owned scratch remains absent; no resurrection')
check({path: ident(a.ROOT / path) for path in r['source_inputs']} == r['source_inputs'], 'Final frozen candidate postflight unchanged')
check(a.inventory(a.RUN) == main['facts']['original_artifact_inventory'], 'Raw artifact postflight unchanged since first audit')
# Read Git refs as filesystem data, without a git subprocess or process probes.
def head(root):
    pointer = (root / '.git').read_text().strip()
    gd = Path(pointer.removeprefix('gitdir: '))
    if not gd.is_absolute(): gd = (root / gd).resolve()
    value = (gd / 'HEAD').read_text().strip()
    common = (gd / (gd / 'commondir').read_text().strip()).resolve() if (gd / 'commondir').exists() else gd
    if not value.startswith('ref: '): return value
    ref = value[5:]
    for base in [gd, common]:
        target = base / ref
        if target.exists(): return target.read_text().strip()
    for line in (common / 'packed-refs').read_text().splitlines():
        if line.endswith(' ' + ref): return line.split()[0]
    raise RuntimeError('Cannot resolve HEAD')
parent_head = head(a.PARENT)
check(parent_head == '25ac442c5213326b3601456a5fd62898f152111f', 'Parent delivery HEAD matches brief; not evidence of R2 integration')
check(head(a.ROOT) == r['revision'], 'Candidate base HEAD remains frozen')
parent_source_differences = [path for path, value in r['source_inputs'].items() if ident(a.PARENT / path) != value]
report = dict(schema=1, verdict='ACCEPT', observed_utc=datetime.now(timezone.utc).isoformat(),
              command=[sys.executable, '-B', str(Path(__file__).resolve())], script=ident(__file__),
              checks=a.CHECKS, source_inputs_sha256=r['source_inputs_sha256'], parent_head=parent_head,
              candidate_base=r['revision'], parent_source_differences=parent_source_differences,
              audit=ident(OUT / 'audit.json'), reviewer_process_probes=0, reviewer_product_executions=0)
(OUT / 'supplemental.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(verdict='ACCEPT', checks=len(a.CHECKS), parent_source_differences=parent_source_differences)))
