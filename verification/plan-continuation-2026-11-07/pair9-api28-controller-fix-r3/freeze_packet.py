"""Rebind only lane-owned source paths; preserve every external R1 binding."""
from pathlib import Path
import run_api28 as r

def main():
    original = r.BASE / 'pair9-api28-controller'
    frozen = r.load(original / 'controller-packet.json')
    r.require(len(frozen['bindings']) == 1168, 'R1 binding inventory changed')
    for name in ('run_api28.py', 'cleanup_control.py', 'host_controls.py', 'freeze_packet.py'):
        frozen['bindings'].pop(str(original / name))
        path = r.HERE / name
        frozen['bindings'][str(path)] = {**r.identity(path), 'realPath': str(path.resolve())}
    path = r.HERE / 'server_fd_exec.py'
    frozen['bindings'][str(path)] = {**r.identity(path), 'realPath': str(path.resolve())}
    frozen['controllerSHA256'] = r.identity(r.HERE / 'run_api28.py')['sha256']
    frozen['r2Transport'] = {'numericClientHost': '127.0.0.1', 'serverListener': 'parent retained; SCM_RIGHTS; official acceptfd',
                             'sameServerClientSHA256': r.ADB_SHA, 'reviewRequired': True,
                             'emulatorDescendantSocket': 'tcp:127.0.0.1:<owned-port>',
                             'emulatorDescendantAddress': '127.0.0.1'}
    r.require(r.identity(r.HERE / 'cleanup_control.py')['sha256'] == r.LIFECYCLE_SHA, 'lifecycle changed')
    r.verify_bindings(frozen)
    r.save(r.HERE / 'controller-packet.json', frozen)
    print('1164 external bindings unchanged; 4 owned paths rebound; 1 descriptor helper added; total 1169')

if __name__ == '__main__': main()
