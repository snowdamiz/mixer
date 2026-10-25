// Node's WASI is a development oracle, never an owned runtime/admission receipt.
import { WASI } from 'node:wasi';
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const [mode, path] = process.argv.slice(2);
assert.ok(mode === 'command' || mode === 'reactor');
const module = await WebAssembly.compile(await readFile(path));
const wasi = new WASI({ version: 'preview1', args: ['fieldlog-corpus'], env: {}, preopens: {}, returnOnExit: true });
const imports = wasi.getImportObject();
let phase = 'instantiate';
const calls = {};
for (const [name, operation] of Object.entries(imports.wasi_snapshot_preview1)) {
    imports.wasi_snapshot_preview1[name] = (...args) => {
        const byPhase = calls[phase] ??= {};
        byPhase[name] = (byPhase[name] ?? 0) + 1;
        return operation(...args);
    };
}
const instance = await WebAssembly.instantiate(module, imports);
const memory = [{ phase, bytes: instance.exports.memory.buffer.byteLength }];
let initializationCalls = 0;
const statuses = [];
if (mode === 'reactor') {
    assert.equal(instance.exports._start, undefined);
    assert.equal(typeof instance.exports._initialize, 'function');
    assert.equal(typeof instance.exports.mixer_fieldlog_corpus_v1, 'function');
    phase = 'initialize';
    // WASI.initialize invokes the actual exported _initialize exactly once.
    // It must not be followed by a direct second _initialize call.
    initializationCalls += 1;
    wasi.initialize(instance);
    memory.push({ phase, bytes: instance.exports.memory.buffer.byteLength });
    for (let index = 0; index < 2; index++) {
        phase = `invoke-${index + 1}`;
        statuses.push(instance.exports.mixer_fieldlog_corpus_v1());
        assert.equal(statuses.at(-1), 0);
        memory.push({ phase, bytes: instance.exports.memory.buffer.byteLength });
    }
} else {
    assert.equal(instance.exports.mixer_fieldlog_corpus_v1, undefined);
    phase = 'command';
    statuses.push(wasi.start(instance));
    assert.equal(statuses[0], 0);
    memory.push({ phase, bytes: instance.exports.memory.buffer.byteLength });
}
console.error('FIELDLOG_ORACLE ' + JSON.stringify({ authorization: false, mode,
    initializationCalls, invocationCalls: mode === 'reactor' ? 2 : 1, statuses,
    calls, memory, exports: WebAssembly.Module.exports(module), imports: WebAssembly.Module.imports(module) }));
