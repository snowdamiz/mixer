"""Bounded stable observation reads plus explicit deadline propagation.

Only a demonstrably superseded regular inode is retried. No unlinked inode,
symlink, hardlink, unstable in-place content or malformed payload is accepted.
"""
import hashlib
import json
import math
import os
import pathlib
import stat
import time

MAX_OBSERVATION=16_000_000
MAX_ATTEMPTS=4
DIRECT_BUDGET_SECONDS=.050

def require(ok,reason):
    if not ok:raise ValueError(reason)

def identity(info):return (info.st_dev,info.st_ino)
def metadata(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,
            info.st_mtime_ns,info.st_ctime_ns,info.st_uid,info.st_gid)

def regular_shape(info,allow_unlinked=False):
    require(stat.S_ISREG(info.st_mode),'Observation must be a regular file')
    require(info.st_nlink in ((0,1) if allow_unlinked else (1,)),'Observation must have exactly one link')
    require(0<info.st_size<=MAX_OBSERVATION,'Observation size outside fixed bound')

def stable_info(fd,path,initial):
    require(path.parent.resolve()==path.parent and path.resolve()==path,'Observation canonical parent/path redirected during read')
    current=os.fstat(fd);regular_shape(current,allow_unlinked=True)
    require(identity(current)==identity(initial),'Descriptor identity changed')
    try:named=os.lstat(path)
    except FileNotFoundError:
        # The opened regular inode has lost the canonical name. Its bytes are
        # rejected; reopening may find a later immutable atomic snapshot.
        raise FileNotFoundError('Observation canonical name was atomically removed') from None
    regular_shape(named)
    if identity(named)!=identity(current):
        raise FileNotFoundError('Observation inode was atomically superseded')
    require(current.st_nlink==1,'Unlinked descriptor has no corresponding stable path')
    require(metadata(current)==metadata(initial)==metadata(named),'Observation metadata changed in place')
    return current

def read_payload(fd):
    chunks=[];remaining=MAX_OBSERVATION+1
    while remaining:
        chunk=os.read(fd,min(65536,remaining))
        if not chunk:break
        chunks.append(chunk);remaining-=len(chunk)
    return b''.join(chunks)

def read_once(documents):
    require(type(documents) is pathlib.PosixPath,'Canonical fixed Documents path required')
    path=documents/'observations.json'
    require(documents.is_dir() and documents.resolve()==documents and path.resolve()==path,'Observation path redirected')
    flags=os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_CLOEXEC',0)
    fd=os.open(path,flags)
    try:
        initial=os.fstat(fd);regular_shape(initial,allow_unlinked=True)
        stable_info(fd,path,initial)
        payload=read_payload(fd)
        require(len(payload)<=MAX_OBSERVATION and len(payload)==initial.st_size,'Observation payload length changed or exceeded bound')
        stable_info(fd,path,initial)
        def pairs(entries):
            require(len(dict(entries))==len(entries),'Duplicate observation JSON key')
            return dict(entries)
        value=json.loads(payload,object_pairs_hook=pairs,
                         parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite observation JSON number')))
        require(type(value) is dict and type(value.get('state')) is dict and type(value.get('events')) is list and bool(value['events']),'Malformed observation object')
        state=value['state']
        require(type(state.get('identity')) is str and bool(state['identity']) and all(type(state.get(k)) is bool for k in ('isOn','retainedOn','enabled','allowed')),'Malformed native observation state')
        final=stable_info(fd,path,initial)
        signature=[final.st_ino,final.st_mtime_ns,len(payload),hashlib.sha256(payload).hexdigest()]
        return value,signature
    finally:os.close(fd)

def read_observation(documents,*,deadline,max_attempts=MAX_ATTEMPTS,clock=None):
    clock=time.monotonic if clock is None else clock
    require(type(deadline) in (int,float) and math.isfinite(deadline),'Finite absolute observation deadline required')
    require(type(max_attempts) is int and 1<=max_attempts<=MAX_ATTEMPTS,'Fixed observation attempt cap required')
    last=None
    for _ in range(max_attempts):
        if clock()>=deadline:raise FileNotFoundError('Existing observation deadline expired')
        try:
            result=read_once(documents)
        except FileNotFoundError as error:last=error;continue
        if clock()>=deadline:raise FileNotFoundError('Observation completed after existing deadline')
        return result
    raise FileNotFoundError('Fixed atomic observation attempt cap exhausted') from last

def deadline_bridge(base):
    class DeadlineBridge(base):
        """Only observation/deadline adapters; inherited wait/request logic remains unchanged."""
        def observe(self):
            effective=getattr(self,'_observation_read_deadline',None)
            if effective is None:effective=min(self.deadline,time.monotonic()+DIRECT_BUDGET_SECONDS)
            observed=read_observation(self.documents[self.current['candidate']],deadline=effective,max_attempts=MAX_ATTEMPTS)
            self.last_observation={'observation':observed[0],'signature':observed[1]}
            return observed
        def wait(self,predicate,seconds=6):
            prior=getattr(self,'_observation_read_deadline',None)
            effective=min(self.deadline,time.monotonic()+seconds)
            if prior is not None:effective=min(effective,prior)
            self._observation_read_deadline=effective
            try:return super().wait(predicate,seconds)
            finally:
                if prior is None:del self._observation_read_deadline
                else:self._observation_read_deadline=prior
    return DeadlineBridge
