"""Drive a relocated kit's stock controller without touching a simulator."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from delivery import http, read, require


def check(kit, work):
    work.mkdir()
    copied = work / "relocated"
    shutil.copytree(kit, copied, symlinks=True)
    subprocess.run(["shasum", "-a", "256", "-c", "MEMBERS.sha256"], cwd=copied,
                   check=True, stdout=subprocess.DEVNULL)
    controller = work / "controller"
    with (work / "controller.log").open("wb") as log:
        child = subprocess.Popen([sys.executable, "-B", copied / "delivery.py", "serve",
                                   copied / "tools", copied / "releases", controller, copied / "delivery.json"],
                                  stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            lease = controller / "control.json"
            deadline = time.monotonic() + 6
            while not lease.exists():
                require(child.poll() is None and time.monotonic() < deadline, "Controller lease missing")
                time.sleep(0.05)
            lease_value = read(lease)
            port, token = lease_value["port"], lease_value["token"]
            configured = copied / "private.xctestrun"
            subprocess.run([sys.executable, "-B", copied / "configure.py", copied, lease, configured], check=True)
            require(http(port, "/prior", method="POST")[0] == 403, "Unauthorized controller request")
            require(http(port, "/successor", method="POST", token=token)[0] == 409, "Out-of-order controller request")
            origin = None
            for phase in ("prior", "successor", "rollback"):
                status, body = http(port, "/" + phase, method="POST", token=token)
                current = json.loads(body)["port"]
                require(status == 200 and (origin is None or current == origin), "Origin changed during the journey")
                origin = current
            require(http(port, "/offline", method="POST", token=token) == (200, b"{}"), "Offline controller transition")
            require(child.wait(timeout=5) == 0, "Controller did not close")
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
                child.wait(timeout=8)
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise RuntimeError(f"Unresolved controller group {child.pid}")
    receipt = read(controller / "receipt.json")
    require(receipt["status"] == "passed" and not receipt["hold"], "Controller did not observe clean closure")
    return dict(relocated=True, configuredPlan=True, unauthorizedStatus=403, outOfOrderStatus=409,
                phases=receipt["phases"], originCleanup=receipt["originCleanup"], controllerGroupAbsent=True)


if __name__ == "__main__":
    print(json.dumps(check(*map(Path, sys.argv[1:])), indent=2))
