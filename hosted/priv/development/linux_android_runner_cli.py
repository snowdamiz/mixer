"""Initialize or serve the private, operator-configured Linux Android runner."""

import argparse
import json
import signal
import sqlite3

from compiler_worker import Refusal, digest
from linux_android_docker_adapter import open_docker_runner
from linux_android_runner import unique_object
from native_artifact_worker import read_owned


REQUIRED = {
    "directory", "recipe_sha256", "store_id", "manifest", "docker",
    "daemon_socket", "daemon_id",
}
LAYOUTS = ({"inputs", "outputs"}, {"pair25_root"})
OPTIONAL = {"command_timeout", "completions"}
CONFIG_LIMIT = 256 * 1024


def configuration(path, expected_sha256):
    data = read_owned(path, CONFIG_LIMIT, allow_owner_write=True)
    if digest(data) != expected_sha256:
        raise Refusal("Linux runner configuration digest mismatch")
    config = json.loads(data, object_pairs_hook=unique_object)
    if (type(config) is not dict or config.keys() - REQUIRED - OPTIONAL not in LAYOUTS
            or not REQUIRED <= config.keys()
            or any(type(config[key]) is not str or not config[key] for key in config.keys() - OPTIONAL)
            or ("command_timeout" in config and type(config["command_timeout"]) not in (int, float))
            or ("completions" in config and type(config["completions"]) is not dict)):
        raise Refusal("Invalid Linux runner configuration")
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("initialize", "serve"))
    parser.add_argument("config")
    parser.add_argument("config_sha256")
    args = parser.parse_args()

    stopping = False

    def stop(_signal, _frame):
        nonlocal stopping
        stopping = True

    try:
        config = configuration(args.config, args.config_sha256)
        if args.mode == "initialize":
            with open_docker_runner(**config, initialize=True):
                return
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, stop)
        with open_docker_runner(**config) as server:
            # Let the current request settle and leave any operation in the
            # journals for the next runner process.
            while not stopping:
                server.serve_one()
    except (OSError, ValueError, KeyError, TypeError, OverflowError,
            RecursionError, sqlite3.Error, Refusal) as error:
        raise SystemExit("Linux runner refused startup or service") from error


if __name__ == "__main__":
    main()
