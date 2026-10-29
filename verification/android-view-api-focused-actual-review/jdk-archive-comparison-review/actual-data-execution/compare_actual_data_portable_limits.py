"""ROOT-SELECTED DATA COMPARISON: one invocation.
CPU/output caps apply; address-space rejection is reported without claiming enforcement.
Proposed command: /opt/homebrew/bin/python3 -I -B -S this_file.py.
"""
import binascii
import builtins
import gzip
import hashlib
import io
import json
import os
import resource
import stat
import struct
import sys
import tarfile
import zlib

_BINDING = json.loads(r'''{"complete":true,"actual_observation":{"repository":"snowdamiz/mixer","run_id":40863640582,"attempt":1,"source_commit":"47b62878bae3aa3d4dff5d565b63f4a533e7abde","artifact":{"id":12892168454,"bytes":5904159,"sha256":"b166c2e2ce0dbff158315166ce407cd21915e560fcb22577ffd1630f1556cfb0"},"context":{"expected_members":74,"other_exact_hash_matches":72,"remaining_comparison_members":["lib/ct.sym","lib/jrt-fs.jar"],"artifact_environment_ImageVersion":"20261026.354.1","root_job_setup_log_ImageVersion":"20261025.353.1","image_label_discrepancy_retained":true,"labels_establish_old_mismatch_cause_or_provenance":false}},"successful_audit":{"path":"/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-focused-actual-review/jdk-data-actual-review/actual-review-receipt.json","bytes":20879,"sha256":"d7f01dbbe7c163562c058342cff3a14b3a2ee4601997029adc7b2364d79369c9"},"successful_audit_seal":{"path":"/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-focused-actual-review/jdk-data-actual-review/actual-review-seal.json","bytes":1696,"sha256":"9552689837be59939a0f2c829f10ed748bcc8e7fcd7aa8174074903718e5a5a2"},"observed_raw":{"lib/ct.sym":{"path":"/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-focused-actual-review/jdk-data-actual-review/local/recovery-001/raw/ct.sym.raw-data.bin","bytes":8264052,"sha256":"7bcc87b05b8e68f71e20c176c9af0efadc7292e0ca192f217b3f620e0c108a53"},"lib/jrt-fs.jar":{"path":"/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-focused-actual-review/jdk-data-actual-review/local/recovery-001/raw/jrt-fs.jar.raw-data.bin","bytes":110495,"sha256":"ae34105a07841c5ecc172ccc16732cf25d5b5adbfdbf1e03463c4a2bc91b1cbf"}}}''')
_SOURCE_INPUT = {"path": "/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/compare_data.py", "bytes": 16443, "sha256": "156ce9f6ab5d5da580c788c051cbc98229ad641bd150810ef0bb93c92c2ff8c2"}
_ARCHIVE_INPUT = {"path": "/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-boundary-linux-tool-profile/local/OpenJDK17U-jdk_x64_linux_hotspot_17.0.21_9.tar.gz", "bytes": 193594705, "sha256": "8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711"}
_CHUNK = 65536
_MAX_OUTPUT = 67174400
_LIMITS = {"cpu_seconds": 120, "address_space_requested_bytes": 1073741824, "address_space_rejection_allowed": True, "file_size_bytes": _MAX_OUTPUT + 1, "external_wall_seconds_enforced": None}
_STAGE = "bindings"

def _need(ok, reason):
    if not ok:
        raise ValueError(reason)

def _hex(value, length):
    return type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value)

def _file_key(info):
    return tuple(getattr(info, key) for key in ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns"))

def _node_key(info):
    return (info.st_dev, info.st_ino, info.st_mode)

def _validate_named(spec):
    _need(type(spec) is dict and set(spec) == {"path", "bytes", "sha256"}, "exact named input contract required")
    path = spec["path"]
    _need(type(path) is str and path.startswith("/") and len(path.encode("utf-8")) <= 4096, "absolute bounded named input path required")
    parts = path.split("/")[1:]
    _need(1 <= len(parts) <= 128 and all(part and part not in (".", "..") and "\x00" not in part for part in parts), "unsafe named input path")
    _need(type(spec["bytes"]) is int and 0 < spec["bytes"] <= 193594705 and _hex(spec["sha256"], 64), "complete exact input identity required")

def _read_stable(spec):
    # One final file open and one sequential read pass. Parent components are
    # opened with O_NOFOLLOW and retained to verify every name after the read.
    _validate_named(spec)
    _need(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NONBLOCK"), "nofollow stable-read platform required")
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    directories, file_fd = [], None
    try:
        root_fd = os.open("/", flags | os.O_DIRECTORY)
        directories.append((root_fd, None, None))
        parts = spec["path"].split("/")[1:]
        for part in parts[:-1]:
            parent = directories[-1][0]
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=parent)
            directories.append((child, parent, part))
        parent = directories[-1][0]
        file_fd = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(file_fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_size == spec["bytes"], "named input is not the exact-size ordinary file")
        digest, chunks, size = hashlib.sha256(), [], 0
        while True:
            block = os.read(file_fd, min(_CHUNK, spec["bytes"] - size + 1))
            if not block:
                break
            size += len(block)
            _need(size <= spec["bytes"], "named input grew beyond exact byte cap")
            digest.update(block); chunks.append(block)
        after = os.fstat(file_fd)
        named_after = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        _need(_file_key(before) == _file_key(after) == _file_key(named_after), "named file changed during acquisition")
        for directory, parent_fd, name in directories[1:]:
            _need(_node_key(os.fstat(directory)) == _node_key(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)), "named parent changed during acquisition")
        _need(size == spec["bytes"] and digest.hexdigest() == spec["sha256"], "named input exact length/SHA256 mismatch")
        immutable = b"".join(chunks)
        _need(type(immutable) is bytes and len(immutable) == size, "immutable complete input required")
        return immutable, {"path": spec["path"], "bytes": size, "sha256": digest.hexdigest(), "before_stat": list(_file_key(before)), "after_stat": list(_file_key(after)), "named_after_stat": list(_file_key(named_after)), "symlink_components_followed": False, "file_opens": 1, "sequential_read_passes": 1}
    finally:
        if file_fd is not None:
            os.close(file_fd)
        for directory, _, _ in reversed(directories):
            os.close(directory)

def _run():
    global _STAGE
    _need(_BINDING["complete"] is True, "actual audit/raw bindings are incomplete; no input read or comparison selected")
    _need(sys.flags.isolated and sys.flags.dont_write_bytecode and sys.flags.no_site, "requires Python -I -B -S")
    _need(sys.version_info[:3] == (3, 14, 8), "requires root-observed Python3.14.8")
    _need(set(_BINDING["observed_raw"]) == {"lib/ct.sym", "lib/jrt-fs.jar"}, "exact two audited raw members required")
    _need(_hex(_BINDING["actual_observation"]["source_commit"], 40), "full audited source commit required")
    for spec in (_SOURCE_INPUT, _ARCHIVE_INPUT, _BINDING["successful_audit"], *_BINDING["observed_raw"].values()):
        _validate_named(spec)
    _need(_BINDING["successful_audit"]["bytes"] <= 1048576, "audit receipt exceeds1MiB cap")
    _need(_BINDING["observed_raw"]["lib/ct.sym"]["bytes"] <= 16777216 and _BINDING["observed_raw"]["lib/jrt-fs.jar"]["bytes"] <= 1048576, "audited raw input cap")
    _paths = [spec["path"] for spec in (_SOURCE_INPUT, _ARCHIVE_INPUT, _BINDING["successful_audit"], *_BINDING["observed_raw"].values())]
    _need(len(set(_paths)) == 5, "five distinct named inputs required")
    # Nonempty exact codec warmup is required before import denials.
    _need(b"\x82".decode("cp437", "strict") == "\u00e9", "stdlib cp437 warmup assertion failed")
    _STAGE = "self-limits"
    _limit_effects = {}
    for _label, _kind, _requested in (("cpu", resource.RLIMIT_CPU, _LIMITS["cpu_seconds"]), ("address_space", resource.RLIMIT_AS, _LIMITS["address_space_requested_bytes"]), ("file_size", resource.RLIMIT_FSIZE, _LIMITS["file_size_bytes"])):
        _STAGE = "self-limit-" + _label
        _before = resource.getrlimit(_kind)
        try:
            resource.setrlimit(_kind, (_requested, _requested))
        except ValueError as _limit_error:
            if _label != "address_space" or str(_limit_error) != "current limit exceeds maximum limit":
                raise
            _after = resource.getrlimit(_kind)
            _need(_after == _before, "rejected address-space limit unexpectedly changed")
            _limit_effects[_label] = {"requested": _requested, "before": list(_before), "after": list(_after), "enforced": False, "error": str(_limit_error), "root_selected_fallback": "finite input/decompression/output caps; no OS address-space cap claimed"}
        else:
            _after = resource.getrlimit(_kind)
            _need(_after == (_requested, _requested), "self-limit readback differs")
            _limit_effects[_label] = {"requested": _requested, "before": list(_before), "after": list(_after), "enforced": True}
    _STAGE = "named-read-acquisition"
    loaded, receipts = {}, {}
    for label, spec in (("source", _SOURCE_INPUT), ("audit", _BINDING["successful_audit"]), ("archive", _ARCHIVE_INPUT), *( (member, _BINDING["observed_raw"][member]) for member in ("lib/ct.sym", "lib/jrt-fs.jar") )):
        loaded[label], receipts[label] = _read_stable(spec)
    audit_value = json.loads(loaded["audit"])
    _need(type(audit_value) is dict, "bound successful audit receipt must be a JSON object")
    _need(audit_value["status"] == "reviewed-exact13-complete74-data-observation", "successful exact13/74 audit status required")
    audited_binding = audit_value["binding"]
    _need(audited_binding["repository"] == "snowdamiz/mixer" and audited_binding["run_id"] == 40863640582 and audited_binding["run_attempt"] == 1 and audited_binding["delivered_head"] == _BINDING["actual_observation"]["source_commit"] and audited_binding["artifact_id"] == 12892168454, "successful audit run/source/artifact binding mismatch")
    _need(audited_binding["archive"] == {"bytes": 5904159, "sha256": "b166c2e2ce0dbff158315166ce407cd21915e560fcb22577ffd1630f1556cfb0"}, "successful audit artifact identity mismatch")
    raw_rows = audit_value["raw_exports"]
    _need(type(raw_rows) is list and len(raw_rows) == 2 and {row["member"] for row in raw_rows} == set(_BINDING["observed_raw"]), "successful audit exact raw exports required")
    for row in raw_rows:
        _need({key: row[key] for key in ("path", "bytes", "sha256")} == _BINDING["observed_raw"][row["member"]] and row["inner_archive_inspected"] is False, "successful audit raw identity mismatch")
    counts = audit_value["runtime_members"]
    _need(counts["expected"] == 74 and counts["matches"] == 72 and counts["mismatch_count"] == 2 and counts["refusals"] == 0, "successful audit expected74/other72 context mismatch")
    _need(audit_value["admission"]["provider_runtime_admitted"] is False and audit_value["admission"]["all_prior_holds_preserved"] is True, "successful audit must preserve runtime holds")
    _runtime = {"version": sys.version, "implementation": sys.implementation.name, "executable": sys.executable, "isolated": True, "dont_write_bytecode": True, "no_site": True}
    _STAGE = "guards"
    class GuardDenial(PermissionError):
        pass
    
    def _deny(*args, **kwargs):
        raise GuardDenial("synthetic checker forbids filesystem/process/network/native-loader/timer operations")
    
    # All subject imports are already loaded above. No deferred subject import is admitted.
    _ALLOWED_IMPORTS = frozenset(("binascii", "gzip", "hashlib", "io", "json", "stat", "struct", "tarfile", "zlib"))
    _original_import, _original_exec, _original_compile = builtins.__import__, builtins.exec, builtins.compile
    
    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name not in _ALLOWED_IMPORTS:
            raise GuardDenial("import refused: " + str(name))
        return _original_import(name, globals, locals, fromlist, level)
    
    def _audit(event, args):
        if event == "open" or event.startswith(("os.", "subprocess.", "socket.", "ctypes.", "signal.", "resource.", "mmap.", "winreg.", "_winapi.", "pty.")):
            raise GuardDenial("audit refused: " + event)
        if event == "import" and args[0] not in _ALLOWED_IMPORTS:
            raise GuardDenial("deferred import refused")
    
    # Deny known no-audit process queries, waits, signals and clocks if their modules
    # were loaded transitively. This inspects module dictionaries, never host state.
    _os_names = ("open", "fdopen", "listdir", "scandir", "stat", "lstat", "fstat", "readlink", "read", "write", "close", "chdir", "fchdir", "getcwd", "getcwdb", "mkdir", "makedirs", "unlink", "remove", "rmdir", "removedirs", "rename", "renames", "replace", "link", "symlink", "chmod", "fchmod", "chown", "fchown", "lchown", "utime", "truncate", "ftruncate", "system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe", "getpid", "getppid", "getpgid", "getpgrp", "getsid", "setsid", "setpgid", "kill", "killpg", "wait", "waitpid", "waitid", "wait3", "wait4", "pidfd_open", "times", "getloadavg", "sched_getaffinity", "sched_setaffinity", "sched_getscheduler", "sched_setscheduler", "sched_yield", "getpriority", "setpriority", "urandom")
    for _modname in ("os", "posix", "nt"):
        _mod = sys.modules.get(_modname)
        if _mod is not None:
            for _name in _os_names:
                if hasattr(_mod, _name):
                    setattr(_mod, _name, _deny)
    for _modname, _names in {
        "time": ("sleep", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "process_time", "process_time_ns", "thread_time", "thread_time_ns", "clock_gettime", "clock_gettime_ns", "clock_getres", "clock_settime", "clock_settime_ns"),
        "signal": ("signal", "getsignal", "alarm", "pause", "setitimer", "getitimer", "pthread_kill", "pthread_sigmask", "sigpending", "sigwait", "sigwaitinfo", "sigtimedwait", "raise_signal"),
        "socket": ("socket", "socketpair", "create_connection", "create_server", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostname", "getfqdn"),
        "_socket": ("socket", "socketpair", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostname"),
        "ctypes": ("CDLL", "PyDLL", "WinDLL", "OleDLL", "CFUNCTYPE", "PYFUNCTYPE", "WINFUNCTYPE", "cast", "memmove", "memset", "string_at", "wstring_at"),
        "_ctypes": ("dlopen", "LoadLibrary", "call_function", "call_cdeclfunction", "dlsym"),
        "threading": ("Thread", "Timer"),
        "_thread": ("start_new_thread", "start_new", "allocate_lock", "allocate", "get_ident", "get_native_id"),
        "resource": ("getrusage", "getrlimit", "setrlimit", "prlimit"),
        "subprocess": ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"),
    }.items():
        _mod = sys.modules.get(_modname)
        if _mod is not None:
            for _name in _names:
                if hasattr(_mod, _name):
                    setattr(_mod, _name, _deny)
    sys.addaudithook(_audit)
    builtins.__import__, builtins.open, io.open = _guarded_import, _deny, _deny
    builtins.input, builtins.breakpoint = _deny, _deny
    
    _STAGE = "source-evaluation"
    subject = {"__name__": "frozen_comparator_actual_data_subject", "__builtins__": builtins.__dict__}
    _original_exec(_original_compile(loaded["source"], "<frozen-compare-data>", "exec"), subject)
    _STAGE = "fixed-two-member-comparison"
    observed = {member: loaded[member] for member in ("lib/ct.sym", "lib/jrt-fs.jar")}
    observed_identities = {member: {"bytes": _BINDING["observed_raw"][member]["bytes"], "sha256": _BINDING["observed_raw"][member]["sha256"]} for member in observed}
    report = subject["compare_data"](loaded["archive"], observed, observed_identities)
    _need(report["runtime_admitted"] is False and report["prepared13_or152_pass"] is False and report["cause_or_provider_provenance_established"] is False, "comparison must preserve qualification holds")
    report["guarded_wrapper"] = {"schema": 1, "actual_observation": _BINDING["actual_observation"], "successful_audit": _BINDING["successful_audit"], "successful_audit_seal": _BINDING["successful_audit_seal"], "source": _SOURCE_INPUT, "observed_raw": _BINDING["observed_raw"], "stable_input_reads": receipts, "limits": _LIMITS, "self_limit_results": _limit_effects, "runtime": _runtime, "source_evaluated_after_denials": True, "subprocesses": 0, "Java_or_JVM": False, "runtime_admitted": False}
    _STAGE = "bounded-canonical-output"
    payload = subject["canonical"](report)
    _need(len(payload) <= _MAX_OUTPUT, "guarded canonical JSON output exceeds bounded cap")
    summary = {"status": "fixed-two-member-data-comparison-complete", "run_id": _BINDING["actual_observation"]["run_id"], "outcomes": {member: row["outcome"] for member, row in report["results"].items()}, "json_bytes": len(payload), "json_sha256": hashlib.sha256(payload).hexdigest(), "runtime_admitted": False}
    return payload, summary

try:
    _payload, _summary = _run()
except Exception as error:
    _failure = {"schema": 1, "status": "refused-no-success-report", "stage": _STAGE, "error_type": type(error).__name__, "error": str(error)[:2048], "actual_comparison_completed": False, "runtime_admitted": False}
    print(json.dumps(_failure, sort_keys=True, separators=(",", ":")))
    raise SystemExit(1)
_summary_bytes = json.dumps(_summary, sort_keys=True, separators=(",", ":")).encode("ascii")
if len(_summary_bytes) > 8192:
    raise SystemExit("bounded summary cap exceeded before report write")
sys.stdout.buffer.write(_payload + b"\n")
sys.stderr.buffer.write(_summary_bytes + b"\n")
