import assert from "node:assert/strict";
import childProcess, {spawn, spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {access, lstat, readFile} from "node:fs/promises";
import {createRequire} from "node:module";
import {createConnection, createServer} from "node:net";
import {join, resolve} from "node:path";
import {setTimeout as delay} from "node:timers/promises";
import {pathToFileURL} from "node:url";
import {selectOwnedWorkerd} from "../../hosted-worker-controller/test/owned-workerd-identity.mjs";
import {absent, deadline, until, WorkerdCustody} from "./workerd-custody.mjs";

const root = resolve(import.meta.dirname, "../..");
const [scratch, toolchain] = process.argv.slice(2);
assert(scratch && toolchain, "missing fixture paths");
const require = createRequire(join(toolchain, "package.json"));
const {Miniflare} = require("miniflare");
const workerd = require("workerd");
const lock = require(join(toolchain, "package-lock.json"));
for (const [name, version] of [["workerd", workerd.version], ["miniflare", require("miniflare/package.json").version]]) {
  assert.equal(version, lock.packages["node_modules/" + name].version, name + " differs from lock");
}
const {current, pointerKey} = await import(pathToFileURL(join(scratch, "dist/src/storage.js")));
const socketPath = join(scratch, "authority.sock");
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const receipt = {
  status: "failed", checks: {}, closure: {},
  node: process.version, workerd: workerd.version, miniflare: require("miniflare/package.json").version,
};
const frameLimit = 8 * 1024 * 1024 + 65_536;

async function* frames(socket) {
  let data = Buffer.alloc(0);
  for await (const bytes of socket) {
    assert(data.length + bytes.length <= frameLimit, "fixture response exceeds frame limit");
    data = Buffer.concat([data, bytes]);
    let newline;
    while ((newline = data.indexOf(10)) !== -1) {
      const line = data.subarray(0, newline);
      data = data.subarray(newline + 1);
      yield JSON.parse(line);
    }
  }
  assert.equal(data.length, 0, "incomplete fixture reply");
}

function connect(message) {
  const socket = createConnection({path: socketPath});
  socket.setTimeout(15_000, () => socket.destroy(new Error("fixture IPC deadline")));
  // The async iterator observes stream errors when awaiting a frame.
  const reader = frames(socket);
  const send = payload => socket.write(JSON.stringify(payload) + "\n");
  send(message);
  return {
    send, close: () => socket.destroy(),
    async read() {
      const {done, value} = await reader.next();
      assert(!done, "missing fixture reply");
      return value;
    },
  };
}

async function rpc(op, args = {}) {
  const client = connect({...args, op});
  try {
    return await client.read();
  } finally {
    client.close();
  }
}

function postgres(state) {
  const observed = spawnSync(join(scratch, "db-probe"), [join(scratch, "ca.pem"), state], {
    encoding: "utf8", timeout: 4500, maxBuffer: 4096,
  });
  assert.equal(observed.status, 0, observed.stderr || observed.error?.message);
  return observed.stdout.trim();
}

async function postmaster() {
  const [pid, data, , port] = (await readFile(join(scratch, "db/postmaster.pid"), "utf8")).split("\n");
  assert(data === join(scratch, "db") && port === "5432", "unexpected postmaster coordinates");
  const owned = Number(pid);
  assert(Number.isSafeInteger(owned) && owned > 1 && !absent(owned), "postmaster identity unavailable");
  return owned;
}

async function portReusable(port) {
  const server = createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
}

function launch(name, executable, args, cwd) {
  const child = spawn(executable, args, {cwd, detached: true, stdio: ["ignore", "pipe", "pipe"]});
  let output = "";
  for (const stream of [child.stdout, child.stderr]) {
    stream.on("data", chunk => { output = (output + chunk).slice(-32_768); });
  }
  let settled;
  const terminal = new Promise(resolve => {
    child.once("error", error => { settled = {error: error.message}; resolve(settled); });
    child.once("close", (code, signal) => { settled = {code, signal}; resolve(settled); });
  });
  return {
    pid: child.pid,
    get terminal() { return settled; },
    get output() { return output; },
    async close(signal) {
      const pid = child.pid;
      if (!pid) return {pid, ...await terminal};
      if (signal && !settled) child.kill(signal);
      const result = await deadline(terminal, 8000, name + "_close");
      await until(() => {
        const rows = processRows();
        return !rows.some(row => row.pid === pid || row.group === pid);
      }, 2500);
      return {pid, ...result, exactPidAbsent: true, groupAbsent: true};
    },
  };
}

function processRows() {
  const table = spawnSync("/bin/ps", ["-axo", "pid=,ppid=,pgid=,comm="], {
    encoding: "utf8", timeout: 3000, maxBuffer: 8 * 1024 * 1024,
  });
  assert.equal(table.status, 0, "process observation failed");
  return table.stdout.trim().split("\n").map(line => {
    const match = /^(\d+)\s+(\d+)\s+(\d+)\s+(.+)$/.exec(line.trim());
    assert(match, "process identity unavailable");
    return {pid: Number(match[1]), parentPid: Number(match[2]), group: Number(match[3]), command: match[4]};
  }).filter(row => row.pid !== table.pid);
}

function observeWorkerd(phase, custody) {
  custody.observe(phase, () => {
    const processes = processRows();
    const identity = selectOwnedWorkerd({
      ownerPid: process.pid, executable: workerd.default, platform: process.platform, processes,
    });
    return {pid: identity.pid, processes};
  });
}

const originalSpawn = childProcess.spawn;
const custody = new WorkerdCustody();
childProcess.spawn = function captureWorkerd(program, args, options) {
  if (program === workerd.default) {
    return custody.capture(originalSpawn.bind(this), program, args, options);
  }
  return originalSpawn.call(this, program, args, options);
};

let database;
let databaseClosing;
let authority;
let runtime;
let publicURL;
let ipc;
let phase = "normal";
let lastAck;
let fenceCalls = 0;
let fixtureDone = false;
let fixtureReady = false;

async function startDatabase() {
  assert(!database, "owned database already started");
  databaseClosing = undefined;
  database = launch("postgres", "postgres", ["-D", join(scratch, "db")], scratch);
  await until(() => {
    assert(!database.terminal, database.output);
    const ready = spawnSync("pg_isready", ["-h", scratch, "-p", "5432", "-t", "1"], {timeout: 1500});
    assert(!ready.error, ready.error?.message);
    return ready.status === 0;
  }, 7000);
  assert.equal(await postmaster(), database.pid);
}

function closeDatabase() {
  assert(database, "missing owned database");
  databaseClosing ??= database.close("SIGINT").then(closed => {
    database = undefined;
    return closed;
  });
  return databaseClosing;
}

async function stopDatabase() {
  const owned = database;
  const closed = await closeDatabase();
  assert.equal(closed.code, 0, owned.output);
  assert.equal(postgres("down"), "connection_refused");
  return closed;
}

try {
  await startDatabase();
  authority = launch("phoenix", "mix", [
    "test", "--warnings-as-errors", "--trace", "test/mixer_hosted/releases/configured_release_replay_test.exs",
  ], join(root, "hosted"));
  await until(async () => {
    assert(!authority.terminal, authority.output);
    return access(join(scratch, "authority.ready")).then(() => true, () => false);
  }, 90_000);
  fixtureReady = true;
  const socket = await lstat(socketPath);
  assert(socket.isSocket() && (socket.mode & 0o777) === 0o600);
  const fixture = await rpc("fixture");
  const {target, active, historical, staged_digest: staged, halt_assignment: haltAssignment} = fixture;
  receipt.checks.database = {before: postgres("up")};
  const dist = join(scratch, "dist");

  async function bridge(request) {
    const operation = new URL(request.url).pathname.slice(1);
    assert.equal(request.method, "POST");
    const body = await request.json();
    if (operation === "read" || operation === "artifact") {
      return Response.json(await rpc(operation, body));
    }
    if (operation === "fence") {
      assert(!ipc, "overlapping fence");
      fenceCalls++;
      if (phase === "stale") assert.equal(await rpc("halt"), "halted");
      const client = connect({...body, op: "fence"});
      try {
        const response = await client.read();
        if (Object.hasOwn(response, "grant_ms")) ipc = client;
        return Response.json(response);
      } finally {
        if (!ipc) client.close();
      }
    }
    if (operation === "finish" && ipc) {
      const client = ipc;
      ipc = undefined;
      lastAck = body.result;
      try {
        // Simulate losing proof of an already-dispatched CAS. The authority
        // peer must never acknowledge it positively in this control.
        if (phase !== "late") client.send({result: phase === "lost" ? "indeterminate" : body.result});
        return Response.json(await client.read());
      } finally {
        client.close();
      }
    }
    return new Response(null, {status: 404});
  }

  const common = {
    modules: true, modulesRoot: dist, compatibilityDate: "2026-07-30",
    modulesRules: [{type: "ESModule", include: ["**/*.js"]}],
    bindings: {DELIVERY_TARGET: JSON.stringify(target)},
    r2Buckets: {DELIVERY_PUBLIC: "release-replay"},
  };
  runtime = new Miniflare({host: "127.0.0.1", port: 0, cf: false, r2Persist: join(scratch, "r2"), workers: [
    {...common, name: "delivery", scriptPath: join(dist, "src/index.js")},
    {...common, name: "fixture-publisher", routes: [], scriptPath: join(dist, "test/cross-runtime-worker.js"),
      durableObjects: {PUBLISHER: "FixturePublisher"},
      serviceBindings: {AUTHORITY: bridge}},
  ]});
  publicURL = await deadline(runtime.ready, 12_000, "workerd_ready");
  observeWorkerd("ready", custody);

  const privateNamespace = await deadline(runtime.getDurableObjectNamespace("PUBLISHER", "fixture-publisher"),
    4000, "writer_binding");
  const writer = privateNamespace.get(privateNamespace.idFromName("release-replay"));
  const bucket = await deadline(runtime.getR2Bucket("DELIVERY_PUBLIC", "delivery"), 4000, "bucket_binding");
  const readPointer = () => current(bucket, target);
  const key = pointerKey(target);
  async function publish(leaseMs, late = false) {
    // Miniflare calls Durable Object stubs asynchronously. Its generic Worker
    // RPC proxy can block the Node event loop used by the authority binding.
    const reply = await deadline(writer.publish(target, leaseMs, late), 9000, "publish");
    return {result: reply.result, attempted: reply.attempted};
  }
  const offer = fields => "/v3/updates?" + new URLSearchParams({...target, installation: "fixture-installation", ...fields});
  const download = (digest, fields) => "/v3/artifacts/" + digest + "?" +
    new URLSearchParams({organization: target.organization, project: target.project, ...fields});
  async function read(path, status, options) {
    const response = await fetch(new URL(path, publicURL), {...options, signal: AbortSignal.timeout(2500)});
    assert.equal(response.status, status, path);
    const data = Buffer.from(await response.arrayBuffer());
    if (path.startsWith("/v3/")) assert.equal(response.headers.get("cache-control"), "no-store");
    return data;
  }

  const activeSigned = Buffer.from(active.assignment, "base64");
  const activeBytes = Buffer.from(active.envelope, "base64");
  const historicalBytes = Buffer.from(historical.envelope, "base64");
  const expectedOffer = Buffer.from('{"signed_assignment":' + activeSigned +
    ',"artifact_url":' + JSON.stringify(download(active.digest)) + '}');
  const expectedArtifacts = [
    {manifest_sha256: active.digest, envelope_sha256: hash(activeBytes)},
    {manifest_sha256: historical.digest, envelope_sha256: hash(historicalBytes)},
  ];

  async function assertVisible() {
    assert.deepEqual(await read(offer(), 200), expectedOffer);
    assert.deepEqual(await read(download(active.digest), 200), activeBytes);
    assert.deepEqual(await read(download(historical.digest), 200), historicalBytes);
    await read(offer({organization: "unrelated-org"}), 204);
    await read(offer({channel: "unrelated-channel"}), 204);
    await read(download(active.digest, {project: "unrelated-project"}), 404);
    await read(download(staged), 404);
  }

  const noWrite = {result: "unavailable", attempted: null};
  await read("/publish", 405, {method: "POST"});
  const forcedWriter = await deadline(writer.fetch("http://fixture.invalid/publish", {method: "POST"}),
    3000, "writer_http_denial");
  assert.equal(forcedWriter.status, 404);
  await read(offer(), 204);
  await read(download(active.digest), 404);
  assert.equal(await rpc("read", {target: {...target, project: "unrelated-project"}}), null);
  assert.equal(await readPointer(), null);

  const issued = await publish(6500);
  assert.equal(issued.result, "applied");
  const initial = await readPointer();
  assert.equal(initial.hash, issued.attempted);
  assert.equal(initial.snapshot.revision, "1");
  assert.equal(initial.snapshot.expires_at_ms - initial.snapshot.issued_at_ms, 6500);
  assert.equal(initial.snapshot.head.sequence, "8");
  assert.equal(initial.snapshot.head.assignment_sha256, hash(activeSigned));
  assert.deepEqual(initial.snapshot.artifacts, expectedArtifacts);
  const stagedArtifacts = await bucket.list({prefix: key.replace("/current", "/artifact/")});
  assert(!stagedArtifacts.truncated);
  assert.deepEqual(stagedArtifacts.objects.map(entry => entry.key.split("/").at(-1)).sort(),
    expectedArtifacts.map(entry => entry.manifest_sha256).sort());

  await assertVisible();
  const {assignment: _, ...priorAuthority} = await rpc("read", {target});
  receipt.closure.outagePostmaster = await stopDatabase();
  receipt.checks.database.outage = "connection_refused";
  assert(Date.now() < initial.snapshot.expires_at_ms);
  await assertVisible();
  assert(Date.now() < initial.snapshot.expires_at_ms, "before-expiry reads overran lease");
  assert.deepEqual(await rpc("fence", {authority: priorAuthority}), {result: "unavailable"});
  const callsBeforeRefresh = fenceCalls;
  assert.deepEqual(await publish(6500), noWrite);
  assert.equal(fenceCalls, callsBeforeRefresh);
  assert.deepEqual(await readPointer(), initial);
  await delay(Math.max(0, initial.snapshot.expires_at_ms - Date.now() + 50));
  await read(offer(), 204);
  await read(download(active.digest), 404);
  await read(download(historical.digest), 404);
  assert.deepEqual(await readPointer(), initial);
  receipt.checks.outage = {
    offerSha256: hash(expectedOffer), assignmentSha256: hash(activeSigned),
    artifacts: expectedArtifacts, unrelatedDenied: true, stagedOnlyDenied: true,
    writerHttpDenied: true, initialPointer: initial, freshReadUnavailable: true,
    cachedFenceUnavailable: true, expiredOffer: 204, expiredArtifacts: [404, 404],
  };

  await startDatabase();
  receipt.checks.database.recovered = postgres("up");
  await until(async () => (await rpc("read", {target})) !== null, 6000);

  phase = "late";
  assert.deepEqual(await publish(120_000, true), {result: "indeterminate", attempted: null});
  assert.equal(lastAck, "expired");
  assert.deepEqual(await readPointer(), initial);
  receipt.checks.late = {result: "indeterminate", localPermit: "expired", pointerUnchanged: true};

  phase = "lost";
  const lost = await publish(120_000);
  assert.equal(lost.result, "indeterminate");
  assert.equal(lastAck, "applied");
  const recovered = await readPointer();
  assert.equal(recovered.hash, lost.attempted);
  assert.equal(recovered.snapshot.revision, "2");
  assert.deepEqual(recovered.snapshot.head, initial.snapshot.head);
  assert.deepEqual(recovered.snapshot.artifacts, expectedArtifacts);
  assert.equal(recovered.snapshot.expires_at_ms, fixture.valid_until_unix * 1000);
  await assertVisible();
  receipt.checks.recovery = {ambiguity: "indeterminate", reconciled: recovered, rootDeadlineCap: true};

  await until(() => rpc("writer_ready"), 8000);
  phase = "stale";
  assert.deepEqual(await publish(120_000), {result: "stale", attempted: null});
  assert.deepEqual(await readPointer(), recovered);
  phase = "normal";
  const stopped = await publish(120_000);
  assert.equal(stopped.result, "applied");
  const halted = await readPointer();
  assert.equal(halted.hash, stopped.attempted);
  assert.equal(halted.snapshot.revision, "3");
  assert.equal(halted.snapshot.head.sequence, "9");
  assert.equal(halted.snapshot.head.enabled, false);
  assert.equal(halted.snapshot.head.assignment_sha256, hash(Buffer.from(haltAssignment, "base64")));
  assert.deepEqual(halted.snapshot.artifacts, expectedArtifacts);
  assert.equal(await bucket.put(key, recovered.hash, {onlyIf: {etagMatches: recovered.etag}}), null);
  assert.deepEqual(await readPointer(), halted);
  await read(offer(), 204);
  assert.deepEqual(await read(download(active.digest), 200), activeBytes);
  assert.deepEqual(await read(download(historical.digest), 200), historicalBytes);
  await read(download(staged), 404);
  receipt.checks.halt = {staleAuthorityRefused: true, staleEtagRefused: true, offer: 204, pointer: halted};
  receipt.closure.recoveredPostmaster = await stopDatabase();
  assert.equal(await rpc("done"), "done");
  fixtureDone = true;
  receipt.status = "passed";
} catch (error) {
  receipt.failure = String(error.stack ?? error).slice(0, 3500);
} finally {
  ipc?.close();
  const cleanup = await Promise.allSettled([
    (async () => {
      if (database) receipt.closure.postmaster = await closeDatabase();
    })(),
    (async () => {
      if (!authority) return;
      if (fixtureReady && !fixtureDone && !authority.terminal) {
        fixtureDone = await rpc("done").then(value => value === "done", () => false);
      }
      receipt.closure.phoenix = await authority.close(fixtureDone ? undefined : "SIGTERM");
      if (receipt.status === "passed") {
        assert.equal(receipt.closure.phoenix.code, 0, authority.output);
        const summary = /Result: 1 passed, 3 skipped/.exec(authority.output);
        const seed = /seed: (\d+)/.exec(authority.output)?.[1];
        assert(summary && seed, authority.output);
        receipt.exunit = {summary: summary[0], seed: Number(seed)};
        await Promise.all([portReusable(5432), portReusable(47301)]);
        receipt.closure.databaseAndPhoenixPortsReusable = true;
      }
    })(),
    (async () => {
      if (!runtime) return;
      if (custody.receipt.ready === "verified") {
        try { observeWorkerd("beforeDispose", custody); } catch { /* still dispose owned instance */ }
      }
      await custody.close(() => runtime.dispose());
      custody.assertTerminal();
      await assert.rejects(fetch(publicURL, {signal: AbortSignal.timeout(1000)}), /fetch failed/);
      receipt.closure.workerd = custody.receipt;
    })(),
  ]);
  childProcess.spawn = originalSpawn;
  const unknown = cleanup.filter(result => result.status === "rejected");
  if (unknown.length) {
    receipt.status = "failed";
    receipt.closure.hold = {scratch, databasePid: database?.pid, phoenixPid: authority?.pid, workerd: custody.receipt,
      errors: unknown.map(result => String(result.reason).slice(0, 500))};
    process.exitCode = 74;
  } else if (receipt.status !== "passed") {
    process.exitCode = 1;
  }
  if (receipt.status !== "passed") {
    process.stderr.write((authority?.output ?? "") + (database?.output ?? ""));
  }
  process.stdout.write("MIXER_DELIVERY_REPLAY " + JSON.stringify(receipt) + "\n", () => {
    if (unknown.length) process.exit(74);
  });
}
