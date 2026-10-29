"""DRAFT only: fixed root-selected data observation bootstrap, zero child commands.
No local execution is authorized by this source preparation.
"""
import sys
sys.dont_write_bytecode = True
import os
import stat
import json
import hashlib
import resource
import builtins

PREP = "verification/android-view-api-focused-actual-review/jdk-observation-preparation"
WORKFLOW = ".github/workflows/android-view-api-jdk-data-observation.yml"
JDK = "/usr/lib/jvm/temurin-17-jdk-amd64"
TEMP = "/home/runner/work/_temp"
EXPECTED_SHA = "c75e64616ebb599f7337df7d7026286f1fd2d300347b59e28fb8a1051fdef13f"
OUTFD = None


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "duplicate JSON key")
        value[key] = item
    return value


def parse_json(data):
    return json.loads(data.decode("utf-8", "strict"), object_pairs_hook=strict_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite JSON")))


def identity(st):
    return {"device": st.st_dev, "inode": st.st_ino, "mode": st.st_mode,
        "links": st.st_nlink, "size": st.st_size,
        "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns}


def directory_identity(st):
    return (st.st_dev, st.st_ino, st.st_mode)


def open_absolute(path, flags):
    require(isinstance(path, str) and path.startswith("/") and len(path) <= 1024, "invalid absolute file path")
    parts = path[1:].split("/")
    require(parts and len(parts) <= 20 and all(p and p not in (".", "..") for p in parts), "unsafe absolute file path")
    fds = []
    edges = []
    try:
        parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        fds.append(parent)
        for index, name in enumerate(parts):
            final = index == len(parts) - 1
            selected_flags = flags if final else os.O_RDONLY | os.O_DIRECTORY
            fd = os.open(name, selected_flags | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
            fds.append(fd)
            before = os.fstat(fd)
            if not final:
                require(stat.S_ISDIR(before.st_mode), "non-directory ancestor")
            edges.append((parent, name, fd, directory_identity(before)))
            parent = fd
        return fds[-1], fds, edges
    except BaseException:
        for fd in reversed(fds):
            os.close(fd)
        raise


def close_opened(fds):
    for fd in reversed(fds):
        os.close(fd)


def check_edges(edges):
    for parent, name, fd, before in edges:
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        require(not stat.S_ISLNK(current.st_mode), "observed path became a symlink")
        require(directory_identity(current) == before == directory_identity(os.fstat(fd)), "observed path or ancestor identity changed")


def read_regular(path, cap, budget, retain_cap=0, package_md5=False):
    fds = []
    actual = {"status": "refused", "path": path}
    private_data = None
    try:
        fd, fds, edges = open_absolute(path, os.O_RDONLY)
        before = os.fstat(fd)
        actual["before"] = identity(before)
        require(stat.S_ISREG(before.st_mode), "selected file is not regular")
        require(0 <= before.st_size <= cap, "selected file exceeds its byte cap")
        require(before.st_size <= budget["remaining"], "selected file exceeds remaining aggregate byte cap")
        hasher = hashlib.sha256()
        md5 = hashlib.md5(usedforsecurity=False) if package_md5 else None
        retain = before.st_size <= retain_cap if retain_cap else False
        chunks = []
        consumed = 0
        while consumed < before.st_size:
            count = min(1048576, before.st_size - consumed, budget["remaining"])
            require(count > 0, "aggregate byte budget exhausted")
            chunk = os.read(fd, count)
            require(bool(chunk), "selected file ended before its initial size")
            consumed += len(chunk)
            budget["remaining"] -= len(chunk)
            budget["actual_bytes_read"] += len(chunk)
            hasher.update(chunk)
            if md5 is not None:
                md5.update(chunk)
            if retain:
                chunks.append(chunk)
        after = os.fstat(fd)
        actual["after"] = identity(after)
        require(identity(before) == identity(after), "selected file changed during bounded read")
        check_edges(edges)
        current = os.stat(edges[-1][1], dir_fd=edges[-1][0], follow_symlinks=False)
        require(identity(current) == identity(before), "selected file namespace metadata changed")
        actual.update({"status": "stable-regular-file", "bytes": consumed,
            "sha256": hasher.hexdigest(), "known_initial_size_read": True,
            "extra_eof_read_attempted": False})
        if md5 is not None:
            actual["package_md5"] = md5.hexdigest()
        if retain:
            private_data = b"".join(chunks)
    except (OSError, ValueError) as exc:
        actual["reason"] = str(exc)[:1024]
        actual["status"] = "refused"
        private_data = None
    finally:
        close_opened(fds)
    return actual, private_data


def mandatory_data(path, cap):
    actual, data = read_regular(path, cap, {"remaining": cap, "actual_bytes_read": 0}, retain_cap=cap)
    require(actual["status"] == "stable-regular-file" and data is not None, "required named source data refused: " + path)
    return data, actual


def write_bytes(dirfd, name, data, exclusive=True):
    require(name and "/" not in name and name not in (".", ".."), "unsafe output basename")
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=dirfd)
    try:
        offset = 0
        while offset < len(data):
            count = os.write(fd, data[offset:offset + 1048576])
            require(count > 0, "short output write")
            offset += count
    finally:
        os.close(fd)


def write_json(name, value):
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    require(len(data) <= 1048576, "JSON output exceeds1MiB cap")
    temporary = "." + name + ".next"
    write_bytes(OUTFD, temporary, data)
    os.replace(temporary, name, src_dir_fd=OUTFD, dst_dir_fd=OUTFD)


def self_limits():
    selected = (
        ("RLIMIT_CPU", 90), ("RLIMIT_AS", 536870912),
        ("RLIMIT_FSIZE", 20971520), ("RLIMIT_NOFILE", 64),
        ("RLIMIT_CORE", 0), ("RLIMIT_NPROC", 0),
    )
    applied = {}
    for name, cap in selected:
        number = getattr(resource, name)
        soft, hard = resource.getrlimit(number)
        bound = cap if hard == resource.RLIM_INFINITY else min(cap, hard)
        resource.setrlimit(number, (bound, bound))
        applied[name] = list(resource.getrlimit(number))
    return applied


def active_api_denials():
    denied = []
    def blocked(*args, **kwargs):
        raise RuntimeError("active runtime/process/network/timer API denied in data-only observer")
    # These are deliberately self/process APIs, not filesystem operations.
    names = (
        "system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp",
        "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe",
        "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
        "kill", "killpg", "pidfd_open", "wait", "wait3", "wait4", "waitid", "waitpid",
        "getpid", "getppid", "getpgrp", "getpgid", "getsid", "setsid", "setpgid",
        "getpriority", "setpriority", "sched_getaffinity", "sched_setaffinity",
        "sched_getparam", "sched_setparam", "sched_getscheduler", "sched_setscheduler",
        "sched_rr_get_interval", "times", "getloadavg", "uname", "nice", "abort",
    )
    for name in names:
        if hasattr(os, name):
            setattr(os, name, blocked)
            denied.append("os." + name)
    for name in ("getrlimit", "setrlimit", "prlimit", "getrusage"):
        if hasattr(resource, name):
            setattr(resource, name, blocked)
            denied.append("resource." + name)
    # Patch already-imported timer/thread APIs without importing those modules.
    for module_name, names in (
        ("time", ("sleep", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "process_time", "process_time_ns", "thread_time", "thread_time_ns", "clock_gettime", "clock_gettime_ns", "clock_getres", "clock_settime", "clock_settime_ns")),
        ("_thread", ("start_new_thread", "start_new", "get_ident", "get_native_id", "interrupt_main")),
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
        if event.startswith(("subprocess.", "socket.", "ctypes.", "signal.", "_thread.", "pty.")) or event in {
            "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.spawn", "os.startfile", "os.uname"}:
            blocked()
    sys.addaudithook(audit)
    return {"os_resource_and_loaded_timer_thread_apis_denied": denied,
        "audit_denied_module_families": sorted(denied_modules),
        "scope": "Source-level defense in depth, not a hostile-code sandbox or independent kernel confinement."}


def python_identity():
    require(sys.executable in ("/usr/bin/python3", "/usr/bin/python3.12"), "unselected Python executable")
    require(sys.flags.isolated == 1 and sys.flags.dont_write_bytecode == 1 and sys.flags.no_site == 1, "Python must use -I -B -S")
    alias_fd, fds, edges = open_absolute("/usr/bin", os.O_RDONLY | os.O_DIRECTORY)
    try:
        before = os.stat("python3", dir_fd=alias_fd, follow_symlinks=False)
        target = os.readlink("python3", dir_fd=alias_fd) if stat.S_ISLNK(before.st_mode) else None
        require(target in (None, "python3.12", "/usr/bin/python3.12"), "unexpected fixed Python alias target")
        resolved = "/usr/bin/python3.12" if target is not None else "/usr/bin/python3"
        data, executable = mandatory_data(resolved, 33554432)
        del data
        after = os.stat("python3", dir_fd=alias_fd, follow_symlinks=False)
        require(identity(before) == identity(after), "Python alias changed while observing executable")
        check_edges(edges)
        return {"sys_version": sys.version, "sys_executable": sys.executable,
            "flags": ["-I", "-B", "-S"], "alias": {"path": "/usr/bin/python3", "before": identity(before), "after": identity(after), "literal_target": target},
            "executable_file": executable, "runtime_admitted_by_root_not_hermetic": True}
    finally:
        close_opened(fds)


def main():
    global OUTFD
    applied = self_limits()
    env_names = ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF", "GITHUB_EVENT_NAME", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW_REF", "GITHUB_WORKFLOW_SHA", "GITHUB_WORKSPACE", "RUNNER_TEMP", "RUNNER_OS", "ImageOS", "ImageVersion")
    env = {name: os.environ.get(name, "") for name in env_names}
    require(env["GITHUB_REPOSITORY"] == "snowdamiz/mixer", "repository mismatch")
    require(env["GITHUB_REF"] == "refs/heads/main" and env["GITHUB_EVENT_NAME"] == "workflow_dispatch", "manual main dispatch required")
    require(env["GITHUB_RUN_ATTEMPT"] == "1" and env["GITHUB_RUN_ID"].isascii() and env["GITHUB_RUN_ID"].isdigit() and len(env["GITHUB_RUN_ID"]) <= 20, "one selected attempt1 only")
    require(env["RUNNER_TEMP"] == TEMP and env["RUNNER_OS"] == "Linux" and env["ImageOS"] == "ubuntu24", "fixed Ubuntu24.04 provider context required")
    require(env["ImageVersion"] and len(env["ImageVersion"]) <= 128 and all(c in "0123456789.-" for c in env["ImageVersion"]), "observed image version missing or malformed")
    workspace = env["GITHUB_WORKSPACE"]
    require(workspace == "/home/runner/work/mixer/mixer", "unexpected fixed checkout root")
    tempfd, tempfds, tempedges = open_absolute(TEMP, os.O_RDONLY | os.O_DIRECTORY)
    try:
        output_name = "mixer-jdk-observation-" + env["GITHUB_RUN_ID"] + "-1"
        os.mkdir(output_name, 0o700, dir_fd=tempfd)
        OUTFD = os.open(output_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=tempfd)
        write_json("bootstrap-receipt.json", {"schema": 1, "status": "bootstrap-started-no-observer", "self_limits": applied, "child_commands": [], "diagnostic_only": True})
        raw = os.environ.get("MIXER_ROOT_SELECTION_JSON", "").encode("utf-8")
        require(0 < len(raw) <= 65536, "bounded explicit root selection required")
        selection = parse_json(raw)
        keys = {"schema", "diagnostic_only", "dispatch_selected", "repository", "delivered_head", "branch_ref", "workflow_path", "workflow_sha256", "source_manifest_sha256", "dispatch_nonce", "run_attempt", "child_commands", "preserve_all_prior_holds", "admit_ambient_ubuntu_python_checkout_upload", "allowance"}
        require(isinstance(selection, dict) and set(selection) == keys, "exact root selection shape required")
        require(type(selection["schema"]) is int and selection["schema"] == 1 and selection["diagnostic_only"] is True and selection["dispatch_selected"] is True, "unselected diagnostic template cannot run")
        require(selection["repository"] == env["GITHUB_REPOSITORY"] and selection["branch_ref"] == env["GITHUB_REF"], "root repository/ref mismatch")
        head = selection["delivered_head"]
        require(isinstance(head, str) and len(head) == 40 and all(c in "0123456789abcdef" for c in head), "exact delivered SHA required")
        require(head == env["GITHUB_SHA"] == env["GITHUB_WORKFLOW_SHA"], "delivered/run/workflow SHA mismatch")
        require(selection["workflow_path"] == WORKFLOW and env["GITHUB_WORKFLOW_REF"] == "snowdamiz/mixer/" + WORKFLOW + "@refs/heads/main", "workflow ref mismatch")
        require(type(selection["run_attempt"]) is int and selection["run_attempt"] == 1 and selection["child_commands"] == [], "zero child commands and one attempt required")
        require(selection["preserve_all_prior_holds"] is True and selection["admit_ambient_ubuntu_python_checkout_upload"] is True, "explicit root boundary acceptance required")
        require(selection["allowance"] == {"new_diagnostic_runs": 1, "attempts": 1, "old_focused_allowance_reused": False} and type(selection["allowance"].get("new_diagnostic_runs")) is int and type(selection["allowance"].get("attempts")) is int and selection["allowance"].get("old_focused_allowance_reused") is False, "new diagnostic allowance only")
        for key in ("workflow_sha256", "source_manifest_sha256", "dispatch_nonce"):
            value = selection[key]
            require(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "invalid exact selection hash or nonce")
        manifest_data, manifest_identity = mandatory_data(workspace + "/" + PREP + "/source-manifest.json", 65536)
        require(digest(manifest_data) == selection["source_manifest_sha256"], "source manifest differs from selected hash")
        manifest = parse_json(manifest_data)
        expected_names = ["bootstrap.py", "contract.json", "expected-runtime-members.json", "observe_jdk.py", "workflow-draft.yml"]
        require(set(manifest) == {"schema", "scope", "members"} and manifest["schema"] == 1 and [r["path"] for r in manifest["members"]] == expected_names, "fixed source manifest shape mismatch")
        sources = {}
        source_ids = {}
        for row in manifest["members"]:
            require(set(row) == {"path", "bytes", "sha256"}, "invalid source manifest row")
            data, actual = mandatory_data(workspace + "/" + PREP + "/" + row["path"], 1048576)
            require(len(data) == row["bytes"] and digest(data) == row["sha256"], "selected source member changed: " + row["path"])
            sources[row["path"]] = data
            source_ids[row["path"]] = actual
        installed, workflow_id = mandatory_data(workspace + "/" + WORKFLOW, 65536)
        require(installed == sources["workflow-draft.yml"] and digest(installed) == selection["workflow_sha256"], "installed workflow differs from selected reviewed bytes")
        contract = parse_json(sources["contract.json"])
        nonce = selection["dispatch_nonce"]
        require(nonce == contract["selection"]["fresh_nonce"], "fresh exact candidate nonce mismatch")
        require(contract["selection"]["dispatch_selected"] is False and contract["selection"]["delivered_head"] is None, "source contract must stay unbound")
        runtime_data = sources["expected-runtime-members.json"]
        require(len(runtime_data) == 10885 and digest(runtime_data) == EXPECTED_SHA, "frozen74-member runtime manifest changed")
        source_data, original_manifest_id = mandatory_data(workspace + "/verification/android-view-api-boundary-linux-tool-profile/runtime-members.json", 65536)
        require(source_data == runtime_data, "original frozen runtime manifest differs")
        require(contract["expected_manifest"]["sha256"] == EXPECTED_SHA and contract["fixed_provider"]["jdk_root"] == JDK, "fixed contract profile changed")
        reservation = {"schema": 1, "dispatch_nonce": nonce, "github_sha": head, "run_id": env["GITHUB_RUN_ID"], "run_attempt": 1, "status": "reserved-once-zero-child-commands-no-restart", "child_commands": []}
        reservation_bytes = (json.dumps(reservation, sort_keys=True) + "\n").encode("utf-8")
        # This O_EXCL marker is deliberately outside the run output; cross-run one-shot
        # enforcement still requires root's dispatch ledger on fresh hosted machines.
        write_bytes(tempfd, ".mixer-jdk-observation-" + nonce + ".reservation.json", reservation_bytes)
        write_bytes(OUTFD, "nonce-reservation.json", reservation_bytes)
        write_json("root-selection.json", selection)
        check_edges(tempedges)
        python = python_identity()
        denials = active_api_denials()
        provider = {"runner_label_from_reviewed_workflow": "ubuntu-24.04", "observed_environment": {name: env[name] for name in ("RUNNER_OS", "ImageOS", "ImageVersion")}, "old_run_image_context_only": "20261025.353.1", "same_image_as_old_run_assumed": False}
        selected_source = {"delivered_head": head, "workflow_path": WORKFLOW, "workflow_sha256": digest(installed), "source_manifest_sha256": digest(manifest_data), "source_members": source_ids, "workflow_identity": workflow_id, "source_manifest_identity": manifest_identity, "original_runtime_manifest_identity": original_manifest_id, "run_id": env["GITHUB_RUN_ID"], "run_attempt": 1, "dispatch_nonce": nonce}
        bootstrap_receipt = {"schema": 1, "status": "guards-installed-before-sealed-observer", "diagnostic_only": True, "child_commands": [], "self_limits": applied, "python": python, "provider": provider, "active_denials": denials, "selected_source": selected_source}
        write_json("bootstrap-receipt.json", bootstrap_receipt)
        rows = parse_json(runtime_data)
        allowed_observation_paths = {JDK + "/" + row["path"] for row in rows if isinstance(row, dict) and isinstance(row.get("path"), str)} | {"/var/lib/dpkg/status", "/var/lib/dpkg/info/temurin-17-jdk.md5sums"}
        def scoped_read(path, cap, budget, retain_cap=0, package_md5=False):
            require(path in allowed_observation_paths, "observer file read outside exact allowlist")
            return read_regular(path, cap, budget, retain_cap, package_md5)
        def retain_archive_data(member, data, actual):
            selected = {"lib/ct.sym": ("ct.sym.raw-data.bin", 16777216), "lib/jrt-fs.jar": ("jrt-fs.jar.raw-data.bin", 1048576)}
            require(member in selected, "raw retention outside the two selected archive-data paths")
            name, cap = selected[member]
            require(isinstance(data, bytes) and len(data) <= cap and len(data) == actual["bytes"] and digest(data) == actual["sha256"], "raw archive data retention identity/cap mismatch")
            write_bytes(OUTFD, name, data)
            return {"status": "retained-stable-observed-bytes", "path": name, "source": member, "bytes": len(data), "sha256": digest(data), "mode": "0600-data-only", "archive_inspection_performed": False}
        ctx = {"runtime_rows": rows, "expected_manifest_identity": {"members": 74, "expected_bytes": 198674633, "manifest_sha256": EXPECTED_SHA}, "selected_source": selected_source, "provider": provider, "python_identity": python, "limits": contract["limits"], "limitations": contract["limitations"], "read_regular": scoped_read, "hash_data": digest, "retain_archive_data": retain_archive_data, "checkpoint": lambda report: write_json("observation.json", report)}
        safe_names = ("isinstance", "list", "dict", "set", "len", "any", "all", "type", "int", "str", "sorted", "ValueError", "UnicodeError", "bool", "next")
        namespace = {"__builtins__": {name: getattr(builtins, name) for name in safe_names}, "__name__": "sealed_jdk_data_observer"}
        # Execute only already-hashed fixed observer bytes in this interpreter;
        # no module search, bytecode file, native loader, child, or script argv runner.
        exec(compile(sources["observe_jdk.py"], PREP + "/observe_jdk.py", "exec"), namespace)
        result = namespace["observe"](ctx)
        bootstrap_receipt["status"] = "sealed-observer-returned-data-only"
        bootstrap_receipt["observer_exit_code"] = result
        write_json("bootstrap-receipt.json", bootstrap_receipt)
        print(json.dumps({"diagnostic_only": True, "owned_child_commands": 0, "exit_code": result}, sort_keys=True))
        return result
    except Exception as exc:
        if OUTFD is not None:
            try:
                write_json("bootstrap-refusal.json", {"schema": 1, "status": "refused-data-only", "exception_type": type(exc).__name__, "reason": str(exc)[:1024], "child_commands": [], "runtime_admitted": False})
            except Exception:
                pass
        raise
    finally:
        if OUTFD is not None:
            os.close(OUTFD)
            OUTFD = None
        close_opened(tempfds)


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        # An already-written checkpoint survives ordinary later failures. Provider
        # kill or a blocking filesystem syscall may prevent a final receipt.
        if OUTFD is not None:
            try:
                write_json("bootstrap-refusal.json", {"schema": 1, "status": "refused-data-only", "exception_type": type(exc).__name__, "reason": str(exc)[:1024], "child_commands": [], "runtime_admitted": False})
            except Exception:
                pass
        print(json.dumps({"status": "refused-data-only", "exception_type": type(exc).__name__, "reason": str(exc)[:1024], "child_commands": []}, sort_keys=True))
        code = 1
    raise SystemExit(code)
