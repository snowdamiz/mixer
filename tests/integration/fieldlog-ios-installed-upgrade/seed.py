"""Generate the deterministic four-swatch file selected in the Files picker."""
import struct
import sys
import zlib
from pathlib import Path


def chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data)))


def write_seed(path):
    colors = [(216, 46, 69), (28, 162, 122), (40, 90, 209), (239, 185, 50)]
    rows = [b"\0" + bytes(left) * 960 + bytes(right) * 960
            for left, right in zip(colors[::2], colors[1::2])]
    header = struct.pack(">IIBBBBB", 1920, 1280, 8, 2, 0, 0, 0)
    with Path(path).open("xb") as file:
        file.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
                   chunk(b"sRGB", b"\0") +
                   chunk(b"IDAT", zlib.compress(rows[0] * 640 + rows[1] * 640, 9)) +
                   chunk(b"IEND", b""))


if __name__ == "__main__":
    write_seed(sys.argv[1])
