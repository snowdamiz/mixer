from pathlib import Path
import json, os, subprocess, sys, time

p = Path(__file__).parent
c = json.loads((p / 'selection.json').read_text())
owned = Path(c['ownedScratch'])
mode = sys.argv[1]
assert mode in c['modes'] and not (p / (mode + '-fixtures-result.json')).exists()
env = os.environ.copy()
env.update(DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',
    SDKROOT='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk',
    TMPDIR=str(owned / (mode + '-tmp')) + '/', CLANG_MODULE_CACHE_PATH=str(owned / ('modules-' + mode)))
argv = ['/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift',
    'test', '--skip-build', '--package-path', c['package'], '--scratch-path', str(owned / ('build-' + mode)),
    '--cache-path', str(owned / ('cache-' + mode)), '--config-path', str(owned / ('config-' + mode)),
    '--security-path', str(owned / ('security-' + mode)), '--disable-sandbox', '-c', mode, '-j', '2']
started = time.monotonic()
with (p / (mode + '-fixtures.log')).open('wb') as log:
    process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    row = {'argv': argv, 'pid': process.pid, 'pgid': process.pid, 'sourceTreeSHA256': c['sourceTreeSHA256']}
    (p / (mode + '-fixtures-command.json')).write_text(json.dumps(row, indent=2) + '\n')
    try:
        code = process.wait(timeout=240)
    except subprocess.TimeoutExpired:
        row.update(state='UNKNOWN', reason='SDK test outer deadline; preserve this exact run without retry or cleanup')
        (p / (mode + '-fixtures-HOLD.json')).write_text(json.dumps(row, indent=2) + '\n')
        raise SystemExit(74)
try:
    os.killpg(process.pid, 0)
    absent = False
except ProcessLookupError:
    absent = True
row.update(exitCode=code, groupAbsent=absent, seconds=time.monotonic() - started)
(p / (mode + '-fixtures-result.json')).write_text(json.dumps(row, indent=2) + '\n')
print(json.dumps({k: v for k, v in row.items() if k != 'argv'}))
