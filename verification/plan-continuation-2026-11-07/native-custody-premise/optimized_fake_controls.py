#!/usr/bin/env python3
"""Second and final pass: same controls, fake children with real bounded pipes.

No process launch, group probe or signal reaches the OS. The normal pass's
unresolved groups and retained scratch are never accessed.
"""
import json
import resource
import os
from pathlib import Path
import runpy
import signal
import sys
import time
from unittest.mock import patch
import cleanup_control as c

OUT=Path(__file__).resolve().parent
children={}


class Child:
    def __init__(self,argv,**kwargs):
        self.pid=90000000+len(children)
        self.returncode=None
        self.start=time.monotonic()
        self.duration=0
        self.code=0
        self.events=[]
        self.writers={}
        for name in ('stdout','stderr'):
            read,write=os.pipe()
            setattr(self,name,os.fdopen(read,'rb',buffering=0))
            self.writers[name]=write
        source=argv[-1]
        if 'os.close(1)' in source:
            self.events=[(0,'stdout',b''),(.2,'stderr',b'err')];self.duration=.2
        elif 'failure-before-timeout' in source:
            self.events=[(0,'stdout',b'failure-before-timeout\n'),(0,'stderr',b'')];self.duration=2
        elif 'motionEffectiveRestored' in source:
            self.events=[(0,'stdout',b'INSTRUMENTATION_RESULT: motionEffectiveRestored=true\nfailure=synthetic\n'),(0,'stderr',b'')];self.code=7
        elif "b'x'*2048" in source:
            self.events=[(0,'stdout',b'x'*2048),(0,'stderr',b'')];self.duration=2
        elif "b'x'*700" in source:
            self.events=[(0,'stdout',b'x'*700),(0,'stderr',b'y'*700)]
        elif "b'a'*400" in source:
            self.events=[(0,'stdout',b'a'*400),(0,'stderr',b'')]
        elif "b'b'*400" in source:
            self.events=[(0,'stdout',b''),(0,'stderr',b'b'*400)];self.duration=2
        elif "b'c'*400" in source:
            self.events=[(0,'stdout',b'c'*400),(0,'stderr',b'')]
        elif "print('ok')" in source:
            self.events=[(0,'stdout',b'ok\n'),(0,'stderr',b'')]
        elif 'time.sleep(' in source:
            self.duration=.2 if 'time.sleep(.2)' in source else 2
        else:
            raise RuntimeError('Unexpected host-only child stimulus: '+source)
        children[self.pid]=self
        self.tick()

    def tick(self):
        if self.returncode is not None:return
        elapsed=time.monotonic()-self.start
        pending=[]
        for at,name,data in self.events:
            if elapsed>=at:
                if data:os.write(self.writers[name],data)
                os.close(self.writers.pop(name))
            else:pending.append((at,name,data))
        self.events=pending
        if elapsed>=self.duration:
            self.returncode=self.code
            self.close_writers()

    def close_writers(self):
        for fd in self.writers.values():os.close(fd)
        self.writers.clear()

    def poll(self):
        self.tick()
        return self.returncode

    def kill(self):
        self.returncode=-9
        self.events=[]
        self.close_writers()


def group(pid,sig):
    if pid not in children:raise AssertionError('unowned fake ID')
    child=children[pid];child.tick()
    if child.returncode is not None:raise ProcessLookupError('synthetic positive absence')
    if sig==signal.SIGKILL:child.kill()
    elif sig!=0:raise AssertionError('unexpected signal')


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(110,115))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(RuntimeError('120s fake suite deadline')))
    signal.alarm(120)
    original_pump=c.Commands.pump
    def pump(manager,seconds=.02):
        for child in children.values():child.tick()
        return original_pump(manager,seconds)
    with patch.object(c.subprocess,'Popen',side_effect=Child),patch.object(c.os,'killpg',side_effect=group),patch.object(c.Commands,'pump',pump),patch.object(c.subprocess,'run',side_effect=RuntimeError('helper launch forbidden')):
        try:runpy.run_path(str(OUT/'host_controls.py'),run_name='__main__')
        except SystemExit as result:code=result.code
    path=OUT/'host-controls-optimized.json'
    receipt=json.loads(path.read_text())
    receipt.update(processMode='FAKE_ONLY_WITH_REAL_PIPES',realProcessLaunches=0,realGroupCalls=0,
                   entryCommand=[sys.executable,'-B','-O',str(Path(__file__).resolve())],
                   scope='26 controls with fake process lifetimes and positive absence; real pipe EOF/output collection. Does not qualify OS custody or supersede the failed normal pass.')
    path.write_text(json.dumps(receipt,indent=2)+'\n')
    sys.exit(code)
