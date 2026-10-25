"""Review-only guard installed before an unchanged host composition probe."""
import os
from pathlib import Path
import sys

owned=Path(os.environ['MIXER_REVIEW_OWNED']).resolve()
def review_audit(event,args):
    if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise AssertionError('Independent child review guard forbids '+event)
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=os.fsdecode(args[0])
        if any(word in path.lower() for word in ('hosted','catalog','authority-driver','worker-transport')):
            raise AssertionError('Excluded lane read: '+path)
        flags=args[2] if len(args)>2 else 0
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):
            assert Path(path).resolve().is_relative_to(owned),path
sys.addaudithook(review_audit)
