import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { WASI } from 'node:wasi';

const wasi = new WASI({ version: 'preview1', preopens: {}, returnOnExit: true });
const module = await WebAssembly.compile(await readFile(process.argv[2]));
const instance = await WebAssembly.instantiate(module, wasi.getImportObject());
assert.equal(instance.exports._start, undefined);
wasi.initialize(instance);
if (process.argv[3] === undefined) {
  assert.equal(instance.exports.mixer_s3_replay(), 0);
} else {
  const { memory, mixer_guest_ui_start_v3: start, mixer_guest_ui_event_v3: event } = instance.exports;
  let header = start();
  for (let step = 0; step < Number(process.argv[3]); step += 1) {
    assert.notEqual(header, 0);
    const view = new DataView(memory.buffer, header, 32);
    assert.equal(view.getUint32(0, true), 0x3349554d);
    assert.equal(view.getUint32(4, true), 32);
    const frame = view.getUint32(8, true);
    const length = view.getUint32(12, true);
    console.log(new TextDecoder('utf-8', { fatal: true }).decode(new Uint8Array(memory.buffer, frame, length)));
    if (step + 1 < Number(process.argv[3])) {
      new Uint8Array(memory.buffer, view.getUint32(16, true), 1)[0] = step + 1;
      header = event(1);
    }
  }
}
