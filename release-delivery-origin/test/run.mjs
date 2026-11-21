import assert from "node:assert/strict";
import childProcess, {spawn, spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mkdir, mkdtemp, readFile, writeFile} from "node:fs/promises";
import {createRequire} from "node:module";
import {join, resolve} from "node:path";
import {setTimeout as delay} from "node:timers/promises";
import {selectOwnedWorkerd} from "../../hosted-worker-controller/test/owned-workerd-identity.mjs";
import {exerciseProjectionPublisher} from "./publisher.mjs";
import {absent, deadline, removeReplayScratch, until, WorkerdCustody} from "./workerd-custody.mjs";

const root = resolve(import.meta.dirname, "../..");
const controller = join(root, "hosted-worker-controller");
const require = createRequire(join(controller, "package.json"));
const pgTools = process.env.MIXER_DELIVERY_PG_BIN;
const {Miniflare} = require("miniflare");
const workerd = require("workerd");
const scratch = await mkdtemp("/tmp/mixer-w11-delivery-");
process.env.TMPDIR = scratch;
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const receipt = {
  node: process.version, workerd: workerd.version,
  miniflare: require("miniflare/package.json").version,
  status: "failed", commands: {}, checks: {}, closure: {},
};
const tools = tool => pgTools ? join(pgTools, tool) : tool;

const unresolved = new Set();
function launch(name, program, args, options = {}) {
  const child = spawn(program, args, {stdio: ["ignore", "pipe", "pipe"], detached: true, ...options});
  const terminal = new Promise(resolve => {
    child.once("error", error => resolve({error}));
    child.once("close", (code, signal) => resolve({code, signal}));
  });
  let output = "";
  let stderr = "";
  child.stdout.on("data", bytes => { output = (output + bytes).slice(-128_000); });
  child.stderr.on("data", bytes => { stderr = (stderr + bytes).slice(-32_000); });
  const pid = child.pid;
  if (pid) unresolved.add(pid);

  async function collect(ms) {
    const result = await deadline(terminal, ms, name);
    if (result.error) throw result.error;
    await until(() => absent(-pid), 2500);
    unresolved.delete(pid);
    receipt.commands[name] = {pid, ...result, groupAbsent: true};
    return {...result, output, stderr};
  }

  async function stop(signal = "SIGINT") {
    if (!pid || !unresolved.has(pid)) return;
    if (!absent(-pid)) process.kill(-pid, signal);
    try {
      return await collect(6000);
    } catch (error) {
      if (!String(error.message).endsWith("_deadline")) throw error;
      if (!absent(-pid)) process.kill(-pid, "SIGKILL");
      return await collect(4000);
    }
  }

  return {pid, collect, stop};
}

async function run(name, program, args, options, timeout = 5000) {
  const child = launch(name, program, args, options);
  try {
    return await child.collect(timeout);
  } finally {
    await child.stop("SIGTERM");
  }
}

async function success(...args) {
  const result = await run(...args);
  assert.equal(result.code, 0, result.stderr + result.output);
  return result.output.trim();
}

function processRows() {
  const table = spawnSync("/bin/ps", ["-axo", "pid=,ppid=,comm="],
    {encoding: "utf8", timeout: 3000, maxBuffer: 8 * 1024 * 1024});
  assert.equal(table.status, 0, "process observation failed");
  return table.stdout.trim().split("\n").map(line => {
    const match = /^(\d+)\s+(\d+)\s+(.+)$/.exec(line.trim());
    assert(match, "process identity unavailable");
    return {pid: Number(match[1]), parentPid: Number(match[2]), command: match[3]};
  }).filter(row => row.pid !== table.pid);
}

function observeWorkerd(phase) {
  return workerdCustody.observe(phase, () => {
    const processes = processRows();
    const identity = selectOwnedWorkerd({ownerPid: process.pid, executable: workerd.default,
      platform: process.platform, processes});
    return {pid: identity.pid, processes};
  });
}

async function signerInputs() {
  const fixture = join(scratch, "fixture");
  const overlay = join(scratch, "overlay.json");
  const services = join(root, "services");
  await mkdir(fixture);
  await writeFile(overlay, JSON.stringify({Replace: {
    [join(services, "internal/publicupdatefixture/fixture_test.go")]:
      join(root, "tests/integration/public-update/fixture_test.go"),
  }}));
  const binary = join(scratch, "signer");
  await success("fixture-signer-build", "go", [
    "test", "-vet=off", "-mod=readonly", "-modcacherw", "-overlay", overlay, "-c", "-o", binary, "./internal/publicupdatefixture",
  ], {cwd: services, env: {...process.env, GOCACHE: join(scratch, "go-build"),
    GOMODCACHE: join(scratch, "go-mod")}}, 120_000);
  await success("fixture-signer", binary, ["-test.run", "^TestSignInputs$"], {cwd: fixture,
    env: {...process.env, FIXTURE_DIRECTORY: fixture, FIXTURE_ADDRESS: "127.0.0.1:0",
      FIXTURE_PUBLISHER: "fixture-only", FIXTURE_FOREIGN: "fixture-only-foreign", FIXTURE_READER: "fixture-only-reader"}});
  const coordinates = JSON.parse(await readFile(join(fixture, "coordinates.json")));
  const assignments = {};
  for (const label of ["publish-first", "promote", "halt", "resume"]) {
    assignments[label] = (await readFile(join(fixture, label + ".json"), "utf8")).trimEnd();
  }
  const manifest = (await readFile(join(fixture, "first", "signed-manifest.json"), "utf8")).trimEnd();
  const payload = await readFile(join(fixture, "first", "payload.wasm"));
  const artifact = '{"signed_manifest":' + manifest + ',"payload":"' + payload.toString("base64") + '"}';
  return {target: {...coordinates.scope, runtime: coordinates.runtime, channel: coordinates.channel},
    installations: coordinates.installations, artifact, assignments, manifestHash: coordinates.first};
}

let postgres;
let mf;
let workerURL;
let workerdCustody;
const originalSpawn = childProcess.spawn;
// Capture the pinned runtime's direct handle even if readiness fails before
// the independent executable/parent observation can run.
childProcess.spawn = function captureWorkerd(program, args, options) {
  if (workerdCustody && program === workerd.default) {
    return workerdCustody.capture(originalSpawn.bind(this), program, args, options);
  }
  return originalSpawn.call(this, program, args, options);
};
try {
  const fixture = await signerInputs();
  const data = join(scratch, "pg");
  // Keep the private socket short enough for Darwin and bind no TCP socket.
  const socket = join(scratch, "s");
  const port = "55432";
  await mkdir(socket);
  receipt.postgres = await success("postgres-version", tools("postgres"), ["--version"]);
  await success("initdb", tools("initdb"), ["-D", data, "-U", "fixture", "--no-locale",
    "--auth-local=trust", "--auth-host=reject", "--no-sync"], {cwd: scratch}, 20_000);
  postgres = launch("postgres", tools("postgres"), ["-D", data, "-p", port, "-h", "", "-k", socket], {cwd: scratch});
  const sqlArgs = ["-X", "-h", socket, "-p", port, "-U", "fixture", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-Atq"];
  const sqlOptions = {cwd: data, env: {...process.env, PGCONNECT_TIMEOUT: "1"}};
  let readiness = 0;
  await until(async () => (await run("db-ready-" + ++readiness, tools("psql"),
    [...sqlArgs, "-c", "SELECT 1"], sqlOptions)).code === 0, 9000);

  // This table is the explicit fixture source for the exporter handoff. The
  // test seeds only signed public bytes, then copies them out through psql.
  const publication = Buffer.from(JSON.stringify(fixture));
  const inserted = publication.toString("hex");
  const selected = await success("fixture-select", tools("psql"), [...sqlArgs, "-c",
    "CREATE TABLE fixture_publication (published bytea NOT NULL); INSERT INTO fixture_publication VALUES (decode('" +
    inserted + "','hex')); SELECT encode(published,'hex') FROM fixture_publication"], sqlOptions);
  assert.deepEqual(Buffer.from(selected, "hex"), publication);
  const {target, assignments, artifact, manifestHash, installations} = JSON.parse(Buffer.from(selected, "hex"));
  const script = name => join(root, "verification/local/w11-delivery-dist", name);
  const common = {
    modules: true, modulesRoot: script(""), compatibilityDate: "2026-07-30",
    modulesRules: [{type: "ESModule", include: ["**/*.js"]}],
    bindings: {DELIVERY_TARGET: JSON.stringify(target)},
    r2Buckets: {DELIVERY_PUBLIC: "local-release-public-only"},
  };
  workerdCustody = new WorkerdCustody();
  mf = new Miniflare({host: "127.0.0.1", port: 0, cf: false, r2Persist: join(scratch, "r2"),
    workers: [
      {...common, name: "delivery", scriptPath: script("src/index.js")},
      {...common, name: "fixture-writer", scriptPath: script("test/worker.js")},
      {...common, name: "projection-delivery", scriptPath: script("src/index.js"),
        r2Buckets: {DELIVERY_PUBLIC: "local-release-projection-test"}},
    ]});
  workerURL = await deadline(mf.ready, 12_000, "workerd_ready");
  observeWorkerd("ready");
  const writer = await deadline(mf.getWorker("fixture-writer"), 5000, "writer_ready");
  const internal = (path, body) => writer.fetch("http://fixture.invalid" + path,
    {method: "POST", body, signal: AbortSignal.timeout(4500)});
  async function write(path, body, expected = 200) {
    const response = await internal(path, body);
    const text = await response.text();
    assert.equal(response.status, expected, text);
    return expected === 200 ? JSON.parse(text) : text;
  }

  const offer = fields => "/v3/updates?" + new URLSearchParams({...target, installation: installations.early, ...fields});
  const download = (fields, digest = manifestHash) => "/v3/artifacts/" + digest + "?" +
    new URLSearchParams({organization: target.organization, project: target.project, ...fields});
  async function get(path, status, method = "GET") {
    const response = await fetch(new URL(path, workerURL), {method, signal: AbortSignal.timeout(4500)});
    assert.equal(response.status, status, path);
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    return Buffer.from(await response.arrayBuffer());
  }

  await get(offer(), 204);
  await get(download(), 404);
  const artifactRef = {manifest_sha256: manifestHash, envelope_sha256: hash(artifact)};
  const signedHashes = {};
  for (const [label, signed] of Object.entries(assignments)) {
    signedHashes[label] = await write("/assignment", signed);
    assert.equal(signedHashes[label], hash(signed));
  }

  function snapshot(revision, label, lease = 60_000) {
    const {sequence, rollout_basis_points} = JSON.parse(assignments[label]).assignment;
    const now = Date.now();
    return {version: 1, target, revision: String(revision), issued_at_ms: now, expires_at_ms: now + lease,
      head: {sequence: String(sequence), assignment_sha256: signedHashes[label],
        artifact_sha256: manifestHash, rollout_basis_points, enabled: true},
      artifacts: [artifactRef]};
  }
  const apply = (value, expected) => write("/snapshot", JSON.stringify(value), expected);
  assert.equal(await apply(snapshot(1, "publish-first"), 409), "snapshot_artifact");
  await get(offer(), 204);
  await get(download(), 404);
  assert.deepEqual(await write("/artifact?digest=" + manifestHash, artifact), artifactRef);
  await get(download(), 404);

  assert.equal(await apply(snapshot(1, "publish-first", 300_001), 409), "snapshot_input");
  const initial = snapshot(1, "publish-first", 6500);
  const wrongWire = JSON.parse(assignments["publish-first"]);
  wrongWire.assignment.sequence = "1";
  assert.equal(await write("/assignment", JSON.stringify(wrongWire), 409), "assignment_input");
  wrongWire.assignment.sequence = 1;
  wrongWire.assignment.scope.organization = "foreign-org";
  assert.equal(await write("/assignment", JSON.stringify(wrongWire), 409), "assignment_input");
  assert.equal(await apply(initial), "applied");
  assert.equal(await apply(initial), "unchanged");
  const expectedOffer = '{"signed_assignment":' + assignments["publish-first"] +
    ',"artifact_url":' + JSON.stringify(download()) + '}';
  const beforeOffer = await get(offer(), 200);
  const beforeArtifact = await get(download(), 200);
  assert.deepEqual(beforeOffer, Buffer.from(expectedOffer));
  assert.deepEqual(beforeArtifact, Buffer.from(artifact));
  await get(offer({installation: installations.outside}), 204);
  await get(offer({installation: installations.expansion}), 204);
  await get(offer({project: "foreign-project"}), 204);
  await get(download({organization: "foreign-org"}), 404);
  await get(download({project: "foreign-project"}), 404);
  for (const mismatch of [{app: "foreign-app"}, {environment: "other"}, {platform: "ios" === target.platform ? "android" : "ios"},
    {runtime: "f".repeat(64)}, {channel: "other"}]) await get(offer(mismatch), 204);
  await get(offer() + "&project=" + target.project, 400);
  await get(offer() + "&x=" + "a".repeat(4200), 400);
  await get(download({}, "f".repeat(64)), 404);
  await get(offer(), 405, "POST");
  await get("/snapshot", 404);
  await get(download({}, manifestHash) + "&installation=x", 400);

  const postgresChildren = processRows().filter(process => process.parentPid === postgres.pid).map(process => process.pid);
  assert(postgresChildren.length > 0, "no PostgreSQL workers observed before shutdown");
  const stopped = await postgres.stop();
  assert.equal(stopped.code, 0, stopped.stderr);
  await until(() => absent(postgres.pid) && postgresChildren.every(absent), 2500);
  receipt.closure.postgresChildrenAbsent = postgresChildren;
  const offline = await run("db-offline", tools("psql"), [...sqlArgs, "-c", "SELECT 1"], sqlOptions);
  assert.equal(offline.code, 2, offline.stderr);
  assert.match(offline.stderr, /No such file or directory|Connection refused/);
  assert.deepEqual(await get(offer(), 200), beforeOffer);
  assert.deepEqual(await get(download(), 200), beforeArtifact);
  await get(offer({organization: "foreign-org"}), 204);
  await get(download({project: "foreign-project"}), 404);
  receipt.checks.outage = {upstreamReadBefore: true, upstreamConnectionFailedAfter: true,
    assignmentSequence: initial.head.sequence, offerBytes: beforeOffer.length, offerSha256: hash(beforeOffer),
    artifactBytes: beforeArtifact.length, artifactEnvelopeSha256: hash(beforeArtifact), artifactManifestSha256: manifestHash,
    exactBeforeAfter: true, tenantMismatch: {offer: 204, artifact: 404}};
  await delay(Math.max(0, initial.expires_at_ms - Date.now() + 25));
  assert(absent(-postgres.pid));
  await get(offer(), 204);
  await get(download(), 404);
  receipt.checks.expiryOffline = {offer: 204, artifact: 404};

  const promoted = snapshot(2, "promote");
  assert.equal(await apply(promoted), "applied");
  await get(offer({installation: installations.expansion}), 200);
  await get(offer({installation: installations.outside}), 204);
  const replacedBytes = artifact + " ";
  assert.equal(await write("/artifact?digest=" + manifestHash, replacedBytes, 409), "object_digest");
  assert.deepEqual(await get(download(), 200), beforeArtifact);

  const halt = snapshot(3, "halt");
  assert.equal(await apply(halt), "applied");
  await get(offer(), 204);
  assert.deepEqual(await get(download(), 200), beforeArtifact);
  assert.equal(await apply(snapshot(4, "promote"), 409), "snapshot_stale");
  const resumed = snapshot(4, "resume");
  assert.equal(await apply(resumed), "applied");
  await get(offer(), 200);

  const conflicting = snapshot(5, "resume");
  conflicting.head.sequence = "7";
  assert.equal(await apply(conflicting, 409), "snapshot_assignment");
  const bucket = await mf.getR2Bucket("DELIVERY_PUBLIC", "delivery");
  const pointerKey = ["v1", target.organization, target.project, target.app, target.environment,
    target.platform, target.runtime, target.channel].join(":") + "/current";
  const priorPointer = await bucket.get(pointerKey);
  const priorPointerBytes = await priorPointer.text();

  const revoked = snapshot(5, "resume");
  revoked.head.enabled = false;
  revoked.artifacts = [];
  const other = structuredClone(revoked);
  other.expires_at_ms -= 1000;
  const attempts = await Promise.all([internal("/snapshot", JSON.stringify(revoked)), internal("/snapshot", JSON.stringify(other))]);
  const results = await Promise.all(attempts.map(response => response.text()));
  assert.equal(results.filter(value => value === '"applied"').length, 1, results.join(", "));
  assert(results.some(value => value === '"retry"' || value === "snapshot_stale"), results.join(", "));
  const staleWrite = await bucket.put(pointerKey, priorPointerBytes,
    {onlyIf: {etagMatches: priorPointer.etag}});
  assert.equal(staleWrite, null, "old pointer ETag must not restore the prior grant");
  await get(offer(), 204);
  await get(download(), 404);
  assert.equal(await apply(snapshot(6, "resume"), 409), "snapshot_stale");
  receipt.checks.snapshot = {missingArtifactRejected: true, stagedArtifactInvisible: true,
    exactReplayUnchanged: true, leaseMaximumEnforced: true, olderSequenceRejected: true, mismatchedAssignmentRejected: true, invalidStageRejected: true,
    immutableArtifactOverwriteRejected: true, cohort: {beforeExpansion: 204, afterExpansion: 200, outside: 204},
    haltSequence: halt.head.sequence, haltOffer: 204, haltArtifact: 200, resumeOffer: 200,
    revocation: {offer: 204, artifact: 404, sameSequenceReopenRejected: true, stalePointerETagRejected: true, concurrentApplyResults: results.sort()}};
  const {publishProjection} = await import(script("src/publisher.js"));
  const {current} = await import(script("src/storage.js"));
  receipt.checks.projectionPublisher = await exerciseProjectionPublisher({
    bucket: await mf.getR2Bucket("DELIVERY_PUBLIC", "projection-delivery"),
    worker: await mf.getWorker("projection-delivery"),
    target, assignments, artifact, manifestHash, installation: installations.early,
    current, publishProjection,
  });
  receipt.status = "passed";
} catch (error) {
  receipt.failure = error.message;
  throw error;
} finally {
  try {
    const closures = await Promise.allSettled([
      postgres?.stop(),
      (async () => {
        if (!workerdCustody) return;
        if (workerdCustody.receipt.ready === "verified") {
          try { observeWorkerd("beforeDispose"); } catch {
            // Retain the failed observation and still dispose through Miniflare.
          }
        }
        await workerdCustody.close(mf && (() => mf.dispose()));
        const {pid, pgid, close, exactPidAbsent, groupAbsent} = workerdCustody.receipt;
        if (close && exactPidAbsent) {
          receipt.closure.workerd = [{pid, pgid, ...close, exactPidAbsent, groupAbsent}];
        }
      })(),
    ]);
    const failed = closures.find(result => result.status === "rejected");
    if (failed) throw failed.reason;
    assert.equal(unresolved.size, 0, "unresolved process group custody");
    if (workerURL) await assert.rejects(fetch(workerURL, {signal: AbortSignal.timeout(1000)}), /fetch failed/);
    await removeReplayScratch(scratch, workerdCustody);
    receipt.closure.scratchRemoved = true;
  } catch (error) {
    const replayPassed = receipt.status === "passed";
    receipt.status = "failed";
    receipt.closure.hold = {error: error.message.slice(0, 256), scratch,
      workerd: workerdCustody?.receipt, unresolvedCount: unresolved.size, unresolved: [...unresolved].slice(0, 8)};
    if (replayPassed) throw error;
  } finally {
    childProcess.spawn = originalSpawn;
    process.stdout.write(JSON.stringify(receipt, null, 2) + "\n");
  }
}
