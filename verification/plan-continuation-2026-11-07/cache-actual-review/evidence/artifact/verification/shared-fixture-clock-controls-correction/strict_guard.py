"""Supplement the unchanged adoption guard before any local subject import."""
import os
import signal
import socket
import subprocess
import time
from offline_guard import DENIED, install as original_install


def install(root):
    original_install(root)

    def blocked(*args, **kwargs):
        DENIED.append('supplemental process/session/group/signal/wait/socket entry')
        raise RuntimeError('Local clock controls prohibit this operation')

    for name in ['abort', '_exit', 'execl', 'execle', 'execlp', 'execlpe', 'execv',
                 'execve', 'execvp', 'execvpe', 'spawnl', 'spawnle', 'spawnlp',
                 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe',
                 'pidfd_open', 'openpty']:
        if hasattr(os, name):
            setattr(os, name, blocked)
    for name in ['pidfd_send_signal', 'sigwaitinfo', 'sigtimedwait']:
        if hasattr(signal, name):
            setattr(signal, name, blocked)
    for name in ['socketpair', 'fromfd', 'fromshare', 'create_server', 'getaddrinfo',
                 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr']:
        if hasattr(socket, name):
            setattr(socket, name, blocked)
    for name in ['getstatusoutput', 'getoutput']:
        if hasattr(subprocess, name):
            setattr(subprocess, name, blocked)
    for name in ['clock_settime', 'clock_settime_ns']:
        if hasattr(time, name):
            setattr(time, name, blocked)
