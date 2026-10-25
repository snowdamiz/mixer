

def cleanup():
    for path in (HERE / "commands").glob("*/receipt.json"):
        receipt = read(path)
        assert receipt["processGroupEmpty"], "unknown or live owned group: " + str(path)
        assert observe_group(receipt["processGroup"])["state"] == "absent", "owned PGID not proven absent"
    assert SCRATCH.exists() and not SCRATCH.is_symlink()
    info = SCRATCH.stat()
    holders = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(SCRATCH)], capture_output=True, timeout=30)
    (HERE / "scratch-holders.stdout").write_bytes(holders.stdout)
    (HERE / "scratch-holders.stderr").write_bytes(holders.stderr)
    result = {"path": str(SCRATCH), "holderExitCode": holders.returncode, "removed": False}
    assert holders.returncode == 1 and not holders.stdout and not holders.stderr, "owned scratch still has holders"
    assert (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino) == (info.st_dev, info.st_ino)
    if BINARY.exists():
        binary = identity(BINARY)
        with BINARY.open("rb") as source, gzip.GzipFile(filename=str(BINARY) + ".gz", mode="wb", mtime=0) as dest:
            shutil.copyfileobj(source, dest)
        result["retainedExecutable"] = {"uncompressed": binary, "gzip": identity(str(BINARY) + ".gz")}
        with gzip.open(str(BINARY) + ".gz", "rb") as stream:
            assert hashlib.sha256(stream.read()).hexdigest() == binary["sha256"]
        own = subprocess.run(["/usr/sbin/lsof", "-nP", str(BINARY)], capture_output=True, timeout=30)
        (HERE / "binary-holders.stdout").write_bytes(own.stdout)
        (HERE / "binary-holders.stderr").write_bytes(own.stderr)
        assert own.returncode == 1 and not own.stdout and not own.stderr
        BINARY.unlink()
    result["logicalBytesRemoved"] = sum(p.stat().st_size for p in SCRATCH.rglob("*") if p.is_file())
    shutil.rmtree(SCRATCH)
    result["removed"] = not SCRATCH.exists()
    save("cleanup.json", result)
    print(json.dumps(result))
