#!/usr/bin/env python3
"""Collect public advisory metadata; never resolve, install, compile or start Mixer."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import ssl
import subprocess
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOG = ROOT / "verification/github-delivery-lifecycle-layout/phoenix-job.log"
COMMANDS = []


def command(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=True)
    COMMANDS.append({"argv": argv, "exit_code": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    return result.stdout.strip()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    request = urllib.request.Request(url, headers={"Accept": "application/json",
                                                  "User-Agent": "mixer-advisory-review"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
        record = {"url": url, "resolved_url": response.url, "status": response.status,
                  "retrieved_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
                  "sha256": sha(data), "size_bytes": len(data),
                  "etag": response.headers.get("ETag"),
                  "last_modified": response.headers.get("Last-Modified")}
    return json.loads(data), record


def main():
    revision = command(["git", "rev-parse", "HEAD"])
    tree = command(["git", "rev-parse", "HEAD^{tree}"])
    git_version = command(["git", "--version"])
    paths = [
        "AGENTS.md", "mixer-product-plan.md", "PLAN.md", "hosted/mix.exs",
        "hosted/mix.lock", "THIRD_PARTY.yml", "hosted/.tool-versions",
        "hosted/config/config.exs", "hosted/lib/mixer_hosted/runtime_config.ex",
        "hosted/lib/mixer_hosted/application.ex", "hosted/lib/mixer_hosted_web/endpoint.ex",
        "hosted/lib/mixer_hosted_web/router.ex",
        "hosted/lib/mixer_hosted/identity/access_token_verifier.ex",
        "hosted/lib/mixer_hosted/identity/trust_snapshot.ex",
        "hosted/lib/mixer_hosted/billing/webhook_transport.ex",
        "hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex",
        "hosted/lib/mixer_hosted_web/plugs/customer_artifact_request.ex",
        "hosted/lib/mixer_hosted_web/plugs/customer_workspace_request.ex",
        "hosted/lib/mixer_hosted/browser_auth/store.ex", ".github/workflows/hosted.yml",
        "hosted/scripts/test-local.py",
        "verification/github-delivery-lifecycle-layout/phoenix-job.log",
    ]
    inputs = {}
    for name in paths:
        data = (ROOT / name).read_bytes()
        inputs[name] = {"sha256": sha(data), "size_bytes": len(data)}
    input_digest = sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode())

    log = LOG.read_text()
    # This parses the saved dependency report, not source syntax or release authority.
    advisories = []
    package = None
    version = None
    severity = None
    cve = None
    for line_number, line in enumerate(log.splitlines(), 1):
        matched = re.search(r"  (\w+) ([\d.]+) VULNERABLE!", line)
        if matched:
            package, version = matched.groups()
        matched = re.search(r"EEF-(CVE-[\d-]+) \((HIGH|MEDIUM|LOW|CRITICAL)\)", line)
        if matched:
            cve, severity = matched.groups()
        matched = re.search(r"aka: .*?(GHSA-[a-z0-9-]+)", line)
        if matched:
            ghsa = matched.group(1)
            repository = {"bandit": "mtrudel/bandit", "jose": "potatosalad/erlang-jose"}[package]
            data, retrieval = fetch(f"https://api.github.com/repos/{repository}/security-advisories/{ghsa}")
            entries = [v for v in data["vulnerabilities"]
                       if v["package"]["name"] == package]
            assert entries, (ghsa, package)
            advisories.append({
                "package": package, "pinned_version": version,
                "log_alias_line": line_number, "log_cve": cve,
                "log_severity": severity, "ghsa_id": ghsa,
                "cve_id": data.get("cve_id"), "summary": data["summary"],
                "github_severity": data["severity"],
                "published_at": data["published_at"], "updated_at": data["updated_at"],
                "withdrawn_at": data.get("withdrawn_at"),
                "vulnerabilities": entries, "identifiers": data["identifiers"],
                "references": sorted(set(re.findall(r"https?://[^\s)>\]]+", data["description"]))),
                "html_url": data["html_url"],
                "source_code_location": data.get("source_code_location"),
                "metadata_retrieval": retrieval,
            })
    assert len(advisories) == 19, len(advisories)
    (HERE / "advisories.json").write_text(json.dumps(advisories, indent=2) + "\n")

    candidates = []
    for package, version in [("bandit", "1.14.0"), ("jose", "1.11.13")]:
        data, retrieval = fetch(f"https://hex.pm/api/packages/{package}/releases/{version}")
        data = {key: data[key] for key in ["meta", "version", "checksum", "url", "has_docs",
                                          "inserted_at", "updated_at", "requirements", "html_url",
                                          "retirement", "security_advisories", "docs_html_url"]}
        candidates.append({"package": package, "version": version,
                           "metadata": data, "retrieval": retrieval})
    (HERE / "upgrade-candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")

    matched_lines = log.splitlines()[405:519]
    (HERE / "ci-advisory-excerpt.log").write_text("\n".join(matched_lines) + "\n")
    receipt = {
        "schema": "mixer.hosted-dependency-advisory-review.v1",
        "collected_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "scope": "Read-only hosted advisory metadata and canonical source review; artifacts only.",
        "source_revision": revision, "source_tree": tree,
        "selected_input_sha256": input_digest, "selected_inputs": inputs,
        "tools": {"python": sys.version, "python_executable": sys.executable,
                  "platform": platform.platform(), "tls": ssl.OPENSSL_VERSION,
                  "git": git_version},
        "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
        "subprocess_commands": COMMANDS,
        "observed_affected_pins": {"bandit": "1.13.1", "jose": "1.11.12"},
        "advisory_count": len(advisories),
        "not_executed": ["Mix", "dependency installation or resolution", "compiler",
                         "hosted runtime/listener", "native runtime", "device",
                         "UI automation", "screen capture", "global process inventory"],
        "qualification": "Version matches and source reachability review only; no exploitation, upgrade, runtime or GA acceptance.",
    }
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"advisory_count": len(advisories), "source_revision": revision,
                      "selected_input_sha256": input_digest,
                      "candidate_versions": [{"package": c["package"], "version": c["version"],
                                              "retirement": c["metadata"].get("retirement")}
                                             for c in candidates]}, indent=2))


if __name__ == "__main__":
    main()
