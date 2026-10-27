"""Independent finite raw-stdio controls; each invocation owns one contained case.

Never retry an uncertain saved descriptor number or erase an uncertainty ledger.
The only numeric cleanup outside the candidate consumes independent fresh births.
"""
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
import weakref
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "new/replay/corrected/replay"))
import prototype as p


def capture(call):
    try:
        return call(), None
    except BaseException as error:
        return None, error


def refused(call):
    _, error = capture(call)
    assert isinstance(error, p.Refusal), repr(error)
    return error.code


def fault_list(error):
    assert isinstance(error, p.CleanupAggregate)
    return [f for e in error.cleanup_errors for f in e.failures]


def trace(error):
    return {"type": type(error).__name__, "text": str(error), "trace": traceback.format_exception(error, chain=False)} if error else None


def inaccessible(owner):
    for call in (owner.fileno, lambda: owner.read(1), lambda: owner.seek(0)):
        assert refused(call) == "stdio-owner-not-open"


def blocked(directory):
    assert refused(lambda: p.RawStdio(directory)) == "stdio-admission-quarantined-or-full"
    assert refused(lambda: p.Retained(directory / "no-birth", 1, output=True)) == "owner-admission-quarantined-or-full"
    assert not (directory / "no-birth").exists()


def closures(directory, pattern, body, baseexception=False):
    bundle = p.terminal_streams(directory)
    bundle.__enter__()
    owners = [bundle.out, bundle.err]
    numbers = [x.fileno() for x in owners]
    primary = ValueError("exact independent primary")
    result = {"exact": object()}
    if body in ("result", "both"):
        bundle.completed(result)
    active_primary = primary if body in ("primary", "both") else None
    errors = [KeyboardInterrupt("independent cancellation") if baseexception and i == 1 else OSError("independent stream " + str(i)) for i in range(2)]
    calls = []
    original = p._stdio_close_syscall

    def close(number):
        index = numbers.index(number)
        calls.append(index)
        inaccessible(owners[index])
        if pattern[index] != "p":
            original(number)
        if pattern[index] != "-":
            raise errors[index]

    with patch.object(p, "_stdio_close_syscall", close):
        _, caught = capture(lambda: bundle.__exit__(type(active_primary), active_primary, None))
        assert isinstance(caught, p.CleanupAggregate)
        assert caught.primary is active_primary
        assert caught.retained_result is (result if body in ("result", "both") else None)
        expected = [errors[i] for i in (1, 0) if pattern[i] != "-"]
        observed = fault_list(caught)
        assert len(observed) == len(expected)
        assert all(f.exception is e for f, e in zip(observed, expected))
        assert calls == [1, 0]
        _, repeated = capture(lambda: bundle.__exit__(None, None, None))
        assert repeated is caught
        for owner in owners:
            _, repeat = capture(owner.close)
            if owner.state == "quarantined":
                assert isinstance(repeat, p.CleanupFailure) and repeat.report is owner._report
            else:
                assert repeat is None
        gc.collect()
        assert calls == [1, 0]
    snapshot = p.ownership_snapshot()
    assert not snapshot["healthy_zero"] and snapshot["stdio_uncertain_close_records"] == len(expected)
    assert snapshot["stdio_path_obligations"] == 0
    actual_open = []
    for i, number in enumerate(numbers):
        _, error = capture(lambda: os.fstat(number))
        if error is None:
            actual_open.append(i)
        assert (error is None) == (pattern[i] == "p")
        inaccessible(owners[i])
    blocked(directory)
    return {"case": "independent-close", "pattern": pattern, "body": body, "baseexception": baseexception, "calls": calls, "controlled_preclose_fds_actually_open": actual_open, "primary_identity": True, "result_identity": True, "all_failure_identities": True, "original_primary": trace(active_primary), "cleanup_exceptions": [trace(x) for x in expected], "repeated_cleanup_and_gc_syscalls": 0}


def acquire(directory, index, stage, cleanup_mode):
    primary = RuntimeError("independent acquisition " + str(index) + " " + stage)
    cleanup_error = SystemExit("independent first-owner close")
    owners, births, close_calls, unlink_calls = [], [], [], []
    primitive = p.tempfile.mkstemp
    acquire_original = p._stdio_acquire
    prepare_original = p._stdio_prepare
    close_original = p._stdio_close_syscall
    unlink_original = os.unlink
    attempts = 0

    def mkstemp(*args, **kwargs):
        nonlocal attempts
        current = attempts
        attempts += 1
        if current == index and stage == "primitive-before":
            raise primary
        value = primitive(*args, **kwargs)
        births.append(value)
        return value

    def acquired(owner, scratch):
        owners.append(owner)
        acquire_original(owner, scratch)
        assert owner._token.number == births[-1][0]
        assert p.STDIO_TOKENS[owner._token.generation] is owner._token
        assert p.STDIO_PATHS[owner.generation] == births[-1][1]
        if len(owners) - 1 == index and stage == "captured-birth":
            raise primary

    def prepare(owner):
        if owners.index(owner) == index and stage == "prepare-before":
            raise primary
        prepare_original(owner)
        if owners.index(owner) == index and stage == "prepare-after":
            raise primary

    def unlink(path, *args, **kwargs):
        target = str(path) == str(births[-1][1]) if births else False
        if target:
            current = len(unlink_calls)
            unlink_calls.append(str(path))
            if current == index and stage == "unlink-before":
                raise primary
            value = unlink_original(path, *args, **kwargs)
            if current == index and stage == "unlink-after":
                raise primary
            return value
        return unlink_original(path, *args, **kwargs)

    def close(number):
        close_calls.append(number)
        if births and number == births[0][0] and cleanup_mode != "-":
            if cleanup_mode == "q":
                close_original(number)
            raise cleanup_error
        close_original(number)

    bundle = p.terminal_streams(directory)
    with patch.object(p.tempfile, "mkstemp", mkstemp), patch.object(p, "_stdio_acquire", acquired), patch.object(p, "_stdio_prepare", prepare), patch.object(p.os, "unlink", unlink), patch.object(p, "_stdio_close_syscall", close):
        _, caught = capture(bundle.__enter__)
        assert caught is not None
        actual_primary = caught.primary if isinstance(caught, p.CleanupAggregate) else caught
        assert actual_primary is primary
        assert attempts == index + 1
        assert sorted(close_calls) == sorted(x[0] for x in births)
        assert len(close_calls) == len(set(close_calls))
        before = (tuple(close_calls), tuple(unlink_calls))
        for owner in owners:
            capture(owner.close)
        capture(lambda: bundle.__exit__(None, None, None))
        gc.collect()
        assert (tuple(close_calls), tuple(unlink_calls)) == before
    pending_path = stage in ("captured-birth", "prepare-before", "unlink-before", "unlink-after")
    state = p.ownership_snapshot()
    assert state["stdio_path_obligations"] == int(pending_path)
    assert state["stdio_uncertain_close_records"] == int(cleanup_mode != "-")
    assert state["healthy_zero"] == (not pending_path and cleanup_mode == "-")
    if pending_path or cleanup_mode != "-":
        blocked(directory)
    fault_count = 0
    if isinstance(caught, p.CleanupAggregate):
        faults = fault_list(caught)
        assert sum(f.exception is primary for f in faults) == int(pending_path)
        assert sum(f.exception is cleanup_error for f in faults) == int(cleanup_mode != "-")
        assert len(faults) == int(pending_path) + int(cleanup_mode != "-")
        fault_count = len(faults)
    else:
        assert not pending_path and cleanup_mode == "-"
    return {"case": "independent-acquisition", "index": index, "stage": stage, "cleanup_mode": cleanup_mode, "primitive_attempts": attempts, "captured_births": len(births), "close_attempts": len(close_calls), "path_obligations": int(pending_path), "all_failure_identities": True, "cleanup_faults": fault_count, "original_primary": trace(primary), "first_owner_cleanup_exception": trace(cleanup_error) if cleanup_mode != "-" else None}


def path_reuse(directory, after):
    original_unlink = os.unlink
    error = OSError("independent unlink reporting failure")
    calls = []
    owners = []
    original_acquire = p._stdio_acquire
    def acquired(owner, scratch):
        owners.append(owner)
        return original_acquire(owner, scratch)
    def unlink(path, *args, **kwargs):
        calls.append(str(path))
        if after:
            original_unlink(path, *args, **kwargs)
        raise error
    with patch.object(p, "_stdio_acquire", acquired), patch.object(p.os, "unlink", unlink):
        _, caught = capture(lambda: p.RawStdio(directory))
    assert isinstance(caught, p.CleanupAggregate) and caught.primary is error
    owner = owners[0]
    path = Path(owner._path)
    assert path.exists() is not after
    saved = owner._token.number
    _, closed_error = capture(lambda: os.fstat(saved))
    assert isinstance(closed_error, OSError)
    # Replace only this test's pathname after its known successful fd close.
    # No uncertain descriptor close is retried and no candidate ledger is cleared.
    if not after:
        # Move the known fixture entry aside; do not replay its failed unlink.
        os.rename(path, directory / "moved-original-fixture")
    fresh = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fresh, b"replacement path content")
        before = p.ownership_snapshot()
        with patch.object(p.os, "unlink", side_effect=AssertionError("old path retry")), patch.object(p, "_stdio_close_syscall", side_effect=AssertionError("old number retry")):
            _, repeat = capture(owner.close)
            assert isinstance(repeat, p.CleanupFailure) and repeat.report is owner._report
            gc.collect()
        assert path.read_bytes() == b"replacement path content"
        os.lseek(fresh, 0, os.SEEK_SET)
        assert os.read(fresh, 128) == b"replacement path content"
        assert p.ownership_snapshot() == before
        assert before["stdio_path_obligations"] == 1 and before["stdio_owners"] == 1 and before["stdio_uncertain_close_records"] == 0 and before["stdio_contexts"] == 0 and not before["healthy_zero"]
        blocked(directory)
    finally:
        os.close(fresh)  # This is the independent replacement's successful birth.
    return {"case": "independent-path-reuse", "after_real_unlink": after, "replacement_untouched": True, "old_name_or_number_retries": 0, "fd_closed_path_obligation_retained": True, "model_uncertainty_not_retired_by_fixture_replacement": True}


def descriptor_reuse(directory):
    bundle = p.terminal_streams(directory)
    bundle.__enter__()
    owner = bundle.err
    target = owner.fileno()
    original = p._stdio_close_syscall
    error = OSError("independent post-close uncertainty")
    def close(number):
        original(number)
        if number == target:
            raise error
    with patch.object(p, "_stdio_close_syscall", close):
        _, caught = capture(lambda: bundle.__exit__(None, None, None))
    assert fault_list(caught)[0].exception is error
    file = directory / "new-owner"
    file.write_bytes(b"live independent birth")
    fresh = []
    try:
        for _ in range(4):
            number = os.open(file, os.O_RDONLY)
            fresh.append(number)
            if number == target:
                break
        assert fresh[-1] == target
        with patch.object(p, "_stdio_close_syscall", side_effect=AssertionError("uncertain retry")), patch.object(p.os, "close", side_effect=AssertionError("hidden automatic close")):
            capture(owner.close)
            capture(lambda: bundle.__exit__(None, None, None))
            gc.collect()
        assert os.read(fresh[-1], 64) == b"live independent birth"
        assert not p.ownership_snapshot()["healthy_zero"]
    finally:
        for number in reversed(fresh):
            os.close(number)
    return {"case": "independent-descriptor-reuse", "natural_number_reuse": True, "fresh_owner_readable": True, "old_numeric_retries_or_destructor_closes": 0}


def healthy(directory):
    references = []
    for round_number in range(24):
        bundle = p.terminal_streams(directory)
        bundle.__enter__()
        old = tuple(bundle)
        numbers = [x.fileno() for x in old]
        for owner in old:
            assert not isinstance(owner, io.IOBase)
            assert not any("__del__" in typ.__dict__ for typ in type(owner).__mro__)
            assert refused(lambda: owner.read(True)) == "stdio-read-cap"
            assert refused(lambda: owner.read(513)) == "stdio-read-cap"
            assert refused(lambda: owner.seek(1)) == "stdio-seek-shape"
        assert refused(lambda: p.RawStdio(directory)) == "stdio-admission-quarantined-or-full"
        bundle.completed(None)
        assert refused(lambda: bundle.completed(object())) == "stdio-result-state"
        bundle.__exit__(None, None, None)
        references.extend(weakref.ref(x) for x in old)
        fresh = p.terminal_streams(directory)
        fresh.__enter__()
        assert [x.fileno() for x in fresh] == numbers
        with patch.object(p, "_stdio_close_syscall", side_effect=AssertionError("repeat/destructor close")):
            for owner in old:
                assert owner.close() is owner._report
                inaccessible(owner)
            bundle.__exit__(None, None, None)
            del owner, old, bundle
            gc.collect()
            assert all(ref() is None for ref in references)
        os.write(fresh.out.fileno(), b"fresh")
        fresh.out.seek(0)
        assert fresh.out.read(5) == b"fresh"
        fresh.__exit__(None, None, None)
        del fresh
        assert p.ownership_snapshot()["healthy_zero"]
    return {"case": "independent-healthy-repeated-gc", "rounds": 24, "successful_old_owners_collected": len(references), "natural_reuse_rounds": 24, "extra_cleanup_closes": 0, "growing_successful_global_ledger": False}


def read_boundary(directory, mode):
    # All acknowledged bytes are supplied by real os.read on our owned regular fd.
    # The controlled schedule limits successful chunks or injects EINTR only.
    owner = p.RawStdio(directory)
    number = owner.fileno()
    data = bytes(range(64))
    os.write(number, data)
    owner.seek(0)
    original = os.read
    calls = []
    size = 31 if mode == "chunks31" else 32
    def read(fd, count):
        assert fd == number
        calls.append(count)
        if mode.startswith("interrupt") and len(calls) <= (31 if mode == "interrupt31" else 32):
            raise InterruptedError("controlled EINTR")
        return original(fd, min(count, 1) if mode.startswith("chunks") else count)
    try:
        with patch.object(p.os, "read", read):
            value, error = capture(lambda: owner.read(size))
        expected_exhaustion = mode == "interrupt32"
        observation = {"case": "independent-read-boundary", "mode": mode, "read_calls": len(calls), "requested": calls, "value_hex": value.hex() if value is not None else None, "observed_error": trace(error), "expected_bytes_hex": data[:size].hex() if not expected_exhaustion else None, "expected_success": not expected_exhaustion, "source_attempt_bound": 32, "real_os_read_under_controlled_chunk_or_EINTR_schedule": True}
        if expected_exhaustion:
            observation["required_behavior_pass"] = isinstance(error, p.Refusal) and error.code == "stdio-read-attempts" and len(calls) == 32
        else:
            observation["required_behavior_pass"] = error is None and value == data[:size] and len(calls) <= 32
        print(json.dumps(observation, sort_keys=True), flush=True)
        assert observation["required_behavior_pass"], "completion within the32 allowed reads must succeed"
        return observation
    finally:
        owner.close()
        assert p.ownership_snapshot()["healthy_zero"]


def actual_child(directory, mode):
    body = directory / "body"
    profile = directory / "profile"
    chunk = b"K" * 4096
    digest = hashlib.sha256()
    with body.open("xb") as output:
        for _ in range(625):
            output.write(chunk)
            digest.update(chunk)
    with profile.open("xb") as output:
        output.write(b"H" * 512)
        with body.open("rb") as source:
            while part := source.read(4096):
                output.write(part)
    expected = {"profile": hashlib.sha256(profile.read_bytes()).hexdigest(), "subrange": digest.hexdigest(), "body": digest.hexdigest(), "adoptions": 2}
    processes, streams, close_calls = [], [], []
    original_spawn = p.subprocess.Popen
    original_prepare = p._stdio_prepare
    original_close = p._stdio_close_syscall
    original_complete = p.TerminalStreams.completed
    original_read = os.read
    injected = [OSError("child stderr pre-close"), OSError("child stdout post-close")]
    primary = LookupError("after exact child-step completion")
    completions = []
    child_read_calls = 0
    def spawn(*args, **kwargs):
        assert kwargs["close_fds"] is True and len(kwargs["pass_fds"]) == 2
        assert args[0][1:4] == ["-I", "-S", "-B"]
        process = original_spawn(*args, **kwargs)
        processes.append(process)
        return process
    def prepare(owner):
        streams.append(owner)
        return original_prepare(owner)
    def close(number):
        index = next(i for i, stream in enumerate(streams) if stream._token.number == number)
        close_calls.append(index)
        if mode.startswith("cleanup"):
            if index == 0:
                original_close(number)
            raise injected[index]
        return original_close(number)
    def completed(bundle, value):
        completions.append(value)
        original_complete(bundle, value)
        if mode == "cleanup-primary-result":
            raise primary
    def read(fd, count):
        nonlocal child_read_calls
        if mode in ("read-last", "read-eof-last") and len(streams) == 2 and fd == streams[0]._token.number:
            child_read_calls += 1
            if child_read_calls <= (31 if mode == "read-last" else 30):
                raise InterruptedError("independent child report EINTR")
        return original_read(fd, count)
    with p.CleanupFrame() as frame:
        held_profile = frame.adopt(p.Retained(profile, p.PROFILE))
        held_body = frame.adopt(p.Retained(body, p.BODY))
        with patch.object(p.subprocess, "Popen", spawn), patch.object(p, "_stdio_prepare", prepare), patch.object(p, "_stdio_close_syscall", close), patch.object(p.TerminalStreams, "completed", completed), patch.object(p.os, "read", read):
            value, caught = capture(lambda: p.child_consume(held_profile, held_body, directory))
        assert len(processes) == 1 and processes[0].returncode == 0
        assert close_calls == [1, 0]
        assert not held_profile.live and not held_body.live
        if mode.startswith("cleanup"):
            assert isinstance(caught, p.CleanupAggregate)
            assert caught.primary is (primary if mode == "cleanup-primary-result" else None)
            assert caught.retained_result is completions[0]
            faults = fault_list(caught)
            assert len(faults) == 2
            assert faults[0].exception is injected[1] and faults[1].exception is injected[0]
            actual = caught.retained_result
            assert actual[0] == expected and actual[1]["terminal_reaped"]
        elif mode == "read-last":
            # The real child report is shorter than the512-byte request. A short
            # nonempty32nd read has NOT completed that request or observed EOF.
            assert isinstance(caught, p.Refusal) and caught.code == "stdio-read-attempts"
            assert child_read_calls == 32 and not completions
        elif mode == "read-eof-last":
            assert caught is None and value[0] == expected and value[1]["terminal_reaped"]
            assert child_read_calls == 32
        else:
            assert caught is None and value[0] == expected and value[1]["terminal_reaped"]
    state = p.ownership_snapshot()
    assert state["healthy_zero"] is (not mode.startswith("cleanup"))
    return {"case": "independent-actual-fixed-child", "mode": mode, "child_terminal_reaped": True, "child_exit": 0, "exact_result_join": mode != "read-last", "primary_result_and_all_error_identities": True, "stdio_close_calls": close_calls, "stdout_read_calls": child_read_calls, "expected_bounded_refusal": mode == "read-last", "complete_composition_or_Rust_authority": False}


def main(argv):
    scratch = ROOT / "owned-scratch"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="independent-", dir=scratch) as name:
        directory = Path(name)
        if argv[1] == "close":
            result = closures(directory, argv[2], argv[3], len(argv) > 4)
        elif argv[1] == "acquire":
            result = acquire(directory, int(argv[2]), argv[3], argv[4])
        elif argv[1] == "path-reuse":
            result = path_reuse(directory, argv[2] == "after")
        elif argv[1] == "descriptor-reuse":
            result = descriptor_reuse(directory)
        elif argv[1] == "healthy":
            result = healthy(directory)
        elif argv[1] == "read":
            result = read_boundary(directory, argv[2])
        elif argv[1] == "child":
            result = actual_child(directory, argv[2])
        else:
            raise ValueError("closed case argv")
        result["ownership_before_fixture_cleanup"] = p.ownership_snapshot()
    result["ownership_at_process_exit"] = p.ownership_snapshot()
    result["uncertain_saved_numbers_retried"] = False
    result["real_OS_ambiguity_retired"] = False
    result["process_containment_is_healthy_cleanup"] = False
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main(sys.argv)
    except BaseException:
        print(json.dumps({"case": "required-failure-cleanup-observation", "ownership_after_stack_and_fixture_cleanup": p.ownership_snapshot(), "scratch_entries_remaining": len(list((ROOT / "owned-scratch").iterdir()))}, sort_keys=True), flush=True)
        raise
