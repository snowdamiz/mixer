import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { WASI } from 'node:wasi';
import { performance } from 'node:perf_hooks';

const [mode, artifact] = process.argv.slice(2);
assert.ok(['command', 'reactor', 'inspect'].includes(mode));
const started = performance.now();
const module = new WebAssembly.Module(readFileSync(artifact));
const compiled = performance.now();
const imports = WebAssembly.Module.imports(module);
const exports = WebAssembly.Module.exports(module);
const report = { imports, exports, readAndCompileMs: compiled - started };

if (mode !== 'inspect') {
  const wasi = new WASI({
    version: 'preview1', args: ['fieldlog'], env: {}, preopens: {}, returnOnExit: true,
  });
  const importObject = wasi.getImportObject();
  const calls = {};
  const lastReturn = {};
  for (const { module: namespace, name, kind } of imports) {
    assert.equal(namespace, 'wasi_snapshot_preview1');
    assert.equal(kind, 'function');
    const original = importObject[namespace][name];
    assert.equal(typeof original, 'function');
    importObject[namespace][name] = (...args) => {
      calls[name] = (calls[name] ?? 0) + 1;
      if (name === 'proc_exit') {
        report.wasiExit = args[0];
      }
      const result = original(...args);
      lastReturn[name] = result;
      return result;
    };
  }
  const instance = new WebAssembly.Instance(module, importObject);
  const instantiated = performance.now();
  report.instantiateMs = instantiated - compiled;
  report.initialLinearBytes = instance.exports.memory.buffer.byteLength;
  report.calls = calls;
  report.lastReturn = lastReturn;

  if (mode === 'command') {
    const status = wasi.start(instance);
    report.completeJourneyMs = performance.now() - instantiated;
    report.exitCode = status;
    if (status !== 0) process.exitCode = 1;
  } else {
    const { memory, mixer_guest_ui_start_v3: start, mixer_guest_ui_event_v3: event } = instance.exports;
    const measure = (label, operation) => {
      const stepStarted = performance.now();
      const value = operation();
      report.turns[label] = performance.now() - stepStarted;
      return value;
    };
    report.turns = {};
    measure('initialize', () => wasi.initialize(instance));
    const pointer = measure('firstFrame', start);
    const readHeader = () => {
      const words = new DataView(memory.buffer, pointer, 32);
      assert.equal(words.getUint32(0, true), 0x3349554d);
      assert.equal(words.getUint32(4, true), 32);
      const document = words.getUint32(8, true);
      const length = words.getUint32(12, true);
      const input = words.getUint32(16, true);
      assert.equal(words.getUint32(20, true), 1_048_576);
      assert.ok(length > 0 && length <= 4096);
      const frame = new Uint8Array(memory.buffer, document, length);
      const value = new TextDecoder('utf-8', { fatal: true }).decode(frame);
      console.log(value);
      return input;
    };
    let input = readHeader();
    for (const [index, label] of ['load', 'open', 'blankSave', 'save', 'reopen'].entries()) {
      new Uint8Array(memory.buffer, input, 1)[0] = index + 1;
      assert.equal(measure(label, () => event(1)), pointer);
      input = readHeader();
    }
  }

  report.finalLinearBytes = instance.exports.memory.buffer.byteLength;
  report.peakProcessRSSBytes = process.resourceUsage().maxRSS * 1024;
}
console.error(JSON.stringify(report));
