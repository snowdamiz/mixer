"""Exercise the Pair25 bridge on real loopback sockets without a browser."""
from contextlib import closing
from hashlib import sha256
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event, Thread
import unittest
from urllib.parse import urlencode, urlsplit

import browser
from run import ATTACHMENTS


class BrowserBridgeTest(unittest.TestCase):
    def test_streams_only_the_bound_profile_attachments(self):
        payload = bytes(range(256)) * 1600
        first_block = 64 * 1024
        downstream_received = Event()
        upstream_completed = Event()
        backend_targets = []
        expected = {
            "organization_id": "owner", "project_id": "project", "application_id": "example.source.app",
            "platform": "android", "source_sha256": "a" * 64, "toolchain_lock_sha256": "b" * 64,
            "build_definition_sha256": "c" * 64,
        }
        evidence = browser.BrowserEvidence(expected | {"source_input_id": "starter"}, {})
        evidence.queued = expected | {"build_id": "build-" + "d" * 64}
        query = "?" + urlencode(evidence.queued)
        kinds = list(ATTACHMENTS)
        paths = [f"{browser.ARTIFACTS}/{kind}" for kind in kinds]
        downloads = [
            {"kind": kind, "sizeBytes": len(payload), "sha256": sha256(payload).hexdigest(),
             "contentType": media, "contentDisposition": f'attachment; filename="{filename}"'}
            for kind, (media, filename) in ATTACHMENTS.items()
        ]
        general = "/console-api/v1/unrelated"

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                backend_targets.append(self.path)
                if self.path == general:
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                cookie = self.headers.get("Cookie")
                if cookie != "__Host-mixer-session=fresh-owner":
                    self.send_response(404 if cookie else 401)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                item = downloads[paths.index(urlsplit(self.path).path)]
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Content-Type", item["contentType"])
                self.send_header("Content-Disposition", item["contentDisposition"])
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Request-ID", "synthetic-loopback")
                self.send_header("ETag", '"' + item["sha256"] + '"')
                self.end_headers()
                self.wfile.write(payload[:first_block])
                if downstream_received.wait(3):
                    self.wfile.write(payload[first_block:])
                    upstream_completed.set()

        with HTTPServer((browser.HOST, 0), Handler) as upstream:
            thread = Thread(target=upstream.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
            thread.start()
            try:
                auth = {"port": upstream.server_port, "cookie": "queue-owner"}
                with browser.bridge(Path(__file__).resolve().parent, auth, evidence, True) as (port, _, terminal_url):
                    def request(path, status, cookie=None, *, read_first=False):
                        headers = {"Host": f"localhost:{port}"}
                        if cookie:
                            headers["Cookie"] = cookie
                        with closing(HTTPConnection(browser.HOST, port, timeout=4)) as client:
                            client.request("GET", path, headers=headers)
                            with client.getresponse() as response:
                                self.assertEqual(response.status, status)
                                prefix = b""
                                if read_first:
                                    prefix = response.read(first_block)
                                    self.assertEqual(prefix, payload[:first_block])
                                    self.assertFalse(upstream_completed.is_set())
                                    downstream_received.set()
                                return response.headers, prefix + response.read()

                    target = paths[0] + query
                    handoff = urlsplit(terminal_url)
                    session_path = f"{handoff.path}?{handoff.query}"
                    request(session_path, 404)
                    request(target, 404)
                    evidence.begin_terminal("fresh-owner", {
                        "buildId": evidence.queued["build_id"], "revision": 2,
                        "state": "native_succeeded", "platform": "android", "attempt": 1,
                    }, {"events": []}, downloads)
                    headers, _ = request(session_path, 303)
                    cookie = headers["Set-Cookie"].split(";", 1)[0]
                    self.assertEqual(cookie, "__Host-mixer-session=fresh-owner")
                    request(session_path, 410)
                    request(paths[0] + query.replace("d" * 64, "e" * 64), 404, cookie)
                    request(target + "&extra=", 404, cookie)
                    request(browser.ARTIFACTS + "/other" + query, 404, cookie)
                    request(target.replace("build-artifacts", "build-%61rtifacts"), 404, cookie)
                    self.assertEqual(backend_targets, [])

                    request(target, 401)
                    request(target, 404, "__Host-mixer-session=outsider")
                    for path, item in zip(paths, downloads, strict=True):
                        headers, data = request(path + query, 200, cookie, read_first=path == paths[0])
                        self.assertEqual(len(data), item["sizeBytes"])
                        self.assertEqual(sha256(data).hexdigest(), item["sha256"])
                        self.assertEqual(headers["Content-Type"], item["contentType"])
                        self.assertEqual(headers["Content-Disposition"], item["contentDisposition"])
                        self.assertEqual(headers["Content-Length"], str(item["sizeBytes"]))
                        self.assertEqual(headers["Cache-Control"], "no-store")
                        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                        self.assertEqual(headers["X-Request-ID"], "synthetic-loopback")
                        self.assertEqual(headers["ETag"], '"' + item["sha256"] + '"')
                    self.assertTrue(upstream_completed.is_set())
                    request(general, 502, cookie)
                self.assertEqual(backend_targets, [target, target, *(path + query for path in paths), general])
                self.assertEqual(list(evidence.receipt["terminal"]["downloads"]), kinds)
                with closing(HTTPConnection(browser.HOST, port, timeout=1)) as client:
                    with self.assertRaises(ConnectionRefusedError):
                        client.connect()
            finally:
                downstream_received.set()
                upstream.shutdown()
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
