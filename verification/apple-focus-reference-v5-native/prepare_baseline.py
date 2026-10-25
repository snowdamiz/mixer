#!/usr/bin/env python3
"""Read-only simulator/tool baseline; this cannot create or dispatch a selection."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DEVELOPER = '/Applications/Xcode_26.6.app/Contents/Developer'
FRONTEND = DEVELOPER + '/Applications/Simulator.app/Contents/MacOS/Simulator'


def main():
    output = BASE / 'preparation-baseline'
    output.mkdir()
    commands = {}
    def query(name, argv, frontend_filter=False):
        started = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'DEVELOPER_DIR': DEVELOPER,
                                  'PYTHONDONTWRITEBYTECODE':'1'}, capture_output=True, timeout=30)
        stdout = result.stdout
        if frontend_filter:
            stdout = ('\n'.join(line.strip() for line in stdout.decode().splitlines()
                                if line.strip().endswith(FRONTEND)) + '\n').encode()
        (output / (name + '.stdout')).write_bytes(stdout)
        (output / (name + '.stderr')).write_bytes(result.stderr)
        commands[name] = dict(argv=argv, cwd=str(ROOT), DEVELOPER_DIR=DEVELOPER,
            exitCode=result.returncode, elapsedSeconds=time.monotonic()-started,
            stdoutScope='Pinned Simulator frontend rows only' if frontend_filter else 'complete',
            stdoutSHA256=hashlib.sha256(stdout).hexdigest(), stderrSHA256=hashlib.sha256(result.stderr).hexdigest())
        assert result.returncode == 0, name + ' failed'
        return stdout.decode().strip()
    devices=json.loads(query('devices',['/usr/bin/xcrun','simctl','list','devices','--json']))
    runtimes=json.loads(query('runtimes',['/usr/bin/xcrun','simctl','list','runtimes','--json']))
    frontends=query('frontends',['/bin/ps','-axo','pid=,lstart=,comm='],True).splitlines()
    xcode=query('xcode-version',[DEVELOPER+'/usr/bin/xcodebuild','-version'])
    swift=query('swift-version',[DEVELOPER+'/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc','--version'])
    python=query('python-version',[sys.executable,'--version'])
    simctl=query('simctl-path',['/usr/bin/xcrun','--find','simctl'])
    xcresulttool=query('xcresulttool-path',['/usr/bin/xcrun','--find','xcresulttool'])
    result_version=query('xcresulttool-version',['/usr/bin/xcrun','xcresulttool','version'])
    system=query('system-version',['/usr/bin/sw_vers'])
    architecture=query('architecture',['/usr/bin/uname','-m'])
    tools={}
    for value in ['/usr/bin/xcrun',simctl,xcresulttool,DEVELOPER+'/usr/bin/xcodebuild',
                  DEVELOPER+'/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc',sys.executable]:
        path=Path(value)
        raw=path.read_bytes()
        tools[value]=dict(resolvedPath=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    selected=next(row for row in runtimes['runtimes'] if row['identifier']=='com.apple.CoreSimulator.SimRuntime.iOS-26-5')
    receipt=dict(schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        command=[sys.executable,'-B',str(Path(__file__).resolve())],scriptSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Read-only current tools/simulator inventory; advisory, root refreshes before creation/selection',
        sourceRevisionLabel='7744c1cc28b24a46f4339b25b38ce4d0cf76cbe8',sourceRevisionMeaning='Existing root decision label; no Git query',
        sourceTreeSHA256='696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a',
        selectedRuntime={k:selected[k] for k in ['identifier','version','buildversion','isAvailable','supportedArchitectures']},
        baselineDevices=devices,baselineFrontends=frontends,commands=commands,tools=tools,
        versions=dict(xcode=xcode,swift=swift,python=python,xcresulttool=result_version,system=system,architecture=architecture),
        nativeSelected=False,nativeExecuted=False,simulatorCreated=False,physicalPhones='disconnected-deferred')
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(observedUTC=receipt['observedUTC'],selectedRuntime=receipt['selectedRuntime'],
        versions=receipt['versions'],baselineFrontends=frontends,devices=[dict(udid=row['udid'],name=row['name'],state=row['state']) for rows in devices['devices'].values() for row in rows]),indent=2))


if __name__ == '__main__':
    main()
