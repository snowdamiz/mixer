// Repeat the reviewed controller suites without overwriting frozen evidence.
import {createHash} from "node:crypto";
import {spawn, spawnSync} from "node:child_process";
import {mkdir, mkdtemp, readFile, readdir, copyFile, writeFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, resolve} from "node:path";

const project = resolve(import.meta.dirname, ".."), root = resolve(project, "..");
const output = process.env.MIXER_CONTROLLER_CHECK_DIR
  ? resolve(process.env.MIXER_CONTROLLER_CHECK_DIR)
  : await mkdtemp(join(tmpdir(), "mixer-controller-check-"));
if (process.env.MIXER_CONTROLLER_CHECK_DIR) await mkdir(output, {recursive: false});
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const source = {};
async function bindFile(path) {
  const name = path.slice(root.length + 1), bytes = await readFile(path);
  source[name] = hash(bytes);
  const snapshot = join(output, "source", name);
  await mkdir(resolve(snapshot, ".."), {recursive: true});
  await writeFile(snapshot, bytes);
}
async function inventory(directory) {
  for (const item of await readdir(directory, {withFileTypes: true})) {
    const path = join(directory, item.name);
    if (item.isDirectory()) await inventory(path);
    else if (item.isFile()) await bindFile(path);
    else throw new Error("unexpected_source_entry: " + path);
  }
}
await inventory(join(project, "src"));
await inventory(join(project, "test"));
for (const name of ["package.json", "package-lock.json", "build.mjs", "audit-build.mjs", "tsconfig.json"])
  await bindFile(join(project, name));
for (const name of [
  "verification/hosted-worker-controller-contract/acceptance.mjs",
  "verification/hosted-worker-controller-contract/vectors.json",
  "verification/hosted-worker-transport/cross-runtime-vectors.json",
  "verification/hosted-worker-controller-implementation/jason-control-vectors.json",
  "verification/hosted-worker-controller-v2/inputs/verification/hosted-worker-controller-implementation-independent-review/regressions.mjs",
  "verification/hosted-worker-controller-v2/focused.mjs",
]) await bindFile(join(root, name));
const orderedSource = Object.fromEntries(Object.entries(source).sort(([a], [b]) => a.localeCompare(b)));
const sourceDigest = hash(JSON.stringify(orderedSource));
await writeFile(join(output, "source-manifest.json"), JSON.stringify(orderedSource, null, 2) + "\n");
const commands = [];
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function alive(pid) {
  try { process.kill(-pid, 0); return true; }
  catch (error) { if (error.code === "ESRCH") return false; throw error; }
}
function signalGroup(pid, signal) {
  try { process.kill(-pid, signal); }
  catch (error) { if (error.code !== "ESRCH") throw error; }
}
async function run(name, args, extraEnv = {}) {
  const directory = join(output, name);
  await mkdir(directory);
  const scratch = join(directory, "scratch");
  await mkdir(scratch);
  const stdout = [], stderr = [], started = new Date().toISOString();
  const child = spawn(process.execPath, args, {
    cwd: project, detached: true, stdio: ["ignore", "pipe", "pipe"],
    env: {...process.env, ...extraEnv, TMPDIR: scratch, TMP: scratch, TEMP: scratch},
  });
  child.stdout.on("data", bytes => stdout.push(bytes));
  child.stderr.on("data", bytes => stderr.push(bytes));
  let exitCode = null, exitSignal = null, timedOut = false, spawnError = null;
  const processManagementErrors = [];
  const probe = () => {
    if (!child.pid) return false;
    try { return alive(child.pid); }
    catch (error) { processManagementErrors.push({operation: "probe", code: error.code, message: error.message}); return null; }
  };
  const send = signal => {
    if (!child.pid) return;
    try { signalGroup(child.pid, signal); }
    catch (error) { processManagementErrors.push({operation: signal, code: error.code, message: error.message}); }
  };
  const exited = new Promise(resolve => {
    child.once("exit", (code, signal) => { exitCode = code; exitSignal = signal; resolve(); });
    child.once("error", error => { spawnError = error.message; resolve(); });
  });
  const closed = new Promise(resolve => child.once("close", resolve));
  const timer = setTimeout(() => { timedOut = true; send("SIGTERM"); }, 300_000);
  const forceTimer = setTimeout(() => send("SIGKILL"), 305_000);
  let terminalTimer, directChildTerminal = false;
  await Promise.race([
    exited.then(() => { directChildTerminal = true; }),
    new Promise(resolve => { terminalTimer = setTimeout(() => { timedOut = true; resolve(); }, 310_000); }),
  ]);
  clearTimeout(terminalTimer);
  clearTimeout(timer); clearTimeout(forceTimer);
  const signals = [];
  // Retire owned descendants even if the direct test process exited first.
  for (const signal of ["SIGTERM", "SIGKILL"]) {
    if (probe() !== true) break;
    send(signal); signals.push(signal);
    const deadline = performance.now() + 5_000;
    while (probe() === true && performance.now() < deadline) await pause(25);
  }
  const terminalGroupState = probe();
  const processGroupEmpty = terminalGroupState === false && processManagementErrors.length === 0;
  // Wait for pipe EOF, not just the direct child's exit, before hashing output.
  let closeTimer, eofObserved = false, eofError = null;
  try {
    await Promise.race([closed, new Promise((_, reject) => {
      closeTimer = setTimeout(() => reject(new Error("owned_output_eof_timeout: " + name)), 5_000);
    })]);
    eofObserved = true;
  } catch (error) {
    eofError = error.message;
    // A failed EOF check must still retain the output already observed and a
    // command receipt. Preserve scratch while an unknown holder may remain.
    child.stdout.destroy(); child.stderr.destroy();
  } finally { clearTimeout(closeTimer); }
  const remainingTemporaryEntries = await readdir(scratch);
  const scratchRemoved = directChildTerminal && processGroupEmpty && eofObserved;
  if (scratchRemoved) await rm(scratch, {recursive: true});
  const out = Buffer.concat(stdout), err = Buffer.concat(stderr);
  await writeFile(join(directory, "stdout"), out);
  await writeFile(join(directory, "stderr"), err);
  const record = {name, argv: [process.execPath, ...args], cwd: project, started,
    finished: new Date().toISOString(), pid: child.pid ?? null, exitCode, exitSignal,
    timedOut, spawnError, signals, processGroupEmpty, sourceDigest, eofObserved, eofError,
    directChildTerminal, terminalGroupState, processManagementErrors,
    directChildUnrefOnFailure: !directChildTerminal,
    scratch, scratchRemoved, remainingTemporaryEntries,
    stdoutSHA256: hash(out), stderrSHA256: hash(err)};
  commands.push(record);
  await writeFile(join(directory, "command.json"), JSON.stringify(record, null, 2) + "\n");
  // Return the incomplete-cleanup receipt after the finite observation window;
  // an unconfirmed child must not silently keep this reporting process alive.
  if (!directChildTerminal) child.unref();
  console.log(JSON.stringify({name, exitCode, timedOut, processGroupEmpty}));
  if (exitCode !== 0 || timedOut || spawnError || !directChildTerminal || !processGroupEmpty || !eofObserved)
    throw new Error("controller_check_failed: " + name);
}

let failure = null;
try {
  await run("build", ["build.mjs"]);
  await run("original", ["test/run.mjs"], {MIXER_CONTROLLER_TEST_REPORT: join(output, "original-report.json")});
  for (const [name, fixture] of [
    ["regressions", "verification/hosted-worker-controller-v2/inputs/verification/hosted-worker-controller-implementation-independent-review/regressions.mjs"],
    ["focused", "verification/hosted-worker-controller-v2/focused.mjs"],
  ]) {
    const directory = join(output, name + "-fixture");
    await mkdir(directory);
    const bytes = await readFile(join(root, fixture));
    await copyFile(join(root, fixture), join(directory, name + ".mjs"));
    await writeFile(join(directory, "bindings.json"), JSON.stringify({scratch: root, source_tree_sha256: sourceDigest, fixture, fixtureSHA256: hash(bytes)}, null, 2) + "\n");
    await run(name, [join(directory, name + ".mjs")], {MIXER_V2_RUN_DIR: directory});
  }
  await run("production-closure", ["audit-build.mjs"], {MIXER_CONTROLLER_CLOSURE_REPORT: join(output, "production-closure.json")});
  for (const report of ["original-report.json", "regressions-fixture/regression-report.json", "focused-fixture/focused-report.json"]) {
    const value = JSON.parse(await readFile(join(output, report), "utf8"));
    if (value.status !== "passed") throw new Error("failed_report: " + report);
    for (const entry of value.cleanup) {
      if (entry.persist) {
        try { await readdir(entry.persist); throw new Error("owned_storage_survived: " + entry.persist); }
        catch (error) { if (error.code !== "ENOENT") throw error; }
      }
    }
  }
  for (const [name, expected] of Object.entries(orderedSource))
    if (hash(await readFile(join(root, name))) !== expected) throw new Error("source_changed_during_checks: " + name);
} catch (error) { failure = error.stack; }
const revision = spawnSync("git", ["rev-parse", "HEAD"], {cwd: root, encoding: "utf8"});
const dependencies = {};
for (const name of ["typescript", "miniflare", "workerd", "@cloudflare/workers-types"])
  dependencies[name] = JSON.parse(await readFile(join(project, "node_modules", name, "package.json"), "utf8")).version;
const result = {status: failure ? "failed" : "passed", revision: revision.stdout.trim(),
  node: process.version, platform: process.platform, architecture: process.arch,
  dependencies, sourceDigest, commands, failure, output,
  scope: "Local workerd/SQLite controller; synthetic clock and provider; no cloud or GA qualification"};
await writeFile(join(output, "receipt.json"), JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify({status: result.status, output}));
if (failure) { console.error(failure); process.exitCode = 1; }
