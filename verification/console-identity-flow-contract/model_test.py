"""Executable design specimen; never imported by product or an auth verifier.

Models only one-time login transactions and browser generation fencing. The
`externally_admitted` test input stands in for unimplemented independent token
and authoritative identity checks. It is not authentication evidence.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


def random_value() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class AuthorizationRequest:
    state: str
    nonce: str
    code_challenge: str


@dataclass(frozen=True)
class Claim:
    browser_key: str
    epoch: int
    nonce_digest: str
    expires_at: int
    claim_id: str
    return_path: str


class LoginModel:
    """A single-process atomic model, not a replicated or durable session store."""

    issuer = "https://provider.example.invalid"
    return_routes = {"workspace": "/workspace"}
    login_failure_path = "/login"  # Proposed new product route, not implemented.

    def __init__(self):
        self.lock = threading.Lock()
        self.browsers = {}
        self.transactions = {}
        self.claims = set()

    def preauth(self):
        cookie = random_value()
        with self.lock:
            self.browsers[digest(cookie)] = {"epoch": 0, "expires_at": None}
        return cookie

    def begin(self, cookie, now, return_route="workspace"):
        if return_route not in self.return_routes:
            raise ValueError("invalid_return_route")
        state, nonce, verifier = random_value(), random_value(), random_value()
        key = digest(cookie)
        with self.lock:
            browser = self.browsers.get(key)
            if browser is None:
                raise ValueError("unauthenticated")
            browser["epoch"] += 1
            self.transactions[digest(state)] = {
                "browser": key, "epoch": browser["epoch"], "nonce": digest(nonce),
                "verifier": verifier, "expires_at": now + 300, "issuer": self.issuer,
                "return_path": self.return_routes[return_route],
            }
        return AuthorizationRequest(state, nonce, challenge(verifier))

    def claim(self, state, cookie, issuer, now):
        key = digest(cookie)
        with self.lock:
            transaction = self.transactions.get(digest(state))
            browser = self.browsers.get(key)
            if transaction is None or browser is None or transaction["browser"] != key or \
                    transaction["epoch"] != browser["epoch"] or \
                    transaction["issuer"] != issuer or now >= transaction["expires_at"]:
                raise ValueError("invalid_transaction")
            del self.transactions[digest(state)]
            claim_id = random_value()
            self.claims.add(claim_id)
            return Claim(key, browser["epoch"], transaction["nonce"], transaction["expires_at"], claim_id,
                         transaction["return_path"])

    def complete(self, claim, verified_nonce, now, access_expires_at, *, externally_admitted):
        """Fixture verdict is supplied, never computed or treated as a real verifier."""
        with self.lock:
            if claim.claim_id not in self.claims:
                raise ValueError("invalid_transaction")
            self.claims.remove(claim.claim_id)
            browser = self.browsers.get(claim.browser_key)
            if browser is None or browser["epoch"] != claim.epoch or \
                    not hmac.compare_digest(digest(verified_nonce), claim.nonce_digest) or \
                    now >= claim.expires_at or now >= access_expires_at or \
                    access_expires_at - now > 900 or not externally_admitted:
                raise ValueError("authentication_failed")
            del self.browsers[claim.browser_key]
            authenticated_cookie = random_value()
            self.browsers[digest(authenticated_cookie)] = {
                "epoch": 1, "expires_at": access_expires_at,
            }
            return authenticated_cookie

    def logout(self, cookie):
        with self.lock:
            self.browsers.pop(digest(cookie), None)

    def metadata(self, cookie, now):
        with self.lock:
            browser = self.browsers.get(digest(cookie))
            if browser is None or browser["expires_at"] is None or now >= browser["expires_at"]:
                return {"state": "unauthenticated"}
            return {"state": "authenticated", "expires_at": browser["expires_at"]}


class ContractModelTests(unittest.TestCase):
    def setUp(self):
        self.model = LoginModel()
        self.cookie = self.model.preauth()
        self.request = self.model.begin(self.cookie, 100)

    def claim(self):
        return self.model.claim(self.request.state, self.cookie, self.model.issuer, 110)

    def complete(self, claim, **overrides):
        params = {"verified_nonce": self.request.nonce, "now": 120,
                  "access_expires_at": 500, "externally_admitted": True}
        return self.model.complete(claim, **(params | overrides))

    def test_rfc7636_appendix_b_vector(self):
        self.assertEqual(challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"),
                         "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")

    def test_distinct_256_bit_values_and_no_verifier_in_request(self):
        self.assertEqual(len(self.request.state), 43)
        self.assertEqual(len(self.request.nonce), 43)
        self.assertNotEqual(self.request.state, self.request.nonce)
        self.assertFalse(hasattr(self.request, "verifier"))

    def test_success_rotates_cookie_and_exposes_only_metadata(self):
        authenticated = self.complete(self.claim())
        self.assertNotEqual(authenticated, self.cookie)
        self.assertNotIn(digest(self.cookie), self.model.browsers)
        self.assertEqual(self.model.metadata(authenticated, 121),
                         {"state": "authenticated", "expires_at": 500})

    def test_callback_claim_is_once_under_concurrency(self):
        def attempt(_):
            try:
                return self.claim()
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(attempt, range(32)))
        self.assertEqual(sum(item is not None for item in outcomes), 1)

    def test_cross_browser_reject_does_not_consume_legitimate_transaction(self):
        other = self.model.preauth()
        with self.assertRaises(ValueError):
            self.model.claim(self.request.state, other, self.model.issuer, 110)
        self.claim()

    def test_issuer_mixup_rejects_before_claim(self):
        with self.assertRaises(ValueError):
            self.model.claim(self.request.state, self.cookie, "https://attacker.example.invalid", 110)
        self.claim()

    def test_transaction_expires_at_exact_boundary(self):
        with self.assertRaises(ValueError):
            self.model.claim(self.request.state, self.cookie, self.model.issuer, 400)

    def test_replacement_login_invalidates_old_state(self):
        self.model.begin(self.cookie, 110)
        with self.assertRaises(ValueError):
            self.claim()

    def test_replacement_login_invalidates_claim_after_provider_io(self):
        claim = self.claim()
        self.model.begin(self.cookie, 115)
        with self.assertRaises(ValueError):
            self.complete(claim)

    def test_logout_before_callback_invalidates_state(self):
        self.model.logout(self.cookie)
        with self.assertRaises(ValueError):
            self.claim()

    def test_logout_during_provider_io_prevents_completion(self):
        claim = self.claim()
        self.model.logout(self.cookie)
        with self.assertRaises(ValueError):
            self.complete(claim)

    def test_logout_after_completion_removes_authenticated_session(self):
        authenticated = self.complete(self.claim())
        self.model.logout(authenticated)
        self.assertEqual(self.model.metadata(authenticated, 121), {"state": "unauthenticated"})

    def test_unknown_or_revoked_external_identity_cannot_complete(self):
        with self.assertRaises(ValueError):
            self.complete(self.claim(), externally_admitted=False)

    def test_nonce_mismatch_rejects_and_consumes_claim(self):
        claim = self.claim()
        with self.assertRaises(ValueError):
            self.complete(claim, verified_nonce=random_value())
        with self.assertRaises(ValueError):
            self.complete(claim)

    def test_access_expiry_exact_boundary_rejects(self):
        with self.assertRaises(ValueError):
            self.complete(self.claim(), access_expires_at=120)

    def test_completion_after_transaction_deadline_rejects(self):
        with self.assertRaises(ValueError):
            self.complete(self.claim(), now=400)

    def test_authenticated_metadata_expires_at_exact_boundary(self):
        authenticated = self.complete(self.claim())
        self.assertEqual(self.model.metadata(authenticated, 500), {"state": "unauthenticated"})

    def test_open_return_target_is_rejected(self):
        for route in ("https://attacker.example.invalid", "//attacker.example.invalid", "/v3/orgs", "workspace?x=1",
                      "/console/", "/console/login", "/workspace", "/login"):
            with self.subTest(route=route), self.assertRaises(ValueError):
                self.model.begin(self.cookie, 110, route)

    def test_return_enum_resolves_to_root_mounted_workspace_route(self):
        self.assertEqual(self.claim().return_path, "/workspace")
        self.assertEqual(self.model.login_failure_path, "/login")


if __name__ == "__main__":
    unittest.main(verbosity=2)
