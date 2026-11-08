"""Owned fake-child test workspace; original runner and packs remain read-only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V2 = ROOT / 'verification/cache-fixture-shared-input-candidate-v2'
OLD = ROOT / 'verification/shared-fixture-clock-controls-correction'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def original_source():
    path = OLD / 'control_source.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != '37633792ac6383dcf43f12dd833a097d38921dc9b80e1b57bec41f0c34311d70':
        raise RuntimeError('Historical control adapter differs')
    return load('historical_control_source', path).control_source()


def workspace(label, source):
    if not label or not all(c.isalnum() or c in '-_' for c in label):
        raise RuntimeError('Simple control label required')
    evidence = HERE / 'evidence'
    evidence.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix=label + '-', dir=evidence))
    scratch = destination / 'scratch'
    scratch.mkdir()
    tempfile.tempdir = str(scratch)
    sys.path.insert(0, str(V2))
    module = types.ModuleType('deadline_controls_' + label.replace('-', '_'))
    module.__file__ = str(V2 / 'test_runner.py')
    sys.modules[module.__name__] = module
    exec(compile(source, str(HERE / 'runner-controls.py'), 'exec'), module.__dict__)
    # Only evidence/cwd routing changes. Runner's __file__ and source hashes remain frozen.
    module.HERE = destination
    for name in ['check_cache_state.py', 'materialize_pack.py']:
        shutil.copyfile(V2 / name, destination / name)
    overlay = module.r.overlay
    old_here, old_materialized = overlay.HERE, overlay.MATERIALIZED
    try:
        overlay.HERE = destination
        overlay.MATERIALIZED = destination / 'materialized'
        overlay.materialize()
        module.r.PACK = overlay.MATERIALIZED / 'pack'
    finally:
        overlay.HERE, overlay.MATERIALIZED = old_here, old_materialized
    return module, destination


def write_guard():
    sys.dont_write_bytecode = True
    def audit(event, args):
        paths = []
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                paths = [args[0]]
        elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
            # shutil's fd-relative removal was already bound to an owned directory.
            if len(args) > 1 and isinstance(args[-1], int) and args[-1] != -1:
                return
            paths = [args[0]]
        elif event in {'os.rename', 'os.link', 'os.symlink'}:
            paths = args[:2]
        for value in paths:
            if not Path(os.fsdecode(value)).resolve().is_relative_to(HERE):
                raise RuntimeError('Write outside owned correction: ' + str(value))
        if event.startswith('socket.'):
            raise RuntimeError('Network forbidden')
    sys.addaudithook(audit)
