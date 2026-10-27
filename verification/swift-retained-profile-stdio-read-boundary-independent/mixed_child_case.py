"""Real fixed-child terminal result plus nested independent cleanup failures."""
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from boundary_case import ROOT, p, capture, fault_list, inaccessible, trace


def main():
    scratch = ROOT / "owned-scratch"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mixed-independent-", dir=scratch) as name:
        directory = Path(name)
        profile = directory / "profile"
        body = directory / "body"
        data = b"Z" * p.BODY
        body.write_bytes(data)
        profile.write_bytes(b"B" * 512 + data)
        digest = hashlib.sha256(data).hexdigest()
        expected = {"profile": hashlib.sha256(b"B" * 512 + data).hexdigest(), "body": digest, "subrange": digest, "adoptions": 2}
        del data
        primary = KeyError("exact independent primary after completed child")
        retained_error = OSError("exact independent retained preclose")
        stream_errors = [OSError("exact independent stdout postclose"), OSError("exact independent stderr preclose")]
        streams, processes, results, stream_calls, retained_calls = [], [], [], [], []
        original_prepare = p._stdio_prepare
        original_stream_close = p._stdio_close_syscall
        original_complete = p.TerminalStreams.completed
        original_spawn = p.subprocess.Popen
        original_close = os.close
        frame = p.CleanupFrame()
        profile_owner = frame.adopt(p.Retained(profile, p.PROFILE))
        body_owner = frame.adopt(p.Retained(body, p.BODY))
        retained_target = body_owner._leaf
        all_retained = [token for owner in frame.owners for token in owner._tokens]
        numbers = [x.number for x in all_retained]
        def prepare(owner):
            streams.append(owner)
            return original_prepare(owner)
        def spawn(*args, **kwargs):
            process = original_spawn(*args, **kwargs)
            processes.append(process)
            return process
        def completed(bundle, value):
            results.append(value)
            original_complete(bundle, value)
            raise primary
        def stdio_close(number):
            index = next(i for i, owner in enumerate(streams) if owner._token.number == number)
            stream_calls.append(index)
            inaccessible(streams[index])
            if index == 0:
                original_stream_close(number)
            raise stream_errors[index]
        def close(number):
            closing = next((token for token in all_retained if token.number == number and token.state == "closing"), None)
            if closing is not None:
                retained_calls.append(number)
                if closing is retained_target:
                    raise retained_error
            return original_close(number)
        with patch.object(p, "_stdio_prepare", prepare), patch.object(p.subprocess, "Popen", spawn), patch.object(p.TerminalStreams, "completed", completed), patch.object(p, "_stdio_close_syscall", stdio_close), patch.object(p.os, "close", close):
            def composition_step():
                with frame:
                    p.child_consume(profile_owner, body_owner, directory)
            _, caught = capture(composition_step)
            assert isinstance(caught, p.CleanupAggregate)
            assert caught.primary is primary and caught.retained_result is results[0]
            faults = fault_list(caught)
            assert len(faults) == 3
            assert faults[0].exception is stream_errors[1]
            assert faults[1].exception is stream_errors[0]
            assert faults[2].exception is retained_error
            assert results[0][0] == expected and results[0][1]["terminal_reaped"]
            assert len(processes) == 1 and processes[0].returncode == 0
            assert stream_calls == [1, 0]
            assert len(retained_calls) == len(set(retained_calls)) == len(all_retained)
            assert sorted(retained_calls) == sorted(numbers)
            before = (tuple(retained_calls), tuple(stream_calls))
            for owner in frame.owners + streams:
                capture(owner.close)
            gc.collect()
            assert (tuple(retained_calls), tuple(stream_calls)) == before
        os.fstat(retained_target.number)
        state = p.ownership_snapshot()
        assert state["uncertain_close_records"] == 1 and state["stdio_uncertain_close_records"] == 2
        assert state["owners"] == 1 and state["stdio_owners"] == 2 and not state["healthy_zero"]
        output = {"case": "independent-real-child-nested-cleanup-join", "actual_fixed_child_terminal_reaped": True, "child_exit": processes[0].returncode, "exact_primary_identity": True, "exact_completed_child_result_identity": True, "all_three_cleanup_exception_identities": True, "all_independent_retained_descriptors_attempted_once": len(all_retained), "stream_close_order": stream_calls, "known_preclose_retained_descriptor_actually_open": True, "original_primary": trace(primary), "cleanup_exceptions": [trace(f.exception) for f in faults], "ownership_before_fixture_cleanup": state}
    assert p.ownership_snapshot() == state
    output["ownership_at_process_exit"] = state
    output["real_OS_ambiguity_retired"] = False
    output["uncertain_saved_numbers_retried"] = False
    output["fixture_directory_cleanup_is_healthy_cleanup"] = False
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
