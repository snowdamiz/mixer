"""Foreground operator for reading a retained private source map."""

import ctypes
import errno
import math
import os
import secrets
import select
import signal
import socket
import struct
import subprocess
import stat
import sys
import time


MAXIMUM_BYTES = 4 * 1024 * 1024
MAXIMUM_RETENTION = 2**53 - 1
OUTPUT_SECONDS = 5
AUTHORIZATION_SECONDS = 30
TRANSFER_CHUNK_BYTES = 64 * 1024
AUTHORIZATION_HEADER = struct.Struct("!QQI")
INTERRUPT_POLL_SECONDS = 0.1


if sys.platform == "darwin":
    # The 64-bit Darwin statfs layout from <sys/mount.h>.
    class MountInfo(ctypes.Structure):
        _fields_ = [
            ("block_size", ctypes.c_uint32), ("io_size", ctypes.c_int32),
            ("counts", ctypes.c_uint64 * 5), ("fsid", ctypes.c_int32 * 2),
            ("owner", ctypes.c_uint32), ("type_number", ctypes.c_uint32),
            ("flags", ctypes.c_uint32), ("subtype", ctypes.c_uint32),
            ("fs_type", ctypes.c_char * 16), ("names", ctypes.c_char * 2048),
            ("extended_flags", ctypes.c_uint32), ("reserved", ctypes.c_uint32 * 7),
        ]

    libc = ctypes.CDLL(None, use_errno=True)
    mount_info = getattr(
        libc, "fstatfs$INODE64" if os.uname().machine == "x86_64" else "fstatfs"
    )
    libc.acl_get_fd.argtypes = [ctypes.c_int]
    libc.acl_get_fd.restype = ctypes.c_void_p
    libc.acl_free.argtypes = [ctypes.c_void_p]

    def supported_mount(info):
        mnt_local = 0x00001000
        mnt_ignore_ownership = 0x00200000
        mnt_ext_fskit = 0x00000002
        return (info.fs_type == b"apfs" and info.flags & mnt_local
                and not info.flags & mnt_ignore_ownership
                and not info.extended_flags & mnt_ext_fskit)

    def acl_absent(fd, _directory):
        ctypes.set_errno(0)
        acl = libc.acl_get_fd(fd)
        if acl is None:
            return ctypes.get_errno() == errno.ENOENT
        libc.acl_free(acl)
        return False

elif sys.platform == "linux":
    # The 64-bit Linux statfs layout from <sys/vfs.h>.
    class MountInfo(ctypes.Structure):
        _fields_ = [
            ("fs_type", ctypes.c_long), ("block_size", ctypes.c_long),
            ("counts", ctypes.c_ulong * 5), ("fsid", ctypes.c_int * 2),
            ("name_len", ctypes.c_long), ("fragment_size", ctypes.c_long),
            ("flags", ctypes.c_long), ("reserved", ctypes.c_long * 4),
        ]

    libc = ctypes.CDLL(None, use_errno=True)
    mount_info = libc.fstatfs

    def supported_mount(info):
        # ext2/3/4, tmpfs, XFS and Btrfs implement kernel POSIX permissions.
        return info.fs_type in (0xEF53, 0x01021994, 0x58465342, 0x9123683E)

    def missing_acl(fd, name):
        try:
            os.getxattr(fd, name)
        except OSError as error:
            return error.errno == errno.ENODATA
        return False

    def acl_absent(fd, directory):
        return (missing_acl(fd, "system.posix_acl_access")
                and (not directory or missing_acl(fd, "system.posix_acl_default")))


def private_filesystem_object(fd, directory):
    info = MountInfo()
    return (mount_info(fd, ctypes.byref(info)) == 0 and supported_mount(info)
            and acl_absent(fd, directory))


def open_parent(parts, uid):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for part in parts:
            entry = os.fstat(fd)
            # A sticky shared ancestor can host a trusted owner's directory.
            if (entry.st_uid not in (0, uid)
                    or (entry.st_mode & 0o022 and not entry.st_mode & stat.S_ISVTX)
                    or not private_filesystem_object(fd, directory=True)):
                raise PermissionError
            previous, fd = fd, os.open(part, flags, dir_fd=fd)
            os.close(previous)
        entry = os.fstat(fd)
        if (entry.st_uid != uid or stat.S_IMODE(entry.st_mode) != 0o700
                or not private_filesystem_object(fd, directory=True)):
            raise PermissionError
    except BaseException:
        os.close(fd)
        raise
    return fd


class IndeterminateOutput(Exception):
    """The rename or owned staging cleanup could not be confirmed."""


def rename_no_replace(stage, parent, name):
    if sys.platform == "darwin":
        rename = libc.renameatx_np
        no_replace = 0x00000004  # RENAME_EXCL
    else:
        rename = libc.renameat2
        no_replace = 1  # RENAME_NOREPLACE
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                       ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(stage, b"payload", parent, os.fsencode(name), no_replace) != 0:
        error = ctypes.get_errno()
        if error == errno.EIO:
            raise IndeterminateOutput
        raise OSError(error, os.strerror(error))


def write_payload(fd, uid, payload):
    entry = os.fstat(fd)
    if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != uid
            or entry.st_nlink != 1 or entry.st_size != 0
            or stat.S_IMODE(entry.st_mode) != 0o600
            or not private_filesystem_object(fd, directory=False)):
        raise PermissionError
    remaining = memoryview(payload)
    while remaining:
        count = os.write(fd, remaining)
        if count == 0:
            raise OSError
        remaining = remaining[count:]
    os.fsync(fd)


def remove_stage_entry(remove, name, directory):
    try:
        remove(name, dir_fd=directory)
    except OSError as error:
        raise IndeterminateOutput from error


def close_directory(fd):
    try:
        os.close(fd)
    except OSError as error:
        raise IndeterminateOutput from error


def stage_payload(stage, parent, name, uid, payload, authorize):
    entry = os.fstat(stage)
    if (entry.st_uid != uid or stat.S_IMODE(entry.st_mode) != 0o700
            or not private_filesystem_object(stage, directory=True)):
        raise PermissionError
    fd = os.open("payload", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=stage)
    try:
        try:
            write_payload(fd, uid, payload)
        finally:
            os.close(fd)
        if not authorize():
            raise PermissionError
        rename_no_replace(stage, parent, name)
    except IndeterminateOutput:
        raise
    except Exception:
        remove_stage_entry(os.unlink, "payload", stage)
        raise


def write_new_file(parent, name, uid, payload, authorize):
    staging = ".mixer-source-map-" + secrets.token_hex(16)
    os.mkdir(staging, 0o700, dir_fd=parent)
    try:
        stage = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=parent)
        try:
            stage_payload(stage, parent, name, uid, payload, authorize)
        finally:
            close_directory(stage)
    except IndeterminateOutput:
        raise
    except Exception:
        remove_stage_entry(os.rmdir, staging, parent)
        raise
    remove_stage_entry(os.rmdir, staging, parent)


class ReadExpired(OSError):
    """The authorization window for the private map closed during the read."""


def validity_remaining(valid_until):
    nanoseconds = valid_until * 10**9 - time.time_ns()
    if nanoseconds <= 0:
        raise ReadExpired
    return nanoseconds / 10**9


def remaining(deadline, valid_until=None):
    seconds = deadline - time.monotonic()
    if valid_until is not None:
        seconds = min(seconds, validity_remaining(valid_until))
    if seconds <= 0:
        raise TimeoutError
    return seconds


def wait_for_socket(connection, event, deadline, valid_until):
    poll = select.poll()
    poll.register(connection, event)
    seconds = min(remaining(deadline, valid_until), INTERRUPT_POLL_SECONDS)
    poll.poll(math.ceil(seconds * 1000))


def receive_exact(connection, size, deadline, *, valid_until=None, checkpoint=lambda: None):
    data = bytearray()
    connection.setblocking(False)
    while len(data) < size:
        checkpoint()
        remaining(deadline, valid_until)
        try:
            chunk = connection.recv(min(size - len(data), TRANSFER_CHUNK_BYTES))
        except BlockingIOError:
            wait_for_socket(connection, select.POLLIN, deadline, valid_until)
            continue
        remaining(deadline, valid_until)
        if not chunk:
            break
        data.extend(chunk)
    return data


def send_exact(connection, payload, deadline, valid_until, checkpoint=lambda: None):
    connection.setblocking(False)
    unsent = memoryview(payload)
    while unsent:
        checkpoint()
        remaining(deadline, valid_until)
        try:
            sent = connection.send(unsent[:TRANSFER_CHUNK_BYTES])
        except BlockingIOError:
            wait_for_socket(connection, select.POLLOUT, deadline, valid_until)
            continue
        if sent == 0:
            raise BrokenPipeError
        unsent = unsent[sent:]
    remaining(deadline, valid_until)


def worker(path, deadline, valid_until):
    if (sys.platform not in ("darwin", "linux") or ctypes.sizeof(ctypes.c_long) != 8
            or os.uname().machine not in ("arm64", "aarch64", "x86_64")):
        return 1
    mount_info.argtypes = [ctypes.c_int, ctypes.POINTER(MountInfo)]
    mount_info.restype = ctypes.c_int

    parts = path.split("/")
    if parts[0] != "" or len(parts) < 3 or any(p in ("", ".", "..") for p in parts[1:]):
        return 1

    with socket.socket(fileno=0) as connection:
        header = receive_exact(connection, 4, deadline, valid_until=valid_until)
        size = int.from_bytes(header, "big")
        if len(header) != 4 or not 1 <= size <= MAXIMUM_BYTES:
            return 1
        payload = receive_exact(connection, size, deadline, valid_until=valid_until)
        if len(payload) != size:
            return 1
        remaining(deadline, valid_until)

        def authorize():
            send_exact(connection, b"R", deadline, valid_until)
            permission = receive_exact(connection, 1, deadline, valid_until=valid_until)
            remaining(deadline, valid_until)
            return permission == b"P"

        uid = os.geteuid()
        parent = open_parent(parts[1:-1], uid)
        try:
            write_new_file(parent, parts[-1], uid, payload, authorize)
        finally:
            close_directory(parent)
    return 0


def publish(path, payload, deadline, valid_until=None):
    cancelled = False

    def cancel(_signum, _frame):
        nonlocal cancelled
        cancelled = True

    handlers = {sig: signal.signal(sig, cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        return publish_owned(path, payload, deadline, valid_until, lambda: cancelled)
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


def publish_owned(path, payload, deadline, valid_until, cancelled):
    connection, endpoint = socket.socketpair()
    with connection, endpoint:
        remaining(deadline, valid_until)
        if cancelled():
            return 1
        # The foreground owns launch through PID acquisition even when
        # the call returns after the deadline.
        child = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", os.path.abspath(__file__),
             "--publish-worker", path, repr(deadline), str(valid_until or 0)],
            stdin=endpoint, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={}, start_new_session=True,
        )
        permitted = False
        try:
            endpoint.close()
            with connection:
                try:
                    if not cancelled():
                        send_exact(connection, struct.pack("!I", len(payload)), deadline, valid_until)
                        send_exact(connection, payload, deadline, valid_until)
                        ready = receive_exact(connection, 1, deadline, valid_until=valid_until)
                        if ready == b"R" and not cancelled():
                            send_exact(connection, b"P", deadline, valid_until)
                            permitted = True
                except (BrokenPipeError, ConnectionResetError):
                    pass
            status = child.wait(timeout=remaining(deadline))
        except (OSError, subprocess.TimeoutExpired):
            return report_indeterminate(child.pid)
        finally:
            # EOF revokes any permission still outstanding. Keep the foreground
            # alive until the exact direct child is reaped, including on expiry.
            try:
                connection.close()
            finally:
                child.wait()

    if status == 0 and permitted:
        return 0
    if status == 1:
        return 1
    return report_indeterminate(child.pid)


def report_indeterminate(pid):
    print(f"output_indeterminate helper_pid={pid}", file=sys.stderr, flush=True)
    return 2


class AuthorizationInterrupted(Exception):
    """The foreground accounted for the authorizer before reporting SIGINT."""


class AuthorizationIndeterminate(Exception):
    """The authorizer's process group could not be confirmed gone."""

    def __init__(self, child):
        super().__init__(child.pid)
        self.pid = child.pid
        self.reaped = child.returncode is not None


def stop_authorizer(child):
    deadline = time.monotonic() + OUTPUT_SECONDS
    try:
        if child.returncode is None:
            try:
                # The direct child still owns this PID, even if already exited.
                os.killpg(child.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                # The child might still exit after the socket closed. Observe it.
                pass
            child.wait(timeout=remaining(deadline))
        while True:
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                return
            time.sleep(min(remaining(deadline), INTERRUPT_POLL_SECONDS))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AuthorizationIndeterminate(child) from error


def wait_for_authorizer(child, checkpoint, deadline, valid_until=None):
    while True:
        checkpoint()
        timeout = min(INTERRUPT_POLL_SECONDS, remaining(deadline, valid_until))
        try:
            status = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            continue
        remaining(deadline, valid_until)
        return status


def read_authorized_frame(connection, child, checkpoint):
    # Allow time for local Mix startup and authorization before the output window.
    startup_deadline = time.monotonic() + AUTHORIZATION_SECONDS
    first = receive_exact(connection, 1, startup_deadline, checkpoint=checkpoint)
    if not first:
        return wait_for_authorizer(child, checkpoint, startup_deadline), None
    deadline = time.monotonic() + OUTPUT_SECONDS
    header = first + receive_exact(connection, AUTHORIZATION_HEADER.size - 1, deadline,
                                   checkpoint=checkpoint)
    if len(header) != AUTHORIZATION_HEADER.size:
        raise OSError
    retain_until, valid_until, size = AUTHORIZATION_HEADER.unpack(header)
    if not 1 <= valid_until <= retain_until <= MAXIMUM_RETENTION or not 1 <= size <= MAXIMUM_BYTES:
        raise OSError

    # Keep the monotonic cap even if the wall clock subsequently moves back.
    now = time.monotonic()
    deadline = min(deadline, now + validity_remaining(valid_until))
    send_exact(connection, b"A", deadline, valid_until, checkpoint)
    payload = receive_exact(
        connection, size, deadline, valid_until=valid_until, checkpoint=checkpoint
    )
    if len(payload) != size or receive_exact(
        connection, 1, deadline, valid_until=valid_until, checkpoint=checkpoint
    ):
        raise OSError
    status = wait_for_authorizer(child, checkpoint, deadline, valid_until)
    return status, (retain_until, valid_until, payload, deadline)


def read_from_mix(sequence, digest, mix_command):
    interrupted = False

    def interrupt(_signum, _frame):
        nonlocal interrupted
        interrupted = True

    def checkpoint():
        if interrupted:
            raise AuthorizationInterrupted

    # A raising handler could unwind Popen after spawn but before PID
    # acquisition. Record SIGINT through launch, transfer and exact-child reap.
    previous = signal.signal(signal.SIGINT, interrupt)
    try:
        result = read_from_owned_mix(sequence, digest, mix_command, checkpoint)
    finally:
        signal.signal(signal.SIGINT, previous)
    checkpoint()
    return result


def read_from_owned_mix(sequence, digest, mix_command, checkpoint):
    connection, endpoint = socket.socketpair()
    with connection, endpoint:
        env = dict(os.environ, MIXER_PRIVATE_SOURCE_MAP_FD=str(endpoint.fileno()))
        checkpoint()
        try:
            child = subprocess.Popen(
                [*mix_command, "read", sequence, digest], env=env, pass_fds=(endpoint.fileno(),),
                start_new_session=True,
            )
        except OSError:
            checkpoint()
            raise
        try:
            with connection:
                endpoint.close()
                return read_authorized_frame(connection, child, checkpoint)
        finally:
            # A successful wait only reaps Mix. Observe its group before any
            # result leaves this scope, even for SIGINT delivered after wait.
            stop_authorizer(child)
            checkpoint()


def main(args, mix_command=("mix", "run", "--no-start", "scripts/private-source-map.exs")):
    if len(args) != 4 or args[0] != "read":
        print("invalid_request", file=sys.stderr)
        return 1

    _, sequence, digest, path = args
    try:
        status, result = read_from_mix(sequence, digest, mix_command)
        if status and result is None:
            return status if status > 0 else 1
        if status or result is None:
            raise OSError
        retain_until, valid_until, payload, deadline = result
        status = publish(path, payload, deadline, valid_until)
    except ReadExpired:
        print("not_found", file=sys.stderr)
        return 1
    except AuthorizationInterrupted:
        print("authorization_interrupted", file=sys.stderr)
        return 130
    except AuthorizationIndeterminate as error:
        print(f"authorization_indeterminate mix_pid={error.pid} mix_pgid={error.pid} "
              f"mix_reaped={str(error.reaped).lower()}", file=sys.stderr, flush=True)
        return 2
    except (OSError, subprocess.TimeoutExpired):
        status = 1

    if status == 0:
        print(f"retain_until={retain_until}")
    elif status == 1:
        print("output_unavailable", file=sys.stderr)
    return status


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 4 and args[0] == "--publish-worker":
        # The token and connection configuration are absent from this child.
        try:
            status = worker(args[1], float(args[2]), int(args[3]) or None)
        except IndeterminateOutput:
            status = 2
        except Exception:
            status = 1
    else:
        status = main(args)
    sys.exit(status)
