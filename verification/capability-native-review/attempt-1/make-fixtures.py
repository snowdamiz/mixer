#!/usr/bin/env python3
"""Independently authored tiny Wasm inputs for a public C-boundary client."""
from pathlib import Path
import sys


def u(n):
    out = bytearray()
    while True:
        rest = n >> 7
        out.append((n & 127) | (128 if rest else 0))
        n = rest
        if not n: return bytes(out)


def text(s):
    data = s.encode(); return u(len(data)) + data


def section(tag, body): return bytes([tag]) + u(len(body)) + body

def sig(params, results): return b'\x60' + u(len(params)) + bytes(params) + u(len(results)) + bytes(results)

def body(code):
    data = b'\x00' + bytes(code)
    return u(len(data)) + data


def capability():
    i32, i64 = 0x7f, 0x7e
    types = [sig([], []), sig([i32] * 3, [i32]), sig([i64, i32, i32, i32], [i32]), sig([i64], [i32])]
    m = b'\0asm\x01\0\0\0' + section(1, u(len(types)) + b''.join(types))
    imports = [('storage_get', 1), ('poll', 2), ('cancel', 3)]
    m += section(2, u(3) + b''.join(text('mixer.capability.v1') + text(name) + b'\0' + u(ty) for name, ty in imports))
    # Defined startup/wake; forwarding enqueue/poll/cancel; trap; bounded-by-host spin.
    m += section(3, u(7) + bytes([0, 0, 1, 2, 3, 0, 0]))
    m += section(5, b'\x01\x01\x01\x10')  # one defined memory, min1 max16
    exports = [('startup', 3), ('mixer_guest_capability_ready_v1', 4), ('enqueue', 5), ('poll', 6), ('cancel', 7), ('trap', 8), ('spin', 9)]
    m += section(7, u(len(exports)) + b''.join(text(name) + b'\0' + u(index) for name, index in exports))
    codes = [b'\x0b', b'\x0b', b'\x20\0\x20\x01\x20\x02\x10\0\x0b',
             b'\x20\0\x20\x01\x20\x02\x20\x03\x10\x01\x0b', b'\x20\0\x10\x02\x0b',
             b'\x00\x0b', b'\x03\x40\x0c\x00\x0b\x0b']
    return m + section(10, u(len(codes)) + b''.join(body(code) for code in codes))


def legacy():
    m = b'\0asm\x01\0\0\0' + section(1, b'\x01' + sig([], []))
    m += section(3, b'\x01\x00') + section(5, b'\x01\x00\x01')
    m += section(7, b'\x01' + text('run') + b'\x00\x00')
    return m + section(10, b'\x01' + body(b'\x0b'))


if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    (out / 'capability.wasm').write_bytes(capability())
    (out / 'legacy.wasm').write_bytes(legacy())
