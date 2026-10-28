"""Root-released, one-shot synthetic16 host tests; never actual input or capture."""
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
RUNNER = ROOT / "verification/swift-physical-verifier-host-runner-2"
SCRIPT = RUNNER / "run-synthetic16.py"
OUT = RUNNER / "runtime"
LANE = ROOT / "verification/swift-root-bound-dispatch-physical-evidence-v2"
BASE_PLAN = LANE / "host-test-plan.json"
BASE_PLAN_SHA = "83fdb4bae803e4f0374307f1302e2ecf4a67c5b37edfbcbc5f97faef1e44786e"
PLAN = RUNNER / "host-test-plan.json"
PLAN_SHA = "49348e2c66677933bca0028324bab7a52e639a894512c62b81bd367ea8f7d475"
PACKET_SHA = "866d0058d5f54116f3459bc0fcf4a3afe6437e30f796c69d3759d2de8893bedc"
REVIEW = ROOT / "verification/swift-root-bound-dispatch-physical-evidence-independent-v2"
REVIEW_SHA = "0ca1c7d76fa013bbf0a93b3f1c9231722822d70de38ce109f1563b268d379f18"
REVIEW_RESULT_SHA = "fc0715c8fb230e383f86a2113f3a589bae4c014a3039436d887fe8a64d365bda"
RELEASE = ROOT / "verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-v2-host-release-2.json"
PYTHON = "/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14"
BUILD = LANE / "command"
TMP = BUILD / "tmp"
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
SEEN = []
OWNED = []
ERRORS = []
PINS = {}


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
    require(type(item["bytes"]) is int and 0 <= item["bytes"] <= 16777216, "pin byte bound")
    require(type(item["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", item["sha256"]), "pin hash syntax")
    row = {"bytes": item["bytes"], "sha256": item["sha256"]}
    name = str(path)
    require(name not in PINS or PINS[name] == row, "conflicting pin: " + name)
    PINS[name] = row


def plan_diff(left, right, path=""):
    if type(left) is not type(right):
        return [path]
    if type(left) is dict:
        differences = []
        for key in sorted(set(left) | set(right)):
            nested = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in left or key not in right:
                differences.append(nested)
            else:
                differences.extend(plan_diff(left[key], right[key], nested))
        return differences
    if type(left) is list:
        if len(left) != len(right):
            return [path]
        return [difference for index, (a, b) in enumerate(zip(left, right))
                for difference in plan_diff(a, b, path + "/" + str(index))]
    return [] if left == right else [path]


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
    with (OUT / name).open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    deadline(55)


def generated_inventory(offset):
    rows, pending, count, size = [], [BUILD], 0, 0
    require(stat.S_ISDIR(BUILD.lstat().st_mode) and BUILD.resolve() == BUILD, "owned directory redirected")
    while pending:
        deadline(offset)
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                deadline(offset)
                count += 1
                require(count <= 64, "generated member cap")
                path = Path(entry.path)
                info = entry.stat(follow_symlinks=False)
                require(path.name != "__pycache__" and path.suffix not in (".pyc", ".pyo"), "bytecode artifact")
                row = {"path": str(path.relative_to(BUILD)), "bytes": info.st_size if stat.S_ISREG(info.st_mode) else 0}
                if stat.S_ISDIR(info.st_mode):
                    row["type"] = "directory"
                    pending.append(path)
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "generated symlink, special file, or shared hard link")
                    size += info.st_size
                    require(size <= 16777216, "generated byte cap")
                    row["type"] = "file"
                rows.append(row)
    # Complete bounded membership/type/size traversal precedes all file hashing.
    for row in rows:
        if row["type"] == "file":
            row["sha256"] = digest(BUILD / row["path"], offset)
    return {"members": sorted(rows, key=lambda row: row["path"]), "member_count": count, "file_bytes": size}


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
    record = {"kind": "synthetic16", "argv": plan["argv"], "environment": plan["environment"],
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
            if not record.get("reaped") and exited(record):
                record["cleanup_path"] = "completed-child-no-signals"
                require(reap_completed(record), "unknown child closure")
            for key, _ in selector.select(0.025):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = buffers[key.data]
                cap = 262144 if key.data == "stdout" else 524288
                room = cap - len(target)
                target.extend(chunk[:room])
                if len(chunk) > room:
                    record["output_truncated"] = True
                    raise RuntimeError(key.data + " output cap exceeded")
        require(record["returncode"] == 0, "synthetic16 unexpected exit")
        record["full_streams_captured"] = True
    finally:
        selector.close()
        for stream in (child.stdout, child.stderr):
            stream.close()
        for key, data in buffers.items():
            name = "host-tests." + key
            with (OUT / name).open("xb") as handle:
                handle.write(data)
            record[key] = {"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        record["end_seconds"] = time.monotonic() - START
    return buffers


def check_output(buffers, roster):
    require(not buffers["stdout"], "unexpected stdout")
    families = roster["families"]
    names = [row["test_method"] for row in families]
    require(len(names) == len(set(names)) == 16 and [row["family"] for row in families] == ["P%02d" % i for i in range(1, 17)], "frozen roster mismatch")
    expected = [name + " (__main__.RegionCertificateControls." + name + ") ... ok" for name in names]
    output = buffers["stderr"].decode("utf-8", errors="strict")
    lines = output.splitlines()
    require(lines[:16] == expected, "missing, duplicate, extra, failed, or skipped method")
    require(len(lines) == 21 and lines[16] == "" and lines[17] == "-" * 70 and
            re.fullmatch(r"Ran 16 tests in [0-9]+\.[0-9]{3}s", lines[18]) and
            lines[19] == "" and lines[20] == "OK", "non-standard unittest output or summary")
    # splitlines drops one final newline, so compare the complete framing too.
    require(output == "\n".join(expected) + "\n\n" + "-" * 70 + "\n" + lines[18] + "\n\nOK\n", "unexpected warning, traceback, or trailing output")
    return names


def prepare():
    require(__debug__ and sys.dont_write_bytecode and Path(__file__).absolute() == SCRIPT and Path.cwd() == ROOT, "exact non-optimized -B controller/cwd required")
    require(str(Path(sys.executable).resolve()) == PYTHON, "controller interpreter differs from pinned Python")
    require(sys.argv == [str(SCRIPT)], "controller accepts no arguments")
    base_plan = control(BASE_PLAN, BASE_PLAN_SHA)
    plan = control(PLAN, PLAN_SHA)
    require(plan_diff(base_plan, plan) == ["/controller_environment", "/root_release_required/path"],
            "amendment must change exactly the controller environment and release path")
    expected_controller_environment = dict(base_plan["environment"], __CF_USER_TEXT_ENCODING="0x1F5:0x0:0x0")
    require(len(expected_controller_environment) == 8 and plan["controller_environment"] == expected_controller_environment and
            plan["root_release_required"]["path"] == str(RELEASE.relative_to(ROOT)), "exact plan amendment values")
    packet = control(LANE / "seal.json", PACKET_SHA)
    members(LANE, packet)
    require(packet["host_test_plan_sha256"] == BASE_PLAN_SHA and packet["complete_capacity_accepted"] is False, "packet base-plan/scope binding")
    manifest = control(LANE / "input-manifest.json")
    roster = control(LANE / "test-family-map.json")
    for row in manifest["inputs"] + plan["source_files"]:
        add_pin(relative(ROOT, row["path"]), row)
    review = control(REVIEW / "seal.json", REVIEW_SHA)
    members(REVIEW, review)
    result = control(REVIEW / "review-result.json", REVIEW_RESULT_SHA)
    for row in (review, result):
        require(row["host_plan_sha256"] == BASE_PLAN_SHA and row["producer_seal_sha256"] == PACKET_SHA and
                row["synthetic_host_test_release_recommended"] is True, "independent review binding/recommendation")
    require(result["findings"] == [] and result["source_files"] == plan["source_files"] and
            result["target_import_syntax_parse_compile_tests_actual_saved_input_capture_or_runtime_execution"] == 0,
            "independent source-only review scope")
    release = control(RELEASE)
    require(release["schema"] == 1 and release["python_test_lane_released"] is True and
            type(release["python_test_invocations"]) is int and release["python_test_invocations"] == 1 and
            type(release["automatic_retries"]) is int and release["automatic_retries"] == 0, "root one-shot release required")
    require(release["plan_sha256"] == PLAN_SHA and release["base_plan_sha256"] == BASE_PLAN_SHA and
            release["packet_seal_sha256"] == PACKET_SHA and
            release["independent_source_review_plan_sha256"] == BASE_PLAN_SHA and
            release["independent_source_review_packet_seal_sha256"] == PACKET_SHA and
            release["independent_source_review_accepted"] is True and release["source_files"] == plan["source_files"], "root release input bindings")
    expected_review = {"path": str((REVIEW / "seal.json").relative_to(ROOT)),
                       "bytes": PINS[str(REVIEW / "seal.json")]["bytes"], "sha256": REVIEW_SHA}
    require(release["independent_source_review"] == expected_review, "exact root-approved independent review seal required")
    add_pin(SCRIPT, {"bytes": regular(SCRIPT).st_size, "sha256": release["controller_sha256"]})
    runner_manifest = control(RUNNER / "manifest.json", release["runner_manifest_sha256"])
    require(runner_manifest["schema"] == 1 and runner_manifest["member_count"] == len(runner_manifest["members"]) == 5,
            "runner manifest membership")
    require([row["path"] for row in runner_manifest["members"]] == ["AMENDMENT.md", "README.md", "host-test-plan.json", "release-schema.json", "run-synthetic16.py"],
            "runner manifest exact files")
    for row in runner_manifest["members"]:
        add_pin(relative(RUNNER, row["path"]), row)
    add_pin(Path(PYTHON), plan["python_tool"])
    require(plan["argv"] == [PYTHON, "-B", str(LANE / "source/tests_region_certificate.py")] and plan["cwd"] == str(ROOT), "exact test command")
    environment = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
                   "PYTHONHASHSEED": "0", "TMPDIR": str(TMP), "TZ": "UTC"}
    require(plan["environment"] == environment, "exact child environment")
    require(dict(os.environ) == plan["controller_environment"], "exact eight-key controller environment required")
    require(plan["owned_outputs"]["directory"] == str(BUILD) and plan["owned_outputs"]["temporary_directory"] == str(TMP), "exact owned outputs")
    require(not os.path.lexists(BUILD) and not os.path.lexists(OUT), "one-shot output already exists; never retry or overwrite")
    require(sys.version == plan["python_version_from_this_preparation"], "pinned Python version differs")
    return plan, packet, roster, release


def main():
    for sig in SIGNALS:
        signal.signal(sig, lambda number, _frame: SEEN.append(number))
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    # Unreleased/invalid preparation fails before creating output or any child.
    plan, packet, roster, release = prepare()
    outcome = {"schema": 1, "plan_sha256": PLAN_SHA, "base_plan_sha256": BASE_PLAN_SHA,
               "packet_seal_sha256": PACKET_SHA, "controller_environment": dict(os.environ),
               "allowed_plan_diff": ["/controller_environment", "/root_release_required/path"],
               "packet_tree_sha256": packet["tree_sha256"], "independent_source_review_sha256": REVIEW_SHA,
               "all_results_local_geometry_only": True, "complete_capacity_accepted": False,
               "physical_capacity_prices_backings_root_funding_product_GA_accepted": False,
               "source_files": plan["source_files"], "python_version": sys.version,
               "python_tool": plan["python_tool"], "controller_sha256": release["controller_sha256"],
               "runner_manifest_sha256": release["runner_manifest_sha256"], "automatic_retries": 0}
    OUT.mkdir(exist_ok=False)
    created_build = False
    passed = False
    try:
        outcome["pins_before"] = verify_pins(44)
        require(not SEEN, "signal during preflight")
        BUILD.mkdir(exist_ok=False)
        created_build = True
        TMP.mkdir(exist_ok=False)
        require(list(BUILD.iterdir()) == [TMP] and not list(TMP.iterdir()), "fresh command/tmp only")
        buffers = command(plan)
        outcome["passing_methods"] = check_output(buffers, roster)
        outcome["tests_passed"] = 16
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
                outcome["generated"] = generated_inventory(49)
                shutil.rmtree(BUILD)
                deadline(49)
                outcome["generated_directory_removed"] = not os.path.lexists(BUILD)
            else:
                outcome["generated_inventory_deferred_for_uncertain_closure"] = created_build
                outcome["generated_directory_removed"] = False
            outcome["pins_after"] = verify_pins(53.5)
            require(outcome.get("pins_before") == outcome["pins_after"], "before/after pin inventory differs")
            outcome["all_pins_rechecked"] = True
        except BaseException as error:
            ERRORS.append("post: " + repr(error) + "\n" + traceback.format_exc(limit=8))
        outcome.update(commands=[{k: v for k, v in r.items() if k != "child"} for r in OWNED],
                       errors=ERRORS, owned_groups_closed=closed, elapsed_before_observation_seconds=time.monotonic() - START)
        save("observations.json", outcome)
        observations_sha = None
        finalization_errors = []
        try:
            observations_sha = digest(OUT / "observations.json", 53.5)
        except BaseException as error:
            finalization_errors.append("observation hash: " + repr(error))
        # All hashing/observation precedes this reviewed one-way signal cutoff.
        signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        cutoff = time.monotonic() - START
        observed = SEEN + [int(sig) for sig in signal.sigpending() if sig in SIGNALS]
        for sig in SIGNALS:
            signal.signal(sig, signal.SIG_IGN)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, SIGNALS)
        passed = (not ERRORS and not finalization_errors and not observed and cutoff < 53.5 and closed and
                  outcome.get("tests_passed") == 16 and outcome.get("all_pins_rechecked") is True and
                  outcome.get("generated_directory_removed") is True and
                  OWNED[0].get("full_streams_captured") is True and not OWNED[0].get("output_truncated"))
        save("receipt.json", {"schema": 1, "status": "passed" if passed else "failed", "plan_sha256": PLAN_SHA,
            "base_plan_sha256": BASE_PLAN_SHA,
            "packet_seal_sha256": PACKET_SHA, "controller_sha256": release["controller_sha256"],
            "signal_cutoff_seconds": cutoff, "observed_signals": observed, "observations_sha256": observations_sha,
            "finalization_errors": finalization_errors,
            "signal_scope": "Observed/pending through the one-way cutoff after all hashing; later signals outside this receipt.",
            "all_results_local_geometry_only": True, "complete_capacity_accepted": False,
            "physical_capacity_prices_backings_root_funding_product_GA_accepted": False})
        print(json.dumps({"status": "passed" if passed else "failed", "tests": outcome.get("tests_passed", 0),
                          "elapsed_seconds": time.monotonic() - START, "receipt": str(OUT / "receipt.json")}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
