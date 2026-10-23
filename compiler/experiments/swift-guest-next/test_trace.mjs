import test from 'node:test';
import assert from 'node:assert/strict';
import { addRequest, checkedView, memoryDiff, summarizeRequest } from './trace_support.mjs';

test('byte/page diff preserves absolute page identity and range boundaries', () => {
  const before = new Uint8Array(131073), after = before.slice();
  after[65535] = 1; after[65536] = 2; after[131072] = 3;
  assert.deepEqual(memoryDiff(before, after), { comparedBytes: 131073, changedBytes: 3, changed64KiBPages: 3 });
  assert.deepEqual(memoryDiff(before, after, 65535, 2), { comparedBytes: 2, changedBytes: 2, changed64KiBPages: 2 });
  assert.throws(() => memoryDiff(before, after, 131073, 1));
  assert.throws(() => memoryDiff(before, after, -1, 1));
});

test('iovec diagnostic sums separate ranges and rejects full out-of-bounds transfers', () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const view = new DataView(memory.buffer);
  view.setUint32(0, 100, true); view.setUint32(4, 3, true);
  view.setUint32(8, 200, true); view.setUint32(12, 7, true);
  assert.deepEqual(summarizeRequest('fd_write', [1, 0, 2, 20], memory), { fd: 1, iovecs: 2, requestedBytes: 10 });
  view.setUint32(12, 65536, true);
  assert.throws(() => summarizeRequest('fd_write', [1, 0, 2, 20], memory));
  assert.throws(() => checkedView(memory, -1, 2));
  assert.equal(checkedView(memory, 65536, 0).byteLength, 0);
  assert.throws(() => summarizeRequest('random_get', [-1, 2], memory));
});

test('request aggregation retains totals and bounds repeated metadata', () => {
  const entry = {};
  addRequest(entry, { fd: 1, iovecs: 2, requestedBytes: 10 });
  addRequest(entry, { fd: 1, iovecs: 3, requestedBytes: 5 });
  assert.deepEqual(entry, { fd: [1], maximumIovecs: 3, totalRequestedBytes: 15, maximumRequestedBytes: 10 });
  for (let i = 2; i <= 64; i++) addRequest(entry, { fd: i });
  assert.throws(() => addRequest(entry, { fd: 65 }));
});
