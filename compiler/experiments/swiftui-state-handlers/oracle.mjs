import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { WASI } from 'node:wasi';

const wasi = new WASI({ version: 'preview1', preopens: {}, returnOnExit: true });
const module = await WebAssembly.compile(await readFile(process.argv[2]));
const instance = await WebAssembly.instantiate(module, wasi.getImportObject());
assert.equal(instance.exports._start, undefined);
wasi.initialize(instance);
assert.equal(instance.exports.mixer_s3_replay(), 0);
