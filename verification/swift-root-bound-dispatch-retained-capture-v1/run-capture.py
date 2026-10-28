"""One root-released alternate diagnostic retained IR/assembly capture; never a host run."""
import time
START = time.monotonic()
from pathlib import Path
import errno
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import traceback

ROOT = Path("/Users/andreyyurlov/Documents/dev/mixer")
LANE = ROOT / "verification/swift-root-bound-dispatch-retained-capture-v1"
SCRIPT = LANE / "run-capture.py"
OUT = LANE / "runtime"
BASE_PLAN = LANE / "base-capture-plan.json"
BASE_PLAN_SHA = "15413684daf6815fbc9773c7fecf669f035768116524e567a841bd571c3f31c8"
BASE_ARGV_SHA = "799f61fd0bff3d5eba3849b784e7bc7b699a5ee84a2a814f298f407befb28e75"
PLAN = LANE / "plan.json"
PLAN_SHA = "1a7eb62837ade6b2f8256f64111bb11bc57fb216308b0131785a3990d744a601"
RELEASE = ROOT / "verification/swift-semantic-adapter-root-review/dispatch-retained-physical-capture-release.json"
PYTHON = "/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14"
BUILD = LANE / "command"
TMP = BUILD / "tmp"
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
SEEN = []
SIGNAL_OVERFLOW = False
OWNED = []
ERRORS = []
PINS = {}
BUILD_IDENTITY = None
LIVE_MAX_MEMBERS = 0
LIVE_MAX_BYTES = 0


def observe_signal(number, _frame):
    global SIGNAL_OVERFLOW
    if len(SEEN) < 64:
        SEEN.append(number)
    else:
        SIGNAL_OVERFLOW = True


def require(value, message):
    if not value:
        raise RuntimeError(message)


def deadline(offset):
    if time.monotonic() - START >= offset:
        raise RuntimeError("deadline exceeded: " + str(offset))


def relative(base, name):
    require(type(name) is str and name and "\\" not in name, "invalid relative pin path")
    value = Path(name)
    require(not value.is_absolute() and all(part not in ("", ".", "..") for part in name.split("/")), "escaping pin path")
    return base / value


def regular(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode), "non-regular pin: " + str(path))
    # Refuse redirected parent paths, including symlinks under the checkout.
    require(path.resolve(strict=True) == path, "redirected pin path: " + str(path))
    return info


def digest(path, offset):
    deadline(offset)
    info = regular(path)
    h = hashlib.sha256()
    count = 0
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), "pin changed during open")
        while chunk := handle.read(262144):
            deadline(offset)
            count += len(chunk)
            require(count <= info.st_size, "pin grew during hash")
            h.update(chunk)
        after = os.fstat(handle.fileno())
    require(count == info.st_size and (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
            (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns), "pin changed during hash")
    deadline(offset)
    return h.hexdigest()


def control(path, expected=None):
    deadline(44)
    info = regular(path)
    require(info.st_size <= 1048576, "control size cap")
    with path.open("rb") as handle:
        raw = handle.read(1048577)
    require(len(raw) == info.st_size and len(raw) <= 1048576, "control size changed")
    sha = hashlib.sha256(raw).hexdigest()
    if expected is not None:
        require(sha == expected, "control hash: " + str(path))

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate control key")
            result[key] = value
        return result

    result = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    require(type(result) is dict, "control must be an object")
    add_pin(path, {"bytes": len(raw), "sha256": sha})
    return result


def add_pin(path, item):
    require(type(item["bytes"]) is int and 0 <= item["bytes"] <= 1073741824, "pin byte bound")
    require(type(item["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", item["sha256"]), "pin hash syntax")
    row = {"bytes": item["bytes"], "sha256": item["sha256"]}
    name = str(path)
    require(name not in PINS or PINS[name] == row, "conflicting pin: " + name)
    PINS[name] = row
    require(len(PINS) <= 512 and sum(value["bytes"] for value in PINS.values()) <= 4294967296, "aggregate input pin bound")


def members(base, seal):
    rows = seal["members"]
    require(type(rows) is list and len(rows) == seal["member_count"] <= 64, "seal member count")
    names = [row["path"] for row in rows]
    require(len(set(names)) == len(names), "duplicate sealed member")
    for row in rows:
        add_pin(relative(base, row["path"]), row)
    tree = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    require(tree == seal["tree_sha256"], "seal member tree")


def verify_pins(offset):
    observed = []
    for name, item in sorted(PINS.items()):
        path = Path(name)
        require(regular(path).st_size == item["bytes"], "pin size: " + name)
        sha = digest(path, offset)
        require(sha == item["sha256"], "pin hash: " + name)
        observed.append({"path": name, "bytes": item["bytes"], "sha256": sha})
    return observed


def save(name, value):
    deadline(55)
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    require(len(raw) <= 1048576, "evidence JSON bound")
    with (OUT / name).open("xb") as handle:
        handle.write(raw)
    deadline(55)


def generated_inventory(offset, hash_files=True, live=False):
    global LIVE_MAX_MEMBERS, LIVE_MAX_BYTES
    rows, pending, count, size = [], [BUILD], 0, 0
    root_info = BUILD.lstat()
    require(stat.S_ISDIR(root_info.st_mode) and BUILD.resolve() == BUILD and
            (root_info.st_dev, root_info.st_ino) == BUILD_IDENTITY, "owned directory redirected/replaced")
    while pending:
        deadline(offset)
        directory = pending.pop()
        try:
            entries = os.scandir(directory)
        except FileNotFoundError:
            require(live, "closed generated directory disappeared")
            continue
        with entries:
            for entry in entries:
                deadline(offset)
                count += 1
                require(count <= 64, "generated member cap")
                path = Path(entry.path)
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    require(live, "closed generated namespace changed")
                    continue
                row = {"path": str(path.relative_to(BUILD)), "bytes": info.st_size if stat.S_ISREG(info.st_mode) else 0}
                if stat.S_ISDIR(info.st_mode):
                    row["type"] = "directory"
                    pending.append(path)
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "generated symlink, special file, or shared hard link")
                    size += info.st_size
                    require(size <= 268435456, "generated byte cap")
                    row["type"] = "file"
                rows.append(row)
    # Complete bounded membership/type/size traversal precedes all file hashing.
    LIVE_MAX_MEMBERS = max(LIVE_MAX_MEMBERS, count)
    LIVE_MAX_BYTES = max(LIVE_MAX_BYTES, size)
    if hash_files:
        for row in rows:
            if row["type"] == "file":
                row["sha256"] = digest(BUILD / row["path"], offset)
    return {"members": sorted(rows, key=lambda row: row["path"]), "member_count": count, "file_bytes": size}


def preserve_generated(offset):
    before = generated_inventory(offset)
    destination = OUT / "generated"
    destination.mkdir(exist_ok=False)
    copied = []
    for row in before["members"]:
        deadline(offset)
        target = relative(destination, row["path"])
        if row["type"] == "directory":
            target.mkdir(parents=True, exist_ok=True)
            continue
        source = relative(BUILD, row["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        info = regular(source)
        require(info.st_size == row["bytes"] and info.st_nlink == 1, "artifact size/link changed before retention")
        h = hashlib.sha256()
        count = 0
        with source.open("rb") as reader, target.open("xb") as writer:
            opened = os.fstat(reader.fileno())
            require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), "artifact changed during open")
            while chunk := reader.read(min(262144, row["bytes"] - count + 1)):
                deadline(offset)
                require(count + len(chunk) <= row["bytes"], "artifact grew during retention")
                h.update(chunk)
                writer.write(chunk)
                count += len(chunk)
            after = os.fstat(reader.fileno())
        require(count == row["bytes"] and h.hexdigest() == row["sha256"] and
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
                (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns), "retained memory/source bytes changed")
        require(digest(target, offset) == row["sha256"], "retained copy hash")
        copied.append({"path": str(target.relative_to(OUT)), "bytes": count, "sha256": h.hexdigest()})
    after = generated_inventory(offset)
    require(before == after, "generated files changed across retention")
    return before, copied


class OwnedPopen(subprocess.Popen):
    def __del__(self):
        # Popen's destructor may poll/reap an unresolved child implicitly. All
        # observations/reaping here must stay explicit, especially after EPERM.
        pass


def call(record, operation, function):
    require(not record.get("permission_refusal"), "sticky permission refusal; no further custody syscall")
    record["active_syscall"] = operation
    try:
        return function()
    except OSError as error:
        record.setdefault("syscall_errors", []).append({"operation": operation, "errno": error.errno,
            "message": str(error), "stack": traceback.format_exc(limit=6)})
        if error.errno in (errno.EPERM, errno.EACCES):
            record["permission_refusal"] = True
        raise


def exited(record):
    require(not record.get("reaped"), "completion observation after reap forbidden")
    result = call(record, "waitid exact child WEXITED|WNOHANG|WNOWAIT",
                  lambda: os.waitid(os.P_PID, record["pid"], os.WEXITED | os.WNOHANG | os.WNOWAIT))
    if result is not None:
        require(result.si_pid == record["pid"] and result.si_code in (os.CLD_EXITED, os.CLD_KILLED, os.CLD_DUMPED), "unexpected completion proof")
        record["completion_observation"] = {"pid": result.si_pid, "code": result.si_code,
            "status": result.si_status, "signal": result.si_signo, "seconds": time.monotonic() - START}
    return result is not None


def group_absent(record):
    def probe():
        try:
            os.killpg(record["pid"], 0)
            return False
        except ProcessLookupError:
            return True
    return call(record, "killpg exact owned group zero-signal absence observation", probe)


def reap_completed(record):
    require(record.get("custody") and record.get("completion_observation") and not record.get("reaped"), "reap requires exact completed child")
    call(record, "Popen.wait only after WNOWAIT completion proof", lambda: record["child"].wait(timeout=0))
    record.update(reaped=True, returncode=record["child"].returncode, reap_seconds=time.monotonic() - START)
    # No active signal is permitted after completion/reap. A surviving or reused
    # numeric group supplies no authority; only observe absence until deadline.
    while not group_absent(record):
        deadline(49)
        time.sleep(0.005)
    record.update(group_absent=True, group_absent_seconds=time.monotonic() - START)
    return True


def close(record):
    if record.get("permission_refusal") or record.get("custody_uncertain"):
        return False
    if record.get("reaped"):
        # Successful absence is terminal; do not probe a potentially reused ID.
        return record.get("group_absent", False)
    if not record.get("custody"):
        return False
    deadline(49)
    if exited(record):
        record["cleanup_path"] = "completed-child-no-signals"
        return reap_completed(record)
    record["cleanup_path"] = "still-running-owned-child"
    for sig, grace in ((signal.SIGTERM, 0.1), (signal.SIGKILL, 0.0)):
        deadline(49)
        if exited(record):
            return reap_completed(record)
        try:
            call(record, "killpg exact owned group " + sig.name, lambda: os.killpg(record["pid"], sig))
            record.setdefault("signals", []).append({"signal": sig.name, "seconds": time.monotonic() - START})
        except ProcessLookupError:
            record["custody_uncertain"] = True
            return False
        until = min(START + 49, time.monotonic() + grace)
        while time.monotonic() < until:
            if exited(record):
                return reap_completed(record)
            time.sleep(0.005)
    while not exited(record):
        deadline(49)
        time.sleep(0.005)
    return reap_completed(record)


def command(plan):
    deadline(44)
    require(not SEEN and not OWNED, "signal before command or attempted retry")
    record = {"kind": "compiler-capture", "argv": plan["argv"], "environment": plan["environment"],
              "cwd": plan["cwd"], "start_seconds": time.monotonic() - START}
    # Record exists immediately when Popen returns, before any custody syscall.
    child = OwnedPopen(plan["argv"], cwd=plan["cwd"], env=plan["environment"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    record.update(child=child, pid=child.pid)
    OWNED.append(record)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    selector = selectors.DefaultSelector()
    try:
        record.update(pgid=call(record, "getpgid exact child", lambda: os.getpgid(child.pid)),
                      sid=call(record, "getsid exact child", lambda: os.getsid(child.pid)))
        record["custody"] = record["pid"] == record["pgid"] == record["sid"]
        require(record["custody"], "child group/session identity mismatch")
        for key, stream in (("stdout", child.stdout), ("stderr", child.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, key)
        while selector.get_map() or not record.get("reaped"):
            deadline(44)
            require(not SEEN, "signal during command")
            generated_inventory(44, hash_files=False, live=True)
            if not record.get("reaped") and exited(record):
                record["cleanup_path"] = "completed-child-no-signals"
                require(reap_completed(record), "unknown child closure")
            for key, _ in selector.select(0.025):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = buffers[key.data]
                cap = 1048576 if key.data == "stdout" else 2097152
                room = cap - len(target)
                target.extend(chunk[:room])
                if len(chunk) > room:
                    record["output_truncated"] = True
                    raise RuntimeError(key.data + " output cap exceeded")
        require(record["returncode"] == 0, "compiler-capture unexpected exit")
        record["full_streams_captured"] = True
    finally:
        selector.close()
        for stream in (child.stdout, child.stderr):
            stream.close()
        for key, data in buffers.items():
            name = "compile." + key
            with (OUT / name).open("xb") as handle:
                handle.write(data)
            record[key] = {"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        record["end_seconds"] = time.monotonic() - START
    return buffers


def check_output(buffers, policy):
    require(not buffers["stdout"], "unexpected stdout")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate diagnostic key")
            result[key] = value
        return result
    records = []
    raw = bytes(buffers["stderr"])
    require(raw.endswith(b"\n") and len(raw) <= 2097152, "diagnostic stream framing/bound")
    for line in raw.splitlines():
        deadline(44)
        require(line and len(records) < 4, "missing/extra diagnostic record")
        records.append(json.loads(line.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))))
    require(json.dumps(records, sort_keys=True, separators=(",", ":")) ==
            json.dumps(policy["records"], sort_keys=True, separators=(",", ":")), "exact source146 diagnostics differ")
    require(len(records) == 4 and [value["level"] for value in records] == ["warning"] * 4 and
            records[-1]["message"] == "3 warnings emitted", "exact three baseline warnings and summary required")
    return {"warning_objects": 3, "success_summary_objects": 1,
            "policy_sha256": PINS[str(LANE / "diagnostic-policy.json")]["sha256"],
            "actual_memory_bytes": len(raw), "actual_memory_sha256": hashlib.sha256(raw).hexdigest()}


def prepare():
    require(__debug__ and sys.dont_write_bytecode and Path(__file__).absolute() == SCRIPT and Path.cwd() == ROOT, "exact non-optimized -B controller/cwd required")
    require(str(Path(sys.executable).resolve()) == PYTHON, "controller interpreter differs from pinned Python")
    require(sys.argv == [str(SCRIPT)], "controller accepts no arguments")
    base_plan = control(BASE_PLAN, BASE_PLAN_SHA)
    plan = control(PLAN, PLAN_SHA)
    release = control(RELEASE)
    require(type(release["schema"]) is int and release["schema"] == 1 and
            type(release["compiler_invocations"]) is int and release["compiler_invocations"] == 1 and
            type(release["automatic_retries"]) is int and release["automatic_retries"] == 0 and
            release["compiler_lane_released"] is True and release["reserved_output_authorized"] is True,
            "root one-shot compiler and exact output reservation release required")
    require(release["base_capture_plan_sha256"] == BASE_PLAN_SHA and release["controller_plan_sha256"] == PLAN_SHA and
            release["argv_sha256"] == BASE_ARGV_SHA and release["independent_source_review_accepted"] is True and
            release["semantic_map_approved"] is False and release["actual_verifier_input_run_released"] is False,
            "root capture-only release bindings")
    packet = control(LANE / "seal.json", release["capture_packet_seal_sha256"])
    members(LANE, packet)
    require(packet["controller_plan_sha256"] == PLAN_SHA and packet["base_capture_plan_sha256"] == BASE_PLAN_SHA and
            packet["complete_capacity_accepted"] is False, "packet plan/scope binding")
    manifest = control(LANE / "input-manifest.json")
    require(type(manifest["inputs"]) is list and len(manifest["inputs"]) <= 384, "approved input manifest bound")
    for row in manifest["inputs"]:
        path = Path(row["path"])
        add_pin(path if path.is_absolute() else relative(ROOT, row["path"]), row)
    review_row = release["independent_source_review"]
    review_path = relative(ROOT, review_row["path"])
    require(review_row["path"].startswith("verification/") and review_path.name == "seal.json" and
            regular(review_path).st_size == review_row["bytes"], "independent review seal path/size")
    review = control(review_path, review_row["sha256"])
    members(review_path.parent, review)
    require(release["independent_source_review_subject"] == {"base_capture_plan_sha256": BASE_PLAN_SHA,
            "controller_plan_sha256": PLAN_SHA, "controller_sha256": release["controller_sha256"],
            "capture_packet_seal_sha256": release["capture_packet_seal_sha256"]}, "root-approved review subject")
    add_pin(SCRIPT, {"bytes": regular(SCRIPT).st_size, "sha256": release["controller_sha256"]})
    add_pin(Path(PYTHON), plan["python_tool"])
    for key in ("argv", "environment", "cwd", "bounds", "source_directory", "source_tree_sha256", "source_manifest", "compiler", "toolchain_manifest", "SDK_manifest"):
        require(json.dumps(plan[key], sort_keys=True) == json.dumps(base_plan[key], sort_keys=True), "frozen capture field changed: " + key)
    require(hashlib.sha256(json.dumps(plan["argv"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == BASE_ARGV_SHA,
            "exact frozen argv digest")
    require(plan["cwd"] == str(ROOT) and base_plan["owned_output_directory"] == str(BUILD) and
            plan["environment"]["TMPDIR"] == str(TMP), "predeclared root-owned output reservation")
    require(dict(os.environ) == plan["controller_environment"], "exact eight-key controller environment required")
    require(not os.path.lexists(BUILD) and not os.path.lexists(OUT), "one-shot output already exists; never retry or overwrite")
    require(sys.version == plan["python_version_from_this_preparation"], "pinned Python version differs")
    source_manifest = control(ROOT / plan["source_manifest"]["path"], plan["source_manifest"]["sha256"])
    require(source_manifest["member_count"] == len(source_manifest["members"]) == 146 and
            source_manifest["tree_sha256"] == plan["source_tree_sha256"], "original source146 manifest")
    source_tree = hashlib.sha256(json.dumps(source_manifest["members"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(source_tree == plan["source_tree_sha256"], "original source tree digest")
    for row in source_manifest["members"]:
        add_pin(relative(Path(plan["source_directory"]), row["path"]), row)
    toolchain = control(ROOT / plan["toolchain_manifest"]["path"], plan["toolchain_manifest"]["sha256"])
    require(type(toolchain["members"]) is list and len(toolchain["members"]) == 67, "approved compiler/sysroot member set")
    for row in toolchain["members"]:
        add_pin(relative(Path(toolchain["root"]), row["path"]), row)
    sdk = control(ROOT / plan["SDK_manifest"]["path"], plan["SDK_manifest"]["sha256"])
    require(str(Path(sdk["requested"]).resolve(strict=True)) == sdk["resolved"], "approved SDK path resolution")
    for row in sdk["settings"]:
        add_pin(Path(row["path"]), row)
    policy = control(LANE / "diagnostic-policy.json")
    require(policy["schema"] == 1 and policy["status"] == "frozen-exact-source-bound-baseline-diagnostics" and
            policy["source_tree"] == plan["source_tree_sha256"] and len(policy["records"]) == 4, "prospective exact diagnostic policy")
    frontier = control(ROOT / plan["frontier"]["path"], plan["frontier"]["sha256"])
    require([row["id"] for row in frontier["targets"]] == ["Caller", "Closure", "Dispatch", "Body"], "four original target identities")
    return plan, packet, policy, frontier, release


def main():
    global BUILD_IDENTITY
    for sig in SIGNALS:
        signal.signal(sig, observe_signal)
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    # Unreleased/invalid preparation fails before creating output or any child.
    plan, packet, policy, frontier, release = prepare()
    outcome = {"schema": 1, "plan_sha256": PLAN_SHA, "base_plan_sha256": BASE_PLAN_SHA,
               "packet_seal_sha256": release["capture_packet_seal_sha256"], "controller_environment": dict(os.environ),
               "packet_tree_sha256": packet["tree_sha256"], "independent_source_review": release["independent_source_review"],
               "all_results_local_geometry_only": True, "complete_capacity_accepted": False,
               "alternate_diagnostic_configuration_only": True, "original_capture_qualified": False, "runtime_admission_accepted": False,
               "physical_capacity_prices_backings_root_funding_product_GA_accepted": False,
               "source_tree_sha256": plan["source_tree_sha256"], "python_version": sys.version,
               "python_tool": plan["python_tool"], "controller_sha256": release["controller_sha256"],
               "compiler_version_from_prior_pinned_receipt": plan["version_from_prior_pinned_receipt"], "automatic_retries": 0,
               "frontier_complete": False, "frontier_status": "incomplete-until-independent-actual-target-mapping",
               "frontier_targets": [{"id": row["id"], "source": row["source"], "mapping": "unresolved"} for row in frontier["targets"]],
               "missing_private_DCE_or_ambiguous_targets_cannot_complete_frontier": True}
    OUT.mkdir(exist_ok=False)
    created_build = False
    passed = False
    try:
        outcome["pins_before"] = verify_pins(44)
        require(not SEEN, "signal during preflight")
        BUILD.mkdir(exist_ok=False)
        created_build = True
        info = BUILD.lstat()
        BUILD_IDENTITY = (info.st_dev, info.st_ino)
        TMP.mkdir(exist_ok=False)
        require(list(BUILD.iterdir()) == [TMP] and not list(TMP.iterdir()), "fresh command/tmp only")
        buffers = command(plan)
        outcome["diagnostics"] = check_output(buffers, policy)
    except BaseException as error:
        ERRORS.append(type(error).__name__ + ": " + str(error) + "\n" + traceback.format_exc(limit=8))
    finally:
        for record in OWNED:
            try:
                if not close(record):
                    ERRORS.append("unknown owned child/group closure; artifacts preserved")
            except BaseException as error:
                ERRORS.append("cleanup: " + repr(error) + "\n" + traceback.format_exc(limit=8))
        closed = len(OWNED) == 1 and all(r.get("custody") and r.get("completion_observation") and
                  r.get("reaped") and r.get("group_absent") and not r.get("permission_refusal") for r in OWNED)
        try:
            deadline(49)
            if created_build and closed:
                outcome["generated"], outcome["retained_generated_files"] = preserve_generated(49)
                required = {"generated/dispatch.ll", "generated/dispatch.s"}
                retained = {row["path"]: row for row in outcome["retained_generated_files"]}
                require(required <= set(retained) and all(retained[name]["bytes"] > 0 for name in required), "missing/empty IR or assembly artifact")
                shutil.rmtree(BUILD)
                deadline(49)
                outcome["generated_directory_removed"] = not os.path.lexists(BUILD)
            else:
                outcome["generated_inventory_deferred_for_uncertain_closure"] = created_build
                outcome["generated_directory_removed"] = False
            outcome["pins_after"] = verify_pins(53.5)
            require(outcome.get("pins_before") == outcome["pins_after"], "before/after pin inventory differs")
            outcome["all_pins_rechecked"] = True
            for row in outcome.get("retained_generated_files", []):
                require(regular(relative(OUT, row["path"])).st_size == row["bytes"] and
                        digest(relative(OUT, row["path"]), 53.5) == row["sha256"], "retained artifact changed after cleanup")
            for record in OWNED:
                for name in ("stdout", "stderr"):
                    row = record[name]
                    require(regular(relative(OUT, row["file"])).st_size == row["bytes"] and
                            digest(relative(OUT, row["file"]), 53.5) == row["sha256"], "saved compiler stream differs from captured memory")
        except BaseException as error:
            ERRORS.append("post: " + repr(error) + "\n" + traceback.format_exc(limit=8))
        outcome.update(commands=[{k: v for k, v in r.items() if k != "child"} for r in OWNED],
                       errors=ERRORS, owned_groups_closed=closed, observed_live_max_members=LIVE_MAX_MEMBERS,
                       observed_live_max_bytes=LIVE_MAX_BYTES, signal_record_overflow=SIGNAL_OVERFLOW,
                       elapsed_before_observation_seconds=time.monotonic() - START)
        raw_complete = (not ERRORS and closed and outcome.get("diagnostics") is not None and
                        outcome.get("all_pins_rechecked") is True and outcome.get("generated_directory_removed") is True and
                        OWNED[0].get("full_streams_captured") is True and not OWNED[0].get("output_truncated"))
        output_rows = []
        if raw_complete:
            retained = {row["path"]: row for row in outcome["retained_generated_files"]}
            for name, path in (("ir", "generated/dispatch.ll"), ("asm", "generated/dispatch.s")):
                row = retained[path]
                output_rows.append({"name": name, "bytes": row["bytes"], "sha256": row["sha256"]})
            for name in ("stdout", "stderr"):
                row = OWNED[0][name]
                output_rows.append({"name": name, "bytes": row["bytes"], "sha256": row["sha256"]})
        capture_observation = {"schema": 1, "status": "captured-artifacts-only", "binding": plan["verifier_binding"],
            "alternate_diagnostic_configuration_only": True, "original_capture_qualified": False, "runtime_admission_accepted": False,
            "compiler_exit": OWNED[0].get("returncode") if OWNED else None, "outputs": output_rows,
            "source_manifest_sha256": plan["source_manifest"]["sha256"], "owned_groups_closed": closed,
            "cleanup_complete": outcome.get("generated_directory_removed") is True, "bounds_met": raw_complete,
            "truncated": any(row.get("output_truncated") for row in OWNED), "capture_complete": raw_complete}
        save("capture-observation.json", capture_observation)
        save("observations.json", outcome)
        observations_sha = None
        capture_observation_sha = None
        finalization_errors = []
        try:
            observations_sha = digest(OUT / "observations.json", 53.5)
            capture_observation_sha = digest(OUT / "capture-observation.json", 53.5)
        except BaseException as error:
            finalization_errors.append("observation hash: " + repr(error))
        # All hashing/observation precedes this reviewed one-way signal cutoff.
        signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        cutoff = time.monotonic() - START
        observed = SEEN + [int(sig) for sig in signal.sigpending() if sig in SIGNALS]
        for sig in SIGNALS:
            signal.signal(sig, signal.SIG_IGN)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, SIGNALS)
        passed = (not ERRORS and not finalization_errors and not observed and not SIGNAL_OVERFLOW and cutoff < 53.5 and closed and
                  raw_complete and outcome.get("all_pins_rechecked") is True and
                  outcome.get("generated_directory_removed") is True and
                  OWNED[0].get("full_streams_captured") is True and not OWNED[0].get("output_truncated"))
        save("receipt.json", {"schema": 1, "status": "captured-artifacts-only" if passed else "failed", "plan_sha256": PLAN_SHA,
            "base_plan_sha256": BASE_PLAN_SHA,
            "packet_seal_sha256": release["capture_packet_seal_sha256"], "controller_sha256": release["controller_sha256"],
            "signal_cutoff_seconds": cutoff, "observed_signals": observed, "observations_sha256": observations_sha,
            "capture_observation_sha256": capture_observation_sha, "frontier_complete": False,
            "signal_record_overflow": SIGNAL_OVERFLOW,
            "finalization_errors": finalization_errors,
            "signal_scope": "Observed/pending through the one-way cutoff after all hashing; later signals outside this receipt.",
            "all_results_local_geometry_only": True, "complete_capacity_accepted": False,
            "alternate_diagnostic_configuration_only": True, "original_capture_qualified": False, "runtime_admission_accepted": False,
            "physical_capacity_prices_backings_root_funding_product_GA_accepted": False})
        print(json.dumps({"status": "captured-artifacts-only" if passed else "failed", "compiler_invocations": len(OWNED),
                          "elapsed_seconds": time.monotonic() - START, "receipt": str(OUT / "receipt.json")}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
