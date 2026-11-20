"""Exercise the Starter restore's authenticated readback assertions offline."""

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlencode


spec = importlib.util.spec_from_file_location(
    "starter_restore", Path(__file__).with_name("replay-starter.py")
)
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class StarterReadbackTest(unittest.TestCase):
    def setUp(self):
        self.auth = {"cookie": "owner", "unrelatedCookie": "outsider"}
        self.selection = {"org_id": "tenant-a", "build_id": "starter-build"}
        self.query = urlencode(sorted(self.selection.items()))
        self.files = {
            "unsigned_native_binary": b"app",
            "debug_symbols": b"symbols",
            "resource_inventory": b"inventory",
        }
        self.row = {"artifacts": [
            {"kind": kind, "sha256": hashlib.sha256(contents).hexdigest(),
             "sizeBytes": len(contents)}
            for kind, contents in self.files.items()
        ]}
        self.build = {"build": {
            "buildId": "starter-build", "revision": 2, "state": "native_succeeded",
            "artifacts": [
                dict(item, downloadPath=f"/console-api/v1/build-artifacts/{item['kind']}?{self.query}")
                for item in self.row["artifacts"]
            ],
        }}
        self.reads = []
        self.denial_body = b'{"error":{"code":"not_found"}}'
        self.denial_cache = "no-store"

    def http(self, auth, path):
        self.reads.append((auth["cookie"], path))
        if auth["cookie"] == "outsider":
            return 404, {"cache-control": self.denial_cache}, self.denial_body
        headers = {"cache-control": "no-store"}
        route = path.split("?", 1)[0]
        if route == "/console-api/v1/builds":
            return 200, headers, json.dumps(self.build).encode()
        if route == "/console-api/v1/build-logs":
            return 200, headers, b'''{"buildLogs":{"revision":2,"state":"native_succeeded","attempt":1,
                "events":[{"event":"compiler_finished","exitCode":0},{"event":"build_command_finished","exitCode":0}]}}'''
        kind = route.rsplit("/", 1)[1]
        headers.update({"content-type": "application/octet-stream",
                        "content-disposition": f'attachment; filename="{kind}"'})
        return 200, headers, self.files[kind]

    def readback(self):
        with patch.object(replay.starter, "http", self.http):
            return replay.get_readback(self.auth, self.selection, self.row)

    def test_downloads_the_advertised_paths_and_matches_the_artifacts(self):
        results = self.readback()
        for item in self.build["build"]["artifacts"]:
            kind, advertised = item["kind"], item["downloadPath"]
            self.assertIn(("owner", advertised), self.reads)
            self.assertIn(("outsider", advertised), self.reads)
            self.assertEqual(results[kind]["sha256"], item["sha256"])
            self.assertEqual(results[kind]["sizeBytes"], item["sizeBytes"])

    def test_incomplete_descriptors_stop_before_download(self):
        self.build["build"]["artifacts"].pop()
        with self.assertRaisesRegex(RuntimeError, "incomplete artifact"):
            self.readback()
        self.assertEqual(len(self.reads), 2)

    def test_wrong_descriptor_digest_stops_before_download(self):
        self.build["build"]["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "descriptor differs"):
            self.readback()
        self.assertEqual(len(self.reads), 2)

    def test_extra_blank_query_field_stops_before_download(self):
        self.build["build"]["artifacts"][0]["downloadPath"] += "&extra="
        with self.assertRaisesRegex(RuntimeError, "does not bind"):
            self.readback()
        self.assertEqual(len(self.reads), 2)

    def test_denial_with_build_data_is_not_accepted(self):
        self.denial_body = b'{"error":{"code":"not_found"},"build":{"buildId":"starter-build"}}'
        with self.assertRaises(RuntimeError):
            self.readback()

    def test_cacheable_denial_is_not_accepted(self):
        self.denial_cache = "public, max-age=60"
        with self.assertRaisesRegex(RuntimeError, "can be cached"):
            self.readback()


if __name__ == "__main__":
    unittest.main()
