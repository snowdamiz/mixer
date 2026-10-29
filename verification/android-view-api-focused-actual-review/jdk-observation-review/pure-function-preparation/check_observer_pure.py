"""Proposed source-bound pure observer check. UNRUN; root selects one execution.
No bootstrap import/execution, real observation callback, child, or runtime tool.
"""
import sys
sys.dont_write_bytecode = True
import os
import stat
import json
import hashlib
import builtins
import resource
import ast

PREP = "/Users/andreyyurlov/Documents/dev/mixer/verification/android-view-api-focused-actual-review/jdk-observation-preparation"
SOURCE_MANIFEST_SHA = "f865a86fb102646eb2c25e8fab00e13651de4f950e474e7faae4561516e69fb0"
FROZEN = [
    {
        "path": "bootstrap.py",
        "bytes": 23487,
        "sha256": "9e54a8b30a52b4759be1ff97f4f92f41a0ad276578d6e3dfcc7d0d2c8085c93e"
    },
    {
        "path": "contract.json",
        "bytes": 7052,
        "sha256": "2c783ac0d44c9ceaa74fa3e8a47678f5662523e4ec18eeea969947b2cd9bac10"
    },
    {
        "path": "expected-runtime-members.json",
        "bytes": 10885,
        "sha256": "c75e64616ebb599f7337df7d7026286f1fd2d300347b59e28fb8a1051fdef13f"
    },
    {
        "path": "observe_jdk.py",
        "bytes": 9546,
        "sha256": "b5591bb1766a036a90428573497d3cf9f03254e1e444c646eaa7848951f3e7d3"
    },
    {
        "path": "workflow-draft.yml",
        "bytes": 4044,
        "sha256": "18a7451271c17ca9fdbaae74091a859a7e49337e93d5f6a3277699f4159d6f0a"
    }
]
SAFE_NAMES = ("isinstance", "list", "dict", "set", "len", "any", "all", "type", "int", "str", "sorted", "ValueError", "UnicodeError", "bool", "next")
JDK = "/usr/lib/jvm/temurin-17-jdk-amd64/"
RAW_CAPS = {"lib/ct.sym": 16777216, "lib/jrt-fs.jar": 1048576}
EXPECTED_CASES = 42
RESULTS = []


def need(ok, reason):
    if not ok:
        raise AssertionError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def clone(value):
    return json.loads(json.dumps(value, allow_nan=False))


def deny_active_apis():
    """Install source-level denials; do not call any denied API as a probe."""
    denied = []
    def blocked(*args, **kwargs):
        raise RuntimeError("active API forbidden in pure observer check")
    os_names = (
        "system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp",
        "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe",
        "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
        "kill", "killpg", "pidfd_open", "wait", "wait3", "wait4", "waitid", "waitpid",
        "getpid", "getppid", "getpgrp", "getpgid", "getsid", "setsid", "setpgid",
        "getpriority", "setpriority", "sched_getaffinity", "sched_setaffinity",
        "sched_getparam", "sched_setparam", "sched_getscheduler", "sched_setscheduler",
        "sched_rr_get_interval", "times", "getloadavg", "uname", "nice", "abort",
        "getuid", "geteuid", "getgid", "getegid", "getgroups", "getresuid", "getresgid", "getlogin",
        "setuid", "seteuid", "setgid", "setegid", "setgroups", "setreuid", "setregid", "setresuid", "setresgid",
    )
    for name in os_names:
        if hasattr(os, name):
            setattr(os, name, blocked)
            denied.append("os." + name)
    for name in ("getrlimit", "setrlimit", "prlimit", "getrusage"):
        if hasattr(resource, name):
            setattr(resource, name, blocked)
            denied.append("resource." + name)
    for module_name, names in (
        ("time", ("sleep", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "process_time", "process_time_ns", "thread_time", "thread_time_ns", "clock_gettime", "clock_gettime_ns", "clock_getres", "clock_settime", "clock_settime_ns")),
        ("_thread", ("start_new_thread", "start_new", "get_ident", "get_native_id", "interrupt_main")),
        ("signal", ("signal", "alarm", "setitimer", "getitimer", "pause", "raise_signal", "pthread_kill", "pthread_sigmask", "sigpending", "sigwait", "sigwaitinfo", "sigtimedwait")),
        ("socket", ("socket", "socketpair", "create_connection", "getaddrinfo", "gethostbyname", "gethostbyaddr")),
    ):
        module = sys.modules.get(module_name)
        if module is not None:
            for name in names:
                if hasattr(module, name):
                    setattr(module, name, blocked)
                    denied.append(module_name + "." + name)
    denied_modules = {"subprocess", "_posixsubprocess", "socket", "_socket", "ssl", "ctypes", "_ctypes", "signal", "_signal", "select", "selectors", "asyncio", "threading", "multiprocessing", "concurrent", "pty", "platform", "time"}
    def audit(event, args):
        if event == "import" and args and str(args[0]).split(".")[0] in denied_modules:
            blocked()
        if event.startswith(("subprocess.", "socket.", "ctypes.", "signal.", "_thread.", "pty.")) or event in {"os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.spawn", "os.startfile", "os.uname"}:
            blocked()
    sys.addaudithook(audit)
    return {"installed_before_subject_reads_or_compile": True,
        "patched_apis": denied, "denied_module_families": sorted(denied_modules),
        "scope": "Source-level defense in depth; exact reviewed code, not a hostile-code sandbox."}


def read_frozen(name, expected_bytes, expected_sha):
    """Only fixed local subject-source input; never a JDK/package input."""
    need(name in {row["path"] for row in FROZEN} | {"source-manifest.json"}, "unbound source name")
    fd = os.open(PREP + "/" + name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size == expected_bytes <= 65536, "bounded regular frozen source required")
        chunks = []
        remaining = expected_bytes
        while remaining:
            chunk = os.read(fd, min(4096, remaining))
            need(bool(chunk), "source ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        current = os.stat(PREP + "/" + name, follow_symlinks=False)
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        need(all(getattr(before, field) == getattr(after, field) == getattr(current, field) for field in fields), "source changed during read")
        data = b"".join(chunks)
        need(digest(data) == expected_sha, "frozen source hash differs: " + name)
        return data
    finally:
        os.close(fd)


def check(name, function):
    try:
        function()
        RESULTS.append({"name": name, "pass": True})
    except Exception as exc:
        RESULTS.append({"name": name, "pass": False, "exception_type": type(exc).__name__, "reason": str(exc)[:300]})


def refused(function):
    try:
        function()
    except (ValueError, UnicodeError):
        return
    raise AssertionError("expected pure function refusal")


def mutated(rows, change):
    value = clone(rows)
    change(value)
    return value


def run_pure_checks(subject, rows, contract):
    exact = subject["exact_manifest"]
    classify = subject["classify"]
    package = subject["selected_package"]
    md5s = subject["selected_md5"]
    check("exact safe builtin namespace", lambda: need(tuple(subject["__builtins__"]) == SAFE_NAMES, "builtin namespace drift"))
    check("exact74 baseline", lambda: need(exact(rows) is rows, "manifest result differs"))
    manifest_cases = (
        ("object manifest", lambda: {"members": rows}),
        ("missing member", lambda: rows[1:]),
        ("extra member", lambda: rows + [rows[0]]),
        ("absolute path", lambda: mutated(rows, lambda r: r[0].update(path="/bin/java"))),
        ("dotdot path", lambda: mutated(rows, lambda r: r[0].update(path="lib/../java"))),
        ("case alias", lambda: mutated(rows, lambda r: r[1].update(path="bin/JAVA"))),
        ("boolean bytes", lambda: mutated(rows, lambda r: r[0].update(bytes=True))),
        ("per-file cap plus1", lambda: mutated(rows, lambda r: r[0].update(bytes=268435457))),
        ("expected-total drift", lambda: mutated(rows, lambda r: r[0].update(bytes=r[0]["bytes"] + 1))),
        ("uppercase digest", lambda: mutated(rows, lambda r: r[0].update(sha256="A" * 64))),
        ("unordered manifest", lambda: list(reversed(rows))),
    )
    for name, make in manifest_cases:
        check("manifest refuses " + name, lambda make=make: refused(lambda: exact(make())))
    expected = rows[0]
    for name, observed, outcome in (
        ("matching", {"status": "stable-regular-file", "bytes": expected["bytes"], "sha256": expected["sha256"]}, "matches-frozen-expected-data-only"),
        ("size mismatch", {"status": "stable-regular-file", "bytes": expected["bytes"] + 1, "sha256": expected["sha256"]}, "differs-from-frozen-expected"),
        ("hash mismatch", {"status": "stable-regular-file", "bytes": expected["bytes"], "sha256": "0" * 64}, "differs-from-frozen-expected"),
        ("refused", {"status": "refused"}, "unobserved-refused"),
    ):
        check("classify " + name, lambda observed=observed, outcome=outcome: need(classify(expected, observed) == outcome, "wrong classification"))
    stanza = b"Package: temurin-17-jdk\nStatus: install ok installed\nArchitecture: amd64\nVersion: synthetic-only"
    prefix = "Package: unrelated\nDescription: café\n\n".encode("utf-8")
    for name, data, selected, start, separator in (
        ("EOF no LF", stanza, stanza, 0, None),
        ("EOF one LF", stanza + b"\n", stanza + b"\n", 0, None),
        ("blank separator", stanza + b"\n\n", stanza, 0, "\n\n"),
        ("UTF8 preceding stanza", prefix + stanza + b"\n\nPackage: another\nVersion: SECRET", stanza, len(prefix), "\n\n"),
    ):
        def span_case(data=data, selected=selected, start=start, separator=separator):
            result = package(data)
            need(result["exact_selected_stanza"].encode("utf-8") == selected, "selected bytes changed")
            need(result["selected_span"] == {"start_byte": start, "bytes": len(selected), "ends_with_lf": selected.endswith(b"\n"), "separator_after": separator}, "span metadata differs")
            need("SECRET" not in json.dumps(result), "unrelated package output escaped")
        check("package exact span " + name, span_case)
    for name, data in (
        ("duplicate stanza", stanza + b"\n\n" + stanza),
        ("duplicate field", stanza + b"\nVersion: duplicate"),
        ("missing field", stanza.replace(b"Architecture: amd64\n", b"")),
        ("name suffix", stanza.replace(b"temurin-17-jdk", b"temurin-17-jdk-extra")),
        ("CR", stanza + b"\r"), ("NUL", stanza + b"\x00"), ("invalid UTF8", stanza + b"\xff"),
    ):
        check("package refuses " + name, lambda data=data: refused(lambda: package(data)))
    padded = stanza + b"\nDescription: "
    padded += b"x" * (65536 - len(padded))
    check("package stanza cap inclusive", lambda: need(package(padded)["selected_span"]["bytes"] == 65536, "inclusive cap wrong"))
    check("package stanza cap plus1", lambda: refused(lambda: package(padded + b"x")))
    ct_target = "usr/lib/jvm/temurin-17-jdk-amd64/lib/ct.sym"
    jar_target = "usr/lib/jvm/temurin-17-jdk-amd64/lib/jrt-fs.jar"
    ct_line = "0" * 32 + "  " + ct_target + "\r\n"
    jar_line = "1" * 32 + "  " + jar_target
    def checksum_lines():
        result = md5s((ct_line + jar_line + "\n" + "2" * 32 + "  unrelated/SECRET\n").encode("ascii"))
        need(result["lib/ct.sym"]["exact_selected_line"] == ct_line, "CRLF line changed")
        need(result["lib/jrt-fs.jar"]["exact_selected_line"] == jar_line + "\n", "LF line changed")
        need("SECRET" not in json.dumps(result), "unselected checksum escaped")
        need(md5s(jar_line.encode("ascii"))["lib/jrt-fs.jar"]["exact_selected_line"] == jar_line, "EOF line changed")
    check("selected checksum exact lines only", checksum_lines)
    check("duplicate selected checksum refused", lambda: refused(lambda: md5s((ct_line + ct_line).encode("ascii"))))
    check("malformed selected checksum refused", lambda: refused(lambda: md5s(("z" * 32 + "  " + ct_target).encode("ascii"))))
    check("missing optional checksums explicit", lambda: need(all(value.get("status") == "selected-package-checksum-absent" for value in md5s(b"").values()), "absence not explicit"))
    for scenario in ("baseline", "nonraw-mismatch", "per-file-refusal", "aggregate-refusal", "raw-cap-omission", "package-refusal", "optional-md5-absent", "optional-md5-malformed"):
        check("observe in memory " + scenario, lambda scenario=scenario: observe_case(subject, rows, contract, stanza, prefix, scenario))


def observe_case(subject, rows, contract, stanza, prefix, scenario):
    """Finite synthetic callback observations; does not test real filesystem reads."""
    by_path = {row["path"]: row for row in rows}
    raw = {"lib/ct.sym": b"synthetic ct bytes", "lib/jrt-fs.jar": b"synthetic jar bytes"}
    status = prefix + stanza + (b"\nVersion: duplicate" if scenario == "package-refusal" else b"") + b"\n\nPackage: later\nVersion: SECRET"
    md5_text = "".join(hashlib.md5(raw[member], usedforsecurity=False).hexdigest() + "  usr/lib/jvm/temurin-17-jdk-amd64/" + member + "\n" for member in RAW_CAPS).encode("ascii")
    if scenario == "optional-md5-malformed":
        md5_text += md5_text
    state = {"calls": [], "retained": {}, "checkpoints": 0, "last": None, "jdk_budget_id": None}
    def read_memory(path, cap, budget, retain_cap=0, package_md5=False):
        state["calls"].append(path)
        if path.startswith(JDK):
            member = path[len(JDK):]
            need(member in by_path and cap == 268435456 and retain_cap == RAW_CAPS.get(member, 0) and package_md5 is (member in RAW_CAPS), "JDK callback request drift")
            if state["jdk_budget_id"] is None:
                state["jdk_budget_id"] = id(budget)
            need(id(budget) == state["jdk_budget_id"], "JDK aggregate budget replaced")
            expected = by_path[member]
            payload = raw.get(member)
            size = len(payload) if payload is not None else expected["bytes"]
            sha = digest(payload) if payload is not None else expected["sha256"]
            if scenario == "nonraw-mismatch" and member == "lib/classlist":
                sha = "0" * 64
            if scenario == "per-file-refusal" and member == "lib/modules":
                size = 268435457
            if scenario == "aggregate-refusal" and member == "bin/java":
                size, sha = 268435456, "0" * 64
            if scenario == "raw-cap-omission" and member == "lib/ct.sym":
                size, sha, payload = 16777217, "0" * 64, None
            if size > cap or size > budget["remaining"]:
                return {"status": "refused", "reason": "synthetic cap refusal"}, None
            budget["remaining"] -= size
            budget["actual_bytes_read"] += size
            observed = {"status": "stable-regular-file", "bytes": size, "sha256": sha}
            if package_md5 and payload is not None:
                observed["package_md5"] = hashlib.md5(payload, usedforsecurity=False).hexdigest()
            return observed, payload if payload is not None and size <= retain_cap else None
        need(package_md5 is False and id(budget) != state["jdk_budget_id"], "package callback shares JDK budget")
        if path == "/var/lib/dpkg/status":
            need(cap == retain_cap == 8388608, "status cap request drift")
            payload = status
        else:
            need(path == "/var/lib/dpkg/info/temurin-17-jdk.md5sums" and cap == retain_cap == 1048576, "metadata path/cap drift")
            if scenario == "optional-md5-absent":
                return {"status": "refused", "reason": "synthetic absent"}, None
            payload = md5_text
        return {"status": "stable-regular-file", "bytes": len(payload), "sha256": digest(payload)}, payload
    def retain_memory(member, data, actual):
        need(member in RAW_CAPS and isinstance(data, bytes) and len(data) <= RAW_CAPS[member] and len(data) == actual["bytes"] and digest(data) == actual["sha256"], "raw-copy identity/cap drift")
        need(member not in state["retained"], "duplicate raw retention")
        state["retained"][member] = data
        return {"status": "retained-stable-observed-bytes", "bytes": len(data), "sha256": digest(data)}
    def checkpoint_memory(report):
        state["checkpoints"] += 1
        state["last"] = clone(report)
    ctx = {"runtime_rows": clone(rows), "expected_manifest_identity": {"members": 74, "manifest_sha256": FROZEN[2]["sha256"]}, "selected_source": {"fixture": True}, "provider": {"fixture": True}, "python_identity": {"fixture": True}, "limits": contract["limits"], "limitations": ["Synthetic in-memory callback observations only"], "read_regular": read_memory, "hash_data": digest, "retain_archive_data": retain_memory, "checkpoint": checkpoint_memory}
    result = subject["observe"](ctx)
    report = state["last"]
    need(state["calls"] == [JDK + row["path"] for row in rows] + ["/var/lib/dpkg/status", "/var/lib/dpkg/info/temurin-17-jdk.md5sums"] and state["checkpoints"] == 78, "observation scope/checkpoint count drift")
    need(report["runtime_admitted"] is False and report["prepared13_or152_pass"] is False and report["old_focused_allowance_reused"] is False and report["child_commands"] == [] and report["owned_java_attempts"] == 0, "acceptance label drift")
    need(report["jdk_actual_bytes_read"] <= 335544320 and report["unexpected_membership_observed"] is False, "report scope drift")
    partial = scenario in {"per-file-refusal", "aggregate-refusal", "raw-cap-omission", "package-refusal"}
    need(result == (1 if partial else 0) and report["status"] == ("partial-data-observation-refusals" if partial else "complete-expected74-data-observation"), "partial/complete result drift")
    if scenario in {"per-file-refusal", "aggregate-refusal"}:
        need("lib/modules" in report["refused_members"] and report["expected_members_observed"] < 74, "cap refusal not reported")
    elif scenario == "raw-cap-omission":
        need(report["raw_archive_data"]["lib/ct.sym"]["status"] == "omitted" and "lib/ct.sym" not in state["retained"], "oversized raw data retained")
    elif scenario == "package-refusal":
        need(report["package_metadata"]["status"]["status"] == "selection-refused" and "selected" not in report["package_metadata"]["status"], "bad status selection accepted")
    else:
        need(report["expected_members_observed"] == 74, "stable member count drift")
    if scenario == "nonraw-mismatch":
        need("lib/classlist" in report["differing_members"], "nonraw mismatch lost")
    if scenario not in {"raw-cap-omission"}:
        need(set(state["retained"]) == set(RAW_CAPS), "two raw copies not preserved")
    if scenario not in {"package-refusal"}:
        selected = report["package_metadata"]["status"]["selected"]
        need(selected["selected_span"]["start_byte"] == len(prefix) and selected["selected_span"]["sha256"] == digest(stanza) and "SECRET" not in json.dumps(selected), "exact selected package bytes/hash drift")
    if scenario in {"optional-md5-absent", "optional-md5-malformed"}:
        need(all(entry["matches"] is None for entry in report["package_md5_comparisons"].values()), "unavailable optional checksum became matching")
    elif scenario != "raw-cap-omission":
        need(all(entry["matches"] is True for entry in report["package_md5_comparisons"].values()), "selected checksum association drift")


def main():
    need(sys.flags.isolated == 1 and sys.flags.dont_write_bytecode == 1 and sys.flags.no_site == 1 and len(sys.argv) == 1, "invoke exactly with -I -B -S and no script arguments")
    guards = deny_active_apis()
    report = {"schema": 1, "status": "refused", "scope": "Actual frozen observer pure functions and in-memory callbacks only; bootstrap compiled as data, never evaluated/imported/called.", "guards": guards, "source_manifest_sha256": SOURCE_MANIFEST_SHA, "frozen_sources": FROZEN, "python_version": sys.version, "checks": RESULTS, "bootstrap_executed": False, "observer_real_filesystem_callbacks_called": False, "fixed_source_input_reads": 6, "child_commands": [], "runtime_admitted": False}
    try:
        manifest = read_frozen("source-manifest.json", 923, SOURCE_MANIFEST_SHA)
        need(json.loads(manifest.decode("utf-8"))["members"] == FROZEN, "source manifest table drift")
        sources = {row["path"]: read_frozen(row["path"], row["bytes"], row["sha256"]) for row in FROZEN}
        tree = compile(sources["bootstrap.py"], "frozen-bootstrap.py", "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)
        compile(sources["bootstrap.py"], "frozen-bootstrap.py", "exec", dont_inherit=True)
        report["bootstrap_compiled_as_data_only"] = True
        assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "safe_names" for target in node.targets)]
        need(len(assignments) == 1 and isinstance(assignments[0].value, ast.Tuple) and all(isinstance(value, ast.Constant) and isinstance(value.value, str) for value in assignments[0].value.elts), "bootstrap safe_names literal shape drift")
        actual_names = tuple(value.value for value in assignments[0].value.elts)
        need(actual_names == SAFE_NAMES, "bootstrap exact builtin namespace differs")
        namespace = {"__builtins__": {name: getattr(builtins, name) for name in actual_names}, "__name__": "sealed_jdk_data_observer"}
        exec(compile(sources["observe_jdk.py"], "frozen-observe_jdk.py", "exec", dont_inherit=True), namespace)
        run_pure_checks(namespace, json.loads(sources["expected-runtime-members.json"].decode("utf-8")), json.loads(sources["contract.json"].decode("utf-8")))
        need(len(RESULTS) == EXPECTED_CASES, "pure case count differs")
        report["status"] = "passed-pure-function-checks" if all(item["pass"] for item in RESULTS) else "failed-pure-function-checks"
    except Exception as exc:
        report["exception_type"] = type(exc).__name__
        report["reason"] = str(exc)[:300]
    report["passed"] = sum(item["pass"] for item in RESULTS)
    report["failed"] = sum(not item["pass"] for item in RESULTS)
    output = json.dumps(report, sort_keys=True, allow_nan=False)
    need(len(output.encode("utf-8")) <= 32768, "check output exceeds32KiB")
    print(output)
    return 0 if report["status"] == "passed-pure-function-checks" else 1


if __name__ == "__main__":
    raise SystemExit(main())
