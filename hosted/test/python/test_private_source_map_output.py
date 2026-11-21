"""Filesystem fault controls for the private source-map export helper."""

from contextlib import redirect_stderr
import errno
import importlib.util
import io
import os
import select
from pathlib import Path
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch


helper = Path(__file__).resolve().parents[2] / "priv/local_source_map_retention/private_output.py"
spec = importlib.util.spec_from_file_location("private_output", helper)
output = importlib.util.module_from_spec(spec)
spec.loader.exec_module(output)


class PrivateSourceMapOutputTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.destination = self.directory / "export"
        self.parent = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, self.parent)

    def export(self, authorize=lambda: True):
        output.write_new_file(self.parent, "export", os.geteuid(), b"synthetic-map", authorize)

    def assert_clean_retry(self):
        self.assertEqual(list(self.directory.iterdir()), [])
        self.export()
        self.assertEqual(self.destination.read_bytes(), b"synthetic-map")
        self.assertEqual(list(self.directory.iterdir()), [self.destination])

    def test_destination_arriving_after_stage_preserves_its_inode(self):
        collision = None

        def collide():
            nonlocal collision
            self.assertFalse(self.destination.exists())
            self.destination.write_bytes(b"existing")
            collision = self.destination.stat()
            return True

        with self.assertRaises(FileExistsError):
            self.export(collide)
        self.assertTrue(os.path.samestat(collision, self.destination.stat()))
        self.assertEqual(self.destination.read_bytes(), b"existing")
        self.assertEqual(list(self.directory.iterdir()), [self.destination])

    def test_partial_write_failure_touches_only_private_staging(self):
        write = os.write

        def fail_after_a_prefix(fd, payload):
            if len(payload) == len(b"synthetic-map"):
                return write(fd, payload[:1])
            raise OSError(errno.ENOSPC, "injected write failure")

        with patch.object(output.os, "write", side_effect=fail_after_a_prefix):
            with self.assertRaises(OSError) as error:
                self.export()
        self.assertEqual(error.exception.errno, errno.ENOSPC)
        self.assert_clean_retry()

    def test_fstat_failure_cleans_stage_and_allows_retry(self):
        fstat = os.fstat

        def fail_on_file(fd):
            entry = fstat(fd)
            if stat.S_ISREG(entry.st_mode):
                raise OSError(errno.EIO, "injected fstat failure")
            return entry

        with patch.object(output.os, "fstat", side_effect=fail_on_file):
            with self.assertRaises(OSError) as error:
                self.export()
        self.assertEqual(error.exception.errno, errno.EIO)
        self.assert_clean_retry()

    def test_abandonment_after_staging_leaves_no_export(self):
        with self.assertRaises(PermissionError):
            self.export(lambda: False)
        self.assert_clean_retry()

    def test_uncertain_rename_preserves_staging(self):
        with patch.object(output, "rename_no_replace", side_effect=output.IndeterminateOutput):
            with self.assertRaises(output.IndeterminateOutput):
                self.export()
        self.assertFalse(self.destination.exists())
        [staging] = self.directory.iterdir()
        self.assertTrue(staging.name.startswith(".mixer-source-map-"))
        self.assertEqual((staging / "payload").read_bytes(), b"synthetic-map")

    def test_wall_expiry_during_permission_read_refuses_publication(self):
        connection = Mock()
        wall_now = 99 * 10**9
        chunks = iter([struct.pack("!I", 5), b"inert", b"P"])

        def receive(_size):
            nonlocal wall_now
            chunk = next(chunks)
            if chunk == b"P":
                wall_now = 100 * 10**9
            return chunk

        connection.recv.side_effect = receive
        connection.send.side_effect = len
        with (patch.object(output.time, "time_ns", side_effect=lambda: wall_now),
              patch.object(output.socket, "socket") as socket_factory):
            socket_factory.return_value.__enter__.return_value = connection
            with self.assertRaises(output.ReadExpired):
                output.worker(str(self.destination), time.monotonic() + 5, 100)

        connection.send.assert_called_once_with(b"R")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_owned_worker_exports_the_maximum_and_preserves_an_existing_destination(self):
        payload = bytes([0, 255, 1, 254]) * (1024 * 1024)
        self.assertEqual(output.publish(self.destination, payload, time.monotonic() + 5), 0)
        original = self.destination.stat()
        self.assertEqual(stat.S_IMODE(original.st_mode), 0o600)
        self.assertEqual(original.st_nlink, 1)
        self.assertEqual(output.publish(self.destination, b"other", time.monotonic() + 5), 1)
        self.assertTrue(os.path.samestat(original, self.destination.stat()))
        self.assertEqual(self.destination.read_bytes(), payload)
        self.assertEqual(list(self.directory.iterdir()), [self.destination])

    def test_actual_launch_after_expiry_is_reaped_without_receiving_any_bytes(self):
        observed = self.directory / "observed"
        popen = subprocess.Popen
        children = []
        deadline = time.monotonic() + 0.1

        def late_launch(_args, **options):
            time.sleep(max(0, deadline - time.monotonic()) + 0.05)
            child = popen(
                [sys.executable, "-I", "-S", "-B", "-c",
                 "import os,sys; data = os.read(0,4096); "
                 "open(sys.argv[1],'xb').write(str(os.getpid()).encode()+b':' + data)",
                 observed],
                **options,
            )
            children.append(child)
            return child

        errors = io.StringIO()
        with patch.object(output.subprocess, "Popen", side_effect=late_launch), redirect_stderr(errors):
            self.assertEqual(output.publish(self.destination, b"inert", deadline), 2)

        [child] = children
        self.assertEqual(observed.read_bytes(), f"{child.pid}:".encode())
        self.assertEqual(errors.getvalue(), f"output_indeterminate helper_pid={child.pid}\n")
        self.assertEqual(child.returncode, 0)
        with self.assertRaises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.directory.iterdir()), [observed])

    def test_ready_after_expiry_gets_eof_and_is_reaped(self):
        observed = self.directory / "observed"
        popen = subprocess.Popen
        children = []
        deadline = time.monotonic() + 0.5

        def slow_stage(_args, **options):
            child = popen(
                [sys.executable, "-I", "-S", "-B", "-c", """
import os, socket, sys, time
with socket.socket(fileno=0) as connection:
    received = connection.recv(9, socket.MSG_WAITALL)
    assert received == b"\\x00\\x00\\x00\\x05inert"
    time.sleep(max(0, float(sys.argv[2]) - time.monotonic()) + 0.05)
    try:
        connection.sendall(b"R")
    except BrokenPipeError:
        pass
    assert connection.recv(1) == b""
open(sys.argv[1], "xb").write(b"closed without permission")
""", observed, str(deadline)],
                **options,
            )
            children.append(child)
            return child

        with patch.object(output.subprocess, "Popen", side_effect=slow_stage), redirect_stderr(io.StringIO()):
            self.assertEqual(output.publish(self.destination, b"inert", deadline), 2)

        [child] = children
        self.assertEqual(observed.read_bytes(), b"closed without permission")
        self.assertEqual(child.returncode, 0)
        self.assertFalse(self.destination.exists())

    def test_worker_authorized_before_expiry_may_finish_late_with_indeterminate_result(self):
        observed = self.directory / "observed"
        popen = subprocess.Popen
        children = []
        deadline = time.monotonic() + 0.5

        def slow_finish(_args, **options):
            child = popen(
                [sys.executable, "-I", "-S", "-B", "-c", """
import socket, sys, time
with socket.socket(fileno=0) as connection:
    assert len(connection.recv(9, socket.MSG_WAITALL)) == 9
    connection.sendall(b"R")
    assert connection.recv(1) == b"P"
    time.sleep(max(0, float(sys.argv[2]) - time.monotonic()) + 0.05)
open(sys.argv[1], "xb").write(b"permitted worker finished late")
""", observed, str(deadline)],
                **options,
            )
            children.append(child)
            return child

        errors = io.StringIO()
        with patch.object(output.subprocess, "Popen", side_effect=slow_finish), redirect_stderr(errors):
            self.assertEqual(output.publish(self.destination, b"inert", deadline), 2)

        [child] = children
        self.assertEqual(observed.read_bytes(), b"permitted worker finished late")
        self.assertEqual(errors.getvalue(), f"output_indeterminate helper_pid={child.pid}\n")
        self.assertEqual(child.returncode, 0)


class PrivateSourceMapAuthorizationTest(unittest.TestCase):
    def test_mix_does_not_send_a_response_for_an_expired_map(self):
        script = helper.parents[2] / "scripts/private-source-map.exs"
        stub = """
defmodule MixerHosted.Releases.SourceMapOperator do
  def main(_, _), do: {:ok, %{bytes: "inert", retain_until: 4102444800, valid_until: 1}}
end
Code.require_file(System.fetch_env!("INERT_OPERATOR_SCRIPT"))
"""
        connection, endpoint = socket.socketpair()
        with connection, endpoint:
            env = {key: value for key, value in os.environ.items() if not key.startswith("MIXER_")}
            env.update(INERT_OPERATOR_SCRIPT=str(script),
                       MIXER_PRIVATE_SOURCE_MAP_FD=str(endpoint.fileno()))
            with subprocess.Popen(
                ["elixir", "-e", stub, "--", "read", "1", "inert"], env=env,
                pass_fds=(endpoint.fileno(),), stderr=subprocess.PIPE,
            ) as child:
                endpoint.close()
                connection.settimeout(10)
                with connection:
                    self.assertEqual(connection.recv(4096), b"")
                errors = child.communicate(timeout=5)[1]
        self.assertEqual(child.returncode, 1)
        self.assertEqual(errors, b"not_found\n")

    def test_expired_header_is_refused_before_body_read(self):
        self.assert_refusal_before_body(expiry=100, wall_seconds=100)

    def test_out_of_range_header_is_refused_before_body_read(self):
        self.assert_refusal_before_body(expiry=2**53, wall_seconds=100)

    def test_invalid_frame_size_or_deadline_order_is_refused_before_body_read(self):
        self.assert_refusal_before_body(expiry=101, wall_seconds=100, size=4 * 1024**2 + 1)
        self.assert_refusal_before_body(expiry=101, wall_seconds=100, retention=100)

    def assert_refusal_before_body(self, expiry, wall_seconds, retention=None, size=5):
        frame = struct.pack("!QQI", retention or expiry, expiry, size) + b"inert"
        inert = """
import os, socket, sys
with socket.socket(fileno=int(os.environ["MIXER_PRIVATE_SOURCE_MAP_FD"])) as connection:
    connection.sendall(bytes.fromhex(sys.argv[1]))
"""
        requests = []
        receive = output.receive_exact

        def observe(connection, size, *args, **kwargs):
            requests.append(size)
            return receive(connection, size, *args, **kwargs)

        errors = io.StringIO()
        with (patch.object(output, "receive_exact", side_effect=observe),
              patch.object(output.time, "time", return_value=wall_seconds),
              patch.object(output.time, "time_ns", return_value=wall_seconds * 10**9),
              redirect_stderr(errors)):
            status = output.main(["read", "1", "inert", "/inert/export"],
                                 (sys.executable, "-I", "-S", "-B", "-c", inert, frame.hex()))
        self.assertEqual(status, 1)
        self.assertEqual(requests, [1, 19])

    def test_expiry_between_header_and_body_is_checked_on_both_sides_of_recv(self):
        for during_body in (False, True):
            with self.subTest(during_body=during_body):
                connection = Mock()
                wall_now = 99 * 10**9
                header = struct.pack("!QQI", 200, 100, 5)
                chunks = iter([header[:1], header[1:], b"inert"])

                def receive(_size):
                    nonlocal wall_now
                    chunk = next(chunks)
                    if during_body and chunk == b"inert":
                        wall_now = 100 * 10**9
                    return chunk

                def acknowledge(_ready):
                    nonlocal wall_now
                    if not during_body:
                        wall_now = 100 * 10**9
                    return 1

                connection.recv.side_effect = receive
                connection.send.side_effect = acknowledge
                child = Mock()
                with patch.object(output.time, "time_ns", side_effect=lambda: wall_now):
                    with self.assertRaises(output.ReadExpired):
                        output.read_authorized_frame(connection, child, lambda: None)

                connection.send.assert_called_once_with(b"A")
                self.assertEqual(connection.recv.call_count, 3 if during_body else 2)
                child.wait.assert_not_called()

    def test_backpressured_mix_rechecks_expiry_after_queued_readiness(self):
        script = helper.parents[2] / "scripts/private-source-map.exs"
        stub = """
defmodule MixerHosted.Releases.SourceMapOperator do
  def main(_, _) do
    expiry = System.system_time(:second) + 3
    {:ok, %{bytes: :binary.copy("x", 4 * 1024 * 1024),
            retain_until: expiry + 60, valid_until: expiry}}
  end
end

:socket.info()
parent = self()
writer = spawn(fn ->
  receive do
    :start ->
      Code.require_file(System.fetch_env!("INERT_OPERATOR_SCRIPT"))
      send(parent, :done)
  end
end)
:erlang.trace_pattern({:socket, :send, 4}, [{:_, [], [{:return_trace}]}], [])
:erlang.trace(writer, true, [:call])
send(writer, :start)
receive do
  {:trace, ^writer, :return_from, {:socket, :send, 4}, :ok} -> :ok
after
  5_000 -> raise "missing header send"
end
receive do
  {:trace, ^writer, :return_from, {:socket, :send, 4}, {:select, _}} -> :ok
after
  3_000 -> raise "missing send backpressure"
end
true = :erlang.suspend_process(writer)
IO.puts("blocked")

wait_for_ready = fn loop, attempts ->
  {:messages, messages} = Process.info(writer, :messages)
  cond do
    Enum.any?(messages, &match?({:"$socket", _, :select, _}, &1)) -> :ok
    attempts == 0 -> raise "missing queued readiness"
    true -> Process.sleep(10); loop.(loop, attempts - 1)
  end
end
wait_for_ready.(wait_for_ready, 100)
IO.puts("ready")
"resume\n" = IO.gets("")
true = :erlang.resume_process(writer)
receive do
  :done -> System.halt(0)
after
  3_000 -> raise "missing writer exit"
end
"""
        connection, endpoint = socket.socketpair()
        with connection, endpoint:
            endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
            env = {key: value for key, value in os.environ.items() if not key.startswith("MIXER_")}
            env.update(INERT_OPERATOR_SCRIPT=str(script),
                       MIXER_PRIVATE_SOURCE_MAP_FD=str(endpoint.fileno()))
            child = subprocess.Popen(
                ["elixir", "-e", stub, "--", "read", "1", "inert"], env=env,
                pass_fds=(endpoint.fileno(),), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, bufsize=0,
            )
            try:
                endpoint.close()
                connection.settimeout(5)
                header = connection.recv(output.AUTHORIZATION_HEADER.size, socket.MSG_WAITALL)
                retention, expiry, size = output.AUTHORIZATION_HEADER.unpack(header)
                self.assertLess(expiry, retention)
                connection.sendall(b"A")

                def expect(line):
                    self.assertTrue(select.select([child.stdout], [], [], 5)[0])
                    self.assertEqual(child.stdout.readline(), line)

                expect(b"blocked\n")
                received = 0
                connection.setblocking(False)
                while received < size:
                    try:
                        chunk = connection.recv(65536)
                    except BlockingIOError:
                        break
                    self.assertTrue(chunk)
                    received += len(chunk)
                self.assertGreater(received, 0)
                self.assertLess(received, size)
                expect(b"ready\n")
                time.sleep(max(0, expiry - time.time()) + 0.05)
                child.stdin.write(b"resume\n")
                connection.settimeout(5)
                self.assertEqual(connection.recv(65536), b"")
                self.assertEqual(child.communicate(timeout=5)[1], b"not_found\n")
                self.assertEqual(child.returncode, 1)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
                for pipe in (child.stdin, child.stdout, child.stderr):
                    pipe.close()

    def test_sigint_after_successful_frame_and_reap_has_already_proved_group_absence(self):
        self.assert_completed_frame_custody(interrupt_after_return=True, deny_observation=False)

    def test_unobservable_group_blocks_publication_after_successful_frame(self):
        self.assert_completed_frame_custody(interrupt_after_return=False, deny_observation=True)

    def assert_completed_frame_custody(self, interrupt_after_return, deny_observation):
        inert = """
import os, socket, struct, time
with socket.socket(fileno=int(os.environ["MIXER_PRIVATE_SOURCE_MAP_FD"])) as connection:
    connection.settimeout(5)
    expiry = int(time.time()) + 30
    connection.sendall(struct.pack("!QQI", expiry + 60, expiry, 5))
    assert connection.recv(1) == b"A"
    connection.sendall(b"inert")
"""
        read_owned = output.read_from_owned_mix
        killpg = os.killpg
        observed = []

        def observe_group(group, sig):
            self.assertEqual(sig, 0)
            observed.append(group)
            if deny_observation:
                # A late interrupt must not obscure unknown group custody.
                os.kill(os.getpid(), signal.SIGINT)
                raise PermissionError(errno.EPERM, "injected group observation denial")
            return killpg(group, 0)

        def read_then_interrupt(*args):
            result = read_owned(*args)
            if interrupt_after_return:
                os.kill(os.getpid(), signal.SIGINT)
            return result

        errors = io.StringIO()
        with (patch.object(output, "read_from_owned_mix", side_effect=read_then_interrupt),
              patch.object(output.os, "killpg", side_effect=observe_group),
              patch.object(output, "publish") as publish, redirect_stderr(errors)):
            status = output.main(["read", "1", "inert", "/inert/export"],
                                 (sys.executable, "-I", "-S", "-B", "-c", inert))
        publish.assert_not_called()
        [pid] = observed
        if deny_observation:
            self.assertEqual(status, 2)
            self.assertEqual(errors.getvalue(),
                             f"authorization_indeterminate mix_pid={pid} mix_pgid={pid} "
                             "mix_reaped=true\n")
        else:
            self.assertEqual(status, 130)
            self.assertEqual(errors.getvalue(), "authorization_interrupted\n")
        with self.assertRaises(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)
        with self.assertRaises(ProcessLookupError):
            os.killpg(pid, 0)

    def test_directed_sigint_during_authorization_reaps_mix(self):
        self.assert_interrupt_reaps_mix(during_launch=False)

    def test_directed_sigint_during_launch_handoff_reaps_mix(self):
        self.assert_interrupt_reaps_mix(during_launch=True)

    def test_unknown_group_absence_reports_mix_pid_and_pgid(self):
        self.assert_interrupt_reaps_mix(during_launch=True, deny_observation=True)

    def assert_interrupt_reaps_mix(self, during_launch, deny_observation=False):
        inert = """
import os, signal, socket, sys, time
with socket.socket(fileno=int(os.environ["MIXER_PRIVATE_SOURCE_MAP_FD"])) as connection:
    connection.settimeout(5)
    if sys.argv[1] == "interrupt":
        time.sleep(0.2)
        os.kill(os.getppid(), signal.SIGINT)
    assert connection.recv(1) == b""
"""
        popen = subprocess.Popen
        killpg = os.killpg
        children = []

        def owned_launch(args, **options):
            child = popen(args, **options)
            children.append(child)
            if during_launch:
                os.kill(os.getpid(), signal.SIGINT)
            return child

        def observe_group(group, sig):
            self.assertEqual(group, children[0].pid)
            if deny_observation and sig == 0:
                raise PermissionError(errno.EPERM, "injected process-group observation denial")
            return killpg(group, sig)

        arg = "wait" if during_launch else "interrupt"
        errors = io.StringIO()
        try:
            with (patch.object(output.subprocess, "Popen", side_effect=owned_launch),
                  patch.object(output.os, "killpg", side_effect=observe_group),
                  redirect_stderr(errors)):
                status = output.main(["read", "1", "inert", "/inert/export"],
                                     (sys.executable, "-I", "-S", "-B", "-c", inert, arg))
            [child] = children
            if deny_observation:
                self.assertEqual(status, 2)
                self.assertEqual(errors.getvalue(),
                                 f"authorization_indeterminate mix_pid={child.pid} "
                                 f"mix_pgid={child.pid} mix_reaped=true\n")
            else:
                self.assertEqual(status, 130)
                self.assertEqual(errors.getvalue(), "authorization_interrupted\n")
            self.assertIsNotNone(child.returncode)
            with self.assertRaises(ChildProcessError):
                os.waitpid(child.pid, os.WNOHANG)
            with self.assertRaises(ProcessLookupError):
                os.killpg(child.pid, 0)
        except KeyboardInterrupt:
            self.fail("SIGINT escaped before the foreground could account for Mix")
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
