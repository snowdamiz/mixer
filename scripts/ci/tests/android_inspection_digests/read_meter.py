"""Count actual bytes returned by content streams; no timing comparisons."""
import os, pathlib
class Stream:
    def __init__(self, raw, meter, identity):
        self.raw, self.meter, self.identity = raw, meter, identity
    def __enter__(self):
        self.raw.__enter__(); return self
    def __exit__(self,*args): return self.raw.__exit__(*args)
    def __getattr__(self,name): return getattr(self.raw,name)
    def read(self,*args):
        value=self.raw.read(*args)
        self.meter.read_calls+=1
        self.meter.bytes_read+=len(value)
        if value: self.meter.identities_read.add(self.identity)
        if self.meter.after_read is not None: self.meter.after_read(self,value)
        return value
class Meter:
    def __init__(self, after_read=None):
        self.bytes_read=0; self.read_calls=0; self.opens=0
        self.identities_read=set(); self.after_read=after_read
    def wrap(self, raw):
        info=os.fstat(raw.fileno())
        self.opens+=1
        return Stream(raw,self,(info.st_dev,info.st_ino))
    def __enter__(self):
        self.path_open=pathlib.Path.open; self.fdopen=os.fdopen
        meter=self
        def path_open(p,*args,**kwargs):
            raw=meter.path_open(p,*args,**kwargs)
            mode=args[0] if args else kwargs.get('mode','r')
            return meter.wrap(raw) if mode=='rb' else raw
        def fdopen(fd,*args,**kwargs):
            raw=meter.fdopen(fd,*args,**kwargs)
            mode=args[0] if args else kwargs.get('mode','r')
            return meter.wrap(raw) if mode=='rb' else raw
        pathlib.Path.open=path_open; os.fdopen=fdopen
        return self
    def __exit__(self,*args):
        pathlib.Path.open=self.path_open; os.fdopen=self.fdopen
    def result(self):
        return {'contentBytesRead':self.bytes_read,'contentReadCalls':self.read_calls,'targetOpens':self.opens,'uniqueNonemptyPhysicalFilesRead':len(self.identities_read)}
