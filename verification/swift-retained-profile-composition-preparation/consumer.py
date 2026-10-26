"""Closed finite child for fixture descriptor-adoption controls only."""
import hashlib
import json
import os
import stat
import sys

seen = set()


def adopt(text, size):
    if not text.isascii() or not text.isdecimal() or len(text) > 10:
        raise ValueError("fd token")
    fd = int(text)
    if fd < 3 or fd in seen:
        raise ValueError("one adoption per fd")
    seen.add(fd)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_size != size:
        raise ValueError("regular exact length")
    return os.fdopen(fd, "rb", buffering=0, closefd=True)


def hashed(file, offset, length, buffer):
    file.seek(offset)
    digest = hashlib.sha256()
    for start in range(0, length, 4096):
        view = memoryview(buffer)[:min(4096, length - start)]
        pos = 0
        for _ in range(32):
            try:
                n = file.readinto(view[pos:])
            except InterruptedError:
                continue
            if type(n) is not int or n <= 0 or n > len(view) - pos:
                raise ValueError("read")
            pos += n
            if pos == len(view):
                break
        if pos != len(view):
            raise ValueError("read attempts")
        digest.update(view)
    for _ in range(32):
        try:
            n = file.readinto(memoryview(buffer)[:1])
        except InterruptedError:
            continue
        if n != 0:
            raise ValueError("EOF")
        return digest.hexdigest()
    raise ValueError("EOF attempts")


def main(argv):
    if len(argv) != 3:
        raise ValueError("closed argv")
    buffer = bytearray(4096)
    with adopt(argv[1], 2560512) as profile, adopt(argv[2], 2560000) as body:
        result = {"profile": hashed(profile, 0, 2560512, buffer), "subrange": hashed(profile, 512, 2560000, buffer), "body": hashed(body, 0, 2560000, buffer), "adoptions": len(seen)}
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main(sys.argv)
