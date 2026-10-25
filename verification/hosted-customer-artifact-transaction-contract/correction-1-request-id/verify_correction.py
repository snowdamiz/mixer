#!/usr/bin/env python3
"""Verify preserved original hashes and only the declared document correction."""
from pathlib import Path
import difflib
import hashlib
import json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    correction = Path(__file__).resolve().parent
    packet = correction.parent
    root = packet.parents[1]
    prior = correction / "prior"
    original = json.loads((prior / "receipt.json").read_text())
    assert (prior / "receipt.json").read_bytes() == (packet / "receipt.json").read_bytes()
    document = root / "docs/hosted-customer-artifact-transaction-contract.md"
    for artifact in original["artifacts"]:
        live = root / artifact["path"]
        archived = prior / ("document.md" if live == document else live.name)
        assert digest(archived) == artifact["sha256"], artifact["path"]
        if live != document:
            assert digest(live) == artifact["sha256"], artifact["path"]
    old = (prior / "document.md").read_text()
    expected = old
    replacements = json.loads((correction / "changes.json").read_text())["replacements"]
    assert len(replacements) == 5
    for change in replacements:
        assert expected.count(change["old"]) == 1, change["old"]
        expected = expected.replace(change["old"], change["new"], 1)
    actual = document.read_text()
    assert actual == expected, "Live document has undeclared edits"
    assert "server_request_uuid" not in actual and "request UUID" not in actual
    assert "MixerHosted.Authorization.with_authorized_transaction/4,5" in actual
    assert "exactly 32 lowercase hexadecimal characters encoding 16 cryptographically random" in actual
    delta = "".join(difflib.unified_diff(
        old.splitlines(keepends=True), actual.splitlines(keepends=True),
        fromfile="prior/document.md", tofile="docs/hosted-customer-artifact-transaction-contract.md"))
    assert (correction / "document.diff").read_text() == delta
    seal = correction / "receipt.json"
    if seal.exists():
        receipt = json.loads(seal.read_text())
        assert receipt["previous_receipt_sha256"] == digest(prior / "receipt.json")
        assert receipt["old_document_sha256"] == digest(prior / "document.md")
        assert receipt["corrected_document_sha256"] == digest(document)
        for artifact in receipt["artifacts"]:
            assert digest(root / artifact["path"]) == artifact["sha256"], artifact["path"]
    for path in [document, correction / "README.md", correction / "changes.json", Path(__file__)]:
        raw = path.read_bytes()
        assert raw.endswith(b"\n")
        assert all(line == line.rstrip(b" \t") for line in raw.splitlines()), path.name
    print(json.dumps({"status": "correction_packet_valid", "original_sealed_artifacts": 5,
                      "declared_replacements": 5, "product_cases_passed": 0,
                      "product_cases_pending": 35,
                      "corrected_document_sha256": digest(document)}, indent=2))


if __name__ == "__main__":
    main()
