#!/usr/bin/env python3
"""Independent fixed ASCII configuration vector; no product imports or execution."""
import hashlib
import json


PAIRS = [
    ["mode", "configured"],
    ["public_origin", "https://console.example.invalid"],
    ["profile_id", "human-main"],
    ["profile_version", 7],
    ["issuer", "https://identity.example.invalid/tenant"],
    ["client_id", "mixer-console"],
    ["api_audience", "mixer-api"],
    ["authorization_endpoint", "https://identity.example.invalid/authorize"],
    ["token_endpoint", "https://identity.example.invalid/token"],
    ["id_token_jwks_endpoint", "https://identity.example.invalid/oidc/keys"],
    ["redirect_uri", "https://console.example.invalid/auth/callback"],
    ["client_auth_method", "client_secret_basic"],
    ["client_credential_ref", "secret://mixer/oidc/client-v1"],
    ["session_vault_ref", "vault://mixer/browser-session-v1"],
    ["scope", "openid mixer.workspace.read"],
    ["response_mode", "query"],
    ["response_iss_required", True],
    ["transaction_seconds", 300],
    ["session_idle_seconds", 900],
    ["return_path", "/workspace"],
    ["failure_path", "/login"],
]
canonical = b"mixer.browser.configuration.v1\0" + json.dumps(
    [1, PAIRS], ensure_ascii=False, separators=(",", ":")
).encode("utf-8")
digest = hashlib.sha256(canonical).hexdigest()
assert len(canonical) == 910
assert digest == "3116d5ef6ac718b3d2442df3648c60ab3fa1d640f73d429ed2b30490f1e2d7f3"
print(json.dumps({"canonical_bytes": len(canonical), "sha256": digest}, sort_keys=True))
