// Development-only Node WASI oracle; not the owned interpreter or an admission token.
import { WASI } from 'node:wasi';
import { readFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { addRequest, memoryDiff, summarizeRequest } from './trace_support.mjs';

const expectedBytes = 52008982;
const expectedSHA = '19ac88f26f0daf34b64acb3c5b895fc79b52701368fc4c532ac8ede5844fee75';
const icu = { start: 1814864, bytes: 33976096,
  sha256: '7ca4d8abf60fbc0b25e57dc658b8c4c4236774d0c78fff601d3cad2dccd59dd9' };
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
if (process.argv.length !== 3) throw Error('usage: trace.mjs immutable-candidate.wasm');
if ((await stat(process.argv[2])).size !== expectedBytes) throw Error('unexpected artifact byte size');
const source = await readFile(process.argv[2]);
if (hash(source) !== expectedSHA) throw Error('unexpected artifact SHA-256');
const module = await WebAssembly.compile(source);
const wasi = new WASI({ version: 'preview1', args: ['fieldlog-corpus'], env: {}, preopens: {}, returnOnExit: true });
const imports = wasi.getImportObject();
const declared = WebAssembly.Module.imports(module);
const counts = {};
let instance, totalCalls = 0;
Error.stackTraceLimit = 40;
const randomSamples = new Set([1, 2, 3, 4, 16, 512, 1024, 2048, 2509, 2510]);
for (const descriptor of declared) {
  if (descriptor.module !== 'wasi_snapshot_preview1' || descriptor.kind !== 'function') {
    throw Error('unexpected import family or kind');
  }
  const { module: namespace, name } = descriptor;
  const implementation = imports[namespace][name];
  if (typeof implementation !== 'function' || counts[name]) throw Error('missing or duplicate import');
  const entry = counts[name] = { calls: 0, returns: {}, threw: 0 };
  imports[namespace][name] = (...args) => {
    if (!instance) throw Error('unexpected pre-instance import');
    if (++totalCalls > 100000) throw Error('diagnostic host-call limit exceeded');
    entry.calls++;
    addRequest(entry, summarizeRequest(name, args, instance.exports.memory));
    if (name === 'random_get' && randomSamples.has(entry.calls)) {
      entry.sampleStacks ??= [];
      entry.sampleStacks.push({ call: entry.calls, requestedBytes: args[1] >>> 0, stack: new Error('random_get diagnostic sample').stack });
    }
    try {
      const result = implementation(...args);
      const key = result === undefined ? 'void' : String(result);
      entry.returns[key] = (entry.returns[key] ?? 0) + 1;
      return result;
    } catch (error) { entry.threw++; throw error; }
  };
}
instance = await WebAssembly.instantiate(module, imports);
const before = new Uint8Array(instance.exports.memory.buffer).slice();
if (hash(before.subarray(icu.start, icu.start + icu.bytes)) !== icu.sha256) {
  throw Error('unexpected instantiated ICU bytes');
}
const exitCode = wasi.start(instance);
const after = new Uint8Array(instance.exports.memory.buffer);
let newNonzeroBytes = 0;
for (let i = before.length; i < after.length; i++) if (after[i]) newNonzeroBytes++;
const report = {
  authorization: false, oracleOnly: true, artifact: { bytes: source.length, sha256: hash(source) },
  wasiOptions: { args: ['fieldlog-corpus'], env: {}, preopens: {}, returnOnExit: true },
  exitCode, totalCalls, declaredImports: declared, imports: counts,
  invokedImports: Object.keys(counts).filter(name => counts[name].calls),
  uninvokedImports: Object.keys(counts).filter(name => !counts[name].calls),
  memory: { beforeStartBytes: before.length, afterStartBytes: after.length, peakMeasured: false,
    initialExtent: memoryDiff(before, after),
    icuExtent: { ...icu, ...memoryDiff(before, after, icu.start, icu.bytes) },
    grownBytes: after.length - before.length, newNonzeroBytes,
    scope: 'only before/after byte differences; restored writes, interim writes and peak growth are not observed' },
};
console.error('SWIFT_GUEST_TRACE ' + JSON.stringify(report));
process.exitCode = exitCode;
