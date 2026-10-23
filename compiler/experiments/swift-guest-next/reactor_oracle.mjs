// Development oracle for the original linker-only probe; no owned-VM qualification.
import { readFile } from 'node:fs/promises';
import { WASI } from 'node:wasi';
import assert from 'node:assert/strict';
const module = await WebAssembly.compile(await readFile(process.argv[2]));
const wasi = new WASI({ version: 'preview1', args: [], env: {}, preopens: {}, returnOnExit: true });
const instance = await WebAssembly.instantiate(module, wasi.getImportObject());
assert.equal(instance.exports._start, undefined);
assert.equal(typeof instance.exports._initialize, 'function');
wasi.initialize(instance);
assert.equal(instance.exports.mixer_linker_probe_add(20, 22), 42);
assert.equal(instance.exports.mixer_linker_probe_add(2147483647, 1), -2147483648);
console.log(JSON.stringify({ authorization: false, oracleOnly: true, result: 42,
  wrappedResult: -2147483648, exports: WebAssembly.Module.exports(module), imports: WebAssembly.Module.imports(module) }));
