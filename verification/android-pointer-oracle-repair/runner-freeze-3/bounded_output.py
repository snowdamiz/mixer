"""Shared thread-safe 32MiB runner log budget with a reserved cleanup tail."""
from pathlib import Path
import threading

LIMIT=33554432
RESERVED_CLEANUP=131072
CLEANUP_NAMES={'owned-process-before-stop','stop-only-owned-emulator','owned-process-before-terminate','owned-process-before-kill','port-after-5586','port-after-5587'}

class Budget:
    def __init__(self):
        self.bytes=0;self.overflow=False;self.lock=threading.Lock();self.failures=[]
    def append(self,stream,data,*,cleanup=False):
        with self.lock:
            ceiling=LIMIT if cleanup else LIMIT-RESERVED_CLEANUP
            remaining=max(0,ceiling-self.bytes);kept=data[:remaining];stream.write(kept);stream.flush();self.bytes+=len(kept)
            if len(kept)!=len(data):
                self.overflow=True;self.failures.append({'requestedBytes':len(data),'retainedBytes':len(kept),'cleanup':cleanup})
    def write(self,path,data,*,cleanup=False):
        with Path(path).open('xb') as stream:self.append(stream,data,cleanup=cleanup)
    def report(self):
        with self.lock:return {'limitBytes':LIMIT,'reservedCleanupBytes':RESERVED_CLEANUP,'retainedLogBytes':self.bytes,'overflow':self.overflow,'overflows':list(self.failures)}

class Reader:
    def __init__(self,process,stream,budget):
        self.process=process;self.stream=stream;self.budget=budget;self.failure=None
        self.thread=threading.Thread(target=self.read,name='mixer-owned-emulator-log',daemon=True);self.thread.start()
    def read(self):
        try:
            while True:
                block=self.process.stdout.read(65536)
                if not block:break
                self.budget.append(self.stream,block)
        except BaseException as failure:self.failure=repr(failure)
        finally:self.process.stdout.close()
    def finish(self):
        self.thread.join(5)
        if self.thread.is_alive():raise RuntimeError('owned emulator output reader did not finish')
        if self.failure:raise RuntimeError('owned emulator output reader failed '+self.failure)
