"""Selected known-source fixture controls only. No product/compiler/custody imports."""
import sys
sys.dont_write_bytecode = True
if not (sys.flags.isolated == 1 and sys.flags.no_site == 1):
    raise RuntimeError("Run with -I -B -S")
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import time
import types
import unittest
import xml.etree.ElementTree as ET
import zlib

class Refusal(RuntimeError):
    pass

def need(value, message):
    if not value:
        raise Refusal(message)

def stat_identity(value):
    return (value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns)

def bounded_file(path, maximum, check=lambda:None, retain=False):
    """One nofollow, nonblocking descriptor; at most maximum+1 bytes are read."""
    need(type(maximum) is int and maximum >= 0, "Finite nonnegative byte cap required")
    path = Path(path)
    check()
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "Ordinary bounded file required")
    digest,total,chunks = hashlib.sha256(),0,[]
    descriptor = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor,"rb") as stream:
        opened = os.fstat(stream.fileno())
        need(stat.S_ISREG(opened.st_mode) and stat_identity(opened) == stat_identity(before),
             "File changed before nofollow open")
        while True:
            check()
            chunk = stream.read(min(1048576,maximum-total+1))
            if not chunk: break
            total += len(chunk)
            need(total <= maximum,"File grew beyond byte bound")
            digest.update(chunk)
            if retain: chunks.append(chunk)
        check()
        need(stat_identity(os.fstat(stream.fileno())) == stat_identity(before),
             "File descriptor changed during bounded read")
    check()
    need(stat_identity(path.lstat()) == stat_identity(before) and total == before.st_size,
         "File path changed during bounded read")
    return (b"".join(chunks) if retain else None),{"bytes":total,"sha256":digest.hexdigest()}

def file_snapshot(path, maximum, check=lambda:None):
    return bounded_file(path,maximum,check,True)


HERE = Path(__file__).resolve().parent
GUARD_SHA256 = "a21b0e80f9efe937bf18117d8f2c611f386073c796ba91c74f009c724a561197"

def main():
    need(len(sys.argv) == 1,"This launcher takes no positional arguments")
    selected = os.environ.get("MIXER_PAIR7_CONTROL_ROOT")
    need(isinstance(selected,str) and selected,"Explicit fresh owned fixture root required")
    root = Path(selected)
    need(root.is_absolute() and root.parent.resolve(strict=True) == root.parent
         and root.name.startswith("pair7-java-controls-") and not os.path.lexists(root)
         and not root.is_relative_to(HERE) and not HERE.is_relative_to(root),
         "Separate fresh canonical fixture root required")
    deadline = time.monotonic()+30
    def check():
        need(time.monotonic() < deadline,"Fixture guard bootstrap wall deadline exhausted")
    source,identity = file_snapshot(HERE/"fixture_guard.py",65536,check)
    need(identity["sha256"] == GUARD_SHA256,"Selected fixture guard hash changed")
    guard = types.ModuleType("pair7_v3_fixture_guard")
    guard.__file__ = str(HERE/"fixture_guard.py")
    sys.modules[guard.__name__] = guard
    exec(compile(source,guard.__file__,"exec"),guard.__dict__)
    root.mkdir(exist_ok=False)
    guard.install(root,HERE)
    # The pinned guard is active before any control or subject data module import.
    seal_data,_ = file_snapshot(HERE/"seal.json",65536,check)
    seal = json.loads(seal_data)
    row = next(r for r in seal["members"] if r["path"] == "test_source_controls.py")
    control_path = HERE/"test_source_controls.py"
    source,identity = file_snapshot(control_path,524288,check)
    need(identity == {k:row[k] for k in ("bytes","sha256")},"Selected controls changed")
    module = types.ModuleType("__main__")
    module.__file__ = str(control_path)
    sys.modules["__main__"] = module
    sys.argv = [str(control_path)]
    exec(compile(source,str(control_path),"exec"),module.__dict__)

if __name__ == "__main__":
    main()
