#!/usr/bin/env python3
"""Check saved console evidence and current sources; does not execute a browser."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = read(PACKET / "manifest.json")
for group in ("sources", "evidence", "buildArtifacts"):
    for path, expected in manifest[group].items():
        assert digest(ROOT / path) == expected, (group, path)
review = read(ROOT / "verification/console-release-view-independent-review/source-and-artifact-manifest.json")
for path, expected in review["sourceFiles"].items():
    assert digest(ROOT / path) == expected, ("independent source", path)
for path, expected in review["artifacts"].items():
    assert digest(ROOT / "console/dist" / path) == expected, ("independent build", path)
commands = read(PACKET / "final-validation-commands.json")["commands"]
assert all(row["exitCode"] == 0 for row in commands)
assert "# pass 17" in (PACKET / "final-tests.stdout").read_text()
assert "# fail 0" in (PACKET / "final-tests.stdout").read_text()
assert "# pass 6" in (ROOT / "verification/console-release-view-independent-review/tests.stdout").read_text()
states = read(PACKET / "browser-state-transitions.json")
assert len(states) == 6
production = read(PACKET / "browser-production.json")
assert "Page not found" in production["preview"]
assert "Release data unavailable" in production["releases"]
mobile = read(PACKET / "browser-mobile-layout.json")
assert mobile["width"] == mobile["scrollWidth"] == 375
assert len(mobile["tables"]) == 2 and mobile["logoLoaded"] == 128
assert read(PACKET / "browser-skip-link-repair.json")["focusedId"] == "main-content"
context = read(PACKET / "browser-context.json")
assert context["errors"] == []
assert context["nativeSelectArrowKeyChangeVerified"] is False
print(json.dumps({"outcome": "passed", "scope": "saved evidence and current source/output bindings only",
                  "sources": len(manifest["sources"]), "evidenceFiles": len(manifest["evidence"]),
                  "buildArtifacts": len(manifest["buildArtifacts"]), "independentSourceFiles": len(review["sourceFiles"]),
                  "runtimeBrowserStatesRecorded": len(states), "nativeSelectArrowKeys": "unverified"}, indent=2))
