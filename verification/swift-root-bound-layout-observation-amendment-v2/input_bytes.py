"""Bind the exact bounded in-memory bytes before any actual parser call."""
import time
from parser import need
from check import sha

def read_pinned_bytes(path,expected,deadline,*,opener=None):
    need(time.monotonic()<deadline,'saved-memory-read-deadline')
    # A regular reader receives one finite read budget, including one byte to
    # distinguish the exact expected length from an overlong input.
    open_input=path.open if opener is None else opener
    with open_input('rb') as handle:raw=handle.read(expected['bytes']+1)
    need(time.monotonic()<deadline,'saved-memory-read-completion-deadline')
    need(type(raw) is bytes,'saved-memory-not-bytes')
    need(len(raw)==expected['bytes'],'saved-memory-length')
    need(sha(raw)==expected['sha256'],'saved-memory-sha256')
    return raw
