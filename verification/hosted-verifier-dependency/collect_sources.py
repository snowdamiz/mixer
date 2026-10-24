#!/usr/bin/env python3
"""Capture primary package metadata; no credentials, provider calls, or listeners."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parent
SOURCES = {
    "jose-package": "https://hex.pm/api/packages/jose",
    "jose-release": "https://hex.pm/api/packages/jose/releases/1.11.12",
    "jason-package": "https://hex.pm/api/packages/jason",
    "jason-release": "https://hex.pm/api/packages/jason/releases/1.4.5",
    "joken-package": "https://hex.pm/api/packages/joken",
    "joken-release": "https://hex.pm/api/packages/joken/releases/2.7.0",
    "guardian-package": "https://hex.pm/api/packages/guardian",
    "guardian-release": "https://hex.pm/api/packages/guardian/releases/2.5.0",
    "jose-advisory": "https://api.github.com/advisories/GHSA-9mg4-v392-8j68",
    "jose-upstream": "https://api.github.com/repos/potatosalad/erlang-jose",
    "jose-tags": "https://api.github.com/repos/potatosalad/erlang-jose/git/ref/tags/1.11.12",
    "jose-advisories": "https://hex.pm/packages/jose/advisories",
    "jason-advisories": "https://hex.pm/packages/jason/advisories",
    "joken-advisories": "https://hex.pm/packages/joken/advisories",
    "guardian-advisories": "https://hex.pm/packages/guardian/advisories",
}

manifest = []
for name, url in SOURCES.items():
    request = urllib.request.Request(url, headers={"User-Agent": "Mixer-dependency-qualification/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(2_000_000)
        content_type = response.headers.get("Content-Type", "")
        suffix = ".json" if "json" in content_type else ".html"
        path = BASE / "sources" / (name + suffix)
        path.write_bytes(raw)
        manifest.append({"url": url, "final_url": response.url, "status": response.status,
                         "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         "path": str(path.relative_to(BASE)), "bytes": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest()})
        print(f"{name}: {response.status} {len(raw)} bytes {manifest[-1]['sha256']}")
(BASE / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
