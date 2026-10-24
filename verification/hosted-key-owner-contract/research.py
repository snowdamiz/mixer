#!/usr/bin/env python3
"""Capture authoritative package metadata and the exact installed API excerpts."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

base = Path(__file__).resolve().parent
sources = [
    ("mint-package.json", "https://hex.pm/api/packages/mint"),
    ("mint-release.json", "https://hex.pm/api/packages/mint/releases/1.11.0"),
    ("mint-advisories.json", "https://api.github.com/repos/elixir-mint/mint/security-advisories?per_page=100"),
    ("mint-releases.json", "https://api.github.com/repos/elixir-mint/mint/releases?per_page=5"),
]
observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
fetched = []
for filename, url in sources:
    request = urllib.request.Request(url, headers={"User-Agent": "Mixer-contract-review", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read(2_000_001)
        assert len(data) <= 2_000_000
        (base / filename).write_bytes(data)
        fetched.append({"url": url, "output": filename, "httpStatus": response.status,
                        "sha256": hashlib.sha256(data).hexdigest()})
root = Path(subprocess.check_output(["erl", "-noshell", "-eval", 'io:format("~s",[code:root_dir()]),halt().'], text=True))
excerpts = {
    "lib/inets-9.8/src/http_client/httpc.erl": [(272, 310), (334, 347), (431, 451), (1968, 1972)],
    "lib/inets-9.8/src/http_client/httpc_handler.erl": [(979, 1034), (1486, 1513)],
    "lib/inets-9.8/src/http_client/httpc_response.erl": [(68, 85)],
    "lib/ssl-11.7.7/src/ssl.erl": [(2305, 2321)],
    "lib/kernel-11.0.4/src/inet_res.erl": [(302, 386)],
}
installed = []
for relative, intervals in excerpts.items():
    path = root / relative
    data = path.read_bytes()
    lines = data.decode().splitlines()
    installed.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                      "excerpts": [{"start": start, "end": end, "text": "\n".join(lines[start-1:end])} for start, end in intervals]})
receipt = {"schema": 1, "observedUTC": observed, "command": ["python3", str(base / "research.py")],
           "networkSourceScope": "Public primary metadata only; no provider credentials/resources or product dependency changes.",
           "fetched": fetched, "installedSources": installed,
           "mintTarball": {"url": "https://repo.hex.pm/tarballs/mint-1.11.0.tar", "sha256": hashlib.sha256((base / "mint-1.11.0.tar").read_bytes()).hexdigest()},
           "onlineDocsPatchDrift": "Online OTP docs observed 29.1.2/inets9.8.1/ssl11.7.8; installed source and TLS probe use29.1.1/inets9.8/ssl11.7.7.",
           "webPrimaryReferences": ["https://www.erlang.org/doc/apps/inets/httpc.html#request/5", "https://www.erlang.org/doc/apps/ssl/ssl.html#connect/4", "https://www.erlang.org/doc/apps/kernel/inet_res.html#resolve/5", "https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3", "https://github.com/elixir-mint/mint/tree/v1.11.0", "https://github.com/elixir-mint/mint/security/advisories"]}
(base / "research.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"metadataSources": len(fetched), "installedSources": len(installed), "mintVersion": json.loads((base / "mint-release.json").read_text())["version"], "advisoryRecords": len(json.loads((base / "mint-advisories.json").read_text()))}))
