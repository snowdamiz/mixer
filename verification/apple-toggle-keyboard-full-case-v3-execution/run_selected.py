#!/usr/bin/env python3
"""One selected private invocation; first outcome is never retried or replaced."""
import datetime
import hashlib
import importlib.util
import inspect
import json
import os
import pathlib
import stat
import sys
import time
import traceback

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ADAPTER = ROOT / 'verification/apple-toggle-keyboard-full-case-v3-adapter'
PREP = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3'
SELECTION = ROOT / 'verification/apple-toggle-keyboard-full-case-root-review/v3-adapter/execution-selection.json'
SEAL = '137b6dc9b681eff1358712c34d9b71a3b356072ee6954b4a99e9a8c32b60f46b'
SELECTION_HASH = '07fd2d6cde05214ee9a5d89359326081e174ae60f4989117997d027356f5ce49'
REVISION = '50f70a798fea43e1e77b1d95faa1bbda3fc029e0'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010EnabledFromOff', 'test020EnabledFromOn',
           'test030StaleFromOff', 'test040StaleFromOn', 'test050DisabledFromOff', 'test060DisabledFromOn']


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def publish(name, value):
    with (BASE / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def file_record(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return dict(kind='symlink', target=os.readlink(path), mode=stat.S_IMODE(info.st_mode))
    if stat.S_ISDIR(info.st_mode):
        return dict(kind='directory', mode=stat.S_IMODE(info.st_mode))
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Unexpected bound input file type: ' + str(path))
    return dict(kind='file', sha256=sha(path), bytes=info.st_size, mode=stat.S_IMODE(info.st_mode))


def bound_inputs():
    names = {'AGENTS.md', str(SELECTION.relative_to(ROOT)),
             'verification/apple-toggle-keyboard-full-case-root-review/v3-adapter/acceptance.json',
             'verification/apple-toggle-keyboard-full-case-root-review/v3-build/acceptance.json',
             'verification/apple-toggle-keyboard-full-case-preparation-v3/runtime-selection.json',
             'verification/apple-toggle-keyboard-full-case-preparation-v3/input-bindings.json',
             'verification/apple-toggle-keyboard-full-case-v3-build/supplement/build-products-manifest.json',
             'verification/apple-toggle-keyboard-full-case-v3-build/supplement/test-runner-products.tar.gz',
             'verification/apple-toggle-keyboard-full-case-v3-build/supplement/tools-verified.json',
             'docs/apple-toggle-keyboard-full-case-v3-adapter.md',
             'docs/apple-toggle-keyboard-full-case-v3-adapter-independent-review.md'}
    for relative in ['verification/apple-toggle-keyboard-full-case-v3-adapter/packet-seal.json',
                     'verification/apple-toggle-keyboard-full-case-v3-adapter-independent-review/review-seal.json',
                     'verification/apple-toggle-keyboard-full-case-v3-build/packet-seal.json',
                     'verification/apple-toggle-keyboard-full-case-preparation-v3/packet-seal.json',
                     'verification/apple-toggle-keyboard-full-case-independent-review-v3/review-seal.json']:
        names.add(relative)
        names.update(read(ROOT / relative)['files'])
    names.update(read(PREP / 'input-bindings.json'))
    names.update(read(ADAPTER / 'selected-inputs.json')['files'])
    return {name: file_record(pathlib.Path(name) if name.startswith('/') else ROOT / name) for name in sorted(names)}


def main():
    started = time.monotonic()
    publish('attempt-started.json', dict(schema=1, observedUTC=utc(), sourceRevision=REVISION,
        sourceRevisionScope='Inherited root acceptance metadata; no Git command', maximumNativeAttempts=1,
        retriesPermitted=False, compilerInvocationsPermitted=False, applicationRebuildPermitted=False,
        argv=[sys.executable, '-B', str(pathlib.Path(__file__).resolve())], cwd=str(ROOT),
        privateInvocation='adapter.compose().run(EXACT_ADAPTER_SEAL, "interaction")',
        adapterSealSHA256=SEAL, executionSelectionSHA256=SELECTION_HASH,
        pythonVersion=sys.version, pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
        pythonExecutableSHA256=sha(pathlib.Path(sys.executable).resolve()),
        toolMetadata=read(ROOT / 'verification/apple-toggle-keyboard-full-case-v3-build/supplement/tools-verified.json'),
        physicalPhones='disconnected-deferred', carrierAccepted=False, gaAccepted=False))
    stage = 'input-validation'
    harness = None
    native_calls = 0
    first_error = None
    result = None
    try:
        if sha(SELECTION) != SELECTION_HASH or sha(ADAPTER / 'packet-seal.json') != SEAL:
            raise ValueError('Root selected input changed')
        selected = read(SELECTION)
        if selected['status'] != 'one-bounded-native-attempt-selected' or selected['maximumAttempts'] != 1 or selected['retriesPermitted'] is not False:
            raise ValueError('Exact one-attempt root selection required')
        if selected['proposal']['methods'] != METHODS or selected['adapterSealSHA256'] != SEAL:
            raise ValueError('Root selected method/seal binding changed')
        before = bound_inputs()
        publish('inputs-before.json', before)
        stage = 'adapter-import-and-composition'
        # The accepted adapter needs its packet-local read-only helper bootstrap.
        sys.path.insert(0, str(ADAPTER))
        spec = importlib.util.spec_from_file_location('_mixer_selected_v3_native_adapter', ADAPTER / 'adapter.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        if str(inspect.signature(adapter.compose)) != '()':
            raise ValueError('Selected adapter compose signature changed')
        harness = adapter.compose()
        stage = 'private-run-contract-inspection'
        signature = str(inspect.signature(harness.run))
        if signature != "(reviewed_seal, scope='interaction')" or set(harness.SCOPES) != {'interaction'} or harness.SCOPES['interaction']['methods'] != METHODS:
            raise ValueError('Composed private runner signature/scope differs')
        publish('composition.json', dict(schema=1, observedUTC=utc(), adapterComposeSignature='()',
            composedResultType=type(harness).__name__, privateRunSignature=signature,
            expectedMethods=METHODS, expectedCases=sorted(harness.SCOPES['interaction']['cases']),
            runtimePath=str(harness.RUN_DIR), productArchive=str(harness.PRODUCT_ARCHIVE),
            nativeInvocationsSoFar=0, sourceOnlyComposition=True))
        stage = 'single-native-invocation'
        native_calls = 1
        publish('native-invocation-started.json', dict(schema=1, observedUTC=utc(), invocation=1,
            adapterSealSHA256=SEAL, scope='interaction', methods=METHODS))
        result = harness.run(SEAL, 'interaction')
        publish('returned-result.json', result)
    except BaseException as error:
        first_error = error
        redact = (harness.last_outcome.commands.redact if harness is not None and hasattr(harness, 'last_outcome') else lambda value: value)
        publish('original-exception.json', dict(schema=1, observedUTC=utc(), stage=stage,
            type=type(error).__name__, message=redact(str(error)),
            traceback=redact(''.join(traceback.format_exception(error))), nativeInvocationCount=native_calls,
            originalOutcomeRetained=True, retryAttempted=False))
        raise
    finally:
        if (BASE / 'inputs-before.json').exists():
            try:
                after = bound_inputs()
                publish('inputs-after.json', after)
                publish('input-reconciliation.json', dict(schema=1, observedUTC=utc(),
                    exactBeforeAfterMatch=after == read(BASE / 'inputs-before.json'), entries=len(after)))
            except BaseException as record_error:
                publish('input-reconciliation-error.json', dict(type=type(record_error).__name__, message=str(record_error)))
                if first_error is None:
                    raise
        publish('invocation-receipt.json', dict(schema=1, finishedUTC=utc(), seconds=time.monotonic()-started,
            sourceRevision=REVISION, nativeInvocationCount=native_calls, stage=stage,
            returnedNormally=first_error is None, originalExceptionType=None if first_error is None else type(first_error).__name__,
            runtimePathPresent=os.path.lexists(PREP / 'runtime'), physicalPhones='disconnected-deferred',
            nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False))


if __name__ == '__main__':
    main()
