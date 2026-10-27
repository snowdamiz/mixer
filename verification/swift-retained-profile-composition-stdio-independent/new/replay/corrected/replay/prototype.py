"""Finite retained-descriptor composition prototype for quiescent fixtures only.

No authentic Rust owner export, source/build admission or real context is wired.
All eight claims are derived from separate retained file descriptors. This API
has no field capable of granting semantic, release, runtime or GA authority.
"""
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile

CHUNK = 4096
ATTEMPTS = 32
BODY = 2560000
PROFILE = BODY + 512
NAMES = ("baseline", "candidate", "original_input", "event_schema", "profile_adapter_binary", "layout_receipt", "original_validated_snapshot", "profile_row_body")
CAPS = (131072, 131072, 67108864, 65536, 67108864, 262144, 16777216, BODY)
SCOPE = "trusted-quiescent-fixture-v1"
STDIO_OWNERS = {}
STDIO_TOKENS = {}
STDIO_UNCERTAIN_CLOSES = {}
STDIO_PATHS = {}
QUARANTINES = []
MAX_OWNERS = 9
MAX_FDS_PER_OWNER = 65
OWNERS = {}
TOKENS = {}
UNCERTAIN_CLOSES = {}
_NEXT_GENERATION = 0


class Refusal(Exception):
    def __init__(self, code, stage, progress=None):
        self.code, self.stage = code, stage
        self.progress = asdict(progress) if progress is not None else None
        super().__init__(code + ":" + stage)


@dataclass
class IOCount:
    read_calls: int = 0
    write_calls: int = 0
    read_requested: int = 0
    write_requested: int = 0
    read_acknowledged: int = 0
    write_acknowledged: int = 0


def _generation():
    global _NEXT_GENERATION
    if _NEXT_GENERATION == (1 << 64) - 1:
        raise Refusal("generation-exhausted", "ownership")
    _NEXT_GENERATION += 1
    return _NEXT_GENERATION


@dataclass
class _Descriptor:
    generation: int
    owner_generation: int
    number: int
    state: str = "owned"


@dataclass(frozen=True)
class CloseFault:
    token_generation: int
    owner_generation: int
    saved_number: int  # Observation only; this record has no close capability.
    exception: BaseException
    resource_kind: str = "retained"


@dataclass(frozen=True)
class CleanupReport:
    owner_generation: int
    terminal_state: str
    attempted_generations: tuple
    closed_generations: tuple
    uncertain_generations: tuple
    failures: tuple


class CleanupFailure(OSError):
    def __init__(self, report):
        self.report = report
        self.failures = report.failures
        super().__init__("retained close uncertainty; no numeric retry permitted")


class CleanupAggregate(Refusal):
    """Retain the original failure/result and every cleanup error in order."""
    def __init__(self, primary, cleanup_errors, retained_result=None):
        if isinstance(primary, CleanupAggregate):
            retained_result = primary.retained_result if retained_result is None else retained_result
            cleanup_errors = primary.cleanup_errors + tuple(cleanup_errors)
            primary = primary.primary
        self.primary = primary
        self.cleanup_errors = tuple(cleanup_errors)
        self.retained_result = retained_result
        super().__init__(getattr(primary, "code", "cleanup-failed"), getattr(primary, "stage", "cleanup"))


class _NumberObservations:
    """Read-only accounting view, never an authority to operate on numbers."""
    def __init__(self, tokens=None): self._tokens = tokens or (lambda:TOKENS)
    def _numbers(self):
        return {token.number for token in self._tokens().values() if token.number is not None}
    def __iter__(self): return iter(tuple(sorted(self._numbers())))
    def __len__(self): return len(self._numbers())
    def __bool__(self): return bool(self._tokens())
    def __contains__(self, number): return number in self._numbers()
    def __eq__(self, other): return self._numbers() == other
    def __repr__(self): return repr(self._numbers())
    def remove(self, _): raise Refusal("accounting-view-read-only", "ownership")
    discard = remove
    def clear(self): raise Refusal("accounting-view-read-only", "ownership")


OPEN_FDS = _NumberObservations()
STDIO_FDS = _NumberObservations(lambda:STDIO_TOKENS)


def ownership_snapshot():
    states = {name: sum(t.state == name for t in TOKENS.values()) for name in ("owned", "closing", "uncertain")}
    stdio_states = {name:sum(t.state == name for t in STDIO_TOKENS.values()) for name in ("acquiring","owned","closing","uncertain")}
    return {"owners": len(OWNERS), "token_states": states, "uncertain_close_records": len(UNCERTAIN_CLOSES), "leased_child_quarantines": len(QUARANTINES), "stdio_contexts": len(STDIO_FDS), "stdio_owners":len(STDIO_OWNERS),"stdio_token_states":stdio_states,"stdio_uncertain_close_records":len(STDIO_UNCERTAIN_CLOSES),"stdio_path_obligations":len(STDIO_PATHS),"healthy_zero": not (OWNERS or TOKENS or UNCERTAIN_CLOSES or QUARANTINES or STDIO_OWNERS or STDIO_TOKENS or STDIO_UNCERTAIN_CLOSES or STDIO_PATHS)}


class _DescriptorAccess:
    """A generation-bound wrapper borrow; numeric equality is observation only."""
    def __init__(self, owner, token):
        self._owner, self._token = owner, token
    @property
    def saved_number(self): return self._token.number
    def __index__(self):
        self._owner.idle()
        if self._owner._leaf is not self._token or TOKENS.get(self._token.generation) is not self._token:
            raise Refusal("stale-descriptor-borrow", "ownership")
        return self._token.number
    def __int__(self): return self.__index__()
    def __str__(self): return str(self._token.number)
    def __repr__(self): return f"DescriptorObservation(owner={self._owner.generation},number={self.saved_number})"
    def __hash__(self): return hash(self._token.number)
    def __eq__(self, other):
        return self.saved_number == (other.saved_number if isinstance(other, _DescriptorAccess) else other)


def _open(*args, owner, **kwargs):
    if owner.state != "opening" or OWNERS.get(owner.generation) is not owner or len(owner._tokens) >= MAX_FDS_PER_OWNER or UNCERTAIN_CLOSES or STDIO_UNCERTAIN_CLOSES or STDIO_PATHS or QUARANTINES:
        raise Refusal("open-ownership", "ownership")
    generation = _generation()
    fd = os.open(*args, **kwargs)
    token = _Descriptor(generation, owner.generation, fd)
    owner._tokens.append(token)
    TOKENS[generation] = token
    return fd


def _close(token, owner):
    if owner.state != "closing" or token.state != "owned" or token.owner_generation != owner.generation or TOKENS.get(token.generation) is not token:
        raise Refusal("close-ownership", "ownership")
    token.state = "closing"  # Consume close capability BEFORE the sole syscall.
    try:
        os.close(token.number)
    except BaseException as error:
        token.state = "uncertain"
        fault = CloseFault(token.generation, owner.generation, token.number, error)
        UNCERTAIN_CLOSES[token.generation] = fault
        return fault
    token.state = "closed"
    del TOKENS[token.generation]
    return None


def identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_nlink)


class Retained:
    def __init__(self, path, size, output=False):
        self.path, self.size = str(path), size
        self.fds, self.links, self.fd = [], [], None
        self._tokens, self._leaf, self._lease = [], None, None
        self._report = None
        self.state = "new"
        if len(OWNERS) >= MAX_OWNERS or UNCERTAIN_CLOSES or STDIO_UNCERTAIN_CLOSES or STDIO_PATHS or QUARANTINES:
            raise Refusal("owner-admission-quarantined-or-full", "ownership")
        self.generation = _generation()
        self.state = "opening"
        OWNERS[self.generation] = self
        try:
            if not os.path.isabs(self.path) or len(self.path) > 4096:
                raise Refusal("path", "open")
            parts = self.path[1:].split("/")
            if not 1 <= len(parts) <= 64 or any(not x or x in (".", "..") or len(x.encode()) > 255 for x in parts):
                raise Refusal("path", "open")
            parent = _open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, owner=self)
            self.fds.append(parent)
            for part in parts[:-1]:
                child = _open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent, owner=self)
                self.fds.append(child)
                self.links.append((parent, part, child))
                parent = child
            flags = os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_RDWR | os.O_CREAT | os.O_EXCL if output else os.O_RDONLY)
            leaf = _open(parts[-1], flags, 0o600, dir_fd=parent, owner=self)
            self.fds.append(leaf)
            self.links.append((parent, parts[-1], leaf))
            self._leaf = self._tokens[-1]
            st = os.fstat(leaf)
            if not stat.S_ISREG(st.st_mode) or st.st_size != (0 if output else size) or st.st_nlink != 1:
                raise Refusal("regular-length-links", "open")
            if os.lseek(leaf, 0, os.SEEK_CUR) != 0:
                raise Refusal("offset", "open")
            self.initial = identity(st)
            self.fd = _DescriptorAccess(self, self._leaf)
            self.state = "open"
            self.check(output=output)
        except BaseException as primary:
            try:
                self.close()
            except BaseException as cleanup:
                raise CleanupAggregate(primary, (cleanup,)) from primary
            raise

    @property
    def live(self): return self._lease is not None

    def __enter__(self):
        self.idle()
        return self

    def __exit__(self, _kind, primary, _traceback):
        try:
            self.close()
        except BaseException as cleanup:
            if primary is not None:
                raise CleanupAggregate(primary, (cleanup,)) from primary
            raise

    def close(self):
        if self.state == "closed":
            return self._report
        if self.state == "quarantined":
            raise CleanupFailure(self._report)
        if self.state not in ("open", "opening"):
            raise Refusal("close-not-open", "close")
        if self.live:
            raise Refusal("child-live", "close")
        self.state = "closing"  # All access and child handoff now refuse.
        self.links.clear()
        attempted, closed, uncertain, failures = [], [], [], []
        for token in reversed(self._tokens):
            attempted.append(token.generation)
            try:
                fault = _close(token, self)
            except BaseException as error:
                # A local close-boundary refusal is also terminal uncertainty:
                # no raw-number retry, and other independent tokens still run.
                token.state = "uncertain"
                fault = CloseFault(token.generation, self.generation, token.number, error)
                UNCERTAIN_CLOSES[token.generation] = fault
            if fault is None:
                closed.append(token.generation)
            else:
                uncertain.append(token.generation)
                failures.append(fault)
        self.fds.clear()
        self.state = "quarantined" if failures else "closed"
        if not failures:
            del OWNERS[self.generation]
        self._report = CleanupReport(self.generation, self.state, tuple(attempted), tuple(closed), tuple(uncertain), tuple(failures))
        if failures:
            raise CleanupFailure(self._report)
        return self._report

    def idle(self):
        if self.state != "open" or OWNERS.get(self.generation) is not self:
            raise Refusal("owner-not-open", "parent-access")
        if not self._tokens or any(token.state != "owned" or TOKENS.get(token.generation) is not token or token.owner_generation != self.generation for token in self._tokens):
            raise Refusal("stale-owner-generation", "parent-access")
        if self.live:
            raise Refusal("shared-OFD-live", "parent-access")

    def seek(self, offset, whence=os.SEEK_SET):
        self.idle()
        return os.lseek(self.fd, offset, whence)

    def readinto(self, view):
        self.idle()
        return os.readv(self.fd, [view])

    def check(self, output=False):
        self.idle()
        for parent, name, fd in self.links:
            now = os.stat(name, dir_fd=parent, follow_symlinks=False)
            held = os.fstat(fd)
            if (now.st_dev, now.st_ino, now.st_mode) != (held.st_dev, held.st_ino, held.st_mode):
                raise Refusal("path-identity", "custody")
        held = os.fstat(self.fd)
        if not stat.S_ISREG(held.st_mode) or held.st_nlink != 1:
            raise Refusal("regular-links", "custody")
        if not output and identity(held) != self.initial:
            raise Refusal("metadata-drift", "custody")


class CleanupFrame:
    """A bounded set of independent owners, all attempted even after errors."""
    def __init__(self):
        self.owners, self.result = [], None
    def __enter__(self): return self
    def adopt(self, owner):
        if len(self.owners) >= MAX_OWNERS or any(x is owner for x in self.owners):
            raise Refusal("cleanup-frame-cap", "ownership")
        owner.idle()
        self.owners.append(owner)
        return owner
    def __exit__(self, _kind, primary, _traceback):
        errors = []
        for owner in reversed(self.owners):
            try:
                owner.close()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise CleanupAggregate(primary, errors, self.result) from primary


class IO:
    """One source-level os.readv/write invocation per call; internals excluded."""
    def read(self, fd, view):
        if not isinstance(fd, _DescriptorAccess):
            raise Refusal("owned-access-required", "read")
        return os.readv(fd, [view])

    def write(self, fd, view):
        if not isinstance(fd, _DescriptorAccess):
            raise Refusal("owned-access-required", "write")
        return os.write(fd, view)


def transfer(io, fd, view, counts, writing):
    position = 0
    for _ in range(ATTEMPTS):
        request = len(view) - position
        if request == 0:
            return
        if writing:
            counts.write_calls += 1
            counts.write_requested += request
        else:
            counts.read_calls += 1
            counts.read_requested += request
        try:
            n = (io.write if writing else io.read)(fd, view[position:])
        except InterruptedError:
            continue
        except OSError as e:
            raise Refusal("io-error", "write" if writing else "read", counts) from e
        if type(n) is not int or n <= 0 or n > request:
            raise Refusal("zero-or-overreport", "write" if writing else "read", counts)
        position += n
        if writing:
            counts.write_acknowledged += n
        else:
            counts.read_acknowledged += n
        if position == len(view):
            return
    raise Refusal("attempt-exhaustion", "write" if writing else "read", counts)


def eof(io, fd, buffer, counts):
    for _ in range(ATTEMPTS):
        counts.read_calls += 1
        counts.read_requested += 1
        try:
            n = io.read(fd, memoryview(buffer)[:1])
        except InterruptedError:
            continue
        except OSError as e:
            raise Refusal("io-error", "EOF", counts) from e
        if type(n) is int and 0 < n <= 1:
            counts.read_acknowledged += n
        if type(n) is not int or n != 0:
            raise Refusal("extra-or-overreport", "EOF", counts)
        return
    raise Refusal("attempt-exhaustion", "EOF", counts)


def hash_range(held, buffer, counts, io, offset=0, length=None, exact_eof=True):
    held.idle()
    length = held.size if length is None else length
    if offset < 0 or length < 0 or offset + length > held.size:
        raise Refusal("range", "hash")
    held.check()
    os.lseek(held.fd, offset, os.SEEK_SET)
    h = hashlib.sha256()
    for start in range(0, length, CHUNK):
        v = memoryview(buffer)[:min(CHUNK, length - start)]
        transfer(io, held.fd, v, counts, False)
        h.update(v)
    if exact_eof:
        if offset + length != held.size:
            raise Refusal("nonterminal-EOF", "hash")
        eof(io, held.fd, buffer, counts)
    held.check()
    return h.digest()


def header_check(header, claims, source_bytes):
    if type(header) is not bytes or len(header) != 512 or header[:8] != b"MIXPRF01":
        raise Refusal("header", "admission")
    w = struct.unpack("<15Q", header[8:128])
    if w[:4] != (1, 512, 32, 80000) or w[4] != source_bytes or w[5] > 0xffffffff:
        raise Refusal("header-scalars", "admission")
    if not 1 <= w[6] <= 64 or not 1 <= w[7] <= 64 or w[8] != 1 or w[9] > w[10]:
        raise Refusal("header-initial-shape", "admission")
    if w[12:] != (0, 0, 0) or any(header[384:]):
        raise Refusal("reserved", "admission")
    for i, actual in enumerate(claims):
        if header[128 + i * 32:160 + i * 32] != actual:
            raise Refusal("digest-slot-" + str(i), "admission")


def bind_fixture_template(transport, claims, source_bytes):
    """Proposed host-only amendment, not an accepted product helper.

    Preserve the raw transport separately. All nonclaim bytes remain identical.
    The caller's all-zero opaque claims are never treated as verified bindings.
    """
    if len(claims) != 8 or any(type(x) is not bytes or len(x) != 32 for x in claims):
        raise Refusal("digest-count-width", "transport")
    header_check(transport, [bytes(32)] * 8, source_bytes)
    final = transport[:128] + b"".join(claims) + transport[384:]
    header_check(final, claims, source_bytes)
    if final[:128] != transport[:128] or final[384:] != transport[384:]:
        raise Refusal("nonclaim-drift", "transport")
    return final


class ChildLease:
    def __init__(self, held):
        self.held, self.process = held, None
        self.state, self.pass_fds = "new", None

    def __enter__(self):
        if self.state != "new" or len({x.fd for x in self.held}) != len(self.held):
            raise Refusal("child-lease", "launch")
        for x in self.held:
            x.idle()
        self.pass_fds = tuple(int(x.fd) for x in self.held)
        for x in self.held:
            x._lease = self
        self.state = "entered"
        return self

    def claim_launch(self):
        if self.state != "entered" or any(x.state != "open" or x._lease is not self or OWNERS.get(x.generation) is not x for x in self.held):
            raise Refusal("stale-child-adoption", "launch")
        self.state = "launch-consumed"
        return self.pass_fds

    def __exit__(self, *_):
        if self.process is not None and self.process.returncode is None:
            # Never close/read/seek an OFD still shared with an unreaped child.
            # This fault is source-reviewed, not exercised with a stuck OS child.
            QUARANTINES.append((self.process, self.held))
            self.state = "quarantined"
            raise Refusal("unreaped-child-quarantine", "terminal-reap")
        for x in self.held:
            if x._lease is not self:
                raise Refusal("lease-owner-mismatch", "terminal-reap")
            x._lease = None
        self.state = "closed"


def child_lease(*held):
    return ChildLease(held)


def _stdio_acquire(owner,scratch):
    # mkstemp returns a RAW fd and pathname, no Python FileIO/BufferedRandom owner.
    if owner.state!="opening" or STDIO_OWNERS.get(owner.generation) is not owner or owner._token.state!="acquiring" or STDIO_TOKENS.get(owner._token.generation) is not owner._token:
        raise Refusal("stdio-acquisition-ownership","stdio-acquisition")
    number,path=tempfile.mkstemp(prefix=".mixer-stdio-",dir=scratch)
    # Store the birth handle in the pre-registered token before any later hook
    # or fallible registration/prepare step; a post-return fault cannot hide it.
    owner._token.number=number;owner._token.state="owned";owner._path=path
    STDIO_PATHS[owner.generation]=path


def _stdio_prepare(owner):
    if owner.state!="opening" or STDIO_OWNERS.get(owner.generation) is not owner or owner._token.state!="owned" or STDIO_TOKENS.get(owner._token.generation) is not owner._token:
        raise Refusal("stdio-prepare-ownership","stdio-acquisition")
    info=os.fstat(owner._token.number)
    if not stat.S_ISREG(info.st_mode) or info.st_size != 0:
        raise Refusal("stdio-regular-empty","stdio-acquisition")
    os.unlink(owner._path)
    owner._path=None
    del STDIO_PATHS[owner.generation]


def _stdio_close_syscall(number):
    os.close(number)


class RawStdio:
    """Explicit raw-fd owner. No owning Python stream, finalizer or __del__."""
    def __init__(self,scratch):
        self.state="new";self._token=None;self._path=None;self._path_error=None;self._report=None
        if len(STDIO_OWNERS)>=2 or UNCERTAIN_CLOSES or STDIO_UNCERTAIN_CLOSES or STDIO_PATHS or QUARANTINES:
            raise Refusal("stdio-admission-quarantined-or-full","stdio-acquisition")
        self.generation=_generation();token_generation=_generation()
        STDIO_OWNERS[self.generation]=self;self.state="opening"
        try:
            self._token=_Descriptor(token_generation,self.generation,None,"acquiring")
            STDIO_TOKENS[token_generation]=self._token
            _stdio_acquire(self,scratch)
            _stdio_prepare(self)
            self.state="open"
        except BaseException as primary:
            self._path_error=primary
            try:self.close()
            except BaseException as cleanup:raise CleanupAggregate(primary,(cleanup,)) from primary
            raise

    def idle(self):
        if self.state!="open" or STDIO_OWNERS.get(self.generation) is not self or self._token is None or self._token.state!="owned" or STDIO_TOKENS.get(self._token.generation) is not self._token:
            raise Refusal("stdio-owner-not-open","stdio-access")

    def fileno(self):
        self.idle()
        return self._token.number

    def seek(self,offset):
        self.idle()
        if type(offset) is not int or offset!=0:raise Refusal("stdio-seek-shape","stdio-access")
        return os.lseek(self._token.number,0,os.SEEK_SET)

    def read(self,size):
        self.idle()
        if type(size) is not int or not 0<=size<=512:raise Refusal("stdio-read-cap","stdio-access")
        parts=[];remaining=size
        for _ in range(32):
            if remaining==0:return b"".join(parts)
            self.idle()
            try:part=os.read(self._token.number,remaining)
            except InterruptedError:continue
            if not part:return b"".join(parts)
            parts.append(part);remaining-=len(part)
        raise Refusal("stdio-read-attempts","stdio-access")

    def close(self):
        if self.state=="closed":return self._report
        if self.state=="quarantined":raise CleanupFailure(self._report)
        if self.state not in ("opening","open"):raise Refusal("stdio-close-not-open","stdio-close")
        self.state="closing"
        token=self._token;fault=None;attempted=();closed=();uncertain=();failures=[]
        if token is not None and token.number is None:
            token.state="unacquired"
            del STDIO_TOKENS[token.generation]
        elif token is not None:
            attempted=(token.generation,)
            was_owned=token.state=="owned" and token.owner_generation==self.generation and STDIO_TOKENS.get(token.generation) is token and STDIO_OWNERS.get(self.generation) is self
            token.state="closing"  # Consume the ONLY close capability first.
            try:
                if not was_owned:raise Refusal("stdio-close-ownership","stdio-close")
                _stdio_close_syscall(token.number)
            except BaseException as error:
                token.state="uncertain"
                fault=CloseFault(token.generation,self.generation,token.number,error,"stdio")
                STDIO_UNCERTAIN_CLOSES[token.generation]=fault
                uncertain=(token.generation,)
                failures.append(fault)
            else:
                token.state="closed";closed=(token.generation,)
                del STDIO_TOKENS[token.generation]
        if self._path is not None:
            failures.append(CloseFault(token.generation,self.generation,token.number,self._path_error or Refusal("stdio-path-unresolved","stdio-cleanup"),"stdio-path"))
        self.state="quarantined" if failures else "closed"
        if not failures:del STDIO_OWNERS[self.generation]
        self._report=CleanupReport(self.generation,self.state,attempted,closed,uncertain,tuple(failures))
        if failures:raise CleanupFailure(self._report)
        return self._report


class TerminalStreams:
    def __init__(self,scratch):
        self.scratch=scratch;self.state="new";self._frame=CleanupFrame();self._terminal_error=None;self._has_result=False
    def __enter__(self):
        if self.state!="new":raise Refusal("stdio-context-not-new","stdio-acquisition")
        self.state="opening"
        try:
            self.out=self._frame.adopt(RawStdio(self.scratch))
            self.err=self._frame.adopt(RawStdio(self.scratch))
        except BaseException as primary:
            try:self._frame.__exit__(type(primary),primary,primary.__traceback__)
            except BaseException as combined:
                self.state="quarantined";self._terminal_error=combined;raise
            if isinstance(primary,CleanupAggregate):
                self.state="quarantined";self._terminal_error=primary
            else:self.state="closed"
            raise
        self.state="entered"
        return self
    def __iter__(self):return iter((self.out,self.err))
    def completed(self,result):
        if self.state!="entered" or self._has_result:raise Refusal("stdio-result-state","stdio-result")
        self._has_result=True;self._frame.result=result
    def __exit__(self,kind,primary,tb):
        if self.state=="closed":return False
        if self.state=="quarantined":raise self._terminal_error
        if self.state!="entered":raise Refusal("stdio-context-not-open","stdio-close")
        try:self._frame.__exit__(kind,primary,tb)
        except BaseException as combined:
            self.state="quarantined";self._terminal_error=combined;raise
        self.state="closed"
        return False


def terminal_streams(scratch):return TerminalStreams(scratch)


def child_consume(profile, body, scratch):
    script = Path(__file__).with_name("consumer.py")
    executable = os.path.realpath(sys.executable)
    argv = [executable, "-I", "-S", "-B", str(script), str(profile.fd), str(body.fd)]
    with terminal_streams(scratch) as streams:
        out,err=streams
        process = None
        with child_lease(profile, body) as lease:
            try:
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, close_fds=True, pass_fds=lease.claim_launch(), env={"LC_ALL": "C", "LANG": "C"}, cwd=scratch)
                lease.process = process
                try:
                    code = process.wait(timeout=5)
                except subprocess.TimeoutExpired as e:
                    process.kill()
                    process.wait(timeout=5)
                    raise Refusal("child-timeout", "terminal-reap") from e
                if code != 0:
                    raise Refusal("child-status", "terminal-reap")
            finally:
                if process is not None and process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
        for stream in (out, err):
            if os.fstat(stream.fileno()).st_size > 512:
                raise Refusal("child-output-cap", "child-report")
            stream.seek(0)
        raw, errors = out.read(512), err.read(512)
        if errors:
            raise Refusal("child-stderr", "child-report")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as e:
            raise Refusal("child-report", "child-report") from e
        if type(result) is not dict or set(result) != {"profile", "subrange", "body", "adoptions"} or result["adoptions"] != 2:
            raise Refusal("child-report", "child-report")
        observation=(result,{"argv": argv, "pass_fds_count": 2, "terminal_reaped": process.returncode is not None, "stdout_bytes": len(raw), "stderr_bytes": len(errors), "consumer_source": "consumer.py", "consumer_custody": "separate packet source receipt; no executable attestation"})
        streams.completed(observation)
    return observation


def compose_fixture(paths, sizes, header, output, scratch, scope=SCOPE):
    if scope != SCOPE:
        raise Refusal("unsupported-custody", "admission")
    if set(paths) != set(NAMES) or set(sizes) != set(NAMES):
        raise Refusal("closed-inputs", "admission")
    if any(type(sizes[k]) is not int or not 0 < sizes[k] <= cap for k, cap in zip(NAMES, CAPS)) or sizes[NAMES[7]] != BODY:
        raise Refusal("length-budget", "admission")
    with CleanupFrame() as frame:
        inputs = [frame.adopt(Retained(paths[k], sizes[k])) for k in NAMES]
        result = compose_from_retained_fixture(inputs, header, output, scratch, scope)
        frame.result = result
    return result


def compose_from_retained_fixture(inputs, header, output, scratch, scope=SCOPE):
    """Borrow retained fixture owners; never reopen any of their paths.

    The body may be the same still-open descriptor a finite synthetic writer just
    completed at EOF. This is not proof of the missing authentic Rust producer.
    """
    if scope != SCOPE:
        raise Refusal("unsupported-custody", "admission")
    if len(inputs) != 8 or any(type(x) is not Retained for x in inputs):
        raise Refusal("retained-inputs", "admission")
    if any(type(x.size) is not int or not 0 < x.size <= cap for x, cap in zip(inputs, CAPS)) or inputs[7].size != BODY:
        raise Refusal("length-budget", "admission")
    for i, held in enumerate(inputs):
        held.idle()
        position = os.lseek(held.fd, 0, os.SEEK_CUR)
        if position not in ((0, BODY) if i == 7 else (0,)):
            raise Refusal("input-offset", "admission")
    buffer, counts, io = bytearray(CHUNK), IOCount(), IO()
    ids = [x.initial[:2] for x in inputs]
    if len(set(ids)) != len(ids):
        raise Refusal("input-alias", "admission")
    claims = [hash_range(x, buffer, counts, io) for x in inputs]
    header_check(header, claims, inputs[2].size)
    with CleanupFrame() as output_frame:
        result = output_frame.adopt(Retained(output, PROFILE, output=True))
        if result.initial[:2] in ids:
            raise Refusal("output-alias", "admission")
        transfer(io, result.fd, memoryview(header), counts, True)
        body = inputs[7]
        os.lseek(body.fd, 0, os.SEEK_SET)
        for start in range(0, BODY, CHUNK):
            v = memoryview(buffer)[:min(CHUNK, BODY - start)]
            transfer(io, body.fd, v, counts, False)
            transfer(io, result.fd, v, counts, True)
        eof(io, body.fd, buffer, counts)
        if os.fstat(result.fd).st_size != PROFILE or os.lseek(result.fd, 0, os.SEEK_CUR) != PROFILE:
            raise Refusal("output-length-offset", "composition", counts)
        result.initial = identity(os.fstat(result.fd))
        result.check()
        profile_pre = hash_range(result, buffer, counts, io)
        subrange_pre = hash_range(result, buffer, counts, io, 512, BODY)
        if subrange_pre != claims[7]:
            raise Refusal("subrange-digest", "composition", counts)
        child, child_receipt = child_consume(result, body, scratch)
        profile_post = hash_range(result, buffer, counts, io)
        subrange_post = hash_range(result, buffer, counts, io, 512, BODY)
        post = [hash_range(x, buffer, counts, io) for x in inputs]
        if post != claims or profile_pre != profile_post or subrange_pre != subrange_post:
            raise Refusal("retained-byte-drift", "post-consumer", counts)
        expected = {"profile": profile_pre.hex(), "subrange": claims[7].hex(), "body": claims[7].hex(), "adoptions": 2}
        if child != expected:
            raise Refusal("child-join", "post-consumer", counts)
        observation = {"scope": SCOPE, "fixture_only": True, "claims": [x.hex() for x in claims], "profile_sha256": profile_post.hex(), "body_sha256": subrange_post.hex(), "profile_bytes": PROFILE, "output_acknowledged_bytes": counts.write_acknowledged, "io": asdict(counts), "child": child_receipt, "authority": dict(real_binding=False, semantic_metrics=False, full_replay=False, runtime=False, ota=False, ga=False)}
        output_frame.result = observation
    return observation
