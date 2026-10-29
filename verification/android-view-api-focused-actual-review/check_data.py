"""Finite synthetic data controls only. No subject inspector import or runtime."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import types
import json
import io
import zipfile
import stat
import struct
import hashlib
HERE = Path(__file__).resolve().parent


def own_module(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec", dont_inherit=True), module.__dict__)
    return module


guard = own_module(HERE / "guarded_inspector.py", "actual_review_guard")
guard_receipt = guard.install_guards()
data = guard.load_data_module(HERE / "audit_data.py", "actual_review_data")
passed, failed = [], []


def test(name, action):
    try:
        action()
        passed.append(name)
    except BaseException as error:
        failed.append({"name": name, "error": type(error).__name__ + ": " + str(error)[:500]})


def need(value):
    if not value:
        raise AssertionError("control did not hold")


def refuses(action, exception=data.Refusal):
    try:
        action()
    except exception:
        return
    raise AssertionError("expected refusal")


def archive(rows):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name, content, mode in rows:
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 29, 0, 0, 0))
            info.create_system = 3
            info.external_attr = mode << 16
            z.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED)
    return stream.getvalue()


regular = stat.S_IFREG | 0o644
good = archive([("commands/java-version/stdout", b"", regular), ("receipt.json", b'{"a":1}\n', regular)])
test("strict valid JSON", lambda: need(data.strict_json(b'{"a":1,"b":[true,null]}') == {"a": 1, "b": [True, None]}))
for name, raw in [("duplicate", b'{"a":1,"a":2}'), ("nested duplicate", b'{"a":{"x":1,"x":2}}'), ("NaN", b'NaN'), ("Infinity", b'Infinity'), ("overflow", b'1e9999'), ("BOM", b'\xef\xbb\xbf{}'), ("trailing", b'{}x'), ("surrogate", b'"\\ud800"'), ("invalid UTF8", b'"\xff"')]:
    test("JSON refuses " + name, lambda raw=raw: refuses(lambda: data.strict_json(raw)))
test("JSON byte bound", lambda: refuses(lambda: data.strict_json(b'{}', maximum=1)))
test("JSON depth bound", lambda: refuses(lambda: data.strict_json(b'[' * 70 + b'0' + b']' * 70)))
test("ZIP valid contents and hashes", lambda: need(data.inspect_zip(good)[0]["receipt.json"] == b'{"a":1}\n'))
for name in ("../escape", "/absolute", "x/../escape", "x//empty", "./dot", "x\\backslash", "C:drive", "x/\x01control", "a/" * 17 + "file"):
    test("ZIP path refusal " + repr(name), lambda name=name: refuses(lambda: data.inspect_zip(archive([(name, b"x", regular)]))))
test("ZIP duplicate", lambda: refuses(lambda: data.inspect_zip(archive([("same", b"a", regular), ("same", b"b", regular)]))))
test("ZIP case alias", lambda: refuses(lambda: data.inspect_zip(archive([("Same", b"a", regular), ("same", b"b", regular)]))))
test("ZIP symlink", lambda: refuses(lambda: data.inspect_zip(archive([("link", b"../target", stat.S_IFLNK | 0o777)]))))
test("ZIP device", lambda: refuses(lambda: data.inspect_zip(archive([("dev", b"", stat.S_IFCHR | 0o600)]))))
test("ZIP file-parent collision", lambda: refuses(lambda: data.inspect_zip(archive([("a", b"file", regular), ("a/b", b"child", regular)]))))
corrupt = bytearray(good)
corrupt[30 + len("commands/java-version/stdout") + 2] ^= 1
test("ZIP CRC corruption", lambda: refuses(lambda: data.inspect_zip(bytes(corrupt))))
wrong_name = bytearray(good)
wrong_name[30] = ord("X")
test("ZIP local name disagreement", lambda: refuses(lambda: data.inspect_zip(bytes(wrong_name))))
encrypted = bytearray(good)
struct.pack_into("<H", encrypted, 6, 1)
test("ZIP local flags disagreement", lambda: refuses(lambda: data.inspect_zip(bytes(encrypted))))
test("ZIP truncated archive", lambda: refuses(lambda: data.inspect_zip(good[:50])))
test("pending actual binding refuses", lambda: refuses(lambda: data.validate_binding({"schema": 1})))
test("frozen source selection and closed inputs", lambda: need(data.source_audit()["producer_members"] == 115))
test("active process creation denied", lambda: refuses(lambda: guard.subprocess.run(["must-never-execute"]), guard.ActiveAPIDenied))
test("active group signal denied", lambda: refuses(lambda: guard.os.killpg(-1, 0), guard.ActiveAPIDenied))
test("active raw wait denied", lambda: refuses(lambda: guard.os.waitpid(-1, 0), guard.ActiveAPIDenied))
test("active timer denied", lambda: refuses(lambda: guard.time.sleep(0), guard.ActiveAPIDenied))
test("active socket denied", lambda: refuses(lambda: guard.socket.socket(), guard.ActiveAPIDenied))
test("active native library denied", lambda: refuses(lambda: guard.ctypes.CDLL(None), guard.ActiveAPIDenied))
test("unreviewed subject import denied", lambda: refuses(lambda: __import__("subprocess"), guard.ActiveAPIDenied))

if len(sys.argv) != 2:
    raise ValueError("exact ignored output directory required")
out = Path(sys.argv[1]).absolute()
need(out.is_relative_to(HERE / "local"))
out.mkdir(parents=True, exist_ok=False)
report = {"schema": 1, "scope": "own source/data/synthetic controls only", "actual_run_reviewed": False,
          "subject_inspector_imports": 0, "subject_compiler_JVM_product_native_UI_capture_phone_runs": 0,
          "network_git_gh_actions": 0, "command": list(sys.orig_argv), "python": {"executable": sys.executable, "version": sys.version},
          "sources": [{"path": p.name, **data.identity(p.read_bytes())} for p in (Path(__file__), HERE / "audit_data.py", HERE / "guarded_inspector.py")],
          "guard": guard_receipt, "passed": passed, "failed": failed, "passed_count": len(passed), "failed_count": len(failed)}
(out / "receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({"passed": len(passed), "failed": len(failed), "receipt": str(out / "receipt.json")}))
if failed:
    raise AssertionError(json.dumps(failed))
