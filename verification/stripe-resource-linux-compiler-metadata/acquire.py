#!/usr/bin/env python3
"""Selected bounded raw metadata acquisition only; authentication follows offline."""
import datetime
import hashlib
import json
from pathlib import Path
import signal
import ssl
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTION = ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-compiler-metadata-selection.json"
SELECTION_SHA = "f6ab6043c6f840f429b11a0296773b909470e5a449c0e7c8e8a5f541fd55c459"
ORIGIN = "https://ports.ubuntu.com/ubuntu-ports/"
SUITES = ("noble", "noble-updates", "noble-security")
ALLOWED = {ORIGIN + "dists/" + suite + suffix for suite in SUITES
    for suffix in ("/InRelease", "/main/binary-arm64/Packages.xz")}


def allowed(url):
    if url not in ALLOWED:
        raise ValueError("URL outside selected metadata allowlist")


def within_bounds(total, item, signed_release):
    if total > 33554432 or item > (1048576 if signed_release else 33554432):
        raise ValueError("selected metadata byte limit")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("unselected redirect refused")


def main():
    if hashlib.sha256(SELECTION.read_bytes()).hexdigest() != SELECTION_SHA:
        raise ValueError("selection mismatch")
    selection = json.loads(SELECTION.read_text())
    if selection["selectedPhases"] != ["C1", "C2", "C3"]:
        raise ValueError("metadata-only phases required")
    out = HERE / "acquisition"
    out.mkdir(mode=0o700, exist_ok=False)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    deadline = time.monotonic() + 120
    total = 0
    records = []
    status = "failed"
    error_record = None
    def expired(_sig, _frame):
        raise TimeoutError("selected request/metadata wall bound")
    prior = signal.signal(signal.SIGALRM, expired)
    try:
        for suite in SUITES:
            for suffix, label in (("/InRelease", "InRelease"), ("/main/binary-arm64/Packages.xz", "Packages.xz")):
                url = ORIGIN + "dists/" + suite + suffix
                allowed(url)
                started = time.monotonic()
                remaining = min(30, deadline - started)
                if remaining <= 0:
                    raise TimeoutError("metadata wall bound")
                signal.setitimer(signal.ITIMER_REAL, remaining)
                path = out / (suite + "." + label)
                record = {"url": url, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "path": str(path.relative_to(ROOT)), "authenticated": False, "bytes": 0}
                records.append(record)
                request = urllib.request.Request(url, headers={"Accept-Encoding": "identity", "User-Agent": "Mixer-selected-metadata/1"})
                with opener.open(request, timeout=remaining) as response, path.open("xb") as stream:
                    if response.status != 200 or response.geturl() != url:
                        raise ValueError("unexpected metadata response")
                    record["httpStatus"] = response.status
                    record["contentLength"] = response.headers.get("Content-Length")
                    item_limit = 1048576 if label == "InRelease" else 33554432
                    if record["contentLength"] is not None:
                        within_bounds(total + int(record["contentLength"]), int(record["contentLength"]), label == "InRelease")
                    while True:
                        remaining_bytes = min(33554432 - total, item_limit - record["bytes"])
                        if remaining_bytes <= 0:
                            if record["contentLength"] is not None and int(record["contentLength"]) == record["bytes"]:
                                break
                            raise ValueError("selected metadata byte limit reached")
                        chunk = response.read(min(65536, remaining_bytes))
                        if not chunk:
                            break
                        total += len(chunk)
                        record["bytes"] += len(chunk)
                        within_bounds(total, record["bytes"], label == "InRelease")
                        stream.write(chunk)
                signal.setitimer(signal.ITIMER_REAL, 0)
                record["elapsedSeconds"] = time.monotonic() - started
                record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                if record["contentLength"] is not None and int(record["contentLength"]) != record["bytes"]:
                    raise ValueError("metadata response size mismatch")
        status = "raw-selected-metadata-acquired-authentication-pending"
    except Exception as error:
        error_record = {"type": type(error).__name__, "reason": str(error)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior)
        receipt = {"schema": 1, "status": status, "selectionSha256": SELECTION_SHA, "records": records,
            "observedBytes": total, "error": error_record, "requestRetries": 0, "redirectsFollowed": 0,
            "credentialsOrProxyInherited": False, "packageRequests": 0, "metadataAuthenticated": False,
            "runtimeResourceAuthorized": False, "gaAccepted": False}
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "observedBytes": total, "requests": len(records), "error": error_record}))


if __name__ == "__main__":
    main()
