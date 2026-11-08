"""Receive one reserved listener, then exec official ADB in the same owned process."""
import array
import hashlib
import os
from pathlib import Path
import socket
import sys


def receive(channel, token):
    channel.sendall(token.encode('ascii'))
    data, ancillary, flags, _ = channel.recvmsg(1, socket.CMSG_SPACE(array.array('i').itemsize))
    descriptors = array.array('i')
    for level, kind, payload in ancillary:
        if level != socket.SOL_SOCKET or kind != socket.SCM_RIGHTS:
            raise RuntimeError('unexpected descriptor message')
        descriptors.frombytes(payload)
    if data != b'F' or flags & socket.MSG_CTRUNC or len(descriptors) != 1:
        raise RuntimeError('exactly one listener required')
    return descriptors[0]


def main():
    channel_path, token, binary, expected_sha, serial, port = sys.argv[1:]
    if hashlib.sha256(Path(binary).read_bytes()).hexdigest() != expected_sha:
        raise RuntimeError('sealed server executable drift')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
        channel.settimeout(5)
        channel.connect(channel_path)
        fd = receive(channel, token)
    listener = socket.socket(fileno=fd)
    if listener.getsockname() != ('127.0.0.1', int(port)):
        raise RuntimeError('listener identity mismatch')
    os.set_inheritable(fd, True)
    os.execv(binary, [binary, '-L', 'acceptfd:' + str(fd), '-s', serial,
                      '--one-device', serial, 'server', 'nodaemon'])


if __name__ == '__main__':
    main()
