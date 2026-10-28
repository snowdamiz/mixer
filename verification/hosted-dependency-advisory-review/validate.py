#!/usr/bin/env python3
"""Validate collected evidence, not vulnerability reachability or product behavior."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def version(value):
    # Only compare the observed release pins and explicit advisory bounds.
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-pre\.(\d+))?", value)
    assert match, value
    major, minor, patch, pre = match.groups()
    return (int(major), int(minor), int(patch), 1 if pre is None else 0,
            0 if pre is None else int(pre))


def main():
    advisories = json.loads((HERE / "advisories.json").read_text())
    candidates = json.loads((HERE / "upgrade-candidates.json").read_text())
    receipt = json.loads((HERE / "receipt.json").read_text())
    expected = {"bandit": ("1.13.1", "1.14.0"), "jose": ("1.11.12", "1.11.13")}
    checks = []
    assert len(advisories) == 19 and len({a["ghsa_id"] for a in advisories}) == 19
    checks.append("19 unique logged GHSA IDs collected from primary maintainer API")
    assert collections.Counter(a["package"] for a in advisories) == {"bandit": 11, "jose": 8}
    checks.append("11 Bandit and 8 JOSE advisories")
    for a in advisories:
        pin, candidate = expected[a["package"]]
        assert a["pinned_version"] == pin
        assert a["log_cve"] == a["cve_id"]
        assert a["log_severity"].lower() == a["github_severity"]
        assert a["withdrawn_at"] is None
        assert a["metadata_retrieval"]["status"] == 200
        assert len(a["vulnerabilities"]) == 1
        v = a["vulnerabilities"][0]
        assert v["package"]["name"] == a["package"]
        lower, upper = v["vulnerable_version_range"].split(", ")
        assert lower.startswith(">= ") and upper.startswith("< ")
        assert version(lower[3:]) <= version(pin) < version(upper[2:])
        assert candidate == v["patched_versions"] == upper[2:]
    checks.append("all exact pins fall within primary ranges; candidate equals every patched version")
    checks.append("all log CVE aliases and severities agree; no collected advisory withdrawn")
    for c in candidates:
        assert c["version"] == expected[c["package"]][1]
        assert c["retrieval"]["status"] == 200
        assert c["metadata"]["retirement"] is None
    checks.append("both candidate Hex release records are published and not retired")
    protected = ["hosted/mix.exs", "hosted/mix.lock", "THIRD_PARTY.yml",
                 ".github/workflows/hosted.yml", "hosted/lib/mixer_hosted/browser_auth/store.ex"]
    for name in protected:
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        assert actual == receipt["selected_inputs"][name]["sha256"], name
    checks.append("all five protected dependency/product/workflow files retain collected bytes")
    result = {"checked_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
              "command": ["python3", "-B", "verification/hosted-dependency-advisory-review/validate.py"],
              "status": "pass", "checks": checks,
              "scope": "Evidence metadata consistency and protected-source hashes only; no product tests or exploit reproduction."}
    (HERE / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
