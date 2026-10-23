// Independently authored diagnostic helpers. No production execution authority.
export function memoryDiff(before, after, start = 0, length = before.length) {
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(length) || start < 0 || length < 0 ||
      start + length > before.length || start + length > after.length) throw Error('invalid diff range');
  let changedBytes = 0;
  const pages = new Set();
  for (let i = start; i < start + length; i++) {
    if (before[i] !== after[i]) { changedBytes++; pages.add(Math.floor(i / 65536)); }
  }
  return { comparedBytes: length, changedBytes, changed64KiBPages: pages.size };
}

export function checkedView(memory, pointer, bytes) {
  pointer >>>= 0;
  if (!Number.isSafeInteger(bytes) || bytes < 0 || pointer + bytes > memory.buffer.byteLength) {
    throw Error('diagnostic observed out-of-bounds import range');
  }
  return new DataView(memory.buffer, pointer, bytes);
}

export function summarizeRequest(name, args, memory) {
  const u32 = n => n >>> 0;
  if (name === 'random_get') {
    checkedView(memory, args[0], u32(args[1]));
    return { requestedBytes: u32(args[1]) };
  }
  if (name === 'clock_time_get') return { clockID: u32(args[0]), precision: String(args[1]) };
  if (name === 'clock_res_get') return { clockID: u32(args[0]) };
  if (name === 'fd_write' || name === 'fd_read') {
    const count = u32(args[2]);
    if (count > 65536) throw Error('diagnostic iovec count exceeded');
    const view = checkedView(memory, args[1], count * 8);
    let requestedBytes = 0;
    for (let i = 0; i < count; i++) {
      const pointer = view.getUint32(i * 8, true);
      const bytes = view.getUint32(i * 8 + 4, true);
      checkedView(memory, pointer, bytes);
      requestedBytes += bytes;
    }
    return { fd: u32(args[0]), iovecs: count, requestedBytes };
  }
  if (name.startsWith('fd_')) return { fd: u32(args[0]) };
  if (name === 'proc_exit') return { exitCode: u32(args[0]) };
  return {};
}

export function addRequest(entry, request) {
  for (const [key, value] of Object.entries(request)) {
    if (key === 'requestedBytes') {
      entry.totalRequestedBytes = (entry.totalRequestedBytes ?? 0) + value;
      entry.maximumRequestedBytes = Math.max(entry.maximumRequestedBytes ?? 0, value);
    } else if (key === 'iovecs') entry.maximumIovecs = Math.max(entry.maximumIovecs ?? 0, value);
    else {
      entry[key] ??= [];
      if (!entry[key].includes(value)) {
        if (entry[key].length >= 64) throw Error('diagnostic distinct-value limit exceeded');
        entry[key].push(value);
      }
    }
  }
}
