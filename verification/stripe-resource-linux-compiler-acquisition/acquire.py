#!/usr/bin/env python3
"""C4: exclusive bounded HTTPS acquisition of exact signed package bytes.

No package parsing, extraction, installation, script, or compiler execution.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import ssl
import stat
import sys
import time
import urllib.parse
import urllib.request


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTION = ROOT/"verification/stripe-webhook-resource-ingress-root-review/linux-compiler-acquisition-selection.json"
SELECTION_SHA = "9205ee66e314f1f6c572817464de611ed4e3cf1a2a9bd84057963706a7a23308"
METADATA_SEAL = ROOT/"verification/stripe-resource-linux-compiler-metadata-v3/seal.json"
METADATA_SEAL_SHA = "a229a85cb950facf79cc1c3c68760100246269ea1100f8c113459bf3418be80b"
LOCK = ROOT/"verification/stripe-resource-linux-compiler-metadata-v3/package-lock.json"
LOCK_SHA = "4db8b41afffdf796acaec18bcc3b5574be593af0c11c4cb860b39da5d64a36b4"
ORIGIN = "https://ports.ubuntu.com/ubuntu-ports/"
SINGLE_LIMIT = 67108864
TOTAL_LIMIT = 134217728
STORAGE_LIMIT = 805306368
REQUEST_SECONDS = 30
WALL_SECONDS = 180


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")


def checked_url(url, allowed):
    require(url in allowed, "URL outside exact locked allowlist")
    parsed = urllib.parse.urlsplit(url)
    filename = allowed[url]["filename"]
    path = PurePosixPath(filename)
    require(parsed.scheme == "https" and parsed.netloc == "ports.ubuntu.com"
            and not parsed.query and not parsed.fragment and not parsed.username and not parsed.password
            and url == ORIGIN+filename and filename.startswith("pool/main/")
            and str(path) == filename and not path.is_absolute()
            and all(part not in ("", ".", "..") for part in filename.split("/"))
            and "%" not in filename and "\\" not in filename, "unsafe locked origin or path")


def checked_lock(lock):
    packages = lock["packages"]
    require(lock["status"] == "native-offline-APT-selected-signed-artifacts-locked-not-acquired"
            and len(packages) == 36 and lock["packageCount"] == 36
            and sum(item["bytes"] for item in packages) == 50997408,
            "exact selected package set mismatch")
    require(len(packages) <= 48 and sum(item["bytes"] for item in packages) <= TOTAL_LIMIT,
            "locked aggregate bounds")
    allowed = {item["url"]: item for item in packages}
    require(len(allowed) == len(packages), "duplicate locked URL")
    require(len({Path(item["filename"]).name for item in packages}) == len(packages), "duplicate output filename")
    for item in packages:
        checked_url(item["url"], allowed)
        require(0 < item["bytes"] <= SINGLE_LIMIT and item["architecture"] in ("arm64", "all"), "locked package bounds or architecture")
        require(len(item["sha256"]) == 64 and all(c in "0123456789abcdef" for c in item["sha256"]), "locked SHA256 missing")
        require(item["signedProvenance"] and all(source["signerFingerprint"] == "F6ECB3762474EDA9D21B7022871920D1991BC93C"
                for source in item["signedProvenance"]), "signed package provenance missing")
    return allowed


def remaining_time(deadline, now=time.monotonic):
    remaining = deadline-now()
    if remaining <= 0:
        raise TimeoutError("selected cumulative wall deadline")
    return min(REQUEST_SECONDS, remaining)


def request_time(deadline, started, now=time.monotonic):
    remaining_time(deadline, now)
    if now()-started >= REQUEST_SECONDS:
        raise TimeoutError("selected per-request deadline")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("all redirects refused; no retry")


def new_private_directory(path):
    path.mkdir(mode=0o700, exist_ok=False)
    require(stat.S_ISDIR(path.lstat().st_mode) and stat.S_IMODE(path.lstat().st_mode) == 0o700,
            "new private directory mode mismatch")


def exclusive_partial(path):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    info = os.fstat(descriptor)
    if not (stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
            and stat.S_IMODE(info.st_mode) == 0o600):
        os.close(descriptor)
        raise ValueError("exclusive partial is not an owned regular file")
    return descriptor, (info.st_dev, info.st_ino)


def remove_owned_partial(path, identity):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return True
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
            and (info.st_dev, info.st_ino) == identity and info.st_nlink == 1,
            "partial cleanup identity mismatch; no unrelated mutation")
    path.unlink()
    return not path.exists()


def transfer(package, opener, output, allowed, budget, record, now=time.monotonic):
    """One attempt; injected opener/clock allow finite offline failure controls."""
    url = package["url"]
    checked_url(url, allowed)
    require(0 < package["bytes"] <= SINGLE_LIMIT, "selected single package bound")
    require(budget["observedBytes"]+package["bytes"] <= TOTAL_LIMIT, "selected aggregate package bound")
    require(budget["retainedBytes"]+package["bytes"] <= STORAGE_LIMIT, "selected owned storage bound")
    remaining = remaining_time(budget["deadline"], now)
    partial = output/(Path(package["filename"]).name+".partial")
    destination = output/Path(package["filename"]).name
    descriptor, identity = exclusive_partial(partial)
    value, accepted = hashlib.sha256(), 0
    record.update({"url": url, "expectedBytes": package["bytes"], "expectedSha256": package["sha256"],
                   "observedBytes": 0, "writtenBytes": 0, "status": "failed", "partialCleanup": False,
                   "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    started = now()
    try:
        request = urllib.request.Request(url, headers={"Accept-Encoding": "identity", "User-Agent": "Mixer-selected-package-acquisition/1"})
        record["requestStarted"] = True
        with os.fdopen(descriptor, "wb") as stream, opener.open(request, timeout=remaining) as response:
            descriptor = None
            request_time(budget["deadline"], started, now)
            require(response.status == 200 and response.geturl() == url, "unexpected package response status or origin")
            require(response.headers.get("Content-Encoding", "identity") == "identity", "unselected content encoding")
            record["httpStatus"] = response.status
            record["responseUrl"] = response.geturl()
            record["contentLength"] = response.headers.get("Content-Length")
            if record["contentLength"] is not None:
                require(record["contentLength"].isdigit() and int(record["contentLength"]) == package["bytes"], "Content-Length differs from signed package size")
            while True:
                request_time(budget["deadline"], started, now)
                allowance = min(65536, package["bytes"]-accepted+1, TOTAL_LIMIT-budget["observedBytes"])
                require(allowance > 0, "selected transfer byte bound reached")
                block = response.read(allowance)
                request_time(budget["deadline"], started, now)
                if not block:
                    break
                budget["observedBytes"] += len(block)
                record["observedBytes"] += len(block)
                require(budget["observedBytes"] <= TOTAL_LIMIT and accepted+len(block) <= package["bytes"], "response exceeds signed or aggregate byte bound")
                stream.write(block)
                value.update(block)
                accepted += len(block)
                record["writtenBytes"] = accepted
            stream.flush()
            os.fsync(stream.fileno())
        record["actualSha256"] = value.hexdigest()
        require(accepted == package["bytes"] and value.hexdigest() == package["sha256"], "signed package size or SHA256 mismatch")
        # link is an exclusive publication: an existing path is never replaced.
        os.link(partial, destination, follow_symlinks=False)
        partial.unlink()
        record["partialCleanup"] = True
        final = destination.lstat()
        require(stat.S_ISREG(final.st_mode) and final.st_nlink == 1 and stat.S_IMODE(final.st_mode) == 0o600,
                "final payload file invariant")
        budget["retainedBytes"] += accepted
        record.update({"status": "signed-size-and-SHA256-verified", "bytes": accepted,
                       "sha256": value.hexdigest(), "filename": destination.name})
        return destination
    except BaseException as error:
        record["error"] = {"type": type(error).__name__, "reason": str(error)}
        raise
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if partial.exists() or partial.is_symlink():
            record["partialCleanup"] = remove_owned_partial(partial, identity)
        else:
            record["partialCleanup"] = True
        record["elapsedSeconds"] = now()-started


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"executeRequired": True, "packagesSelected": 36, "extractionSelected": False}))
        return
    require(sha(SELECTION) == SELECTION_SHA and sha(METADATA_SEAL) == METADATA_SEAL_SHA and sha(LOCK) == LOCK_SHA,
            "selection, metadata seal or lock mismatch")
    selection = json.loads(SELECTION.read_text())
    require(selection["phase"] == "C4" and selection["exactPackageCount"] == 36
            and selection["exactTransferBytes"] == 50997408 and selection["packageAcquisitionSelected"] is True
            and selection["packageInstallationSelected"] is False and selection["compilerExecutionSelected"] is False
            and selection["resourceRuntimeSelected"] is False, "selected scope mismatch")
    for name, expected in json.loads(METADATA_SEAL.read_text())["files"].items():
        require(sha(ROOT/name) == expected, "preserved metadata packet changed")
    lock = json.loads(LOCK.read_text())
    allowed = checked_lock(lock)
    attempt = HERE/"attempt"
    new_private_directory(attempt)
    output = attempt/"packages"
    new_private_directory(output)
    context = ssl.create_default_context()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))
    started = time.monotonic()
    budget = {"observedBytes": 0, "retainedBytes": 0, "deadline": started+WALL_SECONDS}
    records, error_record = [], None
    receipt = {"schema": 1, "status": "failed-prerequisite", "selectionSha256": SELECTION_SHA,
        "metadataSealSha256": METADATA_SEAL_SHA, "packageLockSha256": LOCK_SHA,
        "sourceSha256": sha(Path(__file__)), "argv": sys.argv, "cwd": str(ROOT),
        "hostPython": {"version": sys.version, "executable": str(Path(sys.executable).resolve()), "sha256": sha(Path(sys.executable).resolve())},
        "TLS": {"library": ssl.OPENSSL_VERSION, "certificateVerification": "default-verified", "hostnameVerification": context.check_hostname},
        "credentialsOrProxyInherited": False, "requestRetries": 0, "redirectsFollowed": 0,
        "simultaneousRequests": 1, "records": records,
        "extractionExecuted": False, "installationExecuted": False, "maintainerScriptsExecuted": False,
        "compilerExecuted": False, "helperExecuted": False, "nifLoaded": False,
        "rootfsOrReleaseConstructed": False, "resourceRuntimeRowsExecuted": 0,
        "LinuxArtifactAccepted": False, "LinuxResourceRuntimeAccepted": False, "gaAccepted": False, "gitOperations": 0}
    def expired(_sig, _frame):
        raise TimeoutError("selected request or cumulative acquisition deadline")
    def interrupted(_sig, _frame):
        raise InterruptedError("selected acquisition interrupted; partial cleanup required")
    prior = {sig: signal.getsignal(sig) for sig in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM)}
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        for package in lock["packages"]:
            record = {"name": package["name"], "version": package["version"], "architecture": package["architecture"]}
            records.append(record)
            signal.setitimer(signal.ITIMER_REAL, remaining_time(budget["deadline"]))
            transfer(package, opener, output, allowed, budget, record)
            signal.setitimer(signal.ITIMER_REAL, 0)
            save(attempt/"receipt.json", receipt)
        require(budget["retainedBytes"] == 50997408 and len(records) == 36, "acquisition completeness mismatch")
        receipt["status"] = "all-36-locked-package-archives-verified-not-extracted"
    except BaseException as error:
        error_record = {"type": type(error).__name__, "reason": str(error)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in prior.items():
            signal.signal(sig, handler)
        receipt.update({"observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "elapsedSeconds": time.monotonic()-started, "observedTransferBytes": budget["observedBytes"],
            "verifiedRetainedPackageBytes": budget["retainedBytes"], "error": error_record,
            "packageRequests": sum(record.get("requestStarted", False) for record in records),
            "cleanup": {"allKnownPartialsRemoved": all(record.get("partialCleanup", True) for record in records),
                        "partialFilesRemaining": [path.name for path in output.iterdir() if path.name.endswith(".partial")]},
            "preservedMetadataSealUnchanged": sha(METADATA_SEAL) == METADATA_SEAL_SHA,
            "preservedPackageLockUnchanged": sha(LOCK) == LOCK_SHA})
        save(attempt/"receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "requests": receipt["packageRequests"],
                      "verifiedBytes": budget["retainedBytes"], "error": error_record, "cleanup": receipt["cleanup"]}))


if __name__ == "__main__":
    main()
