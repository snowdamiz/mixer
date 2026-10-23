// Original, read-only reference diagnostic. This grants no owned-VM authority.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { WASI } from 'node:wasi';

const [path, expectedHash] = process.argv.slice(2);
const bytes = await readFile(path);
assert.equal(createHash('sha256').update(bytes).digest('hex'), expectedHash);
const module = await WebAssembly.compile(bytes);
const wasi = new WASI({version: 'preview1', args: ['fieldlog-corpus'], env: {}, preopens: {}, returnOnExit: true});
const imports = wasi.getImportObject();
let instance;
let phase = 'instantiate';
const phases = {};
const u32 = value => value >>> 0;
const counters = () => phases[phase] ??= {calls: {}, randomBytes: 0, randomMaximumRequest: 0, clockIds: {}, writeBytes: 0, writeMaximumIovecs: 0, writeFds: {}, preopenResults: {}, fdstatResults: {}, errno: {}};
const bump = (object, key) => { object[key] = (object[key] ?? 0) + 1; };
for (const [name, operation] of Object.entries(imports.wasi_snapshot_preview1)) {
    imports.wasi_snapshot_preview1[name] = (...args) => {
        const c = counters();
        bump(c.calls, name);
        if (name === 'random_get') {
            c.randomBytes += u32(args[1]);
            c.randomMaximumRequest = Math.max(c.randomMaximumRequest, u32(args[1]));
        }
        if (name === 'clock_time_get' || name === 'clock_res_get') bump(c.clockIds, `${name}:${u32(args[0])}`);
        if (name === 'fd_write') {
            const memory = new DataView(instance.exports.memory.buffer);
            const count = u32(args[2]);
            assert.ok(count <= 1024, 'diagnostic iovec ceiling');
            c.writeMaximumIovecs = Math.max(c.writeMaximumIovecs, count);
            bump(c.writeFds, u32(args[0]));
            for (let index = 0; index < count; index++) {
                const entry = u32(args[1]) + index * 8;
                assert.ok(entry + 8 <= memory.byteLength);
                c.writeBytes += memory.getUint32(entry + 4, true);
            }
        }
        const result = operation(...args);
        if (typeof result === 'number') bump(c.errno, `${name}:${result}`);
        if (name === 'fd_prestat_get') bump(c.preopenResults, `${u32(args[0])}:${result}`);
        if (name === 'fd_fdstat_get') {
            const memory = new DataView(instance.exports.memory.buffer);
            const start = u32(args[1]);
            assert.ok(start + 24 <= memory.byteLength);
            // Only defined fields count; ABI padding and the oracle's pipe rights
            // are not the desired contract for a bounded product logging sink.
            const value = {filetype: memory.getUint8(start), flags: memory.getUint16(start + 2, true), rightsBase: memory.getBigUint64(start + 8, true).toString(), rightsInheriting: memory.getBigUint64(start + 16, true).toString()};
            bump(c.fdstatResults, `${u32(args[0])}:${result}:${JSON.stringify(value)}`);
        }
        return result;
    };
}
instance = await WebAssembly.instantiate(module, imports);
const memory = [{phase, bytes: instance.exports.memory.buffer.byteLength}];
assert.equal(instance.exports._start, undefined);
phase = 'initialize';
wasi.initialize(instance);
memory.push({phase, bytes: instance.exports.memory.buffer.byteLength});
const statuses = [];
for (let index = 1; index <= 2; index++) {
    phase = `invoke-${index}`;
    statuses.push(instance.exports.mixer_fieldlog_corpus_v1());
    memory.push({phase, bytes: instance.exports.memory.buffer.byteLength});
}
assert.deepEqual(statuses, [0, 0]);
console.error('EXECUTION_NEXT_DIAGNOSTIC ' + JSON.stringify({authorization: false, ownedExecution: false, moduleSHA256: expectedHash, initializationCalls: 1, statuses, phases, memory}));
