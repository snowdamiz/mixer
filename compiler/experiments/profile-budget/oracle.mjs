// Development oracle only. Production execution remains the independently owned VM.
import { WASI } from 'node:wasi';
import { readFile } from 'node:fs/promises';
const wasi = new WASI({ version: 'preview1', args: ['fieldlog-corpus'], env: {}, preopens: {}, returnOnExit: true });
const module = await WebAssembly.compile(await readFile(process.argv[2]));
const instance = await WebAssembly.instantiate(module, wasi.getImportObject());
const before = instance.exports.memory.buffer.byteLength;
const status = wasi.start(instance);
console.error('PROFILE_MEMORY ' + JSON.stringify({ beforeStartBytes: before, afterStartBytes: instance.exports.memory.buffer.byteLength, peakMeasured: false }));
process.exitCode = status;
