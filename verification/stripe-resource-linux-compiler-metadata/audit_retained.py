"""Read-only audit of retained metadata and native authentication receipts.

This rechecks byte bindings, not signatures: gpgv ran only in the retained C2
container. No Docker, network, package solver, or native execution occurs here.
"""
import hashlib
import json
import lzma
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
SIGNER = "F6ECB3762474EDA9D21B7022871920D1991BC93C"
SELECTION_SHA = "f6ab6043c6f840f429b11a0296773b909470e5a449c0e7c8e8a5f541fd55c459"
MAX_EXPANDED = 256 * 1024 * 1024


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cleartext(raw):
    # RFC 4880 cleartext framing only; authentication is retained gpgv evidence.
    body = raw.split(b"\n\n", 1)[1].split(b"-----BEGIN PGP SIGNATURE-----", 1)[0]
    return b"".join(line[2:] if line.startswith(b"- ") else line
                    for line in body.splitlines(keepends=True))


def main():
    require(digest(ROOT / "verification/stripe-webhook-resource-ingress-root-review/linux-compiler-metadata-selection.json") == SELECTION_SHA,
            "selected authority bytes changed")
    for phase, archive in (("C1", "run_container-c1-authored.py"),
                           ("C2", "run_container-c2-authored.py")):
        receipt = json.loads((PACKET / phase / "receipt.json").read_text())
        require(digest(PACKET / archive) == receipt["runnerSha256"], "executed runner archive changed")
        require(receipt["status"] == "failed-prerequisite", "failed history changed")
        require(all(receipt["cleanup"].values()), "cleanup incomplete")
        for command in receipt["commands"]:
            for output in command["outputs"].values():
                path = ROOT / output["path"]
                require(path.stat().st_size == output["bytes"] and digest(path) == output["sha256"], "raw command output changed")
    c2 = json.loads((PACKET / "C2/receipt.json").read_text())
    require(digest(PACKET / "verify-c2-authored.sh") == c2["probeSha256"], "executed probe archive changed")
    for name, expected in c2["snapshotFiles"].items():
        require(digest(PACKET / "inputs-C2" / name) == expected, "executed snapshot source changed")
    stdout = (PACKET / "C2/06-probe.stdout").read_text()
    require("MIXER_ALL_METADATA_AUTHENTICATED=1" in stdout, "native authentication marker missing")
    require("MIXER_TAMPERED_SIGNATURE_REJECTED=1" in stdout, "native signature control missing")
    manifest = json.loads((PACKET / "metadata-authenticated-manifest.json").read_text())
    require(not manifest["APTDependencyResolutionExecuted"] and manifest["exactDependencyLock"] is None, "unobserved lock claim")
    acquisition = json.loads((PACKET / "acquisition/receipt.json").read_text())
    require(acquisition["packageRequests"] == 0 and len(acquisition["records"]) == 6, "unexpected acquisition scope")
    for record in acquisition["records"]:
        path = ROOT / record["path"]
        require(path.stat().st_size == record["bytes"] and digest(path) == record["sha256"], "acquisition bytes changed")
    total = 0
    for suite, item in manifest["indexes"].items():
        require(item["signerFingerprint"] == SIGNER, "signer binding changed")
        require(f"MIXER_SIGNER_VERIFIED={suite}:{SIGNER}" in stdout, "native signer receipt missing")
        require(f"MIXER_INDEX_VERIFIED={suite}:{item['indexAlgorithm']}:{item['indexDigest']}:{item['compressedBytes']}" in stdout, "native index receipt missing")
        raw = PACKET / "acquisition" / (suite + ".InRelease")
        require(digest(raw) == item["inReleaseSha256"], "InRelease binding changed")
        release = cleartext(raw.read_bytes())
        require(hashlib.sha256(release).hexdigest() == item["nativeVerifiedCleartextSha256"], "gpgv cleartext binding changed")
        require((ROOT / item["releasePath"]).read_bytes() == release, "retained cleartext changed")
        rows = release.decode().split("SHA256:\n", 1)[1].split("\nSHA", 1)[0].splitlines()
        require(f" {item['expandedDigest']} {item['expandedBytes']:16d} main/binary-arm64/Packages" in rows
                or any(row.split() == [item["expandedDigest"], str(item["expandedBytes"]), "main/binary-arm64/Packages"] for row in rows),
                "signed uncompressed index row missing")
        compressed = PACKET / "acquisition" / (suite + ".Packages.xz")
        require(digest(compressed) == item["compressedSha256"] and compressed.stat().st_size == item["compressedBytes"], "compressed index changed")
        value, size = hashlib.sha256(), 0
        with lzma.open(compressed, "rb") as stream:
            while True:
                block = stream.read(min(65536, MAX_EXPANDED - total + 1))
                if not block:
                    break
                total += len(block)
                size += len(block)
                require(total <= MAX_EXPANDED, "expanded byte bound exceeded")
                value.update(block)
        require(size == item["expandedBytes"] and value.hexdigest() == item["expandedDigest"], "expanded signed size/hash mismatch")
        retained = ROOT / item["expandedPath"]
        require(retained.stat().st_size == size and digest(retained) == value.hexdigest(), "retained index changed")
    require(total == manifest["expandedBytes"], "expanded total changed")
    print(json.dumps({"status": "retained-evidence-bindings-pass", "nativeSignatureReexecution": False,
                      "authenticatedSuites": 3, "expandedBytes": total, "exactDependencyLock": None,
                      "nativeAttempts": 2, "cleanupBothObserved": True}, sort_keys=True))


if __name__ == "__main__":
    main()
