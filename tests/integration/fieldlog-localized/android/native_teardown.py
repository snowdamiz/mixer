"""Final observations for the root-owned Android localization replay."""

import os
import subprocess
import time


class UnknownCustody(RuntimeError):
    """The replay must retain the instance's scratch and port reservations."""


def reverse_is_empty(result: subprocess.CompletedProcess[bytes]) -> bool:
    result.check_returncode()
    return not result.stdout.strip()


def reap_owned_session(process: subprocess.Popen, *, reap_seconds=16, group_seconds=4) -> int:
    """Wait after shutdown for a direct child launched with start_new_session=True."""
    try:
        exit_code = process.wait(timeout=reap_seconds)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UnknownCustody(f"Direct child {process.pid} was not reaped") from error

    deadline = time.monotonic() + group_seconds
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return exit_code
        except OSError as error:
            raise UnknownCustody(f"Could not observe owned group {process.pid}") from error
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    raise UnknownCustody(f"Owned group {process.pid} remained after child exit {exit_code}")
