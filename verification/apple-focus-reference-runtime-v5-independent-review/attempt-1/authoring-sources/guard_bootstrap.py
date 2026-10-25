"""Independent guard installed before any producer module is loaded."""
import json
import os
from pathlib import Path
import runpy
import sys

ROOT=Path(os.environ['MIXER_V5_CLOSED_ROOT']).resolve()
PYTHON=Path(sys.base_prefix).resolve()
DENIED=[]

def audit(event,args):
    if event in ('os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise AssertionError('Independent host boundary forbids '+event)
    if event=='subprocess.Popen':
        executable,argv=args[:2]
        assert Path(executable).resolve()==Path(sys.executable).resolve()
        assert argv[1:3]==['-B','-c'] and len(argv)==5
    if event in ('open','os.scandir','os.listdir') and args and isinstance(args[0],(str,bytes)):
        path=Path(os.fsdecode(args[0])).resolve()
        if any(word in str(path).lower() for word in ('hosted','catalog','authority-driver','worker-transport')):
            raise AssertionError('Excluded lane '+str(path))
        if not (path.is_relative_to(ROOT) or path.is_relative_to(PYTHON) or str(path)=='/dev/null'):
            DENIED.append({'event':event,'path':str(path)})
            raise PermissionError('Independent closed-root read denied: '+str(path))

sys.dont_write_bytecode=True
sys.addaudithook(audit)
target=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(ROOT/'verification/apple-focus-reference-runtime-v5'))
sys.path.insert(0,str(target.parent))
sys.argv=sys.argv[1:]
runpy.run_path(str(target),run_name='__main__',init_globals={'INDEPENDENT_DENIED':DENIED})
