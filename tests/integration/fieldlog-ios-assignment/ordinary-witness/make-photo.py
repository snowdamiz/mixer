#!/usr/bin/env python3
"""Write one deterministic, synthetic RGB image for the owned Photo Library."""

from pathlib import Path
import struct
import sys
import zlib


def chunk(name, data):
    return (struct.pack(">I", len(data)) + name + data
            + struct.pack(">I", zlib.crc32(name + data)))


width, height = 83, 61
rows = []
for y in range(height):
    row = bytearray([0])
    for x in range(width):
        row.extend((210, 80, 35) if (x // 8 + y // 8) % 2 == 0 else (25, 100, 185))
    rows.append(row)
image = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(b"".join(rows)))
    + chunk(b"IEND", b"")
)
with Path(sys.argv[1]).open("xb") as out:
    out.write(image)
