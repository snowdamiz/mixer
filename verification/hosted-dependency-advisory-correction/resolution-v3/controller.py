#!/usr/bin/env python3
"""Root-released, one-attempt dependency resolution; never compile/start Mixer."""
import time
START = time.monotonic()
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
ROOT = PACKET.parents[1]
WORK, CLEANUP, POSTHASH, RECEIPT = [START + n for n in (40, 46, 52, 55)]
CAP = 262_144
STATE = {"status": "failed", "commands": [], "errors": [], "groups": [],
         "phase_offsets_seconds": {"work": 40, "cleanup": 46, "posthash": 52, "receipt": 55},
         "runtime_qualification": "dependency resolution only; no product compile/test/start"}
CHILD = None
CANCELLED = False
STOP_SIGNALS = {signal.SIGINT, signal.SIGTERM}


class Refusal(Exception):
    pass


def guard(deadline):
    if (CANCELLED and deadline <= WORK) or time.monotonic() >= deadline:
        raise Refusal("cancelled" if CANCELLED and deadline <= WORK else "phase deadline reached")


def interrupt(_signum, _frame):
    global CANCELLED
    CANCELLED = True
    STATE["cancelled"] = True
    STATE.setdefault("handled_stop_signals", []).append(_signum)


def pinned_bytes(path, expected, deadline, cap=1_048_576):
    guard(deadline)
    with path.open("rb") as source:
        raw = source.read(cap + 1)
    if len(raw) > cap or hashlib.sha256(raw).hexdigest() != expected:
        raise Refusal("pinned byte mismatch: " + str(path))
    guard(deadline)
    return raw


def signal_cutoff():
    # One way: never restore this mask. Establish the finite cutoff before the
    # protected pending-signal snapshot. No source/output hashes follow it.
    guard(POSTHASH)
    signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
    cutoff = time.monotonic()
    STATE["signal_observation_cutoff_elapsed_seconds"] = cutoff - START
    pending = sorted(int(sig) for sig in signal.sigpending() & STOP_SIGNALS)
    cancelled_through_cutoff = bool(CANCELLED or STATE.get("cancelled") or pending)
    STATE["stop_signals_pending_at_cutoff_snapshot"] = pending
    STATE["cancelled_through_cutoff"] = cancelled_through_cutoff
    STATE["signal_observation_scope"] = "Handled before cutoff or pending in protected snapshot. Snapshot may conservatively include signals just after cutoff; later blocked signals are outside the guaranteed observation scope."
    if cancelled_through_cutoff:
        STATE["errors"].append({"phase": "signal_cutoff", "message": "cancellation observed through finite cutoff"})
    return cancelled_through_cutoff


def sha(path, deadline):
    result = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(262_144):
            guard(deadline)
            result.update(chunk)
    return result.hexdigest()


def write_json(path, value, deadline):
    guard(deadline)
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    if len(data) > 1_048_576:
        raise Refusal("JSON output exceeds 1 MiB")
    path.write_bytes(data)
    guard(deadline)


def disk_guard(scratch, deadline):
    count = size = 0
    pending = [scratch]
    while pending:
        guard(deadline)
        with os.scandir(pending.pop()) as entries:
            for item in entries:
                guard(deadline)
                count += 1
                if count > 10_000 or item.is_symlink():
                    raise Refusal("scratch entry limit or symlink")
                if item.is_dir(follow_symlinks=False):
                    pending.append(Path(item.path))
                elif item.is_file(follow_symlinks=False):
                    size += item.stat(follow_symlinks=False).st_size
                else:
                    raise Refusal("unexpected scratch file type")
                if size > 268_435_456:
                    raise Refusal("scratch exceeds 256 MiB")
    return {"entries": count, "bytes": size}


def child_exited(process):
    # WNOWAIT deliberately keeps the leader unreaped, preventing PID/PGID reuse
    # while this controller can still signal that owned process group.
    return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def group_absent(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True


def close_child(owned, deadline):
    process = owned["process"]
    evidence = owned["evidence"]
    if evidence.get("closed"):
        return True
    if owned.get("reaped") and evidence.get("custody_confirmed"):
        while time.monotonic() < deadline and not group_absent(process.pid):
            time.sleep(0.01)
        evidence["closed"] = group_absent(process.pid)
        return evidence["closed"]
    if not evidence.get("custody_confirmed"):
        evidence["cleanup_error"] = "custody uncertain; no group signal or scratch deletion"
        return False
    try:
        # All signals occur while the original direct child remains unreaped.
        for sig, grace in [(signal.SIGTERM, 0.10), (signal.SIGKILL, 0.0)]:
            if time.monotonic() >= deadline:
                return False
            try:
                os.killpg(process.pid, sig)
                evidence.setdefault("signals", []).append(sig.name)
            except ProcessLookupError:
                pass
            until = min(deadline, time.monotonic() + grace)
            while time.monotonic() < until:
                time.sleep(max(0.0, min(0.01, until - time.monotonic())))
        while time.monotonic() < deadline and not child_exited(process):
            time.sleep(0.01)
        if not child_exited(process):
            return False
        process.wait(timeout=0)
        owned["reaped"] = True
        evidence["returncode"] = process.returncode
        # Never signal after reaping: an observed nonempty group is only waited
        # on. If it does not disappear, closure remains unknown and scratch stays.
        while time.monotonic() < deadline and not group_absent(process.pid):
            time.sleep(0.01)
        evidence["closed"] = group_absent(process.pid)
        evidence["cleanup_elapsed_seconds"] = time.monotonic() - START
        return evidence["closed"]
    except (OSError, subprocess.SubprocessError) as error:
        evidence["cleanup_error"] = type(error).__name__
        return False


def drain(process, selector, buffers, deadline):
    guard(deadline)
    for key, _ in selector.select(timeout=min(0.025, max(0, deadline - time.monotonic()))):
        chunk = os.read(key.fd, 65_536)
        if not chunk:
            selector.unregister(key.fileobj)
        else:
            target = buffers[key.data]
            remaining = CAP - len(target)
            target.extend(chunk[:remaining])
            if len(chunk) > remaining:
                raise Refusal(key.data + " exceeds 256 KiB")


def run_command(command, environment, scratch, attempt):
    global CHILD
    guard(WORK)
    evidence = {"name": command["name"], "argv": command["argv"],
                "start_elapsed_seconds": time.monotonic() - START,
                "absolute_deadline_elapsed_seconds": 40, "custody_confirmed": False,
                "closed": False}
    STATE["commands"].append(evidence)
    command_environment = dict(environment, **command.get("environment_override", {}))
    process = subprocess.Popen(command["argv"], cwd=scratch / "project",
                               env=command_environment, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    CHILD = {"process": process, "evidence": evidence, "reaped": False}
    STATE["groups"].append(evidence)
    evidence["pid"] = process.pid
    evidence.update(pgid=os.getpgid(process.pid), sid=os.getsid(process.pid))
    evidence["custody_confirmed"] = evidence["pid"] == evidence["pgid"] == evidence["sid"]
    if not evidence["custody_confirmed"]:
        raise Refusal("new child group/session mismatch")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    selector = selectors.DefaultSelector()
    for name, stream in [("stdout", process.stdout), ("stderr", process.stderr)]:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    last_disk_check = 0.0
    try:
        while not child_exited(process):
            drain(process, selector, buffers, WORK)
            if time.monotonic() - last_disk_check >= 0.10:
                evidence["scratch_size"] = disk_guard(scratch, WORK)
                last_disk_check = time.monotonic()
        # Close owned helper processes before advancing to another command.
        if not close_child(CHILD, min(WORK, time.monotonic() + 0.5)):
            raise Refusal("command process-group closure not known")
        while selector.get_map():
            drain(process, selector, buffers, WORK)
        if evidence["returncode"] != 0:
            raise Refusal("command failed: " + command["name"])
    finally:
        selector.close()
        for stream in [process.stdout, process.stderr]:
            stream.close()
        for name, data in buffers.items():
            path = attempt / (command["name"] + "." + name)
            path.write_bytes(data)
            evidence[name] = {"path": path.name, "bytes": len(data),
                              "sha256": hashlib.sha256(data).hexdigest()}
        evidence["end_elapsed_seconds"] = time.monotonic() - START


def verify_sources(preparation, deadline):
    for name, item in preparation["selected_inputs"].items():
        if sha(ROOT / name, deadline) != item["sha256"]:
            raise Refusal("selected canonical source changed: " + name)
    prior = ROOT / "verification/hosted-dependency-advisory-review"
    old = preparation["prior_advisory_packet"]
    if sha(prior / "seal.sha256", deadline) != old["seal_sha256"]:
        raise Refusal("prior advisory seal changed")
    for item in old["entries"]:
        if sha(prior / item["path"], deadline) != item["sha256"]:
            raise Refusal("prior advisory packet changed")
    for item in preparation["tool_files"]:
        if sha(Path(item["path"]), deadline) != item["sha256"]:
            raise Refusal("tool file changed")
    archive = preparation["installed_hex_archive"]
    for name, item in archive["files"].items():
        if sha(Path(archive["root"]) / name, deadline) != item["sha256"]:
            raise Refusal("installed Hex archive changed")


def verify_packet(plan, deadline):
    for name, expected in plan["packet_inputs"].items():
        if sha(PACKET / name, deadline) != expected:
            raise Refusal("prepared packet input changed: " + name)
    for item in plan["additional_pinned_sources"]:
        if sha(Path(item["path"]), deadline) != item["sha256"]:
            raise Refusal("additional selected source changed")


def remove_owned_tree(path, deadline):
    guard(deadline)
    with os.scandir(path) as entries:
        for item in entries:
            guard(deadline)
            if item.is_symlink():
                raise Refusal("refusing cleanup after unexpected symlink")
            if item.is_dir(follow_symlinks=False):
                remove_owned_tree(Path(item.path), deadline)
            else:
                os.unlink(item.path)
    guard(deadline)
    path.rmdir()


def lock_inventory(path, deadline):
    guard(deadline)
    raw = path.read_bytes()
    if len(raw) > 1_048_576:
        raise Refusal("lock exceeds 1 MiB")
    lines = raw.splitlines(keepends=True)
    if lines[0] != b"%{\n" or lines[-1] != b"}\n":
        raise Refusal("unsupported lock envelope")
    result = {}
    pattern = rb'  "([a-z0-9_]+)": (\{:hex, :([a-z0-9_]+), "([0-9.]+)", "([a-f0-9]{64})", .+, "hexpm", "([a-f0-9]{64})"\}),\n'
    for line in lines[1:-1]:
        guard(deadline)
        match = re.fullmatch(pattern, line)
        if not match or match[1] != match[3] or match[1].decode() in result:
            raise Refusal("unsupported or duplicate lock entry")
        result[match[1].decode()] = {
            "version": match[4].decode(), "inner_checksum": match[5].decode(),
            "outer_checksum": match[6].decode(), "entry_sha256": hashlib.sha256(line).hexdigest()}
    if len(result) != 21:
        raise Refusal("expected exactly 21 lock entries")
    return result


def main():
    if len(sys.argv) != 4 or sys.argv[1:3] != ["--root-release", "--plan-sha256"] or not re.fullmatch(r"[a-f0-9]{64}", sys.argv[3]):
        raise Refusal("requires root release and exact selected plan SHA256")
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, interrupt)
    plan_raw = pinned_bytes(HERE / "resolution-plan-v3.json", sys.argv[3], WORK)
    plan = json.loads(plan_raw)
    if sha(Path(__file__), WORK) != plan["controller_sha256"]:
        raise Refusal("controller source pin mismatch")
    preparation_sha = plan["packet_inputs"]["preparation-receipt.json"]
    preparation_raw = pinned_bytes(PACKET / "preparation-receipt.json", preparation_sha, WORK)
    preparation = json.loads(preparation_raw)
    attempt = HERE / "attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True, mode=0o700)
    scratch = attempt / "scratch"
    scratch.mkdir(mode=0o700)
    marker = uuid.uuid4().hex
    (scratch / ".owner").write_text(marker)
    STATE.update(source_revision=preparation["source_revision"],
                 source_tree=preparation["source_tree"],
                 preparation_receipt_sha256=preparation_sha,
                 controller_sha256=plan["controller_sha256"], plan_sha256=sys.argv[3],
                 attempt=str(attempt), scratch=str(scratch), started_unix_seconds=time.time())
    print(json.dumps({"status": "started", "attempt": str(attempt)}), flush=True)
    successful_work = False
    try:
        verify_sources(preparation, WORK)
        verify_packet(plan, WORK)
        for name in ["project", "tmp", "mix-home/archives", "hex-home", "beam-home"]:
            (scratch / name).mkdir(parents=True, exist_ok=True)
        for name, target in [("proposal/mix.exs", scratch / "project/mix.exs"),
                             ("inputs/mix.lock", scratch / "project/mix.lock"),
                             ("resolution-v3/inetrc", scratch / "inetrc")]:
            target.write_bytes(pinned_bytes(PACKET / name, plan["packet_inputs"][name], WORK))
        STATE["resolver_policy"] = {"ERL_INETRC": str(scratch / "inetrc"),
                                    "sha256": plan["packet_inputs"]["resolution-v3/inetrc"],
                                    "lookup": ["dns", "file"], "native_fallback": False}
        archive = preparation["installed_hex_archive"]
        for name, item in archive["files"].items():
            guard(WORK)
            source = Path(archive["root"]) / name
            target = scratch / "mix-home/archives/hex-2.5.1" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if sha(target, WORK) != item["sha256"]:
                raise Refusal("copied Hex archive differs")
        environment = {k: v.replace("${OPERATION_SCRATCH}", str(scratch))
                       for k, v in plan["environment"].items()}
        STATE["environment"] = environment
        before = lock_inventory(scratch / "project/mix.lock", WORK)
        resolved_hash = None
        for command in plan["commands"]:
            pinned_bytes(scratch / "inetrc", plan["packet_inputs"]["resolution-v3/inetrc"], WORK)
            pinned_bytes(scratch / "project/mix.exs", plan["packet_inputs"]["proposal/mix.exs"], WORK)
            run_command(command, environment, scratch, attempt)
            if command["name"] == "resolve-and-fetch-private-dependencies":
                resolved_hash = sha(scratch / "project/mix.lock", WORK)
            elif command["name"] == "offline-locked-recheck":
                if sha(scratch / "project/mix.lock", WORK) != resolved_hash:
                    raise Refusal("offline locked recheck changed lock bytes")
        after = lock_inventory(scratch / "project/mix.lock", WORK)
        expected = {"bandit": "1.14.0", "jose": "1.11.13"}
        if before.keys() != after.keys():
            raise Refusal("package set changed")
        candidate_sha = next(item["sha256"] for item in preparation["prior_advisory_packet"]["entries"]
                             if item["path"] == "upgrade-candidates.json")
        candidate_raw = pinned_bytes(ROOT / "verification/hosted-dependency-advisory-review/upgrade-candidates.json", candidate_sha, WORK)
        candidates = json.loads(candidate_raw)
        official = {c["package"]: c["metadata"]["checksum"] for c in candidates}
        for name, item in after.items():
            if name in expected:
                if item["version"] != expected[name] or item["outer_checksum"] != official[name]:
                    raise Refusal("selected version/checksum differs from official candidate")
            elif item != before[name]:
                raise Refusal("extra lock entry changed: " + name)
        STATE["lock_inventory"] = {"entries": after, "changed": sorted(expected),
                                    "unchanged_other_entries": 19, "entry_count": 21,
                                    "unchanged_other_entry_hashes": {
                                        name: {"before": before[name]["entry_sha256"],
                                               "after": after[name]["entry_sha256"]}
                                        for name in after if name not in expected},
                                    "official_candidate_outer_checksums": official,
                                    "verified": True}
        successful_work = True
    except Exception as error:
        STATE["errors"].append({"phase": "work", "type": type(error).__name__, "message": str(error)[:1024]})
    finally:
        # Cancellation stops work; reserved cleanup/posthash/receipt still run.
        if CHILD is not None and not close_child(CHILD, CLEANUP):
            STATE["errors"].append({"phase": "cleanup", "message": "owned group closure unknown"})
        STATE["groups_closed"] = all(item.get("closed", False) for item in STATE["groups"])
        try:
            guard(POSTHASH)
            lock = scratch / "project/mix.lock"
            if STATE["groups_closed"] and lock.is_file() and lock.stat().st_size <= 1_048_576:
                shutil.copyfile(lock, attempt / "actual-mix.lock")
                STATE["retained_lock_sha256"] = sha(attempt / "actual-mix.lock", POSTHASH)
            verify_sources(preparation, POSTHASH)
            verify_packet(plan, POSTHASH)
            if sha(Path(__file__), POSTHASH) != plan["controller_sha256"]:
                raise Refusal("controller changed during operation")
            if sha(HERE / "resolution-plan-v3.json", POSTHASH) != STATE["plan_sha256"]:
                raise Refusal("plan changed during operation")
            STATE["canonical_and_prior_packet_unchanged"] = True
            if STATE["groups_closed"] and "lock_inventory" in STATE:
                write_json(attempt / "lock-inventory.json", STATE["lock_inventory"], POSTHASH)
            STATE["scratch_size"] = disk_guard(scratch, POSTHASH)
            if (scratch / "inetrc").exists():
                pinned_bytes(scratch / "inetrc", plan["packet_inputs"]["resolution-v3/inetrc"], POSTHASH)
            if STATE["groups_closed"] and (scratch / ".owner").read_text() == marker:
                guard(POSTHASH)
                remove_owned_tree(scratch, POSTHASH)
                STATE["scratch_removed"] = not scratch.exists()
                guard(POSTHASH)
            else:
                STATE["scratch_removed"] = False
            STATE["retained_output_hashes"] = {}
            for output in sorted(attempt.iterdir()):
                guard(POSTHASH)
                if output.is_file():
                    STATE["retained_output_hashes"][output.name] = sha(output, POSTHASH)
            STATE["all_output_and_source_hashing_finished_elapsed_seconds"] = time.monotonic() - START
        except Exception as error:
            STATE["errors"].append({"phase": "posthash", "type": type(error).__name__, "message": str(error)[:1024]})
        try:
            if "all_output_and_source_hashing_finished_elapsed_seconds" not in STATE:
                raise Refusal("no success cutoff after incomplete output/source hashing")
            cancelled = signal_cutoff()
            if successful_work and not STATE["errors"] and STATE.get("scratch_removed") and not cancelled:
                STATE["status"] = "resolved_two_pins_only"
        except Exception as error:
            STATE["errors"].append({"phase": "signal_cutoff", "type": type(error).__name__, "message": str(error)[:1024]})
        STATE["ended_elapsed_seconds"] = time.monotonic() - START
        write_json(attempt / "receipt.json", STATE, RECEIPT)
        print(json.dumps({"status": STATE["status"], "receipt": str(attempt / "receipt.json"),
                          "elapsed_seconds": time.monotonic() - START}))
    return 0 if STATE["status"] == "resolved_two_pins_only" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"status": "failed_before_or_during_receipt", "type": type(error).__name__,
                          "message": str(error)[:1024], "elapsed_seconds": time.monotonic() - START}), file=sys.stderr)
        raise SystemExit(1)
