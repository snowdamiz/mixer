"""Installed before each hash-pinned, native-disabled host composition import."""
import os
from pathlib import Path
import sys

root=Path(os.environ['MIXER_V5_CLOSED_ROOT']).resolve()
base=root/'verification/apple-focus-reference-runtime-v5'
runtime=Path(sys.base_prefix).resolve()
def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise AssertionError('Closed V5 child forbids '+event)
    if event in ('os.scandir','os.listdir') and args and isinstance(args[0],(str,bytes)):
        path=Path(os.fsdecode(args[0])).resolve()
        assert path.is_relative_to(root) or path.is_relative_to(runtime),path
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=Path(os.fsdecode(args[0])).resolve()
        assert not any(w in str(path).lower() for w in ('hosted','catalog','authority-driver','worker-transport')),path
        flags=args[2] if len(args)>2 else 0
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):assert path.is_relative_to(base),path
        else:assert path.is_relative_to(root) or path.is_relative_to(runtime) or str(path)=='/dev/null',path
sys.dont_write_bytecode=True
sys.addaudithook(audit)
